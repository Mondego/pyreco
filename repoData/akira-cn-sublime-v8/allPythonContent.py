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
__version__ = "3.2.0"
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
        elif isinstance(attrs, dict):
            attrs = attrs.items()
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
__FILENAME__ = core
#coding: utf8

import sublime, sublime_plugin
import sys,os,re

MODULE_PATH = os.getcwd()

def cross_platform():
	platform = sublime.platform()
	settings = sublime.load_settings('cross_platform.sublime-settings')
	platform_supported = settings.get(platform)
	if(not platform_supported):
		raise Exception, '''
			Sorry, the v8 engine for this platform are not built yet. 
			Maybe you need to build v8 follow the guide of lib/PyV8/README.md. 
		'''
	lib_path = platform_supported.get('lib_path')
	if(not lib_path in sys.path):
		sys.path.append(os.path.join(MODULE_PATH, lib_path))
		sys.path.append(MODULE_PATH)

cross_platform();

try:
	import PyV8
except Exception, e:
	raise Exception, '''
		Sorry, the v8 engine are not built correctlly.
		Maybe you need to build v8 follow the guide of lib/PyV8/README.md. 
	''' 

from jscontext.commonjs import CommonJS
CommonJS.append(MODULE_PATH)

def package_file(filename):
	return os.path.join(MODULE_PATH, filename)	

JSCONSOLE_VIEW_NAME = 'jsconsole_view'
class JsConsoleCommand(sublime_plugin.WindowCommand):
	def __init__(self, window):
		self.console = window.get_output_panel(JSCONSOLE_VIEW_NAME)
		self.console.set_name(JSCONSOLE_VIEW_NAME)
		self.window = window
		version = sublime.load_settings('package-metadata.json').get('version') or 'dev'
		js_print_m(self.console, "#JavaScript Console (build:" + version + ")")
		JsConsoleCommand.core = JSCore(self.console)
	def run(self):
		if(not 'history' in dir(JsConsoleCommand)):
			JsConsoleCommand.history = []
			JsConsoleCommand.history_index = -1
		
		self.window.run_command("show_panel", {"panel": "output."+JSCONSOLE_VIEW_NAME})
		self.console.set_syntax_file(package_file('Console.tmLanguage'))
		self.window.focus_view(self.console)

def js_print_m(view, msg):
	edit = view.begin_edit()
	view.insert(edit, view.size(), (str(msg) + "\n>>> ").decode('utf-8'))
	view.end_edit(edit)

class JsCommandCommand(sublime_plugin.TextCommand):
	def run(self, edit, module, command, args = []):
		try:
			r = JsConsoleCommand.core.execute('require("'+str(module)+'")')
			apply(getattr(r, command), [self.view, edit]+args)
		except Exception, ex:
			print ex

class JsExecCommand(sublime_plugin.TextCommand):
	def __init__(self, view):
		self.view = view
	def run(self, edit):
		sel = self.view.sel()[0]
		line = self.view.line(sel.begin())
		if(line.end() == int(self.view.size())):
			command = self.view.substr(line)[4:].strip()
			if(command):
				self.view.insert(edit, self.view.size(), '\n')
				JsConsoleCommand.history.append(command) 
				JsConsoleCommand.history_index = len(JsConsoleCommand.history) - 1
				try:
					r = JsConsoleCommand.core.execute(command.encode('utf-8'))
					js_print_m(self.view, r)
				except Exception, ex:
					js_print_m(self.view, ex)
				finally:
					self.view.run_command("goto_line", {"line": self.view.rowcol(self.view.size())[0]+1})
					self.view.sel().clear()
					self.view.sel().add(self.view.size())

class KeyBackspace(sublime_plugin.TextCommand):
	def run(self, edit):
		sel = self.view.sel()[0]
		begin = sel.begin()
		end = sel.end()
		if(self.view.rowcol(begin)[1] > 4 and self.view.line(begin).contains(self.view.line(self.view.size()))):
			if(begin == end):
				self.view.run_command("left_delete")
			else:
				self.view.replace(edit, sel, '')

class JsHistoryBackward(sublime_plugin.TextCommand):
	def run(self, edit):
		sel = self.view.sel()[0]
		line = self.view.line(sel.begin())
		if(line.contains(self.view.line(self.view.size())) and JsConsoleCommand.history_index >= 0):
			command = JsConsoleCommand.history[JsConsoleCommand.history_index]
			self.view.replace(edit, line, ">>> " + command)
			JsConsoleCommand.history_index = JsConsoleCommand.history_index - 1
			self.view.sel().clear()
			self.view.sel().add(self.view.size())

class JsHistoryForward(sublime_plugin.TextCommand):
	def run(self, edit):
		sel = self.view.sel()[0]
		line = self.view.line(sel.begin())
		if(line.contains(self.view.line(self.view.size())) and JsConsoleCommand.history_index + 2 < len(JsConsoleCommand.history)):
			JsConsoleCommand.history_index = JsConsoleCommand.history_index + 1
			command = JsConsoleCommand.history[JsConsoleCommand.history_index + 1]
			self.view.replace(edit, line, ">>> " + command)
			self.view.sel().clear()
			self.view.sel().add(self.view.size())

class EventListener(sublime_plugin.EventListener):
	def on_selection_modified(self, view):
		if(view.name() != JSCONSOLE_VIEW_NAME):
			return
		
		sel = view.sel()[0]
		if(view.line(sel.begin()).contains(view.line(view.size())) and view.rowcol(sel.begin())[1] > 3):
			view.set_read_only(False)
		else:
			view.set_read_only(True)


class JSCore(CommonJS):
	def __init__(self, console):
		self.console = console
		def log(msg):
			print msg
			js_print_m(console, msg)
		self.console.log = log
		CommonJS.__init__(self)
	@property 
	def sublime(self):
		return sublime
	@property 
	def window(self):
		return sublime.active_window()
	@property 
	def view(self):
		return sublime.active_window().active_view()
	def alert(self, msg):
		js_print_m(self.console, msg)
########NEW FILE########
__FILENAME__ = dom
from BeautifulSoup import BeautifulSoup, Tag, NavigableString, Comment
from PyV8 import JSClass, JSArray

def normalizeNode(node = None):
	if('_Node__wrap' in dir(node)):
		return node._Node__wrap
	if(isinstance(node, BeautifulSoup)): #Document
		return Document(node)
	if(isinstance(node, Tag)):	#ElementNode
		return ElementNode(node)
	elif(isinstance(node, NavigableString)): #TextNode
		return TextNode(node)
	elif(isinstance(node, Comment)): #CommentNode
		return CommentNode(node)
	
	return node	

class Document(JSClass):
	def __init__(self, source):
		if(not isinstance(source, BeautifulSoup)):
			source = BeautifulSoup(source)
		self._soup = source
		self.nodeType = 9
	def getElementById(self, id):
		node = self._soup.find(id=id)
		return normalizeNode(node)
	def getElementsByTagName(self, tagName):
		if(tagName == '*'):
			tagName = True
		nodelist = self._soup.findAll(tagName)
		return JSArray([normalizeNode(node) for node in nodelist])
	def getElementsByClassName(self, className):
		nodelist = self._soup.findAll(None, {"class":className})
		return JSArray([normalizeNode(node) for node in nodelist])
	def createElement(self, tagName):
		return normalizeNode(BeautifulSoup(tagName).contents[0])
	@property	
	def body(self):
		return normalizeNode(self._soup.find('body'))

class Node(JSClass, object): #baseclass
	def __init__(self, soup):
		soup.__wrap = self
		self._soup = soup

	@property
	def parentNode(self):
		return normalizeNode(self._soup.parent)

	@property
	def parentElement(self):
		return normalizeNode(self._soup.parent)
	
	@property	
	def ownerDocument(self):
		return normalizeNode(self._soup.findParents()[-1])
	
	@property
	def nextSibling(self):
		return normalizeNode(self._soup.nextSibling)
	
	@property
	def previousSibling(self):
		return normalizeNode(self._soup.previousSibling)

class ElementNode(Node):
	def __init__(self, node):
		self.nodeType = 1
		Node.__init__(self, node)
	def getElementsByTagName(self, tagName):
		if(tagName == '*'):
			tagName = True		
		nodelist = self._soup.findAll(tagName)
		return JSArray([normalizeNode(node) for node in nodelist])
	def getElementsByClassName(self, className):
		nodelist = self._soup.findAll(None, {"class":className})
		return JSArray([normalizeNode(node) for node in nodelist])
	
	@property
	def tagName(self):
		return self._soup.name.upper()
	
	@property
	def nodeName(self):
		return self._soup.name.upper()
	
	@property 
	def childNodes(self):
		node = self._soup
		return JSArray([normalizeNode(node) for node in node.contents])
	
	@property
	def firstChild(self):
		node = self._soup
		if(len(node.contents)):
		 	return normalizeNode(node.contents[0])
	
	def lastChild(self):
		node = self._soup
		if(len(node.contents)):
			return normalizeNode(node.contents[-1])

	@property
	def children(self):
		return JSArray(filter(lambda n: n.nodeType == 1, self.childNodes))

	@property
	def innerHTML(self):
		node = self._soup
		return ''.join([unicode(n).encode('utf-8') for n in node.contents])
	@innerHTML.setter
	def innerHTML(self, html):
		self._soup.contents = BeautifulSoup(html).contents
	
	@property
	def outerHTML(self):
		return unicode(self._soup).encode('utf-8')
		
	@property
	def textContent(self):
		return self._soup.getText()

	@property
	def name(self):
		return self._soup['name']
	@name.setter
	def name(self, value):
		self._soup['name'] = value

	@property
	def id(self):
		return self._soup['id']
	@id.setter
	def id(self, value):
		self._soup['id'] = value

	@property
	def value(self):
		return self._soup['value']
	@value.setter
	def value(self, value):
		self._soup['value'] = value
	
	@property
	def className(self):
		return self._soup['class']
	@className.setter
	def className(self, value):
		self._soup['class'] = value
	
	@property
	def selected(self):
		return self._soup['selected'] == 'selected'
	@selected.setter
	def selected(self, value):
		if(value == True):
			value = "selected"
		self._soup['selected'] = value

	@property
	def checked(self):
		return self._soup['checked'] == 'checked'
	@checked.setter
	def checked(self, value):
		if(value == True):
			value = "checked"
		self._soup['checked'] = value

	@property
	def disabled(self):
		return self._soup['disabled'] == 'disabled'
	@disabled.setter
	def disabled(self, value):
		if(value == True):
			value = "disabled"
		self._soup['disabled'] = value

	@property
	def type(self):
		return self._soup['type']
	
	@property
	def readOnly(self):
		pass

	def appendChild(self, node):
		return self._soup.append(node)
	
	def removeChild(self, node):
		return self._soup.contents.remove(node._soup)

	def getAttribute(self, attr):
		return self._soup[attr]
	
	def setAttribute(self, attr, value):
		self._soup[attr] = value
	
	def removeAttribute(self, attr):
		del self._soup[attr]

class TextNode(Node):
	def __init__(self, node):
		self.nodeType = 3
		self.nodeName = "#text"
		Node.__init__(self, node)
	
	@property
	def nodeValue(self):
		return self._soup.encode('utf-8')

class CommentNode(Node):
	def __init__(self, node):
		self.nodeType = 8
		self.nodeName = "#comment"
		self.nodeValue = node.encode('utf-8')
		Node.__init__(self, node)

	@property
	def nodeValue(self):
		return self._soup.encode('utf-8')
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
__version__ = "3.2.0"
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
        elif isinstance(attrs, dict):
            attrs = attrs.items()
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
__FILENAME__ = browser
import sys, re
import logging
from urllib2 import Request, urlopen, HTTPError
from urlparse import urlparse
from email.utils import formatdate

import PyV8, w3c

import BeautifulSoup

class Navigator(PyV8.JSClass):
    _js_log = logging.getLogger("navigator.base")

    appCodeName = ''
    appName = ''
    appVersion = ''
    cookieEnabled = False
    platform = ''
    javaEnabled = False
    taintEnabled = False

    def __init__(self, win=None, ua='Unknown/Unknown'):
        self._win = win
        self.userAgent = ua

        m = re.match(r'^(\w+)\/(.+)$', ua)

        if(m):
            self.appCodeName = m.group(1)
            self.appVersion = m.group(2)

        if(ua.find("Windows") >= 0):
            self.platform = "Win32"
        elif(ua.find("Mac OS") >= 0):
            self.platform = "MacPPC"
        elif(ua.find("Linux") >= 0):
            self.platform = "Linux"

    @property
    def window(self):
        return self._win

    @property
    def userLanguage(self):
        import locale

        return locale.getdefaultlocale()[0]

    def fetch(self, url):
        self._js_log.debug("fetching HTML from %s", url)
        
        request = Request(url)
        request.add_header('User-Agent', self.userAgent)
        request.add_header('Referer', self._win.url)
        if self._win.doc.cookie:
            request.add_header('Cookie', self._win.doc.cookie)

        response = urlopen(request)

        if response.code != 200:
            self._js_log.warn("fail to fetch HTML from %s, code=%d, msg=%s", url, response.code, response.msg)
            
            raise HTTPError(url, response.code, "fail to fetch HTML", response.info(), 0)

        headers = response.info()
        kwds = { 'referer': self._win.url }

        if headers.has_key('set-cookie'):
            kwds['cookie'] = headers['set-cookie']

        if headers.has_key('last-modified'):
            kwds['lastModified'] = headers['last-modified']

        return response.read(), kwds

class Webkit(Navigator):
    def __init__(self, win=None, ua="Mozilla/5.0 (Windows NT 5.1) AppleWebkit/535.1 (KHTML, like Gecko) Chrome/14.0.825.0 Safari/535.1"):
        super(Webkit, self).__init__(win, ua)
        self.appName = "Netscape"
        self.cookieEnabled = True

class Gecko(Navigator):
    def __init__(self, win=None, ua="Mozilla/5.0 (Windows NT 5.1; rv:8.0.1) Gecko/20100101 Firefox/8.0.1"):
        super(Gecko, self).__init__(win, ua)
        self.appName = "Netscape"
        self.cookieEnabled = True

class Trident(Navigator):
    def __init__(self, win=None, ua="Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0)"):
        super(Trident, self).__init__(win, ua)
        self.appName = "Microsoft Internet Explorer"
        self.cookieEnabled = True

def matchNavigator(ua):
    if(ua.find("Chrome")):
        return Webkit(ua=ua)
    elif(ua.find("Gecko")):
        return Gecko(ua=ua)
    elif(ua.find("MSIE")):
        return Trident(ua=ua)
    else:
        return Trident()

class Location(PyV8.JSClass):
    def __init__(self, win):
        self.win = win

    @property
    def parts(self):
        return urlparse(self.win.url)

    @property
    def href(self):
        return self.win.url

    @href.setter
    def href(self, url):
        self.win.open(url)

    @property
    def protocol(self):
        return self.parts.scheme

    @property
    def host(self):
        return self.parts.netloc

    @property
    def hostname(self):
        return self.parts.hostname

    @property
    def port(self):
        return self.parts.port

    @property
    def pathname(self):
        return self.parts.path

    @property
    def search(self):
        return self.parts.query

    @property
    def hash(self):
        return self.parts.fragment

    def assign(self, url):
        """Loads a new HTML document."""
        self.win.open(url)

    def reload(self):
        """Reloads the current page."""
        self.win.open(self.win.url)

    def replace(self, url):
        """Replaces the current document by loading another document at the specified URL."""
        self.win.open(url)

class Screen(PyV8.JSClass):
    def __init__(self, width, height, depth=32):
        self._width = width
        self._height = height
        self._depth = depth

    @property
    def availWidth(self):
        return self._width

    @property
    def availHeight(self):
        return self._height

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def colorDepth(self):
        return self._depth

    @property
    def pixelDepth(self):
        return self._depth

class History(PyV8.JSClass):
    def __init__(self, win):
        self._win = win
        self.urls = []
        self.pos = None

    @property
    def window(self):
        return self._win

    @property
    def length(self):
        """the number of URLs in the history list"""
        return len(self.urls)

    def back(self):
        """Loads the previous URL in the history list"""
        return self.go(-1)

    def forward(self):
        """Loads the next URL in the history list"""
        return self.go(1)

    def go(self, num_or_url):
        """Loads a specific URL from the history list"""
        try:
            off = int(num_or_url)

            self.pos += off
            self.pos = min(max(0, self.pos), len(self.urls)-1)

            self._win.open(self.urls[self.pos])
        except ValueError:
            self._win.open(num_or_url)

    def update(self, url, replace=False):
        if self.pos is None:
            self.urls.append(url)
            self.pos = 0
        elif replace:
            self.urls[self.pos] = url
        elif self.urls[self.pos] != url:
            self.urls = self.urls[:self.pos+1]
            self.urls.append(url)
            self.pos += 1

class HtmlWindow(PyV8.JSClass):
    _js_log = logging.getLogger("html.window")

    class Timer(object):
        def __init__(self, code, repeat, lang='JavaScript'):
            self.code = code
            self.repeat = repeat
            self.lang = lang

    _js_timers = []

    def __init__(self, url, dom_or_doc, navigator_or_class=Trident, name="", target='_blank',
                 parent=None, opener=None, replace=False, screen=None, width=800, height=600, left=0, top=0, **kwds):
        self.url = url
        self.doc = w3c.getDOMImplementation(dom_or_doc, **kwds) if isinstance(dom_or_doc, BeautifulSoup.BeautifulSoup) else dom_or_doc
        self.doc.window = self

        self._navigator = navigator_or_class(self) if type(navigator_or_class) == type else navigator_or_class
        self._location = Location(self)
        self._history = History(self)

        self._history.update(url, replace)

        self._target = target
        self._parent = parent
        self._opener = opener
        self._screen = screen or Screen(width, height, 32)
        self._closed = False

        self.name = name
        self.defaultStatus = ""
        self.status = ""
        self._left = left
        self._top = top
        self.innerWidth = width
        self.innerHeight = height
        self.outerWidth = width
        self.outerHeight = height

    @property
    def closed(self):
        """whether a window has been closed or not"""
        return self._closed

    def close(self):
        """Closes the current window"""
        self._closed = True

    @property
    def window(self):
        return self

    @property
    def document(self):
        return self.doc

    def _findAll(self, tags):
        return self.doc.doc.findAll(tags, recursive=True)

    @property
    def frames(self):
        """an array of all the frames (including iframes) in the current window"""
        return w3c.HTMLCollection(self.doc, [self.doc.createHTMLElement(self.doc, f) for f in self._findAll(['frame', 'iframe'])])

    @property
    def length(self):
        """the number of frames (including iframes) in a window"""
        return len(self._findAll(['frame', 'iframe']))

    @property
    def history(self):
        """the History object for the window"""
        return self._history

    @property
    def location(self):
        """the Location object for the window"""
        return self._location

    @property
    def navigator(self):
        """the Navigator object for the window"""
        return self._navigator

    @property
    def opener(self):
        """a reference to the window that created the window"""
        return self._opener

    @property
    def pageXOffset(self):
        return 0

    @property
    def pageYOffset(self):
        return 0

    @property
    def parent(self):
        return self._parent

    @property
    def screen(self):
        return self._screen

    @property
    def screenLeft(self):
        return self._left

    @property
    def screenTop(self):
        return self._top

    @property
    def screenX(self):
        return self._left

    @property
    def screenY(self):
        return self._top

    @property
    def self(self):
        return self

    @property
    def top(self):
        return self

    def alert(self, msg):
        """Displays an alert box with a message and an OK button"""
        print "ALERT: ", str(msg).decode('utf-8')

    def confirm(self, msg):
        """Displays a dialog box with a message and an OK and a Cancel button"""
        ret = raw_input("CONFIRM: %s [Y/n] " % msg)

        return ret in ['', 'y', 'Y', 't', 'T']

    def focus(self):
        """Sets focus to the current window"""
        pass

    def blur(self):
        """Removes focus from the current window"""
        pass

    def moveBy(self, x, y):
        """Moves a window relative to its current position"""
        pass

    def moveTo(self, x, y):
        """Moves a window to the specified position"""
        pass

    def resizeBy(self, w, h):
        """Resizes the window by the specified pixels"""
        pass

    def resizeTo(self, w, h):
        """Resizes the window to the specified width and height"""
        pass

    def scrollBy(self, xnum, ynum):
        """Scrolls the content by the specified number of pixels"""
        pass

    def scrollTo(self, xpos, ypos):
        """Scrolls the content to the specified coordinates"""
        pass

    def setTimeout(self, code, interval, lang="JavaScript"):
        timer = HtmlWindow.Timer(code, False, lang)
        self._js_timers.append((interval, timer))

        return len(self._js_timers)-1

    def clearTimeout(self, idx):
        self._js_timers[idx] = None

    def setInterval(self, code, interval, lang="JavaScript"):
        timer = HtmlWindow.Timer(code, True, lang)
        self._js_timers.append((interval, timer))

        return len(self._js_timers)-1

    def clearInterval(self, idx):
        self._js_timers[idx] = None

    def createPopup(self):
        raise NotImplementedError()

    def open(self, url=None, name='_blank', specs='', replace=False):
        self._js_log.info("window.open(url='%s', name='%s', specs='%s')", url, name, specs)
        
        if url:
            html, kwds = self._navigator.fetch(url)
        else:
            url = 'about:blank'
            html = ''
            kwds = {}

        dom = BeautifulSoup.BeautifulSoup(html)

        for spec in specs.split(','):
            spec = [s.strip() for s in spec.split('=')]

            if len(spec) == 2:
                if spec[0] in ['width', 'height', 'left', 'top']:
                    kwds[spec[0]] = int(spec[1])

        if name in ['_blank', '_parent', '_self', '_top']:
            kwds['target'] = name
            name = ''
        else:
            kwds['target'] = '_blank'

        return HtmlWindow(url, dom, self._navigator, name, parent=self, opener=self, replace=replace, **kwds)

    @property
    def context(self):
        if not hasattr(self, "_context"):
            self._context = PyV8.JSContext(self)

        return self._context

    def evalScript(self, script, tag=None):
        if isinstance(script, unicode):
            script = script.encode('utf-8')

        if tag:
            self.doc.current = tag
        else:
            body = self.doc.body

            self.doc.current = body.tag.contents[-1] if body else self.doc.doc.contents[-1]

        self._js_log.debug("executing script: %s", script)

        with self.context as ctxt:
            ctxt.eval(script)

    def fireOnloadEvents(self):
        for tag in self._findAll('script'):
            self.evalScript(tag.string, tag=tag)

        body = self.doc.body

        if body and body.tag.has_key('onload'):
            self.evalScript(body.tag['onload'], tag=body.tag.contents[-1])

        if hasattr(self, 'onload'):
            self.evalScript(self.onload)

    def fireExpiredTimer(self):
        pass

    def Image(self):
        return self.doc.createElement('img')

import unittest

TEST_URL = 'http://localhost:8080/path?query=key#frag'
TEST_HTML = """
<html>
<head>
    <title></title>
</head>
<body onload='load()'>
    <frame src="#"/>
    <iframe src="#"/>
    <script>
    function load()
    {
        alert('onload');
    }
    document.write("<p id='hello'>world</p>");
    </script>
</body>
</html>
"""

class HtmlWindowTest(unittest.TestCase):
    def setUp(self):
        self.doc = w3c.parseString(TEST_HTML)
        self.win = HtmlWindow(TEST_URL, self.doc)

    def testWindow(self):
        self.assertEquals(self.doc, self.win.document)
        self.assertEquals(self.win, self.win.window)
        self.assertEquals(self.win, self.win.self)

        self.assertFalse(self.win.closed)
        self.win.close()
        self.assert_(self.win.closed)

        self.assertEquals(2, self.win.frames.length)
        self.assertEquals(2, self.win.length)
        
        self.assertEquals(1, self.win.history.length)

        loc = self.win.location

        self.assert_(loc)
        self.assertEquals("frag", loc.hash)
        self.assertEquals("localhost:8080", loc.host)
        self.assertEquals("localhost", loc.hostname)
        self.assertEquals(TEST_URL, loc.href)
        self.assertEquals("/path", loc.pathname)
        self.assertEquals(8080, loc.port)
        self.assertEquals("http", loc.protocol)
        self.assertEquals("query=key", loc.search)

    def testOpen(self):
        url = 'http://www.google.com'
        win = self.win.open(url, specs="width=640, height=480")
        self.assertEquals(url, win.url)

        self.assert_(win.document)
        self.assertEquals(url, win.document.URL)
        self.assertEquals('www.google.com', win.document.domain)
        self.assertEquals(640, win.innerWidth)
        self.assertEquals(480, win.innerHeight)

    def testScript(self):
        self.win.fireOnloadEvents()

        tag = self.doc.getElementById('hello')

        self.assertEquals(u'P', tag.nodeName)

    def testTimer(self):
        pass

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG if "-v" in sys.argv else logging.WARN,
                        format='%(asctime)s %(levelname)s %(message)s')

    unittest.main()
########NEW FILE########
__FILENAME__ = commonjs
import os, re, platform
from PyV8 import JSContext, JSError

from logger import logger

class CommonJS():
	_js_path = [os.path.dirname(__file__), os.path.join(os.path.dirname(__file__),'core')]
	_js_logger = logger().instance()

	def __init__(self):
		self._js_threadlock = False
		self._js_ctx = JSContext(self)
		self._js_modules = {}
		self._loaded_modules = {}

		for jsroot in CommonJS._js_path:
			for (root, dirs, files) in os.walk(jsroot):
				#print files
				for _file in files:
					m = re.compile('(.*)\.js$').match(_file)
					relpath = os.path.relpath(root, jsroot)
					namespace = re.sub(r'^\.', '', relpath)
					namespace = re.sub(r'^\\', '/', namespace)
					if(namespace):
						namespace = namespace + '/'
					if(m):
						self._js_modules.update({namespace + m.group(1) : os.path.join(root,_file)})

		self.execute("var exports;");				
	
	@staticmethod
	def append(path):
		if(path not in CommonJS._js_path):
			CommonJS._js_path.append(path)

	def require(self, module):
		if(not self._js_modules.has_key(module)):
			raise Exception, "unknown module `" + module + "`"
		path = self._js_modules[module]

		if(not self._loaded_modules.has_key(path)):
			self._js_logger.info("loading module <%s>...", module)
			code = file(path).read()
			try:
				code = code.decode('utf-8')
				if(platform.system() == 'Windows'):
					code = code.encode('utf-8')
				self._js_ctx.eval(code)
			except JSError, ex:
				self._js_logger.error(ex)
				self._js_logger.debug(ex.stackTrace)
				raise Exception, ex
			self._loaded_modules[path] = self._js_ctx.locals.exports
			return self._loaded_modules[path]
		else:
			return self._loaded_modules[path]

	def execute(self, code, args = []):
		self._js_ctx.enter()
		
		# use lock while jscode executing to make mutil-thread work
		while self._js_threadlock: 
			pass
		self._js_threadlock = True
		try:
			if(isinstance(code, basestring)):
				code = code.decode('utf-8')
				if(platform.system() == 'Windows'):
					code = code.encode('utf-8')
				r = self._js_ctx.eval(code)
			else:
				r = apply(code, args)
			return r
		except JSError, ex:
			self._js_logger.error(ex)
			self._js_logger.debug(ex.stackTrace)
			raise Exception, ex
		finally:
			self._js_threadlock = False
			self._js_ctx.leave()
########NEW FILE########
__FILENAME__ = dom
from BeautifulSoup import BeautifulSoup, Tag, NavigableString, Comment
from PyV8 import JSClass, JSArray

def normalizeNode(node = None):
	if('_Node__wrap' in dir(node)):
		return node._Node__wrap
	if(isinstance(node, BeautifulSoup)): #Document
		return Document(node)
	if(isinstance(node, Tag)):	#ElementNode
		return ElementNode(node)
	elif(isinstance(node, NavigableString)): #TextNode
		return TextNode(node)
	elif(isinstance(node, Comment)): #CommentNode
		return CommentNode(node)
	
	return node	

class DomDocument(JSClass):
	def __init__(self, source):
		if(not isinstance(source, BeautifulSoup)):
			source = BeautifulSoup(source)
		self._soup = source
		self.nodeType = 9
	def getElementById(self, id):
		node = self._soup.find(id=id)
		return normalizeNode(node)
	def getElementsByTagName(self, tagName):
		if(tagName == '*'):
			tagName = True
		nodelist = self._soup.findAll(tagName)
		return JSArray([normalizeNode(node) for node in nodelist])
	def getElementsByClassName(self, className):
		nodelist = self._soup.findAll(None, {"class":className})
		return JSArray([normalizeNode(node) for node in nodelist])
	def createElement(self, tagName):
		return normalizeNode(BeautifulSoup(tagName).contents[0])
	@property	
	def body(self):
		return normalizeNode(self._soup.find('body'))

class Node(JSClass, object): #baseclass
	def __init__(self, soup):
		soup.__wrap = self
		self._soup = soup

	@property
	def parentNode(self):
		return normalizeNode(self._soup.parent)

	@property
	def parentElement(self):
		return normalizeNode(self._soup.parent)
	
	@property	
	def ownerDocument(self):
		return normalizeNode(self._soup.findParents()[-1])
	
	@property
	def nextSibling(self):
		return normalizeNode(self._soup.nextSibling)
	
	@property
	def previousSibling(self):
		return normalizeNode(self._soup.previousSibling)

class ElementNode(Node):
	def __init__(self, node):
		self.nodeType = 1
		Node.__init__(self, node)
	def getElementsByTagName(self, tagName):
		if(tagName == '*'):
			tagName = True		
		nodelist = self._soup.findAll(tagName)
		return JSArray([normalizeNode(node) for node in nodelist])
	def getElementsByClassName(self, className):
		nodelist = self._soup.findAll(None, {"class":className})
		return JSArray([normalizeNode(node) for node in nodelist])
	
	@property
	def tagName(self):
		return self._soup.name.upper()
	
	@property
	def nodeName(self):
		return self._soup.name.upper()
	
	@property 
	def childNodes(self):
		node = self._soup
		return JSArray([normalizeNode(node) for node in node.contents])
	
	@property
	def firstChild(self):
		node = self._soup
		if(len(node.contents)):
		 	return normalizeNode(node.contents[0])
	
	def lastChild(self):
		node = self._soup
		if(len(node.contents)):
			return normalizeNode(node.contents[-1])

	@property
	def children(self):
		return JSArray(filter(lambda n: n.nodeType == 1, self.childNodes))

	@property
	def innerHTML(self):
		node = self._soup
		return ''.join([unicode(n).encode('utf-8') for n in node.contents])
	@innerHTML.setter
	def innerHTML(self, html):
		self._soup.contents = BeautifulSoup(html).contents
	
	@property
	def outerHTML(self):
		return unicode(self._soup).encode('utf-8')
		
	@property
	def textContent(self):
		return self._soup.getText()

	@property
	def name(self):
		return self._soup['name']
	@name.setter
	def name(self, value):
		self._soup['name'] = value

	@property
	def id(self):
		return self._soup['id']
	@id.setter
	def id(self, value):
		self._soup['id'] = value

	@property
	def value(self):
		return self._soup['value']
	@value.setter
	def value(self, value):
		self._soup['value'] = value
	
	@property
	def className(self):
		return self._soup['class']
	@className.setter
	def className(self, value):
		self._soup['class'] = value
	
	@property
	def selected(self):
		return self._soup['selected'] == 'selected'
	@selected.setter
	def selected(self, value):
		if(value == True):
			value = "selected"
		self._soup['selected'] = value

	@property
	def checked(self):
		return self._soup['checked'] == 'checked'
	@checked.setter
	def checked(self, value):
		if(value == True):
			value = "checked"
		self._soup['checked'] = value

	@property
	def disabled(self):
		return self._soup['disabled'] == 'disabled'
	@disabled.setter
	def disabled(self, value):
		if(value == True):
			value = "disabled"
		self._soup['disabled'] = value

	@property
	def type(self):
		return self._soup['type']
	
	@property
	def readOnly(self):
		pass

	def appendChild(self, node):
		return self._soup.append(node)
	
	def removeChild(self, node):
		return self._soup.contents.remove(node._soup)

	def getAttribute(self, attr):
		return self._soup[attr]
	
	def setAttribute(self, attr, value):
		self._soup[attr] = value
	
	def removeAttribute(self, attr):
		del self._soup[attr]

class TextNode(Node):
	def __init__(self, node):
		self.nodeType = 3
		self.nodeName = "#text"
		Node.__init__(self, node)
	
	@property
	def nodeValue(self):
		return self._soup.encode('utf-8')

class CommentNode(Node):
	def __init__(self, node):
		self.nodeType = 8
		self.nodeName = "#comment"
		self.nodeValue = node.encode('utf-8')
		Node.__init__(self, node)

	@property
	def nodeValue(self):
		return self._soup.encode('utf-8')
########NEW FILE########
__FILENAME__ = logger
# coding=utf-8

import logging
import logging.handlers
import datetime
import os

logging.basicConfig()

class logger():
    _loggers = {}

    def __init__(self, name = 'default'):
        self.name = name
        self.logger = logger._loggers.get(name)

        if(not self.logger):
            self.logger = logging.getLogger(self.name)
            self.logger.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(thread)d %(asctime)s %(levelname)s %(message)s')
            filehandler = logging.handlers.TimedRotatingFileHandler(
                os.path.join(os.path.dirname(__file__), "logs","log"), 'D', 1, 7)
            filehandler.suffix = "%Y-%m-%d"
            filehandler.setFormatter(formatter)
            self.logger.addHandler(filehandler)
            logger._loggers[name] = self.logger

    def instance(self):
        return self.logger
########NEW FILE########
__FILENAME__ = node
#!/usr/bin/env python
#
# Purely event-based I/O for V8 javascript w/ PyV8.
# http://tinyclouds.org/node/
#
import sys, os.path, json

import logging

import threading
import socket, SocketServer, BaseHTTPServer
from urlparse import urlparse

import PyV8

__author__ = "flier.lu@gmail.com"
__version__ = "%%prog 0.1 (Google v8 engine v%s)" % PyV8.JSEngine.version

class File(PyV8.JSClass):
    logger = logging.getLogger('file')
    
    def __init__(self, file=None):
        self.file = file
        
    def open(self, path, mode):        
        self.file = open(path, mode)
        
    def read(self, length, position=None):
        if position:
            self.file.seek(position)
            
        return self.file.read(length)
        
    def write(self, data, position=None):
        if position:
            self.file.seek(position)
            
        return self.file.write(data)
        
    def close(self):
        self.file.close()

class FileSystem(PyV8.JSClass):
    logger = logging.getLogger('filesystem')
    
    def File(self, options={}):
        return File()
    
class ServerRequest(PyV8.JSClass, BaseHTTPServer.BaseHTTPRequestHandler):
    logger = logging.getLogger('web.request')
    
    def __init__(self, request, client_address, server):
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, request, client_address, server)
        
    @property
    def uri(self):
        if hasattr(self, '__uri'):
            return self.__uri
        
        o = urlparse(self.path)
        
        params = dict([tuple(v.split('=')) for v in o.query.split('&')]) if o.query else {}
        
        self.__uri = {
            'host' : o.hostname,
            'port' : o.port,
            'user' : o.username,
            'password' : o.password,            
            'path' : o.path,
            'file' : os.path.basename(o.path),
            'directory' : os.path.dirname(o.path),
            'params' : params,
        }

        return self.__uri
    
    @property
    def method(self):
        return self.command
        
    def handle_request(self):
        self.logger.info("handle request from %s:%d" % self.client_address)
        
        self.finished = threading.Event()
        
        try:
            self.server.server.listener(self, ServerResponse(self.server.server, self))
        except PyV8.JSError, e:
            self.logger.warn("fail to execute callback script, %s", str(e))
        except Exception, e:
            self.logger.warn("unknown error occured, %s", str(e))
            
        self.finished.wait()
            
    do_GET = do_POST = do_HEAD = handle_request    
        
class ServerResponse(PyV8.JSClass):
    logger = logging.getLogger('web.response')
    
    def __init__(self, server, handler):
        self.server = server
        self.handler = handler
        
    def sendHeader(self, statusCode, headers):
        self.handler.send_response(statusCode)
        
        for i in range(len(headers)):
            self.handler.send_header(headers[i][0], headers[i][1])
            
        self.handler.end_headers()
    
    def sendBody(self, chunk, encoding='ascii'):        
        self.handler.wfile.write(chunk)
    
    def finish(self):
        self.handler.wfile.close()
        self.handler.finished.set()
    
class WebServer(PyV8.JSClass):
    logger = logging.getLogger('web.server')
    
    __alive = []
    __terminated = False
    
    def __init__(self, listener, options):
        self.listener = listener
        self.options = options
        
    def listen(self, port, hostname=None):        
        self.server = SocketServer.ThreadingTCPServer((hostname or 'localhost', port), ServerRequest)
        self.server.server = self
        
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.setName('WebServer')
        self.thread.setDaemon(True)        
        self.thread.start()
        
        WebServer.__alive.append(self.thread)
        
        self.logger.info("start web server at %s:%d" % self.server.server_address)
    
    def close(self):
        self.server.shutdown()
        
        self.logger.info("shutdown web server at %s:%d" % self.server.server_address)
        
    @staticmethod
    def run():
        while not WebServer.__terminated:
            if WebServer.__alive:
                for thread in WebServer.__alive:
                    if thread.isAlive():
                        thread.join(0.5)
                        
                    if WebServer.__terminated:
                        break
                    
                    if not thread.isAlive():
                        WebServer.__alive.remove(thread)
                        break
                
    @staticmethod
    def stop():
        WebServer.__terminated = True

class Http(PyV8.JSClass):
    logger = logging.getLogger('http')
    
    def createServer(self, listener, options=None):
        return WebServer(listener, options)
    
class Tcp(PyV8.JSClass):
    logger = logging.getLogger('tcp')

class Dns(PyV8.JSClass):
    logger = logging.getLogger('dns')

class Node(PyV8.JSClass):
    logger = logging.getLogger('node')
    
    def __init__(self):
        self.stdout = File(sys.stdout)
        self.stderr = File(sys.stderr)
        self.stdin = File(sys.stdin)
        self.ARGV = sys.argv
        
        self.fs = FileSystem()
        self.http = Http()
        self.tcp = Tcp()
        self.dns = Dns()
        
    def debug(self, string):
        self.stdout.write(string)
        
    def exit(self, code):
        sys.exit(code)
        
class Timer(object):
    logger = logging.getLogger('timer')
    
    __timeout_id = 0
    __timeout_timers = {}
    
    __interval_id = 0
    __interval_timers = {}    
        
    def setTimeout(self, callback, delay):
        timer = threading.Timer(delay / 1000.0, callback)        
        
        self.__timeout_id += 1
        self.__timeout_timers[self.__timeout_id] = timer
        
        timer.start()
        
        self.logger.info("add #%d timer will call %s after %sms", self.__timeout_id, callback, delay)
    
    def clearTimeout(self, timeoutId):
        if self.__timeout_timers.has_key(timeoutId):
            self.__timeout_timers[timeoutId].cancel()
            
            del self.__timeout_timers[timeoutId]
            
            self.logger.info("cancel #%d timer", timeoutId)
        else:
            self.logger.warn("#%d timer was not found", timeoutId)
    
    def setInterval(self, callback, delay):
        def handler():
            callback()
            
            self.setInterval(self, callback, delay)
            
        timer = threading.Timer(delay / 1000.0, handler)
        
        self.__interval_id += 1
        self.__interval_timers[self.__interval_id] = timer
        
        timer.start()
        
        self.logger.info("add #%d interval timer will call %s every %sms", self.__interval_id, callback, delay)
    
    def clearInterval(intervalId):
        if self.__interval_timers.has_key(intervalId):
            self.__interval_timers[intervalId].cancel()
            
            del self.__interval_timers[intervalId]
            
            self.logger.info("cancel #%d interval timer", intervalId)
        else:
            self.logger.warn("#%d interval timer was not found", intervalId)
        
class Env(PyV8.JSClass, Timer):
    logger = logging.getLogger('env')
    
    def __init__(self):
        self.node = Node()
        
    def puts(self, str):
        self.node.stdout.write(str + '\n')    
        
    def p(self, object):
        self.stdout.write(json.dumps(object))        

class Loader(object):
    logger = logging.getLogger('loader')
    
    def __init__(self):
        self.scripts = []        
        
    def addScript(self, script, filename):
        self.scripts.append((script, filename))
    
    def run(self):
        env = Env()
        
        with PyV8.JSContext(env) as ctxt:
            for filename in self.args:
                try:
                    with open(filename, 'r') as f:
                        ctxt.locals.__filename = filename
                        ctxt.eval(f.read())
                except IOError, e:
                    self.logger.warn("fail to read script from file '%s', %s", filename, str(e))
                except PyV8.JSError, e:
                    self.logger.warn("fail to execute script from file '%s', %s", filename, str(e))
                    
            try:
                WebServer.run()
            except KeyboardInterrupt:
                WebServer.stop()
                    
    def parseCmdline(self):
        from optparse import OptionParser
        
        parser = OptionParser(usage="Usage: %prog [options] <scripts>", version=__version__)
        
        parser.add_option("-q", "--quiet", action="store_const",
                          const=logging.FATAL, dest="logLevel", default=logging.WARN)
        parser.add_option("-v", "--verbose", action="store_const",
                          const=logging.INFO, dest="logLevel")
        parser.add_option("-d", "--debug", action="store_const",
                          const=logging.DEBUG, dest="logLevel")
        parser.add_option("--log-format", dest="logFormat",
                          default="%(asctime)s %(levelname)s %(name)s %(message)s")
        parser.add_option("--log-file", dest="logFile")
        
        self.opts, self.args = parser.parse_args()
        
        logging.basicConfig(level=self.opts.logLevel,
                            format=self.opts.logFormat,
                            filename=self.opts.logFile or 'node.log')        
        
        if len(self.args) == 0:
            parser.error("missing script files")
        
        return True

if __name__ == '__main__':
    loader = Loader()
    
    if loader.parseCmdline():    
        loader.run()
########NEW FILE########
__FILENAME__ = runtime
#JavaScript HTML Context for PyV8

from PyV8 import JSClass
from logger import logger
import re, threading, hashlib

import urllib,urllib2

from w3c import parseString, Document, HTMLElement
from commonjs import CommonJS

import browser

from StringIO import StringIO
import gzip

class JSR(CommonJS, browser.HtmlWindow):
	def __init__(self, url_or_dom, charset=None, headers={}, body={}, timeout=2):
		urllib2.socket.setdefaulttimeout(timeout)
		jsonp = False

		if(isinstance(url_or_dom, Document)):
			url = "localhost:document"
			dom = url_or_dom

		elif(url_or_dom.startswith('<')):
			url = "localhost:string"
			dom = parseString(url_or_dom)

		else: #url
			url = url_or_dom
			if(not re.match(r'\w+\:\/\/', url)):
				url = "http://" + url

			request = urllib2.Request(url, urllib.urlencode(body), headers=headers) 
			response = urllib2.urlopen(url)
			
			contentType = response.headers.get('Content-Type')

			if(contentType):
				#print contentType
				t = re.search(r'x-javascript|json', contentType)
				if(t):
					jsonp = True
				m = re.match(r'^.*;\s*charset=(.*)$', contentType)
				if(m):
					charset = m.group(1) 
				#print charset

			if(not charset):
				charset = 'utf-8' #default charset
				# guess charset from httpheader

			html = response.read()
			encoding = response.headers.get('Content-Encoding')

			if(encoding and encoding == 'gzip'):
			    buf = StringIO(html)
			    f = gzip.GzipFile(fileobj=buf)
			    html = f.read()	
			    			
			self.__html__ = html
			html = unicode(html, encoding=charset, errors='ignore')
			dom = parseString(html)	

		navigator = browser.matchNavigator(headers.get('User-Agent') or '')
			
		browser.HtmlWindow.__init__(self, url, dom, navigator)
		CommonJS.__init__(self)
		
		self.console = JSConsole(self._js_logger)
		
		for module in "base, array.h, function.h, helper.h, object.h, string.h, date.h, custevent, selector, dom_retouch".split(","):
			self.execute(self.require, [module.strip()])
		
		if(jsonp):
			code = "window.data=" + html.encode('utf-8')
			self.execute(code)
			#print code

		self._js_logger.info('JavaScript runtime ready.')

	_js_timer_map = {}

	def _js_execTimer(self, id, callback, delay, repeat = False):
		code = '(function f(){ _js_timers[' + str(id) + '][1].code();'
		if(repeat):
			code = code + '_js_execTimer(' + str(id) + ', f, ' + str(delay) + ', true);'
		code = code + '})();'

		#thread locking
		self._js_timer_map[id] = threading.Timer(delay / 1000.0, lambda: self.execute(code))
		self._js_timer_map[id].start()

	def setTimeout(self, callback, delay):
		timerId = super(JSR, self).setTimeout(callback, delay)
		self._js_execTimer(timerId, callback, delay, False)
		return timerId

	def clearTimeout(self, timerId):
		if(timerId in self._js_timer_map):
			self._js_timer_map[timerId].cancel()
			self._js_timer_map[timerId] = None
			super(JSR, self).clearTimeout(timerId)

	def setInterval(self, callback, delay):
		timerId = super(JSR, self).setInterval(callback, delay)
		self._js_execTimer(timerId, callback, delay, True)
		return timerId		
	
	def clearInterval(self, timerId):
		if(timerId in self._js_timer_map):
			self._js_timer_map[timerId].cancel()
			self._js_timer_map[timerId] = None
			super(JSR, self).clearTimeout(timerId)

	def md5(self, str):
		return hashlib.md5(str).hexdigest()

class JSConsole(JSClass):
	def __init__(self, logger):
		self._js_logger = logger
	def log(self, msg):
		self._js_logger.info(str(msg).decode('utf-8'))
########NEW FILE########
__FILENAME__ = w3c
#!/usr/bin/env python
from __future__ import with_statement

import sys, re, string

from urlparse import urlparse

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import logging

import BeautifulSoup

import PyV8

class abstractmethod(object):
    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwds):
        raise NotImplementedError("method %s is abstract." % self.func.func_name)

class DOMException(RuntimeError, PyV8.JSClass):
    def __init__(self, code):
        self.code = code
        
    INDEX_SIZE_ERR                 = 1  # If index or size is negative, or greater than the allowed value
    DOMSTRING_SIZE_ERR             = 2  # If the specified range of text does not fit into a DOMString
    HIERARCHY_REQUEST_ERR          = 3  # If any node is inserted somewhere it doesn't belong
    WRONG_DOCUMENT_ERR             = 4  # If a node is used in a different document than the one that created it (that doesn't support it)
    INVALID_CHARACTER_ERR          = 5  # If an invalid or illegal character is specified, such as in a name. 
    NO_DATA_ALLOWED_ERR            = 6  # If data is specified for a node which does not support data
    NO_MODIFICATION_ALLOWED_ERR    = 7  # If an attempt is made to modify an object where modifications are not allowed
    NOT_FOUND_ERR                  = 8  # If an attempt is made to reference a node in a context where it does not exist
    NOT_SUPPORTED_ERR              = 9  # If the implementation does not support the type of object requested
    INUSE_ATTRIBUTE_ERR            = 10 # If an attempt is made to add an attribute that is already in use elsewhere    
    
class Node(PyV8.JSClass):
    # NodeType
    ELEMENT_NODE                   = 1
    ATTRIBUTE_NODE                 = 2
    TEXT_NODE                      = 3
    CDATA_SECTION_NODE             = 4
    ENTITY_REFERENCE_NODE          = 5
    ENTITY_NODE                    = 6
    PROCESSING_INSTRUCTION_NODE    = 7
    COMMENT_NODE                   = 8
    DOCUMENT_NODE                  = 9
    DOCUMENT_TYPE_NODE             = 10
    DOCUMENT_FRAGMENT_NODE         = 11
    NOTATION_NODE                  = 12
    
    def __init__(self, doc):
        self.doc = doc        
        
    def __repr__(self):
        return "<Node %s at 0x%08X>" % (self.nodeName, id(self))
                
    def __eq__(self, other):
        return hasattr(other, "doc") and self.doc == other.doc
        
    def __ne__(self, other):
        return not self.__eq__(other)
    
    @property
    @abstractmethod
    def nodeType(self):
        pass
    
    @property
    @abstractmethod
    def nodeName(self):
        pass
    
    @abstractmethod
    def getNodeValue(self):
        return None
    
    @abstractmethod
    def setNodeValue(self, value):
        raise DOMException(DOMException.NO_MODIFICATION_ALLOWED_ERR)
    
    nodeValue = property(getNodeValue, setNodeValue)
    
    @property
    def attributes(self):
        return None
    
    @property
    def childNodes(self):
        return NodeList(self.doc, [])
        
    @property
    def firstChild(self):
        return None
            
    @property
    def lastChild(self):
        return None
            
    @property
    def nextSibling(self):
        return None
            
    @property
    def previousSibling(self):
        return None
            
    @property
    def parentNode(self):
        return None
    
    @property
    def ownerDocument(self):
        return self.doc
    
    def insertBefore(self, newChild, refChild):
        raise DOMException(DOMException.HIERARCHY_REQUEST_ERR)

    def insertAfter(self, newChild, refChild):
        raise DOMException(DOMException.HIERARCHY_REQUEST_ERR)

    def replaceChild(self, newChild, oldChild):
        raise DOMException(DOMException.HIERARCHY_REQUEST_ERR)
    
    def removeChild(self, oldChild):
        raise DOMException(DOMException.NOT_FOUND_ERR)
    
    def appendChild(self, newChild):
        raise DOMException(DOMException.HIERARCHY_REQUEST_ERR)
    
    def hasChildNodes(self):
        return False
    
    @abstractmethod
    def cloneNode(self, deep):
        pass
    
    @staticmethod
    def wrap(doc, obj):
        if obj is None:
            return None
        
        if type(obj) == BeautifulSoup.CData:
            return CDATASection(doc, obj)
        
        if type(obj) == BeautifulSoup.NavigableString:
            return Text(doc, obj)        
        
        return DOMImplementation.createHTMLElement(doc, obj)
    
class NodeList(PyV8.JSClass):
    def __init__(self, doc, nodes):
        self.doc = doc
        self.nodes = nodes
        
    def __len__(self):
        return self.length
        
    def __getitem__(self, key):
        return self.item(int(key))
    
    def item(self, index):
        node = self.nodes[index]
        if(isinstance(node, BeautifulSoup.NavigableString)):
            return unicode(node)
        return DOMImplementation.createHTMLElement(self.doc, node) if 0 <= index and index < len(self.nodes) else None
    
    @property
    def length(self):
        return len(self.nodes)

class NamedNodeMap(PyV8.JSClass):
    def __init__(self, parent):        
        self.parent = parent
        
    def getNamedItem(self, name):
        return self.parent.getAttributeNode(name)
    
    def setNamedItem(self, attr):
        oldattr = self.parent.getAttributeNode(attr.name)
        
        attr.parent = self.parent
        
        self.parent.tag[attr.name] = attr.value
        
        if oldattr:
            oldattr.parent = None
        
        return oldattr
    
    def removeNamedItem(self, name):
        self.parent.removeAttribute(name)
    
    def item(self, index):
        names = self.parent.tag.attrMap.keys()
        return self.parent.getAttributeNode(names[index]) if 0 <= index and index < len(names) else None
    
    @property
    def length(self):        
        return len(self.parent.tag._getAttrMap()) 
        
class Attr(Node):
    _value = ""
    
    def __init__(self, parent, attr):
        self.parent = parent
        self.attr = attr
        
        self._value = self.getValue()
        
    def __repr__(self):
        return "<Attr object %s%s at 0x%08X>" % ("%s." % self.parent.tagName if self.parent else "", self.attr, id(self))
        
    def __eq__(self, other):
        return hasattr(other, "parent") and self.parent == other.parent and \
               hasattr(other, "attr") and self.attr == other.attr
        
    @property
    def nodeType(self):
        return Node.ATTRIBUTE_NODE
       
    @property        
    def nodeName(self):
        return self.attr
    
    def getNodeValue(self):
        return self.getValue()
    
    def setNodeValue(self, value):
        return self.setValue(value)
        
    nodeValue = property(getNodeValue, setNodeValue)
    
    @property
    def childNodes(self):
        return NodeList(self.parent.doc, [])
    
    @property
    def parentNode(self):
        return Node.wrap(self.parent.doc, self.parent)
        
    @property
    def ownerDocument(self):
        return self.parent.doc
    
    @property
    def name(self):
        return self.attr
    
    def specified(self):
        return self.parent.has_key(self.attr)
    
    def getValue(self):
        if self.parent:
            if self.parent.tag.has_key(self.attr):
                return self.parent.tag[self.attr]
            
        return self._value 
        
    def setValue(self, value):
        self._value = value
        
        if self.parent:
            self.parent.tag[self.attr] = value
        
    value = property(getValue, setValue)
    
class Element(Node):
    def __init__(self, doc, tag):
        Node.__init__(self, doc)
        self.tag = tag
        if('__wrap__' in dir(tag)):
            raise Exception, 'tag has been initialized'
        tag.__wrap__ = self

    def __str__(self):
        return str(self.tag)

    def __unicode__(self):
        return unicode(self.tag)
        
    def __repr__(self):
        return "<Element %s at 0x%08X>" % (self.tag.name, id(self))
        
    def __eq__(self, other):
        return Node.__eq__(self, other) and hasattr(other, "tag") and self.tag == other.tag
        
    @property
    def nodeType(self):
        return Node.ELEMENT_NODE
       
    @property
    def nodeName(self):
        return self.tagName
    
    @property
    def nodeValue(self):
        return None
    
    @property
    def attributes(self):
        return NamedNodeMap(self)    
    
    @property
    def parentNode(self):
        return Node.wrap(self.doc, self.tag.parent)
    
    @property
    def parentElement(self):
        return Node.wrap(self.doc, self.tag.parent)

    @property
    def childNodes(self):
        return NodeList(self.doc, self.tag.contents)
        
    @property
    def firstChild(self):
        return Node.wrap(self.doc, self.tag.contents[0]) if len(self.tag) > 0 else None
            
    @property
    def lastChild(self):
        return Node.wrap(self.doc, self.tag.contents[-1]) if len(self.tag) > 0 else None
            
    @property
    def nextSibling(self):
        return Node.wrap(self.doc, self.tag.nextSibling)
            
    @property
    def previousSibling(self):
        return Node.wrap(self.doc, self.tag.previousSibling)
        
    def checkChild(self, child):
        if not isinstance(child, Node):
            raise DOMException(DOMException.HIERARCHY_REQUEST_ERR)            
        
    def findChild(self, child):
        try:
            return self.tag.contents.index(child.tag)
        except ValueError:
            return -1
        
    def insertBefore(self, newChild, refChild):        
        self.checkChild(newChild)
        self.checkChild(refChild)
        
        index = self.findChild(refChild)        
        
        if index < 0:
            self.tag.append(newChild.tag)            
        else:        
            self.tag.insert(index, newChild.tag)
        
        return newChild

    def insertAfter(self, newChild, refChild):
        self.checkChild(newChild)
        self.checkChild(refChild)

        index = self.findChild(refChild)

        if index < 0:
            self.tag.append(newChild.tag)
        else:
            self.tag.insert(index+1, newChild.tag)

        return newChild

    def replaceChild(self, newChild, oldChild):
        self.checkChild(newChild)
        self.checkChild(oldChild)
        
        index = self.findChild(oldChild)
        
        if index < 0:
            raise DOMException(DOMException.NOT_FOUND_ERR)
            
        self.tag.contents[index] = newChild.tag
        
        return oldChild
    
    def removeChild(self, oldChild):
        self.checkChild(oldChild)
        
        self.tag.contents.remove(oldChild.tag)
        
        return oldChild
    
    def appendChild(self, newChild):
        if newChild:            
            if isinstance(newChild, Text):            
                self.tag.append(str(newChild))
            else:
                self.checkChild(newChild)
                
                self.tag.append(newChild.tag)
            
        return newChild
    
    def hasChildNodes(self):
        return len(self.tag.contents) > 0
    
    @property
    def tagName(self):
        return self.tag.name.upper()
    
    def getAttribute(self, name):
        return self.tag[name] if self.tag.has_key(name) else ""
        
    def setAttribute(self, name, value):
        self.tag[name] = value
        
    def removeAttribute(self, name):
        del self.tag[name]
        
    def getAttributeNode(self, name):
        return Attr(self, name) if self.tag.has_key(name) else None
    
    def setAttributeNode(self, attr):
        self.tag[attr.name] = attr.value
    
    def removeAttributeNode(self, attr):
        del self.tag[attr.name]
    
    def getElementsByTagName(self, tagname):
        if(tagname == '*'):
            tagname = True    
        else:
            tagname = tagname.lower()   
        return NodeList(self.doc, self.tag.findAll(tagname))
    
    def normalize(self):
        pass

class CharacterData(Node):
    def __init__(self, doc, tag):
        Node.__init__(self, doc)
        
        self.tag = tag
        
    def __str__(self):
        return str(self.tag)
        
    def getData(self):
        return unicode(self.tag)
        
    def setData(self, data):
        raise DOMException(DOMException.NO_MODIFICATION_ALLOWED_ERR)
        
    data = property(getData, setData)
    
    @property
    def length(self):
        return len(self.tag)
        
    def substringData(self, offset, count):
        return self.tag[offset:offset+count]
        
    def appendData(self, arg):
        raise DOMException(DOMException.NO_MODIFICATION_ALLOWED_ERR)
        
    def insertData(self, offset, arg):
        raise DOMException(DOMException.NO_MODIFICATION_ALLOWED_ERR)
        
    def deleteData(self, offset, count):
        raise DOMException(DOMException.NO_MODIFICATION_ALLOWED_ERR)
        
    def replaceData(self, offset, count, arg):
        raise DOMException(DOMException.NO_MODIFICATION_ALLOWED_ERR)

class Text(CharacterData):
    def __repr__(self):
        return "<Text '%s' at 0x%08X>" % (self.tag, id(self))

    def splitText(self, offset):
        raise DOMException(DOMException.NO_MODIFICATION_ALLOWED_ERR)
        
class CDATASection(Text):
    def __repr__(self):
        return "<CDATA '%s' at 0x%08X>" % (self.tag, id(self))

class Comment(CharacterData):
    pass

class DocumentFragment(Node):
    def __init__(self, doc, tags):
        Node.__init__(self, doc)
        
        self.tags = tags

class DocumentType(Node):
    RE_DOCTYPE = re.compile("^DOCTYPE (\w+)", re.M + re.S)
    
    def __init__(self, doc, tag):
        Node.__init__(self, doc)
        
        self.parse(tag)
        
    def parse(self, text):
        m = self.RE_DOCTYPE.match(text)
        
        self._name = m.group(1) if m else ""
        
    @property
    def name(self):
        return self._name
    
    @property
    def entities(self):
        raise NotImplementedError()
    
    @property
    def notations(self):
        raise NotImplementedError()
    
class Notation(Node):
    @property
    def publicId(self):
        pass
    
    @property
    def systemId(self):
        pass
    
class Entity(Node):
    @property
    def publicId(self):
        pass
    
    @property
    def systemId(self):
        pass
    
    @property
    def notationName(self):
        pass
    
class EntityReference(Node):
    def __init__(self, doc, name):
        Node.__init__(self, doc)
        
        self.name = name
        
    def nodeName(self):
        return self.name
    
class ProcessingInstruction(Node):
    def __init__(self, doc, target, data):
        self._target = target
        self.data = data
        
    @property
    def target(self):
        return self._target   

class Document(Node):
    def __str__(self):
        return str(self.doc)

    def __unicode__(self):
        return unicode(self.doc)

    def __repr__(self):
        return "<Document at 0x%08X>" % id(self)

    @property
    def nodeType(self):
        return Node.DOCUMENT_NODE
    
    @property
    def nodeName(self):
        return "#document"
    
    @property
    def nodeValue(self):
        return None
    
    @property
    def childNodes(self):
        return NodeList(self.doc, self.doc.contents)
        
    @property
    def doctype(self):
        for tag in self.doc:
            if isinstance(tag, BeautifulSoup.Declaration) and tag.startswith("DOCTYPE"):
                return DocumentType(self.doc, tag)
                
        return None
    
    @property
    def implementation(self):
        return self
    
    @property
    def documentElement(self):        
        return Node.wrap(self, self.doc.find('html'))
        
    onCreateElement = None
    
    def createElement(self, tagname):        
        element = DOMImplementation.createHTMLElement(self, BeautifulSoup.Tag(self.doc, tagname))
        
        if self.onCreateElement:
            self.onCreateElement(element)
        
        return element
    
    def createDocumentFragment(self):
        return DocumentFragment(self)
    
    def createTextNode(self, data):
        return Text(self, BeautifulSoup.NavigableString(data))
    
    def createComment(self, data):
        return Comment(self, data)
    
    def createCDATASection(self, data):
        return CDATASection(self, data)
    
    def createProcessingInstruction(self, target, data):
        return ProcessingInstruction(self, target, data)
    
    def createAttribute(self, name):
        return Attr(None, name)
    
    def createEntityReference(self, name):
        return EntityReference(self, name)
    
    def getElementsByTagName(self, tagname):
        if(tagname == '*'):
            tagname = True    
        else:
            tagname = tagname.lower()
        return NodeList(self.doc, self.doc.findAll(tagname))
        
def attr_property(name, attrtype=str, readonly=False, default=None):
    def getter(self):
        return attrtype(self.tag[name]) if self.tag.has_key(name) else default
        
    def setter(self, value):
        self.tag[name] = attrtype(value)
        
    return property(getter) if readonly else property(getter, setter)
        
def text_property(readonly=False):
    def getter(self):
        return self.tag.string
    
    def setter(self, text):
        if self.tag.string:
            self.tag.contents[0] = BeautifulSoup.NavigableString(text)
        else:
            self.tag.append(text)
                    
        self.tag.string = self.tag.contents[0]
        
    return property(getter) if readonly else property(getter, setter)
        
class HTMLCollection(PyV8.JSClass):
    def __init__(self, doc, nodes):
        self.doc = doc
        self.nodes = nodes
        
    def __len__(self):
        return self.length
        
    def __getitem__(self, key):        
        try:
            return self.item(int(key))
        except TypeError:
            return self.namedItem(str(key))        
        
    @property
    def length(self):
        return len(self.nodes)
    
    def item(self, index):
        node = self.nodes[index]
                
        return DOMImplementation.createHTMLElement(self.doc, node) if node else None
    
    def namedItem(self, name):
        for node in self.nodes:
            if node.nodeName == name:
                return DOMImplementation.createHTMLElement(self.doc, node) if node else None
            
        return None
    
class CSSStyleDeclaration(object):
    def __init__(self, style):
        self.props = dict([prop.strip().split(': ') for prop in style.split(';') if prop])
        
        for k, v in self.props.items():
            if v and v[0] == v[-1] and v[0] in ['"', "'"]:
                self.props[k] = v[1:-1]                
        
    @property
    def cssText(self):
        return '; '.join(["%s: %s" % (k, v) for k, v in self.props.items()])
        
    def getPropertyValue(self, name):
        return self.props.get(name, '')
        
    def removeProperty(self, name):
        v = self.props.get(name, '')
        
        if v:
            del self.props[name]
            
        return v
    
    @property
    def length(self):
        return len(self.props)
        
    def item(self, index):
        if type(index) == str:
            return self.props.get(index, '')
        
        if index < 0 or index >= len(self.props):
            return ''
        
        return self.props[self.props.keys()[index]]
        
    def __getattr__(self, name):
        if hasattr(object, name):
            return object.__getattribute__(self, name)
        else:
            return object.__getattribute__(self, 'props').get(name, '')
        
    def __setattr__(self, name, value):
        if name == 'props':
            object.__setattr__(self, name, value)
        else:
            object.__getattribute__(self, 'props')[name] = value
    
class ElementCSSInlineStyle(object):
    @property
    def style(self):
        return CSSStyleDeclaration(self.tag['style'] if self.tag.has_key('style') else '')

class HTMLElement(Element, ElementCSSInlineStyle):    
    id = attr_property("id")
    title = attr_property("title")
    lang = attr_property("lang")
    dir = attr_property("dir")
    className = attr_property("class")
    
    @property
    def innerHTML(self):
        if not self.hasChildNodes():
            return ""

        html = StringIO()

        for tag in self.tag.contents:
            html.write(str(tag).strip())

        return html.getvalue()

    @innerHTML.setter
    def innerHTML(self, html):
        dom = BeautifulSoup.BeautifulSoup(html)

        for node in dom.contents:
            self.tag.append(node)
    
    @property
    def textContent(self):
        return self.tag.getText()
    @textContent.setter
    def textContent(self, text):
        dom = BeautifulSoup.BeautifulSoup(text)

        for node in dom.contents:
            self.tag.append(node)        

    @property
    def innerText(self):
        return self.tag.getText()
    @innerText.setter
    def innerText(self, text):
        dom = BeautifulSoup.BeautifulSoup(text)

        for node in dom.contents:
            self.tag.append(node)   

class HTMLHtmlElement(HTMLElement):
    version = attr_property("version")
    
class HTMLHeadElement(HTMLElement):
    profile = attr_property("profile")
    
class HTMLLinkElement(HTMLElement):
    disabled = False
    
    charset = attr_property("charset")
    href = attr_property("href")
    hreflang = attr_property("hreflang")
    media = attr_property("media")
    rel = attr_property("rel")
    rev = attr_property("rev")
    target = attr_property("target")
    type = attr_property("type")
    
class HTMLTitleElement(HTMLElement):
    text = text_property()
    
class HTMLMetaElement(HTMLElement):
    content = attr_property("content")
    httpEquiv = attr_property("http-equiv")
    name = attr_property("name")
    scheme = attr_property("scheme")
    
class HTMLBaseElement(HTMLElement):
    href = attr_property("href")
    target = attr_property("target")
    
class HTMLIsIndexElement(HTMLElement):
    form = None
    prompt = attr_property("prompt")
    
class HTMLStyleElement(HTMLElement):
    disabled = False
    
    media = attr_property("media")
    type = attr_property("type")
    
class HTMLBodyElement(HTMLElement):
    background = attr_property("background")
    bgColor = attr_property("bgcolor")
    link = attr_property("link")
    aLink = attr_property("alink")
    vLink = attr_property("vlink")
    text = attr_property("text")
    
class HTMLFormElement(HTMLElement):
    @property
    def elements(self):
        raise NotImplementedError()
    
    @property
    def length(self):
        raise NotImplementedError()
    
    name = attr_property("name")
    acceptCharset = attr_property("accept-charset", default="UNKNOWN")
    action = attr_property("action")
    enctype = attr_property("enctype", default="application/x-www-form-urlencoded")
    method = attr_property("method", default="get")
    target = attr_property("target")
    
    def submit(self):
        raise NotImplementedError()
    
    def reset(self):
        raise NotImplementedError()
    
class HTMLSelectElement(HTMLElement):
    @property
    def type(self):
        raise NotImplementedError()
        
    selectedIndex = 0
    value = None
    
    @property
    def length(self):
        raise NotImplementedError()
        
    @property
    def form(self):
        raise NotImplementedError()
        
    @property
    def options(self):
        raise NotImplementedError()
        
    disabled = attr_property("disabled", bool)
    multiple = attr_property("multiple", bool)    
    name = attr_property("name")
    size = attr_property("size", long)
    tabIndex = attr_property("tabindex", long)
    
    def add(self, element, before):
        raise NotImplementedError()
        
    def remove(self, index):
        raise NotImplementedError()
        
    def blur(self):
        raise NotImplementedError()

    def focus(self):
        raise NotImplementedError()
        
class HTMLOptGroupElement(HTMLElement):
    disabled = attr_property("disabled", bool)    
    label = attr_property("label")
    
class HTMLOptionElement(HTMLElement):
    @property
    def form(self):
        raise NotImplementedError()
        
    defaultSelected = attr_property("selected", bool)    
    text = text_property(readonly=True)    
    index = attr_property("index", long)
    disabled = attr_property("disabled", bool)    
    label = attr_property("label")
    selected = False
    value = attr_property("value")
    
class HTMLInputElement(HTMLElement):    
    defaultValue = attr_property("value")
    defaultChecked = attr_property("checked")
    
    @property
    def form(self):
        raise NotImplementedError()
    
    accept = attr_property("accept")
    accessKey = attr_property("accesskey")
    align = attr_property("align")
    alt = attr_property("alt")
    checked = attr_property("checked", bool)
    disabled = attr_property("disabled", bool)
    maxLength = attr_property("maxlength", long, default=sys.maxint)
    name = attr_property("name")
    readOnly = attr_property("readonly", bool)
    size = attr_property("size")
    src = attr_property("src")
    tabIndex = attr_property("tabindex", long)
    type = attr_property("type", readonly=True, default="text")
    useMap = attr_property("usermap")
    
    @abstractmethod
    def getValue(self):
        pass
    
    @abstractmethod
    def setValue(self, value):
        pass
    
    value = property(getValue, setValue)
    
    def blur(self):
        pass
    
    def focus(self):
        pass
    
    def select(self):
        pass
    
    def click(self):
        pass
    
class HTMLTextAreaElement(HTMLElement):
    defaultValue = None
    
    @property
    def form(self):
        pass
    
    accessKey = attr_property("accesskey")
    cols = attr_property("cols", long)
    disabled = attr_property("disabled", bool)
    name = attr_property("name")
    readOnly = attr_property("readonly", bool)
    rows = attr_property("rows", long)
    tabIndex = attr_property("tabindex", long)
    value = text_property()
    
    @property
    def type(self):
        return "textarea"
    
class HTMLButtonElement(HTMLElement):
    @property
    def form(self):
        pass    
    
    accessKey = attr_property("accesskey")
    disabled = attr_property("disabled", bool)
    name = attr_property("name")
    tabIndex = attr_property("tabindex", long)
    type = attr_property("type")
    value = attr_property("value")
    
class HTMLAppletElement(HTMLElement):
    align = attr_property("align")
    alt = attr_property("alt")
    archive = attr_property("archive")
    code = attr_property("code")
    codeBase = attr_property("codebase")
    height = attr_property("height")
    hspace = attr_property("hspace")
    name = attr_property("name")
    object = attr_property("object")
    vspace = attr_property("vspace")
    width = attr_property("width")
    
class HTMLImageElement(HTMLElement):
    align = attr_property("align")
    alt = attr_property("alt")
    border = attr_property("border")
    height = attr_property("height")
    hspace = attr_property("hspace")
    isMap = attr_property("ismap")
    longDesc = attr_property("longdesc")
    lowSrc = attr_property("lowsrc")
    name = attr_property("name")
    src = attr_property("src")
    useMap = attr_property("usemap")
    vspace = attr_property("vspace")
    width = attr_property("width")
    
class HTMLScriptElement(HTMLElement):
    text = text_property()    
    htmlFor = None
    event = None
    charset = attr_property("charset")
    defer = attr_property("defer", bool)
    src = attr_property("src")
    type = attr_property("type")
    
class HTMLFrameSetElement(HTMLElement):
    cols = attr_property("cols")
    rows = attr_property("rows")

class HTMLFrameElement(HTMLElement):
    frameBorder = attr_property("frameborder")
    longDesc = attr_property("longdesc")
    marginHeight = attr_property("marginheight")
    marginWidth = attr_property("marginwidth")
    name = attr_property("name")
    noResize = attr_property("noresize", bool)
    scrolling = attr_property("scrolling")
    src = attr_property("src")
    
class HTMLIFrameElement(HTMLElement):
    align = attr_property("align")
    frameBorder = attr_property("frameborder")
    height = attr_property("height")
    longDesc = attr_property("longdesc")
    marginHeight = attr_property("marginheight")
    marginWidth = attr_property("marginwidth")
    name = attr_property("name")    
    scrolling = attr_property("scrolling")
    src = attr_property("src")
    width = attr_property("width")

def xpath_property(xpath, readonly=False):
    RE_INDEXED = re.compile("(\w+)\[([^\]]+)\]")
    
    parts = xpath.split('/')
    
    def getChildren(tag, parts, recursive=False):
        if len(parts) == 0:
            return [tag]
        
        part = parts[0]
        
        if part == '':
            return getChildren(tag, parts[1:], True)
            
        if part == 'text()':
            return [tag.string]
        
        m = RE_INDEXED.match(part)
        
        if m:
            name = m.group(1)
            idx = m.group(2)
        else:
            name = part
            idx = None

        children = []

        tags = tag.findAll(name, recursive=recursive)

        if idx:
            if idx[0] == '@':
                tags = [tag for tag in tags if tag.has_key(idx[1:])]
            else:
                tags = [tags[int(idx)-1]]
        
        for child in tags:
            children += getChildren(child, parts[1:])
            
        return children
        
    def getter(self):
        children = getChildren(self.doc, parts)
        
        if parts[-1] == 'text()':
            return "".join(children)

        m = RE_INDEXED.match(parts[-1])

        if m:
            try:
                string.atoi(m.group(2))

                return DOMImplementation.createHTMLElement(self.doc, children[0]) if len(children) > 0 else None
            except ValueError: 
                pass
                
        return HTMLCollection(self.doc, children)
        
    def setter(self, value):
        tag = self.doc
        
        for part in parts:
            if part == '':
                continue
            elif part == 'text()':
                if tag.string:
                    tag.contents[0] = BeautifulSoup.NavigableString(value)
                else:
                    tag.append(value)                    
                    
                tag.string = tag.contents[0]

                return
            else:
                child = tag.find(part)
                
                if not child:
                    child = BeautifulSoup.Tag(self.doc, part)
                    
                    tag.append(child)
                    
                tag = child
                
        tag.append(value)

    return property(getter) if readonly else property(getter, setter)

class HTMLDocument(Document):
    title = xpath_property("/html/head/title/text()")
    body = xpath_property("/html/body[1]")

    images = xpath_property("//img", readonly=True)
    applets = xpath_property("//applet", readonly=True)
    forms = xpath_property("//form", readonly=True)
    links = xpath_property("//a[@href]", readonly=True)
    anchors = xpath_property("//a[@name]", readonly=True)

    def __init__(self, doc, win=None, referer=None, lastModified=None, cookie=''):
        Document.__init__(self, doc)

        self._win = win
        self._referer = referer
        self._lastModified = lastModified
        self._cookie = cookie

        self._html = None

        self.current = None

    @property
    def window(self):
        return self._win

    @window.setter
    def window(self, win):
        self._win = win

    @property
    def referrer(self):
        return self._referer

    @property
    def lastModified(self):
        raise self._lastModified

    @property
    def cookie(self):
        return self._cookie
        
    @property
    def domain(self):
        return urlparse(self._win.url).hostname if self._win else ''
        
    @property
    def URL(self):
        return self._win.url if self._win else ''

    def open(self, mimetype='text/html', replace=False):
        self._html = StringIO()

        return self
    
    def close(self):
        html = self._html.getvalue()
        self._html.close()
        self._html = None

        self.doc = BeautifulSoup.BeautifulSoup(html)

    def write(self, html):
        if self._html:
            self._html.write(html)
        else:
            tag = self.current
            parent = tag.parent
            pos = parent.contents.index(tag) + 1

            for tag in BeautifulSoup.BeautifulSoup(html).contents:
                parent.insert(pos, tag)

                pos += 1

    def writeln(self, text):
        self.write(text + "\n")
    
    def getElementById(self, elementId):
        tag = self.doc.find(id=elementId)
        return DOMImplementation.createHTMLElement(self, tag) if tag else None

    def getElementsByName(self, elementName):
        tags = self.doc.findAll(attrs={'name': elementName})
        
        return HTMLCollection(self.doc, tags)

class DOMImplementation(HTMLDocument):
    def hasFeature(self, feature, version):
        return feature == "HTML" and version == "1.0"
        
    TAGS = {
        "html" : HTMLHtmlElement,
        "head" : HTMLHeadElement,
        "link" : HTMLLinkElement,
        "title" : HTMLTitleElement,
        "meta" : HTMLMetaElement,
        "base" : HTMLBaseElement,
        "isindex" : HTMLIsIndexElement,
        "style" : HTMLStyleElement,
        "body" : HTMLBodyElement,
        "form" : HTMLFormElement,
        "select" : HTMLSelectElement,
        "optgroup" : HTMLOptGroupElement,
        "option" : HTMLOptionElement,
        "input" : HTMLInputElement,
        "textarea" : HTMLTextAreaElement,
        "button" : HTMLButtonElement,
        "applet" : HTMLAppletElement,
        "img" : HTMLImageElement,
        "script" : HTMLScriptElement,
        "frameset" : HTMLFrameSetElement,
        "frame" : HTMLFrameElement,
        "iframe" : HTMLIFrameElement,
    }
        
    @staticmethod
    def createHTMLElement(doc, tag):   
        if('__wrap__' in dir(tag)):
            return tag.__wrap__     
        if DOMImplementation.TAGS.has_key(tag.name.lower()):            
            return DOMImplementation.TAGS[tag.name.lower()](doc, tag)
        else:
            return HTMLElement(doc, tag)
    
def getDOMImplementation(dom=None, **kwds):
    return DOMImplementation(dom if dom else BeautifulSoup.BeautifulSoup(), **kwds)
    
def parseString(html, **kwds):
    return DOMImplementation(BeautifulSoup.BeautifulSoup(html), **kwds)
    
def parse(file, **kwds):
    if isinstance(file, StringTypes):
        with open(file, 'r') as f:
            return parseString(f.read())
    
    return parseString(file.read(), **kwds)
    
import unittest

TEST_HTML = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
                      "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <!-- This is a comment -->
        <title>this is a test</title>
        <script type="text/javascript"> 
        //<![CDATA[
        function load()
        {
            alert("load");
        }
        function unload()
        {
            alsert("unload");
        }
        //]]>
        </script>         
    </head>
    <body onload="load()" onunload="unload()">
        <p id="hello">Hello World!</p>
        <form name="first"></form>
        <form name="second"></form>
        <a href="#">link</a>
        <a name="#">anchor</a>
    </body>
</html>"""

class DocumentTest(unittest.TestCase):
    def setUp(self):
        self.doc = parseString(TEST_HTML)
        
        self.assert_(self.doc)
        
    def testNode(self):
        self.assertEquals(Node.DOCUMENT_NODE, self.doc.nodeType)
        self.assertEquals("#document", self.doc.nodeName)
        self.failIf(self.doc.nodeValue)
        
        html = self.doc.documentElement
        
        self.assert_(html)        
        self.assertEquals(Node.ELEMENT_NODE, html.nodeType)
        self.assertEquals("HTML", html.nodeName)
        self.failIf(html.nodeValue)
        
        attr = html.getAttributeNode("xmlns")
        
        self.assert_(attr)

        self.assertEquals(Node.ATTRIBUTE_NODE, attr.nodeType)
        self.assertEquals("xmlns", attr.nodeName)
        self.assertEquals("http://www.w3.org/1999/xhtml", attr.nodeValue)
        
    def testNodeList(self):
        nodes = self.doc.getElementsByTagName("body")
        
        self.assertEquals(1, nodes.length)
        
        self.assert_(nodes.item(0))
        self.failIf(nodes.item(-1))
        self.failIf(nodes.item(1))

        self.assertEquals(1, len(nodes))

        self.assert_(nodes[0])
        self.failIf(nodes[-1])
        self.failIf(nodes[1])

    def testDocument(self):
        nodes = self.doc.getElementsByTagName("body")
        
        body = nodes.item(0)
        
        self.assertEquals("BODY", body.tagName)   
    
    def testDocumentType(self):
        doctype = self.doc.doctype
        
        self.assert_(doctype)
        
        self.assertEquals("html", doctype.name)
                
    def testElement(self):
        html = self.doc.documentElement
        
        self.assertEquals("HTML", html.tagName)
        self.assertEquals("http://www.w3.org/1999/xhtml", html.getAttribute("xmlns"))
        self.assert_(html.getAttributeNode("xmlns"))
        
        nodes = html.getElementsByTagName("body")
        
        self.assertEquals(1, nodes.length)
        
        body = nodes.item(0)
        
        self.assertEquals("BODY", body.tagName)
        
        div = self.doc.createElement("div")
        
        self.assert_(div)
        self.failIf(div.hasChildNodes())
        self.assertEquals(0, len(div.childNodes))
        
        a = self.doc.createElement("a")
        b = self.doc.createElement("b")
        p = self.doc.createElement("p")
        
        self.assert_(a == div.appendChild(a))
        self.assert_(div.hasChildNodes())
        self.assertEquals(1, len(div.childNodes))        
        self.assert_(a == div.childNodes[0])
        
        self.assert_(b == div.insertBefore(b, a))
        self.assertEquals(2, len(div.childNodes))
        self.assert_(b == div.childNodes[0])
        self.assert_(a == div.childNodes[1])
        
        self.assert_(a == div.replaceChild(p, a))
        self.assertEquals(2, len(div.childNodes))
        self.assert_(b == div.childNodes[0])
        self.assert_(p == div.childNodes[1])
        
        self.assert_(b == div.removeChild(b))
        self.assertEquals(1, len(div.childNodes))        
        self.assert_(p == div.childNodes[0])
        
        self.assertRaises(DOMException, div.appendChild, "hello")
        self.assertRaises(DOMException, div.insertBefore, "hello", p)
        self.assertRaises(DOMException, div.replaceChild, "hello", p)
        self.assertRaises(DOMException, div.removeChild, "hello")
        
    def testAttr(self):
        html = self.doc.documentElement
        
        attr = html.getAttributeNode("xmlns")
        
        self.assert_(attr)
        
        self.assertEquals(html, attr.parentNode)
        self.failIf(attr.hasChildNodes())        
        self.assert_(attr.childNodes != None)
        self.assertEquals(0, attr.childNodes.length)
        self.failIf(attr.firstChild)
        self.failIf(attr.lastChild)
        self.failIf(attr.previousSibling)
        self.failIf(attr.nextSibling)
        self.failIf(attr.attributes)
        
        self.assertFalse(attr.hasChildNodes())        
        
        self.assertEquals(self.doc, attr.ownerDocument)

        self.assertEquals("xmlns", attr.name)        
        self.assert_(True, attr.specified)
        
        self.assertEquals("http://www.w3.org/1999/xhtml", attr.value)
        
        attr.value = "test"
        
        self.assertEquals("test", attr.value)
        self.assertEquals("test", html.getAttribute("xmlns"))
        
        body = html.getElementsByTagName("body").item(0)
        
        self.assert_(body)
        
        onload = body.getAttributeNode("onload")
        onunload = body.getAttributeNode("onunload")
        
        self.assert_(onload)
        self.assert_(onunload)

    def testNamedNodeMap(self):
        attrs = self.doc.getElementsByTagName("body").item(0).attributes
        
        self.assert_(attrs)
        
        self.assertEquals(2, attrs.length)
        
        attr = attrs.getNamedItem("onload")
        
        self.assert_(attr)        
        self.assertEquals("onload", attr.name)
        self.assertEquals("load()", attr.value)
        
        attr = attrs.getNamedItem("onunload")
        
        self.assert_(attr)        
        self.assertEquals("onunload", attr.name)
        self.assertEquals("unload()", attr.value)
        
        self.failIf(attrs.getNamedItem("nonexists"))
        
        self.failIf(attrs.item(-1))
        self.failIf(attrs.item(attrs.length))
        
        for i in xrange(attrs.length):
            self.assert_(attrs.item(i))
            
        attr = self.doc.createAttribute("hello")
        attr.value = "world"
        
        self.assert_(attr)
        
        self.failIf(attrs.setNamedItem(attr))
        self.assertEquals("world", attrs.getNamedItem("hello").value)
        
        attr.value = "flier"
        
        self.assertEquals("flier", attrs.getNamedItem("hello").value)
        
        attrs.getNamedItem("hello").value = "world"
        
        self.assertEquals("world", attr.value)
        
        old = attrs.setNamedItem(self.doc.createAttribute("hello"))
        
        self.assert_(old)
        self.assertEquals(old.name, attr.name)
        self.assertEquals(old.value, attr.value)
        
        self.assertNotEquals(old, attr)
        
        self.assertEquals(attr, attrs.getNamedItem("hello"))
        
        attrs.getNamedItem("hello").value = "flier"
        
        self.assertEquals("flier", attrs.getNamedItem("hello").value)
        self.assertEquals("flier", attr.value)
        self.assertEquals("world", old.value)
        self.failIf(old.parent)

class HTMLDocumentTest(unittest.TestCase):
    def setUp(self):
        self.doc = parseString(TEST_HTML)
        
        self.assert_(self.doc)
        
    def testHTMLElement(self):
        p = self.doc.getElementById('hello')
        
        self.assert_(p)
        
        self.assertEquals('hello', p.id)
        
        p.id = 'test'
        
        self.assertEquals(p, self.doc.getElementById('test'))
        
        forms = self.doc.getElementsByName('first')
        
        self.assertEquals(1, len(forms))

        self.assertEquals('<p id="test">Hello World!</p>' +
                          '<form name="first"></form>' +
                          '<form name="second"></form>' +
                          '<a href="#">link</a>' +
                          '<a name="#">anchor</a>',
                          self.doc.getElementsByTagName('body')[0].innerHTML)
        self.assertEquals("Hello World!", p.innerHTML)
        self.assertEquals("", self.doc.getElementsByTagName('form')[0].innerHTML)

        self.assertEquals(None, self.doc.getElementById('inner'))

        self.doc.getElementsByTagName('form')[0].innerHTML = "<div id='inner'/>"

        self.assertEquals(u'DIV', self.doc.getElementById('inner').tagName)
        
    def testDocument(self):
        self.assertEquals("this is a test", self.doc.title)
        
        self.doc.title = "another title"
        
        self.assertEquals("another title", self.doc.title)
        
        doc = parseString("<html></html>")
        
        self.failIf(doc.title)
        
        doc.title = "another title"        
        
        self.assertEquals("another title", doc.title)        
        
        self.assertEquals(self.doc.getElementsByTagName('body')[0], self.doc.body)
        
        forms = self.doc.forms
        
        self.assert_(forms != None)
        self.assertEquals(2, len(forms))
        
        self.assert_(isinstance(forms[0], HTMLFormElement))
        self.assertEquals("first", forms[0].name)
        self.assertEquals("second", forms[1].name)

        self.assertEquals(1, len(self.doc.links))
        self.assertEquals(1, len(self.doc.anchors))

    def testWrite(self):
        self.assertEquals("this is a test", self.doc.title)

        doc = self.doc.open()
        doc.write("<html><head><title>Hello World</title></head><body></body></html>")
        doc.close()

        self.assertEquals("Hello World", doc.title)

        doc.current = doc.getElementsByTagName('title')[0].tag
        doc.write("<meta/>")

        self.assertEquals("<head><title>Hello World</title><meta /></head>", str(doc.getElementsByTagName('head')[0]))
        
class CSSStyleDeclarationTest(unittest.TestCase):
    def testParse(self):
        style = 'width: "auto"; border: "none"; font-family: "serif"; background: "red"'
        
        css = CSSStyleDeclaration(style)
        
        self.assert_(css)
        self.assertEquals('width: auto; font-family: serif; border: none; background: red', css.cssText)
        self.assertEquals(4, css.length)
        
        self.assertEquals('auto', css.getPropertyValue('width'))
        self.assertEquals('', css.getPropertyValue('height'))
        
        self.assertEquals('auto', css.item(0))
        self.assertEquals('auto', css.width)
        
        css.width = 'none'
        
        self.assertEquals('none', css.getPropertyValue('width'))
        self.assertEquals('none', css.item(0))
        self.assertEquals('none', css.width)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG if "-v" in sys.argv else logging.WARN,
                        format='%(asctime)s %(levelname)s %(message)s')
    
    unittest.main()
########NEW FILE########
__FILENAME__ = jshint
#coding: utf8

import sublime, sublime_plugin
import PyV8
import sys, re, platform
from core import package_file

JSHINT_VIEW_NAME = 'jshint_view'
class JsHintCommand(sublime_plugin.WindowCommand):
	def __init__(self, window):
		self.panel = window.get_output_panel(JSHINT_VIEW_NAME)
		self.panel.set_name(JSHINT_VIEW_NAME)
		self.window = window
		ctx = PyV8.JSContext()
		ctx.enter()
		jshint_file = file(package_file("jshint.js"))
		source = jshint_file.read()
		self.jshint = ctx.eval(source)
		jshint_file.close()		

	def run(self):
		view = self.window.active_view()
		jsscopes = view.find_by_selector('source.js - entity.name.tag.script.html - punctuation.definition.tag.html')

		self.window.run_command("show_panel", {"panel": "output."+JSHINT_VIEW_NAME})
		#self.window.focus_view(self.panel)
		self.panel.set_read_only(False)
		edit = self.panel.begin_edit()
		self.panel.erase(edit, sublime.Region(0, self.panel.size()))
		self.panel.insert(edit, self.panel.size(), view.file_name() + '\n')
		self.panel.insert(edit, self.panel.size(), "parsing...")
		settings = sublime.load_settings('JSHINT.sublime-settings')
		hint_options = dump_settings(settings, 
										["asi", "bitwise", "boss","browser","couch","curly","debug","devel","dojo","eqeqeq","eqnull","es5","esnext","evil","expr","forin","funcscope","globalstrict","immed","iterator","jquery","lastsemic","latedef","laxbreak","loopfunc","mootools","multistr","newcap","noarg","node","noempty","nonew","nonstandard","nomen","onevar","onecase","passfail","plusplus","proto","prototypejs","regexdash","regexp","rhino","undef","scripturl","shadow","smarttabs","strict","sub","supernew","trailing","validthis","white","wsh"])
		self.panel.end_edit(edit)
		self.panel.set_read_only(True)

		def show_errors():
			self.panel.set_read_only(False)
			edit = self.panel.begin_edit()
			self.panel.insert(edit, self.panel.size(), "done" + '\n\n')
			count_warnings = 0

			for scope in jsscopes:
				source = view.substr(scope)
				if(self.jshint(source, hint_options)):
					pass
				else:
					result = self.jshint.data()
					for error in result.errors:
						if(error):
							keys = dir(error)
							evidence = character = line = ''
							
							details = []
							if('line' in keys):
								details.append(' line : ' + str(error.line + view.rowcol(scope.begin())[0]))
							if('character' in keys):
								details.append(' character : ' + str(error.character))
							if('evidence' in keys):
								details.append(' near : ' + error.evidence.decode("UTF-8"));
							if(settings.get("warnings") or 'id' in keys and not re.compile("^warning ").match(error.id)):
								self.panel.insert(edit, self.panel.size(), error.id + ' : ' + error.reason + ' ,'.join(details) + ' \n')
							if(re.compile("^warning ").match(error.id)):
								count_warnings = count_warnings + 1

			line_errors = self.panel.find_all('^error.*')
			self.panel.add_regions('jshint_errors', line_errors, "invalid")

			self.panel.insert(edit, self.panel.size(), '\n' + str(len(line_errors)) + ' errors, ' + str(count_warnings) + ' warnings\n\n')

			if(not settings.get("warnings")):
				self.panel.insert(edit, self.panel.size(), '(You can set `warnings` to true via `JSHINT.sublime-settings` to show warning details)\n\n')

			self.panel.end_edit(edit)
			self.panel.set_read_only(True)
			self.window.focus_view(self.panel)
		
		sublime.set_timeout(show_errors, 1)


def dump_settings(settings, keys):
	ret = {}
	for key in keys:
		ret.update({key : settings.get(key)})
	return ret;

def on_syntax_error(view, context, scope):
	source = view.substr(scope)
	try:
		if(platform.system() == 'Windows'):
			try:
				source = source.encode('utf-8')
			except:
				source = source.encode('gbk')
		context.eval(source)
	except Exception,ex:
		if('name' in dir(ex) and ex.name == 'SyntaxError'):
			err_region = sublime.Region(scope.begin() + ex.startPos, scope.begin() + ex.endPos)
			view.add_regions('v8_errors', [err_region], "invalid")	
			if('message' in dir(ex)):
				sublime.status_message(ex.message)

def get_file_view(window, file_name):
    for file_view in window.views():
    	if(file_view.file_name() == file_name):
    		return file_view

class EventListener(sublime_plugin.EventListener):
	def __init__(self):
		ctx = PyV8.JSContext()
		ctx.enter()
		self.ctx = ctx
		self.file_view = None
	
	def on_deactivated(self, view):
	    if self.file_view:
	    	self.file_view.erase_regions('jshint_errors')
	    			    	    		
	def on_selection_modified(self, view):
	    if view.name() != JSHINT_VIEW_NAME:
	      return
	  
	    window = sublime.active_window()
	    file_name = view.substr(view.line(0))

	    file_view = get_file_view(window, file_name)
	    self.file_view = file_view
	  	  
	    if(file_view):
		    region = view.line(view.sel()[0])
		    text = view.substr(region);

		    m = re.compile('.*line : (\d+) , character : (\d+)').match(text)
		    if(m):
		    	view.add_regions('jshint_focus', [region], "string")
		    	(row, col) = m.groups()
		    	point = file_view.text_point(int(row) - 1, 0)
		    	line = file_view.line(point)
		    	file_view.add_regions('jshint_errors', [line], "invalid")	
    			window.focus_view(file_view)
    			file_view.run_command("goto_line", {"line": row})
	      		
	def on_modified(self, view):
		sublime.set_timeout((lambda view,context : (lambda: realtimeHint(view, context)))(view, self.ctx), 1)
		

def realtimeHint(view, ctx):
	jsscopes = view.find_by_selector('source.js - entity.name.tag.script.html - punctuation.definition.tag.html')
	if(not jsscopes):
		return

	view.erase_regions('v8_errors')
	sublime.status_message('')

	for scope in jsscopes:
		on_syntax_error(view, ctx, scope)
		

########NEW FILE########
__FILENAME__ = PyV8
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import with_statement

import sys, os, re

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

try:
    import json
except ImportError:
    import simplejson as json

import _PyV8

__author__ = 'Flier Lu <flier.lu@gmail.com>'
__version__ = '1.0'

__all__ = ["ReadOnly", "DontEnum", "DontDelete", "Internal",
           "JSError", "JSObject", "JSArray", "JSFunction",
           "JSClass", "JSEngine", "JSContext",
           "JSObjectSpace", "JSAllocationAction",
           "JSStackTrace", "JSStackFrame", "profiler", 
           "JSExtension", "JSLocker", "JSUnlocker", "AST"]

class JSAttribute(object):
    def __init__(self, name):
        self.name = name

    def __call__(self, func):
        setattr(func, "__%s__" % self.name, True)
        
        return func

ReadOnly = JSAttribute(name='readonly')
DontEnum = JSAttribute(name='dontenum')
DontDelete = JSAttribute(name='dontdel')
Internal = JSAttribute(name='internal')

class JSError(Exception):
    def __init__(self, impl):
        Exception.__init__(self)

        self._impl = impl

    def __str__(self):
        return str(self._impl)

    def __unicode__(self, *args, **kwargs):
        return unicode(self._impl)

    def __getattribute__(self, attr):
        impl = super(JSError, self).__getattribute__("_impl")

        try:
            return getattr(impl, attr)
        except AttributeError:
            return super(JSError, self).__getattribute__(attr)

    RE_FRAME = re.compile(r"\s+at\s(?:new\s)?(?P<func>.+)\s\((?P<file>[^:]+):?(?P<row>\d+)?:?(?P<col>\d+)?\)")
    RE_FUNC = re.compile(r"\s+at\s(?:new\s)?(?P<func>.+)\s\((?P<file>[^\)]+)\)")
    RE_FILE = re.compile(r"\s+at\s(?P<file>[^:]+):?(?P<row>\d+)?:?(?P<col>\d+)?")

    @staticmethod
    def parse_stack(value):
        stack = []

        def int_or_nul(value):
            return int(value) if value else None

        for line in value.split('\n')[1:]:
            m = JSError.RE_FRAME.match(line)

            if m:
                stack.append((m.group('func'), m.group('file'), int_or_nul(m.group('row')), int_or_nul(m.group('col'))))
                continue

            m = JSError.RE_FUNC.match(line)

            if m:
                stack.append((m.group('func'), m.group('file'), None, None))
                continue

            m = JSError.RE_FILE.match(line)

            if m:
                stack.append((None, m.group('file'), int_or_nul(m.group('row')), int_or_nul(m.group('col'))))
                continue

            assert line

        return stack

    @property
    def frames(self):
        return self.parse_stack(self.stackTrace)

_PyV8._JSError._jsclass = JSError

JSObject = _PyV8.JSObject
JSArray = _PyV8.JSArray
JSFunction = _PyV8.JSFunction
JSExtension = _PyV8.JSExtension

def func_apply(self, thisArg, argArray=[]):
    if isinstance(thisArg, JSObject):
        return self.invoke(thisArg, argArray)

    this = JSContext.current.eval("(%s)" % json.dumps(thisArg))

    return self.invoke(this, argArray)

JSFunction.apply = func_apply

class JSLocker(_PyV8.JSLocker):
    def __enter__(self):
        self.enter()

        if JSContext.entered:
            self.leave()
            raise RuntimeError("Lock should be acquired before enter the context")

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if JSContext.entered:
            self.leave()
            raise RuntimeError("Lock should be released after leave the context")

        self.leave()

    def __nonzero__(self):
        return self.entered()

class JSUnlocker(_PyV8.JSUnlocker):
    def __enter__(self):
        self.enter()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.leave()

    def __nonzero__(self):
        return self.entered()

class JSClass(object):
    __properties__ = {}
    __watchpoints__ = {}

    def __getattr__(self, name):
        if name == 'constructor':
            return JSClassConstructor(self.__class__)

        if name == 'prototype':
            return JSClassPrototype(self.__class__)

        prop = self.__dict__.setdefault('__properties__', {}).get(name, None)

        if prop and callable(prop[0]):
            return prop[0]()

        raise AttributeError(name)

    def __setattr__(self, name, value):
        prop = self.__dict__.setdefault('__properties__', {}).get(name, None)

        if prop and callable(prop[1]):
            return prop[1](value)

        return object.__setattr__(self, name, value)

    def toString(self):
        "Returns a string representation of an object."
        return "[object %s]" % self.__class__.__name__

    def toLocaleString(self):
        "Returns a value as a string value appropriate to the host environment's current locale."
        return self.toString()

    def valueOf(self):
        "Returns the primitive value of the specified object."
        return self

    def hasOwnProperty(self, name):
        "Returns a Boolean value indicating whether an object has a property with the specified name."
        return hasattr(self, name)

    def isPrototypeOf(self, obj):
        "Returns a Boolean value indicating whether an object exists in the prototype chain of another object."
        raise NotImplementedError()

    def __defineGetter__(self, name, getter):
        "Binds an object's property to a function to be called when that property is looked up."
        self.__properties__[name] = (getter, self.__lookupSetter__(name))

    def __lookupGetter__(self, name):
        "Return the function bound as a getter to the specified property."
        return self.__properties__.get(name, (None, None))[0]

    def __defineSetter__(self, name, setter):
        "Binds an object's property to a function to be called when an attempt is made to set that property."
        self.__properties__[name] = (self.__lookupGetter__(name), setter)

    def __lookupSetter__(self, name):
        "Return the function bound as a setter to the specified property."
        return self.__properties__.get(name, (None, None))[1]

    def watch(self, prop, handler):
        "Watches for a property to be assigned a value and runs a function when that occurs."
        self.__watchpoints__[prop] = handler

    def unwatch(self, prop):
        "Removes a watchpoint set with the watch method."
        del self.__watchpoints__[prop]

class JSClassConstructor(JSClass):
    def __init__(self, cls):
        self.cls = cls

    @property
    def name(self):
        return self.cls.__name__

    def toString(self):
        return "function %s() {\n  [native code]\n}" % self.name

    def __call__(self, *args, **kwds):
        return self.cls(*args, **kwds)

class JSClassPrototype(JSClass):
    def __init__(self, cls):
        self.cls = cls

    @property
    def constructor(self):
        return JSClassConstructor(self.cls)

    @property
    def name(self):
        return self.cls.__name__

class JSDebugProtocol(object):
    """
    Support the V8 debugger JSON based protocol.

    <http://code.google.com/p/v8/wiki/DebuggerProtocol>
    """
    class Packet(object):
        REQUEST = 'request'
        RESPONSE = 'response'
        EVENT = 'event'

        def __init__(self, payload):
            self.data = json.loads(payload) if type(payload) in [str, unicode] else payload

        @property
        def seq(self):
            return self.data['seq']

        @property
        def type(self):
            return self.data['type']

    class Request(Packet):
        @property
        def cmd(self):
            return self.data['command']

        @property
        def args(self):
            return self.data['args']

    class Response(Packet):
        @property
        def request_seq(self):
            return self.data['request_seq']

        @property
        def cmd(self):
            return self.data['command']

        @property
        def body(self):
            return self.data['body']

        @property
        def running(self):
            return self.data['running']

        @property
        def success(self):
            return self.data['success']

        @property
        def message(self):
            return self.data['message']

    class Event(Packet):
        @property
        def event(self):
            return self.data['event']

        @property
        def body(self):
            return self.data['body']

    def __init__(self):
        self.seq = 0

    def nextSeq(self):
        seq = self.seq
        self.seq += 1

        return seq

    def parsePacket(self, payload):
        obj = json.loads(payload)

        return JSDebugProtocol.Event(obj) if obj['type'] == 'event' else JSDebugProtocol.Response(obj)
    
class JSDebugEvent(_PyV8.JSDebugEvent):
    class FrameData(object):
        def __init__(self, frame, count, name, value):
            self.frame = frame
            self.count = count
            self.name = name
            self.value = value

        def __len__(self):
            return self.count(self.frame)

        def __iter__(self):
            for i in xrange(self.count(self.frame)):
                yield (self.name(self.frame, i), self.value(self.frame, i))

    class Frame(object):
        def __init__(self, frame):
            self.frame = frame

        @property
        def index(self):
            return int(self.frame.index())

        @property
        def function(self):
            return self.frame.func()

        @property
        def receiver(self):
            return self.frame.receiver()

        @property
        def isConstructCall(self):
            return bool(self.frame.isConstructCall())

        @property
        def isDebuggerFrame(self):
            return bool(self.frame.isDebuggerFrame())

        @property
        def argumentCount(self):
            return int(self.frame.argumentCount())

        def argumentName(self, idx):
            return str(self.frame.argumentName(idx))

        def argumentValue(self, idx):
            return self.frame.argumentValue(idx)

        @property
        def arguments(self):
            return FrameData(self, self.argumentCount, self.argumentName, self.argumentValue)

        def localCount(self, idx):
            return int(self.frame.localCount())

        def localName(self, idx):
            return str(self.frame.localName(idx))

        def localValue(self, idx):
            return self.frame.localValue(idx)

        @property
        def locals(self):
            return FrameData(self, self.localCount, self.localName, self.localValue)

        @property
        def sourcePosition(self):
            return self.frame.sourcePosition()

        @property
        def sourceLine(self):
            return int(self.frame.sourceLine())

        @property
        def sourceColumn(self):
            return int(self.frame.sourceColumn())

        @property
        def sourceLineText(self):
            return str(self.frame.sourceLineText())

        def evaluate(self, source, disable_break = True):
            return self.frame.evaluate(source, disable_break)

        @property
        def invocationText(self):
            return str(self.frame.invocationText())

        @property
        def sourceAndPositionText(self):
            return str(self.frame.sourceAndPositionText())

        @property
        def localsText(self):
            return str(self.frame.localsText())

        def __str__(self):
            return str(self.frame.toText())

    class Frames(object):
        def __init__(self, state):
            self.state = state

        def __len__(self):
            return self.state.frameCount

        def __iter__(self):
            for i in xrange(self.state.frameCount):
                yield self.state.frame(i)

    class State(object):
        def __init__(self, state):
            self.state = state

        @property
        def frameCount(self):
            return int(self.state.frameCount())

        def frame(self, idx = None):
            return JSDebugEvent.Frame(self.state.frame(idx))

        @property
        def selectedFrame(self):
            return int(self.state.selectedFrame())

        @property
        def frames(self):
            return JSDebugEvent.Frames(self)

        def __repr__(self):
            s = StringIO()

            try:
                for frame in self.frames:
                    s.write(str(frame))

                return s.getvalue()
            finally:
                s.close()

    class DebugEvent(object):
        pass

    class StateEvent(DebugEvent):
        __state = None

        @property
        def state(self):
            if not self.__state:
                self.__state = JSDebugEvent.State(self.event.executionState())

            return self.__state

    class BreakEvent(StateEvent):
        type = _PyV8.JSDebugEvent.Break

        def __init__(self, event):
            self.event = event

    class ExceptionEvent(StateEvent):
        type = _PyV8.JSDebugEvent.Exception

        def __init__(self, event):
            self.event = event

    class NewFunctionEvent(DebugEvent):
        type = _PyV8.JSDebugEvent.NewFunction

        def __init__(self, event):
            self.event = event

    class Script(object):
        def __init__(self, script):
            self.script = script

        @property
        def source(self):
            return self.script.source()

        @property
        def id(self):
            return self.script.id()

        @property
        def name(self):
            return self.script.name()

        @property
        def lineOffset(self):
            return self.script.lineOffset()

        @property
        def lineCount(self):
            return self.script.lineCount()

        @property
        def columnOffset(self):
            return self.script.columnOffset()

        @property
        def type(self):
            return self.script.type()

        def __repr__(self):
            return "<%s script %s @ %d:%d> : '%s'" % (self.type, self.name,
                                                      self.lineOffset, self.columnOffset,
                                                      self.source)

    class CompileEvent(StateEvent):
        def __init__(self, event):
            self.event = event

        @property
        def script(self):
            if not hasattr(self, "_script"):
                setattr(self, "_script", JSDebugEvent.Script(self.event.script()))

            return self._script

        def __str__(self):
            return str(self.script)

    class BeforeCompileEvent(CompileEvent):
        type = _PyV8.JSDebugEvent.BeforeCompile

        def __init__(self, event):
            JSDebugEvent.CompileEvent.__init__(self, event)

        def __repr__(self):
            return "before compile script: %s\n%s" % (repr(self.script), repr(self.state))

    class AfterCompileEvent(CompileEvent):
        type = _PyV8.JSDebugEvent.AfterCompile

        def __init__(self, event):
            JSDebugEvent.CompileEvent.__init__(self, event)

        def __repr__(self):
            return "after compile script: %s\n%s" % (repr(self.script), repr(self.state))

    onMessage = None
    onBreak = None
    onException = None
    onNewFunction = None
    onBeforeCompile = None
    onAfterCompile = None

class JSDebugger(JSDebugProtocol, JSDebugEvent):
    def __init__(self):
        JSDebugProtocol.__init__(self)
        JSDebugEvent.__init__(self)

    def __enter__(self):
        self.enabled = True

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.enabled = False

    @property
    def context(self):
        if not hasattr(self, '_context'):
            self._context = JSContext(ctxt=_PyV8.debug().context)

        return self._context

    def isEnabled(self):
        return _PyV8.debug().enabled

    def setEnabled(self, enable):
        dbg = _PyV8.debug()

        if enable:
            dbg.onDebugEvent = self.onDebugEvent
            dbg.onDebugMessage = self.onDebugMessage
            dbg.onDispatchDebugMessages = self.onDispatchDebugMessages
        else:
            dbg.onDebugEvent = None
            dbg.onDebugMessage = None
            dbg.onDispatchDebugMessages = None

        dbg.enabled = enable

    enabled = property(isEnabled, setEnabled)

    def onDebugMessage(self, msg, data):
        if self.onMessage:
            self.onMessage(json.loads(msg))

    def onDebugEvent(self, type, state, evt):
        if type == JSDebugEvent.Break:
            if self.onBreak: self.onBreak(JSDebugEvent.BreakEvent(evt))
        elif type == JSDebugEvent.Exception:
            if self.onException: self.onException(JSDebugEvent.ExceptionEvent(evt))
        elif type == JSDebugEvent.NewFunction:
            if self.onNewFunction: self.onNewFunction(JSDebugEvent.NewFunctionEvent(evt))
        elif type == JSDebugEvent.BeforeCompile:
            if self.onBeforeCompile: self.onBeforeCompile(JSDebugEvent.BeforeCompileEvent(evt))
        elif type == JSDebugEvent.AfterCompile:
            if self.onAfterCompile: self.onAfterCompile(JSDebugEvent.AfterCompileEvent(evt))

    def onDispatchDebugMessages(self):
        return True

    def debugBreak(self):
        _PyV8.debug().debugBreak()

    def debugBreakForCommand(self):
        _PyV8.debug().debugBreakForCommand()

    def cancelDebugBreak(self):
        _PyV8.debug().cancelDebugBreak()

    def processDebugMessages(self):
        _PyV8.debug().processDebugMessages()

    def sendCommand(self, cmd, *args, **kwds):
        request = json.dumps({
            'seq': self.nextSeq(),
            'type': 'request',
            'command': cmd,
            'arguments': kwds
        })

        _PyV8.debug().sendCommand(request)

        return request

    def debugContinue(self, action='next', steps=1):
        return self.sendCommand('continue', stepaction=action)

    def stepNext(self, steps=1):
        """Step to the next statement in the current function."""
        return self.debugContinue(action='next', steps=steps)

    def stepIn(self, steps=1):
        """Step into new functions invoked or the next statement in the current function."""
        return self.debugContinue(action='in', steps=steps)

    def stepOut(self, steps=1):
        """Step out of the current function."""
        return self.debugContinue(action='out', steps=steps)

    def stepMin(self, steps=1):
        """Perform a minimum step in the current function."""
        return self.debugContinue(action='out', steps=steps)

class JSProfiler(_PyV8.JSProfiler):
    @property
    def logs(self):
        pos = 0

        while True:
            size, buf = self.getLogLines(pos)

            if size == 0:
                break

            for line in buf.split('\n'):
                yield line

            pos += size

profiler = JSProfiler()

JSObjectSpace = _PyV8.JSObjectSpace
JSAllocationAction = _PyV8.JSAllocationAction

class JSEngine(_PyV8.JSEngine):
    def __init__(self):
        _PyV8.JSEngine.__init__(self)
        
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        del self

JSScript = _PyV8.JSScript

JSStackTrace = _PyV8.JSStackTrace
JSStackTrace.Options = _PyV8.JSStackTraceOptions
JSStackFrame = _PyV8.JSStackFrame

class JSIsolate(_PyV8.JSIsolate):
    def __enter__(self):
        self.enter()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.leave()

        del self

class JSContext(_PyV8.JSContext):
    def __init__(self, obj=None, extensions=None, ctxt=None):
        if JSLocker.active:
            self.lock = JSLocker()
            self.lock.enter()

        if ctxt:
            _PyV8.JSContext.__init__(self, ctxt)
        else:
            _PyV8.JSContext.__init__(self, obj, extensions or [])

    def __enter__(self):
        self.enter()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.leave()

        if hasattr(JSLocker, 'lock'):
            self.lock.leave()
            self.lock = None

        del self

# contribute by marc boeker <http://code.google.com/u/marc.boeker/>
def convert(obj):
    if type(obj) == _PyV8.JSArray:
        return [convert(v) for v in obj]

    if type(obj) == _PyV8.JSObject:
        return dict([[str(k), convert(obj.__getattr__(str(k)))] for k in obj.__members__])

    return obj

class AST:
    Scope = _PyV8.AstScope
    VarMode = _PyV8.AstVariableMode
    Var = _PyV8.AstVariable
    Label = _PyV8.AstLabel
    NodeType = _PyV8.AstNodeType
    Node = _PyV8.AstNode
    Statement = _PyV8.AstStatement
    Expression = _PyV8.AstExpression
    Breakable = _PyV8.AstBreakableStatement
    Block = _PyV8.AstBlock
    Declaration = _PyV8.AstDeclaration
    Iteration = _PyV8.AstIterationStatement
    DoWhile = _PyV8.AstDoWhileStatement
    While = _PyV8.AstWhileStatement
    For = _PyV8.AstForStatement
    ForIn = _PyV8.AstForInStatement
    ExpressionStatement = _PyV8.AstExpressionStatement
    Continue = _PyV8.AstContinueStatement
    Break = _PyV8.AstBreakStatement
    Return = _PyV8.AstReturnStatement
    With = _PyV8.AstWithStatement
    Case = _PyV8.AstCaseClause
    Switch = _PyV8.AstSwitchStatement
    Try = _PyV8.AstTryStatement
    TryCatch = _PyV8.AstTryCatchStatement
    TryFinally = _PyV8.AstTryFinallyStatement
    Debugger = _PyV8.AstDebuggerStatement
    Empty = _PyV8.AstEmptyStatement
    Literal = _PyV8.AstLiteral
    MaterializedLiteral = _PyV8.AstMaterializedLiteral
    PropertyKind = _PyV8.AstPropertyKind
    ObjectProperty = _PyV8.AstObjectProperty
    Object = _PyV8.AstObjectLiteral
    RegExp = _PyV8.AstRegExpLiteral
    Array = _PyV8.AstArrayLiteral
    VarProxy = _PyV8.AstVariableProxy
    Property = _PyV8.AstProperty
    Call = _PyV8.AstCall
    CallNew = _PyV8.AstCallNew
    CallRuntime = _PyV8.AstCallRuntime
    Op = _PyV8.AstOperation
    UnaryOp = _PyV8.AstUnaryOperation
    BinOp = _PyV8.AstBinaryOperation
    CountOp = _PyV8.AstCountOperation
    CompOp = _PyV8.AstCompareOperation
    Conditional = _PyV8.AstConditional
    Assignment = _PyV8.AstAssignment
    Throw = _PyV8.AstThrow
    Function = _PyV8.AstFunctionLiteral
    SharedFunction = _PyV8.AstSharedFunctionInfoLiteral
    This = _PyV8.AstThisFunction

from datetime import *
import unittest
import logging
import traceback

class TestContext(unittest.TestCase):
    def testMultiNamespace(self):
        self.assert_(not bool(JSContext.inContext))
        self.assert_(not bool(JSContext.entered))

        class Global(object):
            name = "global"

        g = Global()

        with JSContext(g) as ctxt:
            self.assert_(bool(JSContext.inContext))
            self.assertEquals(g.name, str(JSContext.entered.locals.name))
            self.assertEquals(g.name, str(JSContext.current.locals.name))

            class Local(object):
                name = "local"

            l = Local()

            with JSContext(l):
                self.assert_(bool(JSContext.inContext))
                self.assertEquals(l.name, str(JSContext.entered.locals.name))
                self.assertEquals(l.name, str(JSContext.current.locals.name))

            self.assert_(bool(JSContext.inContext))
            self.assertEquals(g.name, str(JSContext.entered.locals.name))
            self.assertEquals(g.name, str(JSContext.current.locals.name))

        self.assert_(not bool(JSContext.entered))
        self.assert_(not bool(JSContext.inContext))

    def _testMultiContext(self):
        # Create an environment
        with JSContext() as ctxt0:
            ctxt0.securityToken = "password"

            global0 = ctxt0.locals
            global0.custom = 1234

            self.assertEquals(1234, int(global0.custom))

            # Create an independent environment
            with JSContext() as ctxt1:
                ctxt1.securityToken = ctxt0.securityToken

                global1 = ctxt1.locals
                global1.custom = 1234

                with ctxt0:
                    self.assertEquals(1234, int(global0.custom))
                self.assertEquals(1234, int(global1.custom))

                # Now create a new context with the old global
                with JSContext(global1) as ctxt2:
                    ctxt2.securityToken = ctxt1.securityToken

                    with ctxt1:
                        self.assertEquals(1234, int(global1.custom))
                        
                    self.assertEquals(1234, int(global2.custom))

    def _testSecurityChecks(self):
        with JSContext() as env1:
            env1.securityToken = "foo"

            # Create a function in env1.
            env1.eval("spy=function(){return spy;}")

            spy = env1.locals.spy

            self.assert_(isinstance(spy, _PyV8.JSFunction))

            # Create another function accessing global objects.
            env1.eval("spy2=function(){return 123;}")

            spy2 = env1.locals.spy2

            self.assert_(isinstance(spy2, _PyV8.JSFunction))

            # Switch to env2 in the same domain and invoke spy on env2.
            env2 = JSContext()

            env2.securityToken = "foo"

            with env2:
                result = spy.apply(env2.locals)

                self.assert_(isinstance(result, _PyV8.JSFunction))

            env2.securityToken = "bar"

            # Call cross_domain_call, it should throw an exception
            with env2:
                self.assertRaises(JSError, spy2.apply, env2.locals)

    def _testCrossDomainDelete(self):
        with JSContext() as env1:
            env2 = JSContext()

            # Set to the same domain.
            env1.securityToken = "foo"
            env2.securityToken = "foo"

            env1.locals.prop = 3

            env2.locals.env1 = env1.locals

            # Change env2 to a different domain and delete env1.prop.
            #env2.securityToken = "bar"

            self.assertEquals(3, int(env1.eval("prop")))

            print env1.eval("env1")

            with env2:
                self.assertEquals(3, int(env2.eval("this.env1.prop")))
                self.assertEquals("false", str(e.eval("delete env1.prop")))

            # Check that env1.prop still exists.
            self.assertEquals(3, int(env1.locals.prop))

class TestWrapper(unittest.TestCase):
    def testObject(self):
        with JSContext() as ctxt:
            o = ctxt.eval("new Object()")

            self.assert_(hash(o) > 0)

            o1 = o.clone()

            self.assertEquals(hash(o1), hash(o))
            self.assert_(o != o1)

    def testAutoConverter(self):
        with JSContext() as ctxt:
            ctxt.eval("""
                var_i = 1;
                var_f = 1.0;
                var_s = "test";
                var_b = true;
                var_s_obj = new String("test");
                var_b_obj = new Boolean(true);
                var_f_obj = new Number(1.5);
            """)

            vars = ctxt.locals

            var_i = vars.var_i

            self.assert_(var_i)
            self.assertEquals(1, int(var_i))

            var_f = vars.var_f

            self.assert_(var_f)
            self.assertEquals(1.0, float(vars.var_f))

            var_s = vars.var_s
            self.assert_(var_s)
            self.assertEquals("test", str(vars.var_s))

            var_b = vars.var_b
            self.assert_(var_b)
            self.assert_(bool(var_b))

            self.assertEquals("test", vars.var_s_obj)
            self.assert_(vars.var_b_obj)
            self.assertEquals(1.5, vars.var_f_obj)

            attrs = dir(ctxt.locals)

            self.assert_(attrs)
            self.assert_("var_i" in attrs)
            self.assert_("var_f" in attrs)
            self.assert_("var_s" in attrs)
            self.assert_("var_b" in attrs)
            self.assert_("var_s_obj" in attrs)
            self.assert_("var_b_obj" in attrs)
            self.assert_("var_f_obj" in attrs)

    def testExactConverter(self):
        class MyInteger(int, JSClass):
            pass

        class MyString(str, JSClass):
            pass

        class MyUnicode(unicode, JSClass):
            pass

        class MyDateTime(time, JSClass):
            pass

        class Global(JSClass):
            var_bool = True
            var_int = 1
            var_float = 1.0
            var_str = 'str'
            var_unicode = u'unicode'
            var_datetime = datetime.now()
            var_date = date.today()
            var_time = time()

            var_myint = MyInteger()
            var_mystr = MyString('mystr')
            var_myunicode = MyUnicode('myunicode')
            var_mytime = MyDateTime()

        with JSContext(Global()) as ctxt:
            typename = ctxt.eval("(function (name) { return this[name].constructor.name; })")
            typeof = ctxt.eval("(function (name) { return typeof(this[name]); })")

            self.assertEquals('Boolean', typename('var_bool'))
            self.assertEquals('Number', typename('var_int'))
            self.assertEquals('Number', typename('var_float'))
            self.assertEquals('String', typename('var_str'))
            self.assertEquals('String', typename('var_unicode'))
            self.assertEquals('Date', typename('var_datetime'))
            self.assertEquals('Date', typename('var_date'))
            self.assertEquals('Date', typename('var_time'))

            self.assertEquals('MyInteger', typename('var_myint'))
            self.assertEquals('MyString', typename('var_mystr'))
            self.assertEquals('MyUnicode', typename('var_myunicode'))
            self.assertEquals('MyDateTime', typename('var_mytime'))

            self.assertEquals('object', typeof('var_myint'))
            self.assertEquals('object', typeof('var_mystr'))
            self.assertEquals('object', typeof('var_myunicode'))
            self.assertEquals('object', typeof('var_mytime'))

    def testJavascriptWrapper(self):
        with JSContext() as ctxt:
            self.assertEquals(type(None), type(ctxt.eval("null")))
            self.assertEquals(type(None), type(ctxt.eval("undefined")))
            self.assertEquals(bool, type(ctxt.eval("true")))
            self.assertEquals(str, type(ctxt.eval("'test'")))
            self.assertEquals(int, type(ctxt.eval("123")))
            self.assertEquals(float, type(ctxt.eval("3.14")))
            self.assertEquals(datetime, type(ctxt.eval("new Date()")))
            self.assertEquals(JSArray, type(ctxt.eval("[1, 2, 3]")))
            self.assertEquals(JSFunction, type(ctxt.eval("(function() {})")))
            self.assertEquals(JSObject, type(ctxt.eval("new Object()")))

    def testPythonWrapper(self):
        with JSContext() as ctxt:
            typeof = ctxt.eval("(function type(value) { return typeof value; })")
            protoof = ctxt.eval("(function protoof(value) { return Object.prototype.toString.apply(value); })")

            self.assertEquals('[object Null]', protoof(None))
            self.assertEquals('boolean', typeof(True))
            self.assertEquals('number', typeof(123))
            self.assertEquals('number', typeof(123l))
            self.assertEquals('number', typeof(3.14))
            self.assertEquals('string', typeof('test'))
            self.assertEquals('string', typeof(u'test'))

            self.assertEquals('[object Date]', protoof(datetime.now()))
            self.assertEquals('[object Date]', protoof(date.today()))
            self.assertEquals('[object Date]', protoof(time()))

            def test():
                pass

            self.assertEquals('[object Function]', protoof(abs))
            self.assertEquals('[object Function]', protoof(test))
            self.assertEquals('[object Function]', protoof(self.testPythonWrapper))
            self.assertEquals('[object Function]', protoof(int))

    def testFunction(self):
        with JSContext() as ctxt:
            func = ctxt.eval("""
                (function ()
                {
                    function a()
                    {
                        return "abc";
                    }

                    return a();
                })
                """)

            self.assertEquals("abc", str(func()))
            self.assert_(func != None)
            self.assertFalse(func == None)

            func = ctxt.eval("(function test() {})")

            self.assertEquals("test", func.name)
            self.assertEquals("", func.resname)
            self.assertEquals(0, func.linenum)
            self.assertEquals(14, func.colnum)
            self.assertEquals(0, func.lineoff)
            self.assertEquals(0, func.coloff)
            
            #TODO fix me, why the setter doesn't work?

            func.name = "hello"

            #self.assertEquals("hello", func.name)

    def testCall(self):
        class Hello(object):
            def __call__(self, name):
                return "hello " + name

        class Global(JSClass):
            hello = Hello()

        with JSContext(Global()) as ctxt:
            self.assertEquals("hello flier", ctxt.eval("hello('flier')"))

    def testJSFunction(self):
        with JSContext() as ctxt:
            hello = ctxt.eval("(function (name) { return 'hello ' + name; })")

            self.assert_(isinstance(hello, _PyV8.JSFunction))
            self.assertEquals("hello flier", hello('flier'))
            self.assertEquals("hello flier", hello.invoke(['flier']))

            obj = ctxt.eval("({ 'name': 'flier', 'hello': function (name) { return 'hello ' + name + ' from ' + this.name; }})")
            hello = obj.hello
            self.assert_(isinstance(hello, JSFunction))
            self.assertEquals("hello flier from flier", hello('flier'))

            tester = ctxt.eval("({ 'name': 'tester' })")
            self.assertEquals("hello flier from tester", hello.invoke(tester, ['flier']))
            self.assertEquals("hello flier from json", hello.apply({ 'name': 'json' }, ['flier']))

    def testJSError(self):
        with JSContext() as ctxt:
            try:
                ctxt.eval('throw "test"')
                self.fail()
            except:
                self.assert_(JSError, sys.exc_type)

    def testErrorInfo(self):
        with JSContext() as ctxt:
            with JSEngine() as engine:
                try:
                    engine.compile("""
                        function hello()
                        {
                            throw Error("hello world");
                        }

                        hello();""", "test", 10, 10).run()
                    self.fail()
                except JSError, e:
                    self.assert_(str(e).startswith('JSError: Error: hello world ( test @ 14 : 34 )  ->'))
                    self.assertEqual("Error", e.name)
                    self.assertEqual("hello world", e.message)
                    self.assertEqual("test", e.scriptName)
                    self.assertEqual(14, e.lineNum)
                    self.assertEqual(102, e.startPos)
                    self.assertEqual(103, e.endPos)
                    self.assertEqual(34, e.startCol)
                    self.assertEqual(35, e.endCol)
                    self.assertEqual('throw Error("hello world");', e.sourceLine.strip())
                    self.assertEqual('Error: hello world\n' +
                                     '    at Error (unknown source)\n' +
                                     '    at hello (test:14:35)\n' +
                                     '    at test:17:25', e.stackTrace)

    def testParseStack(self):
        self.assertEquals([
            ('Error', 'unknown source', None, None),
            ('test', 'native', None, None),
            ('<anonymous>', 'test0', 3, 5),
            ('f', 'test1', 2, 19),
            ('g', 'test2', 1, 15),
            (None, 'test3', 1, None),
            (None, 'test3', 1, 1),
        ], JSError.parse_stack("""Error: err
            at Error (unknown source)
            at test (native)
            at new <anonymous> (test0:3:5)
            at f (test1:2:19)
            at g (test2:1:15)
            at test3:1
            at test3:1:1"""))

    def testStackTrace(self):
        class Global(JSClass):
            def GetCurrentStackTrace(self, limit):
                return JSStackTrace.GetCurrentStackTrace(4, JSStackTrace.Options.Detailed)

        with JSContext(Global()) as ctxt:
            st = ctxt.eval("""
                function a()
                {
                    return GetCurrentStackTrace(10);
                }
                function b()
                {
                    return eval("a()");
                }
                function c()
                {
                    return new b();
                }
            c();""", "test")

            self.assertEquals(4, len(st))
            self.assertEquals("\tat a (test:4:28)\n\tat (eval)\n\tat b (test:8:28)\n\tat c (test:12:28)\n", str(st))
            self.assertEquals("test.a (4:28)\n. (1:1) eval\ntest.b (8:28) constructor\ntest.c (12:28)",
                              "\n".join(["%s.%s (%d:%d)%s%s" % (
                                f.scriptName, f.funcName, f.lineNum, f.column,
                                ' eval' if f.isEval else '',
                                ' constructor' if f.isConstructor else '') for f in st]))

    def testPythonException(self):
        class Global(JSClass):
            def raiseException(self):
                raise RuntimeError("Hello")

        with JSContext(Global()) as ctxt:
            r = ctxt.eval("""
                msg ="";
                try
                {
                    this.raiseException()
                }
                catch(e)
                {
                    msg += "catch " + e + ";";
                }
                finally
                {
                    msg += "finally";
                }""")
            self.assertEqual("catch Error: Hello;finally", str(ctxt.locals.msg))

    def testExceptionMapping(self):
        class TestException(Exception):
            pass

        class Global(JSClass):
            def raiseIndexError(self):
                return [1, 2, 3][5]

            def raiseAttributeError(self):
                None.hello()

            def raiseSyntaxError(self):
                eval("???")

            def raiseTypeError(self):
                int(sys)

            def raiseNotImplementedError(self):
                raise NotImplementedError("Not support")

            def raiseExceptions(self):
                raise TestException()

        with JSContext(Global()) as ctxt:
            ctxt.eval("try { this.raiseIndexError(); } catch (e) { msg = e; }")

            self.assertEqual("RangeError: list index out of range", str(ctxt.locals.msg))

            ctxt.eval("try { this.raiseAttributeError(); } catch (e) { msg = e; }")

            self.assertEqual("ReferenceError: 'NoneType' object has no attribute 'hello'", str(ctxt.locals.msg))

            ctxt.eval("try { this.raiseSyntaxError(); } catch (e) { msg = e; }")

            self.assertEqual("SyntaxError: invalid syntax", str(ctxt.locals.msg))

            ctxt.eval("try { this.raiseTypeError(); } catch (e) { msg = e; }")

            self.assertEqual("TypeError: int() argument must be a string or a number, not 'module'", str(ctxt.locals.msg))

            ctxt.eval("try { this.raiseNotImplementedError(); } catch (e) { msg = e; }")

            self.assertEqual("Error: Not support", str(ctxt.locals.msg))

            self.assertRaises(TestException, ctxt.eval, "this.raiseExceptions();")

    def testArray(self):
        with JSContext() as ctxt:
            array = ctxt.eval("""
                var array = new Array();

                for (i=0; i<10; i++)
                {
                    array[i] = 10-i;
                }

                array;
                """)

            self.assert_(isinstance(array, _PyV8.JSArray))
            self.assertEqual(10, len(array))

            self.assert_(5 in array)
            self.assertFalse(15 in array)

            l = list(array)

            self.assertEqual(10, len(l))

            for i in xrange(10):
                self.assertEqual(10-i, array[i])
                self.assertEqual(10-i, l[i])

            array[5] = 0

            self.assertEqual(0, array[5])

            del array[5]

            self.assertEquals(None, array[5])

            ctxt.locals.array1 = JSArray(5)
            ctxt.locals.array2 = JSArray([1, 2, 3, 4, 5])

            for i in xrange(len(ctxt.locals.array2)):
                ctxt.locals.array1[i] = ctxt.locals.array2[i] * 10

            ctxt.eval("""
                var sum = 0;

                for (i=0; i<array1.length; i++)
                    sum += array1[i]

                for (i=0; i<array2.length; i++)
                    sum += array2[i]
                """)

            self.assertEqual(165, ctxt.locals.sum)

            ctxt.locals.array3 = [1, 2, 3, 4, 5]
            self.assert_(ctxt.eval('array3[1] === 2'))
            self.assert_(ctxt.eval('array3[9] === undefined'))

            cases = {
                "a = Array(7); for(i=0; i<a.length; i++) a[i] = i; a[3] = undefined; a[a.length-1]; a" : ("0,1,2,,4,5,6", [0, 1, 2, None, 4, 5, 6]),
                "a = Array(7); for(i=0; i<a.length - 1; i++) a[i] = i; a[a.length-1]; a" : ("0,1,2,3,4,5,", [0, 1, 2, 3, 4, 5, None]),
                "a = Array(7); for(i=1; i<a.length; i++) a[i] = i; a[a.length-1]; a" : (",1,2,3,4,5,6", [None, 1, 2, 3, 4, 5, 6])
            }

            for code, (keys, values) in cases.items():
                array = ctxt.eval(code)

                self.assertEquals(keys, str(array))
                self.assertEquals(values, [array[i] for i in range(len(array))])

    def testMultiDimArray(self):
        with JSContext() as ctxt:
            ret = ctxt.eval("""
                ({
                    'test': function(){
                        return  [
                            [ 1, 'abla' ],
                            [ 2, 'ajkss' ],
                        ]
                    }
                })
                """).test()

            self.assertEquals([[1, 'abla'], [2, 'ajkss']], convert(ret))

    def testLazyConstructor(self):
        class Globals(JSClass):
            def __init__(self):
                self.array=JSArray([1,2,3])

        with JSContext(Globals()) as ctxt:
            self.assertEqual(2, ctxt.eval("""array[1]"""))

    def testForEach(self):
        class NamedClass(object):
            foo = 1

            def __init__(self):
                self.bar = 2

            @property
            def foobar(self):
                return self.foo + self.bar

        def gen(x):
            for i in range(x):
                yield i

        with JSContext() as ctxt:
            func = ctxt.eval("""(function (k) {
                var result = [];
                for (var prop in k) {
                  result.push(prop);
                }
                return result;
            })""")

            self.assertEquals(["bar", "foo", "foobar"], list(func(NamedClass())))
            self.assertEquals(["0", "1", "2"], list(func([1, 2, 3])))
            self.assertEquals(["0", "1", "2"], list(func((1, 2, 3))))
            self.assertEquals(["1", "2", "3"], list(func({1:1, 2:2, 3:3})))

            self.assertEquals(["0", "1", "2"], list(func(gen(3))))

    def testDict(self):
        import UserDict

        with JSContext() as ctxt:
            obj = ctxt.eval("var r = { 'a' : 1, 'b' : 2 }; r")

            self.assertEqual(1, obj.a)
            self.assertEqual(2, obj.b)

            self.assertEqual({ 'a' : 1, 'b' : 2 }, dict(obj))

            self.assertEqual({ 'a': 1,
                               'b': [1, 2, 3],
                               'c': { 'str' : 'goofy',
                                      'float' : 1.234,
                                      'obj' : { 'name': 'john doe' }},
                               'd': True,
                               'e': None },
                             convert(ctxt.eval("""var x =
                             { a: 1,
                               b: [1, 2, 3],
                               c: { str: 'goofy',
                                    float: 1.234,
                                    obj: { name: 'john doe' }},
                               d: true,
                               e: null }; x""")))

    def testDate(self):
        with JSContext() as ctxt:
            now1 = ctxt.eval("new Date();")

            self.assert_(now1)

            now2 = datetime.utcnow()

            delta = now2 - now1 if now2 > now1 else now1 - now2

            self.assert_(delta < timedelta(seconds=1))

            func = ctxt.eval("(function (d) { return d.toString(); })")

            now = datetime.now()

            self.assert_(str(func(now)).startswith(now.strftime("%a %b %d %Y %H:%M:%S")))

    def testUnicode(self):
        with JSContext() as ctxt:
            self.assertEquals(u"人", unicode(ctxt.eval(u"\"人\""), "utf-8"))
            self.assertEquals(u"é", unicode(ctxt.eval(u"\"é\""), "utf-8"))

            func = ctxt.eval("(function (msg) { return msg.length; })")

            self.assertEquals(2, func(u"测试"))

    def testClassicStyleObject(self):
        class FileSystemWarpper:
            @property
            def cwd(self):
                return os.getcwd()

        class Global:
            @property
            def fs(self):
                return FileSystemWarpper()

        with JSContext(Global()) as ctxt:
            self.assertEquals(os.getcwd(), ctxt.eval("fs.cwd"))

    def testRefCount(self):
        count = sys.getrefcount(None)

        class Global(JSClass):
            pass

        with JSContext(Global()) as ctxt:
            ctxt.eval("""
                var none = null;
            """)

            self.assertEquals(count+1, sys.getrefcount(None))

            ctxt.eval("""
                var none = null;
            """)

            self.assertEquals(count+1, sys.getrefcount(None))

    def testProperty(self):
        class Global(JSClass):
            def __init__(self, name):
                self._name = name
            def getname(self):
                return self._name
            def setname(self, name):
                self._name = name
            def delname(self):
                self._name = 'deleted'

            name = property(getname, setname, delname)

        g = Global('world')

        with JSContext(g) as ctxt:
            self.assertEquals('world', ctxt.eval("name"))
            self.assertEquals('flier', ctxt.eval("this.name = 'flier';"))
            self.assertEquals('flier', ctxt.eval("name"))
            self.assert_(ctxt.eval("delete name"))
            ###
            # FIXME replace the global object with Python object
            #
            #self.assertEquals('deleted', ctxt.eval("name"))
            #ctxt.eval("__defineGetter__('name', function() { return 'fixed'; });")
            #self.assertEquals('fixed', ctxt.eval("name"))

    def testGetterAndSetter(self):
        class Global(JSClass):
           def __init__(self, testval):
               self.testval = testval

        with JSContext(Global("Test Value A")) as ctxt:
           self.assertEquals("Test Value A", ctxt.locals.testval)
           ctxt.eval("""
               this.__defineGetter__("test", function() {
                   return this.testval;
               });
               this.__defineSetter__("test", function(val) {
                   this.testval = val;
               });
           """)
           self.assertEquals("Test Value A",  ctxt.locals.test)

           ctxt.eval("test = 'Test Value B';")

           self.assertEquals("Test Value B",  ctxt.locals.test)

    def testDestructor(self):
        import gc

        owner = self
        owner.deleted = False

        class Hello(object):
            def say(self):
                pass

            def __del__(self):
                owner.deleted = True

        def test():
            with JSContext() as ctxt:
                fn = ctxt.eval("(function (obj) { obj.say(); })")

                obj = Hello()

                self.assert_(2, sys.getrefcount(obj))

                fn(obj)

                self.assert_(3, sys.getrefcount(obj))

                del obj

        test()

        self.assertFalse(owner.deleted)

        JSEngine.collect()
        gc.collect()

        self.assert_(self.deleted)

    def testNullInString(self):
        with JSContext() as ctxt:
            fn = ctxt.eval("(function (s) { return s; })")

            self.assertEquals("hello \0 world", fn("hello \0 world"))

    def testLivingObjectCache(self):
        class Global(JSClass):
            i = 1
            b = True
            o = object()

        with JSContext(Global()) as ctxt:
            self.assert_(ctxt.eval("i == i"))
            self.assert_(ctxt.eval("b == b"))
            self.assert_(ctxt.eval("o == o"))

    def testNamedSetter(self):
        class Obj(JSClass):
            @property
            def p(self):
                return self._p

            @p.setter
            def p(self, value):
                self._p = value

        class Global(JSClass):
            def __init__(self):
                self.obj = Obj()
                self.d = {}
                self.p = None

        with JSContext(Global()) as ctxt:
            ctxt.eval("""
            x = obj;
            x.y = 10;
            x.p = 10;
            d.y = 10;
            """)
            self.assertEquals(10, ctxt.eval("obj.y"))
            self.assertEquals(10, ctxt.eval("obj.p"))
            self.assertEquals(10, ctxt.locals.d['y'])

    def testWatch(self):
        class Obj(JSClass):
            def __init__(self):
                self.p = 1

        class Global(JSClass):
            def __init__(self):
                self.o = Obj()

        with JSContext(Global()) as ctxt:
            ctxt.eval("""
            o.watch("p", function (id, oldval, newval) {
                return oldval + newval;
            });
            """)

            self.assertEquals(1, ctxt.eval("o.p"))

            ctxt.eval("o.p = 2;")

            self.assertEquals(3, ctxt.eval("o.p"))

            ctxt.eval("delete o.p;")

            self.assertEquals(None, ctxt.eval("o.p"))

            ctxt.eval("o.p = 2;")

            self.assertEquals(2, ctxt.eval("o.p"))

            ctxt.eval("o.unwatch('p');")

            ctxt.eval("o.p = 1;")

            self.assertEquals(1, ctxt.eval("o.p"))

    def testReferenceError(self):
        class Global(JSClass):
            def __init__(self):
                self.s = self

        with JSContext(Global()) as ctxt:
            self.assertRaises(ReferenceError, ctxt.eval, 'x')

            self.assert_(ctxt.eval("typeof(x) === 'undefined'"))

            self.assert_(ctxt.eval("typeof(String) === 'function'"))

            self.assert_(ctxt.eval("typeof(s.String) === 'undefined'"))

            self.assert_(ctxt.eval("typeof(s.z) === 'undefined'"))

    def testRaiseExceptionInGetter(self):
        class Document(JSClass):
            def __getattr__(self, name):
                if name == 'y':
                    raise TypeError()

                return JSClass.__getattr__(self, name)

        class Global(JSClass):
            def __init__(self):
                self.document = Document()

        with JSContext(Global()) as ctxt:
            self.assertEquals(None, ctxt.eval('document.x'))
            self.assertRaises(TypeError, ctxt.eval, 'document.y')

class TestMultithread(unittest.TestCase):
    def testLocker(self):
        self.assertFalse(JSLocker.active)
        self.assertFalse(JSLocker.locked)

        with JSLocker() as outter_locker:
            self.assertTrue(JSLocker.active)
            self.assertTrue(JSLocker.locked)

            self.assertTrue(outter_locker)

            with JSLocker() as inner_locker:
                self.assertTrue(JSLocker.locked)

                self.assertTrue(outter_locker)
                self.assertTrue(inner_locker)

                with JSUnlocker() as unlocker:
                    self.assertFalse(JSLocker.locked)

                    self.assertTrue(outter_locker)
                    self.assertTrue(inner_locker)

                self.assertTrue(JSLocker.locked)

        self.assertTrue(JSLocker.active)
        self.assertFalse(JSLocker.locked)

        locker = JSLocker()

        with JSContext():
            self.assertRaises(RuntimeError, locker.__enter__)
            self.assertRaises(RuntimeError, locker.__exit__, None, None, None)

        del locker

    def testMultiPythonThread(self):
        import time, threading

        class Global:
            count = 0
            started = threading.Event()
            finished = threading.Semaphore(0)

            def sleep(self, ms):
                time.sleep(ms / 1000.0)

                self.count += 1

        g = Global()

        def run():
            with JSContext(g) as ctxt:
                ctxt.eval("""
                    started.wait();

                    for (i=0; i<10; i++)
                    {
                        sleep(100);
                    }

                    finished.release();
                """)

        threading.Thread(target=run).start()

        now = time.time()

        self.assertEqual(0, g.count)

        g.started.set()
        g.finished.acquire()

        self.assertEqual(10, g.count)

        self.assert_((time.time() - now) >= 1)

    def testMultiJavascriptThread(self):
        import time, threading

        class Global:
            result = []

            def add(self, value):
                with JSUnlocker():
                    time.sleep(0.1)

                    self.result.append(value)

        g = Global()

        def run():
            with JSContext(g) as ctxt:
                ctxt.eval("""
                    for (i=0; i<10; i++)
                        add(i);
                """)

        threads = [threading.Thread(target=run), threading.Thread(target=run)]

        with JSLocker():
            for t in threads: t.start()

        for t in threads: t.join()

        self.assertEqual(20, len(g.result))

    def _testPreemptionJavascriptThreads(self):
        import time, threading

        class Global:
            result = []

            def add(self, value):
                # we use preemption scheduler to switch between threads
                # so, just comment the JSUnlocker
                #
                # with JSUnlocker() as unlocker:
                time.sleep(0.1)

                self.result.append(value)

        g = Global()

        def run():
            with JSContext(g) as ctxt:
                ctxt.eval("""
                    for (i=0; i<10; i++)
                        add(i);
                """)

        threads = [threading.Thread(target=run), threading.Thread(target=run)]

        with JSLocker() as locker:
            JSLocker.startPreemption(100)

            for t in threads: t.start()

        for t in threads: t.join()

        self.assertEqual(20, len(g.result))

class TestEngine(unittest.TestCase):
    def testClassProperties(self):
        with JSContext() as ctxt:
            self.assert_(str(JSEngine.version).startswith("3."))
            self.assertFalse(JSEngine.dead)

    def testCompile(self):
        with JSContext() as ctxt:
            with JSEngine() as engine:
                s = engine.compile("1+2")

                self.assert_(isinstance(s, _PyV8.JSScript))

                self.assertEquals("1+2", s.source)
                self.assertEquals(3, int(s.run()))

                self.assertRaises(SyntaxError, engine.compile, "1+")

    def testPrecompile(self):
        with JSContext() as ctxt:
            with JSEngine() as engine:
                data = engine.precompile("1+2")

                self.assert_(data)
                self.assertEquals(28, len(data))

                s = engine.compile("1+2", precompiled=data)

                self.assert_(isinstance(s, _PyV8.JSScript))

                self.assertEquals("1+2", s.source)
                self.assertEquals(3, int(s.run()))

                self.assertRaises(SyntaxError, engine.precompile, "1+")

    def testUnicodeSource(self):
        class Global(JSClass):
            var = u'测试'

            def __getattr__(self, name):
                if (name.decode('utf-8')) == u'变量':
                    return self.var

                return JSClass.__getattr__(self, name)

        g = Global()

        with JSContext(g) as ctxt:
            with JSEngine() as engine:
                src = u"""
                function 函数() { return 变量.length; }

                函数();
                """

                data = engine.precompile(src)

                self.assert_(data)
                self.assertEquals(48, len(data))

                s = engine.compile(src, precompiled=data)

                self.assert_(isinstance(s, _PyV8.JSScript))

                self.assertEquals(src.encode('utf-8'), s.source)
                self.assertEquals(2, s.run())

                self.assert_(hasattr(ctxt.locals, u'函数'.encode('utf-8')))

                func = getattr(ctxt.locals, u'函数'.encode('utf-8'))

                self.assert_(isinstance(func, _PyV8.JSFunction))

                self.assertEquals(u'函数'.encode('utf-8'), func.name)
                self.assertEquals("", func.resname)
                self.assertEquals(1, func.linenum)
                self.assertEquals(0, func.lineoff)
                self.assertEquals(0, func.coloff)

                setattr(ctxt.locals, u'变量'.encode('utf-8'), u'测试长字符串')

                self.assertEquals(6, func())

    def testExtension(self):
        extSrc = """function hello(name) { return "hello " + name + " from javascript"; }"""
        extJs = JSExtension("hello/javascript", extSrc)

        self.assert_(extJs)
        self.assertEqual("hello/javascript", extJs.name)
        self.assertEqual(extSrc, extJs.source)
        self.assertFalse(extJs.autoEnable)
        self.assertTrue(extJs.registered)

        TestEngine.extJs = extJs

        with JSContext(extensions=['hello/javascript']) as ctxt:
            self.assertEqual("hello flier from javascript", ctxt.eval("hello('flier')"))

        # test the auto enable property

        with JSContext() as ctxt:
            self.assertRaises(ReferenceError, ctxt.eval, "hello('flier')")

        extJs.autoEnable = True
        self.assertTrue(extJs.autoEnable)

        with JSContext() as ctxt:
            self.assertEqual("hello flier from javascript", ctxt.eval("hello('flier')"))

        extJs.autoEnable = False
        self.assertFalse(extJs.autoEnable)

        with JSContext() as ctxt:
            self.assertRaises(ReferenceError, ctxt.eval, "hello('flier')")

    def testNativeExtension(self):
        extSrc = "native function hello();"
        extPy = JSExtension("hello/python", extSrc, lambda func: lambda name: "hello " + name + " from python", register=False)
        self.assert_(extPy)
        self.assertEqual("hello/python", extPy.name)
        self.assertEqual(extSrc, extPy.source)
        self.assertFalse(extPy.autoEnable)
        self.assertFalse(extPy.registered)
        extPy.register()
        self.assertTrue(extPy.registered)

        TestEngine.extPy = extPy

        with JSContext(extensions=['hello/python']) as ctxt:
            self.assertEqual("hello flier from python", ctxt.eval("hello('flier')"))

    def _testSerialize(self):
        data = None

        self.assertFalse(JSContext.entered)

        with JSContext() as ctxt:
            self.assert_(JSContext.entered)

            #ctxt.eval("function hello(name) { return 'hello ' + name; }")

            data = JSEngine.serialize()

        self.assert_(data)
        self.assert_(len(data) > 0)

        self.assertFalse(JSContext.entered)

        #JSEngine.deserialize()

        self.assert_(JSContext.entered)

        self.assertEquals('hello flier', JSContext.current.eval("hello('flier');"))

    def testEval(self):
        with JSContext() as ctxt:
            self.assertEquals(3, int(ctxt.eval("1+2")))

    def testGlobal(self):
        class Global(JSClass):
            version = "1.0"

        with JSContext(Global()) as ctxt:
            vars = ctxt.locals

            # getter
            self.assertEquals(Global.version, str(vars.version))
            self.assertEquals(Global.version, str(ctxt.eval("version")))

            self.assertRaises(ReferenceError, ctxt.eval, "nonexists")

            # setter
            self.assertEquals(2.0, float(ctxt.eval("version = 2.0")))

            self.assertEquals(2.0, float(vars.version))

    def testThis(self):
        class Global(JSClass):
            version = 1.0

        with JSContext(Global()) as ctxt:
            self.assertEquals("[object Global]", str(ctxt.eval("this")))

            self.assertEquals(1.0, float(ctxt.eval("this.version")))

    def testObjectBuildInMethods(self):
        class Global(JSClass):
            version = 1.0

        with JSContext(Global()) as ctxt:
            self.assertEquals("[object Global]", str(ctxt.eval("this.toString()")))
            self.assertEquals("[object Global]", str(ctxt.eval("this.toLocaleString()")))
            self.assertEquals(Global.version, float(ctxt.eval("this.valueOf()").version))

            self.assert_(bool(ctxt.eval("this.hasOwnProperty(\"version\")")))

            self.assertFalse(ctxt.eval("this.hasOwnProperty(\"nonexistent\")"))

    def testPythonWrapper(self):
        class Global(JSClass):
            s = [1, 2, 3]
            d = {'a': {'b': 'c'}, 'd': ['e', 'f']}

        g = Global()

        with JSContext(g) as ctxt:
            ctxt.eval("""
                s[2] = s[1] + 2;
                s[0] = s[1];
                delete s[1];
            """)
            self.assertEquals([2, 4], g.s)
            self.assertEquals('c', ctxt.eval("d.a.b"))
            self.assertEquals(['e', 'f'], ctxt.eval("d.d"))
            ctxt.eval("""
                d.a.q = 4
                delete d.d
            """)
            self.assertEquals(4, g.d['a']['q'])
            self.assertEquals(None, ctxt.eval("d.d"))

    def testMemoryAllocationCallback(self):
        alloc = {}

        def callback(space, action, size):
            alloc[(space, action)] = alloc.setdefault((space, action), 0) + size

        JSEngine.setMemoryAllocationCallback(callback)

        with JSContext() as ctxt:
            self.assertEquals({}, alloc)

            ctxt.eval("var o = new Array(1000);")

            alloc.has_key((JSObjectSpace.Code, JSAllocationAction.alloc))

        JSEngine.setMemoryAllocationCallback(None)

class TestDebug(unittest.TestCase):
    def setUp(self):
        self.engine = JSEngine()

    def tearDown(self):
        del self.engine

    events = []

    def processDebugEvent(self, event):
        try:
            logging.debug("receive debug event: %s", repr(event))

            self.events.append(repr(event))
        except:
            logging.error("fail to process debug event")
            logging.debug(traceback.extract_stack())

    def testEventDispatch(self):
        debugger = JSDebugger()

        self.assert_(not debugger.enabled)

        debugger.onBreak = lambda evt: self.processDebugEvent(evt)
        debugger.onException = lambda evt: self.processDebugEvent(evt)
        debugger.onNewFunction = lambda evt: self.processDebugEvent(evt)
        debugger.onBeforeCompile = lambda evt: self.processDebugEvent(evt)
        debugger.onAfterCompile = lambda evt: self.processDebugEvent(evt)

        with JSContext() as ctxt:
            debugger.enabled = True

            self.assertEquals(3, int(ctxt.eval("function test() { text = \"1+2\"; return eval(text) } test()")))

            debugger.enabled = False

            self.assertRaises(JSError, JSContext.eval, ctxt, "throw 1")

            self.assert_(not debugger.enabled)

        self.assertEquals(4, len(self.events))

class TestProfile(unittest.TestCase):
    def _testStart(self):
        self.assertFalse(profiler.started)

        profiler.start()

        self.assert_(profiler.started)

        profiler.stop()

        self.assertFalse(profiler.started)

    def _testResume(self):
        self.assert_(profiler.paused)

        self.assertEquals(profiler.Modules.cpu, profiler.modules)

        profiler.resume()

        profiler.resume(profiler.Modules.heap)

        # TODO enable profiler with resume
        #self.assertFalse(profiler.paused)


class TestAST(unittest.TestCase):

    class Checker(object):
        def __init__(self, testcase):
            self.testcase = testcase
            self.called = 0

        def __getattr__(self, name):
            return getattr(self.testcase, name)

        def test(self, script):
            with JSContext() as ctxt:
                JSEngine().compile(script).visit(self)

            return self.called

        def onProgram(self, prog):
            self.ast = prog.toAST()
            self.json = json.loads(prog.toJSON())

            for decl in prog.scope.declarations:
                decl.visit(self)

            for stmt in prog.body:
                stmt.visit(self)

        def onBlock(self, block):
            for stmt in block.statements:
                stmt.visit(self)

        def onExpressionStatement(self, stmt):
            stmt.expression.visit(self)

            #print type(stmt.expression), stmt.expression

    def testBlock(self):
        class BlockChecker(TestAST.Checker):
            def onBlock(self, stmt):
                self.called += 1

                self.assertEquals(AST.NodeType.Block, stmt.type)

                self.assert_(stmt.initializerBlock)
                self.assertFalse(stmt.anonymous)

                target = stmt.breakTarget
                self.assert_(target)
                self.assertFalse(target.bound)
                self.assert_(target.unused)
                self.assertFalse(target.linked)

                self.assertEquals(2, len(stmt.statements))

                self.assertEquals(['%InitializeVarGlobal("i", 0);', '%InitializeVarGlobal("j", 0);'], [str(s) for s in stmt.statements])

        checker = BlockChecker(self)
        self.assertEquals(1, checker.test("var i, j;"))
        self.assertEquals("""FUNC
. NAME ""
. INFERRED NAME ""
. DECLS
. . VAR "i"
. . VAR "j"
. BLOCK INIT
. . CALL RUNTIME  InitializeVarGlobal
. . . LITERAL "i"
. . . LITERAL 0
. . CALL RUNTIME  InitializeVarGlobal
. . . LITERAL "j"
. . . LITERAL 0
""", checker.ast)
        self.assertEquals([u'FunctionLiteral', {u'name': u''},
            [u'Declaration', {u'mode': u'VAR'},
                [u'Variable', {u'name': u'i'}]
            ], [u'Declaration', {u'mode':u'VAR'},
                [u'Variable', {u'name': u'j'}]
            ], [u'Block',
                [u'ExpressionStatement', [u'CallRuntime', {u'name': u'InitializeVarGlobal'},
                    [u'Literal', {u'handle':u'i'}],
                    [u'Literal', {u'handle': 0}]]],
                [u'ExpressionStatement', [u'CallRuntime', {u'name': u'InitializeVarGlobal'},
                    [u'Literal', {u'handle': u'j'}],
                    [u'Literal', {u'handle': 0}]]]
            ]
        ], checker.json)

    def testIfStatement(self):
        class IfStatementChecker(TestAST.Checker):
            def onIfStatement(self, stmt):
                self.called += 1

                self.assert_(stmt)
                self.assertEquals(AST.NodeType.IfStatement, stmt.type)

                self.assertEquals(7, stmt.pos)
                stmt.pos = 100
                self.assertEquals(100, stmt.pos)

                self.assert_(stmt.hasThenStatement)
                self.assert_(stmt.hasElseStatement)

                self.assertEquals("((value % 2) == 0)", str(stmt.condition))
                self.assertEquals("{ s = \"even\"; }", str(stmt.thenStatement))
                self.assertEquals("{ s = \"odd\"; }", str(stmt.elseStatement))

                self.assertFalse(stmt.condition.isPropertyName)

        self.assertEquals(1, IfStatementChecker(self).test("var s; if (value % 2 == 0) { s = 'even'; } else { s = 'odd'; }"))

    def testForStatement(self):
        class ForStatementChecker(TestAST.Checker):
            def onForStatement(self, stmt):
                self.called += 1

                self.assertEquals("{ j += i; }", str(stmt.body))

                self.assertEquals("i = 0;", str(stmt.init))
                self.assertEquals("(i < 10)", str(stmt.condition))
                self.assertEquals("(i++);", str(stmt.next))

                target = stmt.continueTarget

                self.assert_(target)
                self.assertFalse(target.bound)
                self.assert_(target.unused)
                self.assertFalse(target.linked)
                self.assertFalse(stmt.fastLoop)

            def onForInStatement(self, stmt):
                self.called += 1

                self.assertEquals("{ out += name; }", str(stmt.body))

                self.assertEquals("name", str(stmt.each))
                self.assertEquals("names", str(stmt.enumerable))

            def onWhileStatement(self, stmt):
                self.called += 1

                self.assertEquals("{ i += 1; }", str(stmt.body))

                self.assertEquals("(i < 10)", str(stmt.condition))

            def onDoWhileStatement(self, stmt):
                self.called += 1

                self.assertEquals("{ i += 1; }", str(stmt.body))

                self.assertEquals("(i < 10)", str(stmt.condition))
                self.assertEquals(253, stmt.conditionPos)

        self.assertEquals(4, ForStatementChecker(self).test("""
            var i, j;

            for (i=0; i<10; i++) { j+=i; }

            var names = new Array();
            var out = '';

            for (name in names) { out += name; }

            while (i<10) { i += 1; }

            do { i += 1; } while (i<10);
        """))

    def testCallStatements(self):
        class CallStatementChecker(TestAST.Checker):
            def onDeclaration(self, decl):
                self.called += 1

                var = decl.proxy

                if var.name == 's':
                    self.assertEquals(AST.VarMode.var, decl.mode)
                    self.assertEquals(None, decl.function)

                    self.assert_(var.isValidLeftHandSide)
                    self.assertFalse(var.isArguments)
                    self.assertFalse(var.isThis)
                elif var.name == 'hello':
                    self.assertEquals(AST.VarMode.var, decl.mode)
                    self.assert_(decl.function)
                    self.assertEquals('(function hello(name) { s = ("Hello " + name); })', str(decl.function))
                elif var.name == 'dog':
                    self.assertEquals(AST.VarMode.var, decl.mode)
                    self.assert_(decl.function)
                    self.assertEquals('(function dog(name) { (this).name = name; })', str(decl.function))

            def onCall(self, expr):
                self.called += 1

                self.assertEquals("hello", str(expr.expression))
                self.assertEquals(['"flier"'], [str(arg) for arg in expr.args])
                self.assertEquals(143, expr.pos)

            def onCallNew(self, expr):
                self.called += 1

                self.assertEquals("dog", str(expr.expression))
                self.assertEquals(['"cat"'], [str(arg) for arg in expr.args])
                self.assertEquals(171, expr.pos)

            def onCallRuntime(self, expr):
                self.called += 1

                self.assertEquals("InitializeVarGlobal", expr.name)
                self.assertEquals(['"s"', '0'], [str(arg) for arg in expr.args])
                self.assertFalse(expr.isJsRuntime)

        self.assertEquals(6,  CallStatementChecker(self).test("""
            var s;
            function hello(name) { s = "Hello " + name; }
            function dog(name) { this.name = name; }
            hello("flier");
            new dog("cat");
        """))

    def testTryStatements(self):
        class TryStatementsChecker(TestAST.Checker):
            def onThrow(self, expr):
                self.called += 1

                self.assertEquals('"abc"', str(expr.exception))
                self.assertEquals(54, expr.pos)

            def onTryCatchStatement(self, stmt):
                self.called += 1

                self.assertEquals("{ throw \"abc\"; }", str(stmt.tryBlock))
                #FIXME self.assertEquals([], stmt.targets)

                stmt.tryBlock.visit(self)

                self.assertEquals("err", str(stmt.variable.name))
                self.assertEquals("{ s = err; }", str(stmt.catchBlock))

            def onTryFinallyStatement(self, stmt):
                self.called += 1

                self.assertEquals("{ throw \"abc\"; }", str(stmt.tryBlock))
                #FIXME self.assertEquals([], stmt.targets)

                self.assertEquals("{ s += \".\"; }", str(stmt.finallyBlock))

        self.assertEquals(3, TryStatementsChecker(self).test("""
            var s;
            try {
                throw "abc";
            }
            catch (err) {
                s = err;
            };

            try {
                throw "abc";
            }
            finally {
                s += ".";
            }
        """))

    def testLiterals(self):
        class LiteralChecker(TestAST.Checker):
            def onCallRuntime(self, expr):
                expr.args[1].visit(self)

            def onLiteral(self, litr):
                self.called += 1

                self.assertFalse(litr.isPropertyName)
                self.assertFalse(litr.isNull)
                self.assertFalse(litr.isTrue)

            def onRegExpLiteral(self, litr):
                self.called += 1

                self.assertEquals("test", litr.pattern)
                self.assertEquals("g", litr.flags)

            def onObjectLiteral(self, litr):
                self.called += 1

                self.assertEquals('constant:"name"="flier",constant:"sex"=true',
                                  ",".join(["%s:%s=%s" % (prop.kind, prop.key, prop.value) for prop in litr.properties]))

            def onArrayLiteral(self, litr):
                self.called += 1

                self.assertEquals('"hello","world",42',
                                  ",".join([str(value) for value in litr.values]))

        self.assertEquals(4, LiteralChecker(self).test("""
            false;
            /test/g;
            var o = { name: 'flier', sex: true };
            var a = ['hello', 'world', 42];
        """))

    def testOperations(self):
        class OperationChecker(TestAST.Checker):
            def onUnaryOperation(self, expr):
                self.called += 1

                self.assertEquals(AST.Op.BIT_NOT, expr.op)
                self.assertEquals("i", expr.expression.name)

                #print "unary", expr

            def onIncrementOperation(self, expr):
                self.fail()

            def onBinaryOperation(self, expr):
                self.called += 1

                self.assertEquals(AST.Op.ADD, expr.op)
                self.assertEquals("i", str(expr.left))
                self.assertEquals("j", str(expr.right))
                self.assertEquals(28, expr.pos)

                #print "bin", expr

            def onAssignment(self, expr):
                self.called += 1

                self.assertEquals(AST.Op.ASSIGN_ADD, expr.op)
                self.assertEquals(AST.Op.ADD, expr.binop)

                self.assertEquals("i", str(expr.target))
                self.assertEquals("1", str(expr.value))
                self.assertEquals(41, expr.pos)

                self.assertEquals("(i + 1)", str(expr.binOperation))

                self.assert_(expr.compound)

            def onCountOperation(self, expr):
                self.called += 1

                self.assertFalse(expr.prefix)
                self.assert_(expr.postfix)

                self.assertEquals(AST.Op.INC, expr.op)
                self.assertEquals(AST.Op.ADD, expr.binop)
                self.assertEquals(55, expr.pos)
                self.assertEquals("i", expr.expression.name)

                #print "count", expr

            def onCompareOperation(self, expr):
                self.called += 1

                if self.called == 4:
                    self.assertEquals(AST.Op.EQ, expr.op)
                    self.assertEquals(68, expr.pos) # i==j
                else:
                    self.assertEquals(AST.Op.EQ_STRICT, expr.op)
                    self.assertEquals(82, expr.pos) # i===j

                self.assertEquals("i", str(expr.left))
                self.assertEquals("j", str(expr.right))

                #print "comp", expr

            def onConditional(self, expr):
                self.called += 1

                self.assertEquals("(i > j)", str(expr.condition))
                self.assertEquals("i", str(expr.thenExpr))
                self.assertEquals("j", str(expr.elseExpr))

                self.assertEquals(112, expr.thenExprPos)
                self.assertEquals(114, expr.elseExprPos)

        self.assertEquals(7, OperationChecker(self).test("""
        var i, j;
        i+j;
        i+=1;
        i++;
        i==j;
        i===j;
        ~i;
        i>j?i:j;
        """))

if __name__ == '__main__':
    if "-v" in sys.argv:
        level = logging.DEBUG
    else:
        level = logging.WARN

    if "-p" in sys.argv:
        sys.argv.remove("-p")
        print "Press any key to continue..."
        raw_input()

    logging.basicConfig(level=level, format='%(asctime)s %(levelname)s %(message)s')

    logging.info("testing PyV8 module %s with V8 v%s", __version__, JSEngine.version)

    unittest.main()

########NEW FILE########
__FILENAME__ = PyV8
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import with_statement

import sys, os, re

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

try:
    import json
except ImportError:
    import simplejson as json

import _PyV8

__author__ = 'Flier Lu <flier.lu@gmail.com>'
__version__ = '1.0'

__all__ = ["ReadOnly", "DontEnum", "DontDelete", "Internal",
           "JSError", "JSObject", "JSArray", "JSFunction",
           "JSClass", "JSEngine", "JSContext",
           "JSObjectSpace", "JSAllocationAction",
           "JSStackTrace", "JSStackFrame", "profiler", 
           "JSExtension", "JSLocker", "JSUnlocker", "AST"]

class JSAttribute(object):
    def __init__(self, name):
        self.name = name

    def __call__(self, func):
        setattr(func, "__%s__" % self.name, True)
        
        return func

ReadOnly = JSAttribute(name='readonly')
DontEnum = JSAttribute(name='dontenum')
DontDelete = JSAttribute(name='dontdel')
Internal = JSAttribute(name='internal')

class JSError(Exception):
    def __init__(self, impl):
        Exception.__init__(self)

        self._impl = impl

    def __str__(self):
        return str(self._impl)

    def __unicode__(self, *args, **kwargs):
        return unicode(self._impl)

    def __getattribute__(self, attr):
        impl = super(JSError, self).__getattribute__("_impl")

        try:
            return getattr(impl, attr)
        except AttributeError:
            return super(JSError, self).__getattribute__(attr)

    RE_FRAME = re.compile(r"\s+at\s(?:new\s)?(?P<func>.+)\s\((?P<file>[^:]+):?(?P<row>\d+)?:?(?P<col>\d+)?\)")
    RE_FUNC = re.compile(r"\s+at\s(?:new\s)?(?P<func>.+)\s\((?P<file>[^\)]+)\)")
    RE_FILE = re.compile(r"\s+at\s(?P<file>[^:]+):?(?P<row>\d+)?:?(?P<col>\d+)?")

    @staticmethod
    def parse_stack(value):
        stack = []

        def int_or_nul(value):
            return int(value) if value else None

        for line in value.split('\n')[1:]:
            m = JSError.RE_FRAME.match(line)

            if m:
                stack.append((m.group('func'), m.group('file'), int_or_nul(m.group('row')), int_or_nul(m.group('col'))))
                continue

            m = JSError.RE_FUNC.match(line)

            if m:
                stack.append((m.group('func'), m.group('file'), None, None))
                continue

            m = JSError.RE_FILE.match(line)

            if m:
                stack.append((None, m.group('file'), int_or_nul(m.group('row')), int_or_nul(m.group('col'))))
                continue

            assert line

        return stack

    @property
    def frames(self):
        return self.parse_stack(self.stackTrace)

_PyV8._JSError._jsclass = JSError

JSObject = _PyV8.JSObject
JSArray = _PyV8.JSArray
JSFunction = _PyV8.JSFunction
JSExtension = _PyV8.JSExtension

def func_apply(self, thisArg, argArray=[]):
    if isinstance(thisArg, JSObject):
        return self.invoke(thisArg, argArray)

    this = JSContext.current.eval("(%s)" % json.dumps(thisArg))

    return self.invoke(this, argArray)

JSFunction.apply = func_apply

class JSLocker(_PyV8.JSLocker):
    def __enter__(self):
        self.enter()

        if JSContext.entered:
            self.leave()
            raise RuntimeError("Lock should be acquired before enter the context")

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if JSContext.entered:
            self.leave()
            raise RuntimeError("Lock should be released after leave the context")

        self.leave()

    def __nonzero__(self):
        return self.entered()

class JSUnlocker(_PyV8.JSUnlocker):
    def __enter__(self):
        self.enter()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.leave()

    def __nonzero__(self):
        return self.entered()

class JSClass(object):
    __properties__ = {}
    __watchpoints__ = {}

    def __getattr__(self, name):
        if name == 'constructor':
            return JSClassConstructor(self.__class__)

        if name == 'prototype':
            return JSClassPrototype(self.__class__)

        prop = self.__dict__.setdefault('__properties__', {}).get(name, None)

        if prop and callable(prop[0]):
            return prop[0]()

        raise AttributeError(name)

    def __setattr__(self, name, value):
        prop = self.__dict__.setdefault('__properties__', {}).get(name, None)

        if prop and callable(prop[1]):
            return prop[1](value)

        return object.__setattr__(self, name, value)

    def toString(self):
        "Returns a string representation of an object."
        return "[object %s]" % self.__class__.__name__

    def toLocaleString(self):
        "Returns a value as a string value appropriate to the host environment's current locale."
        return self.toString()

    def valueOf(self):
        "Returns the primitive value of the specified object."
        return self

    def hasOwnProperty(self, name):
        "Returns a Boolean value indicating whether an object has a property with the specified name."
        return hasattr(self, name)

    def isPrototypeOf(self, obj):
        "Returns a Boolean value indicating whether an object exists in the prototype chain of another object."
        raise NotImplementedError()

    def __defineGetter__(self, name, getter):
        "Binds an object's property to a function to be called when that property is looked up."
        self.__properties__[name] = (getter, self.__lookupSetter__(name))

    def __lookupGetter__(self, name):
        "Return the function bound as a getter to the specified property."
        return self.__properties__.get(name, (None, None))[0]

    def __defineSetter__(self, name, setter):
        "Binds an object's property to a function to be called when an attempt is made to set that property."
        self.__properties__[name] = (self.__lookupGetter__(name), setter)

    def __lookupSetter__(self, name):
        "Return the function bound as a setter to the specified property."
        return self.__properties__.get(name, (None, None))[1]

    def watch(self, prop, handler):
        "Watches for a property to be assigned a value and runs a function when that occurs."
        self.__watchpoints__[prop] = handler

    def unwatch(self, prop):
        "Removes a watchpoint set with the watch method."
        del self.__watchpoints__[prop]

class JSClassConstructor(JSClass):
    def __init__(self, cls):
        self.cls = cls

    @property
    def name(self):
        return self.cls.__name__

    def toString(self):
        return "function %s() {\n  [native code]\n}" % self.name

    def __call__(self, *args, **kwds):
        return self.cls(*args, **kwds)

class JSClassPrototype(JSClass):
    def __init__(self, cls):
        self.cls = cls

    @property
    def constructor(self):
        return JSClassConstructor(self.cls)

    @property
    def name(self):
        return self.cls.__name__

class JSDebugProtocol(object):
    """
    Support the V8 debugger JSON based protocol.

    <http://code.google.com/p/v8/wiki/DebuggerProtocol>
    """
    class Packet(object):
        REQUEST = 'request'
        RESPONSE = 'response'
        EVENT = 'event'

        def __init__(self, payload):
            self.data = json.loads(payload) if type(payload) in [str, unicode] else payload

        @property
        def seq(self):
            return self.data['seq']

        @property
        def type(self):
            return self.data['type']

    class Request(Packet):
        @property
        def cmd(self):
            return self.data['command']

        @property
        def args(self):
            return self.data['args']

    class Response(Packet):
        @property
        def request_seq(self):
            return self.data['request_seq']

        @property
        def cmd(self):
            return self.data['command']

        @property
        def body(self):
            return self.data['body']

        @property
        def running(self):
            return self.data['running']

        @property
        def success(self):
            return self.data['success']

        @property
        def message(self):
            return self.data['message']

    class Event(Packet):
        @property
        def event(self):
            return self.data['event']

        @property
        def body(self):
            return self.data['body']

    def __init__(self):
        self.seq = 0

    def nextSeq(self):
        seq = self.seq
        self.seq += 1

        return seq

    def parsePacket(self, payload):
        obj = json.loads(payload)

        return JSDebugProtocol.Event(obj) if obj['type'] == 'event' else JSDebugProtocol.Response(obj)
    
class JSDebugEvent(_PyV8.JSDebugEvent):
    class FrameData(object):
        def __init__(self, frame, count, name, value):
            self.frame = frame
            self.count = count
            self.name = name
            self.value = value

        def __len__(self):
            return self.count(self.frame)

        def __iter__(self):
            for i in xrange(self.count(self.frame)):
                yield (self.name(self.frame, i), self.value(self.frame, i))

    class Frame(object):
        def __init__(self, frame):
            self.frame = frame

        @property
        def index(self):
            return int(self.frame.index())

        @property
        def function(self):
            return self.frame.func()

        @property
        def receiver(self):
            return self.frame.receiver()

        @property
        def isConstructCall(self):
            return bool(self.frame.isConstructCall())

        @property
        def isDebuggerFrame(self):
            return bool(self.frame.isDebuggerFrame())

        @property
        def argumentCount(self):
            return int(self.frame.argumentCount())

        def argumentName(self, idx):
            return str(self.frame.argumentName(idx))

        def argumentValue(self, idx):
            return self.frame.argumentValue(idx)

        @property
        def arguments(self):
            return FrameData(self, self.argumentCount, self.argumentName, self.argumentValue)

        def localCount(self, idx):
            return int(self.frame.localCount())

        def localName(self, idx):
            return str(self.frame.localName(idx))

        def localValue(self, idx):
            return self.frame.localValue(idx)

        @property
        def locals(self):
            return FrameData(self, self.localCount, self.localName, self.localValue)

        @property
        def sourcePosition(self):
            return self.frame.sourcePosition()

        @property
        def sourceLine(self):
            return int(self.frame.sourceLine())

        @property
        def sourceColumn(self):
            return int(self.frame.sourceColumn())

        @property
        def sourceLineText(self):
            return str(self.frame.sourceLineText())

        def evaluate(self, source, disable_break = True):
            return self.frame.evaluate(source, disable_break)

        @property
        def invocationText(self):
            return str(self.frame.invocationText())

        @property
        def sourceAndPositionText(self):
            return str(self.frame.sourceAndPositionText())

        @property
        def localsText(self):
            return str(self.frame.localsText())

        def __str__(self):
            return str(self.frame.toText())

    class Frames(object):
        def __init__(self, state):
            self.state = state

        def __len__(self):
            return self.state.frameCount

        def __iter__(self):
            for i in xrange(self.state.frameCount):
                yield self.state.frame(i)

    class State(object):
        def __init__(self, state):
            self.state = state

        @property
        def frameCount(self):
            return int(self.state.frameCount())

        def frame(self, idx = None):
            return JSDebugEvent.Frame(self.state.frame(idx))

        @property
        def selectedFrame(self):
            return int(self.state.selectedFrame())

        @property
        def frames(self):
            return JSDebugEvent.Frames(self)

        def __repr__(self):
            s = StringIO()

            try:
                for frame in self.frames:
                    s.write(str(frame))

                return s.getvalue()
            finally:
                s.close()

    class DebugEvent(object):
        pass

    class StateEvent(DebugEvent):
        __state = None

        @property
        def state(self):
            if not self.__state:
                self.__state = JSDebugEvent.State(self.event.executionState())

            return self.__state

    class BreakEvent(StateEvent):
        type = _PyV8.JSDebugEvent.Break

        def __init__(self, event):
            self.event = event

    class ExceptionEvent(StateEvent):
        type = _PyV8.JSDebugEvent.Exception

        def __init__(self, event):
            self.event = event

    class NewFunctionEvent(DebugEvent):
        type = _PyV8.JSDebugEvent.NewFunction

        def __init__(self, event):
            self.event = event

    class Script(object):
        def __init__(self, script):
            self.script = script

        @property
        def source(self):
            return self.script.source()

        @property
        def id(self):
            return self.script.id()

        @property
        def name(self):
            return self.script.name()

        @property
        def lineOffset(self):
            return self.script.lineOffset()

        @property
        def lineCount(self):
            return self.script.lineCount()

        @property
        def columnOffset(self):
            return self.script.columnOffset()

        @property
        def type(self):
            return self.script.type()

        def __repr__(self):
            return "<%s script %s @ %d:%d> : '%s'" % (self.type, self.name,
                                                      self.lineOffset, self.columnOffset,
                                                      self.source)

    class CompileEvent(StateEvent):
        def __init__(self, event):
            self.event = event

        @property
        def script(self):
            if not hasattr(self, "_script"):
                setattr(self, "_script", JSDebugEvent.Script(self.event.script()))

            return self._script

        def __str__(self):
            return str(self.script)

    class BeforeCompileEvent(CompileEvent):
        type = _PyV8.JSDebugEvent.BeforeCompile

        def __init__(self, event):
            JSDebugEvent.CompileEvent.__init__(self, event)

        def __repr__(self):
            return "before compile script: %s\n%s" % (repr(self.script), repr(self.state))

    class AfterCompileEvent(CompileEvent):
        type = _PyV8.JSDebugEvent.AfterCompile

        def __init__(self, event):
            JSDebugEvent.CompileEvent.__init__(self, event)

        def __repr__(self):
            return "after compile script: %s\n%s" % (repr(self.script), repr(self.state))

    onMessage = None
    onBreak = None
    onException = None
    onNewFunction = None
    onBeforeCompile = None
    onAfterCompile = None

class JSDebugger(JSDebugProtocol, JSDebugEvent):
    def __init__(self):
        JSDebugProtocol.__init__(self)
        JSDebugEvent.__init__(self)

    def __enter__(self):
        self.enabled = True

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.enabled = False

    @property
    def context(self):
        if not hasattr(self, '_context'):
            self._context = JSContext(ctxt=_PyV8.debug().context)

        return self._context

    def isEnabled(self):
        return _PyV8.debug().enabled

    def setEnabled(self, enable):
        dbg = _PyV8.debug()

        if enable:
            dbg.onDebugEvent = self.onDebugEvent
            dbg.onDebugMessage = self.onDebugMessage
            dbg.onDispatchDebugMessages = self.onDispatchDebugMessages
        else:
            dbg.onDebugEvent = None
            dbg.onDebugMessage = None
            dbg.onDispatchDebugMessages = None

        dbg.enabled = enable

    enabled = property(isEnabled, setEnabled)

    def onDebugMessage(self, msg, data):
        if self.onMessage:
            self.onMessage(json.loads(msg))

    def onDebugEvent(self, type, state, evt):
        if type == JSDebugEvent.Break:
            if self.onBreak: self.onBreak(JSDebugEvent.BreakEvent(evt))
        elif type == JSDebugEvent.Exception:
            if self.onException: self.onException(JSDebugEvent.ExceptionEvent(evt))
        elif type == JSDebugEvent.NewFunction:
            if self.onNewFunction: self.onNewFunction(JSDebugEvent.NewFunctionEvent(evt))
        elif type == JSDebugEvent.BeforeCompile:
            if self.onBeforeCompile: self.onBeforeCompile(JSDebugEvent.BeforeCompileEvent(evt))
        elif type == JSDebugEvent.AfterCompile:
            if self.onAfterCompile: self.onAfterCompile(JSDebugEvent.AfterCompileEvent(evt))

    def onDispatchDebugMessages(self):
        return True

    def debugBreak(self):
        _PyV8.debug().debugBreak()

    def debugBreakForCommand(self):
        _PyV8.debug().debugBreakForCommand()

    def cancelDebugBreak(self):
        _PyV8.debug().cancelDebugBreak()

    def processDebugMessages(self):
        _PyV8.debug().processDebugMessages()

    def sendCommand(self, cmd, *args, **kwds):
        request = json.dumps({
            'seq': self.nextSeq(),
            'type': 'request',
            'command': cmd,
            'arguments': kwds
        })

        _PyV8.debug().sendCommand(request)

        return request

    def debugContinue(self, action='next', steps=1):
        return self.sendCommand('continue', stepaction=action)

    def stepNext(self, steps=1):
        """Step to the next statement in the current function."""
        return self.debugContinue(action='next', steps=steps)

    def stepIn(self, steps=1):
        """Step into new functions invoked or the next statement in the current function."""
        return self.debugContinue(action='in', steps=steps)

    def stepOut(self, steps=1):
        """Step out of the current function."""
        return self.debugContinue(action='out', steps=steps)

    def stepMin(self, steps=1):
        """Perform a minimum step in the current function."""
        return self.debugContinue(action='out', steps=steps)

class JSProfiler(_PyV8.JSProfiler):
    @property
    def logs(self):
        pos = 0

        while True:
            size, buf = self.getLogLines(pos)

            if size == 0:
                break

            for line in buf.split('\n'):
                yield line

            pos += size

profiler = JSProfiler()

JSObjectSpace = _PyV8.JSObjectSpace
JSAllocationAction = _PyV8.JSAllocationAction

class JSEngine(_PyV8.JSEngine):
    def __init__(self):
        _PyV8.JSEngine.__init__(self)
        
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        del self

JSScript = _PyV8.JSScript

JSStackTrace = _PyV8.JSStackTrace
JSStackTrace.Options = _PyV8.JSStackTraceOptions
JSStackFrame = _PyV8.JSStackFrame

class JSIsolate(_PyV8.JSIsolate):
    def __enter__(self):
        self.enter()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.leave()

        del self

class JSContext(_PyV8.JSContext):
    def __init__(self, obj=None, extensions=None, ctxt=None):
        if JSLocker.active:
            self.lock = JSLocker()
            self.lock.enter()

        if ctxt:
            _PyV8.JSContext.__init__(self, ctxt)
        else:
            _PyV8.JSContext.__init__(self, obj, extensions or [])

    def __enter__(self):
        self.enter()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.leave()

        if hasattr(JSLocker, 'lock'):
            self.lock.leave()
            self.lock = None

        del self

# contribute by marc boeker <http://code.google.com/u/marc.boeker/>
def convert(obj):
    if type(obj) == _PyV8.JSArray:
        return [convert(v) for v in obj]

    if type(obj) == _PyV8.JSObject:
        return dict([[str(k), convert(obj.__getattr__(str(k)))] for k in obj.__members__])

    return obj

class AST:
    Scope = _PyV8.AstScope
    VarMode = _PyV8.AstVariableMode
    Var = _PyV8.AstVariable
    Label = _PyV8.AstLabel
    NodeType = _PyV8.AstNodeType
    Node = _PyV8.AstNode
    Statement = _PyV8.AstStatement
    Expression = _PyV8.AstExpression
    Breakable = _PyV8.AstBreakableStatement
    Block = _PyV8.AstBlock
    Declaration = _PyV8.AstDeclaration
    Iteration = _PyV8.AstIterationStatement
    DoWhile = _PyV8.AstDoWhileStatement
    While = _PyV8.AstWhileStatement
    For = _PyV8.AstForStatement
    ForIn = _PyV8.AstForInStatement
    ExpressionStatement = _PyV8.AstExpressionStatement
    Continue = _PyV8.AstContinueStatement
    Break = _PyV8.AstBreakStatement
    Return = _PyV8.AstReturnStatement
    With = _PyV8.AstWithStatement
    Case = _PyV8.AstCaseClause
    Switch = _PyV8.AstSwitchStatement
    Try = _PyV8.AstTryStatement
    TryCatch = _PyV8.AstTryCatchStatement
    TryFinally = _PyV8.AstTryFinallyStatement
    Debugger = _PyV8.AstDebuggerStatement
    Empty = _PyV8.AstEmptyStatement
    Literal = _PyV8.AstLiteral
    MaterializedLiteral = _PyV8.AstMaterializedLiteral
    PropertyKind = _PyV8.AstPropertyKind
    ObjectProperty = _PyV8.AstObjectProperty
    Object = _PyV8.AstObjectLiteral
    RegExp = _PyV8.AstRegExpLiteral
    Array = _PyV8.AstArrayLiteral
    VarProxy = _PyV8.AstVariableProxy
    Property = _PyV8.AstProperty
    Call = _PyV8.AstCall
    CallNew = _PyV8.AstCallNew
    CallRuntime = _PyV8.AstCallRuntime
    Op = _PyV8.AstOperation
    UnaryOp = _PyV8.AstUnaryOperation
    BinOp = _PyV8.AstBinaryOperation
    CountOp = _PyV8.AstCountOperation
    CompOp = _PyV8.AstCompareOperation
    Conditional = _PyV8.AstConditional
    Assignment = _PyV8.AstAssignment
    Throw = _PyV8.AstThrow
    Function = _PyV8.AstFunctionLiteral
    SharedFunction = _PyV8.AstSharedFunctionInfoLiteral
    This = _PyV8.AstThisFunction

from datetime import *
import unittest
import logging
import traceback

class TestContext(unittest.TestCase):
    def testMultiNamespace(self):
        self.assert_(not bool(JSContext.inContext))
        self.assert_(not bool(JSContext.entered))

        class Global(object):
            name = "global"

        g = Global()

        with JSContext(g) as ctxt:
            self.assert_(bool(JSContext.inContext))
            self.assertEquals(g.name, str(JSContext.entered.locals.name))
            self.assertEquals(g.name, str(JSContext.current.locals.name))

            class Local(object):
                name = "local"

            l = Local()

            with JSContext(l):
                self.assert_(bool(JSContext.inContext))
                self.assertEquals(l.name, str(JSContext.entered.locals.name))
                self.assertEquals(l.name, str(JSContext.current.locals.name))

            self.assert_(bool(JSContext.inContext))
            self.assertEquals(g.name, str(JSContext.entered.locals.name))
            self.assertEquals(g.name, str(JSContext.current.locals.name))

        self.assert_(not bool(JSContext.entered))
        self.assert_(not bool(JSContext.inContext))

    def _testMultiContext(self):
        # Create an environment
        with JSContext() as ctxt0:
            ctxt0.securityToken = "password"

            global0 = ctxt0.locals
            global0.custom = 1234

            self.assertEquals(1234, int(global0.custom))

            # Create an independent environment
            with JSContext() as ctxt1:
                ctxt1.securityToken = ctxt0.securityToken

                global1 = ctxt1.locals
                global1.custom = 1234

                with ctxt0:
                    self.assertEquals(1234, int(global0.custom))
                self.assertEquals(1234, int(global1.custom))

                # Now create a new context with the old global
                with JSContext(global1) as ctxt2:
                    ctxt2.securityToken = ctxt1.securityToken

                    with ctxt1:
                        self.assertEquals(1234, int(global1.custom))
                        
                    self.assertEquals(1234, int(global2.custom))

    def _testSecurityChecks(self):
        with JSContext() as env1:
            env1.securityToken = "foo"

            # Create a function in env1.
            env1.eval("spy=function(){return spy;}")

            spy = env1.locals.spy

            self.assert_(isinstance(spy, _PyV8.JSFunction))

            # Create another function accessing global objects.
            env1.eval("spy2=function(){return 123;}")

            spy2 = env1.locals.spy2

            self.assert_(isinstance(spy2, _PyV8.JSFunction))

            # Switch to env2 in the same domain and invoke spy on env2.
            env2 = JSContext()

            env2.securityToken = "foo"

            with env2:
                result = spy.apply(env2.locals)

                self.assert_(isinstance(result, _PyV8.JSFunction))

            env2.securityToken = "bar"

            # Call cross_domain_call, it should throw an exception
            with env2:
                self.assertRaises(JSError, spy2.apply, env2.locals)

    def _testCrossDomainDelete(self):
        with JSContext() as env1:
            env2 = JSContext()

            # Set to the same domain.
            env1.securityToken = "foo"
            env2.securityToken = "foo"

            env1.locals.prop = 3

            env2.locals.env1 = env1.locals

            # Change env2 to a different domain and delete env1.prop.
            #env2.securityToken = "bar"

            self.assertEquals(3, int(env1.eval("prop")))

            print env1.eval("env1")

            with env2:
                self.assertEquals(3, int(env2.eval("this.env1.prop")))
                self.assertEquals("false", str(e.eval("delete env1.prop")))

            # Check that env1.prop still exists.
            self.assertEquals(3, int(env1.locals.prop))

class TestWrapper(unittest.TestCase):
    def testObject(self):
        with JSContext() as ctxt:
            o = ctxt.eval("new Object()")

            self.assert_(hash(o) > 0)

            o1 = o.clone()

            self.assertEquals(hash(o1), hash(o))
            self.assert_(o != o1)

    def testAutoConverter(self):
        with JSContext() as ctxt:
            ctxt.eval("""
                var_i = 1;
                var_f = 1.0;
                var_s = "test";
                var_b = true;
                var_s_obj = new String("test");
                var_b_obj = new Boolean(true);
                var_f_obj = new Number(1.5);
            """)

            vars = ctxt.locals

            var_i = vars.var_i

            self.assert_(var_i)
            self.assertEquals(1, int(var_i))

            var_f = vars.var_f

            self.assert_(var_f)
            self.assertEquals(1.0, float(vars.var_f))

            var_s = vars.var_s
            self.assert_(var_s)
            self.assertEquals("test", str(vars.var_s))

            var_b = vars.var_b
            self.assert_(var_b)
            self.assert_(bool(var_b))

            self.assertEquals("test", vars.var_s_obj)
            self.assert_(vars.var_b_obj)
            self.assertEquals(1.5, vars.var_f_obj)

            attrs = dir(ctxt.locals)

            self.assert_(attrs)
            self.assert_("var_i" in attrs)
            self.assert_("var_f" in attrs)
            self.assert_("var_s" in attrs)
            self.assert_("var_b" in attrs)
            self.assert_("var_s_obj" in attrs)
            self.assert_("var_b_obj" in attrs)
            self.assert_("var_f_obj" in attrs)

    def testExactConverter(self):
        class MyInteger(int, JSClass):
            pass

        class MyString(str, JSClass):
            pass

        class MyUnicode(unicode, JSClass):
            pass

        class MyDateTime(time, JSClass):
            pass

        class Global(JSClass):
            var_bool = True
            var_int = 1
            var_float = 1.0
            var_str = 'str'
            var_unicode = u'unicode'
            var_datetime = datetime.now()
            var_date = date.today()
            var_time = time()

            var_myint = MyInteger()
            var_mystr = MyString('mystr')
            var_myunicode = MyUnicode('myunicode')
            var_mytime = MyDateTime()

        with JSContext(Global()) as ctxt:
            typename = ctxt.eval("(function (name) { return this[name].constructor.name; })")
            typeof = ctxt.eval("(function (name) { return typeof(this[name]); })")

            self.assertEquals('Boolean', typename('var_bool'))
            self.assertEquals('Number', typename('var_int'))
            self.assertEquals('Number', typename('var_float'))
            self.assertEquals('String', typename('var_str'))
            self.assertEquals('String', typename('var_unicode'))
            self.assertEquals('Date', typename('var_datetime'))
            self.assertEquals('Date', typename('var_date'))
            self.assertEquals('Date', typename('var_time'))

            self.assertEquals('MyInteger', typename('var_myint'))
            self.assertEquals('MyString', typename('var_mystr'))
            self.assertEquals('MyUnicode', typename('var_myunicode'))
            self.assertEquals('MyDateTime', typename('var_mytime'))

            self.assertEquals('object', typeof('var_myint'))
            self.assertEquals('object', typeof('var_mystr'))
            self.assertEquals('object', typeof('var_myunicode'))
            self.assertEquals('object', typeof('var_mytime'))

    def testJavascriptWrapper(self):
        with JSContext() as ctxt:
            self.assertEquals(type(None), type(ctxt.eval("null")))
            self.assertEquals(type(None), type(ctxt.eval("undefined")))
            self.assertEquals(bool, type(ctxt.eval("true")))
            self.assertEquals(str, type(ctxt.eval("'test'")))
            self.assertEquals(int, type(ctxt.eval("123")))
            self.assertEquals(float, type(ctxt.eval("3.14")))
            self.assertEquals(datetime, type(ctxt.eval("new Date()")))
            self.assertEquals(JSArray, type(ctxt.eval("[1, 2, 3]")))
            self.assertEquals(JSFunction, type(ctxt.eval("(function() {})")))
            self.assertEquals(JSObject, type(ctxt.eval("new Object()")))

    def testPythonWrapper(self):
        with JSContext() as ctxt:
            typeof = ctxt.eval("(function type(value) { return typeof value; })")
            protoof = ctxt.eval("(function protoof(value) { return Object.prototype.toString.apply(value); })")

            self.assertEquals('[object Null]', protoof(None))
            self.assertEquals('boolean', typeof(True))
            self.assertEquals('number', typeof(123))
            self.assertEquals('number', typeof(123l))
            self.assertEquals('number', typeof(3.14))
            self.assertEquals('string', typeof('test'))
            self.assertEquals('string', typeof(u'test'))

            self.assertEquals('[object Date]', protoof(datetime.now()))
            self.assertEquals('[object Date]', protoof(date.today()))
            self.assertEquals('[object Date]', protoof(time()))

            def test():
                pass

            self.assertEquals('[object Function]', protoof(abs))
            self.assertEquals('[object Function]', protoof(test))
            self.assertEquals('[object Function]', protoof(self.testPythonWrapper))
            self.assertEquals('[object Function]', protoof(int))

    def testFunction(self):
        with JSContext() as ctxt:
            func = ctxt.eval("""
                (function ()
                {
                    function a()
                    {
                        return "abc";
                    }

                    return a();
                })
                """)

            self.assertEquals("abc", str(func()))
            self.assert_(func != None)
            self.assertFalse(func == None)

            func = ctxt.eval("(function test() {})")

            self.assertEquals("test", func.name)
            self.assertEquals("", func.resname)
            self.assertEquals(0, func.linenum)
            self.assertEquals(14, func.colnum)
            self.assertEquals(0, func.lineoff)
            self.assertEquals(0, func.coloff)
            
            #TODO fix me, why the setter doesn't work?

            func.name = "hello"

            #self.assertEquals("hello", func.name)

    def testCall(self):
        class Hello(object):
            def __call__(self, name):
                return "hello " + name

        class Global(JSClass):
            hello = Hello()

        with JSContext(Global()) as ctxt:
            self.assertEquals("hello flier", ctxt.eval("hello('flier')"))

    def testJSFunction(self):
        with JSContext() as ctxt:
            hello = ctxt.eval("(function (name) { return 'hello ' + name; })")

            self.assert_(isinstance(hello, _PyV8.JSFunction))
            self.assertEquals("hello flier", hello('flier'))
            self.assertEquals("hello flier", hello.invoke(['flier']))

            obj = ctxt.eval("({ 'name': 'flier', 'hello': function (name) { return 'hello ' + name + ' from ' + this.name; }})")
            hello = obj.hello
            self.assert_(isinstance(hello, JSFunction))
            self.assertEquals("hello flier from flier", hello('flier'))

            tester = ctxt.eval("({ 'name': 'tester' })")
            self.assertEquals("hello flier from tester", hello.invoke(tester, ['flier']))
            self.assertEquals("hello flier from json", hello.apply({ 'name': 'json' }, ['flier']))

    def testJSError(self):
        with JSContext() as ctxt:
            try:
                ctxt.eval('throw "test"')
                self.fail()
            except:
                self.assert_(JSError, sys.exc_type)

    def testErrorInfo(self):
        with JSContext() as ctxt:
            with JSEngine() as engine:
                try:
                    engine.compile("""
                        function hello()
                        {
                            throw Error("hello world");
                        }

                        hello();""", "test", 10, 10).run()
                    self.fail()
                except JSError, e:
                    self.assert_(str(e).startswith('JSError: Error: hello world ( test @ 14 : 34 )  ->'))
                    self.assertEqual("Error", e.name)
                    self.assertEqual("hello world", e.message)
                    self.assertEqual("test", e.scriptName)
                    self.assertEqual(14, e.lineNum)
                    self.assertEqual(102, e.startPos)
                    self.assertEqual(103, e.endPos)
                    self.assertEqual(34, e.startCol)
                    self.assertEqual(35, e.endCol)
                    self.assertEqual('throw Error("hello world");', e.sourceLine.strip())
                    self.assertEqual('Error: hello world\n' +
                                     '    at Error (unknown source)\n' +
                                     '    at hello (test:14:35)\n' +
                                     '    at test:17:25', e.stackTrace)

    def testParseStack(self):
        self.assertEquals([
            ('Error', 'unknown source', None, None),
            ('test', 'native', None, None),
            ('<anonymous>', 'test0', 3, 5),
            ('f', 'test1', 2, 19),
            ('g', 'test2', 1, 15),
            (None, 'test3', 1, None),
            (None, 'test3', 1, 1),
        ], JSError.parse_stack("""Error: err
            at Error (unknown source)
            at test (native)
            at new <anonymous> (test0:3:5)
            at f (test1:2:19)
            at g (test2:1:15)
            at test3:1
            at test3:1:1"""))

    def testStackTrace(self):
        class Global(JSClass):
            def GetCurrentStackTrace(self, limit):
                return JSStackTrace.GetCurrentStackTrace(4, JSStackTrace.Options.Detailed)

        with JSContext(Global()) as ctxt:
            st = ctxt.eval("""
                function a()
                {
                    return GetCurrentStackTrace(10);
                }
                function b()
                {
                    return eval("a()");
                }
                function c()
                {
                    return new b();
                }
            c();""", "test")

            self.assertEquals(4, len(st))
            self.assertEquals("\tat a (test:4:28)\n\tat (eval)\n\tat b (test:8:28)\n\tat c (test:12:28)\n", str(st))
            self.assertEquals("test.a (4:28)\n. (1:1) eval\ntest.b (8:28) constructor\ntest.c (12:28)",
                              "\n".join(["%s.%s (%d:%d)%s%s" % (
                                f.scriptName, f.funcName, f.lineNum, f.column,
                                ' eval' if f.isEval else '',
                                ' constructor' if f.isConstructor else '') for f in st]))

    def testPythonException(self):
        class Global(JSClass):
            def raiseException(self):
                raise RuntimeError("Hello")

        with JSContext(Global()) as ctxt:
            r = ctxt.eval("""
                msg ="";
                try
                {
                    this.raiseException()
                }
                catch(e)
                {
                    msg += "catch " + e + ";";
                }
                finally
                {
                    msg += "finally";
                }""")
            self.assertEqual("catch Error: Hello;finally", str(ctxt.locals.msg))

    def testExceptionMapping(self):
        class TestException(Exception):
            pass

        class Global(JSClass):
            def raiseIndexError(self):
                return [1, 2, 3][5]

            def raiseAttributeError(self):
                None.hello()

            def raiseSyntaxError(self):
                eval("???")

            def raiseTypeError(self):
                int(sys)

            def raiseNotImplementedError(self):
                raise NotImplementedError("Not support")

            def raiseExceptions(self):
                raise TestException()

        with JSContext(Global()) as ctxt:
            ctxt.eval("try { this.raiseIndexError(); } catch (e) { msg = e; }")

            self.assertEqual("RangeError: list index out of range", str(ctxt.locals.msg))

            ctxt.eval("try { this.raiseAttributeError(); } catch (e) { msg = e; }")

            self.assertEqual("ReferenceError: 'NoneType' object has no attribute 'hello'", str(ctxt.locals.msg))

            ctxt.eval("try { this.raiseSyntaxError(); } catch (e) { msg = e; }")

            self.assertEqual("SyntaxError: invalid syntax", str(ctxt.locals.msg))

            ctxt.eval("try { this.raiseTypeError(); } catch (e) { msg = e; }")

            self.assertEqual("TypeError: int() argument must be a string or a number, not 'module'", str(ctxt.locals.msg))

            ctxt.eval("try { this.raiseNotImplementedError(); } catch (e) { msg = e; }")

            self.assertEqual("Error: Not support", str(ctxt.locals.msg))

            self.assertRaises(TestException, ctxt.eval, "this.raiseExceptions();")

    def testArray(self):
        with JSContext() as ctxt:
            array = ctxt.eval("""
                var array = new Array();

                for (i=0; i<10; i++)
                {
                    array[i] = 10-i;
                }

                array;
                """)

            self.assert_(isinstance(array, _PyV8.JSArray))
            self.assertEqual(10, len(array))

            self.assert_(5 in array)
            self.assertFalse(15 in array)

            l = list(array)

            self.assertEqual(10, len(l))

            for i in xrange(10):
                self.assertEqual(10-i, array[i])
                self.assertEqual(10-i, l[i])

            array[5] = 0

            self.assertEqual(0, array[5])

            del array[5]

            self.assertEquals(None, array[5])

            ctxt.locals.array1 = JSArray(5)
            ctxt.locals.array2 = JSArray([1, 2, 3, 4, 5])

            for i in xrange(len(ctxt.locals.array2)):
                ctxt.locals.array1[i] = ctxt.locals.array2[i] * 10

            ctxt.eval("""
                var sum = 0;

                for (i=0; i<array1.length; i++)
                    sum += array1[i]

                for (i=0; i<array2.length; i++)
                    sum += array2[i]
                """)

            self.assertEqual(165, ctxt.locals.sum)

            ctxt.locals.array3 = [1, 2, 3, 4, 5]
            self.assert_(ctxt.eval('array3[1] === 2'))
            self.assert_(ctxt.eval('array3[9] === undefined'))

            cases = {
                "a = Array(7); for(i=0; i<a.length; i++) a[i] = i; a[3] = undefined; a[a.length-1]; a" : ("0,1,2,,4,5,6", [0, 1, 2, None, 4, 5, 6]),
                "a = Array(7); for(i=0; i<a.length - 1; i++) a[i] = i; a[a.length-1]; a" : ("0,1,2,3,4,5,", [0, 1, 2, 3, 4, 5, None]),
                "a = Array(7); for(i=1; i<a.length; i++) a[i] = i; a[a.length-1]; a" : (",1,2,3,4,5,6", [None, 1, 2, 3, 4, 5, 6])
            }

            for code, (keys, values) in cases.items():
                array = ctxt.eval(code)

                self.assertEquals(keys, str(array))
                self.assertEquals(values, [array[i] for i in range(len(array))])

    def testMultiDimArray(self):
        with JSContext() as ctxt:
            ret = ctxt.eval("""
                ({
                    'test': function(){
                        return  [
                            [ 1, 'abla' ],
                            [ 2, 'ajkss' ],
                        ]
                    }
                })
                """).test()

            self.assertEquals([[1, 'abla'], [2, 'ajkss']], convert(ret))

    def testLazyConstructor(self):
        class Globals(JSClass):
            def __init__(self):
                self.array=JSArray([1,2,3])

        with JSContext(Globals()) as ctxt:
            self.assertEqual(2, ctxt.eval("""array[1]"""))

    def testForEach(self):
        class NamedClass(object):
            foo = 1

            def __init__(self):
                self.bar = 2

            @property
            def foobar(self):
                return self.foo + self.bar

        def gen(x):
            for i in range(x):
                yield i

        with JSContext() as ctxt:
            func = ctxt.eval("""(function (k) {
                var result = [];
                for (var prop in k) {
                  result.push(prop);
                }
                return result;
            })""")

            self.assertEquals(["bar", "foo", "foobar"], list(func(NamedClass())))
            self.assertEquals(["0", "1", "2"], list(func([1, 2, 3])))
            self.assertEquals(["0", "1", "2"], list(func((1, 2, 3))))
            self.assertEquals(["1", "2", "3"], list(func({1:1, 2:2, 3:3})))

            self.assertEquals(["0", "1", "2"], list(func(gen(3))))

    def testDict(self):
        import UserDict

        with JSContext() as ctxt:
            obj = ctxt.eval("var r = { 'a' : 1, 'b' : 2 }; r")

            self.assertEqual(1, obj.a)
            self.assertEqual(2, obj.b)

            self.assertEqual({ 'a' : 1, 'b' : 2 }, dict(obj))

            self.assertEqual({ 'a': 1,
                               'b': [1, 2, 3],
                               'c': { 'str' : 'goofy',
                                      'float' : 1.234,
                                      'obj' : { 'name': 'john doe' }},
                               'd': True,
                               'e': None },
                             convert(ctxt.eval("""var x =
                             { a: 1,
                               b: [1, 2, 3],
                               c: { str: 'goofy',
                                    float: 1.234,
                                    obj: { name: 'john doe' }},
                               d: true,
                               e: null }; x""")))

    def testDate(self):
        with JSContext() as ctxt:
            now1 = ctxt.eval("new Date();")

            self.assert_(now1)

            now2 = datetime.utcnow()

            delta = now2 - now1 if now2 > now1 else now1 - now2

            self.assert_(delta < timedelta(seconds=1))

            func = ctxt.eval("(function (d) { return d.toString(); })")

            now = datetime.now()

            self.assert_(str(func(now)).startswith(now.strftime("%a %b %d %Y %H:%M:%S")))

    def testUnicode(self):
        with JSContext() as ctxt:
            self.assertEquals(u"人", unicode(ctxt.eval(u"\"人\""), "utf-8"))
            self.assertEquals(u"é", unicode(ctxt.eval(u"\"é\""), "utf-8"))

            func = ctxt.eval("(function (msg) { return msg.length; })")

            self.assertEquals(2, func(u"测试"))

    def testClassicStyleObject(self):
        class FileSystemWarpper:
            @property
            def cwd(self):
                return os.getcwd()

        class Global:
            @property
            def fs(self):
                return FileSystemWarpper()

        with JSContext(Global()) as ctxt:
            self.assertEquals(os.getcwd(), ctxt.eval("fs.cwd"))

    def testRefCount(self):
        count = sys.getrefcount(None)

        class Global(JSClass):
            pass

        with JSContext(Global()) as ctxt:
            ctxt.eval("""
                var none = null;
            """)

            self.assertEquals(count+1, sys.getrefcount(None))

            ctxt.eval("""
                var none = null;
            """)

            self.assertEquals(count+1, sys.getrefcount(None))

    def testProperty(self):
        class Global(JSClass):
            def __init__(self, name):
                self._name = name
            def getname(self):
                return self._name
            def setname(self, name):
                self._name = name
            def delname(self):
                self._name = 'deleted'

            name = property(getname, setname, delname)

        g = Global('world')

        with JSContext(g) as ctxt:
            self.assertEquals('world', ctxt.eval("name"))
            self.assertEquals('flier', ctxt.eval("this.name = 'flier';"))
            self.assertEquals('flier', ctxt.eval("name"))
            self.assert_(ctxt.eval("delete name"))
            ###
            # FIXME replace the global object with Python object
            #
            #self.assertEquals('deleted', ctxt.eval("name"))
            #ctxt.eval("__defineGetter__('name', function() { return 'fixed'; });")
            #self.assertEquals('fixed', ctxt.eval("name"))

    def testGetterAndSetter(self):
        class Global(JSClass):
           def __init__(self, testval):
               self.testval = testval

        with JSContext(Global("Test Value A")) as ctxt:
           self.assertEquals("Test Value A", ctxt.locals.testval)
           ctxt.eval("""
               this.__defineGetter__("test", function() {
                   return this.testval;
               });
               this.__defineSetter__("test", function(val) {
                   this.testval = val;
               });
           """)
           self.assertEquals("Test Value A",  ctxt.locals.test)

           ctxt.eval("test = 'Test Value B';")

           self.assertEquals("Test Value B",  ctxt.locals.test)

    def testDestructor(self):
        import gc

        owner = self
        owner.deleted = False

        class Hello(object):
            def say(self):
                pass

            def __del__(self):
                owner.deleted = True

        def test():
            with JSContext() as ctxt:
                fn = ctxt.eval("(function (obj) { obj.say(); })")

                obj = Hello()

                self.assert_(2, sys.getrefcount(obj))

                fn(obj)

                self.assert_(3, sys.getrefcount(obj))

                del obj

        test()

        self.assertFalse(owner.deleted)

        JSEngine.collect()
        gc.collect()

        self.assert_(self.deleted)

    def testNullInString(self):
        with JSContext() as ctxt:
            fn = ctxt.eval("(function (s) { return s; })")

            self.assertEquals("hello \0 world", fn("hello \0 world"))

    def testLivingObjectCache(self):
        class Global(JSClass):
            i = 1
            b = True
            o = object()

        with JSContext(Global()) as ctxt:
            self.assert_(ctxt.eval("i == i"))
            self.assert_(ctxt.eval("b == b"))
            self.assert_(ctxt.eval("o == o"))

    def testNamedSetter(self):
        class Obj(JSClass):
            @property
            def p(self):
                return self._p

            @p.setter
            def p(self, value):
                self._p = value

        class Global(JSClass):
            def __init__(self):
                self.obj = Obj()
                self.d = {}
                self.p = None

        with JSContext(Global()) as ctxt:
            ctxt.eval("""
            x = obj;
            x.y = 10;
            x.p = 10;
            d.y = 10;
            """)
            self.assertEquals(10, ctxt.eval("obj.y"))
            self.assertEquals(10, ctxt.eval("obj.p"))
            self.assertEquals(10, ctxt.locals.d['y'])

    def testWatch(self):
        class Obj(JSClass):
            def __init__(self):
                self.p = 1

        class Global(JSClass):
            def __init__(self):
                self.o = Obj()

        with JSContext(Global()) as ctxt:
            ctxt.eval("""
            o.watch("p", function (id, oldval, newval) {
                return oldval + newval;
            });
            """)

            self.assertEquals(1, ctxt.eval("o.p"))

            ctxt.eval("o.p = 2;")

            self.assertEquals(3, ctxt.eval("o.p"))

            ctxt.eval("delete o.p;")

            self.assertEquals(None, ctxt.eval("o.p"))

            ctxt.eval("o.p = 2;")

            self.assertEquals(2, ctxt.eval("o.p"))

            ctxt.eval("o.unwatch('p');")

            ctxt.eval("o.p = 1;")

            self.assertEquals(1, ctxt.eval("o.p"))

    def testReferenceError(self):
        class Global(JSClass):
            def __init__(self):
                self.s = self

        with JSContext(Global()) as ctxt:
            self.assertRaises(ReferenceError, ctxt.eval, 'x')

            self.assert_(ctxt.eval("typeof(x) === 'undefined'"))

            self.assert_(ctxt.eval("typeof(String) === 'function'"))

            self.assert_(ctxt.eval("typeof(s.String) === 'undefined'"))

            self.assert_(ctxt.eval("typeof(s.z) === 'undefined'"))

    def testRaiseExceptionInGetter(self):
        class Document(JSClass):
            def __getattr__(self, name):
                if name == 'y':
                    raise TypeError()

                return JSClass.__getattr__(self, name)

        class Global(JSClass):
            def __init__(self):
                self.document = Document()

        with JSContext(Global()) as ctxt:
            self.assertEquals(None, ctxt.eval('document.x'))
            self.assertRaises(TypeError, ctxt.eval, 'document.y')

class TestMultithread(unittest.TestCase):
    def testLocker(self):
        self.assertFalse(JSLocker.active)
        self.assertFalse(JSLocker.locked)

        with JSLocker() as outter_locker:
            self.assertTrue(JSLocker.active)
            self.assertTrue(JSLocker.locked)

            self.assertTrue(outter_locker)

            with JSLocker() as inner_locker:
                self.assertTrue(JSLocker.locked)

                self.assertTrue(outter_locker)
                self.assertTrue(inner_locker)

                with JSUnlocker() as unlocker:
                    self.assertFalse(JSLocker.locked)

                    self.assertTrue(outter_locker)
                    self.assertTrue(inner_locker)

                self.assertTrue(JSLocker.locked)

        self.assertTrue(JSLocker.active)
        self.assertFalse(JSLocker.locked)

        locker = JSLocker()

        with JSContext():
            self.assertRaises(RuntimeError, locker.__enter__)
            self.assertRaises(RuntimeError, locker.__exit__, None, None, None)

        del locker

    def testMultiPythonThread(self):
        import time, threading

        class Global:
            count = 0
            started = threading.Event()
            finished = threading.Semaphore(0)

            def sleep(self, ms):
                time.sleep(ms / 1000.0)

                self.count += 1

        g = Global()

        def run():
            with JSContext(g) as ctxt:
                ctxt.eval("""
                    started.wait();

                    for (i=0; i<10; i++)
                    {
                        sleep(100);
                    }

                    finished.release();
                """)

        threading.Thread(target=run).start()

        now = time.time()

        self.assertEqual(0, g.count)

        g.started.set()
        g.finished.acquire()

        self.assertEqual(10, g.count)

        self.assert_((time.time() - now) >= 1)

    def testMultiJavascriptThread(self):
        import time, threading

        class Global:
            result = []

            def add(self, value):
                with JSUnlocker():
                    time.sleep(0.1)

                    self.result.append(value)

        g = Global()

        def run():
            with JSContext(g) as ctxt:
                ctxt.eval("""
                    for (i=0; i<10; i++)
                        add(i);
                """)

        threads = [threading.Thread(target=run), threading.Thread(target=run)]

        with JSLocker():
            for t in threads: t.start()

        for t in threads: t.join()

        self.assertEqual(20, len(g.result))

    def _testPreemptionJavascriptThreads(self):
        import time, threading

        class Global:
            result = []

            def add(self, value):
                # we use preemption scheduler to switch between threads
                # so, just comment the JSUnlocker
                #
                # with JSUnlocker() as unlocker:
                time.sleep(0.1)

                self.result.append(value)

        g = Global()

        def run():
            with JSContext(g) as ctxt:
                ctxt.eval("""
                    for (i=0; i<10; i++)
                        add(i);
                """)

        threads = [threading.Thread(target=run), threading.Thread(target=run)]

        with JSLocker() as locker:
            JSLocker.startPreemption(100)

            for t in threads: t.start()

        for t in threads: t.join()

        self.assertEqual(20, len(g.result))

class TestEngine(unittest.TestCase):
    def testClassProperties(self):
        with JSContext() as ctxt:
            self.assert_(str(JSEngine.version).startswith("3."))
            self.assertFalse(JSEngine.dead)

    def testCompile(self):
        with JSContext() as ctxt:
            with JSEngine() as engine:
                s = engine.compile("1+2")

                self.assert_(isinstance(s, _PyV8.JSScript))

                self.assertEquals("1+2", s.source)
                self.assertEquals(3, int(s.run()))

                self.assertRaises(SyntaxError, engine.compile, "1+")

    def testPrecompile(self):
        with JSContext() as ctxt:
            with JSEngine() as engine:
                data = engine.precompile("1+2")

                self.assert_(data)
                self.assertEquals(28, len(data))

                s = engine.compile("1+2", precompiled=data)

                self.assert_(isinstance(s, _PyV8.JSScript))

                self.assertEquals("1+2", s.source)
                self.assertEquals(3, int(s.run()))

                self.assertRaises(SyntaxError, engine.precompile, "1+")

    def testUnicodeSource(self):
        class Global(JSClass):
            var = u'测试'

            def __getattr__(self, name):
                if (name.decode('utf-8')) == u'变量':
                    return self.var

                return JSClass.__getattr__(self, name)

        g = Global()

        with JSContext(g) as ctxt:
            with JSEngine() as engine:
                src = u"""
                function 函数() { return 变量.length; }

                函数();
                """

                data = engine.precompile(src)

                self.assert_(data)
                self.assertEquals(48, len(data))

                s = engine.compile(src, precompiled=data)

                self.assert_(isinstance(s, _PyV8.JSScript))

                self.assertEquals(src.encode('utf-8'), s.source)
                self.assertEquals(2, s.run())

                self.assert_(hasattr(ctxt.locals, u'函数'.encode('utf-8')))

                func = getattr(ctxt.locals, u'函数'.encode('utf-8'))

                self.assert_(isinstance(func, _PyV8.JSFunction))

                self.assertEquals(u'函数'.encode('utf-8'), func.name)
                self.assertEquals("", func.resname)
                self.assertEquals(1, func.linenum)
                self.assertEquals(0, func.lineoff)
                self.assertEquals(0, func.coloff)

                setattr(ctxt.locals, u'变量'.encode('utf-8'), u'测试长字符串')

                self.assertEquals(6, func())

    def testExtension(self):
        extSrc = """function hello(name) { return "hello " + name + " from javascript"; }"""
        extJs = JSExtension("hello/javascript", extSrc)

        self.assert_(extJs)
        self.assertEqual("hello/javascript", extJs.name)
        self.assertEqual(extSrc, extJs.source)
        self.assertFalse(extJs.autoEnable)
        self.assertTrue(extJs.registered)

        TestEngine.extJs = extJs

        with JSContext(extensions=['hello/javascript']) as ctxt:
            self.assertEqual("hello flier from javascript", ctxt.eval("hello('flier')"))

        # test the auto enable property

        with JSContext() as ctxt:
            self.assertRaises(ReferenceError, ctxt.eval, "hello('flier')")

        extJs.autoEnable = True
        self.assertTrue(extJs.autoEnable)

        with JSContext() as ctxt:
            self.assertEqual("hello flier from javascript", ctxt.eval("hello('flier')"))

        extJs.autoEnable = False
        self.assertFalse(extJs.autoEnable)

        with JSContext() as ctxt:
            self.assertRaises(ReferenceError, ctxt.eval, "hello('flier')")

    def testNativeExtension(self):
        extSrc = "native function hello();"
        extPy = JSExtension("hello/python", extSrc, lambda func: lambda name: "hello " + name + " from python", register=False)
        self.assert_(extPy)
        self.assertEqual("hello/python", extPy.name)
        self.assertEqual(extSrc, extPy.source)
        self.assertFalse(extPy.autoEnable)
        self.assertFalse(extPy.registered)
        extPy.register()
        self.assertTrue(extPy.registered)

        TestEngine.extPy = extPy

        with JSContext(extensions=['hello/python']) as ctxt:
            self.assertEqual("hello flier from python", ctxt.eval("hello('flier')"))

    def _testSerialize(self):
        data = None

        self.assertFalse(JSContext.entered)

        with JSContext() as ctxt:
            self.assert_(JSContext.entered)

            #ctxt.eval("function hello(name) { return 'hello ' + name; }")

            data = JSEngine.serialize()

        self.assert_(data)
        self.assert_(len(data) > 0)

        self.assertFalse(JSContext.entered)

        #JSEngine.deserialize()

        self.assert_(JSContext.entered)

        self.assertEquals('hello flier', JSContext.current.eval("hello('flier');"))

    def testEval(self):
        with JSContext() as ctxt:
            self.assertEquals(3, int(ctxt.eval("1+2")))

    def testGlobal(self):
        class Global(JSClass):
            version = "1.0"

        with JSContext(Global()) as ctxt:
            vars = ctxt.locals

            # getter
            self.assertEquals(Global.version, str(vars.version))
            self.assertEquals(Global.version, str(ctxt.eval("version")))

            self.assertRaises(ReferenceError, ctxt.eval, "nonexists")

            # setter
            self.assertEquals(2.0, float(ctxt.eval("version = 2.0")))

            self.assertEquals(2.0, float(vars.version))

    def testThis(self):
        class Global(JSClass):
            version = 1.0

        with JSContext(Global()) as ctxt:
            self.assertEquals("[object Global]", str(ctxt.eval("this")))

            self.assertEquals(1.0, float(ctxt.eval("this.version")))

    def testObjectBuildInMethods(self):
        class Global(JSClass):
            version = 1.0

        with JSContext(Global()) as ctxt:
            self.assertEquals("[object Global]", str(ctxt.eval("this.toString()")))
            self.assertEquals("[object Global]", str(ctxt.eval("this.toLocaleString()")))
            self.assertEquals(Global.version, float(ctxt.eval("this.valueOf()").version))

            self.assert_(bool(ctxt.eval("this.hasOwnProperty(\"version\")")))

            self.assertFalse(ctxt.eval("this.hasOwnProperty(\"nonexistent\")"))

    def testPythonWrapper(self):
        class Global(JSClass):
            s = [1, 2, 3]
            d = {'a': {'b': 'c'}, 'd': ['e', 'f']}

        g = Global()

        with JSContext(g) as ctxt:
            ctxt.eval("""
                s[2] = s[1] + 2;
                s[0] = s[1];
                delete s[1];
            """)
            self.assertEquals([2, 4], g.s)
            self.assertEquals('c', ctxt.eval("d.a.b"))
            self.assertEquals(['e', 'f'], ctxt.eval("d.d"))
            ctxt.eval("""
                d.a.q = 4
                delete d.d
            """)
            self.assertEquals(4, g.d['a']['q'])
            self.assertEquals(None, ctxt.eval("d.d"))

    def testMemoryAllocationCallback(self):
        alloc = {}

        def callback(space, action, size):
            alloc[(space, action)] = alloc.setdefault((space, action), 0) + size

        JSEngine.setMemoryAllocationCallback(callback)

        with JSContext() as ctxt:
            self.assertEquals({}, alloc)

            ctxt.eval("var o = new Array(1000);")

            alloc.has_key((JSObjectSpace.Code, JSAllocationAction.alloc))

        JSEngine.setMemoryAllocationCallback(None)

class TestDebug(unittest.TestCase):
    def setUp(self):
        self.engine = JSEngine()

    def tearDown(self):
        del self.engine

    events = []

    def processDebugEvent(self, event):
        try:
            logging.debug("receive debug event: %s", repr(event))

            self.events.append(repr(event))
        except:
            logging.error("fail to process debug event")
            logging.debug(traceback.extract_stack())

    def testEventDispatch(self):
        debugger = JSDebugger()

        self.assert_(not debugger.enabled)

        debugger.onBreak = lambda evt: self.processDebugEvent(evt)
        debugger.onException = lambda evt: self.processDebugEvent(evt)
        debugger.onNewFunction = lambda evt: self.processDebugEvent(evt)
        debugger.onBeforeCompile = lambda evt: self.processDebugEvent(evt)
        debugger.onAfterCompile = lambda evt: self.processDebugEvent(evt)

        with JSContext() as ctxt:
            debugger.enabled = True

            self.assertEquals(3, int(ctxt.eval("function test() { text = \"1+2\"; return eval(text) } test()")))

            debugger.enabled = False

            self.assertRaises(JSError, JSContext.eval, ctxt, "throw 1")

            self.assert_(not debugger.enabled)

        self.assertEquals(4, len(self.events))

class TestProfile(unittest.TestCase):
    def _testStart(self):
        self.assertFalse(profiler.started)

        profiler.start()

        self.assert_(profiler.started)

        profiler.stop()

        self.assertFalse(profiler.started)

    def _testResume(self):
        self.assert_(profiler.paused)

        self.assertEquals(profiler.Modules.cpu, profiler.modules)

        profiler.resume()

        profiler.resume(profiler.Modules.heap)

        # TODO enable profiler with resume
        #self.assertFalse(profiler.paused)


class TestAST(unittest.TestCase):

    class Checker(object):
        def __init__(self, testcase):
            self.testcase = testcase
            self.called = 0

        def __getattr__(self, name):
            return getattr(self.testcase, name)

        def test(self, script):
            with JSContext() as ctxt:
                JSEngine().compile(script).visit(self)

            return self.called

        def onProgram(self, prog):
            self.ast = prog.toAST()
            self.json = json.loads(prog.toJSON())

            for decl in prog.scope.declarations:
                decl.visit(self)

            for stmt in prog.body:
                stmt.visit(self)

        def onBlock(self, block):
            for stmt in block.statements:
                stmt.visit(self)

        def onExpressionStatement(self, stmt):
            stmt.expression.visit(self)

            #print type(stmt.expression), stmt.expression

    def testBlock(self):
        class BlockChecker(TestAST.Checker):
            def onBlock(self, stmt):
                self.called += 1

                self.assertEquals(AST.NodeType.Block, stmt.type)

                self.assert_(stmt.initializerBlock)
                self.assertFalse(stmt.anonymous)

                target = stmt.breakTarget
                self.assert_(target)
                self.assertFalse(target.bound)
                self.assert_(target.unused)
                self.assertFalse(target.linked)

                self.assertEquals(2, len(stmt.statements))

                self.assertEquals(['%InitializeVarGlobal("i", 0);', '%InitializeVarGlobal("j", 0);'], [str(s) for s in stmt.statements])

        checker = BlockChecker(self)
        self.assertEquals(1, checker.test("var i, j;"))
        self.assertEquals("""FUNC
. NAME ""
. INFERRED NAME ""
. DECLS
. . VAR "i"
. . VAR "j"
. BLOCK INIT
. . CALL RUNTIME  InitializeVarGlobal
. . . LITERAL "i"
. . . LITERAL 0
. . CALL RUNTIME  InitializeVarGlobal
. . . LITERAL "j"
. . . LITERAL 0
""", checker.ast)
        self.assertEquals([u'FunctionLiteral', {u'name': u''},
            [u'Declaration', {u'mode': u'VAR'},
                [u'Variable', {u'name': u'i'}]
            ], [u'Declaration', {u'mode':u'VAR'},
                [u'Variable', {u'name': u'j'}]
            ], [u'Block',
                [u'ExpressionStatement', [u'CallRuntime', {u'name': u'InitializeVarGlobal'},
                    [u'Literal', {u'handle':u'i'}],
                    [u'Literal', {u'handle': 0}]]],
                [u'ExpressionStatement', [u'CallRuntime', {u'name': u'InitializeVarGlobal'},
                    [u'Literal', {u'handle': u'j'}],
                    [u'Literal', {u'handle': 0}]]]
            ]
        ], checker.json)

    def testIfStatement(self):
        class IfStatementChecker(TestAST.Checker):
            def onIfStatement(self, stmt):
                self.called += 1

                self.assert_(stmt)
                self.assertEquals(AST.NodeType.IfStatement, stmt.type)

                self.assertEquals(7, stmt.pos)
                stmt.pos = 100
                self.assertEquals(100, stmt.pos)

                self.assert_(stmt.hasThenStatement)
                self.assert_(stmt.hasElseStatement)

                self.assertEquals("((value % 2) == 0)", str(stmt.condition))
                self.assertEquals("{ s = \"even\"; }", str(stmt.thenStatement))
                self.assertEquals("{ s = \"odd\"; }", str(stmt.elseStatement))

                self.assertFalse(stmt.condition.isPropertyName)

        self.assertEquals(1, IfStatementChecker(self).test("var s; if (value % 2 == 0) { s = 'even'; } else { s = 'odd'; }"))

    def testForStatement(self):
        class ForStatementChecker(TestAST.Checker):
            def onForStatement(self, stmt):
                self.called += 1

                self.assertEquals("{ j += i; }", str(stmt.body))

                self.assertEquals("i = 0;", str(stmt.init))
                self.assertEquals("(i < 10)", str(stmt.condition))
                self.assertEquals("(i++);", str(stmt.next))

                target = stmt.continueTarget

                self.assert_(target)
                self.assertFalse(target.bound)
                self.assert_(target.unused)
                self.assertFalse(target.linked)
                self.assertFalse(stmt.fastLoop)

            def onForInStatement(self, stmt):
                self.called += 1

                self.assertEquals("{ out += name; }", str(stmt.body))

                self.assertEquals("name", str(stmt.each))
                self.assertEquals("names", str(stmt.enumerable))

            def onWhileStatement(self, stmt):
                self.called += 1

                self.assertEquals("{ i += 1; }", str(stmt.body))

                self.assertEquals("(i < 10)", str(stmt.condition))

            def onDoWhileStatement(self, stmt):
                self.called += 1

                self.assertEquals("{ i += 1; }", str(stmt.body))

                self.assertEquals("(i < 10)", str(stmt.condition))
                self.assertEquals(253, stmt.conditionPos)

        self.assertEquals(4, ForStatementChecker(self).test("""
            var i, j;

            for (i=0; i<10; i++) { j+=i; }

            var names = new Array();
            var out = '';

            for (name in names) { out += name; }

            while (i<10) { i += 1; }

            do { i += 1; } while (i<10);
        """))

    def testCallStatements(self):
        class CallStatementChecker(TestAST.Checker):
            def onDeclaration(self, decl):
                self.called += 1

                var = decl.proxy

                if var.name == 's':
                    self.assertEquals(AST.VarMode.var, decl.mode)
                    self.assertEquals(None, decl.function)

                    self.assert_(var.isValidLeftHandSide)
                    self.assertFalse(var.isArguments)
                    self.assertFalse(var.isThis)
                elif var.name == 'hello':
                    self.assertEquals(AST.VarMode.var, decl.mode)
                    self.assert_(decl.function)
                    self.assertEquals('(function hello(name) { s = ("Hello " + name); })', str(decl.function))
                elif var.name == 'dog':
                    self.assertEquals(AST.VarMode.var, decl.mode)
                    self.assert_(decl.function)
                    self.assertEquals('(function dog(name) { (this).name = name; })', str(decl.function))

            def onCall(self, expr):
                self.called += 1

                self.assertEquals("hello", str(expr.expression))
                self.assertEquals(['"flier"'], [str(arg) for arg in expr.args])
                self.assertEquals(143, expr.pos)

            def onCallNew(self, expr):
                self.called += 1

                self.assertEquals("dog", str(expr.expression))
                self.assertEquals(['"cat"'], [str(arg) for arg in expr.args])
                self.assertEquals(171, expr.pos)

            def onCallRuntime(self, expr):
                self.called += 1

                self.assertEquals("InitializeVarGlobal", expr.name)
                self.assertEquals(['"s"', '0'], [str(arg) for arg in expr.args])
                self.assertFalse(expr.isJsRuntime)

        self.assertEquals(6,  CallStatementChecker(self).test("""
            var s;
            function hello(name) { s = "Hello " + name; }
            function dog(name) { this.name = name; }
            hello("flier");
            new dog("cat");
        """))

    def testTryStatements(self):
        class TryStatementsChecker(TestAST.Checker):
            def onThrow(self, expr):
                self.called += 1

                self.assertEquals('"abc"', str(expr.exception))
                self.assertEquals(54, expr.pos)

            def onTryCatchStatement(self, stmt):
                self.called += 1

                self.assertEquals("{ throw \"abc\"; }", str(stmt.tryBlock))
                #FIXME self.assertEquals([], stmt.targets)

                stmt.tryBlock.visit(self)

                self.assertEquals("err", str(stmt.variable.name))
                self.assertEquals("{ s = err; }", str(stmt.catchBlock))

            def onTryFinallyStatement(self, stmt):
                self.called += 1

                self.assertEquals("{ throw \"abc\"; }", str(stmt.tryBlock))
                #FIXME self.assertEquals([], stmt.targets)

                self.assertEquals("{ s += \".\"; }", str(stmt.finallyBlock))

        self.assertEquals(3, TryStatementsChecker(self).test("""
            var s;
            try {
                throw "abc";
            }
            catch (err) {
                s = err;
            };

            try {
                throw "abc";
            }
            finally {
                s += ".";
            }
        """))

    def testLiterals(self):
        class LiteralChecker(TestAST.Checker):
            def onCallRuntime(self, expr):
                expr.args[1].visit(self)

            def onLiteral(self, litr):
                self.called += 1

                self.assertFalse(litr.isPropertyName)
                self.assertFalse(litr.isNull)
                self.assertFalse(litr.isTrue)

            def onRegExpLiteral(self, litr):
                self.called += 1

                self.assertEquals("test", litr.pattern)
                self.assertEquals("g", litr.flags)

            def onObjectLiteral(self, litr):
                self.called += 1

                self.assertEquals('constant:"name"="flier",constant:"sex"=true',
                                  ",".join(["%s:%s=%s" % (prop.kind, prop.key, prop.value) for prop in litr.properties]))

            def onArrayLiteral(self, litr):
                self.called += 1

                self.assertEquals('"hello","world",42',
                                  ",".join([str(value) for value in litr.values]))

        self.assertEquals(4, LiteralChecker(self).test("""
            false;
            /test/g;
            var o = { name: 'flier', sex: true };
            var a = ['hello', 'world', 42];
        """))

    def testOperations(self):
        class OperationChecker(TestAST.Checker):
            def onUnaryOperation(self, expr):
                self.called += 1

                self.assertEquals(AST.Op.BIT_NOT, expr.op)
                self.assertEquals("i", expr.expression.name)

                #print "unary", expr

            def onIncrementOperation(self, expr):
                self.fail()

            def onBinaryOperation(self, expr):
                self.called += 1

                self.assertEquals(AST.Op.ADD, expr.op)
                self.assertEquals("i", str(expr.left))
                self.assertEquals("j", str(expr.right))
                self.assertEquals(28, expr.pos)

                #print "bin", expr

            def onAssignment(self, expr):
                self.called += 1

                self.assertEquals(AST.Op.ASSIGN_ADD, expr.op)
                self.assertEquals(AST.Op.ADD, expr.binop)

                self.assertEquals("i", str(expr.target))
                self.assertEquals("1", str(expr.value))
                self.assertEquals(41, expr.pos)

                self.assertEquals("(i + 1)", str(expr.binOperation))

                self.assert_(expr.compound)

            def onCountOperation(self, expr):
                self.called += 1

                self.assertFalse(expr.prefix)
                self.assert_(expr.postfix)

                self.assertEquals(AST.Op.INC, expr.op)
                self.assertEquals(AST.Op.ADD, expr.binop)
                self.assertEquals(55, expr.pos)
                self.assertEquals("i", expr.expression.name)

                #print "count", expr

            def onCompareOperation(self, expr):
                self.called += 1

                if self.called == 4:
                    self.assertEquals(AST.Op.EQ, expr.op)
                    self.assertEquals(68, expr.pos) # i==j
                else:
                    self.assertEquals(AST.Op.EQ_STRICT, expr.op)
                    self.assertEquals(82, expr.pos) # i===j

                self.assertEquals("i", str(expr.left))
                self.assertEquals("j", str(expr.right))

                #print "comp", expr

            def onConditional(self, expr):
                self.called += 1

                self.assertEquals("(i > j)", str(expr.condition))
                self.assertEquals("i", str(expr.thenExpr))
                self.assertEquals("j", str(expr.elseExpr))

                self.assertEquals(112, expr.thenExprPos)
                self.assertEquals(114, expr.elseExprPos)

        self.assertEquals(7, OperationChecker(self).test("""
        var i, j;
        i+j;
        i+=1;
        i++;
        i==j;
        i===j;
        ~i;
        i>j?i:j;
        """))

if __name__ == '__main__':
    if "-v" in sys.argv:
        level = logging.DEBUG
    else:
        level = logging.WARN

    if "-p" in sys.argv:
        sys.argv.remove("-p")
        print "Press any key to continue..."
        raw_input()

    logging.basicConfig(level=level, format='%(asctime)s %(levelname)s %(message)s')

    logging.info("testing PyV8 module %s with V8 v%s", __version__, JSEngine.version)

    unittest.main()

########NEW FILE########
__FILENAME__ = PyV8
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import with_statement

import sys, os
import StringIO

import _PyV8

__all__ = ["JSError", "JSArray", "JSClass", "JSEngine", "JSContext", \
           "JSExtension", "JSLocker", "JSUnlocker", "debugger", "profiler", "AST"]

class JSError(Exception):
    def __init__(self, impl):
        Exception.__init__(self)
        
        self._impl = impl
        
    def __str__(self):
        return str(self._impl)
        
    def __unicode__(self):
        return unicode(self._impl)
        
    def __getattribute__(self, attr):
        impl = super(JSError, self).__getattribute__("_impl")
        
        try:
            return getattr(impl, attr)
        except AttributeError:
            return super(JSError, self).__getattribute__(attr)
            
_PyV8._JSError._jsclass = JSError

JSArray = _PyV8.JSArray
JSExtension = _PyV8.JSExtension

class JSLocker(_PyV8.JSLocker):
    def __enter__(self):       
        self.enter()
        
        if JSContext.entered:
            self.leave()
            raise RuntimeError("Lock should be acquired before enter the context")
        
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        if JSContext.entered:
            self.leave()
            raise RuntimeError("Lock should be released after leave the context")

        self.leave()
        
    def __nonzero__(self):
        return self.entered()

class JSUnlocker(_PyV8.JSUnlocker):
    def __enter__(self):
        self.enter()
        
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.leave()

    def __nonzero__(self):
        return self.entered()
        
class JSClass(object):    
    def toString(self):
        "Returns a string representation of an object."
        return "[object %s]" % self.__class__.__name__
    
    def toLocaleString(self):
        "Returns a value as a string value appropriate to the host environment's current locale."
        return self.toString()
    
    def valueOf(self):
        "Returns the primitive value of the specified object."
        return self
    
    def hasOwnProperty(self, name):
        "Returns a Boolean value indicating whether an object has a property with the specified name."
        return hasattr(self, name)
    
    def isPrototypeOf(self, obj):
        "Returns a Boolean value indicating whether an object exists in the prototype chain of another object."
        raise NotImplementedError()
    
    def __defineGetter__(self, name, getter):
        "Binds an object's property to a function to be called when that property is looked up."
        if hasattr(type(self), name):
            setter = getattr(type(self), name).fset
        else:
            setter = None
        
        setattr(type(self), name, property(fget=getter, fset=setter))
    
    def __lookupGetter__(self, name):
        "Return the function bound as a getter to the specified property."
        return self.name.fget
    
    def __defineSetter__(self, name, setter):
        "Binds an object's property to a function to be called when an attempt is made to set that property."
        if hasattr(type(self), name):
            getter = getattr(type(self), name).fget
        else:
            getter = None
        
        setattr(type(self), name, property(fget=getter, fset=setter))
    
    def __lookupSetter__(self, name):
        "Return the function bound as a setter to the specified property."
        return self.name.fset

class JSDebug(object):
    class FrameData(object):
        def __init__(self, frame, count, name, value):
            self.frame = frame
            self.count = count
            self.name = name
            self.value = value
            
        def __len__(self):
            return self.count(self.frame)
        
        def __iter__(self):
            for i in xrange(self.count(self.frame)):
                yield (self.name(self.frame, i), self.value(self.frame, i))
        
    class Frame(object):
        def __init__(self, frame):
            self.frame = frame
            
        @property
        def index(self):
            return int(self.frame.index())
            
        @property
        def function(self):
            return self.frame.func()
            
        @property
        def receiver(self):
            return self.frame.receiver()
            
        @property
        def isConstructCall(self):
            return bool(self.frame.isConstructCall())
            
        @property
        def isDebuggerFrame(self):
            return bool(self.frame.isDebuggerFrame())
            
        @property
        def argumentCount(self):
            return int(self.frame.argumentCount())
                    
        def argumentName(self, idx):
            return str(self.frame.argumentName(idx))
                    
        def argumentValue(self, idx):
            return self.frame.argumentValue(idx)
            
        @property
        def arguments(self):
            return FrameData(self, self.argumentCount, self.argumentName, self.argumentValue)
            
        @property
        def localCount(self, idx):
            return int(self.frame.localCount())
                    
        def localName(self, idx):
            return str(self.frame.localName(idx))
                    
        def localValue(self, idx):
            return self.frame.localValue(idx)
            
        @property
        def locals(self):
            return FrameData(self, self.localCount, self.localName, self.localValue)
            
        @property
        def sourcePosition(self):
            return self.frame.sourcePosition()
            
        @property
        def sourceLine(self):
            return int(self.frame.sourceLine())
            
        @property
        def sourceColumn(self):
            return int(self.frame.sourceColumn())
            
        @property
        def sourceLineText(self):
            return str(self.frame.sourceLineText())
                    
        def evaluate(self, source, disable_break = True):
            return self.frame.evaluate(source, disable_break)
            
        @property
        def invocationText(self):
            return str(self.frame.invocationText())
            
        @property
        def sourceAndPositionText(self):
            return str(self.frame.sourceAndPositionText())
            
        @property
        def localsText(self):
            return str(self.frame.localsText())
            
        def __str__(self):
            return str(self.frame.toText())

    class Frames(object):
        def __init__(self, state):
            self.state = state
            
        def __len__(self):
            return self.state.frameCount
            
        def __iter__(self):
            for i in xrange(self.state.frameCount):                
                yield self.state.frame(i)
    
    class State(object):
        def __init__(self, state):            
            self.state = state
            
        @property
        def frameCount(self):
            return int(self.state.frameCount())
            
        def frame(self, idx = None):
            return JSDebug.Frame(self.state.frame(idx))
        
        @property    
        def selectedFrame(self):
            return int(self.state.selectedFrame())
        
        @property
        def frames(self):
            return JSDebug.Frames(self)
        
        def __repr__(self):
            s = StringIO.StringIO()
            
            try:
                for frame in self.frames:
                    s.write(str(frame))
                    
                return s.getvalue()
            finally:
                s.close()
                
    class DebugEvent(object):
        pass
            
    class StateEvent(DebugEvent):
        __state = None

        @property
        def state(self):
            if not self.__state:
                self.__state = JSDebug.State(self.event.executionState())
            
            return self.__state
        
    class BreakEvent(StateEvent):
        type = _PyV8.JSDebugEvent.Break
        
        def __init__(self, event):
            self.event = event
        
    class ExceptionEvent(StateEvent):
        type = _PyV8.JSDebugEvent.Exception
        
        def __init__(self, event):
            self.event = event

    class NewFunctionEvent(DebugEvent):
        type = _PyV8.JSDebugEvent.NewFunction
        
        def __init__(self, event):
            self.event = event
            
    class Script(object):        
        def __init__(self, script):            
            self.script = script            
            
        @property
        def source(self):
            return self.script.source()
            
        @property
        def id(self):
            return self.script.id()
            
        @property
        def name(self):
            return self.script.name()
            
        @property
        def lineOffset(self):
            return self.script.lineOffset() 
            
        @property
        def lineCount(self):
            return self.script.lineCount()
        
        @property    
        def columnOffset(self):
            return self.script.columnOffset()
            
        @property
        def type(self):
            return self.script.type()
            
        def __repr__(self):
            return "<%s script %s @ %d:%d> : '%s'" % (self.type, self.name,
                                                      self.lineOffset, self.columnOffset,
                                                      self.source)
            
    class CompileEvent(StateEvent):
        def __init__(self, event):
            self.event = event

        @property
        def script(self):
            if not hasattr(self, "_script"):
                setattr(self, "_script", JSDebug.Script(self.event.script()))
            
            return self._script
        
        def __str__(self):
            return str(self.script)
            
    class BeforeCompileEvent(CompileEvent):
        type = _PyV8.JSDebugEvent.BeforeCompile        
        
        def __init__(self, event):            
            JSDebug.CompileEvent.__init__(self, event)
        
        def __repr__(self):
            return "before compile script: %s\n%s" % (repr(self.script), repr(self.state))
    
    class AfterCompileEvent(CompileEvent):
        type = _PyV8.JSDebugEvent.AfterCompile        

        def __init__(self, event):            
            JSDebug.CompileEvent.__init__(self, event)

        def __repr__(self):
            return "after compile script: %s\n%s" % (repr(self.script), repr(self.state))

    onMessage = None
    onBreak = None
    onException = None
    onNewFunction = None
    onBeforeCompile = None
    onAfterCompile = None    
    
    def isEnabled(self):
        return _PyV8.debug().enabled
    
    def setEnabled(self, enable):    
        dbg = _PyV8.debug()        
        
        if enable:            
            dbg.onDebugEvent = lambda type, evt: self.onDebugEvent(type, evt)
            dbg.onDebugMessage = lambda msg: self.onDebugMessage(msg)
        else:
            dbg.onDebugEvent = None
            dbg.onDebugMessage = None
            
        dbg.enabled = enable
            
    enabled = property(isEnabled, setEnabled)
        
    def onDebugMessage(self, msg):
        if self.onMessage:
            self.onMessage(msg)
            
    def onDebugEvent(self, type, evt):        
        if type == _PyV8.JSDebugEvent.Break:
            if self.onBreak: self.onBreak(JSDebug.BreakEvent(evt))
        elif type == _PyV8.JSDebugEvent.Exception:
            if self.onException: self.onException(JSDebug.ExceptionEvent(evt))
        elif type == _PyV8.JSDebugEvent.NewFunction:
            if self.onNewFunction: self.onNewFunction(JSDebug.NewFunctionEvent(evt))
        elif type == _PyV8.JSDebugEvent.BeforeCompile:
            if self.onBeforeCompile: self.onBeforeCompile(JSDebug.BeforeCompileEvent(evt))
        elif type == _PyV8.JSDebugEvent.AfterCompile:
            if self.onAfterCompile: self.onAfterCompile(JSDebug.AfterCompileEvent(evt))
        
debugger = JSDebug()

class JSProfiler(_PyV8.JSProfiler):
    Modules = _PyV8.JSProfilerModules
    
    @property
    def logs(self):
        pos = 0
        
        while True:
            size, buf = self.getLogLines(pos)
            
            if size == 0:
                break
            
            for line in buf.split('\n'):
                yield line
                    
            pos += size
        
profiler = JSProfiler()

class JSEngine(_PyV8.JSEngine):
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        del self

class JSContext(_PyV8.JSContext):
    def __init__(self, obj=None, extensions=[]):
        if JSLocker.actived:
            self.lock = JSLocker()
            self.lock.enter()
            
        _PyV8.JSContext.__init__(self, obj, extensions)
        
    def __enter__(self):
        self.enter()
        
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.leave()
        
        if hasattr(JSLocker, 'lock'):
            self.lock.leave()
            self.lock = None
            
        del self
        
# contribute by marc boeker <http://code.google.com/u/marc.boeker/>
def convert(obj):    
    if type(obj) == _PyV8.JSArray:
        return [convert(v) for v in obj]
    
    if type(obj) == _PyV8.JSObject:
        return dict([[str(k), convert(obj.__getattr__(str(k)))] for k in obj.__members__])
        
    return obj

if hasattr(_PyV8, 'AstScope'):
    class AST:
        Scope = _PyV8.AstScope
        Var = _PyV8.AstVariable
        Node = _PyV8.AstNode
        Statement = _PyV8.AstStatement
        Expression = _PyV8.AstExpression
        Expression.Context = _PyV8.AstExpressionContext
        Breakable = _PyV8.AstBreakableStatement
        Block = _PyV8.AstBlock
        Declaration = _PyV8.AstDeclaration
        Iteration = _PyV8.AstIterationStatement
        DoWhile = _PyV8.AstDoWhileStatement
        While = _PyV8.AstWhileStatement
        For = _PyV8.AstForStatement
        ForIn = _PyV8.AstForInStatement
        ExpressionStatement = _PyV8.AstExpressionStatement
        Continue = _PyV8.AstContinueStatement
        Break = _PyV8.AstBreakStatement
        Return = _PyV8.AstReturnStatement
        WithEnter = _PyV8.AstWithEnterStatement
        WithExit = _PyV8.AstWithExitStatement
        Case = _PyV8.AstCaseClause
        Switch = _PyV8.AstSwitchStatement
        Try = _PyV8.AstTryStatement
        TryCatch = _PyV8.AstTryCatchStatement
        TryFinally = _PyV8.AstTryFinallyStatement
        Debugger = _PyV8.AstDebuggerStatement
        Empty = _PyV8.AstEmptyStatement
        Literal = _PyV8.AstLiteral
        MaterializedLiteral = _PyV8.AstMaterializedLiteral
        Object = _PyV8.AstObjectLiteral
        RegExp = _PyV8.AstRegExpLiteral
        Array = _PyV8.AstArrayLiteral
        CatchExtension = _PyV8.AstCatchExtensionObject
        VarProxy = _PyV8.AstVariableProxy
        Slot = _PyV8.AstSlot
        Property = _PyV8.AstProperty
        Call = _PyV8.AstCall
        CallNew = _PyV8.AstCallNew
        CallRuntime = _PyV8.AstCallRuntime
        Op = _PyV8.AstOperation
        UnaryOp = _PyV8.AstUnaryOperation
        BinOp = _PyV8.AstBinaryOperation
        CountOp = _PyV8.AstCountOperation
        CompOp = _PyV8.AstCompareOperation
        Conditional = _PyV8.AstConditional
        Assignment = _PyV8.AstAssignment
        Throw = _PyV8.AstThrow    
        Function = _PyV8.AstFunctionLiteral
        FunctionBoilerplate = _PyV8.AstFunctionBoilerplateLiteral
        This = _PyV8.AstThisFunction
    
import datetime
import unittest
import logging
import traceback

class TestContext(unittest.TestCase):
    def testMultiNamespace(self):
        self.assert_(not bool(JSContext.inContext))
        self.assert_(not bool(JSContext.entered))
        
        class Global(object):
            name = "global"
            
        g = Global()
        
        with JSContext(g) as ctxt:
            self.assert_(bool(JSContext.inContext))
            self.assertEquals(g.name, str(JSContext.entered.locals.name))
            self.assertEquals(g.name, str(JSContext.current.locals.name))
            
            class Local(object):
                name = "local"
                
            l = Local()
            
            with JSContext(l):
                self.assert_(bool(JSContext.inContext))
                self.assertEquals(l.name, str(JSContext.entered.locals.name))
                self.assertEquals(l.name, str(JSContext.current.locals.name))
            
            self.assert_(bool(JSContext.inContext))
            self.assertEquals(g.name, str(JSContext.entered.locals.name))
            self.assertEquals(g.name, str(JSContext.current.locals.name))

        self.assert_(not bool(JSContext.entered))
        self.assert_(not bool(JSContext.inContext))
        
    def _testMultiContext(self):
        # Create an environment
        with JSContext() as ctxt0:
            ctxt0.securityToken = "password"
            
            global0 = ctxt0.locals
            global0.custom = 1234
                
            self.assertEquals(1234, int(global0.custom))
            
            # Create an independent environment
            with JSContext() as ctxt1:
                ctxt1.securityToken = ctxt0.securityToken
                 
                global1 = ctxt1.locals
                global1.custom = 1234
                
                self.assertEquals(1234, int(global0.custom))    
                self.assertEquals(1234, int(global1.custom))
                
                # Now create a new context with the old global
                with JSContext(global1) as ctxt2:
                    ctxt2.securityToken = ctxt1.securityToken

                    self.assertRaises(AttributeError, int, global1.custom)
                    self.assertRaises(AttributeError, int, global2.custom)
            
    def _testSecurityChecks(self):
        with JSContext() as env1:
            env1.securityToken = "foo"
            
            # Create a function in env1.
            env1.eval("spy=function(){return spy;}")                

            spy = env1.locals.spy
            
            self.assert_(isinstance(spy, _PyV8.JSFunction))
            
            # Create another function accessing global objects.
            env1.eval("spy2=function(){return 123;}")
            
            spy2 = env1.locals.spy2

            self.assert_(isinstance(spy2, _PyV8.JSFunction))
            
            # Switch to env2 in the same domain and invoke spy on env2.            
            env2 = JSContext()
            
            env2.securityToken = "foo"
            
            with env2:
                result = spy.apply(env2.locals)
                
                self.assert_(isinstance(result, _PyV8.JSFunction))
                
            env2.securityToken = "bar"            
            
            # Call cross_domain_call, it should throw an exception
            with env2:
                self.assertRaises(JSError, spy2.apply, env2.locals)
                
    def _testCrossDomainDelete(self):
        with JSContext() as env1:
            env2 = JSContext()
            
            # Set to the same domain.
            env1.securityToken = "foo"
            env2.securityToken = "foo"
            
            env1.locals.prop = 3
            
            env2.locals.env1 = env1.locals
            
            # Change env2 to a different domain and delete env1.prop.
            #env2.securityToken = "bar"
            
            self.assertEquals(3, int(env1.eval("prop")))
            
            print env1.eval("env1")
            
            with env2:
                self.assertEquals(3, int(env2.eval("this.env1.prop")))
                self.assertEquals("false", str(e.eval("delete env1.prop")))
            
            # Check that env1.prop still exists.
            self.assertEquals(3, int(env1.locals.prop))            

class TestWrapper(unittest.TestCase):    
    def testAutoConverter(self):
        with JSContext() as ctxt:
            ctxt.eval("""
                var_i = 1;
                var_f = 1.0;
                var_s = "test";
                var_b = true;
            """)
            
            vars = ctxt.locals 
            
            var_i = vars.var_i
            
            self.assert_(var_i)
            self.assertEquals(1, int(var_i))
            
            var_f = vars.var_f
            
            self.assert_(var_f)
            self.assertEquals(1.0, float(vars.var_f))
            
            var_s = vars.var_s
            self.assert_(var_s)
            self.assertEquals("test", str(vars.var_s))
            
            var_b = vars.var_b
            self.assert_(var_b)
            self.assert_(bool(var_b))
            
            attrs = dir(ctxt.locals)
                        
            self.assert_(attrs)
            self.assert_("var_i" in attrs)
            self.assert_("var_f" in attrs)
            self.assert_("var_s" in attrs)
            self.assert_("var_b" in attrs)
            
    def testExactConverter(self):
        class MyInteger(int, JSClass):
            pass
        
        class MyString(str, JSClass):
            pass
        
        class MyUnicode(unicode, JSClass):
            pass
        
        class MyDateTime(datetime.time, JSClass):
            pass
        
        class Global(JSClass):
            var_bool = True
            var_int = 1
            var_float = 1.0
            var_str = 'str'
            var_unicode = u'unicode'
            var_datetime = datetime.datetime.now()
            var_date = datetime.date.today()
            var_time = datetime.time()
            
            var_myint = MyInteger()
            var_mystr = MyString('mystr')
            var_myunicode = MyUnicode('myunicode')
            var_mytime = MyDateTime()
            
        with JSContext(Global()) as ctxt:
            typename = ctxt.eval("(function (name) { return this[name].constructor.name; })")
            typeof = ctxt.eval("(function (name) { return typeof(this[name]); })")
            
            self.assertEquals('Boolean', typename('var_bool'))
            self.assertEquals('Number', typename('var_int'))
            self.assertEquals('Number', typename('var_float'))
            self.assertEquals('String', typename('var_str'))
            self.assertEquals('String', typename('var_unicode'))
            self.assertEquals('Date', typename('var_datetime'))
            self.assertEquals('Date', typename('var_date'))
            self.assertEquals('Date', typename('var_time'))            
            
            # TODO: fill the constructor name of python object
            self.assertEquals('', typename('var_myint'))
            self.assertEquals('', typename('var_mystr'))
            self.assertEquals('', typename('var_myunicode'))
            self.assertEquals('', typename('var_mytime'))            
            
            self.assertEquals('object', typeof('var_myint'))
            self.assertEquals('object', typeof('var_mystr'))
            self.assertEquals('object', typeof('var_myunicode'))
            self.assertEquals('object', typeof('var_mytime'))  
            
    def testFunction(self):
        with JSContext() as ctxt:
            func = ctxt.eval("""
                (function ()
                {
                    function a()
                    {
                        return "abc";    
                    }
                
                    return a();    
                })
                """)
            
            self.assertEquals("abc", str(func()))
            self.assert_(func != None)
            self.assertFalse(func == None)
            
    def testCall(self):
        class Hello(object):
            def __call__(self, name):
                return "hello " + name
            
        class Global(JSClass):
            hello = Hello()
            
        with JSContext(Global()) as ctxt:
            self.assertEquals("hello flier", ctxt.eval("hello('flier')"))
        
    def testJSError(self):
        with JSContext() as ctxt:
            try:
                ctxt.eval('throw "test"')
                self.fail()
            except:
                self.assert_(JSError, sys.exc_type)
                
    def testErrorInfo(self):
        with JSContext() as ctxt:
            with JSEngine() as engine:
                try:
                    engine.compile("""
                        function hello()
                        {
                            throw Error("hello world");
                        }
                        
                        hello();""", "test", 10, 10).run()
                    self.fail()
                except JSError, e:
                    self.assert_(str(e).startswith('JSError: Error: hello world ( test @ 14 : 34 )  ->'))
                    self.assertEqual("Error", e.name)
                    self.assertEqual("hello world", e.message)
                    self.assertEqual("test", e.scriptName)
                    self.assertEqual(14, e.lineNum)
                    self.assertEqual(102, e.startPos)
                    self.assertEqual(103, e.endPos)
                    self.assertEqual(34, e.startCol)
                    self.assertEqual(35, e.endCol)
                    self.assertEqual('throw Error("hello world");', e.sourceLine.strip())
                    self.assertEqual('Error: hello world\n' +
                                     '    at Error (unknown source)\n' +
                                     '    at hello (test:14:35)\n' +
                                     '    at test:17:25', e.stackTrace)
        
    def testPythonException(self):
        class Global(JSClass):
            def raiseException(self):
                raise RuntimeError("Hello")
                
        with JSContext(Global()) as ctxt:
            r = ctxt.eval("""
                msg ="";
                try
                {
                    this.raiseException()
                }
                catch(e)
                {
                    msg += "catch " + e + ";";
                }
                finally
                {
                    msg += "finally";
                }""")
            self.assertEqual("catch Error: Hello;finally", str(ctxt.locals.msg))
        
    def testExceptionMapping(self):
        class Global(JSClass):
            def raiseIndexError(self):
                return [1, 2, 3][5]
            
            def raiseAttributeError(self):
                None.hello()
            
            def raiseSyntaxError(self):
                eval("???")
            
            def raiseTypeError(self):
                int(sys)
                
            def raiseNotImplementedError(self):
                raise NotImplementedError()
        
        with JSContext(Global()) as ctxt:
            ctxt.eval("try { this.raiseIndexError(); } catch (e) { msg = e; }")
            
            self.assertEqual("RangeError", str(ctxt.locals.msg))
            
            ctxt.eval("try { this.raiseAttributeError(); } catch (e) { msg = e; }")
            
            self.assertEqual("ReferenceError", str(ctxt.locals.msg))
            
            ctxt.eval("try { this.raiseSyntaxError(); } catch (e) { msg = e; }")
            
            self.assertEqual("SyntaxError", str(ctxt.locals.msg))
            
            ctxt.eval("try { this.raiseTypeError(); } catch (e) { msg = e; }")
            
            self.assertEqual("TypeError", str(ctxt.locals.msg))
            
            ctxt.eval("try { this.raiseNotImplementedError(); } catch (e) { msg = e; }")
            
            self.assertEqual("Error", str(ctxt.locals.msg))
    def testArray(self):
        with JSContext() as ctxt:
            array = ctxt.eval("""
                var array = new Array();
                
                for (i=0; i<10; i++)
                {
                    array[i] = 10-i;
                }
                
                array;
                """)
            
            self.assert_(isinstance(array, _PyV8.JSArray))
            self.assertEqual(10, len(array))
            
            self.assert_(5 in array)
            self.assertFalse(15 in array)
            
            l = list(array)
            
            self.assertEqual(10, len(l))            
            
            for i in xrange(10):
                self.assertEqual(10-i, array[i])
                self.assertEqual(10-i, l[i])
            
            array[5] = 0
            
            self.assertEqual(0, array[5])
            
            del array[5]
            
            self.assertRaises(IndexError, lambda: array[5])
            
            ctxt.locals.array1 = JSArray(5)
            ctxt.locals.array2 = JSArray([1, 2, 3, 4, 5])
            
            for i in xrange(len(ctxt.locals.array2)):
                ctxt.locals.array1[i] = ctxt.locals.array2[i] * 10
                            
            ctxt.eval("""
                var sum = 0;
                
                for (i=0; i<array1.length; i++)
                    sum += array1[i]
                
                for (i=0; i<array2.length; i++)
                    sum += array2[i]                
                """)
            
            self.assertEqual(165, ctxt.locals.sum)
            
            ctxt.locals.array3 = [1, 2, 3, 4, 5]
            self.assert_(ctxt.eval('array3[1] === 2'))
            self.assert_(ctxt.eval('array3[9] === undefined'))
            
    def testMultiDimArray(self):
        with JSContext() as ctxt:
            ret = ctxt.eval(""" 
                ({ 
                    'test': function(){ 
                        return  [ 
                            [ 1, 'abla' ], 
                            [ 2, 'ajkss' ], 
                        ] 
                    } 
                }) 
                """).test()
            
            self.assertEquals([[1, 'abla'], [2, 'ajkss']], convert(ret))

    def testLazyConstructor(self):
        class Globals(JSClass):
            def __init__(self):
                self.array=JSArray([1,2,3])
        
        with JSContext(Globals()) as ctxt:
            self.assertEqual(2, ctxt.eval("""array[1]"""))
            
    def testForEach(self):
        class NamedClass(JSClass):
            foo = 1
            
            def __init__(self):
                self.bar = 2
                
        with JSContext() as ctxt:
            func = ctxt.eval("""(function (k) {
                var result = [];    
                for (var prop in k) {
                  result.push(prop);
                }
                return result;
            })""")
            
            self.assertEquals(["bar"], list(func(NamedClass())))
            self.assertEquals(["0", "1", "2"], list(func([1, 2, 3])))
            
    def testDict(self):
        import UserDict
        
        with JSContext() as ctxt:
            obj = ctxt.eval("var r = { 'a' : 1, 'b' : 2 }; r")
            
            self.assertEqual(1, obj.a)
            self.assertEqual(2, obj.b)
            
            self.assertEqual({ 'a' : 1, 'b' : 2 }, dict(obj))            
        
            self.assertEqual({ 'a': 1,
                               'b': [1, 2, 3],
                               'c': { 'str' : 'goofy',
                                      'float' : 1.234,
                                      'obj' : { 'name': 'john doe' }},                                      
                               'd': True,
                               'e': None },
                             convert(ctxt.eval("""var x =
                             { a: 1,
                               b: [1, 2, 3],
                               c: { str: 'goofy',
                                    float: 1.234,
                                    obj: { name: 'john doe' }},
                               d: true,
                               e: null }; x""")))
        
    def testDate(self):
        with JSContext() as ctxt:            
            now1 = ctxt.eval("new Date();")
            
            self.assert_(now1)
            
            now2 = datetime.datetime.utcnow()
            
            delta = now2 - now1 if now2 > now1 else now1 - now2
            
            self.assert_(delta < datetime.timedelta(seconds=1))
            
            func = ctxt.eval("(function (d) { return d.toString(); })")
            
            now = datetime.datetime.now() 
            
            self.assert_(str(func(now)).startswith(now.strftime("%a %b %d %Y %H:%M:%S")))
    
    def testUnicode(self):
        with JSContext() as ctxt:
            self.assertEquals(u"人", unicode(ctxt.eval("\"人\""), "utf-8"))
            self.assertEquals(u"é", unicode(ctxt.eval("\"é\""), "utf-8"))
            
            func = ctxt.eval("(function (msg) { return msg.length; })")
            
            self.assertEquals(2, func(u"测试"))
            
    def testClassicStyleObject(self):
        class FileSystemWarpper:
            @property
            def cwd(self):
                return os.getcwd() 
            
        class Global:
            @property
            def fs(self):
                return FileSystemWarpper()
                
        with JSContext(Global()) as ctxt:    
            self.assertEquals(os.getcwd(), ctxt.eval("fs.cwd"))
            
    def testRefCount(self):
        count = sys.getrefcount(None)
        
        class Global(JSClass):
            pass

        with JSContext(Global()) as ctxt:        
            ctxt.eval("""
                var none = null;
            """)
        
            self.assertEquals(count+1, sys.getrefcount(None))

            ctxt.eval("""
                var none = null;
            """)
        
            self.assertEquals(count+1, sys.getrefcount(None))
            
    def testProperty(self):
        class Global(JSClass):
            def __init__(self, name):
                self._name = name
            def getname(self):
                return self._name
            def setname(self, name):
                self._name = name
            def delname(self):
                self._name = 'deleted'
            
            name = property(getname, setname, delname)            
            
        with JSContext(Global('world')) as ctxt:
            self.assertEquals('world', ctxt.eval("name"))
            self.assertEquals('flier', ctxt.eval("name = 'flier';"))
            self.assertEquals('flier', ctxt.eval("name"))
            self.assert_(ctxt.eval("delete name")) # FIXME
            #self.assertEquals('deleted', ctxt.eval("name"))
            ctxt.eval("__defineGetter__('name', function() { return 'fixed'; });")
            self.assertEquals('fixed', ctxt.eval("name"))
            
class TestMutithread(unittest.TestCase):
    def testLocker(self):        
        self.assertFalse(JSLocker.actived)
        self.assertFalse(JSLocker.locked)
        
        with JSLocker() as outter_locker:        
            self.assertTrue(JSLocker.actived)
            self.assertTrue(JSLocker.locked)
            
            self.assertTrue(outter_locker)
            
            with JSLocker() as inner_locker:
                self.assertTrue(JSLocker.locked)
                
                self.assertTrue(outter_locker)
                self.assertTrue(inner_locker)
                
                with JSUnlocker() as unlocker:
                    self.assertFalse(JSLocker.locked)
                
                    self.assertTrue(outter_locker)
                    self.assertTrue(inner_locker)
                    
                self.assertTrue(JSLocker.locked)
                    
        self.assertTrue(JSLocker.actived)
        self.assertFalse(JSLocker.locked)
        
        locker = JSLocker()
        
        with JSContext():
            self.assertRaises(RuntimeError, locker.__enter__)
            self.assertRaises(RuntimeError, locker.__exit__, None, None, None)
            
        del locker
        
    def testMultiPythonThread(self):
        import time, threading
        
        class Global:
            count = 0
            started = threading.Event()
            finished = threading.Semaphore(0)
            
            def sleep(self, ms):
                time.sleep(ms / 1000.0)
                
                self.count += 1
            
        g = Global()
        
        def run():
            with JSContext(g) as ctxt:
                ctxt.eval("""
                    started.wait();                    
                    
                    for (i=0; i<10; i++)
                    {                        
                        sleep(100);
                    }
                    
                    finished.release();
                """)
        
        threading.Thread(target=run).start()        
        
        now = time.time()
        
        self.assertEqual(0, g.count)
        
        g.started.set()
        g.finished.acquire()
        
        self.assertEqual(10, g.count)
        
        self.assert_((time.time() - now) >= 1)        
    
    def testMultiJavascriptThread(self):
        import time, thread, threading
        
        class Global:
            result = []
            
            def add(self, value):
                with JSUnlocker() as unlocker:
                    time.sleep(0.1)
                    
                    self.result.append(value)
                    
        g = Global()
        
        def run():
            with JSContext(g) as ctxt:                
                ctxt.eval("""
                    for (i=0; i<10; i++)
                        add(i);
                """)
                
        threads = [threading.Thread(target=run), threading.Thread(target=run)]
                
        with JSLocker():
            for t in threads: t.start()
            
        for t in threads: t.join()
        
        self.assertEqual(20, len(g.result))
        
    def testPreemptionJavascriptThreads(self):
        import time, thread, threading
        
        class Global:
            result = []
            
            def add(self, value):
                # we use preemption scheduler to switch between threads
                # so, just comment the JSUnlocker
                #
                # with JSUnlocker() as unlocker:
                time.sleep(0.1)
                
                self.result.append(value)
                    
        g = Global()
        
        def run():            
            with JSContext(g) as ctxt:                
                ctxt.eval("""
                    for (i=0; i<10; i++)
                        add(i);
                """)
                
        threads = [threading.Thread(target=run), threading.Thread(target=run)]
        
        with JSLocker() as locker:
            JSLocker.startPreemption(100)
            
            for t in threads: t.start()
            
        for t in threads: t.join()
        
        self.assertEqual(20, len(g.result))
        
class TestEngine(unittest.TestCase):
    def testClassProperties(self):
        with JSContext() as ctxt:
            self.assert_(str(JSEngine.version).startswith("2."))
            self.assertFalse(JSEngine.dead)
        
    def testCompile(self):
        with JSContext() as ctxt:
            with JSEngine() as engine:
                s = engine.compile("1+2")
                
                self.assert_(isinstance(s, _PyV8.JSScript))
                
                self.assertEquals("1+2", s.source)
                self.assertEquals(3, int(s.run()))
                
    def testPrecompile(self):
        with JSContext() as ctxt:
            with JSEngine() as engine:
                data = engine.precompile("1+2")
                
                self.assert_(data)
                self.assertEquals(16, len(data))
                
                s = engine.compile("1+2", precompiled=data)
                
                self.assert_(isinstance(s, _PyV8.JSScript))
                
                self.assertEquals("1+2", s.source)
                self.assertEquals(3, int(s.run()))
                
    def testExtension(self):
        extSrc = """function hello(name) { return "hello " + name + " from javascript"; }"""        
        extJs = JSExtension("hello/javascript", extSrc)
        
        self.assert_(extJs)
        self.assertEqual("hello/javascript", extJs.name)
        self.assertEqual(extSrc, extJs.source)
        self.assertFalse(extJs.autoEnable)
        self.assertTrue(extJs.registered)
        
        TestEngine.extJs = extJs
                
        with JSContext(extensions=['hello/javascript']) as ctxt:
            self.assertEqual("hello flier from javascript", ctxt.eval("hello('flier')"))

        # test the auto enable property
        
        with JSContext() as ctxt:
            self.assertRaises(JSError, ctxt.eval, "hello('flier')")
            
        extJs.autoEnable = True
        self.assertTrue(extJs.autoEnable)
        
        with JSContext() as ctxt:
            self.assertEqual("hello flier from javascript", ctxt.eval("hello('flier')"))
            
        extJs.autoEnable = False
        self.assertFalse(extJs.autoEnable)

        with JSContext() as ctxt:
            self.assertRaises(JSError, ctxt.eval, "hello('flier')")

    def testNativeExtension(self):            
        extSrc = "native function hello();"
        extPy = JSExtension("hello/python", extSrc, lambda func: lambda name: "hello " + name + " from python", register=False)
        self.assert_(extPy)
        self.assertEqual("hello/python", extPy.name)
        self.assertEqual(extSrc, extPy.source)
        self.assertFalse(extPy.autoEnable)
        self.assertFalse(extPy.registered)
        extPy.register()
        self.assertTrue(extPy.registered)
        
        TestEngine.extPy = extPy
        
        with JSContext(extensions=['hello/python']) as ctxt:
            self.assertEqual("hello flier from python", ctxt.eval("hello('flier')"))
        
    def _testSerialize(self):
        data = None
        
        self.assertFalse(JSContext.entered)
        
        with JSContext() as ctxt:
            self.assert_(JSContext.entered)
            
            #ctxt.eval("function hello(name) { return 'hello ' + name; }")
            
            data = JSEngine.serialize()
        
        self.assert_(data)
        self.assert_(len(data) > 0)
            
        self.assertFalse(JSContext.entered)
            
        #JSEngine.deserialize()
        
        self.assert_(JSContext.entered)
        
        self.assertEquals('hello flier', JSContext.current.eval("hello('flier');"))
            
    def testEval(self):
        with JSContext() as ctxt:
            self.assertEquals(3, int(ctxt.eval("1+2")))        
            
    def testGlobal(self):
        class Global(JSClass):
            version = "1.0"            
            
        with JSContext(Global()) as ctxt:            
            vars = ctxt.locals
            
            # getter
            self.assertEquals(Global.version, str(vars.version))            
            self.assertEquals(Global.version, str(ctxt.eval("version")))
                        
            self.assertRaises(JSError, JSContext.eval, ctxt, "nonexists")
            
            # setter
            self.assertEquals(2.0, float(ctxt.eval("version = 2.0")))
            
            self.assertEquals(2.0, float(vars.version))       
            
    def testThis(self):
        class Global(JSClass): 
            version = 1.0            
                
        with JSContext(Global()) as ctxt:
            self.assertEquals("[object Global]", str(ctxt.eval("this")))
            
            self.assertEquals(1.0, float(ctxt.eval("this.version")))            
        
    def testObjectBuildInMethods(self):
        class Global(JSClass):
            version = 1.0
            
        with JSContext(Global()) as ctxt:            
            self.assertEquals("[object Global]", str(ctxt.eval("this.toString()")))
            self.assertEquals("[object Global]", str(ctxt.eval("this.toLocaleString()")))            
            self.assertEquals(Global.version, float(ctxt.eval("this.valueOf()").version))
            
            self.assert_(bool(ctxt.eval("this.hasOwnProperty(\"version\")")))
            
            self.assertFalse(ctxt.eval("this.hasOwnProperty(\"nonexistent\")"))
            
    def testPythonWrapper(self):
        class Global(JSClass):
            s = [1, 2, 3]
            d = {'a': {'b': 'c'}, 'd': ['e', 'f']}
            
        g = Global()
        
        with JSContext(g) as ctxt:            
            ctxt.eval("""
                s[2] = s[1] + 2;
                s[0] = s[1];
                delete s[1];
            """)
            self.assertEquals([2, 4], g.s)
            self.assertEquals('c', ctxt.eval("d.a.b"))
            self.assertEquals(['e', 'f'], ctxt.eval("d.d"))
            ctxt.eval("""
                d.a.q = 4
                delete d.d
            """)
            self.assertEquals(4, g.d['a']['q'])
            self.assertEquals(None, ctxt.eval("d.d"))
            
class TestDebug(unittest.TestCase):
    def setUp(self):
        self.engine = JSEngine()
        
    def tearDown(self):
        del self.engine
        
    events = []    
        
    def processDebugEvent(self, event):
        try:
            logging.debug("receive debug event: %s", repr(event))
            
            self.events.append(repr(event))
        except:
            logging.error("fail to process debug event")            
            logging.debug(traceback.extract_stack())
        
    def testEventDispatch(self):        
        global debugger
        
        self.assert_(not debugger.enabled)
        
        debugger.onBreak = lambda evt: self.processDebugEvent(evt)
        debugger.onException = lambda evt: self.processDebugEvent(evt)
        debugger.onNewFunction = lambda evt: self.processDebugEvent(evt)
        debugger.onBeforeCompile = lambda evt: self.processDebugEvent(evt)
        debugger.onAfterCompile = lambda evt: self.processDebugEvent(evt)
        
        with JSContext() as ctxt:            
            debugger.enabled = True
            
            self.assertEquals(3, int(ctxt.eval("function test() { text = \"1+2\"; return eval(text) } test()")))
            
            debugger.enabled = False            
            
            self.assertRaises(JSError, JSContext.eval, ctxt, "throw 1")
            
            self.assert_(not debugger.enabled)                
            
        self.assertEquals(4, len(self.events))
        
class TestProfile(unittest.TestCase):
    def testStart(self):
        self.assertFalse(profiler.started)
        
        profiler.start()
        
        self.assert_(profiler.started)
        
        profiler.stop()
        
        self.assertFalse(profiler.started)
        
    def testResume(self):
        self.assert_(profiler.paused)
        
        self.assertEquals(profiler.Modules.cpu, profiler.modules)
        
        profiler.resume()
        
        profiler.resume(profiler.Modules.heap)
        
        # TODO enable profiler with resume
        #self.assertFalse(profiler.paused)
        
if __name__ == '__main__':
    if "-v" in sys.argv:
        level = logging.DEBUG
    else:
        level = logging.WARN
    
    logging.basicConfig(level=level, format='%(asctime)s %(levelname)s %(message)s')
    
    logging.info("testing PyV8 module with V8 v%s", JSEngine.version)

    unittest.main()

########NEW FILE########
