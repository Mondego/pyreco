__FILENAME__ = descriptor
"""
Extended types for IBL extraction
"""
from itertools import chain 

from scrapely.extractors import text

class FieldDescriptor(object):
    """description of a scraped attribute"""
    __slots__ = ('name', 'description', 'extractor', 'required')

    def __init__(self, name, description, extractor=text, required=False):
        self.name = name
        self.description = description
        self.extractor = extractor
        self.required = required
    
    def __str__(self):
        return "FieldDescriptor(%s)" % self.name

class ItemDescriptor(object):
    """Simple auto scraping item descriptor. 

    This used to describe type-specific operations and may be overridden where
    necessary.
    """

    def __init__(self, name, description, attribute_descriptors):
        self.name = name
        self.description = description
        self.attribute_map = dict((d.name, d) for d in attribute_descriptors)
        self._required_attributes = [d.name for d in attribute_descriptors \
                if d.required]

    def validated(self, data):
        """Only return the items in the data that are valid"""
        return [d for d in data if self._item_validates(d)]

    def _item_validates(self, item):
        """simply checks that all mandatory attributes are present"""
        variant_attrs = set(chain(*
            [v.keys() for v in item.get('variants', [])]))
        return item and all([(name in item or name in variant_attrs) \
                for name in self._required_attributes])

    def get_required_attributes(self):
        return self._required_attributes
    
    def __str__(self):
        return "ItemDescriptor(%s)" % self.name

    def copy(self):
        attribute_descriptors = []
        for d in self.attribute_map.values():
            attribute_descriptors.append(FieldDescriptor(d.name, d.description, d.extractor, d.required))
        return ItemDescriptor(self.name, self.description, attribute_descriptors)
        # return self

########NEW FILE########
__FILENAME__ = pageobjects
"""
Page objects

This module contains objects representing pages and parts of pages (e.g. tokens
and annotations) used in the instance based learning algorithm.
"""
from itertools import chain
from numpy import array, ndarray

from scrapely.htmlpage import HtmlTagType, HtmlPageRegion, HtmlPageParsedRegion

class TokenType(HtmlTagType):
    """constants for token types"""
    WORD = 0

class TokenDict(object):
    """Mapping from parse tokens to integers
    
    >>> d = TokenDict()
    >>> d.tokenid('i')
    0
    >>> d.tokenid('b')
    1
    >>> d.tokenid('i')
    0

    Tokens can be searched for by id
    >>> d.find_token(1)
    'b'

    The lower 24 bits store the token reference and the higher bits the type.
    """
    
    def __init__(self):
        self.token_ids = {}

    def tokenid(self, token, token_type=TokenType.WORD):
        """create an integer id from the token and token type passed"""
        tid = self.token_ids.setdefault(token, len(self.token_ids))
        return tid | (token_type << 24)
    
    @staticmethod
    def token_type(token):
        """extract the token type from the token id passed"""
        return token >> 24

    def find_token(self, tid):
        """Search for a tag with the given ID

        This is O(N) and is only intended for debugging
        """
        tid &= 0xFFFFFF
        if tid >= len(self.token_ids) or tid < 0:
            raise ValueError("tag id %s out of range" % tid)

        for (token, token_id) in self.token_ids.items():
            if token_id == tid:
                return token
        assert False, "token dictionary is corrupt"

    def token_string(self, tid):
        """create a string representation of a token

        This is O(N).
        """
        templates = ["%s", "<%s>", "</%s>", "<%s/>"]
        return templates[tid >> 24] % self.find_token(tid)

class PageRegion(object):
    """A region in a page, defined by a start and end index"""

    __slots__ = ('start_index', 'end_index')
    
    def __init__(self, start, end):
        self.start_index = start
        self.end_index = end
        
    def __str__(self):
        return "%s(%s, %s)" % (self.__class__.__name__, self.start_index,
                self.end_index)
    
    def __repr__(self):
        return str(self)

class FragmentedHtmlPageRegion(HtmlPageParsedRegion, HtmlPageRegion):
    """An HtmlPageRegion consisting of possibly non-contiguous sub-regions"""
    def __new__(cls, htmlpage, regions):
        text = u''.join(regions)
        return HtmlPageRegion.__new__(cls, htmlpage, text)

    def __init__(self, htmlpage, regions):
        self.htmlpage = htmlpage
        self.regions = regions
    
    @property
    def parsed_fragments(self):
        return chain(*(r.parsed_fragments for r in self.regions))
        
class Page(object):
    """Basic representation of a page. This consists of a reference to a
    dictionary of tokens and an array of raw token ids
    """

    __slots__ = ('token_dict', 'page_tokens')

    def __init__(self, token_dict, page_tokens):
        self.token_dict = token_dict
        # use a numpy array becuase we can index/slice easily and efficiently
        if not isinstance(page_tokens, ndarray):
            page_tokens = array(page_tokens)
        self.page_tokens = page_tokens

class TemplatePage(Page):
    __slots__ = ('annotations', 'id', 'ignored_regions', 'extra_required_attrs')

    def __init__(self, token_dict, page_tokens, annotations, template_id=None, \
            ignored_regions=None, extra_required=None):
        Page.__init__(self, token_dict, page_tokens)
        # ensure order is the same as start tag order in the original page
        annotations = sorted(annotations, key=lambda x: x.end_index, reverse=True)
        self.annotations = sorted(annotations, key=lambda x: x.start_index)
        self.id = template_id
        self.ignored_regions = [i if isinstance(i, PageRegion) else PageRegion(*i) \
            for i in (ignored_regions or [])]
        self.extra_required_attrs = set(extra_required or [])

    def __str__(self):
        summary = []
        for index, token in enumerate(self.page_tokens):
            text = "%s: %s" % (index, self.token_dict.find_token(token))
            summary.append(text)
        return "TemplatePage\n============\nTokens: (index, token)\n%s\nAnnotations: %s\n" % \
                ('\n'.join(summary), '\n'.join(map(str, self.annotations)))

class ExtractionPage(Page):
    """Parsed data belonging to a web page upon which we wish to perform
    extraction.
    """
    __slots__ = ('htmlpage', 'token_page_indexes')

    def __init__(self, htmlpage, token_dict, page_tokens, token_page_indexes):
        """Construct a new ExtractionPage

        Arguments:
            `htmlpage`: The source HtmlPage
            `token_dict`: Token Dictionary used for tokenization
            `page_tokens': array of page tokens for matching
            `token_page_indexes`: indexes of each token in the parsed htmlpage
        """
        Page.__init__(self, token_dict, page_tokens)
        self.htmlpage = htmlpage
        self.token_page_indexes = token_page_indexes
    
    def htmlpage_region(self, start_token_index, end_token_index):
        """The region in the HtmlPage corresonding to the area defined by
        the start_token_index and the end_token_index

        This includes the tokens at the specified indexes
        """
        start = self.token_page_indexes[start_token_index]
        end = self.token_page_indexes[end_token_index]
        return self.htmlpage.subregion(start, end)

    def htmlpage_region_inside(self, start_token_index, end_token_index):
        """The region in the HtmlPage corresonding to the area between 
        the start_token_index and the end_token_index. 

        This excludes the tokens at the specified indexes
        """
        start = self.token_page_indexes[start_token_index] + 1
        end = self.token_page_indexes[end_token_index] - 1
        return self.htmlpage.subregion(start, end)
    
    def htmlpage_tag(self, token_index):
        """The HtmlPage tag at corresponding to the token at token_index"""
        return self.htmlpage.parsed_body[self.token_page_indexes[token_index]]

    def __str__(self):
        summary = []
        for token, tindex in zip(self.page_tokens, self.token_page_indexes):
            text = "%s page[%s]: %s" % (self.token_dict.find_token(token), 
                tindex, self.htmlpage.parsed_body[tindex])
            summary.append(text)
        return "ExtractionPage\n==============\nTokens: %s\n\nRaw text: %s\n\n" \
                % ('\n'.join(summary), self.htmlpage.body)

class AnnotationText(object):
    __slots__ = ('start_text', 'follow_text')

    def __init__(self, start_text=None, follow_text=None):
        self.start_text = start_text
        self.follow_text = follow_text

    def __str__(self):
        return "AnnotationText(%s..%s)" % \
                (repr(self.start_text), repr(self.follow_text))


class AnnotationTag(PageRegion):
    """A tag that annotates part of the document

    It has the following properties:
        start_index - index of the token for the opening tag
        end_index - index of the token for the closing tag
        surrounds_attribute - the attribute name surrounded by this tag
        tag_attributes - list of (tag attribute, extracted attribute) tuples
                         for each item to be extracted from a tag attribute
        annotation_text - text prefix and suffix for the attribute to be extracted
        metadata - dict with annotation data not used by IBL extractor
    """
    __slots__ = ('surrounds_attribute', 'start_index', 'end_index',
            'tag_attributes', 'annotation_text', 'variant_id', 
            'metadata')
    
    def __init__(self, start_index, end_index, surrounds_attribute=None, 
            annotation_text=None, tag_attributes=None, variant_id=None):
        PageRegion.__init__(self, start_index, end_index)
        self.surrounds_attribute = surrounds_attribute
        self.annotation_text = annotation_text
        self.tag_attributes = tag_attributes or []
        self.variant_id = variant_id
        self.metadata = {}

    def __str__(self):
        return "AnnotationTag(%s)" % ", ".join(
                ["%s=%s" % (s, getattr(self, s)) \
                for s in self.__slots__ if getattr(self, s)])

    def __repr__(self):
        return str(self)


########NEW FILE########
__FILENAME__ = pageparsing
"""
Page parsing

Parsing of web pages for extraction task.
"""
import json
from collections import defaultdict
from numpy import array

from scrapely.htmlpage import HtmlTagType, HtmlTag, HtmlPage
from scrapely.extraction.pageobjects import (AnnotationTag,
    TemplatePage, ExtractionPage, AnnotationText, TokenDict, FragmentedHtmlPageRegion)

def parse_strings(template_html, extraction_html):
    """Create a template and extraction page from raw strings

    this is useful for testing purposes
    """
    t = TokenDict()
    template_page = HtmlPage(body=template_html)
    extraction_page = HtmlPage(body=extraction_html)
    return (parse_template(t, template_page), 
            parse_extraction_page(t, extraction_page))

def parse_template(token_dict, template_html):
    """Create an TemplatePage object by parsing the annotated html"""
    parser = TemplatePageParser(token_dict)
    parser.feed(template_html)
    return parser.to_template()

def parse_extraction_page(token_dict, page_html):
    """Create an ExtractionPage object by parsing the html"""
    parser = ExtractionPageParser(token_dict)
    parser.feed(page_html)
    return parser.to_extraction_page()

class InstanceLearningParser(object):
    """Base parser for instance based learning algorithm
    
    This does not require correct HTML and the parsing method should not alter
    the original tag order. It is important that parsing results do not vary.
    """
    def __init__(self, token_dict):
        self.token_dict = token_dict
        self.token_list = []
    
    def _add_token(self, token, token_type, start, end):
        tid = self.token_dict.tokenid(token, token_type)
        self.token_list.append(tid)

    def feed(self, html_page):
        self.html_page = html_page
        self.previous_element_class = None
        for index, data in enumerate(html_page.parsed_body):
            if isinstance(data, HtmlTag):
                self._add_token(data.tag, data.tag_type, data.start, data.end)
                self.handle_tag(data, index)
            else:
                self.handle_data(data, index)
            self.previous_element_class = data.__class__

    def handle_data(self, html_data_fragment, index):
        pass

    def handle_tag(self, html_tag, index):
        pass

_END_UNPAIREDTAG_TAGS = ["form", "div", "p", "table", "tr", "td"]
_AUTO_CLOSE_TAGS_ON_OPEN = {
    # the given keys closes the tags in the list
    "p": ["p"],
    "option": ["option"],
}
_AUTO_CLOSE_TAGS_ON_CLOSE = {
    "select": ["option"],
}
class TemplatePageParser(InstanceLearningParser):
    """Template parsing for instance based learning algorithm"""

    def __init__(self, token_dict):
        InstanceLearningParser.__init__(self, token_dict)
        self.annotations = []
        self.ignored_regions = []
        self.extra_required_attrs = []
        self.ignored_tag_stacks = defaultdict(list)
        # tag names that have not been completed
        self.labelled_tag_stacks = defaultdict(list)
        self.replacement_stacks = defaultdict(list)
        self.unpairedtag_stack = []
        self.variant_stack = []
        self.prev_data = None
        self.last_text_region = None
        self.next_tag_index = 0

    def handle_tag(self, html_tag, index):
        if self.last_text_region:
            self._process_text('')
        
        if html_tag.tag_type == HtmlTagType.OPEN_TAG:
            self._handle_open_tag(html_tag)
        elif html_tag.tag_type == HtmlTagType.CLOSE_TAG:
            self._handle_close_tag(html_tag)
        else:
            # the tag is not paired, it can contain only attribute annotations
            self._handle_unpaired_tag(html_tag)
    
    @staticmethod
    def _read_template_annotation(html_tag):
        template_attr = html_tag.attributes.get('data-scrapy-annotate')
        if template_attr is None:
            return None
        unescaped = template_attr.replace('&quot;', '"')
        return json.loads(unescaped)
    
    @staticmethod
    def _read_bool_template_attribute(html_tag, attribute):
        return html_tag.attributes.get("data-scrapy-" + attribute) == "true"
    
    def _close_unpaired_tag(self):
        self.unpairedtag_stack[0].end_index = self.next_tag_index
        self.unpairedtag_stack = []

    def _handle_unpaired_tag(self, html_tag):
        if self._read_bool_template_attribute(html_tag, "ignore") and html_tag.tag == "img":
            self.ignored_regions.append((self.next_tag_index, self.next_tag_index + 1))
        elif self._read_bool_template_attribute(html_tag, "ignore-beneath"):
            self.ignored_regions.append((self.next_tag_index, None))
        jannotation = self._read_template_annotation(html_tag)
        if jannotation:
            if self.unpairedtag_stack:
                self._close_unpaired_tag()
                
            annotation = AnnotationTag(self.next_tag_index, self.next_tag_index + 1)
            attribute_annotations = jannotation.pop('annotations', {}).items()
            content_key = jannotation.pop('text-content', 'content')
            for extract_attribute, tag_value in attribute_annotations:
                if extract_attribute == content_key:
                    annotation.surrounds_attribute = tag_value
                    self.unpairedtag_stack.append(annotation)
                else:
                    annotation.tag_attributes.append((extract_attribute, tag_value))
            self.annotations.append(annotation)

            self.extra_required_attrs.extend(jannotation.pop('required', []))
            variant_id = jannotation.pop('variant', 0)
            if variant_id > 0:
                annotation.variant_id = variant_id
            assert jannotation.pop("generated", False) == False
            annotation.metadata = jannotation

        self.next_tag_index += 1

    def _handle_open_tag(self, html_tag):
        if self._read_bool_template_attribute(html_tag, "ignore"):
            if html_tag.tag == "img":
                self.ignored_regions.append((self.next_tag_index, self.next_tag_index + 1))
            else:
                self.ignored_regions.append((self.next_tag_index, None))
                self.ignored_tag_stacks[html_tag.tag].append(html_tag)
                
        elif self.ignored_tag_stacks.get(html_tag.tag):
            self.ignored_tag_stacks[html_tag.tag].append(None)
        if self._read_bool_template_attribute(html_tag, "ignore-beneath"):
            self.ignored_regions.append((self.next_tag_index, None))
        
        replacement = html_tag.attributes.pop("data-scrapy-replacement", None)
        if replacement:
            self.token_list.pop()
            self._add_token(replacement, html_tag.tag_type, html_tag.start, html_tag.end)
            self.replacement_stacks[html_tag.tag].append(replacement)
        elif html_tag.tag in self.replacement_stacks:
            self.replacement_stacks[html_tag.tag].append(None)

        if self.unpairedtag_stack:
            if html_tag.tag in _END_UNPAIREDTAG_TAGS:
                self._close_unpaired_tag()
            else:
                self.unpairedtag_stack.append(html_tag.tag)
        
        tagname = replacement or self._update_replacement_stack(html_tag)
        self._handle_unclosed_tags(tagname, _AUTO_CLOSE_TAGS_ON_OPEN)
               
        jannotation = self._read_template_annotation(html_tag)
        if not jannotation:
            if tagname in self.labelled_tag_stacks:
                # add this tag to the stack to match correct end tag
                self.labelled_tag_stacks[tagname].append(None)
            self.next_tag_index += 1
            return
        
        annotation = AnnotationTag(self.next_tag_index, None)
        if jannotation.pop('generated', False):
            self.token_list.pop()
            annotation.start_index -= 1
            if self.previous_element_class == HtmlTag:
                annotation.annotation_text = AnnotationText('')
            else:
                annotation.annotation_text = AnnotationText(self.prev_data)
            if self._read_bool_template_attribute(html_tag, "ignore") \
                    or self._read_bool_template_attribute(html_tag, "ignore-beneath"):
                ignored = self.ignored_regions.pop()
                self.ignored_regions.append((ignored[0]-1, ignored[1]))
                
        self.extra_required_attrs.extend(jannotation.pop('required', []))
        
        attribute_annotations = jannotation.pop('annotations', {}).items()
        content_key = jannotation.pop('text-content', 'content')
        for extract_attribute, tag_value in attribute_annotations:
            if extract_attribute == content_key:
                annotation.surrounds_attribute = tag_value
            else:
                annotation.tag_attributes.append((extract_attribute, tag_value))
 
        variant_id = jannotation.pop('variant', 0)
        if variant_id > 0:
            if annotation.surrounds_attribute is not None:
                self.variant_stack.append(variant_id)
            else:
                annotation.variant_id = variant_id
       
        annotation.metadata = jannotation

        if annotation.annotation_text is None:
            self.next_tag_index += 1
        if self.variant_stack and annotation.variant_id is None:
            variant_id = self.variant_stack[-1]
            if variant_id == '0':
                variant_id = None
            annotation.variant_id = variant_id
        
        # look for a closing tag if the content is important
        if annotation.surrounds_attribute:
            self.labelled_tag_stacks[tagname].append(annotation)
        else:
            annotation.end_index = annotation.start_index + 1
            self.annotations.append(annotation)

    def _handle_close_tag(self, html_tag):
        
        if self.unpairedtag_stack:
            if html_tag.tag == self.unpairedtag_stack[-1]:
                self.unpairedtag_stack.pop()
            else:
                self._close_unpaired_tag()

        ignored_tags = self.ignored_tag_stacks.get(html_tag.tag)
        if ignored_tags is not None:
            tag = ignored_tags.pop()
            if isinstance(tag, HtmlTag):
                for i in range(-1, -len(self.ignored_regions) - 1, -1):
                    if self.ignored_regions[i][1] is None:
                        self.ignored_regions[i] = (self.ignored_regions[i][0], self.next_tag_index)
                        break
            if len(ignored_tags) == 0:
                del self.ignored_tag_stacks[html_tag.tag]

        tagname = self._update_replacement_stack(html_tag)
        self._handle_unclosed_tags(tagname, _AUTO_CLOSE_TAGS_ON_CLOSE)

        labelled_tags = self.labelled_tag_stacks.get(tagname)
        if labelled_tags is None:
            self.next_tag_index += 1
            return
        annotation = labelled_tags.pop()
        if annotation is None:
            self.next_tag_index += 1
        else:
            annotation.end_index = self.next_tag_index
            self.annotations.append(annotation)
            if annotation.annotation_text is not None:
                self.token_list.pop()
                self.last_text_region = annotation
            else:
                self.next_tag_index += 1
            if len(labelled_tags) == 0:
                del self.labelled_tag_stacks[tagname]
            if annotation.variant_id and self.variant_stack:
                prev = self.variant_stack.pop()
                if prev != annotation.variant_id:
                    raise ValueError("unbalanced variant annotation tags")
                    
    def _update_replacement_stack(self, html_tag):
        replacement = html_tag.tag
        if html_tag.tag in self.replacement_stacks:
            replacement = self.replacement_stacks[html_tag.tag].pop()
            if replacement:
                self.token_list.pop()
                self._add_token(replacement, html_tag.tag_type, html_tag.start, html_tag.end)
            if len(self.replacement_stacks[html_tag.tag]) == 0:
                del self.replacement_stacks[html_tag.tag]
        return replacement

    def _handle_unclosed_tags(self, tagname, auto_close_tags):
        """I.e. can't be a p inside another p. Also, an open p element closes
        a previous open p element"""
        if tagname in auto_close_tags:
            for _close_tag in auto_close_tags[tagname]:
                if _close_tag in self.labelled_tag_stacks:
                    annotation = self.labelled_tag_stacks.pop(_close_tag)[0]
                    annotation.end_index = self.next_tag_index
                    self.annotations.append(annotation)
                    break
        return tagname

    def handle_data(self, html_data_fragment, index):
        fragment_text = self.html_page.fragment_data(html_data_fragment)
        self._process_text(fragment_text)

    def _process_text(self, text):
        if self.last_text_region is not None:
            self.last_text_region.annotation_text.follow_text = text
            self.last_text_region = None
        self.prev_data = text

    def to_template(self):
        """create a TemplatePage from the data fed to this parser"""
        return TemplatePage(self.token_dict, self.token_list, self.annotations,
                self.html_page.page_id, self.ignored_regions, self.extra_required_attrs)

class ExtractionPageParser(InstanceLearningParser):
    """Parse an HTML page for extraction using the instance based learning
    algorithm

    This needs to extract the tokens in a similar way to LabelledPageParser,
    it needs to also maintain a mapping from token index to the original content
    so that once regions are identified, the original content can be extracted.
    """
    def __init__(self, token_dict):
        InstanceLearningParser.__init__(self, token_dict)
        self._page_token_indexes = []

    def handle_tag(self, html_tag, index):
        self._page_token_indexes.append(index)
    
    def to_extraction_page(self):
        return ExtractionPage(self.html_page, self.token_dict, array(self.token_list), 
                self._page_token_indexes)

########NEW FILE########
__FILENAME__ = regionextract
"""
Region Extract

Custom extraction for regions in a document
"""
import re
import operator
import copy
import pprint
import cStringIO
from itertools import groupby, izip, starmap

from numpy import array

from scrapely.descriptor import FieldDescriptor
from scrapely.htmlpage import HtmlPageRegion
from scrapely.extraction.similarity import (similar_region,
    longest_unique_subsequence, common_prefix)
from scrapely.extraction.pageobjects import (AnnotationTag,
    PageRegion, FragmentedHtmlPageRegion)

_EXTRACT_HTML = lambda x: x
_DEFAULT_DESCRIPTOR = FieldDescriptor('none', None)

__all__ = ['BasicTypeExtractor',
           'TraceExtractor',
           'RepeatedDataExtractor',
           'AdjacentVariantExtractor',
           'RecordExtractor',
           'TemplatePageExtractor',
           'TextRegionDataExtractor',
           'attrs2dict',
           'labelled_element']

def labelled_element(obj):
    """
    Returns labelled element of the object (extractor or labelled region)
    """
    return getattr(obj, 'annotation', obj)

def _compose(f, g):
    """given unary functions f and g, return a function that computes f(g(x))
    """
    def _exec(x):
        ret = g(x)
        return f(ret) if ret is not None else None
    return _exec

class BasicTypeExtractor(object):
    """The BasicTypeExtractor extracts single attributes corresponding to 
    annotations.
    
    For example:
    >>> from scrapely.extraction.pageparsing import parse_strings
    >>> template, page = parse_strings( \
        u'<h1 data-scrapy-annotate="{&quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">x</h1>', u'<h1> a name</h1>')
    >>> ex = BasicTypeExtractor(template.annotations[0])
    >>> ex.extract(page, 0, 1, None)
    [(u'name', u' a name')]

    It supports attribute descriptors
    >>> descriptor = FieldDescriptor('name', None, lambda x: x.strip())
    >>> ex = BasicTypeExtractor(template.annotations[0], {'name': descriptor})
    >>> ex.extract(page, 0, 1, None)
    [(u'name', u'a name')]
    
    It supports ignoring regions
    >>> template, page = parse_strings(\
        u'<div data-scrapy-annotate="{&quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">x<b> xx</b></div>',\
        u'<div>a name<b> id-9</b></div>')
    >>> ex = BasicTypeExtractor(template.annotations[0])
    >>> ex.extract(page, 0, 3, [PageRegion(1, 2)])
    [(u'name', u'a name')]
    """

    def __init__(self, annotation, attribute_descriptors=None):
        self.annotation = annotation
        if attribute_descriptors is None:
            attribute_descriptors = {}

        if annotation.surrounds_attribute:
            descriptor = attribute_descriptors.get(annotation.surrounds_attribute)
            if descriptor:
                self.content_validate = descriptor.extractor
            else:
                self.content_validate = _EXTRACT_HTML
            self.extract = self._extract_content

        if annotation.tag_attributes:
            self.tag_data = []
            for (tag_attr, extraction_attr) in annotation.tag_attributes:
                descriptor = attribute_descriptors.get(extraction_attr)
                extractf = descriptor.extractor if descriptor else _EXTRACT_HTML
                self.tag_data.append((extractf, tag_attr, extraction_attr))

            self.extract = self._extract_both if \
                    annotation.surrounds_attribute else self._extract_attribute
        
    def _extract_both(self, page, start_index, end_index, ignored_regions=None, **kwargs):
        return self._extract_content(page, start_index, end_index, ignored_regions) + \
            self._extract_attribute(page, start_index, end_index, ignored_regions)

    def _extract_content(self, extraction_page, start_index, end_index, ignored_regions=None, **kwargs):
        """extract content between annotation indexes"""
        if ignored_regions and (start_index <= ignored_regions[0].start_index and
                    end_index >= ignored_regions[-1].end_index):
            starts = [start_index] + [i.end_index for i in ignored_regions if i.end_index is not None]
            ends = [i.start_index for i in ignored_regions]
            if starts[-1] is not None:
                ends.append(end_index)
            included_regions = izip(starts, ends)
            if ends[0] is None:
                included_regions.next()
            regions = starmap(extraction_page.htmlpage_region_inside, included_regions)
            region = FragmentedHtmlPageRegion(extraction_page.htmlpage, list(regions))
        else:
            region = extraction_page.htmlpage_region_inside(start_index, end_index)
        validated = self.content_validate(region)
        return [(self.annotation.surrounds_attribute, validated)] if validated else []
    
    def _extract_attribute(self, extraction_page, start_index, end_index, ignored_regions=None, **kwargs):
        data = []
        for (f, ta, ea) in self.tag_data:
            tag_value = extraction_page.htmlpage_tag(start_index).attributes.get(ta)
            if tag_value:
                region = HtmlPageRegion(extraction_page.htmlpage, tag_value)
                extracted = f(region)
                if extracted is not None:
                    data.append((ea, extracted))
        return data

    @classmethod
    def create(cls, annotations, attribute_descriptors=None):
        """Create a list of basic extractors from the given annotations
        and attribute descriptors
        """
        if attribute_descriptors is None:
            attribute_descriptors = {}
        return [cls._create_basic_extractor(annotation, attribute_descriptors) \
            for annotation in annotations \
            if annotation.surrounds_attribute or annotation.tag_attributes]
    
    @staticmethod
    def _create_basic_extractor(annotation, attribute_descriptors):
        """Create a basic type extractor for the annotation"""
        text_region = annotation.annotation_text
        if text_region is not None:
            region_extract = TextRegionDataExtractor(text_region.start_text, 
                text_region.follow_text).extract
            # copy attribute_descriptors and add the text extractor
            descriptor_copy = dict(attribute_descriptors)
            attr_descr = descriptor_copy.get(annotation.surrounds_attribute, 
                    _DEFAULT_DESCRIPTOR)
            attr_descr = copy.copy(attr_descr)
            attr_descr.extractor = _compose(attr_descr.extractor, region_extract)
            descriptor_copy[annotation.surrounds_attribute] = attr_descr
            attribute_descriptors = descriptor_copy
        return BasicTypeExtractor(annotation, attribute_descriptors)
    
    def extracted_item(self):
        """key used to identify the item extracted"""
        return (self.annotation.surrounds_attribute, self.annotation.tag_attributes)
    
    def __repr__(self):
        return str(self)

    def __str__(self):
        messages = ['BasicTypeExtractor(']
        if self.annotation.surrounds_attribute:
            messages.append(self.annotation.surrounds_attribute)
            if self.content_validate != _EXTRACT_HTML:
                messages += [', extracted with \'', 
                        self.content_validate.__name__, '\'']
        
        if self.annotation.tag_attributes:
            if self.annotation.surrounds_attribute:
                messages.append(';')
            for (f, ta, ea) in self.tag_data:
                messages += [ea, ': tag attribute "', ta, '"']
                if f != _EXTRACT_HTML:
                    messages += [', validated by ', str(f)]
        messages.append(", template[%s:%s])" % \
                (self.annotation.start_index, self.annotation.end_index))
        return ''.join(messages)

class RepeatedDataExtractor(object):
    """Data extractor for handling repeated data"""

    def __init__(self, prefix, suffix, extractors):
        self.prefix = array(prefix)
        self.suffix = array(suffix)
        self.extractor = copy.copy(extractors[0])
        self.annotation = copy.copy(self.extractor.annotation)
        self.annotation.end_index = extractors[-1].annotation.end_index

    def extract(self, page, start_index, end_index, ignored_regions, **kwargs):
        """repeatedly find regions bounded by the repeated 
        prefix and suffix and extract them
        """
        prefixlen = len(self.prefix)
        suffixlen = len(self.suffix)
        index = max(0, start_index - prefixlen)
        max_index = min(len(page.page_tokens) - suffixlen, end_index + len(self.suffix))
        max_start_index = max_index - prefixlen
        extracted = []
        while index <= max_start_index:
            prefix_end = index + prefixlen
            if (page.page_tokens[index:prefix_end] == self.prefix).all():
                for peek in xrange(prefix_end, max_index + 1):
                    if (page.page_tokens[peek:peek + suffixlen] \
                            == self.suffix).all():
                        extracted += self.extractor.extract(page, 
                                prefix_end - 1, peek, ignored_regions, suffix_max_length=suffixlen)
                        index = max(peek, index + 1)
                        break
                else:
                    break
            else:
                index += 1
        return extracted

    @staticmethod
    def apply(template, extractors):
        tokens = template.page_tokens
        output_extractors = []
        group_key = lambda x: (x.extracted_item(), x.annotation.variant_id)
        for extr_key, extraction_group in groupby(extractors, group_key):
            extraction_group = list(extraction_group)
            if extr_key is None or len(extraction_group) == 1:
                output_extractors += extraction_group
                continue

            separating_tokens = [ \
                tokens[x.annotation.end_index:y.annotation.start_index+1] \
                for (x, y) in zip(extraction_group[:-1], extraction_group[1:])]
            
            # calculate the common prefix
            group_start = extraction_group[0].annotation.start_index
            prefix_start = max(0, group_start - len(separating_tokens[0]))
            first_prefix = tokens[prefix_start:group_start+1]
            prefixes = [first_prefix] + separating_tokens
            prefix_pattern = list(reversed(
                common_prefix(*map(reversed, prefixes))))
            
            # calculate the common suffix
            group_end = extraction_group[-1].annotation.end_index
            last_suffix = tokens[group_end:group_end + \
                    len(separating_tokens[-1])]
            suffixes = separating_tokens + [last_suffix]
            suffix_pattern = common_prefix(*suffixes)
            
            # create a repeated data extractor, if there is a suitable 
            # prefix and suffix. (TODO: tune this heuristic)
            matchlen = len(prefix_pattern) + len(suffix_pattern)
            if matchlen >= len(separating_tokens):
                group_extractor = RepeatedDataExtractor(prefix_pattern, 
                    suffix_pattern, extraction_group)
                output_extractors.append(group_extractor)
            else:
                output_extractors += extraction_group
        return output_extractors
    
    def extracted_item(self):
        """key used to identify the item extracted"""
        return self.extractor.extracted_item()
    
    def __repr__(self):
        return "Repeat(%r)" % self.extractor

    def __str__(self):
        return "Repeat(%s)" % self.extractor

class TransposedDataExtractor(object):
    """ """
    pass

_namef = operator.itemgetter(0)
_valuef = operator.itemgetter(1)
def attrs2dict(attributes):
    """convert a list of attributes (name, value) tuples
    into a dict of lists. 

    For example:
    >>> l = [('name', 'sofa'), ('colour', 'red'), ('colour', 'green')]
    >>> attrs2dict(l) == {'name': ['sofa'], 'colour': ['red', 'green']}
    True
    """
    grouped_data = groupby(sorted(attributes, key=_namef), _namef)
    return dict((name, map(_valuef, data)) for (name, data)  in grouped_data)

class RecordExtractor(object):
    """The RecordExtractor will extract records given annotations.
    
    It looks for a similar region in the target document, using the ibl
    similarity algorithm. The annotations are partitioned by the first similar
    region found and searched recursively.

    Records are represented as dicts mapping attribute names to lists
    containing their values.
    
    For example:
    >>> from scrapely.extraction.pageparsing import parse_strings
    >>> template, page = parse_strings( \
            u'<h1 data-scrapy-annotate="{&quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">x</h1>' + \
            u'<p data-scrapy-annotate="{&quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">y</p>', \
            u'<h1>name</h1> <p>description</p>')
    >>> basic_extractors = map(BasicTypeExtractor, template.annotations)
    >>> ex = RecordExtractor.apply(template, basic_extractors)[0]
    >>> ex.extract(page)
    [{u'description': [u'description'], u'name': [u'name']}]
    """
    
    def __init__(self, extractors, template_tokens):
        """Construct a RecordExtractor for the given annotations and their
        corresponding region extractors
        """
        self.extractors = extractors
        self.template_tokens = template_tokens
        self.template_ignored_regions = []
        start_index = min(e.annotation.start_index for e in extractors)
        end_index = max(e.annotation.end_index for e in extractors)
        self.annotation = AnnotationTag(start_index, end_index)
        self.best_match = longest_unique_subsequence
    
    def extract(self, page, start_index=0, end_index=None, ignored_regions=None, **kwargs):
        """extract data from an extraction page
        
        The region in the page to be extracted from may be specified using
        start_index and end_index
        """
        if ignored_regions is None:
            ignored_regions = []
        region_elements = sorted(self.extractors + ignored_regions, key=lambda x: labelled_element(x).start_index)
        _, _, attributes = self._doextract(page, region_elements, start_index, 
                end_index, **kwargs)
        # collect variant data, maintaining the order of variants
        variant_ids = []; variants = {}; items = []
        for k, v in attributes:
            if isinstance(k, int):
                if k in variants:
                    variants[k] += v
                else:
                    variant_ids.append(k)
                    variants[k] = v
            else:
                items.append((k, v))
        
        variant_records = [('variants', attrs2dict(variants[vid])) \
                for vid in variant_ids]
        items += variant_records
        return [attrs2dict(items)]
    
    def _doextract(self, page, region_elements, start_index, end_index, nested_regions=None, ignored_regions=None, **kwargs):
        """Carry out extraction of records using the given annotations
        in the page tokens bounded by start_index and end_index
        """
        # reorder extractors leaving nested ones for the end and separating
        # ignore regions
        nested_regions = nested_regions or []
        ignored_regions = ignored_regions or []
        first_region, following_regions = region_elements[0], region_elements[1:]
        while following_regions and labelled_element(following_regions[0]).start_index \
                < labelled_element(first_region).end_index:
            region = following_regions.pop(0)
            labelled = labelled_element(region)
            if isinstance(labelled, AnnotationTag) or (nested_regions and \
                    labelled_element(nested_regions[-1]).start_index < labelled.start_index \
                    < labelled_element(nested_regions[-1]).end_index):
                nested_regions.append(region)
            else:
                ignored_regions.append(region)
        extracted_data = []
        # end_index is inclusive, but similar_region treats it as exclusive
        end_region = None if end_index is None else end_index + 1
        labelled = labelled_element(first_region)
        score, pindex, sindex = \
            similar_region(page.page_tokens, self.template_tokens,
                labelled, start_index, end_region, self.best_match, **kwargs)
        if score > 0:
            if isinstance(labelled, AnnotationTag):
                similar_ignored_regions = []
                start = pindex
                for i in ignored_regions:
                    s, p, e = similar_region(page.page_tokens, self.template_tokens, \
                              i, start, sindex, self.best_match, **kwargs)
                    if s > 0:
                        similar_ignored_regions.append(PageRegion(p, e))
                        start = e or start
                extracted_data = first_region.extract(page, pindex, sindex, similar_ignored_regions, **kwargs)
                if extracted_data:
                    if first_region.annotation.variant_id:
                        extracted_data = [(first_region.annotation.variant_id, extracted_data)]
            
            if nested_regions:
                _, _, nested_data = self._doextract(page, nested_regions, pindex, sindex, **kwargs)
                extracted_data += nested_data
            if following_regions:
                _, _, following_data = self._doextract(page, following_regions, sindex or start_index, end_index, **kwargs)
                extracted_data += following_data
        
        elif following_regions:
            end_index, _, following_data = self._doextract(page, following_regions, start_index, end_index, **kwargs)
            if end_index is not None:
                pindex, sindex, extracted_data = self._doextract(page, [first_region], start_index, end_index - 1, nested_regions, ignored_regions, **kwargs)
            extracted_data += following_data
        elif nested_regions:
            _, _, nested_data = self._doextract(page, nested_regions, start_index, end_index, **kwargs)
            extracted_data += nested_data
        return pindex, sindex, extracted_data
                
    @classmethod
    def apply(cls, template, extractors):
        return [cls(extractors, template.page_tokens)]
    
    def extracted_item(self):
        return [self.__class__.__name__] + \
                sorted(e.extracted_item() for e in self.extractors)
    
    def __repr__(self):
        return str(self)

    def __str__(self):
        stream = cStringIO.StringIO()
        pprint.pprint(self.extractors, stream)
        stream.seek(0)
        template_data = stream.read()
        if template_data:
            return "%s[\n%s\n]" % (self.__class__.__name__, template_data)
        return "%s[none]" % (self.__class__.__name__)

class AdjacentVariantExtractor(RecordExtractor):
    """Extractor for variants

    This simply extends the RecordExtractor to output data in a "variants"
    attribute.

    The "apply" method will only apply to variants whose items are all adjacent and 
    it will appear as one record so that it can be handled by the RepeatedDataExtractor. 
    """

    def extract(self, page, start_index=0, end_index=None, ignored_regions=None, **kwargs):
        records = RecordExtractor.extract(self, page, start_index, end_index, ignored_regions, **kwargs)
        return [('variants', r['variants'][0]) for r in records if r]
    
    @classmethod
    def apply(cls, template, extractors):
        adjacent_variants = set([])
        variantf = lambda x: x.annotation.variant_id
        for vid, egroup in groupby(extractors, variantf):
            if not vid:
                continue
            if vid in adjacent_variants:
                adjacent_variants.remove(vid)
            else:
                adjacent_variants.add(vid)
        new_extractors = []
        for variant, group_seq in groupby(extractors, variantf):
            group_seq = list(group_seq)
            if variant in adjacent_variants:
                record_extractor = AdjacentVariantExtractor(group_seq, template.page_tokens)
                new_extractors.append(record_extractor)
            else:
                new_extractors += group_seq
        return new_extractors

    def __repr__(self):
        return str(self)

class TraceExtractor(object):
    """Extractor that wraps other extractors and prints an execution
    trace of the extraction process to aid debugging
    """

    def __init__(self, traced, template):
        self.traced = traced
        self.annotation = traced.annotation
        tstart = traced.annotation.start_index
        tend = traced.annotation.end_index
        self.tprefix = " ".join([template.token_dict.token_string(t)
            for t in template.page_tokens[tstart-4:tstart+1]])
        self.tsuffix = " ".join([template.token_dict.token_string(t)
            for t in template.page_tokens[tend:tend+5]])
    
    def summarize_trace(self, page, start, end, ret):
        text_start = page.htmlpage.parsed_body[page.token_page_indexes[start]].start
        text_end = page.htmlpage.parsed_body[page.token_page_indexes[end or -1]].end
        page_snippet = "(...%s)%s(%s...)" % (
                page.htmlpage.body[text_start-50:text_start].replace('\n', ' '), 
                page.htmlpage.body[text_start:text_end], 
                page.htmlpage.body[text_end:text_end+50].replace('\n', ' '))
        pre_summary = "\nstart %s page[%s:%s]\n" % (self.traced.__class__.__name__, start, end)
        post_summary = """
%s page[%s:%s] 

html
%s

annotation
...%s
%s
%s...

extracted
%s
        """ % (self.traced.__class__.__name__, start, end, page_snippet, 
                self.tprefix, self.annotation, self.tsuffix, [r for r in ret if 'trace' not in r])
        return pre_summary, post_summary

    def extract(self, page, start, end, ignored_regions, **kwargs):
        ret = self.traced.extract(page, start, end, ignored_regions, **kwargs)
        if not ret:
            return []

        # handle records by inserting a trace and combining with variant traces
        if len(ret) == 1 and isinstance(ret[0], dict):
            item = ret[0]
            trace = item.pop('trace', [])
            variants = item.get('variants', ())
            for variant in variants:
                trace += variant.pop('trace', [])
            pre_summary, post_summary = self.summarize_trace(page, start, end, ret)
            item['trace'] = [pre_summary] + trace + [post_summary]
            return ret
        
        pre_summary, post_summary = self.summarize_trace(page, start, end, ret)
        return [('trace', pre_summary)] + ret + [('trace', post_summary)]
    
    @staticmethod
    def apply(template, extractors):
        output = []
        for extractor in extractors:
            if not isinstance(extractor, TraceExtractor):
                extractor = TraceExtractor(extractor, template)
            output.append(extractor)
        return output
    
    def extracted_item(self):
        return self.traced.extracted_item()

    def __repr__(self):
        return "Trace(%s)" % repr(self.traced)

class TemplatePageExtractor(object):
    """Top level extractor for a template page"""

    def __init__(self, template, extractors):
        # fixme: handle multiple items per page
        self.extractor = extractors[0]
        self.template = template

    def extract(self, page, start_index=0, end_index=None):
        return self.extractor.extract(page, start_index, end_index, self.template.ignored_regions)
    
    def __repr__(self):
        return repr(self.extractor)

    def __str__(self):
        return str(self.extractor)

# Based on nltk's WordPunctTokenizer
_tokenize = re.compile(r'\w+|[^\w\s]+', re.UNICODE | re.MULTILINE | re.DOTALL).findall

class TextRegionDataExtractor(object):
    """Data Extractor for extracting text fragments from an annotation page
    fragment or string. It extracts based on the longest unique prefix and
    suffix.

    for example:
    >>> extractor = TextRegionDataExtractor('designed by ', '.')
    >>> extractor.extract_text("by Marc Newson.")
    'Marc Newson'

    Both prefix and suffix are optional:
    >>> extractor = TextRegionDataExtractor('designed by ')
    >>> extractor.extract_text("by Marc Newson.")
    'Marc Newson.'
    >>> extractor = TextRegionDataExtractor(suffix='.')
    >>> extractor.extract_text("by Marc Newson.")
    'by Marc Newson'

    It requires a minimum match of at least one word or punctuation character:
    >>> extractor = TextRegionDataExtractor('designed by')
    >>> extractor.extract_text("y Marc Newson.") is None
    True
    """
    def __init__(self, prefix=None, suffix=None):
        self.prefix = (prefix or '')[::-1]
        self.suffix = suffix or ''
        self.minprefix = self.minmatch(self.prefix)
        self.minsuffix = self.minmatch(self.suffix)
 
    @staticmethod
    def minmatch(matchstring):
        """the minimum number of characters that should match in order
        to consider it a match for that string.

        This uses the last word of punctuation character
        """
        tokens = _tokenize(matchstring or '')
        return len(tokens[0]) if tokens else 0

    def extract(self, region):
        """Extract a region from the region passed"""
        text = self.extract_text(region)
        return HtmlPageRegion(region.htmlpage, text) if text else None

    def extract_text(self, text):
        """Extract a substring from the text"""
        pref_index = 0
        if self.minprefix > 0:
            rev_idx, plen = longest_unique_subsequence(text[::-1], self.prefix)
            if plen < self.minprefix:
                return None
            pref_index = -rev_idx
        if self.minsuffix == 0:
            return text[pref_index:]
        sidx, slen = longest_unique_subsequence(text[pref_index:], self.suffix)
        if slen < self.minsuffix:
            return None
        return text[pref_index:pref_index + sidx]

########NEW FILE########
__FILENAME__ = similarity
"""
Similarity calculation for Instance based extraction algorithm.
"""
from itertools import izip, count
from operator import itemgetter
from heapq import nlargest

def common_prefix_length(a, b):
    """Calculate the length of the common prefix in both sequences passed.
    
    For example, the common prefix in this example is [1, 3]
    >>> common_prefix_length([1, 3, 4], [1, 3, 5, 1])
    2
    
    If there is no common prefix, 0 is returned
    >>> common_prefix_length([1], [])
    0
    """
    i = -1
    for i, x, y in izip(count(), a, b):
        if x != y:
            return i
    return i + 1

def common_prefix(*sequences):
    """determine the common prefix of all sequences passed
    
    For example:
    >>> common_prefix('abcdef', 'abc', 'abac')
    ['a', 'b']
    """
    prefix = []
    for sample in izip(*sequences):
        first = sample[0]
        if all(x == first for x in sample[1:]):
            prefix.append(first)
        else:
            break
    return prefix

def longest_unique_subsequence(to_search, subsequence, range_start=0, 
        range_end=None):
    """Find the longest unique subsequence of items in a list or array.  This
    searches the to_search list or array looking for the longest overlapping
    match with subsequence. If the largest match is unique (there is no other
    match of equivalent length), the index and length of match is returned.  If
    there is no match, (None, None) is returned.

    Please see section 3.2 of Extracting Web Data Using Instance-Based
    Learning by Yanhong Zhai and Bing Liu

    For example, the longest match occurs at index 2 and has length 3
    >>> to_search = [6, 3, 2, 4, 3, 2, 5]
    >>> longest_unique_subsequence(to_search, [2, 4, 3])
    (2, 3)
    
    When there are two equally long subsequences, it does not generate a match
    >>> longest_unique_subsequence(to_search, [3, 2])
    (None, None)

    range_start and range_end specify a range in which the match must begin
    >>> longest_unique_subsequence(to_search, [3, 2], 3)
    (4, 2)
    >>> longest_unique_subsequence(to_search, [3, 2], 0, 2)
    (1, 2)
    """
    startval = subsequence[0]
    if range_end is None:
        range_end = len(to_search)
    
    # the comparison to startval ensures only matches of length >= 1 and 
    # reduces the number of calls to the common_length function
    matches = ((i, common_prefix_length(to_search[i:], subsequence)) \
        for i in xrange(range_start, range_end) if startval == to_search[i])
    best2 = nlargest(2, matches, key=itemgetter(1))
    # if there is a single unique best match, return that
    if len(best2) == 1 or len(best2) == 2 and best2[0][1] != best2[1][1]:
        return best2[0]
    return None, None

def first_longest_subsequence(to_search, subsequence, range_start=0, range_end=None):
    """Find the first longest subsequence of the items in a list or array.

    range_start and range_end specify a range in which the match must begin.

    For example, the longest match occurs at index 2 and has length 3
    >>> to_search = [6, 3, 2, 4, 3, 2, 5]
    >>> first_longest_subsequence(to_search, [2, 4, 3])
    (2, 3)

    When there are two equally long subsequences, it return the nearest one)
    >>> first_longest_subsequence(to_search, [3, 2])
    (1, 2)

    >>> first_longest_subsequence([], [3, 2])
    (None, None)
    """
    startval = subsequence[0]
    if range_end is None:
        range_end = len(to_search)

    # the comparison to startval ensures only matches of length >= 1 and
    # reduces the number of calls to the common_length function
    matches = [(i, common_prefix_length(to_search[i:], subsequence)) \
        for i in xrange(range_start, range_end) if startval == to_search[i]]

    if not matches:
        return None, None
    # secondary sort on position and prefer the smaller one (near)
    return max(matches, key=lambda x: (x[1], -x[0]))

def similar_region(extracted_tokens, template_tokens, labelled_region, 
        range_start=0, range_end=None, best_match=longest_unique_subsequence, **kwargs):
    """Given a labelled section in a template, identify a similar region
    in the extracted tokens.

    The start and end index of the similar region in the extracted tokens
    is returned.

    This will return a tuple containing:
    (match score, start index, end index)
    where match score is the sum of the length of the matching prefix and 
    suffix. If there is no unique match, (0, None, None) will be returned.

    start_index and end_index specify a range in which the match must begin
    """
    data_length = len(extracted_tokens)
    if range_end is None:
        range_end = data_length
    # calculate the prefix score by finding a longest subsequence in 
    # reverse order
    reverse_prefix = template_tokens[labelled_region.start_index::-1]
    reverse_tokens = extracted_tokens[::-1]
    (rpi, pscore) = best_match(reverse_tokens, reverse_prefix,
            data_length - range_end, data_length - range_start)

    # None means nothing extracted. Index 0 means there cannot be a suffix.
    if not rpi:
        return 0, None, None
    
    # convert to an index from the start instead of in reverse
    prefix_index = len(extracted_tokens) - rpi - 1
 
    if labelled_region.end_index is None:
        return pscore, prefix_index, None
    elif kwargs.get("suffix_max_length", None) == 0:
        return pscore, prefix_index, range_start + 1

    suffix = template_tokens[labelled_region.end_index:]

    # if it's not a paired tag, use the best match between prefix & suffix
    if labelled_region.start_index == labelled_region.end_index:
        (match_index, sscore) = best_match(extracted_tokens,
            suffix, prefix_index, range_end)
        if match_index == prefix_index:
            return (pscore + sscore, prefix_index, match_index)
        elif pscore > sscore:
            return pscore, prefix_index, prefix_index
        elif sscore > pscore:
            return sscore, match_index, match_index
        return 0, None, None

    # calculate the suffix match on the tokens following the prefix. We could
    # consider the whole page and require a good match.
    (match_index, sscore) = best_match(extracted_tokens,
            suffix, prefix_index + 1, range_end)
    if match_index is None:
        return 0, None, None
    return (pscore + sscore, prefix_index, match_index)


########NEW FILE########
__FILENAME__ = extractors
"""
Extractors collection
"""

import re
import urlparse

from w3lib.html import remove_entities, remove_comments
from w3lib.url import safe_url_string

from scrapely.htmlpage import HtmlPage, HtmlTag, HtmlTagType

#FIXME: the use of "." needs to be localized
_NUMERIC_ENTITIES = re.compile("&#([0-9]+)(?:;|\s)", re.U)
_PRICE_NUMBER_RE = re.compile('(?:^|[^a-zA-Z0-9])(\d+(?:\.\d+)?)(?:$|[^a-zA-Z0-9])')
_NUMBER_RE = re.compile('(\d+(?:\.\d+)?)')
_DECIMAL_RE = re.compile(r'(\d[\d\,]*(?:(?:\.\d+)|(?:)))', re.U | re.M)
_VALPARTS_RE = re.compile("([\.,]?\d+)")

_IMAGES = (
    'mng', 'pct', 'bmp', 'gif', 'jpg', 'jpeg', 'png', 'pst', 'psp', 'tif',
    'tiff', 'ai', 'drw', 'dxf', 'eps', 'ps', 'svg',
)

_IMAGES_TYPES = '|'.join(_IMAGES)
_CSS_IMAGERE = re.compile("background(?:-image)?\s*:\s*url\((.*?)\)", re.I)
_BASE_PATH_RE = "/?(?:[^/]+/)*(?:.+%s)"
_IMAGE_PATH_RE = re.compile(_BASE_PATH_RE % '\.(?:%s)' % _IMAGES_TYPES, re.I)
_GENERIC_PATH_RE = re.compile(_BASE_PATH_RE % '', re.I)
_WS = re.compile("\s+", re.U)

# tags to keep (only for attributes with markup)
_TAGS_TO_KEEP = frozenset(['br', 'p', 'big', 'em', 'small', 'strong', 'sub', 
    'sup', 'ins', 'del', 'code', 'kbd', 'samp', 'tt', 'var', 'pre', 'listing',
    'plaintext', 'abbr', 'acronym', 'address', 'bdo', 'blockquote', 'q', 
    'cite', 'dfn', 'table', 'tr', 'th', 'td', 'tbody', 'ul', 'ol', 'li', 'dl',
    'dd', 'dt'])

# tag names to be replaced by other tag names (overrides tags_to_keep)
_TAGS_TO_REPLACE = {
    'h1': 'strong',
    'h2': 'strong',
    'h3': 'strong',
    'h4': 'strong',
    'h5': 'strong',
    'h6': 'strong',
    'b' : 'strong',
    'i' : 'em',
}
# tags whoose content will be completely removed (recursively)
# (overrides tags_to_keep and tags_to_replace)
_TAGS_TO_PURGE = ('script', 'img', 'input')

def htmlregion(text):
    """convenience function to make an html region from text.
    This is useful for testing
    """
    return HtmlPage(body=text).subregion()

def notags(region, tag_replace=u' '):
    """Removes all html tags"""
    fragments = getattr(region, 'parsed_fragments', None)
    if fragments is None:
        return region
    page = region.htmlpage
    data = [page.fragment_data(f) for f in fragments if not isinstance(f, HtmlTag)]
    return tag_replace.join(data)

def text(region):
    """Converts HTML to text. There is no attempt at formatting other than
    removing excessive whitespace,
    
    For example:
    >>> t = lambda s: text(htmlregion(s))
    >>> t(u'<h1>test</h1>')
    u'test'
    
    Leading and trailing whitespace are removed
    >>> t(u'<h1> test</h1> ')
    u'test'
    
    Comments are removed
    >>> t(u'test <!-- this is a comment --> me')
    u'test me'
    
    Text between script tags is ignored
    >>> t(u"scripts are<script>n't</script> ignored")
    u'scripts are ignored'
    
    HTML entities are converted to text
    >>> t(u"only &pound;42")
    u'only \\xa342'

    >>> t(u"<p>The text</p><?xml:namespace blabla/><p>is here</p>")
    u'The text is here'
    """
    text = remove_entities(region.text_content, encoding=region.htmlpage.encoding)
    return _WS.sub(u' ', text).strip()

def safehtml(region, allowed_tags=_TAGS_TO_KEEP, replace_tags=_TAGS_TO_REPLACE,
    tags_to_purge=_TAGS_TO_PURGE):
    """Creates an HTML subset, using a whitelist of HTML tags.

    The HTML generated is safe for display on a website,without escaping and
    should not cause formatting problems.
    
    Behaviour can be customized through the following keyword arguments:
        allowed_tags is a set of tags that are allowed
        replace_tags is a mapping of tags to alternative tags to substitute.
        tags_to_purge are tags that, if encountered, all content between the
            opening and closing tag is removed.

    For example:
    >>> t = lambda s: safehtml(htmlregion(s))
    >>> t(u'<strong>test <blink>test</blink></strong>')
    u'<strong>test test</strong>'
    
    Some tags, like script, are completely removed
    >>> t(u'<script>test </script>test')
    u'test'

    replace_tags define tags that are converted. By default all headers, bold and indenting
    are converted to strong and em.
    >>> t(u'<h2>header</h2> test <b>bold</b> <i>indent</i>')
    u'<strong>header</strong> test <strong>bold</strong> <em>indent</em>'
    
    tags_to_purge defines the tags that have enclosing content removed:
    >>> t(u'<p>test <script>test</script></p>')
    u'<p>test </p>'

    Comments are stripped, but entities are not converted
    >>> t(u'<!-- comment --> only &pound;42')
    u'only &pound;42'
    
    Paired tags are closed
    >>> t(u'<p>test')
    u'<p>test</p>'

    >>> t(u'<p>test <i><br/><b>test</p>')
    u'<p>test <em><br/><strong>test</strong></em></p>'

    """
    tagstack = []
    def _process_tag(tag):
        tagstr = replace_tags.get(tag.tag, tag.tag)
        if tagstr not in allowed_tags:
            return
        if tag.tag_type == HtmlTagType.OPEN_TAG:
            tagstack.append(tagstr)
            return u"<%s>" % tagstr
        elif tag.tag_type == HtmlTagType.CLOSE_TAG:
            try:
                last = tagstack.pop()
                # common case of matching tag
                if last == tagstr:
                    return u"</%s>" % last
                # output all preceeding tags (if present)
                revtags = tagstack[::-1]
                tindex = revtags.index(tagstr)
                del tagstack[-tindex-1:]
                return u"</%s></%s>" % (last, u"></".join(revtags[:tindex+1]))
            except (ValueError, IndexError):
                # popped from empty stack or failed to find the tag
                pass 
        else:
            assert tag.tag_type == HtmlTagType.UNPAIRED_TAG, "unrecognised tag type"
            return u"<%s/>" % tag.tag
    chunks = list(_process_markup(region, lambda text: text, 
        _process_tag, tags_to_purge)) + ["</%s>" % t for t in reversed(tagstack)]
    return u''.join(chunks).strip()

def _process_markup(region, textf, tagf, tags_to_purge=_TAGS_TO_PURGE):
    fragments = getattr(region, 'parsed_fragments', None)
    if fragments is None:
        yield textf(region)
        return
    fiter = iter(fragments)
    for fragment in fiter:
        if isinstance(fragment, HtmlTag):
            # skip forward to closing script tags
            tag = fragment.tag
            if tag in tags_to_purge:
                # if opening, keep going until closed
                if fragment.tag_type == HtmlTagType.OPEN_TAG:
                    for probe in fiter:
                        if isinstance(probe, HtmlTag) and \
                            probe.tag == tag and \
                            probe.tag_type == HtmlTagType.CLOSE_TAG:
                            break
            else:
                output = tagf(fragment)
                if output:
                    yield output
        else:
            text = region.htmlpage.fragment_data(fragment)
            text = remove_comments(text)
            text = textf(text)
            if text:
                yield text

def html(pageregion):
    """A page region is already html, so this is the identity function"""
    return pageregion

def contains_any_numbers(txt):
    """text that must contain at least one number
    >>> contains_any_numbers('foo')
    >>> contains_any_numbers('$67 at 15% discount')
    '$67 at 15% discount'
    """
    if _NUMBER_RE.search(txt) is not None:
        return txt

def contains_prices(txt):
    """text must contain a number that is not joined to text"""
    if _PRICE_NUMBER_RE.findall(txt) is not None:
        return txt

def contains_numbers(txt, count=1):
    """Must contain a certain amount of numbers
    
    >>> contains_numbers('foo', 2)
    >>> contains_numbers('this 1 has 2 numbers', 2)
    'this 1 has 2 numbers'
    """
    numbers = _NUMBER_RE.findall(txt)
    if len(numbers) == count:
        return txt

def extract_number(txt):
    """Extract a numeric value.
    
    This will fail if more than one numeric value is present.

    >>> extract_number('  45.3')
    '45.3'
    >>> extract_number('  45.3, 7')

    It will handle unescaped entities:
    >>> extract_number(u'&#163;129&#46;99')
    u'129.99'
    """
    txt = _NUMERIC_ENTITIES.sub(lambda m: unichr(int(m.groups()[0])), txt)
    numbers = _NUMBER_RE.findall(txt)
    if len(numbers) == 1:
        return numbers[0]

def extract_price(txt):
    """ 
    Extracts numbers making some price format specific assumptions

    >>> extract_price('asdf 234,234.45sdf ')
    '234234.45'
    >>> extract_price('234,23')
    '234.23'
    >>> extract_price('234,230')
    '234230'
    >>> extract_price('asdf 2234 sdf ')
    '2234'
    >>> extract_price('947')
    '947'
    >>> extract_price('adsfg')
    >>> extract_price('stained, linseed oil finish, clear glas doors')
    >>> extract_price('')
    >>> extract_price(u'&#163;129&#46;99')
    u'129.99'
    """
    txt = _NUMERIC_ENTITIES.sub(lambda m: unichr(int(m.groups()[0])), txt)
    m = _DECIMAL_RE.search(txt)
    if m:
        value = m.group(1)
        parts = _VALPARTS_RE.findall(value)
        decimalpart = parts.pop(-1)
        if decimalpart[0] == "," and len(decimalpart) <= 3:
            decimalpart = decimalpart.replace(",", ".")
        value = "".join(parts + [decimalpart]).replace(",", "") 
        return value
    
def url(txt):
    """convert text to a url
    
    this is quite conservative, since relative urls are supported
    """
    txt = txt.strip("\t\r\n '\"")
    if txt:
        return txt

def image_url(txt):
    """convert text to a url
    
    this is quite conservative, since relative urls are supported
    Example:

        >>> image_url('')

        >>> image_url('   ')

        >>> image_url(' \\n\\n  ')

        >>> image_url('foo-bar.jpg')
        ['foo-bar.jpg']
        >>> image_url('/images/main_logo12.gif')
        ['/images/main_logo12.gif']
        >>> image_url("http://www.image.com/image.jpg")
        ['http://www.image.com/image.jpg']
        >>> image_url("http://www.domain.com/path1/path2/path3/image.jpg")
        ['http://www.domain.com/path1/path2/path3/image.jpg']
        >>> image_url("/path1/path2/path3/image.jpg")
        ['/path1/path2/path3/image.jpg']
        >>> image_url("path1/path2/image.jpg")
        ['path1/path2/image.jpg']
        >>> image_url("background-image : url(http://www.site.com/path1/path2/image.jpg)")
        ['http://www.site.com/path1/path2/image.jpg']
        >>> image_url("background-image : url('http://www.site.com/path1/path2/image.jpg')")
        ['http://www.site.com/path1/path2/image.jpg']
        >>> image_url('background-image : url("http://www.site.com/path1/path2/image.jpg")')
        ['http://www.site.com/path1/path2/image.jpg']
        >>> image_url("background : url(http://www.site.com/path1/path2/image.jpg)")
        ['http://www.site.com/path1/path2/image.jpg']
        >>> image_url("background : url('http://www.site.com/path1/path2/image.jpg')")
        ['http://www.site.com/path1/path2/image.jpg']
        >>> image_url('background : url("http://www.site.com/path1/path2/image.jpg")')
        ['http://www.site.com/path1/path2/image.jpg']
        >>> image_url('/getimage.php?image=totalgardens/outbbq2_400.jpg&type=prod&resizeto=350')
        ['/getimage.php?image=totalgardens/outbbq2_400.jpg&type=prod&resizeto=350']
        >>> image_url('http://www.site.com/getimage.php?image=totalgardens/outbbq2_400.jpg&type=prod&resizeto=350')
        ['http://www.site.com/getimage.php?image=totalgardens/outbbq2_400.jpg&type=prod&resizeto=350']
        >>> image_url('http://s7d4.scene7.com/is/image/Kohler/jaa03267?hei=425&wid=457&op_usm=2,1,2,1&qlt=80')
        ['http://s7d4.scene7.com/is/image/Kohler/jaa03267?hei=425&wid=457&op_usm=2,1,2,1&qlt=80']
        >>> image_url('../image.aspx?thumb=true&amp;boxSize=175&amp;img=Unknoportrait[1].jpg')
        ['../image.aspx?thumb=true&boxSize=175&img=Unknoportrait%5B1%5D.jpg']
        >>> image_url('http://www.sundancecatalog.com/mgen/catalog/test.ms?args=%2245932|MERIDIAN+PENDANT|.jpg%22&is=336,336,0xffffff')
        ['http://www.sundancecatalog.com/mgen/catalog/test.ms?args=%2245932|MERIDIAN+PENDANT|.jpg%22&is=336,336,0xffffff']
        >>> image_url('http://www.site.com/image.php')
        ['http://www.site.com/image.php']
        >>> image_url('background-image:URL(http://s7d5.scene7.com/is/image/wasserstrom/165133?wid=227&hei=227&amp;defaultImage=noimage_wasserstrom)')
        ['http://s7d5.scene7.com/is/image/wasserstrom/165133?wid=227&hei=227&defaultImage=noimage_wasserstrom']

    """
    imgurl = extract_image_url(txt)
    return [safe_url_string(remove_entities(url(imgurl)))] if imgurl else None

def extract_image_url(txt):
    txt = url(txt)
    imgurl = None
    if txt:
        # check if the text is style content
        m = _CSS_IMAGERE.search(txt)
        txt = m.groups()[0] if m else txt
        parsed = urlparse.urlparse(txt)
        path = None
        m = _IMAGE_PATH_RE.search(parsed.path)
        if m:
            path = m.group()
        elif parsed.query:
            m = _GENERIC_PATH_RE.search(parsed.path)
            if m:
                path = m.group()
        if path is not None:
            parsed = list(parsed)
            parsed[2] = path
            imgurl = urlparse.urlunparse(parsed)
        if not imgurl:
            imgurl = txt
    return imgurl

########NEW FILE########
__FILENAME__ = htmlpage
"""
htmlpage

Container objects for representing html pages and their parts in the IBL
system. This encapsulates page related information and prevents parsing
multiple times.
"""
import re, hashlib, urllib2
from copy import deepcopy
from w3lib.encoding import html_to_unicode

def url_to_page(url, encoding=None, default_encoding='utf-8'):
    """Fetch a URL, using python urllib2, and return an HtmlPage object.

    The `url` may be a string, or a `urllib2.Request` object. The `encoding`
    argument can be used to force the interpretation of the page encoding.

    Redirects are followed, and the `url` property of the returned HtmlPage object
    is the url of the final page redirected to.

    If the encoding of the page is known, it can be passed as a keyword argument. If
    unspecified, the encoding is guessed using `w3lib.encoding.html_to_unicode`. 
    `default_encoding` is used if the encoding cannot be determined.
    """
    fh = urllib2.urlopen(url)
    info = fh.info()
    body_str = fh.read()
    # guess content encoding if not specified
    if encoding is None:
        content_type_header = info.getheader("content-encoding")
        encoding, body = html_to_unicode(content_type_header, body_str, 
                default_encoding=default_encoding)
    else:
        body = body_str.decode(encoding)
    return HtmlPage(fh.geturl(), headers=info.dict, body=body, encoding=encoding)

def dict_to_page(jsonpage, body_key='body'):
    """Create an HtmlPage object from a dict object.

    `body_key` is the key where the page body can be found. This is used
    sometimes when we want to store multiple version of the body (annotated and
    original) into the same dict
    """
    url = jsonpage['url']
    headers = jsonpage.get('headers')
    body = jsonpage[body_key]
    page_id = jsonpage.get('page_id')
    encoding = jsonpage.get('encoding', 'utf-8')
    return HtmlPage(url, headers, body, page_id, encoding)

def page_to_dict(page, body_key='body'):
    """Create a dict from the given HtmlPage

    `body_key` indicates what key to store the body into. See `dict_to_page`
    for more info.
    """
    return {
        'url': page.url,
        'headers': page.headers,
        body_key: page.body,
        'page_id': page.page_id,
        'encoding': page.encoding,
    }

class HtmlPage(object):
    """HtmlPage

    This is a parsed HTML page. It contains the page headers, url, raw body and parsed 
    body.

    The parsed body is a list of HtmlDataFragment objects.

    The encoding argument is the original page encoding. This isn't used by the
    core extraction code, but it may be used by some extractors to translate
    entities or encoding urls.
    """
    def __init__(self, url=None, headers=None, body=None, page_id=None, encoding='utf-8'):
        assert isinstance(body, unicode), "unicode expected, got: %s" % type(body).__name__
        self.headers = headers or {}
        self.body = body
        self.url = url or u''
        self.encoding = encoding
        if page_id is None and url:
            self.page_id = hashlib.sha1(url).hexdigest()
        else:
            self.page_id = page_id 
    
    def _set_body(self, body):
        self._body = body
        self.parsed_body = list(parse_html(body))
        
    body = property(lambda x: x._body, _set_body, doc="raw html for the page")
    
    def subregion(self, start=0, end=None):
        """HtmlPageRegion constructed from the start and end index (inclusive)
        into the parsed page
        """
        return HtmlPageParsedRegion(self, start, end)

    def fragment_data(self, data_fragment):
        """portion of the body corresponding to the HtmlDataFragment"""
        return self.body[data_fragment.start:data_fragment.end]

class TextPage(HtmlPage):
    """An HtmlPage with one unique HtmlDataFragment, needed to have a
    convenient text with same interface as html page but avoiding unnecesary
    reparsing"""
    def _set_body(self, text): 
        self._body = text
        self.parsed_body = [HtmlDataFragment(0, len(self._body), True)]
    body = property(lambda x: x._body, _set_body, doc="raw text for the page")

class HtmlPageRegion(unicode):
    """A Region of an HtmlPage that has been extracted
    """
    def __new__(cls, htmlpage, data):
        return unicode.__new__(cls, data)

    def __init__(self, htmlpage, data):
        """Construct a new HtmlPageRegion object.

        htmlpage is the original page and data is the raw html
        """
        self.htmlpage = htmlpage
 
    @property
    def text_content(self):
        return self
        
class HtmlPageParsedRegion(HtmlPageRegion):
    """A region of an HtmlPage that has been extracted

    This has a parsed_fragments property that contains the parsed html 
    fragments contained within this region
    """
    def __new__(cls, htmlpage, start_index, end_index):
        text = htmlpage.body
        if text:
            text_start = htmlpage.parsed_body[start_index].start
            text_end = htmlpage.parsed_body[end_index or -1].end
            text = htmlpage.body[text_start:text_end]
        return HtmlPageRegion.__new__(cls, htmlpage, text)

    def __init__(self, htmlpage, start_index, end_index):
        self.htmlpage = htmlpage
        self.start_index = start_index
        self.end_index = end_index

    def __copy__(self, page=None):
        page = page or self.htmlpage
        obj = HtmlPageParsedRegion.__new__(HtmlPageParsedRegion, page, self.start_index, self.end_index)
        HtmlPageParsedRegion.__init__(obj, page, self.start_index, self.end_index)
        return obj

    def __deepcopy__(self, memo):
        page = deepcopy(self.htmlpage)
        return self.__copy__(page)

    @property
    def parsed_fragments(self):
        """HtmlDataFragment or HtmlTag objects for this parsed region"""
        end = self.end_index + 1 if self.end_index is not None else None
        return self.htmlpage.parsed_body[self.start_index:end]

    @property
    def text_content(self):
        """Text content of this parsed region"""
        text_all = u" ".join(self.htmlpage.body[_element.start:_element.end] \
                for _element in self.parsed_fragments if \
                not isinstance(_element, HtmlTag) and _element.is_text_content)
        return TextPage(self.htmlpage.url, self.htmlpage.headers, \
                text_all, encoding=self.htmlpage.encoding).subregion()


class HtmlTagType(object):
    OPEN_TAG = 1
    CLOSE_TAG = 2 
    UNPAIRED_TAG = 3

class HtmlDataFragment(object):
    __slots__ = ('start', 'end', 'is_text_content')
    
    def __init__(self, start, end, is_text_content=False):
        self.start = start
        self.end = end
        self.is_text_content = is_text_content
        
    def __str__(self):
        return "<HtmlDataFragment [%s:%s] is_text_content: %s>" % (self.start, self.end, self.is_text_content)

    def __repr__(self):
        return str(self)
    
class HtmlTag(HtmlDataFragment):
    __slots__ = ('tag_type', 'tag', 'attributes')

    def __init__(self, tag_type, tag, attributes, start, end):
        HtmlDataFragment.__init__(self, start, end)
        self.tag_type = tag_type
        self.tag = tag
        self.attributes = attributes

    def __str__(self):
        return "<HtmlTag tag='%s' attributes={%s} type='%d' [%s:%s]>" % (self.tag, ', '.join(sorted\
                (["%s: %s" % (k, repr(v)) for k, v in self.attributes.items()])), self.tag_type, self.start, self.end)
    
    def __repr__(self):
        return str(self)

_ATTR = "((?:[^=/<>\s]|/(?!>))+)(?:\s*=(?:\s*\"(.*?)\"|\s*'(.*?)'|([^>\s]+))?)?"
_TAG = "<(\/?)(\w+(?::\w+)?)((?:\s*" + _ATTR + ")+\s*|\s*)(\/?)>?"
_DOCTYPE = r"<!DOCTYPE.*?>"
_SCRIPT = "(<script.*?>)(.*?)(</script.*?>)"
_COMMENT = "(<!--.*?-->|<\?.+?>)"

_ATTR_REGEXP = re.compile(_ATTR, re.I | re.DOTALL)
_HTML_REGEXP = re.compile("%s|%s|%s" % (_COMMENT, _SCRIPT, _TAG), re.I | re.DOTALL)
_DOCTYPE_REGEXP = re.compile("(?:%s)" % _DOCTYPE)
_COMMENT_REGEXP = re.compile(_COMMENT, re.DOTALL)

def parse_html(text):
    """Higher level html parser. Calls lower level parsers and joins sucesive
    HtmlDataFragment elements in a single one.
    """
    # If have doctype remove it.
    start_pos = 0
    match = _DOCTYPE_REGEXP.match(text)
    if match:
        start_pos = match.end()
    prev_end = start_pos
    for match in _HTML_REGEXP.finditer(text, start_pos):
        start = match.start()
        end = match.end()
            
        if start > prev_end:
            yield HtmlDataFragment(prev_end, start, True)

        if match.groups()[0] is not None: # comment
            yield HtmlDataFragment(start, end)
        elif match.groups()[1] is not None: # <script>...</script>
            for e in _parse_script(match):
                yield e
        else: # tag
            yield _parse_tag(match)
        prev_end = end
    textlen = len(text)
    if prev_end < textlen:
        yield HtmlDataFragment(prev_end, textlen, True)

def _parse_script(match):
    """parse a <script>...</script> region matched by _HTML_REGEXP"""
    open_text, content, close_text = match.groups()[1:4]

    open_tag = _parse_tag(_HTML_REGEXP.match(open_text))
    open_tag.start = match.start()
    open_tag.end = match.start() + len(open_text)

    close_tag = _parse_tag(_HTML_REGEXP.match(close_text))
    close_tag.start = match.end() - len(close_text)
    close_tag.end = match.end()
    
    yield open_tag
    if open_tag.end < close_tag.start:
        start_pos = 0
        for m in _COMMENT_REGEXP.finditer(content):
            if m.start() > start_pos:
                yield HtmlDataFragment(open_tag.end + start_pos, open_tag.end + m.start())
            yield HtmlDataFragment(open_tag.end + m.start(), open_tag.end + m.end())
            start_pos = m.end()
        if open_tag.end + start_pos < close_tag.start:
            yield HtmlDataFragment(open_tag.end + start_pos, close_tag.start)
    yield close_tag

def _parse_tag(match):
    """
    parse a tag matched by _HTML_REGEXP
    """
    data = match.groups()
    closing, tag, attr_text = data[4:7]
    # if tag is None then the match is a comment
    if tag is not None:
        unpaired = data[-1]
        if closing:
            tag_type = HtmlTagType.CLOSE_TAG
        elif unpaired:
            tag_type = HtmlTagType.UNPAIRED_TAG
        else:
            tag_type = HtmlTagType.OPEN_TAG
        attributes = []
        for attr_match in _ATTR_REGEXP.findall(attr_text):
            name = attr_match[0].lower()
            values = [v for v in attr_match[1:] if v]
            attributes.append((name, values[0] if values else None))
        return HtmlTag(tag_type, tag.lower(), dict(attributes), match.start(), match.end())

########NEW FILE########
__FILENAME__ = template
import copy
import json

from scrapely.htmlpage import HtmlTag, HtmlTagType

class AnnotationError(Exception):
    pass

class FragmentNotFound(AnnotationError):
    pass

class FragmentAlreadyAnnotated(AnnotationError):
    pass
    
class TemplateMaker(object):

    def __init__(self, htmlpage):
        self.htmlpage = copy.copy(htmlpage)

    def annotate(self, field, score_func, best_match=True):
        """Annotate a field.
        
        ``score_func`` is a callable that receives two arguments: (fragment,
        htmlpage) and returns a relevancy score (float) indicating how relevant
        is the fragment. 0 means the fragment is irrelevant. Higher scores
        means the fragment is more relevant. Otherwise, the closest opening tag
        (to the left) is annotated with the given attribute.

        If ``best_match`` is ``True``, only the best fragment is annotated.
        Otherwise, all fragments (with a positive relevancy) are annotated.

        """
        indexes = self.select(score_func)
        if not indexes:
            raise FragmentNotFound("Fragment not found annotating %r using: %s" % 
                (field, score_func))
        if best_match:
            del indexes[1:]
        for i in indexes:
            self.annotate_fragment(i, field)

    def select(self, score_func):
        """Return the indexes of fragment where score_func returns a positive
        value, reversely sorted by that value"""
        htmlpage = copy.copy(self.htmlpage)
        matches = []
        for i, fragment in enumerate(htmlpage.parsed_body):
            score = score_func(fragment, htmlpage)
            if score:
                matches.append((score, i))
        matches.sort(reverse=True)
        return [x[1] for x in matches]

    def selected_data(self, index):
        """Return the data that would be annotated from the given fragment
        index
        """
        start_tag, end_tag = _enclosing_tags(self.htmlpage, index)
        return self.htmlpage.body[start_tag.start:end_tag.end]

    def annotations(self):
        """Return all annotations contained in the template as a list of tuples
        (annotation, index)
        """
        anlist = []
        for i, f in enumerate(self.htmlpage.parsed_body):
            if isinstance(f, HtmlTag) and f.tag_type == HtmlTagType.OPEN_TAG:
                at = f.attributes.get('data-scrapy-annotate')
                if at:
                    an = json.loads(at.replace('&quot;', '"'))
                    anlist.append((an, i))
        return anlist

    def annotate_fragment(self, index, field):
        for f in self.htmlpage.parsed_body[index::-1]:
            if isinstance(f, HtmlTag) and f.tag_type == HtmlTagType.OPEN_TAG:
                if 'data-scrapy-annotate' in f.attributes:
                    fstr = self.htmlpage.fragment_data(f)
                    raise FragmentAlreadyAnnotated("Fragment already annotated: %s" % fstr)
                d = {'annotations': {'content': field}}
                a = ' data-scrapy-annotate="%s"' % json.dumps(d).replace('"', '&quot;')
                p = self.htmlpage
                p.body = p.body[:f.end-1] + a + p.body[f.end-1:]
                return True
        return False

    def get_template(self):
        """Return the generated template as a HtmlPage object"""
        return self.htmlpage


def best_match(text):
    """Function to use in TemplateMaker.annotate()"""
    def func(fragment, page):
        fdata = page.fragment_data(fragment).strip()
        if text in fdata:
            return float(len(text)) / len(fdata) - (1e-6 * fragment.start)
        else:
            return 0.0
    return func

def _enclosing_tags(htmlpage, index):
    f = htmlpage.parsed_body[index]
    if isinstance(f, HtmlTag) and f.tag_type == HtmlTagType.UNPAIRED_TAG:
        return f, f
    start_tag = end_tag = None
    for f in htmlpage.parsed_body[index::-1]:
        if isinstance(f, HtmlTag) and f.tag_type == HtmlTagType.OPEN_TAG:
            start_tag = f
            break
    if not start_tag:
        raise FragmentNotFound("Unable to find start tag from index %d" % index)
    tcount = 1
    start_index = htmlpage.parsed_body.index(start_tag)
    for f in htmlpage.parsed_body[start_index+1:]:
        if isinstance(f, HtmlTag) and f.tag == start_tag.tag:
            if f.tag_type == HtmlTagType.OPEN_TAG:
                tcount += 1
            if f.tag_type == HtmlTagType.CLOSE_TAG:
                tcount -= 1
                if not tcount:
                    end_tag = f
                    break
    if not end_tag or htmlpage.parsed_body.index(end_tag) < index:
        # end tag not found or tag found is not enclosing 
        return f, f
    return start_tag, end_tag

########NEW FILE########
__FILENAME__ = test_extraction
"""
tests for page parsing

Page parsing effectiveness is measured through the evaluation system. These
tests should focus on specific bits of functionality work correctly.
"""
from unittest import TestCase
from nose_parameterized import parameterized

from scrapely.htmlpage import HtmlPage
from scrapely.descriptor import (FieldDescriptor as A, 
        ItemDescriptor)
from scrapely.extractors import (contains_any_numbers,
        image_url, html, notags)
from scrapely.extraction import InstanceBasedLearningExtractor

# simple page with all features

ANNOTATED_PAGE1 = u"""
<html>
<h1>COMPANY - <ins 
    data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;generated&quot;: true, 
    &quot;annotations&quot;: {&quot;content&quot;: &quot;title&quot;}}" 
>Item Title</ins></h1>
<p>introduction</p>
<div>
<img data-scrapy-annotate="{&quot;variant&quot;: 0, 
    &quot;annotations&quot;: {&quot;src&quot;: &quot;image_url&quot;}}"
    src="img.jpg"/>
<p data-scrapy-annotate="{&quot;variant&quot;: 0, 
    &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">
This is such a nice item<br/> Everybody likes it.
</p>
<br/>
</div>
<p>click here for other items</p>
</html>
"""

EXTRACT_PAGE1 = u"""
<html>
<h1>Scrapy - Nice Product</h1>
<p>introduction</p>
<div>
<img src="nice_product.jpg" alt="a nice product image"/>
<p>wonderful product</p>
<br/>
</div>
</html>
"""

# single tag with multiple items extracted
ANNOTATED_PAGE2 = u"""
<a href="http://example.com/xxx" title="xxx"
    data-scrapy-annotate="{&quot;variant&quot;: 0, 
    &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;, 
        &quot;href&quot;: &quot;image_url&quot;, &quot;title&quot;: &quot;name&quot;}}"
>xx</a>
xxx
</a>
"""
EXTRACT_PAGE2 = u"""<a href='http://example.com/product1.jpg' 
    title="product 1">product 1 is great</a>"""

# matching must match the second attribute in order to find the first
ANNOTATED_PAGE3 = u"""
<p data-scrapy-annotate="{&quot;variant&quot;: 0, 
    &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">xx</p>
<div data-scrapy-annotate="{&quot;variant&quot;: 0, 
    &quot;annotations&quot;: {&quot;content&quot;: &quot;delivery&quot;}}">xx</div>
"""
EXTRACT_PAGE3 = u"""
<p>description</p>
<div>delivery</div>
<p>this is not the description</p>
"""

# test inferring repeated elements
ANNOTATED_PAGE4 = u"""
<ul>
<li data-scrapy-annotate="{&quot;variant&quot;: 0, 
    &quot;annotations&quot;: {&quot;content&quot;: &quot;features&quot;}}">feature1</li>
<li data-scrapy-annotate="{&quot;variant&quot;: 0, 
    &quot;annotations&quot;: {&quot;content&quot;: &quot;features&quot;}}">feature2</li>
</ul>
"""

EXTRACT_PAGE4 = u"""
<ul>
<li>feature1</li> ignore this
<li>feature2</li>
<li>feature3</li>
</ul>
"""

# test variant handling with identical repeated variant
ANNOTATED_PAGE5 =  u"""
<p data-scrapy-annotate="{&quot;annotations&quot;:
    {&quot;content&quot;: &quot;description&quot;}}">description</p>
<table>
<tr>
<td data-scrapy-annotate="{&quot;variant&quot;: 1, &quot;annotations&quot;: 
    {&quot;content&quot;: &quot;colour&quot;}}" >colour 1</td>
<td data-scrapy-annotate="{&quot;variant&quot;: 1, &quot;annotations&quot;: 
    {&quot;content&quot;: &quot;price&quot;}}" >price 1</td>
</tr>
<tr>
<td data-scrapy-annotate="{&quot;variant&quot;: 2, &quot;annotations&quot;: 
    {&quot;content&quot;: &quot;colour&quot;}}" >colour 2</td>
<td data-scrapy-annotate="{&quot;variant&quot;: 2, &quot;annotations&quot;: 
    {&quot;content&quot;: &quot;price&quot;}}" >price 2</td>
</tr>
</table>
"""

ANNOTATED_PAGE5a =  u"""
<p data-scrapy-annotate="{&quot;annotations&quot;:
    {&quot;content&quot;: &quot;description&quot;}}">description</p>
<table>
<tr>
<td data-scrapy-annotate="{&quot;variant&quot;: 1, &quot;annotations&quot;: 
    {&quot;content&quot;: &quot;colour&quot;}}" >colour 1</td>
<td data-scrapy-annotate="{&quot;variant&quot;: 1, &quot;annotations&quot;: 
    {&quot;content&quot;: &quot;price&quot;}, &quot;required&quot;: [&quot;price&quot;]}" >price 1</td>
</tr>
<tr>
<td data-scrapy-annotate="{&quot;variant&quot;: 2, &quot;annotations&quot;: 
    {&quot;content&quot;: &quot;colour&quot;}}" >colour 2</td>
<td data-scrapy-annotate="{&quot;variant&quot;: 2, &quot;annotations&quot;: 
    {&quot;content&quot;: &quot;price&quot;}, &quot;required&quot;: [&quot;price&quot;]}" >price 2</td>
</tr>
</table>
"""

EXTRACT_PAGE5 = u"""
<p>description</p>
<table>
<tr>
<td>colour 1</td>
<td>price 1</td>
</tr>
<tr>
<td>colour 2</td>
<td>price 2</td>
</tr>
<tr>
<td>colour 3</td>
<td>price 3</td>
</tr>
</table>
"""

# test variant handling with irregular structure and some non-variant
# attributes
ANNOTATED_PAGE6 =  u"""
<p data-scrapy-annotate="{&quot;annotations&quot;:
    {&quot;content&quot;: &quot;description&quot;}}">description</p>
<p data-scrapy-annotate="{&quot;variant&quot;: 1, &quot;annotations&quot;: 
    {&quot;content&quot;: &quot;name&quot;}}">name 1</p>
<div data-scrapy-annotate="{&quot;variant&quot;: 3, &quot;annotations&quot;: 
    {&quot;content&quot;: &quot;name&quot;}}" >name 3</div>
<p data-scrapy-annotate="{&quot;variant&quot;: 2, &quot;annotations&quot;: 
    {&quot;content&quot;: &quot;name&quot;}}" >name 2</p>
"""
EXTRACT_PAGE6 =  u"""
<p>description</p>
<p>name 1</p>
<div>name 3</div>
<p>name 2</p>
"""

# test repeating variants at the table column level
ANNOTATED_PAGE7 =  u"""
<table>
<tr>
<td data-scrapy-annotate="{&quot;variant&quot;: 1, &quot;annotations&quot;: 
    {&quot;content&quot;: &quot;colour&quot;}}" >colour 1</td>
<td data-scrapy-annotate="{&quot;variant&quot;: 2, &quot;annotations&quot;: 
    {&quot;content&quot;: &quot;colour&quot;}}" >colour 2</td>
</tr>
<tr>
<td data-scrapy-annotate="{&quot;variant&quot;: 2, &quot;annotations&quot;: 
    {&quot;content&quot;: &quot;price&quot;}}" >price 1</td>
<td data-scrapy-annotate="{&quot;variant&quot;: 2, &quot;annotations&quot;: 
    {&quot;content&quot;: &quot;price&quot;}}" >price 2</td>
</tr>
</table>
"""

EXTRACT_PAGE7 = u"""
<table>
<tr>
<td>colour 1</td>
<td>colour 2</td>
<td>colour 3</td>
</tr>
<tr>
<td>price 1</td>
<td>price 2</td>
<td>price 3</td>
</tr>
</table>
"""

ANNOTATED_PAGE8 = u"""
<html><body>
<h1>A product</h1>
<div data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">
<p>XXXX XXXX xxxxx</p>
<div data-scrapy-ignore="true">
<img scr="image.jpg" /><br/><a link="back.html">Click here to go back</a>
</div>
</div>
<div data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}">
10.00<p data-scrapy-ignore="true"> 13</p>
</div>
</body></html>
"""

EXTRACT_PAGE8 = u"""
<html><body>
<h1>A product</h1>
<div>
<p>A very nice product for all intelligent people</p>
<div>
<img scr="image.jpg" /><br/><a link="back.html">Click here to go back</a>
</div>
</div>
<div>
12.00<p> ID 15</p>
(VAT exc.)</div>
</body></html>
"""

ANNOTATED_PAGE9 = ANNOTATED_PAGE8

EXTRACT_PAGE9 = u"""
<html><body>
<img src="logo.jpg" />
<h1>A product</h1>
<div>
<p>A very nice product for all intelligent people</p>
<div>
<img scr="image.jpg" /><br/><a link="back.html">Click here to go back</a>
</div>
</div>
<div>
12.00<p> ID 16</p>
(VAT exc.)</div>
</body></html>
"""

ANNOTATED_PAGE11 = u"""
<html><body>
<p data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">
<ins data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;generated&quot;: true,
    &quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">
SL342
</ins>
<br/>
Nice product for ladies
<br/><ins data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;generated&quot;: true,
     &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}">
&pound;85.00
</ins>
</p>
<ins data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;generated&quot;: true,
     &quot;annotations&quot;: {&quot;content&quot;: &quot;price_before_discount&quot;}}">
&pound;100.00
</ins>
</body></html>
"""

EXTRACT_PAGE11 = u"""
<html><body>
<p>
SL342
<br/>
Nice product for ladies
<br/>
&pound;85.00
</p>
&pound;100.00
</body></html>
"""

ANNOTATED_PAGE12 = u"""
<html><body>
<h1 data-scrapy-ignore-beneath="true">A product</h1>
<div data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">
<p>XXXX XXXX xxxxx</p>
<div data-scrapy-ignore-beneath="true">
<img scr="image.jpg" /><br/><a link="back.html">Click here to go back</a>
</div>
<div>
10.00<p> 13</p>
</div>
</div>
</body></html>
"""

EXTRACT_PAGE12a = u"""
<html><body>
<h1>A product</h1>
<div>
<p>A very nice product for all intelligent people</p>
<div>
<img scr="image.jpg" /><br/><a link="back.html">Click here to go back</a>
</div>
<div>
12.00<p> ID 15</p>
(VAT exc.)
</div></div>
</body></html>
"""

EXTRACT_PAGE12b = u"""
<html><body>
<h1>A product</h1>
<div>
<p>A very nice product for all intelligent people</p>
<div>
<img scr="image.jpg" /><br/><a link="back.html">Click here to go back</a>
</div>
<div>
12.00<p> ID 15</p>
(VAT exc.)
</div>
<ul>
Features
<li>Feature A</li>
<li>Feature B</li>
</ul>
</div>
</body></html>
"""

# Ex1: nested annotation with token sequence replica outside exterior annotation
# and a possible sequence pattern can be extracted only with
# correct handling of nested annotations
ANNOTATED_PAGE13a = u"""
<html><body>
<span>
<p data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">
<hr/>
<h3 data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">A product</h3>
<b data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}">$50.00</b>
This product is excelent. Buy it!
</p>
</span>
<span>
<p>
<h3>See other products:</h3>
<b>Product b</b>
</p>
</span>
<hr/>
</body></html>
"""

EXTRACT_PAGE13a = u"""
<html><body>
<span>
<p>
<h3>A product</h3>
<b>$50.00</b>
This product is excelent. Buy it!
<hr/>
</p>
</span>
<span>
<p>
<h3>See other products:</h3>
<b>Product B</b>
</p>
</span>
</body></html>
"""

# Ex2: annotation with token sequence replica inside a previous nested annotation
# and a possible sequence pattern can be extracted only with
# correct handling of nested annotations
ANNOTATED_PAGE13b = u"""
<html><body>
<span>
<p data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">
<h3 data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">A product</h3>
<b>Previous price: $50.00</b>
This product is excelent. Buy it!
</p>
</span>
<span>
<p>
<h3>Save 10%!!</h3>
<b data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}">$45.00</b>
</p>
</span>
</body></html>
"""

EXTRACT_PAGE13b = u"""
<html><body>
<span>
<p>
<h3>A product</h3>
<b>$50.00</b>
This product is excelent. Buy it!
</p>
</span>
<span>
<hr/>
<p>
<h3>Save 10%!!</h3>
<b>$45.00</b>
</p>
</span>
<hr/>
</body></html>
"""

ANNOTATED_PAGE14 = u"""
<html><body>
<b data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}"></b>
<p data-scrapy-ignore="true"></p>
</body></html>
"""

EXTRACT_PAGE14 = u"""
<html><body>
</body></html>
"""

ANNOTATED_PAGE15 = u"""
<html><body>
<div data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;short_description&quot;}}">Short
<div data-scrapy-ignore="true" data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;site_id&quot;}}">892342</div>
</div>
<hr/>
<p data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">Description
<b data-scrapy-ignore="true" data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}">90.00</b>
</p>
</body></html>
"""

EXTRACT_PAGE15 = u"""
<html><body>
<hr/>
<p>Description
<b>80.00</b>
</p>
</body></html>
"""

ANNOTATED_PAGE16 = u"""
<html><body>
<div data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">
Description
<p data-scrapy-ignore="true" data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">
name</p>
<p data-scrapy-ignore="true" data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}">
80.00</p>
</div>
</body></html>
"""

EXTRACT_PAGE16 = u"""
<html><body>
<p>product name</p>
<p>90.00</p>
</body></html>
"""

ANNOTATED_PAGE17 = u"""
<html><body>
<span>
<p data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">
This product is excelent. Buy it!
</p>
</span>
<table></table>
<img src="line.jpg" data-scrapy-ignore-beneath="true"/>
<span>
<h3>See other products:</h3>
<p>Product b
</p>
</span>
</body></html>
"""

EXTRACT_PAGE17 = u"""
<html><body>
<span>
<p>
This product is excelent. Buy it!
</p>
</span>
<img src="line.jpg"/>
<span>
<h3>See other products:</h3>
<p>Product B
</p>
</span>
</body></html>
"""

ANNOTATED_PAGE18 = u"""
<html><body>
<div data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">
<ins data-scrapy-ignore="true" data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;generated&quot;: true, &quot;annotations&quot;: {&quot;content&quot;: &quot;site_id&quot;}}">Item Id</ins>
<br>
Description
</div>
</body></html>
"""

EXTRACT_PAGE18 = u"""
<html><body>
<div>
Item Id
<br>
Description
</div>
</body></html>
"""

ANNOTATED_PAGE19 = u"""
<html><body>
<div>
<p data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">Product name</p>
<p data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}">60.00</p>
<img data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;src&quot;: &quot;image_urls&quot;}}" src="image.jpg" />
<p data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;required&quot;: [&quot;description&quot;], &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">description</p>
</div>
</body></html>
"""

EXTRACT_PAGE19a = u"""
<html><body>
<div>
<p>Product name</p>
<p>60.00</p>
<img src="http://example.com/image.jpg" />
<p>description</p>
</div>
</body></html>
"""

EXTRACT_PAGE19b = u"""
<html><body>
<div>
<p>Range</p>
<p>from 20.00</p>
<img src="http://example.com/image1.jpg" />
<p>
<br/>
</div>
</body></html>
"""

ANNOTATED_PAGE20 = u"""
<html><body>
<h1>Product Name</h1>
<img src="product.jpg">
<br/>
<span><ins data-scrapy-annotate="{&quot;variant&quot;: 1, &quot;generated&quot;: true,                                              
&quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">Twin</ins>:</span> $<ins data-scrapy-annotate="{&quot;variant&quot;: 1, &quot;generated&quot;: true,
&quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}">270</ins> - November 2010<br/>
<span><ins data-scrapy-annotate="{&quot;variant&quot;: 2, &quot;generated&quot;: true,
&quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">Queen</ins>:</span> $<ins data-scrapy-annotate="{&quot;variant&quot;: 2, &quot;generated&quot;: true,
&quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}">330</ins> - In stock<br/>
<br/>
</body></html>
"""

EXTRACT_PAGE20 = u"""
<html><body>
<h1>Product Name</h1>
<img src="product.jpg">
<br/>
<span>Twin:</span> $270 - November 2010<br/>
<span>Queen:</span> $330 - Movember 2010<br/>
<br/>
</body></html>
"""

ANNOTATED_PAGE21 = u"""
<html><body>                                                                                                                                                                       
<img src="image.jpg" data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;src&quot;: &quot;image_urls&quot;}}">
<p>
<table>

<tr><td><img src="swatch1.jpg" data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 1, &quot;annotations&quot;: {&quot;src&quot;: &quot;swatches&quot;}}"></td></tr>

<tr><td><img src="swatch2.jpg"></td></tr>

<tr><td><img src="swatch3.jpg"></td></tr>

<tr><td><img src="swatch4.jpg" data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 2, &quot;annotations&quot;: {&quot;src&quot;: &quot;swatches&quot;}}"></td></tr>

</table>

<div data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;category&quot;}}">tables</div>

</body></html>
"""

EXTRACT_PAGE21 = u"""
<html><body>
<img src="image.jpg">
<p>
<table>

<tr><td><img src="swatch1.jpg"></td></tr>

<tr><td><img src="swatch2.jpg"></td></tr>

<tr><td><img src="swatch3.jpg"></td></tr>

<tr><td><img src="swatch4.jpg"></td></tr>

</table>

<div>chairs</div>
</body></html>
"""

ANNOTATED_PAGE22 = u"""
<html><body>                                                                                                                                                                       
<img src="image.jpg" data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;src&quot;: &quot;image_urls&quot;}}">
<p>
<table>

<tr><td>
<p data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 1, &quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">product 1</p>
<b data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 1, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}">$67</b>
<img src="swatch1.jpg" data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 1, &quot;annotations&quot;: {&quot;src&quot;: &quot;swatches&quot;}}">
</td></tr>

<tr><td>
<p>product 2</p>
<b>$70</b>
<img src="swatch2.jpg">
</td></tr>

<tr><td>
<p>product 3</p>
<b>$73</b>
<img src="swatch3.jpg">
</td></tr>

<tr><td>
<p data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 2, &quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">product 4</p>
<b data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 2, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}">$80</b>
<img src="swatch4.jpg" data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 2, &quot;annotations&quot;: {&quot;src&quot;: &quot;swatches&quot;}}">
</td></tr>

</table>

<div data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;category&quot;}}">tables</div>

</body></html>
"""

EXTRACT_PAGE22 = u"""
<html><body>
<img src="image.jpg">
<p>
<table>

<tr><td>
<p>product 1</p>
<b>$70</b>
<img src="swatch1.jpg">
</td></tr>

<tr><td>
<p>product 2</p>
<b>$80</b>
<img src="swatch2.jpg">
</td></tr>

<tr><td>
<p>product 3</p>
<b>$90</b>
<img src="swatch3.jpg">
</td></tr>

<tr><td>
<p>product 4</p>
<b>$100</b>
<img src="swatch4.jpg">
</td></tr>

</table>

<div>chairs</div>
</body></html>
"""

ANNOTATED_PAGE23 = u"""
<html><body>
<h4>Product</h4>
<table>
<tr><td>
<p data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 1, &quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">Variant 1<b data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 1, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}" data-scrapy-ignore="true">560</b></p>
</td></tr>
<tr><td>
<p>Variant 2<b>570</b></p>
</td></tr>
<tr><td>
<p data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 2, &quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">Variant 3<b data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 2, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}" data-scrapy-ignore="true">580</b></p>
</td></tr>
</table>
</body></html>
"""

EXTRACT_PAGE23 = u"""
<html><body>
<h4>Product</h4>
<table>
<tr><td>
<p>Variant 1<b>300</b></p>
</td></tr>
<tr><td>
<p>Variant 2<b>320</b></p>
</td></tr>
<tr><td>
<p>Variant 3<b>340</b></p>
</td></tr>
</table>
</body></html>
"""

ANNOTATED_PAGE24 = u"""
<html><body>
<h1 data-scrapy-ignore-beneath="true">A product</h1>
<div data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">
<p>XXXX XXXX xxxxx</p>
<div data-scrapy-ignore-beneath="true">
<img scr="image.jpg" /><br/><a link="back.html">Click here to go back</a>
</div>
<p data-scrapy-ignore-beneath="true">Important news!!</p>
<div>
10.00<p> 13</p>
</div>
</div>
</body></html>
"""

EXTRACT_PAGE24 = u"""
<html><body>
<h1>A product</h1>
<div>
<p>A very nice product for all intelligent people</p>
<div>
<img scr="image.jpg" /><br/><a link="back.html">Click here to go back</a>
</div>
<p>Important news!!</p>
<div>
12.00<p> ID 15</p>
(VAT exc.)
</div></div>
</body></html>
"""

ANNOTATED_PAGE25 = u"""
<span>
<br>
<input type="radio" name="size" checked value='44'>
<ins data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;generated&quot;: true, 
&quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">"Large"</ins>
<br>
<input type="radio" name="size" checked value='45'>
"X Large"
<br>
<input type="radio" name="size" checked value='46'>
<ins data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;generated&quot;: true, 
&quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">"XX Large"</ins>
</span>
"""


EXTRACT_PAGE25 = u"""
<span>
<br>
<input type="radio" name="size" checked value='44'>
"Large"
<br>
<input type="radio" name="size" checked value='45'>
"X Large"
<br>
<input type="radio" name="size" checked value='46'>
"XX Large"
</span>
"""

ANNOTATED_PAGE26 = u"""
<span>
<br>
<input type="radio" name="size" checked value='44'>
<ins data-scrapy-annotate="{&quot;variant&quot;: 1, &quot;generated&quot;: true, 
&quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">"Large"</ins>
<br>
<input type="radio" name="size" checked value='45'>
"X Large"
<br>
<input type="radio" name="size" checked value='46'>
<ins data-scrapy-annotate="{&quot;variant&quot;: 2, &quot;generated&quot;: true, 
&quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">"XX Large"</ins>
</span>
"""

EXTRACT_PAGE26 = u"""
<span>
<br>
<input type="radio" name="size" checked value='44'>
"Large"
<br>
<input type="radio" name="size" checked value='45'>
"X Large"
<br>
<input type="radio" name="size" checked value='46'>
"XX Large"
</span>
"""

ANNOTATED_PAGE27 = u"""
<span>
<br>
<input type="radio" name="size" checked value='44' data-scrapy-annotate="{&quot;variant&quot;: 1, &quot;generated&quot;: false,
&quot;annotations&quot;: {&quot;value&quot;: &quot;site_id&quot;}}">
<ins data-scrapy-annotate="{&quot;variant&quot;: 1, &quot;generated&quot;: true, 
&quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">"Large"</ins>
<br>
<input type="radio" name="size" checked value='45'>
"X Large"
<br>
<input type="radio" name="size" checked value='46' data-scrapy-annotate="{&quot;variant&quot;: 2, &quot;generated&quot;: false,
&quot;annotations&quot;: {&quot;value&quot;: &quot;site_id&quot;}}">
<ins data-scrapy-annotate="{&quot;variant&quot;: 2, &quot;generated&quot;: true, 
&quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">"XX Large"</ins>
</span>
"""

EXTRACT_PAGE27 = u"""
<span>
<br>
<input type="radio" name="size" checked value='44'>
"Large"
<br>
<input type="radio" name="size" checked value='45'>
"X Large"
<br>
<input type="radio" name="size" checked value='46'>
"XX Large"
</span>
"""

ANNOTATED_PAGE28 = u"""
<span>
<br>
<input type="radio" name="size" checked value='44' data-scrapy-annotate="{&quot;variant&quot;: 1, &quot;generated&quot;: false,
&quot;annotations&quot;: {&quot;value&quot;: &quot;site_id&quot;}}">
<ins data-scrapy-annotate="{&quot;variant&quot;: 1, &quot;generated&quot;: true, 
&quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">"Large"</ins>
<br>
<input type="radio" name="size" checked value='45'>
"X Large"
<br>
<input type="radio" name="size" checked value='46' data-scrapy-annotate="{&quot;variant&quot;: 2, &quot;generated&quot;: false,
&quot;annotations&quot;: {&quot;value&quot;: &quot;site_id&quot;}}">
<ins data-scrapy-annotate="{&quot;variant&quot;: 2, &quot;generated&quot;: true, 
&quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">"XX Large"</ins>
</span>
<div data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;generated&quot;: false,
&quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}">Price: 45</div>
"""

EXTRACT_PAGE28 = u"""
<span>
<br>
<input type="radio" name="size" checked value='44'>
"Large"
<br>
<input type="radio" name="size" checked value='45'>
"X Large"
<br>
<input type="radio" name="size" checked value='46'>
"XX Large"
</span>
<div>Price: 45</div>
"""

ANNOTATED_PAGE29 = u"""
<table>
<tr><td data-scrapy-annotate="{&quot;variant&quot;: 1, &quot;generated&quot;: false,
 &quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">Name 1</td><td data-scrapy-annotate="{&quot;variant&quot;: 1, &quot;generated&quot;: false,
 &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">Desc 1</td><td><span data-scrapy-annotate="{&quot;variant&quot;: 1, &quot;generated&quot;: false,
 &quot;annotations&quot;: {&quot;content&quot;: &quot;tag&quot;}}">Tag 1</span><span>Tag2</span><span data-scrapy-annotate="{&quot;variant&quot;: 1, &quot;generated&quot;: false,
 &quot;annotations&quot;: {&quot;content&quot;: &quot;tag&quot;}}">Tag 3</span></td></tr>
<tr><td>Name 2</td><td>Desc 2</td><td><span>Tag 7</span><span>Tag 8</span></span>Tag 9</span></td></tr>
<tr><td data-scrapy-annotate="{&quot;variant&quot;: 2, &quot;generated&quot;: false,
 &quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">Name 3</td><td data-scrapy-annotate="{&quot;variant&quot;: 2, &quot;generated&quot;: false,
 &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">Desc 3</td><td><span data-scrapy-annotate="{&quot;variant&quot;: 2, &quot;generated&quot;: false,
 &quot;annotations&quot;: {&quot;content&quot;: &quot;tag&quot;}}">Tag 4</span><span>Tag5</span><span data-scrapy-annotate="{&quot;variant&quot;: 2, &quot;generated&quot;: false,
 &quot;annotations&quot;: {&quot;content&quot;: &quot;tag&quot;}}">Tag 6</span></td></tr>
</table>
"""

EXTRACT_PAGE29 = u"""
<table>
<tr><td>Name 1</td><td>Desc 1</td><td><span>Tag 1</span><span>Tag 2</span><span>Tag 3</span></td></tr>
<tr><td>Name 2</td><td>Desc 2</td><td><span>Tag 4</span><span>Tag 5</span><span>Tag 6</span></td></tr>
<tr><td>Name 3</td><td>Desc 3</td><td><span>Tag 7</span><span>Tag 8</span><span>Tag 9</span></td></tr>
</table>
"""

ANNOTATED_PAGE30 = u"""
<div data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;generated&quot;: false,
 &quot;annotations&quot;: {&quot;content&quot;: &quot;phone&quot;}}"><span>029349293</span></div>
"""

EXTRACT_PAGE30a = u"""
<div><span style="font-size:100%">Any text</span></div>
"""

EXTRACT_PAGE30b = u"""
<div><span style="font-size:100%">029847272</span></div>
"""

EXTRACT_PAGE30c = u"""
<div><span><!--item no. 100--></span></div>
"""

EXTRACT_PAGE30d = u"""
<div><span><script>var myvar= 10;</script></span></div>
"""

ANNOTATED_PAGE31 = u"""
<html><body>
<div>
<span data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">Product name</span>
<div><p data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}">60.00</p>
<span data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">description</span>
<span data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;features&quot;}}">features</span>
<img data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;src&quot;: &quot;image_urls&quot;}}" src="image.jpg" />
<table></table>
</div></div>
</body></html>
"""

EXTRACT_PAGE31 = u"""
<html><body>
<div>
<span>Product name</span>
<div><p>60.00</p>
<img src="http://example.com/image.jpg" />
<table></table>
</div></div>
</body></html>
"""

# repeated elements with ignored region only in one of them
ANNOTATED_PAGE32 = u"""
<ul>
<li data-scrapy-annotate="{&quot;variant&quot;: 0, 
    &quot;annotations&quot;: {&quot;content&quot;: &quot;features&quot;}}">feature1<span data-scrapy-ignore="true"> ignore this</span></li>
<li data-scrapy-annotate="{&quot;variant&quot;: 0, 
    &quot;annotations&quot;: {&quot;content&quot;: &quot;features&quot;}}">feature2</li>
</ul>
"""

EXTRACT_PAGE32 = u"""
<ul>
<li>feature1<span> ignore this</span></li>
<li>feature2</li>
<li>feature3</li>
</ul>
"""

DEFAULT_DESCRIPTOR = ItemDescriptor('test', 
        'item test, removes tags from description attribute',
        [A('description', 'description field without tags', notags)])

SAMPLE_DESCRIPTOR1 = ItemDescriptor('test', 'product test', [
            A('name', "Product name", required=True),
            A('price', "Product price, including any discounts and tax or vat", 
                contains_any_numbers, True),    
            A('image_urls', "URLs for one or more images", image_url, True),
            A('description', "The full description of the product", html),
            ]
        )

SAMPLE_DESCRIPTOR1a = ItemDescriptor('test', 'product test', [
            A('name', "Product name"),
            A('price', "Product price, including any discounts and tax or vat", 
                contains_any_numbers),    
            A('image_urls', "URLs for one or more images", image_url),
            A('description', "The full description of the product", html),
            ]
        )

SAMPLE_DESCRIPTOR2 = ItemDescriptor('test', 'item test', [
        A('description', 'description field without tags', notags),
        A('price', "Product price, including any discounts and tax or vat",
                contains_any_numbers),
    ])

SAMPLE_DESCRIPTOR3 = ItemDescriptor('test', 
        'item test',
        [A('phone', 'phone number', lambda x: contains_any_numbers(x.text_content))])

SAMPLE_DESCRIPTOR4 =  ItemDescriptor('test', 
        'item test, removes tags from description attribute',
        [A('description', 'description field without tags', lambda x: x.text_content)])

# A list of (test name, [templates], page, extractors, expected_result)
TEST_DATA = [
    # extract from a similar page
    ('similar page extraction', [ANNOTATED_PAGE1], EXTRACT_PAGE1, DEFAULT_DESCRIPTOR,
        {u'title': [u'Nice Product'], u'description': [u'wonderful product'], 
            u'image_url': [u'nice_product.jpg']}
    ),
    # strip the first 5 characters from the title
    ('extractor test', [ANNOTATED_PAGE1], EXTRACT_PAGE1,
        ItemDescriptor('test', 'product test', 
            [A('title', "something about a title", lambda x: x[5:])]),
        {u'title': [u'Product'], u'description': [u'wonderful product'], 
            u'image_url': [u'nice_product.jpg']}
    ),
    # compilicated tag (multiple attributes and annotation)
    ('multiple attributes and annotation', [ANNOTATED_PAGE2], EXTRACT_PAGE2, DEFAULT_DESCRIPTOR,
        {'name': [u'product 1'], 'image_url': [u'http://example.com/product1.jpg'],
            'description': [u'product 1 is great']}
    ),
    # can only work out correct placement by matching the second attribute first
    ('ambiguous description', [ANNOTATED_PAGE3], EXTRACT_PAGE3, DEFAULT_DESCRIPTOR,
        {'description': [u'description'], 'delivery': [u'delivery']}
    ),
    # infer a repeated structure
    ('repeated elements', [ANNOTATED_PAGE4], EXTRACT_PAGE4, DEFAULT_DESCRIPTOR,
        {'features': [u'feature1', u'feature2', u'feature3']}
    ),
    # identical variants with a repeated structure
    ('repeated identical variants', [ANNOTATED_PAGE5], EXTRACT_PAGE5, DEFAULT_DESCRIPTOR,
         {
             'description': [u'description'],
             'variants': [
                 {u'colour': [u'colour 1'], u'price': [u'price 1']}, 
                 {u'colour': [u'colour 2'], u'price': [u'price 2']}, 
                 {u'colour': [u'colour 3'], u'price': [u'price 3']} 
             ]
         }
    ),
    ('variants with extra required attributes', [ANNOTATED_PAGE5a], EXTRACT_PAGE5, SAMPLE_DESCRIPTOR2,
         {
             'description': [u'description'],
             'variants': [
                 {u'colour': [u'colour 1'], u'price': [u'price 1']}, 
                 {u'colour': [u'colour 2'], u'price': [u'price 2']}, 
                 {u'colour': [u'colour 3'], u'price': [u'price 3']} 
             ]
         }
    ),
    ('test that new descriptor is created from the original', [ANNOTATED_PAGE4], EXTRACT_PAGE4, SAMPLE_DESCRIPTOR2,
        {'features': [u'feature1', u'feature2', u'feature3']}
    ),
    # variants with an irregular structure
    ('irregular variants', [ANNOTATED_PAGE6], EXTRACT_PAGE6, DEFAULT_DESCRIPTOR,
         {
             'description': [u'description'],
             'variants': [
                 {u'name': [u'name 1']}, 
                 {u'name': [u'name 3']}, 
                 {u'name': [u'name 2']}
             ]
         }
    ),
    ('dont fail if extra required attribute has no field descriptor', [ANNOTATED_PAGE5a], EXTRACT_PAGE5,
        DEFAULT_DESCRIPTOR,
          {
             'description': [u'description'],
             'variants': [
                 {u'colour': [u'colour 1'], u'price': [u'price 1']}, 
                 {u'colour': [u'colour 2'], u'price': [u'price 2']}, 
                 {u'colour': [u'colour 3'], u'price': [u'price 3']} 
             ]
         }
    ),

    # discovering repeated variants in table columns
#    ('variants in table columns', [ANNOTATED_PAGE7], EXTRACT_PAGE7, DEFAULT_DESCRIPTOR,
#         {'variants': [
#             {u'colour': [u'colour 1'], u'price': [u'price 1']}, 
#             {u'colour': [u'colour 2'], u'price': [u'price 2']}, 
#             {u'colour': [u'colour 3'], u'price': [u'price 3']}
#         ]}
#    ),
    
    
    # ignored regions
    (
    'ignored_regions', [ANNOTATED_PAGE8], EXTRACT_PAGE8, DEFAULT_DESCRIPTOR,
          {
             'description': [u'\n A very nice product for all intelligent people \n \n'],
             'price': [u'\n12.00\n(VAT exc.)'],
          }
    ),
    # ignored regions and text content extraction
    (
    'ignored_regions', [ANNOTATED_PAGE8], EXTRACT_PAGE8, SAMPLE_DESCRIPTOR4,
          {
             'description': [u'\n A very nice product for all intelligent people \n \n'],
             'price': [u'\n12.00\n(VAT exc.)'],
          }
    ),
    # shifted ignored regions (detected by region similarity)
    (
    'shifted_ignored_regions', [ANNOTATED_PAGE9], EXTRACT_PAGE9, DEFAULT_DESCRIPTOR,
          {
             'description': [u'\n A very nice product for all intelligent people \n \n'],
             'price': [u'\n12.00\n(VAT exc.)'],
          }
    ),
    (# special case with partial annotations
    'special_partial_annotation', [ANNOTATED_PAGE11], EXTRACT_PAGE11, DEFAULT_DESCRIPTOR,
          {
            'name': [u'SL342'],
            'description': ['\nSL342\n \nNice product for ladies\n \n&pound;85.00\n'],
            'price': [u'\xa385.00'],
            'price_before_discount': [u'\xa3100.00'],
          }
    ),
    (# with ignore-beneath feature
    'ignore-beneath', [ANNOTATED_PAGE12], EXTRACT_PAGE12a, DEFAULT_DESCRIPTOR,
          {
            'description': [u'\n A very nice product for all intelligent people \n'],
          }
    ),
    (# ignore-beneath with extra tags
    'ignore-beneath with extra tags', [ANNOTATED_PAGE12], EXTRACT_PAGE12b, DEFAULT_DESCRIPTOR,
          {
            'description': [u'\n A very nice product for all intelligent people \n'],
          }
    ),
    ('nested annotation with replica outside', [ANNOTATED_PAGE13a], EXTRACT_PAGE13a, DEFAULT_DESCRIPTOR,
          {'description': [u'\n A product \n $50.00 \nThis product is excelent. Buy it!\n \n'],
           'price': ["$50.00"],
           'name': [u'A product']}
    ),
    ('outside annotation with nested replica', [ANNOTATED_PAGE13b], EXTRACT_PAGE13b, DEFAULT_DESCRIPTOR,
          {'description': [u'\n A product \n $50.00 \nThis product is excelent. Buy it!\n'],
           'price': ["$45.00"],
           'name': [u'A product']}
    ),
    ('consistency check', [ANNOTATED_PAGE14], EXTRACT_PAGE14, DEFAULT_DESCRIPTOR,
          None,
    ),
    ('consecutive nesting', [ANNOTATED_PAGE15], EXTRACT_PAGE15, DEFAULT_DESCRIPTOR,
          {'description': [u'Description\n \n'],
           'price': [u'80.00']},
    ),
    ('nested inside not found', [ANNOTATED_PAGE16], EXTRACT_PAGE16, DEFAULT_DESCRIPTOR,
          {'price': [u'90.00'],
           'name': [u'product name']},
    ),
    ('ignored region helps to find attributes', [ANNOTATED_PAGE17], EXTRACT_PAGE17, DEFAULT_DESCRIPTOR,
          {'description': [u'\nThis product is excelent. Buy it!\n']},
    ),
    ('ignored region in partial annotation', [ANNOTATED_PAGE18], EXTRACT_PAGE18, DEFAULT_DESCRIPTOR,
          {u'site_id': [u'Item Id'],
           u'description': [u'\nDescription\n']},
    ),
    ('extra required attribute product', [ANNOTATED_PAGE19], EXTRACT_PAGE19a,
         SAMPLE_DESCRIPTOR1,
         {u'price': [u'60.00'],
          u'description': [u'description'],
          u'image_urls': [['http://example.com/image.jpg']],
          u'name': [u'Product name']},
    ),
    ('extra required attribute no product', [ANNOTATED_PAGE19], EXTRACT_PAGE19b,
         SAMPLE_DESCRIPTOR1,
         None,
    ),
    ('repeated partial annotations with variants', [ANNOTATED_PAGE20], EXTRACT_PAGE20, DEFAULT_DESCRIPTOR,
            {u'variants': [
                {'price': ['270'], 'name': ['Twin']},
                {'price': ['330'], 'name': ['Queen']},
            ]},
    ),
    ('variants with swatches', [ANNOTATED_PAGE21], EXTRACT_PAGE21, DEFAULT_DESCRIPTOR,
            {u'category': [u'chairs'],
             u'image_urls': [u'image.jpg'],
             u'variants': [
                {'swatches': ['swatch1.jpg']},
                {'swatches': ['swatch2.jpg']},
                {'swatches': ['swatch3.jpg']},
                {'swatches': ['swatch4.jpg']},
             ]
            },
    ),
    ('variants with swatches complete', [ANNOTATED_PAGE22], EXTRACT_PAGE22, DEFAULT_DESCRIPTOR,
            {u'category': [u'chairs'],
             u'variants': [
                 {u'swatches': [u'swatch1.jpg'],
                  u'price': [u'$70'],
                  u'name': [u'product 1']},
                 {u'swatches': [u'swatch2.jpg'],\
                  u'price': [u'$80'],
                  u'name': [u'product 2']},
                 {u'swatches': [u'swatch3.jpg'],
                  u'price': [u'$90'],
                  u'name': [u'product 3']},
                 {u'swatches': [u'swatch4.jpg'],
                  u'price': [u'$100'],
                  u'name': [u'product 4']}
             ],
             u'image_urls': [u'image.jpg']},
    ),
    ('repeated (variants) with ignore annotations', [ANNOTATED_PAGE23], EXTRACT_PAGE23, DEFAULT_DESCRIPTOR,
        {'variants': [
            {u'price': [u'300'], u'name': [u'Variant 1']},
            {u'price': [u'320'], u'name': [u'Variant 2']},
            {u'price': [u'340'], u'name': [u'Variant 3']}
            ]},
    ),
    (# dont fail when there are two consecutive ignore-beneath
    'double ignore-beneath inside annotation', [ANNOTATED_PAGE24], EXTRACT_PAGE24, DEFAULT_DESCRIPTOR,
          {
            'description': [u'\n A very nice product for all intelligent people \n'],
          }
    ),
    ('repeated partial annotation within same tag', [ANNOTATED_PAGE25], EXTRACT_PAGE25, DEFAULT_DESCRIPTOR,
            {"name": ['"Large"', '"X Large"', '"XX Large"']}
    ),
    ('repeated partial annotation within same tag, variants version', [ANNOTATED_PAGE26], EXTRACT_PAGE26, DEFAULT_DESCRIPTOR,
            {"variants": [
                {"name": ['"Large"']},
                {"name": ['"X Large"']},
                {"name": ['"XX Large"']}
            ]}
    ),
    ('repeated partial annotation within same tag, variants version with more than one attribute',
            [ANNOTATED_PAGE27], EXTRACT_PAGE27, DEFAULT_DESCRIPTOR,
            {"variants": [
                {"name": ['"Large"'], "site_id": ["44"]},
                {"name": ['"X Large"'], "site_id": ["45"]},
                {"name": ['"XX Large"'], "site_id": ["46"]}
            ]}
    ),
    ('repeated partial annotation within same tag, variants version with more than one attribute, more annotations around',
            [ANNOTATED_PAGE28], EXTRACT_PAGE28, DEFAULT_DESCRIPTOR, {
                "price": ["Price: 45"],
                "variants": [
                    {"name": ['"Large"'], "site_id": ["44"]},
                    {"name": ['"X Large"'], "site_id": ["45"]},
                    {"name": ['"XX Large"'], "site_id": ["46"]}]
            }
    ),
    ('repeated annotation inside variants', [ANNOTATED_PAGE29], EXTRACT_PAGE29, DEFAULT_DESCRIPTOR, 
            {'variants': [
                {u'tag': [u'Tag 1', u'Tag 2', u'Tag 3'], u'description': [u'Desc 1'], u'name': [u'Name 1']},
                {u'tag': [u'Tag 4', u'Tag 5', u'Tag 6'], u'description': [u'Desc 2'], u'name': [u'Name 2']},
                {u'tag': [u'Tag 7', u'Tag 8', u'Tag 9'], u'description': [u'Desc 3'], u'name': [u'Name 3']}]
            }

    ),
    ('avoid false positives by allowing to extract only from text content', [ANNOTATED_PAGE30], EXTRACT_PAGE30a, SAMPLE_DESCRIPTOR3,
        None
    ),
    ('only extract from text content', [ANNOTATED_PAGE30], EXTRACT_PAGE30b, SAMPLE_DESCRIPTOR3,
        {u'phone': [u'029847272']}
    ),
    ('avoid false positives on comments', [ANNOTATED_PAGE30], EXTRACT_PAGE30c, SAMPLE_DESCRIPTOR3,
        None
    ),
    ('avoid false positives on scripts', [ANNOTATED_PAGE30], EXTRACT_PAGE30d, SAMPLE_DESCRIPTOR3,
        None
    ),
    ('correctly extract regions that follows more than one consecutive misses', [ANNOTATED_PAGE31], EXTRACT_PAGE31, SAMPLE_DESCRIPTOR1a,
        {
            u'price': [u'60.00'],
            u'name': [u'Product name'],
            u'image_urls': [['http://example.com/image.jpg']]
        }
    ),
    ('single ignored region inside a repeated structure', [ANNOTATED_PAGE32], EXTRACT_PAGE32, DEFAULT_DESCRIPTOR,
        {'features': [u'feature1', u'feature2', u'feature3']}
    ),
]



class TestExtraction(TestCase):
    @parameterized.expand(TEST_DATA)
    def test_extraction(self, name, templates, page, descriptor, expected_output):
        template_pages = [HtmlPage(None, {}, t) for t in templates]

        extractor = InstanceBasedLearningExtractor([(t, descriptor) for t in template_pages])
        actual_output, _ = extractor.extract(HtmlPage(None, {}, page))

        self.assertEqual(expected_output, actual_output and actual_output[0])

########NEW FILE########
__FILENAME__ = test_htmlpage
"""
htmlpage.py tests
"""
import os, copy
from unittest import TestCase

from scrapely.tests import iter_samples
from scrapely.htmlpage import parse_html, HtmlTag, HtmlDataFragment, HtmlPage
from scrapely.tests.test_htmlpage_data import *

def _encode_element(el):
    """
    jsonize parse element
    """
    if isinstance(el, HtmlTag):
        return {"tag": el.tag, "attributes": el.attributes,
            "start": el.start, "end": el.end, "tag_type": el.tag_type}
    if isinstance(el, HtmlDataFragment):
        return {"start": el.start, "end": el.end, "is_text_content": el.is_text_content}
    raise TypeError

def _decode_element(dct):
    """
    dejsonize parse element
    """
    if "tag" in dct:
        return HtmlTag(dct["tag_type"], dct["tag"], \
            dct["attributes"], dct["start"], dct["end"])
    if "start" in dct:
        return HtmlDataFragment(dct["start"], dct["end"], dct.get("is_text_content", True))
    return dct

class TestParseHtml(TestCase):
    """Test for parse_html"""
    def _test_sample(self, source, expected_parsed, samplecount=None):
        parsed = parse_html(source)
        count_element = 0
        count_expected = 0
        for element in parsed:
            if type(element) == HtmlTag:
                count_element += 1
            expected = expected_parsed.pop(0)
            if type(expected) == HtmlTag:
                count_expected += 1
            element_text = source[element.start:element.end]
            expected_text = source[expected.start:expected.end]
            if element.start != expected.start or element.end != expected.end:
                errstring = "[%s,%s] %s != [%s,%s] %s" % (element.start, \
                    element.end, element_text, expected.start, \
                    expected.end, expected_text)
                if samplecount is not None:
                    errstring += " (sample %d)" % samplecount
                assert False, errstring
            if type(element) != type(expected):
                errstring = "(%s) %s != (%s) %s for text\n%s" % (count_element, \
                    repr(type(element)), count_expected, repr(type(expected)), element_text)
                if samplecount is not None:
                    errstring += " (sample %d)" % samplecount
                assert False, errstring
            if type(element) == HtmlTag:
                self.assertEqual(element.tag, expected.tag)
                self.assertEqual(element.attributes, expected.attributes)
                self.assertEqual(element.tag_type, expected.tag_type)
            if type(element) == HtmlDataFragment:
                msg = "Got: %s Expected: %s in sample: %d [%d:%d] (%s)" % \
                        (element.is_text_content, expected.is_text_content, samplecount, element.start, element.end, repr(element_text)) \
                        if samplecount is not None else None
                self.assertEqual(element.is_text_content, expected.is_text_content, msg)

        if expected_parsed:
            errstring = "Expected %s" % repr(expected_parsed)
            if samplecount is not None:
                errstring += " (sample %d)" % samplecount
            assert False, errstring

    def test_parse(self):
        """simple parse_html test"""
        parsed = [_decode_element(d) for d in PARSED]
        sample = {"source": PAGE, "parsed": parsed}
        self._test_sample(PAGE, parsed)
        
    def test_site_samples(self):
        """test parse_html from real cases"""
        for i, (source, parsed) in enumerate(
                iter_samples('htmlpage', object_hook=_decode_element)):
            self._test_sample(source, parsed, i)
 
    def test_bad(self):
        """test parsing of bad html layout"""
        parsed = [_decode_element(d) for d in PARSED2]
        self._test_sample(PAGE2, parsed)

    def test_comments(self):
        """test parsing of tags inside comments"""
        parsed = [_decode_element(d) for d in PARSED3]
        self._test_sample(PAGE3, parsed)

    def test_script_text(self):
        """test parsing of tags inside scripts"""
        parsed = [_decode_element(d) for d in PARSED4]
        self._test_sample(PAGE4, parsed)
        
    def test_sucessive(self):
        """test parsing of sucesive cleaned elements"""
        parsed = [_decode_element(d) for d in PARSED5]
        self._test_sample(PAGE5, parsed)
        
    def test_sucessive2(self):
        """test parsing of sucesive cleaned elements (variant 2)"""
        parsed = [_decode_element(d) for d in PARSED6]
        self._test_sample(PAGE6, parsed)
    
    def test_special_cases(self):
        """some special cases tests"""
        parsed = list(parse_html("<meta http-equiv='Pragma' content='no-cache' />"))
        self.assertEqual(parsed[0].attributes, {'content': 'no-cache', 'http-equiv': 'Pragma'})
        parsed = list(parse_html("<html xmlns='http://www.w3.org/1999/xhtml' xml:lang='en' lang='en'>"))
        self.assertEqual(parsed[0].attributes, {'xmlns': 'http://www.w3.org/1999/xhtml', 'xml:lang': 'en', 'lang': 'en'})
        parsed = list(parse_html("<IMG SRC='http://images.play.com/banners/SAM550a.jpg' align='left' / hspace=5>"))
        self.assertEqual(parsed[0].attributes, {'src': 'http://images.play.com/banners/SAM550a.jpg', \
                                                'align': 'left', 'hspace': '5', '/': None})

    def test_no_ending_body(self):
        """Test case when no ending body nor html elements are present"""
        parsed = [_decode_element(d) for d in PARSED7]
        self._test_sample(PAGE7, parsed)

    def test_malformed(self):
        """Test parsing of some malformed cases"""
        parsed = [_decode_element(d) for d in PARSED8]
        self._test_sample(PAGE8, parsed)

    def test_malformed2(self):
        """Test case when attributes are not separated by space (still recognizable because of quotes)"""
        parsed = [_decode_element(d) for d in PARSED9]
        self._test_sample(PAGE9, parsed)

    def test_empty_subregion(self):
        htmlpage = HtmlPage(body=u"")
        self.assertEqual(htmlpage.subregion(), u"")

    def test_ignore_xml_declaration(self):
        """Ignore xml declarations inside html"""
        parsed = list(parse_html(u"<p>The text</p><?xml:namespace blabla/><p>is here</p>"))
        self.assertFalse(parsed[3].is_text_content)

    def test_copy(self):
        """Test copy/deepcopy"""
        page = HtmlPage(url='http://www.example.com', body=PAGE)
        region = page.subregion(10, 15)
        
        regioncopy = copy.copy(region)
        self.assertEqual(regioncopy.start_index, 10)
        self.assertEqual(regioncopy.end_index, 15)
        self.assertFalse(region is regioncopy)
        self.assertTrue(region.htmlpage is regioncopy.htmlpage)

        regiondeepcopy = copy.deepcopy(region)
        self.assertEqual(regiondeepcopy.start_index, 10)
        self.assertEqual(regiondeepcopy.end_index, 15)
        self.assertFalse(region is regiondeepcopy)
        self.assertFalse(region.htmlpage is regiondeepcopy.htmlpage)

########NEW FILE########
__FILENAME__ = test_htmlpage_data
PAGE = u"""
<style id="scrapy-style" type="text/css">@import url(http://localhost:8000/as/site_media/clean.css);                           
</style>
<body>
<div class="scrapy-selected" id="header">
<img src="company_logo.jpg" style="margin-left: 68px; padding-top:5px;" alt="Logo" width="530" height="105">
<div id="vertrule">
<h1>COMPANY - <ins data-scrapy-annotate="{&quot;variant&quot;: &quot;0&quot;, &quot;generated&quot;: true, &quot;annotations&quot;: {&quot;content&quot;: &quot;title&quot;}}">Item Title</ins></h1>
<p>introduction</p>
<div>
<img src="/upload/img.jpg" classid=""
    data-scrapy-annotate="{&quot;variant&quot;: &quot;0&quot;, &quot;annotations&quot;: {&quot;image_url&quot;: &quot;src&quot;}}"
>
<p classid="" data-scrapy-annotate="{&quot;variant&quot;: &quot;0&quot;, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}"
>
This is such a nice item<br/> Everybody likes it.
</p>
<br></br>
</div>
<p data-scrapy-annotate="{&quot;variant&quot;: &quot;0&quot;, &quot;annotations&quot;: {&quot;content&quot;: &quot;features&quot;}}"
class="" >Power: 50W</p>
<!-- A comment --!>
<ul data-scrapy-replacement='select' class='product'>
<li data-scrapy-replacement='option'>Small</li>
<li data-scrapy-replacement='option'>Big</li>
</ul>
<p>click here for other items</p>
<h3>Louis Chair</h3>
<table class="rulet" width="420" cellpadding="0" cellspacing="0"><tbody>
<tr><td>Height</td>
<td><ins data-scrapy-annotate="{&quot;variant&quot;: &quot;0&quot;, &quot;generated&quot;: true, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}">32.00</ins></td>
</tr><tbody></table>
<p onmouseover='xxx' class= style="my style">
"""

PARSED = [
{'start': 0, 'end': 1},
{'attributes': {'type': 'text/css', 'id': 'scrapy-style'}, 'tag': 'style', 'end': 42, 'start': 1, 'tag_type': 1},
{'start': 42, 'end': 129},
{'attributes': {}, 'tag': 'style', 'end': 137, 'start': 129, 'tag_type': 2},
{'start': 137, 'end': 138},
{'attributes': {}, 'tag': 'body', 'end': 144, 'start': 138, 'tag_type': 1},
{'start': 144, 'end': 145},
{'attributes': {'class': 'scrapy-selected', 'id': 'header'}, 'tag': 'div', 'end': 186, 'start': 145, 'tag_type': 1},
{'start': 186, 'end': 187},
{'attributes': {'src': 'company_logo.jpg', 'style': 'margin-left: 68px; padding-top:5px;', 'width': '530', 'alt': 'Logo', 'height': '105'}, 'tag': 'img', 'end': 295, 'start': 187, 'tag_type': 1},
{'start': 295, 'end': 296},
{'attributes': {'id': 'vertrule'}, 'tag': 'div', 'end': 315, 'start': 296, 'tag_type': 1},
{'start': 315, 'end': 316},
{'attributes': {}, 'tag': 'h1', 'end': 320, 'start': 316, 'tag_type': 1},
{'start': 320, 'end': 330},
{'attributes': {'data-scrapy-annotate': '{&quot;variant&quot;: &quot;0&quot;, &quot;generated&quot;: true, &quot;annotations&quot;: {&quot;content&quot;: &quot;title&quot;}}'}, 'tag': 'ins', 'end': 491, 'start': 330, 'tag_type': 1},
{'start': 491, 'end': 501},
{'attributes': {}, 'tag': 'ins', 'end': 507, 'start': 501, 'tag_type': 2},
{'attributes': {}, 'tag': 'h1', 'end': 512, 'start': 507, 'tag_type': 2},
{'start': 512, 'end': 513},
{'attributes': {}, 'tag': 'p', 'end': 516, 'start': 513, 'tag_type': 1},
{'start': 516, 'end': 528},
{'attributes': {}, 'tag': 'p', 'end': 532, 'start': 528, 'tag_type': 2},
{'start': 532, 'end': 533},
{'attributes': {}, 'tag': 'div', 'end': 538, 'start': 533, 'tag_type': 1},
{'start': 538, 'end': 539},
{'attributes': {'classid': None, 'src': '/upload/img.jpg', 'data-scrapy-annotate': '{&quot;variant&quot;: &quot;0&quot;, &quot;annotations&quot;: {&quot;image_url&quot;: &quot;src&quot;}}'}, 'tag': 'img', 'end': 709, 'start': 539, 'tag_type': 1},
{'start': 709, 'end': 710},
{'attributes': {'classid': None, 'data-scrapy-annotate': '{&quot;variant&quot;: &quot;0&quot;, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}'}, 'tag': 'p', 'end': 858, 'start': 710, 'tag_type': 1},
{'start': 858, 'end': 883},
{'attributes': {}, 'tag': 'br', 'end': 888, 'start': 883, 'tag_type': 3},
{'start': 888, 'end': 909},
{'attributes': {}, 'tag': 'p', 'end': 913, 'start': 909, 'tag_type': 2},
{'start': 913, 'end': 914},
{'attributes': {}, 'tag': 'br', 'end': 918, 'start': 914, 'tag_type': 1},
{'attributes': {}, 'tag': 'br', 'end': 923, 'start': 918, 'tag_type': 2},
{'start': 923, 'end': 924},
{'attributes': {}, 'tag': 'div', 'end': 930, 'start': 924, 'tag_type': 2},
{'start': 930, 'end': 931},
{'attributes': {'data-scrapy-annotate': '{&quot;variant&quot;: &quot;0&quot;, &quot;annotations&quot;: {&quot;content&quot;: &quot;features&quot;}}', 'class': None}, 'tag': 'p', 'end': 1074, 'start': 931, 'tag_type': 1},
{'start': 1074, 'end': 1084},
{'attributes': {}, 'tag': 'p', 'end': 1088, 'start': 1084, 'tag_type': 2},
{'start': 1088, 'end': 1109},
{'attributes': {'data-scrapy-replacement': 'select', 'class': 'product'}, 'tag': 'ul', 'end': 1162, 'start': 1109, 'tag_type': 1},
{'start': 1162, 'end': 1163},
{'attributes': {'data-scrapy-replacement': 'option'}, 'tag': 'li', 'end': 1200, 'start': 1163, 'tag_type': 1},
{'start': 1200, 'end': 1205},
{'attributes': {}, 'tag': 'li', 'end': 1210, 'start': 1205, 'tag_type': 2},
{'start': 1210, 'end': 1211},
{'attributes': {'data-scrapy-replacement': 'option'}, 'tag': 'li', 'end': 1248, 'start': 1211, 'tag_type': 1},
{'start': 1248, 'end': 1251},
{'attributes': {}, 'tag': 'li', 'end': 1256, 'start': 1251, 'tag_type': 2},
{'start': 1256, 'end': 1257},
{'attributes': {}, 'tag': 'ul', 'end': 1262, 'start': 1257, 'tag_type': 2},
{'start': 1262, 'end': 1263},
{'attributes': {}, 'tag': 'p', 'end': 1266, 'start': 1263, 'tag_type': 1},
{'start': 1266, 'end': 1292},
{'attributes': {}, 'tag': 'p', 'end': 1296, 'start': 1292, 'tag_type': 2},
{'start': 1296, 'end': 1297},
{'attributes': {}, 'tag': 'h3', 'end': 1301, 'start': 1297, 'tag_type': 1},
{'start': 1301, 'end': 1312},
{'attributes': {}, 'tag': 'h3', 'end': 1317, 'start': 1312, 'tag_type': 2},
{'start': 1317, 'end': 1318},
{'attributes': {'cellpadding': '0', 'width': '420', 'cellspacing': '0', 'class': 'rulet'}, 'tag': 'table', 'end': 1383, 'start': 1318, 'tag_type': 1},
{'attributes': {}, 'tag': 'tbody', 'end': 1390, 'start': 1383, 'tag_type': 1},
{'start': 1390, 'end': 1391},
{'attributes': {}, 'tag': 'tr', 'end': 1395, 'start': 1391, 'tag_type': 1},
{'attributes': {}, 'tag': 'td', 'end': 1399, 'start': 1395, 'tag_type': 1},
{'start': 1399, 'end': 1405},
{'attributes': {}, 'tag': 'td', 'end': 1410, 'start': 1405, 'tag_type': 2},
{'start': 1410, 'end': 1411},
{'attributes': {}, 'tag': 'td', 'end': 1415, 'start': 1411, 'tag_type': 1},
{'attributes': {'data-scrapy-annotate': '{&quot;variant&quot;: &quot;0&quot;, &quot;generated&quot;: true, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}'}, 'tag': 'ins', 'end': 1576, 'start': 1415, 'tag_type': 1},
{'start': 1576, 'end': 1581},
{'attributes': {}, 'tag': 'ins', 'end': 1587, 'start': 1581, 'tag_type': 2},
{'attributes': {}, 'tag': 'td', 'end': 1592, 'start': 1587, 'tag_type': 2},
{'start': 1592, 'end': 1593},
{'attributes': {}, 'tag': 'tr', 'end': 1598, 'start': 1593, 'tag_type': 2},
{'attributes': {}, 'tag': 'tbody', 'end': 1605, 'start': 1598, 'tag_type': 1},
{'attributes': {}, 'tag': 'table', 'end': 1613, 'start': 1605, 'tag_type': 2},
{'start': 1613, 'end': 1614},
{'attributes': {'style': 'my style', 'onmouseover': 'xxx', 'class': None}, 'tag': 'p', 'end': 1659, 'start': 1614, 'tag_type': 1},
{'start': 1659, 'end': 1660},
]

# for testing parsing of some invalid html code (but still managed by browsers)
PAGE2 = u"""
<html>
<body>
<p class=&#34;MsoNormal&#34; style=&#34;margin: 0cm 0cm 0pt&#34;><span lang=&#34;EN-GB&#34;>
Hello world!
</span>
</p>
</body>
</html>
"""

PARSED2 = [
 {'end': 1, 'start': 0},
 {'attributes': {}, 'end': 7, 'start': 1, 'tag': u'html', 'tag_type': 1},
 {'end': 8, 'start': 7},
 {'attributes': {}, 'end': 14, 'start': 8, 'tag': u'body', 'tag_type': 1},
 {'end': 15, 'start': 14},
 {'attributes': {u'style': u'&#34;margin:', u'0pt&#34;': None, u'class': u'&#34;MsoNormal&#34;', u'0cm': None}, 'end': 80, 'start': 15, 'tag': u'p', 'tag_type': 1},
 {'attributes': {u'lang': u'&#34;EN-GB&#34;'}, 'end': 107, 'start': 80, 'tag': u'span', 'tag_type': 1},
 {'end': 121, 'start': 107},
 {'attributes': {}, 'end': 128, 'start': 121, 'tag': u'span', 'tag_type': 2},
 {'end': 129, 'start': 128},
 {'attributes': {}, 'end': 133, 'start': 129, 'tag': u'p', 'tag_type': 2},
 {'end': 134, 'start': 133},
 {'attributes': {}, 'end': 141, 'start': 134, 'tag': u'body', 'tag_type': 2},
 {'end': 142, 'start': 141},
 {'attributes': {}, 'end': 149, 'start': 142, 'tag': u'html', 'tag_type': 2},
 {'end': 150, 'start': 149},
]

# for testing tags inside comments
PAGE3 = u"""<html><body><h1>Helloooo!!</h1><p>Did i say hello??</p><!--<p>
</p>--><script type="text/javascript">bla<!--comment-->blabla</script></body></html>"""

PARSED3 = [
 {'attributes': {}, 'end': 6, 'start': 0, 'tag': u'html', 'tag_type': 1},
 {'attributes': {}, 'end': 12, 'start': 6, 'tag': u'body', 'tag_type': 1},
 {'attributes': {}, 'end': 16, 'start': 12, 'tag': u'h1', 'tag_type': 1},
 {'end': 26, 'start': 16},
 {'attributes': {}, 'end': 31, 'start': 26, 'tag': u'h1', 'tag_type': 2},
 {'attributes': {}, 'end': 34, 'start': 31, 'tag': u'p', 'tag_type': 1},
 {'end': 51, 'start': 34},
 {'attributes': {}, 'end': 55, 'start': 51, 'tag': u'p', 'tag_type': 2},
 {'end': 70, 'start': 55, 'is_text_content': False},
 {'attributes': {u'type': u'text/javascript'}, 'end': 101, 'start': 70, 'tag': u'script', 'tag_type': 1},
 {'end': 104, 'start': 101, 'is_text_content': False},
 {'end': 118, 'start': 104, 'is_text_content': False},
 {'end': 124, 'start': 118, 'is_text_content': False},
 {'attributes': {}, 'end': 133, 'start': 124, 'tag': u'script', 'tag_type': 2},
 {'attributes': {}, 'end': 140, 'start': 133, 'tag': u'body', 'tag_type': 2},
 {'attributes': {}, 'end': 147, 'start': 140, 'tag': u'html', 'tag_type': 2}
]

# for testing tags inside scripts
PAGE4 = u"""<html><body><h1>Konnichiwa!!</h1>hello<script type="text/javascript">\
doc.write("<img src=" + base + "product/" + productid + ">");\
</script>hello again</body></html>"""

PARSED4 = [
 {'attributes': {}, 'end': 6, 'start': 0, 'tag': u'html', 'tag_type': 1},
 {'attributes': {}, 'end': 12, 'start': 6, 'tag': u'body', 'tag_type': 1},
 {'attributes': {}, 'end': 16, 'start': 12, 'tag': u'h1', 'tag_type': 1},
 {'end': 28,'start': 16},
 {'attributes': {}, 'end': 33, 'start': 28, 'tag': u'h1', 'tag_type': 2},
 {'end': 38, 'start': 33},
 {'attributes': {u'type': u'text/javascript'}, 'end': 69, 'start': 38, 'tag': u'script', 'tag_type': 1},
 {'end': 130, 'start': 69, 'is_text_content': False},
 {'attributes': {}, 'end': 139, 'start': 130, 'tag': u'script', 'tag_type': 2},
 {'end': 150, 'start': 139},
 {'attributes': {}, 'end': 157, 'start': 150, 'tag': u'body', 'tag_type': 2},
 {'attributes': {}, 'end': 164, 'start': 157, 'tag': u'html', 'tag_type': 2},
]

# Test sucessive cleaning elements
PAGE5 = u"""<html><body><script>hello</script><script>brb</script></body><!--commentA--><!--commentB--></html>"""

PARSED5 = [
 {'attributes': {}, 'end': 6, 'start': 0, 'tag': u'html', 'tag_type': 1},
 {'attributes': {}, 'end': 12, 'start': 6, 'tag': u'body', 'tag_type': 1},
 {'attributes': {}, 'end': 20, 'start': 12, 'tag': u'script', 'tag_type': 1},
 {'end': 25, 'start': 20, 'is_text_content': False},
 {'attributes': {}, 'end': 34, 'start': 25, 'tag': u'script', 'tag_type': 2},
 {'attributes': {}, 'end': 42, 'start': 34, 'tag': u'script', 'tag_type': 1},
 {'end': 45, 'start': 42, 'is_text_content': False},
 {'attributes': {}, 'end': 54, 'start': 45, 'tag': u'script', 'tag_type': 2},
 {'attributes': {}, 'end': 61, 'start': 54, 'tag': u'body', 'tag_type': 2},
 {'end': 76, 'start': 61, 'is_text_content': False},
 {'end': 91, 'start': 76, 'is_text_content': False},
 {'attributes': {}, 'end': 98, 'start': 91, 'tag': u'html', 'tag_type': 2},
]
 
# Test sucessive cleaning elements variant 2
PAGE6 = u"""<html><body><script>pss<!--comment-->pss</script>all<script>brb</script>\n\n</body></html>"""

PARSED6 = [
 {'attributes': {}, 'end': 6, 'start': 0, 'tag': u'html', 'tag_type': 1},
 {'attributes': {}, 'end': 12, 'start': 6, 'tag': u'body', 'tag_type': 1},
 {'attributes': {}, 'end': 20, 'start': 12, 'tag': u'script', 'tag_type': 1},
 {'end': 23, 'start': 20, 'is_text_content': False},
 {'end': 37, 'start': 23, 'is_text_content': False},
 {'end': 40, 'start': 37, 'is_text_content': False},
 {'attributes': {}, 'end': 49, 'start': 40, 'tag': u'script', 'tag_type': 2},
 {'end': 52, 'start': 49},
 {'attributes': {}, 'end': 60, 'start': 52, 'tag': u'script', 'tag_type': 1},
 {'end': 63, 'start': 60, 'is_text_content': False},
 {'attributes': {}, 'end': 72, 'start': 63, 'tag': u'script', 'tag_type': 2},
 {'end': 74, 'start': 72},
 {'attributes': {}, 'end': 81, 'start': 74, 'tag': u'body', 'tag_type': 2},
 {'attributes': {}, 'end': 88, 'start': 81, 'tag': u'html', 'tag_type': 2},
]

# Test source without ending body nor html
PAGE7 = u"""<html><body><p>veris in temporibus sub aprilis idibus</p><script>script code</script><!--comment-->"""

PARSED7 = [
    {'attributes' : {}, 'end': 6, 'start': 0, 'tag': u'html', 'tag_type': 1},
    {'attributes': {}, 'end': 12, 'start': 6, 'tag': u'body', 'tag_type': 1},
    {'attributes': {}, 'end': 15, 'start': 12, 'tag': u'p', 'tag_type': 1},
    {'end': 53, 'start': 15},
    {'attributes': {}, 'end': 57, 'start': 53, 'tag': u'p', 'tag_type': 2},
    {'attributes' : {}, 'end': 65, 'start': 57, 'tag': u'script', 'tag_type': 1},
    {'end': 76, 'start': 65, 'is_text_content': False},
    {'attributes' : {}, 'end': 85, 'start': 76, 'tag': u'script', 'tag_type': 2},
    {'end': 99, 'start': 85, 'is_text_content': False},
]

PAGE8 = u"""<a href="/overview.asp?id=277"><img border="0" src="/img/5200814311.jpg" title=\'Vinyl Cornice\'</a></td><table width=\'5\'>"""

PARSED8 = [
   {'attributes' : {u'href' : u"/overview.asp?id=277"}, 'end': 31, 'start': 0, 'tag': u'a', 'tag_type': 1},
   {'attributes' : {u'src' : u"/img/5200814311.jpg", u'border' : u"0", u'title': u'Vinyl Cornice'}, 'end': 94, 'start': 31, 'tag': u'img', 'tag_type': 1},
   {'attributes' : {}, 'end': 98, 'start': 94, 'tag': u'a', 'tag_type': 2},
   {'attributes' : {}, 'end': 103, 'start': 98, 'tag': u'td', 'tag_type': 2},
   {'attributes' : {u'width': u'5'}, 'end': 120, 'start': 103, 'tag': u'table', 'tag_type': 1}
]

PAGE9 = u"""\
<html>\
<body>\
<img width='230' height='150'src='/images/9589.jpg' >\
<a href="/product/9589">Click here</a>\
</body>\
</html>\
"""

PARSED9 = [
    {'attributes' : {}, 'end': 6, 'start': 0, 'tag': 'html', 'tag_type': 1},
    {'attributes' : {}, 'end': 12, 'start': 6, 'tag': 'body', 'tag_type': 1},
    {'attributes' : {'width': '230', 'height': '150', 'src': '/images/9589.jpg'}, 'end': 65, 'start': 12, 'tag': 'img', 'tag_type': 1},
    {'attributes' : {'href': '/product/9589'}, 'end': 89, 'start': 65, 'tag': 'a', 'tag_type': 1},
    {'end': 99, 'start': 89},
    {'attributes' : {}, 'end': 103, 'start': 99, 'tag': 'a', 'tag_type': 2},
    {'attributes' : {}, 'end': 110, 'start': 103, 'tag': 'body', 'tag_type': 2},
    {'attributes' : {}, 'end': 117, 'start': 110, 'tag': 'html', 'tag_type': 2},
]

########NEW FILE########
__FILENAME__ = test_pageparsing
"""
Unit tests for pageparsing
"""
import os
from cStringIO import StringIO
from unittest import TestCase
import numpy

from scrapely.htmlpage import HtmlPage
from scrapely.tests import iter_samples
from scrapely.extraction.pageparsing import (
    InstanceLearningParser, TemplatePageParser, ExtractionPageParser)
from scrapely.extraction.pageobjects import TokenDict, TokenType


SIMPLE_PAGE = u"""
<html> <p some-attr="foo">this is a test</p> </html>
"""

LABELLED_PAGE1 = u"""
<html>
<h1 data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">Some Product</h1>
<p> some stuff</p>
<p data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">
This is such a nice item<br/>
Everybody likes it.
</p>
<p data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}"/>
\xa310.00
<br/>
<p data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;short_description&quot;}}">
Old fashioned product
<p data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;short_description&quot;}}">
For exigent individuals
<p>click here for other items</p>
</html>
"""

BROKEN_PAGE = u"""
<html> <p class="ruleb"align="center">html parser cannot parse this</p></html>
"""

LABELLED_PAGE2 = u"""
<html><body>
<h1>A product</h1>
<div data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">
<p>A very nice product for all intelligent people</p>
<div data-scrapy-ignore="true">
<img scr="image.jpg" /><br/><a link="back.html">Click here to go back</a>
</div>
</div>
<div data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}">
\xa310.00<p data-scrapy-ignore="true"> 13 <br></p>
</div>
<table data-scrapy-ignore="true">
<tr><td data-scrapy-ignore="true"></td></tr>
<tr></tr>
</table>
<img data-scrapy-ignore="true" src="image2.jpg"> 
<img data-scrapy-ignore="true" src="image3.jpg" />
<img data-scrapy-ignore-beneath="true" src="image2.jpg">
<img data-scrapy-ignore-beneath="true" src="image3.jpg" />
</body></html>

"""

LABELLED_PAGE3 = u"""
<html><body>
<h1>A product</h1>
<div data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">
<p>A very nice product for all intelligent people</p>
<div data-scrapy-ignore="true">
<img scr="image.jpg" /><br/><a link="back.html">Click here to go back</a>
</div>
</div>
<div data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">
\xa310.00<p data-scrapy-ignore="true"> 13 <br></p>
<table><tr>
<td>Description 1</td>
<td data-scrapy-ignore-beneath="true">Description 2</td>
<td>Description 3</td>
<td>Description 4</td>
</tr></table>
</div>
</body></html>
"""

LABELLED_PAGE4 = u"""
<html><body>
<h1>A product</h1>
<div>
<p>A very nice product for all intelligent people</p>
<div>
<img scr="image.jpg" /><br/><a link="back.html">Click here to go back</a>
</div>
</div>
<div data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">
\xa310.00<p data-scrapy-ignore="true"> 13 <br></p>
<table><tr>
<td>Description 1</td>
<td data-scrapy-ignore-beneath="true">Description 2</td>
<td>Description 3</td>
<td data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}">
Price \xa310.00</td>
</tr></table>
</div>
</body></html>
"""

LABELLED_PAGE5 = u"""
<html><body>
<ul data-scrapy-replacement='select'>
<li data-scrapy-replacement='option'>Option A</li>
<li>Option I</li>
<li data-scrapy-replacement='option'>Option B</li>
</ul>
</body></html>
"""

LABELLED_PAGE5a = u"""
<ul data-scrapy-replacement="select" name="txtvariant" class="smalltextblk">
<li data-scrapy-replacement="option" data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}, &quot;generated&quot;: false}" value="BLUE">Blue&nbsp;$9.95 - In Stock</li> 
<li data-scrapy-replacement="option" data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}, &quot;generated&quot;: false}" value="RED">Red&nbsp;$9.95 - In Stock</li>
</ul>
"""

LABELLED_PAGE5b = u"""
<ul data-scrapy-replacement="select" name="txtvariant" class="smalltextblk">
<li data-scrapy-replacement="option" data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}, &quot;generated&quot;: false}" value="BLUE">Blue&nbsp;$9.95 - In Stock
<li data-scrapy-replacement="option" data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}, &quot;generated&quot;: false}" value="RED">Red&nbsp;$9.95 - In Stock
</ul>
"""

LABELLED_PAGE6 = u"""
<html><body>
Text A
<p><ins data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;generated&quot;: true, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}">
65.00</ins>pounds</p>
<p>Description: <ins data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;generated&quot;: true, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">
Text B</ins></p>
Text C
</body></html>
"""

LABELLED_PAGE7 = u"""
<html><body>
<div data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">
<ins data-scrapy-ignore="true" data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;generated&quot;: true, &quot;annotations&quot;: {&quot;content&quot;: &quot;site_id&quot;}}">Item Id</ins>
Description
</div>
</body></html>
"""

LABELLED_PAGE8 = u"""
<html><body>
<div data-scrapy-annotate="{&quot;required&quot;: [&quot;description&quot;], &quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}">
<ins data-scrapy-ignore="true" data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;generated&quot;: true, &quot;annotations&quot;: {&quot;content&quot;: &quot;site_id&quot;}}">Item Id</ins>
Description
</div>
</body></html>
"""

LABELLED_PAGE9 = u"""
<html><body>
<img src="image.jpg" data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;src&quot;: &quot;image_urls&quot;}}">
<p data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 1, &quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">product 1</p>
<b data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 1, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}">$67</b>
<p data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 2, &quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">product 2</p>
<b data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 2, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}">$70</b>
<div data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;category&quot;}}">tables</div>
</body></html>
"""

LABELLED_PAGE10 = u"""
<html><body>
<img src="image.jpg" data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;src&quot;: &quot;image_urls&quot;}}">
<p data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 1, &quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">product 1</p>
<b data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 1, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}">$67</b>
<img src="swatch1.jpg" data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 1, &quot;annotations&quot;: {&quot;src&quot;: &quot;swatches&quot;}}">

<p data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 2, &quot;annotations&quot;: {&quot;content&quot;: &quot;name&quot;}}">product 2</p>
<b data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 2, &quot;annotations&quot;: {&quot;content&quot;: &quot;price&quot;}}">$70</b>
<img src="swatch2.jpg" data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 2, &quot;annotations&quot;: {&quot;src&quot;: &quot;swatches&quot;}}">

<div data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 0, &quot;annotations&quot;: {&quot;content&quot;: &quot;category&quot;}}">tables</div>
</body></html>
"""

LABELLED_PAGE11 = u"""
<html><body>
<input type="text" name="3896" data-scrapy-annotate="{&quot;required&quot;: [], &quot;variant&quot;: 1, &quot;annotations&quot;: {&quot;name&quot;: &quot;site_id&quot;}, &quot;generated&quot;: false}" />
</body></html>
"""

LABELLED_PAGE12 = u"""
<head>
<meta name="description" content="This is the description" data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;generated&quot;: false, &quot;text-content&quot;: &quot;text-content:&quot;, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;}}" />
</head>
"""

LABELLED_PAGE13 = u"""
<head>
<meta name="description" content="This is the description" data-scrapy-annotate="{&quot;variant&quot;: 0, &quot;generated&quot;: false, &quot;text-content&quot;: &quot;text-content&quot;, &quot;annotations&quot;: {&quot;content&quot;: &quot;description&quot;, &quot;text-content&quot;: &quot;name&quot;}}">This is the name</meta>
</head>
"""

def _parse_page(parser_class, pagetext):
    htmlpage = HtmlPage(None, {}, pagetext)
    parser = parser_class(TokenDict())
    parser.feed(htmlpage)
    return parser

def _tags(pp, predicate):
    return [pp.token_dict.token_string(s) for s in pp.token_list \
            if predicate(s)]

class TestPageParsing(TestCase):

    def test_instance_parsing(self):
        pp = _parse_page(InstanceLearningParser, SIMPLE_PAGE)
        # all tags
        self.assertEqual(_tags(pp, bool), ['<html>', '<p>', '</p>', '</html>'])

        # open/closing tag handling
        openp = lambda x: pp.token_dict.token_type(x) == TokenType.OPEN_TAG
        self.assertEqual(_tags(pp, openp), ['<html>', '<p>'])
        closep = lambda x: pp.token_dict.token_type(x) == TokenType.CLOSE_TAG
        self.assertEqual(_tags(pp, closep), ['</p>', '</html>'])
    
    def _validate_annotation(self, parser, lable_region, name, start_tag, end_tag):
        self.assertEqual(lable_region.surrounds_attribute, name)
        start_token = parser.token_list[lable_region.start_index]
        self.assertEqual(parser.token_dict.token_string(start_token), start_tag)
        end_token = parser.token_list[lable_region.end_index]
        self.assertEqual(parser.token_dict.token_string(end_token), end_tag)

    def test_template_parsing(self):
        lp = _parse_page(TemplatePageParser, LABELLED_PAGE1)
        self.assertEqual(len(lp.annotations), 5)
        self._validate_annotation(lp, lp.annotations[0], 
                'name', '<h1>', '</h1>')
        
        # all tags were closed
        self.assertEqual(len(lp.labelled_tag_stacks), 0)
    
    def test_extraction_page_parsing(self):
        epp = _parse_page(ExtractionPageParser, SIMPLE_PAGE)
        ep = epp.to_extraction_page()
        self.assertEqual(len(ep.page_tokens), 4)
        self.assertEqual(ep.htmlpage.fragment_data(ep.htmlpage_tag(0)), '<html>')
        self.assertEqual(ep.htmlpage.fragment_data(ep.htmlpage_tag(1)), '<p some-attr="foo">')
        
        self.assertEqual(ep.htmlpage_region_inside(1, 2), 'this is a test')
        self.assertEqual(ep.htmlpage_region_inside(1, 3), 'this is a test</p> ')

    def test_invalid_html(self):
        p = _parse_page(InstanceLearningParser, BROKEN_PAGE)
        self.assertTrue(p)
        
    def test_ignore_region(self):
        """Test ignored regions"""
        p = _parse_page(TemplatePageParser, LABELLED_PAGE2)
        self.assertEqual(p.ignored_regions, [(7,12),(15,17),(19,26),(21,22),(27,28),(28,29),(29,None),(30,None)])
        self.assertEqual(len(p.ignored_tag_stacks), 0)

    def test_ignore_regions2(self):
        """Test ignore-beneath regions"""
        p = _parse_page(TemplatePageParser, LABELLED_PAGE3)
        self.assertEqual(p.ignored_regions, [(7,12),(15,17),(22,None)])
        self.assertEqual(len(p.ignored_tag_stacks), 0)
        
    def test_ignore_regions3(self):
        """Test ignore-beneath with annotation inside region"""
        p = _parse_page(TemplatePageParser, LABELLED_PAGE4)
        self.assertEqual(p.ignored_regions, [(15,17),(22,None)])
        self.assertEqual(len(p.ignored_tag_stacks), 0)
        
    def test_replacement(self):
        """Test parsing of replacement tags"""
        p = _parse_page(TemplatePageParser, LABELLED_PAGE5)
        self.assertEqual(_tags(p, bool), ['<html>', '<body>', '<select>', '<option>',
                    '</option>', '<li>', '</li>', '<option>', '</option>', '</select>', '</body>', '</html>'])

    def test_replacement2(self):
        """Replacement, with annotations"""
        p = _parse_page(TemplatePageParser, LABELLED_PAGE5a)
        self.assertEqual(_tags(p, bool), [u'<select>', u'<option>', u'</option>', u'<option>', u'</option>', u'</select>'])
        self.assertEqual(p.annotations[0].surrounds_attribute, 'price')
        self.assertEqual(p.annotations[0].start_index, 1)
        self.assertEqual(p.annotations[0].end_index, 2)
        self.assertEqual(p.annotations[1].surrounds_attribute, 'price')
        self.assertEqual(p.annotations[1].start_index, 3)
        self.assertEqual(p.annotations[1].end_index, 4)


    def test_replacement3(self):
        """A second case of replacement, with annotations, not closed replaced tags"""
        p = _parse_page(TemplatePageParser, LABELLED_PAGE5b)
        self.assertEqual(_tags(p, bool), [u'<select>', u'<option>', u'<option>', u'</select>'])
        self.assertEqual(p.annotations[0].surrounds_attribute, 'price')
        self.assertEqual(p.annotations[0].start_index, 1)
        self.assertEqual(p.annotations[0].end_index, 2)
        self.assertEqual(p.annotations[1].surrounds_attribute, 'price')
        self.assertEqual(p.annotations[1].start_index, 2)
        self.assertEqual(p.annotations[1].end_index, 3)
        
    def test_partial(self):
        """Test partial annotation parsing"""
        p = _parse_page(TemplatePageParser, LABELLED_PAGE6)
        text = p.annotations[0].annotation_text
        self.assertEqual(text.start_text, '')
        self.assertEqual(text.follow_text, 'pounds')
        text = p.annotations[1].annotation_text
        self.assertEqual(text.start_text, "Description: ")
        self.assertEqual(text.follow_text, '')
        
    def test_ignored_partial(self):
        """Test ignored region declared on partial annotation"""
        p = _parse_page(TemplatePageParser, LABELLED_PAGE7)
        self.assertEqual(p.ignored_regions, [(2, 3)])
        
    def test_extra_required(self):
        """Test parsing of extra required attributes"""
        p = _parse_page(TemplatePageParser, LABELLED_PAGE8)
        self.assertEqual(p.extra_required_attrs, ["description"])
    
    def test_variants(self):
        """Test parsing of variant annotations"""
        annotations = _parse_page(TemplatePageParser, LABELLED_PAGE9).annotations
        self.assertEqual(annotations[0].variant_id, None)
        self.assertEqual(annotations[1].variant_id, 1)
        self.assertEqual(annotations[2].variant_id, 1)
        self.assertEqual(annotations[3].variant_id, 2)
        self.assertEqual(annotations[4].variant_id, 2)
        self.assertEqual(annotations[5].variant_id, None)

    def test_variants_in_attributes(self):
        """Test parsing of variant annotations in attributes"""
        annotations = _parse_page(TemplatePageParser, LABELLED_PAGE10).annotations
        self.assertEqual(annotations[0].variant_id, None)
        self.assertEqual(annotations[1].variant_id, 1)
        self.assertEqual(annotations[2].variant_id, 1)
        self.assertEqual(annotations[3].variant_id, 1)
        self.assertEqual(annotations[4].variant_id, 2)
        self.assertEqual(annotations[5].variant_id, 2)
        self.assertEqual(annotations[6].variant_id, 2)
        self.assertEqual(annotations[7].variant_id, None)

    def test_variant_attribute(self):
        """
        Test self closed tag attribute annotated for a variant
        """
        annotations = _parse_page(TemplatePageParser, LABELLED_PAGE11).annotations
        self.assertEqual(annotations[0].variant_id, 1)

    def test_content_attribute(self):
        """
        Test that attribute with name content is unambiguously interpreted
        """
        annotations = _parse_page(TemplatePageParser, LABELLED_PAGE12).annotations
        self.assertEqual(annotations[0].surrounds_attribute, None)
        self.assertEqual(annotations[0].tag_attributes, [("content", "description")])

    def test_content_and_content_attribute(self):
        """
        Test that attribute with name content and the content itself are unambiguously interpreted
        """
        annotations = _parse_page(TemplatePageParser, LABELLED_PAGE13).annotations
        self.assertEqual(annotations[0].surrounds_attribute, 'name')
        self.assertEqual(annotations[0].tag_attributes, [("content", "description")])

    def test_site_pages(self):
        """
        Tests from real pages. More reliable and easy to build for more complicated structures
        """
        for source, annotations in iter_samples('pageparsing'):
            template = HtmlPage(body=source)
            parser = TemplatePageParser(TokenDict())
            parser.feed(template)
            for annotation in parser.annotations:
                test_annotation = annotations.pop(0)
                for s in annotation.__slots__:
                    if s == "tag_attributes":
                        for pair in getattr(annotation, s):
                            self.assertEqual(list(pair), test_annotation[s].pop(0))
                    else:
                        self.assertEqual(getattr(annotation, s), test_annotation[s])
            self.assertEqual(annotations, [])

########NEW FILE########
__FILENAME__ = test_scraper
from unittest import TestCase
from cStringIO import StringIO

from scrapely import Scraper
from scrapely.htmlpage import HtmlPage
from scrapely.tests import iter_samples

class ScraperTest(TestCase):
    
    def _assert_extracted(self, extracted, expected):
        # FIXME: this is a very weak test - we should assert the 
        # extracted data matches, fixing issues that prevent it
        expect_keys = sorted(expected.keys())
        found_keys = sorted(extracted[0].keys())
        self.assertEqual(expect_keys, found_keys)

    def test_extraction(self):

        samples_encoding = 'latin1'
        [(html1, data1), (html2, data2)] = list(iter_samples(
            'scraper_loadstore', html_encoding=samples_encoding))
        sc = Scraper()
        page1 = HtmlPage(body=html1, encoding=samples_encoding)
        sc.train_from_htmlpage(page1, data1)

        page2 = HtmlPage(body=html2, encoding=samples_encoding)
        extracted_data = sc.scrape_page(page2)
        self._assert_extracted(extracted_data, data2)

        # check still works after serialize/deserialize 
        f = StringIO()
        sc.tofile(f)
        f.seek(0)
        sc = Scraper.fromfile(f)
        extracted_data = sc.scrape_page(page2)
        self._assert_extracted(extracted_data, data2)

########NEW FILE########
__FILENAME__ = test_template
from unittest import TestCase

from scrapely.htmlpage import HtmlPage
from scrapely.template import TemplateMaker, FragmentNotFound, \
    FragmentAlreadyAnnotated, best_match
from scrapely.extraction import InstanceBasedLearningExtractor

class TemplateMakerTest(TestCase):

    PAGE = HtmlPage("http://www.example.com", body=u"""
    <html>
      <body>
        <h1>Some title</h1>
        <p>Some text to annotate here</p>
        <h2>Another title</h2>
        <p>Another text to annotate there</p>
        <p>More text with unpaired tag <img />and that's it</p>
      </body>
    </html>
    """)

    def test_annotate_single(self):
        tm = TemplateMaker(self.PAGE)
        tm.annotate('field1', best_match('text to annotate'))
        tpl = tm.get_template()
        ex = InstanceBasedLearningExtractor([(tpl, None)])
        self.assertEqual(ex.extract(self.PAGE)[0],
            [{u'field1': [u'Some text to annotate here']}])

    def test_annotate_multiple(self):
        tm = TemplateMaker(self.PAGE)
        tm.annotate('field1', best_match('text to annotate'), best_match=False)
        tpl = tm.get_template()
        ex = InstanceBasedLearningExtractor([(tpl, None)])
        self.assertEqual(ex.extract(self.PAGE)[0],
            [{u'field1': [u'Some text to annotate here', u'Another text to annotate there']}])

    def test_annotate_ignore_unpaired(self):
        tm = TemplateMaker(self.PAGE)
        tm.annotate('field1', best_match("and that's"), best_match=False)
        tpl = tm.get_template()
        ex = InstanceBasedLearningExtractor([(tpl, None)])
        self.assertEqual(ex.extract(self.PAGE)[0],
            [{u'field1': [u"More text with unpaired tag <img />and that's it"]}])

    def test_annotate_fragment_not_found(self):
        tm = TemplateMaker(self.PAGE)
        self.assertRaises(FragmentNotFound, tm.annotate, 'field1', best_match("missing text"))

    def test_annotate_fragment_already_annotated(self):
        tm = TemplateMaker(self.PAGE)
        tm.annotate('field1', best_match('text to annotate'))
        self.assertRaises(FragmentAlreadyAnnotated, tm.annotate, 'field1', best_match("text to annotate"))

    def test_selected_data(self):
        tm = TemplateMaker(self.PAGE)
        indexes = tm.select(best_match('text to annotate'))
        data = [tm.selected_data(i) for i in indexes]
        self.assertEqual(data, \
            [u'<p>Some text to annotate here</p>', \
            u'<p>Another text to annotate there</p>'])

    def test_annotations(self):
        tm = TemplateMaker(self.PAGE)
        tm.annotate('field1', best_match('text to annotate'), best_match=False)
        annotations = [x[0] for x in tm.annotations()]
        self.assertEqual(annotations,
            [{u'annotations': {u'content': u'field1'}},
             {u'annotations': {u'content': u'field1'}}])

    def test_best_match(self):
        self.assertEquals(self._matches('text to annotate'),
            ['Some text to annotate here', 'Another text to annotate there'])

    def _matches(self, text):
        bm = best_match(text)
        matches = [(bm(f, self.PAGE), f) for f in self.PAGE.parsed_body]
        matches = [x for x in matches if x[0]]
        matches.sort(reverse=True)
        return [self.PAGE.fragment_data(x[1]) for x in matches]

########NEW FILE########
__FILENAME__ = tool
from __future__ import with_statement
import sys, os, re, cmd, shlex, json, optparse, json, urllib, pprint
from cStringIO import StringIO

from scrapely.htmlpage import HtmlPage, page_to_dict, url_to_page
from scrapely.template import TemplateMaker, best_match
from scrapely.extraction import InstanceBasedLearningExtractor

class IblTool(cmd.Cmd):

    prompt = 'scrapely> '

    def __init__(self, filename, **kw):
        self.filename = filename
        cmd.Cmd.__init__(self, **kw)

    def do_ta(self, line):
        """ta <url> [--encoding ENCODING] - add template"""
        opts, (url,) = parse_at(line)
        t = url_to_page(url, opts.encoding)
        templates = self._load_templates()
        templates.append(t)
        self._save_templates(templates)
        print "[%d] %s" % (len(templates) - 1, t.url)

    def do_tl(self, line):
        """tl - list templates"""
        templates = self._load_templates()
        for n, t in enumerate(templates):
            print "[%d] %s" % (n, t.url)

    def do_td(self, template_id):
        """dt <template> - delete template"""
        templates = self._load_templates()
        try:
            del templates[int(template_id)]
            self._save_templates(templates)
            print "template deleted: %s" % template_id
        except IndexError:
            print "template not found: %s" % template_id

    def do_t(self, line):
        """t <template> <text> - test selection text"""
        template_id, criteria = line.split(' ', 1)
        t = self._load_template(template_id)
        criteria = self._parse_criteria(criteria)
        tm = TemplateMaker(t)
        selection = apply_criteria(criteria, tm)
        for n, i in enumerate(selection):
            print "[%d] %r" % (n, remove_annotation(tm.selected_data(i)))

    def do_a(self, line):
        """a <template> <data> [-n number] [-f field]- add or test annotation

        Add a new annotation (if -f is passed) or test what would be annotated
        otherwise
        """
        template_id, criteria = line.split(' ', 1)
        t = self._load_template(template_id)
        criteria = self._parse_criteria(criteria)
        tm = TemplateMaker(t)
        selection = apply_criteria(criteria, tm)
        if criteria.field:
            for index in selection:
                index = selection[0]
                tm.annotate_fragment(index, criteria.field)
                self._save_template(template_id, tm.get_template())
                print "[new] (%s) %r" % (criteria.field,
                    remove_annotation(tm.selected_data(index)))
        else:
            for n, i in enumerate(selection):
                print "[%d] %r" % (n, remove_annotation(tm.selected_data(i)))

    def do_al(self, template_id):
        """al <template> - list annotations"""
        if assert_or_print(template_id, "missing template id"):
            return
        t = self._load_template(template_id)
        tm = TemplateMaker(t)
        for n, (a, i) in enumerate(tm.annotations()):
            print "[%s-%d] (%s) %r" % (template_id, n, a['annotations']['content'],
                remove_annotation(tm.selected_data(i)))

    def do_s(self, url):
        """s <url> - scrape url"""
        templates = self._load_templates()
        if assert_or_print(templates, "no templates available"):
            return
        # fall back to the template encoding if none is specified
        page = url_to_page(url, default_encoding=templates[0].encoding)
        ex = InstanceBasedLearningExtractor((t, None) for t in templates)
        pprint.pprint(ex.extract(page)[0])

    def default(self, line):
        if line == 'EOF':
            if self.use_rawinput:
                print
            return True
        elif line:
            return cmd.Cmd.default(self, line)

    def _load_annotations(self, template_id):
        t = self._load_template(template_id)
        tm = TemplateMaker(t)
        return [x[0] for x in tm.annotations()]

    def _load_template(self, template_id):
        templates = self._load_templates()
        return templates[int(template_id)]

    def _load_templates(self):
        if not os.path.exists(self.filename):
            return []
        with open(self.filename) as f:
            templates = json.load(f)['templates']
            templates = [HtmlPage(t['url'], body=t['body'], encoding=t['encoding']) \
                for t in templates]
            return templates

    def _save_template(self, template_id, template):
        templates = self._load_templates()
        templates[int(template_id)] = template
        self._save_templates(templates)

    def _save_templates(self, templates):
        with open(self.filename, 'w') as f:
            templates = [page_to_dict(t) for t in templates]
            return json.dump({'templates': templates}, f)

    def _parse_criteria(self, criteria_str):
        """Parse the given criteria string and returns a criteria object"""
        p = optparse.OptionParser()
        p.add_option('-f', '--field', help='field to annotate')
        p.add_option('-n', '--number', type="int", help='number of result to select')
        o, a = p.parse_args(shlex.split(criteria_str))

        encoding = getattr(self.stdin, 'encoding', None) or sys.stdin.encoding
        o.text = ' '.join(a).decode(encoding or 'ascii')
        return o


def parse_at(ta_line):
    p = optparse.OptionParser()
    p.add_option('-e', '--encoding', help='page encoding')
    return p.parse_args(shlex.split(ta_line))

def apply_criteria(criteria, tm):
    """Apply the given criteria object to the given template"""
    func = best_match(criteria.text) if criteria.text else lambda x, y: False
    sel = tm.select(func)
    if criteria.number is not None:
        if criteria.number < len(sel):
            sel = [sel[criteria.number]]
        else:
            sel = []
    return sel

def remove_annotation(text):
    return re.sub(u' ?data-scrapy-annotate=".*?"', '', text)

def assert_or_print(condition, text):
    if not condition:
        sys.stderr.write(text + os.linesep)
        return True

def args_to_file(args):
    s = []
    for a in args:
        if ' ' in a:
            if '"' in a:
                a = "'%s'" % a
            else:
                a = '"%s"' % a
        s.append(a)
    return StringIO(' '.join(s))

def main():
    if len(sys.argv) == 1:
        print "usage: %s <scraper_file> [command arg ...]" % sys.argv[0]
        sys.exit(2)

    filename, args = sys.argv[1], sys.argv[2:]
    if args:
        t = IblTool(filename, stdin=args_to_file(args))
        t.prompt = ''
        t.use_rawinput = False
    else:
        t = IblTool(filename)
    t.cmdloop()

if __name__ == '__main__':
    main()

########NEW FILE########
