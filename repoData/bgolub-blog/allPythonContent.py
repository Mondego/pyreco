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
__version__ = "3.0.7a"
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
try:
    set
except NameError:
    from sets import Set as set

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
__FILENAME__ = demjson
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
r""" A JSON data encoder and decoder.

 This Python module implements the JSON (http://json.org/) data
 encoding format; a subset of ECMAScript (aka JavaScript) for encoding
 primitive data types (numbers, strings, booleans, lists, and
 associative arrays) in a language-neutral simple text-based syntax.
 
 It can encode or decode between JSON formatted strings and native
 Python data types.  Normally you would use the encode() and decode()
 functions defined by this module, but if you want more control over
 the processing you can use the JSON class.

 This implementation tries to be as completely cormforming to all
 intricacies of the standards as possible.  It can operate in strict
 mode (which only allows JSON-compliant syntax) or a non-strict mode
 (which allows much more of the whole ECMAScript permitted syntax).
 This includes complete support for Unicode strings (including
 surrogate-pairs for non-BMP characters), and all number formats
 including negative zero and IEEE 754 non-numbers such a NaN or
 Infinity.

 The JSON/ECMAScript to Python type mappings are:
    ---JSON---             ---Python---
    null                   None
    undefined              undefined  (note 1)
    Boolean (true,false)   bool  (True or False)
    Integer                int or long  (note 2)
    Float                  float
    String                 str or unicode  ( "..." or u"..." )
    Array [a, ...]         list  ( [...] )
    Object {a:b, ...}      dict  ( {...} )
    
    -- Note 1. an 'undefined' object is declared in this module which
       represents the native Python value for this type when in
       non-strict mode.

    -- Note 2. some ECMAScript integers may be up-converted to Python
       floats, such as 1e+40.  Also integer -0 is converted to
       float -0, so as to preserve the sign (which ECMAScript requires).

 In addition, when operating in non-strict mode, several IEEE 754
 non-numbers are also handled, and are mapped to specific Python
 objects declared in this module:

     NaN (not a number)     nan    (float('nan'))
     Infinity, +Infinity    inf    (float('inf'))
     -Infinity              neginf (float('-inf'))

 When encoding Python objects into JSON, you may use types other than
 native lists or dictionaries, as long as they support the minimal
 interfaces required of all sequences or mappings.  This means you can
 use generators and iterators, tuples, UserDict subclasses, etc.

 To make it easier to produce JSON encoded representations of user
 defined classes, if the object has a method named json_equivalent(),
 then it will call that method and attempt to encode the object
 returned from it instead.  It will do this recursively as needed and
 before any attempt to encode the object using it's default
 strategies.  Note that any json_equivalent() method should return
 "equivalent" Python objects to be encoded, not an already-encoded
 JSON-formatted string.  There is no such aid provided to decode
 JSON back into user-defined classes as that would dramatically
 complicate the interface.
 
 When decoding strings with this module it may operate in either
 strict or non-strict mode.  The strict mode only allows syntax which
 is conforming to RFC 4627 (JSON), while the non-strict allows much
 more of the permissible ECMAScript syntax.

 The following are permitted when processing in NON-STRICT mode:

    * Unicode format control characters are allowed anywhere in the input.
    * All Unicode line terminator characters are recognized.
    * All Unicode white space characters are recognized.
    * The 'undefined' keyword is recognized.
    * Hexadecimal number literals are recognized (e.g., 0xA6, 0177).
    * String literals may use either single or double quote marks.
    * Strings may contain \x (hexadecimal) escape sequences, as well as the
      \v and \0 escape sequences.
    * Lists may have omitted (elided) elements, e.g., [,,,,,], with
      missing elements interpreted as 'undefined' values.
    * Object properties (dictionary keys) can be of any of the
      types: string literals, numbers, or identifiers (the later of
      which are treated as if they are string literals)---as permitted
      by ECMAScript.  JSON only permits strings literals as keys.

 Concerning non-strict and non-ECMAScript allowances:

    * Octal numbers: If you allow the 'octal_numbers' behavior (which
      is never enabled by default), then you can use octal integers
      and octal character escape sequences (per the ECMAScript
      standard Annex B.1.2).  This behavior is allowed, if enabled,
      because it was valid JavaScript at one time.

    * Multi-line string literals:  Strings which are more than one
      line long (contain embedded raw newline characters) are never
      permitted. This is neither valid JSON nor ECMAScript.  Some other
      JSON implementations may allow this, but this module considers
      that behavior to be a mistake.

 References:
    * JSON (JavaScript Object Notation)
      <http://json.org/>
    * RFC 4627. The application/json Media Type for JavaScript Object Notation (JSON)
      <http://www.ietf.org/rfc/rfc4627.txt>
    * ECMA-262 3rd edition (1999)
      <http://www.ecma-international.org/publications/files/ecma-st/ECMA-262.pdf>
    * IEEE 754-1985: Standard for Binary Floating-Point Arithmetic.
      <http://www.cs.berkeley.edu/~ejr/Projects/ieee754/>
    
"""

__author__ = "Deron Meranda <http://deron.meranda.us/>"
__date__ = "2008-12-17"
__version__ = "1.4"
__credits__ = """Copyright (c) 2006-2008 Deron E. Meranda <http://deron.meranda.us/>
Licensed under GNU LGPL 3.0 (GNU Lesser General Public License) or
later.  See LICENSE.txt included with this software.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>
or <http://www.fsf.org/licensing/>.

"""

# ------------------------------
# useful global constants

content_type = 'application/json'
file_ext = 'json'
hexdigits = '0123456789ABCDEFabcdef'
octaldigits = '01234567'

# ----------------------------------------------------------------------
# Decimal and float types.
#
# If a JSON number can not be stored in a Python float without loosing
# precision and the Python has the decimal type, then we will try to
# use decimal instead of float.  To make this determination we need to
# know the limits of the float type, but Python doesn't have an easy
# way to tell what the largest floating-point number it supports.  So,
# we detemine the precision and scale of the float type by testing it.

try:
    # decimal module was introduced in Python 2.4
    import decimal
except ImportError:
    decimal = None

def determine_float_precision():
    """Returns a tuple (significant_digits, max_exponent) for the float type.
    """
    import math
    # Just count the digits in pi.  The last two decimal digits
    # may only be partial digits, so discount for them.
    whole, frac = repr(math.pi).split('.')
    sigdigits = len(whole) + len(frac) - 2

    # This is a simple binary search.  We find the largest exponent
    # that the float() type can handle without going infinite or
    # raising errors.
    maxexp = None
    minv = 0; maxv = 1000
    while True:
        if minv+1 == maxv:
            maxexp = minv - 1
            break
        elif maxv < minv:
            maxexp = None
            break
        m = (minv + maxv) // 2
        try:
            f = repr(float( '1e+%d' % m ))
        except ValueError:
            f = None
        else:
            if not f or f[0] < '0' or f[0] > '9':
                f = None
        if not f:
            # infinite
            maxv = m
        else:
            minv = m
    return sigdigits, maxexp

float_sigdigits, float_maxexp = determine_float_precision()

# ----------------------------------------------------------------------
# The undefined value.
#
# ECMAScript has an undefined value (similar to yet distinct from null).
# Neither Python or strict JSON have support undefined, but to allow
# JavaScript behavior we must simulate it.

class _undefined_class(object):
    """Represents the ECMAScript 'undefined' value."""
    __slots__ = []
    def __repr__(self):
        return self.__module__ + '.undefined'
    def __str__(self):
        return 'undefined'
    def __nonzero__(self):
        return False
undefined = _undefined_class()
del _undefined_class


# ----------------------------------------------------------------------
# Non-Numbers: NaN, Infinity, -Infinity
#
# ECMAScript has official support for non-number floats, although
# strict JSON does not.  Python doesn't either.  So to support the
# full JavaScript behavior we must try to add them into Python, which
# is unfortunately a bit of black magic.  If our python implementation
# happens to be built on top of IEEE 754 we can probably trick python
# into using real floats.  Otherwise we must simulate it with classes.

def _nonnumber_float_constants():
    """Try to return the Nan, Infinity, and -Infinity float values.
    
    This is unnecessarily complex because there is no standard
    platform- independent way to do this in Python as the language
    (opposed to some implementation of it) doesn't discuss
    non-numbers.  We try various strategies from the best to the
    worst.
    
    If this Python interpreter uses the IEEE 754 floating point
    standard then the returned values will probably be real instances
    of the 'float' type.  Otherwise a custom class object is returned
    which will attempt to simulate the correct behavior as much as
    possible.

    """
    try:
        # First, try (mostly portable) float constructor.  Works under
        # Linux x86 (gcc) and some Unices.
        nan = float('nan')
        inf = float('inf')
        neginf = float('-inf')
    except ValueError:
        try:
            # Try the AIX (PowerPC) float constructors
            nan = float('NaNQ')
            inf = float('INF')
            neginf = float('-INF')
        except ValueError:
            try:
                # Next, try binary unpacking.  Should work under
                # platforms using IEEE 754 floating point.
                import struct, sys
                xnan = '7ff8000000000000'.decode('hex')  # Quiet NaN
                xinf = '7ff0000000000000'.decode('hex')
                xcheck = 'bdc145651592979d'.decode('hex') # -3.14159e-11
                # Could use float.__getformat__, but it is a new python feature,
                # so we use sys.byteorder.
                if sys.byteorder == 'big':
                    nan = struct.unpack('d', xnan)[0]
                    inf = struct.unpack('d', xinf)[0]
                    check = struct.unpack('d', xcheck)[0]
                else:
                    nan = struct.unpack('d', xnan[::-1])[0]
                    inf = struct.unpack('d', xinf[::-1])[0]
                    check = struct.unpack('d', xcheck[::-1])[0]
                neginf = - inf
                if check != -3.14159e-11:
                    raise ValueError('Unpacking raw IEEE 754 floats does not work')
            except (ValueError, TypeError):
                # Punt, make some fake classes to simulate.  These are
                # not perfect though.  For instance nan * 1.0 == nan,
                # as expected, but 1.0 * nan == 0.0, which is wrong.
                class nan(float):
                    """An approximation of the NaN (not a number) floating point number."""
                    def __repr__(self): return 'nan'
                    def __str__(self): return 'nan'
                    def __add__(self,x): return self
                    def __radd__(self,x): return self
                    def __sub__(self,x): return self
                    def __rsub__(self,x): return self
                    def __mul__(self,x): return self
                    def __rmul__(self,x): return self
                    def __div__(self,x): return self
                    def __rdiv__(self,x): return self
                    def __divmod__(self,x): return (self,self)
                    def __rdivmod__(self,x): return (self,self)
                    def __mod__(self,x): return self
                    def __rmod__(self,x): return self
                    def __pow__(self,exp): return self
                    def __rpow__(self,exp): return self
                    def __neg__(self): return self
                    def __pos__(self): return self
                    def __abs__(self): return self
                    def __lt__(self,x): return False
                    def __le__(self,x): return False
                    def __eq__(self,x): return False
                    def __neq__(self,x): return True
                    def __ge__(self,x): return False
                    def __gt__(self,x): return False
                    def __complex__(self,*a): raise NotImplementedError('NaN can not be converted to a complex')
                if decimal:
                    nan = decimal.Decimal('NaN')
                else:
                    nan = nan()
                class inf(float):
                    """An approximation of the +Infinity floating point number."""
                    def __repr__(self): return 'inf'
                    def __str__(self): return 'inf'
                    def __add__(self,x): return self
                    def __radd__(self,x): return self
                    def __sub__(self,x): return self
                    def __rsub__(self,x): return self
                    def __mul__(self,x):
                        if x is neginf or x < 0:
                            return neginf
                        elif x == 0:
                            return nan
                        else:
                            return self
                    def __rmul__(self,x): return self.__mul__(x)
                    def __div__(self,x):
                        if x == 0:
                            raise ZeroDivisionError('float division')
                        elif x < 0:
                            return neginf
                        else:
                            return self
                    def __rdiv__(self,x):
                        if x is inf or x is neginf or x is nan:
                            return nan
                        return 0.0
                    def __divmod__(self,x):
                        if x == 0:
                            raise ZeroDivisionError('float divmod()')
                        elif x < 0:
                            return (nan,nan)
                        else:
                            return (self,self)
                    def __rdivmod__(self,x):
                        if x is inf or x is neginf or x is nan:
                            return (nan, nan)
                        return (0.0, x)
                    def __mod__(self,x):
                        if x == 0:
                            raise ZeroDivisionError('float modulo')
                        else:
                            return nan
                    def __rmod__(self,x):
                        if x is inf or x is neginf or x is nan:
                            return nan
                        return x
                    def __pow__(self, exp):
                        if exp == 0:
                            return 1.0
                        else:
                            return self
                    def __rpow__(self, x):
                        if -1 < x < 1: return 0.0
                        elif x == 1.0: return 1.0
                        elif x is nan or x is neginf or x < 0:
                            return nan
                        else:
                            return self
                    def __neg__(self): return neginf
                    def __pos__(self): return self
                    def __abs__(self): return self
                    def __lt__(self,x): return False
                    def __le__(self,x):
                        if x is self:
                            return True
                        else:
                            return False
                    def __eq__(self,x):
                        if x is self:
                            return True
                        else:
                            return False
                    def __neq__(self,x):
                        if x is self:
                            return False
                        else:
                            return True
                    def __ge__(self,x): return True
                    def __gt__(self,x): return True
                    def __complex__(self,*a): raise NotImplementedError('Infinity can not be converted to a complex')
                if decimal:
                    inf = decimal.Decimal('Infinity')
                else:
                    inf = inf()
                class neginf(float):
                    """An approximation of the -Infinity floating point number."""
                    def __repr__(self): return '-inf'
                    def __str__(self): return '-inf'
                    def __add__(self,x): return self
                    def __radd__(self,x): return self
                    def __sub__(self,x): return self
                    def __rsub__(self,x): return self
                    def __mul__(self,x):
                        if x is self or x < 0:
                            return inf
                        elif x == 0:
                            return nan
                        else:
                            return self
                    def __rmul__(self,x): return self.__mul__(self)
                    def __div__(self,x):
                        if x == 0:
                            raise ZeroDivisionError('float division')
                        elif x < 0:
                            return inf
                        else:
                            return self
                    def __rdiv__(self,x):
                        if x is inf or x is neginf or x is nan:
                            return nan
                        return -0.0
                    def __divmod__(self,x):
                        if x == 0:
                            raise ZeroDivisionError('float divmod()')
                        elif x < 0:
                            return (nan,nan)
                        else:
                            return (self,self)
                    def __rdivmod__(self,x):
                        if x is inf or x is neginf or x is nan:
                            return (nan, nan)
                        return (-0.0, x)
                    def __mod__(self,x):
                        if x == 0:
                            raise ZeroDivisionError('float modulo')
                        else:
                            return nan
                    def __rmod__(self,x):
                        if x is inf or x is neginf or x is nan:
                            return nan
                        return x
                    def __pow__(self,exp):
                        if exp == 0:
                            return 1.0
                        else:
                            return self
                    def __rpow__(self, x):
                        if x is nan or x is inf or x is inf:
                            return nan
                        return 0.0
                    def __neg__(self): return inf
                    def __pos__(self): return self
                    def __abs__(self): return inf
                    def __lt__(self,x): return True
                    def __le__(self,x): return True
                    def __eq__(self,x):
                        if x is self:
                            return True
                        else:
                            return False
                    def __neq__(self,x):
                        if x is self:
                            return False
                        else:
                            return True
                    def __ge__(self,x):
                        if x is self:
                            return True
                        else:
                            return False
                    def __gt__(self,x): return False
                    def __complex__(self,*a): raise NotImplementedError('-Infinity can not be converted to a complex')
                if decimal:
                    neginf = decimal.Decimal('-Infinity')
                else:
                    neginf = neginf(0)
    return nan, inf, neginf

nan, inf, neginf = _nonnumber_float_constants()
del _nonnumber_float_constants


# ----------------------------------------------------------------------
# String processing helpers

unsafe_string_chars = '"\\' + ''.join([chr(i) for i in range(0x20)])
def skipstringsafe( s, start=0, end=None ):
    i = start
    #if end is None:
    #    end = len(s)
    while i < end and s[i] not in unsafe_string_chars:
        #c = s[i]
        #if c in unsafe_string_chars:
        #    break
        i += 1
    return i
def skipstringsafe_slow( s, start=0, end=None ):
    i = start
    if end is None:
        end = len(s)
    while i < end:
        c = s[i]
        if c == '"' or c == '\\' or ord(c) <= 0x1f:
            break
        i += 1
    return i

def extend_list_with_sep( orig_seq, extension_seq, sepchar='' ):
    if not sepchar:
        orig_seq.extend( extension_seq )
    else:
        for i, x in enumerate(extension_seq):
            if i > 0:
                orig_seq.append( sepchar )
            orig_seq.append( x )

def extend_and_flatten_list_with_sep( orig_seq, extension_seq, separator='' ):
    for i, part in enumerate(extension_seq):
        if i > 0 and separator:
            orig_seq.append( separator )
        orig_seq.extend( part )


# ----------------------------------------------------------------------
# Unicode helpers
#
# JSON requires that all JSON implementations must support the UTF-32
# encoding (as well as UTF-8 and UTF-16).  But earlier versions of
# Python did not provide a UTF-32 codec.  So we must implement UTF-32
# ourselves in case we need it.

def utf32le_encode( obj, errors='strict' ):
    """Encodes a Unicode string into a UTF-32LE encoded byte string."""
    import struct
    try:
        import cStringIO as sio
    except ImportError:
        import StringIO as sio
    f = sio.StringIO()
    write = f.write
    pack = struct.pack
    for c in obj:
        n = ord(c)
        if 0xD800 <= n <= 0xDFFF: # surrogate codepoints are prohibited by UTF-32
            if errors == 'ignore':
                continue
            elif errors == 'replace':
                n = ord('?')
            else:
                cname = 'U+%04X'%n
                raise UnicodeError('UTF-32 can not encode surrogate characters',cname)
        write( pack('<L', n) )
    return f.getvalue()


def utf32be_encode( obj, errors='strict' ):
    """Encodes a Unicode string into a UTF-32BE encoded byte string."""
    import struct
    try:
        import cStringIO as sio
    except ImportError:
        import StringIO as sio
    f = sio.StringIO()
    write = f.write
    pack = struct.pack
    for c in obj:
        n = ord(c)
        if 0xD800 <= n <= 0xDFFF: # surrogate codepoints are prohibited by UTF-32
            if errors == 'ignore':
                continue
            elif errors == 'replace':
                n = ord('?')
            else:
                cname = 'U+%04X'%n
                raise UnicodeError('UTF-32 can not encode surrogate characters',cname)
        write( pack('>L', n) )
    return f.getvalue()


def utf32le_decode( obj, errors='strict' ):
    """Decodes a UTF-32LE byte string into a Unicode string."""
    if len(obj) % 4 != 0:
        raise UnicodeError('UTF-32 decode error, data length not a multiple of 4 bytes')
    import struct
    unpack = struct.unpack
    chars = []
    i = 0
    for i in range(0, len(obj), 4):
        seq = obj[i:i+4]
        n = unpack('<L',seq)[0]
        chars.append( unichr(n) )
    return u''.join( chars )


def utf32be_decode( obj, errors='strict' ):
    """Decodes a UTF-32BE byte string into a Unicode string."""
    if len(obj) % 4 != 0:
        raise UnicodeError('UTF-32 decode error, data length not a multiple of 4 bytes')
    import struct
    unpack = struct.unpack
    chars = []
    i = 0
    for i in range(0, len(obj), 4):
        seq = obj[i:i+4]
        n = unpack('>L',seq)[0]
        chars.append( unichr(n) )
    return u''.join( chars )


def auto_unicode_decode( s ):
    """Takes a string and tries to convert it to a Unicode string.

    This will return a Python unicode string type corresponding to the
    input string (either str or unicode).  The character encoding is
    guessed by looking for either a Unicode BOM prefix, or by the
    rules specified by RFC 4627.  When in doubt it is assumed the
    input is encoded in UTF-8 (the default for JSON).

    """
    if isinstance(s, unicode):
        return s
    if len(s) < 4:
        return s.decode('utf8')  # not enough bytes, assume default of utf-8
    # Look for BOM marker
    import codecs
    bom2 = s[:2]
    bom4 = s[:4]
    a, b, c, d = map(ord, s[:4])  # values of first four bytes
    if bom4 == codecs.BOM_UTF32_LE:
        encoding = 'utf-32le'
        s = s[4:]
    elif bom4 == codecs.BOM_UTF32_BE:
        encoding = 'utf-32be'
        s = s[4:]
    elif bom2 == codecs.BOM_UTF16_LE:
        encoding = 'utf-16le'
        s = s[2:]
    elif bom2 == codecs.BOM_UTF16_BE:
        encoding = 'utf-16be'
        s = s[2:]
    # No BOM, so autodetect encoding used by looking at first four bytes
    # according to RFC 4627 section 3.
    elif a==0 and b==0 and c==0 and d!=0: # UTF-32BE
        encoding = 'utf-32be'
    elif a==0 and b!=0 and c==0 and d!=0: # UTF-16BE
        encoding = 'utf-16be'
    elif a!=0 and b==0 and c==0 and d==0: # UTF-32LE
        encoding = 'utf-32le'
    elif a!=0 and b==0 and c!=0 and d==0: # UTF-16LE
        encoding = 'utf-16le'
    else: #if a!=0 and b!=0 and c!=0 and d!=0: # UTF-8
        # JSON spec says default is UTF-8, so always guess it
        # if we can't guess otherwise
        encoding = 'utf8'
    # Make sure the encoding is supported by Python
    try:
        cdk = codecs.lookup(encoding)
    except LookupError:
        if encoding.startswith('utf-32') \
               or encoding.startswith('ucs4') \
               or encoding.startswith('ucs-4'):
            # Python doesn't natively have a UTF-32 codec, but JSON
            # requires that it be supported.  So we must decode these
            # manually.
            if encoding.endswith('le'):
                unis = utf32le_decode(s)
            else:
                unis = utf32be_decode(s)
        else:
            raise JSONDecodeError('this python has no codec for this character encoding',encoding)
    else:
        # Convert to unicode using a standard codec
        unis = s.decode(encoding)
    return unis


def surrogate_pair_as_unicode( c1, c2 ):
    """Takes a pair of unicode surrogates and returns the equivalent unicode character.

    The input pair must be a surrogate pair, with c1 in the range
    U+D800 to U+DBFF and c2 in the range U+DC00 to U+DFFF.

    """
    n1, n2 = ord(c1), ord(c2)
    if n1 < 0xD800 or n1 > 0xDBFF or n2 < 0xDC00 or n2 > 0xDFFF:
        raise JSONDecodeError('illegal Unicode surrogate pair',(c1,c2))
    a = n1 - 0xD800
    b = n2 - 0xDC00
    v = (a << 10) | b
    v += 0x10000
    return unichr(v)


def unicode_as_surrogate_pair( c ):
    """Takes a single unicode character and returns a sequence of surrogate pairs.

    The output of this function is a tuple consisting of one or two unicode
    characters, such that if the input character is outside the BMP range
    then the output is a two-character surrogate pair representing that character.

    If the input character is inside the BMP then the output tuple will have
    just a single character...the same one.

    """
    n = ord(c)
    if n < 0x10000:
        return (unichr(n),)  # in BMP, surrogate pair not required
    v = n - 0x10000
    vh = (v >> 10) & 0x3ff   # highest 10 bits
    vl = v & 0x3ff  # lowest 10 bits
    w1 = 0xD800 | vh
    w2 = 0xDC00 | vl
    return (unichr(w1), unichr(w2))


# ----------------------------------------------------------------------
# Type identification

def isnumbertype( obj ):
    """Is the object of a Python number type (excluding complex)?"""
    return isinstance(obj, (int,long,float)) \
           and not isinstance(obj, bool) \
           or obj is nan or obj is inf or obj is neginf


def isstringtype( obj ):
    """Is the object of a Python string type?"""
    if isinstance(obj, basestring):
        return True
    # Must also check for some other pseudo-string types
    import types, UserString
    return isinstance(obj, types.StringTypes) \
           or isinstance(obj, UserString.UserString) \
           or isinstance(obj, UserString.MutableString)


# ----------------------------------------------------------------------
# Numeric helpers

def decode_hex( hexstring ):
    """Decodes a hexadecimal string into it's integer value."""
    # We don't use the builtin 'hex' codec in python since it can
    # not handle odd numbers of digits, nor raise the same type
    # of exceptions we want to.
    n = 0
    for c in hexstring:
        if '0' <= c <= '9':
            d = ord(c) - ord('0')
        elif 'a' <= c <= 'f':
            d = ord(c) - ord('a') + 10
        elif 'A' <= c <= 'F':
            d = ord(c) - ord('A') + 10
        else:
            raise JSONDecodeError('not a hexadecimal number',hexstring)
        # Could use ((n << 4 ) | d), but python 2.3 issues a FutureWarning.
        n = (n * 16) + d
    return n


def decode_octal( octalstring ):
    """Decodes an octal string into it's integer value."""
    n = 0
    for c in octalstring:
        if '0' <= c <= '7':
            d = ord(c) - ord('0')
        else:
            raise JSONDecodeError('not an octal number',octalstring)
        # Could use ((n << 3 ) | d), but python 2.3 issues a FutureWarning.
        n = (n * 8) + d
    return n


# ----------------------------------------------------------------------
# Exception classes.

class JSONError(ValueError):
    """Our base class for all JSON-related errors.

    """
    def pretty_description(self):
        err = self.args[0]
        if len(self.args) > 1:
            err += ': '
            for anum, a in enumerate(self.args[1:]):
                if anum > 1:
                    err += ', '
                astr = repr(a)
                if len(astr) > 20:
                    astr = astr[:20] + '...'
                err += astr
        return err

class JSONDecodeError(JSONError):
    """An exception class raised when a JSON decoding error (syntax error) occurs."""


class JSONEncodeError(JSONError):
    """An exception class raised when a python object can not be encoded as a JSON string."""


#----------------------------------------------------------------------
# The main JSON encoder/decoder class.

class JSON(object):
    """An encoder/decoder for JSON data streams.

    Usually you will call the encode() or decode() methods.  The other
    methods are for lower-level processing.

    Whether the JSON parser runs in strict mode (which enforces exact
    compliance with the JSON spec) or the more forgiving non-string mode
    can be affected by setting the 'strict' argument in the object's
    initialization; or by assigning True or False to the 'strict'
    property of the object.

    You can also adjust a finer-grained control over strictness by
    allowing or preventing specific behaviors.  You can get a list of
    all the available behaviors by accessing the 'behaviors' property.
    Likewise the allowed_behaviors and prevented_behaviors list which
    behaviors will be allowed and which will not.  Call the allow()
    or prevent() methods to adjust these.
    
    """
    _escapes_json = { # character escapes in JSON
        '"': '"',
        '/': '/',
        '\\': '\\',
        'b': '\b',
        'f': '\f',
        'n': '\n',
        'r': '\r',
        't': '\t',
        }

    _escapes_js = { # character escapes in Javascript
        '"': '"',
        '\'': '\'',
        '\\': '\\',
        'b': '\b',
        'f': '\f',
        'n': '\n',
        'r': '\r',
        't': '\t',
        'v': '\v',
        '0': '\x00'
        }

    # Following is a reverse mapping of escape characters, used when we
    # output JSON.  Only those escapes which are always safe (e.g., in JSON)
    # are here.  It won't hurt if we leave questionable ones out.
    _rev_escapes = {'\n': '\\n',
                    '\t': '\\t',
                    '\b': '\\b',
                    '\r': '\\r',
                    '\f': '\\f',
                    '"': '\\"',
                    '\\': '\\\\'}

    def __init__(self, strict=False, compactly=True, escape_unicode=False):
        """Creates a JSON encoder/decoder object.
        
        If 'strict' is set to True, then only strictly-conforming JSON
        output will be produced.  Note that this means that some types
        of values may not be convertable and will result in a
        JSONEncodeError exception.
        
        If 'compactly' is set to True, then the resulting string will
        have all extraneous white space removed; if False then the
        string will be "pretty printed" with whitespace and indentation
        added to make it more readable.
        
        If 'escape_unicode' is set to True, then all non-ASCII characters
        will be represented as a unicode escape sequence; if False then
        the actual real unicode character will be inserted if possible.

        The 'escape_unicode' can also be a function, which when called
        with a single argument of a unicode character will return True
        if the character should be escaped or False if it should not.
        
        If you wish to extend the encoding to ba able to handle
        additional types, you should subclass this class and override
        the encode_default() method.
        
        """
        import sys
        self._set_strictness(strict)
        self._encode_compactly = compactly
        try:
            # see if we were passed a predicate function
            b = escape_unicode(u'A')
            self._encode_unicode_as_escapes = escape_unicode
        except (ValueError, NameError, TypeError):
            # Just set to True or False.  We could use lambda x:True
            # to make it more consistent (always a function), but it
            # will be too slow, so we'll make explicit tests later.
            self._encode_unicode_as_escapes = bool(escape_unicode)
        self._sort_dictionary_keys = True

        # The following is a boolean map of the first 256 characters
        # which will quickly tell us which of those characters never
        # need to be escaped.

        self._asciiencodable = [32 <= c < 128 and not self._rev_escapes.has_key(chr(c))
                              for c in range(0,255)]

    def _set_strictness(self, strict):
        """Changes the strictness behavior.

        Pass True to be very strict about JSON syntax, or False to be looser.
        """
        self._allow_any_type_at_start = not strict
        self._allow_all_numeric_signs = not strict
        self._allow_comments = not strict
        self._allow_control_char_in_string = not strict
        self._allow_hex_numbers = not strict
        self._allow_initial_decimal_point = not strict
        self._allow_js_string_escapes = not strict
        self._allow_non_numbers = not strict
        self._allow_nonescape_characters = not strict  # "\z" -> "z"
        self._allow_nonstring_keys = not strict
        self._allow_omitted_array_elements = not strict
        self._allow_single_quoted_strings = not strict
        self._allow_trailing_comma_in_literal = not strict
        self._allow_undefined_values = not strict
        self._allow_unicode_format_control_chars = not strict
        self._allow_unicode_whitespace = not strict
        # Always disable this by default
        self._allow_octal_numbers = False

    def allow(self, behavior):
        """Allow the specified behavior (turn off a strictness check).

        The list of all possible behaviors is available in the behaviors property.
        You can see which behaviors are currently allowed by accessing the
        allowed_behaviors property.

        """
        p = '_allow_' + behavior
        if hasattr(self, p):
            setattr(self, p, True)
        else:
            raise AttributeError('Behavior is not known',behavior)

    def prevent(self, behavior):
        """Prevent the specified behavior (turn on a strictness check).

        The list of all possible behaviors is available in the behaviors property.
        You can see which behaviors are currently prevented by accessing the
        prevented_behaviors property.

        """
        p = '_allow_' + behavior
        if hasattr(self, p):
            setattr(self, p, False)
        else:
            raise AttributeError('Behavior is not known',behavior)

    def _get_behaviors(self):
        return sorted([ n[len('_allow_'):] for n in self.__dict__ \
                        if n.startswith('_allow_')])
    behaviors = property(_get_behaviors,
                         doc='List of known behaviors that can be passed to allow() or prevent() methods')

    def _get_allowed_behaviors(self):
        return sorted([ n[len('_allow_'):] for n in self.__dict__ \
                        if n.startswith('_allow_') and getattr(self,n)])
    allowed_behaviors = property(_get_allowed_behaviors,
                                 doc='List of known behaviors that are currently allowed')

    def _get_prevented_behaviors(self):
        return sorted([ n[len('_allow_'):] for n in self.__dict__ \
                        if n.startswith('_allow_') and not getattr(self,n)])
    prevented_behaviors = property(_get_prevented_behaviors,
                                   doc='List of known behaviors that are currently prevented')

    def _is_strict(self):
        return not self.allowed_behaviors
    strict = property(_is_strict, _set_strictness,
                      doc='True if adherence to RFC 4627 syntax is strict, or False is more generous ECMAScript syntax is permitted')


    def isws(self, c):
        """Determines if the given character is considered as white space.
        
        Note that Javscript is much more permissive on what it considers
        to be whitespace than does JSON.
        
        Ref. ECMAScript section 7.2

        """
        if not self._allow_unicode_whitespace:
            return c in ' \t\n\r'
        else:
            if not isinstance(c,unicode):
                c = unicode(c)
            if c in u' \t\n\r\f\v':
                return True
            import unicodedata
            return unicodedata.category(c) == 'Zs'

    def islineterm(self, c):
        """Determines if the given character is considered a line terminator.

        Ref. ECMAScript section 7.3

        """
        if c == '\r' or c == '\n':
            return True
        if c == u'\u2028' or c == u'\u2029': # unicodedata.category(c) in  ['Zl', 'Zp']
            return True
        return False

    def strip_format_control_chars(self, txt):
        """Filters out all Unicode format control characters from the string.

        ECMAScript permits any Unicode "format control characters" to
        appear at any place in the source code.  They are to be
        ignored as if they are not there before any other lexical
        tokenization occurs.  Note that JSON does not allow them.

        Ref. ECMAScript section 7.1.

        """
        import unicodedata
        txt2 = filter( lambda c: unicodedata.category(unicode(c)) != 'Cf',
                       txt )
        return txt2


    def decode_null(self, s, i=0):
        """Intermediate-level decoder for ECMAScript 'null' keyword.

        Takes a string and a starting index, and returns a Python
        None object and the index of the next unparsed character.

        """
        if i < len(s) and s[i:i+4] == 'null':
            return None, i+4
        raise JSONDecodeError('literal is not the JSON "null" keyword', s)

    def encode_undefined(self):
        """Produces the ECMAScript 'undefined' keyword."""
        return 'undefined'

    def encode_null(self):
        """Produces the JSON 'null' keyword."""
        return 'null'

    def decode_boolean(self, s, i=0):
        """Intermediate-level decode for JSON boolean literals.

        Takes a string and a starting index, and returns a Python bool
        (True or False) and the index of the next unparsed character.

        """
        if s[i:i+4] == 'true':
            return True, i+4
        elif s[i:i+5] == 'false':
            return False, i+5
        raise JSONDecodeError('literal value is not a JSON boolean keyword',s)

    def encode_boolean(self, b):
        """Encodes the Python boolean into a JSON Boolean literal."""
        if bool(b):
            return 'true'
        return 'false'

    def decode_number(self, s, i=0, imax=None):
        """Intermediate-level decoder for JSON numeric literals.

        Takes a string and a starting index, and returns a Python
        suitable numeric type and the index of the next unparsed character.

        The returned numeric type can be either of a Python int,
        long, or float.  In addition some special non-numbers may
        also be returned such as nan, inf, and neginf (technically
        which are Python floats, but have no numeric value.)

        Ref. ECMAScript section 8.5.

        """
        if imax is None:
            imax = len(s)
        # Detect initial sign character(s)
        if not self._allow_all_numeric_signs:
            if s[i] == '+' or (s[i] == '-' and i+1 < imax and \
                               s[i+1] in '+-'):
                raise JSONDecodeError('numbers in strict JSON may only have a single "-" as a sign prefix',s[i:])
        sign = +1
        j = i  # j will point after the sign prefix
        while j < imax and s[j] in '+-':
            if s[j] == '-': sign = sign * -1
            j += 1
        # Check for ECMAScript symbolic non-numbers
        if s[j:j+3] == 'NaN':
            if self._allow_non_numbers:
                return nan, j+3
            else:
                raise JSONDecodeError('NaN literals are not allowed in strict JSON')
        elif s[j:j+8] == 'Infinity':
            if self._allow_non_numbers:
                if sign < 0:
                    return neginf, j+8
                else:
                    return inf, j+8
            else:
                raise JSONDecodeError('Infinity literals are not allowed in strict JSON')
        elif s[j:j+2] in ('0x','0X'):
            if self._allow_hex_numbers:
                k = j+2
                while k < imax and s[k] in hexdigits:
                    k += 1
                n = sign * decode_hex( s[j+2:k] )
                return n, k
            else:
                raise JSONDecodeError('hexadecimal literals are not allowed in strict JSON',s[i:])
        else:
            # Decimal (or octal) number, find end of number.
            # General syntax is:  \d+[\.\d+][e[+-]?\d+]
            k = j   # will point to end of digit sequence
            could_be_octal = ( k+1 < imax and s[k] == '0' )  # first digit is 0
            decpt = None  # index into number of the decimal point, if any
            ept = None # index into number of the e|E exponent start, if any
            esign = '+' # sign of exponent
            sigdigits = 0 # number of significant digits (approx, counts end zeros)
            while k < imax and (s[k].isdigit() or s[k] in '.+-eE'):
                c = s[k]
                if c not in octaldigits:
                    could_be_octal = False
                if c == '.':
                    if decpt is not None or ept is not None:
                        break
                    else:
                        decpt = k-j
                elif c in 'eE':
                    if ept is not None:
                        break
                    else:
                        ept = k-j
                elif c in '+-':
                    if not ept:
                        break
                    esign = c
                else: #digit
                    if not ept:
                        sigdigits += 1
                k += 1
            number = s[j:k]  # The entire number as a string
            #print 'NUMBER IS: ', repr(number), ', sign', sign, ', esign', esign, \
            #      ', sigdigits', sigdigits, \
            #      ', decpt', decpt, ', ept', ept

            # Handle octal integers first as an exception.  If octal
            # is not enabled (the ECMAScipt standard) then just do
            # nothing and treat the string as a decimal number.
            if could_be_octal and self._allow_octal_numbers:
                n = sign * decode_octal( number )
                return n, k

            # A decimal number.  Do a quick check on JSON syntax restrictions.
            if number[0] == '.' and not self._allow_initial_decimal_point:
                raise JSONDecodeError('numbers in strict JSON must have at least one digit before the decimal point',s[i:])
            elif number[0] == '0' and \
                     len(number) > 1 and number[1].isdigit():
                if self._allow_octal_numbers:
                    raise JSONDecodeError('initial zero digit is only allowed for octal integers',s[i:])
                else:
                    raise JSONDecodeError('initial zero digit must not be followed by other digits (octal numbers are not permitted)',s[i:])
            # Make sure decimal point is followed by a digit
            if decpt is not None:
                if decpt+1 >= len(number) or not number[decpt+1].isdigit():
                    raise JSONDecodeError('decimal point must be followed by at least one digit',s[i:])
            # Determine the exponential part
            if ept is not None:
                if ept+1 >= len(number):
                    raise JSONDecodeError('exponent in number is truncated',s[i:])
                try:
                    exponent = int(number[ept+1:])
                except ValueError:
                    raise JSONDecodeError('not a valid exponent in number',s[i:])
                ##print 'EXPONENT', exponent
            else:
                exponent = 0
            # Try to make an int/long first.
            if decpt is None and exponent >= 0:
                # An integer
                if ept:
                    n = int(number[:ept])
                else:
                    n = int(number)
                n *= sign
                if exponent:
                    n *= 10**exponent
                if n == 0 and sign < 0:
                    # minus zero, must preserve negative sign so make a float
                    n = -0.0
            else:
                try:
                    if decimal and (abs(exponent) > float_maxexp or sigdigits > float_sigdigits):
                        try:
                            n = decimal.Decimal(number)
                            n = n.normalize()
                        except decimal.Overflow:
                            if sign<0:
                                n = neginf
                            else:
                                n = inf
                        else:
                            n *= sign
                    else:
                        n = float(number) * sign
                except ValueError:
                    raise JSONDecodeError('not a valid JSON numeric literal', s[i:j])
            return n, k

    def encode_number(self, n):
        """Encodes a Python numeric type into a JSON numeric literal.
        
        The special non-numeric values of float('nan'), float('inf')
        and float('-inf') are translated into appropriate JSON
        literals.
        
        Note that Python complex types are not handled, as there is no
        ECMAScript equivalent type.
        
        """
        if isinstance(n, complex):
            if n.imag:
                raise JSONEncodeError('Can not encode a complex number that has a non-zero imaginary part',n)
            n = n.real
        if isinstance(n, (int,long)):
            return str(n)
        if decimal and isinstance(n, decimal.Decimal):
            return str(n)
        global nan, inf, neginf
        if n is nan:
            return 'NaN'
        elif n is inf:
            return 'Infinity'
        elif n is neginf:
            return '-Infinity'
        elif isinstance(n, float):
            # Check for non-numbers.
            # In python nan == inf == -inf, so must use repr() to distinguish
            reprn = repr(n).lower()
            if ('inf' in reprn and '-' in reprn) or n == neginf:
                return '-Infinity'
            elif 'inf' in reprn or n is inf:
                return 'Infinity'
            elif 'nan' in reprn or n is nan:
                return 'NaN'
            return repr(n)
        else:
            raise TypeError('encode_number expected an integral, float, or decimal number type',type(n))

    def decode_string(self, s, i=0, imax=None):
        """Intermediate-level decoder for JSON string literals.

        Takes a string and a starting index, and returns a Python
        string (or unicode string) and the index of the next unparsed
        character.

        """
        if imax is None:
            imax = len(s)
        if imax < i+2 or s[i] not in '"\'':
            raise JSONDecodeError('string literal must be properly quoted',s[i:])
        closer = s[i]
        if closer == '\'' and not self._allow_single_quoted_strings:
            raise JSONDecodeError('string literals must use double quotation marks in strict JSON',s[i:])
        i += 1 # skip quote
        if self._allow_js_string_escapes:
            escapes = self._escapes_js
        else:
            escapes = self._escapes_json
        ccallowed = self._allow_control_char_in_string
        chunks = []
        _append = chunks.append
        done = False
        high_surrogate = None
        while i < imax:
            c = s[i]
            # Make sure a high surrogate is immediately followed by a low surrogate
            if high_surrogate and (i+1 >= imax or s[i:i+2] != '\\u'):
                raise JSONDecodeError('High unicode surrogate must be followed by a low surrogate',s[i:])
            if c == closer:
                i += 1 # skip end quote
                done = True
                break
            elif c == '\\':
                # Escaped character
                i += 1
                if i >= imax:
                    raise JSONDecodeError('escape in string literal is incomplete',s[i-1:])
                c = s[i]

                if '0' <= c <= '7' and self._allow_octal_numbers:
                    # Handle octal escape codes first so special \0 doesn't kick in yet.
                    # Follow Annex B.1.2 of ECMAScript standard.
                    if '0' <= c <= '3':
                        maxdigits = 3
                    else:
                        maxdigits = 2
                    for k in range(i, i+maxdigits+1):
                        if k >= imax or s[k] not in octaldigits:
                            break
                    n = decode_octal(s[i:k])
                    if n < 128:
                        _append( chr(n) )
                    else:
                        _append( unichr(n) )
                    i = k
                    continue

                if escapes.has_key(c):
                    _append(escapes[c])
                    i += 1
                elif c == 'u' or c == 'x':
                    i += 1
                    if c == 'u':
                        digits = 4
                    else: # c== 'x'
                        if not self._allow_js_string_escapes:
                            raise JSONDecodeError(r'string literals may not use the \x hex-escape in strict JSON',s[i-1:])
                        digits = 2
                    if i+digits >= imax:
                        raise JSONDecodeError('numeric character escape sequence is truncated',s[i-1:])
                    n = decode_hex( s[i:i+digits] )
                    if high_surrogate:
                        # Decode surrogate pair and clear high surrogate
                        _append( surrogate_pair_as_unicode( high_surrogate, unichr(n) ) )
                        high_surrogate = None
                    elif n < 128:
                        # ASCII chars always go in as a str
                        _append( chr(n) )
                    elif 0xd800 <= n <= 0xdbff: # high surrogate
                        if imax < i + digits + 2 or s[i+digits] != '\\' or s[i+digits+1] != 'u':
                            raise JSONDecodeError('High unicode surrogate must be followed by a low surrogate',s[i-2:])
                        high_surrogate = unichr(n)  # remember until we get to the low surrogate
                    elif 0xdc00 <= n <= 0xdfff: # low surrogate
                        raise JSONDecodeError('Low unicode surrogate must be proceeded by a high surrogate',s[i-2:])
                    else:
                        # Other chars go in as a unicode char
                        _append( unichr(n) )
                    i += digits
                else:
                    # Unknown escape sequence
                    if self._allow_nonescape_characters:
                        _append( c )
                        i += 1
                    else:
                        raise JSONDecodeError('unsupported escape code in JSON string literal',s[i-1:])
            elif ord(c) <= 0x1f: # A control character
                if self.islineterm(c):
                    raise JSONDecodeError('line terminator characters must be escaped inside string literals',s[i:])
                elif ccallowed:
                    _append( c )
                    i += 1
                else:
                    raise JSONDecodeError('control characters must be escaped inside JSON string literals',s[i:])
            else: # A normal character; not an escape sequence or end-quote.
                # Find a whole sequence of "safe" characters so we can append them
                # all at once rather than one a time, for speed.
                j = i
                i += 1
                while i < imax and s[i] not in unsafe_string_chars and s[i] != closer:
                    i += 1
                _append(s[j:i])
        if not done:
            raise JSONDecodeError('string literal is not terminated with a quotation mark',s)
        s = ''.join( chunks )
        return s, i

    def encode_string(self, s):
        """Encodes a Python string into a JSON string literal.

        """
        # Must handle instances of UserString specially in order to be
        # able to use ord() on it's simulated "characters".
        import UserString
        if isinstance(s, (UserString.UserString, UserString.MutableString)):
            def tochar(c):
                return c.data
        else:
            # Could use "lambda c:c", but that is too slow.  So we set to None
            # and use an explicit if test inside the loop.
            tochar = None
        
        chunks = []
        chunks.append('"')
        revesc = self._rev_escapes
        asciiencodable = self._asciiencodable
        encunicode = self._encode_unicode_as_escapes
        i = 0
        imax = len(s)
        while i < imax:
            if tochar:
                c = tochar(s[i])
            else:
                c = s[i]
            cord = ord(c)
            if cord < 256 and asciiencodable[cord] and isinstance(encunicode, bool):
                # Contiguous runs of plain old printable ASCII can be copied
                # directly to the JSON output without worry (unless the user
                # has supplied a custom is-encodable function).
                j = i
                i += 1
                while i < imax:
                    if tochar:
                        c = tochar(s[i])
                    else:
                        c = s[i]
                    cord = ord(c)
                    if cord < 256 and asciiencodable[cord]:
                        i += 1
                    else:
                        break
                chunks.append( unicode(s[j:i]) )
            elif revesc.has_key(c):
                # Has a shortcut escape sequence, like "\n"
                chunks.append(revesc[c])
                i += 1
            elif cord <= 0x1F:
                # Always unicode escape ASCII-control characters
                chunks.append(r'\u%04x' % cord)
                i += 1
            elif 0xD800 <= cord <= 0xDFFF:
                # A raw surrogate character!  This should never happen
                # and there's no way to include it in the JSON output.
                # So all we can do is complain.
                cname = 'U+%04X' % cord
                raise JSONEncodeError('can not include or escape a Unicode surrogate character',cname)
            elif cord <= 0xFFFF:
                # Other BMP Unicode character
                if isinstance(encunicode, bool):
                    doesc = encunicode
                else:
                    doesc = encunicode( c )
                if doesc:
                    chunks.append(r'\u%04x' % cord)
                else:
                    chunks.append( c )
                i += 1
            else: # ord(c) >= 0x10000
                # Non-BMP Unicode
                if isinstance(encunicode, bool):
                    doesc = encunicode
                else:
                    doesc = encunicode( c )
                if doesc:
                    for surrogate in unicode_as_surrogate_pair(c):
                        chunks.append(r'\u%04x' % ord(surrogate))
                else:
                    chunks.append( c )
                i += 1
        chunks.append('"')
        return ''.join( chunks )

    def skip_comment(self, txt, i=0):
        """Skips an ECMAScript comment, either // or /* style.

        The contents of the comment are returned as a string, as well
        as the index of the character immediately after the comment.

        """
        if i+1 >= len(txt) or txt[i] != '/' or txt[i+1] not in '/*':
            return None, i
        if not self._allow_comments:
            raise JSONDecodeError('comments are not allowed in strict JSON',txt[i:])
        multiline = (txt[i+1] == '*')
        istart = i
        i += 2
        while i < len(txt):
            if multiline:
                if txt[i] == '*' and i+1 < len(txt) and txt[i+1] == '/':
                    j = i+2
                    break
                elif txt[i] == '/' and i+1 < len(txt) and txt[i+1] == '*':
                    raise JSONDecodeError('multiline /* */ comments may not nest',txt[istart:i+1])
            else:
                if self.islineterm(txt[i]):
                    j = i  # line terminator is not part of comment
                    break
            i += 1

        if i >= len(txt):
            if not multiline:
                j = len(txt)  # // comment terminated by end of file is okay
            else:
                raise JSONDecodeError('comment was never terminated',txt[istart:])
        return txt[istart:j], j

    def skipws(self, txt, i=0, imax=None, skip_comments=True):
        """Skips whitespace.
        """
        if not self._allow_comments and not self._allow_unicode_whitespace:
            if imax is None:
                imax = len(txt)
            while i < imax and txt[i] in ' \r\n\t':
                i += 1
            return i
        else:
            return self.skipws_any(txt, i, imax, skip_comments)

    def skipws_any(self, txt, i=0, imax=None, skip_comments=True):
        """Skips all whitespace, including comments and unicode whitespace

        Takes a string and a starting index, and returns the index of the
        next non-whitespace character.

        If skip_comments is True and not running in strict JSON mode, then
        comments will be skipped over just like whitespace.

        """
        if imax is None:
            imax = len(txt)
        while i < imax:
            if txt[i] == '/':
                cmt, i = self.skip_comment(txt, i)
            if i < imax and self.isws(txt[i]):
                i += 1
            else:
                break
        return i

    def decode_composite(self, txt, i=0, imax=None):
        """Intermediate-level JSON decoder for composite literal types (array and object).

        Takes text and a starting index, and returns either a Python list or
        dictionary and the index of the next unparsed character.

        """
        if imax is None:
            imax = len(txt)
        i = self.skipws(txt, i, imax)
        starti = i
        if i >= imax or txt[i] not in '{[':
            raise JSONDecodeError('composite object must start with "[" or "{"',txt[i:])
        if txt[i] == '[':
            isdict = False
            closer = ']'
            obj = []
        else:
            isdict = True
            closer = '}'
            obj = {}
        i += 1 # skip opener
        i = self.skipws(txt, i, imax)

        if i < imax and txt[i] == closer:
            # empty composite
            i += 1
            done = True
        else:
            saw_value = False   # set to false at beginning and after commas
            done = False
            while i < imax:
                i = self.skipws(txt, i, imax)
                if i < imax and (txt[i] == ',' or txt[i] == closer):
                    c = txt[i]
                    i += 1
                    if c == ',':
                        if not saw_value:
                            # no preceeding value, an elided (omitted) element
                            if isdict:
                                raise JSONDecodeError('can not omit elements of an object (dictionary)')
                            if self._allow_omitted_array_elements:
                                if self._allow_undefined_values:
                                    obj.append( undefined )
                                else:
                                    obj.append( None )
                            else:
                                raise JSONDecodeError('strict JSON does not permit omitted array (list) elements',txt[i:])
                        saw_value = False
                        continue
                    else: # c == closer
                        if not saw_value and not self._allow_trailing_comma_in_literal:
                            if isdict:
                                raise JSONDecodeError('strict JSON does not allow a final comma in an object (dictionary) literal',txt[i-2:])
                            else:
                                raise JSONDecodeError('strict JSON does not allow a final comma in an array (list) literal',txt[i-2:])
                        done = True
                        break

                # Decode the item
                if isdict and self._allow_nonstring_keys:
                    r = self.decodeobj(txt, i, identifier_as_string=True)
                else:
                    r = self.decodeobj(txt, i, identifier_as_string=False)
                if r:
                    if saw_value:
                        # two values without a separating comma
                        raise JSONDecodeError('values must be separated by a comma', txt[i:r[1]])
                    saw_value = True
                    i = self.skipws(txt, r[1], imax)
                    if isdict:
                        key = r[0]  # Ref 11.1.5
                        if not isstringtype(key):
                            if isnumbertype(key):
                                if not self._allow_nonstring_keys:
                                    raise JSONDecodeError('strict JSON only permits string literals as object properties (dictionary keys)',txt[starti:])
                            else:
                                raise JSONDecodeError('object properties (dictionary keys) must be either string literals or numbers',txt[starti:])
                        if i >= imax or txt[i] != ':':
                            raise JSONDecodeError('object property (dictionary key) has no value, expected ":"',txt[starti:])
                        i += 1
                        i = self.skipws(txt, i, imax)
                        rval = self.decodeobj(txt, i)
                        if rval:
                            i = self.skipws(txt, rval[1], imax)
                            obj[key] = rval[0]
                        else:
                            raise JSONDecodeError('object property (dictionary key) has no value',txt[starti:])
                    else: # list
                        obj.append( r[0] )
                else: # not r
                    if isdict:
                        raise JSONDecodeError('expected a value, or "}"',txt[i:])
                    elif not self._allow_omitted_array_elements:
                        raise JSONDecodeError('expected a value or "]"',txt[i:])
                    else:
                        raise JSONDecodeError('expected a value, "," or "]"',txt[i:])
            # end while
        if not done:
            if isdict:
                raise JSONDecodeError('object literal (dictionary) is not terminated',txt[starti:])
            else:
                raise JSONDecodeError('array literal (list) is not terminated',txt[starti:])
        return obj, i

    def decode_javascript_identifier(self, name):
        """Convert a JavaScript identifier into a Python string object.

        This method can be overriden by a subclass to redefine how JavaScript
        identifiers are turned into Python objects.  By default this just
        converts them into strings.

        """
        return name

    def decodeobj(self, txt, i=0, imax=None, identifier_as_string=False, only_object_or_array=False):
        """Intermediate-level JSON decoder.

        Takes a string and a starting index, and returns a two-tuple consting
        of a Python object and the index of the next unparsed character.

        If there is no value at all (empty string, etc), the None is
        returned instead of a tuple.

        """
        if imax is None:
            imax = len(txt)
        obj = None
        i = self.skipws(txt, i, imax)
        if i >= imax:
            raise JSONDecodeError('Unexpected end of input')
        c = txt[i]

        if c == '[' or c == '{':
            obj, i = self.decode_composite(txt, i, imax)
        elif only_object_or_array:
            raise JSONDecodeError('JSON document must start with an object or array type only', txt[i:i+20])
        elif c == '"' or c == '\'':
            obj, i = self.decode_string(txt, i, imax)
        elif c.isdigit() or c in '.+-':
            obj, i = self.decode_number(txt, i, imax)
        elif c.isalpha() or c in'_$':
            j = i
            while j < imax and (txt[j].isalnum() or txt[j] in '_$'):
                j += 1
            kw = txt[i:j]
            if kw == 'null':
                obj, i = None, j
            elif kw == 'true':
                obj, i = True, j
            elif kw == 'false':
                obj, i = False, j
            elif kw == 'undefined':
                if self._allow_undefined_values:
                    obj, i = undefined, j
                else:
                    raise JSONDecodeError('strict JSON does not allow undefined elements',txt[i:])
            elif kw == 'NaN' or kw == 'Infinity':
                obj, i = self.decode_number(txt, i)
            else:
                if identifier_as_string:
                    obj, i = self.decode_javascript_identifier(kw), j
                else:
                    raise JSONDecodeError('unknown keyword or identifier',kw)
        else:
            raise JSONDecodeError('can not decode value',txt[i:])
        return obj, i



    def decode(self, txt):
        """Decodes a JSON-endoded string into a Python object."""
        if self._allow_unicode_format_control_chars:
            txt = self.strip_format_control_chars(txt)
        r = self.decodeobj(txt, 0, only_object_or_array=not self._allow_any_type_at_start)
        if not r:
            raise JSONDecodeError('can not decode value',txt)
        else:
            obj, i = r
            i = self.skipws(txt, i)
            if i < len(txt):
                raise JSONDecodeError('unexpected or extra text',txt[i:])
        return obj

    def encode(self, obj, nest_level=0):
        """Encodes the Python object into a JSON string representation.

        This method will first attempt to encode an object by seeing
        if it has a json_equivalent() method.  If so than it will
        call that method and then recursively attempt to encode
        the object resulting from that call.

        Next it will attempt to determine if the object is a native
        type or acts like a squence or dictionary.  If so it will
        encode that object directly.

        Finally, if no other strategy for encoding the object of that
        type exists, it will call the encode_default() method.  That
        method currently raises an error, but it could be overridden
        by subclasses to provide a hook for extending the types which
        can be encoded.

        """
        chunks = []
        self.encode_helper(chunks, obj, nest_level)
        return ''.join( chunks )

    def encode_helper(self, chunklist, obj, nest_level):
        #print 'encode_helper(chunklist=%r, obj=%r, nest_level=%r)'%(chunklist,obj,nest_level)
        if hasattr(obj, 'json_equivalent'):
            json = self.encode_equivalent( obj, nest_level=nest_level )
            if json is not None:
                chunklist.append( json )
                return
        if obj is None:
            chunklist.append( self.encode_null() )
        elif obj is undefined:
            if self._allow_undefined_values:
                chunklist.append( self.encode_undefined() )
            else:
                raise JSONEncodeError('strict JSON does not permit "undefined" values')
        elif isinstance(obj, bool):
            chunklist.append( self.encode_boolean(obj) )
        elif isinstance(obj, (int,long,float,complex)) or \
                 (decimal and isinstance(obj, decimal.Decimal)):
            chunklist.append( self.encode_number(obj) )
        elif isinstance(obj, basestring) or isstringtype(obj):
            chunklist.append( self.encode_string(obj) )
        else:
            self.encode_composite(chunklist, obj, nest_level)

    def encode_composite(self, chunklist, obj, nest_level):
        """Encodes just dictionaries, lists, or sequences.

        Basically handles any python type for which iter() can create
        an iterator object.

        This method is not intended to be called directly.  Use the
        encode() method instead.

        """
        #print 'encode_complex_helper(chunklist=%r, obj=%r, nest_level=%r)'%(chunklist,obj,nest_level)
        try:
            # Is it a dictionary or UserDict?  Try iterkeys method first.
            it = obj.iterkeys()
        except AttributeError:
            try:
                # Is it a sequence?  Try to make an iterator for it.
                it = iter(obj)
            except TypeError:
                it = None
        if it is not None:
            # Does it look like a dictionary?  Check for a minimal dict or
            # UserDict interface.
            isdict = hasattr(obj, '__getitem__') and hasattr(obj, 'keys')
            compactly = self._encode_compactly
            if isdict:
                chunklist.append('{')
                if compactly:
                    dictcolon = ':'
                else:
                    dictcolon = ' : '
            else:
                chunklist.append('[')
            #print nest_level, 'opening sequence:', repr(chunklist)
            if not compactly:
                indent0 = '  ' * nest_level
                indent = '  ' * (nest_level+1)
                chunklist.append(' ')
            sequence_chunks = []  # use this to allow sorting afterwards if dict
            try: # while not StopIteration
                numitems = 0
                while True:
                    obj2 = it.next()
                    if obj2 is obj:
                        raise JSONEncodeError('trying to encode an infinite sequence',obj)
                    if isdict and not isstringtype(obj2):
                        # Check JSON restrictions on key types
                        if isnumbertype(obj2):
                            if not self._allow_nonstring_keys:
                                raise JSONEncodeError('object properties (dictionary keys) must be strings in strict JSON',obj2)
                        else:
                            raise JSONEncodeError('object properties (dictionary keys) can only be strings or numbers in ECMAScript',obj2)

                    # Encode this item in the sequence and put into item_chunks
                    item_chunks = []
                    self.encode_helper( item_chunks, obj2, nest_level=nest_level+1 )
                    if isdict:
                        item_chunks.append(dictcolon)
                        obj3 = obj[obj2]
                        self.encode_helper(item_chunks, obj3, nest_level=nest_level+2)

                    #print nest_level, numitems, 'item:', repr(obj2)
                    #print nest_level, numitems, 'sequence_chunks:', repr(sequence_chunks)
                    #print nest_level, numitems, 'item_chunks:', repr(item_chunks)
                    #extend_list_with_sep(sequence_chunks, item_chunks)
                    sequence_chunks.append(item_chunks)
                    #print nest_level, numitems, 'new sequence_chunks:', repr(sequence_chunks)
                    numitems += 1
            except StopIteration:
                pass

            if isdict and self._sort_dictionary_keys:
                sequence_chunks.sort()  # Note sorts by JSON repr, not original Python object
            if compactly:
                sep = ','
            else:
                sep = ',\n' + indent

            #print nest_level, 'closing sequence'
            #print nest_level, 'chunklist:', repr(chunklist)
            #print nest_level, 'sequence_chunks:', repr(sequence_chunks)
            extend_and_flatten_list_with_sep( chunklist, sequence_chunks, sep )
            #print nest_level, 'new chunklist:', repr(chunklist)

            if not compactly:
                if numitems > 1:
                    chunklist.append('\n' + indent0)
                else:
                    chunklist.append(' ')
            if isdict:
                chunklist.append('}')
            else:
                chunklist.append(']')
        else: # Can't create an iterator for the object
            json2 = self.encode_default( obj, nest_level=nest_level )
            chunklist.append( json2 )

    def encode_equivalent( self, obj, nest_level=0 ):
        """This method is used to encode user-defined class objects.

        The object being encoded should have a json_equivalent()
        method defined which returns another equivalent object which
        is easily JSON-encoded.  If the object in question has no
        json_equivalent() method available then None is returned
        instead of a string so that the encoding will attempt the next
        strategy.

        If a caller wishes to disable the calling of json_equivalent()
        methods, then subclass this class and override this method
        to just return None.
        
        """
        if hasattr(obj, 'json_equivalent') \
               and callable(getattr(obj,'json_equivalent')):
            obj2 = obj.json_equivalent()
            if obj2 is obj:
                # Try to prevent careless infinite recursion
                raise JSONEncodeError('object has a json_equivalent() method that returns itself',obj)
            json2 = self.encode( obj2, nest_level=nest_level )
            return json2
        else:
            return None

    def encode_default( self, obj, nest_level=0 ):
        """This method is used to encode objects into JSON which are not straightforward.

        This method is intended to be overridden by subclasses which wish
        to extend this encoder to handle additional types.

        """
        raise JSONEncodeError('can not encode object into a JSON representation',obj)


# ------------------------------

def encode( obj, strict=False, compactly=True, escape_unicode=False, encoding=None ):
    """Encodes a Python object into a JSON-encoded string.

    If 'strict' is set to True, then only strictly-conforming JSON
    output will be produced.  Note that this means that some types
    of values may not be convertable and will result in a
    JSONEncodeError exception.

    If 'compactly' is set to True, then the resulting string will
    have all extraneous white space removed; if False then the
    string will be "pretty printed" with whitespace and indentation
    added to make it more readable.

    If 'escape_unicode' is set to True, then all non-ASCII characters
    will be represented as a unicode escape sequence; if False then
    the actual real unicode character will be inserted.

    If no encoding is specified (encoding=None) then the output will
    either be a Python string (if entirely ASCII) or a Python unicode
    string type.

    However if an encoding name is given then the returned value will
    be a python string which is the byte sequence encoding the JSON
    value.  As the default/recommended encoding for JSON is UTF-8,
    you should almost always pass in encoding='utf8'.

    """
    import sys
    encoder = None # Custom codec encoding function
    bom = None  # Byte order mark to prepend to final output
    cdk = None  # Codec to use
    if encoding is not None:
        import codecs
        try:
            cdk = codecs.lookup(encoding)
        except LookupError:
            cdk = None

        if cdk:
            pass
        elif not cdk:
            # No built-in codec was found, see if it is something we
            # can do ourself.
            encoding = encoding.lower()
            if encoding.startswith('utf-32') or encoding.startswith('utf32') \
                   or encoding.startswith('ucs4') \
                   or encoding.startswith('ucs-4'):
                # Python doesn't natively have a UTF-32 codec, but JSON
                # requires that it be supported.  So we must decode these
                # manually.
                if encoding.endswith('le'):
                    encoder = utf32le_encode
                elif encoding.endswith('be'):
                    encoder = utf32be_encode
                else:
                    encoder = utf32be_encode
                    bom = codecs.BOM_UTF32_BE
            elif encoding.startswith('ucs2') or encoding.startswith('ucs-2'):
                # Python has no UCS-2, but we can simulate with
                # UTF-16.  We just need to force us to not try to
                # encode anything past the BMP.
                encoding = 'utf-16'
                if not escape_unicode and not callable(escape_unicode):
                   escape_unicode = lambda c: (0xD800 <= ord(c) <= 0xDFFF) or ord(c) >= 0x10000
            else:
                raise JSONEncodeError('this python has no codec for this character encoding',encoding)

    if not escape_unicode and not callable(escape_unicode):
        if encoding and encoding.startswith('utf'):
            # All UTF-x encodings can do the whole Unicode repertoire, so
            # do nothing special.
            pass
        else:
            # Even though we don't want to escape all unicode chars,
            # the encoding being used may force us to do so anyway.
            # We must pass in a function which says which characters
            # the encoding can handle and which it can't.
            def in_repertoire( c, encoding_func ):
                try:
                    x = encoding_func( c, errors='strict' )
                except UnicodeError:
                    return False
                return True
            if encoder:
                escape_unicode = lambda c: not in_repertoire(c, encoder)
            elif cdk:
                escape_unicode = lambda c: not in_repertoire(c, cdk[0])
            else:
                pass # Let the JSON object deal with it

    j = JSON( strict=strict, compactly=compactly, escape_unicode=escape_unicode )

    unitxt = j.encode( obj )
    if encoder:
        txt = encoder( unitxt )
    elif encoding is not None:
        txt = unitxt.encode( encoding )
    else:
        txt = unitxt
    if bom:
        txt = bom + txt
    return txt


def decode( txt, strict=False, encoding=None, **kw ):
    """Decodes a JSON-encoded string into a Python object.

    If 'strict' is set to True, then those strings that are not
    entirely strictly conforming to JSON will result in a
    JSONDecodeError exception.

    The input string can be either a python string or a python unicode
    string.  If it is already a unicode string, then it is assumed
    that no character set decoding is required.

    However, if you pass in a non-Unicode text string (i.e., a python
    type 'str') then an attempt will be made to auto-detect and decode
    the character encoding.  This will be successful if the input was
    encoded in any of UTF-8, UTF-16 (BE or LE), or UTF-32 (BE or LE),
    and of course plain ASCII works too.
    
    Note though that if you know the character encoding, then you
    should convert to a unicode string yourself, or pass it the name
    of the 'encoding' to avoid the guessing made by the auto
    detection, as with

        python_object = demjson.decode( input_bytes, encoding='utf8' )

    Optional keywords arguments must be of the form
        allow_xxxx=True/False
    or
        prevent_xxxx=True/False
    where each will allow or prevent the specific behavior, after the
    evaluation of the 'strict' argument.  For example, if strict=True
    then by also passing 'allow_comments=True' then comments will be
    allowed.  If strict=False then prevent_comments=True will allow
    everything except comments.
    
    """
    # Initialize the JSON object
    j = JSON( strict=strict )
    for keyword, value in kw.items():
        if keyword.startswith('allow_'):
            behavior = keyword[6:]
            allow = bool(value)
        elif keyword.startswith('prevent_'):
            behavior = keyword[8:]
            allow = not bool(value)
        else:
            raise ValueError('unknown keyword argument', keyword)
        if allow:
            j.allow(behavior)
        else:
            j.prevent(behavior)

    # Convert the input string into unicode if needed.
    if isinstance(txt,unicode):
        unitxt = txt
    else:
        if encoding is None:
            unitxt = auto_unicode_decode( txt )
        else:
            cdk = None # codec
            decoder = None
            import codecs
            try:
                cdk = codecs.lookup(encoding)
            except LookupError:
                encoding = encoding.lower()
                decoder = None
                if encoding.startswith('utf-32') \
                       or encoding.startswith('ucs4') \
                       or encoding.startswith('ucs-4'):
                    # Python doesn't natively have a UTF-32 codec, but JSON
                    # requires that it be supported.  So we must decode these
                    # manually.
                    if encoding.endswith('le'):
                        decoder = utf32le_decode
                    elif encoding.endswith('be'):
                        decoder = utf32be_decode
                    else:
                        if txt.startswith( codecs.BOM_UTF32_BE ):
                            decoder = utf32be_decode
                            txt = txt[4:]
                        elif txt.startswith( codecs.BOM_UTF32_LE ):
                            decoder = utf32le_decode
                            txt = txt[4:]
                        else:
                            if encoding.startswith('ucs'):
                                raise JSONDecodeError('UCS-4 encoded string must start with a BOM')
                            decoder = utf32be_decode # Default BE for UTF, per unicode spec
                elif encoding.startswith('ucs2') or encoding.startswith('ucs-2'):
                    # Python has no UCS-2, but we can simulate with
                    # UTF-16.  We just need to force us to not try to
                    # encode anything past the BMP.
                    encoding = 'utf-16'

            if decoder:
                unitxt = decoder(txt)
            elif encoding:
                unitxt = txt.decode(encoding)
            else:
                raise JSONDecodeError('this python has no codec for this character encoding',encoding)

        # Check that the decoding seems sane.  Per RFC 4627 section 3:
        #    "Since the first two characters of a JSON text will
        #    always be ASCII characters [RFC0020], ..."
        #
        # This check is probably not necessary, but it allows us to
        # raise a suitably descriptive error rather than an obscure
        # syntax error later on.
        #
        # Note that the RFC requirements of two ASCII characters seems
        # to be an incorrect statement as a JSON string literal may
        # have as it's first character any unicode character.  Thus
        # the first two characters will always be ASCII, unless the
        # first character is a quotation mark.  And in non-strict
        # mode we can also have a few other characters too.
        if len(unitxt) > 2:
            first, second = unitxt[:2]
            if first in '"\'':
                pass # second can be anything inside string literal
            else:
                if ((ord(first) < 0x20 or ord(first) > 0x7f) or \
                    (ord(second) < 0x20 or ord(second) > 0x7f)) and \
                    (not j.isws(first) and not j.isws(second)):
                    # Found non-printable ascii, must check unicode
                    # categories to see if the character is legal.
                    # Only whitespace, line and paragraph separators,
                    # and format control chars are legal here.
                    import unicodedata
                    catfirst = unicodedata.category(unicode(first))
                    catsecond = unicodedata.category(unicode(second))
                    if catfirst not in ('Zs','Zl','Zp','Cf') or \
                           catsecond not in ('Zs','Zl','Zp','Cf'):
                        raise JSONDecodeError('the decoded string is gibberish, is the encoding correct?',encoding)
    # Now ready to do the actual decoding
    obj = j.decode( unitxt )
    return obj

# end file

########NEW FILE########
__FILENAME__ = filters
import datetime
from django.template.defaultfilters import timesince
from django.conf import settings
from google.appengine.ext import webapp

register = webapp.template.create_template_register()

UTC_OFFSET = getattr(settings, "UTC_OFFSET", 0)

def bettertimesince(dt):
    delta = datetime.datetime.utcnow() - dt
    local_dt = dt + datetime.timedelta(hours=UTC_OFFSET)
    if delta.days == 0:
        return timesince(dt) + " ago"
    elif delta.days == 1:
        return "Yesterday" + local_dt.strftime(" at %I:%M %p")
    elif delta.days < 5:
        return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][local_dt.weekday()] + local_dt.strftime(" at %I:%M %p")
    elif delta.days < 365:
        return local_dt.strftime("%B %d at %I:%M %p")
    else:
        return local_dt.strftime("%B %d, %Y")

register.filter(bettertimesince)

########NEW FILE########
__FILENAME__ = main
import BeautifulSoup
import demjson
import functools
import hashlib
import logging
import os
import uuid
import urllib

from google.appengine.dist import use_library
use_library("django", "1.0")

from django.conf import settings
settings._target = None
os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

from django.template.defaultfilters import slugify
from django.utils import feedgenerator
from django.utils import simplejson

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.db import djangoforms
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

DOPPLR_TOKEN = getattr(settings, "DOPPLR_TOKEN", None)
MAPS_API_KEY = getattr(settings, "MAPS_API_KEY", None)
SHOW_CURRENT_CITY = getattr(settings, "SHOW_CURRENT_CITY", False)
TITLE = getattr(settings, "TITLE", "Blog")
OLD_WORDPRESS_BLOG = getattr(settings, "OLD_WORDPRESS_BLOG", None)
NUM_RECENT = getattr(settings, "NUM_RECENT", 5)
NUM_MAIN = getattr(settings, "NUM_MAIN", 10)
NUM_FLICKR = getattr(settings, "NUM_FLICKR", 1)
FLICKR_ID = getattr(settings, "FLICKR_ID", None)

webapp.template.register_template_library("filters")

def admin(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        user = users.get_current_user()
        if not user:
            if self.request.method == "GET":
                return self.redirect(users.create_login_url(self.request.uri))
            return self.error(403)
        elif not users.is_current_user_admin():
            return self.error(403)
        else:
            return method(self, *args, **kwargs)
    return wrapper


class MediaRSSFeed(feedgenerator.Atom1Feed):
    def root_attributes(self):
        attrs = super(MediaRSSFeed, self).root_attributes()
        attrs["xmlns:media"] = "http://search.yahoo.com/mrss/"
        return attrs

    def add_item_elements(self, handler, item):
        super(MediaRSSFeed, self).add_item_elements(handler, item)
        self.add_thumbnails_element(handler, item)

    def add_thumbnail_element(self, handler, item):
        thumbnail = item.get("thumbnail", None)
        if thumbnail:
            if thumbnail["title"]:
                handler.addQuickElement("media:title", title)
            handler.addQuickElement("media:thumbnail", "", {
                "url": thumbnail["url"],
            })

    def add_thumbnails_element(self, handler, item):
        thumbnails = item.get("thumbnails", [])
        for thumbnail in thumbnails:
            handler.startElement("media:group", {})
            if thumbnail["title"]:
                handler.addQuickElement("media:title", thumbnail["title"])
            handler.addQuickElement("media:thumbnail", "", thumbnail)
            handler.endElement("media:group")


class Entry(db.Model):
    author = db.UserProperty()
    title = db.StringProperty(required=True)
    slug = db.StringProperty(required=True)
    body = db.TextProperty(required=True)
    published = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    tags = db.ListProperty(db.Category)


class EntryForm(djangoforms.ModelForm):
    class Meta:
        model = Entry
        exclude = ["author", "slug", "published", "updated", "tags"]


class BaseRequestHandler(webapp.RequestHandler):
    def initialize(self, request, response):
        webapp.RequestHandler.initialize(self, request, response)
        if request.path.endswith("/") and not request.path == "/":
            redirect = request.path[:-1]
            if request.query_string:
                redirect += "?" + request.query_string
            return self.redirect(redirect, permanent=True)

    def head(self, *args, **kwargs):
        pass

    def raise_error(self, code):
        self.error(code)
        self.render("%i.html" % code)

    def get_current_city(self):
        key = "current_city/now"
        current_city = memcache.get(key)
        if not current_city:
            try:
                response = urlfetch.fetch("https://www.dopplr.com/api/traveller_info?format=js&token=" + DOPPLR_TOKEN)
                if response.status_code == 200:
                    data = simplejson.loads(response.content)
                    current_city = data["traveller"]["current_city"]
                    current_city["maps_api_key"] = MAPS_API_KEY
                    memcache.set(key, current_city, 60*60*5)
            except (urlfetch.DownloadError, ValueError):
                pass
        return current_city

    def get_recent_entries(self, num=NUM_RECENT):
        key = "entries/recent/%d" % num
        entries = memcache.get(key)
        if not entries:
            entries = db.Query(Entry).order("-published").fetch(limit=num)
            memcache.set(key, list(entries))
        return entries

    def get_main_page_entries(self, num=NUM_MAIN):
        key = "entries/main/%d" % num
        entries = memcache.get(key)
        if not entries:
            entries = db.Query(Entry).order("-published").fetch(limit=num)
            memcache.set(key, list(entries))
        return entries

    def get_archive_entries(self):
        key = "entries/archive"
        entries = memcache.get(key)
        if not entries:
            entries = db.Query(Entry).order("-published")
            memcache.set(key, list(entries))
        return entries

    def get_entry_from_slug(self, slug):
        key = "entry/%s" % slug
        entry = memcache.get(key)
        if not entry:
            entry = db.Query(Entry).filter("slug =", slug).get()
            if entry:
                memcache.set(key, entry)
        return entry

    def get_tagged_entries(self, tag):
        key = "entries/tag/%s" % tag
        entries = memcache.get(key)
        if not entries:
            entries = db.Query(Entry).filter("tags =", tag).order("-published")
            memcache.set(key, list(entries))
        return entries

    def kill_entries_cache(self, slug=None, tags=[]):
        memcache.delete("entries/recent/%d" % NUM_RECENT)
        memcache.delete("entries/main/%d" % NUM_MAIN)
        memcache.delete("entries/archive")
        if slug:
            memcache.delete("entry/%s" % slug)
        for tag in tags:
            memcache.delete("entries/tag/%s" % tag)
        
    def get_integer_argument(self, name, default):
        try:
            return int(self.request.get(name, default))
        except (TypeError, ValueError):
            return default

    def fetch_headers(self, url):
        key = "headers/" + url
        headers = memcache.get(key)
        if not headers:
            try:
                response = urlfetch.fetch(url, method=urlfetch.HEAD)
                if response.status_code == 200:
                    headers = response.headers
                    memcache.set(key, headers)
            except urlfetch.DownloadError:
                pass
        return headers

    def find_enclosure(self, html):
        soup = BeautifulSoup.BeautifulSoup(html)
        img = soup.find("img")
        if img:
            headers = self.fetch_headers(img["src"])
            if headers:
                enclosure = feedgenerator.Enclosure(img["src"],
                    headers["Content-Length"], headers["Content-Type"])
                return enclosure
        return None

    def find_thumbnails(self, html):
        soup = BeautifulSoup.BeautifulSoup(html)
        imgs = soup.findAll("img")
        thumbnails = []
        for img in imgs:
            if "nomediarss" in img.get("class", "").split():
                continue
            thumbnails.append({
                "url": img["src"],
                "title": img.get("title", img.get("alt", "")),
                "width": img.get("width", ""),
                "height": img.get("height", ""),
            })
        return thumbnails

    def generate_sup_id(self, url=None):
        return hashlib.md5(url or self.request.url).hexdigest()[:10]

    def set_sup_id_header(self):
        sup_id = self.generate_sup_id()
        self.response.headers["X-SUP-ID"] = \
            "http://friendfeed.com/api/public-sup.json#%s" % sup_id
            
    def render_feed(self, entries):
        f = MediaRSSFeed(
            title=TITLE,
            link="http://" + self.request.host + "/",
            description=TITLE,
            language="en",
        )
        for entry in entries[:10]:
            f.add_item(
                title=entry.title,
                link=self.entry_link(entry, absolute=True),
                description=entry.body,
                author_name=entry.author.nickname(),
                pubdate=entry.published,
                categories=entry.tags,
                thumbnails=self.find_thumbnails(entry.body),
            )
        data = f.writeString("utf-8")
        self.response.headers["Content-Type"] = "application/atom+xml"
        self.set_sup_id_header()
        self.response.out.write(data)

    def render_json(self, entries):
        json_entries = [{
            "title": entry.title,
            "slug": entry.slug,
            "body": entry.body,
            "author": entry.author.nickname(),
            "published": entry.published.isoformat(),
            "updated": entry.updated.isoformat(),
            "tags": entry.tags,
            "link": self.entry_link(entry, absolute=True),
        } for entry in entries]
        json = {"entries": json_entries}
        self.response.headers["Content-Type"] = "text/javascript"
        self.response.out.write(simplejson.dumps(json, sort_keys=True, 
            indent=self.get_integer_argument("pretty", None)))

    def render(self, template_file, extra_context={}):
        if "entries" in extra_context:
            format = self.request.get("format", None)
            if format == "atom":
                return self.render_feed(extra_context["entries"])
            elif format == "json":
                return self.render_json(extra_context["entries"])
        extra_context["request"] = self.request
        extra_context["admin"] = users.is_current_user_admin()
        extra_context["recent_entries"] = self.get_recent_entries()
        if SHOW_CURRENT_CITY:
            extra_context["current_city"] = self.get_current_city()
        extra_context["flickr_feed"] = self.get_flickr_feed()
        extra_context.update(settings._target.__dict__)
        template_file = "templates/%s" % template_file
        path = os.path.join(os.path.dirname(__file__), template_file)
        self.response.out.write(template.render(path, extra_context))

    def ping(self, entry=None):
        feed = "http://" + self.request.host + "/?format=atom"
        args = urllib.urlencode({
            "name": TITLE,
            "url": "http://" + self.request.host + "/",
            "changesURL": feed,
        })
        response = urlfetch.fetch("http://blogsearch.google.com/ping?" + args)
        args = urllib.urlencode({
            "url": feed,
            "supid": self.generate_sup_id(feed),
        })
        response = urlfetch.fetch("http://friendfeed.com/api/public-sup-ping?" \
            + args)
        args = urllib.urlencode({
            "bloglink": "http://" + self.request.host + "/",
        })
        response = urlfetch.fetch("http://www.feedburner.com/fb/a/pingSubmit?" \
            + args)

    def is_valid_xhtml(self, entry):
        args = urllib.urlencode({
            "uri": self.entry_link(entry, absolute=True),
        })
        try:
            response = urlfetch.fetch("http://validator.w3.org/check?" + args,
                method=urlfetch.HEAD)
        except urlfetch.DownloadError:
            return True
        return response.headers["X-W3C-Validator-Status"] == "Valid"

    def entry_link(self, entry, query_args={}, absolute=False):
        url = "/e/" + entry.slug
        if absolute:
            url = "http://" + self.request.host + url
        if query_args:
            url += "?" + urllib.urlencode(query_args)
        return url

    def get_flickr_feed(self):
        if not FLICKR_ID:
            return {}
        key = "flickr_feed"
        flickr_feed = memcache.get(key)
        if not flickr_feed:
            flickr_feed = {}
            args = urllib.urlencode({
                "id": FLICKR_ID,
                "format": "json",
                "nojsoncallback": 1,
            })
            try:
                response = urlfetch.fetch(
                    "http://api.flickr.com/services/feeds/photos_public.gne?" \
                        + args)
                if response.status_code == 200:
                    try:
                        flickr_feed = demjson.decode(response.content)
                        memcache.set(key, flickr_feed, 60*5)
                    except ValueError:
                        flickr_feed = {}
            except urlfetch.DownloadError:
                pass
        # Slice here to avoid doing it in the template
        flickr_feed["items"] = flickr_feed.get("items", [])[:NUM_FLICKR]
        return flickr_feed


class ArchivePageHandler(BaseRequestHandler):
    def get(self):
        extra_context = {
            "entries": self.get_archive_entries(),
        }
        self.render("archive.html", extra_context)


class DeleteEntryHandler(BaseRequestHandler):
    @admin
    def post(self):
        key = self.request.get("key")
        try:
            entry = db.get(key)
            entry.delete()
            self.kill_entries_cache(slug=entry.slug, tags=entry.tags)
            data = {"success": True}
        except db.BadKeyError:
            data = {"success": False}
        json = simplejson.dumps(data)
        self.response.out.write(json)


class EntryPageHandler(BaseRequestHandler):
    def head(self, slug):
        entry = self.get_entry_from_slug(slug=slug)
        if not entry:
            self.error(404)

    def get(self, slug):
        entry = self.get_entry_from_slug(slug=slug)
        if not entry:
            return self.raise_error(404)
        extra_context = {
            "entries": [entry], # So we can use the same template for everything
            "entry": entry, # To easily pull out the title
            "invalid": self.request.get("invalid", False),
        }
        self.render("entry.html", extra_context)


class FeedRedirectHandler(BaseRequestHandler):
    def get(self):
        self.redirect("/?format=atom", permanent=True)


class MainPageHandler(BaseRequestHandler):
    def head(self):
        if self.request.get("format", None) == "atom":
            self.set_sup_id_header()

    def get(self):
        offset = self.get_integer_argument("start", 0)
        if not offset:
            entries = self.get_main_page_entries()
        else:
            entries = db.Query(Entry).order("-published").fetch(limit=NUM_MAIN,
                offset=offset)
        if not entries and offset > 0:
            return self.redirect("/")
        extra_context = {
            "entries": entries,
            "next": max(offset - NUM_MAIN, 0),
            "previous": offset + NUM_MAIN if len(entries) == NUM_MAIN else None,
            "offset": offset,
        }
        self.render("main.html", extra_context)


class NewEntryHandler(BaseRequestHandler):
    def get_tags_argument(self, name):
        tags = [slugify(tag) for tag in self.request.get(name, "").split(",")]
        tags = set([tag for tag in tags if tag])
        return [db.Category(tag) for tag in tags]
    
    @admin
    def get(self, key=None):
        extra_context = {}
        form = EntryForm()
        if key:
            try:
                entry = db.get(key)
                extra_context["entry"] = entry
                extra_context["tags"] = ", ".join(entry.tags)
                form = EntryForm(instance=entry)
            except db.BadKeyError:
                return self.redirect("/new")
        extra_context["form"] = form
        self.render("edit.html" if key else "new.html", extra_context)

    @admin
    def post(self, key=None):
        extra_context = {}
        form = EntryForm(data=self.request.POST)
        if form.is_valid():
            if key:
                try:
                    entry = db.get(key)
                    extra_context["entry"] = entry
                except db.BadKeyError:
                    return self.raise_error(404)
                entry.title = self.request.get("title")
                entry.body = self.request.get("body")
            else:
                slug = str(slugify(self.request.get("title")))
                if self.get_entry_from_slug(slug=slug):
                    slug += "-" + uuid.uuid4().hex[:4]
                entry = Entry(
                    author=users.get_current_user(),
                    body=self.request.get("body"),
                    title=self.request.get("title"),
                    slug=slug,
                )
            entry.tags = self.get_tags_argument("tags")
            entry.put()
            self.kill_entries_cache(slug=entry.slug if key else None,
                tags=entry.tags)
            if not key:
                self.ping(entry)
            valid = self.is_valid_xhtml(entry)
            return self.redirect(self.entry_link(entry,
                query_args={"invalid": 1} if not valid else {}))
        extra_context["form"] = form
        self.render("edit.html" if key else "new.html", extra_context)


class NotFoundHandler(BaseRequestHandler):
    def head(self):
        self.error(404)

    def get(self):
        self.raise_error(404)


class OldBlogRedirectHandler(BaseRequestHandler):
    def get(self, year, month, day, slug):
        if not OLD_WORDPRESS_BLOG:
           return self.raise_error(404) 
        self.redirect("http://%s/%s/%s/%s/%s/" % 
            (OLD_WORDPRESS_BLOG, year, month, day, slug), permanent=True)


class TagPageHandler(BaseRequestHandler):
    def get(self, tag):
        extra_context = {
            "entries": self.get_tagged_entries(tag),
            "tag": tag,
        }
        self.render("tag.html", extra_context)


class OpenSearchHandler(BaseRequestHandler):
    def get(self):
        self.response.headers["Content-Type"] = "application/xml"
        self.render("opensearch.xml")


class SearchHandler(BaseRequestHandler):
    def get(self):
        self.render("search.html")


application = webapp.WSGIApplication([
    ("/", MainPageHandler),
    ("/archive/?", ArchivePageHandler),
    ("/delete/?", DeleteEntryHandler),
    ("/edit/([\w-]+)/?", NewEntryHandler),
    ("/e/([\w-]+)/?", EntryPageHandler),
    ("/new/?", NewEntryHandler),
    ("/t/([\w-]+)/?", TagPageHandler),
    ("/(\d+)/(\d+)/(\d+)/([\w-]+)/?", OldBlogRedirectHandler),
    ("/feed/?", FeedRedirectHandler),
    ("/opensearch.xml/?", OpenSearchHandler),
    ("/search/?", SearchHandler),
    ("/.*", NotFoundHandler),
], debug=True)

def main():
    logging.getLogger().setLevel(logging.DEBUG)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

########NEW FILE########
