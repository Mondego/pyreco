__FILENAME__ = omnigraffle
import logging
import os

from appscript import *

class OmniGraffleSchema(object):
    """ A class that encapsulates an OmniGraffle schema file"""

    # supported formarts
    EXPORT_FORMATS = {
        "eps": "EPS",
        "pdf": "PDF",
        "png": "PNG",
        
        # FIXME
        # "svg": "SVG",
        # "tiff" : "TIFF",
        # "gif" : "GIF",
        # "jpeg" : "JPEG",
    }

    # attribute header in PDF document that contains the checksum
    PDF_CHECKSUM_ATTRIBUTE = 'OmnigraffleExportChecksum: '

    def __init__(self, og, doc):

        self.og = og
        self.doc = doc
        self.path = doc.path()

    def get_canvas_list(self):
        """
        Returns a list of names of all the canvases in the document
        """

        return [c.name() for c in self.doc.canvases()]

    def export(self, canvasname, fname, format='pdf'):
        """
        Exports one canvas named `canvasname into `fname` using `format` format.
        """

        # canvas name
        assert canvasname and len(canvasname) > 0, 'canvasname is missing'

        self.og.current_export_settings.area_type.set(k.all_graphics)

        # format
        if format not in OmniGraffleSchema.EXPORT_FORMATS:
            raise RuntimeError('Unknown format: %s' % format)

         # find canvas
        canvas = [c for c in self.doc.canvases() if c.name() == canvasname]
        if len(canvas) == 1:
            canvas = canvas[0]
        else:
            raise RuntimeError('Canvas %s does not exist in %s' %
                         (canvasname, self.doc.path()))

        # export
        self.og.windows.first().canvas.set(canvas)
        export_format = OmniGraffleSchema.EXPORT_FORMATS[format]
        # FIXME: does this return something or throw something?
        if (export_format == None):
            self.doc.save(in_=fname)
        else:
            self.doc.save(as_=export_format, in_=fname)

        logging.debug("Exported `%s' into `%s' as %s" % (canvasname, fname, format))

        # appscript.reference.CommandError: Command failed:
        # OSERROR: -50
        # MESSAGE: The document cannot be exported to the specified format.
        # COMMAND: app(u'/Applications/OmniGraffle Professional 5.app').documents[u'schemas.graffle'].save(in_=u'/Users/krikava/Documents/Research/Thesis/phd-manuscript/thesis/figures/mape-k.pdf', as_='Apple PDF pasteboard type')
        # raise RuntimeError('Failed to export canvas: %s to %s' % (canvasname, fname))

    def active_canvas_name(self):
        """
        Returns an active canvas name. The canvas that is currently selected in the the active OmniGraffle window.
        """
        window = self.og.windows.first()
        canvas = window.canvas()
        return canvas.name()

class OmniGraffle(object):

    def __init__(self):
        self.og = app('OmniGraffle 5.app')

    def active_document(self):
        self.og.activate()
        window = self.og.windows.first()
        doc = window.document()

        fname = doc.path()
        logging.debug('Active OmniGraffle file: ' + fname)

        return OmniGraffleSchema(self.og, doc)

    def open(self, fname):
        fname = os.path.abspath(fname)
        if not os.path.isfile(fname) and \
                not os.path.isfile(os.path.join(fname, "data.plist")):
            raise ValueError('File: %s does not exists' % fname)

        fname = os.path.abspath(fname)
        self.og.activate()
        doc = self.og.open(fname)

        logging.debug('Opened OmniGraffle file: ' + fname)

        return OmniGraffleSchema(self.og, doc)

########NEW FILE########
__FILENAME__ = omnigraffle_export
#!/usr/bin/env python

import os
import sys
import optparse
import logging
import tempfile
import hashlib

from Foundation import NSURL, NSMutableDictionary
from Quartz import PDFKit
from omnigraffle import *

def export(source, target, canvasname=None, format='pdf', debug=False, force=False):

    # logging
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')

    # target
    target = os.path.abspath(target)

    # mode
    export_all = os.path.isdir(target)

    # determine the canvas
    if not export_all:
        # guess from filename
        if not canvasname:
            canvasname = os.path.basename(target)
            canvasname = canvasname[:canvasname.rfind('.')]

        if not canvasname or len(canvasname) == 0:
            print >> sys.stderr, "Without canvas name, the target (-t) "\
                                       "must be a directory"
            sys.exit(1)

    # determine the format
    if not export_all:
        # guess from the suffix
        if not format:
            format = target[target.rfind('.')+1:]

    if not format or len(format) == 0:
        format = 'pdf'
    else:
        format = format.lower()

    # check source
    if not os.access(source, os.R_OK):
        print >> sys.stderr, "File: %s could not be opened for reading" % source
        sys.exit(1)

    og = OmniGraffle()
    schema = og.open(source)

    if export_all:
        namemap=lambda c, f: '%s.%s' % (c, f) if f else c

        for c in schema.get_canvas_list():
            targetfile = os.path.join(os.path.abspath(target),
                                      namemap(c, format))
            logging.debug("Exporting `%s' into `%s' as %s" %
                          (c, targetfile, format))
            export_one(schema, targetfile, c, format, force)
    else:
        export_one(schema, target, canvasname, format, force)

def export_one(schema, filename, canvasname, format='pdf', force=False):
    def _checksum(filepath):
        assert os.path.isfile(filepath), '%s is not a file' % filepath

        c = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(128), ''):
                c.update(chunk)

        return c.hexdigest()

    def _checksum_pdf(filepath):
        assert os.path.isfile(filepath), '%s is not a file' % filepath

        url = NSURL.fileURLWithPath_(filepath)
        pdfdoc = PDFKit.PDFDocument.alloc().initWithURL_(url)
        
        assert pdfdoc != None
        
        chsum = None
        attrs = pdfdoc.documentAttributes()
        if PDFKit.PDFDocumentSubjectAttribute in attrs:
            chksum = pdfdoc.documentAttributes()[PDFKit.PDFDocumentSubjectAttribute]
        else:
            return None

        if not chksum.startswith(OmniGraffleSchema.PDF_CHECKSUM_ATTRIBUTE):
            return None
        else:
            return chksum[len(OmniGraffleSchema.PDF_CHECKSUM_ATTRIBUTE):]

    def _compute_canvas_checksum(canvasname):
        tmpfile = tempfile.mkstemp(suffix='.png')[1]
        os.unlink(tmpfile)

        export_one(schema, tmpfile, canvasname, 'png')

        try:
            chksum = _checksum(tmpfile)
            return chksum
        finally:
            os.unlink(tmpfile)

    # checksum
    chksum = None
    if os.path.isfile(filename) and not force:
        existing_chksum = _checksum(filename) if format != 'pdf' \
                                              else _checksum_pdf(filename)

        new_chksum = _compute_canvas_checksum(canvasname)

        if existing_chksum == new_chksum and existing_chksum != None:
            logging.debug('Not exporting `%s` into `%s` as `%s` - canvas has not been changed' % (canvasname, filename, format))
            return False
        else:
            chksum = new_chksum

    elif format == 'pdf':
        chksum = _compute_canvas_checksum(canvasname)

    try:
        schema.export(canvasname, filename, format=format)
    except RuntimeError as e:
        print >> sys.stderr, e.message
        return False

    # update checksum
    if format == 'pdf':
        # save the checksum
        url = NSURL.fileURLWithPath_(filename)
        pdfdoc = PDFKit.PDFDocument.alloc().initWithURL_(url)
        attrs = NSMutableDictionary.alloc().initWithDictionary_(pdfdoc.documentAttributes())

        attrs[PDFKit.PDFDocumentSubjectAttribute] = \
            '%s%s' % (OmniGraffleSchema.PDF_CHECKSUM_ATTRIBUTE, chksum)

        pdfdoc.setDocumentAttributes_(attrs)
        pdfdoc.writeToFile_(filename)

    return True


def main():
    usage = "Usage: %prog [options] <source> <target>"
    parser = optparse.OptionParser(usage=usage)

    parser.add_option('-c',
                      help='canvas name. If not given it will be guessed from '
                      'the target filename unless it is a directory.',
                      metavar='NAME', dest='canvasname')
    parser.add_option('-f',
                      help='format (one of: pdf, png, svg, eps). Guessed '
                      'from the target filename suffix unless it is a '
                      'directory. Defaults to pdf',
                      metavar='FMT', dest='format')
    parser.add_option('--force', action='store_true', help='force the export',
                      dest='force')
    parser.add_option('--debug', action='store_true', help='debug',
                      dest='debug')

    (options, args) = parser.parse_args()

    if len(args) != 2:
        parser.print_help()
        sys.exit(1)

    (source, target) = args

    export(source, target, options.canvasname, options.format, 
        options.debug, options.force)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_omnigraffle_export
import os
import tempfile
import unittest
import shutil
import time
import logging

import omnigraffle
import omnigraffle_export

class OmniGraffleExportTest(unittest.TestCase):

    def __init__(self, methodName='runTest'):
        super(OmniGraffleExportTest, self).__init__(methodName)
        self.files_to_remove = []

    def setUp(self):
        self.path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'test_data', 'basic', 'test.graffle')
        # self.schema = omnigraffle.OmniGraffle().open(self.path)
        # self.assertTrue(self.schema != None)

        logging.basicConfig(level=logging.DEBUG)

    def tearDown(self):
        for f in self.files_to_remove:
            if os.path.isdir(f):
                shutil.rmtree(f)
            else:
                os.unlink(f)

    def testGetCanvasList(self):
        schema = omnigraffle.OmniGraffle().open(self.path)
        self.assertEqual(['Canvas 1', 'Canvas 2'], schema.get_canvas_list())

    def testExport(self):
        schema = omnigraffle.OmniGraffle().open(self.path)
        
        tmpfile = self.genTempFileName('pdf')

        self.assertTrue(self.schema.export('Canvas 1', tmpfile))

        self.assertFalse(self.schema.export('Canvas 1', tmpfile))

        self.files_to_remove.append(tmpfile)

    def testExportWithForceOption(self):
        schema = omnigraffle.OmniGraffle().open(self.path)

        tmpfile = self.genTempFileName('pdf')

        self.assertTrue(omnigraffle_export.export_one(schema, tmpfile, 'Canvas 1'))
        time.sleep(2)

        self.assertTrue(omnigraffle_export.export_one(schema, tmpfile, 'Canvas 1', force=True))

        self.files_to_remove.append(tmpfile)

    def testNotExportingIfNotChanged(self):
        schema = omnigraffle.OmniGraffle().open(self.path)

        tmpfile = self.genTempFileName('pdf')

        self.assertTrue(omnigraffle_export.export_one(schema, tmpfile, 'Canvas 1'))

        time.sleep(2)

        self.assertFalse(omnigraffle_export.export_one(schema, tmpfile, 'Canvas 1'))

        time.sleep(2)

        self.assertTrue(omnigraffle_export.export_one(schema, tmpfile, 'Canvas 1', force=True))

        self.files_to_remove.append(tmpfile)

    def testExportAll(self):
        tmpdir = tempfile.mkdtemp()

        omnigraffle_export.export(self.path, tmpdir)
        self.assertTrue(os.path.exists(os.path.join(tmpdir, 'Canvas 1.pdf')))
        self.assertTrue(os.path.exists(os.path.join(tmpdir, 'Canvas 2.pdf')))

        self.files_to_remove.append(tmpdir)

    @staticmethod
    def genTempFileName(suffix):
        tmpfile = tempfile.mkstemp(suffix='.pdf')[1]
        os.unlink(tmpfile)

        return tmpfile

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
