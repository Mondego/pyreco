__FILENAME__ = furl
#
# furl - URL manipulation made simple.
#
# Arthur Grunseid
# grunseid.com
# grunseid@gmail.com
#
# License: Build Amazing Things (Unlicense)

import re
import abc
import urllib
import urlparse
import warnings
from itertools import izip
from posixpath import normpath

from omdict1D import omdict1D

_absent = object()

#
# TODO(grun): Subclass Path, PathCompositionInterface, Query, and
# QueryCompositionInterface into two subclasses each - one for the URL
# and one for the Fragment.
#
# Subclasses will clean up the code because the valid encodings are
# different between a URL Path and a Fragment Path and a URL Query and a
# Fragment Query.
#
# For example, '?' and '#' don't need to be encoded in Fragment Path
# segments but must be encoded in URL Path segments.
#
# Similarly, '#' doesn't need to be encoded in Fragment Query keys and
# values, but must be encoded in URL Query keys and values.
#

# Map of various URL schemes to their default ports. Scheme strings are
# lowercase.
DEFAULT_PORTS = {
    'ftp': 21,
    'ssh': 22,
    'http': 80,
    'https': 443,
    }

# List of schemes that don't require two slashes after the colon. For example,
# 'mailto:user@google.com' instead of 'mailto://user@google.com'. Scheme
# strings are lowercase.
#
# TODO(grun): Support schemes separated by just ':', not '://' without having
# an explicit list. There are many such schemes in various URIs.
COLON_SEPARATED_SCHEMES = [
    'mailto',
    ]


class Path(object):

    """
    Represents a path comprised of zero or more path segments.

      http://tools.ietf.org/html/rfc3986#section-3.3

    Path parameters aren't supported.

    Attributes:
      _force_absolute: Function whos boolean return value specifies
        whether self.isabsolute should be forced to True or not. If
        _force_absolute(self) returns True, isabsolute is read only and
        raises an AttributeError if assigned to. If
        _force_absolute(self) returns False, isabsolute is mutable and
        can be set to True or False. URL paths use _force_absolute and
        return True if the netloc is non-empty (not equal to
        ''). Fragment paths are never read-only and their
        _force_absolute(self) always returns False.
      segments: List of zero or more path segments comprising this
        path. If the path string has a trailing '/', the last segment
        will be '' and self.isdir will be True and self.isfile will be
        False. An empty segment list represents an empty path, not '/'
        (though they have the same meaning).
      isabsolute: Boolean whether or not this is an absolute path or
        not. An absolute path starts with a '/'. self.isabsolute is
        False if the path is empty (self.segments == [] and str(path) ==
        '').
      strict: Boolean whether or not UserWarnings should be raised if
        improperly encoded path strings are provided to methods that
        take such strings, like load(), add(), set(), remove(), etc.
    """

    SAFE_SEGMENT_CHARS = ":@-._~!$&'()*+,;="

    def __init__(self, path='', force_absolute=lambda _: False, strict=False):
        self.segments = []

        self.strict = strict
        self._isabsolute = False
        self._force_absolute = force_absolute

        self.load(path)

    def load(self, path):
        """
        Load <path>, replacing any existing path. <path> can either be a
        list of segments or a path string to adopt.

        Returns: <self>.
        """
        if not path:
            segments = []
        elif callable_attr(path, 'split'):  # String interface.
            segments = self._segments_from_path(path)
        else:  # List interface.
            segments = path

        if self._force_absolute(self):
            self._isabsolute = True if segments else False
        else:
            self._isabsolute = (segments and segments[0] == '')

        if self.isabsolute and len(segments) > 1 and segments[0] == '':
            segments.pop(0)
        self.segments = [urllib.unquote(segment) for segment in segments]

        return self

    def add(self, path):
        """
        Add <path> to the existing path. <path> can either be a list of
        segments or a path string to append to the existing path.

        Returns: <self>.
        """
        newsegments = path  # List interface.
        if callable_attr(path, 'split'):  # String interface.
            newsegments = self._segments_from_path(path)

        # Preserve the opening '/' if one exists already (self.segments
        # == ['']).
        if self.segments == [''] and newsegments and newsegments[0] != '':
            newsegments.insert(0, '')

        segments = self.segments
        if self.isabsolute and self.segments and self.segments[0] != '':
            segments.insert(0, '')

        self.load(join_path_segments(segments, newsegments))
        return self

    def set(self, path):
        self.load(path)
        return self

    def remove(self, path):
        if path is True:
            self.load('')
        else:
            segments = path  # List interface.
            if isinstance(path, basestring):  # String interface.
                segments = self._segments_from_path(path)
            base = ([''] if self.isabsolute else []) + self.segments
            self.load(remove_path_segments(base, segments))
        return self

    def normalize(self):
        """
        Normalize the path. Turn '//a/./b/../c//' into '/a/c/'.

        Returns: <self>.
        """
        if str(self):
            normalized = normpath(str(self)) + ('/' * self.isdir)
            if normalized.startswith('//'):  # http://bugs.python.org/636648
                normalized = '/' + normalized.lstrip('/')
            self.load(normalized)
        return self

    @property
    def isabsolute(self):
        if self._force_absolute(self):
            return True
        return self._isabsolute

    @isabsolute.setter
    def isabsolute(self, isabsolute):
        """
        Raises: AttributeError if _force_absolute(self) returns True.
        """
        if self._force_absolute(self):
            s = ('Path.isabsolute is True and read-only for URLs with a netloc'
                 ' (a username, password, host, and/or port). A URL path must '
                 "start with a '/' to separate itself from a netloc.")
            raise AttributeError(s)
        self._isabsolute = isabsolute

    @property
    def isdir(self):
        """
        Returns: True if the path ends on a directory, False
        otherwise. If True, the last segment is '', representing the
        trailing '/' of the path.
        """
        return (self.segments == [] or
                (self.segments and self.segments[-1] == ''))

    @property
    def isfile(self):
        """
        Returns: True if the path ends on a file, False otherwise. If
        True, the last segment is not '', representing some file as the
        last segment of the path.
        """
        return not self.isdir

    def __nonzero__(self):
        return len(self.segments) > 0

    def __str__(self):
        segments = list(self.segments)
        if self.isabsolute:
            if not segments:
                segments = ['', '']
            else:
                segments.insert(0, '')
        return self._path_from_segments(segments)

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, str(self))

    def _segments_from_path(self, path):
        """
        Returns: The list of path segments from the path string <path>.

        Raises: UserWarning if <path> is an improperly encoded path
        string and self.strict is True.
        """
        segments = []
        for segment in u2utf8(path).split('/'):
            if not is_valid_encoded_path_segment(segment):
                segment = urllib.quote(segment)
                if self.strict:
                    s = ("Improperly encoded path string received: '%s'. "
                         "Proceeding, but did you mean '%s'?" %
                         (path, self._path_from_segments(segments)))
                    warnings.warn(s, UserWarning)
            segments.append(segment)
        return map(urllib.unquote, segments)

    def _path_from_segments(self, segments):
        """
        Combine the provided path segments <segments> into a path string. Path
        segments in <segments> will be quoted.

        Returns: A path string with quoted path segments.
        """
        if '%' not in ''.join(segments):  # Don't double-encode the path.
            segments = [urllib.quote(u2utf8(segment), self.SAFE_SEGMENT_CHARS)
                        for segment in segments]
        return '/'.join(segments)


class PathCompositionInterface(object):

    """
    Abstract class interface for a parent class that contains a Path.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, strict=False):
        """
        Params:
          force_absolute: See Path._force_absolute.

        Assignments to <self> in __init__() must be added to
        __setattr__() below.
        """
        self._path = Path(force_absolute=self._force_absolute, strict=strict)

    @property
    def path(self):
        return self._path

    @property
    def pathstr(self):
        """This method is deprecated. Use str(furl.path) instead."""
        s = ('furl.pathstr is deprecated. Use str(furl.path) instead. There '
             'should be one, and preferably only one, obvious way to serialize'
             ' a Path object to a string.')
        warnings.warn(s, DeprecationWarning)
        return str(self._path)

    @abc.abstractmethod
    def _force_absolute(self, path):
        """
        Subclass me.
        """
        pass

    def __setattr__(self, attr, value):
        """
        Returns: True if this attribute is handled and set here, False
        otherwise.
        """
        if attr == '_path':
            self.__dict__[attr] = value
            return True
        elif attr == 'path':
            self._path.load(value)
            return True
        return False


class URLPathCompositionInterface(PathCompositionInterface):

    """
    Abstract class interface for a parent class that contains a URL
    Path.

    A URL path's isabsolute attribute is absolute and read-only if a
    netloc is defined. A path cannot start without '/' if there's a
    netloc. For example, the URL 'http://google.coma/path' makes no
    sense. It should be 'http://google.com/a/path'.

    A URL path's isabsolute attribute is mutable if there's no
    netloc. The scheme doesn't matter. For example, the isabsolute
    attribute of the URL path in 'mailto:user@domain.com', with scheme
    'mailto' and path 'user@domain.com', is mutable because there is no
    netloc. See

      http://en.wikipedia.org/wiki/URI_scheme#Examples
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, strict=False):
        PathCompositionInterface.__init__(self, strict=strict)

    def _force_absolute(self, path):
        return bool(path) and self.netloc


class FragmentPathCompositionInterface(PathCompositionInterface):

    """
    Abstract class interface for a parent class that contains a Fragment
    Path.

    Fragment Paths they be set to absolute (self.isabsolute = True) or
    not absolute (self.isabsolute = False).
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, strict=False):
        PathCompositionInterface.__init__(self, strict=strict)

    def _force_absolute(self, path):
        return False


class Query(object):

    """
    Represents a URL query comprised of zero or more unique parameters
    and their respective values.

      http://tools.ietf.org/html/rfc3986#section-3.4


    All interaction with Query.params is done with unquoted strings. So

      f.query.params['a'] = 'a%5E'

    means the intended value for 'a' is 'a%5E', not 'a^'.


    Query.params is implemented as an omdict1D object - a one
    dimensional ordered multivalue dictionary. This provides support for
    repeated URL parameters, like 'a=1&a=2'. omdict1D is a subclass of
    omdict, an ordered multivalue dictionary. Documentation for omdict
    can be found here

      https://github.com/gruns/orderedmultidict

    The one dimensional aspect of omdict1D means that a list of values
    is interpreted as multiple values, not a single value which is
    itself a list of values. This is a reasonable distinction to make
    because URL query parameters are one dimensional - query parameter
    values cannot themselves be composed of sub-values.

    So what does this mean? This means we can safely interpret

      f = furl('http://www.google.com')
      f.query.params['arg'] = ['one', 'two', 'three']

    as three different values for 'arg': 'one', 'two', and 'three',
    instead of a single value which is itself some serialization of the
    python list ['one', 'two', 'three']. Thus, the result of the above
    will be

      f.query.allitems() == [
        ('arg','one'), ('arg','two'), ('arg','three')]

    and not

      f.query.allitems() == [('arg', ['one', 'two', 'three'])]

    The latter doesn't make sense because query parameter values cannot
    be composed of sub-values. So finally

      str(f.query) == 'arg=one&arg=two&arg=three'

    Attributes:
      params: Ordered multivalue dictionary of query parameter key:value
        pairs. Parameters in self.params are maintained URL decoded - 'a
        b' not 'a+b'.
      strict: Boolean whether or not UserWarnings should be raised if
        improperly encoded query strings are provided to methods that
        take such strings, like load(), add(), set(), remove(), etc.
    """

    SAFE_KEY_CHARS = "/?:@-._~!$'()*,"
    SAFE_VALUE_CHARS = "/?:@-._~!$'()*,="

    def __init__(self, query='', strict=False):
        self.strict = strict

        self._params = omdict1D()

        self.load(query)

    def load(self, query):
        self.params.load(self._items(query))
        return self

    def add(self, args):
        for param, value in self._items(args):
            self.params.add(param, value)
        return self

    def set(self, mapping):
        """
        Adopt all mappings in <mapping>, replacing any existing mappings
        with the same key. If a key has multiple values in <mapping>,
        they are all adopted.

        Examples:
          Query({1:1}).set([(1,None),(2,2)]).params.allitems()
            == [(1,None),(2,2)]
          Query({1:None,2:None}).set([(1,1),(2,2),(1,11)]).params.allitems()
            == [(1,1),(2,2),(1,11)]
          Query({1:None}).set([(1,[1,11,111])]).params.allitems()
            == [(1,1),(1,11),(1,111)]

        Returns: <self>.
        """
        self.params.updateall(mapping)
        return self

    def remove(self, query):
        if query is True:
            self.load('')
            return self

        # Single key to remove.
        items = [query]
        # Dictionary or multivalue dictionary of items to remove.
        if callable_attr(query, 'iteritems'):
            items = self._items(query)
        # List of keys or items to remove.
        elif callable_attr(query, '__iter__'):
            items = query

        for item in items:
            if callable_attr(item, '__iter__') and len(item) == 2:
                key, value = item
                self.params.popvalue(key, value, None)
            else:
                key = item
                self.params.pop(key, None)
        return self

    @property
    def params(self):
        return self._params

    @params.setter
    def params(self, params):
        items = self._items(params)

        self._params.clear()
        for key, value in items:
            self._params.add(key, value)

    def encode(self, delimeter='&'):
        """
        Examples:
          Query('a=a&b=#').encode() == 'a=a&b=%23'
          Query('a=a&b=#').encode(';') == 'a=a;b=%23'

        Returns: A URL encoded query string using <delimeter> as the
        delimeter separating key:value pairs. The most common and
        default delimeter is '&', but ';' can also be specified. ';' is
        W3C recommended.
        """
        pairs = []
        for key, value in self.params.iterallitems():
            key, value = u2utf8(key), u2utf8(value)
            quoted_key = urllib.quote_plus(str(key), self.SAFE_KEY_CHARS)
            quoted_value = urllib.quote_plus(str(value), self.SAFE_VALUE_CHARS)
            pair = '='.join([quoted_key, quoted_value])
            if value is None:  # Example: http://sprop.su/?param
                pair = quoted_key
            pairs.append(pair)
        return delimeter.join(pairs)

    def __nonzero__(self):
        return len(self.params) > 0

    def __str__(self):
        return self.encode()

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, str(self))

    def _items(self, items):
        """
        Extract and return the key:value items from various
        containers. Some containers that could hold key:value items are

          - List of (key,value) tuples.
          - Dictionaries of key:value items.
          - Multivalue dictionary of key:value items, with potentially
            repeated keys.
          - Query string with encoded params and values.

        Keys and values are passed through unmodified unless they were
        passed in within an encoded query string, like
        'a=a%20a&b=b'. Keys and values passed in within an encoded query
        string are unquoted by urlparse.parse_qsl(), which uses
        urllib.unquote_plus() internally.

        Returns: List of items as (key, value) tuples. Keys and values
        are passed through unmodified unless they were passed in as part
        of an encoded query string, in which case the final keys and
        values that are returned will be unquoted.

        Raises: UserWarning if <path> is an improperly encoded path
        string and self.strict is True.
        """
        if not items:
            items = []
        # Multivalue Dictionary-like interface. i.e. {'a':1, 'a':2,
        # 'b':2}
        elif callable_attr(items, 'allitems'):
            items = list(items.allitems())
        elif callable_attr(items, 'iterallitems'):
            items = list(items.iterallitems())
        # Dictionary-like interface. i.e. {'a':1, 'b':2, 'c':3}
        elif callable_attr(items, 'iteritems'):
            items = list(items.iteritems())
        elif callable_attr(items, 'items'):
            items = list(items.items())
        # Encoded query string. i.e. 'a=1&b=2&c=3'
        elif isinstance(items, basestring):
            items = self._extract_items_from_querystr(items)
        # Default to list of key:value items interface. i.e. [('a','1'),
        # ('b','2')]
        else:
            items = list(items)

        return items

    def _extract_items_from_querystr(self, querystr):
        pairstrs = [s2 for s1 in querystr.split('&') for s2 in s1.split(';')]

        if self.strict:
            pairs = map(lambda item: item.split('=', 1), pairstrs)
            pairs = map(lambda p: (p[0], '') if len(p) == 1
                        else (p[0], p[1]), pairs)
            for key, value in pairs:
                valid_key = is_valid_encoded_query_key(key)
                valid_value = is_valid_encoded_query_value(value)
                if not valid_key or not valid_value:
                    s = ("Improperly encoded query string received: '%s'. "
                         "Proceeding, but did you mean '%s'?" %
                         (querystr, urllib.urlencode(pairs)))
                    warnings.warn(s, UserWarning)

        items = []
        parsed_items = urlparse.parse_qsl(querystr, keep_blank_values=True)
        for (key, value), pairstr in izip(parsed_items, pairstrs):
            # Empty value without '=', like '?sup'. Encode to utf8 to handle
            # unicode strings.
            if key.encode('utf8') == urllib.quote_plus(pairstr.encode('utf8')):
                value = None
            items.append((key, value))
        return items


class QueryCompositionInterface(object):

    """
    Abstract class interface for a parent class that contains a Query.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, strict=False):
        self._query = Query(strict=strict)

    @property
    def query(self):
        return self._query

    @property
    def querystr(self):
        """This method is deprecated. Use str(furl.query) instead."""
        s = ('furl.querystr is deprecated. Use str(furl.query) instead. There '
             'should be one, and preferably only one, obvious way to serialize'
             ' a Query object to a string.')
        warnings.warn(s, DeprecationWarning)
        return str(self._query)

    @property
    def args(self):
        """
        Shortcut method to access the query parameters, self._query.params.
        """
        return self._query.params

    def __setattr__(self, attr, value):
        """
        Returns: True if this attribute is handled and set here, False
        otherwise.
        """
        if attr == 'args' or attr == 'query':
            self._query.load(value)
            return True
        return False


class Fragment(FragmentPathCompositionInterface, QueryCompositionInterface):

    """
    Represents a URL fragment, comprised internally of a Path and Query
    optionally separated by a '?' character.

      http://tools.ietf.org/html/rfc3986#section-3.5

    Attributes:
      path: Path object from FragmentPathCompositionInterface.
      query: Query object from QueryCompositionInterface.
      separator: Boolean whether or not a '?' separator should be
        included in the string representation of this fragment. When
        False, a '?' character will not separate the fragment path from
        the fragment query in the fragment string. This is useful to
        build fragments like '#!arg1=val1&arg2=val2', where no
        separating '?' is desired.
    """

    def __init__(self, fragment='', strict=False):
        FragmentPathCompositionInterface.__init__(self, strict=strict)
        QueryCompositionInterface.__init__(self, strict=strict)
        self.strict = strict
        self.separator = True

        self.load(fragment)

    def load(self, fragment):
        self.path.load('')
        self.query.load('')

        toks = fragment.split('?', 1)
        if len(toks) == 0:
            self._path.load('')
            self._query.load('')
        elif len(toks) == 1:
            # Does this fragment look like a path or a query? Default to
            # path.
            if '=' in fragment:  # Query example: '#woofs=dogs'.
                self._query.load(fragment)
            else:  # Path example: '#supinthisthread'.
                self._path.load(fragment)
        else:
            # Does toks[1] actually look like a query? Like 'a=a' or
            # 'a=' or '=a'?
            if '=' in toks[1]:
                self._path.load(toks[0])
                self._query.load(toks[1])
            # If toks[1] doesn't look like a query, the user probably
            # provided a fragment string like 'a?b?' that was intended
            # to be adopted as-is, not a two part fragment with path 'a'
            # and query 'b?'.
            else:
                self._path.load(fragment)

    def add(self, path=_absent, args=_absent):
        if path is not _absent:
            self.path.add(path)
        if args is not _absent:
            self.query.add(args)
        return self

    def set(self, path=_absent, args=_absent, separator=_absent):
        if path is not _absent:
            self.path.load(path)
        if args is not _absent:
            self.query.load(args)
        if separator is True or separator is False:
            self.separator = separator
        return self

    def remove(self, fragment=_absent, path=_absent, args=_absent):
        if fragment is True:
            self.load('')
        if path is not _absent:
            self.path.remove(path)
        if args is not _absent:
            self.query.remove(args)
        return self

    def __setattr__(self, attr, value):
        if (not PathCompositionInterface.__setattr__(self, attr, value) and
                not QueryCompositionInterface.__setattr__(self, attr, value)):
            object.__setattr__(self, attr, value)

    def __nonzero__(self):
        return bool(self.path) or bool(self.query)

    def __str__(self):
        path, query = str(self._path), str(self._query)

        # If there is no query or self.separator is False, decode all
        # '?' characters in the path from their percent encoded form
        # '%3F' to '?'. This allows for fragment strings containg '?'s,
        # like '#dog?machine?yes'.
        if path and (not query or not self.separator):
            path = path.replace('%3F', '?')

        if query and path:
            return path + ('?' if self.separator else '') + query
        return path + query

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, str(self))


class FragmentCompositionInterface(object):

    """
    Abstract class interface for a parent class that contains a
    Fragment.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, strict=False):
        self._fragment = Fragment(strict=strict)

    @property
    def fragment(self):
        return self._fragment

    @property
    def fragmentstr(self):
        """This method is deprecated. Use str(furl.fragment) instead."""
        s = ('furl.fragmentstr is deprecated. Use str(furl.fragment) instead. '
             'There should be one, and preferably only one, obvious way to '
             'serialize a Fragment object to a string.')
        warnings.warn(s, DeprecationWarning)
        return str(self._fragment)

    def __setattr__(self, attr, value):
        """
        Returns: True if this attribute is handled and set here, False
        otherwise.
        """
        if attr == 'fragment':
            self.fragment.load(value)
            return True
        return False


class furl(URLPathCompositionInterface, QueryCompositionInterface,
           FragmentCompositionInterface):

    """
    Object for simple parsing and manipulation of a URL and its
    components.

      scheme://username:password@host:port/path?query#fragment

    Attributes:
      DEFAULT_PORTS:
      strict: Boolean whether or not UserWarnings should be raised if
        improperly encoded path, query, or fragment strings are provided
        to methods that take such strings, like load(), add(), set(),
        remove(), etc.
      username: Username string for authentication. Initially None.
      password: Password string for authentication with
        <username>. Initially None.
      scheme: URL scheme. A string ('http', 'https', '', etc) or None.
        All lowercase. Initially None.
      host: URL host (domain, IPv4 address, or IPv6 address), not
        including port. All lowercase. Initially None.
      port: Port. Valid port values are 1-65535, or None meaning no port
        specified.
      netloc: Network location. Combined host and port string. Initially
      None.
      path: Path object from URLPathCompositionInterface.
      query: Query object from QueryCompositionInterface.
      fragment: Fragment object from FragmentCompositionInterface.
    """

    def __init__(self, url='', strict=False):
        """
        Raises: ValueError on invalid url.
        """
        URLPathCompositionInterface.__init__(self, strict=strict)
        QueryCompositionInterface.__init__(self, strict=strict)
        FragmentCompositionInterface.__init__(self, strict=strict)
        self.strict = strict

        self.load(url)  # Raises ValueError on invalid url.

    def load(self, url):
        """
        Parse and load a URL.

        Raises: ValueError on invalid URL (for example malformed IPv6
        address or invalid port).
        """
        self._host = self._port = self._scheme = None
        self.username = self.password = self.scheme = None

        if not isinstance(url, basestring):
            url = str(url)

        # urlsplit() raises a ValueError on malformed IPv6 addresses in
        # Python 2.7+. In Python <= 2.6, urlsplit() doesn't raise a
        # ValueError on malformed IPv6 addresses.
        tokens = urlsplit(url)

        self.netloc = tokens.netloc  # Raises ValueError in Python 2.7+.
        self.scheme = tokens.scheme
        if not self.port:
            self._port = DEFAULT_PORTS.get(self.scheme)
        self.path.load(tokens.path)
        self.query.load(tokens.query)
        self.fragment.load(tokens.fragment)
        return self

    @property
    def scheme(self):
        return self._scheme

    @scheme.setter
    def scheme(self, scheme):
        if isinstance(scheme, basestring):
            scheme = scheme.lower()
        self._scheme = scheme

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, host):
        """
        Raises: ValueError on malformed IPv6 address.
        """
        urlparse.urlsplit('http://%s/' % host)  # Raises ValueError.
        self._host = host

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, port):
        """
        A port value can 1-65535 or None meaning no port specified. If <port>
        is None and self.scheme is a known scheme in DEFAULT_PORTS, the default
        port value from DEFAULT_PORTS will be used.

        Raises: ValueError on invalid port.
        """
        if port is None:
            self._port = DEFAULT_PORTS.get(self.scheme)
        elif is_valid_port(port):
            self._port = int(str(port))
        else:
            raise ValueError("Invalid port: '%s'" % port)

    @property
    def netloc(self):
        userpass = self.username or ''
        if self.password is not None:
            userpass += ':' + self.password
        if userpass or self.username is not None:
            userpass += '@'

        netloc = self.host or ''
        if self.port and self.port != DEFAULT_PORTS.get(self.scheme):
            netloc += ':' + str(self.port)

        netloc = ((userpass or '') + (netloc or ''))
        return netloc if (netloc or self.host == '') else None

    @netloc.setter
    def netloc(self, netloc):
        """
        Params:
          netloc: Network location string, like 'google.com' or
            'google.com:99'.
        Raises: ValueError on invalid port or malformed IPv6 address.
        """
        # Raises ValueError on malformed IPv6 addresses.
        urlparse.urlsplit('http://%s/' % netloc)

        username = password = host = port = None

        if '@' in netloc:
            userpass, netloc = netloc.split('@', 1)
            if ':' in userpass:
                username, password = userpass.split(':', 1)
            else:
                username = userpass

        if ':' in netloc:
            # IPv6 address literal.
            if ']' in netloc:
                colonpos, bracketpos = netloc.rfind(':'), netloc.rfind(']')
                if colonpos > bracketpos and colonpos != bracketpos + 1:
                    raise ValueError("Invalid netloc: '%s'" % netloc)
                elif colonpos > bracketpos and colonpos == bracketpos + 1:
                    host, port = netloc.rsplit(':', 1)
                else:
                    host = netloc.lower()
            else:
                host, port = netloc.rsplit(':', 1)
                host = host.lower()
        else:
            host = netloc.lower()

        # Avoid side effects by assigning self.port before self.host so
        # that if an exception is raised when assigning self.port,
        # self.host isn't updated.
        self.port = port  # Raises ValueError on invalid port.
        self.host = host or None
        self.username = username or None
        self.password = password or None

    @property
    def url(self):
        return str(self)

    @url.setter
    def url(self, url):
        return self._parse(url)

    def add(self, args=_absent, path=_absent, fragment_path=_absent,
            fragment_args=_absent, query_params=_absent):
        """
        Add components to a URL and return this furl instance, <self>.

        If both <args> and <query_params> are provided, a UserWarning is
        raised because <args> is provided as a shortcut for
        <query_params>, not to be used simultaneously with
        <query_params>. Nonetheless, providing both <args> and
        <query_params> behaves as expected, with query keys and values
        from both <args> and <query_params> added to the query - <args>
        first, then <query_params>.

        Parameters:
          args: Shortcut for <query_params>.
          path: A list of path segments to add to the existing path
            segments, or a path string to join with the existing path
            string.
          query_params: A dictionary of query keys and values or list of
            key:value items to add to the query.
          fragment_path: A list of path segments to add to the existing
            fragment path segments, or a path string to join with the
            existing fragment path string.
          fragment_args: A dictionary of query keys and values or list
            of key:value items to add to the fragment's query.

        Returns: <self>.

        Raises: UserWarning if redundant and possibly conflicting <args> and
        <query_params> were provided.
        """
        if args is not _absent and query_params is not _absent:
            s = ('Both <args> and <query_params> provided to furl.add(). '
                 '<args> is a shortcut for <query_params>, not to be used '
                 'with <query_params>. See furl.add() documentation for more '
                 'details.')
            warnings.warn(s, UserWarning)

        if path is not _absent:
            self.path.add(path)
        if args is not _absent:
            self.query.add(args)
        if query_params is not _absent:
            self.query.add(query_params)
        if fragment_path is not _absent or fragment_args is not _absent:
            self.fragment.add(path=fragment_path, args=fragment_args)
        return self

    def set(self, args=_absent, path=_absent, fragment=_absent, scheme=_absent,
            netloc=_absent, fragment_path=_absent, fragment_args=_absent,
            fragment_separator=_absent, host=_absent, port=_absent,
            query=_absent, query_params=_absent, username=_absent,
            password=_absent):
        """
        Set components of a url and return this furl instance, <self>.

        If any overlapping, and hence possibly conflicting, parameters
        are provided, appropriate UserWarning's will be raised. The
        groups of parameters that could potentially overlap are

          <netloc> and (<host> or <port>)
          <fragment> and (<fragment_path> and/or <fragment_args>)
          any two or all of <query>, <args>, and/or <query_params>

        In all of the above groups, the latter parameter(s) take
        precedence over the earlier parameter(s). So, for example

          furl('http://google.com/').set(
            netloc='yahoo.com:99', host='bing.com', port=40)

        will result in a UserWarning being raised and the url becoming

          'http://bing.com:40/'

        not

          'http://yahoo.com:99/

        Parameters:
          args: Shortcut for <query_params>.
          path: A list of path segments or a path string to adopt.
          fragment: Fragment string to adopt.
          scheme: Scheme string to adopt.
          netloc: Network location string to adopt.
          query: Query string to adopt.
          query_params: A dictionary of query keys and values or list of
            key:value items to adopt.
          fragment_path: A list of path segments to adopt for the
            fragment's path or a path string to adopt as the fragment's
            path.
          fragment_args: A dictionary of query keys and values or list
            of key:value items for the fragment's query to adopt.
          fragment_separator: Boolean whether or not there should be a
            '?' separator between the fragment path and fragment query.
          host: Host string to adopt.
          port: Port number to adopt.
          username: Username string to adopt.
          password: Password string to adopt.
        Raises:
          ValueError on invalid port.
          UserWarning if <netloc> and (<host> and/or <port>) are
            provided.
          UserWarning if <query>, <args>, and/or <query_params> are
            provided.
          UserWarning if <fragment> and (<fragment_path>,
            <fragment_args>, and/or <fragment_separator>) are provided.
        Returns: <self>.
        """
        netloc_present = netloc is not _absent
        if (netloc_present and (host is not _absent or port is not _absent)):
            s = ('Possible parameter overlap: <netloc> and <host> and/or '
                 '<port> provided. See furl.set() documentation for more '
                 'details.')
            warnings.warn(s, UserWarning)
        if ((args is not _absent and query is not _absent) or
            (query is not _absent and query_params is not _absent) or
                (args is not _absent and query_params is not _absent)):
            s = ('Possible parameter overlap: <query>, <args>, and/or '
                 '<query_params> provided. See furl.set() documentation for '
                 'more details.')
            warnings.warn(s, UserWarning)
        if (fragment is not _absent and
            (fragment_path is not _absent or fragment_args is not _absent or
             (fragment_separator is not _absent))):
            s = ('Possible parameter overlap: <fragment> and '
                 '(<fragment_path>and/or <fragment_args>) or <fragment> '
                 'and <fragment_separator> provided. See furl.set() '
                 'documentation for more details.')
            warnings.warn(s, UserWarning)

        # Avoid side effects if exceptions are raised.
        oldnetloc, oldport = self.netloc, self.port
        try:
            if netloc is not _absent:
                # Raises ValueError on invalid port or malformed IP.
                self.netloc = netloc
            if port is not _absent:
                self.port = port  # Raises ValueError on invalid port.
        except ValueError:
            self.netloc, self.port = oldnetloc, oldport
            raise

        if username is not _absent:
            self.username = username
        if password is not _absent:
            self.password = password
        if scheme is not _absent:
            self.scheme = scheme
        if host is not _absent:
            self.host = host

        if path is not _absent:
            self.path.load(path)
        if query is not _absent:
            self.query.load(query)
        if args is not _absent:
            self.query.load(args)
        if query_params is not _absent:
            self.query.load(query_params)
        if fragment is not _absent:
            self.fragment.load(fragment)
        if fragment_path is not _absent:
            self.fragment.path.load(fragment_path)
        if fragment_args is not _absent:
            self.fragment.query.load(fragment_args)
        if fragment_separator is not _absent:
            self.fragment.separator = fragment_separator
        return self

    def remove(self, args=_absent, path=_absent, fragment=_absent,
               query=_absent, query_params=_absent, port=False,
               fragment_path=_absent, fragment_args=_absent, username=False,
               password=False):
        """
        Remove components of this furl's URL and return this furl
        instance, <self>.

        Parameters:
          args: Shortcut for query_params.
          path: A list of path segments to remove from the end of the
            existing path segments list, or a path string to remove from
            the end of the existing path string, or True to remove the
            path entirely.
          query: If True, remove the query portion of the URL entirely.
          query_params: A list of query keys to remove from the query,
            if they exist.
          port: If True, remove the port from the network location
            string, if it exists.
          fragment: If True, remove the fragment portion of the URL
            entirely.
          fragment_path: A list of path segments to remove from the end
            of the fragment's path segments or a path string to remove
            from the end of the fragment's path string.
          fragment_args: A list of query keys to remove from the
            fragment's query, if they exist.
          username: If True, remove the username, if it exists.
          password: If True, remove the password, if it exists.
        Returns: <self>.
        """
        if port is True:
            self.port = None
        if username is True:
            self.username = None
        if password is True:
            self.password = None
        if path is not _absent:
            self.path.remove(path)
        if args is not _absent:
            self.query.remove(args)
        if query is not _absent:
            self.query.remove(query)
        if fragment is not _absent:
            self.fragment.remove(fragment)
        if query_params is not _absent:
            self.query.remove(query_params)
        if fragment_path is not _absent:
            self.fragment.path.remove(fragment_path)
        if fragment_args is not _absent:
            self.fragment.query.remove(fragment_args)
        return self

    def join(self, url):
        self.load(urljoin(self.url, str(url)))
        return self

    def copy(self):
        return self.__class__(self)

    def __eq__(self, other):
        return self.url == other.url

    def __setattr__(self, attr, value):
        if (not PathCompositionInterface.__setattr__(self, attr, value) and
            not QueryCompositionInterface.__setattr__(self, attr, value) and
            not FragmentCompositionInterface.__setattr__(self, attr, value)):
            object.__setattr__(self, attr, value)

    def __str__(self):
        path, query, fragment = str(self.path), str(
            self.query), str(self.fragment)
        url = urlparse.urlunsplit(
            (self.scheme, self.netloc, path, query, fragment))

        # Special cases.
        if self.scheme is None:
            if url.startswith('//'):
                url = url[2:]
            elif url.startswith('://'):
                url = url[3:]
        elif self.scheme in COLON_SEPARATED_SCHEMES:
            # Change a '://' separator to ':'. Leave a ':' separator as-is.
            url = _set_scheme(url, self.scheme)
        elif (self.scheme is not None and
              (url == '' or  # Protocol relative URL.
               (url == '%s:' % self.scheme and not str(self.path)))):
            url += '//'
        return url

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, str(self))


def _get_scheme(url):
    if url.lstrip().startswith('//'):  # Protocol relative URL.
        return ''
    beforeColon = url[:max(0, url.find(':'))]
    if beforeColon in COLON_SEPARATED_SCHEMES:
        return beforeColon
    return url[:max(0, url.find('://'))] or None


def _set_scheme(url, newscheme):
    scheme = _get_scheme(url)
    newscheme = newscheme or ''
    newseparator = ':' if newscheme in COLON_SEPARATED_SCHEMES else '://'
    if scheme == '':  # Protocol relative URL.
        url = '%s:%s' % (newscheme, url)
    elif scheme is None and url:  # No scheme.
        url = ''.join([newscheme, newseparator, url])
    elif scheme:  # Existing scheme.
        remainder = url[len(scheme):]
        if remainder.startswith('://'):
            remainder = remainder[3:]
        elif remainder.startswith(':'):
            remainder = remainder[1:]
        url = ''.join([newscheme, newseparator, remainder])
    return url


def urlsplit(url):
    """
    Parameters:
      url: URL string to split.

    Returns: urlparse.SplitResult tuple subclass, just like
    urlparse.urlsplit() returns, with fields (scheme, netloc, path,
    query, fragment, username, password, hostname, port). See the url
    below for more details on urlsplit().

      http://docs.python.org/library/urlparse.html#urlparse.urlsplit
    """
    original_scheme = _get_scheme(url)

    def _change_urltoks_scheme(tup, scheme):
        l = list(tup)
        l[0] = scheme
        return tuple(l)

    # urlsplit() only parses the query for schemes in urlparse.uses_query,
    # so switch to 'http' (a scheme in urlparse.uses_query) for
    # urlparse.urlsplit() and switch back afterwards.
    if original_scheme is not None:
        url = _set_scheme(url, 'http')
    toks = urlparse.urlsplit(url)
    return urlparse.SplitResult(*_change_urltoks_scheme(toks, original_scheme))


def urljoin(base, url):
    """
    Parameters:
      base: Base URL to join with <url>.
      url: Relative or absolute URL to join with <base>.

    Returns: The resultant URL from joining <base> and <url>.
    """
    base_scheme, url_scheme = urlsplit(base).scheme, urlsplit(url).scheme
    httpbase = _set_scheme(base, 'http')
    joined = urlparse.urljoin(httpbase, url)
    if not url_scheme:
        joined = _set_scheme(joined, base_scheme)
    return joined


def join_path_segments(*args):
    """
    Join multiple lists of path segments together, intelligently
    handling path segments borders to preserve intended slashes of the
    final constructed path.

    This function is not encoding aware - it does not test for or change
    the encoding of path segments it is passed.

    Examples:
      join_path_segments(['a'], ['b']) == ['a','b']
      join_path_segments(['a',''], ['b']) == ['a','b']
      join_path_segments(['a'], ['','b']) == ['a','b']
      join_path_segments(['a',''], ['','b']) == ['a','','b']
      join_path_segments(['a','b'], ['c','d']) == ['a','b','c','d']

    Returns: A list containing the joined path segments.
    """
    finals = []
    for segments in args:
        if not segments or segments == ['']:
            continue
        elif not finals:
            finals.extend(segments)
        else:
            # Example #1: ['a',''] + ['b'] == ['a','b']
            # Example #2: ['a',''] + ['','b'] == ['a','','b']
            if finals[-1] == '' and (segments[0] != '' or len(segments) > 1):
                finals.pop(-1)
            # Example: ['a'] + ['','b'] == ['a','b']
            elif finals[-1] != '' and segments[0] == '' and len(segments) > 1:
                segments = segments[1:]
            finals.extend(segments)
    return finals


def remove_path_segments(segments, remove):
    """
    Removes the path segments of <remove> from the end of the path
    segments <segments>.

    Examples:
      # '/a/b/c' - 'b/c' == '/a/'
      remove_path_segments(['','a','b','c'], ['b','c']) == ['','a','']
      # '/a/b/c' - '/b/c' == '/a'
      remove_path_segments(['','a','b','c'], ['','b','c']) == ['','a']

    Returns: The list of all remaining path segments after the segments
    in <remove> have been removed from the end of <segments>. If no
    segments from <remove> were removed from <segments>, <segments> is
    returned unmodified.
    """
    # [''] means a '/', which is properly represented by ['', ''].
    if segments == ['']:
        segments.append('')
    if remove == ['']:
        remove.append('')

    ret = None
    if remove == segments:
        ret = []
    elif len(remove) > len(segments):
        ret = segments
    else:
        toremove = list(remove)

        if len(remove) > 1 and remove[0] == '':
            toremove.pop(0)

        if toremove and toremove == segments[-1 * len(toremove):]:
            ret = segments[:len(segments) - len(toremove)]
            if remove[0] != '' and ret:
                ret.append('')
        else:
            ret = segments

    return ret


def is_valid_port(port):
    port = str(port)
    if not port.isdigit() or int(port) == 0 or int(port) > 65535:
        return False
    return True


def callable_attr(obj, attr):
    return hasattr(obj, attr) and callable(getattr(obj, attr))


def u2utf8(s):
    if isinstance(s, unicode):
        return s.encode('utf8')
    return s


#
# TODO(grun): These regex functions need to be expanded to reflect the
# fact that the valid encoding for a URL Path segment is different from
# a Fragment Path segment, and valid URL Query key and value encoding
# is different than valid Fragment Query key and value encoding.
#
# For example, '?' and '#' don't need to be encoded in Fragment Path
# segments but they must be encoded in URL Path segments.
#
# Similarly, '#' doesn't need to be encoded in Fragment Query keys and
# values, but must be encoded in URL Query keys and values.
#
# Perhaps merge them with URLPath, FragmentPath, URLQuery, and
# FragmentQuery when those new classes are created (see the TODO
# currently at the top of the source, 02/03/2012).
#

# RFC 3986
#   unreserved  = ALPHA / DIGIT / "-" / "." / "_" / "~"
#
#   pct-encoded = "%" HEXDIG HEXDIG
#
#   sub-delims  = "!" / "$" / "&" / "'" / "(" / ")"
#                 / "*" / "+" / "," / ";" / "="
#
#   pchar         = unreserved / pct-encoded / sub-delims / ":" / "@"
#
#   ====
#   Path
#   ====
#   segment       = *pchar
#
#   =====
#   Query
#   =====
#   query       = *( pchar / "/" / "?" )
#
VALID_ENCODED_PATH_SEGMENT_REGEX = re.compile(
    r'^([\w\-\.\~\:\@\!\$\&\'\(\)\*\+\,\;\=]|(\%[\da-fA-F][\da-fA-F]))*$')
def is_valid_encoded_path_segment(segment):
    return bool(VALID_ENCODED_PATH_SEGMENT_REGEX.match(segment))


VALID_ENCODED_QUERY_KEY_REGEX = re.compile(
    r'^([\w\-\.\~\:\@\!\$\&\'\(\)\*\+\,\;\/\?]|(\%[\da-fA-F][\da-fA-F]))*$')
def is_valid_encoded_query_key(key):
    return bool(VALID_ENCODED_QUERY_KEY_REGEX.match(key))


VALID_ENCODED_QUERY_VALUE_REGEX = re.compile(
    r'^([\w\-\.\~\:\@\!\$\&\'\(\)\*\+\,\;\/\?\=]|(\%[\da-fA-F][\da-fA-F]))*$')
def is_valid_encoded_query_value(value):
    return bool(VALID_ENCODED_QUERY_VALUE_REGEX.match(value))

########NEW FILE########
__FILENAME__ = omdict1D
#
# furl - URL manipulation made simple.
#
# Arthur Grunseid
# grunseid.com
# grunseid@gmail.com
#
# License: Build Amazing Things (Unlicense)

from orderedmultidict import omdict


class omdict1D(omdict):

    """
    One dimensional ordered multivalue dictionary. Whenever a list of
    values is passed to set(), __setitem__(), add(), update(), or
    updateall(), it's treated as multiple values and the appropriate
    'list' method is called on that list, like setlist() or
    addlist(). For example:

      omd = omdict1D()

      omd[1] = [1,2,3]
      omd[1] != [1,2,3] # True.
      omd[1] == 1 # True.
      omd.getlist(1) == [1,2,3] # True.

      omd.add(2, [2,3,4])
      omd[2] != [2,3,4] # True.
      omd[2] == 2 # True.
      omd.getlist(2) == [2,3,4] # True.

      omd.update([(3, [3,4,5])])
      omd[3] != [3,4,5] # True.
      omd[3] == 3 # True.
      omd.getlist(3) == [3,4,5] # True.

      omd = omdict([(1,None),(2,None)])
      omd.updateall([(1,[1,11]), (2,[2,22])])
      omd.allitems == [(1,1), (1,11), (2,2), (2,22)]
    """

    def add(self, key, value=[]):
        if not self._quacks_like_a_list_but_not_str(value):
            value = [value]
        if value:
            self._map.setdefault(key, [])
        for val in value:
            node = self._items.append(key, val)
            self._map[key].append(node)
        return self

    def set(self, key, value=[None]):
        return self._set(key, value)

    def __setitem__(self, key, value):
        return self._set(key, value)

    def _bin_update_items(self, items, replace_at_most_one,
                          replacements, leftovers):
        """
        Subclassed from omdict._bin_update_items() to make update() and
        updateall() process lists of values as multiple values.

        <replacements and <leftovers> are modified directly, ala pass by
        reference.
        """
        for key, values in items:
            # <values> is not a list or an empty list.
            like_list_not_str = self._quacks_like_a_list_but_not_str(values)
            if not like_list_not_str or (like_list_not_str and not values):
                values = [values]

            for value in values:
                # If the value is [], remove any existing leftovers with
                # key <key> and set the list of values itself to [],
                # which in turn will later delete <key> when [] is
                # passed to omdict.setlist() in
                # omdict._update_updateall().
                if value == []:
                    replacements[key] = []
                    leftovers[:] = filter(
                        lambda item: key != item[0], leftovers)
                    continue

                # If there are existing items with key <key> that have
                # yet to be marked for replacement, mark that item's
                # value to be replaced by <value> by appending it to
                # <replacements>.  TODO: Refactor for clarity
                if (key in self and
                    (key not in replacements or
                     (key in replacements and
                      replacements[key] == []))):
                    replacements[key] = [value]
                elif (key in self and not replace_at_most_one and
                      len(replacements[key]) < len(self.values(key))):
                    replacements[key].append(value)
                else:
                    if replace_at_most_one:
                        replacements[key] = [value]
                    else:
                        leftovers.append((key, value))

    def _set(self, key, value=[None]):
        if not self._quacks_like_a_list_but_not_str(value):
            value = [value]
        self.setlist(key, value)
        return self

    def _quacks_like_a_list_but_not_str(self, duck):
        return (hasattr(duck, '__iter__') and callable(duck.__iter__) and
                not isinstance(duck, basestring))

########NEW FILE########
__FILENAME__ = test_furl
# -*- coding: utf-8 -*-
#
# furl - URL manipulation made simple.
#
# Arthur Grunseid
# grunseid.com
# grunseid@gmail.com
#
# License: Build Amazing Things (Unlicense)

import sys
import urllib
if sys.version_info[0] >= 2 and sys.version_info[1] >= 7:
    import unittest
else:
    import unittest2 as unittest
import urlparse
import warnings
from itertools import izip
from abc import ABCMeta, abstractmethod
try:
    from collections import OrderedDict as odict  # Python 2.7+.
except ImportError:
    from ordereddict import OrderedDict as odict  # Python 2.4-2.6.

import furl
from furl.omdict1D import omdict1D

PYTHON_27PLUS = sys.version_info[0] >= 2 and sys.version_info[1] >= 7

#
# TODO(grun): Add tests for furl objects with strict=True. Make sure
# UserWarnings are raised when improperly encoded path, query, and
# fragment strings are provided.
#


class itemcontainer(object):

    """
    Utility list subclasses to expose allitems() and iterallitems()
    methods on different kinds of item containers - lists, dictionaries,
    multivalue dictionaries, and query strings. This provides a common
    iteration interface for looping through their items (including items
    with repeated keys).  original() is also provided to get access to a
    copy of the original container.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def allitems(self):
        pass

    @abstractmethod
    def iterallitems(self):
        pass

    @abstractmethod
    def original(self):
        """
        Returns: A copy of the original data type. For example, an
        itemlist would return a list, itemdict a dict, etc.
        """
        pass


class itemlist(list, itemcontainer):

    def allitems(self):
        return list(self.iterallitems())

    def iterallitems(self):
        return iter(self)

    def original(self):
        return list(self)


class itemdict(odict, itemcontainer):

    def allitems(self):
        return self.items()

    def iterallitems(self):
        return self.iteritems()

    def original(self):
        return dict(self)


class itemomdict1D(omdict1D, itemcontainer):

    def original(self):
        return omdict1D(self)


class itemstr(str, itemcontainer):

    def allitems(self):
        # Keys and values get unquoted. i.e. 'a=a%20a' -> ['a', 'a a']. Empty
        # values without '=' have value None.
        items = []
        parsed = urlparse.parse_qsl(self, keep_blank_values=True)
        pairstrs = pairstrs = [s2 for s1 in self.split('&')
                               for s2 in s1.split(';')]
        for (key, value), pairstr in zip(parsed, pairstrs):
            if key == urllib.quote_plus(pairstr):
                value = None
            items.append((key, value))
        return items

    def iterallitems(self):
        return iter(self.allitems())

    def original(self):
        return str(self)


class TestPath(unittest.TestCase):

    def test_isdir_isfile(self):
        for path in ['', '/']:
            p = furl.Path(path)
            assert p.isdir
            assert not p.isfile

        paths = ['dir1/', 'd1/d2/', 'd/d/d/d/d/', '/', '/dir1/', '/d1/d2/d3/']
        for path in paths:
            p = furl.Path(path)
            assert p.isdir
            assert not p.isfile

        for path in ['dir1', 'd1/d2', 'd/d/d/d/d', '/dir1', '/d1/d2/d3']:
            p = furl.Path(path)
            assert p.isfile
            assert not p.isdir

    def test_leading_slash(self):
        p = furl.Path('')
        assert not p.isabsolute
        assert not p.segments
        assert p.isdir and p.isdir != p.isfile
        assert str(p) == ''

        p = furl.Path('/')
        assert p.isabsolute
        assert p.segments == ['']
        assert p.isdir and p.isdir != p.isfile
        assert str(p) == '/'

        p = furl.Path('sup')
        assert not p.isabsolute
        assert p.segments == ['sup']
        assert p.isfile and p.isdir != p.isfile
        assert str(p) == 'sup'

        p = furl.Path('/sup')
        assert p.isabsolute
        assert p.segments == ['sup']
        assert p.isfile and p.isdir != p.isfile
        assert str(p) == '/sup'

        p = furl.Path('a/b/c')
        assert not p.isabsolute
        assert p.segments == ['a', 'b', 'c']
        assert p.isfile and p.isdir != p.isfile
        assert str(p) == 'a/b/c'

        p = furl.Path('/a/b/c')
        assert p.isabsolute
        assert p.segments == ['a', 'b', 'c']
        assert p.isfile and p.isdir != p.isfile
        assert str(p) == '/a/b/c'

        p = furl.Path('a/b/c/')
        assert not p.isabsolute
        assert p.segments == ['a', 'b', 'c', '']
        assert p.isdir and p.isdir != p.isfile
        assert str(p) == 'a/b/c/'

        p.isabsolute = True
        assert p.isabsolute
        assert str(p) == '/a/b/c/'

    def test_encoding(self):
        encoded = ['a%20a', '/%7haypepps/', 'a/:@/a', 'a%2Fb']
        unencoded = ['a+a', '/~haypepps/', 'a/:@/a', 'a/b']

        for path in encoded:
            assert str(furl.Path(path)) == path

        for path in unencoded:
            assert str(furl.Path(path)) == urllib.quote(
                path, "/:@-._~!$&'()*+,;=")

        # Valid path segment characters should not be encoded.
        for char in ":@-._~!$&'()*+,;=":
            f = furl.furl().set(path=char)
            assert str(f.path) == f.url == char
            assert f.path.segments == [char]

        # Invalid path segment characters should be encoded.
        for char in ' ^`<>[]"?':
            f = furl.furl().set(path=char)
            assert str(f.path) == f.url == urllib.quote(char)
            assert f.path.segments == [char]

        # Encode '/' within a path segment.
        segment = 'a/b'  # One path segment that includes the '/' character.
        f = furl.furl().set(path=[segment])
        assert str(f.path) == 'a%2Fb'
        assert f.path.segments == [segment]
        assert f.url == 'a%2Fb'

    def test_load(self):
        self._test_set_load(furl.Path.load)

    def test_set(self):
        self._test_set_load(furl.Path.set)

    def _test_set_load(self, path_set_or_load):
        p = furl.Path('a/b/c/')
        assert path_set_or_load(p, 'asdf/asdf/') == p
        assert not p.isabsolute
        assert str(p) == 'asdf/asdf/'
        assert path_set_or_load(p, ['a', 'b', 'c', '']) == p
        assert not p.isabsolute
        assert str(p) == 'a/b/c/'
        assert path_set_or_load(p, ['', 'a', 'b', 'c', '']) == p
        assert p.isabsolute
        assert str(p) == '/a/b/c/'

    def test_add(self):
        # URL paths.
        p = furl.furl('a/b/c/').path
        assert p.add('d') == p
        assert not p.isabsolute
        assert str(p) == 'a/b/c/d'
        assert p.add('/') == p
        assert not p.isabsolute
        assert str(p) == 'a/b/c/d/'
        assert p.add(['e', 'f', 'e e', '']) == p
        assert not p.isabsolute
        assert str(p) == 'a/b/c/d/e/f/e%20e/'

        p = furl.furl().path
        assert not p.isabsolute
        assert p.add('/') == p
        assert p.isabsolute
        assert str(p) == '/'
        assert p.add('pump') == p
        assert p.isabsolute
        assert str(p) == '/pump'

        p = furl.furl().path
        assert not p.isabsolute
        assert p.add(['', '']) == p
        assert p.isabsolute
        assert str(p) == '/'
        assert p.add(['pump', 'dump', '']) == p
        assert p.isabsolute
        assert str(p) == '/pump/dump/'

        p = furl.furl('http://sprop.ru/a/b/c/').path
        assert p.add('d') == p
        assert p.isabsolute
        assert str(p) == '/a/b/c/d'
        assert p.add('/') == p
        assert p.isabsolute
        assert str(p) == '/a/b/c/d/'
        assert p.add(['e', 'f', 'e e', '']) == p
        assert p.isabsolute
        assert str(p) == '/a/b/c/d/e/f/e%20e/'

        f = furl.furl('http://sprop.ru')
        assert not f.path.isabsolute
        f.path.add('sup')
        assert f.path.isabsolute and str(f.path) == '/sup'

        f = furl.furl('/mrp').add(path='sup')
        assert str(f.path) == '/mrp/sup'

        f = furl.furl('/').add(path='/sup')
        assert f.path.isabsolute and str(f.path) == '/sup'

        f = furl.furl('/hi').add(path='sup')
        assert f.path.isabsolute and str(f.path) == '/hi/sup'

        f = furl.furl('/hi').add(path='/sup')
        assert f.path.isabsolute and str(f.path) == '/hi/sup'

        f = furl.furl('/hi/').add(path='/sup')
        assert f.path.isabsolute and str(f.path) == '/hi//sup'

        # Fragment paths.
        f = furl.furl('http://sprop.ru#mrp')
        assert not f.fragment.path.isabsolute
        f.fragment.path.add('sup')
        assert not f.fragment.path.isabsolute
        assert str(f.fragment.path) == 'mrp/sup'

        f = furl.furl('http://sprop.ru#/mrp')
        assert f.fragment.path.isabsolute
        f.fragment.path.add('sup')
        assert f.fragment.path.isabsolute
        assert str(f.fragment.path) == '/mrp/sup'

    def test_remove(self):
        # Remove lists of path segments.
        p = furl.Path('a/b/s%20s/')
        assert p.remove(['b', 's s']) == p
        assert str(p) == 'a/b/s%20s/'
        assert p.remove(['b', 's s', '']) == p
        assert str(p) == 'a/'
        assert p.remove(['', 'a']) == p
        assert str(p) == 'a/'
        assert p.remove(['a']) == p
        assert str(p) == 'a/'
        assert p.remove(['a', '']) == p
        assert str(p) == ''

        p = furl.Path('a/b/s%20s/')
        assert p.remove(['', 'b', 's s']) == p
        assert str(p) == 'a/b/s%20s/'
        assert p.remove(['', 'b', 's s', '']) == p
        assert str(p) == 'a'
        assert p.remove(['', 'a']) == p
        assert str(p) == 'a'
        assert p.remove(['a', '']) == p
        assert str(p) == 'a'
        assert p.remove(['a']) == p
        assert str(p) == ''

        p = furl.Path('a/b/s%20s/')
        assert p.remove(['a', 'b', 's%20s', '']) == p
        assert str(p) == 'a/b/s%20s/'
        assert p.remove(['a', 'b', 's s', '']) == p
        assert str(p) == ''

        # Remove a path string.
        p = furl.Path('a/b/s%20s/')
        assert p.remove('b/s s/') == p  # Encoding Warning.
        assert str(p) == 'a/'

        p = furl.Path('a/b/s%20s/')
        assert p.remove('b/s%20s/') == p
        assert str(p) == 'a/'
        assert p.remove('a') == p
        assert str(p) == 'a/'
        assert p.remove('/a') == p
        assert str(p) == 'a/'
        assert p.remove('a/') == p
        assert str(p) == ''

        p = furl.Path('a/b/s%20s/')
        assert p.remove('b/s s') == p  # Encoding Warning.
        assert str(p) == 'a/b/s%20s/'

        p = furl.Path('a/b/s%20s/')
        assert p.remove('b/s%20s') == p
        assert str(p) == 'a/b/s%20s/'
        assert p.remove('s%20s') == p
        assert str(p) == 'a/b/s%20s/'
        assert p.remove('s s') == p  # Encoding Warning.
        assert str(p) == 'a/b/s%20s/'
        assert p.remove('b/s%20s/') == p
        assert str(p) == 'a/'
        assert p.remove('/a') == p
        assert str(p) == 'a/'
        assert p.remove('a') == p
        assert str(p) == 'a/'
        assert p.remove('a/') == p
        assert str(p) == ''

        p = furl.Path('a/b/s%20s/')
        assert p.remove('a/b/s s/') == p  # Encoding Warning.
        assert str(p) == ''

        # Remove True.
        p = furl.Path('a/b/s%20s/')
        assert p.remove(True) == p
        assert str(p) == ''

    def test_isabsolute(self):
        paths = ['', '/', 'pump', 'pump/dump', '/pump/dump', '/pump/dump']
        for path in paths:
            # A URL path's isabsolute attribute is mutable if there's no
            # netloc.
            mutable = [
                {},  # No scheme or netloc -> isabsolute is mutable.
                {'scheme': 'nonempty'}]  # Scheme, no netloc -> isabs mutable.
            for kwargs in mutable:
                f = furl.furl().set(path=path, **kwargs)
                if path and path.startswith('/'):
                    assert f.path.isabsolute
                else:
                    assert not f.path.isabsolute
                f.path.isabsolute = False  # No exception.
                assert not f.path.isabsolute and not str(
                    f.path).startswith('/')
                f.path.isabsolute = True  # No exception.
                assert f.path.isabsolute and str(f.path).startswith('/')

            # A URL path's isabsolute attribute is read-only if there's
            # a netloc.
            readonly = [
                # Netloc, no scheme -> isabsolute is read-only if path
                # is non-empty.
                {'netloc': 'nonempty'},
                # Netloc and scheme -> isabsolute is read-only if path
                # is non-empty.
                {'scheme': 'nonempty', 'netloc': 'nonempty'}]
            for kwargs in readonly:
                f = furl.furl().set(path=path, **kwargs)
                if path:  # Exception raised.
                    with self.assertRaises(AttributeError):
                        f.path.isabsolute = False
                    with self.assertRaises(AttributeError):
                        f.path.isabsolute = True
                else:  # No exception raised.
                    f.path.isabsolute = False
                    assert not f.path.isabsolute and not str(
                        f.path).startswith('/')
                    f.path.isabsolute = True
                    assert f.path.isabsolute and str(f.path).startswith('/')

            # A Fragment path's isabsolute attribute is never read-only.
            f = furl.furl().set(fragment_path=path)
            if path and path.startswith('/'):
                assert f.fragment.path.isabsolute
            else:
                assert not f.fragment.path.isabsolute
            f.fragment.path.isabsolute = False  # No exception.
            assert (not f.fragment.path.isabsolute and
                    not str(f.fragment.path).startswith('/'))
            f.fragment.path.isabsolute = True  # No exception.
            assert f.fragment.path.isabsolute and str(
                f.fragment.path).startswith('/')

            # Sanity checks.
            f = furl.furl().set(scheme='mailto', path='dad@pumps.biz')
            assert str(f) == 'mailto:dad@pumps.biz' and not f.path.isabsolute
            f.path.isabsolute = True  # No exception.
            assert str(f) == 'mailto:/dad@pumps.biz' and f.path.isabsolute

            f = furl.furl().set(scheme='sup', fragment_path='/dad@pumps.biz')
            assert str(
                f) == 'sup:#/dad@pumps.biz' and f.fragment.path.isabsolute
            f.fragment.path.isabsolute = False  # No exception.
            assert str(
                f) == 'sup:#dad@pumps.biz' and not f.fragment.path.isabsolute

    def test_normalize(self):
        # Path not modified.
        for path in ['', 'a', '/a', '/a/', '/a/b%20b/c', '/a/b%20b/c/']:
            p = furl.Path(path)
            assert p.normalize() is p and str(p) == str(p.normalize()) == path

        # Path modified.
        tonormalize = [
            ('//', '/'), ('//a', '/a'), ('//a/', '/a/'), ('//a///', '/a/'),
            ('////a/..//b', '/b'), ('/a/..//b//./', '/b/')]
        for path, normalized in tonormalize:
            p = furl.Path(path)
            assert p.normalize() is p and str(p.normalize()) == normalized

    def test_nonzero(self):
        p = furl.Path()
        assert not p

        p = furl.Path('')
        assert not p

        p = furl.Path('')
        assert not p
        p.segments = ['']
        assert p

        p = furl.Path('asdf')
        assert p

        p = furl.Path('/asdf')
        assert p

    def test_unicode(self):
        path = u'/wiki/Восход'
        path_encoded = '/wiki/%D0%92%D0%BE%D1%81%D1%85%D0%BE%D0%B4'
        p = furl.Path(path)
        assert str(p) == path_encoded


class TestQuery(unittest.TestCase):

    def setUp(self):
        # All interaction with parameters is unquoted unless that
        # interaction is through an already encoded query string. In the
        # case of an already encoded query string like 'a=a%20a&b=b',
        # its keys and values will be unquoted.
        self.itemlists = map(itemlist, [
            [], [(1, 1)], [(1, 1), (2, 2)], [
                (1, 1), (1, 11), (2, 2), (3, 3)], [('', '')],
            [('a', 1), ('b', 2), ('a', 3)], [
                ('a', 1), ('b', 'b'), ('a', 0.23)],
            [(0.1, -0.9), (-0.1231, 12312.3123)], [
                (None, None), (None, 'pumps')],
            [('', ''), ('', '')], [('', 'a'), ('', 'b'),
                                   ('b', ''), ('b', 'b')], [('<', '>')],
            [('=', '><^%'), ('><^%', '=')], [
                ("/?:@-._~!$'()*+,", "/?:@-._~!$'()*+,=")],
            [('+', '-')], [('a%20a', 'a%20a')], [('/^`<>[]"', '/^`<>[]"=')],
            [("/?:@-._~!$'()*+,", "/?:@-._~!$'()*+,=")],
        ])
        self.itemdicts = map(itemdict, [
            {}, {1: 1, 2: 2}, {'1': '1', '2': '2',
                               '3': '3'}, {None: None}, {5.4: 4.5},
            {'': ''}, {'': 'a', 'b': ''}, {
                'pue': 'pue', 'a': 'a&a'}, {'=': '====='},
            {'pue': 'pue', 'a': 'a%26a'}, {'%': '`', '`': '%'}, {'+': '-'},
            {"/?:@-._~!$'()*+,": "/?:@-._~!$'()*+,="}, {
                '%25': '%25', '%60': '%60'},
        ])
        self.itemomdicts = map(itemomdict1D, self.itemlists)
        self.itemstrs = map(itemstr, [
            # Basics.
            '', 'a=a', 'a=a&b=b', 'q=asdf&check_keywords=yes&area=default',
            '=asdf',
            # Various quoted and unquoted parameters and values that
            # will be unquoted.
            'space=a+a&amp=a%26a', 'a a=a a&no encoding=sup', 'a+a=a+a',
            'a%20=a+a', 'a%20a=a%20a', 'a+a=a%20a', 'space=a a&amp=a^a',
            'a=a&s=s#s', '+=+', "/?:@-._~!$&'()*+,=/?:@-._~!$'()*+,=",
            'a=a&c=c%5Ec', '<=>&^="', '%3C=%3E&%5E=%22', '%=%;`=`',
            '%25=%25&%60=%60',
            # Only keys, no values.
            'asdfasdf', '/asdf/asdf/sdf', '*******', '!@#(*&@!#(*@!#', 'a&b&',
            'a;b',
            # Repeated parameters.
            'a=a&a=a', 'space=a+a&space=b+b',
            # Empty keys and/or values.
            '=', 'a=', 'a=a&a=', '=a&=b',
            # Semicolon delimeter, like 'a=a;b=b'.
            'a=a;a=a', 'space=a+a;space=b+b',
        ])
        self.items = (self.itemlists + self.itemdicts + self.itemomdicts +
                      self.itemstrs)

    def test_various(self):
        for items in self.items:
            q = furl.Query(items.original())
            assert q.params.allitems() == items.allitems()
            pairs = map(lambda pair: '%s=%s' % (pair[0], pair[1]),
                        self._quote_items(items))

            # encode() and __str__().
            assert str(q) == q.encode() == q.encode('&')

            # __nonzero__().
            if items.allitems():
                assert q
            else:
                assert not q

    def test_load(self):
        for items in self.items:
            q = furl.Query(items.original())
            for update in self.items:
                assert q.load(update) == q
                assert q.params.allitems() == update.allitems()

    def test_add(self):
        for items in self.items:
            q = furl.Query(items.original())
            runningsum = list(items.allitems())
            for itemupdate in self.items:
                assert q.add(itemupdate.original()) == q
                for item in itemupdate.iterallitems():
                    runningsum.append(item)
                assert q.params.allitems() == runningsum

    def test_set(self):
        for items in self.items:
            q = furl.Query(items.original())
            items_omd = omdict1D(items.allitems())
            for update in self.items:
                q.set(update)
                items_omd.updateall(update)
                assert q.params.allitems() == items_omd.allitems()

        # The examples.
        q = furl.Query({1: 1}).set([(1, None), (2, 2)])
        assert q.params.allitems() == [(1, None), (2, 2)]

        q = furl.Query({1: None, 2: None}).set([(1, 1), (2, 2), (1, 11)])
        assert q.params.allitems() == [(1, 1), (2, 2), (1, 11)]

        q = furl.Query({1: None}).set([(1, [1, 11, 111])])
        assert q.params.allitems() == [(1, 1), (1, 11), (1, 111)]

        # Further manual tests.
        q = furl.Query([(2, None), (3, None), (1, None)])
        q.set([(1, [1, 11]), (2, 2), (3, [3, 33])])
        assert q.params.allitems() == [
            (2, 2), (3, 3), (1, 1), (1, 11), (3, 33)]

    def test_remove(self):
        for items in self.items:
            # Remove one key at a time.
            q = furl.Query(items.original())
            for key in dict(items.iterallitems()):
                assert key in q.params
                assert q.remove(key) == q
                assert key not in q.params

            # Remove multiple keys at a time (in this case all of them).
            q = furl.Query(items.original())
            if items.allitems():
                assert q.params
            allkeys = [key for key, value in items.allitems()]
            assert q.remove(allkeys) == q
            assert len(q.params) == 0

            # Remove the whole query string with True.
            q = furl.Query(items.original())
            if items.allitems():
                assert q.params
            assert q.remove(True) == q
            assert len(q.params) == 0

        # List of keys to remove.
        q = furl.Query([('a', '1'), ('b', '2'), ('b', '3'), ('a', '4')])
        q.remove(['a', 'b'])
        assert not q.params.items()

        # List of items to remove.
        q = furl.Query([('a', '1'), ('b', '2'), ('b', '3'), ('a', '4')])
        q.remove([('a', '1'), ('b', '3')])
        assert q.params.allitems() == [('b', '2'), ('a', '4')]

        # Dictionary of items to remove.
        q = furl.Query([('a', '1'), ('b', '2'), ('b', '3'), ('a', '4')])
        q.remove({'b': '3', 'a': '1'})
        assert q.params.allitems() == [('b', '2'), ('a', '4')]

        # Multivalue dictionary of items to remove.
        q = furl.Query([('a', '1'), ('b', '2'), ('b', '3'), ('a', '4')])
        omd = omdict1D([('a', '4'), ('b', '3'), ('b', '2')])
        q.remove(omd)
        assert q.params.allitems() == [('a', '1')]

    def test_params(self):
        # Basics.
        q = furl.Query('a=a&b=b')
        assert q.params == {'a': 'a', 'b': 'b'}
        q.params['sup'] = 'sup'
        assert q.params == {'a': 'a', 'b': 'b', 'sup': 'sup'}
        del q.params['a']
        assert q.params == {'b': 'b', 'sup': 'sup'}
        q.params['b'] = 'BLROP'
        assert q.params == {'b': 'BLROP', 'sup': 'sup'}

        # Blanks keys and values are kept.
        q = furl.Query('=')
        assert q.params == {'': ''} and str(q) == '='
        q = furl.Query('=&=')
        assert q.params.allitems() == [('', ''), ('', '')] and str(q) == '=&='
        q = furl.Query('a=&=b')
        assert q.params == {'a': '', '': 'b'} and str(q) == 'a=&=b'

        # ';' is a valid query delimeter.
        q = furl.Query('=;=')
        assert q.params.allitems() == [('', ''), ('', '')] and str(q) == '=&='
        q = furl.Query('a=a;b=b;c=')
        assert q.params == {
            'a': 'a', 'b': 'b', 'c': ''} and str(q) == 'a=a&b=b&c='

        # Non-string parameters are coerced to strings in the final
        # query string.
        q.params.clear()
        q.params[99] = 99
        q.params[None] = -1
        q.params['int'] = 1
        q.params['float'] = 0.39393
        assert str(q) == '99=99&None=-1&int=1&float=0.39393'

        # Spaces are encoded as '+'s. '+'s are encoded as '%2B'.
        q.params.clear()
        q.params['s s'] = 's s'
        q.params['p+p'] = 'p+p'
        assert str(q) == 's+s=s+s&p%2Bp=p%2Bp'

        # Params is an omdict (ordered multivalue dictionary).
        q.params.clear()
        q.params.add('1', '1').set('2', '4').add('1', '11').addlist(
            3, [3, 3, '3'])
        assert q.params.getlist('1') == ['1', '11'] and q.params['1'] == '1'
        assert q.params.getlist(3) == [3, 3, '3']

        # Assign various things to Query.params and make sure
        # Query.params is reinitialized, not replaced.
        for items in self.items:
            q.params = items.original()
            assert isinstance(q.params, omdict1D)

            pairs = izip(q.params.iterallitems(), items.iterallitems())
            for item1, item2 in pairs:
                assert item1 == item2

        # Value of '' -> '?param='. Value of None -> '?param'.
        q = furl.Query('slrp')
        assert str(q) == 'slrp' and q.params['slrp'] is None
        q = furl.Query('slrp=')
        assert str(q) == 'slrp=' and q.params['slrp'] == ''
        q = furl.Query('prp=&slrp')
        assert q.params['prp'] == '' and q.params['slrp'] is None
        q.params['slrp'] = ''
        assert str(q) == 'prp=&slrp=' and q.params['slrp'] == ''

    def test_unicode(self):
        key, value = u'Восход', u'testä'
        key_encoded = urllib.quote_plus(key.encode('utf8'))
        value_encoded = urllib.quote_plus(value.encode('utf8'))

        q = furl.Query(u'%s=%s' % (key, value))
        assert q.params[key] == value
        assert str(q) == '%s=%s' % (key_encoded, value_encoded)

        q = furl.Query()
        q.params[key] = value
        assert q.params[key] == value
        assert str(q) == '%s=%s' % (key_encoded, value_encoded)

    def _quote_items(self, items):
        # Calculate the expected querystring with proper query encoding.
        #   Valid query key characters: "/?:@-._~!$'()*,;"
        #   Valid query value characters: "/?:@-._~!$'()*,;="
        allitems_quoted = []
        for key, value in items.iterallitems():
            pair = (urllib.quote_plus(str(key), "/?:@-._~!$'()*,;"),
                    urllib.quote_plus(str(value), "/?:@-._~!$'()*,;="))
            allitems_quoted.append(pair)
        return allitems_quoted


class TestQueryCompositionInterface(unittest.TestCase):

    def test_interface(self):
        class tester(furl.QueryCompositionInterface):

            def __init__(self):
                furl.QueryCompositionInterface.__init__(self)

            def __setattr__(self, attr, value):
                fqci = furl.QueryCompositionInterface
                if not fqci.__setattr__(self, attr, value):
                    object.__setattr__(self, attr, value)

        t = tester()
        assert isinstance(t.query, furl.Query)
        assert str(t.query) == ''

        t.query = 'a=a&s=s s'
        assert isinstance(t.query, furl.Query)
        assert str(t.query) == 'a=a&s=s+s'
        assert t.args == t.query.params == {'a': 'a', 's': 's s'}


class TestFragment(unittest.TestCase):

    def test_basics(self):
        f = furl.Fragment()
        assert str(f.path) == '' and str(f.query) == '' and str(f) == ''

        f.args['sup'] = 'foo'
        assert str(f) == 'sup=foo'
        f.path = 'yasup'
        assert str(f) == 'yasup?sup=foo'
        f.path = '/yasup'
        assert str(f) == '/yasup?sup=foo'
        assert str(f.query) == 'sup=foo'
        f.query.params['sup'] = 'kwlpumps'
        assert str(f) == '/yasup?sup=kwlpumps'
        f.query = ''
        assert str(f) == '/yasup'
        f.path = ''
        assert str(f) == ''
        f.args['no'] = 'dads'
        f.query.params['hi'] = 'gr8job'
        assert str(f) == 'no=dads&hi=gr8job'

    def test_load(self):
        comps = [('', '', {}),
                 ('?', '%3F', {}),
                 ('??a??', '%3F%3Fa%3F%3F', {}),
                 ('??a??=', '', {'?a??': ''}),
                 ('schtoot', 'schtoot', {}),
                 ('sch/toot/YOEP', 'sch/toot/YOEP', {}),
                 ('/sch/toot/YOEP', '/sch/toot/YOEP', {}),
                 ('schtoot?', 'schtoot%3F', {}),
                 ('schtoot?NOP', 'schtoot%3FNOP', {}),
                 ('schtoot?NOP=', 'schtoot', {'NOP': ''}),
                 ('schtoot?=PARNT', 'schtoot', {'': 'PARNT'}),
                 ('schtoot?NOP=PARNT', 'schtoot', {'NOP': 'PARNT'}),
                 ('dog?machine?yes', 'dog%3Fmachine%3Fyes', {}),
                 ('dog?machine=?yes', 'dog', {'machine': '?yes'}),
                 ('schtoot?a=a&hok%20sprm', 'schtoot',
                  {'a': 'a', 'hok sprm': ''}),
                 ('schtoot?a=a&hok sprm', 'schtoot',
                  {'a': 'a', 'hok sprm': ''}),
                 ('sch/toot?a=a&hok sprm', 'sch/toot',
                  {'a': 'a', 'hok sprm': ''}),
                 ('/sch/toot?a=a&hok sprm', '/sch/toot',
                  {'a': 'a', 'hok sprm': ''}),
                 ]

        for fragment, path, query in comps:
            f = furl.Fragment()
            f.load(fragment)
            assert str(f.path) == path
            assert f.query.params == query

    def test_add(self):
        f = furl.Fragment('')
        assert f is f.add(path='one two three', args={'a': 'a', 's': 's s'})
        assert str(f) == 'one%20two%20three?a=a&s=s+s'

        f = furl.Fragment('break?legs=broken')
        assert f is f.add(path='horse bones', args={'a': 'a', 's': 's s'})
        assert str(f) == 'break/horse%20bones?legs=broken&a=a&s=s+s'

    def test_set(self):
        f = furl.Fragment('asdf?lol=sup&foo=blorp')
        assert f is f.set(path='one two three', args={'a': 'a', 's': 's s'})
        assert str(f) == 'one%20two%20three?a=a&s=s+s'

        assert f is f.set(path='!', separator=False)
        assert f.separator is False
        assert str(f) == '!a=a&s=s+s'

    def test_remove(self):
        f = furl.Fragment('a/path/great/job?lol=sup&foo=blorp')
        assert f is f.remove(path='job', args=['lol'])
        assert str(f) == 'a/path/great/?foo=blorp'

        assert f is f.remove(path=['path', 'great'], args=['foo'])
        assert str(f) == 'a/path/great/'
        assert f is f.remove(path=['path', 'great', ''])
        assert str(f) == 'a/'

        assert f is f.remove(fragment=True)
        assert str(f) == ''

    def test_encoding(self):
        f = furl.Fragment()
        f.path = "/?:@-._~!$&'()*+,;="
        assert str(f) == "/?:@-._~!$&'()*+,;="
        f.query = {'a': 'a', 'b b': 'NOPE'}
        assert str(f) == "/%3F:@-._~!$&'()*+,;=?a=a&b+b=NOPE"
        f.separator = False
        assert str(f) == "/?:@-._~!$&'()*+,;=a=a&b+b=NOPE"

        f = furl.Fragment()
        f.path = "/?:@-._~!$&'()*+,;= ^`<>[]"
        assert str(f) == "/?:@-._~!$&'()*+,;=%20%5E%60%3C%3E%5B%5D"
        f.query = {'a': 'a', 'b b': 'NOPE'}
        assert str(
            f) == "/%3F:@-._~!$&'()*+,;=%20%5E%60%3C%3E%5B%5D?a=a&b+b=NOPE"
        f.separator = False
        assert str(f) == "/?:@-._~!$&'()*+,;=%20%5E%60%3C%3E%5B%5Da=a&b+b=NOPE"

        f = furl.furl()
        f.fragment = 'a?b?c?d?'
        assert f.url == '#a?b?c?d?'
        # TODO(grun): Once encoding has been fixed with URLPath and
        # FragmentPath, the below line should be:
        #
        #  assert str(f.fragment) == str(f.path) == 'a?b?c?d?'
        #
        assert str(f.fragment) == 'a?b?c?d?'

    def test_nonzero(self):
        f = furl.Fragment()
        assert not f

        f = furl.Fragment('')
        assert not f

        f = furl.Fragment('asdf')
        assert f

        f = furl.Fragment()
        f.path = 'sup'
        assert f

        f = furl.Fragment()
        f.query = 'a=a'
        assert f

        f = furl.Fragment()
        f.path = 'sup'
        f.query = 'a=a'
        assert f

        f = furl.Fragment()
        f.path = 'sup'
        f.query = 'a=a'
        f.separator = False
        assert f


class TestFragmentCompositionInterface(unittest.TestCase):

    def test_interface(self):
        class tester(furl.FragmentCompositionInterface):

            def __init__(self):
                furl.FragmentCompositionInterface.__init__(self)

            def __setattr__(self, attr, value):
                ffci = furl.FragmentCompositionInterface
                if not ffci.__setattr__(self, attr, value):
                    object.__setattr__(self, attr, value)

        t = tester()
        assert isinstance(t.fragment, furl.Fragment)
        assert isinstance(t.fragment.path, furl.Path)
        assert isinstance(t.fragment.query, furl.Query)
        assert str(t.fragment) == ''
        assert t.fragment.separator
        assert str(t.fragment.path) == ''
        assert str(t.fragment.query) == ''

        t.fragment = 'animal meats'
        assert isinstance(t.fragment, furl.Fragment)
        t.fragment.path = 'pump/dump'
        t.fragment.query = 'a=a&s=s+s'
        assert isinstance(t.fragment.path, furl.Path)
        assert isinstance(t.fragment.query, furl.Query)
        assert str(t.fragment.path) == 'pump/dump'
        assert t.fragment.path.segments == ['pump', 'dump']
        assert not t.fragment.path.isabsolute
        assert str(t.fragment.query) == 'a=a&s=s+s'
        assert t.fragment.args == t.fragment.query.params == {
            'a': 'a', 's': 's s'}


class TestFurl(unittest.TestCase):

    def setUp(self):
        # Don't hide duplicate Warnings - test for all of them.
        warnings.simplefilter("always")

    def _param(self, url, key, val):
        # Note: urlparse.urlsplit() doesn't separate the query from the
        # path for all schemes, only those schemes in the list
        # urlparse.uses_query. So, as a result of using
        # urlparse.urlsplit(), this little helper function only works
        # when provided urls whos schemes are also in
        # urlparse.uses_query.
        items = urlparse.parse_qsl(urlparse.urlsplit(url).query, True)
        return (key, val) in items

    def test_unicode(self):
        path = u'Восход'
        path_encoded = '%D0%92%D0%BE%D1%81%D1%85%D0%BE%D0%B4'

        key, value = u'testö', u'testä'
        key_encoded, value_encoded = 'test%C3%B6', 'test%C3%A4'

        base_url = u'http://pumps.ru'
        full_url = '%s/%s?%s=%s' % (base_url, path, key, value)
        full_url_encoded = '%s/%s?%s=%s' % (
            base_url, path_encoded, key_encoded, value_encoded)

        # Accept unicode without raising an exception.
        f = furl.furl(full_url)
        assert f.url == full_url_encoded

        # Accept unicode paths.
        f = furl.furl(base_url)
        f.path = path
        assert f.url == '%s/%s' % (base_url, path_encoded)

        # Accept unicode queries.
        f.args[key] = value
        assert f.args[key] == value  # Unicode keys and values aren't modified.
        assert not isinstance(f.url, unicode)  # URLs cannot contain unicode.
        f.path.segments = [path]
        assert f.path.segments == [path]  # Unicode segments aren't modified.
        assert f.url == full_url_encoded

    def test_scheme(self):
        assert furl.furl().scheme is None
        assert furl.furl('').scheme is None

        # Lowercase.
        assert furl.furl('/sup/').set(scheme='PrOtO').scheme == 'proto'

        # No scheme.
        for url in ['sup.txt', '/d/sup', '#flarg']:
            f = furl.furl(url)
            assert f.scheme is None and f.url == url

        # Protocol relative URLs.
        for url in ['//', '//sup.txt', '//arc.io/d/sup']:
            f = furl.furl(url)
            assert f.scheme == '' and f.url == url

        f = furl.furl('//sup.txt')
        assert f.scheme == ''
        f.scheme = None
        assert f.scheme is None and f.url == 'sup.txt'
        f.scheme = ''
        assert f.scheme == '' and f.url == '//sup.txt'

        # Schemes without slashes , like 'mailto:'.
        f = furl.furl('mailto:sup@sprp.ru')
        assert f.url == 'mailto:sup@sprp.ru'
        f = furl.furl('mailto://sup@sprp.ru')
        assert f.url == 'mailto:sup@sprp.ru'

        f = furl.furl('mailto:sproop:spraps@sprp.ru')
        assert f.scheme == 'mailto'
        assert f.username == 'sproop' and f.password == 'spraps'
        assert f.host == 'sprp.ru'

        f = furl.furl('mailto:')
        assert f.url == 'mailto:' and f.scheme == 'mailto'

    def test_username_and_password(self):
        # Empty usernames and passwords.
        for url in ['', 'http://www.pumps.com/']:
            f = furl.furl(url)
            assert f.username is None and f.password is None

        usernames = ['user', 'a-user_NAME$%^&09']
        passwords = ['pass', 'a-PASS_word$%^&09']
        baseurl = 'http://www.google.com/'

        # Username only.
        userurl = 'http://%s@www.google.com/'
        for username in usernames:
            f = furl.furl(userurl % username)
            assert f.username == username and f.password is None

            f = furl.furl(baseurl)
            f.username = username
            assert f.username == username and f.password is None
            assert f.url == userurl % username

            f = furl.furl(baseurl)
            f.set(username=username)
            assert f.username == username and f.password is None
            assert f.url == userurl % username

            f.remove(username=True)
            assert f.username is None and f.password is None
            assert f.url == baseurl

        # Password only.
        passurl = 'http://:%s@www.google.com/'
        for password in passwords:
            f = furl.furl(passurl % password)
            assert f.password == password and f.username is None

            f = furl.furl(baseurl)
            f.password = password
            assert f.password == password and f.username is None
            assert f.url == passurl % password

            f = furl.furl(baseurl)
            f.set(password=password)
            assert f.password == password and f.username is None
            assert f.url == passurl % password

            f.remove(password=True)
            assert not f.username and not f.password
            assert f.url == baseurl

        # Username and password.
        userpassurl = 'http://%s:%s@www.google.com/'
        for username in usernames:
            for password in passwords:
                f = furl.furl(userpassurl % (username, password))
                assert f.username == username and f.password == password

                f = furl.furl(baseurl)
                f.username = username
                f.password = password
                assert f.username == username and f.password == password
                assert f.url == userpassurl % (username, password)

                f = furl.furl(baseurl)
                f.set(username=username, password=password)
                assert f.username == username and f.password == password
                assert f.url == userpassurl % (username, password)

                f = furl.furl(baseurl)
                f.remove(username=True, password=True)
                assert not f.username and not f.password
                assert f.url == baseurl

        # Username and password in the network location string.
        f = furl.furl()
        f.netloc = 'user@domain.com'
        assert f.username == 'user' and not f.password
        assert f.netloc == 'user@domain.com'

        f = furl.furl()
        f.netloc = ':pass@domain.com'
        assert not f.username and f.password == 'pass'
        assert f.netloc == ':pass@domain.com'

        f = furl.furl()
        f.netloc = 'user:pass@domain.com'
        assert f.username == 'user' and f.password == 'pass'
        assert f.netloc == 'user:pass@domain.com'
        f = furl.furl()
        assert f.username is f.password is None
        f.username = 'uu'
        assert f.username == 'uu' and f.password is None and f.url == 'uu@'
        f.password = 'pp'
        assert f.username == 'uu' and f.password == 'pp' and f.url == 'uu:pp@'
        f.username = ''
        assert f.username == '' and f.password == 'pp' and f.url == ':pp@'
        f.password = ''
        assert f.username == f.password == '' and f.url == ':@'
        f.password = None
        assert f.username == '' and f.password is None and f.url == '@'
        f.username = None
        assert f.username is f.password is None and f.url == ''
        f.password = ''
        assert f.username is None and f.password == '' and f.url == ':@'

    def test_basics(self):
        url = 'hTtP://www.pumps.com/'
        f = furl.furl(url)
        assert f.scheme == 'http'
        assert f.netloc == 'www.pumps.com'
        assert f.host == 'www.pumps.com'
        assert f.port == 80
        assert str(f.path) == '/'
        assert str(f.query) == ''
        assert f.args == f.query.params == {}
        assert str(f.fragment) == ''
        assert f.url == str(f) == url.lower()
        assert f.url == furl.furl(f).url == furl.furl(f.url).url
        assert f is not f.copy() and f.url == f.copy().url

        url = 'HTTPS://wWw.YAHOO.cO.UK/one/two/three?a=a&b=b&m=m%26m#fragment'
        f = furl.furl(url)
        assert f.scheme == 'https'
        assert f.netloc == 'www.yahoo.co.uk'
        assert f.host == 'www.yahoo.co.uk'
        assert f.port == 443
        assert str(f.path) == '/one/two/three'
        assert str(f.query) == 'a=a&b=b&m=m%26m'
        assert f.args == f.query.params == {'a': 'a', 'b': 'b', 'm': 'm&m'}
        assert str(f.fragment) == 'fragment'
        assert f.url == str(f) == url.lower()
        assert f.url == furl.furl(f).url == furl.furl(f.url).url
        assert f is not f.copy() and f.url == f.copy().url

        url = 'sup://192.168.1.102:8080///one//a%20b////?s=kwl%20string#frag'
        f = furl.furl(url)
        assert f.scheme == 'sup'
        assert f.netloc == '192.168.1.102:8080'
        assert f.host == '192.168.1.102'
        assert f.port == 8080
        assert str(f.path) == '///one//a%20b////'
        assert str(f.query) == 's=kwl+string'
        assert f.args == f.query.params == {'s': 'kwl string'}
        assert str(f.fragment) == 'frag'
        quoted = 'sup://192.168.1.102:8080///one//a%20b////?s=kwl+string#frag'
        assert f.url == str(f) == quoted
        assert f.url == furl.furl(f).url == furl.furl(f.url).url
        assert f is not f.copy() and f.url == f.copy().url

        # URL paths are optionally absolute if scheme and netloc are
        # empty.
        f = furl.furl()
        f.path.segments = ['pumps']
        assert str(f.path) == 'pumps'
        f.path = 'pumps'
        assert str(f.path) == 'pumps'

        # Fragment paths are optionally absolute, and not absolute by
        # default.
        f = furl.furl()
        f.fragment.path.segments = ['pumps']
        assert str(f.fragment.path) == 'pumps'
        f.fragment.path = 'pumps'
        assert str(f.fragment.path) == 'pumps'

        # URLs comprised of a netloc string only should not be prefixed
        # with '//', as-is the default behavior of
        # urlparse.urlunsplit().
        f = furl.furl()
        assert f.set(host='foo').url == 'foo'
        assert f.set(host='pumps.com').url == 'pumps.com'
        assert f.set(host='pumps.com', port=88).url == 'pumps.com:88'
        assert f.set(netloc='pumps.com:88').url == 'pumps.com:88'

    def test_basic_manipulation(self):
        f = furl.furl('http://www.pumps.com/')

        f.args.setdefault('foo', 'blah')
        assert str(f) == 'http://www.pumps.com/?foo=blah'
        f.query.params['foo'] = 'eep'
        assert str(f) == 'http://www.pumps.com/?foo=eep'

        f.port = 99
        assert str(f) == 'http://www.pumps.com:99/?foo=eep'

        f.netloc = 'www.yahoo.com:220'
        assert str(f) == 'http://www.yahoo.com:220/?foo=eep'

        f.netloc = 'www.yahoo.com'
        assert f.port == 80
        assert str(f) == 'http://www.yahoo.com/?foo=eep'

        f.scheme = 'sup'
        assert str(f) == 'sup://www.yahoo.com:80/?foo=eep'

        f.port = None
        assert str(f) == 'sup://www.yahoo.com/?foo=eep'

        f.fragment = 'sup'
        assert str(f) == 'sup://www.yahoo.com/?foo=eep#sup'

        f.path = 'hay supppp'
        assert str(f) == 'sup://www.yahoo.com/hay%20supppp?foo=eep#sup'

        f.args['space'] = '1 2'
        assert str(
            f) == 'sup://www.yahoo.com/hay%20supppp?foo=eep&space=1+2#sup'

        del f.args['foo']
        assert str(f) == 'sup://www.yahoo.com/hay%20supppp?space=1+2#sup'

        f.host = 'ohay.com'
        assert str(f) == 'sup://ohay.com/hay%20supppp?space=1+2#sup'

    def test_odd_urls(self):
        # Empty.
        f = furl.furl('')
        assert f.username is f.password is None
        assert f.scheme is f.host is f.port is f.netloc is None
        assert str(f.path) == ''
        assert str(f.query) == ''
        assert f.args == f.query.params == {}
        assert str(f.fragment) == ''
        assert f.url == ''

        # Keep in mind that ';' is a query delimeter for both the URL
        # query and the fragment query, resulting in the str(path),
        # str(query), and str(fragment) values below.
        url = (
            "sup://example.com/:@-._~!$&'()*+,=;:@-._~!$&'()*+,=:@-._~!$&'()*+"
            ",==?/?:@-._~!$'()*+,;=/?:@-._~!$'()*+,;==#/?:@-._~!$&'()*+,;=")
        pathstr = "/:@-._~!$&'()*+,=;:@-._~!$&'()*+,=:@-._~!$&'()*+,=="
        querystr = "/?:@-._~!$'()*+,=&=/?:@-._~!$'()*+,&=="
        fragmentstr = "/?:@-._~!$=&'()*+,=&="
        f = furl.furl(url)
        assert f.scheme == 'sup'
        assert f.host == 'example.com'
        assert f.port is None
        assert f.netloc == 'example.com'
        assert str(f.path) == pathstr
        assert str(f.query) == querystr
        assert str(f.fragment) == fragmentstr

        # Scheme only.
        f = furl.furl('sup://')
        assert f.scheme == 'sup'
        assert f.host is f.port is f.netloc is None
        assert str(f.path) == ''
        assert str(f.query) == ''
        assert f.args == f.query.params == {}
        assert str(f.fragment) == ''
        assert f.url == 'sup://' and f.netloc is None
        f.scheme = None
        assert f.scheme is None and f.netloc is None and f.url == ''
        f.scheme = ''
        assert f.scheme == '' and f.netloc is None and f.url == '//'

        # Host only.
        f = furl.furl().set(host='pumps.meat')
        assert f.url == 'pumps.meat' and f.netloc == f.host == 'pumps.meat'
        f.host = None
        assert f.url == '' and f.host is f.netloc is None
        f.host = ''
        assert f.url == '' and f.host == f.netloc == ''

        # Port only.
        f = furl.furl()
        f.port = 99
        assert f.url == ':99' and f.netloc is not None
        f.port = None
        assert f.url == '' and f.netloc is None

        # urlparse.urlsplit() treats the first two '//' as the beginning
        # of a netloc, even if the netloc is empty.
        f = furl.furl('////path')
        assert f.url == '//path' and str(f.path) == '//path'

        # TODO(grun): Test more odd urls.

    def test_hosts(self):
        # No host.
        url = 'http:///index.html'
        f = furl.furl(url)
        assert f.host is None and furl.furl(url).url == url

        # Valid IPv4 and IPv6 addresses.
        f = furl.furl('http://192.168.1.101')
        f = furl.furl('http://[2001:db8:85a3:8d3:1319:8a2e:370:7348]/')

        # Invalid IPv4 addresses shouldn't raise an exception because
        # urlparse.urlsplit() doesn't raise an exception on invalid IPv4
        # addresses.
        f = furl.furl('http://1.2.3.4.5.6/')

        # Invalid, but well-formed, IPv6 addresses shouldn't raise an
        # exception because urlparse.urlsplit() doesn't raise an
        # exception on invalid IPv6 addresses.
        furl.furl('http://[0:0:0:0:0:0:0:1:1:1:1:1:1:1:1:9999999999999]/')

        # Malformed IPv6 should raise an exception because
        # urlparse.urlsplit() raises an exception in Python v2.7+. In
        # Python <= 2.6, urlsplit() doesn't raise a ValueError on
        # malformed IPv6 addresses.
        if PYTHON_27PLUS:
            with self.assertRaises(ValueError):
                furl.furl('http://[0:0:0:0:0:0:0:1/')
            with self.assertRaises(ValueError):
                furl.furl('http://0:0:0:0:0:0:0:1]/')

    def test_netlocs(self):
        f = furl.furl('http://pumps.com/')
        netloc = '1.2.3.4.5.6:999'
        f.netloc = netloc
        assert f.netloc == netloc
        assert f.host == '1.2.3.4.5.6'
        assert f.port == 999

        netloc = '[0:0:0:0:0:0:0:1:1:1:1:1:1:1:1:9999999999999]:888'
        f.netloc = netloc
        assert f.netloc == netloc
        assert f.host == '[0:0:0:0:0:0:0:1:1:1:1:1:1:1:1:9999999999999]'
        assert f.port == 888

        # Malformed IPv6 should raise an exception because
        # urlparse.urlsplit() raises an exception in Python v2.7+.
        if PYTHON_27PLUS:
            with self.assertRaises(ValueError):
                f.netloc = '[0:0:0:0:0:0:0:1'
            with self.assertRaises(ValueError):
                f.netloc = '0:0:0:0:0:0:0:1]'

        # Invalid ports.
        with self.assertRaises(ValueError):
            f.netloc = '[0:0:0:0:0:0:0:1]:alksdflasdfasdf'
        with self.assertRaises(ValueError):
            f.netloc = 'pump2pump.org:777777777777'

        # No side effects.
        assert f.host == '[0:0:0:0:0:0:0:1:1:1:1:1:1:1:1:9999999999999]'
        assert f.port == 888

    def test_ports(self):
        # Default port values.
        assert furl.furl('http://www.pumps.com/').port == 80
        assert furl.furl('https://www.pumps.com/').port == 443
        assert furl.furl('undefined://www.pumps.com/').port is None

        # Override default port values.
        assert furl.furl('http://www.pumps.com:9000/').port == 9000
        assert furl.furl('https://www.pumps.com:9000/').port == 9000
        assert furl.furl('undefined://www.pumps.com:9000/').port == 9000

        # Reset the port.
        f = furl.furl('http://www.pumps.com:9000/')
        f.port = None
        assert f.url == 'http://www.pumps.com/'
        assert f.port == 80

        f = furl.furl('undefined://www.pumps.com:9000/')
        f.port = None
        assert f.url == 'undefined://www.pumps.com/'
        assert f.port is None

        # Invalid port raises ValueError with no side effects.
        with self.assertRaises(ValueError):
            furl.furl('http://www.pumps.com:invalid/')

        url = 'http://www.pumps.com:400/'
        f = furl.furl(url)
        assert f.port == 400
        with self.assertRaises(ValueError):
            f.port = 'asdf'
        assert f.url == url
        f.port = 9999
        with self.assertRaises(ValueError):
            f.port = []
        with self.assertRaises(ValueError):
            f.port = -1
        with self.assertRaises(ValueError):
            f.port = 77777777777
        assert f.port == 9999
        assert f.url == 'http://www.pumps.com:9999/'

        self.assertRaises(f.set, port='asdf')

    def test_add(self):
        f = furl.furl('http://pumps.com/')

        assert f is f.add(args={'a': 'a', 'm': 'm&m'}, path='kwl jump',
                          fragment_path='1', fragment_args={'f': 'frp'})
        assert self._param(f.url, 'a', 'a')
        assert self._param(f.url, 'm', 'm&m')
        assert str(f.fragment) == '1?f=frp'
        assert str(f.path) == urlparse.urlsplit(f.url).path == '/kwl%20jump'

        assert f is f.add(path='dir', fragment_path='23', args={'b': 'b'},
                          fragment_args={'b': 'bewp'})
        assert self._param(f.url, 'a', 'a')
        assert self._param(f.url, 'm', 'm&m')
        assert self._param(f.url, 'b', 'b')
        assert str(f.path) == '/kwl%20jump/dir'
        assert str(f.fragment) == '1/23?f=frp&b=bewp'

        # Supplying both <args> and <query_params> should raise a
        # warning.
        with warnings.catch_warnings(True) as w1:
            f.add(args={'a': '1'}, query_params={'a': '2'})
            assert len(w1) == 1 and issubclass(w1[0].category, UserWarning)
            assert self._param(
                f.url, 'a', '1') and self._param(f.url, 'a', '2')
            params = f.args.allitems()
            assert params.index(('a', '1')) < params.index(('a', '2'))

    def test_set(self):
        f = furl.furl('http://pumps.com/kwl%20jump/dir')
        assert f is f.set(args={'no': 'nope'}, fragment='sup')
        assert 'a' not in f.args
        assert 'b' not in f.args
        assert f.url == 'http://pumps.com/kwl%20jump/dir?no=nope#sup'

        # No conflict warnings between <host>/<port> and <netloc>, or
        # <query> and <params>.
        assert f is f.set(args={'a': 'a a'}, path='path path/dir', port='999',
                          fragment='moresup', scheme='sup', host='host')
        assert str(f.path) == '/path%20path/dir'
        assert f.url == 'sup://host:999/path%20path/dir?a=a+a#moresup'

        # Path as a list of path segments to join.
        assert f is f.set(path=['d1', 'd2'])
        assert f.url == 'sup://host:999/d1/d2?a=a+a#moresup'
        assert f is f.add(path=['/d3/', '/d4/'])
        assert f.url == 'sup://host:999/d1/d2/%2Fd3%2F/%2Fd4%2F?a=a+a#moresup'

        # Set a lot of stuff (but avoid conflicts, which are tested
        # below).
        f.set(
            query_params={'k': 'k'}, fragment_path='no scrubs', scheme='morp',
            host='myhouse', port=69, path='j$j*m#n', fragment_args={'f': 'f'})
        assert f.url == 'morp://myhouse:69/j$j*m%23n?k=k#no%20scrubs?f=f'

        # No side effects.
        oldurl = f.url
        with self.assertRaises(ValueError):
            f.set(args={'a': 'a a'}, path='path path/dir', port='INVALID_PORT',
                  fragment='moresup', scheme='sup', host='host')
        assert f.url == oldurl
        with warnings.catch_warnings(True) as w1:
            self.assertRaises(
                ValueError, f.set, netloc='nope.com:99', port='NOPE')
            assert len(w1) == 1 and issubclass(w1[0].category, UserWarning)
        assert f.url == oldurl

        # Separator isn't reset with set().
        f = furl.Fragment()
        f.separator = False
        f.set(path='flush', args={'dad': 'nope'})
        assert str(f) == 'flushdad=nope'

        # Test warnings for potentially overlapping parameters.
        f = furl.furl('http://pumps.com')
        warnings.simplefilter("always")

        # Host, port, and netloc overlap - host and port take
        # precedence.
        with warnings.catch_warnings(True) as w1:
            f.set(netloc='dumps.com:99', host='ohay.com')
            assert len(w1) == 1 and issubclass(w1[0].category, UserWarning)
            f.host == 'ohay.com'
            f.port == 99
        with warnings.catch_warnings(True) as w2:
            f.set(netloc='dumps.com:99', port=88)
            assert len(w2) == 1 and issubclass(w2[0].category, UserWarning)
            f.port == 88
        with warnings.catch_warnings(True) as w3:
            f.set(netloc='dumps.com:99', host='ohay.com', port=88)
            assert len(w3) == 1 and issubclass(w3[0].category, UserWarning)

        # Query, args, and query_params overlap - args and query_params
        # take precedence.
        with warnings.catch_warnings(True) as w4:
            f.set(query='yosup', args={'a': 'a', 'b': 'b'})
            assert len(w4) == 1 and issubclass(w4[0].category, UserWarning)
            assert self._param(f.url, 'a', 'a')
            assert self._param(f.url, 'b', 'b')
        with warnings.catch_warnings(True) as w5:
            f.set(query='yosup', query_params={'a': 'a', 'b': 'b'})
            assert len(w5) == 1 and issubclass(w5[0].category, UserWarning)
            assert self._param(f.url, 'a', 'a')
            assert self._param(f.url, 'b', 'b')
        with warnings.catch_warnings(True) as w6:
            f.set(args={'a': 'a', 'b': 'b'}, query_params={'c': 'c', 'd': 'd'})
            assert len(w6) == 1 and issubclass(w6[0].category, UserWarning)
            assert self._param(f.url, 'c', 'c')
            assert self._param(f.url, 'd', 'd')

        # Fragment, fragment_path, fragment_args, and fragment_separator
        # overlap - fragment_separator, fragment_path, and fragment_args
        # take precedence.
        with warnings.catch_warnings(True) as w7:
            f.set(fragment='hi', fragment_path='!', fragment_args={'a': 'a'},
                  fragment_separator=False)
            assert len(w7) == 1 and issubclass(w7[0].category, UserWarning)
            assert str(f.fragment) == '!a=a'
        with warnings.catch_warnings(True) as w8:
            f.set(fragment='hi', fragment_path='bye')
            assert len(w8) == 1 and issubclass(w8[0].category, UserWarning)
            assert str(f.fragment) == 'bye'
        with warnings.catch_warnings(True) as w9:
            f.set(fragment='hi', fragment_args={'a': 'a'})
            assert len(w9) == 1 and issubclass(w9[0].category, UserWarning)
            assert str(f.fragment) == 'hia=a'
        with warnings.catch_warnings(True) as w10:
            f.set(fragment='!?a=a', fragment_separator=False)
            assert len(w10) == 1 and issubclass(w10[0].category, UserWarning)
            assert str(f.fragment) == '!a=a'

    def test_remove(self):
        url = ('http://u:p@host:69/a/big/path/?a=a&b=b&s=s+s#a frag?with=args'
               '&a=a')
        f = furl.furl(url)

        # Remove without parameters removes nothing.
        assert f.url == f.remove().url

        # username, password, and port must be True.
        assert f == f.copy().remove(
            username='nope', password='nope', port='nope')

        # Basics.
        assert f is f.remove(fragment=True, args=['a', 'b'], path='path/',
                             username=True, password=True, port=True)
        assert f.url == 'http://host/a/big/?s=s+s'

        # No errors are thrown when removing URL components that don't exist.
        f = furl.furl(url)
        assert f is f.remove(fragment_path=['asdf'], fragment_args=['asdf'],
                             args=['asdf'], path=['ppp', 'ump'])
        assert self._param(f.url, 'a', 'a')
        assert self._param(f.url, 'b', 'b')
        assert self._param(f.url, 's', 's s')
        assert str(f.path) == '/a/big/path/'
        assert str(f.fragment.path) == 'a%20frag'
        assert f.fragment.args == {'a': 'a', 'with': 'args'}

        # Path as a list of paths to join before removing.
        assert f is f.remove(fragment_path='a frag', fragment_args=['a'],
                             query_params=['a', 'b'], path=['big', 'path', ''],
                             port=True)
        assert f.url == 'http://u:p@host/a/?s=s+s#with=args'

        assert f is f.remove(
            path=True, query=True, fragment=True, username=True,
            password=True)
        assert f.url == 'http://host'

    def test_join(self):
        empty_tests = ['', '/meat', '/meat/pump?a=a&b=b#fragsup',
                       'sup://www.pumps.org/brg/pap/mrf?a=b&c=d#frag?sup', ]
        run_tests = [
            # Join full urls.
            ('unknown://www.yahoo.com', 'unknown://www.yahoo.com'),
            ('unknown://www.yahoo.com?one=two&three=four',
             'unknown://www.yahoo.com?one=two&three=four'),
            ('unknown://www.yahoo.com/new/url/?one=two#blrp',
             'unknown://www.yahoo.com/new/url/?one=two#blrp'),

            # Absolute paths ('/foo').
            ('/pump', 'unknown://www.yahoo.com/pump'),
            ('/pump/2/dump', 'unknown://www.yahoo.com/pump/2/dump'),
            ('/pump/2/dump/', 'unknown://www.yahoo.com/pump/2/dump/'),

            # Relative paths ('../foo').
            ('./crit/', 'unknown://www.yahoo.com/pump/2/dump/crit/'),
            ('.././../././././srp', 'unknown://www.yahoo.com/pump/2/srp'),
            ('../././../nop', 'unknown://www.yahoo.com/nop'),

            # Query included.
            ('/erp/?one=two', 'unknown://www.yahoo.com/erp/?one=two'),
            ('morp?three=four', 'unknown://www.yahoo.com/erp/morp?three=four'),
            ('/root/pumps?five=six',
             'unknown://www.yahoo.com/root/pumps?five=six'),

            # Fragment included.
            ('#sup', 'unknown://www.yahoo.com/root/pumps?five=six#sup'),
            ('/reset?one=two#yepYEP',
             'unknown://www.yahoo.com/reset?one=two#yepYEP'),
            ('./slurm#uwantpump?', 'unknown://www.yahoo.com/slurm#uwantpump?')
        ]

        for test in empty_tests:
            f = furl.furl().join(test)
            assert f.url == test

        f = furl.furl('')
        for join, result in run_tests:
            assert f is f.join(join) and f.url == result

        # Join other furl object, which serialize to strings with str().
        f = furl.furl('')
        for join, result in run_tests:
            tojoin = furl.furl(join)
            assert f is f.join(tojoin) and f.url == result

    def test_equality(self):
        assert furl.furl() is not furl.furl() and furl.furl() == furl.furl()

        url = 'https://www.yahoo.co.uk/one/two/three?a=a&b=b&m=m%26m#fragment'
        assert furl.furl(url) == furl.furl(url)
        assert furl.furl(url).remove(path=True) != furl.furl(url)

    def test_urlsplit(self):
        # Without any delimeters like '://' or '/', the input should be
        # treated as a path.
        urls = ['sup', '127.0.0.1', 'www.google.com', '192.168.1.1:8000']
        for url in urls:
            assert isinstance(furl.urlsplit(url), urlparse.SplitResult)
            assert furl.urlsplit(url).path == urlparse.urlsplit(url).path

        # No changes to existing urlsplit() behavior for known schemes.
        url = 'http://www.pumps.com/'
        assert isinstance(furl.urlsplit(url), urlparse.SplitResult)
        assert furl.urlsplit(url) == urlparse.urlsplit(url)

        url = 'https://www.yahoo.co.uk/one/two/three?a=a&b=b&m=m%26m#fragment'
        assert isinstance(furl.urlsplit(url), urlparse.SplitResult)
        assert furl.urlsplit(url) == urlparse.urlsplit(url)

        # Properly split the query from the path for unknown schemes.
        url = 'unknown://www.yahoo.com?one=two&three=four'
        correct = ('unknown', 'www.yahoo.com', '', 'one=two&three=four', '')
        assert isinstance(furl.urlsplit(url), urlparse.SplitResult)
        assert furl.urlsplit(url) == correct

        url = 'sup://192.168.1.102:8080///one//two////?s=kwl%20string#frag'
        correct = ('sup', '192.168.1.102:8080', '///one//two////',
                   's=kwl%20string', 'frag')
        assert isinstance(furl.urlsplit(url), urlparse.SplitResult)
        assert furl.urlsplit(url) == correct

        url = 'crazyyy://www.yahoo.co.uk/one/two/three?a=a&b=b&m=m%26m#frag'
        correct = ('crazyyy', 'www.yahoo.co.uk', '/one/two/three',
                   'a=a&b=b&m=m%26m', 'frag')
        assert isinstance(furl.urlsplit(url), urlparse.SplitResult)
        assert furl.urlsplit(url) == correct

    def test_join_path_segments(self):
        jps = furl.join_path_segments

        # Empty.
        assert jps() == []
        assert jps([]) == []
        assert jps([], [], [], []) == []

        # Null strings.
        #   [''] means nothing, or an empty string, in the final path
        #     segments.
        #   ['', ''] is preserved as a slash in the final path segments.
        assert jps(['']) == []
        assert jps([''], ['']) == []
        assert jps([''], [''], ['']) == []
        assert jps([''], ['', '']) == ['', '']
        assert jps([''], [''], [''], ['']) == []
        assert jps(['', ''], ['', '']) == ['', '', '']
        assert jps(['', '', ''], ['', '']) == ['', '', '', '']
        assert jps(['', '', '', '', '', '']) == ['', '', '', '', '', '']
        assert jps(['', '', '', ''], ['', '']) == ['', '', '', '', '']
        assert jps(['', '', '', ''], ['', ''], ['']) == ['', '', '', '', '']
        assert jps(['', '', '', ''], ['', '', '']) == ['', '', '', '', '', '']

        # Basics.
        assert jps(['a']) == ['a']
        assert jps(['a', 'b']) == ['a', 'b']
        assert jps(['a'], ['b']) == ['a', 'b']
        assert jps(['1', '2', '3'], ['4', '5']) == ['1', '2', '3', '4', '5']

        # A trailing slash is preserved if no new slash is being added.
        #   ex: ['a', ''] + ['b'] == ['a', 'b'], or 'a/' + 'b' == 'a/b'
        assert jps(['a', ''], ['b']) == ['a', 'b']
        assert jps(['a'], [''], ['b']) == ['a', 'b']
        assert jps(['', 'a', ''], ['b']) == ['', 'a', 'b']
        assert jps(['', 'a', ''], ['b', '']) == ['', 'a', 'b', '']

        # A new slash is preserved if no trailing slash exists.
        #   ex: ['a'] + ['', 'b'] == ['a', 'b'], or 'a' + '/b' == 'a/b'
        assert jps(['a'], ['', 'b']) == ['a', 'b']
        assert jps(['a'], [''], ['b']) == ['a', 'b']
        assert jps(['', 'a'], ['', 'b']) == ['', 'a', 'b']
        assert jps(['', 'a', ''], ['b', '']) == ['', 'a', 'b', '']
        assert jps(['', 'a', ''], ['b'], ['']) == ['', 'a', 'b']
        assert jps(['', 'a', ''], ['b'], ['', '']) == ['', 'a', 'b', '']

        # A trailing slash and a new slash means that an extra slash
        # will exist afterwords.
        # ex: ['a', ''] + ['', 'b'] == ['a', '', 'b'], or 'a/' + '/b'
        #   == 'a//b'
        assert jps(['a', ''], ['', 'b']) == ['a', '', 'b']
        assert jps(['a'], [''], [''], ['b']) == ['a', 'b']
        assert jps(['', 'a', ''], ['', 'b']) == ['', 'a', '', 'b']
        assert jps(['', 'a'], [''], ['b', '']) == ['', 'a', 'b', '']
        assert jps(['', 'a'], [''], [''], ['b'], ['']) == ['', 'a', 'b']
        assert jps(['', 'a'], [''], [''], ['b'], ['', '']) == [
            '', 'a', 'b', '']
        assert jps(['', 'a'], ['', ''], ['b'], ['', '']) == ['', 'a', 'b', '']
        assert jps(['', 'a'], ['', '', ''], ['b']) == ['', 'a', '', 'b']
        assert jps(['', 'a', ''], ['', '', ''], ['', 'b']) == [
            '', 'a', '', '', '', 'b']
        assert jps(['a', '', ''], ['', '', ''], ['', 'b']) == [
            'a', '', '', '', '', 'b']

        # Path segments blocks without slashes, are combined as
        # expected.
        assert jps(['a', 'b'], ['c', 'd']) == ['a', 'b', 'c', 'd']
        assert jps(['a'], ['b'], ['c'], ['d']) == ['a', 'b', 'c', 'd']
        assert jps(['a', 'b', 'c', 'd'], ['e']) == ['a', 'b', 'c', 'd', 'e']
        assert jps(['a', 'b', 'c'], ['d'], ['e', 'f']) == [
            'a', 'b', 'c', 'd', 'e', 'f']

        # Putting it all together.
        assert jps(['a', '', 'b'], ['', 'c', 'd']) == ['a', '', 'b', 'c', 'd']
        assert jps(['a', '', 'b', ''], ['c', 'd']) == ['a', '', 'b', 'c', 'd']
        assert jps(['a', '', 'b', ''], ['c', 'd'], ['', 'e']) == [
            'a', '', 'b', 'c', 'd', 'e']
        assert jps(['', 'a', '', 'b', ''], ['', 'c']) == [
            '', 'a', '', 'b', '', 'c']
        assert jps(['', 'a', ''], ['', 'b', ''], ['', 'c']) == [
            '', 'a', '', 'b', '', 'c']

    def test_remove_path_segments(self):
        rps = furl.remove_path_segments

        # [''] represents a slash, equivalent to ['',''].

        # Basics.
        assert rps([], []) == []
        assert rps([''], ['']) == []
        assert rps(['a'], ['a']) == []
        assert rps(['a'], ['', 'a']) == ['a']
        assert rps(['a'], ['a', '']) == ['a']
        assert rps(['a'], ['', 'a', '']) == ['a']

        # Slash manipulation.
        assert rps([''], ['', '']) == []
        assert rps(['', ''], ['']) == []
        assert rps(['', ''], ['', '']) == []
        assert rps(['', 'a', 'b', 'c'], ['b', 'c']) == ['', 'a', '']
        assert rps(['', 'a', 'b', 'c'], ['', 'b', 'c']) == ['', 'a']
        assert rps(['', 'a', '', ''], ['']) == ['', 'a', '']
        assert rps(['', 'a', '', ''], ['', '']) == ['', 'a', '']
        assert rps(['', 'a', '', ''], ['', '', '']) == ['', 'a']

        # Remove a portion of the path from the tail of the original
        # path.
        assert rps(['', 'a', 'b', ''], ['', 'a', 'b', '']) == []
        assert rps(['', 'a', 'b', ''], ['a', 'b', '']) == ['', '']
        assert rps(['', 'a', 'b', ''], ['b', '']) == ['', 'a', '']
        assert rps(['', 'a', 'b', ''], ['', 'b', '']) == ['', 'a']
        assert rps(['', 'a', 'b', ''], ['', '']) == ['', 'a', 'b']
        assert rps(['', 'a', 'b', ''], ['']) == ['', 'a', 'b']
        assert rps(['', 'a', 'b', ''], []) == ['', 'a', 'b', '']

        assert rps(['', 'a', 'b', 'c'], ['', 'a', 'b', 'c']) == []
        assert rps(['', 'a', 'b', 'c'], ['a', 'b', 'c']) == ['', '']
        assert rps(['', 'a', 'b', 'c'], ['b', 'c']) == ['', 'a', '']
        assert rps(['', 'a', 'b', 'c'], ['', 'b', 'c']) == ['', 'a']
        assert rps(['', 'a', 'b', 'c'], ['c']) == ['', 'a', 'b', '']
        assert rps(['', 'a', 'b', 'c'], ['', 'c']) == ['', 'a', 'b']
        assert rps(['', 'a', 'b', 'c'], []) == ['', 'a', 'b', 'c']
        assert rps(['', 'a', 'b', 'c'], ['']) == ['', 'a', 'b', 'c']

        # Attempt to remove valid subsections, but subsections not from
        # the end of the original path.
        assert rps(['', 'a', 'b', 'c'], ['', 'a', 'b', '']) == [
            '', 'a', 'b', 'c']
        assert rps(['', 'a', 'b', 'c'], ['', 'a', 'b']) == ['', 'a', 'b', 'c']
        assert rps(['', 'a', 'b', 'c'], ['a', 'b']) == ['', 'a', 'b', 'c']
        assert rps(['', 'a', 'b', 'c'], ['a', 'b', '']) == ['', 'a', 'b', 'c']
        assert rps(['', 'a', 'b', 'c'], ['', 'a', 'b']) == ['', 'a', 'b', 'c']
        assert rps(['', 'a', 'b', 'c'], ['', 'a', 'b', '']) == [
            '', 'a', 'b', 'c']

        assert rps(['', 'a', 'b', 'c'], ['a']) == ['', 'a', 'b', 'c']
        assert rps(['', 'a', 'b', 'c'], ['', 'a']) == ['', 'a', 'b', 'c']
        assert rps(['', 'a', 'b', 'c'], ['a', '']) == ['', 'a', 'b', 'c']
        assert rps(['', 'a', 'b', 'c'], ['', 'a', '']) == ['', 'a', 'b', 'c']
        assert rps(['', 'a', 'b', 'c'], ['', 'a', '', '']) == [
            '', 'a', 'b', 'c']
        assert rps(['', 'a', 'b', 'c'], ['', '', 'a', '', '']) == [
            '', 'a', 'b', 'c']

        assert rps(['', 'a', 'b', 'c'], ['']) == ['', 'a', 'b', 'c']
        assert rps(['', 'a', 'b', 'c'], ['', '']) == ['', 'a', 'b', 'c']
        assert rps(['', 'a', 'b', 'c'], ['c', '']) == ['', 'a', 'b', 'c']

        # Attempt to remove segments longer than the original.
        assert rps([], ['a']) == []
        assert rps([], ['a', 'b']) == []
        assert rps(['a'], ['a', 'b']) == ['a']
        assert rps(['a', 'a'], ['a', 'a', 'a']) == ['a', 'a']

    def test_is_valid_port(self):
        valids = [1, 2, 3, 65535, 119, 2930]
        invalids = [-1, -9999, 0, 'a', [], (0), {1: 1}, 65536, 99999, {}, None]

        for port in valids:
            assert furl.is_valid_port(port)
        for port in invalids:
            assert not furl.is_valid_port(port)

    def test_is_valid_encoded_path_segment(segment):
        valids = [('abcdefghijklmnopqrstuvwxyz'
                   'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                   '0123456789' '-._~' ":@!$&'()*+,;="),
                  '', 'a', 'asdf', 'a%20a', '%3F', ]
        invalids = [' ^`<>[]"#/?', ' ', '%3Z', '/', '?']

        for valid in valids:
            assert furl.is_valid_encoded_path_segment(valid)
        for invalid in invalids:
            assert not furl.is_valid_encoded_path_segment(invalid)

    def test_is_valid_encoded_query_key(key):
        valids = [('abcdefghijklmnopqrstuvwxyz'
                   'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                   '0123456789' '-._~' ":@!$&'()*+,;" '/?'),
                  '', 'a', 'asdf', 'a%20a', '%3F', 'a+a', '/', '?', ]
        invalids = [' ^`<>[]"#', ' ', '%3Z', '#']

        for valid in valids:
            assert furl.is_valid_encoded_query_key(valid)
        for invalid in invalids:
            assert not furl.is_valid_encoded_query_key(invalid)

    def test_is_valid_encoded_query_value(value):
        valids = [('abcdefghijklmnopqrstuvwxyz'
                   'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                   '0123456789' '-._~' ":@!$&'()*+,;" '/?='),
                  '', 'a', 'asdf', 'a%20a', '%3F', 'a+a', '/', '?', '=']
        invalids = [' ^`<>[]"#', ' ', '%3Z', '#']

        for valid in valids:
            assert furl.is_valid_encoded_query_value(valid)
        for invalid in invalids:
            assert not furl.is_valid_encoded_query_value(invalid)

########NEW FILE########
__FILENAME__ = test_omdict1D
#
# furl - URL manipulation made simple.
#
# Arthur Grunseid
# grunseid.com
# grunseid@gmail.com
#
# License: Build Amazing Things (Unlicense)

import unittest
from itertools import izip, chain, product, permutations

from furl.omdict1D import omdict1D
from orderedmultidict import omdict

_unique = object()


class TestOmdict1D(unittest.TestCase):

    def setUp(self):
        self.key = 'sup'
        self.keys = [1, 2, -1, 'a', None, 0.9]
        self.values = [1, 2, None]
        self.valuelists = [[], [1], [1, 2, 3], [None, None, 1]]

    def test_update_updateall(self):
        data, omd1, omd2 = omdict(), omdict1D(), omdict1D()

        # All permutations of (self.keys, self.values) and (self.keys,
        # self.valuelists).
        allitems = chain(product(self.keys, self.values),
                         product(self.keys, self.valuelists))

        # All updates of length one item, two items, and three items.
        iterators = [permutations(allitems, 1),
                     permutations(allitems, 2),
                     permutations(allitems, 3),
                     permutations(allitems, 4),
                     ]

        for iterator in iterators:
            for update in iterator:
                data.update(update)
                omd1.update(update)
                omd2.updateall(update)
                for key in omd1.iterkeys():
                    if isinstance(data[key], list):
                        assert omd1[key] == data[key][-1]
                    else:
                        assert omd1[key] == data[key]
                for key in omd2.iterkeys():
                    data_values_unpacked = []
                    for value in data.getlist(key):
                        if isinstance(value, list):
                            data_values_unpacked.extend(value)
                        else:
                            data_values_unpacked.append(value)

                    assert omd2.getlist(key) == data_values_unpacked

        # Test different empty list value locations.
        update_tests = [([(1, None), (2, None)],
                         [(1, [1, 11]), (2, [2, 22])],
                         [(1, 11), (2, 22)]),
                        ([(1, None), (2, None)],
                         [(1, []), (1, 1), (1, 11)],
                         [(1, 11), (2, None)]),
                        ([(1, None), (2, None)],
                         [(1, 1), (1, []), (1, 11)],
                         [(1, 11), (2, None)]),
                        ([(1, None), (2, None)],
                         [(1, 1), (1, 11), (1, [])],
                         [(2, None)]),
                        ]
        for init, update, result in update_tests:
            omd = omdict1D(init)
            omd.update(update)
            assert omd.allitems() == result

        updateall_tests = [([(1, None), (2, None)],
                            [(1, [1, 11]), (2, [2, 22])],
                            [(1, 1), (2, 2), (1, 11), (2, 22)]),
                           ([(1, None), (2, None)],
                            [(1, []), (1, 1), (1, 11)],
                            [(1, 1), (2, None), (1, 11)]),
                           ([(1, None), (2, None)],
                            [(1, 1), (1, []), (1, 11)],
                            [(1, 11), (2, None)]),
                           ([(1, None), (2, None)],
                            [(1, 1), (1, 11), (1, [])],
                            [(2, None)]),
                           ]
        for init, update, result in updateall_tests:
            omd = omdict1D(init)
            omd.updateall(update)
            assert omd.allitems() == result

    def test_add(self):
        runningsum = []
        omd = omdict1D()
        for valuelist in self.valuelists:
            runningsum += valuelist
            if valuelist:
                assert omd.add(self.key, valuelist) == omd
                assert omd[self.key] == omd.get(self.key) == runningsum[0]
                assert omd.getlist(self.key) == runningsum
            else:
                assert self.key not in omd

        runningsum = []
        omd = omdict1D()
        for value in self.values:
            runningsum += [value]
            assert omd.add(self.key, value) == omd
            assert omd[self.key] == omd.get(self.key) == runningsum[0]
            assert omd.getlist(self.key) == runningsum

        # Empty list of values adds nothing.
        assert _unique not in omd
        assert omd.add(_unique, []) == omd
        assert _unique not in omd

    def test_set(self):
        omd1, omd2, omd3 = omdict1D(), omdict1D(), omdict1D()

        for valuelist in self.valuelists:
            omd1[self.key] = valuelist
            assert omd2.set(self.key, valuelist) == omd2
            assert omd3.setlist(self.key, valuelist) == omd3
            assert omd1 == omd2 == omd3 and omd1.getlist(self.key) == valuelist

        # Empty list of values deletes that key and all its values,
        # equivalent to del omd[somekey].
        omd = omdict1D()
        assert _unique not in omd
        omd.set(_unique, [])
        assert omd == omd
        assert _unique not in omd

        omd.set(_unique, [1, 2, 3])
        assert omd.getlist(_unique) == [1, 2, 3]
        omd.set(_unique, [])
        assert _unique not in omd

    def test_setitem(self):
        omd = omdict1D()
        for value, valuelist in izip(self.values, self.valuelists):
            if valuelist:
                omd[self.key] = valuelist
                assert omd[self.key] == omd.get(self.key) == valuelist[0]
                assert omd.getlist(self.key) == valuelist
            else:
                assert self.key not in omd

            omd[self.key] = value
            assert omd[self.key] == omd.get(self.key) == value
            assert omd.getlist(self.key) == [value]

        # Empty list of values deletes that key and all its values,
        # equivalent to del omd[somekey].
        omd = omdict1D()
        assert _unique not in omd
        omd[_unique] = []
        assert omd == omd
        assert _unique not in omd

        omd[_unique] = [1, 2, 3]
        assert omd.getlist(_unique) == [1, 2, 3]
        omd[_unique] = []
        assert _unique not in omd

########NEW FILE########
