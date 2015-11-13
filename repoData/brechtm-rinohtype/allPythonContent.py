__FILENAME__ = rst

import rinoh as rt

from rinoh.dimension import PT, CM, INCH
from rinoh.backend import pdf
from rinoh.frontend.rst import ReStructuredTextParser


#from rinohlib.stylesheets.rinascimento import styles as ieee_styles
from rinohlib.stylesheets.ieee import styles as ieee_styles


styles = rt.StyleSheet('IEEE for rST', base=ieee_styles)
styles['body'] = rt.ParagraphStyle(base=ieee_styles['body'],
                                   indent_first=0,
                                   space_below=6*PT)
styles('line block line', rt.ClassSelector(rt.Paragraph, 'line block line'),
       base='body',
       space_below=0*PT)


# page definition
# ----------------------------------------------------------------------------

class SimplePage(rt.Page):
    topmargin = bottommargin = 2*CM
    leftmargin = rightmargin = 2*CM

    def __init__(self, document):
        super().__init__(document, rt.A5, rt.PORTRAIT)

        body_width = self.width - (self.leftmargin + self.rightmargin)
        body_height = self.height - (self.topmargin + self.bottommargin)
        self.body = rt.Container('body', self, self.leftmargin, self.topmargin,
                                 body_width, body_height)

        self.footnote_space = rt.FootnoteContainer('footnotes', self.body, 0*PT,
                                                   body_height)
        self._footnote_number = 0

        self.content = rt.Container('content', self.body, 0*PT, 0*PT,
                                    bottom=self.footnote_space.top,
                                    chain=document.content)

        self.content._footnote_space = self.footnote_space
##
##        self.header = rt.Container(self, self.leftmargin, self.topmargin / 2,
##                                   body_width, 12*PT)
##        footer_vert_pos = self.topmargin + body_height + self.bottommargin /2
##        self.footer = rt.Container(self, self.leftmargin, footer_vert_pos,
##                                   body_width, 12*PT)
##        header_text = Header(header_style)
##        self.header.append_flowable(header_text)
##        footer_text = Footer(footer_style)
##        self.footer.append_flowable(footer_text)


# main document
# ----------------------------------------------------------------------------
class ReStructuredTextDocument(rt.Document):
    def __init__(self, filename):
        self.styles = styles
        parser = ReStructuredTextParser()
        self.root = parser.parse(filename)
        super().__init__(backend=pdf, title=self.root.get('title'))
        self.content = rt.Chain(self)
        self.parse_input()

    def parse_input(self):
##        toc = TableOfContents(style=toc_style, styles=toc_levels)
        for child in self.root.getchildren():
##            toc.register(flowable)
            self.content << child.flowable()
##        try:
##            for flowable in self.root.body.acknowledgement.parse(self):
##                toc.register(flowable)
##                self.content_flowables.append(flowable)
##        except AttributeError:
##            pass

    def setup(self):
        self.page_count = 1
        page = SimplePage(self)
        self.add_page(page, self.page_count)
##        bib = self.bibliography.bibliography()
##        self.content.append_flowable(bib)

    def new_page(self, chains):
        page = SimplePage(self)
        self.page_count += 1
        self.add_page(page, self.page_count)
        return page.content

########NEW FILE########
__FILENAME__ = test

from rst import ReStructuredTextDocument


if __name__ == '__main__':
    for name in ('FAQ', ):
        document = ReStructuredTextDocument(name + '.txt')
        document.render(name)

########NEW FILE########
__FILENAME__ = rfic2009style

import rinoh as rt

from rinoh.dimension import PT, INCH
from rinoh.font.style import BOLD
from rinoh.paper import LETTER
from rinoh.document import Document, Page, PORTRAIT
from rinoh.layout import Container, DownExpandingContainer, Chain
from rinoh.layout import TopFloatContainer, FootnoteContainer
from rinoh.paragraph import Paragraph, LEFT, BOTH
from rinoh.paragraph import FixedSpacing, TabStop
from rinoh.text import SingleStyledText, MixedStyledText
from rinoh.text import Bold, Emphasized, SmallCaps, Superscript, Subscript
from rinoh.text import BOLD_ITALIC_STYLE
from rinoh.text import Tab as RinohTab
from rinoh.structure import Heading, List, Header, Footer
from rinoh.structure import TableOfContents
from rinoh.reference import Field, Reference, REFERENCE
from rinoh.reference import Note, NoteMarkerWithNote
from rinoh.flowable import GroupedFlowables, StaticGroupedFlowables, Float
from rinoh.float import Figure as RinohFigure
from rinoh.table import Tabular as RinohTabular
from rinoh.table import HTMLTabularData, CSVTabularData
from rinoh.style import ClassSelector, ContextSelector
from rinoh.frontend.xml import element_factory
from rinoh.backend import pdf

import rinoh.frontend.xml.elementtree as xml_frontend

from citeproc import CitationStylesStyle, CitationStylesBibliography
from citeproc import Citation, CitationItem
from rinoh import csl_formatter

from rinohlib.stylesheets.ieee import styles

# pre-load hyphenation dictionary (which otherwise occurs during page rendering,
# and thus invalidates per-page render time)
from rinoh.paragraph import HYPHENATORS
HYPHENATORS[(styles['body'].hyphen_lang, styles['body'].hyphen_chars)]

# styles['math'] = MathStyle(fonts=mathfonts)
#
# styles['equation'] = EquationStyle(base='body',
#                                    math_style='math',
#                                    indent_first=0*PT,
#                                    space_above=6*PT,
#                                    space_below=6*PT,
#                                    justify=CENTER,
#                                    tab_stops=[TabStop(0.5, CENTER),
#                                               TabStop(1.0, RIGHT)])

# custom paragraphs
# ----------------------------------------------------------------------------

class Abstract(Paragraph):
    def __init__(self, text):
        label = SingleStyledText("Abstract \N{EM DASH} ", BOLD_ITALIC_STYLE)
        return super().__init__(label + text)


class IndexTerms(Paragraph):
    def __init__(self, terms):
        label = SingleStyledText("Index Terms \N{EM DASH} ", BOLD_ITALIC_STYLE)
        text = ", ".join(sorted(terms)) + "."
        text = text.capitalize()
        return super().__init__(label + text)


styles('abstract', ClassSelector(Abstract),
       base='body',
       font_weight=BOLD,
       font_size=9*PT,
       line_spacing=FixedSpacing(10*PT),
       indent_first=0.125*INCH,
       space_above=0*PT,
       space_below=0*PT,
       justify=BOTH)

styles('index terms', ClassSelector(IndexTerms),
       base='abstract')


# input parsing
# ----------------------------------------------------------------------------

CustomElement, NestedElement = element_factory(xml_frontend)


class Section(CustomElement):
    def parse(self):
        flowables = []
        for element in self.getchildren():
            flowable = element.process()
            flowables.append(flowable)
        return rt.Section(flowables, id=self.get('id', None))


class Title(NestedElement):
    def parse(self):
        return Heading(self.process_content())


class P(NestedElement):
    def parse(self):
        return Paragraph(self.process_content())


class B(NestedElement):
    def parse(self):
        return Bold(self.process_content())


class Em(NestedElement):
    def parse(self):
        return Emphasized(self.process_content())


class SC(NestedElement):
    def parse(self):
        return SmallCaps(self.process_content())


class Sup(NestedElement):
    def parse(self):
        return Superscript(self.process_content())


class Sub(NestedElement):
    def parse(self):
        return Subscript(self.process_content())


class Tab(CustomElement):
    def parse(self):
        return MixedStyledText([RinohTab()])


class OL(CustomElement):
    def parse(self):
        return List([li.process() for li in self.li], style='enumerated')


class LI(CustomElement):
    def parse(self):
        return [item.process() for item in self.getchildren()]


# class Math(CustomElement):
#     def parse(self):
#         return RinohMath(self.text, style='math')
#
#
# class Eq(CustomElement):
#     def parse(self, id=None):
#         equation = Equation(self.text, style='equation')
#         id = self.get('id', None)
#         if id:
#             document.elements[id] = equation
#         return MixedStyledText([equation])


class Cite(CustomElement):
    def parse(self):
        keys = map(lambda x: x.strip(), self.get('id').split(','))
        items = [CitationItem(key) for key in keys]
        citation = Citation(items)
        return CitationField(citation)


class Ref(CustomElement):
    def parse(self):
        return Reference(self.get('id'), self.get('type', REFERENCE))


class Footnote(NestedElement):
    def parse(self):
        content = [element.parse() for element in self.getchildren()]
        note = Note(StaticGroupedFlowables(content), id=None)
        return NoteMarkerWithNote(note)


class Acknowledgement(CustomElement):
    def parse(self):
        heading = Heading('Acknowledgement', style='unnumbered')
        content = [child.process() for child in self.getchildren()]
        return rt.Section([heading] + content)


class Figure(CustomElement):
    def parse(self):
        caption_text = self.caption.process()
        scale = float(self.get('scale'))
        figure = RinohFigure(self.get('path'), caption_text, scale=scale,
                             id=self.get('id', None))
        return Float(figure)


class Caption(NestedElement):
    pass


class Tabular(CustomElement):
    def parse(self):
        data = HTMLTabularData(self)
        return RinohTabular(data)


class CSVTabular(CustomElement):
    def parse(self):
        data = CSVTabularData(self.get('path'))
        return RinohTabular(data)


# bibliography
# ----------------------------------------------------------------------------

class CitationField(Field):
    def __init__(self, citation):
        super().__init__()
        self.citation = citation

    def prepare(self, document):
        document.bibliography.register(self.citation)

    def warn_unknown_reference_id(self, item, container):
        self.warn("Unknown reference ID '{}'".format(item.key), container)

    def split(self, container):
        callback = lambda item: self.warn_unknown_reference_id(item, container)
        text = self.citation.bibliography.cite(self.citation, callback)
        return self.split_words(text)


class Bibliography(GroupedFlowables):
    location = 'bibliography'

    def __init__(self, bibliography, style=None, parent=None):
        super().__init__(style=style, parent=parent)
        self.source = self
        self.bibliography = bibliography

    def flowables(self, document):
        for entry in self.bibliography.bibliography():
            yield Paragraph(entry, parent=self)


styles('bibliography entry', ContextSelector(ClassSelector(Bibliography),
                                             ClassSelector(Paragraph)),
       base='body',  # TODO: if no base, fall back to next-best selector match?
       font_size=9*PT,
       indent_first=0*PT,
       space_above=0*PT,
       space_below=0*PT,
       tab_stops=[TabStop(0.25*INCH, LEFT)])


# pages and their layout
# ----------------------------------------------------------------------------

class RFICPage(Page):
    topmargin = bottommargin = 1.125*INCH
    leftmargin = rightmargin = 0.85*INCH
    column_spacing = 0.25*INCH

    def __init__(self, document, first=False):
        super().__init__(document, LETTER, PORTRAIT)

        body_width = self.width - (self.leftmargin + self.rightmargin)
        body_height = self.height - (self.topmargin + self.bottommargin)
        body = Container('body', self, self.leftmargin, self.topmargin,
                         body_width, body_height)

        column_width = (body.width - self.column_spacing) / 2.0
        column_top = 0*PT
        if first:
            self.title_box = DownExpandingContainer('title', body)
            column_top = self.title_box.bottom

        self.float_space = TopFloatContainer('top floats', body, top=column_top)
        column_top = self.float_space.bottom

        self.content = document.content

        self.footnote_space = FootnoteContainer('footnotes', body, 0*PT,
                                                body_height)
        self._footnote_number = 0

        self.column1 = Container('column1', body, 0*PT, column_top,
                                 width=column_width,
                                 bottom=self.footnote_space.top,
                                 chain=document.content)
        self.column2 = Container('column2', body,
                                 column_width + self.column_spacing,
                                 column_top,
                                 width=column_width,
                                 bottom=self.footnote_space.top,
                                 chain=document.content)

        self.column1._footnote_space = self.footnote_space
        self.column2._footnote_space = self.footnote_space
        self.column1.float_space = self.float_space
        self.column2.float_space = self.float_space

        self.header = Container('header', self, self.leftmargin,
                                self.topmargin / 2, body_width, 12*PT)
        footer_vert_pos = self.topmargin + body_height + self.bottommargin /2
        self.footer = Container('footer', self, self.leftmargin,
                                footer_vert_pos, body_width, 12*PT)
        header_text = Header()
        self.header.append_flowable(header_text)
        footer_text = Footer()
        self.footer.append_flowable(footer_text)


# main document
# ----------------------------------------------------------------------------
class RFIC2009Paper(Document):
    rngschema = 'rfic.rng'
    namespace = 'http://www.mos6581.org/ns/rficpaper'

    def __init__(self, filename, bibliography_source):
        self.styles = styles
        parser = xml_frontend.Parser(CustomElement, self.namespace,
                                     schema=self.rngschema)
        xml_tree = parser.parse(filename)
        self.root = xml_tree.getroot()

        title = self.root.head.title.text
        authors = [author.text for author in self.root.head.authors.author]
        if len(authors) > 1:
            author = ', '.join(authors[:-1]) + ', and ' + authors[-1]
        else:
            author = authors[0]
        self.keyword_list = [term.text
                             for term in self.root.head.indexterms.term]

        super().__init__(backend=pdf, title=title, author=author,
                         keywords=', '.join(self.keyword_list))
        bibliography_style = CitationStylesStyle('ieee.csl')
        self.bibliography = CitationStylesBibliography(bibliography_style,
                                                       bibliography_source,
                                                       csl_formatter)

        self.parse_input()

    def parse_input(self):
        self.title_par = Paragraph(self.title, style='title')
        self.author_par = Paragraph(self.author, style='author')
        self.affiliation_par = Paragraph(self.root.head.affiliation.text,
                                         style='affiliation')

        self.content = Chain(self)
        self.content << Abstract(self.root.head.abstract.text)
        self.content << IndexTerms(self.keyword_list)

        toc_heading = Heading('Table of Contents', style='unnumbered')
        toc = TableOfContents()
        self.content << rt.Section([toc_heading, toc])
        for element in self.root.body.getchildren():
            self.content << element.process()

        bib_heading = Heading('References', style='unnumbered')
        self.bibliography.sort()
        bib = Bibliography(self.bibliography)
        self.content << rt.Section([bib_heading, bib])

    def setup(self):
        self.page_count = 1
        page = RFICPage(self, first=True)
        self.add_page(page, self.page_count)

        page.title_box << self.title_par
        page.title_box << self.author_par
        page.title_box << self.affiliation_par

    def new_page(self, chains):
        page = RFICPage(self)
        self.page_count += 1
        self.add_page(page, self.page_count)

########NEW FILE########
__FILENAME__ = template
# -*- coding: utf-8 -*-

import time

before_time = time.clock()
from rfic2009style import RFIC2009Paper
from citeproc.source.bibtex import BibTeX
after_time = time.clock()
import_time = after_time - before_time
print('Module import time: {:.2f} seconds'.format(import_time))

before_time = time.clock()
bib_source = BibTeX('references.bib')
doc = RFIC2009Paper('template.xml', bib_source)
after_time = time.clock()
setup_time = after_time - before_time
print('Setup time: {:.2f} seconds'.format(setup_time))

before_time = time.clock()
doc.render('template')
after_time = time.clock()
render_time = after_time - before_time
print('Render time: {:.2f} seconds ({:.2f}s per page)'
      .format(render_time, render_time / doc.page_count))

total_time = import_time + setup_time + render_time
print('Total time: {:.2f} seconds'.format(total_time))

########NEW FILE########
__FILENAME__ = cos
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


import codecs
import hashlib, time

from binascii import hexlify
from codecs import BOM_UTF16_BE
from contextlib import contextmanager
from collections import OrderedDict
from datetime import datetime
from functools import wraps
from io import BytesIO, SEEK_END

from . import pdfdoccodec
from ... import __version__, __release_date__

PDF_VERSION = '1.6'

WHITESPACE = b'\0\t\n\f\r '
DELIMITERS = b'()<>[]{}/%'


# TODO: max line length (not streams)


class Object(object):
    PREFIX = b''
    POSTFIX = b''

    def __init__(self, indirect=False):
        self.indirect = indirect

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self._repr())

    @property
    def object(self):
        return self

    def bytes(self, document):
        if self.indirect:
            reference = document._by_object_id[id(self)]
            out = reference.bytes(document)
        else:
            out = self.direct_bytes(document)
        return out

    def direct_bytes(self, document):
        return self.PREFIX + self._bytes(document) + self.POSTFIX

    def delete(self, document):
        try:
            reference = document._by_object_id[id(self)]
            reference.delete()
        except KeyError:
            pass

    def short_repr(self):
        return repr(self)

    def register_indirect(self, document, visited=None):
        if self.indirect and id(self) not in visited:
            document.register(self)


class Reference(object):
    def __init__(self, document, identifier, generation):
        self.document = document
        self.identifier = identifier
        self.generation = generation

    @property
    def object(self):
        return self.document[self.identifier]

    def bytes(self, document):
        return '{} {} R'.format(self.identifier,
                                self.generation).encode('utf_8')

    def delete(self, document=None):
        if document == self.document:
            del self.document[self.identifier]

    def __repr__(self):
        return '{}<{} {}>'.format(self.object.__class__.__name__,
                                  self.identifier, self.generation)


class Boolean(Object):
    def __init__(self, value, indirect=False):
        super().__init__(indirect)
        self.value = value

    def _repr(self):
        return self.value

    def _bytes(self, document):
        return b'true' if self.value else b'false'


class Integer(Object, int):
    def __new__(cls, value, base=10, indirect=False):
        try:
            obj = int.__new__(cls, value, base)
        except TypeError:
            obj = int.__new__(cls, value)
        return obj

    def __init__(self, value, base=10, indirect=False):
        Object.__init__(self, indirect)

    def _repr(self):
        return int.__repr__(self)

    def _bytes(self, document):
        return int.__str__(self).encode('utf_8')


class Real(Object, float):
    def __new__(cls, value, indirect=False):
        return float.__new__(cls, value)

    def __init__(self, value, indirect=False):
        Object.__init__(self, indirect)

    def _repr(self):
        return float.__repr__(self)

    def _bytes(self, document):
        return float.__repr__(self).encode('utf_8')


class String(Object, bytes):
    PREFIX = b'('
    POSTFIX = b')'
    ESCAPED_CHARACTERS = {ord(b'\n'): br'\n',
                          ord(b'\r'): br'\r',
                          ord(b'\t'): br'\t',
                          ord(b'\b'): br'\b',
                          ord(b'\f'): br'\f',
                          ord(b'\\'): br'\\',
                          ord(b'('): br'\(',
                          ord(b')'): br'\)'}

    def __new__(cls, value, indirect=False):
        try:
            value = value.encode('pdf_doc')
        except UnicodeEncodeError:
            value = BOM_UTF16_BE + value.encode('utf_16')
        except AttributeError:
            pass
        return bytes.__new__(cls, value)

    def __init__(self, value, indirect=False):
        Object.__init__(self, indirect)

    def __str__(self):
        if self.startswith(BOM_UTF16_BE):
            return self.decode('utf_16')
        else:
            return self.decode('pdf_doc')

    def _repr(self):
        try:
            return "'" + str(self) + "'"
        except UnicodeDecodeError:
            return '<{}{}>'.format(hexlify(self[:10]).decode(),
                                   '...' if len(self) > 10 else '')

    def _bytes(self, document):
        escaped = bytearray()
        for char in self:
            if char in self.ESCAPED_CHARACTERS:
                escaped += self.ESCAPED_CHARACTERS[char]
            else:
                escaped.append(char)
        return escaped


class HexString(Object, bytes):
    PREFIX = b'<'
    POSTFIX = b'>'

    def __new__(cls, value, indirect=False):
        return bytes.__new__(cls, value)

    def __init__(self, byte_string, indirect=False):
        Object.__init__(self, indirect)

    def _repr(self):
        return hexlify(self).decode()

    def _bytes(self, document):
        return hexlify(self)


class Date(String):
    def __new__(cls, timestamp, indirect=False):
        local_time = datetime.fromtimestamp(timestamp)
        utc_time = datetime.utcfromtimestamp(timestamp)
        utc_offset = local_time - utc_time
        utc_offset_minutes, utc_offset_seconds = divmod(utc_offset.seconds, 60)
        utc_offset_hours, utc_offset_minutes = divmod(utc_offset_minutes, 60)
        string = local_time.strftime('D:%Y%m%d%H%M%S')
        string += "{:+03d}'{:02d}'".format(utc_offset_hours, utc_offset_minutes)
        return String.__new__(cls, string, indirect)


class Name(Object, bytes):
    PREFIX = b'/'

    # TODO: names should be unique (per document), so check
    def __new__(cls, value, indirect=False):
        try:
            value = value.encode('utf_8')
        except AttributeError:
            pass
        return bytes.__new__(cls, value)

    def __init__(self, value, indirect=False):
        Object.__init__(self, indirect)

    def __str__(self):
        return self.decode('utf_8')

    def _repr(self):
        return str(self)

    def _bytes(self, document):
        escaped = bytearray()
        for char in self:
            if char in WHITESPACE + DELIMITERS + b'#':
                escaped += '#{:02x}'.format(char).encode('ascii')
            else:
                escaped.append(char)
        return escaped


class Container(Object):
    def __init__(self, indirect=False):
        super().__init__(indirect)

    def register_indirect(self, document, visited=None):
        if visited is None:     # visited helps prevent infinite looping when
            visited = set()     # an object holds a reference to an ancestor
        if id(self) not in visited:
            if self.indirect:
                document.register(self)
                visited.add(id(self))
            for item in self.children():
                item.register_indirect(document, visited)


class Array(Container, list):
    PREFIX = b'['
    POSTFIX = b']'

    # TODO: not all methods of list are overridden, so funny
    # behavior is to be expected
    def __init__(self, items=[], indirect=False):
        Container.__init__(self, indirect)
        list.__init__(self, items)

    def __getitem__(self, arg):
        if isinstance(arg, slice):
            items = [elem.object for elem in super().__getitem__(arg)]
            return self.__class__(items, indirect=self.indirect)
        else:
            return super().__getitem__(arg).object

    def _repr(self):
        return ', '.join(elem.object.short_repr() for elem in self)

    def _bytes(self, document):
        return b' '.join(elem.bytes(document) for elem in self)

    def short_repr(self):
        return '<{} {}>'.format(self.__class__.__name__, id(self))

    def children(self):
        for item in self:
            yield item.object


def convert_key_to_name(method):
    @wraps(method)
    def wrapper(obj, key, *args, **kwargs):
        if not isinstance(key, Name):
            key = Name(key)
        return method(obj, key, *args, **kwargs)
    return wrapper


class Dictionary(Container, OrderedDict):
    PREFIX = b'<<'
    POSTFIX = b'>>'

    type = None
    subtype = None

    def __init__(self, indirect=False):
        Container.__init__(self, indirect)
        OrderedDict.__init__(self)
        if self.__class__.type:
            self['Type'] = Name(self.__class__.type)
        if self.__class__.subtype:
            self['Subtype'] = Name(self.__class__.subtype)

    def _repr(self):
        return ', '.join('{}: {}'.format(key, value.object.short_repr())
                         for key, value in self.items())

    @convert_key_to_name
    def __getitem__(self, key):
        return super().__getitem__(key).object

    __setitem__ = convert_key_to_name(OrderedDict.__setitem__)

    __contains__ = convert_key_to_name(OrderedDict.__contains__)

    get = convert_key_to_name(OrderedDict.get)

    def _bytes(self, document):
        return b' '.join(key.bytes(document) + b' ' + value.bytes(document)
                         for key, value in self.items())

    def short_repr(self):
        return '<{} {}>'.format(self.__class__.__name__, id(self))

    def children(self):
        for item in self.values():
            yield item.object


from .filter import PassThrough


class Stream(Dictionary):
    def __init__(self, filter=None):
        # (Streams are always indirectly referenced)
        self._data = BytesIO()
        self._filter = filter or PassThrough()
        super().__init__(indirect=True)
        self._coder = None

    def direct_bytes(self, document):
        out = bytearray()
        try:
            self._coder.close()
        except AttributeError:
            pass
        if not isinstance(self._filter, PassThrough):
            self['Filter'] = Name(self._filter.name)
            if self._filter.params:
                self['DecodeParms'] = self._filter.params
        if 'Length' in self:
            self['Length'].delete(document)
        self['Length'] = Integer(self._data.tell())
        out += super().direct_bytes(document)
        out += b'\nstream\n'
        out += self._data.getvalue()
        out += b'\nendstream'
        return out

    def read(self, n=-1):
        try:
            return self._coder.read(n)
        except AttributeError:
            self._data.seek(0)
            self._coder = self._filter.decoder(self._data)
            return self.read(n)

    def write(self, b):
        try:
            return self._coder.write(b)
        except AttributeError:
            self._data.seek(0)
            self._coder = self._filter.encoder(self._data)
            return self.write(b)

    def reset(self):
        self._coder = None

    def __getattr__(self, name):
        # almost as good as inheriting from BytesIO (which is not possible)
        return getattr(self._data, name)


class XObjectForm(Stream):
    type = 'XObject'
    subtype = 'Form'

    def __init__(self, bounding_box):
        super().__init__()
        self['BBox'] = bounding_box


class ObjectStream(Stream):
    type = 'ObjStm'

    def get_object(self, document, index):
        try:
            object_reader = self._object_reader
            offsets = self._offsets
        except AttributeError:
            decompressed_data = BytesIO(self.read())
            from .reader import PDFObjectReader
            object_reader = PDFObjectReader(decompressed_data, document)
            offsets = self._offsets = {}
            for i in range(self['N']):
                object_number = int(object_reader.read_number())
                offset = int(self['First'] + object_reader.read_number())
                offsets[i] = offset
            self._object_reader = object_reader
        object_reader.file.seek(offsets[index])
        return object_reader.next_item(indirect=True)


class Null(Object):
    def __init__(self, indirect=False):
        super().__init__(indirect)

    def __repr__(self):
        return self.__class__.__name__

    def _bytes(self, document):
        return b'null'



class Document(dict):
    PRODUCER = 'RinohType v{} PDF backend ({})'.format(__version__,
                                                       __release_date__)

    def __init__(self, creator):
        self.catalog = Catalog()
        self.info = Dictionary(indirect=True)
        self.timestamp = time.time()
        self.set_info('Creator', creator)
        self.set_info('Producer', self.PRODUCER)
        self.info['CreationDate'] = Date(self.timestamp)
        self.id = None
        self._by_object_id = {}

    def register(self, obj):
        if id(obj) not in self._by_object_id:
            identifier, generation = self.max_identifier + 1, 0
            reference = Reference(self, identifier, generation)
            self._by_object_id[id(obj)] = reference
            self[identifier] = obj

    @property
    def max_identifier(self):
        try:
            identifier = max(self.keys())
        except ValueError:
            identifier = 0
        return identifier

    def _write_xref_table(self, file, addresses):
        def out(string):
            file.write(string + b'\n')

        out(b'xref')
        out('0 {}'.format(self.max_identifier + 1).encode('utf_8'))
        out(b'0000000000 65535 f ')
        for identifier in range(1, self.max_identifier + 1):
            try:
                address = addresses[identifier]
                out('{:010d} {:05d} n '.format(address, 0).encode('utf_8'))
            except KeyError:
                out(b'0000000000 65535 f ')

    def set_info(self, field, string):
        assert field in ('Creator', 'Producer',
                         'Title', 'Author', 'Subject', 'Keywords')
        if string:
            if field in self.info:
                self.info[field].delete(self)
            self.info[field] = String(string)

    def write(self, file_or_filename):
        def out(string):
            file.write(string + b'\n')

        try:
            file = open(file_or_filename, 'wb')
            close_file = True
        except TypeError:
            file = file_or_filename
            close_file = False

        self.catalog.register_indirect(self)
        self.info.register_indirect(self)
        if 'ModDate' in self.info:
            self.info['ModDate'].delete(self)
        self.info['ModDate'] = Date(self.timestamp)

        out('%PDF-{}'.format(PDF_VERSION).encode('utf_8'))
        file.write(b'%\xDC\xE1\xD8\xB7\n')
        # write out indirect objects
        addresses = {}
        for identifier in range(1, self.max_identifier + 1):
            if identifier in self:
                obj = self[identifier]
                addresses[identifier] = file.tell()
                out('{} 0 obj'.format(identifier).encode('utf_8'))
                out(obj.direct_bytes(self))
                out(b'endobj')
        xref_table_address = file.tell()
        self._write_xref_table(file, addresses)
        out(b'trailer')
        trailer = Dictionary()
        trailer['Size'] = Integer(self.max_identifier + 1)
        trailer['Root'] = self.catalog
        trailer['Info'] = self.info
        md5sum = hashlib.md5()
        md5sum.update(str(self.timestamp).encode())
        md5sum.update(str(file.tell()).encode())
        for value in self.info.values():
            md5sum.update(value._bytes(self))
        new_id = HexString(md5sum.digest())
        if self.id:
            self.id[1] = new_id
        else:
            self.id = Array([new_id, new_id])
        trailer['ID'] = self.id
        out(trailer.bytes(self))
        out(b'startxref')
        out(str(xref_table_address).encode('utf_8'))
        out(b'%%EOF')
        if close_file:
            file.close()


class Catalog(Dictionary):
    type = 'Catalog'

    def __init__(self):
        super().__init__(indirect=True)
        self['Pages'] = Pages()


class Pages(Dictionary):
    type = 'Pages'

    def __init__(self):
        super().__init__(indirect=True)
        self['Count'] = Integer(0)
        self['Kids'] = Array()

    def new_page(self, width, height):
        page = Page(self, width, height)
        self['Kids'].append(page)
        self['Count'] = Integer(self['Count'] + 1)
        return page


class Page(Dictionary):
    type = 'Page'

    def __init__(self, parent, width, height):
        super().__init__(indirect=True)
        self['Parent'] = parent
        self['Resources'] = Dictionary()
        self['MediaBox'] = Array([Integer(0), Integer(0),
                                  Real(width), Real(height)])

    def to_xobject_form(self):
        content_stream = self['Contents']
        xobject = XObjectForm(self['MediaBox'])
        if 'Filter' in content_stream:
            xobject['Filter'] = content_stream['Filter']
        if 'Resources' in self:
            xobject['Resources'] = self['Resources']
        xobject.write(content_stream.getvalue())
        return xobject


class Font(Dictionary):
    type = 'Font'


class SimpleFont(Font):
    def __init__(self):
        raise NotImplementedError()


class Type1Font(Font):
    subtype = 'Type1'

    def __init__(self, font, encoding, font_descriptor):
        super().__init__(True)
        self.font = font
        self['BaseFont'] = Name(font.name)
        self['Encoding'] = encoding
        self['FontDescriptor'] = font_descriptor

    def _bytes(self, document):
        if not 'Widths' in self:
            widths = []
            by_code = {glyph.code: glyph
                       for glyph in self.font._glyphs.values()
                       if glyph.code >= 0}
            try:
                differences = self['Encoding']['Differences']
                first, last = min(differences.taken), max(differences.taken)
            except KeyError:
                first, last = min(by_code.keys()), max(by_code.keys())
            self['FirstChar'] = Integer(first)
            self['LastChar'] = Integer(last)
            for code in range(first, last + 1):
                try:
                    glyph = by_code[code]
                    width = glyph.width
                except KeyError:
                    try:
                        glyph = differences.by_code[code]
                        width = glyph.width
                    except (KeyError, NameError):
                        width = 0
                widths.append(width)
            self['Widths'] = Array(map(Real, widths))
        return super()._bytes(document)


class CompositeFont(Font):
    subtype = 'Type0'

    def __init__(self, descendant_font, encoding, to_unicode=None):
        super().__init__(True)
        self['BaseFont'] = descendant_font.composite_font_name(encoding)
        self['DescendantFonts'] = Array([descendant_font], False)
        try:
            self['Encoding'] = Name(encoding)
        except NotImplementedError:
            self['Encoding'] = encoding
        if to_unicode is not None:
            self['ToUnicode'] = to_unicode


class CIDSystemInfo(Dictionary):
    def __init__(self, ordering, registry, supplement):
        super().__init__(False)
        self['Ordering'] = String(ordering)
        self['Registry'] = String(registry)
        self['Supplement'] = Integer(supplement)


class CIDFont(Font):
    def __init__(self, base_font, cid_system_info, font_descriptor,
                 dw=1000, w=None):
        super().__init__(True)
        self['BaseFont'] = Name(base_font)
        self['FontDescriptor'] = font_descriptor
        self['CIDSystemInfo'] = cid_system_info
        self['DW'] = Integer(dw)
        if w:
            self['W'] = w

    def composite_font_name(self, encoding):
        raise NotImplementedError()


class CIDFontType0(CIDFont):
    subtype = 'CIDFontType0'

    def __init__(self, base_font, cid_system_info, font_descriptor,
                 dw=1000, w=None):
        super().__init__(base_font, cid_system_info, font_descriptor, dw, w)

    def composite_font_name(self, encoding):
        try:
            suffix = encoding['CMapName']
        except TypeError:
            suffix = encoding
        return Name('{}-{}'.format(self['BaseFont'], suffix))


class CIDFontType2(CIDFont):
    subtype = 'CIDFontType2'

    def __init__(self, base_font, cid_system_info, font_descriptor,
                 dw=1000, w=None, cid_to_gid_map=None):
        super().__init__(base_font, cid_system_info, font_descriptor, dw, w)
        if cid_to_gid_map:
            self['CIDToGIDMap'] = cid_to_gid_map

    def composite_font_name(self, encoding):
        return self['BaseFont']


class FontDescriptor(Dictionary):
    type = 'FontDescriptor'

    def __init__(self, font_name, flags, font_bbox, italic_angle, ascent,
                 descent, cap_height, stem_v, font_file, x_height=0):
        super().__init__(True)
        self['FontName'] = Name(font_name)
        self['Flags'] = Integer(flags)
        self['FontBBox'] = Array([Integer(item) for item in font_bbox])
        self['ItalicAngle'] = Integer(italic_angle)
        self['Ascent'] = Integer(ascent)
        self['Descent'] = Integer(descent)
        self['CapHeight'] = Integer(cap_height)
        self['XHeight'] = Integer(x_height)
        self['StemV'] = Integer(stem_v)
        self[font_file.key] = font_file


class Type3FontDescriptor(FontDescriptor):
    def __init__(self):
        raise NotImplementedError()


class Type1FontFile(Stream):
    key = 'FontFile'

    def __init__(self, header, body, filter=None):
        super().__init__(filter)
        self['Length1'] = Integer(len(header))
        self['Length2'] = Integer(len(body))
        self['Length3'] = Integer(0)
        self.write(header)
        self.write(body)


class OpenTypeFontFile(Stream):
    key = 'FontFile3'

    def __init__(self, font_data, filter=None):
        super().__init__(filter)
        self['Subtype'] = Name('OpenType')
        self.write(font_data)


class FontEncoding(Dictionary):
    def __init__(self, indirect=True):
        super().__init__(indirect)
        self['Type'] = Name('Encoding')


class EncodingDifferences(Object):
    def __init__(self, taken):
        super().__init__(False)
        self.taken = taken
        self.previous_free = 1
        self.by_glyph = {}
        self.by_code = {}

    def register(self, glyph):
        try:
            code = self.by_glyph[glyph]
        except KeyError:
            while self.previous_free in self.taken:
                self.previous_free += 1
                if self.previous_free > 255:
                    raise NotImplementedError('Encoding vector is full')
            code = self.previous_free
            self.taken.append(code)
            self.by_glyph[glyph] = code
            self.by_code[code] = glyph
        return code

    def _bytes(self, document):
        # TODO: subclass Array
        output = b'['
        previous = 256
        for code in sorted(self.by_code.keys()):
            if code != previous + 1:
                output += b' ' + Integer(code).bytes(document)
            output += b' ' + Name(self.by_code[code].name).bytes(document)
            previous = code
        output += b' ]'
        return output


class ToUnicode(Stream):
    def __init__(self, mapping, filter=None):
        super().__init__(filter=filter)
        with self._begin_resource('/CIDInit /ProcSet findresource'):
            with self._begin_resource('12 dict'):
                with self._begin('cmap'):
                    cid_system_info = Dictionary()
                    cid_system_info['Registry'] = String('Adobe')
                    cid_system_info['Ordering'] = String('UCS')
                    cid_system_info['Supplement'] = Integer('0')
                    self._def('CIDSystemInfo', cid_system_info)
                    self._def('CMapName', Name('Adobe-Identity-UCS'))
                    self._def('CMapType', Integer(2))
                    with self._begin('codespacerange', 1):
                        self._value(0x0000)
                        self._value(0xFFFF)
                        self.write(b'\n')
                    #with self._begin('bfrange', 1):
                    #    # TODO: limit to sets of 100 entries
                    #    # TODO: ranges should not cross first-byte limits
                    #    self._value(0x0000)
                    #    self._value(0xFFFF)
                    #    self._value(0x0000)
                    with self._begin('bfchar', len(mapping)):
                        # TODO: limit to sets of 100 entries
                        for unicode, cid in mapping.items():
                            self._value(cid)
                            self._value(unicode)
                            self.write(b'\n')
                self.print('CMapName currentdict /CMap defineresource pop')

    @contextmanager
    def _begin_resource(self, string):
        self.print('{} begin'.format(string))
        yield
        self.print('end')

    @contextmanager
    def _begin(self, string, length=None):
        if length:
            self.print('{} '.format(length), end='')
        self.print('begin{}'.format(string))
        yield
        self.print('end{}'.format(string))

    def _def(self, key, value):
        self.print('/{} '.format(key), end='')
        self.write(value.bytes(None))
        self.print(' def')

    def _value(self, value, number_of_bytes=2):
        hex_str = HexString((value).to_bytes(number_of_bytes, byteorder='big'))
        self.write(hex_str.bytes(None))

    def print(self, strng, end='\n'):
        self.write(strng.encode('ascii'))
        self.write(end.encode('ascii'))

########NEW FILE########
__FILENAME__ = filter
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


import struct, zlib

from binascii import hexlify, unhexlify
from math import floor, ceil

from .util import FIFOBuffer


class Filter(object):
    params_class = None

    @property
    def name(self):
        return self.__class__.__name__

    def encoder(self, destination):
        raise NotImplementedError

    def decoder(self, source):
        raise NotImplementedError


class Encoder(object):
    def __init__(self, destination):
        self._destination = destination

    def write(self, b):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError


class Decoder(object):
    def __init__(self, source):
        self._source = source

    def read(self, n=-1):
        raise NotImplementedError


class PassThrough(Filter):
    def encoder(self, destination):
        return PassThroughEncoder(destination)

    def decoder(self, source):
        return PassThroughDecoder(source)


class PassThroughEncoder(Encoder):
    def write(self, b):
        return self._destination.write(b)

    def close(self):
        pass


class PassThroughDecoder(Decoder):
    def read(self, b):
        return self._destination.read(n)


class ASCIIHexDecode(Filter):
    def encoder(self, destination):
        return ASCIIHexEncoder(destination)

    def decode(self, source):
        return ASCIIHexDecoder(source)


class ASCIIHexEncoder(Decoder):
    def write(self, b):
        self._destination.write(hexlify(b))

    def close(self):
        pass


class ASCIIHexDecoder(Decoder):
    def read(self, n=-1):
        return unhexlify(self._source.read(n))


class ASCII85Decode(Filter):
    def encode(self, data):
        raise NotImplementedError

    def decode(self, data):
        raise NotImplementedError


from .cos import Dictionary, Integer


class FlateDecodeParams(Dictionary):
    def __init__(self, predictor=None, colors=None, bits_per_component=None,
                 columns=None):
        if predictor:
            self['Predictor'] = Integer(predictor)
        if colors:
            self['Colors'] = Integer(colors)
        if colors:
            self['BitsPerComponent'] = Integer(bits_per_component)
        if colors:
            self['Columns'] = Integer(columns)

    @property
    def bytes_per_column(self):
        colors = self.get('Colors', 1)
        bits_per_component = self.get('BitsPerComponent', 8)
        columns = self.get('Columns', 1)
        return ceil(colors * bits_per_component / 8 * columns)


class FlateDecode(Filter):
    params_class = FlateDecodeParams

    def __init__(self, params=None, level=6):
        super().__init__()
        self.params = params
        self.level = level

    def encoder(self, destination):
        return FlateEncoder(destination, self.level)

    def decoder(self, source):
        decoded = FlateDecoder(source)
        if self.params and self.params['Predictor'] > 1:
            if self.params['Predictor'] >= 10:
                return PNGReconstructor(decoded, self.params.bytes_per_column)
            else:
                raise NotImplementedError
        else:
            return decoded


class FlateEncoder(Encoder):
    def __init__(self, destination, level):
        super().__init__(destination)
        self._compressor = zlib.compressobj(level)

    def write(self, b):
        self._destination.write(self._compressor.compress(b))

    def close(self):
        self._destination.write(self._compressor.flush())


class FlateDecoder(FIFOBuffer, Decoder):
    def __init__(self, source):
        super().__init__(source)
        self._decompressor = zlib.decompressobj()

    def read_from_source(self, n):
        if self._decompressor is None:
            return b''
        in_data = self._source.read(n)
        out_data = self._decompressor.decompress(in_data)
        if len(in_data) == 0:
            out_data += self._decompressor.flush()
            self._decompressor = None
        elif len(out_data) == 0:
            out_data = self.read_from_source(self, n)
        return out_data


class LZWDecodeParams(FlateDecodeParams):
    def __init__(self, predictor=None, colors=None, bits_per_component=None,
                 columns=None, early_change=None):
        super().__init__(predictor, colors, bits_per_component, columns)
        if early_change:
            self['EarlyChange'] = cos.Integer(early_change)


class PNGReconstructor(FIFOBuffer):
    NONE = 0
    SUB = 1
    UP = 2
    AVERAGE = 3
    PAETH = 4

    # TODO: bitsper...
    def __init__(self, source, bytes_per_column):
        super().__init__(source)
        self.bytes_per_column = bytes_per_column
        self._column_struct = struct.Struct('>{}B'.format(bytes_per_column))
        self._last_values = [0] * bytes_per_column

    def read_from_source(self, n):
        # number of bytes requested `n` is ignored; a single row is fetched
        predictor = struct.unpack('>B', self._source.read(1))[0]
        row = self._source.read(self._column_struct.size)
        values = list(self._column_struct.unpack(row))

        if predictor == self.NONE:
            out_row = row
        elif predictor == self.SUB:
            recon_a = 0
            for index, filt_x in enumerate(values):
                recon_a = values[index] = (filt_x + recon_a) % 256
            out_row = self._column_struct.pack(*values)
        elif predictor == self.UP:
            for index, (filt_x, recon_b) in enumerate(zip(values,
                                                          self._last_values)):
                values[index] = (filt_x + recon_b) % 256
            out_row = self._column_struct.pack(*values)
        elif predictor == self.AVERAGE:
            recon_a = 0
            for index, (filt_x, recon_b) in enumerate(zip(values,
                                                          self._last_values)):
                average = (recon_a + recon_b) // 2
                recon_a = values[index] = (filt_x + average) % 256
            out_row = self._column_struct.pack(*values)
        elif predictor == self.PAETH:
            recon_a = recon_c = 0
            for index, (filt_x, recon_b) in enumerate(zip(values,
                                                          self._last_values)):
                prediction = paeth_predictor(recon_a, recon_b, recon_c)
                recon_a = values[index] = (filt_x + prediction) % 256
            out_row = self._column_struct.pack(*values)

        self._last_values = values
        return out_row


def paeth_predictor(a, b, c):
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    elif pb <= pc:
        return b
    else:
        return c

########NEW FILE########
__FILENAME__ = pdfdoccodec
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


import codecs


def search_function(encoding):
    if encoding == 'pdf_doc':
        return getregentry()


codecs.register(search_function)


### Codec APIs

class Codec(codecs.Codec):
    def encode(self, input, errors='strict'):
        return codecs.charmap_encode(input, errors, encoding_table)

    def decode(self, input, errors='strict'):
        return codecs.charmap_decode(input, errors, decoding_table)


class IncrementalEncoder(codecs.IncrementalEncoder):
    def encode(self, input, final=False):
        return codecs.charmap_encode(input, self.errors, encoding_table)[0]


class IncrementalDecoder(codecs.IncrementalDecoder):
    def decode(self, input, final=False):
        return codecs.charmap_decode(input, self.errors, decoding_table)[0]


class StreamWriter(Codec, codecs.StreamWriter):
    pass


class StreamReader(Codec, codecs.StreamReader):
    pass


### encodings module API

def getregentry():
    return codecs.CodecInfo(
        name='pdf-doc',
        encode=Codec().encode,
        decode=Codec().decode,
        incrementalencoder=IncrementalEncoder,
        incrementaldecoder=IncrementalDecoder,
        streamreader=StreamReader,
        streamwriter=StreamWriter,
    )


### Decoding Table (from the PDF reference)

decoding_table = (
    '\ufffe'    #  0x00 -> (NULL)
    '\ufffe'    #  0x01 -> (START OF HEADING)
    '\ufffe'    #  0x02 -> (START OF TEXT)
    '\ufffe'    #  0x03 -> (END OF TEXT)
    '\ufffe'    #  0x04 -> (END OF TEXT)
    '\ufffe'    #  0x05 -> (END OF TRANSMISSION)
    '\ufffe'    #  0x06 -> (ACKNOWLEDGE)
    '\ufffe'    #  0x07 -> (BELL)
    '\ufffe'    #  0x08 -> (BACKSPACE)
    '\ufffe'    #  0x09 -> (CHARACTER TABULATION)
    '\ufffe'    #  0x0A -> (LINE FEED)
    '\ufffe'    #  0x0B -> (LINE TABULATION)
    '\ufffe'    #  0x0C -> (FORM FEED)
    '\ufffe'    #  0x0D -> (CARRIAGE RETURN)
    '\ufffe'    #  0x0E -> (SHIFT OUT)
    '\ufffe'    #  0x0F -> (SHIFT IN)
    '\ufffe'    #  0x10 -> (DATA LINK ESCAPE)
    '\ufffe'    #  0x11 -> (DEVICE CONTROL ONE)
    '\ufffe'    #  0x12 -> (DEVICE CONTROL TWO)
    '\ufffe'    #  0x13 -> (DEVICE CONTROL THREE)
    '\ufffe'    #  0x14 -> (DEVICE CONTROL FOUR)
    '\ufffe'    #  0x15 -> (NEGATIVE ACKNOWLEDGE)
    '\ufffe'    #  0x16 -> (SYNCRONOUS IDLE)
    '\ufffe'    #  0x17 -> (END OF TRANSMISSION BLOCK)
    '\u02d8'    #  0x18 -> BREVE
    '\u02c7'    #  0x19 -> CARON
    '\u02c6'    #  0x1A -> MODIFIER LETTER CIRCUMFLEX ACCENT
    '\u02d9'    #  0x1B -> DOT ABOVE
    '\u02dd'    #  0x1C -> DOUBLE ACUTE ACCENT
    '\u02db'    #  0x1D -> OGONEK
    '\u02da'    #  0x1E -> RING ABOVE
    '\u02dc'    #  0x1F -> SMALL TILDE
    ' '         #  0x20 -> SPACE (&#32;)
    '!'         #  0x21 -> EXCLAMATION MARK
    '"'         #  0x22 -> QUOTATION MARK (&quot;)
    '#'         #  0x23 -> NUMBER SIGN
    '$'         #  0x24 -> DOLLAR SIGN
    '%'         #  0x25 -> PERCENT SIGN
    '&'         #  0x26 -> AMPERSAND (&amp;)
    "'"         #  0x27 -> APOSTROPHE (&apos;)
    '('         #  0x28 -> LEFT PARENTHESIS
    ')'         #  0x29 -> RIGHT PARENTHESIS
    '*'         #  0x2A -> ASTERISK
    '+'         #  0x2B -> PLUS SIGN
    ','         #  0x2C -> COMMA
    '-'         #  0x2D -> HYPHEN-MINUS
    '.'         #  0x2E -> FULL STOP (period)
    '/'         #  0x2F -> SOLIDUS (slash)
    '0'         #  0x30 -> DIGIT ZERO
    '1'         #  0x31 -> DIGIT ONE
    '2'         #  0x32 -> DIGIT TWO
    '3'         #  0x33 -> DIGIT THREE
    '4'         #  0x34 -> DIGIT FOUR
    '5'         #  0x35 -> DIGIT FIVE
    '6'         #  0x36 -> DIGIT SIX
    '7'         #  0x37 -> DIGIT SEVEN
    '8'         #  0x38 -> DIGIT EIGJT
    '9'         #  0x39 -> DIGIT NINE
    ':'         #  0x3A -> COLON
    ';'         #  0x3B -> SEMICOLON
    '<'         #  0x3C -> LESS THAN SIGN (&lt;)
    '='         #  0x3D -> EQUALS SIGN
    '>'         #  0x3E -> GREATER THAN SIGN (&gt;)
    '?'         #  0x3F -> QUESTION MARK
    '@'         #  0x40 -> COMMERCIAL AT
    'A'         #  0x41 ->
    'B'         #  0x42 ->
    'C'         #  0x43 ->
    'D'         #  0x44 ->
    'E'         #  0x45 ->
    'F'         #  0x46 ->
    'G'         #  0x47 ->
    'H'         #  0x48 ->
    'I'         #  0x49 ->
    'J'         #  0x4A ->
    'K'         #  0x4B ->
    'L'         #  0x4C ->
    'M'         #  0x4D ->
    'N'         #  0x4E ->
    'O'         #  0x4F ->
    'P'         #  0x50 ->
    'Q'         #  0x51 ->
    'R'         #  0x52 ->
    'S'         #  0x53 ->
    'T'         #  0x54 ->
    'U'         #  0x55 ->
    'V'         #  0x56 ->
    'W'         #  0x57 ->
    'X'         #  0x58 ->
    'Y'         #  0x59 ->
    'Z'         #  0x5A ->
    '['         #  0x5B -> LEFT SQUARE BRACKET
    '\\'        #  0x5C -> REVERSE SOLIDUS (backslash)
    ']'         #  0x5D -> RIGHT SQUARE BRACKET
    '^'         #  0x5E -> CIRCUMFLEX ACCENT (hat)
    '_'         #  0x5F -> LOW LINE (SPACING UNDERSCORE)
    '`'         #  0x60 -> GRAVE ACCENT
    'a'         #  0x61 ->
    'b'         #  0x62 ->
    'c'         #  0x63 ->
    'd'         #  0x64 ->
    'e'         #  0x65 ->
    'f'         #  0x66 ->
    'g'         #  0x67 ->
    'h'         #  0x68 ->
    'i'         #  0x69 ->
    'j'         #  0x6A ->
    'k'         #  0x6B ->
    'l'         #  0x6C ->
    'm'         #  0x6D ->
    'n'         #  0x6E ->
    'o'         #  0x6F ->
    'p'         #  0x70 ->
    'q'         #  0x71 ->
    'r'         #  0x72 ->
    's'         #  0x73 ->
    't'         #  0x74 ->
    'u'         #  0x75 ->
    'v'         #  0x76 ->
    'w'         #  0x77 ->
    'x'         #  0x78 ->
    'y'         #  0x79 ->
    'z'         #  0x7A ->
    '{'         #  0x7B -> LEFT CURLY BRACKET
    '|'         #  0x7C -> VERTICAL LINE
    '}'         #  0x7D -> RIGHT CURLY BRACKET
    '~'         #  0x7E -> TILDE
    '\ufffe'    #  0x7F -> Undefined
    '\u2022'    #  0x80 -> BULLET
    '\u2020'    #  0x81 -> DAGGER
    '\u2021'    #  0x82 -> DOUBLE DAGGER
    '\u2026'    #  0x83 -> HORIZONTAL ELLIPSIS
    '\u2014'    #  0x84 -> EM DASH
    '\u2013'    #  0x85 -> EN DASH
    '\u0192'    #  0x86 ->
    '\u2044'    #  0x87 -> FRACTION SLASH (solidus)
    '\u2039'    #  0x88 -> SINGLE LEFT-POINTING ANGLE QUOTATION MARK
    '\u203a'    #  0x89 -> SINGLE RIGHT-POINTING ANGLE QUOTATION MARK
    '\u2212'    #  0x8A ->
    '\u2030'    #  0x8B -> PER MILLE SIGN
    '\u201e'    #  0x8C -> DOUBLE LOW-9 QUOTATION MARK (quotedblbase)
    '\u201c'    #  0x8D -> LEFT DOUBLE QUOTATION MARK (double quote left)
    '\u201d'    #  0x8E -> RIGHT DOUBLE QUOTATION MARK (quotedblright)
    '\u2018'    #  0x8F -> LEFT SINGLE QUOTATION MARK (quoteleft)
    '\u2019'    #  0x90 -> RIGHT SINGLE QUOTATION MARK (quoteright)
    '\u201a'    #  0x91 -> SINGLE LOW-9 QUOTATION MARK (quotesinglbase)
    '\u2122'    #  0x92 -> TRADE MARK SIGN
    '\ufb01'    #  0x93 -> LATIN SMALL LIGATURE FI
    '\ufb02'    #  0x94 -> LATIN SMALL LIGATURE FL
    '\u0141'    #  0x95 -> LATIN CAPITAL LETTER L WITH STROKE
    '\u0152'    #  0x96 -> LATIN CAPITAL LIGATURE OE
    '\u0160'    #  0x97 -> LATIN CAPITAL LETTER S WITH CARON
    '\u0178'    #  0x98 -> LATIN CAPITAL LETTER Y WITH DIAERESIS
    '\u017d'    #  0x99 -> LATIN CAPITAL LETTER Z WITH CARON
    '\u0131'    #  0x9A -> LATIN SMALL LETTER DOTLESS I
    '\u0142'    #  0x9B -> LATIN SMALL LETTER L WITH STROKE
    '\u0153'    #  0x9C -> LATIN SMALL LIGATURE OE
    '\u0161'    #  0x9D -> LATIN SMALL LETTER S WITH CARON
    '\u017e'    #  0x9E -> LATIN SMALL LETTER Z WITH CARON
    '\ufffe'    #  0x9F -> Undefined
    '\u20ac'    #  0xA0 -> EURO SIGN
    '\u00a1'    #  0xA1 -> INVERTED EXCLAMATION MARK
    '\xa2'      #  0xA2 -> CENT SIGN
    '\xa3'      #  0xA3 -> POUND SIGN (sterling)
    '\xa4'      #  0xA4 -> CURRENCY SIGN
    '\xa5'      #  0xA5 -> YEN SIGN
    '\xa6'      #  0xA6 -> BROKEN BAR
    '\xa7'      #  0xA7 -> SECTION SIGN
    '\xa8'      #  0xA8 -> DIAERESIS
    '\xa9'      #  0xA9 -> COPYRIGHT SIGN
    '\xaa'      #  0xAA -> FEMININE ORDINAL INDICATOR
    '\xab'      #  0xAB -> LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
    '\xac'      #  0xAC -> NOT SIGN
    '\ufffe'    #  0xAD -> Undefined
    '\xae'      #  0xAE -> REGISTERED SIGN
    '\xaf'      #  0xAF -> MACRON
    '\xb0'      #  0xB0 -> DEGREE SIGN
    '\xb1'      #  0xB1 -> PLUS-MINUS SIGN
    '\xb2'      #  0xB2 -> SUPERSCRIPT TWO
    '\xb3'      #  0xB3 -> SUPERSCRIPT THREE
    '\xb4'      #  0xB4 -> ACUTE ACCENT
    '\xb5'      #  0xB5 -> MICRO SIGN
    '\xb6'      #  0xB6 -> PILCROW SIGN
    '\xb7'      #  0xB7 -> MIDDLE DOT
    '\xb8'      #  0xB8 -> CEDILLA
    '\xb9'      #  0xB9 -> SUPERSCRIPT ONE
    '\xba'      #  0xBA -> MASCULINE ORDINAL INDICATOR
    '\xbb'      #  0xBB -> RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
    '\xbc'      #  0xBC -> VULGAR FRACTION ONE QUARTER
    '\xbd'      #  0xBD -> VULGAR FRACTION ONE HALF
    '\xbe'      #  0xBE -> VULGAR FRACTION THREE QUARTERS
    '\xbf'      #  0xBF -> INVERTED QUESTION MARK
    '\xc0'      #  0xC0 ->
    '\xc1'      #  0xC1 ->
    '\xc2'      #  0xC2 ->
    '\xc3'      #  0xC3 ->
    '\xc4'      #  0xC4 ->
    '\xc5'      #  0xC5 ->
    '\xc6'      #  0xC6 ->
    '\xc7'      #  0xC7 ->
    '\xc8'      #  0xC8 ->
    '\xc9'      #  0xC9 ->
    '\xca'      #  0xCA ->
    '\xcb'      #  0xCB ->
    '\xcc'      #  0xCC ->
    '\xcd'      #  0xCD ->
    '\xce'      #  0xCE ->
    '\xcf'      #  0xCF ->
    '\xd0'      #  0xD0 ->
    '\xd1'      #  0xD1 ->
    '\xd2'      #  0xD2 ->
    '\xd3'      #  0xD3 ->
    '\xd4'      #  0xD4 ->
    '\xd5'      #  0xD5 ->
    '\xd6'      #  0xD6 ->
    '\xd7'      #  0xD7 ->
    '\xd8'      #  0xD8 ->
    '\xd9'      #  0xD9 ->
    '\xda'      #  0xDA ->
    '\xdb'      #  0xDB ->
    '\xdc'      #  0xDC ->
    '\xdd'      #  0xDD ->
    '\xde'      #  0xDE ->
    '\xdf'      #  0xDF ->
    '\xe0'      #  0xE0 ->
    '\xe1'      #  0xE1 ->
    '\xe2'      #  0xE2 ->
    '\xe3'      #  0xE3 ->
    '\xe4'      #  0xE4 ->
    '\xe5'      #  0xE5 ->
    '\xe6'      #  0xE6 ->
    '\xe7'      #  0xE7 ->
    '\xe8'      #  0xE8 ->
    '\xe9'      #  0xE9 ->
    '\xea'      #  0xEA ->
    '\xeb'      #  0xEB ->
    '\xec'      #  0xEC ->
    '\xed'      #  0xED ->
    '\xee'      #  0xEE ->
    '\xef'      #  0xEF ->
    '\xf0'      #  0xF0 ->
    '\xf1'      #  0xF1 ->
    '\xf2'      #  0xF2 ->
    '\xf3'      #  0xF3 ->
    '\xf4'      #  0xF4 ->
    '\xf5'      #  0xF5 ->
    '\xf6'      #  0xF6 ->
    '\xf7'      #  0xF7 ->
    '\xf8'      #  0xF8 ->
    '\xf9'      #  0xF9 ->
    '\xfa'      #  0xFA ->
    '\xfb'      #  0xFB ->
    '\xfc'      #  0xFC ->
    '\xfd'      #  0xFD ->
    '\xfe'      #  0xFE ->
    '\xff'      #  0xFF ->
)

### Encoding table
encoding_table = codecs.charmap_build(decoding_table)

########NEW FILE########
__FILENAME__ = reader
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


import re, struct, time

from binascii import unhexlify
from collections import OrderedDict
from io import BytesIO, SEEK_CUR, SEEK_END

from . import cos
from .filter import Filter
from .util import FIFOBuffer
from ...util import all_subclasses


DICTIONARY_SUBCLASSES = {}
for cls in all_subclasses(cos.Dictionary):
    if cls.type is not None:
        DICTIONARY_SUBCLASSES.setdefault((cls.type, cls.subtype), cls)

FILTER_SUBCLASSES = {cls.__name__: cls
                     for cls in all_subclasses(Filter)}



class PDFObjectReader(object):
    def __init__(self, file_or_filename, document=None):
        try:
            self.file = open(file_or_filename, 'rb')
        except TypeError:
            self.file = file_or_filename
        self.document = document or self

    def jump_to_next_line(self):
        while True:
            char = self.file.read(1)
            if char == b'\n':
                break
            elif char == b'\r':
                next_char = self.file.read(1)
                if next_char != b'\n':
                    self.file.seek(-1, SEEK_CUR)
                break

    def eat_whitespace(self):
        while True:
            char = self.file.read(1)
            if char == b'':
                break
            if char not in cos.WHITESPACE:
                self.file.seek(-1, SEEK_CUR)
                break

    def next_token(self):
        token = self.file.read(1)
        if token in (cos.HexString.PREFIX, cos.HexString.POSTFIX):
            # check for dict begin/end
            char = self.file.read(1)
            if char == token:
                token += char
            else:
                self.file.seek(-1, SEEK_CUR)
        elif token in cos.DELIMITERS + cos.WHITESPACE:
            pass
        else:
            while True:
                char = self.file.read(1)
                if char in cos.DELIMITERS + cos.WHITESPACE:
                    self.file.seek(-1, SEEK_CUR)
                    break
                token += char
        return token

    def next_item(self, indirect=False):
        self.eat_whitespace()
        restore_pos = self.file.tell()
        token = self.next_token()
        if token == cos.String.PREFIX:
            item = self.read_string(indirect)
        elif token == cos.HexString.PREFIX:
            item = self.read_hex_string(indirect)
        elif token == cos.Array.PREFIX:
            item = self.read_array(indirect)
        elif token == cos.Name.PREFIX:
            item = self.read_name(indirect)
        elif token == cos.Dictionary.PREFIX:
            item = self.read_dictionary_or_stream(indirect)
        elif token == b'true':
            item = cos.Boolean(True, indirect=indirect)
        elif token == b'false':
            item = cos.Boolean(False, indirect=indirect)
        elif token == b'null':
            item = cos.Null(indirect=indirect)
        else:
            # number or indirect reference
            self.file.seek(restore_pos)
            item = self.read_number(indirect)
            restore_pos = self.file.tell()
            if isinstance(item, cos.Integer):
                try:
                    generation = self.read_number()
                    self.eat_whitespace()
                    r = self.next_token()
                    if isinstance(generation, cos.Integer) and r == b'R':
                        item = cos.Reference(self.document, int(item),
                                             int(generation))
                    else:
                        raise ValueError
                except ValueError:
                    self.file.seek(restore_pos)
        return item

    def peek(self, length=50):
        restore_pos = self.file.tell()
        print(self.file.read(length))
        self.file.seek(restore_pos)

    # TODO: move reader function outside to simplify unit testing
    def read_array(self, indirect=False):
        array = cos.Array(indirect=indirect)
        while True:
            self.eat_whitespace()
            token = self.file.read(1)
            if token == cos.Array.POSTFIX:
                break
            self.file.seek(-1, SEEK_CUR)
            item = self.next_item()
            array.append(item)
        return array

    def read_name(self, indirect=False):
        name = b''
        while True:
            char = self.file.read(1)
            if char in cos.DELIMITERS + cos.WHITESPACE:
                self.file.seek(-1, SEEK_CUR)
                break
            elif char == b'#':
                char_code = self.file.read(2)
                char = chr(int(char_code.decode('ascii'), 16)).encode('ascii')
            name += char
        return cos.Name(name, indirect=indirect)

    def read_dictionary_or_stream(self, indirect=False):
        dictionary = cos.Dictionary(indirect=indirect)
        while True:
            self.eat_whitespace()
            token = self.next_token()
            if token == cos.Dictionary.POSTFIX:
                break
            key, value = self.read_name(), self.next_item()
            dictionary[key] = value
        self.eat_whitespace()
        dict_pos = self.file.tell()
        if self.next_token() == b'stream':
            self.jump_to_next_line()
            length = int(dictionary['Length'])
            if 'Filter' in dictionary:
                filter_class = FILTER_SUBCLASSES[str(dictionary['Filter'])]
                if 'DecodeParms' in dictionary:
                    decode_params = dictionary['DecodeParms']
                    decode_params.__class__ = filter_class.params_class
                else:
                    decode_params = None
                stream_filter = filter_class(params=decode_params)
            else:
                stream_filter = None
            stream = cos.Stream(stream_filter)
            stream.update(dictionary)
            stream._data.write(self.file.read(length))
            self.eat_whitespace()
            assert self.next_token() == b'endstream'
            dictionary = stream
        else:
            self.file.seek(dict_pos)
        # try to map to specific Dictionary sub-class
        type = dictionary.get('Type', None)
        subtype = dictionary.get('Subtype', None)
        key = str(type) if type else None, str(subtype) if subtype else None
        if key in DICTIONARY_SUBCLASSES:
            dictionary.__class__ = DICTIONARY_SUBCLASSES[key]
        return dictionary

    escape_chars = b'nrtbf()\\'

    def read_string(self, indirect=False):
        string = b''
        escape = False
        parenthesis_level = 0   # TODO: is currently not used
        while True:
            char = self.file.read(1)
            if escape:
                if char in self.escape_chars:
                    string += char
                elif char == b'\n':
                    pass
                elif char == b'\r' and self.file.read(1) != '\n':
                    self.file.seek(-1, SEEK_CUR)
                elif char.isdigit():
                    for i in range(2):
                        extra = self.file.read(1)
                        if extra.isdigit():
                            char += extra
                        else:
                            self.file.seek(-1, SEEK_CUR)
                            break
                    string += struct.pack('B', int(char, 8))
                else:
                    string += b'\\' + char
                escape = False
            elif char == b'\\':
                escape = True
            elif char == b'(':
                parenthesis_level += 1
            elif char == b')' and parenthesis_level > 0:
                parenthesis_level -= 1
            elif char == cos.String.POSTFIX:
                break
            else:
                string += char
        return cos.String(string, indirect=indirect)

    def read_hex_string(self, indirect=False):
        hex_string = b''
        while True:
            self.eat_whitespace()
            char = self.file.read(1)
            if char == cos.HexString.POSTFIX:
                break
            hex_string += char
        if len(hex_string) % 2 > 0:
            hex_string += b'0'
        return cos.HexString(unhexlify(hex_string), indirect=indirect)

    def read_number(self, indirect=False):
        self.eat_whitespace()
        number_string = b''
        while True:
            char = self.file.read(1)
            if char not in b'+-.0123456789':
                self.file.seek(-1, SEEK_CUR)
                break
            number_string += char
        try:
            number = cos.Integer(number_string, indirect=indirect)
        except ValueError:
            number = cos.Real(number_string, indirect=indirect)
        return number


class PDFReader(PDFObjectReader, cos.Document):
    def __init__(self, file_or_filename):
        super().__init__(file_or_filename)
        self.timestamp = time.time()
        self._by_object_id = {}
        xref_offset = self.find_xref_offset()
        self._xref, trailer = self.parse_xref_table(xref_offset)
        if 'Info' in trailer:
            self.info = trailer['Info']
        else:
            self.info = cos.Dictionary()
        self.id = trailer['ID'] if 'ID' in trailer else None
        self._max_identifier_in_file = int(trailer['Size']) - 1
        self.catalog = trailer['Root']

    @property
    def max_identifier(self):
        return max(super().max_identifier, self._max_identifier_in_file)

    def __getitem__(self, identifier):
        try:
            obj = super().__getitem__(identifier)
        except KeyError:
            obj = self[identifier] = self._xref.get_object(identifier)
        return obj

    def __delitem__(self, identifier):
        del self._xref[identifier]
        super().__delitem__(identifier)

    def parse_trailer(self):
        assert self.next_token() == b'trailer'
        self.jump_to_next_line()
        trailer_dict = self.next_item()
        return trailer_dict
##/Size: (Required; must not be an indirect reference) The total number of entries in the file's
##cross-reference table, as defined by the combination of the original section and all
##update sections. Equivalently, this value is 1 greater than the highest object number
##used in the file.
##Note: Any object in a cross-reference section whose number is greater than this value is
##ignored and considered missing.

    def parse_indirect_object(self, address):
        # save file state
        restore_pos = self.file.tell()
        self.file.seek(address)
        identifier = int(self.read_number())
        generation = int(self.read_number())
        self.eat_whitespace()
        assert self.next_token() == b'obj'
        self.eat_whitespace()
        obj = self.next_item(indirect=True)
        reference = cos.Reference(self, identifier, generation)
        self._by_object_id[id(obj)] = reference
        self.eat_whitespace()
        assert self.next_token() == b'endobj'
        self.file.seek(restore_pos)
        return identifier, obj

    def parse_xref_table(self, offset):
        xref = XRefTable(self)
        self.file.seek(offset)
        assert self.next_token() == b'xref'
        while True:
            try:
                first, total = int(self.read_number()), self.read_number()
                self.jump_to_next_line()
                for identifier in range(first, first + total):
                    line = self.file.read(20)
                    fields = identifier, int(line[:10]), int(line[11:16])
                    if line[17] == ord(b'n'):
                        xref[identifier] = IndirectObjectEntry(*fields)
                    else:
                        assert line[17] == ord(b'f')
                        xref[identifier] = FreeObjectEntry(*fields)
            except ValueError:
                break
        trailer = self.parse_trailer()
        prev_xref = xref_stm = None
        if 'Prev' in trailer:
            prev_xref, prev_trailer = self.parse_xref_table(trailer['Prev'])
        if 'XRefStm' in trailer:
            xref_stm, _ = self.parse_xref_stream(trailer['XRefStm'])
            xref_stm.prev = prev_xref
        xref.prev = xref_stm or prev_xref
        return xref, trailer

    def parse_xref_stream(self, offset):
        identifier, xref_stream = self.parse_indirect_object(offset)
        self[identifier] = xref_stream
        if 'Prev' in xref_stream:
            prev = self.parse_indirect_object(xref_stream['Prev'])
        else:
            prev = None
        xref = XRefTable(self, prev)
        size = int(xref_stream['Size'])
        widths = [int(width) for width in xref_stream['W']]
        assert len(widths) == 3
        if 'Index' in xref_stream:
            index = iter(int(value) for value in xref_stream['Index'])
        else:
            index = (0, size)
        row_struct = struct.Struct('>' + ''.join('{}B'.format(width)
                                                 for width in widths))
        xref_stream.seek(0)
        while True:
            try:
                first, total = next(index), next(index)
            except StopIteration:
                break
            for identifier in range(first, first + total):
                fields = row_struct.unpack(xref_stream.read(row_struct.size))
                if widths[0] == 0:
                    field_type = 1
                else:
                    field_type = fields[0]
                    fields = fields[1:]
                field_class = FIELD_CLASSES[field_type]
                xref[identifier] = field_class(identifier, *fields)
        assert identifier + 1 == size
        return xref, xref_stream

    def find_xref_offset(self):
        self.file.seek(0, SEEK_END)
        offset = self.file.tell() - len('%%EOF')
        while True:
            self.file.seek(offset)
            value = self.file.read(len('startxref'))
            if value == b'startxref':
                self.jump_to_next_line()
                xref_offset = self.read_number()
                self.jump_to_next_line()
                if self.file.read(5) != b'%%EOF':
                    raise ValueError('Invalid PDF file: missing %%EOF')
                break
            offset -= 1
        return int(xref_offset)


class XRefTable(dict):
    def __init__(self, document, prev=None):
        self.document = document
        self.prev = prev

    def get_object(self, identifier):
        try:
            return self[identifier].get_object(self.document)
        except KeyError:
            return self.prev.get_object(identifier)


class XRefEntry(object):
    def get_object(self, document):
        raise NotImplementedError


class FreeObjectEntry(XRefEntry):
    def __init__(self, identifier, next_free_object_identifier, generation):
        self.identifier = identifier
        self.next_free_object_identifier = next_free_object_identifier
        self.generation = generation

    def get_object(self, document):
        raise Exception('Cannot retieve a free object with id {}'
                        .format(self.identifier))


class IndirectObjectEntry(XRefEntry):
    def __init__(self, identifier, address, generation=0):
        self.identifier = identifier
        self.address = address
        self.generation = generation

    def get_object(self, document):
        obj_identifier, obj = document.parse_indirect_object(self.address)
        assert obj_identifier == self.identifier
        return obj


class CompressedObjectEntry(XRefEntry):
    def __init__(self, identifier, object_stream_identifier, object_index):
        self.identifier = identifier
        self.object_stream_identifier = object_stream_identifier
        self.object_index = object_index

    def get_object(self, document):
        object_stream = document[self.object_stream_identifier]
        return object_stream.get_object(document, self.object_index)


FIELD_CLASSES = {0: FreeObjectEntry,
                 1: IndirectObjectEntry,
                 2: CompressedObjectEntry}

########NEW FILE########
__FILENAME__ = util
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


from io import BytesIO


class FIFOBuffer(object):
    def __init__(self, source, buffer_size=4096):
        self._source = source
        self._buffer_size = buffer_size
        self._fifo = BytesIO()
        self._write_pos = 0
        self._read_pos = 0

    @property
    def size(self):
        return self._write_pos - self._read_pos

    def read_from_source(self, n):
        raise NotImplementedError

    def fill_buffer(self):
        self._fifo.seek(self._write_pos)
        data = self.read_from_source(self._buffer_size)
        self._fifo.write(data)
        self._write_pos = self._fifo.tell()
        return len(data) > 0

    def read(self, n=-1):
        while n is None or n < 0 or self.size < n:
            if not self.fill_buffer():
                break
        self._fifo.seek(self._read_pos)
        out = self._fifo.read(n)
        self._read_pos = self._fifo.tell()
        if self._read_pos > self._buffer_size:
            self._fifo = BytesIO(self._fifo.read())
            self._write_pos = self._fifo.tell()
            self._read_pos = 0
        return out

########NEW FILE########
__FILENAME__ = psg
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


from psg.document.dsc import dsc_document
from psg.drawing.box import eps_image, canvas as psg_Canvas



class Document(object):
    extension = '.ps'

    def __init__(self, rinoh_document, title):
        self.rinoh_document = rinoh_document
        self.psg_doc = dsc_document(title)

    def write(self, filename):
        fp = open(filename + self.extension, 'w', encoding='latin-1')
        self.psg_doc.write_to(fp)
        fp.close()


class Page(object):
    def __init__(self, rinoh_page, psg_document, width, height):
        self.rinoh_page = rinoh_page
        self.psg_doc = psg_document
        self.psg_page = psg_document.psg_doc.page((float(width), float(height)))
        self.canvas = PageCanvas(self, self.psg_page.canvas())

    @property
    def document(self):
        return self.rinoh_page.document


class Canvas(object):
    def __init__(self, parent, left, bottom, width, height, clip=False):
        self.parent = parent
        self.psg_canvas = psg_Canvas(parent.psg_canvas,
                                     left, bottom, width, height, clip=clip)

    @property
    def page(self):
        return self.parent.page

    @property
    def document(self):
        return self.page.document

    @property
    def width(self):
        return self.psg_canvas.w()

    @property
    def height(self):
        return self.psg_canvas.h()

    def new(self, left, bottom, width, height, clip=False):
        new_canvas = Canvas(self, left, bottom, width, height, clip)
        return new_canvas

    def append(self, canvas):
        self.psg_canvas.append(canvas.psg_canvas)

    def save_state(self):
        print('gsave', file=self.psg_canvas)

    def restore_state(self):
        print('grestore', file=self.psg_canvas)

    def translate(self, x, y):
        print('{0} {1} translate'.format(x, y), file=self.psg_canvas)

    def scale(self, x, y=None):
        if y is None:
            y = x
        print('{0} {1} scale'.format(x, y), file=self.psg_canvas)

    def move_to(self, x, y):
        print('{0} {1} moveto'.format(x, y), file=self.psg_canvas)

    def line_to(self, x, y):
        print('{0} {1} lineto'.format(x, y), file=self.psg_canvas)

    def new_path(self):
        print('newpath', file=self.psg_canvas)

    def close_path(self):
        print('closepath', file=self.psg_canvas)

    def line_path(self, points):
        self.new_path()
        self.move_to(*points[0])
        for point in points[1:]:
            self.line_to(*point)
        self.close_path()

    def line_width(self, width):
        print('{0} setlinewidth'.format(width), file=self.psg_canvas)

    def color(self, color):
        r, g, b, a = color.rgba
        print('{0} {1} {2} setrgbcolor'.format(r, g, b), file=self.psg_canvas)

    def stroke(self, linewidth, color):
        self.save_state()
        self.color(color)
        self.line_width(float(linewidth))
        print('stroke', file=self.psg_canvas)
        self.restore_state()

    def fill(self):
        self.save_state()
        self.color(color)
        print('fill', file=self.psg_canvas)
        self.restore_state()

    def _select_font(self, font, size):
        self.font_wrapper = self.psg_canvas.page.register_font(font.psFont,
                                                               True)
        print('/{0} findfont'.format(self.font_wrapper.ps_name()),
                                     file=self.psg_canvas)
        print('{0} scalefont'.format(size), file=self.psg_canvas)
        print('setfont', file=self.psg_canvas)

    def show_glyphs(self, x, y, font, size, glyphs, x_displacements):
        self.move_to(x, y)
        self._select_font(font, size)
        try:
            ps_repr = self.font_wrapper.postscript_representation(glyphs)
        except AttributeError:
            raise RuntimeError('No font selected for canvas.')
        widths = ' '.join(map(lambda f: '%.2f' % f, x_displacements))
        print('({0}) [{1}] xshow'.format(ps_repr, widths), file=self.psg_canvas)

    def place_image(self, image):
        canvas.psg_canvas.append(image.eps)


class Image(object):
    def __init__(self, filename):
        self.eps = eps_image(canvas.psg_canvas, open(filename + '.eps', 'rb'),
                             document_level=True)
        self.height = eps.h() * self.scale
        self.width = eps.w() * self.scale


class PageCanvas(Canvas):
    def __init__(self, page, psg_canvas):
        self.parent = page
        self.psg_canvas = psg_canvas

    @property
    def page(self):
        return self.parent.rinoh_page

########NEW FILE########
__FILENAME__ = csl_formatter
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


from .flowable import GroupedFlowables
from .paragraph import Paragraph
from . import text


def preformat(text):
    return text


def factory(cls):
    def __init__(self, string):
        return super(self.__class__, self).__init__(str(string))
    space = {'__init__': __init__}
    return type(cls.__name__, (cls, ), space)


Italic = factory(text.Italic)
Oblique = factory(text.Italic)

Bold = factory(text.Bold)
Light = factory(text.Bold)

Underline = factory(text.Bold)

Superscript = factory(text.Superscript)
Subscript = factory(text.Subscript)

SmallCaps = factory(text.SmallCaps)

########NEW FILE########
__FILENAME__ = decoration
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


from .draw import Rectangle, ShapeStyle
from .layout import DownExpandingContainer, EndOfContainer
from .flowable import Flowable, FlowableStyle
from .style import PARENT_STYLE


__all__ = ['FrameStyle', 'Framed']


class FrameStyle(FlowableStyle, ShapeStyle):
    attributes = {'padding_left': 10,
                  'padding_right': 10,
                  'padding_top': 10,
                  'padding_bottom': 10}


class Framed(Flowable):
    style_class = FrameStyle

    def __init__(self, flowable, style=None, parent=None):
        super().__init__(style=style, parent=parent)
        self.flowable = flowable
        flowable.parent = self

    def render(self, container, descender, state=None):
        document = container.document
        try:
            container.advance(self.get_style('padding_top', document))
            left = self.get_style('padding_left', document)
            right = container.width - self.get_style('padding_right', document)
            pad_container = DownExpandingContainer('PADDING', container,
                                                   left=left, right=right)
            _, descender = self.flowable.flow(pad_container, descender,
                                              state=state)
            container.advance(pad_container.cursor
                              + self.get_style('padding_bottom', document))
            self.render_frame(container, container.height)
            return container.width, descender
        except EndOfContainer:
            self.render_frame(container, container.max_height)
            raise

    def render_frame(self, container, container_height):
        width, height = float(container.width), - float(container_height)
        rect = Rectangle((0, 0), width, height, style=PARENT_STYLE, parent=self)
        rect.render(container.canvas)

########NEW FILE########
__FILENAME__ = dimension
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.

"""
This module exports a single class:

* :class:`Dimension`: Late-evaluated dimension, forming the basis of the layout
  engine

It also exports a number of pre-defined units:

* :const:`PT`: PostScript point
* :const:`INCH`: Inch, equal to 72 PostScript points
* :const:`MM`: Millimeter
* :const:`CM`: Centimeter

"""


__all__ = ['Dimension', 'PT', 'INCH', 'MM', 'CM']


class DimensionType(type):
    """Maps comparison operators to their equivalents in :class:`float`"""

    def __new__(mcs, name, bases, cls_dict):
        """Return a new class with predefined comparison operators"""
        for method_name in ('__lt__', '__le__', '__gt__', '__ge__',
                            '__eq__', '__ne__'):
            cls_dict[method_name] = mcs._make_operator(method_name)
        return type.__new__(mcs, name, bases, cls_dict)

    @staticmethod
    def _make_operator(method_name):
        """Return an operator method that takes parameters of type
        :class:`Dimension`, evaluates them, and delegates to the :class:`float`
        operator with name `method_name`"""
        def operator(self, other):
            """Operator delegating to the :class:`float` method `method_name`"""
            float_operator = getattr(float, method_name)
            return float_operator(float(self), float(other))
        return operator


class DimensionBase(object, metaclass=DimensionType):
    """Late-evaluated dimension. The result of mathematical operations on
    dimension objects is not a statically evaluated version, but rather stores
    references to the operator arguments. The result is only evaluated to a
    number on conversion to a :class:`float`.

    The internal representation is in terms of PostScript points. A PostScript
    point is equal to one 72th of an inch."""

    def __neg__(self):
        return DimensionMultiplication(self, -1)

    def __add__(self, other):
        """Return the sum of this dimension and `other`."""
        return DimensionAddition(self, other)

    __radd__ = __add__

    def __sub__(self, other):
        """Return the difference of this dimension and `other`."""
        return DimensionSubtraction(self, other)

    def __rsub__(self, other):
        """Return the difference of `other` and this dimension."""
        return DimensionSubtraction(other, self)

    def __mul__(self, factor):
        """Return the product of this dimension and `factor`."""
        return DimensionMultiplication(self, factor)

    __rmul__ = __mul__

    def __truediv__(self, divisor):
        """Return the quotient of this dimension and `divisor`."""
        return DimensionMultiplication(self, 1.0 / divisor)

    def __repr__(self):
        """Return a textual representation of the evaluated value."""
        return str(float(self)) + 'pt'

    def __abs__(self):
        """Return the absolute value of this dimension (in points)."""
        return abs(float(self))

    def __float__(self):
        """Evaluate the value of this dimension in points."""
        raise NotImplementedError


class Dimension(DimensionBase):
    # TODO: em, ex? (depends on context)
    def __init__(self, value=0):
        """Initialize a dimension at `value` points."""
        self._value = value

    def grow(self, value):
        self._value += float(value)
        return self

    def __float__(self):
        return float(self._value)


class DimensionAddition(DimensionBase):
    def __init__(self, *addends):
        self.addends = addends

    def __float__(self):
        return sum(map(float, self.addends))


class DimensionSubtraction(DimensionBase):
    def __init__(self, minuend, subtrahend):
        self.minuend = minuend
        self.subtrahend = subtrahend

    def __float__(self):
        return float(self.minuend) - float(self.subtrahend)


class DimensionMultiplication(DimensionBase):
    def __init__(self, multiplicand, multiplier):
        self.multiplicand = multiplicand
        self.multiplier = multiplier

    def __float__(self):
        return float(self.multiplicand) * self.multiplier


class DimensionUnit(object):
    def __init__(self, points_per_unit):
        self.points_per_unit = float(points_per_unit)

    def __rmul__(self, value):
        return Dimension(value * self.points_per_unit)


# Units

PT = DimensionUnit(1)
INCH = DimensionUnit(72*PT)
MM = DimensionUnit(1 / 25.4 * INCH)
CM = DimensionUnit(10*MM)

########NEW FILE########
__FILENAME__ = document
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.

"""
Classes representing a document:

* :class:`Page`: A single page in a document.
* :class:`Document`: Takes an input file and renders its content onto pages.
* :class:`DocumentElement`: Base class for any element that is eventually
                            rendered in the document.

:class:`Page` require a page orientation to be specified:

* :const:`PORTRAIT`: The page's height is larger than its width.
* :const:`LANDSCAPE`: The page's width is larger than its height.

"""


import time
import pickle

from collections import OrderedDict
from itertools import count

from . import __version__, __release_date__
from .layout import FlowableTarget, Container, ReflowRequired
from .backend import pdf
from .warnings import warn


__all__ = ['Page', 'Document', 'DocumentElement', 'PORTRAIT', 'LANDSCAPE']


PORTRAIT = 'portrait'
LANDSCAPE = 'landscape'


class Page(Container):
    """A single page in a document. A :class:`Page` is a :class:`Container`, so
    other containers can be added as children."""

    def __init__(self, document, paper, orientation=PORTRAIT):
        """Initialize this page as part of `document` (:class:`Document`) with a
        size defined by `paper` (:class:`Paper`). The page's `orientation` can
        be either :const:`PORTRAIT` or :const:`LANDSCAPE`."""
        self.paper = paper
        self.orientation = orientation
        if orientation is PORTRAIT:
            width, height = paper.width, paper.height
        elif orientation is LANDSCAPE:
            width, height = paper.height, paper.width
        FlowableTarget.__init__(self, document)
        Container.__init__(self, 'PAGE', None, 0, 0, width, height)
        backend_document = self.document.backend_document
        self.backend_page = document.backend.Page(self, backend_document,
                                                  self.width, self.height)
        self.section = None     # will point to the last section on this page
        self.overflowed_chains = []
        self.canvas = self.backend_page.canvas

    @property
    def page(self):
        """Returns the page itself."""
        return self

    def render(self):
        for index in count():
            try:
                for chain in super().render(rerender=index > 0):
                    yield chain
                break
            except ReflowRequired:
                print('Overflow on page {}, reflowing ({})...'
                      .format(self.number, index + 1))


class BackendDocumentMetadata(object):
    def __init__(self, name):
        self.name = name

    def __get__(self, instance, object_type):
        return instance.backend_document.get_metadata(self.name)

    def __set__(self, instance, value):
        return instance.backend_document.set_metadata(self.name, value)


class Document(object):
    """A document renders the contents described in an input file onto pages.
    This is an abstract base class; subclasses should implement :meth:`setup`
    and :meth:`add_to_chain`."""

    CREATOR = 'RinohType v{} ({})'.format(__version__, __release_date__)

    CACHE_EXTENSION = '.rtc'

    title = BackendDocumentMetadata('title')
    author = BackendDocumentMetadata('author')
    subject = BackendDocumentMetadata('subject')
    keywords = BackendDocumentMetadata('keywords')

    def __init__(self, backend=pdf, title=None, author=None, subject=None,
                 keywords=None):
        """`backend` specifies the backend to use for rendering the document.
        `title`, `author` and `keywords` (iterable of strings) are metadata
        describing the document. These will be written to the output by the
        backend."""
        self._print_version_and_license()
        self.backend = backend
        self.backend_document = self.backend.Document(self, self.CREATOR)

        self.author = author
        self.title = title
        self.subject = subject
        self.keywords = keywords

        self.flowable_targets = []
        self.counters = {}             # counters for Headings, Figures, Tables
        self.elements = OrderedDict()  # mapping id's to Referenceables
        self.ids_by_element = {}       # mapping elements to id's
        self.references = {}           # mapping id's to reference data
        self.number_of_pages = 0       # page count
        self.page_references = {}      # mapping id's to page numbers
        self._unique_id = 0

    def _print_version_and_license(self):
        print('RinohType {} ({})  Copyright (c) Brecht Machiels'
              .format(__version__, __release_date__))
        print('''\
This program comes with ABSOLUTELY NO WARRANTY. Its use is subject
to the terms of the GNU Affero General Public License version 3.''')

    @property
    def unique_id(self):
        """Yields a different integer value on each access, used to uniquely
        identify :class:`Referenceable`s for which no identifier was
        specified."""
        self._unique_id += 1
        return self._unique_id

    def set_reference(self, id, reference_type, value):
        id_references = self.references.setdefault(id, {})
        id_references[reference_type] = value

    def get_reference(self, id, reference_type):
        return self.references[id][reference_type]

    def add_page(self, page, number):
        """Add `page` (:class:`Page`) with page `number` (as displayed) to this
        document."""
        page.number = number
        self.pages.append(page)

    def _load_cache(self, filename):
        """Load the cached page references from `<filename>.ptc`."""
        try:
            with open(filename + self.CACHE_EXTENSION, 'rb') as file:
                prev_number_of_pages, prev_page_references = pickle.load(file)
        except IOError:
            prev_number_of_pages, prev_page_references = -1, {}
        return prev_number_of_pages, prev_page_references

    def _save_cache(self, filename):
        """Save the current state of the page references to `<filename>.ptc`"""
        with open(filename + self.CACHE_EXTENSION, 'wb') as file:
            cache = self.number_of_pages, self.page_references
            pickle.dump(cache, file)

    def render(self, filename):
        """Render the document repeatedly until the output no longer changes due
        to cross-references that need some iterations to converge."""

        def has_converged():
            """Return `True` if the last rendering iteration converged to a
            stable result.

            Practically, this tests whether the total number of pages and page
            references to document elements have changed since the previous
            rendering iteration."""
            nonlocal prev_number_of_pages, prev_page_references
            return (self.number_of_pages == prev_number_of_pages and
                    self.page_references == prev_page_references)

        prev_number_of_pages, prev_page_references = self._load_cache(filename)
        self.number_of_pages = prev_number_of_pages
        self.page_references = prev_page_references.copy()
        for flowable in (flowable for target in self.flowable_targets
                         for flowable in target.flowables):
            flowable.prepare(self)
        self.number_of_pages = self.render_pages()
        while not has_converged():
            prev_number_of_pages = self.number_of_pages
            prev_page_references = self.page_references.copy()
            print('Not yet converged, rendering again...')
            del self.backend_document
            self.backend_document = self.backend.Document(self, self.CREATOR)
            self.number_of_pages = self.render_pages()
        self._save_cache(filename)
        print('Writing output: {}'.format(filename +
                                          self.backend_document.extension))
        self.backend_document.write(filename)

    def render_pages(self):
        """Render the complete document once and return the number of pages
        rendered."""
        self.pages = []
        self.floats = set()
        self.placed_footnotes = set()
        self.setup()
        for page in self.pages:
            chains_requiring_new_page = set(chain for chain in page.render())
            page.place()
            if chains_requiring_new_page:
                self.new_page(chains_requiring_new_page) # this grows self.pages
        return len(self.pages)

    def setup(self):
        """Called by :meth:`render_pages` before the actual rendering takes
        place. This method should create at least one :class:`Page` and add it
        to this document using :meth:`add_page`."""
        raise NotImplementedError

    def new_page(self, chains):
        """Called by :meth:`render_pages` with the :class:`Chain`s that need
        more :class:`Container`s. This method should create a new :class:`Page`
        wich contains a container associated with `chain` and pass it to
        :meth:`add_page`."""
        raise NotImplementedError


class Location(object):
    def __init__(self, document_element):
        self.location = document_element.__class__.__name__


class DocumentElement(object):
    """An element that is directly or indirectly part of a :class:`Document`
    and is eventually rendered to the output."""

    def __init__(self, parent=None, source=None):
        """Initialize this document element as as a child of `parent`
        (:class:`DocumentElement`) if it is not a top-level :class:`Flowable`
        element. `source` should point to a node in the input's document tree
        corresponding to this document element. It is used to point to a
        location in the input file when warnings or errors are generated (see
        the :meth:`warn` method).

        Both parameters are optional, and can be set at a later point by
        assigning to the identically named instance attributes."""
        self.parent = parent
        self.source = source

    @property
    def source(self):
        """The source element this document element was created from."""
        if self._source is not None:
            return self._source
        elif self.parent is not None:
            return self.parent.source
        else:
            return Location(self)

    @source.setter
    def source(self, source):
        """Set `source` as the source element of this document element."""
        self._source = source

    def prepare(self, document):
        pass

    def warn(self, message, container=None):
        """Present the warning `message` to the user, adding information on the
        location of the related element in the input file."""
        if self.source is not None:
            message = '[{}] '.format(self.source.location) + message
        if container is not None:
            message += ' (page {})'.format(container.page.number)
        warn(message)

########NEW FILE########
__FILENAME__ = draw
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


from .style import Style, Styled
from .dimension import PT


__all__ = ['Color', 'BLACK', 'WHITE', 'RED', 'GREEN', 'BLUE',
           'Gray', 'GRAY10', 'GRAY25', 'GRAY50', 'GRAY75', 'GRAY90',
           'LineStyle', 'Line', 'Shape', 'Polygon', 'Rectangle']


class Color(object):
    def __init__(self, red, green, blue, alpha=1):
        self.r = red
        self.g = green
        self.b = blue
        self.a = alpha

    @property
    def rgba(self):
        return self.r, self.g, self.b, self.a


class Gray(Color):
    def __init__(self, luminance, alpha=1):
        super().__init__(luminance, luminance, luminance, alpha)


BLACK = Color(0, 0, 0)
WHITE = Color(1, 1, 1)
GRAY10 = Gray(0.10)
GRAY25 = Gray(0.25)
GRAY50 = Gray(0.50)
GRAY75 = Gray(0.75)
GRAY90 = Gray(0.90)
RED = Color(1, 0, 0)
GREEN = Color(0, 1, 0)
BLUE = Color(0, 0, 1)


class LineStyle(Style):
    attributes = {'stroke_width': 1*PT,
                  'stroke_color': BLACK}


class Line(Styled):
    style_class = LineStyle

    def __init__(self, start, end, style=None, parent=None):
        super().__init__(style=style, parent=parent)
        self.start = start
        self.end = end

    def render(self, canvas, offset=0):
        points = self.start, self.end
        canvas.line_path(points)
        canvas.stroke(self.get_style('stroke_width', canvas.document),
                      self.get_style('stroke_color', canvas.document))


class ShapeStyle(LineStyle):
    attributes = {'fill_color': GRAY90}


class Shape(Styled):
    style_class = ShapeStyle

    def __init__(self, style=None, parent=None):
        super().__init__(style=style, parent=parent)

    def render(self, canvas, offset=0):
        raise NotImplementedError


class Polygon(Shape):
    def __init__(self, points, style=None, parent=None):
        super().__init__(style=style, parent=parent)
        self.points = points

    def render(self, canvas, offset=0):
        canvas.line_path(self.points)
        canvas.close_path()
        canvas.stroke_and_fill(self.get_style('stroke_width', canvas.document),
                               self.get_style('stroke_color', canvas.document),
                               self.get_style('fill_color', canvas.document))


class Rectangle(Polygon):
    def __init__(self, bottom_left, width, height, style=None, parent=None):
        bottom_right = (bottom_left[0] + width, bottom_left[1])
        top_right = (bottom_left[0] + width, bottom_left[1] + height)
        top_left = (bottom_left[0], bottom_left[1] + height)
        points = bottom_left, bottom_right, top_right, top_left
        super().__init__(points, style=style, parent=parent)

########NEW FILE########
__FILENAME__ = float
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


from .flowable import Flowable, InseparableFlowables
from .number import NumberedParagraph
from .reference import Referenceable, REFERENCE, TITLE
from .text import MixedStyledText


__all__ = ['Image', 'Caption', 'Figure']


class Image(Flowable):
    def __init__(self, filename, scale=1.0, style=None, parent=None):
        super().__init__(style=style, parent=parent)
        self.filename = filename
        self.scale = scale

    def render(self, container, last_descender, state=None):
        image = container.canvas.document.backend.Image(self.filename)
        left = float(container.width - image.width) / 2
        top = float(container.cursor)
        container.canvas.place_image(image, left, top, scale=self.scale)
        container.advance(float(image.height))
        return image.width, 0


class Caption(NumberedParagraph):
    def text(self, document):
        label = self.parent.category + ' ' + self.number(document)
        return MixedStyledText(label + self.content, parent=self)


class Figure(Referenceable, InseparableFlowables):
    category = 'Figure'

    def __init__(self, filename, caption, scale=1.0, style=None, id=None):
        self.image = Image(filename, scale=scale, parent=self)
        self.caption_text = caption
        InseparableFlowables.__init__(self, style)
        Referenceable.__init__(self, id)

    def prepare(self, document):
        super().prepare(document)
        element_id = self.get_id(document)
        number = document.counters.setdefault(__class__, 1)
        document.counters[__class__] += 1
        document.set_reference(element_id, REFERENCE, str(number))
        # TODO: need to store formatted number
        document.set_reference(element_id, TITLE, self.caption_text)

    def flowables(self, document):
        caption = Caption(self.caption_text, parent=self)
        return self.image, caption

########NEW FILE########
__FILENAME__ = flowable
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.

"""
Base classes for flowable and floating document elements. These are elements
that make up the content of a document and are rendered onto its pages.

* :class:`Flowable`: Element that is rendered onto a :class:`Container`.
* :class:`FlowableStyle`: Style class specifying the vertical space surrounding
                          a :class:`Flowable`.
* :class:`Floating`: Decorator to transform a :class:`Flowable` into a floating
                     element.
"""


from copy import copy
from itertools import chain, tee

from .dimension import PT
from .layout import (EndOfContainer, DownExpandingContainer, MaybeContainer,
                     VirtualContainer, discard_state)
from .style import Style, Styled


__all__ = ['Flowable', 'FlowableStyle',
           'DummyFlowable', 'WarnFlowable', 'SetMetadataFlowable',
           'InseparableFlowables', 'GroupedFlowables', 'StaticGroupedFlowables',
           'LabeledFlowable', 'GroupedLabeledFlowables',
           'Float']


class FlowableStyle(Style):
    """The :class:`Style` for :class:`Flowable` objects. It has the following
    attributes:

    * `space_above`: Vertical space preceding the flowable (:class:`Dimension`)
    * `space_below`: Vertical space following the flowable (:class:`Dimension`)
    * `margin_left`: Left margin (class:`Dimension`).
    * `margin_right`: Right margin (class:`Dimension`).
    """

    attributes = {'space_above': 0,
                  'space_below': 0,
                  'margin_left': 0,
                  'margin_right': 0}


class FlowableState(object):
    """Stores a :class:`Flowable`\'s rendering state, which can be copied. This
    enables saving the rendering state at certain points in the rendering
    process, so rendering can later be resumed at those points, if needed."""

    def __copy__(self):
        raise NotImplementedError


class Flowable(Styled):
    """An element that can be 'flowed' into a :class:`Container`. A flowable can
    adapt to the width of the container, or it can horizontally align itself in
    the container."""

    style_class = FlowableStyle

    def __init__(self, style=None, parent=None):
        """Initialize this flowable and associate it with the given `style` and
        `parent` (see :class:`Styled`)."""
        super().__init__(style=style, parent=parent)

    @property
    def level(self):
        try:
            return self.parent.level
        except AttributeError:
            return 0

    @property
    def section(self):
        try:
            return self.parent.section
        except AttributeError:
            return None

    def flow(self, container, last_descender, state=None, **kwargs):
        """Flow this flowable into `container` and return the vertical space
        consumed.

        The flowable's contents is preceded by a vertical space with a height
        as specified in its style's `space_above` attribute. Similarly, the
        flowed content is followed by a vertical space with a height given
        by the `space_below` style attribute."""
        document = container.document
        if not state:
            container.advance(float(self.get_style('space_above', document)))
        margin_left = self.get_style('margin_left', document)
        margin_right = self.get_style('margin_right', document)
        right = container.width - margin_right
        margin_container = DownExpandingContainer('MARGIN', container,
                                                  left=margin_left, right=right)
        width, descender = self.render(margin_container, last_descender,
                                       state=state, **kwargs)
        container.advance(margin_container.cursor)
        try:
            container.advance(float(self.get_style('space_below', document)))
        except EndOfContainer:
            pass
        return margin_left + width + margin_right, descender

    def render(self, container, descender, state=None):
        """Renders the flowable's content to `container`, with the flowable's
        top edge lining up with the container's cursor. `descender` is the
        descender height of the preceeding line or `None`."""
        raise NotImplementedError


class DummyFlowable(Flowable):
    style_class = None

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def flow(self, container, last_descender, state=None):
        return 0, last_descender


class WarnFlowable(DummyFlowable):
    def __init__(self, message, parent=None):
        super().__init__(parent=parent)
        self.message = message

    def flow(self, container, last_descender, state=None):
        self.warn(self.message, container)
        return super().flow(container, last_descender, state)


class SetMetadataFlowable(DummyFlowable):
    def __init__(self, parent=None, **metadata):
        super().__init__(parent=parent)
        self.metadata = metadata

    def flow(self, container, last_descender, state=None):
        for field, value in self.metadata:
            setattr(container.document, field, value)
        return super().flow(container)


class InseparableFlowables(Flowable):
    def flowables(self, document):
        raise NotImplementedError

    def render(self, container, last_descender, state=None):
        max_flowable_width = 0
        with MaybeContainer(container) as maybe_container, discard_state():
            for flowable in self.flowables(container.document):
                width, last_descender = flowable.flow(maybe_container,
                                                      last_descender)
                max_flowable_width = max(max_flowable_width, width)
        return max_flowable_width, last_descender


class GroupedFlowablesState(FlowableState):
    def __init__(self, flowables, first_flowable_state=None):
        self.flowables = flowables
        self.first_flowable_state = first_flowable_state

    def __copy__(self):
        copy_list_items, self.flowables = tee(self.flowables)
        copy_first_flowable_state = copy(self.first_flowable_state)
        return self.__class__(copy_list_items, copy_first_flowable_state)

    def next_flowable(self):
        return next(self.flowables)

    def prepend(self, flowable, first_flowable_state):
        self.flowables = chain((flowable, ), self.flowables)
        self.first_flowable_state = first_flowable_state


class GroupedFlowablesStyle(FlowableStyle):
    attributes = {'flowable_spacing': 0}


class GroupedFlowables(Flowable):
    style_class = GroupedFlowablesStyle

    def flowables(self, document):
        raise NotImplementedError

    def render(self, container, descender, state=None, **kwargs):
        max_flowable_width = 0
        flowables = self.flowables(container.document)
        item_spacing = self.get_style('flowable_spacing', container.document)
        state = state or GroupedFlowablesState(flowables)
        flowable = state.next_flowable()
        try:
            while True:
                width, descender = \
                    flowable.flow(container, descender,
                                  state=state.first_flowable_state, **kwargs)
                max_flowable_width = max(max_flowable_width, width)
                state.first_flowable_state = None
                flowable = state.next_flowable()
                container.advance(item_spacing)
        except EndOfContainer as eoc:
            state.prepend(flowable, eoc.flowable_state)
            raise EndOfContainer(state)
        except StopIteration:
            return max_flowable_width, descender


class StaticGroupedFlowables(GroupedFlowables):
    def __init__(self, flowables, style=None, parent=None):
        super().__init__(style=style, parent=parent)
        self.children = flowables
        for flowable in flowables:
            flowable.parent = self

    def prepare(self, document):
        super().prepare(document)
        for child in self.children:
            child.prepare(document)

    def flowables(self, document):
        return iter(self.children)


class LabeledFlowableStyle(FlowableStyle):
    attributes = {'label_min_width': 12*PT,
                  'label_max_width': 80*PT,
                  'label_spacing': 3*PT,
                  'wrap_label': False}


class LabeledFlowable(Flowable):
    style_class = LabeledFlowableStyle

    def __init__(self, label, flowable, style=None, parent=None):
        super().__init__(style=style, parent=parent)
        self.label = label
        self.flowable = flowable
        label.parent = flowable.parent = self

    def prepare(self, document):
        self.label.prepare(document)
        self.flowable.prepare(document)

    def label_width(self, container):
        virtual_container = VirtualContainer(container)
        label_width, _ = self.label.flow(virtual_container, 0)
        return label_width

    def render(self, container, last_descender, state=None,
               max_label_width=None):
        # TODO: line up baseline of label and first flowable
        label_column_min_width = self.get_style('label_min_width', container.document)
        label_column_max_width = self.get_style('label_max_width', container.document)
        wrap_label = self.get_style('wrap_label', container.document)

        label_width = self.label_width(container)
        max_label_width = max_label_width or label_width
        label_column_width = max(label_column_min_width,
                                 min(max_label_width, label_column_max_width))
        label_spillover = not wrap_label and label_width > label_column_width

        def render_label(container):
            width = None if label_spillover else label_column_width
            label_container = DownExpandingContainer('LABEL', container,
                                                     width=width)
            _, descender = self.label.flow(label_container, last_descender)
            return label_container.cursor, descender

        def render_content(container, descender):
            label_spacing = self.get_style('label_spacing', container.document)
            left = label_column_width + label_spacing
            content_container = DownExpandingContainer('CONTENT', container,
                                                       left=left)
            _, descender = self.flowable.flow(content_container, descender,
                                              state=state)
            return content_container.cursor, descender

        with MaybeContainer(container) as maybe_container:
            if not state:
                with discard_state():
                    label_height, label_desc = render_label(maybe_container)
                    if label_spillover:
                        maybe_container.advance(label_height)
                        last_descender = label_desc
            else:
                label_height = label_desc = 0
            content_height, content_desc = render_content(maybe_container,
                                                          last_descender)
            if label_spillover:
                container.advance(content_height)
                descender = content_desc
            else:
                if content_height > label_height:
                    container.advance(content_height)
                    descender = content_desc
                else:
                    container.advance(label_height)
                    descender = label_desc
        return container.width, descender


class GroupedLabeledFlowables(GroupedFlowables):
    def _calculate_label_width(self, container):
        return max(flowable.label_width(container)
                   for flowable in self.flowables(container.document))

    def render(self, container, descender, state=None):
        if state is None:
            max_label_width = self._calculate_label_width(container)
        else:
            max_label_width = state.max_label_width
        try:
            return super().render(container, descender, state=state,
                                  max_label_width=max_label_width)
        except EndOfContainer as eoc:
            eoc.flowable_state.max_label_width = max_label_width
            raise


class Float(Flowable):
    """Transform a :class:`Flowable` into a floating element. A floating element
    or 'float' is not flowed into its designated container, but is forwarded to
    another container pointed to by the former's :attr:`Container.float_space`
    attribute.

    This is typically used to place figures and tables at the top or bottom of a
    page, instead of in between paragraphs."""

    def __init__(self, flowable, style=None, parent=None):
        super().__init__(style=style, parent=parent)
        self.flowable = flowable
        flowable.parent = self

    def prepare(self, document):
        self.flowable.prepare(document)

    def flow(self, container, last_descender, state=None):
        """Flow contents into the float space associated with `container`."""
        if self not in container.document.floats:
            self.flowable.flow(container.float_space, None)
            container.document.floats.add(self)
            container.page.check_overflow()
        return 0, last_descender

########NEW FILE########
__FILENAME__ = mapping

# from the Adobe Glyph List 2.0 (September 20, 2002)
UNICODE_TO_GLYPH_NAME = {
    0x0001: 'controlSTX',
    0x0002: 'controlSOT',
    0x0003: 'controlETX',
    0x0004: 'controlEOT',
    0x0005: 'controlENQ',
    0x0006: 'controlACK',
    0x0007: 'controlBEL',
    0x0008: 'controlBS',
    0x0009: 'controlHT',
    0x000A: 'controlLF',
    0x000B: 'controlVT',
    0x000C: 'controlFF',
    0x000D: 'controlCR',
    0x000E: 'controlSO',
    0x000F: 'controlSI',
    0x0010: 'controlDLE',
    0x0011: 'controlDC1',
    0x0012: 'controlDC2',
    0x0013: 'controlDC3',
    0x0014: 'controlDC4',
    0x0015: 'controlNAK',
    0x0016: 'controlSYN',
    0x0017: 'controlETB',
    0x0018: 'controlCAN',
    0x0019: 'controlEM',
    0x001A: 'controlSUB',
    0x001B: 'controlESC',
    0x001C: 'controlFS',
    0x001D: 'controlGS',
    0x001E: 'controlRS',
    0x001F: 'controlUS',
    0x0020: ('space', 'spacehackarabic'),
    0x0021: 'exclam',
    0x0022: 'quotedbl',
    0x0023: 'numbersign',
    0x0024: 'dollar',
    0x0025: 'percent',
    0x0026: 'ampersand',
    0x0027: 'quotesingle',
    0x0028: 'parenleft',
    0x0029: 'parenright',
    0x002A: 'asterisk',
    0x002B: 'plus',
    0x002C: 'comma',
    0x002D: 'hyphen',
    0x002E: 'period',
    0x002F: 'slash',
    0x0030: 'zero',
    0x0031: 'one',
    0x0032: 'two',
    0x0033: 'three',
    0x0034: 'four',
    0x0035: 'five',
    0x0036: 'six',
    0x0037: 'seven',
    0x0038: 'eight',
    0x0039: 'nine',
    0x003A: 'colon',
    0x003B: 'semicolon',
    0x003C: 'less',
    0x003D: 'equal',
    0x003E: 'greater',
    0x003F: 'question',
    0x0040: 'at',
    0x0041: 'A',
    0x0042: 'B',
    0x0043: 'C',
    0x0044: 'D',
    0x0045: 'E',
    0x0046: 'F',
    0x0047: 'G',
    0x0048: 'H',
    0x0049: 'I',
    0x004A: 'J',
    0x004B: 'K',
    0x004C: 'L',
    0x004D: 'M',
    0x004E: 'N',
    0x004F: 'O',
    0x0050: 'P',
    0x0051: 'Q',
    0x0052: 'R',
    0x0053: 'S',
    0x0054: 'T',
    0x0055: 'U',
    0x0056: 'V',
    0x0057: 'W',
    0x0058: 'X',
    0x0059: 'Y',
    0x005A: 'Z',
    0x005B: 'bracketleft',
    0x005C: 'backslash',
    0x005D: 'bracketright',
    0x005E: 'asciicircum',
    0x005F: 'underscore',
    0x0060: 'grave',
    0x0061: 'a',
    0x0062: 'b',
    0x0063: 'c',
    0x0064: 'd',
    0x0065: 'e',
    0x0066: 'f',
    0x0067: 'g',
    0x0068: 'h',
    0x0069: 'i',
    0x006A: 'j',
    0x006B: 'k',
    0x006C: 'l',
    0x006D: 'm',
    0x006E: 'n',
    0x006F: 'o',
    0x0070: 'p',
    0x0071: 'q',
    0x0072: 'r',
    0x0073: 's',
    0x0074: 't',
    0x0075: 'u',
    0x0076: 'v',
    0x0077: 'w',
    0x0078: 'x',
    0x0079: 'y',
    0x007A: 'z',
    0x007B: 'braceleft',
    0x007C: ('bar', 'verticalbar'),
    0x007D: 'braceright',
    0x007E: 'asciitilde',
    0x007F: 'controlDEL',
    0x00A0: ('nbspace', 'nonbreakingspace'),
    0x00A1: 'exclamdown',
    0x00A2: 'cent',
    0x00A3: 'sterling',
    0x00A4: 'currency',
    0x00A5: 'yen',
    0x00A6: 'brokenbar',
    0x00A7: 'section',
    0x00A8: 'dieresis',
    0x00A9: 'copyright',
    0x00AA: 'ordfeminine',
    0x00AB: 'guillemotleft',
    0x00AC: 'logicalnot',
    0x00AD: ('sfthyphen', 'softhyphen'),
    0x00AE: 'registered',
    0x00AF: ('macron', 'overscore'),
    0x00B0: 'degree',
    0x00B1: 'plusminus',
    0x00B2: 'twosuperior',
    0x00B3: 'threesuperior',
    0x00B4: 'acute',
    0x00B5: ('mu', 'mu1'),
    0x00B6: 'paragraph',
    0x00B7: ('middot', 'periodcentered'),
    0x00B8: 'cedilla',
    0x00B9: 'onesuperior',
    0x00BA: 'ordmasculine',
    0x00BB: 'guillemotright',
    0x00BC: 'onequarter',
    0x00BD: 'onehalf',
    0x00BE: 'threequarters',
    0x00BF: 'questiondown',
    0x00C0: 'Agrave',
    0x00C1: 'Aacute',
    0x00C2: 'Acircumflex',
    0x00C3: 'Atilde',
    0x00C4: 'Adieresis',
    0x00C5: 'Aring',
    0x00C6: 'AE',
    0x00C7: 'Ccedilla',
    0x00C8: 'Egrave',
    0x00C9: 'Eacute',
    0x00CA: 'Ecircumflex',
    0x00CB: 'Edieresis',
    0x00CC: 'Igrave',
    0x00CD: 'Iacute',
    0x00CE: 'Icircumflex',
    0x00CF: 'Idieresis',
    0x00D0: 'Eth',
    0x00D1: 'Ntilde',
    0x00D2: 'Ograve',
    0x00D3: 'Oacute',
    0x00D4: 'Ocircumflex',
    0x00D5: 'Otilde',
    0x00D6: 'Odieresis',
    0x00D7: 'multiply',
    0x00D8: 'Oslash',
    0x00D9: 'Ugrave',
    0x00DA: 'Uacute',
    0x00DB: 'Ucircumflex',
    0x00DC: 'Udieresis',
    0x00DD: 'Yacute',
    0x00DE: 'Thorn',
    0x00DF: 'germandbls',
    0x00E0: 'agrave',
    0x00E1: 'aacute',
    0x00E2: 'acircumflex',
    0x00E3: 'atilde',
    0x00E4: 'adieresis',
    0x00E5: 'aring',
    0x00E6: 'ae',
    0x00E7: 'ccedilla',
    0x00E8: 'egrave',
    0x00E9: 'eacute',
    0x00EA: 'ecircumflex',
    0x00EB: 'edieresis',
    0x00EC: 'igrave',
    0x00ED: 'iacute',
    0x00EE: 'icircumflex',
    0x00EF: 'idieresis',
    0x00F0: 'eth',
    0x00F1: 'ntilde',
    0x00F2: 'ograve',
    0x00F3: 'oacute',
    0x00F4: 'ocircumflex',
    0x00F5: 'otilde',
    0x00F6: 'odieresis',
    0x00F7: 'divide',
    0x00F8: 'oslash',
    0x00F9: 'ugrave',
    0x00FA: 'uacute',
    0x00FB: 'ucircumflex',
    0x00FC: 'udieresis',
    0x00FD: 'yacute',
    0x00FE: 'thorn',
    0x00FF: 'ydieresis',
    0x0100: 'Amacron',
    0x0101: 'amacron',
    0x0102: 'Abreve',
    0x0103: 'abreve',
    0x0104: 'Aogonek',
    0x0105: 'aogonek',
    0x0106: 'Cacute',
    0x0107: 'cacute',
    0x0108: 'Ccircumflex',
    0x0109: 'ccircumflex',
    0x010A: ('Cdot', 'Cdotaccent'),
    0x010B: ('cdot', 'cdotaccent'),
    0x010C: 'Ccaron',
    0x010D: 'ccaron',
    0x010E: 'Dcaron',
    0x010F: 'dcaron',
    0x0110: ('Dcroat', 'Dslash'),
    0x0111: ('dcroat', 'dmacron'),
    0x0112: 'Emacron',
    0x0113: 'emacron',
    0x0114: 'Ebreve',
    0x0115: 'ebreve',
    0x0116: ('Edot', 'Edotaccent'),
    0x0117: ('edot', 'edotaccent'),
    0x0118: 'Eogonek',
    0x0119: 'eogonek',
    0x011A: 'Ecaron',
    0x011B: 'ecaron',
    0x011C: 'Gcircumflex',
    0x011D: 'gcircumflex',
    0x011E: 'Gbreve',
    0x011F: 'gbreve',
    0x0120: ('Gdot', 'Gdotaccent'),
    0x0121: ('gdot', 'gdotaccent'),
    0x0122: ('Gcedilla', 'Gcommaaccent'),
    0x0123: ('gcedilla', 'gcommaaccent'),
    0x0124: 'Hcircumflex',
    0x0125: 'hcircumflex',
    0x0126: 'Hbar',
    0x0127: 'hbar',
    0x0128: 'Itilde',
    0x0129: 'itilde',
    0x012A: 'Imacron',
    0x012B: 'imacron',
    0x012C: 'Ibreve',
    0x012D: 'ibreve',
    0x012E: 'Iogonek',
    0x012F: 'iogonek',
    0x0130: ('Idot', 'Idotaccent'),
    0x0131: 'dotlessi',
    0x0132: 'IJ',
    0x0133: 'ij',
    0x0134: 'Jcircumflex',
    0x0135: 'jcircumflex',
    0x0136: ('Kcedilla', 'Kcommaaccent'),
    0x0137: ('kcedilla', 'kcommaaccent'),
    0x0138: 'kgreenlandic',
    0x0139: 'Lacute',
    0x013A: 'lacute',
    0x013B: ('Lcedilla', 'Lcommaaccent'),
    0x013C: ('lcedilla', 'lcommaaccent'),
    0x013D: 'Lcaron',
    0x013E: 'lcaron',
    0x013F: ('Ldot', 'Ldotaccent'),
    0x0140: ('ldot', 'ldotaccent'),
    0x0141: 'Lslash',
    0x0142: 'lslash',
    0x0143: 'Nacute',
    0x0144: 'nacute',
    0x0145: ('Ncedilla', 'Ncommaaccent'),
    0x0146: ('ncedilla', 'ncommaaccent'),
    0x0147: 'Ncaron',
    0x0148: 'ncaron',
    0x0149: ('napostrophe', 'quoterightn'),
    0x014A: 'Eng',
    0x014B: 'eng',
    0x014C: 'Omacron',
    0x014D: 'omacron',
    0x014E: 'Obreve',
    0x014F: 'obreve',
    0x0150: ('Odblacute', 'Ohungarumlaut'),
    0x0151: ('odblacute', 'ohungarumlaut'),
    0x0152: 'OE',
    0x0153: 'oe',
    0x0154: 'Racute',
    0x0155: 'racute',
    0x0156: ('Rcedilla', 'Rcommaaccent'),
    0x0157: ('rcedilla', 'rcommaaccent'),
    0x0158: 'Rcaron',
    0x0159: 'rcaron',
    0x015A: 'Sacute',
    0x015B: 'sacute',
    0x015C: 'Scircumflex',
    0x015D: 'scircumflex',
    0x015E: 'Scedilla',
    0x015F: 'scedilla',
    0x0160: 'Scaron',
    0x0161: 'scaron',
    0x0162: ('Tcedilla', 'Tcommaaccent'),
    0x0163: ('tcedilla', 'tcommaaccent'),
    0x0164: 'Tcaron',
    0x0165: 'tcaron',
    0x0166: 'Tbar',
    0x0167: 'tbar',
    0x0168: 'Utilde',
    0x0169: 'utilde',
    0x016A: 'Umacron',
    0x016B: 'umacron',
    0x016C: 'Ubreve',
    0x016D: 'ubreve',
    0x016E: 'Uring',
    0x016F: 'uring',
    0x0170: ('Udblacute', 'Uhungarumlaut'),
    0x0171: ('udblacute', 'uhungarumlaut'),
    0x0172: 'Uogonek',
    0x0173: 'uogonek',
    0x0174: 'Wcircumflex',
    0x0175: 'wcircumflex',
    0x0176: 'Ycircumflex',
    0x0177: 'ycircumflex',
    0x0178: 'Ydieresis',
    0x0179: 'Zacute',
    0x017A: 'zacute',
    0x017B: ('Zdot', 'Zdotaccent'),
    0x017C: ('zdot', 'zdotaccent'),
    0x017D: 'Zcaron',
    0x017E: 'zcaron',
    0x017F: ('longs', 'slong'),
    0x0180: 'bstroke',
    0x0181: 'Bhook',
    0x0182: 'Btopbar',
    0x0183: 'btopbar',
    0x0184: 'Tonesix',
    0x0185: 'tonesix',
    0x0186: 'Oopen',
    0x0187: 'Chook',
    0x0188: 'chook',
    0x0189: 'Dafrican',
    0x018A: 'Dhook',
    0x018B: 'Dtopbar',
    0x018C: 'dtopbar',
    0x018D: 'deltaturned',
    0x018E: 'Ereversed',
    0x018F: 'Schwa',
    0x0190: 'Eopen',
    0x0191: 'Fhook',
    0x0192: 'florin',
    0x0193: 'Ghook',
    0x0194: 'Gammaafrican',
    0x0195: 'hv',
    0x0196: 'Iotaafrican',
    0x0197: 'Istroke',
    0x0198: 'Khook',
    0x0199: 'khook',
    0x019A: 'lbar',
    0x019B: 'lambdastroke',
    0x019C: 'Mturned',
    0x019D: 'Nhookleft',
    0x019E: 'nlegrightlong',
    0x019F: 'Ocenteredtilde',
    0x01A0: 'Ohorn',
    0x01A1: 'ohorn',
    0x01A2: 'Oi',
    0x01A3: 'oi',
    0x01A4: 'Phook',
    0x01A5: 'phook',
    0x01A6: 'yr',
    0x01A7: 'Tonetwo',
    0x01A8: 'tonetwo',
    0x01A9: 'Esh',
    0x01AA: 'eshreversedloop',
    0x01AB: 'tpalatalhook',
    0x01AC: 'Thook',
    0x01AD: 'thook',
    0x01AE: 'Tretroflexhook',
    0x01AF: 'Uhorn',
    0x01B0: 'uhorn',
    0x01B1: 'Upsilonafrican',
    0x01B2: 'Vhook',
    0x01B3: 'Yhook',
    0x01B4: 'yhook',
    0x01B5: 'Zstroke',
    0x01B6: 'zstroke',
    0x01B7: 'Ezh',
    0x01B8: 'Ezhreversed',
    0x01B9: 'ezhreversed',
    0x01BA: 'ezhtail',
    0x01BB: 'twostroke',
    0x01BC: 'Tonefive',
    0x01BD: 'tonefive',
    0x01BE: 'glottalinvertedstroke',
    0x01BF: 'wynn',
    0x01C0: 'clickdental',
    0x01C1: 'clicklateral',
    0x01C2: 'clickalveolar',
    0x01C3: 'clickretroflex',
    0x01C4: 'DZcaron',
    0x01C5: 'Dzcaron',
    0x01C6: 'dzcaron',
    0x01C7: 'LJ',
    0x01C8: 'Lj',
    0x01C9: 'lj',
    0x01CA: 'NJ',
    0x01CB: 'Nj',
    0x01CC: 'nj',
    0x01CD: 'Acaron',
    0x01CE: 'acaron',
    0x01CF: 'Icaron',
    0x01D0: 'icaron',
    0x01D1: 'Ocaron',
    0x01D2: 'ocaron',
    0x01D3: 'Ucaron',
    0x01D4: 'ucaron',
    0x01D5: 'Udieresismacron',
    0x01D6: 'udieresismacron',
    0x01D7: 'Udieresisacute',
    0x01D8: 'udieresisacute',
    0x01D9: 'Udieresiscaron',
    0x01DA: 'udieresiscaron',
    0x01DB: 'Udieresisgrave',
    0x01DC: 'udieresisgrave',
    0x01DD: 'eturned',
    0x01DE: 'Adieresismacron',
    0x01DF: 'adieresismacron',
    0x01E0: 'Adotmacron',
    0x01E1: 'adotmacron',
    0x01E2: 'AEmacron',
    0x01E3: 'aemacron',
    0x01E4: 'Gstroke',
    0x01E5: 'gstroke',
    0x01E6: 'Gcaron',
    0x01E7: 'gcaron',
    0x01E8: 'Kcaron',
    0x01E9: 'kcaron',
    0x01EA: 'Oogonek',
    0x01EB: 'oogonek',
    0x01EC: 'Oogonekmacron',
    0x01ED: 'oogonekmacron',
    0x01EE: 'Ezhcaron',
    0x01EF: 'ezhcaron',
    0x01F0: 'jcaron',
    0x01F1: 'DZ',
    0x01F2: 'Dz',
    0x01F3: 'dz',
    0x01F4: 'Gacute',
    0x01F5: 'gacute',
    0x01FA: 'Aringacute',
    0x01FB: 'aringacute',
    0x01FC: 'AEacute',
    0x01FD: 'aeacute',
    0x01FE: ('Oslashacute', 'Ostrokeacute'),
    0x01FF: ('oslashacute', 'ostrokeacute'),
    0x0200: 'Adblgrave',
    0x0201: 'adblgrave',
    0x0202: 'Ainvertedbreve',
    0x0203: 'ainvertedbreve',
    0x0204: 'Edblgrave',
    0x0205: 'edblgrave',
    0x0206: 'Einvertedbreve',
    0x0207: 'einvertedbreve',
    0x0208: 'Idblgrave',
    0x0209: 'idblgrave',
    0x020A: 'Iinvertedbreve',
    0x020B: 'iinvertedbreve',
    0x020C: 'Odblgrave',
    0x020D: 'odblgrave',
    0x020E: 'Oinvertedbreve',
    0x020F: 'oinvertedbreve',
    0x0210: 'Rdblgrave',
    0x0211: 'rdblgrave',
    0x0212: 'Rinvertedbreve',
    0x0213: 'rinvertedbreve',
    0x0214: 'Udblgrave',
    0x0215: 'udblgrave',
    0x0216: 'Uinvertedbreve',
    0x0217: 'uinvertedbreve',
    0x0218: 'Scommaaccent',
    0x0219: 'scommaaccent',
    0x0250: 'aturned',
    0x0251: 'ascript',
    0x0252: 'ascriptturned',
    0x0253: 'bhook',
    0x0254: 'oopen',
    0x0255: 'ccurl',
    0x0256: 'dtail',
    0x0257: 'dhook',
    0x0258: 'ereversed',
    0x0259: 'schwa',
    0x025A: 'schwahook',
    0x025B: 'eopen',
    0x025C: 'eopenreversed',
    0x025D: 'eopenreversedhook',
    0x025E: 'eopenreversedclosed',
    0x025F: 'jdotlessstroke',
    0x0260: 'ghook',
    0x0261: 'gscript',
    0x0263: 'gammalatinsmall',
    0x0264: 'ramshorn',
    0x0265: 'hturned',
    0x0266: 'hhook',
    0x0267: 'henghook',
    0x0268: 'istroke',
    0x0269: 'iotalatin',
    0x026B: 'lmiddletilde',
    0x026C: 'lbelt',
    0x026D: 'lhookretroflex',
    0x026E: 'lezh',
    0x026F: 'mturned',
    0x0270: 'mlonglegturned',
    0x0271: 'mhook',
    0x0272: 'nhookleft',
    0x0273: 'nhookretroflex',
    0x0275: 'obarred',
    0x0277: 'omegalatinclosed',
    0x0278: 'philatin',
    0x0279: 'rturned',
    0x027A: 'rlonglegturned',
    0x027B: 'rhookturned',
    0x027C: 'rlongleg',
    0x027D: 'rhook',
    0x027E: 'rfishhook',
    0x027F: 'rfishhookreversed',
    0x0281: 'Rsmallinverted',
    0x0282: 'shook',
    0x0283: 'esh',
    0x0284: 'dotlessjstrokehook',
    0x0285: 'eshsquatreversed',
    0x0286: 'eshcurl',
    0x0287: 'tturned',
    0x0288: 'tretroflexhook',
    0x0289: 'ubar',
    0x028A: 'upsilonlatin',
    0x028B: 'vhook',
    0x028C: 'vturned',
    0x028D: 'wturned',
    0x028E: 'yturned',
    0x0290: 'zretroflexhook',
    0x0291: 'zcurl',
    0x0292: 'ezh',
    0x0293: 'ezhcurl',
    0x0294: 'glottalstop',
    0x0295: 'glottalstopreversed',
    0x0296: 'glottalstopinverted',
    0x0297: 'cstretched',
    0x0298: 'bilabialclick',
    0x029A: 'eopenclosed',
    0x029B: 'Gsmallhook',
    0x029D: 'jcrossedtail',
    0x029E: 'kturned',
    0x02A0: 'qhook',
    0x02A1: 'glottalstopstroke',
    0x02A2: 'glottalstopstrokereversed',
    0x02A3: 'dzaltone',
    0x02A4: 'dezh',
    0x02A5: 'dzcurl',
    0x02A6: 'ts',
    0x02A7: 'tesh',
    0x02A8: 'tccurl',
    0x02B0: 'hsuperior',
    0x02B1: 'hhooksuperior',
    0x02B2: 'jsuperior',
    0x02B4: 'rturnedsuperior',
    0x02B5: 'rhookturnedsuperior',
    0x02B6: 'Rsmallinvertedsuperior',
    0x02B7: 'wsuperior',
    0x02B8: 'ysuperior',
    0x02B9: 'primemod',
    0x02BA: 'dblprimemod',
    0x02BB: 'commaturnedmod',
    0x02BC: ('afii57929', 'apostrophemod'),
    0x02BD: ('afii64937', 'commareversedmod'),
    0x02BE: 'ringhalfright',
    0x02BF: 'ringhalfleft',
    0x02C0: 'glottalstopmod',
    0x02C1: 'glottalstopreversedmod',
    0x02C2: 'arrowheadleftmod',
    0x02C3: 'arrowheadrightmod',
    0x02C4: 'arrowheadupmod',
    0x02C5: 'arrowheaddownmod',
    0x02C6: 'circumflex',
    0x02C7: 'caron',
    0x02C8: 'verticallinemod',
    0x02C9: 'firsttonechinese',
    0x02CA: 'secondtonechinese',
    0x02CB: 'fourthtonechinese',
    0x02CC: 'verticallinelowmod',
    0x02CD: 'macronlowmod',
    0x02CE: 'gravelowmod',
    0x02CF: 'acutelowmod',
    0x02D0: 'colontriangularmod',
    0x02D1: 'colontriangularhalfmod',
    0x02D2: 'ringhalfrightcentered',
    0x02D3: 'ringhalfleftcentered',
    0x02D4: 'uptackmod',
    0x02D5: 'downtackmod',
    0x02D6: 'plusmod',
    0x02D7: 'minusmod',
    0x02D8: 'breve',
    0x02D9: 'dotaccent',
    0x02DA: 'ring',
    0x02DB: 'ogonek',
    0x02DC: ('ilde', 'tilde'),
    0x02DD: 'hungarumlaut',
    0x02DE: 'rhotichookmod',
    0x02E0: 'gammasuperior',
    0x02E3: 'xsuperior',
    0x02E4: 'glottalstopreversedsuperior',
    0x02E5: 'tonebarextrahighmod',
    0x02E6: 'tonebarhighmod',
    0x02E7: 'tonebarmidmod',
    0x02E8: 'tonebarlowmod',
    0x02E9: 'tonebarextralowmod',
    0x0300: ('gravecmb', 'gravecomb'),
    0x0301: ('acutecmb', 'acutecomb'),
    0x0302: 'circumflexcmb',
    0x0303: ('tildecmb', 'tildecomb'),
    0x0304: 'macroncmb',
    0x0305: 'overlinecmb',
    0x0306: 'brevecmb',
    0x0307: 'dotaccentcmb',
    0x0308: 'dieresiscmb',
    0x0309: ('hookabovecomb', 'hookcmb'),
    0x030A: 'ringcmb',
    0x030B: 'hungarumlautcmb',
    0x030C: 'caroncmb',
    0x030D: 'verticallineabovecmb',
    0x030E: 'dblverticallineabovecmb',
    0x030F: 'dblgravecmb',
    0x0310: 'candrabinducmb',
    0x0311: 'breveinvertedcmb',
    0x0312: 'commaturnedabovecmb',
    0x0313: 'commaabovecmb',
    0x0314: 'commareversedabovecmb',
    0x0315: 'commaaboverightcmb',
    0x0316: 'gravebelowcmb',
    0x0317: 'acutebelowcmb',
    0x0318: 'lefttackbelowcmb',
    0x0319: 'righttackbelowcmb',
    0x031A: 'leftangleabovecmb',
    0x031B: 'horncmb',
    0x031C: 'ringhalfleftbelowcmb',
    0x031D: 'uptackbelowcmb',
    0x031E: 'downtackbelowcmb',
    0x031F: 'plusbelowcmb',
    0x0320: 'minusbelowcmb',
    0x0321: 'hookpalatalizedbelowcmb',
    0x0322: 'hookretroflexbelowcmb',
    0x0323: ('dotbelowcmb', 'dotbelowcomb'),
    0x0324: 'dieresisbelowcmb',
    0x0325: 'ringbelowcmb',
    0x0327: 'cedillacmb',
    0x0328: 'ogonekcmb',
    0x0329: 'verticallinebelowcmb',
    0x032A: 'bridgebelowcmb',
    0x032B: 'dblarchinvertedbelowcmb',
    0x032C: 'caronbelowcmb',
    0x032D: 'circumflexbelowcmb',
    0x032E: 'brevebelowcmb',
    0x032F: 'breveinvertedbelowcmb',
    0x0330: 'tildebelowcmb',
    0x0331: 'macronbelowcmb',
    0x0332: 'lowlinecmb',
    0x0333: 'dbllowlinecmb',
    0x0334: 'tildeoverlaycmb',
    0x0335: 'strokeshortoverlaycmb',
    0x0336: 'strokelongoverlaycmb',
    0x0337: 'solidusshortoverlaycmb',
    0x0338: 'soliduslongoverlaycmb',
    0x0339: 'ringhalfrightbelowcmb',
    0x033A: 'bridgeinvertedbelowcmb',
    0x033B: 'squarebelowcmb',
    0x033C: 'seagullbelowcmb',
    0x033D: 'xabovecmb',
    0x033E: 'tildeverticalcmb',
    0x033F: 'dbloverlinecmb',
    0x0340: 'gravetonecmb',
    0x0341: 'acutetonecmb',
    0x0342: 'perispomenigreekcmb',
    0x0343: 'koroniscmb',
    0x0344: 'dialytikatonoscmb',
    0x0345: 'ypogegrammenigreekcmb',
    0x0360: 'tildedoublecmb',
    0x0361: 'breveinverteddoublecmb',
    0x0374: 'numeralsigngreek',
    0x0375: 'numeralsignlowergreek',
    0x037A: 'ypogegrammeni',
    0x037E: 'questiongreek',
    0x0384: 'tonos',
    0x0385: ('dialytikatonos', 'dieresistonos'),
    0x0386: 'Alphatonos',
    0x0387: 'anoteleia',
    0x0388: 'Epsilontonos',
    0x0389: 'Etatonos',
    0x038A: 'Iotatonos',
    0x038C: 'Omicrontonos',
    0x038E: 'Upsilontonos',
    0x038F: 'Omegatonos',
    0x0390: 'iotadieresistonos',
    0x0391: 'Alpha',
    0x0392: 'Beta',
    0x0393: 'Gamma',
    0x0394: 'Deltagreek',
    0x0395: 'Epsilon',
    0x0396: 'Zeta',
    0x0397: 'Eta',
    0x0398: 'Theta',
    0x0399: 'Iota',
    0x039A: 'Kappa',
    0x039B: 'Lambda',
    0x039C: 'Mu',
    0x039D: 'Nu',
    0x039E: 'Xi',
    0x039F: 'Omicron',
    0x03A0: 'Pi',
    0x03A1: 'Rho',
    0x03A3: 'Sigma',
    0x03A4: 'Tau',
    0x03A5: 'Upsilon',
    0x03A6: 'Phi',
    0x03A7: 'Chi',
    0x03A8: 'Psi',
    0x03A9: 'Omegagreek',
    0x03AA: 'Iotadieresis',
    0x03AB: 'Upsilondieresis',
    0x03AC: 'alphatonos',
    0x03AD: 'epsilontonos',
    0x03AE: 'etatonos',
    0x03AF: 'iotatonos',
    0x03B0: 'upsilondieresistonos',
    0x03B1: 'alpha',
    0x03B2: 'beta',
    0x03B3: 'gamma',
    0x03B4: 'delta',
    0x03B5: 'epsilon',
    0x03B6: 'zeta',
    0x03B7: 'eta',
    0x03B8: 'theta',
    0x03B9: 'iota',
    0x03BA: 'kappa',
    0x03BB: 'lambda',
    0x03BC: 'mugreek',
    0x03BD: 'nu',
    0x03BE: 'xi',
    0x03BF: 'omicron',
    0x03C0: 'pi',
    0x03C1: 'rho',
    0x03C2: ('sigma1', 'sigmafinal'),
    0x03C3: 'sigma',
    0x03C4: 'tau',
    0x03C5: 'upsilon',
    0x03C6: 'phi',
    0x03C7: 'chi',
    0x03C8: 'psi',
    0x03C9: 'omega',
    0x03CA: 'iotadieresis',
    0x03CB: 'upsilondieresis',
    0x03CC: 'omicrontonos',
    0x03CD: 'upsilontonos',
    0x03CE: 'omegatonos',
    0x03D0: 'betasymbolgreek',
    0x03D1: ('theta1', 'thetasymbolgreek'),
    0x03D2: ('Upsilon1', 'Upsilonhooksymbol'),
    0x03D3: 'Upsilonacutehooksymbolgreek',
    0x03D4: 'Upsilondieresishooksymbolgreek',
    0x03D5: ('phi1', 'phisymbolgreek'),
    0x03D6: ('omega1', 'pisymbolgreek'),
    0x03DA: 'Stigmagreek',
    0x03DC: 'Digammagreek',
    0x03DE: 'Koppagreek',
    0x03E0: 'Sampigreek',
    0x03E2: 'Sheicoptic',
    0x03E3: 'sheicoptic',
    0x03E4: 'Feicoptic',
    0x03E5: 'feicoptic',
    0x03E6: 'Kheicoptic',
    0x03E7: 'kheicoptic',
    0x03E8: 'Horicoptic',
    0x03E9: 'horicoptic',
    0x03EA: 'Gangiacoptic',
    0x03EB: 'gangiacoptic',
    0x03EC: 'Shimacoptic',
    0x03ED: 'shimacoptic',
    0x03EE: 'Deicoptic',
    0x03EF: 'deicoptic',
    0x03F0: 'kappasymbolgreek',
    0x03F1: 'rhosymbolgreek',
    0x03F2: 'sigmalunatesymbolgreek',
    0x03F3: 'yotgreek',
    0x0401: ('afii10023', 'Iocyrillic'),
    0x0402: ('afii10051', 'Djecyrillic'),
    0x0403: ('afii10052', 'Gjecyrillic'),
    0x0404: ('afii10053', 'Ecyrillic'),
    0x0405: ('afii10054', 'Dzecyrillic'),
    0x0406: ('afii10055', 'Icyrillic'),
    0x0407: ('afii10056', 'Yicyrillic'),
    0x0408: ('afii10057', 'Jecyrillic'),
    0x0409: ('afii10058', 'Ljecyrillic'),
    0x040A: ('afii10059', 'Njecyrillic'),
    0x040B: ('afii10060', 'Tshecyrillic'),
    0x040C: ('afii10061', 'Kjecyrillic'),
    0x040E: ('afii10062', 'Ushortcyrillic'),
    0x040F: ('afii10145', 'Dzhecyrillic'),
    0x0410: ('Acyrillic', 'afii10017'),
    0x0411: ('afii10018', 'Becyrillic'),
    0x0412: ('afii10019', 'Vecyrillic'),
    0x0413: ('afii10020', 'Gecyrillic'),
    0x0414: ('afii10021', 'Decyrillic'),
    0x0415: ('afii10022', 'Iecyrillic'),
    0x0416: ('afii10024', 'Zhecyrillic'),
    0x0417: ('afii10025', 'Zecyrillic'),
    0x0418: ('afii10026', 'Iicyrillic'),
    0x0419: ('afii10027', 'Iishortcyrillic'),
    0x041A: ('afii10028', 'Kacyrillic'),
    0x041B: ('afii10029', 'Elcyrillic'),
    0x041C: ('afii10030', 'Emcyrillic'),
    0x041D: ('afii10031', 'Encyrillic'),
    0x041E: ('afii10032', 'Ocyrillic'),
    0x041F: ('afii10033', 'Pecyrillic'),
    0x0420: ('afii10034', 'Ercyrillic'),
    0x0421: ('afii10035', 'Escyrillic'),
    0x0422: ('afii10036', 'Tecyrillic'),
    0x0423: ('afii10037', 'Ucyrillic'),
    0x0424: ('afii10038', 'Efcyrillic'),
    0x0425: ('afii10039', 'Khacyrillic'),
    0x0426: ('afii10040', 'Tsecyrillic'),
    0x0427: ('afii10041', 'Checyrillic'),
    0x0428: ('afii10042', 'Shacyrillic'),
    0x0429: ('afii10043', 'Shchacyrillic'),
    0x042A: ('afii10044', 'Hardsigncyrillic'),
    0x042B: ('afii10045', 'Yericyrillic'),
    0x042C: ('afii10046', 'Softsigncyrillic'),
    0x042D: ('afii10047', 'Ereversedcyrillic'),
    0x042E: ('afii10048', 'IUcyrillic'),
    0x042F: ('afii10049', 'IAcyrillic'),
    0x0430: ('acyrillic', 'afii10065'),
    0x0431: ('afii10066', 'becyrillic'),
    0x0432: ('afii10067', 'vecyrillic'),
    0x0433: ('afii10068', 'gecyrillic'),
    0x0434: ('afii10069', 'decyrillic'),
    0x0435: ('afii10070', 'iecyrillic'),
    0x0436: ('afii10072', 'zhecyrillic'),
    0x0437: ('afii10073', 'zecyrillic'),
    0x0438: ('afii10074', 'iicyrillic'),
    0x0439: ('afii10075', 'iishortcyrillic'),
    0x043A: ('afii10076', 'kacyrillic'),
    0x043B: ('afii10077', 'elcyrillic'),
    0x043C: ('afii10078', 'emcyrillic'),
    0x043D: ('afii10079', 'encyrillic'),
    0x043E: ('afii10080', 'ocyrillic'),
    0x043F: ('afii10081', 'pecyrillic'),
    0x0440: ('afii10082', 'ercyrillic'),
    0x0441: ('afii10083', 'escyrillic'),
    0x0442: ('afii10084', 'tecyrillic'),
    0x0443: ('afii10085', 'ucyrillic'),
    0x0444: ('afii10086', 'efcyrillic'),
    0x0445: ('afii10087', 'khacyrillic'),
    0x0446: ('afii10088', 'tsecyrillic'),
    0x0447: ('afii10089', 'checyrillic'),
    0x0448: ('afii10090', 'shacyrillic'),
    0x0449: ('afii10091', 'shchacyrillic'),
    0x044A: ('afii10092', 'hardsigncyrillic'),
    0x044B: ('afii10093', 'yericyrillic'),
    0x044C: ('afii10094', 'softsigncyrillic'),
    0x044D: ('afii10095', 'ereversedcyrillic'),
    0x044E: ('afii10096', 'iucyrillic'),
    0x044F: ('afii10097', 'iacyrillic'),
    0x0451: ('afii10071', 'iocyrillic'),
    0x0452: ('afii10099', 'djecyrillic'),
    0x0453: ('afii10100', 'gjecyrillic'),
    0x0454: ('afii10101', 'ecyrillic'),
    0x0455: ('afii10102', 'dzecyrillic'),
    0x0456: ('afii10103', 'icyrillic'),
    0x0457: ('afii10104', 'yicyrillic'),
    0x0458: ('afii10105', 'jecyrillic'),
    0x0459: ('afii10106', 'ljecyrillic'),
    0x045A: ('afii10107', 'njecyrillic'),
    0x045B: ('afii10108', 'tshecyrillic'),
    0x045C: ('afii10109', 'kjecyrillic'),
    0x045E: ('afii10110', 'ushortcyrillic'),
    0x045F: ('afii10193', 'dzhecyrillic'),
    0x0460: 'Omegacyrillic',
    0x0461: 'omegacyrillic',
    0x0462: ('afii10146', 'Yatcyrillic'),
    0x0463: ('afii10194', 'yatcyrillic'),
    0x0464: 'Eiotifiedcyrillic',
    0x0465: 'eiotifiedcyrillic',
    0x0466: 'Yuslittlecyrillic',
    0x0467: 'yuslittlecyrillic',
    0x0468: 'Yuslittleiotifiedcyrillic',
    0x0469: 'yuslittleiotifiedcyrillic',
    0x046A: 'Yusbigcyrillic',
    0x046B: 'yusbigcyrillic',
    0x046C: 'Yusbigiotifiedcyrillic',
    0x046D: 'yusbigiotifiedcyrillic',
    0x046E: 'Ksicyrillic',
    0x046F: 'ksicyrillic',
    0x0470: 'Psicyrillic',
    0x0471: 'psicyrillic',
    0x0472: ('afii10147', 'Fitacyrillic'),
    0x0473: ('afii10195', 'fitacyrillic'),
    0x0474: ('afii10148', 'Izhitsacyrillic'),
    0x0475: ('afii10196', 'izhitsacyrillic'),
    0x0476: 'Izhitsadblgravecyrillic',
    0x0477: 'izhitsadblgravecyrillic',
    0x0478: 'Ukcyrillic',
    0x0479: 'ukcyrillic',
    0x047A: 'Omegaroundcyrillic',
    0x047B: 'omegaroundcyrillic',
    0x047C: 'Omegatitlocyrillic',
    0x047D: 'omegatitlocyrillic',
    0x047E: 'Otcyrillic',
    0x047F: 'otcyrillic',
    0x0480: 'Koppacyrillic',
    0x0481: 'koppacyrillic',
    0x0482: 'thousandcyrillic',
    0x0483: 'titlocyrilliccmb',
    0x0484: 'palatalizationcyrilliccmb',
    0x0485: 'dasiapneumatacyrilliccmb',
    0x0486: 'psilipneumatacyrilliccmb',
    0x0490: ('afii10050', 'Gheupturncyrillic'),
    0x0491: ('afii10098', 'gheupturncyrillic'),
    0x0492: 'Ghestrokecyrillic',
    0x0493: 'ghestrokecyrillic',
    0x0494: 'Ghemiddlehookcyrillic',
    0x0495: 'ghemiddlehookcyrillic',
    0x0496: 'Zhedescendercyrillic',
    0x0497: 'zhedescendercyrillic',
    0x0498: 'Zedescendercyrillic',
    0x0499: 'zedescendercyrillic',
    0x049A: 'Kadescendercyrillic',
    0x049B: 'kadescendercyrillic',
    0x049C: 'Kaverticalstrokecyrillic',
    0x049D: 'kaverticalstrokecyrillic',
    0x049E: 'Kastrokecyrillic',
    0x049F: 'kastrokecyrillic',
    0x04A0: 'Kabashkircyrillic',
    0x04A1: 'kabashkircyrillic',
    0x04A2: 'Endescendercyrillic',
    0x04A3: 'endescendercyrillic',
    0x04A4: 'Enghecyrillic',
    0x04A5: 'enghecyrillic',
    0x04A6: 'Pemiddlehookcyrillic',
    0x04A7: 'pemiddlehookcyrillic',
    0x04A8: 'Haabkhasiancyrillic',
    0x04A9: 'haabkhasiancyrillic',
    0x04AA: 'Esdescendercyrillic',
    0x04AB: 'esdescendercyrillic',
    0x04AC: 'Tedescendercyrillic',
    0x04AD: 'tedescendercyrillic',
    0x04AE: 'Ustraightcyrillic',
    0x04AF: 'ustraightcyrillic',
    0x04B0: 'Ustraightstrokecyrillic',
    0x04B1: 'ustraightstrokecyrillic',
    0x04B2: 'Hadescendercyrillic',
    0x04B3: 'hadescendercyrillic',
    0x04B4: 'Tetsecyrillic',
    0x04B5: 'tetsecyrillic',
    0x04B6: 'Chedescendercyrillic',
    0x04B7: 'chedescendercyrillic',
    0x04B8: 'Cheverticalstrokecyrillic',
    0x04B9: 'cheverticalstrokecyrillic',
    0x04BA: 'Shhacyrillic',
    0x04BB: 'shhacyrillic',
    0x04BC: 'Cheabkhasiancyrillic',
    0x04BD: 'cheabkhasiancyrillic',
    0x04BE: 'Chedescenderabkhasiancyrillic',
    0x04BF: 'chedescenderabkhasiancyrillic',
    0x04C0: 'palochkacyrillic',
    0x04C1: 'Zhebrevecyrillic',
    0x04C2: 'zhebrevecyrillic',
    0x04C3: 'Kahookcyrillic',
    0x04C4: 'kahookcyrillic',
    0x04C7: 'Enhookcyrillic',
    0x04C8: 'enhookcyrillic',
    0x04CB: 'Chekhakassiancyrillic',
    0x04CC: 'chekhakassiancyrillic',
    0x04D0: 'Abrevecyrillic',
    0x04D1: 'abrevecyrillic',
    0x04D2: 'Adieresiscyrillic',
    0x04D3: 'adieresiscyrillic',
    0x04D4: 'Aiecyrillic',
    0x04D5: 'aiecyrillic',
    0x04D6: 'Iebrevecyrillic',
    0x04D7: 'iebrevecyrillic',
    0x04D8: 'Schwacyrillic',
    0x04D9: ('afii10846', 'schwacyrillic'),
    0x04DA: 'Schwadieresiscyrillic',
    0x04DB: 'schwadieresiscyrillic',
    0x04DC: 'Zhedieresiscyrillic',
    0x04DD: 'zhedieresiscyrillic',
    0x04DE: 'Zedieresiscyrillic',
    0x04DF: 'zedieresiscyrillic',
    0x04E0: 'Dzeabkhasiancyrillic',
    0x04E1: 'dzeabkhasiancyrillic',
    0x04E2: 'Imacroncyrillic',
    0x04E3: 'imacroncyrillic',
    0x04E4: 'Idieresiscyrillic',
    0x04E5: 'idieresiscyrillic',
    0x04E6: 'Odieresiscyrillic',
    0x04E7: 'odieresiscyrillic',
    0x04E8: 'Obarredcyrillic',
    0x04E9: 'obarredcyrillic',
    0x04EA: 'Obarreddieresiscyrillic',
    0x04EB: 'obarreddieresiscyrillic',
    0x04EE: 'Umacroncyrillic',
    0x04EF: 'umacroncyrillic',
    0x04F0: 'Udieresiscyrillic',
    0x04F1: 'udieresiscyrillic',
    0x04F2: 'Uhungarumlautcyrillic',
    0x04F3: 'uhungarumlautcyrillic',
    0x04F4: 'Chedieresiscyrillic',
    0x04F5: 'chedieresiscyrillic',
    0x04F8: 'Yerudieresiscyrillic',
    0x04F9: 'yerudieresiscyrillic',
    0x0531: 'Aybarmenian',
    0x0532: 'Benarmenian',
    0x0533: 'Gimarmenian',
    0x0534: 'Daarmenian',
    0x0535: 'Echarmenian',
    0x0536: 'Zaarmenian',
    0x0537: 'Eharmenian',
    0x0538: 'Etarmenian',
    0x0539: 'Toarmenian',
    0x053A: 'Zhearmenian',
    0x053B: 'Iniarmenian',
    0x053C: 'Liwnarmenian',
    0x053D: 'Xeharmenian',
    0x053E: 'Caarmenian',
    0x053F: 'Kenarmenian',
    0x0540: 'Hoarmenian',
    0x0541: 'Jaarmenian',
    0x0542: 'Ghadarmenian',
    0x0543: 'Cheharmenian',
    0x0544: 'Menarmenian',
    0x0545: 'Yiarmenian',
    0x0546: 'Nowarmenian',
    0x0547: 'Shaarmenian',
    0x0548: 'Voarmenian',
    0x0549: 'Chaarmenian',
    0x054A: 'Peharmenian',
    0x054B: 'Jheharmenian',
    0x054C: 'Raarmenian',
    0x054D: 'Seharmenian',
    0x054E: 'Vewarmenian',
    0x054F: 'Tiwnarmenian',
    0x0550: 'Reharmenian',
    0x0551: 'Coarmenian',
    0x0552: 'Yiwnarmenian',
    0x0553: 'Piwrarmenian',
    0x0554: 'Keharmenian',
    0x0555: 'Oharmenian',
    0x0556: 'Feharmenian',
    0x0559: 'ringhalfleftarmenian',
    0x055A: 'apostrophearmenian',
    0x055B: 'emphasismarkarmenian',
    0x055C: 'exclamarmenian',
    0x055D: 'commaarmenian',
    0x055E: 'questionarmenian',
    0x055F: 'abbreviationmarkarmenian',
    0x0561: 'aybarmenian',
    0x0562: 'benarmenian',
    0x0563: 'gimarmenian',
    0x0564: 'daarmenian',
    0x0565: 'echarmenian',
    0x0566: 'zaarmenian',
    0x0567: 'eharmenian',
    0x0568: 'etarmenian',
    0x0569: 'toarmenian',
    0x056A: 'zhearmenian',
    0x056B: 'iniarmenian',
    0x056C: 'liwnarmenian',
    0x056D: 'xeharmenian',
    0x056E: 'caarmenian',
    0x056F: 'kenarmenian',
    0x0570: 'hoarmenian',
    0x0571: 'jaarmenian',
    0x0572: 'ghadarmenian',
    0x0573: 'cheharmenian',
    0x0574: 'menarmenian',
    0x0575: 'yiarmenian',
    0x0576: 'nowarmenian',
    0x0577: 'shaarmenian',
    0x0578: 'voarmenian',
    0x0579: 'chaarmenian',
    0x057A: 'peharmenian',
    0x057B: 'jheharmenian',
    0x057C: 'raarmenian',
    0x057D: 'seharmenian',
    0x057E: 'vewarmenian',
    0x057F: 'tiwnarmenian',
    0x0580: 'reharmenian',
    0x0581: 'coarmenian',
    0x0582: 'yiwnarmenian',
    0x0583: 'piwrarmenian',
    0x0584: 'keharmenian',
    0x0585: 'oharmenian',
    0x0586: 'feharmenian',
    0x0587: 'echyiwnarmenian',
    0x0589: 'periodarmenian',
    0x0591: ('etnahtafoukhhebrew', 'etnahtafoukhlefthebrew', 'etnahtahebrew',
             'etnahtalefthebrew'),
    0x0592: 'segoltahebrew',
    0x0593: 'shalshelethebrew',
    0x0594: 'zaqefqatanhebrew',
    0x0595: 'zaqefgadolhebrew',
    0x0596: ('tipehahebrew', 'tipehalefthebrew'),
    0x0597: ('reviahebrew', 'reviamugrashhebrew'),
    0x0598: 'zarqahebrew',
    0x0599: 'pashtahebrew',
    0x059A: 'yetivhebrew',
    0x059B: ('tevirhebrew', 'tevirlefthebrew'),
    0x059C: 'gereshaccenthebrew',
    0x059D: 'gereshmuqdamhebrew',
    0x059E: 'gershayimaccenthebrew',
    0x059F: 'qarneyparahebrew',
    0x05A0: 'telishagedolahebrew',
    0x05A1: 'pazerhebrew',
    0x05A3: ('munahhebrew', 'munahlefthebrew'),
    0x05A4: ('mahapakhhebrew', 'mahapakhlefthebrew'),
    0x05A5: ('merkhahebrew', 'merkhalefthebrew'),
    0x05A6: ('merkhakefulahebrew', 'merkhakefulalefthebrew'),
    0x05A7: ('dargahebrew', 'dargalefthebrew'),
    0x05A8: 'qadmahebrew',
    0x05A9: 'telishaqetanahebrew',
    0x05AA: ('yerahbenyomohebrew', 'yerahbenyomolefthebrew'),
    0x05AB: 'olehebrew',
    0x05AC: 'iluyhebrew',
    0x05AD: 'dehihebrew',
    0x05AE: 'zinorhebrew',
    0x05AF: 'masoracirclehebrew',
    0x05B0: ('afii57799', 'sheva', 'sheva115', 'sheva15', 'sheva22', 'sheva2e',
             'shevahebrew', 'shevanarrowhebrew', 'shevaquarterhebrew',
             'shevawidehebrew'),
    0x05B1: ('afii57801', 'hatafsegol', 'hatafsegol17', 'hatafsegol24',
             'hatafsegol30', 'hatafsegolhebrew', 'hatafsegolnarrowhebrew',
             'hatafsegolquarterhebrew', 'hatafsegolwidehebrew'),
    0x05B2: ('afii57800', 'hatafpatah', 'hatafpatah16', 'hatafpatah23',
             'hatafpatah2f', 'hatafpatahhebrew', 'hatafpatahnarrowhebrew',
             'hatafpatahquarterhebrew', 'hatafpatahwidehebrew'),
    0x05B3: ('afii57802', 'hatafqamats', 'hatafqamats1b', 'hatafqamats28',
             'hatafqamats34', 'hatafqamatshebrew', 'hatafqamatsnarrowhebrew',
             'hatafqamatsquarterhebrew', 'hatafqamatswidehebrew'),
    0x05B4: ('afii57793', 'hiriq', 'hiriq14', 'hiriq21', 'hiriq2d',
             'hiriqhebrew', 'hiriqnarrowhebrew', 'hiriqquarterhebrew',
             'hiriqwidehebrew'),
    0x05B5: ('afii57794', 'tsere', 'tsere12', 'tsere1e', 'tsere2b',
             'tserehebrew', 'tserenarrowhebrew', 'tserequarterhebrew',
             'tserewidehebrew'),
    0x05B6: ('afii57795', 'segol', 'segol13', 'segol1f', 'segol2c',
             'segolhebrew', 'segolnarrowhebrew', 'segolquarterhebrew',
             'segolwidehebrew'),
    0x05B7: ('afii57798', 'patah', 'patah11', 'patah1d', 'patah2a',
             'patahhebrew', 'patahnarrowhebrew', 'patahquarterhebrew',
             'patahwidehebrew'),
    0x05B8: ('afii57797', 'qamats', 'qamats10', 'qamats1a', 'qamats1c',
             'qamats27', 'qamats29', 'qamats33', 'qamatsde', 'qamatshebrew',
             'qamatsnarrowhebrew', 'qamatsqatanhebrew',
             'qamatsqatannarrowhebrew', 'qamatsqatanquarterhebrew',
             'qamatsqatanwidehebrew', 'qamatsquarterhebrew',
             'qamatswidehebrew'),
    0x05B9: ('afii57806', 'holam', 'holam19', 'holam26', 'holam32',
             'holamhebrew', 'holamnarrowhebrew', 'holamquarterhebrew',
             'holamwidehebrew'),
    0x05BB: ('afii57796', 'qubuts', 'qubuts18', 'qubuts25', 'qubuts31',
             'qubutshebrew', 'qubutsnarrowhebrew', 'qubutsquarterhebrew',
             'qubutswidehebrew'),
    0x05BC: ('afii57807', 'dagesh', 'dageshhebrew'),
    0x05BD: ('afii57839', 'siluqhebrew', 'siluqlefthebrew'),
    0x05BE: ('afii57645', 'maqafhebrew'),
    0x05BF: ('afii57841', 'rafe', 'rafehebrew'),
    0x05C0: ('afii57842', 'paseqhebrew'),
    0x05C1: ('afii57804', 'shindothebrew'),
    0x05C2: ('afii57803', 'sindothebrew'),
    0x05C3: ('afii57658', 'sofpasuqhebrew'),
    0x05C4: 'upperdothebrew',
    0x05D0: ('afii57664', 'alef', 'alefhebrew'),
    0x05D1: ('afii57665', 'bet', 'bethebrew'),
    0x05D2: ('afii57666', 'gimel', 'gimelhebrew'),
    0x05D3: ('afii57667', 'dalet', 'dalethebrew'),
#    0x05D3 05B0: 'daletsheva',
#    0x05D3 05B0: 'daletshevahebrew',
#    0x05D3 05B1: 'dalethatafsegol',
#    0x05D3 05B1: 'dalethatafsegolhebrew',
#    0x05D3 05B2: 'dalethatafpatah',
#    0x05D3 05B2: 'dalethatafpatahhebrew',
#    0x05D3 05B4: 'dalethiriq',
#    0x05D3 05B4: 'dalethiriqhebrew',
#    0x05D3 05B5: 'dalettsere',
#    0x05D3 05B5: 'dalettserehebrew',
#    0x05D3 05B6: 'daletsegol',
#    0x05D3 05B6: 'daletsegolhebrew',
#    0x05D3 05B7: 'daletpatah',
#    0x05D3 05B7: 'daletpatahhebrew',
#    0x05D3 05B8: 'daletqamats',
#    0x05D3 05B8: 'daletqamatshebrew',
#    0x05D3 05B9: 'daletholam',
#    0x05D3 05B9: 'daletholamhebrew',
#    0x05D3 05BB: 'daletqubuts',
#    0x05D3 05BB: 'daletqubutshebrew',
    0x05D4: ('afii57668', 'he', 'hehebrew'),
    0x05D5: ('afii57669', 'vav', 'vavhebrew'),
    0x05D6: ('afii57670', 'zayin', 'zayinhebrew'),
    0x05D7: ('afii57671', 'het', 'hethebrew'),
    0x05D8: ('afii57672', 'tet', 'tethebrew'),
    0x05D9: ('afii57673', 'yod', 'yodhebrew'),
    0x05DA: ('afii57674', 'finalkaf', 'finalkafhebrew'),
#    0x05DA 05B0: 'finalkafsheva',
#    0x05DA 05B0: 'finalkafshevahebrew',
#    0x05DA 05B8: 'finalkafqamats',
#    0x05DA 05B8: 'finalkafqamatshebrew',
    0x05DB: ('afii57675', 'kaf', 'kafhebrew'),
    0x05DC: ('afii57676', 'lamed', 'lamedhebrew'),
#    0x05DC 05B9 05BC: 'lamedholamdagesh',
#    0x05DC 05B9 05BC: 'lamedholamdageshhebrew',
#    0x05DC 05B9: 'lamedholam',
#    0x05DC 05B9: 'lamedholamhebrew',
    0x05DD: ('afii57677', 'finalmem', 'finalmemhebrew'),
    0x05DE: ('afii57678', 'mem', 'memhebrew'),
    0x05DF: ('afii57679', 'finalnun', 'finalnunhebrew'),
    0x05E0: ('afii57680', 'nun', 'nunhebrew'),
    0x05E1: ('afii57681', 'samekh', 'samekhhebrew'),
    0x05E2: ('afii57682', 'ayin', 'ayinhebrew'),
    0x05E3: ('afii57683', 'finalpe', 'finalpehebrew'),
    0x05E4: ('afii57684', 'pe', 'pehebrew'),
    0x05E5: ('afii57685', 'finaltsadi', 'finaltsadihebrew'),
    0x05E6: ('afii57686', 'tsadi', 'tsadihebrew'),
    0x05E7: ('afii57687', 'qof', 'qofhebrew'),
#    0x05E7 05B0: 'qofsheva',
#    0x05E7 05B0: 'qofshevahebrew',
#    0x05E7 05B1: 'qofhatafsegol',
#    0x05E7 05B1: 'qofhatafsegolhebrew',
#    0x05E7 05B2: 'qofhatafpatah',
#    0x05E7 05B2: 'qofhatafpatahhebrew',
#    0x05E7 05B4: 'qofhiriq',
#    0x05E7 05B4: 'qofhiriqhebrew',
#    0x05E7 05B5: 'qoftsere',
#    0x05E7 05B5: 'qoftserehebrew',
#    0x05E7 05B6: 'qofsegol',
#    0x05E7 05B6: 'qofsegolhebrew',
#    0x05E7 05B7: 'qofpatah',
#    0x05E7 05B7: 'qofpatahhebrew',
#    0x05E7 05B8: 'qofqamats',
#    0x05E7 05B8: 'qofqamatshebrew',
#    0x05E7 05B9: 'qofholam',
#    0x05E7 05B9: 'qofholamhebrew',
#    0x05E7 05BB: 'qofqubuts',
#    0x05E7 05BB: 'qofqubutshebrew',
    0x05E8: ('afii57688', 'resh', 'reshhebrew'),
#    0x05E8 05B0: 'reshsheva',
#    0x05E8 05B0: 'reshshevahebrew',
#    0x05E8 05B1: 'reshhatafsegol',
#    0x05E8 05B1: 'reshhatafsegolhebrew',
#    0x05E8 05B2: 'reshhatafpatah',
#    0x05E8 05B2: 'reshhatafpatahhebrew',
#    0x05E8 05B4: 'reshhiriq',
#    0x05E8 05B4: 'reshhiriqhebrew',
#    0x05E8 05B5: 'reshtsere',
#    0x05E8 05B5: 'reshtserehebrew',
#    0x05E8 05B6: 'reshsegol',
#    0x05E8 05B6: 'reshsegolhebrew',
#    0x05E8 05B7: 'reshpatah',
#    0x05E8 05B7: 'reshpatahhebrew',
#    0x05E8 05B8: 'reshqamats',
#    0x05E8 05B8: 'reshqamatshebrew',
#    0x05E8 05B9: 'reshholam',
#    0x05E8 05B9: 'reshholamhebrew',
#    0x05E8 05BB: 'reshqubuts',
#    0x05E8 05BB: 'reshqubutshebrew',
    0x05E9: ('afii57689', 'shin', 'shinhebrew'),
    0x05EA: ('afii57690', 'tav', 'tavhebrew'),
    0x05F0: ('afii57716', 'vavvavhebrew'),
    0x05F1: ('afii57717', 'vavyodhebrew'),
    0x05F2: ('afii57718', 'yodyodhebrew'),
    0x05F3: 'gereshhebrew',
    0x05F4: 'gershayimhebrew',
    0x060C: ('afii57388', 'commaarabic'),
    0x061B: ('afii57403', 'semicolonarabic'),
    0x061F: ('afii57407', 'questionarabic'),
    0x0621: ('afii57409', 'hamzaarabic', 'hamzalowarabic'),
#    0x0621 064B: 'hamzafathatanarabic',
#    0x0621 064C: 'hamzadammatanarabic',
#    0x0621 064D: 'hamzalowkasratanarabic',
#    0x0621 064E: 'hamzafathaarabic',
#    0x0621 064F: 'hamzadammaarabic',
#    0x0621 0650: 'hamzalowkasraarabic',
#    0x0621 0652: 'hamzasukunarabic',
    0x0622: ('afii57410', 'alefmaddaabovearabic'),
    0x0623: ('afii57411', 'alefhamzaabovearabic'),
    0x0624: ('afii57412', 'wawhamzaabovearabic'),
    0x0625: ('afii57413', 'alefhamzabelowarabic'),
    0x0626: ('afii57414', 'yehhamzaabovearabic'),
    0x0627: ('afii57415', 'alefarabic'),
    0x0628: ('afii57416', 'beharabic'),
    0x0629: ('afii57417', 'tehmarbutaarabic'),
    0x062A: ('afii57418', 'teharabic'),
    0x062B: ('afii57419', 'theharabic'),
    0x062C: ('afii57420', 'jeemarabic'),
    0x062D: ('afii57421', 'haharabic'),
    0x062E: ('afii57422', 'khaharabic'),
    0x062F: ('afii57423', 'dalarabic'),
    0x0630: ('afii57424', 'thalarabic'),
    0x0631: ('afii57425', 'reharabic'),
#    0x0631 FEF3 FE8E 0644: 'rehyehaleflamarabic',
    0x0632: ('afii57426', 'zainarabic'),
    0x0633: ('afii57427', 'seenarabic'),
    0x0634: ('afii57428', 'sheenarabic'),
    0x0635: ('afii57429', 'sadarabic'),
    0x0636: ('afii57430', 'dadarabic'),
    0x0637: ('afii57431', 'taharabic'),
    0x0638: ('afii57432', 'zaharabic'),
    0x0639: ('afii57433', 'ainarabic'),
    0x063A: ('afii57434', 'ghainarabic'),
    0x0640: ('afii57440', 'kashidaautoarabic', 'kashidaautonosidebearingarabic',
             'tatweelarabic'),
    0x0641: ('afii57441', 'feharabic'),
    0x0642: ('afii57442', 'qafarabic'),
    0x0643: ('afii57443', 'kafarabic'),
    0x0644: ('afii57444', 'lamarabic'),
    0x0645: ('afii57445', 'meemarabic'),
    0x0646: ('afii57446', 'noonarabic'),
    0x0647: ('afii57470', 'heharabic'),
    0x0648: ('afii57448', 'wawarabic'),
    0x0649: ('afii57449', 'alefmaksuraarabic'),
    0x064A: ('afii57450', 'yeharabic'),
    0x064B: ('afii57451', 'fathatanarabic'),
    0x064C: ('afii57452', 'dammatanaltonearabic', 'dammatanarabic'),
    0x064D: ('afii57453', 'kasratanarabic'),
    0x064E: ('afii57454', 'fathaarabic', 'fathalowarabic'),
    0x064F: ('afii57455', 'dammaarabic', 'dammalowarabic'),
    0x0650: ('afii57456', 'kasraarabic'),
    0x0651: ('afii57457', 'shaddaarabic'),
#    0x0651 064B: 'shaddafathatanarabic',
    0x0652: ('afii57458', 'sukunarabic'),
    0x0660: ('afii57392', 'zeroarabic', 'zerohackarabic'),
    0x0661: ('afii57393', 'onearabic', 'onehackarabic'),
    0x0662: ('afii57394', 'twoarabic', 'twohackarabic'),
    0x0663: ('afii57395', 'threearabic', 'threehackarabic'),
    0x0664: ('afii57396', 'fourarabic', 'fourhackarabic'),
    0x0665: ('afii57397', 'fivearabic', 'fivehackarabic'),
    0x0666: ('afii57398', 'sixarabic', 'sixhackarabic'),
    0x0667: ('afii57399', 'sevenarabic', 'sevenhackarabic'),
    0x0668: ('afii57400', 'eightarabic', 'eighthackarabic'),
    0x0669: ('afii57401', 'ninearabic', 'ninehackarabic'),
    0x066A: ('afii57381', 'percentarabic'),
    0x066B: ('decimalseparatorarabic', 'decimalseparatorpersian'),
    0x066C: ('thousandsseparatorarabic', 'thousandsseparatorpersian'),
    0x066D: ('afii63167', 'asteriskaltonearabic', 'asteriskarabic'),
    0x0679: ('afii57511', 'tteharabic'),
    0x067E: ('afii57506', 'peharabic'),
    0x0686: ('afii57507', 'tcheharabic'),
    0x0688: ('afii57512', 'ddalarabic'),
    0x0691: ('afii57513', 'rreharabic'),
    0x0698: ('afii57508', 'jeharabic'),
    0x06A4: ('afii57505', 'veharabic'),
    0x06AF: ('afii57509', 'gafarabic'),
    0x06BA: ('afii57514', 'noonghunnaarabic'),
    0x06C1: ('haaltonearabic', 'hehaltonearabic'),
    0x06D1: 'yehthreedotsbelowarabic',
    0x06D2: ('afii57519', 'yehbarreearabic'),
    0x06D5: 'afii57534',
    0x06F0: 'zeropersian',
    0x06F1: 'onepersian',
    0x06F2: 'twopersian',
    0x06F3: 'threepersian',
    0x06F4: 'fourpersian',
    0x06F5: 'fivepersian',
    0x06F6: 'sixpersian',
    0x06F7: 'sevenpersian',
    0x06F8: 'eightpersian',
    0x06F9: 'ninepersian',
    0x0901: 'candrabindudeva',
    0x0902: 'anusvaradeva',
    0x0903: 'visargadeva',
    0x0905: 'adeva',
    0x0906: 'aadeva',
    0x0907: 'ideva',
    0x0908: 'iideva',
    0x0909: 'udeva',
    0x090A: 'uudeva',
    0x090B: 'rvocalicdeva',
    0x090C: 'lvocalicdeva',
    0x090D: 'ecandradeva',
    0x090E: 'eshortdeva',
    0x090F: 'edeva',
    0x0910: 'aideva',
    0x0911: 'ocandradeva',
    0x0912: 'oshortdeva',
    0x0913: 'odeva',
    0x0914: 'audeva',
    0x0915: 'kadeva',
    0x0916: 'khadeva',
    0x0917: 'gadeva',
    0x0918: 'ghadeva',
    0x0919: 'ngadeva',
    0x091A: 'cadeva',
    0x091B: 'chadeva',
    0x091C: 'jadeva',
    0x091D: 'jhadeva',
    0x091E: 'nyadeva',
    0x091F: 'ttadeva',
    0x0920: 'tthadeva',
    0x0921: 'ddadeva',
    0x0922: 'ddhadeva',
    0x0923: 'nnadeva',
    0x0924: 'tadeva',
    0x0925: 'thadeva',
    0x0926: 'dadeva',
    0x0927: 'dhadeva',
    0x0928: 'nadeva',
    0x0929: 'nnnadeva',
    0x092A: 'padeva',
    0x092B: 'phadeva',
    0x092C: 'badeva',
    0x092D: 'bhadeva',
    0x092E: 'madeva',
    0x092F: 'yadeva',
    0x0930: 'radeva',
    0x0931: 'rradeva',
    0x0932: 'ladeva',
    0x0933: 'lladeva',
    0x0934: 'llladeva',
    0x0935: 'vadeva',
    0x0936: 'shadeva',
    0x0937: 'ssadeva',
    0x0938: 'sadeva',
    0x0939: 'hadeva',
    0x093C: 'nuktadeva',
    0x093D: 'avagrahadeva',
    0x093E: 'aavowelsigndeva',
    0x093F: 'ivowelsigndeva',
    0x0940: 'iivowelsigndeva',
    0x0941: 'uvowelsigndeva',
    0x0942: 'uuvowelsigndeva',
    0x0943: 'rvocalicvowelsigndeva',
    0x0944: 'rrvocalicvowelsigndeva',
    0x0945: 'ecandravowelsigndeva',
    0x0946: 'eshortvowelsigndeva',
    0x0947: 'evowelsigndeva',
    0x0948: 'aivowelsigndeva',
    0x0949: 'ocandravowelsigndeva',
    0x094A: 'oshortvowelsigndeva',
    0x094B: 'ovowelsigndeva',
    0x094C: 'auvowelsigndeva',
    0x094D: 'viramadeva',
    0x0950: 'omdeva',
    0x0951: 'udattadeva',
    0x0952: 'anudattadeva',
    0x0953: 'gravedeva',
    0x0954: 'acutedeva',
    0x0958: 'qadeva',
    0x0959: 'khhadeva',
    0x095A: 'ghhadeva',
    0x095B: 'zadeva',
    0x095C: 'dddhadeva',
    0x095D: 'rhadeva',
    0x095E: 'fadeva',
    0x095F: 'yyadeva',
    0x0960: 'rrvocalicdeva',
    0x0961: 'llvocalicdeva',
    0x0962: 'lvocalicvowelsigndeva',
    0x0963: 'llvocalicvowelsigndeva',
    0x0964: 'danda',
    0x0965: 'dbldanda',
    0x0966: 'zerodeva',
    0x0967: 'onedeva',
    0x0968: 'twodeva',
    0x0969: 'threedeva',
    0x096A: 'fourdeva',
    0x096B: 'fivedeva',
    0x096C: 'sixdeva',
    0x096D: 'sevendeva',
    0x096E: 'eightdeva',
    0x096F: 'ninedeva',
    0x0970: 'abbreviationsigndeva',
    0x0981: 'candrabindubengali',
    0x0982: 'anusvarabengali',
    0x0983: 'visargabengali',
    0x0985: 'abengali',
    0x0986: 'aabengali',
    0x0987: 'ibengali',
    0x0988: 'iibengali',
    0x0989: 'ubengali',
    0x098A: 'uubengali',
    0x098B: 'rvocalicbengali',
    0x098C: 'lvocalicbengali',
    0x098F: 'ebengali',
    0x0990: 'aibengali',
    0x0993: 'obengali',
    0x0994: 'aubengali',
    0x0995: 'kabengali',
    0x0996: 'khabengali',
    0x0997: 'gabengali',
    0x0998: 'ghabengali',
    0x0999: 'ngabengali',
    0x099A: 'cabengali',
    0x099B: 'chabengali',
    0x099C: 'jabengali',
    0x099D: 'jhabengali',
    0x099E: 'nyabengali',
    0x099F: 'ttabengali',
    0x09A0: 'tthabengali',
    0x09A1: 'ddabengali',
    0x09A2: 'ddhabengali',
    0x09A3: 'nnabengali',
    0x09A4: 'tabengali',
    0x09A5: 'thabengali',
    0x09A6: 'dabengali',
    0x09A7: 'dhabengali',
    0x09A8: 'nabengali',
    0x09AA: 'pabengali',
    0x09AB: 'phabengali',
    0x09AC: 'babengali',
    0x09AD: 'bhabengali',
    0x09AE: 'mabengali',
    0x09AF: 'yabengali',
    0x09B0: 'rabengali',
    0x09B2: 'labengali',
    0x09B6: 'shabengali',
    0x09B7: 'ssabengali',
    0x09B8: 'sabengali',
    0x09B9: 'habengali',
    0x09BC: 'nuktabengali',
    0x09BE: 'aavowelsignbengali',
    0x09BF: 'ivowelsignbengali',
    0x09C0: 'iivowelsignbengali',
    0x09C1: 'uvowelsignbengali',
    0x09C2: 'uuvowelsignbengali',
    0x09C3: 'rvocalicvowelsignbengali',
    0x09C4: 'rrvocalicvowelsignbengali',
    0x09C7: 'evowelsignbengali',
    0x09C8: 'aivowelsignbengali',
    0x09CB: 'ovowelsignbengali',
    0x09CC: 'auvowelsignbengali',
    0x09CD: 'viramabengali',
    0x09D7: 'aulengthmarkbengali',
    0x09DC: 'rrabengali',
    0x09DD: 'rhabengali',
    0x09DF: 'yyabengali',
    0x09E0: 'rrvocalicbengali',
    0x09E1: 'llvocalicbengali',
    0x09E2: 'lvocalicvowelsignbengali',
    0x09E3: 'llvocalicvowelsignbengali',
    0x09E6: 'zerobengali',
    0x09E7: 'onebengali',
    0x09E8: 'twobengali',
    0x09E9: 'threebengali',
    0x09EA: 'fourbengali',
    0x09EB: 'fivebengali',
    0x09EC: 'sixbengali',
    0x09ED: 'sevenbengali',
    0x09EE: 'eightbengali',
    0x09EF: 'ninebengali',
    0x09F0: 'ramiddlediagonalbengali',
    0x09F1: 'ralowerdiagonalbengali',
    0x09F2: 'rupeemarkbengali',
    0x09F3: 'rupeesignbengali',
    0x09F4: 'onenumeratorbengali',
    0x09F5: 'twonumeratorbengali',
    0x09F6: 'threenumeratorbengali',
    0x09F7: 'fournumeratorbengali',
    0x09F8: 'denominatorminusonenumeratorbengali',
    0x09F9: 'sixteencurrencydenominatorbengali',
    0x09FA: 'issharbengali',
    0x0A02: 'bindigurmukhi',
    0x0A05: 'agurmukhi',
    0x0A06: 'aagurmukhi',
    0x0A07: 'igurmukhi',
    0x0A08: 'iigurmukhi',
    0x0A09: 'ugurmukhi',
    0x0A0A: 'uugurmukhi',
    0x0A0F: 'eegurmukhi',
    0x0A10: 'aigurmukhi',
    0x0A13: 'oogurmukhi',
    0x0A14: 'augurmukhi',
    0x0A15: 'kagurmukhi',
    0x0A16: 'khagurmukhi',
    0x0A17: 'gagurmukhi',
    0x0A18: 'ghagurmukhi',
    0x0A19: 'ngagurmukhi',
    0x0A1A: 'cagurmukhi',
    0x0A1B: 'chagurmukhi',
    0x0A1C: 'jagurmukhi',
    0x0A1D: 'jhagurmukhi',
    0x0A1E: 'nyagurmukhi',
    0x0A1F: 'ttagurmukhi',
    0x0A20: 'tthagurmukhi',
    0x0A21: 'ddagurmukhi',
    0x0A22: 'ddhagurmukhi',
    0x0A23: 'nnagurmukhi',
    0x0A24: 'tagurmukhi',
    0x0A25: 'thagurmukhi',
    0x0A26: 'dagurmukhi',
    0x0A27: 'dhagurmukhi',
    0x0A28: 'nagurmukhi',
    0x0A2A: 'pagurmukhi',
    0x0A2B: 'phagurmukhi',
    0x0A2C: 'bagurmukhi',
    0x0A2D: 'bhagurmukhi',
    0x0A2E: 'magurmukhi',
    0x0A2F: 'yagurmukhi',
    0x0A30: 'ragurmukhi',
    0x0A32: 'lagurmukhi',
    0x0A35: 'vagurmukhi',
    0x0A36: 'shagurmukhi',
    0x0A38: 'sagurmukhi',
    0x0A39: 'hagurmukhi',
    0x0A3C: 'nuktagurmukhi',
    0x0A3E: 'aamatragurmukhi',
    0x0A3F: 'imatragurmukhi',
    0x0A40: 'iimatragurmukhi',
    0x0A41: 'umatragurmukhi',
    0x0A42: 'uumatragurmukhi',
    0x0A47: 'eematragurmukhi',
    0x0A48: 'aimatragurmukhi',
    0x0A4B: 'oomatragurmukhi',
    0x0A4C: 'aumatragurmukhi',
    0x0A4D: 'halantgurmukhi',
    0x0A59: 'khhagurmukhi',
    0x0A5A: 'ghhagurmukhi',
    0x0A5B: 'zagurmukhi',
    0x0A5C: 'rragurmukhi',
    0x0A5E: 'fagurmukhi',
    0x0A66: 'zerogurmukhi',
    0x0A67: 'onegurmukhi',
    0x0A68: 'twogurmukhi',
    0x0A69: 'threegurmukhi',
    0x0A6A: 'fourgurmukhi',
    0x0A6B: 'fivegurmukhi',
    0x0A6C: 'sixgurmukhi',
    0x0A6D: 'sevengurmukhi',
    0x0A6E: 'eightgurmukhi',
    0x0A6F: 'ninegurmukhi',
    0x0A70: 'tippigurmukhi',
    0x0A71: 'addakgurmukhi',
    0x0A72: 'irigurmukhi',
    0x0A73: 'uragurmukhi',
    0x0A74: 'ekonkargurmukhi',
    0x0A81: 'candrabindugujarati',
    0x0A82: 'anusvaragujarati',
    0x0A83: 'visargagujarati',
    0x0A85: 'agujarati',
    0x0A86: 'aagujarati',
    0x0A87: 'igujarati',
    0x0A88: 'iigujarati',
    0x0A89: 'ugujarati',
    0x0A8A: 'uugujarati',
    0x0A8B: 'rvocalicgujarati',
    0x0A8D: 'ecandragujarati',
    0x0A8F: 'egujarati',
    0x0A90: 'aigujarati',
    0x0A91: 'ocandragujarati',
    0x0A93: 'ogujarati',
    0x0A94: 'augujarati',
    0x0A95: 'kagujarati',
    0x0A96: 'khagujarati',
    0x0A97: 'gagujarati',
    0x0A98: 'ghagujarati',
    0x0A99: 'ngagujarati',
    0x0A9A: 'cagujarati',
    0x0A9B: 'chagujarati',
    0x0A9C: 'jagujarati',
    0x0A9D: 'jhagujarati',
    0x0A9E: 'nyagujarati',
    0x0A9F: 'ttagujarati',
    0x0AA0: 'tthagujarati',
    0x0AA1: 'ddagujarati',
    0x0AA2: 'ddhagujarati',
    0x0AA3: 'nnagujarati',
    0x0AA4: 'tagujarati',
    0x0AA5: 'thagujarati',
    0x0AA6: 'dagujarati',
    0x0AA7: 'dhagujarati',
    0x0AA8: 'nagujarati',
    0x0AAA: 'pagujarati',
    0x0AAB: 'phagujarati',
    0x0AAC: 'bagujarati',
    0x0AAD: 'bhagujarati',
    0x0AAE: 'magujarati',
    0x0AAF: 'yagujarati',
    0x0AB0: 'ragujarati',
    0x0AB2: 'lagujarati',
    0x0AB3: 'llagujarati',
    0x0AB5: 'vagujarati',
    0x0AB6: 'shagujarati',
    0x0AB7: 'ssagujarati',
    0x0AB8: 'sagujarati',
    0x0AB9: 'hagujarati',
    0x0ABC: 'nuktagujarati',
    0x0ABE: 'aavowelsigngujarati',
    0x0ABF: 'ivowelsigngujarati',
    0x0AC0: 'iivowelsigngujarati',
    0x0AC1: 'uvowelsigngujarati',
    0x0AC2: 'uuvowelsigngujarati',
    0x0AC3: 'rvocalicvowelsigngujarati',
    0x0AC4: 'rrvocalicvowelsigngujarati',
    0x0AC5: 'ecandravowelsigngujarati',
    0x0AC7: 'evowelsigngujarati',
    0x0AC8: 'aivowelsigngujarati',
    0x0AC9: 'ocandravowelsigngujarati',
    0x0ACB: 'ovowelsigngujarati',
    0x0ACC: 'auvowelsigngujarati',
    0x0ACD: 'viramagujarati',
    0x0AD0: 'omgujarati',
    0x0AE0: 'rrvocalicgujarati',
    0x0AE6: 'zerogujarati',
    0x0AE7: 'onegujarati',
    0x0AE8: 'twogujarati',
    0x0AE9: 'threegujarati',
    0x0AEA: 'fourgujarati',
    0x0AEB: 'fivegujarati',
    0x0AEC: 'sixgujarati',
    0x0AED: 'sevengujarati',
    0x0AEE: 'eightgujarati',
    0x0AEF: 'ninegujarati',
    0x0E01: 'kokaithai',
    0x0E02: 'khokhaithai',
    0x0E03: 'khokhuatthai',
    0x0E04: 'khokhwaithai',
    0x0E05: 'khokhonthai',
    0x0E06: 'khorakhangthai',
    0x0E07: 'ngonguthai',
    0x0E08: 'chochanthai',
    0x0E09: 'chochingthai',
    0x0E0A: 'chochangthai',
    0x0E0B: 'sosothai',
    0x0E0C: 'chochoethai',
    0x0E0D: 'yoyingthai',
    0x0E0E: 'dochadathai',
    0x0E0F: 'topatakthai',
    0x0E10: 'thothanthai',
    0x0E11: 'thonangmonthothai',
    0x0E12: 'thophuthaothai',
    0x0E13: 'nonenthai',
    0x0E14: 'dodekthai',
    0x0E15: 'totaothai',
    0x0E16: 'thothungthai',
    0x0E17: 'thothahanthai',
    0x0E18: 'thothongthai',
    0x0E19: 'nonuthai',
    0x0E1A: 'bobaimaithai',
    0x0E1B: 'poplathai',
    0x0E1C: 'phophungthai',
    0x0E1D: 'fofathai',
    0x0E1E: 'phophanthai',
    0x0E1F: 'fofanthai',
    0x0E20: 'phosamphaothai',
    0x0E21: 'momathai',
    0x0E22: 'yoyakthai',
    0x0E23: 'roruathai',
    0x0E24: 'ruthai',
    0x0E25: 'lolingthai',
    0x0E26: 'luthai',
    0x0E27: 'wowaenthai',
    0x0E28: 'sosalathai',
    0x0E29: 'sorusithai',
    0x0E2A: 'sosuathai',
    0x0E2B: 'hohipthai',
    0x0E2C: 'lochulathai',
    0x0E2D: 'oangthai',
    0x0E2E: 'honokhukthai',
    0x0E2F: 'paiyannoithai',
    0x0E30: 'saraathai',
    0x0E31: 'maihanakatthai',
    0x0E32: 'saraaathai',
    0x0E33: 'saraamthai',
    0x0E34: 'saraithai',
    0x0E35: 'saraiithai',
    0x0E36: 'sarauethai',
    0x0E37: 'saraueethai',
    0x0E38: 'sarauthai',
    0x0E39: 'sarauuthai',
    0x0E3A: 'phinthuthai',
    0x0E3F: 'bahtthai',
    0x0E40: 'saraethai',
    0x0E41: 'saraaethai',
    0x0E42: 'saraothai',
    0x0E43: 'saraaimaimuanthai',
    0x0E44: 'saraaimaimalaithai',
    0x0E45: 'lakkhangyaothai',
    0x0E46: 'maiyamokthai',
    0x0E47: 'maitaikhuthai',
    0x0E48: 'maiekthai',
    0x0E49: 'maithothai',
    0x0E4A: 'maitrithai',
    0x0E4B: 'maichattawathai',
    0x0E4C: 'thanthakhatthai',
    0x0E4D: 'nikhahitthai',
    0x0E4E: 'yamakkanthai',
    0x0E4F: 'fongmanthai',
    0x0E50: 'zerothai',
    0x0E51: 'onethai',
    0x0E52: 'twothai',
    0x0E53: 'threethai',
    0x0E54: 'fourthai',
    0x0E55: 'fivethai',
    0x0E56: 'sixthai',
    0x0E57: 'seventhai',
    0x0E58: 'eightthai',
    0x0E59: 'ninethai',
    0x0E5A: 'angkhankhuthai',
    0x0E5B: 'khomutthai',
    0x1E00: 'Aringbelow',
    0x1E01: 'aringbelow',
    0x1E02: 'Bdotaccent',
    0x1E03: 'bdotaccent',
    0x1E04: 'Bdotbelow',
    0x1E05: 'bdotbelow',
    0x1E06: 'Blinebelow',
    0x1E07: 'blinebelow',
    0x1E08: 'Ccedillaacute',
    0x1E09: 'ccedillaacute',
    0x1E0A: 'Ddotaccent',
    0x1E0B: 'ddotaccent',
    0x1E0C: 'Ddotbelow',
    0x1E0D: 'ddotbelow',
    0x1E0E: 'Dlinebelow',
    0x1E0F: 'dlinebelow',
    0x1E10: 'Dcedilla',
    0x1E11: 'dcedilla',
    0x1E12: 'Dcircumflexbelow',
    0x1E13: 'dcircumflexbelow',
    0x1E14: 'Emacrongrave',
    0x1E15: 'emacrongrave',
    0x1E16: 'Emacronacute',
    0x1E17: 'emacronacute',
    0x1E18: 'Ecircumflexbelow',
    0x1E19: 'ecircumflexbelow',
    0x1E1A: 'Etildebelow',
    0x1E1B: 'etildebelow',
    0x1E1C: 'Ecedillabreve',
    0x1E1D: 'ecedillabreve',
    0x1E1E: 'Fdotaccent',
    0x1E1F: 'fdotaccent',
    0x1E20: 'Gmacron',
    0x1E21: 'gmacron',
    0x1E22: 'Hdotaccent',
    0x1E23: 'hdotaccent',
    0x1E24: 'Hdotbelow',
    0x1E25: 'hdotbelow',
    0x1E26: 'Hdieresis',
    0x1E27: 'hdieresis',
    0x1E28: 'Hcedilla',
    0x1E29: 'hcedilla',
    0x1E2A: 'Hbrevebelow',
    0x1E2B: 'hbrevebelow',
    0x1E2C: 'Itildebelow',
    0x1E2D: 'itildebelow',
    0x1E2E: 'Idieresisacute',
    0x1E2F: 'idieresisacute',
    0x1E30: 'Kacute',
    0x1E31: 'kacute',
    0x1E32: 'Kdotbelow',
    0x1E33: 'kdotbelow',
    0x1E34: 'Klinebelow',
    0x1E35: 'klinebelow',
    0x1E36: 'Ldotbelow',
    0x1E37: 'ldotbelow',
    0x1E38: 'Ldotbelowmacron',
    0x1E39: 'ldotbelowmacron',
    0x1E3A: 'Llinebelow',
    0x1E3B: 'llinebelow',
    0x1E3C: 'Lcircumflexbelow',
    0x1E3D: 'lcircumflexbelow',
    0x1E3E: 'Macute',
    0x1E3F: 'macute',
    0x1E40: 'Mdotaccent',
    0x1E41: 'mdotaccent',
    0x1E42: 'Mdotbelow',
    0x1E43: 'mdotbelow',
    0x1E44: 'Ndotaccent',
    0x1E45: 'ndotaccent',
    0x1E46: 'Ndotbelow',
    0x1E47: 'ndotbelow',
    0x1E48: 'Nlinebelow',
    0x1E49: 'nlinebelow',
    0x1E4A: 'Ncircumflexbelow',
    0x1E4B: 'ncircumflexbelow',
    0x1E4C: 'Otildeacute',
    0x1E4D: 'otildeacute',
    0x1E4E: 'Otildedieresis',
    0x1E4F: 'otildedieresis',
    0x1E50: 'Omacrongrave',
    0x1E51: 'omacrongrave',
    0x1E52: 'Omacronacute',
    0x1E53: 'omacronacute',
    0x1E54: 'Pacute',
    0x1E55: 'pacute',
    0x1E56: 'Pdotaccent',
    0x1E57: 'pdotaccent',
    0x1E58: 'Rdotaccent',
    0x1E59: 'rdotaccent',
    0x1E5A: 'Rdotbelow',
    0x1E5B: 'rdotbelow',
    0x1E5C: 'Rdotbelowmacron',
    0x1E5D: 'rdotbelowmacron',
    0x1E5E: 'Rlinebelow',
    0x1E5F: 'rlinebelow',
    0x1E60: 'Sdotaccent',
    0x1E61: 'sdotaccent',
    0x1E62: 'Sdotbelow',
    0x1E63: 'sdotbelow',
    0x1E64: 'Sacutedotaccent',
    0x1E65: 'sacutedotaccent',
    0x1E66: 'Scarondotaccent',
    0x1E67: 'scarondotaccent',
    0x1E68: 'Sdotbelowdotaccent',
    0x1E69: 'sdotbelowdotaccent',
    0x1E6A: 'Tdotaccent',
    0x1E6B: 'tdotaccent',
    0x1E6C: 'Tdotbelow',
    0x1E6D: 'tdotbelow',
    0x1E6E: 'Tlinebelow',
    0x1E6F: 'tlinebelow',
    0x1E70: 'Tcircumflexbelow',
    0x1E71: 'tcircumflexbelow',
    0x1E72: 'Udieresisbelow',
    0x1E73: 'udieresisbelow',
    0x1E74: 'Utildebelow',
    0x1E75: 'utildebelow',
    0x1E76: 'Ucircumflexbelow',
    0x1E77: 'ucircumflexbelow',
    0x1E78: 'Utildeacute',
    0x1E79: 'utildeacute',
    0x1E7A: 'Umacrondieresis',
    0x1E7B: 'umacrondieresis',
    0x1E7C: 'Vtilde',
    0x1E7D: 'vtilde',
    0x1E7E: 'Vdotbelow',
    0x1E7F: 'vdotbelow',
    0x1E80: 'Wgrave',
    0x1E81: 'wgrave',
    0x1E82: 'Wacute',
    0x1E83: 'wacute',
    0x1E84: 'Wdieresis',
    0x1E85: 'wdieresis',
    0x1E86: 'Wdotaccent',
    0x1E87: 'wdotaccent',
    0x1E88: 'Wdotbelow',
    0x1E89: 'wdotbelow',
    0x1E8A: 'Xdotaccent',
    0x1E8B: 'xdotaccent',
    0x1E8C: 'Xdieresis',
    0x1E8D: 'xdieresis',
    0x1E8E: 'Ydotaccent',
    0x1E8F: 'ydotaccent',
    0x1E90: 'Zcircumflex',
    0x1E91: 'zcircumflex',
    0x1E92: 'Zdotbelow',
    0x1E93: 'zdotbelow',
    0x1E94: 'Zlinebelow',
    0x1E95: 'zlinebelow',
    0x1E96: 'hlinebelow',
    0x1E97: 'tdieresis',
    0x1E98: 'wring',
    0x1E99: 'yring',
    0x1E9A: 'arighthalfring',
    0x1E9B: 'slongdotaccent',
    0x1EA0: 'Adotbelow',
    0x1EA1: 'adotbelow',
    0x1EA2: 'Ahookabove',
    0x1EA3: 'ahookabove',
    0x1EA4: 'Acircumflexacute',
    0x1EA5: 'acircumflexacute',
    0x1EA6: 'Acircumflexgrave',
    0x1EA7: 'acircumflexgrave',
    0x1EA8: 'Acircumflexhookabove',
    0x1EA9: 'acircumflexhookabove',
    0x1EAA: 'Acircumflextilde',
    0x1EAB: 'acircumflextilde',
    0x1EAC: 'Acircumflexdotbelow',
    0x1EAD: 'acircumflexdotbelow',
    0x1EAE: 'Abreveacute',
    0x1EAF: 'abreveacute',
    0x1EB0: 'Abrevegrave',
    0x1EB1: 'abrevegrave',
    0x1EB2: 'Abrevehookabove',
    0x1EB3: 'abrevehookabove',
    0x1EB4: 'Abrevetilde',
    0x1EB5: 'abrevetilde',
    0x1EB6: 'Abrevedotbelow',
    0x1EB7: 'abrevedotbelow',
    0x1EB8: 'Edotbelow',
    0x1EB9: 'edotbelow',
    0x1EBA: 'Ehookabove',
    0x1EBB: 'ehookabove',
    0x1EBC: 'Etilde',
    0x1EBD: 'etilde',
    0x1EBE: 'Ecircumflexacute',
    0x1EBF: 'ecircumflexacute',
    0x1EC0: 'Ecircumflexgrave',
    0x1EC1: 'ecircumflexgrave',
    0x1EC2: 'Ecircumflexhookabove',
    0x1EC3: 'ecircumflexhookabove',
    0x1EC4: 'Ecircumflextilde',
    0x1EC5: 'ecircumflextilde',
    0x1EC6: 'Ecircumflexdotbelow',
    0x1EC7: 'ecircumflexdotbelow',
    0x1EC8: 'Ihookabove',
    0x1EC9: 'ihookabove',
    0x1ECA: 'Idotbelow',
    0x1ECB: 'idotbelow',
    0x1ECC: 'Odotbelow',
    0x1ECD: 'odotbelow',
    0x1ECE: 'Ohookabove',
    0x1ECF: 'ohookabove',
    0x1ED0: 'Ocircumflexacute',
    0x1ED1: 'ocircumflexacute',
    0x1ED2: 'Ocircumflexgrave',
    0x1ED3: 'ocircumflexgrave',
    0x1ED4: 'Ocircumflexhookabove',
    0x1ED5: 'ocircumflexhookabove',
    0x1ED6: 'Ocircumflextilde',
    0x1ED7: 'ocircumflextilde',
    0x1ED8: 'Ocircumflexdotbelow',
    0x1ED9: 'ocircumflexdotbelow',
    0x1EDA: 'Ohornacute',
    0x1EDB: 'ohornacute',
    0x1EDC: 'Ohorngrave',
    0x1EDD: 'ohorngrave',
    0x1EDE: 'Ohornhookabove',
    0x1EDF: 'ohornhookabove',
    0x1EE0: 'Ohorntilde',
    0x1EE1: 'ohorntilde',
    0x1EE2: 'Ohorndotbelow',
    0x1EE3: 'ohorndotbelow',
    0x1EE4: 'Udotbelow',
    0x1EE5: 'udotbelow',
    0x1EE6: 'Uhookabove',
    0x1EE7: 'uhookabove',
    0x1EE8: 'Uhornacute',
    0x1EE9: 'uhornacute',
    0x1EEA: 'Uhorngrave',
    0x1EEB: 'uhorngrave',
    0x1EEC: 'Uhornhookabove',
    0x1EED: 'uhornhookabove',
    0x1EEE: 'Uhorntilde',
    0x1EEF: 'uhorntilde',
    0x1EF0: 'Uhorndotbelow',
    0x1EF1: 'uhorndotbelow',
    0x1EF2: 'Ygrave',
    0x1EF3: 'ygrave',
    0x1EF4: 'Ydotbelow',
    0x1EF5: 'ydotbelow',
    0x1EF6: 'Yhookabove',
    0x1EF7: 'yhookabove',
    0x1EF8: 'Ytilde',
    0x1EF9: 'ytilde',
    0x2002: 'enspace',
    0x200B: 'zerowidthspace',
    0x200C: ('afii61664', 'zerowidthnonjoiner'),
    0x200D: 'afii301',
    0x200E: 'afii299',
    0x200F: 'afii300',
    0x2010: 'hyphentwo',
    0x2012: 'figuredash',
    0x2013: 'endash',
    0x2014: 'emdash',
    0x2015: ('afii00208', 'horizontalbar'),
    0x2016: 'dblverticalbar',
    0x2017: ('dbllowline', 'underscoredbl'),
    0x2018: 'quoteleft',
    0x2019: 'quoteright',
    0x201A: 'quotesinglbase',
    0x201B: ('quoteleftreversed', 'quotereversed'),
    0x201C: 'quotedblleft',
    0x201D: 'quotedblright',
    0x201E: 'quotedblbase',
    0x2020: 'dagger',
    0x2021: 'daggerdbl',
    0x2022: 'bullet',
    0x2024: 'onedotenleader',
    0x2025: ('twodotenleader', 'twodotleader'),
    0x2026: 'ellipsis',
    0x202C: 'afii61573',
    0x202D: 'afii61574',
    0x202E: 'afii61575',
    0x2030: 'perthousand',
    0x2032: 'minute',
    0x2033: 'second',
    0x2035: 'primereversed',
    0x2039: 'guilsinglleft',
    0x203A: 'guilsinglright',
    0x203B: 'referencemark',
    0x203C: 'exclamdbl',
    0x203E: 'overline',
    0x2042: 'asterism',
    0x2044: 'fraction',
    0x2070: 'zerosuperior',
    0x2074: 'foursuperior',
    0x2075: 'fivesuperior',
    0x2076: 'sixsuperior',
    0x2077: 'sevensuperior',
    0x2078: 'eightsuperior',
    0x2079: 'ninesuperior',
    0x207A: 'plussuperior',
    0x207C: 'equalsuperior',
    0x207D: 'parenleftsuperior',
    0x207E: 'parenrightsuperior',
    0x207F: 'nsuperior',
    0x2080: 'zeroinferior',
    0x2081: 'oneinferior',
    0x2082: 'twoinferior',
    0x2083: 'threeinferior',
    0x2084: 'fourinferior',
    0x2085: 'fiveinferior',
    0x2086: 'sixinferior',
    0x2087: 'seveninferior',
    0x2088: 'eightinferior',
    0x2089: 'nineinferior',
    0x208D: 'parenleftinferior',
    0x208E: 'parenrightinferior',
    0x20A1: ('colonmonetary', 'colonsign'),
    0x20A2: 'cruzeiro',
    0x20A3: 'franc',
    0x20A4: ('afii08941', 'lira'),
    0x20A7: 'peseta',
    0x20A9: 'won',
    0x20AA: ('afii57636', 'newsheqelsign', 'sheqel', 'sheqelhebrew'),
    0x20AB: 'dong',
    0x20AC: ('euro', 'Euro'),
    0x2103: 'centigrade',
    0x2105: ('afii61248', 'careof'),
    0x2109: 'fahrenheit',
    0x2111: 'Ifraktur',
    0x2113: ('afii61289', 'lsquare'),
    0x2116: ('afii61352', 'numero'),
    0x2118: 'weierstrass',
    0x211C: 'Rfraktur',
    0x211E: 'prescription',
    0x2121: 'telephone',
    0x2122: 'trademark',
    0x2126: ('Ohm', 'Omega'),
    0x212B: 'angstrom',
    0x212E: 'estimated',
    0x2135: 'aleph',
    0x2153: 'onethird',
    0x2154: 'twothirds',
    0x215B: 'oneeighth',
    0x215C: 'threeeighths',
    0x215D: 'fiveeighths',
    0x215E: 'seveneighths',
    0x2160: 'Oneroman',
    0x2161: 'Tworoman',
    0x2162: 'Threeroman',
    0x2163: 'Fourroman',
    0x2164: 'Fiveroman',
    0x2165: 'Sixroman',
    0x2166: 'Sevenroman',
    0x2167: 'Eightroman',
    0x2168: 'Nineroman',
    0x2169: 'Tenroman',
    0x216A: 'Elevenroman',
    0x216B: 'Twelveroman',
    0x2170: 'oneroman',
    0x2171: 'tworoman',
    0x2172: 'threeroman',
    0x2173: 'fourroman',
    0x2174: 'fiveroman',
    0x2175: 'sixroman',
    0x2176: 'sevenroman',
    0x2177: 'eightroman',
    0x2178: 'nineroman',
    0x2179: 'tenroman',
    0x217A: 'elevenroman',
    0x217B: 'twelveroman',
    0x2190: 'arrowleft',
    0x2191: 'arrowup',
    0x2192: 'arrowright',
    0x2193: 'arrowdown',
    0x2194: 'arrowboth',
    0x2195: 'arrowupdn',
    0x2196: 'arrowupleft',
    0x2197: 'arrowupright',
    0x2198: 'arrowdownright',
    0x2199: 'arrowdownleft',
    0x21A8: ('arrowupdnbse', 'arrowupdownbase'),
    0x21B5: 'carriagereturn',
    0x21BC: 'harpoonleftbarbup',
    0x21C0: 'harpoonrightbarbup',
    0x21C4: 'arrowrightoverleft',
    0x21C5: 'arrowupleftofdown',
    0x21C6: 'arrowleftoverright',
    0x21CD: 'arrowleftdblstroke',
    0x21CF: 'arrowrightdblstroke',
    0x21D0: ('arrowdblleft', 'arrowleftdbl'),
    0x21D1: 'arrowdblup',
    0x21D2: ('arrowdblright', 'dblarrowright'),
    0x21D3: 'arrowdbldown',
    0x21D4: ('arrowdblboth', 'dblarrowleft'),
    0x21DE: 'pageup',
    0x21DF: 'pagedown',
    0x21E0: 'arrowdashleft',
    0x21E1: 'arrowdashup',
    0x21E2: 'arrowdashright',
    0x21E3: 'arrowdashdown',
    0x21E4: 'arrowtableft',
    0x21E5: 'arrowtabright',
    0x21E6: 'arrowleftwhite',
    0x21E7: 'arrowupwhite',
    0x21E8: 'arrowrightwhite',
    0x21E9: 'arrowdownwhite',
    0x21EA: 'capslock',
    0x2200: ('forall', 'universal'),
    0x2202: 'partialdiff',
    0x2203: ('existential', 'thereexists'),
    0x2205: 'emptyset',
    0x2206: ('Delta', 'increment'),
    0x2207: ('gradient', 'nabla'),
    0x2208: 'element',
    0x2209: ('notelement', 'notelementof'),
    0x220B: 'suchthat',
    0x220C: 'notcontains',
    0x220F: 'product',
    0x2211: 'summation',
    0x2212: 'minus',
    0x2213: 'minusplus',
    0x2215: 'divisionslash',
    0x2217: 'asteriskmath',
    0x2219: 'bulletoperator',
    0x221A: 'radical',
    0x221D: 'proportional',
    0x221E: 'infinity',
    0x221F: ('orthogonal', 'rightangle'),
    0x2220: 'angle',
    0x2223: 'divides',
    0x2225: 'parallel',
    0x2226: 'notparallel',
    0x2227: 'logicaland',
    0x2228: 'logicalor',
    0x2229: 'intersection',
    0x222A: 'union',
    0x222B: 'integral',
    0x222C: 'dblintegral',
    0x222E: 'contourintegral',
    0x2234: 'therefore',
    0x2235: 'because',
    0x2236: 'ratio',
    0x2237: 'proportion',
    0x223C: ('similar', 'tildeoperator'),
    0x223D: 'reversedtilde',
    0x2243: 'asymptoticallyequal',
    0x2245: ('approximatelyequal', 'congruent'),
    0x2248: 'approxequal',
    0x224C: 'allequal',
    0x2250: 'approaches',
    0x2251: 'geometricallyequal',
    0x2252: 'approxequalorimage',
    0x2253: 'imageorapproximatelyequal',
    0x2260: 'notequal',
    0x2261: 'equivalence',
    0x2262: 'notidentical',
    0x2264: 'lessequal',
    0x2265: 'greaterequal',
    0x2266: 'lessoverequal',
    0x2267: 'greateroverequal',
    0x226A: 'muchless',
    0x226B: 'muchgreater',
    0x226E: 'notless',
    0x226F: 'notgreater',
    0x2270: 'notlessnorequal',
    0x2271: 'notgreaternorequal',
    0x2272: 'lessorequivalent',
    0x2273: 'greaterorequivalent',
    0x2276: 'lessorgreater',
    0x2277: 'greaterorless',
    0x2279: 'notgreaternorless',
    0x227A: 'precedes',
    0x227B: 'succeeds',
    0x2280: 'notprecedes',
    0x2281: 'notsucceeds',
    0x2282: ('propersubset', 'subset'),
    0x2283: ('propersuperset', 'superset'),
    0x2284: 'notsubset',
    0x2285: 'notsuperset',
    0x2286: ('reflexsubset', 'subsetorequal'),
    0x2287: ('reflexsuperset', 'supersetorequal'),
    0x228A: 'subsetnotequal',
    0x228B: 'supersetnotequal',
    0x2295: ('circleplus', 'pluscircle'),
    0x2296: 'minuscircle',
    0x2297: ('circlemultiply', 'timescircle'),
    0x2299: 'circleot',
    0x22A3: 'tackleft',
    0x22A4: 'tackdown',
    0x22A5: 'perpendicular',
    0x22BF: 'righttriangle',
    0x22C5: 'dotmath',
    0x22CE: 'curlyor',
    0x22CF: 'curlyand',
    0x22DA: 'lessequalorgreater',
    0x22DB: 'greaterequalorless',
    0x22EE: 'ellipsisvertical',
    0x2302: 'house',
    0x2303: 'control',
    0x2305: 'projective',
    0x2310: ('logicalnotreversed', 'revlogicalnot'),
    0x2312: 'arc',
    0x2318: 'propellor',
    0x2320: ('integraltop', 'integraltp'),
    0x2321: ('integralbottom', 'integralbt'),
    0x2325: 'option',
    0x2326: 'deleteright',
    0x2327: 'clear',
    0x2329: 'angleleft',
    0x232A: 'angleright',
    0x232B: 'deleteleft',
    0x2423: 'blank',
    0x2460: 'onecircle',
    0x2461: 'twocircle',
    0x2462: 'threecircle',
    0x2463: 'fourcircle',
    0x2464: 'fivecircle',
    0x2465: 'sixcircle',
    0x2466: 'sevencircle',
    0x2467: 'eightcircle',
    0x2468: 'ninecircle',
    0x2469: 'tencircle',
    0x246A: 'elevencircle',
    0x246B: 'twelvecircle',
    0x246C: 'thirteencircle',
    0x246D: 'fourteencircle',
    0x246E: 'fifteencircle',
    0x246F: 'sixteencircle',
    0x2470: 'seventeencircle',
    0x2471: 'eighteencircle',
    0x2472: 'nineteencircle',
    0x2473: 'twentycircle',
    0x2474: 'oneparen',
    0x2475: 'twoparen',
    0x2476: 'threeparen',
    0x2477: 'fourparen',
    0x2478: 'fiveparen',
    0x2479: 'sixparen',
    0x247A: 'sevenparen',
    0x247B: 'eightparen',
    0x247C: 'nineparen',
    0x247D: 'tenparen',
    0x247E: 'elevenparen',
    0x247F: 'twelveparen',
    0x2480: 'thirteenparen',
    0x2481: 'fourteenparen',
    0x2482: 'fifteenparen',
    0x2483: 'sixteenparen',
    0x2484: 'seventeenparen',
    0x2485: 'eighteenparen',
    0x2486: 'nineteenparen',
    0x2487: 'twentyparen',
    0x2488: 'oneperiod',
    0x2489: 'twoperiod',
    0x248A: 'threeperiod',
    0x248B: 'fourperiod',
    0x248C: 'fiveperiod',
    0x248D: 'sixperiod',
    0x248E: 'sevenperiod',
    0x248F: 'eightperiod',
    0x2490: 'nineperiod',
    0x2491: 'tenperiod',
    0x2492: 'elevenperiod',
    0x2493: 'twelveperiod',
    0x2494: 'thirteenperiod',
    0x2495: 'fourteenperiod',
    0x2496: 'fifteenperiod',
    0x2497: 'sixteenperiod',
    0x2498: 'seventeenperiod',
    0x2499: 'eighteenperiod',
    0x249A: 'nineteenperiod',
    0x249B: 'twentyperiod',
    0x249C: 'aparen',
    0x249D: 'bparen',
    0x249E: 'cparen',
    0x249F: 'dparen',
    0x24A0: 'eparen',
    0x24A1: 'fparen',
    0x24A2: 'gparen',
    0x24A3: 'hparen',
    0x24A4: 'iparen',
    0x24A5: 'jparen',
    0x24A6: 'kparen',
    0x24A7: 'lparen',
    0x24A8: 'mparen',
    0x24A9: 'nparen',
    0x24AA: 'oparen',
    0x24AB: 'pparen',
    0x24AC: 'qparen',
    0x24AD: 'rparen',
    0x24AE: 'sparen',
    0x24AF: 'tparen',
    0x24B0: 'uparen',
    0x24B1: 'vparen',
    0x24B2: 'wparen',
    0x24B3: 'xparen',
    0x24B4: 'yparen',
    0x24B5: 'zparen',
    0x24B6: 'Acircle',
    0x24B7: 'Bcircle',
    0x24B8: 'Ccircle',
    0x24B9: 'Dcircle',
    0x24BA: 'Ecircle',
    0x24BB: 'Fcircle',
    0x24BC: 'Gcircle',
    0x24BD: 'Hcircle',
    0x24BE: 'Icircle',
    0x24BF: 'Jcircle',
    0x24C0: 'Kcircle',
    0x24C1: 'Lcircle',
    0x24C2: 'Mcircle',
    0x24C3: 'Ncircle',
    0x24C4: 'Ocircle',
    0x24C5: 'Pcircle',
    0x24C6: 'Qcircle',
    0x24C7: 'Rcircle',
    0x24C8: 'Scircle',
    0x24C9: 'Tcircle',
    0x24CA: 'Ucircle',
    0x24CB: 'Vcircle',
    0x24CC: 'Wcircle',
    0x24CD: 'Xcircle',
    0x24CE: 'Ycircle',
    0x24CF: 'Zcircle',
    0x24D0: 'acircle',
    0x24D1: 'bcircle',
    0x24D2: 'ccircle',
    0x24D3: 'dcircle',
    0x24D4: 'ecircle',
    0x24D5: 'fcircle',
    0x24D6: 'gcircle',
    0x24D7: 'hcircle',
    0x24D8: 'icircle',
    0x24D9: 'jcircle',
    0x24DA: 'kcircle',
    0x24DB: 'lcircle',
    0x24DC: 'mcircle',
    0x24DD: 'ncircle',
    0x24DE: 'ocircle',
    0x24DF: 'pcircle',
    0x24E0: 'qcircle',
    0x24E1: 'rcircle',
    0x24E2: 'scircle',
    0x24E3: 'tcircle',
    0x24E4: 'ucircle',
    0x24E5: 'vcircle',
    0x24E6: 'wcircle',
    0x24E7: 'xcircle',
    0x24E8: 'ycircle',
    0x24E9: 'zcircle',
    0x2500: 'SF100000',
    0x2502: 'SF110000',
    0x250C: 'SF010000',
    0x2510: 'SF030000',
    0x2514: 'SF020000',
    0x2518: 'SF040000',
    0x251C: 'SF080000',
    0x2524: 'SF090000',
    0x252C: 'SF060000',
    0x2534: 'SF070000',
    0x253C: 'SF050000',
    0x2550: 'SF430000',
    0x2551: 'SF240000',
    0x2552: 'SF510000',
    0x2553: 'SF520000',
    0x2554: 'SF390000',
    0x2555: 'SF220000',
    0x2556: 'SF210000',
    0x2557: 'SF250000',
    0x2558: 'SF500000',
    0x2559: 'SF490000',
    0x255A: 'SF380000',
    0x255B: 'SF280000',
    0x255C: 'SF270000',
    0x255D: 'SF260000',
    0x255E: 'SF360000',
    0x255F: 'SF370000',
    0x2560: 'SF420000',
    0x2561: 'SF190000',
    0x2562: 'SF200000',
    0x2563: 'SF230000',
    0x2564: 'SF470000',
    0x2565: 'SF480000',
    0x2566: 'SF410000',
    0x2567: 'SF450000',
    0x2568: 'SF460000',
    0x2569: 'SF400000',
    0x256A: 'SF540000',
    0x256B: 'SF530000',
    0x256C: 'SF440000',
    0x2580: 'upblock',
    0x2584: 'dnblock',
    0x2588: 'block',
    0x258C: 'lfblock',
    0x2590: 'rtblock',
    0x2591: ('ltshade', 'shadelight'),
    0x2592: ('shade', 'shademedium'),
    0x2593: ('dkshade', 'shadedark'),
    0x25A0: ('blacksquare', 'filledbox'),
    0x25A1: ('H22073', 'whitesquare'),
    0x25A3: 'squarewhitewithsmallblack',
    0x25A4: 'squarehorizontalfill',
    0x25A5: 'squareverticalfill',
    0x25A6: 'squareorthogonalcrosshatchfill',
    0x25A7: 'squareupperlefttolowerrightfill',
    0x25A8: 'squareupperrighttolowerleftfill',
    0x25A9: 'squarediagonalcrosshatchfill',
    0x25AA: ('blacksmallsquare', 'H18543'),
    0x25AB: ('H18551', 'whitesmallsquare'),
    0x25AC: ('blackrectangle', 'filledrect'),
    0x25B2: ('blackuppointingtriangle', 'triagup'),
    0x25B3: 'whiteuppointingtriangle',
    0x25B4: 'blackuppointingsmalltriangle',
    0x25B5: 'whiteuppointingsmalltriangle',
    0x25B6: 'blackrightpointingtriangle',
    0x25B7: 'whiterightpointingtriangle',
    0x25B9: 'whiterightpointingsmalltriangle',
    0x25BA: ('blackrightpointingpointer', 'triagrt'),
    0x25BC: ('blackdownpointingtriangle', 'triagdn'),
    0x25BD: 'whitedownpointingtriangle',
    0x25BF: 'whitedownpointingsmalltriangle',
    0x25C0: 'blackleftpointingtriangle',
    0x25C1: 'whiteleftpointingtriangle',
    0x25C3: 'whiteleftpointingsmalltriangle',
    0x25C4: ('blackleftpointingpointer', 'triaglf'),
    0x25C6: 'blackdiamond',
    0x25C7: 'whitediamond',
    0x25C8: 'whitediamondcontainingblacksmalldiamond',
    0x25C9: 'fisheye',
    0x25CA: 'lozenge',
    0x25CB: ('circle', 'whitecircle'),
    0x25CC: 'dottedcircle',
    0x25CE: 'bullseye',
    0x25CF: ('blackcircle', 'H18533'),
    0x25D0: 'circlewithlefthalfblack',
    0x25D1: 'circlewithrighthalfblack',
    0x25D8: ('bulletinverse', 'invbullet'),
    0x25D9: ('invcircle', 'whitecircleinverse'),
    0x25E2: 'blacklowerrighttriangle',
    0x25E3: 'blacklowerlefttriangle',
    0x25E4: 'blackupperlefttriangle',
    0x25E5: 'blackupperrighttriangle',
    0x25E6: ('openbullet', 'whitebullet'),
    0x25EF: 'largecircle',
    0x2605: 'blackstar',
    0x2606: 'whitestar',
    0x260E: 'telephoneblack',
    0x260F: 'whitetelephone',
    0x261C: 'pointingindexleftwhite',
    0x261D: 'pointingindexupwhite',
    0x261E: 'pointingindexrightwhite',
    0x261F: 'pointingindexdownwhite',
    0x262F: 'yinyang',
    0x263A: ('smileface', 'whitesmilingface'),
    0x263B: ('blacksmilingface', 'invsmileface'),
    0x263C: ('compass', 'sun'),
    0x2640: ('female', 'venus'),
    0x2641: 'earth',
    0x2642: ('male', 'mars'),
    0x2660: ('spade', 'spadesuitblack'),
    0x2661: 'heartsuitwhite',
    0x2662: 'diamondsuitwhite',
    0x2663: ('club', 'clubsuitblack'),
    0x2664: 'spadesuitwhite',
    0x2665: ('heart', 'heartsuitblack'),
    0x2666: 'diamond',
    0x2667: 'clubsuitwhite',
    0x2668: 'hotsprings',
    0x2669: 'quarternote',
    0x266A: 'musicalnote',
    0x266B: ('eighthnotebeamed', 'musicalnotedbl'),
    0x266C: 'beamedsixteenthnotes',
    0x266D: 'musicflatsign',
    0x266F: 'musicsharpsign',
    0x2713: 'checkmark',
    0x278A: 'onecircleinversesansserif',
    0x278B: 'twocircleinversesansserif',
    0x278C: 'threecircleinversesansserif',
    0x278D: 'fourcircleinversesansserif',
    0x278E: 'fivecircleinversesansserif',
    0x278F: 'sixcircleinversesansserif',
    0x2790: 'sevencircleinversesansserif',
    0x2791: 'eightcircleinversesansserif',
    0x2792: 'ninecircleinversesansserif',
    0x279E: 'arrowrightheavy',
    0x3000: 'ideographicspace',
    0x3001: 'ideographiccomma',
    0x3002: 'ideographicperiod',
    0x3003: 'dittomark',
    0x3004: 'jis',
    0x3005: 'ideographiciterationmark',
    0x3006: 'ideographicclose',
    0x3007: 'ideographiczero',
    0x3008: 'anglebracketleft',
    0x3009: 'anglebracketright',
    0x300A: 'dblanglebracketleft',
    0x300B: 'dblanglebracketright',
    0x300C: 'cornerbracketleft',
    0x300D: 'cornerbracketright',
    0x300E: 'whitecornerbracketleft',
    0x300F: 'whitecornerbracketright',
    0x3010: 'blacklenticularbracketleft',
    0x3011: 'blacklenticularbracketright',
    0x3012: 'postalmark',
    0x3013: 'getamark',
    0x3014: 'tortoiseshellbracketleft',
    0x3015: 'tortoiseshellbracketright',
    0x3016: 'whitelenticularbracketleft',
    0x3017: 'whitelenticularbracketright',
    0x3018: 'whitetortoiseshellbracketleft',
    0x3019: 'whitetortoiseshellbracketright',
    0x301C: 'wavedash',
    0x301D: 'quotedblprimereversed',
    0x301E: 'quotedblprime',
    0x3020: 'postalmarkface',
    0x3021: 'onehangzhou',
    0x3022: 'twohangzhou',
    0x3023: 'threehangzhou',
    0x3024: 'fourhangzhou',
    0x3025: 'fivehangzhou',
    0x3026: 'sixhangzhou',
    0x3027: 'sevenhangzhou',
    0x3028: 'eighthangzhou',
    0x3029: 'ninehangzhou',
    0x3036: 'circlepostalmark',
    0x3041: 'asmallhiragana',
    0x3042: 'ahiragana',
    0x3043: 'ismallhiragana',
    0x3044: 'ihiragana',
    0x3045: 'usmallhiragana',
    0x3046: 'uhiragana',
    0x3047: 'esmallhiragana',
    0x3048: 'ehiragana',
    0x3049: 'osmallhiragana',
    0x304A: 'ohiragana',
    0x304B: 'kahiragana',
    0x304C: 'gahiragana',
    0x304D: 'kihiragana',
    0x304E: 'gihiragana',
    0x304F: 'kuhiragana',
    0x3050: 'guhiragana',
    0x3051: 'kehiragana',
    0x3052: 'gehiragana',
    0x3053: 'kohiragana',
    0x3054: 'gohiragana',
    0x3055: 'sahiragana',
    0x3056: 'zahiragana',
    0x3057: 'sihiragana',
    0x3058: 'zihiragana',
    0x3059: 'suhiragana',
    0x305A: 'zuhiragana',
    0x305B: 'sehiragana',
    0x305C: 'zehiragana',
    0x305D: 'sohiragana',
    0x305E: 'zohiragana',
    0x305F: 'tahiragana',
    0x3060: 'dahiragana',
    0x3061: 'tihiragana',
    0x3062: 'dihiragana',
    0x3063: 'tusmallhiragana',
    0x3064: 'tuhiragana',
    0x3065: 'duhiragana',
    0x3066: 'tehiragana',
    0x3067: 'dehiragana',
    0x3068: 'tohiragana',
    0x3069: 'dohiragana',
    0x306A: 'nahiragana',
    0x306B: 'nihiragana',
    0x306C: 'nuhiragana',
    0x306D: 'nehiragana',
    0x306E: 'nohiragana',
    0x306F: 'hahiragana',
    0x3070: 'bahiragana',
    0x3071: 'pahiragana',
    0x3072: 'hihiragana',
    0x3073: 'bihiragana',
    0x3074: 'pihiragana',
    0x3075: 'huhiragana',
    0x3076: 'buhiragana',
    0x3077: 'puhiragana',
    0x3078: 'hehiragana',
    0x3079: 'behiragana',
    0x307A: 'pehiragana',
    0x307B: 'hohiragana',
    0x307C: 'bohiragana',
    0x307D: 'pohiragana',
    0x307E: 'mahiragana',
    0x307F: 'mihiragana',
    0x3080: 'muhiragana',
    0x3081: 'mehiragana',
    0x3082: 'mohiragana',
    0x3083: 'yasmallhiragana',
    0x3084: 'yahiragana',
    0x3085: 'yusmallhiragana',
    0x3086: 'yuhiragana',
    0x3087: 'yosmallhiragana',
    0x3088: 'yohiragana',
    0x3089: 'rahiragana',
    0x308A: 'rihiragana',
    0x308B: 'ruhiragana',
    0x308C: 'rehiragana',
    0x308D: 'rohiragana',
    0x308E: 'wasmallhiragana',
    0x308F: 'wahiragana',
    0x3090: 'wihiragana',
    0x3091: 'wehiragana',
    0x3092: 'wohiragana',
    0x3093: 'nhiragana',
    0x3094: 'vuhiragana',
    0x309B: 'voicedmarkkana',
    0x309C: 'semivoicedmarkkana',
    0x309D: 'iterationhiragana',
    0x309E: 'voicediterationhiragana',
    0x30A1: 'asmallkatakana',
    0x30A2: 'akatakana',
    0x30A3: 'ismallkatakana',
    0x30A4: 'ikatakana',
    0x30A5: 'usmallkatakana',
    0x30A6: 'ukatakana',
    0x30A7: 'esmallkatakana',
    0x30A8: 'ekatakana',
    0x30A9: 'osmallkatakana',
    0x30AA: 'okatakana',
    0x30AB: 'kakatakana',
    0x30AC: 'gakatakana',
    0x30AD: 'kikatakana',
    0x30AE: 'gikatakana',
    0x30AF: 'kukatakana',
    0x30B0: 'gukatakana',
    0x30B1: 'kekatakana',
    0x30B2: 'gekatakana',
    0x30B3: 'kokatakana',
    0x30B4: 'gokatakana',
    0x30B5: 'sakatakana',
    0x30B6: 'zakatakana',
    0x30B7: 'sikatakana',
    0x30B8: 'zikatakana',
    0x30B9: 'sukatakana',
    0x30BA: 'zukatakana',
    0x30BB: 'sekatakana',
    0x30BC: 'zekatakana',
    0x30BD: 'sokatakana',
    0x30BE: 'zokatakana',
    0x30BF: 'takatakana',
    0x30C0: 'dakatakana',
    0x30C1: 'tikatakana',
    0x30C2: 'dikatakana',
    0x30C3: 'tusmallkatakana',
    0x30C4: 'tukatakana',
    0x30C5: 'dukatakana',
    0x30C6: 'tekatakana',
    0x30C7: 'dekatakana',
    0x30C8: 'tokatakana',
    0x30C9: 'dokatakana',
    0x30CA: 'nakatakana',
    0x30CB: 'nikatakana',
    0x30CC: 'nukatakana',
    0x30CD: 'nekatakana',
    0x30CE: 'nokatakana',
    0x30CF: 'hakatakana',
    0x30D0: 'bakatakana',
    0x30D1: 'pakatakana',
    0x30D2: 'hikatakana',
    0x30D3: 'bikatakana',
    0x30D4: 'pikatakana',
    0x30D5: 'hukatakana',
    0x30D6: 'bukatakana',
    0x30D7: 'pukatakana',
    0x30D8: 'hekatakana',
    0x30D9: 'bekatakana',
    0x30DA: 'pekatakana',
    0x30DB: 'hokatakana',
    0x30DC: 'bokatakana',
    0x30DD: 'pokatakana',
    0x30DE: 'makatakana',
    0x30DF: 'mikatakana',
    0x30E0: 'mukatakana',
    0x30E1: 'mekatakana',
    0x30E2: 'mokatakana',
    0x30E3: 'yasmallkatakana',
    0x30E4: 'yakatakana',
    0x30E5: 'yusmallkatakana',
    0x30E6: 'yukatakana',
    0x30E7: 'yosmallkatakana',
    0x30E8: 'yokatakana',
    0x30E9: 'rakatakana',
    0x30EA: 'rikatakana',
    0x30EB: 'rukatakana',
    0x30EC: 'rekatakana',
    0x30ED: 'rokatakana',
    0x30EE: 'wasmallkatakana',
    0x30EF: 'wakatakana',
    0x30F0: 'wikatakana',
    0x30F1: 'wekatakana',
    0x30F2: 'wokatakana',
    0x30F3: 'nkatakana',
    0x30F4: 'vukatakana',
    0x30F5: 'kasmallkatakana',
    0x30F6: 'kesmallkatakana',
    0x30F7: 'vakatakana',
    0x30F8: 'vikatakana',
    0x30F9: 'vekatakana',
    0x30FA: 'vokatakana',
    0x30FB: 'dotkatakana',
    0x30FC: 'prolongedkana',
    0x30FD: 'iterationkatakana',
    0x30FE: 'voicediterationkatakana',
    0x3105: 'bbopomofo',
    0x3106: 'pbopomofo',
    0x3107: 'mbopomofo',
    0x3108: 'fbopomofo',
    0x3109: 'dbopomofo',
    0x310A: 'tbopomofo',
    0x310B: 'nbopomofo',
    0x310C: 'lbopomofo',
    0x310D: 'gbopomofo',
    0x310E: 'kbopomofo',
    0x310F: 'hbopomofo',
    0x3110: 'jbopomofo',
    0x3111: 'qbopomofo',
    0x3112: 'xbopomofo',
    0x3113: 'zhbopomofo',
    0x3114: 'chbopomofo',
    0x3115: 'shbopomofo',
    0x3116: 'rbopomofo',
    0x3117: 'zbopomofo',
    0x3118: 'cbopomofo',
    0x3119: 'sbopomofo',
    0x311A: 'abopomofo',
    0x311B: 'obopomofo',
    0x311C: 'ebopomofo',
    0x311D: 'ehbopomofo',
    0x311E: 'aibopomofo',
    0x311F: 'eibopomofo',
    0x3120: 'aubopomofo',
    0x3121: 'oubopomofo',
    0x3122: 'anbopomofo',
    0x3123: 'enbopomofo',
    0x3124: 'angbopomofo',
    0x3125: 'engbopomofo',
    0x3126: 'erbopomofo',
    0x3127: 'ibopomofo',
    0x3128: 'ubopomofo',
    0x3129: 'iubopomofo',
    0x3131: 'kiyeokkorean',
    0x3132: 'ssangkiyeokkorean',
    0x3133: 'kiyeoksioskorean',
    0x3134: 'nieunkorean',
    0x3135: 'nieuncieuckorean',
    0x3136: 'nieunhieuhkorean',
    0x3137: 'tikeutkorean',
    0x3138: 'ssangtikeutkorean',
    0x3139: 'rieulkorean',
    0x313A: 'rieulkiyeokkorean',
    0x313B: 'rieulmieumkorean',
    0x313C: 'rieulpieupkorean',
    0x313D: 'rieulsioskorean',
    0x313E: 'rieulthieuthkorean',
    0x313F: 'rieulphieuphkorean',
    0x3140: 'rieulhieuhkorean',
    0x3141: 'mieumkorean',
    0x3142: 'pieupkorean',
    0x3143: 'ssangpieupkorean',
    0x3144: 'pieupsioskorean',
    0x3145: 'sioskorean',
    0x3146: 'ssangsioskorean',
    0x3147: 'ieungkorean',
    0x3148: 'cieuckorean',
    0x3149: 'ssangcieuckorean',
    0x314A: 'chieuchkorean',
    0x314B: 'khieukhkorean',
    0x314C: 'thieuthkorean',
    0x314D: 'phieuphkorean',
    0x314E: 'hieuhkorean',
    0x314F: 'akorean',
    0x3150: 'aekorean',
    0x3151: 'yakorean',
    0x3152: 'yaekorean',
    0x3153: 'eokorean',
    0x3154: 'ekorean',
    0x3155: 'yeokorean',
    0x3156: 'yekorean',
    0x3157: 'okorean',
    0x3158: 'wakorean',
    0x3159: 'waekorean',
    0x315A: 'oekorean',
    0x315B: 'yokorean',
    0x315C: 'ukorean',
    0x315D: 'weokorean',
    0x315E: 'wekorean',
    0x315F: 'wikorean',
    0x3160: 'yukorean',
    0x3161: 'eukorean',
    0x3162: 'yikorean',
    0x3163: 'ikorean',
    0x3164: 'hangulfiller',
    0x3165: 'ssangnieunkorean',
    0x3166: 'nieuntikeutkorean',
    0x3167: 'nieunsioskorean',
    0x3168: 'nieunpansioskorean',
    0x3169: 'rieulkiyeoksioskorean',
    0x316A: 'rieultikeutkorean',
    0x316B: 'rieulpieupsioskorean',
    0x316C: 'rieulpansioskorean',
    0x316D: 'rieulyeorinhieuhkorean',
    0x316E: 'mieumpieupkorean',
    0x316F: 'mieumsioskorean',
    0x3170: 'mieumpansioskorean',
    0x3171: 'kapyeounmieumkorean',
    0x3172: 'pieupkiyeokkorean',
    0x3173: 'pieuptikeutkorean',
    0x3174: 'pieupsioskiyeokkorean',
    0x3175: 'pieupsiostikeutkorean',
    0x3176: 'pieupcieuckorean',
    0x3177: 'pieupthieuthkorean',
    0x3178: 'kapyeounpieupkorean',
    0x3179: 'kapyeounssangpieupkorean',
    0x317A: 'sioskiyeokkorean',
    0x317B: 'siosnieunkorean',
    0x317C: 'siostikeutkorean',
    0x317D: 'siospieupkorean',
    0x317E: 'sioscieuckorean',
    0x317F: 'pansioskorean',
    0x3180: 'ssangieungkorean',
    0x3181: 'yesieungkorean',
    0x3182: 'yesieungsioskorean',
    0x3183: 'yesieungpansioskorean',
    0x3184: 'kapyeounphieuphkorean',
    0x3185: 'ssanghieuhkorean',
    0x3186: 'yeorinhieuhkorean',
    0x3187: 'yoyakorean',
    0x3188: 'yoyaekorean',
    0x3189: 'yoikorean',
    0x318A: 'yuyeokorean',
    0x318B: 'yuyekorean',
    0x318C: 'yuikorean',
    0x318D: 'araeakorean',
    0x318E: 'araeaekorean',
    0x3200: 'kiyeokparenkorean',
    0x3201: 'nieunparenkorean',
    0x3202: 'tikeutparenkorean',
    0x3203: 'rieulparenkorean',
    0x3204: 'mieumparenkorean',
    0x3205: 'pieupparenkorean',
    0x3206: 'siosparenkorean',
    0x3207: 'ieungparenkorean',
    0x3208: 'cieucparenkorean',
    0x3209: 'chieuchparenkorean',
    0x320A: 'khieukhparenkorean',
    0x320B: 'thieuthparenkorean',
    0x320C: 'phieuphparenkorean',
    0x320D: 'hieuhparenkorean',
    0x320E: 'kiyeokaparenkorean',
    0x320F: 'nieunaparenkorean',
    0x3210: 'tikeutaparenkorean',
    0x3211: 'rieulaparenkorean',
    0x3212: 'mieumaparenkorean',
    0x3213: 'pieupaparenkorean',
    0x3214: 'siosaparenkorean',
    0x3215: 'ieungaparenkorean',
    0x3216: 'cieucaparenkorean',
    0x3217: 'chieuchaparenkorean',
    0x3218: 'khieukhaparenkorean',
    0x3219: 'thieuthaparenkorean',
    0x321A: 'phieuphaparenkorean',
    0x321B: 'hieuhaparenkorean',
    0x321C: 'cieucuparenkorean',
    0x3220: 'oneideographicparen',
    0x3221: 'twoideographicparen',
    0x3222: 'threeideographicparen',
    0x3223: 'fourideographicparen',
    0x3224: 'fiveideographicparen',
    0x3225: 'sixideographicparen',
    0x3226: 'sevenideographicparen',
    0x3227: 'eightideographicparen',
    0x3228: 'nineideographicparen',
    0x3229: 'tenideographicparen',
    0x322A: 'ideographicmoonparen',
    0x322B: 'ideographicfireparen',
    0x322C: 'ideographicwaterparen',
    0x322D: 'ideographicwoodparen',
    0x322E: 'ideographicmetalparen',
    0x322F: 'ideographicearthparen',
    0x3230: 'ideographicsunparen',
    0x3231: 'ideographicstockparen',
    0x3232: 'ideographichaveparen',
    0x3233: 'ideographicsocietyparen',
    0x3234: 'ideographicnameparen',
    0x3235: 'ideographicspecialparen',
    0x3236: 'ideographicfinancialparen',
    0x3237: 'ideographiccongratulationparen',
    0x3238: 'ideographiclaborparen',
    0x3239: 'ideographicrepresentparen',
    0x323A: 'ideographiccallparen',
    0x323B: 'ideographicstudyparen',
    0x323C: 'ideographicsuperviseparen',
    0x323D: 'ideographicenterpriseparen',
    0x323E: 'ideographicresourceparen',
    0x323F: 'ideographicallianceparen',
    0x3240: 'ideographicfestivalparen',
    0x3242: 'ideographicselfparen',
    0x3243: 'ideographicreachparen',
    0x3260: 'kiyeokcirclekorean',
    0x3261: 'nieuncirclekorean',
    0x3262: 'tikeutcirclekorean',
    0x3263: 'rieulcirclekorean',
    0x3264: 'mieumcirclekorean',
    0x3265: 'pieupcirclekorean',
    0x3266: 'sioscirclekorean',
    0x3267: 'ieungcirclekorean',
    0x3268: 'cieuccirclekorean',
    0x3269: 'chieuchcirclekorean',
    0x326A: 'khieukhcirclekorean',
    0x326B: 'thieuthcirclekorean',
    0x326C: 'phieuphcirclekorean',
    0x326D: 'hieuhcirclekorean',
    0x326E: 'kiyeokacirclekorean',
    0x326F: 'nieunacirclekorean',
    0x3270: 'tikeutacirclekorean',
    0x3271: 'rieulacirclekorean',
    0x3272: 'mieumacirclekorean',
    0x3273: 'pieupacirclekorean',
    0x3274: 'siosacirclekorean',
    0x3275: 'ieungacirclekorean',
    0x3276: 'cieucacirclekorean',
    0x3277: 'chieuchacirclekorean',
    0x3278: 'khieukhacirclekorean',
    0x3279: 'thieuthacirclekorean',
    0x327A: 'phieuphacirclekorean',
    0x327B: 'hieuhacirclekorean',
    0x327F: 'koreanstandardsymbol',
    0x328A: 'ideographmooncircle',
    0x328B: 'ideographfirecircle',
    0x328C: 'ideographwatercircle',
    0x328D: 'ideographwoodcircle',
    0x328E: 'ideographmetalcircle',
    0x328F: 'ideographearthcircle',
    0x3290: 'ideographsuncircle',
    0x3294: 'ideographnamecircle',
    0x3296: 'ideographicfinancialcircle',
    0x3298: 'ideographiclaborcircle',
    0x3299: 'ideographicsecretcircle',
    0x329D: 'ideographicexcellentcircle',
    0x329E: 'ideographicprintcircle',
    0x32A3: 'ideographiccorrectcircle',
    0x32A4: 'ideographichighcircle',
    0x32A5: 'ideographiccentrecircle',
    0x32A6: 'ideographiclowcircle',
    0x32A7: 'ideographicleftcircle',
    0x32A8: 'ideographicrightcircle',
    0x32A9: 'ideographicmedicinecircle',
    0x3300: 'apaatosquare',
    0x3303: 'aarusquare',
    0x3305: 'intisquare',
    0x330D: 'karoriisquare',
    0x3314: 'kirosquare',
    0x3315: 'kiroguramusquare',
    0x3316: 'kiromeetorusquare',
    0x3318: 'guramusquare',
    0x331E: 'kooposquare',
    0x3322: 'sentisquare',
    0x3323: 'sentosquare',
    0x3326: 'dorusquare',
    0x3327: 'tonsquare',
    0x332A: 'haitusquare',
    0x332B: 'paasentosquare',
    0x3331: 'birusquare',
    0x3333: 'huiitosquare',
    0x3336: 'hekutaarusquare',
    0x3339: 'herutusquare',
    0x333B: 'peezisquare',
    0x3342: 'hoonsquare',
    0x3347: 'mansyonsquare',
    0x3349: 'mirisquare',
    0x334A: 'miribaarusquare',
    0x334D: 'meetorusquare',
    0x334E: 'yaadosquare',
    0x3351: 'rittorusquare',
    0x3357: 'wattosquare',
    0x337B: 'heiseierasquare',
    0x337C: 'syouwaerasquare',
    0x337D: 'taisyouerasquare',
    0x337E: 'meizierasquare',
    0x337F: 'corporationsquare',
    0x3380: 'paampssquare',
    0x3381: 'nasquare',
    0x3382: 'muasquare',
    0x3383: 'masquare',
    0x3384: 'kasquare',
    0x3385: 'KBsquare',
    0x3386: 'MBsquare',
    0x3387: 'GBsquare',
    0x3388: 'calsquare',
    0x3389: 'kcalsquare',
    0x338A: 'pfsquare',
    0x338B: 'nfsquare',
    0x338C: 'mufsquare',
    0x338D: 'mugsquare',
    0x338E: 'squaremg',
    0x338F: 'squarekg',
    0x3390: 'Hzsquare',
    0x3391: 'khzsquare',
    0x3392: 'mhzsquare',
    0x3393: 'ghzsquare',
    0x3394: 'thzsquare',
    0x3395: 'mulsquare',
    0x3396: 'mlsquare',
    0x3397: 'dlsquare',
    0x3398: 'klsquare',
    0x3399: 'fmsquare',
    0x339A: 'nmsquare',
    0x339B: 'mumsquare',
    0x339C: 'squaremm',
    0x339D: 'squarecm',
    0x339E: 'squarekm',
    0x339F: 'mmsquaredsquare',
    0x33A0: 'cmsquaredsquare',
    0x33A1: 'squaremsquared',
    0x33A2: 'kmsquaredsquare',
    0x33A3: 'mmcubedsquare',
    0x33A4: 'cmcubedsquare',
    0x33A5: 'mcubedsquare',
    0x33A6: 'kmcubedsquare',
    0x33A7: 'moverssquare',
    0x33A8: 'moverssquaredsquare',
    0x33A9: 'pasquare',
    0x33AA: 'kpasquare',
    0x33AB: 'mpasquare',
    0x33AC: 'gpasquare',
    0x33AD: 'radsquare',
    0x33AE: 'radoverssquare',
    0x33AF: 'radoverssquaredsquare',
    0x33B0: 'pssquare',
    0x33B1: 'nssquare',
    0x33B2: 'mussquare',
    0x33B3: 'mssquare',
    0x33B4: 'pvsquare',
    0x33B5: 'nvsquare',
    0x33B6: 'muvsquare',
    0x33B7: 'mvsquare',
    0x33B8: 'kvsquare',
    0x33B9: 'mvmegasquare',
    0x33BA: 'pwsquare',
    0x33BB: 'nwsquare',
    0x33BC: 'muwsquare',
    0x33BD: 'mwsquare',
    0x33BE: 'kwsquare',
    0x33BF: 'mwmegasquare',
    0x33C0: 'kohmsquare',
    0x33C1: 'mohmsquare',
    0x33C2: 'amsquare',
    0x33C3: 'bqsquare',
    0x33C4: 'squarecc',
    0x33C5: 'cdsquare',
    0x33C6: 'coverkgsquare',
    0x33C7: 'cosquare',
    0x33C8: 'dbsquare',
    0x33C9: 'gysquare',
    0x33CA: 'hasquare',
    0x33CB: 'HPsquare',
    0x33CD: 'KKsquare',
    0x33CE: 'squarekmcapital',
    0x33CF: 'ktsquare',
    0x33D0: 'lmsquare',
    0x33D1: 'squareln',
    0x33D2: 'squarelog',
    0x33D3: 'lxsquare',
    0x33D4: 'mbsquare',
    0x33D5: 'squaremil',
    0x33D6: 'molsquare',
    0x33D8: 'pmsquare',
    0x33DB: 'srsquare',
    0x33DC: 'svsquare',
    0x33DD: 'wbsquare',
    0x5344: 'twentyhangzhou',
    0xF6BE: 'dotlessj',
    0xF6BF: 'LL',
    0xF6C0: 'll',
    0xF6C3: 'commaaccent',
    0xF6C4: 'afii10063',
    0xF6C5: 'afii10064',
    0xF6C6: 'afii10192',
    0xF6C7: 'afii10831',
    0xF6C8: 'afii10832',
    0xF6C9: 'Acute',
    0xF6CA: 'Caron',
    0xF6CB: 'Dieresis',
    0xF6CC: 'DieresisAcute',
    0xF6CD: 'DieresisGrave',
    0xF6CE: 'Grave',
    0xF6CF: 'Hungarumlaut',
    0xF6D0: 'Macron',
    0xF6D1: 'cyrBreve',
    0xF6D2: 'cyrFlex',
    0xF6D3: 'dblGrave',
    0xF6D4: 'cyrbreve',
    0xF6D5: 'cyrflex',
    0xF6D6: 'dblgrave',
    0xF6D7: 'dieresisacute',
    0xF6D8: 'dieresisgrave',
    0xF6D9: 'copyrightserif',
    0xF6DA: 'registerserif',
    0xF6DB: 'trademarkserif',
    0xF6DC: 'onefitted',
    0xF6DD: 'rupiah',
    0xF6DE: 'threequartersemdash',
    0xF6DF: 'centinferior',
    0xF6E0: 'centsuperior',
    0xF6E1: 'commainferior',
    0xF6E2: 'commasuperior',
    0xF6E3: 'dollarinferior',
    0xF6E4: 'dollarsuperior',
    0xF6E5: 'hypheninferior',
    0xF6E6: 'hyphensuperior',
    0xF6E7: 'periodinferior',
    0xF6E8: 'periodsuperior',
    0xF6E9: 'asuperior',
    0xF6EA: 'bsuperior',
    0xF6EB: 'dsuperior',
    0xF6EC: 'esuperior',
    0xF6ED: 'isuperior',
    0xF6EE: 'lsuperior',
    0xF6EF: 'msuperior',
    0xF6F0: 'osuperior',
    0xF6F1: 'rsuperior',
    0xF6F2: 'ssuperior',
    0xF6F3: 'tsuperior',
    0xF6F4: 'Brevesmall',
    0xF6F5: 'Caronsmall',
    0xF6F6: 'Circumflexsmall',
    0xF6F7: 'Dotaccentsmall',
    0xF6F8: 'Hungarumlautsmall',
    0xF6F9: 'Lslashsmall',
    0xF6FA: 'OEsmall',
    0xF6FB: 'Ogoneksmall',
    0xF6FC: 'Ringsmall',
    0xF6FD: 'Scaronsmall',
    0xF6FE: 'Tildesmall',
    0xF6FF: 'Zcaronsmall',
    0xF721: 'exclamsmall',
    0xF724: 'dollaroldstyle',
    0xF726: 'ampersandsmall',
    0xF730: 'zerooldstyle',
    0xF731: 'oneoldstyle',
    0xF732: 'twooldstyle',
    0xF733: 'threeoldstyle',
    0xF734: 'fouroldstyle',
    0xF735: 'fiveoldstyle',
    0xF736: 'sixoldstyle',
    0xF737: 'sevenoldstyle',
    0xF738: 'eightoldstyle',
    0xF739: 'nineoldstyle',
    0xF73F: 'questionsmall',
    0xF760: 'Gravesmall',
    0xF761: 'Asmall',
    0xF762: 'Bsmall',
    0xF763: 'Csmall',
    0xF764: 'Dsmall',
    0xF765: 'Esmall',
    0xF766: 'Fsmall',
    0xF767: 'Gsmall',
    0xF768: 'Hsmall',
    0xF769: 'Ismall',
    0xF76A: 'Jsmall',
    0xF76B: 'Ksmall',
    0xF76C: 'Lsmall',
    0xF76D: 'Msmall',
    0xF76E: 'Nsmall',
    0xF76F: 'Osmall',
    0xF770: 'Psmall',
    0xF771: 'Qsmall',
    0xF772: 'Rsmall',
    0xF773: 'Ssmall',
    0xF774: 'Tsmall',
    0xF775: 'Usmall',
    0xF776: 'Vsmall',
    0xF777: 'Wsmall',
    0xF778: 'Xsmall',
    0xF779: 'Ysmall',
    0xF77A: 'Zsmall',
    0xF7A1: 'exclamdownsmall',
    0xF7A2: 'centoldstyle',
    0xF7A8: 'Dieresissmall',
    0xF7AF: 'Macronsmall',
    0xF7B4: 'Acutesmall',
    0xF7B8: 'Cedillasmall',
    0xF7BF: 'questiondownsmall',
    0xF7E0: 'Agravesmall',
    0xF7E1: 'Aacutesmall',
    0xF7E2: 'Acircumflexsmall',
    0xF7E3: 'Atildesmall',
    0xF7E4: 'Adieresissmall',
    0xF7E5: 'Aringsmall',
    0xF7E6: 'AEsmall',
    0xF7E7: 'Ccedillasmall',
    0xF7E8: 'Egravesmall',
    0xF7E9: 'Eacutesmall',
    0xF7EA: 'Ecircumflexsmall',
    0xF7EB: 'Edieresissmall',
    0xF7EC: 'Igravesmall',
    0xF7ED: 'Iacutesmall',
    0xF7EE: 'Icircumflexsmall',
    0xF7EF: 'Idieresissmall',
    0xF7F0: 'Ethsmall',
    0xF7F1: 'Ntildesmall',
    0xF7F2: 'Ogravesmall',
    0xF7F3: 'Oacutesmall',
    0xF7F4: 'Ocircumflexsmall',
    0xF7F5: 'Otildesmall',
    0xF7F6: 'Odieresissmall',
    0xF7F8: 'Oslashsmall',
    0xF7F9: 'Ugravesmall',
    0xF7FA: 'Uacutesmall',
    0xF7FB: 'Ucircumflexsmall',
    0xF7FC: 'Udieresissmall',
    0xF7FD: 'Yacutesmall',
    0xF7FE: 'Thornsmall',
    0xF7FF: 'Ydieresissmall',
    0xF884: 'maihanakatleftthai',
    0xF885: 'saraileftthai',
    0xF886: 'saraiileftthai',
    0xF887: 'saraueleftthai',
    0xF888: 'saraueeleftthai',
    0xF889: 'maitaikhuleftthai',
    0xF88A: 'maiekupperleftthai',
    0xF88B: 'maieklowrightthai',
    0xF88C: 'maieklowleftthai',
    0xF88D: 'maithoupperleftthai',
    0xF88E: 'maitholowrightthai',
    0xF88F: 'maitholowleftthai',
    0xF890: 'maitriupperleftthai',
    0xF891: 'maitrilowrightthai',
    0xF892: 'maitrilowleftthai',
    0xF893: 'maichattawaupperleftthai',
    0xF894: 'maichattawalowrightthai',
    0xF895: 'maichattawalowleftthai',
    0xF896: 'thanthakhatupperleftthai',
    0xF897: 'thanthakhatlowrightthai',
    0xF898: 'thanthakhatlowleftthai',
    0xF899: 'nikhahitleftthai',
    0xF8E5: 'radicalex',
    0xF8E6: 'arrowvertex',
    0xF8E7: 'arrowhorizex',
    0xF8E8: 'registersans',
    0xF8E9: 'copyrightsans',
    0xF8EA: 'trademarksans',
    0xF8EB: 'parenlefttp',
    0xF8EC: 'parenleftex',
    0xF8ED: 'parenleftbt',
    0xF8EE: 'bracketlefttp',
    0xF8EF: 'bracketleftex',
    0xF8F0: 'bracketleftbt',
    0xF8F1: 'bracelefttp',
    0xF8F2: 'braceleftmid',
    0xF8F3: 'braceleftbt',
    0xF8F4: 'braceex',
    0xF8F5: 'integralex',
    0xF8F6: 'parenrighttp',
    0xF8F7: 'parenrightex',
    0xF8F8: 'parenrightbt',
    0xF8F9: 'bracketrighttp',
    0xF8FA: 'bracketrightex',
    0xF8FB: 'bracketrightbt',
    0xF8FC: 'bracerighttp',
    0xF8FD: 'bracerightmid',
    0xF8FE: 'bracerightbt',
    0xF8FF: 'apple',
    0xFB00: 'ff',
    0xFB01: 'fi',
    0xFB02: 'fl',
    0xFB03: 'ffi',
    0xFB04: 'ffl',
    0xFB1F: ('afii57705', 'doubleyodpatah', 'doubleyodpatahhebrew',
             'yodyodpatahhebrew'),
    0xFB20: 'ayinaltonehebrew',
    0xFB2A: ('afii57694', 'shinshindot', 'shinshindothebrew'),
    0xFB2B: ('afii57695', 'shinsindot', 'shinsindothebrew'),
    0xFB2C: ('shindageshshindot', 'shindageshshindothebrew'),
    0xFB2D: ('shindageshsindot', 'shindageshsindothebrew'),
    0xFB2E: 'alefpatahhebrew',
    0xFB2F: 'alefqamatshebrew',
    0xFB30: 'alefdageshhebrew',
    0xFB31: ('betdagesh', 'betdageshhebrew'),
    0xFB32: ('gimeldagesh', 'gimeldageshhebrew'),
    0xFB33: ('daletdagesh', 'daletdageshhebrew'),
    0xFB34: ('hedagesh', 'hedageshhebrew'),
    0xFB35: ('afii57723', 'vavdagesh', 'vavdagesh65', 'vavdageshhebrew'),
    0xFB36: ('zayindagesh', 'zayindageshhebrew'),
    0xFB38: ('tetdagesh', 'tetdageshhebrew'),
    0xFB39: ('yoddagesh', 'yoddageshhebrew'),
    0xFB3A: ('finalkafdagesh', 'finalkafdageshhebrew'),
    0xFB3B: ('kafdagesh', 'kafdageshhebrew'),
    0xFB3C: ('lameddagesh', 'lameddageshhebrew'),
    0xFB3E: ('memdagesh', 'memdageshhebrew'),
    0xFB40: ('nundagesh', 'nundageshhebrew'),
    0xFB41: ('samekhdagesh', 'samekhdageshhebrew'),
    0xFB43: 'pefinaldageshhebrew',
    0xFB44: ('pedagesh', 'pedageshhebrew'),
    0xFB46: ('tsadidagesh', 'tsadidageshhebrew'),
    0xFB47: ('qofdagesh', 'qofdageshhebrew'),
    0xFB48: 'reshdageshhebrew',
    0xFB49: ('shindagesh', 'shindageshhebrew'),
    0xFB4A: ('tavdages', 'tavdagesh', 'tavdageshhebrew'),
    0xFB4B: ('afii57700', 'vavholam', 'vavholamhebrew'),
    0xFB4C: 'betrafehebrew',
    0xFB4D: 'kafrafehebrew',
    0xFB4E: 'perafehebrew',
    0xFB4F: 'aleflamedhebrew',
    0xFB57: 'pehfinalarabic',
    0xFB58: 'pehinitialarabic',
    0xFB59: 'pehmedialarabic',
    0xFB67: 'ttehfinalarabic',
    0xFB68: 'ttehinitialarabic',
    0xFB69: 'ttehmedialarabic',
    0xFB6B: 'vehfinalarabic',
    0xFB6C: 'vehinitialarabic',
    0xFB6D: 'vehmedialarabic',
    0xFB7B: 'tchehfinalarabic',
    0xFB7C: 'tchehinitialarabic',
#    0xFB7C FEE4: 'tchehmeeminitialarabic',
    0xFB7D: 'tchehmedialarabic',
    0xFB89: 'ddalfinalarabic',
    0xFB8B: 'jehfinalarabic',
    0xFB8D: 'rrehfinalarabic',
    0xFB93: 'gaffinalarabic',
    0xFB94: 'gafinitialarabic',
    0xFB95: 'gafmedialarabic',
    0xFB9F: 'noonghunnafinalarabic',
    0xFBA4: 'hehhamzaaboveisolatedarabic',
    0xFBA5: 'hehhamzaabovefinalarabic',
    0xFBA7: 'hehfinalaltonearabic',
    0xFBA8: 'hehinitialaltonearabic',
    0xFBA9: 'hehmedialaltonearabic',
    0xFBAF: 'yehbarreefinalarabic',
    0xFC08: 'behmeemisolatedarabic',
    0xFC0B: 'tehjeemisolatedarabic',
    0xFC0C: 'tehhahisolatedarabic',
    0xFC0E: 'tehmeemisolatedarabic',
    0xFC48: 'meemmeemisolatedarabic',
    0xFC4B: 'noonjeemisolatedarabic',
    0xFC4E: 'noonmeemisolatedarabic',
    0xFC58: 'yehmeemisolatedarabic',
    0xFC5E: 'shaddadammatanarabic',
    0xFC5F: 'shaddakasratanarabic',
    0xFC60: 'shaddafathaarabic',
    0xFC61: 'shaddadammaarabic',
    0xFC62: 'shaddakasraarabic',
    0xFC6D: 'behnoonfinalarabic',
    0xFC73: 'tehnoonfinalarabic',
    0xFC8D: 'noonnoonfinalarabic',
    0xFC94: 'yehnoonfinalarabic',
    0xFC9F: 'behmeeminitialarabic',
    0xFCA1: 'tehjeeminitialarabic',
    0xFCA2: 'tehhahinitialarabic',
    0xFCA4: 'tehmeeminitialarabic',
    0xFCC9: 'lamjeeminitialarabic',
    0xFCCA: 'lamhahinitialarabic',
    0xFCCB: 'lamkhahinitialarabic',
    0xFCCC: 'lammeeminitialarabic',
    0xFCD1: 'meemmeeminitialarabic',
    0xFCD2: 'noonjeeminitialarabic',
    0xFCD5: 'noonmeeminitialarabic',
    0xFCDD: 'yehmeeminitialarabic',
    0xFD3E: 'parenleftaltonearabic',
    0xFD3F: 'parenrightaltonearabic',
    0xFD88: 'lammeemhahinitialarabic',
    0xFDF2: 'lamlamhehisolatedarabic',
    0xFDFA: 'sallallahoualayhewasallamarabic',
    0xFE30: 'twodotleadervertical',
    0xFE31: 'emdashvertical',
    0xFE32: 'endashvertical',
    0xFE33: 'underscorevertical',
    0xFE34: 'wavyunderscorevertical',
    0xFE35: 'parenleftvertical',
    0xFE36: 'parenrightvertical',
    0xFE37: 'braceleftvertical',
    0xFE38: 'bracerightvertical',
    0xFE39: 'tortoiseshellbracketleftvertical',
    0xFE3A: 'tortoiseshellbracketrightvertical',
    0xFE3B: 'blacklenticularbracketleftvertical',
    0xFE3C: 'blacklenticularbracketrightvertical',
    0xFE3D: 'dblanglebracketleftvertical',
    0xFE3E: 'dblanglebracketrightvertical',
    0xFE3F: 'anglebracketleftvertical',
    0xFE40: 'anglebracketrightvertical',
    0xFE41: 'cornerbracketleftvertical',
    0xFE42: 'cornerbracketrightvertical',
    0xFE43: 'whitecornerbracketleftvertical',
    0xFE44: 'whitecornerbracketrightvertical',
    0xFE49: 'overlinedashed',
    0xFE4A: 'overlinecenterline',
    0xFE4B: 'overlinewavy',
    0xFE4C: 'overlinedblwavy',
    0xFE4D: 'lowlinedashed',
    0xFE4E: 'lowlinecenterline',
    0xFE4F: 'underscorewavy',
    0xFE50: 'commasmall',
    0xFE52: 'periodsmall',
    0xFE54: 'semicolonsmall',
    0xFE55: 'colonsmall',
    0xFE59: 'parenleftsmall',
    0xFE5A: 'parenrightsmall',
    0xFE5B: 'braceleftsmall',
    0xFE5C: 'bracerightsmall',
    0xFE5D: 'tortoiseshellbracketleftsmall',
    0xFE5E: 'tortoiseshellbracketrightsmall',
    0xFE5F: 'numbersignsmall',
    0xFE61: 'asterisksmall',
    0xFE62: 'plussmall',
    0xFE63: 'hyphensmall',
    0xFE64: 'lesssmall',
    0xFE65: 'greatersmall',
    0xFE66: 'equalsmall',
    0xFE69: 'dollarsmall',
    0xFE6A: 'percentsmall',
    0xFE6B: 'atsmall',
    0xFE82: 'alefmaddaabovefinalarabic',
    0xFE84: 'alefhamzaabovefinalarabic',
    0xFE86: 'wawhamzaabovefinalarabic',
    0xFE88: 'alefhamzabelowfinalarabic',
    0xFE8A: 'yehhamzaabovefinalarabic',
    0xFE8B: 'yehhamzaaboveinitialarabic',
    0xFE8C: 'yehhamzaabovemedialarabic',
    0xFE8E: 'aleffinalarabic',
    0xFE90: 'behfinalarabic',
    0xFE91: 'behinitialarabic',
    0xFE92: 'behmedialarabic',
    0xFE94: 'tehmarbutafinalarabic',
    0xFE96: 'tehfinalarabic',
    0xFE97: 'tehinitialarabic',
    0xFE98: 'tehmedialarabic',
    0xFE9A: 'thehfinalarabic',
    0xFE9B: 'thehinitialarabic',
    0xFE9C: 'thehmedialarabic',
    0xFE9E: 'jeemfinalarabic',
    0xFE9F: 'jeeminitialarabic',
    0xFEA0: 'jeemmedialarabic',
    0xFEA2: 'hahfinalarabic',
    0xFEA3: 'hahinitialarabic',
    0xFEA4: 'hahmedialarabic',
    0xFEA6: 'khahfinalarabic',
    0xFEA7: 'khahinitialarabic',
    0xFEA8: 'khahmedialarabic',
    0xFEAA: 'dalfinalarabic',
    0xFEAC: 'thalfinalarabic',
    0xFEAE: 'rehfinalarabic',
    0xFEB0: 'zainfinalarabic',
    0xFEB2: 'seenfinalarabic',
    0xFEB3: 'seeninitialarabic',
    0xFEB4: 'seenmedialarabic',
    0xFEB6: 'sheenfinalarabic',
    0xFEB7: 'sheeninitialarabic',
    0xFEB8: 'sheenmedialarabic',
    0xFEBA: 'sadfinalarabic',
    0xFEBB: 'sadinitialarabic',
    0xFEBC: 'sadmedialarabic',
    0xFEBE: 'dadfinalarabic',
    0xFEBF: 'dadinitialarabic',
    0xFEC0: 'dadmedialarabic',
    0xFEC2: 'tahfinalarabic',
    0xFEC3: 'tahinitialarabic',
    0xFEC4: 'tahmedialarabic',
    0xFEC6: 'zahfinalarabic',
    0xFEC7: 'zahinitialarabic',
    0xFEC8: 'zahmedialarabic',
    0xFECA: 'ainfinalarabic',
    0xFECB: 'aininitialarabic',
    0xFECC: 'ainmedialarabic',
    0xFECE: 'ghainfinalarabic',
    0xFECF: 'ghaininitialarabic',
    0xFED0: 'ghainmedialarabic',
    0xFED2: 'fehfinalarabic',
    0xFED3: 'fehinitialarabic',
    0xFED4: 'fehmedialarabic',
    0xFED6: 'qaffinalarabic',
    0xFED7: 'qafinitialarabic',
    0xFED8: 'qafmedialarabic',
    0xFEDA: 'kaffinalarabic',
    0xFEDB: 'kafinitialarabic',
    0xFEDC: 'kafmedialarabic',
    0xFEDE: 'lamfinalarabic',
    0xFEDF: 'laminitialarabic',
#    0xFEDF FEE4 FEA0: 'lammeemjeeminitialarabic',
#    0xFEDF FEE4 FEA8: 'lammeemkhahinitialarabic',
    0xFEE0: 'lammedialarabic',
    0xFEE2: 'meemfinalarabic',
    0xFEE3: 'meeminitialarabic',
    0xFEE4: 'meemmedialarabic',
    0xFEE6: 'noonfinalarabic',
    0xFEE7: 'nooninitialarabic',
#    0xFEE7 FEEC: 'noonhehinitialarabic',
    0xFEE8: 'noonmedialarabic',
    0xFEEA: ('hehfinalalttwoarabic', 'hehfinalarabic'),
    0xFEEB: 'hehinitialarabic',
    0xFEEC: 'hehmedialarabic',
    0xFEEE: 'wawfinalarabic',
    0xFEF0: 'alefmaksurafinalarabic',
    0xFEF2: 'yehfinalarabic',
    0xFEF3: ('alefmaksurainitialarabic', 'yehinitialarabic'),
    0xFEF4: ('alefmaksuramedialarabic', 'yehmedialarabic'),
    0xFEF5: 'lamalefmaddaaboveisolatedarabic',
    0xFEF6: 'lamalefmaddaabovefinalarabic',
    0xFEF7: 'lamalefhamzaaboveisolatedarabic',
    0xFEF8: 'lamalefhamzaabovefinalarabic',
    0xFEF9: 'lamalefhamzabelowisolatedarabic',
    0xFEFA: 'lamalefhamzabelowfinalarabic',
    0xFEFB: 'lamalefisolatedarabic',
    0xFEFC: 'lamaleffinalarabic',
    0xFEFF: 'zerowidthjoiner',
    0xFF01: 'exclammonospace',
    0xFF02: 'quotedblmonospace',
    0xFF03: 'numbersignmonospace',
    0xFF04: 'dollarmonospace',
    0xFF05: 'percentmonospace',
    0xFF06: 'ampersandmonospace',
    0xFF07: 'quotesinglemonospace',
    0xFF08: 'parenleftmonospace',
    0xFF09: 'parenrightmonospace',
    0xFF0A: 'asteriskmonospace',
    0xFF0B: 'plusmonospace',
    0xFF0C: 'commamonospace',
    0xFF0D: 'hyphenmonospace',
    0xFF0E: 'periodmonospace',
    0xFF0F: 'slashmonospace',
    0xFF10: 'zeromonospace',
    0xFF11: 'onemonospace',
    0xFF12: 'twomonospace',
    0xFF13: 'threemonospace',
    0xFF14: 'fourmonospace',
    0xFF15: 'fivemonospace',
    0xFF16: 'sixmonospace',
    0xFF17: 'sevenmonospace',
    0xFF18: 'eightmonospace',
    0xFF19: 'ninemonospace',
    0xFF1A: 'colonmonospace',
    0xFF1B: 'semicolonmonospace',
    0xFF1C: 'lessmonospace',
    0xFF1D: 'equalmonospace',
    0xFF1E: 'greatermonospace',
    0xFF1F: 'questionmonospace',
    0xFF20: 'atmonospace',
    0xFF21: 'Amonospace',
    0xFF22: 'Bmonospace',
    0xFF23: 'Cmonospace',
    0xFF24: 'Dmonospace',
    0xFF25: 'Emonospace',
    0xFF26: 'Fmonospace',
    0xFF27: 'Gmonospace',
    0xFF28: 'Hmonospace',
    0xFF29: 'Imonospace',
    0xFF2A: 'Jmonospace',
    0xFF2B: 'Kmonospace',
    0xFF2C: 'Lmonospace',
    0xFF2D: 'Mmonospace',
    0xFF2E: 'Nmonospace',
    0xFF2F: 'Omonospace',
    0xFF30: 'Pmonospace',
    0xFF31: 'Qmonospace',
    0xFF32: 'Rmonospace',
    0xFF33: 'Smonospace',
    0xFF34: 'Tmonospace',
    0xFF35: 'Umonospace',
    0xFF36: 'Vmonospace',
    0xFF37: 'Wmonospace',
    0xFF38: 'Xmonospace',
    0xFF39: 'Ymonospace',
    0xFF3A: 'Zmonospace',
    0xFF3B: 'bracketleftmonospace',
    0xFF3C: 'backslashmonospace',
    0xFF3D: 'bracketrightmonospace',
    0xFF3E: 'asciicircummonospace',
    0xFF3F: 'underscoremonospace',
    0xFF40: 'gravemonospace',
    0xFF41: 'amonospace',
    0xFF42: 'bmonospace',
    0xFF43: 'cmonospace',
    0xFF44: 'dmonospace',
    0xFF45: 'emonospace',
    0xFF46: 'fmonospace',
    0xFF47: 'gmonospace',
    0xFF48: 'hmonospace',
    0xFF49: 'imonospace',
    0xFF4A: 'jmonospace',
    0xFF4B: 'kmonospace',
    0xFF4C: 'lmonospace',
    0xFF4D: 'mmonospace',
    0xFF4E: 'nmonospace',
    0xFF4F: 'omonospace',
    0xFF50: 'pmonospace',
    0xFF51: 'qmonospace',
    0xFF52: 'rmonospace',
    0xFF53: 'smonospace',
    0xFF54: 'tmonospace',
    0xFF55: 'umonospace',
    0xFF56: 'vmonospace',
    0xFF57: 'wmonospace',
    0xFF58: 'xmonospace',
    0xFF59: 'ymonospace',
    0xFF5A: 'zmonospace',
    0xFF5B: 'braceleftmonospace',
    0xFF5C: 'barmonospace',
    0xFF5D: 'bracerightmonospace',
    0xFF5E: 'asciitildemonospace',
    0xFF61: 'periodhalfwidth',
    0xFF62: 'cornerbracketlefthalfwidth',
    0xFF63: 'cornerbracketrighthalfwidth',
    0xFF64: 'ideographiccommaleft',
    0xFF65: 'middledotkatakanahalfwidth',
    0xFF66: 'wokatakanahalfwidth',
    0xFF67: 'asmallkatakanahalfwidth',
    0xFF68: 'ismallkatakanahalfwidth',
    0xFF69: 'usmallkatakanahalfwidth',
    0xFF6A: 'esmallkatakanahalfwidth',
    0xFF6B: 'osmallkatakanahalfwidth',
    0xFF6C: 'yasmallkatakanahalfwidth',
    0xFF6D: 'yusmallkatakanahalfwidth',
    0xFF6E: 'yosmallkatakanahalfwidth',
    0xFF6F: 'tusmallkatakanahalfwidth',
    0xFF70: 'katahiraprolongmarkhalfwidth',
    0xFF71: 'akatakanahalfwidth',
    0xFF72: 'ikatakanahalfwidth',
    0xFF73: 'ukatakanahalfwidth',
    0xFF74: 'ekatakanahalfwidth',
    0xFF75: 'okatakanahalfwidth',
    0xFF76: 'kakatakanahalfwidth',
    0xFF77: 'kikatakanahalfwidth',
    0xFF78: 'kukatakanahalfwidth',
    0xFF79: 'kekatakanahalfwidth',
    0xFF7A: 'kokatakanahalfwidth',
    0xFF7B: 'sakatakanahalfwidth',
    0xFF7C: 'sikatakanahalfwidth',
    0xFF7D: 'sukatakanahalfwidth',
    0xFF7E: 'sekatakanahalfwidth',
    0xFF7F: 'sokatakanahalfwidth',
    0xFF80: 'takatakanahalfwidth',
    0xFF81: 'tikatakanahalfwidth',
    0xFF82: 'tukatakanahalfwidth',
    0xFF83: 'tekatakanahalfwidth',
    0xFF84: 'tokatakanahalfwidth',
    0xFF85: 'nakatakanahalfwidth',
    0xFF86: 'nikatakanahalfwidth',
    0xFF87: 'nukatakanahalfwidth',
    0xFF88: 'nekatakanahalfwidth',
    0xFF89: 'nokatakanahalfwidth',
    0xFF8A: 'hakatakanahalfwidth',
    0xFF8B: 'hikatakanahalfwidth',
    0xFF8C: 'hukatakanahalfwidth',
    0xFF8D: 'hekatakanahalfwidth',
    0xFF8E: 'hokatakanahalfwidth',
    0xFF8F: 'makatakanahalfwidth',
    0xFF90: 'mikatakanahalfwidth',
    0xFF91: 'mukatakanahalfwidth',
    0xFF92: 'mekatakanahalfwidth',
    0xFF93: 'mokatakanahalfwidth',
    0xFF94: 'yakatakanahalfwidth',
    0xFF95: 'yukatakanahalfwidth',
    0xFF96: 'yokatakanahalfwidth',
    0xFF97: 'rakatakanahalfwidth',
    0xFF98: 'rikatakanahalfwidth',
    0xFF99: 'rukatakanahalfwidth',
    0xFF9A: 'rekatakanahalfwidth',
    0xFF9B: 'rokatakanahalfwidth',
    0xFF9C: 'wakatakanahalfwidth',
    0xFF9D: 'nkatakanahalfwidth',
    0xFF9E: 'voicedmarkkanahalfwidth',
    0xFF9F: 'semivoicedmarkkanahalfwidth',
    0xFFE0: 'centmonospace',
    0xFFE1: 'sterlingmonospace',
    0xFFE3: 'macronmonospace',
    0xFFE5: 'yenmonospace'}


# from the Adobe Standard Encoding to Unicode table 1.0 (2011 July 12)
# by the Unicode Consortium
ADOBE_STANDARD_TO_UNICODE = {
    'space': 0x20,
    'exclam': 0x21,
    'quotedbl': 0x22,
    'numbersign': 0x23,
    'dollar': 0x24,
    'percent': 0x25,
    'ampersand': 0x26,
    'quoteright': 0x27,
    'parenleft': 0x28,
    'parenright': 0x29,
    'asterisk': 0x2A,
    'plus': 0x2B,
    'comma': 0x2C,
    'hyphen': 0x2D,
    'period': 0x2E,
    'slash': 0x2F,
    'zero': 0x30,
    'one': 0x31,
    'two': 0x32,
    'three': 0x33,
    'four': 0x34,
    'five': 0x35,
    'six': 0x36,
    'seven': 0x37,
    'eight': 0x38,
    'nine': 0x39,
    'colon': 0x3A,
    'semicolon': 0x3B,
    'less': 0x3C,
    'equal': 0x3D,
    'greater': 0x3E,
    'question': 0x3F,
    'at': 0x40,
    'A': 0x41,
    'B': 0x42,
    'C': 0x43,
    'D': 0x44,
    'E': 0x45,
    'F': 0x46,
    'G': 0x47,
    'H': 0x48,
    'I': 0x49,
    'J': 0x4A,
    'K': 0x4B,
    'L': 0x4C,
    'M': 0x4D,
    'N': 0x4E,
    'O': 0x4F,
    'P': 0x50,
    'Q': 0x51,
    'R': 0x52,
    'S': 0x53,
    'T': 0x54,
    'U': 0x55,
    'V': 0x56,
    'W': 0x57,
    'X': 0x58,
    'Y': 0x59,
    'Z': 0x5A,
    'bracketleft': 0x5B,
    'backslash': 0x5C,
    'bracketright': 0x5D,
    'asciicircum': 0x5E,
    'underscore': 0x5F,
    'quoteleft': 0x60,
    'a': 0x61,
    'b': 0x62,
    'c': 0x63,
    'd': 0x64,
    'e': 0x65,
    'f': 0x66,
    'g': 0x67,
    'h': 0x68,
    'i': 0x69,
    'j': 0x6A,
    'k': 0x6B,
    'l': 0x6C,
    'm': 0x6D,
    'n': 0x6E,
    'o': 0x6F,
    'p': 0x70,
    'q': 0x71,
    'r': 0x72,
    's': 0x73,
    't': 0x74,
    'u': 0x75,
    'v': 0x76,
    'w': 0x77,
    'x': 0x78,
    'y': 0x79,
    'z': 0x7A,
    'braceleft': 0x7B,
    'bar': 0x7C,
    'braceright': 0x7D,
    'asciitilde': 0x7E,
    'exclamdown': 0xA1,
    'cent': 0xA2,
    'sterling': 0xA3,
    'fraction': 0xA4,
    'yen': 0xA5,
    'florin': 0xA6,
    'section': 0xA7,
    'currency': 0xA8,
    'quotesingle': 0xA9,
    'quotedblleft': 0xAA,
    'guillemotleft': 0xAB,
    'guilsinglleft': 0xAC,
    'guilsinglright': 0xAD,
    'fi': 0xAE,
    'fl': 0xAF,
    'endash': 0xB1,
    'dagger': 0xB2,
    'daggerdbl': 0xB3,
    'periodcentered': 0xB4,
    'paragraph': 0xB6,
    'bullet': 0xB7,
    'quotesinglbase': 0xB8,
    'quotedblbase': 0xB9,
    'quotedblright': 0xBA,
    'guillemotright': 0xBB,
    'ellipsis': 0xBC,
    'perthousand': 0xBD,
    'questiondown': 0xBF,
    'grave': 0xC1,
    'acute': 0xC2,
    'circumflex': 0xC3,
    'tilde': 0xC4,
    'macron': 0xC5,
    'breve': 0xC6,
    'dotaccent': 0xC7,
    'dieresis': 0xC8,
    'ring': 0xCA,
    'cedilla': 0xCB,
    'hungarumlaut': 0xCD,
    'ogonek': 0xCE,
    'caron': 0xCF,
    'emdash': 0xD0,
    'AE': 0xE1,
    'ordfeminine': 0xE3,
    'Lslash': 0xE8,
    'Oslash': 0xE9,
    'OE': 0xEA,
    'ordmasculine': 0xEB,
    'ae': 0xF1,
    'dotlessi': 0xF5,
    'lslash': 0xF8,
    'oslash': 0xF9,
    'oe': 0xFA,
    'germandbls': 0xFB} # LATIN SMALL LETTER SHARP S


ENCODINGS = {'AdobeStandardEncoding': ADOBE_STANDARD_TO_UNICODE}

########NEW FILE########
__FILENAME__ = cff
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


import struct

from binascii import hexlify
from io import BytesIO


def grab(file, data_format):
    data = file.read(struct.calcsize(data_format))
    return struct.unpack('>' + data_format, data)


card8 = lambda file: grab(file, 'B')[0]
card16 = lambda file: grab(file, 'h')[0]
offsize = card8

def offset(offset_size):
    return lambda file: grab(file, ('B', 'H', 'I', 'L')[offset_size - 1])[0]


class Section(dict):
    def __init__(self, file, offset=None):
        if offset:
            file.seek(offset)
        for name, reader in self.entries:
            self[name] = reader(file)


class Header(Section):
    entries = [('major', card8),
               ('minor', card8),
               ('hdrSize', card8),
               ('offSize', card8)]


class OperatorExeption(Exception):
    def __init__(self, code):
        self.code = code


class Operator(object):
    def __init__(self, name, type, default=None):
        self.name = name
        self.type = type
        self.default = default

    def __repr__(self):
        return "<Operator {}>".format(self.name)


number = lambda array: array[0]
sid = number
boolean = lambda array: number(array) == 1
array = lambda array: array

def delta(array):
    delta = []
    last_value = 0
    for item in array:
        delta.append(last_value + item)
        last_value = item


class Dict(dict):
    # values (operands) - key (operator) pairs
    def __init__(self, file, length, offset=None):
        if offset is not None:
            file.seek(offset)
        else:
            offset = file.tell()
        operands = []
        while file.tell() < offset + length:
            try:
                operands.append(self._next_token(file))
            except OperatorExeption as e:
                operator = self.operators[e.code]
                self[operator.name] = operator.type(operands)
                operands = []

    def _next_token(self, file):
        b0 = card8(file)
        if b0 == 12:
            raise OperatorExeption((12, card8(file)))
        elif b0 <= 22:
            raise OperatorExeption(b0)
        elif b0 == 28:
            return grab(file, 'h')[0]
        elif b0 == 29:
            return grab(file, 'i')[0]
        elif b0 == 30: # real
            real_string = ''
            while True:
                real_string += hexlify(file.read(1)).decode('ascii')
                if 'f' in real_string:
                    real_string = (real_string.replace('a', '.')
                                              .replace('b', 'E')
                                              .replace('c', 'E-')
                                              .replace('e', '-')
                                              .rstrip('f'))
                    return float(real_string)
        elif b0 < 32:
            raise NotImplementedError()
        elif b0 < 247:
            return b0 - 139
        elif b0 < 251:
            b1 = card8(file)
            return (b0 - 247) * 256 + b1 + 108
        elif b0 < 255:
            b1 = card8(file)
            return - (b0 - 251) * 256 - b1 - 108
        else:
            raise NotImplementedError()


class TopDict(Dict):
    operators = {0: Operator('version', sid),
                 1: Operator('Notice', sid),
                 (12, 0): Operator('Copyright', sid),
                 2: Operator('FullName', sid),
                 3: Operator('FamilyName', sid),
                 4: Operator('Weight', sid),
                 (12, 1): Operator('isFixedPitch', boolean, False),
                 (12, 2): Operator('ItalicAngle', number, 0),
                 (12, 3): Operator('UnderlinePosition', number, -100),
                 (12, 4): Operator('UnderlineThickness', number, 50),
                 (12, 5): Operator('PaintType', number, 0),
                 (12, 6): Operator('CharstringType', number, 2),
                 (12, 7): Operator('FontMatrix', array, [0.001, 0, 0, 0.001, 0, 0]),
                 13: Operator('UniqueID', number),
                 5: Operator('FontBBox', array, [0, 0, 0, 0]),
                 (12, 8): Operator('StrokeWidth', number, 0),
                 14: Operator('XUID', array),
                 15: Operator('charset', number, 0), # charset offset (0)
                 16: Operator('Encoding', number, 0), # encoding offset (0)
                 17: Operator('CharStrings', number), # CharStrings offset (0)
                 18: Operator('Private', array), # Private DICT size
                                                           # and offset (0)
                 (12, 20): Operator('SyntheticBase', number), # synthetic base font index
                 (12, 21): Operator('PostScript', sid), # embedded PostScript language code
                 (12, 22): Operator('BaseFontName', sid), # (added as needed by Adobe-based technology)
                 (12, 23): Operator('BaseFontBlend', delta)} # (added as needed by Adobe-based technology)


class Index(list):
    """Array of variable-sized objects"""
    def __init__(self, file, offset_=None):
        if offset_ is not None:
            file.seek(offset_)
        count = card16(file)
        offset_size = card8(file)
        self.offsets = []
        self.sizes = []
        for i in range(count + 1):
            self.offsets.append(offset(offset_size)(file))
        self.offset_reference = file.tell() - 1
        for i in range(count):
            self.sizes.append(self.offsets[i + 1] - self.offsets[i])


class NameIndex(Index):
    def __init__(self, file, offset=None):
        super().__init__(file, offset)
        for name_offset, size in zip(self.offsets, self.sizes):
            file.seek(self.offset_reference + name_offset)
            name = file.read(size).decode('ascii')
            self.append(name)


class TopDictIndex(Index):
    def __init__(self, file, offset=None):
        super().__init__(file, offset)
        for dict_offset, size in zip(self.offsets, self.sizes):
            self.append(TopDict(file, size, self.offset_reference + dict_offset))


class CompactFontFormat(object):
    def __init__(self, file, offset):
        if offset is not None:
            file.seek(offset)
        self.header = Header(file)
        assert self.header['major'] == 1
        self.name = NameIndex(file, offset + self.header['hdrSize'])
        self.top_dicts = TopDictIndex(file)
        #String INDEX
        #Global Subr INDEX
        # -------------------
        #Encodings
        #Charsets
        #FDSelect (CIDFonts only)
        #CharStrings INDEX (per-font) <=========================================
        #Font DICT INDEX (per-font, CIDFonts only)
        #Private DICT (per-font)
        #Local Subr INDEX (per-font or per-Private DICT for CIDFonts)
        #Copyright and Trademark Notices

########NEW FILE########
__FILENAME__ = gpos
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


import struct

from .parse import OpenTypeTable, MultiFormatTable, Record
from .parse import fixed, int16, uint16, tag, glyph_id, offset, Packed
from .parse import array, context, context_array, indirect, indirect_array
from .layout import LayoutTable, ScriptListTable, FeatureListTable, LookupTable
from .layout import Coverage, ClassDefinition, Device
from ...util import cached_property


class ValueFormat(Packed):
    reader = uint16
    fields = [('XPlacement', 0x0001, bool),
              ('YPlacement', 0x0002, bool),
              ('XAdvance', 0x0004, bool),
              ('YAdvance', 0x0008, bool),
              ('XPlaDevice', 0x0010, bool),
              ('YPlaDevice', 0x0020, bool),
              ('XAdvDevice', 0x0040, bool),
              ('YAdvDevice', 0x0080, bool)]
    formats = {'XPlacement': 'h',
               'YPlacement': 'h',
               'XAdvance': 'h',
               'YAdvance': 'h',
               'XPlaDevice': 'H',
               'YPlaDevice': 'H',
               'XAdvDevice': 'H',
               'YAdvDevice': 'H'}

    @cached_property
    def data_format(self):
        data_format = ''
        for name, present in self.items():
            if present:
                data_format += self.formats[name]
        return data_format

    @cached_property
    def present_keys(self):
        keys = []
        for name, present in self.items():
            if present:
                keys.append(name)
        return keys


class ValueRecord(OpenTypeTable):
    formats = {'XPlacement': int16,
               'YPlacement': int16,
               'XAdvance': int16,
               'YAdvance': int16,
               'XPlaDevice': indirect(Device),
               'YPlaDevice': indirect(Device),
               'XAdvDevice': indirect(Device),
               'YAdvDevice': indirect(Device)}

    def __init__(self, file, value_format):
        super().__init__(file)
        for name, present in value_format.items():
            if present:
                self[name] = self.formats[name](file)


class Anchor(MultiFormatTable):
    entries = [('AnchorFormat', uint16),
               ('XCoordinate', int16),
               ('YCoordinate', int16)]
    formats = {2: [('AnchorPoint', uint16)],
               3: [('XDeviceTable', indirect(Device)),
                   ('YDeviceTable', indirect(Device))]}


class MarkRecord(Record):
    entries = [('Class', uint16),
               ('MarkAnchor', indirect(Anchor))]


class MarkArray(OpenTypeTable):
    entries = [('MarkCount', uint16),
               ('MarkRecord', context_array(MarkRecord, 'MarkCount'))]


class SingleAdjustmentSubtable(MultiFormatTable):
    entries = [('PosFormat', uint16),
               ('Coverage', indirect(Coverage)),
               ('ValueFormat', ValueFormat)]
    formats = {1: [('Value', context(ValueRecord, 'ValueFormat'))],
               2: [('ValueCount', uint16),
                   ('Value', context_array(ValueRecord, 'ValueCount',
                                           'ValueFormat'))]}


class PairSetTable(OpenTypeTable):
    entries = [('PairValueCount', uint16)]

    def __init__(self, file, file_offset, format_1, format_2):
        super().__init__(file, file_offset)
        record_format = format_1.data_format + format_2.data_format
        value_1_length = len(format_1)
        format_1_keys = format_1.present_keys
        format_2_keys = format_2.present_keys
        pvr_struct = struct.Struct('>H' + record_format)
        pvr_size = pvr_struct.size
        pvr_list = []
        self.by_second_glyph_id = {}
        for i in range(self['PairValueCount']):
            record_data = pvr_struct.unpack(file.read(pvr_size))
            second_glyph = record_data[0]
            value_1 = {}
            value_2 = {}
            for i, key in enumerate(format_1_keys):
                value_1[key] = record_data[1 + i]
            for i, key in enumerate(format_2_keys):
                value_2[key] = record_data[1 + value_1_length + i]
            pvr = {'Value1': value_1,
                   'Value2': value_2}
            pvr_list.append(pvr)
            self.by_second_glyph_id[second_glyph] = pvr
        self['PairValueRecord'] = pvr_list


class PairAdjustmentSubtable(MultiFormatTable):
    entries = [('PosFormat', uint16),
               ('Coverage', indirect(Coverage)),
               ('ValueFormat1', ValueFormat),
               ('ValueFormat2', ValueFormat)]
    formats = {1: [('PairSetCount', uint16),
                   ('PairSet', indirect_array(PairSetTable, 'PairSetCount',
                                              'ValueFormat1', 'ValueFormat2'))],
               2: [('ClassDef1', indirect(ClassDefinition)),
                   ('ClassDef2', indirect(ClassDefinition)),
                   ('Class1Count', uint16),
                   ('Class2Count', uint16)]}

    def __init__(self, file, file_offset=None):
        super().__init__(file, file_offset)
        format_1, format_2 = self['ValueFormat1'], self['ValueFormat2']
        if self['PosFormat'] == 2:
            record_format = format_1.data_format + format_2.data_format
            c2r_struct = struct.Struct('>' + record_format)
            c2r_size = c2r_struct.size
            value_1_length = len(format_1)
            format_1_keys = format_1.present_keys
            format_2_keys = format_2.present_keys
            class_1_record = []
            for i in range(self['Class1Count']):
                class_2_record = []
                for j in range(self['Class2Count']):
                    record_data = c2r_struct.unpack(file.read(c2r_size))
                    value_1 = {}
                    value_2 = {}
                    for i, key in enumerate(format_1_keys):
                        value_1[key] = record_data[i]
                    for i, key in enumerate(format_2_keys):
                        value_2[key] = record_data[value_1_length + i]
                    class_2_record.append({'Value1': value_1,
                                           'Value2': value_2})
                class_1_record.append(class_2_record)
            self['Class1Record'] = class_1_record

    def lookup(self, a_id, b_id):
        if self['PosFormat'] == 1:
            try:
                index = self['Coverage'].index(a_id)
            except ValueError:
                raise KeyError
            pair_value_record = self['PairSet'][index].by_second_glyph_id[b_id]
            return pair_value_record['Value1']['XAdvance']
        elif self['PosFormat'] == 2:
            a_class = self['ClassDef1'].class_number(a_id)
            b_class = self['ClassDef2'].class_number(b_id)
            class_2_record = self['Class1Record'][a_class][b_class]
            return class_2_record['Value1']['XAdvance']


class EntryExitRecord(OpenTypeTable):
    entries = [('EntryAnchor', indirect(Anchor)),
               ('ExitAnchor', indirect(Anchor, 'EntryExitCount'))]


class CursiveAttachmentSubtable(OpenTypeTable):
    entries = [('PosFormat', uint16),
               ('Coverage', indirect(Coverage)),
               ('EntryExitCount', uint16),
               ('EntryExitRecord', context_array(EntryExitRecord, 'EntryExitCount'))]


class MarkCoverage(OpenTypeTable):
    pass


class BaseCoverage(OpenTypeTable):
    pass


class Mark2Array(OpenTypeTable):
    pass


class BaseRecord(OpenTypeTable):
##    entries = [('BaseAnchor', indirect_array(Anchor, 'ClassCount'))]

    def __init__(self, file, file_offset, class_count):
        super().__init__(self, file, file_offset)
##        self['BaseAnchor'] = indirect_array(Anchor, 'ClassCount'])(file)


class BaseArray(OpenTypeTable):
    entries = [('BaseCount', uint16)]
##               ('BaseRecord', context_array(BaseRecord, 'BaseCount'))]

    def __init__(self, file, file_offset, class_count):
        super().__init__(self, file, file_offset)
        self['BaseRecord'] = array(BaseRecord, self['BaseCount'],
                                   class_count=class_count)(file)


class MarkToBaseAttachmentSubtable(OpenTypeTable):
    entries = [('PosFormat', uint16),
               ('MarkCoverage', indirect(MarkCoverage)),
               ('BaseCoverage', indirect(BaseCoverage)),
               ('ClassCount', uint16),
               ('MarkArray', indirect(MarkArray)),
               ('BaseArray', indirect(BaseArray, 'ClassCount'))]


class MarkToMarkAttachmentSubtable(OpenTypeTable):
    entries = [('PosFormat', uint16),
               ('Mark1Coverage', indirect(MarkCoverage)),
               ('Mark1Coverage', indirect(MarkCoverage)),
               ('ClassCount', uint16),
               ('Mark1Array', indirect(MarkArray)),
               ('Mark1Array', indirect(Mark2Array))]


class GposTable(LayoutTable):
    """Glyph positioning table"""
    tag = 'GPOS'
    lookup_types = {1: SingleAdjustmentSubtable,
                    2: PairAdjustmentSubtable,
                    3: CursiveAttachmentSubtable,
                    4: MarkToBaseAttachmentSubtable,
                    6: MarkToMarkAttachmentSubtable}

########NEW FILE########
__FILENAME__ = gsub
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


from .parse import OpenTypeTable, MultiFormatTable
from .parse import fixed, int16, uint16, tag, glyph_id, offset, array, indirect
from .parse import context_array, indirect_array, Packed
from .layout import LayoutTable, ScriptListTable, FeatureListTable, LookupTable
from .layout import Coverage, ClassDefinition


# Single subsitution (subtable format 1)
class SingleSubTable(MultiFormatTable):
    entries = [('SubstFormat', uint16),
               ('Coverage', indirect(Coverage))]
    formats = {1: [('DeltaGlyphID', glyph_id)],
               2: [('GlyphCount', uint16),
                   ('Substitute', context_array(glyph_id, 'GlyphCount'))]}

    def lookup(self, glyph_id):
        try:
            index = self['Coverage'].index(glyph_id)
        except ValueError:
            raise KeyError
        if self['SubstFormat'] == 1:
            return index + self['DeltaGlyphID']
        else:
            return self['Substitute'][index]


# Alternate subtitition (subtable format 3)
class AlternateSubTable(OpenTypeTable):
    pass


# Ligature subsitution (subtable format 4)
class Ligature(OpenTypeTable):
    entries = [('LigGlyph', glyph_id),
               ('CompCount', uint16)]

    def __init__(self, file, file_offset):
        super().__init__(file, file_offset)
        self['Component'] = array(glyph_id, self['CompCount'] - 1)(file)


class LigatureSet(OpenTypeTable):
    entries = [('LigatureCount', uint16),
               ('Ligature', indirect_array(Ligature, 'LigatureCount'))]


class LigatureSubTable(OpenTypeTable):
    entries = [('SubstFormat', uint16),
               ('Coverage', indirect(Coverage)),
               ('LigSetCount', uint16),
               ('LigatureSet', indirect_array(LigatureSet, 'LigSetCount'))]

    def lookup(self, a_id, b_id):
        try:
            index = self['Coverage'].index(a_id)
        except ValueError:
            raise KeyError
        ligature_set = self['LigatureSet'][index]
        for ligature in ligature_set['Ligature']:
            if ligature['Component'] == [b_id]:
                return ligature['LigGlyph']
        raise KeyError


# Chaining contextual subsitution (subtable format 6)
class ChainSubRule(OpenTypeTable):
    pass
##    entries = [('BacktrackGlyphCount', uint16),
##               ('Backtrack', context_array(glyph_id, 'BacktrackGlyphCount')),
##               ('InputGlyphCount', uint16),
##               ('Input', context_array(glyph_id, 'InputGlyphCount',
##                                       lambda count: count - 1)),
##               ('LookaheadGlyphCount', uint16),
##               ('LookAhead', context_array(glyph_id, 'LookaheadGlyphCount')),
##               ('SubstCount', uint16),
##               ('SubstLookupRecord', context_array(glyph_id, 'SubstCount'))]


class ChainSubRuleSet(OpenTypeTable):
    entries = [('ChainSubRuleCount', uint16),
               ('ChainSubRule', indirect(ChainSubRule))]


class ChainingContextSubtable(MultiFormatTable):
    entries = [('SubstFormat', uint16)]
    formats = {1: [('Coverage', indirect(Coverage)),
                   ('ChainSubRuleSetCount', uint16),
                   ('ChainSubRuleSet', indirect_array(ChainSubRuleSet,
                                                      'ChainSubRuleSetCount'))]}


class GsubTable(LayoutTable):
    """Glyph substitution table"""
    tag = 'GSUB'
    lookup_types = {1: SingleSubTable,
                    3: AlternateSubTable,
                    4: LigatureSubTable}#,
                    #6: ChainingContextSubtable}

########NEW FILE########
__FILENAME__ = ids
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


PLATFORM_UNICODE = 0
PLATFORM_MACINTOSH = 1
PLATFORM_ISO = 2
PLATFORM_WINDOWS = 3
PLATFORM_CUSTOM = 4

LANGUAGE_WINDOWS_EN_US = 0x0409

NAME_COPYRIGHT = 0
NAME_FAMILTY = 1
NAME_SUBFAMILY = 2
NAME_UID = 3
NAME_FULL = 4
NAME_VERSION = 5
NAME_PS_NAME = 6
NAME_TRADEMARK = 7
NAME_MANUFACTURER = 8
NAME_DESIGNER = 9
NAME_DESCRIPTION = 10
NAME_VENDOR_URL = 11
NAME_DESIGNER_URL = 12
NAME_LICENSE = 13
NAME_LICENSE_URL = 14
NAME_PREFERRED_FAMILY = 16
NAME_PREFERRED_SUBFAMILY = 17
# ...

UNICODE_1_0 = 0
UNICODE_1_1 = 1
UNICODE_ISO_IEC_10646 = 2
UNICODE_2_0_BMP = 3
UNICODE_2_0_FULL = 4
UNICODE_VAR_SEQ = 5
UNICODE_FULL = 6

ISO_ASCII = 0
ISO_10646 = 1
ISO_8859_1 = 2

########NEW FILE########
__FILENAME__ = layout
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


from .parse import OpenTypeTable, MultiFormatTable, Record, context_array
from .parse import fixed, array, uint16, tag, glyph_id, offset, indirect, Packed


class ListRecord(Record):
    entries = [('Tag', tag),
               ('Offset', offset)]

    def parse_value(self, file, file_offset, entry_type):
        self['Value'] = entry_type(file, file_offset + self['Offset'])


class ListTable(OpenTypeTable):
    entry_type = None
    entries = [('Count', uint16),
               ('Record', context_array(ListRecord, 'Count'))]

    def __init__(self, file, file_offset):
        super().__init__(file, file_offset)
        self.by_tag = {}
        for record in self['Record']:
            record.parse_value(file, file_offset, self.entry_type)
            tag_list = self.by_tag.setdefault(record['Tag'], [])
            tag_list.append(record['Value'])


class LangSysTable(OpenTypeTable):
    entries = [('LookupOrder', offset),
               ('ReqFeatureIndex', uint16),
               ('FeatureCount', uint16),
               ('FeatureIndex', context_array(uint16, 'FeatureCount'))]


class ScriptTable(ListTable):
    entry_type = LangSysTable
    entries = [('DefaultLangSys', indirect(LangSysTable))] + ListTable.entries


class ScriptListTable(ListTable):
    entry_type = ScriptTable


class FeatureTable(OpenTypeTable):
    entries = [('FeatureParams', offset),
               ('LookupCount', uint16),
               ('LookupListIndex', context_array(uint16, 'LookupCount'))]

    def __init__(self, file, offset):
        super().__init__(file, offset)
        if self['FeatureParams']:
            # TODO: parse Feature Parameters
            pass
        else:
            del self['FeatureParams']


class FeatureListTable(ListTable):
    entry_type = FeatureTable


class LookupFlag(Packed):
    reader = uint16
    fields = [('RightToLeft', 0x0001, bool),
              ('IgnoreBaseGlyphs', 0x0002, bool),
              ('IgnoreLigatures', 0x0004, bool),
              ('IgnoreMarks', 0x0008, bool),
              ('UseMarkFilteringSet', 0x010, bool),
              ('MarkAttachmentType', 0xFF00, int)]


class RangeRecord(OpenTypeTable):
    entries = [('Start', glyph_id),
               ('End', glyph_id),
               ('StartCoverageIndex', uint16)]


class Coverage(MultiFormatTable):
    entries = [('CoverageFormat', uint16)]
    formats = {1: [('GlyphCount', uint16),
                   ('GlyphArray', context_array(glyph_id, 'GlyphCount'))],
               2: [('RangeCount', uint16),
                   ('RangeRecord', context_array(RangeRecord, 'RangeCount'))]}

    def index(self, glyph_id):
        if self['CoverageFormat'] == 1:
            return self['GlyphArray'].index(glyph_id)
        else:
            for record in self['RangeRecord']:
                if record['Start'] <= glyph_id <= record['End']:
                    return (record['StartCoverageIndex']
                            + glyph_id - record['Start'])
            raise ValueError


class ClassRangeRecord(OpenTypeTable):
    entries = [('Start', glyph_id),
               ('End', glyph_id),
               ('Class', uint16)]


class ClassDefinition(MultiFormatTable):
    entries = [('ClassFormat', uint16)]
    formats = {1: [('StartGlyph', glyph_id),
                   ('GlyphCount', uint16),
                   ('ClassValueArray', context_array(uint16, 'GlyphCount'))],
               2: [('ClassRangeCount', uint16),
                   ('ClassRangeRecord', context_array(ClassRangeRecord,
                                                      'ClassRangeCount'))]}

    def class_number(self, glyph_id):
        if self['ClassFormat'] == 1:
            index = glyph_id - self['StartGlyph']
            if 0 <= index < self['GlyphCount']:
                return self['ClassValueArray'][index]
        else:
            for record in self['ClassRangeRecord']:
                if record['Start'] <= glyph_id <= record['End']:
                    return record['Class']
        return 0


class LookupTable(OpenTypeTable):
    entries = [('LookupType', uint16),
               ('LookupFlag', LookupFlag),
               ('SubTableCount', uint16)]

    def __init__(self, file, file_offset, subtable_types):
        super().__init__(file, file_offset)
        offsets = array(uint16, self['SubTableCount'])(file)
        if self['LookupFlag']['UseMarkFilteringSet']:
            self['MarkFilteringSet'] = uint16(file)
        subtable_type = subtable_types[self['LookupType']]
        self['SubTable'] = [subtable_type(file, file_offset + subtable_offset)
                            for subtable_offset in offsets]

    def lookup(self, *args, **kwargs):
        for subtable in self['SubTable']:
            try:
                return subtable.lookup(*args, **kwargs)
            except KeyError:
                pass
        raise KeyError


class DelayedList(list):
    def __init__(self, reader, file, file_offset, item_offsets):
        super().__init__([None] * len(item_offsets))
        self._reader = reader
        self._file = file
        self._offsets = [file_offset + item_offset
                         for item_offset in item_offsets]

    def __getitem__(self, index):
        if super().__getitem__(index) is None:
            self[index] = self._reader(self._file, self._offsets[index])
        return super().__getitem__(index)


class LookupListTable(OpenTypeTable):
    entries = [('LookupCount', uint16)]

    def __init__(self, file, file_offset, types):
        super().__init__(file, file_offset)
        lookup_offsets = array(offset, self['LookupCount'])(file)
        lookup_reader = lambda file, file_offset: LookupTable(file, file_offset,
                                                              types)
        self['Lookup'] = DelayedList(lookup_reader, file, file_offset,
                                     lookup_offsets)


class LayoutTable(OpenTypeTable):
    entries = [('Version', fixed),
               ('ScriptList', indirect(ScriptListTable)),
               ('FeatureList', indirect(FeatureListTable))]

    def __init__(self, file, file_offset):
        super().__init__(file, file_offset)
        lookup_list_offset = offset(file)
        self['LookupList'] = LookupListTable(file,
                                             file_offset + lookup_list_offset,
                                             self.lookup_types)


class Device(OpenTypeTable):
    entries = [('StartSize', uint16),
               ('EndSize', uint16),
               ('DeltaFormat', uint16),
               ('DeltaValue', uint16)]

########NEW FILE########
__FILENAME__ = macglyphs
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


# from Apple's TrueType Reference Manual (December 18, 2003)
MAC_GLYPHS = ('.notdef',
              '.null',
              'nonmarkingreturn',
              'space',
              'exclam',
              'quotedbl',
              'numbersign',
              'dollar',
              'percent',
              'ampersand',
              'quotesingle',
              'parenleft',
              'parenright',
              'asterisk',
              'plus',
              'comma',
              'hyphen',
              'period',
              'slash',
              'zero',
              'one',
              'two',
              'three',
              'four',
              'five',
              'six',
              'seven',
              'eight',
              'nine',
              'colon',
              'semicolon',
              'less',
              'equal',
              'greater',
              'question',
              'at',
              'A',
              'B',
              'C',
              'D',
              'E',
              'F',
              'G',
              'H',
              'I',
              'J',
              'K',
              'L',
              'M',
              'N',
              'O',
              'P',
              'Q',
              'R',
              'S',
              'T',
              'U',
              'V',
              'W',
              'X',
              'Y',
              'Z',
              'bracketleft',
              'backslash',
              'bracketright',
              'asciicircum',
              'underscore',
              'grave',
              'a',
              'b',
              'c',
              'd',
              'e',
              'f',
              'g',
              'h',
              'i',
              'j',
              'k',
              'l',
              'm',
              'n',
              'o',
              'p',
              'q',
              'r',
              's',
              't',
              'u',
              'v',
              'w',
              'x',
              'y',
              'z',
              'braceleft',
              'bar',
              'braceright',
              'asciitilde',
              'Adieresis',
              'Aring',
              'Ccedilla',
              'Eacute',
              'Ntilde',
              'Odieresis',
              'Udieresis',
              'aacute',
              'agrave',
              'acircumflex',
              'adieresis',
              'atilde',
              'aring',
              'ccedilla',
              'eacute',
              'egrave',
              'ecircumflex',
              'edieresis',
              'iacute',
              'igrave',
              'icircumflex',
              'idieresis',
              'ntilde',
              'oacute',
              'ograve',
              'ocircumflex',
              'odieresis',
              'otilde',
              'uacute',
              'ugrave',
              'ucircumflex',
              'udieresis',
              'dagger',
              'degree',
              'cent',
              'sterling',
              'section',
              'bullet',
              'paragraph',
              'germandbls',
              'registered',
              'copyright',
              'trademark',
              'acute',
              'dieresis',
              'notequal',
              'AE',
              'Oslash',
              'infinity',
              'plusminus',
              'lessequal',
              'greaterequal',
              'yen',
              'mu',
              'partialdiff',
              'summation',
              'product',
              'pi',
              'integral',
              'ordfeminine',
              'ordmasculine',
              'Omega',
              'ae',
              'oslash',
              'questiondown',
              'exclamdown',
              'logicalnot',
              'radical',
              'florin',
              'approxequal',
              'Delta',
              'guillemotleft',
              'guillemotright',
              'ellipsis',
              'nonbreakingspace',
              'Agrave',
              'Atilde',
              'Otilde',
              'OE',
              'oe',
              'endash',
              'emdash',
              'quotedblleft',
              'quotedblright',
              'quoteleft',
              'quoteright',
              'divide',
              'lozenge',
              'ydieresis',
              'Ydieresis',
              'fraction',
              'currency',
              'guilsinglleft',
              'guilsinglright',
              'fi',
              'fl',
              'daggerdbl',
              'periodcentered',
              'quotesinglbase',
              'quotedblbase',
              'perthousand',
              'Acircumflex',
              'Ecircumflex',
              'Aacute',
              'Edieresis',
              'Egrave',
              'Iacute',
              'Icircumflex',
              'Idieresis',
              'Igrave',
              'Oacute',
              'Ocircumflex',
              'apple',
              'Ograve',
              'Uacute',
              'Ucircumflex',
              'Ugrave',
              'dotlessi',
              'circumflex',
              'tilde',
              'macron',
              'breve',
              'dotaccent',
              'ring',
              'cedilla',
              'hungarumlaut',
              'ogonek',
              'caron',
              'Lslash',
              'lslash',
              'Scaron',
              'scaron',
              'Zcaron',
              'zcaron',
              'brokenbar',
              'Eth',
              'eth',
              'Yacute',
              'yacute',
              'Thorn',
              'thorn',
              'minus',
              'multiply',
              'onesuperior',
              'twosuperior',
              'threesuperior',
              'onehalf',
              'onequarter',
              'threequarters',
              'franc',
              'Gbreve',
              'gbreve',
              'Idotaccent',
              'Scedilla',
              'scedilla',
              'Cacute',
              'cacute',
              'Ccaron',
              'ccaron',
              'dcroat')

########NEW FILE########
__FILENAME__ = other
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


from .parse import OpenTypeTable, ushort, fword, array, Packed


class KerningCoverage(Packed):
    reader = ushort
    fields = [('horizontal', 0x01, bool),
              ('minimum', 0x02, bool),
              ('cross-stream', 0x04, bool),
              ('override', 0x08, bool),
              ('format', 0xF0, int),]


class KernSubTable(OpenTypeTable):
    """Kerning subtable"""
    entries = [('version', ushort),
               ('length', ushort),
               ('coverage', KerningCoverage)]

    def __init__(self, file, offset):
        super().__init__(file, offset)
        if self['coverage']['format'] == 0:
            self.pairs = {}
            (n_pairs, search_range,
             entry_selector, range_shift) = array(ushort, 4)(file)
            for i in range(n_pairs):
                left, right, value = ushort(file), ushort(file), fword(file)
                left_dict = self.pairs.setdefault(left, {})
                left_dict[right] = value
        else:
            raise NotImplementedError


class KernTable(OpenTypeTable):
    """Kerning table (only for TrueType outlines)"""
    tag = 'kern'
    entries = [('version', ushort),
               ('nTables', ushort)]

    def __init__(self, file, offset):
        super().__init__(file, offset)
        for i in range(self['nTables']):
            subtable = KernSubTable(file, file.tell())
            self[subtable['coverage']['format']] = subtable

########NEW FILE########
__FILENAME__ = parse
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


import hashlib, math, io, struct
from datetime import datetime, timedelta
from collections import OrderedDict

from ...util import all_subclasses


def create_reader(data_format, process_struct=lambda data: data[0]):
    data_struct = struct.Struct('>' + data_format)
    def reader(file):
        data = data_struct.unpack(file.read(data_struct.size))
        return process_struct(data)
    return reader


# using the names and datatypes from the OpenType specification
# http://www.microsoft.com/typography/otspec/
byte = create_reader('B')
char = create_reader('b')
ushort = create_reader('H')
short = create_reader('h')
ulong = create_reader('L')
long = create_reader('l')
fixed = create_reader('L', lambda data: data[0] / 2**16)
int16 = fword = short
uint16 = ufword = ushort
uint24 = create_reader('3B', lambda data: sum([byte << (2 - i)
                                           for i, byte in enumerate(data)]))
string = create_reader('4s', lambda data: data[0].decode('ascii').strip())
tag = string
glyph_id = uint16
offset = uint16

longdatetime = create_reader('q', lambda data: datetime(1904, 1, 1)
                                               + timedelta(seconds=data[0]))


class Packed(OrderedDict):
    reader = None
    fields = []

    def __init__(self, file):
        super().__init__(self)
        self.value = self.__class__.reader(file)
        for name, mask, processor in self.fields:
            self[name] = processor(self.value & mask)


def array(reader, length):
    def array_reader(file, **kwargs):
        return [reader(file, **kwargs) for i in range(length)]
    return array_reader


def context(reader, *indirect_args):
    def context_reader(file, base, table):
        args = [table[key] for key in indirect_args]
        return reader(file, *args)
    return context_reader


def context_array(reader, count_key, *indirect_args, multiplier=1):
    def context_array_reader(file, table=None, **kwargs):
        length = int(table[count_key] * multiplier)
        args = [table[key] for key in indirect_args]
        try:
            return array(reader, length)(file, *args, table=table, **kwargs)
        except TypeError:
            return array(reader, length)(file, *args)
    return context_array_reader


def indirect(reader, *indirect_args, offset_reader=offset):
    def indirect_reader(file, base, **kwargs):
        indirect_offset = offset_reader(file)
        restore_position = file.tell()
        args = [table[key] for key in indirect_args]
        result = reader(file, base + indirect_offset, *args)
        file.seek(restore_position)
        return result
    return indirect_reader


def indirect_array(reader, count_key, *indirect_args):
    def indirect_array_reader(file, base, table):
        offsets = array(offset, table[count_key])(file)
        args = [table[key] for key in indirect_args]
        return [reader(file, base + entry_offset, *args)
                for entry_offset in offsets]
    return indirect_array_reader


class OpenTypeTableBase(OrderedDict):
    entries = []

    def __init__(self, file, file_offset=None):
        super().__init__()
        self.parse(file, file_offset, self.entries)

    def parse(self, file, base, entries):
        for key, reader in entries:
            try: # special readers
                value = reader(file, base=base, table=self)
            except TypeError: # table reader or simple reader
                value = reader(file)
            if key is not None:
                self[key] = value


class OpenTypeTable(OpenTypeTableBase):
    tag = None

    def __init__(self, file, file_offset=None):
        if file_offset is not None:
            file.seek(file_offset)
        super().__init__(file, file_offset)



class MultiFormatTable(OpenTypeTable):
    formats = {}

    def __init__(self, file, file_offset=None, **kwargs):
        super().__init__(file, file_offset)
        table_format = self[self.entries[0][0]]
        if table_format in self.formats:
            self.parse(file, file_offset, self.formats[table_format])


class Record(OpenTypeTableBase):
    """The base offset for indirect entries in a `Record` is the parent table's
    base, not the `Record`'s base."""
    def __init__(self, file, table=None, base=None):
        super().__init__(file, base)
        self._parent_table = table


class OffsetTable(OpenTypeTable):
    entries = [('sfnt version', fixed),
               ('numTables', ushort),
               ('searchRange', ushort),
               ('entrySelector', ushort),
               ('rangeShift', ushort)]


class TableRecord(OpenTypeTable):
    entries = [('tag', tag),
               ('checkSum', ulong),
               ('offset', ulong),
               ('length', ulong)]

    def check_sum(self, file):
        total = 0
        table_offset = self['offset']
        file.seek(table_offset)
        end_of_data = table_offset + 4 * math.ceil(self['length'] / 4)
        while file.tell() < end_of_data:
            value = ulong(file)
            if not (self['tag'] == 'head' and file.tell() == table_offset + 12):
                total += value
        checksum = total % 2**32
        assert checksum == self['checkSum']


from .required import HmtxTable
from .cff import CompactFontFormat
from . import truetype, gpos, gsub, other


class OpenTypeParser(dict):
    def __init__(self, filename):
        disk_file = open(filename, 'rb')
        file = io.BytesIO(disk_file.read())
        disk_file.close()
        offset_table = OffsetTable(file)
        table_records = OrderedDict()
        for i in range(offset_table['numTables']):
            record = TableRecord(file)
            table_records[record['tag']] = record
        for tag, record in table_records.items():
            record.check_sum(file)

        for tag in ('head', 'hhea', 'cmap', 'maxp', 'name', 'post', 'OS/2'):
            self[tag] = self._parse_table(file, table_records[tag])

        self['hmtx'] = HmtxTable(file, table_records['hmtx']['offset'],
                                 self['hhea']['numberOfHMetrics'],
                                 self['maxp']['numGlyphs'])
        try:
            self['CFF'] = CompactFontFormat(file,
                                            table_records['CFF']['offset'])
        except KeyError:
            self['loca'] = truetype.LocaTable(file,
                                              table_records['loca']['offset'],
                                              self['head']['indexToLocFormat'],
                                              self['maxp']['numGlyphs'])
            self['glyf'] = truetype.GlyfTable(file,
                                              table_records['glyf']['offset'],
                                              self['loca'])
        for tag in ('kern', 'GPOS', 'GSUB'):
            if tag in table_records:
                self[tag] = self._parse_table(file, table_records[tag])

    @staticmethod
    def _parse_table(file, table_record):
        for cls in all_subclasses(OpenTypeTable):
            if cls.tag == table_record['tag']:
                return cls(file, table_record['offset'])

########NEW FILE########
__FILENAME__ = required
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


import struct

from .parse import OpenTypeTable, MultiFormatTable, Record
from .parse import byte, ushort, short, ulong, fixed, fword, ufword, uint24
from .parse import longdatetime, string, array, indirect, context_array, Packed
from .macglyphs import MAC_GLYPHS
from . import ids


class HeadTable(OpenTypeTable):
    """Font header"""
    tag = 'head'
    entries = [('version', fixed),
               ('fontRevision', fixed),
               ('checkSumAdjustment', ulong),
               ('magicNumber', ulong),
               ('flags', ushort),
               ('unitsPerEm', ushort),
               ('created', longdatetime),
               ('modified', longdatetime),
               ('xMin', short),
               ('yMin', short),
               ('xMax', short),
               ('yMax', short),
               ('macStyle', ushort),
               ('lowestRecPPEM', ushort),
               ('fontDirectionHint', short),
               ('indexToLocFormat', short),
               ('glyphDataFormat', short)]

    @property
    def bounding_box(self):
        return (self['xMin'], self['yMin'], self['xMax'], self['yMax'])


class HheaTable(OpenTypeTable):
    """Horizontal header"""
    tag = 'hhea'
    entries = [('version', fixed),
               ('Ascender', fword),
               ('Descender', fword),
               ('LineGap', fword),
               ('advanceWidthMax', ufword),
               ('minLeftSideBearing', fword),
               ('minRightSideBearing', fword),
               ('xMaxExtent', fword),
               ('caretSlopeRise', short),
               ('caretSlopeRun', short),
               ('caretOffset', short),
               (None, short),
               (None, short),
               (None, short),
               (None, short),
               ('metricDataFormat', short),
               ('numberOfHMetrics', ushort)]


class HmtxTable(OpenTypeTable):
    """Horizontal metrics"""
    tag = 'htmx'

    def __init__(self, file, file_offset, number_of_h_metrics, num_glyphs):
        super().__init__(file, file_offset)
        # TODO: rewrite using context_array ?
        file.seek(file_offset)
        advance_widths = []
        left_side_bearings = []
        for i in range(number_of_h_metrics):
            advance_width, lsb = ushort(file), short(file)
            advance_widths.append(advance_width)
            left_side_bearings.append(lsb)
        for i in range(num_glyphs - number_of_h_metrics):
            lsb = short(file)
            advance_widths.append(advance_width)
            left_side_bearings.append(lsb)
        self['advanceWidth'] = advance_widths
        self['leftSideBearing'] = left_side_bearings


class MaxpTable(MultiFormatTable):
    """Maximum profile"""
    tag = 'maxp'
    entries = [('version', fixed),
               ('numGlyphs', ushort),
               ('maxPoints', ushort)]
    format_entries = {1.0: [('maxContours', ushort),
                            ('maxCompositePoints', ushort),
                            ('maxCompositeContours', ushort),
                            ('maxZones', ushort),
                            ('maxTwilightPoints', ushort),
                            ('maxStorage', ushort),
                            ('maxFunctionDefs', ushort),
                            ('maxInstructionDefs', ushort),
                            ('maxStackElements', ushort),
                            ('maxSizeOfInstructions', ushort),
                            ('maxComponentElements', ushort),
                            ('maxComponentDepth', ushort)]}


class OS2Table(OpenTypeTable):
    """OS/2 and Windows specific metrics"""
    tag = 'OS/2'
    entries = [('version', ushort),
               ('xAvgCharWidth', short),
               ('usWeightClass', ushort),
               ('usWidthClass', ushort),
               ('fsType', ushort),
               ('ySubscriptXSize', short),
               ('ySubscriptYSize', short),
               ('ySubscriptXOffset', short),
               ('ySubscriptYOffset', short),
               ('ySuperscriptXSize', short),
               ('ySuperscriptYSize', short),
               ('ySuperscriptXOffset', short),
               ('ySuperscriptYOffset', short),
               ('yStrikeoutSize', short),
               ('yStrikeoutPosition', short),
               ('sFamilyClass', short),
               ('panose', array(byte, 10)),
               ('ulUnicodeRange1', ulong),
               ('ulUnicodeRange2', ulong),
               ('ulUnicodeRange3', ulong),
               ('ulUnicodeRange4', ulong),
               ('achVendID', string),
               ('fsSelection', ushort),
               ('usFirstCharIndex', ushort),
               ('usLastCharIndex', ushort),
               ('sTypoAscender', short),
               ('sTypoDescender', short),
               ('sTypoLineGap', short),
               ('usWinAscent', ushort),
               ('usWinDescent', ushort),
               ('ulCodePageRange1', ulong),
               ('ulCodePageRange2', ulong),
               ('sxHeight', short),
               ('sCapHeight', short),
               ('usDefaultChar', ushort),
               ('usBreakChar', ushort),
               ('usMaxContext', ushort)]


class PostTable(MultiFormatTable):
    """PostScript information"""
    tag = 'post'
    entries = [('version', fixed),
               ('italicAngle', fixed),
               ('underlinePosition', fword),
               ('underlineThickness', fword),
               ('isFixedPitch', ulong),
               ('minMemType42', ulong),
               ('maxMemType42', ulong),
               ('minMemType1', ulong),
               ('maxMemType1', ulong)]
    formats = {2.0: [('numberOfGlyphs', ushort),
                     ('glyphNameIndex', context_array(ushort,
                                                      'numberOfGlyphs'))]}

    def __init__(self, file, file_offset):
        super().__init__(file, file_offset)
        self.names = []
        if self['version'] == 2.0:
            num_new_glyphs = max(self['glyphNameIndex']) - 257
            names = []
            for i in range(num_new_glyphs):
                names.append(self._read_pascal_string(file))
            for index in self['glyphNameIndex']:
                if index < 258:
                    name = MAC_GLYPHS[index]
                else:
                    name = names[index - 258]
                self.names.append(name)
        elif self['version'] != 3.0:
            raise NotImplementedError

    def _read_pascal_string(self, file):
        length = byte(file)
        return struct.unpack('>{}s'.format(length),
                             file.read(length))[0].decode('ascii')


class NameRecord(Record):
    entries = [('platformID', ushort),
               ('encodingID', ushort),
               ('languageID', ushort),
               ('nameID', ushort),
               ('length', ushort),
               ('offset', ushort)]


class LangTagRecord(Record):
    entries = [('length', ushort),
               ('offset', ushort)]


class NameTable(MultiFormatTable):
    """Naming table"""
    tag = 'name'
    entries = [('format', ushort),
               ('count', ushort),
               ('stringOffset', ushort),
               ('nameRecord', context_array(NameRecord, 'count'))]
    formats = {1: [('langTagCount', ushort),
                   ('langTagRecord', context_array(LangTagRecord,
                                                   'langTagCount'))]}

    def __init__(self, file, file_offset):
        super().__init__(file, file_offset)
        if self['format'] == 1:
            raise NotImplementedError
        string_offset = file_offset + self['stringOffset']
        self.strings = {}
        for record in self['nameRecord']:
            file.seek(string_offset + record['offset'])
            data = file.read(record['length'])
            if record['platformID'] in (ids.PLATFORM_UNICODE,
                                        ids.PLATFORM_WINDOWS):
                string = data.decode('utf_16_be')
            elif record['platformID'] == ids.PLATFORM_MACINTOSH:
                # TODO: properly decode according to the specified encoding
                string = data.decode('mac_roman')
            else:
                raise NotImplementedError
            name = self.strings.setdefault(record['nameID'], {})
            platform = name.setdefault(record['platformID'], {})
            platform[record['languageID']] = string


class SubHeader(OpenTypeTable):
    entries = [('firstCode', ushort),
               ('entryCount', ushort),
               ('idDelta', short),
               ('idRangeOffset', ushort)]


class CmapGroup(OpenTypeTable):
    entries = [('startCharCode', ulong),
               ('endCharCode', ulong),
               ('startGlyphID', ulong)]


class VariationSelectorRecord(OpenTypeTable):
    entries = [('varSelector', uint24),
               ('defaultUVSOffset', ulong),
               ('nonDefaultUVSOffset', ulong)]


class CmapSubtable(MultiFormatTable):
    entries = [('format', ushort)]
    formats = {0: # Byte encoding table
                  [('length', ushort),
                   ('language', ushort),
                   ('glyphIdArray', array(byte, 256))],
               2: # High-byte mapping through table
                  [('length', ushort),
                   ('language', ushort),
                   ('subHeaderKeys', array(ushort, 256))],
               4: # Segment mapping to delta values
                  [('length', ushort),
                   ('language', ushort),
                   ('segCountX2', ushort),
                   ('searchRange', ushort),
                   ('entrySelector', ushort),
                   ('rangeShift', ushort),
                   ('endCount', context_array(ushort, 'segCountX2',
                                              multiplier=0.5)),
                   (None, ushort),
                   ('startCount', context_array(ushort, 'segCountX2',
                                                multiplier=0.5)),
                   ('idDelta', context_array(short, 'segCountX2',
                                             multiplier=0.5)),
                   ('idRangeOffset', context_array(ushort, 'segCountX2',
                                                   multiplier=0.5))],
               6: # Trimmed table mapping
                  [('length', ushort),
                   ('language', ushort),
                   ('firstCode', ushort),
                   ('entryCount', ushort),
                   ('glyphIdArray', context_array(ushort, 'entryCount'))],
               8: # Mixed 16-bit and 32-bit coverage
                  [(None, ushort),
                   ('length', ulong),
                   ('language', ulong),
                   ('is32', array(byte, 8192)),
                   ('nGroups', ulong),
                   ('group', context_array(CmapGroup, 'nGroups'))],
              10: # Trimmed array
                  [(None, ushort),
                   ('length', ulong),
                   ('language', ulong),
                   ('startCharCode', ulong),
                   ('numchars', ulong),
                   ('glyphs', context_array(ushort, 'numChars'))],
              12: # Segmented coverage
                  [(None, ushort),
                   ('length', ulong),
                   ('language', ulong),
                   ('nGroups', ulong),
                   ('groups', context_array(CmapGroup, 'nGroups'))],
              13: # Many-to-one range mappings
                  [(None, ushort),
                   ('length', ulong),
                   ('language', ulong),
                   ('nGroups', ulong),
                   ('groups', context_array(CmapGroup, 'nGroups'))],
              14: # Unicode Variation Sequences
                  [('length', ulong),
                   ('numVarSelectorRecords', ulong),
                   ('varSelectorRecord', context_array(VariationSelectorRecord,
                                                       'numVarSelectorRecords'))]}

    # TODO
##    formats[99] = [('bla', ushort)]
##    def _format_99_init(self):
##        pass

    def __init__(self, file, file_offset=None):
        # TODO: detect already-parsed table (?)
        super().__init__(file, file_offset)
        # TODO: create format-dependent lookup function instead of storing
        #       everything in a dict (not efficient for format 13 subtables fe)
        if self['format'] == 0:
            indices = array(byte, 256)(file)
            out = {i: index for i, index in enumerate(self['glyphIdArray'])}
        elif self['format'] == 2:
            raise NotImplementedError
        elif self['format'] == 4:
            seg_count = self['segCountX2'] >> 1
            self['glyphIdArray'] = array(ushort, self['length'])(file)
            segments = zip(self['startCount'], self['endCount'],
                           self['idDelta'], self['idRangeOffset'])
            out = {}
            for i, (start, end, delta, range_offset) in enumerate(segments):
                if i == seg_count - 1:
                    assert end == 0xFFFF
                    break
                if range_offset > 0:
                    for j, code in enumerate(range(start, end + 1)):
                        index = (range_offset >> 1) - seg_count + i + j
                        out[code] = self['glyphIdArray'][index]
                else:
                    for code in range(start, end + 1):
                        out[code] = (code + delta) % 2**16
        elif self['format'] == 6:
            out = {code: index for code, index in
                   zip(range(self['firstCode'],
                             self['firstCode'] + self['entryCount']),
                       self['glyphIdArray'])}
        elif self['format'] == 12:
            out = {}
            for group in self['groups']:
                codes = range(group['startCharCode'], group['endCharCode'] + 1)
                segment = {code: group['startGlyphID'] + index
                           for index, code in enumerate(codes)}
                out.update(segment)
        elif self['format'] == 13:
            out = {}
            for group in self['groups']:
                codes = range(group['startCharCode'], group['endCharCode'] + 1)
                segment = {code: group['startGlyphID'] for code in codes}
                out.update(segment)
        else:
            raise NotImplementedError
        self.mapping = out


class CmapRecord(Record):
    entries = [('platformID', ushort),
               ('encodingID', ushort),
               ('subtable', indirect(CmapSubtable, offset_reader=ulong))]


class CmapTable(OpenTypeTable):
    tag = 'cmap'
    entries = [('version', ushort),
               ('numTables', ushort),
               ('encodingRecord', context_array(CmapRecord, 'numTables'))]

    def __init__(self, file, file_offset):
        super().__init__(file, file_offset)
        for record in self['encodingRecord']:
            key = (record['platformID'], record['encodingID'])
            self[key] = record['subtable']

########NEW FILE########
__FILENAME__ = truetype
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


import struct

from .parse import OpenTypeTable, MultiFormatTable, short


class GlyfTable(OpenTypeTable):
    """Glyph outline table"""
    tag = 'glyf'

    def __init__(self, file, file_offset, loca_table):
        super().__init__(file, file_offset)
        self._file_offset = file_offset
        for index, glyph_offset in enumerate(loca_table.offsets()):
            if glyph_offset is not None:
                self[index] = GlyphHeader(file, file_offset + glyph_offset)
                # the glyph header is followed by the glyph description


class GlyphHeader(OpenTypeTable):
    entries = [('numberOfContours', short),
               ('xMin', short),
               ('yMin', short),
               ('xMax', short),
               ('yMax', short)]

    @property
    def bounding_box(self):
        return (self['xMin'], self['yMin'], self['xMax'], self['yMax'])


class LocaTable(OpenTypeTable):
    """Glyph location table"""
    tag = 'loca'

    def __init__(self, file, file_offset, version, num_glyphs):
        super().__init__(file, file_offset)
        self._num_glyphs = num_glyphs
        data_format = 'L' if version == 1 else 'H'
        data_struct = struct.Struct('>{}{}'.format(num_glyphs + 1, data_format))
        self._offsets = data_struct.unpack(file.read(data_struct.size))
        if version == 0:
            self._offsets = [offset * 2 for offset in self._offsets]

    def offsets(self):
        for index in range(self._num_glyphs):
            offset = self._offsets[index]
            if offset != self._offsets[index + 1]:
                yield offset
            else:
                yield None

########NEW FILE########
__FILENAME__ = style
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.



# TODO: split up into weight.py, slant.py and width.py?
# provide aliases (normal, regular, plain, roman)?

# weight
HAIRLINE = 'Hairline'
THIN = 'Thin'
ULTRA_LIGHT = 'Ultra-Light'
EXTRA_LIGHT = 'Extra-Light'
LIGHT = 'Light'
BOOK = 'Book'
REGULAR = 'Regular'
MEDIUM = 'Medium'
DEMI_BOLD = 'Demi-Bold'
BOLD = 'Bold'
EXTRA_BOLD = 'Extra-Bold'
HEAVY = 'Heavy'
BLACK = 'Black'
EXTRA_BLACK = 'Extra-Black'
ULTRA_BLACK = 'Ultra-Black'

# slant
UPRIGHT = 'Upright'
OBLIQUE = 'Oblique'
ITALIC = 'Italic'

# width
NORMAL = 'Normal'
CONDENSED = 'Condensed'
EXTENDED = 'Extended'

# position
SUPERSCRIPT = 'Superscript'
SUBSCRIPT = 'Subscript'

# variant
SMALL_CAPITAL = 'Small Capital'
OLD_STYLE = 'Old Style Figure'

WEIGHTS = (HAIRLINE, THIN, ULTRA_LIGHT, EXTRA_LIGHT, LIGHT, BOOK, REGULAR,
           MEDIUM, DEMI_BOLD, BOLD, EXTRA_BOLD, HEAVY, BLACK, EXTRA_BLACK,
           ULTRA_BLACK)
SLANTS = (UPRIGHT, OBLIQUE, ITALIC)
WIDTHS = (NORMAL, CONDENSED, EXTENDED)
POSITIONS = (NORMAL, SUPERSCRIPT, SUBSCRIPT)
VARIANTS = (SMALL_CAPITAL, OLD_STYLE)

########NEW FILE########
__FILENAME__ = type1
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


import os
import re
import struct

from binascii import unhexlify
from io import BytesIO
from warnings import warn

from . import Font, GlyphMetrics, LeafGetter
from .style import MEDIUM,  UPRIGHT, NORMAL
from .style import SMALL_CAPITAL, OLD_STYLE
from .mapping import UNICODE_TO_GLYPH_NAME, ENCODINGS
from ..util import cached
from ..warnings import RinohWarning


def string(string):
    return string.strip()


def number(string):
    try:
        number = int(string)
    except ValueError:
        number = float(string)
    return number


def boolean(string):
    return string.strip() == 'true'


class AdobeFontMetricsParser(dict):
    SECTIONS = {'FontMetrics': string,
                'CharMetrics': int}

    KEYWORDS = {'FontName': string,
                'FullName': string,
                'FamilyName': string,
                'Weight': string,
                'FontBBox': (number, number, number, number),
                'Version': string,
                'Notice': string,
                'EncodingScheme': string,
                'MappingScheme': int,
                'EscChar': int,
                'CharacterSet': string,
                'Characters': int,
                'IsBaseFont': boolean,
                'VVector': (number, number),
                'IsFixedV': boolean,
                'CapHeight': number,
                'XHeight': number,
                'Ascender': number,
                'Descender': number,
                'StdHW': number,
                'StdVW': number,

                'UnderlinePosition': number,
                'UnderlineThickness': number,
                'ItalicAngle': number,
                'CharWidth': (number, number),
                'IsFixedPitch': boolean}

    HEX_NUMBER = re.compile(r'<([\da-f]+)>', re.I)

    def __init__(self, file):
        self._glyphs = {}
        self._ligatures = {}
        self._kerning_pairs = {}
        sections, section = [self], self
        section_names = [None]
        for line in file.readlines():
            try:
                key, values = line.split(None, 1)
            except ValueError:
                key, values = line.strip(), []
            if not key:
                continue
            if key == 'Comment':
                pass
            elif key.startswith('Start'):
                section_name = key[5:]
                section_names.append(section_name)
                section[section_name] = {}
                section = section[section_name]
                sections.append(section)
            elif key.startswith('End'):
                assert key[3:] == section_names.pop()
                sections.pop()
                section = sections[-1]
            elif section_names[-1] == 'CharMetrics':
                glyph_metrics = self._parse_character_metrics(line)
                self._glyphs[glyph_metrics.name] = glyph_metrics
            elif section_names[-1] == 'KernPairs':
                tokens = line.split()
                if tokens[0] == 'KPX':
                    pair, kerning = (tokens[1], tokens[2]), tokens[-1]
                    self._kerning_pairs[pair] = number(kerning)
                else:
                    raise NotImplementedError
            elif section_names[-1] == 'Composites':
                warn('Composites in Type1 fonts are currently not supported.'
                     '({})'.format(self.filename) if self.filename else '')
            elif key == chr(26):    # EOF marker
                assert not file.read()
            else:
                funcs = self.KEYWORDS[key]
                try:
                    values = [func(val)
                              for func, val in zip(funcs, values.split())]
                except TypeError:
                    values = funcs(values)
                section[key] = values

    def _parse_character_metrics(self, line):
        ligatures = {}
        for item in line.strip().split(';'):
            if not item:
                continue
            tokens = item.split()
            key = tokens[0]
            if key == 'C':
                code = int(tokens[1])
            elif key == 'CH':
                code = int(self.HEX_NUMBER.match(tokens[1]).group(1), base=16)
            elif key in ('WX', 'W0X'):
                width = number(tokens[1])
            elif key in ('WY', 'W0Y'):
                height = number(tokens[1])
            elif key in ('W', 'W0'):
                width, height = number(tokens[1]), number(tokens[2])
            elif key == 'N':
                name = tokens[1]
            elif key == 'B':
                bbox = tuple(number(num) for num in tokens[1:])
            elif key == 'L':
                ligatures[tokens[1]] = tokens[2]
            else:
                raise NotImplementedError
        if ligatures:
            self._ligatures[name] = ligatures
        return GlyphMetrics(name, width, bbox, code)


class AdobeFontMetrics(Font, AdobeFontMetricsParser):
    units_per_em = 1000
    # encoding is set in __init__

    name = LeafGetter('FontMetrics', 'FontName')
    bounding_box = LeafGetter('FontMetrics', 'FontBBox')
    italic_angle = LeafGetter('FontMetrics', 'ItalicAngle')
    ascender = LeafGetter('FontMetrics', 'Ascender', default=750)
    descender = LeafGetter('FontMetrics', 'Descender', default=-250)
    line_gap = 200
    cap_height = LeafGetter('FontMetrics', 'CapHeight', default=700)
    x_height = LeafGetter('FontMetrics', 'XHeight', default=500)
    stem_v = LeafGetter('FontMetrics', 'StdVW', default=50)

    def __init__(self, file_or_filename, weight=MEDIUM, slant=UPRIGHT,
                 width=NORMAL):
        try:
            filename = file_or_filename
            file = open(file_or_filename, 'rt', encoding='ascii')
            close_file = True
        except TypeError:
            filename = None
            file = file_or_filename
            close_file = False
        self._suffixes = {}
        AdobeFontMetricsParser.__init__(self, file)
        if close_file:
            file.close()
        encoding_name = self['FontMetrics']['EncodingScheme']
        if encoding_name == 'FontSpecific':
            self.encoding = {glyph.name: glyph.code
                             for glyph in self._glyphs.values()
                             if glyph.code > -1}
        else:
            self.encoding = ENCODINGS[encoding_name]
        super().__init__(filename,  weight, slant, width)

    _SUFFIXES = {SMALL_CAPITAL: ('.smcp', '.sc', 'small'),
                 OLD_STYLE: ('.oldstyle', )}

    def _find_suffix(self, char, variant, upper=False):
        try:
            return self._suffixes[variant]
        except KeyError:
            for suffix in self._SUFFIXES[variant]:
                for name in self._char_to_name(char):
                    if name + suffix in self._glyphs:
                        self._suffixes[variant] = suffix
                        return suffix
            else:
                return ''
##            if not upper:
##                return self._find_suffix(self.char_to_name(char.upper()),
##                                         possible_suffixes, True)

    def _char_to_name(self, char, variant=None):
        try:
            # TODO: first search character using the font's encoding
            name_or_names = UNICODE_TO_GLYPH_NAME[ord(char)]
            if variant and char != ' ':
                suffix = self._find_suffix(char, variant)
            else:
                suffix = ''
            try:
                yield name_or_names + suffix
            except TypeError:
                for name in name_or_names:
                    yield name + suffix
        except KeyError:
            # TODO: map to uniXXXX or uXXXX names
            warn('Don\'t know how to map unicode index 0x{:04x} ({}) '
                 'to a PostScript glyph name.'.format(ord(char), char),
                 RinohWarning)
            yield 'question'

    @cached
    def get_glyph(self, char, variant=None):
        for name in self._char_to_name(char, variant):
            if name in self._glyphs:
                return self._glyphs[name]
        if variant:
            warn('No {} variant found for unicode index 0x{:04x} ({}), falling '
                 'back to the standard glyph.'.format(variant, ord(char), char),
                 RinohWarning)
            return self.get_glyph(char)
        else:
            warn('{} does not contain glyph for unicode index 0x{:04x} ({}).'
                 .format(self.name, ord(char), char), RinohWarning)
            return self._glyphs['question']

    def get_ligature(self, glyph, successor_glyph):
        try:
            ligature_name = self._ligatures[glyph.name][successor_glyph.name]
            return self._glyphs[ligature_name]
        except KeyError:
            return None

    def get_kerning(self, a, b):
        return self._kerning_pairs.get((a.name, b.name), 0.0)


class PrinterFont(object):
    def __init__(self, header, body, trailer):
        self.header = header
        self.body = body
        self.trailer = trailer


class PrinterFontASCII(PrinterFont):
    START_OF_BODY = re.compile(br'\s*currentfile\s+eexec\s*')

    def __init__(self, filename):
        with open(filename, 'rb') as file:
            header = self._parse_header(file)
            body, trailer = self._parse_body_and_trailer(file)
        super().__init__(header, body, trailer)

    @classmethod
    def _parse_header(cls, file):
        header = BytesIO()
        for line in file:
            # Adobe Reader can't handle carriage returns, so we remove them
            header.write(line.translate(None, b'\r'))
            if cls.START_OF_BODY.match(line.translate(None, b'\r\n')):
                break
        return header.getvalue()

    @staticmethod
    def _parse_body_and_trailer(file):
        body = BytesIO()
        trailer_lines = []
        number_of_zeros = 0
        lines = file.readlines()
        for line in reversed(lines):
            number_of_zeros += line.count(b'0')
            trailer_lines.append(lines.pop())
            if number_of_zeros == 512:
                break
            elif number_of_zeros > 512:
                raise Type1ParseError
        for line in lines:
            cleaned = line.translate(None, b' \t\r\n')
            body.write(unhexlify(cleaned))
        trailer = BytesIO()
        for line in reversed(trailer_lines):
            trailer.write(line.translate(None, b'\r'))
        return body.getvalue(), trailer.getvalue()


class PrinterFontBinary(PrinterFont):
    SECTION_HEADER_FMT = '<BBI'
    SEGMENT_TYPES = {'header': 1,
                     'body': 2,
                     'trailer': 1}

    def __init__(self, filename):
        with open(filename, 'rb') as file:
            segments = []
            for segment_name in ('header', 'body', 'trailer'):
                segment_type, segment = self._read_pfb_segment(file)
                if self.SEGMENT_TYPES[segment_name] != segment_type:
                    raise Type1ParseError('Not a PFB file')
                segments.append(segment)
            check, eof_type = struct.unpack('<BB', file.read(2))
            if check != 128 or eof_type != 3:
                raise Type1ParseError('Not a PFB file')
        super().__init__(*segments)

    @classmethod
    def _read_pfb_segment(cls, file):
        header_data = file.read(struct.calcsize(cls.SECTION_HEADER_FMT))
        check, segment_type, length = struct.unpack(cls.SECTION_HEADER_FMT,
                                                    header_data)
        if check != 128:
            raise Type1ParseError('Not a PFB file')
        return int(segment_type), file.read(length)


class Type1Font(AdobeFontMetrics):
    def __init__(self, filename, weight=MEDIUM, slant=UPRIGHT, width=NORMAL,
                 core=False):
        AdobeFontMetrics.__init__(self, filename + '.afm',  weight, slant, width)
        self.core = core
        if not core:
            if os.path.exists(filename + '.pfb'):
                self.font_program = PrinterFontBinary(filename + '.pfb')
            else:
                self.font_program = PrinterFontASCII(filename + '.pfa')


class Type1ParseError(Exception):
    pass

########NEW FILE########
__FILENAME__ = adobe14
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.

"""Adobe PDF core font set"""

import os

from . import FONTS_PATH
from ..font import TypeFace, TypeFamily
from ..font.type1 import Type1Font
from ..font.style import REGULAR, MEDIUM, BOLD, OBLIQUE, ITALIC, CONDENSED



def path(name):
    return os.path.join(FONTS_PATH, 'adobe14', name)


courier = TypeFace('Courier',
                   Type1Font(path('Courier'), core=True),
                   Type1Font(path('Courier-Oblique'), slant=OBLIQUE, core=True),
                   Type1Font(path('Courier-Bold'), weight=BOLD, core=True),
                   Type1Font(path('Courier-BoldOblique'), weight=BOLD,
                             slant=OBLIQUE, core=True))

helvetica = TypeFace('Helvetica',
                     Type1Font(path('Helvetica'), core=True),
                     Type1Font(path('Helvetica-Oblique'), slant=OBLIQUE,
                               core=True),
                     Type1Font(path('Helvetica-Bold'), weight=BOLD, core=True),
                     Type1Font(path('Helvetica-BoldOblique'), weight=BOLD,
                               slant=OBLIQUE, core=True))

symbol = TypeFace('Symbol', Type1Font(path('Symbol'), core=True))

times = TypeFace('Times',
                 Type1Font(path('Times-Roman'), weight=REGULAR, core=True),
                 Type1Font(path('Times-Italic'), slant=ITALIC, core=True),
                 Type1Font(path('Times-Bold'), weight=BOLD, core=True),
                 Type1Font(path('Times-BoldItalic'), weight=BOLD, slant=ITALIC,
                           core=True))

zapfdingbats = TypeFace('ITC ZapfDingbats', Type1Font(path('ZapfDingbats'),
                        core=True))

# 'Adobe PDF Core Font Set'
pdf_family = TypeFamily(serif=times, sans=helvetica, mono=courier,
                        symbol=symbol, dingbats=zapfdingbats)

########NEW FILE########
__FILENAME__ = adobe35
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.

"""Adobe PostScript core font set"""

import os

from . import FONTS_PATH
from ..font import TypeFace, TypeFamily
from ..font.type1 import Type1Font
from ..font.style import LIGHT, BOOK, REGULAR, MEDIUM, DEMI_BOLD, BOLD
from ..font.style import OBLIQUE, ITALIC, CONDENSED
from ..math import MathFonts


__all__ = ['avantgarde', 'bookman', 'courier', 'helvetica', 'newcenturyschlbk',
           'palatino', 'symbol', 'times', 'zapfchancery', 'zapfdingbats']


def path(name):
    return os.path.join(FONTS_PATH, 'adobe35', name)


avantgarde = TypeFace('ITC Avant Garde Gothic',
                      Type1Font(path('ITCAvantGarde-Book'), weight=BOOK,
                                core=True),
                      Type1Font(path('ITCAvantGarde-BookOblique'), weight=BOOK,
                                slant=OBLIQUE, core=True),
                      Type1Font(path('ITCAvantGarde-Demi'), weight=DEMI_BOLD,
                                core=True),
                      Type1Font(path('ITCAvantGarde-DemiOblique'),
                                weight=DEMI_BOLD, slant=OBLIQUE, core=True))

bookman = TypeFace('ITC Bookman',
                   Type1Font(path('ITCBookman-Light'), weight=LIGHT, core=True),
                   Type1Font(path('ITCBookman-LightItalic'), weight=LIGHT,
                             slant=ITALIC, core=True),
                   Type1Font(path('ITCBookman-Demi'), weight=DEMI_BOLD,
                             core=True),
                   Type1Font(path('ITCBookman-DemiItalic'), weight=DEMI_BOLD,
                             slant=ITALIC, core=True))

courier = TypeFace('Courier',
                   Type1Font(path('Courier'), core=True),
                   Type1Font(path('Courier-Oblique'), slant=OBLIQUE, core=True),
                   Type1Font(path('Courier-Bold'), weight=BOLD, core=True),
                   Type1Font(path('Courier-BoldOblique'), weight=BOLD,
                             slant=OBLIQUE, core=True))

helvetica = TypeFace('Helvetica',
                     Type1Font(path('Helvetica'), core=True),
                     Type1Font(path('Helvetica-Oblique'), slant=OBLIQUE,
                               core=True),
                     Type1Font(path('Helvetica-Bold'), weight=BOLD, core=True),
                     Type1Font(path('Helvetica-BoldOblique'), weight=BOLD,
                               slant=OBLIQUE, core=True),
                     Type1Font(path('Helvetica-Narrow'), width=CONDENSED,
                               core=True),
                     Type1Font(path('Helvetica-NarrowOblique'), width=CONDENSED,
                               slant=OBLIQUE, core=True),
                     Type1Font(path('Helvetica-NarrowBold'), width=CONDENSED,
                               weight=BOLD, core=True),
                     Type1Font(path('Helvetica-NarrowBoldOblique'),
                               width=CONDENSED, weight=BOLD, slant=OBLIQUE,
                               core=True))

newcenturyschlbk = TypeFace('New Century Schoolbook',
                            Type1Font(path('NewCenturySchlbk-Roman'),
                                      core=True),
                            Type1Font(path('NewCenturySchlbk-Italic'),
                                      slant=ITALIC, core=True),
                            Type1Font(path('NewCenturySchlbk-Bold'),
                                      weight=BOLD, core=True),
                            Type1Font(path('NewCenturySchlbk-BoldItalic'),
                                      weight=BOLD, slant=ITALIC, core=True))

palatino = TypeFace('Palatino',
                    Type1Font(path('Palatino-Roman'), core=True),
                    Type1Font(path('Palatino-Italic'), slant=ITALIC, core=True),
                    Type1Font(path('Palatino-Bold'), weight=BOLD, core=True),
                    Type1Font(path('Palatino-BoldItalic'), weight=BOLD,
                              slant=ITALIC, core=True))

symbol = TypeFace('Symbol', Type1Font(path('Symbol'), core=True))

times = TypeFace('Times',
                 Type1Font(path('Times-Roman'), weight=REGULAR, core=True),
                 Type1Font(path('Times-Italic'), slant=ITALIC, core=True),
                 Type1Font(path('Times-Bold'), weight=BOLD, core=True),
                 Type1Font(path('Times-BoldItalic'), weight=BOLD, slant=ITALIC,
                           core=True))

zapfchancery = TypeFace('ITC Zapf Chancery',
                        Type1Font(path('ITCZapfChancery-MediumItalic'),
                                  slant=ITALIC, core=True))

zapfdingbats = TypeFace('ITC ZapfDingbats',
                        Type1Font(path('ZapfDingbats'), core=True))


postscript_mathfonts = MathFonts(newcenturyschlbk.get(),
                                 newcenturyschlbk.get(slant=ITALIC),
                                 newcenturyschlbk.get(weight=BOLD),
                                 helvetica.get(),
                                 courier.get(),
                                 zapfchancery.get(slant=ITALIC),
                                 symbol.get(),
                                 symbol.get())

########NEW FILE########
__FILENAME__ = nodes

import re
import unicodedata

import rinoh as rt

from . import BodyElement, BodySubElement, InlineElement, GroupingElement
from ...util import intersperse


class Text(InlineElement):
    def styled_text(self):
        return re.sub('[\t\r\n ]+', ' ', self.text)


class Document(BodyElement):
    pass


class DocInfo(BodyElement):
    def build_flowable(self):
        return rt.FieldList([child.flowable() for child in self.getchildren()])


# bibliographic elements

class DocInfoField(BodyElement):
    def build_flowable(self, content=None):
        field_name = rt.Paragraph(self.__class__.__name__, style='field_name')
        content = content or rt.Paragraph(self.process_content())
        return rt.LabeledFlowable(field_name, content)


class Author(DocInfoField):
    pass


class Authors(DocInfoField):
    def build_flowable(self):
        authors = []
        for author in self.author:
            authors.append(rt.Paragraph(author.process_content()))
        return super().build_flowable(rt.StaticGroupedFlowables(authors))


class Copyright(DocInfoField):
    pass


class Address(DocInfoField):
    pass


class Organization(DocInfoField):
    pass


class Contact(DocInfoField):
    pass


class Date(DocInfoField):
    pass


class Version(DocInfoField):
    pass


class Revision(DocInfoField):
    pass


class Status(DocInfoField):
    pass


# FIXME: the meta elements are removed from the docutils doctree
class Meta(BodyElement):
    MAP = {'keywords': 'keywords',
           'description': 'subject'}

    def build_flowable(self):
        metadata = {self.MAP[self.get('name')]: self.get('content')}
        return rt.SetMetadataFlowable(**metadata)


# body elements

class System_Message(BodyElement):
    def build_flowable(self):
        return rt.WarnFlowable(self.text)


class Comment(BodyElement):
    def build_flowable(self):
        return rt.DummyFlowable()


class Topic(GroupingElement):
    style = 'topic'

    def build_flowable(self):
        classes = self.get('classes')
        if 'contents' in classes:
            flowables = [rt.TableOfContents(local='local' in classes)]
            try:
                flowables.insert(0, self.title.flowable())
            except AttributeError:
                pass
            return rt.StaticGroupedFlowables(flowables,
                                             style='table of contents')
        else:
            return super().build_flowable()


class Rubric(BodyElement):
    def build_flowable(self):
        return rt.Paragraph(self.process_content(), style='rubric')


class Sidebar(GroupingElement):
    def flowable(self):
        grouped_flowables = super().flowable()
        return rt.Framed(grouped_flowables, style='sidebar')


class Section(BodyElement):
    def build_flowable(self):
        flowables = []
        for element in self.getchildren():
            flowables.append(element.flowable())
        return rt.Section(flowables, id=self.get('ids', None)[0])


class Paragraph(BodyElement):
    def build_flowable(self):
        return rt.Paragraph(super().process_content())


class Compound(GroupingElement):
    pass


class Title(BodyElement):
    def build_flowable(self):
        if isinstance(self.parent, Section):
            return rt.Heading(self.process_content())
        else:
            return rt.Paragraph(self.process_content(), 'title')


class Subtitle(BodyElement):
    def build_flowable(self):
        return rt.Paragraph(self.text, 'subtitle')


class Admonition(GroupingElement):
    def flowable(self):
        return rt.Framed(super().flowable(), style='admonition')


class AdmonitionBase(GroupingElement):
    title = None

    def flowable(self):
        title_par = rt.Paragraph(self.title, style='title')
        content = rt.StaticGroupedFlowables([title_par, super().flowable()])
        framed = rt.Framed(content, style='admonition')
        framed.admonition_type = self.__class__.__name__.lower()
        return framed


class Attention(AdmonitionBase):
    title = 'Attention!'


class Caution(AdmonitionBase):
    title = 'Caution!'


class Danger(AdmonitionBase):
    title = '!DANGER!'


class Error(AdmonitionBase):
    title = 'Error'


class Hint(AdmonitionBase):
    title = 'Hint'


class Important(AdmonitionBase):
    title = 'Important'


class Note(AdmonitionBase):
    title = 'Note'


class Tip(AdmonitionBase):
    title = 'Tip'


class Warning(AdmonitionBase):
    title = 'Warning'


class Generated(InlineElement):
    def styled_text(self):
        return None


class Emphasis(InlineElement):
    def build_styled_text(self):
        return rt.Emphasized(self.text)


class Strong(InlineElement):
    def build_styled_text(self):
        return rt.Bold(self.text)


class Title_Reference(InlineElement):
    def build_styled_text(self):
        return rt.Italic(self.text)


class Literal(InlineElement):
    def build_styled_text(self):
        text = self.text.replace('\n', ' ')
        return rt.SingleStyledText(text, style='monospaced')


class Superscript(InlineElement):
    def build_styled_text(self):
        return rt.Superscript(self.process_content())


class Subscript(InlineElement):
    def build_styled_text(self):
        return rt.Subscript(self.process_content())


class Problematic(BodyElement, InlineElement):
    def build_styled_text(self):
        return rt.SingleStyledText(self.text, style='error')

    def build_flowable(self):
        return rt.DummyFlowable()


class Literal_Block(BodyElement):
    def build_flowable(self):
        text = self.text.replace(' ', unicodedata.lookup('NO-BREAK SPACE'))
        return rt.Paragraph(text, style='literal')


class Block_Quote(GroupingElement):
    style = 'block quote'


class Attribution(Paragraph):
    def build_flowable(self):
        return rt.Paragraph('\N{EM DASH}' + self.process_content(),
                            style='attribution')


class Line_Block(GroupingElement):
    style = 'line block'


class Line(BodyElement):
    def build_flowable(self):
        return rt.Paragraph(self.process_content() or '\n',
                            style='line block line')

class Doctest_Block(BodyElement):
    def build_flowable(self):
        text = self.text.replace(' ', unicodedata.lookup('NO-BREAK SPACE'))
        return rt.Paragraph(text, style='literal')


class Reference(BodyElement, InlineElement):
    def build_styled_text(self):
        return self.process_content()

    def build_flowable(self):
        children = self.getchildren()
        assert len(children) == 1
        return self.image.flowable()


class Footnote(BodyElement):
    def build_flowable(self):
        assert len(self.node['ids']) == 1
        note_id = self.node['ids'][0]
        content = [node.flowable() for node in self.getchildren()[1:]]
        note = rt.Note(rt.StaticGroupedFlowables(content), id=note_id)
        return rt.RegisterNote(note)


class Label(BodyElement):
    def build_flowable(self):
        return rt.DummyFlowable()


class Footnote_Reference(InlineElement):
    def build_styled_text(self):
        return rt.NoteMarker(self.node['refid'])




class Substitution_Definition(BodyElement):
    def build_flowable(self):
        return rt.DummyFlowable()


class Target(BodyElement, InlineElement):
    def build_styled_text(self):
        return self.process_content()

    def build_flowable(self):
        return rt.DummyFlowable()


class Enumerated_List(BodyElement):
    def build_flowable(self):
        # TODO: handle different numbering styles
        return rt.List([item.process() for item in self.list_item],
                       style='enumerated')


class Bullet_List(BodyElement):
    def build_flowable(self):
        return rt.List([item.process() for item in self.list_item],
                       style='bulleted')


class List_Item(BodySubElement):
    def process(self):
        return [item.flowable() for item in self.getchildren()]


class Definition_List(BodyElement):
    def build_flowable(self):
        return rt.DefinitionList([item.process()
                                  for item in self.definition_list_item])


class Definition_List_Item(BodySubElement):
    def process(self):
        term = self.term.styled_text()
        try:
            term += ' : ' + self.classifier.styled_text()
        except AttributeError:
            pass
        return (term, self.definition.flowable())


class Term(InlineElement):
    def build_styled_text(self):
        return self.process_content()


class Classifier(InlineElement):
    def build_styled_text(self):
        return self.process_content('classifier')


class Definition(GroupingElement):
    pass


class Field_List(BodyElement):
    def build_flowable(self):
        return rt.FieldList([field.flowable() for field in self.field])


class Field(BodyElement):
    def build_flowable(self):
        return rt.LabeledFlowable(self.field_name.flowable(),
                                  self.field_body.flowable())


class Field_Name(BodyElement):
    def build_flowable(self):
        return rt.Paragraph(self.process_content(), style='field_name')


class Field_Body(GroupingElement):
    pass


class Option_List(BodyElement):
    def build_flowable(self):
        return rt.FieldList([item.flowable() for item in self.option_list_item])


class Option_List_Item(BodyElement):
    def build_flowable(self):
        return rt.LabeledFlowable(self.option_group.flowable(),
                                  self.description.flowable(),
                                  style='option')


class Option_Group(BodyElement):
    def build_flowable(self):
        options = (option.styled_text() for option in self.option)
        return rt.Paragraph(intersperse(options, ', '), style='option_group')


class Option(InlineElement):
    def build_styled_text(self):
        text = self.option_string.styled_text()
        try:
            delimiter = rt.MixedStyledText(self.option_argument['delimiter'],
                                           style='option_string')
            text += delimiter + self.option_argument.styled_text()
        except AttributeError:
            pass
        return rt.MixedStyledText(text)


class Option_String(InlineElement):
    def build_styled_text(self):
        return rt.MixedStyledText(self.process_content(), style='option_string')


class Option_Argument(InlineElement):
    def build_styled_text(self):
        return rt.MixedStyledText(self.process_content(), style='option_arg')


class Description(GroupingElement):
    pass


class Image(BodyElement):
    def build_flowable(self):
        return rt.Image(self.get('uri').rsplit('.png', 1)[0])


class Transition(BodyElement):
    def build_flowable(self):
        return rt.HorizontalRule()

########NEW FILE########
__FILENAME__ = elementtree
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


import sys

from urllib.parse import urlparse, urljoin
from urllib.request import urlopen
from warnings import warn
from xml.parsers import expat

# this module depends on internals of the Python ElementTree implementation, so
# we can't use the C accelerated versions (which are the default in Python 3.3+)
_cached_etree_modules = {}
for name in list(sys.modules.keys()):
    if name.startswith('xml.etree') or name == '_elementtree':
        _cached_etree_modules[name] = sys.modules.pop(name)
sys.modules['_elementtree'] = None

from xml.etree import ElementTree, ElementPath

for name in list(sys.modules.keys()):
    if name.startswith('xml.etree'):
        del sys.modules[name]
sys.modules.update(_cached_etree_modules)

from ...util import all_subclasses
from . import CATALOG_PATH, CATALOG_URL, CATALOG_NS


class TreeBuilder(ElementTree.TreeBuilder):
    def __init__(self, namespace, line_callback, element_factory=None):
        super().__init__(element_factory)
        self._namespace = namespace
        self._line_callback = line_callback

    def start(self, tag, attrs):
        elem = super().start(tag, attrs)
        elem.sourceline = self._line_callback()
        return elem

    def end(self, tag):
        last = super().end(tag)
        try:
            last._parent = self._elem[-1]
            last._root = self._elem[0]
        except IndexError:
            last._parent = None
            last._root = self
        last._namespace = self._namespace
        return last


class Parser(ElementTree.XMLParser):
    def __init__(self, element_class, namespace=None, schema=None):
        self.element_class = element_class
        if schema:
            warn('The ElementTree based XML parser does not support '
                 'validation. Please use the lxml frontend if you require '
                 'validation.')
        self.namespace = '{{{}}}'.format(namespace) if namespace else ''
        self.element_classes = {self.namespace + cls.__name__.lower(): cls
                                for cls in all_subclasses(self.element_class)}
        tree_builder = TreeBuilder(self.namespace, self.get_current_line_number,
                                   self.lookup)
        super().__init__(target=tree_builder)
        uri_rewrite_map = self.create_uri_rewrite_map()
        self.parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_ALWAYS)
        self.parser.ExternalEntityRefHandler \
            = ExternalEntityRefHandler(self.parser, uri_rewrite_map)

    def get_current_line_number(self):
        return self.parser.CurrentLineNumber

    def lookup(self, tag, attrs):
        try:
            return self.element_classes[tag](tag, attrs)
        except KeyError:
            return self.element_class(tag, attrs)

    def create_uri_rewrite_map(self):
        rewrite_map = {}
        catalog = ElementTree.parse(CATALOG_PATH).getroot()
        for elem in catalog.findall('{{{}}}{}'.format(CATALOG_NS,
                                               'rewriteSystem')):
            start_string = elem.get('systemIdStartString')
            prefix = elem.get('rewritePrefix')
            rewrite_map[start_string] = prefix
        return rewrite_map

    def parse(self, xmlfile):
        xml = ElementTree.ElementTree()
        xml.parse(xmlfile, self)
        xml._filename = xmlfile
        xml.getroot()._roottree = xml
        return xml


class ExternalEntityRefHandler(object):
    def __init__(self, parser, uri_rewrite_map):
        self.parser = parser
        self.uri_rewrite_map = uri_rewrite_map

    def __call__(self, context, base, system_id, public_id):
        if base and not urlparse(system_id).netloc:
            system_id = urljoin(base, system_id)
        # look for local copies of common entity files
        external_parser = self.parser.ExternalEntityParserCreate(context)
        external_parser.ExternalEntityRefHandler \
            = ExternalEntityRefHandler(self.parser, self.uri_rewrite_map)
        for start_string, prefix in self.uri_rewrite_map.items():
            if system_id.startswith(start_string):
                remaining = system_id.split(start_string)[1]
                base = urljoin(CATALOG_URL, prefix)
                system_id = urljoin(base, remaining)
                break
        external_parser.SetBase(system_id)
        with urlopen(system_id) as file:
            external_parser.ParseFile(file)
        return 1


class ObjectifiedElement(ElementTree.Element):
    """Simulation of lxml's ObjectifiedElement for xml.etree"""
    def __getattr__(self, name):
        # the following depends on ElementPath internals, but should be fine
        result = ElementPath.find(self.getchildren(), self._namespace + name)
        if result is None:
            raise AttributeError('No such element: {}'.format(name))
        return result

    def __iter__(self):
        try:
            # same hack as above
            for child in ElementPath.findall(self._parent.getchildren(),
                                             self.tag):
                yield child
        except AttributeError:
            # this is the root element
            yield self


class BaseElement(ObjectifiedElement):
    @property
    def filename(self):
        return self._root._roottree._filename

########NEW FILE########
__FILENAME__ = lxml
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


import os

from lxml import etree, objectify

from ...util import all_subclasses
from . import CATALOG_URL


try:
    os.environ['XML_CATALOG_FILES'] += ' ' + CATALOG_URL
except KeyError:
    os.environ['XML_CATALOG_FILES'] = CATALOG_URL


class Parser(object):
    def __init__(self, element_class, namespace=None, schema=None):
        self.element_class = element_class
        lookup = etree.ElementNamespaceClassLookup()
        namespace = lookup.get_namespace(namespace)
        namespace[None] = self.element_class
        namespace.update({cls.__name__.lower(): cls
                          for cls in all_subclasses(self.element_class)})
        self.parser = objectify.makeparser(remove_comments=True,
                                           no_network=True)
        self.parser.set_element_class_lookup(lookup)
        self.schema = etree.RelaxNG(etree.parse(schema))

    def parse(self, xmlfile):
        xml = objectify.parse(xmlfile, self.parser)#, base_url=".")
        xml.xinclude()
        if not self.schema.validate(xml):
            err = self.schema.error_log
            raise Exception("XML file didn't pass schema validation:\n%s" % err)
        return xml


class BaseElement(objectify.ObjectifiedElement):
    @property
    def filename(self):
        return self.getroottree().docinfo.URL

########NEW FILE########
__FILENAME__ = hyphenator
"""

This is a Pure Python module to hyphenate text.

It is inspired by Ruby's Text::Hyphen, but currently reads standard *.dic files,
that must be installed separately.

In the future it's maybe nice if dictionaries could be distributed together with
this module, in a slightly prepared form, like in Ruby's Text::Hyphen.

Wilbert Berendsen, March 2008
info@wilbertberendsen.nl

Ported to Python 3 by Brecht Machiels
brecht@mos6581.org

License: LGPL. More info: http://python-hyphenator.googlecode.com/

"""

import sys
import re

__all__ = ("Hyphenator")

# cache of per-file Hyph_dict objects
hdcache = {}

# precompile some stuff
parse_hex = re.compile(r'\^{2}([0-9a-f]{2})').sub
parse = re.compile(r'(\d?)(\D?)').findall

def hexrepl(matchObj):
    return chr(int(matchObj.group(1), 16))


class parse_alt(object):
    """
    Parse nonstandard hyphen pattern alternative.
    The instance returns a special int with data about the current position
    in the pattern when called with an odd value.
    """
    def __init__(self, pat, alt):
        alt = alt.split(',')
        self.change = alt[0]
        if len(alt) > 2:
            self.index = int(alt[1])
            self.cut = int(alt[2]) + 1
        else:
            self.index = 1
            self.cut = len(re.sub(r'[\d\.]', '', pat)) + 1
        if pat.startswith('.'):
            self.index += 1

    def __call__(self, val):
        self.index -= 1
        val = int(val)
        if val & 1:
            return dint(val, (self.change, self.index, self.cut))
        else:
            return val


class dint(int):
    """
    Just an int some other data can be stuck to in a data attribute.
    Call with ref=other to use the data from the other dint.
    """
    def __new__(cls, value, data=None, ref=None):
        obj = int.__new__(cls, value)
        if ref and type(ref) is dint:
            obj.data = ref.data
        else:
            obj.data = data
        return obj


class Hyph_dict(object):
    """
    Reads a hyph_*.dic file and stores the hyphenation patterns.
    Parameters:
    -filename : filename of hyph_*.dic to read
    """
    def __init__(self, filename):
        self.patterns = {}
        f = open(filename, 'rb')
        charset = f.readline().strip().decode('ASCII')
        if charset.startswith('charset '):
            charset = charset[8:].strip()

        for pat in f:
            pat = pat.decode(charset).strip()
            if not pat or pat[0] == '%': continue
            # replace ^^hh with the real character
            pat = parse_hex(hexrepl, pat)
            # read nonstandard hyphen alternatives
            if '/' in pat:
                pat, alt = pat.split('/', 1)
                factory = parse_alt(pat, alt)
            else:
                factory = int
            tag, value = zip(*[(s, factory(i or "0")) for i, s in parse(pat)])
            # if only zeros, skip this pattern
            if max(value) == 0: continue
            # chop zeros from beginning and end, and store start offset.
            start, end = 0, len(value)
            while not value[start]: start += 1
            while not value[end-1]: end -= 1
            self.patterns[''.join(tag)] = start, value[start:end]
        f.close()
        self.cache = {}
        self.maxlen = max(map(len, self.patterns.keys()))

    def positions(self, word):
        """
        Returns a list of positions where the word can be hyphenated.
        E.g. for the dutch word 'lettergrepen' this method returns
        the list [3, 6, 9].

        Each position is a 'data int' (dint) with a data attribute.
        If the data attribute is not None, it contains a tuple with
        information about nonstandard hyphenation at that point:
        (change, index, cut)

        change: is a string like 'ff=f', that describes how hyphenation
            should take place.
        index: where to substitute the change, counting from the current
            point
        cut: how many characters to remove while substituting the nonstandard
            hyphenation
        """
        word = word.lower()
        points = self.cache.get(word)
        if points is None:
            prepWord = '.%s.' % word
            res = [0] * (len(prepWord) + 1)
            for i in range(len(prepWord) - 1):
                for j in range(i + 1, min(i + self.maxlen, len(prepWord)) + 1):
                    p = self.patterns.get(prepWord[i:j])
                    if p:
                        offset, value = p
                        s = slice(i + offset, i + offset + len(value))
                        res[s] = map(max, value, res[s])

            points = [dint(i - 1, ref=r) for i, r in enumerate(res) if r % 2]
            self.cache[word] = points
        return points


class Hyphenator(object):
    """
    Reads a hyph_*.dic file and stores the hyphenation patterns.
    Provides methods to hyphenate strings in various ways.
    Parameters:
    -filename : filename of hyph_*.dic to read
    -left: make the first syllabe not shorter than this
    -right: make the last syllabe not shorter than this
    -cache: if true (default), use a cached copy of the dic file, if possible

    left and right may also later be changed:
      h = Hyphenator(file)
      h.left = 1
    """
    def __init__(self, filename, left=2, right=2, cache=True):
        self.left  = left
        self.right = right
        if not cache or filename not in hdcache:
            hdcache[filename] = Hyph_dict(filename)
        self.hd = hdcache[filename]

    def positions(self, word):
        """
        Returns a list of positions where the word can be hyphenated.
        See also Hyph_dict.positions. The points that are too far to
        the left or right are removed.
        """
        right = len(word) - self.right
        return [i for i in self.hd.positions(word) if self.left <= i <= right]

    def iterate(self, word):
        """
        Iterate over all hyphenation possibilities, the longest first.
        """
        for p in reversed(self.positions(word)):
            if p.data:
                # get the nonstandard hyphenation data
                change, index, cut = p.data
                if word.isupper():
                    change = change.upper()
                c1, c2 = change.split('=')
                yield word[:p+index] + c1, c2 + word[p+index+cut:]
            else:
                yield word[:p], word[p:]

    def wrap(self, word, width, hyphen='-'):
        """
        Return the longest possible first part and the last part of the
        hyphenated word. The first part has the hyphen already attached.
        Returns None, if there is no hyphenation point before width, or
        if the word could not be hyphenated.
        """
        width -= len(hyphen)
        for w1, w2 in self.iterate(word):
            if len(w1) <= width:
                return w1 + hyphen, w2

    def inserted(self, word, hyphen='-'):
        """
        Returns the word as a string with all the possible hyphens inserted.
        E.g. for the dutch word 'lettergrepen' this method returns
        the string 'let-ter-gre-pen'. The hyphen string to use can be
        given as the second parameter, that defaults to '-'.
        """
        l = list(word)
        for p in reversed(self.positions(word)):
            if p.data:
                # get the nonstandard hyphenation data
                change, index, cut = p.data
                if word.isupper():
                    change = change.upper()
                l[p + index : p + index + cut] = change.replace('=', hyphen)
            else:
                l.insert(p, hyphen)
        return ''.join(l)

    __call__ = iterate


if __name__ == "__main__":

    dict_file = sys.argv[1]
    word = sys.argv[2]

    h = Hyphenator(dict_file, left=1, right=1)

    for i in h(word):
        print(i)


########NEW FILE########
__FILENAME__ = layout
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.

"""
The layout engine. The container classes allow defining rectangular areas on a
page to which :class:`Flowable`\ s can be rendered.

* :class:`Container`: A rectangular area on a page to which flowables are
                      rendered.
* :class:`DownExpandingContainer`: A container that dynamically grows downwards
                                   as flowables are rendered to it.
* :class:`UpExpandingContainer`: Similar to a :class:`DownExpandingContainer`:,
                                 but upwards expanding.
* :class:`VirtualContainer`: A container who's rendered content is not
                             automatically placed on the page. Afterwards, it
                             can be manually placed, however.
* :exc:`EndOfContainer`: Exception raised when a contianer "overflows" during
                         the rendering of flowables.
* :class:`Chain`: A chain of containers. When a container overflows, the
                  rendering of the chain's flowables is continued in the next
                  container in the chain.
* :class:`FootnoteContainer`: TODO

"""

from collections import deque
from contextlib import contextmanager
from copy import copy

from .dimension import Dimension, PT


__all__ = ['Container', 'DownExpandingContainer', 'UpExpandingContainer',
           'VirtualContainer', 'Chain', 'EndOfContainer', 'FootnoteContainer',
           'MaybeContainer', 'discard_state']


class EndOfContainer(Exception):
    """The end of the :class:`FlowableContainer` has been reached."""

    def __init__(self, flowable_state=None):
        """`flowable_state` represents the rendering state of the
        :class:`Flowable` at the time the :class:`FlowableContainer`" overflows.
        """
        self.flowable_state = flowable_state


class ReflowRequired(Exception):
    """Reflow of the current page is required due to insertion of a float."""


class FlowableTarget(object):
    """Something that takes :class:`Flowable`\ s to be rendered."""

    def __init__(self, document):
        """Initialize this flowable target.

        `document` is the :class:`Document` this flowable target is part of."""
        self.flowables = []
        document.flowable_targets.append(self)

        self.document = document
        """The :class:`Document` this flowable target is part of."""

    def append_flowable(self, flowable):
        """Append a `flowable` to the list of flowables to be rendered."""
        self.flowables.append(flowable)

    def __lshift__(self, flowable):
        """Shorthand for :meth:`append_flowable`. Returns `self` so that it can
        be chained."""
        self.append_flowable(flowable)
        return self

    def render(self):
        """Render the flowabless assigned to this flowable target, in the order
        that they have been added."""
        raise NotImplementedError


class ContainerBase(FlowableTarget):
    """Base class for containers that render :class:`Flowable`\ s to a
    rectangular area on a page. :class:`ContainerBase` takes care of the
    container's horizontal positioning and width. Its subclasses handle the
    vertical positioning and height."""

    def __init__(self, name, parent, left=None, top=None, width=None, height=None,
                 right=None, bottom=None, chain=None):
        """Initialize a this container as a child of the `parent` container.

        The horizontal position and width of the container are determined from
        `left`, `width` and `right`. If only `left` or `right` is specified,
        the container's opposite edge will be placed at the corresponding edge
        of the parent container.

        Similarly, the vertical position and height of the container are
        determined from `top`, `height` and `bottom`. If only one of `top` or
        `bottom` is specified, the container's opposite edge is placed at the
        corresponding edge of the parent container.

        Finally, `chain` is a :class:`Chain` this container will be appended to.
        """
        if left is None:
            left = 0*PT if (right and width) is None else (right - width)
        if width is None:
            width = (parent.width - left) if right is None else (right - left)
        if right is None:
            right = left + width
        self.left = left
        self.width = width
        self.right = right

        if top is None:
            top = 0*PT if (bottom and height) is None else (bottom - height)
        if height is None:
            height = (parent.height - top) if bottom is None else (bottom - top)
        if bottom is None:
            bottom = top + height
        self.top = top
        self.height = height
        self.bottom = bottom

        self.name = name
        self.parent = parent
        if parent is not None:  # the Page subclass has no parent
            super().__init__(parent.document)
            parent.children.append(self)
            self.empty_canvas()
        self.children = []
        self.flowables = []
        self.chain = chain
        if chain:
            self.chain.last_container = self

        self.cursor = 0     # initialized at the container's top edge
        """Keeps track of where the next flowable is to be placed. As flowables
        are flowed into the container, the cursor moves down."""

    def __repr__(self):
        return "{}('{}')".format(self.__class__.__name__, self.name)

    def __getattr__(self, name):
        if name in ('_footnote_space', 'float_space'):
            return getattr(self.parent, name)
        raise AttributeError

    @property
    def page(self):
        """The :class:`Page` this container is located on."""
        return self.parent.page

    def empty_canvas(self):
        self.canvas = self.parent.canvas.new()

    @property
    def remaining_height(self):
        return self.height - self.cursor

    def advance(self, height):
        """Advance the cursor by `height`. If this would cause the cursor to
        point beyond the bottom of the container, an :class:`EndOfContainer`
        exception is raised."""
        self.cursor += height
        if self.cursor > self.height:
            raise EndOfContainer

    def check_overflow(self):
        for child in self.children:
            child.check_overflow()
        if self.remaining_height < 0:
            raise ReflowRequired

    def render(self, rerender=False):
        """Render the contents of this container to its canvas. The contents
        include:

        1. the contents of child containers,
        2. :class:`Flowable`\ s that have been added to this container, and
        3. :class:`Flowable`\ s from the :class:`Chain` associated with this
           container.

        The rendering of the child containers (1) does not affect the rendering
        of the flowables (2 and 3). Therefore, a container typically has either
        children or flowables.
        On the other hand, the flowables from the chain are flowed following
        those assigned directly to this container, so it is possible to combine
        both.

        Note that the rendered contents need to be :meth:`place`d on the parent
        container's canvas before they become visible.

        This method returns an iterator yielding all the :class:`Chain`\ s that
        have run out of containers."""
        for child in self.children:
            for chain in child.render(rerender):
                yield chain
        last_descender = None
        for flowable in self.flowables:
            height, last_descender = flowable.flow(self, last_descender)
        if self.chain:
            self.cursor = 0
            if self.chain.render(self, rerender=rerender):
                yield self.chain

    def place(self):
        """Place this container's canvas onto the parent container's canvas."""
        for child in self.children:
            child.place()
        self.canvas.append(float(self.left), float(self.top))


class Container(ContainerBase):
    """A container that renders :class:`Flowable`\ s to a rectangular area on a
    page. The first flowable is rendered at the top of the container. The next
    flowable is rendered below the first one, and so on.

    A :class:`Container` has an origin (the top-left corner), and a width and
    height. It's contents are rendered relative to the container's position in
    its parent :class:`Container`."""



class ExpandingContainer(Container):
    """An dynamically, vertically growing :class:`Container`."""

    def __init__(self, name, parent, left, top, width, right, bottom,
                 max_height=None):
        """See :class:`ContainerBase` for information on the `parent`, `left`,
        `width` and `right` parameters.

        `max_height` is the maximum height this container can grow to."""
        height = Dimension(0)
        super().__init__(name, parent, left, top, width, height, right, bottom)
        self.max_height = max_height or parent.remaining_height

    @property
    def remaining_height(self):
        return self.max_height - self.cursor

    def advance(self, height):
        """Advance the cursor by `height`. If this would expand the container
        to become larger than its maximum height, an :class:`EndOfContainer`
        exception is raised."""
        self.cursor += height
        if self.max_height and self.cursor > self.max_height:
            raise EndOfContainer
        self._expand(height)

    def _expand(self, height):
        """Grow this container by `height`"""
        self.height.grow(height)


class DownExpandingContainer(ExpandingContainer):
    """A container that is anchored at the top and expands downwards."""

    def __init__(self, name, parent, left=None, top=None, width=None,
                 right=None, max_height=None):
        """See :class:`ContainerBase` for information on the `parent`, `left`,
        `width` and `right` parameters.

        `top` specifies the location of the container's top edge with respect to
        that of the parent container. When `top` is omitted, the top edge is
        placed at the top edge of the parent container.

        `max_height` is the maximum height this container can grow to."""
        top = top or parent.cursor
        super().__init__(name, parent, left, top, width, right, None,
                         max_height)


class UpExpandingContainer(ExpandingContainer):
    """A container that is anchored at the bottom and expands upwards."""

    def __init__(self, name, parent, left=None, bottom=None, width=None,
                 right=None, max_height=None):
        """See :class:`ContainerBase` for information on the `parent`, `left`,
        `width` and `right` parameters.

        `bottom` specifies the location of the container's bottom edge with
        respect to that of the parent container. When `bottom` is omitted, the
        bottom edge is placed at the bottom edge of the parent container.

        `max_height` is the maximum height this container can grow to."""
        bottom = bottom or parent.height
        super().__init__(name, parent, left, None, width, right, bottom,
                         max_height)


class MaybeContainer(DownExpandingContainer):
    def __init__(self, parent, left=None, width=None, right=None):
        super().__init__('MAYBE', parent, left=left, top=parent.cursor,
                         width=width, right=right)
        self._do_place = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, _):
        if (exc_type is None or (issubclass(exc_type, EndOfContainer)
                                 and exc_value.flowable_state)):
            self.do_place()

    def do_place(self):
        self.parent.advance(self.cursor)
        self._do_place = True

    def place(self):
        if self._do_place:
            super().place()


@contextmanager
def discard_state():
    try:
        yield
    except EndOfContainer:
        raise EndOfContainer


class VirtualContainer(DownExpandingContainer):
    """An infinitely down-expanding container who's contents are rendered, but
    not placed on the parent container's canvas afterwards. It can later be
    placed manually by using the :meth:`Canvas.append` method of the
    container's :class:`Canvas`."""

    def __init__(self, parent, width=None):
        """Initialize this virtual container as a child of the `parent`
        container.

        `width` specifies the width of the container."""
        super().__init__('VIRTUAL', parent, width=width,
                         max_height=float('+inf'))

    def place(self):
        """This method has no effect."""
        pass

    def place_at(self, left, top):
        for child in self.children:
            child.place()
        self.canvas.append(float(left), float(top))



class FloatContainer(ExpandingContainer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class TopFloatContainer(FloatContainer, DownExpandingContainer):
    def __init__(self, name, parent, left=None, top=None, width=None,
                 right=None, max_height=None):
        super().__init__(name, parent, left, top, width, right, max_height)


class BottomFloatContainer(UpExpandingContainer, FloatContainer):
    def __init__(self, name, parent, left=None, bottom=None, width=None,
                 right=None, max_height=None):
        super().__init__(name, parent, left, bottom, width, right, max_height)


class FootnoteContainer(UpExpandingContainer):
    def __init__(self, name, parent, left=None, bottom=None, width=None,
                 right=None):
        super().__init__(name, parent, left, bottom, width=width, right=right)
        self._footnote_number = 0
        self._footnote_space = self
        self.last_descender = 0
        self.footnote_queue = deque()

    def add_footnote(self, footnote):
        self.footnote_queue.append(footnote)
        if len(self.footnote_queue) == 1:
            self.flow_footnotes()

    def flow_footnotes(self):
        while self.footnote_queue:
            footnote = self.footnote_queue[0]
            footnote_id = footnote.get_id(self.document)
            if footnote_id not in self.document.placed_footnotes:
                _, self.last_descender = footnote.flow(self, self.last_descender)
                self.document.placed_footnotes.add(footnote_id)
            self.footnote_queue.popleft()

    @property
    def next_number(self):
        self._footnote_number += 1
        return self._footnote_number


class ChainState(object):
    def __init__(self, flowable_index=0, flowable_state=None):
        self.flowable_index = flowable_index
        self.flowable_state = flowable_state

    def __copy__(self):
        return self.__class__(self.flowable_index, copy(self.flowable_state))

    def next_flowable(self):
        self.flowable_index += 1
        self.flowable_state = None


class Chain(FlowableTarget):
    """A :class:`FlowableTarget` that renders its flowables to a series of
    containers. Once a container is filled, the chain starts flowing flowables
    into the next container."""

    def __init__(self, document):
        """Initialize this chain.

        `document` is the :class:`Document` this chain is part of."""
        super().__init__(document)
        self._init_state()

    def _init_state(self):
        """Reset the state of this chain: empty the list of containers, and zero
        the counter keeping track of which flowable needs to be rendered next.
        """
        self._state = ChainState()
        self._fresh_page_state = copy(self._state)
        self._rerendering = False

    def render(self, container, rerender=False):
        """Flow the flowables into the containers that have been added to this
        chain.

        Returns an empty iterator when all flowables have been sucessfully
        rendered.
        When the chain runs out of containers before all flowables have been
        rendered, this method returns an iterator yielding itself. This signals
        the :class:`Document` to generate a new page and register new containers
        with this chain."""
        if rerender:
            container.empty_canvas()
            if not self._rerendering:
                # restore saved state on this chain's 1st container on this page
                self._state = copy(self._fresh_page_state)
                self._rerendering = True
        last_descender = None
        try:
            while self._state.flowable_index < len(self.flowables):
                flowable = self.flowables[self._state.flowable_index]
                height, last_descender \
                    = flowable.flow(container, last_descender,
                                    self._state.flowable_state)
                self._state.next_flowable()
            # all flowables have been rendered
            if container == self.last_container:
                self._init_state()    # reset state for the next rendering loop
            return False
        except EndOfContainer as e:
            self._state.flowable_state = e.flowable_state
            if container == self.last_container:
                # save state for when ReflowRequired occurs
                self._fresh_page_state = copy(self._state)
            return container == self.last_container
        except ReflowRequired:
            self._rerendering = False
            raise

########NEW FILE########
__FILENAME__ = math
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


import os
import unicodedata
from warnings import warn

from .dimension import PT
from .font import TypeFamily
from .text import PARENT_STYLE, Style, CharacterLike, Box, Tab
from .text import MixedStyledText
from .paragraph import Paragraph, ParagraphStyle, TabStop, RIGHT, CENTER
from .mathtext import Fonts, MathtextBackendPs, MathTextWarning, Parser, Bunch
from .mathtext import get_unicode_index
from ._mathtext_data import tex2uni, latex_to_standard


class MathFonts(object):
    default = None

    def __init__(self, roman, italic, bold, sans, mono, cal, symbol, fallback):
        self.roman = roman
        self.italic = italic
        self.bold = bold
        self.sans = sans
        self.mono = mono
        self.cal = cal
        self.symbol = symbol
        self.fallback = fallback


class MathStyle(Style):
    attributes = {'fonts': None, # no default fonts yet
                  'font_size': 10*PT}

    def __init__(self, base=PARENT_STYLE, **attributes):
        super().__init__(base=base, **attributes)


class Math(CharacterLike):
    style_class = MathStyle
    _parser = None

    def __init__(self, equation, style=PARENT_STYLE):
        super().__init__(style)
        self.equation = equation.strip()

    def spans(self):
        font_output = RinohFonts(self)
        fontsize = float(self.get_style('font_size'))
        dpi = 72

        # This is a class variable so we don't rebuild the parser
        # with each request.
        if self._parser is None:
            self.__class__._parser = Parser()

        s = '${}$'.format(self.equation)
        box = self._parser.parse(s, font_output, fontsize, dpi)
        font_output.set_canvas_size(box.width, box.height, box.depth)
        (width, height_depth, depth,
         pswriter, used_characters) = font_output.get_results(box)

        box = Box(width, height_depth - depth, depth, pswriter.getvalue())
        box.parent = self
        yield box


 # TODO: is subclass of ParagraphStyle, but doesn't need all of its attributes!
class EquationStyle(ParagraphStyle):
    attributes = {'math_style': None,
                  'tab_stops': [TabStop(0.5, CENTER), TabStop(1.0, RIGHT)]}

    def __init__(self, base=None, **attributes):
        super().__init__(base=base, **attributes)


class Equation(Paragraph):
    style_class = EquationStyle
    next_number = 1

    def __init__(self, equation, style=None):
        self.ref = str(self.next_number)
        number = '({})'.format(self.next_number)
        self.__class__.next_number += 1
        math = Math(equation, style=style.math_style)
        math.parent = self # TODO: encapsulate
        text = [Tab(), math, Tab(), number]
        super().__init__(text, style)

    def reference(self):
        return self.ref


# adapted from matplotlib.mathtext.StandardPsFonts
class RinohFonts(Fonts):
    def __init__(self, styled):
        Fonts.__init__(self, None, MathtextBackendPs())
        self.styled = styled
        self.glyphd = {}
        self.fonts = {}

        type_family = self.styled.get_style('fonts')
        self.fontmap = {'rm'  : type_family.roman,
                        'it'  : type_family.italic,
                        'bf'  : type_family.bold,
                        'sf'  : type_family.sans,
                        'tt'  : type_family.mono,
                        'cal' : type_family.cal,
                        None  : type_family.symbol,
                        'fb'  : type_family.fallback
                        }

        for font in self.fontmap.values():
            font.psFont.metrics.fname = font.filename

    def _get_font(self, font):
        psg_doc = self.styled.document.backend_document.psg_doc
        psg_doc.add_font(self.fontmap[font].psFont)
        return self.fontmap[font].psFont

    def _get_info(self, fontname, font_class, sym, fontsize, dpi):
        'load the cmfont, metrics and glyph with caching'
        key = fontname, sym, fontsize, dpi
        tup = self.glyphd.get(key)

        if tup is not None:
            return tup

        # Only characters in the "Letter" class should really be italicized.
        # This class includes greek letters, so we're ok
        if (fontname == 'it' and
            (len(sym) > 1 or
             not unicodedata.category(str(sym)).startswith("L"))):
            fontname = 'rm'

        found_symbol = False

        glyph = 'glyph__dummy'

        if sym in latex_to_standard:
            fontname, num = latex_to_standard[sym]
            if fontname == 'psyr':
                fontname = None
            elif fontname == 'pncri8a':
                fontname ='it'
            elif fontname == 'pncr8a':
                fontname ='rm'

        try:
            num = get_unicode_index(sym)
            found_symbol = True
        except ValueError:
            warn("No TeX to unicode mapping for '{}'".format(sym),
                 MathTextWarning)

        slanted = (fontname == 'it')
        font = self._get_font(fontname)
        font_metrics =font.metrics

        if found_symbol:
            try:
                char_metrics = font_metrics[num]
                symbol_name = char_metrics.ps_name
            except KeyError:
                warn("No glyph in font '{}' for '{}'"
                     .format(font.ps_name, sym), MathTextWarning)
                try:
                    font = self._get_font('fb')
                    font_metrics =font.metrics
                    char_metrics = font_metrics[num]
                    symbol_name = char_metrics.ps_name
                except KeyError:
                    warn("No glyph in font '{}' for '{}'"
                         .format(font.ps_name, sym), MathTextWarning)
                    found_symbol = False

        if not found_symbol:
            try:
                glyph = sym = '?'
                num = ord(glyph)
                char_metrics = font_metrics[num]
                symbol_name = char_metrics.ps_name
            except KeyError:
                num, char_metrics = list(font_metrics.items())[0]
                glyph = sym = chr(num)
                symbol_name = char_metrics.ps_name

        offset = 0

        scale = 0.001 * fontsize

        char_bounding_box = char_metrics.bounding_box.as_tuple()
        xmin, ymin, xmax, ymax = [val * scale for val in char_bounding_box]
        metrics = Bunch(
            advance  = char_metrics.width * scale,
            width    = char_metrics.width * scale,
            height   = ymax,
            xmin = xmin,
            xmax = xmax,
            ymin = ymin + offset,
            ymax = ymax + offset,
            # iceberg is the equivalent of TeX's "height"
            iceberg = ymax + offset,
            slanted = slanted
            )

        self.glyphd[key] = Bunch(
            font            = font_metrics,
            fontsize        = fontsize,
            postscript_name = font.ps_name,
            metrics         = metrics,
            symbol_name     = symbol_name,
            num             = num,
            glyph           = glyph,
            offset          = offset
            )

        return self.glyphd[key]

    def get_kern(self, font1, fontclass1, sym1, fontsize1,
                 font2, fontclass2, sym2, fontsize2, dpi):
        if font1 == font2 and fontsize1 == fontsize2:
            info1 = self._get_info(font1, fontclass1, sym1, fontsize1, dpi)
            info2 = self._get_info(font2, fontclass2, sym2, fontsize2, dpi)
            kerning = info1.font.get_kerning(info1.num, info2.num)
            return kerning * 0.001 * fontsize1
        else:
            return 0.0
            #return Fonts.get_kern(self, font1, fontclass1, sym1, fontsize1,
            #                      font2, fontclass2, sym2, fontsize2, dpi)

    def get_xheight(self, font, fontsize, dpi):
        cached_font = self._get_font(font)
        return cached_font.metrics.FontMetrics['XHeight'] * 0.001 * fontsize

    def get_underline_thickness(self, font, fontsize, dpi):
        cached_font_metrics = self._get_font(font).metrics
        ul_th = (cached_font_metrics.FontMetrics['Direction'][0]
                 ['UnderlineThickness'])
        return ul_th * 0.001 * fontsize

########NEW FILE########
__FILENAME__ = mathtext
r"""
:mod:`~matplotlib.mathtext` is a module for parsing a subset of the
TeX math syntax and drawing them to a matplotlib backend.

For a tutorial of its usage see :ref:`mathtext-tutorial`.  This
document is primarily concerned with implementation details.

The module uses pyparsing_ to parse the TeX expression.

.. _pyparsing: http://pyparsing.wikispaces.com/

The Bakoma distribution of the TeX Computer Modern fonts, and STIX
fonts are supported.  There is experimental support for using
arbitrary fonts, but results may vary without proper tweaking and
metrics for those fonts.

If you find TeX expressions that don't parse or render properly,
please email mdroe@stsci.edu, but please check KNOWN ISSUES below first.
"""

import os, sys
from io import StringIO
from math import ceil
from warnings import warn

from .pyparsing_py3 import Combine, Group, Optional, Forward, \
         Literal, OneOrMore, ZeroOrMore, ParseException, Empty, \
         ParseResults, Suppress, oneOf, StringEnd, ParseFatalException, \
         FollowedBy, Regex, ParserElement, QuotedString, ParseBaseException

# Enable packrat parsing
ParserElement.enablePackrat()

from ._mathtext_data import tex2uni, latex_to_standard

####################

# from numpy
inf = float('inf')

def isinf(number):
    return number == inf

# from matplotlib
rcParams = {'mathtext.default': 'it'}

# from matplotlib.ft2font
LOAD_NO_HINTING = 2

# from matplotlib.cbook
class Bunch:
    """
    Often we want to just collect a bunch of stuff together, naming each
    item of the bunch; a dictionary's OK for that, but a small do- nothing
    class is even handier, and prettier to use.  Whenever you want to
    group a few variables:

      >>> point = Bunch(datum=2, squared=4, coord=12)
      >>> point.datum

      By: Alex Martelli
      From: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52308
    """
    def __init__(self, **kwds):
        self.__dict__.update(kwds)


    def __repr__(self):
        keys = self.__dict__.keys()
        return 'Bunch(%s)'%', '.join(['%s=%s'%(k,self.__dict__[k]) for k in keys])


class GetRealpathAndStat:
    def __init__(self):
        self._cache = {}

    def __call__(self, path):
        result = self._cache.get(path)
        if result is None:
            realpath = os.path.realpath(path)
            if sys.platform == 'win32':
                stat_key = realpath
            else:
                stat = os.stat(realpath)
                stat_key = (stat.st_ino, stat.st_dev)
            result = realpath, stat_key
            self._cache[path] = result
        return result
get_realpath_and_stat = GetRealpathAndStat()


def is_string_like(obj):
    'Return True if *obj* looks like a string'
    if isinstance(obj, str): return True
    # numpy strings are subclass of str, ma strings are not
    if ma.isMaskedArray(obj):
        if obj.ndim == 0 and obj.dtype.kind in 'SU':
            return True
        else:
            return False
    try: obj + ''
    except: return False
    return True


##############################################################################
# FONTS

def get_unicode_index(symbol):
    """get_unicode_index(symbol) -> integer

Return the integer index (from the Unicode table) of symbol.  *symbol*
can be a single unicode character, a TeX command (i.e. r'\pi'), or a
Type1 symbol name (i.e. 'phi').
"""
    # From UTF #25: U+2212 minus sign is the preferred
    # representation of the unary and binary minus sign rather than
    # the ASCII-derived U+002D hyphen-minus, because minus sign is
    # unambiguous and because it is rendered with a more desirable
    # length, usually longer than a hyphen.
    if symbol == '-':
        return 0x2212
    try:# This will succeed if symbol is a single unicode char
        return ord(symbol)
    except TypeError:
        pass
    try:# Is symbol a TeX symbol (i.e. \alpha)
        return tex2uni[symbol.strip("\\")]
    except KeyError:
        message = """'%(symbol)s' is not a valid Unicode character or
TeX/Type1 symbol"""%locals()
        raise ValueError(message)

def unichr_safe(index):
    """Return the Unicode character corresponding to the index,
or the replacement character if this is a narrow build of Python
and the requested character is outside the BMP."""
    try:
        return unichr(index)
    except ValueError:
        return unichr(0xFFFD)

class MathtextBackend(object):
    """
    The base class for the mathtext backend-specific code.  The
    purpose of :class:`MathtextBackend` subclasses is to interface
    between mathtext and a specific matplotlib graphics backend.

    Subclasses need to override the following:

      - :meth:`render_glyph`
      - :meth:`render_filled_rect`
      - :meth:`get_results`

    And optionally, if you need to use a Freetype hinting style:

      - :meth:`get_hinting_type`
    """
    def __init__(self):
        self.width = 0
        self.height = 0
        self.depth = 0

    def set_canvas_size(self, w, h, d):
        'Dimension the drawing canvas'
        self.width  = w
        self.height = h
        self.depth  = d

    def render_glyph(self, ox, oy, info):
        """
        Draw a glyph described by *info* to the reference point (*ox*,
        *oy*).
        """
        raise NotImplementedError()

    def render_filled_rect(self, x1, y1, x2, y2):
        """
        Draw a filled black rectangle from (*x1*, *y1*) to (*x2*, *y2*).
        """
        raise NotImplementedError()

    def get_results(self, box):
        """
        Return a backend-specific tuple to return to the backend after
        all processing is done.
        """
        raise NotImplementedError()

    def get_hinting_type(self):
        """
        Get the Freetype hinting type to use with this particular
        backend.
        """
        return LOAD_NO_HINTING


class MathtextBackendPs(MathtextBackend):
    """
    Store information to write a mathtext rendering to the PostScript
    backend.
    """
    def __init__(self):
        self.pswriter = StringIO()
        self.lastfont = None

    def render_glyph(self, ox, oy, info):
        oy = self.height - oy + info.offset
        postscript_name = info.postscript_name
        fontsize        = info.fontsize
        symbol_name     = info.symbol_name

        if (postscript_name, fontsize) != self.lastfont:
            ps = """/%(postscript_name)s findfont
%(fontsize)s scalefont
setfont
""" % locals()
            self.lastfont = postscript_name, fontsize
            self.pswriter.write(ps)

        ps = """%(ox)f %(oy)f moveto
/%(symbol_name)s glyphshow\n
""" % locals()
        self.pswriter.write(ps)

    def render_rect_filled(self, x1, y1, x2, y2):
        ps = "%f %f %f %f rectfill\n" % (x1, self.height - y2, x2 - x1, y2 - y1)
        self.pswriter.write(ps)

    def get_results(self, box, used_characters):
        ship(0, -self.depth, box)
        return (self.width,
                self.height + self.depth,
                self.depth,
                self.pswriter,
                used_characters)


class Fonts(object):
    """
    An abstract base class for a system of fonts to use for mathtext.

    The class must be able to take symbol keys and font file names and
    return the character metrics.  It also delegates to a backend class
    to do the actual drawing.
    """

    def __init__(self, default_font_prop, mathtext_backend):
        """
        *default_font_prop*: A
        :class:`~matplotlib.font_manager.FontProperties` object to use
        for the default non-math font, or the base font for Unicode
        (generic) font rendering.

        *mathtext_backend*: A subclass of :class:`MathTextBackend`
        used to delegate the actual rendering.
        """
        self.default_font_prop = default_font_prop
        self.mathtext_backend = mathtext_backend
        self.used_characters = {}

    def destroy(self):
        """
        Fix any cyclical references before the object is about
        to be destroyed.
        """
        self.used_characters = None

    def get_kern(self, font1, fontclass1, sym1, fontsize1,
                 font2, fontclass2, sym2, fontsize2, dpi):
        """
        Get the kerning distance for font between *sym1* and *sym2*.

        *fontX*: one of the TeX font names::

          tt, it, rm, cal, sf, bf or default/regular (non-math)

        *fontclassX*: TODO

        *symX*: a symbol in raw TeX form. e.g. '1', 'x' or '\sigma'

        *fontsizeX*: the fontsize in points

        *dpi*: the current dots-per-inch
        """
        return 0.

    def get_metrics(self, font, font_class, sym, fontsize, dpi):
        """
        *font*: one of the TeX font names::

          tt, it, rm, cal, sf, bf or default/regular (non-math)

        *font_class*: TODO

        *sym*:  a symbol in raw TeX form. e.g. '1', 'x' or '\sigma'

        *fontsize*: font size in points

        *dpi*: current dots-per-inch

        Returns an object with the following attributes:

          - *advance*: The advance distance (in points) of the glyph.

          - *height*: The height of the glyph in points.

          - *width*: The width of the glyph in points.

          - *xmin*, *xmax*, *ymin*, *ymax* - the ink rectangle of the glyph

          - *iceberg* - the distance from the baseline to the top of
            the glyph.  This corresponds to TeX's definition of
            "height".
        """
        info = self._get_info(font, font_class, sym, fontsize, dpi)
        return info.metrics

    def set_canvas_size(self, w, h, d):
        """
        Set the size of the buffer used to render the math expression.
        Only really necessary for the bitmap backends.
        """
        self.width, self.height, self.depth = ceil(w), ceil(h), ceil(d)
        self.mathtext_backend.set_canvas_size(self.width, self.height, self.depth)

    def render_glyph(self, ox, oy, facename, font_class, sym, fontsize, dpi):
        """
        Draw a glyph at

          - *ox*, *oy*: position

          - *facename*: One of the TeX face names

          - *font_class*:

          - *sym*: TeX symbol name or single character

          - *fontsize*: fontsize in points

          - *dpi*: The dpi to draw at.
        """
        info = self._get_info(facename, font_class, sym, fontsize, dpi)
        realpath, stat_key = get_realpath_and_stat(info.font.fname)
        used_characters = self.used_characters.setdefault(
            stat_key, (realpath, set()))
        used_characters[1].add(info.num)
        self.mathtext_backend.render_glyph(ox, oy, info)

    def render_rect_filled(self, x1, y1, x2, y2):
        """
        Draw a filled rectangle from (*x1*, *y1*) to (*x2*, *y2*).
        """
        self.mathtext_backend.render_rect_filled(x1, y1, x2, y2)

    def get_xheight(self, font, fontsize, dpi):
        """
        Get the xheight for the given *font* and *fontsize*.
        """
        raise NotImplementedError()

    def get_underline_thickness(self, font, fontsize, dpi):
        """
        Get the line thickness that matches the given font.  Used as a
        base unit for drawing lines such as in a fraction or radical.
        """
        raise NotImplementedError()

    def get_used_characters(self):
        """
        Get the set of characters that were used in the math
        expression.  Used by backends that need to subset fonts so
        they know which glyphs to include.
        """
        return self.used_characters

    def get_results(self, box):
        """
        Get the data needed by the backend to render the math
        expression.  The return value is backend-specific.
        """
        result = self.mathtext_backend.get_results(box, self.get_used_characters())
        self.destroy()
        return result

    def get_sized_alternatives_for_symbol(self, fontname, sym):
        """
        Override if your font provides multiple sizes of the same
        symbol.  Should return a list of symbols matching *sym* in
        various sizes.  The expression renderer will select the most
        appropriate size for a given situation from this list.
        """
        return [(fontname, sym)]


##############################################################################
# TeX-LIKE BOX MODEL

# The following is based directly on the document 'woven' from the
# TeX82 source code.  This information is also available in printed
# form:
#
#    Knuth, Donald E.. 1986.  Computers and Typesetting, Volume B:
#    TeX: The Program.  Addison-Wesley Professional.
#
# The most relevant "chapters" are:
#    Data structures for boxes and their friends
#    Shipping pages out (Ship class)
#    Packaging (hpack and vpack)
#    Data structures for math mode
#    Subroutines for math mode
#    Typesetting math formulas
#
# Many of the docstrings below refer to a numbered "node" in that
# book, e.g. node123
#
# Note that (as TeX) y increases downward, unlike many other parts of
# matplotlib.

# How much text shrinks when going to the next-smallest level.  GROW_FACTOR
# must be the inverse of SHRINK_FACTOR.
SHRINK_FACTOR   = 0.7
GROW_FACTOR     = 1.0 / SHRINK_FACTOR
# The number of different sizes of chars to use, beyond which they will not
# get any smaller
NUM_SIZE_LEVELS = 6
# Percentage of x-height of additional horiz. space after sub/superscripts
SCRIPT_SPACE    = 0.2
# Percentage of x-height that sub/superscripts drop below the baseline
SUBDROP         = 0.3
# Percentage of x-height that superscripts drop below the baseline
SUP1            = 0.5
# Percentage of x-height that subscripts drop below the baseline
SUB1            = 0.0
# Percentage of x-height that superscripts are offset relative to the subscript
DELTA           = 0.18

class MathTextWarning(Warning):
    pass

class Node(object):
    """
    A node in the TeX box model
    """
    def __init__(self):
        self.size = 0

    def __repr__(self):
        return self.__internal_repr__()

    def __internal_repr__(self):
        return self.__class__.__name__

    def get_kerning(self, next):
        return 0.0

    def shrink(self):
        """
        Shrinks one level smaller.  There are only three levels of
        sizes, after which things will no longer get smaller.
        """
        self.size += 1

    def grow(self):
        """
        Grows one level larger.  There is no limit to how big
        something can get.
        """
        self.size -= 1

    def render(self, x, y):
        pass

class Box(Node):
    """
    Represents any node with a physical location.
    """
    def __init__(self, width, height, depth):
        Node.__init__(self)
        self.width  = width
        self.height = height
        self.depth  = depth

    def shrink(self):
        Node.shrink(self)
        if self.size < NUM_SIZE_LEVELS:
            self.width  *= SHRINK_FACTOR
            self.height *= SHRINK_FACTOR
            self.depth  *= SHRINK_FACTOR

    def grow(self):
        Node.grow(self)
        self.width  *= GROW_FACTOR
        self.height *= GROW_FACTOR
        self.depth  *= GROW_FACTOR

    def render(self, x1, y1, x2, y2):
        pass

class Vbox(Box):
    """
    A box with only height (zero width).
    """
    def __init__(self, height, depth):
        Box.__init__(self, 0., height, depth)

class Hbox(Box):
    """
    A box with only width (zero height and depth).
    """
    def __init__(self, width):
        Box.__init__(self, width, 0., 0.)

class Char(Node):
    """
    Represents a single character.  Unlike TeX, the font information
    and metrics are stored with each :class:`Char` to make it easier
    to lookup the font metrics when needed.  Note that TeX boxes have
    a width, height, and depth, unlike Type1 and Truetype which use a
    full bounding box and an advance in the x-direction.  The metrics
    must be converted to the TeX way, and the advance (if different
    from width) must be converted into a :class:`Kern` node when the
    :class:`Char` is added to its parent :class:`Hlist`.
    """
    def __init__(self, c, state):
        Node.__init__(self)
        self.c = c
        self.font_output = state.font_output
        assert isinstance(state.font, (str, int))
        self.font = state.font
        self.font_class = state.font_class
        self.fontsize = state.fontsize
        self.dpi = state.dpi
        # The real width, height and depth will be set during the
        # pack phase, after we know the real fontsize
        self._update_metrics()

    def __internal_repr__(self):
        return '`%s`' % self.c

    def _update_metrics(self):
        metrics = self._metrics = self.font_output.get_metrics(
            self.font, self.font_class, self.c, self.fontsize, self.dpi)
        if self.c == ' ':
            self.width = metrics.advance
        else:
            self.width = metrics.width
        self.height = metrics.iceberg
        self.depth = -(metrics.iceberg - metrics.height)

    def is_slanted(self):
        return self._metrics.slanted

    def get_kerning(self, next):
        """
        Return the amount of kerning between this and the given
        character.  Called when characters are strung together into
        :class:`Hlist` to create :class:`Kern` nodes.
        """
        advance = self._metrics.advance - self.width
        kern = 0.
        if isinstance(next, Char):
            kern = self.font_output.get_kern(
                self.font, self.font_class, self.c, self.fontsize,
                next.font, next.font_class, next.c, next.fontsize,
                self.dpi)
        return advance + kern

    def render(self, x, y):
        """
        Render the character to the canvas
        """
        self.font_output.render_glyph(
            x, y,
            self.font, self.font_class, self.c, self.fontsize, self.dpi)

    def shrink(self):
        Node.shrink(self)
        if self.size < NUM_SIZE_LEVELS:
            self.fontsize *= SHRINK_FACTOR
            self.width    *= SHRINK_FACTOR
            self.height   *= SHRINK_FACTOR
            self.depth    *= SHRINK_FACTOR

    def grow(self):
        Node.grow(self)
        self.fontsize *= GROW_FACTOR
        self.width    *= GROW_FACTOR
        self.height   *= GROW_FACTOR
        self.depth    *= GROW_FACTOR

class Accent(Char):
    """
    The font metrics need to be dealt with differently for accents,
    since they are already offset correctly from the baseline in
    TrueType fonts.
    """
    def _update_metrics(self):
        metrics = self._metrics = self.font_output.get_metrics(
            self.font, self.font_class, self.c, self.fontsize, self.dpi)
        self.width = metrics.xmax - metrics.xmin
        self.height = metrics.ymax - metrics.ymin
        self.depth = 0

    def shrink(self):
        Char.shrink(self)
        self._update_metrics()

    def grow(self):
        Char.grow(self)
        self._update_metrics()

    def render(self, x, y):
        """
        Render the character to the canvas.
        """
        self.font_output.render_glyph(
            x - self._metrics.xmin, y + self._metrics.ymin,
            self.font, self.font_class, self.c, self.fontsize, self.dpi)

class List(Box):
    """
    A list of nodes (either horizontal or vertical).
    """
    def __init__(self, elements):
        Box.__init__(self, 0., 0., 0.)
        self.shift_amount = 0.   # An arbitrary offset
        self.children     = elements # The child nodes of this list
        # The following parameters are set in the vpack and hpack functions
        self.glue_set     = 0.   # The glue setting of this list
        self.glue_sign    = 0    # 0: normal, -1: shrinking, 1: stretching
        self.glue_order   = 0    # The order of infinity (0 - 3) for the glue

    def __repr__(self):
        return '[%s <%.02f %.02f %.02f %.02f> %s]' % (
            self.__internal_repr__(),
            self.width, self.height,
            self.depth, self.shift_amount,
            ' '.join([repr(x) for x in self.children]))

    def _determine_order(self, totals):
        """
        A helper function to determine the highest order of glue
        used by the members of this list.  Used by vpack and hpack.
        """
        o = 0
        for i in range(len(totals) - 1, 0, -1):
            if totals[i] != 0.0:
                o = i
                break
        return o

    def _set_glue(self, x, sign, totals, error_type):
        o = self._determine_order(totals)
        self.glue_order = o
        self.glue_sign = sign
        if totals[o] != 0.:
            self.glue_set = x / totals[o]
        else:
            self.glue_sign = 0
            self.glue_ratio = 0.
        if o == 0:
            if len(self.children):
                warn("%s %s: %r" % (error_type, self.__class__.__name__, self),
                     MathTextWarning)

    def shrink(self):
        for child in self.children:
            child.shrink()
        Box.shrink(self)
        if self.size < NUM_SIZE_LEVELS:
            self.shift_amount *= SHRINK_FACTOR
            self.glue_set     *= SHRINK_FACTOR

    def grow(self):
        for child in self.children:
            child.grow()
        Box.grow(self)
        self.shift_amount *= GROW_FACTOR
        self.glue_set     *= GROW_FACTOR

class Hlist(List):
    """
    A horizontal list of boxes.
    """
    def __init__(self, elements, w=0., m='additional', do_kern=True):
        List.__init__(self, elements)
        if do_kern:
            self.kern()
        self.hpack()

    def kern(self):
        """
        Insert :class:`Kern` nodes between :class:`Char` nodes to set
        kerning.  The :class:`Char` nodes themselves determine the
        amount of kerning they need (in :meth:`~Char.get_kerning`),
        and this function just creates the linked list in the correct
        way.
        """
        new_children = []
        num_children = len(self.children)
        if num_children:
            for i in range(num_children):
                elem = self.children[i]
                if i < num_children - 1:
                    next = self.children[i + 1]
                else:
                    next = None

                new_children.append(elem)
                kerning_distance = elem.get_kerning(next)
                if kerning_distance != 0.:
                    kern = Kern(kerning_distance)
                    new_children.append(kern)
            self.children = new_children

    # This is a failed experiment to fake cross-font kerning.
#     def get_kerning(self, next):
#         if len(self.children) >= 2 and isinstance(self.children[-2], Char):
#             if isinstance(next, Char):
#                 print "CASE A"
#                 return self.children[-2].get_kerning(next)
#             elif isinstance(next, Hlist) and len(next.children) and isinstance(next.children[0], Char):
#                 print "CASE B"
#                 result = self.children[-2].get_kerning(next.children[0])
#                 print result
#                 return result
#         return 0.0

    def hpack(self, w=0., m='additional'):
        """
        The main duty of :meth:`hpack` is to compute the dimensions of
        the resulting boxes, and to adjust the glue if one of those
        dimensions is pre-specified.  The computed sizes normally
        enclose all of the material inside the new box; but some items
        may stick out if negative glue is used, if the box is
        overfull, or if a ``\\vbox`` includes other boxes that have
        been shifted left.

          - *w*: specifies a width

          - *m*: is either 'exactly' or 'additional'.

        Thus, ``hpack(w, 'exactly')`` produces a box whose width is
        exactly *w*, while ``hpack(w, 'additional')`` yields a box
        whose width is the natural width plus *w*.  The default values
        produce a box with the natural width.
        """
        # I don't know why these get reset in TeX.  Shift_amount is pretty
        # much useless if we do.
        #self.shift_amount = 0.
        h = 0.
        d = 0.
        x = 0.
        total_stretch = [0.] * 4
        total_shrink = [0.] * 4
        for p in self.children:
            if isinstance(p, Char):
                x += p.width
                h = max(h, p.height)
                d = max(d, p.depth)
            elif isinstance(p, Box):
                x += p.width
                if not isinf(p.height) and not isinf(p.depth):
                    s = getattr(p, 'shift_amount', 0.)
                    h = max(h, p.height - s)
                    d = max(d, p.depth + s)
            elif isinstance(p, Glue):
                glue_spec = p.glue_spec
                x += glue_spec.width
                total_stretch[glue_spec.stretch_order] += glue_spec.stretch
                total_shrink[glue_spec.shrink_order] += glue_spec.shrink
            elif isinstance(p, Kern):
                x += p.width
        self.height = h
        self.depth = d

        if m == 'additional':
            w += x
        self.width = w
        x = w - x

        if x == 0.:
            self.glue_sign = 0
            self.glue_order = 0
            self.glue_ratio = 0.
            return
        if x > 0.:
            self._set_glue(x, 1, total_stretch, "Overfull")
        else:
            self._set_glue(x, -1, total_shrink, "Underfull")

class Vlist(List):
    """
    A vertical list of boxes.
    """
    def __init__(self, elements, h=0., m='additional'):
        List.__init__(self, elements)
        self.vpack()

    def vpack(self, h=0., m='additional', l=float(inf)):
        """
        The main duty of :meth:`vpack` is to compute the dimensions of
        the resulting boxes, and to adjust the glue if one of those
        dimensions is pre-specified.

          - *h*: specifies a height
          - *m*: is either 'exactly' or 'additional'.
          - *l*: a maximum height

        Thus, ``vpack(h, 'exactly')`` produces a box whose height is
        exactly *h*, while ``vpack(h, 'additional')`` yields a box
        whose height is the natural height plus *h*.  The default
        values produce a box with the natural width.
        """
        # I don't know why these get reset in TeX.  Shift_amount is pretty
        # much useless if we do.
        # self.shift_amount = 0.
        w = 0.
        d = 0.
        x = 0.
        total_stretch = [0.] * 4
        total_shrink = [0.] * 4
        for p in self.children:
            if isinstance(p, Box):
                x += d + p.height
                d = p.depth
                if not isinf(p.width):
                    s = getattr(p, 'shift_amount', 0.)
                    w = max(w, p.width + s)
            elif isinstance(p, Glue):
                x += d
                d = 0.
                glue_spec = p.glue_spec
                x += glue_spec.width
                total_stretch[glue_spec.stretch_order] += glue_spec.stretch
                total_shrink[glue_spec.shrink_order] += glue_spec.shrink
            elif isinstance(p, Kern):
                x += d + p.width
                d = 0.
            elif isinstance(p, Char):
                raise RuntimeError("Internal mathtext error: Char node found in Vlist.")

        self.width = w
        if d > l:
            x += d - l
            self.depth = l
        else:
            self.depth = d

        if m == 'additional':
            h += x
        self.height = h
        x = h - x

        if x == 0:
            self.glue_sign = 0
            self.glue_order = 0
            self.glue_ratio = 0.
            return

        if x > 0.:
            self._set_glue(x, 1, total_stretch, "Overfull")
        else:
            self._set_glue(x, -1, total_shrink, "Underfull")

class Rule(Box):
    """
    A :class:`Rule` node stands for a solid black rectangle; it has
    *width*, *depth*, and *height* fields just as in an
    :class:`Hlist`. However, if any of these dimensions is inf, the
    actual value will be determined by running the rule up to the
    boundary of the innermost enclosing box. This is called a "running
    dimension." The width is never running in an :class:`Hlist`; the
    height and depth are never running in a :class:`Vlist`.
    """
    def __init__(self, width, height, depth, state):
        Box.__init__(self, width, height, depth)
        self.font_output = state.font_output

    def render(self, x, y, w, h):
        self.font_output.render_rect_filled(x, y, x + w, y + h)

class Hrule(Rule):
    """
    Convenience class to create a horizontal rule.
    """
    def __init__(self, state, thickness=None):
        if thickness is None:
            thickness = state.font_output.get_underline_thickness(
                state.font, state.fontsize, state.dpi)
        height = depth = thickness * 0.5
        Rule.__init__(self, inf, height, depth, state)

class Vrule(Rule):
    """
    Convenience class to create a vertical rule.
    """
    def __init__(self, state):
        thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)
        Rule.__init__(self, thickness, inf, inf, state)

class Glue(Node):
    """
    Most of the information in this object is stored in the underlying
    :class:`GlueSpec` class, which is shared between multiple glue objects.  (This
    is a memory optimization which probably doesn't matter anymore, but it's
    easier to stick to what TeX does.)
    """
    def __init__(self, glue_type, copy=False):
        Node.__init__(self)
        self.glue_subtype   = 'normal'
        if is_string_like(glue_type):
            glue_spec = GlueSpec.factory(glue_type)
        elif isinstance(glue_type, GlueSpec):
            glue_spec = glue_type
        else:
            raise ArgumentError("glue_type must be a glue spec name or instance.")
        if copy:
            glue_spec = glue_spec.copy()
        self.glue_spec      = glue_spec

    def shrink(self):
        Node.shrink(self)
        if self.size < NUM_SIZE_LEVELS:
            if self.glue_spec.width != 0.:
                self.glue_spec = self.glue_spec.copy()
                self.glue_spec.width *= SHRINK_FACTOR

    def grow(self):
        Node.grow(self)
        if self.glue_spec.width != 0.:
            self.glue_spec = self.glue_spec.copy()
            self.glue_spec.width *= GROW_FACTOR

class GlueSpec(object):
    """
    See :class:`Glue`.
    """
    def __init__(self, width=0., stretch=0., stretch_order=0, shrink=0., shrink_order=0):
        self.width         = width
        self.stretch       = stretch
        self.stretch_order = stretch_order
        self.shrink        = shrink
        self.shrink_order  = shrink_order

    def copy(self):
        return GlueSpec(
            self.width,
            self.stretch,
            self.stretch_order,
            self.shrink,
            self.shrink_order)

    def factory(cls, glue_type):
        return cls._types[glue_type]
    factory = classmethod(factory)

GlueSpec._types = {
    'fil':         GlueSpec(0., 1., 1, 0., 0),
    'fill':        GlueSpec(0., 1., 2, 0., 0),
    'filll':       GlueSpec(0., 1., 3, 0., 0),
    'neg_fil':     GlueSpec(0., 0., 0, 1., 1),
    'neg_fill':    GlueSpec(0., 0., 0, 1., 2),
    'neg_filll':   GlueSpec(0., 0., 0, 1., 3),
    'empty':       GlueSpec(0., 0., 0, 0., 0),
    'ss':          GlueSpec(0., 1., 1, -1., 1)
}

# Some convenient ways to get common kinds of glue

class Fil(Glue):
    def __init__(self):
        Glue.__init__(self, 'fil')

class Fill(Glue):
    def __init__(self):
        Glue.__init__(self, 'fill')

class Filll(Glue):
    def __init__(self):
        Glue.__init__(self, 'filll')

class NegFil(Glue):
    def __init__(self):
        Glue.__init__(self, 'neg_fil')

class NegFill(Glue):
    def __init__(self):
        Glue.__init__(self, 'neg_fill')

class NegFilll(Glue):
    def __init__(self):
        Glue.__init__(self, 'neg_filll')

class SsGlue(Glue):
    def __init__(self):
        Glue.__init__(self, 'ss')

class HCentered(Hlist):
    """
    A convenience class to create an :class:`Hlist` whose contents are
    centered within its enclosing box.
    """
    def __init__(self, elements):
        Hlist.__init__(self, [SsGlue()] + elements + [SsGlue()],
                       do_kern=False)

class VCentered(Hlist):
    """
    A convenience class to create a :class:`Vlist` whose contents are
    centered within its enclosing box.
    """
    def __init__(self, elements):
        Vlist.__init__(self, [SsGlue()] + elements + [SsGlue()])

class Kern(Node):
    """
    A :class:`Kern` node has a width field to specify a (normally
    negative) amount of spacing. This spacing correction appears in
    horizontal lists between letters like A and V when the font
    designer said that it looks better to move them closer together or
    further apart. A kern node can also appear in a vertical list,
    when its *width* denotes additional spacing in the vertical
    direction.
    """
    height = 0
    depth = 0

    def __init__(self, width):
        Node.__init__(self)
        self.width = width

    def __repr__(self):
        return "k%.02f" % self.width

    def shrink(self):
        Node.shrink(self)
        if self.size < NUM_SIZE_LEVELS:
            self.width *= SHRINK_FACTOR

    def grow(self):
        Node.grow(self)
        self.width *= GROW_FACTOR

class SubSuperCluster(Hlist):
    """
    :class:`SubSuperCluster` is a sort of hack to get around that fact
    that this code do a two-pass parse like TeX.  This lets us store
    enough information in the hlist itself, namely the nucleus, sub-
    and super-script, such that if another script follows that needs
    to be attached, it can be reconfigured on the fly.
    """
    def __init__(self):
        self.nucleus = None
        self.sub = None
        self.super = None
        Hlist.__init__(self, [])

class AutoHeightChar(Hlist):
    """
    :class:`AutoHeightChar` will create a character as close to the
    given height and depth as possible.  When using a font with
    multiple height versions of some characters (such as the BaKoMa
    fonts), the correct glyph will be selected, otherwise this will
    always just return a scaled version of the glyph.
    """
    def __init__(self, c, height, depth, state, always=False, factor=None):
        alternatives = state.font_output.get_sized_alternatives_for_symbol(
            state.font, c)

        state = state.copy()
        target_total = height + depth
        for fontname, sym in alternatives:
            state.font = fontname
            char = Char(sym, state)
            if char.height + char.depth >= target_total:
                break

        if factor is None:
            factor = target_total / (char.height + char.depth)
        state.fontsize *= factor
        char = Char(sym, state)

        shift = (depth - char.depth)
        Hlist.__init__(self, [char])
        self.shift_amount = shift

class AutoWidthChar(Hlist):
    """
    :class:`AutoWidthChar` will create a character as close to the
    given width as possible.  When using a font with multiple width
    versions of some characters (such as the BaKoMa fonts), the
    correct glyph will be selected, otherwise this will always just
    return a scaled version of the glyph.
    """
    def __init__(self, c, width, state, always=False, char_class=Char):
        alternatives = state.font_output.get_sized_alternatives_for_symbol(
            state.font, c)

        state = state.copy()
        for fontname, sym in alternatives:
            state.font = fontname
            char = char_class(sym, state)
            if char.width >= width:
                break

        factor = width / char.width
        state.fontsize *= factor
        char = char_class(sym, state)

        Hlist.__init__(self, [char])
        self.width = char.width

class Ship(object):
    """
    Once the boxes have been set up, this sends them to output.  Since
    boxes can be inside of boxes inside of boxes, the main work of
    :class:`Ship` is done by two mutually recursive routines,
    :meth:`hlist_out` and :meth:`vlist_out`, which traverse the
    :class:`Hlist` nodes and :class:`Vlist` nodes inside of horizontal
    and vertical boxes.  The global variables used in TeX to store
    state as it processes have become member variables here.
    """
    def __call__(self, ox, oy, box):
        self.max_push    = 0 # Deepest nesting of push commands so far
        self.cur_s       = 0
        self.cur_v       = 0.
        self.cur_h       = 0.
        self.off_h       = ox
        self.off_v       = oy + box.height
        self.hlist_out(box)

    def clamp(value):
        if value < -1000000000.:
            return -1000000000.
        if value > 1000000000.:
            return 1000000000.
        return value
    clamp = staticmethod(clamp)

    def hlist_out(self, box):
        cur_g         = 0
        cur_glue      = 0.
        glue_order    = box.glue_order
        glue_sign     = box.glue_sign
        base_line     = self.cur_v
        left_edge     = self.cur_h
        self.cur_s    += 1
        self.max_push = max(self.cur_s, self.max_push)
        clamp         = self.clamp

        for p in box.children:
            if isinstance(p, Char):
                p.render(self.cur_h + self.off_h, self.cur_v + self.off_v)
                self.cur_h += p.width
            elif isinstance(p, Kern):
                self.cur_h += p.width
            elif isinstance(p, List):
                # node623
                if len(p.children) == 0:
                    self.cur_h += p.width
                else:
                    edge = self.cur_h
                    self.cur_v = base_line + p.shift_amount
                    if isinstance(p, Hlist):
                        self.hlist_out(p)
                    else:
                        # p.vpack(box.height + box.depth, 'exactly')
                        self.vlist_out(p)
                    self.cur_h = edge + p.width
                    self.cur_v = base_line
            elif isinstance(p, Box):
                # node624
                rule_height = p.height
                rule_depth  = p.depth
                rule_width  = p.width
                if isinf(rule_height):
                    rule_height = box.height
                if isinf(rule_depth):
                    rule_depth = box.depth
                if rule_height > 0 and rule_width > 0:
                    self.cur_v = baseline + rule_depth
                    p.render(self.cur_h + self.off_h,
                             self.cur_v + self.off_v,
                             rule_width, rule_height)
                    self.cur_v = baseline
                self.cur_h += rule_width
            elif isinstance(p, Glue):
                # node625
                glue_spec = p.glue_spec
                rule_width = glue_spec.width - cur_g
                if glue_sign != 0: # normal
                    if glue_sign == 1: # stretching
                        if glue_spec.stretch_order == glue_order:
                            cur_glue += glue_spec.stretch
                            cur_g = round(clamp(float(box.glue_set) * cur_glue))
                    elif glue_spec.shrink_order == glue_order:
                        cur_glue += glue_spec.shrink
                        cur_g = round(clamp(float(box.glue_set) * cur_glue))
                rule_width += cur_g
                self.cur_h += rule_width
        self.cur_s -= 1

    def vlist_out(self, box):
        cur_g         = 0
        cur_glue      = 0.
        glue_order    = box.glue_order
        glue_sign     = box.glue_sign
        self.cur_s    += 1
        self.max_push = max(self.max_push, self.cur_s)
        left_edge     = self.cur_h
        self.cur_v    -= box.height
        top_edge      = self.cur_v
        clamp         = self.clamp

        for p in box.children:
            if isinstance(p, Kern):
                self.cur_v += p.width
            elif isinstance(p, List):
                if len(p.children) == 0:
                    self.cur_v += p.height + p.depth
                else:
                    self.cur_v += p.height
                    self.cur_h = left_edge + p.shift_amount
                    save_v = self.cur_v
                    p.width = box.width
                    if isinstance(p, Hlist):
                        self.hlist_out(p)
                    else:
                        self.vlist_out(p)
                    self.cur_v = save_v + p.depth
                    self.cur_h = left_edge
            elif isinstance(p, Box):
                rule_height = p.height
                rule_depth = p.depth
                rule_width = p.width
                if isinf(rule_width):
                    rule_width = box.width
                rule_height += rule_depth
                if rule_height > 0 and rule_depth > 0:
                    self.cur_v += rule_height
                    p.render(self.cur_h + self.off_h,
                             self.cur_v + self.off_v,
                             rule_width, rule_height)
            elif isinstance(p, Glue):
                glue_spec = p.glue_spec
                rule_height = glue_spec.width - cur_g
                if glue_sign != 0: # normal
                    if glue_sign == 1: # stretching
                        if glue_spec.stretch_order == glue_order:
                            cur_glue += glue_spec.stretch
                            cur_g = round(clamp(float(box.glue_set) * cur_glue))
                    elif glue_spec.shrink_order == glue_order: # shrinking
                        cur_glue += glue_spec.shrink
                        cur_g = round(clamp(float(box.glue_set) * cur_glue))
                rule_height += cur_g
                self.cur_v += rule_height
            elif isinstance(p, Char):
                raise RuntimeError("Internal mathtext error: Char node found in vlist")
        self.cur_s -= 1

ship = Ship()

##############################################################################
# PARSER

def Error(msg):
    """
    Helper class to raise parser errors.
    """
    def raise_error(s, loc, toks):
        raise ParseFatalException(s, loc, msg)

    empty = Empty()
    empty.setParseAction(raise_error)
    return empty

class Parser(object):
    """
    This is the pyparsing-based parser for math expressions.  It
    actually parses full strings *containing* math expressions, in
    that raw text may also appear outside of pairs of ``$``.

    The grammar is based directly on that in TeX, though it cuts a few
    corners.
    """
    _binary_operators = set(r'''
      + *
      \pm             \sqcap                   \rhd
      \mp             \sqcup                   \unlhd
      \times          \vee                     \unrhd
      \div            \wedge                   \oplus
      \ast            \setminus                \ominus
      \star           \wr                      \otimes
      \circ           \diamond                 \oslash
      \bullet         \bigtriangleup           \odot
      \cdot           \bigtriangledown         \bigcirc
      \cap            \triangleleft            \dagger
      \cup            \triangleright           \ddagger
      \uplus          \lhd                     \amalg'''.split())

    _relation_symbols = set(r'''
      = < > :
      \leq            \geq             \equiv           \models
      \prec           \succ            \sim             \perp
      \preceq         \succeq          \simeq           \mid
      \ll             \gg              \asymp           \parallel
      \subset         \supset          \approx          \bowtie
      \subseteq       \supseteq        \cong            \Join
      \sqsubset       \sqsupset        \neq             \smile
      \sqsubseteq     \sqsupseteq      \doteq           \frown
      \in             \ni              \propto
      \vdash          \dashv           \dots'''.split())

    _arrow_symbols = set(r'''
      \leftarrow              \longleftarrow           \uparrow
      \Leftarrow              \Longleftarrow           \Uparrow
      \rightarrow             \longrightarrow          \downarrow
      \Rightarrow             \Longrightarrow          \Downarrow
      \leftrightarrow         \longleftrightarrow      \updownarrow
      \Leftrightarrow         \Longleftrightarrow      \Updownarrow
      \mapsto                 \longmapsto              \nearrow
      \hookleftarrow          \hookrightarrow          \searrow
      \leftharpoonup          \rightharpoonup          \swarrow
      \leftharpoondown        \rightharpoondown        \nwarrow
      \rightleftharpoons      \leadsto'''.split())

    _spaced_symbols = _binary_operators | _relation_symbols | _arrow_symbols

    _punctuation_symbols = set(r', ; . ! \ldotp \cdotp'.split())

    _overunder_symbols = set(r'''
       \sum \prod \coprod \bigcap \bigcup \bigsqcup \bigvee
       \bigwedge \bigodot \bigotimes \bigoplus \biguplus
       '''.split())

    _overunder_functions = set(
        r"lim liminf limsup sup max min".split())

    _dropsub_symbols = set(r'''\int \oint'''.split())

    _fontnames = set("rm cal it tt sf bf default bb frak circled scr regular".split())

    _function_names = set("""
      arccos csc ker min arcsin deg lg Pr arctan det lim sec arg dim
      liminf sin cos exp limsup sinh cosh gcd ln sup cot hom log tan
      coth inf max tanh""".split())

    _ambi_delim = set(r"""
      | \| / \backslash \uparrow \downarrow \updownarrow \Uparrow
      \Downarrow \Updownarrow .""".split())

    _left_delim = set(r"( [ \{ < \lfloor \langle \lceil".split())

    _right_delim = set(r") ] \} > \rfloor \rangle \rceil".split())

    def __init__(self):
        # All forward declarations are here
        accent           = Forward()
        ambi_delim       = Forward()
        auto_delim       = Forward()
        binom            = Forward()
        bslash           = Forward()
        c_over_c         = Forward()
        customspace      = Forward()
        end_group        = Forward()
        float_literal    = Forward()
        font             = Forward()
        frac             = Forward()
        function         = Forward()
        genfrac          = Forward()
        group            = Forward()
        int_literal      = Forward()
        latexfont        = Forward()
        lbracket         = Forward()
        left_delim       = Forward()
        lbrace           = Forward()
        main             = Forward()
        math             = Forward()
        math_string      = Forward()
        non_math         = Forward()
        operatorname     = Forward()
        overline         = Forward()
        placeable        = Forward()
        rbrace           = Forward()
        rbracket         = Forward()
        required_group   = Forward()
        right_delim      = Forward()
        right_delim_safe = Forward()
        simple           = Forward()
        simple_group     = Forward()
        single_symbol    = Forward()
        space            = Forward()
        sqrt             = Forward()
        stackrel         = Forward()
        start_group      = Forward()
        subsuper         = Forward()
        subsuperop       = Forward()
        symbol           = Forward()
        symbol_name      = Forward()
        token            = Forward()
        unknown_symbol   = Forward()

        # Set names on everything -- very useful for debugging
        for key, val in locals().items():
            if key != 'self':
                val.setName(key)

        float_literal << Regex(r"[-+]?([0-9]+\.?[0-9]*|\.[0-9]+)")
        int_literal   << Regex("[-+]?[0-9]+")

        lbrace        << Literal('{').suppress()
        rbrace        << Literal('}').suppress()
        lbracket      << Literal('[').suppress()
        rbracket      << Literal(']').suppress()
        bslash        << Literal('\\')

        space         << oneOf(list(self._space_widths.keys()))
        customspace   << (Suppress(Literal(r'\hspace'))
                          - ((lbrace + float_literal + rbrace)
                            | Error(r"Expected \hspace{n}")))

        unicode_range =  "\U00000080-\U0001ffff"
        single_symbol << Regex(R"([a-zA-Z0-9 +\-*/<>=:,.;!\?&'@()\[\]|%s])|(\\[%%${}\[\]_|])" %
                               unicode_range)
        symbol_name   << (Combine(bslash + oneOf(list(tex2uni.keys()))) +
                          FollowedBy(Regex("[^A-Za-z]").leaveWhitespace() | StringEnd()))
        symbol        << (single_symbol | symbol_name).leaveWhitespace()

        c_over_c      << Suppress(bslash) + oneOf(list(self._char_over_chars.keys()))

        accent        << Group(
                             Suppress(bslash)
                           + oneOf(list(self._accent_map.keys()) + list(self._wide_accents))
                           - placeable
                         )

        function      << Suppress(bslash) + oneOf(list(self._function_names))

        start_group   << Optional(latexfont) + lbrace
        end_group     << rbrace.copy()
        simple_group  << Group(lbrace + ZeroOrMore(token) + rbrace)
        required_group<< Group(lbrace + OneOrMore(token) + rbrace)
        group         << Group(start_group + ZeroOrMore(token) + end_group)

        font          << Suppress(bslash) + oneOf(list(self._fontnames))
        latexfont     << Suppress(bslash) + oneOf(['math' + x for x in self._fontnames])

        frac          << Group(
                             Suppress(Literal(r"\frac"))
                           - ((required_group + required_group) | Error(r"Expected \frac{num}{den}"))
                         )

        stackrel      << Group(
                             Suppress(Literal(r"\stackrel"))
                           - ((required_group + required_group) | Error(r"Expected \stackrel{num}{den}"))
                         )

        binom         << Group(
                             Suppress(Literal(r"\binom"))
                           - ((required_group + required_group) | Error(r"Expected \binom{num}{den}"))
                         )

        ambi_delim    << oneOf(list(self._ambi_delim))
        left_delim    << oneOf(list(self._left_delim))
        right_delim   << oneOf(list(self._right_delim))
        right_delim_safe << oneOf(list(self._right_delim - set(['}'])) + [r'\}'])

        genfrac       << Group(
                             Suppress(Literal(r"\genfrac"))
                           - (((lbrace + Optional(ambi_delim | left_delim, default='') + rbrace)
                           +   (lbrace + Optional(ambi_delim | right_delim_safe, default='') + rbrace)
                           +   (lbrace + float_literal + rbrace)
                           +   simple_group + required_group + required_group)
                           | Error(r"Expected \genfrac{ldelim}{rdelim}{rulesize}{style}{num}{den}"))
                         )

        sqrt          << Group(
                             Suppress(Literal(r"\sqrt"))
                           - ((Optional(lbracket + int_literal + rbracket, default=None)
                              + required_group)
                           | Error("Expected \sqrt{value}"))
                         )

        overline      << Group(
                             Suppress(Literal(r"\overline"))
                           - (required_group | Error("Expected \overline{value}"))
                         )

        unknown_symbol<< Combine(bslash + Regex("[A-Za-z]*"))

        operatorname  << Group(
                             Suppress(Literal(r"\operatorname"))
                           - ((lbrace + ZeroOrMore(simple | unknown_symbol) + rbrace)
                              | Error("Expected \operatorname{value}"))
                         )

        placeable     << ( accent # Must be first
                         | symbol # Must be second
                         | c_over_c
                         | function
                         | group
                         | frac
                         | stackrel
                         | binom
                         | genfrac
                         | sqrt
                         | overline
                         | operatorname
                         )

        simple        << ( space
                         | customspace
                         | font
                         | subsuper
                         )

        subsuperop    << oneOf(["_", "^"])

        subsuper      << Group(
                             (Optional(placeable) + OneOrMore(subsuperop - placeable))
                           | placeable
                         )

        token         << ( simple
                         | auto_delim
                         | unknown_symbol # Must be last
                         )

        auto_delim    << (Suppress(Literal(r"\left"))
                          - ((left_delim | ambi_delim) | Error("Expected a delimiter"))
                          + Group(ZeroOrMore(simple | auto_delim))
                          + Suppress(Literal(r"\right"))
                          - ((right_delim | ambi_delim) | Error("Expected a delimiter"))
                         )

        math          << OneOrMore(token)

        math_string   << QuotedString('$', '\\', unquoteResults=False)

        non_math      << Regex(r"(?:(?:\\[$])|[^$])*").leaveWhitespace()

        main          << (non_math + ZeroOrMore(math_string + non_math)) + StringEnd()

        # Set actions
        for key, val in locals().items():
            if hasattr(self, key):
                val.setParseAction(getattr(self, key))

        self._expression = main
        self._math_expression = math

    def parse(self, s, fonts_object, fontsize, dpi):
        """
        Parse expression *s* using the given *fonts_object* for
        output, at the given *fontsize* and *dpi*.

        Returns the parse tree of :class:`Node` instances.
        """
        self._state_stack = [self.State(fonts_object, 'default', 'rm', fontsize, dpi)]
        self._em_width_cache = {}
        try:
            result = self._expression.parseString(s)
        except ParseBaseException as err:
            print(s)
            raise ValueError("\n".join([
                        "",
                        err.line,
                        " " * (err.column - 1) + "^",
                        str(err)]))
        self._state_stack = None
        self._em_width_cache = {}
        self._expression.resetCache()
        return result[0]

    # The state of the parser is maintained in a stack.  Upon
    # entering and leaving a group { } or math/non-math, the stack
    # is pushed and popped accordingly.  The current state always
    # exists in the top element of the stack.
    class State(object):
        """
        Stores the state of the parser.

        States are pushed and popped from a stack as necessary, and
        the "current" state is always at the top of the stack.
        """
        def __init__(self, font_output, font, font_class, fontsize, dpi):
            self.font_output = font_output
            self._font = font
            self.font_class = font_class
            self.fontsize = fontsize
            self.dpi = dpi

        def copy(self):
            return Parser.State(
                self.font_output,
                self.font,
                self.font_class,
                self.fontsize,
                self.dpi)

        def _get_font(self):
            return self._font
        def _set_font(self, name):
            if name in ('rm', 'it', 'bf'):
                self.font_class = name
            self._font = name
        font = property(_get_font, _set_font)

    def get_state(self):
        """
        Get the current :class:`State` of the parser.
        """
        return self._state_stack[-1]

    def pop_state(self):
        """
        Pop a :class:`State` off of the stack.
        """
        self._state_stack.pop()

    def push_state(self):
        """
        Push a new :class:`State` onto the stack which is just a copy
        of the current state.
        """
        self._state_stack.append(self.get_state().copy())

    def main(self, s, loc, toks):
        #~ print "finish", toks
        return [Hlist(toks)]

    def math_string(self, s, loc, toks):
        # print "math_string", toks[0][1:-1]
        return self._math_expression.parseString(toks[0][1:-1])

    def math(self, s, loc, toks):
        #~ print "math", toks
        hlist = Hlist(toks)
        self.pop_state()
        return [hlist]

    def non_math(self, s, loc, toks):
        #~ print "non_math", toks
        s = toks[0].replace(r'\$', '$')
        symbols = [Char(c, self.get_state()) for c in s]
        hlist = Hlist(symbols)
        # We're going into math now, so set font to 'it'
        self.push_state()
        self.get_state().font = rcParams['mathtext.default']
        return [hlist]

    def _make_space(self, percentage):
        # All spaces are relative to em width
        state = self.get_state()
        key = (state.font, state.fontsize, state.dpi)
        width = self._em_width_cache.get(key)
        if width is None:
            metrics = state.font_output.get_metrics(
                state.font, rcParams['mathtext.default'], 'm', state.fontsize, state.dpi)
            width = metrics.advance
            self._em_width_cache[key] = width
        return Kern(width * percentage)

    _space_widths = { r'\ '      : 0.3,
                      r'\,'      : 0.4,
                      r'\;'      : 0.8,
                      r'\quad'   : 1.6,
                      r'\qquad'  : 3.2,
                      r'\!'      : -0.4,
                      r'\/'      : 0.4 }
    def space(self, s, loc, toks):
        assert(len(toks)==1)
        num = self._space_widths[toks[0]]
        box = self._make_space(num)
        return [box]

    def customspace(self, s, loc, toks):
        return [self._make_space(float(toks[0]))]

    def symbol(self, s, loc, toks):
        # print "symbol", toks
        c = toks[0]
        if c == "'":
            c = '\prime'
        try:
            char = Char(c, self.get_state())
        except ValueError:
            raise ParseFatalException(s, loc, "Unknown symbol: %s" % c)

        if c in self._spaced_symbols:
            return [Hlist( [self._make_space(0.2),
                            char,
                            self._make_space(0.2)] ,
                           do_kern = False)]
        elif c in self._punctuation_symbols:
            return [Hlist( [char,
                            self._make_space(0.2)] ,
                           do_kern = False)]
        return [char]

    def unknown_symbol(self, s, loc, toks):
        # print "symbol", toks
        c = toks[0]
        raise ParseFatalException(s, loc, "Unknown symbol: %s" % c)

    _char_over_chars = {
        # The first 2 entires in the tuple are (font, char, sizescale) for
        # the two symbols under and over.  The third element is the space
        # (in multiples of underline height)
        r'AA' : (  ('rm', 'A', 1.0), (None, '\circ', 0.5), 0.0),
    }

    def c_over_c(self, s, loc, toks):
        sym = toks[0]
        state = self.get_state()
        thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)

        under_desc, over_desc, space = \
            self._char_over_chars.get(sym, (None, None, 0.0))
        if under_desc is None:
            raise ParseFatalException("Error parsing symbol")

        over_state = state.copy()
        if over_desc[0] is not None:
            over_state.font = over_desc[0]
        over_state.fontsize *= over_desc[2]
        over = Accent(over_desc[1], over_state)

        under_state = state.copy()
        if under_desc[0] is not None:
            under_state.font = under_desc[0]
        under_state.fontsize *= under_desc[2]
        under = Char(under_desc[1], under_state)

        width = max(over.width, under.width)

        over_centered = HCentered([over])
        over_centered.hpack(width, 'exactly')

        under_centered = HCentered([under])
        under_centered.hpack(width, 'exactly')

        return Vlist([
                over_centered,
                Vbox(0., thickness * space),
                under_centered
                ])

    _accent_map = {
        r'hat'   : r'\circumflexaccent',
        r'breve' : r'\combiningbreve',
        r'bar'   : r'\combiningoverline',
        r'grave' : r'\combininggraveaccent',
        r'acute' : r'\combiningacuteaccent',
        r'ddot'  : r'\combiningdiaeresis',
        r'tilde' : r'\combiningtilde',
        r'dot'   : r'\combiningdotabove',
        r'vec'   : r'\combiningrightarrowabove',
        r'"'     : r'\combiningdiaeresis',
        r"`"     : r'\combininggraveaccent',
        r"'"     : r'\combiningacuteaccent',
        r'~'     : r'\combiningtilde',
        r'.'     : r'\combiningdotabove',
        r'^'     : r'\circumflexaccent',
        r'overrightarrow' : r'\rightarrow',
        r'overleftarrow'  : r'\leftarrow'
        }

    _wide_accents = set(r"widehat widetilde widebar".split())

    def accent(self, s, loc, toks):
        assert(len(toks)==1)
        state = self.get_state()
        thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)
        if len(toks[0]) != 2:
            raise ParseFatalException("Error parsing accent")
        accent, sym = toks[0]
        if accent in self._wide_accents:
            accent = AutoWidthChar(
                '\\' + accent, sym.width, state, char_class=Accent)
        else:
            accent = Accent(self._accent_map[accent], state)
        centered = HCentered([accent])
        centered.hpack(sym.width, 'exactly')
        return Vlist([
                centered,
                Vbox(0., thickness * 2.0),
                Hlist([sym])
                ])

    def function(self, s, loc, toks):
        #~ print "function", toks
        self.push_state()
        state = self.get_state()
        state.font = 'rm'
        hlist = Hlist([Char(c, state) for c in toks[0]])
        self.pop_state()
        hlist.function_name = toks[0]
        return hlist

    def operatorname(self, s, loc, toks):
        self.push_state()
        state = self.get_state()
        state.font = 'rm'
        # Change the font of Chars, but leave Kerns alone
        for c in toks[0]:
            if isinstance(c, Char):
                c.font = 'rm'
                c._update_metrics()
        self.pop_state()
        return Hlist(toks[0])

    def start_group(self, s, loc, toks):
        self.push_state()
        # Deal with LaTeX-style font tokens
        if len(toks):
            self.get_state().font = toks[0][4:]
        return []

    def group(self, s, loc, toks):
        grp = Hlist(toks[0])
        return [grp]
    required_group = simple_group = group

    def end_group(self, s, loc, toks):
        self.pop_state()
        return []

    def font(self, s, loc, toks):
        assert(len(toks)==1)
        name = toks[0]
        self.get_state().font = name
        return []

    def is_overunder(self, nucleus):
        if isinstance(nucleus, Char):
            return nucleus.c in self._overunder_symbols
        elif isinstance(nucleus, Hlist) and hasattr(nucleus, 'function_name'):
            return nucleus.function_name in self._overunder_functions
        return False

    def is_dropsub(self, nucleus):
        if isinstance(nucleus, Char):
            return nucleus.c in self._dropsub_symbols
        return False

    def is_slanted(self, nucleus):
        if isinstance(nucleus, Char):
            return nucleus.is_slanted()
        return False

    def subsuper(self, s, loc, toks):
        assert(len(toks)==1)
        # print 'subsuper', toks

        nucleus = None
        sub = None
        super = None

        if len(toks[0]) == 1:
            return toks[0].asList()
        elif len(toks[0]) == 2:
            op, next = toks[0]
            nucleus = Hbox(0.0)
            if op == '_':
                sub = next
            else:
                super = next
        elif len(toks[0]) == 3:
            nucleus, op, next = toks[0]
            if op == '_':
                sub = next
            else:
                super = next
        elif len(toks[0]) == 5:
            nucleus, op1, next1, op2, next2 = toks[0]
            if op1 == op2:
                if op1 == '_':
                    raise ParseFatalException("Double subscript")
                else:
                    raise ParseFatalException("Double superscript")
            if op1 == '_':
                sub = next1
                super = next2
            else:
                super = next1
                sub = next2
        else:
            raise ParseFatalException(
                "Subscript/superscript sequence is too long. "
                "Use braces { } to remove ambiguity.")

        state = self.get_state()
        rule_thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)
        xHeight = state.font_output.get_xheight(
            state.font, state.fontsize, state.dpi)

        # Handle over/under symbols, such as sum or integral
        if self.is_overunder(nucleus):
            vlist = []
            shift = 0.
            width = nucleus.width
            if super is not None:
                super.shrink()
                width = max(width, super.width)
            if sub is not None:
                sub.shrink()
                width = max(width, sub.width)

            if super is not None:
                hlist = HCentered([super])
                hlist.hpack(width, 'exactly')
                vlist.extend([hlist, Kern(rule_thickness * 3.0)])
            hlist = HCentered([nucleus])
            hlist.hpack(width, 'exactly')
            vlist.append(hlist)
            if sub is not None:
                hlist = HCentered([sub])
                hlist.hpack(width, 'exactly')
                vlist.extend([Kern(rule_thickness * 3.0), hlist])
                shift = hlist.height
            vlist = Vlist(vlist)
            vlist.shift_amount = shift + nucleus.depth
            result = Hlist([vlist])
            return [result]

        # Handle regular sub/superscripts
        shift_up = nucleus.height - SUBDROP * xHeight
        if self.is_dropsub(nucleus):
            shift_down = nucleus.depth + SUBDROP * xHeight
        else:
            shift_down = SUBDROP * xHeight
        if super is None:
            # node757
            sub.shrink()
            x = Hlist([sub])
            # x.width += SCRIPT_SPACE * xHeight
            shift_down = max(shift_down, SUB1)
            clr = x.height - (abs(xHeight * 4.0) / 5.0)
            shift_down = max(shift_down, clr)
            x.shift_amount = shift_down
        else:
            super.shrink()
            x = Hlist([super, Kern(SCRIPT_SPACE * xHeight)])
            # x.width += SCRIPT_SPACE * xHeight
            clr = SUP1 * xHeight
            shift_up = max(shift_up, clr)
            clr = x.depth + (abs(xHeight) / 4.0)
            shift_up = max(shift_up, clr)
            if sub is None:
                x.shift_amount = -shift_up
            else: # Both sub and superscript
                sub.shrink()
                y = Hlist([sub])
                # y.width += SCRIPT_SPACE * xHeight
                shift_down = max(shift_down, SUB1 * xHeight)
                clr = (2.0 * rule_thickness -
                       ((shift_up - x.depth) - (y.height - shift_down)))
                if clr > 0.:
                    shift_up += clr
                    shift_down += clr
                if self.is_slanted(nucleus):
                    x.shift_amount = DELTA * (shift_up + shift_down)
                x = Vlist([x,
                           Kern((shift_up - x.depth) - (y.height - shift_down)),
                           y])
                x.shift_amount = shift_down

        result = Hlist([nucleus, x])
        return [result]

    def _genfrac(self, ldelim, rdelim, rule, style, num, den):
        state = self.get_state()
        thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)

        rule = float(rule)
        num.shrink()
        den.shrink()
        cnum = HCentered([num])
        cden = HCentered([den])
        width = max(num.width, den.width)
        cnum.hpack(width, 'exactly')
        cden.hpack(width, 'exactly')
        vlist = Vlist([cnum,                      # numerator
                       Vbox(0, thickness * 2.0),  # space
                       Hrule(state, rule),        # rule
                       Vbox(0, thickness * 2.0),  # space
                       cden                       # denominator
                       ])

        # Shift so the fraction line sits in the middle of the
        # equals sign
        metrics = state.font_output.get_metrics(
            state.font, rcParams['mathtext.default'],
            '=', state.fontsize, state.dpi)
        shift = (cden.height -
                 ((metrics.ymax + metrics.ymin) / 2 -
                  thickness * 3.0))
        vlist.shift_amount = shift

        result = [Hlist([vlist, Hbox(thickness * 2.)])]
        if ldelim or rdelim:
            if ldelim == '':
                ldelim = '.'
            if rdelim == '':
                rdelim = '.'
            return self._auto_sized_delimiter(ldelim, result, rdelim)
        return result

    def genfrac(self, s, loc, toks):
        assert(len(toks)==1)
        assert(len(toks[0])==6)

        return self._genfrac(*tuple(toks[0]))

    def frac(self, s, loc, toks):
        assert(len(toks)==1)
        assert(len(toks[0])==2)
        state = self.get_state()

        thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)
        num, den = toks[0]

        return self._genfrac('', '', thickness, '', num, den)

    def stackrel(self, s, loc, toks):
        assert(len(toks)==1)
        assert(len(toks[0])==2)
        num, den = toks[0]

        return self._genfrac('', '', 0.0, '', num, den)

    def binom(self, s, loc, toks):
        assert(len(toks)==1)
        assert(len(toks[0])==2)
        num, den = toks[0]

        return self._genfrac('(', ')', 0.0, '', num, den)

    def sqrt(self, s, loc, toks):
        #~ print "sqrt", toks
        root, body = toks[0]
        state = self.get_state()
        thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)

        # Determine the height of the body, and add a little extra to
        # the height so it doesn't seem cramped
        height = body.height - body.shift_amount + thickness * 5.0
        depth = body.depth + body.shift_amount
        check = AutoHeightChar(r'\__sqrt__', height, depth, state, always=True)
        height = check.height - check.shift_amount
        depth = check.depth + check.shift_amount

        # Put a little extra space to the left and right of the body
        padded_body = Hlist([Hbox(thickness * 2.0),
                             body,
                             Hbox(thickness * 2.0)])
        rightside = Vlist([Hrule(state),
                           Fill(),
                           padded_body])
        # Stretch the glue between the hrule and the body
        rightside.vpack(height + (state.fontsize * state.dpi) / (100.0 * 12.0),
                        'exactly', depth)

        # Add the root and shift it upward so it is above the tick.
        # The value of 0.6 is a hard-coded hack ;)
        if root is None:
            root = Box(check.width * 0.5, 0., 0.)
        else:
            root = Hlist([Char(x, state) for x in root])
            root.shrink()
            root.shrink()

        root_vlist = Vlist([Hlist([root])])
        root_vlist.shift_amount = -height * 0.6

        hlist = Hlist([root_vlist,               # Root
                       # Negative kerning to put root over tick
                       Kern(-check.width * 0.5),
                       check,                    # Check
                       rightside])               # Body
        return [hlist]

    def overline(self, s, loc, toks):
        assert(len(toks)==1)
        assert(len(toks[0])==1)

        body = toks[0][0]

        state = self.get_state()
        thickness = state.font_output.get_underline_thickness(
            state.font, state.fontsize, state.dpi)

        height = body.height - body.shift_amount + thickness * 3.0
        depth = body.depth + body.shift_amount

        # Place overline above body
        rightside = Vlist([Hrule(state),
                           Fill(),
                           Hlist([body])])

        # Stretch the glue between the hrule and the body
        rightside.vpack(height + (state.fontsize * state.dpi) / (100.0 * 12.0),
                        'exactly', depth)

        hlist = Hlist([rightside])
        return [hlist]

    def _auto_sized_delimiter(self, front, middle, back):
        state = self.get_state()
        if len(middle):
            height = max([x.height for x in middle])
            depth = max([x.depth for x in middle])
            factor = None
        else:
            height = 0
            depth = 0
            factor = 1.0
        parts = []
        # \left. and \right. aren't supposed to produce any symbols
        if front != '.':
            parts.append(AutoHeightChar(front, height, depth, state, factor=factor))
        parts.extend(middle)
        if back != '.':
            parts.append(AutoHeightChar(back, height, depth, state, factor=factor))
        hlist = Hlist(parts)
        return hlist

    def auto_delim(self, s, loc, toks):
        #~ print "auto_delim", toks
        front, middle, back = toks

        return self._auto_sized_delimiter(front, middle.asList(), back)

###
########NEW FILE########
__FILENAME__ = number
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.

"""
Functions for formatting numbers:

* :func:`format_number`: Format a number according to a given style.

"""

from .paragraph import ParagraphBase, ParagraphStyle
from .style import Style
from .text import FixedWidthSpace


__all__ = ['NumberStyle', 'NumberedParagraph',
           'NUMBER', 'CHARACTER_LC', 'CHARACTER_UC', 'ROMAN_LC', 'ROMAN_UC',
           'SYMBOL', 'format_number']


NUMBER = 'number'
CHARACTER_LC = 'character'
CHARACTER_UC = 'CHARACTER'
ROMAN_LC = 'roman'
ROMAN_UC = 'ROMAN'
SYMBOL = 'symbol'


def format_number(number, format):
    """Format `number` according the given `format`:

    * :const:`NUMBER`: plain arabic number (1, 2, 3, ...)
    * :const:`CHARACTER_LC`: lowercase letters (a, b, c, ..., aa, ab, ...)
    * :const:`CHARACTER_UC`: uppercase letters (A, B, C, ..., AA, AB, ...)
    * :const:`ROMAN_LC`: lowercase Roman (i, ii, iii, iv, v, vi, ...)
    * :const:`ROMAN_UC`: uppercase Roman (I, II, III, IV, V, VI, ...)

    """
    if format == NUMBER:
        return str(number)
    elif format == CHARACTER_LC:
        string = ''
        while number > 0:
            number, ordinal = divmod(number, 26)
            if ordinal == 0:
                ordinal = 26
                number -= 1
            string = chr(ord('a') - 1 + ordinal) + string
        return string
    elif format == CHARACTER_UC:
        return format_number(number, CHARACTER_LC).upper()
    elif format == ROMAN_LC:
        return romanize(number).lower()
    elif format == ROMAN_UC:
        return romanize(number)
    elif format == SYMBOL:
        return symbolize(number)
    else:
        raise ValueError("Unknown number format '{}'".format(format))


# romanize by Kay Schluehr - from http://billmill.org/python_roman.html

NUMERALS = (('M', 1000), ('CM', 900), ('D', 500), ('CD', 400),
            ('C', 100), ('XC', 90), ('L', 50), ('XL', 40),
            ('X', 10), ('IX', 9), ('V', 5), ('IV', 4), ('I', 1))

def romanize(number):
    """Convert `number` to a Roman numeral."""
    roman = []
    for numeral, value in NUMERALS:
        times, number = divmod(number, value)
        roman.append(times * numeral)
    return ''.join(roman)


SYMBOLS = ('*', '†', '‡', '§', '‖', '¶', '#')

def symbolize(number):
    """Convert `number` to a foot/endnote symbol."""
    repeat, index = divmod(number - 1, len(SYMBOLS))
    return SYMBOLS[index] * (1 + repeat)


class NumberStyle(Style):
    attributes = {'number_format': NUMBER,
                  'number_suffix': '.'}


class NumberedParagraphStyle(ParagraphStyle, NumberStyle):
    pass


class NumberedParagraph(ParagraphBase):
    style_class = NumberedParagraphStyle

    def __init__(self, content, style=None, parent=None):
        super().__init__(style=style, parent=parent)
        self.content = content

    def number(self, document):
        number_format = self.get_style('number_format', document)
        if not number_format:
            return ''
        suffix = self.get_style('number_suffix', document)
        formatted_number = DirectReference(self.section, REFERENCE)
        return formatted_number + suffix + FixedWidthSpace()

    def text(self, document):
        raise NotImplementedError


from .reference import DirectReference, REFERENCE

########NEW FILE########
__FILENAME__ = paper
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.

"""
The :class:`Paper` class and a number of predefined paper sizes:

* International: :const:`A0` down to :const:`A10`
* North America: :const:`LETTER`, :const:`LEGAL`, :const:`JUNIOR_LEGAL`,
                 :const:`LEDGER` and :const:`TABLOID`
"""


from .dimension import INCH, MM


__all__ = ['Paper',
           'A0', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9', 'A10',
           'LETTER', 'LEGAL', 'JUNIOR_LEGAL', 'LEDGER', 'TABLOID']


class Paper(object):
    """Defines a paper size."""

    def __init__(self, width, height):
        """Initialize paper with size `width` and `height`."""
        self.width = width
        self.height = height


# International (DIN 476 / ISO 216)

A0 = Paper(841*MM, 1189*MM)
A1 = Paper(594*MM, 841*MM)
A2 = Paper(420*MM, 594*MM)
A3 = Paper(297*MM, 420*MM)
A4 = Paper(210*MM, 297*MM)
A5 = Paper(148*MM, 210*MM)
A6 = Paper(105*MM, 148*MM)
A7 = Paper(74*MM, 105*MM)
A8 = Paper(52*MM, 74*MM)
A9 = Paper(37*MM, 52*MM)
A10 = Paper(26*MM, 37*MM)


# North America

LETTER = Paper(8.5*INCH, 11*INCH)
LEGAL = Paper(8.5*INCH, 14*INCH)
JUNIOR_LEGAL = Paper(8*INCH, 5*INCH)
LEDGER = Paper(17*INCH, 11*INCH)
TABLOID = Paper(11*INCH, 17*INCH)

########NEW FILE########
__FILENAME__ = paragraph
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.

"""
Classes for representing paragraphs and typesetting them:

* :class:`Paragraph`: A paragraph of mixed-styled text.
* :class:`ParagraphStyle`: Style class specifying paragraph formatting.
* :class:`TabStop`: Horizontal position for aligning text of successive lines.

The line spacing option in a :class:`ParagraphStyle` can be any of:

* :class:`ProportionalSpacing`: Line spacing proportional to the line height.
* :class:`FixedSpacing`: Fixed line spacing, with optional minimum spacing.
* :class:`Leading`: Line spacing determined by the space in between two lines.
* :const:`DEFAULT`: The default line spacing as specified by the font.
* :const:`STANDARD`: Line spacing equal to 120% of the line height.
* :const:`SINGLE`: Line spacing equal to the line height (no leading).
* :const:`DOUBLE`: Line spacing of double the line height.

Horizontal justification of lines can be one of:

* :const:`LEFT`
* :const:`RIGHT`
* :const:`CENTER`
* :const:`BOTH`

"""

import os

from copy import copy
from functools import lru_cache, partial
from itertools import tee

from . import DATA_PATH
from .dimension import DimensionBase, PT
from .flowable import Flowable, FlowableStyle, FlowableState
from .font.style import SMALL_CAPITAL
from .hyphenator import Hyphenator
from .layout import EndOfContainer
from .text import TextStyle, MixedStyledText
from .util import consumer


__all__ = ['Paragraph', 'ParagraphStyle', 'TabStop',
           'ProportionalSpacing', 'FixedSpacing', 'Leading',
           'DEFAULT', 'STANDARD', 'SINGLE', 'DOUBLE',
           'LEFT', 'RIGHT', 'CENTER', 'BOTH']


# Text justification

LEFT = 'left'
RIGHT = 'right'
CENTER = 'center'
BOTH = 'justify'


# Line spacing

class LineSpacing(object):
    """Base class for line spacing types. Line spacing is defined as the
    distance between the baselines of two consecutive lines."""

    def advance(self, line, last_descender, document):
        """Return the distance between the descender of the previous line and
        the baseline of the current line."""
        raise NotImplementedError


class DefaultSpacing(LineSpacing):
    """The default line spacing as specified by the font."""

    def advance(self, line, last_descender, document):
        max_line_gap = max(float(glyph_span.span.line_gap(document))
                           for glyph_span in line)
        ascender = max(float(glyph_span.span.ascender(document))
                       for glyph_span in line)
        return ascender + max_line_gap


DEFAULT = DefaultSpacing()
"""The default line spacing as specified by the font."""


class ProportionalSpacing(LineSpacing):
    """Line spacing proportional to the line height."""

    def __init__(self, factor):
        """`factor` specifies the amount by which the line height is multiplied
        to obtain the line spacing."""
        self.factor = factor

    def advance(self, line, last_descender, document):
        max_font_size = max(float(glyph_span.span.height(document))
                            for glyph_span in line)
        return self.factor * max_font_size + last_descender


STANDARD = ProportionalSpacing(1.2)
"""Line spacing of 1.2 times the line height."""


SINGLE = ProportionalSpacing(1.0)
"""Line spacing equal to the line height (no leading)."""


DOUBLE = ProportionalSpacing(2.0)
"""Line spacing of double the line height."""


class FixedSpacing(LineSpacing):
    """Fixed line spacing, with optional minimum spacing."""

    def __init__(self, pitch, minimum=SINGLE):
        """`pitch` specifies the distance between the baseline of two
        consecutive lines of text.
        Optionally, `minimum` specifies the minimum :class:`LineSpacing` to use,
        which can prevent lines with large fonts from overlapping. If no minimum
        is required, set to `None`."""
        self.pitch = float(pitch)
        self.minimum = minimum

    def advance(self, line, last_descender, document):
        advance = self.pitch + last_descender
        if self.minimum is not None:
            minimum = self.minimum.advance(line, last_descender, document)
            return max(advance, minimum)
        else:
            return advance


class Leading(LineSpacing):
    """Line spacing determined by the space in between two lines."""

    def __init__(self, leading):
        """`leading` specifies the space between the bottom of a line and the
        top of the following line."""
        self.leading = float(leading)

    def advance(self, line, last_descender):
        ascender = max(float(item.ascender) for item in line)
        return ascender + self.leading


class TabStop(object):
    """Horizontal position for aligning text of successive lines."""

    def __init__(self, position, align=LEFT, fill=None):
        """`position` can be an absolute position (:class:`Dimension`) or can
        be relative to the line width (:class:`float`, between 0 and 1).
        The alingment of text with respect to the tab stop is determined by
        `align`, which can be :const:`LEFT`, :const:`RIGHT` or :const:`CENTER`.
        Optionally, `fill` specifies a string pattern to fill the empty tab
        space with."""
        self._position = position
        self.align = align
        self.fill = fill

    def get_position(self, line_width):
        """Return the absolute position of this tab stop."""
        if isinstance(self._position, DimensionBase):
            return float(self._position)
        else:
            return line_width * self._position


# TODO: look at Word/OpenOffice for more options
class ParagraphStyle(TextStyle, FlowableStyle):
    """The :class:`Style` for :class:`Paragraph` objects. It has the following
    attributes:

    * `indent_first`: Indentation of the first line of text (class:`Dimension`).
    * `line_spacing`: Spacing between the baselines of two successive lines of
                      text (:class:`LineSpacing`).
    * `justify`: Alignment of the text to the margins (:const:`LEFT`,
                 :const:`RIGHT`, :const:`CENTER` or :const:`BOTH`).
    * `tab_stops`: The tab stops for this paragraph (list of :class:`TabStop`).
    """

    attributes = {'indent_first': 0*PT,
                  'line_spacing': DEFAULT,
                  'justify': BOTH,
                  'tab_stops': []}

    def __init__(self, base=None, **attributes):
        super().__init__(base=base, **attributes)


class ParagraphState(FlowableState):
    def __init__(self, spans, first_line=True, nested_flowable_state=None,
                 _current_span=None, _items=None, _current_item=None):
        self.spans = spans
        self.current_span = _current_span or None
        self.items = _items or iter([])
        self.current_item = _current_item or None
        self.first_line = first_line
        self.nested_flowable_state = nested_flowable_state

    def __copy__(self):
        copy_spans, self.spans = tee(self.spans)
        copy_items, self.items = tee(self.items)
        copy_nested_flowable_state = copy(self.nested_flowable_state)
        return self.__class__(copy_spans, self.first_line,
                              copy_nested_flowable_state,
                              _current_span=self.current_span,
                              _items=copy_items,
                              _current_item=self.current_item)

    def next_item(self, container):
        if self.current_item:
            self.current_item, current_item = None, self.current_item
            return self.current_span, current_item
        try:
            return self.current_span, next(self.items)
        except StopIteration:
            self.current_span = next(self.spans)
            self.items = self.current_span.split(container)
            return self.next_item(container)

    def prepend_item(self, item):
        self.current_item = item


class ParagraphBase(Flowable):
    """A paragraph of mixed-styled text that can be flowed into a
    :class:`Container`."""

    style_class = ParagraphStyle

    def render(self, container, descender, state=None):
        """Typeset the paragraph onto `container`, starting below the current
        cursor position of the container. `descender` is the descender height of
        the preceeding line or `None`.
        When the end of the container is reached, the rendering state is
        preserved to continue setting the rest of the paragraph when this method
        is called with a new container."""
        document = container.document
        indent_first = 0 if state else float(self.get_style('indent_first',
                                                            document))
        line_width = float(container.width)
        line_spacing = self.get_style('line_spacing', document)
        justification = self.get_style('justify', document)
        tab_stops = self.get_style('tab_stops', document)

        # `saved_state` is updated after successfully rendering each line, so
        # that when `container` overflows on rendering a line, the words in that
        # line are yielded again on the next typeset() call.
        state = state or ParagraphState(self.text(document).spans())
        saved_state = copy(state)
        max_line_width = 0

        def typeset_line(line, last_line=False, force=False):
            """Typeset `line` and, if no exception is raised, update the
            paragraph's internal rendering state."""
            nonlocal span, state, saved_state, max_line_width, descender
            try:
                max_line_width = max(max_line_width, line._cursor)
                descender = line.typeset(container, justification, line_spacing,
                                         descender, last_line, force)
                saved_state = copy(state)
                return Line(tab_stops, line_width, container)
            except EndOfContainer:
                raise EndOfContainer(saved_state)

        line = Line(tab_stops, line_width, container, indent_first)
        last_span = None
        while True:
            try:
                span, word = state.next_item(container)  # raises StopIteration
                if span is not last_span:
                    line_span_send = line.new_span(span, document).send
                    hyphenate = create_hyphenate(span, document)
                    last_span = span

                if word == '\n':
                    line = typeset_line(line, last_line=True, force=True)
                    line_span_send = line.new_span(span, document).send
                elif not line_span_send(word):
                    for first, second in hyphenate(word):
                        if line_span_send(first):
                            state.prepend_item(second)
                            break
                    else:
                        state.prepend_item(word)
                    line = typeset_line(line)
                    line_span_send = line.new_span(span, document).send
            except StopIteration:
                if line:
                    typeset_line(line, last_line=True)
                break

        return max_line_width, descender


class Paragraph(ParagraphBase, MixedStyledText):
    def __init__(self, text_or_items, style=None, parent=None):
        """See :class:`MixedStyledText`. As a paragraph typically doesn't have
        a parent, `style` should be specified."""
        MixedStyledText.__init__(self, text_or_items, style=style, parent=parent)

    def text(self, document):
        return self


class HyphenatorStore(dict):
    def __missing__(self, key):
        hyphen_lang, hyphen_chars = key
        dic_path = dic_file = 'hyph_{}.dic'.format(hyphen_lang)
        if not os.path.exists(dic_path):
            dic_path = os.path.join(os.path.join(DATA_PATH, 'hyphen'), dic_file)
            if not os.path.exists(dic_path):
                raise IOError("Hyphenation dictionary '{}' neither found in "
                              "current directory, nor in the data directory"
                              .format(dic_file))
        self[key] = hyphenator = Hyphenator(dic_path, hyphen_chars, hyphen_chars)
        return hyphenator


HYPHENATORS = HyphenatorStore()


def create_hyphenate(span, document):
    if not span.get_style('hyphenate', document):
        def dont_hyphenate(word):
            return
            yield
        return dont_hyphenate

    hyphenator = HYPHENATORS[span.get_style('hyphen_lang', document),
                             span.get_style('hyphen_chars', document)]
    def hyphenate(word):
        """Generator yielding possible options for splitting this single-styled
        text (assuming it is a word) across two lines. Items yielded are tuples
        containing the first (with trailing hyphen) and second part of the split
        word.

        In the first returned option, the word is split at the right-most
        possible break point. In subsequent items, the break point advances to
        the front of the word.
        If hyphenation is not possible or simply not enabled, a single tuple is
        yielded of which the first element is the word itself, and the second
        element is `None`."""
        for first, second in hyphenator.iterate(word):
            yield first + '-', second
    return hyphenate


@lru_cache()
def create_to_glyphs(font, scale, variant, kerning, ligatures):
    get_glyph = partial(font.get_glyph, variant=variant)
    # TODO: handle ligatures at span borders
    def word_to_glyphs(word):
        glyphs = [get_glyph(char) for char in word]
        if ligatures:
            glyphs = form_ligatures(glyphs, font.get_ligature)
        if kerning:
            glyphs_kern = kern(glyphs, font.get_kerning)
        else:
            glyphs_kern = [(glyph, 0.0) for glyph in glyphs]
        return [(glyph, scale * (glyph.width + kern_adjust))
                for glyph, kern_adjust in glyphs_kern]

    return word_to_glyphs


def form_ligatures(glyphs, get_ligature):
    glyphs = iter(glyphs)
    result = []
    prev_glyph = next(glyphs)
    for glyph in glyphs:
        ligature_glyph = get_ligature(prev_glyph, glyph)
        if ligature_glyph:
            prev_glyph = ligature_glyph
        else:
            result.append(prev_glyph)
            prev_glyph = glyph
    result.append(prev_glyph)
    return result


def kern(glyphs, get_kerning):
    glyphs = iter(glyphs)
    result = []
    prev_glyph = next(glyphs)
    for glyph in glyphs:
        result.append((prev_glyph, get_kerning(prev_glyph, glyph)))
        prev_glyph = glyph
    result.append((prev_glyph, 0.0))
    return result


class GlyphsSpan(list):
    def __init__(self, span, word_to_glyphs):
        super().__init__()
        self.span = span
        self.filled_tabs = {}
        self.word_to_glyphs = word_to_glyphs
        self.number_of_spaces = 0
        self.space_glyph_and_width = list(word_to_glyphs(' ')[0])

    def append_space(self):
        self.number_of_spaces += 1
        self.append(self.space_glyph_and_width)

    def _fill_tabs(self):
        for index, glyph_and_width in enumerate(super().__iter__()):
            if index in self.filled_tabs:
                fill_string = self.filled_tabs[index]
                tab_width = glyph_and_width[1]
                fill_glyphs = self.word_to_glyphs(fill_string)
                fill_string_width = sum(width for glyph, width in fill_glyphs)
                number, rest = divmod(tab_width, fill_string_width)
                yield glyph_and_width[0], rest
                for i in range(int(number)):
                    for fill_glyph_and_width in fill_glyphs:
                        yield fill_glyph_and_width
            else:
                yield glyph_and_width

    def __iter__(self):
        if self.filled_tabs:
            return self._fill_tabs()
        else:
            return super().__iter__()


class Line(list):
    """Helper class for building and typesetting a single line of text within
    a :class:`Paragraph`."""

    def __init__(self, tab_stops, width, container, indent=0):
        """`tab_stops` is a list of tab stops, as given in the paragraph style.
        `width` is the available line width.
        `indent` specifies the left indent width.
        `container` passes the :class:`Container` that wil hold this line."""
        super().__init__()
        self.tab_stops = tab_stops
        self.width = width
        self.indent = indent
        self.container = container
        self._cursor = indent
        self._has_tab = False
        self._has_filled_tab = False
        self._current_tab = None
        self._current_tab_stop = None

    @consumer
    def new_span(self, span, document):
        font = span.font(document)
        scale = span.height(document) / font.units_per_em
        variant = (SMALL_CAPITAL if span.get_style('small_caps', document) else None)
        word_to_glyphs = create_to_glyphs(font, scale, variant,
                                          span.get_style('kerning', document),
                                          span.get_style('ligatures', document))
        glyphs_span = GlyphsSpan(span, word_to_glyphs)
        space_glyph, space_width = glyphs_span.space_glyph_and_width
        super().append(glyphs_span)

        success = True
        while True:
            word = (yield success)
            success = True
            if word == ' ':
                self._cursor += space_width
                glyphs_span.append_space()
            elif word == '\t':
                if not self.tab_stops:
                    span.warn('No tab stops defined for this  paragraph style.',
                              self.container)
                    self._cursor += space_width
                    glyphs_span.append_space()
                    continue
                self._has_tab = True
                for tab_stop in self.tab_stops:
                    tab_position = tab_stop.get_position(self.width)
                    if self._cursor < tab_position:
                        tab_width = tab_position - self._cursor
                        tab_glyph_and_width = [glyphs_span.space_glyph_and_width[0],
                                               tab_width]
                        if tab_stop.fill:
                            self._has_filled_tab = True
                            glyphs_span.filled_tabs[len(glyphs_span)] = tab_stop.fill
                        glyphs_span.append(tab_glyph_and_width)
                        self._cursor += tab_width
                        self._current_tab_stop = tab_stop
                        if tab_stop.align in (RIGHT, CENTER):
                            self._current_tab = tab_glyph_and_width
                            self._current_tab_stop = tab_stop
                        else:
                            self._current_tab = None
                            self._current_tab_stop = None
                        break
                else:
                    span.warn('Tab did not fall into any of the tab stops.',
                              self.container)
            else:
                glyphs_and_widths = word_to_glyphs(word)
                width = sum(width for glyph, width in glyphs_and_widths)
                if self._current_tab:
                    current_tab = self._current_tab
                    tab_width = current_tab[1]
                    factor = 2 if self._current_tab_stop.align == CENTER else 1
                    item_width = width / factor
                    if item_width < tab_width:
                        current_tab[1] -= item_width
                    else:
                        span.warn('Tab space exceeded.', self.container)
                        current_tab[1] = 0
                        self._current_tab = None
                    self._cursor -= tab_width
                if self._cursor + width > self.width:
                    if not self[0]:
                        span.warn('item too long to fit on line',
                                  self.container)
                    else:
                        success = False
                        continue
                self._cursor += width
                glyphs_span += glyphs_and_widths

    def typeset(self, container, justification, line_spacing, last_descender,
                last_line=False, force=False):
        """Typeset the line in `container` below its current cursor position.
        Advances the container's cursor to below the descender of this line.

        `justification` and `line_spacing` are passed on from the paragraph
        style. `last_descender` is the previous line's descender, used in the
        vertical positioning of this line. Finally, `last_line` specifies
        whether this is the last line of the paragraph.

        Returns the line's descender size."""
        document = container.document

        # remove empty spans at the end of the line
        while len(self) > 1 and len(self[-1]) == 0:
            self.pop()

        # abort if the line is empty
        if not self or (not force and len(self) == 1 and len(self[-1]) == 0):
            return last_descender

        # drop space at the end of the line
        last_span = self[-1]
        if last_span and last_span[-1] == last_span.space_glyph_and_width:
            last_span.pop()
            last_span.number_of_spaces -= 1
            self._cursor -= last_span.space_glyph_and_width[1]

        descender = min(glyph_span.span.descender(document)
                        for glyph_span in self)
        if last_descender is None:
            advance = max(glyph_span.span.ascender(document)
                          for glyph_span in self)
        else:
            advance = line_spacing.advance(self, last_descender, document)
        container.advance(advance)
        if - descender > container.remaining_height:
            raise EndOfContainer

        # horizontal displacement
        left = self.indent

        if self._has_tab or justification == BOTH and last_line:
            justification = LEFT
        extra_space = self.width - self._cursor
        if justification == BOTH:
            # TODO: padding added to spaces should be prop. to font size
            nr_spaces = sum(glyph_span.number_of_spaces for glyph_span in self)
            if nr_spaces > 0:
                add_to_spaces = extra_space / nr_spaces
                for glyph_span in self:
                    glyph_span.space_glyph_and_width[1] += add_to_spaces
        elif justification == CENTER:
            left += extra_space / 2.0
        elif justification == RIGHT:
            left += extra_space

        for glyph_span in self:
            left += container.canvas.show_glyphs(left, container.cursor,
                                                 glyph_span, document)
        container.advance(- descender)
        return descender

########NEW FILE########
__FILENAME__ = pyparsing_py3
# module pyparsing.py
#
# Copyright (c) 2003-2010  Paul T. McGuire
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#from __future__ import generators

__doc__ = \
"""
pyparsing module - Classes and methods to define and execute parsing grammars

The pyparsing module is an alternative approach to creating and executing simple grammars,
vs. the traditional lex/yacc approach, or the use of regular expressions.  With pyparsing, you
don't need to learn a new syntax for defining grammars or matching expressions - the parsing module
provides a library of classes that you use to construct the grammar directly in Python.

Here is a program to parse "Hello, World!" (or any greeting of the form C{"<salutation>, <addressee>!"})::

    from pyparsing import Word, alphas

    # define grammar of a greeting
    greet = Word( alphas ) + "," + Word( alphas ) + "!"

    hello = "Hello, World!"
    print hello, "->", greet.parseString( hello )

The program outputs the following::

    Hello, World! -> ['Hello', ',', 'World', '!']

The Python representation of the grammar is quite readable, owing to the self-explanatory
class names, and the use of '+', '|' and '^' operators.

The parsed results returned from C{parseString()} can be accessed as a nested list, a dictionary, or an
object with named attributes.

The pyparsing module handles some of the problems that are typically vexing when writing text parsers:
 - extra or missing whitespace (the above program will also handle "Hello,World!", "Hello  ,  World  !", etc.)
 - quoted strings
 - embedded comments
"""

__version__ = "1.5.5"
__versionTime__ = "12 Aug 2010 03:56"
__author__ = "Paul McGuire <ptmcg@users.sourceforge.net>"

import string
from weakref import ref as wkref
import copy
import sys
import warnings
import re
import sre_constants
import collections
#~ sys.stderr.write( "testing pyparsing module, version %s, %s\n" % (__version__,__versionTime__ ) )

__all__ = [
'And', 'CaselessKeyword', 'CaselessLiteral', 'CharsNotIn', 'Combine', 'Dict', 'Each', 'Empty',
'FollowedBy', 'Forward', 'GoToColumn', 'Group', 'Keyword', 'LineEnd', 'LineStart', 'Literal',
'MatchFirst', 'NoMatch', 'NotAny', 'OneOrMore', 'OnlyOnce', 'Optional', 'Or',
'ParseBaseException', 'ParseElementEnhance', 'ParseException', 'ParseExpression', 'ParseFatalException',
'ParseResults', 'ParseSyntaxException', 'ParserElement', 'QuotedString', 'RecursiveGrammarException',
'Regex', 'SkipTo', 'StringEnd', 'StringStart', 'Suppress', 'Token', 'TokenConverter', 'Upcase',
'White', 'Word', 'WordEnd', 'WordStart', 'ZeroOrMore',
'alphanums', 'alphas', 'alphas8bit', 'anyCloseTag', 'anyOpenTag', 'cStyleComment', 'col',
'commaSeparatedList', 'commonHTMLEntity', 'countedArray', 'cppStyleComment', 'dblQuotedString',
'dblSlashComment', 'delimitedList', 'dictOf', 'downcaseTokens', 'empty', 'getTokensEndLoc', 'hexnums',
'htmlComment', 'javaStyleComment', 'keepOriginalText', 'line', 'lineEnd', 'lineStart', 'lineno',
'makeHTMLTags', 'makeXMLTags', 'matchOnlyAtCol', 'matchPreviousExpr', 'matchPreviousLiteral',
'nestedExpr', 'nullDebugAction', 'nums', 'oneOf', 'opAssoc', 'operatorPrecedence', 'printables',
'punc8bit', 'pythonStyleComment', 'quotedString', 'removeQuotes', 'replaceHTMLEntity',
'replaceWith', 'restOfLine', 'sglQuotedString', 'srange', 'stringEnd',
'stringStart', 'traceParseAction', 'unicodeString', 'upcaseTokens', 'withAttribute',
'indentedBlock', 'originalTextFor',
]

"""
Detect if we are running version 3.X and make appropriate changes
Robert A. Clark
"""
_PY3K = sys.version_info[0] > 2
if _PY3K:
    _MAX_INT = sys.maxsize
    basestring = str
    unichr = chr
    _ustr = str
    alphas = string.ascii_lowercase + string.ascii_uppercase
else:
    _MAX_INT = sys.maxint
    range = xrange
    set = lambda s : dict( [(c,0) for c in s] )
    alphas = string.lowercase + string.uppercase

    def _ustr(obj):
        """Drop-in replacement for str(obj) that tries to be Unicode friendly. It first tries
           str(obj). If that fails with a UnicodeEncodeError, then it tries unicode(obj). It
           then < returns the unicode object | encodes it with the default encoding | ... >.
        """
        if isinstance(obj,unicode):
            return obj

        try:
            # If this works, then _ustr(obj) has the same behaviour as str(obj), so
            # it won't break any existing code.
            return str(obj)

        except UnicodeEncodeError:
            # The Python docs (http://docs.python.org/ref/customization.html#l2h-182)
            # state that "The return value must be a string object". However, does a
            # unicode object (being a subclass of basestring) count as a "string
            # object"?
            # If so, then return a unicode object:
            return unicode(obj)
            # Else encode it... but how? There are many choices... :)
            # Replace unprintables with escape codes?
            #return unicode(obj).encode(sys.getdefaultencoding(), 'backslashreplace_errors')
            # Replace unprintables with question marks?
            #return unicode(obj).encode(sys.getdefaultencoding(), 'replace')
            # ...


# build list of single arg builtins, tolerant of Python version, that can be used as parse actions
singleArgBuiltins = []
import builtins
for fname in "sum len enumerate sorted reversed list tuple set any all".split():
    try:
        singleArgBuiltins.append(getattr(builtins,fname))
    except AttributeError:
        continue

def _xml_escape(data):
    """Escape &, <, >, ", ', etc. in a string of data."""

    # ampersand must be replaced first
    for from_,to_ in zip('&><"\'', "amp gt lt quot apos".split()):
        data = data.replace(from_, '&'+to_+';')
    return data

class _Constants(object):
    pass

nums       = string.digits
hexnums    = nums + "ABCDEFabcdef"
alphanums  = alphas + nums
_bslash    = chr(92)
printables = "".join( [ c for c in string.printable if c not in string.whitespace ] )

class ParseBaseException(Exception):
    """base exception class for all parsing runtime exceptions"""
    # Performance tuning: we construct a *lot* of these, so keep this
    # constructor as small and fast as possible
    def __init__( self, pstr, loc=0, msg=None, elem=None ):
        self.loc = loc
        if msg is None:
            self.msg = pstr
            self.pstr = ""
        else:
            self.msg = msg
            self.pstr = pstr
        self.parserElement = elem

    def __getattr__( self, aname ):
        """supported attributes by name are:
            - lineno - returns the line number of the exception text
            - col - returns the column number of the exception text
            - line - returns the line containing the exception text
        """
        if( aname == "lineno" ):
            return lineno( self.loc, self.pstr )
        elif( aname in ("col", "column") ):
            return col( self.loc, self.pstr )
        elif( aname == "line" ):
            return line( self.loc, self.pstr )
        else:
            raise AttributeError(aname)

    def __str__( self ):
        return "%s (at char %d), (line:%d, col:%d)" % \
                ( self.msg, self.loc, self.lineno, self.column )
    def __repr__( self ):
        return _ustr(self)
    def markInputline( self, markerString = ">!<" ):
        """Extracts the exception line from the input string, and marks
           the location of the exception with a special symbol.
        """
        line_str = self.line
        line_column = self.column - 1
        if markerString:
            line_str = "".join( [line_str[:line_column],
                                markerString, line_str[line_column:]])
        return line_str.strip()
    def __dir__(self):
        return "loc msg pstr parserElement lineno col line " \
               "markInputLine __str__ __repr__".split()

class ParseException(ParseBaseException):
    """exception thrown when parse expressions don't match class;
       supported attributes by name are:
        - lineno - returns the line number of the exception text
        - col - returns the column number of the exception text
        - line - returns the line containing the exception text
    """
    pass

class ParseFatalException(ParseBaseException):
    """user-throwable exception thrown when inconsistent parse content
       is found; stops all parsing immediately"""
    pass

class ParseSyntaxException(ParseFatalException):
    """just like C{ParseFatalException}, but thrown internally when an
       C{ErrorStop} ('-' operator) indicates that parsing is to stop immediately because
       an unbacktrackable syntax error has been found"""
    def __init__(self, pe):
        super(ParseSyntaxException, self).__init__(
                                    pe.pstr, pe.loc, pe.msg, pe.parserElement)

#~ class ReparseException(ParseBaseException):
    #~ """Experimental class - parse actions can raise this exception to cause
       #~ pyparsing to reparse the input string:
        #~ - with a modified input string, and/or
        #~ - with a modified start location
       #~ Set the values of the ReparseException in the constructor, and raise the
       #~ exception in a parse action to cause pyparsing to use the new string/location.
       #~ Setting the values as None causes no change to be made.
       #~ """
    #~ def __init_( self, newstring, restartLoc ):
        #~ self.newParseText = newstring
        #~ self.reparseLoc = restartLoc

class RecursiveGrammarException(Exception):
    """exception thrown by C{validate()} if the grammar could be improperly recursive"""
    def __init__( self, parseElementList ):
        self.parseElementTrace = parseElementList

    def __str__( self ):
        return "RecursiveGrammarException: %s" % self.parseElementTrace

class _ParseResultsWithOffset(object):
    def __init__(self,p1,p2):
        self.tup = (p1,p2)
    def __getitem__(self,i):
        return self.tup[i]
    def __repr__(self):
        return repr(self.tup)
    def setOffset(self,i):
        self.tup = (self.tup[0],i)

class ParseResults(object):
    """Structured parse results, to provide multiple means of access to the parsed data:
       - as a list (C{len(results)})
       - by list index (C{results[0], results[1]}, etc.)
       - by attribute (C{results.<resultsName>})
       """
    #~ __slots__ = ( "__toklist", "__tokdict", "__doinit", "__name", "__parent", "__accumNames", "__weakref__" )
    def __new__(cls, toklist, name=None, asList=True, modal=True ):
        if isinstance(toklist, cls):
            return toklist
        retobj = object.__new__(cls)
        retobj.__doinit = True
        return retobj

    # Performance tuning: we construct a *lot* of these, so keep this
    # constructor as small and fast as possible
    def __init__( self, toklist, name=None, asList=True, modal=True ):
        if self.__doinit:
            self.__doinit = False
            self.__name = None
            self.__parent = None
            self.__accumNames = {}
            if isinstance(toklist, list):
                self.__toklist = toklist[:]
            else:
                self.__toklist = [toklist]
            self.__tokdict = dict()

        if name is not None and name:
            if not modal:
                self.__accumNames[name] = 0
            if isinstance(name,int):
                name = _ustr(name) # will always return a str, but use _ustr for consistency
            self.__name = name
            if not toklist in (None,'',[]):
                if isinstance(toklist,basestring):
                    toklist = [ toklist ]
                if asList:
                    if isinstance(toklist,ParseResults):
                        self[name] = _ParseResultsWithOffset(toklist.copy(),0)
                    else:
                        self[name] = _ParseResultsWithOffset(ParseResults(toklist[0]),0)
                    self[name].__name = name
                else:
                    try:
                        self[name] = toklist[0]
                    except (KeyError,TypeError,IndexError):
                        self[name] = toklist

    def __getitem__( self, i ):
        if isinstance( i, (int,slice) ):
            return self.__toklist[i]
        else:
            if i not in self.__accumNames:
                return self.__tokdict[i][-1][0]
            else:
                return ParseResults([ v[0] for v in self.__tokdict[i] ])

    def __setitem__( self, k, v ):
        if isinstance(v,_ParseResultsWithOffset):
            self.__tokdict[k] = self.__tokdict.get(k,list()) + [v]
            sub = v[0]
        elif isinstance(k,int):
            self.__toklist[k] = v
            sub = v
        else:
            self.__tokdict[k] = self.__tokdict.get(k,list()) + [_ParseResultsWithOffset(v,0)]
            sub = v
        if isinstance(sub,ParseResults):
            sub.__parent = wkref(self)

    def __delitem__( self, i ):
        if isinstance(i,(int,slice)):
            mylen = len( self.__toklist )
            del self.__toklist[i]

            # convert int to slice
            if isinstance(i, int):
                if i < 0:
                    i += mylen
                i = slice(i, i+1)
            # get removed indices
            removed = list(range(*i.indices(mylen)))
            removed.reverse()
            # fixup indices in token dictionary
            for name in self.__tokdict:
                occurrences = self.__tokdict[name]
                for j in removed:
                    for k, (value, position) in enumerate(occurrences):
                        occurrences[k] = _ParseResultsWithOffset(value, position - (position > j))
        else:
            del self.__tokdict[i]

    def __contains__( self, k ):
        return k in self.__tokdict

    def __len__( self ): return len( self.__toklist )
    def __bool__(self): return len( self.__toklist ) > 0
    __nonzero__ = __bool__
    def __iter__( self ): return iter( self.__toklist )
    def __reversed__( self ): return iter( reversed(self.__toklist) )
    def keys( self ):
        """Returns all named result keys."""
        return self.__tokdict.keys()

    def pop( self, index=-1 ):
        """Removes and returns item at specified index (default=last).
           Will work with either numeric indices or dict-key indicies."""
        ret = self[index]
        del self[index]
        return ret

    def get(self, key, defaultValue=None):
        """Returns named result matching the given key, or if there is no
           such name, then returns the given C{defaultValue} or C{None} if no
           C{defaultValue} is specified."""
        if key in self:
            return self[key]
        else:
            return defaultValue

    def insert( self, index, insStr ):
        """Inserts new element at location index in the list of parsed tokens."""
        self.__toklist.insert(index, insStr)
        # fixup indices in token dictionary
        for name in self.__tokdict:
            occurrences = self.__tokdict[name]
            for k, (value, position) in enumerate(occurrences):
                occurrences[k] = _ParseResultsWithOffset(value, position + (position > index))

    def items( self ):
        """Returns all named result keys and values as a list of tuples."""
        return [(k,self[k]) for k in self.__tokdict]

    def values( self ):
        """Returns all named result values."""
        return [ v[-1][0] for v in self.__tokdict.values() ]

    def __getattr__( self, name ):
        if True: #name not in self.__slots__:
            if name in self.__tokdict:
                if name not in self.__accumNames:
                    return self.__tokdict[name][-1][0]
                else:
                    return ParseResults([ v[0] for v in self.__tokdict[name] ])
            else:
                return ""
        return None

    def __add__( self, other ):
        ret = self.copy()
        ret += other
        return ret

    def __iadd__( self, other ):
        if other.__tokdict:
            offset = len(self.__toklist)
            addoffset = ( lambda a: (a<0 and offset) or (a+offset) )
            otheritems = other.__tokdict.items()
            otherdictitems = [(k, _ParseResultsWithOffset(v[0],addoffset(v[1])) )
                                for (k,vlist) in otheritems for v in vlist]
            for k,v in otherdictitems:
                self[k] = v
                if isinstance(v[0],ParseResults):
                    v[0].__parent = wkref(self)

        self.__toklist += other.__toklist
        self.__accumNames.update( other.__accumNames )
        return self

    def __radd__(self, other):
        if isinstance(other,int) and other == 0:
            return self.copy()

    def __repr__( self ):
        return "(%s, %s)" % ( repr( self.__toklist ), repr( self.__tokdict ) )

    def __str__( self ):
        out = "["
        sep = ""
        for i in self.__toklist:
            if isinstance(i, ParseResults):
                out += sep + _ustr(i)
            else:
                out += sep + repr(i)
            sep = ", "
        out += "]"
        return out

    def _asStringList( self, sep='' ):
        out = []
        for item in self.__toklist:
            if out and sep:
                out.append(sep)
            if isinstance( item, ParseResults ):
                out += item._asStringList()
            else:
                out.append( _ustr(item) )
        return out

    def asList( self ):
        """Returns the parse results as a nested list of matching tokens, all converted to strings."""
        out = []
        for res in self.__toklist:
            if isinstance(res,ParseResults):
                out.append( res.asList() )
            else:
                out.append( res )
        return out

    def asDict( self ):
        """Returns the named parse results as dictionary."""
        return dict( self.items() )

    def copy( self ):
        """Returns a new copy of a C{ParseResults} object."""
        ret = ParseResults( self.__toklist )
        ret.__tokdict = self.__tokdict.copy()
        ret.__parent = self.__parent
        ret.__accumNames.update( self.__accumNames )
        ret.__name = self.__name
        return ret

    def asXML( self, doctag=None, namedItemsOnly=False, indent="", formatted=True ):
        """Returns the parse results as XML. Tags are created for tokens and lists that have defined results names."""
        nl = "\n"
        out = []
        namedItems = dict( [ (v[1],k) for (k,vlist) in self.__tokdict.items()
                                                            for v in vlist ] )
        nextLevelIndent = indent + "  "

        # collapse out indents if formatting is not desired
        if not formatted:
            indent = ""
            nextLevelIndent = ""
            nl = ""

        selfTag = None
        if doctag is not None:
            selfTag = doctag
        else:
            if self.__name:
                selfTag = self.__name

        if not selfTag:
            if namedItemsOnly:
                return ""
            else:
                selfTag = "ITEM"

        out += [ nl, indent, "<", selfTag, ">" ]

        worklist = self.__toklist
        for i,res in enumerate(worklist):
            if isinstance(res,ParseResults):
                if i in namedItems:
                    out += [ res.asXML(namedItems[i],
                                        namedItemsOnly and doctag is None,
                                        nextLevelIndent,
                                        formatted)]
                else:
                    out += [ res.asXML(None,
                                        namedItemsOnly and doctag is None,
                                        nextLevelIndent,
                                        formatted)]
            else:
                # individual token, see if there is a name for it
                resTag = None
                if i in namedItems:
                    resTag = namedItems[i]
                if not resTag:
                    if namedItemsOnly:
                        continue
                    else:
                        resTag = "ITEM"
                xmlBodyText = _xml_escape(_ustr(res))
                out += [ nl, nextLevelIndent, "<", resTag, ">",
                                                xmlBodyText,
                                                "</", resTag, ">" ]

        out += [ nl, indent, "</", selfTag, ">" ]
        return "".join(out)

    def __lookup(self,sub):
        for k,vlist in self.__tokdict.items():
            for v,loc in vlist:
                if sub is v:
                    return k
        return None

    def getName(self):
        """Returns the results name for this token expression."""
        if self.__name:
            return self.__name
        elif self.__parent:
            par = self.__parent()
            if par:
                return par.__lookup(self)
            else:
                return None
        elif (len(self) == 1 and
               len(self.__tokdict) == 1 and
               self.__tokdict.values()[0][0][1] in (0,-1)):
            return self.__tokdict.keys()[0]
        else:
            return None

    def dump(self,indent='',depth=0):
        """Diagnostic method for listing out the contents of a C{ParseResults}.
           Accepts an optional C{indent} argument so that this string can be embedded
           in a nested display of other data."""
        out = []
        out.append( indent+_ustr(self.asList()) )
        keys = self.items()
        keys.sort()
        for k,v in keys:
            if out:
                out.append('\n')
            out.append( "%s%s- %s: " % (indent,('  '*depth), k) )
            if isinstance(v,ParseResults):
                if v.keys():
                    out.append( v.dump(indent,depth+1) )
                else:
                    out.append(_ustr(v))
            else:
                out.append(_ustr(v))
        return "".join(out)

    # add support for pickle protocol
    def __getstate__(self):
        return ( self.__toklist,
                 ( self.__tokdict.copy(),
                   self.__parent is not None and self.__parent() or None,
                   self.__accumNames,
                   self.__name ) )

    def __setstate__(self,state):
        self.__toklist = state[0]
        self.__tokdict, \
        par, \
        inAccumNames, \
        self.__name = state[1]
        self.__accumNames = {}
        self.__accumNames.update(inAccumNames)
        if par is not None:
            self.__parent = wkref(par)
        else:
            self.__parent = None

    def __dir__(self):
        return dir(super(ParseResults,self)) + self.keys()

collections.MutableMapping.register(ParseResults)

def col (loc,strg):
    """Returns current column within a string, counting newlines as line separators.
   The first column is number 1.

   Note: the default parsing behavior is to expand tabs in the input string
   before starting the parsing process.  See L{I{ParserElement.parseString}<ParserElement.parseString>} for more information
   on parsing strings containing <TAB>s, and suggested methods to maintain a
   consistent view of the parsed string, the parse location, and line and column
   positions within the parsed string.
   """
    return (loc<len(strg) and strg[loc] == '\n') and 1 or loc - strg.rfind("\n", 0, loc)

def lineno(loc,strg):
    """Returns current line number within a string, counting newlines as line separators.
   The first line is number 1.

   Note: the default parsing behavior is to expand tabs in the input string
   before starting the parsing process.  See L{I{ParserElement.parseString}<ParserElement.parseString>} for more information
   on parsing strings containing <TAB>s, and suggested methods to maintain a
   consistent view of the parsed string, the parse location, and line and column
   positions within the parsed string.
   """
    return strg.count("\n",0,loc) + 1

def line( loc, strg ):
    """Returns the line of text containing loc within a string, counting newlines as line separators.
       """
    lastCR = strg.rfind("\n", 0, loc)
    nextCR = strg.find("\n", loc)
    if nextCR >= 0:
        return strg[lastCR+1:nextCR]
    else:
        return strg[lastCR+1:]

def _defaultStartDebugAction( instring, loc, expr ):
    print ("Match " + _ustr(expr) + " at loc " + _ustr(loc) + "(%d,%d)" % ( lineno(loc,instring), col(loc,instring) ))

def _defaultSuccessDebugAction( instring, startloc, endloc, expr, toks ):
    print ("Matched " + _ustr(expr) + " -> " + str(toks.asList()))

def _defaultExceptionDebugAction( instring, loc, expr, exc ):
    print ("Exception raised:" + _ustr(exc))

def nullDebugAction(*args):
    """'Do-nothing' debug action, to suppress debugging output during parsing."""
    pass

class ParserElement(object):
    """Abstract base level parser element class."""
    DEFAULT_WHITE_CHARS = " \n\t\r"
    verbose_stacktrace = False

    def setDefaultWhitespaceChars( chars ):
        """Overrides the default whitespace chars
        """
        ParserElement.DEFAULT_WHITE_CHARS = chars
    setDefaultWhitespaceChars = staticmethod(setDefaultWhitespaceChars)

    def __init__( self, savelist=False ):
        self.parseAction = list()
        self.failAction = None
        #~ self.name = "<unknown>"  # don't define self.name, let subclasses try/except upcall
        self.strRepr = None
        self.resultsName = None
        self.saveAsList = savelist
        self.skipWhitespace = True
        self.whiteChars = ParserElement.DEFAULT_WHITE_CHARS
        self.copyDefaultWhiteChars = True
        self.mayReturnEmpty = False # used when checking for left-recursion
        self.keepTabs = False
        self.ignoreExprs = list()
        self.debug = False
        self.streamlined = False
        self.mayIndexError = True # used to optimize exception handling for subclasses that don't advance parse index
        self.errmsg = ""
        self.modalResults = True # used to mark results names as modal (report only last) or cumulative (list all)
        self.debugActions = ( None, None, None ) #custom debug actions
        self.re = None
        self.callPreparse = True # used to avoid redundant calls to preParse
        self.callDuringTry = False

    def copy( self ):
        """Make a copy of this C{ParserElement}.  Useful for defining different parse actions
           for the same parsing pattern, using copies of the original parse element."""
        cpy = copy.copy( self )
        cpy.parseAction = self.parseAction[:]
        cpy.ignoreExprs = self.ignoreExprs[:]
        if self.copyDefaultWhiteChars:
            cpy.whiteChars = ParserElement.DEFAULT_WHITE_CHARS
        return cpy

    def setName( self, name ):
        """Define name for this expression, for use in debugging."""
        self.name = name
        self.errmsg = "Expected " + self.name
        if hasattr(self,"exception"):
            self.exception.msg = self.errmsg
        return self

    def setResultsName( self, name, listAllMatches=False ):
        """Define name for referencing matching tokens as a nested attribute
           of the returned parse results.
           NOTE: this returns a *copy* of the original C{ParserElement} object;
           this is so that the client can define a basic element, such as an
           integer, and reference it in multiple places with different names.

           You can also set results names using the abbreviated syntax,
           C{expr("name")} in place of C{expr.setResultsName("name")} -
           see L{I{__call__}<__call__>}.
        """
        newself = self.copy()
        newself.resultsName = name
        newself.modalResults = not listAllMatches
        return newself

    def setBreak(self,breakFlag = True):
        """Method to invoke the Python pdb debugger when this element is
           about to be parsed. Set C{breakFlag} to True to enable, False to
           disable.
        """
        if breakFlag:
            _parseMethod = self._parse
            def breaker(instring, loc, doActions=True, callPreParse=True):
                import pdb
                pdb.set_trace()
                return _parseMethod( instring, loc, doActions, callPreParse )
            breaker._originalParseMethod = _parseMethod
            self._parse = breaker
        else:
            if hasattr(self._parse,"_originalParseMethod"):
                self._parse = self._parse._originalParseMethod
        return self

    def _normalizeParseActionArgs( f ):
        """Internal method used to decorate parse actions that take fewer than 3 arguments,
           so that all parse actions can be called as C{f(s,l,t)}."""
        STAR_ARGS = 4

        # special handling for single-argument builtins
        if (f in singleArgBuiltins):
            numargs = 1
        else:
            try:
                restore = None
                if isinstance(f,type):
                    restore = f
                    f = f.__init__
                if not _PY3K:
                    codeObj = f.func_code
                else:
                    codeObj = f.code
                if codeObj.co_flags & STAR_ARGS:
                    return f
                numargs = codeObj.co_argcount
                if not _PY3K:
                    if hasattr(f,"im_self"):
                        numargs -= 1
                else:
                    if hasattr(f,"__self__"):
                        numargs -= 1
                if restore:
                    f = restore
            except AttributeError:
                try:
                    if not _PY3K:
                        call_im_func_code = f.__call__.im_func.func_code
                    else:
                        call_im_func_code = f.__code__

                    # not a function, must be a callable object, get info from the
                    # im_func binding of its bound __call__ method
                    if call_im_func_code.co_flags & STAR_ARGS:
                        return f
                    numargs = call_im_func_code.co_argcount
                    if not _PY3K:
                        if hasattr(f.__call__,"im_self"):
                            numargs -= 1
                    else:
                        if hasattr(f.__call__,"__self__"):
                            numargs -= 0
                except AttributeError:
                    if not _PY3K:
                        call_func_code = f.__call__.func_code
                    else:
                        call_func_code = f.__call__.__code__
                    # not a bound method, get info directly from __call__ method
                    if call_func_code.co_flags & STAR_ARGS:
                        return f
                    numargs = call_func_code.co_argcount
                    if not _PY3K:
                        if hasattr(f.__call__,"im_self"):
                            numargs -= 1
                    else:
                        if hasattr(f.__call__,"__self__"):
                            numargs -= 1


        # print ("adding function %s with %d args" % (f.func_name,numargs))
        if numargs == 3:
            return f
        else:
            if numargs > 3:
                def tmp(s,l,t):
                    return f(s,l,t)
            elif numargs == 2:
                def tmp(s,l,t):
                    return f(l,t)
            elif numargs == 1:
                def tmp(s,l,t):
                    return f(t)
            else: #~ numargs == 0:
                def tmp(s,l,t):
                    return f()
            try:
                tmp.__name__ = f.__name__
            except (AttributeError,TypeError):
                # no need for special handling if attribute doesnt exist
                pass
            try:
                tmp.__doc__ = f.__doc__
            except (AttributeError,TypeError):
                # no need for special handling if attribute doesnt exist
                pass
            try:
                tmp.__dict__.update(f.__dict__)
            except (AttributeError,TypeError):
                # no need for special handling if attribute doesnt exist
                pass
            return tmp
    _normalizeParseActionArgs = staticmethod(_normalizeParseActionArgs)

    def setParseAction( self, *fns, **kwargs ):
        """Define action to perform when successfully matching parse element definition.
           Parse action fn is a callable method with 0-3 arguments, called as C{fn(s,loc,toks)},
           C{fn(loc,toks)}, C{fn(toks)}, or just C{fn()}, where:
            - s   = the original string being parsed (see note below)
            - loc = the location of the matching substring
            - toks = a list of the matched tokens, packaged as a ParseResults object
           If the functions in fns modify the tokens, they can return them as the return
           value from fn, and the modified list of tokens will replace the original.
           Otherwise, fn does not need to return any value.

           Note: the default parsing behavior is to expand tabs in the input string
           before starting the parsing process.  See L{I{parseString}<parseString>} for more information
           on parsing strings containing <TAB>s, and suggested methods to maintain a
           consistent view of the parsed string, the parse location, and line and column
           positions within the parsed string.
           """
        self.parseAction = list(map(self._normalizeParseActionArgs, list(fns)))
        self.callDuringTry = ("callDuringTry" in kwargs and kwargs["callDuringTry"])
        return self

    def addParseAction( self, *fns, **kwargs ):
        """Add parse action to expression's list of parse actions. See L{I{setParseAction}<setParseAction>}."""
        self.parseAction += list(map(self._normalizeParseActionArgs, list(fns)))
        self.callDuringTry = self.callDuringTry or ("callDuringTry" in kwargs and kwargs["callDuringTry"])
        return self

    def setFailAction( self, fn ):
        """Define action to perform if parsing fails at this expression.
           Fail acton fn is a callable function that takes the arguments
           C{fn(s,loc,expr,err)} where:
            - s = string being parsed
            - loc = location where expression match was attempted and failed
            - expr = the parse expression that failed
            - err = the exception thrown
           The function returns no value.  It may throw C{ParseFatalException}
           if it is desired to stop parsing immediately."""
        self.failAction = fn
        return self

    def _skipIgnorables( self, instring, loc ):
        exprsFound = True
        while exprsFound:
            exprsFound = False
            for e in self.ignoreExprs:
                try:
                    while 1:
                        loc,dummy = e._parse( instring, loc )
                        exprsFound = True
                except ParseException:
                    pass
        return loc

    def preParse( self, instring, loc ):
        if self.ignoreExprs:
            loc = self._skipIgnorables( instring, loc )

        if self.skipWhitespace:
            wt = self.whiteChars
            instrlen = len(instring)
            while loc < instrlen and instring[loc] in wt:
                loc += 1

        return loc

    def parseImpl( self, instring, loc, doActions=True ):
        return loc, []

    def postParse( self, instring, loc, tokenlist ):
        return tokenlist

    #~ @profile
    def _parseNoCache( self, instring, loc, doActions=True, callPreParse=True ):
        debugging = ( self.debug ) #and doActions )

        if debugging or self.failAction:
            #~ print ("Match",self,"at loc",loc,"(%d,%d)" % ( lineno(loc,instring), col(loc,instring) ))
            if (self.debugActions[0] ):
                self.debugActions[0]( instring, loc, self )
            if callPreParse and self.callPreparse:
                preloc = self.preParse( instring, loc )
            else:
                preloc = loc
            tokensStart = preloc
            try:
                try:
                    loc,tokens = self.parseImpl( instring, preloc, doActions )
                except IndexError:
                    raise ParseException( instring, len(instring), self.errmsg, self )
            except ParseBaseException as err:
                #~ print ("Exception raised:", err)
                if self.debugActions[2]:
                    self.debugActions[2]( instring, tokensStart, self, err )
                if self.failAction:
                    self.failAction( instring, tokensStart, self, err )
                raise
        else:
            if callPreParse and self.callPreparse:
                preloc = self.preParse( instring, loc )
            else:
                preloc = loc
            tokensStart = preloc
            if self.mayIndexError or loc >= len(instring):
                try:
                    loc,tokens = self.parseImpl( instring, preloc, doActions )
                except IndexError:
                    raise ParseException( instring, len(instring), self.errmsg, self )
            else:
                loc,tokens = self.parseImpl( instring, preloc, doActions )

        tokens = self.postParse( instring, loc, tokens )

        retTokens = ParseResults( tokens, self.resultsName, asList=self.saveAsList, modal=self.modalResults )
        if self.parseAction and (doActions or self.callDuringTry):
            if debugging:
                try:
                    for fn in self.parseAction:
                        tokens = fn( instring, tokensStart, retTokens )
                        if tokens is not None:
                            retTokens = ParseResults( tokens,
                                                      self.resultsName,
                                                      asList=self.saveAsList and isinstance(tokens,(ParseResults,list)),
                                                      modal=self.modalResults )
                except ParseBaseException as err:
                    #~ print "Exception raised in user parse action:", err
                    if (self.debugActions[2] ):
                        self.debugActions[2]( instring, tokensStart, self, err )
                    raise
            else:
                for fn in self.parseAction:
                    tokens = fn( instring, tokensStart, retTokens )
                    if tokens is not None:
                        retTokens = ParseResults( tokens,
                                                  self.resultsName,
                                                  asList=self.saveAsList and isinstance(tokens,(ParseResults,list)),
                                                  modal=self.modalResults )

        if debugging:
            #~ print ("Matched",self,"->",retTokens.asList())
            if (self.debugActions[1] ):
                self.debugActions[1]( instring, tokensStart, loc, self, retTokens )

        return loc, retTokens

    def tryParse( self, instring, loc ):
        try:
            return self._parse( instring, loc, doActions=False )[0]
        except ParseFatalException:
            raise ParseException( instring, loc, self.errmsg, self)

    # this method gets repeatedly called during backtracking with the same arguments -
    # we can cache these arguments and save ourselves the trouble of re-parsing the contained expression
    def _parseCache( self, instring, loc, doActions=True, callPreParse=True ):
        lookup = (self,instring,loc,callPreParse,doActions)
        if lookup in ParserElement._exprArgCache:
            value = ParserElement._exprArgCache[ lookup ]
            if isinstance(value, Exception):
                raise value
            return value
        else:
            try:
                value = self._parseNoCache( instring, loc, doActions, callPreParse )
                ParserElement._exprArgCache[ lookup ] = (value[0],value[1].copy())
                return value
            except ParseBaseException as err:
                err.__traceback__ = None
                ParserElement._exprArgCache[ lookup ] = err
                raise

    _parse = _parseNoCache

    # argument cache for optimizing repeated calls when backtracking through recursive expressions
    _exprArgCache = {}
    def resetCache():
        ParserElement._exprArgCache.clear()
    resetCache = staticmethod(resetCache)

    _packratEnabled = False
    def enablePackrat():
        """Enables "packrat" parsing, which adds memoizing to the parsing logic.
           Repeated parse attempts at the same string location (which happens
           often in many complex grammars) can immediately return a cached value,
           instead of re-executing parsing/validating code.  Memoizing is done of
           both valid results and parsing exceptions.

           This speedup may break existing programs that use parse actions that
           have side-effects.  For this reason, packrat parsing is disabled when
           you first import pyparsing.  To activate the packrat feature, your
           program must call the class method C{ParserElement.enablePackrat()}.  If
           your program uses C{psyco} to "compile as you go", you must call
           C{enablePackrat} before calling C{psyco.full()}.  If you do not do this,
           Python will crash.  For best results, call C{enablePackrat()} immediately
           after importing pyparsing.
        """
        if not ParserElement._packratEnabled:
            ParserElement._packratEnabled = True
            ParserElement._parse = ParserElement._parseCache
    enablePackrat = staticmethod(enablePackrat)

    def parseString( self, instring, parseAll=False ):
        """Execute the parse expression with the given string.
           This is the main interface to the client code, once the complete
           expression has been built.

           If you want the grammar to require that the entire input string be
           successfully parsed, then set C{parseAll} to True (equivalent to ending
           the grammar with C{StringEnd()}).

           Note: C{parseString} implicitly calls C{expandtabs()} on the input string,
           in order to report proper column numbers in parse actions.
           If the input string contains tabs and
           the grammar uses parse actions that use the C{loc} argument to index into the
           string being parsed, you can ensure you have a consistent view of the input
           string by:
            - calling C{parseWithTabs} on your grammar before calling C{parseString}
              (see L{I{parseWithTabs}<parseWithTabs>})
            - define your parse action using the full C{(s,loc,toks)} signature, and
              reference the input string using the parse action's C{s} argument
            - explictly expand the tabs in your input string before calling
              C{parseString}
        """
        ParserElement.resetCache()
        if not self.streamlined:
            self.streamline()
            #~ self.saveAsList = True
        for e in self.ignoreExprs:
            e.streamline()
        if not self.keepTabs:
            instring = instring.expandtabs()
        try:
            loc, tokens = self._parse( instring, 0 )
            if parseAll:
                #loc = self.preParse( instring, loc )
                se = StringEnd()
                se._parse( instring, loc )
        except ParseBaseException as err:
            if ParserElement.verbose_stacktrace:
                raise
            else:
                # catch and re-raise exception from here, clears out pyparsing internal stack trace
                raise err
        else:
            return tokens

    def scanString( self, instring, maxMatches=_MAX_INT ):
        """Scan the input string for expression matches.  Each match will return the
           matching tokens, start location, and end location.  May be called with optional
           C{maxMatches} argument, to clip scanning after 'n' matches are found.

           Note that the start and end locations are reported relative to the string
           being parsed.  See L{I{parseString}<parseString>} for more information on parsing
           strings with embedded tabs."""
        if not self.streamlined:
            self.streamline()
        for e in self.ignoreExprs:
            e.streamline()

        if not self.keepTabs:
            instring = _ustr(instring).expandtabs()
        instrlen = len(instring)
        loc = 0
        preparseFn = self.preParse
        parseFn = self._parse
        ParserElement.resetCache()
        matches = 0
        try:
            while loc <= instrlen and matches < maxMatches:
                try:
                    preloc = preparseFn( instring, loc )
                    nextLoc,tokens = parseFn( instring, preloc, callPreParse=False )
                except ParseException:
                    loc = preloc+1
                else:
                    if nextLoc > loc:
                        matches += 1
                        yield tokens, preloc, nextLoc
                        loc = nextLoc
                    else:
                        loc = preloc+1
        except ParseBaseException as err:
            if ParserElement.verbose_stacktrace:
                raise
            else:
                # catch and re-raise exception from here, clears out pyparsing internal stack trace
                raise err

    def transformString( self, instring ):
        """Extension to C{scanString}, to modify matching text with modified tokens that may
           be returned from a parse action.  To use C{transformString}, define a grammar and
           attach a parse action to it that modifies the returned token list.
           Invoking C{transformString()} on a target string will then scan for matches,
           and replace the matched text patterns according to the logic in the parse
           action.  C{transformString()} returns the resulting transformed string."""
        out = []
        lastE = 0
        # force preservation of <TAB>s, to minimize unwanted transformation of string, and to
        # keep string locs straight between transformString and scanString
        self.keepTabs = True
        try:
            for t,s,e in self.scanString( instring ):
                out.append( instring[lastE:s] )
                if t:
                    if isinstance(t,ParseResults):
                        out += t.asList()
                    elif isinstance(t,list):
                        out += t
                    else:
                        out.append(t)
                lastE = e
            out.append(instring[lastE:])
            return "".join(map(_ustr,out))
        except ParseBaseException as err:
            if ParserElement.verbose_stacktrace:
                raise
            else:
                # catch and re-raise exception from here, clears out pyparsing internal stack trace
                raise err

    def searchString( self, instring, maxMatches=_MAX_INT ):
        """Another extension to C{scanString}, simplifying the access to the tokens found
           to match the given parse expression.  May be called with optional
           C{maxMatches} argument, to clip searching after 'n' matches are found.
        """
        try:
            return ParseResults([ t for t,s,e in self.scanString( instring, maxMatches ) ])
        except ParseBaseException as err:
            if ParserElement.verbose_stacktrace:
                raise
            else:
                # catch and re-raise exception from here, clears out pyparsing internal stack trace
                raise err

    def __add__(self, other ):
        """Implementation of + operator - returns And"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return And( [ self, other ] )

    def __radd__(self, other ):
        """Implementation of + operator when left operand is not a C{ParserElement}"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other + self

    def __sub__(self, other):
        """Implementation of - operator, returns C{And} with error stop"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return And( [ self, And._ErrorStop(), other ] )

    def __rsub__(self, other ):
        """Implementation of - operator when left operand is not a C{ParserElement}"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other - self

    def __mul__(self,other):
        """Implementation of * operator, allows use of C{expr * 3} in place of
           C{expr + expr + expr}.  Expressions may also me multiplied by a 2-integer
           tuple, similar to C{{min,max}} multipliers in regular expressions.  Tuples
           may also include C{None} as in:
            - C{expr*(n,None)} or C{expr*(n,)} is equivalent
              to C{expr*n + ZeroOrMore(expr)}
              (read as "at least n instances of C{expr}")
            - C{expr*(None,n)} is equivalent to C{expr*(0,n)}
              (read as "0 to n instances of C{expr}")
            - C{expr*(None,None)} is equivalent to C{ZeroOrMore(expr)}
            - C{expr*(1,None)} is equivalent to C{OneOrMore(expr)}

           Note that C{expr*(None,n)} does not raise an exception if
           more than n exprs exist in the input stream; that is,
           C{expr*(None,n)} does not enforce a maximum number of expr
           occurrences.  If this behavior is desired, then write
           C{expr*(None,n) + ~expr}

        """
        if isinstance(other,int):
            minElements, optElements = other,0
        elif isinstance(other,tuple):
            other = (other + (None, None))[:2]
            if other[0] is None:
                other = (0, other[1])
            if isinstance(other[0],int) and other[1] is None:
                if other[0] == 0:
                    return ZeroOrMore(self)
                if other[0] == 1:
                    return OneOrMore(self)
                else:
                    return self*other[0] + ZeroOrMore(self)
            elif isinstance(other[0],int) and isinstance(other[1],int):
                minElements, optElements = other
                optElements -= minElements
            else:
                raise TypeError("cannot multiply 'ParserElement' and ('%s','%s') objects", type(other[0]),type(other[1]))
        else:
            raise TypeError("cannot multiply 'ParserElement' and '%s' objects", type(other))

        if minElements < 0:
            raise ValueError("cannot multiply ParserElement by negative value")
        if optElements < 0:
            raise ValueError("second tuple value must be greater or equal to first tuple value")
        if minElements == optElements == 0:
            raise ValueError("cannot multiply ParserElement by 0 or (0,0)")

        if (optElements):
            def makeOptionalList(n):
                if n>1:
                    return Optional(self + makeOptionalList(n-1))
                else:
                    return Optional(self)
            if minElements:
                if minElements == 1:
                    ret = self + makeOptionalList(optElements)
                else:
                    ret = And([self]*minElements) + makeOptionalList(optElements)
            else:
                ret = makeOptionalList(optElements)
        else:
            if minElements == 1:
                ret = self
            else:
                ret = And([self]*minElements)
        return ret

    def __rmul__(self, other):
        return self.__mul__(other)

    def __or__(self, other ):
        """Implementation of | operator - returns C{MatchFirst}"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return MatchFirst( [ self, other ] )

    def __ror__(self, other ):
        """Implementation of | operator when left operand is not a C{ParserElement}"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other | self

    def __xor__(self, other ):
        """Implementation of ^ operator - returns C{Or}"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return Or( [ self, other ] )

    def __rxor__(self, other ):
        """Implementation of ^ operator when left operand is not a C{ParserElement}"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other ^ self

    def __and__(self, other ):
        """Implementation of & operator - returns C{Each}"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return Each( [ self, other ] )

    def __rand__(self, other ):
        """Implementation of & operator when left operand is not a C{ParserElement}"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other & self

    def __invert__( self ):
        """Implementation of ~ operator - returns C{NotAny}"""
        return NotAny( self )

    def __call__(self, name):
        """Shortcut for C{setResultsName}, with C{listAllMatches=default}::
             userdata = Word(alphas).setResultsName("name") + Word(nums+"-").setResultsName("socsecno")
           could be written as::
             userdata = Word(alphas)("name") + Word(nums+"-")("socsecno")
           """
        return self.setResultsName(name)

    def suppress( self ):
        """Suppresses the output of this C{ParserElement}; useful to keep punctuation from
           cluttering up returned output.
        """
        return Suppress( self )

    def leaveWhitespace( self ):
        """Disables the skipping of whitespace before matching the characters in the
           C{ParserElement}'s defined pattern.  This is normally only used internally by
           the pyparsing module, but may be needed in some whitespace-sensitive grammars.
        """
        self.skipWhitespace = False
        return self

    def setWhitespaceChars( self, chars ):
        """Overrides the default whitespace chars
        """
        self.skipWhitespace = True
        self.whiteChars = chars
        self.copyDefaultWhiteChars = False
        return self

    def parseWithTabs( self ):
        """Overrides default behavior to expand <TAB>s to spaces before parsing the input string.
           Must be called before C{parseString} when the input grammar contains elements that
           match <TAB> characters."""
        self.keepTabs = True
        return self

    def ignore( self, other ):
        """Define expression to be ignored (e.g., comments) while doing pattern
           matching; may be called repeatedly, to define multiple comment or other
           ignorable patterns.
        """
        if isinstance( other, Suppress ):
            if other not in self.ignoreExprs:
                self.ignoreExprs.append( other.copy() )
        else:
            self.ignoreExprs.append( Suppress( other.copy() ) )
        return self

    def setDebugActions( self, startAction, successAction, exceptionAction ):
        """Enable display of debugging messages while doing pattern matching."""
        self.debugActions = (startAction or _defaultStartDebugAction,
                             successAction or _defaultSuccessDebugAction,
                             exceptionAction or _defaultExceptionDebugAction)
        self.debug = True
        return self

    def setDebug( self, flag=True ):
        """Enable display of debugging messages while doing pattern matching.
           Set C{flag} to True to enable, False to disable."""
        if flag:
            self.setDebugActions( _defaultStartDebugAction, _defaultSuccessDebugAction, _defaultExceptionDebugAction )
        else:
            self.debug = False
        return self

    def __str__( self ):
        return self.name

    def __repr__( self ):
        return _ustr(self)

    def streamline( self ):
        self.streamlined = True
        self.strRepr = None
        return self

    def checkRecursion( self, parseElementList ):
        pass

    def validate( self, validateTrace=[] ):
        """Check defined expressions for valid structure, check for infinite recursive definitions."""
        self.checkRecursion( [] )

    def parseFile( self, file_or_filename, parseAll=False ):
        """Execute the parse expression on the given file or filename.
           If a filename is specified (instead of a file object),
           the entire file is opened, read, and closed before parsing.
        """
        try:
            file_contents = file_or_filename.read()
        except AttributeError:
            f = open(file_or_filename, "rb")
            file_contents = f.read()
            f.close()
        try:
            return self.parseString(file_contents, parseAll)
        except ParseBaseException as err:
            # catch and re-raise exception from here, clears out pyparsing internal stack trace
            raise err

    def __eq__(self,other):
        if isinstance(other, ParserElement):
            return self is other or self.__dict__ == other.__dict__
        elif isinstance(other, basestring):
            try:
                self.parseString(_ustr(other), parseAll=True)
                return True
            except ParseBaseException:
                return False
        else:
            return super(ParserElement,self)==other

    def __ne__(self,other):
        return not (self == other)

    def __hash__(self):
        return hash(id(self))

    def __req__(self,other):
        return self == other

    def __rne__(self,other):
        return not (self == other)


class Token(ParserElement):
    """Abstract C{ParserElement} subclass, for defining atomic matching patterns."""
    def __init__( self ):
        super(Token,self).__init__( savelist=False )
        #self.myException = ParseException("",0,"",self)

    def setName(self, name):
        s = super(Token,self).setName(name)
        self.errmsg = "Expected " + self.name
        #s.myException.msg = self.errmsg
        return s


class Empty(Token):
    """An empty token, will always match."""
    def __init__( self ):
        super(Empty,self).__init__()
        self.name = "Empty"
        self.mayReturnEmpty = True
        self.mayIndexError = False


class NoMatch(Token):
    """A token that will never match."""
    def __init__( self ):
        super(NoMatch,self).__init__()
        self.name = "NoMatch"
        self.mayReturnEmpty = True
        self.mayIndexError = False
        self.errmsg = "Unmatchable token"
        #self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions=True ):
        raise ParseException(instring, loc, self.errmsg, self)


class Literal(Token):
    """Token to exactly match a specified string."""
    def __init__( self, matchString ):
        super(Literal,self).__init__()
        self.match = matchString
        self.matchLen = len(matchString)
        try:
            self.firstMatchChar = matchString[0]
        except IndexError:
            warnings.warn("null string passed to Literal; use Empty() instead",
                            SyntaxWarning, stacklevel=2)
            self.__class__ = Empty
        self.name = '"%s"' % _ustr(self.match)
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = False
        #self.myException.msg = self.errmsg
        self.mayIndexError = False

    # Performance tuning: this routine gets called a *lot*
    # if this is a single character match string  and the first character matches,
    # short-circuit as quickly as possible, and avoid calling startswith
    #~ @profile
    def parseImpl( self, instring, loc, doActions=True ):
        if (instring[loc] == self.firstMatchChar and
            (self.matchLen==1 or instring.startswith(self.match,loc)) ):
            return loc+self.matchLen, self.match
        raise ParseException( instring, loc, self.errmsg, self )
_L = Literal

class Keyword(Token):
    """Token to exactly match a specified string as a keyword, that is, it must be
       immediately followed by a non-keyword character.  Compare with C{Literal}::
         Literal("if") will match the leading 'if' in 'ifAndOnlyIf'.
         Keyword("if") will not; it will only match the leading 'if in 'if x=1', or 'if(y==2)'
       Accepts two optional constructor arguments in addition to the keyword string:
       C{identChars} is a string of characters that would be valid identifier characters,
       defaulting to all alphanumerics + "_" and "$"; C{caseless} allows case-insensitive
       matching, default is False.
    """
    DEFAULT_KEYWORD_CHARS = alphanums+"_$"

    def __init__( self, matchString, identChars=DEFAULT_KEYWORD_CHARS, caseless=False ):
        super(Keyword,self).__init__()
        self.match = matchString
        self.matchLen = len(matchString)
        try:
            self.firstMatchChar = matchString[0]
        except IndexError:
            warnings.warn("null string passed to Keyword; use Empty() instead",
                            SyntaxWarning, stacklevel=2)
        self.name = '"%s"' % self.match
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = False
        #self.myException.msg = self.errmsg
        self.mayIndexError = False
        self.caseless = caseless
        if caseless:
            self.caselessmatch = matchString.upper()
            identChars = identChars.upper()
        self.identChars = set(identChars)

    def parseImpl( self, instring, loc, doActions=True ):
        if self.caseless:
            if ( (instring[ loc:loc+self.matchLen ].upper() == self.caselessmatch) and
                 (loc >= len(instring)-self.matchLen or instring[loc+self.matchLen].upper() not in self.identChars) and
                 (loc == 0 or instring[loc-1].upper() not in self.identChars) ):
                return loc+self.matchLen, self.match
        else:
            if (instring[loc] == self.firstMatchChar and
                (self.matchLen==1 or instring.startswith(self.match,loc)) and
                (loc >= len(instring)-self.matchLen or instring[loc+self.matchLen] not in self.identChars) and
                (loc == 0 or instring[loc-1] not in self.identChars) ):
                return loc+self.matchLen, self.match
        raise ParseException( instring, loc, self.errmsg, self )

    def copy(self):
        c = super(Keyword,self).copy()
        c.identChars = Keyword.DEFAULT_KEYWORD_CHARS
        return c

    def setDefaultKeywordChars( chars ):
        """Overrides the default Keyword chars
        """
        Keyword.DEFAULT_KEYWORD_CHARS = chars
    setDefaultKeywordChars = staticmethod(setDefaultKeywordChars)

class CaselessLiteral(Literal):
    """Token to match a specified string, ignoring case of letters.
       Note: the matched results will always be in the case of the given
       match string, NOT the case of the input text.
    """
    def __init__( self, matchString ):
        super(CaselessLiteral,self).__init__( matchString.upper() )
        # Preserve the defining literal.
        self.returnString = matchString
        self.name = "'%s'" % self.returnString
        self.errmsg = "Expected " + self.name
        #self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions=True ):
        if instring[ loc:loc+self.matchLen ].upper() == self.match:
            return loc+self.matchLen, self.returnString
        raise ParseException( instring, loc, self.errmsg, self )

class CaselessKeyword(Keyword):
    def __init__( self, matchString, identChars=Keyword.DEFAULT_KEYWORD_CHARS ):
        super(CaselessKeyword,self).__init__( matchString, identChars, caseless=True )

    def parseImpl( self, instring, loc, doActions=True ):
        if ( (instring[ loc:loc+self.matchLen ].upper() == self.caselessmatch) and
             (loc >= len(instring)-self.matchLen or instring[loc+self.matchLen].upper() not in self.identChars) ):
            return loc+self.matchLen, self.match
        raise ParseException( instring, loc, self.errmsg, self )

class Word(Token):
    """Token for matching words composed of allowed character sets.
       Defined with string containing all allowed initial characters,
       an optional string containing allowed body characters (if omitted,
       defaults to the initial character set), and an optional minimum,
       maximum, and/or exact length.  The default value for C{min} is 1 (a
       minimum value < 1 is not valid); the default values for C{max} and C{exact}
       are 0, meaning no maximum or exact length restriction.
    """
    def __init__( self, initChars, bodyChars=None, min=1, max=0, exact=0, asKeyword=False ):
        super(Word,self).__init__()
        self.initCharsOrig = initChars
        self.initChars = set(initChars)
        if bodyChars :
            self.bodyCharsOrig = bodyChars
            self.bodyChars = set(bodyChars)
        else:
            self.bodyCharsOrig = initChars
            self.bodyChars = set(initChars)

        self.maxSpecified = max > 0

        if min < 1:
            raise ValueError("cannot specify a minimum length < 1; use Optional(Word()) if zero-length word is permitted")

        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = _MAX_INT

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        #self.myException.msg = self.errmsg
        self.mayIndexError = False
        self.asKeyword = asKeyword

        if ' ' not in self.initCharsOrig+self.bodyCharsOrig and (min==1 and max==0 and exact==0):
            if self.bodyCharsOrig == self.initCharsOrig:
                self.reString = "[%s]+" % _escapeRegexRangeChars(self.initCharsOrig)
            elif len(self.bodyCharsOrig) == 1:
                self.reString = "%s[%s]*" % \
                                      (re.escape(self.initCharsOrig),
                                      _escapeRegexRangeChars(self.bodyCharsOrig),)
            else:
                self.reString = "[%s][%s]*" % \
                                      (_escapeRegexRangeChars(self.initCharsOrig),
                                      _escapeRegexRangeChars(self.bodyCharsOrig),)
            if self.asKeyword:
                self.reString = r"\b"+self.reString+r"\b"
            try:
                self.re = re.compile( self.reString )
            except:
                self.re = None

    def parseImpl( self, instring, loc, doActions=True ):
        if self.re:
            result = self.re.match(instring,loc)
            if not result:
                raise ParseException(instring, loc, self.errmsg, self)

            loc = result.end()
            return loc,result.group()

        if not(instring[ loc ] in self.initChars):
            raise ParseException( instring, loc, self.errmsg, self )
        start = loc
        loc += 1
        instrlen = len(instring)
        bodychars = self.bodyChars
        maxloc = start + self.maxLen
        maxloc = min( maxloc, instrlen )
        while loc < maxloc and instring[loc] in bodychars:
            loc += 1

        throwException = False
        if loc - start < self.minLen:
            throwException = True
        if self.maxSpecified and loc < instrlen and instring[loc] in bodychars:
            throwException = True
        if self.asKeyword:
            if (start>0 and instring[start-1] in bodychars) or (loc<instrlen and instring[loc] in bodychars):
                throwException = True

        if throwException:
            raise ParseException( instring, loc, self.errmsg, self )

        return loc, instring[start:loc]

    def __str__( self ):
        try:
            return super(Word,self).__str__()
        except:
            pass


        if self.strRepr is None:

            def charsAsStr(s):
                if len(s)>4:
                    return s[:4]+"..."
                else:
                    return s

            if ( self.initCharsOrig != self.bodyCharsOrig ):
                self.strRepr = "W:(%s,%s)" % ( charsAsStr(self.initCharsOrig), charsAsStr(self.bodyCharsOrig) )
            else:
                self.strRepr = "W:(%s)" % charsAsStr(self.initCharsOrig)

        return self.strRepr


class Regex(Token):
    """Token for matching strings that match a given regular expression.
       Defined with string specifying the regular expression in a form recognized by the inbuilt Python re module.
    """
    compiledREtype = type(re.compile("[A-Z]"))
    def __init__( self, pattern, flags=0):
        """The parameters pattern and flags are passed to the re.compile() function as-is. See the Python re module for an explanation of the acceptable patterns and flags."""
        super(Regex,self).__init__()

        if isinstance(pattern, basestring):
            if len(pattern) == 0:
                warnings.warn("null string passed to Regex; use Empty() instead",
                        SyntaxWarning, stacklevel=2)

            self.pattern = pattern
            self.flags = flags

            try:
                self.re = re.compile(self.pattern, self.flags)
                self.reString = self.pattern
            except sre_constants.error:
                warnings.warn("invalid pattern (%s) passed to Regex" % pattern,
                    SyntaxWarning, stacklevel=2)
                raise

        elif isinstance(pattern, Regex.compiledREtype):
            self.re = pattern
            self.pattern = \
            self.reString = str(pattern)
            self.flags = flags

        else:
            raise ValueError("Regex may only be constructed with a string or a compiled RE object")

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        #self.myException.msg = self.errmsg
        self.mayIndexError = False
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        result = self.re.match(instring,loc)
        if not result:
            raise ParseException(instring, loc, self.errmsg, self)

        loc = result.end()
        d = result.groupdict()
        ret = ParseResults(result.group())
        if d:
            for k in d:
                ret[k] = d[k]
        return loc,ret

    def __str__( self ):
        try:
            return super(Regex,self).__str__()
        except:
            pass

        if self.strRepr is None:
            self.strRepr = "Re:(%s)" % repr(self.pattern)

        return self.strRepr


class QuotedString(Token):
    """Token for matching strings that are delimited by quoting characters.
    """
    def __init__( self, quoteChar, escChar=None, escQuote=None, multiline=False, unquoteResults=True, endQuoteChar=None):
        """
           Defined with the following parameters:
            - quoteChar - string of one or more characters defining the quote delimiting string
            - escChar - character to escape quotes, typically backslash (default=None)
            - escQuote - special quote sequence to escape an embedded quote string (such as SQL's "" to escape an embedded ") (default=None)
            - multiline - boolean indicating whether quotes can span multiple lines (default=False)
            - unquoteResults - boolean indicating whether the matched text should be unquoted (default=True)
            - endQuoteChar - string of one or more characters defining the end of the quote delimited string (default=None => same as quoteChar)
        """
        super(QuotedString,self).__init__()

        # remove white space from quote chars - wont work anyway
        quoteChar = quoteChar.strip()
        if len(quoteChar) == 0:
            warnings.warn("quoteChar cannot be the empty string",SyntaxWarning,stacklevel=2)
            raise SyntaxError()

        if endQuoteChar is None:
            endQuoteChar = quoteChar
        else:
            endQuoteChar = endQuoteChar.strip()
            if len(endQuoteChar) == 0:
                warnings.warn("endQuoteChar cannot be the empty string",SyntaxWarning,stacklevel=2)
                raise SyntaxError()

        self.quoteChar = quoteChar
        self.quoteCharLen = len(quoteChar)
        self.firstQuoteChar = quoteChar[0]
        self.endQuoteChar = endQuoteChar
        self.endQuoteCharLen = len(endQuoteChar)
        self.escChar = escChar
        self.escQuote = escQuote
        self.unquoteResults = unquoteResults

        if multiline:
            self.flags = re.MULTILINE | re.DOTALL
            self.pattern = r'%s(?:[^%s%s]' % \
                ( re.escape(self.quoteChar),
                  _escapeRegexRangeChars(self.endQuoteChar[0]),
                  (escChar is not None and _escapeRegexRangeChars(escChar) or '') )
        else:
            self.flags = 0
            self.pattern = r'%s(?:[^%s\n\r%s]' % \
                ( re.escape(self.quoteChar),
                  _escapeRegexRangeChars(self.endQuoteChar[0]),
                  (escChar is not None and _escapeRegexRangeChars(escChar) or '') )
        if len(self.endQuoteChar) > 1:
            self.pattern += (
                '|(?:' + ')|(?:'.join(["%s[^%s]" % (re.escape(self.endQuoteChar[:i]),
                                               _escapeRegexRangeChars(self.endQuoteChar[i]))
                                    for i in range(len(self.endQuoteChar)-1,0,-1)]) + ')'
                )
        if escQuote:
            self.pattern += (r'|(?:%s)' % re.escape(escQuote))
        if escChar:
            self.pattern += (r'|(?:%s.)' % re.escape(escChar))
            self.escCharReplacePattern = re.escape(self.escChar)+"(.)"
        self.pattern += (r')*%s' % re.escape(self.endQuoteChar))

        try:
            self.re = re.compile(self.pattern, self.flags)
            self.reString = self.pattern
        except sre_constants.error:
            warnings.warn("invalid pattern (%s) passed to Regex" % self.pattern,
                SyntaxWarning, stacklevel=2)
            raise

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        #self.myException.msg = self.errmsg
        self.mayIndexError = False
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        result = instring[loc] == self.firstQuoteChar and self.re.match(instring,loc) or None
        if not result:
            raise ParseException(instring, loc, self.errmsg, self)

        loc = result.end()
        ret = result.group()

        if self.unquoteResults:

            # strip off quotes
            ret = ret[self.quoteCharLen:-self.endQuoteCharLen]

            if isinstance(ret,basestring):
                # replace escaped characters
                if self.escChar:
                    ret = re.sub(self.escCharReplacePattern,"\g<1>",ret)

                # replace escaped quotes
                if self.escQuote:
                    ret = ret.replace(self.escQuote, self.endQuoteChar)

        return loc, ret

    def __str__( self ):
        try:
            return super(QuotedString,self).__str__()
        except:
            pass

        if self.strRepr is None:
            self.strRepr = "quoted string, starting with %s ending with %s" % (self.quoteChar, self.endQuoteChar)

        return self.strRepr


class CharsNotIn(Token):
    """Token for matching words composed of characters *not* in a given set.
       Defined with string containing all disallowed characters, and an optional
       minimum, maximum, and/or exact length.  The default value for C{min} is 1 (a
       minimum value < 1 is not valid); the default values for C{max} and C{exact}
       are 0, meaning no maximum or exact length restriction.
    """
    def __init__( self, notChars, min=1, max=0, exact=0 ):
        super(CharsNotIn,self).__init__()
        self.skipWhitespace = False
        self.notChars = notChars

        if min < 1:
            raise ValueError("cannot specify a minimum length < 1; use Optional(CharsNotIn()) if zero-length char group is permitted")

        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = _MAX_INT

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = ( self.minLen == 0 )
        #self.myException.msg = self.errmsg
        self.mayIndexError = False

    def parseImpl( self, instring, loc, doActions=True ):
        if instring[loc] in self.notChars:
            raise ParseException( instring, loc, self.errmsg, self )

        start = loc
        loc += 1
        notchars = self.notChars
        maxlen = min( start+self.maxLen, len(instring) )
        while loc < maxlen and \
              (instring[loc] not in notchars):
            loc += 1

        if loc - start < self.minLen:
            raise ParseException( instring, loc, self.errmsg, self )

        return loc, instring[start:loc]

    def __str__( self ):
        try:
            return super(CharsNotIn, self).__str__()
        except:
            pass

        if self.strRepr is None:
            if len(self.notChars) > 4:
                self.strRepr = "!W:(%s...)" % self.notChars[:4]
            else:
                self.strRepr = "!W:(%s)" % self.notChars

        return self.strRepr

class White(Token):
    """Special matching class for matching whitespace.  Normally, whitespace is ignored
       by pyparsing grammars.  This class is included when some whitespace structures
       are significant.  Define with a string containing the whitespace characters to be
       matched; default is C{" \\t\\r\\n"}.  Also takes optional C{min}, C{max}, and C{exact} arguments,
       as defined for the C{Word} class."""
    whiteStrs = {
        " " : "<SPC>",
        "\t": "<TAB>",
        "\n": "<LF>",
        "\r": "<CR>",
        "\f": "<FF>",
        }
    def __init__(self, ws=" \t\r\n", min=1, max=0, exact=0):
        super(White,self).__init__()
        self.matchWhite = ws
        self.setWhitespaceChars( "".join([c for c in self.whiteChars if c not in self.matchWhite]) )
        #~ self.leaveWhitespace()
        self.name = ("".join([White.whiteStrs[c] for c in self.matchWhite]))
        self.mayReturnEmpty = True
        self.errmsg = "Expected " + self.name
        #self.myException.msg = self.errmsg

        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = _MAX_INT

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact

    def parseImpl( self, instring, loc, doActions=True ):
        if not(instring[ loc ] in self.matchWhite):
            raise ParseException( instring, loc, self.errmsg, self )
        start = loc
        loc += 1
        maxloc = start + self.maxLen
        maxloc = min( maxloc, len(instring) )
        while loc < maxloc and instring[loc] in self.matchWhite:
            loc += 1

        if loc - start < self.minLen:
            raise ParseException( instring, loc, self.errmsg, self )

        return loc, instring[start:loc]


class _PositionToken(Token):
    def __init__( self ):
        super(_PositionToken,self).__init__()
        self.name=self.__class__.__name__
        self.mayReturnEmpty = True
        self.mayIndexError = False

class GoToColumn(_PositionToken):
    """Token to advance to a specific column of input text; useful for tabular report scraping."""
    def __init__( self, colno ):
        super(GoToColumn,self).__init__()
        self.col = colno

    def preParse( self, instring, loc ):
        if col(loc,instring) != self.col:
            instrlen = len(instring)
            if self.ignoreExprs:
                loc = self._skipIgnorables( instring, loc )
            while loc < instrlen and instring[loc].isspace() and col( loc, instring ) != self.col :
                loc += 1
        return loc

    def parseImpl( self, instring, loc, doActions=True ):
        thiscol = col( loc, instring )
        if thiscol > self.col:
            raise ParseException( instring, loc, "Text not in expected column", self )
        newloc = loc + self.col - thiscol
        ret = instring[ loc: newloc ]
        return newloc, ret

class LineStart(_PositionToken):
    """Matches if current position is at the beginning of a line within the parse string"""
    def __init__( self ):
        super(LineStart,self).__init__()
        self.setWhitespaceChars( ParserElement.DEFAULT_WHITE_CHARS.replace("\n","") )
        self.errmsg = "Expected start of line"
        #self.myException.msg = self.errmsg

    def preParse( self, instring, loc ):
        preloc = super(LineStart,self).preParse(instring,loc)
        if instring[preloc] == "\n":
            loc += 1
        return loc

    def parseImpl( self, instring, loc, doActions=True ):
        if not( loc==0 or
            (loc == self.preParse( instring, 0 )) or
            (instring[loc-1] == "\n") ): #col(loc, instring) != 1:
            raise ParseException( instring, loc, self.errmsg, self )
        return loc, []

class LineEnd(_PositionToken):
    """Matches if current position is at the end of a line within the parse string"""
    def __init__( self ):
        super(LineEnd,self).__init__()
        self.setWhitespaceChars( ParserElement.DEFAULT_WHITE_CHARS.replace("\n","") )
        self.errmsg = "Expected end of line"
        #self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions=True ):
        if loc<len(instring):
            if instring[loc] == "\n":
                return loc+1, "\n"
            else:
                raise ParseException( instring, loc, self.errmsg, self )
        elif loc == len(instring):
            return loc+1, []
        else:
            raise ParseException( instring, loc, self.errmsg, self )

class StringStart(_PositionToken):
    """Matches if current position is at the beginning of the parse string"""
    def __init__( self ):
        super(StringStart,self).__init__()
        self.errmsg = "Expected start of text"
        #self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions=True ):
        if loc != 0:
            # see if entire string up to here is just whitespace and ignoreables
            if loc != self.preParse( instring, 0 ):
                raise ParseException( instring, loc, self.errmsg, self )
        return loc, []

class StringEnd(_PositionToken):
    """Matches if current position is at the end of the parse string"""
    def __init__( self ):
        super(StringEnd,self).__init__()
        self.errmsg = "Expected end of text"
        #self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions=True ):
        if loc < len(instring):
            raise ParseException( instring, loc, self.errmsg, self )
        elif loc == len(instring):
            return loc+1, []
        elif loc > len(instring):
            return loc, []
        else:
            raise ParseException( instring, loc, self.errmsg, self )

class WordStart(_PositionToken):
    """Matches if the current position is at the beginning of a Word, and
       is not preceded by any character in a given set of wordChars
       (default=C{printables}). To emulate the C{\b} behavior of regular expressions,
       use C{WordStart(alphanums)}. C{WordStart} will also match at the beginning of
       the string being parsed, or at the beginning of a line.
    """
    def __init__(self, wordChars = printables):
        super(WordStart,self).__init__()
        self.wordChars = set(wordChars)
        self.errmsg = "Not at the start of a word"

    def parseImpl(self, instring, loc, doActions=True ):
        if loc != 0:
            if (instring[loc-1] in self.wordChars or
                instring[loc] not in self.wordChars):
                raise ParseException( instring, loc, self.errmsg, self )
        return loc, []

class WordEnd(_PositionToken):
    """Matches if the current position is at the end of a Word, and
       is not followed by any character in a given set of wordChars
       (default=C{printables}). To emulate the C{\b} behavior of regular expressions,
       use C{WordEnd(alphanums)}. C{WordEnd} will also match at the end of
       the string being parsed, or at the end of a line.
    """
    def __init__(self, wordChars = printables):
        super(WordEnd,self).__init__()
        self.wordChars = set(wordChars)
        self.skipWhitespace = False
        self.errmsg = "Not at the end of a word"

    def parseImpl(self, instring, loc, doActions=True ):
        instrlen = len(instring)
        if instrlen>0 and loc<instrlen:
            if (instring[loc] in self.wordChars or
                instring[loc-1] not in self.wordChars):
                raise ParseException( instring, loc, self.errmsg, self )
        return loc, []


class ParseExpression(ParserElement):
    """Abstract subclass of ParserElement, for combining and post-processing parsed tokens."""
    def __init__( self, exprs, savelist = False ):
        super(ParseExpression,self).__init__(savelist)
        if isinstance( exprs, list ):
            self.exprs = exprs
        elif isinstance( exprs, basestring ):
            self.exprs = [ Literal( exprs ) ]
        else:
            try:
                self.exprs = list( exprs )
            except TypeError:
                self.exprs = [ exprs ]
        self.callPreparse = False

    def __getitem__( self, i ):
        return self.exprs[i]

    def append( self, other ):
        self.exprs.append( other )
        self.strRepr = None
        return self

    def leaveWhitespace( self ):
        """Extends leaveWhitespace defined in base class, and also invokes leaveWhitespace on
           all contained expressions."""
        self.skipWhitespace = False
        self.exprs = [ e.copy() for e in self.exprs ]
        for e in self.exprs:
            e.leaveWhitespace()
        return self

    def ignore( self, other ):
        if isinstance( other, Suppress ):
            if other not in self.ignoreExprs:
                super( ParseExpression, self).ignore( other )
                for e in self.exprs:
                    e.ignore( self.ignoreExprs[-1] )
        else:
            super( ParseExpression, self).ignore( other )
            for e in self.exprs:
                e.ignore( self.ignoreExprs[-1] )
        return self

    def __str__( self ):
        try:
            return super(ParseExpression,self).__str__()
        except:
            pass

        if self.strRepr is None:
            self.strRepr = "%s:(%s)" % ( self.__class__.__name__, _ustr(self.exprs) )
        return self.strRepr

    def streamline( self ):
        super(ParseExpression,self).streamline()

        for e in self.exprs:
            e.streamline()

        # collapse nested And's of the form And( And( And( a,b), c), d) to And( a,b,c,d )
        # but only if there are no parse actions or resultsNames on the nested And's
        # (likewise for Or's and MatchFirst's)
        if ( len(self.exprs) == 2 ):
            other = self.exprs[0]
            if ( isinstance( other, self.__class__ ) and
                  not(other.parseAction) and
                  other.resultsName is None and
                  not other.debug ):
                self.exprs = other.exprs[:] + [ self.exprs[1] ]
                self.strRepr = None
                self.mayReturnEmpty |= other.mayReturnEmpty
                self.mayIndexError  |= other.mayIndexError

            other = self.exprs[-1]
            if ( isinstance( other, self.__class__ ) and
                  not(other.parseAction) and
                  other.resultsName is None and
                  not other.debug ):
                self.exprs = self.exprs[:-1] + other.exprs[:]
                self.strRepr = None
                self.mayReturnEmpty |= other.mayReturnEmpty
                self.mayIndexError  |= other.mayIndexError

        return self

    def setResultsName( self, name, listAllMatches=False ):
        ret = super(ParseExpression,self).setResultsName(name,listAllMatches)
        return ret

    def validate( self, validateTrace=[] ):
        tmp = validateTrace[:]+[self]
        for e in self.exprs:
            e.validate(tmp)
        self.checkRecursion( [] )

class And(ParseExpression):
    """Requires all given C{ParseExpressions} to be found in the given order.
       Expressions may be separated by whitespace.
       May be constructed using the '+' operator.
    """

    class _ErrorStop(Empty):
        def __init__(self, *args, **kwargs):
            super(Empty,self).__init__(*args, **kwargs)
            self.leaveWhitespace()

    def __init__( self, exprs, savelist = True ):
        super(And,self).__init__(exprs, savelist)
        self.mayReturnEmpty = True
        for e in self.exprs:
            if not e.mayReturnEmpty:
                self.mayReturnEmpty = False
                break
        self.setWhitespaceChars( exprs[0].whiteChars )
        self.skipWhitespace = exprs[0].skipWhitespace
        self.callPreparse = True

    def parseImpl( self, instring, loc, doActions=True ):
        # pass False as last arg to _parse for first element, since we already
        # pre-parsed the string as part of our And pre-parsing
        loc, resultlist = self.exprs[0]._parse( instring, loc, doActions, callPreParse=False )
        errorStop = False
        for e in self.exprs[1:]:
            if isinstance(e, And._ErrorStop):
                errorStop = True
                continue
            if errorStop:
                try:
                    loc, exprtokens = e._parse( instring, loc, doActions )
                except ParseSyntaxException:
                    raise
                except ParseBaseException as e:
                    e.__traceback__ = None
                    raise ParseSyntaxException(e)
                except IndexError:
                    raise ParseSyntaxException( ParseException(instring, len(instring), self.errmsg, self) )
            else:
                loc, exprtokens = e._parse( instring, loc, doActions )
            if exprtokens or exprtokens.keys():
                resultlist += exprtokens
        return loc, resultlist

    def __iadd__(self, other ):
        if isinstance( other, basestring ):
            other = Literal( other )
        return self.append( other ) #And( [ self, other ] )

    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )
            if not e.mayReturnEmpty:
                break

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " ".join( [ _ustr(e) for e in self.exprs ] ) + "}"

        return self.strRepr


class Or(ParseExpression):
    """Requires that at least one C{ParseExpression} is found.
       If two expressions match, the expression that matches the longest string will be used.
       May be constructed using the '^' operator.
    """
    def __init__( self, exprs, savelist = False ):
        super(Or,self).__init__(exprs, savelist)
        self.mayReturnEmpty = False
        for e in self.exprs:
            if e.mayReturnEmpty:
                self.mayReturnEmpty = True
                break

    def parseImpl( self, instring, loc, doActions=True ):
        maxExcLoc = -1
        maxMatchLoc = -1
        maxException = None
        for e in self.exprs:
            try:
                loc2 = e.tryParse( instring, loc )
            except ParseException as err:
                err.__traceback__ = None
                if err.loc > maxExcLoc:
                    maxException = err
                    maxExcLoc = err.loc
            except IndexError:
                if len(instring) > maxExcLoc:
                    maxException = ParseException(instring,len(instring),e.errmsg,self)
                    maxExcLoc = len(instring)
            else:
                if loc2 > maxMatchLoc:
                    maxMatchLoc = loc2
                    maxMatchExp = e

        if maxMatchLoc < 0:
            if maxException is not None:
                maxException.__traceback__ = None
                raise maxException
            else:
                raise ParseException(instring, loc, "no defined alternatives to match", self)

        return maxMatchExp._parse( instring, loc, doActions )

    def __ixor__(self, other ):
        if isinstance( other, basestring ):
            other = Literal( other )
        return self.append( other ) #Or( [ self, other ] )

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " ^ ".join( [ _ustr(e) for e in self.exprs ] ) + "}"

        return self.strRepr

    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )


class MatchFirst(ParseExpression):
    """Requires that at least one C{ParseExpression} is found.
       If two expressions match, the first one listed is the one that will match.
       May be constructed using the '|' operator.
    """
    def __init__( self, exprs, savelist = False ):
        super(MatchFirst,self).__init__(exprs, savelist)
        if exprs:
            self.mayReturnEmpty = False
            for e in self.exprs:
                if e.mayReturnEmpty:
                    self.mayReturnEmpty = True
                    break
        else:
            self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        maxExcLoc = -1
        maxException = None
        for e in self.exprs:
            try:
                ret = e._parse( instring, loc, doActions )
                return ret
            except ParseException as err:
                err.__traceback__ = None
                if err.loc > maxExcLoc:
                    maxException = err
                    maxExcLoc = err.loc
            except IndexError:
                if len(instring) > maxExcLoc:
                    maxException = ParseException(instring,len(instring),e.errmsg,self)
                    maxExcLoc = len(instring)

        # only got here if no expression matched, raise exception for match that made it the furthest
        else:
            if maxException is not None:
                maxException.__traceback__ = None
                raise maxException
            else:
                raise ParseException(instring, loc, "no defined alternatives to match", self)

    def __ior__(self, other ):
        if isinstance( other, basestring ):
            other = Literal( other )
        return self.append( other ) #MatchFirst( [ self, other ] )

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " | ".join( [ _ustr(e) for e in self.exprs ] ) + "}"

        return self.strRepr

    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )


class Each(ParseExpression):
    """Requires all given C{ParseExpressions} to be found, but in any order.
       Expressions may be separated by whitespace.
       May be constructed using the '&' operator.
    """
    def __init__( self, exprs, savelist = True ):
        super(Each,self).__init__(exprs, savelist)
        self.mayReturnEmpty = True
        for e in self.exprs:
            if not e.mayReturnEmpty:
                self.mayReturnEmpty = False
                break
        self.skipWhitespace = True
        self.initExprGroups = True

    def parseImpl( self, instring, loc, doActions=True ):
        if self.initExprGroups:
            opt1 = [ e.expr for e in self.exprs if isinstance(e,Optional) ]
            opt2 = [ e for e in self.exprs if e.mayReturnEmpty and e not in opt1 ]
            self.optionals = opt1 + opt2
            self.multioptionals = [ e.expr for e in self.exprs if isinstance(e,ZeroOrMore) ]
            self.multirequired = [ e.expr for e in self.exprs if isinstance(e,OneOrMore) ]
            self.required = [ e for e in self.exprs if not isinstance(e,(Optional,ZeroOrMore,OneOrMore)) ]
            self.required += self.multirequired
            self.initExprGroups = False
        tmpLoc = loc
        tmpReqd = self.required[:]
        tmpOpt  = self.optionals[:]
        matchOrder = []

        keepMatching = True
        while keepMatching:
            tmpExprs = tmpReqd + tmpOpt + self.multioptionals + self.multirequired
            failed = []
            for e in tmpExprs:
                try:
                    tmpLoc = e.tryParse( instring, tmpLoc )
                except ParseException:
                    failed.append(e)
                else:
                    matchOrder.append(e)
                    if e in tmpReqd:
                        tmpReqd.remove(e)
                    elif e in tmpOpt:
                        tmpOpt.remove(e)
            if len(failed) == len(tmpExprs):
                keepMatching = False

        if tmpReqd:
            missing = ", ".join( [ _ustr(e) for e in tmpReqd ] )
            raise ParseException(instring,loc,"Missing one or more required elements (%s)" % missing )

        # add any unmatched Optionals, in case they have default values defined
        matchOrder += list(e for e in self.exprs if isinstance(e,Optional) and e.expr in tmpOpt)

        resultlist = []
        for e in matchOrder:
            loc,results = e._parse(instring,loc,doActions)
            resultlist.append(results)

        finalResults = ParseResults([])
        for r in resultlist:
            dups = {}
            for k in r.keys():
                if k in finalResults.keys():
                    tmp = ParseResults(finalResults[k])
                    tmp += ParseResults(r[k])
                    dups[k] = tmp
            finalResults += ParseResults(r)
            for k,v in dups.items():
                finalResults[k] = v
        return loc, finalResults

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " & ".join( [ _ustr(e) for e in self.exprs ] ) + "}"

        return self.strRepr

    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )


class ParseElementEnhance(ParserElement):
    """Abstract subclass of C{ParserElement}, for combining and post-processing parsed tokens."""
    def __init__( self, expr, savelist=False ):
        super(ParseElementEnhance,self).__init__(savelist)
        if isinstance( expr, basestring ):
            expr = Literal(expr)
        self.expr = expr
        self.strRepr = None
        if expr is not None:
            self.mayIndexError = expr.mayIndexError
            self.mayReturnEmpty = expr.mayReturnEmpty
            self.setWhitespaceChars( expr.whiteChars )
            self.skipWhitespace = expr.skipWhitespace
            self.saveAsList = expr.saveAsList
            self.callPreparse = expr.callPreparse
            self.ignoreExprs.extend(expr.ignoreExprs)

    def parseImpl( self, instring, loc, doActions=True ):
        if self.expr is not None:
            return self.expr._parse( instring, loc, doActions, callPreParse=False )
        else:
            raise ParseException("",loc,self.errmsg,self)

    def leaveWhitespace( self ):
        self.skipWhitespace = False
        self.expr = self.expr.copy()
        if self.expr is not None:
            self.expr.leaveWhitespace()
        return self

    def ignore( self, other ):
        if isinstance( other, Suppress ):
            if other not in self.ignoreExprs:
                super( ParseElementEnhance, self).ignore( other )
                if self.expr is not None:
                    self.expr.ignore( self.ignoreExprs[-1] )
        else:
            super( ParseElementEnhance, self).ignore( other )
            if self.expr is not None:
                self.expr.ignore( self.ignoreExprs[-1] )
        return self

    def streamline( self ):
        super(ParseElementEnhance,self).streamline()
        if self.expr is not None:
            self.expr.streamline()
        return self

    def checkRecursion( self, parseElementList ):
        if self in parseElementList:
            raise RecursiveGrammarException( parseElementList+[self] )
        subRecCheckList = parseElementList[:] + [ self ]
        if self.expr is not None:
            self.expr.checkRecursion( subRecCheckList )

    def validate( self, validateTrace=[] ):
        tmp = validateTrace[:]+[self]
        if self.expr is not None:
            self.expr.validate(tmp)
        self.checkRecursion( [] )

    def __str__( self ):
        try:
            return super(ParseElementEnhance,self).__str__()
        except:
            pass

        if self.strRepr is None and self.expr is not None:
            self.strRepr = "%s:(%s)" % ( self.__class__.__name__, _ustr(self.expr) )
        return self.strRepr


class FollowedBy(ParseElementEnhance):
    """Lookahead matching of the given parse expression.  C{FollowedBy}
    does *not* advance the parsing position within the input string, it only
    verifies that the specified parse expression matches at the current
    position.  C{FollowedBy} always returns a null token list."""
    def __init__( self, expr ):
        super(FollowedBy,self).__init__(expr)
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        self.expr.tryParse( instring, loc )
        return loc, []


class NotAny(ParseElementEnhance):
    """Lookahead to disallow matching with the given parse expression.  C{NotAny}
    does *not* advance the parsing position within the input string, it only
    verifies that the specified parse expression does *not* match at the current
    position.  Also, C{NotAny} does *not* skip over leading whitespace. C{NotAny}
    always returns a null token list.  May be constructed using the '~' operator."""
    def __init__( self, expr ):
        super(NotAny,self).__init__(expr)
        #~ self.leaveWhitespace()
        self.skipWhitespace = False  # do NOT use self.leaveWhitespace(), don't want to propagate to exprs
        self.mayReturnEmpty = True
        self.errmsg = "Found unwanted token, "+_ustr(self.expr)
        #self.myException = ParseException("",0,self.errmsg,self)

    def parseImpl( self, instring, loc, doActions=True ):
        try:
            self.expr.tryParse( instring, loc )
        except (ParseException,IndexError):
            pass
        else:
            raise ParseException( instring, loc, self.errmsg, self )
        return loc, []

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "~{" + _ustr(self.expr) + "}"

        return self.strRepr


class ZeroOrMore(ParseElementEnhance):
    """Optional repetition of zero or more of the given expression."""
    def __init__( self, expr ):
        super(ZeroOrMore,self).__init__(expr)
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        tokens = []
        try:
            loc, tokens = self.expr._parse( instring, loc, doActions, callPreParse=False )
            hasIgnoreExprs = ( len(self.ignoreExprs) > 0 )
            while 1:
                if hasIgnoreExprs:
                    preloc = self._skipIgnorables( instring, loc )
                else:
                    preloc = loc
                loc, tmptokens = self.expr._parse( instring, preloc, doActions )
                if tmptokens or tmptokens.keys():
                    tokens += tmptokens
        except (ParseException,IndexError):
            pass

        return loc, tokens

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "[" + _ustr(self.expr) + "]..."

        return self.strRepr

    def setResultsName( self, name, listAllMatches=False ):
        ret = super(ZeroOrMore,self).setResultsName(name,listAllMatches)
        ret.saveAsList = True
        return ret


class OneOrMore(ParseElementEnhance):
    """Repetition of one or more of the given expression."""
    def parseImpl( self, instring, loc, doActions=True ):
        # must be at least one
        loc, tokens = self.expr._parse( instring, loc, doActions, callPreParse=False )
        try:
            hasIgnoreExprs = ( len(self.ignoreExprs) > 0 )
            while 1:
                if hasIgnoreExprs:
                    preloc = self._skipIgnorables( instring, loc )
                else:
                    preloc = loc
                loc, tmptokens = self.expr._parse( instring, preloc, doActions )
                if tmptokens or tmptokens.keys():
                    tokens += tmptokens
        except (ParseException,IndexError):
            pass

        return loc, tokens

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + _ustr(self.expr) + "}..."

        return self.strRepr

    def setResultsName( self, name, listAllMatches=False ):
        ret = super(OneOrMore,self).setResultsName(name,listAllMatches)
        ret.saveAsList = True
        return ret

class _NullToken(object):
    def __bool__(self):
        return False
    __nonzero__ = __bool__
    def __str__(self):
        return ""

_optionalNotMatched = _NullToken()
class Optional(ParseElementEnhance):
    """Optional matching of the given expression.
       A default return string can also be specified, if the optional expression
       is not found.
    """
    def __init__( self, exprs, default=_optionalNotMatched ):
        super(Optional,self).__init__( exprs, savelist=False )
        self.defaultValue = default
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        try:
            loc, tokens = self.expr._parse( instring, loc, doActions, callPreParse=False )
        except (ParseException,IndexError):
            if self.defaultValue is not _optionalNotMatched:
                if self.expr.resultsName:
                    tokens = ParseResults([ self.defaultValue ])
                    tokens[self.expr.resultsName] = self.defaultValue
                else:
                    tokens = [ self.defaultValue ]
            else:
                tokens = []
        return loc, tokens

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "[" + _ustr(self.expr) + "]"

        return self.strRepr


class SkipTo(ParseElementEnhance):
    """Token for skipping over all undefined text until the matched expression is found.
       If C{include} is set to true, the matched expression is also parsed (the skipped text
       and matched expression are returned as a 2-element list).  The C{ignore}
       argument is used to define grammars (typically quoted strings and comments) that
       might contain false matches.
    """
    def __init__( self, other, include=False, ignore=None, failOn=None ):
        super( SkipTo, self ).__init__( other )
        self.ignoreExpr = ignore
        self.mayReturnEmpty = True
        self.mayIndexError = False
        self.includeMatch = include
        self.asList = False
        if failOn is not None and isinstance(failOn, basestring):
            self.failOn = Literal(failOn)
        else:
            self.failOn = failOn
        self.errmsg = "No match found for "+_ustr(self.expr)
        #self.myException = ParseException("",0,self.errmsg,self)

    def parseImpl( self, instring, loc, doActions=True ):
        startLoc = loc
        instrlen = len(instring)
        expr = self.expr
        failParse = False
        while loc <= instrlen:
            try:
                if self.failOn:
                    try:
                        self.failOn.tryParse(instring, loc)
                    except ParseBaseException:
                        pass
                    else:
                        failParse = True
                        raise ParseException(instring, loc, "Found expression " + str(self.failOn))
                    failParse = False
                if self.ignoreExpr is not None:
                    while 1:
                        try:
                            loc = self.ignoreExpr.tryParse(instring,loc)
                            # print("found ignoreExpr, advance to", loc)
                        except ParseBaseException:
                            break
                expr._parse( instring, loc, doActions=False, callPreParse=False )
                skipText = instring[startLoc:loc]
                if self.includeMatch:
                    loc,mat = expr._parse(instring,loc,doActions,callPreParse=False)
                    if mat:
                        skipRes = ParseResults( skipText )
                        skipRes += mat
                        return loc, [ skipRes ]
                    else:
                        return loc, [ skipText ]
                else:
                    return loc, [ skipText ]
            except (ParseException,IndexError):
                if failParse:
                    raise
                else:
                    loc += 1
        raise ParseException( instring, loc, self.errmsg, self )

class Forward(ParseElementEnhance):
    """Forward declaration of an expression to be defined later -
       used for recursive grammars, such as algebraic infix notation.
       When the expression is known, it is assigned to the C{Forward} variable using the '<<' operator.

       Note: take care when assigning to C{Forward} not to overlook precedence of operators.
       Specifically, '|' has a lower precedence than '<<', so that::
          fwdExpr << a | b | c
       will actually be evaluated as::
          (fwdExpr << a) | b | c
       thereby leaving b and c out as parseable alternatives.  It is recommended that you
       explicitly group the values inserted into the C{Forward}::
          fwdExpr << (a | b | c)
    """
    def __init__( self, other=None ):
        super(Forward,self).__init__( other, savelist=False )

    def __lshift__( self, other ):
        if isinstance( other, basestring ):
            other = Literal(other)
        self.expr = other
        self.mayReturnEmpty = other.mayReturnEmpty
        self.strRepr = None
        self.mayIndexError = self.expr.mayIndexError
        self.mayReturnEmpty = self.expr.mayReturnEmpty
        self.setWhitespaceChars( self.expr.whiteChars )
        self.skipWhitespace = self.expr.skipWhitespace
        self.saveAsList = self.expr.saveAsList
        self.ignoreExprs.extend(self.expr.ignoreExprs)
        return None

    def leaveWhitespace( self ):
        self.skipWhitespace = False
        return self

    def streamline( self ):
        if not self.streamlined:
            self.streamlined = True
            if self.expr is not None:
                self.expr.streamline()
        return self

    def validate( self, validateTrace=[] ):
        if self not in validateTrace:
            tmp = validateTrace[:]+[self]
            if self.expr is not None:
                self.expr.validate(tmp)
        self.checkRecursion([])

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        self._revertClass = self.__class__
        self.__class__ = _ForwardNoRecurse
        try:
            if self.expr is not None:
                retString = _ustr(self.expr)
            else:
                retString = "None"
        finally:
            self.__class__ = self._revertClass
        return self.__class__.__name__ + ": " + retString

    def copy(self):
        if self.expr is not None:
            return super(Forward,self).copy()
        else:
            ret = Forward()
            ret << self
            return ret

class _ForwardNoRecurse(Forward):
    def __str__( self ):
        return "..."

class TokenConverter(ParseElementEnhance):
    """Abstract subclass of ParseExpression, for converting parsed results."""
    def __init__( self, expr, savelist=False ):
        super(TokenConverter,self).__init__( expr )#, savelist )
        self.saveAsList = False

class Upcase(TokenConverter):
    """Converter to upper case all matching tokens."""
    def __init__(self, *args):
        super(Upcase,self).__init__(*args)
        warnings.warn("Upcase class is deprecated, use upcaseTokens parse action instead",
                       DeprecationWarning,stacklevel=2)

    def postParse( self, instring, loc, tokenlist ):
        return list(map( string.upper, tokenlist ))


class Combine(TokenConverter):
    """Converter to concatenate all matching tokens to a single string.
       By default, the matching patterns must also be contiguous in the input string;
       this can be disabled by specifying C{'adjacent=False'} in the constructor.
    """
    def __init__( self, expr, joinString="", adjacent=True ):
        super(Combine,self).__init__( expr )
        # suppress whitespace-stripping in contained parse expressions, but re-enable it on the Combine itself
        if adjacent:
            self.leaveWhitespace()
        self.adjacent = adjacent
        self.skipWhitespace = True
        self.joinString = joinString
        self.callPreparse = True

    def ignore( self, other ):
        if self.adjacent:
            ParserElement.ignore(self, other)
        else:
            super( Combine, self).ignore( other )
        return self

    def postParse( self, instring, loc, tokenlist ):
        retToks = tokenlist.copy()
        del retToks[:]
        retToks += ParseResults([ "".join(tokenlist._asStringList(self.joinString)) ], modal=self.modalResults)

        if self.resultsName and len(retToks.keys())>0:
            return [ retToks ]
        else:
            return retToks

class Group(TokenConverter):
    """Converter to return the matched tokens as a list - useful for returning tokens of ZeroOrMore and OneOrMore expressions."""
    def __init__( self, expr ):
        super(Group,self).__init__( expr )
        self.saveAsList = True

    def postParse( self, instring, loc, tokenlist ):
        return [ tokenlist ]

class Dict(TokenConverter):
    """Converter to return a repetitive expression as a list, but also as a dictionary.
       Each element can also be referenced using the first token in the expression as its key.
       Useful for tabular report scraping when the first column can be used as a item key.
    """
    def __init__( self, exprs ):
        super(Dict,self).__init__( exprs )
        self.saveAsList = True

    def postParse( self, instring, loc, tokenlist ):
        for i,tok in enumerate(tokenlist):
            if len(tok) == 0:
                continue
            ikey = tok[0]
            if isinstance(ikey,int):
                ikey = _ustr(tok[0]).strip()
            if len(tok)==1:
                tokenlist[ikey] = _ParseResultsWithOffset("",i)
            elif len(tok)==2 and not isinstance(tok[1],ParseResults):
                tokenlist[ikey] = _ParseResultsWithOffset(tok[1],i)
            else:
                dictvalue = tok.copy() #ParseResults(i)
                del dictvalue[0]
                if len(dictvalue)!= 1 or (isinstance(dictvalue,ParseResults) and dictvalue.keys()):
                    tokenlist[ikey] = _ParseResultsWithOffset(dictvalue,i)
                else:
                    tokenlist[ikey] = _ParseResultsWithOffset(dictvalue[0],i)

        if self.resultsName:
            return [ tokenlist ]
        else:
            return tokenlist


class Suppress(TokenConverter):
    """Converter for ignoring the results of a parsed expression."""
    def postParse( self, instring, loc, tokenlist ):
        return []

    def suppress( self ):
        return self


class OnlyOnce(object):
    """Wrapper for parse actions, to ensure they are only called once."""
    def __init__(self, methodCall):
        self.callable = ParserElement._normalizeParseActionArgs(methodCall)
        self.called = False
    def __call__(self,s,l,t):
        if not self.called:
            results = self.callable(s,l,t)
            self.called = True
            return results
        raise ParseException(s,l,"")
    def reset(self):
        self.called = False

def traceParseAction(f):
    """Decorator for debugging parse actions."""
    f = ParserElement._normalizeParseActionArgs(f)
    def z(*paArgs):
        thisFunc = f.func_name
        s,l,t = paArgs[-3:]
        if len(paArgs)>3:
            thisFunc = paArgs[0].__class__.__name__ + '.' + thisFunc
        sys.stderr.write( ">>entering %s(line: '%s', %d, %s)\n" % (thisFunc,line(l,s),l,t) )
        try:
            ret = f(*paArgs)
        except Exception as exc:
            sys.stderr.write( "<<leaving %s (exception: %s)\n" % (thisFunc,exc) )
            raise exc
        sys.stderr.write( "<<leaving %s (ret: %s)\n" % (thisFunc,ret) )
        return ret
    try:
        z.__name__ = f.__name__
    except AttributeError:
        pass
    return z

#
# global helpers
#
def delimitedList( expr, delim=",", combine=False ):
    """Helper to define a delimited list of expressions - the delimiter defaults to ','.
       By default, the list elements and delimiters can have intervening whitespace, and
       comments, but this can be overridden by passing C{combine=True} in the constructor.
       If C{combine} is set to True, the matching tokens are returned as a single token
       string, with the delimiters included; otherwise, the matching tokens are returned
       as a list of tokens, with the delimiters suppressed.
    """
    dlName = _ustr(expr)+" ["+_ustr(delim)+" "+_ustr(expr)+"]..."
    if combine:
        return Combine( expr + ZeroOrMore( delim + expr ) ).setName(dlName)
    else:
        return ( expr + ZeroOrMore( Suppress( delim ) + expr ) ).setName(dlName)

def countedArray( expr ):
    """Helper to define a counted list of expressions.
       This helper defines a pattern of the form::
           integer expr expr expr...
       where the leading integer tells how many expr expressions follow.
       The matched tokens returns the array of expr tokens as a list - the leading count token is suppressed.
    """
    arrayExpr = Forward()
    def countFieldParseAction(s,l,t):
        n = int(t[0])
        arrayExpr << (n and Group(And([expr]*n)) or Group(empty))
        return []
    return ( Word(nums).setName("arrayLen").setParseAction(countFieldParseAction, callDuringTry=True) + arrayExpr )

def _flatten(L):
    if type(L) is not list: return [L]
    if L == []: return L
    return _flatten(L[0]) + _flatten(L[1:])

def matchPreviousLiteral(expr):
    """Helper to define an expression that is indirectly defined from
       the tokens matched in a previous expression, that is, it looks
       for a 'repeat' of a previous expression.  For example::
           first = Word(nums)
           second = matchPreviousLiteral(first)
           matchExpr = first + ":" + second
       will match C{"1:1"}, but not C{"1:2"}.  Because this matches a
       previous literal, will also match the leading C{"1:1"} in C{"1:10"}.
       If this is not desired, use C{matchPreviousExpr}.
       Do *not* use with packrat parsing enabled.
    """
    rep = Forward()
    def copyTokenToRepeater(s,l,t):
        if t:
            if len(t) == 1:
                rep << t[0]
            else:
                # flatten t tokens
                tflat = _flatten(t.asList())
                rep << And( [ Literal(tt) for tt in tflat ] )
        else:
            rep << Empty()
    expr.addParseAction(copyTokenToRepeater, callDuringTry=True)
    return rep

def matchPreviousExpr(expr):
    """Helper to define an expression that is indirectly defined from
       the tokens matched in a previous expression, that is, it looks
       for a 'repeat' of a previous expression.  For example::
           first = Word(nums)
           second = matchPreviousExpr(first)
           matchExpr = first + ":" + second
       will match C{"1:1"}, but not C{"1:2"}.  Because this matches by
       expressions, will *not* match the leading C{"1:1"} in C{"1:10"};
       the expressions are evaluated first, and then compared, so
       C{"1"} is compared with C{"10"}.
       Do *not* use with packrat parsing enabled.
    """
    rep = Forward()
    e2 = expr.copy()
    rep << e2
    def copyTokenToRepeater(s,l,t):
        matchTokens = _flatten(t.asList())
        def mustMatchTheseTokens(s,l,t):
            theseTokens = _flatten(t.asList())
            if  theseTokens != matchTokens:
                raise ParseException("",0,"")
        rep.setParseAction( mustMatchTheseTokens, callDuringTry=True )
    expr.addParseAction(copyTokenToRepeater, callDuringTry=True)
    return rep

def _escapeRegexRangeChars(s):
    #~  escape these chars: ^-]
    for c in r"\^-]":
        s = s.replace(c,_bslash+c)
    s = s.replace("\n",r"\n")
    s = s.replace("\t",r"\t")
    return _ustr(s)

def oneOf( strs, caseless=False, useRegex=True ):
    """Helper to quickly define a set of alternative Literals, and makes sure to do
       longest-first testing when there is a conflict, regardless of the input order,
       but returns a C{MatchFirst} for best performance.

       Parameters:
        - strs - a string of space-delimited literals, or a list of string literals
        - caseless - (default=False) - treat all literals as caseless
        - useRegex - (default=True) - as an optimization, will generate a Regex
          object; otherwise, will generate a C{MatchFirst} object (if C{caseless=True}, or
          if creating a C{Regex} raises an exception)
    """
    if caseless:
        isequal = ( lambda a,b: a.upper() == b.upper() )
        masks = ( lambda a,b: b.upper().startswith(a.upper()) )
        parseElementClass = CaselessLiteral
    else:
        isequal = ( lambda a,b: a == b )
        masks = ( lambda a,b: b.startswith(a) )
        parseElementClass = Literal

    if isinstance(strs,(list,tuple)):
        symbols = list(strs[:])
    elif isinstance(strs,basestring):
        symbols = strs.split()
    else:
        warnings.warn("Invalid argument to oneOf, expected string or list",
                SyntaxWarning, stacklevel=2)

    i = 0
    while i < len(symbols)-1:
        cur = symbols[i]
        for j,other in enumerate(symbols[i+1:]):
            if ( isequal(other, cur) ):
                del symbols[i+j+1]
                break
            elif ( masks(cur, other) ):
                del symbols[i+j+1]
                symbols.insert(i,other)
                cur = other
                break
        else:
            i += 1

    if not caseless and useRegex:
        #~ print (strs,"->", "|".join( [ _escapeRegexChars(sym) for sym in symbols] ))
        try:
            if len(symbols)==len("".join(symbols)):
                return Regex( "[%s]" % "".join( [ _escapeRegexRangeChars(sym) for sym in symbols] ) )
            else:
                return Regex( "|".join( [ re.escape(sym) for sym in symbols] ) )
        except:
            warnings.warn("Exception creating Regex for oneOf, building MatchFirst",
                    SyntaxWarning, stacklevel=2)


    # last resort, just use MatchFirst
    return MatchFirst( [ parseElementClass(sym) for sym in symbols ] )

def dictOf( key, value ):
    """Helper to easily and clearly define a dictionary by specifying the respective patterns
       for the key and value.  Takes care of defining the C{Dict}, C{ZeroOrMore}, and C{Group} tokens
       in the proper order.  The key pattern can include delimiting markers or punctuation,
       as long as they are suppressed, thereby leaving the significant key text.  The value
       pattern can include named results, so that the C{Dict} results can include named token
       fields.
    """
    return Dict( ZeroOrMore( Group ( key + value ) ) )

def originalTextFor(expr, asString=True):
    """Helper to return the original, untokenized text for a given expression.  Useful to
       restore the parsed fields of an HTML start tag into the raw tag text itself, or to
       revert separate tokens with intervening whitespace back to the original matching
       input text. Simpler to use than the parse action C{keepOriginalText}, and does not
       require the inspect module to chase up the call stack.  By default, returns a
       string containing the original parsed text.

       If the optional C{asString} argument is passed as False, then the return value is a
       C{ParseResults} containing any results names that were originally matched, and a
       single token containing the original matched text from the input string.  So if
       the expression passed to C{originalTextFor} contains expressions with defined
       results names, you must set C{asString} to False if you want to preserve those
       results name values."""
    locMarker = Empty().setParseAction(lambda s,loc,t: loc)
    endlocMarker = locMarker.copy()
    endlocMarker.callPreparse = False
    matchExpr = locMarker("_original_start") + expr + endlocMarker("_original_end")
    if asString:
        extractText = lambda s,l,t: s[t._original_start:t._original_end]
    else:
        def extractText(s,l,t):
            del t[:]
            t.insert(0, s[t._original_start:t._original_end])
            del t["_original_start"]
            del t["_original_end"]
    matchExpr.setParseAction(extractText)
    return matchExpr

# convenience constants for positional expressions
empty       = Empty().setName("empty")
lineStart   = LineStart().setName("lineStart")
lineEnd     = LineEnd().setName("lineEnd")
stringStart = StringStart().setName("stringStart")
stringEnd   = StringEnd().setName("stringEnd")

_escapedPunc = Word( _bslash, r"\[]-*.$+^?()~ ", exact=2 ).setParseAction(lambda s,l,t:t[0][1])
_printables_less_backslash = "".join([ c for c in printables if c not in  r"\]" ])
_escapedHexChar = Combine( Suppress(_bslash + "0x") + Word(hexnums) ).setParseAction(lambda s,l,t:unichr(int(t[0],16)))
_escapedOctChar = Combine( Suppress(_bslash) + Word("0","01234567") ).setParseAction(lambda s,l,t:unichr(int(t[0],8)))
_singleChar = _escapedPunc | _escapedHexChar | _escapedOctChar | Word(_printables_less_backslash,exact=1)
_charRange = Group(_singleChar + Suppress("-") + _singleChar)
_reBracketExpr = Literal("[") + Optional("^").setResultsName("negate") + Group( OneOrMore( _charRange | _singleChar ) ).setResultsName("body") + "]"

_expanded = lambda p: (isinstance(p,ParseResults) and ''.join([ unichr(c) for c in range(ord(p[0]),ord(p[1])+1) ]) or p)

def srange(s):
    r"""Helper to easily define string ranges for use in Word construction.  Borrows
       syntax from regexp '[]' string range definitions::
          srange("[0-9]")   -> "0123456789"
          srange("[a-z]")   -> "abcdefghijklmnopqrstuvwxyz"
          srange("[a-z$_]") -> "abcdefghijklmnopqrstuvwxyz$_"
       The input string must be enclosed in []'s, and the returned string is the expanded
       character set joined into a single string.
       The values enclosed in the []'s may be::
          a single character
          an escaped character with a leading backslash (such as \- or \])
          an escaped hex character with a leading '\0x' (\0x21, which is a '!' character)
          an escaped octal character with a leading '\0' (\041, which is a '!' character)
          a range of any of the above, separated by a dash ('a-z', etc.)
          any combination of the above ('aeiouy', 'a-zA-Z0-9_$', etc.)
    """
    try:
        return "".join([_expanded(part) for part in _reBracketExpr.parseString(s).body])
    except:
        return ""

def matchOnlyAtCol(n):
    """Helper method for defining parse actions that require matching at a specific
       column in the input text.
    """
    def verifyCol(strg,locn,toks):
        if col(locn,strg) != n:
            raise ParseException(strg,locn,"matched token not at column %d" % n)
    return verifyCol

def replaceWith(replStr):
    """Helper method for common parse actions that simply return a literal value.  Especially
       useful when used with C{transformString()}.
    """
    def _replFunc(*args):
        return [replStr]
    return _replFunc

def removeQuotes(s,l,t):
    """Helper parse action for removing quotation marks from parsed quoted strings.
       To use, add this parse action to quoted string using::
         quotedString.setParseAction( removeQuotes )
    """
    return t[0][1:-1]

def upcaseTokens(s,l,t):
    """Helper parse action to convert tokens to upper case."""
    return [ tt.upper() for tt in map(_ustr,t) ]

def downcaseTokens(s,l,t):
    """Helper parse action to convert tokens to lower case."""
    return [ tt.lower() for tt in map(_ustr,t) ]

def keepOriginalText(s,startLoc,t):
    """DEPRECATED - use new helper method C{originalTextFor}.
       Helper parse action to preserve original parsed text,
       overriding any nested parse actions."""
    try:
        endloc = getTokensEndLoc()
    except ParseException:
        raise ParseFatalException("incorrect usage of keepOriginalText - may only be called as a parse action")
    del t[:]
    t += ParseResults(s[startLoc:endloc])
    return t

def getTokensEndLoc():
    """Method to be called from within a parse action to determine the end
       location of the parsed tokens."""
    import inspect
    fstack = inspect.stack()
    try:
        # search up the stack (through intervening argument normalizers) for correct calling routine
        for f in fstack[2:]:
            if f[3] == "_parseNoCache":
                endloc = f[0].f_locals["loc"]
                return endloc
        else:
            raise ParseFatalException("incorrect usage of getTokensEndLoc - may only be called from within a parse action")
    finally:
        del fstack

def _makeTags(tagStr, xml):
    """Internal helper to construct opening and closing tag expressions, given a tag name"""
    if isinstance(tagStr,basestring):
        resname = tagStr
        tagStr = Keyword(tagStr, caseless=not xml)
    else:
        resname = tagStr.name

    tagAttrName = Word(alphas,alphanums+"_-:")
    if (xml):
        tagAttrValue = dblQuotedString.copy().setParseAction( removeQuotes )
        openTag = Suppress("<") + tagStr("tag") + \
                Dict(ZeroOrMore(Group( tagAttrName + Suppress("=") + tagAttrValue ))) + \
                Optional("/",default=[False]).setResultsName("empty").setParseAction(lambda s,l,t:t[0]=='/') + Suppress(">")
    else:
        printablesLessRAbrack = "".join( [ c for c in printables if c not in ">" ] )
        tagAttrValue = quotedString.copy().setParseAction( removeQuotes ) | Word(printablesLessRAbrack)
        openTag = Suppress("<") + tagStr + \
                Dict(ZeroOrMore(Group( tagAttrName.setParseAction(downcaseTokens) + \
                Optional( Suppress("=") + tagAttrValue ) ))) + \
                Optional("/",default=[False]).setResultsName("empty").setParseAction(lambda s,l,t:t[0]=='/') + Suppress(">")
    closeTag = Combine(_L("</") + tagStr + ">")

    openTag = openTag.setResultsName("start"+"".join(resname.replace(":"," ").title().split())).setName("<%s>" % tagStr)
    closeTag = closeTag.setResultsName("end"+"".join(resname.replace(":"," ").title().split())).setName("</%s>" % tagStr)
    openTag.tag = resname
    closeTag.tag = resname
    return openTag, closeTag

def makeHTMLTags(tagStr):
    """Helper to construct opening and closing tag expressions for HTML, given a tag name"""
    return _makeTags( tagStr, False )

def makeXMLTags(tagStr):
    """Helper to construct opening and closing tag expressions for XML, given a tag name"""
    return _makeTags( tagStr, True )

def withAttribute(*args,**attrDict):
    """Helper to create a validating parse action to be used with start tags created
       with makeXMLTags or makeHTMLTags. Use withAttribute to qualify a starting tag
       with a required attribute value, to avoid false matches on common tags such as
       <TD> or <DIV>.

       Call withAttribute with a series of attribute names and values. Specify the list
       of filter attributes names and values as:
        - keyword arguments, as in (class="Customer",align="right"), or
        - a list of name-value tuples, as in ( ("ns1:class", "Customer"), ("ns2:align","right") )
       For attribute names with a namespace prefix, you must use the second form.  Attribute
       names are matched insensitive to upper/lower case.

       To verify that the attribute exists, but without specifying a value, pass
       withAttribute.ANY_VALUE as the value.
       """
    if args:
        attrs = args[:]
    else:
        attrs = attrDict.items()
    attrs = [(k,v) for k,v in attrs]
    def pa(s,l,tokens):
        for attrName,attrValue in attrs:
            if attrName not in tokens:
                raise ParseException(s,l,"no matching attribute " + attrName)
            if attrValue != withAttribute.ANY_VALUE and tokens[attrName] != attrValue:
                raise ParseException(s,l,"attribute '%s' has value '%s', must be '%s'" %
                                            (attrName, tokens[attrName], attrValue))
    return pa
withAttribute.ANY_VALUE = object()

opAssoc = _Constants()
opAssoc.LEFT = object()
opAssoc.RIGHT = object()

def operatorPrecedence( baseExpr, opList ):
    """Helper method for constructing grammars of expressions made up of
       operators working in a precedence hierarchy.  Operators may be unary or
       binary, left- or right-associative.  Parse actions can also be attached
       to operator expressions.

       Parameters:
        - baseExpr - expression representing the most basic element for the nested
        - opList - list of tuples, one for each operator precedence level in the
          expression grammar; each tuple is of the form
          (opExpr, numTerms, rightLeftAssoc, parseAction), where:
           - opExpr is the pyparsing expression for the operator;
              may also be a string, which will be converted to a Literal;
              if numTerms is 3, opExpr is a tuple of two expressions, for the
              two operators separating the 3 terms
           - numTerms is the number of terms for this operator (must
              be 1, 2, or 3)
           - rightLeftAssoc is the indicator whether the operator is
              right or left associative, using the pyparsing-defined
              constants opAssoc.RIGHT and opAssoc.LEFT.
           - parseAction is the parse action to be associated with
              expressions matching this operator expression (the
              parse action tuple member may be omitted)
    """
    ret = Forward()
    lastExpr = baseExpr | ( Suppress('(') + ret + Suppress(')') )
    for i,operDef in enumerate(opList):
        opExpr,arity,rightLeftAssoc,pa = (operDef + (None,))[:4]
        if arity == 3:
            if opExpr is None or len(opExpr) != 2:
                raise ValueError("if numterms=3, opExpr must be a tuple or list of two expressions")
            opExpr1, opExpr2 = opExpr
        thisExpr = Forward()#.setName("expr%d" % i)
        if rightLeftAssoc == opAssoc.LEFT:
            if arity == 1:
                matchExpr = FollowedBy(lastExpr + opExpr) + Group( lastExpr + OneOrMore( opExpr ) )
            elif arity == 2:
                if opExpr is not None:
                    matchExpr = FollowedBy(lastExpr + opExpr + lastExpr) + Group( lastExpr + OneOrMore( opExpr + lastExpr ) )
                else:
                    matchExpr = FollowedBy(lastExpr+lastExpr) + Group( lastExpr + OneOrMore(lastExpr) )
            elif arity == 3:
                matchExpr = FollowedBy(lastExpr + opExpr1 + lastExpr + opExpr2 + lastExpr) + \
                            Group( lastExpr + opExpr1 + lastExpr + opExpr2 + lastExpr )
            else:
                raise ValueError("operator must be unary (1), binary (2), or ternary (3)")
        elif rightLeftAssoc == opAssoc.RIGHT:
            if arity == 1:
                # try to avoid LR with this extra test
                if not isinstance(opExpr, Optional):
                    opExpr = Optional(opExpr)
                matchExpr = FollowedBy(opExpr.expr + thisExpr) + Group( opExpr + thisExpr )
            elif arity == 2:
                if opExpr is not None:
                    matchExpr = FollowedBy(lastExpr + opExpr + thisExpr) + Group( lastExpr + OneOrMore( opExpr + thisExpr ) )
                else:
                    matchExpr = FollowedBy(lastExpr + thisExpr) + Group( lastExpr + OneOrMore( thisExpr ) )
            elif arity == 3:
                matchExpr = FollowedBy(lastExpr + opExpr1 + thisExpr + opExpr2 + thisExpr) + \
                            Group( lastExpr + opExpr1 + thisExpr + opExpr2 + thisExpr )
            else:
                raise ValueError("operator must be unary (1), binary (2), or ternary (3)")
        else:
            raise ValueError("operator must indicate right or left associativity")
        if pa:
            matchExpr.setParseAction( pa )
        thisExpr << ( matchExpr | lastExpr )
        lastExpr = thisExpr
    ret << lastExpr
    return ret

dblQuotedString = Regex(r'"(?:[^"\n\r\\]|(?:"")|(?:\\x[0-9a-fA-F]+)|(?:\\.))*"').setName("string enclosed in double quotes")
sglQuotedString = Regex(r"'(?:[^'\n\r\\]|(?:'')|(?:\\x[0-9a-fA-F]+)|(?:\\.))*'").setName("string enclosed in single quotes")
quotedString = Regex(r'''(?:"(?:[^"\n\r\\]|(?:"")|(?:\\x[0-9a-fA-F]+)|(?:\\.))*")|(?:'(?:[^'\n\r\\]|(?:'')|(?:\\x[0-9a-fA-F]+)|(?:\\.))*')''').setName("quotedString using single or double quotes")
unicodeString = Combine(_L('u') + quotedString.copy())

def nestedExpr(opener="(", closer=")", content=None, ignoreExpr=quotedString.copy()):
    """Helper method for defining nested lists enclosed in opening and closing
       delimiters ("(" and ")" are the default).

       Parameters:
        - opener - opening character for a nested list (default="("); can also be a pyparsing expression
        - closer - closing character for a nested list (default=")"); can also be a pyparsing expression
        - content - expression for items within the nested lists (default=None)
        - ignoreExpr - expression for ignoring opening and closing delimiters (default=quotedString)

       If an expression is not provided for the content argument, the nested
       expression will capture all whitespace-delimited content between delimiters
       as a list of separate values.

       Use the ignoreExpr argument to define expressions that may contain
       opening or closing characters that should not be treated as opening
       or closing characters for nesting, such as quotedString or a comment
       expression.  Specify multiple expressions using an Or or MatchFirst.
       The default is quotedString, but if no expressions are to be ignored,
       then pass None for this argument.
    """
    if opener == closer:
        raise ValueError("opening and closing strings cannot be the same")
    if content is None:
        if isinstance(opener,basestring) and isinstance(closer,basestring):
            if len(opener) == 1 and len(closer)==1:
                if ignoreExpr is not None:
                    content = (Combine(OneOrMore(~ignoreExpr +
                                    CharsNotIn(opener+closer+ParserElement.DEFAULT_WHITE_CHARS,exact=1))
                                ).setParseAction(lambda t:t[0].strip()))
                else:
                    content = (empty.copy()+CharsNotIn(opener+closer+ParserElement.DEFAULT_WHITE_CHARS
                                ).setParseAction(lambda t:t[0].strip()))
            else:
                if ignoreExpr is not None:
                    content = (Combine(OneOrMore(~ignoreExpr +
                                    ~Literal(opener) + ~Literal(closer) +
                                    CharsNotIn(ParserElement.DEFAULT_WHITE_CHARS,exact=1))
                                ).setParseAction(lambda t:t[0].strip()))
                else:
                    content = (Combine(OneOrMore(~Literal(opener) + ~Literal(closer) +
                                    CharsNotIn(ParserElement.DEFAULT_WHITE_CHARS,exact=1))
                                ).setParseAction(lambda t:t[0].strip()))
        else:
            raise ValueError("opening and closing arguments must be strings if no content expression is given")
    ret = Forward()
    if ignoreExpr is not None:
        ret << Group( Suppress(opener) + ZeroOrMore( ignoreExpr | ret | content ) + Suppress(closer) )
    else:
        ret << Group( Suppress(opener) + ZeroOrMore( ret | content )  + Suppress(closer) )
    return ret

def indentedBlock(blockStatementExpr, indentStack, indent=True):
    """Helper method for defining space-delimited indentation blocks, such as
       those used to define block statements in Python source code.

       Parameters:
        - blockStatementExpr - expression defining syntax of statement that
            is repeated within the indented block
        - indentStack - list created by caller to manage indentation stack
            (multiple statementWithIndentedBlock expressions within a single grammar
            should share a common indentStack)
        - indent - boolean indicating whether block must be indented beyond the
            the current level; set to False for block of left-most statements
            (default=True)

       A valid block must contain at least one blockStatement.
    """
    def checkPeerIndent(s,l,t):
        if l >= len(s): return
        curCol = col(l,s)
        if curCol != indentStack[-1]:
            if curCol > indentStack[-1]:
                raise ParseFatalException(s,l,"illegal nesting")
            raise ParseException(s,l,"not a peer entry")

    def checkSubIndent(s,l,t):
        curCol = col(l,s)
        if curCol > indentStack[-1]:
            indentStack.append( curCol )
        else:
            raise ParseException(s,l,"not a subentry")

    def checkUnindent(s,l,t):
        if l >= len(s): return
        curCol = col(l,s)
        if not(indentStack and curCol < indentStack[-1] and curCol <= indentStack[-2]):
            raise ParseException(s,l,"not an unindent")
        indentStack.pop()

    NL = OneOrMore(LineEnd().setWhitespaceChars("\t ").suppress())
    INDENT = Empty() + Empty().setParseAction(checkSubIndent)
    PEER   = Empty().setParseAction(checkPeerIndent)
    UNDENT = Empty().setParseAction(checkUnindent)
    if indent:
        smExpr = Group( Optional(NL) +
            #~ FollowedBy(blockStatementExpr) +
            INDENT + (OneOrMore( PEER + Group(blockStatementExpr) + Optional(NL) )) + UNDENT)
    else:
        smExpr = Group( Optional(NL) +
            (OneOrMore( PEER + Group(blockStatementExpr) + Optional(NL) )) )
    blockStatementExpr.ignore(_bslash + LineEnd())
    return smExpr

alphas8bit = srange(r"[\0xc0-\0xd6\0xd8-\0xf6\0xf8-\0xff]")
punc8bit = srange(r"[\0xa1-\0xbf\0xd7\0xf7]")

anyOpenTag,anyCloseTag = makeHTMLTags(Word(alphas,alphanums+"_:"))
commonHTMLEntity = Combine(_L("&") + oneOf("gt lt amp nbsp quot").setResultsName("entity") +";").streamline()
_htmlEntityMap = dict(zip("gt lt amp nbsp quot".split(),'><& "'))
replaceHTMLEntity = lambda t : t.entity in _htmlEntityMap and _htmlEntityMap[t.entity] or None

# it's easy to get these comment structures wrong - they're very common, so may as well make them available
cStyleComment = Regex(r"/\*(?:[^*]*\*+)+?/").setName("C style comment")

htmlComment = Regex(r"<!--[\s\S]*?-->")
restOfLine = Regex(r".*").leaveWhitespace()
dblSlashComment = Regex(r"\/\/(\\\n|.)*").setName("// comment")
cppStyleComment = Regex(r"/(?:\*(?:[^*]*\*+)+?/|/[^\n]*(?:\n[^\n]*)*?(?:(?<!\\)|\Z))").setName("C++ style comment")

javaStyleComment = cppStyleComment
pythonStyleComment = Regex(r"#.*").setName("Python style comment")
_noncomma = "".join( [ c for c in printables if c != "," ] )
_commasepitem = Combine(OneOrMore(Word(_noncomma) +
                                  Optional( Word(" \t") +
                                            ~Literal(",") + ~LineEnd() ) ) ).streamline().setName("commaItem")
commaSeparatedList = delimitedList( Optional( quotedString.copy() | _commasepitem, default="") ).setName("commaSeparatedList")


if __name__ == "__main__":

    def test( teststring ):
        try:
            tokens = simpleSQL.parseString( teststring )
            tokenlist = tokens.asList()
            print (teststring + "->"   + str(tokenlist))
            print ("tokens = "         + str(tokens))
            print ("tokens.columns = " + str(tokens.columns))
            print ("tokens.tables = "  + str(tokens.tables))
            print (tokens.asXML("SQL",True))
        except ParseBaseException as err:
            print (teststring + "->")
            print (err.line)
            print (" "*(err.column-1) + "^")
            print (err)
        print()

    selectToken    = CaselessLiteral( "select" )
    fromToken      = CaselessLiteral( "from" )

    ident          = Word( alphas, alphanums + "_$" )
    columnName     = delimitedList( ident, ".", combine=True ).setParseAction( upcaseTokens )
    columnNameList = Group( delimitedList( columnName ) )#.setName("columns")
    tableName      = delimitedList( ident, ".", combine=True ).setParseAction( upcaseTokens )
    tableNameList  = Group( delimitedList( tableName ) )#.setName("tables")
    simpleSQL      = ( selectToken + \
                     ( '*' | columnNameList ).setResultsName( "columns" ) + \
                     fromToken + \
                     tableNameList.setResultsName( "tables" ) )

    test( "SELECT * from XYZZY, ABC" )
    test( "select * from SYS.XYZZY" )
    test( "Select A from Sys.dual" )
    test( "Select AA,BB,CC from Sys.dual" )
    test( "Select A, B, C from Sys.dual" )
    test( "Select A, B, C from Sys.dual" )
    test( "Xelect A, B, C from Sys.dual" )
    test( "Select A, B, C frox Sys.dual" )
    test( "Select" )
    test( "Select ^^^ frox Sys.dual" )
    test( "Select A, B, C from Sys.dual, Table2   " )

########NEW FILE########
__FILENAME__ = reference
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


from .flowable import LabeledFlowable, DummyFlowable
from .number import NumberStyle, format_number
from .paragraph import Paragraph
from .style import PARENT_STYLE
from .text import SingleStyledText, TextStyle


__all__ = ['Field', 'Variable', 'Referenceable', 'Reference',
           'NoteMarker', 'Note', 'RegisterNote', 'NoteMarkerWithNote',
           'PAGE_NUMBER', 'NUMBER_OF_PAGES', 'SECTION_NUMBER', 'SECTION_TITLE']


class Field(SingleStyledText):
    def __init__(self, style=PARENT_STYLE, parent=None):
        super().__init__('', style=style, parent=parent)


PAGE_NUMBER = 'page number'
NUMBER_OF_PAGES = 'number of pages'
SECTION_NUMBER = 'section number'
SECTION_TITLE = 'section title'


class Variable(Field):
    def __init__(self, type, style=PARENT_STYLE):
        super().__init__(style=style)
        self.type = type

    def __repr__(self):
        return "{0}({1})".format(self.__class__.__name__, self.type)

    def split(self, container):
        text = '?'
        if self.type == PAGE_NUMBER:
            text = str(container.page.number)
        elif self.type == NUMBER_OF_PAGES:
            number = container.document.number_of_pages
            text = str(number)
        elif self.type == SECTION_NUMBER and container.page.section:
            section_id = container.page.section.get_id(container.document)
            text = container.document.get_reference(section_id, REFERENCE) or ''
        elif self.type == SECTION_TITLE and container.page.section:
            section_id = container.page.section.get_id(container.document)
            text = container.document.get_reference(section_id, TITLE)

        return self.split_words(text)


class Referenceable(object):
    def __init__(self, id):
        self.id = id

    def prepare(self, document):
        element_id = self.id or document.unique_id
        if self.id is None:
            document.ids_by_element[self] = element_id
        document.elements[element_id] = self
        super().prepare(document)

    def get_id(self, document):
        return self.id or document.ids_by_element[self]

    def update_page_reference(self, page):
        document = page.document
        document.page_references[self.get_id(document)] = page.number


REFERENCE = 'reference'
PAGE = 'page'
TITLE = 'title'
POSITION = 'position'


class Reference(Field):
    def __init__(self, target_id, type=REFERENCE, style=PARENT_STYLE):
        super().__init__(style=style)
        self._target_id = target_id
        self.type = type

    def target_id(self, document):
        return self._target_id

    def split(self, container):
        target_id = self.target_id(container.document)
        try:
            if self.type == REFERENCE:
                text = container.document.get_reference(target_id, self.type)
                if text is None:
                    self.warn('Cannot reference "{}"'.format(target_id),
                              container)
                    text = ''
            elif self.type == PAGE:
                try:
                    text = str(container.document.page_references[target_id])
                except KeyError:
                    text = '??'
            elif self.type == TITLE:
                text = container.document.get_reference(target_id, self.type)
            else:
                raise NotImplementedError
        except KeyError:
            self.warn("Unknown label '{}'".format(target_id), container)
            text = "??".format(target_id)

        return self.split_words(text)


class DirectReference(Reference):
    def __init__(self, referenceable, type=REFERENCE, style=PARENT_STYLE):
        super().__init__(None, type=type, style=style)
        self.referenceable = referenceable

    def target_id(self, document):
        return self.referenceable.get_id(document)


class Note(Referenceable, LabeledFlowable):
    def __init__(self, flowable, id, style=None, parent=None):
        Referenceable.__init__(self, id)
        label = Paragraph(DirectReference(self))
        LabeledFlowable.__init__(self, label, flowable, style=style,
                                 parent=parent)


class RegisterNote(DummyFlowable):
    def __init__(self, note, parent=None):
        super().__init__(parent=parent)
        self.note = note

    def prepare(self, document):
        self.note.prepare(document)


class NoteMarkerStyle(TextStyle, NumberStyle):
    pass


class NoteMarker(Reference):
    style_class = NoteMarkerStyle

    def __init__(self, target_id, type=REFERENCE, style=None):
        super().__init__(target_id, type=type, style=style)

    def prepare(self, document):
        target_id = self.target_id(document)
        try:  # set reference only once (notes can be referenced multiple times)
            document.get_reference(target_id, REFERENCE)
        except KeyError:
            number_format = self.get_style('number_format', document)
            counter = document.counters.setdefault(__class__, [])
            counter.append(self)
            formatted_number = format_number(len(counter), number_format)
            document.set_reference(target_id, REFERENCE, formatted_number)

    def split(self, container):
        note = container.document.elements[self.target_id(container.document)]
        container._footnote_space.add_footnote(note)
        return super().split(container)
        # TODO: handle overflow in footnote_space


class NoteMarkerWithNote(DirectReference, NoteMarker):
    def __init__(self, note, type=REFERENCE, style=PARENT_STYLE):
        super().__init__(note, type=type, style=style)
        self.note = note

    def prepare(self, document):
        self.note.prepare(document)
        super().prepare(document)

########NEW FILE########
__FILENAME__ = structure
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


from itertools import count, repeat

from .draw import Line, LineStyle
from .flowable import GroupedFlowables, StaticGroupedFlowables
from .flowable import LabeledFlowable, GroupedLabeledFlowables
from .flowable import Flowable, FlowableStyle, GroupedFlowablesStyle
from .number import NumberStyle, format_number
from .number import NumberedParagraph, NumberedParagraphStyle
from .paragraph import ParagraphStyle, Paragraph
from .reference import Referenceable, Reference
from .reference import REFERENCE, TITLE, PAGE
from .reference import Variable, PAGE_NUMBER, NUMBER_OF_PAGES
from .reference import SECTION_NUMBER, SECTION_TITLE
from .text import SingleStyledText, MixedStyledText, Tab
from .dimension import PT
from .style import PARENT_STYLE


__all__ = ['Section', 'Heading', 'ListStyle', 'List', 'ListItem', 'FieldList',
           'DefinitionListStyle', 'DefinitionList', 'DefinitionTerm',
           'HeaderStyle', 'Header', 'FooterStyle', 'Footer',
           'TableOfContentsStyle', 'TableOfContents', 'TableOfContentsEntry',
           'HorizontalRule', 'HorizontalRuleStyle']


class Section(Referenceable, StaticGroupedFlowables):
    def __init__(self, flowables, id=None, style=None, parent=None):
        Referenceable.__init__(self, id)
        StaticGroupedFlowables.__init__(self, flowables, style=style,
                                        parent=parent)

    @property
    def level(self):
        try:
            return self.parent.level + 1
        except AttributeError:
            return 1

    @property
    def section(self):
        return self


class HeadingStyle(NumberedParagraphStyle):
    attributes = {'number_separator': '.'}


class Heading(NumberedParagraph):
    style_class = HeadingStyle

    def __init__(self, title, style=None, parent=None):
        super().__init__(title, style=style, parent=parent)

    def __repr__(self):
        return '{}({}) (style={})'.format(self.__class__.__name__, self.title,
                                          self.style)

    def prepare(self, document):
        section_id = self.section.get_id(document)
        numbering_style = self.get_style('number_format', document)
        if numbering_style:
            heading_counters = document.counters.setdefault(__class__, {})
            level_counter = heading_counters.setdefault(self.level, [])
            level_counter.append(self)
            number = len(level_counter)
            formatted_number = format_number(number, numbering_style)
            separator = self.get_style('number_separator', document)
            if separator is not None and self.level > 1:
                parent_id = self.section.parent.section.get_id(document)
                parent_ref = document.get_reference(parent_id, REFERENCE)
                formatted_number = parent_ref + separator + formatted_number
        else:
            formatted_number = None
        document.set_reference(section_id, REFERENCE, formatted_number)
        document.set_reference(section_id, TITLE, str(self.content))

    def text(self, document):
        number = self.number(document)
        return MixedStyledText(number + self.content, parent=self)

    def render(self, container, last_descender, state=None):
        result = super().render(container, last_descender, state=state)
        if self.level == 1:
            container.page.section = self.parent
        self.parent.update_page_reference(container.page)
        return result


class ListStyle(GroupedFlowablesStyle, NumberStyle):
    attributes = {'ordered': False,
                  'bullet': SingleStyledText('\N{BULLET}')}


class List(GroupedLabeledFlowables):
    style_class = ListStyle

    def __init__(self, items, style=None):
        super().__init__(style)
        self.items = items

    def flowables(self, document):
        if self.get_style('ordered', document):
            number_format = self.get_style('number_format', document)
            numbers = (format_number(i, number_format) for i in count(1))
            suffix = self.get_style('number_suffix', document)
        else:
            numbers = repeat(self.get_style('bullet', document))
            suffix = ''
        for number, item in zip(numbers, self.items):
            label = Paragraph(number + suffix)
            flowable = StaticGroupedFlowables(item)
            yield ListItem(label, flowable, parent=self)


class ListItem(LabeledFlowable):
    pass


class FieldList(GroupedLabeledFlowables, StaticGroupedFlowables):
    pass


class DefinitionListStyle(GroupedFlowablesStyle, ParagraphStyle):
    attributes = {'term_style': PARENT_STYLE,
                  'indentation': 10*PT}

    def __init__(self, base=None, **attributes):
        super().__init__(base=base, **attributes)


class DefinitionList(GroupedFlowables):
    style_class = DefinitionListStyle

    def __init__(self, items, style=None):
        super().__init__(style)
        self.items = items
        for term, definition in items:
            definition.parent = self

    def flowables(self, document):
        for (term, definition) in self.items:
            yield DefinitionTerm(term, parent=self)
            yield definition


class DefinitionTerm(Paragraph):
    pass


class HeaderStyle(ParagraphStyle):
    attributes = {}

    def __init__(self, base=None, **attributes):
        super().__init__(base=base, **attributes)


class Header(Paragraph):
    style_class = HeaderStyle

    def __init__(self, style=None, parent=None):
        text = Variable(SECTION_NUMBER) + ' ' + Variable(SECTION_TITLE)
        super().__init__(text, style=style, parent=parent)


class FooterStyle(ParagraphStyle):
    attributes = {}

    def __init__(self, base=None, **attributes):
        super().__init__(base=base, **attributes)


class Footer(Paragraph):
    style_class = FooterStyle

    def __init__(self, style=None, parent=None):
        text = Variable(PAGE_NUMBER) + ' / ' + Variable(NUMBER_OF_PAGES)
        super().__init__(text, style=style, parent=parent)


class TableOfContentsStyle(GroupedFlowablesStyle, ParagraphStyle):
    attributes = {'depth': 3}

    def __init__(self, base=None, **attributes):
        super().__init__(base=base, **attributes)


class TableOfContents(GroupedFlowables):
    style_class = TableOfContentsStyle
    location = 'table of contents'

    def __init__(self, local=False, style=None, parent=None):
        super().__init__(style=style, parent=parent)
        self.local = local
        self.source = self

    def flowables(self, document):
        def limit_items(items, section):
            section_id = section.get_id(document)
            section_level = section.level

            # fast-forward `items` to the first sub-section of `section`
            while next(items)[0] != section_id:
                pass

            for flowable_id, flowable in items:
                if flowable.level == section_level:
                    break
                yield flowable_id, flowable

        depth = self.get_style('depth', document)
        items = ((flowable_id, flowable)
                 for flowable_id, flowable in document.elements.items()
                 if isinstance(flowable, Section) and flowable.level <= depth)
        if self.local and self.section:
            items = limit_items(items, self.section)

        for flowable_id, flowable in items:
            text = [Reference(flowable_id, type=REFERENCE), Tab(),
                    Reference(flowable_id, type=TITLE), Tab(),
                    Reference(flowable_id, type=PAGE)]
            yield TableOfContentsEntry(text, flowable.level, parent=self)


class TableOfContentsEntry(Paragraph):
    def __init__(self, text_or_items, depth, style=None, parent=None):
        super().__init__(text_or_items, style=style, parent=parent)
        self.depth = depth


class HorizontalRuleStyle(FlowableStyle, LineStyle):
    pass


class HorizontalRule(Flowable):
    style_class = HorizontalRuleStyle

    def render(self, container, descender, state=None):
        width = float(container.width)
        line = Line((0, 0), (width, 0), style=PARENT_STYLE, parent=self)
        line.render(container.canvas)
        return width, 0

########NEW FILE########
__FILENAME__ = style
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.

"""
Base classes and exceptions for styled document elements.

* :class:`Style`: Dictionary storing a set of style attributes
* :class:`Styled`: A styled entity, having a :class:`Style` associated with it
* :class:`StyleStore`: Dictionary storing a set of related `Style`s by name
* :const:`PARENT_STYLE`: Special style that forwards style lookups to the parent
                        :class:`Styled`
* :exc:`ParentStyleException`: Thrown when style attribute lookup needs to be
                               delegated to the parent :class:`Styled`
"""


from collections import OrderedDict

from .document import DocumentElement
from .util import cached


__all__ = ['Style', 'Styled', 'StyleSheet', 'ClassSelector', 'ContextSelector',
           'PARENT_STYLE', 'ParentStyleException']


class ParentStyleException(Exception):
    """Style attribute not found. Consult the parent :class:`Styled`."""


class DefaultValueException(Exception):
    """The attribute is not specified in this :class:`Style` or any of its base
    styles. Return the default value for the attribute."""


class Style(dict):
    """"Dictionary storing style attributes.

    Attrributes can also be accessed as attributes."""

    attributes = {}
    """Dictionary holding the supported style attributes for this :class:`Style`
    class (keys) and their default values (values)"""

    def __init__(self, base=None, **attributes):
        """Style attributes are as passed as keyword arguments. Supported
        attributes include those defined in the :attr:`attributes` attribute of
        this style class and those defined in style classes this one inherits
        from.

        Optionally, a `base` (:class:`Style`) is passed, where attributes are
        looked up when they have not been specified in this style.
        Alternatively, if `base` is :class:`PARENT_STYLE`, the attribute lookup
        is forwarded to the parent of the element the lookup originates from.
        If `base` is a :class:`str`, it is used to look up the base style in
        the :class:`StyleStore` this style is stored in."""
        self.base = base
        self.name = None
        self.store = None
        for attribute in attributes:
            if attribute not in self._supported_attributes():
                raise TypeError('%s is not a supported attribute' % attribute)
        super().__init__(attributes)

    @property
    def base(self):
        """Return the base style for this style."""
        if isinstance(self._base, str):
            return self.store[self._base]
        else:
            return self._base

    @base.setter
    def base(self, base):
        """Set this style's base to `base`"""
        self._base = base

    def __repr__(self):
        """Return a textual representation of this style."""
        return '{0}({1}) > {2}'.format(self.__class__.__name__, self.name or '',
                                       self.base)

    def __copy__(self):
        copy = self.__class__(base=self.base, **self)
        if self.name is not None:
            copy.name = self.name + ' (copy)'
            copy.store = self.store
        return copy

    def __getattr__(self, attribute):
        return self[attribute]

    def __getitem__(self, attribute):
        """Return the value of `attribute`.

        If the attribute is not specified in this :class:`Style`, find it in
        this style's base styles (hierarchically), or ultimately raise a
        :class:`DefaultValueException`."""
        try:
            return super().__getitem__(attribute)
        except KeyError:
            if self.base is None:
                raise DefaultValueException
            return self.base[attribute]

    @classmethod
    def _get_default(cls, attribute):
        """Return the default value for `attribute`.

        If no default is specified in this style, get the default from the
        nearest superclass.
        If `attribute` is not supported, raise a :class:`KeyError`."""
        try:
            for super_cls in cls.__mro__:
                if attribute in super_cls.attributes:
                    return super_cls.attributes[attribute]
        except AttributeError:
            raise KeyError("No attribute '{}' in {}".format(attribute, cls))

    @classmethod
    def _supported_attributes(cls):
        """Return a :class:`set` of the attributes supported by this style
        class."""
        attributes = set()
        try:
            for super_cls in cls.__mro__:
                attributes.update(super_cls.attributes.keys())
        except AttributeError:
            return attributes


class ParentStyle(Style):
    """Special style that delegates attribute lookups by raising a
    :class:`ParentStyleException` on each attempt to access an attribute."""

    def __repr__(self):
        return self.__class__.__name__

    def __getitem__(self, attribute):
        raise ParentStyleException


PARENT_STYLE = ParentStyle()
"""Special style that forwards style lookups to the parent of the
:class:`Styled` from which the lookup originates."""


class Styled(DocumentElement):
    """An element that has a :class:`Style` associated with it."""

    style_class = None
    """The :class:`Style` subclass that corresponds to this :class:`Styled`
    subclass."""

    def __init__(self, style=None, parent=None):
        """Associates `style` with this element. If `style` is `None`, an empty
        :class:`Style` is create, effectively using the defaults defined for the
        associated :class:`Style` class).
        A `parent` can be passed on object initialization, or later by
        assignment to the `parent` attribute."""
        super().__init__(parent=parent)
        if (isinstance(style, Style)
                and not isinstance(style, (self.style_class, ParentStyle))):
            raise TypeError('the style passed to {} should be of type {} '
                            '(a {} was passed instead)'
                            .format(self.__class__.__name__,
                                    self.style_class.__name__,
                                    style.__class__.__name__))
        self.style = style

    @property
    def path(self):
        parent = self.parent.path + ' > ' if self.parent else ''
        style = '[{}]'.format(self.style) if self.style else ''
        return parent + self.__class__.__name__ + style

    @cached
    def get_style(self, attribute, document=None):
        try:
            return self.get_style_recursive(attribute, document)
        except DefaultValueException:
            self.warn('Falling back to default style for ({})'
                      .format(self.path))
            return self.style_class._get_default(attribute)

    def get_style_recursive(self, attribute, document=None):
        style = self._style(document)
        if style is None:
            raise DefaultValueException
        try:
            return style[attribute]
        except ParentStyleException:
            return self.parent.get_style_recursive(attribute, document)

    @cached
    def _style(self, document):
        if isinstance(self.style, Style):
            if isinstance(self.style, ParentStyle):
                return document.styles.find_style(self) or self.style
            else:
                return self.style
        else:
            return document.styles.find_style(self)


class StyleSheet(OrderedDict):
    """Dictionary storing a set of related :class:`Style`s by name.

    :class:`Style`s stored in a :class:`StyleStore` can refer to their base
    style by name. See :class:`Style`."""

    def __init__(self, name, base=None):
        super().__init__()
        self.name = name
        self.base = base
        self.selectors = {}

    def __getitem__(self, name):
        if name in self:
            return super().__getitem__(name)
        elif self.base is not None:
            return self.base[name]
        else:
            raise KeyError

    def __setitem__(self, name, style):
        style.name = name
        style.store = self
        super().__setitem__(name, style)

    def __call__(self, name, selector, **kwargs):
        self[name] = selector.cls.style_class(**kwargs)
        self.selectors[selector] = name

    def best_match(self, styled):
        max_score, best_match = Specificity(0, 0, 0), None
        for selector, name in self.selectors.items():
            score = selector.match(styled)
            if score > max_score:
                best_match = name
                max_score = score
        return max_score, best_match

    def find_style(self, styled):
        max_score, best_match = self.best_match(styled)
        if self.base:
            base_max_score, base_best_match = self.base.best_match(styled)
            if base_max_score > max_score:
                max_score, best_match = base_max_score, base_best_match
        if sum(max_score):
            print("({}) matches '{}'".format(styled.path, best_match))
            return self[best_match]


class Specificity(tuple):
    def __new__(cls, *items):
        return super().__new__(cls, items)

    def __add__(self, other):
        return tuple(a + b for a, b in zip(self, other))

    def __bool__(self):
        return any(self)


class Selector(object):
    def __init__(self, cls):
        self.cls = cls

    def match(self, styled):
        raise NotImplementedError


class ClassSelector(Selector):
    def __init__(self, cls, style_class=None, **attributes):
        super().__init__(cls)
        self.style_class = style_class
        self.attributes = attributes

    def match(self, styled):
        if not isinstance(styled, self.cls):
            return Specificity(False, False, False)
        class_match = 2 if type(styled) == self.cls else 1
        attributes_result = style_class_result = None
        if self.attributes:
            for attr, value in self.attributes.items():
                if not hasattr(styled, attr) or getattr(styled, attr) != value:
                    attributes_result = False
                    break
            else:
                attributes_result = True
        if self.style_class is not None:
            style_class_result = styled.style == self.style_class

        if False in (attributes_result, style_class_result):
            return Specificity(False, False, False)
        else:
            return Specificity(style_class_result or False,
                               attributes_result or False, class_match)


class ContextSelector(Selector):
    def __init__(self, *selectors):
        super().__init__(selectors[-1].cls)
        self.selectors = selectors

    def match(self, styled):
        total_score = Specificity(0, 0, 0)
        for selector in reversed(self.selectors):
            if styled is None:
                return Specificity(0, 0, 0)
            score = selector.match(styled)
            if not score:
                return Specificity(0, 0, 0)
            total_score += score
            styled = styled.parent
        return total_score

########NEW FILE########
__FILENAME__ = table
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


import csv

from copy import copy

from .draw import Line
from .flowable import Flowable
from .layout import VirtualContainer
from .paragraph import Paragraph, ParagraphStyle
from .dimension import PT


__all__ = ['Tabular', 'TabularStyle', 'HTMLTabularData', 'CSVTabularData',
           'TOP', 'MIDDLE', 'BOTTOM']


TOP = 'top'
MIDDLE = 'middle'
BOTTOM = 'bottom'


class CellStyle(ParagraphStyle):
    attributes = {'top_border': None,
                  'right_border': None,
                  'bottom_border': None,
                  'left_border': None,
                  'vertical_align': MIDDLE}

    def __init__(self, base=None, **attributes):
        super().__init__(base=base, **attributes)


class TabularStyle(CellStyle):
    # TODO: attributes (colgroup line style, header line style, header text style

    def __init__(self, base=None, **attributes):
        super().__init__(base=base, **attributes)
        self.cell_style = []

    def __getitem__(self, attribute):
        value = super().__getitem__(attribute)
        return value

    def set_cell_style(self, style, rows=slice(None), cols=slice(None)):
        self.cell_style.append(((rows, cols), style))
        style.base = self


class RenderedCell(object):
    def __init__(self, cell, container, x_position):
        self.cell = cell
        self.container = container
        self.x_position = x_position

    @property
    def width(self):
        return float(self.container.width)

    @property
    def height(self):
        return float(self.container.height)

    @property
    def rowspan(self):
        return self.cell.rowspan


class Tabular(Flowable):
    style_class = TabularStyle

    def __init__(self, data, style=None):
        super().__init__(style=style)
        self.data = data

    def render(self, container, last_descender, state=None):
        # TODO: allow data to override style (align)
        doc = container.document
        canvas = container.canvas
        table_width = float(container.width)
        row_heights = []
        rendered_rows = []

        # set up cell styles
        if isinstance(self.style, str):
            style = doc.styles[self.style]
        else:
            style = self._style(container.document)
        cell_styles = Array([[style for c in range(self.data.columns)]
                             for r in range(self.data.rows)])
        for (row_slice, col_slice), style in style.cell_style:
            if isinstance(row_slice, int):
                row_range = [row_slice]
            else:
                row_indices = row_slice.indices(cell_styles.rows)
                row_range = range(*row_indices)
            for ri in row_range:
                if isinstance(col_slice, int):
                    col_range = [col_slice]
                else:
                    col_indices = col_slice.indices(cell_styles.columns)
                    col_range = range(*col_indices)
                for ci in col_range:
                    old_style = cell_styles[ri][ci]
                    cell_styles[ri][ci] = copy(style)
                    cell_styles[ri][ci].base = old_style

        # calculate column widths (static)
        column_widths = []
        total_width = sum(map(lambda x: int(x['width'][:-1]),
                              self.data.column_options))
        for c, options in enumerate(self.data.column_options):
            fraction = int(options['width'][:-1])
            column_widths.append(table_width * fraction / total_width)

        # render cell content
        row_spanned_cells = {}
        for r, row in enumerate(self.data):
            rendered_row = []
            x_cursor = 0
            row_height = 0
            for c, cell in enumerate(row):
                if (r, c) in row_spanned_cells:
                    x_cursor += row_spanned_cells[r, c].width
                    continue
                elif cell is None:
                    continue
                cell_width = column_widths[c] * cell.colspan
                buffer = VirtualContainer(container, cell_width*PT)
                cell_style = cell_styles[r][c]
                self.render_cell(cell, buffer, cell_style)
                rendered_cell = RenderedCell(cell, buffer, x_cursor)
                rendered_row.append(rendered_cell)
                if cell.rowspan == 1:
                    row_height = max(row_height, rendered_cell.height)
                x_cursor += cell_width
                for i in range(r + 1, r + cell.rowspan):
                    row_spanned_cells[i, c] = rendered_cell
            row_heights.append(row_height)
            rendered_rows.append(rendered_row)

        # handle oversized vertically spanned cells
        for r, rendered_row in enumerate(rendered_rows):
            for c, rendered_cell in enumerate(rendered_row):
                if rendered_cell.rowspan > 1:
                    row_height = sum(row_heights[r:r + rendered_cell.rowspan])
                    shortage = rendered_cell.height - row_height
                    if shortage > 0:
                        padding = shortage / rendered_cell.rowspan
                        for i in range(r, r + rendered_cell.rowspan):
                            row_heights[i] += padding

        y_cursor = container.cursor
        table_height = sum(row_heights)
        container.advance(table_height)

        # place cell content and render cell border
        for r, rendered_row in enumerate(rendered_rows):
            for c, rendered_cell in enumerate(rendered_row):
                if rendered_cell.rowspan > 1:
                    row_height = sum(row_heights[r:r + rendered_cell.rowspan])
                else:
                    row_height = row_heights[r]
                x_cursor = rendered_cell.x_position
                y_pos = float(y_cursor + row_height)
                cell_width = rendered_cell.width
                border_buffer = canvas.new()
                cell_style = cell_styles[r][c]
                self.draw_cell_border(border_buffer, cell_width, row_height,
                                      cell_style)
                border_buffer.append(x_cursor, y_pos)
                if cell_style.vertical_align == MIDDLE:
                    vertical_offset = (row_height - rendered_cell.height) / 2
                elif cell_style.vertical_align == BOTTOM:
                    vertical_offset = (row_height - rendered_cell.height)
                else:
                    vertical_offset = 0
                y_offset = float(y_cursor + vertical_offset)
                rendered_cell.container.place_at(x_cursor, y_offset)
            y_cursor += row_height
        return container.width, 0

    def render_cell(self, cell, container, style):
        if cell is not None and cell.content:
            cell_par = Paragraph(cell.content, style=style, parent=self)
            return cell_par.flow(container, None)
        else:
            return 0

    def draw_cell_border(self, canvas, width, height, style):
        left, bottom, right, top = 0, 0, width, height
        if style.top_border:
            line = Line((left, top), (right, top), style.top_border)
            line.render(canvas)
        if style.right_border:
            line = Line((right, top), (right, bottom), style.right_border)
            line.render(canvas)
        if style.bottom_border:
            line = Line((left, bottom), (right, bottom), style.bottom_border)
            line.render(canvas)
        if style.left_border:
            line = Line((left, bottom), (left, top), style.left_border)
            line.render(canvas)


class Array(list):
    def __init__(self, rows):
        super().__init__(rows)

    @property
    def rows(self):
        return len(self)

    @property
    def columns(self):
        return len(self[0])


class TabularCell(object):
    def __init__(self, content, rowspan=1, colspan=1):
        self.content = content
        self.rowspan = rowspan
        self.colspan = colspan

    def __repr__(self):
        if self.content is not None:
            return self.content
        else:
            return '<empty>'


class TabularRow(list):
    def __init__(self, items):
        super().__init__(items)


class TabularData(object):
    def __init__(self, body, head=None, foot=None,
                 column_options=None, column_groups=None):
        self.body = body
        self.head = head
        self.foot = foot
        if column_options is None:
            column_groups = [body.columns]
            column_options = [{'width': '1*'} for c in range(body.columns)]
        self.column_options = column_options
        self.column_groups = column_groups

    @property
    def rows(self):
        total = self.body.rows
        if self.head:
            total += self.head.rows
        if self.foot:
            total += self.foot.rows
        return total

    @property
    def columns(self):
        return self.body.columns

    def __iter__(self):
        if self.head:
            for row in self.head:
                yield row
        for row in self.body:
            yield row
        if self.foot:
            for row in self.foot:
                yield row


class HTMLTabularData(TabularData):
    def __init__(self, element):
        try:
            body = self.parse_row_group(element.tbody)
            try:
                head = self.parse_row_group(element.thead)
            except AtrributeError:
                thead = None
            try:
                foot = self.parse_row_group(element.tfoot)
            except AtrributeError:
                foot = None
        except AttributeError:
            body = self.parse_row_group(element)
            head = foot = None
        column_groups, column_options = self.parse_column_options(element)
        super().__init__(body, head, foot, column_options, column_groups)

    def parse_column_options(self, element):
        try:
            column_groups = []
            column_options = []
            for colgroup in element.colgroup:
                span = int(colgroup.get('span', 1))
                width = colgroup.get('width')
                column_groups.append(span)
                options = [{'width': width} for c in range(span)]
                try:
                    for c, col in enumerate(colgroup.col):
                        if 'width' in col.attrib:
                            options[c]['width'] = col.get('width')
                except AttributeError:
                    pass
                column_options += options
            return column_groups, column_options
        except AttributeError:
            return None, None

    def parse_row_group(self, element):
        rows = []
        spanned_cells = []
        for r, tr in enumerate(element.tr):
            row_cells = []
            cells = tr.getchildren()
            index = c = 0
            while index < len(cells):
                if (r, c) in spanned_cells:
                    cell = None
                else:
                    rowspan = int(cells[index].get('rowspan', 1))
                    colspan = int(cells[index].get('colspan', 1))
                    cell = TabularCell(cells[index].text, rowspan, colspan)
                    if rowspan > 1 or colspan > 1:
                        for j in range(c, c + colspan):
                            for i in range(r, r + rowspan):
                                spanned_cells.append((i, j))
                    index += 1
                row_cells.append(cell)
                c += 1
            rows.append(TabularRow(row_cells))
        return Array(rows)


class CSVTabularData(TabularData):
    def __init__(self, filename):
        rows = []
        with open(filename, newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                row_cells = [TabularCell(cell) for cell in row]
                rows.append(TabularRow(row_cells))
        body = Array(rows)
        super().__init__(body)

########NEW FILE########
__FILENAME__ = text
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.

"""
Classes for describing styled text:

* :class:`SingleStyledText`: Text of a single style.
* :class:`MixedStyledText`: Text where different substrings can have different
                            styles.
* :class:`LiteralText`: Text that is typeset as is, including newlines and tabs.
* :class:`TextStyle`: Style class specifying the font and other styling of text.

A number of :class:`MixedStyledText` subclasses are provided for changing a
single style attribute of the passed text:

* :class:`Bold`
* :class:`Italic`
* :class:`Emphasized`
* :class:`SmallCaps`
* :class:`Superscript`
* :class:`Subscript`

Some characters with special properties and are represented by special classes:

* :class:`Space`
* :class:`FixedWidthSpace`
* :class:`NoBreakSpace`
* :class:`Spacer
* :class:`Tab`
* :class:`Newline`

"""

from itertools import groupby

from .dimension import PT
from .draw import BLACK
from .font.style import MEDIUM, UPRIGHT, NORMAL, BOLD, ITALIC
from .font.style import SUPERSCRIPT, SUBSCRIPT
from .fonts import adobe14
from .style import Style, Styled, PARENT_STYLE


__all__ = ['TextStyle', 'StyledText', 'SingleStyledText', 'MixedStyledText',
           'Space', 'FixedWidthSpace', 'NoBreakSpace', 'Spacer',
           'Tab', 'Newline',
           'Bold', 'Italic', 'Emphasized', 'SmallCaps', 'Superscript',
           'Subscript']


class TextStyle(Style):
    """The :class:`Style` for :class:`StyledText` objects. It has the following
    attributes:

    * `typeface`: :class:`TypeFace` to set the text in.
    * `font_weight`: Thickness of the character outlines relative to their
                     height.
    * `font_slant`: Slope of the characters.
    * `font_width`: Stretch of the characters.
    * `font_size`: Height of characters expressed in PostScript points or
                   :class:`Dimension`.
    * `small_caps`: Use small capital glyphs or not (:class:`bool`).
    * `position`: Vertical text position; normal, super- or subscript.
    * `kerning`: Improve inter-letter spacing (:class:`bool`).
    * `ligatures`: Run letters together, where possible (:class:`bool`).
    * `hyphenate`: Allow words to be broken over two lines (:class:`bool`).
    * `hyphen_chars`: Minimum number of characters in either part of a
                      hyphenated word (:class:`int`).
    * `hyphen_lang`: Language to use for hyphenation. Accepts language locale
                     codes, such as 'en_US' (:class:`str`).

    `font_weight`, `font_slant`, `font_width` and `position` accept the values
    defined in the :mod:`font.style` module.

    The default value for each of the style attributes are defined in the
    :attr:`attributes` attribute."""

    attributes = {'typeface': adobe14.times,
                  'font_weight': MEDIUM,
                  'font_slant': UPRIGHT,
                  'font_width': NORMAL,
                  'font_size': 10*PT,
                  'font_color': BLACK,
                  'small_caps': False,
                  'position': None,
                  'kerning': True,
                  'ligatures': True,
                  # TODO: character spacing
                  'hyphenate': True,
                  'hyphen_chars': 2,
                  'hyphen_lang': 'en_US'}

    def __init__(self, base=PARENT_STYLE, **attributes):
        """Initialize this text style with the given style `attributes` and
        `base` style. The default (`base` = :const:`PARENT_STYLE`) is to inherit
        the style of the parent of the :class:`Styled` element."""
        super().__init__(base=base, **attributes)


class CharacterLike(Styled):
    def __init__(self, style=PARENT_STYLE):
        super().__init__(style)

    def __repr__(self):
        return "{0}(style={1})".format(self.__class__.__name__, self.style)

    @property
    def width(self):
        raise NotImplementedError

    def height(self, document):
        raise NotImplementedError

    def render(self):
        raise NotImplementedError


class StyledText(Styled):
    """Base class for text that has a :class:`TextStyle` associated with it."""

    style_class = TextStyle

    def __init__(self, style=PARENT_STYLE, parent=None):
        """Initialize this styled text with the given `style` and `parent` (see
        :class:`Styled`). The default (`style` = :const:`PARENT_STYLE`) is to
        inherit the style of the parent of this styled text. """
        super().__init__(style, parent)

    def __add__(self, other):
        """Return the concatenation of this styled text and `other`. If `other`
        is `None`, this styled text itself is returned."""
        return MixedStyledText([self, other]) if other is not None else self

    def __radd__(self, other):
        """Return the concatenation of `other` and this styled text. If `other`
        is `None`, this styled text itself is returned."""
        return MixedStyledText([other, self]) if other is not None else self

    def __iadd__(self, other):
        """Return the concatenation of this styled text and `other`. If `other`
        is `None`, this styled text itself is returned."""
        return self + other

    position = {SUPERSCRIPT: 1 / 3,
                SUBSCRIPT: - 1 / 6}
    position_size = 583 / 1000

    def is_script(self, document):
        """Returns `True` if this styled text is super/subscript."""
        style = self._style(document)
        if style not in (PARENT_STYLE, None) and 'position' in style:
            return style.position is not None
        return False

    def script_level(self, document):
        """Nesting level of super/subscript."""
        try:
            level = self.parent.script_level(document)
        except AttributeError:
            level = -1
        return level + 1 if self.is_script(document) else level

    def height(self, document):
        """Font size after super/subscript size adjustment."""
        height = float(self.get_style('font_size', document))
        script_level = self.script_level(document)
        if script_level > -1:
            height *= self.position_size * (5 / 6)**script_level
        return height

    def y_offset(self, document):
        """Vertical baseline offset (up is positive)."""
        offset = (self.parent.y_offset(document)\
                  if hasattr(self.parent, 'y_offset') else 0)
        if self.is_script(document):
            offset += (self.parent.height(document) *
                       self.position[self._style(document).position])
            # The Y offset should only change once for the nesting level
            # where the position style is set, hence we don't recursively
            # get the position style using self.get_style('position')
        return offset

    def spans(self):
        """Generator yielding all spans in this styled text, one
        item at a time (used in typesetting)."""
        raise NotImplementedError


class SingleStyledText(StyledText):
    """Styled text where all text shares a single :class:`TextStyle`."""

    def __init__(self, text, style=PARENT_STYLE, parent=None):
        """Initialize this single-styled text with `text` (:class:`str`),
        `style`, and `parent` (see :class:`StyledText`).

        In `text`, tab, line-feed and newline characters are all considered
        whitespace. Consecutive whitespace characters are reduced to a single
        space."""
        super().__init__(style=style, parent=parent)
        self.text = text

    def __repr__(self):
        """Return a representation of this single-styled text; the text string
        along with a representation of its :class:`TextStyle`."""
        return "{0}('{1}', style={2})".format(self.__class__.__name__,
                                              self.text, self.style)

    def __str__(self):
        """Return the text content of this single-styled text."""
        return self.text

    def font(self, document):
        """The :class:`Font` described by this single-styled text's style.

        If the exact font style as described by the `font_weight`,
        `font_slant` and `font_width` style attributes is not present in the
        `typeface`, the closest font available is returned instead, and a
        warning is printed."""
        typeface = self.get_style('typeface', document)
        weight = self.get_style('font_weight', document)
        slant = self.get_style('font_slant', document)
        width = self.get_style('font_width', document)
        return typeface.get(weight=weight, slant=slant, width=width)

    def ascender(self, document):
        return (self.font(document).ascender_in_pt
                * float(self.get_style('font_size', document)))

    def descender(self, document):
        return (self.font(document).descender_in_pt
                * float(self.get_style('font_size', document)))

    def line_gap(self, document):
        return (self.font(document).line_gap_in_pt
                * float(self.get_style('font_size', document)))

    def spans(self):
        yield self

    @staticmethod
    def split_words(text):
        def is_special_character(char):
            return char in ' \t\n'

        for is_special, characters in groupby(text, is_special_character):
            if is_special:
                for char in characters:
                    yield char
            else:
                yield ''.join(characters)

    def split(self, container):
        """Yield the words and spaces in this single-styled text."""
        return self.split_words(self.text)


class MixedStyledText(StyledText, list):
    """Concatenation of :class:`StyledText` objects."""

    def __init__(self, text_or_items, style=PARENT_STYLE, parent=None):
        """Initialize this mixed-styled text as the concatenation of
        `text_or_items`, which is either a single text item or an iterable of
        text items. Individual text items can be :class:`StyledText` or
        :class:`str` objects. This mixed-styled text is set as the parent of
        each of the text items.

        See :class:`StyledText` for information on `style`, and `parent`."""
        super().__init__(style=style, parent=parent)
        if isinstance(text_or_items, (str, StyledText)):
            text_or_items = (text_or_items, )
        for item in text_or_items:
            self.append(item)

    def __repr__(self):
        """Return a representation of this mixed-styled text; its children
        along with a representation of its :class:`TextStyle`."""
        return '{}{} (style={})'.format(self.__class__.__name__,
                                        super().__repr__(), self.style)

    def __str__(self):
        """Return the text content of this mixed-styled text."""
        return ''.join(str(item) for item in self)

    def prepare(self, document):
        for item in self:
            item.prepare(document)

    def append(self, item):
        """Append `item` (:class:`StyledText` or :class:`str`) to the end of
        this mixed-styled text.

        The parent of `item` is set to this mixed-styled text."""
        if isinstance(item, str):
            item = SingleStyledText(item, style=PARENT_STYLE)
        item.parent = self
        list.append(self, item)

    def spans(self):
        """Recursively yield all the :class:`SingleStyledText` items in this
        mixed-styled text."""
        return (span for item in self for span in item.spans())


class Character(SingleStyledText):
    """:class:`SingleStyledText` consisting of a single character."""


class Space(Character):
    """A space character."""

    def __init__(self, fixed_width=False, style=PARENT_STYLE, parent=None):
        """Initialize this space. `fixed_width` specifies whether this space
        can be stretched (`False`) or not (`True`) in justified paragraphs.
        See :class:`StyledText` about `style` and `parent`."""
        super().__init__(' ', style=style, parent=parent)
        self.fixed_width = fixed_width


class FixedWidthSpace(Space):
    """A fixed-width space character."""

    def __init__(self, style=PARENT_STYLE, parent=None):
        """Initialize this fixed-width space with `style` and `parent` (see
        :class:`StyledText`)."""
        super().__init__(True, style=style, parent=parent)


class NoBreakSpace(Character):
    """Non-breaking space character.

    Lines cannot wrap at a this type of space."""

    def __init__(self, style=PARENT_STYLE, parent=None):
        """Initialize this non-breaking space with `style` and `parent` (see
        :class:`StyledText`)."""
        super().__init__(' ', style=style, parent=parent)


class Spacer(FixedWidthSpace):
    """A space of a specific width."""

    def __init__(self, width, style=PARENT_STYLE, parent=None):
        """Initialize this spacer at `width` with `style` and `parent` (see
        :class:`StyledText`)."""
        super().__init__(style=style, parent=parent)
        self._width = width

    def widths(self):
        """Generator yielding the width of this spacer."""
        yield float(self._width)


class Box(Character):
    def __init__(self, width, height, depth, ps):
        super().__init__('?')
        self._width = width
        self._height = height
        self.depth = depth
        self.ps = ps

    @property
    def width(self):
        return self._width

    def height(self, document):
        return self._height

    def render(self, canvas, x, y):
        box_canvas = canvas.new(x, y - self.depth, self.width,
                                self.height + self.depth)
        print(self.ps, file=box_canvas.psg_canvas)
        canvas.append(box_canvas)
        return self.width


class ControlCharacter(Character):
    """A non-printing character that affects typesetting of the text near it."""

    exception = Exception

    def __init__(self, char):
        """Initialize this control character with it's unicode `char`."""
        super().__init__(char)

    def __repr__(self):
        """A textual representation of this control character."""
        return self.__class__.__name__

    @property
    def width(self):
        """Raises the exception associated with this control character.

        This method is called during typesetting."""
        raise self.exception


class NewlineException(Exception):
    """Exception signaling a :class:`Newline`."""


class Newline(ControlCharacter):
    """Control character ending the current line and starting a new one."""

    exception = NewlineException

    def __init__(self, *args, **kwargs):
        """Initiatize this newline character."""
        super().__init__('\n')


class Tab(ControlCharacter):
    """Tabulator character, used for vertically aligning text."""

    def __init__(self, *args, **kwargs):
        """Initialize this tab character. Its attribute :attr:`tab_width` is set
        a later point in time when context (:class:`TabStop`) is available."""
        super().__init__('\t')


# predefined text styles

ITALIC_STYLE = EMPHASIZED_STYLE = TextStyle(font_slant=ITALIC)
BOLD_STYLE = TextStyle(font_weight=BOLD)
BOLD_ITALIC_STYLE = TextStyle(font_weight=BOLD, font_slant=ITALIC)
SMALL_CAPITALS_STYLE = TextStyle(small_caps=True)
SUPERSCRIPT_STYLE = TextStyle(position=SUPERSCRIPT)
SUBSCRIPT_STYLE = TextStyle(position=SUBSCRIPT)


class Bold(MixedStyledText):
    """Bold text."""

    def __init__(self, text):
        """Accepts a single instance of :class:`str` or :class:`StyledText`, or
        an iterable of these."""
        super().__init__(text, style=BOLD_STYLE)


class Italic(MixedStyledText):
    """Italic text."""

    def __init__(self, text, parent=None):
        """Accepts a single instance of :class:`str` or :class:`StyledText`, or
        an iterable of these."""
        super().__init__(text, style=ITALIC_STYLE, parent=parent)


class Emphasized(MixedStyledText):
    """Emphasized text."""

    def __init__(self, text, parent=None):
        """Accepts a single instance of :class:`str` or :class:`StyledText`, or
        an iterable of these."""
        super().__init__(text, style=EMPHASIZED_STYLE, parent=parent)


class SmallCaps(MixedStyledText):
    """Small capitals text."""

    def __init__(self, text, parent=None):
        """Accepts a single instance of :class:`str` or :class:`StyledText`, or
        an iterable of these."""
        super().__init__(text, style=SMALL_CAPITALS_STYLE, parent=parent)


class Superscript(MixedStyledText):
    """Superscript."""

    def __init__(self, text, parent=None):
        """Accepts a single instance of :class:`str` or :class:`StyledText`, or
        an iterable of these."""
        super().__init__(text, style=SUPERSCRIPT_STYLE, parent=parent)


class Subscript(MixedStyledText):
    """Subscript."""

    def __init__(self, text, parent=None):
        """Accepts a single instance of :class:`str` or :class:`StyledText`, or
        an iterable of these."""
        super().__init__(text, style=SUBSCRIPT_STYLE, parent=parent)

########NEW FILE########
__FILENAME__ = util
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.

"""
Collection of miscellaneous classes, functions and decorators:

* :class:`Decorator`: Superclass for decorator classes of the decorator design
                      pattern
* :func:`all_subclasses`: Generator yielding all subclasses of `cls` recursively
* :func:`intersperse`: Generator inserting an element between every two elements
                       of a given iterable
* :class:`cached_property`: Caching property decorator
* :func:`timed`: Method decorator printing the time the method call took
"""


import time

from functools import wraps


__all__ = ['Decorator', 'all_subclasses', 'intersperse', 'cached_property',
           'timed']


# functions

def all_subclasses(cls):
    """Generator yielding all subclasses of `cls` recursively"""
    for subcls in cls.__subclasses__():
        yield subcls
        for subsubcls in all_subclasses(subcls):
            yield subsubcls


def intersperse(iterable, element):
    """Generator yielding all elements of `iterable`, but with `element`
    inserted between each two consecutive elements"""
    iterable = iter(iterable)
    yield next(iterable)
    while True:
        next_from_iterable = next(iterable)
        yield element
        yield next_from_iterable


# function decorators

def consumer(function):
    """Decorator that makes a generator function automatically advance to its
    first yield point when initially called (PEP 342)."""
    @wraps(function)
    def wrapper(*args, **kwargs):
        generator = function(*args, **kwargs)
        next(generator)
        return generator
    return wrapper


def static_variable(variable_name, value):
    """Decorator that sets a static variable `variable_name` with initial value
    `value` on the decorated function."""
    def wrapper(function):
        setattr(function, variable_name, value)
        return function
    return wrapper


# method decorators

def cached(function):
    """Method decorator caching a method's returned values."""
    cache_variable = '_cached_' + function.__name__
    @wraps(function)
    def function_wrapper(obj, *args, **kwargs):
        # values are cached in a dict stored in the object
        try:
            cache = getattr(obj, cache_variable)
        except AttributeError:
            cache = {}
            setattr(obj, cache_variable, cache)
        args_kwargs = args + tuple(kwargs.values())
        try:
            return cache[args_kwargs]
        except KeyError:
            cache_value = function(obj, *args, **kwargs)
            cache[args_kwargs] = cache_value
            return cache_value
    return function_wrapper


class cached_property(property):
    """Property decorator that additionally caches the return value of the
    decorated getter method."""
    def __init__(self, function, *args, **kwargs):
        super().__init__(function, *args, **kwargs)
        self._cache_variable = '_cached_' + function.__name__

    def __get__(self, obj, *args):
        # the cached value is stored as an attribute of the object
        cache_variable = self._cache_variable
        try:
            return getattr(obj, cache_variable)
        except AttributeError:
            cache_value = super().__get__(obj, *args)
            setattr(obj, cache_variable, cache_value)
            return cache_value


def cached_generator(function):
    """Method decorator caching a generator's yielded items."""
    cache_variable = '_cached_' + function.__name__
    @wraps(function)
    def function_wrapper(obj, *args, **kwargs):
        # values are cached in a list stored in the object
        try:
            for item in getattr(obj, cache_variable):
                yield item
        except AttributeError:
            setattr(obj, cache_variable, [])
            cache = getattr(obj, cache_variable)
            for item in function(obj, *args, **kwargs):
                cache.append(item)
                yield item
    return function_wrapper


def timed(function):
    """Decorator timing the method call and printing the result to `stdout`"""
    @wraps(function)
    def function_wrapper(obj, *args, **kwargs):
        """Wrapper function printing the time taken by the call to `function`"""
        name = obj.__class__.__name__ + '.' + function.__name__
        start = time.clock()
        result = function(obj, *args, **kwargs)
        print('{}: {:.4f} seconds'.format(name, time.clock() - start))
        return result
    return function_wrapper

########NEW FILE########
__FILENAME__ = warnings
# This file is part of RinohType, the Python document preparation system.
#
# Copyright (c) Brecht Machiels.
#
# Use of this source code is subject to the terms of the GNU Affero General
# Public License v3. See the LICENSE file or http://www.gnu.org/licenses/.


import warnings
from warnings import formatwarning as standard_formatwarning
from warnings import showwarning as standard_showwarning


class RinohWarning(Warning):
    pass


def warn(message):
    warnings.warn(RinohWarning(message))


def formatwarning(message, category, filename, lineno, line=None):
    if category == RinohWarning:
        return '{}\n'.format(message.args[0])
    else:
        return standard_formatwarning(message, category, filename, lineno, line)


warnings.formatwarning = formatwarning

########NEW FILE########
__FILENAME__ = _mathtext_data
"""
font data tables for truetype and afm computer modern fonts
"""
# this dict maps symbol names to fontnames, glyphindex.  To get the
# glyph index from the character code, you have to use get_charmap

"""
from matplotlib.ft2font import FT2Font
font = FT2Font('/usr/local/share/matplotlib/cmr10.ttf')
items = font.get_charmap().items()
items.sort()

for charcode, glyphind in items:
    print charcode, glyphind
"""

latex_to_bakoma = {
    r'\oint'                     : ('cmex10',  45),
    r'\bigodot'                  : ('cmex10',  50),
    r'\bigoplus'                 : ('cmex10',  55),
    r'\bigotimes'                : ('cmex10',  59),
    r'\sum'                      : ('cmex10',  51),
    r'\prod'                     : ('cmex10',  24),
    r'\int'                      : ('cmex10',  56),
    r'\bigcup'                   : ('cmex10',  28),
    r'\bigcap'                   : ('cmex10',  60),
    r'\biguplus'                 : ('cmex10',  32),
    r'\bigwedge'                 : ('cmex10',   4),
    r'\bigvee'                   : ('cmex10',  37),
    r'\coprod'                   : ('cmex10',  42),
    r'\__sqrt__'                 : ('cmex10',  48),
    r'\leftbrace'                : ('cmex10',  92),
    r'{'                         : ('cmex10',  92),
    r'\{'                        : ('cmex10',  92),
    r'\rightbrace'               : ('cmex10', 130),
    r'}'                         : ('cmex10', 130),
    r'\}'                        : ('cmex10', 130),
    r'\leftangle'                : ('cmex10',  97),
    r'\rightangle'               : ('cmex10',  64),
    r'\langle'                   : ('cmex10',  97),
    r'\rangle'                   : ('cmex10',  64),
    r'\widehat'                  : ('cmex10',  15),
    r'\widetilde'                : ('cmex10',  52),
    r'\widebar'                  : ('cmr10',  131),

    r'\omega'                    : ('cmmi10',  29),
    r'\varepsilon'               : ('cmmi10',  20),
    r'\vartheta'                 : ('cmmi10',  22),
    r'\varrho'                   : ('cmmi10',  61),
    r'\varsigma'                 : ('cmmi10',  41),
    r'\varphi'                   : ('cmmi10',   6),
    r'\leftharpoonup'            : ('cmmi10', 108),
    r'\leftharpoondown'          : ('cmmi10',  68),
    r'\rightharpoonup'           : ('cmmi10', 117),
    r'\rightharpoondown'         : ('cmmi10',  77),
    r'\triangleright'            : ('cmmi10', 130),
    r'\triangleleft'             : ('cmmi10',  89),
    r'.'                         : ('cmmi10',  51),
    r','                         : ('cmmi10',  44),
    r'<'                         : ('cmmi10',  99),
    r'/'                         : ('cmmi10',  98),
    r'>'                         : ('cmmi10', 107),
    r'\flat'                     : ('cmmi10', 131),
    r'\natural'                  : ('cmmi10',  90),
    r'\sharp'                    : ('cmmi10',  50),
    r'\smile'                    : ('cmmi10',  97),
    r'\frown'                    : ('cmmi10',  58),
    r'\ell'                      : ('cmmi10', 102),
    r'\imath'                    : ('cmmi10',   8),
    r'\jmath'                    : ('cmmi10',  65),
    r'\wp'                       : ('cmmi10',  14),
    r'\alpha'                    : ('cmmi10',  13),
    r'\beta'                     : ('cmmi10',  35),
    r'\gamma'                    : ('cmmi10',  24),
    r'\delta'                    : ('cmmi10',  38),
    r'\epsilon'                  : ('cmmi10',  54),
    r'\zeta'                     : ('cmmi10',  10),
    r'\eta'                      : ('cmmi10',   5),
    r'\theta'                    : ('cmmi10',  18),
    r'\iota'                     : ('cmmi10',  28),
    r'\lambda'                   : ('cmmi10',   9),
    r'\mu'                       : ('cmmi10',  32),
    r'\nu'                       : ('cmmi10',  34),
    r'\xi'                       : ('cmmi10',   7),
    r'\pi'                       : ('cmmi10',  36),
    r'\kappa'                    : ('cmmi10',  30),
    r'\rho'                      : ('cmmi10',  39),
    r'\sigma'                    : ('cmmi10',  21),
    r'\tau'                      : ('cmmi10',  43),
    r'\upsilon'                  : ('cmmi10',  25),
    r'\phi'                      : ('cmmi10',  42),
    r'\chi'                      : ('cmmi10',  17),
    r'\psi'                      : ('cmmi10',  31),
    r'|'                         : ('cmsy10',  47),
    r'\|'                        : ('cmsy10',  47),
    r'('                         : ('cmr10',  119),
    r'\leftparen'                : ('cmr10',  119),
    r'\rightparen'               : ('cmr10',   68),
    r')'                         : ('cmr10',   68),
    r'+'                         : ('cmr10',   76),
    r'0'                         : ('cmr10',   40),
    r'1'                         : ('cmr10',  100),
    r'2'                         : ('cmr10',   49),
    r'3'                         : ('cmr10',  110),
    r'4'                         : ('cmr10',   59),
    r'5'                         : ('cmr10',  120),
    r'6'                         : ('cmr10',   69),
    r'7'                         : ('cmr10',  127),
    r'8'                         : ('cmr10',   77),
    r'9'                         : ('cmr10',   22),
    r'                           :'                    : ('cmr10',   85),
    r';'                         : ('cmr10',   31),
    r'='                         : ('cmr10',   41),
    r'\leftbracket'              : ('cmr10',   62),
    r'['                         : ('cmr10',   62),
    r'\rightbracket'             : ('cmr10',   72),
    r']'                         : ('cmr10',   72),
    r'\%'                        : ('cmr10',   48),
    r'%'                         : ('cmr10',   48),
    r'\$'                        : ('cmr10',   99),
    r'@'                         : ('cmr10',  111),
    r'\#'                        : ('cmr10',   39),
    r'\_'                        : ('cmtt10', 79),
    r'\Gamma'                    : ('cmr10',  19),
    r'\Delta'                    : ('cmr10',   6),
    r'\Theta'                    : ('cmr10',   7),
    r'\Lambda'                   : ('cmr10',  14),
    r'\Xi'                       : ('cmr10',   3),
    r'\Pi'                       : ('cmr10',  17),
    r'\Sigma'                    : ('cmr10',  10),
    r'\Upsilon'                  : ('cmr10',  11),
    r'\Phi'                      : ('cmr10',   9),
    r'\Psi'                      : ('cmr10',  15),
    r'\Omega'                    : ('cmr10',  12),

    # these are mathml names, I think.  I'm just using them for the
    # tex methods noted
    r'\circumflexaccent'         : ('cmr10',   124), # for \hat
    r'\combiningbreve'           : ('cmr10',   81),  # for \breve
    r'\combiningoverline'        : ('cmr10',   131),  # for \bar
    r'\combininggraveaccent'     : ('cmr10', 114), # for \grave
    r'\combiningacuteaccent'     : ('cmr10', 63), # for \accute
    r'\combiningdiaeresis'       : ('cmr10', 91), # for \ddot
    r'\combiningtilde'           : ('cmr10', 75), # for \tilde
    r'\combiningrightarrowabove' : ('cmmi10', 110), # for \vec
    r'\combiningdotabove'        : ('cmr10', 26), # for \dot

    r'\leftarrow'                : ('cmsy10',  10),
    r'\uparrow'                  : ('cmsy10',  25),
    r'\downarrow'                : ('cmsy10',  28),
    r'\leftrightarrow'           : ('cmsy10',  24),
    r'\nearrow'                  : ('cmsy10',  99),
    r'\searrow'                  : ('cmsy10',  57),
    r'\simeq'                    : ('cmsy10', 108),
    r'\Leftarrow'                : ('cmsy10', 104),
    r'\Rightarrow'               : ('cmsy10', 112),
    r'\Uparrow'                  : ('cmsy10',  60),
    r'\Downarrow'                : ('cmsy10',  68),
    r'\Leftrightarrow'           : ('cmsy10',  51),
    r'\nwarrow'                  : ('cmsy10',  65),
    r'\swarrow'                  : ('cmsy10', 116),
    r'\propto'                   : ('cmsy10',  15),
    r'\infty'                    : ('cmsy10',  32),
    r'\in'                       : ('cmsy10',  59),
    r'\ni'                       : ('cmsy10', 122),
    r'\bigtriangleup'            : ('cmsy10',  80),
    r'\bigtriangledown'          : ('cmsy10', 132),
    r'\slash'                    : ('cmsy10',  87),
    r'\forall'                   : ('cmsy10',  21),
    r'\exists'                   : ('cmsy10',   5),
    r'\neg'                      : ('cmsy10',  20),
    r'\emptyset'                 : ('cmsy10',  33),
    r'\Re'                       : ('cmsy10',  95),
    r'\Im'                       : ('cmsy10',  52),
    r'\top'                      : ('cmsy10', 100),
    r'\bot'                      : ('cmsy10',  11),
    r'\aleph'                    : ('cmsy10',  26),
    r'\cup'                      : ('cmsy10',   6),
    r'\cap'                      : ('cmsy10',  19),
    r'\uplus'                    : ('cmsy10',  58),
    r'\wedge'                    : ('cmsy10',  43),
    r'\vee'                      : ('cmsy10',  96),
    r'\vdash'                    : ('cmsy10', 109),
    r'\dashv'                    : ('cmsy10',  66),
    r'\lfloor'                   : ('cmsy10', 117),
    r'\rfloor'                   : ('cmsy10',  74),
    r'\lceil'                    : ('cmsy10', 123),
    r'\rceil'                    : ('cmsy10',  81),
    r'\lbrace'                   : ('cmsy10',  92),
    r'\rbrace'                   : ('cmsy10', 105),
    r'\mid'                      : ('cmsy10',  47),
    r'\vert'                     : ('cmsy10',  47),
    r'\Vert'                     : ('cmsy10',  44),
    r'\updownarrow'              : ('cmsy10',  94),
    r'\Updownarrow'              : ('cmsy10',  53),
    r'\backslash'                : ('cmsy10', 126),
    r'\wr'                       : ('cmsy10', 101),
    r'\nabla'                    : ('cmsy10', 110),
    r'\sqcup'                    : ('cmsy10',  67),
    r'\sqcap'                    : ('cmsy10', 118),
    r'\sqsubseteq'               : ('cmsy10',  75),
    r'\sqsupseteq'               : ('cmsy10', 124),
    r'\S'                        : ('cmsy10', 129),
    r'\dag'                      : ('cmsy10',  71),
    r'\ddag'                     : ('cmsy10', 127),
    r'\P'                        : ('cmsy10', 130),
    r'\clubsuit'                 : ('cmsy10',  18),
    r'\diamondsuit'              : ('cmsy10',  34),
    r'\heartsuit'                : ('cmsy10',  22),
    r'-'                         : ('cmsy10',  17),
    r'\cdot'                     : ('cmsy10',  78),
    r'\times'                    : ('cmsy10',  13),
    r'*'                         : ('cmsy10',   9),
    r'\ast'                      : ('cmsy10',   9),
    r'\div'                      : ('cmsy10',  31),
    r'\diamond'                  : ('cmsy10',  48),
    r'\pm'                       : ('cmsy10',   8),
    r'\mp'                       : ('cmsy10',  98),
    r'\oplus'                    : ('cmsy10',  16),
    r'\ominus'                   : ('cmsy10',  56),
    r'\otimes'                   : ('cmsy10',  30),
    r'\oslash'                   : ('cmsy10', 107),
    r'\odot'                     : ('cmsy10',  64),
    r'\bigcirc'                  : ('cmsy10', 115),
    r'\circ'                     : ('cmsy10',  72),
    r'\bullet'                   : ('cmsy10',  84),
    r'\asymp'                    : ('cmsy10', 121),
    r'\equiv'                    : ('cmsy10',  35),
    r'\subseteq'                 : ('cmsy10', 103),
    r'\supseteq'                 : ('cmsy10',  42),
    r'\leq'                      : ('cmsy10',  14),
    r'\geq'                      : ('cmsy10',  29),
    r'\preceq'                   : ('cmsy10',  79),
    r'\succeq'                   : ('cmsy10', 131),
    r'\sim'                      : ('cmsy10',  27),
    r'\approx'                   : ('cmsy10',  23),
    r'\subset'                   : ('cmsy10',  50),
    r'\supset'                   : ('cmsy10',  86),
    r'\ll'                       : ('cmsy10',  85),
    r'\gg'                       : ('cmsy10',  40),
    r'\prec'                     : ('cmsy10',  93),
    r'\succ'                     : ('cmsy10',  49),
    r'\rightarrow'               : ('cmsy10',  12),
    r'\to'                       : ('cmsy10',  12),
    r'\spadesuit'                : ('cmsy10',   7),
}

latex_to_cmex = {
    r'\__sqrt__'   : 112,
    r'\bigcap'     : 92,
    r'\bigcup'     : 91,
    r'\bigodot'    : 75,
    r'\bigoplus'   : 77,
    r'\bigotimes'  : 79,
    r'\biguplus'   : 93,
    r'\bigvee'     : 95,
    r'\bigwedge'   : 94,
    r'\coprod'     : 97,
    r'\int'        : 90,
    r'\leftangle'  : 173,
    r'\leftbrace'  : 169,
    r'\oint'       : 73,
    r'\prod'       : 89,
    r'\rightangle' : 174,
    r'\rightbrace' : 170,
    r'\sum'        : 88,
    r'\widehat'    : 98,
    r'\widetilde'  : 101,
}

latex_to_standard = {
    r'\cong'                     : ('psyr', 64),
    r'\Delta'                    : ('psyr', 68),
    r'\Phi'                      : ('psyr', 70),
    r'\Gamma'                    : ('psyr', 89),
    r'\alpha'                    : ('psyr', 97),
    r'\beta'                     : ('psyr', 98),
    r'\chi'                      : ('psyr', 99),
    r'\delta'                    : ('psyr', 100),
    r'\varepsilon'               : ('psyr', 101),
    r'\phi'                      : ('psyr', 102),
    r'\gamma'                    : ('psyr', 103),
    r'\eta'                      : ('psyr', 104),
    r'\iota'                     : ('psyr', 105),
    r'\varpsi'                   : ('psyr', 106),
    r'\kappa'                    : ('psyr', 108),
    r'\nu'                       : ('psyr', 110),
    r'\pi'                       : ('psyr', 112),
    r'\theta'                    : ('psyr', 113),
    r'\rho'                      : ('psyr', 114),
    r'\sigma'                    : ('psyr', 115),
    r'\tau'                      : ('psyr', 116),
    r'\upsilon'                  : ('psyr', 117),
    r'\varpi'                    : ('psyr', 118),
    r'\omega'                    : ('psyr', 119),
    r'\xi'                       : ('psyr', 120),
    r'\psi'                      : ('psyr', 121),
    r'\zeta'                     : ('psyr', 122),
    r'\sim'                      : ('psyr', 126),
    r'\leq'                      : ('psyr', 163),
    r'\infty'                    : ('psyr', 165),
    r'\clubsuit'                 : ('psyr', 167),
    r'\diamondsuit'              : ('psyr', 168),
    r'\heartsuit'                : ('psyr', 169),
    r'\spadesuit'                : ('psyr', 170),
    r'\leftrightarrow'           : ('psyr', 171),
    r'\leftarrow'                : ('psyr', 172),
    r'\uparrow'                  : ('psyr', 173),
    r'\rightarrow'               : ('psyr', 174),
    r'\downarrow'                : ('psyr', 175),
    r'\pm'                       : ('psyr', 176),
    r'\geq'                      : ('psyr', 179),
    r'\times'                    : ('psyr', 180),
    r'\propto'                   : ('psyr', 181),
    r'\partial'                  : ('psyr', 182),
    r'\bullet'                   : ('psyr', 183),
    r'\div'                      : ('psyr', 184),
    r'\neq'                      : ('psyr', 185),
    r'\equiv'                    : ('psyr', 186),
    r'\approx'                   : ('psyr', 187),
    r'\ldots'                    : ('psyr', 188),
    r'\aleph'                    : ('psyr', 192),
    r'\Im'                       : ('psyr', 193),
    r'\Re'                       : ('psyr', 194),
    r'\wp'                       : ('psyr', 195),
    r'\otimes'                   : ('psyr', 196),
    r'\oplus'                    : ('psyr', 197),
    r'\oslash'                   : ('psyr', 198),
    r'\cap'                      : ('psyr', 199),
    r'\cup'                      : ('psyr', 200),
    r'\supset'                   : ('psyr', 201),
    r'\supseteq'                 : ('psyr', 202),
    r'\subset'                   : ('psyr', 204),
    r'\subseteq'                 : ('psyr', 205),
    r'\in'                       : ('psyr', 206),
    r'\notin'                    : ('psyr', 207),
    r'\angle'                    : ('psyr', 208),
    r'\nabla'                    : ('psyr', 209),
    r'\textregistered'           : ('psyr', 210),
    r'\copyright'                : ('psyr', 211),
    r'\texttrademark'            : ('psyr', 212),
    r'\Pi'                       : ('psyr', 213),
    r'\prod'                     : ('psyr', 213),
    r'\surd'                     : ('psyr', 214),
    r'\__sqrt__'                 : ('psyr', 214),
    r'\cdot'                     : ('psyr', 215),
    r'\urcorner'                 : ('psyr', 216),
    r'\vee'                      : ('psyr', 217),
    r'\wedge'                    : ('psyr', 218),
    r'\Leftrightarrow'           : ('psyr', 219),
    r'\Leftarrow'                : ('psyr', 220),
    r'\Uparrow'                  : ('psyr', 221),
    r'\Rightarrow'               : ('psyr', 222),
    r'\Downarrow'                : ('psyr', 223),
    r'\Diamond'                  : ('psyr', 224),
    r'\langle'                   : ('psyr', 225),
    r'\Sigma'                    : ('psyr', 229),
    r'\sum'                      : ('psyr', 229),
    r'\forall'                   : ('psyr',  34),
    r'\exists'                   : ('psyr',  36),
    r'\lceil'                    : ('psyr', 233),
    r'\lbrace'                   : ('psyr', 123),
    r'\Psi'                      : ('psyr',  89),
    r'\bot'                      : ('psyr', 0o136),
    r'\Omega'                    : ('psyr', 0o127),
    r'\leftbracket'              : ('psyr', 0o133),
    r'\rightbracket'             : ('psyr', 0o135),
    r'\leftbrace'                : ('psyr', 123),
    r'\leftparen'                : ('psyr', 0o50),
    r'\prime'                    : ('psyr', 0o242),
    r'\sharp'                    : ('psyr', 0o43),
    r'\slash'                    : ('psyr', 0o57),
    r'\Lamda'                    : ('psyr', 0o114),
    r'\neg'                      : ('psyr', 0o330),
    r'\Upsilon'                  : ('psyr', 0o241),
    r'\rightbrace'               : ('psyr', 0o175),
    r'\rfloor'                   : ('psyr', 0o373),
    r'\lambda'                   : ('psyr', 0o154),
    r'\to'                       : ('psyr', 0o256),
    r'\Xi'                       : ('psyr', 0o130),
    r'\emptyset'                 : ('psyr', 0o306),
    r'\lfloor'                   : ('psyr', 0o353),
    r'\rightparen'               : ('psyr', 0o51),
    r'\rceil'                    : ('psyr', 0o371),
    r'\ni'                       : ('psyr', 0o47),
    r'\epsilon'                  : ('psyr', 0o145),
    r'\Theta'                    : ('psyr', 0o121),
    r'\langle'                   : ('psyr', 0o341),
    r'\leftangle'                : ('psyr', 0o341),
    r'\rangle'                   : ('psyr', 0o361),
    r'\rightangle'               : ('psyr', 0o361),
    r'\rbrace'                   : ('psyr', 0o175),
    r'\circ'                     : ('psyr', 0o260),
    r'\diamond'                  : ('psyr', 0o340),
    r'\mu'                       : ('psyr', 0o155),
    r'\mid'                      : ('psyr', 0o352),
    r'\imath'                    : ('pncri8a', 105),
    r'\%'                        : ('pncr8a',  37),
    r'\$'                        : ('pncr8a',  36),
    r'\{'                        : ('pncr8a', 123),
    r'\}'                        : ('pncr8a', 125),
    r'\backslash'                : ('pncr8a',  92),
    r'\ast'                      : ('pncr8a',  42),
    r'\#'                        : ('pncr8a',  35),

    r'\circumflexaccent'         : ('pncri8a',   124), # for \hat
    r'\combiningbreve'           : ('pncri8a',   81),  # for \breve
    r'\combininggraveaccent'     : ('pncri8a', 114), # for \grave
    r'\combiningacuteaccent'     : ('pncri8a', 63), # for \accute
    r'\combiningdiaeresis'       : ('pncri8a', 91), # for \ddot
    r'\combiningtilde'           : ('pncri8a', 75), # for \tilde
    r'\combiningrightarrowabove' : ('pncri8a', 110), # for \vec
    r'\combiningdotabove'        : ('pncri8a', 26), # for \dot
}

# Automatically generated.

type12uni = {
    'uni24C8'        : 9416,
    'aring'          : 229,
    'uni22A0'        : 8864,
    'uni2292'        : 8850,
    'quotedblright'  : 8221,
    'uni03D2'        : 978,
    'uni2215'        : 8725,
    'uni03D0'        : 976,
    'V'              : 86,
    'dollar'         : 36,
    'uni301E'        : 12318,
    'uni03D5'        : 981,
    'four'           : 52,
    'uni25A0'        : 9632,
    'uni013C'        : 316,
    'uni013B'        : 315,
    'uni013E'        : 318,
    'Yacute'         : 221,
    'uni25DE'        : 9694,
    'uni013F'        : 319,
    'uni255A'        : 9562,
    'uni2606'        : 9734,
    'uni0180'        : 384,
    'uni22B7'        : 8887,
    'uni044F'        : 1103,
    'uni22B5'        : 8885,
    'uni22B4'        : 8884,
    'uni22AE'        : 8878,
    'uni22B2'        : 8882,
    'uni22B1'        : 8881,
    'uni22B0'        : 8880,
    'uni25CD'        : 9677,
    'uni03CE'        : 974,
    'uni03CD'        : 973,
    'uni03CC'        : 972,
    'uni03CB'        : 971,
    'uni03CA'        : 970,
    'uni22B8'        : 8888,
    'uni22C9'        : 8905,
    'uni0449'        : 1097,
    'uni20DD'        : 8413,
    'uni20DC'        : 8412,
    'uni20DB'        : 8411,
    'uni2231'        : 8753,
    'uni25CF'        : 9679,
    'uni306E'        : 12398,
    'uni03D1'        : 977,
    'uni01A1'        : 417,
    'uni20D7'        : 8407,
    'uni03D6'        : 982,
    'uni2233'        : 8755,
    'uni20D2'        : 8402,
    'uni20D1'        : 8401,
    'uni20D0'        : 8400,
    'P'              : 80,
    'uni22BE'        : 8894,
    'uni22BD'        : 8893,
    'uni22BC'        : 8892,
    'uni22BB'        : 8891,
    'underscore'     : 95,
    'uni03C8'        : 968,
    'uni03C7'        : 967,
    'uni0328'        : 808,
    'uni03C5'        : 965,
    'uni03C4'        : 964,
    'uni03C3'        : 963,
    'uni03C2'        : 962,
    'uni03C1'        : 961,
    'uni03C0'        : 960,
    'uni2010'        : 8208,
    'uni0130'        : 304,
    'uni0133'        : 307,
    'uni0132'        : 306,
    'uni0135'        : 309,
    'uni0134'        : 308,
    'uni0137'        : 311,
    'uni0136'        : 310,
    'uni0139'        : 313,
    'uni0138'        : 312,
    'uni2244'        : 8772,
    'uni229A'        : 8858,
    'uni2571'        : 9585,
    'uni0278'        : 632,
    'uni2239'        : 8761,
    'p'              : 112,
    'uni3019'        : 12313,
    'uni25CB'        : 9675,
    'uni03DB'        : 987,
    'uni03DC'        : 988,
    'uni03DA'        : 986,
    'uni03DF'        : 991,
    'uni03DD'        : 989,
    'uni013D'        : 317,
    'uni220A'        : 8714,
    'uni220C'        : 8716,
    'uni220B'        : 8715,
    'uni220E'        : 8718,
    'uni220D'        : 8717,
    'uni220F'        : 8719,
    'uni22CC'        : 8908,
    'Otilde'         : 213,
    'uni25E5'        : 9701,
    'uni2736'        : 10038,
    'perthousand'    : 8240,
    'zero'           : 48,
    'uni279B'        : 10139,
    'dotlessi'       : 305,
    'uni2279'        : 8825,
    'Scaron'         : 352,
    'zcaron'         : 382,
    'uni21D8'        : 8664,
    'egrave'         : 232,
    'uni0271'        : 625,
    'uni01AA'        : 426,
    'uni2332'        : 9010,
    'section'        : 167,
    'uni25E4'        : 9700,
    'Icircumflex'    : 206,
    'ntilde'         : 241,
    'uni041E'        : 1054,
    'ampersand'      : 38,
    'uni041C'        : 1052,
    'uni041A'        : 1050,
    'uni22AB'        : 8875,
    'uni21DB'        : 8667,
    'dotaccent'      : 729,
    'uni0416'        : 1046,
    'uni0417'        : 1047,
    'uni0414'        : 1044,
    'uni0415'        : 1045,
    'uni0412'        : 1042,
    'uni0413'        : 1043,
    'degree'         : 176,
    'uni0411'        : 1041,
    'K'              : 75,
    'uni25EB'        : 9707,
    'uni25EF'        : 9711,
    'uni0418'        : 1048,
    'uni0419'        : 1049,
    'uni2263'        : 8803,
    'uni226E'        : 8814,
    'uni2251'        : 8785,
    'uni02C8'        : 712,
    'uni2262'        : 8802,
    'acircumflex'    : 226,
    'uni22B3'        : 8883,
    'uni2261'        : 8801,
    'uni2394'        : 9108,
    'Aring'          : 197,
    'uni2260'        : 8800,
    'uni2254'        : 8788,
    'uni0436'        : 1078,
    'uni2267'        : 8807,
    'k'              : 107,
    'uni22C8'        : 8904,
    'uni226A'        : 8810,
    'uni231F'        : 8991,
    'smalltilde'     : 732,
    'uni2201'        : 8705,
    'uni2200'        : 8704,
    'uni2203'        : 8707,
    'uni02BD'        : 701,
    'uni2205'        : 8709,
    'uni2204'        : 8708,
    'Agrave'         : 192,
    'uni2206'        : 8710,
    'uni2209'        : 8713,
    'uni2208'        : 8712,
    'uni226D'        : 8813,
    'uni2264'        : 8804,
    'uni263D'        : 9789,
    'uni2258'        : 8792,
    'uni02D3'        : 723,
    'uni02D2'        : 722,
    'uni02D1'        : 721,
    'uni02D0'        : 720,
    'uni25E1'        : 9697,
    'divide'         : 247,
    'uni02D5'        : 725,
    'uni02D4'        : 724,
    'ocircumflex'    : 244,
    'uni2524'        : 9508,
    'uni043A'        : 1082,
    'uni24CC'        : 9420,
    'asciitilde'     : 126,
    'uni22B9'        : 8889,
    'uni24D2'        : 9426,
    'uni211E'        : 8478,
    'uni211D'        : 8477,
    'uni24DD'        : 9437,
    'uni211A'        : 8474,
    'uni211C'        : 8476,
    'uni211B'        : 8475,
    'uni25C6'        : 9670,
    'uni017F'        : 383,
    'uni017A'        : 378,
    'uni017C'        : 380,
    'uni017B'        : 379,
    'uni0346'        : 838,
    'uni22F1'        : 8945,
    'uni22F0'        : 8944,
    'two'            : 50,
    'uni2298'        : 8856,
    'uni24D1'        : 9425,
    'E'              : 69,
    'uni025D'        : 605,
    'scaron'         : 353,
    'uni2322'        : 8994,
    'uni25E3'        : 9699,
    'uni22BF'        : 8895,
    'F'              : 70,
    'uni0440'        : 1088,
    'uni255E'        : 9566,
    'uni22BA'        : 8890,
    'uni0175'        : 373,
    'uni0174'        : 372,
    'uni0177'        : 375,
    'uni0176'        : 374,
    'bracketleft'    : 91,
    'uni0170'        : 368,
    'uni0173'        : 371,
    'uni0172'        : 370,
    'asciicircum'    : 94,
    'uni0179'        : 377,
    'uni2590'        : 9616,
    'uni25E2'        : 9698,
    'uni2119'        : 8473,
    'uni2118'        : 8472,
    'uni25CC'        : 9676,
    'f'              : 102,
    'ordmasculine'   : 186,
    'uni229B'        : 8859,
    'uni22A1'        : 8865,
    'uni2111'        : 8465,
    'uni2110'        : 8464,
    'uni2113'        : 8467,
    'uni2112'        : 8466,
    'mu'             : 181,
    'uni2281'        : 8833,
    'paragraph'      : 182,
    'nine'           : 57,
    'uni25EC'        : 9708,
    'v'              : 118,
    'uni040C'        : 1036,
    'uni0113'        : 275,
    'uni22D0'        : 8912,
    'uni21CC'        : 8652,
    'uni21CB'        : 8651,
    'uni21CA'        : 8650,
    'uni22A5'        : 8869,
    'uni21CF'        : 8655,
    'uni21CE'        : 8654,
    'uni21CD'        : 8653,
    'guilsinglleft'  : 8249,
    'backslash'      : 92,
    'uni2284'        : 8836,
    'uni224E'        : 8782,
    'uni224D'        : 8781,
    'uni224F'        : 8783,
    'uni224A'        : 8778,
    'uni2287'        : 8839,
    'uni224C'        : 8780,
    'uni224B'        : 8779,
    'uni21BD'        : 8637,
    'uni2286'        : 8838,
    'uni030F'        : 783,
    'uni030D'        : 781,
    'uni030E'        : 782,
    'uni030B'        : 779,
    'uni030C'        : 780,
    'uni030A'        : 778,
    'uni026E'        : 622,
    'uni026D'        : 621,
    'six'            : 54,
    'uni026A'        : 618,
    'uni026C'        : 620,
    'uni25C1'        : 9665,
    'uni20D6'        : 8406,
    'uni045B'        : 1115,
    'uni045C'        : 1116,
    'uni256B'        : 9579,
    'uni045A'        : 1114,
    'uni045F'        : 1119,
    'uni045E'        : 1118,
    'A'              : 65,
    'uni2569'        : 9577,
    'uni0458'        : 1112,
    'uni0459'        : 1113,
    'uni0452'        : 1106,
    'uni0453'        : 1107,
    'uni2562'        : 9570,
    'uni0451'        : 1105,
    'uni0456'        : 1110,
    'uni0457'        : 1111,
    'uni0454'        : 1108,
    'uni0455'        : 1109,
    'icircumflex'    : 238,
    'uni0307'        : 775,
    'uni0304'        : 772,
    'uni0305'        : 773,
    'uni0269'        : 617,
    'uni0268'        : 616,
    'uni0300'        : 768,
    'uni0301'        : 769,
    'uni0265'        : 613,
    'uni0264'        : 612,
    'uni0267'        : 615,
    'uni0266'        : 614,
    'uni0261'        : 609,
    'uni0260'        : 608,
    'uni0263'        : 611,
    'uni0262'        : 610,
    'a'              : 97,
    'uni2207'        : 8711,
    'uni2247'        : 8775,
    'uni2246'        : 8774,
    'uni2241'        : 8769,
    'uni2240'        : 8768,
    'uni2243'        : 8771,
    'uni2242'        : 8770,
    'uni2312'        : 8978,
    'ogonek'         : 731,
    'uni2249'        : 8777,
    'uni2248'        : 8776,
    'uni3030'        : 12336,
    'q'              : 113,
    'uni21C2'        : 8642,
    'uni21C1'        : 8641,
    'uni21C0'        : 8640,
    'uni21C7'        : 8647,
    'uni21C6'        : 8646,
    'uni21C5'        : 8645,
    'uni21C4'        : 8644,
    'uni225F'        : 8799,
    'uni212C'        : 8492,
    'uni21C8'        : 8648,
    'uni2467'        : 9319,
    'oacute'         : 243,
    'uni028F'        : 655,
    'uni028E'        : 654,
    'uni026F'        : 623,
    'uni028C'        : 652,
    'uni028B'        : 651,
    'uni028A'        : 650,
    'uni2510'        : 9488,
    'ograve'         : 242,
    'edieresis'      : 235,
    'uni22CE'        : 8910,
    'uni22CF'        : 8911,
    'uni219F'        : 8607,
    'comma'          : 44,
    'uni22CA'        : 8906,
    'uni0429'        : 1065,
    'uni03C6'        : 966,
    'uni0427'        : 1063,
    'uni0426'        : 1062,
    'uni0425'        : 1061,
    'uni0424'        : 1060,
    'uni0423'        : 1059,
    'uni0422'        : 1058,
    'uni0421'        : 1057,
    'uni0420'        : 1056,
    'uni2465'        : 9317,
    'uni24D0'        : 9424,
    'uni2464'        : 9316,
    'uni0430'        : 1072,
    'otilde'         : 245,
    'uni2661'        : 9825,
    'uni24D6'        : 9430,
    'uni2466'        : 9318,
    'uni24D5'        : 9429,
    'uni219A'        : 8602,
    'uni2518'        : 9496,
    'uni22B6'        : 8886,
    'uni2461'        : 9313,
    'uni24D4'        : 9428,
    'uni2460'        : 9312,
    'uni24EA'        : 9450,
    'guillemotright' : 187,
    'ecircumflex'    : 234,
    'greater'        : 62,
    'uni2011'        : 8209,
    'uacute'         : 250,
    'uni2462'        : 9314,
    'L'              : 76,
    'bullet'         : 8226,
    'uni02A4'        : 676,
    'uni02A7'        : 679,
    'cedilla'        : 184,
    'uni02A2'        : 674,
    'uni2015'        : 8213,
    'uni22C4'        : 8900,
    'uni22C5'        : 8901,
    'uni22AD'        : 8877,
    'uni22C7'        : 8903,
    'uni22C0'        : 8896,
    'uni2016'        : 8214,
    'uni22C2'        : 8898,
    'uni22C3'        : 8899,
    'uni24CF'        : 9423,
    'uni042F'        : 1071,
    'uni042E'        : 1070,
    'uni042D'        : 1069,
    'ydieresis'      : 255,
    'l'              : 108,
    'logicalnot'     : 172,
    'uni24CA'        : 9418,
    'uni0287'        : 647,
    'uni0286'        : 646,
    'uni0285'        : 645,
    'uni0284'        : 644,
    'uni0283'        : 643,
    'uni0282'        : 642,
    'uni0281'        : 641,
    'uni027C'        : 636,
    'uni2664'        : 9828,
    'exclamdown'     : 161,
    'uni25C4'        : 9668,
    'uni0289'        : 649,
    'uni0288'        : 648,
    'uni039A'        : 922,
    'endash'         : 8211,
    'uni2640'        : 9792,
    'uni20E4'        : 8420,
    'uni0473'        : 1139,
    'uni20E1'        : 8417,
    'uni2642'        : 9794,
    'uni03B8'        : 952,
    'uni03B9'        : 953,
    'agrave'         : 224,
    'uni03B4'        : 948,
    'uni03B5'        : 949,
    'uni03B6'        : 950,
    'uni03B7'        : 951,
    'uni03B0'        : 944,
    'uni03B1'        : 945,
    'uni03B2'        : 946,
    'uni03B3'        : 947,
    'uni2555'        : 9557,
    'Adieresis'      : 196,
    'germandbls'     : 223,
    'Odieresis'      : 214,
    'space'          : 32,
    'uni0126'        : 294,
    'uni0127'        : 295,
    'uni0124'        : 292,
    'uni0125'        : 293,
    'uni0122'        : 290,
    'uni0123'        : 291,
    'uni0120'        : 288,
    'uni0121'        : 289,
    'quoteright'     : 8217,
    'uni2560'        : 9568,
    'uni2556'        : 9558,
    'ucircumflex'    : 251,
    'uni2561'        : 9569,
    'uni2551'        : 9553,
    'uni25B2'        : 9650,
    'uni2550'        : 9552,
    'uni2563'        : 9571,
    'uni2553'        : 9555,
    'G'              : 71,
    'uni2564'        : 9572,
    'uni2552'        : 9554,
    'quoteleft'      : 8216,
    'uni2565'        : 9573,
    'uni2572'        : 9586,
    'uni2568'        : 9576,
    'uni2566'        : 9574,
    'W'              : 87,
    'uni214A'        : 8522,
    'uni012F'        : 303,
    'uni012D'        : 301,
    'uni012E'        : 302,
    'uni012B'        : 299,
    'uni012C'        : 300,
    'uni255C'        : 9564,
    'uni012A'        : 298,
    'uni2289'        : 8841,
    'Q'              : 81,
    'uni2320'        : 8992,
    'uni2321'        : 8993,
    'g'              : 103,
    'uni03BD'        : 957,
    'uni03BE'        : 958,
    'uni03BF'        : 959,
    'uni2282'        : 8834,
    'uni2285'        : 8837,
    'uni03BA'        : 954,
    'uni03BB'        : 955,
    'uni03BC'        : 956,
    'uni2128'        : 8488,
    'uni25B7'        : 9655,
    'w'              : 119,
    'uni0302'        : 770,
    'uni03DE'        : 990,
    'uni25DA'        : 9690,
    'uni0303'        : 771,
    'uni0463'        : 1123,
    'uni0462'        : 1122,
    'uni3018'        : 12312,
    'uni2514'        : 9492,
    'question'       : 63,
    'uni25B3'        : 9651,
    'uni24E1'        : 9441,
    'one'            : 49,
    'uni200A'        : 8202,
    'uni2278'        : 8824,
    'ring'           : 730,
    'uni0195'        : 405,
    'figuredash'     : 8210,
    'uni22EC'        : 8940,
    'uni0339'        : 825,
    'uni0338'        : 824,
    'uni0337'        : 823,
    'uni0336'        : 822,
    'uni0335'        : 821,
    'uni0333'        : 819,
    'uni0332'        : 818,
    'uni0331'        : 817,
    'uni0330'        : 816,
    'uni01C1'        : 449,
    'uni01C0'        : 448,
    'uni01C3'        : 451,
    'uni01C2'        : 450,
    'uni2353'        : 9043,
    'uni0308'        : 776,
    'uni2218'        : 8728,
    'uni2219'        : 8729,
    'uni2216'        : 8726,
    'uni2217'        : 8727,
    'uni2214'        : 8724,
    'uni0309'        : 777,
    'uni2609'        : 9737,
    'uni2213'        : 8723,
    'uni2210'        : 8720,
    'uni2211'        : 8721,
    'uni2245'        : 8773,
    'B'              : 66,
    'uni25D6'        : 9686,
    'iacute'         : 237,
    'uni02E6'        : 742,
    'uni02E7'        : 743,
    'uni02E8'        : 744,
    'uni02E9'        : 745,
    'uni221D'        : 8733,
    'uni221E'        : 8734,
    'Ydieresis'      : 376,
    'uni221C'        : 8732,
    'uni22D7'        : 8919,
    'uni221A'        : 8730,
    'R'              : 82,
    'uni24DC'        : 9436,
    'uni033F'        : 831,
    'uni033E'        : 830,
    'uni033C'        : 828,
    'uni033B'        : 827,
    'uni033A'        : 826,
    'b'              : 98,
    'uni228A'        : 8842,
    'uni22DB'        : 8923,
    'uni2554'        : 9556,
    'uni046B'        : 1131,
    'uni046A'        : 1130,
    'r'              : 114,
    'uni24DB'        : 9435,
    'Ccedilla'       : 199,
    'minus'          : 8722,
    'uni24DA'        : 9434,
    'uni03F0'        : 1008,
    'uni03F1'        : 1009,
    'uni20AC'        : 8364,
    'uni2276'        : 8822,
    'uni24C0'        : 9408,
    'uni0162'        : 354,
    'uni0163'        : 355,
    'uni011E'        : 286,
    'uni011D'        : 285,
    'uni011C'        : 284,
    'uni011B'        : 283,
    'uni0164'        : 356,
    'uni0165'        : 357,
    'Lslash'         : 321,
    'uni0168'        : 360,
    'uni0169'        : 361,
    'uni25C9'        : 9673,
    'uni02E5'        : 741,
    'uni21C3'        : 8643,
    'uni24C4'        : 9412,
    'uni24E2'        : 9442,
    'uni2277'        : 8823,
    'uni013A'        : 314,
    'uni2102'        : 8450,
    'Uacute'         : 218,
    'uni2317'        : 8983,
    'uni2107'        : 8455,
    'uni221F'        : 8735,
    'yacute'         : 253,
    'uni3012'        : 12306,
    'Ucircumflex'    : 219,
    'uni015D'        : 349,
    'quotedbl'       : 34,
    'uni25D9'        : 9689,
    'uni2280'        : 8832,
    'uni22AF'        : 8879,
    'onehalf'        : 189,
    'uni221B'        : 8731,
    'Thorn'          : 222,
    'uni2226'        : 8742,
    'M'              : 77,
    'uni25BA'        : 9658,
    'uni2463'        : 9315,
    'uni2336'        : 9014,
    'eight'          : 56,
    'uni2236'        : 8758,
    'multiply'       : 215,
    'uni210C'        : 8460,
    'uni210A'        : 8458,
    'uni21C9'        : 8649,
    'grave'          : 96,
    'uni210E'        : 8462,
    'uni0117'        : 279,
    'uni016C'        : 364,
    'uni0115'        : 277,
    'uni016A'        : 362,
    'uni016F'        : 367,
    'uni0112'        : 274,
    'uni016D'        : 365,
    'uni016E'        : 366,
    'Ocircumflex'    : 212,
    'uni2305'        : 8965,
    'm'              : 109,
    'uni24DF'        : 9439,
    'uni0119'        : 281,
    'uni0118'        : 280,
    'uni20A3'        : 8355,
    'uni20A4'        : 8356,
    'uni20A7'        : 8359,
    'uni2288'        : 8840,
    'uni24C3'        : 9411,
    'uni251C'        : 9500,
    'uni228D'        : 8845,
    'uni222F'        : 8751,
    'uni222E'        : 8750,
    'uni222D'        : 8749,
    'uni222C'        : 8748,
    'uni222B'        : 8747,
    'uni222A'        : 8746,
    'uni255B'        : 9563,
    'Ugrave'         : 217,
    'uni24DE'        : 9438,
    'guilsinglright' : 8250,
    'uni250A'        : 9482,
    'Ntilde'         : 209,
    'uni0279'        : 633,
    'questiondown'   : 191,
    'uni256C'        : 9580,
    'Atilde'         : 195,
    'uni0272'        : 626,
    'uni0273'        : 627,
    'uni0270'        : 624,
    'ccedilla'       : 231,
    'uni0276'        : 630,
    'uni0277'        : 631,
    'uni0274'        : 628,
    'uni0275'        : 629,
    'uni2252'        : 8786,
    'uni041F'        : 1055,
    'uni2250'        : 8784,
    'Z'              : 90,
    'uni2256'        : 8790,
    'uni2257'        : 8791,
    'copyright'      : 169,
    'uni2255'        : 8789,
    'uni043D'        : 1085,
    'uni043E'        : 1086,
    'uni043F'        : 1087,
    'yen'            : 165,
    'uni041D'        : 1053,
    'uni043B'        : 1083,
    'uni043C'        : 1084,
    'uni21B0'        : 8624,
    'uni21B1'        : 8625,
    'uni21B2'        : 8626,
    'uni21B3'        : 8627,
    'uni21B4'        : 8628,
    'uni21B5'        : 8629,
    'uni21B6'        : 8630,
    'uni21B7'        : 8631,
    'uni21B8'        : 8632,
    'Eacute'         : 201,
    'uni2311'        : 8977,
    'uni2310'        : 8976,
    'uni228F'        : 8847,
    'uni25DB'        : 9691,
    'uni21BA'        : 8634,
    'uni21BB'        : 8635,
    'uni21BC'        : 8636,
    'uni2017'        : 8215,
    'uni21BE'        : 8638,
    'uni21BF'        : 8639,
    'uni231C'        : 8988,
    'H'              : 72,
    'uni0293'        : 659,
    'uni2202'        : 8706,
    'uni22A4'        : 8868,
    'uni231E'        : 8990,
    'uni2232'        : 8754,
    'uni225B'        : 8795,
    'uni225C'        : 8796,
    'uni24D9'        : 9433,
    'uni225A'        : 8794,
    'uni0438'        : 1080,
    'uni0439'        : 1081,
    'uni225D'        : 8797,
    'uni225E'        : 8798,
    'uni0434'        : 1076,
    'X'              : 88,
    'uni007F'        : 127,
    'uni0437'        : 1079,
    'Idieresis'      : 207,
    'uni0431'        : 1073,
    'uni0432'        : 1074,
    'uni0433'        : 1075,
    'uni22AC'        : 8876,
    'uni22CD'        : 8909,
    'uni25A3'        : 9635,
    'bar'            : 124,
    'uni24BB'        : 9403,
    'uni037E'        : 894,
    'uni027B'        : 635,
    'h'              : 104,
    'uni027A'        : 634,
    'uni027F'        : 639,
    'uni027D'        : 637,
    'uni027E'        : 638,
    'uni2227'        : 8743,
    'uni2004'        : 8196,
    'uni2225'        : 8741,
    'uni2224'        : 8740,
    'uni2223'        : 8739,
    'uni2222'        : 8738,
    'uni2221'        : 8737,
    'uni2220'        : 8736,
    'x'              : 120,
    'uni2323'        : 8995,
    'uni2559'        : 9561,
    'uni2558'        : 9560,
    'uni2229'        : 8745,
    'uni2228'        : 8744,
    'udieresis'      : 252,
    'uni029D'        : 669,
    'ordfeminine'    : 170,
    'uni22CB'        : 8907,
    'uni233D'        : 9021,
    'uni0428'        : 1064,
    'uni24C6'        : 9414,
    'uni22DD'        : 8925,
    'uni24C7'        : 9415,
    'uni015C'        : 348,
    'uni015B'        : 347,
    'uni015A'        : 346,
    'uni22AA'        : 8874,
    'uni015F'        : 351,
    'uni015E'        : 350,
    'braceleft'      : 123,
    'uni24C5'        : 9413,
    'uni0410'        : 1040,
    'uni03AA'        : 938,
    'uni24C2'        : 9410,
    'uni03AC'        : 940,
    'uni03AB'        : 939,
    'macron'         : 175,
    'uni03AD'        : 941,
    'uni03AF'        : 943,
    'uni0294'        : 660,
    'uni0295'        : 661,
    'uni0296'        : 662,
    'uni0297'        : 663,
    'uni0290'        : 656,
    'uni0291'        : 657,
    'uni0292'        : 658,
    'atilde'         : 227,
    'Acircumflex'    : 194,
    'uni2370'        : 9072,
    'uni24C1'        : 9409,
    'uni0298'        : 664,
    'uni0299'        : 665,
    'Oslash'         : 216,
    'uni029E'        : 670,
    'C'              : 67,
    'quotedblleft'   : 8220,
    'uni029B'        : 667,
    'uni029C'        : 668,
    'uni03A9'        : 937,
    'uni03A8'        : 936,
    'S'              : 83,
    'uni24C9'        : 9417,
    'uni03A1'        : 929,
    'uni03A0'        : 928,
    'exclam'         : 33,
    'uni03A5'        : 933,
    'uni03A4'        : 932,
    'uni03A7'        : 935,
    'Zcaron'         : 381,
    'uni2133'        : 8499,
    'uni2132'        : 8498,
    'uni0159'        : 345,
    'uni0158'        : 344,
    'uni2137'        : 8503,
    'uni2005'        : 8197,
    'uni2135'        : 8501,
    'uni2134'        : 8500,
    'uni02BA'        : 698,
    'uni2033'        : 8243,
    'uni0151'        : 337,
    'uni0150'        : 336,
    'uni0157'        : 343,
    'equal'          : 61,
    'uni0155'        : 341,
    'uni0154'        : 340,
    's'              : 115,
    'uni233F'        : 9023,
    'eth'            : 240,
    'uni24BE'        : 9406,
    'uni21E9'        : 8681,
    'uni2060'        : 8288,
    'Egrave'         : 200,
    'uni255D'        : 9565,
    'uni24CD'        : 9421,
    'uni21E1'        : 8673,
    'uni21B9'        : 8633,
    'hyphen'         : 45,
    'uni01BE'        : 446,
    'uni01BB'        : 443,
    'period'         : 46,
    'igrave'         : 236,
    'uni01BA'        : 442,
    'uni2296'        : 8854,
    'uni2297'        : 8855,
    'uni2294'        : 8852,
    'uni2295'        : 8853,
    'colon'          : 58,
    'uni2293'        : 8851,
    'uni2290'        : 8848,
    'uni2291'        : 8849,
    'uni032D'        : 813,
    'uni032E'        : 814,
    'uni032F'        : 815,
    'uni032A'        : 810,
    'uni032B'        : 811,
    'uni032C'        : 812,
    'uni231D'        : 8989,
    'Ecircumflex'    : 202,
    'uni24D7'        : 9431,
    'uni25DD'        : 9693,
    'trademark'      : 8482,
    'Aacute'         : 193,
    'cent'           : 162,
    'uni0445'        : 1093,
    'uni266E'        : 9838,
    'uni266D'        : 9837,
    'uni266B'        : 9835,
    'uni03C9'        : 969,
    'uni2003'        : 8195,
    'uni2047'        : 8263,
    'lslash'         : 322,
    'uni03A6'        : 934,
    'uni2043'        : 8259,
    'uni250C'        : 9484,
    'uni2040'        : 8256,
    'uni255F'        : 9567,
    'uni24CB'        : 9419,
    'uni0472'        : 1138,
    'uni0446'        : 1094,
    'uni0474'        : 1140,
    'uni0475'        : 1141,
    'uni2508'        : 9480,
    'uni2660'        : 9824,
    'uni2506'        : 9478,
    'uni2502'        : 9474,
    'c'              : 99,
    'uni2500'        : 9472,
    'N'              : 78,
    'uni22A6'        : 8870,
    'uni21E7'        : 8679,
    'uni2130'        : 8496,
    'uni2002'        : 8194,
    'breve'          : 728,
    'uni0442'        : 1090,
    'Oacute'         : 211,
    'uni229F'        : 8863,
    'uni25C7'        : 9671,
    'uni229D'        : 8861,
    'uni229E'        : 8862,
    'guillemotleft'  : 171,
    'uni0329'        : 809,
    'uni24E5'        : 9445,
    'uni011F'        : 287,
    'uni0324'        : 804,
    'uni0325'        : 805,
    'uni0326'        : 806,
    'uni0327'        : 807,
    'uni0321'        : 801,
    'uni0322'        : 802,
    'n'              : 110,
    'uni2032'        : 8242,
    'uni2269'        : 8809,
    'uni2268'        : 8808,
    'uni0306'        : 774,
    'uni226B'        : 8811,
    'uni21EA'        : 8682,
    'uni0166'        : 358,
    'uni203B'        : 8251,
    'uni01B5'        : 437,
    'idieresis'      : 239,
    'uni02BC'        : 700,
    'uni01B0'        : 432,
    'braceright'     : 125,
    'seven'          : 55,
    'uni02BB'        : 699,
    'uni011A'        : 282,
    'uni29FB'        : 10747,
    'brokenbar'      : 166,
    'uni2036'        : 8246,
    'uni25C0'        : 9664,
    'uni0156'        : 342,
    'uni22D5'        : 8917,
    'uni0258'        : 600,
    'ugrave'         : 249,
    'uni22D6'        : 8918,
    'uni22D1'        : 8913,
    'uni2034'        : 8244,
    'uni22D3'        : 8915,
    'uni22D2'        : 8914,
    'uni203C'        : 8252,
    'uni223E'        : 8766,
    'uni02BF'        : 703,
    'uni22D9'        : 8921,
    'uni22D8'        : 8920,
    'uni25BD'        : 9661,
    'uni25BE'        : 9662,
    'uni25BF'        : 9663,
    'uni041B'        : 1051,
    'periodcentered' : 183,
    'uni25BC'        : 9660,
    'uni019E'        : 414,
    'uni019B'        : 411,
    'uni019A'        : 410,
    'uni2007'        : 8199,
    'uni0391'        : 913,
    'uni0390'        : 912,
    'uni0393'        : 915,
    'uni0392'        : 914,
    'uni0395'        : 917,
    'uni0394'        : 916,
    'uni0397'        : 919,
    'uni0396'        : 918,
    'uni0399'        : 921,
    'uni0398'        : 920,
    'uni25C8'        : 9672,
    'uni2468'        : 9320,
    'sterling'       : 163,
    'uni22EB'        : 8939,
    'uni039C'        : 924,
    'uni039B'        : 923,
    'uni039E'        : 926,
    'uni039D'        : 925,
    'uni039F'        : 927,
    'I'              : 73,
    'uni03E1'        : 993,
    'uni03E0'        : 992,
    'uni2319'        : 8985,
    'uni228B'        : 8843,
    'uni25B5'        : 9653,
    'uni25B6'        : 9654,
    'uni22EA'        : 8938,
    'uni24B9'        : 9401,
    'uni044E'        : 1102,
    'uni0199'        : 409,
    'uni2266'        : 8806,
    'Y'              : 89,
    'uni22A2'        : 8866,
    'Eth'            : 208,
    'uni266F'        : 9839,
    'emdash'         : 8212,
    'uni263B'        : 9787,
    'uni24BD'        : 9405,
    'uni22DE'        : 8926,
    'uni0360'        : 864,
    'uni2557'        : 9559,
    'uni22DF'        : 8927,
    'uni22DA'        : 8922,
    'uni22DC'        : 8924,
    'uni0361'        : 865,
    'i'              : 105,
    'uni24BF'        : 9407,
    'uni0362'        : 866,
    'uni263E'        : 9790,
    'uni028D'        : 653,
    'uni2259'        : 8793,
    'uni0323'        : 803,
    'uni2265'        : 8805,
    'daggerdbl'      : 8225,
    'y'              : 121,
    'uni010A'        : 266,
    'plusminus'      : 177,
    'less'           : 60,
    'uni21AE'        : 8622,
    'uni0315'        : 789,
    'uni230B'        : 8971,
    'uni21AF'        : 8623,
    'uni21AA'        : 8618,
    'uni21AC'        : 8620,
    'uni21AB'        : 8619,
    'uni01FB'        : 507,
    'uni01FC'        : 508,
    'uni223A'        : 8762,
    'uni01FA'        : 506,
    'uni01FF'        : 511,
    'uni01FD'        : 509,
    'uni01FE'        : 510,
    'uni2567'        : 9575,
    'uni25E0'        : 9696,
    'uni0104'        : 260,
    'uni0105'        : 261,
    'uni0106'        : 262,
    'uni0107'        : 263,
    'uni0100'        : 256,
    'uni0101'        : 257,
    'uni0102'        : 258,
    'uni0103'        : 259,
    'uni2038'        : 8248,
    'uni2009'        : 8201,
    'uni2008'        : 8200,
    'uni0108'        : 264,
    'uni0109'        : 265,
    'uni02A1'        : 673,
    'uni223B'        : 8763,
    'uni226C'        : 8812,
    'uni25AC'        : 9644,
    'uni24D3'        : 9427,
    'uni21E0'        : 8672,
    'uni21E3'        : 8675,
    'Udieresis'      : 220,
    'uni21E2'        : 8674,
    'D'              : 68,
    'uni21E5'        : 8677,
    'uni2621'        : 9761,
    'uni21D1'        : 8657,
    'uni203E'        : 8254,
    'uni22C6'        : 8902,
    'uni21E4'        : 8676,
    'uni010D'        : 269,
    'uni010E'        : 270,
    'uni010F'        : 271,
    'five'           : 53,
    'T'              : 84,
    'uni010B'        : 267,
    'uni010C'        : 268,
    'uni2605'        : 9733,
    'uni2663'        : 9827,
    'uni21E6'        : 8678,
    'uni24B6'        : 9398,
    'uni22C1'        : 8897,
    'oslash'         : 248,
    'acute'          : 180,
    'uni01F0'        : 496,
    'd'              : 100,
    'OE'             : 338,
    'uni22E3'        : 8931,
    'Igrave'         : 204,
    'uni2308'        : 8968,
    'uni2309'        : 8969,
    'uni21A9'        : 8617,
    't'              : 116,
    'uni2313'        : 8979,
    'uni03A3'        : 931,
    'uni21A4'        : 8612,
    'uni21A7'        : 8615,
    'uni21A6'        : 8614,
    'uni21A1'        : 8609,
    'uni21A0'        : 8608,
    'uni21A3'        : 8611,
    'uni21A2'        : 8610,
    'parenright'     : 41,
    'uni256A'        : 9578,
    'uni25DC'        : 9692,
    'uni24CE'        : 9422,
    'uni042C'        : 1068,
    'uni24E0'        : 9440,
    'uni042B'        : 1067,
    'uni0409'        : 1033,
    'uni0408'        : 1032,
    'uni24E7'        : 9447,
    'uni25B4'        : 9652,
    'uni042A'        : 1066,
    'uni228E'        : 8846,
    'uni0401'        : 1025,
    'adieresis'      : 228,
    'uni0403'        : 1027,
    'quotesingle'    : 39,
    'uni0405'        : 1029,
    'uni0404'        : 1028,
    'uni0407'        : 1031,
    'uni0406'        : 1030,
    'uni229C'        : 8860,
    'uni2306'        : 8966,
    'uni2253'        : 8787,
    'twodotenleader' : 8229,
    'uni2131'        : 8497,
    'uni21DA'        : 8666,
    'uni2234'        : 8756,
    'uni2235'        : 8757,
    'uni01A5'        : 421,
    'uni2237'        : 8759,
    'uni2230'        : 8752,
    'uni02CC'        : 716,
    'slash'          : 47,
    'uni01A0'        : 416,
    'ellipsis'       : 8230,
    'uni2299'        : 8857,
    'uni2238'        : 8760,
    'numbersign'     : 35,
    'uni21A8'        : 8616,
    'uni223D'        : 8765,
    'uni01AF'        : 431,
    'uni223F'        : 8767,
    'uni01AD'        : 429,
    'uni01AB'        : 427,
    'odieresis'      : 246,
    'uni223C'        : 8764,
    'uni227D'        : 8829,
    'uni0280'        : 640,
    'O'              : 79,
    'uni227E'        : 8830,
    'uni21A5'        : 8613,
    'uni22D4'        : 8916,
    'uni25D4'        : 9684,
    'uni227F'        : 8831,
    'uni0435'        : 1077,
    'uni2302'        : 8962,
    'uni2669'        : 9833,
    'uni24E3'        : 9443,
    'uni2720'        : 10016,
    'uni22A8'        : 8872,
    'uni22A9'        : 8873,
    'uni040A'        : 1034,
    'uni22A7'        : 8871,
    'oe'             : 339,
    'uni040B'        : 1035,
    'uni040E'        : 1038,
    'uni22A3'        : 8867,
    'o'              : 111,
    'uni040F'        : 1039,
    'Edieresis'      : 203,
    'uni25D5'        : 9685,
    'plus'           : 43,
    'uni044D'        : 1101,
    'uni263C'        : 9788,
    'uni22E6'        : 8934,
    'uni2283'        : 8835,
    'uni258C'        : 9612,
    'uni219E'        : 8606,
    'uni24E4'        : 9444,
    'uni2136'        : 8502,
    'dagger'         : 8224,
    'uni24B7'        : 9399,
    'uni219B'        : 8603,
    'uni22E5'        : 8933,
    'three'          : 51,
    'uni210B'        : 8459,
    'uni2534'        : 9524,
    'uni24B8'        : 9400,
    'uni230A'        : 8970,
    'hungarumlaut'   : 733,
    'parenleft'      : 40,
    'uni0148'        : 328,
    'uni0149'        : 329,
    'uni2124'        : 8484,
    'uni2125'        : 8485,
    'uni2126'        : 8486,
    'uni2127'        : 8487,
    'uni0140'        : 320,
    'uni2129'        : 8489,
    'uni25C5'        : 9669,
    'uni0143'        : 323,
    'uni0144'        : 324,
    'uni0145'        : 325,
    'uni0146'        : 326,
    'uni0147'        : 327,
    'uni210D'        : 8461,
    'fraction'       : 8260,
    'uni2031'        : 8241,
    'uni2196'        : 8598,
    'uni2035'        : 8245,
    'uni24E6'        : 9446,
    'uni016B'        : 363,
    'uni24BA'        : 9402,
    'uni266A'        : 9834,
    'uni0116'        : 278,
    'uni2115'        : 8469,
    'registered'     : 174,
    'J'              : 74,
    'uni25DF'        : 9695,
    'uni25CE'        : 9678,
    'uni273D'        : 10045,
    'dieresis'       : 168,
    'uni212B'        : 8491,
    'uni0114'        : 276,
    'uni212D'        : 8493,
    'uni212E'        : 8494,
    'uni212F'        : 8495,
    'uni014A'        : 330,
    'uni014B'        : 331,
    'uni014C'        : 332,
    'uni014D'        : 333,
    'uni014E'        : 334,
    'uni014F'        : 335,
    'uni025E'        : 606,
    'uni24E8'        : 9448,
    'uni0111'        : 273,
    'uni24E9'        : 9449,
    'Ograve'         : 210,
    'j'              : 106,
    'uni2195'        : 8597,
    'uni2194'        : 8596,
    'uni2197'        : 8599,
    'uni2037'        : 8247,
    'uni2191'        : 8593,
    'uni2190'        : 8592,
    'uni2193'        : 8595,
    'uni2192'        : 8594,
    'uni29FA'        : 10746,
    'uni2713'        : 10003,
    'z'              : 122,
    'uni2199'        : 8601,
    'uni2198'        : 8600,
    'uni2667'        : 9831,
    'ae'             : 230,
    'uni0448'        : 1096,
    'semicolon'      : 59,
    'uni2666'        : 9830,
    'uni038F'        : 911,
    'uni0444'        : 1092,
    'uni0447'        : 1095,
    'uni038E'        : 910,
    'uni0441'        : 1089,
    'uni038C'        : 908,
    'uni0443'        : 1091,
    'uni038A'        : 906,
    'uni0250'        : 592,
    'uni0251'        : 593,
    'uni0252'        : 594,
    'uni0253'        : 595,
    'uni0254'        : 596,
    'at'             : 64,
    'uni0256'        : 598,
    'uni0257'        : 599,
    'uni0167'        : 359,
    'uni0259'        : 601,
    'uni228C'        : 8844,
    'uni2662'        : 9826,
    'uni0319'        : 793,
    'uni0318'        : 792,
    'uni24BC'        : 9404,
    'uni0402'        : 1026,
    'uni22EF'        : 8943,
    'Iacute'         : 205,
    'uni22ED'        : 8941,
    'uni22EE'        : 8942,
    'uni0311'        : 785,
    'uni0310'        : 784,
    'uni21E8'        : 8680,
    'uni0312'        : 786,
    'percent'        : 37,
    'uni0317'        : 791,
    'uni0316'        : 790,
    'uni21D6'        : 8662,
    'uni21D7'        : 8663,
    'uni21D4'        : 8660,
    'uni21D5'        : 8661,
    'uni21D2'        : 8658,
    'uni21D3'        : 8659,
    'uni21D0'        : 8656,
    'uni2138'        : 8504,
    'uni2270'        : 8816,
    'uni2271'        : 8817,
    'uni2272'        : 8818,
    'uni2273'        : 8819,
    'uni2274'        : 8820,
    'uni2275'        : 8821,
    'bracketright'   : 93,
    'uni21D9'        : 8665,
    'uni21DF'        : 8671,
    'uni21DD'        : 8669,
    'uni21DE'        : 8670,
    'AE'             : 198,
    'uni03AE'        : 942,
    'uni227A'        : 8826,
    'uni227B'        : 8827,
    'uni227C'        : 8828,
    'asterisk'       : 42,
    'aacute'         : 225,
    'uni226F'        : 8815,
    'uni22E2'        : 8930,
    'uni0386'        : 902,
    'uni22E0'        : 8928,
    'uni22E1'        : 8929,
    'U'              : 85,
    'uni22E7'        : 8935,
    'uni22E4'        : 8932,
    'uni0387'        : 903,
    'uni031A'        : 794,
    'eacute'         : 233,
    'uni22E8'        : 8936,
    'uni22E9'        : 8937,
    'uni24D8'        : 9432,
    'uni025A'        : 602,
    'uni025B'        : 603,
    'uni025C'        : 604,
    'e'              : 101,
    'uni0128'        : 296,
    'uni025F'        : 607,
    'uni2665'        : 9829,
    'thorn'          : 254,
    'uni0129'        : 297,
    'uni253C'        : 9532,
    'uni25D7'        : 9687,
    'u'              : 117,
    'uni0388'        : 904,
    'uni0389'        : 905,
    'uni0255'        : 597,
    'uni0171'        : 369,
    'uni0384'        : 900,
    'uni0385'        : 901,
    'uni044A'        : 1098,
    'uni252C'        : 9516,
    'uni044C'        : 1100,
    'uni044B'        : 1099
}

uni2type1 = dict(((v,k) for k,v in type12uni.items()))

tex2uni = {
    'widehat'                  : 0x0302,
    'widetilde'                : 0x0303,
    'widebar'                  : 0x0305,
    'langle'                   : 0x27e8,
    'rangle'                   : 0x27e9,
    'perp'                     : 0x27c2,
    'neq'                      : 0x2260,
    'Join'                     : 0x2a1d,
    'leqslant'                 : 0x2a7d,
    'geqslant'                 : 0x2a7e,
    'lessapprox'               : 0x2a85,
    'gtrapprox'                : 0x2a86,
    'lesseqqgtr'               : 0x2a8b,
    'gtreqqless'               : 0x2a8c,
    'triangleeq'               : 0x225c,
    'eqslantless'              : 0x2a95,
    'eqslantgtr'               : 0x2a96,
    'backepsilon'              : 0x03f6,
    'precapprox'               : 0x2ab7,
    'succapprox'               : 0x2ab8,
    'fallingdotseq'            : 0x2252,
    'subseteqq'                : 0x2ac5,
    'supseteqq'                : 0x2ac6,
    'varpropto'                : 0x221d,
    'precnapprox'              : 0x2ab9,
    'succnapprox'              : 0x2aba,
    'subsetneqq'               : 0x2acb,
    'supsetneqq'               : 0x2acc,
    'lnapprox'                 : 0x2ab9,
    'gnapprox'                 : 0x2aba,
    'longleftarrow'            : 0x27f5,
    'longrightarrow'           : 0x27f6,
    'longleftrightarrow'       : 0x27f7,
    'Longleftarrow'            : 0x27f8,
    'Longrightarrow'           : 0x27f9,
    'Longleftrightarrow'       : 0x27fa,
    'longmapsto'               : 0x27fc,
    'leadsto'                  : 0x21dd,
    'dashleftarrow'            : 0x290e,
    'dashrightarrow'           : 0x290f,
    'circlearrowleft'          : 0x21ba,
    'circlearrowright'         : 0x21bb,
    'leftrightsquigarrow'      : 0x21ad,
    'leftsquigarrow'           : 0x219c,
    'rightsquigarrow'          : 0x219d,
    'Game'                     : 0x2141,
    'hbar'                     : 0x0127,
    'hslash'                   : 0x210f,
    'ldots'                    : 0x2026,
    'vdots'                    : 0x22ee,
    'doteqdot'                 : 0x2251,
    'doteq'                    : 8784,
    'partial'                  : 8706,
    'gg'                       : 8811,
    'asymp'                    : 8781,
    'blacktriangledown'        : 9662,
    'otimes'                   : 8855,
    'nearrow'                  : 8599,
    'varpi'                    : 982,
    'vee'                      : 8744,
    'vec'                      : 8407,
    'smile'                    : 8995,
    'succnsim'                 : 8937,
    'gimel'                    : 8503,
    'vert'                     : 124,
    '|'                        : 124,
    'varrho'                   : 1009,
    'P'                        : 182,
    'approxident'              : 8779,
    'Swarrow'                  : 8665,
    'textasciicircum'          : 94,
    'imageof'                  : 8887,
    'ntriangleleft'            : 8938,
    'nleq'                     : 8816,
    'div'                      : 247,
    'nparallel'                : 8742,
    'Leftarrow'                : 8656,
    'lll'                      : 8920,
    'oiint'                    : 8751,
    'ngeq'                     : 8817,
    'Theta'                    : 920,
    'origof'                   : 8886,
    'blacksquare'              : 9632,
    'solbar'                   : 9023,
    'neg'                      : 172,
    'sum'                      : 8721,
    'Vdash'                    : 8873,
    'coloneq'                  : 8788,
    'degree'                   : 176,
    'bowtie'                   : 8904,
    'blacktriangleright'       : 9654,
    'varsigma'                 : 962,
    'leq'                      : 8804,
    'ggg'                      : 8921,
    'lneqq'                    : 8808,
    'scurel'                   : 8881,
    'stareq'                   : 8795,
    'BbbN'                     : 8469,
    'nLeftarrow'               : 8653,
    'nLeftrightarrow'          : 8654,
    'k'                        : 808,
    'bot'                      : 8869,
    'BbbC'                     : 8450,
    'Lsh'                      : 8624,
    'leftleftarrows'           : 8647,
    'BbbZ'                     : 8484,
    'digamma'                  : 989,
    'BbbR'                     : 8477,
    'BbbP'                     : 8473,
    'BbbQ'                     : 8474,
    'vartriangleright'         : 8883,
    'succsim'                  : 8831,
    'wedge'                    : 8743,
    'lessgtr'                  : 8822,
    'veebar'                   : 8891,
    'mapsdown'                 : 8615,
    'Rsh'                      : 8625,
    'chi'                      : 967,
    'prec'                     : 8826,
    'nsubseteq'                : 8840,
    'therefore'                : 8756,
    'eqcirc'                   : 8790,
    'textexclamdown'           : 161,
    'nRightarrow'              : 8655,
    'flat'                     : 9837,
    'notin'                    : 8713,
    'llcorner'                 : 8990,
    'varepsilon'               : 949,
    'bigtriangleup'            : 9651,
    'aleph'                    : 8501,
    'dotminus'                 : 8760,
    'upsilon'                  : 965,
    'Lambda'                   : 923,
    'cap'                      : 8745,
    'barleftarrow'             : 8676,
    'mu'                       : 956,
    'boxplus'                  : 8862,
    'mp'                       : 8723,
    'circledast'               : 8859,
    'tau'                      : 964,
    'in'                       : 8712,
    'backslash'                : 92,
    'varnothing'               : 8709,
    'sharp'                    : 9839,
    'eqsim'                    : 8770,
    'gnsim'                    : 8935,
    'Searrow'                  : 8664,
    'updownarrows'             : 8645,
    'heartsuit'                : 9825,
    'trianglelefteq'           : 8884,
    'ddag'                     : 8225,
    'sqsubseteq'               : 8849,
    'mapsfrom'                 : 8612,
    'boxbar'                   : 9707,
    'sim'                      : 8764,
    'Nwarrow'                  : 8662,
    'nequiv'                   : 8802,
    'succ'                     : 8827,
    'vdash'                    : 8866,
    'Leftrightarrow'           : 8660,
    'parallel'                 : 8741,
    'invnot'                   : 8976,
    'natural'                  : 9838,
    'ss'                       : 223,
    'uparrow'                  : 8593,
    'nsim'                     : 8769,
    'hookrightarrow'           : 8618,
    'Equiv'                    : 8803,
    'approx'                   : 8776,
    'Vvdash'                   : 8874,
    'nsucc'                    : 8833,
    'leftrightharpoons'        : 8651,
    'Re'                       : 8476,
    'boxminus'                 : 8863,
    'equiv'                    : 8801,
    'Lleftarrow'               : 8666,
    'thinspace'                : 8201,
    'll'                       : 8810,
    'Cup'                      : 8915,
    'measeq'                   : 8798,
    'upharpoonleft'            : 8639,
    'lq'                       : 8216,
    'Upsilon'                  : 933,
    'subsetneq'                : 8842,
    'greater'                  : 62,
    'supsetneq'                : 8843,
    'Cap'                      : 8914,
    'L'                        : 321,
    'spadesuit'                : 9824,
    'lrcorner'                 : 8991,
    'not'                      : 824,
    'bar'                      : 772,
    'rightharpoonaccent'       : 8401,
    'boxdot'                   : 8865,
    'l'                        : 322,
    'leftharpoondown'          : 8637,
    'bigcup'                   : 8899,
    'iint'                     : 8748,
    'bigwedge'                 : 8896,
    'downharpoonleft'          : 8643,
    'textasciitilde'           : 126,
    'subset'                   : 8834,
    'leqq'                     : 8806,
    'mapsup'                   : 8613,
    'nvDash'                   : 8877,
    'looparrowleft'            : 8619,
    'nless'                    : 8814,
    'rightarrowbar'            : 8677,
    'Vert'                     : 8214,
    'downdownarrows'           : 8650,
    'uplus'                    : 8846,
    'simeq'                    : 8771,
    'napprox'                  : 8777,
    'ast'                      : 8727,
    'twoheaduparrow'           : 8607,
    'doublebarwedge'           : 8966,
    'Sigma'                    : 931,
    'leftharpoonaccent'        : 8400,
    'ntrianglelefteq'          : 8940,
    'nexists'                  : 8708,
    'times'                    : 215,
    'measuredangle'            : 8737,
    'bumpeq'                   : 8783,
    'carriagereturn'           : 8629,
    'adots'                    : 8944,
    'checkmark'                : 10003,
    'lambda'                   : 955,
    'xi'                       : 958,
    'rbrace'                   : 125,
    'rbrack'                   : 93,
    'Nearrow'                  : 8663,
    'maltese'                  : 10016,
    'clubsuit'                 : 9827,
    'top'                      : 8868,
    'overarc'                  : 785,
    'varphi'                   : 966,
    'Delta'                    : 916,
    'iota'                     : 953,
    'nleftarrow'               : 8602,
    'candra'                   : 784,
    'supset'                   : 8835,
    'triangleleft'             : 9665,
    'gtreqless'                : 8923,
    'ntrianglerighteq'         : 8941,
    'quad'                     : 8195,
    'Xi'                       : 926,
    'gtrdot'                   : 8919,
    'leftthreetimes'           : 8907,
    'minus'                    : 8722,
    'preccurlyeq'              : 8828,
    'nleftrightarrow'          : 8622,
    'lambdabar'                : 411,
    'blacktriangle'            : 9652,
    'kernelcontraction'        : 8763,
    'Phi'                      : 934,
    'angle'                    : 8736,
    'spadesuitopen'            : 9828,
    'eqless'                   : 8924,
    'mid'                      : 8739,
    'varkappa'                 : 1008,
    'Ldsh'                     : 8626,
    'updownarrow'              : 8597,
    'beta'                     : 946,
    'textquotedblleft'         : 8220,
    'rho'                      : 961,
    'alpha'                    : 945,
    'intercal'                 : 8890,
    'beth'                     : 8502,
    'grave'                    : 768,
    'acwopencirclearrow'       : 8634,
    'nmid'                     : 8740,
    'nsupset'                  : 8837,
    'sigma'                    : 963,
    'dot'                      : 775,
    'Rightarrow'               : 8658,
    'turnednot'                : 8985,
    'backsimeq'                : 8909,
    'leftarrowtail'            : 8610,
    'approxeq'                 : 8778,
    'curlyeqsucc'              : 8927,
    'rightarrowtail'           : 8611,
    'Psi'                      : 936,
    'copyright'                : 169,
    'yen'                      : 165,
    'vartriangleleft'          : 8882,
    'rasp'                     : 700,
    'triangleright'            : 9655,
    'precsim'                  : 8830,
    'infty'                    : 8734,
    'geq'                      : 8805,
    'updownarrowbar'           : 8616,
    'precnsim'                 : 8936,
    'H'                        : 779,
    'ulcorner'                 : 8988,
    'looparrowright'           : 8620,
    'ncong'                    : 8775,
    'downarrow'                : 8595,
    'circeq'                   : 8791,
    'subseteq'                 : 8838,
    'bigstar'                  : 9733,
    'prime'                    : 8242,
    'lceil'                    : 8968,
    'Rrightarrow'              : 8667,
    'oiiint'                   : 8752,
    'curlywedge'               : 8911,
    'vDash'                    : 8872,
    'lfloor'                   : 8970,
    'ddots'                    : 8945,
    'exists'                   : 8707,
    'underbar'                 : 817,
    'Pi'                       : 928,
    'leftrightarrows'          : 8646,
    'sphericalangle'           : 8738,
    'coprod'                   : 8720,
    'circledcirc'              : 8858,
    'gtrsim'                   : 8819,
    'gneqq'                    : 8809,
    'between'                  : 8812,
    'theta'                    : 952,
    'complement'               : 8705,
    'arceq'                    : 8792,
    'nVdash'                   : 8878,
    'S'                        : 167,
    'wr'                       : 8768,
    'wp'                       : 8472,
    'backcong'                 : 8780,
    'lasp'                     : 701,
    'c'                        : 807,
    'nabla'                    : 8711,
    'dotplus'                  : 8724,
    'eta'                      : 951,
    'forall'                   : 8704,
    'eth'                      : 240,
    'colon'                    : 58,
    'sqcup'                    : 8852,
    'rightrightarrows'         : 8649,
    'sqsupset'                 : 8848,
    'mapsto'                   : 8614,
    'bigtriangledown'          : 9661,
    'sqsupseteq'               : 8850,
    'propto'                   : 8733,
    'pi'                       : 960,
    'pm'                       : 177,
    'dots'                     : 0x2026,
    'nrightarrow'              : 8603,
    'textasciiacute'           : 180,
    'Doteq'                    : 8785,
    'breve'                    : 774,
    'sqcap'                    : 8851,
    'twoheadrightarrow'        : 8608,
    'kappa'                    : 954,
    'vartriangle'              : 9653,
    'diamondsuit'              : 9826,
    'pitchfork'                : 8916,
    'blacktriangleleft'        : 9664,
    'nprec'                    : 8832,
    'vdots'                    : 8942,
    'curvearrowright'          : 8631,
    'barwedge'                 : 8892,
    'multimap'                 : 8888,
    'textquestiondown'         : 191,
    'cong'                     : 8773,
    'rtimes'                   : 8906,
    'rightzigzagarrow'         : 8669,
    'rightarrow'               : 8594,
    'leftarrow'                : 8592,
    '__sqrt__'                 : 8730,
    'twoheaddownarrow'         : 8609,
    'oint'                     : 8750,
    'bigvee'                   : 8897,
    'eqdef'                    : 8797,
    'sterling'                 : 163,
    'phi'                      : 981,
    'Updownarrow'              : 8661,
    'backprime'                : 8245,
    'emdash'                   : 8212,
    'Gamma'                    : 915,
    'i'                        : 305,
    'rceil'                    : 8969,
    'leftharpoonup'            : 8636,
    'Im'                       : 8465,
    'curvearrowleft'           : 8630,
    'wedgeq'                   : 8793,
    'fallingdotseq'            : 8786,
    'curlyeqprec'              : 8926,
    'questeq'                  : 8799,
    'less'                     : 60,
    'upuparrows'               : 8648,
    'tilde'                    : 771,
    'textasciigrave'           : 96,
    'smallsetminus'            : 8726,
    'ell'                      : 8467,
    'cup'                      : 8746,
    'danger'                   : 9761,
    'nVDash'                   : 8879,
    'cdotp'                    : 183,
    'cdots'                    : 8943,
    'hat'                      : 770,
    'eqgtr'                    : 8925,
    'enspace'                  : 8194,
    'psi'                      : 968,
    'frown'                    : 8994,
    'acute'                    : 769,
    'downzigzagarrow'          : 8623,
    'ntriangleright'           : 8939,
    'cupdot'                   : 8845,
    'circleddash'              : 8861,
    'oslash'                   : 8856,
    'mho'                      : 8487,
    'd'                        : 803,
    'sqsubset'                 : 8847,
    'cdot'                     : 8901,
    'Omega'                    : 937,
    'OE'                       : 338,
    'veeeq'                    : 8794,
    'Finv'                     : 8498,
    't'                        : 865,
    'leftrightarrow'           : 8596,
    'swarrow'                  : 8601,
    'rightthreetimes'          : 8908,
    'rightleftharpoons'        : 8652,
    'lesssim'                  : 8818,
    'searrow'                  : 8600,
    'because'                  : 8757,
    'gtrless'                  : 8823,
    'star'                     : 8902,
    'nsubset'                  : 8836,
    'zeta'                     : 950,
    'dddot'                    : 8411,
    'bigcirc'                  : 9675,
    'Supset'                   : 8913,
    'circ'                     : 8728,
    'slash'                    : 8725,
    'ocirc'                    : 778,
    'prod'                     : 8719,
    'twoheadleftarrow'         : 8606,
    'daleth'                   : 8504,
    'upharpoonright'           : 8638,
    'odot'                     : 8857,
    'Uparrow'                  : 8657,
    'O'                        : 216,
    'hookleftarrow'            : 8617,
    'trianglerighteq'          : 8885,
    'nsime'                    : 8772,
    'oe'                       : 339,
    'nwarrow'                  : 8598,
    'o'                        : 248,
    'ddddot'                   : 8412,
    'downharpoonright'         : 8642,
    'succcurlyeq'              : 8829,
    'gamma'                    : 947,
    'scrR'                     : 8475,
    'dag'                      : 8224,
    'thickspace'               : 8197,
    'frakZ'                    : 8488,
    'lessdot'                  : 8918,
    'triangledown'             : 9663,
    'ltimes'                   : 8905,
    'scrB'                     : 8492,
    'endash'                   : 8211,
    'scrE'                     : 8496,
    'scrF'                     : 8497,
    'scrH'                     : 8459,
    'scrI'                     : 8464,
    'rightharpoondown'         : 8641,
    'scrL'                     : 8466,
    'scrM'                     : 8499,
    'frakC'                    : 8493,
    'nsupseteq'                : 8841,
    'circledR'                 : 174,
    'circledS'                 : 9416,
    'ngtr'                     : 8815,
    'bigcap'                   : 8898,
    'scre'                     : 8495,
    'Downarrow'                : 8659,
    'scrg'                     : 8458,
    'overleftrightarrow'       : 8417,
    'scro'                     : 8500,
    'lnsim'                    : 8934,
    'eqcolon'                  : 8789,
    'curlyvee'                 : 8910,
    'urcorner'                 : 8989,
    'lbrace'                   : 123,
    'Bumpeq'                   : 8782,
    'delta'                    : 948,
    'boxtimes'                 : 8864,
    'overleftarrow'            : 8406,
    'prurel'                   : 8880,
    'clubsuitopen'             : 9831,
    'cwopencirclearrow'        : 8635,
    'geqq'                     : 8807,
    'rightleftarrows'          : 8644,
    'ac'                       : 8766,
    'ae'                       : 230,
    'int'                      : 8747,
    'rfloor'                   : 8971,
    'risingdotseq'             : 8787,
    'nvdash'                   : 8876,
    'diamond'                  : 8900,
    'ddot'                     : 776,
    'backsim'                  : 8765,
    'oplus'                    : 8853,
    'triangleq'                : 8796,
    'check'                    : 780,
    'ni'                       : 8715,
    'iiint'                    : 8749,
    'ne'                       : 8800,
    'lesseqgtr'                : 8922,
    'obar'                     : 9021,
    'supseteq'                 : 8839,
    'nu'                       : 957,
    'AA'                       : 8491,
    'AE'                       : 198,
    'models'                   : 8871,
    'ominus'                   : 8854,
    'dashv'                    : 8867,
    'omega'                    : 969,
    'rq'                       : 8217,
    'Subset'                   : 8912,
    'rightharpoonup'           : 8640,
    'Rdsh'                     : 8627,
    'bullet'                   : 8729,
    'divideontimes'            : 8903,
    'lbrack'                   : 91,
    'textquotedblright'        : 8221,
    'Colon'                    : 8759,
    '%'                        : 37,
    '$'                        : 36,
    '{'                        : 123,
    '}'                        : 125,
    '_'                        : 95,
    '#'                        : 35,
    'imath'                    : 0x131,
    'circumflexaccent'         : 770,
    'combiningbreve'           : 774,
    'combiningoverline'        : 772,
    'combininggraveaccent'     : 768,
    'combiningacuteaccent'     : 769,
    'combiningdiaeresis'       : 776,
    'combiningtilde'           : 771,
    'combiningrightarrowabove' : 8407,
    'combiningdotabove'        : 775,
    'to'                       : 8594,
    'succeq'                   : 8829,
    'emptyset'                 : 8709,
    'leftparen'                : 40,
    'rightparen'               : 41,
    'bigoplus'                 : 10753,
    'leftangle'                : 10216,
    'rightangle'               : 10217,
    'leftbrace'                : 124,
    'rightbrace'               : 125,
    'jmath'                    : 567,
    'bigodot'                  : 10752,
    'preceq'                   : 8828,
    'biguplus'                 : 10756,
    'epsilon'                  : 949,
    'vartheta'                 : 977,
    'bigotimes'                : 10754
}

# Each element is a 4-tuple of the form:
#   src_start, src_end, dst_font, dst_start
#
stix_virtual_fonts = {
    'bb':
        {
        'rm':
            [
            (0x0030, 0x0039, 'rm', 0x1d7d8), # 0-9
            (0x0041, 0x0042, 'rm', 0x1d538), # A-B
            (0x0043, 0x0043, 'rm', 0x2102),  # C
            (0x0044, 0x0047, 'rm', 0x1d53b), # D-G
            (0x0048, 0x0048, 'rm', 0x210d),  # H
            (0x0049, 0x004d, 'rm', 0x1d540), # I-M
            (0x004e, 0x004e, 'rm', 0x2115),  # N
            (0x004f, 0x004f, 'rm', 0x1d546), # O
            (0x0050, 0x0051, 'rm', 0x2119),  # P-Q
            (0x0052, 0x0052, 'rm', 0x211d),  # R
            (0x0053, 0x0059, 'rm', 0x1d54a), # S-Y
            (0x005a, 0x005a, 'rm', 0x2124),  # Z
            (0x0061, 0x007a, 'rm', 0x1d552), # a-z
            (0x0393, 0x0393, 'rm', 0x213e),  # \Gamma
            (0x03a0, 0x03a0, 'rm', 0x213f),  # \Pi
            (0x03a3, 0x03a3, 'rm', 0x2140),  # \Sigma
            (0x03b3, 0x03b3, 'rm', 0x213d),  # \gamma
            (0x03c0, 0x03c0, 'rm', 0x213c),  # \pi
            ],
        'it':
            [
            (0x0030, 0x0039, 'rm', 0x1d7d8), # 0-9
            (0x0041, 0x0042, 'it', 0xe154),  # A-B
            (0x0043, 0x0043, 'it', 0x2102),  # C
            (0x0044, 0x0044, 'it', 0x2145),  # D
            (0x0045, 0x0047, 'it', 0xe156),  # E-G
            (0x0048, 0x0048, 'it', 0x210d),  # H
            (0x0049, 0x004d, 'it', 0xe159),  # I-M
            (0x004e, 0x004e, 'it', 0x2115),  # N
            (0x004f, 0x004f, 'it', 0xe15e),  # O
            (0x0050, 0x0051, 'it', 0x2119),  # P-Q
            (0x0052, 0x0052, 'it', 0x211d),  # R
            (0x0053, 0x0059, 'it', 0xe15f),  # S-Y
            (0x005a, 0x005a, 'it', 0x2124),  # Z
            (0x0061, 0x0063, 'it', 0xe166),  # a-c
            (0x0064, 0x0065, 'it', 0x2146),  # d-e
            (0x0066, 0x0068, 'it', 0xe169),  # f-h
            (0x0069, 0x006a, 'it', 0x2148),  # i-j
            (0x006b, 0x007a, 'it', 0xe16c),  # k-z
            (0x0393, 0x0393, 'it', 0x213e),  # \Gamma (missing in beta STIX fonts)
            (0x03a0, 0x03a0, 'it', 0x213f),  # \Pi
            (0x03a3, 0x03a3, 'it', 0x2140),  # \Sigma (missing in beta STIX fonts)
            (0x03b3, 0x03b3, 'it', 0x213d),  # \gamma (missing in beta STIX fonts)
            (0x03c0, 0x03c0, 'it', 0x213c),  # \pi
            ],
        'bf':
            [
            (0x0030, 0x0039, 'rm', 0x1d7d8), # 0-9
            (0x0041, 0x0042, 'bf', 0xe38a),  # A-B
            (0x0043, 0x0043, 'bf', 0x2102),  # C
            (0x0044, 0x0044, 'bf', 0x2145),  # D
            (0x0045, 0x0047, 'bf', 0xe38d),  # E-G
            (0x0048, 0x0048, 'bf', 0x210d),  # H
            (0x0049, 0x004d, 'bf', 0xe390),  # I-M
            (0x004e, 0x004e, 'bf', 0x2115),  # N
            (0x004f, 0x004f, 'bf', 0xe395),  # O
            (0x0050, 0x0051, 'bf', 0x2119),  # P-Q
            (0x0052, 0x0052, 'bf', 0x211d),  # R
            (0x0053, 0x0059, 'bf', 0xe396),  # S-Y
            (0x005a, 0x005a, 'bf', 0x2124),  # Z
            (0x0061, 0x0063, 'bf', 0xe39d),  # a-c
            (0x0064, 0x0065, 'bf', 0x2146),  # d-e
            (0x0066, 0x0068, 'bf', 0xe3a2),  # f-h
            (0x0069, 0x006a, 'bf', 0x2148),  # i-j
            (0x006b, 0x007a, 'bf', 0xe3a7),  # k-z
            (0x0393, 0x0393, 'bf', 0x213e),  # \Gamma
            (0x03a0, 0x03a0, 'bf', 0x213f),  # \Pi
            (0x03a3, 0x03a3, 'bf', 0x2140),  # \Sigma
            (0x03b3, 0x03b3, 'bf', 0x213d),  # \gamma
            (0x03c0, 0x03c0, 'bf', 0x213c),  # \pi
            ],
        },
    'cal':
        [
        (0x0041, 0x005a, 'it', 0xe22d), # A-Z
        ],
    'circled':
        {
        'rm':
            [
            (0x0030, 0x0030, 'rm', 0x24ea), # 0
            (0x0031, 0x0039, 'rm', 0x2460), # 1-9
            (0x0041, 0x005a, 'rm', 0x24b6), # A-Z
            (0x0061, 0x007a, 'rm', 0x24d0)  # a-z
            ],
        'it':
            [
            (0x0030, 0x0030, 'rm', 0x24ea), # 0
            (0x0031, 0x0039, 'rm', 0x2460), # 1-9
            (0x0041, 0x005a, 'it', 0x24b6), # A-Z
            (0x0061, 0x007a, 'it', 0x24d0)  # a-z
            ],
        'bf':
            [
            (0x0030, 0x0030, 'bf', 0x24ea), # 0
            (0x0031, 0x0039, 'bf', 0x2460), # 1-9
            (0x0041, 0x005a, 'bf', 0x24b6), # A-Z
            (0x0061, 0x007a, 'bf', 0x24d0)  # a-z
            ],
        },
    'frak':
        {
        'rm':
            [
            (0x0041, 0x0042, 'rm', 0x1d504), # A-B
            (0x0043, 0x0043, 'rm', 0x212d),  # C
            (0x0044, 0x0047, 'rm', 0x1d507), # D-G
            (0x0048, 0x0048, 'rm', 0x210c),  # H
            (0x0049, 0x0049, 'rm', 0x2111),  # I
            (0x004a, 0x0051, 'rm', 0x1d50d), # J-Q
            (0x0052, 0x0052, 'rm', 0x211c),  # R
            (0x0053, 0x0059, 'rm', 0x1d516), # S-Y
            (0x005a, 0x005a, 'rm', 0x2128),  # Z
            (0x0061, 0x007a, 'rm', 0x1d51e), # a-z
            ],
        'it':
            [
            (0x0041, 0x0042, 'rm', 0x1d504), # A-B
            (0x0043, 0x0043, 'rm', 0x212d),  # C
            (0x0044, 0x0047, 'rm', 0x1d507), # D-G
            (0x0048, 0x0048, 'rm', 0x210c),  # H
            (0x0049, 0x0049, 'rm', 0x2111),  # I
            (0x004a, 0x0051, 'rm', 0x1d50d), # J-Q
            (0x0052, 0x0052, 'rm', 0x211c),  # R
            (0x0053, 0x0059, 'rm', 0x1d516), # S-Y
            (0x005a, 0x005a, 'rm', 0x2128),  # Z
            (0x0061, 0x007a, 'rm', 0x1d51e), # a-z
            ],
        'bf':
            [
            (0x0041, 0x005a, 'bf', 0x1d56c), # A-Z
            (0x0061, 0x007a, 'bf', 0x1d586), # a-z
            ],
        },
    'scr':
        [
        (0x0041, 0x0041, 'it', 0x1d49c), # A
        (0x0042, 0x0042, 'it', 0x212c),  # B
        (0x0043, 0x0044, 'it', 0x1d49e), # C-D
        (0x0045, 0x0046, 'it', 0x2130),  # E-F
        (0x0047, 0x0047, 'it', 0x1d4a2), # G
        (0x0048, 0x0048, 'it', 0x210b),  # H
        (0x0049, 0x0049, 'it', 0x2110),  # I
        (0x004a, 0x004b, 'it', 0x1d4a5), # J-K
        (0x004c, 0x004c, 'it', 0x2112),  # L
        (0x004d, 0x003d, 'it', 0x2133),  # M
        (0x004e, 0x0051, 'it', 0x1d4a9), # N-Q
        (0x0052, 0x0052, 'it', 0x211b),  # R
        (0x0053, 0x005a, 'it', 0x1d4ae), # S-Z
        (0x0061, 0x0064, 'it', 0x1d4b6), # a-d
        (0x0065, 0x0065, 'it', 0x212f),  # e
        (0x0066, 0x0066, 'it', 0x1d4bb), # f
        (0x0067, 0x0067, 'it', 0x210a),  # g
        (0x0068, 0x006e, 'it', 0x1d4bd), # h-n
        (0x006f, 0x006f, 'it', 0x2134),  # o
        (0x0070, 0x007a, 'it', 0x1d4c5), # p-z
        ],
    'sf':
        {
        'rm':
            [
            (0x0030, 0x0039, 'rm', 0x1d7e2), # 0-9
            (0x0041, 0x005a, 'rm', 0x1d5a0), # A-Z
            (0x0061, 0x007a, 'rm', 0x1d5ba), # a-z
            (0x0391, 0x03a9, 'rm', 0xe17d),  # \Alpha-\Omega
            (0x03b1, 0x03c9, 'rm', 0xe196),  # \alpha-\omega
            (0x03d1, 0x03d1, 'rm', 0xe1b0),  # theta variant
            (0x03d5, 0x03d5, 'rm', 0xe1b1),  # phi variant
            (0x03d6, 0x03d6, 'rm', 0xe1b3),  # pi variant
            (0x03f1, 0x03f1, 'rm', 0xe1b2),  # rho variant
            (0x03f5, 0x03f5, 'rm', 0xe1af),  # lunate epsilon
            (0x2202, 0x2202, 'rm', 0xe17c),  # partial differential
            ],
        'it':
            [
            # These numerals are actually upright.  We don't actually
            # want italic numerals ever.
            (0x0030, 0x0039, 'rm', 0x1d7e2), # 0-9
            (0x0041, 0x005a, 'it', 0x1d608), # A-Z
            (0x0061, 0x007a, 'it', 0x1d622), # a-z
            (0x0391, 0x03a9, 'rm', 0xe17d),  # \Alpha-\Omega
            (0x03b1, 0x03c9, 'it', 0xe1d8),  # \alpha-\omega
            (0x03d1, 0x03d1, 'it', 0xe1f2),  # theta variant
            (0x03d5, 0x03d5, 'it', 0xe1f3),  # phi variant
            (0x03d6, 0x03d6, 'it', 0xe1f5),  # pi variant
            (0x03f1, 0x03f1, 'it', 0xe1f4),  # rho variant
            (0x03f5, 0x03f5, 'it', 0xe1f1),  # lunate epsilon
            ],
        'bf':
            [
            (0x0030, 0x0039, 'bf', 0x1d7ec), # 0-9
            (0x0041, 0x005a, 'bf', 0x1d5d4), # A-Z
            (0x0061, 0x007a, 'bf', 0x1d5ee), # a-z
            (0x0391, 0x03a9, 'bf', 0x1d756), # \Alpha-\Omega
            (0x03b1, 0x03c9, 'bf', 0x1d770), # \alpha-\omega
            (0x03d1, 0x03d1, 'bf', 0x1d78b), # theta variant
            (0x03d5, 0x03d5, 'bf', 0x1d78d), # phi variant
            (0x03d6, 0x03d6, 'bf', 0x1d78f), # pi variant
            (0x03f0, 0x03f0, 'bf', 0x1d78c), # kappa variant
            (0x03f1, 0x03f1, 'bf', 0x1d78e), # rho variant
            (0x03f5, 0x03f5, 'bf', 0x1d78a), # lunate epsilon
            (0x2202, 0x2202, 'bf', 0x1d789), # partial differential
            (0x2207, 0x2207, 'bf', 0x1d76f), # \Nabla
            ],
        },
    'tt':
        [
        (0x0030, 0x0039, 'rm', 0x1d7f6), # 0-9
        (0x0041, 0x005a, 'rm', 0x1d670), # A-Z
        (0x0061, 0x007a, 'rm', 0x1d68a)  # a-z
        ],
    }

########NEW FILE########
__FILENAME__ = ieee

from rinoh import (
    StyleSheet, ClassSelector, ContextSelector,
    StyledText, MixedStyledText, Paragraph, Heading, ParagraphStyle,
    FixedSpacing, ProportionalSpacing,
    List, ListItem, DefinitionList, DefinitionTerm,
    GroupedFlowables, StaticGroupedFlowables,
    Header, Footer, Figure, Caption, Tabular, Framed, HorizontalRule,
    NoteMarker, Note, TableOfContents, TableOfContentsEntry, Line, TabStop,
    DEFAULT, LEFT, RIGHT, CENTER, BOTH, MIDDLE,
    NUMBER, ROMAN_UC, CHARACTER_UC, SYMBOL,
    PT, INCH, CM, RED, Color, Gray
)

from rinoh.font import TypeFamily
from rinoh.font.style import REGULAR, UPRIGHT, ITALIC, BOLD, SUPERSCRIPT

from rinohlib.fonts.texgyre.termes import typeface as times
from rinohlib.fonts.texgyre.cursor import typeface as courier


ieee_family = TypeFamily(serif=times, mono=courier)

styles = StyleSheet('IEEE')

styles('body', ClassSelector(Paragraph),
       typeface=ieee_family.serif,
       font_weight=REGULAR,
       font_size=10*PT,
       line_spacing=FixedSpacing(12*PT),
       indent_first=0.125*INCH,
       space_above=0*PT,
       space_below=0*PT,
       justify=BOTH,
       kerning=True,
       ligatures=True,
       hyphen_lang='en_US',
       hyphen_chars=4)

styles('monospaced', ClassSelector(StyledText, 'monospaced'),
       font_size=9*PT,
       typeface=ieee_family.mono,
       hyphenate=False,
       ligatures=False)

styles('error', ClassSelector(StyledText, 'error'),
       font_color=RED)

styles('literal', ClassSelector(Paragraph, 'literal'),
       base='body',
       font_size=9*PT,
       justify=LEFT,
       indent_first=0,
       margin_left=0.5*CM,
       typeface=ieee_family.mono,
       ligatures=False,
       hyphenate=False)
       #noWrap=True,   # but warn on overflow
       #literal=True ?)

styles('block quote', ClassSelector(GroupedFlowables, 'block quote'),
       margin_left=1*CM)

styles('attribution', ClassSelector(Paragraph, 'attribution'),
       base='body',
       justify=RIGHT)

styles('line block', ContextSelector(ClassSelector(GroupedFlowables, 'line block'),
                                     ClassSelector(GroupedFlowables, 'line block')),
       margin_left=0.5*CM)

styles('title', ClassSelector(Paragraph, 'title'),
       typeface=ieee_family.serif,
       font_weight=REGULAR,
       font_size=18*PT,
       line_spacing=ProportionalSpacing(1.2),
       space_above=6*PT,
       space_below=6*PT,
       justify=CENTER)

styles('subtitle', ClassSelector(Paragraph, 'subtitle'),
       base='title',
       font_size=14*PT)

styles('author', ClassSelector(Paragraph, 'author'),
       base='title',
       font_size=12*PT,
       line_spacing=ProportionalSpacing(1.2))

styles('affiliation', ClassSelector(Paragraph, 'affiliation'),
       base='author',
       space_below=6*PT + 12*PT)

styles('heading level 1', ClassSelector(Heading, level=1),
       typeface=ieee_family.serif,
       font_weight=REGULAR,
       font_size=10*PT,
       small_caps=True,
       justify=CENTER,
       line_spacing=FixedSpacing(12*PT),
       space_above=18*PT,
       space_below=6*PT,
       number_format=ROMAN_UC)

styles('unnumbered heading level 1', ClassSelector(Heading, 'unnumbered',
                                                   level=1),
       base='heading level 1',
       number_format=None)

styles('heading level 2', ClassSelector(Heading, level=2),
       base='heading level 1',
       font_slant=ITALIC,
       font_size=10*PT,
       small_caps=False,
       justify=LEFT,
       line_spacing=FixedSpacing(12*PT),
       space_above=6*PT,
       space_below=6*PT,
       number_format=CHARACTER_UC)

styles('heading level 3', ClassSelector(Heading, level=3),
       base='heading level 2',
       font_size=9*PT,
       font_slant=UPRIGHT,
       font_weight=BOLD,
       line_spacing=FixedSpacing(12*PT),
       space_above=3*PT,
       space_below=3*PT,
       number_format=None)

styles('topic', ClassSelector(GroupedFlowables, 'topic'),
       margin_left=0.5*CM)

styles('topic title', ContextSelector(ClassSelector(GroupedFlowables, 'topic'),
                                      ClassSelector(Paragraph, 'title')),
       base='body',
       font_weight=BOLD,
       indent_first=0,
       space_above=5*PT,
       space_below=5*PT)

styles('rubric', ClassSelector(Paragraph, 'rubric'),
       base='topic title',
       justify=CENTER,
       font_color=Color(0.5, 0, 0))

styles('sidebar frame', ClassSelector(Framed, 'sidebar'),
       fill_color=Color(1.0, 1.0, 0.9))

styles('sidebar title', ContextSelector(ClassSelector(Framed, 'sidebar'),
                                        ClassSelector(GroupedFlowables),
                                        ClassSelector(Paragraph, 'title')),
       base='body',
       font_size=12*PT,
       font_weight=BOLD,
       indent_first=0,
       space_above=5*PT,
       space_below=5*PT)

styles('sidebar subtitle', ContextSelector(ClassSelector(Framed, 'sidebar'),
                                           ClassSelector(GroupedFlowables),
                                           ClassSelector(Paragraph, 'subtitle')),
       base='body',
       font_weight=BOLD,
       indent_first=0,
       space_above=2*PT,
       space_below=2*PT)

styles('list item number', ContextSelector(ClassSelector(ListItem),
                                           ClassSelector(Paragraph)),
       base='body',
       indent_first=0,
       justify=RIGHT)

styles('enumerated list', ClassSelector(List, 'enumerated'),
       space_above=5*PT,
       space_below=5*PT,
       ordered=True,
       flowable_spacing=0*PT,
       number_format=NUMBER,
       number_suffix=')')

styles('nested enumerated list', ContextSelector(ClassSelector(ListItem),
                                                 ClassSelector(List,
                                                               'enumerated')),
       base='enumerated list',
       margin_left=10*PT)

styles('bulleted list', ClassSelector(List, 'bulleted'),
       base='enumerated list',
       ordered=False,
       flowable_spacing=0*PT)

styles('nested bulleted list', ContextSelector(ClassSelector(ListItem),
                                               ClassSelector(List, 'bulleted')),
       base='bulleted list',
       margin_left=10*PT)

styles('list item body', ContextSelector(ClassSelector(ListItem),
                                         ClassSelector(GroupedFlowables)),
       space_above=0,
       space_below=0,
       margin_left=0,
       margin_right=0)

styles('list item paragraph', ContextSelector(ClassSelector(ListItem),
                                              ClassSelector(GroupedFlowables),
                                              ClassSelector(Paragraph)),
       base='body',
       space_above=0*PT,
       space_below=0*PT,
       margin_left=0*PT,
       indent_first=0*PT)

styles('definition list', ClassSelector(DefinitionList),
       base='body')

styles('definition term', ClassSelector(DefinitionTerm),
       base='body',
       indent_first=0,
       font_weight=BOLD)

styles('definition term classifier', ClassSelector(StyledText, 'classifier'),
       font_weight=REGULAR)

styles('definition', ContextSelector(ClassSelector(DefinitionList),
                                     ClassSelector(GroupedFlowables)),
       margin_left=15*PT)


# field lists

styles('field name', ClassSelector(Paragraph, 'field_name'),
       base='body',
       indent_first=0,
       justify=LEFT,
       font_weight=BOLD)


# option lists

styles('option', ClassSelector(Paragraph, 'option_group'),
       base='body',
       indent_first=0,
       justify=LEFT)

styles('option string', ClassSelector(MixedStyledText, 'option_string'),
       base='body',
       typeface=ieee_family.mono,
       font_size=8*PT)

styles('option argument', ClassSelector(MixedStyledText, 'option_arg'),
       base='body',
       font_slant=ITALIC)


styles('admonition', ClassSelector(Framed, 'admonition'),
       space_above=5*PT,
       space_below=5*PT,
       padding_left=10*PT,
       padding_right=10*PT,
       padding_top=4*PT,
       padding_bottom=4*PT,
       fill_color=Color(0.94, 0.94, 1.0),
       stroke_width=1*PT,
       stroke_color=Gray(0.4))

styles('admonition title', ContextSelector(ClassSelector(Framed, 'admonition'),
                                           ClassSelector(GroupedFlowables),
                                           ClassSelector(Paragraph, 'title')),
       base='body',
       font_weight=BOLD,
       indent_first=0,
       space_above=5*PT,
       space_below=5*PT)

styles['red admonition title'] = ParagraphStyle(base='admonition title',
                                                font_color=RED)

for admonition_type in ('attention', 'caution', 'danger', 'error', 'warning'):
    selector = ContextSelector(ClassSelector(Framed, 'admonition',
                                             admonition_type=admonition_type),
                               ClassSelector(GroupedFlowables),
                               ClassSelector(Paragraph, 'title'))
    styles.selectors[selector] = 'red admonition title'


styles('header', ClassSelector(Header),
       base='body',
       indent_first=0*PT,
       font_size=9*PT)

styles('footer', ClassSelector(Footer),
       base='header',
       indent_first=0*PT,
       justify=CENTER)

styles('footnote marker', ClassSelector(NoteMarker),
       position=SUPERSCRIPT,
       number_format=SYMBOL)

styles('footnote paragraph', ContextSelector(ClassSelector(Note),
                                             ClassSelector(GroupedFlowables),
                                             ClassSelector(Paragraph)),
       base='body',
       font_size=9*PT,
       indent_first=0,
       line_spacing=FixedSpacing(10*PT))

styles('footnote label', ContextSelector(ClassSelector(Note),
                                         ClassSelector(Paragraph)),
       base='footnote paragraph',
       justify=RIGHT)

styles('figure', ClassSelector(Figure),
       space_above=10*PT,
       space_below=12*PT)

styles('figure caption', ContextSelector(ClassSelector(Figure),
                                         ClassSelector(Caption)),
       typeface=ieee_family.serif,
       font_weight=REGULAR,
       font_size=9*PT,
       line_spacing=FixedSpacing(10*PT),
       indent_first=0*PT,
       space_above=20*PT,
       space_below=0*PT,
       justify=BOTH)

styles('table of contents', ClassSelector(TableOfContents),
       base='body',
       indent_first=0,
       depth=3)

styles('toc level 1', ClassSelector(TableOfContentsEntry, depth=1),
       base='table of contents',
       font_weight=BOLD,
       tab_stops=[TabStop(0.6*CM),
                  TabStop(1.0, RIGHT, '. ')])

styles('toc level 2', ClassSelector(TableOfContentsEntry, depth=2),
       base='table of contents',
       margin_left=0.6*CM,
       tab_stops=[TabStop(1.2*CM),
                  TabStop(1.0, RIGHT, '. ')])

styles('toc level 3', ClassSelector(TableOfContentsEntry, depth=3),
       base='table of contents',
       margin_left=1.2*CM,
       tab_stops=[TabStop(1.8*CM),
                  TabStop(1.0, RIGHT, '. ')])

styles('L3 toc level 3', ContextSelector(ClassSelector(TableOfContents, level=2),
                                         ClassSelector(TableOfContentsEntry, depth=3)),
       base='table of contents',
       margin_left=0,
       tab_stops=[TabStop(0.6*CM),
                  TabStop(1.0, RIGHT, '. ')])

styles('tabular', ClassSelector(Tabular),
       typeface=ieee_family.serif,
       font_weight=REGULAR,
       font_size=10*PT,
       line_spacing=FixedSpacing(12*PT),
       indent_first=0*PT,
       space_above=0*PT,
       space_below=0*PT,
       justify=CENTER,
       vertical_align=MIDDLE,
       left_border='red line',
       right_border='red line',
       bottom_border='red line',
       top_border='red line')

styles('red line', ClassSelector(Line),
       stroke_width=0.2*PT,
       stroke_color=RED)

styles('thick line', ClassSelector(Line),
       stroke_width=1*PT)

styles('first row', ClassSelector(Tabular, 'NOMATCH'),  # TODO: find proper fix
       font_weight=BOLD,
       bottom_border='thick line')

styles('first column', ClassSelector(Tabular, 'NOMATCH'),
       font_slant=ITALIC,
       right_border='thick line')

styles('numbers', ClassSelector(Tabular, 'NOMATCH'),
       typeface=ieee_family.mono)

styles['tabular'].set_cell_style(styles['first row'], rows=0)
styles['tabular'].set_cell_style(styles['first column'], cols=0)
styles['tabular'].set_cell_style(styles['numbers'], rows=slice(1,None),
                                 cols=slice(1,None))

styles('horizontal rule', ClassSelector(HorizontalRule),
       space_above=10*PT,
       space_below=15*PT,
       margin_left=40*PT,
       margin_right=40*PT)
########NEW FILE########
__FILENAME__ = rinascimento


from rinoh import (
    StyleSheet, ClassSelector, ContextSelector,
    GroupedFlowables,
    StyledText, Paragraph, Heading,
    List, ListItem, DefinitionList,
    DEFAULT, LEFT, CENTER, RIGHT, BOTH, NUMBER,
    PT, CM
)

from rinoh.font import TypeFamily
from rinoh.font.style import REGULAR, ITALIC

from rinohlib.fonts.texgyre.pagella import typeface as pagella
from rinohlib.fonts.texgyre.cursor import typeface as cursor


fontFamily = TypeFamily(serif=pagella, mono=cursor)

styles = StyleSheet('Rinascimento')

styles('body', ClassSelector(Paragraph),
       typeface=fontFamily.serif,
       font_weight=REGULAR,
       font_size=10*PT,
       line_spacing=DEFAULT,
       #indent_first=0.125*INCH,
       space_above=0*PT,
       space_below=10*PT,
       justify=BOTH)

styles('title', ClassSelector(Paragraph, 'title'),
       typeface=fontFamily.serif,
       font_size=16*PT,
       line_spacing=DEFAULT,
       space_above=6*PT,
       space_below=6*PT,
       justify=CENTER)

styles('literal', ClassSelector(Paragraph, 'literal'),
       base='body',
       #font_size=9*PT,
       justify=LEFT,
       margin_left=1*CM,
       typeface=fontFamily.mono,
       ligatures=False)
       #noWrap=True,   # but warn on overflow
       #literal=True ?)

styles('block quote', ClassSelector(Paragraph, 'block quote'),
       base='body',
       margin_left=1*CM)

styles('heading level 1', ClassSelector(Heading, level=1),
       typeface=fontFamily.serif,
       font_size=14*PT,
       line_spacing=DEFAULT,
       space_above=14*PT,
       space_below=6*PT,
       numbering_style=None)

styles('heading level 2', ClassSelector(Heading, level=2),
       base='heading level 1',
       font_slant=ITALIC,
       font_size=12*PT,
       line_spacing=DEFAULT,
       space_above=6*PT,
       space_below=6*PT)

styles('monospaced', ClassSelector(StyledText, 'monospaced'),
       typeface=fontFamily.mono)

styles('list item', ClassSelector(ListItem),
       label_width=12*PT,
       label_spacing=3*PT)

styles('list item label', ContextSelector(ClassSelector(ListItem),
                                          ClassSelector(Paragraph)),
       base='body',
       justify=RIGHT)

styles('enumerated list', ClassSelector(List, 'enumerated'),
       base='body',
       ordered=True,
       margin_left=5*PT,
       flowable_spacing=0*PT,
       numbering_style=NUMBER,
       numbering_separator='.')

styles('bulleted list', ClassSelector(List, 'bulleted'),
       base='body',
       ordered=False,
       margin_left=5*PT,
       flowable_spacing=0*PT)

styles('list item paragraph', ContextSelector(ClassSelector(ListItem),
                                              ClassSelector(GroupedFlowables),
                                              ClassSelector(Paragraph)),
       base='body',
       indent_first=0)

styles('definition list', ClassSelector(DefinitionList),
       base='body')

########NEW FILE########
__FILENAME__ = afm


from rinoh.font.type1 import AdobeFontMetrics


if __name__ == '__main__':
    afm = AdobeFontMetrics(r'..\rinoh\data\fonts\adobe14\Times-Roman.afm')

########NEW FILE########
__FILENAME__ = backend_pdf

from io import StringIO, BytesIO

from rinoh.backend.pdf.cos import (Document, Boolean, Catalog, String,
                                  Dictionary, Stream, XObjectForm)
from rinoh.backend.pdf.reader import PDFReader



image = PDFReader('../examples/rfic2009/fig2.pdf')
image_page = image.catalog['Pages']['Kids'][0]

d = Document()

b = Boolean(True, indirect=True)

page = d.catalog['Pages'].new_page(100, 150)

page['Resources']['XObject'] = Dictionary()
page['Resources']['XObject']['Im01'] = image_page.to_xobject_form()

page['Contents'] = Stream()
page['Contents'].write(b'0.2 0 0 0.2 30 30 cm')
page['Contents'].write('/Im01 Do'.encode('utf_8'))

file = open('backend_pdf.pdf', 'wb')
d.write(file)

file.close()

########NEW FILE########
__FILENAME__ = opentype

import time

from rinoh.font.opentype import OpenTypeFont
from rinoh.font.style import SMALL_CAPITAL


if __name__ == '__main__':
    time.clock()
    ot = OpenTypeFont('texgyretermes-regular.otf')
    ot2 = OpenTypeFont('Cuprum.otf')
    ot3 = OpenTypeFont('Puritan2.otf')

    print(ot.get_kerning(ot.get_glyph('V'), ot.get_glyph('A')))
    print(ot2.get_kerning(ot2.get_glyph('U'), ot2.get_glyph('A')))
    print(ot.get_ligature(ot.get_glyph('f'), ot.get_glyph('f')))
    print(ot.get_ligature(ot.get_glyph('f'), ot.get_glyph('i')))
    print(ot.get_ligature(ot.get_glyph('f'), ot.get_glyph('i')))
    print(ot.get_glyph('s').code, ot.get_glyph('s', SMALL_CAPITAL).code)
    run_time = time.clock()
    print('Total execution time: {} seconds'.format(run_time))

########NEW FILE########
__FILENAME__ = pdf_read
﻿
from rinoh.backend.pdf.reader import PDFReader



if __name__ == '__main__':
    pdf = PDFReader('../examples/rfic2009/template.pdf')
    print(pdf.catalog)
    print(pdf.info)
    print(pdf.id)
    print(pdf.catalog['Pages']['Kids'])
    print(pdf.catalog['Pages']['Kids'][0])
    print(pdf.catalog['Pages']['Kids'][0]['Contents'])
    pdf.write('template_out.pdf')

########NEW FILE########
__FILENAME__ = test_dimension


import unittest


from rinoh.dimension import Dimension, PT, INCH


class TestDimension(unittest.TestCase):

    # utility methods

    def assertEqualAndIsNeither(self, operation, term1, term2, reference):
        result = operation(term1, term2)
        self.assertEqual(result, reference)
        self.assertIsNot(result, term1)
        self.assertIsNot(result, term2)

    def assertEqualAndIsFirst(self, operation, term1, term2, reference):
        result = operation(term1, term2)
        self.assertEqual(result, reference)
        self.assertIs(result, term1)

    # test operators

    def test_addition(self):
        op = lambda a, b: a + b
        self.assertEqualAndIsNeither(op, 100*PT, 10, 110)
        self.assertEqualAndIsNeither(op, 100*PT, 10*PT, 110)
        self.assertEqualAndIsNeither(op, 100, 10*PT,  110)
        self.assertEqualAndIsNeither(op, 1*INCH, 8*PT, 80)

    def test_subtraction(self):
        op = lambda a, b: a - b
        self.assertEqualAndIsNeither(op, 100*PT, 10, 90)
        self.assertEqualAndIsNeither(op, 100*PT, 10*PT, 90)
        self.assertEqualAndIsNeither(op, 100, 10*PT, 90)
        self.assertEqualAndIsNeither(op, 1*INCH, 2*PT, 70)

    def test_multiplication(self):
        op = lambda a, b: a * b
        self.assertEqualAndIsNeither(op, 3, 30*PT, 90)
        self.assertEqualAndIsNeither(op, 30*PT, 3, 90)

    def test_division(self):
        op = lambda a, b: a / b
        self.assertEqualAndIsNeither(op, 30*PT, 5, 6)

    def test_inplace_addition(self):
        def op(a, b):
            a += b
            return a
        self.assertEqualAndIsFirst(op, 20*PT, 50, 70)
        self.assertEqualAndIsFirst(op, 20*PT, 30*PT, 50)

    def test_inplace_subtraction(self):
        def op(a, b):
            a -= b
            return a
        self.assertEqualAndIsFirst(op, 100*PT, 50, 50)
        self.assertEqualAndIsFirst(op, 100*PT, 30*PT, 70)

    def test_inplace_multiplication(self):
        def op(a, b):
            a *= b
            return a
        self.assertEqualAndIsFirst(op, 20*PT, 3, 60)

    def test_inplace_division(self):
        def op(a, b):
            a /= b
            return a
        self.assertEqualAndIsFirst(op, 60*PT, 3, 20)

    def test_negation(self):
        op = lambda a, _: - a
        self.assertEqualAndIsNeither(op, 20*PT, None, -20)

    # test late evaluation

    def test_late_addition(self):
        def op(a, b):
            result = a + b
            a += 2*PT
            return result
        self.assertEqualAndIsNeither(op, 10*PT, 5*PT, 17)

    def test_late_subtraction(self):
        def op(a, b):
            result = a - b
            a += 2*PT
            return result
        self.assertEqualAndIsNeither(op, 10*PT, 5*PT, 7)

    def test_late_multiplication(self):
        def op(a, b):
            result = a * b
            a += 2*PT
            return result
        self.assertEqualAndIsNeither(op, 10*PT, 2, 24)

    def test_late_division(self):
        def op(a, b):
            result = a / b
            a += 2*PT
            return result
        self.assertEqualAndIsNeither(op, 10*PT, 2, 6)

########NEW FILE########
__FILENAME__ = test_pdf_reader


import unittest


from pyte.backend.pdf.reader import PDFObjectReader


class TestPDFReader(unittest.TestCase):

    def test_read_name(self):
        def test_name(bytes_name, unicode_name):
            name = read_name(BytesIO(bytes_name))
            self.assertEqual(str(name), unicode_name)

        test_name(b'Adobe#20Green Blue', 'Adobe Green Blue')
        test_name(b'PANTONE#205757#20CV', 'PANTONE 5757 CV')
        test_name(b'paired#28#29parentheses', 'paired()parentheses')
        test_name(b'The_Key_of_F#23_Minor', 'The_Key_of_F#_Minor')
        test_name(b'A#42', 'AB')

########NEW FILE########
__FILENAME__ = test_tab


import unittest


from rinoh.dimension import PT
from rinoh.paragraph import TabStop, Line, LEFT, RIGHT, CENTER
from rinoh.text import Tab, Spacer


class StyledTextStub(object):
    def __init__(self, width):
        self.width = float(width)

    def warn(self, message):
        pass

    def hyphenate(self):
        yield self, None


class TestTab(unittest.TestCase):

    def test__tab_space_exceeded(self):
        tab_stops = [TabStop(30*PT, LEFT),
                     TabStop(100*PT, CENTER),
                     TabStop(190*PT, RIGHT)]
        line = Line(tab_stops, width=200*PT, indent=0)
        self.assertEqual(line._cursor, 0)
        line.append(StyledTextStub(20*PT))
        self.assertFalse(line._has_tab)
        self.assertEqual(line._cursor, 20*PT)

        # jump to the first (LEFT) tab stop
        first_tab = Tab()
        line.append(first_tab)
        self.assertTrue(line._has_tab)
        self.assertEqual(line._cursor, 30*PT)
        line.append(StyledTextStub(20*PT))
        self.assertEqual(line._cursor, 50*PT)
        line.append(StyledTextStub(10*PT))
        self.assertEqual(line._cursor, 60*PT)

        # jump to the second (CENTER) tab stop
        second_tab = Tab()
        line.append(second_tab)
        self.assertEqual(line._cursor, 100*PT)
        self.assertEqual(second_tab.tab_width, 40*PT)
        line.append(StyledTextStub(20*PT))
        self.assertEqual(second_tab.tab_width, 30*PT)
        self.assertEqual(line._cursor, 110*PT)
        line.append(StyledTextStub(40*PT))
        self.assertEqual(second_tab.tab_width, 10*PT)
        self.assertEqual(line._cursor, 130*PT)
        # exceed the available space
        line.append(StyledTextStub(60*PT))
        self.assertEqual(second_tab.tab_width, 0)
        self.assertEqual(line._cursor, 180*PT)

        # jump to the third (RIGHT) tab stop
        line.append(Tab())
        self.assertEqual(line._cursor, 190*PT)
        spillover = line.append(StyledTextStub(30*PT))
        self.assertTrue(spillover)

########NEW FILE########
__FILENAME__ = type1


from rinoh.font.type1 import Type1Font


if __name__ == '__main__':
    pfb = Type1Font(r'..\examples\rfic2009\fonts\qtmr')
    print(pfb.header.decode('ascii'))

########NEW FILE########
