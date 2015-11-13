__FILENAME__ = _html5lib
__all__ = [
    'HTML5TreeBuilder',
    ]

import warnings
from bs4.builder import (
    PERMISSIVE,
    HTML,
    HTML_5,
    HTMLTreeBuilder,
    )
from bs4.element import NamespacedAttribute
import html5lib
from html5lib.constants import namespaces
from bs4.element import (
    Comment,
    Doctype,
    NavigableString,
    Tag,
    )

class HTML5TreeBuilder(HTMLTreeBuilder):
    """Use html5lib to build a tree."""

    features = ['html5lib', PERMISSIVE, HTML_5, HTML]

    def prepare_markup(self, markup, user_specified_encoding):
        # Store the user-specified encoding for use later on.
        self.user_specified_encoding = user_specified_encoding
        return markup, None, None, False

    # These methods are defined by Beautiful Soup.
    def feed(self, markup):
        if self.soup.parse_only is not None:
            warnings.warn("You provided a value for parse_only, but the html5lib tree builder doesn't support parse_only. The entire document will be parsed.")
        parser = html5lib.HTMLParser(tree=self.create_treebuilder)
        doc = parser.parse(markup, encoding=self.user_specified_encoding)

        # Set the character encoding detected by the tokenizer.
        if isinstance(markup, unicode):
            # We need to special-case this because html5lib sets
            # charEncoding to UTF-8 if it gets Unicode input.
            doc.original_encoding = None
        else:
            doc.original_encoding = parser.tokenizer.stream.charEncoding[0]

    def create_treebuilder(self, namespaceHTMLElements):
        self.underlying_builder = TreeBuilderForHtml5lib(
            self.soup, namespaceHTMLElements)
        return self.underlying_builder

    def test_fragment_to_document(self, fragment):
        """See `TreeBuilder`."""
        return u'<html><head></head><body>%s</body></html>' % fragment


class TreeBuilderForHtml5lib(html5lib.treebuilders._base.TreeBuilder):

    def __init__(self, soup, namespaceHTMLElements):
        self.soup = soup
        super(TreeBuilderForHtml5lib, self).__init__(namespaceHTMLElements)

    def documentClass(self):
        self.soup.reset()
        return Element(self.soup, self.soup, None)

    def insertDoctype(self, token):
        name = token["name"]
        publicId = token["publicId"]
        systemId = token["systemId"]

        doctype = Doctype.for_name_and_ids(name, publicId, systemId)
        self.soup.object_was_parsed(doctype)

    def elementClass(self, name, namespace):
        tag = self.soup.new_tag(name, namespace)
        return Element(tag, self.soup, namespace)

    def commentClass(self, data):
        return TextNode(Comment(data), self.soup)

    def fragmentClass(self):
        self.soup = BeautifulSoup("")
        self.soup.name = "[document_fragment]"
        return Element(self.soup, self.soup, None)

    def appendChild(self, node):
        # XXX This code is not covered by the BS4 tests.
        self.soup.append(node.element)

    def getDocument(self):
        return self.soup

    def getFragment(self):
        return html5lib.treebuilders._base.TreeBuilder.getFragment(self).element

class AttrList(object):
    def __init__(self, element):
        self.element = element
        self.attrs = dict(self.element.attrs)
    def __iter__(self):
        return list(self.attrs.items()).__iter__()
    def __setitem__(self, name, value):
        "set attr", name, value
        self.element[name] = value
    def items(self):
        return list(self.attrs.items())
    def keys(self):
        return list(self.attrs.keys())
    def __len__(self):
        return len(self.attrs)
    def __getitem__(self, name):
        return self.attrs[name]
    def __contains__(self, name):
        return name in list(self.attrs.keys())


class Element(html5lib.treebuilders._base.Node):
    def __init__(self, element, soup, namespace):
        html5lib.treebuilders._base.Node.__init__(self, element.name)
        self.element = element
        self.soup = soup
        self.namespace = namespace

    def appendChild(self, node):
        if (node.element.__class__ == NavigableString and self.element.contents
            and self.element.contents[-1].__class__ == NavigableString):
            # Concatenate new text onto old text node
            # XXX This has O(n^2) performance, for input like
            # "a</a>a</a>a</a>..."
            old_element = self.element.contents[-1]
            new_element = self.soup.new_string(old_element + node.element)
            old_element.replace_with(new_element)
        else:
            self.element.append(node.element)
            node.parent = self

    def getAttributes(self):
        return AttrList(self.element)

    def setAttributes(self, attributes):
        if attributes is not None and len(attributes) > 0:

            converted_attributes = []
            for name, value in list(attributes.items()):
                if isinstance(name, tuple):
                    new_name = NamespacedAttribute(*name)
                    del attributes[name]
                    attributes[new_name] = value

            self.soup.builder._replace_cdata_list_attribute_values(
                self.name, attributes)
            for name, value in attributes.items():
                self.element[name] = value

            # The attributes may contain variables that need substitution.
            # Call set_up_substitutions manually.
            #
            # The Tag constructor called this method when the Tag was created,
            # but we just set/changed the attributes, so call it again.
            self.soup.builder.set_up_substitutions(self.element)
    attributes = property(getAttributes, setAttributes)

    def insertText(self, data, insertBefore=None):
        text = TextNode(self.soup.new_string(data), self.soup)
        if insertBefore:
            self.insertBefore(text, insertBefore)
        else:
            self.appendChild(text)

    def insertBefore(self, node, refNode):
        index = self.element.index(refNode.element)
        if (node.element.__class__ == NavigableString and self.element.contents
            and self.element.contents[index-1].__class__ == NavigableString):
            # (See comments in appendChild)
            old_node = self.element.contents[index-1]
            new_str = self.soup.new_string(old_node + node.element)
            old_node.replace_with(new_str)
        else:
            self.element.insert(index, node.element)
            node.parent = self

    def removeChild(self, node):
        node.element.extract()

    def reparentChildren(self, newParent):
        while self.element.contents:
            child = self.element.contents[0]
            child.extract()
            if isinstance(child, Tag):
                newParent.appendChild(
                    Element(child, self.soup, namespaces["html"]))
            else:
                newParent.appendChild(
                    TextNode(child, self.soup))

    def cloneNode(self):
        tag = self.soup.new_tag(self.element.name, self.namespace)
        node = Element(tag, self.soup, self.namespace)
        for key,value in self.attributes:
            node.attributes[key] = value
        return node

    def hasContent(self):
        return self.element.contents

    def getNameTuple(self):
        if self.namespace == None:
            return namespaces["html"], self.name
        else:
            return self.namespace, self.name

    nameTuple = property(getNameTuple)

class TextNode(Element):
    def __init__(self, element, soup):
        html5lib.treebuilders._base.Node.__init__(self, None)
        self.element = element
        self.soup = soup

    def cloneNode(self):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = _htmlparser
"""Use the HTMLParser library to parse HTML files that aren't too bad."""

__all__ = [
    'HTMLParserTreeBuilder',
    ]

from HTMLParser import (
    HTMLParser,
    HTMLParseError,
    )
import sys
import warnings

# Starting in Python 3.2, the HTMLParser constructor takes a 'strict'
# argument, which we'd like to set to False. Unfortunately,
# http://bugs.python.org/issue13273 makes strict=True a better bet
# before Python 3.2.3.
#
# At the end of this file, we monkeypatch HTMLParser so that
# strict=True works well on Python 3.2.2.
major, minor, release = sys.version_info[:3]
CONSTRUCTOR_TAKES_STRICT = (
    major > 3
    or (major == 3 and minor > 2)
    or (major == 3 and minor == 2 and release >= 3))

from bs4.element import (
    CData,
    Comment,
    Declaration,
    Doctype,
    ProcessingInstruction,
    )
from bs4.dammit import EntitySubstitution, UnicodeDammit

from bs4.builder import (
    HTML,
    HTMLTreeBuilder,
    STRICT,
    )


HTMLPARSER = 'html.parser'

class BeautifulSoupHTMLParser(HTMLParser):
    def handle_starttag(self, name, attrs):
        # XXX namespace
        self.soup.handle_starttag(name, None, None, dict(attrs))

    def handle_endtag(self, name):
        self.soup.handle_endtag(name)

    def handle_data(self, data):
        self.soup.handle_data(data)

    def handle_charref(self, name):
        # XXX workaround for a bug in HTMLParser. Remove this once
        # it's fixed.
        if name.startswith('x'):
            real_name = int(name.lstrip('x'), 16)
        else:
            real_name = int(name)

        try:
            data = unichr(real_name)
        except (ValueError, OverflowError), e:
            data = u"\N{REPLACEMENT CHARACTER}"

        self.handle_data(data)

    def handle_entityref(self, name):
        character = EntitySubstitution.HTML_ENTITY_TO_CHARACTER.get(name)
        if character is not None:
            data = character
        else:
            data = "&%s;" % name
        self.handle_data(data)

    def handle_comment(self, data):
        self.soup.endData()
        self.soup.handle_data(data)
        self.soup.endData(Comment)

    def handle_decl(self, data):
        self.soup.endData()
        if data.startswith("DOCTYPE "):
            data = data[len("DOCTYPE "):]
        self.soup.handle_data(data)
        self.soup.endData(Doctype)

    def unknown_decl(self, data):
        if data.upper().startswith('CDATA['):
            cls = CData
            data = data[len('CDATA['):]
        else:
            cls = Declaration
        self.soup.endData()
        self.soup.handle_data(data)
        self.soup.endData(cls)

    def handle_pi(self, data):
        self.soup.endData()
        if data.endswith("?") and data.lower().startswith("xml"):
            # "An XHTML processing instruction using the trailing '?'
            # will cause the '?' to be included in data." - HTMLParser
            # docs.
            #
            # Strip the question mark so we don't end up with two
            # question marks.
            data = data[:-1]
        self.soup.handle_data(data)
        self.soup.endData(ProcessingInstruction)


class HTMLParserTreeBuilder(HTMLTreeBuilder):

    is_xml = False
    features = [HTML, STRICT, HTMLPARSER]

    def __init__(self, *args, **kwargs):
        if CONSTRUCTOR_TAKES_STRICT:
            kwargs['strict'] = False
        self.parser_args = (args, kwargs)

    def prepare_markup(self, markup, user_specified_encoding=None,
                       document_declared_encoding=None):
        """
        :return: A 4-tuple (markup, original encoding, encoding
        declared within markup, whether any characters had to be
        replaced with REPLACEMENT CHARACTER).
        """
        if isinstance(markup, unicode):
            return markup, None, None, False

        try_encodings = [user_specified_encoding, document_declared_encoding]
        dammit = UnicodeDammit(markup, try_encodings, is_html=True)
        return (dammit.markup, dammit.original_encoding,
                dammit.declared_html_encoding,
                dammit.contains_replacement_characters)

    def feed(self, markup):
        args, kwargs = self.parser_args
        parser = BeautifulSoupHTMLParser(*args, **kwargs)
        parser.soup = self.soup
        try:
            parser.feed(markup)
        except HTMLParseError, e:
            warnings.warn(RuntimeWarning(
                "Python's built-in HTMLParser cannot parse the given document. This is not a bug in Beautiful Soup. The best solution is to install an external parser (lxml or html5lib), and use Beautiful Soup with that parser. See http://www.crummy.com/software/BeautifulSoup/bs4/doc/#installing-a-parser for help."))
            raise e

# Patch 3.2 versions of HTMLParser earlier than 3.2.3 to use some
# 3.2.3 code. This ensures they don't treat markup like <p></p> as a
# string.
#
# XXX This code can be removed once most Python 3 users are on 3.2.3.
if major == 3 and minor == 2 and not CONSTRUCTOR_TAKES_STRICT:
    import re
    attrfind_tolerant = re.compile(
        r'\s*((?<=[\'"\s])[^\s/>][^\s/=>]*)(\s*=+\s*'
        r'(\'[^\']*\'|"[^"]*"|(?![\'"])[^>\s]*))?')
    HTMLParserTreeBuilder.attrfind_tolerant = attrfind_tolerant

    locatestarttagend = re.compile(r"""
  <[a-zA-Z][-.a-zA-Z0-9:_]*          # tag name
  (?:\s+                             # whitespace before attribute name
    (?:[a-zA-Z_][-.:a-zA-Z0-9_]*     # attribute name
      (?:\s*=\s*                     # value indicator
        (?:'[^']*'                   # LITA-enclosed value
          |\"[^\"]*\"                # LIT-enclosed value
          |[^'\">\s]+                # bare value
         )
       )?
     )
   )*
  \s*                                # trailing whitespace
""", re.VERBOSE)
    BeautifulSoupHTMLParser.locatestarttagend = locatestarttagend

    from html.parser import tagfind, attrfind

    def parse_starttag(self, i):
        self.__starttag_text = None
        endpos = self.check_for_whole_start_tag(i)
        if endpos < 0:
            return endpos
        rawdata = self.rawdata
        self.__starttag_text = rawdata[i:endpos]

        # Now parse the data between i+1 and j into a tag and attrs
        attrs = []
        match = tagfind.match(rawdata, i+1)
        assert match, 'unexpected call to parse_starttag()'
        k = match.end()
        self.lasttag = tag = rawdata[i+1:k].lower()
        while k < endpos:
            if self.strict:
                m = attrfind.match(rawdata, k)
            else:
                m = attrfind_tolerant.match(rawdata, k)
            if not m:
                break
            attrname, rest, attrvalue = m.group(1, 2, 3)
            if not rest:
                attrvalue = None
            elif attrvalue[:1] == '\'' == attrvalue[-1:] or \
                 attrvalue[:1] == '"' == attrvalue[-1:]:
                attrvalue = attrvalue[1:-1]
            if attrvalue:
                attrvalue = self.unescape(attrvalue)
            attrs.append((attrname.lower(), attrvalue))
            k = m.end()

        end = rawdata[k:endpos].strip()
        if end not in (">", "/>"):
            lineno, offset = self.getpos()
            if "\n" in self.__starttag_text:
                lineno = lineno + self.__starttag_text.count("\n")
                offset = len(self.__starttag_text) \
                         - self.__starttag_text.rfind("\n")
            else:
                offset = offset + len(self.__starttag_text)
            if self.strict:
                self.error("junk characters in start tag: %r"
                           % (rawdata[k:endpos][:20],))
            self.handle_data(rawdata[i:endpos])
            return endpos
        if end.endswith('/>'):
            # XHTML-style empty tag: <span attr="value" />
            self.handle_startendtag(tag, attrs)
        else:
            self.handle_starttag(tag, attrs)
            if tag in self.CDATA_CONTENT_ELEMENTS:
                self.set_cdata_mode(tag)
        return endpos

    def set_cdata_mode(self, elem):
        self.cdata_elem = elem.lower()
        self.interesting = re.compile(r'</\s*%s\s*>' % self.cdata_elem, re.I)

    BeautifulSoupHTMLParser.parse_starttag = parse_starttag
    BeautifulSoupHTMLParser.set_cdata_mode = set_cdata_mode

    CONSTRUCTOR_TAKES_STRICT = True

########NEW FILE########
__FILENAME__ = _lxml
__all__ = [
    'LXMLTreeBuilderForXML',
    'LXMLTreeBuilder',
    ]

from StringIO import StringIO
import collections
from lxml import etree
from bs4.element import Comment, Doctype, NamespacedAttribute
from bs4.builder import (
    FAST,
    HTML,
    HTMLTreeBuilder,
    PERMISSIVE,
    TreeBuilder,
    XML)
from bs4.dammit import UnicodeDammit

LXML = 'lxml'

class LXMLTreeBuilderForXML(TreeBuilder):
    DEFAULT_PARSER_CLASS = etree.XMLParser

    is_xml = True

    # Well, it's permissive by XML parser standards.
    features = [LXML, XML, FAST, PERMISSIVE]

    CHUNK_SIZE = 512

    @property
    def default_parser(self):
        # This can either return a parser object or a class, which
        # will be instantiated with default arguments.
        return etree.XMLParser(target=self, strip_cdata=False, recover=True)

    def __init__(self, parser=None, empty_element_tags=None):
        if empty_element_tags is not None:
            self.empty_element_tags = set(empty_element_tags)
        if parser is None:
            # Use the default parser.
            parser = self.default_parser
        if isinstance(parser, collections.Callable):
            # Instantiate the parser with default arguments
            parser = parser(target=self, strip_cdata=False)
        self.parser = parser
        self.soup = None
        self.nsmaps = None

    def _getNsTag(self, tag):
        # Split the namespace URL out of a fully-qualified lxml tag
        # name. Copied from lxml's src/lxml/sax.py.
        if tag[0] == '{':
            return tuple(tag[1:].split('}', 1))
        else:
            return (None, tag)

    def prepare_markup(self, markup, user_specified_encoding=None,
                       document_declared_encoding=None):
        """
        :return: A 3-tuple (markup, original encoding, encoding
        declared within markup).
        """
        if isinstance(markup, unicode):
            return markup, None, None, False

        try_encodings = [user_specified_encoding, document_declared_encoding]
        dammit = UnicodeDammit(markup, try_encodings, is_html=True)
        return (dammit.markup, dammit.original_encoding,
                dammit.declared_html_encoding,
                dammit.contains_replacement_characters)

    def feed(self, markup):
        if isinstance(markup, basestring):
            markup = StringIO(markup)
        # Call feed() at least once, even if the markup is empty,
        # or the parser won't be initialized.
        data = markup.read(self.CHUNK_SIZE)
        self.parser.feed(data)
        while data != '':
            # Now call feed() on the rest of the data, chunk by chunk.
            data = markup.read(self.CHUNK_SIZE)
            if data != '':
                self.parser.feed(data)
        self.parser.close()

    def close(self):
        self.nsmaps = None

    def start(self, name, attrs, nsmap={}):
        # Make sure attrs is a mutable dict--lxml may send an immutable dictproxy.
        attrs = dict(attrs)

        nsprefix = None
        # Invert each namespace map as it comes in.
        if len(nsmap) == 0 and self.nsmaps != None:
            # There are no new namespaces for this tag, but namespaces
            # are in play, so we need a separate tag stack to know
            # when they end.
            self.nsmaps.append(None)
        elif len(nsmap) > 0:
            # A new namespace mapping has come into play.
            if self.nsmaps is None:
                self.nsmaps = []
            inverted_nsmap = dict((value, key) for key, value in nsmap.items())
            self.nsmaps.append(inverted_nsmap)
            # Also treat the namespace mapping as a set of attributes on the
            # tag, so we can recreate it later.
            attrs = attrs.copy()
            for prefix, namespace in nsmap.items():
                attribute = NamespacedAttribute(
                    "xmlns", prefix, "http://www.w3.org/2000/xmlns/")
                attrs[attribute] = namespace

        if self.nsmaps is not None and len(self.nsmaps) > 0:
            # Namespaces are in play. Find any attributes that came in
            # from lxml with namespaces attached to their names, and
            # turn then into NamespacedAttribute objects.
            new_attrs = {}
            for attr, value in attrs.items():
                namespace, attr = self._getNsTag(attr)
                if namespace is None:
                    new_attrs[attr] = value
                else:
                    nsprefix = self._prefix_for_namespace(namespace)
                    attr = NamespacedAttribute(nsprefix, attr, namespace)
                    new_attrs[attr] = value
            attrs = new_attrs

        namespace, name = self._getNsTag(name)
        nsprefix = self._prefix_for_namespace(namespace)
        self.soup.handle_starttag(name, namespace, nsprefix, attrs)

    def _prefix_for_namespace(self, namespace):
        """Find the currently active prefix for the given namespace."""
        if namespace is None:
            return None
        for inverted_nsmap in reversed(self.nsmaps):
            if inverted_nsmap is not None and namespace in inverted_nsmap:
                return inverted_nsmap[namespace]

    def end(self, name):
        self.soup.endData()
        completed_tag = self.soup.tagStack[-1]
        namespace, name = self._getNsTag(name)
        nsprefix = None
        if namespace is not None:
            for inverted_nsmap in reversed(self.nsmaps):
                if inverted_nsmap is not None and namespace in inverted_nsmap:
                    nsprefix = inverted_nsmap[namespace]
                    break
        self.soup.handle_endtag(name, nsprefix)
        if self.nsmaps != None:
            # This tag, or one of its parents, introduced a namespace
            # mapping, so pop it off the stack.
            self.nsmaps.pop()
            if len(self.nsmaps) == 0:
                # Namespaces are no longer in play, so don't bother keeping
                # track of the namespace stack.
                self.nsmaps = None

    def pi(self, target, data):
        pass

    def data(self, content):
        self.soup.handle_data(content)

    def doctype(self, name, pubid, system):
        self.soup.endData()
        doctype = Doctype.for_name_and_ids(name, pubid, system)
        self.soup.object_was_parsed(doctype)

    def comment(self, content):
        "Handle comments as Comment objects."
        self.soup.endData()
        self.soup.handle_data(content)
        self.soup.endData(Comment)

    def test_fragment_to_document(self, fragment):
        """See `TreeBuilder`."""
        return u'<?xml version="1.0" encoding="utf-8"?>\n%s' % fragment


class LXMLTreeBuilder(HTMLTreeBuilder, LXMLTreeBuilderForXML):

    features = [LXML, HTML, FAST, PERMISSIVE]
    is_xml = False

    @property
    def default_parser(self):
        return etree.HTMLParser

    def feed(self, markup):
        self.parser.feed(markup)
        self.parser.close()

    def test_fragment_to_document(self, fragment):
        """See `TreeBuilder`."""
        return u'<html><body>%s</body></html>' % fragment

########NEW FILE########
__FILENAME__ = dammit
# -*- coding: utf-8 -*-
"""Beautiful Soup bonus library: Unicode, Dammit

This class forces XML data into a standard format (usually to UTF-8 or
Unicode).  It is heavily based on code from Mark Pilgrim's Universal
Feed Parser. It does not rewrite the XML or HTML to reflect a new
encoding; that's the tree builder's job.
"""

import codecs
from htmlentitydefs import codepoint2name
import re
import logging

# Import a library to autodetect character encodings.
chardet_type = None
try:
    # First try the fast C implementation.
    #  PyPI package: cchardet
    import cchardet
    def chardet_dammit(s):
        return cchardet.detect(s)['encoding']
except ImportError:
    try:
        # Fall back to the pure Python implementation
        #  Debian package: python-chardet
        #  PyPI package: chardet
        import chardet
        def chardet_dammit(s):
            return chardet.detect(s)['encoding']
        #import chardet.constants
        #chardet.constants._debug = 1
    except ImportError:
        # No chardet available.
        def chardet_dammit(s):
            return None

# Available from http://cjkpython.i18n.org/.
try:
    import iconv_codec
except ImportError:
    pass

xml_encoding_re = re.compile(
    '^<\?.*encoding=[\'"](.*?)[\'"].*\?>'.encode(), re.I)
html_meta_re = re.compile(
    '<\s*meta[^>]+charset\s*=\s*["\']?([^>]*?)[ /;\'">]'.encode(), re.I)

class EntitySubstitution(object):

    """Substitute XML or HTML entities for the corresponding characters."""

    def _populate_class_variables():
        lookup = {}
        reverse_lookup = {}
        characters_for_re = []
        for codepoint, name in list(codepoint2name.items()):
            character = unichr(codepoint)
            if codepoint != 34:
                # There's no point in turning the quotation mark into
                # &quot;, unless it happens within an attribute value, which
                # is handled elsewhere.
                characters_for_re.append(character)
                lookup[character] = name
            # But we do want to turn &quot; into the quotation mark.
            reverse_lookup[name] = character
        re_definition = "[%s]" % "".join(characters_for_re)
        return lookup, reverse_lookup, re.compile(re_definition)
    (CHARACTER_TO_HTML_ENTITY, HTML_ENTITY_TO_CHARACTER,
     CHARACTER_TO_HTML_ENTITY_RE) = _populate_class_variables()

    CHARACTER_TO_XML_ENTITY = {
        "'": "apos",
        '"': "quot",
        "&": "amp",
        "<": "lt",
        ">": "gt",
        }

    BARE_AMPERSAND_OR_BRACKET = re.compile("([<>]|"
                                           "&(?!#\d+;|#x[0-9a-fA-F]+;|\w+;)"
                                           ")")

    @classmethod
    def _substitute_html_entity(cls, matchobj):
        entity = cls.CHARACTER_TO_HTML_ENTITY.get(matchobj.group(0))
        return "&%s;" % entity

    @classmethod
    def _substitute_xml_entity(cls, matchobj):
        """Used with a regular expression to substitute the
        appropriate XML entity for an XML special character."""
        entity = cls.CHARACTER_TO_XML_ENTITY[matchobj.group(0)]
        return "&%s;" % entity

    @classmethod
    def quoted_attribute_value(self, value):
        """Make a value into a quoted XML attribute, possibly escaping it.

         Most strings will be quoted using double quotes.

          Bob's Bar -> "Bob's Bar"

         If a string contains double quotes, it will be quoted using
         single quotes.

          Welcome to "my bar" -> 'Welcome to "my bar"'

         If a string contains both single and double quotes, the
         double quotes will be escaped, and the string will be quoted
         using double quotes.

          Welcome to "Bob's Bar" -> "Welcome to &quot;Bob's bar&quot;
        """
        quote_with = '"'
        if '"' in value:
            if "'" in value:
                # The string contains both single and double
                # quotes.  Turn the double quotes into
                # entities. We quote the double quotes rather than
                # the single quotes because the entity name is
                # "&quot;" whether this is HTML or XML.  If we
                # quoted the single quotes, we'd have to decide
                # between &apos; and &squot;.
                replace_with = "&quot;"
                value = value.replace('"', replace_with)
            else:
                # There are double quotes but no single quotes.
                # We can use single quotes to quote the attribute.
                quote_with = "'"
        return quote_with + value + quote_with

    @classmethod
    def substitute_xml(cls, value, make_quoted_attribute=False):
        """Substitute XML entities for special XML characters.

        :param value: A string to be substituted. The less-than sign will
          become &lt;, the greater-than sign will become &gt;, and any
          ampersands that are not part of an entity defition will
          become &amp;.

        :param make_quoted_attribute: If True, then the string will be
         quoted, as befits an attribute value.
        """
        # Escape angle brackets, and ampersands that aren't part of
        # entities.
        value = cls.BARE_AMPERSAND_OR_BRACKET.sub(
            cls._substitute_xml_entity, value)

        if make_quoted_attribute:
            value = cls.quoted_attribute_value(value)
        return value

    @classmethod
    def substitute_html(cls, s):
        """Replace certain Unicode characters with named HTML entities.

        This differs from data.encode(encoding, 'xmlcharrefreplace')
        in that the goal is to make the result more readable (to those
        with ASCII displays) rather than to recover from
        errors. There's absolutely nothing wrong with a UTF-8 string
        containg a LATIN SMALL LETTER E WITH ACUTE, but replacing that
        character with "&eacute;" will make it more readable to some
        people.
        """
        return cls.CHARACTER_TO_HTML_ENTITY_RE.sub(
            cls._substitute_html_entity, s)


class UnicodeDammit:
    """A class for detecting the encoding of a *ML document and
    converting it to a Unicode string. If the source encoding is
    windows-1252, can replace MS smart quotes with their HTML or XML
    equivalents."""

    # This dictionary maps commonly seen values for "charset" in HTML
    # meta tags to the corresponding Python codec names. It only covers
    # values that aren't in Python's aliases and can't be determined
    # by the heuristics in find_codec.
    CHARSET_ALIASES = {"macintosh": "mac-roman",
                       "x-sjis": "shift-jis"}

    ENCODINGS_WITH_SMART_QUOTES = [
        "windows-1252",
        "iso-8859-1",
        "iso-8859-2",
        ]

    def __init__(self, markup, override_encodings=[],
                 smart_quotes_to=None, is_html=False):
        self.declared_html_encoding = None
        self.smart_quotes_to = smart_quotes_to
        self.tried_encodings = []
        self.contains_replacement_characters = False

        if markup == '' or isinstance(markup, unicode):
            self.markup = markup
            self.unicode_markup = unicode(markup)
            self.original_encoding = None
            return

        new_markup, document_encoding, sniffed_encoding = \
            self._detectEncoding(markup, is_html)
        self.markup = new_markup

        u = None
        if new_markup != markup:
            # _detectEncoding modified the markup, then converted it to
            # Unicode and then to UTF-8. So convert it from UTF-8.
            u = self._convert_from("utf8")
            self.original_encoding = sniffed_encoding

        if not u:
            for proposed_encoding in (
                override_encodings + [document_encoding, sniffed_encoding]):
                if proposed_encoding is not None:
                    u = self._convert_from(proposed_encoding)
                    if u:
                        break

        # If no luck and we have auto-detection library, try that:
        if not u and not isinstance(self.markup, unicode):
            u = self._convert_from(chardet_dammit(self.markup))

        # As a last resort, try utf-8 and windows-1252:
        if not u:
            for proposed_encoding in ("utf-8", "windows-1252"):
                u = self._convert_from(proposed_encoding)
                if u:
                    break

        # As an absolute last resort, try the encodings again with
        # character replacement.
        if not u:
            for proposed_encoding in (
                override_encodings + [
                    document_encoding, sniffed_encoding, "utf-8", "windows-1252"]):
                if proposed_encoding != "ascii":
                    u = self._convert_from(proposed_encoding, "replace")
                if u is not None:
                    logging.warning(
                            "Some characters could not be decoded, and were "
                            "replaced with REPLACEMENT CHARACTER.")
                    self.contains_replacement_characters = True
                    break

        # We could at this point force it to ASCII, but that would
        # destroy so much data that I think giving up is better
        self.unicode_markup = u
        if not u:
            self.original_encoding = None

    def _sub_ms_char(self, match):
        """Changes a MS smart quote character to an XML or HTML
        entity, or an ASCII character."""
        orig = match.group(1)
        if self.smart_quotes_to == 'ascii':
            sub = self.MS_CHARS_TO_ASCII.get(orig).encode()
        else:
            sub = self.MS_CHARS.get(orig)
            if type(sub) == tuple:
                if self.smart_quotes_to == 'xml':
                    sub = '&#x'.encode() + sub[1].encode() + ';'.encode()
                else:
                    sub = '&'.encode() + sub[0].encode() + ';'.encode()
            else:
                sub = sub.encode()
        return sub

    def _convert_from(self, proposed, errors="strict"):
        proposed = self.find_codec(proposed)
        if not proposed or (proposed, errors) in self.tried_encodings:
            return None
        self.tried_encodings.append((proposed, errors))
        markup = self.markup

        # Convert smart quotes to HTML if coming from an encoding
        # that might have them.
        if (self.smart_quotes_to is not None
            and proposed.lower() in self.ENCODINGS_WITH_SMART_QUOTES):
            smart_quotes_re = b"([\x80-\x9f])"
            smart_quotes_compiled = re.compile(smart_quotes_re)
            markup = smart_quotes_compiled.sub(self._sub_ms_char, markup)

        try:
            #print "Trying to convert document to %s (errors=%s)" % (
            #    proposed, errors)
            u = self._to_unicode(markup, proposed, errors)
            self.markup = u
            self.original_encoding = proposed
        except Exception as e:
            #print "That didn't work!"
            #print e
            return None
        #print "Correct encoding: %s" % proposed
        return self.markup

    def _to_unicode(self, data, encoding, errors="strict"):
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
        newdata = unicode(data, encoding, errors)
        return newdata

    def _detectEncoding(self, xml_data, is_html=False):
        """Given a document, tries to detect its XML encoding."""
        xml_encoding = sniffed_xml_encoding = None
        try:
            if xml_data[:4] == b'\x4c\x6f\xa7\x94':
                # EBCDIC
                xml_data = self._ebcdic_to_ascii(xml_data)
            elif xml_data[:4] == b'\x00\x3c\x00\x3f':
                # UTF-16BE
                sniffed_xml_encoding = 'utf-16be'
                xml_data = unicode(xml_data, 'utf-16be').encode('utf-8')
            elif (len(xml_data) >= 4) and (xml_data[:2] == b'\xfe\xff') \
                     and (xml_data[2:4] != b'\x00\x00'):
                # UTF-16BE with BOM
                sniffed_xml_encoding = 'utf-16be'
                xml_data = unicode(xml_data[2:], 'utf-16be').encode('utf-8')
            elif xml_data[:4] == b'\x3c\x00\x3f\x00':
                # UTF-16LE
                sniffed_xml_encoding = 'utf-16le'
                xml_data = unicode(xml_data, 'utf-16le').encode('utf-8')
            elif (len(xml_data) >= 4) and (xml_data[:2] == b'\xff\xfe') and \
                     (xml_data[2:4] != b'\x00\x00'):
                # UTF-16LE with BOM
                sniffed_xml_encoding = 'utf-16le'
                xml_data = unicode(xml_data[2:], 'utf-16le').encode('utf-8')
            elif xml_data[:4] == b'\x00\x00\x00\x3c':
                # UTF-32BE
                sniffed_xml_encoding = 'utf-32be'
                xml_data = unicode(xml_data, 'utf-32be').encode('utf-8')
            elif xml_data[:4] == b'\x3c\x00\x00\x00':
                # UTF-32LE
                sniffed_xml_encoding = 'utf-32le'
                xml_data = unicode(xml_data, 'utf-32le').encode('utf-8')
            elif xml_data[:4] == b'\x00\x00\xfe\xff':
                # UTF-32BE with BOM
                sniffed_xml_encoding = 'utf-32be'
                xml_data = unicode(xml_data[4:], 'utf-32be').encode('utf-8')
            elif xml_data[:4] == b'\xff\xfe\x00\x00':
                # UTF-32LE with BOM
                sniffed_xml_encoding = 'utf-32le'
                xml_data = unicode(xml_data[4:], 'utf-32le').encode('utf-8')
            elif xml_data[:3] == b'\xef\xbb\xbf':
                # UTF-8 with BOM
                sniffed_xml_encoding = 'utf-8'
                xml_data = unicode(xml_data[3:], 'utf-8').encode('utf-8')
            else:
                sniffed_xml_encoding = 'ascii'
                pass
        except:
            xml_encoding_match = None
        xml_encoding_match = xml_encoding_re.match(xml_data)
        if not xml_encoding_match and is_html:
            xml_encoding_match = html_meta_re.search(xml_data)
        if xml_encoding_match is not None:
            xml_encoding = xml_encoding_match.groups()[0].decode(
                'ascii').lower()
            if is_html:
                self.declared_html_encoding = xml_encoding
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
        if not charset:
            return charset
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
            c.EBCDIC_TO_ASCII_MAP = string.maketrans(
            ''.join(map(chr, list(range(256)))), ''.join(map(chr, emap)))
        return s.translate(c.EBCDIC_TO_ASCII_MAP)

    # A partial mapping of ISO-Latin-1 to HTML entities/XML numeric entities.
    MS_CHARS = {b'\x80': ('euro', '20AC'),
                b'\x81': ' ',
                b'\x82': ('sbquo', '201A'),
                b'\x83': ('fnof', '192'),
                b'\x84': ('bdquo', '201E'),
                b'\x85': ('hellip', '2026'),
                b'\x86': ('dagger', '2020'),
                b'\x87': ('Dagger', '2021'),
                b'\x88': ('circ', '2C6'),
                b'\x89': ('permil', '2030'),
                b'\x8A': ('Scaron', '160'),
                b'\x8B': ('lsaquo', '2039'),
                b'\x8C': ('OElig', '152'),
                b'\x8D': '?',
                b'\x8E': ('#x17D', '17D'),
                b'\x8F': '?',
                b'\x90': '?',
                b'\x91': ('lsquo', '2018'),
                b'\x92': ('rsquo', '2019'),
                b'\x93': ('ldquo', '201C'),
                b'\x94': ('rdquo', '201D'),
                b'\x95': ('bull', '2022'),
                b'\x96': ('ndash', '2013'),
                b'\x97': ('mdash', '2014'),
                b'\x98': ('tilde', '2DC'),
                b'\x99': ('trade', '2122'),
                b'\x9a': ('scaron', '161'),
                b'\x9b': ('rsaquo', '203A'),
                b'\x9c': ('oelig', '153'),
                b'\x9d': '?',
                b'\x9e': ('#x17E', '17E'),
                b'\x9f': ('Yuml', ''),}

    # A parochial partial mapping of ISO-Latin-1 to ASCII. Contains
    # horrors like stripping diacritical marks to turn á into a, but also
    # contains non-horrors like turning “ into ".
    MS_CHARS_TO_ASCII = {
        b'\x80' : 'EUR',
        b'\x81' : ' ',
        b'\x82' : ',',
        b'\x83' : 'f',
        b'\x84' : ',,',
        b'\x85' : '...',
        b'\x86' : '+',
        b'\x87' : '++',
        b'\x88' : '^',
        b'\x89' : '%',
        b'\x8a' : 'S',
        b'\x8b' : '<',
        b'\x8c' : 'OE',
        b'\x8d' : '?',
        b'\x8e' : 'Z',
        b'\x8f' : '?',
        b'\x90' : '?',
        b'\x91' : "'",
        b'\x92' : "'",
        b'\x93' : '"',
        b'\x94' : '"',
        b'\x95' : '*',
        b'\x96' : '-',
        b'\x97' : '--',
        b'\x98' : '~',
        b'\x99' : '(TM)',
        b'\x9a' : 's',
        b'\x9b' : '>',
        b'\x9c' : 'oe',
        b'\x9d' : '?',
        b'\x9e' : 'z',
        b'\x9f' : 'Y',
        b'\xa0' : ' ',
        b'\xa1' : '!',
        b'\xa2' : 'c',
        b'\xa3' : 'GBP',
        b'\xa4' : '$', #This approximation is especially parochial--this is the
                       #generic currency symbol.
        b'\xa5' : 'YEN',
        b'\xa6' : '|',
        b'\xa7' : 'S',
        b'\xa8' : '..',
        b'\xa9' : '',
        b'\xaa' : '(th)',
        b'\xab' : '<<',
        b'\xac' : '!',
        b'\xad' : ' ',
        b'\xae' : '(R)',
        b'\xaf' : '-',
        b'\xb0' : 'o',
        b'\xb1' : '+-',
        b'\xb2' : '2',
        b'\xb3' : '3',
        b'\xb4' : ("'", 'acute'),
        b'\xb5' : 'u',
        b'\xb6' : 'P',
        b'\xb7' : '*',
        b'\xb8' : ',',
        b'\xb9' : '1',
        b'\xba' : '(th)',
        b'\xbb' : '>>',
        b'\xbc' : '1/4',
        b'\xbd' : '1/2',
        b'\xbe' : '3/4',
        b'\xbf' : '?',
        b'\xc0' : 'A',
        b'\xc1' : 'A',
        b'\xc2' : 'A',
        b'\xc3' : 'A',
        b'\xc4' : 'A',
        b'\xc5' : 'A',
        b'\xc6' : 'AE',
        b'\xc7' : 'C',
        b'\xc8' : 'E',
        b'\xc9' : 'E',
        b'\xca' : 'E',
        b'\xcb' : 'E',
        b'\xcc' : 'I',
        b'\xcd' : 'I',
        b'\xce' : 'I',
        b'\xcf' : 'I',
        b'\xd0' : 'D',
        b'\xd1' : 'N',
        b'\xd2' : 'O',
        b'\xd3' : 'O',
        b'\xd4' : 'O',
        b'\xd5' : 'O',
        b'\xd6' : 'O',
        b'\xd7' : '*',
        b'\xd8' : 'O',
        b'\xd9' : 'U',
        b'\xda' : 'U',
        b'\xdb' : 'U',
        b'\xdc' : 'U',
        b'\xdd' : 'Y',
        b'\xde' : 'b',
        b'\xdf' : 'B',
        b'\xe0' : 'a',
        b'\xe1' : 'a',
        b'\xe2' : 'a',
        b'\xe3' : 'a',
        b'\xe4' : 'a',
        b'\xe5' : 'a',
        b'\xe6' : 'ae',
        b'\xe7' : 'c',
        b'\xe8' : 'e',
        b'\xe9' : 'e',
        b'\xea' : 'e',
        b'\xeb' : 'e',
        b'\xec' : 'i',
        b'\xed' : 'i',
        b'\xee' : 'i',
        b'\xef' : 'i',
        b'\xf0' : 'o',
        b'\xf1' : 'n',
        b'\xf2' : 'o',
        b'\xf3' : 'o',
        b'\xf4' : 'o',
        b'\xf5' : 'o',
        b'\xf6' : 'o',
        b'\xf7' : '/',
        b'\xf8' : 'o',
        b'\xf9' : 'u',
        b'\xfa' : 'u',
        b'\xfb' : 'u',
        b'\xfc' : 'u',
        b'\xfd' : 'y',
        b'\xfe' : 'b',
        b'\xff' : 'y',
        }

    # A map used when removing rogue Windows-1252/ISO-8859-1
    # characters in otherwise UTF-8 documents.
    #
    # Note that \x81, \x8d, \x8f, \x90, and \x9d are undefined in
    # Windows-1252.
    WINDOWS_1252_TO_UTF8 = {
        0x80 : b'\xe2\x82\xac', # €
        0x82 : b'\xe2\x80\x9a', # ‚
        0x83 : b'\xc6\x92',     # ƒ
        0x84 : b'\xe2\x80\x9e', # „
        0x85 : b'\xe2\x80\xa6', # …
        0x86 : b'\xe2\x80\xa0', # †
        0x87 : b'\xe2\x80\xa1', # ‡
        0x88 : b'\xcb\x86',     # ˆ
        0x89 : b'\xe2\x80\xb0', # ‰
        0x8a : b'\xc5\xa0',     # Š
        0x8b : b'\xe2\x80\xb9', # ‹
        0x8c : b'\xc5\x92',     # Œ
        0x8e : b'\xc5\xbd',     # Ž
        0x91 : b'\xe2\x80\x98', # ‘
        0x92 : b'\xe2\x80\x99', # ’
        0x93 : b'\xe2\x80\x9c', # “
        0x94 : b'\xe2\x80\x9d', # ”
        0x95 : b'\xe2\x80\xa2', # •
        0x96 : b'\xe2\x80\x93', # –
        0x97 : b'\xe2\x80\x94', # —
        0x98 : b'\xcb\x9c',     # ˜
        0x99 : b'\xe2\x84\xa2', # ™
        0x9a : b'\xc5\xa1',     # š
        0x9b : b'\xe2\x80\xba', # ›
        0x9c : b'\xc5\x93',     # œ
        0x9e : b'\xc5\xbe',     # ž
        0x9f : b'\xc5\xb8',     # Ÿ
        0xa0 : b'\xc2\xa0',     #  
        0xa1 : b'\xc2\xa1',     # ¡
        0xa2 : b'\xc2\xa2',     # ¢
        0xa3 : b'\xc2\xa3',     # £
        0xa4 : b'\xc2\xa4',     # ¤
        0xa5 : b'\xc2\xa5',     # ¥
        0xa6 : b'\xc2\xa6',     # ¦
        0xa7 : b'\xc2\xa7',     # §
        0xa8 : b'\xc2\xa8',     # ¨
        0xa9 : b'\xc2\xa9',     # ©
        0xaa : b'\xc2\xaa',     # ª
        0xab : b'\xc2\xab',     # «
        0xac : b'\xc2\xac',     # ¬
        0xad : b'\xc2\xad',     # ­
        0xae : b'\xc2\xae',     # ®
        0xaf : b'\xc2\xaf',     # ¯
        0xb0 : b'\xc2\xb0',     # °
        0xb1 : b'\xc2\xb1',     # ±
        0xb2 : b'\xc2\xb2',     # ²
        0xb3 : b'\xc2\xb3',     # ³
        0xb4 : b'\xc2\xb4',     # ´
        0xb5 : b'\xc2\xb5',     # µ
        0xb6 : b'\xc2\xb6',     # ¶
        0xb7 : b'\xc2\xb7',     # ·
        0xb8 : b'\xc2\xb8',     # ¸
        0xb9 : b'\xc2\xb9',     # ¹
        0xba : b'\xc2\xba',     # º
        0xbb : b'\xc2\xbb',     # »
        0xbc : b'\xc2\xbc',     # ¼
        0xbd : b'\xc2\xbd',     # ½
        0xbe : b'\xc2\xbe',     # ¾
        0xbf : b'\xc2\xbf',     # ¿
        0xc0 : b'\xc3\x80',     # À
        0xc1 : b'\xc3\x81',     # Á
        0xc2 : b'\xc3\x82',     # Â
        0xc3 : b'\xc3\x83',     # Ã
        0xc4 : b'\xc3\x84',     # Ä
        0xc5 : b'\xc3\x85',     # Å
        0xc6 : b'\xc3\x86',     # Æ
        0xc7 : b'\xc3\x87',     # Ç
        0xc8 : b'\xc3\x88',     # È
        0xc9 : b'\xc3\x89',     # É
        0xca : b'\xc3\x8a',     # Ê
        0xcb : b'\xc3\x8b',     # Ë
        0xcc : b'\xc3\x8c',     # Ì
        0xcd : b'\xc3\x8d',     # Í
        0xce : b'\xc3\x8e',     # Î
        0xcf : b'\xc3\x8f',     # Ï
        0xd0 : b'\xc3\x90',     # Ð
        0xd1 : b'\xc3\x91',     # Ñ
        0xd2 : b'\xc3\x92',     # Ò
        0xd3 : b'\xc3\x93',     # Ó
        0xd4 : b'\xc3\x94',     # Ô
        0xd5 : b'\xc3\x95',     # Õ
        0xd6 : b'\xc3\x96',     # Ö
        0xd7 : b'\xc3\x97',     # ×
        0xd8 : b'\xc3\x98',     # Ø
        0xd9 : b'\xc3\x99',     # Ù
        0xda : b'\xc3\x9a',     # Ú
        0xdb : b'\xc3\x9b',     # Û
        0xdc : b'\xc3\x9c',     # Ü
        0xdd : b'\xc3\x9d',     # Ý
        0xde : b'\xc3\x9e',     # Þ
        0xdf : b'\xc3\x9f',     # ß
        0xe0 : b'\xc3\xa0',     # à
        0xe1 : b'\xa1',     # á
        0xe2 : b'\xc3\xa2',     # â
        0xe3 : b'\xc3\xa3',     # ã
        0xe4 : b'\xc3\xa4',     # ä
        0xe5 : b'\xc3\xa5',     # å
        0xe6 : b'\xc3\xa6',     # æ
        0xe7 : b'\xc3\xa7',     # ç
        0xe8 : b'\xc3\xa8',     # è
        0xe9 : b'\xc3\xa9',     # é
        0xea : b'\xc3\xaa',     # ê
        0xeb : b'\xc3\xab',     # ë
        0xec : b'\xc3\xac',     # ì
        0xed : b'\xc3\xad',     # í
        0xee : b'\xc3\xae',     # î
        0xef : b'\xc3\xaf',     # ï
        0xf0 : b'\xc3\xb0',     # ð
        0xf1 : b'\xc3\xb1',     # ñ
        0xf2 : b'\xc3\xb2',     # ò
        0xf3 : b'\xc3\xb3',     # ó
        0xf4 : b'\xc3\xb4',     # ô
        0xf5 : b'\xc3\xb5',     # õ
        0xf6 : b'\xc3\xb6',     # ö
        0xf7 : b'\xc3\xb7',     # ÷
        0xf8 : b'\xc3\xb8',     # ø
        0xf9 : b'\xc3\xb9',     # ù
        0xfa : b'\xc3\xba',     # ú
        0xfb : b'\xc3\xbb',     # û
        0xfc : b'\xc3\xbc',     # ü
        0xfd : b'\xc3\xbd',     # ý
        0xfe : b'\xc3\xbe',     # þ
        }

    MULTIBYTE_MARKERS_AND_SIZES = [
        (0xc2, 0xdf, 2), # 2-byte characters start with a byte C2-DF
        (0xe0, 0xef, 3), # 3-byte characters start with E0-EF
        (0xf0, 0xf4, 4), # 4-byte characters start with F0-F4
        ]

    FIRST_MULTIBYTE_MARKER = MULTIBYTE_MARKERS_AND_SIZES[0][0]
    LAST_MULTIBYTE_MARKER = MULTIBYTE_MARKERS_AND_SIZES[-1][1]

    @classmethod
    def detwingle(cls, in_bytes, main_encoding="utf8",
                  embedded_encoding="windows-1252"):
        """Fix characters from one encoding embedded in some other encoding.

        Currently the only situation supported is Windows-1252 (or its
        subset ISO-8859-1), embedded in UTF-8.

        The input must be a bytestring. If you've already converted
        the document to Unicode, you're too late.

        The output is a bytestring in which `embedded_encoding`
        characters have been converted to their `main_encoding`
        equivalents.
        """
        if embedded_encoding.replace('_', '-').lower() not in (
            'windows-1252', 'windows_1252'):
            raise NotImplementedError(
                "Windows-1252 and ISO-8859-1 are the only currently supported "
                "embedded encodings.")

        if main_encoding.lower() not in ('utf8', 'utf-8'):
            raise NotImplementedError(
                "UTF-8 is the only currently supported main encoding.")

        byte_chunks = []

        chunk_start = 0
        pos = 0
        while pos < len(in_bytes):
            byte = in_bytes[pos]
            if not isinstance(byte, int):
                # Python 2.x
                byte = ord(byte)
            if (byte >= cls.FIRST_MULTIBYTE_MARKER
                and byte <= cls.LAST_MULTIBYTE_MARKER):
                # This is the start of a UTF-8 multibyte character. Skip
                # to the end.
                for start, end, size in cls.MULTIBYTE_MARKERS_AND_SIZES:
                    if byte >= start and byte <= end:
                        pos += size
                        break
            elif byte >= 0x80 and byte in cls.WINDOWS_1252_TO_UTF8:
                # We found a Windows-1252 character!
                # Save the string up to this point as a chunk.
                byte_chunks.append(in_bytes[chunk_start:pos])

                # Now translate the Windows-1252 character into UTF-8
                # and add it as another, one-byte chunk.
                byte_chunks.append(cls.WINDOWS_1252_TO_UTF8[byte])
                pos += 1
                chunk_start = pos
            else:
                # Go on to the next character.
                pos += 1
        if chunk_start == 0:
            # The string is unchanged.
            return in_bytes
        else:
            # Store the final chunk.
            byte_chunks.append(in_bytes[chunk_start:])
        return b''.join(byte_chunks)


########NEW FILE########
__FILENAME__ = element
import collections
import re
import sys
import warnings
from bs4.dammit import EntitySubstitution

DEFAULT_OUTPUT_ENCODING = "utf-8"
PY3K = (sys.version_info[0] > 2)

whitespace_re = re.compile("\s+")

def _alias(attr):
    """Alias one attribute name to another for backward compatibility"""
    @property
    def alias(self):
        return getattr(self, attr)

    @alias.setter
    def alias(self):
        return setattr(self, attr)
    return alias


class NamespacedAttribute(unicode):

    def __new__(cls, prefix, name, namespace=None):
        if name is None:
            obj = unicode.__new__(cls, prefix)
        else:
            obj = unicode.__new__(cls, prefix + ":" + name)
        obj.prefix = prefix
        obj.name = name
        obj.namespace = namespace
        return obj

class AttributeValueWithCharsetSubstitution(unicode):
    """A stand-in object for a character encoding specified in HTML."""

class CharsetMetaAttributeValue(AttributeValueWithCharsetSubstitution):
    """A generic stand-in for the value of a meta tag's 'charset' attribute.

    When Beautiful Soup parses the markup '<meta charset="utf8">', the
    value of the 'charset' attribute will be one of these objects.
    """

    def __new__(cls, original_value):
        obj = unicode.__new__(cls, original_value)
        obj.original_value = original_value
        return obj

    def encode(self, encoding):
        return encoding


class ContentMetaAttributeValue(AttributeValueWithCharsetSubstitution):
    """A generic stand-in for the value of a meta tag's 'content' attribute.

    When Beautiful Soup parses the markup:
     <meta http-equiv="content-type" content="text/html; charset=utf8">

    The value of the 'content' attribute will be one of these objects.
    """

    CHARSET_RE = re.compile("((^|;)\s*charset=)([^;]*)", re.M)

    def __new__(cls, original_value):
        match = cls.CHARSET_RE.search(original_value)
        if match is None:
            # No substitution necessary.
            return unicode.__new__(unicode, original_value)

        obj = unicode.__new__(cls, original_value)
        obj.original_value = original_value
        return obj

    def encode(self, encoding):
        def rewrite(match):
            return match.group(1) + encoding
        return self.CHARSET_RE.sub(rewrite, self.original_value)


class PageElement(object):
    """Contains the navigational information for some part of the page
    (either a tag or a piece of text)"""

    # There are five possible values for the "formatter" argument passed in
    # to methods like encode() and prettify():
    #
    # "html" - All Unicode characters with corresponding HTML entities
    #   are converted to those entities on output.
    # "minimal" - Bare ampersands and angle brackets are converted to
    #   XML entities: &amp; &lt; &gt;
    # None - The null formatter. Unicode characters are never
    #   converted to entities.  This is not recommended, but it's
    #   faster than "minimal".
    # A function - This function will be called on every string that
    #  needs to undergo entity substition
    FORMATTERS = {
        "html" : EntitySubstitution.substitute_html,
        "minimal" : EntitySubstitution.substitute_xml,
        None : None
        }

    @classmethod
    def format_string(self, s, formatter='minimal'):
        """Format the given string using the given formatter."""
        if not callable(formatter):
            formatter = self.FORMATTERS.get(
                formatter, EntitySubstitution.substitute_xml)
        if formatter is None:
            output = s
        else:
            output = formatter(s)
        return output

    def setup(self, parent=None, previous_element=None):
        """Sets up the initial relations between this element and
        other elements."""
        self.parent = parent
        self.previous_element = previous_element
        if previous_element is not None:
            self.previous_element.next_element = self
        self.next_element = None
        self.previous_sibling = None
        self.next_sibling = None
        if self.parent is not None and self.parent.contents:
            self.previous_sibling = self.parent.contents[-1]
            self.previous_sibling.next_sibling = self

    nextSibling = _alias("next_sibling")  # BS3
    previousSibling = _alias("previous_sibling")  # BS3

    def replace_with(self, replace_with):
        if replace_with is self:
            return
        if replace_with is self.parent:
            raise ValueError("Cannot replace a Tag with its parent.")
        old_parent = self.parent
        my_index = self.parent.index(self)
        self.extract()
        old_parent.insert(my_index, replace_with)
        return self
    replaceWith = replace_with  # BS3

    def unwrap(self):
        my_parent = self.parent
        my_index = self.parent.index(self)
        self.extract()
        for child in reversed(self.contents[:]):
            my_parent.insert(my_index, child)
        return self
    replace_with_children = unwrap
    replaceWithChildren = unwrap  # BS3

    def wrap(self, wrap_inside):
        me = self.replace_with(wrap_inside)
        wrap_inside.append(me)
        return wrap_inside

    def extract(self):
        """Destructively rips this element out of the tree."""
        if self.parent is not None:
            del self.parent.contents[self.parent.index(self)]

        #Find the two elements that would be next to each other if
        #this element (and any children) hadn't been parsed. Connect
        #the two.
        last_child = self._last_descendant()
        next_element = last_child.next_element

        if self.previous_element is not None:
            self.previous_element.next_element = next_element
        if next_element is not None:
            next_element.previous_element = self.previous_element
        self.previous_element = None
        last_child.next_element = None

        self.parent = None
        if self.previous_sibling is not None:
            self.previous_sibling.next_sibling = self.next_sibling
        if self.next_sibling is not None:
            self.next_sibling.previous_sibling = self.previous_sibling
        self.previous_sibling = self.next_sibling = None
        return self

    def _last_descendant(self):
        "Finds the last element beneath this object to be parsed."
        last_child = self
        while hasattr(last_child, 'contents') and last_child.contents:
            last_child = last_child.contents[-1]
        return last_child
    # BS3: Not part of the API!
    _lastRecursiveChild = _last_descendant

    def insert(self, position, new_child):
        if new_child is self:
            raise ValueError("Cannot insert a tag into itself.")
        if (isinstance(new_child, basestring)
            and not isinstance(new_child, NavigableString)):
            new_child = NavigableString(new_child)

        position = min(position, len(self.contents))
        if hasattr(new_child, 'parent') and new_child.parent is not None:
            # We're 'inserting' an element that's already one
            # of this object's children.
            if new_child.parent is self:
                current_index = self.index(new_child)
                if current_index < position:
                    # We're moving this element further down the list
                    # of this object's children. That means that when
                    # we extract this element, our target index will
                    # jump down one.
                    position -= 1
            new_child.extract()

        new_child.parent = self
        previous_child = None
        if position == 0:
            new_child.previous_sibling = None
            new_child.previous_element = self
        else:
            previous_child = self.contents[position - 1]
            new_child.previous_sibling = previous_child
            new_child.previous_sibling.next_sibling = new_child
            new_child.previous_element = previous_child._last_descendant()
        if new_child.previous_element is not None:
            new_child.previous_element.next_element = new_child

        new_childs_last_element = new_child._last_descendant()

        if position >= len(self.contents):
            new_child.next_sibling = None

            parent = self
            parents_next_sibling = None
            while parents_next_sibling is None and parent is not None:
                parents_next_sibling = parent.next_sibling
                parent = parent.parent
                if parents_next_sibling is not None:
                    # We found the element that comes next in the document.
                    break
            if parents_next_sibling is not None:
                new_childs_last_element.next_element = parents_next_sibling
            else:
                # The last element of this tag is the last element in
                # the document.
                new_childs_last_element.next_element = None
        else:
            next_child = self.contents[position]
            new_child.next_sibling = next_child
            if new_child.next_sibling is not None:
                new_child.next_sibling.previous_sibling = new_child
            new_childs_last_element.next_element = next_child

        if new_childs_last_element.next_element is not None:
            new_childs_last_element.next_element.previous_element = new_childs_last_element
        self.contents.insert(position, new_child)

    def append(self, tag):
        """Appends the given tag to the contents of this tag."""
        self.insert(len(self.contents), tag)

    def insert_before(self, predecessor):
        """Makes the given element the immediate predecessor of this one.

        The two elements will have the same parent, and the given element
        will be immediately before this one.
        """
        if self is predecessor:
            raise ValueError("Can't insert an element before itself.")
        parent = self.parent
        if parent is None:
            raise ValueError(
                "Element has no parent, so 'before' has no meaning.")
        # Extract first so that the index won't be screwed up if they
        # are siblings.
        if isinstance(predecessor, PageElement):
            predecessor.extract()
        index = parent.index(self)
        parent.insert(index, predecessor)

    def insert_after(self, successor):
        """Makes the given element the immediate successor of this one.

        The two elements will have the same parent, and the given element
        will be immediately after this one.
        """
        if self is successor:
            raise ValueError("Can't insert an element after itself.")
        parent = self.parent
        if parent is None:
            raise ValueError(
                "Element has no parent, so 'after' has no meaning.")
        # Extract first so that the index won't be screwed up if they
        # are siblings.
        if isinstance(successor, PageElement):
            successor.extract()
        index = parent.index(self)
        parent.insert(index+1, successor)

    def find_next(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the first item that matches the given criteria and
        appears after this Tag in the document."""
        return self._find_one(self.find_all_next, name, attrs, text, **kwargs)
    findNext = find_next  # BS3

    def find_all_next(self, name=None, attrs={}, text=None, limit=None,
                    **kwargs):
        """Returns all items that match the given criteria and appear
        after this Tag in the document."""
        return self._find_all(name, attrs, text, limit, self.next_elements,
                             **kwargs)
    findAllNext = find_all_next  # BS3

    def find_next_sibling(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the closest sibling to this Tag that matches the
        given criteria and appears after this Tag in the document."""
        return self._find_one(self.find_next_siblings, name, attrs, text,
                             **kwargs)
    findNextSibling = find_next_sibling  # BS3

    def find_next_siblings(self, name=None, attrs={}, text=None, limit=None,
                           **kwargs):
        """Returns the siblings of this Tag that match the given
        criteria and appear after this Tag in the document."""
        return self._find_all(name, attrs, text, limit,
                              self.next_siblings, **kwargs)
    findNextSiblings = find_next_siblings   # BS3
    fetchNextSiblings = find_next_siblings  # BS2

    def find_previous(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the first item that matches the given criteria and
        appears before this Tag in the document."""
        return self._find_one(
            self.find_all_previous, name, attrs, text, **kwargs)
    findPrevious = find_previous  # BS3

    def find_all_previous(self, name=None, attrs={}, text=None, limit=None,
                        **kwargs):
        """Returns all items that match the given criteria and appear
        before this Tag in the document."""
        return self._find_all(name, attrs, text, limit, self.previous_elements,
                           **kwargs)
    findAllPrevious = find_all_previous  # BS3
    fetchPrevious = find_all_previous    # BS2

    def find_previous_sibling(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the closest sibling to this Tag that matches the
        given criteria and appears before this Tag in the document."""
        return self._find_one(self.find_previous_siblings, name, attrs, text,
                             **kwargs)
    findPreviousSibling = find_previous_sibling  # BS3

    def find_previous_siblings(self, name=None, attrs={}, text=None,
                               limit=None, **kwargs):
        """Returns the siblings of this Tag that match the given
        criteria and appear before this Tag in the document."""
        return self._find_all(name, attrs, text, limit,
                              self.previous_siblings, **kwargs)
    findPreviousSiblings = find_previous_siblings   # BS3
    fetchPreviousSiblings = find_previous_siblings  # BS2

    def find_parent(self, name=None, attrs={}, **kwargs):
        """Returns the closest parent of this Tag that matches the given
        criteria."""
        # NOTE: We can't use _find_one because findParents takes a different
        # set of arguments.
        r = None
        l = self.find_parents(name, attrs, 1)
        if l:
            r = l[0]
        return r
    findParent = find_parent  # BS3

    def find_parents(self, name=None, attrs={}, limit=None, **kwargs):
        """Returns the parents of this Tag that match the given
        criteria."""

        return self._find_all(name, attrs, None, limit, self.parents,
                             **kwargs)
    findParents = find_parents   # BS3
    fetchParents = find_parents  # BS2

    @property
    def next(self):
        return self.next_element

    @property
    def previous(self):
        return self.previous_element

    #These methods do the real heavy lifting.

    def _find_one(self, method, name, attrs, text, **kwargs):
        r = None
        l = method(name, attrs, text, 1, **kwargs)
        if l:
            r = l[0]
        return r

    def _find_all(self, name, attrs, text, limit, generator, **kwargs):
        "Iterates over a generator looking for things that match."

        if isinstance(name, SoupStrainer):
            strainer = name
        elif text is None and not limit and not attrs and not kwargs:
            # Optimization to find all tags.
            if name is True or name is None:
                return [element for element in generator
                        if isinstance(element, Tag)]
            # Optimization to find all tags with a given name.
            elif isinstance(name, basestring):
                return [element for element in generator
                        if isinstance(element, Tag) and element.name == name]
            else:
                strainer = SoupStrainer(name, attrs, text, **kwargs)
        else:
            # Build a SoupStrainer
            strainer = SoupStrainer(name, attrs, text, **kwargs)
        results = ResultSet(strainer)
        while True:
            try:
                i = next(generator)
            except StopIteration:
                break
            if i:
                found = strainer.search(i)
                if found:
                    results.append(found)
                    if limit and len(results) >= limit:
                        break
        return results

    #These generators can be used to navigate starting from both
    #NavigableStrings and Tags.
    @property
    def next_elements(self):
        i = self.next_element
        while i is not None:
            yield i
            i = i.next_element

    @property
    def next_siblings(self):
        i = self.next_sibling
        while i is not None:
            yield i
            i = i.next_sibling

    @property
    def previous_elements(self):
        i = self.previous_element
        while i is not None:
            yield i
            i = i.previous_element

    @property
    def previous_siblings(self):
        i = self.previous_sibling
        while i is not None:
            yield i
            i = i.previous_sibling

    @property
    def parents(self):
        i = self.parent
        while i is not None:
            yield i
            i = i.parent

    # Methods for supporting CSS selectors.

    tag_name_re = re.compile('^[a-z0-9]+$')

    # /^(\w+)\[(\w+)([=~\|\^\$\*]?)=?"?([^\]"]*)"?\]$/
    #   \---/  \---/\-------------/    \-------/
    #     |      |         |               |
    #     |      |         |           The value
    #     |      |    ~,|,^,$,* or =
    #     |   Attribute
    #    Tag
    attribselect_re = re.compile(
        r'^(?P<tag>\w+)?\[(?P<attribute>\w+)(?P<operator>[=~\|\^\$\*]?)' +
        r'=?"?(?P<value>[^\]"]*)"?\]$'
        )

    def _attr_value_as_string(self, value, default=None):
        """Force an attribute value into a string representation.

        A multi-valued attribute will be converted into a
        space-separated stirng.
        """
        value = self.get(value, default)
        if isinstance(value, list) or isinstance(value, tuple):
            value =" ".join(value)
        return value

    def _attribute_checker(self, operator, attribute, value=''):
        """Create a function that performs a CSS selector operation.

        Takes an operator, attribute and optional value. Returns a
        function that will return True for elements that match that
        combination.
        """
        if operator == '=':
            # string representation of `attribute` is equal to `value`
            return lambda el: el._attr_value_as_string(attribute) == value
        elif operator == '~':
            # space-separated list representation of `attribute`
            # contains `value`
            def _includes_value(element):
                attribute_value = element.get(attribute, [])
                if not isinstance(attribute_value, list):
                    attribute_value = attribute_value.split()
                return value in attribute_value
            return _includes_value
        elif operator == '^':
            # string representation of `attribute` starts with `value`
            return lambda el: el._attr_value_as_string(
                attribute, '').startswith(value)
        elif operator == '$':
            # string represenation of `attribute` ends with `value`
            return lambda el: el._attr_value_as_string(
                attribute, '').endswith(value)
        elif operator == '*':
            # string representation of `attribute` contains `value`
            return lambda el: value in el._attr_value_as_string(attribute, '')
        elif operator == '|':
            # string representation of `attribute` is either exactly
            # `value` or starts with `value` and then a dash.
            def _is_or_starts_with_dash(element):
                attribute_value = element._attr_value_as_string(attribute, '')
                return (attribute_value == value or attribute_value.startswith(
                        value + '-'))
            return _is_or_starts_with_dash
        else:
            return lambda el: el.has_attr(attribute)

    def select(self, selector):
        """Perform a CSS selection operation on the current element."""
        tokens = selector.split()
        current_context = [self]
        for index, token in enumerate(tokens):
            if tokens[index - 1] == '>':
                # already found direct descendants in last step. skip this
                # step.
                continue
            m = self.attribselect_re.match(token)
            if m is not None:
                # Attribute selector
                tag, attribute, operator, value = m.groups()
                if not tag:
                    tag = True
                checker = self._attribute_checker(operator, attribute, value)
                found = []
                for context in current_context:
                    found.extend(
                        [el for el in context.find_all(tag) if checker(el)])
                current_context = found
                continue

            if '#' in token:
                # ID selector
                tag, id = token.split('#', 1)
                if tag == "":
                    tag = True
                el = current_context[0].find(tag, {'id': id})
                if el is None:
                    return [] # No match
                current_context = [el]
                continue

            if '.' in token:
                # Class selector
                tag_name, klass = token.split('.', 1)
                if not tag_name:
                    tag_name = True
                classes = set(klass.split('.'))
                found = []
                def classes_match(tag):
                    if tag_name is not True and tag.name != tag_name:
                        return False
                    if not tag.has_attr('class'):
                        return False
                    return classes.issubset(tag['class'])
                for context in current_context:
                    found.extend(context.find_all(classes_match))
                current_context = found
                continue

            if token == '*':
                # Star selector
                found = []
                for context in current_context:
                    found.extend(context.findAll(True))
                current_context = found
                continue

            if token == '>':
                # Child selector
                tag = tokens[index + 1]
                if not tag:
                    tag = True

                found = []
                for context in current_context:
                    found.extend(context.find_all(tag, recursive=False))
                current_context = found
                continue

            # Here we should just have a regular tag
            if not self.tag_name_re.match(token):
                return []
            found = []
            for context in current_context:
                found.extend(context.findAll(token))
            current_context = found
        return current_context

    # Old non-property versions of the generators, for backwards
    # compatibility with BS3.
    def nextGenerator(self):
        return self.next_elements

    def nextSiblingGenerator(self):
        return self.next_siblings

    def previousGenerator(self):
        return self.previous_elements

    def previousSiblingGenerator(self):
        return self.previous_siblings

    def parentGenerator(self):
        return self.parents


class NavigableString(unicode, PageElement):

    PREFIX = ''
    SUFFIX = ''

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
        return (unicode(self),)

    def __getattr__(self, attr):
        """text.string gives you text. This is for backwards
        compatibility for Navigable*String, but for CData* it lets you
        get the string without the CData wrapper."""
        if attr == 'string':
            return self
        else:
            raise AttributeError(
                "'%s' object has no attribute '%s'" % (
                    self.__class__.__name__, attr))

    def output_ready(self, formatter="minimal"):
        output = self.format_string(self, formatter)
        return self.PREFIX + output + self.SUFFIX


class PreformattedString(NavigableString):
    """A NavigableString not subject to the normal formatting rules.

    The string will be passed into the formatter (to trigger side effects),
    but the return value will be ignored.
    """

    def output_ready(self, formatter="minimal"):
        """CData strings are passed into the formatter.
        But the return value is ignored."""
        self.format_string(self, formatter)
        return self.PREFIX + self + self.SUFFIX

class CData(PreformattedString):

    PREFIX = u'<![CDATA['
    SUFFIX = u']]>'

class ProcessingInstruction(PreformattedString):

    PREFIX = u'<?'
    SUFFIX = u'?>'

class Comment(PreformattedString):

    PREFIX = u'<!--'
    SUFFIX = u'-->'


class Declaration(PreformattedString):
    PREFIX = u'<!'
    SUFFIX = u'!>'


class Doctype(PreformattedString):

    @classmethod
    def for_name_and_ids(cls, name, pub_id, system_id):
        value = name
        if pub_id is not None:
            value += ' PUBLIC "%s"' % pub_id
            if system_id is not None:
                value += ' "%s"' % system_id
        elif system_id is not None:
            value += ' SYSTEM "%s"' % system_id

        return Doctype(value)

    PREFIX = u'<!DOCTYPE '
    SUFFIX = u'>\n'


class Tag(PageElement):

    """Represents a found HTML tag with its attributes and contents."""

    def __init__(self, parser=None, builder=None, name=None, namespace=None,
                 prefix=None, attrs=None, parent=None, previous=None):
        "Basic constructor."

        if parser is None:
            self.parser_class = None
        else:
            # We don't actually store the parser object: that lets extracted
            # chunks be garbage-collected.
            self.parser_class = parser.__class__
        if name is None:
            raise ValueError("No value provided for new tag's name.")
        self.name = name
        self.namespace = namespace
        self.prefix = prefix
        if attrs is None:
            attrs = {}
        elif builder.cdata_list_attributes:
            attrs = builder._replace_cdata_list_attribute_values(
                self.name, attrs)
        else:
            attrs = dict(attrs)
        self.attrs = attrs
        self.contents = []
        self.setup(parent, previous)
        self.hidden = False

        # Set up any substitutions, such as the charset in a META tag.
        if builder is not None:
            builder.set_up_substitutions(self)
            self.can_be_empty_element = builder.can_be_empty_element(name)
        else:
            self.can_be_empty_element = False

    parserClass = _alias("parser_class")  # BS3

    @property
    def is_empty_element(self):
        """Is this tag an empty-element tag? (aka a self-closing tag)

        A tag that has contents is never an empty-element tag.

        A tag that has no contents may or may not be an empty-element
        tag. It depends on the builder used to create the tag. If the
        builder has a designated list of empty-element tags, then only
        a tag whose name shows up in that list is considered an
        empty-element tag.

        If the builder has no designated list of empty-element tags,
        then any tag with no contents is an empty-element tag.
        """
        return len(self.contents) == 0 and self.can_be_empty_element
    isSelfClosing = is_empty_element  # BS3

    @property
    def string(self):
        """Convenience property to get the single string within this tag.

        :Return: If this tag has a single string child, return value
         is that string. If this tag has no children, or more than one
         child, return value is None. If this tag has one child tag,
         return value is the 'string' attribute of the child tag,
         recursively.
        """
        if len(self.contents) != 1:
            return None
        child = self.contents[0]
        if isinstance(child, NavigableString):
            return child
        return child.string

    @string.setter
    def string(self, string):
        self.clear()
        self.append(string.__class__(string))

    def _all_strings(self, strip=False):
        """Yield all child strings, possibly stripping them."""
        for descendant in self.descendants:
            if not isinstance(descendant, NavigableString):
                continue
            if strip:
                descendant = descendant.strip()
                if len(descendant) == 0:
                    continue
            yield descendant
    strings = property(_all_strings)

    @property
    def stripped_strings(self):
        for string in self._all_strings(True):
            yield string

    def get_text(self, separator=u"", strip=False):
        """
        Get all child strings, concatenated using the given separator.
        """
        return separator.join([s for s in self._all_strings(strip)])
    getText = get_text
    text = property(get_text)

    def decompose(self):
        """Recursively destroys the contents of this tree."""
        self.extract()
        i = self
        while i is not None:
            next = i.next_element
            i.__dict__.clear()
            i = next

    def clear(self, decompose=False):
        """
        Extract all children. If decompose is True, decompose instead.
        """
        if decompose:
            for element in self.contents[:]:
                if isinstance(element, Tag):
                    element.decompose()
                else:
                    element.extract()
        else:
            for element in self.contents[:]:
                element.extract()

    def index(self, element):
        """
        Find the index of a child by identity, not value. Avoids issues with
        tag.contents.index(element) getting the index of equal elements.
        """
        for i, child in enumerate(self.contents):
            if child is element:
                return i
        raise ValueError("Tag.index: element not in tag")

    def get(self, key, default=None):
        """Returns the value of the 'key' attribute for the tag, or
        the value given for 'default' if it doesn't have that
        attribute."""
        return self.attrs.get(key, default)

    def has_attr(self, key):
        return key in self.attrs

    def __hash__(self):
        return str(self).__hash__()

    def __getitem__(self, key):
        """tag[key] returns the value of the 'key' attribute for the tag,
        and throws an exception if it's not there."""
        return self.attrs[key]

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
        self.attrs[key] = value

    def __delitem__(self, key):
        "Deleting tag[key] deletes all 'key' attributes for the tag."
        self.attrs.pop(key, None)

    def __call__(self, *args, **kwargs):
        """Calling a tag like a function is the same as calling its
        find_all() method. Eg. tag('a') returns a list of all the A tags
        found within this tag."""
        return self.find_all(*args, **kwargs)

    def __getattr__(self, tag):
        #print "Getattr %s.%s" % (self.__class__, tag)
        if len(tag) > 3 and tag.endswith('Tag'):
            # BS3: soup.aTag -> "soup.find("a")
            tag_name = tag[:-3]
            warnings.warn(
                '.%sTag is deprecated, use .find("%s") instead.' % (
                    tag_name, tag_name))
            return self.find(tag_name)
        # We special case contents to avoid recursion.
        elif not tag.startswith("__") and not tag=="contents":
            return self.find(tag)
        raise AttributeError(
            "'%s' object has no attribute '%s'" % (self.__class__, tag))

    def __eq__(self, other):
        """Returns true iff this tag has the same name, the same attributes,
        and the same contents (recursively) as the given tag."""
        if self is other:
            return True
        if (not hasattr(other, 'name') or
            not hasattr(other, 'attrs') or
            not hasattr(other, 'contents') or
            self.name != other.name or
            self.attrs != other.attrs or
            len(self) != len(other)):
            return False
        for i, my_child in enumerate(self.contents):
            if my_child != other.contents[i]:
                return False
        return True

    def __ne__(self, other):
        """Returns true iff this tag is not identical to the other tag,
        as defined in __eq__."""
        return not self == other

    def __repr__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        """Renders this tag as a string."""
        return self.encode(encoding)

    def __unicode__(self):
        return self.decode()

    def __str__(self):
        return self.encode()

    if PY3K:
        __str__ = __repr__ = __unicode__

    def encode(self, encoding=DEFAULT_OUTPUT_ENCODING,
               indent_level=None, formatter="minimal",
               errors="xmlcharrefreplace"):
        # Turn the data structure into Unicode, then encode the
        # Unicode.
        u = self.decode(indent_level, encoding, formatter)
        return u.encode(encoding, errors)

    def decode(self, indent_level=None,
               eventual_encoding=DEFAULT_OUTPUT_ENCODING,
               formatter="minimal"):
        """Returns a Unicode representation of this tag and its contents.

        :param eventual_encoding: The tag is destined to be
           encoded into this encoding. This method is _not_
           responsible for performing that encoding. This information
           is passed in so that it can be substituted in if the
           document contains a <META> tag that mentions the document's
           encoding.
        """
        attrs = []
        if self.attrs:
            for key, val in sorted(self.attrs.items()):
                if val is None:
                    decoded = key
                else:
                    if isinstance(val, list) or isinstance(val, tuple):
                        val = ' '.join(val)
                    elif not isinstance(val, basestring):
                        val = unicode(val)
                    elif (
                        isinstance(val, AttributeValueWithCharsetSubstitution)
                        and eventual_encoding is not None):
                        val = val.encode(eventual_encoding)

                    text = self.format_string(val, formatter)
                    decoded = (
                        unicode(key) + '='
                        + EntitySubstitution.quoted_attribute_value(text))
                attrs.append(decoded)
        close = ''
        closeTag = ''

        prefix = ''
        if self.prefix:
            prefix = self.prefix + ":"

        if self.is_empty_element:
            close = '/'
        else:
            closeTag = '</%s%s>' % (prefix, self.name)

        pretty_print = (indent_level is not None)
        if pretty_print:
            space = (' ' * (indent_level - 1))
            indent_contents = indent_level + 1
        else:
            space = ''
            indent_contents = None
        contents = self.decode_contents(
            indent_contents, eventual_encoding, formatter)

        if self.hidden:
            # This is the 'document root' object.
            s = contents
        else:
            s = []
            attribute_string = ''
            if attrs:
                attribute_string = ' ' + ' '.join(attrs)
            if pretty_print:
                s.append(space)
            s.append('<%s%s%s%s>' % (
                    prefix, self.name, attribute_string, close))
            if pretty_print:
                s.append("\n")
            s.append(contents)
            if pretty_print and contents and contents[-1] != "\n":
                s.append("\n")
            if pretty_print and closeTag:
                s.append(space)
            s.append(closeTag)
            if pretty_print and closeTag and self.next_sibling:
                s.append("\n")
            s = ''.join(s)
        return s

    def prettify(self, encoding=None, formatter="minimal"):
        if encoding is None:
            return self.decode(True, formatter=formatter)
        else:
            return self.encode(encoding, True, formatter=formatter)

    def decode_contents(self, indent_level=None,
                       eventual_encoding=DEFAULT_OUTPUT_ENCODING,
                       formatter="minimal"):
        """Renders the contents of this tag as a Unicode string.

        :param eventual_encoding: The tag is destined to be
           encoded into this encoding. This method is _not_
           responsible for performing that encoding. This information
           is passed in so that it can be substituted in if the
           document contains a <META> tag that mentions the document's
           encoding.
        """
        pretty_print = (indent_level is not None)
        s = []
        for c in self:
            text = None
            if isinstance(c, NavigableString):
                text = c.output_ready(formatter)
            elif isinstance(c, Tag):
                s.append(c.decode(indent_level, eventual_encoding,
                                  formatter))
            if text and indent_level:
                text = text.strip()
            if text:
                if pretty_print:
                    s.append(" " * (indent_level - 1))
                s.append(text)
                if pretty_print:
                    s.append("\n")
        return ''.join(s)

    def encode_contents(
        self, indent_level=None, encoding=DEFAULT_OUTPUT_ENCODING,
        formatter="minimal"):
        """Renders the contents of this tag as a bytestring."""
        contents = self.decode_contents(indent_level, encoding, formatter)
        return contents.encode(encoding)

    # Old method for BS3 compatibility
    def renderContents(self, encoding=DEFAULT_OUTPUT_ENCODING,
                       prettyPrint=False, indentLevel=0):
        if not prettyPrint:
            indentLevel = None
        return self.encode_contents(
            indent_level=indentLevel, encoding=encoding)

    #Soup methods

    def find(self, name=None, attrs={}, recursive=True, text=None,
             **kwargs):
        """Return only the first child of this Tag matching the given
        criteria."""
        r = None
        l = self.find_all(name, attrs, recursive, text, 1, **kwargs)
        if l:
            r = l[0]
        return r
    findChild = find

    def find_all(self, name=None, attrs={}, recursive=True, text=None,
                 limit=None, **kwargs):
        """Extracts a list of Tag objects that match the given
        criteria.  You can specify the name of the Tag and any
        attributes you want the Tag to have.

        The value of a key-value pair in the 'attrs' map can be a
        string, a list of strings, a regular expression object, or a
        callable that takes a string and returns whether or not the
        string matches for some custom definition of 'matches'. The
        same is true of the tag name."""

        generator = self.descendants
        if not recursive:
            generator = self.children
        return self._find_all(name, attrs, text, limit, generator, **kwargs)
    findAll = find_all       # BS3
    findChildren = find_all  # BS2

    #Generator methods
    @property
    def children(self):
        # return iter() to make the purpose of the method clear
        return iter(self.contents)  # XXX This seems to be untested.

    @property
    def descendants(self):
        if not len(self.contents):
            return
        stopNode = self._last_descendant().next_element
        current = self.contents[0]
        while current is not stopNode:
            yield current
            current = current.next_element

    # Old names for backwards compatibility
    def childGenerator(self):
        return self.children

    def recursiveChildGenerator(self):
        return self.descendants

    # This was kind of misleading because has_key() (attributes) was
    # different from __in__ (contents). has_key() is gone in Python 3,
    # anyway.
    has_key = has_attr

# Next, a couple classes to represent queries and their results.
class SoupStrainer(object):
    """Encapsulates a number of ways of matching a markup element (tag or
    text)."""

    def __init__(self, name=None, attrs={}, text=None, **kwargs):
        self.name = self._normalize_search_value(name)
        if not isinstance(attrs, dict):
            # Treat a non-dict value for attrs as a search for the 'class'
            # attribute.
            kwargs['class'] = attrs
            attrs = None

        if 'class_' in kwargs:
            # Treat class_="foo" as a search for the 'class'
            # attribute, overriding any non-dict value for attrs.
            kwargs['class'] = kwargs['class_']
            del kwargs['class_']

        if kwargs:
            if attrs:
                attrs = attrs.copy()
                attrs.update(kwargs)
            else:
                attrs = kwargs
        normalized_attrs = {}
        for key, value in attrs.items():
            normalized_attrs[key] = self._normalize_search_value(value)

        self.attrs = normalized_attrs
        self.text = self._normalize_search_value(text)

    def _normalize_search_value(self, value):
        # Leave it alone if it's a Unicode string, a callable, a
        # regular expression, a boolean, or None.
        if (isinstance(value, unicode) or callable(value) or hasattr(value, 'match')
            or isinstance(value, bool) or value is None):
            return value

        # If it's a bytestring, convert it to Unicode, treating it as UTF-8.
        if isinstance(value, bytes):
            return value.decode("utf8")

        # If it's listlike, convert it into a list of strings.
        if hasattr(value, '__iter__'):
            new_value = []
            for v in value:
                if (hasattr(v, '__iter__') and not isinstance(v, bytes)
                    and not isinstance(v, unicode)):
                    # This is almost certainly the user's mistake. In the
                    # interests of avoiding infinite loops, we'll let
                    # it through as-is rather than doing a recursive call.
                    new_value.append(v)
                else:
                    new_value.append(self._normalize_search_value(v))
            return new_value

        # Otherwise, convert it into a Unicode string.
        # The unicode(str()) thing is so this will do the same thing on Python 2
        # and Python 3.
        return unicode(str(value))

    def __str__(self):
        if self.text:
            return self.text
        else:
            return "%s|%s" % (self.name, self.attrs)

    def search_tag(self, markup_name=None, markup_attrs={}):
        found = None
        markup = None
        if isinstance(markup_name, Tag):
            markup = markup_name
            markup_attrs = markup
        call_function_with_tag_data = (
            isinstance(self.name, collections.Callable)
            and not isinstance(markup_name, Tag))

        if ((not self.name)
            or call_function_with_tag_data
            or (markup and self._matches(markup, self.name))
            or (not markup and self._matches(markup_name, self.name))):
            if call_function_with_tag_data:
                match = self.name(markup_name, markup_attrs)
            else:
                match = True
                markup_attr_map = None
                for attr, match_against in list(self.attrs.items()):
                    if not markup_attr_map:
                        if hasattr(markup_attrs, 'get'):
                            markup_attr_map = markup_attrs
                        else:
                            markup_attr_map = {}
                            for k, v in markup_attrs:
                                markup_attr_map[k] = v
                    attr_value = markup_attr_map.get(attr)
                    if not self._matches(attr_value, match_against):
                        match = False
                        break
            if match:
                if markup:
                    found = markup
                else:
                    found = markup_name
        if found and self.text and not self._matches(found.string, self.text):
            found = None
        return found
    searchTag = search_tag

    def search(self, markup):
        # print 'looking for %s in %s' % (self, markup)
        found = None
        # If given a list of items, scan it for a text element that
        # matches.
        if hasattr(markup, '__iter__') and not isinstance(markup, (Tag, basestring)):
            for element in markup:
                if isinstance(element, NavigableString) \
                       and self.search(element):
                    found = element
                    break
        # If it's a Tag, make sure its name or attributes match.
        # Don't bother with Tags if we're searching for text.
        elif isinstance(markup, Tag):
            if not self.text or self.name or self.attrs:
                found = self.search_tag(markup)
        # If it's text, make sure the text matches.
        elif isinstance(markup, NavigableString) or \
                 isinstance(markup, basestring):
            if not self.name and not self.attrs and self._matches(markup, self.text):
                found = markup
        else:
            raise Exception(
                "I don't know how to match against a %s" % markup.__class__)
        return found

    def _matches(self, markup, match_against):
        # print u"Matching %s against %s" % (markup, match_against)
        result = False
        if isinstance(markup, list) or isinstance(markup, tuple):
            # This should only happen when searching a multi-valued attribute
            # like 'class'.
            if (isinstance(match_against, unicode)
                and ' ' in match_against):
                # A bit of a special case. If they try to match "foo
                # bar" on a multivalue attribute's value, only accept
                # the literal value "foo bar"
                #
                # XXX This is going to be pretty slow because we keep
                # splitting match_against. But it shouldn't come up
                # too often.
                return (whitespace_re.split(match_against) == markup)
            else:
                for item in markup:
                    if self._matches(item, match_against):
                        return True
                return False

        if match_against is True:
            # True matches any non-None value.
            return markup is not None

        if isinstance(match_against, collections.Callable):
            return match_against(markup)

        # Custom callables take the tag as an argument, but all
        # other ways of matching match the tag name as a string.
        if isinstance(markup, Tag):
            markup = markup.name

        # Ensure that `markup` is either a Unicode string, or None.
        markup = self._normalize_search_value(markup)

        if markup is None:
            # None matches None, False, an empty string, an empty list, and so on.
            return not match_against

        if isinstance(match_against, unicode):
            # Exact string match
            return markup == match_against

        if hasattr(match_against, 'match'):
            # Regexp match
            return match_against.search(markup)

        if hasattr(match_against, '__iter__'):
            # The markup must be an exact match against something
            # in the iterable.
            return markup in match_against


class ResultSet(list):
    """A ResultSet is just a list that keeps track of the SoupStrainer
    that created it."""
    def __init__(self, source):
        list.__init__([])
        self.source = source

########NEW FILE########
__FILENAME__ = testing
"""Helper classes for tests."""

import copy
import functools
import unittest
from unittest import TestCase
from bs4 import BeautifulSoup
from bs4.element import (
    CharsetMetaAttributeValue,
    Comment,
    ContentMetaAttributeValue,
    Doctype,
    SoupStrainer,
)

from bs4.builder import HTMLParserTreeBuilder
default_builder = HTMLParserTreeBuilder


class SoupTest(unittest.TestCase):

    @property
    def default_builder(self):
        return default_builder()

    def soup(self, markup, **kwargs):
        """Build a Beautiful Soup object from markup."""
        builder = kwargs.pop('builder', self.default_builder)
        return BeautifulSoup(markup, builder=builder, **kwargs)

    def document_for(self, markup):
        """Turn an HTML fragment into a document.

        The details depend on the builder.
        """
        return self.default_builder.test_fragment_to_document(markup)

    def assertSoupEquals(self, to_parse, compare_parsed_to=None):
        builder = self.default_builder
        obj = BeautifulSoup(to_parse, builder=builder)
        if compare_parsed_to is None:
            compare_parsed_to = to_parse

        self.assertEqual(obj.decode(), self.document_for(compare_parsed_to))


class HTMLTreeBuilderSmokeTest(object):

    """A basic test of a treebuilder's competence.

    Any HTML treebuilder, present or future, should be able to pass
    these tests. With invalid markup, there's room for interpretation,
    and different parsers can handle it differently. But with the
    markup in these tests, there's not much room for interpretation.
    """

    def assertDoctypeHandled(self, doctype_fragment):
        """Assert that a given doctype string is handled correctly."""
        doctype_str, soup = self._document_with_doctype(doctype_fragment)

        # Make sure a Doctype object was created.
        doctype = soup.contents[0]
        self.assertEqual(doctype.__class__, Doctype)
        self.assertEqual(doctype, doctype_fragment)
        self.assertEqual(str(soup)[:len(doctype_str)], doctype_str)

        # Make sure that the doctype was correctly associated with the
        # parse tree and that the rest of the document parsed.
        self.assertEqual(soup.p.contents[0], 'foo')

    def _document_with_doctype(self, doctype_fragment):
        """Generate and parse a document with the given doctype."""
        doctype = '<!DOCTYPE %s>' % doctype_fragment
        markup = doctype + '\n<p>foo</p>'
        soup = self.soup(markup)
        return doctype, soup

    def test_normal_doctypes(self):
        """Make sure normal, everyday HTML doctypes are handled correctly."""
        self.assertDoctypeHandled("html")
        self.assertDoctypeHandled(
            'html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"')

    def test_public_doctype_with_url(self):
        doctype = 'html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"'
        self.assertDoctypeHandled(doctype)

    def test_system_doctype(self):
        self.assertDoctypeHandled('foo SYSTEM "http://www.example.com/"')

    def test_namespaced_system_doctype(self):
        # We can handle a namespaced doctype with a system ID.
        self.assertDoctypeHandled('xsl:stylesheet SYSTEM "htmlent.dtd"')

    def test_namespaced_public_doctype(self):
        # Test a namespaced doctype with a public id.
        self.assertDoctypeHandled('xsl:stylesheet PUBLIC "htmlent.dtd"')

    def test_real_xhtml_document(self):
        """A real XHTML document should come out more or less the same as it went in."""
        markup = b"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN">
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Hello.</title></head>
<body>Goodbye.</body>
</html>"""
        soup = self.soup(markup)
        self.assertEqual(
            soup.encode("utf-8").replace(b"\n", b""),
            markup.replace(b"\n", b""))

    def test_deepcopy(self):
        """Make sure you can copy the tree builder.

        This is important because the builder is part of a
        BeautifulSoup object, and we want to be able to copy that.
        """
        copy.deepcopy(self.default_builder)

    def test_p_tag_is_never_empty_element(self):
        """A <p> tag is never designated as an empty-element tag.

        Even if the markup shows it as an empty-element tag, it
        shouldn't be presented that way.
        """
        soup = self.soup("<p/>")
        self.assertFalse(soup.p.is_empty_element)
        self.assertEqual(str(soup.p), "<p></p>")

    def test_unclosed_tags_get_closed(self):
        """A tag that's not closed by the end of the document should be closed.

        This applies to all tags except empty-element tags.
        """
        self.assertSoupEquals("<p>", "<p></p>")
        self.assertSoupEquals("<b>", "<b></b>")

        self.assertSoupEquals("<br>", "<br/>")

    def test_br_is_always_empty_element_tag(self):
        """A <br> tag is designated as an empty-element tag.

        Some parsers treat <br></br> as one <br/> tag, some parsers as
        two tags, but it should always be an empty-element tag.
        """
        soup = self.soup("<br></br>")
        self.assertTrue(soup.br.is_empty_element)
        self.assertEqual(str(soup.br), "<br/>")

    def test_nested_formatting_elements(self):
        self.assertSoupEquals("<em><em></em></em>")

    def test_comment(self):
        # Comments are represented as Comment objects.
        markup = "<p>foo<!--foobar-->baz</p>"
        self.assertSoupEquals(markup)

        soup = self.soup(markup)
        comment = soup.find(text="foobar")
        self.assertEqual(comment.__class__, Comment)

    def test_preserved_whitespace_in_pre_and_textarea(self):
        """Whitespace must be preserved in <pre> and <textarea> tags."""
        self.assertSoupEquals("<pre>   </pre>")
        self.assertSoupEquals("<textarea> woo  </textarea>")

    def test_nested_inline_elements(self):
        """Inline elements can be nested indefinitely."""
        b_tag = "<b>Inside a B tag</b>"
        self.assertSoupEquals(b_tag)

        nested_b_tag = "<p>A <i>nested <b>tag</b></i></p>"
        self.assertSoupEquals(nested_b_tag)

        double_nested_b_tag = "<p>A <a>doubly <i>nested <b>tag</b></i></a></p>"
        self.assertSoupEquals(nested_b_tag)

    def test_nested_block_level_elements(self):
        """Block elements can be nested."""
        soup = self.soup('<blockquote><p><b>Foo</b></p></blockquote>')
        blockquote = soup.blockquote
        self.assertEqual(blockquote.p.b.string, 'Foo')
        self.assertEqual(blockquote.b.string, 'Foo')

    def test_correctly_nested_tables(self):
        """One table can go inside another one."""
        markup = ('<table id="1">'
                  '<tr>'
                  "<td>Here's another table:"
                  '<table id="2">'
                  '<tr><td>foo</td></tr>'
                  '</table></td>')

        self.assertSoupEquals(
            markup,
            '<table id="1"><tr><td>Here\'s another table:'
            '<table id="2"><tr><td>foo</td></tr></table>'
            '</td></tr></table>')

        self.assertSoupEquals(
            "<table><thead><tr><td>Foo</td></tr></thead>"
            "<tbody><tr><td>Bar</td></tr></tbody>"
            "<tfoot><tr><td>Baz</td></tr></tfoot></table>")

    def test_deeply_nested_multivalued_attribute(self):
        # html5lib can set the attributes of the same tag many times
        # as it rearranges the tree. This has caused problems with
        # multivalued attributes.
        markup = '<table><div><div class="css"></div></div></table>'
        soup = self.soup(markup)
        self.assertEqual(["css"], soup.div.div['class'])

    def test_angle_brackets_in_attribute_values_are_escaped(self):
        self.assertSoupEquals('<a b="<a>"></a>', '<a b="&lt;a&gt;"></a>')

    def test_entities_in_attributes_converted_to_unicode(self):
        expect = u'<p id="pi\N{LATIN SMALL LETTER N WITH TILDE}ata"></p>'
        self.assertSoupEquals('<p id="pi&#241;ata"></p>', expect)
        self.assertSoupEquals('<p id="pi&#xf1;ata"></p>', expect)
        self.assertSoupEquals('<p id="pi&ntilde;ata"></p>', expect)

    def test_entities_in_text_converted_to_unicode(self):
        expect = u'<p>pi\N{LATIN SMALL LETTER N WITH TILDE}ata</p>'
        self.assertSoupEquals("<p>pi&#241;ata</p>", expect)
        self.assertSoupEquals("<p>pi&#xf1;ata</p>", expect)
        self.assertSoupEquals("<p>pi&ntilde;ata</p>", expect)

    def test_quot_entity_converted_to_quotation_mark(self):
        self.assertSoupEquals("<p>I said &quot;good day!&quot;</p>",
                              '<p>I said "good day!"</p>')

    def test_out_of_range_entity(self):
        expect = u"\N{REPLACEMENT CHARACTER}"
        self.assertSoupEquals("&#10000000000000;", expect)
        self.assertSoupEquals("&#x10000000000000;", expect)
        self.assertSoupEquals("&#1000000000;", expect)

    def test_basic_namespaces(self):
        """Parsers don't need to *understand* namespaces, but at the
        very least they should not choke on namespaces or lose
        data."""

        markup = b'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:mathml="http://www.w3.org/1998/Math/MathML" xmlns:svg="http://www.w3.org/2000/svg"><head></head><body><mathml:msqrt>4</mathml:msqrt><b svg:fill="red"></b></body></html>'
        soup = self.soup(markup)
        self.assertEqual(markup, soup.encode())
        html = soup.html
        self.assertEqual('http://www.w3.org/1999/xhtml', soup.html['xmlns'])
        self.assertEqual(
            'http://www.w3.org/1998/Math/MathML', soup.html['xmlns:mathml'])
        self.assertEqual(
            'http://www.w3.org/2000/svg', soup.html['xmlns:svg'])

    def test_multivalued_attribute_value_becomes_list(self):
        markup = b'<a class="foo bar">'
        soup = self.soup(markup)
        self.assertEqual(['foo', 'bar'], soup.a['class'])

    #
    # Generally speaking, tests below this point are more tests of
    # Beautiful Soup than tests of the tree builders. But parsers are
    # weird, so we run these tests separately for every tree builder
    # to detect any differences between them.
    #

    def test_soupstrainer(self):
        """Parsers should be able to work with SoupStrainers."""
        strainer = SoupStrainer("b")
        soup = self.soup("A <b>bold</b> <meta/> <i>statement</i>",
                         parse_only=strainer)
        self.assertEqual(soup.decode(), "<b>bold</b>")

    def test_single_quote_attribute_values_become_double_quotes(self):
        self.assertSoupEquals("<foo attr='bar'></foo>",
                              '<foo attr="bar"></foo>')

    def test_attribute_values_with_nested_quotes_are_left_alone(self):
        text = """<foo attr='bar "brawls" happen'>a</foo>"""
        self.assertSoupEquals(text)

    def test_attribute_values_with_double_nested_quotes_get_quoted(self):
        text = """<foo attr='bar "brawls" happen'>a</foo>"""
        soup = self.soup(text)
        soup.foo['attr'] = 'Brawls happen at "Bob\'s Bar"'
        self.assertSoupEquals(
            soup.foo.decode(),
            """<foo attr="Brawls happen at &quot;Bob\'s Bar&quot;">a</foo>""")

    def test_ampersand_in_attribute_value_gets_escaped(self):
        self.assertSoupEquals('<this is="really messed up & stuff"></this>',
                              '<this is="really messed up &amp; stuff"></this>')

        self.assertSoupEquals(
            '<a href="http://example.org?a=1&b=2;3">foo</a>',
            '<a href="http://example.org?a=1&amp;b=2;3">foo</a>')

    def test_escaped_ampersand_in_attribute_value_is_left_alone(self):
        self.assertSoupEquals('<a href="http://example.org?a=1&amp;b=2;3"></a>')

    def test_entities_in_strings_converted_during_parsing(self):
        # Both XML and HTML entities are converted to Unicode characters
        # during parsing.
        text = "<p>&lt;&lt;sacr&eacute;&#32;bleu!&gt;&gt;</p>"
        expected = u"<p>&lt;&lt;sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!&gt;&gt;</p>"
        self.assertSoupEquals(text, expected)

    def test_smart_quotes_converted_on_the_way_in(self):
        # Microsoft smart quotes are converted to Unicode characters during
        # parsing.
        quote = b"<p>\x91Foo\x92</p>"
        soup = self.soup(quote)
        self.assertEqual(
            soup.p.string,
            u"\N{LEFT SINGLE QUOTATION MARK}Foo\N{RIGHT SINGLE QUOTATION MARK}")

    def test_non_breaking_spaces_converted_on_the_way_in(self):
        soup = self.soup("<a>&nbsp;&nbsp;</a>")
        self.assertEqual(soup.a.string, u"\N{NO-BREAK SPACE}" * 2)

    def test_entities_converted_on_the_way_out(self):
        text = "<p>&lt;&lt;sacr&eacute;&#32;bleu!&gt;&gt;</p>"
        expected = u"<p>&lt;&lt;sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!&gt;&gt;</p>".encode("utf-8")
        soup = self.soup(text)
        self.assertEqual(soup.p.encode("utf-8"), expected)

    def test_real_iso_latin_document(self):
        # Smoke test of interrelated functionality, using an
        # easy-to-understand document.

        # Here it is in Unicode. Note that it claims to be in ISO-Latin-1.
        unicode_html = u'<html><head><meta content="text/html; charset=ISO-Latin-1" http-equiv="Content-type"/></head><body><p>Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!</p></body></html>'

        # That's because we're going to encode it into ISO-Latin-1, and use
        # that to test.
        iso_latin_html = unicode_html.encode("iso-8859-1")

        # Parse the ISO-Latin-1 HTML.
        soup = self.soup(iso_latin_html)
        # Encode it to UTF-8.
        result = soup.encode("utf-8")

        # What do we expect the result to look like? Well, it would
        # look like unicode_html, except that the META tag would say
        # UTF-8 instead of ISO-Latin-1.
        expected = unicode_html.replace("ISO-Latin-1", "utf-8")

        # And, of course, it would be in UTF-8, not Unicode.
        expected = expected.encode("utf-8")

        # Ta-da!
        self.assertEqual(result, expected)

    def test_real_shift_jis_document(self):
        # Smoke test to make sure the parser can handle a document in
        # Shift-JIS encoding, without choking.
        shift_jis_html = (
            b'<html><head></head><body><pre>'
            b'\x82\xb1\x82\xea\x82\xcdShift-JIS\x82\xc5\x83R\x81[\x83f'
            b'\x83B\x83\x93\x83O\x82\xb3\x82\xea\x82\xbd\x93\xfa\x96{\x8c'
            b'\xea\x82\xcc\x83t\x83@\x83C\x83\x8b\x82\xc5\x82\xb7\x81B'
            b'</pre></body></html>')
        unicode_html = shift_jis_html.decode("shift-jis")
        soup = self.soup(unicode_html)

        # Make sure the parse tree is correctly encoded to various
        # encodings.
        self.assertEqual(soup.encode("utf-8"), unicode_html.encode("utf-8"))
        self.assertEqual(soup.encode("euc_jp"), unicode_html.encode("euc_jp"))

    def test_real_hebrew_document(self):
        # A real-world test to make sure we can convert ISO-8859-9 (a
        # Hebrew encoding) to UTF-8.
        hebrew_document = b'<html><head><title>Hebrew (ISO 8859-8) in Visual Directionality</title></head><body><h1>Hebrew (ISO 8859-8) in Visual Directionality</h1>\xed\xe5\xec\xf9</body></html>'
        soup = self.soup(
            hebrew_document, from_encoding="iso8859-8")
        self.assertEqual(soup.original_encoding, 'iso8859-8')
        self.assertEqual(
            soup.encode('utf-8'),
            hebrew_document.decode("iso8859-8").encode("utf-8"))

    def test_meta_tag_reflects_current_encoding(self):
        # Here's the <meta> tag saying that a document is
        # encoded in Shift-JIS.
        meta_tag = ('<meta content="text/html; charset=x-sjis" '
                    'http-equiv="Content-type"/>')

        # Here's a document incorporating that meta tag.
        shift_jis_html = (
            '<html><head>\n%s\n'
            '<meta http-equiv="Content-language" content="ja"/>'
            '</head><body>Shift-JIS markup goes here.') % meta_tag
        soup = self.soup(shift_jis_html)

        # Parse the document, and the charset is seemingly unaffected.
        parsed_meta = soup.find('meta', {'http-equiv': 'Content-type'})
        content = parsed_meta['content']
        self.assertEqual('text/html; charset=x-sjis', content)

        # But that value is actually a ContentMetaAttributeValue object.
        self.assertTrue(isinstance(content, ContentMetaAttributeValue))

        # And it will take on a value that reflects its current
        # encoding.
        self.assertEqual('text/html; charset=utf8', content.encode("utf8"))

        # For the rest of the story, see TestSubstitutions in
        # test_tree.py.

    def test_html5_style_meta_tag_reflects_current_encoding(self):
        # Here's the <meta> tag saying that a document is
        # encoded in Shift-JIS.
        meta_tag = ('<meta id="encoding" charset="x-sjis" />')

        # Here's a document incorporating that meta tag.
        shift_jis_html = (
            '<html><head>\n%s\n'
            '<meta http-equiv="Content-language" content="ja"/>'
            '</head><body>Shift-JIS markup goes here.') % meta_tag
        soup = self.soup(shift_jis_html)

        # Parse the document, and the charset is seemingly unaffected.
        parsed_meta = soup.find('meta', id="encoding")
        charset = parsed_meta['charset']
        self.assertEqual('x-sjis', charset)

        # But that value is actually a CharsetMetaAttributeValue object.
        self.assertTrue(isinstance(charset, CharsetMetaAttributeValue))

        # And it will take on a value that reflects its current
        # encoding.
        self.assertEqual('utf8', charset.encode("utf8"))

    def test_tag_with_no_attributes_can_have_attributes_added(self):
        data = self.soup("<a>text</a>")
        data.a['foo'] = 'bar'
        self.assertEqual('<a foo="bar">text</a>', data.a.decode())

class XMLTreeBuilderSmokeTest(object):

    def test_docstring_generated(self):
        soup = self.soup("<root/>")
        self.assertEqual(
            soup.encode(), b'<?xml version="1.0" encoding="utf-8"?>\n<root/>')

    def test_real_xhtml_document(self):
        """A real XHTML document should come out *exactly* the same as it went in."""
        markup = b"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN">
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Hello.</title></head>
<body>Goodbye.</body>
</html>"""
        soup = self.soup(markup)
        self.assertEqual(
            soup.encode("utf-8"), markup)

    def test_popping_namespaced_tag(self):
        markup = '<rss xmlns:dc="foo"><dc:creator>b</dc:creator><dc:date>2012-07-02T20:33:42Z</dc:date><dc:rights>c</dc:rights><image>d</image></rss>'
        soup = self.soup(markup)
        self.assertEqual(
            unicode(soup.rss), markup)

    def test_docstring_includes_correct_encoding(self):
        soup = self.soup("<root/>")
        self.assertEqual(
            soup.encode("latin1"),
            b'<?xml version="1.0" encoding="latin1"?>\n<root/>')

    def test_large_xml_document(self):
        """A large XML document should come out the same as it went in."""
        markup = (b'<?xml version="1.0" encoding="utf-8"?>\n<root>'
                  + b'0' * (2**12)
                  + b'</root>')
        soup = self.soup(markup)
        self.assertEqual(soup.encode("utf-8"), markup)


    def test_tags_are_empty_element_if_and_only_if_they_are_empty(self):
        self.assertSoupEquals("<p>", "<p/>")
        self.assertSoupEquals("<p>foo</p>")

    def test_namespaces_are_preserved(self):
        markup = '<root xmlns:a="http://example.com/" xmlns:b="http://example.net/"><a:foo>This tag is in the a namespace</a:foo><b:foo>This tag is in the b namespace</b:foo></root>'
        soup = self.soup(markup)
        root = soup.root
        self.assertEqual("http://example.com/", root['xmlns:a'])
        self.assertEqual("http://example.net/", root['xmlns:b'])

    def test_closing_namespaced_tag(self):
        markup = '<p xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:date>20010504</dc:date></p>'
        soup = self.soup(markup)
        self.assertEqual(unicode(soup.p), markup)

    def test_namespaced_attributes(self):
        markup = '<foo xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><bar xsi:schemaLocation="http://www.example.com"/></foo>'
        soup = self.soup(markup)
        self.assertEqual(unicode(soup.foo), markup)

class HTML5TreeBuilderSmokeTest(HTMLTreeBuilderSmokeTest):
    """Smoke test for a tree builder that supports HTML5."""

    def test_real_xhtml_document(self):
        # Since XHTML is not HTML5, HTML5 parsers are not tested to handle
        # XHTML documents in any particular way.
        pass

    def test_html_tags_have_namespace(self):
        markup = "<a>"
        soup = self.soup(markup)
        self.assertEqual("http://www.w3.org/1999/xhtml", soup.a.namespace)

    def test_svg_tags_have_namespace(self):
        markup = '<svg><circle/></svg>'
        soup = self.soup(markup)
        namespace = "http://www.w3.org/2000/svg"
        self.assertEqual(namespace, soup.svg.namespace)
        self.assertEqual(namespace, soup.circle.namespace)


    def test_mathml_tags_have_namespace(self):
        markup = '<math><msqrt>5</msqrt></math>'
        soup = self.soup(markup)
        namespace = 'http://www.w3.org/1998/Math/MathML'
        self.assertEqual(namespace, soup.math.namespace)
        self.assertEqual(namespace, soup.msqrt.namespace)


def skipIf(condition, reason):
   def nothing(test, *args, **kwargs):
       return None

   def decorator(test_item):
       if condition:
           return nothing
       else:
           return test_item

   return decorator

########NEW FILE########
__FILENAME__ = test_builder_registry
"""Tests of the builder registry."""

import unittest

from bs4 import BeautifulSoup
from bs4.builder import (
    builder_registry as registry,
    HTMLParserTreeBuilder,
    TreeBuilderRegistry,
)

try:
    from bs4.builder import HTML5TreeBuilder
    HTML5LIB_PRESENT = True
except ImportError:
    HTML5LIB_PRESENT = False

try:
    from bs4.builder import (
        LXMLTreeBuilderForXML,
        LXMLTreeBuilder,
        )
    LXML_PRESENT = True
except ImportError:
    LXML_PRESENT = False


class BuiltInRegistryTest(unittest.TestCase):
    """Test the built-in registry with the default builders registered."""

    def test_combination(self):
        if LXML_PRESENT:
            self.assertEqual(registry.lookup('fast', 'html'),
                             LXMLTreeBuilder)

        if LXML_PRESENT:
            self.assertEqual(registry.lookup('permissive', 'xml'),
                             LXMLTreeBuilderForXML)
        self.assertEqual(registry.lookup('strict', 'html'),
                          HTMLParserTreeBuilder)
        if HTML5LIB_PRESENT:
            self.assertEqual(registry.lookup('html5lib', 'html'),
                              HTML5TreeBuilder)

    def test_lookup_by_markup_type(self):
        if LXML_PRESENT:
            self.assertEqual(registry.lookup('html'), LXMLTreeBuilder)
            self.assertEqual(registry.lookup('xml'), LXMLTreeBuilderForXML)
        else:
            self.assertEqual(registry.lookup('xml'), None)
            if HTML5LIB_PRESENT:
                self.assertEqual(registry.lookup('html'), HTML5TreeBuilder)
            else:
                self.assertEqual(registry.lookup('html'), HTMLParserTreeBuilder)

    def test_named_library(self):
        if LXML_PRESENT:
            self.assertEqual(registry.lookup('lxml', 'xml'),
                             LXMLTreeBuilderForXML)
            self.assertEqual(registry.lookup('lxml', 'html'),
                             LXMLTreeBuilder)
        if HTML5LIB_PRESENT:
            self.assertEqual(registry.lookup('html5lib'),
                              HTML5TreeBuilder)

        self.assertEqual(registry.lookup('html.parser'),
                          HTMLParserTreeBuilder)

    def test_beautifulsoup_constructor_does_lookup(self):
        # You can pass in a string.
        BeautifulSoup("", features="html")
        # Or a list of strings.
        BeautifulSoup("", features=["html", "fast"])

        # You'll get an exception if BS can't find an appropriate
        # builder.
        self.assertRaises(ValueError, BeautifulSoup,
                          "", features="no-such-feature")

class RegistryTest(unittest.TestCase):
    """Test the TreeBuilderRegistry class in general."""

    def setUp(self):
        self.registry = TreeBuilderRegistry()

    def builder_for_features(self, *feature_list):
        cls = type('Builder_' + '_'.join(feature_list),
                   (object,), {'features' : feature_list})

        self.registry.register(cls)
        return cls

    def test_register_with_no_features(self):
        builder = self.builder_for_features()

        # Since the builder advertises no features, you can't find it
        # by looking up features.
        self.assertEqual(self.registry.lookup('foo'), None)

        # But you can find it by doing a lookup with no features, if
        # this happens to be the only registered builder.
        self.assertEqual(self.registry.lookup(), builder)

    def test_register_with_features_makes_lookup_succeed(self):
        builder = self.builder_for_features('foo', 'bar')
        self.assertEqual(self.registry.lookup('foo'), builder)
        self.assertEqual(self.registry.lookup('bar'), builder)

    def test_lookup_fails_when_no_builder_implements_feature(self):
        builder = self.builder_for_features('foo', 'bar')
        self.assertEqual(self.registry.lookup('baz'), None)

    def test_lookup_gets_most_recent_registration_when_no_feature_specified(self):
        builder1 = self.builder_for_features('foo')
        builder2 = self.builder_for_features('bar')
        self.assertEqual(self.registry.lookup(), builder2)

    def test_lookup_fails_when_no_tree_builders_registered(self):
        self.assertEqual(self.registry.lookup(), None)

    def test_lookup_gets_most_recent_builder_supporting_all_features(self):
        has_one = self.builder_for_features('foo')
        has_the_other = self.builder_for_features('bar')
        has_both_early = self.builder_for_features('foo', 'bar', 'baz')
        has_both_late = self.builder_for_features('foo', 'bar', 'quux')
        lacks_one = self.builder_for_features('bar')
        has_the_other = self.builder_for_features('foo')

        # There are two builders featuring 'foo' and 'bar', but
        # the one that also features 'quux' was registered later.
        self.assertEqual(self.registry.lookup('foo', 'bar'),
                          has_both_late)

        # There is only one builder featuring 'foo', 'bar', and 'baz'.
        self.assertEqual(self.registry.lookup('foo', 'bar', 'baz'),
                          has_both_early)

    def test_lookup_fails_when_cannot_reconcile_requested_features(self):
        builder1 = self.builder_for_features('foo', 'bar')
        builder2 = self.builder_for_features('foo', 'baz')
        self.assertEqual(self.registry.lookup('bar', 'baz'), None)

########NEW FILE########
__FILENAME__ = test_docs
"Test harness for doctests."

# pylint: disable-msg=E0611,W0142

__metaclass__ = type
__all__ = [
    'additional_tests',
    ]

import atexit
import doctest
import os
#from pkg_resources import (
#    resource_filename, resource_exists, resource_listdir, cleanup_resources)
import unittest

DOCTEST_FLAGS = (
    doctest.ELLIPSIS |
    doctest.NORMALIZE_WHITESPACE |
    doctest.REPORT_NDIFF)


# def additional_tests():
#     "Run the doc tests (README.txt and docs/*, if any exist)"
#     doctest_files = [
#         os.path.abspath(resource_filename('bs4', 'README.txt'))]
#     if resource_exists('bs4', 'docs'):
#         for name in resource_listdir('bs4', 'docs'):
#             if name.endswith('.txt'):
#                 doctest_files.append(
#                     os.path.abspath(
#                         resource_filename('bs4', 'docs/%s' % name)))
#     kwargs = dict(module_relative=False, optionflags=DOCTEST_FLAGS)
#     atexit.register(cleanup_resources)
#     return unittest.TestSuite((
#         doctest.DocFileSuite(*doctest_files, **kwargs)))

########NEW FILE########
__FILENAME__ = test_html5lib
"""Tests to ensure that the html5lib tree builder generates good trees."""

import warnings

try:
    from bs4.builder import HTML5TreeBuilder
    HTML5LIB_PRESENT = True
except ImportError, e:
    HTML5LIB_PRESENT = False
from bs4.element import SoupStrainer
from bs4.testing import (
    HTML5TreeBuilderSmokeTest,
    SoupTest,
    skipIf,
)

@skipIf(
    not HTML5LIB_PRESENT,
    "html5lib seems not to be present, not testing its tree builder.")
class HTML5LibBuilderSmokeTest(SoupTest, HTML5TreeBuilderSmokeTest):
    """See ``HTML5TreeBuilderSmokeTest``."""

    @property
    def default_builder(self):
        return HTML5TreeBuilder()

    def test_soupstrainer(self):
        # The html5lib tree builder does not support SoupStrainers.
        strainer = SoupStrainer("b")
        markup = "<p>A <b>bold</b> statement.</p>"
        with warnings.catch_warnings(record=True) as w:
            soup = self.soup(markup, parse_only=strainer)
        self.assertEqual(
            soup.decode(), self.document_for(markup))

        self.assertTrue(
            "the html5lib tree builder doesn't support parse_only" in
            str(w[0].message))

    def test_correctly_nested_tables(self):
        """html5lib inserts <tbody> tags where other parsers don't."""
        markup = ('<table id="1">'
                  '<tr>'
                  "<td>Here's another table:"
                  '<table id="2">'
                  '<tr><td>foo</td></tr>'
                  '</table></td>')

        self.assertSoupEquals(
            markup,
            '<table id="1"><tbody><tr><td>Here\'s another table:'
            '<table id="2"><tbody><tr><td>foo</td></tr></tbody></table>'
            '</td></tr></tbody></table>')

        self.assertSoupEquals(
            "<table><thead><tr><td>Foo</td></tr></thead>"
            "<tbody><tr><td>Bar</td></tr></tbody>"
            "<tfoot><tr><td>Baz</td></tr></tfoot></table>")

########NEW FILE########
__FILENAME__ = test_htmlparser
"""Tests to ensure that the html.parser tree builder generates good
trees."""

from bs4.testing import SoupTest, HTMLTreeBuilderSmokeTest
from bs4.builder import HTMLParserTreeBuilder

class HTMLParserTreeBuilderSmokeTest(SoupTest, HTMLTreeBuilderSmokeTest):

    @property
    def default_builder(self):
        return HTMLParserTreeBuilder()

    def test_namespaced_system_doctype(self):
        # html.parser can't handle namespaced doctypes, so skip this one.
        pass

    def test_namespaced_public_doctype(self):
        # html.parser can't handle namespaced doctypes, so skip this one.
        pass

########NEW FILE########
__FILENAME__ = test_lxml
"""Tests to ensure that the lxml tree builder generates good trees."""

import re
import warnings

try:
    from bs4.builder import LXMLTreeBuilder, LXMLTreeBuilderForXML
    LXML_PRESENT = True
except ImportError, e:
    LXML_PRESENT = False

from bs4 import (
    BeautifulSoup,
    BeautifulStoneSoup,
    )
from bs4.element import Comment, Doctype, SoupStrainer
from bs4.testing import skipIf
from bs4.tests import test_htmlparser
from bs4.testing import (
    HTMLTreeBuilderSmokeTest,
    XMLTreeBuilderSmokeTest,
    SoupTest,
    skipIf,
)

@skipIf(
    not LXML_PRESENT,
    "lxml seems not to be present, not testing its tree builder.")
class LXMLTreeBuilderSmokeTest(SoupTest, HTMLTreeBuilderSmokeTest):
    """See ``HTMLTreeBuilderSmokeTest``."""

    @property
    def default_builder(self):
        return LXMLTreeBuilder()

    def test_out_of_range_entity(self):
        self.assertSoupEquals(
            "<p>foo&#10000000000000;bar</p>", "<p>foobar</p>")
        self.assertSoupEquals(
            "<p>foo&#x10000000000000;bar</p>", "<p>foobar</p>")
        self.assertSoupEquals(
            "<p>foo&#1000000000;bar</p>", "<p>foobar</p>")

    def test_beautifulstonesoup_is_xml_parser(self):
        # Make sure that the deprecated BSS class uses an xml builder
        # if one is installed.
        with warnings.catch_warnings(record=False) as w:
            soup = BeautifulStoneSoup("<b />")
            self.assertEqual(u"<b/>", unicode(soup.b))

    def test_real_xhtml_document(self):
        """lxml strips the XML definition from an XHTML doc, which is fine."""
        markup = b"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN">
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Hello.</title></head>
<body>Goodbye.</body>
</html>"""
        soup = self.soup(markup)
        self.assertEqual(
            soup.encode("utf-8").replace(b"\n", b''),
            markup.replace(b'\n', b'').replace(
                b'<?xml version="1.0" encoding="utf-8"?>', b''))


@skipIf(
    not LXML_PRESENT,
    "lxml seems not to be present, not testing its XML tree builder.")
class LXMLXMLTreeBuilderSmokeTest(SoupTest, XMLTreeBuilderSmokeTest):
    """See ``HTMLTreeBuilderSmokeTest``."""

    @property
    def default_builder(self):
        return LXMLTreeBuilderForXML()


########NEW FILE########
__FILENAME__ = test_soup
# -*- coding: utf-8 -*-
"""Tests of Beautiful Soup as a whole."""

import logging
import unittest
import sys
from bs4 import (
    BeautifulSoup,
    BeautifulStoneSoup,
)
from bs4.element import (
    CharsetMetaAttributeValue,
    ContentMetaAttributeValue,
    SoupStrainer,
    NamespacedAttribute,
    )
import bs4.dammit
from bs4.dammit import EntitySubstitution, UnicodeDammit
from bs4.testing import (
    SoupTest,
    skipIf,
)
import warnings

try:
    from bs4.builder import LXMLTreeBuilder, LXMLTreeBuilderForXML
    LXML_PRESENT = True
except ImportError, e:
    LXML_PRESENT = False

PYTHON_2_PRE_2_7 = (sys.version_info < (2,7))
PYTHON_3_PRE_3_2 = (sys.version_info[0] == 3 and sys.version_info < (3,2))

class TestDeprecatedConstructorArguments(SoupTest):

    def test_parseOnlyThese_renamed_to_parse_only(self):
        with warnings.catch_warnings(record=True) as w:
            soup = self.soup("<a><b></b></a>", parseOnlyThese=SoupStrainer("b"))
        msg = str(w[0].message)
        self.assertTrue("parseOnlyThese" in msg)
        self.assertTrue("parse_only" in msg)
        self.assertEqual(b"<b></b>", soup.encode())

    def test_fromEncoding_renamed_to_from_encoding(self):
        with warnings.catch_warnings(record=True) as w:
            utf8 = b"\xc3\xa9"
            soup = self.soup(utf8, fromEncoding="utf8")
        msg = str(w[0].message)
        self.assertTrue("fromEncoding" in msg)
        self.assertTrue("from_encoding" in msg)
        self.assertEqual("utf8", soup.original_encoding)

    def test_unrecognized_keyword_argument(self):
        self.assertRaises(
            TypeError, self.soup, "<a>", no_such_argument=True)

    @skipIf(
        not LXML_PRESENT,
        "lxml not present, not testing BeautifulStoneSoup.")
    def test_beautifulstonesoup(self):
        with warnings.catch_warnings(record=True) as w:
            soup = BeautifulStoneSoup("<markup>")
            self.assertTrue(isinstance(soup, BeautifulSoup))
            self.assertTrue("BeautifulStoneSoup class is deprecated")

class TestSelectiveParsing(SoupTest):

    def test_parse_with_soupstrainer(self):
        markup = "No<b>Yes</b><a>No<b>Yes <c>Yes</c></b>"
        strainer = SoupStrainer("b")
        soup = self.soup(markup, parse_only=strainer)
        self.assertEqual(soup.encode(), b"<b>Yes</b><b>Yes <c>Yes</c></b>")


class TestEntitySubstitution(unittest.TestCase):
    """Standalone tests of the EntitySubstitution class."""
    def setUp(self):
        self.sub = EntitySubstitution

    def test_simple_html_substitution(self):
        # Unicode characters corresponding to named HTML entites
        # are substituted, and no others.
        s = u"foo\u2200\N{SNOWMAN}\u00f5bar"
        self.assertEqual(self.sub.substitute_html(s),
                          u"foo&forall;\N{SNOWMAN}&otilde;bar")

    def test_smart_quote_substitution(self):
        # MS smart quotes are a common source of frustration, so we
        # give them a special test.
        quotes = b"\x91\x92foo\x93\x94"
        dammit = UnicodeDammit(quotes)
        self.assertEqual(self.sub.substitute_html(dammit.markup),
                          "&lsquo;&rsquo;foo&ldquo;&rdquo;")

    def test_xml_converstion_includes_no_quotes_if_make_quoted_attribute_is_false(self):
        s = 'Welcome to "my bar"'
        self.assertEqual(self.sub.substitute_xml(s, False), s)

    def test_xml_attribute_quoting_normally_uses_double_quotes(self):
        self.assertEqual(self.sub.substitute_xml("Welcome", True),
                          '"Welcome"')
        self.assertEqual(self.sub.substitute_xml("Bob's Bar", True),
                          '"Bob\'s Bar"')

    def test_xml_attribute_quoting_uses_single_quotes_when_value_contains_double_quotes(self):
        s = 'Welcome to "my bar"'
        self.assertEqual(self.sub.substitute_xml(s, True),
                          "'Welcome to \"my bar\"'")

    def test_xml_attribute_quoting_escapes_single_quotes_when_value_contains_both_single_and_double_quotes(self):
        s = 'Welcome to "Bob\'s Bar"'
        self.assertEqual(
            self.sub.substitute_xml(s, True),
            '"Welcome to &quot;Bob\'s Bar&quot;"')

    def test_xml_quotes_arent_escaped_when_value_is_not_being_quoted(self):
        quoted = 'Welcome to "Bob\'s Bar"'
        self.assertEqual(self.sub.substitute_xml(quoted), quoted)

    def test_xml_quoting_handles_angle_brackets(self):
        self.assertEqual(
            self.sub.substitute_xml("foo<bar>"),
            "foo&lt;bar&gt;")

    def test_xml_quoting_handles_ampersands(self):
        self.assertEqual(self.sub.substitute_xml("AT&T"), "AT&amp;T")

    def test_xml_quoting_ignores_ampersands_when_they_are_part_of_an_entity(self):
        self.assertEqual(
            self.sub.substitute_xml("&Aacute;T&T"),
            "&Aacute;T&amp;T")

    def test_quotes_not_html_substituted(self):
        """There's no need to do this except inside attribute values."""
        text = 'Bob\'s "bar"'
        self.assertEqual(self.sub.substitute_html(text), text)


class TestEncodingConversion(SoupTest):
    # Test Beautiful Soup's ability to decode and encode from various
    # encodings.

    def setUp(self):
        super(TestEncodingConversion, self).setUp()
        self.unicode_data = u'<html><head><meta charset="utf-8"/></head><body><foo>Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!</foo></body></html>'
        self.utf8_data = self.unicode_data.encode("utf-8")
        # Just so you know what it looks like.
        self.assertEqual(
            self.utf8_data,
            b'<html><head><meta charset="utf-8"/></head><body><foo>Sacr\xc3\xa9 bleu!</foo></body></html>')

    def test_ascii_in_unicode_out(self):
        # ASCII input is converted to Unicode. The original_encoding
        # attribute is set.
        ascii = b"<foo>a</foo>"
        soup_from_ascii = self.soup(ascii)
        unicode_output = soup_from_ascii.decode()
        self.assertTrue(isinstance(unicode_output, unicode))
        self.assertEqual(unicode_output, self.document_for(ascii.decode()))
        self.assertEqual(soup_from_ascii.original_encoding.lower(), "ascii")

    def test_unicode_in_unicode_out(self):
        # Unicode input is left alone. The original_encoding attribute
        # is not set.
        soup_from_unicode = self.soup(self.unicode_data)
        self.assertEqual(soup_from_unicode.decode(), self.unicode_data)
        self.assertEqual(soup_from_unicode.foo.string, u'Sacr\xe9 bleu!')
        self.assertEqual(soup_from_unicode.original_encoding, None)

    def test_utf8_in_unicode_out(self):
        # UTF-8 input is converted to Unicode. The original_encoding
        # attribute is set.
        soup_from_utf8 = self.soup(self.utf8_data)
        self.assertEqual(soup_from_utf8.decode(), self.unicode_data)
        self.assertEqual(soup_from_utf8.foo.string, u'Sacr\xe9 bleu!')

    def test_utf8_out(self):
        # The internal data structures can be encoded as UTF-8.
        soup_from_unicode = self.soup(self.unicode_data)
        self.assertEqual(soup_from_unicode.encode('utf-8'), self.utf8_data)

    @skipIf(
        PYTHON_2_PRE_2_7 or PYTHON_3_PRE_3_2,
        "Bad HTMLParser detected; skipping test of non-ASCII characters in attribute name.")
    def test_attribute_name_containing_unicode_characters(self):
        markup = u'<div><a \N{SNOWMAN}="snowman"></a></div>'
        self.assertEqual(self.soup(markup).div.encode("utf8"), markup.encode("utf8"))

class TestUnicodeDammit(unittest.TestCase):
    """Standalone tests of Unicode, Dammit."""

    def test_smart_quotes_to_unicode(self):
        markup = b"<foo>\x91\x92\x93\x94</foo>"
        dammit = UnicodeDammit(markup)
        self.assertEqual(
            dammit.unicode_markup, u"<foo>\u2018\u2019\u201c\u201d</foo>")

    def test_smart_quotes_to_xml_entities(self):
        markup = b"<foo>\x91\x92\x93\x94</foo>"
        dammit = UnicodeDammit(markup, smart_quotes_to="xml")
        self.assertEqual(
            dammit.unicode_markup, "<foo>&#x2018;&#x2019;&#x201C;&#x201D;</foo>")

    def test_smart_quotes_to_html_entities(self):
        markup = b"<foo>\x91\x92\x93\x94</foo>"
        dammit = UnicodeDammit(markup, smart_quotes_to="html")
        self.assertEqual(
            dammit.unicode_markup, "<foo>&lsquo;&rsquo;&ldquo;&rdquo;</foo>")

    def test_smart_quotes_to_ascii(self):
        markup = b"<foo>\x91\x92\x93\x94</foo>"
        dammit = UnicodeDammit(markup, smart_quotes_to="ascii")
        self.assertEqual(
            dammit.unicode_markup, """<foo>''""</foo>""")

    def test_detect_utf8(self):
        utf8 = b"\xc3\xa9"
        dammit = UnicodeDammit(utf8)
        self.assertEqual(dammit.unicode_markup, u'\xe9')
        self.assertEqual(dammit.original_encoding.lower(), 'utf-8')

    def test_convert_hebrew(self):
        hebrew = b"\xed\xe5\xec\xf9"
        dammit = UnicodeDammit(hebrew, ["iso-8859-8"])
        self.assertEqual(dammit.original_encoding.lower(), 'iso-8859-8')
        self.assertEqual(dammit.unicode_markup, u'\u05dd\u05d5\u05dc\u05e9')

    def test_dont_see_smart_quotes_where_there_are_none(self):
        utf_8 = b"\343\202\261\343\203\274\343\202\277\343\202\244 Watch"
        dammit = UnicodeDammit(utf_8)
        self.assertEqual(dammit.original_encoding.lower(), 'utf-8')
        self.assertEqual(dammit.unicode_markup.encode("utf-8"), utf_8)

    def test_ignore_inappropriate_codecs(self):
        utf8_data = u"Räksmörgås".encode("utf-8")
        dammit = UnicodeDammit(utf8_data, ["iso-8859-8"])
        self.assertEqual(dammit.original_encoding.lower(), 'utf-8')

    def test_ignore_invalid_codecs(self):
        utf8_data = u"Räksmörgås".encode("utf-8")
        for bad_encoding in ['.utf8', '...', 'utF---16.!']:
            dammit = UnicodeDammit(utf8_data, [bad_encoding])
            self.assertEqual(dammit.original_encoding.lower(), 'utf-8')

    def test_detect_html5_style_meta_tag(self):

        for data in (
            b'<html><meta charset="euc-jp" /></html>',
            b"<html><meta charset='euc-jp' /></html>",
            b"<html><meta charset=euc-jp /></html>",
            b"<html><meta charset=euc-jp/></html>"):
            dammit = UnicodeDammit(data, is_html=True)
            self.assertEqual(
                "euc-jp", dammit.original_encoding)

    def test_last_ditch_entity_replacement(self):
        # This is a UTF-8 document that contains bytestrings
        # completely incompatible with UTF-8 (ie. encoded with some other
        # encoding).
        #
        # Since there is no consistent encoding for the document,
        # Unicode, Dammit will eventually encode the document as UTF-8
        # and encode the incompatible characters as REPLACEMENT
        # CHARACTER.
        #
        # If chardet is installed, it will detect that the document
        # can be converted into ISO-8859-1 without errors. This happens
        # to be the wrong encoding, but it is a consistent encoding, so the
        # code we're testing here won't run.
        #
        # So we temporarily disable chardet if it's present.
        doc = b"""\357\273\277<?xml version="1.0" encoding="UTF-8"?>
<html><b>\330\250\330\252\330\261</b>
<i>\310\322\321\220\312\321\355\344</i></html>"""
        chardet = bs4.dammit.chardet_dammit
        logging.disable(logging.WARNING)
        try:
            def noop(str):
                return None
            bs4.dammit.chardet_dammit = noop
            dammit = UnicodeDammit(doc)
            self.assertEqual(True, dammit.contains_replacement_characters)
            self.assertTrue(u"\ufffd" in dammit.unicode_markup)

            soup = BeautifulSoup(doc, "html.parser")
            self.assertTrue(soup.contains_replacement_characters)
        finally:
            logging.disable(logging.NOTSET)
            bs4.dammit.chardet_dammit = chardet

    def test_sniffed_xml_encoding(self):
        # A document written in UTF-16LE will be converted by a different
        # code path that sniffs the byte order markers.
        data = b'\xff\xfe<\x00a\x00>\x00\xe1\x00\xe9\x00<\x00/\x00a\x00>\x00'
        dammit = UnicodeDammit(data)
        self.assertEqual(u"<a>áé</a>", dammit.unicode_markup)
        self.assertEqual("utf-16le", dammit.original_encoding)

    def test_detwingle(self):
        # Here's a UTF8 document.
        utf8 = (u"\N{SNOWMAN}" * 3).encode("utf8")

        # Here's a Windows-1252 document.
        windows_1252 = (
            u"\N{LEFT DOUBLE QUOTATION MARK}Hi, I like Windows!"
            u"\N{RIGHT DOUBLE QUOTATION MARK}").encode("windows_1252")

        # Through some unholy alchemy, they've been stuck together.
        doc = utf8 + windows_1252 + utf8

        # The document can't be turned into UTF-8:
        self.assertRaises(UnicodeDecodeError, doc.decode, "utf8")

        # Unicode, Dammit thinks the whole document is Windows-1252,
        # and decodes it into "â˜ƒâ˜ƒâ˜ƒ“Hi, I like Windows!”â˜ƒâ˜ƒâ˜ƒ"

        # But if we run it through fix_embedded_windows_1252, it's fixed:

        fixed = UnicodeDammit.detwingle(doc)
        self.assertEqual(
            u"☃☃☃“Hi, I like Windows!”☃☃☃", fixed.decode("utf8"))

    def test_detwingle_ignores_multibyte_characters(self):
        # Each of these characters has a UTF-8 representation ending
        # in \x93. \x93 is a smart quote if interpreted as
        # Windows-1252. But our code knows to skip over multibyte
        # UTF-8 characters, so they'll survive the process unscathed.
        for tricky_unicode_char in (
            u"\N{LATIN SMALL LIGATURE OE}", # 2-byte char '\xc5\x93'
            u"\N{LATIN SUBSCRIPT SMALL LETTER X}", # 3-byte char '\xe2\x82\x93'
            u"\xf0\x90\x90\x93", # This is a CJK character, not sure which one.
            ):
            input = tricky_unicode_char.encode("utf8")
            self.assertTrue(input.endswith(b'\x93'))
            output = UnicodeDammit.detwingle(input)
            self.assertEqual(output, input)

class TestNamedspacedAttribute(SoupTest):

    def test_name_may_be_none(self):
        a = NamespacedAttribute("xmlns", None)
        self.assertEqual(a, "xmlns")

    def test_attribute_is_equivalent_to_colon_separated_string(self):
        a = NamespacedAttribute("a", "b")
        self.assertEqual("a:b", a)

    def test_attributes_are_equivalent_if_prefix_and_name_identical(self):
        a = NamespacedAttribute("a", "b", "c")
        b = NamespacedAttribute("a", "b", "c")
        self.assertEqual(a, b)

        # The actual namespace is not considered.
        c = NamespacedAttribute("a", "b", None)
        self.assertEqual(a, c)

        # But name and prefix are important.
        d = NamespacedAttribute("a", "z", "c")
        self.assertNotEqual(a, d)

        e = NamespacedAttribute("z", "b", "c")
        self.assertNotEqual(a, e)


class TestAttributeValueWithCharsetSubstitution(unittest.TestCase):

    def test_content_meta_attribute_value(self):
        value = CharsetMetaAttributeValue("euc-jp")
        self.assertEqual("euc-jp", value)
        self.assertEqual("euc-jp", value.original_value)
        self.assertEqual("utf8", value.encode("utf8"))


    def test_content_meta_attribute_value(self):
        value = ContentMetaAttributeValue("text/html; charset=euc-jp")
        self.assertEqual("text/html; charset=euc-jp", value)
        self.assertEqual("text/html; charset=euc-jp", value.original_value)
        self.assertEqual("text/html; charset=utf8", value.encode("utf8"))

########NEW FILE########
__FILENAME__ = test_tree
# -*- coding: utf-8 -*-
"""Tests for Beautiful Soup's tree traversal methods.

The tree traversal methods are the main advantage of using Beautiful
Soup over just using a parser.

Different parsers will build different Beautiful Soup trees given the
same markup, but all Beautiful Soup trees can be traversed with the
methods tested here.
"""

import copy
import pickle
import re
import warnings
from bs4 import BeautifulSoup
from bs4.builder import (
    builder_registry,
    HTMLParserTreeBuilder,
)
from bs4.element import (
    CData,
    Doctype,
    NavigableString,
    SoupStrainer,
    Tag,
)
from bs4.testing import (
    SoupTest,
    skipIf,
)

XML_BUILDER_PRESENT = (builder_registry.lookup("xml") is not None)
LXML_PRESENT = (builder_registry.lookup("lxml") is not None)

class TreeTest(SoupTest):

    def assertSelects(self, tags, should_match):
        """Make sure that the given tags have the correct text.

        This is used in tests that define a bunch of tags, each
        containing a single string, and then select certain strings by
        some mechanism.
        """
        self.assertEqual([tag.string for tag in tags], should_match)

    def assertSelectsIDs(self, tags, should_match):
        """Make sure that the given tags have the correct IDs.

        This is used in tests that define a bunch of tags, each
        containing a single string, and then select certain strings by
        some mechanism.
        """
        self.assertEqual([tag['id'] for tag in tags], should_match)


class TestFind(TreeTest):
    """Basic tests of the find() method.

    find() just calls find_all() with limit=1, so it's not tested all
    that thouroughly here.
    """

    def test_find_tag(self):
        soup = self.soup("<a>1</a><b>2</b><a>3</a><b>4</b>")
        self.assertEqual(soup.find("b").string, "2")

    def test_unicode_text_find(self):
        soup = self.soup(u'<h1>Räksmörgås</h1>')
        self.assertEqual(soup.find(text=u'Räksmörgås'), u'Räksmörgås')

class TestFindAll(TreeTest):
    """Basic tests of the find_all() method."""

    def test_find_all_text_nodes(self):
        """You can search the tree for text nodes."""
        soup = self.soup("<html>Foo<b>bar</b>\xbb</html>")
        # Exact match.
        self.assertEqual(soup.find_all(text="bar"), [u"bar"])
        # Match any of a number of strings.
        self.assertEqual(
            soup.find_all(text=["Foo", "bar"]), [u"Foo", u"bar"])
        # Match a regular expression.
        self.assertEqual(soup.find_all(text=re.compile('.*')),
                         [u"Foo", u"bar", u'\xbb'])
        # Match anything.
        self.assertEqual(soup.find_all(text=True),
                         [u"Foo", u"bar", u'\xbb'])

    def test_find_all_limit(self):
        """You can limit the number of items returned by find_all."""
        soup = self.soup("<a>1</a><a>2</a><a>3</a><a>4</a><a>5</a>")
        self.assertSelects(soup.find_all('a', limit=3), ["1", "2", "3"])
        self.assertSelects(soup.find_all('a', limit=1), ["1"])
        self.assertSelects(
            soup.find_all('a', limit=10), ["1", "2", "3", "4", "5"])

        # A limit of 0 means no limit.
        self.assertSelects(
            soup.find_all('a', limit=0), ["1", "2", "3", "4", "5"])

    def test_calling_a_tag_is_calling_findall(self):
        soup = self.soup("<a>1</a><b>2<a id='foo'>3</a></b>")
        self.assertSelects(soup('a', limit=1), ["1"])
        self.assertSelects(soup.b(id="foo"), ["3"])

    def test_find_all_with_self_referential_data_structure_does_not_cause_infinite_recursion(self):
        soup = self.soup("<a></a>")
        # Create a self-referential list.
        l = []
        l.append(l)

        # Without special code in _normalize_search_value, this would cause infinite
        # recursion.
        self.assertEqual([], soup.find_all(l))

class TestFindAllBasicNamespaces(TreeTest):

    def test_find_by_namespaced_name(self):
        soup = self.soup('<mathml:msqrt>4</mathml:msqrt><a svg:fill="red">')
        self.assertEqual("4", soup.find("mathml:msqrt").string)
        self.assertEqual("a", soup.find(attrs= { "svg:fill" : "red" }).name)


class TestFindAllByName(TreeTest):
    """Test ways of finding tags by tag name."""

    def setUp(self):
        super(TreeTest, self).setUp()
        self.tree =  self.soup("""<a>First tag.</a>
                                  <b>Second tag.</b>
                                  <c>Third <a>Nested tag.</a> tag.</c>""")

    def test_find_all_by_tag_name(self):
        # Find all the <a> tags.
        self.assertSelects(
            self.tree.find_all('a'), ['First tag.', 'Nested tag.'])

    def test_find_all_by_name_and_text(self):
        self.assertSelects(
            self.tree.find_all('a', text='First tag.'), ['First tag.'])

        self.assertSelects(
            self.tree.find_all('a', text=True), ['First tag.', 'Nested tag.'])

        self.assertSelects(
            self.tree.find_all('a', text=re.compile("tag")),
            ['First tag.', 'Nested tag.'])


    def test_find_all_on_non_root_element(self):
        # You can call find_all on any node, not just the root.
        self.assertSelects(self.tree.c.find_all('a'), ['Nested tag.'])

    def test_calling_element_invokes_find_all(self):
        self.assertSelects(self.tree('a'), ['First tag.', 'Nested tag.'])

    def test_find_all_by_tag_strainer(self):
        self.assertSelects(
            self.tree.find_all(SoupStrainer('a')),
            ['First tag.', 'Nested tag.'])

    def test_find_all_by_tag_names(self):
        self.assertSelects(
            self.tree.find_all(['a', 'b']),
            ['First tag.', 'Second tag.', 'Nested tag.'])

    def test_find_all_by_tag_dict(self):
        self.assertSelects(
            self.tree.find_all({'a' : True, 'b' : True}),
            ['First tag.', 'Second tag.', 'Nested tag.'])

    def test_find_all_by_tag_re(self):
        self.assertSelects(
            self.tree.find_all(re.compile('^[ab]$')),
            ['First tag.', 'Second tag.', 'Nested tag.'])

    def test_find_all_with_tags_matching_method(self):
        # You can define an oracle method that determines whether
        # a tag matches the search.
        def id_matches_name(tag):
            return tag.name == tag.get('id')

        tree = self.soup("""<a id="a">Match 1.</a>
                            <a id="1">Does not match.</a>
                            <b id="b">Match 2.</a>""")

        self.assertSelects(
            tree.find_all(id_matches_name), ["Match 1.", "Match 2."])


class TestFindAllByAttribute(TreeTest):

    def test_find_all_by_attribute_name(self):
        # You can pass in keyword arguments to find_all to search by
        # attribute.
        tree = self.soup("""
                         <a id="first">Matching a.</a>
                         <a id="second">
                          Non-matching <b id="first">Matching b.</b>a.
                         </a>""")
        self.assertSelects(tree.find_all(id='first'),
                           ["Matching a.", "Matching b."])

    def test_find_all_by_utf8_attribute_value(self):
        peace = u"םולש".encode("utf8")
        data = u'<a title="םולש"></a>'.encode("utf8")
        soup = self.soup(data)
        self.assertEqual([soup.a], soup.find_all(title=peace))
        self.assertEqual([soup.a], soup.find_all(title=peace.decode("utf8")))
        self.assertEqual([soup.a], soup.find_all(title=[peace, "something else"]))

    def test_find_all_by_attribute_dict(self):
        # You can pass in a dictionary as the argument 'attrs'. This
        # lets you search for attributes like 'name' (a fixed argument
        # to find_all) and 'class' (a reserved word in Python.)
        tree = self.soup("""
                         <a name="name1" class="class1">Name match.</a>
                         <a name="name2" class="class2">Class match.</a>
                         <a name="name3" class="class3">Non-match.</a>
                         <name1>A tag called 'name1'.</name1>
                         """)

        # This doesn't do what you want.
        self.assertSelects(tree.find_all(name='name1'),
                           ["A tag called 'name1'."])
        # This does what you want.
        self.assertSelects(tree.find_all(attrs={'name' : 'name1'}),
                           ["Name match."])

        self.assertSelects(tree.find_all(attrs={'class' : 'class2'}),
                           ["Class match."])

    def test_find_all_by_class(self):
        tree = self.soup("""
                         <a class="1">Class 1.</a>
                         <a class="2">Class 2.</a>
                         <b class="1">Class 1.</b>
                         <c class="3 4">Class 3 and 4.</c>
                         """)

        # Passing in the class_ keyword argument will search against
        # the 'class' attribute.
        self.assertSelects(tree.find_all('a', class_='1'), ['Class 1.'])
        self.assertSelects(tree.find_all('c', class_='3'), ['Class 3 and 4.'])
        self.assertSelects(tree.find_all('c', class_='4'), ['Class 3 and 4.'])

        # Passing in a string to 'attrs' will also search the CSS class.
        self.assertSelects(tree.find_all('a', '1'), ['Class 1.'])
        self.assertSelects(tree.find_all(attrs='1'), ['Class 1.', 'Class 1.'])
        self.assertSelects(tree.find_all('c', '3'), ['Class 3 and 4.'])
        self.assertSelects(tree.find_all('c', '4'), ['Class 3 and 4.'])

    def test_find_by_class_when_multiple_classes_present(self):
        tree = self.soup("<gar class='foo bar'>Found it</gar>")

        f = tree.find_all("gar", class_=re.compile("o"))
        self.assertSelects(f, ["Found it"])

        f = tree.find_all("gar", class_=re.compile("a"))
        self.assertSelects(f, ["Found it"])

        # Since the class is not the string "foo bar", but the two
        # strings "foo" and "bar", this will not find anything.
        f = tree.find_all("gar", class_=re.compile("o b"))
        self.assertSelects(f, [])

    def test_find_all_with_non_dictionary_for_attrs_finds_by_class(self):
        soup = self.soup("<a class='bar'>Found it</a>")

        self.assertSelects(soup.find_all("a", re.compile("ba")), ["Found it"])

        def big_attribute_value(value):
            return len(value) > 3

        self.assertSelects(soup.find_all("a", big_attribute_value), [])

        def small_attribute_value(value):
            return len(value) <= 3

        self.assertSelects(
            soup.find_all("a", small_attribute_value), ["Found it"])

    def test_find_all_with_string_for_attrs_finds_multiple_classes(self):
        soup = self.soup('<a class="foo bar"></a><a class="foo"></a>')
        a, a2 = soup.find_all("a")
        self.assertEqual([a, a2], soup.find_all("a", "foo"))
        self.assertEqual([a], soup.find_all("a", "bar"))

        # If you specify the class as a string that contains a
        # space, only that specific value will be found.
        self.assertEqual([a], soup.find_all("a", class_="foo bar"))
        self.assertEqual([a], soup.find_all("a", "foo bar"))
        self.assertEqual([], soup.find_all("a", "bar foo"))

    def test_find_all_by_attribute_soupstrainer(self):
        tree = self.soup("""
                         <a id="first">Match.</a>
                         <a id="second">Non-match.</a>""")

        strainer = SoupStrainer(attrs={'id' : 'first'})
        self.assertSelects(tree.find_all(strainer), ['Match.'])

    def test_find_all_with_missing_atribute(self):
        # You can pass in None as the value of an attribute to find_all.
        # This will match tags that do not have that attribute set.
        tree = self.soup("""<a id="1">ID present.</a>
                            <a>No ID present.</a>
                            <a id="">ID is empty.</a>""")
        self.assertSelects(tree.find_all('a', id=None), ["No ID present."])

    def test_find_all_with_defined_attribute(self):
        # You can pass in None as the value of an attribute to find_all.
        # This will match tags that have that attribute set to any value.
        tree = self.soup("""<a id="1">ID present.</a>
                            <a>No ID present.</a>
                            <a id="">ID is empty.</a>""")
        self.assertSelects(
            tree.find_all(id=True), ["ID present.", "ID is empty."])

    def test_find_all_with_numeric_attribute(self):
        # If you search for a number, it's treated as a string.
        tree = self.soup("""<a id=1>Unquoted attribute.</a>
                            <a id="1">Quoted attribute.</a>""")

        expected = ["Unquoted attribute.", "Quoted attribute."]
        self.assertSelects(tree.find_all(id=1), expected)
        self.assertSelects(tree.find_all(id="1"), expected)

    def test_find_all_with_list_attribute_values(self):
        # You can pass a list of attribute values instead of just one,
        # and you'll get tags that match any of the values.
        tree = self.soup("""<a id="1">1</a>
                            <a id="2">2</a>
                            <a id="3">3</a>
                            <a>No ID.</a>""")
        self.assertSelects(tree.find_all(id=["1", "3", "4"]),
                           ["1", "3"])

    def test_find_all_with_regular_expression_attribute_value(self):
        # You can pass a regular expression as an attribute value, and
        # you'll get tags whose values for that attribute match the
        # regular expression.
        tree = self.soup("""<a id="a">One a.</a>
                            <a id="aa">Two as.</a>
                            <a id="ab">Mixed as and bs.</a>
                            <a id="b">One b.</a>
                            <a>No ID.</a>""")

        self.assertSelects(tree.find_all(id=re.compile("^a+$")),
                           ["One a.", "Two as."])

    def test_find_by_name_and_containing_string(self):
        soup = self.soup("<b>foo</b><b>bar</b><a>foo</a>")
        a = soup.a

        self.assertEqual([a], soup.find_all("a", text="foo"))
        self.assertEqual([], soup.find_all("a", text="bar"))
        self.assertEqual([], soup.find_all("a", text="bar"))

    def test_find_by_name_and_containing_string_when_string_is_buried(self):
        soup = self.soup("<a>foo</a><a><b><c>foo</c></b></a>")
        self.assertEqual(soup.find_all("a"), soup.find_all("a", text="foo"))

    def test_find_by_attribute_and_containing_string(self):
        soup = self.soup('<b id="1">foo</b><a id="2">foo</a>')
        a = soup.a

        self.assertEqual([a], soup.find_all(id=2, text="foo"))
        self.assertEqual([], soup.find_all(id=1, text="bar"))




class TestIndex(TreeTest):
    """Test Tag.index"""
    def test_index(self):
        tree = self.soup("""<div>
                            <a>Identical</a>
                            <b>Not identical</b>
                            <a>Identical</a>

                            <c><d>Identical with child</d></c>
                            <b>Also not identical</b>
                            <c><d>Identical with child</d></c>
                            </div>""")
        div = tree.div
        for i, element in enumerate(div.contents):
            self.assertEqual(i, div.index(element))
        self.assertRaises(ValueError, tree.index, 1)


class TestParentOperations(TreeTest):
    """Test navigation and searching through an element's parents."""

    def setUp(self):
        super(TestParentOperations, self).setUp()
        self.tree = self.soup('''<ul id="empty"></ul>
                                 <ul id="top">
                                  <ul id="middle">
                                   <ul id="bottom">
                                    <b>Start here</b>
                                   </ul>
                                  </ul>''')
        self.start = self.tree.b


    def test_parent(self):
        self.assertEqual(self.start.parent['id'], 'bottom')
        self.assertEqual(self.start.parent.parent['id'], 'middle')
        self.assertEqual(self.start.parent.parent.parent['id'], 'top')

    def test_parent_of_top_tag_is_soup_object(self):
        top_tag = self.tree.contents[0]
        self.assertEqual(top_tag.parent, self.tree)

    def test_soup_object_has_no_parent(self):
        self.assertEqual(None, self.tree.parent)

    def test_find_parents(self):
        self.assertSelectsIDs(
            self.start.find_parents('ul'), ['bottom', 'middle', 'top'])
        self.assertSelectsIDs(
            self.start.find_parents('ul', id="middle"), ['middle'])

    def test_find_parent(self):
        self.assertEqual(self.start.find_parent('ul')['id'], 'bottom')

    def test_parent_of_text_element(self):
        text = self.tree.find(text="Start here")
        self.assertEqual(text.parent.name, 'b')

    def test_text_element_find_parent(self):
        text = self.tree.find(text="Start here")
        self.assertEqual(text.find_parent('ul')['id'], 'bottom')

    def test_parent_generator(self):
        parents = [parent['id'] for parent in self.start.parents
                   if parent is not None and 'id' in parent.attrs]
        self.assertEqual(parents, ['bottom', 'middle', 'top'])


class ProximityTest(TreeTest):

    def setUp(self):
        super(TreeTest, self).setUp()
        self.tree = self.soup(
            '<html id="start"><head></head><body><b id="1">One</b><b id="2">Two</b><b id="3">Three</b></body></html>')


class TestNextOperations(ProximityTest):

    def setUp(self):
        super(TestNextOperations, self).setUp()
        self.start = self.tree.b

    def test_next(self):
        self.assertEqual(self.start.next_element, "One")
        self.assertEqual(self.start.next_element.next_element['id'], "2")

    def test_next_of_last_item_is_none(self):
        last = self.tree.find(text="Three")
        self.assertEqual(last.next_element, None)

    def test_next_of_root_is_none(self):
        # The document root is outside the next/previous chain.
        self.assertEqual(self.tree.next_element, None)

    def test_find_all_next(self):
        self.assertSelects(self.start.find_all_next('b'), ["Two", "Three"])
        self.start.find_all_next(id=3)
        self.assertSelects(self.start.find_all_next(id=3), ["Three"])

    def test_find_next(self):
        self.assertEqual(self.start.find_next('b')['id'], '2')
        self.assertEqual(self.start.find_next(text="Three"), "Three")

    def test_find_next_for_text_element(self):
        text = self.tree.find(text="One")
        self.assertEqual(text.find_next("b").string, "Two")
        self.assertSelects(text.find_all_next("b"), ["Two", "Three"])

    def test_next_generator(self):
        start = self.tree.find(text="Two")
        successors = [node for node in start.next_elements]
        # There are two successors: the final <b> tag and its text contents.
        tag, contents = successors
        self.assertEqual(tag['id'], '3')
        self.assertEqual(contents, "Three")

class TestPreviousOperations(ProximityTest):

    def setUp(self):
        super(TestPreviousOperations, self).setUp()
        self.end = self.tree.find(text="Three")

    def test_previous(self):
        self.assertEqual(self.end.previous_element['id'], "3")
        self.assertEqual(self.end.previous_element.previous_element, "Two")

    def test_previous_of_first_item_is_none(self):
        first = self.tree.find('html')
        self.assertEqual(first.previous_element, None)

    def test_previous_of_root_is_none(self):
        # The document root is outside the next/previous chain.
        # XXX This is broken!
        #self.assertEqual(self.tree.previous_element, None)
        pass

    def test_find_all_previous(self):
        # The <b> tag containing the "Three" node is the predecessor
        # of the "Three" node itself, which is why "Three" shows up
        # here.
        self.assertSelects(
            self.end.find_all_previous('b'), ["Three", "Two", "One"])
        self.assertSelects(self.end.find_all_previous(id=1), ["One"])

    def test_find_previous(self):
        self.assertEqual(self.end.find_previous('b')['id'], '3')
        self.assertEqual(self.end.find_previous(text="One"), "One")

    def test_find_previous_for_text_element(self):
        text = self.tree.find(text="Three")
        self.assertEqual(text.find_previous("b").string, "Three")
        self.assertSelects(
            text.find_all_previous("b"), ["Three", "Two", "One"])

    def test_previous_generator(self):
        start = self.tree.find(text="One")
        predecessors = [node for node in start.previous_elements]

        # There are four predecessors: the <b> tag containing "One"
        # the <body> tag, the <head> tag, and the <html> tag.
        b, body, head, html = predecessors
        self.assertEqual(b['id'], '1')
        self.assertEqual(body.name, "body")
        self.assertEqual(head.name, "head")
        self.assertEqual(html.name, "html")


class SiblingTest(TreeTest):

    def setUp(self):
        super(SiblingTest, self).setUp()
        markup = '''<html>
                    <span id="1">
                     <span id="1.1"></span>
                    </span>
                    <span id="2">
                     <span id="2.1"></span>
                    </span>
                    <span id="3">
                     <span id="3.1"></span>
                    </span>
                    <span id="4"></span>
                    </html>'''
        # All that whitespace looks good but makes the tests more
        # difficult. Get rid of it.
        markup = re.compile("\n\s*").sub("", markup)
        self.tree = self.soup(markup)


class TestNextSibling(SiblingTest):

    def setUp(self):
        super(TestNextSibling, self).setUp()
        self.start = self.tree.find(id="1")

    def test_next_sibling_of_root_is_none(self):
        self.assertEqual(self.tree.next_sibling, None)

    def test_next_sibling(self):
        self.assertEqual(self.start.next_sibling['id'], '2')
        self.assertEqual(self.start.next_sibling.next_sibling['id'], '3')

        # Note the difference between next_sibling and next_element.
        self.assertEqual(self.start.next_element['id'], '1.1')

    def test_next_sibling_may_not_exist(self):
        self.assertEqual(self.tree.html.next_sibling, None)

        nested_span = self.tree.find(id="1.1")
        self.assertEqual(nested_span.next_sibling, None)

        last_span = self.tree.find(id="4")
        self.assertEqual(last_span.next_sibling, None)

    def test_find_next_sibling(self):
        self.assertEqual(self.start.find_next_sibling('span')['id'], '2')

    def test_next_siblings(self):
        self.assertSelectsIDs(self.start.find_next_siblings("span"),
                              ['2', '3', '4'])

        self.assertSelectsIDs(self.start.find_next_siblings(id='3'), ['3'])

    def test_next_sibling_for_text_element(self):
        soup = self.soup("Foo<b>bar</b>baz")
        start = soup.find(text="Foo")
        self.assertEqual(start.next_sibling.name, 'b')
        self.assertEqual(start.next_sibling.next_sibling, 'baz')

        self.assertSelects(start.find_next_siblings('b'), ['bar'])
        self.assertEqual(start.find_next_sibling(text="baz"), "baz")
        self.assertEqual(start.find_next_sibling(text="nonesuch"), None)


class TestPreviousSibling(SiblingTest):

    def setUp(self):
        super(TestPreviousSibling, self).setUp()
        self.end = self.tree.find(id="4")

    def test_previous_sibling_of_root_is_none(self):
        self.assertEqual(self.tree.previous_sibling, None)

    def test_previous_sibling(self):
        self.assertEqual(self.end.previous_sibling['id'], '3')
        self.assertEqual(self.end.previous_sibling.previous_sibling['id'], '2')

        # Note the difference between previous_sibling and previous_element.
        self.assertEqual(self.end.previous_element['id'], '3.1')

    def test_previous_sibling_may_not_exist(self):
        self.assertEqual(self.tree.html.previous_sibling, None)

        nested_span = self.tree.find(id="1.1")
        self.assertEqual(nested_span.previous_sibling, None)

        first_span = self.tree.find(id="1")
        self.assertEqual(first_span.previous_sibling, None)

    def test_find_previous_sibling(self):
        self.assertEqual(self.end.find_previous_sibling('span')['id'], '3')

    def test_previous_siblings(self):
        self.assertSelectsIDs(self.end.find_previous_siblings("span"),
                              ['3', '2', '1'])

        self.assertSelectsIDs(self.end.find_previous_siblings(id='1'), ['1'])

    def test_previous_sibling_for_text_element(self):
        soup = self.soup("Foo<b>bar</b>baz")
        start = soup.find(text="baz")
        self.assertEqual(start.previous_sibling.name, 'b')
        self.assertEqual(start.previous_sibling.previous_sibling, 'Foo')

        self.assertSelects(start.find_previous_siblings('b'), ['bar'])
        self.assertEqual(start.find_previous_sibling(text="Foo"), "Foo")
        self.assertEqual(start.find_previous_sibling(text="nonesuch"), None)


class TestTagCreation(SoupTest):
    """Test the ability to create new tags."""
    def test_new_tag(self):
        soup = self.soup("")
        new_tag = soup.new_tag("foo", bar="baz")
        self.assertTrue(isinstance(new_tag, Tag))
        self.assertEqual("foo", new_tag.name)
        self.assertEqual(dict(bar="baz"), new_tag.attrs)
        self.assertEqual(None, new_tag.parent)

    def test_tag_inherits_self_closing_rules_from_builder(self):
        if XML_BUILDER_PRESENT:
            xml_soup = BeautifulSoup("", "xml")
            xml_br = xml_soup.new_tag("br")
            xml_p = xml_soup.new_tag("p")

            # Both the <br> and <p> tag are empty-element, just because
            # they have no contents.
            self.assertEqual(b"<br/>", xml_br.encode())
            self.assertEqual(b"<p/>", xml_p.encode())

        html_soup = BeautifulSoup("", "html")
        html_br = html_soup.new_tag("br")
        html_p = html_soup.new_tag("p")

        # The HTML builder users HTML's rules about which tags are
        # empty-element tags, and the new tags reflect these rules.
        self.assertEqual(b"<br/>", html_br.encode())
        self.assertEqual(b"<p></p>", html_p.encode())

    def test_new_string_creates_navigablestring(self):
        soup = self.soup("")
        s = soup.new_string("foo")
        self.assertEqual("foo", s)
        self.assertTrue(isinstance(s, NavigableString))

class TestTreeModification(SoupTest):

    def test_attribute_modification(self):
        soup = self.soup('<a id="1"></a>')
        soup.a['id'] = 2
        self.assertEqual(soup.decode(), self.document_for('<a id="2"></a>'))
        del(soup.a['id'])
        self.assertEqual(soup.decode(), self.document_for('<a></a>'))
        soup.a['id2'] = 'foo'
        self.assertEqual(soup.decode(), self.document_for('<a id2="foo"></a>'))

    def test_new_tag_creation(self):
        builder = builder_registry.lookup('html')()
        soup = self.soup("<body></body>", builder=builder)
        a = Tag(soup, builder, 'a')
        ol = Tag(soup, builder, 'ol')
        a['href'] = 'http://foo.com/'
        soup.body.insert(0, a)
        soup.body.insert(1, ol)
        self.assertEqual(
            soup.body.encode(),
            b'<body><a href="http://foo.com/"></a><ol></ol></body>')

    def test_append_to_contents_moves_tag(self):
        doc = """<p id="1">Don't leave me <b>here</b>.</p>
                <p id="2">Don\'t leave!</p>"""
        soup = self.soup(doc)
        second_para = soup.find(id='2')
        bold = soup.b

        # Move the <b> tag to the end of the second paragraph.
        soup.find(id='2').append(soup.b)

        # The <b> tag is now a child of the second paragraph.
        self.assertEqual(bold.parent, second_para)

        self.assertEqual(
            soup.decode(), self.document_for(
                '<p id="1">Don\'t leave me .</p>\n'
                '<p id="2">Don\'t leave!<b>here</b></p>'))

    def test_replace_with_returns_thing_that_was_replaced(self):
        text = "<a></a><b><c></c></b>"
        soup = self.soup(text)
        a = soup.a
        new_a = a.replace_with(soup.c)
        self.assertEqual(a, new_a)

    def test_unwrap_returns_thing_that_was_replaced(self):
        text = "<a><b></b><c></c></a>"
        soup = self.soup(text)
        a = soup.a
        new_a = a.unwrap()
        self.assertEqual(a, new_a)

    def test_replace_tag_with_itself(self):
        text = "<a><b></b><c>Foo<d></d></c></a><a><e></e></a>"
        soup = self.soup(text)
        c = soup.c
        soup.c.replace_with(c)
        self.assertEqual(soup.decode(), self.document_for(text))

    def test_replace_tag_with_its_parent_raises_exception(self):
        text = "<a><b></b></a>"
        soup = self.soup(text)
        self.assertRaises(ValueError, soup.b.replace_with, soup.a)

    def test_insert_tag_into_itself_raises_exception(self):
        text = "<a><b></b></a>"
        soup = self.soup(text)
        self.assertRaises(ValueError, soup.a.insert, 0, soup.a)

    def test_replace_with_maintains_next_element_throughout(self):
        soup = self.soup('<p><a>one</a><b>three</b></p>')
        a = soup.a
        b = a.contents[0]
        # Make it so the <a> tag has two text children.
        a.insert(1, "two")

        # Now replace each one with the empty string.
        left, right = a.contents
        left.replaceWith('')
        right.replaceWith('')

        # The <b> tag is still connected to the tree.
        self.assertEqual("three", soup.b.string)

    def test_replace_final_node(self):
        soup = self.soup("<b>Argh!</b>")
        soup.find(text="Argh!").replace_with("Hooray!")
        new_text = soup.find(text="Hooray!")
        b = soup.b
        self.assertEqual(new_text.previous_element, b)
        self.assertEqual(new_text.parent, b)
        self.assertEqual(new_text.previous_element.next_element, new_text)
        self.assertEqual(new_text.next_element, None)

    def test_consecutive_text_nodes(self):
        # A builder should never create two consecutive text nodes,
        # but if you insert one next to another, Beautiful Soup will
        # handle it correctly.
        soup = self.soup("<a><b>Argh!</b><c></c></a>")
        soup.b.insert(1, "Hooray!")

        self.assertEqual(
            soup.decode(), self.document_for(
                "<a><b>Argh!Hooray!</b><c></c></a>"))

        new_text = soup.find(text="Hooray!")
        self.assertEqual(new_text.previous_element, "Argh!")
        self.assertEqual(new_text.previous_element.next_element, new_text)

        self.assertEqual(new_text.previous_sibling, "Argh!")
        self.assertEqual(new_text.previous_sibling.next_sibling, new_text)

        self.assertEqual(new_text.next_sibling, None)
        self.assertEqual(new_text.next_element, soup.c)

    def test_insert_string(self):
        soup = self.soup("<a></a>")
        soup.a.insert(0, "bar")
        soup.a.insert(0, "foo")
        # The string were added to the tag.
        self.assertEqual(["foo", "bar"], soup.a.contents)
        # And they were converted to NavigableStrings.
        self.assertEqual(soup.a.contents[0].next_element, "bar")

    def test_insert_tag(self):
        builder = self.default_builder
        soup = self.soup(
            "<a><b>Find</b><c>lady!</c><d></d></a>", builder=builder)
        magic_tag = Tag(soup, builder, 'magictag')
        magic_tag.insert(0, "the")
        soup.a.insert(1, magic_tag)

        self.assertEqual(
            soup.decode(), self.document_for(
                "<a><b>Find</b><magictag>the</magictag><c>lady!</c><d></d></a>"))

        # Make sure all the relationships are hooked up correctly.
        b_tag = soup.b
        self.assertEqual(b_tag.next_sibling, magic_tag)
        self.assertEqual(magic_tag.previous_sibling, b_tag)

        find = b_tag.find(text="Find")
        self.assertEqual(find.next_element, magic_tag)
        self.assertEqual(magic_tag.previous_element, find)

        c_tag = soup.c
        self.assertEqual(magic_tag.next_sibling, c_tag)
        self.assertEqual(c_tag.previous_sibling, magic_tag)

        the = magic_tag.find(text="the")
        self.assertEqual(the.parent, magic_tag)
        self.assertEqual(the.next_element, c_tag)
        self.assertEqual(c_tag.previous_element, the)

    def test_append_child_thats_already_at_the_end(self):
        data = "<a><b></b></a>"
        soup = self.soup(data)
        soup.a.append(soup.b)
        self.assertEqual(data, soup.decode())

    def test_move_tag_to_beginning_of_parent(self):
        data = "<a><b></b><c></c><d></d></a>"
        soup = self.soup(data)
        soup.a.insert(0, soup.d)
        self.assertEqual("<a><d></d><b></b><c></c></a>", soup.decode())

    def test_insert_works_on_empty_element_tag(self):
        # This is a little strange, since most HTML parsers don't allow
        # markup like this to come through. But in general, we don't
        # know what the parser would or wouldn't have allowed, so
        # I'm letting this succeed for now.
        soup = self.soup("<br/>")
        soup.br.insert(1, "Contents")
        self.assertEqual(str(soup.br), "<br>Contents</br>")

    def test_insert_before(self):
        soup = self.soup("<a>foo</a><b>bar</b>")
        soup.b.insert_before("BAZ")
        soup.a.insert_before("QUUX")
        self.assertEqual(
            soup.decode(), self.document_for("QUUX<a>foo</a>BAZ<b>bar</b>"))

        soup.a.insert_before(soup.b)
        self.assertEqual(
            soup.decode(), self.document_for("QUUX<b>bar</b><a>foo</a>BAZ"))

    def test_insert_after(self):
        soup = self.soup("<a>foo</a><b>bar</b>")
        soup.b.insert_after("BAZ")
        soup.a.insert_after("QUUX")
        self.assertEqual(
            soup.decode(), self.document_for("<a>foo</a>QUUX<b>bar</b>BAZ"))
        soup.b.insert_after(soup.a)
        self.assertEqual(
            soup.decode(), self.document_for("QUUX<b>bar</b><a>foo</a>BAZ"))

    def test_insert_after_raises_exception_if_after_has_no_meaning(self):
        soup = self.soup("")
        tag = soup.new_tag("a")
        string = soup.new_string("")
        self.assertRaises(ValueError, string.insert_after, tag)
        self.assertRaises(NotImplementedError, soup.insert_after, tag)
        self.assertRaises(ValueError, tag.insert_after, tag)

    def test_insert_before_raises_notimplementederror_if_before_has_no_meaning(self):
        soup = self.soup("")
        tag = soup.new_tag("a")
        string = soup.new_string("")
        self.assertRaises(ValueError, string.insert_before, tag)
        self.assertRaises(NotImplementedError, soup.insert_before, tag)
        self.assertRaises(ValueError, tag.insert_before, tag)

    def test_replace_with(self):
        soup = self.soup(
                "<p>There's <b>no</b> business like <b>show</b> business</p>")
        no, show = soup.find_all('b')
        show.replace_with(no)
        self.assertEqual(
            soup.decode(),
            self.document_for(
                "<p>There's  business like <b>no</b> business</p>"))

        self.assertEqual(show.parent, None)
        self.assertEqual(no.parent, soup.p)
        self.assertEqual(no.next_element, "no")
        self.assertEqual(no.next_sibling, " business")

    def test_replace_first_child(self):
        data = "<a><b></b><c></c></a>"
        soup = self.soup(data)
        soup.b.replace_with(soup.c)
        self.assertEqual("<a><c></c></a>", soup.decode())

    def test_replace_last_child(self):
        data = "<a><b></b><c></c></a>"
        soup = self.soup(data)
        soup.c.replace_with(soup.b)
        self.assertEqual("<a><b></b></a>", soup.decode())

    def test_nested_tag_replace_with(self):
        soup = self.soup(
            """<a>We<b>reserve<c>the</c><d>right</d></b></a><e>to<f>refuse</f><g>service</g></e>""")

        # Replace the entire <b> tag and its contents ("reserve the
        # right") with the <f> tag ("refuse").
        remove_tag = soup.b
        move_tag = soup.f
        remove_tag.replace_with(move_tag)

        self.assertEqual(
            soup.decode(), self.document_for(
                "<a>We<f>refuse</f></a><e>to<g>service</g></e>"))

        # The <b> tag is now an orphan.
        self.assertEqual(remove_tag.parent, None)
        self.assertEqual(remove_tag.find(text="right").next_element, None)
        self.assertEqual(remove_tag.previous_element, None)
        self.assertEqual(remove_tag.next_sibling, None)
        self.assertEqual(remove_tag.previous_sibling, None)

        # The <f> tag is now connected to the <a> tag.
        self.assertEqual(move_tag.parent, soup.a)
        self.assertEqual(move_tag.previous_element, "We")
        self.assertEqual(move_tag.next_element.next_element, soup.e)
        self.assertEqual(move_tag.next_sibling, None)

        # The gap where the <f> tag used to be has been mended, and
        # the word "to" is now connected to the <g> tag.
        to_text = soup.find(text="to")
        g_tag = soup.g
        self.assertEqual(to_text.next_element, g_tag)
        self.assertEqual(to_text.next_sibling, g_tag)
        self.assertEqual(g_tag.previous_element, to_text)
        self.assertEqual(g_tag.previous_sibling, to_text)

    def test_unwrap(self):
        tree = self.soup("""
            <p>Unneeded <em>formatting</em> is unneeded</p>
            """)
        tree.em.unwrap()
        self.assertEqual(tree.em, None)
        self.assertEqual(tree.p.text, "Unneeded formatting is unneeded")

    def test_wrap(self):
        soup = self.soup("I wish I was bold.")
        value = soup.string.wrap(soup.new_tag("b"))
        self.assertEqual(value.decode(), "<b>I wish I was bold.</b>")
        self.assertEqual(
            soup.decode(), self.document_for("<b>I wish I was bold.</b>"))

    def test_wrap_extracts_tag_from_elsewhere(self):
        soup = self.soup("<b></b>I wish I was bold.")
        soup.b.next_sibling.wrap(soup.b)
        self.assertEqual(
            soup.decode(), self.document_for("<b>I wish I was bold.</b>"))

    def test_wrap_puts_new_contents_at_the_end(self):
        soup = self.soup("<b>I like being bold.</b>I wish I was bold.")
        soup.b.next_sibling.wrap(soup.b)
        self.assertEqual(2, len(soup.b.contents))
        self.assertEqual(
            soup.decode(), self.document_for(
                "<b>I like being bold.I wish I was bold.</b>"))

    def test_extract(self):
        soup = self.soup(
            '<html><body>Some content. <div id="nav">Nav crap</div> More content.</body></html>')

        self.assertEqual(len(soup.body.contents), 3)
        extracted = soup.find(id="nav").extract()

        self.assertEqual(
            soup.decode(), "<html><body>Some content.  More content.</body></html>")
        self.assertEqual(extracted.decode(), '<div id="nav">Nav crap</div>')

        # The extracted tag is now an orphan.
        self.assertEqual(len(soup.body.contents), 2)
        self.assertEqual(extracted.parent, None)
        self.assertEqual(extracted.previous_element, None)
        self.assertEqual(extracted.next_element.next_element, None)

        # The gap where the extracted tag used to be has been mended.
        content_1 = soup.find(text="Some content. ")
        content_2 = soup.find(text=" More content.")
        self.assertEqual(content_1.next_element, content_2)
        self.assertEqual(content_1.next_sibling, content_2)
        self.assertEqual(content_2.previous_element, content_1)
        self.assertEqual(content_2.previous_sibling, content_1)

    def test_extract_distinguishes_between_identical_strings(self):
        soup = self.soup("<a>foo</a><b>bar</b>")
        foo_1 = soup.a.string
        bar_1 = soup.b.string
        foo_2 = soup.new_string("foo")
        bar_2 = soup.new_string("bar")
        soup.a.append(foo_2)
        soup.b.append(bar_2)

        # Now there are two identical strings in the <a> tag, and two
        # in the <b> tag. Let's remove the first "foo" and the second
        # "bar".
        foo_1.extract()
        bar_2.extract()
        self.assertEqual(foo_2, soup.a.string)
        self.assertEqual(bar_2, soup.b.string)

    def test_clear(self):
        """Tag.clear()"""
        soup = self.soup("<p><a>String <em>Italicized</em></a> and another</p>")
        # clear using extract()
        a = soup.a
        soup.p.clear()
        self.assertEqual(len(soup.p.contents), 0)
        self.assertTrue(hasattr(a, "contents"))

        # clear using decompose()
        em = a.em
        a.clear(decompose=True)
        self.assertFalse(hasattr(em, "contents"))

    def test_string_set(self):
        """Tag.string = 'string'"""
        soup = self.soup("<a></a> <b><c></c></b>")
        soup.a.string = "foo"
        self.assertEqual(soup.a.contents, ["foo"])
        soup.b.string = "bar"
        self.assertEqual(soup.b.contents, ["bar"])

    def test_string_set_does_not_affect_original_string(self):
        soup = self.soup("<a><b>foo</b><c>bar</c>")
        soup.b.string = soup.c.string
        self.assertEqual(soup.a.encode(), b"<a><b>bar</b><c>bar</c></a>")

    def test_set_string_preserves_class_of_string(self):
        soup = self.soup("<a></a>")
        cdata = CData("foo")
        soup.a.string = cdata
        self.assertTrue(isinstance(soup.a.string, CData))

class TestElementObjects(SoupTest):
    """Test various features of element objects."""

    def test_len(self):
        """The length of an element is its number of children."""
        soup = self.soup("<top>1<b>2</b>3</top>")

        # The BeautifulSoup object itself contains one element: the
        # <top> tag.
        self.assertEqual(len(soup.contents), 1)
        self.assertEqual(len(soup), 1)

        # The <top> tag contains three elements: the text node "1", the
        # <b> tag, and the text node "3".
        self.assertEqual(len(soup.top), 3)
        self.assertEqual(len(soup.top.contents), 3)

    def test_member_access_invokes_find(self):
        """Accessing a Python member .foo invokes find('foo')"""
        soup = self.soup('<b><i></i></b>')
        self.assertEqual(soup.b, soup.find('b'))
        self.assertEqual(soup.b.i, soup.find('b').find('i'))
        self.assertEqual(soup.a, None)

    def test_deprecated_member_access(self):
        soup = self.soup('<b><i></i></b>')
        with warnings.catch_warnings(record=True) as w:
            tag = soup.bTag
        self.assertEqual(soup.b, tag)
        self.assertEqual(
            '.bTag is deprecated, use .find("b") instead.',
            str(w[0].message))

    def test_has_attr(self):
        """has_attr() checks for the presence of an attribute.

        Please note note: has_attr() is different from
        __in__. has_attr() checks the tag's attributes and __in__
        checks the tag's chidlren.
        """
        soup = self.soup("<foo attr='bar'>")
        self.assertTrue(soup.foo.has_attr('attr'))
        self.assertFalse(soup.foo.has_attr('attr2'))


    def test_attributes_come_out_in_alphabetical_order(self):
        markup = '<b a="1" z="5" m="3" f="2" y="4"></b>'
        self.assertSoupEquals(markup, '<b a="1" f="2" m="3" y="4" z="5"></b>')

    def test_string(self):
        # A tag that contains only a text node makes that node
        # available as .string.
        soup = self.soup("<b>foo</b>")
        self.assertEqual(soup.b.string, 'foo')

    def test_empty_tag_has_no_string(self):
        # A tag with no children has no .stirng.
        soup = self.soup("<b></b>")
        self.assertEqual(soup.b.string, None)

    def test_tag_with_multiple_children_has_no_string(self):
        # A tag with no children has no .string.
        soup = self.soup("<a>foo<b></b><b></b></b>")
        self.assertEqual(soup.b.string, None)

        soup = self.soup("<a>foo<b></b>bar</b>")
        self.assertEqual(soup.b.string, None)

        # Even if all the children are strings, due to trickery,
        # it won't work--but this would be a good optimization.
        soup = self.soup("<a>foo</b>")
        soup.a.insert(1, "bar")
        self.assertEqual(soup.a.string, None)

    def test_tag_with_recursive_string_has_string(self):
        # A tag with a single child which has a .string inherits that
        # .string.
        soup = self.soup("<a><b>foo</b></a>")
        self.assertEqual(soup.a.string, "foo")
        self.assertEqual(soup.string, "foo")

    def test_lack_of_string(self):
        """Only a tag containing a single text node has a .string."""
        soup = self.soup("<b>f<i>e</i>o</b>")
        self.assertFalse(soup.b.string)

        soup = self.soup("<b></b>")
        self.assertFalse(soup.b.string)

    def test_all_text(self):
        """Tag.text and Tag.get_text(sep=u"") -> all child text, concatenated"""
        soup = self.soup("<a>a<b>r</b>   <r> t </r></a>")
        self.assertEqual(soup.a.text, "ar  t ")
        self.assertEqual(soup.a.get_text(strip=True), "art")
        self.assertEqual(soup.a.get_text(","), "a,r, , t ")
        self.assertEqual(soup.a.get_text(",", strip=True), "a,r,t")

class TestCDAtaListAttributes(SoupTest):

    """Testing cdata-list attributes like 'class'.
    """
    def test_single_value_becomes_list(self):
        soup = self.soup("<a class='foo'>")
        self.assertEqual(["foo"],soup.a['class'])

    def test_multiple_values_becomes_list(self):
        soup = self.soup("<a class='foo bar'>")
        self.assertEqual(["foo", "bar"], soup.a['class'])

    def test_multiple_values_separated_by_weird_whitespace(self):
        soup = self.soup("<a class='foo\tbar\nbaz'>")
        self.assertEqual(["foo", "bar", "baz"],soup.a['class'])

    def test_attributes_joined_into_string_on_output(self):
        soup = self.soup("<a class='foo\tbar'>")
        self.assertEqual(b'<a class="foo bar"></a>', soup.a.encode())

    def test_accept_charset(self):
        soup = self.soup('<form accept-charset="ISO-8859-1 UTF-8">')
        self.assertEqual(['ISO-8859-1', 'UTF-8'], soup.form['accept-charset'])

    def test_cdata_attribute_applying_only_to_one_tag(self):
        data = '<a accept-charset="ISO-8859-1 UTF-8"></a>'
        soup = self.soup(data)
        # We saw in another test that accept-charset is a cdata-list
        # attribute for the <form> tag. But it's not a cdata-list
        # attribute for any other tag.
        self.assertEqual('ISO-8859-1 UTF-8', soup.a['accept-charset'])


class TestPersistence(SoupTest):
    "Testing features like pickle and deepcopy."

    def setUp(self):
        super(TestPersistence, self).setUp()
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
        self.tree = self.soup(self.page)

    def test_pickle_and_unpickle_identity(self):
        # Pickling a tree, then unpickling it, yields a tree identical
        # to the original.
        dumped = pickle.dumps(self.tree, 2)
        loaded = pickle.loads(dumped)
        self.assertEqual(loaded.__class__, BeautifulSoup)
        self.assertEqual(loaded.decode(), self.tree.decode())

    def test_deepcopy_identity(self):
        # Making a deepcopy of a tree yields an identical tree.
        copied = copy.deepcopy(self.tree)
        self.assertEqual(copied.decode(), self.tree.decode())

    def test_unicode_pickle(self):
        # A tree containing Unicode characters can be pickled.
        html = u"<b>\N{SNOWMAN}</b>"
        soup = self.soup(html)
        dumped = pickle.dumps(soup, pickle.HIGHEST_PROTOCOL)
        loaded = pickle.loads(dumped)
        self.assertEqual(loaded.decode(), soup.decode())


class TestSubstitutions(SoupTest):

    def test_default_formatter_is_minimal(self):
        markup = u"<b>&lt;&lt;Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!&gt;&gt;</b>"
        soup = self.soup(markup)
        decoded = soup.decode(formatter="minimal")
        # The < is converted back into &lt; but the e-with-acute is left alone.
        self.assertEqual(
            decoded,
            self.document_for(
                u"<b>&lt;&lt;Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!&gt;&gt;</b>"))

    def test_formatter_html(self):
        markup = u"<b>&lt;&lt;Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!&gt;&gt;</b>"
        soup = self.soup(markup)
        decoded = soup.decode(formatter="html")
        self.assertEqual(
            decoded,
            self.document_for("<b>&lt;&lt;Sacr&eacute; bleu!&gt;&gt;</b>"))

    def test_formatter_minimal(self):
        markup = u"<b>&lt;&lt;Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!&gt;&gt;</b>"
        soup = self.soup(markup)
        decoded = soup.decode(formatter="minimal")
        # The < is converted back into &lt; but the e-with-acute is left alone.
        self.assertEqual(
            decoded,
            self.document_for(
                u"<b>&lt;&lt;Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!&gt;&gt;</b>"))

    def test_formatter_null(self):
        markup = u"<b>&lt;&lt;Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!&gt;&gt;</b>"
        soup = self.soup(markup)
        decoded = soup.decode(formatter=None)
        # Neither the angle brackets nor the e-with-acute are converted.
        # This is not valid HTML, but it's what the user wanted.
        self.assertEqual(decoded,
                          self.document_for(u"<b><<Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!>></b>"))

    def test_formatter_custom(self):
        markup = u"<b>&lt;foo&gt;</b><b>bar</b>"
        soup = self.soup(markup)
        decoded = soup.decode(formatter = lambda x: x.upper())
        # Instead of normal entity conversion code, the custom
        # callable is called on every string.
        self.assertEqual(
            decoded,
            self.document_for(u"<b><FOO></b><b>BAR</b>"))

    def test_formatter_is_run_on_attribute_values(self):
        markup = u'<a href="http://a.com?a=b&c=é">e</a>'
        soup = self.soup(markup)
        a = soup.a

        expect_minimal = u'<a href="http://a.com?a=b&amp;c=é">e</a>'

        self.assertEqual(expect_minimal, a.decode())
        self.assertEqual(expect_minimal, a.decode(formatter="minimal"))

        expect_html = u'<a href="http://a.com?a=b&amp;c=&eacute;">e</a>'
        self.assertEqual(expect_html, a.decode(formatter="html"))

        self.assertEqual(markup, a.decode(formatter=None))
        expect_upper = u'<a href="HTTP://A.COM?A=B&C=É">E</a>'
        self.assertEqual(expect_upper, a.decode(formatter=lambda x: x.upper()))

    def test_prettify_accepts_formatter(self):
        soup = BeautifulSoup("<html><body>foo</body></html>")
        pretty = soup.prettify(formatter = lambda x: x.upper())
        self.assertTrue("FOO" in pretty)

    def test_prettify_outputs_unicode_by_default(self):
        soup = self.soup("<a></a>")
        self.assertEqual(unicode, type(soup.prettify()))

    def test_prettify_can_encode_data(self):
        soup = self.soup("<a></a>")
        self.assertEqual(bytes, type(soup.prettify("utf-8")))

    def test_html_entity_substitution_off_by_default(self):
        markup = u"<b>Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!</b>"
        soup = self.soup(markup)
        encoded = soup.b.encode("utf-8")
        self.assertEqual(encoded, markup.encode('utf-8'))

    def test_encoding_substitution(self):
        # Here's the <meta> tag saying that a document is
        # encoded in Shift-JIS.
        meta_tag = ('<meta content="text/html; charset=x-sjis" '
                    'http-equiv="Content-type"/>')
        soup = self.soup(meta_tag)

        # Parse the document, and the charset apprears unchanged.
        self.assertEqual(soup.meta['content'], 'text/html; charset=x-sjis')

        # Encode the document into some encoding, and the encoding is
        # substituted into the meta tag.
        utf_8 = soup.encode("utf-8")
        self.assertTrue(b"charset=utf-8" in utf_8)

        euc_jp = soup.encode("euc_jp")
        self.assertTrue(b"charset=euc_jp" in euc_jp)

        shift_jis = soup.encode("shift-jis")
        self.assertTrue(b"charset=shift-jis" in shift_jis)

        utf_16_u = soup.encode("utf-16").decode("utf-16")
        self.assertTrue("charset=utf-16" in utf_16_u)

    def test_encoding_substitution_doesnt_happen_if_tag_is_strained(self):
        markup = ('<head><meta content="text/html; charset=x-sjis" '
                    'http-equiv="Content-type"/></head><pre>foo</pre>')

        # Beautiful Soup used to try to rewrite the meta tag even if the
        # meta tag got filtered out by the strainer. This test makes
        # sure that doesn't happen.
        strainer = SoupStrainer('pre')
        soup = self.soup(markup, parse_only=strainer)
        self.assertEqual(soup.contents[0].name, 'pre')

class TestEncoding(SoupTest):
    """Test the ability to encode objects into strings."""

    def test_unicode_string_can_be_encoded(self):
        html = u"<b>\N{SNOWMAN}</b>"
        soup = self.soup(html)
        self.assertEqual(soup.b.string.encode("utf-8"),
                          u"\N{SNOWMAN}".encode("utf-8"))

    def test_tag_containing_unicode_string_can_be_encoded(self):
        html = u"<b>\N{SNOWMAN}</b>"
        soup = self.soup(html)
        self.assertEqual(
            soup.b.encode("utf-8"), html.encode("utf-8"))

    def test_encoding_substitutes_unrecognized_characters_by_default(self):
        html = u"<b>\N{SNOWMAN}</b>"
        soup = self.soup(html)
        self.assertEqual(soup.b.encode("ascii"), b"<b>&#9731;</b>")

    def test_encoding_can_be_made_strict(self):
        html = u"<b>\N{SNOWMAN}</b>"
        soup = self.soup(html)
        self.assertRaises(
            UnicodeEncodeError, soup.encode, "ascii", errors="strict")

    def test_decode_contents(self):
        html = u"<b>\N{SNOWMAN}</b>"
        soup = self.soup(html)
        self.assertEqual(u"\N{SNOWMAN}", soup.b.decode_contents())

    def test_encode_contents(self):
        html = u"<b>\N{SNOWMAN}</b>"
        soup = self.soup(html)
        self.assertEqual(
            u"\N{SNOWMAN}".encode("utf8"), soup.b.encode_contents(
                encoding="utf8"))

    def test_deprecated_renderContents(self):
        html = u"<b>\N{SNOWMAN}</b>"
        soup = self.soup(html)
        self.assertEqual(
            u"\N{SNOWMAN}".encode("utf8"), soup.b.renderContents())

class TestNavigableStringSubclasses(SoupTest):

    def test_cdata(self):
        # None of the current builders turn CDATA sections into CData
        # objects, but you can create them manually.
        soup = self.soup("")
        cdata = CData("foo")
        soup.insert(1, cdata)
        self.assertEqual(str(soup), "<![CDATA[foo]]>")
        self.assertEqual(soup.find(text="foo"), "foo")
        self.assertEqual(soup.contents[0], "foo")

    def test_cdata_is_never_formatted(self):
        """Text inside a CData object is passed into the formatter.

        But the return value is ignored.
        """

        self.count = 0
        def increment(*args):
            self.count += 1
            return "BITTER FAILURE"

        soup = self.soup("")
        cdata = CData("<><><>")
        soup.insert(1, cdata)
        self.assertEqual(
            b"<![CDATA[<><><>]]>", soup.encode(formatter=increment))
        self.assertEqual(1, self.count)

    def test_doctype_ends_in_newline(self):
        # Unlike other NavigableString subclasses, a DOCTYPE always ends
        # in a newline.
        doctype = Doctype("foo")
        soup = self.soup("")
        soup.insert(1, doctype)
        self.assertEqual(soup.encode(), b"<!DOCTYPE foo>\n")


class TestSoupSelector(TreeTest):

    HTML = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
"http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<title>The title</title>
<link rel="stylesheet" href="blah.css" type="text/css" id="l1">
</head>
<body>

<div id="main">
<div id="inner">
<h1 id="header1">An H1</h1>
<p>Some text</p>
<p class="onep" id="p1">Some more text</p>
<h2 id="header2">An H2</h2>
<p class="class1 class2 class3" id="pmulti">Another</p>
<a href="http://bob.example.org/" rel="friend met" id="bob">Bob</a>
<h2 id="header3">Another H2</h2>
<a id="me" href="http://simonwillison.net/" rel="me">me</a>
<span class="s1">
<a href="#" id="s1a1">span1a1</a>
<a href="#" id="s1a2">span1a2 <span id="s1a2s1">test</span></a>
<span class="span2">
<a href="#" id="s2a1">span2a1</a>
</span>
<span class="span3"></span>
</span>
</div>
<p lang="en" id="lang-en">English</p>
<p lang="en-gb" id="lang-en-gb">English UK</p>
<p lang="en-us" id="lang-en-us">English US</p>
<p lang="fr" id="lang-fr">French</p>
</div>

<div id="footer">
</div>
"""

    def setUp(self):
        self.soup = BeautifulSoup(self.HTML)

    def assertSelects(self, selector, expected_ids):
        el_ids = [el['id'] for el in self.soup.select(selector)]
        el_ids.sort()
        expected_ids.sort()
        self.assertEqual(expected_ids, el_ids,
            "Selector %s, expected [%s], got [%s]" % (
                selector, ', '.join(expected_ids), ', '.join(el_ids)
            )
        )

    assertSelect = assertSelects

    def assertSelectMultiple(self, *tests):
        for selector, expected_ids in tests:
            self.assertSelect(selector, expected_ids)

    def test_one_tag_one(self):
        els = self.soup.select('title')
        self.assertEqual(len(els), 1)
        self.assertEqual(els[0].name, 'title')
        self.assertEqual(els[0].contents, [u'The title'])

    def test_one_tag_many(self):
        els = self.soup.select('div')
        self.assertEqual(len(els), 3)
        for div in els:
            self.assertEqual(div.name, 'div')

    def test_tag_in_tag_one(self):
        els = self.soup.select('div div')
        self.assertSelects('div div', ['inner'])

    def test_tag_in_tag_many(self):
        for selector in ('html div', 'html body div', 'body div'):
            self.assertSelects(selector, ['main', 'inner', 'footer'])

    def test_tag_no_match(self):
        self.assertEqual(len(self.soup.select('del')), 0)

    def test_invalid_tag(self):
        self.assertEqual(len(self.soup.select('tag%t')), 0)

    def test_header_tags(self):
        self.assertSelectMultiple(
            ('h1', ['header1']),
            ('h2', ['header2', 'header3']),
        )

    def test_class_one(self):
        for selector in ('.onep', 'p.onep', 'html p.onep'):
            els = self.soup.select(selector)
            self.assertEqual(len(els), 1)
            self.assertEqual(els[0].name, 'p')
            self.assertEqual(els[0]['class'], ['onep'])

    def test_class_mismatched_tag(self):
        els = self.soup.select('div.onep')
        self.assertEqual(len(els), 0)

    def test_one_id(self):
        for selector in ('div#inner', '#inner', 'div div#inner'):
            self.assertSelects(selector, ['inner'])

    def test_bad_id(self):
        els = self.soup.select('#doesnotexist')
        self.assertEqual(len(els), 0)

    def test_items_in_id(self):
        els = self.soup.select('div#inner p')
        self.assertEqual(len(els), 3)
        for el in els:
            self.assertEqual(el.name, 'p')
        self.assertEqual(els[1]['class'], ['onep'])
        self.assertFalse(els[0].has_key('class'))

    def test_a_bunch_of_emptys(self):
        for selector in ('div#main del', 'div#main div.oops', 'div div#main'):
            self.assertEqual(len(self.soup.select(selector)), 0)

    def test_multi_class_support(self):
        for selector in ('.class1', 'p.class1', '.class2', 'p.class2',
            '.class3', 'p.class3', 'html p.class2', 'div#inner .class2'):
            self.assertSelects(selector, ['pmulti'])

    def test_multi_class_selection(self):
        for selector in ('.class1.class3', '.class3.class2',
                         '.class1.class2.class3'):
            self.assertSelects(selector, ['pmulti'])

    def test_child_selector(self):
        self.assertSelects('.s1 > a', ['s1a1', 's1a2'])
        self.assertSelects('.s1 > a span', ['s1a2s1'])

    def test_attribute_equals(self):
        self.assertSelectMultiple(
            ('p[class="onep"]', ['p1']),
            ('p[id="p1"]', ['p1']),
            ('[class="onep"]', ['p1']),
            ('[id="p1"]', ['p1']),
            ('link[rel="stylesheet"]', ['l1']),
            ('link[type="text/css"]', ['l1']),
            ('link[href="blah.css"]', ['l1']),
            ('link[href="no-blah.css"]', []),
            ('[rel="stylesheet"]', ['l1']),
            ('[type="text/css"]', ['l1']),
            ('[href="blah.css"]', ['l1']),
            ('[href="no-blah.css"]', []),
            ('p[href="no-blah.css"]', []),
            ('[href="no-blah.css"]', []),
        )

    def test_attribute_tilde(self):
        self.assertSelectMultiple(
            ('p[class~="class1"]', ['pmulti']),
            ('p[class~="class2"]', ['pmulti']),
            ('p[class~="class3"]', ['pmulti']),
            ('[class~="class1"]', ['pmulti']),
            ('[class~="class2"]', ['pmulti']),
            ('[class~="class3"]', ['pmulti']),
            ('a[rel~="friend"]', ['bob']),
            ('a[rel~="met"]', ['bob']),
            ('[rel~="friend"]', ['bob']),
            ('[rel~="met"]', ['bob']),
        )

    def test_attribute_startswith(self):
        self.assertSelectMultiple(
            ('[rel^="style"]', ['l1']),
            ('link[rel^="style"]', ['l1']),
            ('notlink[rel^="notstyle"]', []),
            ('[rel^="notstyle"]', []),
            ('link[rel^="notstyle"]', []),
            ('link[href^="bla"]', ['l1']),
            ('a[href^="http://"]', ['bob', 'me']),
            ('[href^="http://"]', ['bob', 'me']),
            ('[id^="p"]', ['pmulti', 'p1']),
            ('[id^="m"]', ['me', 'main']),
            ('div[id^="m"]', ['main']),
            ('a[id^="m"]', ['me']),
        )

    def test_attribute_endswith(self):
        self.assertSelectMultiple(
            ('[href$=".css"]', ['l1']),
            ('link[href$=".css"]', ['l1']),
            ('link[id$="1"]', ['l1']),
            ('[id$="1"]', ['l1', 'p1', 'header1', 's1a1', 's2a1', 's1a2s1']),
            ('div[id$="1"]', []),
            ('[id$="noending"]', []),
        )

    def test_attribute_contains(self):
        self.assertSelectMultiple(
            # From test_attribute_startswith
            ('[rel*="style"]', ['l1']),
            ('link[rel*="style"]', ['l1']),
            ('notlink[rel*="notstyle"]', []),
            ('[rel*="notstyle"]', []),
            ('link[rel*="notstyle"]', []),
            ('link[href*="bla"]', ['l1']),
            ('a[href*="http://"]', ['bob', 'me']),
            ('[href*="http://"]', ['bob', 'me']),
            ('[id*="p"]', ['pmulti', 'p1']),
            ('div[id*="m"]', ['main']),
            ('a[id*="m"]', ['me']),
            # From test_attribute_endswith
            ('[href*=".css"]', ['l1']),
            ('link[href*=".css"]', ['l1']),
            ('link[id*="1"]', ['l1']),
            ('[id*="1"]', ['l1', 'p1', 'header1', 's1a1', 's1a2', 's2a1', 's1a2s1']),
            ('div[id*="1"]', []),
            ('[id*="noending"]', []),
            # New for this test
            ('[href*="."]', ['bob', 'me', 'l1']),
            ('a[href*="."]', ['bob', 'me']),
            ('link[href*="."]', ['l1']),
            ('div[id*="n"]', ['main', 'inner']),
            ('div[id*="nn"]', ['inner']),
        )

    def test_attribute_exact_or_hypen(self):
        self.assertSelectMultiple(
            ('p[lang|="en"]', ['lang-en', 'lang-en-gb', 'lang-en-us']),
            ('[lang|="en"]', ['lang-en', 'lang-en-gb', 'lang-en-us']),
            ('p[lang|="fr"]', ['lang-fr']),
            ('p[lang|="gb"]', []),
        )

    def test_attribute_exists(self):
        self.assertSelectMultiple(
            ('[rel]', ['l1', 'bob', 'me']),
            ('link[rel]', ['l1']),
            ('a[rel]', ['bob', 'me']),
            ('[lang]', ['lang-en', 'lang-en-gb', 'lang-en-us', 'lang-fr']),
            ('p[class]', ['p1', 'pmulti']),
            ('[blah]', []),
            ('p[blah]', []),
        )

    def test_select_on_element(self):
        # Other tests operate on the tree; this operates on an element
        # within the tree.
        inner = self.soup.find("div", id="main")
        selected = inner.select("div")
        # The <div id="inner"> tag was selected. The <div id="footer">
        # tag was not.
        self.assertSelectsIDs(selected, ['inner'])

########NEW FILE########
__FILENAME__ = convert_edge_list
# -*- coding: utf-8 -*- 

import os
import sys

from itertools import count, izip
from collections import OrderedDict, Set

class IndexOrderedSet(Set):
    """An OrderedFrozenSet-like object
       Allows constant time 'index'ing
       But doesn't allow you to remove elements"""
    def __init__(self, iterable = ()):
        self.num = count()
        self.dict = OrderedDict(izip(iterable, self.num))
    def add(self, elem):
        if elem not in self:
            self.dict[elem] = next(self.num)
    def index(self, elem):
        return self.dict[elem]
    def __contains__(self, elem):
        return elem in self.dict
    def __len__(self):
        return len(self.dict)
    def __iter__(self):
        return iter(self.dict)
    def __repr__(self):
        return 'IndexOrderedSet({})'.format(self.dict.keys())
        
        
def getuidindex(uid,uid_list):
    '''
    获得uid(string)在表list[strings]中的位置
    返回 -1 如果不再表内
    '''
    i=-1
    if uid in uid_list:
        i = uid_list.index(uid)
        
    return i
    
def help():
    print "\t usage: python convert_userid_result.py relation_file.txt"
    print "\t note file must has .txt!"
    print "\t will translate ID to uid in .edgelist file,according to mapping in .map file."

    
    
if __name__ == '__main__':
    try:
        oldfile = sys.argv[1]
        oldfilebase = os.path.splitext(sys.argv[1])[0]
    except:
        help()
        exit()
    print 'converting relation(uid uid) to relation(index index) to edge list,weight free:',
    print oldfile
    newlines=[]
    #get src dst
    uid_list = []
    uid_set = IndexOrderedSet()
    pairs = []
    with open(oldfile) as f:
        count = 0
        for i in f.readlines():
            if i:
                count += 1
                if count % 10000 == 0:
                    print "已读取Edge:",count,"个"
                i = i.rstrip('\n')
                i = i.rstrip('\r')
                res = i.split('\t')
                src = int(res[0])
                dst = int(res[1])
                if src not in uid_set:
                    #uid_list.append(src)
                    uid_set.add(src)
                if dst not in uid_set:
                    #uid_list.append(dst)
                    uid_set.add(dst)
                pairs.append((src,dst))
        f.close()
    print "读取Edges完成"
    #sort mapping list
    #uid_set = set(uid_list)
    ##uid_list = []
    #for i in uid_set:
    #    i=int(i)
    #    uid_list.append(i)
    
    # trans pairs: 123141224 \t 1251231412 to 55 \t 43
    # save to .edgelist
    count = 0
    for pair in pairs:
        count+=1
        if count % 10000 == 0:
            print "已处理Edge:",count,"个"
        src,dst = pair
        isrc = uid_set.index(src) #getuidindex(src,uid_list)
        idst = uid_set.index(dst) #,uid_list)
        newline = str(isrc) + '\t' + str(idst) + '\n'
        newlines.extend(newline)
        #print isrc,' ,',idst
        
    
    newfile = oldfilebase + '.edgelist.txt'
    with open(newfile,'w') as f:
        f.writelines(newlines)
        f.close()
        
    # record mapping uid to index
    # save to .map
    mapfile = oldfilebase +'.map.txt'
    newlines = []
    for uid in uid_set:
        newline = str(uid) + '\t' + str(uid_set.index(uid)) + '\n'
        newlines.append(newline)
    with open(mapfile,'w') as f:
        f.writelines(newlines)
        f.close()
    
    print 'converting finished,gen 2 new file:'
    print newfile
    print mapfile
    
########NEW FILE########
__FILENAME__ = convert_userid_result
# -*- coding: utf-8 -*- 

import os
import sys

#处理前TOPN名用户
TOPN = 20

def getuidindex(uid,uid_list):
    '''
    获得uid(string)在表list[strings]中的位置
    返回 -1 如果不再表内
    '''
    i=-1
    if uid in uid_list:
        i = uid_list.index(uid)
        
    return i
    
def help():
    print "\t usage: python convert_userid_result.py relation_file.rank"
    print "\t will translate ID to uid in .rank file,according to .map file."
    print "\t .rank could be any other string, e.g. salsa,pagerank, etc."
    
if __name__ == '__main__':

    try:
        srcfile = sys.argv[1]
        resfile = srcfile+'.uid.txt'
    except:
        help()
        exit()
        
    tmp = os.path.splitext(sys.argv[1])[0]
    mapfile = os.path.splitext(tmp)[0] + '.map.txt'

    print 'convert rank result file to:'
    print resfile
    print 'using mapfile:'
    print mapfile

    #get mapping
    uid_list = []
    with open(mapfile) as f:
        for line in f.readlines():
            if line:
                uid = line.split()[0]        
                uid_list.append(int(uid))
        f.close()
    
    
    
    
    #get rank res from srcfile:
    #Print top 20 vertices:(blank with \t)
    #1. 27	0.772947
    #2. 19	0.739721
    #3. 25	0.710808
    oldlines = []
    with open(srcfile) as f:
        for i in f.readlines():
            oldlines.append(i)
        f.close()
        
    #处理前20名
    newlines = [ oldlines[0]]
    for line in oldlines:
        if oldlines.index(line) < TOPN+1 and oldlines.index(line)>0:
            res = line.split()
            mapID = res[1]
            uid = str(uid_list[int(mapID)])
            print mapID,'->',uid
            res[1] = uid
            newline = ''
            for i in res:
                newline+= i+' '
            newline+='\n'
            newlines.append(newline)
            
    newlines.extend( oldlines[TOPN+1:])
    #写入结果 resfile
    with open(resfile,'w') as f:
        f.writelines(newlines)
        f.close()
                
    print 'converted rankfile,gen 1 new file:'
    print resfile
    
########NEW FILE########
__FILENAME__ = getRelation
# # -*- coding: utf-8 -*-  
import sys


"""
这是一个新浪微群爬虫。目前只有命令行界面。
使用方法：下回分解。
"""
__author__ =  'David Lau'
__version__=  '0.1'
__nonsense__ = 'weiqun crawler,relation txt generator'

#导入sina_reptile
from sina_reptile import *
from simplecrawlerWAP import *


        
                
if __name__ == '__main__':
    LOGIN_URL = 'http://weibo.cn' #测试用户登陆用
    
    #!编码重要:设置python(2.7.3)的内部处理encoding使用utf-8(默认ascii),以确保能在mac命令行下python执行本文件
    #详见http://docs.python.org/2/howto/unicode.html
    reload(sys)
    sys.setdefaultencoding('utf-8')
    print '系统编码：'
    print sys.getdefaultencoding()
    
        #Trap time stamp    
    LAST_TRAP_TIME = datetime.datetime.now()
    #cookie
    #填写用户COOKIE
    COOKIE1 = 'gsid_CTandWM=4KxsCpOz1GZCmdnhIRfo3dyGpfe;_WEIBO_UID=3231589944'#david
    COOKIE2 = '_WEIBO_UID=3231589944; gsid_CTandWM=4KigCpOz1kJGN62tgSyo96K5D9h'#jion
    COOKIE3 = '_WEIBO_UID=3231589944; gsid_CTandWM=4KfJCpOz1RtwETBsrTJiC7bgieU'#mie
    COOKIE4 = 'gsid_CTandWM=4KHACpOz15FImpwmD6Dq2dJ48aI; _WEIBO_UID=3271500664'#miemiemie
    COOKIE5 = '_WEIBO_UID=3271500664; gsid_CTandWM=4KNhCpOz1mRs5r4AA9S1adTAz7N'#my reg
    COOKIE = COOKIE5
    COOKIES = [COOKIE1,COOKIE2,COOKIE3,COOKIE4,COOKIE5]
    HEADERS_LOGIN = { "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",\
                "Accept-Charset":"GBK,utf-8;q=0.7,*;q=0.3",\
                'Accept-Encoding':'gzip,deflate,sdch',#这里告知服务器，可以用gzip压缩包传递html\ 
                'Accept-Language':'zh-CN,zh;q=0.8',\
                "Connection":"keep-alive",\
                "Host":"weibo.cn",\
                "Cookie": COOKIE,\
                "Referer":'''http://newlogin.sina.cn/crossDomain/?g=4KigCpOz1kJGN62tgSyo96K5D9h&t=1364395377&m=cdba&r=&u=http%3A%2F%2Fweibo.cn%2F%3Fgsid%3D4KigCpOz1kJGN62tgSyo96K5D9h%26vt%3D4&cross=1&vt=4''',\
                "User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_3) AppleWebKit/537.22 (KHTML, like Gecko) Chrome/25.0.1364.172 Safari/537.22",\
                }
          
    HEADERS_WEIQUN = {"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",\
                    'Accept-Encoding':'gzip,deflate',#这里告知服务器，可以用gzip压缩包传递html\ 
                    'Accept-Language':'zh-cn,zh;q=0.8,en-us;q=0.5,en;q=0.3',\
                    'Connection':'keep-alive',\
                    'Cookie':COOKIE,\
                    'Host':'q.weibo.cn',\
                    'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:17.0) Gecko/20100101 Firefox/17.0',\
                }    
                
    userdbname = '../users.db'
    weiquns = [] 
    startpage=1

    
                   
    #读取 weiqun2download.txt 的微群号,下载总页数
    weiqunparas = []
    weiqunids = []     
    print '从weiqun2download.txt读取准备下载的weiqunids:'
    weiqunlist = 'weiqun2download.txt'
    with open(weiqunlist) as f:
        for i in f.readlines():
            res = re.sub('#',' ',i).split(' ')
            weiqunid = res[0].strip()
            endpage = int(res[1].strip())
            startpage = 1
            print  'weiqunid:',weiqunid
            print  'page:',startpage,'~',endpage
            weiqunparas.append( (weiqunid,startpage,endpage) )

        
    
    #wrap 微群crawler参数        
    for para in weiqunparas:
        weiqunid,startpage,endpage = para
        weiqun = ('../weiqun/%d'%int(weiqunid),'../weiqun/%d.db'%int(weiqunid),userdbname,'../users',weiqunid,startpage,endpage,LOGIN_URL)
        weiquns.append(weiqun)
        weiqunids.append(weiqunid)
            
    #初始化多个crawler
    crawlers = []
    for weiqun in weiquns[0:]:
        savedir,weibodbname,userdbname,usersdir,weiqunid,startpage,endpage,login_url = weiqun
    
        #初始化爬虫类
        crawler = Weiqun_crawler(weibodbname,userdbname,usersdir,savedir,weiqunid,startpage,endpage,HEADERS_WEIQUN,HEADERS_LOGIN,COOKIES,login_url ,4)
        crawlers.append(crawler)
        
    for crawler in crawlers:
            #--------------------------从微群db中读取用户，从users.db中读取用户关系，生成用户关系txt文件，格式：FolloerID\tUserID\n----------------------------- 
            crawler.get_user_relation_txt()
            

########NEW FILE########
__FILENAME__ = simplecrawlerWAP
# # -*- coding: utf-8 -*-  
import sys


"""
这是一个新浪微群爬虫。目前只有命令行界面。
使用方法：下回分解。
"""
__author__ =  'David Lau'
__version__=  '0.1'
__nonsense__ = 'weiqun crawler'

#导入sina_reptile
from sina_reptile import *

#调试HTTP Web服务
import httplib
httplib.HTTPConnection.debuglevel = 0

#数据库 Beautiful Soup库
import sqlite3 as sqlite
from bs4 import BeautifulSoup

#url处理
import urlparse

#处理gzip
import StringIO
import StringIO
import gzip
import urllib2
import re
import os
import sys
import datetime
import time
import itertools
import termios
import fcntl
"""
Login to Sina Weibo with cookie
"""
PAGE_REQUEST_ERROR = '请求页不存在'
PAGE_REDIRECT = '如果没有自动跳转,请'
NOBODY_POST_THIS_PAGE = '你加入的群还没有人说话!'
NO_REPLY = '还没有人针对这条微博发表评论!'
WEIBO_SQUARE ='微博广场'
USERPROFILE_PREFIX = 'http://weibo.cn/%s/profile'#uid个人主页
#一般fans/follows第i页的url: http://weibo.cn/uid/fans?page=[i]
FANPAGE_PREFIX = 'http://weibo.cn/%s/fans'#uid的粉丝用户页面
FOPAGE_PREFIX = 'http://weibo.cn/%s/follow'#uid的关注用户页面
FANPAGE_SURFFIX = '?page=%s&st=c23d'
FOPAGE_SURFFIX = '?page=%s&st=c23d'
WEIBO_PER_PAGE = 10

MEET_TRAP = 99

#trap times 记录次数 到一定值则换cookie
TRAP_TIMES = 0


WEIQUN_BASE='http://q.weibo.cn/group/'   

    
def fromUTF8toSysCoding(html):
    '''
    decode and encode with sysencoding
    '''
    syscodetype = sys.getfilesystemencoding()
    return html.decode('utf-8').encode(syscodetype)

def degzip(compresseddata):
    '''
    decompress gzip (html) file,return ungzip html string
    '''
    if(compresseddata[0:3]=='\x1f\x8b\x08'):
        compressedstream = StringIO.StringIO(compresseddata)
        gzipper = gzip.GzipFile(fileobj=compressedstream)
        html = gzipper.read() 
        return html
    else:
        return compresseddata
    
def storehtml(html,path,url=None,showdetail=True):
    '''
    将html存到磁盘path (html来源url)
    #没有文件夹则建立
    '''
    (basename,filename) = os.path.split(path)
    if not os.path.exists(basename):
        os.makedirs(basename)
    #建立文件
    try:
        fd = open(path,'w')#w+模式代表截断（或清空）文件，然后打开文件用于写
        fd.write(html)
        if showdetail:
            print "网页保存到本地"+path+',\turl='+url
    except Exception,E:
        if showdetail:
            print "网页保存到本地"+path+',\turl='+url
    finally:
        fd.close()
      
def urlprocessor(url,header,absUrl=True):
    '''
    带cookie(header)下载url页面html，检查html是否gzip压缩，有则解压；
    需要用Firebug查看浏览器访问时发送的GET headers（包括cookie），模拟，才可以正常访问；否则返回无法找到该页。
    返回: None 错误
         html 正常下载页面内容
    '''
    try:
        req = urllib2.Request(url, headers=header)
        f = urllib2.urlopen(req)
        html = f.read()
        '''
        #解压缩get得到的网页gzip包
        if(f.headers.get('Content-Encoding') == 'gzip'):
            html = degzip(html)

        #把相对地址替换成绝对地址
        if absUrl:
            html = getAbsUrl(url,html)   
        return html 
        '''
    except Exception,E:
        print "urlprocessor():下载页面错误："+url+'，错误代码:'+str(E)
        return None
    
    if html: 
        #解压缩get得到的网页gzip包
        if(f.headers.get('Content-Encoding') == 'gzip'):
            html = degzip(html)
    
        #把相对地址替换成绝对地址
        if absUrl:
            html = getAbsUrl(url,html)   
        
        return html
    else:
        return None
    
def getAbsUrl(base,html):
    '''
    用re把html内的相对地址替换成绝对地址,返回带绝对地址的html
    '''
    regex = '<a href="(.+?)"'
    reobj = re.compile(regex)
    #找出所有相对地址，存放在reladdrList中
    reladdrList = reobj.findall(html)
    for reladdr in reladdrList:
        if ':'  not in reladdr:
            #补全相对地址为绝对地址url,用re替换
            url = urlparse.urljoin(base,reladdr)
            #print "getAbsUrl()处理相对地址："+reladdr
            html = html.replace('<a href="'+reladdr,'<a href="'+url)
    return html
    
def testgetAbsUrl():
    '''
    测试testgetAbsUrl
    '''
    html = '''<div><a href="/profile/1808877652">Nulooper</a><span class="ctt">:NLP初学者报道，希望多多指教</span>&nbsp;<a href="/group/viewRt/225241/103r08nr6th">转发</a>&nbsp;<a href="/group/review/225241/103r08nr6th?&amp;#cmtfrm" class="cc">评论[0]</a>&nbsp;&nbsp;<span class="ct">01月26日 19:30</span></div>'''
    weiqunUrl = 'http://q.weibo.cn/group/225241/'
    html = getAbsUrl(weiqunUrl,html)
    print html

class Weiqun_crawler:
    '''
    微群爬虫类
    '''
    def __init__(self,weibodbname,userdbname,usersdir,savedir,weiqunID,startpage,endpage,headers_weiqun,headers_login,cookies_list,loginurl,begin_with_cookie_n=None):
        '''
        初始化类，设置保存地址，微群号，连接数据库
        '''
        print '----------- 初始化微群爬虫 id:%s -----------'%weiqunID
        #header cookie
        self.begin_with_cookie_n = begin_with_cookie_n
        self.cookies = []
        self.cookies.extend(cookies_list)
        self.cookie_iter = itertools.cycle(self.cookies)
        self.headers_weiqun = headers_weiqun
        self.headers_login = headers_login
        self.cur_cookie = ''
        self.change_cookie_times = 0 #改变cookie的次数
        self.loginurl= loginurl
        self.init_cookie_headers()
        
        #下载网页保存地址
        self.savedir = savedir
        self.weiqunID = str(weiqunID)
        self.usersdir = usersdir
        #扫微群页数
        self.startpage = startpage
        self.endpage = endpage
        #数据库名称
        self.weibodbname = weibodbname
        self.userdbname = userdbname
        #设置微博数据库
        print self.weibodbname
        self.con_weibo = sqlite.connect(self.weibodbname)
        self.cur_weibo = self.con_weibo.cursor()
        #设置用户数据库
        self.con_user = sqlite.connect(self.userdbname)
        self.cur_user = self.con_user.cursor()
        #初始化db表
        self.createweibostable()
        self.createuserstable()
        
        #析取微博信息
        self.allweiboinfos = [] #weiboinfo={raw,id,content...见db table weibos}
        self.replyinfos=[]#储存replyinfo{weiboid,...}(同数据库中weibos的item)
        self.rtinfos=[]#同上
        self.profiles=[]#储存profile={userid,username,weibos微博数,followers粉丝数,followings关注数}
        self.failed_reply_paths=[]#储存分析失败的reply.html路径，需要重新爬取
        self.failed_rt_paths=[]#同上
        #给crawler.cralw..函数返回用 或db网页下载状态用
        self.STATUS_FAILED = 2
        self.STATUS_DOWNLOADED = 1
        self.STATUS_UNDOWNLOAD = 0
        #上次爬虫下载的内容,用与self.is_trap
        self.last_crawl_html = ''
        
        #要下载的微群页表 类型ints
        self.weiqun_pages2download=[]

    def __del__(self):
        '''
        关闭数据库连接
        '''
        #print '----------- 销毁微群爬虫 id:%s -----------'%self.weiqunID
        self.con_weibo.close()
        self.con_user.close()
        
        
    def init_cookie_headers(self):
        #设置开始爬行使用的用户COOKIE
        if self.begin_with_cookie_n is not None: 
            if len(self.cookies) >= self.begin_with_cookie_n:
                if self.begin_with_cookie_n >= 0:
                    self.cur_cookie = self.cookies[self.begin_with_cookie_n]
                    self.headers_weiqun.update({'Cookie':self.cur_cookie})
                    self.headers_login.update({'Cookie':self.cur_cookie})
                    #print 'INIT COOKIE!!!!!!!!!!!!!!!!!!!!!'
                    #self.test_login('http://weibo.cn')
                    return
        #如果没有设置开始用户,则佢第0个COOKIE        
        self.cur_cookie = self.cookies[0]
        self.headers_weiqun.update({'Cookie':self.cur_cookie})
        self.headers_login.update({'Cookie':self.cur_cookie})
        #print 'INIT COOKIE!!!!!!!!!!!!!!!!!!!!!'
        #self.test_login('http://weibo.cn')
        
    def change_cookie_headers(self):
        self.cur_cookie = self.cookie_iter.next()
        self.headers_weiqun.update({'Cookie':self.cur_cookie})
        self.headers_login.update({'Cookie':self.cur_cookie})
        print 'CHANGE COOKIE!!!!!!!!!!!!!!!!!!!!!'
        self.test_login('http://weibo.cn')
        self.change_cookie_times+=1

    def get_user_relation_txt(self):
        '''
        从指定self.微群id 的db获取users,从user.db获取users的关系: follower_uid target_uid
        输出: user_relation_weiqunID.txt (Win CRLF Ansi?)
                第一个用户id标示源用户id，第二个用户id标示目标用户id，源用户关注目标用户
             user_list_all_weiqunID.txt (CRLF)
                每行是所有在关系里出现过的uid unique
        返回:True 成功
            False 失败 读取数据库时
            None 无查询结果
        '''
        print 'get_user_relation_txt: 正在生成用户关系对txt  weiqun=%s'% str(self.weiqunID)
        count = 0
        #选择某微群的所有用户
        sql_weiqundb = ''' SELECT DISTINCT userid FROM weibos ;'''
        #选择某用户的所有关系
        sql_usersdb = ''' SELECT followerid,userid FROM relation WHERE userid=='%s' or followerid=='%s' ;'''
        
        #-----------获取微群db的用户列表--------------------------------------------------------- 
        try:
            self.cur_weibo.execute(sql_weiqundb)
            self.dbcommit()
        except Exception,E:
            print 'get_user_relation_txt 数据库操作错误sql:%s'%sql_weiqundb
            print E
            return False
        userids = []
        res = self.cur_weibo.fetchall()
        if len(res)<1:#查询不到东西 返回None
            print 'get_user_relation_txt:微群%s的数据库%s中没有用户'%(self.weiqunID,self.weiqunID+'.db')
            return None            
        else:#有查询结果(有用户) ,添加到用户列表中userids
            for row in res:
                userid, = row
                #print userid
                #print type(userid)
                if userid not in userids:
                    userids.append(str(userid))
        
        #-----------获取users.db的用户关系--------------------------------------------------------- 
        print 'get_user_relation_txt:正在从users.db读取%d个用户的关系'%len(userids)
        relations = []
        for userid in userids:
            #print '\t获取用户关系uid:%s'%str(userid)
            try:
                self.cur_user.execute(sql_usersdb % (userid,userid))
                self.dbcommit()
            except Exception,E:
                print 'get_user_relation_txt 数据库操作错误sql:%s'%(sql_usersdb % (userid,userid))
                print E
                return False
            res2 = self.cur_user.fetchall()
            
            if len(res2)<1:#查询不到某个用户的关系 跳过
                print 'get_user_relation_txt:users.db中没有微群:%s,uid=%s的用户关系'%(self.weiqunID+'.db',userid)
                #return None
                continue            
            else:#有查询结果(有用户关系) ,添加到用户列表中userids
                for row in res2:
                    followerid,userid = row
                    relation = (followerid,userid)
                    #!!!!!!!!! 可能有重复的 !!!!!!!!!!!
                    relations.append(relation)
                    count+=1
                
        #写到文件中:user_relation_weiqunID.txt (CRLF)
        path = '../weiqun/user_relation_%s.txt' % str(self.weiqunID)
        txtlines = []
        relations.sort()
        for rela in relations:
            followerid,userid = rela
            txtline = str(followerid) + '\t' + str(userid) +'\r\n'
            txtlines.append(txtline)
        with open(path,'w') as f:
            f.writelines(txtlines)
            f.close()
            
        #写到文件中:user_list_all_weiqunID.txt (CRLF)
        usernum=0
        path = '../weiqun/user_list_all_%s.txt' % str(self.weiqunID)
        txtlines = []
        all_uid = set([])#use set as dinstinct list,fast!!
        for rela in relations:
            followerid,userid = rela
            if followerid not in all_uid:
                all_uid.add(followerid)
            if userid not in all_uid:
                all_uid.add(userid) 
        
        all_uid = [i for i in all_uid]
        all_uid.sort()
        for userid in all_uid:
            txtline = str(userid) +'\r\n'
            usernum+=1
            txtlines.append(txtline)
            
        with open(path,'w') as f:
            f.writelines(txtlines)
            f.close()
            
                
        print 'got_user_relation_txt: weiqun=%s'% (str(self.weiqunID))
        print '\t有关注关系',count
        print '\t所有用户(出现在关注关系中的)',usernum
        
    def load_weiqun_pages2download(self):
        '''
        任务:返回未下载\陷阱的微群页(微群id=self.weiqunID),
            更改:
            self.weiqun_pages2download[] of int(page)s
        返回:self.weiqun_pages2download[]
            False 失败
        '''
        print 'load_weiqun_pages2download:读取微群%s的下载列表'%self.weiqunID
        #path, url, status, type='weiqunpage',userid=微群id
        sql = '''SELECT path,url,status,type,userid,page FROM download WHERE userid == '%s' and type=='%s' '''%(str(self.weiqunID),'weiqunpage')
        try:
            self.cur_user.execute(sql)
            self.dbcommit()
        except Exception,E:
            print 'load_download_db_state数据库操作错误sql:%s'%sql
            print E
            return False

        res = self.cur_user.fetchall()
        
        if len(res)<1:#查询不到东西 返回[startpage ~ endpage]
            allpages = [i for i in range(self.startpage, self.endpage)]
            self.weiqun_pages2download = allpages
            return self.weiqun_pages2download
            
        else:#有查询结果(有下载过) 
            self.weiqun_pages2download = [i for i in range(self.startpage, self.endpage)]
            #将已下载过的pages从上表剔除
            for row in res:
                path,url,status,type,weiqunid,page = row
                #如果 没有下载过page 且 page不在weiqun_pages2download中,加入
                if status==self.STATUS_DOWNLOADED and \
                    page in self.weiqun_pages2download:
                    if page < self.endpage:#db记录未下载页数要小于传参的endpage页数
                        self.weiqun_pages2download.remove(page)

            
        
            print 'load_weiqun_pages2download:共%d个未下载'%len(self.weiqun_pages2download) 
            
            return self.weiqun_pages2download
 
    def update_download_db_state(self,url,path,type,status,page=None,userid=None,now=None):
        if now is None:
            now = datetime.datetime.now()
        try:
            self.cur_user.execute('''REPLACE INTO download(userid,type,page,status,url,path) VALUES ('%s','%s',%d,%d,'%s','%s');'''%(str(userid),str(type),int(page),int(status),str(url),str(path)))
            self.dbcommit()
        except Exception,E:
            print 'update_download_db_state:无法replace项'
            print E
            return False
        return True
    
    def load_download_db_state(self,url,path):
        '''
        任务:给定PK:url,path,查询self.userdbname的table:download
        返回:(userid,type,page,status,url,path,randurl,datetime) (最后一项)符合的项,
            None 若无查询结果
        '''
        
        sql = '''SELECT userid,type,page,status,url,path,randurl FROM download WHERE url == '%s' and path== '%s' '''%(str(url),str(path))
        try:
            self.cur_user.execute(sql)
            self.dbcommit()
        except Exception,E:
            print 'load_download_db_state数据库操作错误sql:%s'%sql
            print E
            return None

        res = self.cur_user.fetchall()
        if len(res)<1:#查询不到东西
            return None
        
        if len(res)>1:
            print 'load_download_db_state得到多个sql查询结果,返回最后一个结果'
        for row in res:
            #print type(row)#tuple
            userid,type,page,status,url,path,randurl = row
        
        return userid,type,page,status,url,path,randurl,None
        
    def update_download_list(self,endpage=None,weiqunid='',showdetail = False):
        '''
        任务:将给定微群id的 已/未下载的微群页记录到下载列表self.userdbname -> download table中
        返回:pages_undownload[] 未下载的微群页数列表
        '''
        pages_undownload = []
        #若参数没指定微群id则用crawler自己的微群id   endpage
        if weiqunid == '':    
            weiqunid = str(self.weiqunID)
        if endpage == None:
            endpage = self.endpage
    
        #开始扫描
        for i in range(1,endpage+1):
            weiqunUrl = WEIQUN_BASE + str(weiqunid)
            pageurl = weiqunUrl + '?page=' + str(i)
            path = self.savedir + '/' + str(weiqunid) +  '?page=' + str(i) + '.html'
            
            #判断是否下载过
            try:
                f = open(path,'r')
                localhtml=''
                lines = f.readlines()
                for line in lines:
                    localhtml+=line
                #如果下载过(且不是陷阱页)就不下载了 返回True
                #return True
                if not self.is_weiqun_page_trap(localhtml,showdetail=False):
                    if showdetail:
                        print '\t下载过且非陷阱,更新download table状态:已下载:%s,长度%d'%(path,len(localhtml))
                    # replace download table状态:已下载
                    # 格式path, url, status=1, type='weiqunpage',userid=微群id,page=i
                    succ = self.update_download_db_state(pageurl,path,type='weiqunpage',status=self.STATUS_DOWNLOADED,page=i,userid=weiqunid)
                    if not succ:
                        print 'update_download_list:更新数据库失败'
                else:
                    #if showdetail:
                    print '\t下了陷阱,更新download table状态:下载失败:%s,长度%d'%(path,len(localhtml))
                    # replace download table状态:陷阱
                    # 格式path, url, status=2, type='weiqunpage',userid=微群id,page=i
                    pages_undownload.append(i)
                    succ = self.update_download_db_state(pageurl,path,type='weiqunpage',status=self.STATUS_FAILED,page=i,userid=weiqunid)
                    if not succ:
                        print 'update_download_list:更新数据库失败'
            except Exception as e:
                #if showdetail:
                print '\t没下载过,更新download table状态:待下载:%s'%(path)
                #没有这个文件,改download table状态:待下载
                # 格式path, url, status=0, type='weiqunpage',userid=微群id,page=i
                pages_undownload.append(i)
                succ = self.update_download_db_state(pageurl,path,type='weiqunpage',status=self.STATUS_UNDOWNLOAD,page=i,userid=weiqunid)
                if not succ:
                        print 'update_download_list:更新数据库失败'
                        
        return pages_undownload
        
    def weiqun_crawl_page(self,i):
        '''
        爬虫方法，爬取微群=weiqunID的i页的页面，保存到路径self.savedir内。(如果下载过且非陷阱则跳过)
        保存格式：self.savedir/weiqunID?page=i，i是页码
            修改:下载列表状态:成功下载
        返回:True
            False
        '''
        weiqunUrl = WEIQUN_BASE + str(self.weiqunID)
        pageurl = weiqunUrl + '?page=' + str(i)
        #path = self.savedir/weiqunID?page=2.html,same as http://q.weiqun.cn/group/weiqunID?page=2
        path = self.savedir + '/' + str(self.weiqunID) +  '?page=' + str(i) + '.html'
        
        '''#用update_download_list 代替判断
        #判断是否下载过
        try:
            f = open(path,'r')
            localhtml=''
            lines = f.readlines()
            for line in lines:
                localhtml+=line
            #如果下载过(且不是陷阱页)就不下载了 返回True
            #return True
            if not self.is_weiqun_page_trap(localhtml):
                print '\t下载过且非陷阱,跳过:%s,长度%d'%(path,len(localhtml))
                return True
        except Exception as e:
            pass
        '''
        
        #下载url的html,把绝对地址转换成相对地址
        pagehtml = urlprocessor(pageurl,self.headers_weiqun,absUrl=True)
        #判断是否是trap
        if pagehtml:
            if self.is_weiqun_page_trap(pagehtml) :
                storehtml(pagehtml,path,pageurl)
                print "下载微群页面可能出错,错误样本:%s"%path
                return False
        else:
            #下载页面错误
            return False
        #转换成系统编码
        #pagehtml = fromUTF8toSysCoding(pagehtml)
        storehtml(pagehtml,path,pageurl)
        
        #修改db的下载列表状态:成功下载
        succ = self.update_download_db_state(pageurl,path,type='weiqunpage',status=self.STATUS_DOWNLOADED,page=i,userid=self.weiqunID)
        if not succ:
            print 'update_download_list:更新数据库失败'
        return True

    def is_weiqun_page_trap(self,html,showdetail=True):
        #是否 定向到 失败页
        if html:
            if PAGE_REQUEST_ERROR in html :
                if showdetail:
                    print 'is_weiqun_page_trap陷阱:%s'%PAGE_REQUEST_ERROR
                return True
            if NOBODY_POST_THIS_PAGE in html:
                if showdetail:
                    print 'is_weiqun_page_trap陷阱:%s'%NOBODY_POST_THIS_PAGE
                return True
            if PAGE_REDIRECT in html:
                if showdetail:
                    print 'is_weiqun_page_trap陷阱:%s'%PAGE_REDIRECT
                return True
        if html is None:
            if showdetail:
                print 'is_weiqun_page_trap陷阱: html is None'
            return True
        if len(html)< 4000:
            if showdetail:
                print 'is_weiqun_page_trap陷阱:网页长度过小'
            return True
        #是否与上次访问重复
        if self.last_crawl_html == str(html):
            if showdetail:
                print "is_spider_trap遇到重复网页:%s"%str(html)
            self.last_crawl_html = ''
            return True
        else:
            #缓存上次下载的页面,以备检查是否下载相同页面(反爬虫页)
            self.last_crawl_html = str(html)
        return False
    
    def rtreply_crawl(self,startpage,endpage,showdetail=False):
        '''
        待改善:速度慢,可并行加快下载,串行io提高效率
        前提:运行了 weiqun_crawl_page(),start_analyze_weibos(),end_analyze_weibos() 或数据库中表weibos有原创weibo(isoriginal=1)信息
        任务:从数据库中读取startpage~endpage页每条微博的评论`转发url,下载到:
        该weibo[i].html目录下的 ./weibo[i]/reply,./weibo[i]/rt 目录中
        每条转发\评论命名为rt[j].html,reply[j].html
        '''
        print "开始从数据库中读取每条微博的评论`转发url信息,下载到本地磁盘"
        header = self.headers_weiqun
        self.cur_weibo.execute("SELECT weiboid,path,replyurl,rturl,reply,rt FROM weibos WHERE isoriginal = 1")
        count = 0
        rtcount=0
        replycount=0
        for row in self.cur_weibo.fetchall():
            count+=1
            weiboid,path,replyurl,rturl,reply,rt = row
            #------------handle reply-------------------------------------
            #选取原创微博(isoriginal=1)的 本地存储地址path,评论replyurl
            if reply!=0:
                replyhtml = urlprocessor(replyurl,header)
                if ("请求页不存在 出错了" not in replyhtml):
                    replycount+=1
                    if showdetail: print "处理微博reply,第"+str(replycount)+'条reply:'+path+"的replyurl:"+replyurl
                    replypath = path.rstrip('.html')+'/'+'reply.html'
                    if showdetail: print "\t保存微博reply,第"+str(replycount)+'条reply到路径:'+replypath
                    storehtml(replyhtml,replypath,replyurl,showdetail)
                else:
                    print "下载reply页出错:请求页不存在 出错了,路径:"+path
                    pass
        
            #------------handle rt 基本同上-----------------------------------
            #选取原创微博(isoriginal=1)的 本地存储地址path,转发rturl
            if rt!=0:
                rthtml = urlprocessor(rturl,header)
                if ( PAGE_REQUEST_ERROR not in rthtml):
                    rtcount+=1
                    if showdetail: print "处理微博rt,第"+str(rtcount)+'条rt:'+path+"的rturl:"+rturl
                    rtpath = path.rstrip('.html')+'/'+'rt.html'
                    if showdetail: print "\t保存微博rt,第"+str(rtcount)+'条rt到路径:'+rtpath
                    storehtml(rthtml,rtpath,rturl,showdetail)
                else:
                    print "下载rt页出错:请求页不存在 出错了,路径:"+path
                    pass
                
        print "完成"+str(count)+("条微博的reply(%d) rt(%d)的下载,从:"%(replycount,rtcount))+ str(self.weibodbname)
        
    def start_rtreply_analyze(self):
        '''
        开始对硬盘的所有rt,reply网页进行分析,
        '''
        '''
        前提：当rtreply_crawl()下载好微群的每个reply(rt).html存至磁盘
        任务：1.从磁盘遍历savedir下所有路径为weiqunid?page=[i]/weibo[j]/reply(rt).html，交给self.rtreply_analyze(路径名)：
        返回:分析失败的rt/reply.html相对路径表failed_reply_paths[],failed_rt_paths[]，待重新爬取
        '''
        print "开始分析微博rt,reply：读取本地目录%s下的所有rt,reply"%(self.savedir)
        #self.replyinfos=[]#储存replyinfo{weiboid,...}(同数据库中weibos的item)
        #self.rtinfos=[]#同上
        #self.failed_reply_paths=[]#储存分析失败的reply.html路径，需要重新爬取
        #self.failed_rt_paths=[]#同上
        countrt=0#记录抽取微博rt数量
        countrtfail=0#rt抽取失败的数量
        countreplyfail=0#reply抽取失败的数量
        countreply=0#记录抽取微博reply数量
        #dir是文件名或目录，path是目录
        for pagedir in os.listdir(self.savedir):
            pagepath = self.savedir +'/' + pagedir
            if os.path.isdir(pagepath):
                for weibodir in os.listdir(pagepath):
                    #print pagepath #:./NLP/225241?page=9
                    #print weibodir #:weibo9.html weibo1 ...
                    weibopath = pagepath + '/' + weibodir
                    if os.path.isdir(weibopath):
                        rtpath = weibopath +'/rt.html'
                        replypath = weibopath+'/reply.html'
                        
                        #分析reply页的html
                        if os.path.isfile(rtpath):
                            print '分析rt：'+ replypath 
                            try:
                                f=open(rtpath,'r')
                                html=f.read()
                            except Exception,E:
                                print 'Weiqun_crawler.start_rtreply_analyze()打开本地缓存页面失败：'+str(rtpath)
                                f.close()
                                continue#不分析该页
                            finally:
                                f.close()
                            #分析rt.html
                            rtinfos = self.rt_analyze(html,rtpath)
                            #如果分析失败，记录到失败表中
                            if rtinfos is None:
                                countrtfail+=1
                                self.failed_rt_paths.append(replypath)
                            #成功加入表
                            else:
                                for rtinfo in rtinfos:
                                    countrt+=1
                                    self.rtinfos.append(rtinfo)
                        
                        #分析reply页的html
                        if os.path.isfile(replypath):
                            #print '分析reply：'+ replypath 
                            try:
                                f=open(replypath,'r')
                                html=f.read()
                            except Exception,E:
                                print 'Weiqun_crawler.start_rtreply_analyze()打开本地缓存页面失败：'+str(replypath)
                                f.close()
                                continue#不分析该页
                            finally:
                                f.close()
                            #分析reply.html
                            replyinfos = self.reply_analyze(html,replypath)
                            #如果改页分析失败，记录到失败表中
                            if replyinfos is None:
                                countreplyfail+=1
                                self.failed_reply_paths.append(replypath)
                            #成功加入表
                            else:
                                for replyinfo in replyinfos:
                                    countreply+=1
                                    self.replyinfos.append(replyinfo)
                        
        print "完成%d条reply，%d条rt的分析，失败reply:%d,rt:%d条，从本地目录：%s"%(countreply,countrt,countreplyfail,countrtfail,self.savedir)
        #返回:分析失败的rt/reply.html相对路径表failed_reply_paths[],failed_rt_paths[]，待重新爬取
        return self.failed_reply_paths,self.failed_rt_paths
    
    def end_rtreply_analyze_to_db(self):
        '''
        前提:start_rtreply_analyze()或rtreply_analyze()分析出评论转发内容存入replyinfos[] rtinfos[]
        任务:把replyinfos[] rtinfos[]的项存入数据库self.weibodbname
        '''
        countreply = 0
        countrt =0
        
        for rtinfo in self.rtinfos:
            countrt+=1
            pass
        
        for replyinfo in self.replyinfos:
            countreply+=1
            value=(replyinfo['weiboid'].replace(":",""),\
                #replyinfo['raw'].replace(":","").replace('"','').replace("'",""),\
                '',
                replyinfo['location'].replace(":",""),\
                replyinfo['content'].replace(":","").replace('"','').replace("'",""),\
                #replyinfo['contentraw'].replace(":","").replace('"','').replace("'",""),\
                '',
                replyinfo['username'].replace(":",""),\
                replyinfo['datetime'].replace(":",""),\
                replyinfo['isreplyto'].replace(":",""),\
                replyinfo['replyurl'].replace(":",""),\
                replyinfo['isrtto'].replace(":",""),\
                replyinfo['rturl'].replace(":",""),\
                replyinfo['atwho'].replace(":",""),\
                replyinfo['reply'],\
                replyinfo['rt'],\
                replyinfo['isoriginal'],\
            )
            try:
                #每条原创、评论、转发都看做一个weibo项，用weiboid区分
                #print value
                self.cur_weibo.execute("""INSERT INTO weibos(weiboid,raw,pagelocation,content,contentraw,username,datetime,isreplyto,replyurl,isrtto,rturl,atwho,reply,rt,isoriginal) VALUES('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s',%d,%d,%d);""" %value)                           
                
            except sqlite.Error,E:
                print 'DB:weibos表中插入weiboinfo项(reply)出现异常：INSERT VALUES=' + str(value)
                print E
            finally:
                self.dbcommit()
            
        print "把%d/%d条reply/rt存入数据库：%s"%(countreply,countrt,self.weibodbname)
    
    def reply_analyze(self,html,filename=None):
        '''
        任务：分析reply的html，将每条reply封装成replyinfo{},放入replyinfos[]
        返回：replyinfos[] :replyinfo{}的列表
        '''
        replyinfos=[]
        soup = BeautifulSoup(html)
        title = soup.title.string
        if NO_REPLY in html or  '评论列表' not in title:
            print '分析失败(无效reply页，可能需要重新爬取)：reply_analyze(html,%s)'%filename
            return None
        else:#有reply
            allc = soup.find_all("div", { "class" : "c" })
            #wap
            subject = allc[1]#被评论微博
            replies = allc[2:]#几个评论
            isreplyto = subject['id']#reply to的微博id,格式M_vr02n0ha52
            #print isreplyto
            if isreplyto:
                for reply in replies:
                    weiboid = None
                    userid = ''
                    content =''
                    contentraw=''
                    username = ''
                    userpage = ''
                    datetime = ''
                    replyurl =''
                    isrtto = ''
                    rturl = ''
                    rt=0
                    replynum=0
                    isoriginal = 3 #reply=3
                    atwho = ''
                    try:
                        weiboid = reply['id']
                        #print reply['id']#评论id格作为weiboid,格式C_1120421220327297
                    except KeyError,E:
                        weiboid = None
                        pass
                    if weiboid:
                        contentraw = str(reply)
                        content = str(reply.find('span',{'class':'ctt'}).get_text())
                        datetime = str(reply.find('span',{'class':'ct'}).get_text())
                        replyurl = str(reply.find('span',{'class':'cc'}).get('href'))
                        username = str(reply.a.get_text())
                        #提取"回复@谁:"的谁
                        r = re.compile(r'回复@(.*?):').search(content)
                        if r:
                            atwho = r.group(1)
                            #print atwho
                        replyinfo={}
                        if filename:
                            replyinfo.update({'location':filename})
                        else:
                            replyinfo.update({'location':''})
                            
                        
                        replyinfo.update({'weiboid':weiboid})
                        replyinfo.update({'raw':html})
                        replyinfo.update({'content':content})
                        replyinfo.update({'contentraw':contentraw})
                        replyinfo.update({'username':username})
                        replyinfo.update({'datetime':datetime})
                        replyinfo.update({'isreplyto':isreplyto})
                        replyinfo.update({'isrtto':isrtto})
                        replyinfo.update({'rt':rt})
                        replyinfo.update({'reply':replynum})
                        replyinfo.update({'replyurl':replyurl})
                        replyinfo.update({'rturl':rturl})
                        replyinfo.update({'isoriginal':isoriginal})
                        replyinfo.update({'atwho':atwho})
                        replyinfos.append(replyinfo)
                
                return replyinfos
        
        pass
    
    def rt_analyze(self,html):
        rtinfo={}
        soup = BeautifulSoup(html)
        
        return rtinfo
        pass

    def test_login(self,url):
        '''
        带header cookie访问weibo.cn，测试是否成功登陆首页
        '''
        header = self.headers_login
        #打开url处理html
        html = urlprocessor(url,header,absUrl=True)
        
        #转换成系统编码
        #html = fromUTF8toSysCoding(html)
    
        #获取用户信息打印
        print '测试登陆，请检查用户是否正确：'
        soup = BeautifulSoup(html)
        if soup.find("div", { "class" : "ut" }):
            print soup.find("div", { "class" : "ut" }).get_text()
        #re查找html的用户信息
        #pat_title = re.compile('<div class="ut">(.+?)</div>')
        #r = pat_title.search(html)
        #if r:
        #    print r.group(1)    
    
        #store html to disk
        #path = self.savedir + '/waplogin.html'
        #storehtml(html,path,url)
        #打开./waplogin.html看是否有用户名存在

    def dbcommit(self):
        '''
        提交db操作
        '''
        self.con_weibo.commit()
        self.con_user.commit()

    def dbtest(self):
        #value=('weiboid','1','12341a','4','5','6','7','8','9','10',11,'12','13',14,'15',16,'17')
        #self.cur_weibo.execute("INSERT INTO weibos(weiboid,raw,pagelocation,contentraw,content,userid,userpage,username,datetime,isreplyto,reply,replyurl,isrtto,rt,rturl,isoriginal,atwho) VALUES('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%d','%s','%s','%d','%s','%d','%s');" %value)    
        self.dbcommit()
        pass
    
    def createuserstable(self):
        '''
        初始化 用户信息、用户关系表
        '''
        #建表relation
        try:
            self.cur_user.execute('CREATE TABLE relation(userid TEXT,followerid TEXT,PRIMARY KEY(userid,followerid))')
            self.dbcommit()
        except sqlite.OperationalError,E:
            #print 'DB:%s建表relation出现异常：'%self.userdbname
            #print E
            pass
        #建表profile
        try:
            self.cur_user.execute('CREATE TABLE profile(userid TEXT PRIMARY KEY,username TEXT,followers INTERGER,followings INTERGER,weibos INTERGER)')
            self.dbcommit()
        except sqlite.OperationalError,E:
            #print 'DB:%s建表profile出现异常：'%self.userdbname
            #print E
            pass
        #建表download,保存网页下载进度信息
        try:
            self.cur_user.execute('CREATE TABLE download(url TEXT,path TEXT,type TEXT ,status INTERGER,page INTERGER ,userid TEXT ,randurl TEXT ,datetime TIMESTAMP,PRIMARY KEY(url,path))')
            self.dbcommit()
        except sqlite.OperationalError,E:
            #print 'DB:%s建表download出现异常：'%self.userdbname
            #print E
            pass
            
    def createweibostable(self):
        '''
        初始化微博信息db表
        '''
        try:
            #每条原创、评论、转发都看做一个weibo项，用weiboid区分
            '''
            self.cur_weibo.execute('CREATE TABLE weibos\
             (weiboid TEXT PRIMARY KEY,#主键，每个微博分配一个独立的id=genweiboid() 暂用生成先后顺序分配\
             raw TEXT,                      #此条微博的全部源代码\
             path TEXT,                    #此条微博储存到本地磁盘的位置
             pagelocation TEXT,                       #此条微博所在的网页地址（是爬下来存放在本地磁盘的路径）\
             contentraw TEXT,                     #此条微博内容的源代码\
             content,                             #正文\
             userid TEXT,                         #发微博用户id\
             userpage TEXT,                       #发微博用户主页\
             username TEXT,                       #发微博用户名\
             datetime TEXT,                       #发微博日期时间\
             isreplyto TEXT,                      #是否是某条微博的评论\
             reply INTEGER,                      #微博的评论数\
             replyurl TEXT,                       #微博的评论超链接url\
             isrtto TEXT,                         #是否是某条微博的转发\
             rt INTEGER,                         #微博的转发数\
             rturl TEXT,                          #微博的转发超链接url\
             isoriginal INTEGER,                 #是原创微博吗 1:是 0:否\
             atwho TEXT,                          #这条微博at了谁，如:id1,id2,id3\
             )')
             '''
            self.cur_weibo.execute('CREATE TABLE weibos(weiboid TEXT PRIMARY KEY,path TEXT,pagelocation TEXT,content TEXT,userid TEXT,userpage TEXT,username TEXT,datetime TEXT,isreplyto TEXT,reply INTEGER,replyurl TEXT,isrtto TEXT,rt INTEGER,rturl TEXT,isoriginal INTEGER,atwho TEXT,raw TEXT,contentraw TEXT)')
            self.dbcommit()
        except sqlite.OperationalError,E:
            print 'DB建表weibos出现异常：'
            #print E
            pass    #已经存在table    
        
    def start_crawl_profiles_from_uid_in_weibodb(self,showdetail=False):
        '''
        前提：db:self.weibodbname有uid
        任务：读取db:self.weibodbname的uid，下载uid的type:profile，fans，follow页到本地磁盘/uid/[type]/[i].html
        db:写self.userdbname的download表
        返回:True 完成退出(可能有几个没爬)
        '''
        header = self.headers_login
        print "start_crawl_profiles_from_uid_in_weibodb:开始从数据库读取uid,从网络下载uid主页到本地磁盘self.usersdir/uid/profile.html"
        try:
            self.cur_weibo.execute("SELECT DISTINCT userid FROM weibos")
            self.dbcommit()
        except Exception,E:
            print 'start_crawl_profiles_from_uid_in_weibodb：从db读取uid错误'
            print E
            return None
            
        count_done = 0
        count_invalid_uid = 0
        count_trap = 0
        count_skip = 0
        list = self.cur_weibo.fetchall()
        print '\t共有用户：%d个'%len(list)
        for row in list:
            #print type(row)#tuple
            uid, = row
            #print type(uid)#unicode
            
            if uid==None or uid==0 or uid=='':
                count_invalid_uid+=1
                if showdetail:
                    print "start_crawl_profiles_from_uid_in_weibodb:无效uid:%s"%uid
                continue
            else:
                type = 'profile'
                page = 0
                #下载uid的profile页,存到磁盘
                html = self.crawl_user_page(uid, page, type, header,showdetail)
                
            #处理下载好的html
            if html is None:
            #下载profile失败，则加入失败列表
                count_trap+=1
                if showdetail:
                    print 'start_crawl_profiles_from_uid_in_weibodb:下载用户profile失败,记录在download表上uid：%s' % uid
            elif html == '':
                count_skip+=1
            else:
                count_done+=1
                   
        print '\tstart_crawl_profiles_from_uid_in_db:成功下载/跳过/无效uid/爬虫陷阱的profile页：%d/%d/%d/%d个'%(count_done,count_skip,count_invalid_uid,count_trap)    
        return True

    def start_crawl_fans_follow_from_profiles_in_db(self,delayfunc,stop_when_trap=True,showdetail=False):
        '''
        前提：db:self.userdbname有uid,followers,followings（fans,fos数量）
        任务：读取db:self.userdbname的uid，fans，fos，下载粉丝、关注用户页:[i].html到本地self.usersdir/uid/fans /follow
        输出：文件如上述
        db:写self.userdbname的download表
        返回:True 完全爬完
            MEET_TRAP 遇见陷阱,暂停退出
        '''
        header = self.headers_login
        print "start_crawl_fans_follow_from_profiles_in_db():开始从数据库%s读取uid,关注数,粉丝数，下载每个uid的fans follow页:[i].html到本地磁盘self.usersdir/uid/fans /follow"%self.userdbname
        try:
            self.cur_user.execute("SELECT  userid,weibos,followers,followings FROM profile")
            self.dbcommit()
        except Exception,E:
            print 'start_crawl_fans_follow_from_profiles_in_db：读取uid错误'
            print E
        countuser = 0
        countpage = 0
        countdownload = 0
        list = self.cur_user.fetchall()
        print '\t共有用户：%d个'%len(list)
        for row in list:

            countuser+=1
            #print type(row)#tuple
            uid,weibonum,fansnum,fosnum = row
            
            #延迟,以防被ban
            delayfunc(countpage)
            
            #-----------下载用户fans页---------------------------
            end = int(fansnum / WEIBO_PER_PAGE + 2) 
            type = 'fans'
            for i in range(1,end):
                countpage+=1
                #返回的html是:None则有陷阱,''则是跳过,'...'则是网页内容
                html = self.crawl_user_page(uid, i, 'fans', header, weibonum, fansnum, fosnum, showdetail)
                if html is None:
                    print 'start_crawl_fans_follow_from_profiles_in_db:爬取遇到陷阱，无法爬取uid:%s的%s第%d页'%(uid,type,i)
                    #若参数设定 遇到陷阱停止爬取
                    if stop_when_trap:
                        return MEET_TRAP
                elif html is '':
                    print 'start_crawl_fans_follow_from_profiles_in_db:本地已有,跳过爬取uid:%s的%s第%d页'%(uid,type,i)
                else:#处理 网页HTML代码
                    countdownload+=1
                    pass
                    

            #-----------下载用户follow页---------------------------
            end = int(fosnum / WEIBO_PER_PAGE + 2)
            type = 'follow'
            for i in range(1,end):
                countpage+=1
                html = self.crawl_user_page(uid, i, 'follow', header, weibonum, fansnum, fosnum, showdetail)
                if html is None:
                    print 'start_crawl_fans_follow_from_profiles_in_db:爬取遇到陷阱，无法爬取uid:%s的%s第%d页'%(uid,type,i)
                    print '已经连续爬取%d个网页'%countdownload
                    #若参数设定 遇到陷阱停止爬取
                    if stop_when_trap:
                        
                        return MEET_TRAP
                elif html is '':
                    #if showdetail:
                    print 'start_crawl_fans_follow_from_profiles_in_db:本地已有,跳过爬取uid:%s的%s第%d页'%(uid,type,i)
                else:#处理 网页HTML代码
                    countdownload+=1
                    pass
            
        print 'start_crawl_fans_follow_from_profiles_in_db:共处理用户%d个,处理网页%d个，下载网页%d个'%(countuser,countpage,countdownload)
        return True
        
    def is_spider_trap(self,uid,weibonum,fansnum,fonum,pagetype,html):
        '''
        if uid  not in html:
            #重定向到login的用户主页，但是页面隐含请求url，隐含这个uid，失效！
            print '干 为什么不出来'
            return True
        '''
        if self.last_crawl_html == str(html):
            print "is_spider_trap遇到重复网页:%s"%str(html)
        else:
            self.last_crawl_html = str(html)
        
        
        if LOGIN_USER_NAME in html:
            print "is_spider_trap重定向到登陆用户%s主页" % LOGIN_USER_NAME
            return True
        if (PAGE_REQUEST_ERROR in html):
            return True

        '''
        待改善：添加更多爬虫陷阱例外
        '''
        #不是陷阱
        return False
    
    def gen_user_page_url(self,uid,page,type,showdetail=False):
        '''
        任务:生成给定uid的profile/fans/follow的第page页的url
        输出:url或None(生成失败时)
        '''
        if type == 'follow':
            url_base = FOPAGE_PREFIX % uid + FOPAGE_SURFFIX
        elif type == 'fans':
            url_base = FANPAGE_PREFIX % uid + FANPAGE_SURFFIX
        elif type == 'profile':
            url  = USERPROFILE_PREFIX % uid
        else:#如果type不是上述，参数错误，返回None
            print 'gen_user_page_url：参数错误tpye=%s'%type
            return None
        if type!= 'profile':
            url = url_base % str(page)
        
        return url
    
    def gen_user_page_path(self,uid,page,type,showdetail=False):
        '''
        任务:生成给定uid的profile/fans/follow的第page页的保存文件路径
        输出:path或None(生成失败时)
        '''
        if type == 'follow':
            path_base = self.usersdir+'/%s/follow/' % uid
        elif type == 'fans':
            path_base = self.usersdir+'/%s/fans/' % uid
        elif type == 'profile':
            path = self.usersdir+'/%s/profile.html' % uid
        else:#如果type不是上述，参数错误，返回None
            print 'gen_user_page_path：参数错误tpye=%s'%type
            return None
        if type!= 'profile':
            path = path_base + str(page) + '.html'
        return path
    
    def crawl_user_page(self,uid,page,type,header,weibonum=None,fansnum=None,fosnum=None,showdetail=False):
        '''
        任务：爬取给定uid的关注页（第page页,type是'fans'或者'follow'或者'profile'）(查询self.userdbname,如果爬取过就跳过)
        输出：把关注页存到本地：是self.gen_user_page_path(uid, page, type) = self.usersdir/[uid]/[type]/[i].html(fans或follow) | self.usersdir/[uid]/profile.html
        返回：返回None:遇到爬虫陷阱，储存文件
             返回'':已下载好,跳过爬取,
             返回html:成功爬取，储存文件并
        '''
        url = self.gen_user_page_url(uid, page, type)
        path = self.gen_user_page_path(uid, page, type)
        if url is None or path is None:
            return None
        
        #从self.userdbname检查是否下载过
        godownload = False
        query = self.load_download_db_state(url,path)
        if query is None:
            godownload =True
        else:
            auid,atype,apage,astatus,aurl,apath,arandurl,atimestamp = query
            if astatus != 1:
                godownload = True
        
        if godownload: 
            #下载网页
            html = urlprocessor(url,header,absUrl=True)
            
            #如果是陷阱,依然保存到磁盘，留作分析
            if self.is_spider_trap(uid, weibonum, fansnum, fosnum,type,html): 
                print "crawl_user_page:可能是爬虫陷阱 下载到路径：%s ,url:%s,type:%s下载到第%d页"%(path,url,type,page)
                storehtml(html,path,url)
                #更新下载状态(失败)到数据库table download 
                self.update_download_db_state(url,path,type,self.STATUS_FAILED,page,uid)
                return None
            #成功下载，保存到磁盘
            else:
                #转换成系统编码
                #pagehtml = fromUTF8toSysCoding(pagehtml)
                storehtml(html,path,url)
                #更新下载状态(成功)到数据库table download 
                self.update_download_db_state(url,path,type,self.STATUS_DOWNLOADED,page,uid)
                if showdetail:
                    print 'crawl_user_page成功下载网页到：%s,url：%s'%(path,url)
                return html
        else:#dont download
            if showdetail:
                print 'crawl_user_page不重复下载url:%s,已有有效网页:%s'
            return ''
        
    def analyze_user_profiles(self,showdetail=False):
        '''
        前提：有self.usersdir/[uid]/profile.html
        任务：读取上述所有文件，交由analyze_username_weibos_fans_fos_num()分析（会改动self.profiles[])
        修改：self.profiles[],self.userdbname的table download
        返回：self.profiles[]
            NOne:无文件self.usersdir
        '''
        try:
            os.listdir(self.usersdir)
        except OSError,e:
            print 'analyze_user_profiles错误:无文件self.usersdir'
            print e
            return None
            
        print 'analyze_user_profiles():从硬盘self.usersdir读取%d个用户profile进行关系分析'%len(os.listdir(self.usersdir))
        count = 0
        for uid in os.listdir(self.usersdir):
            path =  self.usersdir +'/' +uid+'/profile.html'
            if os.path.isfile(path):
                with open(path) as f:
                    html = f.read()
                    #分析下载页的 微博[38] 关注[73] 粉丝[27] 数
                    nums = crawler.analyze_username_weibos_fans_fos_num(html,showdetail)
                    if nums is None:#无效profile
                        print 'analyze_user_profiles:无效profile:%s'%path
                        pass
                    else:#有效profile,获取上述项的num
                        if showdetail: print nums
                        username,weibosnum,fansnum,fosnum = nums
                        #将用户的profile {username,uid,weibonum,fansnum,fosnum},加到self.profiles[]中
                        #之后调用end_crawl_user_info_to_db()将self.profiles存入./users.db的user
                        profile = {}
                        profile.update({'username':username,'userid':uid,'weibos':int(weibosnum),'followers':int(fansnum),'followings':fosnum})
                        self.profiles.append(profile)
                        count+=1
        print 'analyze_user_profiles():分析了%d个用户profile，%d个失败'%(count, len(os.listdir(self.usersdir))-count)
        return self.profiles

    def end_store_user_profiles_to_db(self):
        count=0
        for profile in self.profiles:
            userid = profile['userid']
            username = profile['username']
            weibos = profile['weibos']
            followers = profile['followers']
            followings = profile['followings'] 
            try:
                self.cur_user.execute('''INSERT INTO profile(userid,username,weibos,followers,followings) VALUES ('%s','%s',%d,%d,%d); ''' % (userid,username,weibos,followers,followings))
                self.dbcommit()
                count+=1
            except Exception,E:
                print 'end_store_user_profiles_to_db():./user.db往profile表中插入项出现错误：'
                print E
        print 'end_store_user_profiles_to_db():完成%d条profile表项的更新，在db：./user.db'%count
               
    def analyze_username_weibos_fans_fos_num(self,html,showdetail=False):
        '''
        输入:wap html源代码of微博用户profile页:“usrename的微博[0] 关注[21] 粉丝[5] 分组[1] @她的”
        输出：(username,weibonum,fansnum,fosnum) 或 None
        '''
        soup = BeautifulSoup(html)
        title = str(soup.title.string)
        #wap用户名在标题
        username = title.rstrip(u'的微博')
        #wap如果标题有 “微博广场”字样而非username，下载出错，需要重新下载
        if  WEIBO_SQUARE in title:
            return None
        else:
            #wap分析 网页蓝微博[0] 关注[21] 粉丝[5] 分组[1] @她的
            allres = soup.find_all("div", { "class" : "tip2"})
            for res in allres:
                #res类型<class 'bs4.element.Tag'>
                text =  res.get_text()
                
                if (u'微博['in text) and (u'关注[' in text) and (u'粉丝[' in text):
                    if showdetail:  print text#微博[754] 关注[193] 粉丝[261] 分组[1] @她的
                    weibosnum = 0
                    fansnum=0
                    fosnum=0
                    #获取微博数
                    res = re.compile(u'微博\[(.+?)\]').search(text)
                    if res is not None:
                        weibosnum = int(res.group(1))
                    #获取关注数
                    res = re.compile(u'关注\[(.+?)\]').search(text)
                    if res is not None:
                        fosnum = int(res.group(1))
                    #获取粉丝数
                    res = re.compile(u'粉丝\[(.+?)\]').search(text)
                    if res is not None:
                        fansnum = int(res.group(1))
                    #分析成功，返回数目
                    if showdetail:  print username,weibosnum,fansnum,fosnum
                    return username,weibosnum,fansnum,fosnum
                else:#分析错误，返回
                    return None
                
    def test_analyze_weibos_fans_fos_num(self):
        '''
        前提：self.usersdir/uid/profile.html 有文件(执行过self.start_crawl_profiles_from_uid_in_weibodb())
        任务：测试crawler.analyze_username_weibos_fans_fos_num()
        输出：很多行：    微博[1590] 关注[124] 粉丝[153] 分组[1] @她的
                       我们都关注文章同學
        '''
        print '测试test_analyze_weibos_fans_fos_num()，将看到类似\n“微博[233] 关注[257] 粉丝[322] 分组[1] @他的\n智能侠-AI 233 322 257”'
        for uid in os.listdir(self.usersdir):
            path =  self.usersdir+'/'+uid+'/profile.html'
            if os.path.isfile(path):
                with open(path) as f:
                    html = f.read()
                    nums = crawler.analyze_username_weibos_fans_fos_num(html,showdetail=True)
                    if nums is None:
                        print "非有效profile:%s"%path
                    else:
                        print nums
        
    def end_analyze_weibos_to_db(self):
        '''
        输入：self.allweiboinfos[]
        前提：start_analyze_weibos_from_disk()执行完毕，将析取的微博信息self.allweiboinfos[]储存好
        任务：把all weiboinfo{}中内容存至数据库
        '''
        print "将分析好的微博信息self.allweiboinfos[]存入数据库文件:"+self.weibodbname + '...'
        for weiboinfo in self.allweiboinfos:
            #微博在本地磁盘的路径
            path = str(weiboinfo['path']).replace("'",'').replace('"','')
            #微博所在网页page的路径
            pagelocation = str(weiboinfo['pagelocation']).replace("'",'').replace('"','')#去除字符串中的'与"(sqlite 类型TEXT不允许)
            #微博(WAP版)的id
            weiboid = str(weiboinfo['weiboid']).replace("'",'').replace('"','')
            #用户信息
            username = str(weiboinfo['username']).replace("'",'').replace('"','')
            userid = str(weiboinfo['userid']).replace("'",'').replace('"','')
            userpage = str(weiboinfo['userpage']).replace("'",'').replace('"','')
            content = str(weiboinfo['content']).replace("'",'').replace('"','')
            contentraw = str(weiboinfo['contentraw']).replace("'",'').replace('"','')
            replyurl = str(weiboinfo['replyurl']).replace("'",'').replace('"','')
            rturl = str(weiboinfo['rturl']).replace("'",'').replace('"','')
            datetime = str(weiboinfo['datetime']).replace("'",'').replace('"','')
            atwho = str(weiboinfo['atwho']).replace("'",'').replace('"','')
            isreplyto = str(weiboinfo['isreplyto']).replace("'",'').replace('"','')
            raw = str(weiboinfo['raw']).replace("'",'').replace('"','')
            isrtto = str(weiboinfo['isrtto']).replace("'",'').replace('"','')
            reply = int(weiboinfo['reply'])
            rt = int(weiboinfo['rt'])
            isoriginal = int(weiboinfo['isoriginal'])
            
            value =  (weiboid,path,pagelocation,content,userid,userpage,username,datetime,isreplyto,replyurl,isrtto,rturl,atwho,raw,contentraw,reply,rt,isoriginal)
            #往weibos表中插入weiboinfo项
            try:
                #每条原创、评论、转发都看做一个weibo项，用weiboid区分
                self.cur_weibo.execute("""INSERT INTO weibos(weiboid,path,pagelocation,content,userid,userpage,username,datetime,isreplyto,replyurl,isrtto,rturl,atwho,raw,contentraw,reply,rt,isoriginal) VALUES('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s',%d,%d,%d);""" %value)                           
            except sqlite.Error,E:
                print 'DB:weibos表中插入weiboinfo项出现异常：INSERT VALUES=' + str(value)
                print E
            finally:
                self.dbcommit()
        print "完成"
                
    def start_analyze_weibos_from_disk(self,showdetail=True):
        '''
        前提：当weiqun_crawl_page()下载好微群的每个page.html存至磁盘
        任务：1.从磁盘遍历savedir下所有page.html，交给analyze_weiqun_weibo()：
                a.抽出页内每条weibo[j]的html存到self.savedir/weiqunID?pagename_html=[i]/weibo[j].html
                b.分析每条微博，析取信息到weiboinfo={}，dic key同db的weibos表，将每条微博的weiboinfo加到总表allweiboinfos
        返回：allweiboinfos 微博抽取信息的总表。
        '''
        print "开始分析微博：读取本地目录%s下的所有网页"%(self.savedir)
        header = self.headers_weiqun
        self.allweiboinfos = []#微博信息总表，元素是weiboinfo={}
        count=0#记录抽取微博数量
        j=0 #分析第j页上的微博
        for pagename_html in os.listdir(self.savedir):
                #分割文件名与后缀ext，如:pagename_html = '225241?page=1',ext='.html'
                pagename,ext =  os.path.splitext(pagename_html)
                if ext == '.html' and 'page' in pagename:
                    #打开page.html
                    try:
                        f=open(self.savedir+'/'+pagename_html,'r')
                        html=f.read()
                    except Exception,E:
                        print 'Weiqun_crawler.start_analyze_weibos_from_disk()打开本地缓存页面失败：'+str(pagename_html)
                        continue#不分析该页
                    finally:
                        f.close()
                    j+=1
                    
                    #分析第j页的所有微博,存到pageweiboinfos=[weiboinfo1,weiboinfo2,...]，其中weiboinfo={}，内容同db table weibos' item
                    pageweiboinfos = []
                    pageweiboinfos = self.analyze_weiqun_page(html,pagename_html,showdetail)
                    for weiboinfo in pageweiboinfos:
                        #每个微博都加入总表
                        self.allweiboinfos.append(weiboinfo)
                    
                    #把第j页的所有微博源代码单独存到pagename目录下
                    i=0
                    for weiboinfo in pageweiboinfos:
                        count+=1
                        i+=1
                        #建立pagename文件，存放分析微博的源代码weibo[i].html
                        path = self.savedir+'/'+pagename+'/'+'weibo'+str(i)+'.html'
                        weiboinfo.update({'path':path})
                        storehtml(weiboinfo['raw'],weiboinfo['path'],pagename,showdetail=False)
                        if showdetail:  print ("\t分析第%d页第%d条微博并储存在:"%(j,i))+path
                    
                    print '\t分析weiqun页上的微博完毕:%s'%pagename_html
        print "完成%d条微博抽取，从本地目录：%s"%(count,self.savedir)
        return self.allweiboinfos
        
    def analyze_weiqun_page(self,html,pagename,showdetail):
        '''
        分析微群页面html，返回weibos=[],由getweibos()调用
        weibo是抽取出来的html：按一般page中微博格式：（WAP）
        <div class="c" id="M_103r08nr6th">...</div> ,其中id疑似unique?（WAP和Web不一样）
        ???假设id是uid，存为weiboid???
        '''
        
        #完成下面的bs分析:取出该页每条微博的tag，存为weibohtml
        #调用analyze_weibo_from_page提取出多条微博信息weiboinfo{}，存在weiboinfos[]并返回
        weiboinfos=[]
        soup = BeautifulSoup(html)
        allres = soup.find_all("div", { "class" : "c"})
        for res in allres:
            #res类型<class 'bs4.element.Tag'>
            if res.has_key('id'):
                weibohtml=str(res)
                weiboinfo = self.analyze_weibo_from_page(weibohtml,pagename,showdetail)
                if weiboinfo:#如果是一条weibo
                    weiboinfos.append(weiboinfo)
        return weiboinfos

    def analyze_weibo_from_page(self,html,pagelocation,showdetail):
        '''
        分析每条微博的html，抽取出如下元素
        '''
        weiboinfo = {}
        #------------------------------------------------------------------------------ 
        #是否对某条微博的评论、转发，是否原创
        weiboinfo.update({'isreplyto': ''})
        weiboinfo.update({'isrtto' : ''})
        weiboinfo.update({'isoriginal' : 1})
        #------------------------------------------------------------------------------ 
        #at了谁
        atwho = self.analyze_weibo_atwho(html)
        weiboinfo.update({'atwho':atwho})
        #------------------------------------------------------------------------------ 
        #微博所在page(page存在本地磁盘路径)
        pagelocation = self.savedir + '/' + pagelocation
        weiboinfo.update({'pagelocation':pagelocation})
        #------------------------------------------------------------------------------ 
        #纯html文档
        weiboraw = html
        weiboinfo.update({'raw':weiboraw})
        #------------------------------------------------------------------------------ 
        #找出weiboid
        weiboid = self.analyze_weibo_weiboid(html)
        if weiboid: weiboinfo.update({'weiboid':weiboid})
        else:
            print '这不是微博loc:%s'%pagelocation
            return None
        #------------------------------------------------------------------------------ 
        #发帖的userid,username,userpage
        userid,username,userpage = self.analyze_uid_uname_upage_from_weibo(html)
        weiboinfo.update({'userid':userid})
        weiboinfo.update({'username':username})
        weiboinfo.update({'userpage':userpage})
        #------------------------------------------------------------------------------ 
        #微博内容 content 与 contentraw（原始html）
        content,contentraw = self.analyze_weibo_content(html)
        weiboinfo.update({'content':content})
        weiboinfo.update({'contentraw':contentraw})
        #------------------------------------------------------------------------------ 
        #分析转发rt，评论reply，转发超链rturl,评论超链replyurl
        rt,rturl,reply,replyurl = self.analyze_weibo_rtreply(html)
        weiboinfo.update({"rt":rt})
        weiboinfo.update({"rturl":rturl})
        weiboinfo.update({"reply":reply})
        weiboinfo.update({"replyurl":replyurl})
        #------------------------------------------------------------------------------
        #获取datetime 
        datetime = self.analyze_weibo_datetime(html)
        weiboinfo.update({"datetime":datetime})
        #------------------------------------------------------------------------------
        #打印这条weibo析取信息
        if showdetail:
            self.printweiboinfo(weiboinfo)
        
        #返回weiboinfo={}
        return weiboinfo 
            
    def analyze_weibo_atwho(self,html):
        '''
        这条weibo at了谁
        待完善
        '''
        soup = BeautifulSoup(html)
        #待完善
        return ''

    def analyze_weibo_weiboid(self,html):
        '''
        从html找出weiboid，返回str weiboid
        '''
        soup = BeautifulSoup(html)
        idtag = soup.find('div',{'class':'c'})
        try:
            weiboid = idtag['id']
        except KeyError,E:
            #print "这不是微博(无weiboid)"
            return None
        return str(weiboid)
    
    def analyze_uid_uname_upage_from_weibo(self,html):
        '''
        从html找出发weibo的(userid,username,userpage)
        '''
        soup = BeautifulSoup(html)
        usertag = soup.div.div.a
        username = usertag.get_text()
        userpage = usertag.get('href')
        
        if('profile' in userpage):
            userid = userpage.split('/')[-1]
        else:
            userid = userpage
            print 'analyze_uid_uname_upage_from_weibo():获取userid错误'
        return (str(userid),str(username),str(userpage))
    
    def analyze_weibo_content(self,html):
        '''
        从html找出content，以及源代码contentraw
        获取第一个span即可
        返回(content,contentraw)
        '''
        soup = BeautifulSoup(html)
        contenttag = soup.find('span')
        if contenttag:
            content = contenttag.get_text()
        else:
            content = ''
            print '获取content失败'
        #获取contentraw
        if contenttag:
            contentraw = str(contenttag)
        else:
            contentraw = ''
            
        return (str(content),contentraw)
    
    def analyze_weibo_rtreply(self,html):
        '''
        从html分析:转发rt，评论reply，转发超链rturl,评论超链replyurl
        返回(rt,rturl,reply,replyurl)
        '''
        #获取转发，评论字符 rtchars='转发[2]' replychars='评论'
        #rt reply一般在两个span中间，用re找
        replytag = ''
        rttag = ''
        replychars=''
        rtchars=''
        rt=0
        reply=0
        rturl=''
        replyurl=''
        
        regex = '''/span>(.+?)<span class="ct"'''
        res = re.compile(regex).search(html)
        if res:# rtreply='<a href= replyurl ...>评论[1]</a> <a href= rturl>转发[2]</a>'
            rtreply = str(res.group(1))
            tag = BeautifulSoup(rtreply)
            allprobablytags = tag.find_all('a')
            #下面设置rttag 与 replytag，使：
            #replytag = bs('<a href= replyurl ...>评论[1]</a>')
            #rttag = bs('<a href= rturl>转发[2]</a>')
            for tag in allprobablytags:
                if("转发" in tag.get_text()):
                    rttag = tag
                elif("评论" in tag.get_text()):
                    replytag = tag
                else:
                    pass
            
            if rttag is None:
                print "解析微博 转发 错误！"
                print rtreply
            elif replytag is None:
                print "解析微博 评论 错误！"
                print rtreply
            else:#获取 评论[i] 转发[j] 字符串
                replychars = str(replytag.contents[0]) #'转发[2]'
                rtchars = str(rttag.contents[0]) # '评论' or'评论[0]'
            
            #分析转发数rt
            if('[' and ']' in rtchars):
                res = re.compile('\[(.+?)\]').search(rtchars)
                if res is not None:
                    rt = int(res.group(1))
            else:rt=0
            #评论数reply
            if('[' and ']' in replychars):
                res = re.compile('\[(.+?)\]').search(replychars)
                if res is not None:
                    reply = int(res.group(1))
            else:reply=0
            
            #分析转发超链rturl,评论超链replyurl
            rturl=''
            replyurl=''
            if replytag.get('href'):
                replyurl = replytag.get('href')
            if rttag.get('href'):
                rturl = rttag.get('href')
                        
        return (rt,rturl,reply,replyurl)
               
    def analyze_weibo_datetime(self,html):
        '''
        分析weibo html的时间，以字符串返回
        '''
        soup = BeautifulSoup(html)
        datetime = soup.find('span',{'class':'ct'}).get_text()
        if datetime:
            dt = str(datetime)
        else:
            dt = ''
            print '获取datetime失败'
        #待改善：2012-12-13 16:02:59 或者 5分钟前 或者 01月16日 11:11 或者 刚才   
        return dt
    
    def test_rtreply_analyze(self):
        #测试rtreply_analyze()分析本地的rt reply网页
        print '测试：rt_analyze(),reply_analyze()，观察需要先删除db文件，执行后打开db文件观察是否将网页内容析取到db，是否报错'
        self.createweibostable()
        nonereply =  '/Users/mac/Dropbox/weiquncrawler/replytest/none-reply.html'
        multireply = '/Users/mac/Dropbox/weiquncrawler/replytest/reply-multi-page.html'
        with open(nonereply,'r') as f:
            html = f.read()
            self.reply_analyze(html,nonereply)
        with open(multireply,'r') as f:
            html = f.read()
            self.reply_analyze(html,multireply)
        self.end_rtreply_analyze_to_db()
        
    def printweiboinfo(self,weiboinfo):
        '''
        任务：打印weiboinfo{}中内容
        '''
        pagelocation = str(weiboinfo['pagelocation'])
        weiboid = str(weiboinfo['weiboid'])
        username = str(weiboinfo['username'])
        userid = str(weiboinfo['userid'])
        userpage = str(weiboinfo['userpage'])
        content = str(weiboinfo['content'])
        rt = int(weiboinfo['rt'])
        reply = int(weiboinfo['reply'])
        replyurl = str(weiboinfo['replyurl'])
        rturl = str(weiboinfo['rturl'])
        datetime = str(weiboinfo['datetime'])
        print "___________微博___________"
        print "微博所在页："+pagelocation        
        print "微博id："+weiboid
        print "用户名："+username+',用户id：'+userid+",用户主页："+userpage
        print "微博内容："+content
        print "评论数:%d,转发数:%d"%(reply,rt)
        print "评论url:%s\n转发url：%s"%(replyurl,rturl)  
        print '发微博时间:|'+datetime+'|' 
        pass
'''
def change_cookies():
    global COOKIE
    global COOKIE1
    global COOKIE2
    global COOKIE3
    global COOKIE4
    global COOKIE5
    
    if COOKIE == COOKIE1:
        COOKIE = COOKIE2
    elif COOKIE == COOKIE2:
        COOKIE = COOKIE3
    elif COOKIE == COOKIE3:
        COOKIE = COOKIE4
    elif COOKIE == COOKIE4:
        COOKIE = COOKIE5
    elif COOKIE == COOKIE5:
        COOKIE = COOKIE1
    else:
        COOKIE = COOKIE1
    
    print '更换COOKIE!',COOKIE
    print HEADERS_WEIQUN
'''    
def delayfunc(times):

    '''
    global TRAP_TIMES       
    print "TRAP_TIMES:",TRAP_TIMES
    
    TRAP_TIMES+=1
    if TRAP_TIMES > 5:
        #change_cookies()
        TRAP_TIMES = 0
        return int(5)
    '''    
    
    if times == 1:
        sleeptime = int(3)
    elif times == 2:
        sleeptime = int(4)
    elif times == 3:
        sleeptime = int(7)
    elif times == 4:
        sleeptime = int(120)
    elif times == 5:
        sleeptime = int(240)
    elif times == 6:
        sleeptime = int(480)
    elif times == 6:
        sleeptime = int(3600)
    else:
        sleeptime = int(3600)
        
    return sleeptime
    pass
    
def run_my_crawler(crawler,pagelist):
    try:
        for i in pagelist:
            trap_in_same_page = 0
            success = crawler.weiqun_crawl_page(i)
            while not success:
                print '第%d页遇见陷阱' % i
                trap_in_same_page+=1
                sleeptime = delayfunc(trap_in_same_page)
                
                #换COOKIES
                if sleeptime > 50:
                    crawler.change_cookie_headers()
                    trap_in_same_page = 0
                else:
                    print '\t第%d次被陷,睡眠%d秒'%(trap_in_same_page,sleeptime)
                    time.sleep(sleeptime)
                #如果成功下载,则跳出while
                if crawler.weiqun_crawl_page(i):
                    break
                #如果下载同一页 更换cookie超过一定次数,停止
                if crawler.change_cookie_times > 10:
                    print 'CHANGE COOKIE MORE THAN %d times, return False'%crawler.change_cookie_times 
                    return False
    except Exception as e:
        print e
        print "Error occured in run_my_crawler,pid:{1}\nError:{2}",os.getpid(),e
        
def get_pages_to_download(crawler,startpage,endpage):
    '''
    任务:找出crawler.userdbname的数据库表download 没有下载过的微群page号
    返回:pages[]
    '''
    pages = []
    weiqunid = str(crawler.weiqunID)
     
    return pages


    

def multi_thread_crawl_weiqun(crawler,startpage,endpage,threadnum,showdetail = True):
    print '%d线程准备下载微群%s的%d页微博'%(threadnum,str(crawler.weiqunID),crawler.endpage)
    #多线程爬取
    if threadnum>=1:
        #读取db未下载微群页到crawler.weiqun_pages2download[]
        crawler.load_weiqun_pages2download()
        #print 'thread=%d'%threadnum
        pagelist = [i for i in crawler.weiqun_pages2download]
        #如果有page需要下载
        if pagelist:
            #若无法拆分则1线程下载
            if len(pagelist)<threadnum:
                succ = multi_thread_crawl_weiqun(crawler,startpage,endpage,1,showdetail)
                return succ
            else:#可以拆分则拆分
                pagelist_list = chunks_avg(pagelist,threadnum)
                for pagelist in pagelist_list:    
                    p = Process(target=run_my_crawler, args=(crawler,pagelist) )
                    p.start()
                    time.sleep(0)
                return True
        else:
            return False
            
    #以下无用
    #开始顺序爬微群第startpage~endpage页
    elif threadnum==0:
        #读取db未下载微群页到crawler.weiqun_pages2download[]
        crawler.load_weiqun_pages2download()
        #print 'thread==1'
        for i in crawler.weiqun_pages2download:            
            trap_in_same_page = 0
            success = crawler.weiqun_crawl_page(i)
            while not success:
                print '第%d页遇见陷阱' % i
                trap_in_same_page+=1
                sleeptime = delayfunc(trap_in_same_page)
                
                #换COOKIES
                if sleeptime > 50:
                    crawler.change_cookie_headers()
                else:
                    print '\t第%d次被陷,睡眠%d秒'%(trap_in_same_page,sleeptime)
                    time.sleep(sleeptime)
                #如果成功下载,则跳出while
                if crawler.weiqun_crawl_page(i):
                    break
                #如果更换cookie超过一定次数,停止
                if crawler.change_cookie_times > 10:
                    print 'CHANGE COOKIE MORE THAN %d times, return False'%crawler.change_cookie_times 
                    return False
                
            
        return True
    else:
        return False
        
#测试按键有否按下
def kbhit():
    fd = sys.stdin.fileno()
    oldterm = termios.tcgetattr(fd)
    newattr = termios.tcgetattr(fd)
    newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
    termios.tcsetattr(fd, termios.TCSANOW, newattr)
    oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)
    try:
        while True:
            try:
                c = sys.stdin.read(1)
                return True
            except IOError:
                return False
    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)
        
                
if __name__ == '__main__':
    LOGIN_URL = 'http://weibo.cn' #测试用户登陆用
    
    #!编码重要:设置python(2.7.3)的内部处理encoding使用utf-8(默认ascii),以确保能在mac命令行下python执行本文件
    #详见http://docs.python.org/2/howto/unicode.html
    reload(sys)
    sys.setdefaultencoding('utf-8')
    print '系统编码：'
    print sys.getdefaultencoding()
    
    #weiquns=[('./张国荣','./张国荣.db',3231589944,6248,6593,LOGIN_URL)]
    
    
    #Trap time stamp    
    LAST_TRAP_TIME = datetime.datetime.now()
    #cookie
    #填写用户COOKIE
    COOKIE1 = 'gsid_CTandWM=4KxsCpOz1GZCmdnhIRfo3dyGpfe;_WEIBO_UID=3231589944'#david
    COOKIE2 = '_WEIBO_UID=3231589944; gsid_CTandWM=4KigCpOz1kJGN62tgSyo96K5D9h'#jion
    COOKIE3 = '_WEIBO_UID=3231589944; gsid_CTandWM=4KfJCpOz1RtwETBsrTJiC7bgieU'#mie
    COOKIE4 = 'gsid_CTandWM=4KHACpOz15FImpwmD6Dq2dJ48aI; _WEIBO_UID=3271500664'#miemiemie
    COOKIE5 = '_WEIBO_UID=3271500664; gsid_CTandWM=4KNhCpOz1mRs5r4AA9S1adTAz7N'#my reg
    COOKIE = COOKIE5
    COOKIES = [COOKIE1,COOKIE2,COOKIE3,COOKIE4,COOKIE5]
    HEADERS_LOGIN = { "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",\
                "Accept-Charset":"GBK,utf-8;q=0.7,*;q=0.3",\
                'Accept-Encoding':'gzip,deflate,sdch',#这里告知服务器，可以用gzip压缩包传递html\ 
                'Accept-Language':'zh-CN,zh;q=0.8',\
                "Connection":"keep-alive",\
                "Host":"weibo.cn",\
                "Cookie": COOKIE,\
                "Referer":'''http://newlogin.sina.cn/crossDomain/?g=4KigCpOz1kJGN62tgSyo96K5D9h&t=1364395377&m=cdba&r=&u=http%3A%2F%2Fweibo.cn%2F%3Fgsid%3D4KigCpOz1kJGN62tgSyo96K5D9h%26vt%3D4&cross=1&vt=4''',\
                "User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_3) AppleWebKit/537.22 (KHTML, like Gecko) Chrome/25.0.1364.172 Safari/537.22",\
                }
          
    HEADERS_WEIQUN = {"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",\
                    'Accept-Encoding':'gzip,deflate',#这里告知服务器，可以用gzip压缩包传递html\ 
                    'Accept-Language':'zh-cn,zh;q=0.8,en-us;q=0.5,en;q=0.3',\
                    'Connection':'keep-alive',\
                    'Cookie':COOKIE,\
                    'Host':'q.weibo.cn',\
                    'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:17.0) Gecko/20100101 Firefox/17.0',\
                }    


    LOGIN_USER_NAME = 'daviddivad3231589944'
    userdbname = '../users.db'
    weiquns = [] 
    startpage=1
    
                   
    #读取 weiqun2download.txt 的微群号,下载总页数
    weiqunparas = []
    weiqunids = []     
    print '从weiqun2download.txt读取准备下载的weiqunids:'
    weiqunlist = 'weiqun2download.txt'
    with open(weiqunlist) as f:
        for i in f.readlines():
            res = re.sub('#',' ',i).split(' ')
            weiqunid = res[0].strip()
            endpage = int(res[1].strip())
            startpage = 1
            print  'weiqunid:',weiqunid
            print  'page:',startpage,'~',endpage
            weiqunparas.append( (weiqunid,startpage,endpage) )
    #准备db的下载列表
    create_user_db_table(userdbname)
        
    
    #wrap 微群crawler参数        
    for para in weiqunparas:
        weiqunid,startpage,endpage = para
        weiqun = ('../weiqun/%d'%int(weiqunid),'../weiqun/%d.db'%int(weiqunid),userdbname,'../users',weiqunid,startpage,endpage,LOGIN_URL)
        weiquns.append(weiqun)
        weiqunids.append(weiqunid)
            
    #初始化多个crawler
    crawlers = []
    for weiqun in weiquns[0:]:
        savedir,weibodbname,userdbname,usersdir,weiqunid,startpage,endpage,login_url = weiqun
    
        #初始化爬虫类
        crawler = Weiqun_crawler(weibodbname,userdbname,usersdir,savedir,weiqunid,startpage,endpage,HEADERS_WEIQUN,HEADERS_LOGIN,COOKIES,login_url ,4)
        crawlers.append(crawler)
        
        #update下载列表db(初次下载完成使用),返回未下载页数pages
        #crawler.update_download_list( endpage,showdetail=True)
        
        #建立下载列表
        crawler.load_weiqun_pages2download()

        #注意，登陆weibo.cn 和访问微群Headers不一样！
        #Headers使用Firefox登陆用插件Firebug获取
    for crawler in crawlers:
            #对单个微群 n线程爬取微群crawler
            threadnum = 10 #单群10线程一般会导致封禁
            multi_thread_crawl_weiqun(crawler, crawler.startpage, crawler.endpage,\
                threadnum, showdetail=True)
            
            begin_pages = len(crawler.weiqun_pages2download)    
            print '======= 启动爬虫%d线程 微群id:%s 任务:%d页 ======'%(threadnum,\
                str(crawler.weiqunID),begin_pages )
            
            
            #--------------------------分析weibo部分----------------------------- 
            #从磁盘上的网页pages内抽取微博信息weiboinfos[],并把分离的每条微博存到磁盘
            weiboinfos = crawler.start_analyze_weibos_from_disk(showdetail=False)
            #把微博信息存储到数据库中
            crawler.end_analyze_weibos_to_db()
            
            
            #--------------------------处理RT Reply部分----------------------------- 
            #从数据库中读取每条微博的评论`转发url，下载到本地
            crawler.rtreply_crawl(startpage,endpage,showdetail=True)
    
            #分析本地的rt reply网页（返回失败页路径）
            crawler.start_rtreply_analyze()
            #储存rt reply分析结果到db
            crawler.end_rtreply_analyze_to_db()
            
                        


########NEW FILE########
__FILENAME__ = sina_reptile
#!/usr/bin/python
#-*-coding:utf8-*-
from pprint import pprint
from weibopy.auth import OAuthHandler
from weibopy.api import API
from weibopy.binder import bind_api
from weibopy.error import WeibopError
import time,os,pickle,sys
import logging.config 
from multiprocessing import Process

import sqlite3 as sqlite
import math
import re
MAX_INSERT_ERROR = 5000
#from pymongo import Connection
CALL_BACK = 'http://www.littlebuster.com'
CALL_BACK=None
CALL_BACK='oob'
mongo_addr = 'localhost'
mongo_port = 27017
db_name = 'weibo'


a_consumer_key = '211160679'
a_consumer_secret = '63b64d531b98c2dbff2443816f274dd3'
a_key = '44bd489d6a128abefdd297ae8d4a494d'
a_secret = 'fb4d6d537ccc6b23d21dc888007a08d6'
someoneid = '1404376560'
davidid='3231589944'
a_ids = [davidid]

class Sina_reptile():
    """
    爬取sina微博数据
    """

    def __init__(self,consumer_key,consumer_secret,userdbname):
        self.consumer_key,self.consumer_secret = consumer_key,consumer_secret
        self.con_user = None
        self.cur_user = None
        try:
            self.con_user = sqlite.connect(userdbname,timeout = 20)
            self.cur_user = self.con_user.cursor()
        except Exception,e:
            print 'Sina_reptile init无法连接数据库!'
            print e
            return None
        #self.connection = Connection(mongo_addr,mongo_port)
        #self.db = self.connection[db_name]
        #self.collection_userprofile = self.db['userprofile']
        #self.collection_statuses = self.db['statuses']

    def getAtt(self, key):
        try:
            return self.obj.__getattribute__(key)
        except Exception, e:
            print e
            return ''

    def getAttValue(self, obj, key):
        try:
            return obj.__getattribute__(key)
        except Exception, e:
            print e
            return ''

    def auth(self):
        """
        用于获取sina微博  access_token 和access_secret
        """
        if len(self.consumer_key) == 0:
            print "Please set consumer_key"
            return
        
        if len(self.consumer_secret) == 0:
            print "Please set consumer_secret"
            return
        
        self.auth = OAuthHandler(self.consumer_key, self.consumer_secret,CALL_BACK)
        auth_url = self.auth.get_authorization_url()
        print 'Please authorize: ' + auth_url
        verifier = raw_input('PIN: ').strip()
        #403error
        self.auth.get_access_token(verifier)
        self.api = API(self.auth)
        print 'authorize success'

    def setToken(self, token, tokenSecret):
        """
        通过oauth协议以便能获取sina微博数据
        """
        self.auth = OAuthHandler(self.consumer_key, self.consumer_secret)
        self.auth.setToken(token, tokenSecret)
        self.api = API(self.auth)

    def get_userprofile(self,id):
        """
        获取用户基本信息
        """
        try:
            userprofile = {}
            userprofile['id'] = id
            user = self.api.get_user(id)
            self.obj = user
            
            userprofile['screen_name'] = self.getAtt("screen_name")
            userprofile['name'] = self.getAtt("name")
            userprofile['province'] = self.getAtt("province")
            userprofile['city'] = self.getAtt("city")
            userprofile['location'] = self.getAtt("location")
            userprofile['description'] = self.getAtt("description")
            userprofile['url'] = self.getAtt("url")
            userprofile['profile_image_url'] = self.getAtt("profile_image_url")
            userprofile['domain'] = self.getAtt("domain")
            userprofile['gender'] = self.getAtt("gender")
            userprofile['followers_count'] = self.getAtt("followers_count")
            userprofile['friends_count'] = self.getAtt("friends_count")
            userprofile['statuses_count'] = self.getAtt("statuses_count")
            userprofile['favourites_count'] = self.getAtt("favourites_count")
            userprofile['created_at'] = self.getAtt("created_at")
            userprofile['following'] = self.getAtt("following")
            userprofile['allow_all_act_msg'] = self.getAtt("allow_all_act_msg")
            userprofile['geo_enabled'] = self.getAtt("geo_enabled")
            userprofile['verified'] = self.getAtt("verified")

#            for i in userprofile:
#                print type(i),type(userprofile[i])
#                print i,userprofile[i]
#            

        except WeibopError, e:      #捕获到的WeibopError错误的详细原因会被放置在对象e中
            print "error occured when access userprofile use user_id:",id
            print "Error:",e
            #log.error("Error occured when access userprofile use user_id:{0}\nError:{1}".format(id, e),exc_info=sys.exc_info())
            return None
            
        return userprofile

    def get_specific_weibo(self,id):
        """
        获取用户最近发表的50条微博
        """
        statusprofile = {}
        statusprofile['id'] = id
        try:
            #重新绑定get_status函数
            get_status = bind_api( path = '/statuses/show/{id}.json', 
                                 payload_type = 'status',
                                 allowed_param = ['id'])
        except:
            return "**绑定错误**"
        status = get_status(self.api,id)
        self.obj = status
        statusprofile['created_at'] = self.getAtt("created_at")
        statusprofile['text'] = self.getAtt("text")
        statusprofile['source'] = self.getAtt("source")
        statusprofile['favorited'] = self.getAtt("favorited")
        statusprofile['truncated'] = self.getAtt("ntruncatedame")
        statusprofile['in_reply_to_status_id'] = self.getAtt("in_reply_to_status_id")
        statusprofile['in_reply_to_user_id'] = self.getAtt("in_reply_to_user_id")
        statusprofile['in_reply_to_screen_name'] = self.getAtt("in_reply_to_screen_name")
        statusprofile['thumbnail_pic'] = self.getAtt("thumbnail_pic")
        statusprofile['bmiddle_pic'] = self.getAtt("bmiddle_pic")
        statusprofile['original_pic'] = self.getAtt("original_pic")
        statusprofile['geo'] = self.getAtt("geo")
        statusprofile['mid'] = self.getAtt("mid")
        statusprofile['retweeted_status'] = self.getAtt("retweeted_status")
        return statusprofile

    def get_latest_weibo(self,user_id,count):
        """
        获取用户最新发表的count条数据
        """
        statuses,statusprofile = [],{}
        try:            #error occur in the SDK
            timeline = self.api.user_timeline(count=count, user_id=user_id)
        except Exception as e:
            print "error occured when access status use user_id:",user_id
            print "Error:",e
            #log.error("Error occured when access status use user_id:{0}\nError:{1}".format(user_id, e),exc_info=sys.exc_info())
            return None
        for line in timeline:
            self.obj = line
            statusprofile['usr_id'] = user_id
            statusprofile['id'] = self.getAtt("id")
            statusprofile['created_at'] = self.getAtt("created_at")
            statusprofile['text'] = self.getAtt("text")
            statusprofile['source'] = self.getAtt("source")
            statusprofile['favorited'] = self.getAtt("favorited")
            statusprofile['truncated'] = self.getAtt("ntruncatedame")
            statusprofile['in_reply_to_status_id'] = self.getAtt("in_reply_to_status_id")
            statusprofile['in_reply_to_user_id'] = self.getAtt("in_reply_to_user_id")
            statusprofile['in_reply_to_screen_name'] = self.getAtt("in_reply_to_screen_name")
            statusprofile['thumbnail_pic'] = self.getAtt("thumbnail_pic")
            statusprofile['bmiddle_pic'] = self.getAtt("bmiddle_pic")
            statusprofile['original_pic'] = self.getAtt("original_pic")
            statusprofile['geo'] = repr(pickle.dumps(self.getAtt("geo"),pickle.HIGHEST_PROTOCOL))
            statusprofile['mid'] = self.getAtt("mid")
            statusprofile['retweeted_status'] = repr(pickle.dumps(self.getAtt("retweeted_status"),pickle.HIGHEST_PROTOCOL))
            statuses.append(statusprofile)

#            print '*************',type(statusprofile['retweeted_status']),statusprofile['retweeted_status'],'********'
#        for j in statuses:
#            for i in j:
#                print type(i),type(j[i])
#                print i,j[i]

        return statuses

    def friends_ids(self,id):
        """
        获取用户关注列表id
        """
        next_cursor,cursor = 1,0
        ids = []
        while(0!=next_cursor):
            fids = self.api.friends_ids(user_id=id,cursor=cursor)
            self.obj = fids
            ids.extend(self.getAtt("ids"))
            cursor = next_cursor = self.getAtt("next_cursor")
            previous_cursor = self.getAtt("previous_cursor")
        return ids
    
    def followers_ids(self,id):
        """
        获取用户粉丝列表id
        """
        next_cursor,cursor = 1,0
        ids = []
        while(0!=next_cursor):
            fids = self.api.followers_ids(user_id=id,cursor=cursor)
            self.obj = fids
            ids.extend(self.getAtt("ids"))
            cursor = next_cursor = self.getAtt("next_cursor")
            previous_cursor = self.getAtt("previous_cursor")
        return ids
    
    def manage_access(self):
        """
        管理应用访问API速度,适时进行沉睡
        """
        info = self.api.rate_limit_status()
        self.obj = info
        sleep_time = round( (float)(self.getAtt("reset_time_in_seconds"))/self.getAtt("remaining_hits"),2 ) if self.getAtt("remaining_hits") else self.getAtt("reset_time_in_seconds")
        print self.getAtt("remaining_hits"),self.getAtt("reset_time_in_seconds"),self.getAtt("hourly_limit"),self.getAtt("reset_time")
        print "sleep time:",sleep_time,'pid:',os.getpid()
        time.sleep(sleep_time + 1.5)

    def save_data(self,userprofile,statuses):
        #self.collection_statuses.insert(statuses)
        #self.collection_userprofile.insert(userprofile)
        pass
        
def reptile(sina_reptile,userid):
    ids_num,ids,new_ids,return_ids = 1,[userid],[userid],[]
    while(ids_num <= 10000000):
        next_ids = []
        for id in new_ids:
            try:
                sina_reptile.manage_access()
                return_ids = sina_reptile.friends_ids(id)
                ids.extend(return_ids)
                userprofile = sina_reptile.get_userprofile(id)
                statuses = sina_reptile.get_latest_weibo(count=50, user_id=id)
                if statuses is None or userprofile is None:
                    continue
                sina_reptile.save_data(userprofile,statuses)
            except Exception as e:
                print "log Error occured in reptile"
                #log.error("Error occured in reptile,id:{0}\nError:{1}".format(id, e),exc_info=sys.exc_info())
                time.sleep(60)
                continue
            ids_num+=1
            print ids_num
            if(ids_num >= 10000000):break
            next_ids.extend(return_ids)
        next_ids,new_ids = new_ids,next_ids

def run_crawler(consumer_key,consumer_secret,key,secret,userid,userdbname):
    try:
        
        sina_reptile = Sina_reptile(consumer_key,consumer_secret,userdbname)
        sina_reptile.setToken(key, secret)
        reptile(sina_reptile,userid)
        #sina_reptile.connection.close()
    except Exception as e:
        print e
        print 'log Error  occured in run_crawler'
        #log.error("Error occured in run_crawler,pid:{1}\nError:{2}".format(os.getpid(), e),exc_info=sys.exc_info())

def run_my_crawler(consumer_key,consumer_secret,key,secret,userdbname,ids):
    if ids:
        if len(ids)>0:
            try:
                sina_reptile = Sina_reptile(consumer_key,consumer_secret,userdbname)
                sina_reptile.setToken(key, secret)
                reptile_friends_of_uids_to_db(sina_reptile,ids,userdbname)
            except Exception as e:
                print 'Error occured in run_my_crawler,pid:%s'%str(os.getpid())
                print e
                #log.error("Error occured in run_my_crawler,pid:{1}\nError:{2}".format(os.getpid(), e),exc_info=sys.exc_info())
        else:
            print 'run_my_crawler ids[]<=0',ids
    else:
        print 'run_my_crawler ids[] is None',ids

def get_uids_in_weibodb(weibodbname):
    '''
    任务:从数据库weibodbname中获取uids='xxx'
    返回:uids[]
        None 如果无法连接数据库
    '''
    #init db
    try:
        con_weibo = sqlite.connect(weibodbname)
        cur_weibo = con_weibo.cursor()
    except Exception,e:
        print 'reptile_friends_of_uids_to_db无法连接数据库!'
        print e
        return None
    
    try:
        cur_weibo.execute("SELECT DISTINCT userid FROM weibos")
        con_weibo.commit()
    except Exception,E:
        print 'get_uids_in_weibodb：从db读取uid错误'
        print E
        return None


    list = cur_weibo.fetchall()
    uids=[]
    print 'get_uids_in_weibodb共读取用户：%d个 从weibodb:%s'%(len(list),weibodbname)
    for row in list:
        uid, = row
        if uid:
            uids.append(str(uid))
    print 'get_uids_in_weibodb返回取用户：%d个'%len(uids)
    con_weibo.close()
    return uids
        
def get_undonwload_ids(ids):
    '''
    任务:从userdbname数据库中的relation表中
    返回:[]待下载的ids
        None 连接数据库错误
    '''
    print 'get_undonwload_ids:得到%d个用户,从%s找出待下载关系的用户'%(len(ids),userdbname)
    #init db
    try:
        con_user = sqlite.connect(userdbname)
        cur_user = con_user.cursor()
    except Exception,e:
        print 'get_undonwload_ids 无法连接数据库!'
        print e
        return None
    
    #从gotrelation表找出没下载过的ids 
    ids_to_download = []
    for userid in ids:
        userid = str(userid)
        if not has_gotrelation_db(cur_user,con_user,userid):
            if userid not in ids_to_download:
                ids_to_download.append(userid)
                
    print 'get_undonwload_ids:还需要下载%d个用户'%(len(ids_to_download))
    return ids_to_download


def create_user_db_table(userdbname):
    #init db
    print 'create_user_db_table in db:%s'%userdbname
    try:
        con_user = sqlite.connect(userdbname)
        cur_user = con_user.cursor()
    except Exception,e:
        print 'create_user_db_table: error'
        print e
        return None
    #create tb   
    try:
        cur_user.execute('CREATE TABLE relation(userid TEXT ,followerid TEXT,PRIMARY KEY(userid,followerid));')
        con_user.commit()
    except Exception,e:
        print e
        pass
    try:
        cur_user.execute('CREATE TABLE gotrelation(userid TEXT PRIMARY KEY,gotfans INTERGER,gotfos INTERGER);')
        con_user.commit()
    except Exception,e:
        print e
        pass

def reptile_friends_of_uids_to_db(sina_reptile,ids_to_download,userdbname):
    '''
    任务:把ids的粉丝/关注用api爬取,放到userdbname数据库中的relation表中
    返回:None 无法连接数据库
        True 完成
    '''
    print 'reptile_friends_of_uids_to_db:得到%d个用户,待爬取关系至%s'%(len(ids_to_download),userdbname)
       
    for userid in ids_to_download:
        #id 的关注
        frids = reptile_friends_of_uid(sina_reptile,userid)
        #id的粉丝
        foids = reptile_fos_of_uid(sina_reptile,userid)
        print 'reptile_friends_of_uids_to_db:为用户%s找到%d个关注,%d个粉丝'%(userid,len(frids),len(foids))
        count=0
        gotfans = len(foids)
        gotfos  = len(frids)
        ins_fans = 0
        ins_fos = 0
        has_relation = 0
        sql_fri = ''
        sql_fo = ''
        if frids:#用户的关注
            fri_ins_error = 0#记录插入fan错误次数
            for frid in frids:
                frid = str(frid)
                count+=1
                ins_fos+=1
                sql_fri = 'INSERT INTO relation(userid ,followerid) VALUES("%s","%s");'%(frid,userid)
                try:
                    sina_reptile.cur_user.execute(sql_fri)
                except Exception,e:
                    #print 'got fri relation %s fo %s'%(str(userid),str(frid))
                    has_relation+=1
                    fri_ins_error+=1
                    #print sql_fri
                    #print e
                    if fri_ins_error>MAX_INSERT_ERROR:#如果插入三次都错误,很有可能是已有记录,跳出for
                        print '\t插入%d次错误,跳出%s关注关系插入'%(fri_ins_error,userid)
                        break
                    continue
                    pass
            try:
                sina_reptile.con_user.commit()
            except Exception,e:
                print 'reptile_friends_of_uids_to_db commit插入%s的关注(%d个)有问题:'%(userid,len(frids))
                print e
                pass
            
        if foids:#用户的粉丝
            fo_ins_error = 0#记录插入fo错误次数
            for foid in foids:
                followerid = str(foid)
                count+=1
                ins_fans+=1
                sql_fo = 'INSERT INTO relation(userid ,followerid) VALUES("%s","%s");'%(userid,followerid)
                try:
                    sina_reptile.cur_user.execute(sql_fo)
                except Exception,e:
                    #print 'got fri relation %s fo %s'%(str(foid),str(userid))
                    has_relation+=1
                    fo_ins_error+=1
                    #print sql_fo
                    print e
                    if fo_ins_error>MAX_INSERT_ERROR:#如果插入三次都错误,很有可能是已有记录,跳出for
                        print '\t插入%d次错误,跳出%s粉丝关系插入'%(fo_ins_error,userid)
                        break
                    continue
                    pass
            try:
                sina_reptile.con_user.commit()
            except Exception,e:
                print 'reptile_friends_of_uids_to_db commit插入%s的粉丝(%d个)有问题:'%(userid,len(foids))
                print e
                pass
        
        if has_relation!=0:
            print '\tuid:%s已经有关系记录'%str(userid),has_relation,'个'

        
        if count!=(len(frids)+len(foids)):
            print '\t 用户%s少添加关系%d个'%(userid, (len(frids) + len(foids) - count) )
        
        #更新下载表gotrelation
        print '\t更新gotrelation表 uid:%s,fans/fos:'%userid,gotfans,gotfos
        update_gotrelation_db(sina_reptile.cur_user, sina_reptile.con_user,userid,gotfans,gotfos)
    
    sina_reptile.con_user.close()
    print 'reptile_friends_of_uids_to_db:完成%d个用户的关系爬取至%s'%(len(ids_to_download),userdbname)
    return True

def has_gotrelation_db(cur_user,con_user,uid,check_serious=True):
    '''
    任务:检查是否下载过关系
    #如果check_serious 则从db table relation与gotrelation找出fans fos数校对(1秒1个 慢)   
    #否则 查若有gotrelation项  则return True
    '''
    #如果严格检查,则从relation表中找出某个uid的 fans fos数量(1秒1个 慢)   
    if check_serious:
        fans=0
        fos=0
        #get fans relation num
        try:
            cur_user.execute("""SELECT COUNT(*) FROM relation WHERE userid=='%s' ;"""%uid)
            con_user.commit()
            res = cur_user.fetchone()
            fans,=res
        except Exception,e:
            print 'has_gotrelation_db 读取relation表有问题,uid= %s'%(uid)
            print e
            return False 
    
        #get fri relation num
        try:
            cur_user.execute("""SELECT COUNT(*) FROM relation WHERE followerid=='%s' ;"""%uid)
            con_user.commit()
            res = cur_user.fetchone()
            fos,=res
        except Exception,e:
            print 'has_gotrelation_db 读取relation表有问题,uid= %s'%(uid)
            print e
            return False 
    
    
    #从gotrelation表中获取 fans fos数(快)
    try:
        cur_user.execute("""SELECT userid,gotfans,gotfos FROM gotrelation WHERE userid=='%s' ;"""%uid)
        con_user.commit()
    except Exception,e:
        print 'has_gotrelation_db 读取gotrelation表有问题,uid= %s'%(uid)
        print e
        return False
        
    list = cur_user.fetchone()
    if list:
        userid,gotfans,gotfos = list
        if str(userid)==str(uid):
            #看参数决定是否严格检查
            if check_serious:
                if gotfans<=fans and gotfos<=fos:
                    #print 'has_got(serious)....',list,fans,fos
                    return True
            else:#不严格检查  有项则跳过
                #print 'not_got',list,fans,fos
                return True
    
    #print 'final_not_got',uid,fans,fos
    return False

#无用
def test_load_gotrelation_db(userids):
    userids=['1937245577','1402787970','1234567890']
    con_user = sqlite.connect('../users.db')
    cur_user = con_user.cursor()
    sql = '''SELECT    userid FROM    gotrelation WHERE userid=='%s' '''
    for userid in userids:
        try:
            cur_user.execute( sql%str(userid) )
            tup= cur_user.fetchone()
            
            if tup is not None:#有用户
                print sql,userid
                print tup
                
        except Exception,e:
            print 'test_load_gotrelation_db 读取gotrelation表有问题,uid= %s'%(userid)
            print e
    con_user.close()
                
#无用               
def load_gotrelation_db(cur,con,userids):
    '''
    给定userids,到users.db->gotrelation中看看是否有下载好的userid,若没有,加入wait_userids[]
    返回:需要下载的wait_userids
    '''
    #userids.sort()
    sql = '''SELECT    userid FROM    gotrelation WHERE userid=='%s' '''
    #sql = '''SELECT    count(*) FROM    gotrelation  '''
    wait_userids = []
    con_user = sqlite.connect('../users.db')
    cur_user = con_user.cursor()
    for userid in userids:
        #???没有返回??? 单步试试
        try:
            cur_user.execute( sql% str(userid) )
            tup= cur_user.fetchone()
            
            if tup is not None:#有用户
                print '\t已有用户:%s'%str(userid)
                print sql,userid
                print tup
            else:
                #print '\t没有用户:%s'%str(userid)
                wait_userids.append(userid)
                
        except Exception,e:
            print 'test_load_gotrelation_db 读取gotrelation表有问题,uid= %s'%(userid)
            print e
        
    print 'load_gotrelation_db 复查:需要下载%d个用户'%len(wait_userids)
    con_user.close()
    return wait_userids

def update_gotrelation_db(cur_user,con_user,userid,gotfans,gotfos):
    #更新下载表gotrelation
    try:
        cur_user.execute("""REPLACE INTO gotrelation(userid,gotfans,gotfos) VALUES('%s',%d,%d)"""%(userid,gotfans,gotfos))
        con_user.commit()
    except Exception,e:
        print 'update_gotrelation_db 更新gotrelation表有问题,uid= %s'%(userid)
        print e
        
    

def reptile_fos_of_uid(sina_reptile,id):
    '''
    返回:ids[] id的粉丝
    '''
    try:
        sina_reptile.manage_access()
        #ids = [int,int,...]
        return_ids = []
        return_ids.extend(sina_reptile.followers_ids(id))
        #print '获取id:%s的fos:'%id
        #print return_ids
    except Exception as e:
        #log.error("Error occured in reptile,id:{0}\nError:{1}".format(id, e),exc_info=sys.exc_info())
        print 'logerror("Error occured in reptile_fans_fos_of_uid,id:{0}\nError:{1}".format(id, e),exc_info=sys.exc_info()'
        time.sleep(60)
    return return_ids

def reptile_friends_of_uid(sina_reptile,id):
    '''
    返回:ids[] id关注的用户
    '''
    try:
        return_ids = []
        sina_reptile.manage_access()
        #ids = [int,int,...]
        return_ids.extend( sina_reptile.friends_ids(id))
        #print '获取id:%s的fos:'%id
        #print return_ids
    except Exception as e:
        #log.error("Error occured in reptile,id:{0}\nError:{1}".format(id, e),exc_info=sys.exc_info())
        print 'logerror("Error occured in reptile_friends_of_uid,id:{0}\nError:{1}".format(id, e),exc_info=sys.exc_info()'
        time.sleep(60)
    return return_ids


#split the arr into N chunks 
#如[1,2,3,4,5] m=2 -> [[1,2,3] [4,5]]
def chunks(arr, m):
    n = int(math.ceil(len(arr) / float(m)))
    return [arr[i:i + n] for i in range(0, len(arr), n)]

#或者让一共有m块，自动分（尽可能平均）
#如[1,2,3,4,5] m=2 -> [[1,3,5] [2,4]]
def chunks_avg(arr, m):
    n = int(math.ceil(len(arr) / float(m)))
    res = [arr[i:i + n] for i in range(0, len(arr), n)]
    
    if m < len(arr):
        maxsplit = m
    else:
        maxsplit = len(arr)
    newres = [ [] for i in range(0,maxsplit)]
    
    for i in range(0,len(arr)):
        newres[i%m].append(arr[i])
        pass
    return newres
    
def test_chunks():
    arr = []    
    m = 100
    for i in range(1,50):
        arr.append(i)

    res = chunks_avg(arr,m)
    print 'chunks_avg:'
    for i in res:
        print i

    res = chunks(arr,m)
    print 'chunks:'
    for i in res:
        print i
if __name__ == "__main__":
    '''
    读取weiqun2download.txt的weiqunid,从weiqunid.db获取用户id,用api下载用户关系
    '''
    
    #读weiqunid
    print '从weiqun2download.txt读取准备下载的weiqunIDs:'
    weiqunlist = 'weiqun2download.txt'
    weiqunIDs=[]
    weiqunparas=[]
    with open(weiqunlist) as f:
        for i in f.readlines():
            res = re.sub('#',' ',i).split(' ')
            weiqunid = res[0].strip()
            endpage = int(res[1].strip())
            startpage = 1
            print  'weiqunid:',weiqunid
            print  'page:',startpage,'~',endpage
            weiqunparas.append( (weiqunid,startpage,endpage) )
            weiqunIDs.append(weiqunid)

    logging.config.fileConfig("logging.conf")
    log = logging.getLogger('logger_sina_reptile')
    
    
    
    #consumer_key= '应用的key'
    #consumer_secret ='应用的App Secret'
    #token = '用户的Access token key'
    #tokenSecret = '用户的Access token secret'
    

    
    userdbname = '../users.db'
    weiqunids = weiqunIDs
    weibodbnames=[]
    ids_to_download = []
    
    
    
    # my test
    #sina_reptile = Sina_reptile(a_consumer_key,a_consumer_secret,userdbname)
    #sina_reptile.setToken(a_key, a_secret)
    
    #建立users.db(负责储存下载列表,储存用户关系)
    create_user_db_table(userdbname)
    
    #获取所有weiqundb的ids
    for weiqunid in weiqunids:
        weibodbnames.append('../weiqun/%s.db'%weiqunid)

    for weibodbname in weibodbnames:
        ids = get_uids_in_weibodb(weibodbname)
        if ids:
            ids_to_download.extend( get_undonwload_ids(ids) )
    
    #单个爬虫运行
    #reptile_friends_of_uids_to_db(sina_reptile,ids_to_download,userdbname)
    
    #多个爬虫运行
    
    #获取爬虫数目
    crawler_count = 0
    crawlerids = 'clawer.txt'#20线程
    crawlerids = 'crawlertest.txt'#2线程
    with open(crawlerids) as f:
        for i in f.readlines():
            crawler_count+=1
    print '有%d个sina API sectret key'%crawler_count
    
    #切分ids[]
    if len(ids_to_download):
        ids_list = chunks(ids_to_download,crawler_count)
        print '切分成任务块:',crawler_count
    else:#没有任务则推出
        print '没有任务,退出'
        sys.exit(0)
    i=0
    for ids in ids_list:
        i+=len(ids)
    print '\t把%d个ID分成%d个任务.\n开始爬行!!!!!!!!'%(i,len(ids_list))
    
    #开始爬行
    print 'API secret:'
    with open(crawlerids) as f:
        index=0
        for i in f.readlines():
            print i
            j = i.strip().split(' ')
            p = Process(target=run_my_crawler, args=(j[0],j[1],j[2],j[3],userdbname,ids_list[index]))
            index+=1
            print '爬虫%d启动!!'%index
            p.start()
            #time.sleep(10000)

    
    
    #friendids = reptile_friends_of_uid(sina_reptile,ids)
    #print friendids
    
    #userprofile = sina_reptile.get_userprofile(davidid)
    #weibo = sina_reptile.get_specific_weibo("3408234545293850")
    #print userprofile
    #sina_reptile.manage_access()
    #print weibo
    
    #'''


    
    
    # origins:
    #sina_reptile = Sina_reptile('2173594644','fc76ecb30a3734ec6e493e472c5797f8')
    #sina_reptile.auth()
    #sina_reptile.setToken("e42c9ac01abbb0ccf498689f70ecce56", "dee15395b02e87eedc56e380807528a8")
    #sina_reptile.get_userprofile("1735950160")
#    sina_reptile.get_specific_weibo("3408234545293850")
##    sina_reptile.get_latest_weibo(count=50, user_id="1735950160")
##    sina_reptile.friends_ids("1404376560")
#    reptile(sina_reptile)
#    sina_reptile.manage_access()

########NEW FILE########
__FILENAME__ = api


# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import os
import mimetypes

from weibopy.binder import bind_api
from weibopy.error import WeibopError
from weibopy.parsers import ModelParser


class API(object):
    """Mblog API"""

    def __init__(self, auth_handler=None,
        host='api.t.sina.com.cn', search_host='api.t.sina.com.cn',
        cache=None, secure=False, api_root='', search_root='',
        retry_count=0, retry_delay=0, retry_errors=None,source=None,
        parser=None, log = None):
        self.auth = auth_handler
        self.host = host
        if source == None:
            if auth_handler != None:
                self.source = self.auth._consumer.key
        else:
            self.source = source
        self.search_host = search_host
        self.api_root = api_root
        self.search_root = search_root
        self.cache = cache
        self.secure = secure
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.retry_errors = retry_errors
        self.parser = parser or ModelParser()
        self.log = log

    """ statuses/public_timeline """
    public_timeline = bind_api(
        path = '/statuses/public_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = []
    )

    """ statuses/home_timeline """
    home_timeline = bind_api(
        path = '/statuses/home_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/friends_timeline """
    friends_timeline = bind_api(
        path = '/statuses/friends_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )
    """ statuses/comment """
    comment = bind_api(
        path = '/statuses/comment.json',
        method = 'POST',
        payload_type = 'comments',
        allowed_param = ['id', 'cid', 'comment'],
        require_auth = True
    )
    
    """ statuses/comment_destroy """
    comment_destroy  = bind_api(
        path = '/statuses/comment_destroy/{id}.json',
        method = 'DELETE',
        payload_type = 'comments',
        allowed_param = ['id'],
        require_auth = True
    )
    
    """ statuses/comments_timeline """
    comments = bind_api(
        path = '/statuses/comments.json',
        payload_type = 'comments', payload_list = True,
        allowed_param = ['id', 'count', 'page'],
        require_auth = True
    )
    
    """ statuses/comments_timeline """
    comments_timeline = bind_api(
        path = '/statuses/comments_timeline.json',
        payload_type = 'comments', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )
    
    """ statuses/comments_by_me """
    comments_by_me = bind_api(
        path = '/statuses/comments_by_me.json',
        payload_type = 'comments', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )
    
    """ statuses/user_timeline """
    user_timeline = bind_api(
        path = '/statuses/user_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['id', 'user_id', 'screen_name', 'since_id',
                          'max_id', 'count', 'page']
    )

    """ statuses/mentions """
    mentions = bind_api(
        path = '/statuses/mentions.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/counts """
    counts = bind_api(
        path = '/statuses/counts.json',
        payload_type = 'counts', payload_list = True,
        allowed_param = ['ids'],
        require_auth = True
    )
    
    """ statuses/unread """
    unread = bind_api(
        path = '/statuses/unread.json',
        payload_type = 'counts'
    )
    
    """ statuses/retweeted_by_me """
    retweeted_by_me = bind_api(
        path = '/statuses/retweeted_by_me.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/retweeted_to_me """
    retweeted_to_me = bind_api(
        path = '/statuses/retweeted_to_me.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/retweets_of_me """
    retweets_of_me = bind_api(
        path = '/statuses/retweets_of_me.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/show """
    get_status = bind_api(
        path = '/statuses/show.json',
        payload_type = 'status',
        allowed_param = ['id']
    )

    """ statuses/update """
    update_status = bind_api(
        path = '/statuses/update.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['status', 'lat', 'long', 'source'],
        require_auth = True
    )
    """ statuses/upload """
    def upload(self, filename, status, lat=None, long=None, source=None):
        if source is None:
            source=self.source
        headers, post_data = API._pack_image(filename, 1024, source=source, status=status, lat=lat, long=long, contentname="pic")
        args = [status]
        allowed_param = ['status']
        
        if lat is not None:
            args.append(lat)
            allowed_param.append('lat')
        
        if long is not None:
            args.append(long)
            allowed_param.append('long')
        
        if source is not None:
            args.append(source)
            allowed_param.append('source')
        kargs={
               'post_data': post_data,
               'headers': headers,
               }    
        return bind_api(
            path = '/statuses/upload.json',            
            method = 'POST',
            payload_type = 'status',
            require_auth = True,
            allowed_param = allowed_param            
#        )(self, *args, post_data=post_data, headers=headers)
         )(self, *args, **kargs)
        
    """ statuses/reply """
    reply = bind_api(
        path = '/statuses/reply.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id', 'cid','comment'],
        require_auth = True
    )
    
    """ statuses/repost """
    repost = bind_api(
        path = '/statuses/repost.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id', 'status'],
        require_auth = True
    )
    
    """ statuses/destroy """
    destroy_status = bind_api(
        path = '/statuses/destroy/{id}.json',
        method = 'DELETE',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ statuses/retweet """
    retweet = bind_api(
        path = '/statuses/retweet/{id}.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ statuses/retweets """
    retweets = bind_api(
        path = '/statuses/retweets/{id}.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['id', 'count'],
        require_auth = True
    )

    """ users/show """
    get_user = bind_api(
        path = '/users/show.json',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name']
    )
    
    """ Get the authenticated user """
    def me(self):
        return self.get_user(screen_name=self.auth.get_username())

    """ users/search """
    search_users = bind_api(
        path = '/users/search.json',
        payload_type = 'user', payload_list = True,
        require_auth = True,
        allowed_param = ['q', 'per_page', 'page']
    )

    """ statuses/friends """
    friends = bind_api(
        path = '/statuses/friends.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['id', 'user_id', 'screen_name', 'page', 'cursor']
    )

    """ statuses/followers """
    followers = bind_api(
        path = '/statuses/followers.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['id', 'user_id', 'screen_name', 'page', 'cursor']
    )

    """ direct_messages """
    direct_messages = bind_api(
        path = '/direct_messages.json',
        payload_type = 'direct_message', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ direct_messages/sent """
    sent_direct_messages = bind_api(
        path = '/direct_messages/sent.json',
        payload_type = 'direct_message', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )
    """ direct_messages/new """
    new_direct_message = bind_api(
        path = '/direct_messages/new.json',
        method = 'POST',
        payload_type = 'direct_message',
        allowed_param = ['id', 'screen_name', 'user_id', 'text'],
        require_auth = True
    )
    
    """ direct_messages/destroy """
    destroy_direct_message = bind_api(
        path = '/direct_messages/destroy/{id}.json',
        method = 'POST',
        payload_type = 'direct_message',
        allowed_param = ['id'],
        require_auth = True
    )

    """ friendships/create """
    create_friendship = bind_api(
        path = '/friendships/create.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name', 'follow'],
        require_auth = True
    )

    """ friendships/destroy """
    destroy_friendship = bind_api(
        path = '/friendships/destroy.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ friendships/exists """
    exists_friendship = bind_api(
        path = '/friendships/exists.json',
        payload_type = 'json',
        allowed_param = ['user_a', 'user_b']
    )

    """ friendships/show """
    show_friendship = bind_api(
        path = '/friendships/show.json',
        payload_type = 'friendship',
        allowed_param = ['source_id', 'source_screen_name',
                          'target_id', 'target_screen_name']
    )

    """ friends/ids """
    friends_ids = bind_api(
        path = '/friends/ids.json',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name', 'cursor', 'count'],
        require_auth = True
    )

    """ followers/ids """
    followers_ids = bind_api(        
        path = '/followers/ids.json',
        payload_type = 'json',
        allowed_param = ['id', 'page'],
    )

    """ account/verify_credentials """
    def verify_credentials(self):
        try:
            return bind_api(
                path = '/account/verify_credentials.json',
                payload_type = 'user',
                require_auth = True
            )(self)
        except WeibopError:
            return False

    """ account/rate_limit_status """
    rate_limit_status = bind_api(
        path = '/account/rate_limit_status.json',
        payload_type = 'json'
    )

    """ account/update_delivery_device """
    set_delivery_device = bind_api(
        path = '/account/update_delivery_device.json',
        method = 'POST',
        allowed_param = ['device'],
        payload_type = 'user',
        require_auth = True
    )
    """account/get_privacy"""
    get_privacy = bind_api(
        path = '/account/get_privacy.json',
        payload_type = 'json'                  
     )
    """account/update_privacy"""
    update_privacy = bind_api(
        path = '/account/update_privacy.json',
        payload_type = 'json',
        method = 'POST',
        allow_param = ['comment','message','realname','geo','badge'],
        require_auth = True                      
     )
    """ account/update_profile_colors """
    update_profile_colors = bind_api(
        path = '/account/update_profile_colors.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['profile_background_color', 'profile_text_color',
                          'profile_link_color', 'profile_sidebar_fill_color',
                          'profile_sidebar_border_color'],
        require_auth = True
    )
        
    """ account/update_profile_image """
    def update_profile_image(self, filename):
        headers, post_data = API._pack_image(filename=filename, max_size=700, source=self.source)
        return bind_api(
            path = '/account/update_profile_image.json',
            method = 'POST',
            payload_type = 'user',
            require_auth = True
        )(self, post_data=post_data, headers=headers)

    """ account/update_profile_background_image """
    def update_profile_background_image(self, filename, *args, **kargs):
        headers, post_data = API._pack_image(filename, 800)
        bind_api(
            path = '/account/update_profile_background_image.json',
            method = 'POST',
            payload_type = 'user',
            allowed_param = ['tile'],
            require_auth = True
        )(self, post_data=post_data, headers=headers)

    """ account/update_profile """
    update_profile = bind_api(
        path = '/account/update_profile.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['name', 'url', 'location', 'description'],
        require_auth = True
    )

    """ favorites """
    favorites = bind_api(
        path = '/favorites/{id}.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['id', 'page']
    )

    """ favorites/create """
    create_favorite = bind_api(
        path = '/favorites/create/{id}.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ favorites/destroy """
    destroy_favorite = bind_api(
        path = '/favorites/destroy/{id}.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ notifications/follow """
    enable_notifications = bind_api(
        path = '/notifications/follow.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ notifications/leave """
    disable_notifications = bind_api(
        path = '/notifications/leave.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ blocks/create """
    create_block = bind_api(
        path = '/blocks/create.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ blocks/destroy """
    destroy_block = bind_api(
        path = '/blocks/destroy.json',
        method = 'DELETE',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ blocks/exists """
    def exists_block(self, *args, **kargs):
        try:
            bind_api(
                path = '/blocks/exists.json',
                allowed_param = ['id', 'user_id', 'screen_name'],
                require_auth = True
            )(self, *args, **kargs)
        except WeibopError:
            return False
        return True

    """ blocks/blocking """
    blocks = bind_api(
        path = '/blocks/blocking.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['page'],
        require_auth = True
    )

    """ blocks/blocking/ids """
    blocks_ids = bind_api(
        path = '/blocks/blocking/ids.json',
        payload_type = 'json',
        require_auth = True
    )

    """ statuses/repost """
    report_spam = bind_api(
        path = '/report_spam.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ saved_searches """
    saved_searches = bind_api(
        path = '/saved_searches.json',
        payload_type = 'saved_search', payload_list = True,
        require_auth = True
    )

    """ saved_searches/show """
    get_saved_search = bind_api(
        path = '/saved_searches/show/{id}.json',
        payload_type = 'saved_search',
        allowed_param = ['id'],
        require_auth = True
    )

    """ saved_searches/create """
    create_saved_search = bind_api(
        path = '/saved_searches/create.json',
        method = 'POST',
        payload_type = 'saved_search',
        allowed_param = ['query'],
        require_auth = True
    )

    """ saved_searches/destroy """
    destroy_saved_search = bind_api(
        path = '/saved_searches/destroy/{id}.json',
        method = 'DELETE',
        payload_type = 'saved_search',
        allowed_param = ['id'],
        require_auth = True
    )

    """ help/test """
    def test(self):
        try:
            bind_api(
                path = '/help/test.json',
            )(self)
        except WeibopError:
            return False
        return True

    def create_list(self, *args, **kargs):
        return bind_api(
            path = '/%s/lists.json' % self.auth.get_username(),
            method = 'POST',
            payload_type = 'list',
            allowed_param = ['name', 'mode', 'description'],
            require_auth = True
        )(self, *args, **kargs)

    def destroy_list(self, slug):
        return bind_api(
            path = '/%s/lists/%s.json' % (self.auth.get_username(), slug),
            method = 'DELETE',
            payload_type = 'list',
            require_auth = True
        )(self)

    def update_list(self, slug, *args, **kargs):
        return bind_api(
            path = '/%s/lists/%s.json' % (self.auth.get_username(), slug),
            method = 'POST',
            payload_type = 'list',
            allowed_param = ['name', 'mode', 'description'],
            require_auth = True
        )(self, *args, **kargs)

    lists = bind_api(
        path = '/{user}/lists.json',
        payload_type = 'list', payload_list = True,
        allowed_param = ['user', 'cursor'],
        require_auth = True
    )

    lists_memberships = bind_api(
        path = '/{user}/lists/memberships.json',
        payload_type = 'list', payload_list = True,
        allowed_param = ['user', 'cursor'],
        require_auth = True
    )

    lists_subscriptions = bind_api(
        path = '/{user}/lists/subscriptions.json',
        payload_type = 'list', payload_list = True,
        allowed_param = ['user', 'cursor'],
        require_auth = True
    )

    list_timeline = bind_api(
        path = '/{owner}/lists/{slug}/statuses.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['owner', 'slug', 'since_id', 'max_id', 'count', 'page']
    )

    get_list = bind_api(
        path = '/{owner}/lists/{slug}.json',
        payload_type = 'list',
        allowed_param = ['owner', 'slug']
    )

    def add_list_member(self, slug, *args, **kargs):
        return bind_api(
            path = '/%s/%s/members.json' % (self.auth.get_username(), slug),
            method = 'POST',
            payload_type = 'list',
            allowed_param = ['id'],
            require_auth = True
        )(self, *args, **kargs)

    def remove_list_member(self, slug, *args, **kargs):
        return bind_api(
            path = '/%s/%s/members.json' % (self.auth.get_username(), slug),
            method = 'DELETE',
            payload_type = 'list',
            allowed_param = ['id'],
            require_auth = True
        )(self, *args, **kargs)

    list_members = bind_api(
        path = '/{owner}/{slug}/members.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['owner', 'slug', 'cursor']
    )

    def is_list_member(self, owner, slug, user_id):
        try:
            return bind_api(
                path = '/%s/%s/members/%s.json' % (owner, slug, user_id),
                payload_type = 'user'
            )(self)
        except WeibopError:
            return False

    subscribe_list = bind_api(
        path = '/{owner}/{slug}/subscribers.json',
        method = 'POST',
        payload_type = 'list',
        allowed_param = ['owner', 'slug'],
        require_auth = True
    )

    unsubscribe_list = bind_api(
        path = '/{owner}/{slug}/subscribers.json',
        method = 'DELETE',
        payload_type = 'list',
        allowed_param = ['owner', 'slug'],
        require_auth = True
    )

    list_subscribers = bind_api(
        path = '/{owner}/{slug}/subscribers.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['owner', 'slug', 'cursor']
    )

    def is_subscribed_list(self, owner, slug, user_id):
        try:
            return bind_api(
                path = '/%s/%s/subscribers/%s.json' % (owner, slug, user_id),
                payload_type = 'user'
            )(self)
        except WeibopError:
            return False

    """ trends/available """
    trends_available = bind_api(
        path = '/trends/available.json',
        payload_type = 'json',
        allowed_param = ['lat', 'long']
    )

    """ trends/location """
    trends_location = bind_api(
        path = '/trends/{woeid}.json',
        payload_type = 'json',
        allowed_param = ['woeid']
    )

    """ search """
    search = bind_api(
        search_api = True,
        path = '/search.json',
        payload_type = 'search_result', payload_list = True,
        allowed_param = ['q', 'lang', 'locale', 'rpp', 'page', 'since_id', 'geocode', 'show_user']
    )
    search.pagination_mode = 'page'

    """ trends """
    trends = bind_api(
        path = '/trends.json',
        payload_type = 'trends', payload_list = True,
        allowed_param = ['user_id','count','page'],
        require_auth= True
        )
    """trends/statuses"""
    trends_statuses = bind_api(
        path = '/trends/statuses.json', 
        payload_type = 'status', payload_list = True,
        allowed_param = ['trend_name'],
        require_auth = True
        
        )       
    """trends/follow"""
    trends_follow = bind_api(
        path = '/trends/follow.json',
        method = 'POST',
        allowed_param = ['trend_name'],
        require_auth = True
        )                     
    """trends/destroy"""
    trends_destroy = bind_api(
        path = '/trends/destroy.json',
        method = 'DELETE',
        allowed_param = ['trend_id'],
        require_auth = True
        )                                                                   
    """ trends/current """
    trends_current = bind_api(
        search_api = True,
        path = '/trends/current.json',
        payload_type = 'json',
        allowed_param = ['exclude']
    )
    """ trends/hourly"""
    trends_hourly = bind_api(
        search_api = True,
        path = '/trends/hourly.json',
        payload_type = 'trends',
        allowed_param = []
    )                      
    """ trends/daily """
    trends_daily = bind_api(
        search_api = True,
        path = '/trends/daily.json',
        payload_type = 'trends',
        allowed_param = []
    )

    """ trends/weekly """
    trends_weekly = bind_api(
        search_api = True,
        path = '/trends/weekly.json',
        payload_type = 'json',
        allowed_param = []
    )
    """ Tags """
    tags = bind_api(
        path = '/tags.json',
        payload_type = 'tags', payload_list = True,
        allowed_param = ['user_id'],
        require_auth= True,
        )          
    tag_create = bind_api(
        path = '/tags/create.json',
        payload_type = 'tags',
        method = 'POST',
        allowed_param = ['tags'],
        payload_list = True, 
        require_auth = True,
        )                                
    tag_suggestions = bind_api(
        path = '/tags/suggestions.json',
        payload_type = 'tags',
        require_auth = True,
        payload_list = True,
        )
    tag_destroy = bind_api(
        path = '/tags/destroy.json',
        payload_type = 'json',
        method='POST',   
        require_auth = True,
        allowed_param = ['tag_id'],
        ) 
    tag_destroy_batch = bind_api(
        path = '/tags/destroy_batch.json',
        payload_type = 'json',
        method='DELETE',   
        require_auth = True,
        payload_list = True,
        allowed_param = ['ids'],
        )                                                                              
    """ Internal use only """
    @staticmethod
    def _pack_image(filename, max_size, source=None, status=None, lat=None, long=None, contentname="image"):
        """Pack image from file into multipart-formdata post body"""
        # image must be less than 700kb in size
        try:
            if os.path.getsize(filename) > (max_size * 1024):
                raise WeibopError('File is too big, must be less than 700kb.')
        #except os.error, e:
        except os.error:
            raise WeibopError('Unable to access file')

        # image must be gif, jpeg, or png
        file_type = mimetypes.guess_type(filename)
        if file_type is None:
            raise WeibopError('Could not determine file type')
        file_type = file_type[0]
        if file_type not in ['image/gif', 'image/jpeg', 'image/png']:
            raise WeibopError('Invalid file type for image: %s' % file_type)

        # build the mulitpart-formdata body
        fp = open(filename, 'rb')
        BOUNDARY = 'Tw3ePy'
        body = []
        if status is not None:            
            body.append('--' + BOUNDARY)
            body.append('Content-Disposition: form-data; name="status"')
            body.append('Content-Type: text/plain; charset=US-ASCII')
            body.append('Content-Transfer-Encoding: 8bit')
            body.append('')
            body.append(status)
        if source is not None:            
            body.append('--' + BOUNDARY)
            body.append('Content-Disposition: form-data; name="source"')
            body.append('Content-Type: text/plain; charset=US-ASCII')
            body.append('Content-Transfer-Encoding: 8bit')
            body.append('')
            body.append(source)
        if lat is not None:            
            body.append('--' + BOUNDARY)
            body.append('Content-Disposition: form-data; name="lat"')
            body.append('Content-Type: text/plain; charset=US-ASCII')
            body.append('Content-Transfer-Encoding: 8bit')
            body.append('')
            body.append(lat)
        if long is not None:            
            body.append('--' + BOUNDARY)
            body.append('Content-Disposition: form-data; name="long"')
            body.append('Content-Type: text/plain; charset=US-ASCII')
            body.append('Content-Transfer-Encoding: 8bit')
            body.append('')
            body.append(long)
        body.append('--' + BOUNDARY)
        body.append('Content-Disposition: form-data; name="'+ contentname +'"; filename="%s"' % filename)
        body.append('Content-Type: %s' % file_type)
        body.append('Content-Transfer-Encoding: binary')
        body.append('')
        body.append(fp.read())
        body.append('--' + BOUNDARY + '--')
        body.append('')
        fp.close()        
        body.append('--' + BOUNDARY + '--')
        body.append('')
        body = '\r\n'.join(body)
        # build headers
        headers = {
            'Content-Type': 'multipart/form-data; boundary=Tw3ePy',
            'Content-Length': len(body)
        }

        return headers, body


########NEW FILE########
__FILENAME__ = auth

# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from urllib2 import Request, urlopen
import base64

from weibopy import oauth
from weibopy.error import WeibopError
from weibopy.api import API


class AuthHandler(object):

    def apply_auth(self, url, method, headers, parameters):
        """Apply authentication headers to request"""
        raise NotImplementedError

    def get_username(self):
        """Return the username of the authenticated user"""
        raise NotImplementedError


class BasicAuthHandler(AuthHandler):

    def __init__(self, username, password):
        self.username = username
        self._b64up = base64.b64encode('%s:%s' % (username, password))

    def apply_auth(self, url, method, headers, parameters):
        headers['Authorization'] = 'Basic %s' % self._b64up
        
    def get_username(self):
        return self.username


class OAuthHandler(AuthHandler):
    """OAuth authentication handler"""

    OAUTH_HOST = 'api.t.sina.com.cn'
    OAUTH_ROOT = '/oauth/'

    def __init__(self, consumer_key, consumer_secret, callback=None, secure=False):
        self._consumer = oauth.OAuthConsumer(consumer_key, consumer_secret)
        self._sigmethod = oauth.OAuthSignatureMethod_HMAC_SHA1()
        self.request_token = None
        self.access_token = None
        self.callback = callback
        self.username = None
        self.secure = secure

    def _get_oauth_url(self, endpoint):
        if self.secure:
            prefix = 'https://'
        else:
            prefix = 'http://'

        return prefix + self.OAUTH_HOST + self.OAUTH_ROOT + endpoint

    def apply_auth(self, url, method, headers, parameters):
        request = oauth.OAuthRequest.from_consumer_and_token(
            self._consumer, http_url=url, http_method=method,
            token=self.access_token, parameters=parameters
        )
        request.sign_request(self._sigmethod, self._consumer, self.access_token)
        headers.update(request.to_header())

    def _get_request_token(self):
        try:
            url = self._get_oauth_url('request_token')
            request = oauth.OAuthRequest.from_consumer_and_token(
                self._consumer, http_url=url, callback=self.callback
            )
            request.sign_request(self._sigmethod, self._consumer, None)
            print url
            print request.to_header()
            resp = urlopen(Request(url, headers=request.to_header()))
            return oauth.OAuthToken.from_string(resp.read())
        except Exception, e:
            raise WeibopError(e)

    def set_request_token(self, key, secret):
        self.request_token = oauth.OAuthToken(key, secret)

    def set_access_token(self, key, secret):
        self.access_token = oauth.OAuthToken(key, secret)

    def get_authorization_url(self, signin_with_twitter=False):
        """Get the authorization URL to redirect the user"""
        try:
            # get the request token
            self.request_token = self._get_request_token()

            
            print 'here'
            # build auth request and return as url
            if signin_with_twitter:
                url = self._get_oauth_url('authenticate')
            else:
                url = self._get_oauth_url('authorize')
            
            request = oauth.OAuthRequest.from_token_and_callback(
                token=self.request_token, http_url=url, callback=self.callback
            )

            return request.to_url()
        except Exception, e:
            raise WeibopError(e)

    def get_access_token(self, verifier=None):
        """
        After user has authorized the request token, get access token
        with user supplied verifier.
        """
        try:
            url = self._get_oauth_url('access_token')

            # build request
            request = oauth.OAuthRequest.from_consumer_and_token(
                self._consumer,
                token=self.request_token, http_url=url,
                verifier=str(verifier)
            )
            request.sign_request(self._sigmethod, self._consumer, self.request_token)

            # send request                        
            resp = urlopen(Request(url, headers=request.to_header()))
            self.access_token = oauth.OAuthToken.from_string(resp.read())
            
            print 'Access token key: '+ str(self.access_token.key)
            print 'Access token secret: '+ str(self.access_token.secret)
            
            return self.access_token
        except Exception, e:
            raise WeibopError(e)
        
    def setToken(self, token, tokenSecret):
        self.access_token = oauth.OAuthToken(token, tokenSecret)
        
    def get_username(self):
        if self.username is None:
            api = API(self)
            user = api.verify_credentials()
            if user:
                self.username = user.screen_name
            else:
                raise WeibopError("Unable to get username, invalid oauth token!")
        return self.username
########NEW FILE########
__FILENAME__ = binder

# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import httplib
import urllib
import time
import re
from weibopy.error import WeibopError
from weibopy.utils import convert_to_utf8_str

re_path_template = re.compile('{\w+}')


def bind_api(**config):

    class APIMethod(object):
        
        path = config['path']
        payload_type = config.get('payload_type', None)
        payload_list = config.get('payload_list', False)
        allowed_param = config.get('allowed_param', [])
        method = config.get('method', 'GET')
        require_auth = config.get('require_auth', False)
        search_api = config.get('search_api', False)
                
        def __init__(self, api, args, kargs):
            # If authentication is required and no credentials
            # are provided, throw an error.
            if self.require_auth and not api.auth:
                raise WeibopError('Authentication required!')

            self.api = api
            self.post_data = kargs.pop('post_data', None)
            self.retry_count = kargs.pop('retry_count', api.retry_count)
            self.retry_delay = kargs.pop('retry_delay', api.retry_delay)
            self.retry_errors = kargs.pop('retry_errors', api.retry_errors)
            self.headers = kargs.pop('headers', {})
            self.build_parameters(args, kargs)
            # Pick correct URL root to use
            if self.search_api:
                self.api_root = api.search_root
            else:
                self.api_root = api.api_root
            
            # Perform any path variable substitution
            self.build_path()

            if api.secure:
                self.scheme = 'https://'
            else:
                self.scheme = 'http://'

            if self.search_api:
                self.host = api.search_host
            else:
                self.host = api.host

            # Manually set Host header to fix an issue in python 2.5
            # or older where Host is set including the 443 port.
            # This causes Twitter to issue 301 redirect.
            # See Issue http://github.com/joshthecoder/tweepy/issues/#issue/12
            self.headers['Host'] = self.host

        def build_parameters(self, args, kargs):
            self.parameters = {}
            for idx, arg in enumerate(args):
                try:
                    self.parameters[self.allowed_param[idx]] = convert_to_utf8_str(arg)
                except IndexError:
                    raise WeibopError('Too many parameters supplied!')

            for k, arg in kargs.items():
                if arg is None:
                    continue
                if k in self.parameters:
                    raise WeibopError('Multiple values for parameter %s supplied!' % k)

                self.parameters[k] = convert_to_utf8_str(arg)

        def build_path(self):
            for variable in re_path_template.findall(self.path):
                name = variable.strip('{}')

                if name == 'user' and self.api.auth:
                    value = self.api.auth.get_username()
                else:
                    try:
                        value = urllib.quote(self.parameters[name])
                    except KeyError:
                        raise WeibopError('No parameter value found for path variable: %s' % name)
                    del self.parameters[name]

                self.path = self.path.replace(variable, value)

        def execute(self):
            # Build the request URL
            url = self.api_root + self.path
            if self.api.source is not None:
                self.parameters.setdefault('source',self.api.source)
            
            if len(self.parameters):
                if self.method == 'GET' or self.method == 'DELETE':
                    url = '%s?%s' % (url, urllib.urlencode(self.parameters))  
                else:
                    self.headers.setdefault("User-Agent","python")
                    if self.post_data is None:
                        self.headers.setdefault("Accept","text/html")                        
                        self.headers.setdefault("Content-Type","application/x-www-form-urlencoded")
                        self.post_data = urllib.urlencode(self.parameters)           
            # Query the cache if one is available
            # and this request uses a GET method.
            if self.api.cache and self.method == 'GET':
                cache_result = self.api.cache.get(url)
                # if cache result found and not expired, return it
                if cache_result:
                    # must restore api reference
                    if isinstance(cache_result, list):
                        for result in cache_result:
                            result._api = self.api
                    else:
                        cache_result._api = self.api
                    return cache_result
                #urllib.urlencode(self.parameters)
            # Continue attempting request until successful
            # or maximum number of retries is reached.
            sTime = time.time()
            retries_performed = 0
            while retries_performed < self.retry_count + 1:
                # Open connection
                # FIXME: add timeout
                if self.api.secure:
                    conn = httplib.HTTPSConnection(self.host)
                else:
                    conn = httplib.HTTPConnection(self.host)
                # Apply authentication
                if self.api.auth:
                    self.api.auth.apply_auth(
                            self.scheme + self.host + url,
                            self.method, self.headers, self.parameters
                    )
                # Execute request
                try:
                    conn.request(self.method, url, headers=self.headers, body=self.post_data)
                    resp = conn.getresponse()
                except Exception, e:
                    raise WeibopError('Failed to send request: %s' % e + "url=" + str(url) +",self.headers="+ str(self.headers))

                # Exit request loop if non-retry error code
                if self.retry_errors:
                    if resp.status not in self.retry_errors: break
                else:
                    if resp.status == 200: break

                # Sleep before retrying request again
                time.sleep(self.retry_delay)
                retries_performed += 1

            # If an error was returned, throw an exception
            body = resp.read()
            self.api.last_response = resp
            if self.api.log is not None:
                requestUrl = "URL:http://"+ self.host + url
                eTime = '%.0f' % ((time.time() - sTime) * 1000)
                postData = ""
                if self.post_data is not None:
                    postData = ",post:"+ self.post_data[0:500]
                self.api.log.debug(requestUrl +",time:"+ str(eTime)+ postData+",result:"+ body )
            if resp.status != 200:
                try:
                    json = self.api.parser.parse_error(self, body)
                    error_code =  json['error_code']
                    error =  json['error']
                    error_msg = 'error_code:' + error_code +','+ error
                except Exception:
                    error_msg = "Weibo error response: status code = %s" % resp.status
                raise WeibopError(error_msg)
            
            # Parse the response payload
            result = self.api.parser.parse(self, body)
            conn.close()

            # Store result into cache if one is available.
            if self.api.cache and self.method == 'GET' and result:
                self.api.cache.store(url, result)
            return result

    def _call(api, *args, **kargs):

        method = APIMethod(api, args, kargs)
        return method.execute()


    # Set pagination mode
    if 'cursor' in APIMethod.allowed_param:
        _call.pagination_mode = 'cursor'
    elif 'page' in APIMethod.allowed_param:
        _call.pagination_mode = 'page'

    return _call


########NEW FILE########
__FILENAME__ = cache

# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import time
import threading
import os
import cPickle as pickle

try:
    import hashlib
except ImportError:
    # python 2.4
    import md5 as hashlib

try:
    import fcntl
except ImportError:
    # Probably on a windows system
    # TODO: use win32file
    pass


class Cache(object):
    """Cache interface"""

    def __init__(self, timeout=60):
        """Initialize the cache
            timeout: number of seconds to keep a cached entry
        """
        self.timeout = timeout

    def store(self, key, value):
        """Add new record to cache
            key: entry key
            value: data of entry
        """
        raise NotImplementedError

    def get(self, key, timeout=None):
        """Get cached entry if exists and not expired
            key: which entry to get
            timeout: override timeout with this value [optional]
        """
        raise NotImplementedError

    def count(self):
        """Get count of entries currently stored in cache"""
        raise NotImplementedError

    def cleanup(self):
        """Delete any expired entries in cache."""
        raise NotImplementedError

    def flush(self):
        """Delete all cached entries"""
        raise NotImplementedError


class MemoryCache(Cache):
    """In-memory cache"""

    def __init__(self, timeout=60):
        Cache.__init__(self, timeout)
        self._entries = {}
        self.lock = threading.Lock()

    def __getstate__(self):
        # pickle
        return {'entries': self._entries, 'timeout': self.timeout}

    def __setstate__(self, state):
        # unpickle
        self.lock = threading.Lock()
        self._entries = state['entries']
        self.timeout = state['timeout']

    def _is_expired(self, entry, timeout):
        return timeout > 0 and (time.time() - entry[0]) >= timeout

    def store(self, key, value):
        self.lock.acquire()
        self._entries[key] = (time.time(), value)
        self.lock.release()

    def get(self, key, timeout=None):
        self.lock.acquire()
        try:
            # check to see if we have this key
            entry = self._entries.get(key)
            if not entry:
                # no hit, return nothing
                return None

            # use provided timeout in arguments if provided
            # otherwise use the one provided during init.
            if timeout is None:
                timeout = self.timeout

            # make sure entry is not expired
            if self._is_expired(entry, timeout):
                # entry expired, delete and return nothing
                del self._entries[key]
                return None

            # entry found and not expired, return it
            return entry[1]
        finally:
            self.lock.release()

    def count(self):
        return len(self._entries)

    def cleanup(self):
        self.lock.acquire()
        try:
            for k, v in self._entries.items():
                if self._is_expired(v, self.timeout):
                    del self._entries[k]
        finally:
            self.lock.release()

    def flush(self):
        self.lock.acquire()
        self._entries.clear()
        self.lock.release()


class FileCache(Cache):
    """File-based cache"""

    # locks used to make cache thread-safe
    cache_locks = {}

    def __init__(self, cache_dir, timeout=60):
        Cache.__init__(self, timeout)
        if os.path.exists(cache_dir) is False:
            os.mkdir(cache_dir)
        self.cache_dir = cache_dir
        if cache_dir in FileCache.cache_locks:
            self.lock = FileCache.cache_locks[cache_dir]
        else:
            self.lock = threading.Lock()
            FileCache.cache_locks[cache_dir] = self.lock

        if os.name == 'posix':
            self._lock_file = self._lock_file_posix
            self._unlock_file = self._unlock_file_posix
        elif os.name == 'nt':
            self._lock_file = self._lock_file_win32
            self._unlock_file = self._unlock_file_win32
        else:
            print 'Warning! FileCache locking not supported on this system!'
            self._lock_file = self._lock_file_dummy
            self._unlock_file = self._unlock_file_dummy

    def _get_path(self, key):
        md5 = hashlib.md5()
        md5.update(key)
        return os.path.join(self.cache_dir, md5.hexdigest())

    def _lock_file_dummy(self, path, exclusive=True):
        return None

    def _unlock_file_dummy(self, lock):
        return

    def _lock_file_posix(self, path, exclusive=True):
        lock_path = path + '.lock'
        if exclusive is True:
            f_lock = open(lock_path, 'w')
            fcntl.lockf(f_lock, fcntl.LOCK_EX)
        else:
            f_lock = open(lock_path, 'r')
            fcntl.lockf(f_lock, fcntl.LOCK_SH)
        if os.path.exists(lock_path) is False:
            f_lock.close()
            return None
        return f_lock

    def _unlock_file_posix(self, lock):
        lock.close()

    def _lock_file_win32(self, path, exclusive=True):
        # TODO: implement
        return None

    def _unlock_file_win32(self, lock):
        # TODO: implement
        return

    def _delete_file(self, path):
        os.remove(path)
        if os.path.exists(path + '.lock'):
            os.remove(path + '.lock')

    def store(self, key, value):
        path = self._get_path(key)
        self.lock.acquire()
        try:
            # acquire lock and open file
            f_lock = self._lock_file(path)
            datafile = open(path, 'wb')

            # write data
            pickle.dump((time.time(), value), datafile)

            # close and unlock file
            datafile.close()
            self._unlock_file(f_lock)
        finally:
            self.lock.release()

    def get(self, key, timeout=None):
        return self._get(self._get_path(key), timeout)

    def _get(self, path, timeout):
        if os.path.exists(path) is False:
            # no record
            return None
        self.lock.acquire()
        try:
            # acquire lock and open
            f_lock = self._lock_file(path, False)
            datafile = open(path, 'rb')

            # read pickled object
            created_time, value = pickle.load(datafile)
            datafile.close()

            # check if value is expired
            if timeout is None:
                timeout = self.timeout
            if timeout > 0 and (time.time() - created_time) >= timeout:
                # expired! delete from cache
                value = None
                self._delete_file(path)

            # unlock and return result
            self._unlock_file(f_lock)
            return value
        finally:
            self.lock.release()

    def count(self):
        c = 0
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            c += 1
        return c

    def cleanup(self):
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            self._get(os.path.join(self.cache_dir, entry), None)

    def flush(self):
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            self._delete_file(os.path.join(self.cache_dir, entry))


########NEW FILE########
__FILENAME__ = cursor

# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from weibopy.error import WeibopError

class Cursor(object):
    """Pagination helper class"""

    def __init__(self, method, *args, **kargs):
        if hasattr(method, 'pagination_mode'):
            if method.pagination_mode == 'cursor':
                self.iterator = CursorIterator(method, args, kargs)
            else:
                self.iterator = PageIterator(method, args, kargs)
        else:
            raise WeibopError('This method does not perform pagination')

    def pages(self, limit=0):
        """Return iterator for pages"""
        if limit > 0:
            self.iterator.limit = limit
        return self.iterator

    def items(self, limit=0):
        """Return iterator for items in each page"""
        i = ItemIterator(self.iterator)
        i.limit = limit
        return i

class BaseIterator(object):

    def __init__(self, method, args, kargs):
        self.method = method
        self.args = args
        self.kargs = kargs
        self.limit = 0

    def next(self):
        raise NotImplementedError

    def prev(self):
        raise NotImplementedError

    def __iter__(self):
        return self

class CursorIterator(BaseIterator):

    def __init__(self, method, args, kargs):
        BaseIterator.__init__(self, method, args, kargs)
        self.next_cursor = -1
        self.prev_cursor = 0
        self.count = 0

    def next(self):
        if self.next_cursor == 0 or (self.limit and self.count == self.limit):
            raise StopIteration
        data, cursors = self.method(
                cursor=self.next_cursor, *self.args, **self.kargs
        )
        self.prev_cursor, self.next_cursor = cursors
        if len(data) == 0:
            raise StopIteration
        self.count += 1
        return data

    def prev(self):
        if self.prev_cursor == 0:
            raise WeibopError('Can not page back more, at first page')
        data, self.next_cursor, self.prev_cursor = self.method(
                cursor=self.prev_cursor, *self.args, **self.kargs
        )
        self.count -= 1
        return data

class PageIterator(BaseIterator):

    def __init__(self, method, args, kargs):
        BaseIterator.__init__(self, method, args, kargs)
        self.current_page = 0

    def next(self):
        self.current_page += 1
        items = self.method(page=self.current_page, *self.args, **self.kargs)
        if len(items) == 0 or (self.limit > 0 and self.current_page > self.limit):
            raise StopIteration
        return items

    def prev(self):
        if (self.current_page == 1):
            raise WeibopError('Can not page back more, at first page')
        self.current_page -= 1
        return self.method(page=self.current_page, *self.args, **self.kargs)

class ItemIterator(BaseIterator):

    def __init__(self, page_iterator):
        self.page_iterator = page_iterator
        self.limit = 0
        self.current_page = None
        self.page_index = -1
        self.count = 0

    def next(self):
        if self.limit > 0 and self.count == self.limit:
            raise StopIteration
        if self.current_page is None or self.page_index == len(self.current_page) - 1:
            # Reached end of current page, get the next page...
            self.current_page = self.page_iterator.next()
            self.page_index = -1
        self.page_index += 1
        self.count += 1
        return self.current_page[self.page_index]

    def prev(self):
        if self.current_page is None:
            raise WeibopError('Can not go back more, at first page')
        if self.page_index == 0:
            # At the beginning of the current page, move to next...
            self.current_page = self.page_iterator.prev()
            self.page_index = len(self.current_page)
            if self.page_index == 0:
                raise WeibopError('No more items')
        self.page_index -= 1
        self.count -= 1
        return self.current_page[self.page_index]


########NEW FILE########
__FILENAME__ = error

# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

class WeibopError(Exception):
    """Weibopy exception"""

    def __init__(self, reason):
        print reason
        self.reason = reason.encode('utf-8')

    def __str__(self):
        return self.reason


########NEW FILE########
__FILENAME__ = models

# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from weibopy.utils import parse_datetime, parse_html_value, parse_a_href, \
        parse_search_datetime, unescape_html

class ResultSet(list):
    """A list like object that holds results from a Twitter API query."""


class Model(object):

    def __init__(self, api=None):
        self._api = api

    def __getstate__(self):
        # pickle
        pickle = dict(self.__dict__)
        del pickle['_api']  # do not pickle the API reference
        return pickle

    @classmethod
    def parse(cls, api, json):
        """Parse a JSON object into a model instance."""
        raise NotImplementedError

    @classmethod
    def parse_list(cls, api, json_list):
        """Parse a list of JSON objects into a result set of model instances."""
        results = ResultSet()
        for obj in json_list:
            results.append(cls.parse(api, obj))
        return results


class Status(Model):

    @classmethod
    def parse(cls, api, json):
#        print json
        status = cls(api)
        for k, v in json.items():
            if k == 'user':
                user = User.parse(api, v)
                setattr(status, 'author', user)
                setattr(status, 'user', user)  # DEPRECIATED
            elif k == 'screen_name':
                setattr(status, k, v)
            elif k == 'created_at':
                setattr(status, k, parse_datetime(v))
            elif k == 'source':
                if '<' in v:
                    setattr(status, k, parse_html_value(v))
                    setattr(status, 'source_url', parse_a_href(v))
                else:
                    setattr(status, k, v)
            elif k == 'retweeted_status':
                setattr(status, k, Status.parse(api, v))
            elif k == 'geo':
                setattr(status, k, Geo.parse(api, v))
            else:
                setattr(status, k, v)
        return status

    def destroy(self):
        return self._api.destroy_status(self.id)

    def retweet(self):
        return self._api.retweet(self.id)

    def retweets(self):
        return self._api.retweets(self.id)

    def favorite(self):
        return self._api.create_favorite(self.id)
class Geo(Model):

    @classmethod
    def parse(cls, api, json):
        geo = cls(api)
        if json is not None:
            for k, v in json.items():
                setattr(geo, k, v)
        return geo
    
class Comments(Model):

    @classmethod
    def parse(cls, api, json):
        comments = cls(api)
        for k, v in json.items():
            if k == 'user':
                user = User.parse(api, v)
                setattr(comments, 'author', user)
                setattr(comments, 'user', user)
            elif k == 'status':
                status = Status.parse(api, v)
                setattr(comments, 'user', status)
            elif k == 'created_at':
                setattr(comments, k, parse_datetime(v))
            elif k == 'reply_comment':
                setattr(comments, k, User.parse(api, v))
            else:
                setattr(comments, k, v)
        return comments

    def destroy(self):
        return self._api.destroy_status(self.id)

    def retweet(self):
        return self._api.retweet(self.id)

    def retweets(self):
        return self._api.retweets(self.id)

    def favorite(self):
        return self._api.create_favorite(self.id)

class User(Model):

    @classmethod
    def parse(cls, api, json):
        user = cls(api)
        for k, v in json.items():
            if k == 'created_at':
                setattr(user, k, parse_datetime(v))
            elif k == 'status':
                setattr(user, k, Status.parse(api, v))
            elif k == 'screen_name':
                setattr(user, k, v)
            elif k == 'following':
                # twitter sets this to null if it is false
                if v is True:
                    setattr(user, k, True)
                else:
                    setattr(user, k, False)
            else:
                setattr(user, k, v)
        return user

    @classmethod
    def parse_list(cls, api, json_list):
        if isinstance(json_list, list):
            item_list = json_list
        else:
            item_list = json_list['users']

        results = ResultSet()
        for obj in item_list:
            results.append(cls.parse(api, obj))
        return results

    def timeline(self, **kargs):
        return self._api.user_timeline(user_id=self.id, **kargs)

    def friends(self, **kargs):
        return self._api.friends(user_id=self.id, **kargs)

    def followers(self, **kargs):
        return self._api.followers(user_id=self.id, **kargs)

    def follow(self):
        self._api.create_friendship(user_id=self.id)
        self.following = True

    def unfollow(self):
        self._api.destroy_friendship(user_id=self.id)
        self.following = False

    def lists_memberships(self, *args, **kargs):
        return self._api.lists_memberships(user=self.screen_name, *args, **kargs)

    def lists_subscriptions(self, *args, **kargs):
        return self._api.lists_subscriptions(user=self.screen_name, *args, **kargs)

    def lists(self, *args, **kargs):
        return self._api.lists(user=self.screen_name, *args, **kargs)

    def followers_ids(self, *args, **kargs):
        return self._api.followers_ids(user_id=self.id, *args, **kargs)




class DirectMessage(Model):
    @classmethod
    def parse(cls, api, json):
        dm = cls(api)
        for k, v in json.items():
            if k == 'sender' or k == 'recipient':
                setattr(dm, k, User.parse(api, v))
            elif k == 'created_at':
                setattr(dm, k, parse_datetime(v))
            else:
                setattr(dm, k, v)
        return dm

class Friendship(Model):

    @classmethod
    def parse(cls, api, json):
       
        source = cls(api)
        for k, v in json['source'].items():
            setattr(source, k, v)

        # parse target
        target = cls(api)
        for k, v in json['target'].items():
            setattr(target, k, v)

        return source, target


class SavedSearch(Model):

    @classmethod
    def parse(cls, api, json):
        ss = cls(api)
        for k, v in json.items():
            if k == 'created_at':
                setattr(ss, k, parse_datetime(v))
            else:
                setattr(ss, k, v)
        return ss

    def destroy(self):
        return self._api.destroy_saved_search(self.id)


class SearchResult(Model):

    @classmethod
    def parse(cls, api, json):
        result = cls()
        for k, v in json.items():
            if k == 'created_at':
                setattr(result, k, parse_search_datetime(v))
            elif k == 'source':
                setattr(result, k, parse_html_value(unescape_html(v)))
            else:
                setattr(result, k, v)
        return result

    @classmethod
    def parse_list(cls, api, json_list, result_set=None):
        results = ResultSet()
        results.max_id = json_list.get('max_id')
        results.since_id = json_list.get('since_id')
        results.refresh_url = json_list.get('refresh_url')
        results.next_page = json_list.get('next_page')
        results.results_per_page = json_list.get('results_per_page')
        results.page = json_list.get('page')
        results.completed_in = json_list.get('completed_in')
        results.query = json_list.get('query')

        for obj in json_list['results']:
            results.append(cls.parse(api, obj))
        return results

class List(Model):

    @classmethod
    def parse(cls, api, json):
        lst = List(api)
        for k,v in json.items():
            if k == 'user':
                setattr(lst, k, User.parse(api, v))
            else:
                setattr(lst, k, v)
        return lst

    @classmethod
    def parse_list(cls, api, json_list, result_set=None):
        results = ResultSet()
        for obj in json_list['lists']:
            results.append(cls.parse(api, obj))
        return results

    def update(self, **kargs):
        return self._api.update_list(self.slug, **kargs)

    def destroy(self):
        return self._api.destroy_list(self.slug)

    def timeline(self, **kargs):
        return self._api.list_timeline(self.user.screen_name, self.slug, **kargs)

    def add_member(self, id):
        return self._api.add_list_member(self.slug, id)

    def remove_member(self, id):
        return self._api.remove_list_member(self.slug, id)

    def members(self, **kargs):
        return self._api.list_members(self.user.screen_name, self.slug, **kargs)

    def is_member(self, id):
        return self._api.is_list_member(self.user.screen_name, self.slug, id)

    def subscribe(self):
        return self._api.subscribe_list(self.user.screen_name, self.slug)

    def unsubscribe(self):
        return self._api.unsubscribe_list(self.user.screen_name, self.slug)

    def subscribers(self, **kargs):
        return self._api.list_subscribers(self.user.screen_name, self.slug, **kargs)

    def is_subscribed(self, id):
        return self._api.is_subscribed_list(self.user.screen_name, self.slug, id)

class JSONModel(Model):

    @classmethod
    def parse(cls, api, json):
        lst = JSONModel(api)
        for k,v in json.items():
            setattr(lst, k, v)
        return lst

class IDSModel(Model):
    @classmethod
    def parse(cls, api, json):
        ids = IDSModel(api)
        for k, v in json.items():            
            setattr(ids, k, v)
        return ids
    
class Counts(Model):
    @classmethod
    def parse(cls, api, json):
        ids = Counts(api)
        for k, v in json.items():            
            setattr(ids, k, v)
        return ids
class Trends(Model):
    @classmethod
    def parse(cls, api, json):
        ids = Trends(api)
        for k,v in json.items():
            setattr(ids, k , v)
        return ids
class Tags(Model):
    @classmethod
    def parse(cls, api, json):
        ts = Tags(api)
        for k,v in json.items():
            setattr(ts, k , v)
            #setattr(ts,"id",k)
        return ts   
                         
    
class ModelFactory(object):
    """
    Used by parsers for creating instances
    of models. You may subclass this factory
    to add your own extended models.
    """

    status = Status
    comments = Comments
    user = User
    direct_message = DirectMessage
    friendship = Friendship
    saved_search = SavedSearch
    search_result = SearchResult
    list = List
    json = JSONModel
    ids_list = IDSModel
    counts = Counts
    trends = Trends
    tags = Tags

########NEW FILE########
__FILENAME__ = oauth
"""
The MIT License

Copyright (c) 2007 Leah Culver

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import cgi
import urllib
import time
import random
import urlparse
import hmac
import binascii


VERSION = '1.0' # Hi Blaine!
HTTP_METHOD = 'GET'
SIGNATURE_METHOD = 'PLAINTEXT'


class OAuthError(RuntimeError):
    """Generic exception class."""
    def __init__(self, message='OAuth error occured.'):
        self.message = message

def build_authenticate_header(realm=''):
    """Optional WWW-Authenticate header (401 error)"""
    return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

def escape(s):
    """Escape a URL including any /."""
    return urllib.quote(s, safe='~')

def _utf8_str(s):
    """Convert unicode to utf-8."""
    if isinstance(s, unicode):
        return s.encode("utf-8")
    else:
        return str(s)

def generate_timestamp():
    """Get seconds since epoch (UTC)."""
    return int(time.time())

def generate_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])

def generate_verifier(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


class OAuthConsumer(object):
    """Consumer of OAuth authentication.

    OAuthConsumer is a data type that represents the identity of the Consumer
    via its shared secret with the Service Provider.

    """
    key = None
    secret = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret


class OAuthToken(object):
    """OAuthToken is a data type that represents an End User via either an access
    or request token.
    
    key -- the token
    secret -- the token secret

    """
    key = None
    secret = None
    callback = None
    callback_confirmed = None
    verifier = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

    def set_callback(self, callback):
        self.callback = callback
        self.callback_confirmed = 'true'

    def set_verifier(self, verifier=None):
        if verifier is not None:
            self.verifier = verifier
        else:
            self.verifier = generate_verifier()

    def get_callback_url(self):
        if self.callback and self.verifier:
            # Append the oauth_verifier.
            parts = urlparse.urlparse(self.callback)
            scheme, netloc, path, params, query, fragment = parts[:6]
            if query:
                query = '%s&oauth_verifier=%s' % (query, self.verifier)
            else:
                query = 'oauth_verifier=%s' % self.verifier
            return urlparse.urlunparse((scheme, netloc, path, params,
                query, fragment))
        return self.callback

    def to_string(self):
        data = {
            'oauth_token': self.key,
            'oauth_token_secret': self.secret,
        }
        if self.callback_confirmed is not None:
            data['oauth_callback_confirmed'] = self.callback_confirmed
        return urllib.urlencode(data)
 
    def from_string(s):
        """ Returns a token from something like:
        oauth_token_secret=xxx&oauth_token=xxx
        """
        params = cgi.parse_qs(s, keep_blank_values=False)
        key = params['oauth_token'][0]
        secret = params['oauth_token_secret'][0]
        token = OAuthToken(key, secret)
        try:
            token.callback_confirmed = params['oauth_callback_confirmed'][0]
        except KeyError:
            pass # 1.0, no callback confirmed.
        return token
    from_string = staticmethod(from_string)

    def __str__(self):
        return self.to_string()


class OAuthRequest(object):
    """OAuthRequest represents the request and can be serialized.

    OAuth parameters:
        - oauth_consumer_key 
        - oauth_token
        - oauth_signature_method
        - oauth_signature 
        - oauth_timestamp 
        - oauth_nonce
        - oauth_version
        - oauth_verifier
        ... any additional parameters, as defined by the Service Provider.
    """
    parameters = None # OAuth parameters.
    http_method = HTTP_METHOD
    http_url = None
    version = VERSION

    def __init__(self, http_method=HTTP_METHOD, http_url=None, parameters=None):
        self.http_method = http_method
        self.http_url = http_url
        self.parameters = parameters or {}
    def set_parameter(self, parameter, value):
        self.parameters[parameter] = value

    def get_parameter(self, parameter):
        try:
            return self.parameters[parameter]
        except:
            raise OAuthError('Parameter not found: %s' % parameter)

    def _get_timestamp_nonce(self):
        return self.get_parameter('oauth_timestamp'), self.get_parameter(
            'oauth_nonce')

    def get_nonoauth_parameters(self):
        """Get any non-OAuth parameters."""
        parameters = {}
        for k, v in self.parameters.iteritems():
            # Ignore oauth parameters.
            if k.find('oauth_') < 0:
                parameters[k] = v
        return parameters

    def to_header(self, realm=''):
        """Serialize as a header for an HTTPAuth request."""
        auth_header = 'OAuth realm="%s"' % realm
        # Add the oauth parameters.
        if self.parameters:
            for k, v in self.parameters.iteritems():
                if k[:6] == 'oauth_':
                    auth_header += ', %s="%s"' % (k, escape(str(v)))
        return {'Authorization': auth_header}

    def to_postdata(self):
        """Serialize as post data for a POST request."""
        return '&'.join(['%s=%s' % (escape(str(k)), escape(str(v))) \
            for k, v in self.parameters.iteritems()])

    def to_url(self):
        """Serialize as a URL for a GET request."""
        return '%s?%s' % (self.get_normalized_http_url(), self.to_postdata())

    def get_normalized_parameters(self):
        """Return a string that contains the parameters that must be signed."""
        params = self.parameters
        try:
            # Exclude the signature if it exists.
            del params['oauth_signature']
        except:
            pass
        # Escape key values before sorting.
        key_values = [(escape(_utf8_str(k)), escape(_utf8_str(v))) \
            for k,v in params.items()]
        # Sort lexicographically, first after key, then after value.
        key_values.sort()
        # Combine key value pairs into a string.
        return '&'.join(['%s=%s' % (k, v) for k, v in key_values])

    def get_normalized_http_method(self):
        """Uppercases the http method."""
        return self.http_method.upper()

    def get_normalized_http_url(self):
        """Parses the URL and rebuilds it to be scheme://host/path."""
        parts = urlparse.urlparse(self.http_url)
        scheme, netloc, path = parts[:3]
        # Exclude default port numbers.
        if scheme == 'http' and netloc[-3:] == ':80':
            netloc = netloc[:-3]
        elif scheme == 'https' and netloc[-4:] == ':443':
            netloc = netloc[:-4]
        return '%s://%s%s' % (scheme, netloc, path)

    def sign_request(self, signature_method, consumer, token):
        """Set the signature parameter to the result of build_signature."""
        # Set the signature method.
        self.set_parameter('oauth_signature_method',
            signature_method.get_name())
        # Set the signature.
        self.set_parameter('oauth_signature',self.build_signature(signature_method, consumer, token))

    def build_signature(self, signature_method, consumer, token):
        """Calls the build signature method within the signature method."""
        return signature_method.build_signature(self, consumer, token)

    def from_request(http_method, http_url, headers=None, parameters=None,
            query_string=None):
        """Combines multiple parameter sources."""
        if parameters is None:
            parameters = {}

        # Headers
        if headers and 'Authorization' in headers:
            auth_header = headers['Authorization']
            # Check that the authorization header is OAuth.
            if auth_header[:6] == 'OAuth ':
                auth_header = auth_header[6:]
                try:
                    # Get the parameters from the header.
                    header_params = OAuthRequest._split_header(auth_header)
                    parameters.update(header_params)
                except:
                    raise OAuthError('Unable to parse OAuth parameters from '
                        'Authorization header.')

        # GET or POST query string.
        if query_string:
            query_params = OAuthRequest._split_url_string(query_string)
            parameters.update(query_params)

        # URL parameters.
        param_str = urlparse.urlparse(http_url)[4] # query
        url_params = OAuthRequest._split_url_string(param_str)
        parameters.update(url_params)

        if parameters:
            return OAuthRequest(http_method, http_url, parameters)

        return None
    from_request = staticmethod(from_request)

    def from_consumer_and_token(oauth_consumer, token=None,
            callback=None, verifier=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        defaults = {
            'oauth_consumer_key': oauth_consumer.key,
            'oauth_timestamp': generate_timestamp(),
            'oauth_nonce': generate_nonce(),
            'oauth_version': OAuthRequest.version,
        }

        defaults.update(parameters)
        parameters = defaults

        if token:
            parameters['oauth_token'] = token.key
            if token.callback:
                parameters['oauth_callback'] = token.callback
            # 1.0a support for verifier.
            if verifier:
                parameters['oauth_verifier'] = verifier
        elif callback:
            # 1.0a support for callback in the request token request.
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_consumer_and_token = staticmethod(from_consumer_and_token)

    def from_token_and_callback(token, callback=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        parameters['oauth_token'] = token.key

        if callback:
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_token_and_callback = staticmethod(from_token_and_callback)

    def _split_header(header):
        """Turn Authorization: header into parameters."""
        params = {}
        parts = header.split(',')
        for param in parts:
            # Ignore realm parameter.
            if param.find('realm') > -1:
                continue
            # Remove whitespace.
            param = param.strip()
            # Split key-value.
            param_parts = param.split('=', 1)
            # Remove quotes and unescape the value.
            params[param_parts[0]] = urllib.unquote(param_parts[1].strip('\"'))
        return params
    _split_header = staticmethod(_split_header)

    def _split_url_string(param_str):
        """Turn URL string into parameters."""
        parameters = cgi.parse_qs(param_str, keep_blank_values=False)
        for k, v in parameters.iteritems():
            parameters[k] = urllib.unquote(v[0])
        return parameters
    _split_url_string = staticmethod(_split_url_string)

class OAuthServer(object):
    """A worker to check the validity of a request against a data store."""
    timestamp_threshold = 300 # In seconds, five minutes.
    version = VERSION
    signature_methods = None
    data_store = None

    def __init__(self, data_store=None, signature_methods=None):
        self.data_store = data_store
        self.signature_methods = signature_methods or {}

    def set_data_store(self, data_store):
        self.data_store = data_store

    def get_data_store(self):
        return self.data_store

    def add_signature_method(self, signature_method):
        self.signature_methods[signature_method.get_name()] = signature_method
        return self.signature_methods

    def fetch_request_token(self, oauth_request):
        """Processes a request_token request and returns the
        request token on success.
        """
        try:
            # Get the request token for authorization.
            token = self._get_token(oauth_request, 'request')
        except OAuthError:
            # No token required for the initial token request.
            version = self._get_version(oauth_request)
            consumer = self._get_consumer(oauth_request)
            try:
                callback = self.get_callback(oauth_request)
            except OAuthError:
                callback = None # 1.0, no callback specified.
            self._check_signature(oauth_request, consumer, None)
            # Fetch a new token.
            token = self.data_store.fetch_request_token(consumer, callback)
        return token

    def fetch_access_token(self, oauth_request):
        """Processes an access_token request and returns the
        access token on success.
        """
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        try:
            verifier = self._get_verifier(oauth_request)
        except OAuthError:
            verifier = None
        # Get the request token.
        token = self._get_token(oauth_request, 'request')
        self._check_signature(oauth_request, consumer, token)
        new_token = self.data_store.fetch_access_token(consumer, token, verifier)
        return new_token

    def verify_request(self, oauth_request):
        """Verifies an api call and checks all the parameters."""
        # -> consumer and token
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        # Get the access token.
        token = self._get_token(oauth_request, 'access')
        self._check_signature(oauth_request, consumer, token)
        parameters = oauth_request.get_nonoauth_parameters()
        return consumer, token, parameters

    def authorize_token(self, token, user):
        """Authorize a request token."""
        return self.data_store.authorize_request_token(token, user)

    def get_callback(self, oauth_request):
        """Get the callback URL."""
        return oauth_request.get_parameter('oauth_callback')
 
    def build_authenticate_header(self, realm=''):
        """Optional support for the authenticate header."""
        return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

    def _get_version(self, oauth_request):
        """Verify the correct version request for this server."""
        try:
            version = oauth_request.get_parameter('oauth_version')
        except:
            version = VERSION
        if version and version != self.version:
            raise OAuthError('OAuth version %s not supported.' % str(version))
        return version

    def _get_signature_method(self, oauth_request):
        """Figure out the signature with some defaults."""
        try:
            signature_method = oauth_request.get_parameter(
                'oauth_signature_method')
        except:
            signature_method = SIGNATURE_METHOD
        try:
            # Get the signature method object.
            signature_method = self.signature_methods[signature_method]
        except:
            signature_method_names = ', '.join(self.signature_methods.keys())
            raise OAuthError('Signature method %s not supported try one of the '
                'following: %s' % (signature_method, signature_method_names))

        return signature_method

    def _get_consumer(self, oauth_request):
        consumer_key = oauth_request.get_parameter('oauth_consumer_key')
        consumer = self.data_store.lookup_consumer(consumer_key)
        if not consumer:
            raise OAuthError('Invalid consumer.')
        return consumer

    def _get_token(self, oauth_request, token_type='access'):
        """Try to find the token for the provided request token key."""
        token_field = oauth_request.get_parameter('oauth_token')
        token = self.data_store.lookup_token(token_type, token_field)
        if not token:
            raise OAuthError('Invalid %s token: %s' % (token_type, token_field))
        return token
    
    def _get_verifier(self, oauth_request):
        return oauth_request.get_parameter('oauth_verifier')

    def _check_signature(self, oauth_request, consumer, token):
        timestamp, nonce = oauth_request._get_timestamp_nonce()
        self._check_timestamp(timestamp)
        self._check_nonce(consumer, token, nonce)
        signature_method = self._get_signature_method(oauth_request)
        try:
            signature = oauth_request.get_parameter('oauth_signature')
        except:
            raise OAuthError('Missing signature.')
        # Validate the signature.
        valid_sig = signature_method.check_signature(oauth_request, consumer,
            token, signature)
        if not valid_sig:
            key, base = signature_method.build_signature_base_string(
                oauth_request, consumer, token)
            raise OAuthError('Invalid signature. Expected signature base '
                'string: %s' % base)
        built = signature_method.build_signature(oauth_request, consumer, token)

    def _check_timestamp(self, timestamp):
        """Verify that timestamp is recentish."""
        timestamp = int(timestamp)
        now = int(time.time())
        lapsed = abs(now - timestamp)
        if lapsed > self.timestamp_threshold:
            raise OAuthError('Expired timestamp: given %d and now %s has a '
                'greater difference than threshold %d' %
                (timestamp, now, self.timestamp_threshold))

    def _check_nonce(self, consumer, token, nonce):
        """Verify that the nonce is uniqueish."""
        nonce = self.data_store.lookup_nonce(consumer, token, nonce)
        if nonce:
            raise OAuthError('Nonce already used: %s' % str(nonce))


class OAuthClient(object):
    """OAuthClient is a worker to attempt to execute a request."""
    consumer = None
    token = None

    def __init__(self, oauth_consumer, oauth_token):
        self.consumer = oauth_consumer
        self.token = oauth_token

    def get_consumer(self):
        return self.consumer

    def get_token(self):
        return self.token

    def fetch_request_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def access_resource(self, oauth_request):
        """-> Some protected resource."""
        raise NotImplementedError


class OAuthDataStore(object):
    """A database abstraction used to lookup consumers and tokens."""

    def lookup_consumer(self, key):
        """-> OAuthConsumer."""
        raise NotImplementedError

    def lookup_token(self, oauth_consumer, token_type, token_token):
        """-> OAuthToken."""
        raise NotImplementedError

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_request_token(self, oauth_consumer, oauth_callback):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_consumer, oauth_token, oauth_verifier):
        """-> OAuthToken."""
        raise NotImplementedError

    def authorize_request_token(self, oauth_token, user):
        """-> OAuthToken."""
        raise NotImplementedError


class OAuthSignatureMethod(object):
    """A strategy class that implements a signature method."""
    def get_name(self):
        """-> str."""
        raise NotImplementedError

    def build_signature_base_string(self, oauth_request, oauth_consumer, oauth_token):
        """-> str key, str raw."""
        raise NotImplementedError

    def build_signature(self, oauth_request, oauth_consumer, oauth_token):
        """-> str."""
        raise NotImplementedError

    def check_signature(self, oauth_request, consumer, token, signature):
        built = self.build_signature(oauth_request, consumer, token)
        return built == signature


class OAuthSignatureMethod_HMAC_SHA1(OAuthSignatureMethod):

    def get_name(self):
        return 'HMAC-SHA1'
        
    def build_signature_base_string(self, oauth_request, consumer, token):
        sig = (
            escape(oauth_request.get_normalized_http_method()),
            escape(oauth_request.get_normalized_http_url()),
            escape(oauth_request.get_normalized_parameters()),
        )

        key = '%s&' % escape(consumer.secret)
        if token:
            key += escape(token.secret)
        #print "OAuth base string:" + str(sig)
        raw = '&'.join(sig)
        return key, raw

    def build_signature(self, oauth_request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)

        # HMAC object.
        try:
            import hashlib # 2.5
            hashed = hmac.new(key, raw, hashlib.sha1)
        except:
            import sha # Deprecated
            hashed = hmac.new(key, raw, sha)

        # Calculate the digest base 64.
        return binascii.b2a_base64(hashed.digest())[:-1]


class OAuthSignatureMethod_PLAINTEXT(OAuthSignatureMethod):

    def get_name(self):
        return 'PLAINTEXT'

    def build_signature_base_string(self, oauth_request, consumer, token):
        """Concatenates the consumer key and secret."""
        sig = '%s&' % escape(consumer.secret)
        if token:
            sig = sig + escape(token.secret)
        return sig, sig

    def build_signature(self, oauth_request, consumer, token):
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)
        return key
########NEW FILE########
__FILENAME__ = parsers

# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from weibopy.models import ModelFactory
from weibopy.utils import import_simplejson
from weibopy.error import WeibopError

class Parser(object):

    def parse(self, method, payload):
        """
        Parse the response payload and return the result.
        Returns a tuple that contains the result data and the cursors
        (or None if not present).
        """
        raise NotImplementedError

    def parse_error(self, method, payload):
        """
        Parse the error message from payload.
        If unable to parse the message, throw an exception
        and default error message will be used.
        """
        raise NotImplementedError


class JSONParser(Parser):

    payload_format = 'json'

    def __init__(self):
        self.json_lib = import_simplejson()

    def parse(self, method, payload):
        try:
            json = self.json_lib.loads(payload)
        except Exception, e:
            print "Failed to parse JSON payload:"+ str(payload)
            raise WeibopError('Failed to parse JSON payload: %s' % e)

        #if isinstance(json, dict) and 'previous_cursor' in json and 'next_cursor' in json:
        #    cursors = json['previous_cursor'], json['next_cursor']
        #    return json, cursors
        #else:
        return json

    def parse_error(self, method, payload):
        return self.json_lib.loads(payload)


class ModelParser(JSONParser):

    def __init__(self, model_factory=None):
        JSONParser.__init__(self)
        self.model_factory = model_factory or ModelFactory

    def parse(self, method, payload):
        try:
            if method.payload_type is None: return
            model = getattr(self.model_factory, method.payload_type)
        except AttributeError:
            raise WeibopError('No model for this payload type: %s' % method.payload_type)

        json = JSONParser.parse(self, method, payload)
        if isinstance(json, tuple):
            json, cursors = json
        else:
            cursors = None

        if method.payload_list:
            result = model.parse_list(method.api, json)
        else:
            result = model.parse(method.api, json)
        if cursors:
            return result, cursors
        else:
            return result


########NEW FILE########
__FILENAME__ = streaming

# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import httplib
from socket import timeout
from threading import Thread
from time import sleep
import urllib

from weibopy.auth import BasicAuthHandler
from weibopy.models import Status
from weibopy.api import API
from weibopy.error import WeibopError

from weibopy.utils import import_simplejson
json = import_simplejson()

STREAM_VERSION = 1


class StreamListener(object):

    def __init__(self, api=None):
        self.api = api or API()

    def on_data(self, data):
        """Called when raw data is received from connection.

        Override this method if you wish to manually handle
        the stream data. Return False to stop stream and close connection.
        """

        if 'in_reply_to_status_id' in data:
            status = Status.parse(self.api, json.loads(data))
            if self.on_status(status) is False:
                return False
        elif 'delete' in data:
            delete = json.loads(data)['delete']['status']
            if self.on_delete(delete['id'], delete['user_id']) is False:
                return False
        elif 'limit' in data:
            if self.on_limit(json.loads(data)['limit']['track']) is False:
                return False

    def on_status(self, status):
        """Called when a new status arrives"""
        return

    def on_delete(self, status_id, user_id):
        """Called when a delete notice arrives for a status"""
        return

    def on_limit(self, track):
        """Called when a limitation notice arrvies"""
        return

    def on_error(self, status_code):
        """Called when a non-200 status code is returned"""
        return False

    def on_timeout(self):
        """Called when stream connection times out"""
        return


class Stream(object):

    host = 'stream.twitter.com'

    def __init__(self, username, password, listener, timeout=5.0, retry_count = None,
                    retry_time = 10.0, snooze_time = 5.0, buffer_size=1500, headers=None):
        self.auth = BasicAuthHandler(username, password)
        self.running = False
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_time = retry_time
        self.snooze_time = snooze_time
        self.buffer_size = buffer_size
        self.listener = listener
        self.api = API()
        self.headers = headers or {}
        self.body = None

    def _run(self):
        # setup
        self.auth.apply_auth(None, None, self.headers, None)

        # enter loop
        error_counter = 0
        conn = None
        while self.running:
            if self.retry_count and error_counter > self.retry_count:
                # quit if error count greater than retry count
                break
            try:
                conn = httplib.HTTPConnection(self.host)
                conn.connect()
                conn.sock.settimeout(self.timeout)
                conn.request('POST', self.url, self.body, headers=self.headers)
                resp = conn.getresponse()
                if resp.status != 200:
                    if self.listener.on_error(resp.status) is False:
                        break
                    error_counter += 1
                    sleep(self.retry_time)
                else:
                    error_counter = 0
                    self._read_loop(resp)
            except timeout:
                if self.listener.on_timeout() == False:
                    break
                if self.running is False:
                    break
                conn.close()
                sleep(self.snooze_time)
            except Exception:
                # any other exception is fatal, so kill loop
                break

        # cleanup
        self.running = False
        if conn:
            conn.close()

    def _read_loop(self, resp):
        data = ''
        while self.running:
            if resp.isclosed():
                break

            # read length
            length = ''
            while True:
                c = resp.read(1)
                if c == '\n':
                    break
                length += c
            length = length.strip()
            if length.isdigit():
                length = int(length)
            else:
                continue

            # read data and pass into listener
            data = resp.read(length)
            if self.listener.on_data(data) is False:
                self.running = False

    def _start(self, async):
        self.running = True
        if async:
            Thread(target=self._run).start()
        else:
            self._run()

    def firehose(self, count=None, async=False):
        if self.running:
            raise WeibopError('Stream object already connected!')
        self.url = '/%i/statuses/firehose.json?delimited=length' % STREAM_VERSION
        if count:
            self.url += '&count=%s' % count
        self._start(async)

    def retweet(self, async=False):
        if self.running:
            raise WeibopError('Stream object already connected!')
        self.url = '/%i/statuses/retweet.json?delimited=length' % STREAM_VERSION
        self._start(async)

    def sample(self, count=None, async=False):
        if self.running:
            raise WeibopError('Stream object already connected!')
        self.url = '/%i/statuses/sample.json?delimited=length' % STREAM_VERSION
        if count:
            self.url += '&count=%s' % count
        self._start(async)

    def filter(self, follow=None, track=None, async=False):
        params = {}
        self.headers['Content-type'] = "application/x-www-form-urlencoded"
        if self.running:
            raise WeibopError('Stream object already connected!')
        self.url = '/%i/statuses/filter.json?delimited=length' % STREAM_VERSION
        if follow:
            params['follow'] = ','.join(map(str, follow))
        if track:
            params['track'] = ','.join(map(str, track))
        self.body = urllib.urlencode(params)
        self._start(async)

    def disconnect(self):
        if self.running is False:
            return
        self.running = False


########NEW FILE########
__FILENAME__ = utils

# Copyright 2010 Joshua Roesslein
# See LICENSE for details.

from datetime import datetime
import time
import htmlentitydefs
import re


def parse_datetime(str):

    # We must parse datetime this way to work in python 2.4
    if  str:
        return datetime(*(time.strptime(str, '%a %b %d %H:%M:%S +0800 %Y')[0:6]))   
    else:
        print "time blank"
        return ""


def parse_html_value(html):

    return html[html.find('>')+1:html.rfind('<')]


def parse_a_href(atag):

    start = atag.find('"') + 1
    end = atag.find('"', start)
    return atag[start:end]


def parse_search_datetime(str):

    # python 2.4
    return datetime(*(time.strptime(str, '%a, %d %b %Y %H:%M:%S +0000')[0:6]))


def unescape_html(text):
    """Created by Fredrik Lundh (http://effbot.org/zone/re-sub.htm#unescape-html)"""
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)


def convert_to_utf8_str(arg):
    # written by Michael Norton (http://docondev.blogspot.com/)
    if isinstance(arg, unicode):
        arg = arg.encode('utf-8')
    elif not isinstance(arg, str):
        arg = str(arg)
    return arg



def import_simplejson():
    try:
        import simplejson as json
    except ImportError:
        try:
            import json  # Python 2.6+
        except ImportError:
            try:
                from django.utils import simplejson as json  # Google App Engine
            except ImportError:
                raise ImportError, "Can't load a json library"

    return json


########NEW FILE########
