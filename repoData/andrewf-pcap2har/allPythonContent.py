__FILENAME__ = main
#!/usr/bin/env python

'''
Main program that converts pcaps to HAR's.
'''

import os
import optparse
import logging
import sys
import json

from pcap2har import pcap
from pcap2har import http
from pcap2har import httpsession
from pcap2har import har
from pcap2har import tcp
from pcap2har import settings
from pcap2har.packetdispatcher import PacketDispatcher
from pcap2har.pcaputil import print_rusage


# get cmdline args/options
parser = optparse.OptionParser(
    usage='usage: %prog inputfile outputfile'
)
parser.add_option('--no-pages', action='store_false',
                  dest='pages', default=True)
parser.add_option('-d', '--drop-bodies', action='store_true',
                  dest='drop_bodies', default=False)
parser.add_option('-k', '--keep-unfulfilled-requests', action='store_true',
                  dest='keep_unfulfilled', default=False)
parser.add_option('-r', '--resource-usage', action='store_true',
                  dest='resource_usage', default=False)
parser.add_option('--pad_missing_tcp_data', action='store_true',
                  dest='pad_missing_tcp_data', default=False)
parser.add_option('--strict-http-parsing', action='store_true',
                  dest='strict_http_parsing', default=False)
parser.add_option('-l', '--log', dest='logfile', default='pcap2har.log')
options, args = parser.parse_args()

# copy options to settings module
settings.process_pages = options.pages
settings.drop_bodies = options.drop_bodies
settings.keep_unfulfilled_requests = options.keep_unfulfilled
settings.pad_missing_tcp_data = options.pad_missing_tcp_data
settings.strict_http_parse_body = options.strict_http_parsing

# setup logs
logging.basicConfig(filename=options.logfile, level=logging.INFO)

# get filenames, or bail out with usage error
if len(args) == 2:
    inputfile, outputfile = args[0:2]
elif len(args) == 1:
    inputfile = args[0]
    outputfile = inputfile+'.har'
else:
    parser.print_help()
    sys.exit()

logging.info('Processing %s', inputfile)

# parse pcap file
dispatcher = pcap.EasyParsePcap(filename=inputfile)

# parse HAR stuff
session = httpsession.HttpSession(dispatcher)

logging.info('Flows=%d. HTTP pairs=%d' % (len(session.flows), len(session.entries)))

#write the HAR file
with open(outputfile, 'w') as f:
    json.dump(session, f, cls=har.JsonReprEncoder, indent=2, encoding='utf8', sort_keys=True)

if options.resource_usage:
    print_rusage()

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

Copyright (c) 2004-2010, Leonard Richardson

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
__version__ = "3.0.8.1"
__copyright__ = "Copyright (c) 2004-2010 Leonard Richardson"
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
try:
    set
except NameError:
    from sets import Set as set

#These hacks make Beautiful Soup able to parse XML with namespaces
sgmllib.tagfind = re.compile('[a-zA-Z][-_.:a-zA-Z0-9]*')
markupbase._declname_match = re.compile(r'[a-zA-Z][-_.:a-zA-Z0-9]*\s*').match

DEFAULT_OUTPUT_ENCODING = "utf-8"

def _match_css_class(str):
    """Build a RE to match the given CSS class."""
    return re.compile(r"(^|.*\s)%s($|\s)" % str)

# First, the classes that represent markup elements.

class PageElement(object):
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
        myIndex = self.parent.index(self)
        if hasattr(replaceWith, "parent")\
                  and replaceWith.parent is self.parent:
            # We're replacing this element with one of its siblings.
            index = replaceWith.parent.index(replaceWith)
            if index and index < myIndex:
                # Furthermore, it comes before this element. That
                # means that when we extract it, the index of this
                # element will change.
                myIndex = myIndex - 1
        self.extract()
        oldParent.insert(myIndex, replaceWith)

    def replaceWithChildren(self):
        myParent = self.parent
        myIndex = self.parent.index(self)
        self.extract()
        reversedChildren = list(self.contents)
        reversedChildren.reverse()
        for child in reversedChildren:
            myParent.insert(myIndex, child)

    def extract(self):
        """Destructively rips this element out of the tree."""
        if self.parent:
            try:
                del self.parent.contents[self.parent.index(self)]
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
        if isinstance(newChild, basestring) \
            and not isinstance(newChild, NavigableString):
            newChild = NavigableString(newChild)

        position =  min(position, len(self.contents))
        if hasattr(newChild, 'parent') and newChild.parent is not None:
            # We're 'inserting' an element that's already one
            # of this object's children.
            if newChild.parent is self:
                index = self.index(newChild)
                if index > position:
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
        # (Possibly) special case some findAll*(...) searches
        elif text is None and not limit and not attrs and not kwargs:
            # findAll*(True)
            if name is True:
                return [element for element in generator()
                        if isinstance(element, Tag)]
            # findAll*('tag-name')
            elif isinstance(name, basestring):
                return [element for element in generator()
                        if isinstance(element, Tag) and
                        element.name == name]
            else:
                strainer = SoupStrainer(name, attrs, text, **kwargs)
        # Build a SoupStrainer
        else:
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
        while i is not None:
            i = i.next
            yield i

    def nextSiblingGenerator(self):
        i = self
        while i is not None:
            i = i.nextSibling
            yield i

    def previousGenerator(self):
        i = self
        while i is not None:
            i = i.previous
            yield i

    def previousSiblingGenerator(self):
        i = self
        while i is not None:
            i = i.previousSibling
            yield i

    def parentGenerator(self):
        i = self
        while i is not None:
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
        if attrs is None:
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

    def getString(self):
        if (len(self.contents) == 1
            and isinstance(self.contents[0], NavigableString)):
            return self.contents[0]

    def setString(self, string):
        """Replace the contents of the tag with a string"""
        self.clear()
        self.append(string)

    string = property(getString, setString)

    def getText(self, separator=u""):
        if not len(self.contents):
            return u""
        stopNode = self._lastRecursiveChild().next
        strings = []
        current = self.contents[0]
        while current is not stopNode:
            if isinstance(current, NavigableString):
                strings.append(current.strip())
            current = current.next
        return separator.join(strings)

    text = property(getText)

    def get(self, key, default=None):
        """Returns the value of the 'key' attribute for the tag, or
        the value given for 'default' if it doesn't have that
        attribute."""
        return self._getAttrMap().get(key, default)

    def clear(self):
        """Extract all children."""
        for child in self.contents[:]:
            child.extract()

    def index(self, element):
        for i, child in enumerate(self.contents):
            if child is element:
                return i
        raise ValueError("Tag.index: element not in tag")

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
        if other is self:
            return True
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
                if isinstance(val, basestring):
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
        self.extract()
        if len(self.contents) == 0:
            return
        current = self.contents[0]
        while current is not None:
            next = current.next
            if isinstance(current, Tag):
                del current.contents[:]
            current.parent = None
            current.previous = None
            current.previousSibling = None
            current.next = None
            current.nextSibling = None
            current = next

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
        # Just use the iterator from the contents
        return iter(self.contents)

    def recursiveChildGenerator(self):
        if not len(self.contents):
            raise StopIteration
        stopNode = self._lastRecursiveChild().next
        current = self.contents[0]
        while current is not stopNode:
            yield current
            current = current.next


# Next, a couple classes to represent queries and their results.
class SoupStrainer:
    """Encapsulates a number of ways of matching a markup element (tag or
    text)."""

    def __init__(self, name=None, attrs={}, text=None, **kwargs):
        self.name = name
        if isinstance(attrs, basestring):
            kwargs['class'] = _match_css_class(attrs)
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
        if hasattr(markup, "__iter__") \
                and not isinstance(markup, Tag):
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
                 isinstance(markup, basestring):
            if self._matches(markup, self.text):
                found = markup
        else:
            raise Exception, "I don't know how to match against a %s" \
                  % markup.__class__
        return found

    def _matches(self, markup, matchAgainst):
        #print "Matching %s against %s" % (markup, matchAgainst)
        result = False
        if matchAgainst is True:
            result = markup is not None
        elif callable(matchAgainst):
            result = matchAgainst(markup)
        else:
            #Custom match methods take the tag as an argument, but all
            #other ways of matching match the tag name as a string.
            if isinstance(markup, Tag):
                markup = markup.name
            if markup and not isinstance(markup, basestring):
                markup = unicode(markup)
            #Now we know that chunk is either a string, or None.
            if hasattr(matchAgainst, 'match'):
                # It's a regexp object.
                result = markup and matchAgainst.search(markup)
            elif hasattr(matchAgainst, '__iter__'): # list-like
                result = markup in matchAgainst
            elif hasattr(matchAgainst, 'items'):
                result = markup.has_key(matchAgainst)
            elif matchAgainst and isinstance(markup, basestring):
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
        elif hasattr(portion, '__iter__'): # is a list
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
                if not hasattr(self.markupMassage, "__iter__"):
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

        if methodName.startswith('start_') or methodName.startswith('end_') \
               or methodName.startswith('do_'):
            return SGMLParser.__getattr__(self, methodName)
        elif not methodName.startswith('__'):
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
            if (nestingResetTriggers is not None
                and p.name in nestingResetTriggers) \
                or (nestingResetTriggers is None and isResetNesting
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
            attrs = ''.join([' %s="%s"' % (x, y) for x, y in attrs])
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
                                    ('br' , 'hr', 'input', 'img', 'meta',
                                    'spacer', 'link', 'frame', 'base', 'col'))

    PRESERVE_WHITESPACE_TAGS = set(['pre', 'textarea'])

    QUOTE_TAGS = {'script' : None, 'textarea' : None}

    #According to the HTML standard, each of these inline tags can
    #contain another tag of the same type. Furthermore, it's common
    #to actually use these tags this way.
    NESTABLE_INLINE_TAGS = ('span', 'font', 'q', 'object', 'bdo', 'sub', 'sup',
                            'center')

    #According to the HTML standard, these block tags can contain
    #another tag of the same type. Furthermore, it's common
    #to actually use these tags this way.
    NESTABLE_BLOCK_TAGS = ('blockquote', 'div', 'fieldset', 'ins', 'del')

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

    NON_NESTABLE_BLOCK_TAGS = ('address', 'form', 'p', 'pre')

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
     ('em', 'big', 'i', 'small', 'tt', 'abbr', 'acronym', 'strong',
      'cite', 'code', 'dfn', 'kbd', 'samp', 'strong', 'var', 'b',
      'big')

    I_CANT_BELIEVE_THEYRE_NESTABLE_BLOCK_TAGS = ('noscript',)

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
        if isinstance(sub, tuple):
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
__FILENAME__ = dns
import logging


class Packet(object):
    '''
    A DNS packet, wrapped for convenience and with the pcap timestamp

    For the most part, assumes that there is only one question in the packet.
    Any others are recorded but not taken into account in any calculations

    Members:
    ts = timestamp
    names = list of names asked about
    dns = dpkt.dns.DNS
    '''

    def __init__(self, ts, pkt):
        '''
        ts = pcap timestamp
        pkt = dpkt.dns.DNS
        '''
        self.ts = ts
        self.dns = pkt
        self.txid = pkt.id
        self.names = [q.name for q in pkt.qd]
        if len(self.names) > 1:
            logging.warning('DNS packet with multiple questions')

    def name(self):
        return self.names[0]


class Query(object):
    '''
    A DNS question/answer conversation with a single ID

    Member:
    txid = id that all packets must match
    started_ts = time of first packet
    last_ts = time of last known packet
    name = domain name being discussed
    resolved = Bool, whether the question has been answered
    '''

    def __init__(self, initial_packet):
        '''
        initial_packet = dns.Packet, simply the first one on the wire with
        a given ID.
        '''
        self.txid = initial_packet.txid
        self.started_time = initial_packet.ts
        self.last_ts = initial_packet.ts
        self.resolved = False
        self.name = initial_packet.name()

    def add(self, pkt):
        '''
        pkt = dns.Packet
        '''
        assert pkt.txid == self.txid
        self.last_ts = max(pkt.ts, self.last_ts)
        # see if this resolves the query
        if len(pkt.dns.an) > 0:
            self.resolved = True

    def duration(self):
        return self.last_ts - self.started_time


class Processor(object):
    '''
    Processes and interprets DNS packets.

    Call its `add` method with each dns.Packet from the pcap.

    Members:
    queries = {txid: Query}
    by_hostname = {string: [Query]}
    '''

    def __init__(self):
        self.queries = {}
        self.by_hostname = {}

    def add(self, pkt):
        '''
        adds the packet to a Query object by id, and makes sure that Queryies
        are also index by hostname as well.

        pkt = dns.Packet
        '''
        if pkt.txid in self.queries:
            self.queries[pkt.txid].add(pkt)
        else:
            # if we're adding a new query, index it by name too
            new_query = Query(pkt)
            self.queries[pkt.txid] = new_query
            self.add_by_name(new_query)

    def add_by_name(self, query):
        name = query.name
        if name in self.by_hostname:
            self.by_hostname[name].append(query)
        else:
            self.by_hostname[name] = [query]

    def get_resolution_time(self, hostname):
        '''
        Returns the last time it took to resolve the hostname.

        Assumes that the lists in by_hostname are ordered by increasing time.
        Uses the figure from the last Query. If the hostname is not present,
        return None
        '''
        try:
            return self.by_hostname[hostname][-1].duration()
        except KeyError:
            return None

    def num_queries(self, hostname):
        '''
        Returns the number of DNS requests for that name
        '''
        try:
            return len(self.by_hostname[hostname])
        except KeyError:
            return 0

########NEW FILE########
__FILENAME__ = dpkt_http_replacement
# $Id: http.py 59 2010-03-24 15:31:17Z jon.oberheide $

"""Hypertext Transfer Protocol.

This version is modified by Andrew Fleenor, on 2 October 2010, to temporarily
fix the bug where a body is parsed for a request that shouldn't have a body."""

import cStringIO
import dpkt
import logging
import settings

def parse_headers(f):
    """Return dict of HTTP headers parsed from a file object."""
    d = {}
    while 1:
        line = f.readline()
        # regular dpkt checks for premature end of headers
        # but that's too picky
        line = line.strip()
        if not line:
            break
        l = line.split(None, 1)
        if not l[0].endswith(':'):
            raise dpkt.UnpackError('invalid header: %r' % line)
        k = l[0][:-1].lower()
        v = len(l) != 1 and l[1] or ''
        if k in d:
            d[k] += ','+v
        else:
            d[k] = v
    return d


def parse_length(s, base=10):
    """Take a string and convert to int (not long), returning 0 if invalid"""
    try:
        n = int(s, base)
        # int() can actually return long, which can't be used in file.read()
        if isinstance(n, int):
            return n
    except ValueError:
        pass
    # if s was invalid or too big (that is, int returned long)...
    logging.warn('Invalid HTTP content/chunk length "%s", assuming 0' % s)
    return 0


def parse_body(f, version, headers):
    """Return HTTP body parsed from a file object, given HTTP header dict."""
    if headers.get('transfer-encoding', '').lower() == 'chunked':
        l = []
        found_end = False
        while 1:
            try:
                sz = f.readline().split(None, 1)[0]
            except IndexError:
                raise dpkt.UnpackError('missing chunk size')
            n = parse_length(sz, 16)
            if n == 0:  # may happen if sz is invalid
                found_end = True
            buf = f.read(n)
            if f.readline().strip():
                break
            if n and len(buf) == n:
                l.append(buf)
            else:
                break
        if settings.strict_http_parse_body and not found_end:
            raise dpkt.NeedData('premature end of chunked body')
        body = ''.join(l)
    elif 'content-length' in headers:
        # Ethan K B: Have observed malformed 0,0 content lengths
        n = parse_length(headers['content-length'])
        body = f.read(n)
        if len(body) != n:
            logging.warn('HTTP content-length mismatch: expected %d, got %d', n,
                         len(body))
            if settings.strict_http_parse_body:
                raise dpkt.NeedData('short body (missing %d bytes)' % (n - len(body)))
    else:
        # XXX - need to handle HTTP/0.9
        # BTW, this function is not called if status code is 204 or 304
        if version == '1.0':
            # we can assume that there are no further
            # responses on this stream, since 1.0 doesn't
            # support keepalive
            body = f.read()
        elif (version == '1.1' and
              headers.get('connection', None) == 'close'):
            # sender has said they won't send anything else.
            body = f.read()
        # there's also the case where other end sends connection: close,
        # but we don't have the architecture to handle that.
        else:
            # we don't really know what to do
            #print 'returning body as empty string:', version, headers
            body = ''
    return body

def parse_message(message, f):
    """
    Unpack headers and optionally body from the passed file-like object.

    Args:
      message: Request or Response to which to add data.
      f: file-like object, probably StringIO.
    """
    # Parse headers
    message.headers = parse_headers(f)
    # Parse body, unless we know there isn't one
    if not (getattr(message, 'status', None) in ('204', '304')):
        message.body = parse_body(f, message.version, message.headers)
    else:
        message.body = ''
    # Save the rest
    message.data = f.read()

class Message(dpkt.Packet):
    """Hypertext Transfer Protocol headers + body."""
    __metaclass__ = type
    __hdr_defaults__ = {}
    headers = None
    body = None

    def __init__(self, *args, **kwargs):
        if args:
            self.unpack(args[0])
        else:
            self.headers = {}
            self.body = ''
            for k, v in self.__hdr_defaults__.iteritems():
                setattr(self, k, v)
            for k, v in kwargs.iteritems():
                setattr(self, k, v)

    def unpack(self, buf):
        f = cStringIO.StringIO(buf)
        parse_message(self, f)

    def pack_hdr(self):
        return ''.join([ '%s: %s\r\n' % t for t in self.headers.iteritems() ])

    def __len__(self):
        return len(str(self))

    def __str__(self):
        return '%s\r\n%s' % (self.pack_hdr(), self.body)

class Request(Message):
    """Hypertext Transfer Protocol Request."""
    __hdr_defaults__ = {
        'method':'GET',
        'uri':'/',
        'version':'1.0',
        }
    __methods = dict.fromkeys((
        'GET', 'PUT', 'ICY',
        'COPY', 'HEAD', 'LOCK', 'MOVE', 'POLL', 'POST',
        'BCOPY', 'BMOVE', 'MKCOL', 'TRACE', 'LABEL', 'MERGE',
        'DELETE', 'SEARCH', 'UNLOCK', 'REPORT', 'UPDATE', 'NOTIFY',
        'BDELETE', 'CONNECT', 'OPTIONS', 'CHECKIN',
        'PROPFIND', 'CHECKOUT', 'CCM_POST',
        'SUBSCRIBE', 'PROPPATCH', 'BPROPFIND',
        'BPROPPATCH', 'UNCHECKOUT', 'MKACTIVITY',
        'MKWORKSPACE', 'UNSUBSCRIBE', 'RPC_CONNECT',
        'VERSION-CONTROL',
        'BASELINE-CONTROL'
        ))
    __proto = 'HTTP'

    def unpack(self, buf):
        f = cStringIO.StringIO(buf)
        line = f.readline()
        l = line.strip().split()
        if len(l) != 3 or l[0] not in self.__methods or \
           not l[2].startswith(self.__proto):
            raise dpkt.UnpackError('invalid request: %r' % line)
        self.method = l[0]
        self.uri = l[1]
        self.version = l[2][len(self.__proto)+1:]
        parse_message(self, f)

    def __str__(self):
        return '%s %s %s/%s\r\n' % (self.method, self.uri, self.__proto,
                                    self.version) + Message.__str__(self)

class Response(Message):
    """Hypertext Transfer Protocol Response."""
    __hdr_defaults__ = {
        'version':'1.0',
        'status':'200',
        'reason':'OK'
        }
    __proto = 'HTTP'

    def unpack(self, buf):
        f = cStringIO.StringIO(buf)
        line = f.readline()
        l = line.strip().split(None, 2)
        if len(l) < 3 or not l[0].startswith(self.__proto) or not l[1].isdigit():
            raise dpkt.UnpackError('invalid response: %r' % line)
        self.version = l[0][len(self.__proto)+1:]
        self.status = l[1]
        self.reason = l[2]
        parse_message(self, f)

    def __str__(self):
        return '%s/%s %s %s\r\n' % (self.__proto, self.version, self.status,
                                    self.reason) + Message.__str__(self)

if __name__ == '__main__':
    import unittest

    class HTTPTest(unittest.TestCase):
        def test_parse_request(self):
            s = """POST /main/redirect/ab/1,295,,00.html HTTP/1.0\r\nReferer: http://www.email.com/login/snap/login.jhtml\r\nConnection: Keep-Alive\r\nUser-Agent: Mozilla/4.75 [en] (X11; U; OpenBSD 2.8 i386; Nav)\r\nHost: ltd.snap.com\r\nAccept: image/gif, image/x-xbitmap, image/jpeg, image/pjpeg, image/png, */*\r\nAccept-Encoding: gzip\r\nAccept-Language: en\r\nAccept-Charset: iso-8859-1,*,utf-8\r\nContent-type: application/x-www-form-urlencoded\r\nContent-length: 61\r\n\r\nsn=em&mn=dtest4&pw=this+is+atest&fr=true&login=Sign+in&od=www"""
            r = Request(s)
            assert r.method == 'POST'
            assert r.uri == '/main/redirect/ab/1,295,,00.html'
            assert r.body == 'sn=em&mn=dtest4&pw=this+is+atest&fr=true&login=Sign+in&od=www'
            assert r.headers['content-type'] == 'application/x-www-form-urlencoded'
            try:
                r = Request(s[:60])
                assert 'invalid headers parsed!'
            except dpkt.UnpackError:
                pass

        def test_format_request(self):
            r = Request()
            assert str(r) == 'GET / HTTP/1.0\r\n\r\n'
            r.method = 'POST'
            r.uri = '/foo/bar/baz.html'
            r.headers['content-type'] = 'text/plain'
            r.headers['content-length'] = '5'
            r.body = 'hello'
            assert str(r) == 'POST /foo/bar/baz.html HTTP/1.0\r\ncontent-length: 5\r\ncontent-type: text/plain\r\n\r\nhello'
            r = Request(str(r))
            assert str(r) == 'POST /foo/bar/baz.html HTTP/1.0\r\ncontent-length: 5\r\ncontent-type: text/plain\r\n\r\nhello'

        def test_chunked_response(self):
            s = """HTTP/1.1 200 OK\r\nCache-control: no-cache\r\nPragma: no-cache\r\nContent-Type: text/javascript; charset=utf-8\r\nContent-Encoding: gzip\r\nTransfer-Encoding: chunked\r\nSet-Cookie: S=gmail=agg:gmail_yj=v2s:gmproxy=JkU; Domain=.google.com; Path=/\r\nServer: GFE/1.3\r\nDate: Mon, 12 Dec 2005 22:33:23 GMT\r\n\r\na\r\n\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x00\r\n152\r\nm\x91MO\xc4 \x10\x86\xef\xfe\n\x82\xc9\x9eXJK\xe9\xb6\xee\xc1\xe8\x1e6\x9e4\xf1\xe0a5\x86R\xda\x12Yh\x80\xba\xfa\xef\x85\xee\x1a/\xf21\x99\x0c\xef0<\xc3\x81\xa0\xc3\x01\xe6\x10\xc1<\xa7eYT5\xa1\xa4\xac\xe1\xdb\x15:\xa4\x9d\x0c\xfa5K\x00\xf6.\xaa\xeb\x86\xd5y\xcdHY\x954\x8e\xbc*h\x8c\x8e!L7Y\xe6\'\xeb\x82WZ\xcf>8\x1ed\x87\x851X\xd8c\xe6\xbc\x17Z\x89\x8f\xac \x84e\xde\n!]\x96\x17i\xb5\x02{{\xc2z0\x1e\x0f#7\x9cw3v\x992\x9d\xfc\xc2c8\xea[/EP\xd6\xbc\xce\x84\xd0\xce\xab\xf7`\'\x1f\xacS\xd2\xc7\xd2\xfb\x94\x02N\xdc\x04\x0f\xee\xba\x19X\x03TtW\xd7\xb4\xd9\x92\n\xbcX\xa7;\xb0\x9b\'\x10$?F\xfd\xf3CzPt\x8aU\xef\xb8\xc8\x8b-\x18\xed\xec<\xe0\x83\x85\x08!\xf8"[\xb0\xd3j\x82h\x93\xb8\xcf\xd8\x9b\xba\xda\xd0\x92\x14\xa4a\rc\reM\xfd\x87=X;h\xd9j;\xe0db\x17\xc2\x02\xbd\xb0F\xc2in#\xfb:\xb6\xc4x\x15\xd6\x9f\x8a\xaf\xcf)\x0b^\xbc\xe7i\x11\x80\x8b\x00D\x01\xd8/\x82x\xf6\xd8\xf7J(\xae/\x11p\x1f+\xc4p\t:\xfe\xfd\xdf\xa3Y\xfa\xae4\x7f\x00\xc5\xa5\x95\xa1\xe2\x01\x00\x00\r\n0\r\n\r\n"""
            r = Response(s)
            assert r.version == '1.1'
            assert r.status == '200'
            assert r.reason == 'OK'

        def test_multicookie_response(self):
            s = """HTTP/1.x 200 OK\r\nSet-Cookie: first_cookie=cookie1; path=/; domain=.example.com\r\nSet-Cookie: second_cookie=cookie2; path=/; domain=.example.com\r\nContent-Length: 0\r\n\r\n"""
            r = Response(s)
            assert type(r.headers['set-cookie']) is list
            assert len(r.headers['set-cookie']) == 2

    unittest.main()

########NEW FILE########
__FILENAME__ = har
'''
functions and classes for generating HAR data from parsed http data
'''

import http
import json


# json_repr for HTTP header dicts
def header_json_repr(d):
    return [
        {
            'name': k,
            'value': v
        } for k, v in sorted(d.iteritems())
    ]


def query_json_repr(d):
    # d = {string: [string]}
    # we need to print all values of the list
    output = []
    for k, l in sorted(d.iteritems()):
        for v in l:
            output.append({
                'name': k,
                'value': v
            })
    return output


# add json_repr methods to http classes
def HTTPRequestJsonRepr(self):
    '''
    self = http.Request
    '''
    return {
        'method': self.msg.method,
        'url': self.url,
        'httpVersion': 'HTTP/' + self.msg.version,
        'cookies': [],
        'queryString': query_json_repr(self.query),
        'headersSize': -1,
        'headers': header_json_repr(self.msg.headers),
        'bodySize': len(self.msg.body),
    }
http.Request.json_repr = HTTPRequestJsonRepr


def HTTPResponseJsonRepr(self):
    content = {
        'size': self.body_length,
        'mimeType': self.mimeType
    }
    if self.compression_amount is not None:
        content['compression'] = self.compression_amount
    if self.text:
        if self.encoding:
            content['text'] = self.text
            content['encoding'] = self.encoding
        else:
            content['text'] = self.text.encode('utf8')  # must transcode to utf-8
    return {
        'status': int(self.msg.status),
        'statusText': self.msg.reason,
        'httpVersion': 'HTTP/' + self.msg.version,
        'cookies': [],
        'headersSize': -1,
        'bodySize': self.raw_body_length,
        'redirectURL': self.msg.headers['location'] if 'location' in self.msg.headers else '',
        'headers': header_json_repr(self.msg.headers),
        'content': content,
    }
http.Response.json_repr = HTTPResponseJsonRepr


# custom json encoder
class JsonReprEncoder(json.JSONEncoder):
    '''
    Custom Json Encoder that attempts to call json_repr on every object it
    encounters.
    '''

    def default(self, obj):
        if hasattr(obj, 'json_repr'):
            return obj.json_repr()
        return json.JSONEncoder.default(self, obj) # should call super instead?

########NEW FILE########
__FILENAME__ = common
class Error(Exception):
    '''
    Raised when HTTP cannot be parsed from the given data.
    '''
    pass


class DecodingError(Error):
    '''
    Raised when encoded HTTP data cannot be decompressed/decoded/whatever.
    '''
    pass

########NEW FILE########
__FILENAME__ = flow
import logging
import dpkt

import common as http
from request import Request
from response import Response
from .. import settings


class Flow(object):
    '''
    Parses a TCPFlow into HTTP request/response pairs. Or not, depending
    on the integrity of the flow. After __init__, self.pairs contains a
    list of MessagePair's. Requests are paired up with the first response
    that occured after them which has not already been paired with a
    previous request. Responses that don't match up with a request are
    ignored. Requests with no response are paired with None.

    Members:
    pairs = [MessagePair], where either request or response might be None
    '''

    def __init__(self, tcpflow):
        '''
        tcpflow = tcp.Flow
        '''
        # try parsing it with forward as request dir
        success, requests, responses = parse_streams(tcpflow.fwd, tcpflow.rev)
        if not success:
            success, requests, responses = parse_streams(tcpflow.rev, tcpflow.fwd)
            if not success:
                # flow is not HTTP
                raise HTTPError('TCP Flow does not contain HTTP')
        # now optionally clear the data on tcpflow
        if settings.drop_bodies:
            tcpflow.fwd.clear_data()
            tcpflow.rev.clear_data()
        # match up requests with nearest response that occured after them
        # first request is the benchmark; responses before that
        # are irrelevant for now
        self.pairs = []
        # determine a list of responses that we can match up with requests,
        # padding the list with None where necessary.
        try:
            # find the first response to a request we know about,
            # that is, the first response after the first request
            first_response_index = find_index(
                lambda response: response.ts_start > requests[0].ts_start,
                responses
            )
        except LookupError:
            # no responses at all
            pairable_responses = [None for i in requests]
        else:
            # these are responses that match up with our requests
            pairable_responses = responses[first_response_index:]
            # if there are more requests than responses...
            if len(requests) > len(pairable_responses):
                # pad responses with None
                pairable_responses.extend(
                    [None for i in range(len(requests) - len(pairable_responses))]
                )
        # if there are more responses, we would just ignore them anyway,
        # which zip does for us
        # create MessagePair's
        connected = False  # if conn. timing has been added to a request yet
        for req, resp in zip(requests, pairable_responses):
            if not req:
                logging.warning('Request is missing.')
                continue
            if not connected and tcpflow.handshake:
                req.ts_connect = tcpflow.handshake[0].ts
                connected = True
            else:
                req.ts_connect = req.ts_start
            self.pairs.append(MessagePair(req, resp))


class MessagePair(object):
    '''
    An HTTP Request/Response pair/transaction/whatever. Loosely corresponds to
    a HAR entry.
    '''

    def __init__(self, request, response):
        self.request = request
        self.response = response


def gather_messages(MessageClass, tcpdir):
    '''
    Attempts to construct a series of MessageClass objects from the data. The
    basic idea comes from pyper's function, HTTPFlow.analyze.gather_messages.
    Args:
    * MessageClass = class, Request or Response
    * tcpdir = TCPDirection, from which will be extracted the data
    Returns:
    [MessageClass]

    If the first message fails to construct, the flow is considered to be
    invalid. After that, all messages are stored and returned. The end of the
    data is an invalid message. This is designed to handle partially valid HTTP
    flows semi-gracefully: if the flow is bad, the application probably bailed
    on it after that anyway.
    '''
    messages = [] # [MessageClass]
    pointer = 0 # starting index of data that MessageClass should look at
    # while there's data left
    while pointer < len(tcpdir.data):
        #curr_data = tcpdir.data[pointer:pointer+200]  # debug var
        try:
            msg = MessageClass(tcpdir, pointer)
        except dpkt.Error as error:  # if the message failed
            if pointer == 0:  # if this is the first message
                raise http.Error('Invalid http')
            else:  # we're done parsing messages
                logging.warning('We got a dpkt.Error %s, but we are done.' % error)
                break  # out of the loop
        except:
            raise
        # ok, all good
        messages.append(msg)
        pointer += msg.data_consumed
    return messages


def parse_streams(request_stream, response_stream):
    '''
    attempts to construct http.Request/Response's from the corresponding
    passed streams. Failure may either mean that the streams are malformed or
    they are simply switched
    Args:
    request_stream, response_stream = TCPDirection
    Returns:
    True or False, whether parsing succeeded
    request list or None
    response list or None
    '''
    try:
        requests = gather_messages(Request, request_stream)
        responses = gather_messages(Response, response_stream)
    except dpkt.UnpackError as e:
        print 'failed to parse http: ', e
        return False, None, None
    else:
        return True, requests, responses


def find_index(f, seq):
    '''
    returns the index of the first item in seq for which predicate f returns
    True. If no matching item is found, LookupError is raised.
    '''
    for i, item in enumerate(seq):
        if f(item):
            return i
    raise LookupError('no item was found in the sequence that matched the predicate')

########NEW FILE########
__FILENAME__ = message
import logging

class Message(object):
    '''
    Contains a dpkt.http.Request/Response, as well as other data required to
    build a HAR, including (mostly) start and end time.

    * msg: underlying dpkt class
    * data_consumed: how many bytes of input were consumed
    * seq_start: first sequence number of the Message's data in the tcpdir
    * seq_end: first sequence number past Message's data (slice-style indices)
    * ts_start: when Message started arriving (dpkt timestamp)
    * ts_end: when Message had fully arrived (dpkt timestamp)
    * raw_body: body before compression is taken into account
    * tcpdir: The tcp.Direction corresponding to the HTTP message
    '''

    def __init__(self, tcpdir, pointer, msgclass):
        '''
        Args:
        tcpdir = tcp.Direction
        pointer = position within tcpdir.data to start parsing from. byte index
        msgclass = dpkt.http.Request/Response
        '''
        self.tcpdir = tcpdir
        # attempt to parse as http. let exception fall out to caller
        self.msg = msgclass(tcpdir.data[pointer:])
        self.data_consumed = (len(tcpdir.data) - pointer) - len(self.msg.data)
        # save memory by deleting data attribute; it's useless
        self.msg.data = None
        # calculate sequence numbers of data
        self.seq_start = tcpdir.byte_to_seq(pointer)
        self.seq_end = tcpdir.byte_to_seq(pointer + self.data_consumed) # past-the-end
        # calculate arrival_times
        self.ts_start = tcpdir.seq_final_arrival(self.seq_start)
        self.ts_end = tcpdir.seq_final_arrival(self.seq_end - 1)
        if self.ts_start is None or self.ts_end is None:
            logging.warn('Got an HTTP message with unknown start or end time.')
        # get raw body
        self.raw_body = self.msg.body
        self.__pointer = pointer
        # Access self.__raw_msg via raw_msg @property, which will set it if None
        self.__raw_msg = None

    @property
    def raw_msg(self):
        '''
        Returns the message (including header) as a byte string.
        '''
        if not self.__raw_msg:
          self.__raw_msg = self.tcpdir.data[
              self.__pointer:(self.__pointer+self.data_consumed)]
        return self.__raw_msg

########NEW FILE########
__FILENAME__ = request
import urlparse

# dpkt.http is buggy, so we use our modified replacement
from .. import dpkt_http_replacement as dpkt_http
import message as http


class Request(http.Message):
    '''
    HTTP request. Parses higher-level info out of dpkt.http.Request
    Members:
    * query: Query string name-value pairs. {string: [string]}
    * host: hostname of server.
    * fullurl: Full URL, with all components.
    * url: Full URL, but without fragments. (that's what HAR wants)
    '''

    def __init__(self, tcpdir, pointer):
        http.Message.__init__(self, tcpdir, pointer, dpkt_http.Request)
        # get query string. its the URL after the first '?'
        uri = urlparse.urlparse(self.msg.uri)
        self.host = self.msg.headers['host'] if 'host' in self.msg.headers else ''
        fullurl = urlparse.ParseResult('http', self.host, uri.path, uri.params, uri.query, uri.fragment)
        self.fullurl = fullurl.geturl()
        self.url, frag = urlparse.urldefrag(self.fullurl)
        self.query = urlparse.parse_qs(uri.query, keep_blank_values=True)

########NEW FILE########
__FILENAME__ = response
import gzip
import zlib
import cStringIO
from base64 import encodestring as b64encode
import logging

from .. import dpkt_http_replacement as dpkt_http
from ..mediatype import MediaType
from .. import settings

import common as http
import message

# try to import UnicodeDammit from BeautifulSoup,
# starting with system and defaulting to included version
# otherwise, set the name to None
try:
    try:
        from BeautifulSoup import UnicodeDammit
    except ImportError:
        from ..BeautifulSoup import UnicodeDammit
except ImportError:
    UnicodeDammit = None
    log.warning('Can\'t find BeautifulSoup, unicode is more likely to be '
                'misinterpreted')

class Response(message.Message):
    '''
    HTTP response.
    Members:
    * mediaType: mediatype.MediaType, constructed from content-type
    * mimeType: string mime type of returned data
    * body: http decoded body data, otherwise unmodified
    * text: body text, unicoded if possible, otherwise base64 encoded
    * encoding: 'base64' if self.text is base64 encoded binary data, else None
    * compression: string, compression type
    * original_encoding: string, original text encoding/charset/whatever
    * body_length: int, length of body, uncompressed if possible/applicable
    * compression_amount: int or None, difference between lengths of
      uncompressed data and raw data. None if no compression or we're not sure
    '''

    def __init__(self, tcpdir, pointer):
        message.Message.__init__(self, tcpdir, pointer, dpkt_http.Response)
        # get mime type
        if 'content-type' in self.msg.headers:
            self.mediaType = MediaType(self.msg.headers['content-type'])
        else:
            self.mediaType = MediaType('application/x-unknown-content-type')
        self.mimeType = self.mediaType.mimeType()
        # first guess at body size. handle_compression might
        # modify it, but this has to be before clear_body
        self.body_length = len(self.msg.body)
        self.compression_amount = None
        self.text = None
        # handle body stuff
        if settings.drop_bodies:
            self.clear_body()
        else:
            # uncompress body if necessary
            self.handle_compression()
            # try to get out unicode
            self.handle_text()

    def clear_body(self):
        '''
        Clear response body to save memory

        http.Flow has to do most of the work (after any other responses are
        parsed), here we just want to get rid of any references.
        '''
        self.body = self.raw_body = None
        self.msg.body = None

    def handle_compression(self):
        '''
        Sets self.body to the http decoded response data. Sets compression to
        the name of the compresson type.
        '''
        # if content-encoding is found
        if 'content-encoding' in self.msg.headers:
            encoding = self.msg.headers['content-encoding'].lower()
            self.compression = encoding
            # handle gzip
            if encoding == 'gzip' or encoding == 'x-gzip':
                try:
                    gzipfile = gzip.GzipFile(
                        fileobj = cStringIO.StringIO(self.raw_body)
                    )
                    self.body = gzipfile.read()
                except zlib.error:
                    raise http.DecodingError('zlib failed to gunzip HTTP data')
                except:
                    # who knows what else it might raise
                    raise http.DecodingError(
                        'failed to gunzip HTTP data, don\'t know why')
            # handle deflate
            elif encoding == 'deflate':
                try:
                    # NOTE: wbits = -15 is a undocumented feature in python (it's
                    # documented in zlib) that gets rid of the header so we can
                    # do raw deflate. See: http://bugs.python.org/issue5784
                    self.body = zlib.decompress(self.raw_body, -15)
                except zlib.error:
                    raise http.DecodingError(
                        'zlib failed to undeflate HTTP data')
            elif encoding == 'compress' or encoding == 'x-compress':
                # apparently nobody uses this, so basically just ignore it
                self.body = self.raw_body
            elif encoding == 'identity':
                # no compression
                self.body = self.raw_body
            elif 'sdch' in encoding:
                # ignore sdch, a Google proposed modification to HTTP/1.1
                # not in RFC 2616.
                self.body = self.raw_body
            else:
                # I'm pretty sure the above are the only allowed encoding types
                # see RFC 2616 sec 3.5 (http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.5)
                raise http.DecodingError('unknown content-encoding token: ' + encoding)
        else:
            # no compression
            self.compression = 'identity'
            self.body = self.raw_body
        self.body_length = len(self.body)
        # comp_amount is 0 when no compression, which may or may not be to spec
        self.compression_amount = self.body_length - len(self.raw_body)

    def handle_text(self):
        '''
        Takes care of converting body text to unicode, if its text at all.
        Sets self.original_encoding to original char encoding, and converts body
        to unicode if possible. Must come after handle_compression, and after
        self.mediaType is valid.
        '''
        self.encoding = None
        # if the body is text
        if (self.mediaType and
            (self.mediaType.type == 'text' or
                (self.mediaType.type == 'application' and
                 'xml' in self.mediaType.subtype))):
            # if there was a charset parameter in HTTP header, store it
            if 'charset' in self.mediaType.params:
                override_encodings = [self.mediaType.params['charset']]
            else:
                override_encodings = []
            # if there even is data (otherwise,
            # dammit.originalEncoding might be None)
            if self.body != '':
                if UnicodeDammit:
                    # honestly, I don't mind not abiding by RFC 2023.
                    # UnicodeDammit just does what makes sense, and if the
                    # content is remotely standards-compliant, it will do the
                    # right thing.
                    dammit = UnicodeDammit(self.body, override_encodings)
                    # if unicode was found
                    if dammit.unicode:
                        self.text = dammit.unicode
                        self.originalEncoding = dammit.originalEncoding
                    else:
                        # unicode could not be decoded, at all
                        # HAR can't write data, but body might still
                        # be useful as-is
                        pass
                else:
                    # try the stupid version, just guess content-type or utf-8
                    u = None
                    # try our list of encodings + utf8 with strict errors
                    for e in override_encodings + ['utf8', 'iso-8859-1']:
                        try:
                            u = self.body.decode(e, 'strict')
                            self.originalEncoding = e
                            break  # if ^^ didn't throw, we're done
                        except UnicodeError:
                            pass
                    # if none of those worked, try utf8
                    # with 'replace' error mode
                    if not u:
                        # unicode has failed
                        u = self.body.decode('utf8', 'replace')
                        self.originalEncoding = None  # ???
                    self.text = u or None
        else:
            # body is not text
            # base64 encode it and set self.encoding
            # TODO: check with list that this is right
            self.text = b64encode(self.body)
            self.encoding = 'base64'

    @property
    def raw_body_length(self):
        if self.compression_amount is None:
            return self.body_length
        return self.body_length - self.compression_amount

########NEW FILE########
__FILENAME__ = httpsession
'''
Objects for parsing a list of HTTPFlows into data suitable for writing to a
HAR file.
'''

from datetime import datetime
import dpkt
import logging

from pcaputil import ms_from_dpkt_time, ms_from_dpkt_time_diff
from pagetracker import PageTracker
import http
import settings


class Entry(object):
    '''
    represents an HTTP request/response in a form suitable for writing to a HAR
    file.
    Members:
    * request = http.Request
    * response = http.Response
    * page_ref = string
    * startedDateTime = python datetime
    * total_time = from sending of request to end of response, milliseconds
    * time_blocked
    * time_dnsing
    * time_connecting
    * time_sending
    * time_waiting
    * time_receiving
    '''

    def __init__(self, request, response):
        self.request = request
        self.response = response
        self.pageref = None
        self.ts_start = ms_from_dpkt_time(request.ts_connect)
        if request.ts_connect is None:
            self.startedDateTime = None
        else:
            self.startedDateTime = datetime.utcfromtimestamp(request.ts_connect)
        # calculate other timings
        self.time_blocked = -1
        self.time_dnsing = -1
        self.time_connecting = (
            ms_from_dpkt_time_diff(request.ts_start, request.ts_connect))
        self.time_sending = (
            ms_from_dpkt_time_diff(request.ts_end, request.ts_start))
        if response is not None:
            self.time_waiting = (
                ms_from_dpkt_time_diff(response.ts_start, request.ts_end))
            self.time_receiving = (
                ms_from_dpkt_time_diff(response.ts_end, response.ts_start))
            endedDateTime = datetime.utcfromtimestamp(response.ts_end)
            self.total_time = ms_from_dpkt_time_diff(response.ts_end, request.ts_connect)
        else:
            # this can happen if the request never gets a response
            self.time_waiting = -1
            self.time_receiving = -1
            self.total_time = -1

    def json_repr(self):
        '''
        return a JSON serializable python object representation of self.
        '''
        d = {
            'time': self.total_time,
            'request': self.request,
            'response': self.response,
            'timings': {
                'blocked': self.time_blocked,
                'dns': self.time_dnsing,
                'connect': self.time_connecting,
                'send': self.time_sending,
                'wait': self.time_waiting,
                'receive': self.time_receiving
            },
            'cache': {},
        }
        if self.startedDateTime:
            # Z means time is in UTC
            d['startedDateTime'] = self.startedDateTime.isoformat() + 'Z'
        if self.pageref:
            d['pageref'] = self.pageref
        return d

    def add_dns(self, dns_query):
        '''
        Adds the info from the dns.Query to this entry

        Assumes that the dns.Query represents the DNS query required to make
        the request. Or something like that.
        '''
        self.time_dnsing = ms_from_dpkt_time(dns_query.duration())


class UserAgentTracker(object):
    '''
    Keeps track of how many uses each user-agent header receives, and provides
    a function for finding the most-used one.
    '''

    def __init__(self):
        self.data = {}  # {user-agent string: number of uses}

    def add(self, ua_string):
        '''
        Either increments the use-count for the user-agent string, or creates a
        new entry. Call this for each user-agent header encountered.
        '''
        if ua_string in self.data:
            self.data[ua_string] += 1
        else:
            self.data[ua_string] = 1

    def dominant_user_agent(self):
        '''
        Returns the agent string with the most uses.
        '''
        if not len(self.data):
            return None
        elif len(self.data) == 1:
            return self.data.keys()[0]
        else:
            # return the string from the key-value pair with the biggest value
            return max(self.data.iteritems(), key=lambda v: v[1])[0]


class HttpSession(object):
    '''
    Represents all http traffic from within a pcap.

    Members:
    * user_agents = UserAgentTracker
    * user_agent = most-used user-agent in the flow
    * flows = [http.Flow]
    * entries = [Entry], all http request/response pairs
    '''

    def __init__(self, packetdispatcher):
        '''
        parses http.flows from packetdispatcher, and parses those for HAR info
        '''
        # parse http flows
        self.flows = []
        for flow in packetdispatcher.tcp.flows():
            try:
                self.flows.append(http.Flow(flow))
            except http.Error as error:
                logging.warning(error)
            except dpkt.dpkt.Error as error:
                logging.warning(error)
        # combine the messages into a list
        pairs = reduce(lambda p, f: p+f.pairs, self.flows, [])
        # set-up
        self.user_agents = UserAgentTracker()
        if settings.process_pages:
            self.page_tracker = PageTracker()
        else:
            self.page_tracker = None
        self.entries = []
        # sort pairs on request.ts_connect
        pairs.sort(
            key=lambda pair: pair.request.ts_connect
        )
        # iter through messages and do important stuff
        for msg in pairs:
            entry = Entry(msg.request, msg.response)
            # if msg.request has a user-agent, add it to our list
            if 'user-agent' in msg.request.msg.headers:
                self.user_agents.add(msg.request.msg.headers['user-agent'])
            # if msg.request has a referer, keep track of that, too
            if self.page_tracker:
                entry.pageref = self.page_tracker.getref(entry)
            # add it to the list, if we're supposed to keep it.
            if entry.response or settings.keep_unfulfilled_requests:
                self.entries.append(entry)
        self.user_agent = self.user_agents.dominant_user_agent()
        # handle DNS AFTER sorting
        # this algo depends on first appearance of a name
        # being the actual first mention
        names_mentioned = set()
        dns = packetdispatcher.udp.dns
        for entry in self.entries:
            name = entry.request.host
            # if this is the first time seeing the name
            if name not in names_mentioned:
                if name in dns.by_hostname:
                    # TODO: handle multiple DNS queries for now just use last one
                    entry.add_dns(dns.by_hostname[name][-1])
                names_mentioned.add(name)

    def json_repr(self):
        '''
        return a JSON serializable python object representation of self.
        '''
        d = {
            'log': {
                'version': '1.1',
                'creator': {
                    'name': 'pcap2har',
                    'version': '0.1'
                },
                'browser': {
                    'name': self.user_agent,
                    'version': 'mumble'
                },
                'entries': sorted(self.entries, key=lambda x: x.ts_start)
            }
        }
        if self.page_tracker:
            d['log']['pages'] = self.page_tracker
        return d

########NEW FILE########
__FILENAME__ = mediatype
import re
import logging


class MediaType(object):
    '''
    This class parses a media-type string as is found in HTTP headers (possibly
    with params), and exposes the important information in an intuitive interface

    Members:
    * type: string, the main mime type
    * subtype: string, the mime subtype
    * params: {string: string}. Maybe should be {string: [string]}?
    '''

    # RE for parsing media types. type and subtype are alpha-numeric strings
    # possibly with '-'s. Then the optional parameter list: names are same type
    # of string as the types above, values are pretty much anything but another
    # semicolon
    mediatype_re = re.compile(
        r'^([\w\-+.]+)/([\w\-+.]+)((?:\s*;\s*[\w\-]+=[^;]+)*);?\s*$'
    )

    # RE for parsing name-value pairs
    nvpair_re = re.compile(r'^\s*([\w\-]+)=([^;\s]+)\s*$')

    def __init__(self, data):
        '''
        Args:
        data = string, the media type string
        '''
        if not data:
            logging.warning(
                'Setting empty media type to x-unknown-content-type')
            self.set_unknown()
            return
        match = self.mediatype_re.match(data)
        if match:
            # get type/subtype
            self.type = match.group(1).lower()
            self.subtype = match.group(2).lower()
            # params
            self.params = {}
            param_str = match.group(3) # we know this is well-formed, except for extra whitespace
            for pair in param_str.split(';'):
                pair = pair.strip()
                if pair:
                    pairmatch = self.nvpair_re.match(pair)
                    if not pairmatch: raise Exception('MediaType.__init__: invalid pair: "' + pair + '"')
                    self.params[pairmatch.group(1)] = pairmatch.group(2)
            pass
        else:
            logging.warning('Invalid media type string: "%s"' % data)
            self.set_unknown()

    def set_unknown(self):
        self.type = 'application'
        self.subtype = 'x-unknown-content-type'
        self.params = {}

    def mimeType(self):
        return '%s/%s' % (self.type, self.subtype)

    def __str__(self):
        result = self.mimeType()
        for n, v in self.params.iteritems():
            result += '; %s=%s' % (n, v)
        return result

    def __repr__(self):
        return 'MediaType(%s)' % self.__str__()


# test mimetype parsing
if __name__ == '__main__':
    m = MediaType('application/rdf+xml ;charset=ISO-5591-1   ;foo=bar ')
    print m.mimeType()
    print m.params['charset']
    print m.params['foo']
    m = MediaType('image/vnd.microsoft.icon')
    print m.mimeType()

########NEW FILE########
__FILENAME__ = packetdispatcher
import dpkt
import tcp
import udp


class PacketDispatcher:
    '''
    takes a series of dpkt.Packet's and calls callbacks based on their type

    For each packet added, picks it apart into its transport-layer packet type
    and adds it to an appropriate handler object. Automatically creates handler
    objects for now.

    Members:
    * flowbuilder = tcp.FlowBuilder
    * udp = udp.Processor
    '''

    def __init__(self):
        self.tcp = tcp.FlowBuilder()
        self.udp = udp.Processor()

    def add(self, ts, buf, eth):
        '''
        ts = dpkt timestamp
        buf = original packet data
        eth = dpkt.ethernet.Ethernet, whether its real Ethernet or from SLL
        '''
        #decide based on pkt.data
        # if it's IP...
        if (isinstance(eth.data, dpkt.ip.IP) or
            isinstance(eth.data, dpkt.ip6.IP6)):
            ip = eth.data
            # if it's TCP
            if isinstance(ip.data, dpkt.tcp.TCP):
                tcppkt = tcp.Packet(ts, buf, eth, ip, ip.data)
                self.tcp.add(tcppkt)
            # if it's UDP...
            elif isinstance(ip.data, dpkt.udp.UDP):
                self.udp.add(ts, ip.data)

    def finish(self):
        #This is a hack, until tcp.Flow no longer has to be `finish()`ed
        self.tcp.finish()

########NEW FILE########
__FILENAME__ = pagetracker
class Page(object):
    '''
    Members:
    * pageref
    * url = string or None
    * root_document = entry or None
    * startedDateTime
    * user_agent = string, UA of program requesting page
    * title = url
    * referrers = set([string]), urls that have referred to this page, directly
      or indirectly. If anything refers to them, they also belong on this page
    * last_entry = entry, the last entry to be added
    '''

    def __init__(self, pageref, entry, is_root_doc=True):
        '''
        Creates new page with passed ref and data from entry
        '''
        # basics
        self.pageref = pageref
        self.referrers = set()
        self.startedDateTime = entry.startedDateTime
        self.last_entry = entry
        self.user_agent = entry.request.msg.headers.get('user-agent')
        # url, title, etc.
        if is_root_doc:
            self.root_document = entry
            self.url = entry.request.url
            self.title = self.url
        else:
            # if this is a hanging referrer
            if 'referer' in entry.request.msg.headers:
                # save it so other entries w/ the same referrer will come here
                self.referrers.add(entry.request.msg.headers['referer'])
            self.url = None # can't guarantee it's the referrer
            self.title = 'unknown title'

    def has_referrer(self, ref):
        '''
        Returns whether the passed ref might be referring to an url in this page
        '''
        return ref == self.url or ref in self.referrers

    def add(self, entry):
        '''
        Adds the entry to the page's data, whether it likes it or not
        '''
        self.last_entry = entry
        self.referrers.add(entry.request.url)

    def json_repr(self):
        d = {
            'id': self.pageref,
            'title': self.title,
            'pageTimings': default_page_timings
        }
        if self.startedDateTime:
            d['startedDateTime'] = self.startedDateTime.isoformat() + 'Z'
        return d


default_page_timings = {
    'onContentLoad': -1,
    'onLoad': -1
}


def is_root_document(entry):
    '''
    guesses whether the entry is from the root document of a web page
    '''
    # guess based on media type
    if entry.response:  # might be None
        mt = entry.response.mediaType
        if mt.type == 'text':
            if mt.subtype in ['html', 'xhtml', 'xml']:
                # probably...
                return True
    # else, guess by request url?
    return False


class PageTracker(object):
    '''
    Groups http entries into pages.

    Takes a series of http entries and returns string pagerefs. Divides them
    into pages based on http referer headers (and maybe someday by temporal
    locality). Basically all it has to do is sort entries into buckets by any
    means available.
    '''

    def __init__(self):
        self.page_number = 0  # used for generating pageids
        self.pages = []  # [Page]

    def getref(self, entry):
        '''
        takes an Entry and returns a pageref.

        Entries must be passed in by order of arrival
        '''
        # extract interesting information all at once
        req = entry.request  # all the interesting stuff is in the request
        referrer = req.msg.headers.get('referer')
        user_agent = req.msg.headers.get('user-agent')
        matched_page = None  # page we added the request to
        # look through pages for matches
        for page in self.pages:
            # check user agent
            if page.user_agent and user_agent:
                if page.user_agent != user_agent:
                    continue
            # check referrers
            if referrer and page.has_referrer(referrer):
                matched_page = page
                break
        # if we found a page, return it
        if matched_page:
            matched_page.add(entry)
            return matched_page.pageref
        else:
            # make a new page
            return self.new_ref(entry)

    def new_ref(self, entry):
        '''
        Internal. Wraps creating a new pages entry. Returns the new ref
        '''
        new_page = Page(
            self.new_id(),
            entry,
            is_root_document(entry))
        self.pages.append(new_page)
        return new_page.pageref

    def new_id(self):
        result = 'page_%d' % self.page_number
        self.page_number += 1
        return result

    def json_repr(self):
        return sorted(self.pages)

########NEW FILE########
__FILENAME__ = pcap
import logging

import dpkt

from pcaputil import *
import tcp
from packetdispatcher import PacketDispatcher


def ParsePcap(dispatcher, filename=None, reader=None):
    '''
    Parses the passed pcap file or pcap reader.

    Adds the packets to the PacketDispatcher. Keeps a list

    Args:
    dispatcher = PacketDispatcher
    reader = pcaputil.ModifiedReader or None
    filename = filename of pcap file or None

    check for filename first; if there is one, load the reader from that. if
    not, look for reader.
    '''
    if filename:
        f = open(filename, 'rb')
        try:
            pcap = ModifiedReader(f)
        except dpkt.dpkt.Error as e:
            logging.warning('failed to parse pcap file %s' % filename)
            return
    elif reader:
        pcap = reader
    else:
        raise 'function ParsePcap needs either a filename or pcap reader'
    # now we have the reader; read from it
    packet_count = 1  # start from 1 like Wireshark
    errors = [] # store errors for later inspection
    try:
        for packet in pcap:
            ts = packet[0]   # timestamp
            buf = packet[1]  # frame data
            hdr = packet[2]  # libpcap header
            # discard incomplete packets
            if hdr.caplen != hdr.len:
                # log packet number so user can diagnose issue in wireshark
                logging.warning(
                    'ParsePcap: discarding incomplete packet, #%d' %
                    packet_count)
                continue
            # parse packet
            try:
                # handle SLL packets, thanks Libo
                dltoff = dpkt.pcap.dltoff
                if pcap.dloff == dltoff[dpkt.pcap.DLT_LINUX_SLL]:
                    eth = dpkt.sll.SLL(buf)
                # otherwise, for now, assume Ethernet
                else:
                    eth = dpkt.ethernet.Ethernet(buf)
                dispatcher.add(ts, buf, eth)
            # catch errors from this packet
            except dpkt.Error as e:
                errors.append((packet, e, packet_count))
                logging.warning(
                    'Error parsing packet: %s. On packet #%d' %
                    (e, packet_count))
            packet_count += 1
    except dpkt.dpkt.NeedData as error:
        logging.warning(error)
        logging.warning(
            'A packet in the pcap file was too short, packet_count=%d' %
            packet_count)
        errors.append((None, error))


def EasyParsePcap(filename=None, reader=None):
    '''
    Like ParsePcap, but makes and returns a PacketDispatcher for you.
    '''
    dispatcher = PacketDispatcher()
    ParsePcap(dispatcher, filename=filename, reader=reader)
    dispatcher.finish()
    return dispatcher

########NEW FILE########
__FILENAME__ = pcaputil
'''
Various small, useful functions which have no other home.
'''

import dpkt
import resource
import sys

# Re-implemented here only because it's missing on AppEngine.
def inet_ntoa(packed):
    '''Custom implementation of inet_ntoa'''
    if not isinstance(packed, str) or len(packed) != 4:
        raise ValueError('Argument to inet_ntoa must a string of length 4')
    return '.'.join(str(ord(c)) for c in packed)


def friendly_tcp_flags(flags):
    '''
    returns a string containing a user-friendly representation of the tcp flags
    '''
    # create mapping of flags to string repr's
    d = {
        dpkt.tcp.TH_FIN: 'FIN',
        dpkt.tcp.TH_SYN: 'SYN',
        dpkt.tcp.TH_RST: 'RST',
        dpkt.tcp.TH_PUSH: 'PUSH',
        dpkt.tcp.TH_ACK: 'ACK',
        dpkt.tcp.TH_URG: 'URG',
        dpkt.tcp.TH_ECE: 'ECE',
        dpkt.tcp.TH_CWR: 'CWR'
    }
    #make a list of the flags that are activated
    active_flags = filter(lambda t: t[0] & flags, d.iteritems())
    #join all their string representations with '|'
    return '|'.join(t[1] for t in active_flags)


def friendly_socket(sock):
    '''
    returns a socket where the addresses are converted by inet_ntoa into
    human-friendly strings. sock is in tuple format, like
    ((sip, sport),(dip, sport))
    '''
    return '((%s, %d), (%s, %d))' % (
        inet_ntoa(sock[0][0]),
        sock[0][1],
        inet_ntoa(sock[1][0]),
        sock[1][1]
    )


def friendly_data(data):
    '''
    convert (possibly binary) data into a form readable by people on terminals
    '''
    return `data`


def ms_from_timedelta(td):
    '''
    gets the number of ms in td, which is datetime.timedelta.
    Modified from here:
    http://docs.python.org/library/datetime.html#datetime.timedelta, near the
    end of the section.
    '''
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**3


def ms_from_dpkt_time(td):
    '''
    Get milliseconds from a dpkt timestamp. This should probably only really be
    done on a number gotten from subtracting two dpkt timestamps. td could be
    None if the packet if the packet the timestamp should have been gotten
    from was missing, in which case -1 is returned.
    '''
    if td is None:
        return -1
    return int(td * 1000)


def ms_from_dpkt_time_diff(td1, td2):
    '''
    Get milliseconds from the difference of two dpkt timestamps.  Either
    timestamp could be None if packets are missing, in which case -1 is
    returned.
    '''
    if td1 is None or td2 is None:
        return -1
    return ms_from_dpkt_time(td1 - td2)


class ModifiedReader(object):
    '''
    A copy of the dpkt pcap Reader. The only change is that the iterator
    yields the pcap packet header as well, so it's possible to check the true
    frame length, among other things.

    stolen from pyper.
    '''

    def __init__(self, fileobj):
        if hasattr(fileobj, 'name'):
          self.name = fileobj.name
        else:
          self.name = '<unknown>'

        if hasattr(fileobj, 'fileno'):
          self.fd = fileobj.fileno()
        else:
          self.fd = None

        self.__f = fileobj
        buf = self.__f.read(dpkt.pcap.FileHdr.__hdr_len__)
        self.__fh = dpkt.pcap.FileHdr(buf)
        self.__ph = dpkt.pcap.PktHdr
        if self.__fh.magic == dpkt.pcap.PMUDPCT_MAGIC:
            self.__fh = dpkt.pcap.LEFileHdr(buf)
            self.__ph = dpkt.pcap.LEPktHdr
        elif self.__fh.magic != dpkt.pcap.TCPDUMP_MAGIC:
            raise ValueError, 'invalid tcpdump header'
        self.snaplen = self.__fh.snaplen
        self.dloff = dpkt.pcap.dltoff[self.__fh.linktype]
        self.filter = ''

    def fileno(self):
        return self.fd

    def datalink(self):
        return self.__fh.linktype

    def setfilter(self, value, optimize=1):
        return NotImplementedError

    def readpkts(self):
        return list(self)

    def dispatch(self, cnt, callback, *args):
        if cnt > 0:
            for i in range(cnt):
                ts, pkt = self.next()
                callback(ts, pkt, *args)
        else:
            for ts, pkt in self:
                callback(ts, pkt, *args)

    def loop(self, callback, *args):
        self.dispatch(0, callback, *args)

    def __iter__(self):
        self.__f.seek(dpkt.pcap.FileHdr.__hdr_len__)
        while 1:
            buf = self.__f.read(dpkt.pcap.PktHdr.__hdr_len__)
            if not buf: break
            hdr = self.__ph(buf)
            buf = self.__f.read(hdr.caplen)
            yield (hdr.tv_sec + (hdr.tv_usec / 1000000.0), buf, hdr)


class FakeStream(object):
    '''
    Emulates a tcp.Direction with a predetermined data stream.

    Useful for debugging http message classes.
    '''
    def __init__(self, data):
        self.data = data
    def byte_to_seq(self, n):
        return n
    def seq_final_arrival(self, n):
        return None


class FakeFlow(object):
    '''
    Emulates a tcp.Flow, with two FakeStream's.
    '''
    def __init__(self, fwd, rev):
        self.fwd = fwd
        self.rev = rev

def print_rusage():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == 'darwin':
        rss /= 1024  # Mac OSX returns rss in bytes, not KiB
    print 'max_rss:', rss, 'KiB'

########NEW FILE########
__FILENAME__ = settings
process_pages = True
drop_bodies = False  # bodies of http responses, that is

# Whether HTTP parsing should case whether the content length matches the
# content-length header.
strict_http_parse_body = False

# Whether to pad missing data in TCP flows with 0 bytes
pad_missing_tcp_data = False

# Whether to keep requests with missing responses. Could break consumers
# that assume every request has a response.
keep_unfulfilled_requests = False

########NEW FILE########
__FILENAME__ = sortedcollection
'''
This class originates from http://code.activestate.com/recipes/577197-sortedcollection/

It is distributed under the MIT license. Copyright Raymond Hettinger 16 April 2010

Modified by Andrew Fleenor 18 Feb 2011
'''


from bisect import bisect_left, bisect_right

class SortedCollection(object):
    '''Encapsulates a sequence sorted by a given key function.

    SortedCollection() is much easier to work with than using bisect() directly.

    The key function is automatically applied to each search.  The results
    are cached so that the key function is called exactly once for each item.

    Instead of returning a difficult to interpret insertion-point, the three
    find-methods return a specific item in the sequence. They can scan for exact
    matches, the largest item less-than-or-equal to a key, or the smallest item
    greater-than-or-equal to a key.

    Once found, an item's ordinal position can be found with the index() method.

    New items can be added with the insert() and insert_right() methods.

    The usual sequence methods are provided to support indexing, slicing, length
    lookup, clearing, forward and reverse iteration, contains checking, and a
    nice repr.

    Finding and indexing are all O(log n) operations while iteration and
    insertion are O(n).  The initial sort is O(n log n).

    The key function is stored in the 'key' attibute for easy introspection or
    so that you can assign a new key function (triggering an automatic re-sort).

    In short, the class was designed to handle all of the common use cases for
    bisect, but with a simpler API and with automatic support for key functions.

    >>> from pprint import pprint
    >>> from operator import itemgetter

    >>> s = SortedCollection(key=itemgetter(2))
    >>> for record in [
    ...         ('roger', 'young', 30),
    ...         ('bill', 'smith', 22),
    ...         ('angela', 'jones', 28),
    ...         ('david', 'thomas', 32)]:
    ...     s.insert(record)

    >>> pprint(list(s))         # show records sorted by age
    [('bill', 'smith', 22),
     ('angela', 'jones', 28),
     ('roger', 'young', 30),
     ('david', 'thomas', 32)]

    >>> s.find_le(29)           # find oldest person aged 29 or younger
    ('angela', 'jones', 28)

    >>> r = s.find_ge(31)       # find first person aged 31 or older
    >>> s.index(r)              # get the index of their record
    3
    >>> s[3]                    # fetch the record at that index
    ('david', 'thomas', 32)

    >>> s.key = itemgetter(0)   # now sort by first name
    >>> pprint(list(s))
    [('angela', 'jones', 28),
     ('bill', 'smith', 22),
     ('david', 'thomas', 32),
     ('roger', 'young', 30)]

    '''

    def __init__(self, iterable=(), key=None):
        self._key = (lambda x: x) if key is None else key
        self._items = sorted(iterable, key=self._key)
        self._keys = list(map(self._key, self._items))

    def _getkey(self):
        return self._key

    def _setkey(self, key):
        if key is not self._key:
            self.__init__(self._items, key=key)

    def _delkey(self):
        self._setkey(None)

    key = property(_getkey, _setkey, _delkey, 'key function')

    def clear(self):
        self.__init__([], self._key)

    def __len__(self):
        return len(self._items)

    def __getitem__(self, i):
        return self._items[i]

    def __contains__(self, key):
        return key in self._items
        i = bisect_left(self._keys, key)
        return self._keys[i] == key

    def __iter__(self):
        return iter(self._items)

    def __reversed__(self):
        return reversed(self._items)

    def __repr__(self):
        return '%s(%r, key=%s)' % (
            self.__class__.__name__,
            self._items,
            getattr(self._key, '__name__', repr(self._key))
        )

    def index(self, item):
        '''Find the position of an item.  Raise a ValueError if not found'''
        key = self._key(item)
        i = bisect_left(self._keys, key)
        n = len(self)
        while i < n and self._keys[i] == key:
            if self._items[i] == item:
                return i
            i += 1
        raise ValueError('No item found with key equal to: %r' % (key,))

    def insert(self, item):
        'Insert a new item.  If equal keys are found, add to the left'
        key = self._key(item)
        i = bisect_left(self._keys, key)
        self._keys.insert(i, key)
        self._items.insert(i, item)

    def remove(self, index):
        'Remove the item at the passed index'
        # lets IndexError fall out if indices are invalid
        del self._items[index]
        del self._keys[index]

    def insert_right(self, item):
        'Insert a new item.  If equal keys are found, add to the right'
        key = self._key(item)
        i = bisect_right(self._keys, key)
        self._keys.insert(i, key)
        self._items.insert(i, item)

    def find(self, key):
        '''Find item with a key-value equal to key.
        Raise ValueError if no such item exists.

        '''
        i = bisect_left(self._keys, key)
        if self._keys[i] == key:
            return self._items[i]
        raise ValueError('No item found with key equal to: %r' % (key,))

    def find_le(self, key):
        '''Find item with a key-value less-than or equal to key.
        Raise ValueError if no such item exists.
        If multiple key-values are equal, return the leftmost.

        '''
        if not self._items:
            raise ValueError('find_le: No items found')
        i = bisect_left(self._keys, key)
        if i == len(self._keys):
            return self._items[-1]
        if self._keys[i] == key:
            return self._items[i]
        if i == 0:
            raise ValueError('No item found with key at or below: %r' % (key,))
        return self._items[i-1]

    def find_ge(self, key):
        '''Find item with a key-value greater-than or equal to key.
        Raise ValueError if no such item exists.
        If multiple key-values are equal, return the rightmost.

        '''
        i = bisect_right(self._keys, key)
        if i == 0:
            raise ValueError('No item found with key at or above: %r' % (key,))
        if self._keys[i-1] == key:
            return self._items[i-1]
        try:
            return self._items[i]
        except IndexError:
            raise ValueError('No item found with key at or above: %r' % (key,))


if __name__ == '__main__':
    sd = SortedCollection('The quick Brown Fox jumped'.split(), key=str.lower)
    print(sd._keys)
    print(sd._items)
    print(sd._key)
    print(repr(sd))
    print(sd.key)
    sd.key = str.upper
    print(sd.key)
    print(len(sd))
    print(list(sd))
    print(list(reversed(sd)))
    for item in sd:
        assert item in sd
    for i, item in enumerate(sd):
        assert item == sd[i]
    sd.insert('jUmPeD')
    sd.insert_right('QuIcK')
    print(sd._keys)
    print(sd._items)
    print(sd.find_le('JUMPED'), 'jUmPeD')
    print(sd.find_ge('JUMPED'), 'jumped')
    print(sd.find_le('GOAT'), 'Fox')
    print(sd.find_ge('GOAT'), 'jUmPeD')
    print(sd.find('FOX'))
    print(sd[3])
    print(sd[3:5])
    print(sd[-2])
    print(sd[-4:-2])
    for i, item in enumerate(sd):
        print(sd.index(item), i)
    try:
        sd.index('xyzpdq')
    except ValueError:
        pass
    else:
        print('Oops, failed to notify of missing value')


    import doctest
    print(doctest.testmod())

########NEW FILE########
__FILENAME__ = chunk
import seq


class Chunk(object):
    '''
    A chunk of data from a TCP stream in the process of being merged. Takes the
    place of the data tuples, ((begin, end), data, logger) in the old algorithm.
    Adds member functions that encapsulate the main merging logic.
    '''

    def __init__(self):
        '''
        Basic initialization on the chunk.
        '''
        self.data = ''
        self.seq_start = None
        self.seq_end = None

    def merge(self, new, new_seq_callback=None):
        '''
        Attempts to merge the packet or chunk with the existing data. Returns
        details of the operation's success or failure.

        Args:
        new = TCPPacket or TCPChunk
        new_seq_callback = callable(int) or None

        new_seq_callback is a function that will be called with sequence numbers
        of the start of data that has arrived for the first time.

        Returns:
        (overlapped, (added_front_data, added_back_data)): (bool, (bool, bool))

        Overlapped indicates whether the packet/chunk overlapped with the
        existing data. If so, you can stop trying to merge with other packets/
        chunks. The bools in the other tuple indicate whether data was added to
        the front or back of the existing data.

        Note that (True, (False, False)) is a valid value, which indicates that
        the new data was completely inside the existing data
        '''
        # if we have actual data yet (maybe false if there was no init packet)
        if new.data:
            # assume self.seq_* are also valid
            if self.data:
                return self.inner_merge((new.seq_start, new.seq_end),
                                        new.data, new_seq_callback)
            else:
                # if they have data and we don't, just steal theirs
                self.data = new.data
                self.seq_start = new.seq_start
                self.seq_end = new.seq_end
                if new_seq_callback:
                    new_seq_callback(new.seq_start)
                return (True, (True, True))
        # else, there is no data anywhere
        return (False, (False, False))

    def inner_merge(self, newseq, newdata, callback):
        '''
        Internal implementation function for merging, very similar in interface
        to merge_pkt, but concentrates on the nitty-gritty logic of merging, as
        opposed to the high-level logic of merge().

        Args:
        newseq = (seq_begin, seq_end)
        newdata = string, new data
        callback = see new_seq_callback in merge_pkt

        Returns:
        see merge_pkt
        '''
        # setup
        overlapped = False
        added_front_data = False
        added_back_data = False
        # front data?
        if (seq.lt(newseq[0], self.seq_start) and
            seq.lte(self.seq_start, newseq[1])):
            new_data_length = seq.subtract(self.seq_start, newseq[0])
            # slice out new data, stick it on the front
            self.data = newdata[:new_data_length] + self.data
            self.seq_start = newseq[0]
            # notifications
            overlapped = True
            added_front_data = True
            if callback:
                callback(newseq[0])
        # back data?
        if seq.lte(newseq[0], self.seq_end) and seq.lt(self.seq_end, newseq[1]):
            new_data_length = seq.subtract(newseq[1], self.seq_end)
            self.data += newdata[-new_data_length:]
            self.seq_end += new_data_length
            # notifications
            overlapped = True
            added_back_data = True
            if callback:
                # the first seq number of new data in the back
                back_seq_start = newseq[1] - new_data_length
                callback(back_seq_start)
        # completely inside?
        if (seq.lte(self.seq_start, newseq[0]) and
            seq.lte(newseq[1], self.seq_end)):
            overlapped = True
        # done
        return (overlapped, (added_front_data, added_back_data))

########NEW FILE########
__FILENAME__ = common
import dpkt


def detect_handshake(packets):
    '''
    Checks whether the passed list of tcp.Packet's represents a valid TCP
    handshake. Returns True or False.
    '''
    #from dpkt.tcp import * # get TH_* constants
    if len(packets) < 3:
        return False
    if len(packets) > 3:
        log.error('too many packets for detect_handshake')
        return False
    syn, synack, ack = packets
    fwd_seq = None
    rev_seq = None
    if syn.tcp.flags & dpkt.tcp.TH_SYN and not syn.tcp.flags & dpkt.tcp.TH_ACK:
        # have syn
        fwd_seq = syn.seq  # start_seq is the seq field of the segment
        if (synack.flags & dpkt.tcp.TH_SYN and
            synack.flags & dpkt.tcp.TH_ACK and
            synack.ack == fwd_seq + 1):
            # have synack
            rev_seq = synack.seq
            if (ack.flags & dpkt.tcp.TH_ACK and
                ack.ack == rev_seq + 1 and
                ack.seq == fwd_seq + 1):
                # have ack
                return True
    return False

########NEW FILE########
__FILENAME__ = direction
from operator import itemgetter, attrgetter
import logging

from ..sortedcollection import SortedCollection

import packet
import chunk as tcp
from .. import settings


class Direction(object):
    '''
    Represents data moving in one direction in a TCP flow.

    Members:
    * finished = bool. Indicates whether more packets should be expected.
    * chunks = [tcp.Chunk] or None, sorted by seq_start. None iff data
      has been cleared.
    * flow = tcp.Flow, the flow to which the direction belongs
    * arrival_data = SortedCollection([(seq_num, pkt)])
    * final_arrival_data = SortedCollection([(seq_num, ts)])
    * final_data_chunk = Chunk or None, the chunk that contains the final data,
      only after seq_start is valid and before clear_data
    * final_arrival_pointer = the end sequence number of data that has
      completely arrived
    '''

    def __init__(self, flow):
        '''
        Sets things up for adding packets.

        Args:
        flow = tcp.Flow
        '''
        self.finished = False
        self.flow = flow
        self.arrival_data = SortedCollection(key=itemgetter(0))
        self.final_arrival_data = SortedCollection(key=itemgetter(0))
        self.final_arrival_pointer = None
        self.chunks = SortedCollection(key=attrgetter('seq_start'))
        self.final_data_chunk = None

    def add(self, pkt):
        '''
        Merge the packet into the first chunk it overlaps with. If data was
        added to the end of a chunk, attempts to merge the next chunk (if there
        is one). This way, it is ensured that everything is as fully merged as
        it can be with the current data.

        Args:
        pkt = tcp.Packet
        '''
        if self.finished:
            raise RuntimeError('tried to add packets to a finished tcp.Direction')
        if self.chunks is None:
            raise RuntimeError('Tried to add packet to a tcp.Direction'
                               'that has been cleared')
        # discard packets with no payload. we don't care about them here
        if pkt.data == '':
            return
        # attempt to merge packet with existing chunks
        merged = False
        for i, chunk in enumerate(self.chunks):
            overlapped, (front, back) = chunk.merge(
                pkt, self.create_merge_callback(pkt))
            if overlapped:
                # check if this packet bridged the gap between two chunks
                if back and i < (len(self.chunks)-1):
                    overlapped2, result2 = chunk.merge(self.chunks[i+1])
                    # if the gap was bridged, the later chunk is obsolete
                    # so get rid of it.
                    if overlapped2:
                        self.chunks.remove(i+1)
                # if this is the main data chunk, calc final arrival
                if self.seq_start and chunk.seq_start == self.seq_start:
                    if front:
                        # packet was first in stream but is just now arriving
                        self.final_arrival_data.insert((self.seq_start, pkt.ts))
                    if back:  # usual case
                        self.final_arrival_data.insert(
                            (self.final_arrival_pointer, pkt.ts))
                    if not self.final_data_chunk:
                        self.final_data_chunk = chunk
                    self.final_arrival_pointer = self.final_data_chunk.seq_end
                merged = True
                break  # skip further chunks
        if not merged:
            # nothing overlapped with the packet
            # we need a new chunk
            self.new_chunk(pkt)

    @property
    def data(self):
        '''
        returns the TCP data, as far as it has been determined.
        '''
        if self.chunks is None:
            return None
        if self.final_data_chunk:
            return self.final_data_chunk.data
        else:
            if self.finished:
                return ''  # no data was ever added
            else:
                return None  # just don't know at all

    def clear_data(self):
        '''
        Drop data to save memory
        '''
        # we need to make sure we've grabbed any timing info we can
        if not self.finished:
            logging.warn('tried to clear data on an unfinished tcp.Direction')
        # clear the list, to make sure all chunks are orphaned to make it
        # easier for GC. hopefully.
        self.chunks.clear()
        self.chunks = None
        self.final_data_chunk = None

    @property
    def seq_start(self):
        '''
        starting sequence number, as far as we can tell now.
        '''
        if self.flow.handshake:
            assert(self in (self.flow.fwd, self.flow.rev))
            if self is self.flow.fwd:
                return self.flow.handshake[2].seq
            else:
                return self.flow.handshake[1].seq + 1
        elif self.finished:
            if self.chunks:
                return self.chunks[0].seq_start
            else:
                # this will also occur when a Direction with no handshake
                # has been cleared.
                logging.warning('getting seq_start from finished tcp.Direction '
                            'with no handshake and no data')
                return None
        else:
            return None

    def finish(self):
        '''
        Notifies the direction that there are no more packets coming. This means
        that self.data can be decided upon. Also calculates final_arrival for
        any packets that arrived while seq_start was None
        '''
        if settings.pad_missing_tcp_data:
            self.pad_missing_data()
        self.finished = True
        # calculate final_arrival
        if not self.final_arrival_data:
            peak_time = 0.0
            for vertex in self.arrival_data:
                if vertex[1].ts > peak_time:
                    peak_time = vertex[1].ts
                    self.final_arrival_data.insert((vertex[0], vertex[1].ts))

        if self.chunks and not self.final_data_chunk:
            self.final_data_chunk = self.chunks[0]

    def new_chunk(self, pkt):
        '''
        creates a new tcp.Chunk for the pkt to live in. Only called if an
        attempt has been made to merge the packet with all existing chunks.
        '''
        chunk = tcp.Chunk()
        chunk.merge(pkt, self.create_merge_callback(pkt))
        if self.seq_start and chunk.seq_start == self.seq_start:
            self.final_data_chunk = chunk
            self.final_arrival_pointer = chunk.seq_end
            self.final_arrival_data.insert((pkt.seq, pkt.ts))
        self.chunks.insert(chunk)

    def create_merge_callback(self, pkt):
        '''
        Returns a function that will serve as a callback for Chunk. It will
        add the passed sequence number and the packet to self.arrival_data.
        '''
        def callback(seq_num):
            self.arrival_data.insert((seq_num, pkt))
        return callback

    def byte_to_seq(self, byte):
        '''
        Converts the passed byte index to a sequence number in the stream. byte
        is assumed to be zero-based. Returns None if seq_start is None
        '''
        # TODO better handle case where seq_start is None
        seq_start = self.seq_start
        if seq_start is not None:
            return byte + seq_start
        else:
            return None

    def seq_arrival(self, seq_num):
        '''
        returns the packet in which the specified sequence number first arrived.
        '''
        try:
            return self.arrival_data.find_le(seq_num)[1]
        except ValueError:
            return None

    def seq_final_arrival(self, seq_num):
        '''
        Returns the time at which the seq number had fully arrived, that is,
        when all the data before it had also arrived.
        '''
        try:
            return self.final_arrival_data.find_le(seq_num)[1]
        except:
            return None

    def pad_missing_data(self):
        '''Pad missing data in the flow with zero bytes.'''
        if not self.chunks:
            return
        prev_chunk = self.chunks[0]
        for chunk in self.chunks[1:]:
            gap = chunk.seq_start - prev_chunk.seq_end
            if gap > 0:
                logging.info('Padding %d missing bytes at %d',
                             gap, prev_chunk.seq_end)
                first_chunk_pkt = self.seq_arrival(chunk.seq_start)
                chunk_ts = first_chunk_pkt.ts
                pad_pkt = packet.PadPacket(prev_chunk.seq_end, gap, chunk_ts)
                self.add(pad_pkt)
            prev_chunk = chunk

########NEW FILE########
__FILENAME__ = flow
import logging
import common as tcp

from dpkt.tcp import TH_SYN

from ..sortedcollection import SortedCollection
import seq # hopefully no name collisions
from direction import Direction


class NewFlowError(Exception):
    '''
    Used to signal that a new flow should be started.
    '''
    pass


class Flow(object):
    '''
    Represents TCP traffic across a given socket, ideally between a TCP
    handshake and clean connection termination.

    Members:
    * fwd, rev = tcp.Direction, both sides of the communication stream
    * socket = ((srcip, sport), (dstip, dport)). Used for checking the direction
    of packets. Taken from SYN or first packet.
    * packets = list of tcp.Packet's, all packets in the flow
    * handshake = None or (syn, synack, ack) or False. None while a handshake is
    still being searched for, False when we've given up on finding it.
    '''

    def __init__(self):
        self.fwd = Direction(self)
        self.rev = Direction(self)
        self.handshake = None
        self.socket = None
        self.packets = []

    def add(self, pkt):
        '''
        called for every packet coming in, instead of iterating through
        a list
        '''
        # maintain an invariant that packets are ordered by ts;
        # perform ordered insertion (as in insertion sort) if they're
        # not in order because sometimes libpcap writes packets out of
        # order.

        # the correct position for pkt is found by looping i from
        # len(self.packets) descending back to 0 (inclusive);
        # normally, this loop will only run for one iteration.
        for i in xrange(len(self.packets), -1, -1):
            # pkt is at the correct position if it is at the
            # beginning, or if it is >= the packet at its previous
            # position.
            if i == 0 or self.packets[i - 1].ts <= pkt.ts: break
        self.packets.insert(i, pkt)

        # look out for handshake
        # add it to the appropriate direction, if we've found or given up on
        # finding handshake
        if self.handshake is not None:
            if pkt.flags == TH_SYN:
                # syn packet now probably means a new flow started on the same
                # socket. Request (demand?) that a new flow be started.
                raise NewFlowError
            self.merge_pkt(pkt)
        else: # if handshake is None, we're still looking for a handshake
            if len(self.packets) > 13: # or something like that
                # give up
                self.handshake = False
                self.socket = self.packets[0].socket
                self.flush_packets() # merge all stored packets
            # check last three packets
            elif tcp.detect_handshake(self.packets[-3:]):
                # function handles packets < 3 case
                self.handshake = tuple(self.packets[-3:])
                self.socket = self.handshake[0].socket
                self.flush_packets()

    def flush_packets(self):
        '''
        Flush packet buffer by merging all packets into either fwd or rev.
        '''
        for p in self.packets:
            self.merge_pkt(p)

    def merge_pkt(self, pkt):
        '''
        Merges the packet into either the forward or reverse stream, depending
        on its direction.
        '''
        if self.samedir(pkt):
            self.fwd.add(pkt)
        else:
            self.rev.add(pkt)

    def finish(self):
        '''
        Notifies the flow that there are no more packets. This finalizes the
        handshake and socket, flushes any built-up packets, and calls finish on
        fwd and rev.
        '''
        # handle the case where no handshake was detected
        if self.handshake is None:
            self.handshake = False
            self.socket = self.packets[0].socket
            self.flush_packets()
        self.fwd.finish()
        self.rev.finish()

    def samedir(self, pkt):
        '''
        returns whether the passed packet is in the same direction as the
        assumed direction of the flow, which is either that of the SYN or the
        first packet. Raises RuntimeError if self.socket is None
        '''
        if not self.socket:
            raise RuntimeError(
                'called tcp.Flow.samedir before direction is determined')
        src, dst = pkt.socket
        if self.socket == (src, dst):
            return True
        elif self.socket == (dst, src):
            return False
        else:
            raise ValueError(
                'TCPFlow.samedir found a packet from the wrong flow')

    def writeout_data(self, basename):
        '''
        writes out the data in the flows to two files named basename-fwd.dat and
        basename-rev.dat.
        '''
        with open(basename + '-fwd.dat', 'wb') as f:
            f.write(self.fwd.data)
        with open(basename + '-rev.dat', 'wb') as f:
            f.write(self.rev.data)

########NEW FILE########
__FILENAME__ = flowbuilder
import flow as tcp
import logging


class FlowBuilder(object):
    '''
    Builds and stores tcp.Flow's from packets.

    Takes a series of tcp.Packet's and sorts them into the correct tcp.Flow's
    based on their socket. Exposes them in a dictionary keyed by socket. Call
    .add(pkt) for each packet. This will find the right tcp.Flow in the dict and
    call .add() on it. This class should be renamed.

    Members:
    flowdict = {socket: [tcp.Flow]}
    '''

    def __init__(self):
        self.flowdict = {}

    def add(self, pkt):
        '''
        filters out unhandled packets, and sorts the remainder into the correct
        flow
        '''
        #shortcut vars
        src, dst = pkt.socket
        srcip, srcport = src
        dstip, dstport = dst
        # filter out weird packets, LSONG
        if srcport == 5223 or dstport == 5223:
            logging.warning('hpvirtgrp packets are ignored')
            return
        if srcport == 5228 or dstport == 5228:
            logging.warning('hpvroom packets are ignored')
            return
        if srcport == 443 or dstport == 443:
            logging.warning('https packets are ignored')
            return
        # sort the packet into a tcp.Flow in flowdict. If NewFlowError is
        # raised, the existing flow doesn't want any more packets, so we
        # should start a new flow.
        if (src, dst) in self.flowdict:
            try:
                self.flowdict[(src, dst)][-1].add(pkt)
            except tcp.NewFlowError:
                self.new_flow((src, dst), pkt)
        elif (dst, src) in self.flowdict:
            try:
                self.flowdict[(dst, src)][-1].add(pkt)
            except tcp.NewFlowError:
                self.new_flow((dst, src), pkt)
        else:
            self.new_flow((src, dst), pkt)

    def new_flow(self, socket, packet):
        '''
        Adds a new flow to flowdict for socket, and adds the packet.

        Socket must either be present in flowdict or missing entirely, eg., if
        you pass in (src, dst), (dst, src) should not be present.

        Args:
        * socket: ((ip, port), (ip, port))
        * packet: tcp.Packet
        '''
        newflow = tcp.Flow()
        newflow.add(packet)
        if socket in self.flowdict:
            self.flowdict[socket].append(newflow)
        else:
            self.flowdict[socket] = [newflow]

    def flows(self):
        '''
        Generator that iterates over all flows.
        '''
        for flowlist in self.flowdict.itervalues():
            for flow in flowlist:
                yield flow

    def finish(self):
        map(tcp.Flow.finish, self.flows())

########NEW FILE########
__FILENAME__ = packet
import dpkt

from ..pcaputil import *

class Packet(object):
    '''
    Represents a TCP packet. Copied from pyper, with additions. contains
    socket, timestamp, and data

    Members:
    ts = dpkt timestamp
    buf = original data from which eth was constructed
    eth = dpkt.ethernet.Ethernet. Original ethernet frame.
    ip = dpkt.ip.IP. Original IP packet.
    tcp = dpkt.tcp.TCP.
    socket = standard socket tuple: ((srcip, sport), (dstip, dport))
    data = data from TCP segment
    seq, seq_start = sequence number
    seq_end = first sequence number past this packets data (past the end slice
        index style)
    '''

    def __init__(self, ts, buf, eth, ip, tcp):
        '''
        Args:
        ts = timestamp
        buf = original packet data
        eth = dpkt.ethernet.Ethernet that the packet came from
        ip  = dpkt.ip.IP that the packet came from
        tcp = dpkt.tcp.TCP that the packet came from
        '''
        self.ts = ts
        self.buf = buf
        self.eth = eth
        self.ip = ip
        self.tcp = tcp
        self.socket = ((self.ip.src, self.tcp.sport),(self.ip.dst, self.tcp.dport))
        self.data = tcp.data
        self.seq = tcp.seq
        self.ack = tcp.ack
        self.flags = tcp.flags
        self.seq_start = self.tcp.seq
        self.seq_end = self.tcp.seq + len(self.tcp.data) # - 1
        self.rtt = None

    def __cmp__(self, other):
        return cmp(self.ts, other.ts)

    def __eq__(self, other):
        return not self.__ne__(other)

    def __ne__(self, other):
        if isinstance(other, Packet):
            return cmp(self, other) != 0
        else:
            return True

    def __repr__(self):
        return 'Packet(%s, %s, seq=%x , ack=%x, data="%s")' % (
            friendly_socket(self.socket),
            friendly_tcp_flags(self.tcp.flags),
            self.tcp.seq,
            self.tcp.ack,
            friendly_data(self.tcp.data)[:60]
        )


class PadPacket(Packet):
    '''
    Represents a fake TCP packet used for padding missing data.
    '''

    def __init__(self, seq, size, ts):
        self.ts = ts
        self.buf = None
        self.eth = None
        self.ip = None
        self.tcp = None
        self.socket = None
        self.data = '\0' * size
        self.seq = seq
        self.ack = None
        self.flags = None
        self.seq_start = seq
        self.seq_end = self.seq_start + size
        self.rtt = None

    def __repr__(self):
        return 'PadPacket(seq=%d, size=%d)' % (self.seq, len(self.data))

########NEW FILE########
__FILENAME__ = seq
'''
Defines functions for comparing and processing TCP sequence numbers, taking
into account their limited number space.
'''


def twos_comp(x):
    return (~x)+1


numberspace = 2**32 # seq numbers are up to but not including this
halfspace = numberspace / 2


def wrap(x):
    '''
    emulates the cast to int used in the C tcp seq # subtraction algo:
    (int)( (a) - (b) ). Basically, if a number's absolute value is greater
    than half the (unsigned) number space, it needs to be wrapped.
    '''
    # if abs(x) > numberspace / 2, its value must be reduced by numberspace/2,
    # and its sign must be flipped
    if x > halfspace:
        x = 0 - (x - halfspace)
    elif x < -halfspace:
        x = 0 - (x + halfspace)
    # x is now normalized
    return x


def subtract(a, b):
    '''Calculate the difference between a and b, two python longs,
    in a manner suitable for comparing two TCP sequence numbers in a
    wrap-around-sensitive way.'''
    return wrap(a - b)

def lt(a, b):
    return subtract(a, b) < 0

def gt(a, b):
    return subtract(a, b) > 0

def lte(a, b):
    return subtract(a, b) <= 0

def gte(a, b):
    return subtract(a, b) >= 0


import unittest


class TestTcpSeqSubtraction(unittest.TestCase):
    def testNormalSubtraction(self):
        self.assertEqual(subtract(500L, 1L), 499L)
        self.assertEqual(subtract(1L, 1L), 0L)
        self.assertEqual(subtract(0x10000000, 0x20000000), -0x10000000)
        #self.assertEqual(subtract(20L, 0x
    def testWrappedSubtraction(self):
        #self.assertEqual(subtract(0, 0xffffffff), 1)
        # actual: a < b. want: a > b
        self.assertEqual(subtract(0x10000000, 0xd0000000), 0x40000000)
        # actual: a > b. want: a < b
        self.assertEqual(subtract(0xd0000000, 0x10000000), -0x40000000)


class TestLessThan(unittest.TestCase):
    def testLessThan(self):
        self.assertTrue( not lt(100, 10))
        self.assertTrue( lt(0x7fffffff, 0xf0000000))


def runtests():
    suite = unittest.TestSuite()
    suite.addTest(TestTcpSeqSubtraction('testNormalSubtraction'))
    suite.addTest(TestTcpSeqSubtraction('testWrappedSubtraction'))
    suite.addTest(TestLessThan('testLessThan'))
    runner = unittest.TextTestRunner()
    runner.run(suite)

########NEW FILE########
__FILENAME__ = udp
import logging
import dpkt
import dns


class Processor(object):
    '''
    Processes and interprets UDP packets.

    Call its add(pkt) method with each dpkt.udp.UDP packet from the pcap or
    whatever. It will expose information from the packets, at this point mostly
    DNS information. It will automatically create a dns processor and expose it
    as its `dns` member variable.

    This class is basically a nonce, if I may borrow the term, for the sake of
    architectural elegance. But I think it's begging for trouble to combine it
    with DNS handling.
    '''

    def __init__(self):
        self.dns = dns.Processor()

    def add(self, ts, pkt):
        '''
        pkt = dpkt.udp.UDP
        '''
        #check for DNS
        if pkt.sport == 53 or pkt.dport == 53:
            try:
                dnspkt = dpkt.dns.DNS(pkt.data)
                self.dns.add(dns.Packet(ts, dnspkt))
            except dpkt.Error:
                logging.warning('UDP packet on port 53 was not DNS')
        else:
            logging.warning('unkown UDP ports: %d->%d' % (pkt.sport, pkt.dport))

########NEW FILE########
