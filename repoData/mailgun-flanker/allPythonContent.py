__FILENAME__ = address
# coding:utf-8

'''
Public interface for flanker address (email or url) parsing and validation
capabilities.

Public Functions in flanker.addresslib.address module:

    * parse(address, addr_spec_only=False)

      Parse a single address or URL. Can parse just the address spec or the
      full mailbox.

    * parse_list(address_list, strict=False, as_tuple=False)

      Parse a list of addresses, operates in strict or relaxed modes. Strict
      mode will fail at the first instance of invalid grammar, relaxed modes
      tries to recover and continue.

    * validate_address(addr_spec)

      Validates (parse, plus dns, mx check, and custom grammar) a single
      address spec. In the case of a valid address returns an EmailAddress
      object, otherwise returns None.

    * validate_list(addr_list, as_tuple=False)

      Validates an address list, and returns a tuple of parsed and unparsed
      portions.

When valid addresses are returned, they are returned as an instance of either
EmailAddress or UrlAddress in flanker.addresslib.address.

See the parser.py module for implementation details of the parser.
'''

import time
import flanker.addresslib.parser
import flanker.addresslib.validate

from flanker.addresslib.parser import MAX_ADDRESS_LENGTH
from flanker.utils import is_pure_ascii
from flanker.utils import metrics_wrapper
from flanker.mime.message.headers.encoding import encode_string
from flanker.mime.message.headers.encodedword import mime_to_unicode
from urlparse import urlparse

@metrics_wrapper()
def parse(address, addr_spec_only=False, metrics=False):
    '''
    Given an string, returns a scalar object representing a single full
    mailbox (display name and addr-spec), addr-spec, or a url.

    Returns an Address object and optionally metrics on processing
    time if requested.

    Examples:
        >>> address.parse('John Smith <john@smith.com')
        John Smith <john@smith.com>

        >>> print address.parse('John <john@smith.com>', addr_spec_only=True)
        None

        >>> print address.parse('john@smith.com', addr_spec_only=True)
        'john@smith.com'

        >>> address.parse('http://host.com/post?q')
        http://host.com/post?q

        >>> print address.parse('foo')
        None
    '''
    mtimes = {'parsing': 0}

    parser = flanker.addresslib.parser._AddressParser(False)

    try:
        # addr-spec only
        if addr_spec_only:
            bstart = time.time()
            retval = parser.address_spec(address)
            mtimes['parsing'] = time.time() - bstart
            return retval, mtimes

        # full address
        bstart = time.time()
        retval = parser.address(address)
        mtimes['parsing'] = time.time() - bstart
        return retval, mtimes

    # supress any exceptions and return None
    except flanker.addresslib.parser.ParserException:
        return None, mtimes


@metrics_wrapper()
def parse_list(address_list, strict=False, as_tuple=False, metrics=False):
    '''
    Given an string or list of email addresses and/or urls seperated by a
    delimiter (comma (,) or semi-colon (;)), returns an AddressList object
    (an iterable list representing parsed email addresses and urls).

    The Parser operates in strict or relaxed modes. In strict mode the parser
    will quit at the first occurrence of error, in relaxed mode the parser
    will attempt to seek to to known valid location and continue parsing.

    The parser can return a list of parsed addresses or a tuple containing
    the parsed and unparsed portions. The parser also returns the parsing
    time metrics if requested.

    Examples:
        >>> address.parse_list('A <a@b>')
        [A <a@b>]

        >>> address.parse_list('A <a@b>, C <d@e>')
        [A <a@b>, C <d@e>]

        >>> address.parse_list('A <a@b>, C, D <d@e>')
        [A <a@b>, D <d@e>]

        >>> address.parse_list('A <a@b>, C, D <d@e>')
        [A <a@b>]

        >>> address.parse_list('A <a@b>, D <d@e>, http://localhost')
        [A <a@b>, D <d@e>, http://localhost]
    '''
    mtimes = {'parsing': 0}
    parser = flanker.addresslib.parser._AddressParser(strict)

    # if we have a list, transform it into a string first
    if isinstance(address_list, list):
        address_list = ', '.join([str(addr) for addr in address_list])

    # parse
    try:
        bstart = time.time()
        if strict:
            p = parser.address_list(address_list)
            u = []
        else:
            p, u = parser.address_list(address_list)
        mtimes['parsing'] = time.time() - bstart
    except flanker.addresslib.parser.ParserException:
        p, u = (AddressList(), [])

    # return as tuple or just parsed addresses
    if as_tuple:
        return p, u, mtimes
    return p, mtimes


@metrics_wrapper()
def validate_address(addr_spec, metrics=False):
    '''
    Given an addr-spec, runs the pre-parser, the parser, DNS MX checks,
    MX existence checks, and if available, ESP specific grammar for the
    local part.

    In the case of a valid address returns an EmailAddress object, otherwise
    returns None. If requested, will also return the parsing time metrics.

    Examples:
        >>> address.validate_address('john@non-existent-domain.com')
        None

        >>> address.validate_address('user@gmail.com')
        None

        >>> address.validate_address('user.1234@gmail.com')
        user.1234@gmail.com
    '''
    mtimes = {'parsing': 0, 'mx_lookup': 0,
        'dns_lookup': 0, 'mx_conn':0 , 'custom_grammar':0}

    # sanity check
    if addr_spec is None:
        return None, mtimes
    if not is_pure_ascii(addr_spec):
        return None, mtimes

    # preparse address into its parts and perform any ESP specific pre-parsing
    addr_parts = flanker.addresslib.validate.preparse_address(addr_spec)
    if addr_parts is None:
        return None, mtimes

    # run parser against address
    bstart = time.time()
    paddr = parse('@'.join(addr_parts), addr_spec_only=True)
    mtimes['parsing'] = time.time() - bstart
    if paddr is None:
        return None, mtimes

    # lookup if this domain has a mail exchanger
    exchanger, mx_metrics = \
        flanker.addresslib.validate.mail_exchanger_lookup(addr_parts[-1], metrics=True)
    mtimes['mx_lookup'] = mx_metrics['mx_lookup']
    mtimes['dns_lookup'] = mx_metrics['dns_lookup']
    mtimes['mx_conn'] = mx_metrics['mx_conn']
    if exchanger is None:
        return None, mtimes

    # lookup custom local-part grammar if it exists
    bstart = time.time()
    plugin = flanker.addresslib.validate.plugin_for_esp(exchanger)
    mtimes['custom_grammar'] = time.time() - bstart
    if plugin and plugin.validate(addr_parts[0]) is False:
        return None, mtimes

    return paddr, mtimes


@metrics_wrapper()
def validate_list(addr_list, as_tuple=False, metrics=False):
    '''
    Validates an address list, and returns a tuple of parsed and unparsed
    portions.

    Returns results as a list or tuple consisting of the parsed addresses
    and unparsable protions. If requested, will also return parisng time
    metrics.

    Examples:
        >>> address.validate_address_list('a@mailgun.com, c@mailgun.com')
        [a@mailgun.com, c@mailgun.com]

        >>> address.validate_address_list('a@mailgun.com, b@example.com')
        [a@mailgun.com]

        >>> address.validate_address_list('a@b, c@d, e@example.com', as_tuple=True)
        ([a@mailgun.com, c@mailgun.com], ['e@example.com'])
    '''
    mtimes = {'parsing': 0, 'mx_lookup': 0,
        'dns_lookup': 0, 'mx_conn':0 , 'custom_grammar':0}


    if addr_list is None:
        return None, mtimes

    # parse addresses
    bstart = time.time()
    parsed_addresses, unparseable = parse_list(addr_list, as_tuple=True)
    mtimes['parsing'] = time.time() - bstart

    plist = flanker.addresslib.address.AddressList()
    ulist = []

    # make sure parsed list pass dns and esp grammar
    for paddr in parsed_addresses:

        # lookup if this domain has a mail exchanger
        exchanger, mx_metrics = \
            flanker.addresslib.validate.mail_exchanger_lookup(paddr.hostname, metrics=True)
        mtimes['mx_lookup'] += mx_metrics['mx_lookup']
        mtimes['dns_lookup'] += mx_metrics['dns_lookup']
        mtimes['mx_conn'] += mx_metrics['mx_conn']

        if exchanger is None:
            ulist.append(paddr.full_spec())
            continue

        # lookup custom local-part grammar if it exists
        plugin = flanker.addresslib.validate.plugin_for_esp(exchanger)
        bstart = time.time()
        if plugin and plugin.validate(paddr.mailbox) is False:
            ulist.append(paddr.full_spec())
            continue
        mtimes['custom_grammar'] = time.time() - bstart

        plist.append(paddr)

    # loop over unparsable list and check if any can be fixed with
    # preparsing cleanup and if so, run full validator
    for unpar in unparseable:
        paddr, metrics = validate_address(unpar, metrics=True)
        if paddr:
            plist.append(paddr)
        else:
            ulist.append(unpar)

        # update all the metrics
        for k, v in metrics.iteritems():
            metrics[k] += v

    if as_tuple:
        return plist, ulist, mtimes
    return plist, mtimes


def is_email(string):
    if parse(string, True):
        return True
    return False


class Address(object):
    '''
    Base class that represents an address (email or URL). Use it to create
    concrete instances of different addresses:
    '''

    @property
    def supports_routing(self):
        "Indicates that by default this address cannot be routed"
        return False


    class Type(object):
        '''
        Enumerates the types of addresses we support:
            >>> parse('foo@example.com').addr_type
            'email'

            >>> parse('http://example.com').addr_type
            'url'
        '''
        Email = 'email'
        Url   = 'url'


class EmailAddress(Address):
    '''
    Represents a fully parsed email address with built-in support for MIME
    encoding. Note, do not use EmailAddress class directly, use the parse()
    or parse_list() functions to return a scalar or iterable list respectively.

    Examples:
       >>> addr = EmailAddress("Bob Silva", "bob@host.com")
       >>> addr.address
       'bob@host.com'
       >>> addr.hostname
       'host.com'
       >>> addr.mailbox
       'bob'

    Display name is always returned in Unicode, i.e. ready to be displayed on
    web forms:

       >>> addr.display_name
       u'Bob Silva'

    And full email spec is 100% ASCII, encoded for MIME:
       >>> addr.full_spec()
       'Bob Silva <bob@host.com>'
    '''

    __slots__ = ['display_name', 'mailbox', 'hostname', 'address']

    def __init__(self, display_name, spec=None):
        if spec is None:
            spec = display_name
            display_name = None

        assert(spec)

        if display_name is None:
            self.display_name = u''
        else:
            self.display_name = encode_string(None, display_name,
                                              maxlinelen=MAX_ADDRESS_LENGTH)

        parts = spec.rsplit('@', 1)
        self.mailbox = parts[0]
        self.hostname = parts[1].lower()
        self.address = self.mailbox + "@" + self.hostname
        self.addr_type = self.Type.Email

    def __repr__(self):
        '''
        >>> repr(EmailAddress("John Smith", "john@smith.com"))
        'John Smith <john@smith.com>'
        '''
        return self.full_spec()

    def __str__(self):
        '''
        >>> str(EmailAddress("boo@host.com"))
        'boo@host.com'
        '''
        return self.address

    @property
    def supports_routing(self):
        "Email addresses can be routed"
        return True

    @property
    def display_name(self):
        if self._display_name is None:
            return u''
        return mime_to_unicode(self._display_name)

    @display_name.setter
    def display_name(self, value):
        self._display_name = value

    def full_spec(self):
        '''
        Returns a full spec of an email address. Always in ASCII, RFC-2822
        compliant, safe to be included into MIME:

           >>> EmailAddress("Ev K", "ev@example.com").full_spec()
           'Ev K <ev@host.com>'
           >>> EmailAddress("Жека", "ev@example.com").full_spec()
           '=?utf-8?b?0JbQtdC60LA=?= <ev@example.com>'
        '''
        if self._display_name:
            return '{0} <{1}>'.format(self._display_name, self.address)
        return u'{0}'.format(self.address)

    def to_unicode(self):
        "Converts to unicode"
        if self.display_name:
            return u'{0} <{1}>'.format(self.display_name, self.address)
        return u'{0}'.format(self.address)

    def __cmp__(self, other):
        return True

    def __eq__(self, other):
        "Allows comparison of two addresses"
        if other:
            if isinstance(other, basestring):
                other = parse(other)
                if not other:
                    return False
            return self.address.lower() == other.address.lower()
        return False

    def __hash__(self):
        '''
        Hashing allows using Address objects as keys in collections and compare
        them in sets

            >>> a = Address.from_string("a@host")
            >>> b = Address.from_string("A <A@host>")
            >>> hash(a) == hash(b)
            True
            >>> s = set()
            >>> s.add(a)
            >>> s.add(b)
            >>> len(s)
            1
        '''
        return hash(self.address.lower())



class UrlAddress(Address):
    '''
    Represents a parsed URL:
        >>> url = UrlAddress("http://user@host.com:8080?q=a")
        >>> url.hostname
        'host.com'
        >>> url.port
        8080
        >>> url.scheme
        'http'
        >>> str(url)
        'http://user@host.com:8080?q=a'

    Note: do not create UrlAddress class directly by passing raw "internet
    data", use the parse() and parse_list() functions instead.
    '''

    __slots__ = ['address', 'parse_result']

    def __init__(self, spec):
        self.address = spec
        self.parse_result = urlparse(spec)
        self.addr_type = self.Type.Url

    @property
    def hostname(self):
        hostname = self.parse_result.hostname
        if hostname:
            return hostname.lower()

    @property
    def port(self):
        return self.parse_result.port

    @property
    def scheme(self):
        return self.parse_result.scheme

    @property
    def path(self):
        return self.parse_result.path

    def __str__(self):
        return self.address

    def full_spec(self):
        return self.address

    def to_unicode(self):
        return self.address

    def __str__(self):
        return self.address

    def __repr__(self):
        return self.address

    def __eq__(self, other):
        "Allows comparison of two URLs"
        if other:
            if not isinstance(other, basestring):
                other = other.address
            return self.address == other

    def __hash__(self):
        return hash(self.address)


class AddressList(object):
    '''
    Keeps the list of addresses. Each address is an EmailAddress or
    URLAddress objectAddress-derived object.

    To create a list, use the parse_list method, do not create an
    AddressList directly.

    To see if the address is in the list:
        >>> "missing@host.com" in al
        False
        >>> "bob@host.COM" in al
        True
    '''

    def __init__(self, container=None):
        if container is None:
            container = []
        self.container = container


    def append(self, n):
        self.container.append(n)

    def remove(self, n):
        self.container.remove(n)

    def __iter__(self):
        return iter(self.container)

    def __getitem__(self, key):
        return self.container[key]

    def __len__(self):
        return len(self.container)

    def __eq__(self, other):
        "When comparing ourselves to other lists we must ignore order"
        if isinstance(other, list):
            other = parse_list(other)
        return set(self.container) == set(other.container)

    def __str__(self):
        return ''.join(['[', self.full_spec(), ']'])

    def __repr__(self):
        return ''.join(['[', self.full_spec(), ']'])

    def __add__(self, other):
        "Adding two AddressLists together yields another AddressList"
        if isinstance(other, list):
            result = self.container + parse_list(other).container
        else:
            result = self.container + other.container
        return AddressList(result)

    def full_spec(self, delimiter=", "):
        '''
        Returns a full string which looks pretty much what the original was
        like
            >>> adl = AddressList("Foo <foo@host.com>, Bar <bar@host.com>")
            >>> adl.full_spec(delimiter='; ')
            'Foo <foo@host.com; Bar <bar@host.com>'
        '''
        return delimiter.join(addr.full_spec() for addr in self.container)

    def to_unicode(self, delimiter=u", "):
        return delimiter.join(addr.to_unicode() for addr in self.container)

    def to_ascii_list(self):
        return [addr.full_spec() for addr in self.container]

    @property
    def addresses(self):
        '''
        Returns a list of just addresses, i.e. no names:
            >>> adl = AddressList("Foo <foo@host.com>, Bar <bar@host.com>")
            >>> adl.addresses
            ['foo@host.com', 'bar@host.com']
        '''
        return [addr.address for addr in self.container]

    def __str__(self):
        return self.full_spec()

    @property
    def hostnames(self):
        "Returns a set of hostnames used in addresses in this list"
        return set([addr.hostname for addr in self.container])

    @property
    def addr_types(self):
        "Returns a set of address types used in addresses in this list"
        return set([addr.addr_type for addr in self.container])




########NEW FILE########
__FILENAME__ = corrector
# coding:utf-8
'''
Spelling corrector library, used to correct common typos in domains like
gmal.com instead of gmail.com.

The spelling corrector uses difflib which in turn uses the
Ratcliff-Obershelp algorithm [1] to compute the similarity of two strings.
This is a very fast an accurate algorithm for domain spelling correction.

The (only) public method this module has is suggest(word), which given
a domain, suggests an alternative or returns the original domain
if no suggestion exists.

[1] http://xlinux.nist.gov/dads/HTML/ratcliffObershelp.html
'''

import difflib


def suggest(word, cutoff=0.77):
    '''
    Given a domain and a cutoff heuristic, suggest an alternative or return the
    original domain if no suggestion exists.
    '''
    if word in LOOKUP_TABLE:
        return LOOKUP_TABLE[word]

    guess = difflib.get_close_matches(word, MOST_COMMON_DOMAINS, n=1, cutoff=cutoff)
    if guess and len(guess) > 0:
        return guess[0]
    return word


MOST_COMMON_DOMAINS = [
    # mailgun :)
    'mailgun.net',
    # big esps
    'yahoo.com',
    'yahoo.ca',
    'yahoo.co.jp',
    'yahoo.co.uk',
    'ymail.com',
    'hotmail.com',
    'hotmail.ca',
    'hotmail.co.uk',
    'windowslive.com',
    'live.com',
    'outlook.com',
    'msn.com',
    'gmail.com',
    'googlemail.com',
    'aol.com',
    'aim.com',
    'icloud.com',
    'me.com',
    'mac.com',
    'facebook.com',
    # big isps
    'comcast.net',
    'sbcglobal.net',
    'bellsouth.net',
    'verizon.net',
    'earthlink.net',
    'cox.net',
    'charter.net',
    'shaw.ca',
    'bell.net'
]

# domains that the corrector doesn't fix that we should fix
LOOKUP_TABLE = {
    u'yahoo':       u'yahoo.com',
    u'gmail':       u'gmail.com',
    u'hotmail':     u'hotmail.com',
    u'live':        u'live.com',
    u'outlook':     u'outlook.com',
    u'msn':         u'msn.com',
    u'googlemail':  u'googlemail.com',
    u'aol':         u'aol.com',
    u'aim':         u'aim.com',
    u'icloud':      u'icloud.com',
    u'me':          u'me.com',
    u'mac':         u'mac.com',
    u'facebook':    u'facebook.com',
    u'comcast':     u'comcast.net',
    u'sbcglobal':   u'sbcglobal.net',
    u'bellsouth':   u'bellsouth.net',
    u'verizon':     u'verizon.net',
    u'earthlink':   u'earthlink.net',
    u'cox':         u'cox.net',
    u'charter':     u'charter.net',
    u'shaw':        u'shaw.ca',
    u'bell':        u'bell.net'
}

########NEW FILE########
__FILENAME__ = dns_lookup
import collections
import dnsq


class DNSLookup(collections.MutableMapping):
    "DNSLookup has the same interface as a dict, but talks to a DNS server"

    def __init__(self):
        pass

    def __getitem__(self, key):
        try:
            return dnsq.mx_hosts_for(key)
        except:
            return []

    def __setitem__(self, key, value):
        raise InvalidOperation('Setting MX record not supported.')

    def __delitem__(self, key):
        raise InvalidOperation('Deleting MX record not supported.')

    def __iter__(self):
        raise InvalidOperation('Iterating over MX records not supported.')

    def __len__(self):
        raise InvalidOperation('Length of MX records not supported.')


class InvalidOperation(Exception):
    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return self.reason

########NEW FILE########
__FILENAME__ = redis_driver
import collections
import redis

class RedisCache(collections.MutableMapping):
    "RedisCache has the same interface as a dict, but talks to a redis server"

    def __init__(self, host='localhost', port=6379, prefix='mxr:', ttl=604800):
        self.prefix = prefix
        self.ttl = ttl
        self.r = redis.StrictRedis(host=host, port=port, db=0)

    def __getitem__(self, key):
        try:
            return self.r.get(self.__keytransform__(key))
        except:
            return None

    def __setitem__(self, key, value):
        try:
            return self.r.setex(self.__keytransform__(key), self.ttl, value)
        except:
            return None

    def __delitem__(self, key):
        self.r.delete(self.__keytransform__(key))

    def __iter__(self):
        try:
            return self.__value_generator__(self.r.keys(self.prefix + '*'))
        except:
            return iter([])

    def __len__(self):
        try:
            return len(self.r.keys(self.__keytransform__('*')))
        except:
            return 0

    def __keytransform__(self, key):
        return ''.join([self.prefix, str(key)])

    def __value_generator__(self, keys):
        for key in keys:
            yield self.r.get(key)

########NEW FILE########
__FILENAME__ = parser
# coding:utf-8

'''
_AddressParser is an implementation of a recursive descent parser for email
addresses and urls. While _AddressParser can be used directly it is not
recommended, use the the parse() and parse_list() methods which are provided
in the address module for convenience.

The grammar supported by the parser (as well as other limitations) are
outlined below. Plugins are also supported to allow for custom more
restrictive grammar that is typically seen at large Email Service Providers
(ESPs).

For email addresses, the grammar tries to stick to RFC 5322 as much as
possible, but includes relaxed (lax) grammar as well to support for common
realistic uses of email addresses on the Internet.

Grammar:


    address-list      ->    address { delimiter address }
    mailbox           ->    name-addr-rfc | name-addr-lax | addr-spec | url

    name-addr-rfc     ->    [ display-name-rfc ] angle-addr-rfc
    display-name-rfc  ->    [ whitespace ] word { whitespace word }
    angle-addr-rfc    ->    [ whitespace ] < addr-spec > [ whitespace ]

    name-addr-lax     ->    [ display-name-lax ] angle-addr-lax
    display-name-lax  ->    [ whitespace ] word { whitespace word } whitespace
    angle-addr-lax    ->    addr-spec [ whitespace ]

    addr-spec         ->    [ whitespace ] local-part @ domain [ whitespace ]
    local-part        ->    dot-atom | quoted-string
    domain            ->    dot-atom

    word              ->    word-ascii | word-unicode
    word-ascii        ->    atom | quoted-string
    word-unicode      ->    unicode-atom | unicode-qstring
    whitespace        ->    whitespace-ascii | whitespace-unicode


Additional limitations on email addresses:

    1. local-part:
        * Must not be greater than 64 octets

    2. domain:
        * No more than 127 levels
        * Each level no more than 63 octets
        * Texual representation can not exceed 253 characters
        * No level can being or end with -

    3. Maximum mailbox length is len(local-part) + len('@') + len(domain) which
       is 64 + 1 + 253 = 318 characters. Allow 194 characters for a display
       name and the (very generous) limit becomes 512 characters. Allow 1024
       mailboxes and the total limit on a mailbox-list is 524288 characters.
'''

import re
import flanker.addresslib.address

from flanker.addresslib.tokenizer import TokenStream
from flanker.addresslib.tokenizer import LBRACKET
from flanker.addresslib.tokenizer import AT_SYMBOL
from flanker.addresslib.tokenizer import RBRACKET
from flanker.addresslib.tokenizer import DQUOTE
from flanker.addresslib.tokenizer import BAD_DOMAIN
from flanker.addresslib.tokenizer import DELIMITER
from flanker.addresslib.tokenizer import RELAX_ATOM
from flanker.addresslib.tokenizer import WHITESPACE
from flanker.addresslib.tokenizer import UNI_WHITE
from flanker.addresslib.tokenizer import ATOM
from flanker.addresslib.tokenizer import UNI_ATOM
from flanker.addresslib.tokenizer import UNI_QSTR
from flanker.addresslib.tokenizer import DOT_ATOM
from flanker.addresslib.tokenizer import QSTRING
from flanker.addresslib.tokenizer import URL

from flanker.mime.message.headers.encoding import encode_string

from flanker.utils import is_pure_ascii
from flanker.utils import contains_control_chars
from flanker.utils import cleanup_display_name
from flanker.utils import cleanup_email
from flanker.utils import to_utf8


class _AddressParser(object):
    '''
    Do not use _AddressParser directly because it heavily relies on other
    private classes and methods and it's interface is not guarenteed, it
    will change in the future and possibly break your application.

    Instead use the parse() and parse_list() functions in the address.py
    module which will always return a scalar or iterable respectively.
    '''

    def __init__(self, strict=False):
        self.stream = None
        self.strict = strict

    def address_list(self, stream):
        '''
        Extract a mailbox and/or url list from a stream of input, operates in
        strict and relaxed modes.
        '''
        # sanity check
        if not stream:
            raise ParserException('No input provided to parser.')
        if isinstance(stream, str) and not is_pure_ascii(stream):
            raise ParserException('ASCII string contains non-ASCII chars.')

        # to avoid spinning here forever, limit address list length
        if len(stream) > MAX_ADDRESS_LIST_LENGTH:
            raise ParserException('Stream length exceeds maximum allowable ' + \
                'address list length of ' + str(MAX_ADDRESS_LIST_LENGTH) + '.')

        # set stream
        self.stream = TokenStream(stream)

        if self.strict is True:
            return self._address_list_strict()
        return self._address_list_relaxed()

    def address(self, stream):
        '''
        Extract a single address or url from a stream of input, always
        operates in strict mode.
        '''
        # sanity check
        if not stream:
            raise ParserException('No input provided to parser.')
        if isinstance(stream, str) and not is_pure_ascii(stream):
            raise ParserException('ASCII string contains non-ASCII chars.')

        # to avoid spinning here forever, limit mailbox length
        if len(stream) > MAX_ADDRESS_LENGTH:
            raise ParserException('Stream length exceeds maximum allowable ' + \
                'address length of ' + str(MAX_ADDRESS_LENGTH) + '.')

        self.stream = TokenStream(stream)

        addr = self._address()
        if addr:
            # optional whitespace
            self._whitespace()

            # if we hit the end of the stream, we have a valid inbox
            if self.stream.end_of_stream():
                return addr

        return None

    def address_spec(self, stream):
        '''
        Extract a single address spec from a stream of input, always
        operates in strict mode.
        '''
        # sanity check
        if stream is None:
            raise ParserException('No input provided to parser.')
        if isinstance(stream, str) and not is_pure_ascii(stream):
            raise ParserException('ASCII string contains non-ASCII chars.')

        # to avoid spinning here forever, limit mailbox length
        if len(stream) > MAX_ADDRESS_LENGTH:
            raise ParserException('Stream length exceeds maximum allowable ' + \
                'address length of ' + str(MAX_ADDRESS_LENGTH) + '.')

        self.stream = TokenStream(stream)

        addr = self._addr_spec()
        if addr:
            # optional whitespace
            self._whitespace()

            # if we hit the end of the stream, we have a valid inbox
            if self.stream.end_of_stream():
                return addr

        return None


    def _mailbox_post_processing_checks(self, address):
        "Additional post processing checks to ensure mailbox is valid."
        parts = address.split('@')

        # check if local part is less than 256 octets, the actual
        # limit is 64 octets but we quadruple the size here because
        # unsubscribe links are frequently longer
        lpart = parts[0]
        if len(lpart) > 256:
            return False

        # check if the domain is less than 255 octets
        domn = parts[1]
        if len(domn) > 253:
            return False

        # number of labels can not be over 127
        labels = domn.split('.')
        if len(labels) > 127:
            return False

        for label in labels:
            # check the domain doesn't start or end with - and
            # the length of each label is no more than 63 octets
            if BAD_DOMAIN.search(label) or len(label) > 63:
                return False

        return True

    def _address_list_relaxed(self):
        "Grammar: address-list-relaxed -> address { delimiter address }"
        #addrs = []
        addrs = flanker.addresslib.address.AddressList()
        unparsable = []

        # address
        addr = self._address()
        if addr is None:
            # synchronize to the next delimiter (or end of line)
            # append the skipped over text to the unparsable list
            skip = self.stream.synchronize()
            if skip:
                unparsable.append(skip)

            # if no mailbox and end of stream, we were unable
            # return the unparsable stream
            if self.stream.end_of_stream():
                return [], unparsable
        else:
            # if we found a delimiter or end of stream, we have a
            # valid mailbox, add it
            if self.stream.peek(DELIMITER) or self.stream.end_of_stream():
                addrs.append(addr)
            else:
                # otherwise snychornize and add it the unparsable array
                skip = self.stream.synchronize()
                if skip:
                    pre = self.stream.stream[:self.stream.stream.index(skip)]
                    unparsable.append(pre + skip)
                # if we hit the end of the stream, return the results
                if self.stream.end_of_stream():
                    return [], [self.stream.stream]

        while True:
            # delimiter
            dlm = self.stream.get_token(DELIMITER)
            if dlm is None:
                skip = self.stream.synchronize()
                if skip:
                    unparsable.append(skip)
                if self.stream.end_of_stream():
                    break

            # address
            start_pos = self.stream.position
            addr = self._address()
            if addr is None:
                skip = self.stream.synchronize()
                if skip:
                    unparsable.append(skip)

                if self.stream.end_of_stream():
                    break
            else:
                # if we found a delimiter or end of stream, we have a
                # valid mailbox, add it
                if self.stream.peek(DELIMITER) or self.stream.end_of_stream():
                    addrs.append(addr)
                else:
                    # otherwise snychornize and add it the unparsable array
                    skip = self.stream.synchronize()
                    if skip:
                        sskip = self.stream.stream[start_pos:self.stream.position]
                        unparsable.append(sskip)
                    # if we hit the end of the stream, return the results
                    if self.stream.end_of_stream():
                        return addrs, unparsable

        return addrs, unparsable

    def _address_list_strict(self):
        "Grammar: address-list-strict -> address { delimiter address }"
        #addrs = []
        addrs = flanker.addresslib.address.AddressList()

        # address
        addr = self._address()
        if addr is None:
            return addrs
        if self.stream.peek(DELIMITER):
            addrs.append(addr)

        while True:
            # delimiter
            dlm = self.stream.get_token(DELIMITER)
            if dlm is None:
                break

            # address
            addr = self._address()
            if addr is None:
                break
            addrs.append(addr)

        return addrs

    def _address(self):
        "Grammar: address -> name-addr-rfc | name-addr-lax | addr-spec | url"
        start_pos = self.stream.position

        addr = self._name_addr_rfc() or self._name_addr_lax() or \
            self._addr_spec() or self._url()

        # if email address, check that it passes post processing checks
        if addr and isinstance(addr, flanker.addresslib.address.EmailAddress):
            if self._mailbox_post_processing_checks(addr.address) is False:
                # roll back
                self.stream.position = start_pos
                return None

        return addr

    def _url(self):
        "Grammar: url -> url"
        earl = self.stream.get_token(URL)
        if earl is None:
            return None
        return flanker.addresslib.address.UrlAddress(to_utf8(earl))

    def _name_addr_rfc(self):
        "Grammar: name-addr-rfc -> [ display-name-rfc ] angle-addr-rfc"
        start_pos = self.stream.position

        # optional displayname
        dname = self._display_name_rfc()

        aaddr = self._angle_addr_rfc()
        if aaddr is None:
            # roll back
            self.stream.position = start_pos
            return None

        if dname:
            return flanker.addresslib.address.EmailAddress(dname, aaddr)
        return flanker.addresslib.address.EmailAddress(None, aaddr)

    def _display_name_rfc(self):
        "Grammar: display-name-rfc -> [ whitespace ] word { whitespace word }"
        wrds = []

        # optional whitespace
        self._whitespace()

        # word
        wrd = self._word()
        if wrd is None:
            return None
        wrds.append(wrd)

        while True:
            # whitespace
            wtsp = self._whitespace()
            if wtsp is None:
                break
            wrds.append(wtsp)

            # word
            wrd = self._word()
            if wrd is None:
                break
            wrds.append(wrd)

        return cleanup_display_name(''.join(wrds))

    def _angle_addr_rfc(self):
        '''
        Grammar: angle-addr-rfc -> [ whitespace ] < addr-spec > [ whitespace ]"
        '''
        start_pos = self.stream.position

        # optional whitespace
        self._whitespace()

        # left angle bracket
        lbr = self.stream.get_token(LBRACKET)
        if lbr is None:
            # rollback
            self.stream.position = start_pos
            return None

        # addr-spec
        aspec = self._addr_spec(True)
        if aspec is None:
            # rollback
            self.stream.position = start_pos
            return None

        # right angle bracket
        rbr = self.stream.get_token(RBRACKET)
        if rbr is None:
            # rollback
            self.stream.position = start_pos
            return None

         # optional whitespace
        self._whitespace()

        return aspec

    def _name_addr_lax(self):
        "Grammar: name-addr-lax -> [ display-name-lax ] angle-addr-lax"
        start_pos = self.stream.position

        # optional displayname
        dname = self._display_name_lax()

        aaddr = self._angle_addr_lax()
        if aaddr is None:
            # roll back
            self.stream.position = start_pos
            return None

        if dname:
            return flanker.addresslib.address.EmailAddress(dname, aaddr)
        return flanker.addresslib.address.EmailAddress(None, aaddr)

    def _display_name_lax(self):
        '''
        Grammar: display-name-lax ->
            [ whitespace ] word { whitespace word } whitespace"
        '''

        start_pos = self.stream.position
        wrds = []

        # optional whitespace
        self._whitespace()

        # word
        wrd = self._word()
        if wrd is None:
            # roll back
            self.stream.position = start_pos
            return None
        wrds.append(wrd)

        # peek to see if we have a whitespace,
        # if we don't, we have a invalid display-name
        if self.stream.peek(WHITESPACE) is None or \
            self.stream.peek(UNI_WHITE) is None:
            self.stream.position = start_pos
            return None

        while True:
            # whitespace
            wtsp = self._whitespace()
            if wtsp:
                wrds.append(wtsp)

            # if we need to roll back the next word
            start_pos = self.stream.position

            # word
            wrd = self._word()
            if wrd is None:
                self.stream.position = start_pos
                break
            wrds.append(wrd)

            # peek to see if we have a whitespace
            # if we don't pop off the last word break
            if self.stream.peek(WHITESPACE) is None or \
                self.stream.peek(UNI_WHITE) is None:
                # roll back last word
                self.stream.position = start_pos
                wrds.pop()
                break

        return cleanup_display_name(''.join(wrds))

    def _angle_addr_lax(self):
        "Grammar: angle-addr-lax -> addr-spec [ whitespace ]"
        start_pos = self.stream.position

        # addr-spec
        aspec = self._addr_spec(True)
        if aspec is None:
            # rollback
            self.stream.position = start_pos
            return None

        # optional whitespace
        self._whitespace()

        return aspec

    def _addr_spec(self, as_string=False):
        '''
        Grammar: addr-spec -> [ whitespace ] local-part @ domain [ whitespace ]
        '''
        start_pos = self.stream.position

        # optional whitespace
        self._whitespace()

        lpart = self._local_part()
        if lpart is None:
            # rollback
            self.stream.position = start_pos
            return None

        asym = self.stream.get_token(AT_SYMBOL)
        if asym is None:
            # rollback
            self.stream.position = start_pos
            return None

        domn = self._domain()
        if domn is None:
            # rollback
            self.stream.position = start_pos
            return None

        # optional whitespace
        self._whitespace()

        aspec = cleanup_email(''.join([lpart, asym, domn]))
        if as_string:
            return aspec
        return flanker.addresslib.address.EmailAddress(None, aspec)

    def _local_part(self):
        "Grammar: local-part -> dot-atom | quoted-string"
        return self.stream.get_token(DOT_ATOM) or \
            self.stream.get_token(QSTRING)

    def _domain(self):
        "Grammar: domain -> dot-atom"
        return self.stream.get_token(DOT_ATOM)

    def _word(self):
        "Grammar: word -> word-ascii | word-unicode"
        start_pos = self.stream.position

        # ascii word
        ascii_wrd = self._word_ascii()
        if ascii_wrd and not self.stream.peek(UNI_ATOM):
            return ascii_wrd

        # didn't get an ascii word, rollback to try again
        self.stream.position = start_pos

        # unicode word
        return self._word_unicode()

    def _word_ascii(self):
        "Grammar: word-ascii -> atom | qstring"
        wrd = self.stream.get_token(RELAX_ATOM) or self.stream.get_token(QSTRING)
        if wrd and not contains_control_chars(wrd):
            return wrd

        return None

    def _word_unicode(self):
        "Grammar: word-unicode -> unicode-atom | unicode-qstring"
        start_pos = self.stream.position

        # unicode atom
        uwrd = self.stream.get_token(UNI_ATOM)
        if uwrd and isinstance(uwrd, unicode) and not contains_control_chars(uwrd):
            return uwrd

        # unicode qstr
        uwrd = self.stream.get_token(UNI_QSTR, 'qstr')
        if uwrd and isinstance(uwrd, unicode) and not contains_control_chars(uwrd):
            return u'"{0}"'.format(encode_string(None, uwrd))

        # rollback
        self.stream.position = start_pos
        return None


    def _whitespace(self):
        "Grammar: whitespace -> whitespace-ascii | whitespace-unicode"
        return self._whitespace_ascii() or self._whitespace_unicode()

    def _whitespace_ascii(self):
        "Grammar: whitespace-ascii -> whitespace-ascii"
        return self.stream.get_token(WHITESPACE)

    def _whitespace_unicode(self):
        "Grammar: whitespace-unicode -> whitespace-unicode"
        uwhite = self.stream.get_token(UNI_WHITE)
        if uwhite and not is_pure_ascii(uwhite):
            return uwhite
        return None


class ParserException(Exception):
    '''
    Exception raised when the parser encounters some parsing exception.
    '''
    def __init__(self, reason='Unknown parser error.'):
        self.reason = reason

    def __str__(self):
        return self.reason



MAX_ADDRESS_LENGTH = 512
MAX_ADDRESS_NUMBER = 1024
MAX_ADDRESS_LIST_LENGTH = MAX_ADDRESS_LENGTH * MAX_ADDRESS_NUMBER

########NEW FILE########
__FILENAME__ = aol
# coding:utf-8

'''
    Email address validation plugin for aol.com email addresses.

    Notes:

        3-32 characters
        must start with letter
        must end with letter or number
        must use letters, numbers, dot (.) or underscores (_)
        no consecutive dot (.) or underscores (_)
        no dot-underscore (._) or underscore-dot (_.)
        case is ignored

    Grammar:

        local-part  ->  alpha { [ dot | underscore ] ( alpha | num ) }

'''
import re
from flanker.addresslib.tokenizer import TokenStream

ALPHA      = re.compile(r'''
                        [A-Za-z]+
                        ''', re.MULTILINE | re.VERBOSE)

NUMERIC    = re.compile(r'''
                        [0-9]+
                        ''', re.MULTILINE | re.VERBOSE)

ALPHANUM   = re.compile(r'''
                        [A-Za-z0-9]+
                        ''', re.MULTILINE | re.VERBOSE)

DOT        = re.compile(r'''
                        \.
                        ''', re.MULTILINE | re.VERBOSE)

UNDERSCORE = re.compile(r'''
                        \_
                        ''', re.MULTILINE | re.VERBOSE)


def validate(localpart):
    # check string exists and not empty
    if not localpart:
        return False

    # length check
    l = len(localpart)
    if l < 3 or l > 32:
        return False

    # must start with letter
    if ALPHA.match(localpart[0]) is None:
        return False

    # must end with letter or digit
    if ALPHANUM.match(localpart[-1]) is None:
        return False

    # grammar check
    return _validate(localpart)


def _validate(localpart):
    "Grammar: local-part -> alpha  { [ dot | underscore ] ( alpha | num ) }"
    stream = TokenStream(localpart)

    # local-part must being with alpha
    alpa = stream.get_token(ALPHA)
    if alpa is None:
        return False

    while True:
        # optional dot or underscore token
        stream.get_token(DOT) or stream.get_token(UNDERSCORE)

        # alpha or numeric
        alpanum = stream.get_token(ALPHA) or stream.get_token(NUMERIC)
        if alpanum is None:
            break

    # alpha or numeric must be end of stream
    if not stream.end_of_stream():
        return False

    return True

########NEW FILE########
__FILENAME__ = gmail
# coding:utf-8

'''
    Email address validation plugin for gmail.com email addresses.

    Notes:

        must be between 6-30 characters
        must start with letter or number
        must end with letter or number
        must use letters, numbers, or dots (.)
        all dots (.) are ignored
        case is ignored
        plus (+) is allowed, everything after + is ignored
      1. All characters prefixing the plus symbol (+) and stripping all dot
           symbol (.) must be between 6-30 characters.


    Grammar:

        local-part      ->      main-part [ tags ]
        main-part       ->      gmail-prefix gmail-root gmail-suffix
        tags            ->      { + [ gmail-root ] }
        gmail-prefix    ->      alpha | num
        gmail-root      ->      alpha | num | dot
        gmail-suffix    ->      alpha | num
'''
import re
from flanker.addresslib.tokenizer import TokenStream
from flanker.addresslib.tokenizer import ATOM


GMAIL_BASE = re.compile(r'''
                        [A-Za-z0-9\.]+
                        ''', re.MULTILINE | re.VERBOSE)

ALPHANUM   = re.compile(r'''
                        [A-Za-z0-9]+
                        ''', re.MULTILINE | re.VERBOSE)

PLUS       = re.compile(r'''
                        [\+]+
                        ''', re.MULTILINE | re.VERBOSE)


def validate(localpart):
    # check string exists and not empty
    if not localpart:
        return False

    slpart = localpart.replace('.', '')
    lparts = slpart.split('+')
    real_localpart = lparts[0]

    # length check
    l = len(real_localpart)
    if l < 6 or l > 30:
        return False

   # must start with letter or num
    if ALPHANUM.match(real_localpart[0]) is None:
        return False

    # must end with letter or num
    if ALPHANUM.match(real_localpart[-1]) is None:
        return False

    # grammar check
    return _validate(real_localpart)


def _validate(localpart):
    stream = TokenStream(localpart)

    # get the gmail base (alpha, num, or dot)
    mpart = stream.get_token(GMAIL_BASE)
    if mpart is None:
        return False

    # optional tags
    tgs = _tags(stream)

    if not stream.end_of_stream():
        return False

    return True


def _tags(stream):
    while True:
        # plus sign
        pls = stream.get_token(PLUS)

        # optional atom
        if pls:
            stream.get_token(ATOM)
        else:
            break

    return True

########NEW FILE########
__FILENAME__ = google
# coding:utf-8

'''
    Email address validation plugin for Google Apps email addresses.

    Notes:

        must be between 1-64 characters
        must use letters, numbers, dash (-), underscore (_), apostrophes ('), and dots (.)
        if one character, must be alphanum, underscore (_) or apostrophes (')
        otherwise must start with: alphanum, underscore (_), dash (-), or apostrophes(')
        otherwise must end with: alphanum, underscore(_), dash(-), or apostrophes(')
        plus (+) is allowed, everything after + is ignored
        case is ignored

    Grammar:

        local-part      ->      main-part [ tags ]
        main-part       ->      google-prefix google-root google-suffix
        tags            ->      { + [ atom ] }
        google-prefix    ->     alphanum | underscore | dash | apostrophe
        google-root      ->     alphanum | underscore | dash | apostrophe | dots
        google-suffix    ->     alphanum | underscore | dash | apostrophe

    Other limitations:

        1. All characters prefixing the plus symbol (+) must be between 1-64 characters.

'''
import re
from flanker.addresslib.tokenizer import TokenStream
from flanker.addresslib.tokenizer import ATOM


GOOGLE_BASE  = re.compile(r'''
                        [A-Za-z0-9_\-'\.]+
                        ''', re.MULTILINE | re.VERBOSE)

ALPHANUM    = re.compile(r'''
                        [A-Za-z0-9]+
                        ''', re.MULTILINE | re.VERBOSE)

UNDERSCORE  = re.compile(r'''
                        [_]+
                        ''', re.MULTILINE | re.VERBOSE)

APOSTROPHES = re.compile(r'''
                        [']+
                        ''', re.MULTILINE | re.VERBOSE)

DASH        = re.compile(r'''
                        [-]+
                        ''', re.MULTILINE | re.VERBOSE)

DOTS        = re.compile(r'''
                        [.]+
                        ''', re.MULTILINE | re.VERBOSE)

PLUS        = re.compile(r'''
                         [\+]+
                         ''', re.MULTILINE | re.VERBOSE)


def validate(localpart):
    # check string exists and not empty
    if not localpart:
        return False

    lparts = localpart.split('+')
    real_localpart = lparts[0]

    # length check
    l = len(real_localpart)
    if l < 0 or l > 64:
        return False

    # if only one character, must be alphanum, underscore (_), or apostrophe (')
    if len(localpart) == 1 or l == 1:
        if ALPHANUM.match(localpart) or UNDERSCORE.match(localpart) or \
            APOSTROPHES.match(localpart):
            return True
        return False

    # must start with: alphanum, underscore (_), dash (-), or apostrophes(')
    if len(real_localpart) > 0:
        if not ALPHANUM.match(real_localpart[0]) and not UNDERSCORE.match(real_localpart[0]) \
            and not DASH.match(real_localpart[0]) and not APOSTROPHES.match(real_localpart[0]):
            return False
    else:
        return False

    # must end with: alphanum, underscore(_), dash(-), or apostrophes(')
    if not ALPHANUM.match(real_localpart[-1]) and not UNDERSCORE.match(real_localpart[-1]) \
        and not DASH.match(real_localpart[-1]) and not APOSTROPHES.match(real_localpart[-1]):
        return False

    # grammar check
    return _validate(real_localpart)

def _validate(localpart):
    stream = TokenStream(localpart)

    # get the google base
    mpart = stream.get_token(GOOGLE_BASE)
    if mpart is None:
        return False

    # optional tags
    tgs = _tags(stream)

    if not stream.end_of_stream():
        return False

    return True


def _tags(stream):
    while True:
        # plus sign
        pls = stream.get_token(PLUS)

        # optional atom
        if pls:
            stream.get_token(ATOM)
        else:
            break

    return True

########NEW FILE########
__FILENAME__ = hotmail
# coding:utf-8

'''
    Email address validation plugin for hotmail.com email addresses.

    Notes:

        1-64 characters
        must start with letter
        must end with letter, number, hyphen (-), or underscore (_)
        must use letters, numbers, periods (.), hypens (-), or underscores (_)
        only one plus (+) is allowed
        case is ignored

    Grammar:

        local-part      ->  main-part [ tags ]
        main-part       ->  hotmail-prefix hotmail-root hotmail-suffix
        hotmail-prefix  ->  alpha
        hotmail-root    ->  alpha | number | period | hyphen | underscore
        hotmail-suffix  ->  alpha | number | hyphen | underscore
        tags            ->  + [ hotmail-root ]


    Other limitations:

        1. Only one consecutive period (.) is allowed in the local-part
        2. Length of local-part must be no more than 64 characters, and no
           less than 1 characters.

'''
import re
from flanker.addresslib.tokenizer import TokenStream

HOTMAIL_PREFIX  = re.compile(r'''
                            [A-Za-z]+
                            ''', re.MULTILINE | re.VERBOSE)

HOTMAIL_BASE    = re.compile(r'''
                            [A-Za-z0-9\.\-\_]+
                            ''', re.MULTILINE | re.VERBOSE)

HOTMAIL_SUFFIX  = re.compile(r'''
                            [A-Za-z0-9\-\_]+
                            ''', re.MULTILINE | re.VERBOSE)

PLUS            = re.compile(r'''
                            \+
                            ''', re.MULTILINE | re.VERBOSE)

PERIODS         = re.compile(r'''
                            \.{2,}
                            ''', re.MULTILINE | re.VERBOSE)


def validate(localpart):
    # check string exists and not empty
    if not localpart:
        return False

    # remove tag if it exists
    lparts = localpart.split('+')
    real_localpart = lparts[0]

    # length check
    l = len(real_localpart)
    if l < 1 or l > 64:
        return False

    # start can only be alpha
    if HOTMAIL_PREFIX.match(real_localpart[0]) is None:
        return False

    # can not end with dot
    if HOTMAIL_SUFFIX.match(real_localpart[-1]) is None:
        return False

    # no more than one plus (+)
    if localpart.count('+') > 1:
        return False

    # no consecutive periods (..)
    if PERIODS.search(localpart):
        return False

    # grammar check
    retval = _validate(real_localpart)
    return retval


def _validate(localpart):
    stream = TokenStream(localpart)

    # get the hotmail base
    mpart = stream.get_token(HOTMAIL_BASE)
    if mpart is None:
        return False

    # optional tags
    tgs = _tags(stream)

    if not stream.end_of_stream():
        return False

    return True


def _tags(stream):
    pls = stream.get_token(PLUS)
    bse = stream.get_token(HOTMAIL_BASE)

    if bse and pls is None:
        return False

    return True

########NEW FILE########
__FILENAME__ = icloud
# coding:utf-8

'''
    Email address validation plugin for icloud.com email addresses.

    Notes:

        3-20 characters
        must start with letter
        must end with letter or number
        must use letters, numbers, dot (.) or underscores (_)
        no consecutive dot (.) or underscores (_)
        case is ignored
        any number of plus (+) are allowed if followed by at least one alphanum

    Grammar:

        local-part -> icloud-prefix { [ dot | underscore ] icloud-root }
            icloud-suffix
        icloud-prefix = alpha
        icloud-root = alpha | num | plus
        icloud-suffix = alpha | num

    Other limitations:

        * Length of local-part must be no more than 20 characters, and no
          less than 3 characters.

    Open questions:

        * Are dot-underscore (._) or underscore-dot (_.) allowed?
        * Is name.@icloud.com allowed?

'''
import re
from flanker.addresslib.tokenizer import TokenStream

ALPHA          = re.compile(r'''
                            [A-Za-z]+
                            ''', re.MULTILINE | re.VERBOSE)

ALPHANUM      = re.compile(r'''
                           [A-Za-z0-9]+
                           ''', re.MULTILINE | re.VERBOSE)


ICLOUD_PREFIX = re.compile(r'''
                           [A-Za-z]+
                           ''', re.MULTILINE | re.VERBOSE)

ICLOUD_BASE   = re.compile(r'''
                           [A-Za-z0-9\+]+
                           ''', re.MULTILINE | re.VERBOSE)

DOT           = re.compile(r'''
                           \.
                           ''', re.MULTILINE | re.VERBOSE)

UNDERSCORE    = re.compile(r'''
                           \_
                           ''', re.MULTILINE | re.VERBOSE)


def validate(localpart):
    # check string exists and not empty
    if not localpart:
        return False

    lparts = localpart.split('+')
    real_localpart = lparts[0]

    # length check
    l = len(real_localpart)
    if l < 3 or l > 20:
        return False

    # can not end with +
    if localpart[-1] == '+':
        return False

    # must start with letter
    if ALPHA.match(real_localpart[0]) is None:
        return False

    # must end with letter or digit
    if ALPHANUM.match(real_localpart[-1]) is None:
        return False

    # check grammar
    return _validate(real_localpart)


def _validate(localpart):
    stream = TokenStream(localpart)

    # localpart must start with alpha
    alpa = stream.get_token(ICLOUD_PREFIX)
    if alpa is None:
        return False

    while True:
        # optional dot or underscore
        stream.get_token(DOT) or stream.get_token(UNDERSCORE)

        base = stream.get_token(ICLOUD_BASE)
        if base is None:
            break

    if not stream.end_of_stream():
        return False

    return True

########NEW FILE########
__FILENAME__ = yahoo
# coding:utf-8

'''
    Email address validation plugin for yahoo.com email addresses.

    Notes for primary e-mail:

        4-32 characters
        must start with letter
        must end with letter or number
        must use letters, numbers, underscores (_)
        only one dot (.) allowed
        no consecutive dot (.) or underscore (_)
        no dot-underscore (._) or underscore-dot (_.)
        case is ignored
        tags not supported

    Grammar:

        local-part  ->  alpha  { [ dot | underscore ] ( alpha | num ) }

    Other limitations:

        1. No more than a single dot (.) is allowed in the local-part
        2. Length of local-part must be no more than 32 characters, and no
           less than 4 characters.

    Notes for disposable e-mails using "AddressGuard":

        example: base-keyword@yahoo.com

        base and keyword may each be up to 32 characters
        base may contain letters, numbers, underscores
        base must start with a letter
        keyword may contain letters and numbers
        a single hyphen (-) connects the base and keyword

    Grammar:

        local-part  ->  alpha { [ alpha | num | underscore ] } hyphen { [ alpha | num ] }

'''

import re
from flanker.addresslib.tokenizer import TokenStream

ALPHA      = re.compile(r'''
                        [A-Za-z]+
                        ''', re.MULTILINE | re.VERBOSE)

NUMERIC    = re.compile(r'''
                        [0-9]+
                        ''', re.MULTILINE | re.VERBOSE)

ALPHANUM   = re.compile(r'''
                        [A-Za-z0-9]+
                        ''', re.MULTILINE | re.VERBOSE)

DOT        = re.compile(r'''
                        \.
                        ''', re.MULTILINE | re.VERBOSE)

UNDERSCORE = re.compile(r'''
                        \_
                        ''', re.MULTILINE | re.VERBOSE)

HYPHEN     = re.compile(r'''
                        \-
                        ''', re.MULTILINE | re.VERBOSE)


def validate(localpart):
    # check string exists and not empty
    if not localpart:
        return False

    # must start with letter
    if len(localpart) < 1 or ALPHA.match(localpart[0]) is None:
        return False

    # must end with letter or digit
    if ALPHANUM.match(localpart[-1]) is None:
        return False

    # only disposable addresses may contain hyphens
    if HYPHEN.search(localpart):
        return _validate_disposable(localpart)

    # otherwise, normal validation
    return _validate_primary(localpart)


def _validate_primary(localpart):
    # length check
    l = len(localpart)
    if l < 4 or l > 32:
        return False

    # no more than one dot (.)
    if localpart.count('.') > 1:
        return False

    # Grammar: local-part -> alpha  { [ dot | underscore ] ( alpha | num ) }"
    stream = TokenStream(localpart)

    # local-part must being with alpha
    alpa = stream.get_token(ALPHA)
    if alpa is None:
        return False

    while True:
        # optional dot or underscore token
        stream.get_token(DOT) or stream.get_token(UNDERSCORE)

        # alpha or numeric
        alpanum = stream.get_token(ALPHA) or stream.get_token(NUMERIC)
        if alpanum is None:
            break

    # alpha or numeric must be end of stream
    if not stream.end_of_stream():
        return False

    return True

def _validate_disposable(localpart):
    # length check (base + hyphen + keyword)
    l = len(localpart)
    if l < 3 or l > 65:
        return False

    # single hyphen
    if localpart.count('-') != 1:
        return False

    # base and keyword length limit
    parts = localpart.split('-')
    for part in parts:
        l = len(part)
        if l < 1 or l > 32:
            return False

    # Grammar: local-part  ->  alpha { [ alpha | num | underscore ] } hyphen { [ alpha | num ] }
    stream = TokenStream(localpart)

    # must being with alpha
    begin = stream.get_token(ALPHA)
    if begin is None:
        return False

    while True:
        # alpha, num, underscore
        base = stream.get_token(ALPHANUM) or stream.get_token(UNDERSCORE)

        if base is None:
            break

    # hyphen
    hyphen = stream.get_token(HYPHEN)
    if hyphen is None:
        return False

    # keyword must be alpha, num
    stream.get_token(ALPHANUM)

    if not stream.end_of_stream():
        return False

    return True

########NEW FILE########
__FILENAME__ = tokenizer
# coding:utf-8

'''
TokenStream represents a stream of tokens that a parser will consume.
TokenStream can be used to consume tokens, peek ahead, and synchonize to a
delimiter token. The tokens that the token stream operates on are either
compiled regular expressions or strings.
'''

import re

LBRACKET   = '<'
AT_SYMBOL  = '@'
RBRACKET   = '>'
DQUOTE     = '"'

BAD_DOMAIN = re.compile(r'''                                    # start or end
                        ^-|-$                                   # with -
                        ''', re.MULTILINE | re.VERBOSE)

DELIMITER  = re.compile(r'''
                        [,;][,;\s]*                             # delimiter
                        ''', re.MULTILINE | re.VERBOSE)

WHITESPACE = re.compile(r'''
                        (\ |\t)+                                # whitespace
                        ''', re.MULTILINE | re.VERBOSE)

UNI_WHITE  = re.compile(ur'''
                        [
                            \u0020\u00a0\u1680\u180e
                            \u2000-\u200a
                            \u2028\u202f\u205f\u3000
                        ]*
                        ''', re.MULTILINE | re.VERBOSE | re.UNICODE)

RELAX_ATOM = re.compile(r'''
                        ([^\s<>;,"]+)
                        ''', re.MULTILINE | re.VERBOSE)

ATOM       = re.compile(r'''
                        [A-Za-z0-9!#$%&'*+\-/=?^_`{|}~]+        # atext
                        ''', re.MULTILINE | re.VERBOSE)

DOT_ATOM   = re.compile(r'''
                        [A-Za-z0-9!#$%&'*+\-/=?^_`{|}~]+        # atext
                        (\.[A-Za-z0-9!#$%&'*+\-/=?^_`{|}~]+)*   # (dot atext)*
                        ''', re.MULTILINE | re.VERBOSE)

UNI_ATOM = re.compile(ur'''
                        ([^\s<>;,"]+)
                        ''', re.MULTILINE | re.VERBOSE | re.UNICODE)

UNI_QSTR   = re.compile(ur'''
                        "
                        (?P<qstr>([^"]+))
                        "
                        ''', re.MULTILINE | re.VERBOSE | re.UNICODE)

QSTRING    = re.compile(r'''
                        "                                       # dquote
                        (\s*                                    # whitespace
                        ([\x21\x23-\x5b\x5d-\x7e]               # qtext
                        |                                       # or
                        \\[\x21-\x7e\t\ ]))*                    # quoted-pair
                        \s*                                     # whitespace
                        "                                       # dquote
                        ''', re.MULTILINE | re.VERBOSE)

URL        = re.compile(r'''
                        (?:http|https)://
                        [^\s<>{}|\^~\[\]`;,]+
                        ''', re.MULTILINE | re.VERBOSE | re.UNICODE)

class TokenStream(object):
    '''
    Represents the stream of tokens that the parser will consume. The token
    stream can be used to consume tokens, peek ahead, and synchonize to a
    delimiter token.

    When the strem reaches its end, the position is placed
    at one plus the position of the last token.
    '''
    def __init__(self, stream):
        self.position = 0
        self.stream = stream

    def get_token(self, token, ngroup=None):
        '''
        Get the next token from the stream and advance the stream. Token can
        be either a compiled regex or a string.
        '''
        # match single character
        if isinstance(token, basestring) and len(token) == 1:
            if self.peek() == token:
                self.position += 1
                return token
            return None

        # match a pattern
        match = token.match(self.stream, self.position)
        if match:
            advance = match.end() - match.start()
            self.position += advance

            # if we are asking for a named capture, return jus that
            if ngroup:
                return match.group(ngroup)
            # otherwise return the entire capture
            return match.group()

        return None

    def end_of_stream(self):
        '''
        Check if the end of the stream has been reached, if it has, returns
        True, otherwise false.
        '''
        if self.position >= len(self.stream):
            return True
        return False

    def synchronize(self):
        '''
        Advances the stream to synchronizes to the delimiter token. Used primarily
        in relaxed mode parsing.
        '''
        start_pos = self.position
        end_pos = len(self.stream)

        match = DELIMITER.search(self.stream, self.position)
        if match:
            self.position = match.start()
            end_pos = match.start()
        else:
            self.position = end_pos

        skip = self.stream[start_pos:end_pos]
        if skip.strip() == '':
            return None

        return skip

    def peek(self, token=None):
        '''
        Peek at the stream to see what the next token is or peek for a
        specific token.
        '''
        # peek at whats next in the stream
        if token is None:
            if self.position < len(self.stream):
                return self.stream[self.position]
            else:
                return None
        # peek for a specific token
        else:
            match = token.match(self.stream, self.position)
            if match:
                return self.stream[match.start():match.end()]
            return None

########NEW FILE########
__FILENAME__ = validate
# coding:utf-8

'''
Validation module that that supports alternate spelling suggestions for
domains, MX record lookup and query, as well as custom local-part grammar for
large ESPs.

This module should probably not be used directly, use
flanker.addresslib.address unles you are building ontop of the library.

Public Functions in flanker.addresslib.validate module:

    * suggest_alternate(addr_spec)

      Given an addr-spec, suggests an alternate if a typo is found. Returns
      None if no alternate is suggested.

    * preparse_address(addr_spec)

      Preparses email addresses. Used to handle odd behavior by ESPs.

    * plugin_for_esp(mail_exchanger)

      Looks up the custom grammar plugin for a given ESP via the mail
      exchanger.

    * mail_exchanger_lookup(domain)

      Looks up the mail exchanger for a given domain.

    * connect_to_mail_exchanger(mx_hosts)

      Attempts to connect to a given mail exchanger to see if it exists.
'''

import re
import redis
import socket
import time
import flanker.addresslib

from flanker.addresslib import corrector
from flanker.utils import metrics_wrapper


def suggest_alternate(addr_spec):
    '''
    Given an addr-spec, suggests a alternate addr-spec if common spelling
    mistakes are detected in the domain portion.

    Returns an suggested alternate if one is found. Returns None if the
    address is invalid or no suggestions were found.

    Examples:
        >>> print validate.suggest_alternate('john@gmail.com')
        None
        >>> validate.suggest_alternate('john@gmail..com')
        'john@gmail.com'
    '''
    # sanity check
    if addr_spec is None:
        return None

    # preparse address into its parts and perform any ESP specific preparsing
    addr_parts = preparse_address(addr_spec)
    if addr_parts is None:
        return None

    # correct spelling
    sugg_domain = corrector.suggest(addr_parts[-1])

    # if suggested domain is the same as the passed in domain
    # don't return any suggestions
    if sugg_domain == addr_parts[-1]:
        return None

    return '@'.join([addr_parts[0], sugg_domain])


def preparse_address(addr_spec):
    '''
    Preparses email addresses. Used to handle odd behavior by ESPs.
    '''
    # sanity check, ensure we have both local-part and domain
    parts = addr_spec.split('@')
    if len(parts) < 2:
        return None

    # if we add more esp specific checks, they should be done
    # with a dns lookup not string matching domain
    if parts[1] == 'gmail.com' or parts[1] == 'googlemail.com':
        parts[0] = parts[0].replace('.', '')

    return parts


def plugin_for_esp(mail_exchanger):
    '''
    Checks if custom grammar exists for a particular mail exchanger. If
    a grammar is found, the plugin to validate an address for that particular
    email service provider is returned, otherwise None is returned.

    If you are adding the grammar for a email service provider, add the module
    to the flanker.addresslib.plugins directory then update the
    flanker.addresslib package to add it to the known list of custom grammars.
    '''
    for grammar in flanker.addresslib.CUSTOM_GRAMMAR_LIST:
        if grammar[0].match(mail_exchanger):
            return grammar[1]

    return None


@metrics_wrapper()
def mail_exchanger_lookup(domain, metrics=False):
    '''
    Looks up the mail exchanger for a domain. If MX records exist they will
    be returned, if not it will attempt to fallback to A records, if neither
    exist None will be returned.
    '''
    mtimes = {'mx_lookup': 0, 'dns_lookup': 0, 'mx_conn': 0}
    mx_cache = flanker.addresslib.mx_cache

    # look in cache
    bstart = time.time()
    in_cache, cache_value = lookup_exchanger_in_cache(domain)
    mtimes['mx_lookup'] = time.time() - bstart
    if in_cache:
        return cache_value, mtimes

    # dns lookup on domain
    bstart = time.time()
    mx_hosts = lookup_domain(domain)
    mtimes['dns_lookup'] = time.time() - bstart
    if mx_hosts is None:
        # try one more time
        bstart = time.time()
        mx_hosts = lookup_domain(domain)
        mtimes['dns_lookup'] += time.time() - bstart
        if mx_hosts is None:
            mx_cache[domain] = False
            return None, mtimes

    # test connecting to the mx exchanger
    bstart = time.time()
    mail_exchanger = connect_to_mail_exchanger(mx_hosts)
    mtimes['mx_conn'] = time.time() - bstart
    if mail_exchanger is None:
        mx_cache[domain] = False
        return None, mtimes

    # valid mx records, connected to mail exchanger, return True
    mx_cache[domain] = mail_exchanger
    return mail_exchanger, mtimes


def lookup_exchanger_in_cache(domain):
    '''
    Uses a cache to store the results of the mail exchanger lookup to speed
    up lookup times. The default is redis, but this can be overidden by your
    own cache as long as it conforms to the same interface as that of a dict.
    See the implimentation of the redis cache in the flanker.addresslib.driver
    package for more details if you wish to implement your own cache.
    '''
    mx_cache = flanker.addresslib.mx_cache

    lookup = mx_cache[domain]
    if lookup is None:
        return (False, None)

    if lookup == 'False':
        return (True, None)
    else:
        return (True, lookup)


def lookup_domain(domain):
    '''
    The dnspython package is used for dns lookups. The dnspython package uses
    the dns server specified by your operating system. Just like the cache,
    this can be overridden by your own dns lookup method of choice as long
    as it conforms to the same interface as that of a dict. See the the
    implimentation of the dnspython lookup in the flanker.addresslib.driver
    package for more details.
    '''

    dns_lookup = flanker.addresslib.dns_lookup

    fqdn = domain if domain[-1] == '.' else ''.join([domain, '.'])
    mx_hosts = dns_lookup[fqdn]

    if len(mx_hosts) == 0:
        return None
    return mx_hosts


def connect_to_mail_exchanger(mx_hosts):
    '''
    Given a list of MX hosts, attempts to connect to at least one on port 25.
    Returns the mail exchanger it was able to connect to or None.
    '''
    for host in mx_hosts:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            s.connect((host, 25))
            s.close()
            return host
        except:
            continue

    return None


ONE_WEEK = 604800

########NEW FILE########
__FILENAME__ = bounce
import regex as re
from collections import deque
from contextlib import closing
from cStringIO import StringIO
from flanker.mime.message.headers.parsing import parse_stream
from flanker.mime.message.headers import MimeHeaders


def detect(message):
    headers = collect(message)
    return Result(
        score=len(headers) / float(len(HEADERS)),
        status=get_status(headers),
        notification=get_notification(message),
        diagnostic_code=headers.get('Diagnostic-Code'))


def collect(message):
    collected = deque()
    for p in message.walk(with_self=True):
        for h in HEADERS:
            if h in p.headers:
                collected.append((h, p.headers[h]))
        if p.content_type.is_delivery_status():
            collected += collect_from_status(p.body)
    return MimeHeaders(collected)


def collect_from_status(body):
    out = deque()
    with closing(StringIO(body)) as stream:
        for i in xrange(3):
            out += parse_stream(stream)
    return out


def get_status(headers):
    for v in headers.getall('Status'):
        if RE_STATUS.match(v.strip()):
            return v


def get_notification(message):
    for part in message.walk():
        if part.headers.get('Content-Description',
                            '').lower() == 'notification':
            return part.body


HEADERS = ('Action',
           'Content-Description',
           'Diagnostic-Code',
           'Final-Recipient',
           'Received',
           'Remote-Mta',
           'Reporting-Mta',
           'Status')

RE_STATUS = re.compile(r'\d\.\d+\.\d+', re.IGNORECASE)


class Result(object):
    def __init__(self, score, status, notification, diagnostic_code):
        self.score = score
        self.status = status
        self.notification = notification
        self.diagnostic_code = diagnostic_code

########NEW FILE########
__FILENAME__ = create
""" This package is a set of utilities and methods for building mime messages """

import uuid
from flanker.mime.message import ContentType, utils
from flanker.mime.message.part import MimePart, Body, Part, adjust_content_type
from flanker.mime.message import scanner
from flanker.mime.message.headers.parametrized import fix_content_type
from flanker.mime.message.headers import WithParams


def multipart(subtype):
    return MimePart(
        container=Part(
            ContentType(
                "multipart", subtype, {"boundary": uuid.uuid4().hex})),
        is_root=True)


def message_container(message):
    part = MimePart(
        container=Part(ContentType("message", "rfc822")),
        enclosed=message)
    message.set_root(False)
    return part


def text(subtype, body, charset=None, disposition=None, filename=None):
    return MimePart(
        container=Body(
            content_type=ContentType("text", subtype),
            body=body,
            charset=charset,
            disposition=disposition,
            filename=filename),
        is_root=True)


def binary(maintype, subtype, body, filename=None,
           disposition=None, charset=None):
    return MimePart(
        container=Body(
            content_type=ContentType(maintype, subtype),
            body=body,
            charset=charset,
            disposition=disposition,
            filename=filename),
        is_root=True)


def attachment(content_type, body, filename=None,
               disposition=None, charset=None):
    """Smarter method to build attachments that detects the proper content type
    and form of the message based on content type string, body and filename
    of the attachment
    """

    # fix and sanitize content type string and get main and sub parts:
    main, sub = fix_content_type(
        content_type, default=('application', 'octet-stream'))

    # adjust content type based on body or filename if it's not too accurate
    content_type = adjust_content_type(
        ContentType(main, sub), body, filename)

    if content_type.main == 'message':
        message = message_container(from_string(body))
        message.headers['Content-Disposition'] = WithParams(disposition)
        return message
    else:
        return binary(
            content_type.main,
            content_type.sub,
            body, filename,
            disposition,
            charset)


def from_string(string):
    return scanner.scan(string)


def from_python(message):
    return from_string(
        utils.python_message_to_string(message))


def from_message(message):
    return from_string(message.to_string())

########NEW FILE########
__FILENAME__ = charsets
import regex as re
from flanker.mime.message import errors
from flanker.utils import to_utf8, to_unicode


def convert_to_unicode(charset, value):
    #in case of unicode we have nothing to do
    if isinstance(value, unicode):
        return value

    charset = _translate_charset(charset)

    return to_unicode(value, charset=charset)


def _translate_charset(charset):
    """Translates crappy charset into Python analogue (if supported).

    Otherwise returns unmodified.
    """
    # ev: (ticket #2819)
    if "sjis" in charset.lower():
        return 'shift_jis'

    # cp874 looks to be an alias for windows-874
    if "windows-874" == charset.lower():
        return "cp874"

    if 'koi8-r' in charset.lower():
        return 'koi8_r'

    if 'utf-8' in charset.lower() or charset.lower() == 'x-unknown':
        return 'utf-8'

    return charset

########NEW FILE########
__FILENAME__ = errors
class MimeError(Exception):
    pass


class DecodingError(MimeError):
    """Thrown when there is an encoding error."""
    pass


class EncodingError(MimeError):
    """Thrown when there is an decoding error."""
    pass

########NEW FILE########
__FILENAME__ = create
import email
from flanker.mime.message.fallback.part import FallbackMimePart


def from_string(string):
    return FallbackMimePart(email.message_from_string(string))


def from_python(message):
    return FallbackMimePart(message)

########NEW FILE########
__FILENAME__ = part
import logging
import email
from flanker.mime.message.scanner import ContentType
from flanker.mime.message import utils, charsets, headers
from flanker.mime.message.headers import parametrized

log = logging.getLogger(__name__)

class FallbackMimePart(object):

    def __init__(self, python_message):
        self.m = python_message
        self._is_root = False

    def is_body(self):
        return (self.content_type.format_type == 'text' or
                 self.content_type.format_type == 'message')

    def is_root(self):
        return self._is_root

    def set_root(self, value):
        self._is_root = value

    def append(self, message):
        self.m.attach(
            FallbackMimePart(
                email.message_from_string(
                    message.to_string())))

    def remove_headers(self, *headers):
        for header in headers:
            if header in self.headers:
                del self.headers[header]

    def is_bounce(self):
        return False

    @property
    def bounce(self):
        return None

    def to_python_message(self):
        return self.m

    def get_attached_message(self):
        """
        Returns attached message if found, None otherwize
        """
        try:
            for part in self.walk(with_self=True):
                if part.content_type == 'message/rfc822':
                    for p in part.walk():
                        return p
        except Exception:
            log.exception("Failed to get attached message")
            return None

    def walk(self, with_self=False, skip_enclosed=False):
        if with_self:
            yield self

        if self.content_type.is_multipart():
            for p in self.parts:
                yield p
                for x in p.walk(False, skip_enclosed=skip_enclosed):
                    yield x

        elif self.content_type.is_message_container() and not skip_enclosed:
            yield self.enclosed
            for p in self.enclosed.walk(False):
                yield p

    @property
    def content_type(self):
        return ContentType(
            self.m.get_content_maintype(),
            self.m.get_content_subtype(),
            dict(self.m.get_params() or []))

    @property
    def charset(self):
        return self.content_type.params.get('charset', 'ascii')

    @property
    def headers(self):
        return FallbackHeaders(self.m)

    @property
    def body(self):
        if not self.m.is_multipart():
            return charsets.convert_to_unicode(
                self.charset,
                self.m.get_payload(decode=True))

    @body.setter
    def body(self, value):
        if not self.m.is_multipart():
            return self.m.set_payload(
                value.encode('utf-8'), 'utf-8')

    @property
    def parts(self):
        if self.m.is_multipart():
            return [FallbackMimePart(p) for p in self.m.get_payload() if p]
        else:
            return []

    @property
    def enclosed(self):
        if self.content_type == 'message/rfc822':
            return FallbackMimePart(self.m.get_payload()[0])

    @property
    def size(self):
        if not self.m.is_multipart():
            return len(self.m.get_payload(decode=False))
        else:
            return sum(p.size for p in self.parts)

    @property
    def content_encoding(self):
        return self.m.get('Content-Transfer-Encoding')

    @content_encoding.setter
    def content_encoding(self, value):
        pass

    @property
    def content_disposition(self):
        try:
            return parametrized.decode(
                self.m.get('Content-Disposition', ''))
        except:
            return (None, {})

    def to_string(self):
        return utils.python_message_to_string(self.m)

    def to_stream(self, out):
        out.write(self.to_string())

    def is_attachment(self):
        return self.content_disposition[0] == 'attachment'

    def is_inline(self):
        return self.content_disposition[0] == 'inline'

    def is_delivery_notification(self):
        ctype = self.content_type
        return  ctype == 'multipart/report'\
            and ctype.params.get('report-type') == 'delivery-status'

    def __str__(self):
        return "FallbackMimePart"

def try_decode(key, value):
    if isinstance(value, (tuple, list)):
        return value
    elif isinstance(value, str):
        try:
            return headers.parse_header_value(key, value)
        except Exception:
            return unicode(value, 'utf-8', 'ignore')
    elif isinstance(value, unicode):
        return value
    else:
        return ""

class FallbackHeaders(object):

    def __init__(self, message):
        self.m = message

    def __getitem__(self, key):
        return try_decode(key, self.m.get(key))

    def __len__(self):
        return len(self.m._headers)

    def __contains__(self, key):
        return key in self.m

    def __setitem__(self, key, value):
        if key in self.m:
            del self.m[key]
        self.m[key] = headers.to_mime(key, value)

    def __delitem__(self, key):
        del self.m[key]

    def __nonzero__(self):
        return len(self.m) > 0

    def __iter__(self):
        for key, val in self.iteritems():
            yield (key, val)

    def prepend(self, key, val):
        self.m._headers.insert(0, (key, val))

    def add(self, key, value):
        self.m[key] = headers.to_mime(key, value)

    def keys(self):
        return self.m.keys()

    def items(self):
        return [(key, val) for (key, val) in self.iteritems()]

    def iteritems(self):
        for key, val in self.m.items():
            yield (key, try_decode(key, val))

    def get(self, key, default=None):
        val = try_decode(key, self.m.get(key, default))
        return val if val is not None else default

    def getall(self, key):
        return [try_decode(key, v) for v in self.m.get_all(key, [])]

    def __str__(self):
        return str(self.m._headers)

########NEW FILE########
__FILENAME__ = encodedword
# coding:utf-8
import logging
import regex as re

import email.quoprimime
import email.base64mime

from base64 import b64encode

from flanker.mime.message import charsets, errors

log = logging.getLogger(__name__)

#deal with unfolding
foldingWhiteSpace = re.compile(r"(\n\r?|\r\n?)(\s*)")


def unfold(value):
    """
    Unfolding is accomplished by simply removing any CRLF
    that is immediately followed by WSP.  Each header field should be
    treated in its unfolded form for further syntactic and semantic
    evaluation.
    """
    return re.sub(foldingWhiteSpace, r"\2", value)


def decode(header):
    return mime_to_unicode(header)


def mime_to_unicode(header):
    """
    Takes a header value and returns a fully decoded unicode string.
    It differs from standard Python's mail.header.decode_header() because:
        - it is higher level, i.e. returns a unicode string instead of
          an array of tuples
        - it accepts Unicode and non-ASCII strings as well

    >>> header_to_unicode("=?UTF-8?B?UmVbMl06INCX0LXQvNC70Y/QutC4?=")
        u"Земляки"
    >>> header_to_unicode("hello")
        u"Hello"
    """
    try:
        header = unfold(header)
        decoded = []  # decoded parts

        while header:
            match = encodedWord.search(header)
            if match:
                start = match.start()
                if start != 0:
                    # decodes unencoded ascii part to unicode
                    value = charsets.convert_to_unicode(ascii, header[0:start])
                    if value.strip():
                        decoded.append(value)
                # decode a header =?...?= of encoding
                charset, value = decode_part(
                    match.group('charset').lower(),
                    match.group('encoding').lower(),
                    match.group('encoded'))
                decoded.append(charsets.convert_to_unicode(charset, value))
                header = header[match.end():]
            else:
                # no match? append the remainder
                # of the string to the list of chunks
                decoded.append(charsets.convert_to_unicode(ascii, header))
                break
        return u"".join(decoded)
    except Exception:
        try:
            log.warning(
                u"HEADER-DECODE-FAIL: ({0}) - b64encoded".format(
                    b64encode(header)))
        except Exception:
            log.exception("Failed to log exception")
        return header


ascii = 'ascii'

#this spec refers to
#http://tools.ietf.org/html/rfc2047
encodedWord = re.compile(r'''(?P<encodedWord>
  =\?                  # literal =?
  (?P<charset>[^?]*?)  # non-greedy up to the next ? is the charset
  \?                   # literal ?
  (?P<encoding>[qb])   # either a "q" or a "b", case insensitive
  \?                   # literal ?
  (?P<encoded>.*?)     # non-greedy up to the next ?= is the encoded string
  \?=                  # literal ?=
)''', re.VERBOSE | re.IGNORECASE | re.MULTILINE)


def decode_part(charset, encoding, value):
    """
    Attempts to decode part, understands
    'q' - quoted encoding
    'b' - base64 mime encoding

    Returns (charset, decoded-string)
    """
    if encoding == 'q':
        return (charset, email.quoprimime.header_decode(str(value)))

    elif encoding == 'b':
        # Postel's law: add missing padding
        paderr = len(value) % 4
        if paderr:
            value += '==='[:4 - paderr]
        return (charset, email.base64mime.decode(value))

    elif not encoding:
        return (charset, value)

    else:
        raise errors.DecodingError(
            "Unknown encoding: {0}".format(encoding))

########NEW FILE########
__FILENAME__ = encoding
import email.message
import flanker.addresslib.address
import logging

from collections import deque
from email.header import Header
from flanker.mime.message.headers import parametrized
from flanker.utils import to_utf8

log = logging.getLogger(__name__)

# max length for a header line is 80 chars
# max recursion depth is 1000
# 80 * 1000 for header is too much for the system
# so we allow just 100 lines for header
MAX_HEADER_LENGTH = 8000

ADDRESS_HEADERS = ('From', 'To', 'Delivered-To', 'Cc', 'Bcc', 'Reply-To')


def to_mime(key, value):
    if not value:
        return ""

    if type(value) == list:
        return "; ".join(encode(key, v) for v in value)
    else:
        return encode(key, value)


def encode(name, value):
    try:
        if parametrized.is_parametrized(name, value):
            value, params = value
            return encode_parametrized(name, value, params)
        else:
            return encode_unstructured(name, value)
    except Exception:
        log.exception("Failed to encode %s %s" % (name, value))
        raise


def encode_unstructured(name, value):
    if len(value) > MAX_HEADER_LENGTH:
        return to_utf8(value)
    try:
        return Header(
            value.encode("ascii"), "ascii",
            header_name=name).encode(splitchars=' ;,')
    except UnicodeEncodeError:
        if is_address_header(name, value):
            return encode_address_header(name, value)
        else:
            return Header(
                to_utf8(value), "utf-8",
                header_name=name).encode(splitchars=' ;,')


def encode_address_header(name, value):
    out = deque()
    for addr in flanker.addresslib.address.parse_list(value):
        out.append(addr.full_spec())
    return "; ".join(out)


def encode_parametrized(key, value, params):
    if params:
        params = [encode_param(key, n, v) for n, v in params.iteritems()]
        return value + "; " + ("; ".join(params))
    else:
        return value


def encode_param(key, name, value):
    try:
        value = value.encode("ascii")
        return email.message._formatparam(name, value)
    except Exception:
        value = Header(value.encode("utf-8"), "utf-8",  header_name=key).encode(splitchars=' ;,')
        return email.message._formatparam(name, value)


def encode_string(name, value, maxlinelen=None):
    try:
        header = Header(value.encode("ascii"), "ascii", maxlinelen,
                        header_name=name)
    except UnicodeEncodeError:
        header = Header(value.encode("utf-8"), "utf-8", header_name=name)

    return header.encode(splitchars=' ;,')


def is_address_header(key, val):
    return key in ADDRESS_HEADERS and '@' in val

########NEW FILE########
__FILENAME__ = headers
from paste.util.multidict import MultiDict
from flanker.mime.message.headers.parsing import normalize, parse_stream
from flanker.mime.message.headers.encoding import to_mime
from flanker.mime.message.errors import EncodingError


class MimeHeaders(object):
    """Dictionary-like object that preserves the order and
    supports multiple values for the same key, knows
    whether it has been changed after the creation
    """

    def __init__(self, items=()):
        self.v = MultiDict(
            [(normalize(key), val) for (key, val) in items])
        self.changed = False

    def __getitem__(self, key):
        return self.v.get(normalize(key), None)

    def __len__(self):
        return len(self.v)

    def __iter__(self):
        return iter(self.v)

    def __contains__(self, key):
        return normalize(key) in self.v

    def __setitem__(self, key, value):
        self.v[normalize(key)] = _remove_newlines(value)
        self.changed = True

    def __delitem__(self, key):
        del self.v[normalize(key)]
        self.changed = True

    def __nonzero__(self):
        return len(self.v) > 0

    def prepend(self, key, val):
        self.v._items.insert(0, (key, _remove_newlines(val)))
        self.changed = True

    def add(self, key, value):
        """Adds header without changing the
        existing headers with same name"""

        self.v.add(normalize(key), _remove_newlines(value))
        self.changed = True

    def keys(self):
        """
        Returns the keys. (message header names)
        It remembers the order in which they were added, what
        is really important
        """
        return self.v.keys()

    def transform(self, fn):
        """Accepts a function, getting a key, val and returning
        a new pair of key, val and applies the function to all
        header, value pairs in the message.
        """

        changed = [False]

        def tracking_fn(key, val):
            new_key, new_val = fn(key, val)
            if new_val != val or new_key != key:
                changed[0] = True
            return new_key, new_val

        v = MultiDict(tracking_fn(key, val) for key, val in self.v.iteritems())
        if changed[0]:
            self.v = v
            self.changed = True

    def items(self):
        """
        Returns header,val pairs in the preserved order.
        """
        return list(self.iteritems())

    def iteritems(self):
        """
        Returns iterator header,val pairs in the preserved order.
        """
        return self.v.iteritems()

    def get(self, key, default=None):
        """
        Returns header value (case-insensitive).
        """
        return self.v.get(normalize(key), default)

    def getall(self, key):
        """
        Returns all header values by the given header name
        (case-insensitive)
        """
        return self.v.getall(normalize(key))

    def have_changed(self):
        """Tells whether someone has altered the headers
        after creation"""
        return self.changed

    def __str__(self):
        return str(self.v)

    @classmethod
    def from_stream(cls, stream):
        """Takes a stream and reads the headers,
        decodes headers to unicode dict like object"""
        return cls(parse_stream(stream))

    def to_stream(self, stream):
        """Takes a stream and serializes headers
        in a mime format"""

        for h, v in self.v.iteritems():
            try:
                h = h.encode('ascii')
            except UnicodeDecodeError:
                raise EncodingError("Non-ascii header name")
            stream.write("{0}: {1}\r\n".format(h, to_mime(h, v)))


def _remove_newlines(value):
    if not value:
        return ''
    elif isinstance(value, (str, unicode)):
        return value.replace('\r', '').replace('\n', '')
    else:
        return value

########NEW FILE########
__FILENAME__ = parametrized
"""Module that is responsible for parsing parameterized header values
encoded in accordance to rfc2231 (new style) or rfc1342 (old style)
"""
import urllib
import regex as re
from flanker.mime.message.headers import encodedword
from flanker.mime.message import charsets
from collections import deque
from itertools import groupby


def decode(header):
    """Accepts parameterized header value (encoded in accordance to
     rfc2231 (new style) or rfc1342 (old style)
     and returns tuple:
         value, {'key': u'val'}
     returns None in case of any failure
    """
    value, rest = split(encodedword.unfold(header))
    if value is None:
        return None, {}
    elif value:
        return value, decode_parameters(rest)


def is_parametrized(name, value):
    return name in ("Content-Type", "Content-Disposition",
                    "Content-Transfer-Encoding")


def fix_content_type(value, default=None):
    """Content-Type value may be badly broken"""
    if not value:
        return default or ('text', 'plain')
    values = value.lower().split("/")
    if len(values) >= 2:
        return values[:2]
    elif len(values) == 1:
        if values[0] == 'text':
            return 'text', 'plain'
        elif values[0] == 'html':
            return 'text', 'html'
        return 'application', 'octet-stream'


def split(header):
    """Splits value part and parameters part,
    e.g.
         split("MULTIPART/MIXED;boundary=hal_9000")
    becomes:
         ["multipart/mixed", "boundary=hal_9000"]
    """
    match = headerValue.match(header)
    if not match:
        return (None, None)
    return match.group(1).lower(), header[match.end():]


def decode_parameters(string):
    """Parameters can be splitted into several parts, e.g.

    title*0*=us-ascii'en'This%20is%20even%20more%20
    title*1*=%2A%2A%2Afun%2A%2A%2A%20
    title*2="isn't it!"

    decode them to the dictionary with keys and values"""
    parameters = collect_parameters(string)
    groups = {}
    for k, parts in groupby(parameters, get_key):
        groups[k] = concatenate(list(parts))
    return groups


def collect_parameters(rest):
    """Scans the string and collects parts
    that look like parameter, returns deque of strings
    """
    parameters = deque()
    p, rest = match_parameter(rest)
    while p:
        parameters.append(p)
        p, rest = match_parameter(rest)
    return parameters


def concatenate(parts):
    """ Concatenates splitted parts of a parameter in a single parameter,
    e.g.
         URL*0="ftp://";
         URL*1="cs.utk.edu/pub/moore/bulk-mailer/bulk-mailer.tar"

    becomes:

         URL="ftp://cs.utk.edu/pub/moore/bulk-mailer/bulk-mailer.tar"
    """
    part = parts[0]

    if is_old_style(part):
        # old-style parameters do not support any continuations
        return encodedword.mime_to_unicode(get_value(part))
    else:
        return u"".join(
            decode_new_style(p) for p in partition(parts))


def match_parameter(rest):
    for match in (match_old, match_new):
        p, rest = match(rest)
        if p:
            return p, rest
    return (None, rest)


def match_old(rest):
    match = oldStyleParameter.match(rest)
    if match:
        name = match.group('name')
        value = match.group('value')
        return parameter('old', name, value), rest[match.end():]
    else:
        return None, rest


def match_new(rest):
    match = newStyleParameter.match(rest)
    if match:
        name = parse_parameter_name(match.group('name'))
        value = match.group('value')
        return parameter('new', name, value), rest[match.end():]
    else:
        return (None, rest)


def reverse(string):
    """Native reverse of a string looks a little bit cryptic,
    just a readable wrapper"""
    return string[::-1]


def parse_parameter_name(key):
    """New style parameter names can be splitted into parts,
    e.g.

    title*0* means that it's the first part that is encoded
    title*1* means that it's the second part that is encoded
    title*2 means that it is the third part that is unencoded
    title means single unencoded
    title* means single encoded part

    I found it easier to match against a reversed string,
    as regexp is simpler
    """
    m = reverseContinuation.match(reverse(key))
    key = reverse(m.group('key'))
    part = reverse(m.group('part')) if m.group('part') else None
    encoded = m.group('encoded')
    return (key, part, encoded)


def decode_new_style(parameter):
    """Decodes parameter values, quoted or percent encoded, to unicode"""
    if is_quoted(parameter):
        return unquote(parameter)
    if is_encoded(parameter):
        return decode_charset(parameter)
    return get_value(parameter)


def partition(parts):
    """Partitions the parts in accordance to the algo here:
    http://tools.ietf.org/html/rfc2231#section-4.1
    """
    encoded = deque()
    for part in parts:
        if is_encoded(part):
            encoded.append(part)
            continue
        if encoded:
            yield join_parameters(encoded)
            encoded = deque()
        yield part
    if encoded:
        yield join_parameters(encoded)


def decode_charset(parameter):
    """Decodes things like:
    "us-ascii'en'This%20is%20even%20more%20%2A%2A%2Afun%2A%2A%2A%20"
    to unicode """

    v = get_value(parameter)
    parts = v.split("'", 2)
    if len(parts) != 3:
        return v
    charset, language, val = parts
    val = urllib.unquote(val)
    return charsets.convert_to_unicode(charset, val)


def unquote(parameter):
    """Simply removes quotes"""
    return get_value(parameter).strip('"')


def parameter(ptype, key, value):
    """Parameter is stored as a tuple,
    and below are conventional
    """
    return (ptype, key, value)


def is_quoted(part):
    return get_value(part)[0] == '"'


def is_new_style(parameter):
    return parameter[0] == 'new'


def is_old_style(parameter):
    return parameter[0] == 'old'


def is_encoded(part):
    return part[1][2] == '*'


def get_key(parameter):
    if is_old_style(parameter):
        return parameter[1].lower()
    else:
        return parameter[1][0].lower()


def get_value(parameter):
    return parameter[2]


def join_parameters(parts):
    joined = "".join(get_value(p) for p in parts)
    for p in parts:
        return parameter(p[0], p[1], joined)

# used to split header value and parameters
headerValue = re.compile(r"""
       # don't care about the spaces
       ^[\ \t]*
       #main type and sub type or any other value
       ([a-z0-9\-/\.]+)
       # grab the trailing spaces, colons
       [\ \t;]*""", re.IGNORECASE | re.VERBOSE)


oldStyleParameter = re.compile(r"""
     # according to rfc1342, param value can be encoded-word
     # and it's actually very popular, so detect this parameter first
     ^
     # skip spaces
     [\ \t]*
     # parameter name
     (?P<name>
         [^\x00-\x1f\s\(\)<>@,;:\\"/\[\]\?=]+
     )
     # skip spaces
     [\ \t]*
     =
     # skip spaces
     [\ \t]*
     #optional quoting sign
     "?
     # skip spaces
     [\ \t]*
     # and a glorious encoded-word sequence
     (?P<value>
       =\?
       .* # non-greedy to match the end sequence chars
       \?=
     )
     # ends with optional quoting sign that we ignore
     "?
""", re.IGNORECASE | re.VERBOSE)


newStyleParameter = re.compile(r"""
     # Here we grab anything that looks like a parameter
     ^
     # skip spaces
     [\ \t]*
     # parameter name
     (?P<name>
         [^\x00-\x1f\s\(\)<>@,;:\\"/\[\]\?=]+
     )
     # skip spaces
     [\ \t]*
     =
     # skip spaces
     [\ \t]*
     (?P<value>
       (?:
         "(?:
             [\x21\x23-\x5b\x5d-\x7e\ \t]
             |
             (?:\\[\x21-\x7e\t\ ])
          )+"
       )
     |
     # any (US-ASCII) CHAR except SPACE, CTLs, or tspecials
     [^\x00-\x1f\s\(\)<>@,;:\\"/\[\]\?=]+
     )
     # skip spaces
     [\ \t]*
     ;?
""", re.IGNORECASE | re.VERBOSE)

reverseContinuation = re.compile(
    "^(?P<encoded>\*)?(?P<part>\d+\*)?(?P<key>.*)")

########NEW FILE########
__FILENAME__ = parsing
import string
import regex
from collections import deque
from flanker.mime.message.headers import encodedword, parametrized
from flanker.mime.message.headers.wrappers import ContentType, WithParams
from flanker.mime.message.errors import DecodingError
from flanker.utils import to_unicode, is_pure_ascii

MAX_LINE_LENGTH = 10000


def normalize(header):
    return string.capwords(header.lower(), '-')


def parse_stream(stream):
    """Reads the incoming stream and returns list of tuples"""
    out = deque()
    for header in unfold(split(stream)):
        out.append(parse_header(header))
    return out


def parse_header(header):
    """ Accepts a raw header with name, colons and newlines
    and returns it's parsed value
    """
    name, val = split2(header)
    if not is_pure_ascii(name):
        raise DecodingError("Non-ascii header name")
    return name, parse_header_value(name, encodedword.unfold(val))


def parse_header_value(name, val):
    if not is_pure_ascii(val):
        if parametrized.is_parametrized(name, val):
            raise DecodingError("Unsupported value in content- header")
        return to_unicode(val)
    else:
        if parametrized.is_parametrized(name, val):
            val, params = parametrized.decode(val)
            if name == 'Content-Type':
                main, sub = parametrized.fix_content_type(val)
                return ContentType(main, sub, params)
            else:
                return WithParams(val, params)
        elif "=?" in val:
            # may be encoded word
            return encodedword.decode(val)
        else:
            return val


def is_empty(line):
    return line in ('\r\n', '\r', '\n')


RE_HEADER = regex.compile(r'^(From |[\041-\071\073-\176]+:|[\t ])')


def split(fp):
    """Read lines with headers until the start of body"""
    lines = deque()
    for line in fp:
        if len(line) > MAX_LINE_LENGTH:
            raise DecodingError(
                "Line is too long: {0}".format(len(line)))

        if is_empty(line):
            break

        # tricky case if it's not a header and not an empty line
        # ususally means that user forgot to separate the body and newlines
        # so "unread" this line here, what means to treat it like a body
        if not RE_HEADER.match(line):
            fp.seek(fp.tell() - len(line))
            break

        lines.append(line)

    return lines


def unfold(lines):
    headers = deque()

    for line in lines:
        # ignore unix from
        if line.startswith("From "):
            continue
        # this is continuation
        elif line[0] in ' \t':
            extend(headers, line)
        else:
            headers.append(line)

    new_headers = deque()
    for h in headers:
        if isinstance(h, deque):
            new_headers.append("".join(h).rstrip("\r\n"))
        else:
            new_headers.append(h.rstrip("\r\n"))

    return new_headers


def extend(headers, line):
    try:
        header = headers.pop()
    except IndexError:
        # this means that we got invalid header
        # ignore it
        return

    if isinstance(header, deque):
        header.append(line)
        headers.append(header)
    else:
        headers.append(deque((header, line)))


def split2(header):
    pair = header.split(":", 1)
    if len(pair) == 2:
        return normalize(pair[0].rstrip()), pair[1].lstrip()
    else:
        return (None, None)

########NEW FILE########
__FILENAME__ = wrappers
""" Useful wrappers for headers with parameters,
provide some convenience access methods
"""

import regex as re
import flanker.addresslib.address

from email.utils import make_msgid


class WithParams(tuple):

    def __new__(self, value, params=None):
        return tuple.__new__(self, (value, params or {}))

    @property
    def value(self):
        return tuple.__getitem__(self, 0)

    @property
    def params(self):
        return tuple.__getitem__(self, 1)


class ContentType(tuple):

    def __new__(self, main, sub, params=None):
        return tuple.__new__(
            self, (main.lower() + '/' + sub.lower(), params or {}))

    def __init__(self, main, sub, params={}):
        self.main = main
        self.sub = sub

    @property
    def value(self):
        return tuple.__getitem__(self, 0)

    @property
    def params(self):
        return tuple.__getitem__(self, 1)

    @property
    def format_type(self):
        return tuple.__getitem__(self, 0).split('/')[0]

    @property
    def subtype(self):
        return tuple.__getitem__(self, 0).split('/')[1]

    def is_content_type(self):
        return True

    def is_boundary(self):
        return False

    def is_end(self):
        return False

    def is_singlepart(self):
        return self.main != 'multipart' and\
            self.main != 'message' and\
            not self.is_headers_container()

    def is_multipart(self):
        return self.main == 'multipart'

    def is_headers_container(self):
        return self.is_feedback_report() or \
            self.is_rfc_headers() or \
            self.is_message_external_body() or \
            self.is_disposition_notification()

    def is_rfc_headers(self):
        return self == 'text/rfc822-headers'

    def is_message_external_body(self):
        return self == 'message/external-body'

    def is_message_container(self):
        return self == 'message/rfc822' or self == 'message/news'

    def is_disposition_notification(self):
        return self == 'message/disposition-notification'

    def is_delivery_status(self):
        return self == 'message/delivery-status'

    def is_feedback_report(self):
        return self == 'message/feedback-report'

    def is_delivery_report(self):
        return self == 'multipart/report'

    def get_boundary(self):
        return self.params.get("boundary")

    def get_boundary_line(self, final=False):
        return "--{0}{1}".format(
            self.get_boundary(), "--" if final else "")

    def get_charset(self):
        return self.params.get("charset", 'ascii').lower()

    def set_charset(self, value):
        self.params["charset"] = value.lower()

    def __str__(self):
        return "{0}/{1}".format(self.main, self.sub)

    def __eq__(self, other):
        if isinstance(other, ContentType):
            return self.main == other.main \
                and self.sub == other.sub \
                and self.params == other.params
        elif isinstance(other, tuple):
            return tuple.__eq__(self, other)
        elif isinstance(other, (unicode, str)):
            return str(self) == other
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)


class MessageId(str):

    RE_ID = re.compile("<([^<>]+)>", re.I)
    MIN_LENGTH = 5
    MAX_LENGTH = 256

    def __new__(cls, *args, **kw):
        return str.__new__(cls, *args, **kw)

    def __clean(self):
        return self.replace('"', '').replace("'", '')

    def __hash__(self):
        return hash(self.__clean())

    def __eq__(self, other):
        if isinstance(other, MessageId):
            return self.__clean() == other.__clean()
        else:
            return self.__clean() == str(other)

    @classmethod
    def from_string(cls, string):
        if not isinstance(string, (str, unicode)):
            return None
        for message_id in cls.scan(string):
            return message_id

    @classmethod
    def generate(cls, domain=None):
        message_id = make_msgid().strip("<>")
        if domain:
            local = message_id.split('@')[0]
            message_id = "{0}@{1}".format(local, domain)
        return cls(message_id)

    @classmethod
    def is_valid(cls, s):
        return cls.MIN_LENGTH < len(s) < cls.MAX_LENGTH and \
            flanker.addresslib.address.is_email(s)

    @classmethod
    def scan(cls, string):
        for m in cls.RE_ID.finditer(string):
            message_id = m.group(1)
            if cls.is_valid(message_id):
                yield cls(message_id)


class Subject(unicode):
    RE_RE = re.compile("((RE|FW|FWD|HA)([[]\d])*:\s*)*", re.I)

    def __new__(cls, *args, **kw):
        return unicode.__new__(cls, *args, **kw)

    def strip_replies(self):
        return self.RE_RE.sub('', self)

########NEW FILE########
__FILENAME__ = part
import email.utils
import email.encoders
import logging
import mimetypes
import imghdr
import base64
import quopri

from contextlib import closing
from cStringIO import StringIO
from os import path

from email.mime import audio

from flanker.utils import is_pure_ascii
from flanker.mime import bounce
from flanker.mime.message import headers, charsets
from flanker.mime.message.headers import WithParams, ContentType, MessageId, Subject
from flanker.mime.message.headers.parametrized import fix_content_type
from flanker.mime.message.errors import EncodingError, DecodingError

log = logging.getLogger(__name__)

CTE = WithParams('7bit', {})

class Stream(object):

    def __init__(self, content_type, start, end, string, stream):
        self.content_type = content_type
        self.start = start
        self.end = end
        self.string = string
        self.stream = stream

        self._headers = None
        self._body_start = None
        self._body = None
        self._body_changed = False
        self.size = len(self.string)

    @property
    def headers(self):
        self._load_headers()
        return self._headers

    @property
    def body(self):
        self._load_body()
        return self._body

    @body.setter
    def body(self, value):
        self._set_body(value)

    def read_message(self):
        self.stream.seek(self.start)
        return self.stream.read(self.end - self.start + 1)

    def read_body(self):
        self._load_headers()
        self.stream.seek(self._body_start)
        return self.stream.read(self.end - self._body_start + 1)

    def _load_headers(self):
        if self._headers is None:
            self.stream.seek(self.start)
            self._headers = headers.MimeHeaders.from_stream(self.stream)
            self._body_start = self.stream.tell()

    def _load_body(self):
        if self._body is None:
            self._load_headers()
            self.stream.seek(self._body_start)
            self._body = decode_body(
                self.content_type,
                self.headers.get('Content-Transfer-Encoding', CTE).value,
                self.stream.read(self.end - self._body_start + 1))

    def _set_body(self, value):
        self._body = value
        self._body_changed = True


    def headers_changed(self):
        return self._headers is not None and self._headers.have_changed()

    def body_changed(self):
        return self._body_changed


def adjust_content_type(content_type, body=None, filename=None):
    """Adjust content type based on filename or body contents
    """
    if filename and str(content_type) == 'application/octet-stream':
        guessed = mimetypes.guess_type(filename)[0]
        if guessed:
            main, sub = fix_content_type(
                guessed, default=('application', 'octet-stream'))
            content_type = ContentType(main, sub)

    if content_type.main == 'image' and body:
        sub = imghdr.what(None, body)
        if sub:
            content_type = ContentType('image', sub)

    elif content_type.main == 'audio' and body:
        sub = audio._whatsnd(body)
        if sub:
            content_type = ContentType('audio', sub)

    return content_type


class Body(object):
    def __init__(
        self, content_type, body, charset=None, disposition=None, filename=None):
        self.headers = headers.MimeHeaders()
        self.body = body
        self.disposition = disposition or ('attachment' if filename else None)
        self.filename = filename
        self.size = len(body)

        if self.filename:
            self.filename = path.basename(self.filename)

        content_type = adjust_content_type(content_type, body, filename)

        if content_type.main == 'text':
            # the text should have a charset
            if not charset:
                charset = "utf-8"

            # it should be stored as unicode. period
            self.body = charsets.convert_to_unicode(charset, body)

            # let's be simple when possible
            if charset != 'ascii' and is_pure_ascii(body):
                charset = 'ascii'

        self.headers['MIME-Version'] = '1.0'
        self.headers['Content-Type'] = content_type
        if charset:
            content_type.params['charset'] = charset

        if self.disposition:
            self.headers['Content-Disposition'] = WithParams(disposition)
            if self.filename:
                self.headers['Content-Disposition'].params['filename'] = self.filename
                self.headers['Content-Type'].params['name'] = self.filename

    @property
    def content_type(self):
        return self.headers['Content-Type']

    def headers_changed(self):
        return True

    def body_changed(self):
        return True


class Part(object):

    def __init__(self, ctype):
        self.headers = headers.MimeHeaders()
        self.body = None
        self.headers['Content-Type'] = ctype
        self.headers['MIME-Version'] = '1.0'
        self.size = 0

    @property
    def content_type(self):
        return self.headers['Content-Type']

    def headers_changed(self):
        return True

    def body_changed(self):
        return True


class MimePart(object):
    def __init__(self, container, parts=None, enclosed=None, is_root=False):

        self._container = container
        self._is_root = is_root
        self._bounce = None

        self.parts = parts or []
        self.enclosed = enclosed

    @property
    def size(self):
        """ Returns message size in bytes"""
        if self.is_root() and not self.was_changed():
            if isinstance(self._container, Stream):
                return self._container.size
            else:
                return sum(part._container.size
                           for part in self.walk(with_self=True))
        else:
            with closing(_CounterIO()) as out:
                self.to_stream(out)
                return out.getvalue()

    @property
    def headers(self):
        """Returns multi dictionary with headers converted to unicode,
        headers like Content-Type, Content-Disposition are tuples
        ("value", {"param": "val"})"""
        return self._container.headers

    @property
    def content_type(self):
        """ returns object with properties:
        main - main part of content type
        sub - subpart of content type
        params - dictionary with parameters
        """
        return self._container.content_type

    @property
    def content_disposition(self):
        """ returns tuple (value, params) """
        return self.headers.get('Content-Disposition', WithParams(None))

    @property
    def content_encoding(self):
        return self.headers.get(
            'Content-Transfer-Encoding', WithParams('7bit'))

    @content_encoding.setter
    def content_encoding(self, value):
        self.headers['Content-Transfer-Encoding'] = value

    @property
    def body(self):
        """ returns decoded body """
        if self.content_type.is_singlepart()\
                or self.content_type.is_delivery_status():
            return self._container.body

    @body.setter
    def body(self, value):
        if self.content_type.is_singlepart()\
                or self.content_type.is_delivery_status():
            self._container.body = value

    @property
    def charset(self):
        return self.content_type.get_charset()

    @charset.setter
    def charset(self, value):
        charset = value.lower()
        self.content_type.set_charset(value)
        if 'Content-Type' not in self.headers:
            self.headers['Content-Type'] = ContentType('text', 'plain', {})
        self.headers['Content-Type'].params['charset'] = charset
        self.headers.changed = True

    @property
    def message_id(self):
        return MessageId.from_string(self.headers.get('Message-Id', ''))

    @message_id.setter
    def message_id(self, value):
        if not MessageId.is_valid(value):
            raise ValueError("invalid message id format")
        self.headers['Message-Id'] = "<{0}>".format(value)

    @property
    def subject(self):
        return self.headers.get('Subject', '')

    @property
    def clean_subject(self):
        """
        Subject without re, fw, fwd, HA prefixes
        """
        return Subject(self.subject).strip_replies()

    @property
    def references(self):
        """
        Retunrs message-ids referencing the message
        in accordance to jwz threading algo
        """
        refs = list(MessageId.scan(self.headers.get('References', '')))
        if not refs:
            reply = MessageId.from_string(self.headers.get('In-Reply-To', ''))
            if reply:
                refs.append(reply[0])
        return refs

    @property
    def detected_format(self):
        return self.detected_content_type.format_type

    @property
    def detected_subtype(self):
        return self.detected_content_type.subtype

    @property
    def detected_content_type(self):
        """Returns content type based on the body
        content, file name and original content type
        supplied inside the message
        """
        return adjust_content_type(
            self.content_type, filename=self.detected_file_name)

    @property
    def detected_file_name(self):
        """Detects file name based on content type
        or part name
        """
        ctype = self.content_type
        file_name = ctype.params.get('name', '') or ctype.params.get('filename', '')

        cdisp = self.content_disposition
        if cdisp.value == 'attachment':
            file_name = cdisp.params.get('filename', '') or file_name

        # filenames can be presented as tuples, like:
        # ('us-ascii', 'en-us', 'image.jpg')
        if isinstance(file_name, tuple) and len(file_name) == 3:
            # encoding permissible to be empty
            encoding = file_name[0]
            if encoding:
                file_name = file_name[2].decode(encoding)
            else:
                file_name = file_name[2]

        file_name = headers.mime_to_unicode(file_name)
        return file_name

    def is_root(self):
        return self._is_root

    def set_root(self, val):
        self._is_root = bool(val)

    def to_string(self):
        """ returns MIME representation of the message"""
        # this optimisation matters *A LOT*
        # we submit the original string,
        # no copying, no alternation, yeah!
        if self.is_root() and not self.was_changed():
            return self._container.string
        else:
            with closing(StringIO()) as out:
                self.to_stream(out)
                return out.getvalue()

    def to_stream(self, out):
        """ serialzes the message using file like object """
        if not self.was_changed():
            out.write(self._container.read_message())
        else:
            try:
                original_position = out.tell()
                self.to_stream_when_changed(out)
            except DecodingError:
                out.seek(original_position)
                out.write(self._container.read_message())


    def to_stream_when_changed(self, out):

        ctype = self.content_type

        if ctype.is_singlepart():

            if self._container.body_changed():
                charset, encoding, body = encode_body(self)
                if charset:
                    self.charset = charset
                self.content_encoding = WithParams(encoding)
            else:
                body = self._container.read_body()

            # RFC allows subparts without headers
            if self.headers:
                self.headers.to_stream(out)
            elif self.is_root():
                raise EncodingError("Root message should have headers")

            out.write(CRLF)
            out.write(body)
        else:
            self.headers.to_stream(out)
            out.write(CRLF)

            if ctype.is_multipart():
                boundary = ctype.get_boundary_line()
                for index, part in enumerate(self.parts):
                    out.write(
                        (CRLF if index != 0 else "") + boundary + CRLF)
                    part.to_stream(out)
                out.write(CRLF + ctype.get_boundary_line(final=True) + CRLF)

            elif ctype.is_message_container():
                self.enclosed.to_stream(out)

    def was_changed(self):
        if self._container.headers_changed():
            return True

        if self.content_type.is_singlepart():
            if self._container.body_changed():
                return True
            return False

        elif self.content_type.is_multipart():
            return any(p.was_changed() for p in self.parts)

        elif self.content_type.is_message_container():
            return self.enclosed.was_changed()

    def walk(self, with_self=False, skip_enclosed=False):
        """ Returns iterator object traversing through the message parts,
        if you want to include the top level part into the iteration, use
        'with_self' parameter. If you don't want to include parts of
        enclosed messages, use 'skip_enclosed' parameter. Each part itself
        provides headers, content_type and body members.
        """
        if with_self:
            yield self

        if self.content_type.is_multipart():
            for p in self.parts:
                yield p
                for x in p.walk(False, skip_enclosed=skip_enclosed):
                    yield x

        elif self.content_type.is_message_container() and not skip_enclosed:
            yield self.enclosed
            for p in self.enclosed.walk(False):
                yield p

    def is_attachment(self):
        return self.content_disposition.value == 'attachment'

    def is_body(self):
        return (not self.detected_file_name and
                (self.content_type.format_type == 'text' or
                 self.content_type.format_type == 'message'))

    def is_inline(self):
        return self.content_disposition.value == 'inline'

    def is_delivery_notification(self):
        """ Tells whether a message is a system delivery notification """
        ctype = self.content_type
        return  ctype == 'multipart/report'\
            and ctype.params.get('report-type') == 'delivery-status'

    def get_attached_message(self):
        """ Returns attached message if found, None otherwize"""
        try:
            for part in self.walk(with_self=True):
                if part.content_type == 'message/rfc822':
                    for p in part.walk():
                        return p
        except Exception:
            log.exception("Failed to get attached message")
            return None

    def remove_headers(self, *headers):
        """Removes all passed headers name in one operation"""
        for header in headers:
            if header in self.headers:
                del self.headers[header]

    def to_python_message(self):
        return email.message_from_string(self.to_string())

    @property
    def bounce(self):
        """ If the message is bounce, retuns bounce object that
        provides the values:

        score - between 0 and 1
        status -  delivery status
        notification - human readable description
        diagnostic_code - smtp diagnostic codes

        Can raise MimeError in case if MIME is screwed
        """
        if not self._bounce:
            self._bounce = bounce.detect(self)
        return self._bounce

    def is_bounce(self, threshold=0.3):
        """
        Determines whether the message is a bounce message based on
        given threshold.  0.3 is a good conservative base.
        """
        return self.bounce.score > threshold

    def enclose(self, message):
        self.enclosed = message
        message.set_root(False)

    def append(self, *messages):
        for m in messages:
            self.parts.append(m)
            m.set_root(False)

    def __str__(self):
        return "({0})".format(self.content_type)


def decode_body(content_type, content_encoding, body):
    # decode the transfer encoding
    try:
        body = decode_transfer_encoding(
                    content_encoding, body)
    except Exception:
        raise DecodingError("Failed to decode body")

    # decode the charset next
    return decode_charset(content_type, body)


def decode_transfer_encoding(encoding, body):
    if encoding == 'base64':
        return email.utils._bdecode(body)
    elif encoding == 'quoted-printable':
        return email.utils._qdecode(body)
    else:
        return body

def decode_charset(ctype, body):
    if ctype.main != 'text':
        return body

    charset = ctype.get_charset()
    body = charsets.convert_to_unicode(charset, body)

    # for text/html unicode bodies make sure to replace
    # the whitespace (0xA0) with &nbsp; Outlook is reported to
    # have a bug there
    if ctype.sub =='html' and charset == 'utf-8':
        # Outlook bug
        body = body.replace(u'\xa0', u'&nbsp;')

    return body


def encode_body(part):
    content_type = part.content_type
    content_encoding = part.content_encoding.value
    body = part._container.body

    charset = content_type.get_charset()
    if content_type.main == 'text':
        charset, body = encode_charset(charset, body)
        content_encoding = choose_text_encoding(
            charset, content_encoding, body)
    else:
        content_encoding = 'base64'

    body = encode_transfer_encoding(content_encoding, body)
    return charset, content_encoding, body


def encode_charset(preferred_charset, text):
    try:
        charset = preferred_charset or 'ascii'
        text = text.encode(preferred_charset)
    except:
        charset = 'utf-8'
        text = text.encode(charset)
    return charset, text


def encode_transfer_encoding(encoding, body):
    if encoding == 'quoted-printable':
        return email.encoders._qencode(body)
    elif encoding == 'base64':
        return email.encoders._bencode(body)
    else:
        return body


def choose_text_encoding(charset, preferred_encoding, body):
    if charset in ('ascii', 'iso-8859-1', 'us-ascii'):
        if has_long_lines(body):
            return stronger_encoding(preferred_encoding, 'quoted-printable')
        else:
            return preferred_encoding
    else:
        return stronger_encoding(preferred_encoding, 'base64')


def stronger_encoding(a, b):
    weights = {'7bit': 0, 'quoted-printable': 1, 'base64': 1, '8bit': 3}
    if weights.get(a, -1) >= weights[b]:
        return a
    return b


def has_long_lines(text, max_line_len=599):
    '''
    Returns True if text contains lines longer than a certain length.
    Some SMTP servers (Exchange) refuse to accept messages "wider" than
    certain length.
    '''
    if not text:
        return False
    for line in text.splitlines():
        if len(line) >= max_line_len:
            return True
    return False

CRLF = "\r\n"

class _CounterIO(object):
    def __init__(self):
        self.length = 0
    def tell(self):
        return self.length
    def write(self, s):
        self.length += len(s)
    def seek(self, p):
        self.length = p
    def getvalue(self):
        return self.length
    def close(self):
        pass

########NEW FILE########
__FILENAME__ = scanner
import regex as re
from collections import deque
from cStringIO import StringIO
from flanker.mime.message.headers import parsing, is_empty, ContentType
from flanker.mime.message.part import MimePart, Stream
from flanker.mime.message.errors import DecodingError
from logging import getLogger

log = getLogger(__name__)


def scan(string):
    """Scanner that uses 1 pass to scan the entire message and
    build a message tree"""

    if not isinstance(string, str):
        raise DecodingError("Scanner works with byte strings only")

    tokens = tokenize(string)
    if not tokens:
        tokens = [default_content_type()]
    try:
        return traverse(
            Start(), TokensIterator(tokens, string))
    except DecodingError:
        raise
    except Exception:
        raise DecodingError(
            "Mailformed MIME message")


def traverse(pointer, iterator, parent=None):
    """Recursive-descendant parser"""

    iterator.check()
    token = iterator.next()

    # this means that this part does not have any
    # content type set, so set it to RFC default (text/plain)
    # it even can have no headers
    if token.is_end() or token.is_boundary():

        return make_part(
            content_type=default_content_type(),
            start=pointer,
            end=token,
            iterator=iterator,
            parent=parent)

    # this part tells us that it is singlepart
    # so we should ignore all other content-type headers
    # until the boundary or the end of message
    if token.is_singlepart():

        while True:
            iterator.check()
            end = iterator.next()
            if not end.is_content_type():
                break

        return make_part(
            content_type=token,
            start=pointer,
            end=end,
            iterator=iterator,
            parent=parent)

    # good old multipart message
    # here goes the real recursion
    # we scan part by part until the end
    elif token.is_multipart():
        content_type = token

        # well, multipart message should provide
        # some boundary, how could we parse it otherwise?
        boundary = content_type.get_boundary()
        if not boundary:
            raise DecodingError(
                "Multipart message without boundary")

        parts = deque()
        token = iterator.next()

        # we are expecting first boundary for multipart message
        # something is broken otherwize
        if not token.is_boundary() or token != boundary:
            raise DecodingError(
                "Multipart message without starting boundary")

        while True:
            token = iterator.current()
            if token.is_end():
                break
            if token == boundary and token.is_final():
                iterator.next()
                break
            parts.append(
                    traverse(token, iterator, content_type))

        return make_part(
            content_type=content_type,
            start=pointer,
            end=token,
            iterator=iterator,
            parts=parts,
            parent=parent)

    # this is a weird mime part, actually
    # it can contain multiple headers
    # separated by newlines, so we grab them here
    elif token.is_delivery_status():

        if parent and parent.is_multipart():
            while True:
                iterator.check()
                end = iterator.next()
                if not end.is_content_type():
                    break
        else:
            raise DecodingError(
                "Mailformed delivery status message")

        return make_part(
            content_type=token,
            start=pointer,
            end=end,
            iterator=iterator,
            parent=parent)

    # this is a message container that holds
    # a message inside, delimited from parent
    # headers by newline
    elif token.is_message_container():
        enclosed = traverse(pointer, iterator, token)
        return make_part(
            content_type=token,
            start=pointer,
            end=iterator.current(),
            iterator=iterator,
            enclosed=enclosed,
            parent=parent)

    # this part contains headers separated by newlines,
    # grab these headers and enclose them in one part
    elif token.is_headers_container():
        enclosed = grab_headers(pointer, iterator, token)
        return make_part(
            content_type=token,
            start=pointer,
            end=iterator.current(),
            iterator=iterator,
            enclosed=enclosed,
            parent=parent)


def grab_headers(pointer, iterator, parent):
    """This function collects all tokens till the boundary
    or the end of the message. Used to scan parts of the message
    that contain random headers, e.g. text/rfc822-headers"""

    content_type = None
    while True:

        iterator.check()
        end = iterator.next()

        # remember the first content-type we have met when grabbing
        # the headers until the boundary or message end
        if not content_type and end.is_content_type():
            content_type = end

        if not end.is_content_type():
            break

    return make_part(
        content_type=content_type or ContentType("text", "plain"),
        start=pointer,
        end=end,
        iterator=iterator,
        parent=parent)


def default_content_type():
    return ContentType("text", "plain", {'charset': 'ascii'})


def make_part(content_type, start, end, iterator,
        parts=[], enclosed=None, parent=None):

    # here we detect where the message really starts
    # the exact position in the string, at the end of the
    # starting boundary and after the begining of the end boundary
    if start.is_boundary():
        start = start.end + 1
    else:
        start = start.start

    # if this is the message ending, end of part
    # the position of the last symbol of the message
    if end.is_end():
        end = len(iterator.string) - 1
    # for multipart boundaries
    # consider the final boundary as the ending one
    elif content_type.is_multipart():
        end = end.end
    # otherwize, end is position of the the symbol before
    # the boundary start
    else:
        end = end.start - 1

    # our tokenizer detected the begining of the message container
    # that is separated from the enclosed message by newlines
    # here we find where the enclosed message begings by searching for the
    # first newline
    if parent and (parent.is_message_container() or parent.is_headers_container()):
        start = locate_first_newline(iterator.stream, start)

    # ok, finally, create the MimePart.
    # note that it does not parse anything, just remembers
    # the position in the string
    return MimePart(
        container=Stream(
            content_type=content_type,
            start=start,
            end=end,
            stream=iterator.stream,
            string=iterator.string),
        parts=parts,
        enclosed=enclosed,
        is_root=(parent==None))


def locate_first_newline(stream, start):
    """We need to locate the first newline"""
    stream.seek(start)
    for line in stream:
        if is_empty(line):
            return stream.tell()


class TokensIterator(object):

    def __init__(self, tokens, string):
        self.position = -1
        self.tokens = tokens
        self.string = string
        self.stream = StringIO(string)
        self.opcount = 0

    def next(self):
        self.position += 1
        if self.position >= len(self.tokens):
            return END
        return self.tokens[self.position]

    def current(self):
        if self.position >= len(self.tokens):
            return END
        return self.tokens[self.position]

    def back(self):
        self.position -= 1

    def check(self):
        """ This function is used to protect our lovely scanner
        from the deadloops, we count the number of operations performed
        and will raise an exception if things go wrong (too much ops)
        """
        self.opcount += 1
        if self.opcount > MAX_OPS:
            raise DecodingError(
                "Too many parts: {0}, max is {1}".format(
                    self.opcount, MAX_OPS))

class Boundary(object):
    def __init__(self, value, start, end, final=None):
        self.value = value
        self.start = start
        self.end = end
        self.final = final

    def is_final(self):
        return self.final

    def __str__(self):
        return "Boundary({0}, final={1})".format(
            self.value, self.final)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        if isinstance(other, Boundary):
            return self.value == other.value and self.final == other.final
        else:
            return self.value == str(other)

    def is_content_type(self):
        return False

    def is_boundary(self):
        return True

    def is_end(self):
        return False


class End(object):
    def is_end(self):
        return True

    @property
    def start(self):
        return -1

    @property
    def end(self):
        return -1

    def is_boundary(self):
        return False

    def is_content_type(self):
        return False


class Start(object):
    def is_end(self):
        return False

    @property
    def start(self):
        return 0

    @property
    def end(self):
        return 0

    def is_boundary(self):
        return False


pattern = re.compile(
    r"""(?P<ctype>
             ^content-type:

               # field value, consists of printable
               # US-ASCII chars, space and tab
               [\x21-\x7e\ \t]+

              # optional field folded part
              # newline followed by one or more spaces
              # and field value symbols (can not be empty)
              (?:(?:\r\n|\n)[ \t]+[\x20-\x7e \t]+)*
          ) |
         (?P<boundary>
             # this may be a boundary and may be not
             # we just pre-scan it for future consideration
             ^--.*
          )""",
    re.IGNORECASE | re.MULTILINE | re.VERBOSE)


CTYPE = 'ctype'
BOUNDARY = 'boundary'
END = End()
MAX_OPS = 500


def tokenize(string):
    """ This function scans the entire message with a simple regex to find
    all Content-Types and boundaries.
    """
    tokens = deque()
    for m in pattern.finditer(string):
        if m.group(CTYPE):
            name, token = parsing.parse_header(m.group(CTYPE))
        else:
            token = Boundary(
                m.group(BOUNDARY).strip("\t\r\n"),
                grab_newline(m.start(), string, -1),
                grab_newline(m.end(), string, 1))
        tokens.append(token)
    return setup_boundaries(tokens)


def grab_newline(position, string, direction):
    """Boundary can be preceeded by \r\n or \n and can end with \r\n or \n
    this function scans the line to locate these cases.
    """
    while 0 < position < len(string):
        if string[position] == '\n':
            if direction < 0:
                if position - 1 > 0 and string[position-1] == '\r':
                    return position - 1
            return position
        position += direction
    return position


def setup_boundaries(tokens):
    """ We need to reliably determine whether given line is a boundary
    or just pretends to be one. We get all the multipart content-types
    that declare the boundaries and check each boundary against them
    to verify. Additional complexity is that boundary can consist
    of dashes only
    """
    boundaries = [t.get_boundary() for t in tokens \
                      if t.is_content_type() and t.get_boundary()]

    def strip_endings(value):
        if value.endswith("--"):
            return value[:-2]
        else:
            return value

    def setup(token):
        if token.is_content_type():
            return True

        elif token.is_boundary():
            value = token.value[2:]

            if value in boundaries:
                token.value = value
                token.final = False
                return True

            if strip_endings(value) in boundaries:
                token.value = strip_endings(value)
                token.final = True
                return True

            # false boundary
            return False

        else:
            raise DecodingError("Unknown token")

        return token.is_content_type() or \
            (token.is_boundary() and token in boundaries)
    return [t for t in tokens if setup(t)]

########NEW FILE########
__FILENAME__ = threading
"""
Implements message threading
"""
from email.utils import make_msgid


def build_thread(messages):
    """
    Groups given message list by conversation
    returns tree with root linked to all messages
    """
    thread = build_root_set(
        build_table(messages))
    thread.prune_empty()
    return thread


def build_table(messages):
    id_table = {}
    for message in messages:
        map_message(message, id_table)
    return id_table


def build_root_set(table):
    root = Container()
    for container in table.itervalues():
        if not container.parent:
            root.add_child(container)
    return root


def map_message(message, table):

    def container(message_id):
        return table.setdefault(message_id, Container())

    w = Wrapper(message)
    this = container(w.message_id)

    # process case when we have two messages
    # with the same id, we should put
    # our current message to another container
    # otherwise the message would be lost
    if this.message:
        fake_id = make_msgid()
        this = container(fake_id)
    this.message = w

    # link message parents together
    prev = None
    for parent_id in w.references:
        parent = container(parent_id)
        if prev and not parent.parent and not introduces_loop(prev, parent):
            prev.add_child(parent)
        prev = parent

    # process case where this message has parent
    # unlink the old parent in this case
    if this.parent:
        this.parent.remove_child(this)

    # link to the cool parent instead
    if prev and not introduces_loop(prev, this):
        prev.add_child(this)


def introduces_loop(parent, child):
    return parent == child or child.has_descendant(parent)


class Container(object):
    def __init__(self, message=None):
        self.message = message
        self.parent = None
        self.child = None
        self.next = None
        self.prev = None

    def __str__(self):
        return self.message.message_id if self.message else "dummy"

    @property
    def is_dummy(self):
        return not self.message

    @property
    def in_root_set(self):
        return self.parent.parent is None

    @property
    def has_children(self):
        return self.child is not None

    @property
    def has_one_child(self):
        return self.child and self.child.next is None

    @property
    def last_child(self):
        child = self.child
        while child and child.next:
            child = child.next
        return child

    def iter_children(self):
        child = self.child
        while child:
            yield child
            child = child.next

    def has_descendant(self, container):
        child = self.child
        while child:
            if child == container or child.has_descendant(container):
                return True
            child = child.next
        return False

    def add_child(self, container):
        """
        Inserts child in front of list of children
        """
        if self.child:
            container.next = self.child
            self.child.prev = container

        self.child = container
        self.child.parent = self
        self.child.prev = None

    def remove_child(self, container):
        """
        """
        if container.parent != self:
            raise Exception("Operation on child when I'm not parent!")
        if not container.prev:
            self.child = container.next
            if self.child:
                self.child.prev = None
        else:
            container.prev.next = container.next
            if container.next:
                container.next.prev = container.prev
        container.parent = None
        container.prev = None
        container.next = None

    def replace_with_its_children(self, container):
        """
        Replaces container with its children.
        """
        if not container.has_children:
            return

        for c in container.iter_children():
            c.parent = self

        if not container.prev:
            self.child = container.child
        else:
            container.prev.next = container.child
            container.child.prev = container.prev

        if container.next:
            last_child = container.last_child
            container.next.prev = last_child
            last_child.next = container.next

    def prune_empty(self):
        """
        Removes child containers
        that don't have messages inside.
        """
        container = self.child
        while container:
            if container.is_dummy and not container.has_children:
                next_ = container.next
                self.remove_child(container)
                container = next_
            elif container.is_dummy \
                 and container.has_children \
                 and (not container.in_root_set or container.has_one_child):
                # remove container from the list
                # replacing it with it's children
                next_ = container.child
                self.replace_with_its_children(container)
                container.parent = None
                container.child = None
                container = next_
            elif container.has_children:
                container.prune_empty()
                container = container.next
            else:
                container = container.next


class Wrapper(object):
    def __init__(self, message):
        self.message = message
        self.message_id = message.message_id or make_msgid()
        self.references = message.references
        #self.subject = message.subject
        #self.clean_subject = message.clean_subject

########NEW FILE########
__FILENAME__ = utils
from cStringIO import StringIO
from contextlib import closing
from email.generator import Generator

def python_message_to_string(msg):
    """Converts python message to string in a proper way"""
    with closing(StringIO()) as fp:
        g = Generator(fp, mangle_from_=False)
        g.flatten(msg, unixfrom=False)
        return fp.getvalue()

########NEW FILE########
__FILENAME__ = utils
# coding:utf-8
import re
import chardet

from functools import wraps
from flanker.mime.message import errors

'''
Utility functions and classes used by flanker.
'''

def _guess_and_convert(value):
    charset = chardet.detect(value)

    if not charset["encoding"]:
        raise errors.DecodingError("Failed to guess encoding for %s" %(value, ))

    try:
        value = value.decode(charset["encoding"], "replace")
        return value
    except (UnicodeError, LookupError):
        raise errors.DecodingError(str(e))

def _make_unicode(value, charset=None):
    if isinstance(value, unicode):
        return value

    try:
        if charset:
            value = value.decode(charset, "strict")
            return value
        else:
            value = value.decode("utf-8", "strict")
            return value
    except (UnicodeError, LookupError):
        value = _guess_and_convert(value)

    return value

def to_unicode(value, charset=None):
    value = _make_unicode(value, charset)
    return unicode(value.encode("utf-8", "strict"), "utf-8", 'strict')

def to_utf8(value, charset=None):
    '''
    Safely returns a UTF-8 version of a given string
    >>> utils.to_utf8(u'hi')
        'hi'
    '''

    value = _make_unicode(value, charset)

    return value.encode("utf-8", "strict")


def is_pure_ascii(value):
    '''
    Determines whether the given string is a pure ascii
    string
    >>> utils.is_pure_ascii(u"Cаша")
        False
    >>> utils.is_pure_ascii(u"Alice")
        True
    >>> utils.is_pure_ascii("Alice")
        True
    '''

    if value is None:
        return False
    if not isinstance(value, basestring):
        return False

    try:
        value.encode("ascii")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return False
    return True


def cleanup_display_name(name):
    return name.strip(''';,'\r\n ''')


def cleanup_email(email):
    return email.strip("<>;, ")


def contains_control_chars(s):
    if CONTROL_CHAR_RE.match(s):
        return True
    return False


def metrics_wrapper():

    def decorate(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            return_value = f(*args, **kwargs)
            if 'metrics' in kwargs and kwargs['metrics'] == True:
                #return all values
                return return_value

            # if we have a single item
            if len(return_value[:-1]) == 1:
                return return_value[0]

            # return all except the last value
            return return_value[:-1]

        return wrapper

    return decorate


# allows, \t\n\v\f\r (0x09-0x0d)
CONTROL_CHARS = ''.join(map(unichr, range(0, 9) + range(14, 32) + range(127, 160)))
CONTROL_CHAR_RE = re.compile('[%s]' % re.escape(CONTROL_CHARS))

########NEW FILE########
__FILENAME__ = address_test
# coding:utf-8

from .. import *
from nose.tools import assert_equal, assert_not_equal

from flanker.addresslib.address import parse, parse_list
from flanker.addresslib.address import Address, AddressList, EmailAddress, UrlAddress


def test_addr_properties():
    email = parse('name@host.com')
    url = parse('http://host.com')
    non_ascii = parse(u'Gonzalo Bañuelos<gonz@host.com>')

    eq_ (False, url.supports_routing)
    eq_ (True,  email.supports_routing)

    eq_(Address.Type.Email, email.addr_type)
    eq_(Address.Type.Url, url.addr_type)
    eq_(non_ascii, "gonz@host.com")

    adr = parse("Zeka <EV@host.coM>")
    eq_ (str(adr), 'EV@host.com')


def test_address_compare():
    a = EmailAddress("a@host.com")
    b = EmailAddress("b@host.com")
    also_a = EmailAddress("A@host.com")

    ok_(a == also_a)
    #eq_(False, a != "I am also A <a@HOST.com>")
    ok_(a != 'crap')
    ok_(a != None)
    ok_(a != b)

    u = UrlAddress("http://hello.com")
    ok_ (u == "http://hello.com")

    # make sure it works for sets:
    s = set()
    s.add(a)
    s.add(also_a)
    eq_ (1, len(s))
    s.add(u)
    s.add(u)
    eq_ (2, len(s))


def test_local_url():
    u = UrlAddress('http:///foo/bar')
    eq_(None, u.hostname)


def test_addresslist_basics():
    lst = parse_list("http://foo.com:1000; Biz@Kontsevoy.Com   ")
    eq_ (2, len(lst))
    eq_ ("http", lst[0].scheme)
    eq_ ("kontsevoy.com", lst[1].hostname)
    eq_ ("Biz", lst[1].mailbox)
    ok_ ("biz@kontsevoy.com" in lst)

    # test case-sensitivity: hostname must be lowercased, but the local-part needs
    # to remain case-sensitive
    ok_ ("Biz@kontsevoy.com" in str(lst))

    # check parsing:
    spec = '''http://foo.com:8080, "Ev K." <ev@host.com>, "Alex K" alex@yahoo.net; "Tom, S" "tom+[a]"@s.com'''
    lst = parse_list(spec, True)

    eq_ (len(lst), 4)
    eq_ ("http://foo.com:8080", lst[0].address)
    eq_ ("ev@host.com", lst[1].address)
    eq_ ("alex@yahoo.net", lst[2].address)
    eq_ ('"tom+[a]"@s.com', lst[3].address)

    # string-based persistence:
    s = str(lst)
    clone = parse_list(s)
    eq_ (lst, clone)

    # now clone using full spec:
    s = lst.full_spec()
    clone = parse_list(s)
    eq_ (lst, clone)

    # hostnames:
    eq_ (set(['host.com', 'foo.com', 'yahoo.net', 's.com']), lst.hostnames)
    eq_ (set(['url', 'email']), lst.addr_types)

    # add:
    result = lst + parse_list("ev@local.net") + ["foo@bar.com"]
    ok_ (isinstance(result, AddressList))
    eq_ (len(result), len(lst)+2)
    ok_ ("foo@bar.com" in result)


def test_addresslist_with_apostrophe():
    s = '''"Allan G\'o"  <allan@example.com>, "Os Wi" <oswi@example.com>'''
    lst = parse_list(s)
    eq_ (2, len(lst))
    eq_ ('"Allan G\'o" <allan@example.com>', lst[0].full_spec())
    eq_ ('"Os Wi" <oswi@example.com>', lst[1].full_spec())
    lst = parse_list("=?UTF-8?Q?Eugueny_=CF=8E_Kontsevoy?= <eugueny@gmail.com>")
    eq_ ('=?UTF-8?Q?Eugueny_=CF=8E_Kontsevoy?= <eugueny@gmail.com>', lst.full_spec())
    eq_ (u'Eugueny ώ Kontsevoy', lst[0].display_name)


def test_edge_cases():
    email = EmailAddress('"foo.bar@"@example.com')
    eq_('"foo.bar@"@example.com', email.address)

########NEW FILE########
__FILENAME__ = corrector_test
# coding:utf-8

import re
import string
import random

from .. import *

from nose.tools import assert_equal, assert_not_equal, ok_
from nose.tools import nottest

from flanker.addresslib import validate
from flanker.addresslib import corrector


COMMENT = re.compile(r'''\s*#''')


@nottest
def generate_mutated_string(source_str, num):
    letters = list(source_str)
    rchars = string.ascii_lowercase.translate(None, source_str + '.')

    random_orig = random.sample(list(enumerate(source_str)), num)
    random_new = random.sample(list(enumerate(rchars)), num)

    for i, j in zip(random_orig, random_new):
        letters[i[0]] = j[1]

    return ''.join(letters)

@nottest
def generate_longer_string(source_str, num):
    letters = list(source_str)
    rchars = string.ascii_lowercase.translate(None, source_str)

    for i in range(num):
        letters = [random.choice(rchars)] + letters

    return ''.join(letters)

@nottest
def generate_shorter_string(source_str, num):
    return source_str[0:len(source_str)-num]

@nottest
def domain_generator(size=6, chars=string.ascii_letters + string.digits):
    domain = ''.join(random.choice(chars) for x in range(size))
    return ''.join([domain, '.com'])


def test_domain_typo_valid_set():
    sugg_correct = 0
    sugg_total = 0
    print ''

    for line in DOMAIN_TYPO_VALID_TESTS.split('\n'):
        # strip line, skip over empty lines
        line = line.strip()
        if line == '':
            continue

        # skip over comments or empty lines
        match = COMMENT.match(line)
        if match:
            continue

        parts = line.split(',')

        test_str = 'username@' + parts[0]
        corr_str = 'username@' + parts[1]
        sugg_str = validate.suggest_alternate(test_str)

        if sugg_str == corr_str:
            sugg_correct += 1
        else:
            print 'did not match: {0}, {1}'.format(test_str, sugg_str)

        sugg_total += 1

    # ensure that we have greater than 90% accuracy
    accuracy = float(sugg_correct) / sugg_total
    print 'external valid: accuracy: {0}, correct: {1}, total: {2}'.\
        format(accuracy, sugg_correct, sugg_total)
    ok_(accuracy > 0.90)


def test_domain_typo_invalid_set():
    sugg_correct = 0
    sugg_total = 0
    print ''

    for line in DOMAIN_TYPO_INVALID_TESTS.split('\n'):
        # strip line, skip over empty lines
        line = line.strip()
        if line == '':
            continue

        # skip over comments or empty lines
        match = COMMENT.match(line)
        if match:
            continue

        test_str = 'username@' + line
        sugg_str = validate.suggest_alternate(test_str)

        if sugg_str == None:
            sugg_correct += 1
        else:
            print 'incorrect correction: {0}, {1}'.format(test_str, sugg_str)

        sugg_total += 1

    # ensure that we have greater than 90% accuracy
    accuracy = float(sugg_correct) / sugg_total
    print 'external invalid: accuracy: {0}, correct: {1}, total: {2}'.\
        format(accuracy, sugg_correct, sugg_total)
    ok_(accuracy > 0.90)


# For the remaining tests, the accuracy is significantly lower than
# the above because the corrector is tuned to real typos that occur,
# while what we have below are random mutations. Also, because
# this these test are non-deterministic, it's better to have a lower
# lower threshold to ensure that tests don't fail dring deployment
# due to a outlier). Realistic numbers for all thees tests should easily
# be above 80% accuracy range.

def test_suggest_alternate_mutations_valid():
    sugg_correct = 0
    sugg_total = 0
    print ''

    for i in range(1, 3):
        for j in range(100):
            domain = random.choice(corrector.MOST_COMMON_DOMAINS)
            orig_str = 'username@' + domain

            mstr = 'username@' + generate_mutated_string(domain, i)
            sugg_str = validate.suggest_alternate(mstr)
            if sugg_str == orig_str:
                sugg_correct += 1

            sugg_total += 1

    # ensure that we have greater than 60% accuracy
    accuracy = float(sugg_correct) / sugg_total
    print 'mutations valid: accuracy: {0}, correct: {1}, total: {2}'.\
        format(accuracy, sugg_correct, sugg_total)
    ok_(accuracy > 0.60)


def test_suggest_alternate_longer_valid():
    sugg_correct = 0
    sugg_total = 0
    print ''

    for i in range(1, 3):
        for j in range(100):
            domain = random.choice(corrector.MOST_COMMON_DOMAINS)
            orig_str = 'username@' + domain

            lstr = 'username@' + generate_longer_string(domain, i)
            sugg_str = validate.suggest_alternate(lstr)
            if sugg_str == orig_str:
                sugg_correct += 1

            sugg_total += 1

    # ensure that we have greater than 60% accuracy
    accuracy = float(sugg_correct) / sugg_total
    print 'longer valid: accuracy: {0}, correct: {1}, total: {2}'.\
        format(accuracy, sugg_correct, sugg_total)
    ok_(accuracy > 0.60)


def test_suggest_alternate_shorter_valid():
    sugg_correct = 0
    sugg_total = 0
    print ''

    for i in range(1, 3):
        for j in range(100):
            domain = random.choice(corrector.MOST_COMMON_DOMAINS)
            orig_str = 'username@' + domain

            sstr = 'username@' + generate_shorter_string(domain, i)
            sugg_str = validate.suggest_alternate(sstr)
            if sugg_str == orig_str:
                sugg_correct += 1

            sugg_total += 1

    # ensure that we have greater than 60% accuracy
    accuracy = float(sugg_correct) / sugg_total
    print 'shorter valid: accuracy: {0}, correct: {1}, total: {2}'.\
        format(accuracy, sugg_correct, sugg_total)
    ok_(accuracy > 0.60)


def test_suggest_alternate_invalid():
    sugg_correct = 0
    sugg_total = 0
    print ''

    for i in range(3, 10):
        for j in range(100):
            domain = domain_generator(i)

            orig_str = 'username@' + domain
            sugg_str = validate.suggest_alternate(orig_str)
            if sugg_str == None:
                sugg_correct += 1
            else:
                print 'did not match: {0}, {1}'.format(orig_str, sugg_str)

            sugg_total += 1

    # ensure that we have greater than 60% accuracy
    accuracy = float(sugg_correct) / sugg_total
    print 'alternative invalid: accuracy: {0}, correct: {1}, total: {2}'.\
        format(accuracy, sugg_correct, sugg_total)
    ok_(accuracy > 0.60)

########NEW FILE########
__FILENAME__ = external_dataset_test
# coding:utf-8

import re

from .. import *

from nose.tools import assert_equal, assert_not_equal
from flanker.addresslib import address

COMMENT = re.compile(r'''\s*#''')


def test_mailbox_valid_set():
    for line in MAILBOX_VALID_TESTS.split('\n'):
        # strip line, skip over empty lines
        line = line.strip()
        if line == '':
            continue

        # skip over comments or empty lines
        match = COMMENT.match(line)
        if match:
            continue

        mbox = address.parse(line)
        assert_not_equal(mbox, None)

def test_mailbox_invalid_set():
    for line in MAILBOX_INVALID_TESTS.split('\n'):
        # strip line, skip over empty lines
        line = line.strip()
        if line == '':
            continue

        # skip over comments
        match = COMMENT.match(line)
        if match:
            continue

        mbox = address.parse(line)
        assert_equal(mbox, None)

def test_url_valid_set():
    for line in URL_VALID_TESTS.split('\n'):
        # strip line, skip over empty lines
        line = line.strip()
        if line == '':
            continue

        # skip over comments or empty lines
        match = COMMENT.match(line)
        if match:
            continue

        mbox = address.parse(line)
        assert_not_equal(mbox, None)

def test_url_invalid_set():
    for line in URL_INVALID_TESTS.split('\n'):
        # strip line, skip over empty lines
        line = line.strip()
        if line == '':
            continue

        # skip over comments
        match = COMMENT.match(line)
        if match:
            continue

        mbox = address.parse(line)
        assert_equal(mbox, None)

########NEW FILE########
__FILENAME__ = metrics_test
# coding:utf-8

from .. import *
from mock import patch
from nose.tools import assert_equal, assert_not_equal
from nose.tools import nottest

from flanker.addresslib import address, validate

@nottest
def mock_exchanger_lookup(arg, metrics=False):
    mtimes = {'mx_lookup': 10, 'dns_lookup': 20, 'mx_conn': 30}
    if metrics is True:
        if arg == 'ai' or arg == 'mailgun.org' or arg == 'fakecompany.mailgun.org':
            return ('', mtimes)
        else:
            return (None, mtimes)
    else:
        if arg == 'ai' or arg == 'mailgun.org' or arg == 'fakecompany.mailgun.org':
            return ''
        else:
            return None


def test_metrics_parse():
    # parse
    assert_equal(len(address.parse('foo@example.com', metrics=True)), 2)
    p, m = address.parse('foo@example.com', metrics=True)
    assert_equal('parsing' in m, True)
    assert_equal(isinstance(address.parse('foo@example.com', metrics=False), address.EmailAddress), True)
    assert_equal(isinstance(address.parse('foo@example.com'), address.EmailAddress), True)

def test_metrics_parse_list():
    # parse_list
    assert_equal(len(address.parse_list('foo@example.com, bar@example.com', metrics=True)), 2)
    p, m = address.parse_list('foo@example.com, bar@example.com', metrics=True)
    assert_equal('parsing' in m, True)
    assert_equal(isinstance(address.parse_list('foo@example.com, bar@example.com', metrics=False), address.AddressList), True)
    assert_equal(isinstance(address.parse_list('foo@example.com, bar@example.com'), address.AddressList), True)

def test_metrics_validate_address():
    # validate
    with patch.object(validate, 'mail_exchanger_lookup') as mock_method:
        mock_method.side_effect = mock_exchanger_lookup

        assert_equal(len(address.validate_address('foo@mailgun.net', metrics=True)), 2)
        p, m = address.validate_address('foo@mailgun.net', metrics=True)
        assert_equal('parsing' in m, True)
        assert_equal('mx_lookup' in m, True)
        assert_equal('dns_lookup' in m, True)
        assert_equal('mx_conn' in m, True)
        assert_equal('custom_grammar' in m, True)
        assert_equal(isinstance(address.validate_address('foo@mailgun.org', metrics=False), address.EmailAddress), True)
        assert_equal(isinstance(address.validate_address('foo@mailgun.org'), address.EmailAddress), True)

def test_metrics_validate_list():
    # validate_list
    with patch.object(validate, 'mail_exchanger_lookup') as mock_method:
        mock_method.side_effect = mock_exchanger_lookup

        assert_equal(len(address.validate_list('foo@mailgun.org, bar@mailgun.org', metrics=True)), 2)
        p, m = address.validate_list('foo@mailgun.org, bar@mailgun.org', metrics=True)
        assert_equal('parsing' in m, True)
        assert_equal('mx_lookup' in m, True)
        assert_equal('dns_lookup' in m, True)
        assert_equal('mx_conn' in m, True)
        assert_equal('custom_grammar' in m, True)
        assert_equal(isinstance(address.validate_list('foo@mailgun.org, bar@mailgun.org', metrics=False), address.AddressList), True)
        assert_equal(isinstance(address.validate_list('foo@mailgun.org, bar@mailgun.org'), address.AddressList), True)

########NEW FILE########
__FILENAME__ = parser_address_list_test
# coding:utf-8

from itertools import chain, combinations, permutations

from nose.tools import assert_equal, assert_not_equal
from nose.tools import nottest

from flanker.addresslib import address
from flanker.addresslib.address import EmailAddress, AddressList


@nottest
def powerset(iterable):
    "powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s)+1))

@nottest
def run_relaxed_test(string, expected_mlist, expected_unpar):
    mlist, unpar = address.parse_list(string, strict=False, as_tuple=True)
    assert_equal(mlist, expected_mlist)
    assert_equal(unpar, expected_unpar)

@nottest
def run_strict_test(string, expected_mlist):
    mlist = address.parse_list(string, strict=True)
    assert_equal(mlist, expected_mlist)


BILL_AS = EmailAddress(None, 'bill@microsoft.com')
STEVE_AS = EmailAddress(None, 'steve@apple.com')
LINUS_AS = EmailAddress(None, 'torvalds@kernel.org')

BILL_MBX = EmailAddress('Bill Gates', 'bill@microsoft.com')
STEVE_MBX = EmailAddress('Steve Jobs', 'steve@apple.com')
LINUS_MBX = EmailAddress('Linus Torvalds', 'torvalds@kernel.org')


def test_sanity():
    addr_string = 'Bill Gates <bill@microsoft.com>, Steve Jobs <steve@apple.com>; torvalds@kernel.org'
    run_relaxed_test(addr_string, [BILL_MBX, STEVE_MBX, LINUS_AS], [])
    run_strict_test(addr_string,  [BILL_MBX, STEVE_MBX, LINUS_AS])


def test_simple_valid():
    s = '''http://foo.com:8080; "Ev K." <ev@host.com>, "Alex K" alex@yahoo.net, "Tom, S" "tom+[a]"@s.com'''
    addrs = address.parse_list(s)

    assert_equal(4, len(addrs))

    assert_equal(addrs[0].addr_type, 'url')
    assert_equal(addrs[0].address, 'http://foo.com:8080')
    assert_equal(addrs[0].full_spec(), 'http://foo.com:8080')

    assert_equal(addrs[1].addr_type, 'email')
    assert_equal(addrs[1].display_name, '"Ev K."')
    assert_equal(addrs[1].address, 'ev@host.com')
    assert_equal(addrs[1].full_spec(), '"Ev K." <ev@host.com>')

    assert_equal(addrs[2].addr_type, 'email')
    assert_equal(addrs[2].display_name, '"Alex K"')
    assert_equal(addrs[2].address, 'alex@yahoo.net')
    assert_equal(addrs[2].full_spec(), '"Alex K" <alex@yahoo.net>')

    assert_equal(addrs[3].addr_type, 'email')
    assert_equal(addrs[3].display_name, '"Tom, S"')
    assert_equal(addrs[3].address, '"tom+[a]"@s.com')
    assert_equal(addrs[3].full_spec(), '"Tom, S" <"tom+[a]"@s.com>')


    s = '''"Allan G\'o"  <allan@example.com>, "Os Wi" <oswi@example.com>'''
    addrs = address.parse_list(s)

    assert_equal(2, len(addrs))

    assert_equal(addrs[0].addr_type, 'email')
    assert_equal(addrs[0].display_name, '"Allan G\'o"')
    assert_equal(addrs[0].address, 'allan@example.com')
    assert_equal(addrs[0].full_spec(), '"Allan G\'o" <allan@example.com>')

    assert_equal(addrs[1].addr_type, 'email')
    assert_equal(addrs[1].display_name, '"Os Wi"')
    assert_equal(addrs[1].address, 'oswi@example.com')
    assert_equal(addrs[1].full_spec(), '"Os Wi" <oswi@example.com>')


    s = u'''I am also A <a@HOST.com>, Zeka <EV@host.coM> ;Gonzalo Bañuelos<gonz@host.com>'''
    addrs = address.parse_list(s)

    assert_equal(3, len(addrs))

    assert_equal(addrs[0].addr_type, 'email')
    assert_equal(addrs[0].display_name, 'I am also A')
    assert_equal(addrs[0].address, 'a@host.com')
    assert_equal(addrs[0].full_spec(), 'I am also A <a@host.com>')

    assert_equal(addrs[1].addr_type, 'email')
    assert_equal(addrs[1].display_name, 'Zeka')
    assert_equal(addrs[1].address, 'EV@host.com')
    assert_equal(addrs[1].full_spec(), 'Zeka <EV@host.com>')

    assert_equal(addrs[2].addr_type, 'email')
    assert_equal(addrs[2].display_name, u'Gonzalo Bañuelos')
    assert_equal(addrs[2].address, 'gonz@host.com')
    assert_equal(addrs[2].full_spec(), '=?utf-8?q?Gonzalo_Ba=C3=B1uelos?= <gonz@host.com>')


    s = r'''"Escaped" "\e\s\c\a\p\e\d"@sld.com; http://userid:password@example.com:8080, "Dmitry" <my|'`!#_~%$&{}?^+-*@host.com>'''
    addrs = address.parse_list(s)

    assert_equal(3, len(addrs))

    assert_equal(addrs[0].addr_type, 'email')
    assert_equal(addrs[0].display_name, '"Escaped"')
    assert_equal(addrs[0].address, '"\e\s\c\\a\p\e\d"@sld.com')
    assert_equal(addrs[0].full_spec(), '"Escaped" <"\e\s\c\\a\p\e\d"@sld.com>')

    assert_equal(addrs[1].addr_type, 'url')
    assert_equal(addrs[1].address, 'http://userid:password@example.com:8080')
    assert_equal(addrs[1].full_spec(), 'http://userid:password@example.com:8080')

    assert_equal(addrs[2].addr_type, 'email')
    assert_equal(addrs[2].display_name, '"Dmitry"')
    assert_equal(addrs[2].address, 'my|\'`!#_~%$&{}?^+-*@host.com')
    assert_equal(addrs[2].full_spec(), '"Dmitry" <my|\'`!#_~%$&{}?^+-*@host.com>')


    s = "http://foo.com/blah_blah_(wikipedia)"
    addrs = address.parse_list(s)

    assert_equal(1, len(addrs))

    assert_equal(addrs[0].addr_type, 'url')
    assert_equal(addrs[0].address, 'http://foo.com/blah_blah_(wikipedia)')
    assert_equal(addrs[0].full_spec(), 'http://foo.com/blah_blah_(wikipedia)')


    s = "Sasha Klizhentas <klizhentas@gmail.com>"
    addrs = address.parse_list(s)

    assert_equal(1, len(addrs))

    assert_equal(addrs[0].addr_type, 'email')
    assert_equal(addrs[0].display_name, 'Sasha Klizhentas')
    assert_equal(addrs[0].address, 'klizhentas@gmail.com')
    assert_equal(addrs[0].full_spec(), 'Sasha Klizhentas <klizhentas@gmail.com>')


    s = "admin@mailgunhq.com,lift@example.com"
    addrs = address.parse_list(s)

    assert_equal(2, len(addrs))

    assert_equal(addrs[0].addr_type, 'email')
    assert_equal(addrs[0].display_name, '')
    assert_equal(addrs[0].address, 'admin@mailgunhq.com')
    assert_equal(addrs[0].full_spec(), 'admin@mailgunhq.com')

    assert_equal(addrs[1].addr_type, 'email')
    assert_equal(addrs[1].display_name, '')
    assert_equal(addrs[1].address, 'lift@example.com')
    assert_equal(addrs[1].full_spec(), 'lift@example.com')


def test_simple_invalid():
    s = '''httd://foo.com:8080\r\n; "Ev K." <ev@ host.com>\n "Alex K" alex@ , "Tom, S" "tom+["  a]"@s.com'''
    assert_equal(address.AddressList(), address.parse_list(s))

    s = ""
    assert_equal(address.AddressList(), address.parse_list(s))

    s = "crap"
    assert_equal(address.AddressList(), address.parse_list(s))


def test_endpoints():
    # expected result: [foo@example.com, baz@example.com]
    presult = address.parse_list('foo@example.com, bar, baz@example.com', strict=False, as_tuple=False)
    assert isinstance(presult, AddressList)
    assert_equal(2, len(presult))

    # expected result: ([foo@example.com, baz@example.com], ['bar'])
    presult = address.parse_list('foo@example.com, bar, baz@example.com', strict=False, as_tuple=True)
    assert type(presult) is tuple
    assert_equal(2, len(presult[0]))
    assert_equal(1, len(presult[1]))

    # expected result: [foo@example.com]
    presult = address.parse_list('foo@example.com, bar, baz@example.com', strict=True, as_tuple=False)
    assert isinstance(presult, AddressList)
    assert_equal(1, len(presult))

    # expected result: ([foo@example.com], [])
    presult = address.parse_list('foo@example.com, bar, baz@example.com', strict=True, as_tuple=True)
    assert type(presult) is tuple
    assert_equal(1, len(presult[0]))
    assert_equal(0, len(presult[1]))


def test_delimiters_relaxed():
    # permutations
    for e in permutations('  ,,;;'):
        addr_string = 'bill@microsoft.com' + ''.join(e) + 'steve@apple.com, torvalds@kernel.org'
        run_relaxed_test(addr_string, [BILL_AS, STEVE_AS, LINUS_AS], [])

    # powerset
    for e in powerset('  ,,;;'):
        # empty sets will be tested by the synchronize tests
        if ''.join(e).strip() == '':
            continue

        addr_string = 'bill@microsoft.com' + ''.join(e) + 'steve@apple.com, torvalds@kernel.org'
        run_relaxed_test(addr_string, [BILL_AS, STEVE_AS, LINUS_AS], [])

def test_delimiters_strict():
    # permutations
    for e in permutations('  ,,;;'):
        addr_string = 'bill@microsoft.com' + ''.join(e) + 'steve@apple.com, torvalds@kernel.org'
        run_strict_test(addr_string, [BILL_AS, STEVE_AS, LINUS_AS])

    # powerset
    for e in powerset('  ,,;;'):
        # empty sets will be tested by the synchronize tests
        if ''.join(e).strip() == '':
            continue

        addr_string = 'bill@microsoft.com' + ''.join(e) + 'steve@apple.com, torvalds@kernel.org'
        run_strict_test(addr_string, [BILL_AS, STEVE_AS, LINUS_AS])


def test_synchronize_relaxed():
    run_relaxed_test('"@microsoft.com, steve@apple.com', [STEVE_AS], ['"@microsoft.com'])
    run_relaxed_test('"@microsoft.com steve@apple.com', [], ['"@microsoft.com steve@apple.com'])
    run_relaxed_test('"@microsoft.comsteve@apple.com', [], ['"@microsoft.comsteve@apple.com'])

    run_relaxed_test('bill@microsoft.com, steve, torvalds@kernel.org', [BILL_AS, LINUS_AS], ['steve'])
    run_relaxed_test('bill@microsoft.com, steve torvalds', [BILL_AS], ['steve torvalds'])

    run_relaxed_test('bill;  ', [], ['bill'])
    run_relaxed_test('bill ;', [], ['bill '])
    run_relaxed_test('bill ; ', [], ['bill '])

    run_relaxed_test('bill@microsoft.com;  ', [BILL_AS],  [])
    run_relaxed_test('bill@microsoft.com ;', [BILL_AS], [])
    run_relaxed_test('bill@microsoft.com ; ', [BILL_AS], [] )

    run_relaxed_test('bill; steve; linus', [], ['bill', 'steve', 'linus'])

    run_relaxed_test(',;@microsoft.com, steve@apple.com', [STEVE_AS], ['@microsoft.com'])
    run_relaxed_test(',;"@microsoft.comsteve@apple.com', [], ['"@microsoft.comsteve@apple.com'])


def test_synchronize_strict():
    run_strict_test('"@microsoft.com, steve@apple.com', [])
    run_strict_test('"@microsoft.com steve@apple.com', [])
    run_strict_test('"@microsoft.comsteve@apple.com', [])

    run_strict_test('bill@microsoft.com, steve, torvalds@kernel.org', [BILL_AS])
    run_strict_test('bill@microsoft.com, steve torvalds', [BILL_AS])

    run_strict_test('bill;  ', [])
    run_strict_test('bill ;', [])
    run_strict_test('bill ; ', [])

    run_strict_test('bill@microsoft.com;  ', [BILL_AS])
    run_strict_test('bill@microsoft.com ;', [BILL_AS])
    run_strict_test('bill@microsoft.com ; ', [BILL_AS])

    run_strict_test('bill; steve; linus', [])

    run_strict_test(',;@microsoft.com, steve@apple.com', [])
    run_strict_test('",;@microsoft.com steve@apple.com', [])
    run_strict_test(',;"@microsoft.comsteve@apple.com', [])

########NEW FILE########
__FILENAME__ = parser_mailbox_test
# coding:utf-8

from nose.tools import assert_equal, assert_not_equal
from nose.tools import nottest

from flanker.addresslib import address
from flanker.addresslib.address import EmailAddress
from flanker.addresslib.parser import ParserException

VALID_QTEXT         = [chr(x) for x in [0x21] + range(0x23, 0x5b) + range(0x5d, 0x7e)]
VALID_QUOTED_PAIR   = [chr(x) for x in range(0x20, 0x7e)]

FULL_QTEXT = ''.join(VALID_QTEXT)
FULL_QUOTED_PAIR = '\\' + '\\'.join(VALID_QUOTED_PAIR)

CONTROL_CHARS = ''.join(map(unichr, range(0, 9) + range(14, 32) + range(127, 160)))

@nottest
def chunks(l, n):
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

@nottest
def run_full_mailbox_test(string, expected, full_spec=None):
    mbox = address.parse(string)
    if mbox:
        assert_equal(mbox.display_name, expected.display_name)
        assert_equal(mbox.address, expected.address)
        if full_spec:
            assert_equal(mbox.full_spec(), full_spec)
        return
    assert_equal(mbox, expected)

@nottest
def run_mailbox_test(string, expected_string):
    mbox = address.parse(string)
    if mbox:
        assert_equal(mbox.address, expected_string)
        return
    assert_equal(mbox, expected_string)


def test_mailbox():
    "Grammar: mailbox -> name-addr | addr-spec"

    # sanity
    run_full_mailbox_test('Steve Jobs <steve@apple.com>', EmailAddress('Steve Jobs', 'steve@apple.com'))
    run_full_mailbox_test('"Steve Jobs" <steve@apple.com>', EmailAddress('"Steve Jobs"', 'steve@apple.com'))
    run_mailbox_test('<steve@apple.com>', 'steve@apple.com')

    run_full_mailbox_test('Steve Jobs steve@apple.com', EmailAddress('Steve Jobs', 'steve@apple.com'))
    run_full_mailbox_test('"Steve Jobs" steve@apple.com', EmailAddress('"Steve Jobs"', 'steve@apple.com'))
    run_mailbox_test('steve@apple.com', 'steve@apple.com')


def test_name_addr():
    "Grammar: name-addr -> [ display-name ] angle-addr"

    # sanity
    run_full_mailbox_test('Linus Torvalds linus@kernel.org', EmailAddress('Linus Torvalds','linus@kernel.org'))
    run_full_mailbox_test('Linus Torvalds <linus@kernel.org>', EmailAddress('Linus Torvalds','linus@kernel.org'))
    run_mailbox_test('Linus Torvalds', None)
    run_mailbox_test('Linus Torvalds <>', None)
    run_mailbox_test('linus@kernel.org', 'linus@kernel.org')
    run_mailbox_test('<linus@kernel.org>', 'linus@kernel.org')
    try:
        run_mailbox_test(' ', None)
    except ParserException:
        pass


def test_display_name():
    "Grammar: display-name -> word { [ whitespace ] word }"

    # pass atom display-name rfc
    run_full_mailbox_test('ABCDEFGHIJKLMNOPQRSTUVWXYZ <a@b>', EmailAddress('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'a@b'))
    run_full_mailbox_test('abcdefghijklmnopqrstuvwzyz <a@b>', EmailAddress('abcdefghijklmnopqrstuvwzyz', 'a@b'))
    run_full_mailbox_test('0123456789 <a@b>', EmailAddress('0123456789', 'a@b'))
    run_full_mailbox_test('!#$%&\'*+-/=?^_`{|}~ <a@b>', EmailAddress('!#$%&\'*+-/=?^_`{|}~', 'a@b'))
    run_full_mailbox_test('Bill <bill@microsoft.com>', EmailAddress('Bill', 'bill@microsoft.com'))
    run_full_mailbox_test('Bill Gates <bill@microsoft.com>', EmailAddress('Bill Gates', 'bill@microsoft.com'))
    run_full_mailbox_test(' Bill  Gates <bill@microsoft.com>', EmailAddress('Bill  Gates', 'bill@microsoft.com'))
    run_full_mailbox_test(' Bill Gates <bill@microsoft.com>', EmailAddress('Bill Gates', 'bill@microsoft.com'))
    run_full_mailbox_test('Bill Gates<bill@microsoft.com>', EmailAddress('Bill Gates', 'bill@microsoft.com'))
    run_full_mailbox_test(' Bill Gates<bill@microsoft.com>', EmailAddress('Bill Gates', 'bill@microsoft.com'))
    run_full_mailbox_test(' Bill<bill@microsoft.com>', EmailAddress('Bill', 'bill@microsoft.com'))

    # pass atom display-name lax
    run_full_mailbox_test('ABCDEFGHIJKLMNOPQRSTUVWXYZ a@b', EmailAddress('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'a@b'))
    run_full_mailbox_test('abcdefghijklmnopqrstuvwzyz a@b', EmailAddress('abcdefghijklmnopqrstuvwzyz', 'a@b'))
    run_full_mailbox_test('0123456789 a@b', EmailAddress('0123456789', 'a@b'))
    run_full_mailbox_test('!#$%&\'*+-/=?^_`{|}~ a@b', EmailAddress('!#$%&\'*+-/=?^_`{|}~', 'a@b'))
    run_full_mailbox_test('Bill bill@microsoft.com', EmailAddress('Bill', 'bill@microsoft.com'))
    run_full_mailbox_test('Bill Gates bill@microsoft.com', EmailAddress('Bill Gates', 'bill@microsoft.com'))
    run_full_mailbox_test(' Bill  Gates bill@microsoft.com', EmailAddress('Bill  Gates', 'bill@microsoft.com'))
    run_full_mailbox_test(' Bill Gates bill@microsoft.com', EmailAddress('Bill Gates', 'bill@microsoft.com'))


    # fail atom display-name rfc
    run_full_mailbox_test('< <bill@microsoft.com>', None)
    run_full_mailbox_test('< bill <bill@microsoft.com>', None)
    run_full_mailbox_test(' < bill <bill@microsoft.com>', None)

    # fail atom display-name lax
    run_full_mailbox_test('< bill@microsoft.com', None)
    run_full_mailbox_test('< bill bill@microsoft.com', None)
    run_full_mailbox_test(' < bill @microsoft.com', None)


    # pass display-name quoted-string rfc
    run_full_mailbox_test('"{0}" <a@b>'.format(FULL_QTEXT), EmailAddress('"' + FULL_QTEXT + '"', 'a@b'))
    run_full_mailbox_test('"{0}" <a@b>'.format(FULL_QUOTED_PAIR), EmailAddress('"' + FULL_QUOTED_PAIR + '"', 'a@b'))
    run_full_mailbox_test('"<a@b>" <a@b>', EmailAddress('"<a@b>"', 'a@b'))
    run_full_mailbox_test('"Bill" <bill@microsoft.com>', EmailAddress('"Bill"', 'bill@microsoft.com'))
    run_full_mailbox_test('"Bill Gates" <bill@microsoft.com>', EmailAddress('"Bill Gates"', 'bill@microsoft.com'))
    run_full_mailbox_test('" Bill Gates" <bill@microsoft.com>', EmailAddress('" Bill Gates"', 'bill@microsoft.com'))
    run_full_mailbox_test('"Bill Gates " <bill@microsoft.com>', EmailAddress('"Bill Gates "', 'bill@microsoft.com'))
    run_full_mailbox_test('" Bill Gates " <bill@microsoft.com>', EmailAddress('" Bill Gates "', 'bill@microsoft.com'))
    run_full_mailbox_test(' " Bill Gates "<bill@microsoft.com>', EmailAddress('" Bill Gates "', 'bill@microsoft.com'))

    # fail display-name quoted-string rfc
    run_mailbox_test('"{0} <a@b>"'.format(FULL_QUOTED_PAIR), None)
    run_mailbox_test('"{0} <a@b>'.format(FULL_QTEXT), None)
    run_mailbox_test('{0}" <a@b>'.format(FULL_QUOTED_PAIR), None)
    run_mailbox_test('{0} <a@b>'.format(FULL_QUOTED_PAIR), None)
    run_mailbox_test(u'{0} <a@b>'.format(''.join(CONTROL_CHARS)), None)
    run_mailbox_test(u'"{0}" <a@b>'.format(''.join(CONTROL_CHARS)), None)
    for cc in CONTROL_CHARS:
        run_mailbox_test(u'"{0}" <a@b>'.format(cc), None)
        run_mailbox_test(u'{0} <a@b>'.format(cc), None)

    # pass display-name quoted-string lax
    run_full_mailbox_test('"{0}" a@b'.format(FULL_QTEXT), EmailAddress('"' + FULL_QTEXT + '"', 'a@b'))
    run_full_mailbox_test('"{0}" a@b'.format(FULL_QUOTED_PAIR), EmailAddress('"' + FULL_QUOTED_PAIR + '"', 'a@b'))
    run_full_mailbox_test('"a@b" a@b', EmailAddress('"a@b"', 'a@b'))
    run_full_mailbox_test('"Bill" bill@microsoft.com', EmailAddress('"Bill"', 'bill@microsoft.com'))
    run_full_mailbox_test('"Bill Gates" bill@microsoft.com', EmailAddress('"Bill Gates"', 'bill@microsoft.com'))
    run_full_mailbox_test('" Bill Gates" bill@microsoft.com', EmailAddress('" Bill Gates"', 'bill@microsoft.com'))
    run_full_mailbox_test('"Bill Gates " bill@microsoft.com', EmailAddress('"Bill Gates "', 'bill@microsoft.com'))
    run_full_mailbox_test('" Bill Gates " bill@microsoft.com', EmailAddress('" Bill Gates "', 'bill@microsoft.com'))

    # fail display-name quoted-string lax
    run_mailbox_test('"Bill Gates"bill@microsoft.com', None)
    run_mailbox_test('"{0} a@b"'.format(FULL_QUOTED_PAIR), None)
    run_mailbox_test('"{0} a@b'.format(FULL_QTEXT), None)
    run_mailbox_test('{0}" a@b'.format(FULL_QUOTED_PAIR), None)
    run_mailbox_test('{0} a@b'.format(FULL_QUOTED_PAIR), None)
    run_mailbox_test(u'{0} a@b'.format(''.join(CONTROL_CHARS)), None)
    run_mailbox_test(u'"{0}" a@b'.format(''.join(CONTROL_CHARS)), None)
    for cc in CONTROL_CHARS:
        run_mailbox_test(u'{0} a@b'.format(cc), None)
        run_mailbox_test(u'"{0}" a@b'.format(cc), None)

    # pass unicode display-name sanity
    run_full_mailbox_test(u'Bill <bill@microsoft.com>', EmailAddress(u'Bill', 'bill@microsoft.com'))
    run_full_mailbox_test(u'ϐill <bill@microsoft.com>', EmailAddress(u'ϐill', 'bill@microsoft.com'))
    run_full_mailbox_test(u'ϐΙλλ <bill@microsoft.com>', EmailAddress(u'ϐΙλλ', 'bill@microsoft.com'))
    run_full_mailbox_test(u'ϐΙλλ Γαθεσ <bill@microsoft.com>', EmailAddress(u'ϐΙλλ Γαθεσ', 'bill@microsoft.com'))
    run_full_mailbox_test(u'BΙλλ Γαθεσ <bill@microsoft.com>', EmailAddress(u'BΙλλ Γαθεσ', 'bill@microsoft.com'))
    run_full_mailbox_test(u'Bill Γαθεσ <bill@microsoft.com>', EmailAddress(u'Bill Γαθεσ', 'bill@microsoft.com'))

    # fail unicode display-name, sanity
    run_mailbox_test('ϐΙλλ Γαθεσ <bill@microsoft.com>', None)


def test_unicode_display_name():
    # unicode, no quotes, display-name rfc
    run_full_mailbox_test(u'ö <{0}>'.format(u'foo@example.com'),
        EmailAddress(u'ö', 'foo@example.com'), '=?utf-8?b?w7Y=?= <foo@example.com>')
    run_full_mailbox_test(u'Föö <{0}>'.format(u'foo@example.com'),
        EmailAddress(u'Föö', 'foo@example.com'), '=?utf-8?b?RsO2w7Y=?= <foo@example.com>')
    run_full_mailbox_test(u'Foo ö <{0}>'.format(u'foo@example.com'),
        EmailAddress(u'Foo ö', 'foo@example.com'), '=?utf-8?b?Rm9vIMO2?= <foo@example.com>')
    run_full_mailbox_test(u'Foo Föö <{0}>'.format(u'foo@example.com'),
        EmailAddress(u'Foo Föö', 'foo@example.com'), '=?utf-8?b?Rm9vIEbDtsO2?= <foo@example.com>')
    run_full_mailbox_test(u'Foo Föö Foo <{0}>'.format(u'foo@example.com'),
        EmailAddress(u'Foo Föö Foo', 'foo@example.com'), '=?utf-8?b?Rm9vIEbDtsO2IEZvbw==?= <foo@example.com>')
    run_full_mailbox_test(u'Foo Föö Foo Föö <{0}>'.format(u'foo@example.com'),
        EmailAddress(u'Foo Föö Foo Föö', 'foo@example.com'), '=?utf-8?b?Rm9vIEbDtsO2IEZvbyBGw7bDtg==?= <foo@example.com>')

    # unicode, no quotes, display-name lax
    run_full_mailbox_test(u'ö {0}'.format(u'foo@example.com'),
        EmailAddress(u'ö', 'foo@example.com'), '=?utf-8?b?w7Y=?= <foo@example.com>')
    run_full_mailbox_test(u'Föö {0}'.format(u'foo@example.com'),
        EmailAddress(u'Föö', 'foo@example.com'), '=?utf-8?b?RsO2w7Y=?= <foo@example.com>')
    run_full_mailbox_test(u'Foo ö {0}'.format(u'foo@example.com'),
        EmailAddress(u'Foo ö', 'foo@example.com'), '=?utf-8?b?Rm9vIMO2?= <foo@example.com>')
    run_full_mailbox_test(u'Foo Föö {0}'.format(u'foo@example.com'),
        EmailAddress(u'Foo Föö', 'foo@example.com'), '=?utf-8?b?Rm9vIEbDtsO2?= <foo@example.com>')
    run_full_mailbox_test(u'Foo Föö Foo {0}'.format(u'foo@example.com'),
        EmailAddress(u'Foo Föö Foo', 'foo@example.com'), '=?utf-8?b?Rm9vIEbDtsO2IEZvbw==?= <foo@example.com>')
    run_full_mailbox_test(u'Foo Föö Foo Föö {0}'.format(u'foo@example.com'),
        EmailAddress(u'Foo Föö Foo Föö', 'foo@example.com'), '=?utf-8?b?Rm9vIEbDtsO2IEZvbyBGw7bDtg==?= <foo@example.com>')


    # unicode, quotes, display-name rfc
    run_full_mailbox_test(u'"ö" <{0}>'.format(u'foo@example.com'),
        EmailAddress(u'"ö"', 'foo@example.com'), '"=?utf-8?b?w7Y=?=" <foo@example.com>')
    run_full_mailbox_test(u'"Föö" <{0}>'.format(u'foo@example.com'),
        EmailAddress(u'"Föö"', 'foo@example.com'), '"=?utf-8?b?RsO2w7Y=?=" <foo@example.com>')
    run_full_mailbox_test(u'"Foo ö" <{0}>'.format(u'foo@example.com'),
        EmailAddress(u'"Foo ö"', 'foo@example.com'), '"=?utf-8?b?Rm9vIMO2?=" <foo@example.com>')
    run_full_mailbox_test(u'"Foo Föö" <{0}>'.format(u'foo@example.com'),
        EmailAddress(u'"Foo Föö"', 'foo@example.com'), '"=?utf-8?b?Rm9vIEbDtsO2?=" <foo@example.com>')
    run_full_mailbox_test(u'"Foo Föö Foo" <{0}>'.format(u'foo@example.com'),
        EmailAddress(u'"Foo Föö Foo"', 'foo@example.com'), '"=?utf-8?b?Rm9vIEbDtsO2IEZvbw==?=" <foo@example.com>')
    run_full_mailbox_test(u'"Foo Föö Foo Föö" <{0}>'.format(u'foo@example.com'),
        EmailAddress(u'"Foo Föö Foo Föö"', 'foo@example.com'), '"=?utf-8?b?Rm9vIEbDtsO2IEZvbyBGw7bDtg==?=" <foo@example.com>')

    # unicode, quotes, display-name lax
    run_full_mailbox_test(u'"ö" {0}'.format(u'foo@example.com'),
        EmailAddress(u'"ö"', 'foo@example.com'), '"=?utf-8?b?w7Y=?=" <foo@example.com>')
    run_full_mailbox_test(u'"Föö" {0}'.format(u'foo@example.com'),
        EmailAddress(u'"Föö"', 'foo@example.com'), '"=?utf-8?b?RsO2w7Y=?=" <foo@example.com>')
    run_full_mailbox_test(u'"Foo ö" {0}'.format(u'foo@example.com'),
        EmailAddress(u'"Foo ö"', 'foo@example.com'), '"=?utf-8?b?Rm9vIMO2?=" <foo@example.com>')
    run_full_mailbox_test(u'"Foo Föö" {0}'.format(u'foo@example.com'),
        EmailAddress(u'"Foo Föö"', 'foo@example.com'), '"=?utf-8?b?Rm9vIEbDtsO2?=" <foo@example.com>')
    run_full_mailbox_test(u'"Foo Föö Foo" {0}'.format(u'foo@example.com'),
        EmailAddress(u'"Foo Föö Foo"', 'foo@example.com'), '"=?utf-8?b?Rm9vIEbDtsO2IEZvbw==?=" <foo@example.com>')
    run_full_mailbox_test(u'"Foo Föö Foo Föö" {0}'.format(u'foo@example.com'),
        EmailAddress(u'"Foo Föö Foo Föö"', 'foo@example.com'), '"=?utf-8?b?Rm9vIEbDtsO2IEZvbyBGw7bDtg==?=" <foo@example.com>')


    # unicode, random language sampling, see: http://www.columbia.edu/~fdc/utf8/index.html
    run_full_mailbox_test(u'나는 유리를 먹을 수 있어요 <foo@example.com>',
        EmailAddress(u'나는 유리를 먹을 수 있어요', 'foo@example.com'),
        '=?utf-8?b?64KY64qUIOycoOumrOulvCDrqLnsnYQg7IiYIOyeiOyWtOyalA==?= <foo@example.com>')
    run_full_mailbox_test(u'私はガラスを食べられます <foo@example.com>',
        EmailAddress(u'私はガラスを食べられます', 'foo@example.com'),
        '=?utf-8?b?56eB44Gv44Ks44Op44K544KS6aOf44G544KJ44KM44G+44GZ?= <foo@example.com>')
    run_full_mailbox_test(u'ᛖᚴ ᚷᛖᛏ ᛖᛏᛁ <foo@example.com>',
        EmailAddress(u'ᛖᚴ ᚷᛖᛏ ᛖᛏᛁ', 'foo@example.com'),
        '=?utf-8?b?4ZuW4Zq0IOGat+GbluGbjyDhm5bhm4/hm4E=?= <foo@example.com>')
    run_full_mailbox_test(u'Falsches Üben von Xylophonmusik <foo@example.com>',
        EmailAddress(u'Falsches Üben von Xylophonmusik', 'foo@example.com'),
        '=?utf-8?q?Falsches_=C3=9Cben_von_Xylophonmusik?= <foo@example.com>')
    run_full_mailbox_test(u'Съешь же ещё этих <foo@example.com>',
        EmailAddress(u'Съешь же ещё этих', 'foo@example.com'),
        '=?utf-8?b?0KHRitC10YjRjCDQttC1INC10YnRkSDRjdGC0LjRhQ==?= <foo@example.com>')
    run_full_mailbox_test(u'ξεσκεπάζω την <foo@example.com>',
        EmailAddress(u'ξεσκεπάζω την', 'foo@example.com'),
        '=?utf-8?b?zr7Otc+DzrrOtc+AzqzOts+JIM+EzrfOvQ==?= <foo@example.com>')

    # unicode, no quotes, punctuation
    for i in u'''.!#$%&*+-/=?^_`{|}~''':
        run_full_mailbox_test(u'ö {0} <foo@example.com>'.format(i),
            EmailAddress(u'ö {0}'.format(i), 'foo@example.com'))

    # unicode, quotes, punctuation
    for i in u'''.!#$%&*+-/=?^_`{|}~''':
        run_full_mailbox_test(u'"ö {0}" <foo@example.com>'.format(i),
            EmailAddress(u'"ö {0}"'.format(i), 'foo@example.com'))


def test_unicode_special_chars():
    # unicode, special chars, no quotes
    run_full_mailbox_test(u'foo © bar <foo@example.com>',
        EmailAddress(u'foo © bar', 'foo@example.com'),
        '=?utf-8?q?foo_=C2=A9_bar?= <foo@example.com>')
    run_full_mailbox_test(u'foo œ bar <foo@example.com>',
        EmailAddress(u'foo œ bar', 'foo@example.com'),
        '=?utf-8?q?foo_=C5=93_bar?= <foo@example.com>')
    run_full_mailbox_test(u'foo – bar <foo@example.com>',
        EmailAddress(u'foo – bar', 'foo@example.com'),
        '=?utf-8?b?Zm9vIOKAkyBiYXI=?= <foo@example.com>')
    run_full_mailbox_test(u'foo Ǽ bar <foo@example.com>',
        EmailAddress(u'foo Ǽ bar', 'foo@example.com'),
        '=?utf-8?q?foo_=C7=BC_bar?= <foo@example.com>')
    run_full_mailbox_test(u'foo ₤ bar <foo@example.com>',
        EmailAddress(u'foo ₤ bar', 'foo@example.com'),
        '=?utf-8?b?Zm9vIOKCpCBiYXI=?= <foo@example.com>')
    run_full_mailbox_test(u'foo Ω bar <foo@example.com>',
        EmailAddress(u'foo Ω bar', 'foo@example.com'),
        '=?utf-8?b?Zm9vIOKEpiBiYXI=?= <foo@example.com>')
    run_full_mailbox_test(u'foo ↵ bar <foo@example.com>',
        EmailAddress(u'foo ↵ bar', 'foo@example.com'),
        '=?utf-8?b?Zm9vIOKGtSBiYXI=?= <foo@example.com>')
    run_full_mailbox_test(u'foo ∑ bar <foo@example.com>',
        EmailAddress(u'foo ∑ bar', 'foo@example.com'),
        '=?utf-8?b?Zm9vIOKIkSBiYXI=?= <foo@example.com>')
    run_full_mailbox_test(u'foo ⏲ bar <foo@example.com>',
        EmailAddress(u'foo ⏲ bar', 'foo@example.com'),
        '=?utf-8?b?Zm9vIOKPsiBiYXI=?= <foo@example.com>')
    run_full_mailbox_test(u'foo Ⓐ bar <foo@example.com>',
        EmailAddress(u'foo Ⓐ bar', 'foo@example.com'),
        '=?utf-8?b?Zm9vIOKStiBiYXI=?= <foo@example.com>')
    run_full_mailbox_test(u'foo ▒ bar <foo@example.com>',
        EmailAddress(u'foo ▒ bar', 'foo@example.com'),
        '=?utf-8?b?Zm9vIOKWkiBiYXI=?= <foo@example.com>')
    run_full_mailbox_test(u'foo ▲ bar <foo@example.com>',
        EmailAddress(u'foo ▲ bar', 'foo@example.com'),
        '=?utf-8?b?Zm9vIOKWsiBiYXI=?= <foo@example.com>')
    run_full_mailbox_test(u'foo ⚔ bar <foo@example.com>',
        EmailAddress(u'foo ⚔ bar', 'foo@example.com'),
        '=?utf-8?b?Zm9vIOKalCBiYXI=?= <foo@example.com>')
    run_full_mailbox_test(u'foo ✎ bar <foo@example.com>',
        EmailAddress(u'foo ✎ bar', 'foo@example.com'),
        '=?utf-8?b?Zm9vIOKcjiBiYXI=?= <foo@example.com>')
    run_full_mailbox_test(u'foo ⠂ bar <foo@example.com>',
        EmailAddress(u'foo ⠂ bar', 'foo@example.com'),
        '=?utf-8?b?Zm9vIOKggiBiYXI=?= <foo@example.com>')
    run_full_mailbox_test(u'foo ⬀ bar <foo@example.com>',
        EmailAddress(u'foo ⬀ bar', 'foo@example.com'),
        '=?utf-8?b?Zm9vIOKsgCBiYXI=?= <foo@example.com>')
    run_full_mailbox_test(u'foo 💩 bar <foo@example.com>',
        EmailAddress(u'foo 💩 bar', 'foo@example.com'),
        '=?utf-8?b?Zm9vIPCfkqkgYmFy?= <foo@example.com>')

    # unicode, special chars, quotes
    run_full_mailbox_test(u'"foo © bar" <foo@example.com>',
        EmailAddress(u'"foo © bar"', u'foo@example.com'),
        '"=?utf-8?q?foo_=C2=A9_bar?=" <foo@example.com>')
    run_full_mailbox_test(u'"foo œ bar" <foo@example.com>',
        EmailAddress(u'"foo œ bar"', u'foo@example.com'),
        '"=?utf-8?q?foo_=C5=93_bar?=" <foo@example.com>')
    run_full_mailbox_test(u'"foo – bar" <foo@example.com>',
        EmailAddress(u'"foo – bar"', 'foo@example.com'),
        '"=?utf-8?b?Zm9vIOKAkyBiYXI=?=" <foo@example.com>')
    run_full_mailbox_test(u'"foo Ǽ bar" <foo@example.com>',
        EmailAddress(u'"foo Ǽ bar"', u'foo@example.com'),
        '"=?utf-8?q?foo_=C7=BC_bar?=" <foo@example.com>')
    run_full_mailbox_test(u'"foo Ω bar" <foo@example.com>',
        EmailAddress(u'"foo Ω bar"', u'foo@example.com'),
        '"=?utf-8?b?Zm9vIOKEpiBiYXI=?=" <foo@example.com>')
    run_full_mailbox_test(u'"foo ↵ bar" <foo@example.com>',
        EmailAddress(u'"foo ↵ bar"', u'foo@example.com'),
        '"=?utf-8?b?Zm9vIOKGtSBiYXI=?=" <foo@example.com>')
    run_full_mailbox_test(u'"foo ∑ bar" <foo@example.com>',
        EmailAddress(u'"foo ∑ bar"', u'foo@example.com'),
        '"=?utf-8?b?Zm9vIOKIkSBiYXI=?=" <foo@example.com>')
    run_full_mailbox_test(u'"foo ⏲ bar" <foo@example.com>',
        EmailAddress(u'"foo ⏲ bar"', u'foo@example.com'),
        '"=?utf-8?b?Zm9vIOKPsiBiYXI=?=" <foo@example.com>')
    run_full_mailbox_test(u'"foo Ⓐ bar" <foo@example.com>',
        EmailAddress(u'"foo Ⓐ bar"', u'foo@example.com'),
        '"=?utf-8?b?Zm9vIOKStiBiYXI=?=" <foo@example.com>')
    run_full_mailbox_test(u'"foo ▒ bar" <foo@example.com>',
        EmailAddress(u'"foo ▒ bar"', u'foo@example.com'),
        '"=?utf-8?b?Zm9vIOKWkiBiYXI=?=" <foo@example.com>')
    run_full_mailbox_test(u'"foo ▲ bar" <foo@example.com>',
        EmailAddress(u'"foo ▲ bar"', u'foo@example.com'),
        '"=?utf-8?b?Zm9vIOKWsiBiYXI=?=" <foo@example.com>')
    run_full_mailbox_test(u'"foo ⚔ bar" <foo@example.com>',
        EmailAddress(u'"foo ⚔ bar"', u'foo@example.com'),
        '"=?utf-8?b?Zm9vIOKalCBiYXI=?=" <foo@example.com>')
    run_full_mailbox_test(u'"foo ✎ bar" <foo@example.com>',
        EmailAddress(u'"foo ✎ bar"', u'foo@example.com'),
        '"=?utf-8?b?Zm9vIOKcjiBiYXI=?=" <foo@example.com>')
    run_full_mailbox_test(u'"foo ⠂ bar" <foo@example.com>',
        EmailAddress(u'"foo ⠂ bar"', u'foo@example.com'),
        '"=?utf-8?b?Zm9vIOKggiBiYXI=?=" <foo@example.com>')
    run_full_mailbox_test(u'"foo ⬀ bar" <foo@example.com>',
        EmailAddress(u'"foo ⬀ bar"', u'foo@example.com'),
        '"=?utf-8?b?Zm9vIOKsgCBiYXI=?=" <foo@example.com>')
    run_full_mailbox_test(u'"foo 💩 bar" <foo@example.com>',
        EmailAddress(u'"foo 💩 bar"', u'foo@example.com'),
        '"=?utf-8?b?Zm9vIPCfkqkgYmFy?=" <foo@example.com>')

    # unicode, language specific punctuation, just test with !
    run_full_mailbox_test(u'fooǃ foo@example.com',
        EmailAddress(u'fooǃ', u'foo@example.com'),
        '=?utf-8?b?Zm9vx4M=?= <foo@example.com>')
    run_full_mailbox_test(u'foo‼ foo@example.com',
        EmailAddress(u'foo‼', u'foo@example.com'),
        '=?utf-8?b?Zm9v4oC8?= <foo@example.com>')
    run_full_mailbox_test(u'foo⁈ foo@example.com',
        EmailAddress(u'foo⁈', u'foo@example.com'),
        '=?utf-8?b?Zm9v4oGI?= <foo@example.com>')
    run_full_mailbox_test(u'foo⁉ foo@example.com',
        EmailAddress(u'foo⁉', u'foo@example.com'),
        '=?utf-8?b?Zm9v4oGJ?= <foo@example.com>')
    run_full_mailbox_test(u'foo❕ foo@example.com',
        EmailAddress(u'foo❕', u'foo@example.com'),
        '=?utf-8?b?Zm9v4p2V?= <foo@example.com>')
    run_full_mailbox_test(u'foo❗ foo@example.com',
        EmailAddress(u'foo❗', u'foo@example.com'),
        '=?utf-8?b?Zm9v4p2X?= <foo@example.com>')
    run_full_mailbox_test(u'foo❢ foo@example.com',
        EmailAddress(u'foo❢', u'foo@example.com'),
        '=?utf-8?b?Zm9v4p2i?= <foo@example.com>')
    run_full_mailbox_test(u'foo❣ foo@example.com',
        EmailAddress(u'foo❣', u'foo@example.com'),
        '=?utf-8?b?Zm9v4p2j?= <foo@example.com>')
    run_full_mailbox_test(u'fooꜝ foo@example.com',
        EmailAddress(u'fooꜝ', u'foo@example.com'),
        '=?utf-8?b?Zm9v6pyd?= <foo@example.com>')
    run_full_mailbox_test(u'fooꜞ foo@example.com',
        EmailAddress(u'fooꜞ', u'foo@example.com'),
        '=?utf-8?b?Zm9v6pye?= <foo@example.com>')
    run_full_mailbox_test(u'fooꜟ foo@example.com',
        EmailAddress(u'fooꜟ', u'foo@example.com'),
        '=?utf-8?b?Zm9v6pyf?= <foo@example.com>')
    run_full_mailbox_test(u'foo﹗ foo@example.com',
        EmailAddress(u'foo﹗', u'foo@example.com'),
        '=?utf-8?b?Zm9v77mX?= <foo@example.com>')
    run_full_mailbox_test(u'foo！ foo@example.com',
        EmailAddress(u'foo！', u'foo@example.com'),
        '=?utf-8?b?Zm9v77yB?= <foo@example.com>')
    run_full_mailbox_test(u'foo՜ foo@example.com',
        EmailAddress(u'foo՜', u'foo@example.com'),
        '=?utf-8?b?Zm9v1Zw=?= <foo@example.com>')
    run_full_mailbox_test(u'foo߹ foo@example.com',
        EmailAddress(u'foo߹', u'foo@example.com'),
        '=?utf-8?b?Zm9v37k=?= <foo@example.com>')
    run_full_mailbox_test(u'foo႟ foo@example.com',
        EmailAddress(u'foo႟', u'foo@example.com'),
        '=?utf-8?b?Zm9v4YKf?= <foo@example.com>')
    run_full_mailbox_test(u'foo᥄ foo@example.com',
        EmailAddress(u'foo᥄', u'foo@example.com'),
        '=?utf-8?b?Zm9v4aWE?= <foo@example.com>')

    # allow the following characters ()[]@\: unquoted because they are used so often
    run_full_mailbox_test(u'foo ()[]@\: bar <foo@example.com>',
        EmailAddress(u'foo ()[]@\: bar', u'foo@example.com'),
        'foo ()[]@\\: bar <foo@example.com>')


def test_angle_addr():
    "Grammar: angle-addr -> [ whitespace ] < addr-spec > [ whitespace ]"

    # pass angle-addr
    run_mailbox_test('<steve@apple.com>', 'steve@apple.com')
    run_full_mailbox_test('Steve Jobs <steve@apple.com>', EmailAddress('Steve Jobs', 'steve@apple.com'))
    run_full_mailbox_test('Steve Jobs < steve@apple.com>', EmailAddress('Steve Jobs', 'steve@apple.com'))
    run_full_mailbox_test('Steve Jobs <steve@apple.com >', EmailAddress('Steve Jobs', 'steve@apple.com'))
    run_full_mailbox_test('Steve Jobs < steve@apple.com >', EmailAddress('Steve Jobs', 'steve@apple.com'))

    # fail angle-addr
    run_full_mailbox_test('<steve@apple.com', None)
    run_full_mailbox_test('Steve Jobs steve@apple.com>', None)
    run_full_mailbox_test('steve@apple.com>', None)
    run_full_mailbox_test('Steve Jobs <steve@apple.com', None)
    run_full_mailbox_test('Steve Jobs <@steve@apple.com>', None)
    run_full_mailbox_test('<Steve Jobs <steve@apple.com>>', None)
    run_full_mailbox_test('<Steve Jobs <steve@apple.com>', None)
    run_full_mailbox_test('Steve Jobs <steve@apple.com>>', None)
    run_full_mailbox_test('<Steve Jobs> <steve@apple.com>', None)
    run_full_mailbox_test('<Steve Jobs <steve@apple.com>', None)
    run_full_mailbox_test('Steve Jobs> <steve@apple.com>', None)
    run_full_mailbox_test('Steve Jobs <<steve@apple.com>>', None)
    run_full_mailbox_test('Steve Jobs <<steve@apple.com>', None)


def test_addr_spec():
    "Grammar: addr-spec -> [ whitespace ] local-part @ domain [ whitespace ]"

    # pass addr-spec
    run_mailbox_test('linus@kernel.org', 'linus@kernel.org')
    run_mailbox_test(' linus@kernel.org', 'linus@kernel.org')
    run_mailbox_test('linus@kernel.org ', 'linus@kernel.org')
    run_mailbox_test(' linus@kernel.org ', 'linus@kernel.org')
    run_mailbox_test('linus@localhost', 'linus@localhost')

    # fail addr-spec
    run_mailbox_test('linus@', None)
    run_mailbox_test('linus@ ', None)
    run_mailbox_test('linus@;', None)
    run_mailbox_test('linus@@kernel.org', None)
    run_mailbox_test('linus@ @kernel.org', None)
    run_mailbox_test('linus@ @localhost', None)
    run_mailbox_test('linus-at-kernel.org', None)
    run_mailbox_test('linus at kernel.org', None)
    run_mailbox_test('linus kernel.org', None)


def test_local_part():
    "Grammar: local-part -> dot-atom | quoted-string"

    # test length limits
    run_mailbox_test(''.join(['a'*128, '@b']), ''.join(['a'*128, '@b']))
    run_mailbox_test(''.join(['a'*257, '@b']), None)

    # because qtext and quoted-pair are longer than 64 bytes (limit on local-part)
    # we use a sample in testing, every other for qtext and every fifth for quoted-pair
    sample_qtext = FULL_QTEXT[::2]
    sample_qpair = FULL_QUOTED_PAIR[::5]

    # pass dot-atom
    run_mailbox_test('ABCDEFGHIJKLMNOPQRSTUVWXYZ@apple.com', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ@apple.com')
    run_mailbox_test('abcdefghijklmnopqrstuvwzyz@apple.com', 'abcdefghijklmnopqrstuvwzyz@apple.com')
    run_mailbox_test('0123456789@apple.com', '0123456789@apple.com')
    run_mailbox_test('!#$%&\'*+-/=?^_`{|}~@apple.com', '!#$%&\'*+-/=?^_`{|}~@apple.com')
    run_mailbox_test('AZaz09!#$%&\'*+-/=?^_`{|}~@apple.com', 'AZaz09!#$%&\'*+-/=?^_`{|}~@apple.com')
    run_mailbox_test('steve@apple.com', 'steve@apple.com')
    run_mailbox_test(' steve@apple.com', 'steve@apple.com')
    run_mailbox_test('  steve@apple.com', 'steve@apple.com')

    # fail dot-atom
    run_mailbox_test('steve @apple.com', None)
    run_mailbox_test(' steve @apple.com', None)
    run_mailbox_test(', steve@apple.com', None)
    run_mailbox_test(';;steve@apple.com', None)
    run_mailbox_test('"steve@apple.com', None)
    run_mailbox_test('steve"@apple.com', None)
    run_mailbox_test('steve jobs @apple.com', None)
    run_mailbox_test(' steve jobs @apple.com', None)
    run_mailbox_test('steve..jobs@apple.com', None)

    # pass qtext
    for cnk in chunks(FULL_QTEXT, len(FULL_QTEXT)/2):
        run_mailbox_test('"{0}"@b'.format(cnk), '"{0}"@b'.format(cnk))
    run_mailbox_test('" {0}"@b'.format(sample_qtext), '" {0}"@b'.format(sample_qtext))
    run_mailbox_test('"{0} "@b'.format(sample_qtext), '"{0} "@b'.format(sample_qtext))
    run_mailbox_test('" {0} "@b'.format(sample_qtext), '" {0} "@b'.format(sample_qtext))
    run_full_mailbox_test('"{0}" "{0}"@b'.format(sample_qtext),
        EmailAddress('"{0}"'.format(sample_qtext), '"{0}"@b'.format(sample_qtext)))

    # fail qtext
    run_mailbox_test('"{0}""{0}"@b'.format(sample_qtext), None)
    run_mailbox_test('"john""smith"@b'.format(sample_qtext), None)
    run_mailbox_test('"{0}" @b'.format(sample_qtext), None)
    run_mailbox_test(' "{0}" @b'.format(sample_qtext), None)
    run_mailbox_test('"{0}@b'.format(sample_qtext), None)
    run_mailbox_test('{0}"@b'.format(sample_qtext), None)
    run_mailbox_test('{0}@b'.format(sample_qtext), None)
    run_mailbox_test('"{0}@b"'.format(sample_qtext), None)

    # pass quoted-pair
    for cnk in chunks(FULL_QUOTED_PAIR, len(FULL_QUOTED_PAIR)/3):
        run_mailbox_test('"{0}"@b'.format(cnk), '"{0}"@b'.format(cnk))
    run_mailbox_test('" {0}"@b'.format(sample_qpair), '" {0}"@b'.format(sample_qpair))
    run_mailbox_test('"{0} "@b'.format(sample_qpair), '"{0} "@b'.format(sample_qpair))
    run_mailbox_test('" {0} "@b'.format(sample_qpair), '" {0} "@b'.format(sample_qpair))
    run_full_mailbox_test('"{0}" "{0}"@b'.format(sample_qpair),
        EmailAddress('"{0}"'.format(sample_qpair), '"{0}"@b'.format(sample_qpair)))

    # fail quoted-pair
    run_mailbox_test('"{0}""{0}"@b'.format(sample_qpair), None)
    run_mailbox_test('"john""smith"@b'.format(sample_qpair), None)
    run_mailbox_test('"{0}" @b'.format(sample_qpair), None)
    run_mailbox_test(' "{0}" @b'.format(sample_qpair), None)
    run_mailbox_test('"{0}@b'.format(sample_qpair), None)
    run_mailbox_test('{0}"@b'.format(sample_qpair), None)
    run_mailbox_test('{0}@b'.format(sample_qpair), None)
    run_mailbox_test('"{0}@b"'.format(sample_qpair), None)


def test_domain():
    "Grammar: domain -> dot-atom"

    # test length limits
    max_domain_len = ''.join(['a'*62, '.', 'b'*62, '.', 'c'*63, '.', 'd'*63])
    overlimit_domain_one = ''.join(['a'*62, '.', 'b'*62, '.', 'c'*63, '.', 'd'*64])
    overlimit_domain_two = ''.join(['a'*62, '.', 'b'*62, '.', 'c'*63, '.', 'd'*63, '.', 'a'])
    run_mailbox_test(''.join(['b@', 'a'*63]), ''.join(['b@', 'a'*63]))
    run_mailbox_test(''.join(['b@', 'a'*64]), None)
    run_mailbox_test(''.join(['a@', max_domain_len]), ''.join(['a@', max_domain_len]))
    run_mailbox_test(''.join(['a@', overlimit_domain_one]), None)
    run_mailbox_test(''.join(['a@', overlimit_domain_two]), None)


    # pass dot-atom
    run_mailbox_test('bill@ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'bill@abcdefghijklmnopqrstuvwxyz')
    run_mailbox_test('bill@abcdefghijklmnopqrstuvwxyz', 'bill@abcdefghijklmnopqrstuvwxyz')
    run_mailbox_test('bill@0123456789', 'bill@0123456789')
    run_mailbox_test('bill@!#$%&\'*+-/=?^_`{|}~', 'bill@!#$%&\'*+-/=?^_`{|}~')
    run_mailbox_test('bill@microsoft.com', 'bill@microsoft.com')
    run_mailbox_test('bill@retired.microsoft.com', 'bill@retired.microsoft.com')
    run_mailbox_test('bill@microsoft.com ', 'bill@microsoft.com')
    run_mailbox_test('bill@microsoft.com  ', 'bill@microsoft.com')

    # fail dot-atom
    run_mailbox_test('bill@micro soft.com', None)
    run_mailbox_test('bill@micro. soft.com', None)
    run_mailbox_test('bill@micro .soft.com', None)
    run_mailbox_test('bill@micro. .soft.com', None)
    run_mailbox_test('bill@microsoft.com,', None)
    run_mailbox_test('bill@microsoft.com, ', None)
    run_mailbox_test('bill@microsoft.com, ', None)
    run_mailbox_test('bill@microsoft.com , ', None)
    run_mailbox_test('bill@microsoft.com,,', None)
    run_mailbox_test('bill@microsoft.com.', None)
    run_mailbox_test('bill@microsoft.com..', None)
    run_mailbox_test('bill@microsoft..com', None)
    run_mailbox_test('bill@retired.microsoft..com', None)
    run_mailbox_test('bill@.com', None)
    run_mailbox_test('bill@.com.', None)
    run_mailbox_test('bill@.microsoft.com', None)
    run_mailbox_test('bill@.microsoft.com.', None)
    run_mailbox_test('bill@"microsoft.com"', None)
    run_mailbox_test('bill@"microsoft.com', None)
    run_mailbox_test('bill@microsoft.com"', None)


def test_full_spec_symmetry_bug():
    """
    There was a bug that if an address has a display name that is equal or
    longer then 78 characters and consists of at least two words, then
    `full_spec` returned a string where a '\n' character was inserted between
    the display name words.
    """
    # Given
    original = 'very loooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooong <foo@example.com>'
    addr = address.parse(original)

    # When
    restored = addr.full_spec()

    # Then
    assert_equal(original, restored)


########NEW FILE########
__FILENAME__ = parser_test
# coding:utf-8

import email.header

from flanker.addresslib.address import is_email
from flanker.mime.message.headers.encodedword import mime_to_unicode
from mock import patch, Mock
from nose.tools import assert_equal, assert_not_equal
from nose.tools import assert_true, assert_false


def test_is_email():
    assert_true(is_email("ev@host"))
    assert_true(is_email("ev@host.com.com.com"))

    assert_false(is_email("evm"))
    assert_false(is_email(None))


def test_header_to_unicode():
    assert_equal(u'Eugueny ώ Kontsevoy', mime_to_unicode("=?UTF-8?Q?Eugueny_=CF=8E_Kontsevoy?=") )
    assert_equal(u'hello', mime_to_unicode("hello"))
    assert_equal(None, mime_to_unicode(None))

########NEW FILE########
__FILENAME__ = aol_test
# coding:utf-8

import random
import string

from flanker.addresslib import address
from flanker.addresslib import validate

from mock import patch
from nose.tools import assert_equal, assert_not_equal
from nose.tools import nottest

from ... import skip_if_asked

DOMAIN = '@aol.com'
SAMPLE_MX = 'sample.mx.aol.com'

@nottest
def mock_exchanger_lookup(arg, metrics=False):
    mtimes = {'mx_lookup': 0, 'dns_lookup': 0, 'mx_conn': 0}
    return (SAMPLE_MX, mtimes)


def test_exchanger_lookup():
    '''
    Test if exchanger lookup is occuring correctly. If this simple test
    fails that means custom grammar was hit. Then the rest of the tests
    can be mocked. Should always be run during deployment, can be skipped
    during development.
    '''
    skip_if_asked()

    # very simple test that should fail AOL custom grammar
    addr_string = '!mailgun' + DOMAIN
    addr = address.validate_address(addr_string)
    assert_equal(addr, None)


def test_aol_pass():
    with patch.object(validate, 'mail_exchanger_lookup') as mock_method:
        mock_method.side_effect = mock_exchanger_lookup

        # valid length range
        for i in range(3, 33):
            localpart = ''.join(random.choice(string.ascii_letters) for x in range(i))
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # start must be letter
        for i in string.ascii_letters:
            localpart = str(i) + 'aaa'
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # end must be letter or number
        for i in string.ascii_letters + string.digits:
            localpart = 'aaa' + str(i)
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # must be letter, num, dot (.), or underscore
        for i in string.ascii_letters + string.digits + '._':
            localpart = 'aa' + str(i) + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # only zero or one dot (.) allowed
        for i in range(0, 2):
            localpart = 'aa' + '.'*i + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)


def test_aol_fail():
    with patch.object(validate, 'mail_exchanger_lookup') as mock_method:
        mock_method.side_effect = mock_exchanger_lookup

        # invalid length range
        for i in range(0, 3) + range(33, 40):
            localpart = ''.join(random.choice(string.ascii_letters) for x in range(i))
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid start char (must start with letter)
        for i in string.punctuation + string.digits:
            localpart = str(i) + 'aaa'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid end char (must end with letter or digit)
        for i in string.punctuation:
            localpart = 'aaa' + str(i)
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid chars (must be letter, num, underscore, or dot)
        invalid_chars = string.punctuation
        invalid_chars = invalid_chars.replace('.', '')
        invalid_chars = invalid_chars.replace('_', '')
        for i in invalid_chars:
            localpart = 'aa' + str(i) + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # no more than 1 dot (.) allowed
        for i in range(2, 4):
            localpart = 'aa' + '.'*i + 'a' + '.'*i + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # no consecutive: underscore (_) or dot-underscore (._)
        # or underscore-dot (_.)
        for i in range(1, 4):
            localpart = 'aa' + '__'*i + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

            localpart = 'aa' + '._'*i + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

            localpart = 'aa' + '._'*i + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

########NEW FILE########
__FILENAME__ = gmail_test
# coding:utf-8

import random
import string

from flanker.addresslib import address
from flanker.addresslib import validate

from mock import patch
from nose.tools import assert_equal, assert_not_equal
from nose.tools import nottest

from ... import skip_if_asked

DOMAIN = '@gmail.com'
SAMPLE_MX = 'sample.gmail-smtp-in.l.google.com'
ATOM_STR = string.ascii_letters + string.digits + '!#$%&\'*+-/=?^_`{|}~'

@nottest
def mock_exchanger_lookup(arg, metrics=False):
    mtimes = {'mx_lookup': 0, 'dns_lookup': 0, 'mx_conn': 0}
    return (SAMPLE_MX, mtimes)


def test_exchanger_lookup():
    '''
    Test if exchanger lookup is occuring correctly. If this simple test
    fails that means custom grammar was hit. Then the rest of the tests
    can be mocked. Should always be run during deployment, can be skipped
    during development.
    '''
    skip_if_asked()

    # very simple test that should fail Gmail custom grammar
    addr_string = '!mailgun' + DOMAIN
    addr = address.validate_address(addr_string)
    assert_equal(addr, None)


def test_gmail_pass():
    with patch.object(validate, 'mail_exchanger_lookup') as mock_method:
        mock_method.side_effect = mock_exchanger_lookup

        # valid length range
        for i in range(6, 31):
            localpart = ''.join(random.choice(string.ascii_letters) for x in range(i))
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # start must be letter or num
        for i in string.ascii_letters + string.digits:
            localpart = str(i) + 'aaaaa'
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # end must be letter or number
        for i in string.ascii_letters + string.digits:
            localpart = 'aaaaa' + str(i)
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # must be letter, num, or dots
        for i in string.ascii_letters + string.digits + '.':
            localpart = 'aaa' + str(i) + '000'
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # all dots (.) are ignored
        for localpart in ['aaaaaa......', '......aaaaaa', 'aaa......aaa','aa...aa...aa']:
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # everything after plus (+) is ignored
        for localpart in ['aaaaaa+', 'aaaaaa+tag', 'aaaaaa+tag+tag','aaaaaa++tag', 'aaaaaa+' + ATOM_STR]:
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)


def test_gmail_fail():
    with patch.object(validate, 'mail_exchanger_lookup') as mock_method:
        mock_method.side_effect = mock_exchanger_lookup

        # invalid length range
        for i in range(0, 6) + range(31, 40):
            localpart = ''.join(random.choice(string.ascii_letters) for x in range(i))
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid start char (must start with letter)
        for i in string.punctuation:
            localpart = str(i) + 'aaaaa'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid end char (must end with letter or digit)
        for i in string.punctuation:
            localpart = 'aaaaa' + str(i)
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid chars (must be letter, num, or dot)
        invalid_chars = string.punctuation
        invalid_chars = invalid_chars.replace('.', '')
        for i in invalid_chars:
            localpart = 'aaa' + str(i) + '000'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # all dots (.) are ignored
        for localpart in ['aaaaa......', '......aaaaa', 'aaa......aa','aa...a...aa']:
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # everything after plus (+) is ignored
        for localpart in ['+t1', 'a+t1', 'aa+', 'aaa+t1', 'aaaa+t1+t2','aaaaa++t1']:
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

########NEW FILE########
__FILENAME__ = google_test
# coding:utf-8

import random
import string

from flanker.addresslib import address
from flanker.addresslib import validate

from mock import patch
from nose.tools import assert_equal, assert_not_equal
from nose.tools import nottest

from ... import skip_if_asked

DOMAIN = '@google.com'
SAMPLE_MX = 'sample.aspmx.l.google.com'
ATOM_STR = string.ascii_letters + string.digits + '!#$%&\'*+-/=?^_`{|}~'

@nottest
def mock_exchanger_lookup(arg, metrics=False):
    mtimes = {'mx_lookup': 0, 'dns_lookup': 0, 'mx_conn': 0}
    return (SAMPLE_MX, mtimes)


def test_exchanger_lookup():
    '''
    Test if exchanger lookup is occuring correctly. If this simple test
    fails that means custom grammar was hit. Then the rest of the tests
    can be mocked. Should always be run during deployment, can be skipped
    during development.
    '''
    skip_if_asked()

    # very simple test that should fail Google Apps custom grammar
    addr_string = '!mailgun' + DOMAIN
    addr = address.validate_address(addr_string)
    assert_equal(addr, None)


def test_google_pass():
    with patch.object(validate, 'mail_exchanger_lookup') as mock_method:
        mock_method.side_effect = mock_exchanger_lookup

        # if single character, must be alphanum, underscore, or apostrophe
        for i in string.ascii_letters + string.digits + '_\'':
            localpart = str(i)
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # valid length range
        for i in range(1, 65):
            localpart = ''.join(random.choice(string.ascii_letters) for x in range(i))
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # start must be alphanum, underscore, dash, or apostrophe
        for i in string.ascii_letters + string.digits + '_-\'':
            localpart = str(i) + 'aaaaa'
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # end must be alphanum, underscore, dash, or apostrophe
        for i in string.ascii_letters + string.digits + '_-\'':
            localpart = 'aaaaa' + str(i)
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # must be alphanum, underscore, dash, apostrophe, dots
        for i in string.ascii_letters + string.digits + '_-\'.':
            localpart = 'aaa' + str(i) + '000'
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # everything after plus (+) is ignored
        for localpart in ['aa+', 'aa+tag', 'aa+tag+tag', 'aa++tag', 'aa+' + ATOM_STR]:
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)


def test_google_fail():
    with patch.object(validate, 'mail_exchanger_lookup') as mock_method:
        mock_method.side_effect = mock_exchanger_lookup

        # invalid single character (must be alphanum, underscore, or apostrophe)
        invalid_chars = string.punctuation
        invalid_chars = invalid_chars.replace('_', '')
        invalid_chars = invalid_chars.replace('\'', '')
        for i in invalid_chars:
            localpart = str(i)
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid length range
        for i in range(0) + range(65, 80):
            localpart = ''.join(random.choice(string.ascii_letters) for x in range(i))
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid start char (must start with alphanum, underscore, dash, or apostrophe)
        invalid_chars = string.punctuation
        invalid_chars = invalid_chars.replace('_', '')
        invalid_chars = invalid_chars.replace('-', '')
        invalid_chars = invalid_chars.replace('\'', '')
        for i in invalid_chars:
            localpart = str(i) + 'aaaaa'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid end char (must end with alphanum, underscore, dash, or apostrophe)
        invalid_chars = string.punctuation
        invalid_chars = invalid_chars.replace('_', '')
        invalid_chars = invalid_chars.replace('-', '')
        invalid_chars = invalid_chars.replace('\'', '')
        invalid_chars = invalid_chars.replace('+', '')
        for i in invalid_chars:
            localpart = 'aaaaa' + str(i)
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid chars (must be alphanum, underscore, dash, apostrophe, dots)
        invalid_chars = string.punctuation
        invalid_chars = invalid_chars.replace('_', '')
        invalid_chars = invalid_chars.replace('-', '')
        invalid_chars = invalid_chars.replace('\'', '')
        invalid_chars = invalid_chars.replace('.', '')
        invalid_chars = invalid_chars.replace('+', '')
        for i in invalid_chars:
            localpart = 'aaa' + str(i) + '000'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # dots (.) are NOT ignored
        addr1 = address.validate_address('aa..aa' + DOMAIN)
        addr2 = address.validate_address('aa.aa' + DOMAIN)
        assert_not_equal(addr1, addr2)

        # everything after plus (+) is ignored, but something must be infront of it
        for localpart in ['+t1', '+' + ATOM_STR]:
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

########NEW FILE########
__FILENAME__ = hotmail_test
# coding:utf-8

import random
import string

from flanker.addresslib import address
from flanker.addresslib import validate

from mock import patch
from nose.tools import assert_equal, assert_not_equal
from nose.tools import nottest

from ... import skip_if_asked

DOMAIN = '@hotmail.com'
SAMPLE_MX = 'mx0.hotmail.com'

@nottest
def mock_exchanger_lookup(arg, metrics=False):
    mtimes = {'mx_lookup': 0, 'dns_lookup': 0, 'mx_conn': 0}
    return (SAMPLE_MX, mtimes)


def test_exchanger_lookup():
    '''
    Test if exchanger lookup is occuring correctly. If this simple test
    fails that means custom grammar was hit. Then the rest of the tests
    can be mocked. Should always be run during deployment, can be skipped
    during development.
    '''
    skip_if_asked()

    # very simple test that should fail Hotmail custom grammar
    addr_string = '!mailgun' + DOMAIN
    addr = address.validate_address(addr_string)
    assert_equal(addr, None)


def test_hotmail_pass():
    with patch.object(validate, 'mail_exchanger_lookup') as mock_method:
        mock_method.side_effect = mock_exchanger_lookup

        # valid length range
        for i in range(1, 65):
            localpart = ''.join(random.choice(string.ascii_letters) for x in range(i))
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # start must be letter
        for i in string.ascii_letters:
            localpart = str(i) + 'a'
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # end must be letter or number
        for i in string.ascii_letters + string.digits + '-_':
            localpart = 'a' + str(i)
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # must be letter, num, period, hyphen, or underscore
        for i in string.ascii_letters + string.digits + '.-_':
            localpart = 'a' + str(i) + '0'
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # only zero or one plus allowed
        for i in range(0, 2):
            localpart = 'aa' + '+'*i + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # allow multiple periods
        localpart = 'aa.bb.00'
        addr = address.validate_address(localpart + DOMAIN)
        assert_not_equal(addr, None)


def test_hotmail_fail():
    with patch.object(validate, 'mail_exchanger_lookup') as mock_method:
        mock_method.side_effect = mock_exchanger_lookup

        # invalid length range
        for i in range(0, 0) + range(65, 70):
            localpart = ''.join(random.choice(string.ascii_letters) for x in range(i))
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid start char (must start with letter)
        for i in string.punctuation + string.digits:
            localpart = str(i) + 'a'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid end char (must end with letter or num, hyphen, or underscore)
        invalid_end_chars = string.punctuation
        invalid_end_chars = invalid_end_chars.replace('-', '')
        invalid_end_chars = invalid_end_chars.replace('_', '')
        invalid_end_chars = invalid_end_chars.replace('+', '')
        for i in invalid_end_chars:
            localpart = 'a' + str(i)
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid chars (must be letter, num, underscore, or dot)
        invalid_chars = string.punctuation
        invalid_chars = invalid_chars.replace('.', '')
        invalid_chars = invalid_chars.replace('-', '')
        invalid_chars = invalid_chars.replace('_', '')
        invalid_chars = invalid_chars.replace('+', '')
        for i in invalid_chars:
            localpart = 'a' + str(i) + '0'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # no more than 1 consecutive dot (.) or plus (+) allowed
        for i in range(2, 4):
            localpart = 'aa' + '.'*i + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

            localpart = 'aa' + '+'*i + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

########NEW FILE########
__FILENAME__ = icloud_test
# coding:utf-8

import random
import string

from flanker.addresslib import address
from flanker.addresslib import validate

from mock import patch
from nose.tools import assert_equal, assert_not_equal
from nose.tools import nottest

from ... import skip_if_asked

DOMAIN = '@icloud.com'
SAMPLE_MX = 'sample.icloud.com.akadns.net'

@nottest
def mock_exchanger_lookup(arg, metrics=False):
    mtimes = {'mx_lookup': 0, 'dns_lookup': 0, 'mx_conn': 0}
    return (SAMPLE_MX, mtimes)


def test_exchanger_lookup():
    '''
    Test if exchanger lookup is occuring correctly. If this simple test
    fails that means custom grammar was hit. Then the rest of the tests
    can be mocked. Should always be run during deployment, can be skipped
    during development.
    '''
    skip_if_asked()

    # very simple test that should fail iCloud custom grammar
    addr_string = '!mailgun' + DOMAIN
    addr = address.validate_address(addr_string)
    assert_equal(addr, None)


def test_icloud_pass():
    with patch.object(validate, 'mail_exchanger_lookup') as mock_method:
        mock_method.side_effect = mock_exchanger_lookup

        # valid length range
        for i in range(3, 21):
            localpart = ''.join(random.choice(string.ascii_letters) for x in range(i))
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # start must be letter
        for i in string.ascii_letters:
            localpart = str(i) + 'aa'
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # end must be letter or number
        for i in string.ascii_letters + string.digits:
            localpart = 'aa' + str(i)
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # must be letter, num, and underscore
        for i in string.ascii_letters + string.digits + '._':
            localpart = 'aa' + str(i) + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # only zero or one dot (.) or underscore (_) allowed
        for i in range(0, 2):
            localpart = 'aa' + '.'*i + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

            localpart = 'aa' + '_'*i + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # everything after plus (+) is ignored
        for localpart in ['aaa+tag', 'aaa+tag+tag','aaa++tag']:
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)


def test_icloud_fail():
    with patch.object(validate, 'mail_exchanger_lookup') as mock_method:
        mock_method.side_effect = mock_exchanger_lookup

        # invalid length range
        for i in range(0, 3) + range(21, 30):
            localpart = ''.join(random.choice(string.ascii_letters) for x in range(i))
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid start char (must start with letter)
        for i in string.punctuation + string.digits:
            localpart = str(i) + 'aa'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid end char (must end with letter or digit)
        for i in string.punctuation:
            localpart = 'aa' + str(i)
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid chars (must be letter, num, underscore, or dot)
        invalid_chars = string.punctuation
        invalid_chars = invalid_chars.replace('.', '')
        invalid_chars = invalid_chars.replace('_', '')
        for i in invalid_chars:
            localpart = 'aa' + str(i) + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # no more than one dot (.) or underscore (_) allowed
        for i in range(2, 4):
            localpart = 'aa' + '.'*i + 'a' + '.'*i + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

            localpart = 'aa' + '_'*i + 'a' + '_'*i + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # no ending plus (+)
        for i in range(2, 4):
            localpart = 'aaa' + '+'*i
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

########NEW FILE########
__FILENAME__ = yahoo_test
# coding:utf-8

import random
import string

from flanker.addresslib import address
from flanker.addresslib import validate

from mock import patch
from nose.tools import assert_equal, assert_not_equal
from nose.tools import nottest

from ... import skip_if_asked

DOMAIN = '@yahoo.com'
SAMPLE_MX = 'mta0.am0.yahoodns.net'

@nottest
def mock_exchanger_lookup(arg, metrics=False):
    mtimes = {'mx_lookup': 0, 'dns_lookup': 0, 'mx_conn': 0}
    return (SAMPLE_MX, mtimes)


def test_exchanger_lookup():
    '''
    Test if exchanger lookup is occuring correctly. If this simple test
    fails that means custom grammar was hit. Then the rest of the tests
    can be mocked. Should always be run during deployment, can be skipped
    during development.
    '''
    skip_if_asked()

    # very simple test that should fail Yahoo! custom grammar
    addr_string = '!mailgun' + DOMAIN
    addr = address.validate_address(addr_string)
    assert_equal(addr, None)


def test_yahoo_pass():
    with patch.object(validate, 'mail_exchanger_lookup') as mock_method:
        mock_method.side_effect = mock_exchanger_lookup

        # valid length range
        for i in range(4, 33):
            localpart = ''.join(random.choice(string.ascii_letters) for x in range(i))
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # start must be letter
        for i in string.ascii_letters:
            localpart = str(i) + 'aaa'
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # end must be letter or number
        for i in string.ascii_letters + string.digits:
            localpart = 'aaa' + str(i)
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # must be letter, num, and underscore
        for i in string.ascii_letters + string.digits + '_':
            localpart = 'aa' + str(i) + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # only zero or one dot (.) allowed
        for i in range(0, 2):
            localpart = 'aa' + '.'*i + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)


def test_yahoo_disposable_pass():
    with patch.object(validate, 'mail_exchanger_lookup') as mock_method:
        mock_method.side_effect = mock_exchanger_lookup

        # valid length range
        for i in range(1, 32):
            base = ''.join(random.choice(string.ascii_letters) for x in range(i))
            keyword = ''.join(random.choice(string.ascii_letters) for x in range(i))
            localpart = base + '-' + keyword
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # base must be letter, number, underscore
        for i in string.ascii_letters + string.digits + '_':
            localpart = 'aa' + str(i) + '-00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)

        # keyword must be letter, number
        for i in string.ascii_letters + string.digits:
            localpart = 'aa-' + str(i) + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_not_equal(addr, None)


def test_yahoo_disposable_fail():
    with patch.object(validate, 'mail_exchanger_lookup') as mock_method:
        mock_method.side_effect = mock_exchanger_lookup

        # invalid base length range
        for i in range(0) + range(33, 40):
            base = ''.join(random.choice(string.ascii_letters) for x in range(i))
            localpart = base + '-aa'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid keyword length range
        for i in range(0) + range(33, 40):
            keyword = ''.join(random.choice(string.ascii_letters) for x in range(i))
            localpart = 'aa-' + keyword
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid base (must be letter, num, underscore)
        invalid_chars = string.punctuation
        invalid_chars = invalid_chars.replace('_', '')
        for i in invalid_chars:
            localpart = 'aa' + str(i) + '-00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid keyword (must be letter, num)
        invalid_chars = string.punctuation
        for i in invalid_chars:
            localpart = 'aa-' + str(i) + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

def test_yahoo_fail():
    with patch.object(validate, 'mail_exchanger_lookup') as mock_method:
        mock_method.side_effect = mock_exchanger_lookup

        # invalid length range
        for i in range(0, 4) + range(33, 40):
            localpart = ''.join(random.choice(string.ascii_letters) for x in range(i))
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid start char (must start with letter)
        for i in string.punctuation + string.digits:
            localpart = str(i) + 'aaa'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid end char (must end with letter or digit)
        for i in string.punctuation:
            localpart = 'aaa' + str(i)
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # invalid chars (must be letter, num, underscore, or dot)
        # addresses containing a dash may be a valid disposable address
        invalid_chars = string.punctuation
        invalid_chars = invalid_chars.replace('-', '')
        invalid_chars = invalid_chars.replace('.', '')
        invalid_chars = invalid_chars.replace('_', '')
        for i in invalid_chars:
            localpart = 'aa' + str(i) + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # no more than 1 dot (.) allowed
        for i in range(2, 4):
            localpart = 'aa' + '.'*i + 'a' + '.'*i + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

        # no consecutive: underscore (_) or dot-underscore (._)
        # or underscore-dot (_.)
        for i in range(1, 4):
            localpart = 'aa' + '__'*i + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

            localpart = 'aa' + '._'*i + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

            localpart = 'aa' + '._'*i + '00'
            addr = address.validate_address(localpart + DOMAIN)
            assert_equal(addr, None)

########NEW FILE########
__FILENAME__ = validator_test
# coding:utf-8

import re

from .. import *

from nose.tools import assert_equal, assert_not_equal
from nose.tools import nottest
from mock import patch

from flanker.addresslib import address
from flanker.addresslib import validate


COMMENT = re.compile(r'''\s*#''')


@nottest
def valid_localparts(strip_delimiters=False):
    for line in ABRIDGED_LOCALPART_VALID_TESTS.split('\n'):
        # strip line, skip over empty lines
        line = line.strip()
        if line == '':
            continue

        # skip over comments or empty lines
        match = COMMENT.match(line)
        if match:
            continue

        # skip over localparts with delimiters
        if strip_delimiters:
            if ',' in line or ';' in line:
                continue

        yield line

@nottest
def invalid_localparts(strip_delimiters=False):
    for line in ABRIDGED_LOCALPART_INVALID_TESTS.split('\n'):
        # strip line, skip over empty lines
        line = line.strip()
        if line == '':
            continue

        # skip over comments
        match = COMMENT.match(line)
        if match:
            continue

        # skip over localparts with delimiters
        if strip_delimiters:
            if ',' in line or ';' in line:
                continue

        yield line

@nottest
def mock_exchanger_lookup(arg, metrics=False):
    mtimes = {'mx_lookup': 10, 'dns_lookup': 20, 'mx_conn': 30}
    if metrics is True:
        if arg == 'ai' or arg == 'mailgun.org' or arg == 'fakecompany.mailgun.org':
            return ('', mtimes)
        else:
            return (None, mtimes)
    else:
        if arg == 'ai' or arg == 'mailgun.org' or arg == 'fakecompany.mailgun.org':
            return ''
        else:
            return None

def test_abridged_mailbox_valid_set():
    for line in ABRIDGED_LOCALPART_VALID_TESTS.split('\n'):
        # strip line, skip over empty lines
        line = line.strip()
        if line == '':
            continue

        # skip over comments or empty lines
        match = COMMENT.match(line)
        if match:
            continue

        # mocked valid dns lookup for tests
        with patch.object(validate, 'mail_exchanger_lookup') as mock_method:
            mock_method.side_effect = mock_exchanger_lookup

            addr = line + '@ai'
            mbox = address.validate_address(addr)
            assert_not_equal(mbox, None)

            # domain
            addr = line + '@mailgun.org'
            mbox = address.validate_address(addr)
            assert_not_equal(mbox, None)

            # subdomain
            addr = line + '@fakecompany.mailgun.org'
            mbox = address.validate_address(addr)
            assert_not_equal(mbox, None)


def test_abridged_mailbox_invalid_set():
    for line in ABRIDGED_LOCALPART_INVALID_TESTS.split('\n'):
        # strip line, skip over empty lines
        line = line.strip()
        if line == '':
            continue

        # skip over comments
        match = COMMENT.match(line)
        if match:
            continue

        # mocked valid dns lookup for tests
        with patch.object(validate, 'mail_exchanger_lookup') as mock_method:
            mock_method.side_effect = mock_exchanger_lookup

            addr = line + '@ai'
            mbox = address.validate_address(addr)
            assert_equal(mbox, None)

            # domain
            addr = line + '@mailgun.org'
            mbox = address.validate_address(addr)
            assert_equal(mbox, None)

            # subdomain
            addr = line + '@fakecompany.mailgun.org'
            mbox = address.validate_address(addr)
            assert_equal(mbox, None)


def test_parse_syntax_only_false():
    # syntax + validation
    valid_tld_list = [i + '@ai' for i in valid_localparts()]
    valid_domain_list = [i + '@mailgun.org' for i in valid_localparts()]
    valid_subdomain_list = [i + '@fakecompany.mailgun.org' for i in valid_localparts()]

    invalid_mx_list = [i + '@example.com' for i in valid_localparts(True)]
    invalid_tld_list = [i + '@com' for i in invalid_localparts(True)]
    invalid_domain_list = [i + '@example.com' for i in invalid_localparts(True)]
    invalid_subdomain_list = [i + '@sub.example.com' for i in invalid_localparts(True)]

    all_valid_list = valid_tld_list + valid_domain_list + valid_subdomain_list
    all_invalid_list = invalid_mx_list + invalid_tld_list + invalid_domain_list + \
        invalid_subdomain_list
    all_list = all_valid_list + all_invalid_list

    # all valid
    with patch.object(validate, 'mail_exchanger_lookup') as mock_method:
        mock_method.side_effect = mock_exchanger_lookup

        parse, unpar = address.validate_list(', '.join(valid_tld_list), as_tuple=True)
        assert_equal(parse, valid_tld_list)
        assert_equal(unpar, [])

        parse, unpar = address.validate_list(', '.join(valid_domain_list), as_tuple=True)
        assert_equal(parse, valid_domain_list)
        assert_equal(unpar, [])

        parse, unpar = address.validate_list(', '.join(valid_subdomain_list), as_tuple=True)
        assert_equal(parse, valid_subdomain_list)
        assert_equal(unpar, [])

        # all invalid
        parse, unpar = address.validate_list(', '.join(invalid_mx_list), as_tuple=True)
        assert_equal(parse, [])
        assert_equal(unpar, invalid_mx_list)

        parse, unpar = address.validate_list(', '.join(invalid_tld_list), as_tuple=True)
        assert_equal(parse, [])
        assert_equal(unpar, invalid_tld_list)

        parse, unpar = address.validate_list(', '.join(invalid_domain_list), as_tuple=True)
        assert_equal(parse, [])
        assert_equal(unpar, invalid_domain_list)

        parse, unpar = address.validate_list(', '.join(invalid_subdomain_list), as_tuple=True)
        assert_equal(parse, [])
        assert_equal(unpar, invalid_subdomain_list)

        parse, unpar = address.validate_list(', '.join(all_list), as_tuple=True)
        assert_equal(parse, all_valid_list)
        assert_equal(unpar, all_invalid_list)


def test_mx_lookup():
    # skip network tests during development
    skip_if_asked()

    # has MX, has MX server
    addr = address.validate_address('username@mailgun.com')
    assert_not_equal(addr, None)

    # has fallback A, has MX server
    addr = address.validate_address('username@domain.com')
    assert_not_equal(addr, None)

    # has MX, no server answers
    addr = address.validate_address('username@example.com')
    assert_equal(addr, None)

    # no MX
    addr = address.validate_address('username@no-dns-records-for-domain.com')
    assert_equal(addr, None)


def test_mx_connect():
    # skip network tests during development
    skip_if_asked()

    # connect
    addr = address.validate_address('username@mailgun.com')
    assert_not_equal(addr, None)

    # don't connect
    addr = address.validate_address('username@example.com')
    assert_equal(addr, None)


def test_mx_lookup_metrics():
    with patch.object(validate, 'mail_exchanger_lookup') as mock_method:
        mock_method.side_effect = mock_exchanger_lookup

        a, metrics = validate.mail_exchanger_lookup('example.com', metrics=True)
        assert_equal(metrics['mx_lookup'], 10)
        assert_equal(metrics['dns_lookup'], 20)
        assert_equal(metrics['mx_conn'], 30)

        # ensure values are unpacked correctly
        a = validate.mail_exchanger_lookup('example.com', metrics=False)
        a = validate.mail_exchanger_lookup('example.com', metrics=False)

def test_validate_address_metrics():
    with patch.object(validate, 'mail_exchanger_lookup') as mock_method:
        mock_method.side_effect = mock_exchanger_lookup

        parse, metrics = address.validate_address('foo@example.com', metrics=True)

        assert_not_equal(metrics, None)
        assert_equal(metrics['mx_lookup'], 10)
        assert_equal(metrics['dns_lookup'], 20)
        assert_equal(metrics['mx_conn'], 30)

########NEW FILE########
__FILENAME__ = bounce_tests
from nose.tools import *
from .. import *
from flanker.mime import create

def test_bounce_analyzer_on_bounce():
    bm = create.from_string(BOUNCE)
    ok_(bm.is_bounce())
    eq_('5.1.1', bm.bounce.status)
    ok_(bm.bounce.diagnostic_code)


def test_bounce_analyzer_on_regular():
    bm = create.from_string(SIGNED)
    assert_false(bm.is_bounce())


def test_bounce_no_headers_error_message():
    msg = create.from_string("Nothing")
    assert_false(msg.is_bounce())

########NEW FILE########
__FILENAME__ = create_test
# coding:utf-8

from nose.tools import *
from mock import *

import email
import json

from base64 import b64decode

from flanker.mime import create
from flanker.mime.message import errors
from flanker.mime.message.part import MimePart
from email.parser import Parser

from ... import *


def from_python_message_test():
    python_message = Parser().parsestr(MULTIPART)
    message = create.from_python(python_message)

    eq_(python_message['Subject'], message.headers['Subject'])

    ctypes = [p.get_content_type() for p in python_message.walk()]
    ctypes2 = [str(p.content_type) for p in message.walk(with_self=True)]
    eq_(ctypes, ctypes2)

    payloads = [p.get_payload(decode=True) for p in python_message.walk()][1:]
    payloads2 = [p.body for p in message.walk()]

    eq_(payloads, payloads2)


def from_string_message_test():
    message = create.from_string(IPHONE)
    parts = list(message.walk())
    eq_(3, len(parts))
    eq_(u'\n\n\n~Danielle', parts[2].body)


def from_part_message_simple_test():
    message = create.from_string(IPHONE)
    parts = list(message.walk())

    message = create.from_message(parts[2])
    eq_(u'\n\n\n~Danielle', message.body)


def message_from_garbage_test():
    assert_raises(errors.DecodingError, create.from_string, None)
    assert_raises(errors.DecodingError, create.from_string, [])
    assert_raises(errors.DecodingError, create.from_string, MimePart)


def create_singlepart_ascii_test():
    message = create.text("plain", u"Hello")
    message = create.from_string(message.to_string())
    eq_("7bit", message.content_encoding.value)
    eq_("Hello", message.body)


def create_singlepart_unicode_test():
    message = create.text("plain", u"Привет, курилка")
    message = create.from_string(message.to_string())
    eq_("base64", message.content_encoding.value)
    eq_(u"Привет, курилка", message.body)


def create_singlepart_ascii_long_lines_test():
    very_long = "very long line  " * 1000 + "preserve my newlines \r\n\r\n"
    message = create.text("plain", very_long)

    message2 = create.from_string(message.to_string())
    eq_("quoted-printable", message2.content_encoding.value)
    eq_(very_long, message2.body)

    message2 = email.message_from_string(message.to_string())
    eq_(very_long, message2.get_payload(decode=True))


def create_multipart_simple_test():
    message = create.multipart("mixed")
    message.append(
        create.text("plain", "Hello"),
        create.text("html", "<html>Hello</html>"))
    ok_(message.is_root())
    assert_false(message.parts[0].is_root())
    assert_false(message.parts[1].is_root())

    message2 = create.from_string(message.to_string())
    eq_(2, len(message2.parts))
    eq_("multipart/mixed", message2.content_type)
    eq_(2, len(message.parts))
    eq_("Hello", message.parts[0].body)
    eq_("<html>Hello</html>", message.parts[1].body)

    message2 = email.message_from_string(message.to_string())
    eq_("multipart/mixed", message2.get_content_type())
    eq_("Hello", message2.get_payload()[0].get_payload(decode=False))
    eq_("<html>Hello</html>",
        message2.get_payload()[1].get_payload(decode=False))


def create_multipart_with_attachment_test():
    message = create.multipart("mixed")
    filename = u"Мейлган картиночка картиночечка с длинным  именем и пробельчиками"
    message.append(
        create.text("plain", "Hello"),
        create.text("html", "<html>Hello</html>"),
        create.binary(
            "image", "png", MAILGUN_PNG,
            filename, "attachment"))
    eq_(3, len(message.parts))

    message2 = create.from_string(message.to_string())
    eq_(3, len(message2.parts))
    eq_("base64", message2.parts[2].content_encoding.value)
    eq_(MAILGUN_PNG, message2.parts[2].body)
    eq_(filename, message2.parts[2].content_disposition.params['filename'])
    eq_(filename, message2.parts[2].content_type.params['name'])
    ok_(message2.parts[2].is_attachment())

    message2 = email.message_from_string(message.to_string())
    eq_(3, len(message2.get_payload()))
    eq_(MAILGUN_PNG, message2.get_payload()[2].get_payload(decode=True))


def create_multipart_with_text_non_unicode_attachment_test():
    """Make sure we encode text attachment in base64
    """
    message = create.multipart("mixed")
    filename = "text-attachment.txt"
    message.append(
        create.text("plain", "Hello"),
        create.text("html", "<html>Hello</html>"),
        create.binary(
            "text", "plain", u"Саша с уралмаша".encode("koi8-r"),
            filename, "attachment"))

    message2 = create.from_string(message.to_string())

    eq_(3, len(message2.parts))
    attachment = message2.parts[2]
    ok_(attachment.is_attachment())
    eq_("base64", attachment.content_encoding.value)
    eq_(u"Саша с уралмаша", attachment.body)


def create_multipart_with_text_non_unicode_attachment_preserve_encoding_test():
    """Make sure we encode text attachment in base64
    and also preserve charset information
    """
    message = create.multipart("mixed")
    filename = "text-attachment.txt"
    message.append(
        create.text("plain", "Hello"),
        create.text("html", "<html>Hello</html>"),
        create.text(
            "plain",
            u"Саша с уралмаша 2".encode("koi8-r"),
            "koi8-r",
            "attachment",
            filename))

    message2 = create.from_string(message.to_string())

    eq_(3, len(message2.parts))
    attachment = message2.parts[2]
    ok_(attachment.is_attachment())
    eq_("base64", attachment.content_encoding.value)
    eq_("koi8-r", attachment.charset)
    eq_(u"Саша с уралмаша 2", attachment.body)


def create_multipart_nested_test():
    message = create.multipart("mixed")
    nested = create.multipart("alternative")
    nested.append(
        create.text("plain", u"Саша с уралмаша"),
        create.text("html", u"<html>Саша с уралмаша</html>"))
    message.append(
        create.text("plain", "Hello"),
        nested)

    message2 = create.from_string(message.to_string())
    eq_(2, len(message2.parts))
    eq_('text/plain', message2.parts[0].content_type)
    eq_('Hello', message2.parts[0].body)

    eq_(u"Саша с уралмаша", message2.parts[1].parts[0].body)
    eq_(u"<html>Саша с уралмаша</html>", message2.parts[1].parts[1].body)


def create_enclosed_test():
    message = create.text("plain", u"Превед")
    message.headers['From'] = u' Саша <sasha@mailgun.net>'
    message.headers['To'] = u'Женя <ev@mailgun.net>'
    message.headers['Subject'] = u"Все ли ок? Нормальненько??"

    message = create.message_container(message)

    message2 = create.from_string(message.to_string())
    eq_('message/rfc822', message2.content_type)
    eq_(u"Превед", message2.enclosed.body)
    eq_(u'Саша <sasha@mailgun.net>', message2.enclosed.headers['From'])


def create_enclosed_nested_test():
    nested = create.multipart("alternative")
    nested.append(
        create.text("plain", u"Саша с уралмаша"),
        create.text("html", u"<html>Саша с уралмаша</html>"))

    message = create.multipart("mailgun-recipient-variables")
    variables = {"a": u"<b>Саша</b>" * 1024}
    message.append(
        create.binary("application", "json", json.dumps(variables)),
        create.message_container(nested))

    message2 = create.from_string(message.to_string())
    eq_(variables, json.loads(message2.parts[0].body))

    nested = message2.parts[1].enclosed
    eq_(2, len(nested.parts))
    eq_(u"Саша с уралмаша", nested.parts[0].body)
    eq_(u"<html>Саша с уралмаша</html>", nested.parts[1].body)


def guessing_attachments_test():
    binary = create.binary(
        "application", 'octet-stream', MAILGUN_PNG, '/home/alex/mailgun.png')
    eq_('image/png', binary.content_type)
    eq_('mailgun.png', binary.content_type.params['name'])

    binary = create.binary(
        "application", 'octet-stream',
        MAILGUN_PIC, '/home/alex/mailgun.png', disposition='attachment')

    eq_('attachment', binary.headers['Content-Disposition'].value)
    eq_('mailgun.png', binary.headers['Content-Disposition'].params['filename'])

    binary = create.binary(
        "application", 'octet-stream', NOTIFICATION, '/home/alex/mailgun.eml')
    eq_('message/rfc822', binary.content_type)

    binary = create.binary(
        "application", 'octet-stream', MAILGUN_WAV, '/home/alex/audiofile.wav')
    eq_('audio/x-wav', binary.content_type)


def attaching_emails_test():
    attachment = create.attachment(
        "message/rfc822", MULTIPART, "message.eml", "attachment")
    eq_("message/rfc822", attachment.content_type)
    ok_(attachment.is_attachment())

    # now guess by file name
    attachment = create.attachment(
        "application/octet-stream", MULTIPART, "message.eml", "attachment")
    eq_("message/rfc822", attachment.content_type)


def attaching_images_test():
    attachment = create.attachment(
        "application/octet-stream", MAILGUN_PNG, "/home/alex/mailgun.png")
    eq_("image/png", attachment.content_type)


def attaching_text_test():
    attachment = create.attachment(
        "application/octet-stream",
        u"Привет, как дела".encode("koi8-r"), "/home/alex/hi.txt")
    eq_("text/plain", attachment.content_type)
    eq_(u"Привет, как дела", attachment.body)


def guessing_text_encoding_test():
    text = create.text("plain", "hello", "utf-8")
    eq_('ascii', text.charset)

    text = create.text("plain", u"hola, привет", "utf-8")
    eq_('utf-8', text.charset)


def create_long_lines_test():
    val = "hello" * 1024
    text = create.text("plain", val, "utf-8")
    eq_('ascii', text.charset)

    create.from_string(text.to_string())
    eq_(val, text.body)


def create_newlines_in_headers_test():
    text = create.text("plain", 'yo', "utf-8")
    text.headers['Subject'] = 'Hello,\nnewline\r\n\r\n'
    text.headers.add('To', u'\n\nПревед, медвед\n!\r\n')

    text = create.from_string(text.to_string())
    eq_('Hello,newline', text.headers['Subject'])
    eq_(u'Превед, медвед!', text.headers['To'])

########NEW FILE########
__FILENAME__ = fallback_test
# coding:utf-8

from nose.tools import *
from mock import *
import email
from flanker.mime.message.fallback import create
from flanker.mime.message import errors
from flanker.mime import recover
from cStringIO import StringIO
from contextlib import closing
from email import message_from_string

from .... import *

def bad_string_test():
    mime = "Content-Type: multipart/broken\n\n"
    message = create.from_string("Content-Type:multipart/broken")
    eq_(mime, message.to_string())
    with closing(StringIO()) as out:
        message.to_stream(out)
        eq_(mime, out.getvalue())
    list(message.walk())
    message.remove_headers()
    assert_false(message.is_attachment())
    assert_false(message.is_inline())
    assert_false(message.is_delivery_notification())
    assert_false(message.is_bounce())
    ok_(message.to_python_message())
    eq_(None, message.get_attached_message())
    ok_(str(message))


def bad_string_test_2():
    mime = "Content-Mype: multipart/broken\n\n"
    message = create.from_string(mime)
    ok_(message.content_type)
    eq_((None, {}), message.content_disposition)


def bad_python_test():
    message = create.from_python(
        message_from_string("Content-Type:multipart/broken"))
    ok_(message.to_string())
    with closing(StringIO()) as out:
        message.to_stream(out)
        ok_(out.getvalue())
    list(message.walk())
    message.remove_headers()
    assert_false(message.is_attachment())
    assert_false(message.is_inline())
    assert_false(message.is_delivery_notification())
    assert_false(message.is_bounce())
    ok_(message.to_python_message())
    eq_(None, message.get_attached_message())
    ok_(str(message))


def message_alter_body_and_serialize_test():
    message = create.from_string(IPHONE)

    parts = list(message.walk())
    eq_(3, len(parts))
    eq_(u'\n\n\n~Danielle', parts[2].body)
    eq_((None, {}), parts[2].content_disposition)
    eq_(('inline', {'filename': 'photo.JPG'}), parts[1].content_disposition)

    part = list(message.walk())[2]
    part.body = u'Привет, Danielle!\n\n'

    with closing(StringIO()) as out:
        message.to_stream(out)
        message1 = create.from_string(out.getvalue())
        message2 = create.from_string(message.to_string())

    parts = list(message1.walk())
    eq_(3, len(parts))
    eq_(u'Привет, Danielle!\n\n', parts[2].body)

    parts = list(message2.walk())
    eq_(3, len(parts))
    eq_(u'Привет, Danielle!\n\n', parts[2].body)


def message_content_dispositions_test():
    message = create.from_string(IPHONE)

    parts = list(message.walk())
    eq_((None, {}), parts[2].content_disposition)
    eq_(('inline', {'filename': 'photo.JPG'}), parts[1].content_disposition)

    message = create.from_string("Content-Disposition: Нельзя распарсить")
    parts = list(message.walk(with_self=True))
    eq_((None, {}), parts[0].content_disposition)


def message_from_python_test():
    message = create.from_python(email.message_from_string(ENCLOSED))
    eq_(2, len(message.parts))
    eq_('multipart/alternative', message.parts[1].enclosed.content_type)
    eq_('multipart/mixed', message.content_type)
    assert_false(message.body)

    message.headers['Sasha'] = 'Hello!'
    message.remove_headers("Subject", "Nonexisting")
    message.parts[1].enclosed.headers['Yo'] = u'Man'
    ok_(message.to_string())
    ok_(str(message))
    ok_(str(message.parts[0]))

    m = message.get_attached_message()
    eq_('multipart/alternative', str(m.content_type))
    eq_('Thanks!', m.headers['Subject'])


def torture_test():
    message = create.from_string(TORTURE)
    ok_(list(message.walk(with_self=True)))
    ok_(message.size)
    message.parts[0].content_encoding
    message.parts[0].content_encoding = 'blablac'

def text_only_test():
    message = create.from_string(TEXT_ONLY)
    eq_(u"Hello,\nI'm just testing message parsing\n\nBR,\nBob",
        message.body)
    eq_(None, message.bounce)
    eq_(None, message.get_attached_message())

def message_headers_test():
    message = create.from_python(email.message_from_string(ENCLOSED))

    ok_(message.headers)
    eq_(20, len(message.headers))

    # iterate a little bit
    for key, val in message.headers:
        ok_(key)
        ok_(val)

    for key, val in message.headers.items():
        ok_(key)
        ok_(val)

    for key, val in message.headers.iteritems():
        ok_(key)
        ok_(val)

    message.headers.prepend("Received", "Hi")
    message.headers.add("Received", "Yo")
    eq_(22, len(message.headers.keys()))
    ok_(message.headers.get("Received"))
    ok_(message.headers.getall("Received"))
    eq_("a", message.headers.get("Received-No", "a"))
    ok_(str(message.headers))


def bilingual_test():
    message = create.from_string(BILINGUAL)
    eq_(u"Simple text. How are you? Как ты поживаешь?",
        message.headers['Subject'])

    for key, val in message.headers:
        if key == 'Subject':
            eq_(u"Simple text. How are you? Как ты поживаешь?", val)

    message.headers['Subject'] = u"Да все ок!"
    eq_(u"Да все ок!", message.headers['Subject'])

    message = create.from_string(message.to_string())
    eq_(u"Да все ок!", message.headers['Subject'])

    eq_("", message.headers.get("SashaNotExists", ""))


def broken_headers_test():
    message = create.from_string(MAILFORMED_HEADERS)
    ok_(message.headers['Subject'])
    eq_(unicode, type(message.headers['Subject']))


def broken_headers_test_2():
    message = create.from_string(SPAM_BROKEN_HEADERS)
    ok_(message.headers['Subject'])
    eq_(unicode, type(message.headers['Subject']))
    eq_(('text/plain', {'charset': 'iso-8859-1'}),
        message.headers['Content-Type'])
    eq_(unicode, type(message.body))


def test_walk():
    message = recover(ENCLOSED)
    expected = [
        'multipart/mixed',
        'text/plain',
        'message/rfc822',
        'multipart/alternative',
        'text/plain',
        'text/html'
        ]
    eq_(expected[1:], [str(p.content_type) for p in message.walk()])
    eq_(expected, [str(p.content_type) for p in message.walk(with_self=True)])
    eq_(['text/plain', 'message/rfc822'],
        [str(p.content_type) for p in message.walk(skip_enclosed=True)])

########NEW FILE########
__FILENAME__ = encodedword_test
# coding:utf-8

from nose.tools import *
from mock import *
from flanker.mime.message.headers import encodedword
from flanker import utils
from flanker.mime.message import errors, charsets

def encoded_word_test():
    def t(value):
        m  = encodedword.encodedWord.match(value)
        return (m.group('charset'), m.group('encoding'), m.group('encoded'))

    r = t('=?utf-8?B?U2ltcGxlIHRleHQuIEhvdyBhcmUgeW91PyDQmtCw0Log0YLRiyDQv9C+0LY=?=')
    eq_(r[0], 'utf-8')
    eq_(r[1], 'B')
    eq_(r[2], 'U2ltcGxlIHRleHQuIEhvdyBhcmUgeW91PyDQmtCw0Log0YLRiyDQv9C+0LY=')

    r = t('=?UTF-8?Q?=D1=80=D1=83=D1=81=D1=81=D0=BA=D0=B8=D0=B9?=')
    eq_(r[0], 'UTF-8')
    eq_(r[1], 'Q')
    eq_(r[2], '=D1=80=D1=83=D1=81=D1=81=D0=BA=D0=B8=D0=B9')

    r = t('=?iso-8859-1?q?this=20is=20some=20text?=')
    eq_(r[0], 'iso-8859-1')
    eq_(r[1], 'q')
    eq_(r[2], 'this=20is=20some=20text')


def unfold_test():
    u = encodedword.unfold
    eq_('\t\t\t', u('\n\r\t\t\t'))
    eq_('\t\t\t', u('\n\t\t\t'))
    eq_('  ', u('\n\r  '))
    eq_('  ', u('\r\n  '))
    eq_('  ', u('\n  '))
    eq_('  ', u('\r  '))
    eq_(' \t', u('\n\r \t'))


def happy_mime_to_unicode_test():
    v = """   =?utf-8?B?U2ltcGxlIHRleHQuIEhvdyBhcmUgeW91PyDQmtCw0Log0YLRiyDQv9C+0LY=?=\n     =?utf-8?B?0LjQstCw0LXRiNGMPw==?="""
    eq_(u'Simple text. How are you? Как ты поживаешь?', encodedword.mime_to_unicode(v))

    v = ' =?US-ASCII?Q?Foo?= <foo@example.com>'
    eq_(u'Foo <foo@example.com>', encodedword.mime_to_unicode(v))

    v = '''=?UTF-8?Q?=D1=80=D1=83=D1=81=D1=81=D0=BA=D0=B8=D0=B9?=\n     =?UTF-8?Q?_=D0=B8?= english112      =?UTF-8?Q?=D1=81=D0=B0=D0=B1=D0=B6?= subject'''
    eq_(u'русский и english112      сабж subject', encodedword.mime_to_unicode(v))

    v = '=?iso-8859-1?B?SOlhdnkgTel05WwgVW7uY/hk?=\n\t=?iso-8859-1?Q?=E9?='
    eq_(u'Héavy Métål Unîcødé', encodedword.mime_to_unicode(v))


def lying_encodings_mime_to_unicode_test():
    v = '''=?US-ASCII?Q?=D1=80=D1=83=D1=81=D1=81=D0=BA=D0=B8=D0=B9?=\n     =?unknonw?Q?_=D0=B8?= english112      =?UTF-8?Q?=D1=81=D0=B0=D0=B1=D0=B6?= subject'''
    eq_(u'русский и english112      сабж subject', encodedword.mime_to_unicode(v))

def missing_padding_mime_to_unicode_test():
    v = """   =?utf-8?B?U2ltcGxlIHRleHQuIEhvdyBhcmUgeW91PyDQmtCw0Log0YLRiyDQv9C+0LY?=\n     =?utf-8?B?0LjQstCw0LXRiNGMPw?="""
    eq_(u'Simple text. How are you? Как ты поживаешь?', encodedword.mime_to_unicode(v))


def neutral_headings_test():
    v = '''from mail-iy0-f179.google.com (mail-iy0-f179.google.com
\t[209.85.210.179])
\tby mxa.mailgun.org (Postfix) with ESMTP id 2D0D3F01116
\tfor <alex@mailgun.net>; Fri, 17 Dec 2010 12:50:07 +0000 (UTC)'''
    eq_(u'from mail-iy0-f179.google.com (mail-iy0-f179.google.com\t[209.85.210.179])\tby mxa.mailgun.org (Postfix) with ESMTP id 2D0D3F01116\tfor <alex@mailgun.net>; Fri, 17 Dec 2010 12:50:07 +0000 (UTC)', encodedword.mime_to_unicode(v))

    v = '''multipart/mixed; boundary="===============7553021138737466228=="'''
    eq_(v, encodedword.mime_to_unicode(v))


def outlook_encodings_test():
    v = '''=?koi8-r?B?/NTPINPPz8Ldxc7JxSDTIMTMyc7O2c0g08HC1sXL1M/NINPQxcPJwQ==?=
            =?koi8-r?B?zNjOzyDe1M/C2SDQ0s/XxdLJ1Nggy8/EydLP18vJ?='''
    eq_(u"Это сообщение с длинным сабжектом специально чтобы проверить кодировки", encodedword.mime_to_unicode(v))

def gmail_encodings_test():
    v = ''' =?KOI8-R?B?/NTPINPPz8Ldxc7JxSDTIMTMyc7O2c0g08HC1g==?=
            =?KOI8-R?B?xcvUz80g09DFw8nBzNjOzyDe1M/C2SDQ0s/XxdLJ1A==?=
                    =?KOI8-R?B?2CDLz8TJ0s/Xy8k=?='''
    eq_(u"Это сообщение с длинным сабжектом специально чтобы проверить кодировки", encodedword.mime_to_unicode(v))


def aol_encodings_test():
    v = ''' =?utf-8?Q?=D0=AD=D1=82=D0=BE_=D1=81=D0=BE=D0=BE=D0=B1=D1=89=D0=B5=D0=BD?=
     =?utf-8?Q?=D0=B8=D0=B5_=D1=81_=D0=B4=D0=BB=D0=B8=D0=BD=D0=BD=D1=8B=D0=BC?=
      =?utf-8?Q?_=D1=81=D0=B0=D0=B1=D0=B6=D0=B5=D0=BA=D1=82=D0=BE=D0=BC_=D1=81?=
       =?utf-8?Q?=D0=BF=D0=B5=D1=86=D0=B8=D0=B0=D0=BB=D1=8C=D0=BD=D0=BE_=D1=87?=
        =?utf-8?Q?=D1=82=D0=BE=D0=B1=D1=8B_=D0=BF=D1=80=D0=BE=D0=B2=D0=B5=D1=80?=
         =?utf-8?Q?=D0=B8=D1=82=D1=8C_=D0=BA=D0=BE=D0=B4=D0=B8=D1=80=D0=BE=D0=B2?=
          =?utf-8?Q?=D0=BA=D0=B8?='''
    eq_(u"Это сообщение с длинным сабжектом специально чтобы проверить кодировки", encodedword.mime_to_unicode(v))


def yahoo_encodings_test():
    v = '''
     =?utf-8?B?0K3RgtC+INGB0L7QvtCx0YnQtdC90LjQtSDRgSDQtNC70LjQvdC90YvQvCA=?=
      =?utf-8?B?0YHQsNCx0LbQtdC60YLQvtC8INGB0L/QtdGG0LjQsNC70YzQvdC+INGH0YI=?=
       =?utf-8?B?0L7QsdGLINC/0YDQvtCy0LXRgNC40YLRjCDQutC+0LTQuNGA0L7QstC60Lg=?='''
    eq_(u"Это сообщение с длинным сабжектом специально чтобы проверить кодировки", encodedword.mime_to_unicode(v))


def hotmail_encodings_test():
    v = ''' =?koi8-r?B?/NTPINPPz8LdxQ==?= =?koi8-r?B?zsnFINMgxMzJzg==?=
     =?koi8-r?B?ztnNINPBwtbFyw==?= =?koi8-r?B?1M/NINPQxcPJwQ==?=
      =?koi8-r?B?zNjOzyDe1M/C2Q==?= =?koi8-r?B?INDSz9fF0snU2A==?=
       =?koi8-r?B?IMvPxMnSz9fLyQ==?='''
    eq_(u"Это сообщение с длинным сабжектом специально чтобы проверить кодировки", encodedword.mime_to_unicode(v))


def various_encodings_test():
    v = '"=?utf-8?b?6ICD5Y+W5YiG5Lqr?=" <foo@example.com>'
    eq_(u'"考取分享" <foo@example.com>', encodedword.mime_to_unicode(v))

    v = """=?UTF-8?B?0JbQtdC60LA=?= <ev@mailgun.net>, =?UTF-8?B?0JrQvtC90YbQtdCy0L7QuQ==?= <eugueny@gmail.com>"""
    eq_(u"Жека <ev@mailgun.net>, Концевой <eugueny@gmail.com>", encodedword.mime_to_unicode(v))

    v = encodedword.mime_to_unicode("=?utf-8?b?0JrQvtC90YbQtdCy0L7QuQ==?= <ev@host.com>, Bob <bob@host.com>, =?utf-8?b?0JLQuNC90YE=?= <vince@host.com>")
    eq_(u"Концевой <ev@host.com>, Bob <bob@host.com>, Винс <vince@host.com>", v)

    v = '=?UTF-8?B?0J/RgNC+0LLQtdGA0Y/QtdC8INGA0YPRgdGB0LrQuNC1INGB0LDQsdC2?=\n =?UTF-8?B?0LXQutGC0Ysg0Lgg0Y7QvdC40LrQvtC0IOKYoA==?='
    eq_(u'Проверяем русские сабжекты и юникод ☠', encodedword.mime_to_unicode(v))

    v = '=?UTF-8?B?0J/RgNC+0LLQtdGA0Y/QtdC8INGA0YPRgdGB0LrQuNC1INGB0LDQsdC2?=\r\n =?UTF-8?B?0LXQutGC0Ysg0Lgg0Y7QvdC40LrQvtC0IOKYoA==?='
    eq_(u'Проверяем русские сабжекты и юникод ☠', encodedword.mime_to_unicode(v))

    v = u'=?utf-8?Q?Evaneos-Concepci=C3=B3n.pdf?='
    eq_(u'Evaneos-Concepción.pdf', encodedword.mime_to_unicode(v))


@patch.object(utils, '_guess_and_convert', Mock(side_effect=errors.EncodingError()))
def test_convert_to_utf8_unknown_encoding():
    v = "abc\x80def"
    eq_(u"abc\u20acdef", charsets.convert_to_unicode("windows-874", v))
    eq_(u"qwe", charsets.convert_to_unicode('X-UNKNOWN', u"qwe"))
    eq_(u"qwe", charsets.convert_to_unicode('ru_RU.KOI8-R', 'qwe'))
    eq_(u"qwe", charsets.convert_to_unicode('"utf-8"; format="flowed"', 'qwe'))

@patch.object(encodedword, 'unfold', Mock(side_effect=Exception))
def test_error_reporting():
    eq_("Sasha", encodedword.mime_to_unicode("Sasha"))

########NEW FILE########
__FILENAME__ = encoding_test
# coding:utf-8

from email.header import Header

from nose.tools import eq_, ok_
from mock import patch, Mock

from flanker.mime.message import headers
from flanker.mime.message.headers.encoding import (encode_unstructured,
                                                   encode_string)
from flanker.mime.message import part
from flanker.mime import create
from tests import LONG_HEADER


def encodings_test():
    s = (u"Это сообщение с длинным сабжектом "
         u"специально чтобы проверить кодировки")

    eq_(s, headers.mime_to_unicode(headers.to_mime('Subject', s)))

    s = "this is sample ascii string"

    eq_(s, headers.to_mime('Subject',s))
    eq_(s, headers.mime_to_unicode(s))

    s = ("This is a long subject with commas, bob, Jay, suzy, tom, over"
         " 75,250,234 times!")
    folded_s = ("This is a long subject with commas, bob, Jay, suzy, tom, over"
                "\n 75,250,234 times!")
    eq_(folded_s, headers.to_mime('Subject', s))


def string_maxlinelen_test():
    """
    If the encoded string is longer then the maximum line length, which is 76,
    by default then it is broken down into lines. But a maximum line length
    value can be provided in the `maxlinelen` parameter.
    """
    eq_("very\n loooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooong",
        encode_string(None, "very loooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooong"))

    eq_("very loooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooong",
        encode_string(None, "very loooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooong", maxlinelen=78))


@patch.object(part.MimePart, 'was_changed', Mock(return_value=True))        
def max_header_length_test():
    message = create.from_string(LONG_HEADER)
    # this used to fail because exceeded max depth recursion
    ok_(message.headers["Subject"].encode("utf-8") in message.to_string())

    unicode_subject = (u"Это сообщение с длинным сабжектом "
                       u"специально чтобы проверить кодировки")
    ascii_subject = "This is simple ascii subject"

    with patch.object(
        headers.encoding, 'MAX_HEADER_LENGTH', len(ascii_subject) + 1):

        eq_(Header(ascii_subject.encode("ascii"), "ascii", header_name="Subject"),
            encode_unstructured("Subject", ascii_subject))

    with patch.object(
        headers.encoding, 'MAX_HEADER_LENGTH', len(unicode_subject) + 1):

        eq_(Header(unicode_subject.encode("utf-8"), "utf-8", header_name="Subject"),
            encode_unstructured("Subject", unicode_subject))

    with patch.object(headers.encoding, 'MAX_HEADER_LENGTH', 1):

        eq_(ascii_subject.encode("utf-8"),
            encode_unstructured("Subject", ascii_subject))

        eq_(unicode_subject.encode("utf-8"),
            encode_unstructured("Subject", unicode_subject))

########NEW FILE########
__FILENAME__ = headers_test
# coding:utf-8

import zlib

from nose.tools import *
from mock import *
from flanker.mime.message.headers import MimeHeaders
from flanker.mime.message.errors import DecodingError
from cStringIO import StringIO

from .... import *

def headers_case_insensitivity_test():
    h = MimeHeaders()
    h['Content-Type'] = 1
    eq_(1, h['Content-Type'])
    eq_(1, h['conTenT-TyPE'])
    ok_('cOnTenT-TyPE' in h)
    ok_('Content-Type' in h)
    eq_(1, h.get('Content-Type'))
    eq_(None, h.get('Content-Type2'))
    eq_([('Content-Type', 1)], h.items())


def headers_order_preserved_test():
    headers = [('mime-version', '1'), ('rEceived', '2'), ('mime-version', '3'), ('ReceiveD', '4')]
    h = MimeHeaders(headers)

    # various types of iterations
    should_be = [('Mime-Version', '1'), ('Received', '2'), ('Mime-Version', '3'), ('Received', '4')]
    eq_(should_be, h.items())
    ok_(isinstance(h.items(), list))
    eq_(should_be, [p for p in h.iteritems()])

    # iterate over keys
    keys = ['Mime-Version', 'Received', 'Mime-Version', 'Received']
    eq_(keys, [p for p in h])
    eq_(keys, h.keys())


def headers_boolean_test():
    eq_(False, bool(MimeHeaders()))
    eq_(True, bool(MimeHeaders([('A', 1)])))

def headers_to_string_test():
    ok_(str(MimeHeaders([('A', 1)])))


def headers_multiple_values_test():
    headers = [('mime-version', '1'), ('rEceived', '2'), ('mime-version', '3'), ('ReceiveD', '4')]
    h = MimeHeaders(headers)
    eq_(['1', '3'], h.getall('Mime-Version'))

    # set re-sets all values for the message
    h['Mime-Version'] = '5'
    eq_(['5'], h.getall('Mime-Version'))

    # use add to add more values
    h.add('Received', '6')
    eq_(['2', '4', '6'], h.getall('Received'))

    # use prepend to insert header in the begining of the list
    h.prepend('Received', '0')
    eq_(['0', '2', '4', '6'], h.getall('Received'))

    # delete removes it all!
    del h['RECEIVED']
    eq_([], h.getall('Received'))


def headers_length_test():
    h = MimeHeaders()
    eq_(0, len(h))

    headers = [('mime-version', '1'), ('rEceived', '2'), ('mime-version', '3'), ('ReceiveD', '4')]
    h = MimeHeaders(headers)
    eq_(4, len(h))


def headers_alternation_test():
    headers = [('mime-version', '1'), ('rEceived', '2'), ('mime-version', '3'), ('ReceiveD', '4')]

    h = MimeHeaders(headers)
    assert_false(h.have_changed())

    h.prepend('Received', 'Yo')
    ok_(h.have_changed())

    h = MimeHeaders(headers)
    del h['Mime-Version']
    ok_(h.have_changed())

    h = MimeHeaders(headers)
    h['Mime-Version'] = 'a'
    ok_(h.have_changed())

    h = MimeHeaders(headers)
    h.add('Mime-Version', 'a')
    ok_(h.have_changed())

    h = MimeHeaders(headers)
    h.getall('Mime-Version')
    h.get('o')
    assert_false(h.have_changed())


def headers_transform_test():
    headers = [('mime-version', '1'), ('rEceived', '2'), ('mime-version', '3'), ('ReceiveD', '4')]

    h = MimeHeaders(headers)

    # transform tracks whether anything actually changed
    h.transform(lambda key,val: (key, val))
    assert_false(h.have_changed())

    # ok, now something have changed, make sure we've preserved order and did not collapse anything
    h.transform(lambda key,val: ("X-{0}".format(key), "t({0})".format(val)))
    ok_(h.have_changed())

    eq_([('X-Mime-Version', 't(1)'), ('X-Received', 't(2)'), ('X-Mime-Version', 't(3)'), ('X-Received', 't(4)')], h.items())


def headers_parsing_empty_test():
    h = MimeHeaders.from_stream(StringIO(""))
    eq_(0, len(h))

def headers_parsing_ridiculously_long_line_test():
    val = "abcdefg"*100000
    header = "Hello: {0}\r\n".format(val)
    assert_raises(
        DecodingError, MimeHeaders.from_stream, StringIO(header))


def headers_parsing_binary_stuff_survives_test():
    value = zlib.compress("abcdefg")
    header = "Hello: {0}\r\n".format(value)
    assert_raises(
        DecodingError, MimeHeaders.from_stream, StringIO(header))


def broken_sequences_test():
    headers = StringIO("  hello this is a bad header\nGood: this one is ok")
    headers = MimeHeaders.from_stream(headers)
    eq_(1, len(headers))
    eq_("this one is ok", headers["Good"])


def bilingual_message_test():
    headers = MimeHeaders.from_stream(StringIO(BILINGUAL))
    eq_(21, len(headers))
    eq_(u"Simple text. How are you? Как ты поживаешь?", headers['Subject'])
    received_headers = headers.getall('Received')
    eq_(5, len(received_headers))
    ok_('c2cs24435ybk' in received_headers[0])


def headers_roundtrip_test():
    headers = MimeHeaders.from_stream(StringIO(BILINGUAL))
    out = StringIO()
    headers.to_stream(out)

    headers2 = MimeHeaders.from_stream(StringIO(out.getvalue()))
    eq_(21, len(headers2))
    eq_(u"Simple text. How are you? Как ты поживаешь?", headers['Subject'])
    received_headers = headers.getall('Received')
    eq_(5, len(received_headers))
    ok_('c2cs24435ybk' in received_headers[0])
    eq_(headers['Content-Transfer-Encoding'],
        headers2['Content-Transfer-Encoding'])
    eq_(headers['DKIM-Signature'],
        headers2['DKIM-Signature'])



def test_folding_combinations():
    message = """From mrc@example.com Mon Feb  8 02:53:47 PST 1993\nTo: sasha\r\n  continued\n      line\nFrom: single line  \r\nSubject: hello, how are you\r\n today?"""
    headers = MimeHeaders.from_stream(StringIO(message))
    eq_('sasha  continued      line', headers['To'])
    eq_('single line  ', headers['From'])
    eq_("hello, how are you today?", headers['Subject'])

########NEW FILE########
__FILENAME__ = parametrized_test
# coding:utf-8

from nose.tools import *
from mock import *
from flanker.mime.message.headers import parametrized

def old_style_test_google():
    h = """image/png;
	name="=?KOI8-R?B?68HS1MnOy8Eg0yDP3sXO2Cwgz97FztggxMzJzs7ZzSA=?=
	=?KOI8-R?B?0NLFxMzJzs7ZzSDJzcXOxc0g0NLFyc3FzsXNINTByw==?=
	=?KOI8-R?B?yc0g3tTPINTP3s7PINrBys3F1CDU1d7VINDSxdTV3tUg?=
	=?KOI8-R?B?zcXT1MEg0NLT1M8gz8bJx8XU2C5wbmc=?="""
    eq_(('image/png', {'name': u'Картинка с очень, очень длинным предлинным именем преименем таким что точно займет тучу претучу места прсто офигеть.png'}), parametrized.decode(h))


def old_style_test_aol():
    h = '''image/png; name="=?utf-8?Q?=D0=9A=D0=B0=D1=80=D1=82=D0=B8=D0=BD=D0=BA=D0=B0_=D1=81_?=
 =?utf-8?Q?=D0=BE=D1=87=D0=B5=D0=BD=D1=8C,_=D0=BE=D1=87=D0=B5=D0=BD?=
 =?utf-8?Q?=D1=8C_=D0=B4=D0=BB=D0=B8=D0=BD=D0=BD=D1=8B=D0=BC_=D0=BF?=
 =?utf-8?Q?=D1=80=D0=B5=D0=B4=D0=BB=D0=B8=D0=BD=D0=BD=D1=8B=D0=BC_=D0=B8?=
 =?utf-8?Q?=D0=BC=D0=B5=D0=BD=D0=B5=D0=BC_=D0=BF=D1=80=D0=B5=D0=B8=D0=BC?=
 =?utf-8?Q?=D0=B5=D0=BD=D0=B5=D0=BC_=D1=82=D0=B0=D0=BA=D0=B8=D0=BC_?=
 =?utf-8?Q?=D1=87=D1=82=D0=BE_=D1=82=D0=BE=D1=87=D0=BD=D0=BE_=D0=B7?=
 =?utf-8?Q?=D0=B0=D0=B9=D0=BC=D0=B5=D1=82_=D1=82=D1=83=D1=87=D1=83_?=
 =?utf-8?Q?=D0=BF=D1=80=D0=B5=D1=82=D1=83=D1=87=D1=83_=D0=BC=D0=B5=D1=81?=
 =?utf-8?Q?=D1=82=D0=B0_=D0=BF=D1=80=D1=81=D1=82=D0=BE_=D0=BE=D1=84?=
 =?utf-8?Q?=D0=B8=D0=B3=D0=B5=D1=82=D1=8C.png?="'''
    eq_(('image/png', {'name': u'Картинка с очень, очень длинным предлинным именем преименем таким что точно займет тучу претучу места прсто офигеть.png'}), parametrized.decode(h))


def new_style_test():
    # missing ;
    h = ''' application/x-stuff
    title*0*=us-ascii'en'This%20is%20even%20more%20
    title*1*=%2A%2A%2Afun%2A%2A%2A%20
    title*2="isn't it!"'''
    eq_(('application/x-stuff', {'title': u"This is even more ***fun*** isn't it!"}), parametrized.decode(h))

    h = '''message/external-body; access-type=URL;
         URL*0="ftp://";
         URL*1="cs.utk.edu/pub/moore/bulk-mailer/bulk-mailer.tar"'''
    eq_(('message/external-body', {'access-type': 'URL', 'url': u"ftp://cs.utk.edu/pub/moore/bulk-mailer/bulk-mailer.tar"}), parametrized.decode(h))


    h = '''application/x-stuff;
         title*=us-ascii'en-us'This%20is%20%2A%2A%2Afun%2A%2A%2A'''
    eq_(('application/x-stuff', {'title': u"This is ***fun***"}),
        parametrized.decode(h))


def simple_test():
    eq_(("message/rfc822", {}), parametrized.decode("MESSAGE/RFC822"))
    eq_(("text/plain", {}), parametrized.decode("text/plain (this is text)"))


def broken_test():
    eq_((None, {}), parametrized.decode(""))


def content_types_test():
    eq_(('binary', {'name': 'Alices_PDP-10'}), parametrized.decode('''BINARY;name="Alices_PDP-10"'''))
    eq_(('multipart/mixed', {'boundary': 'mail.sleepy.sau.158.532'}), parametrized.decode('''MULTIPART/MIXED;boundary="mail.sleepy.sau.158.532"'''))
    eq_(('multipart/mixed', {'boundary': 'Where_No_Man_Has_Gone_Before'}), parametrized.decode('''MULTIPART/MIXED;boundary=Where_No_Man_Has_Gone_Before'''))
    eq_(('multipart/mixed', {'boundary': 'Alternative_Boundary_8dJn:mu0M2Yt5KaFZ8AdJn:mu0M2=Yt1KaFdA'}), parametrized.decode(''' multipart/mixed; \n\tboundary="Alternative_Boundary_8dJn:mu0M2Yt5KaFZ8AdJn:mu0M2=Yt1KaFdA"'''))
    eq_(('multipart/mixed', {'boundary': '16819560-2078917053-688350843:#11603'}), parametrized.decode('''MULTIPART/MIXED;BOUNDARY="16819560-2078917053-688350843:#11603"'''))

def content_type_param_with_spaces_test():
    eq_(('multipart/alternative',{'boundary':'nextPart'}), parametrized.decode("multipart/alternative; boundary = nextPart"))

########NEW FILE########
__FILENAME__ = part_test
# coding:utf-8
import re
from nose.tools import *
from mock import *
from flanker.mime.create import multipart, text
from flanker.mime.message.scanner import scan
from flanker.mime.message.errors import EncodingError, DecodingError
from email import message_from_string
from contextlib import closing
from cStringIO import StringIO
from flanker.mime.message.part import encode_transfer_encoding

from ... import *
from .scanner_test import TORTURE_PARTS, tree_to_string


def readonly_immutability_test():
    """We can read the headers and access the body without changing a single
    char inside the message"""

    message = scan(BILINGUAL)
    eq_(u"Simple text. How are you? Как ты поживаешь?",
        message.headers['Subject'])
    assert_false(message.was_changed())
    eq_(BILINGUAL, message.to_string())

    message = scan(ENCLOSED)
    pmessage = message_from_string(ENCLOSED)

    # we can read the headers without changing anything
    eq_(u'"Александр Клижентас☯" <bob@example.com>',
        message.headers['To'])
    eq_('Bob Marley <bob@example.net>, Jimmy Hendrix <jimmy@examplehq.com>',
        message.parts[1].enclosed.headers['To'])
    assert_false(message.was_changed())

    # we can also read the body without changing anything
    pbody = pmessage.get_payload()[1].get_payload()[0].get_payload()[0].get_payload(decode=True)
    pbody = unicode(pbody, 'utf-8')
    eq_(pbody, message.parts[1].enclosed.parts[0].body)
    assert_false(message.was_changed())
    eq_(ENCLOSED, message.to_string())


def top_level_headers_immutability_test():
    """We can change the headers without changing the body"""
    message = scan(ENCLOSED)
    message.headers['Subject'] = u'☯Привет! Как дела? Что делаешь?☯'
    out = message.to_string()
    a = ENCLOSED.split("--===============6195527458677812340==", 1)[1]
    b = out.split("--===============6195527458677812340==", 1)[1]
    eq_(a, b, "Bodies should not be changed in any way")


def immutability_test():
    """We can read the headers without changing a single
    char inside the message"""
    message = scan(BILINGUAL)
    eq_(u"Simple text. How are you? Как ты поживаешь?",
        message.headers['Subject'])
    eq_(BILINGUAL, message.to_string())

    message = scan(TORTURE)
    eq_('Multi-media mail demonstration ', message.headers['Subject'])
    eq_(TORTURE, message.to_string())

    message = scan(TORTURE)
    eq_('Multi-media mail demonstration ', message.headers['Subject'])
    with closing(StringIO()) as out:
        message.to_stream(out)
        eq_(TORTURE.rstrip(), out.getvalue().rstrip())


def enclosed_first_part_alternation_test():
    """We've changed one part of the message only, the rest was not changed"""
    message = scan(ENCLOSED)
    message.parts[0].body = 'Hey!\n'
    out = message.to_string()

    a = ENCLOSED.split("--===============6195527458677812340==", 2)[2]
    b = out.split("--===============6195527458677812340==", 2)[2]
    eq_(a, b, "Enclosed message should not be changed")

    message2 = scan(out)
    eq_('Hey!\n', message2.parts[0].body)
    eq_(message.parts[1].enclosed.parts[1].body,
        message2.parts[1].enclosed.parts[1].body)


def enclosed_header_alternation_test():
    """We've changed the headers in the inner part of the message only,
    the rest was not changed"""
    message = scan(ENCLOSED)

    enclosed = message.parts[1].enclosed
    enclosed.headers['Subject'] = u'☯Привет! Как дела? Что делаешь?☯'
    out = message.to_string()

    a = ENCLOSED.split("--===============4360815924781479146==", 1)[1]
    a = a.split("--===============4360815924781479146==--")[0]

    b = out.split("--===============4360815924781479146==", 1)[1]
    b = b.split("--===============4360815924781479146==--")[0]
    eq_(a, b)


def enclosed_header_inner_alternation_test():
    """We've changed the headers in the inner part of the message only,
    the rest was not changed"""
    message = scan(ENCLOSED)

    unicode_value = u'☯Привет! Как дела? Что делаешь?☯'
    enclosed = message.parts[1].enclosed
    enclosed.parts[0].headers['Subject'] = unicode_value

    message2 = scan(message.to_string())
    enclosed2 = message2.parts[1].enclosed

    eq_(unicode_value, enclosed2.parts[0].headers['Subject'])
    eq_(enclosed.parts[0].body, enclosed2.parts[0].body)
    eq_(enclosed.parts[1].body, enclosed2.parts[1].body)



def enclosed_body_alternation_test():
    """We've changed the body in the inner part of the message only,
    the rest was not changed"""
    message = scan(ENCLOSED)

    value = u'☯Привет! Как дела? Что делаешь?, \r\n\r Что новенького?☯'
    enclosed = message.parts[1].enclosed
    enclosed.parts[0].body = value
    out = message.to_string()

    message = scan(out)
    enclosed = message.parts[1].enclosed
    eq_(value, enclosed.parts[0].body)


def enclosed_inner_part_no_headers_test():
    """We've changed the inner part of the entity that has no headers,
    make sure that it was processed correctly"""
    message = scan(TORTURE_PART)

    enclosed = message.parts[1].enclosed
    no_headers = enclosed.parts[0]
    assert_false(no_headers.headers)
    no_headers.body = no_headers.body + "Mailgun!"

    message = scan(message.to_string())
    enclosed = message.parts[1].enclosed
    no_headers = enclosed.parts[0]
    ok_(no_headers.body.endswith("Mailgun!"))


def enclosed_broken_encoding_test():
    """ Make sure we can serialize the message even in case of Decoding errors,
    in this case fallback happens"""

    message = scan(ENCLOSED_BROKEN_ENCODING)
    for p in message.walk():
        try:
            p.headers['A'] = 'b'
        except:
            pass
    with closing(StringIO()) as out:
        message.to_stream(out)
        ok_(out.getvalue())



def double_serialization_test():
    message = scan(TORTURE)
    message.headers['Subject'] = u'Поменяли текст ☢'

    a = message.to_string()
    b = message.to_string()
    with closing(StringIO()) as out:
        message.to_stream(out)
        c = out.getvalue()
    eq_(a, b)
    eq_(b, c)


def preserve_content_encoding_test_8bit():
    """ Make sure that content encoding will be preserved if possible"""
    # 8bit messages
    unicode_value = u'☯Привет! Как дела? Что делаешь?,\n Что новенького?☯'

    # should remain 8bit
    message = scan(EIGHT_BIT)
    message.parts[0].body = unicode_value

    message = scan(message.to_string())
    eq_(unicode_value, message.parts[0].body)
    eq_('8bit', message.parts[0].content_encoding.value)


def preserve_content_encoding_test_quoted_printable():
    """ Make sure that quoted-printable remains quoted-printable"""
    # should remain 8bit
    unicode_value = u'☯Привет! Как дела? Что делаешь?,\n Что новенького?☯'
    message = scan(QUOTED_PRINTABLE)
    body = message.parts[0].body
    message.parts[0].body = body + unicode_value

    message = scan(message.to_string())
    eq_(body + unicode_value, message.parts[0].body)
    eq_('quoted-printable', message.parts[0].content_encoding.value)


def preserve_ascii_test():
    """Make sure that ascii remains ascii whenever possible"""
    # should remain ascii
    message = scan(TEXT_ONLY)
    message.body = u'Hello, how is it going?'
    message = scan(message.to_string())
    eq_('7bit', message.content_encoding.value)


def ascii_to_unicode_test():
    """Make sure that ascii uprades to unicode whenever needed"""
    # contains unicode chars
    message = scan(TEXT_ONLY)
    unicode_value = u'☯Привет! Как дела? Что делаешь?,\n Что новенького?☯'
    message.body = unicode_value
    message = scan(message.to_string())
    eq_('base64', message.content_encoding.value)
    eq_('utf-8', message.content_type.get_charset())
    eq_(unicode_value, message.body)


def ascii_to_quoted_printable_test():
    """Make sure that ascii uprades to quoted-printable if it has long lines"""
    # contains unicode chars
    message = scan(TEXT_ONLY)
    value = u'Hello, how is it going?' * 100
    message.body = value
    message = scan(message.to_string())
    eq_('quoted-printable', message.content_encoding.value)
    eq_('iso-8859-1', message.content_type.get_charset())
    eq_('iso-8859-1', message.charset)
    eq_(value, message.body)


def create_message_without_headers_test():
    """Make sure we can't create a message without headers"""
    message = scan(TEXT_ONLY)
    for h,v in message.headers.items():
        del message.headers[h]

    assert_false(message.headers, message.headers)
    assert_raises(EncodingError, message.to_string)


def create_message_without_body_test():
    """Make sure we can't create a message without headers"""
    message = scan(TEXT_ONLY)
    message.body = ""
    message = scan(message.to_string())
    eq_('', message.body)


def torture_alter_test():
    """Alter the complex message, make sure that the structure
    remained the same"""
    message = scan(TORTURE)
    unicode_value = u'☯Привет! Как дела? Что делаешь?,\n Что новенького?☯'
    message.parts[5].enclosed.parts[0].parts[0].body = unicode_value
    for p in message.walk():
        if str(p.content_type) == 'text/plain':
            p.body = unicode_value
            p.headers['Mailgun-Altered'] = u'Oh yeah'

    message = scan(message.to_string())

    eq_(unicode_value, message.parts[5].enclosed.parts[0].parts[0].body)

    tree = tree_to_string(message).splitlines()
    expected = TORTURE_PARTS.splitlines()
    eq_(len(tree), len(expected))
    for a, b in zip(expected, tree):
        eq_(a, b)


def walk_test():
    message = scan(ENCLOSED)
    expected = [
        'multipart/mixed',
        'text/plain',
        'message/rfc822',
        'multipart/alternative',
        'text/plain',
        'text/html'
        ]
    eq_(expected[1:], [str(p.content_type) for p in message.walk()])
    eq_(expected, [str(p.content_type) for p in message.walk(with_self=True)])
    eq_(['text/plain', 'message/rfc822'],
        [str(p.content_type) for p in message.walk(skip_enclosed=True)])


def to_string_test():
    ok_(str(scan(ENCLOSED)))
    ok_(str(scan(TORTURE)))


def broken_body_test():
    message = scan(ENCLOSED_BROKEN_BODY)
    assert_raises(DecodingError, message.parts[1].enclosed.parts[0]._container._load_body)


def broken_ctype_test():
    """Yahoo fails with russian attachments"""
    message = scan(RUSSIAN_ATTACH_YAHOO)
    assert_raises(
        DecodingError, lambda x: [p.headers for p in message.walk()], 1)

def read_attach_test():
    message = scan(MAILGUN_PIC)
    p = (p for p in message.walk() if p.content_type.main == 'image').next()
    eq_(p.body, MAILGUN_PNG)


def from_python_message_test():
    python_message = message_from_string(MULTIPART)
    message = scan(python_message.as_string())

    eq_(python_message['Subject'], message.headers['Subject'])

    ctypes = [p.get_content_type() for p in python_message.walk()]
    ctypes2 = [p.headers['Content-Type'][0] \
                  for p in message.walk(with_self=True)]
    eq_(ctypes, ctypes2)

    payloads = [p.get_payload(decode=True) for p in python_message.walk()][1:]
    payloads2 = [p.body for p in message.walk()]

    eq_(payloads, payloads2)


def iphone_test():
    message = scan(IPHONE)
    eq_(u'\n\n\n~Danielle', list(message.walk())[2].body)


def content_types_test():
    part = scan(IPHONE)
    eq_((None, {}), part.content_disposition)
    assert_false(part.is_attachment())

    eq_(('inline', {'filename': 'photo.JPG'}), part.parts[1].content_disposition)
    assert_false(part.parts[1].is_attachment())
    ok_(part.parts[1].is_inline())

    part = scan(SPAM_BROKEN_CTYPE)
    eq_((None, {}), part.content_disposition)

    part = scan(MAILGUN_PIC)
    attachment = part.parts[1]
    eq_('image/png', attachment.detected_content_type)
    eq_('png', attachment.detected_subtype)
    eq_('image', attachment.detected_format)
    ok_(not attachment.is_body())


def test_is_body():
    part = scan(IPHONE)
    ok_(part.parts[0].is_body())


def message_attached_test():
    message = scan(BOUNCE)
    message = message.get_attached_message()
    eq_('"Foo B. Baz" <foo@example.com>', message.headers['From'])


def message_attached_does_not_exist_test():
    message = scan(IPHONE)
    eq_(None, message.get_attached_message())


def message_remove_headers_test():
    message = scan(TORTURE)
    message.remove_headers('X-Status', 'X-Keywords', 'X-UID', 'Nothere')
    message = scan(message.to_string())
    for h in ('X-Status', 'X-Keywords', 'X-UID', 'Nothere'):
        ok_(h not in message.headers)


def message_alter_body_and_serialize_test():
    message = scan(IPHONE)
    part = list(message.walk())[2]
    part.body = u'Привет, Danielle!\n\n'

    with closing(StringIO()) as out:
        message.to_stream(out)
        message1 = scan(out.getvalue())
        message2 = scan(message.to_string())

    parts = list(message1.walk())
    eq_(3, len(parts))
    eq_(u'Привет, Danielle!\n\n', parts[2].body)

    parts = list(message2.walk())
    eq_(3, len(parts))
    eq_(u'Привет, Danielle!\n\n', parts[2].body)


def alter_message_test_size():
    # check to make sure size is recalculated after header changed
    stream_part = scan(IPHONE)
    size_before = stream_part.size

    stream_part.headers.add('foo', 'bar')
    size_after = stream_part.size

    eq_(size_before, len(IPHONE))
    eq_(size_after, len(stream_part.to_string()))


def message_size_test():
    # message part as a stream
    stream_part = scan(IPHONE)
    eq_(len(IPHONE), stream_part.size)

    # assemble a message part
    text1 = 'Hey there'
    text2 = 'I am a part number two!!!'
    message = multipart('alternative')
    message.append(
        text('plain', text1),
        text('plain', text2))

    eq_(len(message.to_string()), message.size)


def message_convert_to_python_test():
    message = scan(IPHONE)
    a = message.to_python_message()

    for p in message.walk():
        if p.content_type.main == 'text':
            p.body = p.body
    b = message.to_python_message()

    payloads = [p.body for p in message.walk()]
    payloads1 = list(p.get_payload(decode=True) \
                         for p in a.walk() if not p.is_multipart())
    payloads2 = list(p.get_payload(decode=True) \
                         for p in b.walk() if not p.is_multipart())

    eq_(payloads, payloads2)
    eq_(payloads1, payloads2)


def message_is_bounce_test():
    message = scan(BOUNCE)
    ok_(message.is_bounce())

    message = scan(IPHONE)
    assert_false(message.is_bounce())


def message_is_delivery_notification_test():
    message = scan(NDN)
    ok_(message.is_delivery_notification())
    message = scan(BOUNCE)
    ok_(message.is_delivery_notification())

    message = scan(IPHONE)
    assert_false(message.is_delivery_notification())


def read_body_test():
    """ Make sure we've set up boundaries correctly and
    methods that read raw bodies work fine """
    part = scan(MULTIPART)
    eq_(MULTIPART, part._container.read_message())

    # the body of the multipart message is everything after the message
    body = "--bd1" + MULTIPART.split("--bd1", 1)[1]
    eq_(body, part._container.read_body())

    # body of the text part is the value itself
    eq_('Sasha\r\n', part.parts[0]._container.read_body())

    # body of the inner mime part is the part after the headers
    # and till the outer boundary
    body = "--bd2\r\n" + MULTIPART.split(
        "--bd2\r\n", 1)[1].split("--bd1--", 1)[0]
    eq_(body, part.parts[1]._container.read_body())

    # this is a simple message, make sure we can read the body
    # correctly
    part = scan(NO_CTYPE)
    eq_(NO_CTYPE, part._container.read_message())
    eq_("Hello,\nI'm just testing message parsing\n\nBR,\nBob", part._container.read_body())

    # multipart/related
    part = scan(RELATIVE)
    eq_(RELATIVE, part._container.read_message())
    eq_("""This is html and text message, thanks\r\n\r\n-- \r\nRegards,\r\nBob\r\n""", part.parts[0]._container.read_body())

    # enclosed
    part = scan(ENCLOSED)
    eq_(ENCLOSED, part._container.read_message())
    body = part.parts[1]._container.read_body()
    ok_(body.endswith("--===============4360815924781479146==--"))


def test_encode_transfer_encoding():
    body = "long line " * 100
    encoded_body = encode_transfer_encoding('base64', body)
    # according to  RFC 5322 line "SHOULD be no more than 78 characters"
    assert_less(max([len(l) for l in encoded_body.splitlines()]), 79)

########NEW FILE########
__FILENAME__ = scanner_test
# coding:utf-8
from nose.tools import *
from mock import *
from flanker.mime.message.scanner import scan, ContentType, Boundary
from flanker.mime.message.errors import DecodingError
from email import message_from_string

from ... import *

C = ContentType
B = Boundary


def no_ctype_headers_and_and_boundaries_test():
    """We are ok, when there is no content type and boundaries"""
    message = scan(NO_CTYPE)
    eq_(C('text', 'plain', dict(charset='ascii')), message.content_type)
    pmessage = message_from_string(NO_CTYPE)
    eq_(message.body, pmessage.get_payload(decode=True))
    for a, b in zip(NO_CTYPE_HEADERS, message.headers.iteritems()):
        eq_(a, b)


def multipart_message_test():
    message = scan(EIGHT_BIT)
    pmessage = message_from_string(EIGHT_BIT)

    eq_(C('multipart', 'alternative', dict(boundary='=-omjqkVTVbwdgCWFRgIkx')),
        message.content_type)

    p = unicode(pmessage.get_payload()[0].get_payload(decode=True), 'utf-8')
    eq_(p, message.parts[0].body)

    p = pmessage.get_payload()[1].get_payload(decode=True)
    eq_(p, message.parts[1].body)


def enclosed_message_test():
    message = scan(ENCLOSED)
    pmessage = message_from_string(ENCLOSED)

    eq_(C('multipart', 'mixed',
          dict(boundary='===============6195527458677812340==')),
        message.content_type)
    eq_(u'"Александр Клижентас☯" <bob@example.com>',
        message.headers['To'])

    eq_(pmessage.get_payload()[0].get_payload(), message.parts[0].body)

    enclosed = message.parts[1]
    penclosed = pmessage.get_payload(1)

    eq_(('message/rfc822', {'name': u'thanks.eml'},),
        enclosed.headers['Content-Type'])

    pbody = penclosed.get_payload()[0].get_payload()[0].get_payload(decode=True)
    pbody = unicode(pbody, 'utf-8')
    body = enclosed.enclosed.parts[0].body
    eq_(pbody, body)

    body = enclosed.enclosed.parts[1].body
    pbody = penclosed.get_payload()[0].get_payload()[1].get_payload(decode=True)
    pbody = unicode(pbody, 'utf-8')
    eq_(pbody, body)


def torture_message_test():
    message = scan(TORTURE)
    tree = tree_to_string(message).splitlines()
    expected = TORTURE_PARTS.splitlines()
    eq_(len(tree), len(expected))
    for a, b in zip(expected, tree):
        eq_(a, b)


def fbl_test():
    message = scan(AOL_FBL)
    eq_(3, len(message.parts))


def ndn_test():
    message = scan(NDN)
    ok_(message.is_delivery_notification())
    eq_(3, len(message.parts))
    eq_('Returned mail: Cannot send message for 5 days',
        message.headers['Subject'])
    eq_('text/plain', message.parts[0].content_type)
    ok_(message.parts[1].content_type.is_delivery_status())
    ok_(message.parts[2].content_type.is_message_container())
    eq_('Hello, how are you',
        message.parts[2].enclosed.headers['Subject'])


def ndn_2_test():
    message = scan(BOUNCE)
    ok_(message.is_delivery_notification())
    eq_(3, len(message.parts))
    eq_('text/plain', message.parts[0].content_type)
    ok_(message.parts[1].content_type.is_delivery_status())
    ok_(message.parts[2].content_type.is_message_container())


def mailbox_full_test():
    message = scan(MAILBOX_FULL)
    ok_(message.is_delivery_notification())
    eq_(3, len(message.parts))
    eq_('text/plain', message.parts[0].content_type)
    ok_(message.parts[1].content_type.is_delivery_status())
    ok_(message.parts[2].content_type.is_headers_container())


def test_uservoice_case():
    message = scan(LONG_LINKS)
    html = message.body
    message.body = html
    val = message.to_string()
    for line in val.splitlines():
        print line
        ok_(len(line) < 200)
    message = scan(val)
    eq_(html, message.body)


def test_mangle_case():
    m = scan("From: a@b.com\r\nTo:b@a.com\n\nFrom here")
    m.body = m.body + "\nFrom there"
    m = scan(m.to_string())
    eq_('From here\nFrom there', m.body)


def test_non_ascii_content_type():
    data = """From: me@domain.com
To: you@domain.com
Content-Type: text/点击链接绑定邮箱; charset="us-ascii"

Body."""
    message = scan(data)
    assert_raises(DecodingError, lambda x: message.headers, 1)


def test_non_ascii_from():
    message = scan(FROM_ENCODING)
    eq_(u'"Ingo Lütkebohle" <ingo@blank.pages.de>', message.headers.get('from'))


def notification_about_multipart_test():
    message = scan(NOTIFICATION)
    eq_(3, len(message.parts))
    eq_('multipart/alternative', message.parts[2].enclosed.content_type)


def dashed_boundaries_test():
    message = scan(DASHED_BOUNDARIES)
    eq_(2, len(message.parts))
    eq_('multipart/alternative', message.content_type)
    eq_('text/plain', message.parts[0].content_type)
    eq_('text/html', message.parts[1].content_type)


def bad_messages_test():
    assert_raises(DecodingError, scan, ENCLOSED_ENDLESS)
    assert_raises(DecodingError, scan, NDN_BROKEN)

def apache_mime_message_news_test():
    message = scan(APACHE_MIME_MESSAGE_NEWS)
    eq_('[Fwd: Netscape Enterprise vs. Apache Secure]',
        message.subject)


def missing_final_boundaries_enclosed_test():
    message = scan(ENCLOSED_BROKEN_BOUNDARY)
    eq_(('message/rfc822', {'name': u'thanks.eml'},),
        message.parts[1].headers['Content-Type'])


def missing_final_boundary_test():
    message = scan(MISSING_FINAL_BOUNDARY)
    ok_(message.parts[0].body)


def weird_bounce_test():
    message = scan(WEIRD_BOUNCE)
    eq_(0, len(message.parts))
    eq_('text/plain', message.content_type)

    message = scan(WEIRD_BOUNCE_2)
    eq_(0, len(message.parts))
    eq_('text/plain', message.content_type)

    message = scan(WEIRD_BOUNCE_3)
    eq_(0, len(message.parts))
    eq_('text/plain', message.content_type)


def bounce_headers_only_test():
    message = scan(NOTIFICATION)
    eq_(3, len(message.parts))
    eq_('multipart/alternative',
        str(message.parts[2].enclosed.content_type))

def message_external_body_test():
    message = scan(MESSAGE_EXTERNAL_BODY)
    eq_(2, len(message.parts))
    eq_(message.parts[1].parts[1].content_type.params['access-type'], 'anon-ftp')


def messy_content_types_test():
    message = scan(MISSING_BOUNDARIES)
    eq_(0, len(message.parts))


def disposition_notification_test():
    message = scan(DISPOSITION_NOTIFICATION)
    eq_(3, len(message.parts))


def yahoo_fbl_test():
    message = scan(YAHOO_FBL)
    eq_(3, len(message.parts))
    eq_('text/html', message.parts[2].enclosed.content_type)


def broken_content_type_test():
    message = scan(SPAM_BROKEN_CTYPE)
    eq_(2, len(message.parts))


def missing_newline_test():
    mime = "From: Foo <foo@example.com>\r\nTo: Bar <bar@example.com>\r\nMIME-Version: 1.0\r\nContent-type: text/html\r\nSubject: API Message\r\nhello, world\r\n.\r\n"
    message = scan(mime)
    eq_("hello, world\r\n.\r\n", message.body)

    # check that works with mixed-style-newlines
    mime = "From: Foo <foo@example.com>\r\nTo: Bar <bar@example.com>\r\nMIME-Version: 1.0\r\nContent-type: text/html\r\nSubject: API Message\nhello, world"
    message = scan(mime)
    eq_("hello, world", message.body)


def tree_to_string(part):
    parts = []
    print_tree(part, parts, "")
    return "\n".join(parts)


def print_tree(part, parts, delimiters=""):
    parts.append("{0}{1}".format(delimiters, part.content_type))

    if part.content_type.is_multipart():
        for p in part.parts:
            print_tree(p, parts, delimiters + "-")

    elif part.content_type.is_message_container():
        print_tree(part.enclosed, parts, delimiters + "-")




NO_CTYPE_HEADERS=[
    ('Mime-Version', '1.0'),
    ('Received', 'by 10.68.60.193 with HTTP; Thu, 29 Dec 2011 02:06:53 -0800 (PST)'),
    ('X-Originating-Ip', '[95.37.185.143]'),
    ('Date', 'Thu, 29 Dec 2011 14:06:53 +0400'),
    ('Delivered-To', 'bob@marley.com'),
    ('Message-Id', '<CAEAsyCbSF1Bk7CBuu6zp3Qs8=j2iUkNi3dPkGe6z40q4dmaogQ@mail.gmail.com>'),
    ('Subject', 'Testing message parsing'),
    ('From', 'Bob Marley <bob@marley.com>'),
    ('To', 'hello@there.com')]


TORTURE_PARTS = """multipart/mixed
-text/plain
-message/rfc822
--multipart/alternative
---text/plain
---multipart/mixed
----text/richtext
---application/andrew-inset
-message/rfc822
--audio/basic
-audio/basic
-image/pbm
-message/rfc822
--multipart/mixed
---multipart/mixed
----text/plain
----audio/x-sun
---multipart/mixed
----image/gif
----image/gif
----application/x-be2
----application/atomicmail
---audio/x-sun
-message/rfc822
--multipart/mixed
---text/plain
---image/pgm
---text/plain
-message/rfc822
--multipart/mixed
---text/plain
---image/pbm
-message/rfc822
--application/postscript
-image/gif
-message/rfc822
--multipart/mixed
---audio/basic
---audio/basic
-message/rfc822
--multipart/mixed
---application/postscript
---application/octet-stream
---message/rfc822
----multipart/mixed
-----text/plain
-----multipart/parallel
------image/gif
------audio/basic
-----application/atomicmail
-----message/rfc822
------audio/x-sun
"""

########NEW FILE########
__FILENAME__ = threading_test
# coding:utf-8
"""
Fun begins here!
"""

from ... import *
from nose.tools import *
from mock import *

from flanker.mime import create
from flanker.mime.message.threading import *
from flanker.mime.message.headers import MessageId

@patch.object(MessageId, 'is_valid', Mock(return_value=True))
def test_wrapper_creates_message_id():
    message = create.text('plain','hey')
    w = Wrapper(message)
    ok_(w.message_id)
    eq_([], w.references)

@patch.object(MessageId, 'is_valid', Mock(return_value=True))
def test_wrapper_references():
    message = create.text('plain','hey')
    message.headers['References'] = '<1> <2> <3>'
    message.headers['Message-Id'] = '<4>'
    w = Wrapper(message)
    eq_('4', w.message_id)
    eq_(['1', '2', '3'], w.references)

@patch.object(MessageId, 'is_valid', Mock(return_value=True))
def test_wrapper_in_reply_to():
    message = create.text('plain','hey')
    message.headers['In-Reply-To'] = '<3>'
    message.headers['Message-Id'] = '<4>'
    w = Wrapper(message)
    eq_('4', w.message_id)
    eq_(['3'], w.references)

@patch.object(MessageId, 'is_valid', Mock(return_value=True))
def test_container_to_string():
    eq_('dummy', str(Container()))
    eq_('123@gmail.com', str(tc('123@gmail.com')))

@patch.object(MessageId, 'is_valid', Mock(return_value=True))
def test_container_is_dummy():
    ok_(Container().is_dummy)
    assert_false(tc('1').is_dummy)

@patch.object(MessageId, 'is_valid', Mock(return_value=True))
def test_container_in_root_set():
    c = Container()
    c.parent = Container()
    ok_(c.in_root_set)

    c.parent.parent = Container()
    assert_false(c.in_root_set)

@patch.object(MessageId, 'is_valid', Mock(return_value=True))
def test_container_children():
    c = Container()
    assert_false(c.has_children)
    assert_false(c.has_one_child)

    c.child = Container()
    ok_(c.has_children)
    ok_(c.has_one_child)

    c.child.next = Container()
    ok_(c.has_children)
    assert_false(c.has_one_child)

@patch.object(MessageId, 'is_valid', Mock(return_value=True))
def test_container_find_and_iter_children():
    c = Container()
    eq_(None, c.last_child)
    collected = []
    for child in c.iter_children():
        collected.append(child)

    eq_([], collected)
    assert_false(c.has_descendant(None))
    assert_false(c.has_descendant(c))

    c1,c2 = Container(), Container()
    c.child = c1
    eq_(c1, c.last_child)
    ok_(c.has_descendant(c1))
    assert_false(c.has_descendant(c2))

    c.child.next = c2
    eq_(c2, c.last_child)
    ok_(c.has_descendant(c2))

    collected = []
    for child in c.iter_children():
        collected.append(child)
    eq_([c1,c2], collected)

    c3, c4, c5, c6 = make_empty(4)
    c2.child = c3
    c2.child.child = c4
    c2.child.child.next = c5
    c2.child.child.next.next = c6
    ok_(c.has_descendant(c3))
    ok_(c.has_descendant(c4))
    ok_(c.has_descendant(c5))
    ok_(c.has_descendant(c6))

@patch.object(MessageId, 'is_valid', Mock(return_value=True))
def test_container_add_child():
    c, c1, c2 = make_empty(3)

    c.add_child(c1)
    eq_(c, c1.parent)
    eq_(c1, c.child)
    eq_(None, c1.prev)

    c.add_child(c2)
    eq_(c2, c.child)
    eq_(c1, c2.next)
    eq_(c2, c1.prev)
    eq_(c, c2.parent)
    eq_(None, c2.prev)

@patch.object(MessageId, 'is_valid', Mock(return_value=True))
def test_container_remove_child():
    c, c1, c2 = make_empty(3)

    c.add_child(c1)
    c.remove_child(c1)
    eq_(None, c.child)
    eq_(None, c1.parent)
    eq_(None, c1.prev)
    eq_(None, c1.next)


    c, c1, c2 = make_empty(3)

    c.add_child(c1)
    c.add_child(c2)
    c.remove_child(c1)
    eq_(c2, c.child)
    eq_(None, c2.next)
    eq_(None, c1.prev)


    c, c1, c2 = make_empty(3)

    c.add_child(c1)
    c.add_child(c2)
    c.remove_child(c2)
    eq_(c1, c.child)
    eq_(None, c1.prev)
    eq_(None, c1.next)

    c, c1, c2, c3 = make_empty(4)

    c.add_child(c1)
    c.add_child(c2)
    c.add_child(c3)

    c.remove_child(c2)
    eq_(c3, c.child)
    eq_(c1, c3.next)
    eq_(c3, c1.prev)

@patch.object(MessageId, 'is_valid', Mock(return_value=True))
def test_container_replace_with_its_children():
    # before:
    #
    # a
    # +- b
    #    +- c - d
    #
    # read it like that: a - root, b is a's first child, c is b's first child
    #                    d is c's sibling
    #
    # after:
    #
    # a
    # +- c - d
    #
    a,b,c,d= make_empty(4)

    a.add_child(b)
    b.add_child(d)
    b.add_child(c)

    a.replace_with_its_children(b)
    eq_(c, a.child)
    eq_(d, a.child.next)

    eq_(a, c.parent)
    eq_(a, d.parent)

    eq_(None, a.child.prev)
    eq_(c, d.prev)

    # before:
    #
    # a
    # +- b - e
    #    +- c - d
    #
    # after:
    #
    # a
    # +- c - d - e
    #
    a,b,c,d,e = make_empty(5)

    a.add_child(e)
    a.add_child(b)
    b.add_child(d)
    b.add_child(c)

    a.replace_with_its_children(b)
    eq_(c, a.child)
    eq_(d, a.child.next)
    eq_(d, e.prev)
    eq_(e, d.next)
    #
    # before:
    #
    # a
    # +- b - f - e
    #        +-  c - d
    #
    #
    # after:
    #
    # a
    # +- b - c - d - e
    #
    #
    a,b,c,d,e,f = make_empty(6)

    a.add_child(e)
    a.add_child(f)
    a.add_child(b)

    f.add_child(d)
    f.add_child(c)

    a.replace_with_its_children(f)
    eq_(b, a.child)
    eq_(c, b.next)
    eq_(b, c.prev)
    eq_(d, e.prev)
    eq_(e, d.next)
    eq_(a, c.parent)
    eq_(a, d.parent)

@patch.object(MessageId, 'is_valid', Mock(return_value=True))
def test_prune_empty():
    #
    # before:
    #
    # r
    # +- b
    #    +- c1 (empty)
    #
    # after:
    #
    # r
    # +- b
    #
    b, = make_full('b')
    r, c1 = make_empty(2)
    r.add_child(b)
    b.add_child(c1)

    r.prune_empty()
    eq_(b, r.child)
    eq_(None, b.child)

    #
    # before:
    #
    # r
    # +- b
    #    +- c1 (empty)
    #       +- d
    # after:
    #
    # r
    # +- b
    #    +- d
    #
    b, d = make_full('b', 'd')
    r, c1 = make_empty(2)
    r.add_child(b)
    b.add_child(c1)
    c1.add_child(d)

    r.prune_empty()
    eq_(b, r.child)
    eq_(d, b.child)
    eq_(None, c1.parent)
    eq_(None, c1.child)

    #
    # promote child of containers with empty message and 1 child
    # directly to root level
    #
    # before:
    #
    # r
    # +- c1 (empty)
    #    +- a
    #
    # after:
    #
    # r
    # +- a
    #
    a, = make_full('a')
    r, c1 = make_empty(2)
    r.add_child(c1)
    c1.add_child(a)

    r.prune_empty()
    eq_(a, r.child)
    eq_(None, a.child)
    eq_(r, a.parent)

    #
    # do not promote child of containers with empty message and > 1 child
    # directly to root level
    #
    # before:
    #
    # r
    # +- c1 (empty)
    #    +- a - b
    #
    # after:
    #
    # r
    # +- c1 (empty)
    #    +- a - b
    #
    a,b = make_full('a', 'b')
    r, c1 = make_empty(2)
    r.add_child(c1)
    c1.add_child(b)
    c1.add_child(a)

    r.prune_empty()
    eq_(c1, r.child)
    eq_(a, c1.child)
    eq_(b, a.next)

    #
    # remove useless container
    #
    # before:
    #
    # r
    # +- c1 (empty)
    #    +- c2 (empty)
    #       +- a - b
    #
    # after:
    #
    # r
    # +- c2 (empty)
    #    +- a - b
    #
    a, b = make_full('a', 'b')
    r, c1, c2 = make_empty(3)
    r.add_child(c1)
    c1.add_child(c2)
    c2.add_child(b)
    c2.add_child(a)

    r.prune_empty()
    eq_(c2, r.child)
    eq_(a, c2.child)
    eq_(b, a.next)

    #
    # remove 2 useless containers
    #
    # before:
    #
    # r
    # +- c1 (empty)
    #    +- c2 (empty)
    #       +- c3
    #          +- a - b
    #
    # after:
    #
    # r
    # +- c3 (empty)
    #    +- a - b
    #
    a, b = make_full('a', 'b')
    r, c1, c2, c3 = make_empty(4)
    r.add_child(c1)
    c1.add_child(c2)
    c2.add_child(c3)
    c3.add_child(b)
    c3.add_child(a)

    r.prune_empty()
    eq_(c3, r.child)
    eq_(a, c3.child)
    eq_(b, a.next)


    #
    # remove 2 useless containers
    #
    # before:
    #
    # r
    # +- c1 (empty) ---- c2 (empty)
    #    +- a
    #
    # after:
    #
    # r
    # +- a
    #
    #
    a, b = make_full('a', 'b')
    r, c1, c2 = make_empty(3)
    r.add_child(c2)
    r.add_child(c1)
    c1.add_child(a)

    r.prune_empty()
    eq_(a, r.child)

    #
    # remove tons of useless containers
    #
    # before:
    #
    # r
    # +- c1 (empty) -------------- c4
    #    +- c2 (empty)
    #       +- c3 (empty)
    #          +- a ------ c
    #             +- b     +- d
    #
    # after:
    #
    # r
    # +- c3 (empty)
    #    +- a --- c
    #       +- b  +- d
    #
    a, b, c, d  = make_full('a', 'b', 'c', 'd')
    r, c1, c2, c3, c4 = make_empty(5)
    r.add_child(c4)
    r.add_child(c1)
    c1.add_child(c2)
    c2.add_child(c3)
    c3.add_child(c)
    c.add_child(d)
    c3.add_child(a)
    a.add_child(b)

    r.prune_empty()
    eq_(c3, r.child)
    eq_(None, c3.next)
    eq_(a, c3.child)
    eq_(c, a.next)

    #
    # remove megatons of useless containers
    # cN - empty containers
    #
    # before:
    #
    # r
    # +- c1
    #    +- c2---------- c6 ------- e
    #       +- c3        +- c7----- f
    #          +- c4        +- c8
    #              +- a ------ c
    #                 +- b     +- d
    #
    # after:
    #
    # r
    # +- c1
    #    +- a ---- c
    #       +- b   +- d
    a, b, c, d, e, f  = make_full('a', 'b', 'c', 'd', 'e', 'f')
    r, c1, c2, c3, c4, c5, c6, c7, c8 = make_empty(9)
    r.add_child(c1)
    c1.add_child(e)
    c1.add_child(c6)
    c6.add_child(f)
    c6.add_child(c7)
    c7.add_child(c8)
    c1.add_child(c2)
    c2.add_child(c3)
    c3.add_child(c4)
    c4.add_child(c)
    c.add_child(d)
    c4.add_child(a)
    a.add_child(b)

    r.prune_empty()
    eq_(c1, r.child)
    eq_(None, c1.next)
    eq_(a, c1.child)
    eq_(c, a.next)
    eq_(b, a.child)
    eq_(d, c.child)
    eq_(f, c.next)
    eq_(e, f.next)

@patch.object(MessageId, 'is_valid', Mock(return_value=True))
def test_introduces_loop():
    a, = make_empty(1)
    ok_(introduces_loop(a, a))

    a, b = make_empty(2)
    assert_false(introduces_loop(a, b))

    a, b = make_empty(2)
    b.add_child(a)
    ok_(introduces_loop(a, b))

    a, b, c = make_empty(3)
    b.add_child(c)
    c.add_child(a)
    ok_(introduces_loop(a, b))

@patch.object(MessageId, 'is_valid', Mock(return_value=True))
def test_build_table():
    #
    # Should create valid table for messages arriving
    # in the following order
    #
    # a
    # +- b
    #    + - c
    #        +- d
    #
    # b
    # +- c
    #    +- d
    #
    # c
    # +- d
    #
    # d
    messages = [
        make_message("a"),
        make_message("b", ["a"]),
        make_message("c", ["a", "b"]),
        make_message("d", ["a", "b", "c"])
        ]
    table = build_table(messages)
    eq_(4, len(table))
    eq_('b', table["a"].child.message.message_id)
    eq_('c', table["b"].child.message.message_id)
    eq_('d', table["c"].child.message.message_id)
    eq_(None, table["d"].child)

    #
    # Should create valid chain with dummy containers
    # when c is missing
    #
    # a
    # +- b
    #    + - c (dummy)
    #        +- d
    #
    # b
    # +- c (dummy)
    #    +- d
    #
    # c (dummy)
    # +- d
    #
    # d
    messages = [
        make_message("a"),
        make_message("b", ["a"]),
        make_message("d", ["a", "b", "c"])
        ]
    table = build_table(messages)
    eq_(4, len(table))
    eq_('b', table["a"].child.message.message_id)
    eq_(None, table["b"].child.message)
    eq_('d', table["c"].child.message.message_id)
    eq_(None, table["d"].child)

    # processes situations when messages disagree
    # about threading structure
    #
    # a
    # +- b
    #    +- c
    #       +- d
    #
    # a
    # +- c
    #    +- e
    #

    messages = [
        make_message("e", ["a", "c"]),
        make_message("d", ["a", "b", "c"])
        ]
    table = build_table(messages)
    eq_(5, len(table))
    a = table["a"]
    eq_('d', a.child.next.child.message.message_id)
    eq_('e', a.child.next.child.next.message.message_id)

    # processes situations when messages
    # attempt to introduce some loop
    #
    # a
    # +- b
    #    +- c
    #
    # c
    # +- a
    #

    messages = [
        make_message("c", ["a", "b"]),
        make_message("a", ["c"])
        ]
    table = build_table(messages)
    eq_(3, len(table))
    a = table["a"]
    eq_('c', a.child.child.message.message_id)
    c = table["c"]
    eq_(None, c.child)

    # processes situations when we
    # have multiple messages with the same id
    #
    # b
    # +- a
    #
    # c
    # +- a

    messages = [
        make_message("a", ["b"]),
        make_message("a", ["c"])
        ]
    table = build_table(messages)
    eq_(4, len(table))
    eq_('a', table['a'].message.message_id)
    # we have detected conflict and
    # intentionally created fake message it (to avoid loosing message)
    # here it is:
    fake_id = [key for key in table if key not in ('a', 'b', 'c')][0]
    eq_('a', table[fake_id].message.message_id)

@patch.object(MessageId, 'is_valid', Mock(return_value=True))
def test_build_root_set():
    #
    # Should create valid root set
    # in the following order
    #
    # a
    # +- b
    #    + - c
    #        +- d
    #
    # b
    # +- c
    #    +- d
    #
    # c
    # +- d
    #
    # d
    #
    # e (missing)
    # +- f
    #
    # g
    messages = [
        make_message("a"),
        make_message("b", ["a"]),
        make_message("c", ["a", "b"]),
        make_message("d", ["a", "b", "c"]),
        make_message("f", ["e"]),
        make_message("g")
        ]
    table = build_table(messages)
    root = build_root_set(table)
    eq_('g', root.child.message.message_id)
    eq_('f', root.child.next.child.message.message_id)
    eq_('a', root.child.next.next.message.message_id)
    eq_(None, root.child.next.next.next)

    # Thread should became
    #
    # thread
    #   |
    #   +- g
    #   +- f
    #   +- a
    #      +- b
    #         +- c
    #            +- d

    thread = build_thread(messages)
    eq_('g', thread.child.message.message_id)
    eq_('f', thread.child.next.message.message_id)
    eq_('a', thread.child.next.next.message.message_id)
    eq_('b', thread.child.next.next.child.message.message_id)
    eq_('c', thread.child.next.next.child.child.message.message_id)
    eq_('d', thread.child.next.next.child.child.child.message.message_id)


def make_empty(count):
    return [Container() for i in range(count)]

def make_full(*ids):
    return [tc(id) for id in ids]

def tc(*args, **kwargs):
    return Container(wrapper(*args, **kwargs))

def make_message(message_id, references=None, subject=""):
    message = create.text('plain','hey')
    if message_id:
        message.headers['Message-Id'] = '<{0}>'.format(message_id)
    if references:
        message.headers['References'] = ' '.join(
            '<{0}>'.format(rid) for rid in references)
    return message

def wrapper(message_id, references=None, subject=""):
    return Wrapper(make_message(message_id, references, ""))

########NEW FILE########
__FILENAME__ = tokenizer_test
# coding:utf-8
import zlib
from nose.tools import *
from mock import *
from flanker.mime.message.scanner import tokenize, ContentType, Boundary

from ... import *

C = ContentType
B = Boundary


def no_ctype_and_and_boundaries_test():
    """We are ok, when there is no content type and boundaries"""
    eq_([], tokenize(NO_CTYPE))


def binary_test():
    """Can scan binary stuff: works for 8bit mime"""
    tokens = tokenize(EIGHT_BIT)
    dummy = 0
    expect = [
        C('multipart', 'alternative', dict(boundary="=-omjqkVTVbwdgCWFRgIkx")),
        B("=-omjqkVTVbwdgCWFRgIkx", dummy, dummy, False),
        C('text', 'plain', dict(charset="UTF-8")),
        B("=-omjqkVTVbwdgCWFRgIkx", dummy, dummy, False),
        C('text', 'html', dict(charset="utf-8")),
        B("=-omjqkVTVbwdgCWFRgIkx", dummy, dummy, True)
        ]

    for a,b in zip(expect, tokens):
        eq_(a, b, "{0} != {1}".format(a, b))


def torture_test():
    """Torture is a complex multipart nested message"""

    tokens = tokenize(TORTURE)

    boundaries = set([b.value for b in tokens if b.is_boundary()])
    eq_(TORTURE_BOUNDARIES, boundaries)

    ctypes = [("{0}/{1}".format(b.main, b.sub), b.get_boundary())\
                  for b in tokens if b.is_content_type()]
    for a, b in zip(TORTURE_CTYPES, ctypes):
        eq_(a, b)


def dashed_boundary_test():
    """Make sure we don't screw up when boundary contains -- symbols,
    It's also awesome how fast we scan the 11MB message.
    """

    tokens = tokenize(BIG)
    dummy = 0
    expect = [
        C('multipart', 'mixed', dict(boundary="------------060808020401090407070006")),
        B("------------060808020401090407070006", dummy, dummy, False),
        C('text', 'html', dict(charset="ISO-8859-1")),
        B("------------060808020401090407070006", dummy, dummy, False),
        C('image', 'tiff', dict(name="teplosaurus-hi-res-02.tif")),
        B("------------060808020401090407070006", dummy, dummy, True)
        ]

    for a,b in zip(expect, tokens):
        eq_(a, b, "{0} != {1}".format(a, b))


def dashed_ending_boundary_test():
    """Make sure we don't screw up when boundary contains -- symbols at the
    ending as well"""

    tokens = tokenize(DASHED_BOUNDARIES)
    dummy = 0
    expect = [
        C('multipart', 'alternative', dict(boundary="--120710081418BV.24190.Texte--")),
        B("--120710081418BV.24190.Texte--", dummy, dummy, False),
        C('text', 'plain', dict(charset="UTF-8")),
        B("--120710081418BV.24190.Texte--", dummy, dummy, False),
        C('text', 'html', dict(charset="UTF-8")),
        B("--120710081418BV.24190.Texte--", dummy, dummy, True)
        ]

    for a,b in zip(expect, tokens):
        eq_(a, b, "{0} != {1}".format(a, b))


def complete_garbage_test():
    """ We survive complete garbage test """
    eq_([], tokenize(zlib.compress(NO_CTYPE)))



TORTURE_BOUNDARIES = set([
            'owatagusiam',
            'hal_9000',
            'Interpart_Boundary_AdJn:mu0M2YtJKaFh9AdJn:mu0M2YtJKaFk=',
            'Where_No_Man_Has_Gone_Before',
            'mail.sleepy.sau.158.532',
            'Alternative_Boundary_8dJn:mu0M2Yt5KaFZ8AdJn:mu0M2Yt1KaFdA',
            '16819560-2078917053-688350843:#11603',
            'Where_No_One_Has_Gone_Before',
            'foobarbazola',
            'seconddivider',
            'mail.sleepy.sau.144.8891',
            'Outermost_Trek'
            ])

TORTURE_CTYPES = [
    ('multipart/mixed', 'owatagusiam'),
     ('text/plain', None),
     ('message/rfc822', None),
     ('multipart/alternative', 'Interpart_Boundary_AdJn:mu0M2YtJKaFh9AdJn:mu0M2YtJKaFk='),
     ('multipart/mixed', 'Alternative_Boundary_8dJn:mu0M2Yt5KaFZ8AdJn:mu0M2Yt1KaFdA'),
     ('text/richtext', None),
     ('application/andrew-inset', None),
     ('message/rfc822', None),
     ('audio/basic', None),
     ('audio/basic', None),
     ('image/pbm', None),
     ('message/rfc822', None),
     ('multipart/mixed', 'Outermost_Trek'),
     ('multipart/mixed', 'Where_No_One_Has_Gone_Before'),
     ('audio/x-sun', None),
     ('multipart/mixed', 'Where_No_Man_Has_Gone_Before'),
     ('image/gif', None),
     ('image/gif', None),
     ('application/x-be2', None),
     ('application/atomicmail', None),
     ('audio/x-sun', None),
     ('message/rfc822', None),
     ('multipart/mixed', "mail.sleepy.sau.144.8891"),
     ('image/pgm', None),
     ('message/rfc822', None),
     ('multipart/mixed', "mail.sleepy.sau.158.532"),
     ('image/pbm', None),
     ('message/rfc822', None),
     ('application/postscript', None),
     ('image/gif', None),
     ('message/rfc822', None),
     ('multipart/mixed', 'hal_9000'),
     ('audio/basic', None),
     ('audio/basic', None),
     ('message/rfc822', None),
     ('multipart/mixed', '16819560-2078917053-688350843:#11603'),
     ('application/postscript', None),
     ('application/octet-stream', None),
     ('message/rfc822', None),
     ('multipart/mixed', 'foobarbazola'),
     ('multipart/parallel', 'seconddivider'),
     ('image/gif', None),
     ('audio/basic', None),
     ('application/atomicmail', None),
     ('message/rfc822', None),
     ('audio/x-sun', None)]

########NEW FILE########
