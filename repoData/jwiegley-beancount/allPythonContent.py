__FILENAME__ = assetdef
"""
Asset definition code.

This code can be used to load properties of specific assets from Python modules
with a given set of attributes.
"""

# stdlib imports
import os, re, dircache
from os.path import *


# A dictionary of commodity names to filenames or dict-of-properties.
_commfiles = {}

def add_asset_path(dn):
    for root, dirs, files in os.walk(dn):
        for fn in files:
            if not re.match('[A-Z0-9-.]+$', fn):
                continue
            if fn not in _commfiles:
                _commfiles[fn] = join(root, fn)
                    
def load_asset(fn):
    """ Loan a single asset definition from a file, in Python language."""
    if not exists(fn):
        return None
    d = {}
    execfile(fn, d)
## FIXME: we could insure that some set of attributes is defined.
    return d

def get_asset(comm):
    """
    Find and load the properties of commodity 'comm'. Loading is done lazily,
    since there may be many more definitions than are necessary in typical
    usage.
    """
    try:
        adef = _commfiles[comm]
    except KeyError:
        return None # No properties could be found.

    if isinstance(adef, (str, unicode)):
        adef = _commfiles[comm] = load_asset(fn)

    return adef




########NEW FILE########
__FILENAME__ = beantest
"""
Support for tests.
"""

# beancount imports
from beancount.ledger import Ledger
from beancount.wallet import Wallet


def ledger_str(s, name):
    l = Ledger()
    l.parse_string(s, name=name)
    l.run_directives()
    return l



########NEW FILE########
__FILENAME__ = cmdline
"""
Common cmdline interface for ledger scripts.
"""

# stdlib imports
import sys, os, logging, optparse, re, codecs
from datetime import date
import cPickle as pickle
from os.path import exists, getmtime

# other imports
from beancount.fallback.colorlog import ColorFormatter

# beancount imports
from beancount.ledger import Ledger
from beancount.timeparse import parse_time, parse_one_time
from beancount import install_psyco
from beancount import assetdef


MANY=-1

DATE_WAAAYBACK = date(1800, 1, 1)
DATE_WAAAYFWD = date(4000, 1, 1)

def main(parser, no=MANY):
    "Parse the cmdline as a list of ledger source files and return a Ledger."

    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)-8s:%(message)s')

    parser.add_option('-v', '--verbose', action='store_true',
                      help="Display warnings and non-essential information.")

    parser.add_option('-e', '--encoding', '--input-encoding', action='store',
                      default='utf8',
                      help="Specify the encoding of the input files.")

    parser.add_option('-C', '--no-color',
                      dest='color', action='store_false', default=True,
                      help="Disable color terminal output.")

    parser.add_option('--no-psyco', action='store_true',
                      help="Disable psyco JIT optimizations.")

    parser.add_option('--assets', action='append', default=[],
                      help="Root directories for asset definition files.")

    parser.add_option('--unsafe', '--with-source',
                      action='store_false', default=True,
                      help="Allow serving some possibly sensitive personal "
                      "informations, access to source file, for example.")

    opts, args = parser.parse_args()

    logging.getLogger().setLevel(logging.INFO if opts.verbose else logging.ERROR)

    if sys.stderr.isatty() and opts.color:
        hndlr = logging.getLogger().handlers[-1]
        hndlr.setFormatter(ColorFormatter(hndlr.stream, hndlr.formatter._fmt))

    if not args:
        # Note: the support for env var input is only there to avoid putting off
        # existing ledger users. Remove when it makes sense.
        try:
            args.append(os.environ['LEDGER_FILE'])
        except KeyError:
            parser.error("You must provide some files or set the "
                         "environment variable LEDGER_FILE.")

    if not opts.no_psyco:
        install_psyco()

    for assfn in opts.assets:
        assetdef.add_asset_path(assfn)

    if hasattr(opts, 'begin') and opts.begin:
        opts.begin, _ = parse_one_time(opts.begin)
    if hasattr(opts, 'end') and opts.end:
        opts.end, _ = parse_one_time(opts.end)

    if no == 0:
        return opts, None, args
    elif no == 1:
        ledger = load_ledger(parser, args[0:1], opts)
        args = args[1:]
        return opts, ledger, args
    elif no == MANY:
        ledger = load_ledger(parser, args, opts)
        return opts, ledger, args

def load_ledger(parser, filenames, opts):
    # logging.info("Parsing Ledger source file: %s" % fn)
    ledger = Ledger()
    for fn in filenames:
        if fn == '-':
            f = sys.stdin
        else:
            f = open(fn)
        if opts.encoding:
            Reader = codecs.getreader(opts.encoding)
            f = Reader(f)
        ledger.parse_file(f, fn, opts.encoding)

    run_postprocesses(ledger, opts)

    return ledger

def reload(ledger, opts):
    """
    Parse the files again and create a new Ledger from them.
    """
    # Note: we ignore the pickling for reload.
    ledger2 = Ledger()

    for fn, encoding in ledger.parsed_files:
        f = open(fn)
        if encoding:
            Reader = codecs.getreader(encoding)
            f = Reader(f)
        ledger2.parse_file(f, fn, encoding)

    run_postprocesses(ledger2, opts)

    return ledger2

def run_postprocesses(ledger, opts):
    ledger.run_directives()

    if hasattr(opts, 'begin') and opts.begin:
        ledger.close_books(opts.begin)

    filter_opts = 'account', 'transaction_account', 'note', 'begin', 'end', 'tag'

    if all(hasattr(opts, x) for x in filter_opts):
        pred = create_filter_pred(opts)
        ledger.filter_postings(pred)

    ledger.compute_balsheet('total')




"""
Code to filter down specific postings.
"""

def addopts(parser):
    "Add options for selecting accounts/postings."

    parser.add_option('--begin', '--start', '--close', dest='begin',
                      action='store', metavar='TIME_EXPR',
                      help="Begin time in the interval in use for the flow "
                      "statements (e.g. Income Statement). If specified, "
                      "synthetic entries are inserted to close the books at "
                      "that time, so that level amounts are calculated properly.")

    parser.add_option('--end', '--stop', dest='end',
                      action='store', metavar='TIME_EXPR',
                      help="Ignore postings with a date after the given date. "
                      "This allows the flow statements (e.g. Income Statement) "
                      "to focus on a finite period.")

    group = optparse.OptionGroup(parser, "Options for filtering postings.")

    group.add_option('-a', '--account', action='append', metavar='REGEXP',
                     default=[],
                     help="Filter only the postings whose account matches "
                     "the given regexp.")

    group.add_option('-A', '--transaction-account',
                     action='append', metavar='REGEXP', default=[],
                     help="Filter only the transactions which have at least "
                     "one account which matches the given regexp.")

    group.add_option('-n', '--note', action='append', metavar='REGEXP',
                     help="Filter only the postings with the given notes.")

    group.add_option('-g', '-t', '--tag', action='store', metavar='REGEXP',
                     help="Filter only the postings whose tag matches the "
                     "expression.")

    parser.add_option_group(group)


def create_filter_pred(opts):
    """
    Synthesize and return a predicate that when applied to a Ledger's postings
    will filter only the transactions specified in 'opts'. If there is no filter
    to be applied, simply return None.
    """
    acc_funs = None
    if opts.account:
        try:
            acc_funs = [re.compile(regexp, re.I).search for regexp in opts.account]
        except re.error, e:
            raise SystemExit(e)

    txnacc_funs = None
    if opts.transaction_account:
        try:
            txnacc_funs = [re.compile(regexp, re.I).search for regexp in opts.transaction_account]
        except re.error, e:
            raise SystemExit(e)

    note_funs = None
    if opts.note:
        try:
            note_funs = [re.compile(regexp, re.I).search for regexp in opts.note]
        except re.error, e:
            raise SystemExit(e)


    if opts.begin or opts.end:
        begin = opts.begin or DATE_WAAAYBACK
        end = opts.end or DATE_WAAAYFWD
        interval = (begin, end)
        logging.info("Filtering by interval:  %s  ->  %s" % interval)
    else:
        interval = None

    if opts.tag:
        try:
            tagfun = lambda tags: opts.tag in tags
        except re.error, e:
            raise SystemExit(e)
    else:
        tagfun = None

    if all((x is None) for x in
           (acc_funs, txnacc_funs, note_funs, interval, tagfun)):
        # Simpler predicate for speed optimization.
        def pred(post):
            return True
    else:
        def pred(post):
            if acc_funs is not None:
                if all(not fun(post.get_account_name()) for fun in acc_funs):
                    return False
            if txnacc_funs is not None:
                if all(all(not fun(p.account.fullname) for fun in txnacc_funs)
                       for p in post.get_txn_postings()):
                    return False
            if note_funs is not None:
                if all(not fun(post.get_note() or '') for fun in note_funs):
                    return False
            if interval is not None:
                dbegin, dend = interval
                if not (dbegin <= post.get_date() < dend):
                    return False
            if tagfun is not None:
                tags = post.get_tags()
                if not (tags and tagfun(tags)):
                    return False
            return True

    return pred



########NEW FILE########
__FILENAME__ = BeautifulSoup
"""Beautiful Soup
Elixir and Tonic
"The Screen-Scraper's Friend"
http://www.crummy.com/software/BeautifulSoup/

Beautiful Soup parses a (possibly invalid) XML or HTML document into a
tree representation. It provides methods and Pythonic idioms that make
it easy to navigate, search, and modify the tree.

A well-formed XML/HTML document yields a well-formed data
structure. An ill-formed XML/HTML document yields a correspondingly
ill-formed data structure. If your document is only locally
well-formed, you can use this library to find and process the
well-formed part of it.

Beautiful Soup works with Python 2.2 and up. It has no external
dependencies, but you'll have more success at converting data to UTF-8
if you also install these three packages:

* chardet, for auto-detecting character encodings
  http://chardet.feedparser.org/
* cjkcodecs and iconv_codec, which add more encodings to the ones supported
  by stock Python.
  http://cjkpython.i18n.org/

Beautiful Soup defines classes for two main parsing strategies:

 * BeautifulStoneSoup, for parsing XML, SGML, or your domain-specific
   language that kind of looks like XML.

 * BeautifulSoup, for parsing run-of-the-mill HTML code, be it valid
   or invalid. This class has web browser-like heuristics for
   obtaining a sensible parse tree in the face of common HTML errors.

Beautiful Soup also defines a class (UnicodeDammit) for autodetecting
the encoding of an HTML or XML document, and converting it to
Unicode. Much of this code is taken from Mark Pilgrim's Universal Feed Parser.

For more than you ever wanted to know about Beautiful Soup, see the
documentation:
http://www.crummy.com/software/BeautifulSoup/documentation.html

Here, have some legalese:

Copyright (c) 2004-2008, Leonard Richardson

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

  * Redistributions in binary form must reproduce the above
    copyright notice, this list of conditions and the following
    disclaimer in the documentation and/or other materials provided
    with the distribution.

  * Neither the name of the the Beautiful Soup Consortium and All
    Night Kosher Bakery nor the names of its contributors may be
    used to endorse or promote products derived from this software
    without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE, DAMMIT.

"""
from __future__ import generators

__author__ = "Leonard Richardson (leonardr@segfault.org)"
__version__ = "3.0.7"
__copyright__ = "Copyright (c) 2004-2008 Leonard Richardson"
__license__ = "New-style BSD"

from sgmllib import SGMLParser, SGMLParseError
import codecs
import markupbase
import types
import re
import sgmllib
try:
  from htmlentitydefs import name2codepoint
except ImportError:
  name2codepoint = {}

#These hacks make Beautiful Soup able to parse XML with namespaces
sgmllib.tagfind = re.compile('[a-zA-Z][-_.:a-zA-Z0-9]*')
markupbase._declname_match = re.compile(r'[a-zA-Z][-_.:a-zA-Z0-9]*\s*').match

DEFAULT_OUTPUT_ENCODING = "utf-8"

# First, the classes that represent markup elements.

class PageElement:
    """Contains the navigational information for some part of the page
    (either a tag or a piece of text)"""

    def setup(self, parent=None, previous=None):
        """Sets up the initial relations between this element and
        other elements."""
        self.parent = parent
        self.previous = previous
        self.next = None
        self.previousSibling = None
        self.nextSibling = None
        if self.parent and self.parent.contents:
            self.previousSibling = self.parent.contents[-1]
            self.previousSibling.nextSibling = self

    def replaceWith(self, replaceWith):
        oldParent = self.parent
        myIndex = self.parent.contents.index(self)
        if hasattr(replaceWith, 'parent') and replaceWith.parent == self.parent:
            # We're replacing this element with one of its siblings.
            index = self.parent.contents.index(replaceWith)
            if index and index < myIndex:
                # Furthermore, it comes before this element. That
                # means that when we extract it, the index of this
                # element will change.
                myIndex = myIndex - 1
        self.extract()
        oldParent.insert(myIndex, replaceWith)

    def extract(self):
        """Destructively rips this element out of the tree."""
        if self.parent:
            try:
                self.parent.contents.remove(self)
            except ValueError:
                pass

        #Find the two elements that would be next to each other if
        #this element (and any children) hadn't been parsed. Connect
        #the two.
        lastChild = self._lastRecursiveChild()
        nextElement = lastChild.next

        if self.previous:
            self.previous.next = nextElement
        if nextElement:
            nextElement.previous = self.previous
        self.previous = None
        lastChild.next = None

        self.parent = None
        if self.previousSibling:
            self.previousSibling.nextSibling = self.nextSibling
        if self.nextSibling:
            self.nextSibling.previousSibling = self.previousSibling
        self.previousSibling = self.nextSibling = None
        return self

    def _lastRecursiveChild(self):
        "Finds the last element beneath this object to be parsed."
        lastChild = self
        while hasattr(lastChild, 'contents') and lastChild.contents:
            lastChild = lastChild.contents[-1]
        return lastChild

    def insert(self, position, newChild):
        if (isinstance(newChild, basestring)
            or isinstance(newChild, unicode)) \
            and not isinstance(newChild, NavigableString):
            newChild = NavigableString(newChild)

        position =  min(position, len(self.contents))
        if hasattr(newChild, 'parent') and newChild.parent != None:
            # We're 'inserting' an element that's already one
            # of this object's children.
            if newChild.parent == self:
                index = self.find(newChild)
                if index and index < position:
                    # Furthermore we're moving it further down the
                    # list of this object's children. That means that
                    # when we extract this element, our target index
                    # will jump down one.
                    position = position - 1
            newChild.extract()

        newChild.parent = self
        previousChild = None
        if position == 0:
            newChild.previousSibling = None
            newChild.previous = self
        else:
            previousChild = self.contents[position-1]
            newChild.previousSibling = previousChild
            newChild.previousSibling.nextSibling = newChild
            newChild.previous = previousChild._lastRecursiveChild()
        if newChild.previous:
            newChild.previous.next = newChild

        newChildsLastElement = newChild._lastRecursiveChild()

        if position >= len(self.contents):
            newChild.nextSibling = None

            parent = self
            parentsNextSibling = None
            while not parentsNextSibling:
                parentsNextSibling = parent.nextSibling
                parent = parent.parent
                if not parent: # This is the last element in the document.
                    break
            if parentsNextSibling:
                newChildsLastElement.next = parentsNextSibling
            else:
                newChildsLastElement.next = None
        else:
            nextChild = self.contents[position]
            newChild.nextSibling = nextChild
            if newChild.nextSibling:
                newChild.nextSibling.previousSibling = newChild
            newChildsLastElement.next = nextChild

        if newChildsLastElement.next:
            newChildsLastElement.next.previous = newChildsLastElement
        self.contents.insert(position, newChild)

    def append(self, tag):
        """Appends the given tag to the contents of this tag."""
        self.insert(len(self.contents), tag)

    def findNext(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the first item that matches the given criteria and
        appears after this Tag in the document."""
        return self._findOne(self.findAllNext, name, attrs, text, **kwargs)

    def findAllNext(self, name=None, attrs={}, text=None, limit=None,
                    **kwargs):
        """Returns all items that match the given criteria and appear
        after this Tag in the document."""
        return self._findAll(name, attrs, text, limit, self.nextGenerator,
                             **kwargs)

    def findNextSibling(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the closest sibling to this Tag that matches the
        given criteria and appears after this Tag in the document."""
        return self._findOne(self.findNextSiblings, name, attrs, text,
                             **kwargs)

    def findNextSiblings(self, name=None, attrs={}, text=None, limit=None,
                         **kwargs):
        """Returns the siblings of this Tag that match the given
        criteria and appear after this Tag in the document."""
        return self._findAll(name, attrs, text, limit,
                             self.nextSiblingGenerator, **kwargs)
    fetchNextSiblings = findNextSiblings # Compatibility with pre-3.x

    def findPrevious(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the first item that matches the given criteria and
        appears before this Tag in the document."""
        return self._findOne(self.findAllPrevious, name, attrs, text, **kwargs)

    def findAllPrevious(self, name=None, attrs={}, text=None, limit=None,
                        **kwargs):
        """Returns all items that match the given criteria and appear
        before this Tag in the document."""
        return self._findAll(name, attrs, text, limit, self.previousGenerator,
                           **kwargs)
    fetchPrevious = findAllPrevious # Compatibility with pre-3.x

    def findPreviousSibling(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the closest sibling to this Tag that matches the
        given criteria and appears before this Tag in the document."""
        return self._findOne(self.findPreviousSiblings, name, attrs, text,
                             **kwargs)

    def findPreviousSiblings(self, name=None, attrs={}, text=None,
                             limit=None, **kwargs):
        """Returns the siblings of this Tag that match the given
        criteria and appear before this Tag in the document."""
        return self._findAll(name, attrs, text, limit,
                             self.previousSiblingGenerator, **kwargs)
    fetchPreviousSiblings = findPreviousSiblings # Compatibility with pre-3.x

    def findParent(self, name=None, attrs={}, **kwargs):
        """Returns the closest parent of this Tag that matches the given
        criteria."""
        # NOTE: We can't use _findOne because findParents takes a different
        # set of arguments.
        r = None
        l = self.findParents(name, attrs, 1)
        if l:
            r = l[0]
        return r

    def findParents(self, name=None, attrs={}, limit=None, **kwargs):
        """Returns the parents of this Tag that match the given
        criteria."""

        return self._findAll(name, attrs, None, limit, self.parentGenerator,
                             **kwargs)
    fetchParents = findParents # Compatibility with pre-3.x

    #These methods do the real heavy lifting.

    def _findOne(self, method, name, attrs, text, **kwargs):
        r = None
        l = method(name, attrs, text, 1, **kwargs)
        if l:
            r = l[0]
        return r

    def _findAll(self, name, attrs, text, limit, generator, **kwargs):
        "Iterates over a generator looking for things that match."

        if isinstance(name, SoupStrainer):
            strainer = name
        else:
            # Build a SoupStrainer
            strainer = SoupStrainer(name, attrs, text, **kwargs)
        results = ResultSet(strainer)
        g = generator()
        while True:
            try:
                i = g.next()
            except StopIteration:
                break
            if i:
                found = strainer.search(i)
                if found:
                    results.append(found)
                    if limit and len(results) >= limit:
                        break
        return results

    #These Generators can be used to navigate starting from both
    #NavigableStrings and Tags.
    def nextGenerator(self):
        i = self
        while i:
            i = i.next
            yield i

    def nextSiblingGenerator(self):
        i = self
        while i:
            i = i.nextSibling
            yield i

    def previousGenerator(self):
        i = self
        while i:
            i = i.previous
            yield i

    def previousSiblingGenerator(self):
        i = self
        while i:
            i = i.previousSibling
            yield i

    def parentGenerator(self):
        i = self
        while i:
            i = i.parent
            yield i

    # Utility methods
    def substituteEncoding(self, str, encoding=None):
        encoding = encoding or "utf-8"
        return str.replace("%SOUP-ENCODING%", encoding)

    def toEncoding(self, s, encoding=None):
        """Encodes an object to a string in some encoding, or to Unicode.
        ."""
        if isinstance(s, unicode):
            if encoding:
                s = s.encode(encoding)
        elif isinstance(s, str):
            if encoding:
                s = s.encode(encoding)
            else:
                s = unicode(s)
        else:
            if encoding:
                s  = self.toEncoding(str(s), encoding)
            else:
                s = unicode(s)
        return s

class NavigableString(unicode, PageElement):

    def __new__(cls, value):
        """Create a new NavigableString.

        When unpickling a NavigableString, this method is called with
        the string in DEFAULT_OUTPUT_ENCODING. That encoding needs to be
        passed in to the superclass's __new__ or the superclass won't know
        how to handle non-ASCII characters.
        """
        if isinstance(value, unicode):
            return unicode.__new__(cls, value)
        return unicode.__new__(cls, value, DEFAULT_OUTPUT_ENCODING)

    def __getnewargs__(self):
        return (NavigableString.__str__(self),)

    def __getattr__(self, attr):
        """text.string gives you text. This is for backwards
        compatibility for Navigable*String, but for CData* it lets you
        get the string without the CData wrapper."""
        if attr == 'string':
            return self
        else:
            raise AttributeError, "'%s' object has no attribute '%s'" % (self.__class__.__name__, attr)

    def __unicode__(self):
        return str(self).decode(DEFAULT_OUTPUT_ENCODING)

    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        if encoding:
            return self.encode(encoding)
        else:
            return self

class CData(NavigableString):

    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return "<![CDATA[%s]]>" % NavigableString.__str__(self, encoding)

class ProcessingInstruction(NavigableString):
    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        output = self
        if "%SOUP-ENCODING%" in output:
            output = self.substituteEncoding(output, encoding)
        return "<?%s?>" % self.toEncoding(output, encoding)

class Comment(NavigableString):
    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return "<!--%s-->" % NavigableString.__str__(self, encoding)

class Declaration(NavigableString):
    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return "<!%s>" % NavigableString.__str__(self, encoding)

class Tag(PageElement):

    """Represents a found HTML tag with its attributes and contents."""

    def _invert(h):
        "Cheap function to invert a hash."
        i = {}
        for k,v in h.items():
            i[v] = k
        return i

    XML_ENTITIES_TO_SPECIAL_CHARS = { "apos" : "'",
                                      "quot" : '"',
                                      "amp" : "&",
                                      "lt" : "<",
                                      "gt" : ">" }

    XML_SPECIAL_CHARS_TO_ENTITIES = _invert(XML_ENTITIES_TO_SPECIAL_CHARS)

    def _convertEntities(self, match):
        """Used in a call to re.sub to replace HTML, XML, and numeric
        entities with the appropriate Unicode characters. If HTML
        entities are being converted, any unrecognized entities are
        escaped."""
        x = match.group(1)
        if self.convertHTMLEntities and x in name2codepoint:
            return unichr(name2codepoint[x])
        elif x in self.XML_ENTITIES_TO_SPECIAL_CHARS:
            if self.convertXMLEntities:
                return self.XML_ENTITIES_TO_SPECIAL_CHARS[x]
            else:
                return u'&%s;' % x
        elif len(x) > 0 and x[0] == '#':
            # Handle numeric entities
            if len(x) > 1 and x[1] == 'x':
                return unichr(int(x[2:], 16))
            else:
                return unichr(int(x[1:]))

        elif self.escapeUnrecognizedEntities:
            return u'&amp;%s;' % x
        else:
            return u'&%s;' % x

    def __init__(self, parser, name, attrs=None, parent=None,
                 previous=None):
        "Basic constructor."

        # We don't actually store the parser object: that lets extracted
        # chunks be garbage-collected
        self.parserClass = parser.__class__
        self.isSelfClosing = parser.isSelfClosingTag(name)
        self.name = name
        if attrs == None:
            attrs = []
        self.attrs = attrs
        self.contents = []
        self.setup(parent, previous)
        self.hidden = False
        self.containsSubstitutions = False
        self.convertHTMLEntities = parser.convertHTMLEntities
        self.convertXMLEntities = parser.convertXMLEntities
        self.escapeUnrecognizedEntities = parser.escapeUnrecognizedEntities

        # Convert any HTML, XML, or numeric entities in the attribute values.
        convert = lambda(k, val): (k,
                                   re.sub("&(#\d+|#x[0-9a-fA-F]+|\w+);",
                                          self._convertEntities,
                                          val))
        self.attrs = map(convert, self.attrs)

    def get(self, key, default=None):
        """Returns the value of the 'key' attribute for the tag, or
        the value given for 'default' if it doesn't have that
        attribute."""
        return self._getAttrMap().get(key, default)

    def has_key(self, key):
        return self._getAttrMap().has_key(key)

    def __getitem__(self, key):
        """tag[key] returns the value of the 'key' attribute for the tag,
        and throws an exception if it's not there."""
        return self._getAttrMap()[key]

    def __iter__(self):
        "Iterating over a tag iterates over its contents."
        return iter(self.contents)

    def __len__(self):
        "The length of a tag is the length of its list of contents."
        return len(self.contents)

    def __contains__(self, x):
        return x in self.contents

    def __nonzero__(self):
        "A tag is non-None even if it has no contents."
        return True

    def __setitem__(self, key, value):
        """Setting tag[key] sets the value of the 'key' attribute for the
        tag."""
        self._getAttrMap()
        self.attrMap[key] = value
        found = False
        for i in range(0, len(self.attrs)):
            if self.attrs[i][0] == key:
                self.attrs[i] = (key, value)
                found = True
        if not found:
            self.attrs.append((key, value))
        self._getAttrMap()[key] = value

    def __delitem__(self, key):
        "Deleting tag[key] deletes all 'key' attributes for the tag."
        for item in self.attrs:
            if item[0] == key:
                self.attrs.remove(item)
                #We don't break because bad HTML can define the same
                #attribute multiple times.
            self._getAttrMap()
            if self.attrMap.has_key(key):
                del self.attrMap[key]

    def __call__(self, *args, **kwargs):
        """Calling a tag like a function is the same as calling its
        findAll() method. Eg. tag('a') returns a list of all the A tags
        found within this tag."""
        return apply(self.findAll, args, kwargs)

    def __getattr__(self, tag):
        #print "Getattr %s.%s" % (self.__class__, tag)
        if len(tag) > 3 and tag.rfind('Tag') == len(tag)-3:
            return self.find(tag[:-3])
        elif tag.find('__') != 0:
            return self.find(tag)
        raise AttributeError, "'%s' object has no attribute '%s'" % (self.__class__, tag)

    def __eq__(self, other):
        """Returns true iff this tag has the same name, the same attributes,
        and the same contents (recursively) as the given tag.

        NOTE: right now this will return false if two tags have the
        same attributes in a different order. Should this be fixed?"""
        if not hasattr(other, 'name') or not hasattr(other, 'attrs') or not hasattr(other, 'contents') or self.name != other.name or self.attrs != other.attrs or len(self) != len(other):
            return False
        for i in range(0, len(self.contents)):
            if self.contents[i] != other.contents[i]:
                return False
        return True

    def __ne__(self, other):
        """Returns true iff this tag is not identical to the other tag,
        as defined in __eq__."""
        return not self == other

    def __repr__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        """Renders this tag as a string."""
        return self.__str__(encoding)

    def __unicode__(self):
        return self.__str__(None)

    BARE_AMPERSAND_OR_BRACKET = re.compile("([<>]|"
                                           + "&(?!#\d+;|#x[0-9a-fA-F]+;|\w+;)"
                                           + ")")

    def _sub_entity(self, x):
        """Used with a regular expression to substitute the
        appropriate XML entity for an XML special character."""
        return "&" + self.XML_SPECIAL_CHARS_TO_ENTITIES[x.group(0)[0]] + ";"

    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING,
                prettyPrint=False, indentLevel=0):
        """Returns a string or Unicode representation of this tag and
        its contents. To get Unicode, pass None for encoding.

        NOTE: since Python's HTML parser consumes whitespace, this
        method is not certain to reproduce the whitespace present in
        the original string."""

        encodedName = self.toEncoding(self.name, encoding)

        attrs = []
        if self.attrs:
            for key, val in self.attrs:
                fmt = '%s="%s"'
                if isString(val):
                    if self.containsSubstitutions and '%SOUP-ENCODING%' in val:
                        val = self.substituteEncoding(val, encoding)

                    # The attribute value either:
                    #
                    # * Contains no embedded double quotes or single quotes.
                    #   No problem: we enclose it in double quotes.
                    # * Contains embedded single quotes. No problem:
                    #   double quotes work here too.
                    # * Contains embedded double quotes. No problem:
                    #   we enclose it in single quotes.
                    # * Embeds both single _and_ double quotes. This
                    #   can't happen naturally, but it can happen if
                    #   you modify an attribute value after parsing
                    #   the document. Now we have a bit of a
                    #   problem. We solve it by enclosing the
                    #   attribute in single quotes, and escaping any
                    #   embedded single quotes to XML entities.
                    if '"' in val:
                        fmt = "%s='%s'"
                        if "'" in val:
                            # TODO: replace with apos when
                            # appropriate.
                            val = val.replace("'", "&squot;")

                    # Now we're okay w/r/t quotes. But the attribute
                    # value might also contain angle brackets, or
                    # ampersands that aren't part of entities. We need
                    # to escape those to XML entities too.
                    val = self.BARE_AMPERSAND_OR_BRACKET.sub(self._sub_entity, val)

                attrs.append(fmt % (self.toEncoding(key, encoding),
                                    self.toEncoding(val, encoding)))
        close = ''
        closeTag = ''
        if self.isSelfClosing:
            close = ' /'
        else:
            closeTag = '</%s>' % encodedName

        indentTag, indentContents = 0, 0
        if prettyPrint:
            indentTag = indentLevel
            space = (' ' * (indentTag-1))
            indentContents = indentTag + 1
        contents = self.renderContents(encoding, prettyPrint, indentContents)
        if self.hidden:
            s = contents
        else:
            s = []
            attributeString = ''
            if attrs:
                attributeString = ' ' + ' '.join(attrs)
            if prettyPrint:
                s.append(space)
            s.append('<%s%s%s>' % (encodedName, attributeString, close))
            if prettyPrint:
                s.append("\n")
            s.append(contents)
            if prettyPrint and contents and contents[-1] != "\n":
                s.append("\n")
            if prettyPrint and closeTag:
                s.append(space)
            s.append(closeTag)
            if prettyPrint and closeTag and self.nextSibling:
                s.append("\n")
            s = ''.join(s)
        return s

    def decompose(self):
        """Recursively destroys the contents of this tree."""
        contents = [i for i in self.contents]
        for i in contents:
            if isinstance(i, Tag):
                i.decompose()
            else:
                i.extract()
        self.extract()

    def prettify(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return self.__str__(encoding, True)

    def renderContents(self, encoding=DEFAULT_OUTPUT_ENCODING,
                       prettyPrint=False, indentLevel=0):
        """Renders the contents of this tag as a string in the given
        encoding. If encoding is None, returns a Unicode string.."""
        s=[]
        for c in self:
            text = None
            if isinstance(c, NavigableString):
                text = c.__str__(encoding)
            elif isinstance(c, Tag):
                s.append(c.__str__(encoding, prettyPrint, indentLevel))
            if text and prettyPrint:
                text = text.strip()
            if text:
                if prettyPrint:
                    s.append(" " * (indentLevel-1))
                s.append(text)
                if prettyPrint:
                    s.append("\n")
        return ''.join(s)

    #Soup methods

    def find(self, name=None, attrs={}, recursive=True, text=None,
             **kwargs):
        """Return only the first child of this Tag matching the given
        criteria."""
        r = None
        l = self.findAll(name, attrs, recursive, text, 1, **kwargs)
        if l:
            r = l[0]
        return r
    findChild = find

    def findAll(self, name=None, attrs={}, recursive=True, text=None,
                limit=None, **kwargs):
        """Extracts a list of Tag objects that match the given
        criteria.  You can specify the name of the Tag and any
        attributes you want the Tag to have.

        The value of a key-value pair in the 'attrs' map can be a
        string, a list of strings, a regular expression object, or a
        callable that takes a string and returns whether or not the
        string matches for some custom definition of 'matches'. The
        same is true of the tag name."""
        generator = self.recursiveChildGenerator
        if not recursive:
            generator = self.childGenerator
        return self._findAll(name, attrs, text, limit, generator, **kwargs)
    findChildren = findAll

    # Pre-3.x compatibility methods
    first = find
    fetch = findAll

    def fetchText(self, text=None, recursive=True, limit=None):
        return self.findAll(text=text, recursive=recursive, limit=limit)

    def firstText(self, text=None, recursive=True):
        return self.find(text=text, recursive=recursive)

    #Private methods

    def _getAttrMap(self):
        """Initializes a map representation of this tag's attributes,
        if not already initialized."""
        if not getattr(self, 'attrMap'):
            self.attrMap = {}
            for (key, value) in self.attrs:
                self.attrMap[key] = value
        return self.attrMap

    #Generator methods
    def childGenerator(self):
        for i in range(0, len(self.contents)):
            yield self.contents[i]
        raise StopIteration

    def recursiveChildGenerator(self):
        stack = [(self, 0)]
        while stack:
            tag, start = stack.pop()
            if isinstance(tag, Tag):
                for i in range(start, len(tag.contents)):
                    a = tag.contents[i]
                    yield a
                    if isinstance(a, Tag) and tag.contents:
                        if i < len(tag.contents) - 1:
                            stack.append((tag, i+1))
                        stack.append((a, 0))
                        break
        raise StopIteration

# Next, a couple classes to represent queries and their results.
class SoupStrainer:
    """Encapsulates a number of ways of matching a markup element (tag or
    text)."""

    def __init__(self, name=None, attrs={}, text=None, **kwargs):
        self.name = name
        if isString(attrs):
            kwargs['class'] = attrs
            attrs = None
        if kwargs:
            if attrs:
                attrs = attrs.copy()
                attrs.update(kwargs)
            else:
                attrs = kwargs
        self.attrs = attrs
        self.text = text

    def __str__(self):
        if self.text:
            return self.text
        else:
            return "%s|%s" % (self.name, self.attrs)

    def searchTag(self, markupName=None, markupAttrs={}):
        found = None
        markup = None
        if isinstance(markupName, Tag):
            markup = markupName
            markupAttrs = markup
        callFunctionWithTagData = callable(self.name) \
                                and not isinstance(markupName, Tag)

        if (not self.name) \
               or callFunctionWithTagData \
               or (markup and self._matches(markup, self.name)) \
               or (not markup and self._matches(markupName, self.name)):
            if callFunctionWithTagData:
                match = self.name(markupName, markupAttrs)
            else:
                match = True
                markupAttrMap = None
                for attr, matchAgainst in self.attrs.items():
                    if not markupAttrMap:
                         if hasattr(markupAttrs, 'get'):
                            markupAttrMap = markupAttrs
                         else:
                            markupAttrMap = {}
                            for k,v in markupAttrs:
                                markupAttrMap[k] = v
                    attrValue = markupAttrMap.get(attr)
                    if not self._matches(attrValue, matchAgainst):
                        match = False
                        break
            if match:
                if markup:
                    found = markup
                else:
                    found = markupName
        return found

    def search(self, markup):
        #print 'looking for %s in %s' % (self, markup)
        found = None
        # If given a list of items, scan it for a text element that
        # matches.
        if isList(markup) and not isinstance(markup, Tag):
            for element in markup:
                if isinstance(element, NavigableString) \
                       and self.search(element):
                    found = element
                    break
        # If it's a Tag, make sure its name or attributes match.
        # Don't bother with Tags if we're searching for text.
        elif isinstance(markup, Tag):
            if not self.text:
                found = self.searchTag(markup)
        # If it's text, make sure the text matches.
        elif isinstance(markup, NavigableString) or \
                 isString(markup):
            if self._matches(markup, self.text):
                found = markup
        else:
            raise Exception, "I don't know how to match against a %s" \
                  % markup.__class__
        return found

    def _matches(self, markup, matchAgainst):
        #print "Matching %s against %s" % (markup, matchAgainst)
        result = False
        if matchAgainst == True and type(matchAgainst) == types.BooleanType:
            result = markup != None
        elif callable(matchAgainst):
            result = matchAgainst(markup)
        else:
            #Custom match methods take the tag as an argument, but all
            #other ways of matching match the tag name as a string.
            if isinstance(markup, Tag):
                markup = markup.name
            if markup and not isString(markup):
                markup = unicode(markup)
            #Now we know that chunk is either a string, or None.
            if hasattr(matchAgainst, 'match'):
                # It's a regexp object.
                result = markup and matchAgainst.search(markup)
            elif isList(matchAgainst):
                result = markup in matchAgainst
            elif hasattr(matchAgainst, 'items'):
                result = markup.has_key(matchAgainst)
            elif matchAgainst and isString(markup):
                if isinstance(markup, unicode):
                    matchAgainst = unicode(matchAgainst)
                else:
                    matchAgainst = str(matchAgainst)

            if not result:
                result = matchAgainst == markup
        return result

class ResultSet(list):
    """A ResultSet is just a list that keeps track of the SoupStrainer
    that created it."""
    def __init__(self, source):
        list.__init__([])
        self.source = source

# Now, some helper functions.

def isList(l):
    """Convenience method that works with all 2.x versions of Python
    to determine whether or not something is listlike."""
    return hasattr(l, '__iter__') \
           or (type(l) in (types.ListType, types.TupleType))

def isString(s):
    """Convenience method that works with all 2.x versions of Python
    to determine whether or not something is stringlike."""
    try:
        return isinstance(s, unicode) or isinstance(s, basestring)
    except NameError:
        return isinstance(s, str)

def buildTagMap(default, *args):
    """Turns a list of maps, lists, or scalars into a single map.
    Used to build the SELF_CLOSING_TAGS, NESTABLE_TAGS, and
    NESTING_RESET_TAGS maps out of lists and partial maps."""
    built = {}
    for portion in args:
        if hasattr(portion, 'items'):
            #It's a map. Merge it.
            for k,v in portion.items():
                built[k] = v
        elif isList(portion):
            #It's a list. Map each item to the default.
            for k in portion:
                built[k] = default
        else:
            #It's a scalar. Map it to the default.
            built[portion] = default
    return built

# Now, the parser classes.

class BeautifulStoneSoup(Tag, SGMLParser):

    """This class contains the basic parser and search code. It defines
    a parser that knows nothing about tag behavior except for the
    following:

      You can't close a tag without closing all the tags it encloses.
      That is, "<foo><bar></foo>" actually means
      "<foo><bar></bar></foo>".

    [Another possible explanation is "<foo><bar /></foo>", but since
    this class defines no SELF_CLOSING_TAGS, it will never use that
    explanation.]

    This class is useful for parsing XML or made-up markup languages,
    or when BeautifulSoup makes an assumption counter to what you were
    expecting."""

    SELF_CLOSING_TAGS = {}
    NESTABLE_TAGS = {}
    RESET_NESTING_TAGS = {}
    QUOTE_TAGS = {}
    PRESERVE_WHITESPACE_TAGS = []

    MARKUP_MASSAGE = [(re.compile('(<[^<>]*)/>'),
                       lambda x: x.group(1) + ' />'),
                      (re.compile('<!\s+([^<>]*)>'),
                       lambda x: '<!' + x.group(1) + '>')
                      ]

    ROOT_TAG_NAME = u'[document]'

    HTML_ENTITIES = "html"
    XML_ENTITIES = "xml"
    XHTML_ENTITIES = "xhtml"
    # TODO: This only exists for backwards-compatibility
    ALL_ENTITIES = XHTML_ENTITIES

    # Used when determining whether a text node is all whitespace and
    # can be replaced with a single space. A text node that contains
    # fancy Unicode spaces (usually non-breaking) should be left
    # alone.
    STRIP_ASCII_SPACES = { 9: None, 10: None, 12: None, 13: None, 32: None, }

    def __init__(self, markup="", parseOnlyThese=None, fromEncoding=None,
                 markupMassage=True, smartQuotesTo=XML_ENTITIES,
                 convertEntities=None, selfClosingTags=None, isHTML=False):
        """The Soup object is initialized as the 'root tag', and the
        provided markup (which can be a string or a file-like object)
        is fed into the underlying parser.

        sgmllib will process most bad HTML, and the BeautifulSoup
        class has some tricks for dealing with some HTML that kills
        sgmllib, but Beautiful Soup can nonetheless choke or lose data
        if your data uses self-closing tags or declarations
        incorrectly.

        By default, Beautiful Soup uses regexes to sanitize input,
        avoiding the vast majority of these problems. If the problems
        don't apply to you, pass in False for markupMassage, and
        you'll get better performance.

        The default parser massage techniques fix the two most common
        instances of invalid HTML that choke sgmllib:

         <br/> (No space between name of closing tag and tag close)
         <! --Comment--> (Extraneous whitespace in declaration)

        You can pass in a custom list of (RE object, replace method)
        tuples to get Beautiful Soup to scrub your input the way you
        want."""

        self.parseOnlyThese = parseOnlyThese
        self.fromEncoding = fromEncoding
        self.smartQuotesTo = smartQuotesTo
        self.convertEntities = convertEntities
        # Set the rules for how we'll deal with the entities we
        # encounter
        if self.convertEntities:
            # It doesn't make sense to convert encoded characters to
            # entities even while you're converting entities to Unicode.
            # Just convert it all to Unicode.
            self.smartQuotesTo = None
            if convertEntities == self.HTML_ENTITIES:
                self.convertXMLEntities = False
                self.convertHTMLEntities = True
                self.escapeUnrecognizedEntities = True
            elif convertEntities == self.XHTML_ENTITIES:
                self.convertXMLEntities = True
                self.convertHTMLEntities = True
                self.escapeUnrecognizedEntities = False
            elif convertEntities == self.XML_ENTITIES:
                self.convertXMLEntities = True
                self.convertHTMLEntities = False
                self.escapeUnrecognizedEntities = False
        else:
            self.convertXMLEntities = False
            self.convertHTMLEntities = False
            self.escapeUnrecognizedEntities = False

        self.instanceSelfClosingTags = buildTagMap(None, selfClosingTags)
        SGMLParser.__init__(self)

        if hasattr(markup, 'read'):        # It's a file-type object.
            markup = markup.read()
        self.markup = markup
        self.markupMassage = markupMassage
        try:
            self._feed(isHTML=isHTML)
        except StopParsing:
            pass
        self.markup = None                 # The markup can now be GCed

    def convert_charref(self, name):
        """This method fixes a bug in Python's SGMLParser."""
        try:
            n = int(name)
        except ValueError:
            return
        if not 0 <= n <= 127 : # ASCII ends at 127, not 255
            return
        return self.convert_codepoint(n)

    def _feed(self, inDocumentEncoding=None, isHTML=False):
        # Convert the document to Unicode.
        markup = self.markup
        if isinstance(markup, unicode):
            if not hasattr(self, 'originalEncoding'):
                self.originalEncoding = None
        else:
            dammit = UnicodeDammit\
                     (markup, [self.fromEncoding, inDocumentEncoding],
                      smartQuotesTo=self.smartQuotesTo, isHTML=isHTML)
            markup = dammit.unicode
            self.originalEncoding = dammit.originalEncoding
            self.declaredHTMLEncoding = dammit.declaredHTMLEncoding
        if markup:
            if self.markupMassage:
                if not isList(self.markupMassage):
                    self.markupMassage = self.MARKUP_MASSAGE
                for fix, m in self.markupMassage:
                    markup = fix.sub(m, markup)
                # TODO: We get rid of markupMassage so that the
                # soup object can be deepcopied later on. Some
                # Python installations can't copy regexes. If anyone
                # was relying on the existence of markupMassage, this
                # might cause problems.
                del(self.markupMassage)
        self.reset()

        SGMLParser.feed(self, markup)
        # Close out any unfinished strings and close all the open tags.
        self.endData()
        while self.currentTag.name != self.ROOT_TAG_NAME:
            self.popTag()

    def __getattr__(self, methodName):
        """This method routes method call requests to either the SGMLParser
        superclass or the Tag superclass, depending on the method name."""
        #print "__getattr__ called on %s.%s" % (self.__class__, methodName)

        if methodName.find('start_') == 0 or methodName.find('end_') == 0 \
               or methodName.find('do_') == 0:
            return SGMLParser.__getattr__(self, methodName)
        elif methodName.find('__') != 0:
            return Tag.__getattr__(self, methodName)
        else:
            raise AttributeError

    def isSelfClosingTag(self, name):
        """Returns true iff the given string is the name of a
        self-closing tag according to this parser."""
        return self.SELF_CLOSING_TAGS.has_key(name) \
               or self.instanceSelfClosingTags.has_key(name)

    def reset(self):
        Tag.__init__(self, self, self.ROOT_TAG_NAME)
        self.hidden = 1
        SGMLParser.reset(self)
        self.currentData = []
        self.currentTag = None
        self.tagStack = []
        self.quoteStack = []
        self.pushTag(self)

    def popTag(self):
        tag = self.tagStack.pop()
        # Tags with just one string-owning child get the child as a
        # 'string' property, so that soup.tag.string is shorthand for
        # soup.tag.contents[0]
        if len(self.currentTag.contents) == 1 and \
           isinstance(self.currentTag.contents[0], NavigableString):
            self.currentTag.string = self.currentTag.contents[0]

        #print "Pop", tag.name
        if self.tagStack:
            self.currentTag = self.tagStack[-1]
        return self.currentTag

    def pushTag(self, tag):
        #print "Push", tag.name
        if self.currentTag:
            self.currentTag.contents.append(tag)
        self.tagStack.append(tag)
        self.currentTag = self.tagStack[-1]

    def endData(self, containerClass=NavigableString):
        if self.currentData:
            currentData = u''.join(self.currentData)
            if (currentData.translate(self.STRIP_ASCII_SPACES) == '' and
                not set([tag.name for tag in self.tagStack]).intersection(
                    self.PRESERVE_WHITESPACE_TAGS)):
                if '\n' in currentData:
                    currentData = '\n'
                else:
                    currentData = ' '
            self.currentData = []
            if self.parseOnlyThese and len(self.tagStack) <= 1 and \
                   (not self.parseOnlyThese.text or \
                    not self.parseOnlyThese.search(currentData)):
                return
            o = containerClass(currentData)
            o.setup(self.currentTag, self.previous)
            if self.previous:
                self.previous.next = o
            self.previous = o
            self.currentTag.contents.append(o)


    def _popToTag(self, name, inclusivePop=True):
        """Pops the tag stack up to and including the most recent
        instance of the given tag. If inclusivePop is false, pops the tag
        stack up to but *not* including the most recent instqance of
        the given tag."""
        #print "Popping to %s" % name
        if name == self.ROOT_TAG_NAME:
            return

        numPops = 0
        mostRecentTag = None
        for i in range(len(self.tagStack)-1, 0, -1):
            if name == self.tagStack[i].name:
                numPops = len(self.tagStack)-i
                break
        if not inclusivePop:
            numPops = numPops - 1

        for i in range(0, numPops):
            mostRecentTag = self.popTag()
        return mostRecentTag

    def _smartPop(self, name):

        """We need to pop up to the previous tag of this type, unless
        one of this tag's nesting reset triggers comes between this
        tag and the previous tag of this type, OR unless this tag is a
        generic nesting trigger and another generic nesting trigger
        comes between this tag and the previous tag of this type.

        Examples:
         <p>Foo<b>Bar *<p>* should pop to 'p', not 'b'.
         <p>Foo<table>Bar *<p>* should pop to 'table', not 'p'.
         <p>Foo<table><tr>Bar *<p>* should pop to 'tr', not 'p'.

         <li><ul><li> *<li>* should pop to 'ul', not the first 'li'.
         <tr><table><tr> *<tr>* should pop to 'table', not the first 'tr'
         <td><tr><td> *<td>* should pop to 'tr', not the first 'td'
        """

        nestingResetTriggers = self.NESTABLE_TAGS.get(name)
        isNestable = nestingResetTriggers != None
        isResetNesting = self.RESET_NESTING_TAGS.has_key(name)
        popTo = None
        inclusive = True
        for i in range(len(self.tagStack)-1, 0, -1):
            p = self.tagStack[i]
            if (not p or p.name == name) and not isNestable:
                #Non-nestable tags get popped to the top or to their
                #last occurance.
                popTo = name
                break
            if (nestingResetTriggers != None
                and p.name in nestingResetTriggers) \
                or (nestingResetTriggers == None and isResetNesting
                    and self.RESET_NESTING_TAGS.has_key(p.name)):

                #If we encounter one of the nesting reset triggers
                #peculiar to this tag, or we encounter another tag
                #that causes nesting to reset, pop up to but not
                #including that tag.
                popTo = p.name
                inclusive = False
                break
            p = p.parent
        if popTo:
            self._popToTag(popTo, inclusive)

    def unknown_starttag(self, name, attrs, selfClosing=0):
        #print "Start tag %s: %s" % (name, attrs)
        if self.quoteStack:
            #This is not a real tag.
            #print "<%s> is not real!" % name
            attrs = ''.join(map(lambda(x, y): ' %s="%s"' % (x, y), attrs))
            self.handle_data('<%s%s>' % (name, attrs))
            return
        self.endData()

        if not self.isSelfClosingTag(name) and not selfClosing:
            self._smartPop(name)

        if self.parseOnlyThese and len(self.tagStack) <= 1 \
               and (self.parseOnlyThese.text or not self.parseOnlyThese.searchTag(name, attrs)):
            return

        tag = Tag(self, name, attrs, self.currentTag, self.previous)
        if self.previous:
            self.previous.next = tag
        self.previous = tag
        self.pushTag(tag)
        if selfClosing or self.isSelfClosingTag(name):
            self.popTag()
        if name in self.QUOTE_TAGS:
            #print "Beginning quote (%s)" % name
            self.quoteStack.append(name)
            self.literal = 1
        return tag

    def unknown_endtag(self, name):
        #print "End tag %s" % name
        if self.quoteStack and self.quoteStack[-1] != name:
            #This is not a real end tag.
            #print "</%s> is not real!" % name
            self.handle_data('</%s>' % name)
            return
        self.endData()
        self._popToTag(name)
        if self.quoteStack and self.quoteStack[-1] == name:
            self.quoteStack.pop()
            self.literal = (len(self.quoteStack) > 0)

    def handle_data(self, data):
        self.currentData.append(data)

    def _toStringSubclass(self, text, subclass):
        """Adds a certain piece of text to the tree as a NavigableString
        subclass."""
        self.endData()
        self.handle_data(text)
        self.endData(subclass)

    def handle_pi(self, text):
        """Handle a processing instruction as a ProcessingInstruction
        object, possibly one with a %SOUP-ENCODING% slot into which an
        encoding will be plugged later."""
        if text[:3] == "xml":
            text = u"xml version='1.0' encoding='%SOUP-ENCODING%'"
        self._toStringSubclass(text, ProcessingInstruction)

    def handle_comment(self, text):
        "Handle comments as Comment objects."
        self._toStringSubclass(text, Comment)

    def handle_charref(self, ref):
        "Handle character references as data."
        if self.convertEntities:
            data = unichr(int(ref))
        else:
            data = '&#%s;' % ref
        self.handle_data(data)

    def handle_entityref(self, ref):
        """Handle entity references as data, possibly converting known
        HTML and/or XML entity references to the corresponding Unicode
        characters."""
        data = None
        if self.convertHTMLEntities:
            try:
                data = unichr(name2codepoint[ref])
            except KeyError:
                pass

        if not data and self.convertXMLEntities:
                data = self.XML_ENTITIES_TO_SPECIAL_CHARS.get(ref)

        if not data and self.convertHTMLEntities and \
            not self.XML_ENTITIES_TO_SPECIAL_CHARS.get(ref):
                # TODO: We've got a problem here. We're told this is
                # an entity reference, but it's not an XML entity
                # reference or an HTML entity reference. Nonetheless,
                # the logical thing to do is to pass it through as an
                # unrecognized entity reference.
                #
                # Except: when the input is "&carol;" this function
                # will be called with input "carol". When the input is
                # "AT&T", this function will be called with input
                # "T". We have no way of knowing whether a semicolon
                # was present originally, so we don't know whether
                # this is an unknown entity or just a misplaced
                # ampersand.
                #
                # The more common case is a misplaced ampersand, so I
                # escape the ampersand and omit the trailing semicolon.
                data = "&amp;%s" % ref
        if not data:
            # This case is different from the one above, because we
            # haven't already gone through a supposedly comprehensive
            # mapping of entities to Unicode characters. We might not
            # have gone through any mapping at all. So the chances are
            # very high that this is a real entity, and not a
            # misplaced ampersand.
            data = "&%s;" % ref
        self.handle_data(data)

    def handle_decl(self, data):
        "Handle DOCTYPEs and the like as Declaration objects."
        self._toStringSubclass(data, Declaration)

    def parse_declaration(self, i):
        """Treat a bogus SGML declaration as raw data. Treat a CDATA
        declaration as a CData object."""
        j = None
        if self.rawdata[i:i+9] == '<![CDATA[':
             k = self.rawdata.find(']]>', i)
             if k == -1:
                 k = len(self.rawdata)
             data = self.rawdata[i+9:k]
             j = k+3
             self._toStringSubclass(data, CData)
        else:
            try:
                j = SGMLParser.parse_declaration(self, i)
            except SGMLParseError:
                toHandle = self.rawdata[i:]
                self.handle_data(toHandle)
                j = i + len(toHandle)
        return j

class BeautifulSoup(BeautifulStoneSoup):

    """This parser knows the following facts about HTML:

    * Some tags have no closing tag and should be interpreted as being
      closed as soon as they are encountered.

    * The text inside some tags (ie. 'script') may contain tags which
      are not really part of the document and which should be parsed
      as text, not tags. If you want to parse the text as tags, you can
      always fetch it and parse it explicitly.

    * Tag nesting rules:

      Most tags can't be nested at all. For instance, the occurance of
      a <p> tag should implicitly close the previous <p> tag.

       <p>Para1<p>Para2
        should be transformed into:
       <p>Para1</p><p>Para2

      Some tags can be nested arbitrarily. For instance, the occurance
      of a <blockquote> tag should _not_ implicitly close the previous
      <blockquote> tag.

       Alice said: <blockquote>Bob said: <blockquote>Blah
        should NOT be transformed into:
       Alice said: <blockquote>Bob said: </blockquote><blockquote>Blah

      Some tags can be nested, but the nesting is reset by the
      interposition of other tags. For instance, a <tr> tag should
      implicitly close the previous <tr> tag within the same <table>,
      but not close a <tr> tag in another table.

       <table><tr>Blah<tr>Blah
        should be transformed into:
       <table><tr>Blah</tr><tr>Blah
        but,
       <tr>Blah<table><tr>Blah
        should NOT be transformed into
       <tr>Blah<table></tr><tr>Blah

    Differing assumptions about tag nesting rules are a major source
    of problems with the BeautifulSoup class. If BeautifulSoup is not
    treating as nestable a tag your page author treats as nestable,
    try ICantBelieveItsBeautifulSoup, MinimalSoup, or
    BeautifulStoneSoup before writing your own subclass."""

    def __init__(self, *args, **kwargs):
        if not kwargs.has_key('smartQuotesTo'):
            kwargs['smartQuotesTo'] = self.HTML_ENTITIES
        kwargs['isHTML'] = True
        BeautifulStoneSoup.__init__(self, *args, **kwargs)

    SELF_CLOSING_TAGS = buildTagMap(None,
                                    ['br' , 'hr', 'input', 'img', 'meta',
                                    'spacer', 'link', 'frame', 'base'])

    PRESERVE_WHITESPACE_TAGS = set(['pre', 'textarea'])

    QUOTE_TAGS = {'script' : None, 'textarea' : None}

    #According to the HTML standard, each of these inline tags can
    #contain another tag of the same type. Furthermore, it's common
    #to actually use these tags this way.
    NESTABLE_INLINE_TAGS = ['span', 'font', 'q', 'object', 'bdo', 'sub', 'sup',
                            'center']

    #According to the HTML standard, these block tags can contain
    #another tag of the same type. Furthermore, it's common
    #to actually use these tags this way.
    NESTABLE_BLOCK_TAGS = ['blockquote', 'div', 'fieldset', 'ins', 'del']

    #Lists can contain other lists, but there are restrictions.
    NESTABLE_LIST_TAGS = { 'ol' : [],
                           'ul' : [],
                           'li' : ['ul', 'ol'],
                           'dl' : [],
                           'dd' : ['dl'],
                           'dt' : ['dl'] }

    #Tables can contain other tables, but there are restrictions.
    NESTABLE_TABLE_TAGS = {'table' : [],
                           'tr' : ['table', 'tbody', 'tfoot', 'thead'],
                           'td' : ['tr'],
                           'th' : ['tr'],
                           'thead' : ['table'],
                           'tbody' : ['table'],
                           'tfoot' : ['table'],
                           }

    NON_NESTABLE_BLOCK_TAGS = ['address', 'form', 'p', 'pre']

    #If one of these tags is encountered, all tags up to the next tag of
    #this type are popped.
    RESET_NESTING_TAGS = buildTagMap(None, NESTABLE_BLOCK_TAGS, 'noscript',
                                     NON_NESTABLE_BLOCK_TAGS,
                                     NESTABLE_LIST_TAGS,
                                     NESTABLE_TABLE_TAGS)

    NESTABLE_TAGS = buildTagMap([], NESTABLE_INLINE_TAGS, NESTABLE_BLOCK_TAGS,
                                NESTABLE_LIST_TAGS, NESTABLE_TABLE_TAGS)

    # Used to detect the charset in a META tag; see start_meta
    CHARSET_RE = re.compile("((^|;)\s*charset=)([^;]*)", re.M)

    def start_meta(self, attrs):
        """Beautiful Soup can detect a charset included in a META tag,
        try to convert the document to that charset, and re-parse the
        document from the beginning."""
        httpEquiv = None
        contentType = None
        contentTypeIndex = None
        tagNeedsEncodingSubstitution = False

        for i in range(0, len(attrs)):
            key, value = attrs[i]
            key = key.lower()
            if key == 'http-equiv':
                httpEquiv = value
            elif key == 'content':
                contentType = value
                contentTypeIndex = i

        if httpEquiv and contentType: # It's an interesting meta tag.
            match = self.CHARSET_RE.search(contentType)
            if match:
                if (self.declaredHTMLEncoding is not None or
                    self.originalEncoding == self.fromEncoding):
                    # An HTML encoding was sniffed while converting
                    # the document to Unicode, or an HTML encoding was
                    # sniffed during a previous pass through the
                    # document, or an encoding was specified
                    # explicitly and it worked. Rewrite the meta tag.
                    def rewrite(match):
                        return match.group(1) + "%SOUP-ENCODING%"
                    newAttr = self.CHARSET_RE.sub(rewrite, contentType)
                    attrs[contentTypeIndex] = (attrs[contentTypeIndex][0],
                                               newAttr)
                    tagNeedsEncodingSubstitution = True
                else:
                    # This is our first pass through the document.
                    # Go through it again with the encoding information.
                    newCharset = match.group(3)
                    if newCharset and newCharset != self.originalEncoding:
                        self.declaredHTMLEncoding = newCharset
                        self._feed(self.declaredHTMLEncoding)
                        raise StopParsing
                    pass
        tag = self.unknown_starttag("meta", attrs)
        if tag and tagNeedsEncodingSubstitution:
            tag.containsSubstitutions = True

class StopParsing(Exception):
    pass

class ICantBelieveItsBeautifulSoup(BeautifulSoup):

    """The BeautifulSoup class is oriented towards skipping over
    common HTML errors like unclosed tags. However, sometimes it makes
    errors of its own. For instance, consider this fragment:

     <b>Foo<b>Bar</b></b>

    This is perfectly valid (if bizarre) HTML. However, the
    BeautifulSoup class will implicitly close the first b tag when it
    encounters the second 'b'. It will think the author wrote
    "<b>Foo<b>Bar", and didn't close the first 'b' tag, because
    there's no real-world reason to bold something that's already
    bold. When it encounters '</b></b>' it will close two more 'b'
    tags, for a grand total of three tags closed instead of two. This
    can throw off the rest of your document structure. The same is
    true of a number of other tags, listed below.

    It's much more common for someone to forget to close a 'b' tag
    than to actually use nested 'b' tags, and the BeautifulSoup class
    handles the common case. This class handles the not-co-common
    case: where you can't believe someone wrote what they did, but
    it's valid HTML and BeautifulSoup screwed up by assuming it
    wouldn't be."""

    I_CANT_BELIEVE_THEYRE_NESTABLE_INLINE_TAGS = \
     ['em', 'big', 'i', 'small', 'tt', 'abbr', 'acronym', 'strong',
      'cite', 'code', 'dfn', 'kbd', 'samp', 'strong', 'var', 'b',
      'big']

    I_CANT_BELIEVE_THEYRE_NESTABLE_BLOCK_TAGS = ['noscript']

    NESTABLE_TAGS = buildTagMap([], BeautifulSoup.NESTABLE_TAGS,
                                I_CANT_BELIEVE_THEYRE_NESTABLE_BLOCK_TAGS,
                                I_CANT_BELIEVE_THEYRE_NESTABLE_INLINE_TAGS)

class MinimalSoup(BeautifulSoup):
    """The MinimalSoup class is for parsing HTML that contains
    pathologically bad markup. It makes no assumptions about tag
    nesting, but it does know which tags are self-closing, that
    <script> tags contain Javascript and should not be parsed, that
    META tags may contain encoding information, and so on.

    This also makes it better for subclassing than BeautifulStoneSoup
    or BeautifulSoup."""

    RESET_NESTING_TAGS = buildTagMap('noscript')
    NESTABLE_TAGS = {}

class BeautifulSOAP(BeautifulStoneSoup):
    """This class will push a tag with only a single string child into
    the tag's parent as an attribute. The attribute's name is the tag
    name, and the value is the string child. An example should give
    the flavor of the change:

    <foo><bar>baz</bar></foo>
     =>
    <foo bar="baz"><bar>baz</bar></foo>

    You can then access fooTag['bar'] instead of fooTag.barTag.string.

    This is, of course, useful for scraping structures that tend to
    use subelements instead of attributes, such as SOAP messages. Note
    that it modifies its input, so don't print the modified version
    out.

    I'm not sure how many people really want to use this class; let me
    know if you do. Mainly I like the name."""

    def popTag(self):
        if len(self.tagStack) > 1:
            tag = self.tagStack[-1]
            parent = self.tagStack[-2]
            parent._getAttrMap()
            if (isinstance(tag, Tag) and len(tag.contents) == 1 and
                isinstance(tag.contents[0], NavigableString) and
                not parent.attrMap.has_key(tag.name)):
                parent[tag.name] = tag.contents[0]
        BeautifulStoneSoup.popTag(self)

#Enterprise class names! It has come to our attention that some people
#think the names of the Beautiful Soup parser classes are too silly
#and "unprofessional" for use in enterprise screen-scraping. We feel
#your pain! For such-minded folk, the Beautiful Soup Consortium And
#All-Night Kosher Bakery recommends renaming this file to
#"RobustParser.py" (or, in cases of extreme enterprisiness,
#"RobustParserBeanInterface.class") and using the following
#enterprise-friendly class aliases:
class RobustXMLParser(BeautifulStoneSoup):
    pass
class RobustHTMLParser(BeautifulSoup):
    pass
class RobustWackAssHTMLParser(ICantBelieveItsBeautifulSoup):
    pass
class RobustInsanelyWackAssHTMLParser(MinimalSoup):
    pass
class SimplifyingSOAPParser(BeautifulSOAP):
    pass

######################################################
#
# Bonus library: Unicode, Dammit
#
# This class forces XML data into a standard format (usually to UTF-8
# or Unicode).  It is heavily based on code from Mark Pilgrim's
# Universal Feed Parser. It does not rewrite the XML or HTML to
# reflect a new encoding: that happens in BeautifulStoneSoup.handle_pi
# (XML) and BeautifulSoup.start_meta (HTML).

# Autodetects character encodings.
# Download from http://chardet.feedparser.org/
try:
    import chardet
#    import chardet.constants
#    chardet.constants._debug = 1
except ImportError:
    chardet = None

# cjkcodecs and iconv_codec make Python know about more character encodings.
# Both are available from http://cjkpython.i18n.org/
# They're built in if you use Python 2.4.
try:
    import cjkcodecs.aliases
except ImportError:
    pass
try:
    import iconv_codec
except ImportError:
    pass

class UnicodeDammit:
    """A class for detecting the encoding of a *ML document and
    converting it to a Unicode string. If the source encoding is
    windows-1252, can replace MS smart quotes with their HTML or XML
    equivalents."""

    # This dictionary maps commonly seen values for "charset" in HTML
    # meta tags to the corresponding Python codec names. It only covers
    # values that aren't in Python's aliases and can't be determined
    # by the heuristics in find_codec.
    CHARSET_ALIASES = { "macintosh" : "mac-roman",
                        "x-sjis" : "shift-jis" }

    def __init__(self, markup, overrideEncodings=[],
                 smartQuotesTo='xml', isHTML=False):
        self.declaredHTMLEncoding = None
        self.markup, documentEncoding, sniffedEncoding = \
                     self._detectEncoding(markup, isHTML)
        self.smartQuotesTo = smartQuotesTo
        self.triedEncodings = []
        if markup == '' or isinstance(markup, unicode):
            self.originalEncoding = None
            self.unicode = unicode(markup)
            return

        u = None
        for proposedEncoding in overrideEncodings:
            u = self._convertFrom(proposedEncoding)
            if u: break
        if not u:
            for proposedEncoding in (documentEncoding, sniffedEncoding):
                u = self._convertFrom(proposedEncoding)
                if u: break

        # If no luck and we have auto-detection library, try that:
        if not u and chardet and not isinstance(self.markup, unicode):
            u = self._convertFrom(chardet.detect(self.markup)['encoding'])

        # As a last resort, try utf-8 and windows-1252:
        if not u:
            for proposed_encoding in ("utf-8", "windows-1252"):
                u = self._convertFrom(proposed_encoding)
                if u: break

        self.unicode = u
        if not u: self.originalEncoding = None

    def _subMSChar(self, orig):
        """Changes a MS smart quote character to an XML or HTML
        entity."""
        sub = self.MS_CHARS.get(orig)
        if type(sub) == types.TupleType:
            if self.smartQuotesTo == 'xml':
                sub = '&#x%s;' % sub[1]
            else:
                sub = '&%s;' % sub[0]
        return sub

    def _convertFrom(self, proposed):
        proposed = self.find_codec(proposed)
        if not proposed or proposed in self.triedEncodings:
            return None
        self.triedEncodings.append(proposed)
        markup = self.markup

        # Convert smart quotes to HTML if coming from an encoding
        # that might have them.
        if self.smartQuotesTo and proposed.lower() in("windows-1252",
                                                      "iso-8859-1",
                                                      "iso-8859-2"):
            markup = re.compile("([\x80-\x9f])").sub \
                     (lambda(x): self._subMSChar(x.group(1)),
                      markup)

        try:
            # print "Trying to convert document to %s" % proposed
            u = self._toUnicode(markup, proposed)
            self.markup = u
            self.originalEncoding = proposed
        except Exception, e:
            # print "That didn't work!"
            # print e
            return None
        #print "Correct encoding: %s" % proposed
        return self.markup

    def _toUnicode(self, data, encoding):
        '''Given a string and its encoding, decodes the string into Unicode.
        %encoding is a string recognized by encodings.aliases'''

        # strip Byte Order Mark (if present)
        if (len(data) >= 4) and (data[:2] == '\xfe\xff') \
               and (data[2:4] != '\x00\x00'):
            encoding = 'utf-16be'
            data = data[2:]
        elif (len(data) >= 4) and (data[:2] == '\xff\xfe') \
                 and (data[2:4] != '\x00\x00'):
            encoding = 'utf-16le'
            data = data[2:]
        elif data[:3] == '\xef\xbb\xbf':
            encoding = 'utf-8'
            data = data[3:]
        elif data[:4] == '\x00\x00\xfe\xff':
            encoding = 'utf-32be'
            data = data[4:]
        elif data[:4] == '\xff\xfe\x00\x00':
            encoding = 'utf-32le'
            data = data[4:]
        newdata = unicode(data, encoding)
        return newdata

    def _detectEncoding(self, xml_data, isHTML=False):
        """Given a document, tries to detect its XML encoding."""
        xml_encoding = sniffed_xml_encoding = None
        try:
            if xml_data[:4] == '\x4c\x6f\xa7\x94':
                # EBCDIC
                xml_data = self._ebcdic_to_ascii(xml_data)
            elif xml_data[:4] == '\x00\x3c\x00\x3f':
                # UTF-16BE
                sniffed_xml_encoding = 'utf-16be'
                xml_data = unicode(xml_data, 'utf-16be').encode('utf-8')
            elif (len(xml_data) >= 4) and (xml_data[:2] == '\xfe\xff') \
                     and (xml_data[2:4] != '\x00\x00'):
                # UTF-16BE with BOM
                sniffed_xml_encoding = 'utf-16be'
                xml_data = unicode(xml_data[2:], 'utf-16be').encode('utf-8')
            elif xml_data[:4] == '\x3c\x00\x3f\x00':
                # UTF-16LE
                sniffed_xml_encoding = 'utf-16le'
                xml_data = unicode(xml_data, 'utf-16le').encode('utf-8')
            elif (len(xml_data) >= 4) and (xml_data[:2] == '\xff\xfe') and \
                     (xml_data[2:4] != '\x00\x00'):
                # UTF-16LE with BOM
                sniffed_xml_encoding = 'utf-16le'
                xml_data = unicode(xml_data[2:], 'utf-16le').encode('utf-8')
            elif xml_data[:4] == '\x00\x00\x00\x3c':
                # UTF-32BE
                sniffed_xml_encoding = 'utf-32be'
                xml_data = unicode(xml_data, 'utf-32be').encode('utf-8')
            elif xml_data[:4] == '\x3c\x00\x00\x00':
                # UTF-32LE
                sniffed_xml_encoding = 'utf-32le'
                xml_data = unicode(xml_data, 'utf-32le').encode('utf-8')
            elif xml_data[:4] == '\x00\x00\xfe\xff':
                # UTF-32BE with BOM
                sniffed_xml_encoding = 'utf-32be'
                xml_data = unicode(xml_data[4:], 'utf-32be').encode('utf-8')
            elif xml_data[:4] == '\xff\xfe\x00\x00':
                # UTF-32LE with BOM
                sniffed_xml_encoding = 'utf-32le'
                xml_data = unicode(xml_data[4:], 'utf-32le').encode('utf-8')
            elif xml_data[:3] == '\xef\xbb\xbf':
                # UTF-8 with BOM
                sniffed_xml_encoding = 'utf-8'
                xml_data = unicode(xml_data[3:], 'utf-8').encode('utf-8')
            else:
                sniffed_xml_encoding = 'ascii'
                pass
        except:
            xml_encoding_match = None
        xml_encoding_match = re.compile(
            '^<\?.*encoding=[\'"](.*?)[\'"].*\?>').match(xml_data)
        if not xml_encoding_match and isHTML:
            regexp = re.compile('<\s*meta[^>]+charset=([^>]*?)[;\'">]', re.I)
            xml_encoding_match = regexp.search(xml_data)
        if xml_encoding_match is not None:
            xml_encoding = xml_encoding_match.groups()[0].lower()
            if isHTML:
                self.declaredHTMLEncoding = xml_encoding
            if sniffed_xml_encoding and \
               (xml_encoding in ('iso-10646-ucs-2', 'ucs-2', 'csunicode',
                                 'iso-10646-ucs-4', 'ucs-4', 'csucs4',
                                 'utf-16', 'utf-32', 'utf_16', 'utf_32',
                                 'utf16', 'u16')):
                xml_encoding = sniffed_xml_encoding
        return xml_data, xml_encoding, sniffed_xml_encoding


    def find_codec(self, charset):
        return self._codec(self.CHARSET_ALIASES.get(charset, charset)) \
               or (charset and self._codec(charset.replace("-", ""))) \
               or (charset and self._codec(charset.replace("-", "_"))) \
               or charset

    def _codec(self, charset):
        if not charset: return charset
        codec = None
        try:
            codecs.lookup(charset)
            codec = charset
        except (LookupError, ValueError):
            pass
        return codec

    EBCDIC_TO_ASCII_MAP = None
    def _ebcdic_to_ascii(self, s):
        c = self.__class__
        if not c.EBCDIC_TO_ASCII_MAP:
            emap = (0,1,2,3,156,9,134,127,151,141,142,11,12,13,14,15,
                    16,17,18,19,157,133,8,135,24,25,146,143,28,29,30,31,
                    128,129,130,131,132,10,23,27,136,137,138,139,140,5,6,7,
                    144,145,22,147,148,149,150,4,152,153,154,155,20,21,158,26,
                    32,160,161,162,163,164,165,166,167,168,91,46,60,40,43,33,
                    38,169,170,171,172,173,174,175,176,177,93,36,42,41,59,94,
                    45,47,178,179,180,181,182,183,184,185,124,44,37,95,62,63,
                    186,187,188,189,190,191,192,193,194,96,58,35,64,39,61,34,
                    195,97,98,99,100,101,102,103,104,105,196,197,198,199,200,
                    201,202,106,107,108,109,110,111,112,113,114,203,204,205,
                    206,207,208,209,126,115,116,117,118,119,120,121,122,210,
                    211,212,213,214,215,216,217,218,219,220,221,222,223,224,
                    225,226,227,228,229,230,231,123,65,66,67,68,69,70,71,72,
                    73,232,233,234,235,236,237,125,74,75,76,77,78,79,80,81,
                    82,238,239,240,241,242,243,92,159,83,84,85,86,87,88,89,
                    90,244,245,246,247,248,249,48,49,50,51,52,53,54,55,56,57,
                    250,251,252,253,254,255)
            import string
            c.EBCDIC_TO_ASCII_MAP = string.maketrans( \
            ''.join(map(chr, range(256))), ''.join(map(chr, emap)))
        return s.translate(c.EBCDIC_TO_ASCII_MAP)

    MS_CHARS = { '\x80' : ('euro', '20AC'),
                 '\x81' : ' ',
                 '\x82' : ('sbquo', '201A'),
                 '\x83' : ('fnof', '192'),
                 '\x84' : ('bdquo', '201E'),
                 '\x85' : ('hellip', '2026'),
                 '\x86' : ('dagger', '2020'),
                 '\x87' : ('Dagger', '2021'),
                 '\x88' : ('circ', '2C6'),
                 '\x89' : ('permil', '2030'),
                 '\x8A' : ('Scaron', '160'),
                 '\x8B' : ('lsaquo', '2039'),
                 '\x8C' : ('OElig', '152'),
                 '\x8D' : '?',
                 '\x8E' : ('#x17D', '17D'),
                 '\x8F' : '?',
                 '\x90' : '?',
                 '\x91' : ('lsquo', '2018'),
                 '\x92' : ('rsquo', '2019'),
                 '\x93' : ('ldquo', '201C'),
                 '\x94' : ('rdquo', '201D'),
                 '\x95' : ('bull', '2022'),
                 '\x96' : ('ndash', '2013'),
                 '\x97' : ('mdash', '2014'),
                 '\x98' : ('tilde', '2DC'),
                 '\x99' : ('trade', '2122'),
                 '\x9a' : ('scaron', '161'),
                 '\x9b' : ('rsaquo', '203A'),
                 '\x9c' : ('oelig', '153'),
                 '\x9d' : '?',
                 '\x9e' : ('#x17E', '17E'),
                 '\x9f' : ('Yuml', ''),}

#######################################################################


#By default, act as an HTML pretty-printer.
if __name__ == '__main__':
    import sys
    soup = BeautifulSoup(sys.stdin)
    print soup.prettify()

########NEW FILE########
__FILENAME__ = collections2
__all__ = ['deque', 'defaultdict', 'namedtuple']
# For bootstrapping reasons, the collection ABCs are defined in _abcoll.py.
# They should however be considered an integral part of collections.py.

from collections import *
## from _abcoll import *
## import _abcoll
## __all__ += _abcoll.__all__

## from _collections import deque, defaultdict
from operator import itemgetter as _itemgetter
from keyword import iskeyword as _iskeyword
import sys as _sys

def namedtuple(typename, field_names, verbose=False):
    """Returns a new subclass of tuple with named fields.

    >>> Point = namedtuple('Point', 'x y')
    >>> Point.__doc__                   # docstring for the new class
    'Point(x, y)'
    >>> p = Point(11, y=22)             # instantiate with positional args or keywords
    >>> p[0] + p[1]                     # indexable like a plain tuple
    33
    >>> x, y = p                        # unpack like a regular tuple
    >>> x, y
    (11, 22)
    >>> p.x + p.y                       # fields also accessable by name
    33
    >>> d = p._asdict()                 # convert to a dictionary
    >>> d['x']
    11
    >>> Point(**d)                      # convert from a dictionary
    Point(x=11, y=22)
    >>> p._replace(x=100)               # _replace() is like str.replace() but targets named fields
    Point(x=100, y=22)

    """

    # Parse and validate the field names.  Validation serves two purposes,
    # generating informative error messages and preventing template injection attacks.
    if isinstance(field_names, basestring):
        field_names = field_names.replace(',', ' ').split() # names separated by whitespace and/or commas
    field_names = tuple(field_names)
    for name in (typename,) + field_names:
        if not all(c.isalnum() or c=='_' for c in name):
            raise ValueError('Type names and field names can only contain alphanumeric characters and underscores: %r' % name)
        if _iskeyword(name):
            raise ValueError('Type names and field names cannot be a keyword: %r' % name)
        if name[0].isdigit():
            raise ValueError('Type names and field names cannot start with a number: %r' % name)
    seen_names = set()
    for name in field_names:
        if name.startswith('_'):
            raise ValueError('Field names cannot start with an underscore: %r' % name)
        if name in seen_names:
            raise ValueError('Encountered duplicate field name: %r' % name)
        seen_names.add(name)

    # Create and fill-in the class template
    numfields = len(field_names)
    argtxt = repr(field_names).replace("'", "")[1:-1]   # tuple repr without parens or quotes
    reprtxt = ', '.join('%s=%%r' % name for name in field_names)
    dicttxt = ', '.join('%r: t[%d]' % (name, pos) for pos, name in enumerate(field_names))
    template = '''class %(typename)s(tuple):
        '%(typename)s(%(argtxt)s)' \n
        __slots__ = () \n
        _fields = %(field_names)r \n
        def __new__(cls, %(argtxt)s):
            return tuple.__new__(cls, (%(argtxt)s)) \n
        @classmethod
        def _make(cls, iterable, new=tuple.__new__, len=len):
            'Make a new %(typename)s object from a sequence or iterable'
            result = new(cls, iterable)
            if len(result) != %(numfields)d:
                raise TypeError('Expected %(numfields)d arguments, got %%d' %% len(result))
            return result \n
        def __repr__(self):
            return '%(typename)s(%(reprtxt)s)' %% self \n
        def _asdict(t):
            'Return a new dict which maps field names to their values'
            return {%(dicttxt)s} \n
        def _replace(self, **kwds):
            'Return a new %(typename)s object replacing specified fields with new values'
            result = self._make(map(kwds.pop, %(field_names)r, self))
            if kwds:
                raise ValueError('Got unexpected field names: %%r' %% kwds.keys())
            return result \n\n''' % locals()
    for i, name in enumerate(field_names):
        template += '        %s = property(itemgetter(%d))\n' % (name, i)
    if verbose:
        print template

    # Execute the template string in a temporary namespace
    namespace = dict(itemgetter=_itemgetter)
    try:
        exec template in namespace
    except SyntaxError, e:
        raise SyntaxError(e.message + ':\n' + template)
    result = namespace[typename]

    # For pickling to work, the __module__ variable needs to be set to the frame
    # where the named tuple is created.  Bypass this step in enviroments where
    # sys._getframe is not defined (Jython for example).
    if hasattr(_sys, '_getframe'):
        result.__module__ = _sys._getframe(1).f_globals['__name__']

    return result






if __name__ == '__main__':
    # verify that instances can be pickled
    from cPickle import loads, dumps
    Point = namedtuple('Point', 'x, y', True)
    p = Point(x=10, y=20)
    assert p == loads(dumps(p))

    # test and demonstrate ability to override methods
    class Point(namedtuple('Point', 'x y')):
        __slots__ = ()
        @property
        def hypot(self):
            return (self.x ** 2 + self.y ** 2) ** 0.5
        def __str__(self):
            return 'Point: x=%6.3f  y=%6.3f  hypot=%6.3f' % (self.x, self.y, self.hypot)

    for p in Point(3, 4), Point(14, 5/7.):
        print p

    class Point(namedtuple('Point', 'x y')):
        'Point class with optimized _make() and _replace() without error-checking'
        __slots__ = ()
        _make = classmethod(tuple.__new__)
        def _replace(self, _map=map, **kwds):
            return self._make(_map(kwds.get, ('x', 'y'), self))

    print Point(11, 22)._replace(x=100)

    Point3D = namedtuple('Point3D', Point._fields + ('z',))
    print Point3D.__doc__

    import doctest
    TestResults = namedtuple('TestResults', 'failed attempted')
    print TestResults(*doctest.testmod())

########NEW FILE########
__FILENAME__ = colorlog
"""
A logging module Formatter class that adds colors to the output.
"""

# stdlib imports
import logging
from logging import Formatter

# local imports
from termctrl import TerminalController


class ColorFormatter(Formatter):
    "A logging Formatter class that adds colors to the output."
    
    colordef = (
        (logging.CRITICAL , 'BOLD MAGENTA'),
        (logging.ERROR    , 'BOLD RED'),
        (logging.WARNING  , 'BOLD YELLOW'),
        (logging.INFO     , 'BOLD GREEN'),
        (logging.DEBUG    , 'BOLD CYAN'),
        )

    def __init__(self, stream, *args, **kwds):
        Formatter.__init__(self, *args, **kwds)

        # Create a mapping of levels to format string which is prepared to
        # contain the escape sequences.
        term = TerminalController(stream)
        self.color_fmt = {}
        for levelno, colstr in self.colordef:
            slist = [getattr(term, c) for c in colstr.split()] + ['%s', term.NORMAL]
            self.color_fmt[levelno] = ''.join(slist)

    def format(self, record):
        return self.color_fmt[record.levelno] % Formatter.format(self, record)


########NEW FILE########
__FILENAME__ = ElementInclude
#
# ElementTree
# $Id: ElementInclude.py 3265 2007-09-06 20:42:00Z fredrik $
#
# limited xinclude support for element trees
#
# history:
# 2003-08-15 fl   created
# 2003-11-14 fl   fixed default loader
#
# Copyright (c) 2003-2004 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2007 by Fredrik Lundh
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

##
# Limited XInclude support for the ElementTree package.
##

import copy
import ElementTree

XINCLUDE = "{http://www.w3.org/2001/XInclude}"

XINCLUDE_INCLUDE = XINCLUDE + "include"
XINCLUDE_FALLBACK = XINCLUDE + "fallback"

##
# Fatal include error.

class FatalIncludeError(SyntaxError):
    pass

##
# Default loader.  This loader reads an included resource from disk.
#
# @param href Resource reference.
# @param parse Parse mode.  Either "xml" or "text".
# @param encoding Optional text encoding.
# @return The expanded resource.  If the parse mode is "xml", this
#    is an ElementTree instance.  If the parse mode is "text", this
#    is a Unicode string.  If the loader fails, it can return None
#    or raise an IOError exception.
# @throws IOError If the loader fails to load the resource.

def default_loader(href, parse, encoding=None):
    file = open(href)
    if parse == "xml":
        data = ElementTree.parse(file).getroot()
    else:
        data = file.read()
        if encoding:
            data = data.decode(encoding)
    file.close()
    return data

##
# Expand XInclude directives.
#
# @param elem Root element.
# @param loader Optional resource loader.  If omitted, it defaults
#     to {@link default_loader}.  If given, it should be a callable
#     that implements the same interface as <b>default_loader</b>.
# @throws FatalIncludeError If the function fails to include a given
#     resource, or if the tree contains malformed XInclude elements.
# @throws IOError If the function fails to load a given resource.

def include(elem, loader=None):
    if loader is None:
        loader = default_loader
    # look for xinclude elements
    i = 0
    while i < len(elem):
        e = elem[i]
        if e.tag == XINCLUDE_INCLUDE:
            # process xinclude directive
            href = e.get("href")
            parse = e.get("parse", "xml")
            if parse == "xml":
                node = loader(href, parse)
                if node is None:
                    raise FatalIncludeError(
                        "cannot load %r as %r" % (href, parse)
                        )
                node = copy.copy(node)
                if e.tail:
                    node.tail = (node.tail or "") + e.tail
                elem[i] = node
            elif parse == "text":
                text = loader(href, parse, e.get("encoding"))
                if text is None:
                    raise FatalIncludeError(
                        "cannot load %r as %r" % (href, parse)
                        )
                if i:
                    node = elem[i-1]
                    node.tail = (node.tail or "") + text
                else:
                    elem.text = (elem.text or "") + text + (e.tail or "")
                del elem[i]
                continue
            else:
                raise FatalIncludeError(
                    "unknown parse type in xi:include tag (%r)" % parse
                )
        elif e.tag == XINCLUDE_FALLBACK:
            raise FatalIncludeError(
                "xi:fallback tag must be child of xi:include (%r)" % e.tag
                )
        else:
            include(e, loader)
        i = i + 1

########NEW FILE########
__FILENAME__ = ElementPath
#
# ElementTree
# $Id: ElementPath.py 3276 2007-09-12 06:52:30Z fredrik $
#
# limited xpath support for element trees
#
# history:
# 2003-05-23 fl   created
# 2003-05-28 fl   added support for // etc
# 2003-08-27 fl   fixed parsing of periods in element names
# 2007-09-10 fl   new selection engine
#
# Copyright (c) 2003-2007 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2007 by Fredrik Lundh
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

##
# Implementation module for XPath support.  There's usually no reason
# to import this module directly; the <b>ElementTree</b> does this for
# you, if needed.
##

import re

xpath_tokenizer = re.compile(
    "("
    "'[^']*'|\"[^\"]*\"|"
    "::|"
    "//?|"
    "\.\.|"
    "\(\)|"
    "[/.*:\[\]\(\)@=])|"
    "((?:\{[^}]+\})?[^/:\[\]\(\)@=\s]+)|"
    "\s+"
    ).findall

def prepare_tag(next, token):
    tag = token[1]
    def select(context, result):
        for elem in result:
            for e in elem:
                if e.tag == tag:
                    yield e
    return select

def prepare_star(next, token):
    def select(context, result):
        for elem in result:
            for e in elem:
                yield e
    return select

def prepare_dot(next, token):
    def select(context, result):
        for elem in result:
            yield elem
    return select

def prepare_iter(next, token):
    token = next()
    if token[0] == "*":
        tag = "*"
    elif not token[0]:
        tag = token[1]
    else:
        raise SyntaxError
    def select(context, result):
        for elem in result:
            for e in elem.iter(tag):
                if e is not elem:
                    yield e
    return select

def prepare_dot_dot(next, token):
    def select(context, result):
        parent_map = context.parent_map
        if parent_map is None:
            context.parent_map = parent_map = {}
            for p in context.root.iter():
                for e in p:
                    parent_map[e] = p
        for elem in result:
            if elem in parent_map:
                yield parent_map[elem]
    return select

def prepare_predicate(next, token):
    # this one should probably be refactored...
    token = next()
    if token[0] == "@":
        # attribute
        token = next()
        if token[0]:
            raise SyntaxError("invalid attribute predicate")
        key = token[1]
        token = next()
        if token[0] == "]":
            def select(context, result):
                for elem in result:
                    if elem.get(key) is not None:
                        yield elem
        elif token[0] == "=":
            value = next()[0]
            if value[:1] == "'" or value[:1] == '"':
                value = value[1:-1]
            else:
                raise SyntaxError("invalid comparision target")
            token = next()
            def select(context, result):
                for elem in result:
                    if elem.get(key) == value:
                        yield elem
        if token[0] != "]":
            raise SyntaxError("invalid attribute predicate")
    elif not token[0]:
        tag = token[1]
        token = next()
        if token[0] != "]":
            raise SyntaxError("invalid node predicate")
        def select(context, result):
            for elem in result:
                if elem.find(tag) is not None:
                    yield elem
    else:
        raise SyntaxError("invalid predicate")
    return select

ops = {
    "": prepare_tag,
    "*": prepare_star,
    ".": prepare_dot,
    "..": prepare_dot_dot,
    "//": prepare_iter,
    "[": prepare_predicate,
    }

_cache = {}

class _SelectorContext:
    parent_map = None
    def __init__(self, root):
        self.root = root

# --------------------------------------------------------------------

##
# Find first matching object.

def find(elem, path):
    try:
        return findall(elem, path).next()
    except StopIteration:
        return None

##
# Find all matching objects.

def findall(elem, path):
    # compile selector pattern
    try:
        selector = _cache[path]
    except KeyError:
        if len(_cache) > 100:
            _cache.clear()
        if path[:1] == "/":
            raise SyntaxError("cannot use absolute path on element")
        stream = iter(xpath_tokenizer(path))
        next = stream.next; token = next()
        selector = []
        while 1:
            try:
                selector.append(ops[token[0]](next, token))
            except StopIteration:
                raise SyntaxError("invalid path")
            try:
                token = next()
                if token[0] == "/":
                    token = next()
            except StopIteration:
                break
        _cache[path] = selector
    # execute selector pattern
    result = [elem]
    context = _SelectorContext(elem)
    for select in selector:
        result = select(context, result)
    return result

##
# Find text for first matching object.

def findtext(elem, path, default=None):
    try:
        elem = findall(elem, path).next()
        return elem.text
    except StopIteration:
        return default

########NEW FILE########
__FILENAME__ = ElementTree
#
# ElementTree
# $Id: ElementTree.py 3276 2007-09-12 06:52:30Z fredrik $
#
# light-weight XML support for Python 2.2 and later.
#
# history:
# 2001-10-20 fl   created (from various sources)
# 2001-11-01 fl   return root from parse method
# 2002-02-16 fl   sort attributes in lexical order
# 2002-04-06 fl   TreeBuilder refactoring, added PythonDoc markup
# 2002-05-01 fl   finished TreeBuilder refactoring
# 2002-07-14 fl   added basic namespace support to ElementTree.write
# 2002-07-25 fl   added QName attribute support
# 2002-10-20 fl   fixed encoding in write
# 2002-11-24 fl   changed default encoding to ascii; fixed attribute encoding
# 2002-11-27 fl   accept file objects or file names for parse/write
# 2002-12-04 fl   moved XMLTreeBuilder back to this module
# 2003-01-11 fl   fixed entity encoding glitch for us-ascii
# 2003-02-13 fl   added XML literal factory
# 2003-02-21 fl   added ProcessingInstruction/PI factory
# 2003-05-11 fl   added tostring/fromstring helpers
# 2003-05-26 fl   added ElementPath support
# 2003-07-05 fl   added makeelement factory method
# 2003-07-28 fl   added more well-known namespace prefixes
# 2003-08-15 fl   fixed typo in ElementTree.findtext (Thomas Dartsch)
# 2003-09-04 fl   fall back on emulator if ElementPath is not installed
# 2003-10-31 fl   markup updates
# 2003-11-15 fl   fixed nested namespace bug
# 2004-03-28 fl   added XMLID helper
# 2004-06-02 fl   added default support to findtext
# 2004-06-08 fl   fixed encoding of non-ascii element/attribute names
# 2004-08-23 fl   take advantage of post-2.1 expat features
# 2004-09-03 fl   made Element class visible; removed factory
# 2005-02-01 fl   added iterparse implementation
# 2005-03-02 fl   fixed iterparse support for pre-2.2 versions
# 2005-11-12 fl   added tostringlist/fromstringlist helpers
# 2006-07-05 fl   merged in selected changes from the 1.3 sandbox
# 2006-07-05 fl   removed support for 2.1 and earlier
# 2007-06-21 fl   added deprecation/future warnings
# 2007-08-25 fl   added doctype hook, added parser version attribute etc
# 2007-08-26 fl   added new serializer code (better namespace handling, etc)
# 2007-08-27 fl   warn for broken /tag searches on tree level
# 2007-09-02 fl   added html/text methods to serializer (experimental)
# 2007-09-05 fl   added method argument to tostring/tostringlist
# 2007-09-06 fl   improved error handling
#
# Copyright (c) 1999-2007 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2007 by Fredrik Lundh
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

from __future__ import generators

__all__ = [
    # public symbols
    "Comment",
    "dump",
    "Element", "ElementTree",
    "fromstring", "fromstringlist",
    "iselement", "iterparse",
    "parse", "ParseError",
    "PI", "ProcessingInstruction",
    "QName",
    "SubElement",
    "tostring", "tostringlist",
    "TreeBuilder",
    "VERSION",
    "XML",
    "XMLParser", "XMLTreeBuilder",
    ]

##
# The <b>Element</b> type is a flexible container object, designed to
# store hierarchical data structures in memory. The type can be
# described as a cross between a list and a dictionary.
# <p>
# Each element has a number of properties associated with it:
# <ul>
# <li>a <i>tag</i>. This is a string identifying what kind of data
# this element represents (the element type, in other words).</li>
# <li>a number of <i>attributes</i>, stored in a Python dictionary.</li>
# <li>a <i>text</i> string.</li>
# <li>an optional <i>tail</i> string.</li>
# <li>a number of <i>child elements</i>, stored in a Python sequence</li>
# </ul>
#
# To create an element instance, use the {@link #Element} constructor
# or the {@link #SubElement} factory function.
# <p>
# The {@link #ElementTree} class can be used to wrap an element
# structure, and convert it from and to XML.
##

import sys, re

class _SimpleElementPath(object):
    # emulate pre-1.2 find/findtext/findall behaviour
    def find(self, element, tag):
        for elem in element:
            if elem.tag == tag:
                return elem
        return None
    def findtext(self, element, tag, default=None):
        for elem in element:
            if elem.tag == tag:
                return elem.text or ""
        return default
    def findall(self, element, tag):
        if tag[:3] == ".//":
            return element.getiterator(tag[3:])
        result = []
        for elem in element:
            if elem.tag == tag:
                result.append(elem)
        return result

try:
    import ElementPath
except ImportError:
    # FIXME: issue warning in this case?
    ElementPath = _SimpleElementPath()

VERSION = "1.3a2"

class ParseError(SyntaxError):
    pass

# --------------------------------------------------------------------

##
# Checks if an object appears to be a valid element object.
#
# @param An element instance.
# @return A true value if this is an element object.
# @defreturn flag

def iselement(element):
    # FIXME: not sure about this; might be a better idea to look
    # for tag/attrib/text attributes
    return isinstance(element, Element) or hasattr(element, "tag")

##
# Element class.  This class defines the Element interface, and
# provides a reference implementation of this interface.
# <p>
# The element name, attribute names, and attribute values can be
# either 8-bit ASCII strings or Unicode strings.
#
# @param tag The element name.
# @param attrib An optional dictionary, containing element attributes.
# @param **extra Additional attributes, given as keyword arguments.
# @see Element
# @see SubElement
# @see Comment
# @see ProcessingInstruction

class Element(object):
    # <tag attrib>text<child/>...</tag>tail

    ##
    # (Attribute) Element tag.

    tag = None

    ##
    # (Attribute) Element attribute dictionary.  Where possible, use
    # {@link #Element.get},
    # {@link #Element.set},
    # {@link #Element.keys}, and
    # {@link #Element.items} to access
    # element attributes.

    attrib = None

    ##
    # (Attribute) Text before first subelement.  This is either a
    # string or the value None, if there was no text.

    text = None

    ##
    # (Attribute) Text after this element's end tag, but before the
    # next sibling element's start tag.  This is either a string or
    # the value None, if there was no text.

    tail = None # text after end tag, if any

    def __init__(self, tag, attrib={}, **extra):
        attrib = attrib.copy()
        attrib.update(extra)
        self.tag = tag
        self.attrib = attrib
        self._children = []

    def __repr__(self):
        return "<Element %s at %x>" % (repr(self.tag), id(self))

    ##
    # Creates a new element object of the same type as this element.
    #
    # @param tag Element tag.
    # @param attrib Element attributes, given as a dictionary.
    # @return A new element instance.

    def makeelement(self, tag, attrib):
        return Element(tag, attrib)

    ##
    # Returns the number of subelements.
    #
    # @return The number of subelements.

    def __len__(self):
        return len(self._children)

    def __nonzero__(self):
        import warnings
        warnings.warn(
            "The behavior of this method will change in future versions. "
            "Use specific 'len(elem)' or 'elem is not None' test instead.",
            FutureWarning
            )
        return len(self._children) != 0 # emulate old behaviour

    ##
    # Returns the given subelement.
    #
    # @param index What subelement to return.
    # @return The given subelement.
    # @exception IndexError If the given element does not exist.

    def __getitem__(self, index):
        return self._children[index]

    ##
    # Replaces the given subelement.
    #
    # @param index What subelement to replace.
    # @param element The new element value.
    # @exception IndexError If the given element does not exist.
    # @exception AssertionError If element is not a valid object.

    def __setitem__(self, index, element):
        assert iselement(element)
        self._children[index] = element

    ##
    # Deletes the given subelement.
    #
    # @param index What subelement to delete.
    # @exception IndexError If the given element does not exist.

    def __delitem__(self, index):
        del self._children[index]

    ##
    # Returns a list containing subelements in the given range.
    #
    # @param start The first subelement to return.
    # @param stop The first subelement that shouldn't be returned.
    # @return A sequence object containing subelements.

    def __getslice__(self, start, stop):
        return self._children[start:stop]

    ##
    # Replaces a number of subelements with elements from a sequence.
    #
    # @param start The first subelement to replace.
    # @param stop The first subelement that shouldn't be replaced.
    # @param elements A sequence object with zero or more elements.
    # @exception AssertionError If a sequence member is not a valid object.

    def __setslice__(self, start, stop, elements):
        for element in elements:
            assert iselement(element)
        self._children[start:stop] = list(elements)

    ##
    # Deletes a number of subelements.
    #
    # @param start The first subelement to delete.
    # @param stop The first subelement to leave in there.

    def __delslice__(self, start, stop):
        del self._children[start:stop]

    ##
    # Adds a subelement to the end of this element.
    #
    # @param element The element to add.
    # @exception AssertionError If a sequence member is not a valid object.

    def append(self, element):
        assert iselement(element)
        self._children.append(element)

    ##
    # Appends subelements from a sequence.
    #
    # @param elements A sequence object with zero or more elements.
    # @exception AssertionError If a subelement is not a valid object.
    # @since 1.3

    def extend(self, elements):
        for element in elements:
            assert iselement(element)
        self._children.extend(elements)

    ##
    # Inserts a subelement at the given position in this element.
    #
    # @param index Where to insert the new subelement.
    # @exception AssertionError If the element is not a valid object.

    def insert(self, index, element):
        assert iselement(element)
        self._children.insert(index, element)

    ##
    # Removes a matching subelement.  Unlike the <b>find</b> methods,
    # this method compares elements based on identity, not on tag
    # value or contents.
    #
    # @param element What element to remove.
    # @exception ValueError If a matching element could not be found.
    # @exception AssertionError If the element is not a valid object.

    def remove(self, element):
        assert iselement(element)
        self._children.remove(element)

    ##
    # (Deprecated) Returns all subelements.  The elements are returned
    # in document order.
    #
    # @return A list of subelements.
    # @defreturn list of Element instances

    def getchildren(self):
        import warnings
        warnings.warn(
            "This method will be removed in future versions. "
            "Use 'list(elem)' or iteration over elem instead.",
            DeprecationWarning
            )
        return self._children

    ##
    # Finds the first matching subelement, by tag name or path.
    #
    # @param path What element to look for.
    # @return The first matching element, or None if no element was found.
    # @defreturn Element or None

    def find(self, path):
        return ElementPath.find(self, path)

    ##
    # Finds text for the first matching subelement, by tag name or path.
    #
    # @param path What element to look for.
    # @param default What to return if the element was not found.
    # @return The text content of the first matching element, or the
    #     default value no element was found.  Note that if the element
    #     has is found, but has no text content, this method returns an
    #     empty string.
    # @defreturn string

    def findtext(self, path, default=None):
        return ElementPath.findtext(self, path, default)

    ##
    # Finds all matching subelements, by tag name or path.
    #
    # @param path What element to look for.
    # @return A list or iterator containing all matching elements,
    #    in document order.
    # @defreturn list of Element instances

    def findall(self, path):
        return ElementPath.findall(self, path)

    ##
    # Resets an element.  This function removes all subelements, clears
    # all attributes, and sets the text and tail attributes to None.

    def clear(self):
        self.attrib.clear()
        self._children = []
        self.text = self.tail = None

    ##
    # Gets an element attribute.
    #
    # @param key What attribute to look for.
    # @param default What to return if the attribute was not found.
    # @return The attribute value, or the default value, if the
    #     attribute was not found.
    # @defreturn string or None

    def get(self, key, default=None):
        return self.attrib.get(key, default)

    ##
    # Sets an element attribute.
    #
    # @param key What attribute to set.
    # @param value The attribute value.

    def set(self, key, value):
        self.attrib[key] = value

    ##
    # Gets a list of attribute names.  The names are returned in an
    # arbitrary order (just like for an ordinary Python dictionary).
    #
    # @return A list of element attribute names.
    # @defreturn list of strings

    def keys(self):
        return self.attrib.keys()

    ##
    # Gets element attributes, as a sequence.  The attributes are
    # returned in an arbitrary order.
    #
    # @return A list of (name, value) tuples for all attributes.
    # @defreturn list of (string, string) tuples

    def items(self):
        return self.attrib.items()

    ##
    # Creates a tree iterator.  The iterator loops over this element
    # and all subelements, in document order, and returns all elements
    # with a matching tag.
    # <p>
    # If the tree structure is modified during iteration, new or removed
    # elements may or may not be included.  To get a stable set, use the
    # list() function on the iterator, and loop over the resulting list.
    #
    # @param tag What tags to look for (default is to return all elements).
    # @return An iterator containing all the matching elements.
    # @defreturn iterator

    def iter(self, tag=None):
        if tag == "*":
            tag = None
        if tag is None or self.tag == tag:
            yield self
        for e in self._children:
            for e in e.iter(tag):
                yield e

    # compatibility (FIXME: preserve list behaviour too? see below)
    getiterator = iter

    # def getiterator(self, tag=None):
    #     return list(tag)

    ##
    # Creates a text iterator.  The iterator loops over this element
    # and all subelements, in document order, and returns all inner
    # text.
    #
    # @return An iterator containing all inner text.
    # @defreturn iterator

    def itertext(self):
        if self.text:
            yield self.text
        for e in self:
            for s in e.itertext():
                yield s
            if e.tail:
                yield e.tail

# compatibility
_Element = _ElementInterface = Element

##
# Subelement factory.  This function creates an element instance, and
# appends it to an existing element.
# <p>
# The element name, attribute names, and attribute values can be
# either 8-bit ASCII strings or Unicode strings.
#
# @param parent The parent element.
# @param tag The subelement name.
# @param attrib An optional dictionary, containing element attributes.
# @param **extra Additional attributes, given as keyword arguments.
# @return An element instance.
# @defreturn Element

def SubElement(parent, tag, attrib={}, **extra):
    attrib = attrib.copy()
    attrib.update(extra)
    element = parent.makeelement(tag, attrib)
    parent.append(element)
    return element

##
# Comment element factory.  This factory function creates a special
# element that will be serialized as an XML comment by the standard
# serializer.
# <p>
# The comment string can be either an 8-bit ASCII string or a Unicode
# string.
#
# @param text A string containing the comment string.
# @return An element instance, representing a comment.
# @defreturn Element

def Comment(text=None):
    element = Element(Comment)
    element.text = text
    return element

##
# PI element factory.  This factory function creates a special element
# that will be serialized as an XML processing instruction by the standard
# serializer.
#
# @param target A string containing the PI target.
# @param text A string containing the PI contents, if any.
# @return An element instance, representing a PI.
# @defreturn Element

def ProcessingInstruction(target, text=None):
    element = Element(ProcessingInstruction)
    element.text = target
    if text:
        element.text = element.text + " " + text
    return element

PI = ProcessingInstruction

##
# QName wrapper.  This can be used to wrap a QName attribute value, in
# order to get proper namespace handling on output.
#
# @param text A string containing the QName value, in the form {uri}local,
#     or, if the tag argument is given, the URI part of a QName.
# @param tag Optional tag.  If given, the first argument is interpreted as
#     an URI, and this argument is interpreted as a local name.
# @return An opaque object, representing the QName.

class QName(object):
    def __init__(self, text_or_uri, tag=None):
        if tag:
            text_or_uri = "{%s}%s" % (text_or_uri, tag)
        self.text = text_or_uri
    def __str__(self):
        return self.text
    def __hash__(self):
        return hash(self.text)
    def __cmp__(self, other):
        if isinstance(other, QName):
            return cmp(self.text, other.text)
        return cmp(self.text, other)

# --------------------------------------------------------------------

##
# ElementTree wrapper class.  This class represents an entire element
# hierarchy, and adds some extra support for serialization to and from
# standard XML.
#
# @param element Optional root element.
# @keyparam file Optional file handle or file name.  If given, the
#     tree is initialized with the contents of this XML file.

class ElementTree(object):

    def __init__(self, element=None, file=None):
        assert element is None or iselement(element)
        self._root = element # first node
        if file:
            self.parse(file)

    ##
    # Gets the root element for this tree.
    #
    # @return An element instance.
    # @defreturn Element

    def getroot(self):
        return self._root

    ##
    # Replaces the root element for this tree.  This discards the
    # current contents of the tree, and replaces it with the given
    # element.  Use with care.
    #
    # @param element An element instance.

    def _setroot(self, element):
        assert iselement(element)
        self._root = element

    ##
    # Loads an external XML document into this element tree.
    #
    # @param source A file name or file object.
    # @keyparam parser An optional parser instance.  If not given, the
    #     standard {@link XMLParser} parser is used.
    # @return The document root element.
    # @defreturn Element

    def parse(self, source, parser=None):
        if not hasattr(source, "read"):
            source = open(source, "rb")
        if not parser:
            parser = XMLParser(target=TreeBuilder())
        while 1:
            data = source.read(32768)
            if not data:
                break
            parser.feed(data)
        self._root = parser.close()
        return self._root

    ##
    # Creates a tree iterator for the root element.  The iterator loops
    # over all elements in this tree, in document order.
    #
    # @param tag What tags to look for (default is to return all elements)
    # @return An iterator.
    # @defreturn iterator

    def iter(self, tag=None):
        assert self._root is not None
        return self._root.iter(tag)

    getiterator = iter

    ##
    # Finds the first toplevel element with given tag.
    # Same as getroot().find(path).
    #
    # @param path What element to look for.
    # @return The first matching element, or None if no element was found.
    # @defreturn Element or None

    def find(self, path):
        assert self._root is not None
        if path[:1] == "/":
            path = "." + path
            import warnings
            warnings.warn(
                "This search is broken in 1.3 and earlier; if you rely "
                "on the current behaviour, change it to %r" % path,
                FutureWarning
                )
        return self._root.find(path)

    ##
    # Finds the element text for the first toplevel element with given
    # tag.  Same as getroot().findtext(path).
    #
    # @param path What toplevel element to look for.
    # @param default What to return if the element was not found.
    # @return The text content of the first matching element, or the
    #     default value no element was found.  Note that if the element
    #     has is found, but has no text content, this method returns an
    #     empty string.
    # @defreturn string

    def findtext(self, path, default=None):
        assert self._root is not None
        if path[:1] == "/":
            path = "." + path
            import warnings
            warnings.warn(
                "This search is broken in 1.3 and earlier; if you rely "
                "on the current behaviour, change it to %r" % path,
                FutureWarning
                )
        return self._root.findtext(path, default)

    ##
    # Finds all toplevel elements with the given tag.
    # Same as getroot().findall(path).
    #
    # @param path What element to look for.
    # @return A list or iterator containing all matching elements,
    #    in document order.
    # @defreturn list of Element instances

    def findall(self, path):
        assert self._root is not None
        if path[:1] == "/":
            path = "." + path
            import warnings
            warnings.warn(
                "This search is broken in 1.3 and earlier; if you rely "
                "on the current behaviour, change it to %r" % path,
                FutureWarning
                )
        return self._root.findall(path)

    ##
    # Writes the element tree to a file, as XML.
    #
    # @param file A file name, or a file object opened for writing.
    # @keyparam encoding Optional output encoding (default is US-ASCII).
    # @keyparam method Optional output method ("xml" or "html"; default
    #     is "xml".
    # @keyparam xml_declaration Controls if an XML declaration should
    #     be added to the file.  Use False for never, True for always,
    #     None for only if not US-ASCII or UTF-8.  None is default.

    def write(self, file,
              # keyword arguments
              encoding="us-ascii",
              xml_declaration=None,
              default_namespace=None,
              method=None):
        assert self._root is not None
        if not hasattr(file, "write"):
            file = open(file, "wb")
        write = file.write
        if not method:
            method = "xml"
        if not encoding:
            encoding = "us-ascii"
        elif xml_declaration or (xml_declaration is None and
                                 encoding not in ("utf-8", "us-ascii")):
            write("<?xml version='1.0' encoding='%s'?>\n" % encoding)
        if method == "text":
            _serialize_text(write, self._root, encoding)
        else:
            qnames, namespaces = _namespaces(
                self._root, encoding, default_namespace
                )
            if method == "xml":
                _serialize_xml(
                    write, self._root, encoding, qnames, namespaces
                    )
            elif method == "html":
                _serialize_html(
                    write, self._root, encoding, qnames, namespaces
                    )
            else:
                raise ValueError("unknown method %r" % method)

# --------------------------------------------------------------------
# serialization support

def _namespaces(elem, encoding, default_namespace=None):
    # identify namespaces used in this tree

    # maps qnames to *encoded* prefix:local names
    qnames = {None: None}

    # maps uri:s to prefixes
    namespaces = {}
    if default_namespace:
        namespaces[default_namespace] = ""

    def encode(text):
        return text.encode(encoding)

    def add_qname(qname):
        # calculate serialized qname representation
        try:
            if qname[:1] == "{":
                uri, tag = qname[1:].split("}", 1)
                prefix = namespaces.get(uri)
                if prefix is None:
                    prefix = _namespace_map.get(uri)
                    if prefix is None:
                        prefix = "ns%d" % len(namespaces)
                    if prefix != "xml":
                        namespaces[uri] = prefix
                if prefix:
                    qnames[qname] = encode("%s:%s" % (prefix, tag))
                else:
                    qnames[qname] = encode(tag) # default element
            else:
                if default_namespace:
                    # FIXME: can this be handled in XML 1.0?
                    raise ValueError(
                        "cannot use non-qualified names with "
                        "default_namespace option"
                        )
                qnames[qname] = encode(qname)
        except TypeError:
            _raise_serialization_error(qname)

    # populate qname and namespaces table
    try:
        iterate = elem.iter
    except AttributeError:
        iterate = elem.getiterator # cET compatibility
    for elem in iterate():
        tag = elem.tag
        if isinstance(tag, QName) and tag.text not in qnames:
            add_qname(tag.text)
        elif isinstance(tag, basestring):
            if tag not in qnames:
                add_qname(tag)
        elif tag is not None and tag is not Comment and tag is not PI:
            _raise_serialization_error(tag)
        for key, value in elem.items():
            if isinstance(key, QName):
                key = key.text
            if key not in qnames:
                add_qname(key)
            if isinstance(value, QName) and value.text not in qnames:
                add_qname(value.text)
        text = elem.text
        if isinstance(text, QName) and text.text not in qnames:
            add_qname(text.text)
    return qnames, namespaces

def _serialize_xml(write, elem, encoding, qnames, namespaces):
    tag = elem.tag
    text = elem.text
    if tag is Comment:
        write("<!--%s-->" % _escape_cdata(text, encoding))
    elif tag is ProcessingInstruction:
        write("<?%s?>" % _escape_cdata(text, encoding))
    else:
        tag = qnames[tag]
        if tag is None:
            if text:
                write(_escape_cdata(text, encoding))
            for e in elem:
                _serialize_xml(write, e, encoding, qnames, None)
        else:
            write("<" + tag)
            items = elem.items()
            if items or namespaces:
                items.sort() # lexical order
                for k, v in items:
                    if isinstance(k, QName):
                        k = k.text
                    if isinstance(v, QName):
                        v = qnames[v.text]
                    else:
                        v = _escape_attrib(v, encoding)
                    write(" %s=\"%s\"" % (qnames[k], v))
                if namespaces:
                    items = namespaces.items()
                    items.sort(key=lambda x: x[1]) # sort on prefix
                    for v, k in items:
                        if k:
                            k = ":" + k
                        write(" xmlns%s=\"%s\"" % (
                            k.encode(encoding),
                            _escape_attrib(v, encoding)
                            ))
            if text or len(elem):
                write(">")
                if text:
                    write(_escape_cdata(text, encoding))
                for e in elem:
                    _serialize_xml(write, e, encoding, qnames, None)
                write("</" + tag + ">")
            else:
                write(" />")
    if elem.tail:
        write(_escape_cdata(elem.tail, encoding))

HTML_EMPTY = ("area", "base", "basefont", "br", "col", "frame", "hr",
              "img", "input", "isindex", "link", "meta" "param")

try:
    HTML_EMPTY = set(HTML_EMPTY)
except NameError:
    pass

def _serialize_html(write, elem, encoding, qnames, namespaces):
    tag = elem.tag
    text = elem.text
    if tag is Comment:
        write("<!--%s-->" % _escape_cdata(text, encoding))
    elif tag is ProcessingInstruction:
        write("<?%s?>" % _escape_cdata(text, encoding))
    else:
        tag = qnames[tag]
        if tag is None:
            if text:
                write(_escape_cdata(text, encoding))
            for e in elem:
                _serialize_html(write, e, encoding, qnames, None)
        else:
            write("<" + tag)
            items = elem.items()
            if items or namespaces:
                items.sort() # lexical order
                for k, v in items:
                    if isinstance(k, QName):
                        k = k.text
                    if isinstance(v, QName):
                        v = qnames[v.text]
                    else:
                        v = _escape_attrib_html(v, encoding)
                    # FIXME: handle boolean attributes
                    write(" %s=\"%s\"" % (qnames[k], v))
                if namespaces:
                    items = namespaces.items()
                    items.sort(key=lambda x: x[1]) # sort on prefix
                    for v, k in items:
                        if k:
                            k = ":" + k
                        write(" xmlns%s=\"%s\"" % (
                            k.encode(encoding),
                            _escape_attrib(v, encoding)
                            ))
            write(">")
            tag = tag.lower()
            if text:
                if tag == "script" or tag == "style":
                    write(_encode(text, encoding))
                else:
                    write(_escape_cdata(text, encoding))
            for e in elem:
                _serialize_html(write, e, encoding, qnames, None)
            if tag not in HTML_EMPTY:
                write("</" + tag + ">")
    if elem.tail:
        write(_escape_cdata(elem.tail, encoding))

def _serialize_text(write, elem, encoding):
    for part in elem.itertext():
        write(part.encode(encoding))
    if elem.tail:
        write(elem.tail.encode(encoding))

##
# Registers a namespace prefix.  The registry is global, and any
# existing mapping for either the given prefix or the namespace URI
# will be removed.
#
# @param prefix Namespace prefix.
# @param uri Namespace uri.  Tags and attributes in this namespace
#     will be serialized with the given prefix, if at all possible.
# @raise ValueError If the prefix is reserved, or is otherwise
#     invalid.

def register_namespace(prefix, uri):
    if re.match("ns\d+$", prefix):
        raise ValueError("Prefix format reserved for internal use")
    for k, v in _namespace_map.items():
        if k == uri or v == prefix:
            del _namespace_map[k]
    _namespace_map[uri] = prefix

_namespace_map = {
    # "well-known" namespace prefixes
    "http://www.w3.org/XML/1998/namespace": "xml",
    "http://www.w3.org/1999/xhtml": "html",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
    "http://schemas.xmlsoap.org/wsdl/": "wsdl",
    # xml schema
    "http://www.w3.org/2001/XMLSchema": "xs",
    "http://www.w3.org/2001/XMLSchema-instance": "xsi",
    # dublic core
    "http://purl.org/dc/elements/1.1/": "dc",
}

def _raise_serialization_error(text):
    raise TypeError(
        "cannot serialize %r (type %s)" % (text, type(text).__name__)
        )

def _encode(text, encoding):
    try:
        return text.encode(encoding, "xmlcharrefreplace")
    except (TypeError, AttributeError):
        _raise_serialization_error(text)

def _escape_cdata(text, encoding):
    # escape character data
    try:
        # it's worth avoiding do-nothing calls for strings that are
        # shorter than 500 character, or so.  assume that's, by far,
        # the most common case in most applications.
        if "&" in text:
            text = text.replace("&", "&amp;")
        if "<" in text:
            text = text.replace("<", "&lt;")
        if ">" in text:
            text = text.replace(">", "&gt;")
        return text.encode(encoding, "xmlcharrefreplace")
    except (TypeError, AttributeError):
        _raise_serialization_error(text)

def _escape_attrib(text, encoding):
    # escape attribute value
    try:
        if "&" in text:
            text = text.replace("&", "&amp;")
        if "<" in text:
            text = text.replace("<", "&lt;")
        if ">" in text:
            text = text.replace(">", "&gt;")
        if "\"" in text:
            text = text.replace("\"", "&quot;")
        if "\n" in text:
            text = text.replace("\n", "&#10;")
        return text.encode(encoding, "xmlcharrefreplace")
    except (TypeError, AttributeError):
        _raise_serialization_error(text)

def _escape_attrib_html(text, encoding):
    # escape attribute value
    try:
        if "&" in text:
            text = text.replace("&", "&amp;")
        if ">" in text:
            text = text.replace(">", "&gt;")
        if "\"" in text:
            text = text.replace("\"", "&quot;")
        return text.encode(encoding, "xmlcharrefreplace")
    except (TypeError, AttributeError):
        _raise_serialization_error(text)

# --------------------------------------------------------------------

##
# Generates a string representation of an XML element, including all
# subelements.
#
# @param element An Element instance.
# @return An encoded string containing the XML data.
# @defreturn string

def tostring(element, encoding=None, method=None):
    class dummy:
        pass
    data = []
    file = dummy()
    file.write = data.append
    ElementTree(element).write(file, encoding, method=method)
    return "".join(data)

##
# Generates a string representation of an XML element, including all
# subelements.  The string is returned as a sequence of string fragments.
#
# @param element An Element instance.
# @return A sequence object containing the XML data.
# @defreturn sequence
# @since 1.3

def tostringlist(element, encoding=None):
    class dummy:
        pass
    data = []
    file = dummy()
    file.write = data.append
    ElementTree(element).write(file, encoding)
    # FIXME: merge small fragments into larger parts
    return data

##
# Writes an element tree or element structure to sys.stdout.  This
# function should be used for debugging only.
# <p>
# The exact output format is implementation dependent.  In this
# version, it's written as an ordinary XML file.
#
# @param elem An element tree or an individual element.

def dump(elem):
    # debugging
    if not isinstance(elem, ElementTree):
        elem = ElementTree(elem)
    elem.write(sys.stdout)
    tail = elem.getroot().tail
    if not tail or tail[-1] != "\n":
        sys.stdout.write("\n")

# --------------------------------------------------------------------
# parsing

##
# Parses an XML document into an element tree.
#
# @param source A filename or file object containing XML data.
# @param parser An optional parser instance.  If not given, the
#     standard {@link XMLParser} parser is used.
# @return An ElementTree instance

def parse(source, parser=None):
    tree = ElementTree()
    tree.parse(source, parser)
    return tree

##
# Parses an XML document into an element tree incrementally, and reports
# what's going on to the user.
#
# @param source A filename or file object containing XML data.
# @param events A list of events to report back.  If omitted, only "end"
#     events are reported.
# @param parser An optional parser instance.  If not given, the
#     standard {@link XMLParser} parser is used.
# @return A (event, elem) iterator.

def iterparse(source, events=None, parser=None):
    if not hasattr(source, "read"):
        source = open(source, "rb")
    if not parser:
        parser = XMLParser(target=TreeBuilder())
    return _IterParseIterator(source, events, parser)

class _IterParseIterator(object):

    def __init__(self, source, events, parser):
        self._file = source
        self._events = []
        self._index = 0
        self.root = self._root = None
        self._parser = parser
        # wire up the parser for event reporting
        parser = self._parser._parser
        append = self._events.append
        if events is None:
            events = ["end"]
        for event in events:
            if event == "start":
                try:
                    parser.ordered_attributes = 1
                    parser.specified_attributes = 1
                    def handler(tag, attrib_in, event=event, append=append,
                                start=self._parser._start_list):
                        append((event, start(tag, attrib_in)))
                    parser.StartElementHandler = handler
                except AttributeError:
                    def handler(tag, attrib_in, event=event, append=append,
                                start=self._parser._start):
                        append((event, start(tag, attrib_in)))
                    parser.StartElementHandler = handler
            elif event == "end":
                def handler(tag, event=event, append=append,
                            end=self._parser._end):
                    append((event, end(tag)))
                parser.EndElementHandler = handler
            elif event == "start-ns":
                def handler(prefix, uri, event=event, append=append):
                    try:
                        uri = uri.encode("ascii")
                    except UnicodeError:
                        pass
                    append((event, (prefix or "", uri)))
                parser.StartNamespaceDeclHandler = handler
            elif event == "end-ns":
                def handler(prefix, event=event, append=append):
                    append((event, None))
                parser.EndNamespaceDeclHandler = handler

    def next(self):
        while 1:
            try:
                item = self._events[self._index]
            except IndexError:
                if self._parser is None:
                    self.root = self._root
                    raise StopIteration
                # load event buffer
                del self._events[:]
                self._index = 0
                data = self._file.read(16384)
                if data:
                    self._parser.feed(data)
                else:
                    self._root = self._parser.close()
                    self._parser = None
            else:
                self._index = self._index + 1
                return item

    def __iter__(self):
        return self

##
# Parses an XML document from a string constant.  This function can
# be used to embed "XML literals" in Python code.
#
# @param source A string containing XML data.
# @param parser An optional parser instance.  If not given, the
#     standard {@link XMLParser} parser is used.
# @return An Element instance.
# @defreturn Element

def XML(text, parser=None):
    if not parser:
        parser = XMLParser(target=TreeBuilder())
    parser.feed(text)
    return parser.close()

##
# Parses an XML document from a string constant, and also returns
# a dictionary which maps from element id:s to elements.
#
# @param source A string containing XML data.
# @param parser An optional parser instance.  If not given, the
#     standard {@link XMLParser} parser is used.
# @return A tuple containing an Element instance and a dictionary.
# @defreturn (Element, dictionary)

def XMLID(text, parser=None):
    if not parser:
        parser = XMLParser(target=TreeBuilder())
    parser.feed(text)
    tree = parser.close()
    ids = {}
    for elem in tree.getiterator():
        id = elem.get("id")
        if id:
            ids[id] = elem
    return tree, ids

##
# Parses an XML document from a string constant.  Same as {@link #XML}.
#
# @def fromstring(text)
# @param source A string containing XML data.
# @return An Element instance.
# @defreturn Element

fromstring = XML

##
# Parses an XML document from a sequence of string fragments.
#
# @param sequence A list or other sequence containing XML data fragments.
# @param parser An optional parser instance.  If not given, the
#     standard {@link XMLParser} parser is used.
# @return An Element instance.
# @defreturn Element
# @since 1.3

def fromstringlist(sequence, parser=None):
    if not parser:
        parser = XMLParser(target=TreeBuilder())
    for text in sequence:
        parser.feed(text)
    return parser.close()

# --------------------------------------------------------------------

##
# Generic element structure builder.  This builder converts a sequence
# of {@link #TreeBuilder.start}, {@link #TreeBuilder.data}, and {@link
# #TreeBuilder.end} method calls to a well-formed element structure.
# <p>
# You can use this class to build an element structure using a custom XML
# parser, or a parser for some other XML-like format.
#
# @param element_factory Optional element factory.  This factory
#    is called to create new Element instances, as necessary.

class TreeBuilder(object):

    def __init__(self, element_factory=None):
        self._data = [] # data collector
        self._elem = [] # element stack
        self._last = None # last element
        self._tail = None # true if we're after an end tag
        if element_factory is None:
            element_factory = Element
        self._factory = element_factory

    ##
    # Flushes the builder buffers, and returns the toplevel document
    # element.
    #
    # @return An Element instance.
    # @defreturn Element

    def close(self):
        assert len(self._elem) == 0, "missing end tags"
        assert self._last != None, "missing toplevel element"
        return self._last

    def _flush(self):
        if self._data:
            if self._last is not None:
                text = "".join(self._data)
                if self._tail:
                    assert self._last.tail is None, "internal error (tail)"
                    self._last.tail = text
                else:
                    assert self._last.text is None, "internal error (text)"
                    self._last.text = text
            self._data = []

    ##
    # Adds text to the current element.
    #
    # @param data A string.  This should be either an 8-bit string
    #    containing ASCII text, or a Unicode string.

    def data(self, data):
        self._data.append(data)

    ##
    # Opens a new element.
    #
    # @param tag The element name.
    # @param attrib A dictionary containing element attributes.
    # @return The opened element.
    # @defreturn Element

    def start(self, tag, attrs):
        self._flush()
        self._last = elem = self._factory(tag, attrs)
        if self._elem:
            self._elem[-1].append(elem)
        self._elem.append(elem)
        self._tail = 0
        return elem

    ##
    # Closes the current element.
    #
    # @param tag The element name.
    # @return The closed element.
    # @defreturn Element

    def end(self, tag):
        self._flush()
        self._last = self._elem.pop()
        assert self._last.tag == tag,\
               "end tag mismatch (expected %s, got %s)" % (
                   self._last.tag, tag)
        self._tail = 1
        return self._last

##
# Element structure builder for XML source data, based on the
# <b>expat</b> parser.
#
# @keyparam target Target object.  If omitted, the builder uses an
#     instance of the standard {@link #TreeBuilder} class.
# @keyparam html Predefine HTML entities.  This flag is not supported
#     by the current implementation.
# @keyparam encoding Optional encoding.  If given, the value overrides
#     the encoding specified in the XML file.
# @see #ElementTree
# @see #TreeBuilder

class XMLParser(object):

    def __init__(self, html=0, target=None, encoding=None):
        try:
            from xml.parsers import expat
        except ImportError:
            try:
                import pyexpat; expat = pyexpat
            except ImportError:
                raise ImportError(
                    "No module named expat; use SimpleXMLTreeBuilder instead"
                    )
        parser = expat.ParserCreate(encoding, "}")
        if target is None:
            target = TreeBuilder()
        # underscored names are provided for compatibility only
        self.parser = self._parser = parser
        self.target = self._target = target
        self._error = expat.error
        self._names = {} # name memo cache
        # callbacks
        parser.DefaultHandlerExpand = self._default
        parser.StartElementHandler = self._start
        parser.EndElementHandler = self._end
        parser.CharacterDataHandler = self._data
        # let expat do the buffering, if supported
        try:
            self._parser.buffer_text = 1
        except AttributeError:
            pass
        # use new-style attribute handling, if supported
        try:
            self._parser.ordered_attributes = 1
            self._parser.specified_attributes = 1
            parser.StartElementHandler = self._start_list
        except AttributeError:
            pass
        self._doctype = None
        self.entity = {}
        try:
            self.version = "Expat %d.%d.%d" % expat.version_info
        except AttributeError:
            pass # unknown

    def _raiseerror(self, value):
        err = ParseError(value)
        err.code = value.code
        err.position = value.lineno, value.offset
        raise err

    def _fixtext(self, text):
        # convert text string to ascii, if possible
        try:
            return text.encode("ascii")
        except UnicodeError:
            return text

    def _fixname(self, key):
        # expand qname, and convert name string to ascii, if possible
        try:
            name = self._names[key]
        except KeyError:
            name = key
            if "}" in name:
                name = "{" + name
            self._names[key] = name = self._fixtext(name)
        return name

    def _start(self, tag, attrib_in):
        fixname = self._fixname
        fixtext = self._fixtext
        tag = fixname(tag)
        attrib = {}
        for key, value in attrib_in.items():
            attrib[fixname(key)] = fixtext(value)
        return self.target.start(tag, attrib)

    def _start_list(self, tag, attrib_in):
        fixname = self._fixname
        fixtext = self._fixtext
        tag = fixname(tag)
        attrib = {}
        if attrib_in:
            for i in range(0, len(attrib_in), 2):
                attrib[fixname(attrib_in[i])] = fixtext(attrib_in[i+1])
        return self.target.start(tag, attrib)

    def _data(self, text):
        return self.target.data(self._fixtext(text))

    def _end(self, tag):
        return self.target.end(self._fixname(tag))

    def _default(self, text):
        prefix = text[:1]
        if prefix == "&":
            # deal with undefined entities
            try:
                self.target.data(self.entity[text[1:-1]])
            except KeyError:
                from xml.parsers import expat
                err = expat.error(
                    "undefined entity %s: line %d, column %d" %
                    (text, self._parser.ErrorLineNumber,
                    self._parser.ErrorColumnNumber)
                    )
                err.code = 11 # XML_ERROR_UNDEFINED_ENTITY
                err.lineno = self._parser.ErrorLineNumber
                err.offset = self._parser.ErrorColumnNumber
                raise err
        elif prefix == "<" and text[:9] == "<!DOCTYPE":
            self._doctype = [] # inside a doctype declaration
        elif self._doctype is not None:
            # parse doctype contents
            if prefix == ">":
                self._doctype = None
                return
            text = text.strip()
            if not text:
                return
            self._doctype.append(text)
            n = len(self._doctype)
            if n > 2:
                type = self._doctype[1]
                if type == "PUBLIC" and n == 4:
                    name, type, pubid, system = self._doctype
                elif type == "SYSTEM" and n == 3:
                    name, type, system = self._doctype
                    pubid = None
                else:
                    return
                if pubid:
                    pubid = pubid[1:-1]
                if hasattr(self.target, "doctype"):
                    self.target.doctype(name, pubid, system[1:-1])
                self._doctype = None

    ##
    # Feeds data to the parser.
    #
    # @param data Encoded data.

    def feed(self, data):
        try:
            self._parser.Parse(data, 0)
        except self._error, v:
            self._raiseerror(v)

    ##
    # Finishes feeding data to the parser.
    #
    # @return An element structure.
    # @defreturn Element

    def close(self):
        try:
            self._parser.Parse("", 1) # end of data
        except self._error, v:
            self._raiseerror(v)
        tree = self.target.close()
        del self.target, self._parser # get rid of circular references
        return tree

# compatibility
XMLTreeBuilder = XMLParser

########NEW FILE########
__FILENAME__ = HTMLTreeBuilder
#
# ElementTree
# $Id: HTMLTreeBuilder.py 3265 2007-09-06 20:42:00Z fredrik $
#
# a simple tree builder, for HTML input
#
# history:
# 2002-04-06 fl   created
# 2002-04-07 fl   ignore IMG and HR end tags
# 2002-04-07 fl   added support for 1.5.2 and later
# 2003-04-13 fl   added HTMLTreeBuilder alias
# 2004-12-02 fl   don't feed non-ASCII charrefs/entities as 8-bit strings
# 2004-12-05 fl   don't feed non-ASCII CDATA as 8-bit strings
#
# Copyright (c) 1999-2004 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2007 by Fredrik Lundh
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

##
# Tools to build element trees from HTML files.
##

import htmlentitydefs
import re, string, sys
import mimetools, StringIO

import ElementTree

AUTOCLOSE = "p", "li", "tr", "th", "td", "head", "body"
IGNOREEND = "img", "hr", "meta", "link", "br"

if sys.version[:3] == "1.5":
    is_not_ascii = re.compile(r"[\x80-\xff]").search # 1.5.2
else:
    is_not_ascii = re.compile(eval(r'u"[\u0080-\uffff]"')).search

try:
    from HTMLParser import HTMLParser
except ImportError:
    from sgmllib import SGMLParser
    # hack to use sgmllib's SGMLParser to emulate 2.2's HTMLParser
    class HTMLParser(SGMLParser):
        # the following only works as long as this class doesn't
        # provide any do, start, or end handlers
        def unknown_starttag(self, tag, attrs):
            self.handle_starttag(tag, attrs)
        def unknown_endtag(self, tag):
            self.handle_endtag(tag)

##
# ElementTree builder for HTML source code.  This builder converts an
# HTML document or fragment to an ElementTree.
# <p>
# The parser is relatively picky, and requires balanced tags for most
# elements.  However, elements belonging to the following group are
# automatically closed: P, LI, TR, TH, and TD.  In addition, the
# parser automatically inserts end tags immediately after the start
# tag, and ignores any end tags for the following group: IMG, HR,
# META, and LINK.
#
# @keyparam builder Optional builder object.  If omitted, the parser
#     uses the standard <b>elementtree</b> builder.
# @keyparam encoding Optional character encoding, if known.  If omitted,
#     the parser looks for META tags inside the document.  If no tags
#     are found, the parser defaults to ISO-8859-1.  Note that if your
#     document uses a non-ASCII compatible encoding, you must decode
#     the document before parsing.
#
# @see elementtree.ElementTree

class HTMLTreeBuilder(HTMLParser):

    # FIXME: shouldn't this class be named Parser, not Builder?

    def __init__(self, builder=None, encoding=None):
        self.__stack = []
        if builder is None:
            builder = ElementTree.TreeBuilder()
        self.__builder = builder
        self.encoding = encoding or "iso-8859-1"
        HTMLParser.__init__(self)

    ##
    # Flushes parser buffers, and return the root element.
    #
    # @return An Element instance.

    def close(self):
        HTMLParser.close(self)
        return self.__builder.close()

    ##
    # (Internal) Handles start tags.

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            # look for encoding directives
            http_equiv = content = None
            for k, v in attrs:
                if k == "http-equiv":
                    http_equiv = string.lower(v)
                elif k == "content":
                    content = v
            if http_equiv == "content-type" and content:
                # use mimetools to parse the http header
                header = mimetools.Message(
                    StringIO.StringIO("%s: %s\n\n" % (http_equiv, content))
                    )
                encoding = header.getparam("charset")
                if encoding:
                    self.encoding = encoding
        if tag in AUTOCLOSE:
            if self.__stack and self.__stack[-1] == tag:
                self.handle_endtag(tag)
        self.__stack.append(tag)
        attrib = {}
        if attrs:
            for k, v in attrs:
                attrib[string.lower(k)] = v
        self.__builder.start(tag, attrib)
        if tag in IGNOREEND:
            self.__stack.pop()
            self.__builder.end(tag)

    ##
    # (Internal) Handles end tags.

    def handle_endtag(self, tag):
        if tag in IGNOREEND:
            return
        lasttag = self.__stack.pop()
        if tag != lasttag and lasttag in AUTOCLOSE:
            self.handle_endtag(lasttag)
        self.__builder.end(tag)

    ##
    # (Internal) Handles character references.

    def handle_charref(self, char):
        if char[:1] == "x":
            char = int(char[1:], 16)
        else:
            char = int(char)
        if 0 <= char < 128:
            self.__builder.data(chr(char))
        else:
            self.__builder.data(unichr(char))

    ##
    # (Internal) Handles entity references.

    def handle_entityref(self, name):
        entity = htmlentitydefs.entitydefs.get(name)
        if entity:
            if len(entity) == 1:
                entity = ord(entity)
            else:
                entity = int(entity[2:-1])
            if 0 <= entity < 128:
                self.__builder.data(chr(entity))
            else:
                self.__builder.data(unichr(entity))
        else:
            self.unknown_entityref(name)

    ##
    # (Internal) Handles character data.

    def handle_data(self, data):
        if isinstance(data, type('')) and is_not_ascii(data):
            # convert to unicode, but only if necessary
            data = unicode(data, self.encoding, "ignore")
        self.__builder.data(data)

    ##
    # (Hook) Handles unknown entity references.  The default action
    # is to ignore unknown entities.

    def unknown_entityref(self, name):
        pass # ignore by default; override if necessary

##
# An alias for the <b>HTMLTreeBuilder</b> class.

TreeBuilder = HTMLTreeBuilder

##
# Parse an HTML document or document fragment.
#
# @param source A filename or file object containing HTML data.
# @param encoding Optional character encoding, if known.  If omitted,
#     the parser looks for META tags inside the document.  If no tags
#     are found, the parser defaults to ISO-8859-1.
# @return An ElementTree instance

def parse(source, encoding=None):
    return ElementTree.parse(source, HTMLTreeBuilder(encoding=encoding))

if __name__ == "__main__":
    import sys
    ElementTree.dump(parse(open(sys.argv[1])))

########NEW FILE########
__FILENAME__ = SgmlopXMLTreeBuilder
#
# ElementTree
# $Id$
#
# A simple XML tree builder, based on the sgmlop library.
#
# Note that this version does not support namespaces.  This may be
# changed in future versions.
#
# history:
# 2004-03-28 fl   created
#
# Copyright (c) 1999-2004 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2004 by Fredrik Lundh
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

##
# Tools to build element trees from XML, based on the SGMLOP parser.
# <p>
# The current version does not support XML namespaces.
# <p>
# This tree builder requires the <b>sgmlop</b> extension module
# (available from
# <a href='http://effbot.org/downloads'>http://effbot.org/downloads</a>).
##

import ElementTree

##
# ElementTree builder for XML source data, based on the SGMLOP parser.
#
# @see elementtree.ElementTree

class TreeBuilder:

    def __init__(self, html=0):
        try:
            import sgmlop
        except ImportError:
            raise RuntimeError("sgmlop parser not available")
        self.__builder = ElementTree.TreeBuilder()
        if html:
            import htmlentitydefs
            self.entitydefs.update(htmlentitydefs.entitydefs)
        self.__parser = sgmlop.XMLParser()
        self.__parser.register(self)

    ##
    # Feeds data to the parser.
    #
    # @param data Encoded data.

    def feed(self, data):
        self.__parser.feed(data)

    ##
    # Finishes feeding data to the parser.
    #
    # @return An element structure.
    # @defreturn Element

    def close(self):
        self.__parser.close()
        self.__parser = None
        return self.__builder.close()

    def finish_starttag(self, tag, attrib):
        self.__builder.start(tag, attrib)

    def finish_endtag(self, tag):
        self.__builder.end(tag)

    def handle_data(self, data):
        self.__builder.data(data)

########NEW FILE########
__FILENAME__ = SimpleXMLTreeBuilder
#
# ElementTree
# $Id: SimpleXMLTreeBuilder.py 1862 2004-06-18 07:31:02Z Fredrik $
#
# A simple XML tree builder, based on Python's xmllib
#
# Note that due to bugs in xmllib, this builder does not fully support
# namespaces (unqualified attributes are put in the default namespace,
# instead of being left as is).  Run this module as a script to find
# out if this affects your Python version.
#
# history:
# 2001-10-20 fl   created
# 2002-05-01 fl   added namespace support for xmllib
# 2002-08-17 fl   added xmllib sanity test
#
# Copyright (c) 1999-2004 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2004 by Fredrik Lundh
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

##
# Tools to build element trees from XML files, using <b>xmllib</b>.
# This module can be used instead of the standard tree builder, for
# Python versions where "expat" is not available (such as 1.5.2).
# <p>
# Note that due to bugs in <b>xmllib</b>, the namespace support is
# not reliable (you can run the module as a script to find out exactly
# how unreliable it is on your Python version).
##

import xmllib, string

import ElementTree

##
# ElementTree builder for XML source data.
#
# @see elementtree.ElementTree

class TreeBuilder(xmllib.XMLParser):

    def __init__(self, html=0):
        self.__builder = ElementTree.TreeBuilder()
        if html:
            import htmlentitydefs
            self.entitydefs.update(htmlentitydefs.entitydefs)
        xmllib.XMLParser.__init__(self)

    ##
    # Feeds data to the parser.
    #
    # @param data Encoded data.

    def feed(self, data):
        xmllib.XMLParser.feed(self, data)

    ##
    # Finishes feeding data to the parser.
    #
    # @return An element structure.
    # @defreturn Element

    def close(self):
        xmllib.XMLParser.close(self)
        return self.__builder.close()

    def handle_data(self, data):
        self.__builder.data(data)

    handle_cdata = handle_data

    def unknown_starttag(self, tag, attrs):
        attrib = {}
        for key, value in attrs.items():
            attrib[fixname(key)] = value
        self.__builder.start(fixname(tag), attrib)

    def unknown_endtag(self, tag):
        self.__builder.end(fixname(tag))


def fixname(name, split=string.split):
    # xmllib in 2.0 and later provides limited (and slightly broken)
    # support for XML namespaces.
    if " " not in name:
        return name
    return "{%s}%s" % tuple(split(name, " ", 1))


if __name__ == "__main__":
    import sys
    # sanity check: look for known namespace bugs in xmllib
    p = TreeBuilder()
    text = """\
    <root xmlns='default'>
       <tag attribute='value' />
    </root>
    """
    p.feed(text)
    tree = p.close()
    status = []
    # check for bugs in the xmllib implementation
    tag = tree.find("{default}tag")
    if tag is None:
        status.append("namespaces not supported")
    if tag is not None and tag.get("{default}attribute"):
        status.append("default namespace applied to unqualified attribute")
    # report bugs
    if status:
        print "xmllib doesn't work properly in this Python version:"
        for bug in status:
            print "-", bug
    else:
        print "congratulations; no problems found in xmllib"


########NEW FILE########
__FILENAME__ = SimpleXMLWriter
#
# SimpleXMLWriter
# $Id: SimpleXMLWriter.py 3265 2007-09-06 20:42:00Z fredrik $
#
# a simple XML writer
#
# history:
# 2001-12-28 fl   created
# 2002-11-25 fl   fixed attribute encoding
# 2002-12-02 fl   minor fixes for 1.5.2
# 2004-06-17 fl   added pythondoc markup
# 2004-07-23 fl   added flush method (from Jay Graves)
# 2004-10-03 fl   added declaration method
#
# Copyright (c) 2001-2004 by Fredrik Lundh
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The SimpleXMLWriter module is
#
# Copyright (c) 2001-2004 by Fredrik Lundh
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

##
# Tools to write XML files, without having to deal with encoding
# issues, well-formedness, etc.
# <p>
# The current version does not provide built-in support for
# namespaces. To create files using namespaces, you have to provide
# "xmlns" attributes and explicitly add prefixes to tags and
# attributes.
#
# <h3>Patterns</h3>
#
# The following example generates a small XHTML document.
# <pre>
#
# from elementtree.SimpleXMLWriter import XMLWriter
# import sys
#
# w = XMLWriter(sys.stdout)
#
# html = w.start("html")
#
# w.start("head")
# w.element("title", "my document")
# w.element("meta", name="generator", value="my application 1.0")
# w.end()
#
# w.start("body")
# w.element("h1", "this is a heading")
# w.element("p", "this is a paragraph")
#
# w.start("p")
# w.data("this is ")
# w.element("b", "bold")
# w.data(" and ")
# w.element("i", "italic")
# w.data(".")
# w.end("p")
#
# w.close(html)
# </pre>
##

import re, sys, string

try:
    unicode("")
except NameError:
    def encode(s, encoding):
        # 1.5.2: application must use the right encoding
        return s
    _escape = re.compile(r"[&<>\"\x80-\xff]+") # 1.5.2
else:
    def encode(s, encoding):
        return s.encode(encoding)
    _escape = re.compile(eval(r'u"[&<>\"\u0080-\uffff]+"'))

def encode_entity(text, pattern=_escape):
    # map reserved and non-ascii characters to numerical entities
    def escape_entities(m):
        out = []
        for char in m.group():
            out.append("&#%d;" % ord(char))
        return string.join(out, "")
    return encode(pattern.sub(escape_entities, text), "ascii")

del _escape

#
# the following functions assume an ascii-compatible encoding
# (or "utf-16")

def escape_cdata(s, encoding=None, replace=string.replace):
    s = replace(s, "&", "&amp;")
    s = replace(s, "<", "&lt;")
    s = replace(s, ">", "&gt;")
    if encoding:
        try:
            return encode(s, encoding)
        except UnicodeError:
            return encode_entity(s)
    return s

def escape_attrib(s, encoding=None, replace=string.replace):
    s = replace(s, "&", "&amp;")
    s = replace(s, "'", "&apos;")
    s = replace(s, "\"", "&quot;")
    s = replace(s, "<", "&lt;")
    s = replace(s, ">", "&gt;")
    if encoding:
        try:
            return encode(s, encoding)
        except UnicodeError:
            return encode_entity(s)
    return s

##
# XML writer class.
#
# @param file A file or file-like object.  This object must implement
#    a <b>write</b> method that takes an 8-bit string.
# @param encoding Optional encoding.

class XMLWriter:

    def __init__(self, file, encoding="us-ascii"):
        if not hasattr(file, "write"):
            file = open(file, "w")
        self.__write = file.write
        if hasattr(file, "flush"):
            self.flush = file.flush
        self.__open = 0 # true if start tag is open
        self.__tags = []
        self.__data = []
        self.__encoding = encoding

    def __flush(self):
        # flush internal buffers
        if self.__open:
            self.__write(">")
            self.__open = 0
        if self.__data:
            data = string.join(self.__data, "")
            self.__write(escape_cdata(data, self.__encoding))
            self.__data = []

    ##
    # Writes an XML declaration.

    def declaration(self):
        encoding = self.__encoding
        if encoding == "us-ascii" or encoding == "utf-8":
            self.__write("<?xml version='1.0'?>\n")
        else:
            self.__write("<?xml version='1.0' encoding='%s'?>\n" % encoding)

    ##
    # Opens a new element.  Attributes can be given as keyword
    # arguments, or as a string/string dictionary. You can pass in
    # 8-bit strings or Unicode strings; the former are assumed to use
    # the encoding passed to the constructor.  The method returns an
    # opaque identifier that can be passed to the <b>close</b> method,
    # to close all open elements up to and including this one.
    #
    # @param tag Element tag.
    # @param attrib Attribute dictionary.  Alternatively, attributes
    #    can be given as keyword arguments.
    # @return An element identifier.

    def start(self, tag, attrib={}, **extra):
        self.__flush()
        tag = escape_cdata(tag, self.__encoding)
        self.__data = []
        self.__tags.append(tag)
        self.__write("<%s" % tag)
        if attrib or extra:
            attrib = attrib.copy()
            attrib.update(extra)
            attrib = attrib.items()
            attrib.sort()
            for k, v in attrib:
                k = escape_cdata(k, self.__encoding)
                v = escape_attrib(v, self.__encoding)
                self.__write(" %s=\"%s\"" % (k, v))
        self.__open = 1
        return len(self.__tags)-1

    ##
    # Adds a comment to the output stream.
    #
    # @param comment Comment text, as an 8-bit string or Unicode string.

    def comment(self, comment):
        self.__flush()
        self.__write("<!-- %s -->\n" % escape_cdata(comment, self.__encoding))

    ##
    # Adds character data to the output stream.
    #
    # @param text Character data, as an 8-bit string or Unicode string.

    def data(self, text):
        self.__data.append(text)

    ##
    # Closes the current element (opened by the most recent call to
    # <b>start</b>).
    #
    # @param tag Element tag.  If given, the tag must match the start
    #    tag.  If omitted, the current element is closed.

    def end(self, tag=None):
        if tag:
            assert self.__tags, "unbalanced end(%s)" % tag
            assert escape_cdata(tag, self.__encoding) == self.__tags[-1],\
                   "expected end(%s), got %s" % (self.__tags[-1], tag)
        else:
            assert self.__tags, "unbalanced end()"
        tag = self.__tags.pop()
        if self.__data:
            self.__flush()
        elif self.__open:
            self.__open = 0
            self.__write(" />")
            return
        self.__write("</%s>" % tag)

    ##
    # Closes open elements, up to (and including) the element identified
    # by the given identifier.
    #
    # @param id Element identifier, as returned by the <b>start</b> method.

    def close(self, id):
        while len(self.__tags) > id:
            self.end()

    ##
    # Adds an entire element.  This is the same as calling <b>start</b>,
    # <b>data</b>, and <b>end</b> in sequence. The <b>text</b> argument
    # can be omitted.

    def element(self, tag, text=None, attrib={}, **extra):
        apply(self.start, (tag, attrib), extra)
        if text:
            self.data(text)
        self.end()

    ##
    # Flushes the output stream.

    def flush(self):
        pass # replaced by the constructor

########NEW FILE########
__FILENAME__ = TidyHTMLTreeBuilder
#
# ElementTree
# $Id: TidyHTMLTreeBuilder.py 3265 2007-09-06 20:42:00Z fredrik $
#

from elementtidy.TidyHTMLTreeBuilder import *

########NEW FILE########
__FILENAME__ = TidyTools
#
# ElementTree
# $Id: TidyTools.py 3265 2007-09-06 20:42:00Z fredrik $
#
# tools to run the "tidy" command on an HTML or XHTML file, and return
# the contents as an XHTML element tree.
#
# history:
# 2002-10-19 fl   added to ElementTree library; added getzonebody function
#
# Copyright (c) 1999-2004 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#

##
# Tools to build element trees from HTML, using the external <b>tidy</b>
# utility.
##

import glob, string, os, sys

from ElementTree import ElementTree, Element

NS_XHTML = "{http://www.w3.org/1999/xhtml}"

##
# Convert an HTML or HTML-like file to XHTML, using the <b>tidy</b>
# command line utility.
#
# @param file Filename.
# @param new_inline_tags An optional list of valid but non-standard
#     inline tags.
# @return An element tree, or None if not successful.

def tidy(file, new_inline_tags=None):

    command = ["tidy", "-qn", "-asxml"]

    if new_inline_tags:
        command.append("--new-inline-tags")
        command.append(string.join(new_inline_tags, ","))

    # FIXME: support more tidy options!

    # convert
    os.system(
        "%s %s >%s.out 2>%s.err" % (string.join(command), file, file, file)
        )
    # check that the result is valid XML
    try:
        tree = ElementTree()
        tree.parse(file + ".out")
    except:
        print "*** %s:%s" % sys.exc_info()[:2]
        print ("*** %s is not valid XML "
               "(check %s.err for info)" % (file, file))
        tree = None
    else:
        if os.path.isfile(file + ".out"):
            os.remove(file + ".out")
        if os.path.isfile(file + ".err"):
            os.remove(file + ".err")

    return tree

##
# Get document body from a an HTML or HTML-like file.  This function
# uses the <b>tidy</b> function to convert HTML to XHTML, and cleans
# up the resulting XML tree.
#
# @param file Filename.
# @return A <b>body</b> element, or None if not successful.

def getbody(file, **options):
    # get clean body from text file

    # get xhtml tree
    try:
        tree = apply(tidy, (file,), options)
        if tree is None:
            return
    except IOError, v:
        print "***", v
        return None

    NS = NS_XHTML

    # remove namespace uris
    for node in tree.getiterator():
        if node.tag.startswith(NS):
            node.tag = node.tag[len(NS):]

    body = tree.getroot().find("body")

    return body

##
# Same as <b>getbody</b>, but turns plain text at the start of the
# document into an H1 tag.  This function can be used to parse zone
# documents.
#
# @param file Filename.
# @return A <b>body</b> element, or None if not successful.

def getzonebody(file, **options):

    body = getbody(file, **options)
    if body is None:
        return

    if body.text and string.strip(body.text):
        title = Element("h1")
        title.text = string.strip(body.text)
        title.tail = "\n\n"
        body.insert(0, title)

    body.text = None

    return body

if __name__ == "__main__":

    import sys
    for arg in sys.argv[1:]:
        for file in glob.glob(arg):
            print file, "...", tidy(file)

########NEW FILE########
__FILENAME__ = XMLTreeBuilder
#
# ElementTree
# $Id: XMLTreeBuilder.py 2305 2005-03-01 17:43:09Z fredrik $
#
# an XML tree builder
#
# history:
# 2001-10-20 fl   created
# 2002-05-01 fl   added namespace support for xmllib
# 2002-07-27 fl   require expat (1.5.2 code can use SimpleXMLTreeBuilder)
# 2002-08-17 fl   use tag/attribute name memo cache
# 2002-12-04 fl   moved XMLTreeBuilder to the ElementTree module
#
# Copyright (c) 1999-2004 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2004 by Fredrik Lundh
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

##
# Tools to build element trees from XML files.
##

import ElementTree

##
# (obsolete) ElementTree builder for XML source data, based on the
# <b>expat</b> parser.
# <p>
# This class is an alias for ElementTree.XMLTreeBuilder.  New code
# should use that version instead.
#
# @see elementtree.ElementTree

class TreeBuilder(ElementTree.XMLTreeBuilder):
    pass

##
# (experimental) An alternate builder that supports manipulation of
# new elements.

class FancyTreeBuilder(TreeBuilder):

    def __init__(self, html=0):
        TreeBuilder.__init__(self, html)
        self._parser.StartNamespaceDeclHandler = self._start_ns
        self._parser.EndNamespaceDeclHandler = self._end_ns
        self.namespaces = []

    def _start(self, tag, attrib_in):
        elem = TreeBuilder._start(self, tag, attrib_in)
        self.start(elem)

    def _start_list(self, tag, attrib_in):
        elem = TreeBuilder._start_list(self, tag, attrib_in)
        self.start(elem)

    def _end(self, tag):
        elem = TreeBuilder._end(self, tag)
        self.end(elem)

    def _start_ns(self, prefix, value):
        self.namespaces.insert(0, (prefix, value))

    def _end_ns(self, prefix):
        assert self.namespaces.pop(0)[0] == prefix, "implementation confused"

    ##
    # Hook method that's called when a new element has been opened.
    # May access the <b>namespaces</b> attribute.
    #
    # @param element The new element.  The tag name and attributes are,
    #     set, but it has no children, and the text and tail attributes
    #     are still empty.

    def start(self, element):
        pass

    ##
    # Hook method that's called when a new element has been closed.
    # May access the <b>namespaces</b> attribute.
    #
    # @param element The new element.

    def end(self, element):
        pass

########NEW FILE########
__FILENAME__ = injectrace
"""
Inject some tracing builtins debugging purposes.
"""
__author__ = "Martin Blais <blais@furius.ca>"

# stdlib imports
import sys, os, inspect, pprint, logging
from os import getpid
from os.path import basename


def trace(*args, **kwds):
    """
    Log the object to the 'outfile' file (keyword argument).  We also insert the
    file and line where this tracing statement was inserted.
    """
    # Get the output stream.
    outfile = kwds.pop('outfile', sys.stderr)

    if not kwds.pop('noformat', None):
        msg = _format(args, newline=kwds.pop('newline', False))
    else:
        msg = ' '.join(args)

    # Output.
    outfile.write(msg)
    outfile.flush()


def tracen(*args, **kwds):
    """
    Same as trace(), but output a new line after the trace location.

    Log the object to the 'outfile' file (keyword argument).  We also insert the
    file and line where this tracing statement was inserted.
    """
    # Get the output stream.
    outfile = kwds.pop('outfile', sys.stderr)

    msg = _format(args, newline=True)

    # Output.
    outfile.write(msg)
    outfile.flush()

def tracelog(*args):
    """
    Log the object to the 'outfile' file (keyword argument).  We also insert the
    file and line where this tracing statement was inserted.
    """
    logger = logging.getLogger()
    
    msg = _format(args)

    logger.debug(msg)

def _format(args, newline=0):
    """
    Format the arguments for printing.
    """
    # Get the parent file and line number.
    logging_method = 1
    if not logging_method:
        try:
            stk = inspect.stack()
            frame, filename, lineno, funcname, lines, idx = stk[min(2, len(stk)-1)]
        finally:
            if 'frame' in locals():
                del frame
    else:
        # Use the code from the logging module.
        filename, lineno, funcname = findCaller()

    pfx = '(TRACE [%-5d] %s:%s:%d) ' % (getpid(), basename(filename), funcname, lineno)
    if newline:
        pfx += '\n'

    # Nicely format the stuff to be traced.
    pp = pprint.PrettyPrinter(indent=4, width=70)
    msg = pfx + ', '.join(map(pp.pformat, args)) + '\n'

    return msg


def trace_enter(fun):
    "Decorator for tracing entry and exit of function."

    def wrapped(*args, **kwds):
        targs = [fun.__name__]
        if args:
            targs.append(args)
        if kwds:
            targs.append(kwds)
        trace(*targs)

        return fun(*args, **kwds)

    return wrapped
        

# Inject into builtins for debugging.
import __builtin__
__builtin__.__dict__['trace'] = trace
__builtin__.__dict__['tracen'] = tracen
__builtin__.__dict__['tracelog'] = tracelog
__builtin__.__dict__['trace_enter'] = trace_enter
__builtin__.__dict__['pprint'] = pprint.pprint
__builtin__.__dict__['pformat'] = pprint.pformat


# This is hijacked from logging.py

#
# _srcfile is used when walking the stack to check when we've got the first
# caller stack frame.
#
if hasattr(sys, 'frozen'): #support for py2exe
    _srcfile = "logging%s__init__%s" % (os.sep, __file__[-4:])
elif __file__[-4:].lower() in ['.pyc', '.pyo']:
    _srcfile = __file__[:-4] + '.py'
else:
    _srcfile = __file__
_srcfile = os.path.normcase(_srcfile)

# next bit filched from 1.5.2's inspect.py
def currentframe():
    """Return the frame object for the caller's stack frame."""
    try:
        raise Exception
    except:
        return sys.exc_traceback.tb_frame.f_back

if hasattr(sys, '_getframe'): currentframe = sys._getframe
# done filching

def findCaller():
    """
    Find the stack frame of the caller so that we can note the source
    file name, line number and function name.
    """
    f = currentframe().f_back
    rv = "(unknown file)", 0, "(unknown function)"
    while hasattr(f, "f_code"):
        co = f.f_code
        filename = os.path.normcase(co.co_filename)
        if filename == _srcfile:
            f = f.f_back
            continue
        rv = (filename, f.f_lineno, co.co_name)
        break
    return rv



########NEW FILE########
__FILENAME__ = termctrl
"(From the ASPN Cookbook.)"

import sys, re

class TerminalController:
    """
    A class that can be used to portably generate formatted output to
    a terminal.  
    
    `TerminalController` defines a set of instance variables whose
    values are initialized to the control sequence necessary to
    perform a given action.  These can be simply included in normal
    output to the terminal:

        >>> term = TerminalController()
        >>> print 'This is '+term.GREEN+'green'+term.NORMAL

    Alternatively, the `render()` method can used, which replaces
    '${action}' with the string required to perform 'action':

        >>> term = TerminalController()
        >>> print term.render('This is ${GREEN}green${NORMAL}')

    If the terminal doesn't support a given action, then the value of
    the corresponding instance variable will be set to ''.  As a
    result, the above code will still work on terminals that do not
    support color, except that their output will not be colored.
    Also, this means that you can test whether the terminal supports a
    given action by simply testing the truth value of the
    corresponding instance variable:

        >>> term = TerminalController()
        >>> if term.CLEAR_SCREEN:
        ...     print 'This terminal supports clearning the screen.'

    Finally, if the width and height of the terminal are known, then
    they will be stored in the `COLS` and `LINES` attributes.
    """
    # Cursor movement:
    BOL = ''             #: Move the cursor to the beginning of the line
    UP = ''              #: Move the cursor up one line
    DOWN = ''            #: Move the cursor down one line
    LEFT = ''            #: Move the cursor left one char
    RIGHT = ''           #: Move the cursor right one char

    # Deletion:
    CLEAR_SCREEN = ''    #: Clear the screen and move to home position
    CLEAR_EOL = ''       #: Clear to the end of the line.
    CLEAR_BOL = ''       #: Clear to the beginning of the line.
    CLEAR_EOS = ''       #: Clear to the end of the screen

    # Output modes:
    BOLD = ''            #: Turn on bold mode
    BLINK = ''           #: Turn on blink mode
    DIM = ''             #: Turn on half-bright mode
    REVERSE = ''         #: Turn on reverse-video mode
    NORMAL = ''          #: Turn off all modes

    # Cursor display:
    HIDE_CURSOR = ''     #: Make the cursor invisible
    SHOW_CURSOR = ''     #: Make the cursor visible

    # Terminal size:
    COLS = None          #: Width of the terminal (None for unknown)
    LINES = None         #: Height of the terminal (None for unknown)

    # Foreground colors:
    BLACK = BLUE = GREEN = CYAN = RED = MAGENTA = YELLOW = WHITE = ''
    
    # Background colors:
    BG_BLACK = BG_BLUE = BG_GREEN = BG_CYAN = ''
    BG_RED = BG_MAGENTA = BG_YELLOW = BG_WHITE = ''
    
    _STRING_CAPABILITIES = """
    BOL=cr UP=cuu1 DOWN=cud1 LEFT=cub1 RIGHT=cuf1
    CLEAR_SCREEN=clear CLEAR_EOL=el CLEAR_BOL=el1 CLEAR_EOS=ed BOLD=bold
    BLINK=blink DIM=dim REVERSE=rev UNDERLINE=smul NORMAL=sgr0
    HIDE_CURSOR=cinvis SHOW_CURSOR=cnorm""".split()
    _COLORS = """BLACK BLUE GREEN CYAN RED MAGENTA YELLOW WHITE""".split()
    _ANSICOLORS = "BLACK RED GREEN YELLOW BLUE MAGENTA CYAN WHITE".split()

    def __init__(self, term_stream=sys.stdout):
        """
        Create a `TerminalController` and initialize its attributes
        with appropriate values for the current terminal.
        `term_stream` is the stream that will be used for terminal
        output; if this stream is not a tty, then the terminal is
        assumed to be a dumb terminal (i.e., have no capabilities).
        """
        # Curses isn't available on all platforms
        try: import curses
        except: return

        # If the stream isn't a tty, then assume it has no capabilities.
        if not term_stream.isatty(): return

        # Check the terminal type.  If we fail, then assume that the
        # terminal has no capabilities.
        try: curses.setupterm()
        except: return

        # Look up numeric capabilities.
        self.COLS = curses.tigetnum('cols')
        self.LINES = curses.tigetnum('lines')
        
        # Look up string capabilities.
        for capability in self._STRING_CAPABILITIES:
            (attrib, cap_name) = capability.split('=')
            setattr(self, attrib, self._tigetstr(cap_name) or '')

        # Colors
        set_fg = self._tigetstr('setf')
        if set_fg:
            for i,color in zip(range(len(self._COLORS)), self._COLORS):
                setattr(self, color, curses.tparm(set_fg, i) or '')
        set_fg_ansi = self._tigetstr('setaf')
        if set_fg_ansi:
            for i,color in zip(range(len(self._ANSICOLORS)), self._ANSICOLORS):
                setattr(self, color, curses.tparm(set_fg_ansi, i) or '')
        set_bg = self._tigetstr('setb')
        if set_bg:
            for i,color in zip(range(len(self._COLORS)), self._COLORS):
                setattr(self, 'BG_'+color, curses.tparm(set_bg, i) or '')
        set_bg_ansi = self._tigetstr('setab')
        if set_bg_ansi:
            for i,color in zip(range(len(self._ANSICOLORS)), self._ANSICOLORS):
                setattr(self, 'BG_'+color, curses.tparm(set_bg_ansi, i) or '')

    def _tigetstr(self, cap_name):
        # String capabilities can include "delays" of the form "$<2>".
        # For any modern terminal, we should be able to just ignore
        # these, so strip them out.
        import curses
        cap = curses.tigetstr(cap_name) or ''
        return re.sub(r'\$<\d+>[/*]?', '', cap)

    def render(self, template):
        """
        Replace each $-substitutions in the given template string with
        the corresponding terminal control string (if it's defined) or
        '' (if it's not).
        """
        return re.sub(r'\$\$|\${\w+}', self._render_sub, template)

    def _render_sub(self, match):
        s = match.group()
        if s == '$$': return s
        else: return getattr(self, s[2:-1])

#######################################################################
# Example use case: progress bar
#######################################################################

class ProgressBar:
    """
    A 3-line progress bar, which looks like::
    
                                Header
        20% [===========----------------------------------]
                           progress message

    The progress bar is colored, if the terminal supports color
    output; and adjusts to the width of the terminal.
    """
    BAR = '%3d%% ${GREEN}[${BOLD}%s%s${NORMAL}${GREEN}]${NORMAL}\n'
    HEADER = '${BOLD}${CYAN}%s${NORMAL}\n\n'
        
    def __init__(self, term, header):
        self.term = term
        if not (self.term.CLEAR_EOL and self.term.UP and self.term.BOL):
            raise ValueError("Terminal isn't capable enough -- you "
                             "should use a simpler progress dispaly.")
        self.width = self.term.COLS or 75
        self.bar = term.render(self.BAR)
        self.header = self.term.render(self.HEADER % header.center(self.width))
        self.cleared = 1 #: true if we haven't drawn the bar yet.
        self.update(0, '')

    def update(self, percent, message):
        if self.cleared:
            sys.stdout.write(self.header)
            self.cleared = 0
        n = int((self.width-10)*percent)
        sys.stdout.write(
            self.term.BOL + self.term.UP + self.term.CLEAR_EOL +
            (self.bar % (100*percent, '='*n, '-'*(self.width-10-n))) +
            self.term.CLEAR_EOL + message.center(self.width))

    def clear(self):
        if not self.cleared:
            sys.stdout.write(self.term.BOL + self.term.CLEAR_EOL +
                             self.term.UP + self.term.CLEAR_EOL +
                             self.term.UP + self.term.CLEAR_EOL)
            self.cleared = 1



########NEW FILE########
__FILENAME__ = xmlout
"""
An XML tree building library for output, much simpler than htmlout, and more
efficient, built on top of ElementTree.

This module adds some niceties from the htmlout module to the tree serialization
capabilities of ElementTree, and is much more efficient than htmlout.
"""

# stdlib imports
import types
from StringIO import StringIO

# elementtree/lxml imports
## from lxml import etree
## from lxml.etree import Element
from elementtree.ElementTree import Element, ElementTree, iselement
from elementtree.ElementTree import _serialize_xml
from elementtree import ElementTree as ElementTreeModule 


class Base(Element):
    "Our base element."

    def __init__(self, *children, **attribs):
        if attribs:
            attribs = translate_attribs(attribs)
        Element.__init__(self, self.__class__.__name__.lower(), attribs)

        self.extend(children)

    def add(self, *children):
        return self.extend(children)

    def extend(self, children):
        "A more flexible version of extend."

        children = flatten_recursive(children)
        if children:
            for child in children:
                # Add child element.
                if isinstance(child, Base):
                    assert iselement(child), child
                    self.append(child)
                    
                # Add string.
                elif isinstance(child, (str, unicode)):
                    if not self._children:
                        if not self.text:
                            self.text = ''
                        self.text += child
                    else:
                        lchild = self._children[-1]
                        if not lchild.tail:
                            lchild.tail = ''
                        lchild.tail += child

                else:
                    raise ValueError("Invalid child type: %s" % type(child))

            return child # Return the last child.


def flatten_recursive(s, f=None):
    """ Flattens a recursive structure of lists and tuples into a simple list."""
    if f is None:
        f = []
    for c in s:
        if isinstance(c, (list, tuple)):
            flatten_recursive(c, f)
        else:
            f.append(c)
    return f


_attribute_trans_tbl = {
    'class_': 'class',
    '_class': 'class',
    'class': 'class',
    'CLASS': 'class',
    'Class': 'class',
    'Klass': 'class',
    'klass': 'class',
    '_id': 'id',
    'id_': 'id',
    'ID': 'id',
    'Id': 'id',
    }

_attribute_translate = _attribute_trans_tbl.get

def translate_attribs(attribs):
    """ Given a dict of attributes, apply a translation table on the attribute
    names. This is made to support specifying classes directly."""
    return dict((_attribute_translate(k, k), v) for k, v in attribs.iteritems())

def tostring(node, *args, **kwds):
    if 'pretty' in kwds or 'pretty_print' in kwds:
        if 'pretty' in kwds: del kwds['pretty']
        if 'pretty_print' in kwds: del kwds['pretty_print']
        indent(node)
    return ElementTree(node).write(*args, **kwds)

# From: http://effbot.org/zone/element-lib.htm#prettyprint
# indent: Adds whitespace to the tree, so that saving it as usual results in a
# prettyprinted tree.
#
# FIXME: This is not going to work if we're sharing nodes (if we have a DAG).
def indent(elem, level=0):
    "in-place prettyprint formatter"
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i



def init(cls):
    allnames = """
     html head body frameset base isindex link meta script style title address
     blockquote center del div h1 h2 h3 h4 h5 h6 hr ins isindex noscript p pre dir
     dl dt dd li menu ol ul table caption colgroup col thead tfoot tbody tr td th
     form button fieldset legend input label select optgroup option textarea a
     applet basefont bdo br font iframe img map area bject param q script span sub
     sup abbr acronym cite code del dfn em ins kbd samp strong var b big i s small
     strike tt u frameset frame noframes noop
    """
    clsdict = {}
    for k in map(str.strip, allnames.split()):
        clsdict[k.upper()] = type(k, (cls,), {})
    return clsdict

clsdict = init(Base)
__all__ = ['tostring'] + clsdict.keys()
globals().update(clsdict)




"""
Implement caching of render results by monkey-patching the serialize functions
from the ElementTree module.
"""

def _serialize_xml_cached(write, elem, encoding, qnames, namespaces):
    if hasattr(elem, 'cache'):
        rendered = elem.cache
        if not isinstance(rendered, (str, unicode)):
            sio = StringIO()
            _serialize_xml(sio.write, elem, encoding, qnames, namespaces)
            rendered = sio.getvalue()
            elem.cache = rendered
        else:
            rendered = '<!-- cached -->' + rendered
        write(rendered)
    else:
        _serialize_xml(write, elem, encoding, qnames, namespaces)

ElementTreeModule._serialize_xml = _serialize_xml_cached

########NEW FILE########
__FILENAME__ = inventory
"""
Trade inventory.

This module provides a very flexible inventory object, used to maintain position
and to calculate P+L for a positions, for a single product. In order to compute
P+L, we need to book current trades with past trades, and our inventory object
supports various booking methods to select which positions get booked (FIFO,
LIFO, custom), and a few ways to price the booked positions (real, average
cost). It can also support manual booking of specific trades, in case an
external booking algorithm already takes place.

Note that to avoid precision errors, all prices are expressed as integers scaled
to 10^8.

(We have intended to make this object as flexible as possible, because this is a
generic problem that tends to be badly solved in the financial industry with
error-prone and confusing calculations, and can easily be solved once and for
all.)
"""

# stdlib imports
from collections import deque
from decimal import Decimal

__all__ = ('Inventory', 'FIFOInventory', 'LIFOInventory', 'AvgInventory',
           'BOOKING_FIFO', 'BOOKING_LIFO', 'BOOKING_NONE',
           'PRICING_REAL', 'PRICING_AVERAGE')



class Position(object):
    """ A position that we're holding. Its size represents the remaining size,
    and not the original trade size."""

    def __init__(self, inv, price, size, obj=None):

        # The inventory that this position is attached to. (Note that this is
        # only necessary to access the integer representation converters.)
        self.inv = inv

        # The original price paid for the position.
        self.price = price

        # The current/remaining size of that position.
        self.size = size

        # An trade object that represents a psition (it can be any type of your
        # choosing). These objects are returned when matched and/or removed.
        self.obj = obj

    def __str__(self):
        S = self.inv.S
        if self.obj is not None:
            return '%s @ %s : %s' % (self.size, S(self.price), self.obj)
        else:
            return '%s @ %s' % (self.size, S(self.price))

    def cost(self):
        return self.price * self.size


# Booking methods.
def BOOKING_FIFO(inv):
    "Return the next trade for FIFO booking."
    return inv.positions[0]

def BOOKING_LIFO(inv):
    "Return the next trade for LIFO booking."
    return inv.positions[-1]

def BOOKING_NONE(inv):
    "Prevent from using automatic booking."
    raise IndexError("Automatic booking is disabled. "
                     "You need to close your trades manually.")


# Pricing methods.
PRICING_REAL = object()
PRICING_AVERAGE = object()


class Inventory(object):
    "An interface for inventory objects."

    def __init__(self, booking=BOOKING_NONE, pricing=PRICING_REAL):
        # The booking method, a function object that is supposed to return the
        # next position to be matched.
        self.booking_findnext = booking

        # The pricing method.
        self.pricing_method = pricing

        # Functions that convert into integer, float and string representation.
        if not hasattr(self, 'L'):
            self.L = lambda x: Decimal(str(x))
        if not hasattr(self, 'F'):
            self.F = float
        if not hasattr(self, 'S'):
            self.S = str

        self.reset()

    def reset(self):
        "Reset the realized pnl and position (initial state)."

        # The last marked price for the underlying product.
        self.mark = None

        # The realized P+L for this inventory.
        self._realized_pnl = self.L(0)

        # The price of the last trade.
        self.last_trade_price = None

        # For precision reasons, we track the cost of our positions separately
        # (we could otherwise adjust each of them to the average every time it
        # changes, introducing numerical error, but simplifying the code). This
        # is only used for average cost pricing.
        self.cost4avg = self.L(0)

        # A deque of Position objects for our active position.
        self.positions = deque()

    def reset_position(self):
        """
        Reset the current position to 0. After calling this method, the P+L is
        only the unrealized P+L. We return the list of trade objects for the
        eliminated positions.
        """
        eliminated = [pos.obj for pos in self.positions]
        self.positions = deque()
        return eliminated

    def consolidate(self, price):
        """
        Book all of the current inventory's position at the given price
        (typically, some sort of settlement price) and set the position cost at
        that price. This method does not affect the position, but it transfers
        unrealized P+L into realized P+L. This means that if the mark price is
        equal to the consolidation price, the unrealized P+L is 0 after this
        method is called if the consolidation price is equal to the mark price.
        """
        # We extract the PnL from each position by changing its trade price.
        realized_pnl = 0
        for pos in self.positions:
            realized_pnl += (price - pos.price) * pos.size
            pos.price = price
        self._realized_pnl += realized_pnl

        if self.pricing_method is PRICING_AVERAGE:
            self.cost4avg += realized_pnl
            assert self.cost4avg == self.realcost()

        # Another way to accomplish this would be to perform two trades, but
        # that would delete the information about the trade objects. We used to
        # do it like this:
        ## pos = self.position()
        ## self.trade(price, -pos)
        ## assert self.position() == 0
        ## self.trade(price, pos)

    def reset_pnl(self):
        """
        Reset the realized P+L to 0 and returns it. This method effectively
        transfers out the realized P+L from this inventory.
        """
        rpnl, self._realized_pnl = self._realized_pnl, 0
        return rpnl

    def setmark(self, price):
        "Set the mark price for the current product."
        self.mark = price

    def setmarkexit(self, bid, ask):
        "Set the mark price at the price to exit."
        self.mark = bid if self.position() > 0 else ask

    def _sanity_check(self):
        "Perform some internal sanity checks."

        # Check that the signs of our inventory are all the same.
        if self.positions:
            size = self.positions[0].size
            for pos in self.positions:
                assert pos.size * size > 0, pos

    def position(self):
        "Return the current position this inventory is holding."
        self._sanity_check()
        return sum(pos.size for pos in self.positions) if self.positions else self.L(0)

    def realcost(self):
        "Return the real cost of our current positions."
        return sum(pos.cost() for pos in self.positions) if self.positions else self.L(0)

    def cost(self):
        "Return the original cost of our active position."
        if self.pricing_method is PRICING_REAL:
            return self.realcost()
        else:
            return self.cost4avg

    def value(self):
        "Return the marked value of the entire position."
        pos = self.position()
        if pos != 0:
            if self.mark is None:
                raise ValueError("You need to set the mark to obtain the pnl")
            return pos * self.mark
        else:
            return self.L(0)

    def avgcost(self):
        "Return the average price paid for each unit of the current position."
        pos = self.position()
        return self.L(self.F(self.cost()) / pos) if pos != 0 else self.L(0)

    def realized_pnl(self):
        return self._realized_pnl

    def unrealized_pnl(self):
        "Return the P+L for our current position (not including past realized P+L."
        pos = self.position()
        if pos == 0:
            return self.L(0)
        if self.mark is None:
            raise ValueError("You need to set the mark to obtain the pnl")
        return self.position() * self.mark - self.cost()

    def pnl(self):
        "Return the P+L for our current position (not including past realized P+L."
        return self._realized_pnl + self.unrealized_pnl()

    def dump(self):
        print ',---------------', self
        print '| position       ', self.position()
        print '| mark           ', self.S(self.mark) if self.mark else None
        print '| avgcost        ', self.S(self.avgcost() or 0)
        print '| value          ', self.S(self.value()) if self.mark else None
        print '| cost           ', self.S(self.cost())
        print '| cost4avg       ', self.S(self.cost4avg)
        print '| unrealized_pnl ', self.S(self.unrealized_pnl()) if self.mark else None
        print '| realized_pnl   ', self.S(self.realized_pnl())
        print '| pnl            ', self.S(self.pnl()) if self.mark else None
        print '| inventory:     '
        for pos in self.positions:
            print '|   %s' % pos
        print '`---------------', self

    def close_all(self, price):
        "Close all the positions at the mark price."
        self.trade(price, -self.position())
        assert self.position() == 0

    def _findpos(self, obj):
        "Return the position that corresponds to a specific trade object."
        for pos in self.positions:
            if pos.obj is obj:
                return pos
        else:
            return None

    def close(self, obj, price, quant=None):
        """ Close the position for the trade 'obj' at the given 'price'. If
        'quant' is specified, close the position only partially (otherwise close
        the entire position). Note that the outcome of using this method does
        not depend on the selected booking method."""
        pos = self._findpos(obj)
        if pos is None:
            raise KeyError("Invalid trade object, could not be found: %s" % obj)
        if quant is not None:
            if quant * pos.size <= 0:
                raise KeyError("Invalid close size %s of %s." % (quant, pos.size))
            if abs(quant) > abs(pos.size):
                raise KeyError("Trying to close %s of %s." % (quant, pos.size))
        else:
            quant = -pos.size
        return self._trade(price, quant, None, lambda inv: pos)

    def trade(self, price, quant, obj=None):
        """ Book a trade for size 'quant' at the given 'price', using the
        default booking method. Return list of trade objects booked and
        the PnL realized by this trade (if any).
        Note: if you want to book positions manually, use the close() method."""

        return self._trade(price, quant, obj, self.booking_findnext)

    def _trade(self, price, quant, obj, nextpos):
        """ Trade booking implementation. We book trades at price 'price' for
        the given size 'quant' only. 'obj' is the trade object to this trade,
        and is inserted in the new Position object if there is remaining size.
        'nextpos' is a function that will return the next Position object to be
        booked against (this is the booking method)."""

        ## trace('__________________ _trade', price, quant, obj, booking)

        # A list of (trade-object, quantity) booked.
        booked = []

        # Total size booked during this trade.
        total_booked = 0

        # "Real" PnL for the booked trades.
        real_pnl = 0

        # Book the new trade against existing positions if the trade is not on
        # the same side as our current position.
        position = self.position()
        if quant * position < 0:

            # Process all the positions.
            done = 0
            while self.positions:
                pos = nextpos(self)
                if abs(quant) >= abs(pos.size):
                    # This position is entirely consumed by the trade.
                    booked_quant = pos.size
                    self.positions.remove(pos) # This may become slow.
                else:
                    # This position is only partially consumed by the trade.
                    booked_quant = -quant
                    pos.size += quant
                    done = 1

                quant += booked_quant
                total_booked += booked_quant
                booked.append( (pos.obj, booked_quant) )

                real_pnl += booked_quant * (price - pos.price)
                if done or quant == 0:
                    break

            assert quant * self.position() >= 0

        # Price the booked trades into the realized PnL, depending on method.
        if self.pricing_method is PRICING_REAL:
            realized_pnl = real_pnl
        else:
            if position == 0:
                assert total_booked == 0, total_booked
                realized_pnl = 0
            else:
                realized_cost = self.L((total_booked*self.F(self.cost4avg))/position)
                realized_pnl = total_booked * price - realized_cost
                self.cost4avg -= realized_cost
        self._realized_pnl += realized_pnl
        if total_booked == 0:
            assert realized_pnl == 0, realized_pnl
        else:
            booked.append( (obj, -total_booked) )
            
        # Append the remainder of our trade to the inventory if not all was
        # booked.
        if quant != 0:
            newpos = Position(self, price, quant, obj)
            self.positions.append(newpos)
            if self.pricing_method is PRICING_AVERAGE:
                self.cost4avg += newpos.cost()

        self.last_trade_price = price
        return booked, realized_pnl



class FIFOInventory(Inventory):
    def __init__(self):
        Inventory.__init__(self, booking=BOOKING_FIFO, pricing=PRICING_REAL)

class LIFOInventory(Inventory):
    def __init__(self):
        Inventory.__init__(self, booking=BOOKING_LIFO, pricing=PRICING_REAL)

class AvgInventory(Inventory):
    def __init__(self):
        Inventory.__init__(self, booking=BOOKING_FIFO, pricing=PRICING_AVERAGE)
        # Note: the booking method matters little here, other than for the
        # ordering of the trades that get closed.



########NEW FILE########
__FILENAME__ = ledger
# -*- coding: utf-8 -*-
"""
Main file and data models for the Python version of Ledger.
"""

# stdlib imports
import sys, os, logging, re, codecs, string
from copy import copy, deepcopy
import cPickle as pickle
from decimal import Decimal, getcontext
from datetime import date, timedelta
from os.path import *
from operator import attrgetter
from itertools import count, izip, chain, repeat
from StringIO import StringIO
from bisect import bisect_left, bisect_right
from collections import defaultdict

# beancount imports
from beancount.wallet import Wallet
from beancount.utils import SimpleDummy, iter_pairs
from beancount.inventory import FIFOInventory

# fallback imports
from beancount.fallback.collections2 import namedtuple


__all__ = ('Account', 'Transaction', 'Posting', 'Ledger',
           'CheckDirective')

oneday = timedelta(days=1)

com_unit_precision = ('Miles',)


def init_wallets(py_wallets):
    """
    Initialize globals for precision calculations.
    """
    # Set the representational precision of Decimal objects.
    ctx = getcontext()
    ctx.prec = 16

init_wallets(1)



# The error messages that we use.
INFO     = logging.INFO      # Normal message, not an error.

WARNING  = logging.WARNING   # Benign problem, we continue.

ERROR    = logging.ERROR     # Serious error, but the parsed file is still valid,
                             # for example, a failed assert.

CRITICAL = logging.CRITICAL  # Error that we can't recover from,
                             # the Ledger is invalid.










class Message(object):
    "The encapsulation for a single message."

    def __init__(self, level, message, filename, lineno):
        self.level = level
        self.message = message
        self.filename = filename
        self.lineno = lineno

    def __str__(self):
        return '%s:%s:%d %s' % (self.level, self.filename, self.lineno, self.message)



class Account(object):
    """
    An account object.
    """
    __slots__ = ('sep', 'fullname', 'name', 'ordering', 'postings',
                 'parent', 'children', 'usedcount', 'isdebit', 'commodities',
                 'balances', 'balances_cumul', 'tmp_postings',
                 'checked', 'check_min', 'check_max')

    # Account path separator.
    sep = ':'

    def __init__(self, fullname, ordering):

        # The full name of the account.
        self.fullname = fullname

        # The full name of the account.
        self.name = fullname.split(Account.sep)[-1]
        self.ordering = ordering

        # A list of the postings contained in this account.
        self.postings = []

        # The parent and children accounts.
        self.parent = None
        self.children = []

        # The number of times an account has been requested for use.
        self.usedcount = 0

        # Flag: True if a debit account, False if a credit account, None is unknown.
        self.isdebit = None

        # A list of valid commodities that can be deposited in this account.
        self.commodities = []

        # An attribute that tells if this account contains a check.
        # (Set by the 'check' directive.)
        self.checked = None
        self.check_min = None
        self.check_max = None

        # A dict of available balances on an account object. All the wallet
        # amounts calculated per-account can be stored here under unique names.
        # Some names are reserved: 'total' is the main balance for this account.
        self.balances = {}
        self.balances_cumul = {}

        # Temporary list used in computing balances for the tree of nodes.
        # This list contains lists of postings to process for this account.
        self.tmp_postings = None

    def __str__(self):
        return "<Account '%s'>" % self.fullname
    __repr__ = __str__

    def __len__(self):
        "Return the number of subpostings for the account."
        n = len(self.postings)
        n += sum(len(child) for child in self.children)
        return n

    atypemap = {True: 'Debit',
                False: 'Credit',
                None: ''}
    def getatype(self):
        return self.atypemap[self.isdebit]

    def isroot(self):
        return self.fullname == ''

    def isused(self):
        "Return true if the account is used."
        return self.usedcount > 0

    def subpostings(self):
        """
        Iterator that yields all of the postings in this account and in its
        children accounts.
        """
        for post in self.postings:
            yield post
        for child in self.children:
            for post in child.subpostings():
                yield post

    def get_fullname(self):
        "Compute the full name of the account from its hierarchy."
        if self.parent is None:
            return self.name
        else:
            return Account.sep.join(
                (self.parent.get_fullname(), self.name)).lstrip(':')

    def ischildof(self, cparent):
        """ Return true if the 'cparent' account is a parent of this account (or
        is that account itself)."""

        if self is cparent:
            return True
        elif self.parent is None:
            return False
        else:
            return self.parent.ischildof(cparent)




class Dated(object):
    "Base class for dates and ordered objects."

    actual_date = None
    effective_date = None
    ordering = None

    def __cmp__(self, other):
        """ A comparison function that takes into account the ordering of the
        transactions."""
        c = cmp(self.actual_date, other.actual_date)
        if c != 0:
            return c
        else:
            return cmp(self.ordering, other.ordering)

    def rdate(self):
        return self.actual_date.strftime('%Y-%m-%d')

    def fulldate(self):
        l = [self.actual_date.strftime('%Y-%m-%d')]
        if self.effective_date != self.actual_date:
            l.append(self.effective_date.strftime('=%Y-%m-%d'))
        return ''.join(l)


class Filtrable(object):
    """
    Base class for filtering using the predicate created by the cmdline module.
    """
    def get_date(self):
        pass

    def get_account_name(self):
        pass

    def get_note(self):
        pass

    def get_tags(self):
        pass

    def get_txn_postings(self):
        pass


class Transaction(Dated):
    "A transaction, that contains postings."

    # Parse origin.
    filename = None
    lineno = None

    flag = None
    code = None

    # 'payee' and 'narration' compose the description field. Usually, we want to
    # be able to split the payee apart, because it can be used to further
    # automate the entry of transactions, or to filter down the results by
    # payee. If there is separator, we simply leave the 'payee' field empty.
    payee = None
    narration = None

    # The tags is a (shared) list that is assigned to a set of transactions,
    # using the @begintag and @endtag directives. This can be used to mark
    # transactions during a trip, for example.
    tags = None

    # The vector sum of the various postings here-in contained.
    wallet = None

    def __init__(self):
        # The list of contained postings.
        self.postings = []

    def description(self):
        return ''.join(['%s | ' % self.payee if self.payee else '',
                        self.narration or ''])

    def topline(self):
        "Render the top line of the transaction, without the date."
        # Compute the transaction declaration line.
        l = []
        append = l.append
        append(' ')
        append('%s ' % (self.flag or ' '))
        if self.code:
            append('(%s) ' % self.code)
        desc = self.description()
        if desc:
            append(desc)
        return ''.join(l)

    def __str__(self):
        "Produce a basic rendering for debugging."
        lines = [self.fulldate() + ' ' + self.topline()]
        lines.extend(str(post) for post in self.postings)
        return os.linesep.join(lines)

    def pretty(self):
        "Produce a pretty rendering."
        lines = [self.topline()]
        lines.extend(post.pretty() for post in self.postings)
        return os.linesep.join(lines)

    def get_booking_post(self):
        """Find a booking entry in its posts and return it or None if there
        aren't any."""
        for post in self.postings:
            if post.booking is not None:
                return post


VIRT_NORMAL, VIRT_BALANCED, VIRT_UNBALANCED = 0, 1, 2

class Posting(Dated):
    """
    A posting or entry, that lives within a transaction.
    """
    # Parse origin.
    filename = None
    lineno = None

    # The transaction that this posting belongs to.
    txn = None

    flag = None
    account = None
    account_name = None
    virtual = VIRT_NORMAL
    amount = None

    price = None         # Price-per-commodity.
    cost = None          # The cost of this commodity.

    note = None
    booking = False  # Whether this is a booking entry to be filled in.

    def __init__(self, txn):
        self.txn = txn

    def __str__(self):
        s = '  %-70s %s' % (self.account_name or self.account.name, self.amount)
        if self.note:
            s += ' ; %s' % self.note
        return s
    __repr__ = __str__

    def __key__(self):
        return (self.actual_date, self.ordering)

    def pretty(self):
        "Produce a pretty rendering."
        return '  %-50s %10s (Cost: %10s) %s' % (
            #self.actual_date,
            self.account.fullname,
            self.amount.round(),
            self.cost.round(),
            '; %s' % self.note if self.note else '')

    #
    # Filtrable.
    #
    def get_date(self):
        return self.actual_date

    def get_account_name(self):
        self.account.fullname

    def get_note(self):
        return self.note

    def get_tags(self):
        return self.txn.tags

    def get_txn_postings(self):
        return self.txn.postings


class BookedTrade(object):
    """
    An object that represents all the information that is present in a trade
    (turn-around).
    """
    Leg = namedtuple("Leg",
                     ('post amount_book '
                      'price comm_price '
                      'amount_price xrate amount_target').split())
    # comm_book: the commodity being booked
    # comm_price: the commodity in which the booked commodity is priced
    # comm_target: the target commodity for the gain/loss
    # amount_book: number of units that we booked
    # amount_price: amount in the natural pricing commodity
    # amount_target: amount in the final target commodity

    def __init__(self, account, comm_book, comm_target, post_book):

        # The account and booking commodity.
        self.account = account

        # The commodity being booked.
        self.comm_book = comm_book

        # The target pricing commodity for PnL calculation.
        self.comm_target = comm_target

        # The post that is adjusted for booking.
        self.post_book = post_book

        # The list of (posting, amount, price, amount_in, xrate) that
        # participated in the booked trade.
        self.legs = []

    def close_date(self):
        return self.legs[-1][0].actual_date

    __key__ = close_date
    def __cmp__(self, other):
        return cmp(self.close_date(), other.close_date())

    def add_leg(self, *args):
        "See Leg nested class for required members."
        leg = self.Leg(*args)
        assert leg.post.amount.tocomm() == self.comm_book
        self.legs.append(leg)

    #
    # Implement the Filtrable interface.
    #
    def get_date(self):
        return self.close_date()

    def get_account_name(self):
        return self.account.fullname

    def get_note(self):
        return None

    def get_tags(self):
        return []

    def get_txn_postings(self):
        return [x.post for x in self.legs]



class Ledger(object):
    """
    A ledger object, that contains transactions and directives and all data
    related to the construction of a single ledger, its list of commodities,
    etc.
    """
    def __init__(self):

        # A list of (filename, encoding) parsed.
        self.parsed_files = []

        # A dict of all the accounts.
        self.accounts = {}

        # A list of all the transactions in the file.
        self.transactions = []

        # A list of the commodities names.
        self.commodities = set()

        # A list of all the postings.
        self.postings = []

        # A list of the messages accumulated during the parsing of the ledger.
        self.messages = []

        # The source lines from which the Ledger was built.
        self.source = []

        # A map of commodity to a list of price commodities.
        self.pricedmap = None

        # A map of directive-name to contents.
        self.directives = {}
        add_directive = lambda x: self.directives.__setitem__(x.name, x)
        check = CheckDirective(self)
        add_directive(check)
        add_directive(DefineAccountDirective(self))
        add_directive(DefineCommodityDirective(self))
        add_directive(AutoPadDirective(self, check))
        add_directive(DefvarDirective(self))
        add_directive(BeginTagDirective(self))
        add_directive(EndTagDirective(self))
        add_directive(LocationDirective(self))
        add_directive(PriceDirective(self))

        # Current tags that are being assigned to transactions during parsing.
        self.current_tags = []

        # List of booked trades.
        self.booked_trades = []

        # A dict of payees key names to (full-payee-name, transaction)
        self.payees = {}

    def isvalid(self):
        "Return true if the ledger has not had critical errors."
        return all(self.messages.level != CRITICAL)

    def log(self, level, message, obj):
        "Log a message for later, and display to stderr."
        assert level in (logging.INFO,
                         logging.WARNING,
                         logging.ERROR,
                         logging.CRITICAL), level

        filename, lineno = None, None
        if isinstance(obj, tuple):
            filename, lineno = obj
        if hasattr(obj, 'filename'):
            filename = obj.filename
        if hasattr(obj, 'lineno'):
            lineno = obj.lineno

        if filename is not None:
            filename = abspath(filename)

        msg = Message(level, message, filename, lineno)
        self.messages.append(msg)
        if filename is not None and lineno is not None:
            s = ' %s:%-4d : %s' % (filename, lineno, message)
        else:
            s = ' %s' % message
        logging.log(level, s)


    # Account ordering integer.
    acc_ordering = count().next

    def get_account(self, name, create=False, incrcount=True):
        """
        Return or create an account by name, creating all the intermediate
        account tree nodes as well. 'incrcount' increases the account's 'used'
        count by that much (this is used to figure out which accounts are in
        use).
        """
        accounts = self.accounts
        try:
            acc = accounts[name]
        except KeyError:
            if not create:
                raise
            acc = accounts[name] = Account(name, self.acc_ordering())
            if name:
                # Set and make sure the parent exists.
                parent_name = Account.sep.join(name.split(Account.sep)[:-1])
                acc.parent = self.get_account(parent_name, create)
                children = acc.parent.children
                if acc not in children:
                    children.append(acc)
        if incrcount:
            acc.usedcount += 1
        return acc

    def get_root_account(self):
        "Return the root account."
        return self.get_account('', True)




    # Patterns for comments and empty lines.
    comment_re = re.compile('^\s*;(.*)$')
    empty_re = re.compile('^\s*$')

    # Pattern for date.
    date_re = re.compile('(\d\d\d\d)[/-](\d\d)[/-](\d\d)')

    # A date within a note.
    notedate_re = re.compile('\[(?:%(date)s)?(?:=%(date)s)?\]' %
                             {'date': date_re.pattern})

    # Pattern for a transaction line.
    txn_re = re.compile('^%(date)s(=%(date)s)?\s+(?:(.)\s+)?(\(.*?\))?(.*)$' %
                        {'date': date_re.pattern})
    payee_sep = ' | '
    desc_re = re.compile('(?:\s*([^|]+?)\s*\|)?\s*([^|]*?)\s*$')

    # Pattern for an amount.
    commodity_re = re.compile('"?([A-Za-z][A-Za-z0-9.~\']*)"?')
    amount_re = re.compile('([-+]?\d*(?:\.\d*)?)\s+%(comm)s' %
                           {'comm': commodity_re.pattern})

    # Pattern for an account (note: we don't allow spaces in this version).
    account_re = re.compile('[:A-Za-z0-9-_]+')
    postaccount_re = re.compile('(?:%(accname)s|\[%(accname)s\]|\(%(accname)s\))' %
                                {'accname': account_re.pattern})

    # Pattern for a posting line (part of a transaction).
    posting_re = re.compile(
        ('\s+([*!]\s+)?(%(account)s)' # account name
         '(?:'
         '(?:\s+%(amount)s)?'  # main
         '(?:\s+(?:({)\s*%(amount)s\s*}|({{)\s*%(amount)s\s*}}))?' # declared cost
         '(?:\s+@(@?)(?:\s+%(amount)s))?\s*(?:;(.*))?\s*$'
         '|'
         '\s+(BOOK)\s+%(commodity)s(?:\s+(IN)\s+%(commodity)s)?\s*$'  # booking entry
         ')') %  # price/note
        {'amount': amount_re.pattern,
         'account': postaccount_re.pattern,
         'commodity': commodity_re.pattern})

    # Pattern for the directives, and the special commands.
    directive_re = re.compile('^@([a-z_]+)\s+([^;]*)(;.*)?')
    special_re = re.compile('([YPNDCiobh])\s+')
    command_re = re.compile('!([a-z]+)')

    def parse_string(self, text, name='<string>', encoding='ascii'):
        f = StringIO(text)
        Reader = codecs.getreader(encoding)
        return self.parse_file(Reader(f), name, encoding)

    def parse_file(self, f, fn, encoding='ascii'):
        """
        Parse the file 'fn' in Ledger file format, into this Ledger object.

        return raw, unnormalized lists of objects that were seen in the file.
        (Those objects need to have completions and some conversions done on
        them, and more.)
        """
        self.parsed_files.append((fn, encoding))
        source = self.source = []

        # Cache some attribetus for speed.
        match_comment = self.comment_re.match
        match_empty = self.empty_re.match
        search_notedate = self.notedate_re.search
        match_txn = self.txn_re.match
        match_posting = self.posting_re.match
        match_special = self.special_re.match
        match_command = self.command_re.match
        match_directive = self.directive_re.match

        accounts = self.accounts

        xread = f.readline
        lineno = [0]
        def nextline():
            lineno[0] += 1
            line = xread()
            source.append(line)
            assert isinstance(line, unicode), line
            if not line:
                raise StopIteration
            return line

        add_commodity = self.commodities.add
        next_ordering = count(1).next
        try:
            line = nextline()
            while 1:
                # Skip comments.
                if match_empty(line) or match_comment(line):
                    line = nextline()
                    continue

                # Parse a transaction.
                mo = match_txn(line)
                if mo:
                    txn = Transaction()
                    txn.filename = fn
                    txn.lineno = lineno[0]
                    txn.ordering = next_ordering()
                    txn.tags = self.current_tags
                    self.transactions.append(txn)

                    try:
                        actual_date = date(*map(int, mo.group(1, 2, 3)))
                        if mo.group(4):
                            effective_date = date(*map(int, mo.group(5, 6, 7)))
                        else:
                            effective_date = actual_date
                    except ValueError, e:
                        self.log(CRITICAL, "Date component is out of range: %s" % e,
                                 (fn, lineno[0]))
                        line = nextline()
                        continue

                    txn.actual_date = actual_date
                    txn.effective_date = effective_date

                    txn.flag = mo.group(8)
                    txn.code = mo.group(9)

                    desc_line = mo.group(10)
                    mod = Ledger.desc_re.match(desc_line)
                    if not mod:
                        self.log(ERROR, "Invalid description: %s" % desc_line,
                                 (fn, lineno[0]))
                        line = nextline()
                        continue
                    txn.payee, txn.narration = mod.groups()

                    # Parse the postings.
                    while 1:
                        line = nextline()

                        # Allow comments in between postings, but not empty lines.
                        if match_comment(line):
                            continue

                        mo = match_posting(line)
                        if mo:
                            post = Posting(txn)
                            post.filename, post.lineno = fn, lineno[0]
                            post.ordering = next_ordering()
                            txn.postings.append(post)

                            (post.flag,
                             post.account_name,
                             post.note) = mo.group(1,2,14)

                            booking_comm = (mo.group(16) if mo.group(15) == 'BOOK'
                                            else None)
                            if booking_comm is not None:
                                booking_quote = (
                                    mo.group(18) if mo.group(17) == 'IN' else None)
                                post.booking = (booking_comm, booking_quote)
                            else:
                                post.booking = None

                            # Remove the modifications to the account name.
                            accname = post.account_name
                            fchar = accname[0]
                            if fchar in '[(':
                                accname = accname.strip()[1:-1]
                                post.virtual = (VIRT_BALANCED if fchar == '['
                                                else VIRT_UNBALANCED)
                            post.account = acc = self.get_account(accname, create=1)

                            # Fetch the amount.
                            anum, acom = mo.group(3,4)
                            if anum is not None:
                                anum = Decimal(anum)
                                post.amount = Wallet(acom, anum)
                                add_commodity(acom)
                            else:
                                post.amount = None


                            # Fetch the price.
                            pnum, pcom = mo.group(12,13)
                            if pnum is not None:
                                pnum = Decimal(pnum)
                                add_commodity(pcom)
                                if bool(mo.group(11) == '@'):
                                    pnum /= anum
                                post.price = Wallet(pcom, pnum)
                            else:
                                post.price = None


                            # Fetch the cost.
                            if mo.group(5) == '{':
                                assert mo.group(8) == None
                                cnum, ccom = mo.group(6,7)
                                cnum = anum*Decimal(cnum)
                                post.cost = Wallet(ccom, cnum)
                                add_commodity(ccom)

                            elif mo.group(8) == '{{':
                                assert mo.group(5) == None
                                cnum, ccom = mo.group(9,10)
                                cnum = Decimal(cnum)
                                post.cost = Wallet(ccom, cnum)
                                add_commodity(ccom)

                            else:
                                assert mo.group(5) is None, mo.groups()
                                assert mo.group(8) is None, mo.groups()


                            # Compute the price from the explicit cost.
                            if post.cost is not None:
                                if post.price is None:
                                    post.price = Wallet(ccom, cnum/anum)

                            # Compute the cost from the explicit price.
                            elif post.price is not None:
                                    post.cost = Wallet(pcom, anum*pnum)

                            # Compute the cost directly from the amount.
                            else:
                                post.cost = post.amount
                                if post.cost is not None:
                                    post.cost = Wallet(post.cost) # copy


                            # Look for date overrides in the note field.
                            if post.note:
                                mo = search_notedate(post.note)
                                if mo:
                                    # Set the posting's date according to the
                                    # dates in the note.
                                    actual = mo.group(1,2,3)
                                    if actual[0]:
                                        post.actual_date = date(*map(int, actual))
                                    effective = mo.group(4,5,6)
                                    if effective[0]:
                                        post.effective_date = \
                                            date(*map(int, effective))

                                    # Remove the date spec from the note itself.
                                    post.note = self.notedate_re.sub(post.note, '')

                            # Default values for dates should be those of the
                            # transaction.
                            if post.actual_date is None:
                                post.actual_date = txn.actual_date
                            if post.effective_date is None:
                                post.effective_date = txn.effective_date

                        else:
                            txn = None
                            break
                    continue

                # Parse a directive.
                mo = match_directive(line)
                if mo:
                    direc, direc_line = mo.group(1,2)
                    try:
                        parser = self.directives[direc]
                        parser.parse(direc_line, fn, lineno[0])
                    except ValueError, e:
                        self.log(CRITICAL, "Unknown directive %s: %s" % (direc, e),
                                 (fn, lineno[0]))
                    line = nextline()
                    continue

                # Parse a directive.
                mo = match_special(line)
                if mo:
                    self.log(WARNING, "Directive %s not supported." % mo.group(1),
                             (fn, lineno[0]))
                    line = nextline()
                    continue

                # Parse a directive.
                mo = match_command(line)
                if mo:
                    self.log(CRITICAL, "Command %s not supported." % mo.group(1),
                             (fn, lineno[0]))
                    line = nextline()
                    continue

                self.log(CRITICAL, "Cannot recognize syntax:\n %s" % line.strip(),
                         (fn, lineno[0]))
                line = nextline()

        except StopIteration:
            pass

        self.build_postings_lists()

        # Set the precision map according to some rules about the commodities.
        roundmap = Wallet.roundmap
        for com in self.commodities:
            if com in com_unit_precision:
                prec = 0
            else:
                prec = 2 if (len(com) == 3) else 3
            roundmap[com] = Decimal(str(10**-prec))

        self.complete_balances()
        self.compute_priced_map()
        self.complete_bookings()
        self.build_payee_lists()
        self.build_tag_lists()

    def build_postings_lists(self):
        """ (Re)Builds internal lists of postings from the list of transactions."""

        self.postings = []
        for acc in self.accounts.itervalues():
            acc.postings = []

        for txn in self.transactions:
            for post in txn.postings:
                post.account.postings.append(post)
                self.postings.append(post)

        self.postings.sort()
        for acc in self.accounts.itervalues():
            acc.postings.sort()


    class BalanceVisitor(object):
        """
        A visitor that computes the balance of the given account node.
        """
        def __init__(self, aname, atcost):
            self.aname = aname
            self.atcost = atcost

        def __call__(self, node):

            # Compute local balance.
            bal = Wallet()
            for post in node.tmp_postings:
                assert post.account is node
                bal += (post.cost if self.atcost else post.amount)
            node.balances[self.aname] = bal
            total = Wallet(bal)

            # Compute balance that includes children (cumulative).
            for child in node.children:
                total += child.balances_cumul[self.aname]
            node.balances_cumul[self.aname] = total

    def compute_balsheet(self, aname, atcost=False):
        """
        Compute a balance sheet stored in the given attribute on each account
        node.
        """
        # Set the temporary postings list to the full list.
        for acc in self.accounts.itervalues():
            acc.tmp_postings = acc.postings

        # Accumulate amounts.
        vis = self.BalanceVisitor(aname, atcost)
        self.visit(self.get_root_account(), vis)

        # Reset the temporary lists.
        for acc in self.accounts.itervalues():
            acc.tmp_postings = None

    def compute_balances_from_postings(self, postings, aname, atcost=False):
        """
        Given a set of postings, compute balances into the given attributes.
        """

        # Clear the accumulators.
        for acc in self.accounts.itervalues():
            acc.balances.pop(aname, None)
            acc.balances_cumul.pop(aname, None)

        # Create the temporary postings lists.
        for acc in self.accounts.itervalues():
            acc.tmp_postings = []
        for post in postings:
            post.account.tmp_postings.append(post)

        # Accumulate amounts.
        vis = self.BalanceVisitor(aname, atcost)
        self.visit(self.get_root_account(), vis)

        # Reset the temporary lists.
        for acc in self.accounts.itervalues():
            acc.tmp_postings = None



    def complete_balances(self):
        """
        Fill in missing numbers in each transactions and check if the
        transactions can be made to balance this way.
        """
        # Note: if a price is mentioned, we store the wallet in real terms of the
        # commodity specified in the amount, but we always try to convert to the
        # commodity specified in the price in order to balance.

        for txn in self.transactions:

            # Split postings between normal, virtual and virtual unbalanced.
            postsets = defaultdict(list)
            for post in txn.postings:
                postsets[post.virtual].append(post)

            # Process normal postings.
            self.check_postings_balance(postsets[VIRT_NORMAL])
            self.check_postings_balance(postsets[VIRT_BALANCED])

            # Process virtual balanced postings.

            # Process non-balanced virtual postings.
            for post in postsets[VIRT_UNBALANCED]:
                if post.cost is None:
                    if post.booking is None:
                        self.log(
                            WARNING,
                            "Virtual posting without amount has no effect.", post)
                    post.amount = post.cost = Wallet()

    def get_price_comm(self, comm):
        """ Return the pricing commodity of the given commodity 'comm'. Note
        that there must be a single pricing commodity for this to work. """
        pcomms = self.pricedmap[comm]
        assert len(pcomms) == 1, "Looking in %s for %s." % (pcomms, comm)
        return iter(pcomms).next()

    def complete_bookings(self):
        """
        Complete entries that are automatic bookings in each account.

        Important note: this does *NOT* automatically take into account the
        commissions.
        """

        # Build a list of booking jobs to be done, by looking at all
        # (unresolved) booking posts and finding out which accounts we need to
        # apply booking for which commodity. For example:
        #
        #    2004-11-29 * Sell QQQ
        #      Assets:Investments:RBCDirect:Taxable-CA:QQQ   -50.00 QQQ @ 39.02 USD
        #      Assets:Investments:RBCDirect:Taxable-CA      2233.52 CAD @ 0.8638 USD
        #      Expenses:Financial:Commissions                 25.00 CAD
        #      (Income:Investments:Capital-Gains)           BOOK QQQ IN CAD
        #
        # The 3rd posting tells us that we need to book QQQ, in the account
        # specified in the first posting. We would create a booking job to book
        # QQQ in account 'Assets:Investments:RBCDirect:Taxable-CA:QQQ'. The
        # second (or other) line(s) do(es) not affect the booking. Note that
        # this means that commissions are not included in the booked gain/loss.
        booking_posts = (post for post in self.postings if post.booking)
        booking_jobs = defaultdict(set)
        for post in booking_posts:
            comm_book, _ = post.booking
            n = 0
            for tpost in post.txn.postings:
                if comm_book in tpost.amount:
                    booking_jobs[tpost.account].add(comm_book)
                    n += 1
            if n == 0:
                logging.error("Invalid booking for %s in transaction at %s:%d" %
                              (comm_book, post.txn.filename, post.txn.lineno))

        # Apply the booking jobs to each required account.
        pricedir = self.directives['price']
        for acc, bcomms in sorted(booking_jobs.iteritems()):

            # For each booking commodity.
            for comm_book in bcomms:
                logging.info("Booking  %s  in %s" % (comm_book, acc.fullname))

                # Figure out the pricing commodity of the commodity being
                # booked.
                comm_price = self.get_price_comm(comm_book)

                # Process all of the account's postings in order.
                inv = FIFOInventory()
                booked = []
                for post in acc.postings:

                    # Apply trades to our inventory.
                    if comm_book in post.amount:
                        assert post.price is not None, post
                        assert post.price.tocomm() == comm_price
                        price = post.price.tonum()
                        _booked, _ = inv.trade(price, post.amount[comm_book], post)

                        booked.extend(_booked)

                    # If there is a booking posting in the current transaction,
                    # set its amount to the P+L at this point.
                    #
                    # FIXME: we should preprocess this to avoid the loop in
                    # processing each transaction.
                    txn = post.txn
                    post_book = txn.get_booking_post()
                    if post_book is None:
                        logging.warning("Unbooked %s in transaction at %s:%d" %
                                        (comm_book, txn.filename, txn.lineno))

                    elif not booked:
                        post_book.flag = 'B'
                        post_book.note = 'BOOKED'
                        logging.warning(
                            "Useless booking entry in transaction at %s:%d" %
                            (txn.filename, txn.lineno))

                    else:
                        _comm_book, comm_target = post_book.booking
                        assert _comm_book == comm_book, (_comm_book, comm_book)

                        # Create the trade's legs and compute the PnL.
                        btrade = BookedTrade(acc, comm_book, comm_target, post_book)
                        pnl_price, pnl_target = Decimal(), Decimal()
                        for post, amount_book in booked:
                            price, comm_price = post.price.single()

                            amount_price = -amount_book * price
                            if comm_target is None:
                                xrate = 1
                                amount_target = amount_price
                            else:
                                assert comm_target != comm_price, \
                                       (comm_target, comm_price)
                                xrate = pricedir.getrate(
                                    comm_price, comm_target, post.actual_date)
                                amount_target = amount_price * xrate

                            btrade.add_leg(post, amount_book,
                                           price, comm_price,
                                           amount_price, xrate, amount_target)

                            pnl_price += amount_price
                            pnl_target += amount_target

                        rpnl = inv.reset_pnl()
                        assert pnl_price == rpnl, (pnl_price, rpnl) # Sanity check.

                        w_price = Wallet(comm_price, pnl_price)
                        w_target = Wallet(comm_target or comm_price, pnl_target)

                        if not hasattr(post_book, 'amount_orig'):
                            post_book.amount_orig = Wallet()

                        # Important note: these are usually flow amounts
                        # (income/expense) and so a gain will show as a negative
                        # value, and a loss as a positive one (expense).
                        post_book.amount_orig -= w_price
                        post_book.amount -= w_target
                        post_book.flag = 'B'
                        post_book.note = 'BOOKED'

                        booked[:] = []
                        self.booked_trades.append(btrade)

        self.booked_trades.sort()

        # Note: Maybe we need to include the booking posting if it is not part
        # of the list of transations that makes up a trade.

    def compute_priced_map(self):
        """
        Compute the priced map, that is, the set of commodities that each
        commodity is priced in.
        """
        pmap = defaultdict(set)
        for post in self.postings:
            if post.price is not None:
                assert len(post.amount) == 1
                assert len(post.price) == 1
                pmap[post.amount.keys()[0]].add(post.price.keys()[0])
        self.pricedmap = dict(pmap)

    def check_postings_balance(self, postings):
        """
        Check that the given list of postings balance and automatically fill-in
        for missing ones.
        """
        if not postings:
            return

        # Note: we assume that we've already set the cost to the amount if
        # there was no price defined, so we can just use the cost here (in
        # convert_wallets()).
        cost = Wallet()
        noamount = None
        for post in postings:
            if post.cost is not None:
                cost += post.cost
            else:
                if noamount is None:
                    noamount = post
                else:
                    self.log(CRITICAL, "More than one missing amounts.", post)
                    post.cost = Wallet() # patch it up.

        if noamount:
            # Fill in the missing amount.
            diff = -cost
            noamount.amount = noamount.cost = diff
            cost += diff

        elif bool(cost):
            # If there are only two non-zero commodities, we can simply infer a
            # price between the two and balance automatically. We also store an
            # implicit measure of price.
            if len(cost) == 2:
                it = cost.iteritems()
                com1, amt1 = it.next()
                com2, amt2 = it.next()
                price1 = -amt1/amt2
                price2 = -amt2/amt1
                txn = postings[0].txn
                self.log(WARNING,
                         "Implied price: %s %s/%s  or  %s %s/%s" %
                         (price1, com1, com2, price2, com2, com1), txn)

        # For each commodity, round the cost to a desired precision.
        cost = cost.round()

        if bool(cost):
            txn = postings[0].txn
            self.log(ERROR,
                     "Transaction does not balance: remaining=%s\n%s\n" %
                     (cost.round(), txn),
                     txn)

        ## # Double-check to make sure that all postings in this transaction
        ## # has been normalized.
        ## for post in postings:
        ##     assert post.amount is not None
        ##     assert post.cost is not None

    def visit_preorder(self, node, visitor):
        """
        Visit pre-order all the nodes of the given accounts tree.
        """
        for child in node.children:
            self.visit_preorder(child, visitor)
        visitor(node)

    def visit_postorder(self, node, visitor):
        if visitor(node) is False:
            return
        for child in node.children:
            self.visit_postorder(child, visitor)

    visit = visit_preorder

    def run_directives(self):
        "Run all the directives on the ledger."

        directives = sorted(self.directives.itervalues(),
                            key=attrgetter('prio'))
        for direct in directives:
            direct.apply()

        # We need to re-sort the postings because the directives may have added
        # some out-of-order postings.
        self.build_postings_lists()



    close_flag = 'A'

    def close_books(self, closedate):
        """ Close the books at the specified date 'closedate', replacing all
        entries before that date by opening balances, and resetting
        Income/Revenues and Expenses categories to zero via entries in Equity.
        We also remove trades whose date is before the closed date.
        """
        other_account = self.get_account('Equity:Opening-Balances', create=1)

        # Select all the transactions with date on or after the closing date.
        # This is the set of transactions that we will keep.
        keep_txns = list(txn
                         for txn in self.transactions
                         if txn.actual_date >= closedate)

        # Compute the set of all postings we will keep, the 'in' set (vs.
        # 'out').
        inset = set(post
                    for txn in keep_txns
                    for post in txn.postings)

        # Figure out some accounts to ignore for closing the books (the income
        # statement accounts, mainly).
        income_acc = self.find_account(('Income', 'Revenue', 'Revenues'))
        expenses_acc = self.find_account(('Expenses', 'Expense'))
        imb1_acc = self.find_account(('Imbalance',))
        imb2_acc = self.find_account(('Imbalances',))
        ignore_accounts = filter(None, [income_acc, expenses_acc,
                                        imb1_acc, imb2_acc, other_account])

        # Create automated transactions to replace balances from all the
        # transactions that came before the closing date, transactions which
        # will be removed.
        open_txns = []
        next_ordering = count(1).next
        for acc in self.accounts.itervalues():
            # Ignore income and expenses accounts.
            if any(acc.ischildof(x) for x in ignore_accounts):
                continue

            bal = Wallet()
            for post in acc.postings:
                if post not in inset:
                    bal += post.amount
            if not bal:
                continue

            # Create a transaction to replace the removed postings.
            txn = Transaction()
            txn.ordering = next_ordering()
            txn.actual_date = txn.effective_date = closedate
            txn.flag = self.close_flag
            txn.narration = ("Opening books for account: '%s'" %
                             acc.fullname)

            post = Posting(txn)
            post.ordering = next_ordering()
            txn.postings.append(post)
            post.flag, post.account_name, post.note = txn.flag, acc.fullname, None
            post.account = acc
            post.amount = bal
            post.actual_date = closedate

            # Other side.
            post = Posting(txn)
            post.ordering = next_ordering()
            txn.postings.append(post)
            post.flag, post.account_name, post.note = txn.flag, acc.fullname, None
            post.account = other_account
            post.amount = -bal
            post.actual_date = closedate

            open_txns.append(txn)
            self.log(INFO, " Closing books at %s in %s for %s" %
                     (closedate, acc.fullname, bal), (None, None))

        self.booked_trades = filter(lambda t: t.close_date() >= closedate,
                                    self.booked_trades)

        self.transactions = sorted(open_txns + keep_txns)
        self.build_postings_lists()

    def find_account(self, namelist):
        """ Returns the first account found matching the given name."""
        candidates = []
        for accname in namelist:
            try:
                candidates.append(self.get_account(accname))
            except KeyError:
                pass
        if not candidates:
            return None
        elif len(candidates) > 1:
            raise KeyError("Ambiguous accounts for %s: %s" %
                           (', '.join(namelist),
                            ', '.join(acc.fullname for acc in candidates)))
        else:
            return candidates[0]

    def filter_postings(self, pred):
        """
        Apply the given predicate on all the postings and filter out those for
        which the predicate returns false.

        Important note: as a side-effect, the 'selected' attribute is set to
        true for the nodes that the predicate matches.
        """
        inset = frozenset(filter(pred, self.postings))
        if len(inset) == 0:
            logging.error("No postings selected by predicates.")
            sys.exit(1)

        for post in self.postings:
            post.selected = (post in inset)

        if pred is None:
            return

        self.postings[:] = [post for post in self.postings if post in inset]

        for acc in self.accounts.itervalues():
            acc.postings[:] = [post for post in acc.postings if post in inset]

        self.transactions = [txn for txn in self.transactions
                             if any(post in inset for post in txn.postings)]

        self.booked_trades = filter(pred, self.booked_trades)

        self.build_payee_lists()
        self.build_tag_lists()

    def build_payee_lists(self):
        paydict = defaultdict(list)

        for txn in self.transactions:
            if txn.payee:
                key = txn.payee_key = compute_payee_key(txn.payee)
                paydict[key].append(txn)


        self.payees = {}
        for key, txns in paydict.iteritems():

            # Find the payee name variant with the highest complexity score.
            snames = [(accent_score(txn.payee), txn.payee) for txn in txns]
            snames.sort()
            payee = snames[-1][1]

            self.payees[key] = (payee, txns)

    def build_tag_lists(self):
        tagdict = defaultdict(list)

        for txn in self.transactions:
            if txn.tags is None:
                continue
            for tag in txn.tags:
                tagdict[tag].append(txn)

        self.tags = tagdict


def compute_payee_key(payee):
    return re.sub('[^A-Za-z0-9]', '_',
                  ' '.join(payee.lower().split()).encode('ascii', 'replace'))




_accents = u'áâàäãéêèëíîìïóôòöõúûùüçøñÁÂÀÄÉÊÈËÍÎÌÏÓÔÒÖÚÛÙÜÇØÑ¡¿'

def accent_score(s):
    """ Return a score for a string that ranks strings in importance whevener
    they have capital letters and accents."""
    acc_upper = sum(1 for c in s if c in string.uppercase)
    acc_score = sum(1 for c in s if c in _accents)
    return acc_upper + acc_score









""" Directive parsers.
"""

class Check(SimpleDummy):
    attrs = 'cdate account expected commodity filename lineno flag balance'.split()

    def __cmp__(self, other):
        return cmp(self.cdate, other.cdate)

    def passed(self):
        return self.flag != '!'


class CheckDirective(object):
    """
    Assert that an account has a specific balance at a specific date in a single
    commodity.
    """

    name = 'check'
    prio = 1000

    mre = re.compile("\s*%(date)s\s+(%(account)s)\s+%(amount)s\s*$" %
                     {'date': Ledger.date_re.pattern,
                      'account': Ledger.account_re.pattern,
                      'amount': Ledger.amount_re.pattern})

    def __init__(self, ledger):
        self.checks = []
        self.ledger = ledger

    def parse(self, line, filename, lineno):
        mo = self.mre.match(line)
        if not mo:
            self.ledger.log(CRITICAL, "Invalid check directive:\n %s" % line.strip(),
                            (filename, lineno))
            return
        cdate = date(*map(int, mo.group(1, 2, 3)))
        account = self.ledger.get_account(mo.group(4), create=1)
        com = mo.group(6)
        amount = (com, Decimal(mo.group(5)))
        expected = Wallet(*amount)
        self.checks.append(Check(cdate, account, expected, com, filename, lineno,
                                 None, expected))

    def apply(self):
        ledger = self.ledger

        for acc in ledger.accounts.itervalues():
            acc.checked = False
            acc.check_min = acc.check_max = None

        for chk in self.checks:
            cdate = chk.cdate
            acc = chk.account
            expected = chk.expected

            acc.checked = True

            balance = Wallet()
            for post in acc.subpostings():
                if post.actual_date <= cdate:  ## Note: shouldn't this be "<" ?
                    balance += post.amount

            # Remove the amounts that we're not supposed to be checking from the
            # actual balance.
            balance = balance.mask_commodity(chk.commodity)

            if chk.flag is None:
                chk.flag = '*' if (balance == expected) else '!'
            chk.balance = balance

            # Note: it is contentious whether we should also round the number
            # specified in the check before making the comparison.
            chk.diff = (balance - expected).round()
            if not chk.passed():
                se = expected or 'nothing'
                sb = balance or 'nothing'
                diff = chk.diff or 'nothing'
                ledger.log(ERROR,
                           ("Check failed at  %s  %s :\n"
                            "  Expecting: %s\n"
                            "  Got:       %s\n"
                            "  Diff: %s\n") %
                           (cdate, acc.fullname, se, sb, diff), chk)

            # Update ranges (no matter what).
            acc.check_min = min(acc.check_min, cdate) if acc.check_min else cdate
            acc.check_max = max(acc.check_max, cdate) if acc.check_max else cdate

    def account_checks(self, acc):
        "Return the list of checks for the given account."
        return sorted(chk for chk in self.checks if chk.account is acc)



class DefineAccountDirective(object):
    """
    Declare a valid account and check that all the postings only use declared
    valid acccounts.
    """

    name = 'defaccount'
    prio = 1

    mre = re.compile(("\s*(D[re]|Cr)\s+(%(account)s)\s+"
                      "((?:%(commodity)s(?:,\s*)?)*)\s*$") %
                     {'account': Ledger.account_re.pattern,
                      'commodity': Ledger.commodity_re.pattern})

    def __init__(self, ledger):
        self.definitions = {}
        self.ledger = ledger

    def parse(self, line, filename, lineno):
        mo = self.mre.match(line)
        if not mo:
            self.ledger.log(CRITICAL, "Invalid defaccount directive: %s" % line,
                            (filename, lineno))
            return

        isdebit = (mo.group(1) in ('Dr', 'De'))
        account = self.ledger.get_account(mo.group(2), create=1, incrcount=False)
        commodities = mo.group(3).split(',') if mo.group(3) else None
        if account in self.definitions:
            self.ledger.log(CRITICAL,
                            "Duplicate account definition: %s" % account.fullname,
                            (filename, lineno))
        account.commodities = commodities
        account.isdebit = isdebit
        self.definitions[account] = (filename, lineno)

    def apply(self):
        ledger = self.ledger

        # Compute a set of valid account fullnames.
        valid_accounts = set(x.fullname for x in self.definitions)

        # Check that all the postings have a valid account name.
        for post in ledger.postings:
            accname = post.account.fullname
            if accname not in valid_accounts:
                ledger.log(ERROR, "Invalid account name '%s'." % accname, post)

        # Check for unused accounts.
        for acc, (filename, lineno) in sorted(self.definitions.iteritems()):
            if not acc.isused():
                ledger.log(WARNING, "Account %s is unused." % acc.fullname,
                           (filename, lineno))

        # Check that none of the account's postings are in an invalid commodity.
        for accname in valid_accounts:
            acc = self.ledger.get_account(accname)
            if not acc.commodities:
                continue
            for post in acc.postings:
                comms = post.amount.keys()
                if not comms:
                    continue # Empty amount for posting, ignore it.
                comm = comms[0]
                if comm not in acc.commodities:
                    ledger.log(ERROR, "Invalid commodity '%s' for account '%s'." %
                               (comm, accname), post)



class DefineCommodityDirective(object):
    """
    Define a commodity name.
    """

    name = 'defcomm'
    prio = 1

    market_re = re.compile('"?"?')

    mre = re.compile("\s*%(commodity)s\s+([A-Za-z-][A-Za-z0-9:.-]*)\s+(.+)\s*$" %
                     {'commodity': Ledger.commodity_re.pattern})

    def __init__(self, ledger):
        self.commnames = {}
        self.ledger = ledger

    def parse(self, line, filename, lineno):
        mo = self.mre.match(line)
        if not mo:
            self.ledger.log(CRITICAL, "Invalid defcomm directive: %s" % line,
                            (filename, lineno))
            return

        market, name = mo.group(2, 3)
        if market == '-':
            market = None
        self.commnames[mo.group(1)] = (market, name)

    def apply(self):
        pass



class BeginTagDirective(object):
    """
    Set a page attribute to the transactions between beginpage and endpage
    directives.
    """
    name = 'begintag'
    prio = 1

    def __init__(self, ledger):
        self.ledger = ledger

    def parse(self, line, filename, lineno):
        ledger = self.ledger

        tag = line.strip()
        ledger.current_tags = list(ledger.current_tags) + [tag]
        # Note: it is important to make a copy of the list of current tags
        # stored in 'ledger.current_tags' because this list is getting referenced
        # directly by postings as the file is being read.

    def apply(self):
        # Nothing to do: the tag has been set on the transaction objects during
        # parsing.
        pass

class EndTagDirective(BeginTagDirective):
    name = 'endtag'

    def parse(self, line, filename, lineno):
        ledger = self.ledger
        tag = line.strip()
        assert tag in ledger.current_tags, (tag, ledger.current_tags)
        ledger.current_tags = list(ledger.current_tags)
        ledger.current_tags.remove(tag)
        # copying 'ledger.current_tags', see above, same reason.





class AutoPad(object):
    "Representation of a @pad directive (and its temporary data)."
    def __init__(self, pdate, acc_target, acc_offset, filename, lineno):
        self.pdate = pdate
        self.acc_target = acc_target
        self.acc_offset = acc_offset
        self.filename, self.lineno = filename, lineno

        # The set of commodities that have been adjusted for this pad. (This is
        # used to make only one check per commodity affect each pad.)
        self.adjusted = dict() # commodity -> check
        self.wallet = Wallet()



class AutoPadDirective(object):
    """
    Automatically insert an opening balance before any of the transactions
    before an existing account, to make the first check work. Insert a directive
    like this to automatically insert an entry to balance an account::

      @openbal  Assets:Current:RBC:Checking  Equity:Opening-Balances

    This inserts a transaction before the first transaction in the checking
    account and offsets it with the transaction in the opening balances.
    """

    name = 'pad'
    prio = 2

    flag = 'A'

    mre = re.compile("\s*(?:%(date)s)\s+(%(account)s)\s+(%(account)s)\s*$" %
                     {'date': Ledger.date_re.pattern,
                      'account': Ledger.account_re.pattern})

    def __init__(self, ledger, checkdir):
        self.pads = []
        self.ledger = ledger
        self.checkdir = checkdir

        # A record of the transactions we added.
        self.transactions = []

    def parse(self, line, filename, lineno):
        mo = self.mre.match(line)
        if not mo:
            self.ledger.log(CRITICAL, "Invalid pad directive:\n %s" % line.strip(),
                            (filename, lineno))
            return

        pdate = date(*map(int, mo.group(1, 2, 3)))
        try:
            acc_target = self.ledger.get_account(mo.group(4))
            acc_offset = self.ledger.get_account(mo.group(5))
        except KeyError, e:
            self.ledger.log(CRITICAL, "Invalid account: %s" % e,
                            (filename, lineno))
            return

        pad = AutoPad(pdate, acc_target, acc_offset, filename, lineno)
        self.pads.append(pad)

    def apply(self):
        ledger = self.ledger

        # Arrange pads by target account, then sort them, and deal with them
        # thereafter as such.
        padacc = defaultdict(list)
        for x in self.pads:
            padacc[x.acc_target].append(x)

        for acc_target, pads in padacc.iteritems():

            # Get the list of checks for this account.
            checks = self.checkdir.account_checks(acc_target)
            if not checks:
                continue

            # Merge the account's postings, pads and check and sort them
            # together using a Schwartzian transform with appropriate priorities
            # to disambiguate cases where the date is equal.
            slist = ([((pad.pdate, 0), pad) for pad in pads] +
                     [((chk.cdate, 1), chk) for chk in checks] +
                     [((post.actual_date, 2), post)
                      for post in acc_target.subpostings()])
            slist.sort()

            # The current pad, and a set of the commodities that have already
            # been adjusted for it.
            pad = None
            balance = Wallet()
            for sortkey, x in slist:

                if isinstance(x, AutoPad):
                    # Make this pad the current pad.
                    pad = x

                elif isinstance(x, Check):
                    # Ajust the current pad to reflect this check, if it has not
                    # already been adjusted.
                    chk = x
                    if (pad is not None and
                        chk.commodity not in pad.adjusted):

                        pad.adjusted[chk.commodity] = chk
                        diff = chk.expected - balance
                        balamount = diff.get(chk.commodity)
                        if balamount:
                            pad.wallet[chk.commodity] = balamount

                            # Mark check as having been padded.
                            chk.flag = self.flag

                elif isinstance(x, Posting):
                    post = x
                    balance += post.amount

                else:
                    raise ValueError("Invalid type in list.")

            for pad in pads:
                if not pad.wallet:
                    logging.warning("Ununsed pad at %s:%d" %
                                    (pad.filename, pad.lineno))
                    continue

                txn = Transaction()
                ledger.transactions.append(txn)
                txn.actual_date = txn.effective_date = pad.pdate
                txn.filename = pad.filename
                txn.lineno = -1
                txn.ordering = 0
                txn.flag = self.flag
                txn.payee = self.__class__.__name__

                chkstr = ', '.join('%s:%d' % (chk.filename, chk.lineno)
                                   for chk in pad.adjusted.itervalues())
                txn.narration = u'Automatic opening balance for checks: %s' % chkstr


                for com, num in pad.wallet.iteritems():
                    for acc, anum in ((pad.acc_target, num),
                                      (pad.acc_offset, -num)):

                        # Let's install one posting per commodity, because the input
                        # format does not allow more than that either (it would
                        # work, but we just don't want to break the
                        # 1-posting/1-commodity hypothesis).
                        post = Posting(txn)
                        post.filename, post.lineno = pad.filename, pad.lineno
                        post.actual_date = post.effective_date = txn.actual_date
                        post.ordering = 0
                        post.flag = self.flag
                        post.account_name = acc.fullname
                        post.account = acc
                        txn.postings.append(post)
                        ledger.postings.append(post)
                        acc.postings.append(post)
                        post.amount = post.cost = Wallet(com, anum)

                ledger.log(INFO, "Inserting automatic padding for %s at %s for %s" %
                           (acc_target.fullname, pad.pdate.isoformat(), pad.wallet),
                           (pad.filename, pad.lineno))



class DefvarDirective(object):
    """
    A directive that can be used to define generic parameters for specialized
    applications. For example, the import scripts make use of this directive in
    order to fetch some custom information from the ledger file. The format of
    the variables is generic::

        @defvar MODULE VARNAME VALUE

    VALUE is only interpreted as a string. There can be multiple definitions of
    the same variable (they are accumulated as a list).
    """

    name = 'var'
    prio = 2000

    mre = re.compile("\s*(?P<module>[a-zA-Z0-9]+)"
                     "\s+(?P<varname>[a-zA-Z0-9]+)"
                     "\s+(?P<value>.+)\s*$")

    def __init__(self, ledger):

        self.modules = defaultdict(lambda: defaultdict(list))
        self.ledger = ledger

    def parse(self, line, filename, lineno):
        mo = self.mre.match(line)
        if not mo:
            self.ledger.log(CRITICAL, "Invalid check directive: %s" % line,
                            (filename, lineno))
            return

        self.modules[mo.group('module')][mo.group('varname')].append(
            mo.group('value'))

    def apply(self):
        pass # Nothing to do--the modules do the parsing themselves.

def read_ofx_accounts_map(ledger):
    """
    Process account mapping declarations from the ledger file and return a
    mapping.
    """
    m = {}
    vardir = ledger.directives['var']
    accids = vardir.modules['ofx']['accid']
    for decl in accids:
        accid, accname = [x.strip() for x in decl.split()]
        try:
            acc = ledger.get_account(accname)
        except KeyError:
            raise SystemExit(
                "Could not find account %s\n  @var declaration: %s\n" %
                (accname, decl))
        m[accid] = acc
    return m



class LocationDirective(object):
    """
    A directive that can be used to provide an update on the physical location
    of the main spender in a personal account. This is used to calculate the
    number of days spent in each country for each civil year, in order to

    - declare it to customs if needed (with precision)
    - declare it to the Canadian medicare plans.
    """

    name = 'location'
    prio = 2000

    mre = re.compile(("\s*(?:%(date)s)"
                      "\s+(?P<city>[^,]+)\s*,"
                      "\s+(?P<country>.+)\s*$") %
                     {'date': Ledger.date_re.pattern})

    def __init__(self, ledger):
        self.locations = []
        self.ledger = ledger

    def parse(self, line, filename, lineno):
        mo = self.mre.match(line)
        if not mo:
            self.ledger.log(CRITICAL, "Invalid location directive: %s" % line,
                            (filename, lineno))
            return

        ldate = date(*map(int, mo.group(1, 2, 3)))
        self.locations.append( (ldate, mo.group(4), mo.group(5)) )

    def apply(self):
        pass

        ## # If the ledger appears to be current, append a date for today in order
        ## # to count those days as well.
        ## if not self.locations:
        ##     return
        ## lastloc = sorted(self.locations)[-1]
        ## today = date.today()
        ## if lastloc[0] < today:
        ##     self.locations.append( (today, lastloc[1], lastloc[2]) )


class PriceDirective(object):
    """
    Define prices and exchange rates between two commodities. This is used to
    build an internal price history database that can be used for other
    purposes, for example, converting all values from one commodity to another
    in the reports, and for computing capital gains in a currency different from
    the underlying's rice currency.

    Note that we don't include this feature with the intention of providing
    detailed time-series of prices. Instead, we expect that the user will simply
    enter some of the prices, where relevant for his application.
    """

    name = 'price'
    prio = 100

    mre = re.compile(("\s*(?:%(date)s)"
                      "\s+(?:%(commodity)s)"
                      "\s+%(amount)s"
                      ) %
                     {'date': Ledger.date_re.pattern,
                      'commodity': Ledger.commodity_re.pattern,
                      'amount': Ledger.amount_re.pattern})

    def __init__(self, ledger):
        self.ledger = ledger

        # A map of (from, to) commodity pairs to PriceHistory objects.
        self.prices = defaultdict(PriceHistory)

    def parse(self, line, filename, lineno):
        mo = self.mre.match(line)
        if not mo:
            self.ledger.log(CRITICAL, "Invalid price directive: %s" % line,
                            (filename, lineno))
            return

        ldate = date(*map(int, mo.group(1, 2, 3)))
        base, quote = mo.group(4,6)
        rate = Decimal(mo.group(5))
        phist = self.prices[(base, quote)]
        if phist.finddate(ldate) is not None:
            self.ledger.log(ERROR, "Duplicate price: %s" % line,
                            (filename, lineno))
            return
        else:
            phist.append( (ldate, rate) )
            phist.sort()

    def apply(self):
        # FIXME: This ends up happening too late, we need it beforehand.
        # Sort all the price histories only once.
        for phist in self.prices.itervalues():
            phist.sort()

    def getrate(self, base, quote, date_):
        return self.prices[(base, quote)].interpolate(date_)


class PriceHistory(list):
    """ An object that can accumulate samples of price history and calculate
    interpolated values."""

    def __init__(self):
        list.__init__(self)
        self.m = {}

    def append(self, el):
        assert isinstance(el, tuple)
        assert isinstance(el[0], date)
        assert isinstance(el[1], Decimal)
        self.m[el[0]] = el[1]
        return list.append(self, el)

    def finddate(self, d):
        "Return the rate at precisely date 'd'."
        return self.m.get(d, None)

    def interpolate(self, date_):
        "Linear interpolation of the rate, given our samples."
        if len(self) == 0:
            raise IndexError("Cannot interpolate empty price history.")
        idx = bisect_left(self, (date_, None))

        # Edge cases.
        res = None
        if idx == len(self):
            d, r = self[idx-1]
            res = r
        elif idx == 0:
            d, r = self[0]
            res = r

        # Interpolate between the two closest dates.
        if res is None:
            idx -= 1
            d1, r1 = self[idx]
            d2, r2 = self[idx+1]
            assert d1 < date_, (d1, date_)
            assert d2 >= date_, (d2, date_)
            alpha = Decimal((date_ - d1).days) / Decimal((d2 - d1).days)
            res = (1-alpha)*r1 + (alpha)*r2

        return res




########NEW FILE########
__FILENAME__ = test_balances
"""
Test the computation of the balance sheet.
"""

## FIXME: TODO

########NEW FILE########
__FILENAME__ = test_capgains
"""
Test a case of capital gains booking.
"""

# stdlib imports
import sys
from datetime import date
from decimal import Decimal

# beancount imports
from beancount.ledger import Ledger
from beancount.wallet import Wallet
from beancount.beantest import ledger_str



class TestCapitalGains(object):

    def_accounts = """
@defaccount De Assets:Bank
@defaccount De Assets:Broker
@defaccount Cr Income:CapitalGains
@defaccount De Expenses:Commissions
@defaccount De Expenses:Deductible-Costs
"""

    def test_custom_cost(self):

        # Unbooked capital gains.
        lgr = ledger_str(self.def_accounts + """

2008-01-10 * Bought some shares.
  Assets:Broker              10 AAPL @ 120.00 USD
  Assets:Bank

2008-01-10 * Sold some shares.
  Assets:Broker              -10 AAPL @ 125.00 USD
  Assets:Bank

""", 'unbooked-gains')
        assert len(lgr.transactions) == 2
        assert lgr.transactions[0].postings[1].amount == Wallet('-1200 USD')
        assert lgr.transactions[1].postings[1].amount == Wallet('1250 USD')


        # Forgotten capital gains.
        lgr = ledger_str(self.def_accounts + """

2008-01-10 * Bought some shares.
  Assets:Broker              10 AAPL @ 120.00 USD
  Assets:Bank

2008-01-11 * Sold some shares.
  Assets:Broker              -10 AAPL {120.00 USD} @ 125.00 USD
  Assets:Bank

""", 'forgot-gains')
        assert len(lgr.transactions) == 2
        assert lgr.transactions[0].postings[1].amount == Wallet('-1200 USD')
        assert lgr.transactions[1].postings[1].amount == Wallet('1200 USD')


    def test_custom_cost2(self):

        # Booked capital gains.
        lgr = ledger_str(self.def_accounts + """

2008-01-10 * Bought some shares.
  Assets:Broker              10 AAPL @ 120.00 USD
  Assets:Bank          -1200 USD

2008-01-11 * Sold some shares.
  Assets:Broker              -10 AAPL {120.00 USD} @ 125.00 USD
  Assets:Bank           1250 USD
  Income:CapitalGains      -50 USD

""", 'booked-gains')
        assert len(lgr.transactions) == 2
        assert lgr.transactions[1].postings[0].cost == Wallet('-1200 USD')
        assert lgr.transactions[1].postings[1].amount == Wallet('1250 USD')
        assert lgr.transactions[1].postings[2].amount == Wallet('-50 USD')


    def test_with_commissions(self):

        # Booked capital gains.
        lgr = ledger_str(self.def_accounts + """

2008-01-10 * Bought some shares.
  Assets:Broker              10 AAPL @ 120.00 USD
  Expenses:Commissions      9.95 USD
  Assets:Bank          -1209.95 USD

2008-01-11 * Sold some shares.
  Assets:Broker              -10 AAPL {120.00 USD} @ 125.00 USD
  Assets:Bank            1240.05 USD      ;; actual amount deposited (easy to find on statement)
  Expenses:Commissions      9.95 USD      ;; actual commission for closing the trade
  Income:CapitalGains                     ;; automatically computed gain (from share cost above)
  [Income:CapitalGains]       19.90 USD   ;; offset for commissions to open and close this trade, manually entered
  [Expenses:Deductible-Costs]             ;; an account that track costs for closed trades

""", 'booked-gains')
        assert len(lgr.transactions) == 2

        commisions = 2*Decimal('9.95')
        for accname, amount in (
            ('Assets:Bank', Decimal('50')-commisions),
            ('Expenses:Commissions', commisions),
            ('Income:CapitalGains', -(Decimal('50')-commisions)),
            ):
            assert (lgr.get_account(accname).balances['total'] ==
                    Wallet('USD', amount))









########NEW FILE########
__FILENAME__ = test_cost
"""
Test cost balancing.
"""

# stdlib imports
import sys
from datetime import date

# beancount imports
from beancount.ledger import Ledger
from beancount.wallet import Wallet
from beancount.beantest import ledger_str



class TestCostBalancing(object):

    def_accounts = """
@defaccount De Assets:Bank
@defaccount De Income:Salary
@defaccount De Expenses:TripPlan
@defaccount Cr Income:Planning
@defaccount Cr Income:CapGains
"""

    def test_simple(self):

        # Simple transaction.
        lgr = ledger_str(self.def_accounts + """

2008-01-10 * Bought some shares
  Assets:Bank               100.00 USD
  Income:Salary

""", 'simple')

        assert len(lgr.transactions) == 1
        txn = lgr.transactions[0]
        assert txn.postings[0].amount == Wallet('100 USD')
        assert lgr.get_account('Assets:Bank').balances['total'] == Wallet('100 USD')
        assert lgr.get_account('Income:Salary').balance['total'] == Wallet('-100 USD')


        # Empty unbalanced virtual posting should fail.
        lgr = ledger_str(self.def_accounts + """

2008-01-10 * Bought some shares
  Assets:Bank               100.00 USD
  Income:Salary            -100.00 USD
  (Expenses:TripPlan)

""", 'virtempty')
        assert len(lgr.transactions) == 1
        txn = lgr.transactions[0]
        assert len(txn.postings) == 3
        assert txn.postings[2].amount == Wallet()
## FIXME: how do we assert that there was a warning here?


        # Normal and virtual postings should balance independently.
        lgr = ledger_str(self.def_accounts + """

2008-01-10 * Bought some shares
  Assets:Bank              170.00 USD
  Income:Salary
  [Income:Planning]         42.00 USD
  [Expenses:TripPlan]

""", 'twoempty')
        assert len(lgr.transactions) == 1
        txn = lgr.transactions[0]
        assert len(txn.postings) == 4
        for i, amt in enumerate(('170 USD', '-170 USD',
                                 '42 USD', '-42 USD')):
            assert txn.postings[i].amount == Wallet(amt)



        # Normal and virtual postings should balance independently.
        lgr = ledger_str(self.def_accounts + """

2008-01-10 * 
  Assets:Bank              170.00 USD
  Income:Salary            169.00 USD

""", 'twoempty')
        assert len(lgr.transactions) == 1
        txn = lgr.transactions[0]
## FIXME: how do we assert an error here?




    def test_price(self):

        # Normal price.
        lgr = ledger_str(self.def_accounts + """

2008-01-10 * Bought some shares
  Assets:Broker               10 AAPL @ 121.00 USD
  Assert:Checking

""", 'normal-price')

        assert len(lgr.transactions) == 1
        txn = lgr.transactions[0]
        assert txn.postings[0].amount == Wallet('10 AAPL')
        assert txn.postings[0].price == Wallet('121 USD')
        assert txn.postings[0].cost == Wallet('1210 USD')
        assert lgr.get_account('Assets:Broker').total == Wallet('10 AAPL')
        assert lgr.get_account('Assert:Checking').total == Wallet('-1210 USD')


        # Total price.
        lgr = ledger_str(self.def_accounts + """

2008-01-10 * Bought some shares
  Assets:Broker               10 AAPL @@ 1210.00 USD
  Assert:Checking

""", 'total-price')

        assert len(lgr.transactions) == 1
        txn = lgr.transactions[0]
        assert txn.postings[0].amount == Wallet('10 AAPL')
        assert txn.postings[0].price == Wallet('121 USD')
        assert txn.postings[0].cost == Wallet('1210 USD')
        assert lgr.get_account('Assets:Broker').total == Wallet('10 AAPL')
        assert lgr.get_account('Assert:Checking').total == Wallet('-1210 USD')


    def test_explicit_cost(self):

        # Cost-per-share.
        lgr = ledger_str(self.def_accounts + """

2008-01-10 * Bought some shares
  Assets:Broker               10 AAPL {111.00 USD} @ 121.00 USD
  Assert:Checking

""", 'cost-per-share')

        assert len(lgr.transactions) == 1
        txn = lgr.transactions[0]
        assert txn.postings[0].amount == Wallet('10 AAPL')
        assert txn.postings[0].cost == Wallet('1110 USD')
        assert lgr.get_account('Assets:Broker').total == Wallet('10 AAPL')
        assert lgr.get_account('Assert:Checking').total == Wallet('-1110 USD')


        # Total cost.
        lgr = ledger_str(self.def_accounts + """

2008-01-10 * Bought some shares
  Assets:Broker               10 AAPL {{1110.00 USD}} @ 121.00 USD
  Assert:Checking

""", 'cost-per-share')

        assert len(lgr.transactions) == 1
        txn = lgr.transactions[0]
        assert txn.postings[0].amount == Wallet('10 AAPL')
        assert txn.postings[0].cost == Wallet('1110 USD')
        assert lgr.get_account('Assets:Broker').total == Wallet('10 AAPL')
        assert lgr.get_account('Assert:Checking').total == Wallet('-1110 USD')


    def test_truestory(self):

        # Some other examples.
        lgr = ledger_str(self.def_accounts + """

2007-12-19 * Redemption
  Assets:Broker                 -29.4650 "AIM681" {{-326.62 CAD}} @ 11.197 CAD
  Assets:Checking                    329.92 CAD   ; adjusted cost base
  Income:CapGains  

""", 'true-story-1')

        assert len(lgr.transactions) == 1
        txn = lgr.transactions[0]
        assert lgr.get_account('Income:CapGains').total == Wallet('-3.30 CAD')





########NEW FILE########
__FILENAME__ = test_padding
"""
Test the directive which automatically inserts a transaction to pad for
surrounding checks.
"""

# stdlib imports
import sys
from datetime import date

# beancount imports
from beancount.ledger import Ledger
from beancount.wallet import Wallet
from beancount.beantest import ledger_str



class TestAutoPad(object):

    def_accounts = """
@defaccount De Assets:Bag
@defaccount Cr Equity:Opening-Balances
"""

    def test_padding(self):

        # Testing padding before the first check.
        lgr = ledger_str(self.def_accounts + """
@pad 2008-04-10  Assets:Bag  Equity:Opening-Balances

2008-04-15 * Misc
  Assets:Bag             10.00 USD
  Equity:Opening-Balances

@check 2008-04-20  Assets:Bag  1203.23 USD
        """, 'before')
        assert len(lgr.transactions) == 2
        txn = filter(lambda x: x.flag == 'A', lgr.transactions)[0]
        assert txn.actual_date == date(2008, 4, 10)
        assert txn.postings[0].amount == Wallet('1193.23 USD')


        # Testing padding between checks before a transaction.
        lgr = ledger_str(self.def_accounts + """
2008-04-01 * Misc
  Assets:Bag             43.00 USD
  Equity:Opening-Balances

@check 2008-04-20  Assets:Bag  43.00 USD

@pad 2008-04-22  Assets:Bag  Equity:Opening-Balances

2008-04-23 * Misc
  Assets:Bag             10.00 USD
  Equity:Opening-Balances

@check 2008-04-25  Assets:Bag  64.00 USD
""", 'between1')
        assert len(lgr.transactions) == 3
        txn = filter(lambda x: x.flag == 'A', lgr.transactions)[0]
        assert txn.actual_date == date(2008, 4, 22)
        ## print txn
        assert txn.postings[0].amount == Wallet('11.00 USD')



        # Test padding between checks between transactions.
        lgr = ledger_str(self.def_accounts + """
2008-04-01 * Misc
  Assets:Bag             21.00 USD
  Equity:Opening-Balances

@check 2008-04-20  Assets:Bag  21.00 USD

2008-04-21 * Misc
  Assets:Bag             10.00 USD
  Equity:Opening-Balances

@pad 2008-04-22  Assets:Bag  Equity:Opening-Balances

2008-04-23 * Misc
  Assets:Bag             10.00 USD
  Equity:Opening-Balances

@check 2008-04-24  Assets:Bag  53.01 USD
""", 'between2')
        assert len(lgr.transactions) == 4
        txn = filter(lambda x: x.flag == 'A', lgr.transactions)[0]
        assert txn.actual_date == date(2008, 4, 22)
        assert txn.postings[0].amount == Wallet('12.01 USD')


        # Test padding between checks after transactions.
        lgr = ledger_str(self.def_accounts + """

2008-04-01 * Misc
  Assets:Bag             43.00 USD
  Equity:Opening-Balances

@check 2008-04-20  Assets:Bag  43.00 USD

2008-04-23 * Misc
  Assets:Bag             10.00 USD
  Equity:Opening-Balances

@pad 2008-04-22  Assets:Bag  Equity:Opening-Balances

@check 2008-04-25  Assets:Bag  64.02 USD
""", 'between3')
        assert len(lgr.transactions) == 3
        txn = filter(lambda x: x.flag == 'A', lgr.transactions)[0]
        assert txn.actual_date == date(2008, 4, 22)
        assert txn.postings[0].amount == Wallet('11.02 USD')


        # Test padding between after checks (should fail).
        lgr = ledger_str(self.def_accounts + """
2008-01-01 * Misc
  Assets:Bag             17.00 USD
  Equity:Opening-Balances

@check 2008-04-20  Assets:Bag  17.00 USD

@pad 2008-04-21  Assets:Bag  Equity:Opening-Balances
""", 'after')
        assert len(lgr.transactions) == 1


        # Test padding for an empty amount: should be no padding at all.
        lgr = ledger_str(self.def_accounts + """
2008-01-01 * Misc
  Assets:Bag             43.00 USD
  Equity:Opening-Balances

@check 2008-04-20  Assets:Bag  43.00 USD

@pad 2008-04-22  Assets:Bag  Equity:Opening-Balances

2008-04-23 * Misc
  Assets:Bag             10.00 USD
  Equity:Opening-Balances

@check 2008-04-25  Assets:Bag  53.00 USD
""", 'empty1')
        assert len(lgr.transactions) == 2
        assert not filter(lambda x: x.flag == 'A', lgr.transactions)


        lgr = ledger_str(self.def_accounts + """
@pad 2008-04-12  Assets:Bag  Equity:Opening-Balances
@check 2008-04-20  Assets:Bag  0.00 USD
""", 'empty2')
        assert len(lgr.transactions) == 0


    def test_manycomm(self):
        "Test padding in the presence of many commodities."

        lgr = ledger_str(self.def_accounts + """
@pad 2008-01-01  Assets:Bag  Equity:Opening-Balances

@check 2008-04-02  Assets:Bag    1 CAD
@check 2008-04-02  Assets:Bag    2 USD
@check 2008-04-02  Assets:Bag    3 AAPL
""", 'manycomm')
        assert len(lgr.transactions) == 1
        txn = lgr.transactions[0]
        w = Wallet('1 CAD, 2 USD, 3 AAPL')
        assert txn.postings[0].amount == w
        assert txn.postings[1].amount == -w



########NEW FILE########
__FILENAME__ = test_parsing


def __test_posting_regexp():

    test_posting_lines = """\
  Expenses:Financial:Commissions                                           24.88 USD
  Assets:Investments:RBC-Broker:Account-RSP                      86.132 "NBC860"
  Assets:Investments:RBC-Broker:Account-US                              -130.00 IWM  @ 71.2701 USD
  Assets:Investments:RBC-Broker:Account-US                              9255.05 USD
  Expenses:Financial:Commissions                                            9.95 USD
  ! Expenses:Financial:Fees
    """

    for line in test_posting_lines.splitlines():
        print
        print line
        mo = posting_re.match(line)
        print (mo.groups() if mo else None)


########NEW FILE########
__FILENAME__ = test_pricehist
"""
Test price history interpolation.
"""

# stdlib imports
from datetime import date
from decimal import Decimal

# beancount imports
from beancount.ledger import PriceHistory



class TestPriceHistory(object):

    def test_phist(self):
        phist = PriceHistory()
        phist.append( (date(2008, 2, 3), Decimal('1.1567')) )
        phist.append( (date(2008, 2, 18), Decimal('1.2123')) )
        phist.append( (date(2008, 2, 26), Decimal('1.4023')) )

        assert phist.interpolate(date(2008, 2, 2)) == Decimal('1.1567')
        assert phist.interpolate(date(2008, 2, 3)) == Decimal('1.1567')
        assert phist.interpolate(date(2008, 2, 4)) > Decimal('1.1567')
        assert phist.interpolate(date(2008, 2, 17)) < Decimal('1.2123')
        assert phist.interpolate(date(2008, 2, 18)) == Decimal('1.2123')
        assert phist.interpolate(date(2008, 2, 19)) > Decimal('1.2123')
        assert phist.interpolate(date(2008, 2, 25)) < Decimal('1.4023')
        assert phist.interpolate(date(2008, 2, 26)) == Decimal('1.4023')
        assert phist.interpolate(date(2008, 2, 27)) == Decimal('1.4023')



########NEW FILE########
__FILENAME__ = test_wallet
"""
Wallet arithmetic tests.
"""

# stdlib imports
from decimal import Decimal

# beancount imports
from beancount.wallet import Wallet



class TestWallet(object):

    def test_simple(self):
        "Simple wallet tests."

        w = Wallet()
        assert len(w) == 0

        # Test constructing with keywords.
        w = Wallet(CAD='5.688')
        assert len(w) == 1
        assert w['CAD'] == Decimal('5.688')

        # Test special shortcut constructor.
        w = Wallet('CAD', '5.688')
        assert len(w) == 1
        assert w['CAD'] == Decimal('5.688')

        # Test special shortcut constructor.
        w = Wallet('1 CAD, 2 USD')
        assert len(w) == 2
        assert w['CAD'] == Decimal('1')
        assert w['USD'] == Decimal('2')

        # Test copy constructor.
        w2 = Wallet(w)
        assert w is not w2
        assert w == w2

        # Test copy method.
        ww = w.copy()
        assert isinstance(ww, Wallet), ww

    def test_operators(self):
        "Test some of the basic operations on wallets."

        w1 = Wallet(CAD='17.1')
        w2 = Wallet(CAD='0.9')
        assert w1 + w2 == Wallet(CAD='18.0')
        assert w1 - w2 == Wallet(CAD='16.2')
        assert w1 * 2 == Wallet(CAD='34.2')
        assert w1 / 2 == Wallet(CAD='8.55')

    def test_round(self):
        "Test rounding."

        w = Wallet(CAD='17.1343843', USD='83.42434', EUR='6.237237232')
        mprecision = dict((('USD', Decimal('.01')),
                           ('EUR', Decimal('.0001')),
                           ('JPY', Decimal('.00001')),
                           (None, Decimal('.1')),
                           ))
        wr = w.round(mprecision)
        assert wr['EUR'] == Decimal('6.2372')
        assert wr['USD'] == Decimal('83.42')
        assert wr['CAD'] == Decimal('17.10')

    def test_equality(self):
        "Test equality predicates."

        w1 = Wallet(CAD='17.1343843')
        w1p = Wallet(CAD='17.1343843')
        w2 = Wallet(USD='83.42434')
        w3 = Wallet(CAD='17.8888')
        assert w1 == w1p
        assert w2 != w1
        assert w2 != w1p
        assert w1 != w3

    def test_neg(self):
        "Test negative value."

        w = Wallet(CAD='17.1343843',
                   USD='83.42434')
        assert -w == Wallet(CAD='-17.1343843',
                            USD='-83.42434')

    def test_only(self):
        "Test the only filter."

        w = Wallet(CAD='17.1343843',
                   USD='83.42434')
        assert w.only('CAD') == Wallet(CAD='17.1343843')


    def test_price(self):
        
        w = Wallet(AAPL='20')
        w.price('AAPL', 'USD', Decimal('10'))
        assert w == Wallet(USD='200')
        
        w = Wallet(AAPL='20', MSFT='10.1')
        w.price('AAPL', 'USD', Decimal('10'))
        assert w == Wallet(USD='200', MSFT='10.1')

    def test_split(self):

        w = Wallet()
        wp, wn = w.split()
        assert w == (wp + wn)

        w = Wallet('10 USD')
        wp, wn = w.split()
        assert w == (wp + wn)
        
        w = Wallet('-10 CAD')
        wp, wn = w.split()
        assert w == (wp + wn)

        w = Wallet(USD='10', CAD='-10')
        wp, wn = w.split()
        assert w == (wp + wn)

    def test_convert(self):
        conv = [('INR', 'CAD', 1/Decimal('40'))]

        w = Wallet()
        assert w.convert(conv) == w
        
        w = Wallet('10 USD')
        assert w.convert(conv) == w
        
        w = Wallet('10 INR')
        assert w.convert(conv) == Wallet('0.25 CAD')

        w = Wallet('1600 INR')
        assert w.convert(conv) == Wallet('40 CAD')

    def test_nbthings(self):
        w = Wallet()
        w['USD'] = Decimal('4.1')
        w['JPY'] = Decimal('17.0')
        assert w.nbthings() == Decimal('21.1')


########NEW FILE########
__FILENAME__ = timeparse
"""
Ad-hoc hand-hacked parser that accepts some time specs.
This parser accepts the following syntaxes (examples)::

  A single year:    2007
  A month:          2007 10, Oct 2007, 10-2007
  An interval:      from apr 2006 to: may 2006
  Declared dates:   Q2 2007
   
"""

# stdlib imports
import re, calendar
from datetime import *

__all__ = ('parse_time',)


monthnames = [x.lower() for x in calendar.month_name]

def match_month(name):
    mmatches = [i for (i, n) in enumerate(monthnames) if n.startswith(name)]
    if len(mmatches) == 1:
        return mmatches[0]

def parse_time(timestr):
    timestr = timestr.strip()

    interval = None
    
    # Try to parse an interval.
    mo = re.match('from(?::\s*|\s+)(.*)\s+to(?::\s*|\s+)(.*)$', timestr)
    if mo:
        from_str, to_str = mo.group(1, 2)
        x = parse_one_time(from_str)
        if x is not None:
            from_ = x[0]
            x = parse_one_time(to_str)
            if x is not None:
                to_ = x[0]
                interval = (from_, to_)

    # Try to parse an interval.
    mo = re.match('(?:to|until)(?::\s*|\s+)(.*)$', timestr)
    if mo:
        to_str = mo.group(1)
        x = parse_one_time(to_str)
        if x is not None:
            from_ = date(1900, 1, 1)
            to_ = x[0]
            interval = (from_, to_)

    # Finally try to parse a single time event (which will be interpreted as an
    # interval).
    if interval is None:
        interval = parse_one_time(timestr)

    if interval is None:
        raise ValueError("Unrecognized time spec: %s" % timestr)
    if interval[0] >= interval[1]:
        raise ValueError("Empty or negative interval: %s" % timestr)

    return interval
    
today = date.today()

def parse_one_time(timestr):
    """ Parse a single instant in time and return two dates: the corresponding
    parsed date, and a date for the next interval implied by the single date.
    For example, if '2007' is given (2007-01-01, 2008-01-01) is returned. If
    '2007-04' is given (2007-04-01, 2008-05-01) is returned."""

    if timestr == 'now':
        return (today, today + timedelta(days=1))
    
    mo = re.match('(\d\d\d\d)(?:\s+|\s*[-/]\s*)(\d\d)(?:\s+|\s*[-/]\s*)(\d\d)$', timestr)
    if mo:
        year, month, day = map(int, mo.group(1, 2, 3))
        d1 = date(year, month, day)
        d2 = date(year, month, day) + timedelta(days=1)
        return (d1, d2)

    mo = re.match('(\d\d\d\d)(?:\s+|\s*[-/]\s*)(\d\d)$', timestr)
    if mo:
        year, month = map(int, mo.group(1, 2))
        d = date(year, month, 1)
        _, nbdays = calendar.monthrange(year, month)
        return (d, d + timedelta(days=nbdays))

    mo = re.match('(\d\d)(?:\s+|\s*[-/]\s*)(\d\d\d\d)$', timestr)
    if mo:
        month, year = map(int, mo.group(1, 2))
        d = date(year, month, 1)
        _, nbdays = calendar.monthrange(year, month)
        return (d, d + timedelta(days=nbdays))

    mo = re.match('([a-zA-Z][a-z]*)(?:\s+|-)(\d\d\d\d)$', timestr)
    if mo:
        month = match_month(mo.group(1))
        if month is not None:
            year = int(mo.group(2))
            d = date(year, month, 1)
            _, nbdays = calendar.monthrange(year, month)
            return (d, d + timedelta(days=nbdays))

    mo = re.match('(\d\d\d\d)$', timestr)
    if mo:
        year = int(mo.group(1))
        return (date(year, 1, 1), date(year+1, 1, 1))

    raise ValueError("Cannot parse: %s" % repr(timestr))



########NEW FILE########
__FILENAME__ = utils
"""
Generic utilities.
"""

# stdlib imports
import operator
from itertools import count, izip, chain, repeat

__all__ = ('render_tree', 'itertree', 'SimpleDummy')


def iter_pairs(l, last=True):
    """Iterate among pairs of items. If last is true, the last item will be
    iterated with the second set to None."""
    i = iter(l)
    b = i.next()
    done = 0
    while not done:
        a = b
        try:
            b = i.next()
        except StopIteration:
            if not last:
                raise
            b = None
            done = 1
        yield a, b

def filter_inout(tlist, pred):
    "Split the list in two according to the given predicate."
    list_in, list_out = [], []
    [(list_in if pred(el) else list_out).append(el) for el in tlist]
    return list_in, list_out


def render_tree(root, pred=None, rootname='.'):
    """
    Generic routine to render a tree of nodes into an cute ascii form. The only
    requirements on each node is that they have a 'name' string attribute and a
    'children' attribute, which should be a list of other nodes. This renders a
    cute tree of dictionaries and reutrn a list of (node, str) pairs to be
    rendered. 'pred' is a predicate that determines which nodes get included.
    """
    lines = [(root, '', rootname)]
    lines.extend(_render_node(root, pred, []))
    return lines

def _render_node(node, pred, pre):
    "Render a dictionary node (recursively)."
    nchildren = len(node.children)
    linesets = []

    last, patcont, patpref = 1, '`-- ', '    '
    for i, sub in enumerate(sorted(node.children, key=lambda x: x.fullname, reverse=1)):
        newlines = _render_node(sub, pred, pre + [patpref])

        if newlines or pred is None or pred(sub):
            if newlines:
                linesets.append(newlines)
            linesets.append( [(sub, ''.join(pre) + patcont, sub.name)] )
            if last:
                last, patcont, patpref = 0, '|-- ', '|   '

    linesets.reverse()
    return reduce(operator.add, linesets, [])


def itertree(root, pred=None):
    """
    Iterate over a tree, producing a labeling of the node and the node itself.
    For example, the following output would be typical:

        ordering   node    isterminal
        ---------- ------- ----------
        (0,)       False   node
        (0,0)      True    node
        (0,1)      True    node
        (1,)       False   node
        (1,0)      False   node
        (1,0,0)    True    node
        (1,0,1)    True    node
        (1,0,2)    True    node

    If the 'pred' predicate is provided, it is used to select nodes from the
    tree.
    """
    # First mark the nodes selected by the predicate. (We use a two-pass
    # algorithm because it would be inefficient in Python to prepend/cons to a
    # list, because it is implement as a vector underneath.)
    if pred is not None:
        markset = set()
        _markpred(root, pred, markset)
    else:
        markset = None
    results = []
    _itertree(root, pred, (0,), results, markset)
    return results

def _markpred(node, pred, markset):
    marked = pred(node)
    for child in node.children:
        marked |= _markpred(child, pred, markset)
    if marked:
        markset.add(node)
    return marked

def _itertree(node, pred, pfx, results, markset):
    "Render a dictionary node (recursively)."
    if (markset is None) or (node in markset):
        results.append( (pfx, not node.children, node) )
        i = 0
        for child in node.children:
            _itertree(child, pred, pfx + (i,), results, markset)
            i += 1



class SimpleDummy(object):
    """
    Simply container object with some conveniences. Just set attrs to declare
    its members. What we want is a version of named_tuple whose members we can
    modify.
    """

    attrs = []

    def __init__(self, *args):
        for a, v in izip(self.attrs, chain(args, repeat(None))):
            setattr(self, a, v)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__,
                           ', '.join(map(str, self.astuple())))

    def astuple(self):
        return tuple(getattr(self, a) for a in self.attrs)



########NEW FILE########
__FILENAME__ = wallet
"""
Wallet arithmetic.
"""

# stdlib imports
from decimal import Decimal

__all__ = ('Wallet',)



class Wallet(dict):
    """
    A mapping of currency to amount. The basic operators are suppored.
    """

    # A dict of commodity -> Decimal to determine the default precision for
    # rounding. The 'None' key is used as a default precision value.
    roundmap = {None: Decimal('0.01')}

    def __init__(self, *args, **kwds):
        if len(args) == 2:
            # Initialize from a tuple ('COM', num).
            dict.__init__(self, (args,), **kwds)
        elif len(args) == 1 and isinstance(args[0], str):
            # Initialize from a string "num COM".
            init = []
            for am in args[0].split(','):
                try:
                    num, com = am.strip().split()
                    init.append((com, num))
                except ValueError:
                    raise ValueError(
                        "Invalid string for initializing a Wallet: %s" % args[0])
            dict.__init__(self, init, **kwds)
        else:
            # Initialize like a normal dictionary.
            dict.__init__(self, *args, **kwds)

        # Convert the initialized contents to Decimal objects.
        for k, value in self.iteritems():
            assert k is not None
            if not isinstance(value, Decimal):
                self[k] = Decimal(value)

        _clean(self)

    def copy(self):
        return Wallet(self)

    def only(self, comm):
        "Return a wallet like this one but with only the given commodity."
        try:
            return Wallet(comm, self[comm])
        except KeyError:
            return Wallet()

    def mask_wallet(self, other):
        "Return this wallet with only the commodities in the other wallet."
        return Wallet(
            (com, amt) for com, amt in self.iteritems() if com in other)

    def mask_commodity(self, com):
        "Return this wallet with only its given commodity."
        w = Wallet()
        num = self.get(com, None)
        if num is not None:
            w[com] = num
        return w

    def __str__(self):
        sitems = sorted(self.iteritems(), key=self.commodity_key)
        return ', '.join('%s %s' % (v, k) for k, v in sitems)

    def __repr__(self):
        return 'Wallet(%s)' % dict.__repr__(self)

    def tostrlist(self):
        """Return a list of pairs of strings (commodity, amount) to be
        rendered)."""
        return sorted(self.iteritems(), key=self.commodity_key)

    def tonum(self):
        """Assuming that the wallet contains a single commodity, return the
        amount for that commodity. If the Wallet is empty, return 0."""
        if len(self) == 0:
            d = Decimal()
        elif len(self) == 1:
            d = self.itervalues().next()
        else:
            raise ValueError("Cannot convert wallet %s to a single number." % self)
        return d

    def tocomm(self):
        """Assuming that the wallet contains a single commodity, return the
        amount for that commodity. Fail if the Wallet is empty."""
        if len(self) == 1:
            return self.iterkeys().next()
        else:
            raise ValueError("Cannot convert wallet %s to a single number." % self)

    def single(self):
        """Return a tuple of (amount, commodity) if this wallet contains a
        single thing. If empty or if it contains multiple things, blow up."""
        assert len(self) == 1, "Wallet contains more than one thing."
        c, a = self.iteritems().next()
        return (a, c)

    def __setitem__(self, key, value):
        if not isinstance(value, Decimal):
            value = Decimal(value)
        dict.__setitem__(self, key, value)

    def isempty(self):
        return not any(self.itervalues())

    def __nonzero__(self):
        return any(self.itervalues())

    def __neg__(self):
        return Wallet((k, -v) for k, v in self.iteritems())

    def __add__(self, other):
        if other is None:
            return Wallet(self)
        w = Wallet()
        for k, v1 in self.iteritems():
            if k in other:
                w[k] = v1 + other[k]
            else:
                w[k] = v1
        for k, v2 in other.iteritems():
            if k not in self:
                w[k] = v2
        _clean(w)
        return w

    def __iadd__(self, other):
        if other is None:
            return self
        w = self
        for k, v1 in self.iteritems():
            if k in other:
                w[k] = v1 + other[k]
            else:
                w[k] = v1
        for k, v2 in other.iteritems():
            if k not in self:
                w[k] = v2
        _clean(w)
        return w

    def __sub__(self, other):
        if other is None:
            return Wallet(self)
        w = Wallet()
        for k, v1 in self.iteritems():
            if k in other:
                w[k] = v1 - other[k]
            else:
                w[k] = v1
        for k, v2 in other.iteritems():
            if k not in self:
                w[k] = -v2
        _clean(w)
        return w

    def __isub__(self, other):
        if other is None:
            return self
        w = self
        for k, v1 in self.iteritems():
            if k in other:
                w[k] = v1 - other[k]
            else:
                w[k] = v1
        for k, v2 in other.iteritems():
            if k not in self:
                w[k] = -v2
        _clean(w)
        return w

    def __mul__(self, other):
        assert isinstance(other, (int, Decimal)), repr(other)
        w = Wallet(self)
        for k, v in self.iteritems():
            w[k] *= other
        _clean(w)
        return w

    def __div__(self, other):
        assert isinstance(other, (int, Decimal))
        w = Wallet(self)
        for k, v in self.iteritems():
            w[k] /= other
        _clean(w)
        return w

    def round(self, mprecision=None):
        """
        Given a map of commodity to Decimal objects with a specific precision,
        return a rounded version of this wallet. (The default precision is
        provided by a key of None in the mprecision dict.)
        """
        if mprecision is None:
            mprecision = self.roundmap
        assert isinstance(mprecision, dict)
        w = Wallet()
        for com, amt in self.iteritems():
            try:
                prec = mprecision[com]
            except KeyError:
                prec = mprecision[None]
            w[com] = amt.quantize(prec)
        _clean(w)
        return w

    @staticmethod
    def commodity_key(kv):
        """ A sort key for the commodities."""
        k = kv[0]
        return (comm_importance.get(k, len(k)), k)

    def price(self, comm, ucomm, price):
        """ Replace all the units of 'comm' by units of 'ucomm' at the given
        price. """
        try:
            units = self[comm]
        except KeyError:
            return
        wdiff = Wallet()
        wdiff[comm] = -units
        wdiff[ucomm] = units * price
        self += wdiff

    def split(self):
        """ Split this wallet into two, one with all the positive unit values
        and one with all the negative unit values. This function returns two
        wallets which, summed together, should equal this wallet."""
        wpos, wneg = Wallet(), Wallet()
        zero = Decimal('0')
        for k, value in self.iteritems():
            w = wpos if value > zero else wneg
            w[k] = value
        return wpos, wneg

    def convert(self, conversions):
        """Given a list of (from-asset, to-asset, rate), convert the from-assets
        to to-assets using the specified rate and return a new Wallet with the
        new amounts."""
        w = self.copy()
        if conversions is None:
            return w
        assert isinstance(conversions, list)
        for from_asset, to_asset, rate in conversions:
            if from_asset in w:
                if to_asset not in w:
                    w[to_asset] = Decimal()
                w[to_asset] += w[from_asset] * rate
                del w[from_asset]
        return w

    def nbthings(self):
        """ Return a single number, the total number of things that are stored
        in this wallet. (This is used for fiddling, as a really gross and
        inaccurate approximation of total amount.)"""
        return sum(self.itervalues())





# Order of important for commodities.
comm_importance = {
    'USD': 0,
    'CAD': 1,
    'EUR': 2,
    }



def _clean(w):
    "Remove zero'ed components of the wallet."
    rlist = [k for k, v in w.iteritems() if not v]
    for k in rlist:
        del w[k]


########NEW FILE########
__FILENAME__ = app
"""
All the actual web pages.
This is isolated in a module so we can reload it on every request while we're
developing.
"""

# stdlib imports
import sys, os, logging, re, StringIO, csv
from wsgiref.util import request_uri, application_uri
from os.path import *
from operator import attrgetter
from datetime import date, timedelta
from urlparse import urlparse
from itertools import izip, count, imap
from pprint import pformat
from decimal import Decimal, getcontext
from collections import defaultdict

# fallback imports
from beancount.fallback import xmlout
from beancount.fallback.xmlout import *

# beancount imports
from beancount.ledger import Account
from beancount.ledger import VIRT_NORMAL, VIRT_BALANCED, VIRT_UNBALANCED
from beancount.utils import render_tree, itertree
from beancount.wallet import Wallet
from beancount.web.serve import *
from beancount.utils import iter_pairs
from beancount import cmdline
from beancount.web.market import *



class Template(object):
    "Base template for all our pages."

    output_encoding = 'utf-8'

    def __init__(self, ctx):
        self.initialize(ctx)

    def initialize(self, ctx):
        self.header = DIV(SPAN(ctx.opts.title or ' ', id='title'), id='header')

        self.body = BODY()
        self.head = HEAD(
            META(http_equiv="Content-Type",
                 content="text/html; charset=%s" % self.output_encoding),
            LINK(rel='stylesheet', href=umap('@@Style'), type='text/css'),
            SCRIPT(' ', type="text/javascript", src=umap('@@Treetable')),
            )
        self.html = HTML(self.head, self.body)

        # Add a common header for all pages.
        self.document = DIV(id='document')

        self.navigation = DIV(
            UL(
               LI(A('Menu', href=umap('@@Menu'))),
               LI(A('Chart of Accounts', href=umap('@@ChartOfAccounts'))),
               LI(A('Journals', href=umap('@@JournalIndex'))),
               LI(A('General Ledger', href=umap('@@LedgerGeneral'))),
               LI(A('Bal.Sheet Begin', href=umap('@@BalanceSheetBegin')),
                  ' ... ',
                  A('BalSheet End', href=umap('@@BalanceSheetEnd'))),
               LI(A('Income', href=umap('@@IncomeStatement'))),
               ## LI(A('CashFlow', href=umap('@@CashFlow'))),
               ## LI(A('Capital', href=umap('@@CapitalStatement'))),
               LI(A('Positions', href=umap('@@Positions'))),
               LI(A('Trades', href=umap('@@Trades'))),
               LI(A('Payees', href=umap('@@Payees'))),
               LI(A('Tags', href=umap('@@Tags'))),
               ## LI(A('Activity', href=umap('@@Activity'))),
               ## LI(A('Locations', href=umap('@@Locations'))),
               LI(A('Other...', href=umap('@@Other'))),
               ),
            id='top-navigation')

        self.reload = DIV(A("Reload", href=umap('@@Reload')), id='reload')

        self.style = DIV(
            UL(LI(A('Com', href=umap('@@SetStyle', style='compact'))),
               LI(A('Oth', href=umap('@@SetStyle', style='other'))),
               ##LI(A('O', href=umap('@@SetStyle', style='only'))),
               LI(A('Ful', href=umap('@@SetStyle', style='full'))),
               ),
            id='style-selector')

        self.body.add(self.header)
        self.body.add(self.reload)
        self.body.add(self.style)
        self.body.add(self.navigation)
        self.body.add(self.document)

        self.add = self.document.add

    def render(self, app):
        app.setHeader('Content-Type','text/html')
        ##app.write(doctype)
        contents = tostring(self.html, app,
                            encoding=self.output_encoding,
                            pretty=True)

doctype = '''\
<?xml version="1.0"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
'''



def ljoin(l, sep):
    "Intersperse the given list with the object 'seq'."
    if l:
        nl = [(x, sep) for x in l[:-1]] + [l[-1]]
    else:
        nl = l
    return nl

def hwallet(w, round=True):
    "Return some HTML suitable for rendering a wallet."
    if round:
        w = w.round()
    return ljoin([SPAN('%s %s' % (a,c), CLASS='amount') for (c,a) in w.tostrlist()], ', ')

def hwallet_paren(w, round=True):
    "A version of hwallet that renders negative numbers in parentheses."
    if round:
        w = w.round()
    l = []
    for (c,a) in w.tostrlist():
        if a >= 0:
            a = SPAN('%s %s' % (a,c), CLASS='amount')
        else:
            a = SPAN('(%s) %s' % (-a,c), CLASS='amount')
        l.append(a)
    return ljoin(l, ', ')



# Scavenged from Mercurial.
def cachefunc(func):
    '''cache the result of function calls'''
    # XXX doesn't handle keywords args
    cache = {}
    if func.func_code.co_argcount == 1:
        # we gain a small amount of time because
        # we don't need to pack/unpack the list
        def f(arg):
            if arg not in cache:
                cache[arg] = func(arg)
            return cache[arg]
    else:
        def f(*args):
            if args not in cache:
                cache[args] = func(*args)
            return cache[args]

    return f

websep = '~'

def webaccname(accname):
    return accname.replace(':', websep)

@cachefunc
def haccount_split(accname):
    """Return some HTML for a full account name. This version makes each
    subaccount clickable."""
    l = []
    append = l.append
    comps = []
    cappend = comps.append
    for comp in accname.split(Account.sep):
        cappend(comp)
        wname = websep.join(comps)
        append(A(comp, href=umap('@@JournalAccount', wname), CLASS='accomp'))
    accspan = SPAN(ljoin(l, SPAN(Account.sep, CLASS='accsep')), CLASS='account')
    accspan.cache = 1
    return accspan

@cachefunc
def haccount(accname):
    "Return some HTML for a full account name. There is a single link."
    accspan = SPAN(
        A(accname, href=umap('@@JournalAccount', webaccname(accname)),
          CLASS='accomp'),
        CLASS='account')
    accspan.cache = 1
    return accspan


def page__menu(app, ctx):
    page = Template(ctx)

    t1, t2 = TD(style='width: 50%'), TD(style='width: 50%')
    table = TABLE(TBODY(TR(t1, t2), id='menu', style='width: 100%'))

    t1.add(UL(
               LI(A('Chart of Accounts', href=umap('@@ChartOfAccounts'))),
               LI(A('Journals', href=umap('@@JournalIndex'))),
               LI(A('General Ledger', href=umap('@@LedgerGeneral'))),
               LI(A('Bal.Sheet Begin', href=umap('@@BalanceSheetBegin')),
                  ' ... ',
                  A('BalSheet End', href=umap('@@BalanceSheetEnd'))),
               LI(A('Income', href=umap('@@IncomeStatement'))),
        ))
        
    t2.add(UL(
               ## LI(A('CashFlow', href=umap('@@CashFlow'))),
               ## LI(A('Capital', href=umap('@@CapitalStatement'))),
               LI(A('Positions', href=umap('@@Positions'))),
               LI(A('Trades', href=umap('@@Trades'))),
               LI(A('Payees', href=umap('@@Payees'))),
               LI(A('Tags', href=umap('@@Tags'))),
               ## LI(A('Activity', href=umap('@@Activity'))),
               ## LI(A('Locations', href=umap('@@Locations'))),
               LI(A('Other...', href=umap('@@Other'))),
        ))

    page.add(H1("Index"), table)
    return page.render(app)


def page__chartofaccounts(app, ctx):
    page = Template(ctx)

    table = TABLE(id='chart-of-accounts', CLASS='accounts treetable')
    table.add(THEAD(TR(TH("Account"), TH("Dr/Cr"), TH("Valid Commodities"))))
    it = iter(itertree(ctx.ledger.get_root_account()))
    for acc, td1, tr, skip in treetable_builder(table, it):
        if len(acc) == 0:
            skip()
            continue
        td1.add(
            A(acc.name, href=umap('@@JournalAccount', webaccname(acc.fullname)),
              CLASS='accomp'))
        tr.add(
            TD(acc.getatype()),
            TD(", ".join(acc.commodities) if acc.commodities else ""),
            ## TD("%d" % len(acc.postings)),
            )

    page.add(H1("Chart of Accounts"), table)
    return page.render(app)

def page__other(app, ctx):
    page = Template(ctx)
    page.add(H1("Other pages, Statistics, and Logs"))


    ul1 = UL(
        LI(A('Cash Flow Statement', href=umap('@@CashFlow'))),
        LI(A("Capital Statement", href=umap('@@CapitalStatement')),
           " (Shareholder's Equity)"),
        LI(A('Update Activity', href=umap('@@Activity'))),
        LI(A('Locations', href=umap('@@Locations'))),
        LI(A('Pricing Commodities', href=umap('@@Pricing'))),
        )
    ul2 = UL(
        LI(A('Source', href=umap('@@Source'))),
        LI(A('Message Log (and Errors)', href=umap('@@Messages'))),
        LI(A('Resources Required for CSS (for websuck)',
             href=umap('@@ScrapeResources'))))
    page.add(H2("Other Pages"), ul1, ul2)


    page.add(H2("Command-line Options"), PRE(' '.join(sys.argv)))

    ledger = ctx.ledger
    page.add(H2("Statistics"),
             TABLE(
                 TR(TD("Nb Accounts:"), TD("%d" % len(ledger.accounts))),
                 TR(TD("Nb Accounts with Postings:"),
                    TD("%d" % sum(1 for a in ledger.accounts.itervalues()
                                  if len(a) > 0))),
                 TR(TD("Nb Commodities:"), TD("%d" % len(ledger.commodities))),
                 TR(TD("Nb Transactions:"), TD("%d" % len(ledger.transactions))),
                 TR(TD("Nb Postings:"), TD("%d" % len(ledger.postings))),
                 TR(TD("Nb Payees:"), TD("%d" % len(ledger.payees))),
                 ))

    ul = UL()
    prices = ledger.directives['price'].prices
    for (base, quote), phist in prices.iteritems():
        sym = '%s/%s' % (base, quote)
        ul.add( LI(A("Price History for %s" % sym,
                      href=umap('@@PriceHistory', base, quote))) )
    page.add(H2("Price Histories"), ul)

    return page.render(app)

def page__scraperes(app, ctx):
    page = Template(ctx)
    page.add(H1("Scrape Resources"))
    for id_ in ('@@FolderOpen', '@@FolderClosed', '@@HeaderBackground'):
        page.add(IMG(src=umap(id_)))
    page.add(A("Home", href=umap('@@Home')))

    return page.render(app)



def render_trial_field(ledger, aname, conversions=None):
    """
    Render a trial balance of the accounts tree using a particular field.
    """
    table = TABLE(id='balance', CLASS='accounts treetable')
    table.add(THEAD(TR(TH("Account"), TH("Amount"), TH(), TH("Cum. Sum"))))
    it = iter(itertree(ledger.get_root_account()))
    sum_ = Wallet()
    for acc, td1, tr, skip in treetable_builder(table, it):
        if len(acc) == 0:
            skip()
            continue
        td1.add(
            A(acc.name, href=umap('@@JournalAccount', webaccname(acc.fullname)),
              CLASS='accomp'))

        lbal = acc.balances.get(aname, None)
        bal = acc.balances_cumul.get(aname, None)
        if lbal.isempty() and bal.isempty():
            skip()
            continue

        if lbal is not None:
            lbal = lbal.convert(conversions).round()
            sum_ += lbal
            tr.add(
                TD(hwallet_paren(lbal), CLASS='wallet'),
                )
        else:
            tr.add(
                TD(CLASS='wallet'),
                )

        if bal is not None:
            bal = bal.convert(conversions).round()
            if not lbal and bal:
                tr.add(
                    TD('...'),
                    TD(hwallet_paren(bal),
                       CLASS='wallet'),
                    )

    ## No need to display the sum at the bottom, it's already at the top node.
    ## table.add(TR(TD(), TD(hwallet_paren(sum_)), TD(), TD()))

    return table


def render_txn_field(ledger, aname, conversions=None):
    """
    Render two sets of postings equivalent to the accounts tree using a
    particular field: one that has the same effect, and one that undoes it. This
    function returns two lists of lines for the transactions.
    """
    list_do = []
    list_undo = []

    it = iter(itertree(ledger.get_root_account()))
    sum_ = Wallet()
    for ordering, isterminal, acc in it:
        if len(acc) == 0:
            continue

        lbal = acc.balances.get(aname, None)
        if lbal.isempty():
            continue

        if lbal is not None:
            lbal = lbal.convert(conversions).round()
            for comm, amount in lbal.iteritems():
                list_do.append('  %-60s     %s %s' % (acc.fullname, amount, comm))
                list_undo.append('  %-60s     %s %s' % (acc.fullname, -amount, comm))

    return list_do, list_undo


def page__trialbalance(app, ctx):
    page = Template(ctx)

    ledger = ctx.ledger
    conversions = app.opts.conversions

    table = render_trial_field(ledger, 'total',
                               app.opts.conversions)

    page.add(H1('Trial Balance'), table)
    return page.render(app)


def semi_table(acc, tid, remove_empty=True, conversions=None, aname='total'):
    """ Given an account, create a table for the transactions contained therein
    (including its subaccounts)."""

    table = TABLE(id=tid, CLASS='semi accounts treetable')
    table.add(THEAD(TR(TH("Account"), TH("Amount"))))
    it = iter(itertree(acc))
    sum_ = Wallet()
    for acc, td1, tr, skip in treetable_builder(table, it):
        if remove_empty and len(acc) == 0:
            skip()
            continue

        td1.add(
            A(acc.name, href=umap('@@JournalAccount', webaccname(acc.fullname)),
              CLASS='accomp'))

        balance = acc.balances[aname]
        if conversions:
            balance = balance.convert(conversions)

        sum_ += balance
        tr.add(
            TD(hwallet_paren(balance.round()) if balance else '')
            )

    table.add(TR(TD(B("Totals")),
                 TD(hwallet_paren(sum_))
                 ))

    return table, sum_


def page__balancesheet_end(app, ctx):
    page = Template(ctx)
    page.add(H1("Balance Sheet (Ending)"))

    ledger = ctx.ledger

    a_acc = ledger.find_account(('Assets', 'Asset'))
    l_acc = ledger.find_account(('Liabilities', 'Liability'))
    e_acc = ledger.find_account(('Equity', 'Capital'))
    if None in (a_acc, l_acc, e_acc):
        page.add(P("Could not get all A, L and E accounts.", CLASS="error"))
        return page.render(app)

    a_table, a_total = semi_table(a_acc, 'assets', conversions=app.opts.conversions)
    l_table, l_total = semi_table(l_acc, 'liabilities', conversions=app.opts.conversions)
    e_table, e_total = semi_table(e_acc, 'equity', conversions=app.opts.conversions)
    page.add(DIV(H2("Liabilities", CLASS="duotables"), l_table,
                 H2("Equity", CLASS="duotables"), e_table,
                 CLASS='right'),
             DIV(H2("Assets", CLASS="duotables"), a_table,
                 CLASS='left'),
             )

    total = a_total + l_total + e_total
    page.add(BR(style="clear: both"),
             TABLE( TR(TD(B("A + L + E:")), TD(hwallet(total))),
                    id='net', CLASS='treetable') )

    return page.render(app)


def page__balancesheet_begin(app, ctx):
    page = Template(ctx)
    page.add(H1("Balance Sheet (Beginning)"))

    ## ledger = ctx.ledger

    ## a_acc = ledger.find_account(('Assets', 'Asset'))
    ## l_acc = ledger.find_account(('Liabilities', 'Liability'))
    ## e_acc = ledger.find_account(('Equity', 'Capital'))
    ## if None in (a_acc, l_acc, e_acc):
    ##     page.add(P("Could not get all A, L and E accounts.", CLASS="error"))
    ##     return page.render(app)

    ## a_table, a_total = semi_table(a_acc, 'assets', conversions=app.opts.conversions)
    ## l_table, l_total = semi_table(l_acc, 'liabilities', conversions=app.opts.conversions)
    ## e_table, e_total = semi_table(e_acc, 'equity', conversions=app.opts.conversions)
    ## page.add(DIV(H2("Liabilities", CLASS="duotables"), l_table,
    ##              H2("Equity", CLASS="duotables"), e_table,
    ##              CLASS='right'),
    ##          DIV(H2("Assets", CLASS="duotables"), a_table,
    ##              CLASS='left'),
    ##          )

    ## total = a_total + l_total + e_total
    ## page.add(BR(style="clear: both"),
    ##          TABLE( TR(TD(B("A + L + E:")), TD(hwallet(total))),
    ##                 id='net', CLASS='treetable') )
    page.add('FIXME TODO')

    return page.render(app)



def page__income(app, ctx):
    page = Template(ctx)
    page.add(H1("Income Statement" #" / P&L Report"
                ))

    ledger = ctx.ledger

    i_acc = ledger.find_account(('Income', 'Revenue', 'Revenues'))
    e_acc = ledger.find_account(('Expenses', 'Expense'))
    if None in (i_acc, e_acc):
        page.add(P("Could not get all unique income and expenses accounts.", CLASS="error"))
        return page.render(app)

    i_table, i_total = semi_table(i_acc, 'income', conversions=app.opts.conversions)
    e_table, e_total = semi_table(e_acc, 'expenses', conversions=app.opts.conversions)
    page.add(DIV(H2("Expenses", CLASS="duotables"), e_table,
                 CLASS='right'),
             DIV(H2("Income", CLASS="duotables"), i_table,
                 CLASS='left'),
             )

    net = TABLE(id='net', CLASS='treetable')
    net.add(
        TR(TD("Net Difference:"), TD(hwallet(i_total + e_total))))
    page.add(BR(style="clear: both"),
             H2("Net Difference (Expenses + Income)"), net)

    return page.render(app)


def page__capital(app, ctx):
    page = Template(ctx)
    page.add(H1("Capital Statement"))
    page.add(P("FIXME TODO"))
    return page.render(app)


def page__cashflow(app, ctx):
    page = Template(ctx)
    page.add(H1("Cash-Flow Statement"))
    page.add(P("FIXME TODO"))
    return page.render(app)


def page__payees(app, ctx):
    page = Template(ctx)
    page.add(H1("Payees"))
    ul = page.add(UL())
    for key, (payee, _) in sorted(ctx.ledger.payees.iteritems()):
        ul.add(LI(A(payee, href=umap('@@LedgerPayee', key))))
    return page.render(app)


def page__tags(app, ctx):
    page = Template(ctx)
    page.add(H1("Tags"))
    ul = page.add(UL())
    for tagname in sorted(ctx.ledger.tags.iterkeys()):
        ul.add(LI(A(tagname, href=umap('@@LedgerTag', tagname))))
    return page.render(app)



refcomm = 'USD'

market_url = 'http://finance.google.com/finance?q=%s'

def page__positions(app, ctx):
    page = Template(ctx)
    page.add(H1("Positions / Assets"))
## FIXME: remove
    return page.render(app)


    # First compute the trial balance.
    ledger = ctx.ledger

    a_acc = ledger.find_account(('Assets', 'Asset'))
    if a_acc is None:
        page.add(P("Could not find assets account.", CLASS="error"))
        return page.render(app)

    # Add a table of currencies that we're interested in.
    icurrencies = set(c for c in a_acc.balances['total'].iterkeys()
                      if c in currencies)

    try:
        xrates = get_xrates()
    except IOError:
        xrates = None
    if xrates:
        tbl = TABLE(id="xrates")
        tbl.add(THEAD(TR(TD("Quote"), TD("Base"), TD("Bid"), TD("Ask"))))
        for (quote, base), (bid, ask, dtime) in xrates.iteritems():
            if quote in icurrencies and base in icurrencies:
                tds = [TD(str(x)) for x in (quote, base, bid, ask)]
                tbl.add(TR(tds))
        page.add(H2("Exchange Rates"), tbl)

    # Add a table of positions.
    tbl = TABLE(id="positions")
    tbl.add(THEAD(TR(TD("Description"),
                     TD("Position"), TD("Currency"), TD("Price"), TD("Change"),
                     TD("Total Value"), TD("Total Change"),
                     TD("Total Value (USD)"), TD("Total Change (USD)"))))
    commnames = ledger.directives['defcomm'].commnames
    for comm, amount in a_acc.balances['total'].tostrlist():
        # Strip numbers from the end, to remove splits.
        mo = re.match('(.*)[\'~][0-9]', comm)
        if mo:
            comm = mo.group(1)
        try:
            if comm in currencies:
                pcomms = []
            else:
                pcomms = [x for x in ledger.pricedmap[comm] if x in currencies]
        except KeyError:
            logging.error(comm, ledger.pricedmap)
            continue
        assert len(pcomms) in (0, 1), "Ambiguous commodities: %s" % pcomms
        if pcomms:
            pcomm = pcomms[0]
            try:
                price, change = get_market_price(comm, pcomm)
            except IOError:
                price, change = None, None
            if price is None:
                fprice = fchange = \
                    totvalue = totchange = \
                    totvalue_usd = totchange_usd = "..."
            else:
                fprice = "%s %s" % (price, pcomm)
                fchange = "%s %s" % (change, pcomm)
                totvalue = "%s %s" % (amount * price, pcomm)
                totchange = "%s %s" % (amount * change, pcomm)
                if pcomm == refcomm:
                    rate = Decimal("1")
                else:
                    urate = xrates.get((pcomm, refcomm), None)
                    if urate is not None:
                        bid, ask, _ = urate
                        rate = (bid + ask) / 2
                    else:
                        irate = xrates.get((refcomm, pcomm), None)
                        if irate is not None:
                            bid, ask, _ = irate
                            rate = 1 / ((bid + ask) / 2)
                        else:
                            rate = None

                if rate is not None:
                    totvalue_usd = "%.2f %s" % (amount * price * rate, refcomm)
                    totchange_usd = "%.2f %s" % (amount * change * rate, refcomm)
                else:
                    totvalue_usd = ""
                    totchange_usd = ""
        else:
            pcomm = ''
            fprice = fchange = totvalue = totchange = totvalue_usd = totchange_usd = ''
            if comm in currencies:
                totvalue = "%s %s" % (amount, comm)

        market, name = commnames.get(comm, u'')
        if market is not None:
            name = A(name, href=market_url % market)
        tds = [TD(name, CLASS='l'),
               TD("%s %s" % (amount, comm)), TD(pcomm),
               TD(fprice), TD(fchange),
               TD(totvalue), TD(totchange),
               TD(totvalue_usd), TD(totchange_usd)]

        tbl.add(TR(tds))

    page.add(H2("Total Assets"), tbl)

    return page.render(app)



def page__pricing(app, ctx):
    "A list of the commodities used for pricing each type of financial asset."
    page = Template(ctx)
    page.add(H1("Pricing Commodities"))

    # First compute the trial balance.
    ledger = ctx.ledger

    # Add a table of positions.
    tbl = TABLE(id="pricedmap")
    tbl.add(THEAD(TR(TD("Commodity"), TD("Price Currency"))))
    for comm, pclist in sorted(ledger.pricedmap.iteritems()):
        tbl.add(TR( TD(comm), TD(', '.join(pclist)) ))

    page.add(tbl)

    return page.render(app)


def page__pricehistory(app, ctx):
    """A page that describes the samples of a price history. It expects
    base/quote commodities as input."""
    page = Template(ctx)
    page.add(H1("Price History for %s/%s" % (ctx.base, ctx.quote)))

    tbl, = page.add(TABLE(THEAD(TR(TH("Date"), TH("Rate"))),
                          CLASS='price_history'))

    prices = app.ledger.directives['price'].prices
    phist = prices[(ctx.base, ctx.quote)]
    for date_, rate in phist:
        tbl.append( TR(TD(date_.isoformat()), TD(str(rate))) )

    return page.render(app)




def treetable_builder(tbl, iterator, skiproot=False):
    """
    Given a TABLE object in 'tbl' and a root 'node', create and iterate over the
    rows for creating a JavaScript tree with the treetable JS source. Note that
    the table needs to have a unique 'id' attribute. This is an iterator that yields

      (node, td-of-column-1, tr-for-row, skip-function)

    You need to add the relevant columns on the row object, using data in the
    node.
    """
    iid = tbl.attrib['id']

    ## page.add(
    ##     A(u'<+>', onclick="treetable_expandAll('balance');"),
    ##     A(u'<->', onclick="treetable_collapseAll('balance');"))

    if skiproot:
        iterator.next()

    skipflag = []
    def skipfun():
        skipflag.append(1)

    spc = SPAN(CLASS='foldspc')
    for ordering, isterminal, node in iterator:
        rowid = '%s_%s' % (iid, '_'.join(str(x) for x in ordering))

        pretitle = [spc] * (len(ordering))
        if not isterminal:
            folder = A(IMG(src=umap("@@FolderOpen"), CLASS='folder'),
                       # href='#',
                       onclick="treetable_toggleRow('%s');" % rowid)
            pretitle[-1] = folder

        td = TD(pretitle, CLASS='tree')
        tr = TR(td, id=rowid)
        yield node, td, tr, skipfun
        if skipflag:
            skipflag[:] = []
        else:
            tbl.add(tr)



def page__activity(app, ctx):
    "Output the updated time ranges of each account."

    page = Template(ctx)

    today = date.today()
    table = TABLE(id='activity', CLASS='accounts treetable')
    table.add(THEAD(TR(TH("Account"),
                       TH("Oldest Chk"),
                       TH("Newest Chk"),
                       TH("Last Posting"),
                       TH("Days since"),
                       )))
    it = iter(itertree(ctx.ledger.get_root_account(), pred=attrgetter('checked')))
    for acc, td1, tr, skip in treetable_builder(table, it):
        if len(acc) == 0:
            skip()
            continue

        td1.add(
            A(acc.name, href=umap('@@JournalAccount', webaccname(acc.fullname)),
              CLASS='accomp'))

        append = False
        row = [TD() for _ in xrange(4)]
        elapsed_check, elapsed_post = None, None
        if acc.checked:
            row[0].add(str(acc.check_min))
            row[1].add(str(acc.check_max))
            elapsed_check = (today - acc.check_max).days
            append = True

        if acc.postings:
            post_last = acc.postings[-1]
            row[2].add(str(post_last.actual_date))
            elapsed_post = (today - post_last.actual_date).days
            append = True

        if append:
            row[3].add('%s days' % min(filter(lambda x: x is not None,
                                              [elapsed_check, elapsed_post])))
            tr.extend(row)

    page.add(H1('Activity'), table)
    return page.render(app)



def iter_months(oldest, newest):
    """Yield dates for the first day of every month between oldest and newest."""
    cdate = date(oldest.year, oldest.month, 1)
    while 1:
        yield cdate
        mth = cdate.month % 12 + 1
        year = cdate.year + (1 if mth == 1 else 0)
        cdate = date(year, mth, 1)
        if cdate > newest:
            break


def page__journal_index(app, ctx):
    ledger = app.ledger

    page = Template(ctx)
    ul = UL(
        LI(A("General Journal", href=umap('@@JournalAll')),
           "  (all transactions by-date)"),
        )
    page.add(H1("Journals"),
             ul,
             ## P(I("""Note: These journals display transactions for accounts, ordered by-date; for
             ##        ledgers (transactions by-account), click on any account name
             ##        in any other view.""")),
             )

    if ledger.transactions:
        date_oldest = min(x.actual_date for x in ledger.transactions)
        date_youngest = max(x.actual_date for x in ledger.transactions)
        mths = list(iter_months(date_oldest, date_youngest))
        for d in reversed(mths):
            mthstr = d.strftime('%Y-%m')
            ul.add(LI(A("Journal for %s" % mthstr,
                        href=umap("@@JournalMonthly", d.year, d.month)
                      )))

    return page.render(app)


def page__journal_all(app, ctx):
    """
    List all the transactions.
    """
    acc = ctx.ledger.get_root_account()
    return render_journal(app, ctx, acc)


def page__journal_monthly(app, ctx):
    """
    List all the transactions for a single month.
    """
    year = getattr(ctx, 'year', '')
    mth = getattr(ctx, 'month', '')
    if year and mth:
        year = int(year)
        mth = int(mth)
        dbegin = date(year, mth, 1)
        mth = mth % 12 + 1
        if mth == 1:
            year += 1
        dend = date(year, mth, 1)
    else:
        dbegin = None

    acc = ctx.ledger.get_root_account()
    return render_journal(app, ctx, acc, (dbegin, dend))


def page__journal_account(app, ctx):
    """
    List all the transactions for a single account.
    """
    accname = ctx.accname
    accname = accname.replace(websep, Account.sep)
    try:
        acc = ctx.ledger.get_account(accname)
    except KeyError:
        raise HttpNotFound(accname)
    return render_journal(app, ctx, acc)


def render_journal(app, ctx, acc, dates=None):
    """
    List the transactions that pertain to a list of filtered postings.
    The dates interval is optional.
    """
    page = Template(ctx)
    style = ctx.session.get('style', 'full')
    assert style in ('compact', 'other', 'only', 'full')

    # Check that we have a valid account.
    assert acc, acc
    postings = set(acc.subpostings())

    # Unpack date interval (if specified).
    (dbegin, dend) = dates or (None, None)

    # Get the list of checks for this account and include them in the listing.
    checks = ctx.ledger.directives['check']
    acc_checks = sorted(checks.account_checks(acc))

    if dbegin is not None:
        def dfilter(txn):
            if not (dbegin <= txn.actual_date < dend):
                return True
    else:
        dfilter = None

    table = render_postings_table(postings, style, dfilter, acc_checks)

    if acc.isroot():
        if dbegin is None:
            page.add(H1('General Journal'), table)
        else:
            page.add(H1('Journal for %s' % dbegin), table)
    else:
        page.add(H1('Ledger for ', haccount_split(acc.fullname)), table)

    return page.render(app)


def page__ledger_payee(app, ctx):
    """
    List the transactions that pertain to a list of filtered postings.
    """
    page = Template(ctx)
    style = ctx.session.get('style', 'full')
    assert style in ('compact', 'other', 'only', 'full')

    payee_key = getattr(ctx, 'payee', '')
    payee, txns = ctx.ledger.payees[payee_key]

    # Render a table for the list of transactions.
    postings = []
    for txn in txns:
        postings.extend(txn.postings)
    table_txns = render_postings_table(postings, style)

    # Render a trial balance of only the transactions that involve this payee.
    ctx.ledger.compute_balances_from_postings(postings, 'payee')
    table_flow = render_trial_field(ctx.ledger, 'payee', app.opts.conversions)

    page.add(H1('Payee transactions for %s' % payee),
             H2('Ledger'), table_flow,
             HR(),
             H2('Journal'), table_txns)

    return page.render(app)


def page__ledger_tag(app, ctx):
    """
    List the transactions that pertain to a list of filtered postings.
    """
    page = Template(ctx)
    style = ctx.session.get('style', 'full')
    assert style in ('compact', 'other', 'only', 'full')

    tagname = getattr(ctx, 'tag', '')
    txns = ctx.ledger.tags[tagname]

    # Render a table for the list of transactions.
    postings = []
    for txn in txns:
        postings.extend(txn.postings)
    table_txns = render_postings_table(postings, style)

    # Render a trial balance of only the transactions that involve this tag.
    ctx.ledger.compute_balances_from_postings(postings, 'tag')
    table_flow = render_trial_field(ctx.ledger, 'tag', app.opts.conversions)

    # Render two transactions to replace the transactions in the tags.
    do, undo = render_txn_field(ctx.ledger, 'tag')

    enddate = max(x.actual_date for x in postings)
    txnline = ("%s  S  Summary | Summary transaction for tag:  %s" %
               (enddate, tagname))
    do.insert(0, txnline)
    undo.insert(0, txnline + '  (UNDO)')

    page.add(H1('Tag transactions for %s' % tagname),
             H2('Ledger'), table_flow,
             HR(),
             H2('Journal'), table_txns,
             HR(),
             H2('Equivalent transactions'),
             PRE(os.linesep.join(do)),
             PRE(os.linesep.join(undo)),
             )

    return page.render(app)



def render_postings_table(postings, style,
                          filterfun=None,
                          acc_checks=None,
                          amount_overrides=None):

    table = TABLE(
        THEAD(
            TR(TH("Date"), TH("F"), TH("Description/Posting"),
               TH(""), TH("Amount"), TH("Balance"))),
        CLASS='txntable')

    # Get the list of transactions that relate to the postings.
    txns = set(post.txn for post in postings)

    balance = Wallet()
    for txn in sorted(txns):
        if filterfun is not None and filterfun(txn) is True:
            continue

        if acc_checks is not None:
            register_insert_checks(acc_checks, table, txn.actual_date)

        try:
            sty = 'background-color: %s' % flag_colors[txn.flag]
        except KeyError:
            sty = ''

        # Sum the balance of the selected postings from this transaction.
        txn_amount = Wallet()
        for post in txn.postings:
            if post in postings:
                if amount_overrides and post in amount_overrides:
                    amt = amount_overrides[post]
                else:
                    amt = post.amount
                txn_amount += amt

        # Add this amount to the balance.
        balance += txn_amount

        # Display the transaction line.
        desc = []
        if txn.payee:
            desc.append(A(txn.payee, href=umap('@@LedgerPayee', txn.payee_key),
                          CLASS='payee'))
            desc.append(' | ')
        if txn.narration:
            desc.append(txn.narration)

        tr = TR(TD(txn.rdate()),
                TD(txn.flag, CLASS='flag', style=sty),
                TD(desc, CLASS='description'),
                TD(CLASS='wallet'),
                TD(hwallet(txn_amount), CLASS='wallet'),
                TD(hwallet(balance), CLASS='wallet cumulative'),
                CLASS='txn')
        table.add(tr)

        # Display the postings.
        if style != 'compact':
            for post in txn.postings:
                inlist = post in postings
                if inlist:
                    if style == 'other':
                        continue
                elif style == 'only':
                        continue

                postacc = haccount(post.account.fullname)
                if post.virtual == VIRT_UNBALANCED:
                    postacc = ['(', SPAN(postacc), ')']
                elif post.virtual == VIRT_BALANCED:
                    postacc = ['[', SPAN(postacc), ']']
                if post.note:
                    postacc = [postacc, SPAN(';', post.note, CLASS='postnote')]
                td_account =TD(postacc)
                if inlist:
                    td_account.attrib['class'] = 'highpost'
                tr = TR(TD(post.rdate(), colspan='2', CLASS='postdate'),
                        td_account,
                        TD(hwallet(post.amount), CLASS='wallet'),
                        TD(['@ ', hwallet(post.price, round=False)] if post.price else '', CLASS='price'),
                        TD(),
                        CLASS='posting')

                table.add(tr)

    # Add the remaining checks.
    if acc_checks is not None:
        register_insert_checks(acc_checks, table)

    return table




# Colors for the flag cell.
flag_colors = {'!': '#F66',
               '?': '#F66',
               '*': '#AFA',
               'A': '#AAF'}

# Colors for the body of the check row in the register.
check_colors = {'!': '#F66',
                '?': '#F66',
               '*': '#AFA',
               'A': '#AFA'}


def register_insert_checks(checklist, table, date=None):
    """
    Insert checks in the register.
    Note: this modified 'checklist' to remove the added checks.
    """
    while 1:
        if not checklist:
            break
        chk = checklist[0]
        # Note: we use "<" here because the check's date semantic is "after all
        # transactions on that day", and therefore we need to render the green
        # check line after the transactions on that date.
        if date is None or chk.cdate < date:
            sty = 'background-color: %s' % flag_colors[chk.flag]
            trsty = 'background-color: %s' % check_colors[chk.flag]
            tr = TR(TD(str(chk.cdate)),
                    TD(chk.flag, CLASS='flag', style=sty),
                    TD(u'Check at %s:%s' % (chk.filename, chk.lineno),
                       CLASS='description check'),
                    TD(hwallet(chk.expected), CLASS='wallet'),
                    TD(hwallet(chk.diff)),
                    TD(hwallet(chk.balance), CLASS='wallet'),
                    CLASS='assert', style=trsty)
            table.add(tr)
            del checklist[0]
        else:
            break


def page__source(app, ctx):
    """
    Serve the source of the ledger.
    """
    page = Template(ctx)
    div = DIV(id='source')
    if app.opts.unsafe:
        div.add(P("(Sorry, source not available.)"))
    else:
        for i, line in izip(count(1), ctx.ledger.source):
            div.add(PRE("%4d  |%s" % (i, line.strip())), A(name='line%d' % i))

    page.add(H1('Source'), div)
    return page.render(app)



msgname = {
    logging.ERROR: 'error',
    logging.WARNING: 'warning',
    logging.INFO: 'info',
    logging.CRITICAL: 'critical',
    }

def page__messages(app, ctx):
    """
    Report all ledger errors.
    """
    page = Template(ctx)
    page.add(H1('Parsing Messages'))

    ledger = ctx.ledger
    div = page.add(DIV(CLASS='message'))
    tbl = div.add(TABLE())
    for msg in ledger.messages:
        name = msgname[msg.level]
        tbl.add(TR(TD(name.capitalize(), CLASS=name),
                      TD(A(msg.message, href=umap('@@Source') + '#line%d' % (msg.lineno or 0)))))

    return page.render(app)


ramq_reqdays = 183

def page__locations(app, ctx):
    page = Template(ctx)
    page.add(H1("Locations"))

    # Compute the minimum time in the filtered postings.
    mindate = min(imap(attrgetter('actual_date'), ctx.ledger.postings))
    maxdate = max(imap(attrgetter('actual_date'), ctx.ledger.postings))

    location = ctx.ledger.directives['location']

    # Group lists per year.
    peryear = defaultdict(list)
    for x in sorted(location.locations):
        ldate = x[0]
        peryear[ldate.year].append(x)

    oneday = timedelta(days=1)
    today = date.today()
    tomorrow = today + oneday

    # Cap lists beginnings and ends.
    yitems = sorted(peryear.iteritems())
    city, country = "", ""
    for year, ylist in yitems:
        ldate, _, _ = ylist[0]
        if (ldate.month, ldate.day) != (1, 1):
            ylist.insert(0, (date(year, 1, 1), city, country))

        ldate, city, country = ylist[-1]
        d = date(year+1, 1, 1)
        if d > tomorrow:
            d = tomorrow
        ylist.append((d, city, country))

    for year, ylist in yitems:
        ul = UL()
        comap = defaultdict(int)
        ramq_days = 0
        for x1, x2 in iter_pairs(ylist, False):
            ldate1, city, country = x1
            ldate2, _, _ = x2

            if ((ldate1 <= mindate and ldate2 <= mindate) or
                (ldate1 >= maxdate and ldate2 >= maxdate)):
                continue

            if ldate1 < mindate:
                ldate1 = mindate
            if ldate2 > maxdate:
                ldate2 = maxdate + oneday

            days = (ldate2 - ldate1).days
            ul.append(LI("%s -> %s (%d days) : %s (%s)" %
                         (ldate1, ldate2 - oneday, days, city, country)))
            comap[country] += days
            if country == 'Canada' or days < 21:
                ramq_days += days
                # FIXME: I think that technically I would have to be in Quebec,
                # not just in Canada.

        if len(ul) > 0:
            page.add(H2(str(year)), ul)
            ulc = page.add(H2("Summary %s" % year), UL())
            total_days = 0
            for country, days in sorted(comap.iteritems()):
                ulc.append(LI("%s : %d days" % (country, days)))
                total_days += days
            ulc.append(LI("Total : %d days" % total_days))

            missing_days = ramq_reqdays - ramq_days
            ulc.add(LI("... for RAMQ eligibility: %d days / %d : %s" %
                       (ramq_days, ramq_reqdays,
                        ('Missing %d days' % missing_days
                         if missing_days > 0
                         else 'Okay'))))

    return page.render(app)


def page__trades(app, ctx):
    """
    Render a list of trades.
    """
    page = Template(ctx)
    page.add(H1("Trades"))

    page.add(DIV(A("Download as CSV", href=umap("@@TradesCSV")), CLASS='right-link'))

    style = ctx.session.get('style', 'full')
    ledger = ctx.ledger

    for bt in ledger.booked_trades:

        legs_table = TABLE(
            THEAD(
                TR(TH("Date"), TH("Units"), TH("Price"),
                   TH("Amount"), TH("Exchange Rate"), TH("Report Amount (target CCY)"))),
            CLASS="trades")

        for leg in bt.legs:
            legs_table.add(
                TR(TD(str(leg.post.actual_date)),
                   TD(hwallet(Wallet(bt.comm_book, leg.amount_book))),
                   TD(hwallet(Wallet(leg.comm_price, leg.price))),
                   TD(hwallet(Wallet(leg.comm_price, leg.amount_price))),
                   TD(hwallet(Wallet('%s/%s' % (leg.comm_price, bt.comm_target or '-'), leg.xrate))),
                   TD(hwallet(Wallet(bt.comm_target or leg.comm_price, leg.amount_target))),
                   ))

        post_book = bt.post_book

        # Note: negate the final amounts as they were applied to flow values
        # (income/expense).
        legs_table.add(
            TR(TD('Gain(+) / Loss(-)'),
               TD(),
               TD(),
               TD(hwallet(-bt.post_book.amount_orig)),
               TD(),
               TD(hwallet(-bt.post_book.amount)),
               ))

        postings = [x.post for x in bt.legs]
        overrides = dict((x.post, Wallet(bt.comm_book, x.amount_book))
                         for x in bt.legs)
        table = render_postings_table(postings, style,
                                      amount_overrides=overrides)
        title = '%s - %s %s ; %s' % (
            bt.close_date(),
            bt.comm_book,
            'in %s' % bt.comm_target if bt.comm_target else '',
            bt.account.fullname)
        page.add(DIV(H2(title), legs_table, P("Corresponding transactions:"), table,
                     CLASS='btrade'))

    return page.render(app)



def page__trades_csv(app, ctx):
    """
    Generate a CSV document with the list of trades.
    """
    ledger = ctx.ledger

    rows = [["Date", "Units", "Commodity",
             "CCY", "Price", "Amount", "Gain/Loss",
             "",
             "Report CCY", "XRate", "Report Amount", "Report Gain/Loss"]]

    for bt in ledger.booked_trades:
        rows.append([]) # empty line

        for leg in bt.legs:
            rows.append([
                str(leg.post.actual_date),
                leg.amount_book,
                bt.comm_book,
                leg.comm_price,
                leg.price,
                leg.amount_price,
                '',
                '',
                bt.comm_target or leg.comm_price,
                leg.xrate,
                leg.amount_target,
                ''
                ])

        post_book = bt.post_book
        rows.append(['', '', '', '', '', '',
                     str(bt.post_book.amount_orig.tonum()),
                     '', '', '', '',
                     str(bt.post_book.amount.tonum())])
        rows.append([]) # empty line

    oss = StringIO.StringIO()
    writer = csv.writer(oss)
    writer.writerows(rows)

    app.setHeader('Content-Type','text/csv')
    app.write(oss.getvalue())


def page__reload(app, ctx):
    """
    Reload the ledger file and return to the given URL.
    """
    app.ledger = cmdline.reload(ctx.ledger, app.opts)
    raise HttpRedirect(ctx.environ['HTTP_REFERER'])



def page__setstyle(app, ctx):
    "Set the session's style and redirect where we were."
    ctx.session['style'] = ctx.style[0]
    raise HttpRedirect(ctx.environ['HTTP_REFERER'])



def redirect(*args):
    "Return a resource to redirect to the given resource id."
    def redirect_res(app, ctx):
        raise HttpRedirect(umap(*args))
    return redirect_res

def static(fn, ctype):
    """Return a handler for a static file to be served, with caching.
    Caching is disabled when we're in debug/development mode. """
    cache = []
    def f(app, ctx):
        if ctx.debug or not cache:
            result = open(join(dirname(__file__), fn)).read()
            cache.append(result)
        else:
            result = cache[0]
        app.setHeader('Content-Type', ctype)
        app.write(result)
    return f

def page__servererror(app, ctx):
    app.setHeader('Content-Type','text/html')
    app.write('TODO')
    ## FIXME return the error page here.





# page-id, callable-handler, render-format, regexp-for-matching
# If the regexp is left to a value of None, it is assumed it matches the render string exactly.
page_directory = (

    ('@@Robots', static('robots.txt', 'text/plain'), '/robots.txt', None),
    ('@@Style', static('style.css', 'text/css'), '/style.css', None),
    ('@@Treetable', static('treetable.js', 'text/javascript'), '/treetable.js', None),
    ('@@FolderOpen', static('folder_open.png', 'image/png'), '/folder_open.png', None),
    ('@@FolderClosed', static('folder_closed.png', 'image/png'), '/folder_closed.png', None),
    ('@@HeaderBackground', static("header-universal-dollar.jpg", 'image/jpeg'), '/header.jpg', None),
    ('@@ScrapeResources', page__scraperes, '/scraperes', None),

    ('@@Home', redirect('@@Menu'), '/', None),
    ('@@HomeIndex', redirect('@@Menu'), '/index', None),
    ('@@Menu', page__menu, '/menu', None),

    ('@@ChartOfAccounts', page__chartofaccounts, '/accounts', None),
    ('@@Other', page__other, '/other', None),
    ('@@Activity', page__activity, '/activity', None),
    ('@@BalanceSheet', page__balancesheet_end, '/balsheet_end', None),
    ('@@BalanceSheetEnd', page__balancesheet_end, '/balsheet_end', None),
    ('@@BalanceSheetBegin', page__balancesheet_begin, '/balsheet_beg', None),
    ('@@IncomeStatement', page__income, '/income', None),
    ('@@CapitalStatement', page__capital, '/capital', None),
    ('@@CashFlow', page__cashflow, '/cashflow', None),
    ('@@Payees', page__payees, '/payees', None),
    ('@@Tags', page__tags, '/tags', None),
    ('@@Positions', page__positions, '/positions', None),
    ('@@Locations', page__locations, '/locations', None),
    ('@@Trades', page__trades, '/trades', None),
    ('@@TradesCSV', page__trades_csv, '/trades.csv', None),
    ('@@Pricing', page__pricing, '/pricing', None),
    ('@@PriceHistory', page__pricehistory, '/price/history/%s/%s', '^/price/history/(?P<base>[^/]+)/(?P<quote>[^/]+)$'),

    ('@@JournalIndex', page__journal_index, '/journal/index', None),
    ('@@JournalAll', page__journal_all, '/journal/all', None),
    ('@@JournalMonthly', page__journal_monthly, '/journal/monthly/%04d/%02d', '^/journal/monthly/(?P<year>\d\d\d\d)/(?P<month>\d\d)$'),
    ('@@JournalAccount', page__journal_account, '/ledger/byaccount/%s', '^/ledger/byaccount/(?P<accname>.*)$'),

    ('@@LedgerGeneral', page__trialbalance, '/ledger', "^/(?:ledger|trial)$"),
    ('@@LedgerPayee', page__ledger_payee, '/ledger/bypayee/%s', '^/ledger/bypayee/(?P<payee>.*)$'),
    ('@@LedgerTag', page__ledger_tag, '/ledger/bytag/%s', '^/ledger/bytag/(?P<tag>.*)$'),

    ('@@SetStyle', page__setstyle, '/setstyle', '^/setstyle$'),
    ('@@Messages', page__messages, '/messages', None),
    ('@@Reload', page__reload, '/reload', None),
    ('@@Source', page__source, '/source', None),
    ('@@Error', page__servererror, '/error', None),

    )

mapper = Mapper(page_directory)
umap = urlmap = mapper.map


########NEW FILE########
__FILENAME__ = market
"""
Code utilised to obtain market values.
"""

# stdlib imports
from __future__ import with_statement
import re, urllib, threading, logging
from decimal import Decimal
from datetime import datetime

# other imports
from beancount.fallback.BeautifulSoup import BeautifulSoup


__all__ = ('get_market_price', 'currencies', 'get_xrate', 'get_xrates')


currencies = ['USD', 'CAD', 'JPY', 'EUR', 'AUD', 'CHF', 'BRL']

market_currency = {
    'NYSE': 'USD',
    'TSE': 'CAD',
    }

url_google = 'http://finance.google.com/finance?q=%s'

def getquote_google(sym):
    ssym = sym.strip().lower()
    f = urllib.urlopen(url_google % ssym)
    soup = BeautifulSoup(f)
    el = soup.find('span', 'pr')
    if el is not None:
        # Find the quote currency.
        h1 = soup.find('h1')
        mstr = h1.next.next
        mstr = mstr.replace('&nbsp;', '').replace('\n', '')
        mstring = '\\(([A-Za-z]+),\\s+([A-Z]+):%s\\)' % ssym.upper()
        mo = re.match(mstring, mstr)
        if mo is not None:
            market = mo.group(2)
            comm = market_currency[market]
        else:
            raise ValueError("Unknown market: %s for %s" % (mstr, ssym))
        price = Decimal(el.contents[0])

        chg = soup.find('span', 'bld')
    else:
        comm, price, chg = None, None
        
        
    url = '' % (symbol, stat)
    return urllib.urlopen(url).read().strip().strip('"')



url_yahoo = 'http://download.finance.yahoo.com/d/quotes.csv?s=%s&f=l1c1'

def specDecimal(s):
    if s == 'N/A':
        return Decimal()
    else:
        return Decimal(s)

def getquote_yahoo(sym, pcomm):
    ssym = sym.strip().lower()
    if pcomm == 'CAD':
        ssym += '.TO'
    f = urllib.urlopen(url_yahoo % ssym)
    contents = f.read().strip()
    price, change = [specDecimal(x) for x in contents.split(',')]
    return (price, change)

getquote = getquote_yahoo



# A dict of commodity id to (market price, underlying commodity).
_market_prices = {}
_market_prices_lock = threading.Lock()

def get_market_price(comm, pcomm):
    try:
        return _market_prices[(comm, pcomm)]
    except KeyError:
        t = GetQuoteThread(comm, pcomm)
        t.start()
        return (None, None)
    
class GetQuoteThread(threading.Thread):
    
    def __init__(self, comm, pcomm):
        threading.Thread.__init__(self)
        self.key = (comm, pcomm)

    def run(self):
        logging.info("Fetching price for %s" % str(self.key))
        r = getquote(*self.key)
        with _market_prices_lock:
            _market_prices[self.key] = r
        logging.info("Price for %s = %s" % (self.key, r))
        




def find_currency_rows(soup):
    """
    Find the table rows that have an exchange rate and yield them.
    """
    for row in soup.findAll('tr'):
        for td in row.findAll('td'):
            bolds = td.findAll('b')
            if not bolds:
                break
            else:
                b = bolds[0].contents[0]
                mo = re.match('([A-Z]{3})/([A-Z]{3})', b)
                if mo is None:
                    break
                yield row, mo.group(1, 2)

months = dict((x,i+1)
              for i,x in enumerate(('Jan Feb Mar Apr May Jun Jul'
                                    ' Aug Sep Oct Nov Dec').split()))

def get_rate(tr):
    """
    Given a table row, get the bid and ask as Decimal objects and parse the
    date/time.
    """
    nodes = [x.find('font').contents[0] for x in tr.findAll('td')[1:]]
    bid = Decimal(nodes[0].strip())
    ask = Decimal(nodes[1].strip())
    mo = re.match('\s*[A-Z][a-z]+\s+([A-Z][a-z]+)\s+(\d+)\s+(\d+):(\d+):(\d+)\s+(\d{4})',
                  nodes[2])
    assert mo, nodes[2]
    year, day, hour, min, sec = map(int, mo.group(6, 2, 3, 4, 5))
    mth = months[mo.group(1)]
    dt = datetime(year, mth, day, hour, min, sec)
    return bid, ask, dt


_xrates_url = 'http://www.oanda.com/rtrates'

# Cache of (quote, base) to (bid, ask, time).
_xrates = {}

def refresh_xrates():
    _xrates.clear()
    fn, info = urllib.urlretrieve(_xrates_url)
    soup = BeautifulSoup(open(fn))
    for tr, (quote, base) in find_currency_rows(soup):
        bid, ask, time = get_rate(tr)
        _xrates[(quote, base)] = (bid, ask, time)

def get_xrate(quote, base):
    "Get the given exchange rate."
    try:
        r = _xrates[(quote, base)]
    except KeyError:
        t = threading.Thread(target=refresh_xrates)
        t.start()
        refresh_xrates()
        r = None
    return r
    
def get_xrates():
    """ Return all the exchange rates we have. """
    if _xrates:
        return _xrates.copy()
    else:
        refresh_xrates()




########NEW FILE########
__FILENAME__ = serve
"""
Start a simple web server to display the contents of some Ledger.

We keep this code simplistic, and away from growing into a full-fledged web app
framework as much as possible on purpose! The web server code need not be super
powerful: as simple as possible.
"""

# stdlib imports
import sys, re, cgitb, logging, cgi, traceback
from random import randint
from wsgiref.simple_server import make_server
from wsgiref.util import request_uri, application_uri
from wsgiref.headers import Headers
from StringIO import StringIO
from os.path import *
from copy import copy
from decimal import Decimal
import Cookie

# beancount imports
from beancount import cmdline


__all__ = ('main', 'Mapper',
           'HttpError', 'HttpNotFound', 'HttpRedirect')


# HTTP errors.

class HttpError(Exception):
    code = None

class HttpNotFound(Exception):
    code = 404
    status = '404 Not Found'

class HttpRedirect(Exception):
    code = 302
    status = '302 Found'



class BeanServer(object):
    "A really, really simple application server."

    default_headers = [('Content-Type', 'text/html')]

    def __init__(self, ledger, opts):
        self.ledger = ledger

        self.data = []
        self.load()

        # Map of session to dict.
        self.cookiejar = {}

        # Prototype for context object.
        ctx = self.ctx = Context()
        self.opts = ctx.opts = opts
        ctx.debug = opts.debug

    def setHeader(self, name, value):
        self.headers[name] = value

    def write(self, data):
        assert isinstance(data, str), data
        self.data.append(data)

    def load(self):
        "Load the application pages."
        import app
        reload(app)
        self.mapper = app.mapper

    def __call__(self, environ, start_response):
        if self.ctx.debug:
            self.load()

        self.environ = environ
        self.response = start_response
        del self.data[:]
        self.headers = Headers(self.default_headers)

        ctx = copy(self.ctx) # shallow
        ctx.ledger = self.ledger

        path = environ['PATH_INFO']

        ishtml = '.' not in basename(path) or path.endswith('.html')
        if ishtml:
            # Load cookie (session is only in memory).
            cookie = Cookie.SimpleCookie(environ.get('HTTP_COOKIE', ''))
            has_cookie = (bool(cookie) and
                          'session' in cookie and
                          cookie["session"].value in self.cookiejar)
            if has_cookie:
                session_id = cookie["session"].value
                session = self.cookiejar[session_id]
            else:
                session_id = '%x' % randint(0, 16**16)
                cookie["session"] = session_id
                session = self.cookiejar[session_id] = {}
            ctx.session = session

        try:
            # Linear search in the regexp to match the request path.
            page, vardict = self.mapper.match(path)
            if page is None:
                raise HttpNotFound(path)
            else:
                # Update the context object with components of the request and
                # with the query parameters.
                ctx.environ = environ

                form = cgi.parse(environ=environ)
## FIXME: make this wsgi compatible.
                ## conlen = int(self.environ['CONTENT_LENGTH'])
                ## s = self.environ['wsgi.input'].read(conlen)
                ## form = cgi.parse_qs(s)

                ctx.__dict__.update(form)
                ctx.__dict__.update(vardict)

                page(self, ctx)

                # Add session cookie to headers, if necessary.
                if ishtml and not has_cookie:
                    for k, v in sorted(cookie.items()):
                        self.headers.add_header('Set-Cookie', v.OutputString())

                start_response('200 OK', self.headers.items())
                return self.data

        except HttpRedirect, e:
            location = str(e)
            start_response(e.status, [('Location', location)])
            return [str(e)]

        except HttpError, e:
            status = getattr(e, 'status', '500 Internal Server Error')
            start_response(status, [('Content-Type', 'text/html')])
            return [str(e)]

        except Exception, e:
            # Print out a nicely rendered traceback of the error.
            status = getattr(e, 'status', '200 OK')
            start_response(status, [('Content-Type', 'text/html')])
            failsafe = traceback.format_exc()
            try:
                return [cgitb.html(sys.exc_info())]
            except Exception:
                return ['<pre>', failsafe, '</pre>']




class Context(object):
    """
    An object that contains whatever input parameters or path components for a
    request.
    """


class Mapper(object):
    """Given a desdcription of the pages in the system, build a simple mapper
    object."""
    def __init__(self, page_directory):
        self.direc = page_directory

        self.match_expressions = []
        self.fwd_map = {}

        for rid, handler, render, regexp in self.direc:
            assert handler is not None
            assert render is not None
            if rid:
                self.fwd_map[rid] = render

            if regexp is None:
                regexp = '^%s$' % render
            self.match_expressions.append( (re.compile(regexp), handler) )

    def match(self, path):
        """Try to match the given path to one of our page handlers.
        Return the (handler, var-dict) as a result."""
        for xre, page in self.match_expressions:
            mo = xre.match(path)
            if mo:
                return page, mo.groupdict()
        else:
            return None, None

    def map(self, rid, *args, **kwds):
        """Map a URL forward."""
        url = self.fwd_map[rid] % args
        if kwds:
            query = []
            for kv in kwds.iteritems():
                query.append('%s=%s' % kv)
            url += '?' + '&'.join(query)
        return url





def main():
    import optparse
    parser = optparse.OptionParser(__doc__.strip())

    cmdline.addopts(parser)
    parser.add_option('-d', '--debug', '--devel', action='store_true',
                      help="Debug/development mode: don't cache styles and "
                      "reload code on every request.")

    parser.add_option('-p', '--port', action='store', type='int',
                      default=8080,
                      help="Port to use for local web server.")

    parser.add_option('-T', '--title', action='store',
                      help="Title to display in the web interface.")

    parser.add_option('--conversion', '--convert',
                      action='append', metavar='CONVERSION', default=[],
                      help="Apply the given conversion to wallets before "
                      "displaying them. The option's format should like "
                      "this: '1 EUR = 1.28 USD'.")

    opts, ledger, args = cmdline.main(parser)

    # Parse the specified conversions.
    opts.conversions = []
    for cstr in opts.conversion:
        side = '([0-9.]+)\s+([A-Z]{3})'
        mo = re.match('\s*%s\s*=\s*%s\s*' % (side, side), cstr)
        amt1, amt2 = map(Decimal, mo.group(1, 3))
        comm1, comm2 = mo.group(2, 4)
        opts.conversions.append( (comm1, comm2, amt2/amt1) )

    # Re-enable interrupts.
    import signal; signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Create and run the web server.
    app = BeanServer(ledger, opts)
    httpd = make_server('', opts.port, app)
    sa = httpd.socket.getsockname()
    print ("Ready. ( http://%s:%s )" % (sa[0], sa[1]))
    try:
        while 1:
            httpd.handle_request()  # serve one request, then exit
    except KeyboardInterrupt:
        print 'Interrupted.'


########NEW FILE########
__FILENAME__ = ofx-ba
#!/usr/bin/python
import time, os, httplib, urllib2
import sys

join = str.join

sites = {
		"MYCreditUnion": {
                	"caps": [ "SIGNON", "BASTMT" ],
			"fid": "31337",     # ^- this is what i added, for checking/savings/debit accounts- think "bank statement"
			"fiorg": "MyCreditUnion", 
			"url": "https://ofx.mycreditunion.org",
			"bankid": "21325412453", # bank routing #
		}	
   }
												
def _field(tag,value):
    return "<"+tag+">"+value

def _tag(tag,*contents):
    return join("\r\n",["<"+tag+">"]+list(contents)+["</"+tag+">"])

def _date():
    return time.strftime("%Y%m%d%H%M%S",time.localtime())

def _genuuid():
    return os.popen("uuidgen").read().rstrip().upper()

class OFXClient:
    """Encapsulate an ofx client, config is a dict containg configuration"""
    def __init__(self, config, user, password):
        self.password = password
        self.user = user
        self.config = config
        self.cookie = 3
        config["user"] = user
        config["password"] = password
        if not config.has_key("appid"):
            config["appid"] = "QWIN"  # i've had to fake Quicken to actually get my unwilling test server to talk to me
            config["appver"] = "1200"

    def _cookie(self):
        self.cookie += 1
        return str(self.cookie)

    """Generate signon message"""
    def _signOn(self):
        config = self.config
        fidata = [ _field("ORG",config["fiorg"]) ]
        if config.has_key("fid"):
            fidata += [ _field("FID",config["fid"]) ]
        return _tag("SIGNONMSGSRQV1",
                    _tag("SONRQ",
                         _field("DTCLIENT",_date()),
                         _field("USERID",config["user"]),
                         _field("USERPASS",config["password"]),
                         _field("LANGUAGE","ENG"),
                         _tag("FI", *fidata),
                         _field("APPID",config["appid"]),
                         _field("APPVER",config["appver"]),
                         ))

    def _acctreq(self, dtstart):
        req = _tag("ACCTINFORQ",_field("DTACCTUP",dtstart))
        return self._message("SIGNUP","ACCTINFO",req)

# this is from _ccreq below and reading page 176 of the latest OFX doc.
    def _bareq(self, acctid, dtstart, accttype):
    	config=self.config
	req = _tag("STMTRQ",
		   _tag("BANKACCTFROM",
		   	_field("BANKID",sites [argv[1]] ["bankid"]),
		        _field("ACCTID",acctid),
			_field("ACCTTYPE",accttype)),
		   _tag("INCTRAN",
		   	_field("DTSTART",dtstart),
			_field("INCLUDE","Y")))
	return self._message("BANK","STMT",req)
	
    def _ccreq(self, acctid, dtstart):
        config=self.config
        req = _tag("CCSTMTRQ",
                   _tag("CCACCTFROM",_field("ACCTID",acctid)),
                   _tag("INCTRAN",
                        _field("DTSTART",dtstart),
                        _field("INCLUDE","Y")))
        return self._message("CREDITCARD","CCSTMT",req)

    def _invstreq(self, brokerid, acctid, dtstart):
        dtnow = time.strftime("%Y%m%d%H%M%S",time.localtime())
        req = _tag("INVSTMTRQ",
                   _tag("INVACCTFROM",
                      _field("BROKERID", brokerid),
                      _field("ACCTID",acctid)),
                   _tag("INCTRAN",
                        _field("DTSTART",dtstart),
                        _field("INCLUDE","Y")),
                   _field("INCOO","Y"),
                   _tag("INCPOS",
                        _field("DTASOF", dtnow),
                        _field("INCLUDE","Y")),
                   _field("INCBAL","Y"))
        return self._message("INVSTMT","INVSTMT",req)

    def _message(self,msgType,trnType,request):
        config = self.config
        return _tag(msgType+"MSGSRQV1",
                    _tag(trnType+"TRNRQ",
                         _field("TRNUID",_genuuid()),
                         _field("CLTCOOKIE",self._cookie()),
                         request))
    
    def _header(self):
        return join("\r\n",[ "OFXHEADER:100",
                           "DATA:OFXSGML",
                           "VERSION:102",
                           "SECURITY:NONE",
                           "ENCODING:USASCII",
                           "CHARSET:1252",
                           "COMPRESSION:NONE",
                           "OLDFILEUID:NONE",
                           "NEWFILEUID:"+_genuuid(),
                           ""])

    def baQuery(self, acctid, dtstart, accttype):
    	"""Bank account statement request"""
        return join("\r\n",[self._header(),
 	                  _tag("OFX",
                                self._signOn(),
                                self._bareq(acctid, dtstart, accttype))])
						
    def ccQuery(self, acctid, dtstart):
        """CC Statement request"""
        return join("\r\n",[self._header(),
                          _tag("OFX",
                               self._signOn(),
                               self._ccreq(acctid, dtstart))])

    def acctQuery(self,dtstart):
        return join("\r\n",[self._header(),
                          _tag("OFX",
                               self._signOn(),
                               self._acctreq(dtstart))])

    def invstQuery(self, brokerid, acctid, dtstart):
        return join("\r\n",[self._header(),
                          _tag("OFX",
                               self._signOn(),
                               self._invstreq(brokerid, acctid,dtstart))])

    def doQuery(self,query,name):
        # N.B. urllib doesn't honor user Content-type, use urllib2
        request = urllib2.Request(self.config["url"],
                                  query,
                                  { "Content-type": "application/x-ofx",
                                    "Accept": "*/*, application/x-ofx"
                                  })
        if 1:
            f = urllib2.urlopen(request)
            response = f.read()
            f.close()
            
            f = file(name,"w")
            f.write(response)
            f.close()
	else:
            print request
            print self.config["url"], query
        
        # ...

import getpass
argv = sys.argv
if __name__=="__main__":
    dtstart = time.strftime("%Y%m%d",time.localtime(time.time()-31*86400))
    dtnow = time.strftime("%Y%m%d",time.localtime())
    if len(argv) < 3:
        print "Usage:",sys.argv[0], "site user [account] [CHECKING/SAVINGS/.. if using BASTMT]"
        print "available sites:",join(", ",sites.keys())
        sys.exit()
    passwd = getpass.getpass()
    client = OFXClient(sites[argv[1]], argv[2], passwd)
    if len(argv) < 4:
       query = client.acctQuery("19700101000000")
       client.doQuery(query, argv[1]+"_acct.ofx") 
    else:
       if "CCSTMT" in sites[argv[1]]["caps"]:
          query = client.ccQuery(sys.argv[3], dtstart)
       elif "INVSTMT" in sites[argv[1]]["caps"]:
          query = client.invstQuery(sites[argv[1]]["fiorg"], sys.argv[3], dtstart)
       elif "BASTMT" in sites[argv[1]]["caps"]:
          query = client.baQuery(sys.argv[3], dtstart, sys.argv[4])
       client.doQuery(query, argv[1]+dtnow+".ofx")


########NEW FILE########
__FILENAME__ = ofx
#!/usr/bin/python
import time, os, httplib, urllib2
import sys

join = str.join

sites = {
       "ucard": {
                 "caps": [ "SIGNON", "CCSTMT" ],
                  "fid": "24909",
                "fiorg": "Citigroup",
                  "url": "https://secureofx2.bankhost.com/citi/cgi-forte/ofx_rt?servicename=ofx_rt&pagename=ofx",
                },
    "discover": {
                 "caps": [ "SIGNON", "CCSTMT" ],
                "fiorg": "Discover Financial Services",
                  "fid": "7101",
                  "url": "https://ofx.discovercard.com/",
                },
     "ameritrade": {
                 "caps": [ "SIGNON", "INVSTMT" ],
                "fiorg": "ameritrade.com",
                  "url": "https://ofx.ameritrade.com/ofxproxy/ofx_proxy.dll",
                } 
    }

def _field(tag,value):
    return "<"+tag+">"+value

def _tag(tag,*contents):
    return join("\r\n",["<"+tag+">"]+list(contents)+["</"+tag+">"])

def _date():
    return time.strftime("%Y%m%d%H%M%S",time.localtime())

def _genuuid():
    return os.popen("uuidgen").read().rstrip().upper()

class OFXClient:
    """Encapsulate an ofx client, config is a dict containg configuration"""
    def __init__(self, config, user, password):
        self.password = password
        self.user = user
        self.config = config
        self.cookie = 3
        config["user"] = user
        config["password"] = password
        if not config.has_key("appid"):
            config["appid"] = "PyOFX"
            config["appver"] = "0100"

    def _cookie(self):
        self.cookie += 1
        return str(self.cookie)

    """Generate signon message"""
    def _signOn(self):
        config = self.config
        fidata = [ _field("ORG",config["fiorg"]) ]
        if config.has_key("fid"):
            fidata += [ _field("FID",config["fid"]) ]
        return _tag("SIGNONMSGSRQV1",
                    _tag("SONRQ",
                         _field("DTCLIENT",_date()),
                         _field("USERID",config["user"]),
                         _field("USERPASS",config["password"]),
                         _field("LANGUAGE","ENG"),
                         _tag("FI", *fidata),
                         _field("APPID",config["appid"]),
                         _field("APPVER",config["appver"]),
                         ))

    def _acctreq(self, dtstart):
        req = _tag("ACCTINFORQ",_field("DTACCTUP",dtstart))
        return self._message("SIGNUP","ACCTINFO",req)

    def _ccreq(self, acctid, dtstart):
        config=self.config
        req = _tag("CCSTMTRQ",
                   _tag("CCACCTFROM",_field("ACCTID",acctid)),
                   _tag("INCTRAN",
                        _field("DTSTART",dtstart),
                        _field("INCLUDE","Y")))
        return self._message("CREDITCARD","CCSTMT",req)

    def _invstreq(self, brokerid, acctid, dtstart):
        dtnow = time.strftime("%Y%m%d%H%M%S",time.localtime())
        req = _tag("INVSTMTRQ",
                   _tag("INVACCTFROM",
                      _field("BROKERID", brokerid),
                      _field("ACCTID",acctid)),
                   _tag("INCTRAN",
                        _field("DTSTART",dtstart),
                        _field("INCLUDE","Y")),
                   _field("INCOO","Y"),
                   _tag("INCPOS",
                        _field("DTASOF", dtnow),
                        _field("INCLUDE","Y")),
                   _field("INCBAL","Y"))
        return self._message("INVSTMT","INVSTMT",req)

    def _message(self,msgType,trnType,request):
        config = self.config
        return _tag(msgType+"MSGSRQV1",
                    _tag(trnType+"TRNRQ",
                         _field("TRNUID",_genuuid()),
                         _field("CLTCOOKIE",self._cookie()),
                         request))
    
    def _header(self):
        return join("\r\n",[ "OFXHEADER:100",
                           "DATA:OFXSGML",
                           "VERSION:102",
                           "SECURITY:NONE",
                           "ENCODING:USASCII",
                           "CHARSET:1252",
                           "COMPRESSION:NONE",
                           "OLDFILEUID:NONE",
                           "NEWFILEUID:"+_genuuid(),
                           ""])

    def ccQuery(self, acctid, dtstart):
        """CC Statement request"""
        return join("\r\n",[self._header(),
                          _tag("OFX",
                               self._signOn(),
                               self._ccreq(acctid, dtstart))])

    def acctQuery(self,dtstart):
        return join("\r\n",[self._header(),
                          _tag("OFX",
                               self._signOn(),
                               self._acctreq(dtstart))])

    def invstQuery(self, brokerid, acctid, dtstart):
        return join("\r\n",[self._header(),
                          _tag("OFX",
                               self._signOn(),
                               self._invstreq(brokerid, acctid,dtstart))])

    def doQuery(self,query,name):
        # N.B. urllib doesn't honor user Content-type, use urllib2
        request = urllib2.Request(self.config["url"],
                                  query,
                                  { "Content-type": "application/x-ofx",
                                    "Accept": "*/*, application/x-ofx"
                                  })
        if 1:
            f = urllib2.urlopen(request)
            response = f.read()
            f.close()
            
            f = file(name,"w")
            f.write(response)
            f.close()
	else:
            print request
            print self.config["url"], query
        
        # ...

import getpass
argv = sys.argv
if __name__=="__main__":
    dtstart = time.strftime("%Y%m%d",time.localtime(time.time()-31*86400))
    dtnow = time.strftime("%Y%m%d",time.localtime())
    if len(argv) < 3:
        print "Usage:",sys.argv[0], "site user [account]"
        print "available sites:",join(", ",sites.keys())
        sys.exit()
    passwd = getpass.getpass()
    client = OFXClient(sites[argv[1]], argv[2], passwd)
    if len(argv) < 4:
       query = client.acctQuery("19700101000000")
       client.doQuery(query, argv[1]+"_acct.ofx") 
    else:
       if "CCSTMT" in sites[argv[1]]["caps"]:
          query = client.ccQuery(sys.argv[3], dtstart)
       elif "INVSTMT" in sites[argv[1]]["caps"]:
          query = client.invstQuery(sites[argv[1]]["fiorg"], sys.argv[3], dtstart)
       client.doQuery(query, argv[1]+dtnow+".ofx")


########NEW FILE########
__FILENAME__ = fscmd
#!/usr/bin/env python
"""
A command object that provides commands to work interactively on a tree
hierarchy of nodes similar to a filesystem. The underlying backend is abstracted
and only a few functions have to be provided in order to implement it.
"""

# stdlib imports
import sys, os, cmd, optparse, traceback, logging
from operator import itemgetter
from itertools import imap
from os.path import *



class ResilientParser(optparse.OptionParser):
    "An options parser that does not exit when there is an error."

    def exit(self, status=0, msg=None):
        raise optparse.OptParseError(msg)

class HierarchicalCmd(cmd.Cmd, object):
    """
    A version of Cmd which allows the user to navigate some hierarchy siimlar to
    a file hierarchy.
    """

    prompt = 'bean> '

    def __init__(self):
        cmd.Cmd.__init__(self)

        # The home directory (by default it is the root node).
        self.home = self.get_root_node()

        # The current working directory.
        self.cwd = None
        self.cwdpath = None
        self.cd(self.home)

## FIXME: todo add default and completion handling.
    ## def default(self, line):
    ##     trace('DEFAULT', line)

    ## def completedefault(self, text, line, begidx, endidx):
    ##     pass

    def cmdloop(self):
        while 1:
            try:
                cmd.Cmd.cmdloop(self)
            except Exception, e:
                traceback.print_exc()
                self.stdout.write(str(e) + '\n')
            except KeyboardInterrupt:
                print '\n(Interrupted).'
                pass
            else:
                print
                break

    def parseline(self, line):
        cmd, args, line = super(HierarchicalCmd, self).parseline(line)
        args = splitargs(args)

        parser = getattr(self, 'parser_%s' % cmd, None)
        if parser is not None:
            opts, args = parser.parse_args(args)
        else:
            opts = None

        return cmd, (opts, args), line

    def emptyline(self):
        pass

    def perr(self, s):
        sys.stderr.write("Error: %s\n" % s)



    # ----- Commands ----------------------------------------------------------

    def do_exit(self, _):
        "Exit the shell."
        return True
    do_EOF = do_quit = do_exit

    def do_pwd(self, _):
        "Print name of current/working node."
        path = self.getpath(self.cwd)
        self.stdout.write(path + '\n')

    def do_cd(self, (opts, args)):
        "Change the working node."
        if len(args) > 1:
            return self.perr("Too many arguments.")

        args = [expand(arg, self.cwdpath) for arg in args]
        if not args:
            new_node = self.home
            self.do_pwd(None)

        else:
            node = self.getnode(args[0])
            if node is not None:
                new_node = node
            else:
                return self.perr("Invalid path.")
        self.cd(new_node)

    parser_ls = ResilientParser()
    parser_ls.add_option('-l', '--long', action='store_true',
                         help="Use a long listing format.")
    parser_ls.add_option('-R', '--recursive', action='store_true',
                         help="List nodes recursively.")
    parser_ls.add_option('-r', action='store_true',  # ignored
                         help=optparse.SUPPRESS_HELP)
    parser_ls.add_option('-t', action='store_true',  # ignored
                         help=optparse.SUPPRESS_HELP)

## FIXME: implement -d option.

    def do_ls(self, (opts, args)):
        "List contents of the nodes passed in as arguments."
        args = [expand(arg, self.cwdpath) for arg in args]

        simple_walk = lambda x: imap(itemgetter(0), self.walk(x))
        iterfun = simple_walk if opts.recursive else self.listdir

        fmt = self.fmt_long if opts.long else self.fmt_short

        if not args:
            args = (self.cwdpath,)
        for arg in args:
            write = self.stdout.write

            node = self.getnode(arg)
            if node is None:
                self.perr("ls: cannot access %s: No such node." % arg)
                continue

            if not opts.recursive:
                for child in iterfun(node):
                    m = self.stat(child)
                    if m is None:
                        logging.error("Could not stat '%s'." % child)
                    write(fmt % m + '\n')
            else:
                for child in iterfun(node):
                    m = self.stat(child)
                    if m is None:
                        logging.error("Could not stat '%s'." % child)
                    m['name'] = self.getpath(child, relto=node)
                    write(fmt % m + '\n')

    def do_stat(self, (opts, args)):
        "Stat the node and print the output."

        args = [expand(arg, self.cwdpath) for arg in args]
        for arg in args:
            node = self.getnode(arg)
            if node is None:
                self.perr("Node '%s' does not exist." % arg)
            print
            print '%s:' % arg
            for x in sorted(self.stat(node).iteritems()):
                print '%s: %s' % x
        if args:
            print

    def do_mkdir(self, (opts, args)):
        "Make nodes."
        if not args:
            return self.perr("You must provide at least a node name.")
        dn = expand(args[0], self.cwdpath)
        self.mkdir(dn, *args[1:])

    def do_rmdir(self, (opts, args)):
        "Remove nodes."
        if not args:
            return self.perr("You must provide at least a node name.")
        dn = expand(args[0], self.cwdpath)
        self.rmdir(dn, *args[1:])

    parser_rm = ResilientParser()
    parser_rm.add_option('-r', '--recursive', action='store_true',
                         help="Remove nodes recursively.")
    parser_rm.add_option('-f', '--force', action='store_true',
                         help="Remove nodes and their contents.")

    def do_rm(self, (opts, args)):
        "Remove nodes or node contents."
        if not args:
            return self.perr("You must provide the names of the nodes to remove.")
        args = [expand(arg, self.cwdpath) for arg in args]
        for arg in args:
            node = self.getnode(arg)
            if node is None:
                self.perr("Node '%s' not found." % arg)
                continue

            if opts.recursive:
                for wnode, subnodes in self.walk(node, topdown=False):
                    if opts.force:
                        self.remove_node_contents(wnode)
                    self.remove(wnode)
            else:
                if opts.force:
                    self.remove_node_contents(wnode)
                self.remove(node)

    def do_mv(self, (opts, args)):
        "Move (rename) node."
        if len(args) < 2:
            return self.perr("You must provide naems of nodes to move and target node.")

        src_paths = [expand(x, self.cwdpath) for x in args[:-1]]
        dst_path = expand(args[-1], self.cwdpath)

        # Check all source nodes first.
        src_nodes = []
        for src_path in src_paths:
            node = self.getnode(src_path)
            if node is None:
                return self.perr("Source '%s' does not exist." % src_path)
            src_nodes.append(node)

        if len(src_nodes) > 1:
            # Insure that the destination exists.
            dst_node = self.getnode(dst_path)
            if dst_node is None:
                return self.perr("Target '%s' does not exist." % dst_path)

            # We do the actual reparenting after all nodes verify.
            for node in src_nodes:
                self.set_parent(node, dst_node)

        else:
            dst_node = self.getnode(dst_path)
            if dst_node is not None:
                # This is a move into a directory that already exists.
                parent = dst_node
                name = None

            else:
                # This is a rename. The parent of the renamed node must exist.
                dst_node = self.getnode(dirname(dst_path))
                if dst_node is None:
                    return self.perr("Cannot move into '%s', no such file or directory." %
                                     dirname(dst_path))
                parent = dst_node
                name = basename(dst_path)

            if parent:
                node = src_nodes[0]
                old_parent = self.get_node_parent(node)
                if parent != old_parent:
                    self.set_parent(node, parent)

                if name is not None:
                    self.set_name(node, name)

    def do_debug(self, (opts, args)):
        for x in self.walk():
            print x

    def do_tree(self, (opts, args)):
        trace('FIXME: not implemented.')


    #---------------------------------------------------------------------------
    # Various functions tha deal with the conversion of pathnames to nodes and
    # vice-versa.

    def getpath(self, node, relto=None):
        """
        Given a node-id, return the absolute path it corresponds to.
        If 'relto' is specified, return the path relative to the given node.
        """
        assert isinstance(node, int)

        # Walk up the tree to obtain all the names.
        names = []
        while node is not None:
            name, parent = self.stat_short(node)
            names.append(name)
            if relto is not None and node == relto:
                break
            node = parent

        # Note: we cut away the root node on purpose. The root node is expected
        # to be unique as well.
        names.pop()

        path = os.sep.join(reversed(names))
        if parent is None:
            path = '/' + path
        return path

    def getnode(self, path):
        """
        Return the id of node given the path. If the node is not found, return
        None. 'path' must be an absolute path.
        """
        # We need to start from the root and
        assert self.isabs(path), "Path '%s' is not absolute." % path
        node = self.get_root_node()
        if path.startswith(os.sep):
            path = path[1:]
        comps = [c for c in path.split(os.sep) if c]
        for c in comps:
            node = self.get_child_node(node, c)
            if node is None:
                break
        return node

    def cd(self, node):
        self.cwd = node
        self.cwdpath = self.getpath(self.cwd)
        self.prompt = '[bean] %03s %s> ' % (self.cwd, self.cwdpath)

    def isabs(self, path):
        "Return true if the path is absolute (vs. relative)."
        return path.startswith('/')

    def isdir(self, path):
        """
        Return some node object if the given path exists in the database and is
        a container node (directory). Return None if the path is invalid.
        """
        return self.getnode(path) is not None

    def mkdir(self, path, *args):
        """
        Args may optionally contain the security to use for creating the account.
        """
        dn, bn = dirname(path), basename(path)
        parent_node = self.getnode(dn)
        if parent_node is None:
            return self.perr("The parent directory '%s' does not exist." % dn)
        self.create(parent_node, bn, *args)

    def rmdir(self, path, *args):
        """
        Args may optionally contain the security to use for creating the account.
        """
        node = self.getnode(path)
        if node is None:
            return self.perr("The parent directory '%s' does not exist." % dn)
        self.remove(node, *args)

    def walk(self, node=None, topdown=True):
        """
        Generate the tree nodes in-order, starting from the given node (or the
        root node, if not specified). This method yields pairs of (node,
        childlist). If 'topdown' is True, yield the nodes pre-order, otherwise
        yield the nodes post-order.
        """
        if node is None:
            node = self.get_root_node()
        children = self.listdir(node)
        if topdown:
            yield node, children
        for child in children:
            for x in self.walk(child, topdown):
                yield x
        if not topdown:
            yield node, children


    # ----- kernel interface -----------------------------------------------
    # Override this interface to provide the actual storage.

    def stat(self, node):
        "Return all the attributes of the given node, as a dict."
        raise NotImplementedError

    def stat_short(self, node):
        "Return the (name, parent node) of the given node."
        raise NotImplementedError

    def get_root_node(self):
        "Return the root node."
        raise NotImplementedError

    def get_node_parent(self, node):
        "Return the parent of the given node."
        raise NotImplementedError

    def get_child_node(self, parent, name):
        "Given a parent node and a name, return the corresponding child node."
        raise NotImplementedError

    def listdir(self, node):
        "Return a list of the child nodes."
        raise NotImplementedError

    def create(self, parent, name, *args):
        "Create a new node, with the backend specific 'args'."
        raise NotImplementedError

    def remove(self, node):
        "Remove a node. If the node has children, their parent is set to null."
        raise NotImplementedError

    def remove_node_contents(self, node):
        "Remove the contents of a node."
        raise NotImplementedError

    def set_parent(self, node, parent):
        "Change the parent of 'node' to 'parent'."
        raise NotImplementedError

    def set_name(self, node, name):
        "Change the name of 'node' to 'name'."
        raise NotImplementedError



########NEW FILE########
__FILENAME__ = ledger-submit-bug
#!/usr/bin/env python

Username = username
Password = password

import re
import sys

print "Please enter a description for this bug:"
desc = sys.stdin.read()

print "Thank you; your bug is now being submitted."

from mechanize import Browser

br = Browser()
br.add_password("http://trac.newartisans.com/ledger/login",
                Username, Password)

print "Logging in to the Trac ..."
br.open("http://trac.newartisans.com/ledger/login")
assert br.viewing_html()

# follow second link with element text matching regular expression
print "Opening the New Ticket page ..."
resp1 = br.open("http://trac.newartisans.com/ledger/newticket")

newticket = None
index = 0
for form in br.forms():
    if index == 1:
        newticket = form
        break
    index += 1
br.form = newticket

br["summary"]     = sys.argv[1]
br["description"] = desc
br["owner"]       = ["johnw"]

print "Submitting the ticket ..."
br.submit(nr=1)                 # submit the bug!

print "Done!  Your bug is entered."

########NEW FILE########
