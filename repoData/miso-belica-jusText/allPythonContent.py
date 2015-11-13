__FILENAME__ = core
# -*- coding: utf8 -*-

"""
Copyright (c) 2011 Jan Pomikalek

This software is licensed as described in the file LICENSE.rst.
"""

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import re
import lxml.html
import lxml.sax

from lxml.html.clean import Cleaner
from xml.sax.handler import ContentHandler
from .paragraph import Paragraph
from ._compat import unicode, ignored
from .utils import is_blank, get_stoplist, get_stoplists


MAX_LINK_DENSITY_DEFAULT = 0.2
LENGTH_LOW_DEFAULT = 70
LENGTH_HIGH_DEFAULT = 200
STOPWORDS_LOW_DEFAULT = 0.30
STOPWORDS_HIGH_DEFAULT = 0.32
NO_HEADINGS_DEFAULT = False
# Short and near-good headings within MAX_HEADING_DISTANCE characters before
# a good paragraph are classified as good unless --no-headings is specified.
MAX_HEADING_DISTANCE_DEFAULT = 200
PARAGRAPH_TAGS = [
    'body', 'blockquote', 'caption', 'center', 'col', 'colgroup', 'dd',
    'div', 'dl', 'dt', 'fieldset', 'form', 'legend', 'optgroup', 'option',
    'p', 'pre', 'table', 'td', 'textarea', 'tfoot', 'th', 'thead', 'tr',
    'ul', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
]
DEFAULT_ENCODING = 'utf8'
DEFAULT_ENC_ERRORS = 'replace'
CHARSET_META_TAG_PATTERN = re.compile(br"""<meta[^>]+charset=["']?([^'"/>\s]+)""",
    re.IGNORECASE)


class JustextError(Exception):
    "Base class for jusText exceptions."


class JustextInvalidOptions(JustextError):
    pass


def html_to_dom(html, default_encoding=DEFAULT_ENCODING, encoding=None, errors=DEFAULT_ENC_ERRORS):
    """Converts HTML to DOM."""
    if isinstance(html, unicode):
        decoded_html = html
        # encode HTML for case it's XML with encoding declaration
        forced_encoding = encoding if encoding else default_encoding
        html = html.encode(forced_encoding, errors)
    else:
        decoded_html = decode_html(html, default_encoding, encoding, errors)

    try:
        dom = lxml.html.fromstring(decoded_html)
    except ValueError:
        # Unicode strings with encoding declaration are not supported.
        # for XHTML files with encoding declaration, use the declared encoding
        dom = lxml.html.fromstring(html)

    return dom


def decode_html(html, default_encoding=DEFAULT_ENCODING, encoding=None, errors=DEFAULT_ENC_ERRORS):
    """
    Converts a `html` containing an HTML page into Unicode.
    Tries to guess character encoding from meta tag.
    """
    if isinstance(html, unicode):
        return html

    if encoding:
        return html.decode(encoding, errors)

    match = CHARSET_META_TAG_PATTERN.search(html)
    if match:
        declared_encoding = match.group(1).decode("ASCII")
        # proceed unknown encoding as if it wasn't found at all
        with ignored(LookupError):
            return html.decode(declared_encoding, errors)

    # unknown encoding
    try:
        # try UTF-8 first
        return html.decode("utf8")
    except UnicodeDecodeError:
        # try lucky with default encoding
        try:
            return html.decode(default_encoding, errors)
        except UnicodeDecodeError as e:
            raise JustextError("Unable to decode the HTML to Unicode: " + unicode(e))


def preprocessor(dom):
    "Removes unwanted parts of DOM."
    options = {
        "processing_instructions": False,
        "remove_unknown_tags": False,
        "safe_attrs_only": False,
        "page_structure": False,
        "annoying_tags": False,
        "frames": False,
        "meta": False,
        "links": False,
        "javascript": False,
        "scripts": True,
        "comments": True,
        "style": True,
        "embedded": True,
        "forms": True,
        "kill_tags": ("head",),
    }
    cleaner = Cleaner(**options)

    return cleaner.clean_html(dom)


class ParagraphMaker(ContentHandler):
    """
    A class for converting a HTML page represented as a DOM object into a list
    of paragraphs.
    """

    @classmethod
    def make_paragraphs(cls, root):
        """Converts DOM into paragraphs."""
        handler = cls()
        lxml.sax.saxify(root, handler)
        return handler.paragraphs

    def __init__(self):
        self.path = PathInfo()
        self.paragraphs = []
        self.paragraph = None
        self.link = False
        self.br = False
        self._start_new_pragraph()

    def _start_new_pragraph(self):
        if self.paragraph and self.paragraph.contains_text():
            self.paragraphs.append(self.paragraph)

        self.paragraph = Paragraph(self.path)

    def startElementNS(self, name, qname, attrs):
        name = name[1]
        self.path.append(name)

        if name in PARAGRAPH_TAGS or (name == "br" and self.br):
            if name == "br":
                # the <br><br> is a paragraph separator and should
                # not be included in the number of tags within the
                # paragraph
                self.paragraph.tags_count -= 1
            self._start_new_pragraph()
        else:
            self.br = bool(name == "br")
            if name == 'a':
                self.link = True
            self.paragraph.tags_count += 1

    def endElementNS(self, name, qname):
        name = name[1]
        self.path.pop()

        if name in PARAGRAPH_TAGS:
            self._start_new_pragraph()
        if name == 'a':
            self.link = False

    def endDocument(self):
        self._start_new_pragraph()

    def characters(self, content):
        if is_blank(content):
            return

        text = self.paragraph.append_text(content)

        if self.link:
            self.paragraph.chars_count_in_links += len(text)
        self.br = False


class PathInfo(object):
    def __init__(self):
        # list of triples (tag name, order, children)
        self._elements = []

    @property
    def dom(self):
        return ".".join(e[0] for e in self._elements)

    @property
    def xpath(self):
        return "/" + "/".join("%s[%d]" % e[:2] for e in self._elements)

    def append(self, tag_name):
        children = self._get_children()
        order = children.get(tag_name, 0) + 1
        children[tag_name] = order

        xpath_part = (tag_name, order, {})
        self._elements.append(xpath_part)

        return self

    def _get_children(self):
        if not self._elements:
            return {}

        return self._elements[-1][2]

    def pop(self):
        self._elements.pop()
        return self


def classify_paragraphs(paragraphs, stoplist, length_low=LENGTH_LOW_DEFAULT,
        length_high=LENGTH_HIGH_DEFAULT, stopwords_low=STOPWORDS_LOW_DEFAULT,
        stopwords_high=STOPWORDS_HIGH_DEFAULT, max_link_density=MAX_LINK_DENSITY_DEFAULT,
        no_headings=NO_HEADINGS_DEFAULT):
    "Context-free paragraph classification."

    stoplist = frozenset(w.lower() for w in stoplist)
    for paragraph in paragraphs:
        length = len(paragraph)
        stopword_density = paragraph.stopwords_density(stoplist)
        link_density = paragraph.links_density()
        paragraph.heading = bool(not no_headings and paragraph.is_heading)

        if link_density > max_link_density:
            paragraph.cf_class = 'bad'
        elif ('\xa9' in paragraph.text) or ('&copy' in paragraph.text):
            paragraph.cf_class = 'bad'
        elif re.search('^select|\.select', paragraph.dom_path):
            paragraph.cf_class = 'bad'
        elif length < length_low:
            if paragraph.chars_count_in_links > 0:
                paragraph.cf_class = 'bad'
            else:
                paragraph.cf_class = 'short'
        elif stopword_density >= stopwords_high:
            if length > length_high:
                paragraph.cf_class = 'good'
            else:
                paragraph.cf_class = 'neargood'
        elif stopword_density >= stopwords_low:
            paragraph.cf_class = 'neargood'
        else:
            paragraph.cf_class = 'bad'


def _get_neighbour(i, paragraphs, ignore_neargood, inc, boundary):
    while i + inc != boundary:
        i += inc
        c = paragraphs[i].class_type
        if c in ['good', 'bad']:
            return c
        if c == 'neargood' and not ignore_neargood:
            return c
    return 'bad'


def get_prev_neighbour(i, paragraphs, ignore_neargood):
    """
    Return the class of the paragraph at the top end of the short/neargood
    paragraphs block. If ignore_neargood is True, than only 'bad' or 'good'
    can be returned, otherwise 'neargood' can be returned, too.
    """
    return _get_neighbour(i, paragraphs, ignore_neargood, -1, -1)


def get_next_neighbour(i, paragraphs, ignore_neargood):
    """
    Return the class of the paragraph at the bottom end of the short/neargood
    paragraphs block. If ignore_neargood is True, than only 'bad' or 'good'
    can be returned, otherwise 'neargood' can be returned, too.
    """
    return _get_neighbour(i, paragraphs, ignore_neargood, 1, len(paragraphs))


def revise_paragraph_classification(paragraphs, max_heading_distance=MAX_HEADING_DISTANCE_DEFAULT):
    """
    Context-sensitive paragraph classification. Assumes that classify_pragraphs
    has already been called.
    """
    # copy classes
    for paragraph in paragraphs:
        paragraph.class_type = paragraph.cf_class

    # good headings
    for i, paragraph in enumerate(paragraphs):
        if not (paragraph.heading and paragraph.class_type == 'short'):
            continue
        j = i + 1
        distance = 0
        while j < len(paragraphs) and distance <= max_heading_distance:
            if paragraphs[j].class_type == 'good':
                paragraph.class_type = 'neargood'
                break
            distance += len(paragraphs[j].text)
            j += 1

    # classify short
    new_classes = {}
    for i, paragraph in enumerate(paragraphs):
        if paragraph.class_type != 'short':
            continue
        prev_neighbour = get_prev_neighbour(i, paragraphs, ignore_neargood=True)
        next_neighbour = get_next_neighbour(i, paragraphs, ignore_neargood=True)
        neighbours = set((prev_neighbour, next_neighbour))
        if neighbours == set(['good']):
            new_classes[i] = 'good'
        elif neighbours == set(['bad']):
            new_classes[i] = 'bad'
        # it must be set(['good', 'bad'])
        elif (prev_neighbour == 'bad' and get_prev_neighbour(i, paragraphs, ignore_neargood=False) == 'neargood') or \
             (next_neighbour == 'bad' and get_next_neighbour(i, paragraphs, ignore_neargood=False) == 'neargood'):
            new_classes[i] = 'good'
        else:
            new_classes[i] = 'bad'

    for i, c in new_classes.items():
        paragraphs[i].class_type = c

    # revise neargood
    for i, paragraph in enumerate(paragraphs):
        if paragraph.class_type != 'neargood':
            continue
        prev_neighbour = get_prev_neighbour(i, paragraphs, ignore_neargood=True)
        next_neighbour = get_next_neighbour(i, paragraphs, ignore_neargood=True)
        if (prev_neighbour, next_neighbour) == ('bad', 'bad'):
            paragraph.class_type = 'bad'
        else:
            paragraph.class_type = 'good'

    # more good headings
    for i, paragraph in enumerate(paragraphs):
        if not (paragraph.heading and paragraph.class_type == 'bad' and paragraph.cf_class != 'bad'):
            continue
        j = i + 1
        distance = 0
        while j < len(paragraphs) and distance <= max_heading_distance:
            if paragraphs[j].class_type == 'good':
                paragraph.class_type = 'good'
                break
            distance += len(paragraphs[j].text)
            j += 1


def justext(html_text, stoplist, length_low=LENGTH_LOW_DEFAULT,
        length_high=LENGTH_HIGH_DEFAULT, stopwords_low=STOPWORDS_LOW_DEFAULT,
        stopwords_high=STOPWORDS_HIGH_DEFAULT, max_link_density=MAX_LINK_DENSITY_DEFAULT,
        max_heading_distance=MAX_HEADING_DISTANCE_DEFAULT, no_headings=NO_HEADINGS_DEFAULT,
        encoding=None, default_encoding=DEFAULT_ENCODING,
        enc_errors=DEFAULT_ENC_ERRORS, preprocessor=preprocessor):
    """
    Converts an HTML page into a list of classified paragraphs. Each paragraph
    is represented as instance of class ˙˙justext.paragraph.Paragraph˙˙.
    """
    dom = html_to_dom(html_text, default_encoding, encoding, enc_errors)
    dom = preprocessor(dom)

    paragraphs = ParagraphMaker.make_paragraphs(dom)

    classify_paragraphs(paragraphs, stoplist, length_low, length_high,
        stopwords_low, stopwords_high, max_link_density, no_headings)
    revise_paragraph_classification(paragraphs, max_heading_distance)

    return paragraphs

########NEW FILE########
__FILENAME__ = paragraph
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import re

from .utils import normalize_whitespace


class Paragraph(object):
    """Object representing one block of text in HTML."""
    def __init__(self, path):
        self.dom_path = path.dom
        self.xpath = path.xpath
        self.text_nodes = []
        self.chars_count_in_links = 0
        self.tags_count = 0

    @property
    def is_heading(self):
        return bool(re.search(r"\bh\d\b", self.dom_path))

    @property
    def is_boilerplate(self):
        return self.class_type != "good"

    @property
    def text(self):
        text = "".join(self.text_nodes)
        return normalize_whitespace(text.strip())

    def __len__(self):
        return len(self.text)

    @property
    def words_count(self):
        return len(self.text.split())

    def contains_text(self):
        return bool(self.text_nodes)

    def append_text(self, text):
        text = normalize_whitespace(text)
        self.text_nodes.append(text)
        return text

    def stopwords_count(self, stopwords):
        count = 0

        for word in self.text.split():
            if word.lower() in stopwords:
                count += 1

        return count

    def stopwords_density(self, stopwords):
        words_count = self.words_count
        if words_count == 0:
            return 0

        return self.stopwords_count(stopwords) / words_count

    def links_density(self):
        text_length = len(self.text)
        if text_length == 0:
            return 0

        return self.chars_count_in_links / text_length

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import re
import os
import sys
import pkgutil


MULTIPLE_WHITESPACE_PATTERN = re.compile(r"\s+", re.UNICODE)
def normalize_whitespace(string):
    """Translates multiple white-space into single space."""
    return MULTIPLE_WHITESPACE_PATTERN.sub(" ", string)


def is_blank(string):
    """
    Returns `True` if string contains only white-space characters
    or is empty. Otherwise `False` is returned.
    """
    return not bool(string.lstrip())


def get_stoplists():
    """Returns a collection of built-in stop-lists."""
    path_to_stoplists = os.path.dirname(sys.modules["justext"].__file__)
    path_to_stoplists = os.path.join(path_to_stoplists, "stoplists")

    stoplist_names = []
    for filename in os.listdir(path_to_stoplists):
        name, extension = os.path.splitext(filename)
        if extension == ".txt":
            stoplist_names.append(name)

    return frozenset(stoplist_names)


def get_stoplist(language):
    """Returns an built-in stop-list for the language as a set of words."""
    file_path = os.path.join("stoplists", "%s.txt" % language)
    try:
        stopwords = pkgutil.get_data("justext", file_path)
    except IOError:
        raise ValueError(
            "Stoplist for language '%s' is missing. "
            "Please use function 'get_stoplists' for complete list of stoplists "
            "and feel free to contribute by your own stoplist." % language
        )

    return frozenset(w.decode("utf8").lower() for w in stopwords.splitlines())

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
    import urllib2 as urllib
    URLError = urllib.URLError
except ImportError:
    import urllib.request as urllib
    from urllib.error import URLError


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

########NEW FILE########
__FILENAME__ = __main__
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import re
import os
import sys
import cgi
import codecs

from .core import *
from ._compat import urllib, URLError


def usage():
    return """Usage: %(progname)s -s STOPLIST [OPTIONS] [HTML_FILE]
Convert HTML to plain text and remove boilerplate.

  -o OUTPUT_FILE   if not specified, output is written to stdout
  --encoding=...   default character encoding to be used if not specified
                   in the HTML meta tags (default: %(default_encoding)s)
  --enc-force      force specified encoding, ignore HTML meta tags
  --enc-errors=... errors handling for character encoding conversion:
                     strict: fail on error
                     ignore: ignore characters which can't be converted
                     replace: replace characters which can't be converted
                              with U+FFFD unicode replacement characters
                   (default: %(default_enc_errors)s)
  --format=...     output format; possible values:
                     default: one paragraph per line, each preceded with
                              <p> or <h> (headings)
                     boilerplate: same as default, except for boilerplate
                                  paragraphs are included, too, preceded
                                  with <b>
                     detailed: one paragraph per line, each preceded with
                               <p> tag containing detailed information
                               about classification as attributes
                     krdwrd: KrdWrd compatible format
  --no-headings    disable special handling of headings
  --list-stoplists print a list of inbuilt stoplists and exit
  -V, --version    print version information and exit
  -h, --help       display this help and exit

If no HTML_FILE specified, input is read from stdin.

STOPLIST must be one of the following:
  - one of the inbuilt stoplists; see:
      %(progname)s --list-stoplists
  - path to a file with the most frequent words for given language,
    one per line, in UTF-8 encoding
  - None - this activates a language-independent mode

Advanced options:
  --length-low=INT (default %(length_low)i)
  --length-high=INT (default %(length_high)i)
  --stopwords-low=FLOAT (default %(stopwords_low)f)
  --stopwords-high=FLOAT (default %(stopwords_high)f)
  --max-link-density=FLOAT (default %(max_link_density)f)
  --max-heading-distance=INT (default %(max_heading_distance)i)
""" % {
    'progname': os.path.basename(os.path.basename(sys.argv[0])),
    'length_low': LENGTH_LOW_DEFAULT,
    'length_high': LENGTH_HIGH_DEFAULT,
    'stopwords_low': STOPWORDS_LOW_DEFAULT,
    'stopwords_high': STOPWORDS_HIGH_DEFAULT,
    'max_link_density': MAX_LINK_DENSITY_DEFAULT,
    'max_heading_distance': MAX_HEADING_DISTANCE_DEFAULT,
    'default_encoding': DEFAULT_ENCODING,
    'default_enc_errors': DEFAULT_ENC_ERRORS,
}


def output_default(paragraphs, fp=sys.stdout, no_boilerplate=True):
    """
    Outputs the paragraphs as:
    <tag> text of the first paragraph
    <tag> text of the second paragraph
    ...
    where <tag> is <p>, <h> or <b> which indicates
    standard paragraph, heading or boilerplate respecitvely.
    """
    for paragraph in paragraphs:
        if paragraph.class_type == 'good':
            if paragraph.heading:
                tag = 'h'
            else:
                tag = 'p'
        elif no_boilerplate:
            continue
        else:
            tag = 'b'

        print('<%s> %s' % (tag, cgi.escape(paragraph.text)), file=fp)


def output_detailed(paragraphs, fp=sys.stdout):
    """
    Same as output_default, but only <p> tags are used and the following
    attributes are added: class, cfclass and heading.
    """
    for paragraph in paragraphs:
        output = '<p class="%s" cfclass="%s" heading="%i" xpath="%s"> %s' % (
            paragraph.class_type,
            paragraph.cf_class,
            int(paragraph.heading),
            paragraph.xpath,
            cgi.escape(paragraph.text)
        )
        print(output, file=fp)


def output_krdwrd(paragraphs, fp=sys.stdout):
    """
    Outputs the paragraphs in a KrdWrd compatible format:
    class<TAB>first text node
    class<TAB>second text node
    ...
    where class is 1, 2 or 3 which means
    boilerplate, undecided or good respectively. Headings are output as
    undecided.
    """
    for paragraph in paragraphs:
        if paragraph.class_type in ('good', 'neargood'):
            if paragraph.heading:
                cls = 2
            else:
                cls = 3
        else:
            cls = 1

        for text_node in paragraph.text_nodes:
            print('%i\t%s' % (cls, text_node.strip()), file=fp)


def main():
    import getopt
    from justext import __version__ as VERSION

    try:
        opts, args = getopt.getopt(sys.argv[1:], "o:s:hV", ["encoding=",
            "enc-force", "enc-errors=", "format=",
            "no-headings", "help", "version", "length-low=", "length-high=",
            "stopwords-low=", "stopwords-high=", "max-link-density=",
            "max-heading-distance=", "list-stoplists"])
    except getopt.GetoptError as e:
        print(e, file=sys.stderr)
        print(usage(), file=sys.stderr)
        sys.exit(1)

    stream_writer = codecs.lookup('utf8')[-1]
    fp_in = sys.stdin
    fp_out = stream_writer(sys.stdout)
    stoplist = None
    format = 'default'
    no_headings = False
    length_low = LENGTH_LOW_DEFAULT
    length_high = LENGTH_HIGH_DEFAULT
    stopwords_low = STOPWORDS_LOW_DEFAULT
    stopwords_high = STOPWORDS_HIGH_DEFAULT
    max_link_density = MAX_LINK_DENSITY_DEFAULT
    max_heading_distance = MAX_HEADING_DISTANCE_DEFAULT
    encoding = None
    default_encoding = DEFAULT_ENCODING
    force_default_encoding = False
    enc_errors = DEFAULT_ENC_ERRORS

    try:
        for o, a in opts:
            if o in ("-h", "--help"):
                print(usage())
                sys.exit(0)
            if o in ("-V", "--version"):
                print("%s: jusText v%s\n\nCopyright (c) 2011 Jan Pomikalek <jan.pomikalek@gmail.com>" % (
                    os.path.basename(sys.argv[0]), VERSION))
                sys.exit(0)
            elif o == "--list-stoplists":
                print("\n".join(get_stoplists()))
                sys.exit(0)
            elif o == "-o":
                try:
                    fp_out = codecs.open(a, 'w', 'utf8')
                except IOError as e:
                    raise JustextInvalidOptions(
                        "Can't open %s for writing: %s" % (a, e))
            elif o == "-s":
                if a.lower() == 'none':
                    stoplist = set()
                else:
                    if os.path.isfile(a):
                        try:
                            fp_stoplist = codecs.open(a, 'r', 'utf8')
                            stoplist = set([l.strip() for l in fp_stoplist])
                            fp_stoplist.close()
                        except IOError as e:
                            raise JustextInvalidOptions(
                                "Can't open %s for reading: %s" % (a, e))
                        except UnicodeDecodeError as e:
                            raise JustextInvalidOptions(
                                "Unicode decoding error when reading "
                                "the stoplist (probably not in UTF-8): %s" % e)
                    elif a in get_stoplists():
                        stoplist = get_stoplist(a)
                    else:
                        if re.match('^\w*$', a):
                            # only alphabetical chars, probably misspelled or
                            # unsupported language
                            raise JustextInvalidOptions(
                                "Unknown stoplist: %s\nAvailable stoplists:\n%s" % (
                                    a, '\n'.join(get_stoplists())))
                        else:
                            # probably incorrectly specified path
                            raise JustextInvalidOptions("File not found: %s" % a)
            elif o == "--encoding":
                try:
                    default_encoding = a
                    ''.encode(default_encoding)
                except LookupError:
                    raise JustextInvalidOptions("Uknown character encoding: %s" % a)
            elif o == "--enc-force":
                force_default_encoding = True
            elif o == "--enc-errors":
                if a.lower() in ['strict', 'ignore', 'replace']:
                    enc_errors = a.lower()
                else:
                    raise JustextInvalidOptions("Invalid --enc-errors value: %s" % a)
            elif o == "--format":
                if a in ['default', 'boilerplate', 'detailed', 'krdwrd']:
                    format = a
                else:
                    raise JustextInvalidOptions("Uknown output format: %s" % a)
            elif o == "--no-headings":
                no_headings = True
            elif o == "--length-low":
                try:
                    length_low = int(a)
                except ValueError:
                    raise JustextInvalidOptions(
                        "Invalid value for %s: '%s'. Integer expected." % (o, a))
            elif o == "--length-high":
                try:
                    length_high = int(a)
                except ValueError:
                    raise JustextInvalidOptions(
                        "Invalid value for %s: '%s'. Integer expected." % (o, a))
            elif o == "--stopwords-low":
                try:
                    stopwords_low = float(a)
                except ValueError:
                    raise JustextInvalidOptions(
                        "Invalid value for %s: '%s'. Float expected." % (o, a))
            elif o == "--stopwords-high":
                try:
                    stopwords_high = float(a)
                except ValueError:
                    raise JustextInvalidOptions(
                        "Invalid value for %s: '%s'. Float expected." % (o, a))
            elif o == "--max-link-density":
                try:
                    max_link_density = float(a)
                except ValueError:
                    raise JustextInvalidOptions(
                        "Invalid value for %s: '%s'. Float expected." % (o, a))
            elif o == "--max-heading-distance":
                try:
                    max_heading_distance = int(a)
                except ValueError:
                    raise JustextInvalidOptions(
                        "Invalid value for %s: '%s'. Integer expected." % (o, a))

        if force_default_encoding:
            encoding = default_encoding

        if stoplist is None:
            raise JustextInvalidOptions("No stoplist specified.")

        if not stoplist:
            # empty stoplist, switch to language-independent mode
            stopwords_high = 0
            stopwords_low = 0

        if args:
            try:
                if re.match(r"[^:/]+://", args[0]):
                    fp_in = urllib.urlopen(args[0])
                else:
                    fp_in = open(args[0], 'r')
            except (IOError, URLError) as e:
                raise JustextInvalidOptions(
                    "Can't open %s for reading: %s" % (args[0], e))
                sys.exit(1)

        html_text = fp_in.read()
        if fp_in is not sys.stdin:
            fp_in.close()

        paragraphs = justext(html_text, stoplist, length_low, length_high,
            stopwords_low, stopwords_high, max_link_density, max_heading_distance,
            no_headings, encoding, default_encoding, enc_errors)
        if format == "default":
            output_default(paragraphs, fp_out)
        elif format == "boilerplate":
            output_default(paragraphs, fp_out, no_boilerplate=False)
        elif format == "detailed":
            output_detailed(paragraphs, fp_out)
        elif format == "krdwrd":
            output_krdwrd(paragraphs, fp_out)
        else:
            # this should not happen; format checked when parsing options
            raise AssertionError("Unknown format: %s" % format)

    except JustextError as e:
        print("%s: %s" % (os.path.basename(sys.argv[0]), e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = test_classify_paragraphs
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import unittest

from nose import tools
from justext.core import PathInfo, classify_paragraphs
from justext.paragraph import Paragraph


class TestClassifyParagraphs(unittest.TestCase):
    def _paragraph(self, **kwargs):
        path = PathInfo().append("body").append("p")
        paragraph = Paragraph(path)

        for n, v in kwargs.items():
            if n == "text":
                paragraph.append_text(v)
            else:
                setattr(paragraph, n, v)

        return paragraph

    def test_max_link_density(self):
        paragraphs = [
            self._paragraph(text="0123456789"*2, chars_count_in_links=0),
            self._paragraph(text="0123456789"*2, chars_count_in_links=20),
            self._paragraph(text="0123456789"*8, chars_count_in_links=40),
            self._paragraph(text="0123456789"*8, chars_count_in_links=39),
            self._paragraph(text="0123456789"*8, chars_count_in_links=41),
        ]

        classify_paragraphs(paragraphs, (), max_link_density=0.5)

        tools.assert_equal(paragraphs[0].cf_class, "short")
        tools.assert_equal(paragraphs[1].cf_class, "bad")
        tools.assert_equal(paragraphs[2].cf_class, "bad")
        tools.assert_equal(paragraphs[3].cf_class, "bad")
        tools.assert_equal(paragraphs[4].cf_class, "bad")

    def test_length_low(self):
        paragraphs = [
            self._paragraph(text="0 1 2 3 4 5 6 7 8 9"*2, chars_count_in_links=0),
            self._paragraph(text="0 1 2 3 4 5 6 7 8 9"*2, chars_count_in_links=20),
        ]

        classify_paragraphs(paragraphs, (), max_link_density=1, length_low=1000)

        tools.assert_equal(paragraphs[0].cf_class, "short")
        tools.assert_equal(paragraphs[1].cf_class, "bad")

    def test_stopwords_high(self):
        paragraphs = [
            self._paragraph(text="0 1 2 3 4 5 6 7 8 9"),
            self._paragraph(text="0 1 2 3 4 5 6 7 8 9"*2),
        ]

        classify_paragraphs(paragraphs, ("0",), max_link_density=1, length_low=0,
            stopwords_high=0, length_high=20)

        tools.assert_equal(paragraphs[0].cf_class, "neargood")
        tools.assert_equal(paragraphs[1].cf_class, "good")

    def test_stopwords_low(self):
        paragraphs = [
            self._paragraph(text="0 0 0 0 1 2 3 4 5 6 7 8 9"),
            self._paragraph(text="0 1 2 3 4 5 6 7 8 9"),
            self._paragraph(text="1 2 3 4 5 6 7 8 9"),
        ]

        classify_paragraphs(paragraphs, ("0", "1",), max_link_density=1,
            length_low=0, stopwords_high=1000, stopwords_low=0.2)

        tools.assert_equal(paragraphs[0].cf_class, "neargood")
        tools.assert_equal(paragraphs[1].cf_class, "neargood")
        tools.assert_equal(paragraphs[2].cf_class, "bad")

########NEW FILE########
__FILENAME__ = test_dom_utils
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import unittest

from nose import tools
from lxml import html
from justext.core import preprocessor, html_to_dom


class TestDomUtils(unittest.TestCase):
    def test_remove_comments(self):
        dom = html.fromstring(
            '<html><!-- comment --><body>'
            '<h1>Header</h1>'
            '<!-- comment --> text'
            '<p>footer'
            '</body></html>'
        )

        expected = '<html><!-- comment --><body><h1>Header</h1><!-- comment --> text<p>footer</p></body></html>'
        returned = html.tostring(dom).decode("utf8")
        tools.assert_equal(expected, returned)

        dom = preprocessor(dom)

        expected = '<html><body><h1>Header</h1> text<p>footer</p></body></html>'
        returned = html.tostring(dom).decode("utf8")
        tools.assert_equal(expected, returned)

    def test_remove_head_tag(self):
        html_string = (
            '<html><head><title>Title</title></head><body>'
            '<h1>Header</h1>'
            '<p><span>text</span></p>'
            '<p>footer <em>like</em> a boss</p>'
            '</body></html>'
        )

        dom = html.fromstring(html_string)
        returned = html.tostring(dom).decode("utf8")
        tools.assert_equal(html_string, returned)

        dom = preprocessor(dom)
        returned = html.tostring(dom).decode("utf8")
        expected = (
            '<html><body>'
            '<h1>Header</h1>'
            '<p><span>text</span></p>'
            '<p>footer <em>like</em> a boss</p>'
            '</body></html>'
        )
        tools.assert_equal(expected, returned)

    def test_preprocess_simple_unicode_string(self):
        html_string = (
            '<html><head><title>Title</title></head><body>'
            '<h1>Header</h1>'
            '<p>pre<span>text</span>post<em>emph</em>popost</p>'
            '<p>footer <em>like</em> a boss</p>'
            '</body></html>'
        )

        dom = preprocessor(html_to_dom(html_string))
        returned = html.tostring(dom).decode("utf8")
        expected = (
            '<html><body>'
            '<h1>Header</h1>'
            '<p>pre<span>text</span>post<em>emph</em>popost</p>'
            '<p>footer <em>like</em> a boss</p>'
            '</body></html>'
        )
        tools.assert_equal(expected, returned)

    def test_preprocess_simple_bytes_string(self):
        html_string = (
            b'<html><head><title>Title</title></head><body>'
            b'<h1>Header</h1>'
            b'<p>pre<span>text</span>post<em>emph</em>popost</p>'
            b'<p>footer <em>like</em> a boss</p>'
            b'  <!-- abcdefgh -->\n'
            b'</body></html>'
        )

        dom = preprocessor(html_to_dom(html_string))
        returned = html.tostring(dom).decode("utf8")
        expected = (
            '<html><body>'
            '<h1>Header</h1>'
            '<p>pre<span>text</span>post<em>emph</em>popost</p>'
            '<p>footer <em>like</em> a boss</p>'
            '  \n'
            '</body></html>'
        )
        tools.assert_equal(expected, returned)

    def test_preprocess_simple_unicode_xhtml_string_with_declaration(self):
        html_string = (
            '<?xml version="1.0" encoding="windows-1250"?>'
            '<!DOCTYPE html>'
            '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="sk" lang="sk">'
            '<head>'
            '<title>Hello World</title>'
            '<meta http-equiv="imagetoolbar" content="no" />'
            '<meta http-equiv="Content-Type" content="text/html; charset=windows-1250" />'
            '</head>'
            '<body id="index">'
            '</body>'
            '</html>'
        )

        dom = preprocessor(html_to_dom(html_string))
        returned = html.tostring(dom).decode("utf8")
        expected = (
            '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="sk" lang="sk">'
            '<body id="index">'
            '</body>'
            '</html>'
        )
        tools.assert_equal(expected, returned)

    def test_preprocess_simple_bytes_xhtml_string_with_declaration(self):
        html_string = (
            b'<?xml version="1.0" encoding="windows-1250"?>'
            b'<!DOCTYPE html>'
            b'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="sk" lang="sk">'
            b'<head>'
            b'<title>Hello World</title>'
            b'<meta http-equiv="imagetoolbar" content="no" />'
            b'<meta http-equiv="Content-Type" content="text/html; charset=windows-1250" />'
            b'</head>'
            b'<body id="index">'
            b'</body>'
            b'</html>'
        )

        dom = preprocessor(html_to_dom(html_string))
        returned = html.tostring(dom).decode("utf8")
        expected = (
            '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="sk" lang="sk">'
            '<body id="index">'
            '</body>'
            '</html>'
        )
        tools.assert_equal(expected, returned)

########NEW FILE########
__FILENAME__ = test_html_encoding
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import unittest

from nose import tools
from justext.core import JustextError, decode_html


class TestHtmlEncoding(unittest.TestCase):
    def assert_strings_equal(self, s1, s2, *args):
        tools.assert_equal(type(s1), type(s2), *args)
        tools.assert_equal(s1, s2, *args)

    def test_unicode(self):
        html = "ľščťžýáíéäňúô Ł€"
        decoded_html = decode_html(html)

        self.assert_strings_equal(html, decoded_html)

    def test_utf8_bytes(self):
        html = "ľščťžýáíéäňúô Ł€"
        decoded_html = decode_html(html.encode("utf8"))

        self.assert_strings_equal(html, decoded_html)

    def test_meta_detection_1(self):
        html = '<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-2"/> ľščťžäňôě'
        decoded_html = decode_html(html.encode("iso-8859-2"))

        self.assert_strings_equal(html, decoded_html)

    def test_meta_detection_2(self):
        html = '<meta content=text/html; charset=iso-8859-2 http-equiv="Content-Type"/> ľščťžäňôě'
        decoded_html = decode_html(html.encode("iso-8859-2"))

        self.assert_strings_equal(html, decoded_html)

    def test_meta_detection_3(self):
        html = '<meta content=\'text/html; charset=iso-8859-2\' http-equiv="Content-Type"/> ľščťžäňôě'
        decoded_html = decode_html(html.encode("iso-8859-2"))

        self.assert_strings_equal(html, decoded_html)

    def test_meta_detection_4(self):
        html = '<meta charset=iso-8859-2/> ľščťžäňôě'
        decoded_html = decode_html(html.encode("iso-8859-2"))

        self.assert_strings_equal(html, decoded_html)

    def test_meta_detection_5(self):
        html = '<meta charset="iso-8859-2"/> ľščťžäňôě'
        decoded_html = decode_html(html.encode("iso-8859-2"))

        self.assert_strings_equal(html, decoded_html)

    def test_meta_detection_6(self):
        html = '<meta charset=iso-8859-2/> ľščťžäňôě'
        decoded_html = decode_html(html.encode("iso-8859-2"))

        self.assert_strings_equal(html, decoded_html)

    def test_meta_detection_7(self):
        html = '<meta charset=iso-8859-2> ľščťžäňôě'
        decoded_html = decode_html(html.encode("iso-8859-2"))

        self.assert_strings_equal(html, decoded_html)

    def test_meta_detection_8(self):
        html = '<meta charset=iso-8859-2> ľščťžäňôě'
        decoded_html = decode_html(html.encode("iso-8859-2"))

        self.assert_strings_equal(html, decoded_html)

    def test_meta_detection_9(self):
        html = '<meta content=text/html; charset=iso-8859-2 http-equiv="Content-Type"/> ľščťžäňôě'
        decoded_html = decode_html(html.encode("iso-8859-2"))

        self.assert_strings_equal(html, decoded_html)

    def test_meta_detection_charset_outside_1(self):
        html = '<meta charset="iso-8859-2"/> charset="iso-fake-29" ľščťžäňôě'
        decoded_html = decode_html(html.encode("iso-8859-2"))

        self.assert_strings_equal(html, decoded_html)

    def test_meta_detection_charset_outside_2(self):
        html = '<meta content=text/html; charset=iso-8859-2 http-equiv="Content-Type"/> charset="iso-fake-29" ľščťžäňôě'
        decoded_html = decode_html(html.encode("iso-8859-2"))

        self.assert_strings_equal(html, decoded_html)

    def test_meta_detection_charset_outside_3(self):
        html = '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; CHARSET=ISO-8859-2"> charset="iso-fake-29" ľščťžäňôě'
        decoded_html = decode_html(html.encode("iso-8859-2"))

        self.assert_strings_equal(html, decoded_html)

    def test_unknown_encoding_in_strict_mode(self):
        html = 'ľščťžäňôě'
        tools.assert_raises(JustextError, decode_html, html.encode("iso-8859-2"), errors='strict')

    def test_unknown_encoding_with_default_error_handler(self):
        html = 'ľščťžäňôě'
        decoded = decode_html(html.encode("iso-8859-2"), default_encoding="iso-8859-2")
        self.assertEqual(decoded, html)

    def test_default_encoding(self):
        html = 'ľščťžäňôě'
        decoded_html = decode_html(html.encode("iso-8859-2"), default_encoding="iso-8859-2")

        self.assert_strings_equal(html, decoded_html)

    def test_given_encoding(self):
        html = 'ľščťžäňôě'
        decoded_html = decode_html(html.encode("iso-8859-2"), encoding="iso-8859-2")

        self.assert_strings_equal(html, decoded_html)

    def test_given_wrong_encoding(self):
        html = 'ľščťžäňôě'
        decoded_html = decode_html(html.encode("iso-8859-2"), encoding="ASCII")

        self.assert_strings_equal("\ufffd" * len(html), decoded_html)

    def test_fake_encoding_in_meta(self):
        html = '<meta charset="iso-fake-2"/> ľščťžäňôě'

        tools.assert_raises(JustextError, decode_html, html.encode("iso-8859-2"), errors='strict')

########NEW FILE########
__FILENAME__ = test_paths
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import unittest

from justext.core import PathInfo


class TestPathInfo(unittest.TestCase):
    def test_empty_path(self):
        path = PathInfo()

        self.assertEqual(path.dom, "")
        self.assertEqual(path.xpath, "/")

    def test_path_with_root_only(self):
        path = PathInfo().append("html")

        self.assertEqual(path.dom, "html")
        self.assertEqual(path.xpath, "/html[1]")

    def test_path_with_more_elements(self):
        path = PathInfo().append("html").append("body").append("header").append("h1")

        self.assertEqual(path.dom, "html.body.header.h1")
        self.assertEqual(path.xpath, "/html[1]/body[1]/header[1]/h1[1]")

    def test_contains_multiple_tags_with_the_same_name(self):
        path = PathInfo().append("html").append("body").append("div")

        self.assertEqual(path.dom, "html.body.div")
        self.assertEqual(path.xpath, "/html[1]/body[1]/div[1]")

        path.pop().append("div")

        self.assertEqual(path.dom, "html.body.div")
        self.assertEqual(path.xpath, "/html[1]/body[1]/div[2]")

    def test_more_elements_in_tag(self):
        path = PathInfo().append("html").append("body").append("div")

        self.assertEqual(path.dom, "html.body.div")
        self.assertEqual(path.xpath, "/html[1]/body[1]/div[1]")

        path.pop()

        self.assertEqual(path.dom, "html.body")
        self.assertEqual(path.xpath, "/html[1]/body[1]")

        path.append("span")

        self.assertEqual(path.dom, "html.body.span")
        self.assertEqual(path.xpath, "/html[1]/body[1]/span[1]")

        path.pop()

        self.assertEqual(path.dom, "html.body")
        self.assertEqual(path.xpath, "/html[1]/body[1]")

        path.append("pre")

        self.assertEqual(path.dom, "html.body.pre")
        self.assertEqual(path.xpath, "/html[1]/body[1]/pre[1]")

    def test_removing_element(self):
        path = PathInfo().append("html").append("body")
        path.append("div").append("a").pop()

        self.assertEqual(path.dom, "html.body.div")
        self.assertEqual(path.xpath, "/html[1]/body[1]/div[1]")

        path.pop()

        self.assertEqual(path.dom, "html.body")
        self.assertEqual(path.xpath, "/html[1]/body[1]")

    def test_pop_on_empty_path_raises_exception(self):
        path = PathInfo()
        self.assertRaises(IndexError, path.pop)

########NEW FILE########
__FILENAME__ = test_sax
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import unittest

from nose import tools
from lxml import html
from justext.core import ParagraphMaker


class TestSax(unittest.TestCase):
    def assert_paragraphs_equal(self, paragraph, **kwargs):
        for name, value in kwargs.items():
            returned_value = getattr(paragraph, name)
            msg = "%s: %r != %r" % (name, value, returned_value)
            tools.assert_equal(value, returned_value, msg)

    def test_no_paragraphs(self):
        html_string = '<html><body></body></html>'
        dom = html.fromstring(html_string)

        returned = html.tostring(dom).decode("utf8")
        tools.assert_equal(html_string, returned)

        paragraphs = ParagraphMaker.make_paragraphs(dom)
        tools.assert_equal(len(paragraphs), 0)

    def test_basic(self):
        html_string = (
            '<html><body>'
            '<h1>Header</h1>'
            '<p>text and some <em>other</em> words <span class="class">that I</span> have in my head now</p>'
            '<p>footer</p>'
            '</body></html>'
        )
        dom = html.fromstring(html_string)

        returned = html.tostring(dom).decode("utf8")
        tools.assert_equal(html_string, returned)

        paragraphs = ParagraphMaker.make_paragraphs(dom)
        tools.assert_equal(len(paragraphs), 3)

        self.assert_paragraphs_equal(paragraphs[0], text="Header", words_count=1, tags_count=0)

        text = "text and some other words that I have in my head now"
        self.assert_paragraphs_equal(paragraphs[1], text=text, words_count=12, tags_count=2)

        self.assert_paragraphs_equal(paragraphs[2], text="footer", words_count=1, tags_count=0)

    def test_whitespace_handling(self):
        html_string = (
            '<html><body>'
            '<p>pre<em>in</em>post \t pre  <span class="class"> in </span>  post</p>'
            '<div>pre<em> in </em>post</div>'
            '<pre>pre<em>in </em>post</pre>'
            '<blockquote>pre<em> in</em>post</blockquote>'
            '</body></html>'
        )
        dom = html.fromstring(html_string)

        returned = html.tostring(dom).decode("utf8")
        tools.assert_equal(html_string, returned)

        paragraphs = ParagraphMaker.make_paragraphs(dom)
        tools.assert_equal(len(paragraphs), 4)

        self.assert_paragraphs_equal(paragraphs[0], text="preinpost pre in post",
            words_count=4, tags_count=2)

        self.assert_paragraphs_equal(paragraphs[1], text="pre in post",
            words_count=3, tags_count=1)

        self.assert_paragraphs_equal(paragraphs[2], text="prein post",
            words_count=2, tags_count=1)

        self.assert_paragraphs_equal(paragraphs[3], text="pre inpost",
            words_count=2, tags_count=1)

    def test_multiple_line_break(self):
        html_string = (
            '<html><body>'
            '  normal text   <br><br> another   text  '
            '</body></html>'
        )
        dom = html.fromstring(html_string)

        returned = html.tostring(dom).decode("utf8")
        tools.assert_equal(html_string, returned)

        paragraphs = ParagraphMaker.make_paragraphs(dom)
        tools.assert_equal(len(paragraphs), 2)

        self.assert_paragraphs_equal(paragraphs[0], text="normal text",
            words_count=2, tags_count=0)

        self.assert_paragraphs_equal(paragraphs[1], text="another text",
            words_count=2, tags_count=0)

    def test_inline_text_in_body(self):
        """Inline text should be treated as separate paragraph."""
        html_string = (
            '<html><body>'
            '<sup>I am <strong>top</strong>-inline\n\n\n\n and I am happy \n</sup>'
            '<p>normal text</p>'
            '<code>\nvar i = -INFINITY;\n</code>'
            '<div>after text with variable <var>N</var> </div>'
            '   I am inline\n\n\n\n and I am happy \n'
            '</body></html>'
        )
        dom = html.fromstring(html_string)

        paragraphs = ParagraphMaker.make_paragraphs(dom)
        tools.assert_equal(len(paragraphs), 5)

        self.assert_paragraphs_equal(paragraphs[0], words_count=7, tags_count=2,
            text="I am top-inline and I am happy")

        self.assert_paragraphs_equal(paragraphs[1], words_count=2, tags_count=0,
            text="normal text")

        self.assert_paragraphs_equal(paragraphs[2], words_count=4, tags_count=1,
            text="var i = -INFINITY;")

        self.assert_paragraphs_equal(paragraphs[3], words_count=5, tags_count=1,
            text="after text with variable N")

        self.assert_paragraphs_equal(paragraphs[4], words_count=7, tags_count=0,
            text="I am inline and I am happy")

    def test_links(self):
        """Inline text should be treated as separate paragraph."""
        html_string = (
            '<html><body>'
            '<a>I am <strong>top</strong>-inline\n\n\n\n and I am happy \n</a>'
            '<p>normal text</p>'
            '<code>\nvar i = -INFINITY;\n</code>'
            '<div>after <a>text</a> with variable <var>N</var> </div>'
            '   I am inline\n\n\n\n and I am happy \n'
            '</body></html>'
        )
        dom = html.fromstring(html_string)

        paragraphs = ParagraphMaker.make_paragraphs(dom)
        tools.assert_equal(len(paragraphs), 5)

        self.assert_paragraphs_equal(paragraphs[0], words_count=7, tags_count=2,
            text="I am top-inline and I am happy", chars_count_in_links=31)

        self.assert_paragraphs_equal(paragraphs[1], words_count=2, tags_count=0,
            text="normal text")

        self.assert_paragraphs_equal(paragraphs[2], words_count=4, tags_count=1,
            text="var i = -INFINITY;")

        self.assert_paragraphs_equal(paragraphs[3], words_count=5, tags_count=2,
            text="after text with variable N", chars_count_in_links=4)

        self.assert_paragraphs_equal(paragraphs[4], words_count=7, tags_count=0,
            text="I am inline and I am happy")

########NEW FILE########
__FILENAME__ = test_utils
# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import unittest

from nose import tools
from justext.utils import is_blank, normalize_whitespace, get_stoplists, get_stoplist


class TestStringUtils(unittest.TestCase):
    def test_empty_string_is_blank(self):
        tools.assert_true(is_blank(""))

    def test_string_with_space_is_blank(self):
        tools.assert_true(is_blank(" "))

    def test_string_with_nobreak_space_is_blank(self):
        tools.assert_true(is_blank("\u00A0\t "))

    def test_string_with_narrow_nobreak_space_is_blank(self):
        tools.assert_true(is_blank("\u202F \t"))

    def test_string_with_spaces_is_blank(self):
        tools.assert_true(is_blank("    "))

    def test_string_with_newline_is_blank(self):
        tools.assert_true(is_blank("\n"))

    def test_string_with_tab_is_blank(self):
        tools.assert_true(is_blank("\t"))

    def test_string_with_whitespace_is_blank(self):
        tools.assert_true(is_blank("\t\n "))

    def test_string_with_chars_is_not_blank(self):
        tools.assert_false(is_blank("  #  "))

    def test_normalize_no_change(self):
        string = "a b c d e f g h i j k l m n o p q r s ..."
        tools.assert_equal(string, normalize_whitespace(string))

    def test_normalize_dont_trim(self):
        string = "  a b c d e f g h i j k l m n o p q r s ...  "
        expected = " a b c d e f g h i j k l m n o p q r s ... "
        tools.assert_equal(expected, normalize_whitespace(string))

    def test_normalize_newline_and_tab(self):
        string = "123 \n456\t\n"
        expected = "123 456 "
        tools.assert_equal(expected, normalize_whitespace(string))

    def test_normalize_non_break_spaces(self):
        string = "\u00A0\t €\u202F \t"
        expected = " € "
        tools.assert_equal(expected, normalize_whitespace(string))


class TestStoplistsUtils(unittest.TestCase):
    def test_get_stopwords_list(self):
        stopwords = get_stoplists()

        tools.assert_equal(stopwords, frozenset((
            "Afrikaans", "Albanian", "Arabic", "Aragonese", "Armenian",
            "Aromanian", "Asturian", "Azerbaijani", "Basque", "Belarusian",
            "Belarusian_Taraskievica", "Bengali", "Bishnupriya_Manipuri",
            "Bosnian", "Breton", "Bulgarian", "Catalan", "Cebuano", "Croatian",
            "Czech", "Danish", "Dutch", "English", "Esperanto", "Estonian",
            "Finnish", "French", "Galician", "Georgian", "German", "Greek",
            "Gujarati", "Haitian", "Hebrew", "Hindi", "Hungarian", "Chuvash",
            "Icelandic", "Ido", "Igbo", "Indonesian", "Irish", "Italian",
            "Javanese", "Kannada", "Kazakh", "Korean", "Kurdish", "Kyrgyz",
            "Latin", "Latvian", "Lithuanian", "Lombard", "Low_Saxon",
            "Luxembourgish", "Macedonian", "Malay", "Malayalam", "Maltese",
            "Marathi", "Neapolitan", "Nepali", "Newar", "Norwegian_Bokmal",
            "Norwegian_Nynorsk", "Occitan", "Persian", "Piedmontese", "Polish",
            "Portuguese", "Quechua", "Romanian", "Russian", "Samogitian",
            "Serbian", "Serbo_Croatian", "Sicilian", "Simple_English", "Slovak",
            "Slovenian", "Spanish", "Sundanese", "Swahili", "Swedish",
            "Tagalog", "Tamil", "Telugu", "Turkish", "Turkmen", "Ukrainian",
            "Urdu", "Uzbek", "Vietnamese", "Volapuk", "Walloon", "Waray_Waray",
            "Welsh", "West_Frisian", "Western_Panjabi", "Yoruba",
        )))

    def test_get_real_stoplist(self):
        stopwords = get_stoplist("Slovak")

        tools.assert_true(len(stopwords) > 0)

    def test_get_missing_stoplist(self):
        tools.assert_raises(ValueError, get_stoplist, "Klingon")

########NEW FILE########
