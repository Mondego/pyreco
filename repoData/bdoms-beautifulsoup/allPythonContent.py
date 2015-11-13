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
__FILENAME__ = BeautifulSoupTests
# -*- coding: utf-8 -*-
"""Unit tests for Beautiful Soup.

These tests make sure the Beautiful Soup works as it should. If you
find a bug in Beautiful Soup, the best way to express it is as a test
case like this that fails."""

import unittest
from BeautifulSoup import *

class SoupTest(unittest.TestCase):

    def assertSoupEquals(self, toParse, rep=None, c=BeautifulSoup):
        """Parse the given text and make sure its string rep is the other
        given text."""
        if rep == None:
            rep = toParse
        self.assertEqual(str(c(toParse)), rep)


class FollowThatTag(SoupTest):

    "Tests the various ways of fetching tags from a soup."

    def setUp(self):
        ml = """
        <a id="x">1</a>
        <A id="a">2</a>
        <b id="b">3</a>
        <b href="foo" id="x">4</a>
        <ac width=100>4</ac>"""
        self.soup = BeautifulStoneSoup(ml)

    def testFindAllByName(self):
        matching = self.soup('a')
        self.assertEqual(len(matching), 2)
        self.assertEqual(matching[0].name, 'a')
        self.assertEqual(matching, self.soup.findAll('a'))
        self.assertEqual(matching, self.soup.findAll(SoupStrainer('a')))

    def testFindAllByAttribute(self):
        matching = self.soup.findAll(id='x')
        self.assertEqual(len(matching), 2)
        self.assertEqual(matching[0].name, 'a')
        self.assertEqual(matching[1].name, 'b')

        matching2 = self.soup.findAll(attrs={'id' : 'x'})
        self.assertEqual(matching, matching2)

        strainer = SoupStrainer(attrs={'id' : 'x'})
        self.assertEqual(matching, self.soup.findAll(strainer))

        self.assertEqual(len(self.soup.findAll(id=None)), 1)

        self.assertEqual(len(self.soup.findAll(width=100)), 1)
        self.assertEqual(len(self.soup.findAll(junk=None)), 5)
        self.assertEqual(len(self.soup.findAll(junk=[1, None])), 5)

        self.assertEqual(len(self.soup.findAll(junk=re.compile('.*'))), 0)
        self.assertEqual(len(self.soup.findAll(junk=True)), 0)

        self.assertEqual(len(self.soup.findAll(junk=True)), 0)
        self.assertEqual(len(self.soup.findAll(href=True)), 1)

    def testFindallByClass(self):
        soup = BeautifulSoup('<b class="foo">Foo</b><a class="1 23 4">Bar</a>')
        self.assertEqual(soup.find(attrs='foo').string, "Foo")
        self.assertEqual(soup.find('a', '1').string, "Bar")
        self.assertEqual(soup.find('a', '23').string, "Bar")
        self.assertEqual(soup.find('a', '4').string, "Bar")

        self.assertEqual(soup.find('a', '2'), None)

    def testFindAllByList(self):
        matching = self.soup(['a', 'ac'])
        self.assertEqual(len(matching), 3)

    def testFindAllByHash(self):
        matching = self.soup({'a' : True, 'b' : True})
        self.assertEqual(len(matching), 4)

    def testFindAllText(self):
        soup = BeautifulSoup("<html>\xbb</html>")
        self.assertEqual(soup.findAll(text=re.compile('.*')),
                         [u'\xbb'])

    def testFindAllByRE(self):
        import re
        r = re.compile('a.*')
        self.assertEqual(len(self.soup(r)), 3)

    def testFindAllByMethod(self):
        def matchTagWhereIDMatchesName(tag):
            return tag.name == tag.get('id')

        matching = self.soup.findAll(matchTagWhereIDMatchesName)
        self.assertEqual(len(matching), 2)
        self.assertEqual(matching[0].name, 'a')

    def testFindByIndex(self):
        """For when you have the tag and you want to know where it is."""
        tag = self.soup.find('a', id="a")
        self.assertEqual(self.soup.index(tag), 3)

        # It works for NavigableStrings as well.
        s = tag.string
        self.assertEqual(tag.index(s), 0)

        # If the tag isn't present, a ValueError is raised.
        soup2 = BeautifulSoup("<b></b>")
        tag2 = soup2.find('b')
        self.assertRaises(ValueError, self.soup.index, tag2)

    def testConflictingFindArguments(self):
        """The 'text' argument takes precedence."""
        soup = BeautifulSoup('Foo<b>Bar</b>Baz')
        self.assertEqual(soup.find('b', text='Baz'), 'Baz')
        self.assertEqual(soup.findAll('b', text='Baz'), ['Baz'])

        self.assertEqual(soup.find(True, text='Baz'), 'Baz')
        self.assertEqual(soup.findAll(True, text='Baz'), ['Baz'])

    def testParents(self):
        soup = BeautifulSoup('<ul id="foo"></ul><ul id="foo"><ul><ul id="foo" a="b"><b>Blah')
        b = soup.b
        self.assertEquals(len(b.findParents('ul', {'id' : 'foo'})), 2)
        self.assertEquals(b.findParent('ul')['a'], 'b')

    PROXIMITY_TEST = BeautifulSoup('<b id="1"><b id="2"><b id="3"><b id="4">')

    def testNext(self):
        soup = self.PROXIMITY_TEST
        b = soup.find('b', {'id' : 2})
        self.assertEquals(b.findNext('b')['id'], '3')
        self.assertEquals(b.findNext('b')['id'], '3')
        self.assertEquals(len(b.findAllNext('b')), 2)
        self.assertEquals(len(b.findAllNext('b', {'id' : 4})), 1)

    def testPrevious(self):
        soup = self.PROXIMITY_TEST
        b = soup.find('b', {'id' : 3})
        self.assertEquals(b.findPrevious('b')['id'], '2')
        self.assertEquals(b.findPrevious('b')['id'], '2')
        self.assertEquals(len(b.findAllPrevious('b')), 2)
        self.assertEquals(len(b.findAllPrevious('b', {'id' : 2})), 1)


    SIBLING_TEST = BeautifulSoup('<blockquote id="1"><blockquote id="1.1"></blockquote></blockquote><blockquote id="2"><blockquote id="2.1"></blockquote></blockquote><blockquote id="3"><blockquote id="3.1"></blockquote></blockquote><blockquote id="4">')

    def testNextSibling(self):
        soup = self.SIBLING_TEST
        tag = 'blockquote'
        b = soup.find(tag, {'id' : 2})
        self.assertEquals(b.findNext(tag)['id'], '2.1')
        self.assertEquals(b.findNextSibling(tag)['id'], '3')
        self.assertEquals(b.findNextSibling(tag)['id'], '3')
        self.assertEquals(len(b.findNextSiblings(tag)), 2)
        self.assertEquals(len(b.findNextSiblings(tag, {'id' : 4})), 1)

    def testPreviousSibling(self):
        soup = self.SIBLING_TEST
        tag = 'blockquote'
        b = soup.find(tag, {'id' : 3})
        self.assertEquals(b.findPrevious(tag)['id'], '2.1')
        self.assertEquals(b.findPreviousSibling(tag)['id'], '2')
        self.assertEquals(b.findPreviousSibling(tag)['id'], '2')
        self.assertEquals(len(b.findPreviousSiblings(tag)), 2)
        self.assertEquals(len(b.findPreviousSiblings(tag, id=1)), 1)

    def testTextNavigation(self):
        soup = BeautifulSoup('Foo<b>Bar</b><i id="1"><b>Baz<br />Blee<hr id="1"/></b></i>Blargh')
        baz = soup.find(text='Baz')
        self.assertEquals(baz.findParent("i")['id'], '1')
        self.assertEquals(baz.findNext(text='Blee'), 'Blee')
        self.assertEquals(baz.findNextSibling(text='Blee'), 'Blee')
        self.assertEquals(baz.findNextSibling(text='Blargh'), None)
        self.assertEquals(baz.findNextSibling('hr')['id'], '1')

class SiblingRivalry(SoupTest):
    "Tests the nextSibling and previousSibling navigation."

    def testSiblings(self):
        soup = BeautifulSoup("<ul><li>1<p>A</p>B<li>2<li>3</ul>")
        secondLI = soup.find('li').nextSibling
        self.assert_(secondLI.name == 'li' and secondLI.string == '2')
        self.assertEquals(soup.find(text='1').nextSibling.name, 'p')
        self.assertEquals(soup.find('p').nextSibling, 'B')
        self.assertEquals(soup.find('p').nextSibling.previousSibling.nextSibling, 'B')

class TagsAreObjectsToo(SoupTest):
    "Tests the various built-in functions of Tag objects."

    def testLen(self):
        soup = BeautifulSoup("<top>1<b>2</b>3</top>")
        self.assertEquals(len(soup.top), 3)

class StringEmUp(SoupTest):
    "Tests the use of 'string' as an alias for a tag's only content."

    def testString(self):
        s = BeautifulSoup("<b>foo</b>")
        self.assertEquals(s.b.string, 'foo')

    def testLackOfString(self):
        s = BeautifulSoup("<b>f<i>e</i>o</b>")
        self.assert_(not s.b.string)

    def testStringAssign(self):
        s = BeautifulSoup("<b></b>")
        b = s.b
        b.string = "foo"
        string = b.string
        self.assertEquals(string, "foo")
        self.assert_(isinstance(string, NavigableString))

class AllText(SoupTest):
    "Tests the use of 'text' to get all of string content from the tag."

    def testText(self):
        soup = BeautifulSoup("<ul><li>spam</li><li>eggs</li><li>cheese</li>")
        self.assertEquals(soup.ul.text, "spameggscheese")
        self.assertEquals(soup.ul.getText('/'), "spam/eggs/cheese")

class ThatsMyLimit(SoupTest):
    "Tests the limit argument."

    def testBasicLimits(self):
        s = BeautifulSoup('<br id="1" /><br id="1" /><br id="1" /><br id="1" />')
        self.assertEquals(len(s.findAll('br')), 4)
        self.assertEquals(len(s.findAll('br', limit=2)), 2)
        self.assertEquals(len(s('br', limit=2)), 2)

class OnlyTheLonely(SoupTest):
    "Tests the parseOnly argument to the constructor."
    def setUp(self):
        x = []
        for i in range(1,6):
            x.append('<a id="%s">' % i)
            for j in range(100,103):
                x.append('<b id="%s.%s">Content %s.%s</b>' % (i,j, i,j))
            x.append('</a>')
        self.x = ''.join(x)

    def testOnly(self):
        strainer = SoupStrainer("b")
        soup = BeautifulSoup(self.x, parseOnlyThese=strainer)
        self.assertEquals(len(soup), 15)

        strainer = SoupStrainer(id=re.compile("100.*"))
        soup = BeautifulSoup(self.x, parseOnlyThese=strainer)
        self.assertEquals(len(soup), 5)

        strainer = SoupStrainer(text=re.compile("10[01].*"))
        soup = BeautifulSoup(self.x, parseOnlyThese=strainer)
        self.assertEquals(len(soup), 10)

        strainer = SoupStrainer(text=lambda(x):x[8]=='3')
        soup = BeautifulSoup(self.x, parseOnlyThese=strainer)
        self.assertEquals(len(soup), 3)

class PickleMeThis(SoupTest):
    "Testing features like pickle and deepcopy."

    def setUp(self):
        self.page = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN"
"http://www.w3.org/TR/REC-html40/transitional.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<title>Beautiful Soup: We called him Tortoise because he taught us.</title>
<link rev="made" href="mailto:leonardr@segfault.org">
<meta name="Description" content="Beautiful Soup: an HTML parser optimized for screen-scraping.">
<meta name="generator" content="Markov Approximation 1.4 (module: leonardr)">
<meta name="author" content="Leonard Richardson">
</head>
<body>
<a href="foo">foo</a>
<a href="foo"><b>bar</b></a>
</body>
</html>"""

        self.soup = BeautifulSoup(self.page)

    def testPickle(self):
        import pickle
        dumped = pickle.dumps(self.soup, 2)
        loaded = pickle.loads(dumped)
        self.assertEqual(loaded.__class__, BeautifulSoup)
        self.assertEqual(str(loaded), str(self.soup))

    def testDeepcopy(self):
        from copy import deepcopy
        copied = deepcopy(self.soup)
        self.assertEqual(str(copied), str(self.soup))

    def testUnicodePickle(self):
        import cPickle as pickle
        html = "<b>" + chr(0xc3) + "</b>"
        soup = BeautifulSoup(html)
        dumped = pickle.dumps(soup, pickle.HIGHEST_PROTOCOL)
        loaded = pickle.loads(dumped)
        self.assertEqual(str(loaded), str(soup))


class WriteOnlyCode(SoupTest):
    "Testing the modification of the tree."

    def testModifyAttributes(self):
        soup = BeautifulSoup('<a id="1"></a>')
        soup.a['id'] = 2
        self.assertEqual(soup.renderContents(), '<a id="2"></a>')
        del(soup.a['id'])
        self.assertEqual(soup.renderContents(), '<a></a>')
        soup.a['id2'] = 'foo'
        self.assertEqual(soup.renderContents(), '<a id2="foo"></a>')

    def testNewTagCreation(self):
        "Makes sure tags don't step on each others' toes."
        soup = BeautifulSoup()
        a = Tag(soup, 'a')
        ol = Tag(soup, 'ol')
        a['href'] = 'http://foo.com/'
        self.assertRaises(KeyError, lambda : ol['href'])

    def testNewTagWithAttributes(self):
        """Makes sure new tags can be created complete with attributes."""
        soup = BeautifulSoup()
        a = Tag(soup, 'a', [('href', 'foo')])
        b = Tag(soup, 'b', {'class':'bar'})
        soup.insert(0,a)
        soup.insert(1,b)
        self.assertEqual(soup.a['href'], 'foo')
        self.assertEqual(soup.b['class'], 'bar')

    def testTagReplacement(self):
        # Make sure you can replace an element with itself.
        text = "<a><b></b><c>Foo<d></d></c></a><a><e></e></a>"
        soup = BeautifulSoup(text)
        c = soup.c
        soup.c.replaceWith(c)
        self.assertEquals(str(soup), text)

        # A very simple case
        soup = BeautifulSoup("<b>Argh!</b>")
        soup.find(text="Argh!").replaceWith("Hooray!")
        newText = soup.find(text="Hooray!")
        b = soup.b
        self.assertEqual(newText.previous, b)
        self.assertEqual(newText.parent, b)
        self.assertEqual(newText.previous.next, newText)
        self.assertEqual(newText.next, None)

        # A more complex case
        soup = BeautifulSoup("<a><b>Argh!</b><c></c><d></d></a>")
        soup.b.insert(1, "Hooray!")
        newText = soup.find(text="Hooray!")
        self.assertEqual(newText.previous, "Argh!")
        self.assertEqual(newText.previous.next, newText)

        self.assertEqual(newText.previousSibling, "Argh!")
        self.assertEqual(newText.previousSibling.nextSibling, newText)

        self.assertEqual(newText.nextSibling, None)
        self.assertEqual(newText.next, soup.c)

        text = "<html>There's <b>no</b> business like <b>show</b> business</html>"
        soup = BeautifulSoup(text)
        no, show = soup.findAll('b')
        show.replaceWith(no)
        self.assertEquals(str(soup), "<html>There's  business like <b>no</b> business</html>")

        # Even more complex
        soup = BeautifulSoup("<a><b>Find</b><c>lady!</c><d></d></a>")
        tag = Tag(soup, 'magictag')
        tag.insert(0, "the")
        soup.a.insert(1, tag)

        b = soup.b
        c = soup.c
        theText = tag.find(text=True)
        findText = b.find(text="Find")

        self.assertEqual(findText.next, tag)
        self.assertEqual(tag.previous, findText)
        self.assertEqual(b.nextSibling, tag)
        self.assertEqual(tag.previousSibling, b)
        self.assertEqual(tag.nextSibling, c)
        self.assertEqual(c.previousSibling, tag)

        self.assertEqual(theText.next, c)
        self.assertEqual(c.previous, theText)

        # Aand... incredibly complex.
        soup = BeautifulSoup("""<a>We<b>reserve<c>the</c><d>right</d></b></a><e>to<f>refuse</f><g>service</g></e>""")
        f = soup.f
        a = soup.a
        c = soup.c
        e = soup.e
        weText = a.find(text="We")
        soup.b.replaceWith(soup.f)
        self.assertEqual(str(soup), "<a>We<f>refuse</f></a><e>to<g>service</g></e>")

        self.assertEqual(f.previous, weText)
        self.assertEqual(weText.next, f)
        self.assertEqual(f.previousSibling, weText)
        self.assertEqual(f.nextSibling, None)
        self.assertEqual(weText.nextSibling, f)

    def testReplaceWithChildren(self):
        soup = BeautifulStoneSoup(
            "<top><replace><child1/><child2/></replace></top>",
            selfClosingTags=["child1", "child2"])
        soup.replaceTag.replaceWithChildren()
        self.assertEqual(soup.top.contents[0].name, "child1")
        self.assertEqual(soup.top.contents[1].name, "child2")

    def testAppend(self):
       doc = "<p>Don't leave me <b>here</b>.</p> <p>Don't leave me.</p>"
       soup = BeautifulSoup(doc)
       second_para = soup('p')[1]
       bold = soup.find('b')
       soup('p')[1].append(soup.find('b'))
       self.assertEqual(bold.parent, second_para)
       self.assertEqual(str(soup),
                        "<p>Don't leave me .</p> "
                        "<p>Don't leave me.<b>here</b></p>")

    def testTagExtraction(self):
        # A very simple case
        text = '<html><div id="nav">Nav crap</div>Real content here.</html>'
        soup = BeautifulSoup(text)
        extracted = soup.find("div", id="nav").extract()
        self.assertEqual(str(soup), "<html>Real content here.</html>")
        self.assertEqual(str(extracted), '<div id="nav">Nav crap</div>')

        # A simple case, a more complex test.
        text = "<doc><a>1<b>2</b></a><a>i<b>ii</b></a><a>A<b>B</b></a></doc>"
        soup = BeautifulStoneSoup(text)
        doc = soup.doc
        numbers, roman, letters = soup("a")

        self.assertEqual(roman.parent, doc)
        oldPrevious = roman.previous
        endOfThisTag = roman.nextSibling.previous
        self.assertEqual(oldPrevious, "2")
        self.assertEqual(roman.next, "i")
        self.assertEqual(endOfThisTag, "ii")
        self.assertEqual(roman.previousSibling, numbers)
        self.assertEqual(roman.nextSibling, letters)

        roman.extract()
        self.assertEqual(roman.parent, None)
        self.assertEqual(roman.previous, None)
        self.assertEqual(roman.next, "i")
        self.assertEqual(letters.previous, '2')
        self.assertEqual(roman.previousSibling, None)
        self.assertEqual(roman.nextSibling, None)
        self.assertEqual(endOfThisTag.next, None)
        self.assertEqual(roman.b.contents[0].next, None)
        self.assertEqual(numbers.nextSibling, letters)
        self.assertEqual(letters.previousSibling, numbers)
        self.assertEqual(len(doc.contents), 2)
        self.assertEqual(doc.contents[0], numbers)
        self.assertEqual(doc.contents[1], letters)

        # A more complex case.
        text = "<a>1<b>2<c>Hollywood, baby!</c></b></a>3"
        soup = BeautifulStoneSoup(text)
        one = soup.find(text="1")
        three = soup.find(text="3")
        toExtract = soup.b
        soup.b.extract()
        self.assertEqual(one.next, three)
        self.assertEqual(three.previous, one)
        self.assertEqual(one.parent.nextSibling, three)
        self.assertEqual(three.previousSibling, soup.a)
        
    def testClear(self):
        soup = BeautifulSoup("<ul><li></li><li></li></ul>")
        soup.ul.clear()
        self.assertEqual(len(soup.ul.contents), 0)

class TheManWithoutAttributes(SoupTest):
    "Test attribute access"

    def testHasKey(self):
        text = "<foo attr='bar'>"
        self.assertEquals(BeautifulSoup(text).foo.has_key('attr'), True)

class QuoteMeOnThat(SoupTest):
    "Test quoting"
    def testQuotedAttributeValues(self):
        self.assertSoupEquals("<foo attr='bar'></foo>",
                              '<foo attr="bar"></foo>')

        text = """<foo attr='bar "brawls" happen'>a</foo>"""
        soup = BeautifulSoup(text)
        self.assertEquals(soup.renderContents(), text)

        soup.foo['attr'] = 'Brawls happen at "Bob\'s Bar"'
        newText = """<foo attr='Brawls happen at "Bob&squot;s Bar"'>a</foo>"""
        self.assertSoupEquals(soup.renderContents(), newText)

        self.assertSoupEquals('<this is="really messed up & stuff">',
                              '<this is="really messed up &amp; stuff"></this>')

        # This is not what the original author had in mind, but it's
        # a legitimate interpretation of what they wrote.
        self.assertSoupEquals("""<a href="foo</a>, </a><a href="bar">baz</a>""",
        '<a href="foo&lt;/a&gt;, &lt;/a&gt;&lt;a href="></a>, <a href="bar">baz</a>')

        # SGMLParser generates bogus parse events when attribute values
        # contain embedded brackets, but at least Beautiful Soup fixes
        # it up a little.
        self.assertSoupEquals('<a b="<a>">', '<a b="&lt;a&gt;"></a><a>"></a>')
        self.assertSoupEquals('<a href="http://foo.com/<a> and blah and blah',
                              """<a href='"http://foo.com/'></a><a> and blah and blah</a>""")



class YoureSoLiteral(SoupTest):
    "Test literal mode."
    def testLiteralMode(self):
        text = "<script>if (i<imgs.length)</script><b>Foo</b>"
        soup = BeautifulSoup(text)
        self.assertEqual(soup.script.contents[0], "if (i<imgs.length)")
        self.assertEqual(soup.b.contents[0], "Foo")

    def testTextArea(self):
        text = "<textarea><b>This is an example of an HTML tag</b><&<&</textarea>"
        soup = BeautifulSoup(text)
        self.assertEqual(soup.textarea.contents[0],
                         "<b>This is an example of an HTML tag</b><&<&")

class OperatorOverload(SoupTest):
    "Our operators do it all! Call now!"

    def testTagNameAsFind(self):
        "Tests that referencing a tag name as a member delegates to find()."
        soup = BeautifulSoup('<b id="1">foo<i>bar</i></b><b>Red herring</b>')
        self.assertEqual(soup.b.i, soup.find('b').find('i'))
        self.assertEqual(soup.b.i.string, 'bar')
        self.assertEqual(soup.b['id'], '1')
        self.assertEqual(soup.b.contents[0], 'foo')
        self.assert_(not soup.a)

        #Test the .fooTag variant of .foo.
        self.assertEqual(soup.bTag.iTag.string, 'bar')
        self.assertEqual(soup.b.iTag.string, 'bar')
        self.assertEqual(soup.find('b').find('i'), soup.bTag.iTag)

class NestableEgg(SoupTest):
    """Here we test tag nesting. TEST THE NEST, DUDE! X-TREME!"""

    def testParaInsideBlockquote(self):
        soup = BeautifulSoup('<blockquote><p><b>Foo</blockquote><p>Bar')
        self.assertEqual(soup.blockquote.p.b.string, 'Foo')
        self.assertEqual(soup.blockquote.b.string, 'Foo')
        self.assertEqual(soup.find('p', recursive=False).string, 'Bar')

    def testNestedTables(self):
        text = """<table id="1"><tr><td>Here's another table:
        <table id="2"><tr><td>Juicy text</td></tr></table></td></tr></table>"""
        soup = BeautifulSoup(text)
        self.assertEquals(soup.table.table.td.string, 'Juicy text')
        self.assertEquals(len(soup.findAll('table')), 2)
        self.assertEquals(len(soup.table.findAll('table')), 1)
        self.assertEquals(soup.find('table', {'id' : 2}).parent.parent.parent.name,
                          'table')

        text = "<table><tr><td><div><table>Foo</table></div></td></tr></table>"
        soup = BeautifulSoup(text)
        self.assertEquals(soup.table.tr.td.div.table.contents[0], "Foo")

        text = """<table><thead><tr>Foo</tr></thead><tbody><tr>Bar</tr></tbody>
        <tfoot><tr>Baz</tr></tfoot></table>"""
        soup = BeautifulSoup(text)
        self.assertEquals(soup.table.thead.tr.contents[0], "Foo")

    def testBadNestedTables(self):
        soup = BeautifulSoup("<table><tr><table><tr id='nested'>")
        self.assertEquals(soup.table.tr.table.tr['id'], 'nested')

class CleanupOnAisleFour(SoupTest):
    """Here we test cleanup of text that breaks SGMLParser or is just
    obnoxious."""

    def testSelfClosingtag(self):
        self.assertEqual(str(BeautifulSoup("Foo<br/>Bar").find('br')),
                         '<br />')

        self.assertSoupEquals('<p>test1<br/>test2</p>',
                              '<p>test1<br />test2</p>')

        text = '<p>test1<selfclosing>test2'
        soup = BeautifulStoneSoup(text)
        self.assertEqual(str(soup),
                         '<p>test1<selfclosing>test2</selfclosing></p>')

        soup = BeautifulStoneSoup(text, selfClosingTags='selfclosing')
        self.assertEqual(str(soup),
                         '<p>test1<selfclosing />test2</p>')

    def testSelfClosingTagOrNot(self):
        text = "<item><link>http://foo.com/</link></item>"
        self.assertEqual(BeautifulStoneSoup(text).renderContents(), text)
        self.assertEqual(BeautifulSoup(text).renderContents(),
                         '<item><link />http://foo.com/</item>')

    def testCData(self):
        xml = "<root>foo<![CDATA[foobar]]>bar</root>"
        self.assertSoupEquals(xml, xml)
        r = re.compile("foo.*bar")
        soup = BeautifulSoup(xml)
        self.assertEquals(soup.find(text=r).string, "foobar")
        self.assertEquals(soup.find(text=r).__class__, CData)

    def testComments(self):
        xml = "foo<!--foobar-->baz"
        self.assertSoupEquals(xml)
        r = re.compile("foo.*bar")
        soup = BeautifulSoup(xml)
        self.assertEquals(soup.find(text=r).string, "foobar")
        self.assertEquals(soup.find(text="foobar").__class__, Comment)

    def testDeclaration(self):
        xml = "foo<!DOCTYPE foobar>baz"
        self.assertSoupEquals(xml)
        r = re.compile(".*foo.*bar")
        soup = BeautifulSoup(xml)
        text = "DOCTYPE foobar"
        self.assertEquals(soup.find(text=r).string, text)
        self.assertEquals(soup.find(text=text).__class__, Declaration)

        namespaced_doctype = ('<!DOCTYPE xsl:stylesheet SYSTEM "htmlent.dtd">'
                              '<html>foo</html>')
        soup = BeautifulSoup(namespaced_doctype)
        self.assertEquals(soup.contents[0],
                          'DOCTYPE xsl:stylesheet SYSTEM "htmlent.dtd"')
        self.assertEquals(soup.html.contents[0], 'foo')

    def testEntityConversions(self):
        text = "&lt;&lt;sacr&eacute;&#32;bleu!&gt;&gt;"
        soup = BeautifulStoneSoup(text)
        self.assertSoupEquals(text)

        xmlEnt = BeautifulStoneSoup.XML_ENTITIES
        htmlEnt = BeautifulStoneSoup.HTML_ENTITIES
        xhtmlEnt = BeautifulStoneSoup.XHTML_ENTITIES

        soup = BeautifulStoneSoup(text, convertEntities=xmlEnt)
        self.assertEquals(str(soup), "<<sacr&eacute; bleu!>>")

        soup = BeautifulStoneSoup(text, convertEntities=xmlEnt)
        self.assertEquals(str(soup), "<<sacr&eacute; bleu!>>")

        soup = BeautifulStoneSoup(text, convertEntities=htmlEnt)
        self.assertEquals(unicode(soup), u"<<sacr\xe9 bleu!>>")

        # Make sure the "XML", "HTML", and "XHTML" settings work.
        text = "&lt;&trade;&apos;"
        soup = BeautifulStoneSoup(text, convertEntities=xmlEnt)
        self.assertEquals(unicode(soup), u"<&trade;'")

        soup = BeautifulStoneSoup(text, convertEntities=htmlEnt)
        self.assertEquals(unicode(soup), u"<\u2122&apos;")

        soup = BeautifulStoneSoup(text, convertEntities=xhtmlEnt)
        self.assertEquals(unicode(soup), u"<\u2122'")

        invalidEntity = "foo&#bar;baz"
        soup = BeautifulStoneSoup\
               (invalidEntity,
                convertEntities=htmlEnt)
        self.assertEquals(str(soup), invalidEntity)

    def testNonBreakingSpaces(self):
        soup = BeautifulSoup("<a>&nbsp;&nbsp;</a>",
                             convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        self.assertEquals(unicode(soup), u"<a>\xa0\xa0</a>")

    def testWhitespaceInDeclaration(self):
        self.assertSoupEquals('<! DOCTYPE>', '<!DOCTYPE>')

    def testJunkInDeclaration(self):
        self.assertSoupEquals('<! Foo = -8>a', '<!Foo = -8>a')

    def testIncompleteDeclaration(self):
        self.assertSoupEquals('a<!b <p>c')

    def testEntityReplacement(self):
        self.assertSoupEquals('<b>hello&nbsp;there</b>')

    def testEntitiesInAttributeValues(self):
        self.assertSoupEquals('<x t="x&#241;">', '<x t="x\xc3\xb1"></x>')
        self.assertSoupEquals('<x t="x&#xf1;">', '<x t="x\xc3\xb1"></x>')

        soup = BeautifulSoup('<x t="&gt;&trade;">',
                             convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        self.assertEquals(unicode(soup), u'<x t="&gt;\u2122"></x>')

        uri = "http://crummy.com?sacr&eacute;&amp;bleu"
        link = '<a href="%s"></a>' % uri
        soup = BeautifulSoup(link)
        self.assertEquals(unicode(soup), link)
        #self.assertEquals(unicode(soup.a['href']), uri)

        soup = BeautifulSoup(link, convertEntities=BeautifulSoup.HTML_ENTITIES)
        self.assertEquals(unicode(soup),
                          link.replace("&eacute;", u"\xe9"))

        uri = "http://crummy.com?sacr&eacute;&bleu"
        link = '<a href="%s"></a>' % uri
        soup = BeautifulSoup(link, convertEntities=BeautifulSoup.HTML_ENTITIES)
        self.assertEquals(unicode(soup.a['href']),
                          uri.replace("&eacute;", u"\xe9"))

    def testNakedAmpersands(self):
        html = {'convertEntities':BeautifulStoneSoup.HTML_ENTITIES}
        soup = BeautifulStoneSoup("AT&T ", **html)
        self.assertEquals(str(soup), 'AT&amp;T ')

        nakedAmpersandInASentence = "AT&T was Ma Bell"
        soup = BeautifulStoneSoup(nakedAmpersandInASentence,**html)
        self.assertEquals(str(soup), \
               nakedAmpersandInASentence.replace('&','&amp;'))

        invalidURL = '<a href="http://example.org?a=1&b=2;3">foo</a>'
        validURL = invalidURL.replace('&','&amp;')
        soup = BeautifulStoneSoup(invalidURL)
        self.assertEquals(str(soup), validURL)

        soup = BeautifulStoneSoup(validURL)
        self.assertEquals(str(soup), validURL)


class EncodeRed(SoupTest):
    """Tests encoding conversion, Unicode conversion, and Microsoft
    smart quote fixes."""

    def testUnicodeDammitStandalone(self):
        markup = "<foo>\x92</foo>"
        dammit = UnicodeDammit(markup)
        self.assertEquals(dammit.unicode, "<foo>&#x2019;</foo>")

        hebrew = "\xed\xe5\xec\xf9"
        dammit = UnicodeDammit(hebrew, ["iso-8859-8"])
        self.assertEquals(dammit.unicode, u'\u05dd\u05d5\u05dc\u05e9')
        self.assertEquals(dammit.originalEncoding, 'iso-8859-8')

    def testGarbageInGarbageOut(self):
        ascii = "<foo>a</foo>"
        asciiSoup = BeautifulStoneSoup(ascii)
        self.assertEquals(ascii, str(asciiSoup))

        unicodeData = u"<foo>\u00FC</foo>"
        utf8 = unicodeData.encode("utf-8")
        self.assertEquals(utf8, '<foo>\xc3\xbc</foo>')

        unicodeSoup = BeautifulStoneSoup(unicodeData)
        self.assertEquals(unicodeData, unicode(unicodeSoup))
        self.assertEquals(unicode(unicodeSoup.foo.string), u'\u00FC')

        utf8Soup = BeautifulStoneSoup(utf8, fromEncoding='utf-8')
        self.assertEquals(utf8, str(utf8Soup))
        self.assertEquals(utf8Soup.originalEncoding, "utf-8")

        utf8Soup = BeautifulStoneSoup(unicodeData)
        self.assertEquals(utf8, str(utf8Soup))
        self.assertEquals(utf8Soup.originalEncoding, None)


    def testHandleInvalidCodec(self):
        for bad_encoding in ['.utf8', '...', 'utF---16.!']:
            soup = BeautifulSoup("Räksmörgås", fromEncoding=bad_encoding)
            self.assertEquals(soup.originalEncoding, 'utf-8')

    def testUnicodeSearch(self):
        html = u'<html><body><h1>Räksmörgås</h1></body></html>'
        soup = BeautifulSoup(html)
        self.assertEqual(soup.find(text=u'Räksmörgås'),u'Räksmörgås')

    def testRewrittenXMLHeader(self):
        euc_jp = '<?xml version="1.0 encoding="euc-jp"?>\n<foo>\n\xa4\xb3\xa4\xec\xa4\xcfEUC-JP\xa4\xc7\xa5\xb3\xa1\xbc\xa5\xc7\xa5\xa3\xa5\xf3\xa5\xb0\xa4\xb5\xa4\xec\xa4\xbf\xc6\xfc\xcb\xdc\xb8\xec\xa4\xce\xa5\xd5\xa5\xa1\xa5\xa4\xa5\xeb\xa4\xc7\xa4\xb9\xa1\xa3\n</foo>\n'
        utf8 = "<?xml version='1.0' encoding='utf-8'?>\n<foo>\n\xe3\x81\x93\xe3\x82\x8c\xe3\x81\xafEUC-JP\xe3\x81\xa7\xe3\x82\xb3\xe3\x83\xbc\xe3\x83\x87\xe3\x82\xa3\xe3\x83\xb3\xe3\x82\xb0\xe3\x81\x95\xe3\x82\x8c\xe3\x81\x9f\xe6\x97\xa5\xe6\x9c\xac\xe8\xaa\x9e\xe3\x81\xae\xe3\x83\x95\xe3\x82\xa1\xe3\x82\xa4\xe3\x83\xab\xe3\x81\xa7\xe3\x81\x99\xe3\x80\x82\n</foo>\n"
        soup = BeautifulStoneSoup(euc_jp)
        if soup.originalEncoding != "euc-jp":
            raise Exception("Test failed when parsing euc-jp document. "
                            "If you're running Python >=2.4, or you have "
                            "cjkcodecs installed, this is a real problem. "
                            "Otherwise, ignore it.")

        self.assertEquals(soup.originalEncoding, "euc-jp")
        self.assertEquals(str(soup), utf8)

        old_text = "<?xml encoding='windows-1252'><foo>\x92</foo>"
        new_text = "<?xml version='1.0' encoding='utf-8'?><foo>&rsquo;</foo>"
        self.assertSoupEquals(old_text, new_text)

    def testRewrittenMetaTag(self):
        no_shift_jis_html = '''<html><head>\n<meta http-equiv="Content-language" content="ja" /></head><body><pre>\n\x82\xb1\x82\xea\x82\xcdShift-JIS\x82\xc5\x83R\x81[\x83f\x83B\x83\x93\x83O\x82\xb3\x82\xea\x82\xbd\x93\xfa\x96{\x8c\xea\x82\xcc\x83t\x83@\x83C\x83\x8b\x82\xc5\x82\xb7\x81B\n</pre></body></html>'''
        soup = BeautifulSoup(no_shift_jis_html)

        # Beautiful Soup used to try to rewrite the meta tag even if the
        # meta tag got filtered out by the strainer. This test makes
        # sure that doesn't happen.
        strainer = SoupStrainer('pre')
        soup = BeautifulSoup(no_shift_jis_html, parseOnlyThese=strainer)
        self.assertEquals(soup.contents[0].name, 'pre')

        meta_tag = ('<meta content="text/html; charset=x-sjis" '
                    'http-equiv="Content-type" />')
        shift_jis_html = (
            '<html><head>\n%s\n'
            '<meta http-equiv="Content-language" content="ja" />'
            '</head><body><pre>\n'
            '\x82\xb1\x82\xea\x82\xcdShift-JIS\x82\xc5\x83R\x81[\x83f'
            '\x83B\x83\x93\x83O\x82\xb3\x82\xea\x82\xbd\x93\xfa\x96{\x8c'
            '\xea\x82\xcc\x83t\x83@\x83C\x83\x8b\x82\xc5\x82\xb7\x81B\n'
            '</pre></body></html>') % meta_tag
        soup = BeautifulSoup(shift_jis_html)
        if soup.originalEncoding != "shift-jis":
            raise Exception("Test failed when parsing shift-jis document "
                            "with meta tag '%s'."
                            "If you're running Python >=2.4, or you have "
                            "cjkcodecs installed, this is a real problem. "
                            "Otherwise, ignore it." % meta_tag)
        self.assertEquals(soup.originalEncoding, "shift-jis")

        content_type_tag = soup.meta['content']
        self.assertEquals(content_type_tag[content_type_tag.find('charset='):],
                          'charset=%SOUP-ENCODING%')
        content_type = str(soup.meta)
        index = content_type.find('charset=')
        self.assertEqual(content_type[index:index+len('charset=utf8')+1],
                         'charset=utf-8')
        content_type = soup.meta.__str__('shift-jis')
        index = content_type.find('charset=')
        self.assertEqual(content_type[index:index+len('charset=shift-jis')],
                         'charset=shift-jis')

        self.assertEquals(str(soup), (
                '<html><head>\n'
                '<meta content="text/html; charset=utf-8" '
                'http-equiv="Content-type" />\n'
                '<meta http-equiv="Content-language" content="ja" />'
                '</head><body><pre>\n'
                '\xe3\x81\x93\xe3\x82\x8c\xe3\x81\xafShift-JIS\xe3\x81\xa7\xe3'
                '\x82\xb3\xe3\x83\xbc\xe3\x83\x87\xe3\x82\xa3\xe3\x83\xb3\xe3'
                '\x82\xb0\xe3\x81\x95\xe3\x82\x8c\xe3\x81\x9f\xe6\x97\xa5\xe6'
                '\x9c\xac\xe8\xaa\x9e\xe3\x81\xae\xe3\x83\x95\xe3\x82\xa1\xe3'
                '\x82\xa4\xe3\x83\xab\xe3\x81\xa7\xe3\x81\x99\xe3\x80\x82\n'
                '</pre></body></html>'))
        self.assertEquals(soup.renderContents("shift-jis"),
                          shift_jis_html.replace('x-sjis', 'shift-jis'))

        isolatin ="""<html><meta http-equiv="Content-type" content="text/html; charset=ISO-Latin-1" />Sacr\xe9 bleu!</html>"""
        soup = BeautifulSoup(isolatin)
        self.assertSoupEquals(soup.__str__("utf-8"),
                              isolatin.replace("ISO-Latin-1", "utf-8").replace("\xe9", "\xc3\xa9"))

    def testHebrew(self):
        iso_8859_8= '<HEAD>\n<TITLE>Hebrew (ISO 8859-8) in Visual Directionality</TITLE>\n\n\n\n</HEAD>\n<BODY>\n<H1>Hebrew (ISO 8859-8) in Visual Directionality</H1>\n\xed\xe5\xec\xf9\n</BODY>\n'
        utf8 = '<head>\n<title>Hebrew (ISO 8859-8) in Visual Directionality</title>\n</head>\n<body>\n<h1>Hebrew (ISO 8859-8) in Visual Directionality</h1>\n\xd7\x9d\xd7\x95\xd7\x9c\xd7\xa9\n</body>\n'
        soup = BeautifulStoneSoup(iso_8859_8, fromEncoding="iso-8859-8")
        self.assertEquals(str(soup), utf8)

    def testSmartQuotesNotSoSmartAnymore(self):
        self.assertSoupEquals("\x91Foo\x92 <!--blah-->",
                              '&lsquo;Foo&rsquo; <!--blah-->')

    def testDontConvertSmartQuotesWhenAlsoConvertingEntities(self):
        smartQuotes = "Il a dit, \x8BSacr&eacute; bl&#101;u!\x9b"
        soup = BeautifulSoup(smartQuotes)
        self.assertEquals(str(soup),
                          'Il a dit, &lsaquo;Sacr&eacute; bl&#101;u!&rsaquo;')
        soup = BeautifulSoup(smartQuotes, convertEntities="html")
        self.assertEquals(str(soup),
                          'Il a dit, \xe2\x80\xb9Sacr\xc3\xa9 bleu!\xe2\x80\xba')

    def testDontSeeSmartQuotesWhereThereAreNone(self):
        utf_8 = "\343\202\261\343\203\274\343\202\277\343\202\244 Watch"
        self.assertSoupEquals(utf_8)


class Whitewash(SoupTest):
    """Test whitespace preservation."""

    def testPreservedWhitespace(self):
        self.assertSoupEquals("<pre>   </pre>")
        self.assertSoupEquals("<pre> woo  </pre>")

    def testCollapsedWhitespace(self):
        self.assertSoupEquals("<p>   </p>", "<p> </p>")


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
