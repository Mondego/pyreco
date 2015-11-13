__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.
"""

import os, shutil, sys, tempfile
from optparse import OptionParser

tmpeggs = tempfile.mkdtemp()

usage = '''\
[DESIRED PYTHON FOR BUILDOUT] bootstrap.py [options]

Bootstraps a buildout-based project.

Simply run this script in a directory containing a buildout.cfg, using the
Python that you want bin/buildout to use.

Note that by using --setup-source and --download-base to point to
local resources, you can keep this script from going over the network.
'''

parser = OptionParser(usage=usage)
parser.add_option("-v", "--version", help="use a specific zc.buildout version")

parser.add_option("-t", "--accept-buildout-test-releases",
                  dest='accept_buildout_test_releases',
                  action="store_true", default=False,
                  help=("Normally, if you do not specify a --version, the "
                        "bootstrap script and buildout gets the newest "
                        "*final* versions of zc.buildout and its recipes and "
                        "extensions for you.  If you use this flag, "
                        "bootstrap and buildout will get the newest releases "
                        "even if they are alphas or betas."))
parser.add_option("-c", "--config-file",
                   help=("Specify the path to the buildout configuration "
                         "file to be used."))
parser.add_option("-f", "--find-links",
                   help=("Specify a URL to search for buildout releases"))


options, args = parser.parse_args()

######################################################################
# load/install distribute

to_reload = False
try:
    import pkg_resources, setuptools
    if not hasattr(pkg_resources, '_distribute'):
        to_reload = True
        raise ImportError
except ImportError:
    ez = {}

    try:
        from urllib.request import urlopen
    except ImportError:
        from urllib2 import urlopen

    exec(urlopen('http://python-distribute.org/distribute_setup.py').read(), ez)
    setup_args = dict(to_dir=tmpeggs, download_delay=0, no_fake=True)
    ez['use_setuptools'](**setup_args)

    if to_reload:
        reload(pkg_resources)
    import pkg_resources
    # This does not (always?) update the default working set.  We will
    # do it.
    for path in sys.path:
        if path not in pkg_resources.working_set.entries:
            pkg_resources.working_set.add_entry(path)

######################################################################
# Install buildout

ws  = pkg_resources.working_set

cmd = [sys.executable, '-c',
       'from setuptools.command.easy_install import main; main()',
       '-mZqNxd', tmpeggs]

find_links = os.environ.get(
    'bootstrap-testing-find-links',
    options.find_links or
    ('http://downloads.buildout.org/'
     if options.accept_buildout_test_releases else None)
    )
if find_links:
    cmd.extend(['-f', find_links])

distribute_path = ws.find(
    pkg_resources.Requirement.parse('distribute')).location

requirement = 'zc.buildout'
version = options.version
if version is None and not options.accept_buildout_test_releases:
    # Figure out the most recent final version of zc.buildout.
    import setuptools.package_index
    _final_parts = '*final-', '*final'
    def _final_version(parsed_version):
        for part in parsed_version:
            if (part[:1] == '*') and (part not in _final_parts):
                return False
        return True
    index = setuptools.package_index.PackageIndex(
        search_path=[distribute_path])
    if find_links:
        index.add_find_links((find_links,))
    req = pkg_resources.Requirement.parse(requirement)
    if index.obtain(req) is not None:
        best = []
        bestv = None
        for dist in index[req.project_name]:
            distv = dist.parsed_version
            if _final_version(distv):
                if bestv is None or distv > bestv:
                    best = [dist]
                    bestv = distv
                elif distv == bestv:
                    best.append(dist)
        if best:
            best.sort()
            version = best[-1].version
if version:
    requirement = '=='.join((requirement, version))
cmd.append(requirement)

import subprocess
if subprocess.call(cmd, env=dict(os.environ, PYTHONPATH=distribute_path)) != 0:
    raise Exception(
        "Failed to execute command:\n%s",
        repr(cmd)[1:-1])

######################################################################
# Import and run buildout

ws.add_entry(tmpeggs)
ws.require(requirement)
import zc.buildout.buildout

if not [a for a in args if '=' not in a]:
    args.append('bootstrap')

# if -c was provided, we push it back into args for buildout' main function
if options.config_file is not None:
    args[0:0] = ['-c', options.config_file]

zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
import sys, os, pkginfo, datetime

pkg_info = pkginfo.Develop(os.path.join(os.path.dirname(__file__),'..'))

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx'
    ]

intersphinx_mapping = {
    'http://docs.python.org': None,
    'http://packages.python.org/testfixtures/': None,
    # XXX - errorhandler
    # XXX - xlrd
    # XXX - xlwt
    }

# General
source_suffix = '.txt'
master_doc = 'index'
project = pkg_info.name
copyright = '2008-%s Simplistix Ltd' % datetime.datetime.now().year
version = release = pkg_info.version
exclude_trees = ['_build']
unused_docs = ['description']
pygments_style = 'sphinx'

# Options for HTML output
html_theme = 'default'
htmlhelp_basename = project+'doc'

# Options for LaTeX output
latex_documents = [
  ('index',project+'.tex', project+u' Documentation',
   'Simplistix Ltd', 'manual'),
]


########NEW FILE########
__FILENAME__ = copy
# Copyright (c) 2009-2012 Simplistix Ltd
#
# This Software is released under the MIT License:
# http://www.opensource.org/licenses/mit-license.html
# See license.txt for more details.

from xlutils.filter import process,XLRDReader,XLWTWriter

def copy(wb):
    """
    Copy an :class:`xlrd.Book` into an :class:`xlwt.Workbook` preserving as much
    information from the source object as possible.

    See the :doc:`copy` documentation for an example.
    """
    w = XLWTWriter()
    process(
        XLRDReader(wb,'unknown.xls'),
        w
        )
    return w.output[0][1]

########NEW FILE########
__FILENAME__ = display
# Copyright (c) 2008 Simplistix Ltd
#
# This Software is released under the MIT License:
# http://www.opensource.org/licenses/mit-license.html
# See license.txt for more details.

import xlrd

def quoted_sheet_name(sheet_name, encoding='ascii'):
    if "'" in sheet_name:
        qsn = "'" + sheet_name.replace("'", "''") + "'"
    elif " " in sheet_name:
        qsn = "'" + sheet_name + "'"
    else:
        qsn = sheet_name
    return qsn.encode(encoding, 'replace')
   
def cell_display(cell, datemode=0, encoding='ascii'):
    cty = cell.ctype
    if cty == xlrd.XL_CELL_EMPTY:
        return 'undefined'
    if cty == xlrd.XL_CELL_BLANK:
        return 'blank'
    if cty == xlrd.XL_CELL_NUMBER:
        return 'number (%.4f)' % cell.value
    if cty == xlrd.XL_CELL_DATE:
        try:
            return "date (%04d-%02d-%02d %02d:%02d:%02d)" \
                % xlrd.xldate_as_tuple(cell.value, datemode)
        except xlrd.xldate.XLDateError:
            return "date? (%.6f)" % cell.value
    if cty == xlrd.XL_CELL_TEXT:
        return "text (%s)" % cell.value.encode(encoding, 'replace')
    if cty == xlrd.XL_CELL_ERROR:
        if cell.value in xlrd.error_text_from_code:
            return "error (%s)" % xlrd.error_text_from_code[cell.value]
        return "unknown error code (%r)" % cell.value
    if cty == xlrd.XL_CELL_BOOLEAN:
        return "logical (%s)" % ['FALSE', 'TRUE'][cell.value]
    raise Exception("Unknown Cell.ctype: %r" % cty)

########NEW FILE########
__FILENAME__ = filter
# Copyright (c) 2008-2009 Simplistix Ltd
#
# This Software is released under the MIT License:
# http://www.opensource.org/licenses/mit-license.html
# See license.txt for more details.

import logging
import os
import xlrd,xlwt

from functools import partial
from glob import glob
from shutil import rmtree
from tempfile import mkdtemp
from xlutils.display import quoted_sheet_name,cell_display
from xlutils.margins import cells_all_junk
from xlwt.Style import default_style
logger = logging.getLogger('xlutils.filter')

class BaseReader:
    "A base reader good for subclassing."

    def get_filepaths(self):
        """
        This is the most common method to implement. It must return an
        interable sequence of paths to excel files.
        """
        raise NotImplementedError

    def get_workbooks(self):
        """
        If the data to be processed is not stored in files or if
        special parameters need to be passed to :func:`xlrd.open_workbook`
        then this method must be overriden.
        Any implementation must return an iterable sequence of tuples.
        The first element of which must be an :class:`xlrd.Book` object and the
        second must be the filename of the file from which the book
        object came.
        """
        for path in self.get_filepaths():
            yield (
                xlrd.open_workbook(
                    path,
                    formatting_info=1,
                    on_demand=True,
                    ragged_rows=True),
                os.path.split(path)[1]
                )

    def __call__(self, filter):
        """
        Once instantiated, a reader will be called and have the first
        filter in the chain passed to its :meth:`__call__` method.
        The implementation of this method
        should call the appropriate methods on the filter based on the
        cells found in the :class:`~xlrd.Book` objects returned from the
        :meth:`get_workbooks` method.
        """
        filter.start()
        for workbook,filename in self.get_workbooks():
            filter.workbook(workbook,filename)
            for sheet_x in range(workbook.nsheets):
                sheet = workbook.sheet_by_index(sheet_x)
                filter.sheet(sheet,sheet.name)
                for row_x in xrange(sheet.nrows):
                    filter.row(row_x,row_x)
                    for col_x in xrange(sheet.row_len(row_x)):
                        filter.cell(row_x,col_x,row_x,col_x)
                if workbook.on_demand:
                    workbook.unload_sheet(sheet_x)
        filter.finish()
    
class BaseFilterInterface:
    """
    This is the filter interface that shows the correct way to call the 
    next filter in the chain. 
    The `next` attribute is set up by the :func:`process` function.
    It can make a good base class for a new filter, but subclassing
    :class:`BaseFilter` is often a better idea!
    """

    def start(self):
        """
        This method is called before processing of a batch of input.
        This allows the filter to initialise any required data
        structures and dispose of any existing state from previous
        batches. 

        It is called once before the processing of any workbooks by
        the included reader implementations.

        This method can be called at any time. One common use is to
        reset all the filters in a chain in the event of an error
        during the processing of a `rdbook`.

        Implementations of this method should be extremely robust and
        must ensure that they call the :meth:`start` method of the next filter
        in the chain regardless of any work they do.
        """
        self.next.start()
        
    def workbook(self,rdbook,wtbook_name):
        """
        This method is called every time processing of a new
        workbook starts.

        :param rdbook: the :class:`~xlrd.Book` object from which the new workbook
                 should be created.

        :param wtbook_name: the name of the workbook into which content
                      should be written.
        """
        self.next.workbook(rdbook,wtbook_name)
   
    def sheet(self,rdsheet,wtsheet_name):
        """
        This method is called every time processing of a new
        sheet in the current workbook starts.

        :param rdsheet: the :class:`~xlrd.sheet.Sheet` object from which the new
                  sheet should be created.

        :param wtsheet_name: the name of the sheet into which content
                       should be written.
        """
        self.next.sheet(rdsheet,wtsheet_name)
       
    def set_rdsheet(self,rdsheet):
        """
        This is only ever called by a filter that
        wishes to change the source of cells mid-way through writing a
        sheet.

        :param rdsheet: the :class:`~xlrd.sheet.Sheet` object from which cells from
                  this point forward should be read from.

        """
        self.next.set_rdsheet(rdsheet)
       
    def row(self,rdrowx,wtrowx):
        """
        This is called every time processing of a new
        row in the current sheet starts.
        It is primarily for copying row-based formatting from the
        source row to the target row.

        :param rdrowx: the index of the row in the current sheet from which
                 information for the row to be written should be
                 copied.

        :param wtrowx: the index of the row in sheet to be written to which
                 information should be written for the row being read.
        """
        self.next.row(rdrowx,wtrowx)

    def cell(self,rdrowx,rdcolx,wtrowx,wtcolx):
        """
        This is called for every cell in the sheet being processed.
        This is the most common method in which filtering and queuing
        of onward calls to the next filter takes place.

        :param rdrowx: the index of the row to be read from in the current sheet. 
        :param rdcolx: the index of the column to be read from in the current sheet. 
        :param wtrowx: the index of the row to be written to in the current output sheet. 
        :param wtcolx: the index of the column to be written to in the current output sheet. 
        """
        self.next.cell(rdrowx,rdcolx,wtrowx,wtcolx)

    def finish(self):
        """
        This method is called once processing of all workbooks has
        been completed.

        A filter should call this method on the next filter in the
        chain as an indication that no further calls will be made to
        any methods or that, if they are, any new calls should be
        treated as new batch of workbooks with no information retained
        from the previous batch.
        """
        self.next.finish()

class BaseFilter:
    """
    A concrete filter that implements pass-through behaviour
    for :class:`~xlutils.filter.BaseFilterInterface`.

    This often makes a great base class for your own filters.
    """

    all_methods = (
        'start',
        'workbook',
        'sheet',
        'set_rdsheet',
        'row',
        'cell',
        'finish',
        )

    def sheet(self,rdsheet,wtsheet_name):
        self.rdsheet = rdsheet
        self.next.sheet(rdsheet,wtsheet_name)
       
    def set_rdsheet(self,rdsheet):
        self.rdsheet = rdsheet
        self.next.set_rdsheet(rdsheet)

    def __getattr__(self,name):
        if name not in self.all_methods:
            raise AttributeError(name)
        actual = getattr(self.next,name)
        setattr(self,name,actual)
        return actual

class BaseWriter:
    """
    This is the base writer that copies all data and formatting from
    the specified sources.
    It is designed for sequential use so when, for example, writing
    two workbooks, the calls must be ordered as follows:
    
    - :meth:`workbook` call for first workbook
    - :meth:`sheet` call for first sheet
    - :meth:`row` call for first row
    - :meth:`cell` call for left-most cell of first row
    - :meth:`cell` call for second-left-most cell of first row
    - ...
    - :meth:`row` call for second row
    - ...
    - :meth:`sheet` call for second sheet
    - ...
    - :meth:`workbook` call for second workbook
    - ...
    - :meth:`finish` call

    Usually, only the :meth:`get_stream` method needs to be implemented in subclasses.
    """
    
    wtbook = None
    
    close_after_write = True

    def get_stream(self,filename):
        """
        This method is called once for each file written.
        The filename of the file to be created is passed and something with
        :meth:`~file.write` and :meth:`~file.close`
        methods that behave like a :class:`file` object's must be returned.
        """
        raise NotImplementedError

    def start(self):
        """
        This method should be called before processing of a batch of input.
        This allows the filter to initialise any required data
        structures and dispose of any existing state from previous
        batches. 
        """
        self.wtbook = None
        
    def close(self):
        if self.wtbook is not None:
            stream = self.get_stream(self.wtname)
            self.wtbook.save(stream)
            if self.close_after_write:
                stream.close()
            del self.wtbook
            del self.rdbook
            del self.rdsheet
            del self.wtsheet
            del self.style_list

    def workbook(self,rdbook,wtbook_name):
        """
        This method should be called every time processing of a new
        workbook starts.

        :param rdbook: the :class:`~xlrd.Book` object from which the new workbook
                 will be created.

        :param wtbook_name: the name of the workbook into which content
                      will be written.
        """
        self.close()        
        self.rdbook = rdbook
        self.wtbook = xlwt.Workbook(style_compression=2)
        self.wtbook.dates_1904 = rdbook.datemode
        self.wtname = wtbook_name
        self.style_list = []
        self.wtsheet_names = set()
        # the index of the current wtsheet being written
        self.wtsheet_index = 0
        # have we set a visible sheet already?
        self.sheet_visible = False
        if not rdbook.formatting_info:
            return
        for rdxf in rdbook.xf_list:
            wtxf = xlwt.Style.XFStyle()
            #
            # number format
            #
            wtxf.num_format_str = rdbook.format_map[rdxf.format_key].format_str
            #
            # font
            #
            wtf = wtxf.font
            rdf = rdbook.font_list[rdxf.font_index]
            wtf.height = rdf.height
            wtf.italic = rdf.italic
            wtf.struck_out = rdf.struck_out
            wtf.outline = rdf.outline
            wtf.shadow = rdf.outline
            wtf.colour_index = rdf.colour_index
            wtf.bold = rdf.bold #### This attribute is redundant, should be driven by weight
            wtf._weight = rdf.weight #### Why "private"?
            wtf.escapement = rdf.escapement
            wtf.underline = rdf.underline_type #### 
            # wtf.???? = rdf.underline #### redundant attribute, set on the fly when writing
            wtf.family = rdf.family
            wtf.charset = rdf.character_set
            wtf.name = rdf.name
            # 
            # protection
            #
            wtp = wtxf.protection
            rdp = rdxf.protection
            wtp.cell_locked = rdp.cell_locked
            wtp.formula_hidden = rdp.formula_hidden
            #
            # border(s) (rename ????)
            #
            wtb = wtxf.borders
            rdb = rdxf.border
            wtb.left   = rdb.left_line_style
            wtb.right  = rdb.right_line_style
            wtb.top    = rdb.top_line_style
            wtb.bottom = rdb.bottom_line_style 
            wtb.diag   = rdb.diag_line_style
            wtb.left_colour   = rdb.left_colour_index 
            wtb.right_colour  = rdb.right_colour_index 
            wtb.top_colour    = rdb.top_colour_index
            wtb.bottom_colour = rdb.bottom_colour_index 
            wtb.diag_colour   = rdb.diag_colour_index 
            wtb.need_diag1 = rdb.diag_down
            wtb.need_diag2 = rdb.diag_up
            #
            # background / pattern (rename???)
            #
            wtpat = wtxf.pattern
            rdbg = rdxf.background
            wtpat.pattern = rdbg.fill_pattern
            wtpat.pattern_fore_colour = rdbg.pattern_colour_index
            wtpat.pattern_back_colour = rdbg.background_colour_index
            #
            # alignment
            #
            wta = wtxf.alignment
            rda = rdxf.alignment
            wta.horz = rda.hor_align
            wta.vert = rda.vert_align
            wta.dire = rda.text_direction
            # wta.orie # orientation doesn't occur in BIFF8! Superceded by rotation ("rota").
            wta.rota = rda.rotation
            wta.wrap = rda.text_wrapped
            wta.shri = rda.shrink_to_fit
            wta.inde = rda.indent_level
            # wta.merg = ????
            #
            self.style_list.append(wtxf)
   
    def sheet(self,rdsheet,wtsheet_name):
        """
        This method should be called every time processing of a new
        sheet in the current workbook starts.

        :param rdsheet: the :class:`~xlrd.sheet.Sheet` object from which the new
                  sheet will be created.

        :param wtsheet_name: the name of the sheet into which content
                       will be written.
        """
        
        # these checks should really be done by xlwt!
        if not wtsheet_name:
            raise ValueError('Empty sheet name will result in invalid Excel file!')
        l_wtsheet_name = wtsheet_name.lower()
        if l_wtsheet_name in self.wtsheet_names:
            raise ValueError('A sheet named %r has already been added!'%l_wtsheet_name)
        self.wtsheet_names.add(l_wtsheet_name)
        l_wtsheet_name = len(wtsheet_name)
        if len(wtsheet_name)>31:
            raise ValueError('Sheet name cannot be more than 31 characters long, '
                             'supplied name was %i characters long!'%l_wtsheet_name)
        
        self.rdsheet = rdsheet
        self.wtsheet_name=wtsheet_name
        self.wtsheet = wtsheet = self.wtbook.add_sheet(wtsheet_name,cell_overwrite_ok=True)
        self.wtcols = set() # keep track of which columns have had their attributes set up
        #
        # MERGEDCELLS
        # 
        mc_map = {}
        mc_nfa = set()
        for crange in rdsheet.merged_cells:
            rlo, rhi, clo, chi = crange
            mc_map[(rlo, clo)] = crange
            for rowx in xrange(rlo, rhi):
                for colx in xrange(clo, chi):
                    mc_nfa.add((rowx, colx))
        self.merged_cell_top_left_map = mc_map
        self.merged_cell_already_set = mc_nfa
        if not rdsheet.formatting_info:
            return
        #
        # default column width: STANDARDWIDTH, DEFCOLWIDTH
        #
        if rdsheet.standardwidth is not None:
            # STANDARDWIDTH is expressed in units of 1/256 of a 
            # character-width, but DEFCOLWIDTH is expressed in units of
            # character-width; we lose precision by rounding to
            # the higher whole number of characters.
            #### XXXX TODO: implement STANDARDWIDTH record in xlwt.
            wtsheet.col_default_width = \
                (rdsheet.standardwidth + 255) // 256
        elif rdsheet.defcolwidth is not None:
            wtsheet.col_default_width = rdsheet.defcolwidth
        #
        # WINDOW2
        #
        wtsheet.show_formulas = rdsheet.show_formulas
        wtsheet.show_grid = rdsheet.show_grid_lines
        wtsheet.show_headers = rdsheet.show_sheet_headers
        wtsheet.panes_frozen = rdsheet.panes_are_frozen
        wtsheet.show_zero_values = rdsheet.show_zero_values
        wtsheet.auto_colour_grid = rdsheet.automatic_grid_line_colour
        wtsheet.cols_right_to_left = rdsheet.columns_from_right_to_left
        wtsheet.show_outline = rdsheet.show_outline_symbols
        wtsheet.remove_splits = rdsheet.remove_splits_if_pane_freeze_is_removed
        wtsheet.selected = rdsheet.sheet_selected
        # xlrd doesn't read WINDOW1 records, so we have to make a best
        # guess at which the active sheet should be:
        # (at a guess, only one sheet should be marked as visible)
        if not self.sheet_visible and rdsheet.sheet_visible:
            self.wtbook.active_sheet = self.wtsheet_index
            wtsheet.sheet_visible = 1
        self.wtsheet_index +=1
        
        wtsheet.page_preview = rdsheet.show_in_page_break_preview
        wtsheet.first_visible_row = rdsheet.first_visible_rowx
        wtsheet.first_visible_col = rdsheet.first_visible_colx
        wtsheet.grid_colour = rdsheet.gridline_colour_index
        wtsheet.preview_magn = rdsheet.cooked_page_break_preview_mag_factor
        wtsheet.normal_magn = rdsheet.cooked_normal_view_mag_factor
        #
        # DEFAULTROWHEIGHT
        #
        if rdsheet.default_row_height is not None:
            wtsheet.row_default_height =          rdsheet.default_row_height
        wtsheet.row_default_height_mismatch = rdsheet.default_row_height_mismatch
        wtsheet.row_default_hidden =          rdsheet.default_row_hidden
        wtsheet.row_default_space_above =     rdsheet.default_additional_space_above
        wtsheet.row_default_space_below =     rdsheet.default_additional_space_below
        #
        # BOUNDSHEET
        #
        wtsheet.visibility = rdsheet.visibility
       
        #
        # PANE
        #
        if rdsheet.has_pane_record:
            wtsheet.split_position_units_are_twips = True
            wtsheet.active_pane =              rdsheet.split_active_pane
            wtsheet.horz_split_pos =           rdsheet.horz_split_pos
            wtsheet.horz_split_first_visible = rdsheet.horz_split_first_visible
            wtsheet.vert_split_pos =           rdsheet.vert_split_pos
            wtsheet.vert_split_first_visible = rdsheet.vert_split_first_visible
            
    def set_rdsheet(self,rdsheet):
        """
        This should only ever called by a filter that
        wishes to change the source of cells mid-way through writing a
        sheet.

        :param rdsheet: the :class:`~xlrd.sheet.Sheet` object from which cells from
                  this point forward will be read.

        """
        self.rdsheet = rdsheet
        
    def row(self,rdrowx,wtrowx):
        """
        This should be called every time processing of a new
        row in the current sheet starts.

        :param rdrowx: the index of the row in the current sheet from which
                 information for the row to be written will be
                 copied.

        :param wtrowx: the index of the row in sheet to be written to which
                 information will be written for the row being read.
        """
        wtrow = self.wtsheet.row(wtrowx)
        # empty rows may not have a rowinfo record
        rdrow = self.rdsheet.rowinfo_map.get(rdrowx)
        if rdrow:
            wtrow.height = rdrow.height
            wtrow.has_default_height = rdrow.has_default_height
            wtrow.height_mismatch = rdrow.height_mismatch
            wtrow.level = rdrow.outline_level
            wtrow.collapse = rdrow.outline_group_starts_ends # No kiddin'
            wtrow.hidden = rdrow.hidden
            wtrow.space_above = rdrow.additional_space_above
            wtrow.space_below = rdrow.additional_space_below
            if rdrow.has_default_xf_index:
                wtrow.set_style(self.style_list[rdrow.xf_index])

    def cell(self,rdrowx,rdcolx,wtrowx,wtcolx):
        """
        This should be called for every cell in the sheet being processed.

        :param rdrowx: the index of the row to be read from in the current sheet. 
        :param rdcolx: the index of the column to be read from in the current sheet. 
        :param wtrowx: the index of the row to be written to in the current output sheet. 
        :param wtcolx: the index of the column to be written to in the current output sheet. 
        """
        cell = self.rdsheet.cell(rdrowx,rdcolx)
        # setup column attributes if not already set
        if wtcolx not in self.wtcols and rdcolx in self.rdsheet.colinfo_map:
            rdcol = self.rdsheet.colinfo_map[rdcolx]
            wtcol = self.wtsheet.col(wtcolx)
            wtcol.width = rdcol.width
            wtcol.set_style(self.style_list[rdcol.xf_index])
            wtcol.hidden = rdcol.hidden
            wtcol.level = rdcol.outline_level
            wtcol.collapsed = rdcol.collapsed
            self.wtcols.add(wtcolx)
        # copy cell
        cty = cell.ctype
        if cty == xlrd.XL_CELL_EMPTY:
            return
        if cell.xf_index is not None:
            style = self.style_list[cell.xf_index]
        else:
            style = default_style
        rdcoords2d = (rdrowx, rdcolx)
        if rdcoords2d in self.merged_cell_top_left_map:
            # The cell is the governing cell of a group of 
            # merged cells.
            rlo, rhi, clo, chi = self.merged_cell_top_left_map[rdcoords2d]
            assert (rlo, clo) == rdcoords2d
            self.wtsheet.write_merge(
                wtrowx, wtrowx + rhi - rlo - 1,
                wtcolx, wtcolx + chi - clo - 1, 
                cell.value, style)
            return
        if rdcoords2d in self.merged_cell_already_set:
            # The cell is in a group of merged cells.
            # It has been handled by the write_merge() call above.
            # We avoid writing a record again because:
            # (1) It's a waste of CPU time and disk space.
            # (2) xlwt does not (as at 2007-01-12) ensure that only
            # the last record is written to the file.
            # (3) If you write a data record for a cell
            # followed by a blank record for the same cell,
            # Excel will display a blank but OOo Calc and
            # Gnumeric will display the data :-(
            return
        wtrow = self.wtsheet.row(wtrowx)
        if cty == xlrd.XL_CELL_TEXT:
            wtrow.set_cell_text(wtcolx, cell.value, style)
        elif cty == xlrd.XL_CELL_NUMBER or cty == xlrd.XL_CELL_DATE:
            wtrow.set_cell_number(wtcolx, cell.value, style)
        elif cty == xlrd.XL_CELL_BLANK:
            wtrow.set_cell_blank(wtcolx, style)
        elif cty == xlrd.XL_CELL_BOOLEAN:
            wtrow.set_cell_boolean(wtcolx, cell.value, style)
        elif cty == xlrd.XL_CELL_ERROR:
            wtrow.set_cell_error(wtcolx, cell.value, style)
        else:
            raise Exception(
                "Unknown xlrd cell type %r with value %r at (sheet=%r,rowx=%r,colx=%r)" \
                % (cty, cell.value, self.rdsheet.name, rdrowx, rdcolx)
                )

    def finish(self):
        """
        This method should be called once processing of all workbooks has
        been completed.
        """
        self.close()

    
class GlobReader(BaseReader):
    "A reader that emits events for all files that match the glob in the spec."

    def __init__(self,spec):
        self.spec = spec
        
    def get_filepaths(self):
        return sorted(glob(self.spec))

class XLRDReader(BaseReader):
    "A reader that uses an in-memory :class:`xlrd.Book` object as its source of events."

    def __init__(self,wb,filename):
        self.wb = wb
        self.filename = filename
        
    def get_workbooks(self):
        "Yield the workbook passed during instantiation."
        yield (self.wb,self.filename)

class DirectoryWriter(BaseWriter):
    "A writer that stores files in a filesystem directory"

    def __init__(self,path):
        self.dir_path = path
        
    def get_stream(self,filename):
        """
        Returns a stream for the file in the configured directory
        with the specified name.
        """
        return file(os.path.join(self.dir_path,filename),'wb')

class StreamWriter(BaseWriter):
    "A writer for writing exactly one workbook to the supplied stream"

    fired = False
    close_after_write = False
    
    def __init__(self,stream):
        self.stream = stream
        
    def get_stream(self,filename):
        "Returns the stream passed during instantiation."
        if self.fired:
            raise Exception('Attempt to write more than one workbook')
        self.fired = True
        return self.stream

class XLWTWriter(BaseWriter):
    "A writer that writes to a sequence of in-memory :class:`xlwt.Workbook` objects."

    def __init__(self):
        self.output = []

    def close(self):
        if self.wtbook is not None:
            self.output.append((self.wtname,self.wtbook))
            del self.wtbook

class MethodFilter(BaseFilter):
    """
    This is a base class that implements functionality for filters
    that want to do a common task such as logging, printing or memory
    usage recording on certain calls configured at filter instantiation
    time.

    :ref:`echo` is an example of this.
    """
    
    def method(self,name,*args):
        """
        This is the method that needs to be implemented.
        It is called with the name of the method that was called on
        the MethodFilter and the arguments that were passed to that
        method. 
        """
        raise NotImplementedError
    
    def __init__(self,methods=True):
        if methods==True or methods=='True' or (len(methods)==1 and methods[0]=='True'):
            methods = self.all_methods
        for name in methods:
            if name not in self.all_methods:
                raise ValueError('%r is not a valid method name'%(name,))
            setattr(self,name,partial(self.caller,name))

    def caller(self,name,*args):
        self.method(name,*args)
        getattr(self.next,name)(*args)

class Echo(MethodFilter):
    """
    This filter will print calls to the methods configured when the
    filter is created along with the arguments passed.

    For more details, see the :ref:`documentation <echo>`.
    """

    def __init__(self,name=None,methods=True):
        MethodFilter.__init__(self,methods)
        self.name = name

    def method(self,name,*args):
        if self.name:
            print repr(self.name),
        print "%s:%r"%(name,args)
        
try:
    from guppy import hpy
    guppy = True
except ImportError:
    guppy = False
    
class MemoryLogger(MethodFilter):
    """
    This filter will dump stats to the path it was configured with using
    the heapy package if it is available.
    """

    def __init__(self,path,methods=True):
        MethodFilter.__init__(self,methods)
        self.path = path
        
    def method(self,name,*args):
        if guppy:
            # We instantiate the heapy environment here
            # so that the memory it consumes doesn't hang
            # around for the whole process
            hpy().heap().stat.dump(self.path)
        else:
            logger.error('guppy is not availabe, cannot log memory usage!')
            
            
class ErrorFilter(BaseReader,BaseWriter):
    """
    A filter that gates downstream writers or filters on whether
    or not any errors have occurred.

    See :ref:`error-filters` for details.
    """
    temp_path = None
    
    def __init__(self,level=logging.ERROR,message='No output as errors have occurred.'):
        from errorhandler import ErrorHandler
        self.handler = ErrorHandler(level)
        self.message = message

    def start(self,create=True):
        self.prefix = 0
        self.handler.reset()
        if self.temp_path is not None:
            rmtree(self.temp_path)
        if create:
            self.temp_path = mkdtemp()
        else:
            self.temp_path = None
        BaseWriter.start(self)
        
    def get_stream(self,filename):
        self.prefix+=1
        return open(os.path.join(self.temp_path,str(self.prefix)+'-'+filename),'wb')

    def get_workbooks(self):
        if self.temp_path is None:
            return
        filenames = []
        for name in os.listdir(self.temp_path):
            d = name.split('-',1)
            d.append(name)
            filenames.append(d)
        filenames.sort()
        for i,filename,pathname in filenames:
            yield (
                # We currently don't open with on_demand=True here
                # as error filters should be lastish in the chain
                # so there's not much win.
                # However, if we did, getting rid of the temp dirs
                # becomes a problem as, on Windows, they can't be
                # deleted until the xlrd.Book object is done with
                # and we don't know when that might be :-(
                xlrd.open_workbook(
                    os.path.join(self.temp_path,pathname),
                    formatting_info=1,
                    on_demand=False,
                    ragged_rows=True
                    ),
                filename
                )

    def sheet(self,rdsheet,wtsheet_name):
        self.rdsheet = rdsheet
        BaseWriter.sheet(self,rdsheet,wtsheet_name)

    def cell(self,rdrowx,rdcolx,wtrowx,wtcolx):
        cell = self.rdsheet.cell(rdrowx,rdcolx)
        if cell.ctype == xlrd.XL_CELL_EMPTY:
            return
        if cell.ctype == xlrd.XL_CELL_ERROR:
            logger.error("Cell %s of sheet %r contains a bad value: %s" % (
                        xlrd.cellname(rdrowx, rdcolx),
                        quoted_sheet_name(self.rdsheet.name),
                        cell_display(cell,self.rdbook.datemode),
                        ))
            return
        BaseWriter.cell(self,rdrowx,rdcolx,wtrowx,wtcolx)

    def finish(self):
        """
        The method that triggers downstream filters and writers
        if no errors have occurred.
        """
        BaseWriter.finish(self)
        if self.handler.fired:
            logger.error(self.message)
        else:
            self(self.next)
        self.start(create=False)
        for attr in ('rdbook','rdsheet'):
            if hasattr(self,attr):
                delattr(self,attr)

class Range(object):
    __slots__ = ('rsn','rr','rc','wr','wc','r','c')
    def __init__(self,rsn,rr,rc,wr,wc):
        self.rsn = rsn
        self.rr = rr
        self.rc = rc
        self.wr = wr
        self.wc = wc
        self.r = self.c = 1
    def __repr__(self):
        return '<range:%r:(%i,%i)->(%i,%i)-r:%i,c:%i>' % (
            self.rsn,self.rr,self.rc,self.wr,self.wc,self.r,self.c
            )

class ColumnTrimmer(BaseFilter):
    """
    This filter will strip columns containing no useful data from the
    end of sheets.

    See the :ref:`column_trimmer` documentation for an example.
    """

    def __init__(self,is_junk=None):
        self.is_junk = is_junk
        
    def start(self,chain=True):
        self.rdsheet = None
        self.pending_rdsheet = None
        self.ranges = []
        self.max_nonjunk = 0
        self.max = 0
        if chain:
            self.next.start()
        
    def flush(self):
        if self.rdsheet is not None:
            rsn = None
            for ra in self.ranges:
                if rsn is None:
                    rsn = ra.rsn
                elif ra.rsn!=rsn:
                    self.rdsheet = self.rdbook.sheet_by_name(ra.rsn)
                    self.next.set_rdsheet(self.rdsheet)
                    rsn = ra.rsn
                for r in range(ra.r):
                    for c in range(ra.c):
                        wtcolx=ra.wc+c
                        if wtcolx<=self.max_nonjunk:
                            self.next.cell(ra.rr+r,ra.rc+c,ra.wr+r,ra.wc+c)
            if self.max!=self.max_nonjunk:
                logger.debug("Number of columns trimmed from %d to %d for sheet %r",
                             self.max+1,
                             self.max_nonjunk+1,
                             quoted_sheet_name(self.wtsheet_name))
        self.start(chain=False)

    def workbook(self,rdbook,wtbook_name):
        self.rdbook = rdbook
        self.flush()
        self.next.workbook(rdbook,wtbook_name)
        
    def sheet(self,rdsheet,wtsheet_name):
        self.flush()
        self.rdsheet = rdsheet
        self.wtsheet_name = wtsheet_name
        self.next.sheet(self.rdsheet,wtsheet_name)
        
    def set_rdsheet(self,rdsheet):
        self.pending_rdsheet = rdsheet
        self.rdsheet = rdsheet
    
    def add_range(self,rdrowx,rdcolx,wtrowx,wtcolx):
        if len(self.ranges)>1:
            to_collapse = self.ranges[-1]
            possible = self.ranges[-2]
            if to_collapse.rc==possible.rc and \
               to_collapse.c==possible.c and \
               to_collapse.rr==possible.rr+possible.r:
                possible.r+=to_collapse.r
                self.ranges.pop()
        self.ranges.append(Range(
                self.rdsheet.name,rdrowx,rdcolx,wtrowx,wtcolx
                ))
        
    def cell(self,rdrowx,rdcolx,wtrowx,wtcolx):
        if wtcolx>self.max:
            self.max = wtcolx
        cell = self.rdsheet.cell(rdrowx,rdcolx)
        if wtcolx>self.max_nonjunk and not cells_all_junk((cell,),self.is_junk):
            self.max_nonjunk = wtcolx
        if not self.ranges:
            self.add_range(rdrowx,rdcolx,wtrowx,wtcolx)
        elif self.pending_rdsheet is not None: 
            self.add_range(rdrowx,rdcolx,wtrowx,wtcolx)
            self.pending_rdsheet = None
        else:
            r = self.ranges[-1]
            if rdrowx==r.rr and wtrowx==r.wr and rdcolx==r.rc+r.c and wtcolx==r.wc+r.c:
                r.c+=1
            else:
                self.add_range(rdrowx,rdcolx,wtrowx,wtcolx)
                                                          
    def finish(self):
        self.flush()
        del self.rdbook
        self.next.finish()
        
def process(reader, *chain):
    """
    The driver function for the :mod:`xlutils.filter` module.

    It takes a chain of one :ref:`reader <reader>`, followed by zero or more
    :ref:`filters <filter>` and ending with one :ref:`writer <writer>`.

    All the components are chained together by the :func:`process` function
    setting their ``next`` attributes appropriately. The
    :ref:`reader <reader>` is then called with the first
    :ref:`filter <filter>` in the chain.
    """
    for i in range(len(chain)-1):
        chain[i].next = chain[i+1]
    reader(chain[0])

########NEW FILE########
__FILENAME__ = margins
# -*- coding: ascii -*-

import sys, glob, string

try:
    from xlrd import open_workbook, XL_CELL_EMPTY, XL_CELL_BLANK, XL_CELL_TEXT, XL_CELL_NUMBER, cellname
    null_cell_types = (XL_CELL_EMPTY, XL_CELL_BLANK)
except ImportError:
    # older version
    from xlrd import open_workbook, XL_CELL_EMPTY, XL_CELL_TEXT, XL_CELL_NUMBER
    null_cell_types = (XL_CELL_EMPTY, )

def cells_all_junk(cells, is_rubbish=None):
    """\
    Return True if all cells in the sequence are junk.
    What qualifies as junk:
    -- empty cell
    -- blank cell
    -- zero-length text
    -- text is all whitespace
    -- number cell and is 0.0
    -- text cell and is_rubbish(cell.value) returns True.
    """
    for cell in cells:
        if cell.ctype in null_cell_types:
            continue
        if cell.ctype == XL_CELL_TEXT:
            if not cell.value:
                continue
            if cell.value.isspace():
                continue
        if cell.ctype == XL_CELL_NUMBER:
            if not cell.value:
                continue
        if is_rubbish is not None and is_rubbish(cell):
            continue
        return False
    return True

def ispunc(c, s=set(unicode(string.punctuation))):
    """Return True if c is a single punctuation character"""
    return c in s

def number_of_good_rows(sheet, checker=None, nrows=None, ncols=None):
    """Return 1 + the index of the last row with meaningful data in it."""
    if nrows is None: nrows = sheet.nrows
    if ncols is None: ncols = sheet.ncols
    for rowx in xrange(nrows - 1, -1, -1):
        if not cells_all_junk(sheet.row_slice(rowx, 0, ncols), checker):
            return rowx + 1
    return 0

def number_of_good_cols(sheet, checker=None, nrows=None, ncols=None):
    """Return 1 + the index of the last column with meaningful data in it."""
    if nrows is None: nrows = sheet.nrows
    if ncols is None: ncols = sheet.ncols
    for colx in xrange(ncols - 1, -1, -1):
        if not cells_all_junk(sheet.col_slice(colx, 0, nrows), checker):
            return colx+1
    return 0

def safe_encode(ustr, encoding):
    try:
        return ustr.encode(encoding)
    except (UnicodeEncodeError, UnicodeError):
        return repr(ustr)

def check_file(fname, verbose, do_punc=False, fmt_info=0, encoding='ascii', onesheet=''):
    print
    print fname
    if do_punc:
        checker = ispunc
    else:
        checker = None
    try:
        book = open_workbook(fname, formatting_info=fmt_info, on_demand=True)
    except TypeError:
        try:
            book = open_workbook(fname, formatting_info=fmt_info)
        except TypeError:
            # this is becoming ridiculous
            book = open_workbook(fname)
    totold = totnew = totnotnull = 0
    if onesheet is None or onesheet == "":
        shxrange = range(book.nsheets)
    else:
        try:
            shxrange = [int(onesheet)]
        except ValueError:
            shxrange = [book.sheet_names().index(onesheet)]
    for shx in shxrange:
        sheet = book.sheet_by_index(shx)
        ngoodrows = number_of_good_rows(sheet, checker)
        ngoodcols = number_of_good_cols(sheet, checker, nrows=ngoodrows)
        oldncells = sheet.nrows * sheet.ncols
        newncells = ngoodrows * ngoodcols
        totold += oldncells
        totnew += newncells
        nnotnull = 0
        sheet_density_pct_s = ''
        if verbose >= 2:
            colxrange = range(ngoodcols)
            for rowx in xrange(ngoodrows):
                rowtypes = sheet.row_types(rowx)
                for colx in colxrange:
                    if rowtypes[colx] not in null_cell_types:
                        nnotnull += 1
            totnotnull += nnotnull
            sheet_density_pct = (nnotnull * 100.0) / max(1, newncells)
            sheet_density_pct_s = "; den = %5.1f%%" % sheet_density_pct
        if verbose >= 3:
            # which rows have non_empty cells in the right-most column?
            lastcolx = sheet.ncols - 1
            for rowx in xrange(sheet.nrows):
                cell = sheet.cell(rowx, lastcolx)
                if cell.ctype != XL_CELL_EMPTY:
                    print "%s (%d, %d): type %d, value %r" % (
                        cellname(rowx, lastcolx), rowx, lastcolx, cell.ctype, cell.value)
        if (verbose
            or ngoodrows != sheet.nrows
            or ngoodcols != sheet.ncols
            or (verbose >= 2 and ngoodcells and sheet_density_pct < 90.0)
            ):
            if oldncells:
                pctwaste = (1.0 - float(newncells) / oldncells) * 100.0
            else:
                pctwaste = 0.0
            shname_enc = safe_encode(sheet.name, encoding)
            print "sheet #%2d: RxC %5d x %3d => %5d x %3d; %4.1f%% waste%s (%s)" \
                % (shx, sheet.nrows, sheet.ncols,
                    ngoodrows, ngoodcols, pctwaste, sheet_density_pct_s, shname_enc)
        if hasattr(book, 'unload_sheet'):
            book.unload_sheet(shx)
    if totold:
        pctwaste = (1.0 - float(totnew) / totold) * 100.0
    else:
        pctwaste = 0.0
    print "%d cells => %d cells; %4.1f%% waste" % (totold, totnew, pctwaste)
                
def main():
    import optparse
    usage = "%prog [options] input-file-patterns"
    oparser = optparse.OptionParser(usage)
    oparser.add_option(
        "-v", "--verbosity",
        type="int", default=0,
        help="level of information and diagnostics provided")
    oparser.add_option(
        "-p", "--punc",
        action="store_true", default=False,
        help="treat text cells containing only 1 punctuation char as rubbish")
    oparser.add_option(
        "-e", "--encoding",
        default='',
        help="encoding for text output")
    oparser.add_option(
        "-f", "--formatting",
        action="store_true", default=False,
        help="parse formatting information in the input files")
    oparser.add_option(
        "-s", "--onesheet",
        default="",
        help="restrict output to this sheet (name or index)")
    options, args = oparser.parse_args(sys.argv[1:])
    if len(args) < 1:
        oparser.error("Expected at least 1 arg, found %d" % len(args))
    encoding = options.encoding
    if not encoding:
        encoding = sys.stdout.encoding
    if not encoding:
        encoding = sys.getdefaultencoding()
    for pattern in args:
        for fname in glob.glob(pattern):
            try:
                check_file(fname,
                    options.verbosity, options.punc,
                    options.formatting, encoding, options.onesheet)
            except:
                e1, e2 = sys.exc_info()[:2]
                print "*** File %s => %s:%s" % (fname, e1.__name__, e2)
    
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = save
# Copyright (c) 2008-2012 Simplistix Ltd
#
# This Software is released under the MIT License:
# http://www.opensource.org/licenses/mit-license.html
# See license.txt for more details.

import os
from xlutils.filter import process,XLRDReader,StreamWriter

def save(wb, filename_or_stream):
    "Save the supplied :class:`xlrd.Book` to the supplied stream or filename."
    if isinstance(filename_or_stream,basestring):
        filename = os.path.split(filename_or_stream)[1]
        stream = open(filename_or_stream,'wb')
        close = True
    else:
        filename = 'unknown.xls'
        stream = filename_or_stream
        close = False
    process(
        XLRDReader(wb,filename),
        StreamWriter(stream)
        )
    if close:
        stream.close()

########NEW FILE########
__FILENAME__ = styles
# Copyright (c) 2008-2012 Simplistix Ltd
#
# This Software is released under the MIT License:
# http://www.opensource.org/licenses/mit-license.html
# See license.txt for more details.

class NamedStyle:
    """
    An object with ``name`` and ``xf`` attributes representing
    a particular style in a workbook.
    """
    def __init__(self,name,xf):
        self.name = name
        self.xf = xf
        
class Styles:
    """
    A mapping-like object that will return a :class:`NamedStyle`
    instance for the cell passed to the :meth:`__getitem__`
    method.
    """
    def __init__(self, book):
        xfi_to_name = {}
        for name, info in book.style_name_map.items():
            built_in, xfi = info
            # allow multiple 
            assert xfi not in xfi_to_name or not xfi_to_name[xfi]
            xfi_to_name[xfi] = name
        self.cell_styles = {}
        for xfi in xrange(len(book.xf_list)):
            xf = book.xf_list[xfi]
            if xf.is_style:
                continue
            stylexfi = xf.parent_style_index
            assert stylexfi != 4095 # i.e. 0xFFF
            self.cell_styles[xfi] = NamedStyle(
                xfi_to_name[stylexfi],
                book.xf_list[stylexfi]
                )
        
    def __getitem__(self,cell):
        return self.cell_styles[cell.xf_index]

########NEW FILE########
__FILENAME__ = fixtures
# Copyright (c) 2008 Simplistix Ltd
#
# This Software is released under the MIT License:
# http://www.opensource.org/licenses/mit-license.html
# See license.txt for more details.

import sys
import os.path

from xlrd import XL_CELL_TEXT,Book
from xlrd.biffh import FUN 
from xlrd.formatting import XF, Format, Font, XFAlignment, XFBorder, XFBackground, XFProtection

from xlrd.sheet import Sheet

test_files = os.path.dirname(__file__)

test_xls_path = os.path.join(test_files,'test.xls')

class DummyBook(Book):

    biff_version = 80
    logfile = sys.stdout
    verbosity = 0
    datemode = 0
    on_demand = False

    def __init__(self,
                 formatting_info=0,
                 ragged_rows=False,
                 ):
        Book.__init__(self)
        self.ragged_rows = ragged_rows
        self.formatting_info=formatting_info
        self.initialise_format_info()
        if formatting_info:
            f = Font()
            self.font_list.append(f)
            self.format_map[0]= Format(0,FUN,u'General')
            xf = XF()
            xf.alignment = XFAlignment()
            xf.border = XFBorder()
            xf.background = XFBackground()
            xf.protection = XFProtection()
            self.xf_list.append(xf)
        
    def add(self,sheet):
        self._sheet_names.append(sheet.name)
        self._sheet_list.append(sheet)
        self.nsheets = len(self._sheet_list)

def make_book(rows=[]):
    book = DummyBook()
    sheet = make_sheet(rows,book=book)
    return book

def make_sheet(rows=(),book=None,name='test sheet',number=0):
    if book is None:
        book = DummyBook()
    book._sheet_visibility.append(0)
    sheet = Sheet(book,0,name,number)
    
    book.add(sheet)
    for rowx in range(len(rows)):
        row = rows[rowx]
        for colx in range(len(row)):
            value = row[colx]
            if isinstance(value,tuple):
                cell_type,value = value
            else:
                cell_type=XL_CELL_TEXT
            sheet.put_cell(rowx,colx,cell_type,value,0)
    sheet.tidy_dimensions()
    return sheet

########NEW FILE########
__FILENAME__ = test_copy
# Copyright (c) 2009 Simplistix Ltd
#
# This Software is released under the MIT License:
# http://www.opensource.org/licenses/mit-license.html
# See license.txt for more details.

import os
from mock import Mock
from testfixtures import replace,compare,Comparison as C
from unittest import TestSuite,TestCase,makeSuite
from xlutils.copy import copy
from xlutils.filter import XLRDReader

class TestCopy(TestCase):

    @replace('xlutils.copy.XLWTWriter',Mock())
    @replace('xlutils.copy.process',Mock())
    def test_copy_xlrd(self,c,xlwtw):
        inwb = object()
        
        outwb = Mock()
        xlwtwi = Mock()
        xlwtwi.output=[('junk',outwb)]
        xlwtw.return_value=xlwtwi
        
        self.failUnless(copy(inwb) is outwb)
        
        self.assertEqual(len(c.call_args_list),1)
        args = c.call_args_list[0][0]
        self.assertEqual(len(args),2)
        
        r = args[0]
        self.failUnless(isinstance(r,XLRDReader))
        self.failUnless(r.wb is inwb)
        self.assertEqual(r.filename,'unknown.xls')

        w = args[1]
        self.failUnless(w is xlwtwi)

def test_suite():
    return TestSuite((
        makeSuite(TestCopy),
        ))

########NEW FILE########
__FILENAME__ = test_docs
# Copyright (c) 2008-2012 Simplistix Ltd
#
# This Software is released under the MIT License:
# http://www.opensource.org/licenses/mit-license.html
# See license.txt for more details.

from doctest import REPORT_NDIFF, ELLIPSIS
from fixtures import test_files
from glob import glob
from manuel import doctest
from manuel.testing import TestSuite
from testfixtures import LogCapture,TempDirectory
from os.path import dirname, join, pardir

import os

workspace = os.environ.get('WORKSPACE', join(dirname(__file__), pardir, pardir))
tests = glob(join(workspace, 'docs', '*.txt'))

options = REPORT_NDIFF|ELLIPSIS

def setUp(test):
    test.globs['test_files']=test_files
    test.globs['temp_dir']=TempDirectory().path
    test.globs['TempDirectory']=TempDirectory

def tearDown(test):
    TempDirectory.cleanup_all()
    LogCapture.uninstall_all()

def test_suite():
    m =  doctest.Manuel(optionflags=REPORT_NDIFF|ELLIPSIS)
    return TestSuite(m, *tests,
                     setUp=setUp,
                     tearDown=tearDown)

########NEW FILE########
__FILENAME__ = test_filter
from __future__ import with_statement

# Copyright (c) 2008-2012 Simplistix Ltd
#
# This Software is released under the MIT License:
# http://www.opensource.org/licenses/mit-license.html
# See license.txt for more details.

from mock import Mock
from StringIO import StringIO
from tempfile import TemporaryFile
from testfixtures import compare, Comparison as C, replace, log_capture, ShouldRaise, tempdir
from unittest import TestSuite,TestCase,makeSuite
from xlrd import open_workbook, XL_CELL_NUMBER, XL_CELL_ERROR, XL_CELL_BOOLEAN
from xlrd.formatting import XF
from xlutils.filter import BaseReader,GlobReader,MethodFilter,BaseWriter,process,XLRDReader,XLWTWriter, BaseFilter
from xlutils.tests.fixtures import test_files,test_xls_path,make_book,make_sheet,DummyBook

import os

class TestReader(BaseReader):

    formatting_info = 0
    
    def __init__(self,*sheets,**books):
        self.setup(*sheets,**books)
        
    def setup(self,*sheets,**books):
        self.books = []
        if sheets:
            self.makeBook('test',sheets)
        for name,value in sorted(books.items()):
            self.makeBook(name,value)
        
    def makeBook(self,book_name,sheets):
        book = DummyBook(self.formatting_info)
        index = 0
        for name,rows in sheets:
            make_sheet(rows,book,name,index)
            index+=1
        self.books.append((book,book_name+'.xls'))
        
    def get_workbooks(self):
        return self.books

class TestBaseReader(TestCase):

    def test_no_implementation(self):
        r = BaseReader()
        f = Mock()
        with ShouldRaise(NotImplementedError()):
            r(f)
        self.assertEqual(f.method_calls,[('start',(),{})])
        
    def test_ragged_rows(self):
        class TestReader(BaseReader):
            def get_filepaths(self):
                return (os.path.join(test_files,'ragged.xls'),)
        t = TestReader()
        class TestFilter(BaseFilter):
            def cell(self,rdrowx,rdcolx,wtrowx,wtcolx):
                self.rdsheet.cell(rdrowx,rdcolx)
        f = TestFilter()
        f.next = Mock()
        t(f)
    
    def test_custom_filepaths(self):
        # also tests the __call__ method
        class TestReader(BaseReader):
            def get_filepaths(self):
                return (test_xls_path,)
        t = TestReader()
        f = Mock()
        t(f)
        compare(f.method_calls,[
            ('start',(),{}),
            ('workbook',(C('xlrd.Book',
                           formatting_info=1,
                           on_demand=True,
                           ragged_rows=True,
                           strict=False),'test.xls'),{}),
            ('sheet',(C('xlrd.sheet.Sheet'),u'Sheet1'),{}),
            ('row',(0,0),{}),
            ('cell',(0,0,0,0),{}),
            ('cell',(0,1,0,1),{}),
            ('row',(1,1),{}),
            ('cell',(1,0,1,0),{}),
            ('cell',(1,1,1,1),{}),
            ('sheet',(C('xlrd.sheet.Sheet'),u'Sheet2'),{}),
            ('row',(0,0),{}),
            ('cell',(0,0,0,0),{}),
            ('cell',(0,1,0,1),{}),
            ('row',(1,1),{}),
            ('cell',(1,0,1,0),{}),
            ('cell',(1,1,1,1),{}),
            ('finish',(),{}),
            ])

    def test_custom_getworkbooks(self):
        book = make_book((('1','2','3'),))
        class TestReader(BaseReader):
            def get_workbooks(self):
                yield book,'test.xls'
        t = TestReader()
        f = Mock()
        t(f)
        compare(f.method_calls,[
            ('start',(),{}),
            ('workbook',(C('xlutils.tests.fixtures.DummyBook'),'test.xls'),{}),
            ('sheet',(C('xlrd.sheet.Sheet'),'test sheet'),{}),
            ('row',(0,0),{}),
            ('cell',(0,0,0,0),{}),
            ('cell',(0,1,0,1),{}),
            ('cell',(0,2,0,2),{}),
            ('finish',(),{}),
            ])
        # check we're getting the right things
        self.failUnless(f.method_calls[1][1][0] is book)
        self.failUnless(f.method_calls[2][1][0] is book.sheet_by_index(0))
    
    class MockReader(BaseReader):
        def __init__(self,book):
            book.nsheets=2
            book.sheet_by_index.side_effect = self.sheet_by_index
            book.sheet0.nrows=1
            book.sheet0.ncols=1
            book.sheet0.row_len.return_value = 1
            book.sheet0.name='sheet0'
            book.sheet1.nrows=1
            book.sheet1.ncols=1
            book.sheet1.row_len.return_value = 1
            book.sheet1.name='sheet1'
            self.b = book
            
        def get_workbooks(self):
            return [(self.b,str(id(self.b)))]
        
        def sheet_by_index(self,i):
            return getattr(self.b,'sheet'+str(i))
    
    def test_on_demand_true(self):
        m = Mock()
        book = m.book
        book.on_demand=True
        r = self.MockReader(book)
        f = m.filter
        r(f)
        compare(m.method_calls,[
            ('filter.start', (), {}),
            ('filter.workbook', (book, str(id(book))), {}),
            ('book.sheet_by_index', (0,), {}),
            ('filter.sheet',(book.sheet0, 'sheet0'),{}),
            ('filter.row', (0, 0), {}),
            ('book.sheet0.row_len', (0,), {}),
            ('filter.cell', (0, 0, 0, 0), {}),
            ('book.unload_sheet', (0,), {}),
            ('book.sheet_by_index', (1,), {}),
            ('filter.sheet',(book.sheet1, 'sheet1'),{}),
            ('filter.row', (0, 0), {}),
            ('book.sheet1.row_len', (0,), {}),
            ('filter.cell', (0, 0, 0, 0), {}),
            ('book.unload_sheet', (1,), {}),
            ('filter.finish', (), {})
            ])
        
    def test_on_demand_false(self):
        m = Mock()
        book = m.book
        book.on_demand=False
        r = self.MockReader(book)
        f = m.filter
        r(f)
        compare(m.method_calls,[
            ('filter.start', (), {}),
            ('filter.workbook', (book, str(id(book))), {}),
            ('book.sheet_by_index', (0,), {}),
            ('filter.sheet',(book.sheet0, 'sheet0'),{}),
            ('filter.row', (0, 0), {}),
            ('book.sheet0.row_len', (0,), {}),
            ('filter.cell', (0, 0, 0, 0), {}),
            ('book.sheet_by_index', (1,), {}),
            ('filter.sheet',(book.sheet1, 'sheet1'),{}),
            ('filter.row', (0, 0), {}),
            ('book.sheet1.row_len', (0,), {}),
            ('filter.cell', (0, 0, 0, 0), {}),
            ('filter.finish', (), {})
            ])

class TestBaseFilter(TestCase):

    def setUp(self):
        from xlutils.filter import BaseFilter
        self.filter = BaseFilter()
        self.filter.next = self.tf = Mock()

    def test_start(self):
        self.filter.start()
        self.assertEqual(self.tf.method_calls,[
            ('start',(),{})
            ])
                         
    def test_workbook(self):
        self.filter.workbook('rdbook','wtbook_name')
        self.assertEqual(self.tf.method_calls,[
            ('workbook',('rdbook','wtbook_name'),{})
            ])
                         
    def test_sheet(self):
        self.filter.sheet('rdsheet','wtsheet_name')
        self.assertEqual(self.tf.method_calls,[
            ('sheet',('rdsheet','wtsheet_name'),{})
            ])
                         
    def test_set_rdsheet(self):
        self.filter.set_rdsheet('rdsheet2')
        self.assertEqual(self.tf.method_calls,[
            ('set_rdsheet',('rdsheet2',),{})
            ])
                         
    def test_row(self):
        self.filter.row(0,1)
        self.assertEqual(self.tf.method_calls,[
            ('row',(0,1),{})
            ])
                         
    def test_cell(self):
        self.filter.cell(0,1,2,3)
        self.assertEqual(self.tf.method_calls,[
            ('cell',(0,1,2,3),{})
            ])
                         
    def test_finish(self):
        self.filter.finish()
        self.assertEqual(self.tf.method_calls,[
            ('finish',(),{})
            ])

class OurMethodFilter(MethodFilter):
    def __init__(self,collector,call_on=True):
        MethodFilter.__init__(self,call_on)
        self.collector = collector        
    def method(self,name,*args):
        self.collector.append((name,args))
        
class TestMethodFilter(TestCase):

    def setUp(self):
        self.called = []

    def test_cmp(self):
        cmp(MethodFilter(),OurMethodFilter([]))
        
    def do_calls_and_test(self,filter):
        filter.next = tf = Mock()
        filter.start()
        filter.workbook('rdbook','wtbook_name')
        filter.sheet('rdsheet','wtsheet_name')
        filter.row(0,1)
        filter.cell(0,1,2,3)
        filter.set_rdsheet('rdsheet2')
        filter.finish()
        self.assertEqual(tf.method_calls,[
            ('start',(),{}),
            ('workbook',('rdbook','wtbook_name'),{}),
            ('sheet',('rdsheet','wtsheet_name'),{}),
            ('row',(0,1),{}),
            ('cell',(0,1,2,3),{}),
            ('set_rdsheet',('rdsheet2',),{}),
            ('finish',(),{}),
            ])
        
    def test_all(self):
        self.do_calls_and_test(OurMethodFilter(self.called))
        compare(self.called,[
            ('start',()),
            ('workbook',('rdbook','wtbook_name')),
            ('sheet',('rdsheet','wtsheet_name')),
            ('row',(0,1)),
            ('cell',(0,1,2,3)),
            ('set_rdsheet',('rdsheet2',)),
            ('finish',()),
            ])

    def test_all_text(self):
        self.do_calls_and_test(OurMethodFilter(self.called,call_on='True'))
        compare(self.called,[
            ('start',()),
            ('workbook',('rdbook','wtbook_name')),
            ('sheet',('rdsheet','wtsheet_name')),
            ('row',(0,1)),
            ('cell',(0,1,2,3)),
            ('set_rdsheet',('rdsheet2',)),
            ('finish',()),
            ])

    def test_all_text_list(self):
        self.do_calls_and_test(OurMethodFilter(self.called,call_on=['True']))
        compare(self.called,[
            ('start',()),
            ('workbook',('rdbook','wtbook_name')),
            ('sheet',('rdsheet','wtsheet_name')),
            ('row',(0,1)),
            ('cell',(0,1,2,3)),
            ('set_rdsheet',('rdsheet2',)),
            ('finish',()),
            ])

    def test_somecalls_and_test(self):
        self.do_calls_and_test(OurMethodFilter(self.called,['row','cell']))
        compare(self.called,[
            ('row',(0,1)),
            ('cell',(0,1,2,3)),
            ])

    def test_none(self):
        self.do_calls_and_test(OurMethodFilter(self.called,()))
        compare(self.called,[])

    def test_start(self):
        self.do_calls_and_test(OurMethodFilter(self.called,['start']))
        compare(self.called,[
            ('start',()),
            ])

    def test_workbook(self):
        self.do_calls_and_test(OurMethodFilter(self.called,['workbook']))
        compare(self.called,[
            ('workbook',('rdbook','wtbook_name')),
            ])

    def test_sheet(self):
        self.do_calls_and_test(OurMethodFilter(self.called,['sheet']))
        compare(self.called,[
            ('sheet',('rdsheet','wtsheet_name')),
            ])

    def test_set_rdsheet(self):
        self.do_calls_and_test(OurMethodFilter(self.called,['set_rdsheet']))
        compare(self.called,[
            ('set_rdsheet',('rdsheet2',)),
            ])

    def test_row(self):
        self.do_calls_and_test(OurMethodFilter(self.called,['row']))
        compare(self.called,[
            ('row',(0,1)),
            ])

    def test_cell(self):
        self.do_calls_and_test(OurMethodFilter(self.called,['cell']))
        compare(self.called,[
            ('cell',(0,1,2,3)),
            ])

    def test_finish(self):
        self.do_calls_and_test(OurMethodFilter(self.called,['finish']))
        compare(self.called,[
            ('finish',()),
            ])

    def test_invalid(self):
        with ShouldRaise(ValueError("'foo' is not a valid method name")):
            OurMethodFilter(self.called,['foo'])
        
    
from xlutils.filter import Echo

class TestEcho(TestCase):

    @replace('sys.stdout',StringIO())
    def test_method(self,out):
        filter = Echo(methods=['workbook'])
        filter.method('name','foo',1)
        compare(out.getvalue(),"name:('foo', 1)\n")
        
    @replace('sys.stdout',StringIO())
    def test_method_with_name(self,out):
        filter = Echo('echo',['workbook'])
        filter.method('name','foo',1)
        compare(out.getvalue(),"'echo' name:('foo', 1)\n")
        
    def test_inheritance(self):
        self.failUnless(isinstance(Echo(),MethodFilter))

class TestMemoryLogger(TestCase):
    
    def setUp(self):
        from xlutils.filter import MemoryLogger
        self.filter = MemoryLogger('somepath',['workbook'])

    @replace('xlutils.filter.guppy',True)
    @replace('xlutils.filter.hpy',Mock(),strict=False)
    def test_method(self,hpy):
        self.filter.method('name','foo',1)
        # hpy().heap().stat.dump('somepath')
        compare(hpy.call_args_list,[((),{})])
        hpy_i = hpy.return_value
        compare(hpy_i.method_calls,[('heap',(),{})])
        h = hpy_i.heap.return_value
        compare(h.method_calls,[('stat.dump', ('somepath',),{})])
    
    @replace('xlutils.filter.guppy',False)
    @replace('xlutils.filter.hpy',Mock(),strict=False)
    def test_method_no_heapy(self,hpy):
        self.filter.method('name','foo',1)
        compare(hpy.call_args_list,[])
    
    def test_inheritance(self):
        self.failUnless(isinstance(self.filter,MethodFilter))

from xlutils.filter import ErrorFilter

class TestErrorFilter(TestCase):

    def test_open_workbook_args(self):
        r = TestReader(('Sheet1',[['X']]))
        f = ErrorFilter()
        m = Mock()
        process(r,f,m)
        compare(m.method_calls,[
            ('start',(),{}),
            ('workbook',(C('xlrd.Book',
                           formatting_info=1,
                           on_demand=False,
                           ragged_rows=True,
                           strict=False),'test.xls'),{}),
            ('sheet',(C('xlrd.sheet.Sheet'),u'Sheet1'),{}),
            ('row',(0,0),{}),
            ('cell',(0,0,0,0),{}),
            ('finish',(),{}),
            ])
        
    @log_capture()
    def test_set_rdsheet_1(self,h):
        r = TestReader(
            ('Sheet1',[['S1R0C0']]),
            ('Sheet2',[[(XL_CELL_ERROR,0)]]),
            )
        book = tuple(r.get_workbooks())[0][0]
        # fire methods on filter
        f = ErrorFilter()
        f.next = c = Mock()
        f.start()
        f.workbook(book,'new.xls')
        f.sheet(book.sheet_by_index(0),'new')
        f.cell(0,0,0,0)
        f.set_rdsheet(book.sheet_by_index(1))
        f.cell(0,0,1,0)
        f.finish()
        compare(c.method_calls,[])
        h.check(
            ('xlutils.filter','ERROR',"Cell A1 of sheet 'Sheet2' contains a bad value: error (#NULL!)"),
            ('xlutils.filter','ERROR','No output as errors have occurred.'),
            )

    @log_capture()
    def test_set_rdsheet_2(self,h):
        r = TestReader(
            ('Sheet1',[['S1R0C0']]),
            ('Sheet2',[[(XL_CELL_ERROR,0)]]),
            )
        book = tuple(r.get_workbooks())[0][0]
        # fire methods on filter
        f = ErrorFilter()
        f.next = c = Mock()
        f.start()
        f.workbook(book,'new.xls')
        f.sheet(book.sheet_by_index(0),'new')
        f.cell(0,0,0,0)
        f.cell(0,0,1,0)
        f.finish()
        compare(c.method_calls,[
            ('start', (), {}),
            ('workbook', (C('xlrd.Book'), 'new.xls'),{}),
            ('sheet', (C('xlrd.sheet.Sheet',name='new',strict=False), u'new'),{}),
            ('row', (0, 0),{}),
            ('cell', (0, 0, 0, 0),{}),
            ('row', (1, 1),{}),
            ('cell', (1, 0, 1, 0),{}),
            ('finish', (), {})
            ])
        self.assertEqual(len(h.records),0)
    
    @log_capture()
    def test_multiple_workbooks_with_same_name(self,h):
        r = TestReader(
            ('Sheet1',[['S1R0C0']]),
            )
        book = tuple(r.get_workbooks())[0][0]
        # fire methods on filter
        f = ErrorFilter()
        f.next = c = Mock()
        f.start()
        f.workbook(book,'new.xls')
        f.sheet(book.sheet_by_index(0),'new1')
        f.cell(0,0,0,0)
        f.workbook(book,'new.xls')
        f.sheet(book.sheet_by_index(0),'new2')
        f.cell(0,0,0,0)
        f.finish()
        compare(c.method_calls,[
            ('start', (), {}),
            ('workbook', (C('xlrd.Book'), 'new.xls'),{}),
            ('sheet', (C('xlrd.sheet.Sheet',name='new1',strict=False), u'new1'),{}),
            ('row', (0, 0),{}),
            ('cell', (0, 0, 0, 0),{}),
            ('workbook', (C('xlrd.Book'), 'new.xls'),{}),
            ('sheet', (C('xlrd.sheet.Sheet',name='new2',strict=False), u'new2'),{}),
            ('row', (0, 0),{}),
            ('cell', (0, 0, 0, 0),{}),
            ('finish', (), {})
            ])
        self.assertEqual(len(h.records),0)
    
    def test_finish_resets(self):
        # ...that's `start`s job!
        r = TestReader(
            ('Sheet1',[[(XL_CELL_ERROR,0)]]),
            )
        book = tuple(r.get_workbooks())[0][0]
        # fire methods on filter
        f = ErrorFilter()
        f.next = c = Mock()
        f.start()
        f.workbook(book,'new.xls')
        f.sheet(book.sheet_by_index(0),'new1')
        f.cell(0,0,0,0)
        self.assertTrue(f.handler.fired)
        f.finish()
        compare(c.method_calls,[])
        self.assertFalse(f.handler.fired)
        compare(f.temp_path,None)

    @tempdir()
    def test_start(self,d):
        f = ErrorFilter()
        f.next = m = Mock()
        f.wtbook = 'junk'
        f.handler.fired = 'junk'
        f.temp_path = d.path
        f.prefix = 'junk'
        j = open(os.path.join(d.path,'junk.xls'),'wb')
        j.write('junk')
        j.close()

        f.start()

        compare(f.wtbook,None)
        compare(f.handler.fired,False)
        self.failIf(os.path.exists(d.path))
        compare(os.listdir(f.temp_path),[])
        compare(f.prefix,0)

        f.finish()
        
        compare(m.method_calls,[
            ('start', (), {}),
            ('finish', (), {})
            ])

    @log_capture()
    def test_no_error_on_bools(self,h):
        r = TestReader(
            ('Sheet',[[(XL_CELL_BOOLEAN,True)]]),
            )
        # fire methods on filter
        f = ErrorFilter()
        c = Mock()
        process(r,f,c)
        compare(c.method_calls,[
            ('start', (), {}),
            ('workbook', (C('xlrd.Book'), 'test.xls'),{}),
            ('sheet', (C('xlrd.sheet.Sheet',name='Sheet',strict=False), u'Sheet'),{}),
            ('row', (0, 0),{}),
            ('cell', (0, 0, 0, 0),{}),
            ('finish', (), {})
            ])
        self.assertEqual(len(h.records),0)
    
from xlutils.filter import ColumnTrimmer

class TestColumnTrimmer(TestCase):

    @log_capture()
    def test_set_rdsheet_cols(self,h):
        r = TestReader(
            ('Sheet1',[['X',' ']]),
            ('Sheet2',[['X','X']]),
            )
        book = tuple(r.get_workbooks())[0][0]
        # fire methods on filter
        f = ColumnTrimmer()
        f.next = c = Mock()
        f.start()
        f.workbook(book,'new.xls')
        f.sheet(book.sheet_by_index(0),'new')
        f.row(0,0)
        f.cell(0,0,0,0)
        f.set_rdsheet(book.sheet_by_index(1))
        f.cell(0,0,0,1)
        f.finish()
        compare(c.method_calls,[
            ('start', (), {}),
            ('workbook', (C('xlutils.tests.fixtures.DummyBook'), 'new.xls'),{}),
            ('sheet', (C('xlrd.sheet.Sheet',name='Sheet1',strict=False), u'new'),{}),
            ('row', (0, 0),{}),
            ('cell', (0, 0, 0, 0),{}),
            ('set_rdsheet', (C('xlrd.sheet.Sheet',name='Sheet2',strict=False),),{}),
            ('cell', (0, 0, 0, 1),{}),
            ('finish', (), {})
            ])
        self.assertEqual(len(h.records),0)

    def test_set_rdsheet_rows(self):
        r = TestReader(
            ('Sheet1',[['X',' ']]),
            ('Sheet2',[['X','X'],['X','X'],['X','X']]),
            )
        book = tuple(r.get_workbooks())[0][0]
        # fire methods on filter
        f = ColumnTrimmer()
        f.next = c = Mock()
        f.start()
        f.workbook(book,'new.xls')
        f.sheet(book.sheet_by_index(0),'new')
        f.row(0,0)
        f.cell(0,0,0,0)
        f.set_rdsheet(book.sheet_by_index(1))
        f.cell(2,0,1,0)
        f.finish()
        compare(c.method_calls,[
            ('start', (), {}),
            ('workbook', (C('xlutils.tests.fixtures.DummyBook'), 'new.xls'),{}),
            ('sheet', (C('xlrd.sheet.Sheet',name='Sheet1',strict=False), u'new'),{}),
            ('row', (0, 0),{}),
            ('cell', (0, 0, 0, 0),{}),
            ('set_rdsheet', (C('xlrd.sheet.Sheet',name='Sheet2',strict=False),),{}),
            ('cell', (2, 0, 1, 0),{}),
            ('finish', (), {})
            ])

    def test_set_rdsheet_trim(self):
        r = TestReader(
            ('Sheet1',[['X',' ']]),
            ('Sheet2',[['X','X']]),
            )
        book = tuple(r.get_workbooks())[0][0]
        # fire methods on filter
        f = ColumnTrimmer()
        f.next = c = Mock()
        f.start()
        f.workbook(book,'new.xls')
        f.sheet(book.sheet_by_index(0),'new')
        f.row(0,0)
        f.cell(0,0,0,0)
        f.cell(0,1,0,1)
        f.set_rdsheet(book.sheet_by_index(1))
        f.cell(0,0,1,0)
        f.cell(0,1,1,1)
        f.finish()
        compare(c.method_calls,[
            ('start', (), {}),
            ('workbook', (C('xlutils.tests.fixtures.DummyBook'), 'new.xls'),{}),
            ('sheet', (C('xlrd.sheet.Sheet',name='Sheet1',strict=False), u'new'),{}),
            ('row', (0, 0),{}),
            ('cell', (0, 0, 0, 0),{}),
            ('cell', (0, 1, 0, 1),{}),
            ('set_rdsheet', (C('xlrd.sheet.Sheet',name='Sheet2',strict=False),),{}),
            ('cell', (0, 0, 1, 0),{}),
            ('cell', (0, 1, 1, 1),{}),
            ('finish', (), {})
            ])

    @log_capture()
    def test_use_write_sheet_name_in_logging(self,h):
        r = TestReader(
            ('Sheet1',[['X',' ']]),
            )
        book = tuple(r.get_workbooks())[0][0]
        # fire methods on filter
        f = ColumnTrimmer()
        f.next = c = Mock()
        f.start()
        f.workbook(book,'new.xls')
        f.sheet(book.sheet_by_index(0),'new')
        f.row(0,0)
        f.cell(0,0,0,0)
        f.cell(0,1,0,1)
        f.finish()
        compare(c.method_calls,[
            ('start', (), {}),
            ('workbook', (C('xlutils.tests.fixtures.DummyBook'), 'new.xls'),{}),
            ('sheet', (C('xlrd.sheet.Sheet',name='Sheet1',strict=False), u'new'),{}),
            ('row', (0, 0),{}),
            ('cell', (0, 0, 0, 0),{}),
            ('finish', (),{})
            ])
        h.check((
            'xlutils.filter',
            'DEBUG',
            "Number of columns trimmed from 2 to 1 for sheet 'new'"
                ))

    @log_capture()
    def test_multiple_books(self,h):
        r = GlobReader(os.path.join(test_files,'test*.xls'))
        # fire methods on filter
        f = ColumnTrimmer()
        f.next = c = Mock()
        r(f)
        compare(c.method_calls,[
            ('start', (), {}),
            ('workbook', (C('xlrd.Book'), 'test.xls'),{}),
            ('sheet', (C('xlrd.sheet.Sheet'), u'Sheet1'),{}),
            ('row', (0, 0),{}),
            ('row', (1, 1),{}),
            ('cell', (0, 0, 0, 0),{}),('cell', (0, 1, 0, 1),{}),
            ('cell', (1, 0, 1, 0),{}),('cell', (1, 1, 1, 1),{}),
            ('sheet', (C('xlrd.sheet.Sheet'), u'Sheet2'),{}),
            ('row', (0, 0),{}),
            ('row', (1, 1),{}),
            ('cell', (0, 0, 0, 0),{}),('cell', (0, 1, 0, 1),{}),
            ('cell', (1, 0, 1, 0),{}),('cell', (1, 1, 1, 1),{}),
            ('workbook', (C('xlrd.Book'), 'testall.xls'),{}),
            ('sheet', (C('xlrd.sheet.Sheet'), u'Sheet1'),{}),
            ('row', (0, 0),{}),
            ('row', (1, 1),{}),
            ('row', (2, 2),{}),
            ('row', (3, 3),{}),
            ('row', (4, 4),{}),
            ('row', (5, 5),{}),
            ('cell', (0, 0, 0, 0),{}),('cell', (0, 1, 0, 1),{}),
            ('cell', (1, 0, 1, 0),{}),('cell', (1, 1, 1, 1),{}),
            ('cell', (2, 0, 2, 0),{}),
            ('cell', (3, 0, 3, 0),{}),
            ('cell', (5, 0, 5, 0),{}),('cell', (5, 1, 5, 1),{}),
            ('sheet', (C('xlrd.sheet.Sheet'), u'Sheet2'),{}),
            ('row', (0, 0),{}),
            ('row', (1, 1),{}),
            ('cell', (0, 0, 0, 0),{}),('cell', (0, 1, 0, 1),{}),
            ('cell', (1, 0, 1, 0),{}),('cell', (1, 1, 1, 1),{}),
            ('workbook', (C('xlrd.Book'), 'testnoformatting.xls'), {}),
            ('sheet', (C('xlrd.sheet.Sheet'), u'Sheet1'), {}),
            ('row', (0, 0), {}),
            ('row', (1, 1), {}),
            ('row', (2, 2), {}),
            ('row', (3, 3), {}),
            ('row', (4, 4), {}),
            ('row', (5, 5), {}),
            ('cell', (0, 0, 0, 0), {}),
            ('cell', (0, 1, 0, 1), {}),
            ('cell', (1, 0, 1, 0), {}),
            ('cell', (1, 1, 1, 1), {}),
            ('cell', (2, 0, 2, 0), {}),
            ('cell', (5, 0, 5, 0), {}),
            ('sheet', (C('xlrd.sheet.Sheet'), u'Sheet2'), {}),
            ('row', (0, 0), {}),
            ('row', (1, 1), {}),
            ('cell', (0, 0, 0, 0), {}),
            ('cell', (0, 1, 0, 1), {}),
            ('cell', (1, 0, 1, 0), {}),
            ('cell', (1, 1, 1, 1), {}),
            ('finish', (), {})
            ])
        self.assertEqual(len(h.records),0)

    def test_start(self):
        f = ColumnTrimmer()
        f.next = m = Mock()
        f.rdsheet = 'junk'
        f.pending_rdsheet = 'junk'
        f.ranges = 'junk'
        f.max_nonjunk = 'junk'
        f.max = 'junk'

        f.start()

        compare(f.rdsheet,None)
        compare(f.pending_rdsheet,None)
        compare(f.ranges,[])
        compare(f.max_nonjunk,0)
        compare(f.max,0)

        compare(m.method_calls,[
            ('start', (), {})
            ])
    
class CloseableTemporaryFile:
    def __init__(self,parent,filename):
        self.file = TemporaryFile()
        self.parent=parent
        self.filename=filename
    def close(self):
        self.parent.closed.add(self.filename)
        self.file.seek(0)
    def write(self,*args,**kw):
        self.file.write(*args,**kw)
    def real_close(self):
        self.file.close()
        
class TestWriter(BaseWriter):

    def __init__(self):
        self.files = {}
        self.closed = set()
        
    def get_stream(self,filename):
        f = CloseableTemporaryFile(self,filename)
        self.files[filename]=f
        return f
        
class TestBaseWriter(TestCase):

    def note_index(self,ao,eo,name):
        if name not in self.noted_indexes:
            self.noted_indexes[name]={}
        mapping = self.noted_indexes[name]
        a,e = getattr(ao,name,None),getattr(eo,name,None)
        if a not in mapping:
            mapping[a]=set()
        # for style compression, we may get multiple expected indexes
        # for each actual index in the output file. We just need to make
        # sure all the data is the same.
        mapping.get(a).add(e)
        
    def check_file(self,writer,path,
                   l_a_xf_list=20,
                   l_e_xf_list=26,
                   l_a_format_map=76,
                   l_e_format_map=75,
                   l_a_font_list=9,
                   l_e_font_list=7,
                   **provided_overrides):
        # allow overrides to be specified, as well as
        # default overrides, to save typing
        overrides = {
            'sheet':dict(
                # BUG: xlwt does nothing with col_default_width, it should :-(
                defcolwidth=None,
                )
            }
        for k,d in provided_overrides.items():
            if k in overrides:
                overrides[k].update(d)
            else:
                overrides[k]=d
                
        self.noted_indexes = {}
        # now open the source file
        e = open_workbook(path, formatting_info=1)
        # and the target file
        f = writer.files[os.path.split(path)[1]].file
        a = open_workbook(file_contents=f.read(), formatting_info=1)
        f.close()
        # and then compare
        def assertEqual(e,a,overrides,t,*names):
            for name in names:
                ea = overrides.get(t,{}).get(name,getattr(e,name))
                aa = getattr(a,name)
                self.assertEqual(aa,ea,'%s: %r(actual)!=%r(expected)'%(name,aa,ea))

        assertEqual(e, a, overrides, 'book',
                    'nsheets',
                    'datemode')
        
        for sheet_x in range(a.nsheets):
            ash = a.sheet_by_index(sheet_x)
            es = e.sheet_by_index(sheet_x)
            
            # order doesn't matter in this list
            compare(sorted(ash.merged_cells),sorted(es.merged_cells))

            assertEqual(
                es,ash,overrides,'sheet',
                'show_formulas',
                'show_grid_lines',
                'show_sheet_headers',
                'panes_are_frozen',
                'show_zero_values',
                'automatic_grid_line_colour',
                'columns_from_right_to_left',
                'show_outline_symbols',
                'remove_splits_if_pane_freeze_is_removed',
                'sheet_selected',
                'sheet_visible',
                'show_in_page_break_preview',
                'first_visible_rowx',
                'first_visible_colx',
                'gridline_colour_index',
                'cooked_page_break_preview_mag_factor',
                'cooked_normal_view_mag_factor',
                'default_row_height',
                'default_row_height_mismatch',
                'default_row_hidden',
                'default_additional_space_above',
                'default_additional_space_below',
                'nrows',
                'ncols',
                'standardwidth',
                'vert_split_pos',
                'horz_split_pos',
                'vert_split_first_visible',
                'horz_split_first_visible',
                'split_active_pane',
                )
            for col_x in range(ash.ncols):
                ac = ash.colinfo_map.get(col_x)
                ec = es.colinfo_map.get(col_x)
                if ac is not None:
                    assertEqual(ec,ac,overrides,'col',
                                'width',
                                'hidden',
                                'outline_level',
                                'collapsed',
                                )
                self.note_index(ac,ec,'xf_index')
            for row_x in range(ash.nrows):
                ar = ash.rowinfo_map.get(row_x)
                er = es.rowinfo_map.get(row_x)
                if er is None:
                    # NB: wlxt always writes Rowinfos, even
                    #     if none is supplied.
                    #     So, they end up with default values
                    #     which is what this tests
                    er = ar.__class__
                else:
                    assertEqual(er,ar,overrides,'row',
                                'height',
                                'has_default_height',
                                'height_mismatch',
                                'outline_level',
                                'outline_group_starts_ends',
                                'hidden',
                                'additional_space_above',
                                'additional_space_below',
                                'has_default_xf_index',
                                )
                    if ar.has_default_xf_index:
                        self.note_index(ar,er,'xf_index')
                for col_x in range(ash.ncols):
                    ac = ash.cell(row_x,col_x)
                    ec = es.cell(row_x,col_x)
                    assertEqual(ec,ac,overrides,'cell',
                                'ctype',
                                'value')
                    self.note_index(ac,ec,'xf_index')

        # only XFs that are in use are copied,
        # but we check those copied are identical
        self.assertEqual(len(a.xf_list),l_a_xf_list)
        self.assertEqual(len(e.xf_list),l_e_xf_list)
        for ai,eis in self.noted_indexes['xf_index'].items():
            if ai is None:
                continue
            axf = a.xf_list[ai]
            for ei in eis:
                exf = e.xf_list[ei]
                self.note_index(axf,exf,'format_key')
                self.note_index(axf,exf,'font_index')
                ap = axf.protection
                ep = exf.protection
                assertEqual(ep,ap,overrides,'protection',
                            'cell_locked',
                            'formula_hidden',
                            )
                ab = axf.border
                eb = exf.border
                assertEqual(eb,ab,overrides,'border',
                            'left_line_style',
                            'right_line_style',
                            'top_line_style',
                            'bottom_line_style',
                            'diag_line_style',
                            'left_colour_index',
                            'right_colour_index',
                            'top_colour_index',
                            'bottom_colour_index',
                            'diag_colour_index',
                            'diag_down',
                            'diag_up',
                            )
                ab = axf.background
                eb = exf.background
                assertEqual(eb,ab,overrides,'background',
                            'fill_pattern',
                            'pattern_colour_index',
                            'background_colour_index',
                            )
                aa = axf.alignment
                ea = exf.alignment
                assertEqual(ea,aa,overrides,'alignment',
                            'hor_align',
                            'vert_align',
                            'text_direction',
                            'rotation',
                            'text_wrapped',
                            'shrink_to_fit',
                            'indent_level',
                            )
            
        # xlwt writes more formats than exist in an original,
        # but we check those copied are identical
        self.assertEqual(len(a.format_map), l_a_format_map)
        self.assertEqual(len(e.format_map), l_e_format_map)
        for ai,eis in self.noted_indexes['format_key'].items():
            af = a.format_map[ai]
            for ei in eis:
                ef = e.format_map[ei]
                assertEqual(ef,af,overrides,'format',
                            'format_str',
                            'type')
        # xlwt writes more fonts than exist in an original,
        # but we check those that exist in both...
        self.assertEqual(len(a.font_list),l_a_font_list)
        self.assertEqual(len(e.font_list),l_e_font_list)
        for ai,eis in self.noted_indexes['font_index'].items():
            af = a.font_list[ai]
            for ei in eis:
                ef = e.font_list[ei]
                assertEqual(ef,af,overrides,'font',
                            'height',
                            'italic',
                            'struck_out',
                            'outline',
                            'colour_index',
                            'bold',
                            'weight',
                            'escapement',
                            'underline_type',
                            'family',
                            'character_set',
                            'name',
                            )

    def test_single_workbook_with_all_features(self):
        # create test reader
        test_xls_path = os.path.join(test_files,'testall.xls')
        r = GlobReader(test_xls_path)
        # source sheet must have merged cells for test!
        book = tuple(r.get_workbooks())[0][0]
        self.failUnless(book.sheet_by_index(0).merged_cells)
        # source book must also have a sheet other than the
        # first one selected
        compare([s.sheet_selected for s in book.sheets()],[0,1])
        compare([s.sheet_visible for s in book.sheets()],[0,1])
        # source book must have show zeros set appropriately:
        compare([s.show_zero_values for s in book.sheets()],[0,0])
        # send straight to writer
        w = TestWriter()
        r(w)
        # check stuff on the writer
        self.assertEqual(w.files.keys(),['testall.xls'])
        self.failUnless('testall.xls' in w.closed)
        self.check_file(w,test_xls_path)

    def test_dates(self):
        # create test reader
        xls_path = os.path.join(test_files, 'date.xls')
        r = GlobReader(xls_path)
        # source book must be in weird date mode
        book = tuple(r.get_workbooks())[0][0]
        self.assertEqual(book.datemode, 1)
        # send straight to writer
        w = TestWriter()
        r(w)
        self.check_file(w, xls_path,
                        # date.xls is fewer sheets and styles than the default
                        l_a_xf_list=19,
                        l_e_xf_list=65,
                        l_e_format_map=74,
                        l_a_font_list=7,
                        l_e_font_list=25,
                        # dates.xls had a standardwidth record but xlwt can't
                        # currently write these :-/
                        sheet=dict(standardwidth=None),)

    def test_single_workbook_no_formatting(self):
        # create test reader
        test_xls_path = os.path.join(test_files,'testnoformatting.xls')
        r = XLRDReader(open_workbook(os.path.join(test_files,'testall.xls')),'testnoformatting.xls')
        # source sheet must have merged cells for test!
        # send straight to writer
        w = TestWriter()
        r(w)
        # check stuff on the writer
        self.assertEqual(w.files.keys(),['testnoformatting.xls'])
        self.failUnless('testnoformatting.xls' in w.closed)
        self.check_file(w,test_xls_path,
                        l_a_xf_list=17,
                        l_e_xf_list=17,
                        l_a_format_map=75,
                        l_a_font_list=6,
                        l_e_font_list=6)

    def test_multiple_workbooks(self):
        # globreader is tested elsewhere
        r = GlobReader(os.path.join(test_files,'test*.xls'))
        # send straight to writer
        w = TestWriter()
        r(w)
        # check stuff on the writer
        self.assertEqual(w.files.keys(),['test.xls','testnoformatting.xls','testall.xls'])
        self.failUnless('test.xls' in w.closed)
        self.failUnless('testall.xls' in w.closed)
        self.failUnless('testnoformatting.xls' in w.closed)
        self.check_file(w,os.path.join(test_files,'testall.xls'))
        self.check_file(w,os.path.join(test_files,'test.xls'),
                        18,21,76,75,7,4)
        self.check_file(w,os.path.join(test_files,'testnoformatting.xls'),
                        18,17,75,75,6,6)
    
    def test_start(self):
        w = TestWriter()
        w.wtbook = 'junk'
        w.start()
        compare(w.wtbook,None)
    
    @replace('xlutils.filter.BaseWriter.close',Mock())
    def test_workbook(self,c):
        # style copying is tested in the more complete tests
        # here we just check that certain atributes are set properly
        w = TestWriter()
        w.style_list = 'junk'
        w.wtsheet_names = 'junk'
        w.wtsheet_index = 'junk'
        w.sheet_visible = 'junk'
        b = make_book()
        w.workbook(b,'foo')
        compare(c.call_args_list,[((),{})])
        compare(w.rdbook,b)
        compare(w.wtbook,C('xlwt.Workbook'))
        compare(w.wtname,'foo')
        compare(w.style_list,[])
        compare(w.wtsheet_names,set())
        compare(w.wtsheet_index,0)
        compare(w.sheet_visible,False)
    
    def test_set_rd_sheet(self):
        # also tests that 'row' doesn't have to be called,
        # only cell
        r = TestReader(
            ('Sheet1',(('S1R0C0',),
                       ('S1R1C0',),)),
            ('Sheet2',(('S2R0C0',),
                       ('S2R1C0',),)),
            )
        book = tuple(r.get_workbooks())[0][0]
        # fire methods on writer
        w = TestWriter()
        w.start()
        w.workbook(book,'new.xls')
        w.sheet(book.sheet_by_index(0),'new')
        w.row(0,0)
        w.cell(0,0,0,0)
        w.set_rdsheet(book.sheet_by_index(1))
        w.cell(0,0,1,0)
        w.set_rdsheet(book.sheet_by_index(0))
        w.cell(1,0,2,0)
        w.set_rdsheet(book.sheet_by_index(1))
        w.cell(1,0,3,0)
        w.finish()
        # check everything got written and closed
        self.assertEqual(w.files.keys(),['new.xls'])
        self.failUnless('new.xls' in w.closed)
        # now check the cells written
        f = w.files['new.xls'].file
        a = open_workbook(file_contents=f.read(), formatting_info=1)
        self.assertEqual(a.nsheets,1)
        sheet = a.sheet_by_index(0)
        self.assertEqual(sheet.nrows,4)
        self.assertEqual(sheet.ncols,1)
        self.assertEqual(sheet.cell(0,0).value,'S1R0C0')
        self.assertEqual(sheet.cell(1,0).value,'S2R0C0')
        self.assertEqual(sheet.cell(2,0).value,'S1R1C0')
        self.assertEqual(sheet.cell(3,0).value,'S2R1C0')
        
    def test_bogus_sheet_name(self):
        r = TestReader(
            ('sheet',([['S1R0C0']]),),
            ('Sheet',([['S2R0C0']]),),
            )
        # fire methods on writer
        with ShouldRaise(ValueError(
            "A sheet named 'sheet' has already been added!"
            )):
            r(TestWriter())
    
    def test_empty_sheet_name(self):
        r = TestReader(
            ('',([['S1R0C0']]),),
            )
        # fire methods on writer
        with ShouldRaise(ValueError(
            'Empty sheet name will result in invalid Excel file!'
            )):
            r(TestWriter())
    
    def test_max_length_sheet_name(self):
        name = 'X'*31
        r = TestReader(
            (name,([['S1R0C0']]),),
            )
        w = TestWriter()
        r(w)
        self.assertEqual(w.files.keys(),['test.xls'])
        f = w.files['test.xls'].file
        a = open_workbook(file_contents=f.read(), formatting_info=1)
        self.assertEqual(a.sheet_names(),[name])
        
    def test_panes(self):
        r = TestReader()
        r.formatting_info = True
        
        r.setup(('sheet',[['S1R0C0']]))
        
        book = tuple(r.get_workbooks())[0][0]
        sheet = book.sheet_by_index(0)
        sheet.panes_are_frozen = 1
        sheet.has_pane_record = True
        sheet.vert_split_pos = 1
        sheet.horz_split_pos = 2
        sheet.vert_split_first_visible = 3
        sheet.horz_split_first_visible = 4
        sheet.split_active_pane = 3
        
        w = TestWriter()
        r(w)
        
        self.assertEqual(w.files.keys(),['test.xls'])
        f = w.files['test.xls'].file
        a = open_workbook(file_contents=f.read(),formatting_info=1)
        sheet = a.sheet_by_index(0)
        self.assertEqual(1,sheet.panes_are_frozen)
        self.assertEqual(1,sheet.has_pane_record)
        self.assertEqual(1,sheet.vert_split_pos)
        self.assertEqual(2,sheet.horz_split_pos)
        self.assertEqual(3,sheet.vert_split_first_visible)
        self.assertEqual(4,sheet.horz_split_first_visible)
        # for splits, this is a magic value, and is computed
        # by xlwt.
        self.assertEqual(0,sheet.split_active_pane)
        
    def test_splits(self):
        r = TestReader()
        r.formatting_info = True
        
        r.setup(('sheet',[['S1R0C0']]))
        
        book = tuple(r.get_workbooks())[0][0]
        sheet = book.sheet_by_index(0)
        sheet.panes_are_frozen = 0
        sheet.has_pane_record = True
        sheet.vert_split_pos = 1
        sheet.horz_split_pos = 2
        sheet.vert_split_first_visible = 3
        sheet.horz_split_first_visible = 4
        sheet.split_active_pane = 3
        
        w = TestWriter()
        r(w)
        
        self.assertEqual(w.files.keys(),['test.xls'])
        f = w.files['test.xls'].file
        a = open_workbook(file_contents=f.read(),formatting_info=1)
        sheet = a.sheet_by_index(0)
        self.assertEqual(0,sheet.panes_are_frozen)
        self.assertEqual(1,sheet.has_pane_record)
        self.assertEqual(1,sheet.vert_split_pos)
        self.assertEqual(2,sheet.horz_split_pos)
        self.assertEqual(3,sheet.vert_split_first_visible)
        self.assertEqual(4,sheet.horz_split_first_visible)
        self.assertEqual(3,sheet.split_active_pane)
        
    def test_zoom_factors(self):
        r = TestReader()
        r.formatting_info = True
        
        r.setup(('sheet',[['S1R0C0']]))
        
        book = tuple(r.get_workbooks())[0][0]
        sheet = book.sheet_by_index(0)
        sheet.cooked_normal_view_mag_factor = 33
        sheet.cooked_page_break_preview_mag_factor = 44
        sheet.show_in_page_break_preview = True

        w = TestWriter()
        r(w)
        
        self.assertEqual(w.files.keys(),['test.xls'])
        f = w.files['test.xls'].file
        a = open_workbook(file_contents=f.read(),formatting_info=1)
        sheet = a.sheet_by_index(0)
        self.assertEqual(33,sheet.cooked_normal_view_mag_factor)
        self.assertEqual(44,sheet.cooked_page_break_preview_mag_factor)
        self.assertEqual(1,sheet.show_in_page_break_preview)
        
    def test_excessive_length_sheet_name(self):
        r = TestReader(
            ('X'*32,([['S1R0C0']]),),
            )
        # fire methods on writer
        with ShouldRaise(ValueError(
            'Sheet name cannot be more than 31 characters long, '
            'supplied name was 32 characters long!'
            )):
            r(TestWriter())

    def test_copy_error_cells(self):
        r = TestReader(
            ('Errors',([[(XL_CELL_ERROR,0)]]),),
            )
        w = TestWriter()
        r(w)
        self.assertEqual(w.files.keys(),['test.xls'])
        a = open_workbook(file_contents=w.files['test.xls'].file.read())
        cell = a.sheet_by_index(0).cell(0,0)
        self.assertEqual(cell.ctype,XL_CELL_ERROR)
        self.assertEqual(cell.value,0)
    
    def test_copy_boolean_cells(self):
        r = TestReader(
            ('Bools',([[(XL_CELL_BOOLEAN,True)]]),),
            )
        w = TestWriter()
        r(w)
        self.assertEqual(w.files.keys(),['test.xls'])
        a = open_workbook(file_contents=w.files['test.xls'].file.read())
        cell = a.sheet_by_index(0).cell(0,0)
        self.assertEqual(cell.ctype,XL_CELL_BOOLEAN)
        self.assertEqual(cell.value,True)
    
class TestDirectoryWriter(TestCase):

    def test_inheritance(self):
        from xlutils.filter import DirectoryWriter
        self.failUnless(isinstance(DirectoryWriter('foo'),BaseWriter))

    @tempdir()
    def test_plus_in_workbook_name(self,d):
        from xlutils.filter import DirectoryWriter
        r = TestReader(
            ('Sheet1',[['Cell']]),
            )
        book = tuple(r.get_workbooks())[0][0]
        # fire methods on writer
        w = DirectoryWriter(d.path)
        w.start()
        w.workbook(book,'a+file.xls')
        w.sheet(book.sheet_by_index(0),'new')
        w.row(0,0)
        w.cell(0,0,0,0)
        w.finish()
        # check file exists with the right name
        self.assertEqual(os.listdir(d.path),['a+file.xls'])

class TestXLWTWriter(TestCase):

    def setUp(self):
        self.w = XLWTWriter()
        
    def test_inheritance(self):
        self.failUnless(isinstance(self.w,BaseWriter))

    def test_no_files(self):
        r = GlobReader(os.path.join(test_files,'*not.xls'))
        r(self.w)
        compare(self.w.output,[])
        
    def test_one_file(self):
        r = GlobReader(os.path.join(test_files,'test.xls'))
        r(self.w)
        compare(self.w.output,[
            ('test.xls',C('xlwt.Workbook'))
            ])
        # make sure wtbook is deleted
        compare(self.w.wtbook,None)
        
    def test_multiple_files(self):
        r = GlobReader(os.path.join(test_files,'test*.xls'))
        r(self.w)
        compare(self.w.output,[
            ('test.xls',C('xlwt.Workbook')),
            ('testall.xls',C('xlwt.Workbook')),
            ('testnoformatting.xls',C('xlwt.Workbook')),
            ])
        
    def test_multiple_files_same_name(self):
        r = TestReader(
            ('Sheet1',[['S1R0C0']]),
            )
        book = tuple(r.get_workbooks())[0][0]
        self.w.start()
        self.w.workbook(book,'new.xls')
        self.w.sheet(book.sheet_by_index(0),'new1')
        self.w.cell(0,0,0,0)
        self.w.workbook(book,'new.xls')
        self.w.sheet(book.sheet_by_index(0),'new2')
        self.w.cell(0,0,0,0)
        self.w.finish()
        compare(self.w.output,[
            ('new.xls',C('xlwt.Workbook')),
            ('new.xls',C('xlwt.Workbook')),
            ])
        compare(self.w.output[0][1].get_sheet(0).name,
                'new1')
        compare(self.w.output[1][1].get_sheet(0).name,
                'new2')

class TestProcess(TestCase):

    def test_setup(self):
        class DummyReader:
            def __call__(self,filter):
                filter.finished()
        F1 = Mock()
        F2 = Mock()
        process(DummyReader(),F1,F2)
        self.failUnless(F1.next is F2)
        self.failUnless(isinstance(F2.next,Mock))
        compare(F1.method_calls,[('finished',(),{})])
        compare(F2.method_calls,[])
    
class TestTestReader(TestCase):

    def test_cell_type(self):
        r = TestReader(('Sheet1',(((XL_CELL_NUMBER,0.0),),)))
        book = tuple(r.get_workbooks())[0][0]
        cell = book.sheet_by_index(0).cell(0,0)
        self.assertEqual(cell.value,0.0)
        self.assertEqual(cell.ctype,XL_CELL_NUMBER)
        
    def test(self):
        r = TestReader(
            test1=[('Sheet1',[['R1C1','R1C2'],
                              ['R2C1','R2C2']]),
                   ('Sheet2',[['R3C1','R3C2'],
                              ['R4C1','R4C2']])],
            test2=[('Sheet3',[['R5C1','R5C2'],
                              ['R6C1','R6C2']]),
                   ('Sheet4',[['R7C1','R7C2'],
                              ['R8C1','R8C2']])],
            )
        f = Mock()
        r(f)
        compare([
            ('start', (), {}),
            ('workbook', (C('xlutils.tests.fixtures.DummyBook'), 'test1.xls'), {}),
            ('sheet', (C('xlrd.sheet.Sheet'), 'Sheet1'), {}),
            ('row', (0, 0), {}),
            ('cell', (0, 0, 0, 0), {}),
            ('cell',(0, 1, 0, 1), {}),
            ('row', (1, 1), {}),
            ('cell', (1, 0, 1, 0), {}),
            ('cell',(1, 1, 1, 1), {}),
            ('sheet', (C('xlrd.sheet.Sheet'), 'Sheet2'), {}),
            ('row', (0, 0), {}),
            ('cell', (0, 0, 0, 0), {}),
            ('cell',(0, 1, 0, 1), {}),
            ('row', (1, 1), {}),
            ('cell', (1, 0, 1, 0), {}),
            ('cell',(1, 1, 1, 1), {}),
            ('workbook', (C('xlutils.tests.fixtures.DummyBook'), 'test2.xls'), {}),
            ('sheet', (C('xlrd.sheet.Sheet'), 'Sheet3'), {}),
            ('row', (0, 0), {}),
            ('cell', (0, 0, 0, 0), {}),
            ('cell',(0, 1, 0, 1), {}),
            ('row', (1, 1), {}),
            ('cell', (1, 0, 1, 0), {}),
            ('cell',(1, 1, 1, 1), {}),
            ('sheet', (C('xlrd.sheet.Sheet'), 'Sheet4'), {}),
            ('row', (0, 0), {}),
            ('cell', (0, 0, 0, 0), {}),
            ('cell',(0, 1, 0, 1), {}),
            ('row', (1, 1), {}),
            ('cell', (1, 0, 1, 0), {}),
            ('cell',(1, 1, 1, 1), {}),
            ('finish', (), {})
            ],f.method_calls)
        
    def test_setup(self):
        r = TestReader()
        f = Mock()
        r(f)
        compare([('start', (), {}), ('finish', (), {})],f.method_calls)
        r.setup(('Sheet1',[['R1C1']]),
                test1=[('Sheet2',[['R2C1']])])
        r(f)
        compare([
            ('start', (), {}),
            ('finish', (), {}),
            ('start', (), {}),
            ('workbook',(C('xlutils.tests.fixtures.DummyBook'), 'test.xls'),{}),
            ('sheet', (C('xlrd.sheet.Sheet'), 'Sheet1'), {}),
            ('row', (0, 0), {}),
            ('cell', (0, 0, 0, 0), {}),
            ('workbook',(C('xlutils.tests.fixtures.DummyBook'), 'test1.xls'),{}),
            ('sheet', (C('xlrd.sheet.Sheet'), 'Sheet2'), {}),
            ('row', (0, 0), {}),
            ('cell', (0, 0, 0, 0), {}),
            ('finish', (), {})],f.method_calls)
        
    def test_formatting_info(self):
        r = TestReader()
        f = Mock()
        
        r.formatting_info = True
        
        r.setup(('Sheet1',[['R1C1','R1C2']]))

        # at this point you can now manipulate the xf index as follows:
        book = r.books[0][0]
        sx,rx,cx = 0,0,0
        book.sheet_by_index(sx)._cell_xf_indexes[rx][cx]=42
        # NB: cells where you haven't specified an xf index manually as
        #     above will have an xf index of 0:
        compare(book.sheet_by_index(0).cell(0,1).xf_index,0)

        # NB: when formattng is turned on, an XF will be created at index zero:
        compare(C(XF),book.xf_list[0])
        # ...but no others:
        with ShouldRaise(IndexError):
            book.xf_list[42]
        # so you'll need to manually create them if you need them.
        # See fixtures.py for examples.

        r(f)
        
        compare([
            ('start', (), {}),
            ('workbook',(C('xlutils.tests.fixtures.DummyBook'), 'test.xls'),{}),
            ('sheet', (C('xlrd.sheet.Sheet'), 'Sheet1'), {}),
            ('row', (0, 0), {}),
            ('cell', (0, 0, 0, 0), {}),
            ('cell', (0, 1, 0, 1), {}),
            ('finish', (), {})],f.method_calls)

        compare(book.sheet_by_index(0).cell(0,0).xf_index,42)
        
        
def test_suite():
    return TestSuite((
        makeSuite(TestBaseReader),
        makeSuite(TestTestReader),
        makeSuite(TestBaseFilter),
        makeSuite(TestMethodFilter),
        makeSuite(TestEcho),
        makeSuite(TestMemoryLogger),
        makeSuite(TestErrorFilter),
        makeSuite(TestColumnTrimmer),
        makeSuite(TestBaseWriter),
        makeSuite(TestDirectoryWriter),
        makeSuite(TestXLWTWriter),
        makeSuite(TestProcess),
        ))

########NEW FILE########
__FILENAME__ = test_save
# Copyright (c) 2008 Simplistix Ltd
#
# This Software is released under the MIT License:
# http://www.opensource.org/licenses/mit-license.html
# See license.txt for more details.

import os
from mock import Mock
from shutil import rmtree
from StringIO import StringIO
from tempfile import mkdtemp,TemporaryFile
from testfixtures import replace,tempdir
from unittest import TestSuite,TestCase,makeSuite
from xlutils.save import save
from xlutils.filter import XLRDReader,StreamWriter

class TestSave(TestCase):

    @tempdir()
    @replace('xlutils.save.process',Mock())
    def test_save_path(self,c,d):
        wb = object()
        path = os.path.join(d.path,'path.xls')
        
        save(wb,path)
        
        self.assertEqual(len(c.call_args_list),1)
        args = c.call_args_list[0][0]
        self.assertEqual(len(args),2)
        r = args[0]
        self.failUnless(isinstance(r,XLRDReader))
        self.failUnless(r.wb is wb)
        self.assertEqual(r.filename,'path.xls')
        w = args[1]
        self.failUnless(isinstance(w,StreamWriter))
        f = w.stream
        self.failUnless(isinstance(f,file))
        self.assertEqual(f.name,path)
        self.assertEqual(f.mode,'wb')
        self.assertEqual(f.closed,True)
        
    @replace('xlutils.save.process',Mock())
    def test_save_stringio(self,c):
        wb = object()
        s = StringIO()
        
        save(wb,s)
        
        self.assertEqual(len(c.call_args_list),1)
        args = c.call_args_list[0][0]
        self.assertEqual(len(args),2)
        r = args[0]
        self.failUnless(isinstance(r,XLRDReader))
        self.failUnless(r.wb is wb)
        self.assertEqual(r.filename,'unknown.xls')
        w = args[1]
        self.failUnless(isinstance(w,StreamWriter))
        self.failUnless(w.stream is s)

    @replace('xlutils.save.process',Mock())
    def test_save_tempfile(self,c):
        wb = object()
        ef = TemporaryFile()
        
        save(wb,ef)
        
        self.assertEqual(len(c.call_args_list),1)
        args = c.call_args_list[0][0]
        self.assertEqual(len(args),2)
        r = args[0]
        self.failUnless(isinstance(r,XLRDReader))
        self.failUnless(r.wb is wb)
        self.assertEqual(r.filename,'unknown.xls')
        w = args[1]
        self.failUnless(isinstance(w,StreamWriter))
        af = w.stream
        self.failUnless(af is ef)
        self.assertEqual(ef.closed,False)
    
def test_suite():
    return TestSuite((
        makeSuite(TestSave),
        ))

########NEW FILE########
__FILENAME__ = test_styles
# Copyright (c) 2009 Simplistix Ltd
#
# This Software is released under the MIT License:
# http://www.opensource.org/licenses/mit-license.html
# See license.txt for more details.

from mock import Mock
from testfixtures import should_raise
from unittest import TestSuite,TestCase,makeSuite
from xlutils.styles import Styles

class TestStyles(TestCase):

    def setUp(self):
        self.wb = Mock()
        self.wb.style_name_map = {
            '':(0,0),
            'Normal':(1,0),
            }
        xf0 = Mock()
        xf0.is_style = True
        xf0.parent_style_index=4095
        xf1 = Mock()
        xf1.is_style = False
        xf1.parent_style_index=0
        self.wb.xf_list = [xf0,xf1]
        
    def test_multiple_names_for_xfi_okay(self):
        # setup our mock workbooks
        self.wb.style_name_map = {
            '':(0,0),
            'Normal':(1,0),
            }
        
        # process it into styles
        s = Styles(self.wb)

        # now lookup a "cell" with xfi 0
        cell = Mock()
        cell.xf_index = 1
        self.assertEqual(s[cell].name,'Normal')
        
    def test_multiple_names_for_xfi_bad_1(self):
        self.wb.style_name_map = {
            'A':(0,0),
            'B':(0,0),
            }
        styles = should_raise(Styles,AssertionError)
        styles(self.wb)
        
    def test_multiple_names_for_xfi_bad_2(self):
        self.wb.style_name_map = {
            'A':(0,0),
            '':(0,0),
            }
        styles = should_raise(Styles,AssertionError)
        styles(self.wb)
        
def test_suite():
    return TestSuite((
        makeSuite(TestStyles),
        ))

########NEW FILE########
__FILENAME__ = test_view
# Copyright (c) 2013 Simplistix Ltd
#
# This Software is released under the MIT License:
# http://www.opensource.org/licenses/mit-license.html
# See license.txt for more details.
from datetime import datetime, time
from os import path
from unittest import TestCase

from testfixtures import compare, ShouldRaise

from xlutils.view import View, Row, Col, CheckerView
from xlutils.tests.fixtures import test_files

class Check(object):

    def _check(self, view, *expected):
        actual = []
        for row in view:
            actual.append(tuple(row))
        compare(expected, tuple(actual))
    
class ViewTests(Check, TestCase):
        
    def test_string_index(self):
        self._check(
            View(path.join(test_files,'testall.xls'))['Sheet1'],
            (u'R0C0', u'R0C1'),
            (u'R1C0', u'R1C1'),
            (u'A merged cell', ''),
            ('', ''),
            ('', ''),
            (u'More merged cells', '')
            )

    def test_int_index(self):
        self._check(
            View(path.join(test_files,'testall.xls'))[0],
            (u'R0C0', u'R0C1'),
            (u'R1C0', u'R1C1'),
            (u'A merged cell', ''),
            ('', ''),
            ('', ''),
            (u'More merged cells', '')
            )

    def test_dates_and_times(self):
        self._check(
            View(path.join(test_files,'datetime.xls'))[0],
            (datetime(2012, 4, 13, 0, 0), ),
            (time(12, 54, 37), ),
            (datetime(2014, 2, 14, 4, 56, 23), ),
            )

    def test_subclass(self):
        class MySheetView:
            def __init__(self, book, sheet):
                self.book, self.sheet = book, sheet
        class MyView(View):
            class_ = MySheetView
        view = MyView(path.join(test_files,'testall.xls'))
        sheet_view = view[0]
        self.assertTrue(isinstance(sheet_view, MySheetView))
        self.assertTrue(sheet_view.book is view.book)
        self.assertTrue(sheet_view.sheet is view.book.sheet_by_index(0))

    def test_passed_in_class(self):
        class MySheetView:
            def __init__(self, book, sheet):
                self.book, self.sheet = book, sheet
        view = View(path.join(test_files,'testall.xls'), class_=MySheetView)
        sheet_view = view[0]
        self.assertTrue(isinstance(sheet_view, MySheetView))
        self.assertTrue(sheet_view.book is view.book)
        self.assertTrue(sheet_view.sheet is view.book.sheet_by_index(0))

class SliceTests(Check, TestCase):

    def setUp(self):
        self.view = View(path.join(test_files,'testall.xls'))[0]

    def test_slice_int_ranges(self):
        self._check(
            self.view[1:2, 1:2],
            (u'R1C1',),
            )
        self._check(
            self.view[0:2, 0:1],
            (u'R0C0', ),
            (u'R1C0', ),
            )

    def test_slice_open_ranges(self):
        self._check(
            self.view[1:, 1:],
            (u'R1C1',),
            ('',),
            ('',),
            ('',),
            ('',)
            )
        self._check(
            self.view[:2, :2],
            (u'R0C0', u'R0C1'),
            (u'R1C0', u'R1C1'),
            )
        self._check(
            self.view[:, :],
            (u'R0C0', u'R0C1'),
            (u'R1C0', u'R1C1'),
            (u'A merged cell', ''),
            ('', ''),
            ('', ''),
            (u'More merged cells', '')
            )

    def test_slice_negative_ranges(self):
        self._check(
            self.view[-5:, -1:],
            (u'R1C1',),
            ('',),
            ('',),
            ('',),
            ('',)
            )
        self._check(
            self.view[:-4, :-1],
            (u'R0C0', ),
            (u'R1C0', ),
            )

    def test_slice_string_ranges(self):
        self._check(
            self.view[Row(1):Row(2), Col('A'):Col('B')],
            (u'R0C0', u'R0C1'),
            (u'R1C0', u'R1C1'),
            )

class CheckerViewTests(TestCase):
        
    def test_matches(self):
        CheckerView(path.join(test_files,'testall.xls'))['Sheet1'].compare(
            (u'R0C0', u'R0C1'),
            (u'R1C0', u'R1C1'),
            (u'A merged cell', ''),
            ('', ''),
            ('', ''),
            (u'More merged cells', '')
            )

        
    def test_does_not_match(self):
        with ShouldRaise(AssertionError('''\
Sequence not as expected:

same:
((u'R0C0', u'R0C1'),
 (u'R1C0', u'R1C1'),
 (u'A merged cell', ''),
 ('', ''),
 ('', ''))

first:
((u'More merged cells', 'XX'),)

second:
((u'More merged cells', ''),)''')):
            CheckerView(path.join(test_files,'testall.xls'))['Sheet1'].compare(
                (u'R0C0', u'R0C1'),
                (u'R1C0', u'R1C1'),
                (u'A merged cell', ''),
                ('', ''),
                ('', ''),
                (u'More merged cells', 'XX')
                )

########NEW FILE########
__FILENAME__ = view
# Copyright (c) 2013 Simplistix Ltd
#
# This Software is released under the MIT License:
# http://www.opensource.org/licenses/mit-license.html
# See license.txt for more details.

from datetime import datetime, time
from xlrd import open_workbook, XL_CELL_DATE, xldate_as_tuple
from xlwt.Utils import col_by_name

class Index(object):
    def __init__(self, name):
        self.name = name
        
class Row(Index):
    """
    A one-based, end-inclusive row index for use in slices,
    eg:: ``[Row(1):Row(2), :]``
    """
    def __index__(self):
        return int(self.name) - 1
    
class Col(Index):
    """
    An end-inclusive column label index for use in slices,
    eg: ``[:, Col('A'), Col('B')]``
    """
    def __index__(self):
        return col_by_name(self.name)
    
class SheetView(object):
    """
    A view on a sheet in a workbook. Should be created by indexing a
    :class:`View`.
    
    These can be sliced to create smaller views.
    
    Views can be iterated over to return a set of iterables, one for each row
    in the view. Data is returned as in the cell values with the exception of
    dates and times which are converted into :class:`~datetime.datetime`
    instances.
    """
    def __init__(self, book, sheet, row_slice=None, col_slice=None):
        #: The workbook used by this view.
        self.book = book
        #: The sheet in the workbook used by this view.
        self.sheet = sheet
        for name, source in (('rows', row_slice), ('cols', col_slice)):
            start = 0
            stop = max_n = getattr(self.sheet, 'n'+name)
            if isinstance(source, slice):
                if source.start is not None:
                    start_val = source.start
                    if isinstance(start_val, Index):
                        start_val = start_val.__index__()
                    if start_val <  0:
                        start = max(0, max_n + start_val)
                    elif start_val > 0:
                        start = min(max_n, start_val)
                if source.stop is not None:
                    stop_val = source.stop
                    if isinstance(stop_val, Index):
                        stop_val = stop_val.__index__() + 1
                    if stop_val <  0:
                        stop = max(0, max_n + stop_val)
                    elif stop_val > 0:
                        stop = min(max_n, stop_val)
            setattr(self, name, xrange(start, stop))

    def __row(self, rowx):
        for colx in self.cols:
            value = self.sheet.cell_value(rowx, colx)
            if self.sheet.cell_type(rowx, colx) == XL_CELL_DATE:
                date_parts = xldate_as_tuple(value, self.book.datemode)
                # Times come out with a year of 0.
                if date_parts[0]:
                    value = datetime(*date_parts)
                else:
                    value = time(*date_parts[3:])
            yield value
            
    def __iter__(self):
        for rowx in self.rows:
            yield self.__row(rowx)

    def __getitem__(self, slices):
        assert isinstance(slices, tuple)
        assert len(slices)==2
        return self.__class__(self.book, self.sheet, *slices)
        

class View(object):
    """
    A view wrapper around a :class:`~xlrd.Book` that allows for easy
    iteration over the data in a group of cells.

    :param path: The path of the .xls from which to create views.
    :param class_: An class to use instead of :class:`SheetView` for views of sheets.
    """

    #: This can be replaced in a sub-class to use something other than
    #: :class:`SheetView` for the views of sheets returned.
    class_ = SheetView

    def __init__(self, path, class_=None):
        self.class_ = class_ or self.class_
        self.book = open_workbook(path, formatting_info=1, on_demand=True)

    def __getitem__(self, item):
        """
        Returns of a view of a sheet in the workbook this view is created for.
        
        :param item: either zero-based integer index or a sheet name.
        """
        if isinstance(item, int):
            sheet = self.book.sheet_by_index(item)
        else:
            sheet = self.book.sheet_by_name(item)
        return self.class_(self.book, sheet)

class CheckSheet(SheetView):
    """
    A special sheet view for use in automated tests.
    """
    
    def compare(self, *expected):
        """
        Call to check whether this view contains the expected data.
        If it does not, a descriptive :class:`AssertionError` will
        be raised. Requires
        `testfixtures <http://www.simplistix.co.uk/software/python/testfixtures>`__.

        :param expected: tuples containing the data that should be
                         present in this view.
        """
        actual = []
        for row in self:
            actual.append(tuple(row))

        # late import in case testfixtures isn't around!
        from testfixtures import compare as _compare
        _compare(expected, tuple(actual))

class CheckerView(View):
    """
    A special subclass of :class:`View` for use in automated tests when you
    want to check the contents of a generated spreadsheet.

    Views of sheets are returned as :class:`CheckSheet` instances which have a
    handy :meth:`~CheckSheet.compare` method.
    """
    class_ = CheckSheet

########NEW FILE########
