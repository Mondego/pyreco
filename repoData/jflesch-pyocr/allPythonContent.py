__FILENAME__ = run_tests
#!/usr/bin/env python

import sys
sys.path = [ "src" ] + sys.path
import unittest

from pyocr import cuneiform
from pyocr import pyocr
from pyocr import tesseract

from tests import tests_cuneiform
from tests import tests_tesseract

if __name__ == '__main__':
    for tool in pyocr.TOOLS:
        print("- OCR: %s" % tool.get_name())
        available = tool.is_available()
        print("  is_available(): %s" % (str(available)))
        if available:
            print("  get_version(): %s" % (str(tool.get_version())))
            print("  get_available_languages(): ")
            print("    " + ", ".join(tool.get_available_languages()))
        print("")
    print("")

    print("OCR tool found:")
    for tool in pyocr.get_available_tools():
        print("- %s" % tool.get_name())
    if tesseract.is_available():
        print("---")
        print("Tesseract:")
        unittest.TextTestRunner().run(tests_tesseract.get_all_tests())
    if cuneiform.is_available():
        print("---")
        print("Cuneiform:")
        unittest.TextTestRunner().run(tests_cuneiform.get_all_tests())


########NEW FILE########
__FILENAME__ = builders
"""
Builders: Each builder specifies the expected output format

raw text : TextBuilder
words + boxes : WordBoxBuilder
lines + words + boxes : LineBoxBuilder
"""

try:
    from HTMLParser import HTMLParser
except ImportError:
    from html.parser import HTMLParser

import re
import xml

from .util import to_unicode

__all__ = [
    'Box',
    'TextBuilder',
    'WordBoxBuilder',
    'LineBoxBuilder',
]

_XHTML_HEADER = to_unicode("""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"
 "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<head>
\t<meta http-equiv="content-type" content="text/html; charset=utf-8" />
</head>
""")

class Box(object):
    """
    Boxes are rectangles around each individual element recognized in the
    image. Elements are either char or word depending of the builder that
    was used.
    """

    def __init__(self, content, position):
        """
        Arguments:
            content --- a single string
            position --- the position of the box on the image. Given as a
                tuple of tuple:
                ((width_pt_x, height_pt_x), (width_pt_y, height_pt_y))
        """
        if hasattr(content, 'decode'):
            content = to_unicode("%s") % content
        self.content = content
        self.position = position

    def get_unicode_string(self):
        """
        Return the string corresponding to the box, in unicode (utf8).
        This string can be stored in a file as-is (see write_box_file())
        and reread using read_box_file().
        """
        return to_unicode("%s %d %d %d %d") % (
            self.content,
            self.position[0][0],
            self.position[0][1],
            self.position[1][0],
            self.position[1][1],
        )

    def get_xml_tag(self, parent_doc):
        span_tag = parent_doc.createElement("span")
        span_tag.setAttribute("class", "ocrx_word")
        span_tag.setAttribute("title", ("bbox %d %d %d %d" % (
                (self.position[0][0], self.position[0][1],
                 self.position[1][0], self.position[1][1]))))
        txt = xml.dom.minidom.Text()
        txt.data = self.content.encode('utf-8')
        span_tag.appendChild(txt)
        return span_tag

    def __str__(self):
        return self.get_unicode_string().encode('utf-8')

    def __box_cmp(self, other):
        """
        Comparison function.
        """
        if other == None:
            return -1
        for (x, y) in ((self.position[0][1], other.position[0][1]),
                           (self.position[1][1], other.position[1][1]),
                           (self.position[0][0], other.position[0][0]),
                           (self.position[1][0], other.position[1][0])):
            if x < y:
                return -1
            elif x > y:
                return 1
        return 0

    def __lt__(self, other):
        return self.__box_cmp(other) < 0

    def __gt__(self, other):
        return self.__box_cmp(other) > 0

    def __eq__(self, other):
        return self.__box_cmp(other) == 0

    def __le__(self, other):
        return self.__box_cmp(other) <= 0

    def __ge__(self, other):
        return self.__box_cmp(other) >= 0

    def __ne__(self, other):
        return self.__box_cmp(other) != 0

    def __hash__(self):
        position_hash = 0
        position_hash += ((self.position[0][0] & 0xFF) << 0)
        position_hash += ((self.position[0][1] & 0xFF) << 8)
        position_hash += ((self.position[1][0] & 0xFF) << 16)
        position_hash += ((self.position[1][1] & 0xFF) << 24)
        return (position_hash ^ hash(self.content) ^ hash(self.content))


class LineBox(object):
    """
    Boxes are rectangles around each individual element recognized in the
    image. LineBox are boxes around lines. LineBox contains Box.
    """

    def __init__(self, word_boxes, position):
        """
        Arguments:
            word_boxes --- a single string
            position --- the position of the box on the image. Given as a
                tuple of tuple:
                ((width_pt_x, height_pt_x), (width_pt_y, height_pt_y))
        """
        self.word_boxes = word_boxes
        self.position = position

    def get_unicode_string(self):
        """
        Return the string corresponding to the box, in unicode (utf8).
        This string can be stored in a file as-is (see write_box_file())
        and reread using read_box_file().
        """
        txt = to_unicode("[\n")
        for box in self.word_boxes:
            txt += to_unicode("  %s\n") % box.get_unicode_string()
        return to_unicode("%s] %d %d %d %d") % (
            txt,
            self.position[0][0],
            self.position[0][1],
            self.position[1][0],
            self.position[1][1],
        )

    def __get_content(self):
        txt = to_unicode("")
        for box in self.word_boxes:
            txt += box.content + to_unicode(" ")
        txt = txt.strip()
        return txt

    content = property(__get_content)

    def get_xml_tag(self, parent_doc):
        span_tag = parent_doc.createElement("span")
        span_tag.setAttribute("class", "ocr_line")
        span_tag.setAttribute("title", ("bbox %d %d %d %d" % (
                (self.position[0][0], self.position[0][1],
                 self.position[1][0], self.position[1][1]))))
        for box in self.word_boxes:
            space = xml.dom.minidom.Text()
            space.data = " "
            span_tag.appendChild(space)
            box_xml = box.get_xml_tag(parent_doc)
            span_tag.appendChild(box_xml)
        return span_tag

    def __str__(self):
        return self.get_unicode_string().encode('utf-8')

    def __box_cmp(self, other):
        """
        Comparison function.
        """
        if other == None:
            return -1
        for (x, y) in ((self.position[0][1], other.position[0][1]),
                       (self.position[1][1], other.position[1][1]),
                       (self.position[0][0], other.position[0][0]),
                       (self.position[1][0], other.position[1][0])):
            if (x < y):
                return -1
            elif (x > y):
                return 1
        return 0

    def __lt__(self, other):
        return self.__box_cmp(other) < 0

    def __gt__(self, other):
        return self.__box_cmp(other) > 0

    def __eq__(self, other):
        return self.__box_cmp(other) == 0

    def __le__(self, other):
        return self.__box_cmp(other) <= 0

    def __ge__(self, other):
        return self.__box_cmp(other) >= 0

    def __ne__(self, other):
        return self.__box_cmp(other) != 0

    def __hash__(self):
        content = self.content
        position_hash = 0
        position_hash += ((self.position[0][0] & 0xFF) << 0)
        position_hash += ((self.position[0][1] & 0xFF) << 8)
        position_hash += ((self.position[1][0] & 0xFF) << 16)
        position_hash += ((self.position[1][1] & 0xFF) << 24)
        return (position_hash ^ hash(content) ^ hash(content))


class TextBuilder(object):
    """
    If passed to image_to_string(), image_to_string() will return a simple
    string. This string will be the output of the OCR tool, as-is. In other
    words, the raw text as produced by the tool.

    Warning:
        The returned string is encoded in UTF-8
    """

    file_extensions = ["txt"]
    tesseract_configs = []
    cuneiform_args = ["-f", "text"]

    def __init__(self, tesseract_layout=3):
        self.tesseract_configs = ["-psm", str(tesseract_layout)]
        pass

    @staticmethod
    def read_file(file_descriptor):
        """
        Read a file and extract the content as a string
        """
        return file_descriptor.read().strip()

    @staticmethod
    def write_file(file_descriptor, text):
        """
        Write a string in a file
        """
        file_descriptor.write(text)

    @staticmethod
    def __str__():
        return "Raw text"


class _WordHTMLParser(HTMLParser):
    """
    Tesseract style: Tesseract provides handy but non-standard hOCR tags:
    ocrx_word
    """

    def __init__(self):
        HTMLParser.__init__(self)

        self.__tag_types = []

        self.__current_box_position = None
        self.__current_box_text = None
        self.boxes = []

        self.__current_line_position = None
        self.__current_line_content = []
        self.lines = []

    @staticmethod
    def __parse_position(title):
        for piece in title.split("; "):
            piece = piece.strip()
            if not piece.startswith("bbox"):
                continue
            piece = piece.split(" ")
            position = ((int(piece[1]), int(piece[2])),
                        (int(piece[3]), int(piece[4])))
            return position
        raise Exception("Invalid hocr position: %s" % title)

    def handle_starttag(self, tag, attrs):
        if (tag != "span"):
            return
        position = None
        tag_type = None
        for attr in attrs:
            if attr[0] == 'class':
                tag_type = attr[1]
            if attr[0] == 'title':
                position = attr[1]
        if position is None or tag_type is None:
            return
        if tag_type == 'ocr_word' or tag_type == 'ocrx_word':
            try:
                position = self.__parse_position(position)
                self.__current_box_position = position
            except Exception:
                # invalid position --> old format --> we ignore this tag
                self.__tag_types.append("ignore")
                return
            self.__current_box_text = to_unicode("")
        elif tag_type == 'ocr_line':
            self.__current_line_position = self.__parse_position(position)
            self.__current_line_content = []
        self.__tag_types.append(tag_type)

    def handle_data(self, data):
        if self.__current_box_text == None:
            return
        data = to_unicode("%s") % data
        self.__current_box_text += data

    def handle_endtag(self, tag):
        if tag != 'span':
            return
        tag_type = self.__tag_types.pop()
        if tag_type == 'ocr_word' or tag_type == 'ocrx_word':
            if (self.__current_box_text == None):
                return
            box_position = self.__current_box_position
            box = Box(self.__current_box_text, box_position)
            self.boxes.append(box)
            self.__current_line_content.append(box)
            self.__current_box_text = None
            return
        elif tag_type == 'ocr_line':
            line = LineBox(self.__current_line_content,
                           self.__current_line_position)
            self.lines.append(line)
            self.__current_line_content = []
            return

    @staticmethod
    def __str__():
        return "WordHTMLParser"


class _LineHTMLParser(HTMLParser):
    """
    Cuneiform style: Cuneiform provides the OCR line by line, and for each
    line, the position of all its characters.
    Spaces have "-1 -1 -1 -1" for position".
    """
    def __init__(self):
        HTMLParser.__init__(self)
        self.boxes = []
        self.__line_text = None
        self.__char_positions = None

    def handle_starttag(self, tag, attrs):
        TAG_TYPE_CONTENT = 0
        TAG_TYPE_POSITIONS = 1

        if (tag != "span"):
            return
        tag_type = -1
        for attr in attrs:
            if attr[0] == 'class':
                if attr[1] == 'ocr_line':
                    tag_type = TAG_TYPE_CONTENT
                elif attr[1] == 'ocr_cinfo':
                    tag_type = TAG_TYPE_POSITIONS

        if tag_type == TAG_TYPE_CONTENT:
            self.__line_text = to_unicode("")
            self.__char_positions = []
            return
        elif tag_type == TAG_TYPE_POSITIONS:
            for attr in attrs:
                if attr[0] == 'title':
                    self.__char_positions = attr[1].split(" ")
            # strip x_bboxes
            self.__char_positions = self.__char_positions[1:]
            if self.__char_positions[-1] == "":
                self.__char_positions[:-1]
            try:
                while True:
                    self.__char_positions.remove("-1")
            except ValueError:
                pass

    def handle_data(self, data):
        if self.__line_text == None:
            return
        self.__line_text += data

    def handle_endtag(self, tag):
        if self.__line_text == None or self.__char_positions == []:
            return
        words = self.__line_text.split(" ")
        for word in words:
            if word == "":
                continue
            positions = self.__char_positions[0:4 * len(word)]
            self.__char_positions = self.__char_positions[4 * len(word):]

            left_pos = min([int(positions[x])
                            for x in range(0, 4 * len(word), 4)])
            top_pos = min([int(positions[x])
                           for x in range(1, 4 * len(word), 4)])
            right_pos = max([int(positions[x])
                             for x in range(2, 4 * len(word), 4)])
            bottom_pos = max([int(positions[x])
                              for x in range(3, 4 * len(word), 4)])

            box_pos = ((left_pos, top_pos), (right_pos, bottom_pos))
            box = Box(word, box_pos)
            self.boxes.append(box)
        self.__line_text = None

    @staticmethod
    def __str__():
        return "LineHTMLParser"


class WordBoxBuilder(object):
    """
    If passed to image_to_string(), image_to_string() will return an array of
    Box. Each box contains a word recognized in the image.
    """

    file_extensions = ["html", "hocr"]
    tesseract_configs = ['hocr']
    cuneiform_args = ["-f", "hocr"]

    def __init__(self):
        pass

    def read_file(self, file_descriptor):
        """
        Extract of set of Box from the lines of 'file_descriptor'

        Return:
            An array of Box.
        """
        parsers = [_WordHTMLParser(), _LineHTMLParser()]
        html_str = file_descriptor.read()

        for p in parsers:
            p.feed(html_str)
            if len(p.boxes) > 0:
                return p.boxes
        return []

    @staticmethod
    def write_file(file_descriptor, boxes):
        """
        Write boxes in a box file. Output is a *very* *simplified* version
        of hOCR.

        Warning:
            The file_descriptor must support UTF-8 ! (see module 'codecs')
        """
        global _XHTML_HEADER

        impl = xml.dom.minidom.getDOMImplementation()
        newdoc = impl.createDocument(None, "root", None)

        file_descriptor.write(_XHTML_HEADER)
        file_descriptor.write(to_unicode("<body>\n"))
        for box in boxes:
            xml_str = to_unicode("%s") % box.get_xml_tag(newdoc).toxml()
            file_descriptor.write(xml_str + to_unicode("<br/>\n"))
        file_descriptor.write(to_unicode("</body>\n"))

    @staticmethod
    def __str__():
        return "Word boxes"


class LineBoxBuilder(object):
    """
    If passed to image_to_string(), image_to_string() will return an array of
    LineBox. Each box contains a word recognized in the image.
    """

    file_extensions = ["html", "hocr"]
    tesseract_configs = ['hocr']
    cuneiform_args = ["-f", "hocr"]

    def __init__(self):
        pass

    def read_file(self, file_descriptor):
        """
        Extract of set of Box from the lines of 'file_descriptor'

        Return:
            An array of LineBox.
        """
        parsers = [
            (_WordHTMLParser(), lambda parser: parser.lines),
            (_LineHTMLParser(), lambda parser: [LineBox([box], box.position)
                                                for box in parser.boxes]),
        ]
        html_str = file_descriptor.read()

        for (parser, convertion) in parsers:
            parser.feed(html_str)
            if len(parser.boxes) > 0:
                return convertion(parser)
        return []

    @staticmethod
    def write_file(file_descriptor, boxes):
        """
        Write boxes in a box file. Output is a *very* *simplified* version
        of hOCR.

        Warning:
            The file_descriptor must support UTF-8 ! (see module 'codecs')
        """
        global _XHTML_HEADER

        impl = xml.dom.minidom.getDOMImplementation()
        newdoc = impl.createDocument(None, "root", None)

        file_descriptor.write(_XHTML_HEADER)
        file_descriptor.write(to_unicode("<body>\n"))
        for box in boxes:
            xml_str = box.get_xml_tag(newdoc).toxml()
            if hasattr(xml_str, 'decode'):
                xml_str = xml_str.decode('utf-8')
            file_descriptor.write(xml_str + to_unicode("<br/>\n"))
        file_descriptor.write(to_unicode("</body>\n"))

    @staticmethod
    def __str__():
        return "Line boxes"

########NEW FILE########
__FILENAME__ = cuneiform
#!/usr/bin/env python
'''
cuneiform.py is a wrapper for Cuneiform

USAGE:
 > from PIL import Image
 > from cuneiform import image_to_string
 > print image_to_string(Image.open('test.png'))
 > print image_to_string(Image.open('test-european.jpg'), lang='fra')

COPYRIGHT:
Pyocr is released under the GPL v3.
Copyright (c) Samuel Hoffstaetter, 2009
Copyright (c) Jerome Flesch, 2011-2012
https://github.com/jflesch/python-tesseract#readme
'''

import codecs
from io import BytesIO
import os
import re
import subprocess
import sys
import tempfile

from . import builders
from . import util


# CHANGE THIS IF CUNEIFORM IS NOT IN YOUR PATH, OR IS NAMED DIFFERENTLY
CUNEIFORM_CMD = 'cuneiform'

CUNEIFORM_DATA_POSSIBLE_PATHS = [
    "/usr/local/share/cuneiform",
    "/usr/share/cuneiform",
]

LANGUAGES_LINE_PREFIX = "Supported languages: "
LANGUAGES_SPLIT_RE = re.compile("[^a-z]")
VERSION_LINE_RE = re.compile("Cuneiform for \w+ (\d+).(\d+).(\d+)")

__all__ = [
    'get_available_builders',
    'get_available_languages',
    'get_name',
    'get_version',
    'image_to_string',
    'is_available',
    'CuneiformError',
]


def get_name():
    return "Cuneiform"


def get_available_builders():
    return [
        builders.TextBuilder,
        builders.WordBoxBuilder,
    ]


class CuneiformError(Exception):
    def __init__(self, status, message):
        Exception.__init__(self, message)
        self.status = status
        self.message = message
        self.args = (status, message)


def temp_file(suffix):
    ''' Returns a temporary file '''
    return tempfile.NamedTemporaryFile(prefix='cuneiform_', suffix=suffix)


def cleanup(filename):
    ''' Tries to remove the given filename. Ignores non-existent files '''
    try:
        os.remove(filename)
    except OSError:
        pass


def image_to_string(image, lang=None, builder=None):
    if builder == None:
        builder = builders.TextBuilder()

    with temp_file(builder.file_extensions[0]) as output_file:
        cmd = [CUNEIFORM_CMD]
        if lang != None:
            cmd += ["-l", lang]
        cmd += builder.cuneiform_args
        cmd += ["-o", output_file.name]
        cmd += ["-"]  # stdin

        img_data = BytesIO()
        image = image.convert("RGB")
        image.save(img_data, format="png")

        proc = subprocess.Popen(cmd,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        proc.stdin.write(img_data.getvalue())
        proc.stdin.close()
        output = proc.stdout.read().decode('utf-8')
        retcode = proc.wait()
        if retcode:
            raise CuneiformError(retcode, output)
        with codecs.open(output_file.name, 'r', encoding='utf-8',
                         errors='replace') as file_desc:
            results = builder.read_file(file_desc)
        return results


def is_available():
    return util.is_on_path(CUNEIFORM_CMD)


def get_available_languages():
    proc = subprocess.Popen([CUNEIFORM_CMD, "-l"], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    output = proc.stdout.read().decode('utf-8')
    proc.wait()
    languages = []
    for line in output.split("\n"):
        if not line.startswith(LANGUAGES_LINE_PREFIX):
            continue
        line = line[len(LANGUAGES_LINE_PREFIX):]
        for language in LANGUAGES_SPLIT_RE.split(line):
            if language == "":
                continue
            languages.append(language)
    return languages


def get_version():
    proc = subprocess.Popen([CUNEIFORM_CMD], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    output = proc.stdout.read().decode('utf-8')
    proc.wait()
    for line in output.split("\n"):
        m = VERSION_LINE_RE.match(line)
        g = m.groups()
        if m != None:
            ver = (int(g[0]), int(g[1]), int(g[2]))
            return ver
    return None

########NEW FILE########
__FILENAME__ = pyocr
#!/usr/bin/env python
"""
Wrapper for various OCR tools.

USAGE:
from PIL import Image
import sys
from pyocr import pyocr

tools = pyocr.get_available_tools()[:]
if len(tools) == 0:
    print("No OCR tool found")
    sys.exit(1)
print("Using '%s'" % (tools[0].get_name()))
tools[0].image_to_string(Image.open('test.png'), lang='fra',
                         builder=TextBuilder())


DETAILS:
Each module wrapping an OCR tool provides the following functions:
- get_name(): Return the name of the tool
- is_available(): Returns True if the tool is installed. False else.
- get_version(): Return a tuple containing the version of the tool (if
  installed)
- get_available_builders(): Returns a list of builders that can be used with
  this tool (see image_to_string())
- get_available_languages(): Returns a list of languages supported by this
  tool. Languages are usually written using ISO 3 letters country codes
- image_to_string():
    Takes 3 arguments:
    - an image (see python Imaging "Image" module) (mandatory)
    - lang=<language> (see get_available_languages()) (optional)
    - builder=<builder> (see get_available_builders() or the classes in the
      module 'pyocr.builders') (optional: default is
      pyocr.builders.TextBuilder)
    Returned value depends of the specified builder.


COPYRIGHT:
Pyocr is released under the GPL v3.
Copyright (c) Jerome Flesch, 2011
Tesseract module: Copyright (c) Samuel Hoffstaetter, 2009

WEBSITE:
https://github.com/jflesch/python-tesseract#readme
"""

from . import cuneiform
from . import tesseract

__all__ = [
    'get_available_tools',
    'TOOLS',
    'VERSION',
]


TOOLS = [  # in preference order
    tesseract,
    cuneiform,
]

VERSION = (0, 2, 3)

def get_available_tools():
    """
    Return a list of OCR tools available on the local system.
    """
    available = []
    for tool in TOOLS:
        if tool.is_available():
            available.append(tool)
    return available

########NEW FILE########
__FILENAME__ = tesseract
#!/usr/bin/env python
'''
tesseract.py is a wrapper for google's Tesseract-OCR
( http://code.google.com/p/tesseract-ocr/ ).

USAGE:
 > from PIL import Image
 > from tesseract import image_to_string
 > print(image_to_string(Image.open('test.png')))
 > print(image_to_string(Image.open('test-european.jpg'), lang='fra'))

COPYRIGHT:
Pyocr is released under the GPL v3.
Copyright (c) Samuel Hoffstaetter, 2009
Copyright (c) Jerome Flesch, 2011-2012
https://github.com/jflesch/python-tesseract#readme
'''

import codecs
import os
import subprocess
import sys
import tempfile
import xml.dom.minidom

from . import builders
from . import util


# CHANGE THIS IF TESSERACT IS NOT IN YOUR PATH, OR IS NAMED DIFFERENTLY
TESSERACT_CMD = 'tesseract'

TESSDATA_POSSIBLE_PATHS = [
    "/usr/local/share/tessdata",
    "/usr/share/tessdata",
    "/usr/share/tesseract/tessdata",
    "/usr/local/share/tesseract-ocr/tessdata",
    "/usr/share/tesseract-ocr/tessdata",
    "/app/vendor/tesseract-ocr/tessdata",  # Heroku
]

TESSDATA_EXTENSION = ".traineddata"


__all__ = [
    'CharBoxBuilder',
    'get_available_builders',
    'get_available_languages',
    'get_name',
    'get_version',
    'image_to_string',
    'is_available',
    'TesseractError',
]


class CharBoxBuilder(object):
    """
    If passed to image_to_string(), image_to_string() will return an array of
    Box. Each box correspond to a character recognized in the image.
    """

    file_extensions = ["box"]
    tesseract_configs = ['batch.nochop', 'makebox']

    def __init__(self):
        pass

    @staticmethod
    def read_file(file_descriptor):
        """
        Extract of set of Box from the lines of 'file_descriptor'

        Return:
            An array of Box.
        """
        boxes = []  # note that the order of the boxes may matter to the caller
        for line in file_descriptor.readlines():
            line = line.strip()
            if line == "":
                continue
            elements = line.split(" ")
            if len(elements) < 6:
                continue
            position = ((int(elements[1]), int(elements[2])),
                        (int(elements[3]), int(elements[4])))
            box = builders.Box(elements[0], position)
            boxes.append(box)
        return boxes

    @staticmethod
    def write_file(file_descriptor, boxes):
        """
        Write boxes in a box file. Output is in a the same format than
        tesseract's one.

        Warning:
            The file_descriptor must support UTF-8 ! (see module 'codecs')
        """
        for box in boxes:
            file_descriptor.write(box.get_unicode_string() + " 0\n")

    @staticmethod
    def __str__():
        return "Character boxes"


def get_name():
    return "Tesseract"


def get_available_builders():
    return [
        builders.TextBuilder,
        builders.WordBoxBuilder,
        CharBoxBuilder,
    ]


def run_tesseract(input_filename, output_filename_base, lang=None,
                  configs=None):
    '''
    Runs Tesseract:
        `TESSERACT_CMD` \
                `input_filename` \
                `output_filename_base` \
                [-l `lang`] \
                [`configs`]

    Arguments:
        input_filename --- image to read
        output_filename_base --- file name in which must be stored the result
            (without the extension)
        lang --- Tesseract language to use (if None, none will be specified)
        config --- List of Tesseract configs to use (if None, none will be
            specified)

    Returns:
        Returns (the exit status of Tesseract, Tesseract's output)
    '''

    command = [TESSERACT_CMD, input_filename, output_filename_base]

    if lang is not None:
        command += ['-l', lang]

    if configs != None:
        command += configs

    proc = subprocess.Popen(command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
    # Beware that in some cases, tesseract may print more on stderr than
    # allowed by the buffer of subprocess.Popen.stderr. So we must read stderr
    # asap or Tesseract will remain stuck when trying to write again on stderr.
    # In the end, we just have to make sure that proc.stderr.read() is called
    # before proc.wait()
    errors = proc.stdout.read()
    return (proc.wait(), errors)


def cleanup(filename):
    ''' Tries to remove the given filename. Ignores non-existent files '''
    try:
        os.remove(filename)
    except OSError:
        pass


def temp_file(suffix):
    ''' Returns a temporary file '''
    return tempfile.NamedTemporaryFile(prefix='tess_', suffix=suffix)


class TesseractError(Exception):
    """
    Exception raised when Tesseract fails.
    """
    def __init__(self, status, message):
        Exception.__init__(self, message)
        self.status = status
        self.message = message
        self.args = (status, message)


def image_to_string(image, lang=None, builder=None):
    '''
    Runs tesseract on the specified image. First, the image is written to disk,
    and then the tesseract command is run on the image. Tesseract's result is
    read, and the temporary files are erased.

    Arguments:
        image --- image to OCR
        lang --- tesseract language to use
        builder --- builder used to configure Tesseract and read its result.
            The builder is used to specify the type of output expected.
            Possible builders are TextBuilder or CharBoxBuilder. If builder ==
            None, the builder used will be TextBuilder.

    Returns:
        Depends of the specified builder. By default, it will return a simple
        string.
    '''

    if builder == None:
        builder = builders.TextBuilder()

    with temp_file(".bmp") as input_file:
        with temp_file('')  as output_file:
            output_file_name_base = output_file.name

        image = image.convert("RGB")
        image.save(input_file.name)
        (status, errors) = run_tesseract(input_file.name,
                                         output_file_name_base,
                                         lang=lang,
                                         configs=builder.tesseract_configs)
        if status:
            raise TesseractError(status, errors)

        output_file_name = "ERROR"
        for file_extension in builder.file_extensions:
            output_file_name = ('%s.%s' % (output_file_name_base,
                                           file_extension))
            if not os.access(output_file_name, os.F_OK):
                continue

            try:
                with codecs.open(output_file_name, 'r', encoding='utf-8',
                                 errors='replace') as file_desc:
                    results = builder.read_file(file_desc)
                return results
            finally:
                cleanup(output_file_name)
            break
        raise TesseractError(-1, "Unable to find output file"
                             " last name tried: %s" % output_file_name)


def is_available():
    return util.is_on_path(TESSERACT_CMD)


def get_available_languages():
    """
    Returns the list of languages that Tesseract knows how to handle.

    Returns:
        An array of strings. Note that most languages name conform to ISO 639
        terminology, but not all. Most of the time, truncating the language
        name name returned by this function to 3 letters should do the trick.
    """
    langs = []
    for dirpath in TESSDATA_POSSIBLE_PATHS:
        if not os.access(dirpath, os.R_OK):
            continue
        for filename in os.listdir(dirpath):
            if filename.lower().endswith(TESSDATA_EXTENSION):
                lang = filename[:(-1 * len(TESSDATA_EXTENSION))]
                langs.append(lang)
    return langs


def get_version():
    """
    Returns Tesseract version.

    Returns:
        A tuple corresponding to the version (for instance, (3, 0, 1) for 3.01)

    Exception:
        TesseractError --- Unable to run tesseract or to parse the version
    """
    command = [TESSERACT_CMD, "-v"]

    proc = subprocess.Popen(command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
    ver_string = proc.stdout.read()
    if hasattr(ver_string, 'decode'):
        ver_string = ver_string.decode('utf-8')
    ret = proc.wait()
    if not ret in (0, 1):
        raise TesseractError(ret, ver_string)

    try:
        els = ver_string.split(" ")[1].split(".")
        els = [int(x) for x in els]
        major = els[0]
        minor = els[1]
        upd = 0
        if len(els) >= 3:
            upd = els[2]
        return (major, minor, upd)
    except IndexError:
        raise TesseractError(ret,
                ("Unable to parse Tesseract version (spliting failed): [%s]"
                 % (ver_string)))
    except ValueError:
        raise TesseractError(ret,
                ("Unable to parse Tesseract version (not a number): [%s]"
                 % (ver_string)))


########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python

import os


def to_unicode(string):
    if hasattr(string, 'decode'):
        return string.decode('utf-8')
    return string


def is_on_path(exec_name):
    """
    Indicates if the command 'exec_name' appears to be installed.

    Returns:
        True --- if it is installed
        False --- if it isn't
    """
    for dirpath in os.environ["PATH"].split(os.pathsep):
        path = os.path.join(dirpath, exec_name)
        if os.path.exists(path) and os.access(path, os.X_OK):
            return True
    return False

########NEW FILE########
__FILENAME__ = tests_cuneiform
import codecs
from PIL import Image
import os
import sys
sys.path = [ "src" ] + sys.path
import tempfile

import unittest

from pyocr import builders
from pyocr import cuneiform


class TestContext(unittest.TestCase):
    """
    These tests make sure the requirements for the tests are met.
    """
    def setUp(self):
        pass

    def test_available(self):
        self.assertTrue(cuneiform.is_available(),
                       "cuneiform not found. Is it installed ?")

    def test_version(self):
        self.assertEqual(cuneiform.get_version(), (1, 1, 0),
                         ("cuneiform does not have the expected version"
                          " (1.1.0) ! Tests will fail !"))

    def test_langs(self):
        langs = cuneiform.get_available_languages()
        self.assertTrue("eng" in langs,
                        ("English training does not appear to be installed."
                         " (required for the tests)"))
        self.assertTrue("fra" in langs,
                        ("French training does not appear to be installed."
                         " (required for the tests)"))

    def tearDown(self):
        pass


class TestTxt(unittest.TestCase):
    """
    These tests make sure the "usual" OCR works fine. (the one generating
    a .txt file)
    """
    def setUp(self):
        pass

    def __test_txt(self, image_file, expected_output_file, lang='eng'):
        image_file = "tests/data/" + image_file
        expected_output_file = "tests/cuneiform/" + expected_output_file

        expected_output = ""
        with codecs.open(expected_output_file, 'r', encoding='utf-8') \
                as file_descriptor:
            for line in file_descriptor:
                expected_output += line
        expected_output = expected_output.strip()

        output = cuneiform.image_to_string(Image.open(image_file), lang=lang)

        self.assertEqual(output, expected_output)

    def test_basic(self):
        self.__test_txt('test.png', 'test.txt')

    def test_european(self):
        self.__test_txt('test-european.jpg', 'test-european.txt')

    def test_french(self):
        self.__test_txt('test-french.jpg', 'test-french.txt', 'fra')

    def tearDown(self):
        pass


class TestWordBox(unittest.TestCase):
    """
    These tests make sure that cuneiform box handling works fine.
    """
    def setUp(self):
        self.builder = builders.WordBoxBuilder()

    def __test_txt(self, image_file, expected_box_file, lang='eng'):
        image_file = "tests/data/" + image_file
        expected_box_file = "tests/cuneiform/" + expected_box_file

        with codecs.open(expected_box_file, 'r', encoding='utf-8') \
                as file_descriptor:
            expected_boxes = self.builder.read_file(file_descriptor)
        expected_boxes.sort()

        boxes = cuneiform.image_to_string(Image.open(image_file), lang=lang,
                                          builder=self.builder)
        boxes.sort()

        self.assertEqual(len(boxes), len(expected_boxes))

        for i in range(0, min(len(boxes), len(expected_boxes))):
            try:
                # Python 2.7
                self.assertEqual(type(expected_boxes[i].content), unicode)
                self.assertEqual(type(boxes[i].content), unicode)
            except NameError:
                # Python 3.x
                self.assertEqual(type(expected_boxes[i].content), str)
                self.assertEqual(type(boxes[i].content), str)
            self.assertEqual(boxes[i], expected_boxes[i])

    def test_basic(self):
        self.__test_txt('test.png', 'test.words')

    def test_european(self):
        self.__test_txt('test-european.jpg', 'test-european.words')

    def test_french(self):
        self.__test_txt('test-french.jpg', 'test-french.words', 'fra')

    def test_write_read(self):
        original_boxes = cuneiform.image_to_string(
            Image.open("tests/data/test.png"), builder=self.builder)
        self.assertTrue(len(original_boxes) > 0)

        (file_descriptor, tmp_path) = tempfile.mkstemp()
        try:
            # we must open the file with codecs.open() for utf-8 support
            os.close(file_descriptor)

            with codecs.open(tmp_path, 'w', encoding='utf-8') as file_descriptor:
                self.builder.write_file(file_descriptor, original_boxes)

            with codecs.open(tmp_path, 'r', encoding='utf-8') as file_descriptor:
                new_boxes = self.builder.read_file(file_descriptor)

            self.assertEqual(len(new_boxes), len(original_boxes))
            for i in range(0, len(original_boxes)):
                self.assertEqual(new_boxes[i], original_boxes[i])
        finally:
            os.remove(tmp_path)

    def tearDown(self):
        pass


def get_all_tests():
    all_tests = unittest.TestSuite()

    test_names = [
        'test_available',
        'test_version',
        'test_langs',
    ]
    tests = unittest.TestSuite(map(TestContext, test_names))
    all_tests.addTest(tests)

    test_names = [
        'test_basic',
        'test_european',
        'test_french',
    ]
    tests = unittest.TestSuite(map(TestTxt, test_names))
    all_tests.addTest(tests)

    test_names = [
        'test_basic',
        'test_european',
        'test_french',
        'test_write_read',
    ]
    tests = unittest.TestSuite(map(TestWordBox, test_names))
    all_tests.addTest(tests)

    return all_tests

########NEW FILE########
__FILENAME__ = tests_tesseract
import codecs
from PIL import Image
import os
import sys
sys.path = [ "src" ] + sys.path
import tempfile

import unittest

from pyocr import builders
from pyocr import tesseract


class TestContext(unittest.TestCase):
    """
    These tests make sure the requirements for the tests are met.
    """
    def setUp(self):
        pass

    def test_available(self):
        self.assertTrue(tesseract.is_available(),
                       "Tesseract not found. Is it installed ?")

    @unittest.skipIf(tesseract.get_version() != (3, 2, 1),
                     "This test only works with Tesseract 3.02.1")
    def test_version(self):
        self.assertEqual(tesseract.get_version(), (3, 2, 1),
                         ("Tesseract does not have the expected version"
                          " (3.02.1) ! Tests will fail !"))

    def test_langs(self):
        langs = tesseract.get_available_languages()
        self.assertTrue("eng" in langs,
                        ("English training does not appear to be installed."
                         " (required for the tests)"))
        self.assertTrue("fra" in langs,
                        ("French training does not appear to be installed."
                         " (required for the tests)"))
        self.assertTrue("jpn" in langs,
                        ("Japanese training does not appear to be installed."
                         " (required for the tests)"))


    def tearDown(self):
        pass


class TestTxt(unittest.TestCase):
    """
    These tests make sure the "usual" OCR works fine. (the one generating
    a .txt file)
    """
    def setUp(self):
        pass

    def __test_txt(self, image_file, expected_output_file, lang='eng'):
        image_file = "tests/data/" + image_file
        expected_output_file = "tests/tesseract/" + expected_output_file

        expected_output = ""
        with codecs.open(expected_output_file, 'r', encoding='utf-8') \
                as file_descriptor:
            for line in file_descriptor:
                expected_output += line
        expected_output = expected_output.strip()

        output = tesseract.image_to_string(Image.open(image_file), lang=lang)

        self.assertEqual(output, expected_output)


    def test_basic(self):
        self.__test_txt('test.png', 'test.txt')

    @unittest.skipIf(tesseract.get_version() != (3, 2, 1),
                     "This test only works with Tesseract 3.02.1")
    def test_european(self):
        self.__test_txt('test-european.jpg', 'test-european.txt')

    @unittest.skipIf(tesseract.get_version() != (3, 2, 1),
                     "This test only works with Tesseract 3.02.1")
    def test_french(self):
        self.__test_txt('test-french.jpg', 'test-french.txt', 'fra')

    def test_japanese(self):
        self.__test_txt('test-japanese.jpg', 'test-japanese.txt', 'jpn')

    def tearDown(self):
        pass


class TestCharBox(unittest.TestCase):
    """
    These tests make sure that Tesseract box handling works fine.
    """
    def setUp(self):
        self.builder = tesseract.CharBoxBuilder()

    def __test_txt(self, image_file, expected_box_file, lang='eng'):
        image_file = "tests/data/" + image_file
        expected_box_file = "tests/tesseract/" + expected_box_file

        with codecs.open(expected_box_file, 'r', encoding='utf-8') \
                as file_descriptor:
            expected_boxes = self.builder.read_file(file_descriptor)
        expected_boxes.sort()

        boxes = tesseract.image_to_string(Image.open(image_file), lang=lang,
                                          builder=self.builder)
        boxes.sort()

        self.assertEqual(len(boxes), len(expected_boxes))

        for i in range(0, min(len(boxes), len(expected_boxes))):
            self.assertEqual(boxes[i], expected_boxes[i])

    def test_basic(self):
        self.__test_txt('test.png', 'test.box')

    def test_european(self):
        self.__test_txt('test-european.jpg', 'test-european.box')

    def test_french(self):
        self.__test_txt('test-french.jpg', 'test-french.box', 'fra')

    @unittest.skipIf(tesseract.get_version() != (3, 2, 1),
                     "This test requires Tesseract 3.02.1")
    def test_japanese(self):
        self.__test_txt('test-japanese.jpg', 'test-japanese.box', 'jpn')

    def test_write_read(self):
        original_boxes = tesseract.image_to_string(
            Image.open("tests/data/test.png"), builder=self.builder)
        self.assertTrue(len(original_boxes) > 0)

        (file_descriptor, tmp_path) = tempfile.mkstemp()
        try:
            # we must open the file with codecs.open() for utf-8 support
            os.close(file_descriptor)

            with codecs.open(tmp_path, 'w', encoding='utf-8') as file_descriptor:
                self.builder.write_file(file_descriptor, original_boxes)

            with codecs.open(tmp_path, 'r', encoding='utf-8') as file_descriptor:
                new_boxes = self.builder.read_file(file_descriptor)

            self.assertEqual(len(new_boxes), len(original_boxes))
            for i in range(0, len(original_boxes)):
                self.assertEqual(new_boxes[i], original_boxes[i])
        finally:
            os.remove(tmp_path)

    def tearDown(self):
        pass


class TestWordBox(unittest.TestCase):
    """
    These tests make sure that Tesseract box handling works fine.
    """
    def setUp(self):
        self.builder = builders.WordBoxBuilder()

    def __test_txt(self, image_file, expected_box_file, lang='eng'):
        image_file = "tests/data/" + image_file
        expected_box_file = "tests/tesseract/" + expected_box_file

        with codecs.open(expected_box_file, 'r', encoding='utf-8') \
                as file_descriptor:
            expected_boxes = self.builder.read_file(file_descriptor)
        expected_boxes.sort()

        boxes = tesseract.image_to_string(Image.open(image_file), lang=lang,
                                          builder=self.builder)
        boxes.sort()

        self.assertTrue(len(boxes) > 0)
        self.assertEqual(len(boxes), len(expected_boxes))

        for i in range(0, min(len(boxes), len(expected_boxes))):
            try:
                # python 2.7
                self.assertEqual(type(expected_boxes[i].content), unicode)
                self.assertEqual(type(boxes[i].content), unicode)
            except NameError:
                # python 3
                self.assertEqual(type(expected_boxes[i].content), str)
                self.assertEqual(type(boxes[i].content), str)
            self.assertEqual(boxes[i], expected_boxes[i])

    def test_basic(self):
        self.__test_txt('test.png', 'test.words')

    def test_european(self):
        self.__test_txt('test-european.jpg', 'test-european.words')

    def test_french(self):
        self.__test_txt('test-french.jpg', 'test-french.words', 'fra')

    @unittest.skipIf(tesseract.get_version() != (3, 2, 1),
                     "This test requires Tesseract 3.02.1")
    def test_japanese(self):
        self.__test_txt('test-japanese.jpg', 'test-japanese.words', 'jpn')

    def test_write_read(self):
        original_boxes = tesseract.image_to_string(
            Image.open("tests/data/test.png"), builder=self.builder)
        self.assertTrue(len(original_boxes) > 0)

        (file_descriptor, tmp_path) = tempfile.mkstemp()
        try:
            # we must open the file with codecs.open() for utf-8 support
            os.close(file_descriptor)

            with codecs.open(tmp_path, 'w', encoding='utf-8') as file_descriptor:
                self.builder.write_file(file_descriptor, original_boxes)

            with codecs.open(tmp_path, 'r', encoding='utf-8') as file_descriptor:
                new_boxes = self.builder.read_file(file_descriptor)

            self.assertEqual(len(new_boxes), len(original_boxes))
            for i in range(0, len(original_boxes)):
                self.assertEqual(new_boxes[i], original_boxes[i])
        finally:
            os.remove(tmp_path)

    def tearDown(self):
        pass


class TestLineBox(unittest.TestCase):
    """
    These tests make sure that Tesseract box handling works fine.
    """
    def setUp(self):
        self.builder = builders.LineBoxBuilder()

    def __test_txt(self, image_file, expected_box_file, lang='eng'):
        image_file = "tests/data/" + image_file
        expected_box_file = "tests/tesseract/" + expected_box_file

        boxes = tesseract.image_to_string(Image.open(image_file), lang=lang,
                                          builder=self.builder)
        boxes.sort()

        with codecs.open(expected_box_file, 'r', encoding='utf-8') \
                as file_descriptor:
            expected_boxes = self.builder.read_file(file_descriptor)
        expected_boxes.sort()

        self.assertEqual(len(boxes), len(expected_boxes))

        for i in range(0, min(len(boxes), len(expected_boxes))):
            for j in range(0, len(boxes[i].word_boxes)):
                self.assertEqual(type(boxes[i].word_boxes[j]),
                                 type(expected_boxes[i].word_boxes[j]))
            self.assertEqual(boxes[i], expected_boxes[i])

    def test_basic(self):
        self.__test_txt('test.png', 'test.lines')

    def test_european(self):
        self.__test_txt('test-european.jpg', 'test-european.lines')

    def test_french(self):
        self.__test_txt('test-french.jpg', 'test-french.lines', 'fra')

    @unittest.skipIf(tesseract.get_version() != (3, 2, 1),
                     "This test requires Tesseract 3.02.1")
    def test_japanese(self):
        self.__test_txt('test-japanese.jpg', 'test-japanese.lines', 'jpn')

    def test_write_read(self):
        original_boxes = tesseract.image_to_string(
            Image.open("tests/data/test.png"), builder=self.builder)
        self.assertTrue(len(original_boxes) > 0)

        (file_descriptor, tmp_path) = tempfile.mkstemp()
        try:
            # we must open the file with codecs.open() for utf-8 support
            os.close(file_descriptor)

            with codecs.open(tmp_path, 'w', encoding='utf-8') as file_descriptor:
                self.builder.write_file(file_descriptor, original_boxes)

            with codecs.open(tmp_path, 'r', encoding='utf-8') as file_descriptor:
                new_boxes = self.builder.read_file(file_descriptor)

            self.assertEqual(len(new_boxes), len(original_boxes))
            for i in range(0, len(original_boxes)):
                self.assertEqual(new_boxes[i], original_boxes[i])
        finally:
            os.remove(tmp_path)

    def tearDown(self):
        pass

def get_all_tests():
    all_tests = unittest.TestSuite()

    test_names = [
        'test_available',
        'test_version',
        'test_langs',
    ]
    tests = unittest.TestSuite(map(TestContext, test_names))
    all_tests.addTest(tests)

    test_names = [
        'test_basic',
        'test_european',
        'test_french',
    ]
    tests = unittest.TestSuite(map(TestTxt, test_names))
    all_tests.addTest(tests)

    test_names = [
        'test_basic',
        'test_european',
        'test_french',
        'test_japanese',
        'test_write_read',
    ]
    tests = unittest.TestSuite(map(TestCharBox, test_names))
    all_tests.addTest(tests)
    tests = unittest.TestSuite(map(TestWordBox, test_names))
    all_tests.addTest(tests)
    tests = unittest.TestSuite(map(TestLineBox, test_names))
    all_tests.addTest(tests)

    return all_tests

########NEW FILE########
