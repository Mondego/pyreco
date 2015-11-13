__FILENAME__ = add_custom_css
# Makes Sphinx create a <link> to feedparser.css in the HTML output
def setup(app):
    app.add_stylesheet('feedparser.css')

########NEW FILE########
__FILENAME__ = conf
# project information
project = u'feedparser'
copyright = u'2004-2008 Mark Pilgrim, 2010-2013 Kurt McKee'
version = u'5.1.3'
release = u'5.1.3'
language = u'en'

# documentation options
master_doc = 'index'
exclude_patterns = ['_build']

# use a custom extension to make Sphinx add a <link> to feedparser.css
import sys, os.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
extensions = ['add_custom_css']

# customize the html
# files in html_static_path will be copied into _static/ when compiled
html_static_path = ['_static']

########NEW FILE########
__FILENAME__ = feedparser
"""Universal feed parser

Handles RSS 0.9x, RSS 1.0, RSS 2.0, CDF, Atom 0.3, and Atom 1.0 feeds

Visit https://code.google.com/p/feedparser/ for the latest version
Visit http://packages.python.org/feedparser/ for the latest documentation

Required: Python 2.4 or later
Recommended: iconv_codec <http://cjkpython.i18n.org/>
"""

__version__ = "5.1.3"
__license__ = """
Copyright (c) 2010-2013 Kurt McKee <contactme@kurtmckee.org>
Copyright (c) 2002-2008 Mark Pilgrim
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 'AS IS'
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE."""
__author__ = "Mark Pilgrim <http://diveintomark.org/>"
__contributors__ = ["Jason Diamond <http://injektilo.org/>",
                    "John Beimler <http://john.beimler.org/>",
                    "Fazal Majid <http://www.majid.info/mylos/weblog/>",
                    "Aaron Swartz <http://aaronsw.com/>",
                    "Kevin Marks <http://epeus.blogspot.com/>",
                    "Sam Ruby <http://intertwingly.net/>",
                    "Ade Oshineye <http://blog.oshineye.com/>",
                    "Martin Pool <http://sourcefrog.net/>",
                    "Kurt McKee <http://kurtmckee.org/>",
                    "Bernd Schlapsi <https://github.com/brot>",]

# HTTP "User-Agent" header to send to servers when downloading feeds.
# If you are embedding feedparser in a larger application, you should
# change this to your application name and URL.
USER_AGENT = "UniversalFeedParser/%s +https://code.google.com/p/feedparser/" % __version__

# HTTP "Accept" header to send to servers when downloading feeds.  If you don't
# want to send an Accept header, set this to None.
ACCEPT_HEADER = "application/atom+xml,application/rdf+xml,application/rss+xml,application/x-netcdf,application/xml;q=0.9,text/xml;q=0.2,*/*;q=0.1"

# List of preferred XML parsers, by SAX driver name.  These will be tried first,
# but if they're not installed, Python will keep searching through its own list
# of pre-installed parsers until it finds one that supports everything we need.
PREFERRED_XML_PARSERS = ["drv_libxml2"]

# If you want feedparser to automatically resolve all relative URIs, set this
# to 1.
RESOLVE_RELATIVE_URIS = 1

# If you want feedparser to automatically sanitize all potentially unsafe
# HTML content, set this to 1.
SANITIZE_HTML = 1

# ---------- Python 3 modules (make it work if possible) ----------
try:
    import rfc822
except ImportError:
    from email import _parseaddr as rfc822

try:
    # Python 3.1 introduces bytes.maketrans and simultaneously
    # deprecates string.maketrans; use bytes.maketrans if possible
    _maketrans = bytes.maketrans
except (NameError, AttributeError):
    import string
    _maketrans = string.maketrans

# base64 support for Atom feeds that contain embedded binary data
try:
    import base64, binascii
except ImportError:
    base64 = binascii = None
else:
    # Python 3.1 deprecates decodestring in favor of decodebytes
    _base64decode = getattr(base64, 'decodebytes', base64.decodestring)

# _s2bytes: convert a UTF-8 str to bytes if the interpreter is Python 3
# _l2bytes: convert a list of ints to bytes if the interpreter is Python 3
try:
    if bytes is str:
        # In Python 2.5 and below, bytes doesn't exist (NameError)
        # In Python 2.6 and above, bytes and str are the same type
        raise NameError
except NameError:
    # Python 2
    def _s2bytes(s):
        return s
    def _l2bytes(l):
        return ''.join(map(chr, l))
else:
    # Python 3
    def _s2bytes(s):
        return bytes(s, 'utf8')
    def _l2bytes(l):
        return bytes(l)

# If you want feedparser to allow all URL schemes, set this to ()
# List culled from Python's urlparse documentation at:
#   http://docs.python.org/library/urlparse.html
# as well as from "URI scheme" at Wikipedia:
#   https://secure.wikimedia.org/wikipedia/en/wiki/URI_scheme
# Many more will likely need to be added!
ACCEPTABLE_URI_SCHEMES = (
    'file', 'ftp', 'gopher', 'h323', 'hdl', 'http', 'https', 'imap', 'magnet',
    'mailto', 'mms', 'news', 'nntp', 'prospero', 'rsync', 'rtsp', 'rtspu',
    'sftp', 'shttp', 'sip', 'sips', 'snews', 'svn', 'svn+ssh', 'telnet',
    'wais',
    # Additional common-but-unofficial schemes
    'aim', 'callto', 'cvs', 'facetime', 'feed', 'git', 'gtalk', 'irc', 'ircs',
    'irc6', 'itms', 'mms', 'msnim', 'skype', 'ssh', 'smb', 'svn', 'ymsg',
)
#ACCEPTABLE_URI_SCHEMES = ()

# ---------- required modules (should come with any Python distribution) ----------
import cgi
import codecs
import copy
import datetime
import itertools
import re
import struct
import time
import types
import urllib
import urllib2
import urlparse
import warnings

from htmlentitydefs import name2codepoint, codepoint2name, entitydefs

try:
    from io import BytesIO as _StringIO
except ImportError:
    try:
        from cStringIO import StringIO as _StringIO
    except ImportError:
        from StringIO import StringIO as _StringIO

# ---------- optional modules (feedparser will work without these, but with reduced functionality) ----------

# gzip is included with most Python distributions, but may not be available if you compiled your own
try:
    import gzip
except ImportError:
    gzip = None
try:
    import zlib
except ImportError:
    zlib = None

# If a real XML parser is available, feedparser will attempt to use it.  feedparser has
# been tested with the built-in SAX parser and libxml2.  On platforms where the
# Python distribution does not come with an XML parser (such as Mac OS X 10.2 and some
# versions of FreeBSD), feedparser will quietly fall back on regex-based parsing.
try:
    import xml.sax
    from xml.sax.saxutils import escape as _xmlescape
except ImportError:
    _XML_AVAILABLE = 0
    def _xmlescape(data,entities={}):
        data = data.replace('&', '&amp;')
        data = data.replace('>', '&gt;')
        data = data.replace('<', '&lt;')
        for char, entity in entities:
            data = data.replace(char, entity)
        return data
else:
    try:
        xml.sax.make_parser(PREFERRED_XML_PARSERS) # test for valid parsers
    except xml.sax.SAXReaderNotAvailable:
        _XML_AVAILABLE = 0
    else:
        _XML_AVAILABLE = 1

# sgmllib is not available by default in Python 3; if the end user doesn't have
# it available then we'll lose illformed XML parsing and content santizing
try:
    import sgmllib
except ImportError:
    # This is probably Python 3, which doesn't include sgmllib anymore
    _SGML_AVAILABLE = 0

    # Mock sgmllib enough to allow subclassing later on
    class sgmllib(object):
        class SGMLParser(object):
            def goahead(self, i):
                pass
            def parse_starttag(self, i):
                pass
else:
    _SGML_AVAILABLE = 1

    # sgmllib defines a number of module-level regular expressions that are
    # insufficient for the XML parsing feedparser needs. Rather than modify
    # the variables directly in sgmllib, they're defined here using the same
    # names, and the compiled code objects of several sgmllib.SGMLParser
    # methods are copied into _BaseHTMLProcessor so that they execute in
    # feedparser's scope instead of sgmllib's scope.
    charref = re.compile('&#(\d+|[xX][0-9a-fA-F]+);')
    tagfind = re.compile('[a-zA-Z][-_.:a-zA-Z0-9]*')
    attrfind = re.compile(
        r'\s*([a-zA-Z_][-:.a-zA-Z_0-9]*)[$]?(\s*=\s*'
        r'(\'[^\']*\'|"[^"]*"|[][\-a-zA-Z0-9./,:;+*%?!&$\(\)_#=~\'"@]*))?'
    )

    # Unfortunately, these must be copied over to prevent NameError exceptions
    entityref = sgmllib.entityref
    incomplete = sgmllib.incomplete
    interesting = sgmllib.interesting
    shorttag = sgmllib.shorttag
    shorttagopen = sgmllib.shorttagopen
    starttagopen = sgmllib.starttagopen

    class _EndBracketRegEx:
        def __init__(self):
            # Overriding the built-in sgmllib.endbracket regex allows the
            # parser to find angle brackets embedded in element attributes.
            self.endbracket = re.compile('''([^'"<>]|"[^"]*"(?=>|/|\s|\w+=)|'[^']*'(?=>|/|\s|\w+=))*(?=[<>])|.*?(?=[<>])''')
        def search(self, target, index=0):
            match = self.endbracket.match(target, index)
            if match is not None:
                # Returning a new object in the calling thread's context
                # resolves a thread-safety.
                return EndBracketMatch(match)
            return None
    class EndBracketMatch:
        def __init__(self, match):
            self.match = match
        def start(self, n):
            return self.match.end(n)
    endbracket = _EndBracketRegEx()


# iconv_codec provides support for more character encodings.
# It's available from http://cjkpython.i18n.org/
try:
    import iconv_codec
except ImportError:
    pass

# chardet library auto-detects character encodings
# Download from http://chardet.feedparser.org/
try:
    import chardet
except ImportError:
    chardet = None

# ---------- don't touch these ----------
class ThingsNobodyCaresAboutButMe(Exception): pass
class CharacterEncodingOverride(ThingsNobodyCaresAboutButMe): pass
class CharacterEncodingUnknown(ThingsNobodyCaresAboutButMe): pass
class NonXMLContentType(ThingsNobodyCaresAboutButMe): pass
class UndeclaredNamespace(Exception): pass

SUPPORTED_VERSIONS = {'': u'unknown',
                      'rss090': u'RSS 0.90',
                      'rss091n': u'RSS 0.91 (Netscape)',
                      'rss091u': u'RSS 0.91 (Userland)',
                      'rss092': u'RSS 0.92',
                      'rss093': u'RSS 0.93',
                      'rss094': u'RSS 0.94',
                      'rss20': u'RSS 2.0',
                      'rss10': u'RSS 1.0',
                      'rss': u'RSS (unknown version)',
                      'atom01': u'Atom 0.1',
                      'atom02': u'Atom 0.2',
                      'atom03': u'Atom 0.3',
                      'atom10': u'Atom 1.0',
                      'atom': u'Atom (unknown version)',
                      'cdf': u'CDF',
                      }

class FeedParserDict(dict):
    keymap = {'channel': 'feed',
              'items': 'entries',
              'guid': 'id',
              'date': 'updated',
              'date_parsed': 'updated_parsed',
              'description': ['summary', 'subtitle'],
              'description_detail': ['summary_detail', 'subtitle_detail'],
              'url': ['href'],
              'modified': 'updated',
              'modified_parsed': 'updated_parsed',
              'issued': 'published',
              'issued_parsed': 'published_parsed',
              'copyright': 'rights',
              'copyright_detail': 'rights_detail',
              'tagline': 'subtitle',
              'tagline_detail': 'subtitle_detail'}
    def __getitem__(self, key):
        if key == 'category':
            try:
                return dict.__getitem__(self, 'tags')[0]['term']
            except IndexError:
                raise KeyError, "object doesn't have key 'category'"
        elif key == 'enclosures':
            norel = lambda link: FeedParserDict([(name,value) for (name,value) in link.items() if name!='rel'])
            return [norel(link) for link in dict.__getitem__(self, 'links') if link['rel']==u'enclosure']
        elif key == 'license':
            for link in dict.__getitem__(self, 'links'):
                if link['rel']==u'license' and 'href' in link:
                    return link['href']
        elif key == 'updated':
            # Temporarily help developers out by keeping the old
            # broken behavior that was reported in issue 310.
            # This fix was proposed in issue 328.
            if not dict.__contains__(self, 'updated') and \
                dict.__contains__(self, 'published'):
                warnings.warn("To avoid breaking existing software while "
                    "fixing issue 310, a temporary mapping has been created "
                    "from `updated` to `published` if `updated` doesn't "
                    "exist. This fallback will be removed in a future version "
                    "of feedparser.", DeprecationWarning)
                return dict.__getitem__(self, 'published')
            return dict.__getitem__(self, 'updated')
        elif key == 'updated_parsed':
            if not dict.__contains__(self, 'updated_parsed') and \
                dict.__contains__(self, 'published_parsed'):
                warnings.warn("To avoid breaking existing software while "
                    "fixing issue 310, a temporary mapping has been created "
                    "from `updated_parsed` to `published_parsed` if "
                    "`updated_parsed` doesn't exist. This fallback will be "
                    "removed in a future version of feedparser.",
                    DeprecationWarning)
                return dict.__getitem__(self, 'published_parsed')
            return dict.__getitem__(self, 'updated_parsed')
        else:
            realkey = self.keymap.get(key, key)
            if isinstance(realkey, list):
                for k in realkey:
                    if dict.__contains__(self, k):
                        return dict.__getitem__(self, k)
            elif dict.__contains__(self, realkey):
                return dict.__getitem__(self, realkey)
        return dict.__getitem__(self, key)

    def __contains__(self, key):
        if key in ('updated', 'updated_parsed'):
            # Temporarily help developers out by keeping the old
            # broken behavior that was reported in issue 310.
            # This fix was proposed in issue 328.
            return dict.__contains__(self, key)
        try:
            self.__getitem__(key)
        except KeyError:
            return False
        else:
            return True

    has_key = __contains__

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def __setitem__(self, key, value):
        key = self.keymap.get(key, key)
        if isinstance(key, list):
            key = key[0]
        return dict.__setitem__(self, key, value)

    def setdefault(self, key, value):
        if key not in self:
            self[key] = value
            return value
        return self[key]

    def __getattr__(self, key):
        # __getattribute__() is called first; this will be called
        # only if an attribute was not already found
        try:
            return self.__getitem__(key)
        except KeyError:
            raise AttributeError, "object has no attribute '%s'" % key

    def __hash__(self):
        return id(self)

_cp1252 = {
    128: unichr(8364), # euro sign
    130: unichr(8218), # single low-9 quotation mark
    131: unichr( 402), # latin small letter f with hook
    132: unichr(8222), # double low-9 quotation mark
    133: unichr(8230), # horizontal ellipsis
    134: unichr(8224), # dagger
    135: unichr(8225), # double dagger
    136: unichr( 710), # modifier letter circumflex accent
    137: unichr(8240), # per mille sign
    138: unichr( 352), # latin capital letter s with caron
    139: unichr(8249), # single left-pointing angle quotation mark
    140: unichr( 338), # latin capital ligature oe
    142: unichr( 381), # latin capital letter z with caron
    145: unichr(8216), # left single quotation mark
    146: unichr(8217), # right single quotation mark
    147: unichr(8220), # left double quotation mark
    148: unichr(8221), # right double quotation mark
    149: unichr(8226), # bullet
    150: unichr(8211), # en dash
    151: unichr(8212), # em dash
    152: unichr( 732), # small tilde
    153: unichr(8482), # trade mark sign
    154: unichr( 353), # latin small letter s with caron
    155: unichr(8250), # single right-pointing angle quotation mark
    156: unichr( 339), # latin small ligature oe
    158: unichr( 382), # latin small letter z with caron
    159: unichr( 376), # latin capital letter y with diaeresis
}

_urifixer = re.compile('^([A-Za-z][A-Za-z0-9+-.]*://)(/*)(.*?)')
def _urljoin(base, uri):
    uri = _urifixer.sub(r'\1\3', uri)
    if not isinstance(uri, unicode):
        uri = uri.decode('utf-8', 'ignore')
    try:
        uri = urlparse.urljoin(base, uri)
    except ValueError:
        uri = u''
    if not isinstance(uri, unicode):
        return uri.decode('utf-8', 'ignore')
    return uri

class _FeedParserMixin:
    namespaces = {
        '': '',
        'http://backend.userland.com/rss': '',
        'http://blogs.law.harvard.edu/tech/rss': '',
        'http://purl.org/rss/1.0/': '',
        'http://my.netscape.com/rdf/simple/0.9/': '',
        'http://example.com/newformat#': '',
        'http://example.com/necho': '',
        'http://purl.org/echo/': '',
        'uri/of/echo/namespace#': '',
        'http://purl.org/pie/': '',
        'http://purl.org/atom/ns#': '',
        'http://www.w3.org/2005/Atom': '',
        'http://purl.org/rss/1.0/modules/rss091#': '',

        'http://webns.net/mvcb/':                                'admin',
        'http://purl.org/rss/1.0/modules/aggregation/':          'ag',
        'http://purl.org/rss/1.0/modules/annotate/':             'annotate',
        'http://media.tangent.org/rss/1.0/':                     'audio',
        'http://backend.userland.com/blogChannelModule':         'blogChannel',
        'http://web.resource.org/cc/':                           'cc',
        'http://backend.userland.com/creativeCommonsRssModule':  'creativeCommons',
        'http://purl.org/rss/1.0/modules/company':               'co',
        'http://purl.org/rss/1.0/modules/content/':              'content',
        'http://my.theinfo.org/changed/1.0/rss/':                'cp',
        'http://purl.org/dc/elements/1.1/':                      'dc',
        'http://purl.org/dc/terms/':                             'dcterms',
        'http://purl.org/rss/1.0/modules/email/':                'email',
        'http://purl.org/rss/1.0/modules/event/':                'ev',
        'http://rssnamespace.org/feedburner/ext/1.0':            'feedburner',
        'http://freshmeat.net/rss/fm/':                          'fm',
        'http://xmlns.com/foaf/0.1/':                            'foaf',
        'http://www.w3.org/2003/01/geo/wgs84_pos#':              'geo',
        'http://www.georss.org/georss':                          'georss',
        'http://www.opengis.net/gml':                            'gml',
        'http://postneo.com/icbm/':                              'icbm',
        'http://purl.org/rss/1.0/modules/image/':                'image',
        'http://www.itunes.com/DTDs/PodCast-1.0.dtd':            'itunes',
        'http://example.com/DTDs/PodCast-1.0.dtd':               'itunes',
        'http://purl.org/rss/1.0/modules/link/':                 'l',
        'http://search.yahoo.com/mrss':                          'media',
        # Version 1.1.2 of the Media RSS spec added the trailing slash on the namespace
        'http://search.yahoo.com/mrss/':                         'media',
        'http://madskills.com/public/xml/rss/module/pingback/':  'pingback',
        'http://prismstandard.org/namespaces/1.2/basic/':        'prism',
        'http://www.w3.org/1999/02/22-rdf-syntax-ns#':           'rdf',
        'http://www.w3.org/2000/01/rdf-schema#':                 'rdfs',
        'http://purl.org/rss/1.0/modules/reference/':            'ref',
        'http://purl.org/rss/1.0/modules/richequiv/':            'reqv',
        'http://purl.org/rss/1.0/modules/search/':               'search',
        'http://purl.org/rss/1.0/modules/slash/':                'slash',
        'http://schemas.xmlsoap.org/soap/envelope/':             'soap',
        'http://purl.org/rss/1.0/modules/servicestatus/':        'ss',
        'http://hacks.benhammersley.com/rss/streaming/':         'str',
        'http://purl.org/rss/1.0/modules/subscription/':         'sub',
        'http://purl.org/rss/1.0/modules/syndication/':          'sy',
        'http://schemas.pocketsoap.com/rss/myDescModule/':       'szf',
        'http://purl.org/rss/1.0/modules/taxonomy/':             'taxo',
        'http://purl.org/rss/1.0/modules/threading/':            'thr',
        'http://purl.org/rss/1.0/modules/textinput/':            'ti',
        'http://madskills.com/public/xml/rss/module/trackback/': 'trackback',
        'http://wellformedweb.org/commentAPI/':                  'wfw',
        'http://purl.org/rss/1.0/modules/wiki/':                 'wiki',
        'http://www.w3.org/1999/xhtml':                          'xhtml',
        'http://www.w3.org/1999/xlink':                          'xlink',
        'http://www.w3.org/XML/1998/namespace':                  'xml',
        'http://podlove.org/simple-chapters':                    'psc',
    }
    _matchnamespaces = {}

    can_be_relative_uri = set(['link', 'id', 'wfw_comment', 'wfw_commentrss', 'docs', 'url', 'href', 'comments', 'icon', 'logo'])
    can_contain_relative_uris = set(['content', 'title', 'summary', 'info', 'tagline', 'subtitle', 'copyright', 'rights', 'description'])
    can_contain_dangerous_markup = set(['content', 'title', 'summary', 'info', 'tagline', 'subtitle', 'copyright', 'rights', 'description'])
    html_types = [u'text/html', u'application/xhtml+xml']

    def __init__(self, baseuri=None, baselang=None, encoding=u'utf-8'):
        if not self._matchnamespaces:
            for k, v in self.namespaces.items():
                self._matchnamespaces[k.lower()] = v
        self.feeddata = FeedParserDict() # feed-level data
        self.encoding = encoding # character encoding
        self.entries = [] # list of entry-level data
        self.version = u'' # feed type/version, see SUPPORTED_VERSIONS
        self.namespacesInUse = {} # dictionary of namespaces defined by the feed

        # the following are used internally to track state;
        # this is really out of control and should be refactored
        self.infeed = 0
        self.inentry = 0
        self.incontent = 0
        self.intextinput = 0
        self.inimage = 0
        self.inauthor = 0
        self.incontributor = 0
        self.inpublisher = 0
        self.insource = 0
        
        # georss
        self.ingeometry = 0
        
        self.sourcedata = FeedParserDict()
        self.contentparams = FeedParserDict()
        self._summaryKey = None
        self.namespacemap = {}
        self.elementstack = []
        self.basestack = []
        self.langstack = []
        self.baseuri = baseuri or u''
        self.lang = baselang or None
        self.svgOK = 0
        self.title_depth = -1
        self.depth = 0
        # psc_chapters_flag prevents multiple psc_chapters from being
        # captured in a single entry or item. The transition states are
        # None -> True -> False. psc_chapter elements will only be
        # captured while it is True.
        self.psc_chapters_flag = None
        if baselang:
            self.feeddata['language'] = baselang.replace('_','-')

        # A map of the following form:
        #     {
        #         object_that_value_is_set_on: {
        #             property_name: depth_of_node_property_was_extracted_from,
        #             other_property: depth_of_node_property_was_extracted_from,
        #         },
        #     }
        self.property_depth_map = {}

    def _normalize_attributes(self, kv):
        k = kv[0].lower()
        v = k in ('rel', 'type') and kv[1].lower() or kv[1]
        # the sgml parser doesn't handle entities in attributes, nor
        # does it pass the attribute values through as unicode, while
        # strict xml parsers do -- account for this difference
        if isinstance(self, _LooseFeedParser):
            v = v.replace('&amp;', '&')
            if not isinstance(v, unicode):
                v = v.decode('utf-8')
        return (k, v)

    def unknown_starttag(self, tag, attrs):
        # increment depth counter
        self.depth += 1

        # normalize attrs
        attrs = map(self._normalize_attributes, attrs)

        # track xml:base and xml:lang
        attrsD = dict(attrs)
        baseuri = attrsD.get('xml:base', attrsD.get('base')) or self.baseuri
        if not isinstance(baseuri, unicode):
            baseuri = baseuri.decode(self.encoding, 'ignore')
        # ensure that self.baseuri is always an absolute URI that
        # uses a whitelisted URI scheme (e.g. not `javscript:`)
        if self.baseuri:
            self.baseuri = _makeSafeAbsoluteURI(self.baseuri, baseuri) or self.baseuri
        else:
            self.baseuri = _urljoin(self.baseuri, baseuri)
        lang = attrsD.get('xml:lang', attrsD.get('lang'))
        if lang == '':
            # xml:lang could be explicitly set to '', we need to capture that
            lang = None
        elif lang is None:
            # if no xml:lang is specified, use parent lang
            lang = self.lang
        if lang:
            if tag in ('feed', 'rss', 'rdf:RDF'):
                self.feeddata['language'] = lang.replace('_','-')
        self.lang = lang
        self.basestack.append(self.baseuri)
        self.langstack.append(lang)

        # track namespaces
        for prefix, uri in attrs:
            if prefix.startswith('xmlns:'):
                self.trackNamespace(prefix[6:], uri)
            elif prefix == 'xmlns':
                self.trackNamespace(None, uri)

        # track inline content
        if self.incontent and not self.contentparams.get('type', u'xml').endswith(u'xml'):
            if tag in ('xhtml:div', 'div'):
                return # typepad does this 10/2007
            # element declared itself as escaped markup, but it isn't really
            self.contentparams['type'] = u'application/xhtml+xml'
        if self.incontent and self.contentparams.get('type') == u'application/xhtml+xml':
            if tag.find(':') <> -1:
                prefix, tag = tag.split(':', 1)
                namespace = self.namespacesInUse.get(prefix, '')
                if tag=='math' and namespace=='http://www.w3.org/1998/Math/MathML':
                    attrs.append(('xmlns',namespace))
                if tag=='svg' and namespace=='http://www.w3.org/2000/svg':
                    attrs.append(('xmlns',namespace))
            if tag == 'svg':
                self.svgOK += 1
            return self.handle_data('<%s%s>' % (tag, self.strattrs(attrs)), escape=0)

        # match namespaces
        if tag.find(':') <> -1:
            prefix, suffix = tag.split(':', 1)
        else:
            prefix, suffix = '', tag
        prefix = self.namespacemap.get(prefix, prefix)
        if prefix:
            prefix = prefix + '_'

        # special hack for better tracking of empty textinput/image elements in illformed feeds
        if (not prefix) and tag not in ('title', 'link', 'description', 'name'):
            self.intextinput = 0
        if (not prefix) and tag not in ('title', 'link', 'description', 'url', 'href', 'width', 'height'):
            self.inimage = 0

        # call special handler (if defined) or default handler
        methodname = '_start_' + prefix + suffix
        try:
            method = getattr(self, methodname)
            return method(attrsD)
        except AttributeError:
            # Since there's no handler or something has gone wrong we explicitly add the element and its attributes
            unknown_tag = prefix + suffix
            if len(attrsD) == 0:
                # No attributes so merge it into the encosing dictionary
                return self.push(unknown_tag, 1)
            else:
                # Has attributes so create it in its own dictionary
                context = self._getContext()
                context[unknown_tag] = attrsD

    def unknown_endtag(self, tag):
        # match namespaces
        if tag.find(':') <> -1:
            prefix, suffix = tag.split(':', 1)
        else:
            prefix, suffix = '', tag
        prefix = self.namespacemap.get(prefix, prefix)
        if prefix:
            prefix = prefix + '_'
        if suffix == 'svg' and self.svgOK:
            self.svgOK -= 1

        # call special handler (if defined) or default handler
        methodname = '_end_' + prefix + suffix
        try:
            if self.svgOK:
                raise AttributeError()
            method = getattr(self, methodname)
            method()
        except AttributeError:
            self.pop(prefix + suffix)

        # track inline content
        if self.incontent and not self.contentparams.get('type', u'xml').endswith(u'xml'):
            # element declared itself as escaped markup, but it isn't really
            if tag in ('xhtml:div', 'div'):
                return # typepad does this 10/2007
            self.contentparams['type'] = u'application/xhtml+xml'
        if self.incontent and self.contentparams.get('type') == u'application/xhtml+xml':
            tag = tag.split(':')[-1]
            self.handle_data('</%s>' % tag, escape=0)

        # track xml:base and xml:lang going out of scope
        if self.basestack:
            self.basestack.pop()
            if self.basestack and self.basestack[-1]:
                self.baseuri = self.basestack[-1]
        if self.langstack:
            self.langstack.pop()
            if self.langstack: # and (self.langstack[-1] is not None):
                self.lang = self.langstack[-1]

        self.depth -= 1

    def handle_charref(self, ref):
        # called for each character reference, e.g. for '&#160;', ref will be '160'
        if not self.elementstack:
            return
        ref = ref.lower()
        if ref in ('34', '38', '39', '60', '62', 'x22', 'x26', 'x27', 'x3c', 'x3e'):
            text = '&#%s;' % ref
        else:
            if ref[0] == 'x':
                c = int(ref[1:], 16)
            else:
                c = int(ref)
            text = unichr(c).encode('utf-8')
        self.elementstack[-1][2].append(text)

    def handle_entityref(self, ref):
        # called for each entity reference, e.g. for '&copy;', ref will be 'copy'
        if not self.elementstack:
            return
        if ref in ('lt', 'gt', 'quot', 'amp', 'apos'):
            text = '&%s;' % ref
        elif ref in self.entities:
            text = self.entities[ref]
            if text.startswith('&#') and text.endswith(';'):
                return self.handle_entityref(text)
        else:
            try:
                name2codepoint[ref]
            except KeyError:
                text = '&%s;' % ref
            else:
                text = unichr(name2codepoint[ref]).encode('utf-8')
        self.elementstack[-1][2].append(text)

    def handle_data(self, text, escape=1):
        # called for each block of plain text, i.e. outside of any tag and
        # not containing any character or entity references
        if not self.elementstack:
            return
        if escape and self.contentparams.get('type') == u'application/xhtml+xml':
            text = _xmlescape(text)
        self.elementstack[-1][2].append(text)

    def handle_comment(self, text):
        # called for each comment, e.g. <!-- insert message here -->
        pass

    def handle_pi(self, text):
        # called for each processing instruction, e.g. <?instruction>
        pass

    def handle_decl(self, text):
        pass

    def parse_declaration(self, i):
        # override internal declaration handler to handle CDATA blocks
        if self.rawdata[i:i+9] == '<![CDATA[':
            k = self.rawdata.find(']]>', i)
            if k == -1:
                # CDATA block began but didn't finish
                k = len(self.rawdata)
                return k
            self.handle_data(_xmlescape(self.rawdata[i+9:k]), 0)
            return k+3
        else:
            k = self.rawdata.find('>', i)
            if k >= 0:
                return k+1
            else:
                # We have an incomplete CDATA block.
                return k

    def mapContentType(self, contentType):
        contentType = contentType.lower()
        if contentType == 'text' or contentType == 'plain':
            contentType = u'text/plain'
        elif contentType == 'html':
            contentType = u'text/html'
        elif contentType == 'xhtml':
            contentType = u'application/xhtml+xml'
        return contentType

    def trackNamespace(self, prefix, uri):
        loweruri = uri.lower()
        if not self.version:
            if (prefix, loweruri) == (None, 'http://my.netscape.com/rdf/simple/0.9/'):
                self.version = u'rss090'
            elif loweruri == 'http://purl.org/rss/1.0/':
                self.version = u'rss10'
            elif loweruri == 'http://www.w3.org/2005/atom':
                self.version = u'atom10'
        if loweruri.find(u'backend.userland.com/rss') <> -1:
            # match any backend.userland.com namespace
            uri = u'http://backend.userland.com/rss'
            loweruri = uri
        if loweruri in self._matchnamespaces:
            self.namespacemap[prefix] = self._matchnamespaces[loweruri]
            self.namespacesInUse[self._matchnamespaces[loweruri]] = uri
        else:
            self.namespacesInUse[prefix or ''] = uri

    def resolveURI(self, uri):
        return _urljoin(self.baseuri or u'', uri)

    def decodeEntities(self, element, data):
        return data

    def strattrs(self, attrs):
        return ''.join([' %s="%s"' % (t[0],_xmlescape(t[1],{'"':'&quot;'})) for t in attrs])

    def push(self, element, expectingText):
        self.elementstack.append([element, expectingText, []])

    def pop(self, element, stripWhitespace=1):
        if not self.elementstack:
            return
        if self.elementstack[-1][0] != element:
            return

        element, expectingText, pieces = self.elementstack.pop()

        if self.version == u'atom10' and self.contentparams.get('type', u'text') == u'application/xhtml+xml':
            # remove enclosing child element, but only if it is a <div> and
            # only if all the remaining content is nested underneath it.
            # This means that the divs would be retained in the following:
            #    <div>foo</div><div>bar</div>
            while pieces and len(pieces)>1 and not pieces[-1].strip():
                del pieces[-1]
            while pieces and len(pieces)>1 and not pieces[0].strip():
                del pieces[0]
            if pieces and (pieces[0] == '<div>' or pieces[0].startswith('<div ')) and pieces[-1]=='</div>':
                depth = 0
                for piece in pieces[:-1]:
                    if piece.startswith('</'):
                        depth -= 1
                        if depth == 0:
                            break
                    elif piece.startswith('<') and not piece.endswith('/>'):
                        depth += 1
                else:
                    pieces = pieces[1:-1]

        # Ensure each piece is a str for Python 3
        for (i, v) in enumerate(pieces):
            if not isinstance(v, unicode):
                pieces[i] = v.decode('utf-8')

        output = u''.join(pieces)
        if stripWhitespace:
            output = output.strip()
        if not expectingText:
            return output

        # decode base64 content
        if base64 and self.contentparams.get('base64', 0):
            try:
                output = _base64decode(output)
            except binascii.Error:
                pass
            except binascii.Incomplete:
                pass
            except TypeError:
                # In Python 3, base64 takes and outputs bytes, not str
                # This may not be the most correct way to accomplish this
                output = _base64decode(output.encode('utf-8')).decode('utf-8')

        # resolve relative URIs
        if (element in self.can_be_relative_uri) and output:
            # do not resolve guid elements with isPermalink="false"
            if not element == 'id' or self.guidislink:
                output = self.resolveURI(output)

        # decode entities within embedded markup
        if not self.contentparams.get('base64', 0):
            output = self.decodeEntities(element, output)

        # some feed formats require consumers to guess
        # whether the content is html or plain text
        if not self.version.startswith(u'atom') and self.contentparams.get('type') == u'text/plain':
            if self.lookslikehtml(output):
                self.contentparams['type'] = u'text/html'

        # remove temporary cruft from contentparams
        try:
            del self.contentparams['mode']
        except KeyError:
            pass
        try:
            del self.contentparams['base64']
        except KeyError:
            pass

        is_htmlish = self.mapContentType(self.contentparams.get('type', u'text/html')) in self.html_types
        # resolve relative URIs within embedded markup
        if is_htmlish and RESOLVE_RELATIVE_URIS:
            if element in self.can_contain_relative_uris:
                output = _resolveRelativeURIs(output, self.baseuri, self.encoding, self.contentparams.get('type', u'text/html'))

        # sanitize embedded markup
        if is_htmlish and SANITIZE_HTML:
            if element in self.can_contain_dangerous_markup:
                output = _sanitizeHTML(output, self.encoding, self.contentparams.get('type', u'text/html'))

        if self.encoding and not isinstance(output, unicode):
            output = output.decode(self.encoding, 'ignore')

        # address common error where people take data that is already
        # utf-8, presume that it is iso-8859-1, and re-encode it.
        if self.encoding in (u'utf-8', u'utf-8_INVALID_PYTHON_3') and isinstance(output, unicode):
            try:
                output = output.encode('iso-8859-1').decode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass

        # map win-1252 extensions to the proper code points
        if isinstance(output, unicode):
            output = output.translate(_cp1252)

        # categories/tags/keywords/whatever are handled in _end_category
        if element == 'category':
            return output

        if element == 'title' and -1 < self.title_depth <= self.depth:
            return output

        # store output in appropriate place(s)
        if self.inentry and not self.insource:
            if element == 'content':
                self.entries[-1].setdefault(element, [])
                contentparams = copy.deepcopy(self.contentparams)
                contentparams['value'] = output
                self.entries[-1][element].append(contentparams)
            elif element == 'link':
                if not self.inimage:
                    # query variables in urls in link elements are improperly
                    # converted from `?a=1&b=2` to `?a=1&b;=2` as if they're
                    # unhandled character references. fix this special case.
                    output = re.sub("&([A-Za-z0-9_]+);", "&\g<1>", output)
                    self.entries[-1][element] = output
                    if output:
                        self.entries[-1]['links'][-1]['href'] = output
            else:
                if element == 'description':
                    element = 'summary'
                old_value_depth = self.property_depth_map.setdefault(self.entries[-1], {}).get(element)
                if old_value_depth is None or self.depth <= old_value_depth:
                    self.property_depth_map[self.entries[-1]][element] = self.depth
                    self.entries[-1][element] = output
                if self.incontent:
                    contentparams = copy.deepcopy(self.contentparams)
                    contentparams['value'] = output
                    self.entries[-1][element + '_detail'] = contentparams
        elif (self.infeed or self.insource):# and (not self.intextinput) and (not self.inimage):
            context = self._getContext()
            if element == 'description':
                element = 'subtitle'
            context[element] = output
            if element == 'link':
                # fix query variables; see above for the explanation
                output = re.sub("&([A-Za-z0-9_]+);", "&\g<1>", output)
                context[element] = output
                context['links'][-1]['href'] = output
            elif self.incontent:
                contentparams = copy.deepcopy(self.contentparams)
                contentparams['value'] = output
                context[element + '_detail'] = contentparams
        return output

    def pushContent(self, tag, attrsD, defaultContentType, expectingText):
        self.incontent += 1
        if self.lang:
            self.lang=self.lang.replace('_','-')
        self.contentparams = FeedParserDict({
            'type': self.mapContentType(attrsD.get('type', defaultContentType)),
            'language': self.lang,
            'base': self.baseuri})
        self.contentparams['base64'] = self._isBase64(attrsD, self.contentparams)
        self.push(tag, expectingText)

    def popContent(self, tag):
        value = self.pop(tag)
        self.incontent -= 1
        self.contentparams.clear()
        return value

    # a number of elements in a number of RSS variants are nominally plain
    # text, but this is routinely ignored.  This is an attempt to detect
    # the most common cases.  As false positives often result in silent
    # data loss, this function errs on the conservative side.
    @staticmethod
    def lookslikehtml(s):
        # must have a close tag or an entity reference to qualify
        if not (re.search(r'</(\w+)>',s) or re.search("&#?\w+;",s)):
            return

        # all tags must be in a restricted subset of valid HTML tags
        if filter(lambda t: t.lower() not in _HTMLSanitizer.acceptable_elements,
            re.findall(r'</?(\w+)',s)):
            return

        # all entities must have been defined as valid HTML entities
        if filter(lambda e: e not in entitydefs.keys(), re.findall(r'&(\w+);', s)):
            return

        return 1

    def _mapToStandardPrefix(self, name):
        colonpos = name.find(':')
        if colonpos <> -1:
            prefix = name[:colonpos]
            suffix = name[colonpos+1:]
            prefix = self.namespacemap.get(prefix, prefix)
            name = prefix + ':' + suffix
        return name

    def _getAttribute(self, attrsD, name):
        return attrsD.get(self._mapToStandardPrefix(name))

    def _isBase64(self, attrsD, contentparams):
        if attrsD.get('mode', '') == 'base64':
            return 1
        if self.contentparams['type'].startswith(u'text/'):
            return 0
        if self.contentparams['type'].endswith(u'+xml'):
            return 0
        if self.contentparams['type'].endswith(u'/xml'):
            return 0
        return 1

    def _itsAnHrefDamnIt(self, attrsD):
        href = attrsD.get('url', attrsD.get('uri', attrsD.get('href', None)))
        if href:
            try:
                del attrsD['url']
            except KeyError:
                pass
            try:
                del attrsD['uri']
            except KeyError:
                pass
            attrsD['href'] = href
        return attrsD

    def _save(self, key, value, overwrite=False):
        context = self._getContext()
        if overwrite:
            context[key] = value
        else:
            context.setdefault(key, value)

    def _start_rss(self, attrsD):
        versionmap = {'0.91': u'rss091u',
                      '0.92': u'rss092',
                      '0.93': u'rss093',
                      '0.94': u'rss094'}
        #If we're here then this is an RSS feed.
        #If we don't have a version or have a version that starts with something
        #other than RSS then there's been a mistake. Correct it.
        if not self.version or not self.version.startswith(u'rss'):
            attr_version = attrsD.get('version', '')
            version = versionmap.get(attr_version)
            if version:
                self.version = version
            elif attr_version.startswith('2.'):
                self.version = u'rss20'
            else:
                self.version = u'rss'

    def _start_channel(self, attrsD):
        self.infeed = 1
        self._cdf_common(attrsD)

    def _cdf_common(self, attrsD):
        if 'lastmod' in attrsD:
            self._start_modified({})
            self.elementstack[-1][-1] = attrsD['lastmod']
            self._end_modified()
        if 'href' in attrsD:
            self._start_link({})
            self.elementstack[-1][-1] = attrsD['href']
            self._end_link()

    def _start_feed(self, attrsD):
        self.infeed = 1
        versionmap = {'0.1': u'atom01',
                      '0.2': u'atom02',
                      '0.3': u'atom03'}
        if not self.version:
            attr_version = attrsD.get('version')
            version = versionmap.get(attr_version)
            if version:
                self.version = version
            else:
                self.version = u'atom'

    def _end_channel(self):
        self.infeed = 0
    _end_feed = _end_channel

    def _start_image(self, attrsD):
        context = self._getContext()
        if not self.inentry:
            context.setdefault('image', FeedParserDict())
        self.inimage = 1
        self.title_depth = -1
        self.push('image', 0)

    def _end_image(self):
        self.pop('image')
        self.inimage = 0

    def _start_textinput(self, attrsD):
        context = self._getContext()
        context.setdefault('textinput', FeedParserDict())
        self.intextinput = 1
        self.title_depth = -1
        self.push('textinput', 0)
    _start_textInput = _start_textinput

    def _end_textinput(self):
        self.pop('textinput')
        self.intextinput = 0
    _end_textInput = _end_textinput

    def _start_author(self, attrsD):
        self.inauthor = 1
        self.push('author', 1)
        # Append a new FeedParserDict when expecting an author
        context = self._getContext()
        context.setdefault('authors', [])
        context['authors'].append(FeedParserDict())
    _start_managingeditor = _start_author
    _start_dc_author = _start_author
    _start_dc_creator = _start_author
    _start_itunes_author = _start_author

    def _end_author(self):
        self.pop('author')
        self.inauthor = 0
        self._sync_author_detail()
    _end_managingeditor = _end_author
    _end_dc_author = _end_author
    _end_dc_creator = _end_author
    _end_itunes_author = _end_author

    def _start_itunes_owner(self, attrsD):
        self.inpublisher = 1
        self.push('publisher', 0)

    def _end_itunes_owner(self):
        self.pop('publisher')
        self.inpublisher = 0
        self._sync_author_detail('publisher')

    def _start_contributor(self, attrsD):
        self.incontributor = 1
        context = self._getContext()
        context.setdefault('contributors', [])
        context['contributors'].append(FeedParserDict())
        self.push('contributor', 0)

    def _end_contributor(self):
        self.pop('contributor')
        self.incontributor = 0

    def _start_dc_contributor(self, attrsD):
        self.incontributor = 1
        context = self._getContext()
        context.setdefault('contributors', [])
        context['contributors'].append(FeedParserDict())
        self.push('name', 0)

    def _end_dc_contributor(self):
        self._end_name()
        self.incontributor = 0

    def _start_name(self, attrsD):
        self.push('name', 0)
    _start_itunes_name = _start_name

    def _end_name(self):
        value = self.pop('name')
        if self.inpublisher:
            self._save_author('name', value, 'publisher')
        elif self.inauthor:
            self._save_author('name', value)
        elif self.incontributor:
            self._save_contributor('name', value)
        elif self.intextinput:
            context = self._getContext()
            context['name'] = value
    _end_itunes_name = _end_name

    def _start_width(self, attrsD):
        self.push('width', 0)

    def _end_width(self):
        value = self.pop('width')
        try:
            value = int(value)
        except ValueError:
            value = 0
        if self.inimage:
            context = self._getContext()
            context['width'] = value

    def _start_height(self, attrsD):
        self.push('height', 0)

    def _end_height(self):
        value = self.pop('height')
        try:
            value = int(value)
        except ValueError:
            value = 0
        if self.inimage:
            context = self._getContext()
            context['height'] = value

    def _start_url(self, attrsD):
        self.push('href', 1)
    _start_homepage = _start_url
    _start_uri = _start_url

    def _end_url(self):
        value = self.pop('href')
        if self.inauthor:
            self._save_author('href', value)
        elif self.incontributor:
            self._save_contributor('href', value)
    _end_homepage = _end_url
    _end_uri = _end_url

    def _start_email(self, attrsD):
        self.push('email', 0)
    _start_itunes_email = _start_email

    def _end_email(self):
        value = self.pop('email')
        if self.inpublisher:
            self._save_author('email', value, 'publisher')
        elif self.inauthor:
            self._save_author('email', value)
        elif self.incontributor:
            self._save_contributor('email', value)
    _end_itunes_email = _end_email

    def _getContext(self):
        if self.insource:
            context = self.sourcedata
        elif self.inimage and 'image' in self.feeddata:
            context = self.feeddata['image']
        elif self.intextinput:
            context = self.feeddata['textinput']
        elif self.inentry:
            context = self.entries[-1]
        else:
            context = self.feeddata
        return context

    def _save_author(self, key, value, prefix='author'):
        context = self._getContext()
        context.setdefault(prefix + '_detail', FeedParserDict())
        context[prefix + '_detail'][key] = value
        self._sync_author_detail()
        context.setdefault('authors', [FeedParserDict()])
        context['authors'][-1][key] = value

    def _save_contributor(self, key, value):
        context = self._getContext()
        context.setdefault('contributors', [FeedParserDict()])
        context['contributors'][-1][key] = value

    def _sync_author_detail(self, key='author'):
        context = self._getContext()
        detail = context.get('%s_detail' % key)
        if detail:
            name = detail.get('name')
            email = detail.get('email')
            if name and email:
                context[key] = u'%s (%s)' % (name, email)
            elif name:
                context[key] = name
            elif email:
                context[key] = email
        else:
            author, email = context.get(key), None
            if not author:
                return
            emailmatch = re.search(ur'''(([a-zA-Z0-9\_\-\.\+]+)@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.)|(([a-zA-Z0-9\-]+\.)+))([a-zA-Z]{2,4}|[0-9]{1,3})(\]?))(\?subject=\S+)?''', author)
            if emailmatch:
                email = emailmatch.group(0)
                # probably a better way to do the following, but it passes all the tests
                author = author.replace(email, u'')
                author = author.replace(u'()', u'')
                author = author.replace(u'<>', u'')
                author = author.replace(u'&lt;&gt;', u'')
                author = author.strip()
                if author and (author[0] == u'('):
                    author = author[1:]
                if author and (author[-1] == u')'):
                    author = author[:-1]
                author = author.strip()
            if author or email:
                context.setdefault('%s_detail' % key, FeedParserDict())
            if author:
                context['%s_detail' % key]['name'] = author
            if email:
                context['%s_detail' % key]['email'] = email

    def _start_subtitle(self, attrsD):
        self.pushContent('subtitle', attrsD, u'text/plain', 1)
    _start_tagline = _start_subtitle
    _start_itunes_subtitle = _start_subtitle

    def _end_subtitle(self):
        self.popContent('subtitle')
    _end_tagline = _end_subtitle
    _end_itunes_subtitle = _end_subtitle

    def _start_rights(self, attrsD):
        self.pushContent('rights', attrsD, u'text/plain', 1)
    _start_dc_rights = _start_rights
    _start_copyright = _start_rights

    def _end_rights(self):
        self.popContent('rights')
    _end_dc_rights = _end_rights
    _end_copyright = _end_rights

    def _start_item(self, attrsD):
        self.entries.append(FeedParserDict())
        self.push('item', 0)
        self.inentry = 1
        self.guidislink = 0
        self.title_depth = -1
        self.psc_chapters_flag = None
        id = self._getAttribute(attrsD, 'rdf:about')
        if id:
            context = self._getContext()
            context['id'] = id
        self._cdf_common(attrsD)
    _start_entry = _start_item

    def _end_item(self):
        self.pop('item')
        self.inentry = 0
    _end_entry = _end_item

    def _start_dc_language(self, attrsD):
        self.push('language', 1)
    _start_language = _start_dc_language

    def _end_dc_language(self):
        self.lang = self.pop('language')
    _end_language = _end_dc_language

    def _start_dc_publisher(self, attrsD):
        self.push('publisher', 1)
    _start_webmaster = _start_dc_publisher

    def _end_dc_publisher(self):
        self.pop('publisher')
        self._sync_author_detail('publisher')
    _end_webmaster = _end_dc_publisher

    def _start_published(self, attrsD):
        self.push('published', 1)
    _start_dcterms_issued = _start_published
    _start_issued = _start_published
    _start_pubdate = _start_published

    def _end_published(self):
        value = self.pop('published')
        self._save('published_parsed', _parse_date(value), overwrite=True)
    _end_dcterms_issued = _end_published
    _end_issued = _end_published
    _end_pubdate = _end_published

    def _start_updated(self, attrsD):
        self.push('updated', 1)
    _start_modified = _start_updated
    _start_dcterms_modified = _start_updated
    _start_dc_date = _start_updated
    _start_lastbuilddate = _start_updated

    def _end_updated(self):
        value = self.pop('updated')
        parsed_value = _parse_date(value)
        self._save('updated_parsed', parsed_value, overwrite=True)
    _end_modified = _end_updated
    _end_dcterms_modified = _end_updated
    _end_dc_date = _end_updated
    _end_lastbuilddate = _end_updated

    def _start_created(self, attrsD):
        self.push('created', 1)
    _start_dcterms_created = _start_created

    def _end_created(self):
        value = self.pop('created')
        self._save('created_parsed', _parse_date(value), overwrite=True)
    _end_dcterms_created = _end_created

    def _start_expirationdate(self, attrsD):
        self.push('expired', 1)

    def _end_expirationdate(self):
        self._save('expired_parsed', _parse_date(self.pop('expired')), overwrite=True)

    # geospatial location, or "where", from georss.org

    def _start_georssgeom(self, attrsD):
        self.push('geometry', 0)
        context = self._getContext()
        context['where'] = FeedParserDict()

    _start_georss_point = _start_georssgeom
    _start_georss_line = _start_georssgeom
    _start_georss_polygon = _start_georssgeom
    _start_georss_box = _start_georssgeom

    def _save_where(self, geometry):
        context = self._getContext()
        context['where'].update(geometry)

    def _end_georss_point(self):
        geometry = _parse_georss_point(self.pop('geometry'))
        if geometry:
            self._save_where(geometry)

    def _end_georss_line(self):
        geometry = _parse_georss_line(self.pop('geometry'))
        if geometry:
            self._save_where(geometry)
    
    def _end_georss_polygon(self):
        this = self.pop('geometry')
        geometry = _parse_georss_polygon(this)
        if geometry:
            self._save_where(geometry)

    def _end_georss_box(self):
        geometry = _parse_georss_box(self.pop('geometry'))
        if geometry:
            self._save_where(geometry)

    def _start_where(self, attrsD):
        self.push('where', 0)
        context = self._getContext()
        context['where'] = FeedParserDict()
    _start_georss_where = _start_where

    def _parse_srs_attrs(self, attrsD):
        srsName = attrsD.get('srsname')
        try:
            srsDimension = int(attrsD.get('srsdimension', '2'))
        except ValueError:
            srsDimension = 2
        context = self._getContext()
        context['where']['srsName'] = srsName
        context['where']['srsDimension'] = srsDimension

    def _start_gml_point(self, attrsD):
        self._parse_srs_attrs(attrsD)
        self.ingeometry = 1
        self.push('geometry', 0)

    def _start_gml_linestring(self, attrsD):
        self._parse_srs_attrs(attrsD)
        self.ingeometry = 'linestring'
        self.push('geometry', 0)

    def _start_gml_polygon(self, attrsD):
        self._parse_srs_attrs(attrsD)
        self.push('geometry', 0)

    def _start_gml_exterior(self, attrsD):
        self.push('geometry', 0)

    def _start_gml_linearring(self, attrsD):
        self.ingeometry = 'polygon'
        self.push('geometry', 0)

    def _start_gml_pos(self, attrsD):
        self.push('pos', 0)

    def _end_gml_pos(self):
        this = self.pop('pos')
        context = self._getContext()
        srsName = context['where'].get('srsName')
        srsDimension = context['where'].get('srsDimension', 2)
        swap = True
        if srsName and "EPSG" in srsName:
            epsg = int(srsName.split(":")[-1])
            swap = bool(epsg in _geogCS)
        geometry = _parse_georss_point(this, swap=swap, dims=srsDimension)
        if geometry:
            self._save_where(geometry)

    def _start_gml_poslist(self, attrsD):
        self.push('pos', 0)

    def _end_gml_poslist(self):
        this = self.pop('pos')
        context = self._getContext()
        srsName = context['where'].get('srsName')
        srsDimension = context['where'].get('srsDimension', 2)
        swap = True
        if srsName and "EPSG" in srsName:
            epsg = int(srsName.split(":")[-1])
            swap = bool(epsg in _geogCS)
        geometry = _parse_poslist(
            this, self.ingeometry, swap=swap, dims=srsDimension)
        if geometry:
            self._save_where(geometry)

    def _end_geom(self):
        self.ingeometry = 0
        self.pop('geometry')
    _end_gml_point = _end_geom
    _end_gml_linestring = _end_geom
    _end_gml_linearring = _end_geom
    _end_gml_exterior = _end_geom
    _end_gml_polygon = _end_geom

    def _end_where(self):
        self.pop('where')
    _end_georss_where = _end_where

    # end geospatial

    def _start_cc_license(self, attrsD):
        context = self._getContext()
        value = self._getAttribute(attrsD, 'rdf:resource')
        attrsD = FeedParserDict()
        attrsD['rel'] = u'license'
        if value:
            attrsD['href']=value
        context.setdefault('links', []).append(attrsD)

    def _start_creativecommons_license(self, attrsD):
        self.push('license', 1)
    _start_creativeCommons_license = _start_creativecommons_license

    def _end_creativecommons_license(self):
        value = self.pop('license')
        context = self._getContext()
        attrsD = FeedParserDict()
        attrsD['rel'] = u'license'
        if value:
            attrsD['href'] = value
        context.setdefault('links', []).append(attrsD)
        del context['license']
    _end_creativeCommons_license = _end_creativecommons_license

    def _addTag(self, term, scheme, label):
        context = self._getContext()
        tags = context.setdefault('tags', [])
        if (not term) and (not scheme) and (not label):
            return
        value = FeedParserDict({'term': term, 'scheme': scheme, 'label': label})
        if value not in tags:
            tags.append(value)

    def _start_category(self, attrsD):
        term = attrsD.get('term')
        scheme = attrsD.get('scheme', attrsD.get('domain'))
        label = attrsD.get('label')
        self._addTag(term, scheme, label)
        self.push('category', 1)
    _start_dc_subject = _start_category
    _start_keywords = _start_category

    def _start_media_category(self, attrsD):
        attrsD.setdefault('scheme', u'http://search.yahoo.com/mrss/category_schema')
        self._start_category(attrsD)

    def _end_itunes_keywords(self):
        for term in self.pop('itunes_keywords').split(','):
            if term.strip():
                self._addTag(term.strip(), u'http://www.itunes.com/', None)

    def _start_itunes_category(self, attrsD):
        self._addTag(attrsD.get('text'), u'http://www.itunes.com/', None)
        self.push('category', 1)

    def _end_category(self):
        value = self.pop('category')
        if not value:
            return
        context = self._getContext()
        tags = context['tags']
        if value and len(tags) and not tags[-1]['term']:
            tags[-1]['term'] = value
        else:
            self._addTag(value, None, None)
    _end_dc_subject = _end_category
    _end_keywords = _end_category
    _end_itunes_category = _end_category
    _end_media_category = _end_category

    def _start_cloud(self, attrsD):
        self._getContext()['cloud'] = FeedParserDict(attrsD)

    def _start_link(self, attrsD):
        attrsD.setdefault('rel', u'alternate')
        if attrsD['rel'] == u'self':
            attrsD.setdefault('type', u'application/atom+xml')
        else:
            attrsD.setdefault('type', u'text/html')
        context = self._getContext()
        attrsD = self._itsAnHrefDamnIt(attrsD)
        if 'href' in attrsD:
            attrsD['href'] = self.resolveURI(attrsD['href'])
        expectingText = self.infeed or self.inentry or self.insource
        context.setdefault('links', [])
        if not (self.inentry and self.inimage):
            context['links'].append(FeedParserDict(attrsD))
        if 'href' in attrsD:
            expectingText = 0
            if (attrsD.get('rel') == u'alternate') and (self.mapContentType(attrsD.get('type')) in self.html_types):
                context['link'] = attrsD['href']
        else:
            self.push('link', expectingText)

    def _end_link(self):
        value = self.pop('link')

    def _start_guid(self, attrsD):
        self.guidislink = (attrsD.get('ispermalink', 'true') == 'true')
        self.push('id', 1)
    _start_id = _start_guid

    def _end_guid(self):
        value = self.pop('id')
        self._save('guidislink', self.guidislink and 'link' not in self._getContext())
        if self.guidislink:
            # guid acts as link, but only if 'ispermalink' is not present or is 'true',
            # and only if the item doesn't already have a link element
            self._save('link', value)
    _end_id = _end_guid

    def _start_title(self, attrsD):
        if self.svgOK:
            return self.unknown_starttag('title', attrsD.items())
        self.pushContent('title', attrsD, u'text/plain', self.infeed or self.inentry or self.insource)
    _start_dc_title = _start_title
    _start_media_title = _start_title

    def _end_title(self):
        if self.svgOK:
            return
        value = self.popContent('title')
        if not value:
            return
        self.title_depth = self.depth
    _end_dc_title = _end_title

    def _end_media_title(self):
        title_depth = self.title_depth
        self._end_title()
        self.title_depth = title_depth

    def _start_description(self, attrsD):
        context = self._getContext()
        if 'summary' in context:
            self._summaryKey = 'content'
            self._start_content(attrsD)
        else:
            self.pushContent('description', attrsD, u'text/html', self.infeed or self.inentry or self.insource)
    _start_dc_description = _start_description
    _start_media_description = _start_description

    def _start_abstract(self, attrsD):
        self.pushContent('description', attrsD, u'text/plain', self.infeed or self.inentry or self.insource)

    def _end_description(self):
        if self._summaryKey == 'content':
            self._end_content()
        else:
            value = self.popContent('description')
        self._summaryKey = None
    _end_abstract = _end_description
    _end_dc_description = _end_description
    _end_media_description = _end_description

    def _start_info(self, attrsD):
        self.pushContent('info', attrsD, u'text/plain', 1)
    _start_feedburner_browserfriendly = _start_info

    def _end_info(self):
        self.popContent('info')
    _end_feedburner_browserfriendly = _end_info

    def _start_generator(self, attrsD):
        if attrsD:
            attrsD = self._itsAnHrefDamnIt(attrsD)
            if 'href' in attrsD:
                attrsD['href'] = self.resolveURI(attrsD['href'])
        self._getContext()['generator_detail'] = FeedParserDict(attrsD)
        self.push('generator', 1)

    def _end_generator(self):
        value = self.pop('generator')
        context = self._getContext()
        if 'generator_detail' in context:
            context['generator_detail']['name'] = value

    def _start_admin_generatoragent(self, attrsD):
        self.push('generator', 1)
        value = self._getAttribute(attrsD, 'rdf:resource')
        if value:
            self.elementstack[-1][2].append(value)
        self.pop('generator')
        self._getContext()['generator_detail'] = FeedParserDict({'href': value})

    def _start_admin_errorreportsto(self, attrsD):
        self.push('errorreportsto', 1)
        value = self._getAttribute(attrsD, 'rdf:resource')
        if value:
            self.elementstack[-1][2].append(value)
        self.pop('errorreportsto')

    def _start_summary(self, attrsD):
        context = self._getContext()
        if 'summary' in context:
            self._summaryKey = 'content'
            self._start_content(attrsD)
        else:
            self._summaryKey = 'summary'
            self.pushContent(self._summaryKey, attrsD, u'text/plain', 1)
    _start_itunes_summary = _start_summary

    def _end_summary(self):
        if self._summaryKey == 'content':
            self._end_content()
        else:
            self.popContent(self._summaryKey or 'summary')
        self._summaryKey = None
    _end_itunes_summary = _end_summary

    def _start_enclosure(self, attrsD):
        attrsD = self._itsAnHrefDamnIt(attrsD)
        context = self._getContext()
        attrsD['rel'] = u'enclosure'
        context.setdefault('links', []).append(FeedParserDict(attrsD))

    def _start_source(self, attrsD):
        if 'url' in attrsD:
            # This means that we're processing a source element from an RSS 2.0 feed
            self.sourcedata['href'] = attrsD[u'url']
        self.push('source', 1)
        self.insource = 1
        self.title_depth = -1

    def _end_source(self):
        self.insource = 0
        value = self.pop('source')
        if value:
            self.sourcedata['title'] = value
        self._getContext()['source'] = copy.deepcopy(self.sourcedata)
        self.sourcedata.clear()

    def _start_content(self, attrsD):
        self.pushContent('content', attrsD, u'text/plain', 1)
        src = attrsD.get('src')
        if src:
            self.contentparams['src'] = src
        self.push('content', 1)

    def _start_body(self, attrsD):
        self.pushContent('content', attrsD, u'application/xhtml+xml', 1)
    _start_xhtml_body = _start_body

    def _start_content_encoded(self, attrsD):
        self.pushContent('content', attrsD, u'text/html', 1)
    _start_fullitem = _start_content_encoded

    def _end_content(self):
        copyToSummary = self.mapContentType(self.contentparams.get('type')) in ([u'text/plain'] + self.html_types)
        value = self.popContent('content')
        if copyToSummary:
            self._save('summary', value)

    _end_body = _end_content
    _end_xhtml_body = _end_content
    _end_content_encoded = _end_content
    _end_fullitem = _end_content

    def _start_itunes_image(self, attrsD):
        self.push('itunes_image', 0)
        if attrsD.get('href'):
            self._getContext()['image'] = FeedParserDict({'href': attrsD.get('href')})
        elif attrsD.get('url'):
            self._getContext()['image'] = FeedParserDict({'href': attrsD.get('url')})
    _start_itunes_link = _start_itunes_image

    def _end_itunes_block(self):
        value = self.pop('itunes_block', 0)
        self._getContext()['itunes_block'] = (value == 'yes') and 1 or 0

    def _end_itunes_explicit(self):
        value = self.pop('itunes_explicit', 0)
        # Convert 'yes' -> True, 'clean' to False, and any other value to None
        # False and None both evaluate as False, so the difference can be ignored
        # by applications that only need to know if the content is explicit.
        self._getContext()['itunes_explicit'] = (None, False, True)[(value == 'yes' and 2) or value == 'clean' or 0]

    def _start_media_group(self, attrsD):
        # don't do anything, but don't break the enclosed tags either
        pass

    def _start_media_credit(self, attrsD):
        context = self._getContext()
        context.setdefault('media_credit', [])
        context['media_credit'].append(attrsD)
        self.push('credit', 1)

    def _end_media_credit(self):
        credit = self.pop('credit')
        if credit != None and len(credit.strip()) != 0:
            context = self._getContext()
            context['media_credit'][-1]['content'] = credit

    def _start_media_restriction(self, attrsD):
        context = self._getContext()
        context.setdefault('media_restriction', attrsD)
        self.push('restriction', 1)

    def _end_media_restriction(self):
        restriction = self.pop('restriction')
        if restriction != None and len(restriction.strip()) != 0:
            context = self._getContext()
            context['media_restriction']['content'] = restriction

    def _start_media_license(self, attrsD):
        context = self._getContext()
        context.setdefault('media_license', attrsD)
        self.push('license', 1)

    def _end_media_license(self):
        license = self.pop('license')
        if license != None and len(license.strip()) != 0:
            context = self._getContext()
            context['media_license']['content'] = license

    def _start_media_content(self, attrsD):
        context = self._getContext()
        context.setdefault('media_content', [])
        context['media_content'].append(attrsD)

    def _start_media_thumbnail(self, attrsD):
        context = self._getContext()
        context.setdefault('media_thumbnail', [])
        self.push('url', 1) # new
        context['media_thumbnail'].append(attrsD)

    def _end_media_thumbnail(self):
        url = self.pop('url')
        context = self._getContext()
        if url != None and len(url.strip()) != 0:
            if 'url' not in context['media_thumbnail'][-1]:
                context['media_thumbnail'][-1]['url'] = url

    def _start_media_player(self, attrsD):
        self.push('media_player', 0)
        self._getContext()['media_player'] = FeedParserDict(attrsD)

    def _end_media_player(self):
        value = self.pop('media_player')
        context = self._getContext()
        context['media_player']['content'] = value

    def _start_newlocation(self, attrsD):
        self.push('newlocation', 1)

    def _end_newlocation(self):
        url = self.pop('newlocation')
        context = self._getContext()
        # don't set newlocation if the context isn't right
        if context is not self.feeddata:
            return
        context['newlocation'] = _makeSafeAbsoluteURI(self.baseuri, url.strip())

    def _start_psc_chapters(self, attrsD):
        if self.psc_chapters_flag is None:
	    # Transition from None -> True
            self.psc_chapters_flag = True
            attrsD['chapters'] = []
            self._getContext()['psc_chapters'] = FeedParserDict(attrsD)
            
    def _end_psc_chapters(self):
        # Transition from True -> False
        self.psc_chapters_flag = False
        
    def _start_psc_chapter(self, attrsD):
        if self.psc_chapters_flag:
            start = self._getAttribute(attrsD, 'start')
            attrsD['start_parsed'] = _parse_psc_chapter_start(start)

            context = self._getContext()['psc_chapters']
            context['chapters'].append(FeedParserDict(attrsD))


if _XML_AVAILABLE:
    class _StrictFeedParser(_FeedParserMixin, xml.sax.handler.ContentHandler):
        def __init__(self, baseuri, baselang, encoding):
            xml.sax.handler.ContentHandler.__init__(self)
            _FeedParserMixin.__init__(self, baseuri, baselang, encoding)
            self.bozo = 0
            self.exc = None
            self.decls = {}

        def startPrefixMapping(self, prefix, uri):
            if not uri:
                return
            # Jython uses '' instead of None; standardize on None
            prefix = prefix or None
            self.trackNamespace(prefix, uri)
            if prefix and uri == 'http://www.w3.org/1999/xlink':
                self.decls['xmlns:' + prefix] = uri

        def startElementNS(self, name, qname, attrs):
            namespace, localname = name
            lowernamespace = str(namespace or '').lower()
            if lowernamespace.find(u'backend.userland.com/rss') <> -1:
                # match any backend.userland.com namespace
                namespace = u'http://backend.userland.com/rss'
                lowernamespace = namespace
            if qname and qname.find(':') > 0:
                givenprefix = qname.split(':')[0]
            else:
                givenprefix = None
            prefix = self._matchnamespaces.get(lowernamespace, givenprefix)
            if givenprefix and (prefix == None or (prefix == '' and lowernamespace == '')) and givenprefix not in self.namespacesInUse:
                raise UndeclaredNamespace, "'%s' is not associated with a namespace" % givenprefix
            localname = str(localname).lower()

            # qname implementation is horribly broken in Python 2.1 (it
            # doesn't report any), and slightly broken in Python 2.2 (it
            # doesn't report the xml: namespace). So we match up namespaces
            # with a known list first, and then possibly override them with
            # the qnames the SAX parser gives us (if indeed it gives us any
            # at all).  Thanks to MatejC for helping me test this and
            # tirelessly telling me that it didn't work yet.
            attrsD, self.decls = self.decls, {}
            if localname=='math' and namespace=='http://www.w3.org/1998/Math/MathML':
                attrsD['xmlns']=namespace
            if localname=='svg' and namespace=='http://www.w3.org/2000/svg':
                attrsD['xmlns']=namespace

            if prefix:
                localname = prefix.lower() + ':' + localname
            elif namespace and not qname: #Expat
                for name,value in self.namespacesInUse.items():
                    if name and value == namespace:
                        localname = name + ':' + localname
                        break

            for (namespace, attrlocalname), attrvalue in attrs.items():
                lowernamespace = (namespace or '').lower()
                prefix = self._matchnamespaces.get(lowernamespace, '')
                if prefix:
                    attrlocalname = prefix + ':' + attrlocalname
                attrsD[str(attrlocalname).lower()] = attrvalue
            for qname in attrs.getQNames():
                attrsD[str(qname).lower()] = attrs.getValueByQName(qname)
            localname = str(localname).lower()
            self.unknown_starttag(localname, attrsD.items())

        def characters(self, text):
            self.handle_data(text)

        def endElementNS(self, name, qname):
            namespace, localname = name
            lowernamespace = str(namespace or '').lower()
            if qname and qname.find(':') > 0:
                givenprefix = qname.split(':')[0]
            else:
                givenprefix = ''
            prefix = self._matchnamespaces.get(lowernamespace, givenprefix)
            if prefix:
                localname = prefix + ':' + localname
            elif namespace and not qname: #Expat
                for name,value in self.namespacesInUse.items():
                    if name and value == namespace:
                        localname = name + ':' + localname
                        break
            localname = str(localname).lower()
            self.unknown_endtag(localname)

        def error(self, exc):
            self.bozo = 1
            self.exc = exc

        # drv_libxml2 calls warning() in some cases
        warning = error

        def fatalError(self, exc):
            self.error(exc)
            raise exc

class _BaseHTMLProcessor(sgmllib.SGMLParser):
    special = re.compile('''[<>'"]''')
    bare_ampersand = re.compile("&(?!#\d+;|#x[0-9a-fA-F]+;|\w+;)")
    elements_no_end_tag = set([
      'area', 'base', 'basefont', 'br', 'col', 'command', 'embed', 'frame',
      'hr', 'img', 'input', 'isindex', 'keygen', 'link', 'meta', 'param',
      'source', 'track', 'wbr'
    ])

    def __init__(self, encoding, _type):
        self.encoding = encoding
        self._type = _type
        sgmllib.SGMLParser.__init__(self)

    def reset(self):
        self.pieces = []
        sgmllib.SGMLParser.reset(self)

    def _shorttag_replace(self, match):
        tag = match.group(1)
        if tag in self.elements_no_end_tag:
            return '<' + tag + ' />'
        else:
            return '<' + tag + '></' + tag + '>'

    # By declaring these methods and overriding their compiled code
    # with the code from sgmllib, the original code will execute in
    # feedparser's scope instead of sgmllib's. This means that the
    # `tagfind` and `charref` regular expressions will be found as
    # they're declared above, not as they're declared in sgmllib.
    def goahead(self, i):
        pass
    goahead.func_code = sgmllib.SGMLParser.goahead.func_code

    def __parse_starttag(self, i):
        pass
    __parse_starttag.func_code = sgmllib.SGMLParser.parse_starttag.func_code

    def parse_starttag(self,i):
        j = self.__parse_starttag(i)
        if self._type == 'application/xhtml+xml':
            if j>2 and self.rawdata[j-2:j]=='/>':
                self.unknown_endtag(self.lasttag)
        return j

    def feed(self, data):
        data = re.compile(r'<!((?!DOCTYPE|--|\[))', re.IGNORECASE).sub(r'&lt;!\1', data)
        data = re.sub(r'<([^<>\s]+?)\s*/>', self._shorttag_replace, data)
        data = data.replace('&#39;', "'")
        data = data.replace('&#34;', '"')
        try:
            bytes
            if bytes is str:
                raise NameError
            self.encoding = self.encoding + u'_INVALID_PYTHON_3'
        except NameError:
            if self.encoding and isinstance(data, unicode):
                data = data.encode(self.encoding)
        sgmllib.SGMLParser.feed(self, data)
        sgmllib.SGMLParser.close(self)

    def normalize_attrs(self, attrs):
        if not attrs:
            return attrs
        # utility method to be called by descendants
        attrs = dict([(k.lower(), v) for k, v in attrs]).items()
        attrs = [(k, k in ('rel', 'type') and v.lower() or v) for k, v in attrs]
        attrs.sort()
        return attrs

    def unknown_starttag(self, tag, attrs):
        # called for each start tag
        # attrs is a list of (attr, value) tuples
        # e.g. for <pre class='screen'>, tag='pre', attrs=[('class', 'screen')]
        uattrs = []
        strattrs=''
        if attrs:
            for key, value in attrs:
                value=value.replace('>','&gt;').replace('<','&lt;').replace('"','&quot;')
                value = self.bare_ampersand.sub("&amp;", value)
                # thanks to Kevin Marks for this breathtaking hack to deal with (valid) high-bit attribute values in UTF-8 feeds
                if not isinstance(value, unicode):
                    value = value.decode(self.encoding, 'ignore')
                try:
                    # Currently, in Python 3 the key is already a str, and cannot be decoded again
                    uattrs.append((unicode(key, self.encoding), value))
                except TypeError:
                    uattrs.append((key, value))
            strattrs = u''.join([u' %s="%s"' % (key, value) for key, value in uattrs])
            if self.encoding:
                try:
                    strattrs = strattrs.encode(self.encoding)
                except (UnicodeEncodeError, LookupError):
                    pass
        if tag in self.elements_no_end_tag:
            self.pieces.append('<%s%s />' % (tag, strattrs))
        else:
            self.pieces.append('<%s%s>' % (tag, strattrs))

    def unknown_endtag(self, tag):
        # called for each end tag, e.g. for </pre>, tag will be 'pre'
        # Reconstruct the original end tag.
        if tag not in self.elements_no_end_tag:
            self.pieces.append("</%s>" % tag)

    def handle_charref(self, ref):
        # called for each character reference, e.g. for '&#160;', ref will be '160'
        # Reconstruct the original character reference.
        ref = ref.lower()
        if ref.startswith('x'):
            value = int(ref[1:], 16)
        else:
            value = int(ref)

        if value in _cp1252:
            self.pieces.append('&#%s;' % hex(ord(_cp1252[value]))[1:])
        else:
            self.pieces.append('&#%s;' % ref)

    def handle_entityref(self, ref):
        # called for each entity reference, e.g. for '&copy;', ref will be 'copy'
        # Reconstruct the original entity reference.
        if ref in name2codepoint or ref == 'apos':
            self.pieces.append('&%s;' % ref)
        else:
            self.pieces.append('&amp;%s' % ref)

    def handle_data(self, text):
        # called for each block of plain text, i.e. outside of any tag and
        # not containing any character or entity references
        # Store the original text verbatim.
        self.pieces.append(text)

    def handle_comment(self, text):
        # called for each HTML comment, e.g. <!-- insert Javascript code here -->
        # Reconstruct the original comment.
        self.pieces.append('<!--%s-->' % text)

    def handle_pi(self, text):
        # called for each processing instruction, e.g. <?instruction>
        # Reconstruct original processing instruction.
        self.pieces.append('<?%s>' % text)

    def handle_decl(self, text):
        # called for the DOCTYPE, if present, e.g.
        # <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        #     "http://www.w3.org/TR/html4/loose.dtd">
        # Reconstruct original DOCTYPE
        self.pieces.append('<!%s>' % text)

    _new_declname_match = re.compile(r'[a-zA-Z][-_.a-zA-Z0-9:]*\s*').match
    def _scan_name(self, i, declstartpos):
        rawdata = self.rawdata
        n = len(rawdata)
        if i == n:
            return None, -1
        m = self._new_declname_match(rawdata, i)
        if m:
            s = m.group()
            name = s.strip()
            if (i + len(s)) == n:
                return None, -1  # end of buffer
            return name.lower(), m.end()
        else:
            self.handle_data(rawdata)
#            self.updatepos(declstartpos, i)
            return None, -1

    def convert_charref(self, name):
        return '&#%s;' % name

    def convert_entityref(self, name):
        return '&%s;' % name

    def output(self):
        '''Return processed HTML as a single string'''
        return ''.join([str(p) for p in self.pieces])

    def parse_declaration(self, i):
        try:
            return sgmllib.SGMLParser.parse_declaration(self, i)
        except sgmllib.SGMLParseError:
            # escape the doctype declaration and continue parsing
            self.handle_data('&lt;')
            return i+1

class _LooseFeedParser(_FeedParserMixin, _BaseHTMLProcessor):
    def __init__(self, baseuri, baselang, encoding, entities):
        sgmllib.SGMLParser.__init__(self)
        _FeedParserMixin.__init__(self, baseuri, baselang, encoding)
        _BaseHTMLProcessor.__init__(self, encoding, 'application/xhtml+xml')
        self.entities=entities

    def decodeEntities(self, element, data):
        data = data.replace('&#60;', '&lt;')
        data = data.replace('&#x3c;', '&lt;')
        data = data.replace('&#x3C;', '&lt;')
        data = data.replace('&#62;', '&gt;')
        data = data.replace('&#x3e;', '&gt;')
        data = data.replace('&#x3E;', '&gt;')
        data = data.replace('&#38;', '&amp;')
        data = data.replace('&#x26;', '&amp;')
        data = data.replace('&#34;', '&quot;')
        data = data.replace('&#x22;', '&quot;')
        data = data.replace('&#39;', '&apos;')
        data = data.replace('&#x27;', '&apos;')
        if not self.contentparams.get('type', u'xml').endswith(u'xml'):
            data = data.replace('&lt;', '<')
            data = data.replace('&gt;', '>')
            data = data.replace('&amp;', '&')
            data = data.replace('&quot;', '"')
            data = data.replace('&apos;', "'")
        return data

    def strattrs(self, attrs):
        return ''.join([' %s="%s"' % (n,v.replace('"','&quot;')) for n,v in attrs])

class _RelativeURIResolver(_BaseHTMLProcessor):
    relative_uris = set([('a', 'href'),
                     ('applet', 'codebase'),
                     ('area', 'href'),
                     ('blockquote', 'cite'),
                     ('body', 'background'),
                     ('del', 'cite'),
                     ('form', 'action'),
                     ('frame', 'longdesc'),
                     ('frame', 'src'),
                     ('iframe', 'longdesc'),
                     ('iframe', 'src'),
                     ('head', 'profile'),
                     ('img', 'longdesc'),
                     ('img', 'src'),
                     ('img', 'usemap'),
                     ('input', 'src'),
                     ('input', 'usemap'),
                     ('ins', 'cite'),
                     ('link', 'href'),
                     ('object', 'classid'),
                     ('object', 'codebase'),
                     ('object', 'data'),
                     ('object', 'usemap'),
                     ('q', 'cite'),
                     ('script', 'src'),
                     ('video', 'poster')])

    def __init__(self, baseuri, encoding, _type):
        _BaseHTMLProcessor.__init__(self, encoding, _type)
        self.baseuri = baseuri

    def resolveURI(self, uri):
        return _makeSafeAbsoluteURI(self.baseuri, uri.strip())

    def unknown_starttag(self, tag, attrs):
        attrs = self.normalize_attrs(attrs)
        attrs = [(key, ((tag, key) in self.relative_uris) and self.resolveURI(value) or value) for key, value in attrs]
        _BaseHTMLProcessor.unknown_starttag(self, tag, attrs)

def _resolveRelativeURIs(htmlSource, baseURI, encoding, _type):
    if not _SGML_AVAILABLE:
        return htmlSource

    p = _RelativeURIResolver(baseURI, encoding, _type)
    p.feed(htmlSource)
    return p.output()

def _makeSafeAbsoluteURI(base, rel=None):
    # bail if ACCEPTABLE_URI_SCHEMES is empty
    if not ACCEPTABLE_URI_SCHEMES:
        return _urljoin(base, rel or u'')
    if not base:
        return rel or u''
    if not rel:
        try:
            scheme = urlparse.urlparse(base)[0]
        except ValueError:
            return u''
        if not scheme or scheme in ACCEPTABLE_URI_SCHEMES:
            return base
        return u''
    uri = _urljoin(base, rel)
    if uri.strip().split(':', 1)[0] not in ACCEPTABLE_URI_SCHEMES:
        return u''
    return uri

class _HTMLSanitizer(_BaseHTMLProcessor):
    acceptable_elements = set(['a', 'abbr', 'acronym', 'address', 'area',
        'article', 'aside', 'audio', 'b', 'big', 'blockquote', 'br', 'button',
        'canvas', 'caption', 'center', 'cite', 'code', 'col', 'colgroup',
        'command', 'datagrid', 'datalist', 'dd', 'del', 'details', 'dfn',
        'dialog', 'dir', 'div', 'dl', 'dt', 'em', 'event-source', 'fieldset',
        'figcaption', 'figure', 'footer', 'font', 'form', 'header', 'h1',
        'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'input', 'ins',
        'keygen', 'kbd', 'label', 'legend', 'li', 'm', 'map', 'menu', 'meter',
        'multicol', 'nav', 'nextid', 'ol', 'output', 'optgroup', 'option',
        'p', 'pre', 'progress', 'q', 's', 'samp', 'section', 'select',
        'small', 'sound', 'source', 'spacer', 'span', 'strike', 'strong',
        'sub', 'sup', 'table', 'tbody', 'td', 'textarea', 'time', 'tfoot',
        'th', 'thead', 'tr', 'tt', 'u', 'ul', 'var', 'video', 'noscript'])

    acceptable_attributes = set(['abbr', 'accept', 'accept-charset', 'accesskey',
      'action', 'align', 'alt', 'autocomplete', 'autofocus', 'axis',
      'background', 'balance', 'bgcolor', 'bgproperties', 'border',
      'bordercolor', 'bordercolordark', 'bordercolorlight', 'bottompadding',
      'cellpadding', 'cellspacing', 'ch', 'challenge', 'char', 'charoff',
      'choff', 'charset', 'checked', 'cite', 'class', 'clear', 'color', 'cols',
      'colspan', 'compact', 'contenteditable', 'controls', 'coords', 'data',
      'datafld', 'datapagesize', 'datasrc', 'datetime', 'default', 'delay',
      'dir', 'disabled', 'draggable', 'dynsrc', 'enctype', 'end', 'face', 'for',
      'form', 'frame', 'galleryimg', 'gutter', 'headers', 'height', 'hidefocus',
      'hidden', 'high', 'href', 'hreflang', 'hspace', 'icon', 'id', 'inputmode',
      'ismap', 'keytype', 'label', 'leftspacing', 'lang', 'list', 'longdesc',
      'loop', 'loopcount', 'loopend', 'loopstart', 'low', 'lowsrc', 'max',
      'maxlength', 'media', 'method', 'min', 'multiple', 'name', 'nohref',
      'noshade', 'nowrap', 'open', 'optimum', 'pattern', 'ping', 'point-size',
      'poster', 'pqg', 'preload', 'prompt', 'radiogroup', 'readonly', 'rel',
      'repeat-max', 'repeat-min', 'replace', 'required', 'rev', 'rightspacing',
      'rows', 'rowspan', 'rules', 'scope', 'selected', 'shape', 'size', 'span',
      'src', 'start', 'step', 'summary', 'suppress', 'tabindex', 'target',
      'template', 'title', 'toppadding', 'type', 'unselectable', 'usemap',
      'urn', 'valign', 'value', 'variable', 'volume', 'vspace', 'vrml',
      'width', 'wrap', 'xml:lang'])

    unacceptable_elements_with_end_tag = set(['script', 'applet', 'style'])

    acceptable_css_properties = set(['azimuth', 'background-color',
      'border-bottom-color', 'border-collapse', 'border-color',
      'border-left-color', 'border-right-color', 'border-top-color', 'clear',
      'color', 'cursor', 'direction', 'display', 'elevation', 'float', 'font',
      'font-family', 'font-size', 'font-style', 'font-variant', 'font-weight',
      'height', 'letter-spacing', 'line-height', 'overflow', 'pause',
      'pause-after', 'pause-before', 'pitch', 'pitch-range', 'richness',
      'speak', 'speak-header', 'speak-numeral', 'speak-punctuation',
      'speech-rate', 'stress', 'text-align', 'text-decoration', 'text-indent',
      'unicode-bidi', 'vertical-align', 'voice-family', 'volume',
      'white-space', 'width'])

    # survey of common keywords found in feeds
    acceptable_css_keywords = set(['auto', 'aqua', 'black', 'block', 'blue',
      'bold', 'both', 'bottom', 'brown', 'center', 'collapse', 'dashed',
      'dotted', 'fuchsia', 'gray', 'green', '!important', 'italic', 'left',
      'lime', 'maroon', 'medium', 'none', 'navy', 'normal', 'nowrap', 'olive',
      'pointer', 'purple', 'red', 'right', 'solid', 'silver', 'teal', 'top',
      'transparent', 'underline', 'white', 'yellow'])

    valid_css_values = re.compile('^(#[0-9a-f]+|rgb\(\d+%?,\d*%?,?\d*%?\)?|' +
      '\d{0,2}\.?\d{0,2}(cm|em|ex|in|mm|pc|pt|px|%|,|\))?)$')

    mathml_elements = set(['annotation', 'annotation-xml', 'maction', 'math',
      'merror', 'mfenced', 'mfrac', 'mi', 'mmultiscripts', 'mn', 'mo', 'mover', 'mpadded',
      'mphantom', 'mprescripts', 'mroot', 'mrow', 'mspace', 'msqrt', 'mstyle',
      'msub', 'msubsup', 'msup', 'mtable', 'mtd', 'mtext', 'mtr', 'munder',
      'munderover', 'none', 'semantics'])

    mathml_attributes = set(['actiontype', 'align', 'columnalign', 'columnalign',
      'columnalign', 'close', 'columnlines', 'columnspacing', 'columnspan', 'depth',
      'display', 'displaystyle', 'encoding', 'equalcolumns', 'equalrows',
      'fence', 'fontstyle', 'fontweight', 'frame', 'height', 'linethickness',
      'lspace', 'mathbackground', 'mathcolor', 'mathvariant', 'mathvariant',
      'maxsize', 'minsize', 'open', 'other', 'rowalign', 'rowalign', 'rowalign',
      'rowlines', 'rowspacing', 'rowspan', 'rspace', 'scriptlevel', 'selection',
      'separator', 'separators', 'stretchy', 'width', 'width', 'xlink:href',
      'xlink:show', 'xlink:type', 'xmlns', 'xmlns:xlink'])

    # svgtiny - foreignObject + linearGradient + radialGradient + stop
    svg_elements = set(['a', 'animate', 'animateColor', 'animateMotion',
      'animateTransform', 'circle', 'defs', 'desc', 'ellipse', 'foreignObject',
      'font-face', 'font-face-name', 'font-face-src', 'g', 'glyph', 'hkern',
      'linearGradient', 'line', 'marker', 'metadata', 'missing-glyph', 'mpath',
      'path', 'polygon', 'polyline', 'radialGradient', 'rect', 'set', 'stop',
      'svg', 'switch', 'text', 'title', 'tspan', 'use'])

    # svgtiny + class + opacity + offset + xmlns + xmlns:xlink
    svg_attributes = set(['accent-height', 'accumulate', 'additive', 'alphabetic',
       'arabic-form', 'ascent', 'attributeName', 'attributeType',
       'baseProfile', 'bbox', 'begin', 'by', 'calcMode', 'cap-height',
       'class', 'color', 'color-rendering', 'content', 'cx', 'cy', 'd', 'dx',
       'dy', 'descent', 'display', 'dur', 'end', 'fill', 'fill-opacity',
       'fill-rule', 'font-family', 'font-size', 'font-stretch', 'font-style',
       'font-variant', 'font-weight', 'from', 'fx', 'fy', 'g1', 'g2',
       'glyph-name', 'gradientUnits', 'hanging', 'height', 'horiz-adv-x',
       'horiz-origin-x', 'id', 'ideographic', 'k', 'keyPoints', 'keySplines',
       'keyTimes', 'lang', 'mathematical', 'marker-end', 'marker-mid',
       'marker-start', 'markerHeight', 'markerUnits', 'markerWidth', 'max',
       'min', 'name', 'offset', 'opacity', 'orient', 'origin',
       'overline-position', 'overline-thickness', 'panose-1', 'path',
       'pathLength', 'points', 'preserveAspectRatio', 'r', 'refX', 'refY',
       'repeatCount', 'repeatDur', 'requiredExtensions', 'requiredFeatures',
       'restart', 'rotate', 'rx', 'ry', 'slope', 'stemh', 'stemv',
       'stop-color', 'stop-opacity', 'strikethrough-position',
       'strikethrough-thickness', 'stroke', 'stroke-dasharray',
       'stroke-dashoffset', 'stroke-linecap', 'stroke-linejoin',
       'stroke-miterlimit', 'stroke-opacity', 'stroke-width', 'systemLanguage',
       'target', 'text-anchor', 'to', 'transform', 'type', 'u1', 'u2',
       'underline-position', 'underline-thickness', 'unicode', 'unicode-range',
       'units-per-em', 'values', 'version', 'viewBox', 'visibility', 'width',
       'widths', 'x', 'x-height', 'x1', 'x2', 'xlink:actuate', 'xlink:arcrole',
       'xlink:href', 'xlink:role', 'xlink:show', 'xlink:title', 'xlink:type',
       'xml:base', 'xml:lang', 'xml:space', 'xmlns', 'xmlns:xlink', 'y', 'y1',
       'y2', 'zoomAndPan'])

    svg_attr_map = None
    svg_elem_map = None

    acceptable_svg_properties = set([ 'fill', 'fill-opacity', 'fill-rule',
      'stroke', 'stroke-width', 'stroke-linecap', 'stroke-linejoin',
      'stroke-opacity'])

    def reset(self):
        _BaseHTMLProcessor.reset(self)
        self.unacceptablestack = 0
        self.mathmlOK = 0
        self.svgOK = 0

    def unknown_starttag(self, tag, attrs):
        acceptable_attributes = self.acceptable_attributes
        keymap = {}
        if not tag in self.acceptable_elements or self.svgOK:
            if tag in self.unacceptable_elements_with_end_tag:
                self.unacceptablestack += 1

            # add implicit namespaces to html5 inline svg/mathml
            if self._type.endswith('html'):
                if not dict(attrs).get('xmlns'):
                    if tag=='svg':
                        attrs.append( ('xmlns','http://www.w3.org/2000/svg') )
                    if tag=='math':
                        attrs.append( ('xmlns','http://www.w3.org/1998/Math/MathML') )

            # not otherwise acceptable, perhaps it is MathML or SVG?
            if tag=='math' and ('xmlns','http://www.w3.org/1998/Math/MathML') in attrs:
                self.mathmlOK += 1
            if tag=='svg' and ('xmlns','http://www.w3.org/2000/svg') in attrs:
                self.svgOK += 1

            # chose acceptable attributes based on tag class, else bail
            if  self.mathmlOK and tag in self.mathml_elements:
                acceptable_attributes = self.mathml_attributes
            elif self.svgOK and tag in self.svg_elements:
                # for most vocabularies, lowercasing is a good idea.  Many
                # svg elements, however, are camel case
                if not self.svg_attr_map:
                    lower=[attr.lower() for attr in self.svg_attributes]
                    mix=[a for a in self.svg_attributes if a not in lower]
                    self.svg_attributes = lower
                    self.svg_attr_map = dict([(a.lower(),a) for a in mix])

                    lower=[attr.lower() for attr in self.svg_elements]
                    mix=[a for a in self.svg_elements if a not in lower]
                    self.svg_elements = lower
                    self.svg_elem_map = dict([(a.lower(),a) for a in mix])
                acceptable_attributes = self.svg_attributes
                tag = self.svg_elem_map.get(tag,tag)
                keymap = self.svg_attr_map
            elif not tag in self.acceptable_elements:
                return

        # declare xlink namespace, if needed
        if self.mathmlOK or self.svgOK:
            if filter(lambda (n,v): n.startswith('xlink:'),attrs):
                if not ('xmlns:xlink','http://www.w3.org/1999/xlink') in attrs:
                    attrs.append(('xmlns:xlink','http://www.w3.org/1999/xlink'))

        clean_attrs = []
        for key, value in self.normalize_attrs(attrs):
            if key in acceptable_attributes:
                key=keymap.get(key,key)
                # make sure the uri uses an acceptable uri scheme
                if key == u'href':
                    value = _makeSafeAbsoluteURI(value)
                clean_attrs.append((key,value))
            elif key=='style':
                clean_value = self.sanitize_style(value)
                if clean_value:
                    clean_attrs.append((key,clean_value))
        _BaseHTMLProcessor.unknown_starttag(self, tag, clean_attrs)

    def unknown_endtag(self, tag):
        if not tag in self.acceptable_elements:
            if tag in self.unacceptable_elements_with_end_tag:
                self.unacceptablestack -= 1
            if self.mathmlOK and tag in self.mathml_elements:
                if tag == 'math' and self.mathmlOK:
                    self.mathmlOK -= 1
            elif self.svgOK and tag in self.svg_elements:
                tag = self.svg_elem_map.get(tag,tag)
                if tag == 'svg' and self.svgOK:
                    self.svgOK -= 1
            else:
                return
        _BaseHTMLProcessor.unknown_endtag(self, tag)

    def handle_pi(self, text):
        pass

    def handle_decl(self, text):
        pass

    def handle_data(self, text):
        if not self.unacceptablestack:
            _BaseHTMLProcessor.handle_data(self, text)

    def sanitize_style(self, style):
        # disallow urls
        style=re.compile('url\s*\(\s*[^\s)]+?\s*\)\s*').sub(' ',style)

        # gauntlet
        if not re.match("""^([:,;#%.\sa-zA-Z0-9!]|\w-\w|'[\s\w]+'|"[\s\w]+"|\([\d,\s]+\))*$""", style):
            return ''
        # This replaced a regexp that used re.match and was prone to pathological back-tracking.
        if re.sub("\s*[-\w]+\s*:\s*[^:;]*;?", '', style).strip():
            return ''

        clean = []
        for prop,value in re.findall("([-\w]+)\s*:\s*([^:;]*)",style):
            if not value:
                continue
            if prop.lower() in self.acceptable_css_properties:
                clean.append(prop + ': ' + value + ';')
            elif prop.split('-')[0].lower() in ['background','border','margin','padding']:
                for keyword in value.split():
                    if not keyword in self.acceptable_css_keywords and \
                        not self.valid_css_values.match(keyword):
                        break
                else:
                    clean.append(prop + ': ' + value + ';')
            elif self.svgOK and prop.lower() in self.acceptable_svg_properties:
                clean.append(prop + ': ' + value + ';')

        return ' '.join(clean)

    def parse_comment(self, i, report=1):
        ret = _BaseHTMLProcessor.parse_comment(self, i, report)
        if ret >= 0:
            return ret
        # if ret == -1, this may be a malicious attempt to circumvent
        # sanitization, or a page-destroying unclosed comment
        match = re.compile(r'--[^>]*>').search(self.rawdata, i+4)
        if match:
            return match.end()
        # unclosed comment; deliberately fail to handle_data()
        return len(self.rawdata)


def _sanitizeHTML(htmlSource, encoding, _type):
    if not _SGML_AVAILABLE:
        return htmlSource
    p = _HTMLSanitizer(encoding, _type)
    htmlSource = htmlSource.replace('<![CDATA[', '&lt;![CDATA[')
    p.feed(htmlSource)
    data = p.output()
    data = data.strip().replace('\r\n', '\n')
    return data

class _FeedURLHandler(urllib2.HTTPDigestAuthHandler, urllib2.HTTPRedirectHandler, urllib2.HTTPDefaultErrorHandler):
    def http_error_default(self, req, fp, code, msg, headers):
        # The default implementation just raises HTTPError.
        # Forget that.
        fp.status = code
        return fp

    def http_error_301(self, req, fp, code, msg, hdrs):
        result = urllib2.HTTPRedirectHandler.http_error_301(self, req, fp,
                                                            code, msg, hdrs)
        result.status = code
        result.newurl = result.geturl()
        return result
    # The default implementations in urllib2.HTTPRedirectHandler
    # are identical, so hardcoding a http_error_301 call above
    # won't affect anything
    http_error_300 = http_error_301
    http_error_302 = http_error_301
    http_error_303 = http_error_301
    http_error_307 = http_error_301

    def http_error_401(self, req, fp, code, msg, headers):
        # Check if
        # - server requires digest auth, AND
        # - we tried (unsuccessfully) with basic auth, AND
        # If all conditions hold, parse authentication information
        # out of the Authorization header we sent the first time
        # (for the username and password) and the WWW-Authenticate
        # header the server sent back (for the realm) and retry
        # the request with the appropriate digest auth headers instead.
        # This evil genius hack has been brought to you by Aaron Swartz.
        host = urlparse.urlparse(req.get_full_url())[1]
        if base64 is None or 'Authorization' not in req.headers \
                          or 'WWW-Authenticate' not in headers:
            return self.http_error_default(req, fp, code, msg, headers)
        auth = _base64decode(req.headers['Authorization'].split(' ')[1])
        user, passw = auth.split(':')
        realm = re.findall('realm="([^"]*)"', headers['WWW-Authenticate'])[0]
        self.add_password(realm, host, user, passw)
        retry = self.http_error_auth_reqed('www-authenticate', host, req, headers)
        self.reset_retry_count()
        return retry

def _open_resource(url_file_stream_or_string, etag, modified, agent, referrer, handlers, request_headers):
    """URL, filename, or string --> stream

    This function lets you define parsers that take any input source
    (URL, pathname to local or network file, or actual data as a string)
    and deal with it in a uniform manner.  Returned object is guaranteed
    to have all the basic stdio read methods (read, readline, readlines).
    Just .close() the object when you're done with it.

    If the etag argument is supplied, it will be used as the value of an
    If-None-Match request header.

    If the modified argument is supplied, it can be a tuple of 9 integers
    (as returned by gmtime() in the standard Python time module) or a date
    string in any format supported by feedparser. Regardless, it MUST
    be in GMT (Greenwich Mean Time). It will be reformatted into an
    RFC 1123-compliant date and used as the value of an If-Modified-Since
    request header.

    If the agent argument is supplied, it will be used as the value of a
    User-Agent request header.

    If the referrer argument is supplied, it will be used as the value of a
    Referer[sic] request header.

    If handlers is supplied, it is a list of handlers used to build a
    urllib2 opener.

    if request_headers is supplied it is a dictionary of HTTP request headers
    that will override the values generated by FeedParser.
    """

    if hasattr(url_file_stream_or_string, 'read'):
        return url_file_stream_or_string

    if isinstance(url_file_stream_or_string, basestring) \
       and urlparse.urlparse(url_file_stream_or_string)[0] in ('http', 'https', 'ftp', 'file', 'feed'):
        # Deal with the feed URI scheme
        if url_file_stream_or_string.startswith('feed:http'):
            url_file_stream_or_string = url_file_stream_or_string[5:]
        elif url_file_stream_or_string.startswith('feed:'):
            url_file_stream_or_string = 'http:' + url_file_stream_or_string[5:]
        if not agent:
            agent = USER_AGENT
        # Test for inline user:password credentials for HTTP basic auth
        auth = None
        if base64 and not url_file_stream_or_string.startswith('ftp:'):
            urltype, rest = urllib.splittype(url_file_stream_or_string)
            realhost, rest = urllib.splithost(rest)
            if realhost:
                user_passwd, realhost = urllib.splituser(realhost)
                if user_passwd:
                    url_file_stream_or_string = '%s://%s%s' % (urltype, realhost, rest)
                    auth = base64.standard_b64encode(user_passwd).strip()

        # iri support
        if isinstance(url_file_stream_or_string, unicode):
            url_file_stream_or_string = _convert_to_idn(url_file_stream_or_string)

        # try to open with urllib2 (to use optional headers)
        request = _build_urllib2_request(url_file_stream_or_string, agent, etag, modified, referrer, auth, request_headers)
        opener = urllib2.build_opener(*tuple(handlers + [_FeedURLHandler()]))
        opener.addheaders = [] # RMK - must clear so we only send our custom User-Agent
        try:
            return opener.open(request)
        finally:
            opener.close() # JohnD

    # try to open with native open function (if url_file_stream_or_string is a filename)
    try:
        return open(url_file_stream_or_string, 'rb')
    except (IOError, UnicodeEncodeError, TypeError):
        # if url_file_stream_or_string is a unicode object that
        # cannot be converted to the encoding returned by
        # sys.getfilesystemencoding(), a UnicodeEncodeError
        # will be thrown
        # If url_file_stream_or_string is a string that contains NULL
        # (such as an XML document encoded in UTF-32), TypeError will
        # be thrown.
        pass

    # treat url_file_stream_or_string as string
    if isinstance(url_file_stream_or_string, unicode):
        return _StringIO(url_file_stream_or_string.encode('utf-8'))
    return _StringIO(url_file_stream_or_string)

def _convert_to_idn(url):
    """Convert a URL to IDN notation"""
    # this function should only be called with a unicode string
    # strategy: if the host cannot be encoded in ascii, then
    # it'll be necessary to encode it in idn form
    parts = list(urlparse.urlsplit(url))
    try:
        parts[1].encode('ascii')
    except UnicodeEncodeError:
        # the url needs to be converted to idn notation
        host = parts[1].rsplit(':', 1)
        newhost = []
        port = u''
        if len(host) == 2:
            port = host.pop()
        for h in host[0].split('.'):
            newhost.append(h.encode('idna').decode('utf-8'))
        parts[1] = '.'.join(newhost)
        if port:
            parts[1] += ':' + port
        return urlparse.urlunsplit(parts)
    else:
        return url

def _build_urllib2_request(url, agent, etag, modified, referrer, auth, request_headers):
    request = urllib2.Request(url)
    request.add_header('User-Agent', agent)
    if etag:
        request.add_header('If-None-Match', etag)
    if isinstance(modified, basestring):
        modified = _parse_date(modified)
    elif isinstance(modified, datetime.datetime):
        modified = modified.utctimetuple()
    if modified:
        # format into an RFC 1123-compliant timestamp. We can't use
        # time.strftime() since the %a and %b directives can be affected
        # by the current locale, but RFC 2616 states that dates must be
        # in English.
        short_weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        request.add_header('If-Modified-Since', '%s, %02d %s %04d %02d:%02d:%02d GMT' % (short_weekdays[modified[6]], modified[2], months[modified[1] - 1], modified[0], modified[3], modified[4], modified[5]))
    if referrer:
        request.add_header('Referer', referrer)
    if gzip and zlib:
        request.add_header('Accept-encoding', 'gzip, deflate')
    elif gzip:
        request.add_header('Accept-encoding', 'gzip')
    elif zlib:
        request.add_header('Accept-encoding', 'deflate')
    else:
        request.add_header('Accept-encoding', '')
    if auth:
        request.add_header('Authorization', 'Basic %s' % auth)
    if ACCEPT_HEADER:
        request.add_header('Accept', ACCEPT_HEADER)
    # use this for whatever -- cookies, special headers, etc
    # [('Cookie','Something'),('x-special-header','Another Value')]
    for header_name, header_value in request_headers.items():
        request.add_header(header_name, header_value)
    request.add_header('A-IM', 'feed') # RFC 3229 support
    return request

def _parse_psc_chapter_start(start):
    FORMAT = r'^((\d{2}):)?(\d{2}):(\d{2})(\.(\d{3}))?$'

    m = re.compile(FORMAT).match(start)
    if m is None:
        return None

    _, h, m, s, _, ms = m.groups()
    h, m, s, ms = (int(h or 0), int(m), int(s), int(ms or 0))
    return datetime.timedelta(0, h*60*60 + m*60 + s, ms*1000)

_date_handlers = []
def registerDateHandler(func):
    '''Register a date handler function (takes string, returns 9-tuple date in GMT)'''
    _date_handlers.insert(0, func)

# ISO-8601 date parsing routines written by Fazal Majid.
# The ISO 8601 standard is very convoluted and irregular - a full ISO 8601
# parser is beyond the scope of feedparser and would be a worthwhile addition
# to the Python library.
# A single regular expression cannot parse ISO 8601 date formats into groups
# as the standard is highly irregular (for instance is 030104 2003-01-04 or
# 0301-04-01), so we use templates instead.
# Please note the order in templates is significant because we need a
# greedy match.
_iso8601_tmpl = ['YYYY-?MM-?DD', 'YYYY-0MM?-?DD', 'YYYY-MM', 'YYYY-?OOO',
                'YY-?MM-?DD', 'YY-?OOO', 'YYYY',
                '-YY-?MM', '-OOO', '-YY',
                '--MM-?DD', '--MM',
                '---DD',
                'CC', '']
_iso8601_re = [
    tmpl.replace(
    'YYYY', r'(?P<year>\d{4})').replace(
    'YY', r'(?P<year>\d\d)').replace(
    'MM', r'(?P<month>[01]\d)').replace(
    'DD', r'(?P<day>[0123]\d)').replace(
    'OOO', r'(?P<ordinal>[0123]\d\d)').replace(
    'CC', r'(?P<century>\d\d$)')
    + r'(T?(?P<hour>\d{2}):(?P<minute>\d{2})'
    + r'(:(?P<second>\d{2}))?'
    + r'(\.(?P<fracsecond>\d+))?'
    + r'(?P<tz>[+-](?P<tzhour>\d{2})(:(?P<tzmin>\d{2}))?|Z)?)?'
    for tmpl in _iso8601_tmpl]
try:
    del tmpl
except NameError:
    pass
_iso8601_matches = [re.compile(regex).match for regex in _iso8601_re]
try:
    del regex
except NameError:
    pass
    
def _parse_date_iso8601(dateString):
    '''Parse a variety of ISO-8601-compatible formats like 20040105'''
    m = None
    for _iso8601_match in _iso8601_matches:
        m = _iso8601_match(dateString)
        if m:
            break
    if not m:
        return
    if m.span() == (0, 0):
        return
    params = m.groupdict()
    ordinal = params.get('ordinal', 0)
    if ordinal:
        ordinal = int(ordinal)
    else:
        ordinal = 0
    year = params.get('year', '--')
    if not year or year == '--':
        year = time.gmtime()[0]
    elif len(year) == 2:
        # ISO 8601 assumes current century, i.e. 93 -> 2093, NOT 1993
        year = 100 * int(time.gmtime()[0] / 100) + int(year)
    else:
        year = int(year)
    month = params.get('month', '-')
    if not month or month == '-':
        # ordinals are NOT normalized by mktime, we simulate them
        # by setting month=1, day=ordinal
        if ordinal:
            month = 1
        else:
            month = time.gmtime()[1]
    month = int(month)
    day = params.get('day', 0)
    if not day:
        # see above
        if ordinal:
            day = ordinal
        elif params.get('century', 0) or \
                 params.get('year', 0) or params.get('month', 0):
            day = 1
        else:
            day = time.gmtime()[2]
    else:
        day = int(day)
    # special case of the century - is the first year of the 21st century
    # 2000 or 2001 ? The debate goes on...
    if 'century' in params:
        year = (int(params['century']) - 1) * 100 + 1
    # in ISO 8601 most fields are optional
    for field in ['hour', 'minute', 'second', 'tzhour', 'tzmin']:
        if not params.get(field, None):
            params[field] = 0
    hour = int(params.get('hour', 0))
    minute = int(params.get('minute', 0))
    second = int(float(params.get('second', 0)))
    # weekday is normalized by mktime(), we can ignore it
    weekday = 0
    daylight_savings_flag = -1
    tm = [year, month, day, hour, minute, second, weekday,
          ordinal, daylight_savings_flag]
    # ISO 8601 time zone adjustments
    tz = params.get('tz')
    if tz and tz != 'Z':
        if tz[0] == '-':
            tm[3] += int(params.get('tzhour', 0))
            tm[4] += int(params.get('tzmin', 0))
        elif tz[0] == '+':
            tm[3] -= int(params.get('tzhour', 0))
            tm[4] -= int(params.get('tzmin', 0))
        else:
            return None
    # Python's time.mktime() is a wrapper around the ANSI C mktime(3c)
    # which is guaranteed to normalize d/m/y/h/m/s.
    # Many implementations have bugs, but we'll pretend they don't.
    return time.localtime(time.mktime(tuple(tm)))
registerDateHandler(_parse_date_iso8601)

# 8-bit date handling routines written by ytrewq1.
_korean_year  = u'\ub144' # b3e2 in euc-kr
_korean_month = u'\uc6d4' # bff9 in euc-kr
_korean_day   = u'\uc77c' # c0cf in euc-kr
_korean_am    = u'\uc624\uc804' # bfc0 c0fc in euc-kr
_korean_pm    = u'\uc624\ud6c4' # bfc0 c8c4 in euc-kr

_korean_onblog_date_re = \
    re.compile('(\d{4})%s\s+(\d{2})%s\s+(\d{2})%s\s+(\d{2}):(\d{2}):(\d{2})' % \
               (_korean_year, _korean_month, _korean_day))
_korean_nate_date_re = \
    re.compile(u'(\d{4})-(\d{2})-(\d{2})\s+(%s|%s)\s+(\d{,2}):(\d{,2}):(\d{,2})' % \
               (_korean_am, _korean_pm))
def _parse_date_onblog(dateString):
    '''Parse a string according to the OnBlog 8-bit date format'''
    m = _korean_onblog_date_re.match(dateString)
    if not m:
        return
    w3dtfdate = '%(year)s-%(month)s-%(day)sT%(hour)s:%(minute)s:%(second)s%(zonediff)s' % \
                {'year': m.group(1), 'month': m.group(2), 'day': m.group(3),\
                 'hour': m.group(4), 'minute': m.group(5), 'second': m.group(6),\
                 'zonediff': '+09:00'}
    return _parse_date_w3dtf(w3dtfdate)
registerDateHandler(_parse_date_onblog)

def _parse_date_nate(dateString):
    '''Parse a string according to the Nate 8-bit date format'''
    m = _korean_nate_date_re.match(dateString)
    if not m:
        return
    hour = int(m.group(5))
    ampm = m.group(4)
    if (ampm == _korean_pm):
        hour += 12
    hour = str(hour)
    if len(hour) == 1:
        hour = '0' + hour
    w3dtfdate = '%(year)s-%(month)s-%(day)sT%(hour)s:%(minute)s:%(second)s%(zonediff)s' % \
                {'year': m.group(1), 'month': m.group(2), 'day': m.group(3),\
                 'hour': hour, 'minute': m.group(6), 'second': m.group(7),\
                 'zonediff': '+09:00'}
    return _parse_date_w3dtf(w3dtfdate)
registerDateHandler(_parse_date_nate)

# Unicode strings for Greek date strings
_greek_months = \
  { \
   u'\u0399\u03b1\u03bd': u'Jan',       # c9e1ed in iso-8859-7
   u'\u03a6\u03b5\u03b2': u'Feb',       # d6e5e2 in iso-8859-7
   u'\u039c\u03ac\u03ce': u'Mar',       # ccdcfe in iso-8859-7
   u'\u039c\u03b1\u03ce': u'Mar',       # cce1fe in iso-8859-7
   u'\u0391\u03c0\u03c1': u'Apr',       # c1f0f1 in iso-8859-7
   u'\u039c\u03ac\u03b9': u'May',       # ccdce9 in iso-8859-7
   u'\u039c\u03b1\u03ca': u'May',       # cce1fa in iso-8859-7
   u'\u039c\u03b1\u03b9': u'May',       # cce1e9 in iso-8859-7
   u'\u0399\u03bf\u03cd\u03bd': u'Jun', # c9effded in iso-8859-7
   u'\u0399\u03bf\u03bd': u'Jun',       # c9efed in iso-8859-7
   u'\u0399\u03bf\u03cd\u03bb': u'Jul', # c9effdeb in iso-8859-7
   u'\u0399\u03bf\u03bb': u'Jul',       # c9f9eb in iso-8859-7
   u'\u0391\u03cd\u03b3': u'Aug',       # c1fde3 in iso-8859-7
   u'\u0391\u03c5\u03b3': u'Aug',       # c1f5e3 in iso-8859-7
   u'\u03a3\u03b5\u03c0': u'Sep',       # d3e5f0 in iso-8859-7
   u'\u039f\u03ba\u03c4': u'Oct',       # cfeaf4 in iso-8859-7
   u'\u039d\u03bf\u03ad': u'Nov',       # cdefdd in iso-8859-7
   u'\u039d\u03bf\u03b5': u'Nov',       # cdefe5 in iso-8859-7
   u'\u0394\u03b5\u03ba': u'Dec',       # c4e5ea in iso-8859-7
  }

_greek_wdays = \
  { \
   u'\u039a\u03c5\u03c1': u'Sun', # caf5f1 in iso-8859-7
   u'\u0394\u03b5\u03c5': u'Mon', # c4e5f5 in iso-8859-7
   u'\u03a4\u03c1\u03b9': u'Tue', # d4f1e9 in iso-8859-7
   u'\u03a4\u03b5\u03c4': u'Wed', # d4e5f4 in iso-8859-7
   u'\u03a0\u03b5\u03bc': u'Thu', # d0e5ec in iso-8859-7
   u'\u03a0\u03b1\u03c1': u'Fri', # d0e1f1 in iso-8859-7
   u'\u03a3\u03b1\u03b2': u'Sat', # d3e1e2 in iso-8859-7
  }

_greek_date_format_re = \
    re.compile(u'([^,]+),\s+(\d{2})\s+([^\s]+)\s+(\d{4})\s+(\d{2}):(\d{2}):(\d{2})\s+([^\s]+)')

def _parse_date_greek(dateString):
    '''Parse a string according to a Greek 8-bit date format.'''
    m = _greek_date_format_re.match(dateString)
    if not m:
        return
    wday = _greek_wdays[m.group(1)]
    month = _greek_months[m.group(3)]
    rfc822date = '%(wday)s, %(day)s %(month)s %(year)s %(hour)s:%(minute)s:%(second)s %(zonediff)s' % \
                 {'wday': wday, 'day': m.group(2), 'month': month, 'year': m.group(4),\
                  'hour': m.group(5), 'minute': m.group(6), 'second': m.group(7),\
                  'zonediff': m.group(8)}
    return _parse_date_rfc822(rfc822date)
registerDateHandler(_parse_date_greek)

# Unicode strings for Hungarian date strings
_hungarian_months = \
  { \
    u'janu\u00e1r':   u'01',  # e1 in iso-8859-2
    u'febru\u00e1ri': u'02',  # e1 in iso-8859-2
    u'm\u00e1rcius':  u'03',  # e1 in iso-8859-2
    u'\u00e1prilis':  u'04',  # e1 in iso-8859-2
    u'm\u00e1ujus':   u'05',  # e1 in iso-8859-2
    u'j\u00fanius':   u'06',  # fa in iso-8859-2
    u'j\u00falius':   u'07',  # fa in iso-8859-2
    u'augusztus':     u'08',
    u'szeptember':    u'09',
    u'okt\u00f3ber':  u'10',  # f3 in iso-8859-2
    u'november':      u'11',
    u'december':      u'12',
  }

_hungarian_date_format_re = \
  re.compile(u'(\d{4})-([^-]+)-(\d{,2})T(\d{,2}):(\d{2})((\+|-)(\d{,2}:\d{2}))')

def _parse_date_hungarian(dateString):
    '''Parse a string according to a Hungarian 8-bit date format.'''
    m = _hungarian_date_format_re.match(dateString)
    if not m or m.group(2) not in _hungarian_months:
        return None
    month = _hungarian_months[m.group(2)]
    day = m.group(3)
    if len(day) == 1:
        day = '0' + day
    hour = m.group(4)
    if len(hour) == 1:
        hour = '0' + hour
    w3dtfdate = '%(year)s-%(month)s-%(day)sT%(hour)s:%(minute)s%(zonediff)s' % \
                {'year': m.group(1), 'month': month, 'day': day,\
                 'hour': hour, 'minute': m.group(5),\
                 'zonediff': m.group(6)}
    return _parse_date_w3dtf(w3dtfdate)
registerDateHandler(_parse_date_hungarian)

timezonenames = {
    'ut': 0, 'gmt': 0, 'z': 0,
    'adt': -3, 'ast': -4, 'at': -4,
    'edt': -4, 'est': -5, 'et': -5,
    'cdt': -5, 'cst': -6, 'ct': -6,
    'mdt': -6, 'mst': -7, 'mt': -7,
    'pdt': -7, 'pst': -8, 'pt': -8,
    'a': -1, 'n': 1,
    'm': -12, 'y': 12,
}
# W3 date and time format parser
# http://www.w3.org/TR/NOTE-datetime
# Also supports MSSQL-style datetimes as defined at:
# http://msdn.microsoft.com/en-us/library/ms186724.aspx
# (basically, allow a space as a date/time/timezone separator)
def _parse_date_w3dtf(datestr):
    if not datestr.strip():
        return None
    parts = datestr.lower().split('t')
    if len(parts) == 1:
        # This may be a date only, or may be an MSSQL-style date
        parts = parts[0].split()
        if len(parts) == 1:
            # Treat this as a date only
            parts.append('00:00:00z')
    elif len(parts) > 2:
        return None
    date = parts[0].split('-', 2) 
    if not date or len(date[0]) != 4:
        return None
    # Ensure that `date` has 3 elements. Using '1' sets the default
    # month to January and the default day to the 1st of the month.
    date.extend(['1'] * (3 - len(date)))
    try:
        year, month, day = [int(i) for i in date]
    except ValueError:
        # `date` may have more than 3 elements or may contain
        # non-integer strings.
        return None
    if parts[1].endswith('z'):
        parts[1] = parts[1][:-1]
        parts.append('z')
    # Append the numeric timezone offset, if any, to parts.
    # If this is an MSSQL-style date then parts[2] already contains
    # the timezone information, so `append()` will not affect it.
    # Add 1 to each value so that if `find()` returns -1 it will be
    # treated as False.
    loc = parts[1].find('-') + 1 or parts[1].find('+') + 1 or len(parts[1]) + 1
    loc = loc - 1
    parts.append(parts[1][loc:])
    parts[1] = parts[1][:loc]
    time = parts[1].split(':', 2)
    # Ensure that time has 3 elements. Using '0' means that the
    # minutes and seconds, if missing, will default to 0.
    time.extend(['0'] * (3 - len(time)))
    tzhour = 0
    tzmin = 0
    if parts[2][:1] in ('-', '+'):
        try:
            tzhour = int(parts[2][1:3])
            tzmin = int(parts[2][4:])
        except ValueError:
            return None
        if parts[2].startswith('-'):
            tzhour = tzhour * -1
            tzmin = tzmin * -1
    else:
        tzhour = timezonenames.get(parts[2], 0)
    try:
        hour, minute, second = [int(float(i)) for i in time]
    except ValueError:
        return None
    # Create the datetime object and timezone delta objects
    try:
        stamp = datetime.datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None
    delta = datetime.timedelta(0, 0, 0, 0, tzmin, tzhour)
    # Return the date and timestamp in a UTC 9-tuple
    try:
        return (stamp - delta).utctimetuple()
    except (OverflowError, ValueError):
        # IronPython throws ValueErrors instead of OverflowErrors
        return None

registerDateHandler(_parse_date_w3dtf)

def _parse_date_rfc822(date):
    """Parse RFC 822 dates and times
    http://tools.ietf.org/html/rfc822#section-5

    There are some formatting differences that are accounted for:
    1. Years may be two or four digits.
    2. The month and day can be swapped.
    3. Additional timezone names are supported.
    4. A default time and timezone are assumed if only a date is present.
    """
    daynames = set(['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'])
    months = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    }

    parts = date.lower().split()
    if len(parts) < 5:
        # Assume that the time and timezone are missing
        parts.extend(('00:00:00', '0000'))
    # Remove the day name
    if parts[0][:3] in daynames:
        parts = parts[1:]
    if len(parts) < 5:
        # If there are still fewer than five parts, there's not enough
        # information to interpret this
        return None
    try:
        day = int(parts[0])
    except ValueError:
        # Check if the day and month are swapped
        if months.get(parts[0][:3]):
            try:
                day = int(parts[1])
            except ValueError:
                return None
            else:
                parts[1] = parts[0]
        else:
            return None
    month = months.get(parts[1][:3])
    if not month:
        return None
    try:
        year = int(parts[2])
    except ValueError:
        return None
    # Normalize two-digit years:
    # Anything in the 90's is interpreted as 1990 and on
    # Anything 89 or less is interpreted as 2089 or before
    if len(parts[2]) <= 2:
        year += (1900, 2000)[year < 90]
    timeparts = parts[3].split(':')
    timeparts = timeparts + ([0] * (3 - len(timeparts)))
    try:
        (hour, minute, second) = map(int, timeparts)
    except ValueError:
        return None
    tzhour = 0
    tzmin = 0
    # Strip 'Etc/' from the timezone
    if parts[4].startswith('etc/'):
        parts[4] = parts[4][4:]
    # Normalize timezones that start with 'gmt':
    # GMT-05:00 => -0500
    # GMT => GMT
    if parts[4].startswith('gmt'):
        parts[4] = ''.join(parts[4][3:].split(':')) or 'gmt'
    # Handle timezones like '-0500', '+0500', and 'EST'
    if parts[4] and parts[4][0] in ('-', '+'):
        try:
            tzhour = int(parts[4][1:3])
            tzmin = int(parts[4][3:])
        except ValueError:
            return None
        if parts[4].startswith('-'):
            tzhour = tzhour * -1
            tzmin = tzmin * -1
    else:
        tzhour = timezonenames.get(parts[4], 0)
    # Create the datetime object and timezone delta objects
    try:
        stamp = datetime.datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None
    delta = datetime.timedelta(0, 0, 0, 0, tzmin, tzhour)
    # Return the date and timestamp in a UTC 9-tuple
    try:
        return (stamp - delta).utctimetuple()
    except (OverflowError, ValueError):
        # IronPython throws ValueErrors instead of OverflowErrors
        return None
registerDateHandler(_parse_date_rfc822)

_months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
           'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
def _parse_date_asctime(dt):
    """Parse asctime-style dates"""
    dayname, month, day, remainder = dt.split(None, 3)
    # Convert month and day into zero-padded integers
    month = '%02i ' % (_months.index(month.lower()) + 1)
    day = '%02i ' % (int(day),)
    dt = month + day + remainder
    return time.strptime(dt, '%m %d %H:%M:%S %Y')[:-1] + (0, )
registerDateHandler(_parse_date_asctime)

def _parse_date_perforce(aDateString):
    """parse a date in yyyy/mm/dd hh:mm:ss TTT format"""
    # Fri, 2006/09/15 08:19:53 EDT
    _my_date_pattern = re.compile( \
        r'(\w{,3}), (\d{,4})/(\d{,2})/(\d{2}) (\d{,2}):(\d{2}):(\d{2}) (\w{,3})')

    m = _my_date_pattern.search(aDateString)
    if m is None:
        return None
    dow, year, month, day, hour, minute, second, tz = m.groups()
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    dateString = "%s, %s %s %s %s:%s:%s %s" % (dow, day, months[int(month) - 1], year, hour, minute, second, tz)
    tm = rfc822.parsedate_tz(dateString)
    if tm:
        return time.gmtime(rfc822.mktime_tz(tm))
registerDateHandler(_parse_date_perforce)

def _parse_date(dateString):
    '''Parses a variety of date formats into a 9-tuple in GMT'''
    if not dateString:
        return None
    for handler in _date_handlers:
        try:
            date9tuple = handler(dateString)
        except (KeyError, OverflowError, ValueError):
            continue
        if not date9tuple:
            continue
        if len(date9tuple) != 9:
            continue
        return date9tuple
    return None

# Each marker represents some of the characters of the opening XML
# processing instruction ('<?xm') in the specified encoding.
EBCDIC_MARKER = _l2bytes([0x4C, 0x6F, 0xA7, 0x94])
UTF16BE_MARKER = _l2bytes([0x00, 0x3C, 0x00, 0x3F])
UTF16LE_MARKER = _l2bytes([0x3C, 0x00, 0x3F, 0x00])
UTF32BE_MARKER = _l2bytes([0x00, 0x00, 0x00, 0x3C])
UTF32LE_MARKER = _l2bytes([0x3C, 0x00, 0x00, 0x00])

ZERO_BYTES = _l2bytes([0x00, 0x00])

# Match the opening XML declaration.
# Example: <?xml version="1.0" encoding="utf-8"?>
RE_XML_DECLARATION = re.compile('^<\?xml[^>]*?>')

# Capture the value of the XML processing instruction's encoding attribute.
# Example: <?xml version="1.0" encoding="utf-8"?>
RE_XML_PI_ENCODING = re.compile(_s2bytes('^<\?.*encoding=[\'"](.*?)[\'"].*\?>'))

def convert_to_utf8(http_headers, data):
    '''Detect and convert the character encoding to UTF-8.

    http_headers is a dictionary
    data is a raw string (not Unicode)'''

    # This is so much trickier than it sounds, it's not even funny.
    # According to RFC 3023 ('XML Media Types'), if the HTTP Content-Type
    # is application/xml, application/*+xml,
    # application/xml-external-parsed-entity, or application/xml-dtd,
    # the encoding given in the charset parameter of the HTTP Content-Type
    # takes precedence over the encoding given in the XML prefix within the
    # document, and defaults to 'utf-8' if neither are specified.  But, if
    # the HTTP Content-Type is text/xml, text/*+xml, or
    # text/xml-external-parsed-entity, the encoding given in the XML prefix
    # within the document is ALWAYS IGNORED and only the encoding given in
    # the charset parameter of the HTTP Content-Type header should be
    # respected, and it defaults to 'us-ascii' if not specified.

    # Furthermore, discussion on the atom-syntax mailing list with the
    # author of RFC 3023 leads me to the conclusion that any document
    # served with a Content-Type of text/* and no charset parameter
    # must be treated as us-ascii.  (We now do this.)  And also that it
    # must always be flagged as non-well-formed.  (We now do this too.)

    # If Content-Type is unspecified (input was local file or non-HTTP source)
    # or unrecognized (server just got it totally wrong), then go by the
    # encoding given in the XML prefix of the document and default to
    # 'iso-8859-1' as per the HTTP specification (RFC 2616).

    # Then, assuming we didn't find a character encoding in the HTTP headers
    # (and the HTTP Content-type allowed us to look in the body), we need
    # to sniff the first few bytes of the XML data and try to determine
    # whether the encoding is ASCII-compatible.  Section F of the XML
    # specification shows the way here:
    # http://www.w3.org/TR/REC-xml/#sec-guessing-no-ext-info

    # If the sniffed encoding is not ASCII-compatible, we need to make it
    # ASCII compatible so that we can sniff further into the XML declaration
    # to find the encoding attribute, which will tell us the true encoding.

    # Of course, none of this guarantees that we will be able to parse the
    # feed in the declared character encoding (assuming it was declared
    # correctly, which many are not).  iconv_codec can help a lot;
    # you should definitely install it if you can.
    # http://cjkpython.i18n.org/

    bom_encoding = u''
    xml_encoding = u''
    rfc3023_encoding = u''

    # Look at the first few bytes of the document to guess what
    # its encoding may be. We only need to decode enough of the
    # document that we can use an ASCII-compatible regular
    # expression to search for an XML encoding declaration.
    # The heuristic follows the XML specification, section F:
    # http://www.w3.org/TR/REC-xml/#sec-guessing-no-ext-info
    # Check for BOMs first.
    if data[:4] == codecs.BOM_UTF32_BE:
        bom_encoding = u'utf-32be'
        data = data[4:]
    elif data[:4] == codecs.BOM_UTF32_LE:
        bom_encoding = u'utf-32le'
        data = data[4:]
    elif data[:2] == codecs.BOM_UTF16_BE and data[2:4] != ZERO_BYTES:
        bom_encoding = u'utf-16be'
        data = data[2:]
    elif data[:2] == codecs.BOM_UTF16_LE and data[2:4] != ZERO_BYTES:
        bom_encoding = u'utf-16le'
        data = data[2:]
    elif data[:3] == codecs.BOM_UTF8:
        bom_encoding = u'utf-8'
        data = data[3:]
    # Check for the characters '<?xm' in several encodings.
    elif data[:4] == EBCDIC_MARKER:
        bom_encoding = u'cp037'
    elif data[:4] == UTF16BE_MARKER:
        bom_encoding = u'utf-16be'
    elif data[:4] == UTF16LE_MARKER:
        bom_encoding = u'utf-16le'
    elif data[:4] == UTF32BE_MARKER:
        bom_encoding = u'utf-32be'
    elif data[:4] == UTF32LE_MARKER:
        bom_encoding = u'utf-32le'

    tempdata = data
    try:
        if bom_encoding:
            tempdata = data.decode(bom_encoding).encode('utf-8')
    except (UnicodeDecodeError, LookupError):
        # feedparser recognizes UTF-32 encodings that aren't
        # available in Python 2.4 and 2.5, so it's possible to
        # encounter a LookupError during decoding.
        xml_encoding_match = None
    else:
        xml_encoding_match = RE_XML_PI_ENCODING.match(tempdata)

    if xml_encoding_match:
        xml_encoding = xml_encoding_match.groups()[0].decode('utf-8').lower()
        # Normalize the xml_encoding if necessary.
        if bom_encoding and (xml_encoding in (
            u'u16', u'utf-16', u'utf16', u'utf_16',
            u'u32', u'utf-32', u'utf32', u'utf_32',
            u'iso-10646-ucs-2', u'iso-10646-ucs-4',
            u'csucs4', u'csunicode', u'ucs-2', u'ucs-4'
        )):
            xml_encoding = bom_encoding

    # Find the HTTP Content-Type and, hopefully, a character
    # encoding provided by the server. The Content-Type is used
    # to choose the "correct" encoding among the BOM encoding,
    # XML declaration encoding, and HTTP encoding, following the
    # heuristic defined in RFC 3023.
    http_content_type = http_headers.get('content-type') or ''
    http_content_type, params = cgi.parse_header(http_content_type)
    http_encoding = params.get('charset', '').replace("'", "")
    if not isinstance(http_encoding, unicode):
        http_encoding = http_encoding.decode('utf-8', 'ignore')

    acceptable_content_type = 0
    application_content_types = (u'application/xml', u'application/xml-dtd',
                                 u'application/xml-external-parsed-entity')
    text_content_types = (u'text/xml', u'text/xml-external-parsed-entity')
    if (http_content_type in application_content_types) or \
       (http_content_type.startswith(u'application/') and 
        http_content_type.endswith(u'+xml')):
        acceptable_content_type = 1
        rfc3023_encoding = http_encoding or xml_encoding or u'utf-8'
    elif (http_content_type in text_content_types) or \
         (http_content_type.startswith(u'text/') and
          http_content_type.endswith(u'+xml')):
        acceptable_content_type = 1
        rfc3023_encoding = http_encoding or u'us-ascii'
    elif http_content_type.startswith(u'text/'):
        rfc3023_encoding = http_encoding or u'us-ascii'
    elif http_headers and 'content-type' not in http_headers:
        rfc3023_encoding = xml_encoding or u'iso-8859-1'
    else:
        rfc3023_encoding = xml_encoding or u'utf-8'
    # gb18030 is a superset of gb2312, so always replace gb2312
    # with gb18030 for greater compatibility.
    if rfc3023_encoding.lower() == u'gb2312':
        rfc3023_encoding = u'gb18030'
    if xml_encoding.lower() == u'gb2312':
        xml_encoding = u'gb18030'

    # there are four encodings to keep track of:
    # - http_encoding is the encoding declared in the Content-Type HTTP header
    # - xml_encoding is the encoding declared in the <?xml declaration
    # - bom_encoding is the encoding sniffed from the first 4 bytes of the XML data
    # - rfc3023_encoding is the actual encoding, as per RFC 3023 and a variety of other conflicting specifications
    error = None

    if http_headers and (not acceptable_content_type):
        if 'content-type' in http_headers:
            msg = '%s is not an XML media type' % http_headers['content-type']
        else:
            msg = 'no Content-type specified'
        error = NonXMLContentType(msg)

    # determine character encoding
    known_encoding = 0
    chardet_encoding = None
    tried_encodings = []
    if chardet:
        chardet_encoding = chardet.detect(data)['encoding']
        if not chardet_encoding:
            chardet_encoding = ''
        if not isinstance(chardet_encoding, unicode):
            chardet_encoding = unicode(chardet_encoding, 'ascii', 'ignore')
    # try: HTTP encoding, declared XML encoding, encoding sniffed from BOM
    for proposed_encoding in (rfc3023_encoding, xml_encoding, bom_encoding,
                              chardet_encoding, u'utf-8', u'windows-1252', u'iso-8859-2'):
        if not proposed_encoding:
            continue
        if proposed_encoding in tried_encodings:
            continue
        tried_encodings.append(proposed_encoding)
        try:
            data = data.decode(proposed_encoding)
        except (UnicodeDecodeError, LookupError):
            pass
        else:
            known_encoding = 1
            # Update the encoding in the opening XML processing instruction.
            new_declaration = '''<?xml version='1.0' encoding='utf-8'?>'''
            if RE_XML_DECLARATION.search(data):
                data = RE_XML_DECLARATION.sub(new_declaration, data)
            else:
                data = new_declaration + u'\n' + data
            data = data.encode('utf-8')
            break
    # if still no luck, give up
    if not known_encoding:
        error = CharacterEncodingUnknown(
            'document encoding unknown, I tried ' +
            '%s, %s, utf-8, windows-1252, and iso-8859-2 but nothing worked' %
            (rfc3023_encoding, xml_encoding))
        rfc3023_encoding = u''
    elif proposed_encoding != rfc3023_encoding:
        error = CharacterEncodingOverride(
            'document declared as %s, but parsed as %s' %
            (rfc3023_encoding, proposed_encoding))
        rfc3023_encoding = proposed_encoding

    return data, rfc3023_encoding, error

# Match XML entity declarations.
# Example: <!ENTITY copyright "(C)">
RE_ENTITY_PATTERN = re.compile(_s2bytes(r'^\s*<!ENTITY([^>]*?)>'), re.MULTILINE)

# Match XML DOCTYPE declarations.
# Example: <!DOCTYPE feed [ ]>
RE_DOCTYPE_PATTERN = re.compile(_s2bytes(r'^\s*<!DOCTYPE([^>]*?)>'), re.MULTILINE)

# Match safe entity declarations.
# This will allow hexadecimal character references through,
# as well as text, but not arbitrary nested entities.
# Example: cubed "&#179;"
# Example: copyright "(C)"
# Forbidden: explode1 "&explode2;&explode2;"
RE_SAFE_ENTITY_PATTERN = re.compile(_s2bytes('\s+(\w+)\s+"(&#\w+;|[^&"]*)"'))

def replace_doctype(data):
    '''Strips and replaces the DOCTYPE, returns (rss_version, stripped_data)

    rss_version may be 'rss091n' or None
    stripped_data is the same XML document with a replaced DOCTYPE
    '''

    # Divide the document into two groups by finding the location
    # of the first element that doesn't begin with '<?' or '<!'.
    start = re.search(_s2bytes('<\w'), data)
    start = start and start.start() or -1
    head, data = data[:start+1], data[start+1:]

    # Save and then remove all of the ENTITY declarations.
    entity_results = RE_ENTITY_PATTERN.findall(head)
    head = RE_ENTITY_PATTERN.sub(_s2bytes(''), head)

    # Find the DOCTYPE declaration and check the feed type.
    doctype_results = RE_DOCTYPE_PATTERN.findall(head)
    doctype = doctype_results and doctype_results[0] or _s2bytes('')
    if _s2bytes('netscape') in doctype.lower():
        version = u'rss091n'
    else:
        version = None

    # Re-insert the safe ENTITY declarations if a DOCTYPE was found.
    replacement = _s2bytes('')
    if len(doctype_results) == 1 and entity_results:
        match_safe_entities = lambda e: RE_SAFE_ENTITY_PATTERN.match(e)
        safe_entities = filter(match_safe_entities, entity_results)
        if safe_entities:
            replacement = _s2bytes('<!DOCTYPE feed [\n<!ENTITY') \
                        + _s2bytes('>\n<!ENTITY ').join(safe_entities) \
                        + _s2bytes('>\n]>')
    data = RE_DOCTYPE_PATTERN.sub(replacement, head) + data

    # Precompute the safe entities for the loose parser.
    safe_entities = dict((k.decode('utf-8'), v.decode('utf-8'))
                      for k, v in RE_SAFE_ENTITY_PATTERN.findall(replacement))
    return version, data, safe_entities


# GeoRSS geometry parsers. Each return a dict with 'type' and 'coordinates'
# items, or None in the case of a parsing error.

def _parse_poslist(value, geom_type, swap=True, dims=2):
    if geom_type == 'linestring':
        return _parse_georss_line(value, swap, dims)
    elif geom_type == 'polygon':
        ring = _parse_georss_line(value, swap, dims)
        return {'type': u'Polygon', 'coordinates': (ring['coordinates'],)}
    else:
        return None

def _gen_georss_coords(value, swap=True, dims=2):
    # A generator of (lon, lat) pairs from a string of encoded GeoRSS
    # coordinates. Converts to floats and swaps order.
    latlons = itertools.imap(float, value.strip().replace(',', ' ').split())
    nxt = latlons.next
    while True:
        t = [nxt(), nxt()][::swap and -1 or 1]
        if dims == 3:
            t.append(nxt())
        yield tuple(t)

def _parse_georss_point(value, swap=True, dims=2):
    # A point contains a single latitude-longitude pair, separated by
    # whitespace. We'll also handle comma separators.
    try:
        coords = list(_gen_georss_coords(value, swap, dims))
        return {u'type': u'Point', u'coordinates': coords[0]}
    except (IndexError, ValueError):
        return None

def _parse_georss_line(value, swap=True, dims=2):
    # A line contains a space separated list of latitude-longitude pairs in
    # WGS84 coordinate reference system, with each pair separated by
    # whitespace. There must be at least two pairs.
    try:
        coords = list(_gen_georss_coords(value, swap, dims))
        return {u'type': u'LineString', u'coordinates': coords}
    except (IndexError, ValueError):
        return None

def _parse_georss_polygon(value, swap=True, dims=2):
    # A polygon contains a space separated list of latitude-longitude pairs,
    # with each pair separated by whitespace. There must be at least four
    # pairs, with the last being identical to the first (so a polygon has a
    # minimum of three actual points). 
    try:
        ring = list(_gen_georss_coords(value, swap, dims))
    except (IndexError, ValueError):
        return None
    if len(ring) < 4:
        return None
    return {u'type': u'Polygon', u'coordinates': (ring,)}

def _parse_georss_box(value, swap=True, dims=2):
    # A bounding box is a rectangular region, often used to define the extents
    # of a map or a rough area of interest. A box contains two space seperate
    # latitude-longitude pairs, with each pair separated by whitespace. The
    # first pair is the lower corner, the second is the upper corner.
    try:
        coords = list(_gen_georss_coords(value, swap, dims))
        return {u'type': u'Box', u'coordinates': tuple(coords)}
    except (IndexError, ValueError):
        return None

# end geospatial parsers


def parse(url_file_stream_or_string, etag=None, modified=None, agent=None, referrer=None, handlers=None, request_headers=None, response_headers=None):
    '''Parse a feed from a URL, file, stream, or string.

    request_headers, if given, is a dict from http header name to value to add
    to the request; this overrides internally generated values.
    '''

    if handlers is None:
        handlers = []
    if request_headers is None:
        request_headers = {}
    if response_headers is None:
        response_headers = {}

    result = FeedParserDict()
    result['feed'] = FeedParserDict()
    result['entries'] = []
    result['bozo'] = 0
    if not isinstance(handlers, list):
        handlers = [handlers]
    try:
        f = _open_resource(url_file_stream_or_string, etag, modified, agent, referrer, handlers, request_headers)
        data = f.read()
    except Exception, e:
        result['bozo'] = 1
        result['bozo_exception'] = e
        data = None
        f = None

    if hasattr(f, 'headers'):
        result['headers'] = dict(f.headers)
    # overwrite existing headers using response_headers
    if 'headers' in result:
        result['headers'].update(response_headers)
    elif response_headers:
        result['headers'] = copy.deepcopy(response_headers)

    # lowercase all of the HTTP headers for comparisons per RFC 2616
    if 'headers' in result:
        http_headers = dict((k.lower(), v) for k, v in result['headers'].items())
    else:
        http_headers = {}

    # if feed is gzip-compressed, decompress it
    if f and data and http_headers:
        if gzip and 'gzip' in http_headers.get('content-encoding', ''):
            try:
                data = gzip.GzipFile(fileobj=_StringIO(data)).read()
            except (IOError, struct.error), e:
                # IOError can occur if the gzip header is bad.
                # struct.error can occur if the data is damaged.
                result['bozo'] = 1
                result['bozo_exception'] = e
                if isinstance(e, struct.error):
                    # A gzip header was found but the data is corrupt.
                    # Ideally, we should re-request the feed without the
                    # 'Accept-encoding: gzip' header, but we don't.
                    data = None
        elif zlib and 'deflate' in http_headers.get('content-encoding', ''):
            try:
                data = zlib.decompress(data)
            except zlib.error, e:
                try:
                    # The data may have no headers and no checksum.
                    data = zlib.decompress(data, -15)
                except zlib.error, e:
                    result['bozo'] = 1
                    result['bozo_exception'] = e

    # save HTTP headers
    if http_headers:
        if 'etag' in http_headers:
            etag = http_headers.get('etag', u'')
            if not isinstance(etag, unicode):
                etag = etag.decode('utf-8', 'ignore')
            if etag:
                result['etag'] = etag
        if 'last-modified' in http_headers:
            modified = http_headers.get('last-modified', u'')
            if modified:
                result['modified'] = modified
                result['modified_parsed'] = _parse_date(modified)
    if hasattr(f, 'url'):
        if not isinstance(f.url, unicode):
            result['href'] = f.url.decode('utf-8', 'ignore')
        else:
            result['href'] = f.url
        result['status'] = 200
    if hasattr(f, 'status'):
        result['status'] = f.status
    if hasattr(f, 'close'):
        f.close()

    if data is None:
        return result

    # Stop processing if the server sent HTTP 304 Not Modified.
    if getattr(f, 'code', 0) == 304:
        result['version'] = u''
        result['debug_message'] = 'The feed has not changed since you last checked, ' + \
            'so the server sent no data.  This is a feature, not a bug!'
        return result

    data, result['encoding'], error = convert_to_utf8(http_headers, data)
    use_strict_parser = result['encoding'] and True or False
    if error is not None:
        result['bozo'] = 1
        result['bozo_exception'] = error

    result['version'], data, entities = replace_doctype(data)

    # Ensure that baseuri is an absolute URI using an acceptable URI scheme.
    contentloc = http_headers.get('content-location', u'')
    href = result.get('href', u'')
    baseuri = _makeSafeAbsoluteURI(href, contentloc) or _makeSafeAbsoluteURI(contentloc) or href

    baselang = http_headers.get('content-language', None)
    if not isinstance(baselang, unicode) and baselang is not None:
        baselang = baselang.decode('utf-8', 'ignore')

    if not _XML_AVAILABLE:
        use_strict_parser = 0
    if use_strict_parser:
        # initialize the SAX parser
        feedparser = _StrictFeedParser(baseuri, baselang, 'utf-8')
        saxparser = xml.sax.make_parser(PREFERRED_XML_PARSERS)
        saxparser.setFeature(xml.sax.handler.feature_namespaces, 1)
        try:
            # disable downloading external doctype references, if possible
            saxparser.setFeature(xml.sax.handler.feature_external_ges, 0)
        except xml.sax.SAXNotSupportedException:
            pass
        saxparser.setContentHandler(feedparser)
        saxparser.setErrorHandler(feedparser)
        source = xml.sax.xmlreader.InputSource()
        source.setByteStream(_StringIO(data))
        try:
            saxparser.parse(source)
        except xml.sax.SAXException, e:
            result['bozo'] = 1
            result['bozo_exception'] = feedparser.exc or e
            use_strict_parser = 0
    if not use_strict_parser and _SGML_AVAILABLE:
        feedparser = _LooseFeedParser(baseuri, baselang, 'utf-8', entities)
        feedparser.feed(data.decode('utf-8', 'replace'))
    result['feed'] = feedparser.feeddata
    result['entries'] = feedparser.entries
    result['version'] = result['version'] or feedparser.version
    result['namespaces'] = feedparser.namespacesInUse
    return result

# The list of EPSG codes for geographic (latitude/longitude) coordinate
# systems to support decoding of GeoRSS GML profiles.
_geogCS = [
3819, 3821, 3824, 3889, 3906, 4001, 4002, 4003, 4004, 4005, 4006, 4007, 4008,
4009, 4010, 4011, 4012, 4013, 4014, 4015, 4016, 4018, 4019, 4020, 4021, 4022,
4023, 4024, 4025, 4027, 4028, 4029, 4030, 4031, 4032, 4033, 4034, 4035, 4036,
4041, 4042, 4043, 4044, 4045, 4046, 4047, 4052, 4053, 4054, 4055, 4075, 4081,
4120, 4121, 4122, 4123, 4124, 4125, 4126, 4127, 4128, 4129, 4130, 4131, 4132,
4133, 4134, 4135, 4136, 4137, 4138, 4139, 4140, 4141, 4142, 4143, 4144, 4145,
4146, 4147, 4148, 4149, 4150, 4151, 4152, 4153, 4154, 4155, 4156, 4157, 4158,
4159, 4160, 4161, 4162, 4163, 4164, 4165, 4166, 4167, 4168, 4169, 4170, 4171,
4172, 4173, 4174, 4175, 4176, 4178, 4179, 4180, 4181, 4182, 4183, 4184, 4185,
4188, 4189, 4190, 4191, 4192, 4193, 4194, 4195, 4196, 4197, 4198, 4199, 4200,
4201, 4202, 4203, 4204, 4205, 4206, 4207, 4208, 4209, 4210, 4211, 4212, 4213,
4214, 4215, 4216, 4218, 4219, 4220, 4221, 4222, 4223, 4224, 4225, 4226, 4227,
4228, 4229, 4230, 4231, 4232, 4233, 4234, 4235, 4236, 4237, 4238, 4239, 4240,
4241, 4242, 4243, 4244, 4245, 4246, 4247, 4248, 4249, 4250, 4251, 4252, 4253,
4254, 4255, 4256, 4257, 4258, 4259, 4260, 4261, 4262, 4263, 4264, 4265, 4266,
4267, 4268, 4269, 4270, 4271, 4272, 4273, 4274, 4275, 4276, 4277, 4278, 4279,
4280, 4281, 4282, 4283, 4284, 4285, 4286, 4287, 4288, 4289, 4291, 4292, 4293,
4294, 4295, 4296, 4297, 4298, 4299, 4300, 4301, 4302, 4303, 4304, 4306, 4307,
4308, 4309, 4310, 4311, 4312, 4313, 4314, 4315, 4316, 4317, 4318, 4319, 4322,
4324, 4326, 4463, 4470, 4475, 4483, 4490, 4555, 4558, 4600, 4601, 4602, 4603,
4604, 4605, 4606, 4607, 4608, 4609, 4610, 4611, 4612, 4613, 4614, 4615, 4616,
4617, 4618, 4619, 4620, 4621, 4622, 4623, 4624, 4625, 4626, 4627, 4628, 4629,
4630, 4631, 4632, 4633, 4634, 4635, 4636, 4637, 4638, 4639, 4640, 4641, 4642,
4643, 4644, 4645, 4646, 4657, 4658, 4659, 4660, 4661, 4662, 4663, 4664, 4665,
4666, 4667, 4668, 4669, 4670, 4671, 4672, 4673, 4674, 4675, 4676, 4677, 4678,
4679, 4680, 4681, 4682, 4683, 4684, 4685, 4686, 4687, 4688, 4689, 4690, 4691,
4692, 4693, 4694, 4695, 4696, 4697, 4698, 4699, 4700, 4701, 4702, 4703, 4704,
4705, 4706, 4707, 4708, 4709, 4710, 4711, 4712, 4713, 4714, 4715, 4716, 4717,
4718, 4719, 4720, 4721, 4722, 4723, 4724, 4725, 4726, 4727, 4728, 4729, 4730,
4731, 4732, 4733, 4734, 4735, 4736, 4737, 4738, 4739, 4740, 4741, 4742, 4743,
4744, 4745, 4746, 4747, 4748, 4749, 4750, 4751, 4752, 4753, 4754, 4755, 4756,
4757, 4758, 4759, 4760, 4761, 4762, 4763, 4764, 4765, 4801, 4802, 4803, 4804,
4805, 4806, 4807, 4808, 4809, 4810, 4811, 4813, 4814, 4815, 4816, 4817, 4818,
4819, 4820, 4821, 4823, 4824, 4901, 4902, 4903, 4904, 4979 ]

########NEW FILE########
__FILENAME__ = feedparsertest
#!/usr/bin/env python

__author__ = "Mark Pilgrim <http://diveintomark.org/>"
__license__ = """
Copyright (c) 2010-2013 Kurt McKee <contactme@kurtmckee.org>
Copyright (c) 2004-2008 Mark Pilgrim
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 'AS IS'
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE."""

import codecs
import datetime
import glob
import operator
import os
import posixpath
import pprint
import re
import struct
import sys
import threading
import time
import unittest
import urllib
import warnings
import zlib
import BaseHTTPServer
import SimpleHTTPServer

import feedparser

if not feedparser._XML_AVAILABLE:
    sys.stderr.write('No XML parsers available, unit testing can not proceed\n')
    sys.exit(1)

try:
    # the utf_32 codec was introduced in Python 2.6; it's necessary to
    # check this as long as feedparser supports Python 2.4 and 2.5
    codecs.lookup('utf_32')
except LookupError:
    _UTF32_AVAILABLE = False
else:
    _UTF32_AVAILABLE = True

_s2bytes = feedparser._s2bytes
_l2bytes = feedparser._l2bytes

#---------- custom HTTP server (used to serve test feeds) ----------

_PORT = 8097 # not really configurable, must match hardcoded port in tests
_HOST = '127.0.0.1' # also not really configurable

class FeedParserTestRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    headers_re = re.compile(_s2bytes(r"^Header:\s+([^:]+):(.+)$"), re.MULTILINE)

    def send_head(self):
        """Send custom headers defined in test case

        Example:
        <!--
        Header:   Content-type: application/atom+xml
        Header:   X-Foo: bar
        -->
        """
        # Short-circuit the HTTP status test `test_redirect_to_304()`
        if self.path == '/-/return-304.xml':
            self.send_response(304)
            self.send_header('Content-type', 'text/xml')
            self.end_headers()
            return feedparser._StringIO(u''.encode('utf-8'))
        path = self.translate_path(self.path)
        # the compression tests' filenames determine the header sent
        if self.path.startswith('/tests/compression'):
            if self.path.endswith('gz'):
                headers = {'Content-Encoding': 'gzip'}
            else:
                headers = {'Content-Encoding': 'deflate'}
            headers['Content-type'] = 'application/xml'
        else:
            headers = dict([(k.decode('utf-8'), v.decode('utf-8').strip()) for k, v in self.headers_re.findall(open(path, 'rb').read())])
        f = open(path, 'rb')
        if (self.headers.get('if-modified-since') == headers.get('Last-Modified', 'nom')) \
            or (self.headers.get('if-none-match') == headers.get('ETag', 'nomatch')):
            status = 304
        else:
            status = 200
        headers.setdefault('Status', status)
        self.send_response(int(headers['Status']))
        headers.setdefault('Content-type', self.guess_type(path))
        self.send_header("Content-type", headers['Content-type'])
        self.send_header("Content-Length", str(os.stat(f.name)[6]))
        for k, v in headers.items():
            if k not in ('Status', 'Content-type'):
                self.send_header(k, v)
        self.end_headers()
        return f

    def log_request(self, *args):
        pass

class FeedParserTestServer(threading.Thread):
    """HTTP Server that runs in a thread and handles a predetermined number of requests"""

    def __init__(self, requests):
        threading.Thread.__init__(self)
        self.requests = requests
        self.ready = threading.Event()

    def run(self):
        self.httpd = BaseHTTPServer.HTTPServer((_HOST, _PORT), FeedParserTestRequestHandler)
        self.ready.set()
        while self.requests:
            self.httpd.handle_request()
            self.requests -= 1
        self.ready.clear()

#---------- dummy test case class (test methods are added dynamically) ----------
unicode1_re = re.compile(_s2bytes(" u'"))
unicode2_re = re.compile(_s2bytes(' u"'))

# _bytes is only used in everythingIsUnicode().
# In Python 2 it's str, and in Python 3 it's bytes.
_bytes = type(_s2bytes(''))

def everythingIsUnicode(d):
    """Takes a dictionary, recursively verifies that every value is unicode"""
    for k, v in d.iteritems():
        if isinstance(v, dict) and k != 'headers':
            if not everythingIsUnicode(v):
                return False
        elif isinstance(v, list):
            for i in v:
                if isinstance(i, dict) and not everythingIsUnicode(i):
                    return False
                elif isinstance(i, _bytes):
                    return False
        elif isinstance(v, _bytes):
            return False
    return True

def failUnlessEval(self, xmlfile, evalString, msg=None):
    """Fail unless eval(evalString, env)"""
    env = feedparser.parse(xmlfile)
    try:
        if not eval(evalString, globals(), env):
            failure=(msg or 'not eval(%s) \nWITH env(%s)' % (evalString, pprint.pformat(env)))
            raise self.failureException, failure
        if not everythingIsUnicode(env):
            raise self.failureException, "not everything is unicode \nWITH env(%s)" % (pprint.pformat(env), )
    except SyntaxError:
        # Python 3 doesn't have the `u""` syntax, so evalString needs to be modified,
        # which will require the failure message to be updated
        evalString = re.sub(unicode1_re, _s2bytes(" '"), evalString)
        evalString = re.sub(unicode2_re, _s2bytes(' "'), evalString)
        if not eval(evalString, globals(), env):
            failure=(msg or 'not eval(%s) \nWITH env(%s)' % (evalString, pprint.pformat(env)))
            raise self.failureException, failure

class BaseTestCase(unittest.TestCase):
    failUnlessEval = failUnlessEval

class TestCase(BaseTestCase):
    pass

class TestTemporaryFallbackBehavior(unittest.TestCase):
    "These tests are temporarily here because of issues 310 and 328"
    def test_issue_328_fallback_behavior(self):
        warnings.filterwarnings('error')

        d = feedparser.FeedParserDict()
        d['published'] = u'pub string'
        d['published_parsed'] = u'pub tuple'
        d['updated'] = u'upd string'
        d['updated_parsed'] = u'upd tuple'
        # Ensure that `updated` doesn't map to `published` when it exists
        self.assertTrue('published' in d)
        self.assertTrue('published_parsed' in d)
        self.assertTrue('updated' in d)
        self.assertTrue('updated_parsed' in d)
        self.assertEqual(d['published'], 'pub string')
        self.assertEqual(d['published_parsed'], 'pub tuple')
        self.assertEqual(d['updated'], 'upd string')
        self.assertEqual(d['updated_parsed'], 'upd tuple')

        d = feedparser.FeedParserDict()
        d['published'] = u'pub string'
        d['published_parsed'] = u'pub tuple'
        # Ensure that `updated` doesn't actually exist
        self.assertTrue('updated' not in d)
        self.assertTrue('updated_parsed' not in d)
        # Ensure that accessing `updated` throws a DeprecationWarning
        try:
            d['updated']
        except DeprecationWarning:
            # Expected behavior
            pass
        else:
            # Wrong behavior
            self.assertEqual(True, False)
        try:
            d['updated_parsed']
        except DeprecationWarning:
            # Expected behavior
            pass
        else:
            # Wrong behavior
            self.assertEqual(True, False)
        # Ensure that `updated` maps to `published`
        warnings.filterwarnings('ignore')
        self.assertEqual(d['updated'], u'pub string')
        self.assertEqual(d['updated_parsed'], u'pub tuple')
        warnings.resetwarnings()


class TestEverythingIsUnicode(unittest.TestCase):
    "Ensure that `everythingIsUnicode()` is working appropriately"
    def test_everything_is_unicode(self):
        self.assertTrue(everythingIsUnicode(
            {'a': u'a', 'b': [u'b', {'c': u'c'}], 'd': {'e': u'e'}}
        ))
    def test_not_everything_is_unicode(self):
        self.assertFalse(everythingIsUnicode({'a': _s2bytes('a')}))
        self.assertFalse(everythingIsUnicode({'a': [_s2bytes('a')]}))
        self.assertFalse(everythingIsUnicode({'a': {'b': _s2bytes('b')}}))
        self.assertFalse(everythingIsUnicode({'a': [{'b': _s2bytes('b')}]}))

class TestLooseParser(BaseTestCase):
    "Test the sgmllib-based parser by manipulating feedparser " \
    "into believing no XML parsers are installed"
    def __init__(self, arg):
        unittest.TestCase.__init__(self, arg)
        self._xml_available = feedparser._XML_AVAILABLE
    def setUp(self):
        feedparser._XML_AVAILABLE = 0
    def tearDown(self):
        feedparser._XML_AVAILABLE = self._xml_available

class TestStrictParser(BaseTestCase):
    pass

class TestMicroformats(BaseTestCase):
    pass

class TestEncodings(BaseTestCase):
    def test_doctype_replacement(self):
        "Ensure that non-ASCII-compatible encodings don't hide " \
        "disallowed ENTITY declarations"
        doc = """<?xml version="1.0" encoding="utf-16be"?>
        <!DOCTYPE feed [
            <!ENTITY exponential1 "bogus ">
            <!ENTITY exponential2 "&exponential1;&exponential1;">
            <!ENTITY exponential3 "&exponential2;&exponential2;">
        ]>
        <feed><title type="html">&exponential3;</title></feed>"""
        doc = codecs.BOM_UTF16_BE + doc.encode('utf-16be')
        result = feedparser.parse(doc)
        self.assertEqual(result['feed']['title'], u'&amp;exponential3')
    def test_gb2312_converted_to_gb18030_in_xml_encoding(self):
        # \u55de was chosen because it exists in gb18030 but not gb2312
        feed = u'''<?xml version="1.0" encoding="gb2312"?>
                  <feed><title>\u55de</title></feed>'''
        result = feedparser.parse(feed.encode('gb18030'), response_headers={
            'Content-Type': 'text/xml'
        })
        self.assertEqual(result.encoding, 'gb18030')

class TestFeedParserDict(unittest.TestCase):
    "Ensure that FeedParserDict returns values as expected and won't crash"
    def setUp(self):
        self.d = feedparser.FeedParserDict()
    def _check_key(self, k):
        self.assertTrue(k in self.d)
        self.assertTrue(hasattr(self.d, k))
        self.assertEqual(self.d[k], 1)
        self.assertEqual(getattr(self.d, k), 1)
    def _check_no_key(self, k):
        self.assertTrue(k not in self.d)
        self.assertTrue(not hasattr(self.d, k))
    def test_empty(self):
        keys = (
            'a','entries', 'id', 'guid', 'summary', 'subtitle', 'description',
            'category', 'enclosures', 'license', 'categories',
        )
        for k in keys:
            self._check_no_key(k)
        self.assertTrue('items' not in self.d)
        self.assertTrue(hasattr(self.d, 'items')) # dict.items() exists
    def test_neutral(self):
        self.d['a'] = 1
        self._check_key('a')
    def test_single_mapping_target_1(self):
        self.d['id'] = 1
        self._check_key('id')
        self._check_key('guid')
    def test_single_mapping_target_2(self):
        self.d['guid'] = 1
        self._check_key('id')
        self._check_key('guid')
    def test_multiple_mapping_target_1(self):
        self.d['summary'] = 1
        self._check_key('summary')
        self._check_key('description')
    def test_multiple_mapping_target_2(self):
        self.d['subtitle'] = 1
        self._check_key('subtitle')
        self._check_key('description')
    def test_multiple_mapping_mapped_key(self):
        self.d['description'] = 1
        self._check_key('summary')
        self._check_key('description')
    def test_license(self):
        self.d['links'] = []
        try:
            self.d['license']
            self.assertTrue(False)
        except KeyError:
            pass
        self.d['links'].append({'rel': 'license'})
        try:
            self.d['license']
            self.assertTrue(False)
        except KeyError:
            pass
        self.d['links'].append({'rel': 'license', 'href': 'http://dom.test/'})
        self.assertEqual(self.d['license'], 'http://dom.test/')
    def test_category(self):
        self.d['tags'] = []
        try:
            self.d['category']
            self.assertTrue(False)
        except KeyError:
            pass
        self.d['tags'] = [{}]
        try:
            self.d['category']
            self.assertTrue(False)
        except KeyError:
            pass
        self.d['tags'] = [{'term': 'cat'}]
        self.assertEqual(self.d['category'], 'cat')
        self.d['tags'].append({'term': 'dog'})
        self.assertEqual(self.d['category'], 'cat')

class TestOpenResource(unittest.TestCase):
    "Ensure that `_open_resource()` interprets its arguments as URIs, " \
    "file-like objects, or in-memory feeds as expected"
    def test_fileobj(self):
        r = feedparser._open_resource(sys.stdin, '', '', '', '', [], {})
        self.assertTrue(r is sys.stdin)
    def test_feed(self):
        f = feedparser.parse(u'feed://localhost:8097/tests/http/target.xml')
        self.assertEqual(f.href, u'http://localhost:8097/tests/http/target.xml')
    def test_feed_http(self):
        f = feedparser.parse(u'feed:http://localhost:8097/tests/http/target.xml')
        self.assertEqual(f.href, u'http://localhost:8097/tests/http/target.xml')
    def test_bytes(self):
        s = '<feed><item><title>text</title></item></feed>'.encode('utf-8')
        r = feedparser._open_resource(s, '', '', '', '', [], {})
        self.assertEqual(s, r.read())
    def test_string(self):
        s = '<feed><item><title>text</title></item></feed>'
        r = feedparser._open_resource(s, '', '', '', '', [], {})
        self.assertEqual(s.encode('utf-8'), r.read())
    def test_unicode_1(self):
        s = u'<feed><item><title>text</title></item></feed>'
        r = feedparser._open_resource(s, '', '', '', '', [], {})
        self.assertEqual(s.encode('utf-8'), r.read())
    def test_unicode_2(self):
        s = u'<feed><item><title>t\u00e9xt</title></item></feed>'
        r = feedparser._open_resource(s, '', '', '', '', [], {})
        self.assertEqual(s.encode('utf-8'), r.read())

class TestMakeSafeAbsoluteURI(unittest.TestCase):
    "Exercise the URI joining and sanitization code"
    base = u'http://d.test/d/f.ext'
    def _mktest(rel, expect, doc):
        def fn(self):
            value = feedparser._makeSafeAbsoluteURI(self.base, rel)
            self.assertEqual(value, expect)
        fn.__doc__ = doc
        return fn

    # make the test cases; the call signature is:
    # (relative_url, expected_return_value, test_doc_string)
    test_abs = _mktest(u'https://s.test/', u'https://s.test/', 'absolute uri')
    test_rel = _mktest(u'/new', u'http://d.test/new', 'relative uri')
    test_bad = _mktest(u'x://bad.test/', u'', 'unacceptable uri protocol')
    test_mag = _mktest(u'magnet:?xt=a', u'magnet:?xt=a', 'magnet uri')

    def test_catch_ValueError(self):
        'catch ValueError in Python 2.7 and up'
        uri = u'http://bad]test/'
        value1 = feedparser._makeSafeAbsoluteURI(uri)
        value2 = feedparser._makeSafeAbsoluteURI(self.base, uri)
        swap = feedparser.ACCEPTABLE_URI_SCHEMES
        feedparser.ACCEPTABLE_URI_SCHEMES = ()
        value3 = feedparser._makeSafeAbsoluteURI(self.base, uri)
        feedparser.ACCEPTABLE_URI_SCHEMES = swap
        # Only Python 2.7 and up throw a ValueError, otherwise uri is returned
        self.assertTrue(value1 in (uri, u''))
        self.assertTrue(value2 in (uri, u''))
        self.assertTrue(value3 in (uri, u''))

class TestConvertToIdn(unittest.TestCase):
    "Test IDN support (unavailable in Jython as of Jython 2.5.2)"
    # this is the greek test domain
    hostname = u'\u03c0\u03b1\u03c1\u03ac\u03b4\u03b5\u03b9\u03b3\u03bc\u03b1'
    hostname += u'.\u03b4\u03bf\u03ba\u03b9\u03bc\u03ae'
    def test_control(self):
        r = feedparser._convert_to_idn(u'http://example.test/')
        self.assertEqual(r, u'http://example.test/')
    def test_idn(self):
        r = feedparser._convert_to_idn(u'http://%s/' % (self.hostname,))
        self.assertEqual(r, u'http://xn--hxajbheg2az3al.xn--jxalpdlp/')
    def test_port(self):
        r = feedparser._convert_to_idn(u'http://%s:8080/' % (self.hostname,))
        self.assertEqual(r, u'http://xn--hxajbheg2az3al.xn--jxalpdlp:8080/')

class TestCompression(unittest.TestCase):
    "Test the gzip and deflate support in the HTTP code"
    def test_gzip_good(self):
        f = feedparser.parse('http://localhost:8097/tests/compression/gzip.gz')
        self.assertEqual(f.version, 'atom10')
    def test_gzip_not_compressed(self):
        f = feedparser.parse('http://localhost:8097/tests/compression/gzip-not-compressed.gz')
        self.assertEqual(f.bozo, 1)
        self.assertTrue(isinstance(f.bozo_exception, IOError))
        self.assertEqual(f['feed']['title'], 'gzip')
    def test_gzip_struct_error(self):
        f = feedparser.parse('http://localhost:8097/tests/compression/gzip-struct-error.gz')
        self.assertEqual(f.bozo, 1)
        self.assertTrue(isinstance(f.bozo_exception, struct.error))
    def test_zlib_good(self):
        f = feedparser.parse('http://localhost:8097/tests/compression/deflate.z')
        self.assertEqual(f.version, 'atom10')
    def test_zlib_no_headers(self):
        f = feedparser.parse('http://localhost:8097/tests/compression/deflate-no-headers.z')
        self.assertEqual(f.version, 'atom10')
    def test_zlib_not_compressed(self):
        f = feedparser.parse('http://localhost:8097/tests/compression/deflate-not-compressed.z')
        self.assertEqual(f.bozo, 1)
        self.assertTrue(isinstance(f.bozo_exception, zlib.error))
        self.assertEqual(f['feed']['title'], 'deflate')

class TestHTTPStatus(unittest.TestCase):
    "Test HTTP redirection and other status codes"
    def test_301(self):
        f = feedparser.parse('http://localhost:8097/tests/http/http_status_301.xml')
        self.assertEqual(f.status, 301)
        self.assertEqual(f.href, 'http://localhost:8097/tests/http/target.xml')
        self.assertEqual(f.entries[0].title, 'target')
    def test_302(self):
        f = feedparser.parse('http://localhost:8097/tests/http/http_status_302.xml')
        self.assertEqual(f.status, 302)
        self.assertEqual(f.href, 'http://localhost:8097/tests/http/target.xml')
        self.assertEqual(f.entries[0].title, 'target')
    def test_303(self):
        f = feedparser.parse('http://localhost:8097/tests/http/http_status_303.xml')
        self.assertEqual(f.status, 303)
        self.assertEqual(f.href, 'http://localhost:8097/tests/http/target.xml')
        self.assertEqual(f.entries[0].title, 'target')
    def test_307(self):
        f = feedparser.parse('http://localhost:8097/tests/http/http_status_307.xml')
        self.assertEqual(f.status, 307)
        self.assertEqual(f.href, 'http://localhost:8097/tests/http/target.xml')
        self.assertEqual(f.entries[0].title, 'target')
    def test_304(self):
        # first retrieve the url
        u = 'http://localhost:8097/tests/http/http_status_304.xml'
        f = feedparser.parse(u)
        self.assertEqual(f.status, 200)
        self.assertEqual(f.entries[0].title, 'title 304')
        # extract the etag and last-modified headers
        e = [v for k, v in f.headers.items() if k.lower() == 'etag'][0]
        mh = [v for k, v in f.headers.items() if k.lower() == 'last-modified'][0]
        ms = f.updated
        mt = f.updated_parsed
        md = datetime.datetime(*mt[0:7])
        self.assertTrue(isinstance(mh, basestring))
        self.assertTrue(isinstance(ms, basestring))
        self.assertTrue(isinstance(mt, time.struct_time))
        self.assertTrue(isinstance(md, datetime.datetime))
        # test that sending back the etag results in a 304
        f = feedparser.parse(u, etag=e)
        self.assertEqual(f.status, 304)
        # test that sending back last-modified (string) results in a 304
        f = feedparser.parse(u, modified=ms)
        self.assertEqual(f.status, 304)
        # test that sending back last-modified (9-tuple) results in a 304
        f = feedparser.parse(u, modified=mt)
        self.assertEqual(f.status, 304)
        # test that sending back last-modified (datetime) results in a 304
        f = feedparser.parse(u, modified=md)
        self.assertEqual(f.status, 304)
    def test_404(self):
        f = feedparser.parse('http://localhost:8097/tests/http/http_status_404.xml')
        self.assertEqual(f.status, 404)
    def test_redirect_to_304(self):
        # ensure that an http redirect to an http 304 doesn't
        # trigger a bozo_exception
        u = 'http://localhost:8097/tests/http/http_redirect_to_304.xml'
        f = feedparser.parse(u)
        self.assertTrue(f.bozo == 0)
        self.assertTrue(f.status == 302)

class TestDateParsers(unittest.TestCase):
    "Test the various date parsers; most of the test cases are constructed " \
    "dynamically based on the contents of the `date_tests` dict, below"
    def test_None(self):
        self.assertTrue(feedparser._parse_date(None) is None)
    def _check_date(self, func, dtstring, expected_value):
        try:
            parsed_value = func(dtstring)
        except (OverflowError, ValueError):
            parsed_value = None
        self.assertEqual(parsed_value, expected_value)
        # self.assertEqual(parsed_value, feedparser._parse_date(dtstring))
    def test_year_10000_date(self):
        # On some systems this date string will trigger an OverflowError.
        # On Jython and x64 systems, however, it's interpreted just fine.
        try:
            date = feedparser._parse_date_rfc822(u'Sun, 31 Dec 9999 23:59:59 -9999')
        except OverflowError:
            date = None
        self.assertTrue(date in (None, (10000, 1, 5, 4, 38, 59, 2, 5, 0)))

date_tests = {
    feedparser._parse_date_greek: (
        (u'', None), # empty string
        (u'\u039a\u03c5\u03c1, 11 \u0399\u03bf\u03cd\u03bb 2004 12:00:00 EST', (2004, 7, 11, 17, 0, 0, 6, 193, 0)),
    ),
    feedparser._parse_date_hungarian: (
        (u'', None), # empty string
        (u'2004-j\u00falius-13T9:15-05:00', (2004, 7, 13, 14, 15, 0, 1, 195, 0)),
    ),
    feedparser._parse_date_iso8601: (
        (u'', None), # empty string
        (u'-0312', (2003, 12, 1, 0, 0, 0, 0, 335, 0)), # 2-digit year/month only variant
        (u'031231', (2003, 12, 31, 0, 0, 0, 2, 365, 0)), # 2-digit year/month/day only, no hyphens
        (u'03-12-31', (2003, 12, 31, 0, 0, 0, 2, 365, 0)), # 2-digit year/month/day only
        (u'-03-12', (2003, 12, 1, 0, 0, 0, 0, 335, 0)), # 2-digit year/month only
        (u'03335', (2003, 12, 1, 0, 0, 0, 0, 335, 0)), # 2-digit year/ordinal, no hyphens
        (u'2003-12-31T10:14:55.1234Z', (2003, 12, 31, 10, 14, 55, 2, 365, 0)), # fractional seconds
        # Special case for Google's extra zero in the month
        (u'2003-012-31T10:14:55+00:00', (2003, 12, 31, 10, 14, 55, 2, 365, 0)),
    ),
    feedparser._parse_date_nate: (
        (u'', None), # empty string
        (u'2004-05-25 \uc624\ud6c4 11:23:17', (2004, 5, 25, 14, 23, 17, 1, 146, 0)),
    ),
    feedparser._parse_date_onblog: (
        (u'', None), # empty string
        (u'2004\ub144 05\uc6d4 28\uc77c  01:31:15', (2004, 5, 27, 16, 31, 15, 3, 148, 0)),
    ),
    feedparser._parse_date_perforce: (
        (u'', None), # empty string
        (u'Fri, 2006/09/15 08:19:53 EDT', (2006, 9, 15, 12, 19, 53, 4, 258, 0)),
    ),
    feedparser._parse_date_rfc822: (
        (u'', None), # empty string
        (u'Thu, 01 Jan 0100 00:00:01 +0100', (99, 12, 31, 23, 0, 1, 3, 365, 0)), # ancient date
        (u'Thu, 01 Jan 04 19:48:21 GMT', (2004, 1, 1, 19, 48, 21, 3, 1, 0)), # 2-digit year
        (u'Thu, 01 Jan 2004 19:48:21 GMT', (2004, 1, 1, 19, 48, 21, 3, 1, 0)), # 4-digit year
        (u'Thu,  5 Apr 2012 10:00:00 GMT', (2012, 4, 5, 10, 0, 0, 3, 96, 0)), # 1-digit day
        (u'Wed, 19 Aug 2009 18:28:00 Etc/GMT', (2009, 8, 19, 18, 28, 0, 2, 231, 0)), # etc/gmt timezone
        (u'Wed, 19 Feb 2012 22:40:00 GMT-01:01', (2012, 2, 19, 23, 41, 0, 6, 50, 0)), # gmt+hh:mm timezone
        (u'Mon, 13 Feb, 2012 06:28:00 UTC', (2012, 2, 13, 6, 28, 0, 0, 44, 0)), # extraneous comma
        (u'Thu, 01 Jan 2004 00:00 GMT', (2004, 1, 1, 0, 0, 0, 3, 1, 0)), # no seconds
        (u'Thu, 01 Jan 2004', (2004, 1, 1, 0, 0, 0, 3, 1, 0)), # no time
        # Additional tests to handle Disney's long month names and invalid timezones
        (u'Mon, 26 January 2004 16:31:00 AT', (2004, 1, 26, 20, 31, 0, 0, 26, 0)),
        (u'Mon, 26 January 2004 16:31:00 ET', (2004, 1, 26, 21, 31, 0, 0, 26, 0)),
        (u'Mon, 26 January 2004 16:31:00 CT', (2004, 1, 26, 22, 31, 0, 0, 26, 0)),
        (u'Mon, 26 January 2004 16:31:00 MT', (2004, 1, 26, 23, 31, 0, 0, 26, 0)),
        (u'Mon, 26 January 2004 16:31:00 PT', (2004, 1, 27, 0, 31, 0, 1, 27, 0)),
        # Swapped month and day
        (u'Thu Aug 30 2012 17:26:16 +0200', (2012, 8, 30, 15, 26, 16, 3, 243, 0)),
        (u'Sun, 16 Dec 2012 1:2:3:4 GMT', None), # invalid time
        (u'Sun, 16 zzz 2012 11:47:32 GMT', None), # invalid month
        (u'Sun, Dec x 2012 11:47:32 GMT', None), # invalid day (swapped day/month)
        ('Sun, 16 Dec zz 11:47:32 GMT', None), # invalid year
        ('Sun, 16 Dec 2012 11:47:32 +zz:00', None), # invalid timezone hour
        ('Sun, 16 Dec 2012 11:47:32 +00:zz', None), # invalid timezone minute
        ('Sun, 99 Jun 2009 12:00:00 GMT', None), # out-of-range day
    ),
    feedparser._parse_date_asctime: (
        (u'Sun Jan  4 16:29:06 2004', (2004, 1, 4, 16, 29, 6, 6, 4, 0)),
    ),
    feedparser._parse_date_w3dtf: (
        (u'', None), # empty string
        (u'2003-12-31T10:14:55Z', (2003, 12, 31, 10, 14, 55, 2, 365, 0)), # UTC
        (u'2003-12-31T10:14:55-08:00', (2003, 12, 31, 18, 14, 55, 2, 365, 0)), # San Francisco timezone
        (u'2003-12-31T18:14:55+08:00', (2003, 12, 31, 10, 14, 55, 2, 365, 0)), # Tokyo timezone
        (u'2007-04-23T23:25:47.538+10:00', (2007, 4, 23, 13, 25, 47, 0, 113, 0)), # fractional seconds
        (u'2003-12-31', (2003, 12, 31, 0, 0, 0, 2, 365, 0)), # year/month/day only
        (u'2003-12', (2003, 12, 1, 0, 0, 0, 0, 335, 0)), # year/month only
        (u'2003', (2003, 1, 1, 0, 0, 0, 2, 1, 0)), # year only
        # Special cases for rollovers in leap years
        (u'2004-02-28T18:14:55-08:00', (2004, 2, 29, 2, 14, 55, 6, 60, 0)), # feb 28 in leap year
        (u'2003-02-28T18:14:55-08:00', (2003, 3, 1, 2, 14, 55, 5, 60, 0)), # feb 28 in non-leap year
        (u'2000-02-28T18:14:55-08:00', (2000, 2, 29, 2, 14, 55, 1, 60, 0)), # feb 28 in leap year on century divisible by 400
        # Out-of-range times
        (u'9999-12-31T23:59:59-99:99', None), # Date is out-of-range
        (u'2003-12-31T25:14:55Z', None), # invalid (25 hours)
        (u'2003-12-31T10:61:55Z', None), # invalid (61 minutes)
        (u'2003-12-31T10:14:61Z', None), # invalid (61 seconds)
        # Invalid formats
        (u'22013', None), # Year is too long
        (u'013', None), # Year is too short
        (u'2013-01-27-01', None), # Date has to many parts
        (u'2013-01-28T11:30:00-06:00Textra', None), # Too many 't's
        # Non-integer values
        (u'2013-xx-27', None), # Date
        (u'2013-01-28T09:xx:00Z', None), # Time
        (u'2013-01-28T09:00:00+00:xx', None), # Timezone
        # MSSQL-style dates
        (u'2004-07-08 23:56:58 -00:20', (2004, 7, 9, 0, 16, 58, 4, 191, 0)), # with timezone
        (u'2004-07-08 23:56:58', (2004, 7, 8, 23, 56, 58, 3, 190, 0)), # without timezone
        (u'2004-07-08 23:56:58.0', (2004, 7, 8, 23, 56, 58, 3, 190, 0)), # with fractional second
    )
}

def make_date_test(f, s, t):
    return lambda self: self._check_date(f, s, t)

for func, items in date_tests.iteritems():
    for i, (dtstring, dttuple) in enumerate(items):
        uniqfunc = make_date_test(func, dtstring, dttuple)
        setattr(TestDateParsers, 'test_%s_%02i' % (func.__name__, i), uniqfunc)


class TestHTMLGuessing(unittest.TestCase):
    "Exercise the HTML sniffing code"
    def _mktest(text, expect, doc):
        def fn(self):
            value = bool(feedparser._FeedParserMixin.lookslikehtml(text))
            self.assertEqual(value, expect)
        fn.__doc__ = doc
        return fn

    test_text_1 = _mktest(u'plain text', False, u'plain text')
    test_text_2 = _mktest(u'2 < 3', False, u'plain text with angle bracket')
    test_html_1 = _mktest(u'<a href="">a</a>', True, u'anchor tag')
    test_html_2 = _mktest(u'<i>i</i>', True, u'italics tag')
    test_html_3 = _mktest(u'<b>b</b>', True, u'bold tag')
    test_html_4 = _mktest(u'<code>', False, u'allowed tag, no end tag')
    test_html_5 = _mktest(u'<rss> .. </rss>', False, u'disallowed tag')
    test_entity_1 = _mktest(u'AT&T', False, u'corporation name')
    test_entity_2 = _mktest(u'&copy;', True, u'named entity reference')
    test_entity_3 = _mktest(u'&#169;', True, u'numeric entity reference')
    test_entity_4 = _mktest(u'&#xA9;', True, u'hex numeric entity reference')

#---------- additional api unit tests, not backed by files

class TestBuildRequest(unittest.TestCase):
    "Test that HTTP request objects are created as expected"
    def test_extra_headers(self):
        """You can pass in extra headers and they go into the request object."""

        request = feedparser._build_urllib2_request(
          'http://example.com/feed',
          'agent-name',
          None, None, None, None,
          {'Cache-Control': 'max-age=0'})
        # nb, urllib2 folds the case of the headers
        self.assertEqual(
          request.get_header('Cache-control'), 'max-age=0')


class TestLxmlBug(unittest.TestCase):
    def test_lxml_etree_bug(self):
        try:
            import lxml.etree
        except ImportError:
            pass
        else:
            doc = u"<feed>&illformed_charref</feed>".encode('utf8')
            # Importing lxml.etree currently causes libxml2 to
            # throw SAXException instead of SAXParseException.
            feedparser.parse(feedparser._StringIO(doc))
        self.assertTrue(True)

#---------- parse test files and create test methods ----------
def convert_to_utf8(data):
    "Identify data's encoding using its byte order mark" \
    "and convert it to its utf-8 equivalent"
    if data[:4] == _l2bytes([0x4c, 0x6f, 0xa7, 0x94]):
        return data.decode('cp037').encode('utf-8')
    elif data[:4] == _l2bytes([0x00, 0x00, 0xfe, 0xff]):
        if not _UTF32_AVAILABLE:
            return None
        return data.decode('utf-32be').encode('utf-8')
    elif data[:4] == _l2bytes([0xff, 0xfe, 0x00, 0x00]):
        if not _UTF32_AVAILABLE:
            return None
        return data.decode('utf-32le').encode('utf-8')
    elif data[:4] == _l2bytes([0x00, 0x00, 0x00, 0x3c]):
        if not _UTF32_AVAILABLE:
            return None
        return data.decode('utf-32be').encode('utf-8')
    elif data[:4] == _l2bytes([0x3c, 0x00, 0x00, 0x00]):
        if not _UTF32_AVAILABLE:
            return None
        return data.decode('utf-32le').encode('utf-8')
    elif data[:4] == _l2bytes([0x00, 0x3c, 0x00, 0x3f]):
        return data.decode('utf-16be').encode('utf-8')
    elif data[:4] == _l2bytes([0x3c, 0x00, 0x3f, 0x00]):
        return data.decode('utf-16le').encode('utf-8')
    elif (data[:2] == _l2bytes([0xfe, 0xff])) and (data[2:4] != _l2bytes([0x00, 0x00])):
        return data[2:].decode('utf-16be').encode('utf-8')
    elif (data[:2] == _l2bytes([0xff, 0xfe])) and (data[2:4] != _l2bytes([0x00, 0x00])):
        return data[2:].decode('utf-16le').encode('utf-8')
    elif data[:3] == _l2bytes([0xef, 0xbb, 0xbf]):
        return data[3:]
    # no byte order mark was found
    return data

skip_re = re.compile(_s2bytes("SkipUnless:\s*(.*?)\n"))
desc_re = re.compile(_s2bytes("Description:\s*(.*?)\s*Expect:\s*(.*)\s*-->"))
def getDescription(xmlfile, data):
    """Extract test data

    Each test case is an XML file which contains not only a test feed
    but also the description of the test and the condition that we
    would expect the parser to create when it parses the feed.  Example:
    <!--
    Description: feed title
    Expect:      feed['title'] == u'Example feed'
    -->
    """
    skip_results = skip_re.search(data)
    if skip_results:
        skipUnless = skip_results.group(1).strip()
    else:
        skipUnless = '1'
    search_results = desc_re.search(data)
    if not search_results:
        raise RuntimeError, "can't parse %s" % xmlfile
    description, evalString = map(lambda s: s.strip(), list(search_results.groups()))
    description = xmlfile + ": " + unicode(description, 'utf8')
    return description, evalString, skipUnless

def buildTestCase(xmlfile, description, evalString):
    func = lambda self, xmlfile=xmlfile, evalString=evalString: \
         self.failUnlessEval(xmlfile, evalString)
    func.__doc__ = description
    return func

def runtests():
    "Read the files in the tests/ directory, dynamically add tests to the " \
    "TestCases above, spawn the HTTP server, and run the test suite"
    if sys.argv[1:]:
        allfiles = filter(lambda s: s.endswith('.xml'), reduce(operator.add, map(glob.glob, sys.argv[1:]), []))
        wellformedfiles = illformedfiles = encodingfiles = entitiesfiles = microformatfiles = []
        sys.argv = [sys.argv[0]] #+ sys.argv[2:]
    else:
        allfiles = glob.glob(os.path.join('.', 'tests', '**', '**', '*.xml'))
        wellformedfiles = glob.glob(os.path.join('.', 'tests', 'wellformed', '**', '*.xml'))
        illformedfiles = glob.glob(os.path.join('.', 'tests', 'illformed', '*.xml'))
        encodingfiles = glob.glob(os.path.join('.', 'tests', 'encoding', '*.xml'))
        entitiesfiles = glob.glob(os.path.join('.', 'tests', 'entities', '*.xml'))
        microformatfiles = glob.glob(os.path.join('.', 'tests', 'microformats', '**', '*.xml'))
    httpd = None
    # there are several compression test cases that must be accounted for
    # as well as a number of http status tests that redirect to a target
    # and a few `_open_resource`-related tests
    httpcount = 6 + 16 + 2
    httpcount += len([f for f in allfiles if 'http' in f])
    httpcount += len([f for f in wellformedfiles if 'http' in f])
    httpcount += len([f for f in illformedfiles if 'http' in f])
    httpcount += len([f for f in encodingfiles if 'http' in f])
    try:
        for c, xmlfile in enumerate(allfiles + encodingfiles + illformedfiles + entitiesfiles):
            addTo = TestCase
            if xmlfile in encodingfiles:
                addTo = TestEncodings
            elif xmlfile in entitiesfiles:
                addTo = (TestStrictParser, TestLooseParser)
            elif xmlfile in microformatfiles:
                addTo = TestMicroformats
            elif xmlfile in wellformedfiles:
                addTo = (TestStrictParser, TestLooseParser)
            f = open(xmlfile, 'rb')
            data = f.read()
            f.close()
            if 'encoding' in xmlfile:
                data = convert_to_utf8(data)
                if data is None:
                    # convert_to_utf8 found a byte order mark for utf_32
                    # but it's not supported in this installation of Python
                    if 'http' in xmlfile:
                        httpcount -= 1 + (xmlfile in wellformedfiles)
                    continue
            description, evalString, skipUnless = getDescription(xmlfile, data)
            testName = 'test_%06d' % c
            ishttp = 'http' in xmlfile
            try:
                if not eval(skipUnless): raise NotImplementedError
            except (ImportError, LookupError, NotImplementedError, AttributeError):
                if ishttp:
                    httpcount -= 1 + (xmlfile in wellformedfiles)
                continue
            if ishttp:
                xmlfile = 'http://%s:%s/%s' % (_HOST, _PORT, posixpath.normpath(xmlfile.replace('\\', '/')))
            testFunc = buildTestCase(xmlfile, description, evalString)
            if isinstance(addTo, tuple):
                setattr(addTo[0], testName, testFunc)
                setattr(addTo[1], testName, testFunc)
            else:
                setattr(addTo, testName, testFunc)
        if httpcount:
            httpd = FeedParserTestServer(httpcount)
            httpd.daemon = True
            httpd.start()
            httpd.ready.wait()
        testsuite = unittest.TestSuite()
        testloader = unittest.TestLoader()
        testsuite.addTest(testloader.loadTestsFromTestCase(TestCase))
        testsuite.addTest(testloader.loadTestsFromTestCase(TestStrictParser))
        testsuite.addTest(testloader.loadTestsFromTestCase(TestLooseParser))
        testsuite.addTest(testloader.loadTestsFromTestCase(TestEncodings))
        testsuite.addTest(testloader.loadTestsFromTestCase(TestDateParsers))
        testsuite.addTest(testloader.loadTestsFromTestCase(TestHTMLGuessing))
        testsuite.addTest(testloader.loadTestsFromTestCase(TestHTTPStatus))
        testsuite.addTest(testloader.loadTestsFromTestCase(TestCompression))
        testsuite.addTest(testloader.loadTestsFromTestCase(TestConvertToIdn))
        testsuite.addTest(testloader.loadTestsFromTestCase(TestMicroformats))
        testsuite.addTest(testloader.loadTestsFromTestCase(TestOpenResource))
        testsuite.addTest(testloader.loadTestsFromTestCase(TestFeedParserDict))
        testsuite.addTest(testloader.loadTestsFromTestCase(TestMakeSafeAbsoluteURI))
        testsuite.addTest(testloader.loadTestsFromTestCase(TestEverythingIsUnicode))
        testsuite.addTest(testloader.loadTestsFromTestCase(TestTemporaryFallbackBehavior))
        testsuite.addTest(testloader.loadTestsFromTestCase(TestLxmlBug))
        testresults = unittest.TextTestRunner(verbosity=1).run(testsuite)

        # Return 0 if successful, 1 if there was a failure
        sys.exit(not testresults.wasSuccessful())
    finally:
        if httpd:
            if httpd.requests:
                # Should never get here unless something went horribly wrong, like the
                # user hitting Ctrl-C.  Tell our HTTP server that it's done, then do
                # one more request to flush it.  This rarely works; the combination of
                # threading, self-terminating HTTP servers, and unittest is really
                # quite flaky.  Just what you want in a testing framework, no?
                httpd.requests = 0
                if httpd.ready:
                    urllib.urlopen('http://127.0.0.1:8097/tests/wellformed/rss/aaa_wellformed.xml').read()
            httpd.join(0)

if __name__ == "__main__":
    runtests()

########NEW FILE########
__FILENAME__ = sgmllib3
"""A parser for SGML, using the derived class as a static DTD."""

# XXX This only supports those SGML features used by HTML.

# XXX There should be a way to distinguish between PCDATA (parsed
# character data -- the normal case), RCDATA (replaceable character
# data -- only char and entity references and end tags are special)
# and CDATA (character data -- only end tags are special).  RCDATA is
# not supported at all.

import _markupbase
import re

__all__ = ["SGMLParser", "SGMLParseError"]

# Regular expressions used for parsing

interesting = re.compile('[&<]')
incomplete = re.compile('&([a-zA-Z][a-zA-Z0-9]*|#[0-9]*)?|'
                           '<([a-zA-Z][^<>]*|'
                              '/([a-zA-Z][^<>]*)?|'
                              '![^<>]*)?')

entityref = re.compile('&([a-zA-Z][-.a-zA-Z0-9]*)[^a-zA-Z0-9]')
charref = re.compile('&#([0-9]+)[^0-9]')

starttagopen = re.compile('<[>a-zA-Z]')
shorttagopen = re.compile('<[a-zA-Z][-.a-zA-Z0-9]*/')
shorttag = re.compile('<([a-zA-Z][-.a-zA-Z0-9]*)/([^/]*)/')
piclose = re.compile('>')
endbracket = re.compile('[<>]')
tagfind = re.compile('[a-zA-Z][-_.a-zA-Z0-9]*')
attrfind = re.compile(
    r'\s*([a-zA-Z_][-:.a-zA-Z_0-9]*)(\s*=\s*'
    r'(\'[^\']*\'|"[^"]*"|[][\-a-zA-Z0-9./,:;+*%?!&$\(\)_#=~\'"@]*))?')


class SGMLParseError(RuntimeError):
    """Exception raised for all parse errors."""
    pass


# SGML parser base class -- find tags and call handler functions.
# Usage: p = SGMLParser(); p.feed(data); ...; p.close().
# The dtd is defined by deriving a class which defines methods
# with special names to handle tags: start_foo and end_foo to handle
# <foo> and </foo>, respectively, or do_foo to handle <foo> by itself.
# (Tags are converted to lower case for this purpose.)  The data
# between tags is passed to the parser by calling self.handle_data()
# with some data as argument (the data may be split up in arbitrary
# chunks).  Entity references are passed by calling
# self.handle_entityref() with the entity reference as argument.

class SGMLParser(_markupbase.ParserBase):
    # Definition of entities -- derived classes may override
    entity_or_charref = re.compile('&(?:'
      '([a-zA-Z][-.a-zA-Z0-9]*)|#([0-9]+)'
      ')(;?)')

    def __init__(self, verbose=0):
        """Initialize and reset this instance."""
        self.verbose = verbose
        self.reset()

    def reset(self):
        """Reset this instance. Loses all unprocessed data."""
        self.__starttag_text = None
        self.rawdata = ''
        self.stack = []
        self.lasttag = '???'
        self.nomoretags = 0
        self.literal = 0
        _markupbase.ParserBase.reset(self)

    def setnomoretags(self):
        """Enter literal mode (CDATA) till EOF.

        Intended for derived classes only.
        """
        self.nomoretags = self.literal = 1

    def setliteral(self, *args):
        """Enter literal mode (CDATA).

        Intended for derived classes only.
        """
        self.literal = 1

    def feed(self, data):
        """Feed some data to the parser.

        Call this as often as you want, with as little or as much text
        as you want (may include '\n').  (This just saves the text,
        all the processing is done by goahead().)
        """

        self.rawdata = self.rawdata + data
        self.goahead(0)

    def close(self):
        """Handle the remaining data."""
        self.goahead(1)

    def error(self, message):
        raise SGMLParseError(message)

    # Internal -- handle data as far as reasonable.  May leave state
    # and data to be processed by a subsequent call.  If 'end' is
    # true, force handling all data as if followed by EOF marker.
    def goahead(self, end):
        rawdata = self.rawdata
        i = 0
        n = len(rawdata)
        while i < n:
            if self.nomoretags:
                self.handle_data(rawdata[i:n])
                i = n
                break
            match = interesting.search(rawdata, i)
            if match: j = match.start()
            else: j = n
            if i < j:
                self.handle_data(rawdata[i:j])
            i = j
            if i == n: break
            if rawdata[i] == '<':
                if starttagopen.match(rawdata, i):
                    if self.literal:
                        self.handle_data(rawdata[i])
                        i = i+1
                        continue
                    k = self.parse_starttag(i)
                    if k < 0: break
                    i = k
                    continue
                if rawdata.startswith("</", i):
                    k = self.parse_endtag(i)
                    if k < 0: break
                    i = k
                    self.literal = 0
                    continue
                if self.literal:
                    if n > (i + 1):
                        self.handle_data("<")
                        i = i+1
                    else:
                        # incomplete
                        break
                    continue
                if rawdata.startswith("<!--", i):
                        # Strictly speaking, a comment is --.*--
                        # within a declaration tag <!...>.
                        # This should be removed,
                        # and comments handled only in parse_declaration.
                    k = self.parse_comment(i)
                    if k < 0: break
                    i = k
                    continue
                if rawdata.startswith("<?", i):
                    k = self.parse_pi(i)
                    if k < 0: break
                    i = i+k
                    continue
                if rawdata.startswith("<!", i):
                    # This is some sort of declaration; in "HTML as
                    # deployed," this should only be the document type
                    # declaration ("<!DOCTYPE html...>").
                    k = self.parse_declaration(i)
                    if k < 0: break
                    i = k
                    continue
            elif rawdata[i] == '&':
                if self.literal:
                    self.handle_data(rawdata[i])
                    i = i+1
                    continue
                match = charref.match(rawdata, i)
                if match:
                    name = match.group(1)
                    self.handle_charref(name)
                    i = match.end(0)
                    if rawdata[i-1] != ';': i = i-1
                    continue
                match = entityref.match(rawdata, i)
                if match:
                    name = match.group(1)
                    self.handle_entityref(name)
                    i = match.end(0)
                    if rawdata[i-1] != ';': i = i-1
                    continue
            else:
                self.error('neither < nor & ??')
            # We get here only if incomplete matches but
            # nothing else
            match = incomplete.match(rawdata, i)
            if not match:
                self.handle_data(rawdata[i])
                i = i+1
                continue
            j = match.end(0)
            if j == n:
                break # Really incomplete
            self.handle_data(rawdata[i:j])
            i = j
        # end while
        if end and i < n:
            self.handle_data(rawdata[i:n])
            i = n
        self.rawdata = rawdata[i:]
        # XXX if end: check for empty stack

    # Extensions for the DOCTYPE scanner:
    _decl_otherchars = '='

    # Internal -- parse processing instr, return length or -1 if not terminated
    def parse_pi(self, i):
        rawdata = self.rawdata
        if rawdata[i:i+2] != '<?':
            self.error('unexpected call to parse_pi()')
        match = piclose.search(rawdata, i+2)
        if not match:
            return -1
        j = match.start(0)
        self.handle_pi(rawdata[i+2: j])
        j = match.end(0)
        return j-i

    def get_starttag_text(self):
        return self.__starttag_text

    # Internal -- handle starttag, return length or -1 if not terminated
    def parse_starttag(self, i):
        self.__starttag_text = None
        start_pos = i
        rawdata = self.rawdata
        if shorttagopen.match(rawdata, i):
            # SGML shorthand: <tag/data/ == <tag>data</tag>
            # XXX Can data contain &... (entity or char refs)?
            # XXX Can data contain < or > (tag characters)?
            # XXX Can there be whitespace before the first /?
            match = shorttag.match(rawdata, i)
            if not match:
                return -1
            tag, data = match.group(1, 2)
            self.__starttag_text = '<%s/' % tag
            tag = tag.lower()
            k = match.end(0)
            self.finish_shorttag(tag, data)
            self.__starttag_text = rawdata[start_pos:match.end(1) + 1]
            return k
        # XXX The following should skip matching quotes (' or ")
        # As a shortcut way to exit, this isn't so bad, but shouldn't
        # be used to locate the actual end of the start tag since the
        # < or > characters may be embedded in an attribute value.
        match = endbracket.search(rawdata, i+1)
        if not match:
            return -1
        j = match.start(0)
        # Now parse the data between i+1 and j into a tag and attrs
        attrs = []
        if rawdata[i:i+2] == '<>':
            # SGML shorthand: <> == <last open tag seen>
            k = j
            tag = self.lasttag
        else:
            match = tagfind.match(rawdata, i+1)
            if not match:
                self.error('unexpected call to parse_starttag')
            k = match.end(0)
            tag = rawdata[i+1:k].lower()
            self.lasttag = tag
        while k < j:
            match = attrfind.match(rawdata, k)
            if not match: break
            attrname, rest, attrvalue = match.group(1, 2, 3)
            if not rest:
                attrvalue = attrname
            else:
                if (attrvalue[:1] == "'" == attrvalue[-1:] or
                    attrvalue[:1] == '"' == attrvalue[-1:]):
                    # strip quotes
                    attrvalue = attrvalue[1:-1]
                attrvalue = self.entity_or_charref.sub(
                    self._convert_ref, attrvalue)
            attrs.append((attrname.lower(), attrvalue))
            k = match.end(0)
        if rawdata[j] == '>':
            j = j+1
        self.__starttag_text = rawdata[start_pos:j]
        self.finish_starttag(tag, attrs)
        return j

    # Internal -- convert entity or character reference
    def _convert_ref(self, match):
        if match.group(2):
            return self.convert_charref(match.group(2)) or \
                '&#%s%s' % match.groups()[1:]
        elif match.group(3):
            return self.convert_entityref(match.group(1)) or \
                '&%s;' % match.group(1)
        else:
            return '&%s' % match.group(1)

    # Internal -- parse endtag
    def parse_endtag(self, i):
        rawdata = self.rawdata
        match = endbracket.search(rawdata, i+1)
        if not match:
            return -1
        j = match.start(0)
        tag = rawdata[i+2:j].strip().lower()
        if rawdata[j] == '>':
            j = j+1
        self.finish_endtag(tag)
        return j

    # Internal -- finish parsing of <tag/data/ (same as <tag>data</tag>)
    def finish_shorttag(self, tag, data):
        self.finish_starttag(tag, [])
        self.handle_data(data)
        self.finish_endtag(tag)

    # Internal -- finish processing of start tag
    # Return -1 for unknown tag, 0 for open-only tag, 1 for balanced tag
    def finish_starttag(self, tag, attrs):
        try:
            method = getattr(self, 'start_' + tag)
        except AttributeError:
            try:
                method = getattr(self, 'do_' + tag)
            except AttributeError:
                self.unknown_starttag(tag, attrs)
                return -1
            else:
                self.handle_starttag(tag, method, attrs)
                return 0
        else:
            self.stack.append(tag)
            self.handle_starttag(tag, method, attrs)
            return 1

    # Internal -- finish processing of end tag
    def finish_endtag(self, tag):
        if not tag:
            found = len(self.stack) - 1
            if found < 0:
                self.unknown_endtag(tag)
                return
        else:
            if tag not in self.stack:
                try:
                    method = getattr(self, 'end_' + tag)
                except AttributeError:
                    self.unknown_endtag(tag)
                else:
                    self.report_unbalanced(tag)
                return
            found = len(self.stack)
            for i in range(found):
                if self.stack[i] == tag: found = i
        while len(self.stack) > found:
            tag = self.stack[-1]
            try:
                method = getattr(self, 'end_' + tag)
            except AttributeError:
                method = None
            if method:
                self.handle_endtag(tag, method)
            else:
                self.unknown_endtag(tag)
            del self.stack[-1]

    # Overridable -- handle start tag
    def handle_starttag(self, tag, method, attrs):
        method(attrs)

    # Overridable -- handle end tag
    def handle_endtag(self, tag, method):
        method()

    # Example -- report an unbalanced </...> tag.
    def report_unbalanced(self, tag):
        if self.verbose:
            print('*** Unbalanced </' + tag + '>')
            print('*** Stack:', self.stack)

    def convert_charref(self, name):
        """Convert character reference, may be overridden."""
        try:
            n = int(name)
        except ValueError:
            return
        if not 0 <= n <= 127:
            return
        return self.convert_codepoint(n)

    def convert_codepoint(self, codepoint):
        return chr(codepoint)

    def handle_charref(self, name):
        """Handle character reference, no need to override."""
        replacement = self.convert_charref(name)
        if replacement is None:
            self.unknown_charref(name)
        else:
            self.handle_data(replacement)

    # Definition of entities -- derived classes may override
    entitydefs = \
            {'lt': '<', 'gt': '>', 'amp': '&', 'quot': '"', 'apos': '\''}

    def convert_entityref(self, name):
        """Convert entity references.

        As an alternative to overriding this method; one can tailor the
        results by setting up the self.entitydefs mapping appropriately.
        """
        table = self.entitydefs
        if name in table:
            return table[name]
        else:
            return

    def handle_entityref(self, name):
        """Handle entity references, no need to override."""
        replacement = self.convert_entityref(name)
        if replacement is None:
            self.unknown_entityref(name)
        else:
            self.handle_data(replacement)

    # Example -- handle data, should be overridden
    def handle_data(self, data):
        pass

    # Example -- handle comment, could be overridden
    def handle_comment(self, data):
        pass

    # Example -- handle declaration, could be overridden
    def handle_decl(self, decl):
        pass

    # Example -- handle processing instruction, could be overridden
    def handle_pi(self, data):
        pass

    # To be overridden -- handlers for unknown objects
    def unknown_starttag(self, tag, attrs): pass
    def unknown_endtag(self, tag): pass
    def unknown_charref(self, ref): pass
    def unknown_entityref(self, ref): pass


class TestSGMLParser(SGMLParser):

    def __init__(self, verbose=0):
        self.testdata = ""
        SGMLParser.__init__(self, verbose)

    def handle_data(self, data):
        self.testdata = self.testdata + data
        if len(repr(self.testdata)) >= 70:
            self.flush()

    def flush(self):
        data = self.testdata
        if data:
            self.testdata = ""
            print('data:', repr(data))

    def handle_comment(self, data):
        self.flush()
        r = repr(data)
        if len(r) > 68:
            r = r[:32] + '...' + r[-32:]
        print('comment:', r)

    def unknown_starttag(self, tag, attrs):
        self.flush()
        if not attrs:
            print('start tag: <' + tag + '>')
        else:
            print('start tag: <' + tag, end=' ')
            for name, value in attrs:
                print(name + '=' + '"' + value + '"', end=' ')
            print('>')

    def unknown_endtag(self, tag):
        self.flush()
        print('end tag: </' + tag + '>')

    def unknown_entityref(self, ref):
        self.flush()
        print('*** unknown entity ref: &' + ref + ';')

    def unknown_charref(self, ref):
        self.flush()
        print('*** unknown char ref: &#' + ref + ';')

    def unknown_decl(self, data):
        self.flush()
        print('*** unknown decl: [' + data + ']')

    def close(self):
        SGMLParser.close(self)
        self.flush()


def test(args = None):
    import sys

    if args is None:
        args = sys.argv[1:]

    if args and args[0] == '-s':
        args = args[1:]
        klass = SGMLParser
    else:
        klass = TestSGMLParser

    if args:
        file = args[0]
    else:
        file = 'test.html'

    if file == '-':
        f = sys.stdin
    else:
        try:
            f = open(file, 'r')
        except IOError as msg:
            print(file, ":", msg)
            sys.exit(1)

    data = f.read()
    if f is not sys.stdin:
        f.close()

    x = klass()
    for c in data:
        x.feed(c)
    x.close()


if __name__ == '__main__':
    test()

########NEW FILE########
