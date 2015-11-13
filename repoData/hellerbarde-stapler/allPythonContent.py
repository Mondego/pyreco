__FILENAME__ = commands
"""Module containing the actual commands stapler understands."""

import math
import os.path
import os

from pyPdf import PdfFileWriter, PdfFileReader

from . import CommandError, iohelper
import staplelib


def select(args, inverse=False):
    """
    Concatenate files / select pages from files.

    inverse=True excludes rather than includes the selected pages from
    the file.
    """

    filesandranges = iohelper.parse_ranges(args[:-1])
    outputfilename = args[-1]
    verbose = staplelib.OPTIONS.verbose

    if not filesandranges or not outputfilename:
        raise CommandError("Both input and output filenames are required.")

    output = PdfFileWriter()
    try:
        for input in filesandranges:
            pdf = input['pdf']
            if verbose:
                print input['name']

            # empty range means "include all pages"
            if not inverse:
                pagerange = input['pages'] or [
                    (p, iohelper.ROTATION_NONE) for p in
                    range(1, pdf.getNumPages() + 1)]
            else:
                excluded = [p for p, r in input['pages']]
                pagerange = [(p, iohelper.ROTATION_NONE) for p in
                             range(1, pdf.getNumPages() + 1) if
                             p not in excluded]

            for pageno, rotate in pagerange:
                if 1 <= pageno <= pdf.getNumPages():
                    if verbose:
                        print "Using page: {} (rotation: {} deg.)".format(
                            pageno, rotate)
                    
                    output.addPage(pdf.getPage(pageno-1)
                                   .rotateClockwise(rotate))
                else:
                    raise CommandError("Page {} not found in {}.".format(
                        pageno, input['name']))

    except Exception, e:
        raise CommandError(e)

    if os.path.isabs(outputfilename):
        iohelper.write_pdf(output, outputfilename)
    else:
        iohelper.write_pdf(output, staplelib.OPTIONS.destdir + 
                           os.sep + outputfilename)


def delete(args):
    """Concatenate files and remove pages from files."""

    return select(args, inverse=True)


def split(args):
    """Burst an input file into one file per page."""

    files = args
    verbose = staplelib.OPTIONS.verbose

    if not files:
        raise CommandError("No input files specified.")

    inputs = []
    try:
        for f in files:
            inputs.append(iohelper.read_pdf(f))
    except Exception, e:
        raise CommandError(e)

    filecount = 0
    pagecount = 0
    for input in inputs:
        # zero-padded output file name
        (base, ext) = os.path.splitext(os.path.basename(files[filecount]))
        output_template = ''.join([
            base, 
            '_',
            '%0', 
            str(math.ceil(math.log10(input.getNumPages()))), 
            'd',
            ext
        ])

        for pageno in range(input.getNumPages()):
            output = PdfFileWriter()
            output.addPage(input.getPage(pageno))

            outputname = output_template % (pageno + 1)
            if verbose:
                print outputname
            iohelper.write_pdf(output, staplelib.OPTIONS.destdir + 
                               os.sep + outputname)
            pagecount += 1
        filecount += 1

    if verbose:
        print "\n{} page(s) in {} file(s) processed.".format(
            pagecount, filecount)


def info(args):
    """Display Metadata content for all input files."""
    files = args

    if not files:
        raise CommandError("No input files specified.")

    for f in files:
        pdf = iohelper.read_pdf(f)
        print "*** Metadata for {}".format(f)
        print
        info = pdf.documentInfo
        if info:
            for name, value in info.items():
                print "    {}:  {}".format(name, value)
        else:
            print "    (No metadata found.)"
        print

########NEW FILE########
__FILENAME__ = iohelper
"""Helper functions for user-supplied arguments and file I/O."""

import getpass
import os.path
import re
import sys

from pyPdf import PdfFileWriter, PdfFileReader

from . import CommandError
import staplelib


ROTATION_NONE = 0
ROTATION_RIGHT = 90
ROTATION_TURN = 180
ROTATION_LEFT = 270
ROTATIONS = {'u': ROTATION_NONE,
             'r': ROTATION_RIGHT,
             'd': ROTATION_TURN,
             'l': ROTATION_LEFT}


def read_pdf(filename):
    """Open a PDF file with pyPdf."""
    if not os.path.exists(filename):
        raise CommandError("{} does not exist".format(filename))
    pdf = PdfFileReader(file(filename, "rb"))
    if pdf.isEncrypted:
        while True:
            pw = prompt_for_pw(filename)
            matched = pdf.decrypt(pw)
            if matched:
                break
            else:
                print "The password did not match."
    return pdf


def write_pdf(pdf, filename):
    """Write the content of a PdfFileWriter object to a file."""
    if os.path.exists(filename):
        raise CommandError("File already exists: {}".format(filename))

    opt = staplelib.OPTIONS
    if opt:
        if opt.ownerpw or opt.userpw:
            pdf.encrypt(opt.userpw or '', opt.ownerpw)

    outputStream = file(filename, "wb")
    pdf.write(outputStream)
    outputStream.close()


def prompt_for_pw(filename):
    """Prompt the user for the password to access an input file."""
    print 'Please enter a password to decrypt {}.'.format(filename)
    print '(The password will not be shown. Press ^C to cancel).'

    try:
        return getpass.getpass('--> ')
    except KeyboardInterrupt:
        sys.stderr.write('Aborted by user.\n')
        sys.exit(2)


def check_input_files(files):
    """Make sure all input files exist."""

    for filename in files:
        if not os.path.exists(filename):
            raise CommandError("{} does not exist".format(filename))


def check_output_file(filename):
    """Make sure the output file does not exist."""

    if os.path.exists(filename):
        raise CommandError("File already exists: {}".format(filename))


def parse_ranges(files_and_ranges):
    """Parse a list of filenames followed by ranges."""

    operations = []
    for inputname in files_and_ranges:
        if inputname.lower().endswith('.pdf'):
            operations.append({"name": inputname,
                               "pdf": read_pdf(inputname),
                               "pages": []})
        else:
            match = re.match('([0-9]+|end)(?:-([0-9]+|end))?([LRD]?)',
                                inputname)
            if not match:
                raise CommandError('Invalid range: {}'.format(inputname))

            current = operations[-1]
            max_page = current['pdf'].getNumPages()
            # allow "end" as alias for the last page
            replace_end = lambda page: (
                max_page if page.lower() == 'end' else int(page))
            begin = replace_end(match.group(1))
            end = replace_end(match.group(2)) if match.group(2) else begin

            rotate = ROTATIONS.get((match.group(3) or 'u').lower())

            if begin > max_page or end > max_page:
                raise CommandError(
                    "Range {}-{} exceeds maximum page number "
                    "{} of file {}".format(
                        begin, end, max_page, current['name']))

            # negative ranges sort pages backwards
            if begin < end:
                pagerange = range(begin, end + 1)
            else:
                pagerange = range(end, begin + 1)[::-1]

            for p in pagerange:
                current['pages'].append((p, rotate))

    return operations

########NEW FILE########
__FILENAME__ = stapler
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Main stapler dispatcher."""

from optparse import OptionParser
import os
import sys

from . import commands, CommandError
import staplelib


USAGE = """
usage: %prog [options] mode input.pdf ... [output.pdf]

Modes:
cat/sel: <inputfile> [<pagerange>] ... (output needed)
    Select the given pages/ranges from input files.
    No range means all pages.
del: <inputfile> [<pagerange>[<rotation>]] ... (output needed)
    Select all but the given pages/ranges from input files.
burst/split: <inputfile> ... (no output needed)
    Create one file per page in input pdf files (no output needed)
info: <inputfile> ... (no output needed)
    Display PDF metadata

Page ranges:
    n - single numbers mean single pages (e.g., 15)
    n-m - page ranges include the entire specified range (e.g. 1-6)
    m-n - negative ranges sort pages backwards (e.g., 6-3)

Extended page range options:
    ...-end will be replaced with the last page in the file
    R, L, or D will rotate the respective range +90, -90, or 180 degrees,
        respectively. (e.g., 1-15R)
""".strip()

# command line option parser
parser = OptionParser(usage=USAGE)
parser.add_option('-o', '--ownerpw', action='store', dest='ownerpw',
                  help='Set owner password to encrypt output file with',
                  default=None)
parser.add_option('-u', '--userpw', action='store', dest='userpw',
                  help='Set user password to encrypt output file with',
                  default=None)
parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
                  default=False)
parser.add_option('-d', '--destdir', dest="destdir", default="." + os.sep,
                  help="directory where to store output file",)


def main():
    """
    Handle all command line arguments and pass them on to the respective
    commands.
    """
    (staplelib.OPTIONS, args) = parser.parse_args()

    if not os.path.exists(staplelib.OPTIONS.destdir):
        print_error("cannot find output directory named {}".format(
                    staplelib.OPTIONS.destdir))

    if (len(args) < 2):
        print_error("Not enough arguments", show_usage=True)

    modes = {
        "cat": commands.select,
        "sel": commands.select,
        "split": commands.split,
        "burst": commands.split,
        "del": commands.delete,
        "info": commands.info,
    }

    mode = args[0]
    args = args[1:]
    if not mode in modes:
        print_error('Please enter a valid mode', show_usage=True)

    if staplelib.OPTIONS.verbose:
        print "Mode: %s" % mode

    # dispatch call to known subcommand
    try:
        modes[mode](args)
    except CommandError, e:
        print_error(e)


def print_error(msg, code=1, show_usage=False):
    """Pretty-print an error to the user."""
    sys.stderr.write(str('Error: {}\n'.format(msg)))

    if show_usage:
        sys.stderr.write("\n{}\n".format(parser.get_usage()))

    sys.exit(code)

########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/env python

import os.path
import shutil
from subprocess import check_call
import tempfile
import unittest

from pyPdf import PdfFileReader


HERE = os.path.abspath(os.path.dirname(__file__))
TESTFILE_DIR = os.path.join(HERE, 'testfiles')
STAPLER = os.path.join(HERE, '..', 'stapler')
ONEPAGE_PDF = os.path.join(TESTFILE_DIR, '1page.pdf')
FIVEPAGE_PDF = os.path.join(TESTFILE_DIR, '5page.pdf')


class TestStapler(unittest.TestCase):
    """Some unit tests for the stapler tool."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.outputfile = os.path.join(self.tmpdir, 'output.pdf')
        os.chdir(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        os.chdir(HERE)

    def test_cat(self):
        """Make sure files are properly concatenated."""
        check_call([STAPLER, 'cat', ONEPAGE_PDF, FIVEPAGE_PDF,
                    self.outputfile])
        self.assert_(os.path.isfile(self.outputfile))
        pdf = PdfFileReader(file(self.outputfile, 'rb'))
        self.assertEqual(pdf.getNumPages(), 6)

    def test_split(self):
        """Make sure a file is properly split into pages."""
        check_call([STAPLER, 'split', FIVEPAGE_PDF])

        filelist = os.listdir(self.tmpdir)
        self.assertEqual(len(filelist), 5)
        for f in os.listdir(self.tmpdir):
            pdf = PdfFileReader(file(os.path.join(self.tmpdir, f), 'rb'))
            self.assertEqual(pdf.getNumPages(), 1)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
