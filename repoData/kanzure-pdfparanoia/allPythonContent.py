__FILENAME__ = core
# -*- coding: utf-8 -*-
"""
pdfparanoia.core
~~~~~~~~~~~~~~~

This module provides most of the heavy lifting of pdfparanoia.

"""

import sys
import inspect

from .parser import (
    parse_pdf,
    parse_content,
)

from .plugin import Plugin

from pdfparanoia.plugins import *

def find_plugins():
    """
    Returns a list of all compatible plugins.
    """
    def inspection(thing):
        iswanted = inspect.isclass(thing)
        iswanted = iswanted and issubclass(thing, Plugin)
        iswanted = iswanted and thing is not Plugin
        return iswanted
    plugins = inspect.getmembers(sys.modules[__name__], inspection)
    plugins = [each[1] for each in plugins]
    return plugins

def scrub(obj, verbose=False):
    """
    Removes watermarks from a pdf and returns the resulting pdf as a string.
    """
    # reset the file handler
    if hasattr(obj, "seek"):
        obj.seek(0)
    else:
        obj = open(obj, "rb")

    # load up the raw bytes
    content = obj.read()

    # get a list of plugins that will manipulate this paper
    plugins = find_plugins()

    # clean this pdf as much as possible
    for plugin in plugins:
        content = plugin.scrub(content, verbose=verbose)

    return content


########NEW FILE########
__FILENAME__ = eraser
# -*- coding: utf-8 -*-
"""
pdfparanoia.eraser
~~~~~~~~~~~~~~~

Tools to erase things from pdfs by direct manipulation of the pdf format.

"""

def manipulate_pdf(content, objid, callback, *args):
    """
    Iterates through a pdf looking for the object with the objid id. When the
    object is found, callback is called with a reference to the current list of
    output lines.
    """
    outlines = []
    content = content.replace("\r\n", "\n")
    lines = content.split("\n")
    last_line = None
    skip_mode = False
    for line in lines:
        if line == "":
            outlines.append("")
            continue
        if not skip_mode:
            if last_line in ["endobj", "endobj ", None]:
                if line[-3:] == "obj" or line[-4:] == "obj " or " obj <<" in line[0:50] or " obj<<" in line[0:50]:
                    if line.startswith(str(objid) + " "):
                        skip_mode = True
                        last_line = line
                        callback(outlines, *args)
                        continue
            outlines.append(line)
        elif skip_mode:
            if line == "endobj" or line == "endobj ":
                skip_mode = False
        last_line = line
    output = "\n".join(outlines)
    return output

def remove_object_by_id(content, objid):
    """
    Deletes an object from a pdf. Mostly streams and FlateDecode stuff.
    """
    def _remove_object(outlines): pass
    output = manipulate_pdf(content, objid, _remove_object)
    return output

def replace_object_with(content, objid, replacement):
    """
    Replaces an object from a pdf. Mostly streams. This is useful for replacing
    an encoded object with a plaintext object.
    """
    def _replace_object_with(outlines, details):
        objid = details["objid"]
        replacement = details["replacement"]

        output = str(objid) + " 0 obj\n"
        output += "<</Length " + str(len(replacement)+2) + ">>stream\n"
        output += replacement
        output += "\nendstream\nendobj\n"

        for line in output.split("\n"):
            outlines.append(line)

    output = manipulate_pdf(content, objid, _replace_object_with, {"objid": objid, "replacement": replacement})
    return output


########NEW FILE########
__FILENAME__ = parser
# -*- coding: utf-8 -*-
"""
pdfparanoia.parser
~~~~~~~~~~~~~~~

Deals with the existential nature of parsing pdfs.

"""

try:
    from StringIO import StringIO
except ImportError: # py3k
    from io import StringIO, BytesIO

# Maybe one day pdfquery will be able to save pdf.
# from pdfquery import PDFQuery

import pdfminer.pdfparser
import pdfminer.pdfdocument

from .eraser import replace_object_with

def parse_pdf(handler):
    """
    Parses a PDF via pdfminer.
    """
    # reset to the beginning of the data
    handler.seek(0)

    # setup for parsing
    parser = pdfminer.pdfparser.PDFParser(handler)
    doc = pdfminer.pdfdocument.PDFDocument(parser)

    # actual parsing
    doc.initialize()

    return doc

def parse_content(content):
    """
    Parses a PDF via pdfminer from a string. There are some problems with
    pdfminer accepting StringIO objects, so this is a temporary hack.
    """
    stream = StringIO(content)
    return parse_pdf(stream)

def deflate(content):
    """
    Converts all FlateDecode streams into plaintext streams. This significantly
    increases the size of a pdf, but it's useful for debugging and searching
    for how watermarks are implemented.

    Not all elements are preserved in the resulting document. This is for
    debugging only.
    """
    # parse the pdf
    pdf = parse_content(content)

    # get a list of all object ids
    xref = pdf.xrefs[0]
    objids = xref.get_objids()

    # store new replacements
    replacements = []

    # scan through each object looking for things to deflate
    for objid in objids:
        obj = pdf.getobj(objid)
        if hasattr(obj, "attrs"):
            if obj.attrs.has_key("Filter") and str(obj.attrs["Filter"]) == "/FlateDecode":
                obj.decode()
                data = obj.data
                if len(data) < 1000:
                    replacements.append([objid, data])

    # apply the replacements to the document
    for (objid, replacement) in replacements:
        content = replace_object_with(content, objid, replacement)

    return content


########NEW FILE########
__FILENAME__ = plugin
# -*- coding: utf-8 -*-
"""
pdfparanoia.plugin
~~~~~~~~~~~~~~~

Defines how plugins work.

"""

class Plugin:
    @classmethod
    def scrub(cls, content, verbose=False):
        """
        Removes watermarks from the given pdf.
        """
        raise NotImplementedError("must be implemented by the subclass")


########NEW FILE########
__FILENAME__ = aip
# -*- coding: utf-8 -*-

import sys

from copy import copy

from ..parser import parse_content
from ..eraser import remove_object_by_id
from ..plugin import Plugin

class AmericanInstituteOfPhysics(Plugin):
    """
    American Institute of Physics
    ~~~~~~~~~~~~~~~

    These watermarks are pretty basic, but sometimes they don't have indexes
    attached for whatever reason.
    """

    @classmethod
    def scrub(cls, content, verbose=0):
        evil_ids = []

        # parse the pdf into a pdfminer document
        pdf = parse_content(content)

        # get a list of all object ids
        xref = pdf.xrefs[0]
        objids = xref.get_objids()

        # check each object in the pdf
        for objid in objids:
            # get an object by id
            obj = pdf.getobj(objid)

            if hasattr(obj, "attrs"):
                # watermarks tend to be in FlateDecode elements
                if "Filter" in obj.attrs and str(obj.attrs["Filter"]) == "/FlateDecode":
                    length = obj.attrs["Length"]

                    # the watermark is never very long
                    if length < 1000:
                        #rawdata = copy(obj.rawdata)
                        data = copy(obj.get_data())

                        phrase="Redistribution subject to AIP license or copyright"
                        if phrase in str(data):
                            if verbose >= 2:
                                sys.stderr.write("%s: Found object %s with %r: %r; omitting..." % (cls.__name__, objid, phrase, data))
                            elif verbose >= 1:
                                sys.stderr.write("%s: Found object %s with %r; omitting..." % (cls.__name__, objid, phrase,))

                            evil_ids.append(objid)

        for objid in evil_ids:
            content = remove_object_by_id(content, objid)

        return content


########NEW FILE########
__FILENAME__ = ieee
# -*- coding: utf-8 -*-

from copy import copy
import sys

from ..parser import parse_content
from ..eraser import remove_object_by_id
from ..plugin import Plugin

class IEEEXplore(Plugin):
    """
    IEEE Xplore
    ~~~~~~~~~~~~~~~

    """

    @classmethod
    def scrub(cls, content, verbose=0):
        evil_ids = []

        # parse the pdf into a pdfminer document
        pdf = parse_content(content)

        # get a list of all object ids
        xref = pdf.xrefs[0]
        objids = xref.get_objids()

        # check each object in the pdf
        for objid in objids:
            # get an object by id
            obj = pdf.getobj(objid)

            if hasattr(obj, "attrs"):
                # watermarks tend to be in FlateDecode elements
                if "Filter" in obj.attrs and str(obj.attrs["Filter"]) == "/FlateDecode":
                    #length = obj.attrs["Length"]
                    #rawdata = copy(obj.rawdata)
                    data = copy(obj.get_data())

                    phrase= "Authorized licensed use limited to: "
                    if phrase in str(data):
                        if verbose >= 2:
                            sys.stderr.write("%s: Found object %s with %r: %r; omitting..." % (cls.__name__, objid, phrase, data[data.index(phrase):data.index(phrase)+1000]))
                        elif verbose >= 1:
                            sys.stderr.write("%s: Found object %s with %r; omitting..." % (cls.__name__, objid, phrase,))

                        evil_ids.append(objid)

        for objid in evil_ids:
            content = remove_object_by_id(content, objid)

        return content


########NEW FILE########
__FILENAME__ = jstor
# -*- coding: utf-8 -*-

from copy import copy

import sys

from ..parser import parse_content
from ..eraser import (
    replace_object_with,
)
from ..plugin import Plugin

from pdfminer.pdftypes import PDFObjectNotFound

class JSTOR(Plugin):
    """
    JSTOR
    ~~~~~~~~~~~~~~~

    JSTOR watermarks a first page with an "Accessed" date, lots of TC barf, and
    then also a watermark at the bottom of each page with a timestamp.

    Watermarks removed:
        * "Accessed" timestamp on the front page
        * footer watermarks on each page

    This was primary written for JSTOR pdfs generated by:
         /Producer (itext-paulo-155 \(itextpdf.sf.net-lowagie.com\))
    """

    # these terms appear on a page that has been watermarked
    requirements = [
        "All use subject to ",
        "JSTOR Terms and Conditions",
        "This content downloaded  on",
    ]

    @classmethod
    def scrub(cls, content, verbose=0):
        replacements = []

        # jstor has certain watermarks only on the first page
        page_id = 0

        # parse the pdf into a pdfminer document
        pdf = parse_content(content)

        # get a list of all object ids
        xref = pdf.xrefs[0]
        objids = xref.get_objids()

        # check each object in the pdf
        for objid in objids:
            # get an object by id
            try:
                obj = pdf.getobj(objid)

                if hasattr(obj, "attrs"):
                    if obj.attrs.has_key("Filter") and str(obj.attrs["Filter"]) == "/FlateDecode":
                        data = copy(obj.get_data())

                        # make sure all of the requirements are in there
                        if all([requirement in data for requirement in JSTOR.requirements]):
                            better_content = data

                            # remove the date
                            startpos = better_content.find("This content downloaded ")
                            endpos = better_content.find(")", startpos)
                            segment = better_content[startpos:endpos]
                            if verbose >= 2 and replacements:
                                sys.stderr.write("%s: Found object %s with %r: %r; omitting..." % (cls.__name__, objid, cls.requirements, segment))

                            better_content = better_content.replace(segment, "")

                            # it looks like all of the watermarks are at the end?
                            better_content = better_content[:-160]

                            # "Accessed on dd/mm/yyy hh:mm"
                            #
                            # the "Accessed" line is only on the first page
                            #
                            # it's based on /F2
                            #
                            # This would be better if it could be decoded to
                            # actually search for the "Accessed" text.
                            if page_id == 0 and "/F2 11 Tf\n" in better_content:
                                startpos = better_content.rfind("/F2 11 Tf\n")
                                endpos = better_content.find("Tf\n", startpos+5)

                                if verbose >= 2 and replacements:
                                    sys.stderr.write("%s: Found object %s with %r: %r; omitting..." % (cls.__name__, objid, cls.requirements, better_content[startpos:endpos]))

                                better_content = better_content[0:startpos] + better_content[endpos:]

                            replacements.append([objid, better_content])

                            page_id += 1
            except PDFObjectNotFound, e:
                print >>sys.stderr, 'Missing object: %r' % e

        if verbose >= 1 and replacements:
            sys.stderr.write("%s: Found objects %s with %r; omitting..." % (cls.__name__, [deets[0] for deets in replacements], cls.requirements))

        for deets in replacements:
            objid = deets[0]
            replacement = deets[1]
            content = replace_object_with(content, objid, replacement)

        return content


########NEW FILE########
__FILENAME__ = rsc
# -*- coding: utf-8 -*-

from copy import copy
import sys
from ..parser import parse_content
from ..plugin import Plugin
import base64

class RoyalSocietyOfChemistry(Plugin):
    """
    RoyalSocietyOfChemistry
    ~~~~~~~~~~~~~~~

    RSC watermarks each PDF with a "Downloaded" date and the name
    of the institution from which the PDF was downloaded.
    
    Watermarks removed:
        * "Downloaded by" watermark and timestamp on the each page
        * "Published on" watermark on the side of each page

    This was primary written for RSC PDF's from http://pubs.rsc.org
    """
        
    @classmethod
    def scrub(cls, content, verbose=0):
        replacements = []
        
        # List of watermark strings to remove
        watermarks = [
            "Downloaded by ",
            "Downloaded on ",
            "Published on ",
            #"View Article Online",
            #"Journal Homepage",
            #"Table of Contents for this issue",
        ]

        # Confirm the PDF is from the RSC
        if "pubs.rsc.org" in content:
            
            # parse the pdf into a pdfminer document
            pdf = parse_content(content)

            # get a list of all object ids
            xref = pdf.xrefs[0]
            objids = xref.get_objids()

            # check each object in the pdf
            for objid in objids:
                # get an object by id
                obj = pdf.getobj(objid)

                if hasattr(obj, "attrs"):
                    # watermarks tend to be in FlateDecode elements
                    if obj.attrs.has_key("Filter") and str(obj.attrs["Filter"]) == "/FlateDecode":
                        rawdata = copy(obj.rawdata)
                        data = copy(obj.get_data())

                        # Check if any of the watermarks are in the current object
                        for phrase in watermarks:
                            if phrase in data:
                                if verbose >= 2:
                                    sys.stderr.write("%s: Found object %s with %r: %r; omitting...\n" % (cls.__name__, objid, phrase, data[data.index(phrase):data.index(phrase)+1000]))
                                elif verbose >= 1:
                                    sys.stderr.write("%s: Found object %s with %r; omitting...\n" % (cls.__name__, objid, phrase)) 
                                
                                # We had a match so replace the watermark data with an empty string                 
                                replacements.append([rawdata, ""])
            
        for deets in replacements:
            # Directly replace the stream data in binary encoded object
            content = content.replace( deets[0], deets[1])

        return content



########NEW FILE########
__FILENAME__ = sciencemagazine
# -*- coding: utf-8 -*-

from copy import copy
import sys

from ..parser import parse_content
from ..eraser import remove_object_by_id
from ..plugin import Plugin

class ScienceMagazine(Plugin):
    """
    Science Magazine
    ~~~~~~~~~~~~~~~

    Remove ads from academic papers. :(
    """

    # TODO: better confirmation that the paper is from sciencemag. Look for
    # "oascentral" in one of the URIs, since the ads are all hyperlinked to
    # that server.

    @classmethod
    def scrub(cls, content, verbose=0):
        evil_ids = []

        # parse the pdf into a pdfminer document
        pdf = parse_content(content)

        # get a list of all object ids
        xref = pdf.xrefs[0]
        objids = xref.get_objids()

        # check each object in the pdf
        for objid in objids:
            # get an object by id
            obj = pdf.getobj(objid)

            if hasattr(obj, "attrs"):
                if ("Width" in obj.attrs) and str(obj.attrs["Width"]) == "432":
                    if "Height" in obj.attrs and str(obj.attrs["Height"]) == "230":
                        evil_ids.append(objid)

        if len(evil_ids) > 1:
            raise Exception("too many ads detected on the page, please double check?")

        for objid in evil_ids:
            content = remove_object_by_id(content, objid)

        return content

########NEW FILE########
__FILENAME__ = spie
# -*- coding: utf-8 -*-

from copy import copy
import sys

from ..parser import parse_content
from ..plugin import Plugin

class SPIE(Plugin):
    """
    Society of Photo-Optical Instrumentation Engineers
    ~~~~~~~~~~~~~~~

    These watermarks are shown on each page, but are only defined in one place.
    Also, there seems to be some interference from some of the other
    pdfparanoia plugins causing the deletion of images in the document.
    Side-effects need to be better accounted for.

    """

    @classmethod
    def scrub(cls, content, verbose=False):
        evil_ids = []

        # parse the pdf into a pdfminer document
        pdf = parse_content(content)

        # get a list of all object ids
        xrefs = pdf._parser.read_xref()
        xref = xrefs[0]
        objids = xref.get_objids()

        # check each object in the pdf
        for objid in objids:
            # get an object by id
            obj = pdf.getobj(objid)

            if hasattr(obj, "attrs"):
                # watermarks tend to be in FlateDecode elements
                if obj.attrs.has_key("Filter") and str(obj.attrs["Filter"]) == "/FlateDecode":
                    data = copy(obj.get_data())

                    phrase="Downloaded From:"
                    if phrase in data:
                        if verbose:
                            sys.stderr.write("%s: found object %s with %r; omitting..." % (cls.__name__, objid, phrase))
                        evil_ids.append(objid)

        for objid in evil_ids:
            # for some reason SPIE pdfs are broken by this, images are randomly removed
            #content = remove_object_by_id(content, objid)
            continue

        return content


########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
"""
pdfparanoia.utils
~~~~~~~~~~~~~~~

This module provides utility functions used both in pdfparanoia and that are
also useful for external consumption.
"""


########NEW FILE########
__FILENAME__ = test_aip
# -*- coding: utf-8 -*-

import unittest
import pdfparanoia

class AmericanInstituteOfPhysicsTestCase(unittest.TestCase):
    def test_aip(self):
        file_handler = open("tests/samples/aip/a7132c0d62d7c00e92e8e0553f480556.pdf", "rb")
        content = file_handler.read()
        self.assertIn("\n4 0 obj\n", content)
        self.assertIn("\n10 0 obj\n", content)

        output = pdfparanoia.plugins.AmericanInstituteOfPhysics.scrub(content)
        self.assertNotIn("\n4 0 obj\n", output)
        self.assertNotIn("\n10 0 obj\n", output)


########NEW FILE########
__FILENAME__ = test_eraser
# -*- coding: utf-8 -*-

import unittest
from pdfparanoia.eraser import remove_object_by_id

class EraserTestCase(unittest.TestCase):
    def test_remove_object_by_id(self):
        content = ""
        output = remove_object_by_id(content, 1)
        self.assertEqual(content, output)

        content = ""
        output = remove_object_by_id(content, 2)
        self.assertEqual(content, output)

        content = ""
        output = remove_object_by_id(content, 100)
        self.assertEqual(content, output)

        content = "1 0 obj\nthings\nendobj\nleftovers"
        output = remove_object_by_id(content, 2)
        self.assertEqual(content, output)

        content = "1 0 obj\nthings\nendobj\nleftovers"
        output = remove_object_by_id(content, 1)
        self.assertEqual("leftovers", output)


########NEW FILE########
__FILENAME__ = test_ieee
# -*- coding: utf-8 -*-

import unittest
import pdfparanoia

class IEEEXploreTestCase(unittest.TestCase):
    def test_ieee(self):
        file_handler = open("tests/samples/ieee/9984106e01b63d996f19f383b8d96f02.pdf", "rb")
        content = file_handler.read()
        self.assertIn("\n4 0 obj", content)
        self.assertIn("\n7 0 obj", content)

        output = pdfparanoia.plugins.IEEEXplore.scrub(content)
        self.assertNotIn("\n19 0 obj", output)
        self.assertNotIn("\n37 0 obj", output)
        self.assertNotIn("\n43 0 obj", output)
        self.assertNotIn("\n53 0 obj", output)
        self.assertNotIn("\n64 0 obj", output)
        self.assertNotIn("\n73 0 obj", output)


########NEW FILE########
__FILENAME__ = test_jstor
# -*- coding: utf-8 -*-

import unittest
import pdfparanoia

class JSTORTestCase(unittest.TestCase):
    def test_jstor(self):
        file_handler = open("tests/samples/jstor/231a515256115368c142f528cee7f727.pdf", "rb")
        content = file_handler.read()
        file_handler.close()
        self.assertIn("\n18 0 obj \n", content)

        # this section will later be manipulated
        self.assertIn("\n19 0 obj \n", content)

        output = pdfparanoia.plugins.JSTOR.scrub(content)

        # FlateDecode should be replaced with a decompressed section
        self.assertIn("\n19 0 obj\n<</Length 2862>>stream", output)


########NEW FILE########
__FILENAME__ = test_rsc
# -*- coding: utf-8 -*-

import unittest
import pdfparanoia

class RoyalSocietyOfChemistryTestCase(unittest.TestCase):
    def test_rsc(self):
        file_handler = open("tests/samples/rsc/3589bf649f8bb019bd97be9880627b7c.pdf", "rb")
        content = file_handler.read()
        file_handler.close()

        # Check the PDF is from the RSC
        self.assertIn("pubs.rsc.org", content)

        output = pdfparanoia.plugins.RoyalSocietyOfChemistry.scrub(content)

        # Check the PDF was output correctly and still 
        # contains the RSC url. 
        self.assertIn("pubs.rsc.org", output)


########NEW FILE########
__FILENAME__ = test_spie
# -*- coding: utf-8 -*-

import unittest
import pdfparanoia

class SPIETestCase(unittest.TestCase):
    def test_spie(self):
        file_handler = open("tests/samples/spie/266c86e6f47e39415584450f5a3af4d0.pdf", "rb")
        content = file_handler.read()
        self.assertIn("\n46 0 obj", content)

        output = pdfparanoia.plugins.SPIE.scrub(content)
        self.assertNotIn("\n55 0 obj", output)


########NEW FILE########
