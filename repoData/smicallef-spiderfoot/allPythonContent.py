__FILENAME__ = metapdf
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 Ali Anari
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""
.. module:: metapdf
   :platform: Unix, Windows
   :synopsis: The metapdf class implementation.

.. moduleauthor:: Ali Anari <ali@alianari.com>

"""

__author__ = "Ali Anari"
__author_email__ = "ali@alianari.com"


import os, re
from pyPdf import PdfFileReader


class _meta_pdf_reader(object):

    def __init__(self):
        self.instance = self.__hash__()
        self.metadata_regex = re.compile('(?:\/(\w+)\s?\(([^\n\r]*)\)\n?\r?)', re.S)
        self.metadata_offset = 2048

    def read_metadata(self, stream):

        """This function reads a PDF file stream and returns its metadata.
        :param file_name: The PDF file stream to read.
        :type file_name: str
        :returns: dict -- The returned metadata as a dictionary of properties.

        """

        # Scan the last 2048 bytes, the most
        # frequent metadata density block
        stream.seek(-self.metadata_offset, os.SEEK_END)
        properties = dict()
        try:
            properties = dict(('/' + p.group(1), p.group(2).decode('utf-8')) \
                for p in self.metadata_regex.finditer(stream.read(self.metadata_offset)))
            if '/Author' in properties:
                return properties
        except UnicodeDecodeError:
            properties.clear()

        # Parse the xref table using pyPdf
        properties = PdfFileReader(stream).documentInfo
        if properties:
            return properties

        return {}

_metaPdfReader = _meta_pdf_reader()
def MetaPdfReader(): return _metaPdfReader

########NEW FILE########
__FILENAME__ = contenttypes
# -*- coding: utf-8 -*-
"""
The various inner content types in an open XML document
"""
# $Id: contenttypes.py 6800 2007-12-04 11:17:01Z glenfant $

import os
from lxml import etree
import namespaces as ns
import utils

# Common properties
CT_CORE_PROPS = 'application/vnd.openxmlformats-package.core-properties+xml'
CT_EXT_PROPS = 'application/vnd.openxmlformats-officedocument.extended-properties+xml'
CT_CUSTOM_PROPS = 'application/vnd.openxmlformats-officedocument.custom-properties+xml'

# Wordprocessing document
# See...
# http://technet2.microsoft.com/Office/en-us/library/e077da98-0216-45eb-b6a7-957f9c510a851033.mspx?pf=true
# ...for the various
CT_WORDPROC_DOCX_PUBLIC = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
CT_WORDPROC_DOTX_PUBLIC = 'application/vnd.openxmlformats-officedocument.wordprocessingml.template'
CT_WORDPROC_DOCM_PUBLIC = 'application/vnd.ms-word.document.macroEnabled.12'
CT_WORDPROC_DOTM_PUBLIC = 'application/vnd.ms-word.template.macroEnabled.12'

CT_WORDPROC_DOCUMENT = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'
CT_WORDPROC_NUMBERING = 'application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml'
CT_WORDPROC_STYPES = 'application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml'
CT_WORDPROC_FONTS = 'application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml'
CT_WORDPROC_SETINGS = 'application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml'
CT_WORDPROC_FOOTNOTES = 'application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml'
CT_WORDPROC_ENDNOTES = 'application/vnd.openxmlformats-officedocument.wordprocessingml.endnotes+xml'
CT_WORDPROC_COMMENTS = 'application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml'

# Presentation document
CT_PRESENTATION_PPTX_PUBLIC = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
CT_PRESENTATION_PPTM_PUBLIC = 'application/vnd.ms-powerpoint.presentation.macroEnabled.12'
CT_PRESENTATION_PPSX_PUBLIC = 'application/vnd.openxmlformats-officedocument.presentationml.slideshow'
CT_PRESENTATION_PPSM_PUBLIC = 'application/vnd.ms-powerpoint.slideshow.macroEnabled.12'
CT_PRESENTATION_PPAM_PUBLIC = 'application/vnd.ms-powerpoint.addin.macroEnabled.12'
CT_PRESENTATION_POTX_PUBLIC = 'application/vnd.openxmlformats-officedocument.presentationml.template'
CT_PRESENTATION_POTM_PUBLIC = 'application/vnd.ms-powerpoint.template.macroEnabled.12'

# FIXME: Other presentation inner content types but useless for now...
CT_PRESENTATION_SLIDE = 'application/vnd.openxmlformats-officedocument.presentationml.slide+xml'

# Spreadsheet document
CT_SPREADSHEET_XLAM_PUBLIC = 'application/vnd.ms-excel.addin.macroEnabled.12'
CT_SPREADSHEET_XLSB_PUBLIC = 'application/vnd.ms-excel.sheet.binary.macroEnabled.12'
CT_SPREADSHEET_XLSM_PUBLIC = 'application/vnd.ms-excel.sheet.macroEnabled.12'
CT_SPREADSHEET_XLSX_PUBLIC = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
CT_SPREADSHEET_XLTM_PUBLIC = 'application/vnd.ms-excel.template.macroEnabled.12'
CT_SPREADSHEET_XLTX_PUBLIC = 'application/vnd.openxmlformats-officedocument.spreadsheetml.template'

# FIXME: Other spreadsheet inner content types but useless for now...
CT_SPREADSHEET_WORKSHEET = 'application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml'
CT_SPREADSHEET_SHAREDSTRINGS = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml'


class ContentTypes(object):
    """Handles features from the [Content_Types].xml file"""

    def __init__(self, content_types_file):
        """Constructor
        @param content_types_file: a file like object of [Content_Types].xml
        """

        self.overrides = {} # {subpart content type: [xml file, ...], ...}
        context = etree.iterparse(content_types_file, tag='{%s}Override' % ns.CONTENT_TYPES)
        for dummy, override in context:
            key = override.get('ContentType')
            if self.overrides.has_key(key):
                self.overrides[key].append(override.get('PartName'))
            else:
                self.overrides[key] = [override.get('PartName')]
        return


    def getPathsForContentType(self, content_type):
        """Finds the path in the document to that content type
        @param content_type: a MIME content type
        @return: list of paths in the content type
        """

        return self.overrides.get(content_type, [])


    def getTreesFor(self, document, content_type):
        """Provides all XML documents for that content type
        @param document: a Document or subclass object
        @param content_type: a MIME content type
        @return: list of etree._ElementTree of that content type
        """

        # Relative path without potential leading path separator
        # otherwise os.path.join doesn't work
        for rel_path in self.overrides[content_type]:
            if rel_path[0] in ('/', '\\'):
                rel_path = rel_path[1:]
            file_path = os.path.join(document._cache_dir, rel_path)
            yield etree.parse(utils.xmlFile(file_path, 'rb'))
        return


    @property
    def listMetaContentTypes(self):
        """The content types with metadata
        @return: ['application/xxx', ...]
        """

        all_md_content_types = (
            CT_CORE_PROPS,
            CT_EXT_PROPS,
            CT_CUSTOM_PROPS)
        return [k for k in self.overrides.keys() if k in all_md_content_types]


########NEW FILE########
__FILENAME__ = document
# -*- coding: utf-8 -*-
"""
The document modules handles an Open XML document
"""
# $Id$

import os
import tempfile
import zipfile
import shutil
import fnmatch
import urllib

import lxml

import contenttypes
from namespaces import ns_map
from utils import xmlFile
from utils import toUnicode


class Document(object):
    """Handling of Open XML document (all types)
    Must be subclassed for various types of documents (word processing, ...)
    Subclasses must provide these attributes:
    - _extpattern_to_mime: a mapping ({'*.ext': 'aplication/xxx'}, ...}
    - _text_extractors: a sequence of extractor objects that have:
      - content_type: attribute that the extractor can handle
      - indexableText(tree): method that returns a sequence of words from an lxml
        ElementTree object.
    """
    # These properties must be overriden by subclasses
    _extpattern_to_mime = {}
    _text_extractors = []

    def __init__(self, file_, mime_type=None):
        """Creating a new document
        @param file_: An opened file(like) obj to the document
        A file must be opened in 'rb' mode
        """
        self.mime_type = mime_type

        # Some shortcuts
        op_sep = os.path.sep
        op_join = os.path.join
        op_isdir = os.path.isdir
        op_dirname = os.path.dirname

        # Preliminary settings depending on input
        self.filename = getattr(file_, 'name', None)
        if self.filename is None and mime_type is None:
            raise ValueError("Cannot guess mime type from such object, you should use the mime_type constructor arg.")

        # Need to make a real file for urllib.urlopen objects
        if isinstance(file_, urllib.addinfourl):
            fh, self._cache_file = tempfile.mkstemp()
            fh = os.fdopen(fh, 'wb')
            fh.write(file_.read())
            fh.close()
            file_.close()
            file_ = open(self._cache_file, 'rb')

        # Inflating the file
        self._cache_dir = tempfile.mkdtemp()
        openxmldoc = zipfile.ZipFile(file_, 'r', zipfile.ZIP_DEFLATED)
        for outpath in openxmldoc.namelist():
            # We need to be sure that target dir exists
            rel_outpath = op_sep.join(outpath.split('/'))
            abs_outpath = op_join(self._cache_dir, rel_outpath)
            abs_outdir = op_dirname(abs_outpath)
            if not op_isdir(abs_outdir):
                os.makedirs(abs_outdir)
            fh = file(abs_outpath, 'wb')
            fh.write(openxmldoc.read(outpath))
            fh.close()
        openxmldoc.close()
        file_.close()

        # Getting the content types decl
        ct_file = op_join(self._cache_dir, '[Content_Types].xml')
        self.content_types = contenttypes.ContentTypes(xmlFile(ct_file, 'rb'))


    @property
    def mimeType(self):
        """The official MIME type for this document
        @return: 'application/xxx' for this file
        """
        if self.mime_type:
            # Supposed validated by the factory
            return self.mime_type
        for pattern, mime_type in self._extpattern_to_mime.items():
            if fnmatch.fnmatch(self.filename, pattern):
                return mime_type


    @property
    def coreProperties(self):
        """Document core properties
        @return: mapping of metadata
        """
        return self._tagValuedProperties(contenttypes.CT_CORE_PROPS)


    @property
    def extendedProperties(self):
        """Document extended properties
        @return: mapping of metadata
        """
        return self._tagValuedProperties(contenttypes.CT_EXT_PROPS)


    def _tagValuedProperties(self, content_type):
        """Document properties for property files having constructs like
         <ns:name>value</ns:name>
         @param content_type: contenttypes.CT_CORE_PROPS or contenttypes.CT_EXT_PROPS
         @return: mapping like {'property name': 'property value', ...}
        """
        rval = {}
        if not content_type in self.content_types.listMetaContentTypes:
            # We fail silently
            return rval
        for tree in self.content_types.getTreesFor(self, content_type):
            for elt in tree.getroot().getchildren():
                tag = elt.tag.split('}')[-1] # Removing namespace if any
                rval[toUnicode(tag)] = toUnicode(elt.text)
        return rval


    @property
    def customProperties(self):
        """Document custom properties
        @return: mapping of metadata
        FIXME: This is ugly. We do not convert the properties as indicated
        with the http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes
        namespace
        """
        rval = {}
        if len(self.content_types.getPathsForContentType(contenttypes.CT_CUSTOM_PROPS)) == 0:
            # We may have no custom properties at all.
            return rval
        XPath = lxml.etree.XPath # Class shortcut
        properties_xpath = XPath('custom-properties:property', namespaces=ns_map)
        propname_xpath = XPath('@name')
        propvalue_xpath = XPath('*/text()')
        for tree in self.content_types.getTreesFor(self, contenttypes.CT_CUSTOM_PROPS):
            for elt in properties_xpath(tree.getroot()):
                rval[toUnicode(propname_xpath(elt)[0])] = u" ".join(propvalue_xpath(elt))
        return rval


    @property
    def allProperties(self):
        """Helper that merges core, extended and custom properties
        @return: mapping of metadata
        """
        rval = {}
        rval.update(self.coreProperties)
        rval.update(self.extendedProperties)
        rval.update(self.customProperties)
        return rval


    def indexableText(self, include_properties=True):
        """Note that self._text_extractors must be overriden by subclasses
        """
        text = set()
        for extractor in self._text_extractors:
            for tree in self.content_types.getTreesFor(self, extractor.content_type):
                words = extractor.indexableText(tree)
                text |= words

        if include_properties:
            for prop_value in self.allProperties.values():
                if prop_value is not None:
                    text.add(prop_value)
        return u' '.join([word for word in text])

    def allText(self):
        trees = set()
        for content_type in self.content_types.overrides.keys():
            for tree in self.content_types.getTreesFor(self, content_type):
                trees.add(tree)
        for tree in trees:
            # textFromTree must be provided by subclasses
            yield self.textFromTree(tree)


    def __del__(self):
        """Cleanup at Document object deletion
        """
        self._cleanup()
        return


    def _cleanup(self):
        """Removing all temporary files
        Be warned that "cleanuping" your document makes it unusable.
        """
        if hasattr(self, '_cache_dir'):
            shutil.rmtree(self._cache_dir, ignore_errors=True)
        if hasattr(self, '_cache_file'):
            os.remove(self._cache_file)
        return


    @classmethod
    def canProcessMime(cls, mime_type):
        """Check if we can process such mime type
        @param mime_type: Mime type as 'application/xxx'
        @return: True if we can process such mime
        """
        supported_mimes = cls._extpattern_to_mime.values()
        return mime_type in supported_mimes


    @classmethod
    def canProcessFilename(cls, filename):
        """Check if we can process such file based on name
        @param filename: File name as 'mydoc.docx'
        @return: True if we can process such file
        """
        supported_patterns = cls._extpattern_to_mime.keys()
        for pattern in supported_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True
        return False


########NEW FILE########
__FILENAME__ = namespaces
# -*- coding: utf-8 -*-
"""
Namespaces that may be used in various XML files
"""
# $Id: namespaces.py 6800 2007-12-04 11:17:01Z glenfant $

CONTENT_TYPES = 'http://schemas.openxmlformats.org/package/2006/content-types'

# Properties (common for all openxml types)
CORE_PROPERTIES = 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties'
EXTENDED_PROPERTIES = 'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties'
CUSTOM_PROPERTIES = 'http://schemas.openxmlformats.org/officeDocument/2006/custom-properties'

# Wordprocessing
WP_MAIN = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

# Spreadsheet
SS_MAIN = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'

# Presentation
PR_MAIN = 'http://schemas.openxmlformats.org/drawingml/2006/main'

# Namespaces mapping useful for XPath expression shortcuts
ns_map = {
    'content-types': CONTENT_TYPES,
    'core-properties': CORE_PROPERTIES,
    'extended-properties': EXTENDED_PROPERTIES,
    'custom-properties': CUSTOM_PROPERTIES,
    'wordprocessing-main': WP_MAIN,
    'spreadsheet-main': SS_MAIN,
    'presentation-main': PR_MAIN
    }

########NEW FILE########
__FILENAME__ = presentation
# -*- coding: utf-8 -*-
"""
The presentation module handles a PresentationML Open XML document (read *.pptx)
"""
# $Id: presentation.py 6800 2007-12-04 11:17:01Z glenfant $

import document
from utils import IndexableTextExtractor
import contenttypes as ct
import namespaces

class PresentationDocument(document.Document):
    """Handles specific features of a PresentationML document
    """
    _extpattern_to_mime = {
        '*.pptx': ct.CT_PRESENTATION_PPTX_PUBLIC,
        '*.pptm': ct.CT_PRESENTATION_PPTM_PUBLIC,
        '*.potx': ct.CT_PRESENTATION_POTX_PUBLIC,
        '*.potm': ct.CT_PRESENTATION_POTM_PUBLIC,
        '*.ppsx': ct.CT_PRESENTATION_PPSX_PUBLIC,
        '*.ppsm': ct.CT_PRESENTATION_PPSM_PUBLIC,
        # FIXME: Not sure we can honour below types
#        '*.ppam': ct.CT_PRESENTATION_PPAM_PUBLIC
        }

    _text_extractors = (
        IndexableTextExtractor(ct.CT_PRESENTATION_SLIDE, 'presentation-main:t', separator=' '),
        )

    def textFromTree(self, tree):
        for text in tree.xpath('//presentation-main:t/text()', namespaces=namespaces.ns_map):
            yield ''.join(t.encode('utf-8') for t in text)


########NEW FILE########
__FILENAME__ = shell
#! python
# -*- coding: utf-8 -*-
# $Id: shell.py 61 2009-12-18 10:53:19Z gilles.lenfant $
"""Command line tool"""

import os
import optparse
import time
import codecs
import locale
import types
import openxmllib

DEFAULT_CHARSET = locale.getpreferredencoding()
USAGE = """%%prog [options] command file
Version: %s
%s
Commands:
* `metadata' shows the file's metadata.
* `words' shows all words from file."""
VERSION = openxmllib.version


class Application(object):
    """Command line utility showing openxml document informations."""

    def __init__(self):

        def check_charset_option(option, opt_str, value, parser):
            """Value must be a valid charset"""
            try:
                dummy = codecs.lookup(value)
            except LookupError, e:
                raise optparse.OptionValueError(
                    "Charset '%s' in unknown or not supported by your sytem."
                    % value)
            setattr(parser.values, option.dest, value)
            return

        parser = optparse.OptionParser(
            usage=USAGE % (VERSION, self.__class__.__doc__),
            version=VERSION)
        parser.add_option(
            '-c', '--charset', dest='charset', default=DEFAULT_CHARSET,
            type='string', action='callback', callback=check_charset_option,
            help="Converts output to this charset (default %s)" % DEFAULT_CHARSET
            )
        parser.add_option(
            '-v', '--verbosity', dest='verbosity', default=0, action='count',
            help="Adds verbosity for each '-v'")
        self.options, self.args = parser.parse_args()
        if (len(self.args) < 2
            or self.args[0] not in self.commands.keys()):
            parser.error("Invalid arguments")
        self.filenames = self.args[1:]
        return

    def run(self):
        self.commands[self.args[0]](self)
        return

    def metadataCmd(self):
        self.log(1, "Showing metadata of %s.", ", ".join(self.filenames))
        for filename in self.filenames:
            self.showMetadata(filename)
        return

    def wordsCmd(self):
        self.log(1, "Showing words of %s.", ", ".join(self.filenames))
        for filename in self.filenames:
            self.showWords(filename)
        return

    commands = {
        'metadata': metadataCmd,
        'words': wordsCmd
        }

    def showMetadata(self, filename):
        if not self.checkfile(filename):
            return
        self.log(1, "Processing %s...", filename)
        doc = openxmllib.openXmlDocument(path=filename)
        self.log(2, "Core properties:")
        for k, v in doc.coreProperties.items():
            print "%s: %s" % (self.recode(k), self.recode(v))
        self.log(2, "Extended properties:")
        for k, v in doc.extendedProperties.items():
            print "%s: %s" % (self.recode(k), self.recode(v))
        self.log(2, "Custom properties:")
        for k, v in doc.customProperties.items():
            print "%s: %s" % (self.recode(k), self.recode(v))
        return

    def showWords(self, filename):
        if not self.checkfile(filename):
            return
        self.log(1, "Processing %s...", filename)
        start_time = time.time()
        doc = openxmllib.openXmlDocument(path=filename)
        text = doc.indexableText(include_properties=False)
        duration = time.time() - start_time
        print self.recode(text)
        self.log(1, "Words extracted in %s second(s)", duration)
        return

    def checkfile(self, filename):
        if not os.path.isfile(filename):
            self.log(0, "'%s' is not a file, skipped", filename)
            return False
        return True

    def log(self, required_verbosity, message, *args):
        if self.options.verbosity >= required_verbosity:
            print message % args
        return

    def recode(self, utext):
        if type(utext) is types.UnicodeType:
            return utext.encode(self.options.charset, 'replace')
        return utext

def openxmlinfo():
    Application().run()
    return

########NEW FILE########
__FILENAME__ = spreadsheet
# -*- coding: utf-8 -*-
"""
The spreadsheet module handles a SpreadsheetML Open XML document (read *.xlsx)
"""
# $Id: spreadsheet.py 6800 2007-12-04 11:17:01Z glenfant $

import document
from utils import IndexableTextExtractor
import contenttypes as ct
import namespaces


class SpreadsheetDocument(document.Document):
    """Handles specific features of a SpreadsheetML document
    """
    _extpattern_to_mime = {
        '*.xlsx': ct.CT_SPREADSHEET_XLSX_PUBLIC,
        '*.xlsm': ct.CT_SPREADSHEET_XLSM_PUBLIC,
        '*.xltx': ct.CT_SPREADSHEET_XLTX_PUBLIC,
        '*.xltm': ct.CT_SPREADSHEET_XLTM_PUBLIC,
        # FIXME: note sure we can honour below types...
#        '*.xlam': ct.CT_SPREADSHEET_XLAM_PUBLIC,
#        '*.xlsb': ct.CT_SPREADSHEET_XLSB_PUBLIC
        }

    _text_extractors = (
        IndexableTextExtractor(ct.CT_SPREADSHEET_SHAREDSTRINGS, 'spreadsheet-main:t', separator=' '),
        )


    def textFromTree(self, tree):

        for text in tree.xpath('//spreadsheet-main:t/text()', namespaces=namespaces.ns_map):
            yield ''.join(t.encode('utf-8') for t in text)


########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
"""Various utilities for openxmllib"""
# $Id: utils.py 6800 2007-12-04 11:17:01Z glenfant $

import re
from lxml import etree

from namespaces import ns_map

def xmlFile(path, mode='r'):
    """lxml cannot parse XML files starting with a BOM
    (see http://www.w3.org/TR/2000/REC-xml-20001006 in F.1.)
    In case such XML file is used, we must skip these characters
    So we open all XML files for read with 'xmlFile'.
    TODO: File this issue to lxml ML or tracker (feature or bug ?)
    """
    fh = file(path, mode)
    while fh.read(1) != '<': # Ignoring everything before '<?xml...'
        pass
    fh.seek(-1, 1)
    return fh


def toUnicode(objekt):
    """Safely converts anything returned by lxml services to unicode
    @param objekt: anything
    @return: the object itself if not a string, otherwise the unicode of the string
    """
    if not isinstance(objekt, str):
        return objekt
    return unicode(objekt, 'utf-8')


class IndexableTextExtractor(object):

    wordssearch_rx = re.compile(r'\w+', re.UNICODE)
    text_extract_xpath = etree.XPath('text()')

    def __init__(self, content_type, *text_elements, **kwargs):
        """Building the extractor
        @param content_type: content_type of the part for which the extractor is defined
        @param text_elements: default text elements. See self.addTextElement(...)
        """
        self.content_type = content_type
        self.text_elts_xpaths = [etree.XPath('//' + te, namespaces=ns_map)
                                 for te in text_elements]
        if 'separator' in kwargs:
            self.separator = kwargs['separator']
        else:
            self.separator = ''
        return


    def indexableText(self, tree):
        """Provides the indexable - search engine oriented - raw text
        @param tree: an ElementTree
        @return: set(["foo", "bar", ...])
        """
        rval = set()
        root = tree.getroot()
        for txp in self.text_elts_xpaths:
            elts = txp(root)
            texts = []
            # Texts in element may be empty
            for elt in elts:
                text = self.text_extract_xpath(elt)
                if len(text) > 0:
                    texts.append(text[0])
            texts = self.separator.join(texts)
            texts = [toUnicode(x) for x in self.wordssearch_rx.findall(texts)
                     if len(x) > 0]
            rval |= set(texts)
        return rval


########NEW FILE########
__FILENAME__ = wordprocessing
# -*- coding: utf-8 -*-
"""The wordprocessing module handles a WordprocessingML Open XML document (read *.docx)"""
# $Id: wordprocessing.py 6800 2007-12-04 11:17:01Z glenfant $

import document
from utils import IndexableTextExtractor
import contenttypes as ct
import namespaces


class WordprocessingDocument(document.Document):
    """Handles specific features of a WordprocessingML document
    """
    _extpattern_to_mime = {
        '*.docx': ct.CT_WORDPROC_DOCX_PUBLIC,
        '*.docm': ct.CT_WORDPROC_DOCM_PUBLIC,
        '*.dotx': ct.CT_WORDPROC_DOTX_PUBLIC,
        '*.dotm': ct.CT_WORDPROC_DOTM_PUBLIC
        }

    _text_extractors = (
        IndexableTextExtractor(ct.CT_WORDPROC_DOCUMENT, 'wordprocessing-main:t', separator=''),
        )

    def textFromTree(self, tree):
        for paragraph in tree.xpath('//wordprocessing-main:p', namespaces=namespaces.ns_map):
            path = '%s//wordprocessing-main:t/text()' % tree.getpath(paragraph)
            nsmap = dict(paragraph.nsmap)
            nsmap.update(namespaces.ns_map)
            text = tree.xpath(path, namespaces=nsmap)
            yield ''.join(t.encode('utf-8') for t in text)


########NEW FILE########
__FILENAME__ = filters
# vim: sw=4:expandtab:foldmethod=marker
#
# Copyright (c) 2006, Mathieu Fenniak
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# * The name of the author may not be used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


"""
Implementation of stream filters for PDF.
"""
__author__ = "Mathieu Fenniak"
__author_email__ = "biziqe@mathieu.fenniak.net"

from utils import PdfReadError
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

try:
    import zlib
    def decompress(data):
        return zlib.decompress(data)
    def compress(data):
        return zlib.compress(data)
except ImportError:
    # Unable to import zlib.  Attempt to use the System.IO.Compression
    # library from the .NET framework. (IronPython only)
    import System
    from System import IO, Collections, Array
    def _string_to_bytearr(buf):
        retval = Array.CreateInstance(System.Byte, len(buf))
        for i in range(len(buf)):
            retval[i] = ord(buf[i])
        return retval
    def _bytearr_to_string(bytes):
        retval = ""
        for i in range(bytes.Length):
            retval += chr(bytes[i])
        return retval
    def _read_bytes(stream):
        ms = IO.MemoryStream()
        buf = Array.CreateInstance(System.Byte, 2048)
        while True:
            bytes = stream.Read(buf, 0, buf.Length)
            if bytes == 0:
                break
            else:
                ms.Write(buf, 0, bytes)
        retval = ms.ToArray()
        ms.Close()
        return retval
    def decompress(data):
        bytes = _string_to_bytearr(data)
        ms = IO.MemoryStream()
        ms.Write(bytes, 0, bytes.Length)
        ms.Position = 0  # fseek 0
        gz = IO.Compression.DeflateStream(ms, IO.Compression.CompressionMode.Decompress)
        bytes = _read_bytes(gz)
        retval = _bytearr_to_string(bytes)
        gz.Close()
        return retval
    def compress(data):
        bytes = _string_to_bytearr(data)
        ms = IO.MemoryStream()
        gz = IO.Compression.DeflateStream(ms, IO.Compression.CompressionMode.Compress, True)
        gz.Write(bytes, 0, bytes.Length)
        gz.Close()
        ms.Position = 0 # fseek 0
        bytes = ms.ToArray()
        retval = _bytearr_to_string(bytes)
        ms.Close()
        return retval


class FlateDecode(object):
    def decode(data, decodeParms):
        data = decompress(data)
        predictor = 1
        if decodeParms:
            predictor = decodeParms.get("/Predictor", 1)
        # predictor 1 == no predictor
        if predictor != 1:
            columns = decodeParms["/Columns"]
            # PNG prediction:
            if predictor >= 10 and predictor <= 15:
                output = StringIO()
                # PNG prediction can vary from row to row
                rowlength = columns + 1
                assert len(data) % rowlength == 0
                prev_rowdata = (0,) * rowlength
                for row in xrange(len(data) / rowlength):
                    rowdata = [ord(x) for x in data[(row*rowlength):((row+1)*rowlength)]]
                    filterByte = rowdata[0]
                    if filterByte == 0:
                        pass
                    elif filterByte == 1:
                        for i in range(2, rowlength):
                            rowdata[i] = (rowdata[i] + rowdata[i-1]) % 256
                    elif filterByte == 2:
                        for i in range(1, rowlength):
                            rowdata[i] = (rowdata[i] + prev_rowdata[i]) % 256
                    else:
                        # unsupported PNG filter
                        raise PdfReadError("Unsupported PNG filter %r" % filterByte)
                    prev_rowdata = rowdata
                    output.write(''.join([chr(x) for x in rowdata[1:]]))
                data = output.getvalue()
            else:
                # unsupported predictor
                raise PdfReadError("Unsupported flatedecode predictor %r" % predictor)
        return data
    decode = staticmethod(decode)

    def encode(data):
        return compress(data)
    encode = staticmethod(encode)

class ASCIIHexDecode(object):
    def decode(data, decodeParms=None):
        retval = ""
        char = ""
        x = 0
        while True:
            c = data[x]
            if c == ">":
                break
            elif c.isspace():
                x += 1
                continue
            char += c
            if len(char) == 2:
                retval += chr(int(char, base=16))
                char = ""
            x += 1
        assert char == ""
        return retval
    decode = staticmethod(decode)

class ASCII85Decode(object):
    def decode(data, decodeParms=None):
        retval = ""
        group = []
        x = 0
        hitEod = False
        # remove all whitespace from data
        data = [y for y in data if not (y in ' \n\r\t')]
        while not hitEod:
            c = data[x]
            if len(retval) == 0 and c == "<" and data[x+1] == "~":
                x += 2
                continue
            #elif c.isspace():
            #    x += 1
            #    continue
            elif c == 'z':
                assert len(group) == 0
                retval += '\x00\x00\x00\x00'
                continue
            elif c == "~" and data[x+1] == ">":
                if len(group) != 0:
                    # cannot have a final group of just 1 char
                    assert len(group) > 1
                    cnt = len(group) - 1
                    group += [ 85, 85, 85 ]
                    hitEod = cnt
                else:
                    break
            else:
                c = ord(c) - 33
                assert c >= 0 and c < 85
                group += [ c ]
            if len(group) >= 5:
                b = group[0] * (85**4) + \
                    group[1] * (85**3) + \
                    group[2] * (85**2) + \
                    group[3] * 85 + \
                    group[4]
                assert b < (2**32 - 1)
                c4 = chr((b >> 0) % 256)
                c3 = chr((b >> 8) % 256)
                c2 = chr((b >> 16) % 256)
                c1 = chr(b >> 24)
                retval += (c1 + c2 + c3 + c4)
                if hitEod:
                    retval = retval[:-4+hitEod]
                group = []
            x += 1
        return retval
    decode = staticmethod(decode)

def decodeStreamData(stream):
    from generic import NameObject
    filters = stream.get("/Filter", ())
    if len(filters) and not isinstance(filters[0], NameObject):
        # we have a single filter instance
        filters = (filters,)
    data = stream._data
    for filterType in filters:
        if filterType == "/FlateDecode":
            data = FlateDecode.decode(data, stream.get("/DecodeParms"))
        elif filterType == "/ASCIIHexDecode":
            data = ASCIIHexDecode.decode(data)
        elif filterType == "/ASCII85Decode":
            data = ASCII85Decode.decode(data)
        elif filterType == "/Crypt":
            decodeParams = stream.get("/DecodeParams", {})
            if "/Name" not in decodeParams and "/Type" not in decodeParams:
                pass
            else:
                raise NotImplementedError("/Crypt filter with /Name or /Type not supported yet")
        else:
            # unsupported filter
            raise NotImplementedError("unsupported filter %s" % filterType)
    return data

if __name__ == "__main__":
    assert "abc" == ASCIIHexDecode.decode('61\n626\n3>')

    ascii85Test = """
     <~9jqo^BlbD-BleB1DJ+*+F(f,q/0JhKF<GL>Cj@.4Gp$d7F!,L7@<6@)/0JDEF<G%<+EV:2F!,
     O<DJ+*.@<*K0@<6L(Df-\\0Ec5e;DffZ(EZee.Bl.9pF"AGXBPCsi+DGm>@3BB/F*&OCAfu2/AKY
     i(DIb:@FD,*)+C]U=@3BN#EcYf8ATD3s@q?d$AftVqCh[NqF<G:8+EV:.+Cf>-FD5W8ARlolDIa
     l(DId<j@<?3r@:F%a+D58'ATD4$Bl@l3De:,-DJs`8ARoFb/0JMK@qB4^F!,R<AKZ&-DfTqBG%G
     >uD.RTpAKYo'+CT/5+Cei#DII?(E,9)oF*2M7/c~>
    """
    ascii85_originalText="Man is distinguished, not only by his reason, but by this singular passion from other animals, which is a lust of the mind, that by a perseverance of delight in the continued and indefatigable generation of knowledge, exceeds the short vehemence of any carnal pleasure."
    assert ASCII85Decode.decode(ascii85Test) == ascii85_originalText


########NEW FILE########
__FILENAME__ = generic
# vim: sw=4:expandtab:foldmethod=marker
#
# Copyright (c) 2006, Mathieu Fenniak
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# * The name of the author may not be used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


"""
Implementation of generic PDF objects (dictionary, number, string, and so on)
"""
__author__ = "Mathieu Fenniak"
__author_email__ = "biziqe@mathieu.fenniak.net"

import re
from utils import readNonWhitespace, RC4_encrypt
import filters
import utils
import decimal
import codecs

def readObject(stream, pdf):
    tok = stream.read(1)
    stream.seek(-1, 1) # reset to start
    if tok == 't' or tok == 'f':
        # boolean object
        return BooleanObject.readFromStream(stream)
    elif tok == '(':
        # string object
        return readStringFromStream(stream)
    elif tok == '/':
        # name object
        return NameObject.readFromStream(stream)
    elif tok == '[':
        # array object
        return ArrayObject.readFromStream(stream, pdf)
    elif tok == 'n':
        # null object
        return NullObject.readFromStream(stream)
    elif tok == '<':
        # hexadecimal string OR dictionary
        peek = stream.read(2)
        stream.seek(-2, 1) # reset to start
        if peek == '<<':
            return DictionaryObject.readFromStream(stream, pdf)
        else:
            return readHexStringFromStream(stream)
    elif tok == '%':
        # comment
        while tok not in ('\r', '\n'):
            tok = stream.read(1)
        tok = readNonWhitespace(stream)
        stream.seek(-1, 1)
        return readObject(stream, pdf)
    else:
        # number object OR indirect reference
        if tok == '+' or tok == '-':
            # number
            return NumberObject.readFromStream(stream)
        peek = stream.read(20)
        stream.seek(-len(peek), 1) # reset to start
        if re.match(r"(\d+)\s(\d+)\sR[^a-zA-Z]", peek) != None:
            return IndirectObject.readFromStream(stream, pdf)
        else:
            return NumberObject.readFromStream(stream)

class PdfObject(object):
    def getObject(self):
        """Resolves indirect references."""
        return self


class NullObject(PdfObject):
    def writeToStream(self, stream, encryption_key):
        stream.write("null")

    def readFromStream(stream):
        nulltxt = stream.read(4)
        if nulltxt != "null":
            raise utils.PdfReadError, "error reading null object"
        return NullObject()
    readFromStream = staticmethod(readFromStream)


class BooleanObject(PdfObject):
    def __init__(self, value):
        self.value = value

    def writeToStream(self, stream, encryption_key):
        if self.value:
            stream.write("true")
        else:
            stream.write("false")

    def readFromStream(stream):
        word = stream.read(4)
        if word == "true":
            return BooleanObject(True)
        elif word == "fals":
            stream.read(1)
            return BooleanObject(False)
        assert False
    readFromStream = staticmethod(readFromStream)


class ArrayObject(list, PdfObject):
    def writeToStream(self, stream, encryption_key):
        stream.write("[")
        for data in self:
            stream.write(" ")
            data.writeToStream(stream, encryption_key)
        stream.write(" ]")

    def readFromStream(stream, pdf):
        arr = ArrayObject()
        tmp = stream.read(1)
        if tmp != "[":
            raise utils.PdfReadError, "error reading array"
        while True:
            # skip leading whitespace
            tok = stream.read(1)
            while tok.isspace():
                tok = stream.read(1)
            stream.seek(-1, 1)
            # check for array ending
            peekahead = stream.read(1)
            if peekahead == "]":
                break
            stream.seek(-1, 1)
            # read and append obj
            arr.append(readObject(stream, pdf))
        return arr
    readFromStream = staticmethod(readFromStream)


class IndirectObject(PdfObject):
    def __init__(self, idnum, generation, pdf):
        self.idnum = idnum
        self.generation = generation
        self.pdf = pdf

    def getObject(self):
        return self.pdf.getObject(self).getObject()

    def __repr__(self):
        return "IndirectObject(%r, %r)" % (self.idnum, self.generation)

    def __eq__(self, other):
        return (
            other != None and
            isinstance(other, IndirectObject) and
            self.idnum == other.idnum and
            self.generation == other.generation and
            self.pdf is other.pdf
            )

    def __ne__(self, other):
        return not self.__eq__(other)

    def writeToStream(self, stream, encryption_key):
        stream.write("%s %s R" % (self.idnum, self.generation))

    def readFromStream(stream, pdf):
        idnum = ""
        while True:
            tok = stream.read(1)
            if tok.isspace():
                break
            idnum += tok
        generation = ""
        while True:
            tok = stream.read(1)
            if tok.isspace():
                break
            generation += tok
        r = stream.read(1)
        if r != "R":
            raise utils.PdfReadError("error reading indirect object reference")
        return IndirectObject(int(idnum), int(generation), pdf)
    readFromStream = staticmethod(readFromStream)


class FloatObject(decimal.Decimal, PdfObject):
    def __new__(cls, value="0", context=None):
        return decimal.Decimal.__new__(cls, str(value), context)
    def __repr__(self):
        if self == self.to_integral():
            return str(self.quantize(decimal.Decimal(1)))
        else:
            # XXX: this adds useless extraneous zeros.
            return "%.5f" % self
    def writeToStream(self, stream, encryption_key):
        stream.write(repr(self))


class NumberObject(int, PdfObject):
    def __init__(self, value):
        int.__init__(value)

    def writeToStream(self, stream, encryption_key):
        stream.write(repr(self))

    def readFromStream(stream):
        name = ""
        while True:
            tok = stream.read(1)
            if tok != '+' and tok != '-' and tok != '.' and not tok.isdigit():
                stream.seek(-1, 1)
                break
            name += tok
        if name.find(".") != -1:
            return FloatObject(name)
        else:
            return NumberObject(name)
    readFromStream = staticmethod(readFromStream)


##
# Given a string (either a "str" or "unicode"), create a ByteStringObject or a
# TextStringObject to represent the string.
def createStringObject(string):
    if isinstance(string, unicode):
        return TextStringObject(string)
    elif isinstance(string, str):
        if string.startswith(codecs.BOM_UTF16_BE):
            retval = TextStringObject(string.decode("utf-16"))
            retval.autodetect_utf16 = True
            return retval
        else:
            # This is probably a big performance hit here, but we need to
            # convert string objects into the text/unicode-aware version if
            # possible... and the only way to check if that's possible is
            # to try.  Some strings are strings, some are just byte arrays.
            try:
                retval = TextStringObject(decode_pdfdocencoding(string))
                retval.autodetect_pdfdocencoding = True
                return retval
            except UnicodeDecodeError:
                return ByteStringObject(string)
    else:
        raise TypeError("createStringObject should have str or unicode arg")


def readHexStringFromStream(stream):
    stream.read(1)
    txt = ""
    x = ""
    while True:
        tok = readNonWhitespace(stream)
        if tok == ">":
            break
        x += tok
        if len(x) == 2:
            txt += chr(int(x, base=16))
            x = ""
    if len(x) == 1:
        x += "0"
    if len(x) == 2:
        txt += chr(int(x, base=16))
    return createStringObject(txt)


def readStringFromStream(stream):
    tok = stream.read(1)
    parens = 1
    txt = ""
    while True:
        tok = stream.read(1)
        if tok == "(":
            parens += 1
        elif tok == ")":
            parens -= 1
            if parens == 0:
                break
        elif tok == "\\":
            tok = stream.read(1)
            if tok == "n":
                tok = "\n"
            elif tok == "r":
                tok = "\r"
            elif tok == "t":
                tok = "\t"
            elif tok == "b":
                tok = "\b"
            elif tok == "f":
                tok = "\f"
            elif tok == "(":
                tok = "("
            elif tok == ")":
                tok = ")"
            elif tok == "\\":
                tok = "\\"
            elif tok.isdigit():
                # "The number ddd may consist of one, two, or three
                # octal digits; high-order overflow shall be ignored.
                # Three octal digits shall be used, with leading zeros
                # as needed, if the next character of the string is also
                # a digit." (PDF reference 7.3.4.2, p 16)
                for i in range(2):
                    ntok = stream.read(1)
                    if ntok.isdigit():
                        tok += ntok
                    else:
                        break
                tok = chr(int(tok, base=8))
            elif tok in "\n\r":
                # This case is  hit when a backslash followed by a line
                # break occurs.  If it's a multi-char EOL, consume the
                # second character:
                tok = stream.read(1)
                if not tok in "\n\r":
                    stream.seek(-1, 1)
                # Then don't add anything to the actual string, since this
                # line break was escaped:
                tok = ''
            else:
                raise utils.PdfReadError("Unexpected escaped string")
        txt += tok
    return createStringObject(txt)


##
# Represents a string object where the text encoding could not be determined.
# This occurs quite often, as the PDF spec doesn't provide an alternate way to
# represent strings -- for example, the encryption data stored in files (like
# /O) is clearly not text, but is still stored in a "String" object.
class ByteStringObject(str, PdfObject):

    ##
    # For compatibility with TextStringObject.original_bytes.  This method
    # returns self.
    original_bytes = property(lambda self: self)

    def writeToStream(self, stream, encryption_key):
        bytearr = self
        if encryption_key:
            bytearr = RC4_encrypt(encryption_key, bytearr)
        stream.write("<")
        stream.write(bytearr.encode("hex"))
        stream.write(">")


##
# Represents a string object that has been decoded into a real unicode string.
# If read from a PDF document, this string appeared to match the
# PDFDocEncoding, or contained a UTF-16BE BOM mark to cause UTF-16 decoding to
# occur.
class TextStringObject(unicode, PdfObject):
    autodetect_pdfdocencoding = False
    autodetect_utf16 = False

    ##
    # It is occasionally possible that a text string object gets created where
    # a byte string object was expected due to the autodetection mechanism --
    # if that occurs, this "original_bytes" property can be used to
    # back-calculate what the original encoded bytes were.
    original_bytes = property(lambda self: self.get_original_bytes())

    def get_original_bytes(self):
        # We're a text string object, but the library is trying to get our raw
        # bytes.  This can happen if we auto-detected this string as text, but
        # we were wrong.  It's pretty common.  Return the original bytes that
        # would have been used to create this object, based upon the autodetect
        # method.
        if self.autodetect_utf16:
            return codecs.BOM_UTF16_BE + self.encode("utf-16be")
        elif self.autodetect_pdfdocencoding:
            return encode_pdfdocencoding(self)
        else:
            raise Exception("no information about original bytes")

    def writeToStream(self, stream, encryption_key):
        # Try to write the string out as a PDFDocEncoding encoded string.  It's
        # nicer to look at in the PDF file.  Sadly, we take a performance hit
        # here for trying...
        try:
            bytearr = encode_pdfdocencoding(self)
        except UnicodeEncodeError:
            bytearr = codecs.BOM_UTF16_BE + self.encode("utf-16be")
        if encryption_key:
            bytearr = RC4_encrypt(encryption_key, bytearr)
            obj = ByteStringObject(bytearr)
            obj.writeToStream(stream, None)
        else:
            stream.write("(")
            for c in bytearr:
                if not c.isalnum() and c != ' ':
                    stream.write("\\%03o" % ord(c))
                else:
                    stream.write(c)
            stream.write(")")


class NameObject(str, PdfObject):
    delimiterCharacters = "(", ")", "<", ">", "[", "]", "{", "}", "/", "%"

    def __init__(self, data):
        str.__init__(data)

    def writeToStream(self, stream, encryption_key):
        stream.write(self)

    def readFromStream(stream):
        name = stream.read(1)
        if name != "/":
            raise utils.PdfReadError, "name read error"
        while True:
            tok = stream.read(1)
            if tok.isspace() or tok in NameObject.delimiterCharacters:
                stream.seek(-1, 1)
                break
            name += tok
        return NameObject(name)
    readFromStream = staticmethod(readFromStream)


class DictionaryObject(dict, PdfObject):

    def __init__(self, *args, **kwargs):
        if len(args) == 0:
            self.update(kwargs)
        elif len(args) == 1:
            arr = args[0]
            # If we're passed a list/tuple, make a dict out of it
            if not hasattr(arr, "iteritems"):
                newarr = {}
                for k, v in arr:
                    newarr[k] = v
                arr = newarr
            self.update(arr)
        else:
            raise TypeError("dict expected at most 1 argument, got 3")

    def update(self, arr):
        # note, a ValueError halfway through copying values
        # will leave half the values in this dict.
        for k, v in arr.iteritems():
            self.__setitem__(k, v)

    def raw_get(self, key):
        return dict.__getitem__(self, key)

    def __setitem__(self, key, value):
        if not isinstance(key, PdfObject):
            raise ValueError("key must be PdfObject")
        if not isinstance(value, PdfObject):
            raise ValueError("value must be PdfObject")
        return dict.__setitem__(self, key, value)

    def setdefault(self, key, value=None):
        if not isinstance(key, PdfObject):
            raise ValueError("key must be PdfObject")
        if not isinstance(value, PdfObject):
            raise ValueError("value must be PdfObject")
        return dict.setdefault(self, key, value)

    def __getitem__(self, key):
        return dict.__getitem__(self, key).getObject()

    ##
    # Retrieves XMP (Extensible Metadata Platform) data relevant to the
    # this object, if available.
    # <p>
    # Stability: Added in v1.12, will exist for all future v1.x releases.
    # @return Returns a {@link #xmp.XmpInformation XmlInformation} instance
    # that can be used to access XMP metadata from the document.  Can also
    # return None if no metadata was found on the document root.
    def getXmpMetadata(self):
        metadata = self.get("/Metadata", None)
        if metadata == None:
            return None
        metadata = metadata.getObject()
        import xmp
        if not isinstance(metadata, xmp.XmpInformation):
            metadata = xmp.XmpInformation(metadata)
            self[NameObject("/Metadata")] = metadata
        return metadata

    ##
    # Read-only property that accesses the {@link
    # #DictionaryObject.getXmpData getXmpData} function.
    # <p>
    # Stability: Added in v1.12, will exist for all future v1.x releases.
    xmpMetadata = property(lambda self: self.getXmpMetadata(), None, None)

    def writeToStream(self, stream, encryption_key):
        stream.write("<<\n")
        for key, value in self.items():
            key.writeToStream(stream, encryption_key)
            stream.write(" ")
            value.writeToStream(stream, encryption_key)
            stream.write("\n")
        stream.write(">>")

    def readFromStream(stream, pdf):
        tmp = stream.read(2)
        if tmp != "<<":
            raise utils.PdfReadError, "dictionary read error"
        data = {}
        while True:
            tok = readNonWhitespace(stream)
            if tok == ">":
                stream.read(1)
                break
            stream.seek(-1, 1)
            key = readObject(stream, pdf)
            tok = readNonWhitespace(stream)
            stream.seek(-1, 1)
            value = readObject(stream, pdf)
            if data.has_key(key):
                # multiple definitions of key not permitted
                raise utils.PdfReadError, "multiple definitions in dictionary"
            data[key] = value
        pos = stream.tell()
        s = readNonWhitespace(stream)
        if s == 's' and stream.read(5) == 'tream':
            eol = stream.read(1)
            # odd PDF file output has spaces after 'stream' keyword but before EOL.
            # patch provided by Danial Sandler
            while eol == ' ':
                eol = stream.read(1)
            assert eol in ("\n", "\r")
            if eol == "\r":
                # read \n after
                stream.read(1)
            # this is a stream object, not a dictionary
            assert data.has_key("/Length")
            length = data["/Length"]
            if isinstance(length, IndirectObject):
                t = stream.tell()
                length = pdf.getObject(length)
                stream.seek(t, 0)
            data["__streamdata__"] = stream.read(length)
            e = readNonWhitespace(stream)
            ndstream = stream.read(8)
            if (e + ndstream) != "endstream":
                # (sigh) - the odd PDF file has a length that is too long, so
                # we need to read backwards to find the "endstream" ending.
                # ReportLab (unknown version) generates files with this bug,
                # and Python users into PDF files tend to be our audience.
                # we need to do this to correct the streamdata and chop off
                # an extra character.
                pos = stream.tell()
                stream.seek(-10, 1)
                end = stream.read(9)
                if end == "endstream":
                    # we found it by looking back one character further.
                    data["__streamdata__"] = data["__streamdata__"][:-1]
                else:
                    stream.seek(pos, 0)
                    raise utils.PdfReadError, "Unable to find 'endstream' marker after stream."
        else:
            stream.seek(pos, 0)
        if data.has_key("__streamdata__"):
            return StreamObject.initializeFromDictionary(data)
        else:
            retval = DictionaryObject()
            retval.update(data)
            return retval
    readFromStream = staticmethod(readFromStream)


class StreamObject(DictionaryObject):
    def __init__(self):
        self._data = None
        self.decodedSelf = None

    def writeToStream(self, stream, encryption_key):
        self[NameObject("/Length")] = NumberObject(len(self._data))
        DictionaryObject.writeToStream(self, stream, encryption_key)
        del self["/Length"]
        stream.write("\nstream\n")
        data = self._data
        if encryption_key:
            data = RC4_encrypt(encryption_key, data)
        stream.write(data)
        stream.write("\nendstream")

    def initializeFromDictionary(data):
        if data.has_key("/Filter"):
            retval = EncodedStreamObject()
        else:
            retval = DecodedStreamObject()
        retval._data = data["__streamdata__"]
        del data["__streamdata__"]
        del data["/Length"]
        retval.update(data)
        return retval
    initializeFromDictionary = staticmethod(initializeFromDictionary)

    def flateEncode(self):
        if self.has_key("/Filter"):
            f = self["/Filter"]
            if isinstance(f, ArrayObject):
                f.insert(0, NameObject("/FlateDecode"))
            else:
                newf = ArrayObject()
                newf.append(NameObject("/FlateDecode"))
                newf.append(f)
                f = newf
        else:
            f = NameObject("/FlateDecode")
        retval = EncodedStreamObject()
        retval[NameObject("/Filter")] = f
        retval._data = filters.FlateDecode.encode(self._data)
        return retval


class DecodedStreamObject(StreamObject):
    def getData(self):
        return self._data

    def setData(self, data):
        self._data = data


class EncodedStreamObject(StreamObject):
    def __init__(self):
        self.decodedSelf = None

    def getData(self):
        if self.decodedSelf:
            # cached version of decoded object
            return self.decodedSelf.getData()
        else:
            # create decoded object
            decoded = DecodedStreamObject()
            decoded._data = filters.decodeStreamData(self)
            for key, value in self.items():
                if not key in ("/Length", "/Filter", "/DecodeParms"):
                    decoded[key] = value
            self.decodedSelf = decoded
            return decoded._data

    def setData(self, data):
        raise utils.PdfReadError, "Creating EncodedStreamObject is not currently supported"


class RectangleObject(ArrayObject):
    def __init__(self, arr):
        # must have four points
        assert len(arr) == 4
        # automatically convert arr[x] into NumberObject(arr[x]) if necessary
        ArrayObject.__init__(self, [self.ensureIsNumber(x) for x in arr])

    def ensureIsNumber(self, value):
        if not isinstance(value, (NumberObject, FloatObject)):
            value = FloatObject(value)
        return value

    def __repr__(self):
        return "RectangleObject(%s)" % repr(list(self))

    def getLowerLeft_x(self):
        return self[0]

    def getLowerLeft_y(self):
        return self[1]

    def getUpperRight_x(self):
        return self[2]

    def getUpperRight_y(self):
        return self[3]

    def getUpperLeft_x(self):
        return self.getLowerLeft_x()
    
    def getUpperLeft_y(self):
        return self.getUpperRight_y()

    def getLowerRight_x(self):
        return self.getUpperRight_x()

    def getLowerRight_y(self):
        return self.getLowerLeft_y()

    def getLowerLeft(self):
        return self.getLowerLeft_x(), self.getLowerLeft_y()

    def getLowerRight(self):
        return self.getLowerRight_x(), self.getLowerRight_y()

    def getUpperLeft(self):
        return self.getUpperLeft_x(), self.getUpperLeft_y()

    def getUpperRight(self):
        return self.getUpperRight_x(), self.getUpperRight_y()

    def setLowerLeft(self, value):
        self[0], self[1] = [self.ensureIsNumber(x) for x in value]

    def setLowerRight(self, value):
        self[2], self[1] = [self.ensureIsNumber(x) for x in value]

    def setUpperLeft(self, value):
        self[0], self[3] = [self.ensureIsNumber(x) for x in value]

    def setUpperRight(self, value):
        self[2], self[3] = [self.ensureIsNumber(x) for x in value]

    def getWidth(self):
        return self.getUpperRight_x() - self.getLowerLeft_x()

    def getHeight(self):
        return self.getUpperRight_y() - self.getLowerLeft_x()

    lowerLeft = property(getLowerLeft, setLowerLeft, None, None)
    lowerRight = property(getLowerRight, setLowerRight, None, None)
    upperLeft = property(getUpperLeft, setUpperLeft, None, None)
    upperRight = property(getUpperRight, setUpperRight, None, None)


def encode_pdfdocencoding(unicode_string):
    retval = ''
    for c in unicode_string:
        try:
            retval += chr(_pdfDocEncoding_rev[c])
        except KeyError:
            raise UnicodeEncodeError("pdfdocencoding", c, -1, -1,
                    "does not exist in translation table")
    return retval

def decode_pdfdocencoding(byte_array):
    retval = u''
    for b in byte_array:
        c = _pdfDocEncoding[ord(b)]
        if c == u'\u0000':
            raise UnicodeDecodeError("pdfdocencoding", b, -1, -1,
                    "does not exist in translation table")
        retval += c
    return retval

_pdfDocEncoding = (
  u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000',
  u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000',
  u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000',
  u'\u02d8', u'\u02c7', u'\u02c6', u'\u02d9', u'\u02dd', u'\u02db', u'\u02da', u'\u02dc',
  u'\u0020', u'\u0021', u'\u0022', u'\u0023', u'\u0024', u'\u0025', u'\u0026', u'\u0027',
  u'\u0028', u'\u0029', u'\u002a', u'\u002b', u'\u002c', u'\u002d', u'\u002e', u'\u002f',
  u'\u0030', u'\u0031', u'\u0032', u'\u0033', u'\u0034', u'\u0035', u'\u0036', u'\u0037',
  u'\u0038', u'\u0039', u'\u003a', u'\u003b', u'\u003c', u'\u003d', u'\u003e', u'\u003f',
  u'\u0040', u'\u0041', u'\u0042', u'\u0043', u'\u0044', u'\u0045', u'\u0046', u'\u0047',
  u'\u0048', u'\u0049', u'\u004a', u'\u004b', u'\u004c', u'\u004d', u'\u004e', u'\u004f',
  u'\u0050', u'\u0051', u'\u0052', u'\u0053', u'\u0054', u'\u0055', u'\u0056', u'\u0057',
  u'\u0058', u'\u0059', u'\u005a', u'\u005b', u'\u005c', u'\u005d', u'\u005e', u'\u005f',
  u'\u0060', u'\u0061', u'\u0062', u'\u0063', u'\u0064', u'\u0065', u'\u0066', u'\u0067',
  u'\u0068', u'\u0069', u'\u006a', u'\u006b', u'\u006c', u'\u006d', u'\u006e', u'\u006f',
  u'\u0070', u'\u0071', u'\u0072', u'\u0073', u'\u0074', u'\u0075', u'\u0076', u'\u0077',
  u'\u0078', u'\u0079', u'\u007a', u'\u007b', u'\u007c', u'\u007d', u'\u007e', u'\u0000',
  u'\u2022', u'\u2020', u'\u2021', u'\u2026', u'\u2014', u'\u2013', u'\u0192', u'\u2044',
  u'\u2039', u'\u203a', u'\u2212', u'\u2030', u'\u201e', u'\u201c', u'\u201d', u'\u2018',
  u'\u2019', u'\u201a', u'\u2122', u'\ufb01', u'\ufb02', u'\u0141', u'\u0152', u'\u0160',
  u'\u0178', u'\u017d', u'\u0131', u'\u0142', u'\u0153', u'\u0161', u'\u017e', u'\u0000',
  u'\u20ac', u'\u00a1', u'\u00a2', u'\u00a3', u'\u00a4', u'\u00a5', u'\u00a6', u'\u00a7',
  u'\u00a8', u'\u00a9', u'\u00aa', u'\u00ab', u'\u00ac', u'\u0000', u'\u00ae', u'\u00af',
  u'\u00b0', u'\u00b1', u'\u00b2', u'\u00b3', u'\u00b4', u'\u00b5', u'\u00b6', u'\u00b7',
  u'\u00b8', u'\u00b9', u'\u00ba', u'\u00bb', u'\u00bc', u'\u00bd', u'\u00be', u'\u00bf',
  u'\u00c0', u'\u00c1', u'\u00c2', u'\u00c3', u'\u00c4', u'\u00c5', u'\u00c6', u'\u00c7',
  u'\u00c8', u'\u00c9', u'\u00ca', u'\u00cb', u'\u00cc', u'\u00cd', u'\u00ce', u'\u00cf',
  u'\u00d0', u'\u00d1', u'\u00d2', u'\u00d3', u'\u00d4', u'\u00d5', u'\u00d6', u'\u00d7',
  u'\u00d8', u'\u00d9', u'\u00da', u'\u00db', u'\u00dc', u'\u00dd', u'\u00de', u'\u00df',
  u'\u00e0', u'\u00e1', u'\u00e2', u'\u00e3', u'\u00e4', u'\u00e5', u'\u00e6', u'\u00e7',
  u'\u00e8', u'\u00e9', u'\u00ea', u'\u00eb', u'\u00ec', u'\u00ed', u'\u00ee', u'\u00ef',
  u'\u00f0', u'\u00f1', u'\u00f2', u'\u00f3', u'\u00f4', u'\u00f5', u'\u00f6', u'\u00f7',
  u'\u00f8', u'\u00f9', u'\u00fa', u'\u00fb', u'\u00fc', u'\u00fd', u'\u00fe', u'\u00ff'
)

assert len(_pdfDocEncoding) == 256

_pdfDocEncoding_rev = {}
for i in xrange(256):
    char = _pdfDocEncoding[i]
    if char == u"\u0000":
        continue
    assert char not in _pdfDocEncoding_rev
    _pdfDocEncoding_rev[char] = i


########NEW FILE########
__FILENAME__ = pdf
# -*- coding: utf-8 -*-
#
# vim: sw=4:expandtab:foldmethod=marker
#
# Copyright (c) 2006, Mathieu Fenniak
# Copyright (c) 2007, Ashish Kulkarni <kulkarni.ashish@gmail.com>
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# * The name of the author may not be used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


"""
A pure-Python PDF library with very minimal capabilities.  It was designed to
be able to split and merge PDF files by page, and that's about all it can do.
It may be a solid base for future PDF file work in Python.
"""
__author__ = "Mathieu Fenniak"
__author_email__ = "biziqe@mathieu.fenniak.net"

import math
import struct
from sys import version_info
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import filters
import utils
import warnings
from generic import *
from utils import readNonWhitespace, readUntilWhitespace, ConvertFunctionsToVirtualList

if version_info < ( 2, 4 ):
   from sets import ImmutableSet as frozenset

if version_info < ( 2, 5 ):
    from md5 import md5
else:
    from hashlib import md5

##
# This class supports writing PDF files out, given pages produced by another
# class (typically {@link #PdfFileReader PdfFileReader}).
class PdfFileWriter(object):
    def __init__(self):
        self._header = "%PDF-1.3"
        self._objects = []  # array of indirect objects

        # The root of our page tree node.
        pages = DictionaryObject()
        pages.update({
                NameObject("/Type"): NameObject("/Pages"),
                NameObject("/Count"): NumberObject(0),
                NameObject("/Kids"): ArrayObject(),
                })
        self._pages = self._addObject(pages)

        # info object
        info = DictionaryObject()
        info.update({
                NameObject("/Producer"): createStringObject(u"Python PDF Library - http://pybrary.net/pyPdf/")
                })
        self._info = self._addObject(info)

        # root object
        root = DictionaryObject()
        root.update({
            NameObject("/Type"): NameObject("/Catalog"),
            NameObject("/Pages"): self._pages,
            })
        self._root = self._addObject(root)

    def _addObject(self, obj):
        self._objects.append(obj)
        return IndirectObject(len(self._objects), 0, self)

    def getObject(self, ido):
        if ido.pdf != self:
            raise ValueError("pdf must be self")
        return self._objects[ido.idnum - 1]

    ##
    # Common method for inserting or adding a page to this PDF file.
    #
    # @param page The page to add to the document.  This argument should be
    #             an instance of {@link #PageObject PageObject}.
    # @param action The function which will insert the page in the dictionnary.
    #               Takes: page list, page to add.
    def _addPage(self, page, action):
        assert page["/Type"] == "/Page"
        page[NameObject("/Parent")] = self._pages
        page = self._addObject(page)
        pages = self.getObject(self._pages)
        action(pages["/Kids"], page)
        pages[NameObject("/Count")] = NumberObject(pages["/Count"] + 1)

    ##
    # Adds a page to this PDF file.  The page is usually acquired from a
    # {@link #PdfFileReader PdfFileReader} instance.
    # <p>
    # Stability: Added in v1.0, will exist for all v1.x releases.
    #
    # @param page The page to add to the document.  This argument should be
    #             an instance of {@link #PageObject PageObject}.
    def addPage(self, page):
        self._addPage(page, list.append)

    ##
    # Insert a page in this PDF file.  The page is usually acquired from a
    # {@link #PdfFileReader PdfFileReader} instance.
    #
    # @param page The page to add to the document.  This argument should be
    #             an instance of {@link #PageObject PageObject}.
    # @param index Position at which the page will be inserted.
    def insertPage(self, page, index=0):
        self._addPage(page, lambda l, p: l.insert(index, p))

    ##
    # Retrieves a page by number from this PDF file.
    # @return Returns a {@link #PageObject PageObject} instance.
    def getPage(self, pageNumber):
        pages = self.getObject(self._pages)
        # XXX: crude hack
        return pages["/Kids"][pageNumber].getObject()

    ##
    # Return the number of pages.
    # @return The number of pages.
    def getNumPages(self):
        pages = self.getObject(self._pages)
        return int(pages[NameObject("/Count")])

    ##
    # Append a blank page to this PDF file and returns it. If no page size
    # is specified, use the size of the last page; throw
    # PageSizeNotDefinedError if it doesn't exist.
    # @param width The width of the new page expressed in default user
    # space units.
    # @param height The height of the new page expressed in default user
    # space units.
    def addBlankPage(self, width=None, height=None):
        page = PageObject.createBlankPage(self, width, height)
        self.addPage(page)
        return page

    ##
    # Insert a blank page to this PDF file and returns it. If no page size
    # is specified, use the size of the page in the given index; throw
    # PageSizeNotDefinedError if it doesn't exist.
    # @param width  The width of the new page expressed in default user
    #               space units.
    # @param height The height of the new page expressed in default user
    #               space units.
    # @param index  Position to add the page.
    def insertBlankPage(self, width=None, height=None, index=0):
        if width is None or height is None and \
                (self.getNumPages() - 1) >= index:
            oldpage = self.getPage(index)
            width = oldpage.mediaBox.getWidth()
            height = oldpage.mediaBox.getHeight()
        page = PageObject.createBlankPage(self, width, height)
        self.insertPage(page, index)
        return page

    ##
    # Encrypt this PDF file with the PDF Standard encryption handler.
    # @param user_pwd The "user password", which allows for opening and reading
    # the PDF file with the restrictions provided.
    # @param owner_pwd The "owner password", which allows for opening the PDF
    # files without any restrictions.  By default, the owner password is the
    # same as the user password.
    # @param use_128bit Boolean argument as to whether to use 128bit
    # encryption.  When false, 40bit encryption will be used.  By default, this
    # flag is on.
    def encrypt(self, user_pwd, owner_pwd = None, use_128bit = True):
        import time, random
        if owner_pwd == None:
            owner_pwd = user_pwd
        if use_128bit:
            V = 2
            rev = 3
            keylen = 128 / 8
        else:
            V = 1
            rev = 2
            keylen = 40 / 8
        # permit everything:
        P = -1
        O = ByteStringObject(_alg33(owner_pwd, user_pwd, rev, keylen))
        ID_1 = md5(repr(time.time())).digest()
        ID_2 = md5(repr(random.random())).digest()
        self._ID = ArrayObject((ByteStringObject(ID_1), ByteStringObject(ID_2)))
        if rev == 2:
            U, key = _alg34(user_pwd, O, P, ID_1)
        else:
            assert rev == 3
            U, key = _alg35(user_pwd, rev, keylen, O, P, ID_1, False)
        encrypt = DictionaryObject()
        encrypt[NameObject("/Filter")] = NameObject("/Standard")
        encrypt[NameObject("/V")] = NumberObject(V)
        if V == 2:
            encrypt[NameObject("/Length")] = NumberObject(keylen * 8)
        encrypt[NameObject("/R")] = NumberObject(rev)
        encrypt[NameObject("/O")] = ByteStringObject(O)
        encrypt[NameObject("/U")] = ByteStringObject(U)
        encrypt[NameObject("/P")] = NumberObject(P)
        self._encrypt = self._addObject(encrypt)
        self._encrypt_key = key

    ##
    # Writes the collection of pages added to this object out as a PDF file.
    # <p>
    # Stability: Added in v1.0, will exist for all v1.x releases.
    # @param stream An object to write the file to.  The object must support
    # the write method, and the tell method, similar to a file object.
    def write(self, stream):
        import struct

        externalReferenceMap = {}

        # PDF objects sometimes have circular references to their /Page objects
        # inside their object tree (for example, annotations).  Those will be
        # indirect references to objects that we've recreated in this PDF.  To
        # address this problem, PageObject's store their original object
        # reference number, and we add it to the external reference map before
        # we sweep for indirect references.  This forces self-page-referencing
        # trees to reference the correct new object location, rather than
        # copying in a new copy of the page object.
        for objIndex in xrange(len(self._objects)):
            obj = self._objects[objIndex]
            if isinstance(obj, PageObject) and obj.indirectRef != None:
                data = obj.indirectRef
                if not externalReferenceMap.has_key(data.pdf):
                    externalReferenceMap[data.pdf] = {}
                if not externalReferenceMap[data.pdf].has_key(data.generation):
                    externalReferenceMap[data.pdf][data.generation] = {}
                externalReferenceMap[data.pdf][data.generation][data.idnum] = IndirectObject(objIndex + 1, 0, self)

        self.stack = []
        self._sweepIndirectReferences(externalReferenceMap, self._root)
        del self.stack

        # Begin writing:
        object_positions = []
        stream.write(self._header + "\n")
        for i in range(len(self._objects)):
            idnum = (i + 1)
            obj = self._objects[i]
            object_positions.append(stream.tell())
            stream.write(str(idnum) + " 0 obj\n")
            key = None
            if hasattr(self, "_encrypt") and idnum != self._encrypt.idnum:
                pack1 = struct.pack("<i", i + 1)[:3]
                pack2 = struct.pack("<i", 0)[:2]
                key = self._encrypt_key + pack1 + pack2
                assert len(key) == (len(self._encrypt_key) + 5)
                md5_hash = md5(key).digest()
                key = md5_hash[:min(16, len(self._encrypt_key) + 5)]
            obj.writeToStream(stream, key)
            stream.write("\nendobj\n")

        # xref table
        xref_location = stream.tell()
        stream.write("xref\n")
        stream.write("0 %s\n" % (len(self._objects) + 1))
        stream.write("%010d %05d f \n" % (0, 65535))
        for offset in object_positions:
            stream.write("%010d %05d n \n" % (offset, 0))

        # trailer
        stream.write("trailer\n")
        trailer = DictionaryObject()
        trailer.update({
                NameObject("/Size"): NumberObject(len(self._objects) + 1),
                NameObject("/Root"): self._root,
                NameObject("/Info"): self._info,
                })
        if hasattr(self, "_ID"):
            trailer[NameObject("/ID")] = self._ID
        if hasattr(self, "_encrypt"):
            trailer[NameObject("/Encrypt")] = self._encrypt
        trailer.writeToStream(stream, None)
        
        # eof
        stream.write("\nstartxref\n%s\n%%%%EOF\n" % (xref_location))

    def _sweepIndirectReferences(self, externMap, data):
        if isinstance(data, DictionaryObject):
            for key, value in data.items():
                origvalue = value
                value = self._sweepIndirectReferences(externMap, value)
                if isinstance(value, StreamObject):
                    # a dictionary value is a stream.  streams must be indirect
                    # objects, so we need to change this value.
                    value = self._addObject(value)
                data[key] = value
            return data
        elif isinstance(data, ArrayObject):
            for i in range(len(data)):
                value = self._sweepIndirectReferences(externMap, data[i])
                if isinstance(value, StreamObject):
                    # an array value is a stream.  streams must be indirect
                    # objects, so we need to change this value
                    value = self._addObject(value)
                data[i] = value
            return data
        elif isinstance(data, IndirectObject):
            # internal indirect references are fine
            if data.pdf == self:
                if data.idnum in self.stack:
                    return data
                else:
                    self.stack.append(data.idnum)
                    realdata = self.getObject(data)
                    self._sweepIndirectReferences(externMap, realdata)
                    self.stack.pop()
                    return data
            else:
                newobj = externMap.get(data.pdf, {}).get(data.generation, {}).get(data.idnum, None)
                if newobj == None:
                    newobj = data.pdf.getObject(data)
                    self._objects.append(None) # placeholder
                    idnum = len(self._objects)
                    newobj_ido = IndirectObject(idnum, 0, self)
                    if not externMap.has_key(data.pdf):
                        externMap[data.pdf] = {}
                    if not externMap[data.pdf].has_key(data.generation):
                        externMap[data.pdf][data.generation] = {}
                    externMap[data.pdf][data.generation][data.idnum] = newobj_ido
                    newobj = self._sweepIndirectReferences(externMap, newobj)
                    self._objects[idnum-1] = newobj
                    return newobj_ido
                return newobj
        else:
            return data


##
# Initializes a PdfFileReader object.  This operation can take some time, as
# the PDF stream's cross-reference tables are read into memory.
# <p>
# Stability: Added in v1.0, will exist for all v1.x releases.
#
# @param stream An object that supports the standard read and seek methods
#               similar to a file object.
class PdfFileReader(object):
    def __init__(self, stream):
        self.flattenedPages = None
        self.resolvedObjects = {}
        self.read(stream)
        self.stream = stream
        self._override_encryption = False

    ##
    # Retrieves the PDF file's document information dictionary, if it exists.
    # Note that some PDF files use metadata streams instead of docinfo
    # dictionaries, and these metadata streams will not be accessed by this
    # function.
    # <p>
    # Stability: Added in v1.6, will exist for all future v1.x releases.
    # @return Returns a {@link #DocumentInformation DocumentInformation}
    #         instance, or None if none exists.
    def getDocumentInfo(self):
        if not self.trailer.has_key("/Info"):
            return None
        obj = self.trailer['/Info']
        retval = DocumentInformation()
        retval.update(obj)
        return retval

    ##
    # Read-only property that accesses the {@link
    # #PdfFileReader.getDocumentInfo getDocumentInfo} function.
    # <p>
    # Stability: Added in v1.7, will exist for all future v1.x releases.
    documentInfo = property(lambda self: self.getDocumentInfo(), None, None)

    ##
    # Retrieves XMP (Extensible Metadata Platform) data from the PDF document
    # root.
    # <p>
    # Stability: Added in v1.12, will exist for all future v1.x releases.
    # @return Returns a {@link #generic.XmpInformation XmlInformation}
    # instance that can be used to access XMP metadata from the document.
    # Can also return None if no metadata was found on the document root.
    def getXmpMetadata(self):
        try:
            self._override_encryption = True
            return self.trailer["/Root"].getXmpMetadata()
        finally:
            self._override_encryption = False

    ##
    # Read-only property that accesses the {@link #PdfFileReader.getXmpData
    # getXmpData} function.
    # <p>
    # Stability: Added in v1.12, will exist for all future v1.x releases.
    xmpMetadata = property(lambda self: self.getXmpMetadata(), None, None)

    ##
    # Calculates the number of pages in this PDF file.
    # <p>
    # Stability: Added in v1.0, will exist for all v1.x releases.
    # @return Returns an integer.
    def getNumPages(self):
        if self.flattenedPages == None:
            self._flatten()
        return len(self.flattenedPages)

    ##
    # Read-only property that accesses the {@link #PdfFileReader.getNumPages
    # getNumPages} function.
    # <p>
    # Stability: Added in v1.7, will exist for all future v1.x releases.
    numPages = property(lambda self: self.getNumPages(), None, None)

    ##
    # Retrieves a page by number from this PDF file.
    # <p>
    # Stability: Added in v1.0, will exist for all v1.x releases.
    # @return Returns a {@link #PageObject PageObject} instance.
    def getPage(self, pageNumber):
        ## ensure that we're not trying to access an encrypted PDF
        #assert not self.trailer.has_key("/Encrypt")
        if self.flattenedPages == None:
            self._flatten()
        return self.flattenedPages[pageNumber]

    ##
    # Read-only property that accesses the 
    # {@link #PdfFileReader.getNamedDestinations 
    # getNamedDestinations} function.
    # <p>
    # Stability: Added in v1.10, will exist for all future v1.x releases.
    namedDestinations = property(lambda self:
                                  self.getNamedDestinations(), None, None)

    ##
    # Retrieves the named destinations present in the document.
    # <p>
    # Stability: Added in v1.10, will exist for all future v1.x releases.
    # @return Returns a dict which maps names to {@link #Destination
    # destinations}.
    def getNamedDestinations(self, tree=None, retval=None):
        if retval == None:
            retval = {}
            catalog = self.trailer["/Root"]
            
            # get the name tree
            if catalog.has_key("/Dests"):
                tree = catalog["/Dests"]
            elif catalog.has_key("/Names"):
                names = catalog['/Names']
                if names.has_key("/Dests"):
                    tree = names['/Dests']
        
        if tree == None:
            return retval

        if tree.has_key("/Kids"):
            # recurse down the tree
            for kid in tree["/Kids"]:
                self.getNamedDestinations(kid.getObject(), retval)

        if tree.has_key("/Names"):
            names = tree["/Names"]
            for i in range(0, len(names), 2):
                key = names[i].getObject()
                val = names[i+1].getObject()
                if isinstance(val, DictionaryObject) and val.has_key('/D'):
                    val = val['/D']
                dest = self._buildDestination(key, val)
                if dest != None:
                    retval[key] = dest

        return retval

    ##
    # Read-only property that accesses the {@link #PdfFileReader.getOutlines
    # getOutlines} function.
    # <p>
    # Stability: Added in v1.10, will exist for all future v1.x releases.
    outlines = property(lambda self: self.getOutlines(), None, None)

    ##
    # Retrieves the document outline present in the document.
    # <p>
    # Stability: Added in v1.10, will exist for all future v1.x releases.
    # @return Returns a nested list of {@link #Destination destinations}.
    def getOutlines(self, node=None, outlines=None):
        if outlines == None:
            outlines = []
            catalog = self.trailer["/Root"]
            
            # get the outline dictionary and named destinations
            if catalog.has_key("/Outlines"):
                lines = catalog["/Outlines"]
                if lines.has_key("/First"):
                    node = lines["/First"]
            self._namedDests = self.getNamedDestinations()
            
        if node == None:
          return outlines
          
        # see if there are any more outlines
        while 1:
            outline = self._buildOutline(node)
            if outline:
                outlines.append(outline)

            # check for sub-outlines
            if node.has_key("/First"):
                subOutlines = []
                self.getOutlines(node["/First"], subOutlines)
                if subOutlines:
                    outlines.append(subOutlines)

            if not node.has_key("/Next"):
                break
            node = node["/Next"]

        return outlines

    def _buildDestination(self, title, array):
        page, typ = array[0:2]
        array = array[2:]
        return Destination(title, page, typ, *array)
          
    def _buildOutline(self, node):
        dest, title, outline = None, None, None
        
        if node.has_key("/A") and node.has_key("/Title"):
            # Action, section 8.5 (only type GoTo supported)
            title  = node["/Title"]
            action = node["/A"]
            if action["/S"] == "/GoTo":
                dest = action["/D"]
        elif node.has_key("/Dest") and node.has_key("/Title"):
            # Destination, section 8.2.1
            title = node["/Title"]
            dest  = node["/Dest"]

        # if destination found, then create outline
        if dest:
            if isinstance(dest, ArrayObject):
                outline = self._buildDestination(title, dest)
            elif isinstance(dest, unicode) and self._namedDests.has_key(dest):
                outline = self._namedDests[dest]
                outline[NameObject("/Title")] = title
            else:
                raise utils.PdfReadError("Unexpected destination %r" % dest)
        return outline

    ##
    # Read-only property that emulates a list based upon the {@link
    # #PdfFileReader.getNumPages getNumPages} and {@link #PdfFileReader.getPage
    # getPage} functions.
    # <p>
    # Stability: Added in v1.7, and will exist for all future v1.x releases.
    pages = property(lambda self: ConvertFunctionsToVirtualList(self.getNumPages, self.getPage),
            None, None)

    def _flatten(self, pages=None, inherit=None, indirectRef=None):
        inheritablePageAttributes = (
            NameObject("/Resources"), NameObject("/MediaBox"),
            NameObject("/CropBox"), NameObject("/Rotate")
            )
        if inherit == None:
            inherit = dict()
        if pages == None:
            self.flattenedPages = []
            catalog = self.trailer["/Root"].getObject()
            pages = catalog["/Pages"].getObject()
        t = pages["/Type"]
        if t == "/Pages":
            for attr in inheritablePageAttributes:
                if pages.has_key(attr):
                    inherit[attr] = pages[attr]
            for page in pages["/Kids"]:
                addt = {}
                if isinstance(page, IndirectObject):
                    addt["indirectRef"] = page
                self._flatten(page.getObject(), inherit, **addt)
        elif t == "/Page":
            for attr,value in inherit.items():
                # if the page has it's own value, it does not inherit the
                # parent's value:
                if not pages.has_key(attr):
                    pages[attr] = value
            pageObj = PageObject(self, indirectRef)
            pageObj.update(pages)
            self.flattenedPages.append(pageObj)

    def getObject(self, indirectReference):
        retval = self.resolvedObjects.get(indirectReference.generation, {}).get(indirectReference.idnum, None)
        if retval != None:
            return retval
        if indirectReference.generation == 0 and \
           self.xref_objStm.has_key(indirectReference.idnum):
            # indirect reference to object in object stream
            # read the entire object stream into memory
            stmnum,idx = self.xref_objStm[indirectReference.idnum]
            objStm = IndirectObject(stmnum, 0, self).getObject()
            assert objStm['/Type'] == '/ObjStm'
            assert idx < objStm['/N']
            streamData = StringIO(objStm.getData())
            for i in range(objStm['/N']):
                objnum = NumberObject.readFromStream(streamData)
                readNonWhitespace(streamData)
                streamData.seek(-1, 1)
                offset = NumberObject.readFromStream(streamData)
                readNonWhitespace(streamData)
                streamData.seek(-1, 1)
                t = streamData.tell()
                streamData.seek(objStm['/First']+offset, 0)
                obj = readObject(streamData, self)
                self.resolvedObjects[0][objnum] = obj
                streamData.seek(t, 0)
            return self.resolvedObjects[0][indirectReference.idnum]
        start = self.xref[indirectReference.generation][indirectReference.idnum]
        self.stream.seek(start, 0)
        idnum, generation = self.readObjectHeader(self.stream)
        assert idnum == indirectReference.idnum
        assert generation == indirectReference.generation
        retval = readObject(self.stream, self)

        # override encryption is used for the /Encrypt dictionary
        if not self._override_encryption and self.isEncrypted:
            # if we don't have the encryption key:
            if not hasattr(self, '_decryption_key'):
                raise Exception, "file has not been decrypted"
            # otherwise, decrypt here...
            import struct
            pack1 = struct.pack("<i", indirectReference.idnum)[:3]
            pack2 = struct.pack("<i", indirectReference.generation)[:2]
            key = self._decryption_key + pack1 + pack2
            assert len(key) == (len(self._decryption_key) + 5)
            md5_hash = md5(key).digest()
            key = md5_hash[:min(16, len(self._decryption_key) + 5)]
            retval = self._decryptObject(retval, key)

        self.cacheIndirectObject(generation, idnum, retval)
        return retval

    def _decryptObject(self, obj, key):
        if isinstance(obj, ByteStringObject) or isinstance(obj, TextStringObject):
            obj = createStringObject(utils.RC4_encrypt(key, obj.original_bytes))
        elif isinstance(obj, StreamObject):
            obj._data = utils.RC4_encrypt(key, obj._data)
        elif isinstance(obj, DictionaryObject):
            for dictkey, value in obj.items():
                obj[dictkey] = self._decryptObject(value, key)
        elif isinstance(obj, ArrayObject):
            for i in range(len(obj)):
                obj[i] = self._decryptObject(obj[i], key)
        return obj

    def readObjectHeader(self, stream):
        # Should never be necessary to read out whitespace, since the
        # cross-reference table should put us in the right spot to read the
        # object header.  In reality... some files have stupid cross reference
        # tables that are off by whitespace bytes.
        readNonWhitespace(stream); stream.seek(-1, 1)
        idnum = readUntilWhitespace(stream)
        generation = readUntilWhitespace(stream)
        obj = stream.read(3)
        readNonWhitespace(stream)
        stream.seek(-1, 1)
        return int(idnum), int(generation)

    def cacheIndirectObject(self, generation, idnum, obj):
        if not self.resolvedObjects.has_key(generation):
            self.resolvedObjects[generation] = {}
        self.resolvedObjects[generation][idnum] = obj

    def read(self, stream):
        # start at the end:
        stream.seek(-1, 2)
        line = ''
        while not line:
            line = self.readNextEndLine(stream)
        if line[:5] != "%%EOF":
            raise utils.PdfReadError, "EOF marker not found"

        # find startxref entry - the location of the xref table
        line = self.readNextEndLine(stream)
        startxref = int(line)
        line = self.readNextEndLine(stream)
        if line[:9] != "startxref":
            raise utils.PdfReadError, "startxref not found"

        # read all cross reference tables and their trailers
        self.xref = {}
        self.xref_objStm = {}
        self.trailer = DictionaryObject()
        while 1:
            # load the xref table
            stream.seek(startxref, 0)
            x = stream.read(1)
            if x == "x":
                # standard cross-reference table
                ref = stream.read(4)
                if ref[:3] != "ref":
                    raise utils.PdfReadError, "xref table read error"
                readNonWhitespace(stream)
                stream.seek(-1, 1)
                while 1:
                    num = readObject(stream, self)
                    readNonWhitespace(stream)
                    stream.seek(-1, 1)
                    size = readObject(stream, self)
                    readNonWhitespace(stream)
                    stream.seek(-1, 1)
                    cnt = 0
                    while cnt < size:
                        line = stream.read(20)
                        # It's very clear in section 3.4.3 of the PDF spec
                        # that all cross-reference table lines are a fixed
                        # 20 bytes.  However... some malformed PDF files
                        # use a single character EOL without a preceeding
                        # space.  Detect that case, and seek the stream
                        # back one character.  (0-9 means we've bled into
                        # the next xref entry, t means we've bled into the
                        # text "trailer"):
                        if line[-1] in "0123456789t":
                            stream.seek(-1, 1)
                        offset, generation = line[:16].split(" ")
                        offset, generation = int(offset), int(generation)
                        if not self.xref.has_key(generation):
                            self.xref[generation] = {}
                        if self.xref[generation].has_key(num):
                            # It really seems like we should allow the last
                            # xref table in the file to override previous
                            # ones. Since we read the file backwards, assume
                            # any existing key is already set correctly.
                            pass
                        else:
                            self.xref[generation][num] = offset
                        cnt += 1
                        num += 1
                    readNonWhitespace(stream)
                    stream.seek(-1, 1)
                    trailertag = stream.read(7)
                    if trailertag != "trailer":
                        # more xrefs!
                        stream.seek(-7, 1)
                    else:
                        break
                readNonWhitespace(stream)
                stream.seek(-1, 1)
                newTrailer = readObject(stream, self)
                for key, value in newTrailer.items():
                    if not self.trailer.has_key(key):
                        self.trailer[key] = value
                if newTrailer.has_key("/Prev"):
                    startxref = newTrailer["/Prev"]
                else:
                    break
            elif x.isdigit():
                # PDF 1.5+ Cross-Reference Stream
                stream.seek(-1, 1)
                idnum, generation = self.readObjectHeader(stream)
                xrefstream = readObject(stream, self)
                assert xrefstream["/Type"] == "/XRef"
                self.cacheIndirectObject(generation, idnum, xrefstream)
                streamData = StringIO(xrefstream.getData())
                idx_pairs = xrefstream.get("/Index", [0, xrefstream.get("/Size")])
                entrySizes = xrefstream.get("/W")
                for num, size in self._pairs(idx_pairs):
                    cnt = 0
                    while cnt < size:
                        for i in range(len(entrySizes)):
                            d = streamData.read(entrySizes[i])
                            di = convertToInt(d, entrySizes[i])
                            if i == 0:
                                xref_type = di
                            elif i == 1:
                                if xref_type == 0:
                                    next_free_object = di
                                elif xref_type == 1:
                                    byte_offset = di
                                elif xref_type == 2:
                                    objstr_num = di
                            elif i == 2:
                                if xref_type == 0:
                                    next_generation = di
                                elif xref_type == 1:
                                    generation = di
                                elif xref_type == 2:
                                    obstr_idx = di
                        if xref_type == 0:
                            pass
                        elif xref_type == 1:
                            if not self.xref.has_key(generation):
                                self.xref[generation] = {}
                            if not num in self.xref[generation]:
                                self.xref[generation][num] = byte_offset
                        elif xref_type == 2:
                            if not num in self.xref_objStm:
                                self.xref_objStm[num] = [objstr_num, obstr_idx]
                        cnt += 1
                        num += 1
                trailerKeys = "/Root", "/Encrypt", "/Info", "/ID"
                for key in trailerKeys:
                    if xrefstream.has_key(key) and not self.trailer.has_key(key):
                        self.trailer[NameObject(key)] = xrefstream.raw_get(key)
                if xrefstream.has_key("/Prev"):
                    startxref = xrefstream["/Prev"]
                else:
                    break
            else:
                # bad xref character at startxref.  Let's see if we can find
                # the xref table nearby, as we've observed this error with an
                # off-by-one before.
                stream.seek(-11, 1)
                tmp = stream.read(20)
                xref_loc = tmp.find("xref")
                if xref_loc != -1:
                    startxref -= (10 - xref_loc)
                    continue
                else:
                    # no xref table found at specified location
                    assert False
                    break

    def _pairs(self, array):
        i = 0
        while True:
            yield array[i], array[i+1]
            i += 2
            if (i+1) >= len(array):
                break

    def readNextEndLine(self, stream):
        line = ""
        while True:
            x = stream.read(1)
            stream.seek(-2, 1)
            if x == '\n' or x == '\r':
                while x == '\n' or x == '\r':
                    x = stream.read(1)
                    stream.seek(-2, 1)
                stream.seek(1, 1)
                break
            else:
                line = x + line
        return line

    ##
    # When using an encrypted / secured PDF file with the PDF Standard
    # encryption handler, this function will allow the file to be decrypted.
    # It checks the given password against the document's user password and
    # owner password, and then stores the resulting decryption key if either
    # password is correct.
    # <p>
    # It does not matter which password was matched.  Both passwords provide
    # the correct decryption key that will allow the document to be used with
    # this library.
    # <p>
    # Stability: Added in v1.8, will exist for all future v1.x releases.
    #
    # @return 0 if the password failed, 1 if the password matched the user
    # password, and 2 if the password matched the owner password.
    #
    # @exception NotImplementedError Document uses an unsupported encryption
    # method.
    def decrypt(self, password):
        self._override_encryption = True
        try:
            return self._decrypt(password)
        finally:
            self._override_encryption = False

    def _decrypt(self, password):
        encrypt = self.trailer['/Encrypt'].getObject()
        if encrypt['/Filter'] != '/Standard':
            raise NotImplementedError, "only Standard PDF encryption handler is available"
        if not (encrypt['/V'] in (1, 2)):
            raise NotImplementedError, "only algorithm code 1 and 2 are supported"
        user_password, key = self._authenticateUserPassword(password)
        if user_password:
            self._decryption_key = key
            return 1
        else:
            rev = encrypt['/R'].getObject()
            if rev == 2:
                keylen = 5
            else:
                keylen = encrypt['/Length'].getObject() / 8
            key = _alg33_1(password, rev, keylen)
            real_O = encrypt["/O"].getObject()
            if rev == 2:
                userpass = utils.RC4_encrypt(key, real_O)
            else:
                val = real_O
                for i in range(19, -1, -1):
                    new_key = ''
                    for l in range(len(key)):
                        new_key += chr(ord(key[l]) ^ i)
                    val = utils.RC4_encrypt(new_key, val)
                userpass = val
            owner_password, key = self._authenticateUserPassword(userpass)
            if owner_password:
                self._decryption_key = key
                return 2
        return 0

    def _authenticateUserPassword(self, password):
        encrypt = self.trailer['/Encrypt'].getObject()
        rev = encrypt['/R'].getObject()
        owner_entry = encrypt['/O'].getObject().original_bytes
        p_entry = encrypt['/P'].getObject()
        id_entry = self.trailer['/ID'].getObject()
        id1_entry = id_entry[0].getObject()
        if rev == 2:
            U, key = _alg34(password, owner_entry, p_entry, id1_entry)
        elif rev >= 3:
            U, key = _alg35(password, rev,
                    encrypt["/Length"].getObject() / 8, owner_entry,
                    p_entry, id1_entry,
                    encrypt.get("/EncryptMetadata", BooleanObject(False)).getObject())
        real_U = encrypt['/U'].getObject().original_bytes
        return U == real_U, key

    def getIsEncrypted(self):
        return self.trailer.has_key("/Encrypt")

    ##
    # Read-only boolean property showing whether this PDF file is encrypted.
    # Note that this property, if true, will remain true even after the {@link
    # #PdfFileReader.decrypt decrypt} function is called.
    isEncrypted = property(lambda self: self.getIsEncrypted(), None, None)


def getRectangle(self, name, defaults):
    retval = self.get(name)
    if isinstance(retval, RectangleObject):
        return retval
    if retval == None:
        for d in defaults:
            retval = self.get(d)
            if retval != None:
                break
    if isinstance(retval, IndirectObject):
        retval = self.pdf.getObject(retval)
    retval = RectangleObject(retval)
    setRectangle(self, name, retval)
    return retval

def setRectangle(self, name, value):
    if not isinstance(name, NameObject):
        name = NameObject(name)
    self[name] = value

def deleteRectangle(self, name):
    del self[name]

def createRectangleAccessor(name, fallback):
    return \
        property(
            lambda self: getRectangle(self, name, fallback),
            lambda self, value: setRectangle(self, name, value),
            lambda self: deleteRectangle(self, name)
            )

##
# This class represents a single page within a PDF file.  Typically this object
# will be created by accessing the {@link #PdfFileReader.getPage getPage}
# function of the {@link #PdfFileReader PdfFileReader} class, but it is
# also possible to create an empty page with the createBlankPage static
# method.
# @param pdf PDF file the page belongs to (optional, defaults to None).
class PageObject(DictionaryObject):
    def __init__(self, pdf=None, indirectRef=None):
        DictionaryObject.__init__(self)
        self.pdf = pdf
        # Stores the original indirect reference to this object in its source PDF
        self.indirectRef = indirectRef

    ##
    # Returns a new blank page.
    # If width or height is None, try to get the page size from the
    # last page of pdf. If pdf is None or contains no page, a
    # PageSizeNotDefinedError is raised.
    # @param pdf    PDF file the page belongs to
    # @param width  The width of the new page expressed in default user
    #               space units.
    # @param height The height of the new page expressed in default user
    #               space units.
    def createBlankPage(pdf=None, width=None, height=None):
        page = PageObject(pdf)

        # Creates a new page (cf PDF Reference  7.7.3.3)
        page.__setitem__(NameObject('/Type'), NameObject('/Page'))
        page.__setitem__(NameObject('/Parent'), NullObject())
        page.__setitem__(NameObject('/Resources'), DictionaryObject())
        if width is None or height is None:
            if pdf is not None and pdf.getNumPages() > 0:
                lastpage = pdf.getPage(pdf.getNumPages() - 1)
                width = lastpage.mediaBox.getWidth()
                height = lastpage.mediaBox.getHeight()
            else:
                raise utils.PageSizeNotDefinedError()
        page.__setitem__(NameObject('/MediaBox'),
            RectangleObject([0, 0, width, height]))

        return page
    createBlankPage = staticmethod(createBlankPage)

    ##
    # Rotates a page clockwise by increments of 90 degrees.
    # <p>
    # Stability: Added in v1.1, will exist for all future v1.x releases.
    # @param angle Angle to rotate the page.  Must be an increment of 90 deg.
    def rotateClockwise(self, angle):
        assert angle % 90 == 0
        self._rotate(angle)
        return self

    ##
    # Rotates a page counter-clockwise by increments of 90 degrees.
    # <p>
    # Stability: Added in v1.1, will exist for all future v1.x releases.
    # @param angle Angle to rotate the page.  Must be an increment of 90 deg.
    def rotateCounterClockwise(self, angle):
        assert angle % 90 == 0
        self._rotate(-angle)
        return self

    def _rotate(self, angle):
        currentAngle = self.get("/Rotate", 0)
        self[NameObject("/Rotate")] = NumberObject(currentAngle + angle)

    def _mergeResources(res1, res2, resource):
        newRes = DictionaryObject()
        newRes.update(res1.get(resource, DictionaryObject()).getObject())
        page2Res = res2.get(resource, DictionaryObject()).getObject()
        renameRes = {}
        for key in page2Res.keys():
            if newRes.has_key(key) and newRes[key] != page2Res[key]:
                newname = NameObject(key + "renamed")
                renameRes[key] = newname
                newRes[newname] = page2Res[key]
            elif not newRes.has_key(key):
                newRes[key] = page2Res.raw_get(key)
        return newRes, renameRes
    _mergeResources = staticmethod(_mergeResources)

    def _contentStreamRename(stream, rename, pdf):
        if not rename:
            return stream
        stream = ContentStream(stream, pdf)
        for operands,operator in stream.operations:
            for i in range(len(operands)):
                op = operands[i]
                if isinstance(op, NameObject):
                    operands[i] = rename.get(op, op)
        return stream
    _contentStreamRename = staticmethod(_contentStreamRename)

    def _pushPopGS(contents, pdf):
        # adds a graphics state "push" and "pop" to the beginning and end
        # of a content stream.  This isolates it from changes such as 
        # transformation matricies.
        stream = ContentStream(contents, pdf)
        stream.operations.insert(0, [[], "q"])
        stream.operations.append([[], "Q"])
        return stream
    _pushPopGS = staticmethod(_pushPopGS)

    def _addTransformationMatrix(contents, pdf, ctm):
        # adds transformation matrix at the beginning of the given
        # contents stream.
        a, b, c, d, e, f = ctm
        contents = ContentStream(contents, pdf)
        contents.operations.insert(0, [[FloatObject(a), FloatObject(b),
            FloatObject(c), FloatObject(d), FloatObject(e),
            FloatObject(f)], " cm"])
        return contents
    _addTransformationMatrix = staticmethod(_addTransformationMatrix)

    ##
    # Returns the /Contents object, or None if it doesn't exist.
    # /Contents is optionnal, as described in PDF Reference  7.7.3.3
    def getContents(self):
      if self.has_key("/Contents"):
        return self["/Contents"].getObject()
      else:
        return None

    ##
    # Merges the content streams of two pages into one.  Resource references
    # (i.e. fonts) are maintained from both pages.  The mediabox/cropbox/etc
    # of this page are not altered.  The parameter page's content stream will
    # be added to the end of this page's content stream, meaning that it will
    # be drawn after, or "on top" of this page.
    # <p>
    # Stability: Added in v1.4, will exist for all future 1.x releases.
    # @param page2 An instance of {@link #PageObject PageObject} to be merged
    #              into this one.
    def mergePage(self, page2):
        self._mergePage(page2)

    ##
    # Actually merges the content streams of two pages into one. Resource
    # references (i.e. fonts) are maintained from both pages. The
    # mediabox/cropbox/etc of this page are not altered. The parameter page's
    # content stream will be added to the end of this page's content stream,
    # meaning that it will be drawn after, or "on top" of this page.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged
    #              into this one.
    # @param page2transformation A fuction which applies a transformation to
    #                            the content stream of page2. Takes: page2
    #                            contents stream. Must return: new contents
    #                            stream. If omitted, the content stream will
    #                            not be modified.
    def _mergePage(self, page2, page2transformation=None):
        # First we work on merging the resource dictionaries.  This allows us
        # to find out what symbols in the content streams we might need to
        # rename.

        newResources = DictionaryObject()
        rename = {}
        originalResources = self["/Resources"].getObject()
        page2Resources = page2["/Resources"].getObject()

        for res in "/ExtGState", "/Font", "/XObject", "/ColorSpace", "/Pattern", "/Shading", "/Properties":
            new, newrename = PageObject._mergeResources(originalResources, page2Resources, res)
            if new:
                newResources[NameObject(res)] = new
                rename.update(newrename)

        # Combine /ProcSet sets.
        newResources[NameObject("/ProcSet")] = ArrayObject(
            frozenset(originalResources.get("/ProcSet", ArrayObject()).getObject()).union(
                frozenset(page2Resources.get("/ProcSet", ArrayObject()).getObject())
            )
        )

        newContentArray = ArrayObject()

        originalContent = self.getContents()
        if originalContent is not None:
            newContentArray.append(PageObject._pushPopGS(
                  originalContent, self.pdf))

        page2Content = page2.getContents()
        if page2Content is not None:
            if page2transformation is not None:
                page2Content = page2transformation(page2Content)
            page2Content = PageObject._contentStreamRename(
                page2Content, rename, self.pdf)
            page2Content = PageObject._pushPopGS(page2Content, self.pdf)
            newContentArray.append(page2Content)

        self[NameObject('/Contents')] = ContentStream(newContentArray, self.pdf)
        self[NameObject('/Resources')] = newResources

    ##
    # This is similar to mergePage, but a transformation matrix is
    # applied to the merged stream.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged.
    # @param ctm   A 6 elements tuple containing the operands of the
    #              transformation matrix
    def mergeTransformedPage(self, page2, ctm):
        self._mergePage(page2, lambda page2Content:
            PageObject._addTransformationMatrix(page2Content, page2.pdf, ctm))

    ##
    # This is similar to mergePage, but the stream to be merged is scaled
    # by appling a transformation matrix.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged.
    # @param factor The scaling factor
    def mergeScaledPage(self, page2, factor):
        # CTM to scale : [ sx 0 0 sy 0 0 ]
        return self.mergeTransformedPage(page2, [factor, 0,
                                                 0,      factor,
                                                 0,      0])

    ##
    # This is similar to mergePage, but the stream to be merged is rotated
    # by appling a transformation matrix.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged.
    # @param rotation The angle of the rotation, in degrees
    def mergeRotatedPage(self, page2, rotation):
        rotation = math.radians(rotation)
        return self.mergeTransformedPage(page2,
            [math.cos(rotation),  math.sin(rotation),
             -math.sin(rotation), math.cos(rotation),
             0,                   0])

    ##
    # This is similar to mergePage, but the stream to be merged is translated
    # by appling a transformation matrix.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged.
    # @param tx    The translation on X axis
    # @param tx    The translation on Y axis
    def mergeTranslatedPage(self, page2, tx, ty):
        return self.mergeTransformedPage(page2, [1,  0,
                                                 0,  1,
                                                 tx, ty])

    ##
    # This is similar to mergePage, but the stream to be merged is rotated
    # and scaled by appling a transformation matrix.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged.
    # @param rotation The angle of the rotation, in degrees
    # @param factor The scaling factor
    def mergeRotatedScaledPage(self, page2, rotation, scale):
        rotation = math.radians(rotation)
        rotating = [[math.cos(rotation), math.sin(rotation),0],
                    [-math.sin(rotation),math.cos(rotation), 0],
                    [0,                  0,                  1]]
        scaling = [[scale,0,    0],
                   [0,    scale,0],
                   [0,    0,    1]]
        ctm = utils.matrixMultiply(rotating, scaling)

        return self.mergeTransformedPage(page2,
                                         [ctm[0][0], ctm[0][1],
                                          ctm[1][0], ctm[1][1],
                                          ctm[2][0], ctm[2][1]])

    ##
    # This is similar to mergePage, but the stream to be merged is translated
    # and scaled by appling a transformation matrix.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged.
    # @param scale The scaling factor
    # @param tx    The translation on X axis
    # @param tx    The translation on Y axis
    def mergeScaledTranslatedPage(self, page2, scale, tx, ty):
        translation = [[1, 0, 0],
                       [0, 1, 0],
                       [tx,ty,1]]
        scaling = [[scale,0,    0],
                   [0,    scale,0],
                   [0,    0,    1]]
        ctm = utils.matrixMultiply(scaling, translation)

        return self.mergeTransformedPage(page2, [ctm[0][0], ctm[0][1],
                                                 ctm[1][0], ctm[1][1],
                                                 ctm[2][0], ctm[2][1]])

    ##
    # This is similar to mergePage, but the stream to be merged is translated,
    # rotated and scaled by appling a transformation matrix.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged.
    # @param tx    The translation on X axis
    # @param ty    The translation on Y axis
    # @param rotation The angle of the rotation, in degrees
    # @param scale The scaling factor
    def mergeRotatedScaledTranslatedPage(self, page2, rotation, scale, tx, ty):
        translation = [[1, 0, 0],
                       [0, 1, 0],
                       [tx,ty,1]]
        rotation = math.radians(rotation)
        rotating = [[math.cos(rotation), math.sin(rotation),0],
                    [-math.sin(rotation),math.cos(rotation), 0],
                    [0,                  0,                  1]]
        scaling = [[scale,0,    0],
                   [0,    scale,0],
                   [0,    0,    1]]
        ctm = utils.matrixMultiply(rotating, scaling)
        ctm = utils.matrixMultiply(ctm, translation)

        return self.mergeTransformedPage(page2, [ctm[0][0], ctm[0][1],
                                                 ctm[1][0], ctm[1][1],
                                                 ctm[2][0], ctm[2][1]])

    ##
    # Applys a transformation matrix the page.
    #
    # @param ctm   A 6 elements tuple containing the operands of the
    #              transformation matrix
    def addTransformation(self, ctm):
        originalContent = self.getContents()
        if originalContent is not None:
            newContent = PageObject._addTransformationMatrix(
                originalContent, self.pdf, ctm)
            newContent = PageObject._pushPopGS(newContent, self.pdf)
            self[NameObject('/Contents')] = newContent

    ##
    # Scales a page by the given factors by appling a transformation
    # matrix to its content and updating the page size.
    #
    # @param sx The scaling factor on horizontal axis
    # @param sy The scaling factor on vertical axis
    def scale(self, sx, sy):
        self.addTransformation([sx, 0,
                                0,  sy,
                                0,  0])
        self.mediaBox = RectangleObject([
            float(self.mediaBox.getLowerLeft_x()) * sx,
            float(self.mediaBox.getLowerLeft_y()) * sy,
            float(self.mediaBox.getUpperRight_x()) * sx,
            float(self.mediaBox.getUpperRight_y()) * sy])

    ##
    # Scales a page by the given factor by appling a transformation
    # matrix to its content and updating the page size.
    #
    # @param factor The scaling factor
    def scaleBy(self, factor):
        self.scale(factor, factor)

    ##
    # Scales a page to the specified dimentions by appling a
    # transformation matrix to its content and updating the page size.
    #
    # @param width The new width
    # @param height The new heigth
    def scaleTo(self, width, height):
        sx = width / (self.mediaBox.getUpperRight_x() -
                      self.mediaBox.getLowerLeft_x ())
        sy = height / (self.mediaBox.getUpperRight_y() -
                       self.mediaBox.getLowerLeft_x ())
        self.scale(sx, sy)

    ##
    # Compresses the size of this page by joining all content streams and
    # applying a FlateDecode filter.
    # <p>
    # Stability: Added in v1.6, will exist for all future v1.x releases.
    # However, it is possible that this function will perform no action if
    # content stream compression becomes "automatic" for some reason.
    def compressContentStreams(self):
        content = self.getContents()
        if content is not None:
            if not isinstance(content, ContentStream):
                content = ContentStream(content, self.pdf)
            self[NameObject("/Contents")] = content.flateEncode()

    ##
    # Locate all text drawing commands, in the order they are provided in the
    # content stream, and extract the text.  This works well for some PDF
    # files, but poorly for others, depending on the generator used.  This will
    # be refined in the future.  Do not rely on the order of text coming out of
    # this function, as it will change if this function is made more
    # sophisticated.
    # <p>
    # Stability: Added in v1.7, will exist for all future v1.x releases.  May
    # be overhauled to provide more ordered text in the future.
    # @return a unicode string object
    def extractText(self):
        text = u""
        content = self["/Contents"].getObject()
        if not isinstance(content, ContentStream):
            content = ContentStream(content, self.pdf)
        # Note: we check all strings are TextStringObjects.  ByteStringObjects
        # are strings where the byte->string encoding was unknown, so adding
        # them to the text here would be gibberish.
        for operands,operator in content.operations:
            if operator == "Tj":
                _text = operands[0]
                if isinstance(_text, TextStringObject):
                    text += _text
            elif operator == "T*":
                text += "\n"
            elif operator == "'":
                text += "\n"
                _text = operands[0]
                if isinstance(_text, TextStringObject):
                    text += operands[0]
            elif operator == '"':
                _text = operands[2]
                if isinstance(_text, TextStringObject):
                    text += "\n"
                    text += _text
            elif operator == "TJ":
                for i in operands[0]:
                    if isinstance(i, TextStringObject):
                        text += i
        return text

    ##
    # A rectangle (RectangleObject), expressed in default user space units,
    # defining the boundaries of the physical medium on which the page is
    # intended to be displayed or printed.
    # <p>
    # Stability: Added in v1.4, will exist for all future v1.x releases.
    mediaBox = createRectangleAccessor("/MediaBox", ())

    ##
    # A rectangle (RectangleObject), expressed in default user space units,
    # defining the visible region of default user space.  When the page is
    # displayed or printed, its contents are to be clipped (cropped) to this
    # rectangle and then imposed on the output medium in some
    # implementation-defined manner.  Default value: same as MediaBox.
    # <p>
    # Stability: Added in v1.4, will exist for all future v1.x releases.
    cropBox = createRectangleAccessor("/CropBox", ("/MediaBox",))

    ##
    # A rectangle (RectangleObject), expressed in default user space units,
    # defining the region to which the contents of the page should be clipped
    # when output in a production enviroment.
    # <p>
    # Stability: Added in v1.4, will exist for all future v1.x releases.
    bleedBox = createRectangleAccessor("/BleedBox", ("/CropBox", "/MediaBox"))

    ##
    # A rectangle (RectangleObject), expressed in default user space units,
    # defining the intended dimensions of the finished page after trimming.
    # <p>
    # Stability: Added in v1.4, will exist for all future v1.x releases.
    trimBox = createRectangleAccessor("/TrimBox", ("/CropBox", "/MediaBox"))

    ##
    # A rectangle (RectangleObject), expressed in default user space units,
    # defining the extent of the page's meaningful content as intended by the
    # page's creator.
    # <p>
    # Stability: Added in v1.4, will exist for all future v1.x releases.
    artBox = createRectangleAccessor("/ArtBox", ("/CropBox", "/MediaBox"))


class ContentStream(DecodedStreamObject):
    def __init__(self, stream, pdf):
        self.pdf = pdf
        self.operations = []
        # stream may be a StreamObject or an ArrayObject containing
        # multiple StreamObjects to be cat'd together.
        stream = stream.getObject()
        if isinstance(stream, ArrayObject):
            data = ""
            for s in stream:
                data += s.getObject().getData()
            stream = StringIO(data)
        else:
            stream = StringIO(stream.getData())
        self.__parseContentStream(stream)

    def __parseContentStream(self, stream):
        # file("f:\\tmp.txt", "w").write(stream.read())
        stream.seek(0, 0)
        operands = []
        while True:
            peek = readNonWhitespace(stream)
            if peek == '':
                break
            stream.seek(-1, 1)
            if peek.isalpha() or peek == "'" or peek == '"':
                operator = ""
                while True:
                    tok = stream.read(1)
                    if tok.isspace() or tok in NameObject.delimiterCharacters:
                        stream.seek(-1, 1)
                        break
                    elif tok == '':
                        break
                    operator += tok
                if operator == "BI":
                    # begin inline image - a completely different parsing
                    # mechanism is required, of course... thanks buddy...
                    assert operands == []
                    ii = self._readInlineImage(stream)
                    self.operations.append((ii, "INLINE IMAGE"))
                else:
                    self.operations.append((operands, operator))
                    operands = []
            elif peek == '%':
                # If we encounter a comment in the content stream, we have to
                # handle it here.  Typically, readObject will handle
                # encountering a comment -- but readObject assumes that
                # following the comment must be the object we're trying to
                # read.  In this case, it could be an operator instead.
                while peek not in ('\r', '\n'):
                    peek = stream.read(1)
            else:
                operands.append(readObject(stream, None))

    def _readInlineImage(self, stream):
        # begin reading just after the "BI" - begin image
        # first read the dictionary of settings.
        settings = DictionaryObject()
        while True:
            tok = readNonWhitespace(stream)
            stream.seek(-1, 1)
            if tok == "I":
                # "ID" - begin of image data
                break
            key = readObject(stream, self.pdf)
            tok = readNonWhitespace(stream)
            stream.seek(-1, 1)
            value = readObject(stream, self.pdf)
            settings[key] = value
        # left at beginning of ID
        tmp = stream.read(3)
        assert tmp[:2] == "ID"
        data = ""
        while True:
            tok = stream.read(1)
            if tok == "E":
                next = stream.read(1)
                if next == "I":
                    break
                else:
                    stream.seek(-1, 1)
                    data += tok
            else:
                data += tok
        x = readNonWhitespace(stream)
        stream.seek(-1, 1)
        return {"settings": settings, "data": data}

    def _getData(self):
        newdata = StringIO()
        for operands,operator in self.operations:
            if operator == "INLINE IMAGE":
                newdata.write("BI")
                dicttext = StringIO()
                operands["settings"].writeToStream(dicttext, None)
                newdata.write(dicttext.getvalue()[2:-2])
                newdata.write("ID ")
                newdata.write(operands["data"])
                newdata.write("EI")
            else:
                for op in operands:
                    op.writeToStream(newdata, None)
                    newdata.write(" ")
                newdata.write(operator)
            newdata.write("\n")
        return newdata.getvalue()

    def _setData(self, value):
        self.__parseContentStream(StringIO(value))

    _data = property(_getData, _setData)


##
# A class representing the basic document metadata provided in a PDF File.
# <p>
# As of pyPdf v1.10, all text properties of the document metadata have two
# properties, eg. author and author_raw.  The non-raw property will always
# return a TextStringObject, making it ideal for a case where the metadata is
# being displayed.  The raw property can sometimes return a ByteStringObject,
# if pyPdf was unable to decode the string's text encoding; this requires
# additional safety in the caller and therefore is not as commonly accessed.
class DocumentInformation(DictionaryObject):
    def __init__(self):
        DictionaryObject.__init__(self)

    def getText(self, key):
        retval = self.get(key, None)
        if isinstance(retval, TextStringObject):
            return retval
        return None

    ##
    # Read-only property accessing the document's title.  Added in v1.6, will
    # exist for all future v1.x releases.  Modified in v1.10 to always return a
    # unicode string (TextStringObject).
    # @return A unicode string, or None if the title is not provided.
    title = property(lambda self: self.getText("/Title"))
    title_raw = property(lambda self: self.get("/Title"))

    ##
    # Read-only property accessing the document's author.  Added in v1.6, will
    # exist for all future v1.x releases.  Modified in v1.10 to always return a
    # unicode string (TextStringObject).
    # @return A unicode string, or None if the author is not provided.
    author = property(lambda self: self.getText("/Author"))
    author_raw = property(lambda self: self.get("/Author"))

    ##
    # Read-only property accessing the subject of the document.  Added in v1.6,
    # will exist for all future v1.x releases.  Modified in v1.10 to always
    # return a unicode string (TextStringObject).
    # @return A unicode string, or None if the subject is not provided.
    subject = property(lambda self: self.getText("/Subject"))
    subject_raw = property(lambda self: self.get("/Subject"))

    ##
    # Read-only property accessing the document's creator.  If the document was
    # converted to PDF from another format, the name of the application (for
    # example, OpenOffice) that created the original document from which it was
    # converted.  Added in v1.6, will exist for all future v1.x releases.
    # Modified in v1.10 to always return a unicode string (TextStringObject).
    # @return A unicode string, or None if the creator is not provided.
    creator = property(lambda self: self.getText("/Creator"))
    creator_raw = property(lambda self: self.get("/Creator"))

    ##
    # Read-only property accessing the document's producer.  If the document
    # was converted to PDF from another format, the name of the application
    # (for example, OSX Quartz) that converted it to PDF.  Added in v1.6, will
    # exist for all future v1.x releases.  Modified in v1.10 to always return a
    # unicode string (TextStringObject).
    # @return A unicode string, or None if the producer is not provided.
    producer = property(lambda self: self.getText("/Producer"))
    producer_raw = property(lambda self: self.get("/Producer"))


##
# A class representing a destination within a PDF file.
# See section 8.2.1 of the PDF 1.6 reference.
# Stability: Added in v1.10, will exist for all v1.x releases.
class Destination(DictionaryObject):
    def __init__(self, title, page, typ, *args):
        DictionaryObject.__init__(self)
        self[NameObject("/Title")] = title
        self[NameObject("/Page")] = page
        self[NameObject("/Type")] = typ
        
        # from table 8.2 of the PDF 1.6 reference.
        if typ == "/XYZ":
            (self[NameObject("/Left")], self[NameObject("/Top")],
                self[NameObject("/Zoom")]) = args
        elif typ == "/FitR":
            (self[NameObject("/Left")], self[NameObject("/Bottom")],
                self[NameObject("/Right")], self[NameObject("/Top")]) = args
        elif typ in ["/FitH", "FitBH"]:
            self[NameObject("/Top")], = args
        elif typ in ["/FitV", "FitBV"]:
            self[NameObject("/Left")], = args
        elif typ in ["/Fit", "FitB"]:
            pass
        else:
            raise utils.PdfReadError("Unknown Destination Type: %r" % typ)
          
    ##
    # Read-only property accessing the destination title.
    # @return A string.
    title = property(lambda self: self.get("/Title"))

    ##
    # Read-only property accessing the destination page.
    # @return An integer.
    page = property(lambda self: self.get("/Page"))

    ##
    # Read-only property accessing the destination type.
    # @return A string.
    typ = property(lambda self: self.get("/Type"))

    ##
    # Read-only property accessing the zoom factor.
    # @return A number, or None if not available.
    zoom = property(lambda self: self.get("/Zoom", None))

    ##
    # Read-only property accessing the left horizontal coordinate.
    # @return A number, or None if not available.
    left = property(lambda self: self.get("/Left", None))

    ##
    # Read-only property accessing the right horizontal coordinate.
    # @return A number, or None if not available.
    right = property(lambda self: self.get("/Right", None))

    ##
    # Read-only property accessing the top vertical coordinate.
    # @return A number, or None if not available.
    top = property(lambda self: self.get("/Top", None))

    ##
    # Read-only property accessing the bottom vertical coordinate.
    # @return A number, or None if not available.
    bottom = property(lambda self: self.get("/Bottom", None))

def convertToInt(d, size):
    if size > 8:
        raise utils.PdfReadError("invalid size in convertToInt")
    d = "\x00\x00\x00\x00\x00\x00\x00\x00" + d
    d = d[-8:]
    return struct.unpack(">q", d)[0]

# ref: pdf1.8 spec section 3.5.2 algorithm 3.2
_encryption_padding = '\x28\xbf\x4e\x5e\x4e\x75\x8a\x41\x64\x00\x4e\x56' + \
        '\xff\xfa\x01\x08\x2e\x2e\x00\xb6\xd0\x68\x3e\x80\x2f\x0c' + \
        '\xa9\xfe\x64\x53\x69\x7a'

# Implementation of algorithm 3.2 of the PDF standard security handler,
# section 3.5.2 of the PDF 1.6 reference.
def _alg32(password, rev, keylen, owner_entry, p_entry, id1_entry, metadata_encrypt=True):
    # 1. Pad or truncate the password string to exactly 32 bytes.  If the
    # password string is more than 32 bytes long, use only its first 32 bytes;
    # if it is less than 32 bytes long, pad it by appending the required number
    # of additional bytes from the beginning of the padding string
    # (_encryption_padding).
    password = (password + _encryption_padding)[:32]
    # 2. Initialize the MD5 hash function and pass the result of step 1 as
    # input to this function.
    import struct
    m = md5(password)
    # 3. Pass the value of the encryption dictionary's /O entry to the MD5 hash
    # function.
    m.update(owner_entry)
    # 4. Treat the value of the /P entry as an unsigned 4-byte integer and pass
    # these bytes to the MD5 hash function, low-order byte first.
    p_entry = struct.pack('<i', p_entry)
    m.update(p_entry)
    # 5. Pass the first element of the file's file identifier array to the MD5
    # hash function.
    m.update(id1_entry)
    # 6. (Revision 3 or greater) If document metadata is not being encrypted,
    # pass 4 bytes with the value 0xFFFFFFFF to the MD5 hash function.
    if rev >= 3 and not metadata_encrypt:
        m.update("\xff\xff\xff\xff")
    # 7. Finish the hash.
    md5_hash = m.digest()
    # 8. (Revision 3 or greater) Do the following 50 times: Take the output
    # from the previous MD5 hash and pass the first n bytes of the output as
    # input into a new MD5 hash, where n is the number of bytes of the
    # encryption key as defined by the value of the encryption dictionary's
    # /Length entry.
    if rev >= 3:
        for i in range(50):
            md5_hash = md5(md5_hash[:keylen]).digest()
    # 9. Set the encryption key to the first n bytes of the output from the
    # final MD5 hash, where n is always 5 for revision 2 but, for revision 3 or
    # greater, depends on the value of the encryption dictionary's /Length
    # entry.
    return md5_hash[:keylen]

# Implementation of algorithm 3.3 of the PDF standard security handler,
# section 3.5.2 of the PDF 1.6 reference.
def _alg33(owner_pwd, user_pwd, rev, keylen):
    # steps 1 - 4
    key = _alg33_1(owner_pwd, rev, keylen)
    # 5. Pad or truncate the user password string as described in step 1 of
    # algorithm 3.2.
    user_pwd = (user_pwd + _encryption_padding)[:32]
    # 6. Encrypt the result of step 5, using an RC4 encryption function with
    # the encryption key obtained in step 4.
    val = utils.RC4_encrypt(key, user_pwd)
    # 7. (Revision 3 or greater) Do the following 19 times: Take the output
    # from the previous invocation of the RC4 function and pass it as input to
    # a new invocation of the function; use an encryption key generated by
    # taking each byte of the encryption key obtained in step 4 and performing
    # an XOR operation between that byte and the single-byte value of the
    # iteration counter (from 1 to 19).
    if rev >= 3:
        for i in range(1, 20):
            new_key = ''
            for l in range(len(key)):
                new_key += chr(ord(key[l]) ^ i)
            val = utils.RC4_encrypt(new_key, val)
    # 8. Store the output from the final invocation of the RC4 as the value of
    # the /O entry in the encryption dictionary.
    return val

# Steps 1-4 of algorithm 3.3
def _alg33_1(password, rev, keylen):
    # 1. Pad or truncate the owner password string as described in step 1 of
    # algorithm 3.2.  If there is no owner password, use the user password
    # instead.
    password = (password + _encryption_padding)[:32]
    # 2. Initialize the MD5 hash function and pass the result of step 1 as
    # input to this function.
    m = md5(password)
    # 3. (Revision 3 or greater) Do the following 50 times: Take the output
    # from the previous MD5 hash and pass it as input into a new MD5 hash.
    md5_hash = m.digest()
    if rev >= 3:
        for i in range(50):
            md5_hash = md5(md5_hash).digest()
    # 4. Create an RC4 encryption key using the first n bytes of the output
    # from the final MD5 hash, where n is always 5 for revision 2 but, for
    # revision 3 or greater, depends on the value of the encryption
    # dictionary's /Length entry.
    key = md5_hash[:keylen]
    return key

# Implementation of algorithm 3.4 of the PDF standard security handler,
# section 3.5.2 of the PDF 1.6 reference.
def _alg34(password, owner_entry, p_entry, id1_entry):
    # 1. Create an encryption key based on the user password string, as
    # described in algorithm 3.2.
    key = _alg32(password, 2, 5, owner_entry, p_entry, id1_entry)
    # 2. Encrypt the 32-byte padding string shown in step 1 of algorithm 3.2,
    # using an RC4 encryption function with the encryption key from the
    # preceding step.
    U = utils.RC4_encrypt(key, _encryption_padding)
    # 3. Store the result of step 2 as the value of the /U entry in the
    # encryption dictionary.
    return U, key

# Implementation of algorithm 3.4 of the PDF standard security handler,
# section 3.5.2 of the PDF 1.6 reference.
def _alg35(password, rev, keylen, owner_entry, p_entry, id1_entry, metadata_encrypt):
    # 1. Create an encryption key based on the user password string, as
    # described in Algorithm 3.2.
    key = _alg32(password, rev, keylen, owner_entry, p_entry, id1_entry)
    # 2. Initialize the MD5 hash function and pass the 32-byte padding string
    # shown in step 1 of Algorithm 3.2 as input to this function. 
    m = md5()
    m.update(_encryption_padding)
    # 3. Pass the first element of the file's file identifier array (the value
    # of the ID entry in the document's trailer dictionary; see Table 3.13 on
    # page 73) to the hash function and finish the hash.  (See implementation
    # note 25 in Appendix H.) 
    m.update(id1_entry)
    md5_hash = m.digest()
    # 4. Encrypt the 16-byte result of the hash, using an RC4 encryption
    # function with the encryption key from step 1. 
    val = utils.RC4_encrypt(key, md5_hash)
    # 5. Do the following 19 times: Take the output from the previous
    # invocation of the RC4 function and pass it as input to a new invocation
    # of the function; use an encryption key generated by taking each byte of
    # the original encryption key (obtained in step 2) and performing an XOR
    # operation between that byte and the single-byte value of the iteration
    # counter (from 1 to 19). 
    for i in range(1, 20):
        new_key = ''
        for l in range(len(key)):
            new_key += chr(ord(key[l]) ^ i)
        val = utils.RC4_encrypt(new_key, val)
    # 6. Append 16 bytes of arbitrary padding to the output from the final
    # invocation of the RC4 function and store the 32-byte result as the value
    # of the U entry in the encryption dictionary. 
    # (implementator note: I don't know what "arbitrary padding" is supposed to
    # mean, so I have used null bytes.  This seems to match a few other
    # people's implementations)
    return val + ('\x00' * 16), key

#if __name__ == "__main__":
#    output = PdfFileWriter()
#
#    input1 = PdfFileReader(file("test\\5000-s1-05e.pdf", "rb"))
#    page1 = input1.getPage(0)
#
#    input2 = PdfFileReader(file("test\\PDFReference16.pdf", "rb"))
#    page2 = input2.getPage(0)
#    page3 = input2.getPage(1)
#    page1.mergePage(page2)
#    page1.mergePage(page3)
#
#    input3 = PdfFileReader(file("test\\cc-cc.pdf", "rb"))
#    page1.mergePage(input3.getPage(0))
#
#    page1.compressContentStreams()
#
#    output.addPage(page1)
#    output.write(file("test\\merge-test.pdf", "wb"))



########NEW FILE########
__FILENAME__ = utils
# vim: sw=4:expandtab:foldmethod=marker
#
# Copyright (c) 2006, Mathieu Fenniak
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# * The name of the author may not be used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


"""
Utility functions for PDF library.
"""
__author__ = "Mathieu Fenniak"
__author_email__ = "biziqe@mathieu.fenniak.net"

#ENABLE_PSYCO = False
#if ENABLE_PSYCO:
#    try:
#        import psyco
#    except ImportError:
#        ENABLE_PSYCO = False
#
#if not ENABLE_PSYCO:
#    class psyco:
#        def proxy(func):
#            return func
#        proxy = staticmethod(proxy)

def readUntilWhitespace(stream, maxchars=None):
    txt = ""
    while True:
        tok = stream.read(1)
        if tok.isspace() or not tok:
            break
        txt += tok
        if len(txt) == maxchars:
            break
    return txt

def readNonWhitespace(stream):
    tok = ' '
    while tok == '\n' or tok == '\r' or tok == ' ' or tok == '\t':
        tok = stream.read(1)
    return tok

class ConvertFunctionsToVirtualList(object):
    def __init__(self, lengthFunction, getFunction):
        self.lengthFunction = lengthFunction
        self.getFunction = getFunction

    def __len__(self):
        return self.lengthFunction()

    def __getitem__(self, index):
        if not isinstance(index, int):
            raise TypeError, "sequence indices must be integers"
        len_self = len(self)
        if index < 0:
            # support negative indexes
            index = len_self + index
        if index < 0 or index >= len_self:
            raise IndexError, "sequence index out of range"
        return self.getFunction(index)

def RC4_encrypt(key, plaintext):
    S = [i for i in range(256)]
    j = 0
    for i in range(256):
        j = (j + S[i] + ord(key[i % len(key)])) % 256
        S[i], S[j] = S[j], S[i]
    i, j = 0, 0
    retval = ""
    for x in range(len(plaintext)):
        i = (i + 1) % 256
        j = (j + S[i]) % 256
        S[i], S[j] = S[j], S[i]
        t = S[(S[i] + S[j]) % 256]
        retval += chr(ord(plaintext[x]) ^ t)
    return retval

def matrixMultiply(a, b):
    return [[sum([float(i)*float(j)
                  for i, j in zip(row, col)]
                ) for col in zip(*b)]
            for row in a]

class PyPdfError(Exception):
    pass

class PdfReadError(PyPdfError):
    pass

class PageSizeNotDefinedError(PyPdfError):
    pass

if __name__ == "__main__":
    # test RC4
    out = RC4_encrypt("Key", "Plaintext")
    print repr(out)
    pt = RC4_encrypt("Key", out)
    print repr(pt)

########NEW FILE########
__FILENAME__ = xmp
import re
import datetime
import decimal
from generic import PdfObject
from xml.dom import getDOMImplementation
from xml.dom.minidom import parseString

RDF_NAMESPACE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
DC_NAMESPACE = "http://purl.org/dc/elements/1.1/"
XMP_NAMESPACE = "http://ns.adobe.com/xap/1.0/"
PDF_NAMESPACE = "http://ns.adobe.com/pdf/1.3/"
XMPMM_NAMESPACE = "http://ns.adobe.com/xap/1.0/mm/"

# What is the PDFX namespace, you might ask?  I might ask that too.  It's
# a completely undocumented namespace used to place "custom metadata"
# properties, which are arbitrary metadata properties with no semantic or
# documented meaning.  Elements in the namespace are key/value-style storage,
# where the element name is the key and the content is the value.  The keys
# are transformed into valid XML identifiers by substituting an invalid
# identifier character with \u2182 followed by the unicode hex ID of the
# original character.  A key like "my car" is therefore "my\u21820020car".
#
# \u2182, in case you're wondering, is the unicode character
# \u{ROMAN NUMERAL TEN THOUSAND}, a straightforward and obvious choice for
# escaping characters.
#
# Intentional users of the pdfx namespace should be shot on sight.  A
# custom data schema and sensical XML elements could be used instead, as is
# suggested by Adobe's own documentation on XMP (under "Extensibility of
# Schemas").
#
# Information presented here on the /pdfx/ schema is a result of limited
# reverse engineering, and does not constitute a full specification.
PDFX_NAMESPACE = "http://ns.adobe.com/pdfx/1.3/"

iso8601 = re.compile("""
        (?P<year>[0-9]{4})
        (-
            (?P<month>[0-9]{2})
            (-
                (?P<day>[0-9]+)
                (T
                    (?P<hour>[0-9]{2}):
                    (?P<minute>[0-9]{2})
                    (:(?P<second>[0-9]{2}(.[0-9]+)?))?
                    (?P<tzd>Z|[-+][0-9]{2}:[0-9]{2})
                )?
            )?
        )?
        """, re.VERBOSE)

##
# An object that represents Adobe XMP metadata.
class XmpInformation(PdfObject):

    def __init__(self, stream):
        self.stream = stream
        docRoot = parseString(self.stream.getData())
        self.rdfRoot = docRoot.getElementsByTagNameNS(RDF_NAMESPACE, "RDF")[0]
        self.cache = {}

    def writeToStream(self, stream, encryption_key):
        self.stream.writeToStream(stream, encryption_key)

    def getElement(self, aboutUri, namespace, name):
        for desc in self.rdfRoot.getElementsByTagNameNS(RDF_NAMESPACE, "Description"):
            if desc.getAttributeNS(RDF_NAMESPACE, "about") == aboutUri:
                attr = desc.getAttributeNodeNS(namespace, name)
                if attr != None:
                    yield attr
                for element in desc.getElementsByTagNameNS(namespace, name):
                    yield element

    def getNodesInNamespace(self, aboutUri, namespace):
        for desc in self.rdfRoot.getElementsByTagNameNS(RDF_NAMESPACE, "Description"):
            if desc.getAttributeNS(RDF_NAMESPACE, "about") == aboutUri:
                for i in range(desc.attributes.length):
                    attr = desc.attributes.item(i)
                    if attr.namespaceURI == namespace:
                        yield attr
                for child in desc.childNodes:
                    if child.namespaceURI == namespace:
                        yield child

    def _getText(self, element):
        text = ""
        for child in element.childNodes:
            if child.nodeType == child.TEXT_NODE:
                text += child.data
        return text

    def _converter_string(value):
        return value

    def _converter_date(value):
        m = iso8601.match(value)
        year = int(m.group("year"))
        month = int(m.group("month") or "1")
        day = int(m.group("day") or "1")
        hour = int(m.group("hour") or "0")
        minute = int(m.group("minute") or "0")
        second = decimal.Decimal(m.group("second") or "0")
        seconds = second.to_integral(decimal.ROUND_FLOOR)
        milliseconds = (second - seconds) * 1000000
        tzd = m.group("tzd") or "Z"
        dt = datetime.datetime(year, month, day, hour, minute, seconds, milliseconds)
        if tzd != "Z":
            tzd_hours, tzd_minutes = [int(x) for x in tzd.split(":")]
            tzd_hours *= -1
            if tzd_hours < 0:
                tzd_minutes *= -1
            dt = dt + datetime.timedelta(hours=tzd_hours, minutes=tzd_minutes)
        return dt
    _test_converter_date = staticmethod(_converter_date)

    def _getter_bag(namespace, name, converter):
        def get(self):
            cached = self.cache.get(namespace, {}).get(name)
            if cached:
                return cached
            retval = []
            for element in self.getElement("", namespace, name):
                bags = element.getElementsByTagNameNS(RDF_NAMESPACE, "Bag")
                if len(bags):
                    for bag in bags:
                        for item in bag.getElementsByTagNameNS(RDF_NAMESPACE, "li"):
                            value = self._getText(item)
                            value = converter(value)
                            retval.append(value)
            ns_cache = self.cache.setdefault(namespace, {})
            ns_cache[name] = retval
            return retval
        return get

    def _getter_seq(namespace, name, converter):
        def get(self):
            cached = self.cache.get(namespace, {}).get(name)
            if cached:
                return cached
            retval = []
            for element in self.getElement("", namespace, name):
                seqs = element.getElementsByTagNameNS(RDF_NAMESPACE, "Seq")
                if len(seqs):
                    for seq in seqs:
                        for item in seq.getElementsByTagNameNS(RDF_NAMESPACE, "li"):
                            value = self._getText(item)
                            value = converter(value)
                            retval.append(value)
                else:
                    value = converter(self._getText(element))
                    retval.append(value)
            ns_cache = self.cache.setdefault(namespace, {})
            ns_cache[name] = retval
            return retval
        return get

    def _getter_langalt(namespace, name, converter):
        def get(self):
            cached = self.cache.get(namespace, {}).get(name)
            if cached:
                return cached
            retval = {}
            for element in self.getElement("", namespace, name):
                alts = element.getElementsByTagNameNS(RDF_NAMESPACE, "Alt")
                if len(alts):
                    for alt in alts:
                        for item in alt.getElementsByTagNameNS(RDF_NAMESPACE, "li"):
                            value = self._getText(item)
                            value = converter(value)
                            retval[item.getAttribute("xml:lang")] = value
                else:
                    retval["x-default"] = converter(self._getText(element))
            ns_cache = self.cache.setdefault(namespace, {})
            ns_cache[name] = retval
            return retval
        return get

    def _getter_single(namespace, name, converter):
        def get(self):
            cached = self.cache.get(namespace, {}).get(name)
            if cached:
                return cached
            value = None
            for element in self.getElement("", namespace, name):
                if element.nodeType == element.ATTRIBUTE_NODE:
                    value = element.nodeValue
                else:
                    value = self._getText(element)
                break
            if value != None:
                value = converter(value)
            ns_cache = self.cache.setdefault(namespace, {})
            ns_cache[name] = value
            return value
        return get

    ##
    # Contributors to the resource (other than the authors).  An unsorted
    # array of names.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_contributor = property(_getter_bag(DC_NAMESPACE, "contributor", _converter_string))

    ##
    # Text describing the extent or scope of the resource.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_coverage = property(_getter_single(DC_NAMESPACE, "coverage", _converter_string))

    ##
    # A sorted array of names of the authors of the resource, listed in order
    # of precedence.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_creator = property(_getter_seq(DC_NAMESPACE, "creator", _converter_string))

    ##
    # A sorted array of dates (datetime.datetime instances) of signifigance to
    # the resource.  The dates and times are in UTC.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_date = property(_getter_seq(DC_NAMESPACE, "date", _converter_date))

    ##
    # A language-keyed dictionary of textual descriptions of the content of the
    # resource.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_description = property(_getter_langalt(DC_NAMESPACE, "description", _converter_string))

    ##
    # The mime-type of the resource.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_format = property(_getter_single(DC_NAMESPACE, "format", _converter_string))

    ##
    # Unique identifier of the resource.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_identifier = property(_getter_single(DC_NAMESPACE, "identifier", _converter_string))

    ##
    # An unordered array specifying the languages used in the resource.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_language = property(_getter_bag(DC_NAMESPACE, "language", _converter_string))

    ##
    # An unordered array of publisher names.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_publisher = property(_getter_bag(DC_NAMESPACE, "publisher", _converter_string))

    ##
    # An unordered array of text descriptions of relationships to other
    # documents.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_relation = property(_getter_bag(DC_NAMESPACE, "relation", _converter_string))

    ##
    # A language-keyed dictionary of textual descriptions of the rights the
    # user has to this resource.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_rights = property(_getter_langalt(DC_NAMESPACE, "rights", _converter_string))

    ##
    # Unique identifier of the work from which this resource was derived.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_source = property(_getter_single(DC_NAMESPACE, "source", _converter_string))

    ##
    # An unordered array of descriptive phrases or keywrods that specify the
    # topic of the content of the resource.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_subject = property(_getter_bag(DC_NAMESPACE, "subject", _converter_string))

    ##
    # A language-keyed dictionary of the title of the resource.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_title = property(_getter_langalt(DC_NAMESPACE, "title", _converter_string))

    ##
    # An unordered array of textual descriptions of the document type.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_type = property(_getter_bag(DC_NAMESPACE, "type", _converter_string))

    ##
    # An unformatted text string representing document keywords.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    pdf_keywords = property(_getter_single(PDF_NAMESPACE, "Keywords", _converter_string))

    ##
    # The PDF file version, for example 1.0, 1.3.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    pdf_pdfversion = property(_getter_single(PDF_NAMESPACE, "PDFVersion", _converter_string))

    ##
    # The name of the tool that created the PDF document.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    pdf_producer = property(_getter_single(PDF_NAMESPACE, "Producer", _converter_string))

    ##
    # The date and time the resource was originally created.  The date and
    # time are returned as a UTC datetime.datetime object.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    xmp_createDate = property(_getter_single(XMP_NAMESPACE, "CreateDate", _converter_date))
    
    ##
    # The date and time the resource was last modified.  The date and time
    # are returned as a UTC datetime.datetime object.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    xmp_modifyDate = property(_getter_single(XMP_NAMESPACE, "ModifyDate", _converter_date))

    ##
    # The date and time that any metadata for this resource was last
    # changed.  The date and time are returned as a UTC datetime.datetime
    # object.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    xmp_metadataDate = property(_getter_single(XMP_NAMESPACE, "MetadataDate", _converter_date))

    ##
    # The name of the first known tool used to create the resource.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    xmp_creatorTool = property(_getter_single(XMP_NAMESPACE, "CreatorTool", _converter_string))

    ##
    # The common identifier for all versions and renditions of this resource.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    xmpmm_documentId = property(_getter_single(XMPMM_NAMESPACE, "DocumentID", _converter_string))

    ##
    # An identifier for a specific incarnation of a document, updated each
    # time a file is saved.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    xmpmm_instanceId = property(_getter_single(XMPMM_NAMESPACE, "InstanceID", _converter_string))

    def custom_properties(self):
        if not hasattr(self, "_custom_properties"):
            self._custom_properties = {}
            for node in self.getNodesInNamespace("", PDFX_NAMESPACE):
                key = node.localName
                while True:
                    # see documentation about PDFX_NAMESPACE earlier in file
                    idx = key.find(u"\u2182")
                    if idx == -1:
                        break
                    key = key[:idx] + chr(int(key[idx+1:idx+5], base=16)) + key[idx+5:]
                if node.nodeType == node.ATTRIBUTE_NODE:
                    value = node.nodeValue
                else:
                    value = self._getText(node)
                self._custom_properties[key] = value
        return self._custom_properties

    ##
    # Retrieves custom metadata properties defined in the undocumented pdfx
    # metadata schema.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    # @return Returns a dictionary of key/value items for custom metadata
    # properties.
    custom_properties = property(custom_properties)



########NEW FILE########
__FILENAME__ = socks
"""SocksiPy - Python SOCKS module.
Version 1.00

Copyright 2006 Dan-Haim. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of Dan Haim nor the names of his contributors may be used
   to endorse or promote products derived from this software without specific
   prior written permission.
   
THIS SOFTWARE IS PROVIDED BY DAN HAIM "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL DAN HAIM OR HIS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA
OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMANGE.


This module provides a standard socket-like interface for Python
for tunneling connections through SOCKS proxies.

"""

"""

Minor modifications made by Christopher Gilbert (http://motomastyle.com/)
for use in PyLoris (http://pyloris.sourceforge.net/)

Minor modifications made by Mario Vilas (http://breakingcode.wordpress.com/)
mainly to merge bug fixes found in Sourceforge

Minor modification made by Steve Micallef (http://www.binarypool.com/)
to add getaddrinfo, as per http://stackoverflow.com/questions/13184205/dns-over-proxy

"""

import socket
import struct
import sys

PROXY_TYPE_SOCKS4 = 1
PROXY_TYPE_SOCKS5 = 2
PROXY_TYPE_HTTP = 3

_defaultproxy = None
_orgsocket = socket.socket

class ProxyError(Exception): pass
class GeneralProxyError(ProxyError): pass
class Socks5AuthError(ProxyError): pass
class Socks5Error(ProxyError): pass
class Socks4Error(ProxyError): pass
class HTTPError(ProxyError): pass

_generalerrors = ("success",
    "invalid data",
    "not connected",
    "not available",
    "bad proxy type",
    "bad input")

_socks5errors = ("succeeded",
    "general SOCKS server failure",
    "connection not allowed by ruleset",
    "Network unreachable",
    "Host unreachable",
    "Connection refused",
    "TTL expired",
    "Command not supported",
    "Address type not supported",
    "Unknown error")

_socks5autherrors = ("succeeded",
    "authentication is required",
    "all offered authentication methods were rejected",
    "unknown username or invalid password",
    "unknown error")

_socks4errors = ("request granted",
    "request rejected or failed",
    "request rejected because SOCKS server cannot connect to identd on the client",
    "request rejected because the client program and identd report different user-ids",
    "unknown error")

def setdefaultproxy(proxytype=None, addr=None, port=None, rdns=True, username=None, password=None):
    """setdefaultproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
    Sets a default proxy which all further socksocket objects will use,
    unless explicitly changed.
    """
    global _defaultproxy
    _defaultproxy = (proxytype, addr, port, rdns, username, password)

def create_connection(address, timeout=None, source_address=None):
    sock = socksocket()
    sock.connect(address)
    return sock

def getaddrinfo(*args):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (args[0], args[1]))]

def wrapmodule(module):
    """wrapmodule(module)
    Attempts to replace a module's socket library with a SOCKS socket. Must set
    a default proxy using setdefaultproxy(...) first.
    This will only work on modules that import socket directly into the namespace;
    most of the Python Standard Library falls into this category.
    """
    if _defaultproxy != None:
        module.socket.socket = socksocket
    else:
        raise GeneralProxyError((4, "no proxy specified"))

class socksocket(socket.socket):
    """socksocket([family[, type[, proto]]]) -> socket object
    Open a SOCKS enabled socket. The parameters are the same as
    those of the standard socket init. In order for SOCKS to work,
    you must specify family=AF_INET, type=SOCK_STREAM and proto=0.
    """

    def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, _sock=None):
        _orgsocket.__init__(self, family, type, proto, _sock)
        if _defaultproxy != None:
            self.__proxy = _defaultproxy
        else:
            self.__proxy = (None, None, None, None, None, None)
        self.__proxysockname = None
        self.__proxypeername = None

    def __recvall(self, count):
        """__recvall(count) -> data
        Receive EXACTLY the number of bytes requested from the socket.
        Blocks until the required number of bytes have been received.
        """
        data = self.recv(count)
        while len(data) < count:
            d = self.recv(count-len(data))
            if not d: raise GeneralProxyError((0, "connection closed unexpectedly"))
            data = data + d
        return data

    def setproxy(self, proxytype=None, addr=None, port=None, rdns=True, username=None, password=None):
        """setproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
        Sets the proxy to be used.
        proxytype -    The type of the proxy to be used. Three types
                are supported: PROXY_TYPE_SOCKS4 (including socks4a),
                PROXY_TYPE_SOCKS5 and PROXY_TYPE_HTTP
        addr -        The address of the server (IP or DNS).
        port -        The port of the server. Defaults to 1080 for SOCKS
                servers and 8080 for HTTP proxy servers.
        rdns -        Should DNS queries be preformed on the remote side
                (rather than the local side). The default is True.
                Note: This has no effect with SOCKS4 servers.
        username -    Username to authenticate with to the server.
                The default is no authentication.
        password -    Password to authenticate with to the server.
                Only relevant when username is also provided.
        """
        self.__proxy = (proxytype, addr, port, rdns, username, password)

    def __negotiatesocks5(self, destaddr, destport):
        """__negotiatesocks5(self,destaddr,destport)
        Negotiates a connection through a SOCKS5 server.
        """
        # First we'll send the authentication packages we support.
        if (self.__proxy[4]!=None) and (self.__proxy[5]!=None):
            # The username/password details were supplied to the
            # setproxy method so we support the USERNAME/PASSWORD
            # authentication (in addition to the standard none).
            self.sendall(struct.pack('BBBB', 0x05, 0x02, 0x00, 0x02))
        else:
            # No username/password were entered, therefore we
            # only support connections with no authentication.
            self.sendall(struct.pack('BBB', 0x05, 0x01, 0x00))
        # We'll receive the server's response to determine which
        # method was selected
        chosenauth = self.__recvall(2)
        if chosenauth[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        # Check the chosen authentication method
        if chosenauth[1:2] == chr(0x00).encode():
            # No authentication is required
            pass
        elif chosenauth[1:2] == chr(0x02).encode():
            # Okay, we need to perform a basic username/password
            # authentication.
            self.sendall(chr(0x01).encode() + chr(len(self.__proxy[4])) + self.__proxy[4] + chr(len(self.__proxy[5])) + self.__proxy[5])
            authstat = self.__recvall(2)
            if authstat[0:1] != chr(0x01).encode():
                # Bad response
                self.close()
                raise GeneralProxyError((1, _generalerrors[1]))
            if authstat[1:2] != chr(0x00).encode():
                # Authentication failed
                self.close()
                raise Socks5AuthError((3, _socks5autherrors[3]))
            # Authentication succeeded
        else:
            # Reaching here is always bad
            self.close()
            if chosenauth[1] == chr(0xFF).encode():
                raise Socks5AuthError((2, _socks5autherrors[2]))
            else:
                raise GeneralProxyError((1, _generalerrors[1]))
        # Now we can request the actual connection
        req = struct.pack('BBB', 0x05, 0x01, 0x00)
        # If the given destination address is an IP address, we'll
        # use the IPv4 address request even if remote resolving was specified.
        try:
            ipaddr = socket.inet_aton(destaddr)
            req = req + chr(0x01).encode() + ipaddr
        except socket.error:
            # Well it's not an IP number,  so it's probably a DNS name.
            if self.__proxy[3]:
                # Resolve remotely
                ipaddr = None
                req = req + chr(0x03).encode() + chr(len(destaddr)).encode() + destaddr
            else:
                # Resolve locally
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
                req = req + chr(0x01).encode() + ipaddr
        req = req + struct.pack(">H", destport)
        self.sendall(req)
        # Get the response
        resp = self.__recvall(4)
        if resp[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        elif resp[1:2] != chr(0x00).encode():
            # Connection failed
            self.close()
            if ord(resp[1:2])<=8:
                raise Socks5Error((ord(resp[1:2]), _socks5errors[ord(resp[1:2])]))
            else:
                raise Socks5Error((9, _socks5errors[9]))
        # Get the bound address/port
        elif resp[3:4] == chr(0x01).encode():
            boundaddr = self.__recvall(4)
        elif resp[3:4] == chr(0x03).encode():
            resp = resp + self.recv(1)
            boundaddr = self.__recvall(ord(resp[4:5]))
        else:
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        boundport = struct.unpack(">H", self.__recvall(2))[0]
        self.__proxysockname = (boundaddr, boundport)
        if ipaddr != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def getproxysockname(self):
        """getsockname() -> address info
        Returns the bound IP address and port number at the proxy.
        """
        return self.__proxysockname

    def getproxypeername(self):
        """getproxypeername() -> address info
        Returns the IP and port number of the proxy.
        """
        return _orgsocket.getpeername(self)

    def getpeername(self):
        """getpeername() -> address info
        Returns the IP address and port number of the destination
        machine (note: getproxypeername returns the proxy)
        """
        return self.__proxypeername

    def __negotiatesocks4(self,destaddr,destport):
        """__negotiatesocks4(self,destaddr,destport)
        Negotiates a connection through a SOCKS4 server.
        """
        # Check if the destination address provided is an IP address
        rmtrslv = False
        try:
            ipaddr = socket.inet_aton(destaddr)
        except socket.error:
            # It's a DNS name. Check where it should be resolved.
            if self.__proxy[3]:
                ipaddr = struct.pack("BBBB", 0x00, 0x00, 0x00, 0x01)
                rmtrslv = True
            else:
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
        # Construct the request packet
        req = struct.pack(">BBH", 0x04, 0x01, destport) + ipaddr
        # The username parameter is considered userid for SOCKS4
        if self.__proxy[4] != None:
            req = req + self.__proxy[4]
        req = req + chr(0x00).encode()
        # DNS name if remote resolving is required
        # NOTE: This is actually an extension to the SOCKS4 protocol
        # called SOCKS4A and may not be supported in all cases.
        if rmtrslv:
            req = req + destaddr + chr(0x00).encode()
        self.sendall(req)
        # Get the response from the server
        resp = self.__recvall(8)
        if resp[0:1] != chr(0x00).encode():
            # Bad data
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        if resp[1:2] != chr(0x5A).encode():
            # Server returned an error
            self.close()
            if ord(resp[1:2]) in (91, 92, 93):
                self.close()
                raise Socks4Error((ord(resp[1:2]), _socks4errors[ord(resp[1:2]) - 90]))
            else:
                raise Socks4Error((94, _socks4errors[4]))
        # Get the bound address/port
        self.__proxysockname = (socket.inet_ntoa(resp[4:]), struct.unpack(">H", resp[2:4])[0])
        if rmtrslv != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def __negotiatehttp(self, destaddr, destport):
        """__negotiatehttp(self,destaddr,destport)
        Negotiates a connection through an HTTP server.
        """
        # If we need to resolve locally, we do this now
        if not self.__proxy[3]:
            addr = socket.gethostbyname(destaddr)
        else:
            addr = destaddr
        self.sendall(("CONNECT " + addr + ":" + str(destport) + " HTTP/1.1\r\n" + "Host: " + destaddr + "\r\n\r\n").encode())
        # We read the response until we get the string "\r\n\r\n"
        resp = self.recv(1)
        while resp.find("\r\n\r\n".encode()) == -1:
            resp = resp + self.recv(1)
        # We just need the first line to check if the connection
        # was successful
        statusline = resp.splitlines()[0].split(" ".encode(), 2)
        if statusline[0] not in ("HTTP/1.0".encode(), "HTTP/1.1".encode()):
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        try:
            statuscode = int(statusline[1])
        except ValueError:
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        if statuscode != 200:
            self.close()
            raise HTTPError((statuscode, statusline[2]))
        self.__proxysockname = ("0.0.0.0", 0)
        self.__proxypeername = (addr, destport)

    def connect(self, destpair):
        """connect(self, despair)
        Connects to the specified destination through a proxy.
        destpar - A tuple of the IP/DNS address and the port number.
        (identical to socket's connect).
        To select the proxy server use setproxy().
        """
        # Do a minimal input check first
        if (not type(destpair) in (list,tuple)) or (len(destpair) < 2) or (type(destpair[0]) != type('')) or (type(destpair[1]) != int):
            raise GeneralProxyError((5, _generalerrors[5]))
        if self.__proxy[0] == PROXY_TYPE_SOCKS5:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self, (self.__proxy[1], portnum))
            self.__negotiatesocks5(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_SOCKS4:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self,(self.__proxy[1], portnum))
            self.__negotiatesocks4(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_HTTP:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 8080
            _orgsocket.connect(self,(self.__proxy[1], portnum))
            self.__negotiatehttp(destpair[0], destpair[1])
        elif self.__proxy[0] == None:
            _orgsocket.connect(self, (destpair[0], destpair[1]))
        else:
            raise GeneralProxyError((4, _generalerrors[4]))

########NEW FILE########
__FILENAME__ = sfp_affilinfo
#-------------------------------------------------------------------------------
# Name:         sfp_affilinfo
# Purpose:      Identify the domain and IP of affiliates (useful for reporting/analysis.)
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     8/10/2013
# Copyright:   (c) Steve Micallef 2013
# Licence:     GPL
#-------------------------------------------------------------------------------

import re
import sys
import socket
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_affilinfo(SpiderFootPlugin):
    """Affiliate Info:Gather information about confirmed affiliates (IP Addresses, Domains)."""

    # Default options
    opts = { }

    # Option descriptions
    optdescs = {
        # For each option in opts you should have a key/value pair here
        # describing it. It will end up in the UI to explain the option
        # to the end-user.
    }

    # Target
    baseDomain = None # calculated from the URL in setup
    results = dict()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = dict()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    # * = be notified about all events.
    def watchedEvents(self):
        return ["AFFILIATE"]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "AFFILIATE_DOMAIN", "AFFILIATE_IPADDR" ]

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data
        if '://' in eventData:
            fqdn = sf.urlFQDN(eventData)
        else:
            fqdn = eventData

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)
        domain = sf.hostDomain(fqdn, self.opts['_internettlds'])
        sf.debug("Domain for " + fqdn + " is " + domain)

        sf.debug("Affiliate domain: " + domain)
        evt = SpiderFootEvent("AFFILIATE_DOMAIN", domain, self.__name__, event)
        self.notifyListeners(evt)

        # Resolve the IP
        try:
            notif = list()
            addrs = socket.gethostbyname_ex(fqdn)
            for addr in addrs:
                if type(addr) == list:
                    for a in addr:
                        if sf.validIP(a):
                            notif.append(a)
                else:
                    if sf.validIP(addr):            
                        notif.append(addr)
            for a in notif:
                sf.debug("Affiliate IP: " + a)
                evt = SpiderFootEvent("AFFILIATE_IPADDR", a, self.__name__, event)
                self.notifyListeners(evt)

        except BaseException as e:
            sf.debug("Unable to get an IP for " + fqdn + "(" + str(e) + ")")
            return None

# End of sfp_affilinfo class

########NEW FILE########
__FILENAME__ = sfp_bingsearch
#-------------------------------------------------------------------------------
# Name:         sfp_bingsearch
# Purpose:      Searches Bing for content related to the domain in question.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     06/10/2013
# Copyright:   (c) Steve Micallef 2013
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import random
import re
import time
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_bingsearch(SpiderFootPlugin):
    """Bing:Some light Bing scraping to identify sub-domains and links."""

    # Default options
    opts = {
        'fetchlinks':   True,   # Should we fetch links on the base domain?
        'pages':        20      # Number of bing results pages to iterate
    }

    # Option descriptions
    optdescs = {
        'fetchlinks': "Fetch links found on the target domain-name?",
        'pages':    "Number of Bing results pages to iterate through."
    }

    # Target
    baseDomain = None
    results = list()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = list()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return None

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "LINKED_URL_INTERNAL", "SEARCH_ENGINE_WEB_CONTENT", 
            "CO_HOSTED_SITE" ]

    def start(self):
        # Sites hosted on the domain
        pages = sf.bingIterate("site:" + self.baseDomain, dict(limit=self.opts['pages'],
            useragent=self.opts['_useragent'], timeout=self.opts['_fetchtimeout']))
        if pages == None:
            sf.info("No results returned from Bing.")
            return None

        for page in pages.keys():
            if page in self.results:
                continue
            else:
                self.results.append(page)

            # Check if we've been asked to stop
            if self.checkForStop():
                return None

            # Submit the bing results for analysis
            evt = SpiderFootEvent("SEARCH_ENGINE_WEB_CONTENT", pages[page], self.__name__)
            self.notifyListeners(evt)

            # We can optionally fetch links to our domain found in the search
            # results. These may not have been identified through spidering.
            if self.opts['fetchlinks']:
                links = sf.parseLinks(page, pages[page], self.baseDomain)
                if len(links) == 0:
                    continue

                for link in links:
                    if link in self.results:
                        continue
                    else:
                        self.results.append(link)
                    if sf.urlBaseUrl(link).endswith(self.baseDomain):
                        sf.debug("Found a link: " + link)
                        if self.checkForStop():
                            return None

                        evt = SpiderFootEvent("LINKED_URL_INTERNAL", link, self.__name__)
                        self.notifyListeners(evt)

# End of sfp_bingsearch class

########NEW FILE########
__FILENAME__ = sfp_blacklist
#-------------------------------------------------------------------------------
# Name:         sfp_blacklist
# Purpose:      SpiderFoot plug-in for looking up whether IPs/Netblocks/Domains
#               appear in various block lists, indicating potential open-relays,
#               open proxies, malicious servers, vulnerable servers, etc.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     07/01/2014
# Copyright:   (c) Steve Micallef 2014
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import re
import socket
import random
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_blacklist(SpiderFootPlugin):
    """Blacklist: Query various blacklist database for open relays, open proxies, vulnerable servers, etc."""

    # Default options
    opts = {
    }

    # Option descriptions
    optdescs = {
    }

    # Target
    baseDomain = None
    results = dict()

    # Whole bunch here:
    # http://en.wikipedia.org/wiki/Comparison_of_DNS_blacklists
    # Check out:
    # http://www.blocklist.de/en/rbldns.html
    checks = {
        "http.dnsbl.sorbs.net": "SORBS - Open HTTP Proxy",
        "socks.dnsbl.sorbs.net": "SORBS - Open SOCKS Proxy",
        "misc.dnsbl.sorbs.net": "SORBS - Open Proxy",
        "smtp.dnsbl.sorbs.net": "SORBS - Open SMTP Relay",
        "spam.dnsbl.sorbs.net": 'SORBS - Spammer',
        "recent.spam.dnsbl.sorbs.net": 'SORBS - Recent Spammer',
        "web.dnsbl.sorbs.net": 'SORBS - Vulnerability exposed to spammers',
        "dnsbl.dronebl.org": {
            "127.0.0.3": "dronebl.org - IRC Drone",
            "127.0.0.5": "dronebl.org - Bottler",
            "127.0.0.6": "dronebl.org - Unknown spambot or drone",
            "127.0.0.7": "dronebl.org - DDOS Drone",
            "127.0.0.8": "dronebl.org - SOCKS Proxy",
            "127.0.0.9": "dronebl.org - HTTP Proxy",
            "127.0.0.10": "dronebl.org - ProxyChain",
            "127.0.0.13": "dronebl.org - Brute force attackers",
            "127.0.0.14": "dronebl.org - Open Wingate Proxy",
            "127.0.0.15": "dronebl.org - Compromised router / gateway",
            "127.0.0.17": "dronebl.org - Automatically determined botnet IPs (experimental)",
            "127.0.0.255": "dronebl.org - Unknown"
        },
        "dnsbl-1.uceprotect.net": 'UCEPROTECT - Level 1 (high likelihood)',
        "dnsbl-2.uceprotect.net": 'UCEPROTECT - Level 2 (some false positives)',
        'zen.spamhaus.org': {
            '127.0.0.2': "Spamhaus (Zen) - Spammer",
            '127.0.0.3': "Spamhaus (Zen) - Spammer",
            '127.0.0.4': "Spamhaus (Zen) - Proxies, Trojans, etc.",
            '127.0.0.5': "Spamhaus (Zen) - Proxies, Trojans, etc.",
            '127.0.0.6': "Spamhaus (Zen) - Proxies, Trojans, etc.",
            '127.0.0.7': "Spamhaus (Zen) - Proxies, Trojans, etc.",
            '127.0.0.10': "Spamhaus (Zen) - Potential Spammer",
            '127.0.0.11': "Spamhaus (Zen) - Potential Spammer"
        }
    }

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.results = dict()
        self.baseDomain = target

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return [ 'IP_ADDRESS', 'AFFILIATE_IPADDR' ]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "BLACKLISTED_IPADDR", "BLACKLISTED_AFFILIATE_IPADDR" ]

    # Swap 1.2.3.4 to 4.3.2.1
    def reverseAddr(self, ipaddr):
        return '.'.join(reversed(ipaddr.split('.')))

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data
        parentEvent = event

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        if self.results.has_key(eventData):
            return None

        self.results[eventData] = True

        for domain in self.checks:
            try:
                lookup = self.reverseAddr(eventData) + "." + domain
                sf.debug("Checking Blacklist: " + lookup)
                addrs = socket.gethostbyname_ex(lookup)
                sf.debug("Addresses returned: " + str(addrs))

                text = None
                for addr in addrs:
                    if type(addr) == list:
                        for a in addr:
                            if type(self.checks[domain]) is str:
                                text = self.checks[domain]
                                break
                            else:
                                if str(a) not in self.checks[domain].keys():
                                    sf.debug("Return code not found in list: " + str(a))
                                    continue
                                k = str(a)
                                text = self.checks[domain][k]
                                break

                    else:
                        if type(self.checks[domain]) is str:
                            text = self.checks[domain]
                            break
                        else:
                            if str(addr) not in self.checks.keys():
                                sf.debug("Return code not found in list: " + str(addr))
                                continue

                            k = str(addr)
                            text = self.checks[domain][k]
                            break
                
                if text != None:
                    if eventName == "AFFILIATE_IPADDR":
                        evt = SpiderFootEvent('BLACKLISTED_AFFILIATE_IPADDR',
                            text, self.__name__, parentEvent)
                        self.notifyListeners(evt)
                    else:
                        evt = SpiderFootEvent('BLACKLISTED_IPADDR', 
                            text, self.__name__, parentEvent)
                        self.notifyListeners(evt)
            except BaseException as e:
                sf.debug("Unable to resolve " + eventData + " / " + lookup + ": " + str(e))
 
        return None

# End of sfp_blacklist class

########NEW FILE########
__FILENAME__ = sfp_cookie
#-------------------------------------------------------------------------------
# Name:         sfp_cookie
# Purpose:      SpiderFoot plug-in for extracting cookies from HTTP headers.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     06/04/2014
# Copyright:   (c) Steve Micallef 2014
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import re
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_cookie(SpiderFootPlugin):
    """Cookies:Extract Cookies from HTTP headers."""

    # Default options
    opts = { }

    # Target
    baseDomain = None # calculated from the URL in setup
    results = dict()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = dict()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return ["WEBSERVER_HTTPHEADERS"]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "TARGET_WEB_COOKIE" ]

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data
        parentEvent = event.sourceEvent
        eventSource = event.sourceEvent.data

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)
        if self.results.has_key(eventSource):
            return None
        else:
            self.results[eventSource] = True

        if not sf.urlBaseUrl(eventSource).endswith(self.baseDomain):
            sf.debug("Not collecting cookies from external sites.")
            return None

        if eventData.has_key('set-cookie'):
            evt = SpiderFootEvent("TARGET_WEB_COOKIE", eventData['set-cookie'], 
                self.__name__, parentEvent)
            self.notifyListeners(evt)

# End of sfp_cookie class

########NEW FILE########
__FILENAME__ = sfp_crossref
#-------------------------------------------------------------------------------
# Name:         sfp_crossref
# Purpose:      SpiderFoot plug-in for scanning links identified from the
#               spidering process, and for external links, fetching them to
#               see if those sites link back to the original site, indicating a
#               potential relationship between the external sites.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     06/04/2012
# Copyright:   (c) Steve Micallef 2012
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import re
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_crossref(SpiderFootPlugin):
    """Cross-Reference:Identify whether other domains are associated ('Affiliates') of the target."""

    # Default options
    opts = {
        'forcebase':    True, # Check the base URL for a link back to the seed
                              # domain in order to be considered a valid crossref
        'checkbase':    True, # Only check the base URL for a relationship if
                              # the link provided contains no crossref
        'checkcontent': True  # Submit affiliate content for other modules to
                              # analyze
    }

    # Option descriptions
    optdescs = {
        "forcebase":    "Require the base domain of an external URL for affiliation?",
        "checkbase":    "Check the base domain of a URL for affiliation?",
        "checkcontent": "Submit the affiliate content to other modules for analysis?"
    }

    # Internal results tracking
    results = dict()
    fetched = list()

    # Target
    baseDomain = None

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = dict()
        self.fetched = list()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return ['LINKED_URL_EXTERNAL', 'SIMILARDOMAIN', 'CO_HOSTED_SITE']

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "AFFILIATE", "AFFILIATE_WEB_CONTENT" ]

    # Handle events sent to this module
    # In this module's case, eventData will be the URL or a domain which
    # was found in some content somewhere.
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        # The SIMILARDOMAIN and CO_HOSTED_SITE events supply domains, 
        # not URLs. Assume HTTP.
        if eventName in [ 'SIMILARDOMAIN', 'CO_HOSTED_SITE' ]:
            eventData = 'http://'+ eventData.lower()

        # We are only interested in external sites for the crossref
        if sf.urlBaseUrl(eventData).endswith(self.baseDomain):
            sf.debug("Ignoring " + eventData + " as not external")
            return None

        # If forcebase is set, we don't bother checking the URL from the event,
        # just it's base URL.
        if self.opts['forcebase']:
            url = sf.urlBaseUrl(eventData)
        else:
            url = eventData

        if url in self.fetched:
            sf.debug("Ignoring " + url + " as already tested")
            return

        sf.debug("Testing for affiliation: " + url)
        res = sf.fetchUrl(url, timeout=self.opts['_fetchtimeout'], 
            useragent=self.opts['_useragent'])
        self.fetched.append(url)

        if res['content'] == None:
            sf.debug("Ignoring " + url + " as no data returned")
            return None

        # Search for mentions of our domain in the external site's data
        matches = re.findall("([\.\'\/\"\ ]" + self.baseDomain + "[\.\'\/\"\ ])", 
            res['content'], re.IGNORECASE)

        # If the domain wasn't found in the affiliate, and checkbase is set,
        # fetch the base URL of the affiliate to check for a crossref. Don't bother
        # if forcebase was set, as we would've already checked that anyway.
        if not self.opts['forcebase'] and len(matches) > 0 and self.opts['checkbase']:
            # Check the base url to see if there is an affiliation
            url = sf.urlBaseUrl(eventData)
            res = sf.fetchUrl(url, timeout=self.opts['_fetchtimeout'], 
                useragent=self.opts['_useragent'])
            if res['content'] != None:
                matches = re.findall("([\.\'\/\"\ ]" + self.baseDomain + "[\'\/\"\ ])", 
                    res['content'], re.IGNORECASE)
            else:
                return None

        if len(matches) > 0:
            if self.results.has_key(url):
                return None

            self.results[url] = True
            sf.info("Found affiliate: " + url)
            evt1 = SpiderFootEvent("AFFILIATE", url, self.__name__, event)
            self.notifyListeners(evt1)
            if self.opts['checkcontent']:
                evt2 = SpiderFootEvent("AFFILIATE_WEB_CONTENT", res['content'], self.__name__, evt1)
                self.notifyListeners(evt2)

        return None

# End of sfp_crossref class

########NEW FILE########
__FILENAME__ = sfp_defaced
#-------------------------------------------------------------------------------
# Name:         sfp_defaced
# Purpose:      Checks if a domain or IP appears on the zone-h.org defacement
#               archive.
#
# Author:       steve@binarypool.com
#
# Created:     09/01/2014
# Copyright:   (c) Steve Micallef, 2014
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import time
import re
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_defaced(SpiderFootPlugin):
    """Defacement Check:Check if an IP or domain appears on the zone-h.org defacement archive."""

    # Default options
    opts = { 
        'daysback': 30,
        'checkcohosts': True,
        'checkaffiliates': True
    }

    # Option descriptions
    optdescs = {
        'daysback': "Ignore defacements older than this many days.",
        'checkcohosts': "Check co-hosted sites?",   
        'checkaffiliates': "Check affiliates?"
    }

    # Be sure to completely clear any class variables in setup()
    # or you run the risk of data persisting between scan runs.

    # Target
    baseDomain = None # calculated from the URL in setup
    results = list()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = list()

        # Clear / reset any other class member variables here
        # or you risk them persisting between threads.

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    # * = be notified about all events.
    def watchedEvents(self):
        return ["IP_ADDRESS", "SUBDOMAIN",
            "AFFILIATE_DOMAIN", "AFFILIATE_IPADDR",
            "CO_HOSTED_SITE" ]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "DEFACED", "DEFACED_IPADDR", "DEFACED_AFFILIATE", 
            "DEFACED_COHOST", "DEFACED_AFFILIATE_IPADDR" ]

    def lookupItem(self, target, typeId):
        found = False
        curDate = time.strftime("%Y%m%d")
        url = "http://www.zone-h.org/archive/" + typeId + "=" + target
        res = sf.fetchUrl(url, useragent=self.opts['_useragent'])
        if res['content'] == None:
            sf.debug("Unable to fetch data from Zone-H for " + target + "(" + typeId + ")")
            return None

        if "<img id='cryptogram' src='/captcha.py'>" in res['content']:
            sf.error("CAPTCHA returned from zone-h.org.", False)
            return None

        rx = "<td>(\d+/\d+/\d+)</td>"
        grps = re.findall(rx, res['content'], re.IGNORECASE|re.DOTALL)
        for m in grps:
            sf.debug("Found defaced site: " + target + "(" + typeId + ")")
            found = True
            # Zone-H returns in YYYY/MM/DD
            date = m.replace('/', '')
            if int(date) < int(curDate)-30:
                sf.debug("Defaced site found but too old: " + date)
                found = False
                continue

            if found:
                return url

        return None

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        if eventData in self.results:
            sf.debug("Skipping " + eventData + ", already checked.")
            return None
        else:
            self.results.append(eventData)

        if eventName == 'CO_HOSTED_SITE' and not self.opts['checkcohosts']:
            return None
        if eventName == 'AFFILIATE_DOMAIN' or eventName == 'AFFILIATE_IPADDR' \
            and not self.opts['checkaffiliates']:
            return None

        evtType = 'DEFACED'
        typeId = 'domain'

        if eventName == 'IP_ADDRESS':
            evtType = 'DEFACED_IPADDR'
            typeId = 'ip'

        if eventName == 'CO_HOSTED_SITE':
            evtType = 'DEFACED_COHOST'

        if eventName == 'AFFILIATE_DOMAIN':
            evtType = 'DEFACED_AFFILIATE'

        if eventName == 'AFFILIATE_IPADDR':
            evtType = 'DEFACED_AFFILIATE_IPADDR'
            typeId = 'ip'

        url = self.lookupItem(eventData, typeId)
        if self.checkForStop():
            return None

        # Notify other modules of what you've found
        if url != None:
            text = eventData + "\n" + url
            evt = SpiderFootEvent(evtType, text, self.__name__, event)
            self.notifyListeners(evt)

        return None

    def start(self):
        if self.checkForStop():
            return None

        url = self.lookupItem(self.baseDomain, 'domain')
        if url != None:
            text = self.baseDomain + "\n" + url
            evt = SpiderFootEvent('DEFACED', text, self.__name__)
            self.notifyListeners(evt)

# End of sfp_malcheck class

########NEW FILE########
__FILENAME__ = sfp_dns
#-------------------------------------------------------------------------------
# Name:         sfp_dns
# Purpose:      SpiderFoot plug-in for gathering IP addresses from sub-domains
#        and hostnames identified, and optionally affiliates.
#        Can also identify affiliates and other sub-domains based on
#        reverse-looking up the IP address identified.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     16/09/2012
# Copyright:   (c) Steve Micallef 2012
# Licence:     GPL
#-------------------------------------------------------------------------------

import socket
import sys
import re
import random
import dns
from netaddr import IPAddress, IPNetwork
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_dns(SpiderFootPlugin):
    """DNS:Performs a number of DNS checks to obtain Sub-domains/Hostnames, IP Addresses and Affiliates."""

    # Default options
    opts = {
        'reverselookup':    True,    # Reverse-resolve IPs to names for
                                    # more clues.
        'subnetlookup': True,
        'netblocklookup': True,
        'maxnetblock': 24,
        'lookaside': True,
        'lookasidecount': 10,
        'onlyactive': True,
        "skipcommononwildcard": True,
        "commonsubs":   [ "www", "web", "ns", "mail", "dns", "mx", "gw", "proxy",
                          "ssl", "fw", "gateway", "firewall", "www1", "www2",
                          "ns0", "ns1", "ns2", "dns0", "dns1", "dns2", "mx1", "mx2"
                         ] # Common sub-domains to try.

    }

    # Option descriptions
    optdescs = {
        'skipcommononwildcard': "If wildcard DNS is detected, only attempt to look up the first common sub-domain from the common sub-domain list.",
        'reverselookup': "Obtain new URLs and possible affiliates based on reverse-resolved IPs?",
        'subnetlookup': "If reverse-resolving is enabled, look up all IPs on the same subnet for possible hosts on the same target domain?",
        'netblocklookup': "If reverse-resolving is enabled, look up all IPs on owned netblocks for possible hosts on the same target domain?",
        'maxnetblock': "Maximum netblock/subnet size to look up all IPs within (CIDR value, 24 = /24, 16 = /16, etc.)",
        'onlyactive': "Only report sub-domains/hostnames that resolve to an IP.",
        'lookaside': "For each IP discovered, try and reverse look-up IPs 'next to' that IP.",
        'lookasidecount': "If look-aside is enabled, the number of IPs on each 'side' of the IP to look up",
        "commonsubs":   "Common sub-domains to try. Prefix with an '@' to iterate through a file containing sub-domains to try (one per line), e.g. @C:\subdomains.txt or @/home/bob/subdomains.txt. Or supply a URL to load the list from there."
    }

    # Target
    baseDomain = None
    results = dict()
    subresults = dict()
    resolveCache = dict()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.results = dict()
        self.subresults = dict()
        self.resolveCache = dict()
        self.baseDomain = target

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        arr = ['RAW_DNS_RECORDS', 'SEARCH_ENGINE_WEB_CONTENT', 'RAW_RIR_DATA',
            'TARGET_WEB_CONTENT', 'LINKED_URL_INTERNAL', 'SUBDOMAIN' ]
        if self.opts['reverselookup']:
            arr.extend(['IP_ADDRESS', 'NETBLOCK', 'IP_SUBNET'])
        return arr

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "IP_ADDRESS", "SUBDOMAIN", "PROVIDER_MAIL", 
            "PROVIDER_DNS", "AFFILIATE", "RAW_DNS_RECORDS" ]

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data
        addrs = None
        parentEvent = event

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        if self.subresults.has_key(eventData):
            return None

        self.subresults[eventData] = True

        if eventName in [ "SEARCH_ENGINE_WEB_CONTENT", "TARGET_WEB_CONTENT",
            "LINKED_URL_INTERNAL", "RAW_RIR_DATA", "RAW_DNS_RECORDS" ]:
            # If we've received a link or some raw data, extract potential sub-domains
            # from the data for resolving later.
            matches = re.findall("([a-zA-Z0-9\-\.]+\." + self.baseDomain + ")", eventData,
                re.IGNORECASE)

            if matches != None:
                for match in matches:
                    if match.lower().startswith("2f"):
                        continue

                    self.processHost(match, parentEvent)

            # Nothing left to do with internal links and raw data
            return None

        if eventName in [ 'NETBLOCK', 'IP_SUBNET' ]:
            if eventName == 'NETBLOCK' and not self.opts['netblocklookup']:
                return None
            if eventName == 'IP_SUBNET' and not self.opts['subnetlookup']:
                return None

            if IPNetwork(eventData).prefixlen < self.opts['maxnetblock']:
                sf.debug("Network size bigger than permitted: " + \
                    str(IPNetwork(eventData).prefixlen) + " > " + \
                    str(self.opts['maxnetblock']))
                return None

            sf.debug("Looking up IPs in " + eventData)
            for ip in IPNetwork(eventData):
                if self.checkForStop():
                    return None
                ipaddr = str(ip)

                if self.results.has_key(ipaddr):
                    continue
                else:
                    self.results[ipaddr] = True

                try:
                    addrs = socket.gethostbyaddr(ipaddr)
                    sf.debug("Found a reversed hostname from " + ipaddr + \
                        " (" + str(addrs) + ")")
                    for addr in addrs:
                        if type(addr) == list:
                            for host in addr:
                                # Don't report on anything on the same subnet if
                                # if doesn't resolve to something on the target
                                if not host.endswith(self.baseDomain) and \
                                    eventName == 'IP_SUBNET':
                                    continue
                                self.processHost(host, parentEvent)
                        else:
                            if not addr.endswith(self.baseDomain) and \
                                eventName == 'IP_SUBNET':
                                continue
                            self.processHost(addr, parentEvent)
                except Exception as e:
                    #sf.debug("Exception encountered: " + str(e))
                    continue

            return None

        # Handling SUBDOMAIN and IP_ADDRESS events..

        # Don't look up stuff twice
        if self.results.has_key(eventData):
            sf.debug("Skipping " + eventData + " as already resolved.")
            return None
        else:
            self.results[eventData] = True

        try:
            if eventName != 'IP_ADDRESS':
                if '://' in eventData:
                    addrs = self.resolveHost(sf.urlFQDN(eventData))
                else:
                    addrs = self.resolveHost(eventData)
                if addrs == None:
                    return None
            else:
                addrs = socket.gethostbyaddr(eventData)
        except BaseException as e:
            sf.info("Unable to resolve " + eventData + " (" + str(e) + ")")
            return None

        for addr in addrs:
            if type(addr) == list:
                for host in addr:
                    self.processHost(host, parentEvent)
            else:
                self.processHost(addr, parentEvent)

        # Try to reverse-resolve
        if self.opts['lookaside'] and eventName == 'IP_ADDRESS':
            ip = IPAddress(eventData)
            minip = IPAddress(int(ip) - self.opts['lookasidecount'])
            maxip = IPAddress(int(ip) + self.opts['lookasidecount'])
            sf.debug("Lookaside max: " + str(maxip) + ", min: " + str(minip))
            s = int(minip)
            c = int(maxip)
            while s <= c:
                sip = str(IPAddress(s))
                if self.checkForStop():
                    return None

                if self.results.has_key(sip):
                    s = s + 1
                    continue

                try:
                    addrs = socket.gethostbyaddr(sip)
                    for addr in addrs:
                        if type(addr) == list:
                            for host in addr:
                                if host.endswith(self.baseDomain):
                                    self.processHost(host, parentEvent)
                        else:
                            if addr.endswith(self.baseDomain):
                                self.processHost(addr, parentEvent)
                except BaseException as e:
                    sf.debug("Look-aside lookup failed: " + str(e))
                s = s + 1
            
        return None

    # Resolve a host
    def resolveHost(self, hostname):
        if self.resolveCache.has_key(hostname):
            sf.debug("Returning cached result for " + hostname)
            return self.resolveCache[hostname]

        try:
            ret = socket.gethostbyname_ex(hostname)
            self.resolveCache[hostname] = ret
            return ret
        except BaseException as e:
            sf.info("Unable to resolve " + hostname + " (" + str(e) + ")")
            return None

    def processHost(self, host, parentEvent=None):
        sf.debug("Found host: " + host)
        # If the returned hostname is on a different
        # domain to baseDomain, flag it as an affiliate
        if not host.lower().endswith(self.baseDomain):
            if sf.validIP(host):
                htype = "IP_ADDRESS"
            else:
                htype = "AFFILIATE"
        else:
            htype = "SUBDOMAIN"
                
        if parentEvent != None:
            # Don't report back the same thing that was provided
            if htype == parentEvent.eventType and host == parentEvent.data:
                return

        if htype == "SUBDOMAIN" and self.opts['onlyactive']:
            if self.resolveHost(host) == None:
                return None

        evt = SpiderFootEvent(htype, host, self.__name__, parentEvent)
        self.notifyListeners(evt)

    def start(self):
        sf.debug("Gathering DNS records..")
        # Process the raw data alone
        recdata = dict()
        recs = {
            'MX': ['\S+ \d+ IN MX \d+ (\S+)\.', 'PROVIDER_MAIL'],
            'NS': ['\S+ \d+ IN NS (\S+)\.', 'PROVIDER_DNS']
        }

        for rec in recs.keys():
            try:
                req = dns.message.make_query(self.baseDomain, dns.rdatatype.from_text(rec))
    
                if self.opts['_dnsserver'] != "":
                    n = self.opts['_dnsserver']
                else:
                    ns = dns.resolver.get_default_resolver()
                    n = ns.nameservers[0]
            
                res = dns.query.udp(req, n)
                for x in res.answer:
                    for rx in recs.keys():
                        sf.debug("Checking " + str(x) + " + against " + recs[rx][0])
                        grps = re.findall(recs[rx][0], str(x), re.IGNORECASE|re.DOTALL)
                        if len(grps) > 0:
                            for m in grps:
                                sf.debug("Matched: " +  m)
                                strdata = unicode(m, 'utf-8', errors='replace')
                                evt = SpiderFootEvent(recs[rx][1], strdata, 
                                    self.__name__)
                                self.notifyListeners(evt)
                                if not strdata.endswith(self.baseDomain):
                                    evt = SpiderFootEvent("AFFILIATE", strdata, 
                                        self.__name__)
                                    self.notifyListeners(evt)
                        else:
                                strdata = unicode(str(x), 'utf-8', errors='replace')
                                evt = SpiderFootEvent("RAW_DNS_RECORDS", strdata, 
                                    self.__name__) 
                                self.notifyListeners(evt)
            except BaseException as e:
                sf.error("Failed to obtain DNS response: " + str(e), False)

        sublist = self.opts['commonsubs']

        # Also look up the base target itself
        sublist.append('')
        # User may have supplied a file or URL containing the subdomains
        if self.opts['commonsubs'][0].startswith("http://") or \
            self.opts['commonsubs'][0].startswith("https://") or \
            self.opts['commonsubs'][0].startswith("@"):
            sublist = sf.optValueToData(self.opts['commonsubs'][0])
            
        sf.debug("Iterating through possible sub-domains [" + str(sublist) + "]")
        count = 0
        wildcard = sf.checkDnsWildcard(self.baseDomain)
        # Try resolving common names
        for sub in sublist:
            if wildcard and self.opts['skipcommononwildcard'] and count > 0:
                sf.debug("Wildcard DNS detected, skipping iterating through remaining hosts.")
                return None
                
            if self.checkForStop():
                return None

            count += 1
            if sub != "":
                name = sub + "." + self.baseDomain
            else:
                name = self.baseDomain
            # Don't look up stuff twice
            if self.results.has_key(name):
                sf.debug("Skipping " + name + " as already resolved.")
                continue
            else:
                self.results[name] = True

            addrs = self.resolveHost(name)
            if addrs != None:
                self.processHost(name)
                for addr in addrs:
                    if type(addr) == list:
                        for host in addr:
                            if host not in self.results.keys():
                                self.processHost(host)
                                self.results[host] = True
                    else:
                        if addr not in self.results.keys():
                            self.processHost(addr)
                            self.results[addr] = True

# End of sfp_dns class

########NEW FILE########
__FILENAME__ = sfp_email
#-------------------------------------------------------------------------------
# Name:         sfp_email
# Purpose:      SpiderFoot plug-in for scanning retreived content by other
#               modules (such as sfp_spider) and identifying e-mail addresses
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     06/04/2012
# Copyright:   (c) Steve Micallef 2012
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import re
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_email(SpiderFootPlugin):
    """E-Mail:Identify e-mail addresses in any obtained data."""

    # Default options
    opts = {
        # options specific to this module
        'includesubdomains':   True, # Include e-mail addresses on sub-domains of
                                    # the target domain
        'includeexternal':  False # Include e-mail addrs on external domains
    }

    # Option descriptions
    optdescs = {
        'includesubdomains': "Report e-mail addresses on a sub-domain of the target base domain-name?",
        'includeexternal': "Report e-mail addresses not on the target base domain-name?"
    }

    # Target
    baseDomain = None
    results = dict()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = dict()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return ["*"]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "EMAILADDR" ]

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data
        parentEvent = event.sourceEvent

        if eventName == "EMAILADDR":
            return None

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        if type(eventData) not in [ str, unicode ]:
            sf.debug("Unhandled type to find e-mails: " + str(type(eventData)))
            return None

        matches = re.findall("([a-zA-Z\.0-9_\-]+@[a-zA-Z\.0-9_\-]+)", eventData)
        for match in matches:
            sf.debug("Found possible email: " + match)

            if len(match) < 4:
                sf.debug("Likely invalid address.")
                continue

            if self.baseDomain not in match.lower():
                sf.debug("E-mail (or something) from somewhere else..")
                continue

            self.results[match] = True

            # Include e-mail addresses on sub-domains within the domain?
            if not self.opts['includesubdomains']:
                if not match.lower().endswith('@' + self.baseDomain):
                    sf.debug("Ignoring e-mail address on a sub-domain: " + match)
                    continue

            # Include external domains as e-mail addresses?
            if not self.opts['includeexternal']:
                if not match.lower().endswith(self.baseDomain):
                    sf.debug("Ignoring e-mail address on an external domain" + match)
                    continue

            sf.info("Found e-mail address: " + match)
            evt = SpiderFootEvent("EMAILADDR", match, self.__name__, parentEvent)
            self.notifyListeners(evt)

        return None

# End of sfp_email class

########NEW FILE########
__FILENAME__ = sfp_filemeta
#-------------------------------------------------------------------------------
# Name:         sfp_filemeta
# Purpose:      From Spidering and from searching search engines, extracts file
#               meta data from files matching certain file extensions.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     25/04/2014
# Copyright:   (c) Steve Micallef 2014
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import random
import re
import time
import urllib
import mimetypes
import metapdf
import pyPdf
import openxmllib
from StringIO import StringIO
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_filemeta(SpiderFootPlugin):
    """File Metadata:Extracts meta data from certain file types."""

    # Default options
    opts = {
        'fileexts':     [ "docx", "pptx", 'xlsx', 'pdf' ],
        'timeout':      300
    }

    # Option descriptions
    optdescs = {
        'fileexts': "File extensions of files you want to analyze the meta data of (only PDF, DOCX, XLSX and PPTX are supported.)",
        'timeout':  "Download timeout for files, in seconds."
    }

    # Target
    baseDomain = None
    results = list()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = list()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return [ "LINKED_URL_INTERNAL", "INTERESTING_FILE" ]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "RAW_FILE_META_DATA" ]

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        if eventData in self.results:
            return None
        else:
            self.results.append(eventData)

        for fileExt in self.opts['fileexts']:
            if self.checkForStop():
                return None

            if "." + fileExt.lower() in eventData.lower():
                # Fetch the file, allow much more time given that these files are
                # typically large.
                ret = sf.fetchUrl(eventData, timeout=self.opts['timeout'], 
                    useragent=self.opts['_useragent'], dontMangle=True)
                if ret['content'] == None:
                    sf.error("Unable to fetch file for meta analysis: " + \
                        eventData, False)
                    return None

                if len(ret['content']) < 1024:
                    sf.error("Strange content encountered, size of " + \
                        len(res['content']), False)

                meta = None
                # Based on the file extension, handle it
                if fileExt.lower() == "pdf":
                    try:
                        data = StringIO(ret['content'])
                        meta = str(metapdf.MetaPdfReader().read_metadata(data))
                        sf.debug("Obtained meta data from " + eventData)
                    except BaseException as e:
                        sf.error("Unable to parse meta data from: " + \
                            eventData + "(" + str(e) + ")", False)
                        return None

                if fileExt.lower() in [ "pptx", "docx", "xlsx" ]:
                    try:
                        mtype = mimetypes.guess_type(eventData)[0]
                        doc = openxmllib.openXmlDocument(data=ret['content'], mime_type=mtype)
                        sf.debug("Office type: " + doc.mimeType)
                        meta = str(doc.allProperties)
                    except ValueError as e:
                        sf.error("Unable to parse meta data from: " + \
                            eventData + "(" + str(e) + ")", False)
                    except lxml.etree.XMLSyntaxError as e:
                        sf.error("Unable to parse XML within: " + \
                            eventData + "(" + str(e) + ")", False)

                if meta != None:
                    evt = SpiderFootEvent("RAW_FILE_META_DATA", meta,
                        self.__name__, event)
                    self.notifyListeners(evt)

                
# End of sfp_filemeta class

########NEW FILE########
__FILENAME__ = sfp_geoip
#-------------------------------------------------------------------------------
# Name:         sfp_geoip
# Purpose:      SpiderFoot plug-in to identify the Geo-location of IP addresses
#               identified by other modules.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     18/02/2013
# Copyright:   (c) Steve Micallef 2013
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import re
import json
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_geoip(SpiderFootPlugin):
    """GeoIP:Identifies the physical location of IP addresses identified."""

    # Default options
    opts = { }

    # Target
    baseDomain = None
    results = dict()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = dict()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return ['IP_ADDRESS']

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "GEOINFO" ]

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        # Don't look up stuff twice
        if self.results.has_key(eventData):
            sf.debug("Skipping " + eventData + " as already mapped.")
            return None
        else:
            self.results[eventData] = True

        res = sf.fetchUrl("http://freegeoip.net/json/" + eventData,
            timeout=self.opts['_fetchtimeout'], useragent=self.opts['_useragent'])
        if res['content'] == None:
            sf.info("No GeoIP info found for " + eventData)
        try:
            hostip = json.loads(res['content'])
        except Exception as e:
            sf.debug("Error processing JSON response.")
            return None

        sf.info("Found GeoIP for " + eventData + ": " + hostip['country_name'])
        countrycity = hostip['country_name']

        evt = SpiderFootEvent("GEOINFO", countrycity, self.__name__, event)
        self.notifyListeners(evt)

        return None

# End of sfp_geoip class

########NEW FILE########
__FILENAME__ = sfp_googlesearch
#-------------------------------------------------------------------------------
# Name:         sfp_googlesearch
# Purpose:      Searches Google for content related to the domain in question.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     07/05/2012
# Copyright:   (c) Steve Micallef 2012
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import random
import re
import time
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_googlesearch(SpiderFootPlugin):
    """Google:Some light Google scraping to identify sub-domains and links."""

    # Default options
    opts = {
        'fetchlinks':   True,   # Should we fetch links on the base domain?
        'pages':        20      # Number of google results pages to iterate
    }

    # Option descriptions
    optdescs = {
        'fetchlinks': "Fetch links found on the target domain-name?",
        'pages':    "Number of Google results pages to iterate through."
    }

    # Target
    baseDomain = None
    results = list()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = list()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return None

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "LINKED_URL_INTERNAL", "SEARCH_ENGINE_WEB_CONTENT" ]

    def start(self):
        # Sites hosted on the domain
        pages = sf.googleIterate("site:" + self.baseDomain, 
            dict(limit=self.opts['pages'], useragent=self.opts['_useragent'],
            timeout=self.opts['_fetchtimeout']))
        if pages == None:
            sf.info("No results returned from Google.")
            return None

        for page in pages.keys():
            if page in self.results:
                continue
            else:
                self.results.append(page)

            # Check if we've been asked to stop
            if self.checkForStop():
                return None

            # Submit the google results for analysis
            evt = SpiderFootEvent("SEARCH_ENGINE_WEB_CONTENT", pages[page], self.__name__)
            self.notifyListeners(evt)

            # We can optionally fetch links to our domain found in the search
            # results. These may not have been identified through spidering.
            if self.opts['fetchlinks']:
                links = sf.parseLinks(page, pages[page], self.baseDomain)
                if len(links) == 0:
                    continue

                for link in links:
                    if link in self.results:
                        continue
                    else:
                        self.results.append(link)
                    sf.debug("Found a link: " + link)
                    if sf.urlBaseUrl(link).endswith(self.baseDomain):
                        if self.checkForStop():
                            return None

                        evt = SpiderFootEvent("LINKED_URL_INTERNAL", link, self.__name__)
                        self.notifyListeners(evt)

# End of sfp_googlesearch class

########NEW FILE########
__FILENAME__ = sfp_honeypot
#-------------------------------------------------------------------------------
# Name:         sfp_honeypot
# Purpose:      SpiderFoot plug-in for looking up whether IPs appear in the
#               projecthoneypot.org database.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     16/04/2014
# Copyright:   (c) Steve Micallef 2014
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import re
import socket
import random
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_honeypot(SpiderFootPlugin):
    """Honeypot Checker: Query the projecthoneypot.org database for entries."""

    # Default options
    opts = {
        'apikey': "",
        'searchengine': False,
        'threatscore': 0,
        'timelimit': 30
    }

    # Option descriptions
    optdescs = {
        'apikey': "The API key you obtained from projecthoneypot.org",
        'searchengine': "Include entries considered search engines?",
        'threatscore': "Threat score minimum, 0 being everything and 255 being only the most serious.",
        'timelimit': "Maximum days old an entry can be. 255 is the maximum, 0 means you'll get nothing."
    }

    # Target
    baseDomain = None
    results = dict()

    # Status codes according to:
    # http://www.projecthoneypot.org/httpbl_api.php
    statuses = {
        "0": "Search Engine",
        "1": "Suspicious",
        "2": "Harvester",
        "3": "Suspicious & Harvester",
        "4": "Comment Spammer",
        "5": "Suspicious & Comment Spammer",
        "6": "Harvester & Comment Spammer",
        "7": "Suspicious & Harvester & Comment Spammer",
        "8": "Unknown (8)",
        "9": "Unknown (9)",
        "10": "Unknown (10)"
    }

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.results = dict()
        self.baseDomain = target

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return [ 'IP_ADDRESS', 'AFFILIATE_IPADDR' ]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "BLACKLISTED_IPADDR", "BLACKLISTED_AFFILIATE_IPADDR" ]

    # Swap 1.2.3.4 to 4.3.2.1
    def reverseAddr(self, ipaddr):
        return '.'.join(reversed(ipaddr.split('.')))

    # Returns text about the IP status returned from DNS
    def reportIP(self, addr):
        bits = addr.split(".")
        if int(bits[1]) > self.opts['timelimit']:
            return None

        if int(bits[2]) < self.opts['threatscore']:
            return None

        if int(bits[3]) == 0 and self.opts['searchengine']:
            return None

        text = "Honeypotproject: " + self.statuses[bits[3]] + \
            "\nLast Activity: " + bits[1] + " days ago" + \
            "\nThreat Level: " + bits[2]
        return text

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data
        parentEvent = event

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        if self.opts['apikey'] == "":
            sf.error("You enabled sfp_honeypot but did not set an API key!", False)
            return None

        if self.results.has_key(eventData):
            return None
        self.results[eventData] = True

        try:
            lookup = self.opts['apikey'] + "." + \
                self.reverseAddr(eventData) + ".dnsbl.httpbl.org"

            sf.debug("Checking Honeypot: " + lookup)
            addrs = socket.gethostbyname_ex(lookup)
            sf.debug("Addresses returned: " + str(addrs))

            text = None
            for addr in addrs:
                if type(addr) == list:
                    for a in addr:
                        text = self.reportIP(a)
                        if text == None:
                            continue
                        else:
                            break
                else:
                    text = self.reportIP(addr)
                    if text == None:
                        continue
                    else:
                        break

            if text != None:
                if eventName == "AFFILIATE_IPADDR":
                    evt = SpiderFootEvent('BLACKLISTED_AFFILIATE_IPADDR',
                        text, self.__name__, parentEvent)
                    self.notifyListeners(evt)
                else:
                    evt = SpiderFootEvent('BLACKLISTED_IPADDR', 
                        text, self.__name__, parentEvent)
                    self.notifyListeners(evt)
        except BaseException as e:
            sf.debug("Unable to resolve " + eventData + " / " + lookup + ": " + str(e))
 
# End of sfp_honeypot class

########NEW FILE########
__FILENAME__ = sfp_intfiles
#-------------------------------------------------------------------------------
# Name:         sfp_intfiles
# Purpose:      From Spidering and from searching search engines, identifies
#               files of potential interest.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     06/04/2014
# Copyright:   (c) Steve Micallef 2014
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import random
import re
import time
import urllib
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_intfiles(SpiderFootPlugin):
    """Interesting Files:Identifies potential files of interest, e.g. office documents."""

    # Default options
    opts = {
        'pages':        20,      # Number of search results pages to iterate
        'fileexts':     [ "doc", "docx", "ppt", "pptx", "pdf", 'xls', 'xlsx' ],
        'usesearch':    True,
        'searchengine': "yahoo"
    }

    # Option descriptions
    optdescs = {
        'pages':    "Number of search engine results pages to iterate through if using one.",
        'fileexts': "File extensions of files you consider interesting.",
        'usesearch': "Use search engines to quickly find files. If false, only spidering will be used.",
        'searchengine': "If using a search engine, which one? google, yahoo or bing."
    }

    # Target
    baseDomain = None
    results = list()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = list()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return [ "LINKED_URL_INTERNAL" ]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "SEARCH_ENGINE_WEB_CONTENT", "INTERESTING_FILE" ]

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        for fileExt in self.opts['fileexts']:
            if "." + fileExt.lower() in eventData.lower():
                if eventData in self.results:
                    continue
                else:
                    self.results.append(eventData)
                evt = SpiderFootEvent("INTERESTING_FILE", eventData, self.__name__)
                self.notifyListeners(evt)

    def yahooCleaner(self, string):
        return " url=\"" + urllib.unquote(string.group(1)) + "\" "

    def start(self):
        if not self.opts['usesearch']:
            return None

        for fileExt in self.opts['fileexts']:
            # Sites hosted on the domain
            if self.opts['searchengine'].lower() == "google":
                pages = sf.googleIterate("site:" + self.baseDomain + "+" + \
                    "%2Bext:" + fileExt, dict(limit=self.opts['pages'],
                    useragent=self.opts['_useragent'], 
                    timeout=self.opts['_fetchtimeout']))

            if self.opts['searchengine'].lower() == "bing":
                pages = sf.bingIterate("site:" + self.baseDomain + "+" + \
                    "%2Bext:" + fileExt, dict(limit=self.opts['pages'],
                    useragent=self.opts['_useragent'], 
                    timeout=self.opts['_fetchtimeout']))

            if self.opts['searchengine'].lower() == "yahoo":
                pages = sf.yahooIterate("site:" + self.baseDomain + "+" + \
                    "%2Bext:" + fileExt, dict(limit=self.opts['pages'],
                    useragent=self.opts['_useragent'], 
                    timeout=self.opts['_fetchtimeout']))

            if pages == None:
                sf.info("No results returned from " + self.opts['searchengine'] + \
                    " for " + fileExt + " files.")
                continue

            for page in pages.keys():
                if page in self.results:
                    continue
                else:
                    self.results.append(page)

                # Check if we've been asked to stop
                if self.checkForStop():
                    return None

                # Submit the gresults for analysis
                evt = SpiderFootEvent("SEARCH_ENGINE_WEB_CONTENT", pages[page], self.__name__)
                self.notifyListeners(evt)

                if self.opts['searchengine'].lower() == "yahoo":
                    res = re.sub("RU=(.[^\/]+)\/RK=", self.yahooCleaner,
                        pages[page], 0)
                else:
                    res = pages[page]

                links = sf.parseLinks(page, res, self.baseDomain)
                if len(links) == 0:
                    continue

                for link in links:
                    if link in self.results:
                        continue
                    else:
                        self.results.append(link)

                    if sf.urlBaseUrl(link).endswith(self.baseDomain) and \
                        "." + fileExt.lower() in link.lower():
                        sf.info("Found an interesting file: " + link)
                        evt = SpiderFootEvent("INTERESTING_FILE", link, self.__name__)
                        self.notifyListeners(evt)

# End of sfp_intfiles class

########NEW FILE########
__FILENAME__ = sfp_ir
#-------------------------------------------------------------------------------
# Name:         sfp_ir
# Purpose:      Queries Internet registryes like RIPE (incl. ARIN) to get 
#               netblocks and other bits of info.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     8/12/2013
# Copyright:   (c) Steve Micallef 2013
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import re
import json
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_ir(SpiderFootPlugin):
    """Internet Registries:Queries Internet Registries to identify netblocks and other info."""

    # Default options
    opts = { }

    # Target
    baseDomain = None
    results = dict()
    currentEventSrc = None
    memCache = dict()
    nbreported = dict()
    keyword = None

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = dict()
        self.memCache = dict()
        self.currentEventSrc = None
        self.nbreported = dict()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

        self.keyword = sf.domainKeyword(self.baseDomain, 
            self.opts['_internettlds']).lower()

    # What events is this module interested in for input
    def watchedEvents(self):
        return ['IP_ADDRESS']

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "NETBLOCK", "RAW_RIR_DATA", "BGP_AS", "PROVIDER_INTERNET" ]

    # Fetch content and notify of the raw data
    def fetchRir(self, url):
        if self.memCache.has_key(url):
            res = self.memCache[url]
        else:
            res = sf.fetchUrl(url, timeout=self.opts['_fetchtimeout'], 
                useragent=self.opts['_useragent'])
            if res['content'] != None:
                self.memCache[url] = res
                evt = SpiderFootEvent("RAW_RIR_DATA", res['content'], self.__name__, 
                    self.currentEventSrc)
                self.notifyListeners(evt)
        return res

    # Get the netblock the IP resides in
    def ipNetblock(self, ipaddr):
        prefix = None

        res = self.fetchRir("https://stat.ripe.net/data/network-info/data.json?resource=" + ipaddr)
        if res['content'] == None:
            sf.debug("No Netblock info found/available for " + ipaddr + " at RIPE.")
            return None

        try:
            j = json.loads(res['content'])
        except Exception as e:
            sf.debug("Error processing JSON response.")
            return None

        prefix = j["data"]["prefix"]
        if prefix == None:
            sf.debug("Could not identify network prefix.")
            return None

        return prefix

    # Get the AS owning the netblock
    def netblockAs(self, prefix):
        asn = None

        res = self.fetchRir("https://stat.ripe.net/data/whois/data.json?resource=" + prefix)
        if res['content'] == None:
            sf.debug("No AS info found/available for prefix: " + prefix + " at RIPE.")
            return None

        try:
            j = json.loads(res['content'])
            if len(j["data"]["irr_records"]) > 0:
                data = j["data"]["irr_records"][0]
            else:
                data = j["data"]["records"][0]
        except Exception as e:
            sf.debug("Error processing JSON response.")
            return None

        for rec in data:
            if rec["key"] == "origin":
                asn = rec["value"]
                break

        return str(asn)

    # Owner information about an AS
    def asOwnerInfo(self, asn):
        ownerinfo = dict()

        res = self.fetchRir("https://stat.ripe.net/data/whois/data.json?resource=" + asn)
        if res['content'] == None:
            sf.debug("No info found/available for ASN: " + asn + " at RIPE.")
            return None

        try:
            j = json.loads(res['content'])
            data = j["data"]["records"]
        except Exception as e:
            sf.debug("Error processing JSON response.")
            return None

        for rec in data:
            for d in rec:
                if d["key"].lower().startswith("org") or \
                    d["key"].lower().startswith("as") or \
                    d["key"].lower().startswith("descr") and \
                    d["value"].lower() not in [ "null", "none", "none specified" ]:
                    if ownerinfo.has_key(d["key"]):
                        ownerinfo[d["key"]].append(d["value"])
                    else:
                        ownerinfo[d["key"]] = [ d["value"] ]

        sf.debug("Returning ownerinfo: " + str(ownerinfo))
        return ownerinfo

    # Netblocks owned by an AS
    def asNetblocks(self, asn):
        netblocks = list()

        res = self.fetchRir("https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS" + asn)
        if res['content'] == None:
            sf.debug("No netblocks info found/available for AS" + asn + " at RIPE.")
            return None

        try:
            j = json.loads(res['content'])
            data = j["data"]["prefixes"]
        except Exception as e:
            sf.debug("Error processing JSON response.")
            return None

        for rec in data:
            netblocks.append(rec["prefix"])
            sf.info("Additional netblock found from same AS: " + rec["prefix"])

        return netblocks

    # Neighbours to an AS
    def asNeighbours(self, asn):
        neighbours = list()

        res = self.fetchRir("https://stat.ripe.net/data/asn-neighbours/data.json?resource=AS" + asn)
        if res['content'] == None:
            sf.debug("No neighbour info found/available for AS" + asn + " at RIPE.")
            return None

        try:
            j = json.loads(res['content'])
            data = j["data"]["neighbours"]
        except Exception as e:
            sf.debug("Error processing JSON response.")
            return None

        for rec in data:
            neighbours.append(str(rec['asn']))

        return neighbours

    # Determine whether there is a textual link between the target 
    # and the string supplied.
    def findName(self, string):
        # Simplest check to perform..
        if self.baseDomain in string:
            return True

        # Slightly more complex..
        rx = [ 
            '^{0}[-_/\'\"\\\.,\?\! ]',
            '[-_/\'\"\\\.,\?\! ]{0}$',
            '[-_/\'\"\\\.,\?\! ]{0}[-_/\'\"\\\.,\?\! ]'
        ]

        # Mess with the keyword as a last resort..
        keywordList = list()
        # Create versions of the keyword, esp. if hyphens are involved.
        keywordList.append(self.keyword)
        keywordList.append(self.keyword.replace('-', ' '))
        keywordList.append(self.keyword.replace('-', '_'))
        keywordList.append(self.keyword.replace('-', ''))
        for kw in keywordList:
            for r in rx:
                if re.match(r.format(kw), string, re.IGNORECASE) != None:
                    return True
        
        return False

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data
        self.currentEventSrc = event

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        # Don't look up stuff twice
        if self.results.has_key(eventData):
            sf.debug("Skipping " + eventData + " as already mapped.")
            return None
        else:
            self.results[eventData] = True

        prefix = self.ipNetblock(eventData)
        if prefix == None:
            sf.debug("Could not identify network prefix.")
            return None

        asn = self.netblockAs(prefix)
        if asn == None:
            sf.debug("Could not identify netblock AS.")
            return None

        ownerinfo = self.asOwnerInfo(asn)
        owned = False

        if ownerinfo != None:
            for k in ownerinfo.keys():
                items = ownerinfo[k]
                for item in items:
                    if self.findName(item.lower()):
                        owned = True

        if owned:
            sf.info("Owned netblock found: " + prefix + "(" + asn + ")")
            evt = SpiderFootEvent("NETBLOCK", prefix, self.__name__, event)
            self.notifyListeners(evt)
            asevt = SpiderFootEvent("BGP_AS", asn, self.__name__, event)
            self.notifyListeners(asevt)

            # Don't report additional netblocks from this AS if we've
            # already found this AS before.
            if not self.nbreported.has_key(asn):
                # 2. Find all the netblocks owned by this AS
                self.nbreported[asn] = True
                netblocks = self.asNetblocks(asn)
                if netblocks != None:
                    for netblock in netblocks:
                        if netblock == prefix:
                            continue
    
                        # Technically this netblock was identified via the AS, not
                        # the original IP event, so link it to asevt, not event.
                        evt = SpiderFootEvent("NETBLOCK", netblock, 
                            self.__name__, asevt)
                        self.notifyListeners(evt)

                # 3. Find all the AS neighbors to this AS
                neighs = self.asNeighbours(asn)
                if neighs == None:
                    return None

                for nasn in neighs:
                    if self.checkForStop():
                        return None

                    ownerinfo = self.asOwnerInfo(nasn)
                    ownertext = ''
                    if ownerinfo != None:
                        for k, v in ownerinfo.iteritems():
                            ownertext = ownertext + k + ": " + ', '.join(v) + "\n"
    
                    if len(ownerinfo) > 0:
                        evt = SpiderFootEvent("PROVIDER_INTERNET", ownertext,
                            self.__name__, asevt)
                        self.notifyListeners(evt)                           
        else:
            # If they don't own the netblock they are serving from, then
            # the netblock owner is their Internet provider.

            # Report the netblock instead as a subnet encapsulating the IP
            evt = SpiderFootEvent("IP_SUBNET", prefix, self.__name__, event)
            self.notifyListeners(evt)

            ownertext = ''
            if ownerinfo != None:
                for k, v in ownerinfo.iteritems():
                    ownertext = ownertext + k + ": " + ', '.join(v) + "\n"
                evt = SpiderFootEvent("PROVIDER_INTERNET", ownertext,
                    self.__name__, event)
                self.notifyListeners(evt)

        return None

# End of sfp_ir class

########NEW FILE########
__FILENAME__ = sfp_malcheck
#-------------------------------------------------------------------------------
# Name:         sfp_malcheck
# Purpose:      Checks if an ASN, IP or domain is malicious.
#
# Author:       steve@binarypool.com
#
# Created:     14/12/2013
# Copyright:   (c) Steve Micallef, 2013
# Licence:     GPL
#-------------------------------------------------------------------------------

from netaddr import IPAddress, IPNetwork
import sys
import re
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

malchecks = {
    'abuse.ch Zeus Tracker (Domain)': {
        'id': 'abusezeusdomain',
        'type': 'list',
        'checks': ['domain'],
        'url':  'https://zeustracker.abuse.ch/blocklist.php?download=baddomains'
    },
    'abuse.ch Zeus Tracker (IP)': {
        'id': 'abusezeusip',
        'type': 'list',
        'checks': ['ip', 'netblock'],
        'url': 'https://zeustracker.abuse.ch/blocklist.php?download=badips'
    },
    'abuse.ch SpyEye Tracker (Domain)': {
        'id': 'abusespydomain',
        'type': 'list',
        'checks': ['domain'],
        'url':  'https://spyeyetracker.abuse.ch/blocklist.php?download=domainblocklist'
    },
    'abuse.ch SpyEye Tracker (IP)': {
        'id': 'abusespyip',
        'type': 'list',
        'checks': ['ip', 'netblock'],
        'url':  'https://spyeyetracker.abuse.ch/blocklist.php?download=ipblocklist'
    },
    'abuse.ch Palevo Tracker (Domain)': {
        'id': 'abusepalevodomain',
        'type': 'list',
        'checks': ['domain'],
        'url':  'https://palevotracker.abuse.ch/blocklists.php?download=domainblocklist'
    },
    'abuse.ch Palevo Tracker (IP)': {
        'id': 'abusepalevoip',
        'type': 'list',
        'checks': ['ip', 'netblock'],
        'url':  'https://palevotracker.abuse.ch/blocklists.php?download=ipblocklist'
    },
    'Google SafeBrowsing (Domain/IP)': {
        'id': 'googledomain',
        'type': 'query',
        'checks': ['domain', 'ip' ],
        'url': 'http://www.google.com/safebrowsing/diagnostic?site={0}',
        'badregex': [ '.*may harm your computer.*',
            '.*this site has hosted malicious software.*'
        ],
        'goodregex': []
    },
    'Google SafeBrowsing (ASN)': {
        'id': 'googleasn',
        'type': 'query',
        'checks': ['asn'],
        'url': 'http://www.google.com/safebrowsing/diagnostic?site=AS:{0}',
        'badregex': [ '.*for example.*, that appeared to function as intermediaries.*',
            '.*this network has hosted sites that have distributed malicious.*'
        ],
        'goodregex': []
    },
    'McAfee Site Advisor': {
        'id': 'mcafeedomain',
        'type': 'query',
        'checks': ['domain'],
        'url': 'http://www.siteadvisor.com/sites/{0}',
        'badregex': ['.*This link might be dangerous.*'],
        'goodregex': []
    },
    'AVG Safety Report': {
        'id': 'avgdomain',
        'type': 'query',
        'checks': ['domain'],
        'url': 'http://www.avgthreatlabs.com/website-safety-reports/domain/{0}',
        'badregex': ['.*potentially active malware was detected.*'],
        'goodregex': []
    },
    'malwaredomains.com IP List': {
        'id': 'malwaredomainsip',
        'type': 'list',
        'checks': ['ip', 'netblock'],
        'url': 'http://www.malwaredomainlist.com/hostslist/ip.txt'
    },
    'malwaredomains.com Domain List': {
        'id': 'malwaredomainsdomain',
        'type': 'list',
        'checks': ['domain'],
        'url': 'http://www.malwaredomainlist.com/hostslist/hosts.txt',
        'regex': '.*\s+{0}[\s$]'
    },
    'PhishTank': {
        'id': 'phishtank',
        'type': 'list',
        'checks': ['domain'],
        'url': 'http://data.phishtank.com/data/online-valid.csv',
        'regex': '\d+,\w+://(.*\.)?[^a-zA-Z0-9]?{0}.*,http://www.phishtank.com/.*'
    },
    'malc0de.com List': {
        'id': 'malc0de',
        'type': 'list',
        'checks': ['ip', 'netblock'],
        'url': 'http://malc0de.com/bl/IP_Blacklist.txt'
    },
    'TOR Node List': {
        'id': 'tornodes',
        'type': 'list',
        'checks': [ 'ip', 'netblock' ],
        'url': 'http://torstatus.blutmagie.de/ip_list_all.php/Tor_ip_list_ALL.csv'
    },
    'blocklist.de List': {
        'id': 'blocklistde',
        'type': 'list',
        'checks': [ 'ip', 'netblock' ],
        'url': 'http://lists.blocklist.de/lists/all.txt'
    },
    'Autoshun.org List': {
        'id': 'autoshun',
        'type': 'list',
        'checks': [ 'ip', 'netblock' ],
        'url': 'http://www.autoshun.org/files/shunlist.csv',
        'regex': '{0},.*'
    },
    'Internet Storm Center': {
        'id': 'isc',
        'type': 'query',
        'checks': [ 'ip' ],
        'url': 'https://isc.sans.edu/api/ip/{0}',
        'badregex': [ '.*attacks.*' ],
        'goodregex': []
    },
    'AlienVault IP Reputation Database': {
        'id': 'alienvault',
        'type': 'list',
        'checks': [ 'ip', 'netblock' ],
        'url': 'https://reputation.alienvault.com/reputation.generic',
        'regex': '{0} #.*'
    },
    'OpenBL.org Blacklist': {
        'id': 'openbl',
        'type': 'list',
        'checks': [ 'ip', 'netblock' ],
        'url': 'http://www.openbl.org/lists/base.txt'
    },
    'ThreatExpert.com Database': {
        'id': 'threatexpert',
        'type': 'query',
        'checks': [ 'ip', 'domain' ],
        'url': 'http://www.threatexpert.com/reports.aspx?find={0}&tf=3',
        'badregex': [ '.*<strong>Findings</strong>.*' ],
        'goodregex': []
    },
    'TotalHash.com Database': {
        'id': 'totalhash',
        'type': 'query',
        'checks': [ 'ip', 'domain' ],
        'url': 'http://totalhash.com/search/dnsrr:*{0}%20or%20ip:{0}',
        'badregex': [ '.*<a href=\"/analysis.*' ],
        'goodregex': []
    },
    'Nothink.org SSH Scanners': {
        'id': 'nothinkssh',
        'type': 'list',
        'checks': [ 'ip', 'netblock', 'domain' ],
        'url': 'http://www.nothink.org/blacklist/blacklist_ssh_week.txt'
    },
    'Nothink.org Malware IRC Traffic': {
        'id': 'nothinkirc',
        'type': 'list',
        'checks': [ 'ip', 'netblock', 'domain' ],
        'url': 'http://www.nothink.org/blacklist/blacklist_malware_irc.txt'
    },
    'Nothink.org Malware HTTP Traffic': {
        'id': 'nothinkhttp',
        'type': 'list',
        'checks': [ 'ip', 'netblock', 'domain' ],
        'url': 'http://www.nothink.org/blacklist/blacklist_malware_http.txt'
    }  
}

class sfp_malcheck(SpiderFootPlugin):
    """Malicious Check:Check if a website, IP or ASN is considered malicious by various sources."""

    # Default options
    opts = { 
        'abusezeusdomain': True,
        'abusezeusip': True,
        'abusespydomain': True,
        'abusespyip': True,
        'abusepalevodomain': True,
        'abusepalevoip': True,
        'googledomain': True,
        'googleasn': True,
        'malwaredomainsdomain': True,
        'malwaredomainsip': True,
        'mcafeedomain': True,
        'avgdomain': True,
        'phishtank': True,
        'malc0de': True,
        'blocklistde': True,
        'autoshun': True,
        'isc': True,
        'tornodes': True,
        'alienvault': True,
        'openbl': True,
        'totalhash': True,
        'threatexpert': True,
        'nothinkssh': True,
        'nothinkirc': True,
        'nothinkhttp': True,
        'aaacheckaffiliates': True, # prefix with aaa so they appear on the top of the UI list
        'aaacheckcohosts': True,
        'aaacacheperiod': 18,
        'aaachecknetblocks': True,
        'aaachecksubnets': True
    }

    # Option descriptions
    optdescs = {
        'abusezeusdomain': "Enable abuse.ch Zeus domain check?",
        'abusezeusip': "Enable abuse.ch Zeus IP check?",
        'abusespydomain': "Enable abuse.ch SpyEye domain check?",
        'abusespyip': "Enable abuse.ch SpeEye IP check?",
        'abusepalevodomain': "Enable abuse.ch Palevo domain check?",
        'abusepalevoip': "Enable abuse.ch Palevo IP check?",
        'googledomain': "Enable Google Safe Browsing domain check?",
        'googleasn': "Enable Google Safe Browsing ASN check?",
        'malwaredomainsdomain': "Enable malwaredomainlist.com domain check?",
        'malwaredomainsip': "Enable malwaredomainlist.com IP check?",
        'mcafeedomain': "Enable McAfee Site Advisor check?",
        'avgdomain': "Enable AVG Safety check?",
        'phishtank': "Enable PhishTank check?",
        'malc0de': "Enable malc0de.com check?",
        'blocklistde': 'Enable blocklist.de check?',
        'tornodes': 'Enable TOR exit node check?',
        'autoshun': 'Enable Autoshun.org check?',
        'isc': 'Enable Internet Storm Center check?',
        'alienvault': 'Enable AlienVault IP Reputation check?',
        'openbl': 'Enable OpenBL.org Blacklist check?',
        'totalhash': 'Enable totalhash.com check?',
        'threatexpert': 'Enable threatexpert.com check?',
        'nothinkssh': 'Enable Nothink.org SSH attackers check?',
        'nothinkirc': 'Enable Nothink.org Malware DNS traffic check?',
        'nothinkhttp': 'Enable Nothink.org Malware HTTP traffic check?',
        'aaacheckaffiliates': "Apply checks to affiliates?",
        'aaacheckcohosts': "Apply checks to sites found to be co-hosted on the target's IP?",
        'aaacacheperiod':  "Hours to cache list data before re-fetching.",
        'aaachecknetblocks': "Report if any malicious IPs are found within owned netblocks?",
        'aaachecksubnets': "Check if any malicious IPs are found within the same subnet of the target?"
    }

    # Be sure to completely clear any class variables in setup()
    # or you run the risk of data persisting between scan runs.

    # Target
    baseDomain = None # calculated from the URL in setup
    results = list()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = list()

        # Clear / reset any other class member variables here
        # or you risk them persisting between threads.

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    # * = be notified about all events.
    def watchedEvents(self):
        return ["IP_ADDRESS", "BGP_AS", "SUBDOMAIN", "IP_SUBNET",
            "AFFILIATE_DOMAIN", "AFFILIATE_IPADDR",
            "CO_HOSTED_SITE", "NETBLOCK" ]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "MALICIOUS_ASN", "MALICIOUS_IPADDR", "MALICIOUS_SUBDOMAIN",
            "MALICIOUS_AFFILIATE_IPADDR", "MALICIOUS_AFFILIATE", "MALICIOUS_SUBNET",
            "MALICIOUS_COHOST" ]

    # Check the regexps to see whether the content indicates maliciousness
    def contentMalicious(self, content, goodregex, badregex):
        # First, check for the bad indicators
        if len(badregex) > 0:
            for rx in badregex:
                if re.match(rx, content, re.IGNORECASE|re.DOTALL):
                    sf.debug("Found to be bad")
                    return True

        # Finally, check for good indicators
        if len(goodregex) > 0:
            for rx in goodregex:
                if re.match(rx, content, re.IGNORECASE|re.DOTALL):
                    sf.debug("Found to be good")
                    return False

        # If nothing was matched, reply None
        sf.debug("Neither good nor bad, unknown.")
        return None

    # Look up 'query' type sources
    def resourceQuery(self, id, target, targetType):
        sf.debug("Querying " + id + " for maliciousness of " + target)
        for check in malchecks.keys():
            cid = malchecks[check]['id']
            if id == cid and malchecks[check]['type'] == "query":
                url = unicode(malchecks[check]['url'])
                res = sf.fetchUrl(url.format(target), useragent=self.opts['_useragent'])
                if res['content'] == None:
                    sf.error("Unable to fetch " + url.format(target), False)
                    return None
                if self.contentMalicious(res['content'], 
                    malchecks[check]['goodregex'],
                    malchecks[check]['badregex']):
                    return url.format(target)

        return None

    # Look up 'list' type resources
    def resourceList(self, id, target, targetType):
        targetDom = ''
        # Get the base domain if we're supplied a domain
        if targetType == "domain":
            targetDom = sf.hostDomain(target, self.opts['_internettlds'])

        for check in malchecks.keys():
            cid = malchecks[check]['id']
            if id == cid and malchecks[check]['type'] == "list":
                data = dict()
                url = malchecks[check]['url']
                data['content'] = sf.cacheGet("sfmal_" + cid, self.opts['aaacacheperiod'])
                if data['content'] == None:
                    data = sf.fetchUrl(url, useragent=self.opts['_useragent'])
                    if data['content'] == None:
                        sf.error("Unable to fetch " + url, False)
                        return None
                    else:
                        sf.cachePut("sfmal_" + cid, data['content'])

                # If we're looking at netblocks
                if targetType == "netblock":
                    iplist = list()
                    # Get the regex, replace {0} with an IP address matcher to 
                    # build a list of IP.
                    # Cycle through each IP and check if it's in the netblock.
                    if malchecks[check].has_key('regex'):
                        rx = rxTgt = malchecks[check]['regex'].replace("{0}", \
                            "(\d+\.\d+\.\d+\.\d+)")
                        sf.debug("New regex for " + check + ": " + rx)
                        for line in data['content'].split('\n'):
                            grp = re.findall(rx, line, re.IGNORECASE)
                            if len(grp) > 0:
                                #sf.debug("Adding " + grp[0] + " to list.")
                                iplist.append(grp[0])
                    else:
                        iplist = data['content'].split('\n')

                    for ip in iplist:
                        if len(ip) < 8 or ip.startswith("#"):
                            continue
                        ip = ip.strip()

                        try:
                            if IPAddress(ip) in IPNetwork(target):
                                sf.debug(ip + " found within netblock/subnet " + \
                                    target + " in " + check)
                                return url
                        except Exception as e:
                                sf.debug("Error encountered parsing: " + str(e))
                                continue

                    return None

                # If we're looking at hostnames/domains/IPs
                if not malchecks[check].has_key('regex'):
                    for line in data['content'].split('\n'):
                        if line == target or (targetType == "domain" and line == targetDom):
                            sf.debug(target + "/" + targetDom + " found in " + check + " list.")
                            return url
                else:
                    # Check for the domain and the hostname
                    rxDom = unicode(malchecks[check]['regex']).format(targetDom)
                    rxTgt = unicode(malchecks[check]['regex']).format(target)
                    for line in data['content'].split('\n'):
                        if (targetType == "domain" and re.match(rxDom, line, re.IGNORECASE)) or \
                            re.match(rxTgt, line, re.IGNORECASE):
                            sf.debug(target + "/" + targetDom + " found in " + check + " list.")
                            return url
        return None

    def lookupItem(self, resourceId, itemType, target):
        for check in malchecks.keys():
            cid = malchecks[check]['id']
            if cid == resourceId and itemType in malchecks[check]['checks']:
                sf.debug("Checking maliciousness of " + target + " (" +  \
                    itemType + ") with: " + cid)
                if malchecks[check]['type'] == "query":
                    return self.resourceQuery(cid, target, itemType)
                if malchecks[check]['type'] == "list":
                    return self.resourceList(cid, target, itemType)

        return None

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        if eventData in self.results:
            sf.debug("Skipping " + eventData + ", already checked.")
            return None
        else:
            self.results.append(eventData)

        if eventName == 'CO_HOSTED_SITE' and not self.opts['aaacheckcohosts']:
            return None
        if eventName == 'AFFILIATE_DOMAIN' or eventName == 'AFFILIATE_IPADDR' \
            and not self.opts['aaacheckaffiliates']:
            return None
        if eventName == 'NETBLOCK' and not self.opts['aaachecknetblocks']:
            return None
        if eventName == 'IP_SUBNET' and not self.opts['aaachecksubnets']:
            return None

        for check in malchecks.keys():
            cid = malchecks[check]['id']
            # If the module is enabled..
            if self.opts[cid]:
                if eventName in [ 'IP_ADDRESS', 'AFFILIATE_IPADDR' ]:
                    typeId = 'ip'
                    if eventName == 'IP_ADDRESS':
                        evtType = 'MALICIOUS_IPADDR'
                    else:
                        evtType = 'MALICIOUS_AFFILIATE_IPADDR'

                if eventName in [ 'BGP_AS' ]:
                    typeId = 'asn' 
                    evtType = 'MALICIOUS_ASN'

                if eventName in [ 'CO_HOSTED_SITE', 'AFFILIATE_DOMAIN', 'SUBDOMAIN' ]:
                    typeId = 'domain'
                    if eventName == 'SUBDOMAIN':
                        evtType = 'MALICIOUS_SUBDOMAIN'
                    if eventName == 'AFFILIATE_DOMAIN':
                        evtType = 'MALICIOUS_AFFILIATE'
                    if eventName == 'CO_HOSTED_SITE':
                        evtType = 'MALICIOUS_COHOST'

                if eventName == 'NETBLOCK':
                    typeId = 'netblock'
                    evtType = 'MALICIOUS_NETBLOCK'
                if eventName == 'IP_SUBNET':
                    typeId = 'netblock'
                    evtType = 'MALICIOUS_SUBNET'

                url = self.lookupItem(cid, typeId, eventData)
                if self.checkForStop():
                    return None

                # Notify other modules of what you've found
                if url != None:
                    text = check + " [" + eventData + "]\n" + "<SFURL>" + url + "</SFURL>"
                    evt = SpiderFootEvent(evtType, text, self.__name__, event)
                    self.notifyListeners(evt)

        return None

    def start(self):
        if self.baseDomain in self.results:
            return None
        else:
            self.results.append(self.baseDomain)

        for check in malchecks.keys():
            if self.checkForStop():
                return None

            cid = malchecks[check]['id']
            if self.opts[cid]:
                url = self.lookupItem(cid, 'domain', self.baseDomain)
                if url != None:
                    text = check + " [" + self.baseDomain + "]\n<SFURL>" + url + "</SFURL>"
                    evt = SpiderFootEvent('MALICIOUS_SUBDOMAIN', text, self.__name__)
                    self.notifyListeners(evt)

# End of sfp_malcheck class

########NEW FILE########
__FILENAME__ = sfp_names
#-------------------------------------------------------------------------------
# Name:         sfp_names
# Purpose:      Identify human names in content fetched.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     24/03/2014
# Copyright:   (c) Steve Micallef
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import re
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_names(SpiderFootPlugin):
    """Name Extractor:Attempt to identify human names in fetched content."""

    # Default options
    opts = { 
        'algotune': 50
    }

    # Option descriptions
    optdescs = {
        'algotune': "A value between 0-100 to tune the sensitivity of the name finder. Less than 40 will give you a lot of junk, over 50 and you'll probably miss things but will have less false positives."
    }

    # Be sure to completely clear any class variables in setup()
    # or you run the risk of data persisting between scan runs.

    # Target
    baseDomain = None # calculated from the URL in setup
    results = dict()
    d = None
    n = None
    fq = None

    def builddict(self, files):
        wd = dict()

        for f in files:
            wdct = open(sf.myPath() + "/ext/ispell/" + f, 'r')
            dlines = wdct.readlines()

            for w in dlines:
                w = w.strip().lower()
                wd[w.split('/')[0]] = True

        return wd.keys()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = dict()

        d = self.builddict(["english.0", "english.2", "english.4",
                        "british.0", "british.2", "british.4",
                        "american.0", "american.2", "american.4"])
        self.n = self.builddict(["names.list"])
        self.fq = [ "north", "south", "east", "west", "santa", "san", "blog", "sao" ]
        # Take dictionary words out of the names list to keep things clean
        self.d = list(set(d) - set(self.n))

        # Clear / reset any other class member variables here
        # or you risk them persisting between threads.

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    # * = be notified about all events.
    def watchedEvents(self):
        return ["TARGET_WEB_CONTENT"]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "HUMAN_NAME" ]

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        # Stage 1: Find things that look (very vaguely) like names
        m = re.findall("([A-Z][a-z]+)\s+.?.?\s?([A-Z][a-zA-Z\'\-]+)", eventData)
        for r in m:
            # Start off each match as 0 points.
            p = 0
            notindict = False

            # Shouldn't encounter "Firstname's Secondname"
            first = r[0].lower()
            if first[len(first)-2] == "'" or first[len(first)-1] == "'":
               continue

            # Strip off trailing ' or 's
            secondOrig = r[1].replace("'s", "")
            secondOrig = secondOrig.rstrip("'")
            second = r[1].lower().replace("'s", "")
            second = second.rstrip("'")

            # If both words are not in the dictionary, add 75 points.
            if first not in self.d and second not in self.d:
                p = p + 75
                notindict = True

            # If the first word is a known popular first name, award 50 points.
            if first in self.n:
                p = p + 50

            # If either word is 2 characters, subtract 50 points.
            if len(first) == 2 or len(second) == 2:
                p = p - 50

            # If the first word is in our cue list, knock out more points.
            if first in self.fq:
                p = p - 50

            # If the first word is in the dictionary but the second isn't,
            # subtract 40 points.
            if notindict == False:
                if first in self.d and second not in self.d:
                    p = p - 20

                # If the second word is in the dictionary but the first isn't,
                # reduce 20 points.
                if first not in self.d and second in self.d:
                    p = p - 40

            name = r[0] + " " + secondOrig

            if p > self.opts['algotune']:
                # Notify other modules of what you've found
                evt = SpiderFootEvent("HUMAN_NAME", name, self.__name__, event)
                self.notifyListeners(evt)

# End of sfp_names class

########NEW FILE########
__FILENAME__ = sfp_pageinfo
#-------------------------------------------------------------------------------
# Name:         sfp_pageinfo
# Purpose:      SpiderFoot plug-in for scanning retreived content by other
#               modules (such as sfp_spider) and building up information about
#               the page, such as whether it uses Javascript, has forms, and more.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     02/05/2012
# Copyright:   (c) Steve Micallef 2012
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import re
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

# Indentify pages that use Javascript libs, handle passwords, have forms,
# permit file uploads and more to come.
regexps = dict({
    'URL_JAVASCRIPT':  list(['text/javascript', '<script ']),
    'URL_FORM':        list(['<form ', 'method=[PG]', '<input ']),
    'URL_PASSWORD':    list(['<input.*type=[\"\']*password']),
    'URL_UPLOAD':      list(['type=[\"\']*file']),
    'URL_JAVA_APPLET':     list(['<applet ']),
    'URL_FLASH':    list(['\.swf[ \'\"]'])
})

class sfp_pageinfo(SpiderFootPlugin):
    """Page Info:Obtain information about web pages (do they take passwords, do they contain forms,
etc.)"""

    # Default options
    opts = { }

    # Target
    baseDomain = None # calculated from the URL in setup
    results = dict()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = dict()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return ["TARGET_WEB_CONTENT"]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "URL_STATIC", "URL_JAVASCRIPT", "URL_FORM", "URL_PASSWORD",
            "URL_UPLOAD", "URL_JAVA_APPLET", "URL_FLASH", "PROVIDER_JAVASCRIPT" ]

    # Handle events sent to this module
    def handleEvent(self, event):
        # We are only interested in the raw data from the spidering module
        # because the spidering module will always provide events with the
        # event.sourceEvent.data set to the URL of the source.
        if "sfp_spider" not in event.module:
            sf.debug("Ignoring web content from " + event.module)
            return None

        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data
        eventSource = event.sourceEvent.data # will be the URL of the raw data

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        # We aren't interested in describing pages that are not hosted on
        # our base domain.
        if not sf.urlBaseUrl(eventSource).endswith(self.baseDomain):
            sf.debug("Not gathering page info for external site " + eventSource)
            return None

        if eventSource not in self.results.keys():
            self.results[eventSource] = list()
        else:
            sf.debug("Already checked this page for a page type, skipping.")
            return None

        # Check the configured regexps to determine the page type
        for regexpGrp in regexps.keys():
            if regexpGrp in self.results[eventSource]:
                continue

            for regex in regexps[regexpGrp]:
                matches = re.findall(regex, eventData, re.IGNORECASE)
                if len(matches) > 0 and regexpGrp not in self.results[eventSource]:
                    sf.info("Matched " + regexpGrp + " in content from " + eventSource)
                    self.results[eventSource].append(regexpGrp)
                    evt = SpiderFootEvent(regexpGrp, eventSource, self.__name__, event.sourceEvent)
                    self.notifyListeners(evt)

        # If no regexps were matched, consider this a static page
        if len(self.results[eventSource]) == 0:
            sf.info("Treating " + eventSource + " as URL_STATIC")
            evt = SpiderFootEvent("URL_STATIC", eventSource, self.__name__, event.sourceEvent)
            self.notifyListeners(evt)

        # Check for externally referenced Javascript pages
        matches = re.findall("<script.*src=[\'\"]?([^\'\">]*)", eventData, re.IGNORECASE)
        if len(matches) > 0:
            for match in matches:
                if '://' in match and not sf.urlBaseUrl(match).endswith(self.baseDomain):
                    sf.debug("Externally hosted Javascript found at: " + match)
                    evt = SpiderFootEvent("PROVIDER_JAVASCRIPT", match, self.__name__, event.sourceEvent)
                    self.notifyListeners(evt)

        return None

# End of sfp_pageinfo class

########NEW FILE########
__FILENAME__ = sfp_pastebin
#-------------------------------------------------------------------------------
# Name:         sfp_pastebin
# Purpose:      Searches Google for PasteBin content related to the domain in 
#               question.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     20/03/2014
# Copyright:   (c) Steve Micallef 2014
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import random
import re
import time
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_pastebin(SpiderFootPlugin):
    """PasteBin:PasteBin scraping (via Google) to identify related content."""

    # Default options
    opts = {
        'pages':        20      # Number of google results pages to iterate
    }

    # Option descriptions
    optdescs = {
        'pages':    "Number of search results pages to iterate through."
    }

    # Target
    baseDomain = None
    results = list()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = list()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return None

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "SEARCH_ENGINE_WEB_CONTENT", "PASTEBIN_CONTENT" ]

    def start(self):
        # Sites hosted on the domain
        pages = sf.googleIterate("site:pastebin.com+\"" + \
            self.baseDomain + "\"", dict(limit=self.opts['pages'],
            useragent=self.opts['_useragent'], timeout=self.opts['_fetchtimeout']))

        if pages == None:
            sf.info("No results returned from Google PasteBin search.")
            return None

        for page in pages.keys():
            if page in self.results:
                continue
            else:
                self.results.append(page)

            # Check if we've been asked to stop
            if self.checkForStop():
                return None

            # Submit the google results for analysis
            evt = SpiderFootEvent("SEARCH_ENGINE_WEB_CONTENT", pages[page], self.__name__)
            self.notifyListeners(evt)

            # Fetch the PasteBin page
            links = sf.parseLinks(page, pages[page], "pastebin.com")
            if len(links) == 0:
                continue

            for link in links:
                if link in self.results:
                    continue
                else:
                    self.results.append(link)

                sf.debug("Found a link: " + link)
                if sf.urlBaseUrl(link).endswith("pastebin.com"):
                    if self.checkForStop():
                        return None

                    res = sf.fetchUrl(link, timeout=self.opts['_fetchtimeout'],
                        useragent=self.opts['_useragent'])

                    if res['content'] == None:
                        sf.debug("Ignoring " + link + " as no data returned")
                        continue

                    evt = SpiderFootEvent("SEARCH_ENGINE_WEB_CONTENT",
                        res['content'], self.__name__)
                    self.notifyListeners(evt)

                    # Sometimes pastebin search results false positives
                    if re.search("[^a-zA-Z\-\_]" + re.escape(self.baseDomain) + \
                        "[^a-zA-Z\-\_]", res['content'], re.IGNORECASE) == None:
                        continue

                    try:
                        startIndex = res['content'].index(self.baseDomain)-120
                        endIndex = startIndex+len(self.baseDomain)+240
                    except BaseException as e:
                        sf.debug("String not found in pastebin content.")
                        continue

                    data = res['content'][startIndex:endIndex]

                    evt = SpiderFootEvent("PASTEBIN_CONTENT",
                        "<SFURL>" + link + "</SFURL>\n" + "\"... " + data + " ...\"", 
                        self.__name__)
                    self.notifyListeners(evt)


# End of sfp_pastebin class

########NEW FILE########
__FILENAME__ = sfp_portscan_basic
#-------------------------------------------------------------------------------
# Name:         sfp_portscan_basic
# Purpose:      SpiderFoot plug-in for performing a basic port scan of IP
#               addresses identified.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     20/02/2013
# Copyright:   (c) Steve Micallef 2013
# Licence:     GPL
#-------------------------------------------------------------------------------

from netaddr import IPAddress, IPNetwork
import sys
import re
import socket
import random
import threading
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_portscan_basic(SpiderFootPlugin):
    """Port Scanner:Scans for commonly open TCP ports on Internet-facing systems."""

    # Default options
    opts = {
                            # Commonly used ports on external-facing systems
        'ports':            [ '21', '22', '23', '25', '53', '79', '80', '81', '88', '110','111', 
                            '113', '119', '123', '137', '138', '139', '143', '161', '179',
                            '389', '443', '445', '465', '512', '513', '514', '515', '3306',
                            '5432', '1521', '2638', '1433', '3389', '5900', '5901', '5902',
                            '5903', '5631', '631', '636',
                            '990', '992', '993', '995', '1080', '8080', '8888', '9000' ],
        'timeout':          15,
        'maxthreads':       10,
        'randomize':        True,
        'netblockscan':     True,
        'netblockscanmax':  24
    }

    # Option descriptions
    optdescs = {
        'maxthreads':   "Number of ports to try to open simultaneously (number of threads to spawn at once.)",
        'ports':    "The TCP ports to scan. Prefix with an '@' to iterate through a file containing ports to try (one per line), e.g. @C:\ports.txt or @/home/bob/ports.txt. Or supply a URL to load the list from there.",
        'timeout':  "Seconds before giving up on a port.",
        'randomize':    "Randomize the order of ports scanned.",
        'netblockscan': "Port scan all IPs within identified owned netblocks?",
        'netblockscanmax': "Maximum netblock/subnet size to scan IPs within (CIDR value, 24 = /24, 16 = /16, etc.)"
    }

    # Target
    baseDomain = None
    results = dict()
    portlist = list()
    portResults = dict()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = dict()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

        if self.opts['ports'][0].startswith("http://") or \
            self.opts['ports'][0].startswith("https://") or \
            self.opts['ports'][0].startswith("@"):
            self.portlist = sf.optValueToData(self.opts['ports'][0])
        else:
            self.portlist = self.opts['ports']

        # Convert to integers
        self.portlist = [int(x) for x in self.portlist]

        if self.opts['randomize']:
            random.shuffle(self.portlist)

    # What events is this module interested in for input
    def watchedEvents(self):
        return ['IP_ADDRESS', 'NETBLOCK']

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "TCP_PORT_OPEN", "TCP_PORT_OPEN_BANNER" ]

    def tryPort(self, ip, port):
        try:
            sock = socket.create_connection((ip, port), self.opts['timeout'])
            sock.settimeout(self.opts['timeout'])
            self.portResults[ip + ":" + str(port)] = True
        except Exception as e:
            self.portResults[ip + ":" + str(port)] = False
            return

        # If the port was open, see what we can read
        try:
            self.portResults[ip + ":" + str(port)] = sock.recv(4096)
        except Exception as e:
            sock.close()
            return

        sock.close()

    def tryPortWrapper(self, ip, portList):
        self.portResults = dict()
        running = True
        i = 0
        t = []

        # Spawn threads for scanning
        while i < len(portList):
            sf.info("Spawning thread to check port: " + str(portList[i]) + " on " + ip)
            t.append(threading.Thread(name='sfp_portscan_basic_' + str(portList[i]), 
                target=self.tryPort, args=(ip, portList[i])))
            t[i].start()
            i += 1

        # Block until all threads are finished
        while running:
            found = False
            for rt in threading.enumerate():
                if rt.name.startswith("sfp_portscan_basic_"):
                    found = True

            if not found:
                running = False

        return self.portResults

    # Generate TCP_PORT_OPEN_BANNER event
    def sendEvent(self, resArray, srcEvent):
        for cp in resArray:
            if resArray[cp]:
                sf.info("TCP Port " + cp + " found to be OPEN.")
                (addr, port) = cp.split(":")
                evt = SpiderFootEvent("TCP_PORT_OPEN", port, self.__name__, srcEvent)
                self.notifyListeners(evt)
                if resArray[cp] != "" and resArray[cp] != True:
                    bevt = SpiderFootEvent("TCP_PORT_OPEN_BANNER", resArray[cp],
                        self.__name__, evt)
                    self.notifyListeners(bevt)


    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data
        scanIps = list()

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        try:
            if eventName == "NETBLOCK" and self.opts['netblockscan']:
                net = IPNetwork(eventData)
                if net.prefixlen < self.opts['netblockscanmax']:
                    sf.debug("Skipping port scanning of " + eventData + ", too big.")
                    return None

                for ip in list(net):
                    scanIps.append(str(ip))
            else:
                scanIps.append(eventData)
        except BaseException as e:
            sf.error("Strange netblock identified, unable to parse: " + \
                eventData + " (" + str(e) + ")", False)
            return None

        for ipAddr in scanIps:
            # Don't look up stuff twice
            if self.results.has_key(ipAddr):
                sf.debug("Skipping " + ipAddr + " as already scanned.")
                return None
            else:
                self.results[ipAddr] = True

            i = 0
            portArr = []
            for port in self.portlist:
                if self.checkForStop():
                    return None
                
                if i < self.opts['maxthreads']:
                    portArr.append(port)    
                    i += 1
                else:
                    self.sendEvent(self.tryPortWrapper(ipAddr, portArr), event)
                    i = 1
                    portArr = []
                    portArr.append(port)

            # Scan whatever is remaining
            self.sendEvent(self.tryPortWrapper(ipAddr, portArr), event)

# End of sfp_portscan_basic class

########NEW FILE########
__FILENAME__ = sfp_sharedip
#-------------------------------------------------------------------------------
# Name:         sfp_sharedip
# Purpose:      Searches Bing and/or Robtex.com for hosts sharing the same IP.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     12/04/2014
# Copyright:   (c) Steve Micallef 2014
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import random
import re
import time
import socket
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_sharedip(SpiderFootPlugin):
    """Shared IP:Search Bing and/or Robtex.com for hosts sharing the same IP."""

    # Default options
    opts = {
        'cohostsamedomain': False,
        'pages': 20,
        'source': 'robtex',
        'verify': True
    }

    # Option descriptions
    optdescs = {
        'cohostsamedomain': "Treat co-hosted sites on the same target domain as co-hosting?",
        'pages': "If using Bing, how many pages to iterate through.",
        'source': "Source: bing or robtex.",
        'verify': "Verify co-hosts are valid by checking if they still resolve to the shared IP."
    }

    # Target
    baseDomain = None
    results = list()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = list()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return [ "IP_ADDRESS" ]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "CO_HOSTED_SITE", "SEARCH_ENGINE_WEB_CONTENT" ]

    def validateIP(self, host, ip):
        try:
            addrs = socket.gethostbyname_ex(host)
        except BaseException as e:
            sf.debug("Unable to resolve " + host + ": " + str(e))
            return False

        for addr in addrs:
            if type(addr) == list:
                for a in addr:
                    if str(a) == ip:
                        return True
            else:
                if str(addr) == ip:
                    return True
        return False

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data
        self.currentEventSrc = event

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        # Don't look up stuff twice
        if eventData in self.results:
            sf.debug("Skipping " + eventData + " as already mapped.")
            return None
        else:
            self.results.append(eventData)

        # Robtex
        if self.opts['source'].lower() == "robtex":
            res = sf.fetchUrl("https://www.robtex.com/ip/" + eventData + ".html")
            if res['content'] == None:
                sf.error("Unable to fetch robtex content.", False)
                return None

            myres = list()
            blob = re.findall(".*Pointing to(.[^!]+)shared_pp_pa.*", res['content'],
                re.IGNORECASE|re.DOTALL)
            if len(blob) > 0:
                matches = re.findall("href=\"//www.robtex.com/dns/(.[^\"]*).html",
                    blob[0], re.IGNORECASE)
                for m in matches:
                    sf.info("Found something on same IP: " + m)
                    if not self.opts['cohostsamedomain'] and m.endswith(self.baseDomain):
                        sf.debug("Skipping " + m + " because it is on the same domain.")
                        continue

                    if '*' in m:
                        sf.debug("Skipping wildcard name: " + m)
                        continue

                    if '.' not in m:
                        sf.debug("Skipping tld: " + m)
                        continue

                    if m not in myres and m != eventData:
                        if self.opts['verify'] and not self.validateIP(m, eventData):
                            sf.debug("Host no longer resolves to our IP.")
                            continue
                        evt = SpiderFootEvent("CO_HOSTED_SITE", m, self.__name__, event)
                        self.notifyListeners(evt)
                        myres.append(m)

        # Bing
        if self.opts['source'].lower() == "bing":
            results = sf.bingIterate("ip:" + eventData, dict(limit=self.opts['pages'],
                useragent=self.opts['_useragent'], timeout=self.opts['_fetchtimeout']))
            myres = list()
            if results == None:
                sf.info("No data returned from Bing.")
                return None

            for key in results.keys():
                res = results[key]
                matches = re.findall("<div class=\"sb_meta\"><cite>(\S+)</cite>", 
                    res, re.IGNORECASE)
                for match in matches:
                    sf.info("Found something on same IP: " + match)
                    site = sf.urlFQDN(match)
                    if site not in myres and site != eventData:
                        if not self.opts['cohostsamedomain'] and site.endswith(self.baseDomain):
                            sf.debug("Skipping " + site + " because it is on the same domain.")
                            continue
                        if self.opts['verify'] and not self.validateIP(m, eventData):
                            sf.debug("Host no longer resolves to our IP.")
                            continue
                        evt = SpiderFootEvent("CO_HOSTED_SITE", site, self.__name__, event)
                        self.notifyListeners(evt)
                        myres.append(site)

                # Submit the bing results for analysis
                evt = SpiderFootEvent("SEARCH_ENGINE_WEB_CONTENT", results[key], 
                    self.__name__, event)
                self.notifyListeners(evt)

# End of sfp_sharedip class

########NEW FILE########
__FILENAME__ = sfp_shodan
#-------------------------------------------------------------------------------
# Name:         sfp_shodan
# Purpose:      Query SHODAN for identified IP addresses.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     19/03/2014
# Copyright:   (c) Steve Micallef
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import json
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_shodan(SpiderFootPlugin):
    """SHODAN:Obtain information from SHODAN about identified IP addresses."""

    # Default options
    opts = { 
        "apikey":   ""
    }

    # Option descriptions
    optdescs = {
        "apikey":   "Your SHODAN API Key."
    }

    # Be sure to completely clear any class variables in setup()
    # or you run the risk of data persisting between scan runs.

    # Target
    baseDomain = None # calculated from the URL in setup
    results = dict()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = dict()

        # Clear / reset any other class member variables here
        # or you risk them persisting between threads.

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return ["IP_ADDRESS"]

    # What events this module produces
    def producedEvents(self):
        return ["OPERATING_SYSTEM", "DEVICE_TYPE", 
            "TCP_PORT_OPEN", "TCP_PORT_OPEN_BANNER"]

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        if self.opts['apikey'] == "":
            sf.error("You enabled sfp_shodan but did not set an API key!", False)
            return None

       # Don't look up stuff twice
        if self.results.has_key(eventData):
            sf.debug("Skipping " + eventData + " as already mapped.")
            return None
        else:
            self.results[eventData] = True

        res = sf.fetchUrl("https://api.shodan.io/shodan/host/" + eventData + \
            "?key=" + self.opts['apikey'],
            timeout=self.opts['_fetchtimeout'], useragent=self.opts['_useragent'])
        if res['content'] == None:
            sf.info("No SHODAN info found for " + eventData)
            return None

        try:
            info = json.loads(res['content'])
        except Exception as e:
            sf.error("Error processing JSON response from SHODAN.", False)
            return None

        os = info.get('os')
        devtype = info.get('devicetype')

        if os != None:
            # Notify other modules of what you've found
            evt = SpiderFootEvent("OPERATING_SYSTEM", os, self.__name__, event)
            self.notifyListeners(evt)

        if devtype != None:
            # Notify other modules of what you've found
            evt = SpiderFootEvent("DEVICE_TYPE", devtype, self.__name__, event)
            self.notifyListeners(evt)


        sf.info("Found SHODAN data for " + eventData)
        for rec in info['data']:
            port = str(rec.get('port'))
            banner = rec.get('banner')

            if port != None:
                # Notify other modules of what you've found
                evt = SpiderFootEvent("TCP_PORT_OPEN", port, self.__name__, event)
                self.notifyListeners(evt)

            if banner != None:
                # Notify other modules of what you've found
                evt = SpiderFootEvent("TCP_PORT_OPEN_BANNER", banner, self.__name__, event)
                self.notifyListeners(evt)

        return None

# End of sfp_shodan class

########NEW FILE########
__FILENAME__ = sfp_similar
#-------------------------------------------------------------------------------
# Name:         sfp_similar
# Purpose:      SpiderFoot plug-in for identifying domains that look similar
#               to the one being queried.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     06/04/2012
# Copyright:   (c) Steve Micallef 2012
# Licence:     GPL
#-------------------------------------------------------------------------------

import socket
import sys
import re
import time
import random
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# These are all string builders, {0} = the domain keyword, {1} = the page number

# Domaintools.com:
# Seems to be the best choice overall
domtoolUrlLeft = "http://www.domaintools.com/buy/domain-search/?q={0}&bc=25&bn=y&bh=A&order=left&pool=A&filter=y&search_type=&rows=100&de_search=Search&page={1}"
domtoolUrlRight = "http://www.domaintools.com/buy/domain-search/?q={0}&bc=25&bn=y&bh=A&order=right&pool=A&filter=y&search_type=&rows=100&de_search=Search&page={1}"
domtoolLastPageIndicator = "&gt;&gt;"
domtoolIncrement = 100

# Namedroppers.org:
# Downside is that a maximum of 500 results are returned
namedropUrlLeft = "http://www.namedroppers.org/b/q?p={1}&k={0}&min=1&max=63&order=0&display=0&first=1&adv=1&com=1&net=1&org=1&edu=1&biz=1&us=1&info=1&name=1"
namedropUrlRight = "http://www.namedroppers.org/b/q?p={1}&k={0}&min=1&max=63&order=0&display=0&last=1&adv=1&com=1&net=1&org=1&edu=1&biz=1&us=1&info=1&name=1"
namedropLastPageIndicator = "&gt;&gt;"

# Whois.com:
# Downside is that this doesn't allow startswith/endswith searching
whoisUrlFirst = "http://www.whois.net/domain-keyword-search/{0}"
whoisUrlN = "http://www.whois.net/domain-keyword-search/{0}/{1}"
whoisLastPageIndicator = "Next >"
whoisIncrement = 16

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_similar(SpiderFootPlugin):
    """Similar Domains:Search various sources to identify similar looking domain names."""

    # Default options
    opts = {
        'source':       'ALL', # domaintools, namedroppers or ALL
        'method':       'left,right', # left and/or right (doesn't apply to whois.com)
        'activeonly':   True # Only report domains that have content (try to fetch the page)
    }

    # Option descriptions
    optdescs = {
        'source':       "Provider to use: 'domaintools', 'namedroppers' or 'ALL'.",
        'method':       "Pattern search method to use: 'left,right', 'left' or 'right'.",
        'activeonly':   "Only report domains that have content (try to fetch the page)?"
    }

    # Internal results tracking
    results = list()

    # Target
    baseDomain = None

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = list()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    def findDomains(self, keyword, content):
        matches = re.findall("([a-z0-9\-]*" + keyword + "[a-z0-9\-]*\.[a-z]+)", 
            content, re.IGNORECASE)

        return matches

    # What events is this module interested in for input
    def watchedEvents(self):
        return None

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "SIMILARDOMAIN" ]

    # Fetch and loop through Whois.com results, updating our results data. Stop
    # once we've reached the end.
    def scrapeWhois(self, keyword):
        reachedEnd = False
        i = 0
        while not reachedEnd:
            if i == 0:
                # First iteration
                fetchPage = whoisUrlFirst.format(keyword)
            else:
                # Subsequent iterations have a different URL (in chunks of 16)
                fetchPage = whoisUrlN.format(keyword, i * whoisIncrement)

            # Check if we've been asked to stop
            if self.checkForStop():
                return None

            whois = sf.fetchUrl(fetchPage, timeout=self.opts['_fetchtimeout'], 
                useragent=self.opts['_useragent'])
            if whois['content'] == None:
                return None

            # Extract the similar domains out of the whois content
            freshResults = self.findDomains(keyword, whois['content'])
            for result in freshResults:
                if result in self.results:
                    continue

                self.storeResult(fetchPage, result)

            if not whoisLastPageIndicator in whois['content']:
                reachedEnd = True
            else:
                time.sleep(random.randint(1, 10))

            i += 1

    def scrapeDomaintools(self, keyword, position):
        reachedEnd = False
        i = 1 # Using 0 will cause the first page to appear twice
        while not reachedEnd:
            if position == "LEFT":
                fetchPage = domtoolUrlLeft.format(keyword, i)
            else:
                fetchPage = domtoolUrlRight.format(keyword, i)

            if self.checkForStop():
                return None

            domtool = sf.fetchUrl(fetchPage, timeout=self.opts['_fetchtimeout'], 
                useragent=self.opts['_useragent'])
            if domtool['content'] == None:
                return None

            # Extract the similar domains out of the domain tools content
            freshResults = self.findDomains(keyword, domtool['content'])
            for result in freshResults:
                if result in self.results:
                    continue
                # Images for the domain get picked up by the regexp
                if '.jpg' in result:
                    continue

                self.storeResult(fetchPage, result)

            if not domtoolLastPageIndicator in domtool['content']:
                reachedEnd = True
            else:
                time.sleep(random.randint(1, 10))

            i += 1

    def scrapeNamedroppers(self, keyword, position):
        reachedEnd = False
        i = 1 # Using 0 will cause the first page to appear twice
        while not reachedEnd:
            if position == "LEFT":
                fetchPage = namedropUrlLeft.format(keyword, i)
            else:
                fetchPage = namedropUrlRight.format(keyword, i)

            if self.checkForStop():
                return None

            namedrop = sf.fetchUrl(fetchPage, timeout=self.opts['_fetchtimeout'], 
                useragent=self.opts['_useragent'])
            if namedrop['content'] == None:
                return None

            # Extract the similar domains out of the namedropper content
            freshResults = self.findDomains(keyword, namedrop['content'])
            for result in freshResults:
                if result in self.results:
                    continue

                self.storeResult(fetchPage, result)

            if not namedropLastPageIndicator in namedrop['content']:
                reachedEnd = True
            else:
                time.sleep(random.randint(1, 10))

            i += 1

    # Store the result internally and notify listening modules
    def storeResult(self, source, result):
        if result == self.baseDomain:
            return

        sf.info("Found a similar domain: " + result)
        self.results.append(result)

        # Inform listening modules
        if self.opts['activeonly']:
            if self.checkForStop():
                return None

            pageContent = sf.fetchUrl('http://' + result, 
                timeout=self.opts['_fetchtimeout'], useragent=self.opts['_useragent'])
            if pageContent['content'] != None:
                evt = SpiderFootEvent("SIMILARDOMAIN", result, self.__name__)
                self.notifyListeners(evt)
        else:
            evt = SpiderFootEvent("SIMILARDOMAIN", result, self.__name__)
            self.notifyListeners(evt)


    # Search for similar sounding domains
    def start(self):
        keyword = sf.domainKeyword(self.baseDomain, self.opts['_internettlds'])
        sf.debug("Keyword extracted from " + self.baseDomain + ": " + keyword)

        # No longer seems to work.
        #if "whois" in self.opts['source'] or "ALL" in self.opts['source']:
        #    self.scrapeWhois(keyword)

        # Check popular Internet repositories for domains containing our target keyword
        if "domtools" in self.opts['source'] or "ALL" in self.opts['source']:
            if "left" in self.opts['method']:
                self.scrapeDomaintools(keyword, "LEFT")
            if "right" in self.opts['method']:
                self.scrapeDomaintools(keyword, "RIGHT")

        if "namedroppers" in self.opts['source'] or "ALL" in self.opts['source']:
            if "left" in self.opts['method']:
                self.scrapeNamedroppers(keyword, "LEFT")
            if "right" in self.opts['method']:
                self.scrapeNamedroppers(keyword, "RIGHT")

        return None

# End of sfp_similar class

########NEW FILE########
__FILENAME__ = sfp_social
#-------------------------------------------------------------------------------
# Name:         sfp_social`
# Purpose:      Identify the usage of popular social networks
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     26/05/2013
# Copyright:   (c) Steve Micallef 2013
# Licence:     GPL
#-------------------------------------------------------------------------------

import re
import sys
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

regexps = dict({
    "LinkedIn (Individual)": list(['.*linkedin.com/in/([a-zA-Z0-9_]+$)']),
    "LinkedIn (Company)": list(['.*linkedin.com/company/([a-zA-Z0-9_]+$)']),
    "Github":           list(['.*github.com/([a-zA-Z0-9_]+)\/']),
    "Google+":          list(['.*plus.google.com/([0-9]+$)']),
    "Facebook":         list(['.*facebook.com/([a-zA-Z0-9_]+$)']),
    "YouTube":          list(['.*youtube.com/([a-zA-Z0-9_]+$)']),
    "Twitter":          list(['.*twitter.com/([a-zA-Z0-9_]{1,15}$)',
                              '.*twitter.com/#!/([a-zA-Z0-9_]{1,15}$)'
                        ]),
    "SlideShare":       list(['.*slideshare.net/([a-zA-Z0-9_]+$)'])
})

class sfp_social(SpiderFootPlugin):
    """Social Networks:Identify presence on social media networks such as LinkedIn, Twitter and others."""

    # Default options
    opts = { }

    # Option descriptions
    optdescs = {
        # For each option in opts you should have a key/value pair here
        # describing it. It will end up in the UI to explain the option
        # to the end-user.
    }

    # Target
    baseDomain = None # calculated from the URL in setup
    results = dict()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = dict()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    # * = be notified about all events.
    def watchedEvents(self):
        return ["LINKED_URL_EXTERNAL"]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "SOCIAL_MEDIA" ]

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        if eventData not in self.results.keys():
            self.results[eventData] = True
        else:
            return None

        for regexpGrp in regexps.keys():
            for regex in regexps[regexpGrp]:
                bits = re.match(regex, eventData, re.IGNORECASE)
                if bits != None:
                    sf.info("Matched " + regexpGrp + " in " + eventData)
                    evt = SpiderFootEvent("SOCIAL_MEDIA", regexpGrp + ": " + \
                        bits.group(1), self.__name__, event)
                    self.notifyListeners(evt)

        return None

    # If you intend for this module to act on its own (e.g. not solely rely
    # on events from other modules, then you need to have a start() method
    # and within that method call self.checkForStop() to see if you've been
    # politely asked by the controller to stop your activities (user abort.)

# End of sfp_social class

########NEW FILE########
__FILENAME__ = sfp_socialprofiles
#-------------------------------------------------------------------------------
# Name:         sfp_socialprofiles
# Purpose:      Obtains social media profiles of any identified human names.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     12/04/2014
# Copyright:   (c) Steve Micallef 2014
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import random
import re
import time
import urllib
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

sites = {
    # Search string to use, domain name the profile will sit on within 
    # those search results.
    "Facebook": ['+intitle:%22{0}%22%20+site:facebook.com', 
        '"(https?://[a-z\.]*facebook.[a-z\.]+/[^\"<> ]+)"' ],
    "Google+": ['+intitle:%22{0}%22%20+site:plus.google.com', 
        '"(https?://plus.google.[a-z\.]+/\d+[^\"<>\/ ]+)"' ],
    "LinkedIn": ['+intitle:%22{0}%22%20+site:linkedin.com', 
        '"(https?://[a-z\.]*linkedin.[a-z\.]+/[^\"<> ]+)"' ]
}

class sfp_socialprofiles(SpiderFootPlugin):
    """Social Media Profiles:Identify the social media profiles for human names identified."""

    # Default options
    opts = {
        'pages': 1,
        'method': "yahoo",
        'tighten': True
    }

    # Option descriptions
    optdescs = {
        'pages': "Number of search engine pages of identified profiles to iterate through.",
        'tighten': "Tighten results by expecting to find the keyword of the target domain mentioned in the social media profile page results?",
        'method': "Search engine to use: google, yahoo or bing."
    }

    # Target
    baseDomain = None
    keyword = None
    results = list()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = list()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

        self.keyword = sf.domainKeyword(self.baseDomain, 
            self.opts['_internettlds']).lower()

    # What events is this module interested in for input
    def watchedEvents(self):
        return [ "HUMAN_NAME" ]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "SOCIAL_MEDIA" ]

    def yahooCleaner(self, string):
        ret = "\"" + urllib.unquote(string.group(1)) + "\""
        return ret

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data
        self.currentEventSrc = event

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        # Don't look up stuff twice
        if eventData in self.results:
            sf.debug("Skipping " + eventData + " as already mapped.")
            return None
        else:
            self.results.append(eventData)

        for site in sites.keys():
            searchStr = sites[site][0].format(eventData).replace(" ", "%20")
            searchDom = sites[site][1]

            if self.opts['method'].lower() == "google":
                results = sf.googleIterate(searchStr, dict(limit=self.opts['pages'],
                    useragent=self.opts['_useragent'], 
                    timeout=self.opts['_fetchtimeout']))

            if self.opts['method'].lower() == "yahoo":
                results = sf.yahooIterate(searchStr, dict(limit=self.opts['pages'],
                    useragent=self.opts['_useragent'], 
                    timeout=self.opts['_fetchtimeout']))

            if self.opts['method'].lower() == "bing":
                results = sf.bingIterate(searchStr, dict(limit=self.opts['pages'],
                    useragent=self.opts['_useragent'],
                    timeout=self.opts['_fetchtimeout']))

            if results == None:
                sf.info("No data returned from " + self.opts['method'] + ".")
                return None

            if self.checkForStop():
                return None

            pauseSecs = random.randint(4, 15)
            sf.debug("Pausing for " + str(pauseSecs))
            time.sleep(pauseSecs)

            for key in results.keys():
                instances = list()
                # Yahoo requires some additional parsing
                if self.opts['method'].lower() == "yahoo":
                    res = re.sub("RU=(.[^\/]+)\/RK=", self.yahooCleaner, 
                        results[key], 0)
                else:
                    res = results[key]

                matches = re.findall(searchDom, res, re.IGNORECASE)

                if matches != None:
                    for match in matches:
                        if match in instances:
                            continue
                        else:
                            instances.append(match)

                        if self.checkForStop():
                            return None

                        # Fetch the profile page if we are checking
                        # for a firm relationship.
                        if self.opts['tighten']:
                            pres = sf.fetchUrl(match, timeout=self.opts['_fetchtimeout'],
                                useragent=self.opts['_useragent'])

                            if pres['content'] == None:
                                continue
                            else:
                                if re.search("[^a-zA-Z\-\_]" + self.keyword + \
                                    "[^a-zA-Z\-\_]", pres['content'], re.IGNORECASE) == None:
                                    continue

                        sf.info("Social Media Profile found at " + site + ": " + match)
                        evt = SpiderFootEvent("SOCIAL_MEDIA", match, 
                            self.__name__, event)
                        self.notifyListeners(evt)

                # Submit the bing results for analysis
                evt = SpiderFootEvent("SEARCH_ENGINE_WEB_CONTENT", res, 
                    self.__name__, event)
                self.notifyListeners(evt)

# End of sfp_socialprofiles class

########NEW FILE########
__FILENAME__ = sfp_spider
#-------------------------------------------------------------------------------
# Name:         sfp_spider
# Purpose:      SpiderFoot plug-in for spidering sites and returning meta data
#               for other plug-ins to consume.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     25/03/2012
# Copyright:   (c) Steve Micallef 2012
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import re
import time
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in __init__)
sf = None

class sfp_spider(SpiderFootPlugin):
    """Spider:Spidering of web-pages to extract content for searching. """

    # Default options
    opts = {
        'robotsonly':   False, # only follow links specified by robots.txt
        'pause':        1, # number of seconds to pause between fetches
        'maxpages':     100, # max number of pages to fetch
        'maxlevels':    3, # max number of levels to traverse within a site
        'usecookies':   True, # Use cookies?
        'start':        [ 'http://', 'https://' ],
        'filterfiles':  ['png','gif','jpg','jpeg','tiff', 'tif', 'js', 'css', 'tar',
                        'pdf','tif','ico','flv', 'mp4', 'mp3', 'avi', 'mpg', 'gz',
                        'mpeg', 'iso', 'dat', 'mov', 'swf', 'rar', 'exe', 'zip',
                        'bin', 'bz2', 'xsl', 'doc', 'docx', 'ppt', 'pptx', 'xls',
                        'xlsx', 'csv'],
        'filterusers':  True, # Don't follow /~user directories
        'noexternal':   True, # Should links to external sites be ignored? (**dangerous if False**)
        'nosubs':       False, # Should links to subdomains be ignored?
    }

    # Option descriptions
    optdescs = {
        'robotsonly':   "Only follow links specified by robots.txt?",
        'pause':        "Number of seconds to pause between fetches.",
        'usecookies':   "Accept and use cookies?",
        'start':        "Prepend targets with these until you get a hit, to start spidering.",
        'maxpages':     "Maximum number of pages to fetch per target identified.",
        'maxlevels':    "Maximum levels to traverse per target identified.",
        'filterfiles':  "File extensions to ignore (don't fetch them.)",
        'filterusers':  "Skip spidering of /~user directories?",
        'noexternal':   "Skip spidering of external sites? (**dangerous if False**)",
        'nosubs':       "Skip spidering of subdomains of the target?"
    }

    # If using robots.txt, this will get populated with filter rules
    robotsRules = dict()

    # Target
    baseDomain = None

    # Pages already fetched
    fetchedPages = dict()

    # Events for links identified
    urlEvents = dict()

    # Tracked cookies per site
    siteCookies = dict()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.fetchedPages = dict()
        self.urlEvents = dict()
        self.siteCookies = dict()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # Fetch data from a URL and obtain all links that should be followed
    def processUrl(self, url):
        site = sf.urlFQDN(url)
        cookies = None
        if self.siteCookies.has_key(site):
            sf.debug("Restoring cookies for " + site + ": " + str(self.siteCookies[site]))
            cookies = self.siteCookies[site]
        # Fetch the contents of the supplied URL (object returned)
        fetched = sf.fetchUrl(url, False, cookies, 
            self.opts['_fetchtimeout'], self.opts['_useragent'])
        self.fetchedPages[url] = True

        # Track cookies a site has sent, then send the back in subsquent requests
        if self.opts['usecookies'] and fetched['headers'] != None:
            if fetched['headers'].get('Set-Cookie'):
                self.siteCookies[site] = fetched['headers'].get('Set-Cookie')
                sf.debug("Saving cookies for " + site + ": " + str(self.siteCookies[site]))

        if not self.urlEvents.has_key(url):
            self.urlEvents[url] = None

        # Notify modules about the content obtained
        self.contentNotify(url, fetched, self.urlEvents[url])

        if fetched['realurl'] != None and fetched['realurl'] != url:
            sf.debug("Redirect of " + url + " to " + fetched['realurl'])
            # Store the content for the redirect so that it isn't fetched again
            self.fetchedPages[fetched['realurl']] = True
            # Notify modules about the new link
            self.urlEvents[fetched['realurl']] = self.linkNotify(fetched['realurl'], 
                self.urlEvents[url])
            url = fetched['realurl'] # override the URL if we had a redirect

        # Extract links from the content
        links = sf.parseLinks(url, fetched['content'], self.baseDomain)

        if links == None or len(links) == 0:
            sf.info("No links found at " + url)
            return None

        # Notify modules about the links found
        # Aside from the first URL, this will be the first time a new
        # URL is spotted.
        for link in links:
            # Supply the SpiderFootEvent of the parent URL as the parent
            self.urlEvents[link] = self.linkNotify(link, self.urlEvents[url])

        sf.debug('Links found from parsing: ' + str(links))
        return links

    # Clear out links that we don't want to follow
    def cleanLinks(self, links):
        returnLinks = dict()

        for link in links.keys():
            linkBase = sf.urlBaseUrl(link)

            # Optionally skip external sites (typical behaviour..)
            if self.opts['noexternal'] and not sf.urlBaseUrl(link).endswith(self.baseDomain):
                sf.debug('Ignoring external site: ' + link)
                continue

            # Optionally skip sub-domain sites
            if self.opts['nosubs'] and not sf.urlBaseUrl(link).endswith('://' + self.baseDomain):
                sf.debug("Ignoring subdomain: " + link)
                continue

            # Optionally skip user directories
            if self.opts['filterusers'] and '/~' in link:
                sf.debug("Ignoring user folder: " + link)
                continue

            # If we are respecting robots.txt, filter those out too
            checkRobots = lambda blocked: str.lower(blocked) in link.lower() or blocked == '*'
            if self.opts['robotsonly'] and filter(checkRobots, self.robotsRules[linkBase]):
                sf.debug("Ignoring page found in robots.txt: " + link)
                continue

            # Filter out certain file types (if user chooses to)
            checkExts = lambda ext: link.lower().endswith('.' + ext.lower())
            if filter(checkExts, self.opts['filterfiles']):
                sf.debug('Ignoring filtered extension: ' + link)
                continue

            # All tests passed, add link to be spidered
            sf.debug("Adding URL for spidering: " + link)
            returnLinks[link] = links[link]

        return returnLinks

    # Notify listening modules about links
    def linkNotify(self, url, parentEvent=None):
        if sf.urlBaseUrl(url).endswith(self.baseDomain):
            type = "LINKED_URL_INTERNAL"
        else:
            type = "LINKED_URL_EXTERNAL"

        event = SpiderFootEvent(type, url, self.__name__, parentEvent)
        self.notifyListeners(event)

        return event

    # Notify listening modules about raw data and others
    def contentNotify(self, url, httpresult, parentEvent=None):
        event = SpiderFootEvent("TARGET_WEB_CONTENT", httpresult['content'], 
            self.__name__, parentEvent)
        self.notifyListeners(event)

        event = SpiderFootEvent("WEBSERVER_HTTPHEADERS", httpresult['headers'],
            self.__name__, parentEvent)
        self.notifyListeners(event)

        event = SpiderFootEvent("HTTP_CODE", str(httpresult['code']),
            self.__name__, parentEvent)
        self.notifyListeners(event)

    # Trigger spidering off the following events..
    # Google search provides LINKED_URL_INTERNAL, and DNS lookups
    # provide SUBDOMAIN.
    def watchedEvents(self):
        return [ "LINKED_URL_INTERNAL", "SUBDOMAIN" ]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "WEBSERVER_HTTPHEADERS", "HTTP_CODE", "LINKED_URL_INTERNAL",
            "LINKED_URL_EXTERNAL", "TARGET_WEB_CONTENT" ]

    # Some other modules may request we spider things
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data
        spiderTarget = None

        # Ignore self-generated events so that we don't end up in a recursive loop
        if "sfp_spider" in srcModuleName:
            sf.debug("Ignoring event from myself.")
            return None

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        if eventData in self.urlEvents.keys():
            sf.debug("Ignoring " + eventData + " as already spidered or is being spidered.")           
            return None
        else:
            self.urlEvents[eventData] = event

        # Determine where to start spidering from if it's a SUBDOMAIN event
        if eventName == "SUBDOMAIN":
            for prefix in self.opts['start']:
                res = sf.fetchUrl(prefix + eventData, timeout=self.opts['_fetchtimeout'], 
                    useragent=self.opts['_useragent'])
                if res['content'] != None:
                    spiderTarget = prefix + eventData
                    break
        else:
            spiderTarget = eventData

        if spiderTarget == None:
            return None

        sf.info("Initiating spider of " + spiderTarget)

        # Link the spidered URL to the event that triggered it
        self.urlEvents[spiderTarget] = event
        return self.spiderFrom(spiderTarget)

    # Start spidering
    def spiderFrom(self, startingPoint):
        keepSpidering = True
        totalFetched = 0
        levelsTraversed = 0
        nextLinks = dict()
        targetBase = sf.urlBaseUrl(startingPoint)

        # Are we respecting robots.txt?
        if self.opts['robotsonly'] and not self.robotsRules.has_key(targetBase):
            robotsTxt = sf.fetchUrl(targetBase + '/robots.txt', 
                timeout=self.opts['_fetchtimeout'], useragent=self.opts['_useragent'])
            if robotsTxt['content'] != None:
                sf.debug('robots.txt contents: ' + robotsTxt['content'])
                self.robotsRules[targetBase] = sf.parseRobotsTxt(robotsTxt['content'])
            else:
                sf.error("Unable to fetch robots.txt and you've asked to abide by its contents.")
                return None

        # First iteration we are starting with links found on the start page
        # Iterations after that are based on links found on those pages,
        # and so on..
        links = self.processUrl(startingPoint)  # fetch first page

        # No links from the first fetch means we've got a problem
        if links == None:
            sf.error("No links found on the first fetch!", exception=False)
            return

        while keepSpidering:
            # Gets hit in the second and subsequent iterations when more links
            # are found
            if len(nextLinks) > 0:
                links = dict()

                # Fetch content from the new links
                for link in nextLinks.keys():
                    # Always skip links we've already fetched
                    if (link in self.fetchedPages.keys()):
                        sf.debug("Already fetched " + link + ", skipping.")
                        continue

                    # Check if we've been asked to stop
                    if self.checkForStop():
                        return None

                    sf.debug("Fetching fresh content from: " + link)
                    time.sleep(self.opts['pause'])
                    freshLinks = self.processUrl(link)
                    if freshLinks != None:
                        links.update(freshLinks)

                    totalFetched += 1
                    if totalFetched >= self.opts['maxpages']:
                        sf.info("Maximum number of pages (" + str(self.opts['maxpages']) + \
                            ") reached.")
                        keepSpidering = False
                        break

            nextLinks = self.cleanLinks(links)
            sf.info("Found links: " + str(nextLinks))

            # We've scanned through another layer of the site
            levelsTraversed += 1
            sf.info("Now at traversal level: " + str(levelsTraversed))
            if levelsTraversed >= self.opts['maxlevels']:
                sf.info("Maximum number of levels (" + str(self.opts['maxlevels']) + \
                    ") reached.")
                keepSpidering = False

            # We've reached the end of our journey..
            if len(nextLinks) == 0:
                sf.info("No more links found to spider, finishing..")
                keepSpidering = False

            # We've been asked to stop scanning
            if self.checkForStop():
                keepSpidering = False

        return
# End of sfp_spider class

########NEW FILE########
__FILENAME__ = sfp_sslcert
#-------------------------------------------------------------------------------
# Name:         sfp_sslcert
# Purpose:      Gather information about SSL certificates behind HTTPS sites.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     23/08/2013
# Copyright:   (c) Steve Micallef
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import socket
import socks
import ssl
import time
import M2Crypto
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_sslcert(SpiderFootPlugin):
    """SSL:Gather information about SSL certificates used by the target's HTTPS sites."""

    # Default options
    opts = { 
        "tryhttp":  True,
        "ssltimeout":   5,
        "certexpiringdays": 30
    }

    # Option descriptions
    optdescs = { 
        "tryhttp":  "Also try to HTTPS-connect to HTTP sites and hostnames.",
        "ssltimeout":   "Seconds before giving up trying to HTTPS connect.",
        "certexpiringdays": "Number of days in the future a certificate expires to consider it as expiring."
    }

    # Be sure to completely clear any class variables in setup()
    # or you run the risk of data persisting between scan runs.

    # Target
    baseDomain = None # calculated from the URL in setup
    results = dict()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = dict()

        # Clear / reset any other class member variables here
        # or you risk them persisting between threads.

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    # * = be notified about all events.
    def watchedEvents(self):
        return ["SUBDOMAIN", "LINKED_URL_INTERNAL"]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "SSL_CERTIFICATE_ISSUED", "SSL_CERTIFICATE_ISSUER",
            "SSL_CERTIFICATE_MISMATCH", "SSL_CERTIFICATE_EXPIRED",
            "SSL_CERTIFICATE_EXPIRING", "SSL_CERTIFICATE_RAW" ]

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        if eventName == "LINKED_URL_INTERNAL":
            fqdn = sf.urlFQDN(eventData.lower())
        else:
            fqdn = eventData

        if not self.results.has_key(fqdn):
            self.results[fqdn] = True
        else:
            return None

        if not eventData.lower().startswith("https://") and not self.opts['tryhttp']:
            return None

        sf.debug("Testing SSL for: " + eventData)
        # Re-fetch the certificate from the site and process
        try:
            s = socket.socket()
            s.settimeout(int(self.opts['ssltimeout']))
            s.connect((fqdn, 443))
            sock = ssl.wrap_socket(s)
            sock.do_handshake()
            rawcert = sock.getpeercert(True)
            cert = ssl.DER_cert_to_PEM_cert(rawcert)
            m2cert = M2Crypto.X509.load_cert_string(cert)
        except BaseException as x:
            sf.info("Unable to SSL-connect to " + fqdn + ": " + str(x))
            return None

        # Generate the event for the raw cert (in text form)
        # Cert raw data text contains a lot of gems..
        rawevt = SpiderFootEvent("SSL_CERTIFICATE_RAW", m2cert.as_text(), self.__name__, event)
        self.notifyListeners(rawevt)

        # Generate events for other cert aspects
        self.getIssued(m2cert, event)
        self.getIssuer(m2cert, event)
        self.checkHostMatch(m2cert, fqdn, event)
        self.checkExpiry(m2cert, event)

    # Report back who the certificate was issued to
    def getIssued(self, cert, sevt):
        issued = cert.get_subject().as_text()
        evt = SpiderFootEvent("SSL_CERTIFICATE_ISSUED", issued, self.__name__, sevt)
        self.notifyListeners(evt)

    # Report back the certificate issuer
    def getIssuer(self, cert, sevt):
        issuer = cert.get_issuer().as_text()
        evt = SpiderFootEvent("SSL_CERTIFICATE_ISSUER", issuer, self.__name__, sevt)
        self.notifyListeners(evt)

    # Check if the hostname matches the name of the server
    def checkHostMatch(self, cert, fqdn, sevt):
        fqdn = fqdn.lower()
        hosts = ""

        # Extract the CN from the issued section
        issued = cert.get_subject().as_text()
        sf.debug("Checking for " + fqdn + " in " + issued.lower())
        if "cn=" + fqdn in issued.lower():
            hosts = 'dns:' + fqdn

        try:
            hosts = hosts + " " + cert.get_ext("subjectAltName").get_value().lower()
        except LookupError as e:
            sf.debug("No alternative name found in certificate.")

        fqdn_tld = ".".join(fqdn.split(".")[1:]).lower()
        if "dns:"+fqdn not in hosts and "dns:*."+fqdn_tld not in hosts:
            evt = SpiderFootEvent("SSL_CERTIFICATE_MISMATCH", hosts, self.__name__, sevt)
            self.notifyListeners(evt)

    # Check if the expiration date is in the future
    def checkExpiry(self, cert, sevt):
        exp = int(time.mktime(cert.get_not_after().get_datetime().timetuple()))
        expstr = cert.get_not_after().get_datetime().strftime("%Y-%m-%d %H:%M:%S")
        now = int(time.time())
        warnexp = now + self.opts['certexpiringdays'] * 86400

        if exp <= now:
            evt = SpiderFootEvent("SSL_CERTIFICATE_EXPIRED", expstr, self.__name__,
                sevt)
            self.notifyListeners(evt)
            return None
           
        if exp <= warnexp:
            evt = SpiderFootEvent("SSL_CERTIFICATE_EXPIRING", expstr, self.__name__,
                sevt)
            self.notifyListeners(evt)
            return None

# End of sfp_sslcert class

########NEW FILE########
__FILENAME__ = sfp_stor_print
#-------------------------------------------------------------------------------
# Name:         sfp_stor_print
# Purpose:      SpiderFoot plug-in for 'storing' events (by printing them to
#               the screen. This is used for debugging.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     06/04/2012
# Copyright:   (c) Steve Micallef 2012
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import re
from sflib import SpiderFoot, SpiderFootPlugin

# SpiderFoot standard lib (must be initialized in __init__)
sf = None

class sfp_stor_print(SpiderFootPlugin):
    # Default options
    opts = {
        'datasize':     100 # Number of characters to print from event data
    }

    # Option descriptions
    optdescs = {
        "datasize": "Maximum number of bytes to print on the screen for debug."
    }

    def __init__(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # Module description
    def descr(self):
        return "Debugging module for printing results instead of storing them."

    # What events is this module interested in for input
    def watchedEvents(self):
        return ["*"]

    # Handle events sent to this module
    def handleEvent(self, srcModuleName, eventName, eventSource, eventSourceEvent, eventData):
        sf.debug("RESULT:")
        sf.debug("\tSource: " + srcModuleName)
        sf.debug("\tEvent: " + eventName)
        sf.debug("\tEvent Source: " + eventSource)
        if len(eventData) > self.opts['datasize']:
            eventDataStripped = eventData[0:self.opts['datasize']] + '...'
        else:
            eventDataStripped = eventData
        sf.debug("\tEvent Data: " + eventDataStripped)

        return None

# End of sfp_stor_print class

########NEW FILE########
__FILENAME__ = sfp_strangeheaders
#-------------------------------------------------------------------------------
# Name:         sfp_strangeheaders
# Purpose:      SpiderFoot plug-in for identifying non-standard HTTP headers
#               in web server responses.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     01/12/2013
# Copyright:   (c) Steve Micallef 2013
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import re
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

# Standard headers, taken from http://en.wikipedia.org/wiki/List_of_HTTP_header_fields
headers = [ "access-control-allow-origin","accept-ranges","age","allow","cache-control",
"connection","content-encoding","content-language","content-length","content-location",
"content-md5","content-disposition","content-range","content-type","date","etag",
"expires","last-modified","link","location","p3p","pragma","proxy-authenticate",
"refresh","retry-after","server","set-cookie","status","strict-transport-security",
"trailer","transfer-encoding","vary","via","warning","www-authenticate",
"x-frame-options","x-xss-protection","content-security-policy","x-content-security-policy",
"x-webkit-csp","x-content-type-options","x-powered-by","x-ua-compatible" ]

class sfp_strangeheaders(SpiderFootPlugin):
    """Strange Headers:Obtain non-standard HTTP headers returned by web servers."""

    # Default options
    opts = { }

    # Target
    baseDomain = None # calculated from the URL in setup
    results = dict()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = dict()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return ["WEBSERVER_HTTPHEADERS"]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "WEBSERVER_STRANGEHEADER" ]

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data
        parentEvent = event.sourceEvent
        eventSource = event.sourceEvent.data

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)
        if self.results.has_key(eventSource):
            return None
        else:
            self.results[eventSource] = True

        if not sf.urlBaseUrl(eventSource).endswith(self.baseDomain):
            sf.debug("Not collecting header information for external sites.")
            return None

        for key in eventData:
            if key.lower() not in headers:
                val = key + ": " + eventData[key]
                evt = SpiderFootEvent("WEBSERVER_STRANGEHEADER", val, 
                    self.__name__, parentEvent)
                self.notifyListeners(evt)

# End of sfp_strangeheaders class

########NEW FILE########
__FILENAME__ = sfp_template
#-------------------------------------------------------------------------------
# Name:         sfp_XXX
# Purpose:      Description of the plug-in.
#
# Author:      Name and e-mail address
#
# Created:     Date
# Copyright:   (c) Name
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_XXX(SpiderFootPlugin):
    """Name:Description"""

    # Default options
    opts = { }

    # Option descriptions
    optdescs = {
        # For each option in opts you should have a key/value pair here
        # describing it. It will end up in the UI to explain the option
        # to the end-user.
    }

    # Be sure to completely clear any class variables in setup()
    # or you run the risk of data persisting between scan runs.

    # Target
    baseDomain = None # calculated from the URL in setup
    results = dict()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = dict()

        # Clear / reset any other class member variables here
        # or you risk them persisting between threads.

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    # * = be notified about all events.
    def watchedEvents(self):
        return ["*"]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return None

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data
        # If you are processing TARGET_WEB_CONTENT from sfp_spider, this is how you 
        # would get the source of that raw data (e.g. a URL.)
        eventSource = event.sourceEvent.data

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        # DO SOMETHING HERE

        # Notify other modules of what you've found
        evt = SpiderFootEvent("EVENT_CODE_HERE", "data here", self.__name__, event.sourceEvent)
        self.notifyListeners(evt)

        return None

    # If you intend for this module to act on its own (e.g. not solely rely
    # on events from other modules, then you need to have a start() method
    # and within that method call self.checkForStop() to see if you've been
    # politely asked by the controller to stop your activities (user abort.)

# End of sfp_XXX class

########NEW FILE########
__FILENAME__ = sfp_tldsearch
#-------------------------------------------------------------------------------
# Name:         sfp_tldsearch
# Purpose:      SpiderFoot plug-in for identifying the existence of this target
#               on other TLDs.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     31/08/2013
# Copyright:   (c) Steve Micallef 2013
# Licence:     GPL
#-------------------------------------------------------------------------------

import socket
import sys
import re
import time
import random
import threading
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_tldsearch(SpiderFootPlugin):
    """TLD Search:Search all Internet TLDs for domains with the same name as the target (this can be slow.)"""

    # Default options
    opts = {
        'activeonly':   True, # Only report domains that have content (try to fetch the page)
        'skipwildcards':    True,
        'maxthreads':   100
    }

    # Option descriptions
    optdescs = {
        'activeonly':   "Only report domains that have content (try to fetch the page)?",
        "skipwildcards":    "Skip TLDs and sub-TLDs that have wildcard DNS.",
        "maxthreads":   "Number of simultaneous DNS resolutions to perform at once."
    }

    # Internal results tracking
    results = list()

    # Target
    baseDomain = None

    # Track TLD search results between threads
    tldResults = dict()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = list()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return None

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "SIMILARDOMAIN" ]

    def tryTld(self, target):
        try:
            addrs = socket.gethostbyname_ex(target)
            self.tldResults[target] = True
        except BaseException as e:
            self.tldResults[target] = False

    def tryTldWrapper(self, tldList):
        self.tldResults = dict()
        running = True
        i = 0
        t = []

        # Spawn threads for scanning
        sf.info("Spawning threads to check TLDs: " + str(tldList))
        for tld in tldList:
            tn = 'sfp_tldsearch_' + str(random.randint(0,999999999))
            t.append(threading.Thread(name=tn, target=self.tryTld, args=(tld,)))
            t[i].start()
            i += 1

        # Block until all threads are finished
        while running:
            found = False
            for rt in threading.enumerate():
                if rt.name.startswith("sfp_tldsearch_"):
                    found = True

            if not found:
                running = False

        for res in self.tldResults.keys():
            if self.tldResults[res]:
                self.sendEvent(None, res)

    # Store the result internally and notify listening modules
    def sendEvent(self, source, result):
        if result == self.baseDomain:
            return

        sf.info("Found a TLD with the target's name: " + result)
        self.results.append(result)

        # Inform listening modules
        if self.opts['activeonly']:
            if self.checkForStop():
                return None

            pageContent = sf.fetchUrl('http://' + result,
                timeout=self.opts['_fetchtimeout'], useragent=self.opts['_useragent'])
            if pageContent['content'] != None:
                evt = SpiderFootEvent("SIMILARDOMAIN", result, self.__name__)
                self.notifyListeners(evt)
        else:
            evt = SpiderFootEvent("SIMILARDOMAIN", result, self.__name__)
            self.notifyListeners(evt)

    # Search for similar sounding domains
    def start(self):
        keyword = sf.domainKeyword(self.baseDomain, self.opts['_internettlds'])
        sf.debug("Keyword extracted from " + self.baseDomain + ": " + keyword)
        targetList = list()

        # Look through all TLDs for the existence of this target keyword
        for tld in self.opts['_internettlds']:
            if type(tld) != unicode:
                tld = unicode(tld.strip(), errors='ignore')
            else:
                tld = tld.strip()

            if tld.startswith("//") or len(tld) == 0:
                continue

            if tld.startswith("!") or tld.startswith("*") or tld.startswith(".."):
                continue

            if tld.endswith(".arpa"):
                continue

            if self.opts['skipwildcards'] and sf.checkDnsWildcard(tld):
                continue

            tryDomain = keyword + "." + tld

            if self.checkForStop():
                return None

            if len(targetList) <= self.opts['maxthreads']:
                targetList.append(tryDomain)
            else:
                self.tryTldWrapper(targetList)
                targetList = list()

        # Scan whatever may be left over.
        if len(targetList) > 0:
            self.tryTldWrapper(targetList)

        return None

# End of sfp_tldsearch class

########NEW FILE########
__FILENAME__ = sfp_virustotal
#-------------------------------------------------------------------------------
# Name:         sfp_virustotal
# Purpose:      Query VirusTotal for identified IP addresses.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     21/03/2014
# Copyright:   (c) Steve Micallef
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import json
import time
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_virustotal(SpiderFootPlugin):
    """VirusTotal:Obtain information from VirusTotal about identified IP addresses."""

    # Default options
    opts = { 
        "apikey":   "",
        "publicapi":    True,
        "checkcohosts": True,
        "checkaffiliates":  True
    }

    # Option descriptions
    optdescs = {
        "apikey":   "Your VirusTotal API Key.",
        "publicapi":    "Are you using a public key? If so SpiderFoot will pause for 15 seconds after each query to avoid VirusTotal dropping requests.",
        "checkcohosts": "Check co-hosted sites?",
        "checkaffiliates": "Check affiliates?"
    }

    # Be sure to completely clear any class variables in setup()
    # or you run the risk of data persisting between scan runs.

    # Target
    baseDomain = None # calculated from the URL in setup
    results = dict()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = dict()

        # Clear / reset any other class member variables here
        # or you risk them persisting between threads.

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return ["IP_ADDRESS", "AFFILIATE_IPADDR", 
            "AFFILIATE_DOMAIN", "CO_HOSTED_SITE"]

    # What events this module produces
    def producedEvents(self):
        return ["MALICIOUS_IPADDR", "MALICIOUS_SUBDOMAIN",
            "MALICIOUS_COHOST", "MALICIOUS_AFFILIATE",
            "MALICIOUS_AFFILIATE_IPADDR"]

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        if self.opts['apikey'] == "":
            sf.error("You enabled sfp_virustotal but did not set an API key!", False)
            return None

       # Don't look up stuff twice
        if self.results.has_key(eventData):
            sf.debug("Skipping " + eventData + " as already mapped.")
            return None
        else:
            self.results[eventData] = True

        if eventName.startswith("AFFILIATE") and not self.opts['checkaffiliates']:
            return None

        if eventName == 'CO_HOSTED_SITE' and not self.opts['checkcohosts']:
            return None

        if eventName in [ "AFFILIATE_DOMAIN", "CO_HOSTED_SITE" ]:
            url = "https://www.virustotal.com/vtapi/v2/domain/report?domain="
        else:
            url = "https://www.virustotal.com/vtapi/v2/ip-address/report?ip="

        res = sf.fetchUrl(url + eventData + "&apikey=" + self.opts['apikey'],
            timeout=self.opts['_fetchtimeout'], useragent="SpiderFoot")

        # Public API is limited to 4 queries per minute
        if self.opts['publicapi']:
            time.sleep(15)

        if res['content'] == None:
            sf.info("No VirusTotal info found for " + eventData)
            return None

        try:
            info = json.loads(res['content'])
        except Exception as e:
            sf.error("Error processing JSON response from VirusTotal.", False)
            return None

        if info.has_key('detected_urls'):
            sf.info("Found VirusTotal URL data for " + eventData)
            if eventName == "IP_ADDRESS":
                evt = "MALICIOUS_IPADDR"
                infotype = "ip-address"

            if eventName == "AFFILIATE_IPADDR":
                evt = "MALICIOUS_AFFILIATE_IPADDR"
                infotype = "ip-address"

            if eventName == "AFFILIATE_DOMAIN":
                evt = "MALICIOUS_AFFILIATE"
                infotype = "domain"

            if eventName == "CO_HOSTED_SITE":
                evt = "MALICIOUS_COHOST"
                infotype = "domain"

            infourl = "<SFURL>https://www.virustotal.com/en/" + infotype + "/" + \
                eventData + "/information/</SFURL>"

            # Notify other modules of what you've found
            e = SpiderFootEvent(evt, "VirusTotal [" + eventData + "]\n" + \
                infourl, self.__name__, event)
            self.notifyListeners(e)

    def start(self):
        if self.baseDomain in self.results.keys():
            return None
        else:
            self.results[self.baseDomain] = True

        url = "https://www.virustotal.com/vtapi/v2/domain/report?domain="
        res = sf.fetchUrl(url + self.baseDomain + "&apikey=" + self.opts['apikey'],
            timeout=self.opts['_fetchtimeout'], useragent="SpiderFoot")

        if res['code'] == 403:
            sf.error("VirusTotal API limit reached or invalid API key.", False)
            return None

        if res['content'] == None:
            sf.info("No VirusTotal info found for " + self.baseDomain)
            return None

        try:
            info = json.loads(res['content'])
        except Exception as e:
            sf.error("Error processing JSON response from VirusTotal.", False)
            return None

        if info.has_key('detected_urls'):
            infourl = "<SFURL>https://www.virustotal.com/en/domain/" + self.baseDomain + \
                "/information/</SFURL>"

            # Notify other modules of what you've found
            e = SpiderFootEvent("MALICIOUS_SUBDOMAIN", "VirusTotal [" + \
                self.baseDomain + "]\n" + infourl, self.__name__)
            self.notifyListeners(e)

# End of sfp_virustotal class

########NEW FILE########
__FILENAME__ = sfp_webframework
#-------------------------------------------------------------------------------
# Name:         sfp_webframework
# Purpose:      Identify the usage of popular web frameworks.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     25/05/2013
# Copyright:   (c) Steve Micallef 2013
# Licence:     GPL
#-------------------------------------------------------------------------------

import re
import sys
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

regexps = dict({
    "jQuery":           list(['jquery']), # unlikely false positive
    "YUI":              list(['\/yui\/', 'yui\-', 'yui\.']),
    "Prototype":        list(['\/prototype\/', 'prototype\-', 'prototype\.js']),
    "ZURB Foundation":  list(['\/foundation\/', 'foundation\-', 'foundation\.js']),
    "Bootstrap":        list(['\/bootstrap\/', 'bootstrap\-', 'bootstrap\.js']),
    "ExtJS":            list(['[\'\"\=]ext\.js', 'extjs', '\/ext\/*\.js']),
    "Mootools":         list(['\/mootools\/', 'mootools\-', 'mootools\.js']),
    "Dojo":             list(['\/dojo\/', '[\'\"\=]dojo\-', '[\'\"\=]dojo\.js']),
    "Wordpress":        list(['\/wp-includes\/', '\/wp-content\/'])
})

class sfp_webframework(SpiderFootPlugin):
    """Web Framework:Identify the usage of popular web frameworks like jQuery, YUI and others."""

    # Default options
    opts = { }

    # Option descriptions
    optdescs = {
        # For each option in opts you should have a key/value pair here
        # describing it. It will end up in the UI to explain the option
        # to the end-user.
    }

    # Target
    baseDomain = None # calculated from the URL in setup
    results = dict()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = dict()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    # * = be notified about all events.
    def watchedEvents(self):
        return ["TARGET_WEB_CONTENT"]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "URL_WEB_FRAMEWORK" ]

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data

        # We only want web content
        if srcModuleName != "sfp_spider":
            return None

        # If you are processing TARGET_WEB_CONTENT, this is how you would get the
        # source of that raw data (e.g. a URL.)
        eventSource = event.sourceEvent.data

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        if eventSource not in self.results.keys():
            self.results[eventSource] = list()

        # We only want web content for pages on the target site
        if not sf.urlBaseUrl(eventSource).endswith(self.baseDomain):
            sf.debug("Not collecting web content information for external sites.")
            return None

        for regexpGrp in regexps.keys():
            if regexpGrp in self.results[eventSource]:
                continue

            for regex in regexps[regexpGrp]:
                matches = re.findall(regex, eventData, re.IGNORECASE)
                if len(matches) > 0 and regexpGrp not in self.results[eventSource]:
                    sf.info("Matched " + regexpGrp + " in content from " + eventSource)
                    self.results[eventSource].append(regexpGrp)
                    evt = SpiderFootEvent("URL_WEB_FRAMEWORK", regexpGrp, 
                        self.__name__, event.sourceEvent)
                    self.notifyListeners(evt)

        return None

    # If you intend for this module to act on its own (e.g. not solely rely
    # on events from other modules, then you need to have a start() method
    # and within that method call self.checkForStop() to see if you've been
    # politely asked by the controller to stop your activities (user abort.)

# End of sfp_webframework class

########NEW FILE########
__FILENAME__ = sfp_websvr
#-------------------------------------------------------------------------------
# Name:         sfp_websvr
# Purpose:      SpiderFoot plug-in for scanning retreived content by other
#               modules (such as sfp_spider) and identifying web servers used
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     06/04/2012
# Copyright:   (c) Steve Micallef 2012
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import re
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_websvr(SpiderFootPlugin):
    """Web Server:Obtain web server banners to identify versions of web servers being used."""

    # Default options
    opts = { }

    # Target
    baseDomain = None # calculated from the URL in setup
    results = dict()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = dict()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return ["WEBSERVER_HTTPHEADERS"]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "WEBSERVER_BANNER", "WEBSERVER_TECHNOLOGY" ]

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data
        parentEvent = event.sourceEvent
        eventSource = event.sourceEvent.data

        sf.debug("Received event, " + eventName + ", from " + srcModuleName)
        if self.results.has_key(eventSource):
            return None
        else:
            self.results[eventSource] = True

        if not sf.urlBaseUrl(eventSource).endswith(self.baseDomain):
            sf.debug("Not collecting web server information for external sites.")
            return None

        # Could apply some smarts here, for instance looking for certain
        # banners and therefore classifying them further (type and version,
        # possibly OS. This could also trigger additional tests, such as 404s
        # and other errors to see what the header looks like.
        if eventData.has_key('server'):
            evt = SpiderFootEvent("WEBSERVER_BANNER", eventData['server'], 
                self.__name__, parentEvent)
            self.notifyListeners(evt)

            sf.info("Found web server: " + eventData['server'] + " (" + eventSource + ")")

        if eventData.has_key('x-powered-by'):
            evt = SpiderFootEvent("WEBSERVER_TECHNOLOGY", eventData['x-powered-by'], 
                self.__name__, parentEvent)
            self.notifyListeners(evt)
            return None

        tech = None
        if eventData.has_key('set-cookie') and 'PHPSESS' in eventData['set-cookie']:
            tech = "PHP"

        if eventData.has_key('set-cookie') and 'JSESSIONID' in eventData['set-cookie']:
            tech = "Java/JSP"

        if eventData.has_key('set-cookie') and 'ASP.NET' in eventData['set-cookie']:
            tech = "ASP.NET"

        if eventData.has_key('x-aspnet-version'):
            tech = "ASP.NET"

        if tech != None and '.jsp' in eventSource:
            tech = "Java/JSP"

        if tech != None and '.php' in eventSource:
            tech = "PHP"

        evt = SpiderFootEvent("WEBSERVER_TECHNOLOGY", tech, self.__name__, parentEvent)
        self.notifyListeners(evt)

# End of sfp_websvr class

########NEW FILE########
__FILENAME__ = sfp_yahoosearch
#-------------------------------------------------------------------------------
# Name:         sfp_yahoosearch
# Purpose:      Searches Yahoo for content related to the domain in question.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     12/04/2014
# Copyright:   (c) Steve Micallef 2014
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import random
import re
import time
import urllib
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

# SpiderFoot standard lib (must be initialized in setup)
sf = None

class sfp_yahoosearch(SpiderFootPlugin):
    """Yahoo:Some light Yahoo scraping to identify sub-domains and links."""

    # Default options
    opts = {
        'fetchlinks':   True,   # Should we fetch links on the base domain?
        'pages':        20      # Number of yahoo results pages to iterate
    }

    # Option descriptions
    optdescs = {
        'fetchlinks': "Fetch links found on the target domain-name?",
        'pages':    "Number of Yahoo results pages to iterate through."
    }

    # Target
    baseDomain = None
    results = list()

    def setup(self, sfc, target, userOpts=dict()):
        global sf

        sf = sfc
        self.baseDomain = target
        self.results = list()

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return None

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return [ "LINKED_URL_INTERNAL", "SEARCH_ENGINE_WEB_CONTENT", 
            "CO_HOSTED_SITE" ]

    def yahooCleaner(self, string):
        return " url=\"" + urllib.unquote(string.group(1)) + "\" "

    def start(self):
        # Sites hosted on the domain
        pages = sf.yahooIterate("site:" + self.baseDomain, dict(limit=self.opts['pages'],
            useragent=self.opts['_useragent'], timeout=self.opts['_fetchtimeout']))
        if pages == None:
            sf.info("No results returned from Yahoo.")
            return None

        for page in pages.keys():
            if page in self.results:
                continue
            else:
                self.results.append(page)

            # Check if we've been asked to stop
            if self.checkForStop():
                return None

            content = re.sub("RU=(.[^\/]+)\/RK=", self.yahooCleaner, pages[page])

            # Submit the yahoo results for analysis
            evt = SpiderFootEvent("SEARCH_ENGINE_WEB_CONTENT", content, self.__name__)
            self.notifyListeners(evt)

            # We can optionally fetch links to our domain found in the search
            # results. These may not have been identified through spidering.
            if self.opts['fetchlinks']:
                links = sf.parseLinks(page, content, self.baseDomain)
                if len(links) == 0:
                    continue

                for link in links:
                    if link in self.results:
                        continue
                    else:
                        self.results.append(link)
                    if sf.urlBaseUrl(link).endswith(self.baseDomain):
                        sf.debug("Found a link: " + link)
                        if self.checkForStop():
                            return None

                        evt = SpiderFootEvent("LINKED_URL_INTERNAL", link, self.__name__)
                        self.notifyListeners(evt)

# End of sfp_yahoosearch class

########NEW FILE########
__FILENAME__ = sfp__stor_db
#-------------------------------------------------------------------------------
# Name:         sfp_stor_db
# Purpose:      SpiderFoot plug-in for storing events to the local SpiderFoot
#               SQLite database.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     14/05/2012
# Copyright:   (c) Steve Micallef 2012
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import re
from sflib import SpiderFoot, SpiderFootPlugin

# SpiderFoot standard lib (must be initialized in setup)
sf = None
sfdb = None

class sfp__stor_db(SpiderFootPlugin):
    """Storage:Stores scan results into the back-end SpiderFoot database. You will need this."""

    # Default options
    opts = {
        'maxstorage':   1024 # max bytes for any piece of info stored (0 = unlimited)
    }

    # Option descriptions
    optdescs = {
        'maxstorage':   "Maximum bytes to store for any piece of information retreived (0 = unlimited.)"
    }

    def setup(self, sfc, target, userOpts=dict()):
        global sf
        global sfdb

        sf = sfc

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

        # Use the database handle passed to us
        # Should change to get the DBH out of sfc
        sfdb = userOpts['__sfdb__']

    # What events is this module interested in for input
    # Because this is a storage plugin, we are interested in everything so we
    # can store all events for later analysis.
    def watchedEvents(self):
        return ["*"]

    # Handle events sent to this module
    def handleEvent(self, sfEvent):
        if self.opts['maxstorage'] != 0:
            if len(sfEvent.data) > self.opts['maxstorage']:
                sf.debug("Storing an event: " + sfEvent.eventType)
                sfdb.scanEventStore(self.opts['__guid__'], sfEvent, self.opts['maxstorage'])
                return None
        
        sf.debug("Storing an event: " + sfEvent.eventType)
        sfdb.scanEventStore(self.opts['__guid__'], sfEvent)


# End of sfp__stor_db class

########NEW FILE########
__FILENAME__ = sf
#-------------------------------------------------------------------------------
# Name:         sf
# Purpose:      Main wrapper for calling all SpiderFoot modules
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     03/04/2012
# Copyright:   (c) Steve Micallef 2012
# Licence:     GPL
#-------------------------------------------------------------------------------

import sys
import os, inspect

# Look under ext ford 3rd party dependencies
cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile(inspect.currentframe()))[0],"ext")))
if cmd_subfolder not in sys.path:
    sys.path.insert(0, cmd_subfolder)

deps = [ 'M2Crypto', 'netaddr', 'dns', 'cherrypy', 'mako', 'socks', 
    'pyPdf', 'metapdf', 'openxmllib' ]
for mod in deps:
    try:
        if mod.startswith("ext."):
            modname = mod.split('.')
            __import__('ext', fromlist=[modname[1]])
        else:
            __import__(mod)
    except ImportError as e:
        print ""
        print "Critical Start-up Failure: " + str(e)
        print "================================="
        print "It appears you are missing a module required for SpiderFoot"
        print "to function. Please refer to the README file to get a list of"
        print "the dependencies and install them."
        print ""
        print "Python modules required are: "
        for mod in deps:
            print " - " + mod
        print ""
        print "If you are running on Windows and getting this error, please"
        print "report this as a bug to support@spiderfoot.net."
        print ""
        sys.exit(-1)

import imp
import time
import os
import cherrypy
from sflib import SpiderFoot
from sfwebui import SpiderFootWebUi

# 'Global' configuration options
# These can be overriden on a per-module basis, and some will
# be overridden from saved configuration settings stored in the DB.
sfConfig = {
    '_debug':            False, # Debug
    '__blocknotif':      False, # Block notifications
    '_useragent':        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0', # User-Agent to use for HTTP requests
    '_dnsserver':       '', # Override the default resolver
    '_fetchtimeout':     5, # number of seconds before giving up on a fetch
    '_internettlds':    'http://mxr.mozilla.org/mozilla-central/source/netwerk/dns/effective_tld_names.dat?raw=1',
    '_internettlds_cache':  72,
    '__database':        'spiderfoot.db',
    '__webaddr':         '127.0.0.1',
    '__webport':         5001,
    '__guid__':          None, # unique ID of scan. Will be set after start-up.
    '__modules__':       None, # List of modules. Will be set after start-up.
    '_socks1type':    '',
    '_socks2addr':    '',
    '_socks3port':    '',
    '_socks4user':    '',
    '_socks5pwd':     '',
    '_socks6dns':     True
}

sfOptdescs = {
    '_debug':       "Enable debugging?",
    '_internettlds':    "List of Internet TLDs.",
    '_internettlds_cache': "Hours to cache the Internet TLD list. This can safely be quite a long time given that the list doesn't change too often.",
    '_useragent':   "User-Agent string to use for HTTP requests. Prefix with an '@' to randomly select the User Agent from a file containing user agent strings for each request, e.g. @C:\useragents.txt or @/home/bob/useragents.txt. Or supply a URL to load the list from there.",
    '_dnsserver':   "Override the default resolver with another DNS server. For example, 8.8.8.8 is Google's open DNS server.",
    '_fetchtimeout':    "Number of seconds before giving up on a HTTP request.",
    '_socks1type':    "SOCKS Server Type. Can be '4', '5' or 'HTTP'",
    '_socks2addr':    'SOCKS Server IP Address.',
    '_socks3port':    'SOCKS Server TCP Port. Usually 1080 for 4/5 and 8080 for HTTP.',
    '_socks4user':    'SOCKS Username. Valid only for SOCKS4 and SOCKS5 servers.',
    '_socks5pwd':     "SOCKS Password. Valid only for SOCKS5 servers.",
    '_socks6dns':     "Pass DNS through the SOCKS proxy?",
    '_modulesenabled':  "Modules enabled for the scan." # This is a hack to get a description for
                                                         # an option not actually available.
}

if __name__ == '__main__':
    if len(sys.argv) > 1:
        (addr, port) = sys.argv[1].split(":")
        sfConfig['__webaddr'] = addr
        sfConfig['__webport'] = int(port)

    sf = SpiderFoot(sfConfig)
    sfModules = dict()

    # Go through each module in the modules directory with a .py extension
    for filename in os.listdir(sf.myPath() + '/modules/'):
        if filename.startswith("sfp_") and filename.endswith(".py"):
            # Skip the module template and debugging modules
            if filename == "sfp_template.py" or filename == 'sfp_stor_print.py':
                continue
            modName = filename.split('.')[0]

            # Load and instantiate the module
            sfModules[modName] = dict()
            mod = __import__('modules.' + modName, globals(), locals(), [modName])
            sfModules[modName]['object'] = getattr(mod, modName)()
            sfModules[modName]['name'] = sfModules[modName]['object'].__doc__.split(":",2)[0]
            sfModules[modName]['descr'] = sfModules[modName]['object'].__doc__.split(":",2)[1]
            sfModules[modName]['provides'] = sfModules[modName]['object'].producedEvents()
            sfModules[modName]['consumes'] = sfModules[modName]['object'].watchedEvents()
            if hasattr(sfModules[modName]['object'], 'opts'):
                sfModules[modName]['opts'] = sfModules[modName]['object'].opts
            if hasattr(sfModules[modName]['object'], 'optdescs'):
                sfModules[modName]['optdescs'] = sfModules[modName]['object'].optdescs

    if len(sfModules.keys()) < 1:
        print "No modules found in the modules directory."
        sys.exit(-1)

    # Add module info to sfConfig so it can be used by the UI
    sfConfig['__modules__'] = sfModules
    # Add descriptions of the global config options
    sfConfig['__globaloptdescs__'] = sfOptdescs

    # Start the web server so you can start looking at results
    print "Starting web server at http://" + sfConfig['__webaddr'] + \
        ":" + str(sfConfig['__webport']) + "..."

    cherrypy.config.update({
        'server.socket_host': sfConfig['__webaddr'],
        'server.socket_port': sfConfig['__webport']
    })

    # Disable auto-reloading of content
    cherrypy.engine.autoreload.unsubscribe()

    # Enable access to static files via the web directory
    currentDir = os.path.abspath(sf.myPath())
    conf = { '/static': { 
        'tools.staticdir.on': True,
        'tools.staticdir.dir': os.path.join(currentDir, 'static')
    }}
                        
    # Try starting the web server. If it fails due to a database being
    # missing, start a smaller web server just for setting up the DB.
    cherrypy.quickstart(SpiderFootWebUi(sfConfig), config=conf)

########NEW FILE########
__FILENAME__ = sfdb
#-------------------------------------------------------------------------------
# Name:         sfdb
# Purpose:      Common functions for working with the database back-end.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     15/05/2012
# Copyright:   (c) Steve Micallef 2012
# Licence:     GPL
#-------------------------------------------------------------------------------

import hashlib
import random
import sqlite3
import sys
import time
from sflib import SpiderFoot

# SpiderFoot class passed to us
sf = None

class SpiderFootDb:
    # Queries for creating the SpiderFoot database
    createQueries = [
            "PRAGMA journal_mode=WAL",
            "CREATE TABLE tbl_event_types ( \
                event       VARCHAR NOT NULL PRIMARY KEY, \
                event_descr VARCHAR NOT NULL, \
                event_raw   INT NOT NULL DEFAULT 0 \
            )",
            "CREATE TABLE tbl_config ( \
                scope   VARCHAR NOT NULL, \
                opt     VARCHAR NOT NULL, \
                val     VARCHAR NOT NULL, \
                PRIMARY KEY (scope, opt) \
            )",
            "CREATE TABLE tbl_scan_instance ( \
                guid        VARCHAR NOT NULL PRIMARY KEY, \
                name        VARCHAR NOT NULL, \
                seed_target VARCHAR NOT NULL, \
                created     INT DEFAULT 0, \
                started     INT DEFAULT 0, \
                ended       INT DEFAULT 0, \
                status      VARCHAR NOT NULL \
            )",
            "CREATE TABLE tbl_scan_log ( \
                scan_instance_id    VARCHAR NOT NULL REFERENCES tbl_scan_instance(guid), \
                generated           INT NOT NULL, \
                component           VARCHAR, \
                type                VARCHAR NOT NULL, \
                message             VARCHAR \
            )",
            "CREATE TABLE tbl_scan_config ( \
                scan_instance_id    VARCHAR NOT NULL REFERENCES tbl_scan_instance(guid), \
                component           VARCHAR NOT NULL, \
                opt                 VARCHAR NOT NULL, \
                val                 VARCHAR NOT NULL \
            )",
            "CREATE TABLE tbl_scan_results ( \
                scan_instance_id    VARCHAR NOT NULL REFERENCES tbl_scan_instance(guid), \
                hash                VARCHAR NOT NULL, \
                type                VARCHAR NOT NULL REFERENCES tbl_event_types(event), \
                generated           INT NOT NULL, \
                confidence          INT NOT NULL DEFAULT 100, \
                visibility          INT NOT NULL DEFAULT 100, \
                risk                INT NOT NULL DEFAULT 0, \
                module              VARCHAR NOT NULL, \
                data                VARCHAR, \
                source_event_hash  VARCHAR DEFAULT 'ROOT' \
            )",
            "CREATE INDEX idx_scan_results_id ON tbl_scan_results (scan_instance_id)",
            "CREATE INDEX idx_scan_results_type ON tbl_scan_results (scan_instance_id, type)",
            "CREATE INDEX idx_scan_results_hash ON tbl_scan_results (scan_instance_id, hash)",
            "CREATE INDEX idx_scan_results_srchash ON tbl_scan_results (scan_instance_id, source_event_hash)",
            "CREATE INDEX idx_scan_logs ON tbl_scan_log (scan_instance_id)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('AFFILIATE', 'Affiliate - Hostname', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('AFFILIATE_DOMAIN', 'Affiliate - Domain', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('AFFILIATE_IPADDR', 'Affiliate - IP Address', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('AFFILIATE_IP_SUBNET', 'Affiliate - IP Address - Subnet', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('AFFILIATE_WEB_CONTENT', 'Affiliate - Web Content', 1)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('BGP_AS', 'BGP AS Ownership', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('BLACKLISTED_IPADDR', 'Blacklisted IP Address', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('BLACKLISTED_AFFILIATE_IPADDR', 'Blacklisted Affiliate IP Address', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('CO_HOSTED_SITE', 'Co-Hosted Site', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('DEFACED', 'Defaced', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('DEFACED_IPADDR', 'Defaced IP Address', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('DEFACED_AFFILIATE', 'Defaced Affiliate', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('DEFACED_AFFILIATE_IPADDR', 'Defaced Affiliate IP Address', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('DEFACED_COHOST', 'Defaced Co-Hosted Site', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('DEVICE_TYPE', 'Device Type', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('DOMAIN_NAME', 'Domain Name', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('EMAILADDR', 'Email Address', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('GEOINFO', 'Physical Location', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('HTTP_CODE', 'HTTP Status Code', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('HUMAN_NAME', 'Human Name', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('INITIAL_TARGET', 'User-Supplied Target', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('INTERESTING_FILE', 'Interesting File', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('IP_ADDRESS', 'IP Address', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('IP_SUBNET', 'IP Address - Subnet', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('NETBLOCK', 'Netblock Ownership', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('MALICIOUS_ASN', 'Malicious AS', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('MALICIOUS_IPADDR', 'Malicious IP Address', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('MALICIOUS_COHOST', 'Malicious Co-Hosted Site', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('MALICIOUS_DOMAIN_NAME', 'Malicious Domain Name', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('MALICIOUS_SUBDOMAIN', 'Malicious Sub-domain/Host', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('MALICIOUS_AFFILIATE', 'Malicious Affiliate', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('MALICIOUS_AFFILIATE_IPADDR', 'Malicious Affiliate IP Address', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('MALICIOUS_NETBLOCK', 'Owned Netblock with Malicious IP', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('MALICIOUS_SUBNET', 'Malicious IP on Same Subnet', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('LINKED_URL_INTERNAL', 'Linked URL - Internal', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('LINKED_URL_EXTERNAL', 'Linked URL - External', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('OPERATING_SYSTEM', 'Operating System', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('PASTEBIN_CONTENT', 'PasteBin Content', 1)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('PROVIDER_DNS', 'Name Server (DNS ''NS'' Records)', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('PROVIDER_INTERNET', 'Internet Service Provider', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('PROVIDER_MAIL', 'Email Gateway (DNS ''MX'' Records)', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('PROVIDER_JAVASCRIPT', 'Externally Hosted Javascript', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('RAW_RIR_DATA', 'Raw Data from RIRs', 1)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('RAW_DNS_RECORDS', 'Raw DNS Records', 1)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('RAW_FILE_META_DATA', 'Raw File Meta Data', 1)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('SEARCH_ENGINE_WEB_CONTENT', 'Search Engine''s Web Content', 1)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('SOCIAL_MEDIA', 'Social Media Presence', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('SUBDOMAIN', 'Sub-domain/Hostname', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('SIMILARDOMAIN', 'Similar Domain', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('SSL_CERTIFICATE_ISSUED', 'SSL Certificate - Issued to', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('SSL_CERTIFICATE_ISSUER', 'SSL Certificate - Issued by', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('SSL_CERTIFICATE_MISMATCH', 'SSL Certificate Host Mismatch', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('SSL_CERTIFICATE_EXPIRED', 'SSL Certificate Expired', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('SSL_CERTIFICATE_EXPIRING', 'SSL Certificate Expiring', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('SSL_CERTIFICATE_RAW', 'SSL Certificate - Raw Data', 1)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('TARGET_WEB_CONTENT', 'Web Content', 1)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('TARGET_WEB_COOKIE', 'Cookies', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('TCP_PORT_OPEN', 'Open TCP Port', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('TCP_PORT_OPEN_BANNER', 'Open TCP Port Banner', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('URL_FORM', 'URL (Form)', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('URL_FLASH', 'URL (Uses Flash)', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('URL_JAVASCRIPT', 'URL (Uses Javascript)', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('URL_WEB_FRAMEWORK', 'URL (Uses a Web Framework)', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('URL_JAVA_APPLET', 'URL (Uses Java applet)', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('URL_STATIC', 'URL (Purely Static)', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('URL_PASSWORD', 'URL (Accepts Passwords)', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('URL_UPLOAD', 'URL (Accepts Uploads)', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('WEBSERVER_BANNER', 'Web Server', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('WEBSERVER_HTTPHEADERS', 'HTTP Headers', 1)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('WEBSERVER_STRANGEHEADER', 'Non-Standard HTTP Header', 0)",
            "INSERT INTO tbl_event_types (event, event_descr, event_raw) VALUES ('WEBSERVER_TECHNOLOGY', 'Web Technology', 0)"
    ]

    def __init__(self, opts):
        global sf
        sf = SpiderFoot(opts)

        # connect() will create the database file if it doesn't exist, but
        # at least we can use this opportunity to ensure we have permissions to
        # read and write to such a file.
        dbh = sqlite3.connect(sf.myPath() + "/" + opts['__database'], timeout=10)
        if dbh == None:
            sf.fatal("Could not connect to internal database, and couldn't create " + \
                opts['__database'])
        dbh.text_factory = str

        self.conn = dbh
        self.dbh = dbh.cursor()

        # Now we actually check to ensure the database file has the schema set
        # up correctly.
        try:
            self.dbh.execute('SELECT COUNT(*) FROM tbl_scan_config')
        except sqlite3.Error:
            # .. If not set up, we set it up.
            try:
                self.create()
            except BaseException as e:
                sf.error("Tried to set up the SpiderFoot database schema, but failed: " + \
                    e.args[0])
        return

    #
    # Back-end database operations
    #

    # Create the back-end schema
    def create(self):
        try:
            for qry in self.createQueries:
                self.dbh.execute(qry)
            self.conn.commit()
        except sqlite3.Error as e:
            raise BaseException("SQL error encountered when setting up database: " +
                e.args[0])

    # Close the database handle
    def close(self):
        self.dbh.close()

    # Get event types
    def eventTypes(self):
        qry = "SELECT event_descr, event, event_raw FROM tbl_event_types"
        try:
            self.dbh.execute(qry)
            return self.dbh.fetchall()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when retreiving event types:" +
                e.args[0])

    # Log an event to the database
    def scanLogEvent(self, instanceId, classification, message, component=None):
        if component == None:
            component = "SpiderFoot"

        qry = "INSERT INTO tbl_scan_log \
            (scan_instance_id, generated, component, type, message) \
            VALUES (?, ?, ?, ?, ?)"
        try:
            self.dbh.execute(qry, (
                    instanceId, time.time() * 1000, component, classification, message
                ))
            self.conn.commit()
        except sqlite3.Error as e:
            if "locked" in e.args[0]:
                # TODO: Do something smarter here to handle locked databases
                sf.fatal("Unable to log event in DB: " + e.args[0])
            else:
                sf.fatal("Unable to log event in DB: " + e.args[0])

        return True

    # Generate an globally unique ID for this scan
    def scanInstanceGenGUID(self, scanName):
        hashStr = hashlib.sha256(
                scanName +
                str(time.time() * 1000) +
                str(random.randint(100000, 999999))
            ).hexdigest()
        return hashStr

    # Store a scan instance
    def scanInstanceCreate(self, instanceId, scanName, scanTarget):
        qry = "INSERT INTO tbl_scan_instance \
            (guid, name, seed_target, created, status) \
            VALUES (?, ?, ?, ?, ?)"
        try:
            self.dbh.execute(qry, (
                    instanceId, scanName, scanTarget, time.time() * 1000, 'CREATED'
                ))
            self.conn.commit()
        except sqlite3.Error as e:
            sf.fatal("Unable to create instance in DB: " + e.args[0])

        return True

    # Update the start time, end time or status (or all 3) of a scan instance
    def scanInstanceSet(self, instanceId, started=None, ended=None, status=None):
        qvars = list()
        qry = "UPDATE tbl_scan_instance SET "

        if started != None:
            qry += " started = ?,"
            qvars.append(started)

        if ended != None:
            qry += " ended = ?,"
            qvars.append(ended)

        if status != None:
            qry += " status = ?,"
            qvars.append(status)

        # guid = guid is a little hack to avoid messing with , placement above
        qry += " guid = guid WHERE guid = ?"
        qvars.append(instanceId)

        try:
            self.dbh.execute(qry, qvars)
            self.conn.commit()
        except sqlite3.Error:
            sf.fatal("Unable to set information for the scan instance.")

    # Return info about a scan instance (name, target, created, started,
    # ended, status) - don't need this yet - untested
    def scanInstanceGet(self, instanceId):
        qry = "SELECT name, seed_target, ROUND(created/1000) AS created, \
            ROUND(started/1000) AS started, ROUND(ended/1000) AS ended, status \
            FROM tbl_scan_instance WHERE guid = ?"
        qvars = [instanceId]
        try:
            self.dbh.execute(qry, qvars)
            return self.dbh.fetchone()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when retreiving scan instance:" +
                e.args[0])

    # Obtain a summary of the results per event type
    def scanResultSummary(self, instanceId):
        qry = "SELECT r.type, e.event_descr, MAX(ROUND(generated)) AS last_in, \
            count(*) AS total, count(DISTINCT r.data) as utotal FROM \
            tbl_scan_results r, tbl_event_types e WHERE e.event = r.type \
            AND r.scan_instance_id = ? GROUP BY r.type ORDER BY e.event_descr"
        qvars = [instanceId]
        try:
            self.dbh.execute(qry, qvars)
            return self.dbh.fetchall()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when fetching result summary: " +
                e.args[0])

    # Obtain the data for a scan and event type
    def scanResultEvent(self, instanceId, eventType='ALL'):
        qry = "SELECT ROUND(c.generated) AS generated, c.data, \
            s.data as 'source_data', \
            c.module, c.type, c.confidence, c.visibility, c.risk, c.hash, \
            c.source_event_hash, t.event_descr \
            FROM tbl_scan_results c, tbl_scan_results s, tbl_event_types t \
            WHERE c.scan_instance_id = ? AND c.source_event_hash = s.hash AND \
            s.scan_instance_id = c.scan_instance_id AND \
            t.event = c.type"

        qvars = [instanceId]

        if eventType != "ALL":
            qry = qry + " AND c.type = ?"
            qvars.append(eventType)

        qry = qry + " ORDER BY c.data"

        #print "QRY: " + qry

        try:
            self.dbh.execute(qry, qvars)
            return self.dbh.fetchall()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when fetching result events: " +
                e.args[0])

    # Obtain a unique list of elements
    def scanResultEventUnique(self, instanceId, eventType='ALL'):
        qry = "SELECT DISTINCT data, type, COUNT(*) FROM tbl_scan_results \
            WHERE scan_instance_id = ?"
        qvars = [instanceId]

        if eventType != "ALL":
            qry = qry + " AND type = ?"
            qvars.append(eventType)

        qry = qry + " GROUP BY type, data ORDER BY COUNT(*)"

        try:
            self.dbh.execute(qry, qvars)
            return self.dbh.fetchall()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when fetching unique result events: " +
                e.args[0])

    # Get scan logs
    def scanLogs(self, instanceId, limit=None):
        qry = "SELECT generated AS generated, component, \
            type, message FROM tbl_scan_log WHERE scan_instance_id = ? \
            ORDER BY generated DESC"
        qvars = [instanceId]

        if limit != None:
            qry = qry + " LIMIT ?"
            qvars.append(limit)

        try:
            self.dbh.execute(qry, qvars)
            return self.dbh.fetchall()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when fetching scan logs: " +
                e.args[0])

    # Get scan errors
    def scanErrors(self, instanceId, limit=None):
        qry = "SELECT generated AS generated, component, \
            message FROM tbl_scan_log WHERE scan_instance_id = ? \
            AND type = 'ERROR' ORDER BY generated DESC"
        qvars = [instanceId]

        if limit != None:
            qry = qry + " LIMIT ?"
            qvars.append(limit)

        try:
            self.dbh.execute(qry, qvars)
            return self.dbh.fetchall()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when fetching scan errors: " +
                e.args[0])

    # Delete a scan instance
    def scanInstanceDelete(self, instanceId):
        qry1 = "DELETE FROM tbl_scan_instance WHERE guid = ?"
        qry2 = "DELETE FROM tbl_scan_config WHERE scan_instance_id = ?"
        qry3 = "DELETE FROM tbl_scan_results WHERE scan_instance_id = ?"
        qry4 = "DELETE FROM tbl_scan_log WHERE scan_instance_id = ?"
        qvars = [instanceId]
        try:
            self.dbh.execute(qry1, qvars)
            self.dbh.execute(qry2, qvars)
            self.dbh.execute(qry3, qvars)
            self.dbh.execute(qry4, qvars)
            self.conn.commit()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when deleting scan: " +
                e.args[0])

    # Store the default configuration
    def configSet(self, optMap=dict()):
        qry = "REPLACE INTO tbl_config (scope, opt, val) VALUES (?, ?, ?)"
        for opt in optMap.keys():
            # Module option
            if ":" in opt:
                parts = opt.split(':')
                qvals = [ parts[0], parts[1], optMap[opt] ]
            else:
            # Global option
                qvals = [ "GLOBAL", opt, optMap[opt] ]

            try:
                self.dbh.execute(qry, qvals)
            except sqlite3.Error as e:
                sf.error("SQL error encountered when storing config, aborting: " +
                    e.args[0])

            self.conn.commit()

    # Retreive the config from the database
    def configGet(self):
        qry = "SELECT scope, opt, val FROM tbl_config"
        try:
            retval = dict()
            self.dbh.execute(qry)
            for [scope, opt, val] in self.dbh.fetchall():
                if scope == "GLOBAL":
                    retval[opt] = val
                else:
                    retval[scope + ":" + opt] = val

            return retval
        except sqlite3.Error as e:
            sf.error("SQL error encountered when fetching configuration: " + e.args[0])

    # Reset the config to default (clear it from the DB and let the hard-coded
    # settings in the code take effect.)
    def configClear(self):
        qry = "DELETE from tbl_config"
        try:
            self.dbh.execute(qry)
            self.conn.commit()
        except sqlite3.Error as e:
            sf.error("Unable to clear configuration from the database: " + e.args[0])

    # Store a configuration value for a scan
    def scanConfigSet(self, id, optMap=dict()):
        qry = "REPLACE INTO tbl_scan_config \
                (scan_instance_id, component, opt, val) VALUES (?, ?, ?, ?)"

        for opt in optMap.keys():
            # Module option
            if ":" in opt:
                parts = opt.split(':')
                qvals = [ id, parts[0], parts[1], optMap[opt] ]
            else:
            # Global option
                qvals = [ id, "GLOBAL", opt, optMap[opt] ]

            try:
                self.dbh.execute(qry, qvals)
            except sqlite3.Error as e:
                sf.error("SQL error encountered when storing config, aborting: " +
                    e.args[0])

            self.conn.commit()

    # Retreive configuration data for a scan component
    def scanConfigGet(self, instanceId):
        qry = "SELECT component, opt, val FROM tbl_scan_config \
                WHERE scan_instance_id = ? ORDER BY component, opt"
        qvars = [instanceId]
        try:
            retval = dict()
            self.dbh.execute(qry, qvars)
            for [component, opt, val] in self.dbh.fetchall():
                if component == "GLOBAL":
                    retval[opt] = val
                else:
                    retval[component + ":" + opt] = val
            return retval
        except sqlite3.Error as e:
            sf.error("SQL error encountered when fetching configuration: " + e.args[0])

    # Store an event
    # eventData is a SpiderFootEvent object with the following variables:
    # - eventType: the event, e.g. URL_FORM, RAW_DATA, etc.
    # - generated: time the event occurred
    # - confidence: how sure are we of this data's validity, 0-100
    # - visibility: how 'visible' was this data, 0-100
    # - risk: how much risk does this data represent, 0-100
    # - module: module that generated the event
    # - data: the actual data, i.e. a URL, port number, webpage content, etc.
    # - sourceEventHash: hash of the event that triggered this event
    # And getHash() will return the event hash.
    def scanEventStore(self, instanceId, sfEvent, truncateSize=0):
        storeData = ''

        if type(sfEvent.data) is not unicode:
            # If sfEvent.data is a dict or list, convert it to a string first, as
            # those types do not have a unicode converter.
            if type(sfEvent.data) is str:
                storeData = unicode(sfEvent.data, 'utf-8', errors='replace')
            else:
                try:
                    storeData = unicode(str(sfEvent.data), 'utf-8', errors='replace')
                except BaseException as e:
                    sf.fatal("Unhandled type detected: " + str(type(sfEvent.data)))
        else:
            storeData = sfEvent.data

        if truncateSize > 0:
            storeData = storeData[0:truncateSize]

        qry = "INSERT INTO tbl_scan_results \
            (scan_instance_id, hash, type, generated, confidence, \
            visibility, risk, module, data, source_event_hash) \
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        qvals = [ instanceId, sfEvent.getHash(), sfEvent.eventType, sfEvent.generated,
            sfEvent.confidence, sfEvent.visibility, sfEvent.risk,
            sfEvent.module, storeData, sfEvent.sourceEventHash ]

        #print "STORING: " + str(qvals)

        try:
            self.dbh.execute(qry, qvals)
            self.conn.commit()
            return None
        except sqlite3.Error as e:
            sf.fatal("SQL error encountered when storing event data (" + str(self.dbh) + ": " +
                e.args[0])

    # List of all previously run scans
    def scanInstanceList(self):
        # SQLite doesn't support OUTER JOINs, so we need a work-around that
        # does a UNION of scans with results and scans without results to 
        # get a complete listing.
        qry = "SELECT i.guid, i.name, i.seed_target, ROUND(i.created/1000), \
            ROUND(i.started)/1000 as started, ROUND(i.ended)/1000, i.status, COUNT(r.type) \
            FROM tbl_scan_instance i, tbl_scan_results r WHERE i.guid = r.scan_instance_id \
            GROUP BY i.guid \
            UNION ALL \
            SELECT i.guid, i.name, i.seed_target, ROUND(i.created/1000), \
            ROUND(i.started)/1000 as started, ROUND(i.ended)/1000, i.status, '0' \
            FROM tbl_scan_instance i  WHERE i.guid NOT IN ( \
            SELECT distinct scan_instance_id FROM tbl_scan_results) \
            ORDER BY started DESC"
        try:
            self.dbh.execute(qry)
            return self.dbh.fetchall()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when fetching scan list: " + e.args[0])

    # History of data from the scan
    def scanResultHistory(self, instanceId):
        qry = "SELECT STRFTIME('%H:%M %w', generated, 'unixepoch') AS hourmin, \
                type, COUNT(*) FROM tbl_scan_results \
                WHERE scan_instance_id = ? GROUP BY hourmin, type"
        qvars = [instanceId]
        try:
            self.dbh.execute(qry, qvars)
            return self.dbh.fetchall()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when fetching scan history: " + e.args[0])


    # Get the source IDs, types and data for a set of IDs
    def scanElementSources(self, instanceId, elementIdList):
        # the output of this needs to be aligned with scanResultEvent,
        # as other functions call both expecting the same output.
        qry = "SELECT ROUND(c.generated) AS generated, c.data, \
            s.data as 'source_data', \
            c.module, c.type, c.confidence, c.visibility, c.risk, c.hash, \
            c.source_event_hash, t.event_descr \
            FROM tbl_scan_results c, tbl_scan_results s, tbl_event_types t \
            WHERE c.scan_instance_id = ? AND c.source_event_hash = s.hash AND \
            s.scan_instance_id = c.scan_instance_id AND \
            t.event = c.type AND c.hash in ("
        qvars = [instanceId]

        for hashId in elementIdList:
            qry = qry + "'" + hashId + "',"
        qry = qry + "'')"

        try:
            self.dbh.execute(qry, qvars)
            return self.dbh.fetchall()
        except sqlite3.Error as e:
            sf.error("SQL error encountered when getting source element IDs: " + e.args[0])



########NEW FILE########
__FILENAME__ = sflib
#-------------------------------------------------------------------------------
# Name:         sflib
# Purpose:      Common functions used by SpiderFoot modules.
#               Also defines the SpiderFootPlugin abstract class for modules.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     26/03/2012
# Copyright:   (c) Steve Micallef 2012
# Licence:     GPL
#-------------------------------------------------------------------------------

import inspect
import hashlib
import gzip
import re
import os
import random
import socket
import sys
import time
import urllib2
import StringIO

class SpiderFoot:
    dbh = None
    scanGUID = None

    # 'options' is a dictionary of options which changes the behaviour
    # of how certain things are done in this module
    # 'handle' will be supplied if the module is being used within the
    # SpiderFoot GUI, in which case all feedback should be fed back
    def __init__(self, options, handle=None):
        self.handle = handle
        self.opts = options

    # Bit of a hack to support SOCKS because of the loading order of
    # modules. sfscan will call this to update the socket reference
    # to the SOCKS one.
    def updateSocket(self, sock):
        socket = sock
        urllib2.socket = sock

    # Supplied an option value, return the data based on what the
    # value is. If val is a URL, you'll get back the fetched content,
    # if val is a file path it will be loaded and get back the contents,
    # and if a string it will simply be returned back.
    def optValueToData(self, val, fatal=True, splitLines=True):
        if val.startswith('@'):
            fname = val.split('@')[1]
            try:
                self.info("Loading configuration data from: " + fname)
                f = open(fname, "r")
                if splitLines:
                    arr = f.readlines()
                    ret = list()
                    for x in arr:
                        ret.append(x.rstrip('\n'))
                else:
                    ret = f.read()
                return ret
            except BaseException as b:
                if fatal:
                    self.error("Unable to open option file, " + fname + ".")
                else:
                    return None

        if val.lower().startswith('http://') or val.lower().startswith('https://'):
            try:
                self.info("Downloading configuration data from: " + val)
                res = urllib2.urlopen(val)
                data = res.read()
                if splitLines:
                    return data.splitlines()
                else:
                    return data
            except BaseException as e:
                if fatal:
                    self.error("Unable to open option URL, " + val + ".")
                else:
                    return None

        return val

    # Called usually some time after instantiation
    # to set up a database handle and scan GUID, used
    # for logging events to the database about a scan.
    def setDbh(self, handle):
        self.dbh = handle

    def setScanId(self, id):
        self.scanGUID = id

    def _dblog(self, level, message, component=None):
        return self.dbh.scanLogEvent(self.scanGUID, level, message, component)

    def error(self, error, exception=True):
        if self.dbh == None:
            print '[Error] ' + error
        else:
            self._dblog("ERROR", error)
        if exception:
            raise BaseException("Internal Error Encountered: " + error)

    def fatal(self, error):
        if self.dbh == None:
            print '[Fatal] ' + error
        else:
            self._dblog("FATAL", error)
        exit(-1)

    def status(self, message):
        if self.dbh == None:
            print "[Status] " + message
        else:
            self._dblog("STATUS", message)

    def info(self, message):
        frm = inspect.stack()[1]
        mod = inspect.getmodule(frm[0])

        if mod == None:
            modName = "Unknown"
        else:
            modName = mod.__name__

        if self.dbh == None:
            print '[' + modName + '] ' + message
        else:
            self._dblog("INFO", message, modName)
        return

    def debug(self, message):
        if self.opts['_debug'] == False:
            return
        frm = inspect.stack()[1]
        mod = inspect.getmodule(frm[0])

        if mod == None:
            modName = "Unknown"
        else:
            modName = mod.__name__

        if self.dbh == None:
            print '[' + modName + '] ' + message
        else:
            self._dblog("DEBUG", message, modName)
        return

    def myPath(self):
        # This will get us the program's directory, even if we are frozen using py2exe.

        # Determine whether we've been compiled by py2exe
        if hasattr(sys, "frozen"):
            return os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding()))

        return os.path.dirname(unicode(__file__, sys.getfilesystemencoding()))

    #
    # Caching
    #

    # Return the cache path
    def cachePath(self):
        path = self.myPath() + '/cache'
        if not os.path.isdir(path):
            os.mkdir(path)
        return path

    # Store data to the cache
    def cachePut(self, label, data):
        pathLabel = hashlib.sha224(label).hexdigest()
        cacheFile = self.cachePath() + "/" + pathLabel
        fp = file(cacheFile, "w")
        if type(data) is list:
            for line in data:
                fp.write(line + '\n')
        else:
            data = data.encode('utf-8')
            fp.write(data)
        fp.close()

    # Retreive data from the cache
    def cacheGet(self, label, timeoutHrs):
        pathLabel = hashlib.sha224(label).hexdigest()
        cacheFile = self.cachePath() + "/" + pathLabel
        try:
            (m, i, d, n, u, g, sz, atime, mtime, ctime) = os.stat(cacheFile)

            if sz == 0:
                return None

            if mtime > time.time() - timeoutHrs*3600 or timeoutHrs == 0:
                fp = file(cacheFile, "r")
                fileContents = fp.read()
                fp.close()
                fileContents = fileContents.decode('utf-8')
                return fileContents
            else:
                return None
        except BaseException as e:
            return None

    #
    # Configuration process
    #

    # Convert a Python dictionary to something storable
    # in the database.
    def configSerialize(self, opts, filterSystem=True):
        storeopts = dict()

        for opt in opts.keys():
            # Filter out system temporary variables like GUID and others
            if opt.startswith('__') and filterSystem:
                continue

            if type(opts[opt]) is int or type(opts[opt]) is str:
                storeopts[opt] = opts[opt]

            if type(opts[opt]) is bool:
                if opts[opt]:
                    storeopts[opt] = 1
                else:
                    storeopts[opt] = 0
            if type(opts[opt]) is list:
                storeopts[opt] = ','.join(opts[opt])

        if not opts.has_key('__modules__'):
            return storeopts

        for mod in opts['__modules__']:
            for opt in opts['__modules__'][mod]['opts']:
                if opt.startswith('_') and filterSystem:
                    continue

                if type(opts['__modules__'][mod]['opts'][opt]) is int or \
                    type(opts['__modules__'][mod]['opts'][opt]) is str:
                    storeopts[mod + ":" + opt] = opts['__modules__'][mod]['opts'][opt]

                if type(opts['__modules__'][mod]['opts'][opt]) is bool:
                    if opts['__modules__'][mod]['opts'][opt]:
                        storeopts[mod + ":" + opt] = 1
                    else:
                        storeopts[mod + ":" + opt] = 0
                if type(opts['__modules__'][mod]['opts'][opt]) is list:
                    storeopts[mod + ":" + opt] = ','.join(str(x) \
                        for x in opts['__modules__'][mod]['opts'][opt])

        return storeopts
    
    # Take strings, etc. from the database or UI and convert them
    # to a dictionary for Python to process.
    # referencePoint is needed to know the actual types the options
    # are supposed to be.
    def configUnserialize(self, opts, referencePoint, filterSystem=True):
        returnOpts = referencePoint

        # Global options
        for opt in referencePoint.keys():
            if opt.startswith('__') and filterSystem:
                # Leave out system variables
                continue
            if opts.has_key(opt):
                if type(referencePoint[opt]) is bool:
                    if opts[opt] == "1":
                        returnOpts[opt] = True
                    else:
                        returnOpts[opt] = False

                if type(referencePoint[opt]) is str:
                    returnOpts[opt] = str(opts[opt])

                if type(referencePoint[opt]) is int:
                    returnOpts[opt] = int(opts[opt])

                if type(referencePoint[opt]) is list:
                    if type(referencePoint[opt][0]) is int:
                        returnOpts[opt] = list()
                        for x in str(opts[opt]).split(","):
                             returnOpts[opt].append(int(x))
                    else:
                        returnOpts[opt] = str(opts[opt]).split(",")

        if not referencePoint.has_key('__modules__'):
            return returnOpts

        # Module options
        # A lot of mess to handle typing..
        for modName in referencePoint['__modules__']:
            for opt in referencePoint['__modules__'][modName]['opts']:
                if opt.startswith('_') and filterSystem:
                    continue
                if opts.has_key(modName + ":" + opt):
                    if type(referencePoint['__modules__'][modName]['opts'][opt]) is bool:
                        if opts[modName + ":" + opt] == "1":
                            returnOpts['__modules__'][modName]['opts'][opt] = True
                        else:
                            returnOpts['__modules__'][modName]['opts'][opt] = False

                    if type(referencePoint['__modules__'][modName]['opts'][opt]) is str:
                        returnOpts['__modules__'][modName]['opts'][opt] = \
                            str(opts[modName + ":" + opt])

                    if type(referencePoint['__modules__'][modName]['opts'][opt]) is int:
                        returnOpts['__modules__'][modName]['opts'][opt] = \
                            int(opts[modName + ":" + opt])

                    if type(referencePoint['__modules__'][modName]['opts'][opt]) is list:
                        if type(referencePoint['__modules__'][modName]['opts'][opt][0]) is int:
                            returnOpts['__modules__'][modName]['opts'][opt] = list()
                            for x in str(opts[modName + ":" + opt]).split(","):
                                returnOpts['__modules__'][modName]['opts'][opt].append(int(x))
                        else:
                            returnOpts['__modules__'][modName]['opts'][opt] = \
                                str(opts[modName + ":" + opt]).split(",")

        return returnOpts

    # Return an array of module names for returning the
    # types specified.
    def modulesProducing(self, events):
        modlist = list()
        for mod in self.opts['__modules__'].keys():
            if self.opts['__modules__'][mod]['provides'] == None:
                continue

            for evtype in self.opts['__modules__'][mod]['provides']:
                if evtype in events and mod not in modlist:
                    modlist.append(mod)

        return modlist

    # Return an array of modules that consume the types
    # specified.
    def modulesConsuming(self, events):
        modlist = list()
        for mod in self.opts['__modules__'].keys():
            if self.opts['__modules__'][mod]['consumes'] == None:
                continue

            for evtype in self.opts['__modules__'][mod]['consumes']:
                if evtype in events and mod not in modlist:
                    modlist.append(mod)

        return modlist

    # Return an array of types that are produced by the list
    # of modules supplied.
    def eventsFromModules(self, modules):
        evtlist = list()
        for mod in modules:
            if mod in self.opts['__modules__'].keys():
                if self.opts['__modules__'][mod]['provides'] != None:
                    for evt in self.opts['__modules__'][mod]['provides']:
                        evtlist.append(evt)

        return evtlist

    # Return an array of types that are consumed by the list
    # of modules supplied.
    def eventsToModules(self, modules):
        evtlist = list()
        for mod in modules:
            if mod in self.opts['__modules__'].keys():
                if self.opts['__modules__'][mod]['consumes'] != None:
                    for evt in self.opts['__modules__'][mod]['consumes']:
                        evtlist.append(evt)

        return evtlist

    #
    # URL parsing functions
    #

    # Turn a relative path into an absolute path
    def urlRelativeToAbsolute(self, url):
        finalBits = list()

        if '..' not in url:
            return url

        bits = url.split('/')

        for chunk in bits:
            if chunk == '..':
                # Don't pop the last item off if we're at the top
                if len(finalBits) <= 1:
                    continue

                # Don't pop the last item off if the first bits are not the path
                if '://' in url and len(finalBits) <= 3:
                    continue

                finalBits.pop()
                continue

            finalBits.append(chunk)

        #self.debug('xfrmed rel to abs path: ' + url + ' to ' + '/'.join(finalBits))
        return '/'.join(finalBits)

    # Extract the top level directory from a URL
    def urlBaseDir(self, url):

        bits = url.split('/')

        # For cases like 'www.somesite.com'
        if len(bits) == 0:
            #self.debug('base dir of ' + url + ' not identified, using URL as base.')
            return url + '/'

        # For cases like 'http://www.blah.com'
        if '://' in url and url.count('/') < 3:
            #self.debug('base dir of ' + url + ' is: ' + url + '/')
            return url + '/'

        base = '/'.join(bits[:-1])
        #self.debug('base dir of ' + url + ' is: ' + base + '/')
        return base + '/'

    # Extract the scheme and domain from a URL
    # Does not return the trailing slash! So you can do .endswith()
    # checks.
    def urlBaseUrl(self, url):
        if '://' in url:
            bits = re.match('(\w+://.[^/:]*)[:/].*', url)
        else:
            bits = re.match('(.[^/:]*)[:/]', url)

        if bits == None:
            return url.lower()

        #self.debug('base url of ' + url + ' is: ' + bits.group(1))
        return bits.group(1).lower()

    # Extract the FQDN from a URL
    def urlFQDN(self, url):
        baseurl = self.urlBaseUrl(url)
        if '://' not in baseurl:
            count = 0
        else:
            count = 2

        # http://abc.com will split to ['http:', '', 'abc.com']
        return baseurl.split('/')[count].lower()

    # Extract the keyword (the domain without the TLD or any subdomains)
    # from a domain.
    def domainKeyword(self, domain, tldList):
        # Strip off the TLD
        tld = '.'.join(self.hostDomain(domain.lower(), tldList).split('.')[1:])
        ret = domain.lower().replace('.'+tld, '')

        # If the user supplied a domain with a sub-domain, return the second part
        if '.' in ret:
            return ret.split('.')[-1]
        else:
            return ret
        
    # Obtain the domain name for a supplied hostname
    # tldList needs to be an array based on the Mozilla public list
    def hostDomain(self, hostname, tldList):
        ps = PublicSuffixList(tldList)
        return ps.get_public_suffix(hostname)

    # Simple way to verify IPs.
    def validIP(self, address):
        parts = address.split(".")
        if parts == None:
            return False

        if len(parts) != 4:
            return False
        for item in parts:
            if not item.isdigit():
                return False
            if not 0 <= int(item) <= 255:
                return False
        return True

    # Converts a dictionary of k -> array to a nested
    # tree that can be digested by d3 for visualizations.
    def dataParentChildToTree(self, data):
        def get_children(needle, haystack):
            #print "called"
            ret = list()

            if needle not in haystack.keys():
                return None

            if haystack[needle] == None:
                return None

            for c in haystack[needle]:
                #print "found child of " + needle + ": " + c
                ret.append({ "name": c, "children": get_children(c, haystack) })
            return ret

        # Find the element with no parents, that's our root.
        root = None
        for k in data.keys():
            if data[k] == None:
                continue

            contender = True
            for ck in data.keys():
                if data[ck] == None:
                    continue

                if k in data[ck]:
                    contender = False

            if contender:
                root = k
                break

        if root == None:
            #print "*BUG*: Invalid structure - needs to go back to one root."
            final = { }
        else:
            final = { "name": root, "children": get_children(root, data) }

        return final

    #
    # General helper functions to automate many common tasks between modules
    #

    # Parse the contents of robots.txt, returns a list of patterns
    # which should not be followed
    def parseRobotsTxt(self, robotsTxtData):
        returnArr = list()

        # We don't check the User-Agent rule yet.. probably should at some stage

        for line in robotsTxtData.splitlines():
            if line.lower().startswith('disallow:'):
                m = re.match('disallow:\s*(.[^ #]*)', line, re.IGNORECASE)
                self.debug('robots.txt parsing found disallow: ' + m.group(1))
                returnArr.append(m.group(1))
                continue

        return returnArr

    # Find all URLs within the supplied content. This does not fetch any URLs!
    # A dictionary will be returned, where each link will have the keys
    # 'source': The URL where the link was obtained from
    # 'original': What the link looked like in the content it was obtained from
    # The key will be the *absolute* URL of the link obtained, so for example if
    # the link '/abc' was obtained from 'http://xyz.com', the key in the dict will
    # be 'http://xyz.com/abc' with the 'original' attribute set to '/abc'
    def parseLinks(self, url, data, domain):
        returnLinks = dict()

        if data == None or len(data) == 0:
            self.debug('parseLinks() called with no data to parse')
            return None

        # Find actual links
        try:
            regRel = re.compile('(href|src|action|url)[:=][ \'\"]*(.[^\'\"<> ]*)',
                re.IGNORECASE)
            urlsRel = regRel.findall(data)
        except Exception as e:
            self.error("Error applying regex to: " + data)
            return None

        # Find potential links that aren't links (text possibly in comments, etc.)
        try:
            # Because we're working with a big blob of text now, don't worry
            # about clobbering proper links by url decoding them.
            data = urllib2.unquote(data)
            regRel = re.compile('(.)([a-zA-Z0-9\-\.]+\.'+domain+')', 
                re.IGNORECASE)
            urlsRel = urlsRel + regRel.findall(data)
        except Exception as e:
            self.error("Error applying regex2 to: " + data)
        try:
            # Some links are sitting inside a tag, e.g. Google's use of <cite>
            regRel = re.compile('(>)('+domain+'/.[^<]+)', re.IGNORECASE)
            urlsRel = urlsRel + regRel.findall(data)
        except Exception as e:
            self.error("Error applying regex3 to: " + data)

        # Loop through all the URLs/links found by the regex
        for linkTuple in urlsRel:
            # Remember the regex will return two vars (two groups captured)
            meta = linkTuple[0]
            link = linkTuple[1]
            absLink = None

            # Don't include stuff likely part of some dynamically built incomplete
            # URL found in Javascript code (character is part of some logic)
            if link[len(link)-1] == '.' or link[0] == '+' or \
                'javascript:' in link.lower() or '();' in link:
                self.debug('unlikely link: ' + link)
                continue

            # Filter in-page links
            if re.match('.*#.[^/]+', link):
                self.debug('in-page link: ' + link)
                continue

            # Ignore mail links
            if 'mailto:' in link.lower():
                self.debug("Ignoring mail link: " + link)
                continue

            # URL decode links
            if '%2f' in link.lower():
                link = urllib2.unquote(link)

            # Capture the absolute link:
            # If the link contains ://, it is already an absolute link
            if '://' in link:
                absLink = link

            # If the link starts with a /, the absolute link is off the base URL
            if link.startswith('/'):
                absLink = self.urlBaseUrl(url) + link

            # Maybe the domain was just mentioned and not a link, so we make it one
            if absLink == None and domain.lower() in link.lower():
                absLink = 'http://' + link

            # Otherwise, it's a flat link within the current directory
            if absLink == None:
                absLink = self.urlBaseDir(url) + link

            # Translate any relative pathing (../)
            absLink = self.urlRelativeToAbsolute(absLink)
            returnLinks[absLink] = {'source': url, 'original': link}

        return returnLinks

    # Fetch a URL, return the response object
    def fetchUrl(self, url, fatal=False, cookies=None, timeout=30, 
        useragent="SpiderFoot", headers=None, dontMangle=False):
        result = {
            'code': None,
            'status': None,
            'content': None,
            'headers': None,
            'realurl': None
        }

        if url == None:
            self.error('Blank URL supplied to be fetched')
            return result

        # Clean the URL
        url = url.encode('ascii', 'ignore')

        try:
            header = dict()
            if type(useragent) is list:
                header['User-Agent'] = random.choice(useragent)
            else:
                header['User-Agent'] = useragent

            # Add custom headers
            if headers != None:
                for k in headers.keys():
                    header[k] = headers[k]

            req = urllib2.Request(url, None, header)
            if cookies != None:
                req.add_header('cookie', cookies)
                self.info("Fetching (incl. cookies): " + url + \
                    " [user-agent: " + header['User-Agent'] + "] [timeout: " + \
                    str(timeout) + "]")
            else:
                self.info("Fetching: " + url + " [user-agent: " + \
                    header['User-Agent'] + "] [timeout: " + str(timeout) + "]")

            result['headers'] = dict()
            opener = urllib2.build_opener(SmartRedirectHandler())
            fullPage = opener.open(req, timeout=timeout)
            content = fullPage.read()

            for k, v in fullPage.info().items():
                result['headers'][k.lower()] = v

            # Content is compressed
            if 'gzip' in result['headers'].get('content-encoding', ''):
                content = gzip.GzipFile(fileobj=StringIO.StringIO(content)).read()

            if dontMangle:
                result['content'] = content
            else:
                result['content'] = unicode(content, 'utf-8', errors='replace')

            #print "FOR: " + url
            #print "HEADERS: " + str(result['headers'])
            result['realurl'] = fullPage.geturl()
            result['code'] = fullPage.getcode()
            result['status'] = 'OK'
        except urllib2.HTTPError as h:
            self.info("HTTP code " + str(h.code) + " encountered for " + url)
            # Capture the HTTP error code
            result['code'] = h.code
            for k, v in h.info().items():
                result['headers'][k.lower()] = v
            if fatal:
                self.fatal('URL could not be fetched (' + h.code + ')')
        except urllib2.URLError as e:
            self.info("Error fetching " + url + "(" + str(e) + ")")
            result['status'] = str(e)
            if fatal:
                self.fatal('URL could not be fetched (' + str(e) + ')')
        except Exception as x:
            self.info("Unexpected exception occurred fetching: " + url + " (" + str(x) + ")")
            result['content'] = None
            result['status'] = str(x)
            if fatal:
                self.fatal('URL could not be fetched (' + str(x) + ')')

        return result

    # Check if wildcard DNS is enabled by looking up two random hostnames
    def checkDnsWildcard(self, target):
        randpool = 'bcdfghjklmnpqrstvwxyz3456789'
        randhost1 = ''.join([random.choice(randpool) for x in range(6)])
        randhost2 = ''.join([random.choice(randpool) for x in range(10)])

        # An exception will be raised if either of the resolutions fail
        try:
            addrs = socket.gethostbyname_ex(randhost1 + "." + target)
            addrs = socket.gethostbyname_ex(randhost2 + "." + target)
            self.debug(target + " has wildcard DNS.")
            return True
        except BaseException as e:
            self.debug(target + " does not have wildcard DNS.")
            return False

    # Scrape Google for content, starting at startUrl and iterating through
    # results based on options supplied. Will return a dictionary of all pages
    # fetched and their contents {page => content}.
    # Options accepted:
    # limit: number of search result pages before returning, default is 10
    # nopause: don't randomly pause between fetches
    # useragent: User-Agent string to use
    # timeout: Fetch timeout
    def googleIterate(self, searchString, opts=dict()):
        limit = 10
        fetches = 0
        returnResults = dict()

        if opts.has_key('limit'):
            limit = opts['limit']

        # We attempt to make the URL look as authentically human as possible
        seedUrl = "http://www.google.com/search?q={0}".format(searchString) + \
            "&ie=utf-8&oe=utf-8&aq=t&rls=org.mozilla:en-US:official&client=firefox-a"
        firstPage = self.fetchUrl(seedUrl, timeout=opts['timeout'],
            useragent=opts['useragent'])
        if firstPage['code'] == 403 or firstPage['code'] == 503:
            self.error("Google doesn't like us right now..", False)
            return None

        if firstPage['content'] == None:
            self.error("Failed to fetch content from Google.", False)
            return None

        if "name=\"captcha\"" in firstPage['content']:
            self.error("Google returned a CAPTCHA.", False)
            return None

        returnResults[seedUrl] = firstPage['content']
        matches = re.findall("(\/search\S+start=\d+.[^\'\"]*sa=N)", 
            firstPage['content'])

        while matches > 0 and fetches < limit:
            nextUrl = None
            fetches += 1
            for match in matches:
                # Google moves in increments of 10
                if "start=" + str(fetches*10) in match:
                    nextUrl = match.replace("&amp;", "&")

            if nextUrl == None:
                self.debug("Nothing left to scan for in Google results.")
                return returnResults
            self.info("Next Google URL: " + nextUrl)

            # Wait for a random number of seconds between fetches
            if not opts.has_key('nopause'):
                pauseSecs = random.randint(4, 15)
                self.info("Pausing for " + str(pauseSecs))
                time.sleep(pauseSecs)

            nextPage = self.fetchUrl('http://www.google.com' + nextUrl,
                timeout=opts['timeout'], useragent=opts['useragent'])
            if nextPage['code'] == 403 or nextPage['code'] == 503:
                self.error("Google doesn't like us right now..", False)
                return returnResults

            if nextPage['content'] == None:
                self.error("Failed to fetch subsequent content from Google.", False)
                return returnResults

            if "name=\"captcha\"" in nextPage['content']:
                self.error("Google returned a CAPTCHA.", False)
                return None

            returnResults[nextUrl] = nextPage['content']
            matches = re.findall("(\/search\S+start=\d+.[^\'\"]*)", 
                nextPage['content'], re.IGNORECASE)

        return returnResults

    # Scrape Bing for content, starting at startUrl and iterating through
    # results based on options supplied. Will return a dictionary of all pages
    # fetched and their contents {page => content}.
    # Options accepted:
    # limit: number of search result pages before returning, default is 10
    # nopause: don't randomly pause between fetches
    # useragent: User-Agent string to use
    # timeout: Fetch timeout
    def bingIterate(self, searchString, opts=dict()):
        limit = 10
        fetches = 0
        returnResults = dict()

        if opts.has_key('limit'):
            limit = opts['limit']

        # We attempt to make the URL look as authentically human as possible
        seedUrl = "http://www.bing.com/search?q={0}".format(searchString) + \
            "&pc=MOZI"
        firstPage = self.fetchUrl(seedUrl, timeout=opts['timeout'],
            useragent=opts['useragent'])
        if firstPage['code'] == 400:
            self.error("Bing doesn't like us right now..", False)
            return None

        if firstPage['content'] == None:
            self.error("Failed to fetch content from Bing.", False)
            return None

        if "/challengepic?" in firstPage['content']:
            self.error("Bing returned a CAPTCHA.", False)
            return None

        returnResults[seedUrl] = firstPage['content']

        matches = re.findall("(\/search\S+first=\d+.[^\'\"]*FORM=\S+)", 
            firstPage['content'])
        while matches > 0 and fetches < limit:
            nextUrl = None
            fetches += 1
            for match in matches:
                # Bing moves in increments of 10
                if "first=" + str((fetches*10)+1) in match:
                    nextUrl = match.replace("&amp;", "&").replace("%3a", ":")

            if nextUrl == None:
                self.debug("Nothing left to scan for in Bing results.")
                return returnResults
            self.info("Next Bing URL: " + nextUrl)

            # Wait for a random number of seconds between fetches
            if not opts.has_key('nopause'):
                pauseSecs = random.randint(4, 15)
                self.info("Pausing for " + str(pauseSecs))
                time.sleep(pauseSecs)

            nextPage = self.fetchUrl('http://www.bing.com' + nextUrl,
                timeout=opts['timeout'], useragent=opts['useragent'])
            if nextPage['code'] == 400:
                self.error("Bing doesn't like us any more..", False)
                return returnResults

            if nextPage['content'] == None:
                self.error("Failed to fetch subsequent content from Bing.", False)
                return returnResults

            if "/challengepic?" in firstPage['content']:
                self.error("Bing returned a CAPTCHA.", False)
                return None

            returnResults[nextUrl] = nextPage['content']
            matches = re.findall("(\/search\S+first=\d+.[^\'\"]*)", 
                nextPage['content'], re.IGNORECASE)

        return returnResults

    # Scrape Yahoo for content, starting at startUrl and iterating through
    # results based on options supplied. Will return a dictionary of all pages
    # fetched and their contents {page => content}.
    # Options accepted:
    # limit: number of search result pages before returning, default is 10
    # nopause: don't randomly pause between fetches
    # useragent: User-Agent string to use
    # timeout: Fetch timeout
    def yahooIterate(self, searchString, opts=dict()):
        limit = 10
        fetches = 0
        returnResults = dict()

        if opts.has_key('limit'):
            limit = opts['limit']

        # We attempt to make the URL look as authentically human as possible
        seedUrl = "https://search.yahoo.com/search?p={0}".format(searchString) + \
            "&toggle=1&cop=mss&ei=UTF-8"
        firstPage = self.fetchUrl(seedUrl, timeout=opts['timeout'],
            useragent=opts['useragent'])
        if firstPage['code'] == 403:
            self.error("Yahoo doesn't like us right now..", False)
            return None

        if firstPage['content'] == None:
            self.error("Failed to fetch content from Yahoo.", False)
            return None

        returnResults[seedUrl] = firstPage['content']

        matches = re.findall("(\/search;\S+b=\d+.[^\'\"]*)", 
            firstPage['content'])
        while matches > 0 and fetches < limit:
            nextUrl = None
            fetches += 1
            for match in matches:
                # Yahoo moves in increments of 10
                if "b=" + str((fetches*10)+1) in match:
                    nextUrl = "https://search.yahoo.com" + match

            if nextUrl == None:
                self.debug("Nothing left to scan for in Yahoo results.")
                return returnResults
            self.info("Next Yahoo URL: " + nextUrl)

            # Wait for a random number of seconds between fetches
            if not opts.has_key('nopause'):
                pauseSecs = random.randint(4, 15)
                self.info("Pausing for " + str(pauseSecs))
                time.sleep(pauseSecs)

            nextPage = self.fetchUrl(nextUrl,
                timeout=opts['timeout'], useragent=opts['useragent'])
            if nextPage['code'] == 403:
                self.error("Yahoo doesn't like us any more..", False)
                return returnResults

            if nextPage['content'] == None:
                self.error("Failed to fetch subsequent content from Yahoo.", False)
                return returnResults

            returnResults[nextUrl] = nextPage['content']
            matches = re.findall("(\/search;\S+b=\d+.[^\'\"]*)",
                nextPage['content'], re.IGNORECASE)

        return returnResults

#
# SpiderFoot plug-in module base class
#
class SpiderFootPlugin(object):
    # Will be set to True by the controller if the user aborts scanning
    _stopScanning = False
    # Modules that will be notified when this module produces events
    _listenerModules = list()
    # Current event being processed
    _currentEvent = None
    # Name of this module, set at startup time
    __name__ = "module_name_not_set!"

    # Not really needed in most cases.
    def __init__(self):
        pass

    # Hack to override module's use of socket, replacing it with
    # one that uses the supplied SOCKS server
    def _updateSocket(self, sock):
        socket = sock
        urllib2.socket = sock

    # Used to clear any listener relationships, etc. This is needed because
    # Python seems to cache local variables even between threads.
    def clearListeners(self):
        self._listenerModules = list()
        self._stopScanning = False

    # Will always be overriden by the implementer.
    def setup(self, sf, url, userOpts=dict()):
        pass

    # Listener modules which will get notified once we have data for them to
    # work with.
    def registerListener(self, listener):
        self._listenerModules.append(listener)

    # Call the handleEvent() method of every other plug-in listening for
    # events from this plug-in. Remember that those plug-ins will be called
    # within the same execution context of this thread, not on their own.
    def notifyListeners(self, sfEvent):
        eventName = sfEvent.eventType
        eventData = sfEvent.data
        storeOnly = False # Under some conditions, only store and don't notify

        if eventData == None or (type(eventData) is unicode and len(eventData) == 0):
            #print "No data to send for " + eventName + " to " + listener.__module__
            return None

        # Look back to ensure the original notification for an element
        # is what's linked to children. For instance, sfp_dns may find
        # xyz.abc.com, and then sfp_ripe obtains some raw data for the
        # same, and then sfp_dns finds xyz.abc.com in there, we should
        # suppress the notification of that to other modules, as the
        # original xyz.abc.com notification from sfp_dns will trigger
        # those modules anyway. This also avoids messy iterations that
        # traverse many many levels.

        # storeOnly is used in this case so that the source to dest
        # relationship is made, but no further events are triggered
        # from dest, as we are already operating on dest's original
        # notification from one of the upstream events.

        prevEvent = sfEvent.sourceEvent
        while prevEvent != None:
            if prevEvent.sourceEvent != None:
                if prevEvent.sourceEvent.eventType == sfEvent.eventType and \
                    prevEvent.sourceEvent.data.lower() == sfEvent.data.lower():
                    #print "Skipping notification of " + sfEvent.eventType + " / " + sfEvent.data
                    storeOnly = True
                    break
            prevEvent = prevEvent.sourceEvent

        self._listenerModules.sort()
        for listener in self._listenerModules:
            #print listener.__module__ + ": " + listener.watchedEvents().__str__()
            if eventName not in listener.watchedEvents() and '*' not in listener.watchedEvents():
                #print listener.__module__ + " not listening for " + eventName
                continue

            if storeOnly and "__stor" not in listener.__module__:
                #print "Storing only for " + sfEvent.eventType + " / " + sfEvent.data
                continue

            #print "Notifying " + eventName + " to " + listener.__module__
            listener._currentEvent = sfEvent

            # Check if we've been asked to stop in the meantime, so that
            # notifications stop triggering module activity.
            if self.checkForStop():
                return None

            listener.handleEvent(sfEvent)

    # Called to stop scanning
    def stopScanning(self):
        self._stopScanning = True

    # For modules to use to check for when they should give back control
    def checkForStop(self):
        return self._stopScanning

    # Return a list of the default configuration options for the module.
    def defaultOpts(self):
        return self.opts

    # What events is this module interested in for input. The format is a list
    # of event types that are applied to event types that this module wants to
    # be notified of, or * if it wants everything.
    # Will usually be overriden by the implementer, unless it is interested
    # in all events (default behavior).
    def watchedEvents(self):
        return [ '*' ]

    # What events this module produces
    # This is to support the end user in selecting modules based on events
    # produced.
    def producedEvents(self):
        return None

    # Handle events to this module
    # Will usually be overriden by the implementer, unless it doesn't handle
    # any events.
    def handleEvent(self, sfEvent):
        return None

    # Kick off the work (for some modules nothing will happen here, but instead
    # the work will start from the handleEvent() method.
    # Will usually be overriden by the implementer.
    def start(self):
        return None

# Class for SpiderFoot Events
class SpiderFootEvent(object):
    generated = None
    eventType = None
    confidence = None
    visibility = None
    risk = None
    module = None
    data = None
    sourceEvent = None
    sourceEventHash = None
    __id = None
    
    def __init__(self, eventType, data, module, sourceEvent=None,
        confidence=100, visibility=100, risk=0):
        self.eventType = eventType
        self.generated = time.time()
        self.confidence = confidence
        self.visibility = visibility
        self.risk = risk
        self.module = module
        self.data = data
        self.sourceEvent = sourceEvent

        # "ROOT" is a special "hash" reserved for elements with no
        # actual parent (e.g. the first page spidered.)
        if sourceEvent != None:
            self.sourceEventHash = sourceEvent.getHash()
        else:
            self.sourceEventHash = "ROOT"

        self.__id = self.eventType + str(self.generated) + self.module + \
            str(random.randint(0, 99999999))

    # Unique hash of this event
    def getHash(self):
        if self.eventType == "INITIAL_TARGET":
            return "ROOT"

        digestStr = self.__id.encode('raw_unicode_escape')
        return hashlib.sha256(digestStr).hexdigest()

    # Update variables as new information becomes available
    def setConfidence(self, confidence):
        self.confidence = confidence

    def setVisibility(self, visibility):
        self.visibility = visibility

    def setRisk(self, risk):
        self.risk = risk

    def setSourceEventHash(self, srcHash):
        self.sourceEventHash = srcHash


# Override the default redirectors to re-use cookies
class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_301(self, req, fp, code, msg, headers):
        if headers.has_key("Set-Cookie"):
            req.add_header('cookie', headers['Set-Cookie'])
        result = urllib2.HTTPRedirectHandler.http_error_301(
            self, req, fp, code, msg, headers)
        return result

    def http_error_302(self, req, fp, code, msg, headers):
        if headers.has_key("Set-Cookie"):
            req.add_header('cookie', headers['Set-Cookie'])
        result = urllib2.HTTPRedirectHandler.http_error_302(
            self, req, fp, code, msg, headers)
        return result


"""
Public Suffix List module for Python.
See LICENSE.tp for applicable license.
"""

class PublicSuffixList(object):
	def __init__(self, input_data):
		"""Reads and parses public suffix list.
		
		input_file is a file object or another iterable that returns
		lines of a public suffix list file. If input_file is None, an
		UTF-8 encoded file named "publicsuffix.txt" in the same
		directory as this Python module is used.
		
		The file format is described at http://publicsuffix.org/list/
		"""

		#if input_file is None:
			#input_path = os.path.join(os.path.dirname(__file__), 'publicsuffix.txt')
			#input_file = codecs.open(input_path, "r", "utf8")

		root = self._build_structure(input_data)
		self.root = self._simplify(root)

	def _find_node(self, parent, parts):
		if not parts:
			return parent

		if len(parent) == 1:
			parent.append({})

		assert len(parent) == 2
		negate, children = parent

		child = parts.pop()

		child_node = children.get(child, None)

		if not child_node:
			children[child] = child_node = [0]

		return self._find_node(child_node, parts)

	def _add_rule(self, root, rule):
		if rule.startswith('!'):
			negate = 1
			rule = rule[1:]
		else:
			negate = 0

		parts = rule.split('.')
		self._find_node(root, parts)[0] = negate

	def _simplify(self, node):
		if len(node) == 1:
			return node[0]

		return (node[0], dict((k, self._simplify(v)) for (k, v) in node[1].items()))

	def _build_structure(self, fp):
		root = [0]

		for line in fp:
			line = line.strip()
			if line.startswith('//') or not line:
				continue

			self._add_rule(root, line.split()[0].lstrip('.'))

		return root

	def _lookup_node(self, matches, depth, parent, parts):
		if parent in (0, 1):
			negate = parent
			children = None
		else:
			negate, children = parent

		matches[-depth] = negate

		if depth < len(parts) and children:
			for name in ('*', parts[-depth]):
				child = children.get(name, None)
				if child is not None:
					self._lookup_node(matches, depth+1, child, parts)

	def get_public_suffix(self, domain):
		"""get_public_suffix("www.example.com") -> "example.com"

		Calling this function with a DNS name will return the
		public suffix for that name.

		Note that for internationalized domains the list at
		http://publicsuffix.org uses decoded names, so it is
		up to the caller to decode any Punycode-encoded names.
		"""

		parts = domain.lower().lstrip('.').split('.')
		hits = [None] * len(parts)

		self._lookup_node(hits, 1, self.root, parts)

		for i, what in enumerate(hits):
			if what is not None and what == 0:
				return '.'.join(parts[i:])

########NEW FILE########
__FILENAME__ = sfscan
#-----------------------------------------------------------------
# Name:         sfscan
# Purpose:      Scanning control functionality
#
# Author:       Steve Micallef <steve@binarypool.com>
#
# Created:      11/03/2013
# Copyright:    (c) Steve Micallef 2013
# License:      GPL
#-----------------------------------------------------------------
import json
import traceback
import os
import time
import sys
import socket
import socks
import dns.resolver
from copy import deepcopy
from sfdb import SpiderFootDb
from sflib import SpiderFoot, SpiderFootEvent

# Controls all scanning activity
# Eventually change this to be able to control multiple scan instances
class SpiderFootScanner:
    moduleInstances = None
    status = "UNKNOWN"
    myId = None

    def __init__(self, name, target, moduleList, globalOpts, moduleOpts):
        self.config = deepcopy(globalOpts)
        self.sf = SpiderFoot(self.config)
        self.target = target
        self.moduleList = moduleList
        self.name = name

        return

    # Status of the currently running scan (if any)
    def scanStatus(self, id):
        if id != self.myId:
            return "UNKNOWN"
        return self.status  

    # Stop a scan (id variable is unnecessary for now given that only one simultaneous
    # scan is permitted.)
    def stopScan(self, id):
        if id != self.myId:
            return None

        if self.moduleInstances == None:
            return None

        for modName in self.moduleInstances.keys():
            self.moduleInstances[modName].stopScanning()

    # Start running a scan
    def startScan(self):
        self.moduleInstances = dict()
        dbh = SpiderFootDb(self.config)
        self.sf.setDbh(dbh)
        aborted = False

        # Create a unique ID for this scan and create it in the back-end DB.
        self.config['__guid__'] = dbh.scanInstanceGenGUID(self.target)
        self.sf.setScanId(self.config['__guid__'])
        self.myId = self.config['__guid__']
        dbh.scanInstanceCreate(self.config['__guid__'], self.name, self.target)
        dbh.scanInstanceSet(self.config['__guid__'], time.time() * 1000, None, 'STARTING')
        self.status = "STARTING"
        
        # Save the config current set for this scan
        self.config['_modulesenabled'] = self.moduleList
        dbh.scanConfigSet(self.config['__guid__'], self.sf.configSerialize(self.config))

        self.sf.status("Scan [" + self.config['__guid__'] + "] initiated.")
        # moduleList = list of modules the user wants to run
        try:
            # Process global options that point to other places for data

            # If a SOCKS server was specified, set it up
            if self.config['_socks1type'] != '':
                socksType = socks.PROXY_TYPE_SOCKS4
                socksDns = self.config['_socks6dns']
                socksAddr = self.config['_socks2addr']
                socksPort = int(self.config['_socks3port'])
                socksUsername = ''
                socksPassword = ''

                if self.config['_socks1type'] == '4':
                    socksType = socks.PROXY_TYPE_SOCKS4
                if self.config['_socks1type'] == '5':
                    socksType = socks.PROXY_TYPE_SOCKS5
                    socksUsername = self.config['_socks4user']
                    socksPassword = self.config['_socks5pwd']
                    
                if self.config['_socks1type'] == 'HTTP':
                    socksType = socks.PROXY_TYPE_HTTP
                   
                self.sf.debug("SOCKS: " + socksAddr + ":" + str(socksPort) + \
                    "(" + socksUsername + ":" + socksPassword + ")")
                socks.setdefaultproxy(socksType, socksAddr, socksPort, 
                    socksDns, socksUsername, socksPassword)

                # Override the default socket and getaddrinfo calls with the 
                # SOCKS ones
                socket.socket = socks.socksocket
                socket.create_connection = socks.create_connection
                socket.getaddrinfo = socks.getaddrinfo

                self.sf.updateSocket(socket)
            
            # Override the default DNS server
            if self.config['_dnsserver'] != "":
                res = dns.resolver.Resolver()
                res.nameservers = [ self.config['_dnsserver'] ]
                dns.resolver.override_system_resolver(res)
            else:
                dns.resolver.restore_system_resolver()

            # Set the user agent
            self.config['_useragent'] = self.sf.optValueToData(self.config['_useragent'])

            # Get internet TLDs
            tlddata = self.sf.cacheGet("internet_tlds", self.config['_internettlds_cache'])
            # If it wasn't loadable from cache, load it from scratch
            if tlddata == None:
                self.config['_internettlds'] = self.sf.optValueToData(self.config['_internettlds'])
                self.sf.cachePut("internet_tlds", self.config['_internettlds'])
            else:
                self.config["_internettlds"] = tlddata.splitlines()

            for modName in self.moduleList:
                if modName == '':
                    continue

                module = __import__('modules.' + modName, globals(), locals(), [modName])
                mod = getattr(module, modName)()
                mod.__name__ = modName

                # A bit hacky: we pass the database object as part of the config. This
                # object should only be used by the internal SpiderFoot modules writing
                # to the database, which at present is only sfp__stor_db.
                # Individual modules cannot create their own SpiderFootDb instance or
                # we'll get database locking issues, so it all goes through this.
                self.config['__sfdb__'] = dbh

                # Set up the module
                # Configuration is a combined global config with module-specific options
                #modConfig = deepcopy(self.config)
                modConfig = self.config['__modules__'][modName]['opts']
                for opt in self.config.keys():
                    modConfig[opt] = self.config[opt]

                mod.clearListeners() # clear any listener relationships from the past
                mod.setup(self.sf, self.target, modConfig)
                self.moduleInstances[modName] = mod

                # Override the module's local socket module
                # to be the SOCKS one.
                if self.config['_socks1type'] != '':
                    mod._updateSocket(socket)

                self.sf.status(modName + " module loaded.")

            # Register listener modules and then start all modules sequentially
            for module in self.moduleInstances.values():
                for listenerModule in self.moduleInstances.values():
                    # Careful not to register twice or you will get duplicate events
                    if listenerModule in module._listenerModules:
                        continue
                    # Note the absence of a check for whether a module can register
                    # to itself. That is intentional because some modules will
                    # act on their own notifications (e.g. sfp_dns)!
                    if listenerModule.watchedEvents() != None:
                        module.registerListener(listenerModule)

            dbh.scanInstanceSet(self.config['__guid__'], status='RUNNING')
            self.status = "RUNNING"

            # Create the "ROOT" event which un-triggered modules will link events to
            rootEvent = SpiderFootEvent("INITIAL_TARGET", self.target, "SpiderFoot UI")
            dbh.scanEventStore(self.config['__guid__'], rootEvent)

            # Start the modules sequentially.
            for module in self.moduleInstances.values():
                # Check in case the user requested to stop the scan between modules initializing
                if module.checkForStop():
                    dbh.scanInstanceSet(self.config['__guid__'], status='ABORTING')
                    self.status = "ABORTING"
                    aborted = True
                    break
                # Many modules' start() method will return None, as most will rely on 
                # notifications during the scan from other modules.
                module.start()

            # Check if any of the modules ended due to being stopped
            for module in self.moduleInstances.values():
                if module.checkForStop():
                    aborted = True

            if aborted:
                self.sf.status("Scan [" + self.config['__guid__'] + "] aborted.")
                dbh.scanInstanceSet(self.config['__guid__'], None, time.time() * 1000, 'ABORTED')
                self.status = "ABORTED"
            else:
                self.sf.status("Scan [" + self.config['__guid__'] + "] completed.")
                dbh.scanInstanceSet(self.config['__guid__'], None, time.time() * 1000, 'FINISHED')
                self.status = "FINISHED"
        except BaseException as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.sf.error("Unhandled exception (" + e.__class__.__name__ + ") " + \
                "encountered during scan. Please report this as a bug: " + \
                repr(traceback.format_exception(exc_type, exc_value, exc_traceback)), False)
            self.sf.status("Scan [" + self.config['__guid__'] + "] failed: " + str(e))
            dbh.scanInstanceSet(self.config['__guid__'], None, time.time() * 1000, 'ERROR-FAILED')
            self.status = "ERROR-FAILED"

        self.moduleInstances = None
        dbh.close()
        self.sf.setDbh(None)
        self.sf.setScanId(None)


########NEW FILE########
__FILENAME__ = sfwebui
#-----------------------------------------------------------------
# Name:         sfwebui
# Purpose:      User interface class for use with a web browser
#
# Author:       Steve Micallef <steve@binarypool.com>
#
# Created:      30/09/2012
# Copyright:    (c) Steve Micallef 2012
# License:      GPL
#-----------------------------------------------------------------
import json
import threading
import cherrypy
import cgi
import csv
import os
import time
import random
import urllib2
from copy import deepcopy
from mako.lookup import TemplateLookup
from mako.template import Template
from sfdb import SpiderFootDb
from sflib import SpiderFoot
from sfscan import SpiderFootScanner
from StringIO import StringIO

class SpiderFootWebUi:
    lookup = TemplateLookup(directories=[''])
    defaultConfig = dict()
    config = dict()
    scanner = None
    token = None

    def __init__(self, config):
        self.defaultConfig = deepcopy(config)
        dbh = SpiderFootDb(config)
        # 'config' supplied will be the defaults, let's supplement them
        # now with any configuration which may have previously been
        # saved.
        sf = SpiderFoot(config)
        self.config = sf.configUnserialize(dbh.configGet(), config)

        if self.config['__webaddr'] == "0.0.0.0":
            addr = "<IP of this host>"
        else:
            addr = self.config['__webaddr']

        print ""
        print ""
        print "*************************************************************"
        print " Use SpiderFoot by starting your web browser of choice and "
        print " browse to http://" + addr + ":" + str(self.config['__webport'])
        print "*************************************************************"
        print ""
        print ""


    # Sanitize user input
    def cleanUserInput(self, inputList):
        ret = list()

        for item in inputList:
            c = cgi.escape(item, True)
            c = c.replace('\'', '&quot;')
            ret.append(c)

        return ret

    #
    # USER INTERFACE PAGES
    #

    # Get result data in CSV format
    def scaneventresultexport(self, id, type, dialect="excel"):
        dbh = SpiderFootDb(self.config)
        data = dbh.scanResultEvent(id, type)
        fileobj = StringIO()
        parser = csv.writer(fileobj, dialect=dialect)
        parser.writerow(["Updated", "Type", "Module", "Source", "Data"])
        for row in data:
            lastseen = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[0]))
            datafield = str(row[1]).replace("<SFURL>", "").replace("</SFURL>", "")
            parser.writerow([lastseen, str(row[4]), str(row[3]), str(row[2]), datafield])
        cherrypy.response.headers['Content-Disposition'] = "attachment; filename=SpiderFoot.csv"
        cherrypy.response.headers['Content-Type'] = "application/csv"
        cherrypy.response.headers['Pragma'] = "no-cache"
        return fileobj.getvalue()
    scaneventresultexport.exposed = True

    # Configuration used for a scan
    def scanopts(self, id):
        ret = dict()
        dbh = SpiderFootDb(self.config)
        ret['config'] = dbh.scanConfigGet(id)
        ret['configdesc'] = dict()
        for key in ret['config'].keys():
            if ':' not in key:
                ret['configdesc'][key] = self.config['__globaloptdescs__'][key]
            else:
                [ modName, modOpt ] = key.split(':')
                if not modName in self.config['__modules__'].keys():
                    continue

                if not modOpt in self.config['__modules__'][modName]['optdescs'].keys():
                    continue

                ret['configdesc'][key] = self.config['__modules__'][modName]['optdescs'][modOpt]

        sf = SpiderFoot(self.config)
        meta = dbh.scanInstanceGet(id)
        if meta[3] != 0:
            started = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(meta[3]))
        else:
            started = "Not yet"

        if meta[4] != 0:
            finished = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(meta[4]))
        else:
            finished = "Not yet"
        ret['meta'] = [meta[0], meta[1], meta[2], started, finished, meta[5]]

        return json.dumps(ret)
    scanopts.exposed = True

    # Configure a new scan
    def newscan(self):
        dbh = SpiderFootDb(self.config)
        types = dbh.eventTypes()
        templ = Template(filename='dyn/newscan.tmpl', lookup=self.lookup)
        return templ.render(pageid='NEWSCAN', types=types, 
            modules=self.config['__modules__'])
    newscan.exposed = True

    # Main page listing scans available
    def index(self):
        # Look for referenced templates in the current directory only
        templ = Template(filename='dyn/scanlist.tmpl', lookup=self.lookup)
        return templ.render(pageid='SCANLIST')
    index.exposed = True

    # Information about a selected scan
    def scaninfo(self, id):
        dbh = SpiderFootDb(self.config)
        res = dbh.scanInstanceGet(id)
        if res == None:
            return self.error("Scan ID not found.")

        templ = Template(filename='dyn/scaninfo.tmpl', lookup=self.lookup)
        return templ.render(id=id, name=res[0], status=res[5], 
            pageid="SCANLIST")
    scaninfo.exposed = True

    # Settings
    def opts(self):
        templ = Template(filename='dyn/opts.tmpl', lookup=self.lookup)
        self.token = random.randint(0, 99999999)
        return templ.render(opts=self.config, pageid='SETTINGS', token=self.token)
    opts.exposed = True

    # Generic error, but not exposed as not called directly
    def error(self, message):
        templ = Template(filename='dyn/error.tmpl', lookup=self.lookup)
        return templ.render(message=message)

    # Delete a scan
    def scandelete(self, id, confirm=None):
        dbh = SpiderFootDb(self.config)
        res = dbh.scanInstanceGet(id)
        if res == None:
            return self.error("Scan ID not found.")

        if confirm != None:
            dbh.scanInstanceDelete(id)
            raise cherrypy.HTTPRedirect("/")
        else:
            templ = Template(filename='dyn/scandelete.tmpl', lookup=self.lookup)
            return templ.render(id=id, name=res[0], pageid="SCANLIST")
    scandelete.exposed = True

    # Save settings, also used to completely reset them to default
    def savesettings(self, allopts, token):
        if str(token) != str(self.token):
            return self.error("Invalid token (" + str(self.token) + ").")

        try:
            dbh = SpiderFootDb(self.config)
            # Reset config to default
            if allopts == "RESET":
                dbh.configClear() # Clear it in the DB
                self.config = deepcopy(self.defaultConfig) # Clear in memory
            else:
                useropts = json.loads(allopts)
                cleanopts = dict()
                for opt in useropts.keys():
                    cleanopts[opt] = self.cleanUserInput([useropts[opt]])[0]

                currentopts = deepcopy(self.config)

                # Make a new config where the user options override
                # the current system config.
                sf = SpiderFoot(self.config)
                self.config = sf.configUnserialize(cleanopts, currentopts)

                dbh.configSet(sf.configSerialize(currentopts))
        except Exception as e:
            return self.error("Processing one or more of your inputs failed: " + str(e))

        templ = Template(filename='dyn/opts.tmpl', lookup=self.lookup)
        self.token = random.randint(0, 99999999)
        return templ.render(opts=self.config, pageid='SETTINGS', updated=True, 
            token=self.token)
    savesettings.exposed = True

    # Initiate a scan
    def startscan(self, scanname, scantarget, modulelist, typelist):
        modopts = dict() # Not used yet as module options are set globally
        modlist = list()
        sf = SpiderFoot(self.config)
        dbh = SpiderFootDb(self.config)
        types = dbh.eventTypes()

        [scanname, scantarget] = self.cleanUserInput([scanname, scantarget])

        if scanname == "" or scantarget == "":
            return self.error("Form incomplete.")

        if typelist == "" and modulelist == "":
            return self.error("Form incomplete.")

        if modulelist != "":
            modlist = modulelist.replace('module_', '').split(',')
        else:
            typesx = typelist.replace('type_', '').split(',')
            # 1. Find all modules that produce the requested types
            modlist = sf.modulesProducing(typesx)
            newmods = deepcopy(modlist)
            newmodcpy = deepcopy(newmods)
            # 2. For each type those modules consume, get modules producing
            while len(newmodcpy) > 0:
                for etype in sf.eventsToModules(newmodcpy):
                    xmods = sf.modulesProducing([etype])
                    for mod in xmods:
                        if mod not in modlist:
                            modlist.append(mod)
                            newmods.append(mod)
                newmodcpy = deepcopy(newmods)
                newmods = list()

        # Add our mandatory storage module..
        if "sfp__stor_db" not in modlist:
            modlist.append("sfp__stor_db")
        modlist.sort()

        # For now we don't permit multiple simultaneous scans
        for thread in threading.enumerate():
            if thread.name.startswith("SF_"):
                templ = Template(filename='dyn/newscan.tmpl', lookup=self.lookup)
                return templ.render(modules=self.config['__modules__'], 
                    alreadyRunning=True, runningScan=thread.name[3:], 
                    types=types, pageid="NEWSCAN")

        # Start running a new scan
        self.scanner = SpiderFootScanner(scanname, scantarget.lower(), modlist, 
            self.config, modopts)
        t = threading.Thread(name="SF_" + scanname, target=self.scanner.startScan)
        t.start()

        # Spin cycles waiting for the scan ID to be set
        while self.scanner.myId == None:
            time.sleep(1)
            continue

        templ = Template(filename='dyn/scaninfo.tmpl', lookup=self.lookup)
        return templ.render(id=self.scanner.myId, name=scanname, 
            status=self.scanner.status, pageid="SCANLIST")
    startscan.exposed = True

    # Stop a scan (id variable is unnecessary for now given that only one simultaneous
    # scan is permitted.)
    def stopscan(self, id):
        if self.scanner == None:
            return self.error("There are no scans running. A data consistency " + \
                "error for this scan probably exists. <a href='/scandelete?id=" + \
                id + "&confirm=1'>Click here to delete it.</a>")

        if self.scanner.scanStatus(id) == "ABORTED":
            return self.error("The scan is already aborted.")

        if not self.scanner.scanStatus(id) == "RUNNING":
            return self.error("The running scan is currently in the state '" + \
                self.scanner.scanStatus(id) + "', please try again later or restart " + \
                " SpiderFoot.")

        self.scanner.stopScan(id)
        templ = Template(filename='dyn/scanlist.tmpl', lookup=self.lookup)
        return templ.render(pageid='SCANLIST',stoppedscan=True)
    stopscan.exposed = True

    #
    # DATA PROVIDERS
    #

    # Scan log data
    def scanlog(self, id, limit=None):
        dbh = SpiderFootDb(self.config)
        data = dbh.scanLogs(id, limit)
        retdata = []
        for row in data:
            generated = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[0]/1000))
            retdata.append([generated, row[1], row[2], 
                cgi.escape(unicode(row[3], errors='replace'))])
        return json.dumps(retdata)
    scanlog.exposed = True

    # Scan error data
    def scanerrors(self, id, limit=None):
        dbh = SpiderFootDb(self.config)
        data = dbh.scanErrors(id, limit)
        retdata = []
        for row in data:
            generated = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[0]/1000))
            retdata.append([generated, row[1],
                cgi.escape(unicode(row[2], errors='replace'))])
        return json.dumps(retdata)
    scanerrors.exposed = True

    # Produce a list of scans
    def scanlist(self):
        dbh = SpiderFootDb(self.config)
        data = dbh.scanInstanceList()
        retdata = []
        for row in data:
            created = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[3]))
            if row[4] != 0:
                started = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[4]))
            else:
                started = "Not yet"

            if row[5] != 0:
                finished = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[5]))
            else:
                finished = "Not yet"
            retdata.append([row[0], row[1], row[2], created, started, finished, row[6], row[7]])
        return json.dumps(retdata)
    scanlist.exposed = True

    # Basic information about a scan
    def scanstatus(self, id):
        dbh = SpiderFootDb(self.config)
        data = dbh.scanInstanceGet(id)
        created = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data[2]))
        started = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data[3]))
        ended = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data[4]))

        retdata = [data[0], data[1], created, started, ended, data[5]]
        return json.dumps(retdata)
    scanstatus.exposed = True

    # Summary of scan results
    def scansummary(self, id):
        dbh = SpiderFootDb(self.config)
        data = dbh.scanResultSummary(id)
        retdata = []
        for row in data:
            lastseen = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[2]))
            retdata.append([row[0], row[1], lastseen, row[3], row[4]])
        return json.dumps(retdata)
    scansummary.exposed = True

    # Event results for a scan
    def scaneventresults(self, id, eventType):
        dbh = SpiderFootDb(self.config)
        data = dbh.scanResultEvent(id, eventType)
        retdata = []
        for row in data:
            lastseen = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[0]))
            escapeddata = cgi.escape(row[1])
            escapedsrc = cgi.escape(row[2])
            retdata.append([lastseen, escapeddata, escapedsrc, 
                row[3], row[5], row[6], row[7], row[8]])
        return json.dumps(retdata, ensure_ascii=False)
    scaneventresults.exposed = True

    # Unique event results for a scan
    def scaneventresultsunique(self, id, eventType):
        dbh = SpiderFootDb(self.config)
        data = dbh.scanResultEventUnique(id, eventType)
        retdata = []
        for row in data:
            escaped = cgi.escape(row[0])
            retdata.append([escaped, row[1], row[2]])
        return json.dumps(retdata, ensure_ascii=False)
    scaneventresultsunique.exposed = True

    # Historical data for the scan, graphs will be rendered in JS
    def scanhistory(self, id):
        dbh = SpiderFootDb(self.config)
        data = dbh.scanResultHistory(id)
        return json.dumps(data, ensure_ascii=False)
    scanhistory.exposed = True

    def scanelementtypediscovery(self, id, eventType):
        keepGoing = True
        sf = SpiderFoot(self.config)
        dbh = SpiderFootDb(self.config)
        pc = dict()
        datamap = dict()

        # Get the events we will be tracing back from
        leafSet = dbh.scanResultEvent(id, eventType)

        # Get the first round of source IDs for the leafs
        nextIds = list()
        for row in leafSet:
            # these must be unique values!
            parentId = row[9]
            childId = row[8]
            datamap[childId] = row

            if pc.has_key(parentId):
                if childId not in pc[parentId]:
                    pc[parentId].append(childId)
            else:
                pc[parentId] = [ childId ]

            # parents of the leaf set
            if parentId not in nextIds:
                nextIds.append(parentId)

        while keepGoing:
            #print "Next IDs: " + str(nextIds)
            parentSet = dbh.scanElementSources(id, nextIds)
            nextIds = list()
            keepGoing = False

            for row in parentSet:
                parentId = row[9]
                childId = row[8]
                datamap[childId] = row

                # Prevent us from looping at root
                # 0 = event_hash and 3 = source_event_hash
                if row[8] == "ROOT" and row[9] == "ROOT":
                    continue

                if pc.has_key(parentId):
                    if childId not in pc[parentId]:
                        pc[parentId].append(childId)
                else:
                    pc[parentId] = [ childId ]
                if parentId not in nextIds:
                    nextIds.append(parentId)
                # Stop until we've found ROOT
                # 3 = source_event_hash
                if row[3] != "ROOT":
                    keepGoing = True

        #print pc
        retdata = dict()
        retdata['tree'] = sf.dataParentChildToTree(pc)
        retdata['data'] = datamap
        return json.dumps(retdata, ensure_ascii=False)
    scanelementtypediscovery.exposed = True

########NEW FILE########
