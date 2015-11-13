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
__FILENAME__ = easter
"""
Copyright (c) 2003-2007  Gustavo Niemeyer <gustavo@niemeyer.net>

This module offers extensions to the standard python 2.3+
datetime module.
"""
__author__ = "Gustavo Niemeyer <gustavo@niemeyer.net>"
__license__ = "PSF License"

import datetime

__all__ = ["easter", "EASTER_JULIAN", "EASTER_ORTHODOX", "EASTER_WESTERN"]

EASTER_JULIAN   = 1
EASTER_ORTHODOX = 2
EASTER_WESTERN  = 3

def easter(year, method=EASTER_WESTERN):
    """
    This method was ported from the work done by GM Arts,
    on top of the algorithm by Claus Tondering, which was
    based in part on the algorithm of Ouding (1940), as
    quoted in "Explanatory Supplement to the Astronomical
    Almanac", P.  Kenneth Seidelmann, editor.

    This algorithm implements three different easter
    calculation methods:
    
    1 - Original calculation in Julian calendar, valid in
        dates after 326 AD
    2 - Original method, with date converted to Gregorian
        calendar, valid in years 1583 to 4099
    3 - Revised method, in Gregorian calendar, valid in
        years 1583 to 4099 as well

    These methods are represented by the constants:

    EASTER_JULIAN   = 1
    EASTER_ORTHODOX = 2
    EASTER_WESTERN  = 3

    The default method is method 3.
    
    More about the algorithm may be found at:

    http://users.chariot.net.au/~gmarts/eastalg.htm

    and

    http://www.tondering.dk/claus/calendar.html

    """

    if not (1 <= method <= 3):
        raise ValueError, "invalid method"

    # g - Golden year - 1
    # c - Century
    # h - (23 - Epact) mod 30
    # i - Number of days from March 21 to Paschal Full Moon
    # j - Weekday for PFM (0=Sunday, etc)
    # p - Number of days from March 21 to Sunday on or before PFM
    #     (-6 to 28 methods 1 & 3, to 56 for method 2)
    # e - Extra days to add for method 2 (converting Julian
    #     date to Gregorian date)

    y = year
    g = y % 19
    e = 0
    if method < 3:
        # Old method
        i = (19*g+15)%30
        j = (y+y//4+i)%7
        if method == 2:
            # Extra dates to convert Julian to Gregorian date
            e = 10
            if y > 1600:
                e = e+y//100-16-(y//100-16)//4
    else:
        # New method
        c = y//100
        h = (c-c//4-(8*c+13)//25+19*g+15)%30
        i = h-(h//28)*(1-(h//28)*(29//(h+1))*((21-g)//11))
        j = (y+y//4+i+2-c+c//4)%7

    # p can be from -6 to 56 corresponding to dates 22 March to 23 May
    # (later dates apply to method 2, although 23 May never actually occurs)
    p = i-j+e
    d = 1+(p+27+(p+6)//40)%31
    m = 3+(p+26)//30
    return datetime.date(int(y),int(m),int(d))


########NEW FILE########
__FILENAME__ = parser
# -*- coding:iso-8859-1 -*-
"""
Copyright (c) 2003-2007  Gustavo Niemeyer <gustavo@niemeyer.net>

This module offers extensions to the standard python 2.3+
datetime module.
"""
__author__ = "Gustavo Niemeyer <gustavo@niemeyer.net>"
__license__ = "PSF License"

import datetime
import string
import time
import sys
import os

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import relativedelta
import tz


__all__ = ["parse", "parserinfo"]


# Some pointers:
#
# http://www.cl.cam.ac.uk/~mgk25/iso-time.html
# http://www.iso.ch/iso/en/prods-services/popstds/datesandtime.html
# http://www.w3.org/TR/NOTE-datetime
# http://ringmaster.arc.nasa.gov/tools/time_formats.html
# http://search.cpan.org/author/MUIR/Time-modules-2003.0211/lib/Time/ParseDate.pm
# http://stein.cshl.org/jade/distrib/docs/java.text.SimpleDateFormat.html


class _timelex(object):

    def __init__(self, instream):
        if isinstance(instream, basestring):
            instream = StringIO(instream)
        self.instream = instream
        self.wordchars = ('abcdfeghijklmnopqrstuvwxyz'
                          'ABCDEFGHIJKLMNOPQRSTUVWXYZ_'
                          'ßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ'
                          'ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ')
        self.numchars = '0123456789'
        self.whitespace = ' \t\r\n'
        self.charstack = []
        self.tokenstack = []
        self.eof = False

    def get_token(self):
        if self.tokenstack:
            return self.tokenstack.pop(0)
        seenletters = False
        token = None
        state = None
        wordchars = self.wordchars
        numchars = self.numchars
        whitespace = self.whitespace
        while not self.eof:
            if self.charstack:
                nextchar = self.charstack.pop(0)
            else:
                nextchar = self.instream.read(1)
                while nextchar == '\x00':
                    nextchar = self.instream.read(1)
            if not nextchar:
                self.eof = True
                break
            elif not state:
                token = nextchar
                if nextchar in wordchars:
                    state = 'a'
                elif nextchar in numchars:
                    state = '0'
                elif nextchar in whitespace:
                    token = ' '
                    break # emit token
                else:
                    break # emit token
            elif state == 'a':
                seenletters = True
                if nextchar in wordchars:
                    token += nextchar
                elif nextchar == '.':
                    token += nextchar
                    state = 'a.'
                else:
                    self.charstack.append(nextchar)
                    break # emit token
            elif state == '0':
                if nextchar in numchars:
                    token += nextchar
                elif nextchar == '.':
                    token += nextchar
                    state = '0.'
                else:
                    self.charstack.append(nextchar)
                    break # emit token
            elif state == 'a.':
                seenletters = True
                if nextchar == '.' or nextchar in wordchars:
                    token += nextchar
                elif nextchar in numchars and token[-1] == '.':
                    token += nextchar
                    state = '0.'
                else:
                    self.charstack.append(nextchar)
                    break # emit token
            elif state == '0.':
                if nextchar == '.' or nextchar in numchars:
                    token += nextchar
                elif nextchar in wordchars and token[-1] == '.':
                    token += nextchar
                    state = 'a.'
                else:
                    self.charstack.append(nextchar)
                    break # emit token
        if (state in ('a.', '0.') and
            (seenletters or token.count('.') > 1 or token[-1] == '.')):
            l = token.split('.')
            token = l[0]
            for tok in l[1:]:
                self.tokenstack.append('.')
                if tok:
                    self.tokenstack.append(tok)
        return token

    def __iter__(self):
        return self

    def next(self):
        token = self.get_token()
        if token is None:
            raise StopIteration
        return token

    def split(cls, s):
        return list(cls(s))
    split = classmethod(split)


class _resultbase(object):

    def __init__(self):
        for attr in self.__slots__:
            setattr(self, attr, None)

    def _repr(self, classname):
        l = []
        for attr in self.__slots__:
            value = getattr(self, attr)
            if value is not None:
                l.append("%s=%s" % (attr, `value`))
        return "%s(%s)" % (classname, ", ".join(l))

    def __repr__(self):
        return self._repr(self.__class__.__name__)


class parserinfo(object):

    # m from a.m/p.m, t from ISO T separator
    JUMP = [" ", ".", ",", ";", "-", "/", "'",
            "at", "on", "and", "ad", "m", "t", "of",
            "st", "nd", "rd", "th"] 

    WEEKDAYS = [("Mon", "Monday"),
                ("Tue", "Tuesday"),
                ("Wed", "Wednesday"),
                ("Thu", "Thursday"),
                ("Fri", "Friday"),
                ("Sat", "Saturday"),
                ("Sun", "Sunday")]
    MONTHS   = [("Jan", "January"),
                ("Feb", "February"),
                ("Mar", "March"),
                ("Apr", "April"),
                ("May", "May"),
                ("Jun", "June"),
                ("Jul", "July"),
                ("Aug", "August"),
                ("Sep", "September"),
                ("Oct", "October"),
                ("Nov", "November"),
                ("Dec", "December")]
    HMS = [("h", "hour", "hours"),
           ("m", "minute", "minutes"),
           ("s", "second", "seconds")]
    AMPM = [("am", "a"),
            ("pm", "p")]
    UTCZONE = ["UTC", "GMT", "Z"]
    PERTAIN = ["of"]
    TZOFFSET = {}

    def __init__(self, dayfirst=False, yearfirst=False):
        self._jump = self._convert(self.JUMP)
        self._weekdays = self._convert(self.WEEKDAYS)
        self._months = self._convert(self.MONTHS)
        self._hms = self._convert(self.HMS)
        self._ampm = self._convert(self.AMPM)
        self._utczone = self._convert(self.UTCZONE)
        self._pertain = self._convert(self.PERTAIN)

        self.dayfirst = dayfirst
        self.yearfirst = yearfirst

        self._year = time.localtime().tm_year
        self._century = self._year//100*100

    def _convert(self, lst):
        dct = {}
        for i in range(len(lst)):
            v = lst[i]
            if isinstance(v, tuple):
                for v in v:
                    dct[v.lower()] = i
            else:
                dct[v.lower()] = i
        return dct

    def jump(self, name):
        return name.lower() in self._jump

    def weekday(self, name):
        if len(name) >= 3:
            try:
                return self._weekdays[name.lower()]
            except KeyError:
                pass
        return None

    def month(self, name):
        if len(name) >= 3:
            try:
                return self._months[name.lower()]+1
            except KeyError:
                pass
        return None

    def hms(self, name):
        try:
            return self._hms[name.lower()]
        except KeyError:
            return None

    def ampm(self, name):
        try:
            return self._ampm[name.lower()]
        except KeyError:
            return None

    def pertain(self, name):
        return name.lower() in self._pertain

    def utczone(self, name):
        return name.lower() in self._utczone

    def tzoffset(self, name):
        if name in self._utczone:
            return 0
        return self.TZOFFSET.get(name)

    def convertyear(self, year):
        if year < 100:
            year += self._century
            if abs(year-self._year) >= 50:
                if year < self._year:
                    year += 100
                else:
                    year -= 100
        return year

    def validate(self, res):
        # move to info
        if res.year is not None:
            res.year = self.convertyear(res.year)
        if res.tzoffset == 0 and not res.tzname or res.tzname == 'Z':
            res.tzname = "UTC"
            res.tzoffset = 0
        elif res.tzoffset != 0 and res.tzname and self.utczone(res.tzname):
            res.tzoffset = 0
        return True


class parser(object):

    def __init__(self, info=None):
        self.info = info or parserinfo()

    def parse(self, timestr, default=None,
                    ignoretz=False, tzinfos=None,
                    **kwargs):
        if not default:
            default = datetime.datetime.now().replace(hour=0, minute=0,
                                                      second=0, microsecond=0)
        res = self._parse(timestr, **kwargs)
        if res is None:
            raise ValueError, "unknown string format"
        repl = {}
        for attr in ["year", "month", "day", "hour",
                     "minute", "second", "microsecond"]:
            value = getattr(res, attr)
            if value is not None:
                repl[attr] = value
        ret = default.replace(**repl)
        if res.weekday is not None and not res.day:
            ret = ret+relativedelta.relativedelta(weekday=res.weekday)
        if not ignoretz:
            if callable(tzinfos) or tzinfos and res.tzname in tzinfos:
                if callable(tzinfos):
                    tzdata = tzinfos(res.tzname, res.tzoffset)
                else:
                    tzdata = tzinfos.get(res.tzname)
                if isinstance(tzdata, datetime.tzinfo):
                    tzinfo = tzdata
                elif isinstance(tzdata, basestring):
                    tzinfo = tz.tzstr(tzdata)
                elif isinstance(tzdata, int):
                    tzinfo = tz.tzoffset(res.tzname, tzdata)
                else:
                    raise ValueError, "offset must be tzinfo subclass, " \
                                      "tz string, or int offset"
                ret = ret.replace(tzinfo=tzinfo)
            elif res.tzname and res.tzname in time.tzname:
                ret = ret.replace(tzinfo=tz.tzlocal())
            elif res.tzoffset == 0:
                ret = ret.replace(tzinfo=tz.tzutc())
            elif res.tzoffset:
                ret = ret.replace(tzinfo=tz.tzoffset(res.tzname, res.tzoffset))
        return ret

    class _result(_resultbase):
        __slots__ = ["year", "month", "day", "weekday",
                     "hour", "minute", "second", "microsecond",
                     "tzname", "tzoffset"]

    def _parse(self, timestr, dayfirst=None, yearfirst=None, fuzzy=False):
        info = self.info
        if dayfirst is None:
            dayfirst = info.dayfirst
        if yearfirst is None:
            yearfirst = info.yearfirst
        res = self._result()
        l = _timelex.split(timestr)
        try:

            # year/month/day list
            ymd = []

            # Index of the month string in ymd
            mstridx = -1

            len_l = len(l)
            i = 0
            while i < len_l:

                # Check if it's a number
                try:
                    value_repr = l[i]
                    value = float(value_repr)
                except ValueError:
                    value = None

                if value is not None:
                    # Token is a number
                    len_li = len(l[i])
                    i += 1
                    if (len(ymd) == 3 and len_li in (2, 4)
                        and (i >= len_l or (l[i] != ':' and
                                            info.hms(l[i]) is None))):
                        # 19990101T23[59]
                        s = l[i-1]
                        res.hour = int(s[:2])
                        if len_li == 4:
                            res.minute = int(s[2:])
                    elif len_li == 6 or (len_li > 6 and l[i-1].find('.') == 6):
                        # YYMMDD or HHMMSS[.ss]
                        s = l[i-1] 
                        if not ymd and l[i-1].find('.') == -1:
                            ymd.append(info.convertyear(int(s[:2])))
                            ymd.append(int(s[2:4]))
                            ymd.append(int(s[4:]))
                        else:
                            # 19990101T235959[.59]
                            res.hour = int(s[:2])
                            res.minute = int(s[2:4])
                            res.second, res.microsecond = _parsems(s[4:])
                    elif len_li == 8:
                        # YYYYMMDD
                        s = l[i-1]
                        ymd.append(int(s[:4]))
                        ymd.append(int(s[4:6]))
                        ymd.append(int(s[6:]))
                    elif len_li in (12, 14):
                        # YYYYMMDDhhmm[ss]
                        s = l[i-1]
                        ymd.append(int(s[:4]))
                        ymd.append(int(s[4:6]))
                        ymd.append(int(s[6:8]))
                        res.hour = int(s[8:10])
                        res.minute = int(s[10:12])
                        if len_li == 14:
                            res.second = int(s[12:])
                    elif ((i < len_l and info.hms(l[i]) is not None) or
                          (i+1 < len_l and l[i] == ' ' and
                           info.hms(l[i+1]) is not None)):
                        # HH[ ]h or MM[ ]m or SS[.ss][ ]s
                        if l[i] == ' ':
                            i += 1
                        idx = info.hms(l[i])
                        while True:
                            if idx == 0:
                                res.hour = int(value)
                                if value%1:
                                    res.minute = int(60*(value%1))
                            elif idx == 1:
                                res.minute = int(value)
                                if value%1:
                                    res.second = int(60*(value%1))
                            elif idx == 2:
                                res.second, res.microsecond = \
                                    _parsems(value_repr)
                            i += 1
                            if i >= len_l or idx == 2:
                                break
                            # 12h00
                            try:
                                value_repr = l[i]
                                value = float(value_repr)
                            except ValueError:
                                break
                            else:
                                i += 1
                                idx += 1
                                if i < len_l:
                                    newidx = info.hms(l[i])
                                    if newidx is not None:
                                        idx = newidx
                    elif i+1 < len_l and l[i] == ':':
                        # HH:MM[:SS[.ss]]
                        res.hour = int(value)
                        i += 1
                        value = float(l[i])
                        res.minute = int(value)
                        if value%1:
                            res.second = int(60*(value%1))
                        i += 1
                        if i < len_l and l[i] == ':':
                            res.second, res.microsecond = _parsems(l[i+1])
                            i += 2
                    elif i < len_l and l[i] in ('-', '/', '.'):
                        sep = l[i]
                        ymd.append(int(value))
                        i += 1
                        if i < len_l and not info.jump(l[i]):
                            try:
                                # 01-01[-01]
                                ymd.append(int(l[i]))
                            except ValueError:
                                # 01-Jan[-01]
                                value = info.month(l[i])
                                if value is not None:
                                    ymd.append(value)
                                    assert mstridx == -1
                                    mstridx = len(ymd)-1
                                else:
                                    return None
                            i += 1
                            if i < len_l and l[i] == sep:
                                # We have three members
                                i += 1
                                value = info.month(l[i])
                                if value is not None:
                                    ymd.append(value)
                                    mstridx = len(ymd)-1
                                    assert mstridx == -1
                                else:
                                    ymd.append(int(l[i]))
                                i += 1
                    elif i >= len_l or info.jump(l[i]):
                        if i+1 < len_l and info.ampm(l[i+1]) is not None:
                            # 12 am
                            res.hour = int(value)
                            if res.hour < 12 and info.ampm(l[i+1]) == 1:
                                res.hour += 12
                            elif res.hour == 12 and info.ampm(l[i+1]) == 0:
                                res.hour = 0
                            i += 1
                        else:
                            # Year, month or day
                            ymd.append(int(value))
                        i += 1
                    elif info.ampm(l[i]) is not None:
                        # 12am
                        res.hour = int(value)
                        if res.hour < 12 and info.ampm(l[i]) == 1:
                            res.hour += 12
                        elif res.hour == 12 and info.ampm(l[i]) == 0:
                            res.hour = 0
                        i += 1
                    elif not fuzzy:
                        return None
                    else:
                        i += 1
                    continue

                # Check weekday
                value = info.weekday(l[i])
                if value is not None:
                    res.weekday = value
                    i += 1
                    continue

                # Check month name
                value = info.month(l[i])
                if value is not None:
                    ymd.append(value)
                    assert mstridx == -1
                    mstridx = len(ymd)-1
                    i += 1
                    if i < len_l:
                        if l[i] in ('-', '/'):
                            # Jan-01[-99]
                            sep = l[i]
                            i += 1
                            ymd.append(int(l[i]))
                            i += 1
                            if i < len_l and l[i] == sep:
                                # Jan-01-99
                                i += 1
                                ymd.append(int(l[i]))
                                i += 1
                        elif (i+3 < len_l and l[i] == l[i+2] == ' '
                              and info.pertain(l[i+1])):
                            # Jan of 01
                            # In this case, 01 is clearly year
                            try:
                                value = int(l[i+3])
                            except ValueError:
                                # Wrong guess
                                pass
                            else:
                                # Convert it here to become unambiguous
                                ymd.append(info.convertyear(value))
                            i += 4
                    continue

                # Check am/pm
                value = info.ampm(l[i])
                if value is not None:
                    if value == 1 and res.hour < 12:
                        res.hour += 12
                    elif value == 0 and res.hour == 12:
                        res.hour = 0
                    i += 1
                    continue

                # Check for a timezone name
                if (res.hour is not None and len(l[i]) <= 5 and
                    res.tzname is None and res.tzoffset is None and
                    not [x for x in l[i] if x not in string.ascii_uppercase]):
                    res.tzname = l[i]
                    res.tzoffset = info.tzoffset(res.tzname)
                    i += 1

                    # Check for something like GMT+3, or BRST+3. Notice
                    # that it doesn't mean "I am 3 hours after GMT", but
                    # "my time +3 is GMT". If found, we reverse the
                    # logic so that timezone parsing code will get it
                    # right.
                    if i < len_l and l[i] in ('+', '-'):
                        l[i] = ('+', '-')[l[i] == '+']
                        res.tzoffset = None
                        if info.utczone(res.tzname):
                            # With something like GMT+3, the timezone
                            # is *not* GMT.
                            res.tzname = None

                    continue

                # Check for a numbered timezone
                if res.hour is not None and l[i] in ('+', '-'):
                    signal = (-1,1)[l[i] == '+']
                    i += 1
                    len_li = len(l[i])
                    if len_li == 4:
                        # -0300
                        res.tzoffset = int(l[i][:2])*3600+int(l[i][2:])*60
                    elif i+1 < len_l and l[i+1] == ':':
                        # -03:00
                        res.tzoffset = int(l[i])*3600+int(l[i+2])*60
                        i += 2
                    elif len_li <= 2:
                        # -[0]3
                        res.tzoffset = int(l[i][:2])*3600
                    else:
                        return None
                    i += 1
                    res.tzoffset *= signal

                    # Look for a timezone name between parenthesis
                    if (i+3 < len_l and
                        info.jump(l[i]) and l[i+1] == '(' and l[i+3] == ')' and
                        3 <= len(l[i+2]) <= 5 and
                        not [x for x in l[i+2]
                                if x not in string.ascii_uppercase]):
                        # -0300 (BRST)
                        res.tzname = l[i+2]
                        i += 4
                    continue

                # Check jumps
                if not (info.jump(l[i]) or fuzzy):
                    return None

                i += 1

            # Process year/month/day
            len_ymd = len(ymd)
            if len_ymd > 3:
                # More than three members!?
                return None
            elif len_ymd == 1 or (mstridx != -1 and len_ymd == 2):
                # One member, or two members with a month string
                if mstridx != -1:
                    res.month = ymd[mstridx]
                    del ymd[mstridx]
                if len_ymd > 1 or mstridx == -1:
                    if ymd[0] > 31:
                        res.year = ymd[0]
                    else:
                        res.day = ymd[0]
            elif len_ymd == 2:
                # Two members with numbers
                if ymd[0] > 31:
                    # 99-01
                    res.year, res.month = ymd
                elif ymd[1] > 31:
                    # 01-99
                    res.month, res.year = ymd
                elif dayfirst and ymd[1] <= 12:
                    # 13-01
                    res.day, res.month = ymd
                else:
                    # 01-13
                    res.month, res.day = ymd
            if len_ymd == 3:
                # Three members
                if mstridx == 0:
                    res.month, res.day, res.year = ymd
                elif mstridx == 1:
                    if ymd[0] > 31 or (yearfirst and ymd[2] <= 31):
                        # 99-Jan-01
                        res.year, res.month, res.day = ymd
                    else:
                        # 01-Jan-01
                        # Give precendence to day-first, since
                        # two-digit years is usually hand-written.
                        res.day, res.month, res.year = ymd
                elif mstridx == 2:
                    # WTF!?
                    if ymd[1] > 31:
                        # 01-99-Jan
                        res.day, res.year, res.month = ymd
                    else:
                        # 99-01-Jan
                        res.year, res.day, res.month = ymd
                else:
                    if ymd[0] > 31 or \
                       (yearfirst and ymd[1] <= 12 and ymd[2] <= 31):
                        # 99-01-01
                        res.year, res.month, res.day = ymd
                    elif ymd[0] > 12 or (dayfirst and ymd[1] <= 12):
                        # 13-01-01
                        res.day, res.month, res.year = ymd
                    else:
                        # 01-13-01
                        res.month, res.day, res.year = ymd

        except (IndexError, ValueError, AssertionError):
            return None

        if not info.validate(res):
            return None
        return res

DEFAULTPARSER = parser()
def parse(timestr, parserinfo=None, **kwargs):
    if parserinfo:
        return parser(parserinfo).parse(timestr, **kwargs)
    else:
        return DEFAULTPARSER.parse(timestr, **kwargs)


class _tzparser(object):

    class _result(_resultbase):

        __slots__ = ["stdabbr", "stdoffset", "dstabbr", "dstoffset",
                     "start", "end"]

        class _attr(_resultbase):
            __slots__ = ["month", "week", "weekday",
                         "yday", "jyday", "day", "time"]

        def __repr__(self):
            return self._repr("")

        def __init__(self):
            _resultbase.__init__(self)
            self.start = self._attr()
            self.end = self._attr()

    def parse(self, tzstr):
        res = self._result()
        l = _timelex.split(tzstr)
        try:

            len_l = len(l)

            i = 0
            while i < len_l:
                # BRST+3[BRDT[+2]]
                j = i
                while j < len_l and not [x for x in l[j]
                                            if x in "0123456789:,-+"]:
                    j += 1
                if j != i:
                    if not res.stdabbr:
                        offattr = "stdoffset"
                        res.stdabbr = "".join(l[i:j])
                    else:
                        offattr = "dstoffset"
                        res.dstabbr = "".join(l[i:j])
                    i = j
                    if (i < len_l and
                        (l[i] in ('+', '-') or l[i][0] in "0123456789")):
                        if l[i] in ('+', '-'):
                            # Yes, that's right.  See the TZ variable
                            # documentation.
                            signal = (1,-1)[l[i] == '+']
                            i += 1
                        else:
                            signal = -1
                        len_li = len(l[i])
                        if len_li == 4:
                            # -0300
                            setattr(res, offattr,
                                    (int(l[i][:2])*3600+int(l[i][2:])*60)*signal)
                        elif i+1 < len_l and l[i+1] == ':':
                            # -03:00
                            setattr(res, offattr,
                                    (int(l[i])*3600+int(l[i+2])*60)*signal)
                            i += 2
                        elif len_li <= 2:
                            # -[0]3
                            setattr(res, offattr,
                                    int(l[i][:2])*3600*signal)
                        else:
                            return None
                        i += 1
                    if res.dstabbr:
                        break
                else:
                    break

            if i < len_l:
                for j in range(i, len_l):
                    if l[j] == ';': l[j] = ','

                assert l[i] == ','

                i += 1

            if i >= len_l:
                pass
            elif (8 <= l.count(',') <= 9 and
                not [y for x in l[i:] if x != ','
                       for y in x if y not in "0123456789"]):
                # GMT0BST,3,0,30,3600,10,0,26,7200[,3600]
                for x in (res.start, res.end):
                    x.month = int(l[i])
                    i += 2
                    if l[i] == '-':
                        value = int(l[i+1])*-1
                        i += 1
                    else:
                        value = int(l[i])
                    i += 2
                    if value:
                        x.week = value
                        x.weekday = (int(l[i])-1)%7
                    else:
                        x.day = int(l[i])
                    i += 2
                    x.time = int(l[i])
                    i += 2
                if i < len_l:
                    if l[i] in ('-','+'):
                        signal = (-1,1)[l[i] == "+"]
                        i += 1
                    else:
                        signal = 1
                    res.dstoffset = (res.stdoffset+int(l[i]))*signal
            elif (l.count(',') == 2 and l[i:].count('/') <= 2 and
                  not [y for x in l[i:] if x not in (',','/','J','M',
                                                     '.','-',':')
                         for y in x if y not in "0123456789"]):
                for x in (res.start, res.end):
                    if l[i] == 'J':
                        # non-leap year day (1 based)
                        i += 1
                        x.jyday = int(l[i])
                    elif l[i] == 'M':
                        # month[-.]week[-.]weekday
                        i += 1
                        x.month = int(l[i])
                        i += 1
                        assert l[i] in ('-', '.')
                        i += 1
                        x.week = int(l[i])
                        if x.week == 5:
                            x.week = -1
                        i += 1
                        assert l[i] in ('-', '.')
                        i += 1
                        x.weekday = (int(l[i])-1)%7
                    else:
                        # year day (zero based)
                        x.yday = int(l[i])+1

                    i += 1

                    if i < len_l and l[i] == '/':
                        i += 1
                        # start time
                        len_li = len(l[i])
                        if len_li == 4:
                            # -0300
                            x.time = (int(l[i][:2])*3600+int(l[i][2:])*60)
                        elif i+1 < len_l and l[i+1] == ':':
                            # -03:00
                            x.time = int(l[i])*3600+int(l[i+2])*60
                            i += 2
                            if i+1 < len_l and l[i+1] == ':':
                                i += 2
                                x.time += int(l[i])
                        elif len_li <= 2:
                            # -[0]3
                            x.time = (int(l[i][:2])*3600)
                        else:
                            return None
                        i += 1

                    assert i == len_l or l[i] == ','

                    i += 1

                assert i >= len_l

        except (IndexError, ValueError, AssertionError):
            return None
        
        return res


DEFAULTTZPARSER = _tzparser()
def _parsetz(tzstr):
    return DEFAULTTZPARSER.parse(tzstr)


def _parsems(value):
    """Parse a I[.F] seconds value into (seconds, microseconds)."""
    if "." not in value:
        return int(value), 0
    else:
        i, f = value.split(".")
        return int(i), int(f.ljust(6, "0")[:6])


# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = relativedelta
"""
Copyright (c) 2003-2010  Gustavo Niemeyer <gustavo@niemeyer.net>

This module offers extensions to the standard python 2.3+
datetime module.
"""
__author__ = "Gustavo Niemeyer <gustavo@niemeyer.net>"
__license__ = "PSF License"

import datetime
import calendar

__all__ = ["relativedelta", "MO", "TU", "WE", "TH", "FR", "SA", "SU"]

class weekday(object):
    __slots__ = ["weekday", "n"]

    def __init__(self, weekday, n=None):
        self.weekday = weekday
        self.n = n

    def __call__(self, n):
        if n == self.n:
            return self
        else:
            return self.__class__(self.weekday, n)

    def __eq__(self, other):
        try:
            if self.weekday != other.weekday or self.n != other.n:
                return False
        except AttributeError:
            return False
        return True

    def __repr__(self):
        s = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")[self.weekday]
        if not self.n:
            return s
        else:
            return "%s(%+d)" % (s, self.n)

MO, TU, WE, TH, FR, SA, SU = weekdays = tuple([weekday(x) for x in range(7)])

class relativedelta:
    """
The relativedelta type is based on the specification of the excelent
work done by M.-A. Lemburg in his mx.DateTime extension. However,
notice that this type does *NOT* implement the same algorithm as
his work. Do *NOT* expect it to behave like mx.DateTime's counterpart.

There's two different ways to build a relativedelta instance. The
first one is passing it two date/datetime classes:

    relativedelta(datetime1, datetime2)

And the other way is to use the following keyword arguments:

    year, month, day, hour, minute, second, microsecond:
        Absolute information.

    years, months, weeks, days, hours, minutes, seconds, microseconds:
        Relative information, may be negative.

    weekday:
        One of the weekday instances (MO, TU, etc). These instances may
        receive a parameter N, specifying the Nth weekday, which could
        be positive or negative (like MO(+1) or MO(-2). Not specifying
        it is the same as specifying +1. You can also use an integer,
        where 0=MO.

    leapdays:
        Will add given days to the date found, if year is a leap
        year, and the date found is post 28 of february.

    yearday, nlyearday:
        Set the yearday or the non-leap year day (jump leap days).
        These are converted to day/month/leapdays information.

Here is the behavior of operations with relativedelta:

1) Calculate the absolute year, using the 'year' argument, or the
   original datetime year, if the argument is not present.

2) Add the relative 'years' argument to the absolute year.

3) Do steps 1 and 2 for month/months.

4) Calculate the absolute day, using the 'day' argument, or the
   original datetime day, if the argument is not present. Then,
   subtract from the day until it fits in the year and month
   found after their operations.

5) Add the relative 'days' argument to the absolute day. Notice
   that the 'weeks' argument is multiplied by 7 and added to
   'days'.

6) Do steps 1 and 2 for hour/hours, minute/minutes, second/seconds,
   microsecond/microseconds.

7) If the 'weekday' argument is present, calculate the weekday,
   with the given (wday, nth) tuple. wday is the index of the
   weekday (0-6, 0=Mon), and nth is the number of weeks to add
   forward or backward, depending on its signal. Notice that if
   the calculated date is already Monday, for example, using
   (0, 1) or (0, -1) won't change the day.
    """

    def __init__(self, dt1=None, dt2=None,
                 years=0, months=0, days=0, leapdays=0, weeks=0,
                 hours=0, minutes=0, seconds=0, microseconds=0,
                 year=None, month=None, day=None, weekday=None,
                 yearday=None, nlyearday=None,
                 hour=None, minute=None, second=None, microsecond=None):
        if dt1 and dt2:
            if not isinstance(dt1, datetime.date) or \
               not isinstance(dt2, datetime.date):
                raise TypeError, "relativedelta only diffs datetime/date"
            if type(dt1) is not type(dt2):
                if not isinstance(dt1, datetime.datetime):
                    dt1 = datetime.datetime.fromordinal(dt1.toordinal())
                elif not isinstance(dt2, datetime.datetime):
                    dt2 = datetime.datetime.fromordinal(dt2.toordinal())
            self.years = 0
            self.months = 0
            self.days = 0
            self.leapdays = 0
            self.hours = 0
            self.minutes = 0
            self.seconds = 0
            self.microseconds = 0
            self.year = None
            self.month = None
            self.day = None
            self.weekday = None
            self.hour = None
            self.minute = None
            self.second = None
            self.microsecond = None
            self._has_time = 0

            months = (dt1.year*12+dt1.month)-(dt2.year*12+dt2.month)
            self._set_months(months)
            dtm = self.__radd__(dt2)
            if dt1 < dt2:
                while dt1 > dtm:
                    months += 1
                    self._set_months(months)
                    dtm = self.__radd__(dt2)
            else:
                while dt1 < dtm:
                    months -= 1
                    self._set_months(months)
                    dtm = self.__radd__(dt2)
            delta = dt1 - dtm
            self.seconds = delta.seconds+delta.days*86400
            self.microseconds = delta.microseconds
        else:
            self.years = years
            self.months = months
            self.days = days+weeks*7
            self.leapdays = leapdays
            self.hours = hours
            self.minutes = minutes
            self.seconds = seconds
            self.microseconds = microseconds
            self.year = year
            self.month = month
            self.day = day
            self.hour = hour
            self.minute = minute
            self.second = second
            self.microsecond = microsecond

            if type(weekday) is int:
                self.weekday = weekdays[weekday]
            else:
                self.weekday = weekday

            yday = 0
            if nlyearday:
                yday = nlyearday
            elif yearday:
                yday = yearday
                if yearday > 59:
                    self.leapdays = -1
            if yday:
                ydayidx = [31,59,90,120,151,181,212,243,273,304,334,366]
                for idx, ydays in enumerate(ydayidx):
                    if yday <= ydays:
                        self.month = idx+1
                        if idx == 0:
                            self.day = yday
                        else:
                            self.day = yday-ydayidx[idx-1]
                        break
                else:
                    raise ValueError, "invalid year day (%d)" % yday

        self._fix()

    def _fix(self):
        if abs(self.microseconds) > 999999:
            s = self.microseconds//abs(self.microseconds)
            div, mod = divmod(self.microseconds*s, 1000000)
            self.microseconds = mod*s
            self.seconds += div*s
        if abs(self.seconds) > 59:
            s = self.seconds//abs(self.seconds)
            div, mod = divmod(self.seconds*s, 60)
            self.seconds = mod*s
            self.minutes += div*s
        if abs(self.minutes) > 59:
            s = self.minutes//abs(self.minutes)
            div, mod = divmod(self.minutes*s, 60)
            self.minutes = mod*s
            self.hours += div*s
        if abs(self.hours) > 23:
            s = self.hours//abs(self.hours)
            div, mod = divmod(self.hours*s, 24)
            self.hours = mod*s
            self.days += div*s
        if abs(self.months) > 11:
            s = self.months//abs(self.months)
            div, mod = divmod(self.months*s, 12)
            self.months = mod*s
            self.years += div*s
        if (self.hours or self.minutes or self.seconds or self.microseconds or
            self.hour is not None or self.minute is not None or
            self.second is not None or self.microsecond is not None):
            self._has_time = 1
        else:
            self._has_time = 0

    def _set_months(self, months):
        self.months = months
        if abs(self.months) > 11:
            s = self.months//abs(self.months)
            div, mod = divmod(self.months*s, 12)
            self.months = mod*s
            self.years = div*s
        else:
            self.years = 0

    def __radd__(self, other):
        if not isinstance(other, datetime.date):
            raise TypeError, "unsupported type for add operation"
        elif self._has_time and not isinstance(other, datetime.datetime):
            other = datetime.datetime.fromordinal(other.toordinal())
        year = (self.year or other.year)+self.years
        month = self.month or other.month
        if self.months:
            assert 1 <= abs(self.months) <= 12
            month += self.months
            if month > 12:
                year += 1
                month -= 12
            elif month < 1:
                year -= 1
                month += 12
        day = min(calendar.monthrange(year, month)[1],
                  self.day or other.day)
        repl = {"year": year, "month": month, "day": day}
        for attr in ["hour", "minute", "second", "microsecond"]:
            value = getattr(self, attr)
            if value is not None:
                repl[attr] = value
        days = self.days
        if self.leapdays and month > 2 and calendar.isleap(year):
            days += self.leapdays
        ret = (other.replace(**repl)
               + datetime.timedelta(days=days,
                                    hours=self.hours,
                                    minutes=self.minutes,
                                    seconds=self.seconds,
                                    microseconds=self.microseconds))
        if self.weekday:
            weekday, nth = self.weekday.weekday, self.weekday.n or 1
            jumpdays = (abs(nth)-1)*7
            if nth > 0:
                jumpdays += (7-ret.weekday()+weekday)%7
            else:
                jumpdays += (ret.weekday()-weekday)%7
                jumpdays *= -1
            ret += datetime.timedelta(days=jumpdays)
        return ret

    def __rsub__(self, other):
        return self.__neg__().__radd__(other)

    def __add__(self, other):
        if not isinstance(other, relativedelta):
            raise TypeError, "unsupported type for add operation"
        return relativedelta(years=other.years+self.years,
                             months=other.months+self.months,
                             days=other.days+self.days,
                             hours=other.hours+self.hours,
                             minutes=other.minutes+self.minutes,
                             seconds=other.seconds+self.seconds,
                             microseconds=other.microseconds+self.microseconds,
                             leapdays=other.leapdays or self.leapdays,
                             year=other.year or self.year,
                             month=other.month or self.month,
                             day=other.day or self.day,
                             weekday=other.weekday or self.weekday,
                             hour=other.hour or self.hour,
                             minute=other.minute or self.minute,
                             second=other.second or self.second,
                             microsecond=other.second or self.microsecond)

    def __sub__(self, other):
        if not isinstance(other, relativedelta):
            raise TypeError, "unsupported type for sub operation"
        return relativedelta(years=other.years-self.years,
                             months=other.months-self.months,
                             days=other.days-self.days,
                             hours=other.hours-self.hours,
                             minutes=other.minutes-self.minutes,
                             seconds=other.seconds-self.seconds,
                             microseconds=other.microseconds-self.microseconds,
                             leapdays=other.leapdays or self.leapdays,
                             year=other.year or self.year,
                             month=other.month or self.month,
                             day=other.day or self.day,
                             weekday=other.weekday or self.weekday,
                             hour=other.hour or self.hour,
                             minute=other.minute or self.minute,
                             second=other.second or self.second,
                             microsecond=other.second or self.microsecond)

    def __neg__(self):
        return relativedelta(years=-self.years,
                             months=-self.months,
                             days=-self.days,
                             hours=-self.hours,
                             minutes=-self.minutes,
                             seconds=-self.seconds,
                             microseconds=-self.microseconds,
                             leapdays=self.leapdays,
                             year=self.year,
                             month=self.month,
                             day=self.day,
                             weekday=self.weekday,
                             hour=self.hour,
                             minute=self.minute,
                             second=self.second,
                             microsecond=self.microsecond)

    def __nonzero__(self):
        return not (not self.years and
                    not self.months and
                    not self.days and
                    not self.hours and
                    not self.minutes and
                    not self.seconds and
                    not self.microseconds and
                    not self.leapdays and
                    self.year is None and
                    self.month is None and
                    self.day is None and
                    self.weekday is None and
                    self.hour is None and
                    self.minute is None and
                    self.second is None and
                    self.microsecond is None)

    def __mul__(self, other):
        f = float(other)
        return relativedelta(years=self.years*f,
                             months=self.months*f,
                             days=self.days*f,
                             hours=self.hours*f,
                             minutes=self.minutes*f,
                             seconds=self.seconds*f,
                             microseconds=self.microseconds*f,
                             leapdays=self.leapdays,
                             year=self.year,
                             month=self.month,
                             day=self.day,
                             weekday=self.weekday,
                             hour=self.hour,
                             minute=self.minute,
                             second=self.second,
                             microsecond=self.microsecond)

    def __eq__(self, other):
        if not isinstance(other, relativedelta):
            return False
        if self.weekday or other.weekday:
            if not self.weekday or not other.weekday:
                return False
            if self.weekday.weekday != other.weekday.weekday:
                return False
            n1, n2 = self.weekday.n, other.weekday.n
            if n1 != n2 and not ((not n1 or n1 == 1) and (not n2 or n2 == 1)):
                return False
        return (self.years == other.years and
                self.months == other.months and
                self.days == other.days and
                self.hours == other.hours and
                self.minutes == other.minutes and
                self.seconds == other.seconds and
                self.leapdays == other.leapdays and
                self.year == other.year and
                self.month == other.month and
                self.day == other.day and
                self.hour == other.hour and
                self.minute == other.minute and
                self.second == other.second and
                self.microsecond == other.microsecond)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __div__(self, other):
        return self.__mul__(1/float(other))

    def __repr__(self):
        l = []
        for attr in ["years", "months", "days", "leapdays",
                     "hours", "minutes", "seconds", "microseconds"]:
            value = getattr(self, attr)
            if value:
                l.append("%s=%+d" % (attr, value))
        for attr in ["year", "month", "day", "weekday",
                     "hour", "minute", "second", "microsecond"]:
            value = getattr(self, attr)
            if value is not None:
                l.append("%s=%s" % (attr, `value`))
        return "%s(%s)" % (self.__class__.__name__, ", ".join(l))

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = rrule
"""
Copyright (c) 2003-2010  Gustavo Niemeyer <gustavo@niemeyer.net>

This module offers extensions to the standard python 2.3+
datetime module.
"""
__author__ = "Gustavo Niemeyer <gustavo@niemeyer.net>"
__license__ = "PSF License"

import itertools
import datetime
import calendar
import thread
import sys

__all__ = ["rrule", "rruleset", "rrulestr",
           "YEARLY", "MONTHLY", "WEEKLY", "DAILY",
           "HOURLY", "MINUTELY", "SECONDLY",
           "MO", "TU", "WE", "TH", "FR", "SA", "SU"]

# Every mask is 7 days longer to handle cross-year weekly periods.
M366MASK = tuple([1]*31+[2]*29+[3]*31+[4]*30+[5]*31+[6]*30+
                 [7]*31+[8]*31+[9]*30+[10]*31+[11]*30+[12]*31+[1]*7)
M365MASK = list(M366MASK)
M29, M30, M31 = range(1,30), range(1,31), range(1,32)
MDAY366MASK = tuple(M31+M29+M31+M30+M31+M30+M31+M31+M30+M31+M30+M31+M31[:7])
MDAY365MASK = list(MDAY366MASK)
M29, M30, M31 = range(-29,0), range(-30,0), range(-31,0)
NMDAY366MASK = tuple(M31+M29+M31+M30+M31+M30+M31+M31+M30+M31+M30+M31+M31[:7])
NMDAY365MASK = list(NMDAY366MASK)
M366RANGE = (0,31,60,91,121,152,182,213,244,274,305,335,366)
M365RANGE = (0,31,59,90,120,151,181,212,243,273,304,334,365)
WDAYMASK = [0,1,2,3,4,5,6]*55
del M29, M30, M31, M365MASK[59], MDAY365MASK[59], NMDAY365MASK[31]
MDAY365MASK = tuple(MDAY365MASK)
M365MASK = tuple(M365MASK)

(YEARLY,
 MONTHLY,
 WEEKLY,
 DAILY,
 HOURLY,
 MINUTELY,
 SECONDLY) = range(7)

# Imported on demand.
easter = None
parser = None

class weekday(object):
    __slots__ = ["weekday", "n"]

    def __init__(self, weekday, n=None):
        if n == 0:
            raise ValueError, "Can't create weekday with n == 0"
        self.weekday = weekday
        self.n = n

    def __call__(self, n):
        if n == self.n:
            return self
        else:
            return self.__class__(self.weekday, n)

    def __eq__(self, other):
        try:
            if self.weekday != other.weekday or self.n != other.n:
                return False
        except AttributeError:
            return False
        return True

    def __repr__(self):
        s = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")[self.weekday]
        if not self.n:
            return s
        else:
            return "%s(%+d)" % (s, self.n)

MO, TU, WE, TH, FR, SA, SU = weekdays = tuple([weekday(x) for x in range(7)])

class rrulebase:
    def __init__(self, cache=False):
        if cache:
            self._cache = []
            self._cache_lock = thread.allocate_lock()
            self._cache_gen  = self._iter()
            self._cache_complete = False
        else:
            self._cache = None
            self._cache_complete = False
        self._len = None

    def __iter__(self):
        if self._cache_complete:
            return iter(self._cache)
        elif self._cache is None:
            return self._iter()
        else:
            return self._iter_cached()

    def _iter_cached(self):
        i = 0
        gen = self._cache_gen
        cache = self._cache
        acquire = self._cache_lock.acquire
        release = self._cache_lock.release
        while gen:
            if i == len(cache):
                acquire()
                if self._cache_complete:
                    break
                try:
                    for j in range(10):
                        cache.append(gen.next())
                except StopIteration:
                    self._cache_gen = gen = None
                    self._cache_complete = True
                    break
                release()
            yield cache[i]
            i += 1
        while i < self._len:
            yield cache[i]
            i += 1

    def __getitem__(self, item):
        if self._cache_complete:
            return self._cache[item]
        elif isinstance(item, slice):
            if item.step and item.step < 0:
                return list(iter(self))[item]
            else:
                return list(itertools.islice(self,
                                             item.start or 0,
                                             item.stop or sys.maxint,
                                             item.step or 1))
        elif item >= 0:
            gen = iter(self)
            try:
                for i in range(item+1):
                    res = gen.next()
            except StopIteration:
                raise IndexError
            return res
        else:
            return list(iter(self))[item]

    def __contains__(self, item):
        if self._cache_complete:
            return item in self._cache
        else:
            for i in self:
                if i == item:
                    return True
                elif i > item:
                    return False
        return False

    # __len__() introduces a large performance penality.
    def count(self):
        if self._len is None:
            for x in self: pass
        return self._len

    def before(self, dt, inc=False):
        if self._cache_complete:
            gen = self._cache
        else:
            gen = self
        last = None
        if inc:
            for i in gen:
                if i > dt:
                    break
                last = i
        else:
            for i in gen:
                if i >= dt:
                    break
                last = i
        return last

    def after(self, dt, inc=False):
        if self._cache_complete:
            gen = self._cache
        else:
            gen = self
        if inc:
            for i in gen:
                if i >= dt:
                    return i
        else:
            for i in gen:
                if i > dt:
                    return i
        return None

    def between(self, after, before, inc=False):
        if self._cache_complete:
            gen = self._cache
        else:
            gen = self
        started = False
        l = []
        if inc:
            for i in gen:
                if i > before:
                    break
                elif not started:
                    if i >= after:
                        started = True
                        l.append(i)
                else:
                    l.append(i)
        else:
            for i in gen:
                if i >= before:
                    break
                elif not started:
                    if i > after:
                        started = True
                        l.append(i)
                else:
                    l.append(i)
        return l

class rrule(rrulebase):
    def __init__(self, freq, dtstart=None,
                 interval=1, wkst=None, count=None, until=None, bysetpos=None,
                 bymonth=None, bymonthday=None, byyearday=None, byeaster=None,
                 byweekno=None, byweekday=None,
                 byhour=None, byminute=None, bysecond=None,
                 cache=False):
        rrulebase.__init__(self, cache)
        global easter
        if not dtstart:
            dtstart = datetime.datetime.now().replace(microsecond=0)
        elif not isinstance(dtstart, datetime.datetime):
            dtstart = datetime.datetime.fromordinal(dtstart.toordinal())
        else:
            dtstart = dtstart.replace(microsecond=0)
        self._dtstart = dtstart
        self._tzinfo = dtstart.tzinfo
        self._freq = freq
        self._interval = interval
        self._count = count
        if until and not isinstance(until, datetime.datetime):
            until = datetime.datetime.fromordinal(until.toordinal())
        self._until = until
        if wkst is None:
            self._wkst = calendar.firstweekday()
        elif type(wkst) is int:
            self._wkst = wkst
        else:
            self._wkst = wkst.weekday
        if bysetpos is None:
            self._bysetpos = None
        elif type(bysetpos) is int:
            if bysetpos == 0 or not (-366 <= bysetpos <= 366):
                raise ValueError("bysetpos must be between 1 and 366, "
                                 "or between -366 and -1")
            self._bysetpos = (bysetpos,)
        else:
            self._bysetpos = tuple(bysetpos)
            for pos in self._bysetpos:
                if pos == 0 or not (-366 <= pos <= 366):
                    raise ValueError("bysetpos must be between 1 and 366, "
                                     "or between -366 and -1")
        if not (byweekno or byyearday or bymonthday or
                byweekday is not None or byeaster is not None):
            if freq == YEARLY:
                if not bymonth:
                    bymonth = dtstart.month
                bymonthday = dtstart.day
            elif freq == MONTHLY:
                bymonthday = dtstart.day
            elif freq == WEEKLY:
                byweekday = dtstart.weekday()
        # bymonth
        if not bymonth:
            self._bymonth = None
        elif type(bymonth) is int:
            self._bymonth = (bymonth,)
        else:
            self._bymonth = tuple(bymonth)
        # byyearday
        if not byyearday:
            self._byyearday = None
        elif type(byyearday) is int:
            self._byyearday = (byyearday,)
        else:
            self._byyearday = tuple(byyearday)
        # byeaster
        if byeaster is not None:
            if not easter:
                from dateutil import easter
            if type(byeaster) is int:
                self._byeaster = (byeaster,)
            else:
                self._byeaster = tuple(byeaster)
        else:
            self._byeaster = None
        # bymonthay
        if not bymonthday:
            self._bymonthday = ()
            self._bynmonthday = ()
        elif type(bymonthday) is int:
            if bymonthday < 0:
                self._bynmonthday = (bymonthday,)
                self._bymonthday = ()
            else:
                self._bymonthday = (bymonthday,)
                self._bynmonthday = ()
        else:
            self._bymonthday = tuple([x for x in bymonthday if x > 0])
            self._bynmonthday = tuple([x for x in bymonthday if x < 0])
        # byweekno
        if byweekno is None:
            self._byweekno = None
        elif type(byweekno) is int:
            self._byweekno = (byweekno,)
        else:
            self._byweekno = tuple(byweekno)
        # byweekday / bynweekday
        if byweekday is None:
            self._byweekday = None
            self._bynweekday = None
        elif type(byweekday) is int:
            self._byweekday = (byweekday,)
            self._bynweekday = None
        elif hasattr(byweekday, "n"):
            if not byweekday.n or freq > MONTHLY:
                self._byweekday = (byweekday.weekday,)
                self._bynweekday = None
            else:
                self._bynweekday = ((byweekday.weekday, byweekday.n),)
                self._byweekday = None
        else:
            self._byweekday = []
            self._bynweekday = []
            for wday in byweekday:
                if type(wday) is int:
                    self._byweekday.append(wday)
                elif not wday.n or freq > MONTHLY:
                    self._byweekday.append(wday.weekday)
                else:
                    self._bynweekday.append((wday.weekday, wday.n))
            self._byweekday = tuple(self._byweekday)
            self._bynweekday = tuple(self._bynweekday)
            if not self._byweekday:
                self._byweekday = None
            elif not self._bynweekday:
                self._bynweekday = None
        # byhour
        if byhour is None:
            if freq < HOURLY:
                self._byhour = (dtstart.hour,)
            else:
                self._byhour = None
        elif type(byhour) is int:
            self._byhour = (byhour,)
        else:
            self._byhour = tuple(byhour)
        # byminute
        if byminute is None:
            if freq < MINUTELY:
                self._byminute = (dtstart.minute,)
            else:
                self._byminute = None
        elif type(byminute) is int:
            self._byminute = (byminute,)
        else:
            self._byminute = tuple(byminute)
        # bysecond
        if bysecond is None:
            if freq < SECONDLY:
                self._bysecond = (dtstart.second,)
            else:
                self._bysecond = None
        elif type(bysecond) is int:
            self._bysecond = (bysecond,)
        else:
            self._bysecond = tuple(bysecond)

        if self._freq >= HOURLY:
            self._timeset = None
        else:
            self._timeset = []
            for hour in self._byhour:
                for minute in self._byminute:
                    for second in self._bysecond:
                        self._timeset.append(
                                datetime.time(hour, minute, second,
                                                    tzinfo=self._tzinfo))
            self._timeset.sort()
            self._timeset = tuple(self._timeset)

    def _iter(self):
        year, month, day, hour, minute, second, weekday, yearday, _ = \
            self._dtstart.timetuple()

        # Some local variables to speed things up a bit
        freq = self._freq
        interval = self._interval
        wkst = self._wkst
        until = self._until
        bymonth = self._bymonth
        byweekno = self._byweekno
        byyearday = self._byyearday
        byweekday = self._byweekday
        byeaster = self._byeaster
        bymonthday = self._bymonthday
        bynmonthday = self._bynmonthday
        bysetpos = self._bysetpos
        byhour = self._byhour
        byminute = self._byminute
        bysecond = self._bysecond

        ii = _iterinfo(self)
        ii.rebuild(year, month)

        getdayset = {YEARLY:ii.ydayset,
                     MONTHLY:ii.mdayset,
                     WEEKLY:ii.wdayset,
                     DAILY:ii.ddayset,
                     HOURLY:ii.ddayset,
                     MINUTELY:ii.ddayset,
                     SECONDLY:ii.ddayset}[freq]
        
        if freq < HOURLY:
            timeset = self._timeset
        else:
            gettimeset = {HOURLY:ii.htimeset,
                          MINUTELY:ii.mtimeset,
                          SECONDLY:ii.stimeset}[freq]
            if ((freq >= HOURLY and
                 self._byhour and hour not in self._byhour) or
                (freq >= MINUTELY and
                 self._byminute and minute not in self._byminute) or
                (freq >= SECONDLY and
                 self._bysecond and second not in self._bysecond)):
                timeset = ()
            else:
                timeset = gettimeset(hour, minute, second)

        total = 0
        count = self._count
        while True:
            # Get dayset with the right frequency
            dayset, start, end = getdayset(year, month, day)

            # Do the "hard" work ;-)
            filtered = False
            for i in dayset[start:end]:
                if ((bymonth and ii.mmask[i] not in bymonth) or
                    (byweekno and not ii.wnomask[i]) or
                    (byweekday and ii.wdaymask[i] not in byweekday) or
                    (ii.nwdaymask and not ii.nwdaymask[i]) or
                    (byeaster and not ii.eastermask[i]) or
                    ((bymonthday or bynmonthday) and
                     ii.mdaymask[i] not in bymonthday and
                     ii.nmdaymask[i] not in bynmonthday) or
                    (byyearday and
                     ((i < ii.yearlen and i+1 not in byyearday
                                      and -ii.yearlen+i not in byyearday) or
                      (i >= ii.yearlen and i+1-ii.yearlen not in byyearday
                                       and -ii.nextyearlen+i-ii.yearlen
                                           not in byyearday)))):
                    dayset[i] = None
                    filtered = True

            # Output results
            if bysetpos and timeset:
                poslist = []
                for pos in bysetpos:
                    if pos < 0:
                        daypos, timepos = divmod(pos, len(timeset))
                    else:
                        daypos, timepos = divmod(pos-1, len(timeset))
                    try:
                        i = [x for x in dayset[start:end]
                                if x is not None][daypos]
                        time = timeset[timepos]
                    except IndexError:
                        pass
                    else:
                        date = datetime.date.fromordinal(ii.yearordinal+i)
                        res = datetime.datetime.combine(date, time)
                        if res not in poslist:
                            poslist.append(res)
                poslist.sort()
                for res in poslist:
                    if until and res > until:
                        self._len = total
                        return
                    elif res >= self._dtstart:
                        total += 1
                        yield res
                        if count:
                            count -= 1
                            if not count:
                                self._len = total
                                return
            else:
                for i in dayset[start:end]:
                    if i is not None:
                        date = datetime.date.fromordinal(ii.yearordinal+i)
                        for time in timeset:
                            res = datetime.datetime.combine(date, time)
                            if until and res > until:
                                self._len = total
                                return
                            elif res >= self._dtstart:
                                total += 1
                                yield res
                                if count:
                                    count -= 1
                                    if not count:
                                        self._len = total
                                        return

            # Handle frequency and interval
            fixday = False
            if freq == YEARLY:
                year += interval
                if year > datetime.MAXYEAR:
                    self._len = total
                    return
                ii.rebuild(year, month)
            elif freq == MONTHLY:
                month += interval
                if month > 12:
                    div, mod = divmod(month, 12)
                    month = mod
                    year += div
                    if month == 0:
                        month = 12
                        year -= 1
                    if year > datetime.MAXYEAR:
                        self._len = total
                        return
                ii.rebuild(year, month)
            elif freq == WEEKLY:
                if wkst > weekday:
                    day += -(weekday+1+(6-wkst))+self._interval*7
                else:
                    day += -(weekday-wkst)+self._interval*7
                weekday = wkst
                fixday = True
            elif freq == DAILY:
                day += interval
                fixday = True
            elif freq == HOURLY:
                if filtered:
                    # Jump to one iteration before next day
                    hour += ((23-hour)//interval)*interval
                while True:
                    hour += interval
                    div, mod = divmod(hour, 24)
                    if div:
                        hour = mod
                        day += div
                        fixday = True
                    if not byhour or hour in byhour:
                        break
                timeset = gettimeset(hour, minute, second)
            elif freq == MINUTELY:
                if filtered:
                    # Jump to one iteration before next day
                    minute += ((1439-(hour*60+minute))//interval)*interval
                while True:
                    minute += interval
                    div, mod = divmod(minute, 60)
                    if div:
                        minute = mod
                        hour += div
                        div, mod = divmod(hour, 24)
                        if div:
                            hour = mod
                            day += div
                            fixday = True
                            filtered = False
                    if ((not byhour or hour in byhour) and
                        (not byminute or minute in byminute)):
                        break
                timeset = gettimeset(hour, minute, second)
            elif freq == SECONDLY:
                if filtered:
                    # Jump to one iteration before next day
                    second += (((86399-(hour*3600+minute*60+second))
                                //interval)*interval)
                while True:
                    second += self._interval
                    div, mod = divmod(second, 60)
                    if div:
                        second = mod
                        minute += div
                        div, mod = divmod(minute, 60)
                        if div:
                            minute = mod
                            hour += div
                            div, mod = divmod(hour, 24)
                            if div:
                                hour = mod
                                day += div
                                fixday = True
                    if ((not byhour or hour in byhour) and
                        (not byminute or minute in byminute) and
                        (not bysecond or second in bysecond)):
                        break
                timeset = gettimeset(hour, minute, second)

            if fixday and day > 28:
                daysinmonth = calendar.monthrange(year, month)[1]
                if day > daysinmonth:
                    while day > daysinmonth:
                        day -= daysinmonth
                        month += 1
                        if month == 13:
                            month = 1
                            year += 1
                            if year > datetime.MAXYEAR:
                                self._len = total
                                return
                        daysinmonth = calendar.monthrange(year, month)[1]
                    ii.rebuild(year, month)

class _iterinfo(object):
    __slots__ = ["rrule", "lastyear", "lastmonth",
                 "yearlen", "nextyearlen", "yearordinal", "yearweekday",
                 "mmask", "mrange", "mdaymask", "nmdaymask",
                 "wdaymask", "wnomask", "nwdaymask", "eastermask"]

    def __init__(self, rrule):
        for attr in self.__slots__:
            setattr(self, attr, None)
        self.rrule = rrule

    def rebuild(self, year, month):
        # Every mask is 7 days longer to handle cross-year weekly periods.
        rr = self.rrule
        if year != self.lastyear:
            self.yearlen = 365+calendar.isleap(year)
            self.nextyearlen = 365+calendar.isleap(year+1)
            firstyday = datetime.date(year, 1, 1)
            self.yearordinal = firstyday.toordinal()
            self.yearweekday = firstyday.weekday()

            wday = datetime.date(year, 1, 1).weekday()
            if self.yearlen == 365:
                self.mmask = M365MASK
                self.mdaymask = MDAY365MASK
                self.nmdaymask = NMDAY365MASK
                self.wdaymask = WDAYMASK[wday:]
                self.mrange = M365RANGE
            else:
                self.mmask = M366MASK
                self.mdaymask = MDAY366MASK
                self.nmdaymask = NMDAY366MASK
                self.wdaymask = WDAYMASK[wday:]
                self.mrange = M366RANGE

            if not rr._byweekno:
                self.wnomask = None
            else:
                self.wnomask = [0]*(self.yearlen+7)
                #no1wkst = firstwkst = self.wdaymask.index(rr._wkst)
                no1wkst = firstwkst = (7-self.yearweekday+rr._wkst)%7
                if no1wkst >= 4:
                    no1wkst = 0
                    # Number of days in the year, plus the days we got
                    # from last year.
                    wyearlen = self.yearlen+(self.yearweekday-rr._wkst)%7
                else:
                    # Number of days in the year, minus the days we
                    # left in last year.
                    wyearlen = self.yearlen-no1wkst
                div, mod = divmod(wyearlen, 7)
                numweeks = div+mod//4
                for n in rr._byweekno:
                    if n < 0:
                        n += numweeks+1
                    if not (0 < n <= numweeks):
                        continue
                    if n > 1:
                        i = no1wkst+(n-1)*7
                        if no1wkst != firstwkst:
                            i -= 7-firstwkst
                    else:
                        i = no1wkst
                    for j in range(7):
                        self.wnomask[i] = 1
                        i += 1
                        if self.wdaymask[i] == rr._wkst:
                            break
                if 1 in rr._byweekno:
                    # Check week number 1 of next year as well
                    # TODO: Check -numweeks for next year.
                    i = no1wkst+numweeks*7
                    if no1wkst != firstwkst:
                        i -= 7-firstwkst
                    if i < self.yearlen:
                        # If week starts in next year, we
                        # don't care about it.
                        for j in range(7):
                            self.wnomask[i] = 1
                            i += 1
                            if self.wdaymask[i] == rr._wkst:
                                break
                if no1wkst:
                    # Check last week number of last year as
                    # well. If no1wkst is 0, either the year
                    # started on week start, or week number 1
                    # got days from last year, so there are no
                    # days from last year's last week number in
                    # this year.
                    if -1 not in rr._byweekno:
                        lyearweekday = datetime.date(year-1,1,1).weekday()
                        lno1wkst = (7-lyearweekday+rr._wkst)%7
                        lyearlen = 365+calendar.isleap(year-1)
                        if lno1wkst >= 4:
                            lno1wkst = 0
                            lnumweeks = 52+(lyearlen+
                                           (lyearweekday-rr._wkst)%7)%7//4
                        else:
                            lnumweeks = 52+(self.yearlen-no1wkst)%7//4
                    else:
                        lnumweeks = -1
                    if lnumweeks in rr._byweekno:
                        for i in range(no1wkst):
                            self.wnomask[i] = 1

        if (rr._bynweekday and
            (month != self.lastmonth or year != self.lastyear)):
            ranges = []
            if rr._freq == YEARLY:
                if rr._bymonth:
                    for month in rr._bymonth:
                        ranges.append(self.mrange[month-1:month+1])
                else:
                    ranges = [(0, self.yearlen)]
            elif rr._freq == MONTHLY:
                ranges = [self.mrange[month-1:month+1]]
            if ranges:
                # Weekly frequency won't get here, so we may not
                # care about cross-year weekly periods.
                self.nwdaymask = [0]*self.yearlen
                for first, last in ranges:
                    last -= 1
                    for wday, n in rr._bynweekday:
                        if n < 0:
                            i = last+(n+1)*7
                            i -= (self.wdaymask[i]-wday)%7
                        else:
                            i = first+(n-1)*7
                            i += (7-self.wdaymask[i]+wday)%7
                        if first <= i <= last:
                            self.nwdaymask[i] = 1

        if rr._byeaster:
            self.eastermask = [0]*(self.yearlen+7)
            eyday = easter.easter(year).toordinal()-self.yearordinal
            for offset in rr._byeaster:
                self.eastermask[eyday+offset] = 1

        self.lastyear = year
        self.lastmonth = month

    def ydayset(self, year, month, day):
        return range(self.yearlen), 0, self.yearlen

    def mdayset(self, year, month, day):
        set = [None]*self.yearlen
        start, end = self.mrange[month-1:month+1]
        for i in range(start, end):
            set[i] = i
        return set, start, end

    def wdayset(self, year, month, day):
        # We need to handle cross-year weeks here.
        set = [None]*(self.yearlen+7)
        i = datetime.date(year, month, day).toordinal()-self.yearordinal
        start = i
        for j in range(7):
            set[i] = i
            i += 1
            #if (not (0 <= i < self.yearlen) or
            #    self.wdaymask[i] == self.rrule._wkst):
            # This will cross the year boundary, if necessary.
            if self.wdaymask[i] == self.rrule._wkst:
                break
        return set, start, i

    def ddayset(self, year, month, day):
        set = [None]*self.yearlen
        i = datetime.date(year, month, day).toordinal()-self.yearordinal
        set[i] = i
        return set, i, i+1

    def htimeset(self, hour, minute, second):
        set = []
        rr = self.rrule
        for minute in rr._byminute:
            for second in rr._bysecond:
                set.append(datetime.time(hour, minute, second,
                                         tzinfo=rr._tzinfo))
        set.sort()
        return set

    def mtimeset(self, hour, minute, second):
        set = []
        rr = self.rrule
        for second in rr._bysecond:
            set.append(datetime.time(hour, minute, second, tzinfo=rr._tzinfo))
        set.sort()
        return set

    def stimeset(self, hour, minute, second):
        return (datetime.time(hour, minute, second,
                tzinfo=self.rrule._tzinfo),)


class rruleset(rrulebase):

    class _genitem:
        def __init__(self, genlist, gen):
            try:
                self.dt = gen()
                genlist.append(self)
            except StopIteration:
                pass
            self.genlist = genlist
            self.gen = gen

        def next(self):
            try:
                self.dt = self.gen()
            except StopIteration:
                self.genlist.remove(self)

        def __cmp__(self, other):
            return cmp(self.dt, other.dt)

    def __init__(self, cache=False):
        rrulebase.__init__(self, cache)
        self._rrule = []
        self._rdate = []
        self._exrule = []
        self._exdate = []

    def rrule(self, rrule):
        self._rrule.append(rrule)
    
    def rdate(self, rdate):
        self._rdate.append(rdate)

    def exrule(self, exrule):
        self._exrule.append(exrule)

    def exdate(self, exdate):
        self._exdate.append(exdate)

    def _iter(self):
        rlist = []
        self._rdate.sort()
        self._genitem(rlist, iter(self._rdate).next)
        for gen in [iter(x).next for x in self._rrule]:
            self._genitem(rlist, gen)
        rlist.sort()
        exlist = []
        self._exdate.sort()
        self._genitem(exlist, iter(self._exdate).next)
        for gen in [iter(x).next for x in self._exrule]:
            self._genitem(exlist, gen)
        exlist.sort()
        lastdt = None
        total = 0
        while rlist:
            ritem = rlist[0]
            if not lastdt or lastdt != ritem.dt:
                while exlist and exlist[0] < ritem:
                    exlist[0].next()
                    exlist.sort()
                if not exlist or ritem != exlist[0]:
                    total += 1
                    yield ritem.dt
                lastdt = ritem.dt
            ritem.next()
            rlist.sort()
        self._len = total

class _rrulestr:

    _freq_map = {"YEARLY": YEARLY,
                 "MONTHLY": MONTHLY,
                 "WEEKLY": WEEKLY,
                 "DAILY": DAILY,
                 "HOURLY": HOURLY,
                 "MINUTELY": MINUTELY,
                 "SECONDLY": SECONDLY}

    _weekday_map = {"MO":0,"TU":1,"WE":2,"TH":3,"FR":4,"SA":5,"SU":6}

    def _handle_int(self, rrkwargs, name, value, **kwargs):
        rrkwargs[name.lower()] = int(value)

    def _handle_int_list(self, rrkwargs, name, value, **kwargs):
        rrkwargs[name.lower()] = [int(x) for x in value.split(',')]

    _handle_INTERVAL   = _handle_int
    _handle_COUNT      = _handle_int
    _handle_BYSETPOS   = _handle_int_list
    _handle_BYMONTH    = _handle_int_list
    _handle_BYMONTHDAY = _handle_int_list
    _handle_BYYEARDAY  = _handle_int_list
    _handle_BYEASTER   = _handle_int_list
    _handle_BYWEEKNO   = _handle_int_list
    _handle_BYHOUR     = _handle_int_list
    _handle_BYMINUTE   = _handle_int_list
    _handle_BYSECOND   = _handle_int_list

    def _handle_FREQ(self, rrkwargs, name, value, **kwargs):
        rrkwargs["freq"] = self._freq_map[value]

    def _handle_UNTIL(self, rrkwargs, name, value, **kwargs):
        global parser
        if not parser:
            from dateutil import parser
        try:
            rrkwargs["until"] = parser.parse(value,
                                           ignoretz=kwargs.get("ignoretz"),
                                           tzinfos=kwargs.get("tzinfos"))
        except ValueError:
            raise ValueError, "invalid until date"

    def _handle_WKST(self, rrkwargs, name, value, **kwargs):
        rrkwargs["wkst"] = self._weekday_map[value]

    def _handle_BYWEEKDAY(self, rrkwargs, name, value, **kwarsg):
        l = []
        for wday in value.split(','):
            for i in range(len(wday)):
                if wday[i] not in '+-0123456789':
                    break
            n = wday[:i] or None
            w = wday[i:]
            if n: n = int(n)
            l.append(weekdays[self._weekday_map[w]](n))
        rrkwargs["byweekday"] = l

    _handle_BYDAY = _handle_BYWEEKDAY

    def _parse_rfc_rrule(self, line,
                         dtstart=None,
                         cache=False,
                         ignoretz=False,
                         tzinfos=None):
        if line.find(':') != -1:
            name, value = line.split(':')
            if name != "RRULE":
                raise ValueError, "unknown parameter name"
        else:
            value = line
        rrkwargs = {}
        for pair in value.split(';'):
            name, value = pair.split('=')
            name = name.upper()
            value = value.upper()
            try:
                getattr(self, "_handle_"+name)(rrkwargs, name, value,
                                               ignoretz=ignoretz,
                                               tzinfos=tzinfos)
            except AttributeError:
                raise ValueError, "unknown parameter '%s'" % name
            except (KeyError, ValueError):
                raise ValueError, "invalid '%s': %s" % (name, value)
        return rrule(dtstart=dtstart, cache=cache, **rrkwargs)

    def _parse_rfc(self, s,
                   dtstart=None,
                   cache=False,
                   unfold=False,
                   forceset=False,
                   compatible=False,
                   ignoretz=False,
                   tzinfos=None):
        global parser
        if compatible:
            forceset = True
            unfold = True
        s = s.upper()
        if not s.strip():
            raise ValueError, "empty string"
        if unfold:
            lines = s.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].rstrip()
                if not line:
                    del lines[i]
                elif i > 0 and line[0] == " ":
                    lines[i-1] += line[1:]
                    del lines[i]
                else:
                    i += 1
        else:
            lines = s.split()
        if (not forceset and len(lines) == 1 and
            (s.find(':') == -1 or s.startswith('RRULE:'))):
            return self._parse_rfc_rrule(lines[0], cache=cache,
                                         dtstart=dtstart, ignoretz=ignoretz,
                                         tzinfos=tzinfos)
        else:
            rrulevals = []
            rdatevals = []
            exrulevals = []
            exdatevals = []
            for line in lines:
                if not line:
                    continue
                if line.find(':') == -1:
                    name = "RRULE"
                    value = line
                else:
                    name, value = line.split(':', 1)
                parms = name.split(';')
                if not parms:
                    raise ValueError, "empty property name"
                name = parms[0]
                parms = parms[1:]
                if name == "RRULE":
                    for parm in parms:
                        raise ValueError, "unsupported RRULE parm: "+parm
                    rrulevals.append(value)
                elif name == "RDATE":
                    for parm in parms:
                        if parm != "VALUE=DATE-TIME":
                            raise ValueError, "unsupported RDATE parm: "+parm
                    rdatevals.append(value)
                elif name == "EXRULE":
                    for parm in parms:
                        raise ValueError, "unsupported EXRULE parm: "+parm
                    exrulevals.append(value)
                elif name == "EXDATE":
                    for parm in parms:
                        if parm != "VALUE=DATE-TIME":
                            raise ValueError, "unsupported RDATE parm: "+parm
                    exdatevals.append(value)
                elif name == "DTSTART":
                    for parm in parms:
                        raise ValueError, "unsupported DTSTART parm: "+parm
                    if not parser:
                        from dateutil import parser
                    dtstart = parser.parse(value, ignoretz=ignoretz,
                                           tzinfos=tzinfos)
                else:
                    raise ValueError, "unsupported property: "+name
            if (forceset or len(rrulevals) > 1 or
                rdatevals or exrulevals or exdatevals):
                if not parser and (rdatevals or exdatevals):
                    from dateutil import parser
                set = rruleset(cache=cache)
                for value in rrulevals:
                    set.rrule(self._parse_rfc_rrule(value, dtstart=dtstart,
                                                    ignoretz=ignoretz,
                                                    tzinfos=tzinfos))
                for value in rdatevals:
                    for datestr in value.split(','):
                        set.rdate(parser.parse(datestr,
                                               ignoretz=ignoretz,
                                               tzinfos=tzinfos))
                for value in exrulevals:
                    set.exrule(self._parse_rfc_rrule(value, dtstart=dtstart,
                                                     ignoretz=ignoretz,
                                                     tzinfos=tzinfos))
                for value in exdatevals:
                    for datestr in value.split(','):
                        set.exdate(parser.parse(datestr,
                                                ignoretz=ignoretz,
                                                tzinfos=tzinfos))
                if compatible and dtstart:
                    set.rdate(dtstart)
                return set
            else:
                return self._parse_rfc_rrule(rrulevals[0],
                                             dtstart=dtstart,
                                             cache=cache,
                                             ignoretz=ignoretz,
                                             tzinfos=tzinfos)

    def __call__(self, s, **kwargs):
        return self._parse_rfc(s, **kwargs)

rrulestr = _rrulestr()

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = tz
"""
Copyright (c) 2003-2007  Gustavo Niemeyer <gustavo@niemeyer.net>

This module offers extensions to the standard python 2.3+
datetime module.
"""
__author__ = "Gustavo Niemeyer <gustavo@niemeyer.net>"
__license__ = "PSF License"

import datetime
import struct
import time
import sys
import os

relativedelta = None
parser = None
rrule = None

__all__ = ["tzutc", "tzoffset", "tzlocal", "tzfile", "tzrange",
           "tzstr", "tzical", "tzwin", "tzwinlocal", "gettz"]

try:
    from dateutil.tzwin import tzwin, tzwinlocal
except (ImportError, OSError):
    tzwin, tzwinlocal = None, None

ZERO = datetime.timedelta(0)
EPOCHORDINAL = datetime.datetime.utcfromtimestamp(0).toordinal()

class tzutc(datetime.tzinfo):

    def utcoffset(self, dt):
        return ZERO
     
    def dst(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def __eq__(self, other):
        return (isinstance(other, tzutc) or
                (isinstance(other, tzoffset) and other._offset == ZERO))

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "%s()" % self.__class__.__name__

    __reduce__ = object.__reduce__

class tzoffset(datetime.tzinfo):

    def __init__(self, name, offset):
        self._name = name
        self._offset = datetime.timedelta(seconds=offset)

    def utcoffset(self, dt):
        return self._offset

    def dst(self, dt):
        return ZERO

    def tzname(self, dt):
        return self._name

    def __eq__(self, other):
        return (isinstance(other, tzoffset) and
                self._offset == other._offset)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "%s(%s, %s)" % (self.__class__.__name__,
                               `self._name`,
                               self._offset.days*86400+self._offset.seconds)

    __reduce__ = object.__reduce__

class tzlocal(datetime.tzinfo):

    _std_offset = datetime.timedelta(seconds=-time.timezone)
    if time.daylight:
        _dst_offset = datetime.timedelta(seconds=-time.altzone)
    else:
        _dst_offset = _std_offset

    def utcoffset(self, dt):
        if self._isdst(dt):
            return self._dst_offset
        else:
            return self._std_offset

    def dst(self, dt):
        if self._isdst(dt):
            return self._dst_offset-self._std_offset
        else:
            return ZERO

    def tzname(self, dt):
        return time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        # We can't use mktime here. It is unstable when deciding if
        # the hour near to a change is DST or not.
        # 
        # timestamp = time.mktime((dt.year, dt.month, dt.day, dt.hour,
        #                         dt.minute, dt.second, dt.weekday(), 0, -1))
        # return time.localtime(timestamp).tm_isdst
        #
        # The code above yields the following result:
        #
        #>>> import tz, datetime
        #>>> t = tz.tzlocal()
        #>>> datetime.datetime(2003,2,15,23,tzinfo=t).tzname()
        #'BRDT'
        #>>> datetime.datetime(2003,2,16,0,tzinfo=t).tzname()
        #'BRST'
        #>>> datetime.datetime(2003,2,15,23,tzinfo=t).tzname()
        #'BRST'
        #>>> datetime.datetime(2003,2,15,22,tzinfo=t).tzname()
        #'BRDT'
        #>>> datetime.datetime(2003,2,15,23,tzinfo=t).tzname()
        #'BRDT'
        #
        # Here is a more stable implementation:
        #
        timestamp = ((dt.toordinal() - EPOCHORDINAL) * 86400
                     + dt.hour * 3600
                     + dt.minute * 60
                     + dt.second)
        return time.localtime(timestamp+time.timezone).tm_isdst

    def __eq__(self, other):
        if not isinstance(other, tzlocal):
            return False
        return (self._std_offset == other._std_offset and
                self._dst_offset == other._dst_offset)
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "%s()" % self.__class__.__name__

    __reduce__ = object.__reduce__

class _ttinfo(object):
    __slots__ = ["offset", "delta", "isdst", "abbr", "isstd", "isgmt"]

    def __init__(self):
        for attr in self.__slots__:
            setattr(self, attr, None)

    def __repr__(self):
        l = []
        for attr in self.__slots__:
            value = getattr(self, attr)
            if value is not None:
                l.append("%s=%s" % (attr, `value`))
        return "%s(%s)" % (self.__class__.__name__, ", ".join(l))

    def __eq__(self, other):
        if not isinstance(other, _ttinfo):
            return False
        return (self.offset == other.offset and
                self.delta == other.delta and
                self.isdst == other.isdst and
                self.abbr == other.abbr and
                self.isstd == other.isstd and
                self.isgmt == other.isgmt)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __getstate__(self):
        state = {}
        for name in self.__slots__:
            state[name] = getattr(self, name, None)
        return state

    def __setstate__(self, state):
        for name in self.__slots__:
            if name in state:
                setattr(self, name, state[name])

class tzfile(datetime.tzinfo):

    # http://www.twinsun.com/tz/tz-link.htm
    # ftp://elsie.nci.nih.gov/pub/tz*.tar.gz
    
    def __init__(self, fileobj):
        if isinstance(fileobj, basestring):
            self._filename = fileobj
            fileobj = open(fileobj)
        elif hasattr(fileobj, "name"):
            self._filename = fileobj.name
        else:
            self._filename = `fileobj`

        # From tzfile(5):
        #
        # The time zone information files used by tzset(3)
        # begin with the magic characters "TZif" to identify
        # them as time zone information files, followed by
        # sixteen bytes reserved for future use, followed by
        # six four-byte values of type long, written in a
        # ``standard'' byte order (the high-order  byte
        # of the value is written first).

        if fileobj.read(4) != "TZif":
            raise ValueError, "magic not found"

        fileobj.read(16)

        (
         # The number of UTC/local indicators stored in the file.
         ttisgmtcnt,

         # The number of standard/wall indicators stored in the file.
         ttisstdcnt,
         
         # The number of leap seconds for which data is
         # stored in the file.
         leapcnt,

         # The number of "transition times" for which data
         # is stored in the file.
         timecnt,

         # The number of "local time types" for which data
         # is stored in the file (must not be zero).
         typecnt,

         # The  number  of  characters  of "time zone
         # abbreviation strings" stored in the file.
         charcnt,

        ) = struct.unpack(">6l", fileobj.read(24))

        # The above header is followed by tzh_timecnt four-byte
        # values  of  type long,  sorted  in ascending order.
        # These values are written in ``standard'' byte order.
        # Each is used as a transition time (as  returned  by
        # time(2)) at which the rules for computing local time
        # change.

        if timecnt:
            self._trans_list = struct.unpack(">%dl" % timecnt,
                                             fileobj.read(timecnt*4))
        else:
            self._trans_list = []

        # Next come tzh_timecnt one-byte values of type unsigned
        # char; each one tells which of the different types of
        # ``local time'' types described in the file is associated
        # with the same-indexed transition time. These values
        # serve as indices into an array of ttinfo structures that
        # appears next in the file.
        
        if timecnt:
            self._trans_idx = struct.unpack(">%dB" % timecnt,
                                            fileobj.read(timecnt))
        else:
            self._trans_idx = []
        
        # Each ttinfo structure is written as a four-byte value
        # for tt_gmtoff  of  type long,  in  a  standard  byte
        # order, followed  by a one-byte value for tt_isdst
        # and a one-byte  value  for  tt_abbrind.   In  each
        # structure, tt_gmtoff  gives  the  number  of
        # seconds to be added to UTC, tt_isdst tells whether
        # tm_isdst should be set by  localtime(3),  and
        # tt_abbrind serves  as an index into the array of
        # time zone abbreviation characters that follow the
        # ttinfo structure(s) in the file.

        ttinfo = []

        for i in range(typecnt):
            ttinfo.append(struct.unpack(">lbb", fileobj.read(6)))

        abbr = fileobj.read(charcnt)

        # Then there are tzh_leapcnt pairs of four-byte
        # values, written in  standard byte  order;  the
        # first  value  of  each pair gives the time (as
        # returned by time(2)) at which a leap second
        # occurs;  the  second  gives the  total  number of
        # leap seconds to be applied after the given time.
        # The pairs of values are sorted in ascending order
        # by time.

        # Not used, for now
        if leapcnt:
            leap = struct.unpack(">%dl" % (leapcnt*2),
                                 fileobj.read(leapcnt*8))

        # Then there are tzh_ttisstdcnt standard/wall
        # indicators, each stored as a one-byte value;
        # they tell whether the transition times associated
        # with local time types were specified as standard
        # time or wall clock time, and are used when
        # a time zone file is used in handling POSIX-style
        # time zone environment variables.

        if ttisstdcnt:
            isstd = struct.unpack(">%db" % ttisstdcnt,
                                  fileobj.read(ttisstdcnt))

        # Finally, there are tzh_ttisgmtcnt UTC/local
        # indicators, each stored as a one-byte value;
        # they tell whether the transition times associated
        # with local time types were specified as UTC or
        # local time, and are used when a time zone file
        # is used in handling POSIX-style time zone envi-
        # ronment variables.

        if ttisgmtcnt:
            isgmt = struct.unpack(">%db" % ttisgmtcnt,
                                  fileobj.read(ttisgmtcnt))

        # ** Everything has been read **

        # Build ttinfo list
        self._ttinfo_list = []
        for i in range(typecnt):
            gmtoff, isdst, abbrind =  ttinfo[i]
            # Round to full-minutes if that's not the case. Python's
            # datetime doesn't accept sub-minute timezones. Check
            # http://python.org/sf/1447945 for some information.
            gmtoff = (gmtoff+30)//60*60
            tti = _ttinfo()
            tti.offset = gmtoff
            tti.delta = datetime.timedelta(seconds=gmtoff)
            tti.isdst = isdst
            tti.abbr = abbr[abbrind:abbr.find('\x00', abbrind)]
            tti.isstd = (ttisstdcnt > i and isstd[i] != 0)
            tti.isgmt = (ttisgmtcnt > i and isgmt[i] != 0)
            self._ttinfo_list.append(tti)

        # Replace ttinfo indexes for ttinfo objects.
        trans_idx = []
        for idx in self._trans_idx:
            trans_idx.append(self._ttinfo_list[idx])
        self._trans_idx = tuple(trans_idx)

        # Set standard, dst, and before ttinfos. before will be
        # used when a given time is before any transitions,
        # and will be set to the first non-dst ttinfo, or to
        # the first dst, if all of them are dst.
        self._ttinfo_std = None
        self._ttinfo_dst = None
        self._ttinfo_before = None
        if self._ttinfo_list:
            if not self._trans_list:
                self._ttinfo_std = self._ttinfo_first = self._ttinfo_list[0]
            else:
                for i in range(timecnt-1,-1,-1):
                    tti = self._trans_idx[i]
                    if not self._ttinfo_std and not tti.isdst:
                        self._ttinfo_std = tti
                    elif not self._ttinfo_dst and tti.isdst:
                        self._ttinfo_dst = tti
                    if self._ttinfo_std and self._ttinfo_dst:
                        break
                else:
                    if self._ttinfo_dst and not self._ttinfo_std:
                        self._ttinfo_std = self._ttinfo_dst

                for tti in self._ttinfo_list:
                    if not tti.isdst:
                        self._ttinfo_before = tti
                        break
                else:
                    self._ttinfo_before = self._ttinfo_list[0]

        # Now fix transition times to become relative to wall time.
        #
        # I'm not sure about this. In my tests, the tz source file
        # is setup to wall time, and in the binary file isstd and
        # isgmt are off, so it should be in wall time. OTOH, it's
        # always in gmt time. Let me know if you have comments
        # about this.
        laststdoffset = 0
        self._trans_list = list(self._trans_list)
        for i in range(len(self._trans_list)):
            tti = self._trans_idx[i]
            if not tti.isdst:
                # This is std time.
                self._trans_list[i] += tti.offset
                laststdoffset = tti.offset
            else:
                # This is dst time. Convert to std.
                self._trans_list[i] += laststdoffset
        self._trans_list = tuple(self._trans_list)

    def _find_ttinfo(self, dt, laststd=0):
        timestamp = ((dt.toordinal() - EPOCHORDINAL) * 86400
                     + dt.hour * 3600
                     + dt.minute * 60
                     + dt.second)
        idx = 0
        for trans in self._trans_list:
            if timestamp < trans:
                break
            idx += 1
        else:
            return self._ttinfo_std
        if idx == 0:
            return self._ttinfo_before
        if laststd:
            while idx > 0:
                tti = self._trans_idx[idx-1]
                if not tti.isdst:
                    return tti
                idx -= 1
            else:
                return self._ttinfo_std
        else:
            return self._trans_idx[idx-1]

    def utcoffset(self, dt):
        if not self._ttinfo_std:
            return ZERO
        return self._find_ttinfo(dt).delta

    def dst(self, dt):
        if not self._ttinfo_dst:
            return ZERO
        tti = self._find_ttinfo(dt)
        if not tti.isdst:
            return ZERO

        # The documentation says that utcoffset()-dst() must
        # be constant for every dt.
        return tti.delta-self._find_ttinfo(dt, laststd=1).delta

        # An alternative for that would be:
        #
        # return self._ttinfo_dst.offset-self._ttinfo_std.offset
        #
        # However, this class stores historical changes in the
        # dst offset, so I belive that this wouldn't be the right
        # way to implement this.
        
    def tzname(self, dt):
        if not self._ttinfo_std:
            return None
        return self._find_ttinfo(dt).abbr

    def __eq__(self, other):
        if not isinstance(other, tzfile):
            return False
        return (self._trans_list == other._trans_list and
                self._trans_idx == other._trans_idx and
                self._ttinfo_list == other._ttinfo_list)

    def __ne__(self, other):
        return not self.__eq__(other)


    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, `self._filename`)

    def __reduce__(self):
        if not os.path.isfile(self._filename):
            raise ValueError, "Unpickable %s class" % self.__class__.__name__
        return (self.__class__, (self._filename,))

class tzrange(datetime.tzinfo):

    def __init__(self, stdabbr, stdoffset=None,
                 dstabbr=None, dstoffset=None,
                 start=None, end=None):
        global relativedelta
        if not relativedelta:
            from dateutil import relativedelta
        self._std_abbr = stdabbr
        self._dst_abbr = dstabbr
        if stdoffset is not None:
            self._std_offset = datetime.timedelta(seconds=stdoffset)
        else:
            self._std_offset = ZERO
        if dstoffset is not None:
            self._dst_offset = datetime.timedelta(seconds=dstoffset)
        elif dstabbr and stdoffset is not None:
            self._dst_offset = self._std_offset+datetime.timedelta(hours=+1)
        else:
            self._dst_offset = ZERO
        if dstabbr and start is None:
            self._start_delta = relativedelta.relativedelta(
                    hours=+2, month=4, day=1, weekday=relativedelta.SU(+1))
        else:
            self._start_delta = start
        if dstabbr and end is None:
            self._end_delta = relativedelta.relativedelta(
                    hours=+1, month=10, day=31, weekday=relativedelta.SU(-1))
        else:
            self._end_delta = end

    def utcoffset(self, dt):
        if self._isdst(dt):
            return self._dst_offset
        else:
            return self._std_offset

    def dst(self, dt):
        if self._isdst(dt):
            return self._dst_offset-self._std_offset
        else:
            return ZERO

    def tzname(self, dt):
        if self._isdst(dt):
            return self._dst_abbr
        else:
            return self._std_abbr

    def _isdst(self, dt):
        if not self._start_delta:
            return False
        year = datetime.datetime(dt.year,1,1)
        start = year+self._start_delta
        end = year+self._end_delta
        dt = dt.replace(tzinfo=None)
        if start < end:
            return dt >= start and dt < end
        else:
            return dt >= start or dt < end

    def __eq__(self, other):
        if not isinstance(other, tzrange):
            return False
        return (self._std_abbr == other._std_abbr and
                self._dst_abbr == other._dst_abbr and
                self._std_offset == other._std_offset and
                self._dst_offset == other._dst_offset and
                self._start_delta == other._start_delta and
                self._end_delta == other._end_delta)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "%s(...)" % self.__class__.__name__

    __reduce__ = object.__reduce__

class tzstr(tzrange):
    
    def __init__(self, s):
        global parser
        if not parser:
            from dateutil import parser
        self._s = s

        res = parser._parsetz(s)
        if res is None:
            raise ValueError, "unknown string format"

        # Here we break the compatibility with the TZ variable handling.
        # GMT-3 actually *means* the timezone -3.
        if res.stdabbr in ("GMT", "UTC"):
            res.stdoffset *= -1

        # We must initialize it first, since _delta() needs
        # _std_offset and _dst_offset set. Use False in start/end
        # to avoid building it two times.
        tzrange.__init__(self, res.stdabbr, res.stdoffset,
                         res.dstabbr, res.dstoffset,
                         start=False, end=False)

        if not res.dstabbr:
            self._start_delta = None
            self._end_delta = None
        else:
            self._start_delta = self._delta(res.start)
            if self._start_delta:
                self._end_delta = self._delta(res.end, isend=1)

    def _delta(self, x, isend=0):
        kwargs = {}
        if x.month is not None:
            kwargs["month"] = x.month
            if x.weekday is not None:
                kwargs["weekday"] = relativedelta.weekday(x.weekday, x.week)
                if x.week > 0:
                    kwargs["day"] = 1
                else:
                    kwargs["day"] = 31
            elif x.day:
                kwargs["day"] = x.day
        elif x.yday is not None:
            kwargs["yearday"] = x.yday
        elif x.jyday is not None:
            kwargs["nlyearday"] = x.jyday
        if not kwargs:
            # Default is to start on first sunday of april, and end
            # on last sunday of october.
            if not isend:
                kwargs["month"] = 4
                kwargs["day"] = 1
                kwargs["weekday"] = relativedelta.SU(+1)
            else:
                kwargs["month"] = 10
                kwargs["day"] = 31
                kwargs["weekday"] = relativedelta.SU(-1)
        if x.time is not None:
            kwargs["seconds"] = x.time
        else:
            # Default is 2AM.
            kwargs["seconds"] = 7200
        if isend:
            # Convert to standard time, to follow the documented way
            # of working with the extra hour. See the documentation
            # of the tzinfo class.
            delta = self._dst_offset-self._std_offset
            kwargs["seconds"] -= delta.seconds+delta.days*86400
        return relativedelta.relativedelta(**kwargs)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, `self._s`)

class _tzicalvtzcomp:
    def __init__(self, tzoffsetfrom, tzoffsetto, isdst,
                       tzname=None, rrule=None):
        self.tzoffsetfrom = datetime.timedelta(seconds=tzoffsetfrom)
        self.tzoffsetto = datetime.timedelta(seconds=tzoffsetto)
        self.tzoffsetdiff = self.tzoffsetto-self.tzoffsetfrom
        self.isdst = isdst
        self.tzname = tzname
        self.rrule = rrule

class _tzicalvtz(datetime.tzinfo):
    def __init__(self, tzid, comps=[]):
        self._tzid = tzid
        self._comps = comps
        self._cachedate = []
        self._cachecomp = []

    def _find_comp(self, dt):
        if len(self._comps) == 1:
            return self._comps[0]
        dt = dt.replace(tzinfo=None)
        try:
            return self._cachecomp[self._cachedate.index(dt)]
        except ValueError:
            pass
        lastcomp = None
        lastcompdt = None
        for comp in self._comps:
            if not comp.isdst:
                # Handle the extra hour in DST -> STD
                compdt = comp.rrule.before(dt-comp.tzoffsetdiff, inc=True)
            else:
                compdt = comp.rrule.before(dt, inc=True)
            if compdt and (not lastcompdt or lastcompdt < compdt):
                lastcompdt = compdt
                lastcomp = comp
        if not lastcomp:
            # RFC says nothing about what to do when a given
            # time is before the first onset date. We'll look for the
            # first standard component, or the first component, if
            # none is found.
            for comp in self._comps:
                if not comp.isdst:
                    lastcomp = comp
                    break
            else:
                lastcomp = comp[0]
        self._cachedate.insert(0, dt)
        self._cachecomp.insert(0, lastcomp)
        if len(self._cachedate) > 10:
            self._cachedate.pop()
            self._cachecomp.pop()
        return lastcomp

    def utcoffset(self, dt):
        return self._find_comp(dt).tzoffsetto

    def dst(self, dt):
        comp = self._find_comp(dt)
        if comp.isdst:
            return comp.tzoffsetdiff
        else:
            return ZERO

    def tzname(self, dt):
        return self._find_comp(dt).tzname

    def __repr__(self):
        return "<tzicalvtz %s>" % `self._tzid`

    __reduce__ = object.__reduce__

class tzical:
    def __init__(self, fileobj):
        global rrule
        if not rrule:
            from dateutil import rrule

        if isinstance(fileobj, basestring):
            self._s = fileobj
            fileobj = open(fileobj)
        elif hasattr(fileobj, "name"):
            self._s = fileobj.name
        else:
            self._s = `fileobj`

        self._vtz = {}

        self._parse_rfc(fileobj.read())

    def keys(self):
        return self._vtz.keys()

    def get(self, tzid=None):
        if tzid is None:
            keys = self._vtz.keys()
            if len(keys) == 0:
                raise ValueError, "no timezones defined"
            elif len(keys) > 1:
                raise ValueError, "more than one timezone available"
            tzid = keys[0]
        return self._vtz.get(tzid)

    def _parse_offset(self, s):
        s = s.strip()
        if not s:
            raise ValueError, "empty offset"
        if s[0] in ('+', '-'):
            signal = (-1,+1)[s[0]=='+']
            s = s[1:]
        else:
            signal = +1
        if len(s) == 4:
            return (int(s[:2])*3600+int(s[2:])*60)*signal
        elif len(s) == 6:
            return (int(s[:2])*3600+int(s[2:4])*60+int(s[4:]))*signal
        else:
            raise ValueError, "invalid offset: "+s

    def _parse_rfc(self, s):
        lines = s.splitlines()
        if not lines:
            raise ValueError, "empty string"

        # Unfold
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            if not line:
                del lines[i]
            elif i > 0 and line[0] == " ":
                lines[i-1] += line[1:]
                del lines[i]
            else:
                i += 1

        tzid = None
        comps = []
        invtz = False
        comptype = None
        for line in lines:
            if not line:
                continue
            name, value = line.split(':', 1)
            parms = name.split(';')
            if not parms:
                raise ValueError, "empty property name"
            name = parms[0].upper()
            parms = parms[1:]
            if invtz:
                if name == "BEGIN":
                    if value in ("STANDARD", "DAYLIGHT"):
                        # Process component
                        pass
                    else:
                        raise ValueError, "unknown component: "+value
                    comptype = value
                    founddtstart = False
                    tzoffsetfrom = None
                    tzoffsetto = None
                    rrulelines = []
                    tzname = None
                elif name == "END":
                    if value == "VTIMEZONE":
                        if comptype:
                            raise ValueError, \
                                  "component not closed: "+comptype
                        if not tzid:
                            raise ValueError, \
                                  "mandatory TZID not found"
                        if not comps:
                            raise ValueError, \
                                  "at least one component is needed"
                        # Process vtimezone
                        self._vtz[tzid] = _tzicalvtz(tzid, comps)
                        invtz = False
                    elif value == comptype:
                        if not founddtstart:
                            raise ValueError, \
                                  "mandatory DTSTART not found"
                        if tzoffsetfrom is None:
                            raise ValueError, \
                                  "mandatory TZOFFSETFROM not found"
                        if tzoffsetto is None:
                            raise ValueError, \
                                  "mandatory TZOFFSETFROM not found"
                        # Process component
                        rr = None
                        if rrulelines:
                            rr = rrule.rrulestr("\n".join(rrulelines),
                                                compatible=True,
                                                ignoretz=True,
                                                cache=True)
                        comp = _tzicalvtzcomp(tzoffsetfrom, tzoffsetto,
                                              (comptype == "DAYLIGHT"),
                                              tzname, rr)
                        comps.append(comp)
                        comptype = None
                    else:
                        raise ValueError, \
                              "invalid component end: "+value
                elif comptype:
                    if name == "DTSTART":
                        rrulelines.append(line)
                        founddtstart = True
                    elif name in ("RRULE", "RDATE", "EXRULE", "EXDATE"):
                        rrulelines.append(line)
                    elif name == "TZOFFSETFROM":
                        if parms:
                            raise ValueError, \
                                  "unsupported %s parm: %s "%(name, parms[0])
                        tzoffsetfrom = self._parse_offset(value)
                    elif name == "TZOFFSETTO":
                        if parms:
                            raise ValueError, \
                                  "unsupported TZOFFSETTO parm: "+parms[0]
                        tzoffsetto = self._parse_offset(value)
                    elif name == "TZNAME":
                        if parms:
                            raise ValueError, \
                                  "unsupported TZNAME parm: "+parms[0]
                        tzname = value
                    elif name == "COMMENT":
                        pass
                    else:
                        raise ValueError, "unsupported property: "+name
                else:
                    if name == "TZID":
                        if parms:
                            raise ValueError, \
                                  "unsupported TZID parm: "+parms[0]
                        tzid = value
                    elif name in ("TZURL", "LAST-MODIFIED", "COMMENT"):
                        pass
                    else:
                        raise ValueError, "unsupported property: "+name
            elif name == "BEGIN" and value == "VTIMEZONE":
                tzid = None
                comps = []
                invtz = True

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, `self._s`)

if sys.platform != "win32":
    TZFILES = ["/etc/localtime", "localtime"]
    TZPATHS = ["/usr/share/zoneinfo", "/usr/lib/zoneinfo", "/etc/zoneinfo"]
else:
    TZFILES = []
    TZPATHS = []

def gettz(name=None):
    tz = None
    if not name:
        try:
            name = os.environ["TZ"]
        except KeyError:
            pass
    if name is None or name == ":":
        for filepath in TZFILES:
            if not os.path.isabs(filepath):
                filename = filepath
                for path in TZPATHS:
                    filepath = os.path.join(path, filename)
                    if os.path.isfile(filepath):
                        break
                else:
                    continue
            if os.path.isfile(filepath):
                try:
                    tz = tzfile(filepath)
                    break
                except (IOError, OSError, ValueError):
                    pass
        else:
            tz = tzlocal()
    else:
        if name.startswith(":"):
            name = name[:-1]
        if os.path.isabs(name):
            if os.path.isfile(name):
                tz = tzfile(name)
            else:
                tz = None
        else:
            for path in TZPATHS:
                filepath = os.path.join(path, name)
                if not os.path.isfile(filepath):
                    filepath = filepath.replace(' ','_')
                    if not os.path.isfile(filepath):
                        continue
                try:
                    tz = tzfile(filepath)
                    break
                except (IOError, OSError, ValueError):
                    pass
            else:
                tz = None
                if tzwin:
                    try:
                        tz = tzwin(name)
                    except OSError:
                        pass
                if not tz:
                    from dateutil.zoneinfo import gettz
                    tz = gettz(name)
                if not tz:
                    for c in name:
                        # name must have at least one offset to be a tzstr
                        if c in "0123456789":
                            try:
                                tz = tzstr(name)
                            except ValueError:
                                pass
                            break
                    else:
                        if name in ("GMT", "UTC"):
                            tz = tzutc()
                        elif name in time.tzname:
                            tz = tzlocal()
    return tz

# vim:ts=4:sw=4:et

########NEW FILE########
__FILENAME__ = tzwin
# This code was originally contributed by Jeffrey Harris.
import datetime
import struct
import _winreg

__author__ = "Jeffrey Harris & Gustavo Niemeyer <gustavo@niemeyer.net>"

__all__ = ["tzwin", "tzwinlocal"]

ONEWEEK = datetime.timedelta(7)

TZKEYNAMENT = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Time Zones"
TZKEYNAME9X = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Time Zones"
TZLOCALKEYNAME = r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation"

def _settzkeyname():
    global TZKEYNAME
    handle = _winreg.ConnectRegistry(None, _winreg.HKEY_LOCAL_MACHINE)
    try:
        _winreg.OpenKey(handle, TZKEYNAMENT).Close()
        TZKEYNAME = TZKEYNAMENT
    except WindowsError:
        TZKEYNAME = TZKEYNAME9X
    handle.Close()

_settzkeyname()

class tzwinbase(datetime.tzinfo):
    """tzinfo class based on win32's timezones available in the registry."""

    def utcoffset(self, dt):
        if self._isdst(dt):
            return datetime.timedelta(minutes=self._dstoffset)
        else:
            return datetime.timedelta(minutes=self._stdoffset)

    def dst(self, dt):
        if self._isdst(dt):
            minutes = self._dstoffset - self._stdoffset
            return datetime.timedelta(minutes=minutes)
        else:
            return datetime.timedelta(0)
        
    def tzname(self, dt):
        if self._isdst(dt):
            return self._dstname
        else:
            return self._stdname

    def list():
        """Return a list of all time zones known to the system."""
        handle = _winreg.ConnectRegistry(None, _winreg.HKEY_LOCAL_MACHINE)
        tzkey = _winreg.OpenKey(handle, TZKEYNAME)
        result = [_winreg.EnumKey(tzkey, i)
                  for i in range(_winreg.QueryInfoKey(tzkey)[0])]
        tzkey.Close()
        handle.Close()
        return result
    list = staticmethod(list)

    def display(self):
        return self._display
    
    def _isdst(self, dt):
        dston = picknthweekday(dt.year, self._dstmonth, self._dstdayofweek,
                               self._dsthour, self._dstminute,
                               self._dstweeknumber)
        dstoff = picknthweekday(dt.year, self._stdmonth, self._stddayofweek,
                                self._stdhour, self._stdminute,
                                self._stdweeknumber)
        if dston < dstoff:
            return dston <= dt.replace(tzinfo=None) < dstoff
        else:
            return not dstoff <= dt.replace(tzinfo=None) < dston


class tzwin(tzwinbase):

    def __init__(self, name):
        self._name = name

        handle = _winreg.ConnectRegistry(None, _winreg.HKEY_LOCAL_MACHINE)
        tzkey = _winreg.OpenKey(handle, "%s\%s" % (TZKEYNAME, name))
        keydict = valuestodict(tzkey)
        tzkey.Close()
        handle.Close()

        self._stdname = keydict["Std"].encode("iso-8859-1")
        self._dstname = keydict["Dlt"].encode("iso-8859-1")

        self._display = keydict["Display"]
        
        # See http://ww_winreg.jsiinc.com/SUBA/tip0300/rh0398.htm
        tup = struct.unpack("=3l16h", keydict["TZI"])
        self._stdoffset = -tup[0]-tup[1]         # Bias + StandardBias * -1
        self._dstoffset = self._stdoffset-tup[2] # + DaylightBias * -1
        
        (self._stdmonth,
         self._stddayofweek,  # Sunday = 0
         self._stdweeknumber, # Last = 5
         self._stdhour,
         self._stdminute) = tup[4:9]

        (self._dstmonth,
         self._dstdayofweek,  # Sunday = 0
         self._dstweeknumber, # Last = 5
         self._dsthour,
         self._dstminute) = tup[12:17]

    def __repr__(self):
        return "tzwin(%s)" % repr(self._name)

    def __reduce__(self):
        return (self.__class__, (self._name,))


class tzwinlocal(tzwinbase):
    
    def __init__(self):

        handle = _winreg.ConnectRegistry(None, _winreg.HKEY_LOCAL_MACHINE)

        tzlocalkey = _winreg.OpenKey(handle, TZLOCALKEYNAME)
        keydict = valuestodict(tzlocalkey)
        tzlocalkey.Close()

        self._stdname = keydict["StandardName"].encode("iso-8859-1")
        self._dstname = keydict["DaylightName"].encode("iso-8859-1")

        try:
            tzkey = _winreg.OpenKey(handle, "%s\%s"%(TZKEYNAME, self._stdname))
            _keydict = valuestodict(tzkey)
            self._display = _keydict["Display"]
            tzkey.Close()
        except OSError:
            self._display = None

        handle.Close()
        
        self._stdoffset = -keydict["Bias"]-keydict["StandardBias"]
        self._dstoffset = self._stdoffset-keydict["DaylightBias"]


        # See http://ww_winreg.jsiinc.com/SUBA/tip0300/rh0398.htm
        tup = struct.unpack("=8h", keydict["StandardStart"])

        (self._stdmonth,
         self._stddayofweek,  # Sunday = 0
         self._stdweeknumber, # Last = 5
         self._stdhour,
         self._stdminute) = tup[1:6]

        tup = struct.unpack("=8h", keydict["DaylightStart"])

        (self._dstmonth,
         self._dstdayofweek,  # Sunday = 0
         self._dstweeknumber, # Last = 5
         self._dsthour,
         self._dstminute) = tup[1:6]

    def __reduce__(self):
        return (self.__class__, ())

def picknthweekday(year, month, dayofweek, hour, minute, whichweek):
    """dayofweek == 0 means Sunday, whichweek 5 means last instance"""
    first = datetime.datetime(year, month, 1, hour, minute)
    weekdayone = first.replace(day=((dayofweek-first.isoweekday())%7+1))
    for n in xrange(whichweek):
        dt = weekdayone+(whichweek-n)*ONEWEEK
        if dt.month == month:
            return dt

def valuestodict(key):
    """Convert a registry key's values to a dictionary."""
    dict = {}
    size = _winreg.QueryInfoKey(key)[1]
    for i in range(size):
        data = _winreg.EnumValue(key, i)
        dict[data[0]] = data[1]
    return dict

########NEW FILE########
__FILENAME__ = delicious-html
#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
#
# This is SELFICIOUS by Yuuta
# UPDATED: 2010-12-24 15:06:39

import hashlib
import BeautifulSoup
import datetime
from importers import BaseImporter

class DeliciousLocalHTMLImporter(BaseImporter):
    """
    Imports bookmarks from an HTML file saved from delicious. To get this kind of
    files, visit <a
    href="https://secure.delicious.com/settings/bookmarks/export">
    https://secure.delicious.com/settings/bookmarks/export
    </a> &mdash;make sure to check "include my tags" and "include my notes"
    """
    service_name = 'delicious-html'
    service_verbose_name = "Local HTML bookmarks file saved from delicious"
    form = """
        <p>
        <label for="htmlfile" class="gauche">Upload your HTML file: </label>
        <input id="htmlfile" type="file" name="htmlfile" />
        </p> 
        """
    def __init__(self, tornado_handler):
        try:
            uploaded_file = tornado_handler.request.files['htmlfile'][0]
            self.data = uploaded_file['body']
            self.success = True
        except:
            self.success = False
            self.error = 'fetch'
        super(DeliciousLocalHTMLImporter, self).__init__(tornado_handler)

    def posts(self):
        if self.success:
            posts = []
            soup = BeautifulSoup.BeautifulSoup(self.data)
            anchors = soup.findAll("a")
            h = hashlib.sha1()
            for a in anchors:
                h.update(a['href'])
                if a.parent.nextSibling and a.parent.nextSibling.name  == 'dd':
                    text = unicode(a.parent.nextSibling.string)
                else:
                    text = ''
                posts.append({
                    'hash':h.hexdigest(),
                    'url':a['href'],
                    'title':unicode(a.string),
                    'description':text,
                    'tags':unicode(a['tags']).split(','),
                    'time':datetime.datetime.fromtimestamp(float(a['add_date']))
                })
            return posts
        else:
            return []

########NEW FILE########
__FILENAME__ = delicious-v1
#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
#
# This is SELFICIOUS by Yuuta
# UPDATED: 2010-12-23 18:54:07

import urllib2
import base64
import hashlib
from xml.dom import minidom
import dateutil.parser
from importers import BaseImporter

class DeliciousV1Importer(BaseImporter):
    """
    A Delicious posts importer for old accounts i.e. Not tied with Yahoo
    accounts - Using the user's username and password.
    """
    service_name = 'delicious-v1'
    service_verbose_name = "Old Delicious Account"
    form = """
        <p>
            <label for="username">Delicious Username</label>
            <input name="username" class="text" type="text" id="username"/>
        </p>
        <p>
            <label for="password">Delicious Password</label>
            <input name="password" class="text" type="password" id="password"/>
        </p>
        """

    def __init__(self, tornado_handler):
        self.url = "https://api.del.icio.us/v1/posts/all"
        self.domain = "https://api.del.icio.us/"
        self.user = tornado_handler.get_argument("username", "")
        self.password = tornado_handler.get_argument("password", "")
        super(DeliciousV1Importer, self).__init__(tornado_handler)

    def fetch_posts(self):
        try:
            passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
            passman.add_password(None, self.domain, self.user, self.password)
            authhandler = urllib2.HTTPBasicAuthHandler(passman)
            opener = urllib2.build_opener(authhandler)
            urllib2.install_opener(opener)
            self.data = urllib2.urlopen(self.url).read()
            self.success = True
        except:
            self.success = False
            self.error = "fetch"
            self.data = None

    def posts(self):
        self.fetch_posts()
        if self.success:
            posts = []
            dom = minidom.parseString(self.data)
            h = hashlib.sha1()
            for node in dom.getElementsByTagName('post'):
                h.update(node.getAttribute('href'))
                posts.append({
                    'hash':h.hexdigest(),
                    'url':node.getAttribute('href'),
                    'title':node.getAttribute('description'),
                    'description':node.getAttribute('extended'),
                    'tags':node.getAttribute('tag').split(' '),
                    'time':dateutil.parser.parse(node.getAttribute('time'))
                })
            return posts
        else:
            return []

########NEW FILE########
__FILENAME__ = delicious-xml
#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
#
# This is SELFICIOUS by Yuuta
# UPDATED: 2010-12-23 20:53:41

import urllib2
import base64
import hashlib
from xml.dom import minidom
import dateutil.parser
from importers import BaseImporter

class DeliciousLocalXMLImporter(BaseImporter):
    """
    Imports bookmarks from an XML file saved from delicious. To get this kind of
    files, visit <a
    href="https://api.del.icio.us/v1/posts/all">http://api.del.icio.us/v1/posts/all
    </a> (if you're an old delicious user) 
    """
    service_name = 'delicious-xml'
    service_verbose_name = "Local XML file saved from delicious"
    form = """
        <p>
        <label for="xmlfile" class="gauche">Upload your XML file: </label>
        <input id="xmlfile" type="file" name="xmlfile" />
        </p> 
        """

    def __init__(self, tornado_handler):
        try:
            uploaded_file = tornado_handler.request.files['xmlfile'][0]
            self.data = uploaded_file['body']
            self.success = True
        except:
            self.success = False
            self.error = 'fetch'
        super(DeliciousLocalXMLImporter, self).__init__(tornado_handler)

    def posts(self):
        if self.success:
            posts = []
            dom = minidom.parseString(self.data)
            h = hashlib.sha1()
            for node in dom.getElementsByTagName('post'):
                h.update(node.getAttribute('href'))
                posts.append({
                    'hash':h.hexdigest(),
                    'url':node.getAttribute('href'),
                    'title':node.getAttribute('description'),
                    'description':node.getAttribute('extended'),
                    'tags':node.getAttribute('tag').split(' '),
                    'time':dateutil.parser.parse(node.getAttribute('time'))
                })
            return posts
        else:
            return []

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
# -*- coding: utf-8 -*- 
#
# This is SELFICIOUS by Yuuta
# UPDATED: 2010-12-23 19:08:39

import logging
import hashlib
import functools
import os
import os.path
import re
import tornado.web
import tornado.wsgi
import unicodedata
import wsgiref.handlers

from google.appengine.api import users
from google.appengine.ext import db

from utils import memoize, unmemoize
import importers
import settings


class Entry(db.Model):
    """
    A single entry.
    service: the service's name from which the entry comes -may be empty
    hash: a hash (sha1) of the url
    """
    service = db.StringProperty(required=False)
    hash = db.StringProperty(required=True)
    title = db.StringProperty(required=True)
    description = db.TextProperty()
    url = db.LinkProperty(required=True)
    time = db.DateTimeProperty(auto_now_add=True)
    tags = db.ListProperty(db.Category)


def administrator(method):
    """Decorate with this method to restrict to site admins."""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            if self.request.method == "GET":
                self.redirect(self.get_login_url())
                return
            raise web.HTTPError(403)
        elif not self.current_user.administrator:
            if self.request.method == "GET":
                self.redirect("/")
                return
            raise web.HTTPError(403)
        else:
            return method(self, *args, **kwargs)
    return wrapper


class BaseHandler(tornado.web.RequestHandler):
    """Implements Google Accounts authentication methods."""
    def get_current_user(self):
        user = users.get_current_user()
        if user: user.administrator = users.is_current_user_admin()
        return user

    def get_login_url(self):
        return users.create_login_url(self.request.uri)

    def render_string(self, template_name, **kwargs):
        return tornado.web.RequestHandler.render_string(
            self, template_name, users=users, **kwargs)

    def slugify(self, title):
        slug = unicodedata.normalize("NFKD", title).encode("ascii", "ignore")
        slug = re.sub(r"[^\w]+", " ", slug)
        return "-".join(slug.lower().strip().split())

    @memoize('/entries/recent')
    def get_recent_entries(self):
        entries = db.Query(Entry).order("-time").fetch(limit=5)
        return entries

    @memoize('/entries/home')
    def get_home_entries(self):
        entries = db.Query(Entry).order("-time").fetch(limit=10)
        return entries

    @memoize('/entries/archive')
    def get_archive_entries(self):
        entries = db.Query(Entry).order("-time")
        return entries

    @memoize('/entries/tag/%s')
    def get_tagged_entries(self, tag):
        entries = db.Query(Entry).filter("tags =", tag).order("-time")
        return entries

    def free_cache(self, tags=[]):
        """Use utils.unmemoize to delete stuff from memcache"""
        unmemoize([ "/entries/recent", "/entries/home", "/entries/archive"])
        unmemoize(["/entries/tag/%s" % tag for tag in tags])


class HomeHandler(BaseHandler):
    def get(self):
        entries = self.get_home_entries()
        import_success = self.get_argument('imported', None)
        error = self.get_argument('error', "")
        self.render("home.html", entries=entries, import_success=import_success,
                error_message=importers.messages[error])


class ArchiveHandler(BaseHandler):
    def get(self):
        entries = self.get_archive_entries()
        self.render("archive.html", entries=entries)


class TagHandler(BaseHandler):
    def get(self, tag):
        entries = self.get_tagged_entries(tag)
        self.render("tag.html", tag=tag, entries=entries)


class BookmarkHandler(BaseHandler):
    @administrator
    def get(self):
        key = self.get_argument("key", None)
        entry = Entry.get(key) if key else None
        self.render("form.html", entry=entry)

    @administrator
    def post(self):
        key = self.get_argument("key", None)
        if key:
            entry = Entry.get(key)
            entry.title = self.get_argument("title", "")
            entry.description = self.get_argument("description", "")
            entry.url = self.get_argument("url", "")
        else:
            h = hashlib.sha1()
            h.update(self.get_argument("url", ""))
            entry = Entry(
                service="internal",
                title=self.get_argument("title", ""),
                description=self.get_argument("description", ""),
                url=self.get_argument("url", ""),
                hash=h.hexdigest(),
            )
        tags = set([self.slugify(unicode(tag)) for tag in
            self.get_argument("tags", "").split(",")])
        tags = [db.Category(tag) for tag in tags if tag]
        entry.tags = tags
        entry.put()
        self.free_cache(tags=entry.tags)
        self.redirect("/")


class ImportHandler(BaseHandler):
    @administrator
    def get(self):
        services = importers.list()
        self.render("import.html", services=services)

    @administrator
    def post(self):
        service = self.get_argument("service", "")
        try:
            service_class = importers.new(service)
            importer = service_class(self)
            posts = importer.posts()
            if importer.success:
                self._save_posts(posts, service)
                self.redirect("/?imported=1")
            else:
                self.redirect("/?imported=0&error=%s"%importer.error)
        except NotImplementedError:
            self.redirect("/?imported=0&error=unknown_service")

    def _save_posts(self, posts, service):
        for post in posts:
            entry = Entry(
                service=service,
                hash=post['hash'],
                url=post['url'],
                title=post['title'],
                description=post['description'],
                time=post['time'],
                tags = [db.Category(tag) for tag in post['tags'] if tag ]
            )
            entry.put()
        self.free_cache()
        

class DeleteHandler(BaseHandler):
    @administrator
    def get(self):
        key = self.get_argument("key")
        try:
            entry = Entry.get(key)
            self.free_cache(tags=entry.tags)
        except db.BadKeyError:
            raise tornado.web.HTTPError(404)
        entry.delete()
        self.redirect("/")


class EntryModule(tornado.web.UIModule):
    def render(self, entry):
        return self.render_string("modules/entry.html", entry=entry)


settings = {
    "site_title": getattr(settings, 'SITE_TITLE', u'My Bookmarks'),
    "template_path": os.path.join(os.path.dirname(__file__), "templates"),
    "ui_modules": {"Entry": EntryModule,},
    "xsrf_cookies": True,
    "debug": os.environ.get("SERVER_SOFTWARE", "").startswith("Development/"),
}

application = tornado.wsgi.WSGIApplication([
    (r"/", HomeHandler),
    (r"/archive", ArchiveHandler),
    (r"/tag/([^/]+)/?", TagHandler),
    (r"/post", BookmarkHandler),
    (r"/import", ImportHandler),
    (r"/index", tornado.web.RedirectHandler, {"url": "/archive"}),
    (r"/delete", DeleteHandler),
], **settings)


def main():
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = settings.sample
#!/usr/bin/env python 
# -*- coding: utf-8 -*- 

"""
Copy this file to settings.py and change the variable below to customize your
bookmarking site.
"""

SITE_TITLE = "My SELFICIOUS!"


########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python 
# -*- coding: utf-8 -*- 
#
# This is SELFICIOUS by Yuuta
# UPDATED: 2010-12-22 22:28:40

import logging
from google.appengine.api import memcache

def keygen(format, *args, **kwargs):
    """generates a key from args and kwargs using format"""
    allargs = args+tuple(kwargs[key] for key in sorted(kwargs.keys()))
    key = format % allargs[0:format.count('%')]
    return key

def memoize(keyformat, time=600, cache_null=False):
    """Decorator to memoize functions using memcache."""
    def decorator(fxn):
        def wrapper(self, *args, **kwargs):
            key = keygen(keyformat, *args, **kwargs)
            data = memcache.get(key)
            if data is not None:
                logging.info('From memcache: %s' % key)
                return data
            data = fxn(self, *args, **kwargs)
            if data or cache_null:
                memcache.set(key, data, time)
            return data
        return wrapper
    return decorator

def unmemoize(keys_list):
    memcache.delete_multi(keys_list)

########NEW FILE########
