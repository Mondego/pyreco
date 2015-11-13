__FILENAME__ = annotated_text
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from itertools import groupby
from lxml.sax import saxify, ContentHandler
from .utils import is_blank, shrink_text
from ._compat import to_unicode


_SEMANTIC_TAGS = frozenset((
    "a", "abbr", "acronym", "b", "big", "blink", "blockquote", "cite", "code",
    "dd", "del", "dfn", "dir", "dl", "dt", "em", "h", "h1", "h2", "h3", "h4",
    "h5", "h6", "i", "ins", "kbd", "li", "marquee", "menu", "ol", "pre", "q",
    "s", "samp", "strike", "strong", "sub", "sup", "tt", "u", "ul", "var",
))


class AnnotatedTextHandler(ContentHandler):
    """A class for converting a HTML DOM into annotated text."""

    @classmethod
    def parse(cls, dom):
        """Converts DOM into paragraphs."""
        handler = cls()
        saxify(dom, handler)
        return handler.content

    def __init__(self):
        self._content = []
        self._paragraph = []
        self._dom_path = []

    @property
    def content(self):
        return self._content

    def startElementNS(self, name, qname, attrs):
        namespace, name = name

        if name in _SEMANTIC_TAGS:
            self._dom_path.append(to_unicode(name))

    def endElementNS(self, name, qname):
        namespace, name = name

        if name == "p" and self._paragraph:
            self._append_paragraph(self._paragraph)
        elif name in ("ol", "ul", "pre") and self._paragraph:
            self._append_paragraph(self._paragraph)
            self._dom_path.pop()
        elif name in _SEMANTIC_TAGS:
            self._dom_path.pop()

    def endDocument(self):
        if self._paragraph:
            self._append_paragraph(self._paragraph)

    def _append_paragraph(self, paragraph):
        paragraph = self._process_paragraph(paragraph)
        self._content.append(paragraph)
        self._paragraph = []

    def _process_paragraph(self, paragraph):
        current_paragraph = []

        for annotation, items in groupby(paragraph, key=lambda i: i[1]):
            if annotation and "li" in annotation:
                for text, _ in items:
                    text = shrink_text(text)
                    current_paragraph.append((text, annotation))
            else:
                text = "".join(i[0] for i in items)
                text = shrink_text(text)
                current_paragraph.append((text, annotation))

        return tuple(current_paragraph)

    def characters(self, content):
        if is_blank(content):
            return

        if self._dom_path:
            pair = (content, tuple(sorted(frozenset(self._dom_path))))
        else:
            pair = (content, None)

        self._paragraph.append(pair)

########NEW FILE########
__FILENAME__ = document
# -*- coding: utf8 -*-

"""Generate a clean nice starting html document to process for an article."""

from __future__ import absolute_import

import re
import logging
import chardet

from lxml.etree import (
    tounicode,
    XMLSyntaxError,
)
from lxml.html import (
    document_fromstring,
    HTMLParser,
)

from ._compat import (
    to_bytes,
    to_unicode,
    unicode,
    unicode_compatible,
)
from .utils import (
    cached_property,
    ignored,
)


logger = logging.getLogger("breadability")


TAG_MARK_PATTERN = re.compile(to_bytes(r"</?[^>]*>\s*"))
UTF8_PARSER = HTMLParser(encoding="utf8")
CHARSET_META_TAG_PATTERN = re.compile(
    br"""<meta[^>]+charset=["']?([^'"/>\s]+)""",
    re.IGNORECASE
)


def decode_html(html):
    """
    Converts bytes stream containing an HTML page into Unicode.
    Tries to guess character encoding from meta tag of by "chardet" library.
    """
    if isinstance(html, unicode):
        return html

    match = CHARSET_META_TAG_PATTERN.search(html)
    if match:
        declared_encoding = match.group(1).decode("ASCII")
        # proceed unknown encoding as if it wasn't found at all
        with ignored(LookupError):
            return html.decode(declared_encoding, "ignore")

    # try to enforce UTF-8 firstly
    with ignored(UnicodeDecodeError):
        return html.decode("utf8")

    text = TAG_MARK_PATTERN.sub(to_bytes(" "), html)
    diff = text.decode("utf8", "ignore").encode("utf8")
    sizes = len(diff), len(text)

    # 99% of text is UTF-8
    if abs(len(text) - len(diff)) < max(sizes) * 0.01:
        return html.decode("utf8", "ignore")

    # try detect encoding
    encoding = "utf8"
    encoding_detector = chardet.detect(text)
    if encoding_detector["encoding"]:
        encoding = encoding_detector["encoding"]

    return html.decode(encoding, "ignore")


BREAK_TAGS_PATTERN = re.compile(
    to_unicode(r"(?:<\s*[bh]r[^>]*>\s*)+"),
    re.IGNORECASE
)


def convert_breaks_to_paragraphs(html):
    """
    Converts <hr> tag and multiple <br> tags into paragraph.
    """
    logger.debug("Converting multiple <br> & <hr> tags into <p>.")

    return BREAK_TAGS_PATTERN.sub(_replace_break_tags, html)


def _replace_break_tags(match):
    tags = match.group()

    if to_unicode("<hr") in tags:
        return to_unicode("</p><p>")
    elif tags.count(to_unicode("<br")) > 1:
        return to_unicode("</p><p>")
    else:
        return tags


def build_document(html_content, base_href=None):
    """Requires that the `html_content` not be None"""
    assert html_content is not None

    if isinstance(html_content, unicode):
        html_content = html_content.encode("utf8", "xmlcharrefreplace")

    try:
        document = document_fromstring(html_content, parser=UTF8_PARSER)
    except XMLSyntaxError:
        raise ValueError("Failed to parse document contents.")

    if base_href:
        document.make_links_absolute(base_href, resolve_base_href=True)
    else:
        document.resolve_base_href()

    return document


@unicode_compatible
class OriginalDocument(object):
    """The original document to process."""

    def __init__(self, html, url=None):
        self._html = html
        self._url = url

    @property
    def url(self):
        """Source URL of HTML document."""
        return self._url

    def __unicode__(self):
        """Renders the document as a string."""
        return tounicode(self.dom)

    @cached_property
    def dom(self):
        """Parsed HTML document from the input."""
        html = self._html
        if not isinstance(html, unicode):
            html = decode_html(html)

        html = convert_breaks_to_paragraphs(html)
        document = build_document(html, self._url)

        return document

    @cached_property
    def links(self):
        """Links within the document."""
        return self.dom.findall(".//a")

    @cached_property
    def title(self):
        """Title attribute of the parsed document."""
        title_element = self.dom.find(".//title")
        if title_element is None or title_element.text is None:
            return ""
        else:
            return title_element.text.strip()

########NEW FILE########
__FILENAME__ = readable
# -*- coding: utf8 -*-

from __future__ import absolute_import

import logging

from copy import deepcopy
from operator import attrgetter
from pprint import PrettyPrinter
from lxml.html.clean import Cleaner
from lxml.etree import tounicode, tostring
from lxml.html import fragment_fromstring, fromstring

from .document import OriginalDocument
from .annotated_text import AnnotatedTextHandler
from .scoring import (
    get_class_weight,
    get_link_density,
    is_unlikely_node,
    score_candidates,
)
from .utils import cached_property, shrink_text


html_cleaner = Cleaner(
    scripts=True, javascript=True, comments=True,
    style=True, links=True, meta=False, add_nofollow=False,
    page_structure=False, processing_instructions=True,
    embedded=False, frames=False, forms=False,
    annoying_tags=False, remove_tags=None, kill_tags=("noscript", "iframe"),
    remove_unknown_tags=False, safe_attrs_only=False)


SCORABLE_TAGS = ("div", "p", "td", "pre", "article")
ANNOTATION_TAGS = (
    "a", "abbr", "acronym", "b", "big", "blink", "blockquote", "br", "cite",
    "code", "dd", "del", "dir", "dl", "dt", "em", "font", "h", "h1", "h2",
    "h3", "h4", "h5", "h6", "hr", "i", "ins", "kbd", "li", "marquee", "menu",
    "ol", "p", "pre", "q", "s", "samp", "span", "strike", "strong", "sub",
    "sup", "tt", "u", "ul", "var",
)
NULL_DOCUMENT = """
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html;charset=UTF-8">
    </head>
    <body>
    </body>
</html>
"""

logger = logging.getLogger("breadability")


def ok_embedded_video(node):
    """Check if this embed/video is an ok one to count."""
    good_keywords = ('youtube', 'blip.tv', 'vimeo')

    node_str = tounicode(node)
    for key in good_keywords:
        if key in node_str:
            return True

    return False


def build_base_document(dom, return_fragment=True):
    """
    Builds a base document with the body as root.

    :param dom: Parsed lxml tree (Document Object Model).
    :param bool return_fragment: If True only <div> fragment is returned.
        Otherwise full HTML document is returned.
    """
    body_element = dom.find(".//body")

    if body_element is None:
        fragment = fragment_fromstring('<div id="readabilityBody"/>')
        fragment.append(dom)
    else:
        body_element.tag = "div"
        body_element.set("id", "readabilityBody")
        fragment = body_element

    return document_from_fragment(fragment, return_fragment)


def build_error_document(dom, return_fragment=True):
    """
    Builds an empty erorr document with the body as root.

    :param bool return_fragment: If True only <div> fragment is returned.
        Otherwise full HTML document is returned.
    """
    fragment = fragment_fromstring(
        '<div id="readabilityBody" class="parsing-error"/>')

    return document_from_fragment(fragment, return_fragment)


def document_from_fragment(fragment, return_fragment):
    if return_fragment:
        document = fragment
    else:
        document = fromstring(NULL_DOCUMENT)
        body_element = document.find(".//body")
        body_element.append(fragment)

    document.doctype = "<!DOCTYPE html>"
    return document


def check_siblings(candidate_node, candidate_list):
    """
    Looks through siblings for content that might also be related.
    Things like preambles, content split by ads that we removed, etc.
    """
    candidate_css = candidate_node.node.get("class")
    potential_target = candidate_node.content_score * 0.2
    sibling_target_score = potential_target if potential_target > 10 else 10
    parent = candidate_node.node.getparent()
    siblings = parent.getchildren() if parent is not None else []

    for sibling in siblings:
        append = False
        content_bonus = 0

        if sibling is candidate_node.node:
            append = True

        # Give a bonus if sibling nodes and top candidates have the example
        # same class name
        if candidate_css and sibling.get("class") == candidate_css:
            content_bonus += candidate_node.content_score * 0.2

        if sibling in candidate_list:
            adjusted_score = \
                candidate_list[sibling].content_score + content_bonus

            if adjusted_score >= sibling_target_score:
                append = True

        if sibling.tag == "p":
            link_density = get_link_density(sibling)
            content = sibling.text_content()
            content_length = len(content)

            if content_length > 80 and link_density < 0.25:
                append = True
            elif content_length < 80 and link_density == 0:
                if ". " in content:
                    append = True

        if append:
            logger.debug(
                "Sibling appended: %s %r", sibling.tag, sibling.attrib)
            if sibling.tag not in ("div", "p"):
                # We have a node that isn't a common block level element, like
                # a form or td tag. Turn it into a div so it doesn't get
                # filtered out later by accident.
                sibling.tag = "div"

            if candidate_node.node != sibling:
                candidate_node.node.append(sibling)

    return candidate_node


def clean_document(node):
    """Cleans up the final document we return as the readable article."""
    if node is None or len(node) == 0:
        return None

    logger.debug("\n\n-------------- CLEANING DOCUMENT -----------------")
    to_drop = []

    for n in node.iter():
        # clean out any in-line style properties
        if "style" in n.attrib:
            n.set("style", "")

        # remove embended objects unless it's wanted video
        if n.tag in ("object", "embed") and not ok_embedded_video(n):
            logger.debug("Dropping node %s %r", n.tag, n.attrib)
            to_drop.append(n)

        # clean headings with bad css or high link density
        if n.tag in ("h1", "h2", "h3", "h4") and get_class_weight(n) < 0:
            logger.debug("Dropping <%s>, it's insignificant", n.tag)
            to_drop.append(n)

        if n.tag in ("h3", "h4") and get_link_density(n) > 0.33:
            logger.debug("Dropping <%s>, it's insignificant", n.tag)
            to_drop.append(n)

        # drop block element without content and children
        if n.tag in ("div", "p"):
            text_content = shrink_text(n.text_content())
            if len(text_content) < 5 and not n.getchildren():
                logger.debug(
                    "Dropping %s %r without content.", n.tag, n.attrib)
                to_drop.append(n)

        # finally try out the conditional cleaning of the target node
        if clean_conditionally(n):
            to_drop.append(n)

    drop_nodes_with_parents(to_drop)

    return node


def drop_nodes_with_parents(nodes):
    for node in nodes:
        if node.getparent() is None:
            continue

        node.drop_tree()
        logger.debug(
            "Dropped node with parent %s %r %s",
            node.tag,
            node.attrib,
            node.text_content()[:50]
        )


def clean_conditionally(node):
    """Remove the clean_el if it looks like bad content based on rules."""
    if node.tag not in ('form', 'table', 'ul', 'div', 'p'):
        return  # this is not the tag we are looking for

    weight = get_class_weight(node)
    # content_score = LOOK up the content score for this node we found
    # before else default to 0
    content_score = 0

    if weight + content_score < 0:
        logger.debug('Dropping conditional node')
        logger.debug('Weight + score < 0')
        return True

    commas_count = node.text_content().count(',')
    if commas_count < 10:
        logger.debug(
            "There are %d commas so we're processing more.", commas_count)

        # If there are not very many commas, and the number of
        # non-paragraph elements is more than paragraphs or other ominous
        # signs, remove the element.
        p = len(node.findall('.//p'))
        img = len(node.findall('.//img'))
        li = len(node.findall('.//li')) - 100
        inputs = len(node.findall('.//input'))

        embed = 0
        embeds = node.findall('.//embed')
        for e in embeds:
            if ok_embedded_video(e):
                embed += 1
        link_density = get_link_density(node)
        content_length = len(node.text_content())

        remove_node = False

        if li > p and node.tag != 'ul' and node.tag != 'ol':
            logger.debug('Conditional drop: li > p and not ul/ol')
            remove_node = True
        elif inputs > p / 3.0:
            logger.debug('Conditional drop: inputs > p/3.0')
            remove_node = True
        elif content_length < 25 and (img == 0 or img > 2):
            logger.debug('Conditional drop: len < 25 and 0/>2 images')
            remove_node = True
        elif weight < 25 and link_density > 0.2:
            logger.debug('Conditional drop: weight small (%f) and link is dense (%f)', weight, link_density)
            remove_node = True
        elif weight >= 25 and link_density > 0.5:
            logger.debug('Conditional drop: weight big but link heavy')
            remove_node = True
        elif (embed == 1 and content_length < 75) or embed > 1:
            logger.debug(
                'Conditional drop: embed w/o much content or many embed')
            remove_node = True

        if remove_node:
            logger.debug('Node will be removed: %s %r %s', node.tag, node.attrib, node.text_content()[:30])

        return remove_node

    return False  # nope, don't remove anything


def prep_article(doc):
    """Once we've found our target article we want to clean it up.

    Clean out:
    - inline styles
    - forms
    - strip empty <p>
    - extra tags
    """
    return clean_document(doc)


def find_candidates(document):
    """
    Finds cadidate nodes for the readable version of the article.

    Here's we're going to remove unlikely nodes, find scores on the rest,
    clean up and return the final best match.
    """
    nodes_to_score = set()
    should_remove = set()

    for node in document.iter():
        if is_unlikely_node(node):
            logger.debug(
                "We should drop unlikely: %s %r", node.tag, node.attrib)
            should_remove.add(node)
        elif is_bad_link(node):
            logger.debug(
                "We should drop bad link: %s %r", node.tag, node.attrib)
            should_remove.add(node)
        elif node.tag in SCORABLE_TAGS:
            nodes_to_score.add(node)

    return score_candidates(nodes_to_score), should_remove


def is_bad_link(node):
    """
    Helper to determine if the node is link that is useless.

    We've hit articles with many multiple links that should be cleaned out
    because they're just there to pollute the space. See tests for examples.
    """
    if node.tag != "a":
        return False

    name = node.get("name")
    href = node.get("href")
    if name and not href:
        return True

    if href:
        href_parts = href.split("#")
        if len(href_parts) == 2 and len(href_parts[1]) > 25:
            return True

    return False


class Article(object):
    """Parsed readable object"""

    def __init__(self, html, url=None, return_fragment=True):
        """
        Create the Article we're going to use.

        :param html: The string of HTML we're going to parse.
        :param url: The url so we can adjust the links to still work.
        :param return_fragment: Should we return a <div> fragment or
            a full <html> document.
        """
        self._original_document = OriginalDocument(html, url=url)
        self._return_fragment = return_fragment

    def __str__(self):
        return tostring(self._readable())

    def __unicode__(self):
        return tounicode(self._readable())

    @cached_property
    def dom(self):
        """Parsed lxml tree (Document Object Model) of the given html."""
        try:
            dom = self._original_document.dom
            # cleaning doesn't return, just wipes in place
            html_cleaner(dom)
            return leaf_div_elements_into_paragraphs(dom)
        except ValueError:
            return None

    @cached_property
    def candidates(self):
        """Generates list of candidates from the DOM."""
        dom = self.dom
        if dom is None or len(dom) == 0:
            return None

        candidates, unlikely_candidates = find_candidates(dom)
        drop_nodes_with_parents(unlikely_candidates)

        return candidates

    @cached_property
    def main_text(self):
        dom = deepcopy(self.readable_dom).get_element_by_id("readabilityBody")
        return AnnotatedTextHandler.parse(dom)

    @cached_property
    def readable(self):
        return tounicode(self.readable_dom)

    @cached_property
    def readable_dom(self):
        return self._readable()

    def _readable(self):
        """The readable parsed article"""
        if not self.candidates:
            logger.info("No candidates found in document.")
            return self._handle_no_candidates()

        # right now we return the highest scoring candidate content
        best_candidates = sorted(
            (c for c in self.candidates.values()),
            key=attrgetter("content_score"), reverse=True)

        printer = PrettyPrinter(indent=2)
        logger.debug(printer.pformat(best_candidates))

        # since we have several candidates, check the winner's siblings
        # for extra content
        winner = best_candidates[0]
        updated_winner = check_siblings(winner, self.candidates)
        updated_winner.node = prep_article(updated_winner.node)
        if updated_winner.node is not None:
            dom = build_base_document(
                updated_winner.node, self._return_fragment)
        else:
            logger.info(
                'Had candidates but failed to find a cleaned winning DOM.')
            dom = self._handle_no_candidates()

        return self._remove_orphans(dom.get_element_by_id("readabilityBody"))

    def _remove_orphans(self, dom):
        for node in dom.iterdescendants():
            if len(node) == 1 and tuple(node)[0].tag == node.tag:
                node.drop_tag()

        return dom

    def _handle_no_candidates(self):
        """
        If we fail to find a good candidate we need to find something else.
        """
        # since we've not found a good candidate we're should help this
        if self.dom is not None and len(self.dom):
            dom = prep_article(self.dom)
            dom = build_base_document(dom, self._return_fragment)
            return self._remove_orphans(
                dom.get_element_by_id("readabilityBody"))
        else:
            logger.info("No document to use.")
            return build_error_document(self._return_fragment)


def leaf_div_elements_into_paragraphs(document):
    """
    Turn some block elements that don't have children block level
    elements into <p> elements.

    Since we can't change the tree as we iterate over it, we must do this
    before we process our document.
    """
    for element in document.iter(tag="div"):
        child_tags = tuple(n.tag for n in element.getchildren())
        if "div" not in child_tags and "p" not in child_tags:
            logger.debug(
                "Changing leaf block element <%s> into <p>", element.tag)
            element.tag = "p"

    return document

########NEW FILE########
__FILENAME__ = scoring
# -*- coding: utf8 -*-

"""Handle dealing with scoring nodes and content for our parsing."""

from __future__ import absolute_import
from __future__ import division, print_function

import re
import logging

from hashlib import md5
from lxml.etree import tostring
from ._compat import to_bytes
from .utils import normalize_whitespace


# A series of sets of attributes we check to help in determining if a node is
# a potential candidate or not.
CLS_UNLIKELY = re.compile(
    "combx|comment|community|disqus|extra|foot|header|menu|remark|rss|"
    "shoutbox|sidebar|sponsor|ad-break|agegate|pagination|pager|perma|popup|"
    "tweet|twitter|social|breadcrumb",
    re.IGNORECASE
)
CLS_MAYBE = re.compile(
    "and|article|body|column|main|shadow|entry",
    re.IGNORECASE
)
CLS_WEIGHT_POSITIVE = re.compile(
    "article|body|content|entry|main|page|pagination|post|text|blog|story",
    re.IGNORECASE
)
CLS_WEIGHT_NEGATIVE = re.compile(
    "combx|comment|com-|contact|foot|footer|footnote|head|masthead|media|meta|"
    "outbrain|promo|related|scroll|shoutbox|sidebar|sponsor|shopping|tags|"
    "tool|widget",
    re.IGNORECASE
)

logger = logging.getLogger("breadability")


def check_node_attributes(pattern, node, *attributes):
    """
    Searches match in attributes against given pattern and if
    finds the match against any of them returns True.
    """
    for attribute_name in attributes:
        attribute = node.get(attribute_name)
        if attribute is not None and pattern.search(attribute):
            return True

    return False


def generate_hash_id(node):
    """
    Generates a hash_id for the node in question.

    :param node: lxml etree node
    """
    try:
        content = tostring(node)
    except Exception:
        logger.exception("Generating of hash failed")
        content = to_bytes(repr(node))

    hash_id = md5(content).hexdigest()
    return hash_id[:8]


def get_link_density(node, node_text=None):
    """
    Computes the ratio for text in given node and text in links
    contained in the node. It is computed from number of
    characters in the texts.

    :parameter Element node:
        HTML element in which links density is computed.
    :parameter string node_text:
        Text content of given node if it was obtained before.
    :returns float:
        Returns value of computed 0 <= density <= 1, where 0 means
        no links and 1 means that node contains only links.
    """
    if node_text is None:
        node_text = node.text_content()
    node_text = normalize_whitespace(node_text.strip())

    text_length = len(node_text)
    if text_length == 0:
        return 0.0

    links_length = sum(map(_get_normalized_text_length, node.findall(".//a")))
    # Give 50 bonus chars worth of length for each img.
    # Tweaking this 50 down a notch should help if we hit false positives.
    img_bonuses = 50 * len(node.findall(".//img"))
    links_length = max(0, links_length - img_bonuses)

    return links_length / text_length


def _get_normalized_text_length(node):
    return len(normalize_whitespace(node.text_content().strip()))


def get_class_weight(node):
    """
    Computes weight of element according to its class/id.

    We're using sets to help efficiently check for existence of matches.
    """
    weight = 0

    if check_node_attributes(CLS_WEIGHT_NEGATIVE, node, "class"):
        weight -= 25
    if check_node_attributes(CLS_WEIGHT_POSITIVE, node, "class"):
        weight += 25

    if check_node_attributes(CLS_WEIGHT_NEGATIVE, node, "id"):
        weight -= 25
    if check_node_attributes(CLS_WEIGHT_POSITIVE, node, "id"):
        weight += 25

    return weight


def is_unlikely_node(node):
    """
    Short helper for checking unlikely status.

    If the class or id are in the unlikely list, and there's not also a
    class/id in the likely list then it might need to be removed.
    """
    unlikely = check_node_attributes(CLS_UNLIKELY, node, "class", "id")
    maybe = check_node_attributes(CLS_MAYBE, node, "class", "id")

    return bool(unlikely and not maybe and node.tag != "body")


def score_candidates(nodes):
    """Given a list of potential nodes, find some initial scores to start"""
    MIN_HIT_LENTH = 25
    candidates = {}

    for node in nodes:
        logger.debug("* Scoring candidate %s %r", node.tag, node.attrib)

        # if the node has no parent it knows of then it ends up creating a
        # body & html tag to parent the html fragment
        parent = node.getparent()
        if parent is None:
            logger.debug("Skipping candidate - parent node is 'None'.")
            continue

        grand = parent.getparent()
        if grand is None:
            logger.debug("Skipping candidate - grand parent node is 'None'.")
            continue

        # if paragraph is < `MIN_HIT_LENTH` characters don't even count it
        inner_text = node.text_content().strip()
        if len(inner_text) < MIN_HIT_LENTH:
            logger.debug(
                "Skipping candidate - inner text < %d characters.",
                MIN_HIT_LENTH)
            continue

        # initialize readability data for the parent
        # add parent node if it isn't in the candidate list
        if parent not in candidates:
            candidates[parent] = ScoredNode(parent)

        if grand not in candidates:
            candidates[grand] = ScoredNode(grand)

        # add a point for the paragraph itself as a base
        content_score = 1

        if inner_text:
            # add 0.25 points for any commas within this paragraph
            commas_count = inner_text.count(",")
            content_score += commas_count * 0.25
            logger.debug("Bonus points for %d commas.", commas_count)

            # subtract 0.5 points for each double quote within this paragraph
            double_quotes_count = inner_text.count('"')
            content_score += double_quotes_count * -0.5
            logger.debug(
                "Penalty points for %d double-quotes.", double_quotes_count)

            # for every 100 characters in this paragraph, add another point
            # up to 3 points
            length_points = len(inner_text) / 100
            content_score += min(length_points, 3.0)
            logger.debug("Bonus points for length of text: %f", length_points)

        # add the score to the parent
        logger.debug(
            "Bonus points for parent %s %r with score %f: %f",
            parent.tag, parent.attrib, candidates[parent].content_score,
            content_score)
        candidates[parent].content_score += content_score
        # the grand node gets half
        logger.debug(
            "Bonus points for grand %s %r with score %f: %f",
            grand.tag, grand.attrib, candidates[grand].content_score,
            content_score / 2.0)
        candidates[grand].content_score += content_score / 2.0

        if node not in candidates:
            candidates[node] = ScoredNode(node)
        candidates[node].content_score += content_score

    for candidate in candidates.values():
        adjustment = 1.0 - get_link_density(candidate.node)
        candidate.content_score *= adjustment
        logger.debug(
            "Link density adjustment for %s %r: %f",
            candidate.node.tag, candidate.node.attrib, adjustment)

    return candidates


class ScoredNode(object):
    """
    We need Scored nodes we use to track possible article matches

    We might have a bunch of these so we use __slots__ to keep memory usage
    down.
    """
    __slots__ = ('node', 'content_score')

    def __init__(self, node):
        """Given node, set an initial score and weigh based on css and id"""
        self.node = node
        self.content_score = 0

        if node.tag in ('div', 'article'):
            self.content_score = 5
        if node.tag in ('pre', 'td', 'blockquote'):
            self.content_score = 3

        if node.tag in ('address', 'ol', 'ul', 'dl', 'dd', 'dt', 'li', 'form'):
            self.content_score = -3
        if node.tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'th'):
            self.content_score = -5

        self.content_score += get_class_weight(node)

    @property
    def hash_id(self):
        return generate_hash_id(self.node)

    def __repr__(self):
        if self.node is None:
            return "<NullScoredNode with score {2:0.1F}>" % self.content_score

        return "<ScoredNode {0} {1}: {2:0.1F}>".format(
            self.node.tag,
            self.node.attrib,
            self.content_score
        )

########NEW FILE########
__FILENAME__ = client
# -*- coding: utf8 -*-

"""
A fast python port of arc90's readability tool

Usage:
    breadability [options] <resource>
    breadability --version
    breadability --help

Arguments:
  <resource>      URL or file path to process in readable form.

Options:
  -f, --fragment  Output html fragment by default.
  -b, --browser   Open the parsed content in your web browser.
  -d, --debug     Output the detailed scoring information for debugging
                  parsing.
  -v, --verbose   Increase logging verbosity to DEBUG.
  --version       Display program's version number and exit.
  -h, --help      Display this help message and exit.
"""

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals


import logging
import locale
import webbrowser

from tempfile import NamedTemporaryFile
from docopt import docopt
from .. import __version__
from .._compat import urllib
from ..readable import Article


HEADERS = {
    "User-Agent": 'breadability/{version} ({url})'.format(
        url="https://github.com/bookieio/breadability",
        version=__version__
    )
}


def parse_args():
    return docopt(__doc__, version=__version__)


def main():
    args = parse_args()
    logger = logging.getLogger("breadability")

    if args["--verbose"]:
        logger.setLevel(logging.DEBUG)

    resource = args["<resource>"]
    if resource.startswith("www"):
        resource = "http://" + resource

    url = None
    if resource.startswith("http://") or resource.startswith("https://"):
        url = resource

        request = urllib.Request(url, headers=HEADERS)
        response = urllib.urlopen(request)
        content = response.read()
        response.close()
    else:
        with open(resource, "r") as file:
            content = file.read()

    document = Article(content, url=url, return_fragment=args["--fragment"])
    if args["--browser"]:
        html_file = NamedTemporaryFile(mode="wb", suffix=".html", delete=False)

        content = document.readable.encode("utf8")
        html_file.write(content)
        html_file.close()

        webbrowser.open(html_file.name)
    else:
        encoding = locale.getpreferredencoding()
        content = document.readable.encode(encoding)
        print(content)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_helper
# -*- coding: utf8 -*-

"""
Helper to generate a new set of article test files for breadability.

Usage:
    breadability_test --name <name> <url>
    breadability_test --version
    breadability_test --help

Arguments:
  <url>                   The url of content to fetch for the article.html

Options:
  -n <name>, --name=<name>  Name of the test directory.
  --version                 Show program's version number and exit.
  -h, --help                Show this help message and exit.
"""

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from os import mkdir
from os.path import join, dirname, pardir, exists as path_exists
from docopt import docopt
from .. import __version__
from .._compat import to_unicode, urllib


TEST_PATH = join(
    dirname(__file__),
    pardir, pardir,
    "tests/test_articles"
)

TEST_TEMPLATE = '''# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from os.path import join, dirname
from breadability.readable import Article
from ...compat import unittest


class TestArticle(unittest.TestCase):
    """
    Test the scoring and parsing of the article from URL below:
    %(source_url)s
    """

    def setUp(self):
        """Load up the article for us"""
        article_path = join(dirname(__file__), "article.html")
        with open(article_path, "rb") as file:
            self.document = Article(file.read(), "%(source_url)s")

    def tearDown(self):
        """Drop the article"""
        self.document = None

    def test_parses(self):
        """Verify we can parse the document."""
        self.assertIn('id="readabilityBody"', self.document.readable)

    def test_content_exists(self):
        """Verify that some content exists."""
        self.assertIn("#&@#&@#&@", self.document.readable)

    def test_content_does_not_exist(self):
        """Verify we cleaned out some content that shouldn't exist."""
        self.assertNotIn("", self.document.readable)
'''


def parse_args():
    return docopt(__doc__, version=__version__)


def make_test_directory(name):
    """Generates a new directory for tests."""
    directory_name = "test_" + name.replace(" ", "_")
    directory_path = join(TEST_PATH, directory_name)

    if not path_exists(directory_path):
        mkdir(directory_path)

    return directory_path


def make_test_files(directory_path, url):
    init_file = join(directory_path, "__init__.py")
    open(init_file, "a").close()

    data = TEST_TEMPLATE % {
        "source_url": to_unicode(url)
    }

    test_file = join(directory_path, "test_article.py")
    with open(test_file, "w") as file:
        file.write(data)


def fetch_article(directory_path, url):
    """Get the content of the url and make it the article.html"""
    opener = urllib.build_opener()
    opener.addheaders = [("Accept-Charset", "utf-8")]

    response = opener.open(url)
    html_data = response.read()
    response.close()

    path = join(directory_path, "article.html")
    with open(path, "wb") as file:
        file.write(html_data)


def main():
    """Run the script."""
    args = parse_args()
    directory = make_test_directory(args["--name"])
    make_test_files(directory, args["<url>"])
    fetch_article(directory, args["<url>"])


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import re

try:
    from contextlib import ignored
except ImportError:
    from contextlib import contextmanager

    @contextmanager
    def ignored(*exceptions):
        try:
            yield
        except tuple(exceptions):
            pass


MULTIPLE_WHITESPACE_PATTERN = re.compile(r"\s+", re.UNICODE)


def is_blank(text):
    """
    Returns ``True`` if string contains only whitespace characters
    or is empty. Otherwise ``False`` is returned.
    """
    return not text or text.isspace()


def shrink_text(text):
    return normalize_whitespace(text.strip())


def normalize_whitespace(text):
    """
    Translates multiple whitespace into single space character.
    If there is at least one new line character chunk is replaced
    by single LF (Unix new line) character.
    """
    return MULTIPLE_WHITESPACE_PATTERN.sub(_replace_whitespace, text)


def _replace_whitespace(match):
    text = match.group()

    if "\n" in text or "\r" in text:
        return "\n"
    else:
        return " "


def cached_property(getter):
    """
    Decorator that converts a method into memoized property.
    The decorator works as expected only for classes with
    attribute '__dict__' and immutable properties.
    """
    def decorator(self):
        key = "_cached_property_" + getter.__name__

        if not hasattr(self, key):
            setattr(self, key, getter(self))

        return getattr(self, key)

    decorator.__name__ = getter.__name__
    decorator.__module__ = getter.__module__
    decorator.__doc__ = getter.__doc__

    return property(decorator)

########NEW FILE########
__FILENAME__ = _compat
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from sys import version_info


PY3 = version_info[0] == 3


if PY3:
    bytes = bytes
    unicode = str
else:
    bytes = str
    unicode = unicode
string_types = (bytes, unicode,)


try:
    # Assert to hush pyflakes about the unused import. This is a _compat
    # module and we expect this to aid in other code importing urllib.
    import urllib2 as urllib
    assert urllib
except ImportError:
    import urllib.request as urllib
    assert urllib


def unicode_compatible(cls):
    """
    Decorator for unicode compatible classes. Method ``__unicode__``
    has to be implemented to work decorator as expected.
    """
    if PY3:
        cls.__str__ = cls.__unicode__
        cls.__bytes__ = lambda self: self.__str__().encode("utf8")
    else:
        cls.__str__ = lambda self: self.__unicode__().encode("utf8")

    return cls


def to_string(object):
    return to_unicode(object) if PY3 else to_bytes(object)


def to_bytes(object):
    try:
        if isinstance(object, bytes):
            return object
        elif isinstance(object, unicode):
            return object.encode("utf8")
        else:
            # try encode instance to bytes
            return instance_to_bytes(object)
    except UnicodeError:
        # recover from codec error and use 'repr' function
        return to_bytes(repr(object))


def to_unicode(object):
    try:
        if isinstance(object, unicode):
            return object
        elif isinstance(object, bytes):
            return object.decode("utf8")
        else:
            # try decode instance to unicode
            return instance_to_unicode(object)
    except UnicodeError:
        # recover from codec error and use 'repr' function
        return to_unicode(repr(object))


def instance_to_bytes(instance):
    if PY3:
        if hasattr(instance, "__bytes__"):
            return bytes(instance)
        elif hasattr(instance, "__str__"):
            return unicode(instance).encode("utf8")
    else:
        if hasattr(instance, "__str__"):
            return bytes(instance)
        elif hasattr(instance, "__unicode__"):
            return unicode(instance).encode("utf8")

    return to_bytes(repr(instance))


def instance_to_unicode(instance):
    if PY3:
        if hasattr(instance, "__str__"):
            return unicode(instance)
        elif hasattr(instance, "__bytes__"):
            return bytes(instance).decode("utf8")
    else:
        if hasattr(instance, "__unicode__"):
            return unicode(instance)
        elif hasattr(instance, "__str__"):
            return bytes(instance).decode("utf8")

    return to_unicode(repr(instance))

########NEW FILE########
__FILENAME__ = compat
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

try:
    import unittest2 as unittest
except ImportError:
    import unittest

########NEW FILE########
__FILENAME__ = test_annotated_text
# -*- coding: utf8 -*-

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals
)

from lxml.html import fragment_fromstring, document_fromstring
from breadability.readable import Article
from breadability.annotated_text import AnnotatedTextHandler
from .compat import unittest
from .utils import load_snippet, load_article


class TestAnnotatedText(unittest.TestCase):
    def test_simple_document(self):
        dom = fragment_fromstring("<p>This is\n\tsimple\ttext.</p>")
        annotated_text = AnnotatedTextHandler.parse(dom)

        expected = [
            (
                ("This is\nsimple text.", None),
            ),
        ]
        self.assertEqual(annotated_text, expected)

    def test_empty_paragraph(self):
        dom = fragment_fromstring("<div><p>Paragraph <p>\t  \n</div>")
        annotated_text = AnnotatedTextHandler.parse(dom)

        expected = [
            (
                ("Paragraph", None),
            ),
        ]
        self.assertEqual(annotated_text, expected)

    def test_multiple_paragraphs(self):
        dom = fragment_fromstring("<div><p> 1 first<p> 2\tsecond <p>3\rthird   </div>")
        annotated_text = AnnotatedTextHandler.parse(dom)

        expected = [
            (
                ("1 first", None),
            ),
            (
                ("2 second", None),
            ),
            (
                ("3\nthird", None),
            ),
        ]
        self.assertEqual(annotated_text, expected)

    def test_single_annotation(self):
        dom = fragment_fromstring("<div><p> text <em>emphasis</em> <p> last</div>")
        annotated_text = AnnotatedTextHandler.parse(dom)

        expected = [
            (
                ("text", None),
                ("emphasis", ("em",)),
            ),
            (
                ("last", None),
            ),
        ]
        self.assertEqual(annotated_text, expected)

    def test_recursive_annotation(self):
        dom = fragment_fromstring("<div><p> text <em><i><em>emphasis</em></i></em> <p> last</div>")
        annotated_text = AnnotatedTextHandler.parse(dom)

        expected = [
            (
                ("text", None),
                ("emphasis", ("em", "i")),
            ),
            (
                ("last", None),
            ),
        ]
        self.assertEqual(annotated_text, expected)

    def test_annotations_without_explicit_paragraph(self):
        dom = fragment_fromstring("<div>text <strong>emphasis</strong>\t<b>hmm</b> </div>")
        annotated_text = AnnotatedTextHandler.parse(dom)

        expected = [
            (
                ("text", None),
                ("emphasis", ("strong",)),
                ("hmm", ("b",)),
            ),
        ]
        self.assertEqual(annotated_text, expected)

    def test_process_paragraph_with_chunked_text(self):
        handler = AnnotatedTextHandler()
        paragraph = handler._process_paragraph([
            (" 1", ("b", "del")),
            (" 2", ("b", "del")),
            (" 3", None),
            (" 4", None),
            (" 5", None),
            (" 6", ("em",)),
        ])

        expected = (
            ("1 2", ("b", "del")),
            ("3 4 5", None),
            ("6", ("em",)),
        )
        self.assertEqual(paragraph, expected)

    def test_include_heading(self):
        dom = document_fromstring(load_snippet("h1_and_2_paragraphs.html"))
        annotated_text = AnnotatedTextHandler.parse(dom.find("body"))

        expected = [
            (
                ('Nadpis H1, ktorý chce byť prvý s textom ale predbehol ho "title"', ("h1",)),
                ("Toto je prvý odstavec a to je fajn.", None),
            ),
            (
                ("Tento text je tu aby vyplnil prázdne miesto v srdci súboru.\nAj súbory majú predsa city.", None),
            ),
        ]
        self.assertSequenceEqual(annotated_text, expected)

    def test_real_article(self):
        article = Article(load_article("zdrojak_automaticke_zabezpeceni.html"))
        annotated_text = article.main_text

        expected = [
            (
                ("Automatické zabezpečení", ("h1",)),
                ("Úroveň zabezpečení aplikace bych rozdělil do tří úrovní:", None),
            ),
            (
                ("Aplikace zabezpečená není, neošetřuje uživatelské vstupy ani své výstupy.", ("li", "ol")),
                ("Aplikace se o zabezpečení snaží, ale takovým způsobem, že na ně lze zapomenout.", ("li", "ol")),
                ("Aplikace se o zabezpečení stará sama, prakticky se nedá udělat chyba.", ("li", "ol")),
            ),
            (
                ("Jak se tyto úrovně projevují v jednotlivých oblastech?", None),
            ),
            (
                ("XSS", ("a", "h2")),
                ("Druhou úroveň představuje ruční ošetřování pomocí", None),
                ("htmlspecialchars", ("a", "kbd")),
                (". Třetí úroveň zdánlivě reprezentuje automatické ošetřování v šablonách, např. v", None),
                ("Nette Latte", ("a", "strong")),
                (". Proč píšu zdánlivě? Problém je v tom, že ošetření se dá obvykle snadno zakázat, např. v Latte pomocí", None),
                ("{!$var}", ("code",)),
                (". Viděl jsem šablony plné vykřičníků i na místech, kde být neměly. Autor to vysvětlil tak, že psaní", None),
                ("{$var}", ("code",)),
                ("někde způsobovalo problémy, které po přidání vykřičníku zmizely, tak je začal psát všude.", None),
            ),
            (
                ("<?php\n$safeHtml = $texy->process($content_texy);\n$content = Html::el()->setHtml($safeHtml);\n// v šabloně pak můžeme použít {$content}\n?>", ("pre", )),
            ),
            (
                ("Ideální by bylo, když by už samotná metoda", None),
                ("process()", ("code",)),
                ("vracela instanci", None),
                ("Html", ("code",)),
                (".", None),
            ),
        ]
        self.assertSequenceEqual(annotated_text, expected)

########NEW FILE########
__FILENAME__ = test_article
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import os

from breadability.readable import Article
from ...compat import unittest


class TestAntipopeBlog(unittest.TestCase):
    """Test the scoring and parsing of the Blog Post"""

    def setUp(self):
        """Load up the article for us"""
        article_path = os.path.join(os.path.dirname(__file__), 'article.html')
        self.article = open(article_path).read()

    def tearDown(self):
        """Drop the article"""
        self.article = None

    def test_parses(self):
        """Verify we can parse the document."""
        doc = Article(self.article)
        self.assertTrue('id="readabilityBody"' in doc.readable)

    def test_comments_cleaned(self):
        """The div with the comments should be removed."""
        doc = Article(self.article)
        self.assertTrue('class="comments"' not in doc.readable)

    def test_beta_removed(self):
        """The id=beta element should be removed

        It's link heavy and causing a lot of garbage content. This should be
        removed.

        """
        doc = Article(self.article)
        self.assertTrue('id="beta"' not in doc.readable)

########NEW FILE########
__FILENAME__ = test_article
import os
try:
    # Python < 2.7
    import unittest2 as unittest
except ImportError:
    import unittest

from breadability.readable import Article


class TestBusinessInsiderArticle(unittest.TestCase):
    """Test the scoring and parsing of the Blog Post"""

    def setUp(self):

        """Load up the article for us"""
        article_path = os.path.join(os.path.dirname(__file__), 'article.html')
        self.article = open(article_path).read()

    def tearDown(self):
        """Drop the article"""
        self.article = None

    def test_parses(self):
        """Verify we can parse the document."""
        doc = Article(self.article)
        self.assertTrue('id="readabilityBody"' in doc.readable)

    def test_images_preserved(self):
        """The div with the comments should be removed."""
        doc = Article(self.article)
        self.assertTrue('bharath-kumar-a-co-founder-at-pugmarksme-suggests-working-on-a-sunday-late-night.jpg' in doc.readable)
        self.assertTrue('bryan-guido-hassin-a-university-professor-and-startup-junkie-uses-airplane-days.jpg' in doc.readable)

########NEW FILE########
__FILENAME__ = test_article
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from os.path import join, dirname
from breadability.readable import Article
from ...compat import unittest


class TestArticle(unittest.TestCase):
    """
    Test the scoring and parsing of the article from URL below:
    http://www.businessinsider.com/tech-ceos-favorite-productivity-hacks-2013-8
    """

    def setUp(self):
        """Load up the article for us"""
        article_path = join(dirname(__file__), "article.html")
        with open(article_path, "rb") as file:
            self.document = Article(file.read(), "http://www.businessinsider.com/tech-ceos-favorite-productivity-hacks-2013-8")

    def tearDown(self):
        """Drop the article"""
        self.document = None

    def test_parses(self):
        """Verify we can parse the document."""
        self.assertIn('id="readabilityBody"', self.document.readable)

    def test_images_preserved(self):
        """The div with the comments should be removed."""
        images = [
            'bharath-kumar-a-co-founder-at-pugmarksme-suggests-working-on-a-sunday-late-night.jpg',
            'bryan-guido-hassin-a-university-professor-and-startup-junkie-uses-airplane-days.jpg',
        ]

        for image in images:
            self.assertIn(image, self.document.readable, image)

########NEW FILE########
__FILENAME__ = test_article
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from os.path import join, dirname
from breadability.readable import Article
from breadability._compat import unicode
from ...compat import unittest


class TestArticle(unittest.TestCase):
    """
    Test the scoring and parsing of the article from URL below:
    http://www.zdrojak.cz/clanky/jeste-k-testovani/
    """

    def setUp(self):
        """Load up the article for us"""
        article_path = join(dirname(__file__), "article.html")
        with open(article_path, "rb") as file:
            self.document = Article(file.read(), "http://www.zdrojak.cz/clanky/jeste-k-testovani/")

    def tearDown(self):
        """Drop the article"""
        self.document = None

    def test_parses(self):
        """Verify we can parse the document."""
        self.assertIn('id="readabilityBody"', self.document.readable)

    def test_content_exists(self):
        """Verify that some content exists."""
        self.assertIsInstance(self.document.readable, unicode)

        text = "S automatizovaným testováním kódu (a ve zbytku článku budu mít na mysli právě to) jsem se setkal v několika firmách."
        self.assertIn(text, self.document.readable)

        text = "Ke čtení naleznete mnoho různých materiálů, od teoretických po praktické ukázky."
        self.assertIn(text, self.document.readable)

    def test_content_does_not_exist(self):
        """Verify we cleaned out some content that shouldn't exist."""
        self.assertNotIn("Pokud vás problematika zajímá, využijte možnosti navštívit školení", self.document.readable)

########NEW FILE########
__FILENAME__ = test_article
# -*- coding: utf8 -*-

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals
)

import os

from operator import attrgetter
from breadability.readable import Article
from breadability.readable import check_siblings
from breadability.readable import prep_article
from ...compat import unittest


class TestArticle(unittest.TestCase):
    """Test the scoring and parsing of the Article"""

    def setUp(self):
        """Load up the article for us"""
        article_path = os.path.join(os.path.dirname(__file__), 'article.html')
        self.article = open(article_path).read()

    def tearDown(self):
        """Drop the article"""
        self.article = None

    def test_parses(self):
        """Verify we can parse the document."""
        doc = Article(self.article)
        self.assertTrue('id="readabilityBody"' in doc.readable)

    def test_content_exists(self):
        """Verify that some content exists."""
        doc = Article(self.article)
        self.assertTrue('Amazon and Google' in doc.readable)
        self.assertFalse('Linkblog updated' in doc.readable)
        self.assertFalse(
            '#anExampleGoogleDoesntIntendToShareBlogAndItWill' in doc.readable)

    @unittest.skip("Test fails because of some weird hash.")
    def test_candidates(self):
        """Verify we have candidates."""
        doc = Article(self.article)
        # from lxml.etree import tounicode
        found = False
        wanted_hash = '04e46055'

        for node in doc.candidates.values():
            if node.hash_id == wanted_hash:
                found = node

        self.assertTrue(found)

        # we have the right node, it must be deleted for some reason if it's
        # not still there when we need it to be.
        # Make sure it's not in our to drop list.
        for node in doc._should_drop:
            self.assertFalse(node == found.node)

        by_score = sorted(
            [c for c in doc.candidates.values()],
            key=attrgetter('content_score'), reverse=True)
        self.assertTrue(by_score[0].node == found.node)

        updated_winner = check_siblings(by_score[0], doc.candidates)
        updated_winner.node = prep_article(updated_winner.node)

        # This article hits up against the img > p conditional filtering
        # because of the many .gif images in the content. We've removed that
        # rule.

########NEW FILE########
__FILENAME__ = test_article
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from os.path import join, dirname
from breadability.readable import Article
from ...compat import unittest


class TestSweetsharkBlog(unittest.TestCase):
    """
    Test the scoring and parsing of the article from URL below:
    http://sweetshark.livejournal.com/11564.html
    """

    def setUp(self):
        """Load up the article for us"""
        article_path = join(dirname(__file__), "article.html")
        with open(article_path, "rb") as file:
            self.document = Article(file.read(), "http://sweetshark.livejournal.com/11564.html")

    def tearDown(self):
        """Drop the article"""
        self.document = None

    def test_parses(self):
        """Verify we can parse the document."""
        self.assertIn('id="readabilityBody"', self.document.readable)

    def test_content_after_video(self):
        """The div with the comments should be removed."""
        self.assertIn('Stay hungry, Stay foolish', self.document.readable)

########NEW FILE########
__FILENAME__ = test_orig_document
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from collections import defaultdict
from breadability._compat import (
    to_unicode,
    to_bytes,
    unicode,
)

from breadability.document import (
    convert_breaks_to_paragraphs,
    decode_html,
    OriginalDocument,
)
from .compat import unittest
from .utils import load_snippet


class TestOriginalDocument(unittest.TestCase):
    """Verify we can process html into a document to work off of."""

    def test_convert_br_tags_to_paragraphs(self):
        returned = convert_breaks_to_paragraphs(
            ("<div>HI<br><br>How are you?<br><br> \t \n  <br>"
             "Fine\n I guess</div>"))

        self.assertEqual(
            returned,
            "<div>HI</p><p>How are you?</p><p>Fine\n I guess</div>")

    def test_convert_hr_tags_to_paragraphs(self):
        returned = convert_breaks_to_paragraphs(
            "<div>HI<br><br>How are you?<hr/> \t \n  <br>Fine\n I guess</div>")

        self.assertEqual(
            returned,
            "<div>HI</p><p>How are you?</p><p>Fine\n I guess</div>")

    def test_readin_min_document(self):
        """Verify we can read in a min html document"""
        doc = OriginalDocument(load_snippet('document_min.html'))
        self.assertTrue(to_unicode(doc).startswith('<html>'))
        self.assertEqual(doc.title, 'Min Document Title')

    def test_readin_with_base_url(self):
        """Passing a url should update links to be absolute links"""
        doc = OriginalDocument(
            load_snippet('document_absolute_url.html'),
            url="http://blog.mitechie.com/test.html")
        self.assertTrue(to_unicode(doc).startswith('<html>'))

        # find the links on the page and make sure each one starts with out
        # base url we told it to use.
        links = doc.links
        self.assertEqual(len(links), 3)
        # we should have two links that start with our blog url
        # and one link that starts with amazon
        link_counts = defaultdict(int)
        for link in links:
            if link.get('href').startswith('http://blog.mitechie.com'):
                link_counts['blog'] += 1
            else:
                link_counts['other'] += 1

        self.assertEqual(link_counts['blog'], 2)
        self.assertEqual(link_counts['other'], 1)

    def test_no_br_allowed(self):
        """We convert all <br/> tags to <p> tags"""
        doc = OriginalDocument(load_snippet('document_min.html'))
        self.assertIsNone(doc.dom.find('.//br'))

    def test_empty_title(self):
        """We convert all <br/> tags to <p> tags"""
        document = OriginalDocument(
            "<html><head><title></title></head><body></body></html>")
        self.assertEqual(document.title, "")

    def test_title_only_with_tags(self):
        """We convert all <br/> tags to <p> tags"""
        document = OriginalDocument(
            "<html><head><title><em></em></title></head><body></body></html>")
        self.assertEqual(document.title, "")

    def test_no_title(self):
        """We convert all <br/> tags to <p> tags"""
        document = OriginalDocument("<html><head></head><body></body></html>")
        self.assertEqual(document.title, "")

    def test_encoding(self):
        text = "ľščťžýáíéäúňôůě".encode("iso-8859-2")
        html = decode_html(text)
        self.assertEqual(type(html), unicode)

    def test_encoding_short(self):
        text = to_bytes("ľščťžýáíé")
        html = decode_html(text)
        self.assertEqual(type(html), unicode)
        self.assertEqual(html, "ľščťžýáíé")

########NEW FILE########
__FILENAME__ = test_readable
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from lxml.etree import tounicode
from lxml.html import document_fromstring
from lxml.html import fragment_fromstring
from breadability._compat import to_unicode
from breadability.readable import (
    Article,
    get_class_weight,
    get_link_density,
    is_bad_link,
    leaf_div_elements_into_paragraphs,
    score_candidates,
)
from breadability.scoring import ScoredNode
from .compat import unittest
from .utils import load_snippet, load_article


class TestReadableDocument(unittest.TestCase):
    """Verify we can process html into a document to work off of."""

    def test_load_doc(self):
        """We get back an element tree from our original doc"""
        doc = Article(load_snippet('document_min.html'))
        # We get back the document as a div tag currently by default.
        self.assertEqual(doc.readable_dom.tag, 'div')

    def test_title_loads(self):
        """Verify we can fetch the title of the parsed article"""
        doc = Article(load_snippet('document_min.html'))
        self.assertEqual(
            doc._original_document.title,
            'Min Document Title'
        )

    def test_doc_no_scripts_styles(self):
        """Step #1 remove all scripts from the document"""
        doc = Article(load_snippet('document_scripts.html'))
        readable = doc.readable_dom
        self.assertEqual(readable.findall(".//script"), [])
        self.assertEqual(readable.findall(".//style"), [])
        self.assertEqual(readable.findall(".//link"), [])

    def test_find_body_exists(self):
        """If the document has a body, we store that as the readable html

        No sense processing anything other than the body content.

        """
        doc = Article(load_snippet('document_min.html'))
        self.assertEqual(doc.readable_dom.tag, 'div')
        self.assertEqual(doc.readable_dom.get('id'), 'readabilityBody')

    def test_body_doesnt_exist(self):
        """If we can't find a body, then we create one.

        We build our doc around the rest of the html we parsed.

        """
        doc = Article(load_snippet('document_no_body.html'))
        self.assertEqual(doc.readable_dom.tag, 'div')
        self.assertEqual(doc.readable_dom.get('id'), 'readabilityBody')

    def test_bare_content(self):
        """If the document is just pure content, no html tags we should be ok

        We build our doc around the rest of the html we parsed.

        """
        doc = Article(load_snippet('document_only_content.html'))
        self.assertEqual(doc.readable_dom.tag, 'div')
        self.assertEqual(doc.readable_dom.get('id'), 'readabilityBody')

    def test_no_content(self):
        """Without content we supply an empty unparsed doc."""
        doc = Article('')
        self.assertEqual(doc.readable_dom.tag, 'div')
        self.assertEqual(doc.readable_dom.get('id'), 'readabilityBody')
        self.assertEqual(doc.readable_dom.get('class'), 'parsing-error')


class TestCleaning(unittest.TestCase):
    """Test out our cleaning processing we do."""

    def test_unlikely_hits(self):
        """Verify we wipe out things from our unlikely list."""
        doc = Article(load_snippet('test_readable_unlikely.html'))
        readable = doc.readable_dom
        must_not_appear = [
            'comment', 'community', 'disqus', 'extra', 'foot',
            'header', 'menu', 'remark', 'rss', 'shoutbox', 'sidebar',
            'sponsor', 'ad-break', 'agegate', 'pagination' '', 'pager',
            'popup', 'tweet', 'twitter', 'imgBlogpostPermalink']

        want_to_appear = ['and', 'article', 'body', 'column', 'main', 'shadow']

        for i in must_not_appear:
            # we cannot find any class or id with this value
            by_class = readable.find_class(i)

            for test in by_class:
                # if it's here it cannot have the must not class without the
                # want to appear class
                found = False
                for cls in test.get('class').split():
                    if cls in want_to_appear:
                        found = True
                self.assertTrue(found)

            by_ids = readable.get_element_by_id(i, False)
            if by_ids is not False:
                found = False
                for ids in test.get('id').split():
                    if ids in want_to_appear:
                        found = True
                self.assertTrue(found)

    def test_misused_divs_transform(self):
        """Verify we replace leaf node divs with p's

        They should have the same content, just be a p vs a div

        """
        test_html = "<html><body><div>simple</div></body></html>"
        test_doc = document_fromstring(test_html)
        self.assertEqual(
            tounicode(
                leaf_div_elements_into_paragraphs(test_doc)),
            to_unicode("<html><body><p>simple</p></body></html>")
        )

        test_html2 = ('<html><body><div>simple<a href="">link</a>'
                      '</div></body></html>')
        test_doc2 = document_fromstring(test_html2)
        self.assertEqual(
            tounicode(
                leaf_div_elements_into_paragraphs(test_doc2)),
            to_unicode(
                '<html><body><p>simple<a href="">link</a></p></body></html>')
        )

    def test_dont_transform_div_with_div(self):
        """Verify that only child <div> element is replaced by <p>."""
        dom = document_fromstring(
            "<html><body><div>text<div>child</div>"
            "aftertext</div></body></html>"
        )

        self.assertEqual(
            tounicode(
                leaf_div_elements_into_paragraphs(dom)),
            to_unicode(
                "<html><body><div>text<p>child</p>"
                "aftertext</div></body></html>"
            )
        )

    def test_bad_links(self):
        """Some links should just not belong."""
        bad_links = [
            '<a name="amazonAndGoogleHaveMadeAnAudaciousGrabOfNamespaceOnTheInternetAsFarAsICanSeeTheresBeenNoMentionOfThisInTheTechPress">&nbsp;</a>',
            '<a href="#amazonAndGoogleHaveMadeAnAudaciousGrabOfNamespaceOnTheInternetAsFarAsICanSeeTheresBeenNoMentionOfThisInTheTechPress"><img src="http://scripting.com/images/2001/09/20/sharpPermaLink3.gif" class="imgBlogpostPermalink" width="6" height="9" border="0" alt="permalink"></a>',
            '<a href="http://scripting.com/stories/2012/06/15/theTechPressIsOutToLunch.html#anExampleGoogleDoesntIntendToShareBlogAndItWillOnlyBeUsedToPointToBloggerSitesIfYouHaveATumblrOrWordpressBlogYouCantHaveABlogDomainHereIsTheAHrefhttpgtldresulticannorgapplicationresultapplicationstatusapplicationdetails527publicListingaOfGooglesAHrefhttpdropboxscriptingcomdavemiscgoogleblogapplicationhtmlapplicationa"><img src="http://scripting.com/images/2001/09/20/sharpPermaLink3.gif" class="imgBlogpostPermalink" width="6" height="9" border="0" alt="permalink"></a>'
        ]

        for l in bad_links:
            link = fragment_fromstring(l)
            self.assertTrue(is_bad_link(link))


class TestCandidateNodes(unittest.TestCase):
    """Candidate nodes are scoring containers we use."""

    def test_candidate_scores(self):
        """We should be getting back objects with some scores."""
        fives = ['<div/>']
        threes = ['<pre/>', '<td/>', '<blockquote/>']
        neg_threes = ['<address/>', '<ol/>']
        neg_fives = ['<h1/>', '<h2/>', '<h3/>', '<h4/>']

        for n in fives:
            doc = fragment_fromstring(n)
            self.assertEqual(ScoredNode(doc).content_score, 5)

        for n in threes:
            doc = fragment_fromstring(n)
            self.assertEqual(ScoredNode(doc).content_score, 3)

        for n in neg_threes:
            doc = fragment_fromstring(n)
            self.assertEqual(ScoredNode(doc).content_score, -3)

        for n in neg_fives:
            doc = fragment_fromstring(n)
            self.assertEqual(ScoredNode(doc).content_score, -5)

    def test_article_enables_candidate_access(self):
        """Candidates are accessible after document processing."""
        doc = Article(load_article('ars.001.html'))
        self.assertTrue(hasattr(doc, 'candidates'))


class TestClassWeights(unittest.TestCase):
    """Certain ids and classes get us bonus points."""

    def test_positive_class(self):
        """Some classes get us bonus points."""
        node = fragment_fromstring('<p class="article">')
        self.assertEqual(get_class_weight(node), 25)

    def test_positive_ids(self):
        """Some ids get us bonus points."""
        node = fragment_fromstring('<p id="content">')
        self.assertEqual(get_class_weight(node), 25)

    def test_negative_class(self):
        """Some classes get us negative points."""
        node = fragment_fromstring('<p class="comment">')
        self.assertEqual(get_class_weight(node), -25)

    def test_negative_ids(self):
        """Some ids get us negative points."""
        node = fragment_fromstring('<p id="media">')
        self.assertEqual(get_class_weight(node), -25)


class TestScoringNodes(unittest.TestCase):
    """We take out list of potential nodes and score them up."""

    def test_we_get_candidates(self):
        """Processing candidates should get us a list of nodes to try out."""
        doc = document_fromstring(load_article("ars.001.html"))
        test_nodes = tuple(doc.iter("p", "td", "pre"))
        candidates = score_candidates(test_nodes)

        # this might change as we tweak our algorithm, but if it does,
        # it signifies we need to look at what we changed.
        self.assertEqual(len(candidates.keys()), 37)

        # one of these should have a decent score
        scores = sorted(c.content_score for c in candidates.values())
        self.assertTrue(scores[-1] > 100)

    def test_bonus_score_per_100_chars_in_p(self):
        """Nodes get 1 point per 100 characters up to max. 3 points."""
        def build_candidates(length):
            html = "<p>%s</p>" % ("c" * length)
            node = fragment_fromstring(html)

            return [node]

        test_nodes = build_candidates(50)
        candidates = score_candidates(test_nodes)
        pscore_50 = max(c.content_score for c in candidates.values())

        test_nodes = build_candidates(100)
        candidates = score_candidates(test_nodes)
        pscore_100 = max(c.content_score for c in candidates.values())

        test_nodes = build_candidates(300)
        candidates = score_candidates(test_nodes)
        pscore_300 = max(c.content_score for c in candidates.values())

        test_nodes = build_candidates(400)
        candidates = score_candidates(test_nodes)
        pscore_400 = max(c.content_score for c in candidates.values())

        self.assertAlmostEqual(pscore_50 + 0.5, pscore_100)
        self.assertAlmostEqual(pscore_100 + 2.0, pscore_300)
        self.assertAlmostEqual(pscore_300, pscore_400)


class TestLinkDensityScoring(unittest.TestCase):
    """Link density will adjust out candidate scoresself."""

    def test_link_density(self):
        """Test that we get a link density"""
        doc = document_fromstring(load_article('ars.001.html'))
        for node in doc.iter('p', 'td', 'pre'):
            density = get_link_density(node)

            # the density must be between 0, 1
            self.assertTrue(density >= 0.0 and density <= 1.0)


class TestSiblings(unittest.TestCase):
    """Siblings will be included if their content is related."""

    @unittest.skip("Not implemented yet.")
    def test_bad_siblings_not_counted(self):
        raise NotImplementedError()

    @unittest.skip("Not implemented yet.")
    def test_good_siblings_counted(self):
        raise NotImplementedError()


class TestMainText(unittest.TestCase):
    def test_empty(self):
        article = Article("")
        annotated_text = article.main_text

        self.assertEqual(annotated_text, [])

    def test_no_annotations(self):
        article = Article("<div><p>This is text with no annotations</p></div>")
        annotated_text = article.main_text

        self.assertEqual(annotated_text,
            [(("This is text with no annotations", None),)])

    def test_one_annotation(self):
        article = Article("<div><p>This is text\r\twith <del>no</del> annotations</p></div>")
        annotated_text = article.main_text

        expected = [(
            ("This is text\nwith", None),
            ("no", ("del",)),
            ("annotations", None),
        )]
        self.assertEqual(annotated_text, expected)

    def test_simple_snippet(self):
        snippet = Article(load_snippet("annotated_1.html"))
        annotated_text = snippet.main_text

        expected = [
            (
                ("Paragraph is more", None),
                ("better", ("em",)),
                (".\nThis text is very", None),
                ("pretty", ("strong",)),
                ("'cause she's girl.", None),
            ),
            (
                ("This is not", None),
                ("crap", ("big",)),
                ("so", None),
                ("readability", ("dfn",)),
                ("me :)", None),
            )
        ]
        self.assertEqual(annotated_text, expected)

########NEW FILE########
__FILENAME__ = test_scoring
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import re

from operator import attrgetter
from lxml.html import document_fromstring
from lxml.html import fragment_fromstring
from breadability.readable import Article
from breadability.scoring import (
    check_node_attributes,
    generate_hash_id,
    get_class_weight,
    score_candidates,
    ScoredNode,
)
from breadability.readable import (
    get_link_density,
    is_unlikely_node,
)
from .compat import unittest
from .utils import load_snippet


class TestHashId(unittest.TestCase):
    def test_generate_hash(self):
        dom = fragment_fromstring("<div>ľščťžýáí</div>")
        generate_hash_id(dom)

    def test_hash_from_id_on_exception(self):
        generate_hash_id(None)

    def test_different_hashes(self):
        dom = fragment_fromstring("<div>ľščťžýáí</div>")
        hash_dom = generate_hash_id(dom)
        hash_none = generate_hash_id(None)

        self.assertNotEqual(hash_dom, hash_none)

    def test_equal_hashes(self):
        dom1 = fragment_fromstring("<div>ľščťžýáí</div>")
        dom2 = fragment_fromstring("<div>ľščťžýáí</div>")
        hash_dom1 = generate_hash_id(dom1)
        hash_dom2 = generate_hash_id(dom2)
        self.assertEqual(hash_dom1, hash_dom2)

        hash_none1 = generate_hash_id(None)
        hash_none2 = generate_hash_id(None)
        self.assertEqual(hash_none1, hash_none2)


class TestCheckNodeAttr(unittest.TestCase):
    """Verify a node has a class/id in the given set.

    The idea is that we have sets of known good/bad ids and classes and need
    to verify the given node does/doesn't have those classes/ids.

    """
    def test_has_class(self):
        """Verify that a node has a class in our set."""
        test_pattern = re.compile('test1|test2', re.I)
        test_node = fragment_fromstring('<div/>')
        test_node.set('class', 'test2 comment')

        self.assertTrue(
            check_node_attributes(test_pattern, test_node, 'class'))

    def test_has_id(self):
        """Verify that a node has an id in our set."""
        test_pattern = re.compile('test1|test2', re.I)
        test_node = fragment_fromstring('<div/>')
        test_node.set('id', 'test2')

        self.assertTrue(check_node_attributes(test_pattern, test_node, 'id'))

    def test_lacks_class(self):
        """Verify that a node does not have a class in our set."""
        test_pattern = re.compile('test1|test2', re.I)
        test_node = fragment_fromstring('<div/>')
        test_node.set('class', 'test4 comment')
        self.assertFalse(
            check_node_attributes(test_pattern, test_node, 'class'))

    def test_lacks_id(self):
        """Verify that a node does not have an id in our set."""
        test_pattern = re.compile('test1|test2', re.I)
        test_node = fragment_fromstring('<div/>')
        test_node.set('id', 'test4')
        self.assertFalse(check_node_attributes(test_pattern, test_node, 'id'))


class TestLinkDensity(unittest.TestCase):
    """Verify we calc our link density correctly."""

    def test_empty_node(self):
        """An empty node doesn't have much of a link density"""
        doc = Article("<div></div>")
        self.assertEqual(get_link_density(doc.readable_dom), 0.0)

    def test_small_doc_no_links(self):
        doc = Article(load_snippet('document_min.html'))
        self.assertEqual(get_link_density(doc.readable_dom), 0.0)

    def test_several_links(self):
        """This doc has a 3 links with the majority of content."""
        doc = Article(load_snippet('document_absolute_url.html'))
        self.assertAlmostEqual(get_link_density(doc.readable_dom), 22/37)


class TestClassWeight(unittest.TestCase):
    """Verify we score nodes correctly based on their class/id attributes."""

    def test_no_matches_zero(self):
        """If you don't have the attribute then you get a weight of 0"""
        node = fragment_fromstring("<div></div>")
        self.assertEqual(get_class_weight(node), 0)

    def test_id_hits(self):
        """If the id is in the list then it gets a weight"""
        test_div = '<div id="post">Content</div>'
        node = fragment_fromstring(test_div)
        self.assertEqual(get_class_weight(node), 25)

        test_div = '<div id="comments">Content</div>'
        node = fragment_fromstring(test_div)
        self.assertEqual(get_class_weight(node), -25)

    def test_class_hits(self):
        """If the class is in the list then it gets a weight"""
        test_div = '<div class="something post">Content</div>'
        node = fragment_fromstring(test_div)
        self.assertEqual(get_class_weight(node), 25)

        test_div = '<div class="something comments">Content</div>'
        node = fragment_fromstring(test_div)
        self.assertEqual(get_class_weight(node), -25)

    def test_scores_collide(self):
        """We might hit both positive and negative scores.

        Positive and negative scoring is done independently so it's possible
        to hit both positive and negative scores and cancel each other out.

        """
        test_div = '<div id="post" class="something comment">Content</div>'
        node = fragment_fromstring(test_div)
        self.assertEqual(get_class_weight(node), 0)

        test_div = '<div id="post" class="post comment">Content</div>'
        node = fragment_fromstring(test_div)
        self.assertEqual(get_class_weight(node), 25)

    def test_scores_only_once(self):
        """Scoring is not cumulative within a class hit."""
        test_div = '<div class="post main">Content</div>'
        node = fragment_fromstring(test_div)
        self.assertEqual(get_class_weight(node), 25)


class TestUnlikelyNode(unittest.TestCase):
    """is_unlikely_node should help verify our node is good/bad."""

    def test_body_is_always_likely(self):
        """The body tag is always a likely node."""
        test_div = '<body class="comment"><div>Content</div></body>'
        node = fragment_fromstring(test_div)
        self.assertFalse(is_unlikely_node(node))

    def test_is_unlikely(self):
        "Keywords in the class/id will make us believe this is unlikely."
        test_div = '<div class="something comments">Content</div>'
        node = fragment_fromstring(test_div)
        self.assertTrue(is_unlikely_node(node))

        test_div = '<div id="comments">Content</div>'
        node = fragment_fromstring(test_div)
        self.assertTrue(is_unlikely_node(node))

    def test_not_unlikely(self):
        """Suck it double negatives."""
        test_div = '<div id="post">Content</div>'
        node = fragment_fromstring(test_div)
        self.assertFalse(is_unlikely_node(node))

        test_div = '<div class="something post">Content</div>'
        node = fragment_fromstring(test_div)
        self.assertFalse(is_unlikely_node(node))

    def test_maybe_hits(self):
        """We've got some maybes that will overrule an unlikely node."""
        test_div = '<div id="comments" class="article">Content</div>'
        node = fragment_fromstring(test_div)
        self.assertFalse(is_unlikely_node(node))


class TestScoredNode(unittest.TestCase):
    """ScoredNodes constructed have initial content_scores, etc."""

    def test_hash_id(self):
        """ScoredNodes have a hash_id based on their content

        Since this is based on the html there are chances for collisions, but
        it helps us follow and identify nodes through the scoring process. Two
        identical nodes would score the same, so meh all good.

        """
        test_div = '<div id="comments" class="article">Content</div>'
        node = fragment_fromstring(test_div)
        snode = ScoredNode(node)
        self.assertEqual(snode.hash_id, 'ffa4c519')

    def test_div_content_score(self):
        """A div starts out with a score of 5 and modifies from there"""
        test_div = '<div id="" class="">Content</div>'
        node = fragment_fromstring(test_div)
        snode = ScoredNode(node)
        self.assertEqual(snode.content_score, 5)

        test_div = '<div id="article" class="">Content</div>'
        node = fragment_fromstring(test_div)
        snode = ScoredNode(node)
        self.assertEqual(snode.content_score, 30)

        test_div = '<div id="comments" class="">Content</div>'
        node = fragment_fromstring(test_div)
        snode = ScoredNode(node)
        self.assertEqual(snode.content_score, -20)

    def test_headings_score(self):
        """Heading tags aren't likely candidates, hurt their scores."""
        test_div = '<h2>Heading</h2>'
        node = fragment_fromstring(test_div)
        snode = ScoredNode(node)
        self.assertEqual(snode.content_score, -5)

    def test_list_items(self):
        """Heading tags aren't likely candidates, hurt their scores."""
        test_div = '<li>list item</li>'
        node = fragment_fromstring(test_div)
        snode = ScoredNode(node)
        self.assertEqual(snode.content_score, -3)


class TestScoreCandidates(unittest.TestCase):
    """The grand daddy of tests to make sure our scoring works

    Now scoring details will change over time, so the most important thing is
    to make sure candidates come out in the right order, not necessarily how
    they scored. Make sure to keep this in mind while getting tests going.

    """

    def test_simple_candidate_set(self):
        """Tests a simple case of two candidate nodes"""
        html = """
            <html>
            <body>
                <div class="content">
                    <p>This is a great amount of info</p>
                    <p>And more content <a href="/index">Home</a>
                </div>
                <div class="footer">
                    <p>This is a footer</p>
                    <p>And more content <a href="/index">Home</a>
                </div>
            </body>
            </html>
        """
        dom = document_fromstring(html)
        div_nodes = dom.findall(".//div")

        candidates = score_candidates(div_nodes)
        ordered = sorted(
            (c for c in candidates.values()), reverse=True,
            key=attrgetter("content_score"))

        self.assertEqual(ordered[0].node.tag, "div")
        self.assertEqual(ordered[0].node.attrib["class"], "content")
        self.assertEqual(ordered[1].node.tag, "body")
        self.assertEqual(ordered[2].node.tag, "html")
        self.assertEqual(ordered[3].node.tag, "div")
        self.assertEqual(ordered[3].node.attrib["class"], "footer")

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from os.path import abspath, dirname, join


TEST_DIR = abspath(dirname(__file__))


def load_snippet(file_name):
    """Helper to fetch in the content of a test snippet."""
    file_path = join(TEST_DIR, "data/snippets", file_name)
    with open(file_path, "rb") as file:
        return file.read()


def load_article(file_name):
    """Helper to fetch in the content of a test article."""
    file_path = join(TEST_DIR, "data/articles", file_name)
    with open(file_path, "rb") as file:
        return file.read()

########NEW FILE########
