__FILENAME__ = build
#!/usr/bin/env python

import sys
sys.path.append("tools")
import mergejs

have_compressor = None
try:
    import jsmin
    have_compressor = "jsmin"
except ImportError:
    try:
        import minimize
        have_compressor = "minimize"
    except Exception, E:
        print E
        pass

sourceDirectory = "../src"
configFilename = "library.cfg"
outputFilename = "pretty-json-min.js"

if len(sys.argv) > 1:
    configFilename = sys.argv[1]
    extension = configFilename[-4:]

    if extension  != ".cfg":
        configFilename = sys.argv[1] + ".cfg"

if len(sys.argv) > 2:
    outputFilename = sys.argv[2]

print "Merging libraries."
merged = mergejs.run(sourceDirectory, None, configFilename)
if have_compressor == "jsmin":
    print "Compressing using jsmin."
    minimized = jsmin.jsmin(merged)
elif have_compressor == "minimize":
    print "Compressing using minimize."
    minimized = minimize.minimize(merged)
else: # fallback
    print "Not compressing."
    minimized = merged 
print "Adding license file."
minimized = file("license.txt").read() + minimized

print "Writing to %s." % outputFilename
file(outputFilename, "w").write(minimized)

print "Done."

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
well-formed part of it. The BeautifulSoup class 

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

"""
from __future__ import generators

__author__ = "Leonard Richardson (leonardr@segfault.org)"
__version__ = "3.0.4"
__copyright__ = "Copyright (c) 2004-2007 Leonard Richardson"
__license__ = "PSF"

from sgmllib import SGMLParser, SGMLParseError
import codecs
import types
import re
import sgmllib
try:
  from htmlentitydefs import name2codepoint
except ImportError:
  name2codepoint = {}

#This hack makes Beautiful Soup able to parse XML with namespaces
sgmllib.tagfind = re.compile('[a-zA-Z][-_.:a-zA-Z0-9]*')

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

    def findNext(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the first item that matches the given criteria and
        appears after this Tag in the document."""
        return self._findOne(self.findAllNext, name, attrs, text, **kwargs)

    def findAllNext(self, name=None, attrs={}, text=None, limit=None,
                    **kwargs):
        """Returns all items that match the given criteria and appear
        before after Tag in the document."""
        return self._findAll(name, attrs, text, limit, self.nextGenerator)

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

    def __getattr__(self, attr):
        """text.string gives you text. This is for backwards
        compatibility for Navigable*String, but for CData* it lets you
        get the string without the CData wrapper."""
        if attr == 'string':
            return self
        else:
            raise AttributeError, "'%s' object has no attribute '%s'" % (self.__class__.__name__, attr)

    def __unicode__(self):
        return self.__str__(None)

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

    XML_SPECIAL_CHARS_TO_ENTITIES = { "'" : "squot",
                                      '"' : "quote",
                                      "&" : "amp",
                                      "<" : "lt",
                                      ">" : "gt" }

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
                        # This can't happen naturally, but it can happen
                        # if you modify an attribute value after parsing.
                        if "'" in val:
                            val = val.replace("'", "&squot;")

                    # Now we're okay w/r/t quotes. But the attribute
                    # value might also contain angle brackets, or
                    # ampersands that aren't part of entities. We need
                    # to escape those to XML entities too.
                    val = re.sub("([<>]|&(?![^\s]+;))",
                                 lambda x: "&" + self.XML_SPECIAL_CHARS_TO_ENTITIES[x.group(0)[0]] + ";",
                                 val)
                                      
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
    
    #Utility methods

    def append(self, tag):
        """Appends the given tag to the contents of this tag."""
        self.contents.append(tag)

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
        return isinstance(s, unicode) or isintance(s, basestring) 
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

    XML_ENTITY_LIST = {}
    for i in Tag.XML_SPECIAL_CHARS_TO_ENTITIES.values():
        XML_ENTITY_LIST[i] = True 

    SELF_CLOSING_TAGS = {}
    NESTABLE_TAGS = {}
    RESET_NESTING_TAGS = {}
    QUOTE_TAGS = {}

    MARKUP_MASSAGE = [(re.compile('(<[^<>]*)/>'),
                       lambda x: x.group(1) + ' />'),
                      (re.compile('<!\s+([^<>]*)>'),
                       lambda x: '<!' + x.group(1) + '>')
                      ]

    ROOT_TAG_NAME = u'[document]'

    HTML_ENTITIES = "html"
    XML_ENTITIES = "xml"

    def __init__(self, markup="", parseOnlyThese=None, fromEncoding=None,
                 markupMassage=True, smartQuotesTo=XML_ENTITIES,
                 convertEntities=None, selfClosingTags=None):
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
        if self.convertEntities:
            # It doesn't make sense to convert encoded characters to
            # entities even while you're converting entities to Unicode.
            # Just convert it all to Unicode.
            self.smartQuotesTo = None
        self.instanceSelfClosingTags = buildTagMap(None, selfClosingTags)
        SGMLParser.__init__(self)
            
        if hasattr(markup, 'read'):        # It's a file-type object.
            markup = markup.read()
        self.markup = markup
        self.markupMassage = markupMassage
        try:
            self._feed()
        except StopParsing:
            pass
        self.markup = None                 # The markup can now be GCed
        
    def _feed(self, inDocumentEncoding=None):
        # Convert the document to Unicode.
        markup = self.markup
        if isinstance(markup, unicode):
            if not hasattr(self, 'originalEncoding'):
                self.originalEncoding = None
        else:
            dammit = UnicodeDammit\
                     (markup, [self.fromEncoding, inDocumentEncoding],
                      smartQuotesTo=self.smartQuotesTo)
            markup = dammit.unicode
            self.originalEncoding = dammit.originalEncoding
        if markup:
            if self.markupMassage:
                if not isList(self.markupMassage):
                    self.markupMassage = self.MARKUP_MASSAGE            
                for fix, m in self.markupMassage:
                    markup = fix.sub(m, markup)
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
            self.currentTag.append(tag)
        self.tagStack.append(tag)
        self.currentTag = self.tagStack[-1]

    def endData(self, containerClass=NavigableString):
        if self.currentData:
            currentData = ''.join(self.currentData)
            if not currentData.strip():
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
         <p>Foo<b>Bar<p> should pop to 'p', not 'b'.
         <p>Foo<table>Bar<p> should pop to 'table', not 'p'.
         <p>Foo<table><tr>Bar<p> should pop to 'tr', not 'p'.
         <p>Foo<b>Bar<p> should pop to 'p', not 'b'.

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
            text = "xml version='1.0' encoding='%SOUP-ENCODING%'"
        self._toStringSubclass(text, ProcessingInstruction)

    def handle_comment(self, text):
        "Handle comments as Comment objects."
        self._toStringSubclass(text, Comment)

    def handle_charref(self, ref):
        "Handle character references as data."
        if self.convertEntities in [self.HTML_ENTITIES,
                                    self.XML_ENTITIES]:
            data = unichr(int(ref))
        else:
            data = '&#%s;' % ref
        self.handle_data(data)

    def handle_entityref(self, ref):
        """Handle entity references as data, possibly converting known
        HTML entity references to the corresponding Unicode
        characters."""
        data = None
        if self.convertEntities == self.HTML_ENTITIES or \
               (self.convertEntities == self.XML_ENTITIES and \
                self.XML_ENTITY_LIST.get(ref)):
            try:
                data = unichr(name2codepoint[ref])
            except KeyError:
                pass
        if not data:
            data = '&%s;' % ref
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
        BeautifulStoneSoup.__init__(self, *args, **kwargs)

    SELF_CLOSING_TAGS = buildTagMap(None,
                                    ['br' , 'hr', 'input', 'img', 'meta',
                                    'spacer', 'link', 'frame', 'base'])

    QUOTE_TAGS = {'script': None}
    
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
    CHARSET_RE = re.compile("((^|;)\s*charset=)([^;]*)")

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
                if getattr(self, 'declaredHTMLEncoding') or \
                       (self.originalEncoding == self.fromEncoding):
                    # This is our second pass through the document, or
                    # else an encoding was specified explicitly and it
                    # worked. Rewrite the meta tag.
                    newAttr = self.CHARSET_RE.sub\
                              (lambda(match):match.group(1) +
                               "%SOUP-ENCODING%", value)
                    attrs[contentTypeIndex] = (attrs[contentTypeIndex][0],
                                               newAttr)
                    tagNeedsEncodingSubstitution = True
                else:
                    # This is our first pass through the document.
                    # Go through it again with the new information.
                    newCharset = match.group(3)
                    if newCharset and newCharset != self.originalEncoding:
                        self.declaredHTMLEncoding = newCharset
                        self._feed(self.declaredHTMLEncoding)
                        raise StopParsing
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
#"RobustParser.py" (or, in cases of extreme enterprisness,
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
except:
    chardet = None
chardet = None

# cjkcodecs and iconv_codec make Python know about more character encodings.
# Both are available from http://cjkpython.i18n.org/
# They're built in if you use Python 2.4.
try:
    import cjkcodecs.aliases
except:
    pass
try:
    import iconv_codec
except:
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
                 smartQuotesTo='xml'):
        self.markup, documentEncoding, sniffedEncoding = \
                     self._detectEncoding(markup)
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
    
    def _detectEncoding(self, xml_data):
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
            xml_encoding_match = re.compile \
                                 ('^<\?.*encoding=[\'"](.*?)[\'"].*\?>')\
                                 .match(xml_data)
        except:
            xml_encoding_match = None
        if xml_encoding_match:
            xml_encoding = xml_encoding_match.groups()[0].lower()
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
        except LookupError:
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
    soup = BeautifulSoup(sys.stdin.read())
    print soup.prettify()

########NEW FILE########
__FILENAME__ = exampleparser
#!/usr/bin/env python

import sys
import os
import re
import urllib2
import time
from xml.dom.minidom import Document

try:
    import xml.etree.ElementTree as ElementTree 
except ImportError:
    try:
        import cElementTree as ElementTree
    except ImportError:
        try:
            import elementtree.ElementTree as ElementTree
        except ImportError:
            import lxml.etree as ElementTree

missing_deps = False
try:
    import simplejson
    from BeautifulSoup import BeautifulSoup
except ImportError, E:
    missing_deps = E 

feedName = "example-list.xml"
feedPath = "http://openlayers.org/dev/examples/"

def getListOfOnlineExamples(baseUrl):
    """
    useful if you want to get a list of examples a url. not used by default.
    """
    html = urllib2.urlopen(baseUrl)
    soup = BeautifulSoup(html)
    examples = soup.findAll('li')
    examples = [example.find('a').get('href') for example in examples]
    examples = [example for example in examples if example.endswith('.html')]
    examples = [example for example in examples]
    return examples
    
def getListOfExamples(relPath):
    """
    returns list of .html filenames within a given path - excludes example-list.html
    """
    examples = os.listdir(relPath)
    examples = [example for example in examples if example.endswith('.html') and example != "example-list.html"]
    return examples
    

def getExampleHtml(location):
    """
    returns html of a specific example that is available online or locally
    """
    print '.',
    if location.startswith('http'):
        return urllib2.urlopen(location).read()
    else:
        f = open(location)
        html = f.read()
        f.close()
        return html
        
    
def extractById(soup, tagId, value=None):
    """
    returns full contents of a particular tag id
    """
    beautifulTag = soup.find(id=tagId)
    if beautifulTag:
        if beautifulTag.contents: 
            value = str(beautifulTag.renderContents()).strip()
            value = value.replace('\t','')
            value = value.replace('\n','')
    return value

def getRelatedClasses(html):
    """
    parses the html, and returns a list of all OpenLayers Classes 
    used within (ie what parts of OL the javascript uses).  
    """
    rawstr = r'''(?P<class>OpenLayers\..*?)\('''
    return re.findall(rawstr, html)

def parseHtml(html,ids):
    """
    returns dictionary of items of interest
    """
    soup = BeautifulSoup(html)
    d = {}
    for tagId in ids:
        d[tagId] = extractById(soup,tagId)
    #classes should eventually be parsed from docs - not automatically created.
    classes = getRelatedClasses(html)
    d['classes'] = classes
    return d

def getSvnInfo(path):
    h = os.popen("svn info %s --xml" % path)
    tree = ElementTree.fromstring(h.read())
    h.close()
    d = {
        'url': tree.findtext('entry/url'),
        'author': tree.findtext('entry/commit/author'),
        'date': tree.findtext('entry/commit/date')
    }
    return d
    
def createFeed(examples):
    doc = Document()
    atomuri = "http://www.w3.org/2005/Atom"
    feed = doc.createElementNS(atomuri, "feed")
    feed.setAttribute("xmlns", atomuri)
    title = doc.createElementNS(atomuri, "title")
    title.appendChild(doc.createTextNode("OpenLayers Examples"))
    feed.appendChild(title)
    link = doc.createElementNS(atomuri, "link")
    link.setAttribute("rel", "self")
    link.setAttribute("href", feedPath + feedName)
    
    modtime = time.strftime("%Y-%m-%dT%I:%M:%SZ", time.gmtime())
    id = doc.createElementNS(atomuri, "id")
    id.appendChild(doc.createTextNode("%s%s#%s" % (feedPath, feedName, modtime)))
    feed.appendChild(id)
    
    updated = doc.createElementNS(atomuri, "updated")
    updated.appendChild(doc.createTextNode(modtime))
    feed.appendChild(updated)

    examples.sort(key=lambda x:x["modified"])
    for example in sorted(examples, key=lambda x:x["modified"], reverse=True):
        entry = doc.createElementNS(atomuri, "entry")
        
        title = doc.createElementNS(atomuri, "title")
        title.appendChild(doc.createTextNode(example["title"] or example["example"]))
        entry.appendChild(title)
        
        link = doc.createElementNS(atomuri, "link")
        link.setAttribute("href", "%s%s" % (feedPath, example["example"]))
        entry.appendChild(link)
    
        summary = doc.createElementNS(atomuri, "summary")
        summary.appendChild(doc.createTextNode(example["shortdesc"] or example["example"]))
        entry.appendChild(summary)
        
        updated = doc.createElementNS(atomuri, "updated")
        updated.appendChild(doc.createTextNode(example["modified"]))
        entry.appendChild(updated)
        
        author = doc.createElementNS(atomuri, "author")
        name = doc.createElementNS(atomuri, "name")
        name.appendChild(doc.createTextNode(example["author"]))
        author.appendChild(name)
        entry.appendChild(author)
        
        id = doc.createElementNS(atomuri, "id")
        id.appendChild(doc.createTextNode("%s%s#%s" % (feedPath, example["example"], example["modified"])))
        entry.appendChild(id)
        
        feed.appendChild(entry)

    doc.appendChild(feed)
    return doc    
    
def wordIndex(examples):
    """
    Create an inverted index based on words in title and shortdesc.  Keys are
    lower cased words.  Values are dictionaries with example index keys and
    count values.
    """
    index = {}
    unword = re.compile("\\W+")
    keys = ["shortdesc", "title"]
    for i in range(len(examples)):
        for key in keys:
            text = examples[i][key]
            if text:
                words = unword.split(text)
                for word in words:
                    if word:
                        word = word.lower()
                        if index.has_key(word):
                            if index[word].has_key(i):
                                index[word][i] += 1
                            else:
                                index[word][i] = 1
                        else:
                            index[word] = {i: 1}
    return index
    
if __name__ == "__main__":

    if missing_deps:
        print "This script requires simplejson and BeautifulSoup. You don't have them. \n(%s)" % E
        sys.exit()
    
    if len(sys.argv) > 1:
        outFile = open(sys.argv[1],'w')
    else:
        outFile = open('../examples/example-list.js','w')
    
    examplesLocation = '../examples'
    print 'Reading examples from %s and writing out to %s' % (examplesLocation, outFile.name)
   
    exampleList = []
    docIds = ['title','shortdesc']
   
    #comment out option to create docs from online resource
    #examplesLocation = 'http://svn.openlayers.org/sandbox/docs/examples/'
    #examples = getListOfOnlineExamples(examplesLocation)

    examples = getListOfExamples(examplesLocation)

    modtime = time.strftime("%Y-%m-%dT%I:%M:%SZ", time.gmtime())

    for example in examples:
        url = os.path.join(examplesLocation,example)
        html = getExampleHtml(url)
        tagvalues = parseHtml(html,docIds)
        tagvalues['example'] = example
        # add in svn info
        d = getSvnInfo(url)
        tagvalues["modified"] = d["date"] or modtime
        tagvalues["author"] = d["author"] or "anonymous"
        tagvalues['link'] = example

        exampleList.append(tagvalues)
        
    print
    
    exampleList.sort(key=lambda x:x['example'].lower())
    
    index = wordIndex(exampleList)

    json = simplejson.dumps({"examples": exampleList, "index": index})
    #give the json a global variable we can use in our js.  This should be replaced or made optional.
    json = 'var info=' + json 
    outFile.write(json)
    outFile.close()

    print "writing feed to ../examples/%s " % feedName
    atom = open('../examples/%s' % feedName, 'w')
    doc = createFeed(exampleList)
    atom.write(doc.toxml())
    atom.close()


    print 'complete'

    

########NEW FILE########
__FILENAME__ = jsmin
#!/usr/bin/python

# This code is original from jsmin by Douglas Crockford, it was translated to
# Python by Baruch Even. The original code had the following copyright and
# license.
#
# /* jsmin.c
#    2007-01-08
#
# Copyright (c) 2002 Douglas Crockford  (www.crockford.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# The Software shall be used for Good, not Evil.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# */

from StringIO import StringIO

def jsmin(js):
    ins = StringIO(js)
    outs = StringIO()
    JavascriptMinify().minify(ins, outs)
    str = outs.getvalue()
    if len(str) > 0 and str[0] == '\n':
        str = str[1:]
    return str

def isAlphanum(c):
    """return true if the character is a letter, digit, underscore,
           dollar sign, or non-ASCII character.
    """
    return ((c >= 'a' and c <= 'z') or (c >= '0' and c <= '9') or
            (c >= 'A' and c <= 'Z') or c == '_' or c == '$' or c == '\\' or (c is not None and ord(c) > 126));

class UnterminatedComment(Exception):
    pass

class UnterminatedStringLiteral(Exception):
    pass

class UnterminatedRegularExpression(Exception):
    pass

class JavascriptMinify(object):

    def _outA(self):
        self.outstream.write(self.theA)
    def _outB(self):
        self.outstream.write(self.theB)

    def _get(self):
        """return the next character from stdin. Watch out for lookahead. If
           the character is a control character, translate it to a space or
           linefeed.
        """
        c = self.theLookahead
        self.theLookahead = None
        if c == None:
            c = self.instream.read(1)
        if c >= ' ' or c == '\n':
            return c
        if c == '': # EOF
            return '\000'
        if c == '\r':
            return '\n'
        return ' '

    def _peek(self):
        self.theLookahead = self._get()
        return self.theLookahead

    def _next(self):
        """get the next character, excluding comments. peek() is used to see
           if a '/' is followed by a '/' or '*'.
        """
        c = self._get()
        if c == '/':
            p = self._peek()
            if p == '/':
                c = self._get()
                while c > '\n':
                    c = self._get()
                return c
            if p == '*':
                c = self._get()
                while 1:
                    c = self._get()
                    if c == '*':
                        if self._peek() == '/':
                            self._get()
                            return ' '
                    if c == '\000':
                        raise UnterminatedComment()

        return c

    def _action(self, action):
        """do something! What you do is determined by the argument:
           1   Output A. Copy B to A. Get the next B.
           2   Copy B to A. Get the next B. (Delete A).
           3   Get the next B. (Delete B).
           action treats a string as a single character. Wow!
           action recognizes a regular expression if it is preceded by ( or , or =.
        """
        if action <= 1:
            self._outA()

        if action <= 2:
            self.theA = self.theB
            if self.theA == "'" or self.theA == '"':
                while 1:
                    self._outA()
                    self.theA = self._get()
                    if self.theA == self.theB:
                        break
                    if self.theA <= '\n':
                        raise UnterminatedStringLiteral()
                    if self.theA == '\\':
                        self._outA()
                        self.theA = self._get()


        if action <= 3:
            self.theB = self._next()
            if self.theB == '/' and (self.theA == '(' or self.theA == ',' or
                                     self.theA == '=' or self.theA == ':' or
                                     self.theA == '[' or self.theA == '?' or
                                     self.theA == '!' or self.theA == '&' or
                                     self.theA == '|'):
                self._outA()
                self._outB()
                while 1:
                    self.theA = self._get()
                    if self.theA == '/':
                        break
                    elif self.theA == '\\':
                        self._outA()
                        self.theA = self._get()
                    elif self.theA <= '\n':
                        raise UnterminatedRegularExpression()
                    self._outA()
                self.theB = self._next()


    def _jsmin(self):
        """Copy the input to the output, deleting the characters which are
           insignificant to JavaScript. Comments will be removed. Tabs will be
           replaced with spaces. Carriage returns will be replaced with linefeeds.
           Most spaces and linefeeds will be removed.
        """
        self.theA = '\n'
        self._action(3)

        while self.theA != '\000':
            if self.theA == ' ':
                if isAlphanum(self.theB):
                    self._action(1)
                else:
                    self._action(2)
            elif self.theA == '\n':
                if self.theB in ['{', '[', '(', '+', '-']:
                    self._action(1)
                elif self.theB == ' ':
                    self._action(3)
                else:
                    if isAlphanum(self.theB):
                        self._action(1)
                    else:
                        self._action(2)
            else:
                if self.theB == ' ':
                    if isAlphanum(self.theA):
                        self._action(1)
                    else:
                        self._action(3)
                elif self.theB == '\n':
                    if self.theA in ['}', ']', ')', '+', '-', '"', '\'']:
                        self._action(1)
                    else:
                        if isAlphanum(self.theA):
                            self._action(1)
                        else:
                            self._action(3)
                else:
                    self._action(1)

    def minify(self, instream, outstream):
        self.instream = instream
        self.outstream = outstream
        self.theA = None
        self.thaB = None
        self.theLookahead = None

        self._jsmin()
        self.instream.close()

if __name__ == '__main__':
    import sys
    jsm = JavascriptMinify()
    jsm.minify(sys.stdin, sys.stdout)

########NEW FILE########
__FILENAME__ = mergejs
#!/usr/bin/env python
#
# Merge multiple JavaScript source code files into one.
#
# Usage:
# This script requires source files to have dependencies specified in them.
#
# Dependencies are specified with a comment of the form:
#
#     // @requires <file path>
#
#  e.g.
#
#    // @requires Geo/DataSource.js
#
# This script should be executed like so:
#
#     mergejs.py <output.js> <directory> [...]
#
# e.g.
#
#     mergejs.py openlayers.js Geo/ CrossBrowser/
#
#  This example will cause the script to walk the `Geo` and
#  `CrossBrowser` directories--and subdirectories thereof--and import
#  all `*.js` files encountered. The dependency declarations will be extracted
#  and then the source code from imported files will be output to 
#  a file named `openlayers.js` in an order which fulfils the dependencies
#  specified.
#
#
# Note: This is a very rough initial version of this code.
#
# -- Copyright 2005-2008 MetaCarta, Inc. / OpenLayers project --
#

# TODO: Allow files to be excluded. e.g. `Crossbrowser/DebugMode.js`?
# TODO: Report error when dependency can not be found rather than KeyError.

import re
import os
import sys

SUFFIX_JAVASCRIPT = ".js"

RE_REQUIRE = "@requires:? (.*)\n" # TODO: Ensure in comment?
class SourceFile:
    """
    Represents a Javascript source code file.
    """

    def __init__(self, filepath, source):
        """
        """
        self.filepath = filepath
        self.source = source

        self.requiredBy = []


    def _getRequirements(self):
        """
        Extracts the dependencies specified in the source code and returns
        a list of them.
        """
        # TODO: Cache?
        return re.findall(RE_REQUIRE, self.source)

    requires = property(fget=_getRequirements, doc="")



def usage(filename):
    """
    Displays a usage message.
    """
    print "%s [-c <config file>] <output.js> <directory> [...]" % filename


class Config:
    """
    Represents a parsed configuration file.

    A configuration file should be of the following form:

        [first]
        3rd/prototype.js
        core/application.js
        core/params.js
        # A comment

        [last]
        core/api.js # Another comment

        [exclude]
        3rd/logger.js

    All headings are required.

    The files listed in the `first` section will be forced to load
    *before* all other files (in the order listed). The files in `last`
    section will be forced to load *after* all the other files (in the
    order listed).

    The files list in the `exclude` section will not be imported.

    Any text appearing after a # symbol indicates a comment.
    
    """

    def __init__(self, filename):
        """
        Parses the content of the named file and stores the values.
        """
        lines = [re.sub("#.*?$", "", line).strip() # Assumes end-of-line character is present
                 for line in open(filename)
                 if line.strip() and not line.strip().startswith("#")] # Skip blank lines and comments

        self.forceFirst = lines[lines.index("[first]") + 1:lines.index("[last]")]

        self.forceLast = lines[lines.index("[last]") + 1:lines.index("[include]")]
        self.include =  lines[lines.index("[include]") + 1:lines.index("[exclude]")]
        self.exclude =  lines[lines.index("[exclude]") + 1:]

def run (sourceDirectory, outputFilename = None, configFile = None):
    cfg = None
    if configFile:
        cfg = Config(configFile)

    allFiles = []

    ## Find all the Javascript source files
    for root, dirs, files in os.walk(sourceDirectory):
        for filename in files:
            if filename.endswith(SUFFIX_JAVASCRIPT) and not filename.startswith("."):
                filepath = os.path.join(root, filename)[len(sourceDirectory)+1:]
                filepath = filepath.replace("\\", "/")
                if cfg and cfg.include:
                    if filepath in cfg.include or filepath in cfg.forceFirst:
                        allFiles.append(filepath)
                elif (not cfg) or (filepath not in cfg.exclude):
                    allFiles.append(filepath)

    ## Header inserted at the start of each file in the output
    HEADER = "/* " + "=" * 70 + "\n    %s\n" + "   " + "=" * 70 + " */\n\n"

    files = {}

    order = [] # List of filepaths to output, in a dependency satisfying order 

    ## Import file source code
    ## TODO: Do import when we walk the directories above?
    for filepath in allFiles:
        print "Importing: %s" % filepath
        fullpath = os.path.join(sourceDirectory, filepath).strip()
        content = open(fullpath, "U").read() # TODO: Ensure end of line @ EOF?
        files[filepath] = SourceFile(filepath, content) # TODO: Chop path?

    print

    from toposort import toposort

    complete = False
    resolution_pass = 1

    while not complete:
        order = [] # List of filepaths to output, in a dependency satisfying order 
        nodes = []
        routes = []
        ## Resolve the dependencies
        print "Resolution pass %s... " % resolution_pass
        resolution_pass += 1 

        for filepath, info in files.items():
            nodes.append(filepath)
            for neededFilePath in info.requires:
                routes.append((neededFilePath, filepath))

        for dependencyLevel in toposort(nodes, routes):
            for filepath in dependencyLevel:
                order.append(filepath)
                if not files.has_key(filepath):
                    print "Importing: %s" % filepath
                    fullpath = os.path.join(sourceDirectory, filepath).strip()
                    content = open(fullpath, "U").read() # TODO: Ensure end of line @ EOF?
                    files[filepath] = SourceFile(filepath, content) # TODO: Chop path?
        


        # Double check all dependencies have been met
        complete = True
        try:
            for fp in order:
                if max([order.index(rfp) for rfp in files[fp].requires] +
                       [order.index(fp)]) != order.index(fp):
                    complete = False
        except:
            complete = False
        
        print    


    ## Move forced first and last files to the required position
    if cfg:
        print "Re-ordering files..."
        order = cfg.forceFirst + [item
                     for item in order
                     if ((item not in cfg.forceFirst) and
                         (item not in cfg.forceLast))] + cfg.forceLast
    
    print
    ## Output the files in the determined order
    result = []

    for fp in order:
        f = files[fp]
        print "Exporting: ", f.filepath
        result.append(HEADER % f.filepath)
        source = f.source
        result.append(source)
        if not source.endswith("\n"):
            result.append("\n")

    print "\nTotal files merged: %d " % len(files)

    if outputFilename:
        print "\nGenerating: %s" % (outputFilename)
        open(outputFilename, "w").write("".join(result))
    return "".join(result)

if __name__ == "__main__":
    import getopt

    options, args = getopt.getopt(sys.argv[1:], "-c:")
    
    try:
        outputFilename = args[0]
    except IndexError:
        usage(sys.argv[0])
        raise SystemExit
    else:
        sourceDirectory = args[1]
        if not sourceDirectory:
            usage(sys.argv[0])
            raise SystemExit

    configFile = None
    if options and options[0][0] == "-c":
        configFile = options[0][1]
        print "Parsing configuration file: %s" % filename

    run( sourceDirectory, outputFilename, configFile )

########NEW FILE########
__FILENAME__ = minimize
# Minimal Python Minimizer
# Copyright 2008, Christopher Schmidt
# Released under the MIT License
#
# Taken from: http://svn.crschmidt.net/personal/python/minimize.py
# $Id: minimize.py 6 2008-01-03 06:33:35Z crschmidt $
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import re

def strip_comments_helper(data):
    """remove all /* */ format comments and surrounding whitespace."""
    p = re.compile(r'[\s]*/\*.*?\*/[\s]*', re.DOTALL)
    return p.sub('',data)

def minimize(data, exclude=None):
    """Central function call. This will call all other compression
       functions. To add further compression algorithms, simply add
       functions whose names end in _helper which take a string as input 
       and return a more compressed string as output."""
    for key, item in globals().iteritems():
        if key.endswith("_helper"):
            func_key = key[:-7]
            if not exclude or not func_key in exclude:   
                data = item(data)
    return data   

if __name__ == "__main__":
    import sys
    print minimize(open(sys.argv[1]).read())

########NEW FILE########
__FILENAME__ = oldot
import re
import os    
def run():
    sourceDirectory = "../lib/OpenLayers"    
    allFiles = []
    SUFFIX_JAVASCRIPT = ".js"
    ## Find all the Javascript source files
    for root, dirs, files in os.walk(sourceDirectory):
        for filename in files:
            if filename.endswith(SUFFIX_JAVASCRIPT) and not filename.startswith("."):
                filepath = os.path.join(root, filename)[len(sourceDirectory)+1:]
                filepath = filepath.replace("\\", "/")
                data = open(os.path.join(sourceDirectory, filepath)).read()
                parents = re.search("OpenLayers.Class\((.*?){", data, 
                      re.DOTALL)
                if parents:
                    parents = [x.strip() for x in parents.group(1).strip().strip(",").split(",")]
                else: 
                    parents = []
                cls = "OpenLayers.%s" % filepath.strip(".js").replace("/", ".")
                allFiles.append([cls, parents])
    return allFiles
print """
digraph name {
  fontname = "Helvetica"
  fontsize = 8
  K = 0.6

  node [
    fontname = "Helvetica"
    fontsize = 8
    shape = "plaintext"
  ]
"""

for i in run():
    print i[0].replace(".", "_")
    for item in i[1]:
        if not item: continue
        print "%s -> %s" % (i[0].replace(".","_"), item.replace(".", "_"))
    print "; "

print """}"""

########NEW FILE########
__FILENAME__ = shrinksafe
#!/usr/bin/env python
#
# Script to provide a wrapper around the ShrinkSafe "web service"
# <http://shrinksafe.dojotoolkit.org/>
#

#
# We use this script for two reasons:
#
#  * This avoids having to install and configure Java and the standalone
#    ShrinkSafe utility.
#
#  * The current ShrinkSafe standalone utility was broken when we last
#    used it.
#

import sys

import urllib
import urllib2

URL_SHRINK_SAFE = "http://shrinksafe.dojotoolkit.org/shrinksafe.php"

# This would normally be dynamically generated:
BOUNDARY_MARKER = "---------------------------72288400411964641492083565382"
                   
if __name__ == "__main__":
    ## Grab the source code
    try:
        sourceFilename = sys.argv[1]
    except:
        print "Usage: %s (<source filename>|-)" % sys.argv[0]
        raise SystemExit

    if sourceFilename == "-":
        sourceCode = sys.stdin.read()
        sourceFilename = "stdin.js"
    else:
        sourceCode = open(sourceFilename).read()
        
    ## Create the request replicating posting of the form from the web page
    request = urllib2.Request(url=URL_SHRINK_SAFE)
    request.add_header("Content-Type",
                       "multipart/form-data; boundary=%s" % BOUNDARY_MARKER)
    request.add_data("""
--%s
Content-Disposition: form-data; name="shrinkfile[]"; filename="%s"
Content-Type: application/x-javascript

%s
""" % (BOUNDARY_MARKER, sourceFilename, sourceCode))

    ## Deliver the result
    print urllib2.urlopen(request).read(),

########NEW FILE########
__FILENAME__ = toposort
#
# According to <http://www.vrplumber.com/programming/> this file
# is licensed under a BSD-style license. We only use the section
# originally by Tim Peters.
#
# TODO: The use of this code needs to be okayed by someone.
#

class RecursionError( OverflowError, ValueError ):
    '''Unable to calculate result because of recursive structure'''
    

def sort(nodes, routes, noRecursion=1):
    '''Passed a list of node IDs and a list of source,dest ID routes
    attempt to create a list of stages where each sub list
    is one stage in a process.
    '''
    children, parents = _buildChildrenLists(routes)
    # first stage is those nodes
    # having no incoming routes...
    stage = []
    stages = [stage]
    taken = []
    for node in nodes:
        if (not parents.get(node)):
            stage.append (node)
    if nodes and not stage:
        # there is no element which does not depend on
        # some other element!!!
        stage.append( nodes[0])
    taken.extend( stage )
    nodes = filter ( lambda x, l=stage: x not in l, nodes )
    while nodes:
        previousStageChildren = []
        nodelen = len(nodes)
        # second stage are those nodes
        # which are direct children of the first stage
        for node in stage:
            for child in children.get (node, []):
                if child not in previousStageChildren and child not in taken:
                    previousStageChildren.append(child)
                elif child in taken and noRecursion:
                    raise RecursionError( (child, node) )
        # unless they are children of other direct children...
        # TODO, actually do that...
        stage = previousStageChildren
        removes = []
        for current in stage:
            currentParents = parents.get( current, [] )
            for parent in currentParents:
                if parent in stage and parent != current:
                    # might wind up removing current...
                    if not current in parents.get(parent, []):
                        # is not mutually dependent...
                        removes.append( current )
        for remove in removes:
            while remove in stage:
                stage.remove( remove )
        stages.append( stage)
        taken.extend( stage )
        nodes = filter ( lambda x, l=stage: x not in l, nodes )
        if nodelen == len(nodes):
            if noRecursion:
                raise RecursionError( nodes )
            else:
                stages.append( nodes[:] )
                nodes = []
    return stages

def _buildChildrenLists (routes):
    childrenTable = {}
    parentTable = {}
    for sourceID,destinationID in routes:
        currentChildren = childrenTable.get( sourceID, [])
        currentParents = parentTable.get( destinationID, [])
        if not destinationID in currentChildren:
            currentChildren.append ( destinationID)
        if not sourceID in currentParents:
            currentParents.append ( sourceID)
        childrenTable[sourceID] = currentChildren
        parentTable[destinationID] = currentParents
    return childrenTable, parentTable


def toposort (nodes, routes, noRecursion=1):
    '''Topological sort from Tim Peters, fairly efficient
    in comparison (it seems).'''
    #first calculate the recursion depth
    
    dependencies = {}
    inversedependencies = {}
    if not nodes:
        return []
    if not routes:
        return [nodes]
    for node in nodes:
        dependencies[ node ] = (0, node)
        inversedependencies[ node ] = []
    
    
    for depended, depends in routes:
        # is it a null rule
        try:
            newdependencylevel, object = dependencies.get ( depends, (0, depends))
        except TypeError:
            print depends
            raise
        dependencies[ depends ] = (newdependencylevel + 1,  depends)
        # "dependency (existence) of depended-on"
        newdependencylevel,object = dependencies.get ( depended, (0, depended) )
        dependencies[ depended ] = (newdependencylevel, depended)
        # Inverse dependency set up
        dependencieslist = inversedependencies.get ( depended, [])
        dependencieslist.append (depends)
        inversedependencies[depended] = dependencieslist
    ### Now we do the actual sorting
    # The first task is to create the sortable
    # list of dependency-levels
    sortinglist = dependencies.values()
    sortinglist.sort ()
    output = []
    while sortinglist:
        deletelist = []
        generation = []
        output.append( generation)
        while sortinglist and sortinglist[0][0] == 0:
            number, object = sortinglist[0]
            generation.append ( object )
            deletelist.append( object )
            for inverse in inversedependencies.get(object, () ):
                try:
                    oldcount, inverse = dependencies [ inverse]
                    if oldcount > 0:
                        # will be dealt with on later pass
                        dependencies [ inverse] = (oldcount-1, inverse)
                    else:
                        # will be dealt with on this pass,
                        # so needs not to be in the sorting list next time
                        deletelist.append( inverse )
                    # just in case a loop comes through
                    inversedependencies[object] = []
                except KeyError:
                    # dealing with a recursion-breaking run...
                    pass
            del sortinglist [0]
        # if no elements could be deleted, then
        # there is something which depends upon itself
        if not deletelist:
            if noRecursion:
                raise RecursionError( sortinglist )
            else:
                # hack so that something gets deleted...
##                import pdb
##                pdb.set_trace()
                dependencies[sortinglist[0][1]] = (0,sortinglist[0][1])
        # delete the items that were dealt with
        for item in deletelist:
            try:
                del dependencies [ item ]
            except KeyError:
                pass
        # need to recreate the sortinglist
        sortinglist = dependencies.values()
        if not generation:
            output.remove( generation )
        sortinglist.sort ()
    return output





if __name__ == "__main__":

    nodes = ['a', 'b', 'c', 'd', 'e', 'f']
    route = [('a', 'b'), ('b', 'c'), ('b', 'd'), ('e','f')]

    for x in  toposort( nodes, route):
        for a in x:
            print a

    raise SystemExit



    import pprint, traceback
    nodes= [ 0,1,2,3,4,5 ]
    testingValues = [
        [ (0,1),(1,2),(2,3),(3,4),(4,5)],
        [ (0,1),(0,2),(1,2),(3,4),(4,5)],
        [
        (0,1),
        (0,2),
        (0,2),
                    (2,4),
                    (2,5),
                (3,2),
        (0,3)],
        [
        (0,1), # 3-element cycle test, no orphan nodes
        (1,2),
        (2,0),
                    (2,4),
                    (2,5),
                (3,2),
        (0,3)],
        [
        (0,1),
        (1,1),
        (1,1),
                (1,4),
                (1,5),
                (1,2),
        (3,1),
        (2,1),
        (2,0)],
        [
            (0,1),
            (1,0),
            (0,2),
            (0,3),
        ],
        [
            (0,1),
            (1,0),
            (0,2),
            (3,1),
        ],
    ]
    print 'sort, no recursion allowed'
    for index in range(len(testingValues)):
##        print '    %s -- %s'%( index, testingValues[index])
        try:
            print '        ', sort( nodes, testingValues[index] )
        except:
            print 'exception raised'
    print 'toposort, no recursion allowed'
    for index in range(len(testingValues)):
##        print '    %s -- %s'%( index, testingValues[index])
        try:
            print '        ', toposort( nodes, testingValues[index] )
        except:
            print 'exception raised'
    print 'sort, recursion allowed'
    for index in range(len(testingValues)):
##        print '    %s -- %s'%( index, testingValues[index])
        try:
            print '        ', sort( nodes, testingValues[index],0 )
        except:
            print 'exception raised'
    print 'toposort, recursion allowed'
    for index in range(len(testingValues)):
##        print '    %s -- %s'%( index, testingValues[index])
        try:
            print '        ', toposort( nodes, testingValues[index],0 )
        except:
            print 'exception raised'
        
        
    

########NEW FILE########
