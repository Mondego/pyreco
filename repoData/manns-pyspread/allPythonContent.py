__FILENAME__ = macrotest2
def f(x):
	return x*x
########NEW FILE########
__FILENAME__ = macro_chart

import guidata
from guiqwt.plot import CurveDialog
from guiqwt.builder import make

_app = guidata.qapplication()

def hist(data):
	"""Plots histogram"""
	
	win = CurveDialog(edit=False, toolbar=True, wintitle="Histogram test")
	plot = win.get_plot()
	plot.add_item(make.histogram(data))
	win.show()
	win.exec_()
########NEW FILE########
__FILENAME__ = macro_draw
import wx
def draw_rect(grid, attr, dc, rect):
	"""Draws a rect"""
	dc.SetBrush(wx.Brush(wx.Colour(15, 255, 127), wx.SOLID))
	dc.SetPen(wx.Pen(wx.BLUE, 1, wx.SOLID))
	dc.DrawRectangleRect(rect)
def draw_bmp(bmp_filepath):
	"""Draws bitmap"""
	def draw(grid, attr, dc, rect):
		bmp = wx.EmptyBitmap(100, 100)
		try:
			dummy = open(bmp_filepath)
			dummy.close()
			bmp.LoadFile(bmp_filepath, wx.BITMAP_TYPE_ANY)
			dc.DrawBitmap(bmp, 0, 0)
		except:
			return
	return draw
def draw(draw_func):
	"""Executes the draw function"""
	return draw_func

########NEW FILE########
__FILENAME__ = macro_equation

def eq(code, **kwargs):
	from matplotlib.figure import Figure
	if "horizontalalignment" not in kwargs:
		kwargs["horizontalalignment"] = "center"
	if "verticalalignment" not in kwargs:
		kwargs["verticalalignment"] = "center"
	f = Figure(frameon=False)
	f.text(0.5, 0.5, code, **kwargs)
	return f
########NEW FILE########
__FILENAME__ = macrotest2
def f(x):
	return x*x
########NEW FILE########
__FILENAME__ = test_grid_actions
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------


"""
test_grid_actions
=================

Unit tests for _grid_actions.py

"""

import os
import sys

import bz2
import wx
app = wx.App()

TESTPATH = os.sep.join(os.path.realpath(__file__).split(os.sep)[:-1]) + os.sep
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 3)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 2)

from src.gui._main_window import MainWindow
from src.lib.selection import Selection

from src.lib.testlib import params, pytest_generate_tests
from src.lib.testlib import basic_setup_test, restore_basic_grid

from src.gui._events import *


class TestFileActions(object):
    """File actions test class"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, title="pyspread", S=None)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

        # Filenames
        # ---------

        # File with valid signature
        self.filename_valid_sig = TESTPATH + "test1.pys"
        self.grid.actions.sign_file(self.filename_valid_sig)

        # File without signature
        self.filename_no_sig = TESTPATH + "test2.pys"

        # File with invalid signature
        self.filename_invalid_sig = TESTPATH + "test3.pys"

        # File for self.grid size test
        self.filename_gridsize = TESTPATH + "test4.pys"
        self.grid.actions.sign_file(self.filename_gridsize)

        # Empty file
        self.filename_empty = TESTPATH + "test5.pys"

        # File name that cannot be accessed
        self.filename_not_permitted = TESTPATH + "test6.pys"

        # File name without file
        self.filename_wrong = TESTPATH + "test-1.pys"

        # File for testing save
        self.filename_save = TESTPATH + "test_save.pys"

    def test_validate_signature(self):
        """Tests signature validation"""

        # Test missing sig file
        assert not self.grid.actions.validate_signature(self.filename_no_sig)

        # Test valid sig file
        assert self.grid.actions.validate_signature(self.filename_valid_sig)

        # Test invalid sig file
        assert not \
            self.grid.actions.validate_signature(self.filename_invalid_sig)

    def test_enter_safe_mode(self):
        """Tests safe mode entry"""

        self.grid.actions.leave_safe_mode()
        self.grid.actions.enter_safe_mode()
        assert self.grid.code_array.safe_mode

    def test_leave_safe_mode(self):
        """Tests save mode exit"""

        self.grid.actions.enter_safe_mode()
        self.grid.actions.leave_safe_mode()
        assert not self.grid.code_array.safe_mode

    def test_approve(self):

        # Test if safe_mode is correctly set for invalid sig
        self.grid.actions.approve(self.filename_invalid_sig)

        assert self.grid.GetTable().data_array.safe_mode

        # Test if safe_mode is correctly set for valid sig

        self.grid.actions.approve(self.filename_valid_sig)

        assert not self.grid.GetTable().data_array.safe_mode

        # Test if safe_mode is correctly set for missing sig
        self.grid.actions.approve(self.filename_no_sig)

        assert self.grid.GetTable().data_array.safe_mode

        # Test if safe_mode is correctly set for io-error sig

        os.chmod(self.filename_not_permitted, 0200)
        os.chmod(self.filename_not_permitted + ".sig", 0200)

        self.grid.actions.approve(self.filename_not_permitted)

        assert self.grid.GetTable().data_array.safe_mode

        os.chmod(self.filename_not_permitted, 0644)
        os.chmod(self.filename_not_permitted + ".sig", 0644)

    def test_clear_globals_reload_modules(self):
        """Tests clear_globals_reload_modules"""

        self.grid.code_array[(0, 0, 0)] = "'Test1'"
        self.grid.code_array[(0, 0, 0)]
        assert self.grid.code_array.result_cache

        self.grid.actions.clear_globals_reload_modules()
        assert not self.grid.code_array.result_cache

    def test_get_file_version(self):
        """Tests infile version string."""

        infile = bz2.BZ2File(self.filename_valid_sig)
        version = self.grid.actions._get_file_version(infile)
        assert version == "0.1"
        infile.close()

    def test_clear(self):
        """Tests empty_grid method"""

        # Set up self.grid

        self.grid.code_array[(0, 0, 0)] = "'Test1'"
        self.grid.code_array[(3, 1, 1)] = "'Test2'"

        self.grid.actions.set_col_width(1, 23)
        self.grid.actions.set_col_width(0, 233)
        self.grid.actions.set_row_height(0, 0)

        selection = Selection([], [], [], [], [(0, 0)])
        self.grid.actions.set_attr("bgcolor", wx.RED, selection)
        self.grid.actions.set_attr("frozen", "print 'Testcode'", selection)

        # Clear self.grid

        self.grid.actions.clear()

        # Code content

        assert self.grid.code_array((0, 0, 0)) is None
        assert self.grid.code_array((3, 1, 1)) is None

        assert list(self.grid.code_array[:2, 0, 0]) == [None, None]

        # Cell attributes
        cell_attributes = self.grid.code_array.cell_attributes
        assert cell_attributes == []

        # Row heights and column widths

        row_heights = self.grid.code_array.row_heights
        assert len(row_heights) == 0

        col_widths = self.grid.code_array.col_widths
        assert len(col_widths) == 0

        # Undo and redo
        undolist = self.grid.code_array.unredo.undolist
        redolist = self.grid.code_array.unredo.redolist
        assert undolist == []
        assert redolist == []

        # Caches

        # Clear self.grid again because lookup is added in resultcache

        self.grid.actions.clear()

        result_cache = self.grid.code_array.result_cache
        assert len(result_cache) == 0

    def test_open(self):
        """Tests open functionality"""

        class Event(object):
            attr = {}
        event = Event()

        # Test missing file
        event.attr["filepath"] = self.filename_wrong

        assert not self.grid.actions.open(event)

        # Test unaccessible file
        os.chmod(self.filename_not_permitted, 0200)
        event.attr["filepath"] = self.filename_not_permitted
        assert not self.grid.actions.open(event)

        os.chmod(self.filename_not_permitted, 0644)

        # Test empty file
        event.attr["filepath"] = self.filename_empty
        assert not self.grid.actions.open(event)

        assert self.grid.GetTable().data_array.safe_mode  # sig is also empty

        # Test invalid sig files
        event.attr["filepath"] = self.filename_invalid_sig
        self.grid.actions.open(event)

        assert self.grid.GetTable().data_array.safe_mode

        # Test file with sig
        event.attr["filepath"] = self.filename_valid_sig
        self.grid.actions.open(event)

        assert not self.grid.GetTable().data_array.safe_mode

        # Test file without sig
        event.attr["filepath"] = self.filename_no_sig
        self.grid.actions.open(event)

        assert self.grid.GetTable().data_array.safe_mode

        # Test self.grid size for valid file
        event.attr["filepath"] = self.filename_gridsize
        self.grid.actions.open(event)

        new_shape = self.grid.GetTable().data_array.shape
        assert new_shape == (1000, 100, 10)

        # Test self.grid content for valid file
        assert not self.grid.code_array.safe_mode
        assert self.grid.GetTable().data_array[0, 0, 0] == "test4"

    def test_save(self):
        """Tests save functionality"""

        class Event(object):
            attr = {}
        event = Event()

        # Test normal save
        event.attr["filepath"] = self.filename_save

        self.grid.actions.save(event)

        savefile = open(self.filename_save)

        assert savefile
        savefile.close()

        # Test double filename

        self.grid.actions.save(event)

        # Test io error

        os.chmod(self.filename_save, 0200)
        try:
            self.grid.actions.save(event)
            raise IOError("No error raised even though target not writable")
        except IOError:
            pass
        os.chmod(self.filename_save, 0644)

        # Test invalid file name

        event.attr["filepath"] = None
        try:
            self.grid.actions.save(event)
            raise TypeError("None accepted as filename")
        except TypeError:
            pass

        # Test sig creation is happening

        sigfile = open(self.filename_save + ".sig")
        assert sigfile
        sigfile.close()

        os.remove(self.filename_save)
        os.remove(self.filename_save + ".sig")

    def test_sign_file(self):
        """Tests signing functionality"""

        try:
            os.remove(self.filename_valid_sig + ".sig")
        except OSError:
            pass
        self.grid.actions.sign_file(self.filename_valid_sig)
        dirlist = os.listdir(TESTPATH)

        filepath = self.filename_valid_sig + ".sig"
        filename = filepath[len(TESTPATH):]

        assert filename in dirlist


class TestTableRowActionsMixins(object):
    """Unit test class for TableRowActionsMixins"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    param_set_row_height = [
        {'row': 0, 'tab': 0, 'height': 0},
        {'row': 0, 'tab': 1, 'height': 0},
        {'row': 0, 'tab': 0, 'height': 34},
        {'row': 10, 'tab': 12, 'height': 3245.78},
    ]

    @params(param_set_row_height)
    def test_set_row_height(self, row, tab, height):
        self.grid.current_table = tab
        self.grid.actions.set_row_height(row, height)
        row_heights = self.grid.code_array.row_heights
        assert row_heights[row, tab] == height

    param_insert_rows = [
        {'row': -1, 'no_rows': 0, 'test_key': (0, 0, 0), 'test_val': "'Test'"},
        {'row': -1, 'no_rows': 1, 'test_key': (0, 0, 0), 'test_val': None},
        {'row': -1, 'no_rows': 1, 'test_key': (1, 0, 0), 'test_val': "'Test'"},
        {'row': -1, 'no_rows': 5, 'test_key': (5, 0, 0), 'test_val': "'Test'"},
        {'row': 1, 'no_rows': 1, 'test_key': (0, 0, 0), 'test_val': "'Test'"},
        {'row': 1, 'no_rows': 1, 'test_key': (1, 0, 0), 'test_val': None},
        {'row': -1, 'no_rows': 1, 'test_key': (2, 1, 0), 'test_val': "3"},
        {'row': 0, 'no_rows': 500, 'test_key': (501, 1, 0), 'test_val': "3"},
    ]

    @params(param_insert_rows)
    def test_insert_rows(self, row, no_rows, test_key, test_val):
        """Tests insertion action for rows"""

        basic_setup_test(self.grid, self.grid.actions.insert_rows, test_key,
                         test_val, row, no_rows=no_rows)

    param_delete_rows = [
        {'row': 0, 'no_rows': 0, 'test_key': (0, 0, 0), 'test_val': "'Test'"},
        {'row': 0, 'no_rows': 1, 'test_key': (0, 0, 0), 'test_val': None},
        {'row': 0, 'no_rows': 1, 'test_key': (0, 1, 0), 'test_val': "3"},
        {'row': 0, 'no_rows': 995, 'test_key': (4, 99, 0),
         'test_val': "$^%&$^"},
        {'row': 1, 'no_rows': 1, 'test_key': (0, 1, 0), 'test_val': "1"},
        {'row': 1, 'no_rows': 1, 'test_key': (1, 1, 0), 'test_val': None},
        {'row': 1, 'no_rows': 999, 'test_key': (0, 0, 0),
         'test_val': "'Test'"},
    ]

    @params(param_delete_rows)
    def test_delete_rows(self, row, no_rows, test_key, test_val):
        """Tests deletion action for rows"""

        basic_setup_test(self.grid, self.grid.actions.delete_rows, test_key,
                         test_val, row, no_rows=no_rows)


class TestTableColumnActionsMixin(object):
    """Unit test class for TableColumnActionsMixin"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    param_set_col_width = [
        {'col': 0, 'tab': 0, 'width': 0},
        {'col': 0, 'tab': 1, 'width': 0},
        {'col': 0, 'tab': 0, 'width': 34},
        {'col': 10, 'tab': 12, 'width': 3245.78},
    ]

    @params(param_set_col_width)
    def test_set_col_width(self, col, tab, width):
        self.grid.current_table = tab
        self.grid.actions.set_col_width(col, width)
        col_widths = self.grid.code_array.col_widths
        assert col_widths[col, tab] == width

    param_set_col_width_selection = [
        {'cursorCol': 1, 'tab': 0, 'width': 7,
         'cols': [0, 1, 2], 'fullboxes': [], 'partialboxes': []},
        {'cursorCol': 1, 'tab': 0, 'width': 8,
         'cols': [], 'fullboxes': [0, 1, 2], 'partialboxes': []},
        {'cursorCol': 1, 'tab': 0, 'width': 9,
         'cols': [], 'fullboxes': [], 'partialboxes': [0, 1, 2]},
        {'cursorCol': 7, 'tab': 0, 'width': 10,
         'cols': [0, 1, 2], 'fullboxes': [], 'partialboxes': []},
        {'cursorCol': 7, 'tab': 0, 'width': 11,
         'cols': [], 'fullboxes': [0, 1, 2], 'partialboxes': []},
        {'cursorCol': 7, 'tab': 0, 'width': 12,
         'cols': [], 'fullboxes': [], 'partialboxes': [0, 1, 2]},
        {'cursorCol': 1, 'tab': 1, 'width': 13,
         'cols': [], 'fullboxes': [], 'partialboxes': []},
        {'cursorCol': 1, 'tab': 1, 'width': 13,
         'cols': [0, 1], 'fullboxes': [2, 3], 'partialboxes': [4, 5]},
        {'cursorCol': 1, 'tab': 1, 'width': 14,
         'cols': [0, 1], 'fullboxes': [2, 3], 'partialboxes': [3, 4]},
        {'cursorCol': 1, 'tab': 1, 'width': 14,
         'cols': [0, 1], 'fullboxes': [1, 2], 'partialboxes': [3, 4]},
        {'cursorCol': 1, 'tab': 1, 'width': 15,
         'cols': [0, 1], 'fullboxes': [2, 3], 'partialboxes': [4, 5]},
        {'cursorCol': 1, 'tab': 1, 'width': 1,
         'cols': [0, 1], 'fullboxes': [2, 3], 'partialboxes': [4, 5]},
    ]

    @params(param_set_col_width_selection)
    def test_set_col_width_selection(self, cursorCol, cols, fullboxes,
                                     partialboxes, tab, width):
        """
        cursorCol: Column user was dragging when trying resize multiple
        cols: Full columns selected to be edited
        fullboxes: Columns which are fully selected via a box in the selection
        partialboxes: Columns which are part of a selection, but do
                    do not include the full columns.
        tab: Current table
        width: Desired new width for all columns
        To run: In this directory !python -m pytest -k test_set_col_width_s
        """
        class event_test_harness(object):
            def __init__(self, cursorCol):
                self.cursorCol = cursorCol

            def GetRowOrCol(self):
                return self.cursorCol

            def Skip(self):
                pass

        # Setup For Test
        max_rows = self.grid.code_array.shape[0] - 1
        event = event_test_harness(cursorCol)
        self.grid.current_table = tab
        self.grid.ClearSelection()
        for col in cols:
            self.grid.SelectCol(col, addToSelected=True)
        for col in fullboxes:
            self.grid.SelectBlock(0, col, max_rows, col, addToSelected=True)
        for col in partialboxes:
            self.grid.SelectBlock(0, col, max_rows-1, col, addToSelected=True)

        # Perform test
        self.grid.actions.set_col_width(cursorCol, width)
        self.grid.handlers.OnColSize(event)

        # Check results -- Cursor col should always be resized
        col_widths = self.grid.code_array.col_widths
        assert col_widths[cursorCol, tab] == width

        # Check results -- Full selected columns
        for col in cols:
            assert col_widths[col, tab] == width

        # Check results -- Boxes of full columns selected
        for col in fullboxes:
            assert col_widths[col, tab] == width

        # Check results -- Boxes of full columns selected
        for col in partialboxes:
            if col != cursorCol and col not in fullboxes:
                assert col_widths.get((col, tab), -1) != width

    param_insert_cols = [
        {'col': -1, 'no_cols': 0, 'test_key': (0, 0, 0), 'test_val': "'Test'"},
        {'col': -1, 'no_cols': 1, 'test_key': (0, 0, 0), 'test_val': None},
        {'col': -1, 'no_cols': 1, 'test_key': (0, 1, 0), 'test_val': "'Test'"},
        {'col': -1, 'no_cols': 5, 'test_key': (0, 5, 0), 'test_val': "'Test'"},
        {'col': 0, 'no_cols': 1, 'test_key': (0, 0, 0), 'test_val': "'Test'"},
        {'col': 0, 'no_cols': 1, 'test_key': (0, 1, 0), 'test_val': None},
        {'col': 0, 'no_cols': 1, 'test_key': (1, 2, 0), 'test_val': "3"},
    ]

    @params(param_insert_cols)
    def test_insert_cols(self, col, no_cols, test_key, test_val):
        """Tests insertion action for columns"""

        basic_setup_test(self.grid, self.grid.actions.insert_cols, test_key,
                         test_val, col, no_cols=no_cols)

    param_delete_cols = [
        {'col': -1, 'no_cols': 0, 'test_key': (0, 0, 0), 'test_val': "'Test'"},
        {'col': -1, 'no_cols': 1, 'test_key': (0, 2, 0), 'test_val': None},
        {'col': -1, 'no_cols': 1, 'test_key': (0, 1, 0), 'test_val': "2"},
        {'col': -1, 'no_cols': 95, 'test_key': (999, 4, 0),
         'test_val': "$^%&$^"},
        {'col': 0, 'no_cols': 1, 'test_key': (0, 1, 0), 'test_val': "2"},
        {'col': 0, 'no_cols': 1, 'test_key': (1, 1, 0), 'test_val': "4"},
        {'col': 1, 'no_cols': 99, 'test_key': (0, 0, 0),
         'test_val': "'Test'"},
    ]

    @params(param_delete_cols)
    def test_delete_cols(self, col, no_cols, test_key, test_val):
        """Tests deletion action for columns"""

        basic_setup_test(self.grid, self.grid.actions.delete_cols, test_key,
                         test_val, col, no_cols=no_cols)


class TestTableTabActionsMixin(object):
    """Unit test class for TableTabActionsMixin"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    param_insert_tabs = [
        {'tab': -1, 'no_tabs': 0, 'test_key': (0, 0, 0), 'test_val': "'Test'"},
        {'tab': -1, 'no_tabs': 1, 'test_key': (0, 0, 0), 'test_val': None},
        {'tab': -1, 'no_tabs': 1, 'test_key': (0, 0, 1), 'test_val': "'Test'"},
        {'tab': -1, 'no_tabs': 2, 'test_key': (0, 0, 2), 'test_val': "'Test'"},
        {'tab': 0, 'no_tabs': 1, 'test_key': (0, 0, 0), 'test_val': "'Test'"},
        {'tab': 0, 'no_tabs': 1, 'test_key': (0, 0, 1), 'test_val': None},
    ]

    @params(param_insert_tabs)
    def test_insert_tabs(self, tab, no_tabs, test_key, test_val):
        """Tests insertion action for tabs"""

        basic_setup_test(self.grid, self.grid.actions.insert_tabs, test_key,
                         test_val, tab, no_tabs=no_tabs)

    param_delete_tabs = [
        {'tab': 0, 'no_tabs': 0, 'test_key': (0, 0, 0), 'test_val': "'Test'"},
        {'tab': 0, 'no_tabs': 1, 'test_key': (0, 2, 0), 'test_val': None},
        {'tab': 0, 'no_tabs': 1, 'test_key': (1, 2, 1), 'test_val': "78"},
        {'tab': 2, 'no_tabs': 1, 'test_key': (1, 2, 1), 'test_val': None},
        {'tab': 1, 'no_tabs': 1, 'test_key': (1, 2, 1), 'test_val': "78"},
        {'tab': 0, 'no_tabs': 2, 'test_key': (1, 2, 0), 'test_val': "78"},
    ]

    @params(param_delete_tabs)
    def test_delete_tabs(self, tab, no_tabs, test_key, test_val):
        """Tests deletion action for tabs"""

        basic_setup_test(self.grid, self.grid.actions.delete_tabs, test_key,
                         test_val, tab, no_tabs=no_tabs)


class TestTableActions(object):
    """Unit test class for TableActions"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    param_paste = [
        {'tl_cell': (0, 0, 0), 'data': [["78"]],
         'test_key': (0, 0, 0), 'test_val': "78"},
        {'tl_cell': (40, 0, 0), 'data': [[None]],
         'test_key': (40, 0, 0), 'test_val': None},
        {'tl_cell': (0, 0, 0), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (0, 0, 0), 'test_val': "1"},
        {'tl_cell': (0, 0, 0), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (1, 1, 0), 'test_val': "4"},
        {'tl_cell': (0, 0, 0), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (1, 1, 1), 'test_val': None},
        {'tl_cell': (41, 0, 0), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (40, 0, 0), 'test_val': None},
        {'tl_cell': (1, 0, 0), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (1, 0, 0), 'test_val': "1"},
        {'tl_cell': (40, 1, 0), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (40, 1, 0), 'test_val': "1"},
        {'tl_cell': (40, 1, 0), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (40, 0, 0), 'test_val': None},
        {'tl_cell': (123, 5, 0), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (123, 6, 0), 'test_val': "2"},
        {'tl_cell': (1, 1, 2), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (1, 1, 2), 'test_val': "1"},
        {'tl_cell': (1, 1, 2), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (2, 1, 2), 'test_val': "3"},
        {'tl_cell': (999, 0, 0), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (999, 0, 0), 'test_val': "1"},
        {'tl_cell': (999, 99, 2), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (999, 99, 2), 'test_val': "1"},
        {'tl_cell': (999, 98, 2), 'data': [["1", "2"], ["3", "4"]],
         'test_key': (999, 99, 2), 'test_val': "2"},
    ]

    @params(param_paste)
    def test_paste(self, tl_cell, data, test_key, test_val):
        """Tests paste into self.grid"""

        basic_setup_test(self.grid, self.grid.actions.paste, test_key,
                         test_val, tl_cell, data)

    param_change_grid_shape = [
        {'shape': (1, 1, 1)},
        {'shape': (2, 1, 3)},
        {'shape': (1, 1, 40)},
        {'shape': (1000, 100, 3)},
        {'shape': (80000000, 80000000, 80000000)},
    ]

    @params(param_change_grid_shape)
    def test_change_grid_shape(self, shape):
        """Tests action for changing the self.grid shape"""

        self.grid.actions.clear()

        self.grid.actions.change_grid_shape(shape)

        res_shape = self.grid.code_array.shape
        assert res_shape == shape

        br_key = tuple(dim - 1 for dim in shape)
        assert self.grid.code_array(br_key) is None

    param_replace_cells = [
        {'key': (0, 0, 0), 'sorted_row_idxs': [1, 0, 2, 3, 4, 5, 6, 7, 8, 9],
         'res_key': (0, 0, 0), 'res': "3"},
        {'key': (0, 0, 0), 'sorted_row_idxs': [1, 0, 2, 3, 4, 5, 6, 7, 8, 9],
         'res_key': (1, 0, 0), 'res': "1"},
        {'key': (0, 0, 0), 'sorted_row_idxs': [1, 0, 2, 3, 4, 5, 6, 7, 8, 9],
         'res_key': (2, 0, 0), 'res': "45"},
        {'key': (0, 0, 0), 'sorted_row_idxs': [1, 0, 2, 3, 4, 5, 6, 7, 8, 9],
         'res_key': (9, 0, 0), 'res': '33'},
        {'key': (0, 0, 0), 'sorted_row_idxs': [1, 0, 2, 3, 4, 5, 6, 7, 8, 9],
         'res_key': (3, 0, 1), 'res': "1"},
        {'key': (5, 1, 0), 'sorted_row_idxs': [0, 5, 2, 3, 4, 5, 6, 1, 8, 9],
         'res_key': (1, 1, 0), 'res': "3.2"},
        {'key': (0, 0, 0), 'sorted_row_idxs': [0, 5, 2, 3, 4, 5, 6, 1, 8, 9],
         'res_key': (5, 1, 0), 'res': None},
        {'key': (0, 2, 0), 'sorted_row_idxs': [1, 0, 2, 3, 4, 5, 9, 7, 8, 6],
         'res_key': (9, 2, 0), 'res': "1j"},
    ]

    @params(param_replace_cells)
    def test_replace_cells(self, key, sorted_row_idxs, res_key, res):
        """Tests replace_cells method"""

        self.grid.actions.change_grid_shape((10, 3, 2))

        data = {
            (0, 0, 0): "1",
            (1, 0, 0): "3",
            (2, 0, 0): "45",
            (9, 0, 0): "33",
            (3, 1, 0): "'Test'",
            (5, 1, 0): "3.2",
            (6, 2, 0): "1j",
            (3, 0, 1): "1",
        }
        for __key in data:
            self.grid.code_array[__key] = data[__key]

        self.grid.actions.replace_cells(key, sorted_row_idxs)

        assert self.grid.code_array(res_key) == res

    param_sort_ascending = [
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], []),
         'res_key': (0, 0, 0), 'res': "1"},
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], []),
         'res_key': (2, 0, 0), 'res': "33"},
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], []),
         'res_key': (3, 0, 0), 'res': "45"},
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], []),
         'res_key': (4, 0, 0), 'res': None},
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], []),
         'res_key': (3, 1, 0), 'res': "'Test'"},
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], [(1, 1)]),
         'res_key': (2, 0, 0), 'res': "45"},
    ]

    @params(param_sort_ascending)
    def test_sort_ascending(self, key, selection, res_key, res):
        """Tests sort_ascending method"""

        self.grid.actions.change_grid_shape((10, 3, 2))

        data = {
            (0, 0, 0): "1",
            (1, 0, 0): "3",
            (2, 0, 0): "45",
            (9, 0, 0): "33",
            (2, 1, 0): "'Test'",
            (5, 1, 0): "3.2",
            (6, 2, 0): "1j",
            (3, 0, 1): "1",
        }

        for __key in data:
            self.grid.code_array[__key] = data[__key]


        selection.grid_select(self.grid)

        try:
            self.grid.actions.sort_ascending(key)
            assert self.grid.code_array(res_key) == res

        except TypeError:
            assert res == 'fail'

    param_sort_descending = [
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], []),
         'res_key': (0, 0, 0), 'res': "45"},
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], []),
         'res_key': (2, 0, 0), 'res': "3"},
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], []),
         'res_key': (3, 0, 0), 'res': "1"},
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], []),
         'res_key': (4, 0, 0), 'res': None},
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], []),
         'res_key': (0, 1, 0), 'res': "'Test'"},
        {'key': (0, 0, 0), 'selection': Selection([], [], [], [], [(1, 1)]),
         'res_key': (2, 0, 0), 'res': "45"},
    ]

    @params(param_sort_descending)
    def test_sort_descending(self, key, selection, res_key, res):
        """Tests sort_descending method"""

        self.grid.actions.change_grid_shape((10, 3, 2))

        data = {
            (0, 0, 0): "1",
            (1, 0, 0): "3",
            (2, 0, 0): "45",
            (9, 0, 0): "33",
            (2, 1, 0): "'Test'",
            (5, 1, 0): "3.2",
            (6, 2, 0): "1j",
            (3, 0, 1): "1",
        }

        for __key in data:
            self.grid.code_array[__key] = data[__key]

        selection.grid_select(self.grid)

        try:
            self.grid.actions.sort_descending(key)
            assert self.grid.code_array(res_key) == res

        except TypeError:
            assert res == 'fail'


class TestUnRedoActions(object):
    """Unit test class for undo and redo actions"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    def test_undo(self):
        """Tests undo action"""

        restore_basic_grid(self.grid)
        self.grid.actions.clear()

        self.grid.code_array[(0, 0, 0)] = "Test"

        self.grid.actions.undo()

        assert self.grid.code_array((0, 0, 0)) is None

    def test_redo(self):
        """Tests redo action"""

        self.test_undo()
        self.grid.actions.redo()

        assert self.grid.code_array((0, 0, 0)) == "Test"


class TestGridActions(object):
    """self.grid level self.grid actions test class"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    class Event(object):
        pass

    def test_new(self):
        """Tests creation of a new spreadsheets"""

        dims = [1, 1, 1, 10, 1, 1, 1, 10, 1, 1, 1, 10, 10, 10, 10]
        dims = zip(dims[::3], dims[1::3], dims[2::3])

        for dim in dims:
            event = self.Event()
            event.shape = dim
            self.grid.actions.new(event)
            new_shape = self.grid.GetTable().data_array.shape
            assert new_shape == dim

    param_switch_to_table = [
        {'tab': 2},
        {'tab': 0},
    ]

    @params(param_switch_to_table)
    def test_switch_to_table(self, tab):
        event = self.Event()
        event.newtable = tab
        self.grid.actions.switch_to_table(event)
        assert self.grid.current_table == tab

    param_cursor = [
        {'key': (0, 0, 0)},
        {'key': (0, 1, 2)},
        {'key': (999, 99, 1)},
    ]

    @params(param_cursor)
    def test_cursor(self, key):
        self.grid.cursor = key
        assert self.grid.cursor == key


class TestSelectionActions(object):
    """Selection actions test class"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    # No tests for
    # * get_selection
    # * select_cell
    # * select_slice
    # because of close integration with selection in GUI

    def test_delete_selection(self):
        """Tests for delete_selection"""

        self.grid.code_array[(0, 0, 0)] = "Test"
        self.grid.code_array[(0, 0, 1)] = "Not deleted"

        self.grid.actions.select_cell(0, 0)
        self.grid.actions.delete_selection()

        assert self.grid.code_array[(0, 0, 0)] is None
        assert self.grid.code_array((0, 0, 1)) == "Not deleted"

        # Make sure that the result cache is empty
        assert not self.grid.code_array.result_cache

    def test_quote_selection(self):
        """Tests for quote_selection"""

        self.grid.code_array[(1, 0, 0)] = "Q1"
        self.grid.code_array[(2, 0, 0)] = '"NQ1"'

        self.grid.actions.select_cell(1, 0)
        self.grid.actions.select_cell(2, 0, add_to_selected=True)

        self.grid.actions.quote_selection()

        assert self.grid.code_array((1, 0, 0)) == '"Q1"'
        assert self.grid.code_array((2, 0, 0)) == '"NQ1"'

class TestFindActions(object):
    """FindActions test class"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

        # Content for find and replace operations
        grid_data = {
            (0, 0, 0): u"Test",
            (1, 0, 0): u"Test1",
            (2, 0, 0): u"Test2",
        }

        for key in grid_data:
            self.grid.code_array[key] = grid_data[key]

    # Search flags ["UP" xor "DOWN", "WHOLE_WORD", "MATCH_CASE", "REG_EXP"]

    param_find = [
        {'gridpos': [0, 0, 0], 'find_string': "test",
         'flags': ["DOWN"], 'res_key': (1, 0, 0)},
        {'gridpos': [0, 0, 0], 'find_string': "test",
         'flags': ["UP"], 'res_key': (2, 0, 0)},
        {'gridpos': [0, 0, 0], 'find_string': "test",
         'flags': ["DOWN", "MATCH_CASE"], 'res_key': None},
        {'gridpos': [1, 0, 0], 'find_string': "test",
         'flags': ["DOWN"], 'res_key': (2, 0, 0)},
        {'gridpos': [0, 0, 0], 'find_string': "Test",
         'flags': ["DOWN", "MATCH_CASE"], 'res_key': (1, 0, 0)},
        {'gridpos': [0, 0, 0], 'find_string': "Test",
         'flags': ["DOWN", "WHOLE_WORD"], 'res_key': (0, 0, 0)},
        {'gridpos': [0, 0, 0], 'find_string': "Test1",
         'flags': ["DOWN", "MATCH_CASE", "WHOLE_WORD"], 'res_key': (1, 0, 0)},
        {'gridpos': [0, 0, 0], 'find_string': "es*.2",
         'flags': ["DOWN"], 'res_key': None},
        {'gridpos': [0, 0, 0], 'find_string': "es*.2",
         'flags': ["DOWN", "REG_EXP"], 'res_key': (2, 0, 0)},
    ]

    @params(param_find)
    def test_find(self, gridpos, find_string, flags, res_key):
        """Tests for find"""

        res = self.grid.actions.find(gridpos, find_string, flags)
        assert res == res_key

    param_replace = [
        {'findpos': (0, 0, 0), 'find_string': "Test",
         'replace_string': "Hello", 'res': "Hello"},
        {'findpos': (1, 0, 0), 'find_string': "Test",
         'replace_string': "Hello", 'res': "Hello1"},
        {'findpos': (1, 0, 0), 'find_string': "est",
         'replace_string': "Hello", 'res': "THello1"},
    ]

    @params(param_replace)
    def test_replace(self, findpos, find_string, replace_string, res):
        """Tests for replace"""

        self.grid.actions.replace(findpos, find_string, replace_string)
        assert self.grid.code_array(findpos) == res


class TestAllGridActions(object):
    """AllGridActions test class"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    param_replace_bbox_none = [
        {'bbox': ((0, 0), (1, 234)), 'res': ((0, 0), (1, 234))},
        {'bbox': ((None, None), (2, 234)), 'res': ((0, 0), (2, 234))},
        {'bbox': ((None, None), (None, None)), 'res': ((0, 0), (999, 99))},
    ]

    @params(param_replace_bbox_none)
    def test_replace_bbox_none(self, bbox, res):
        """Tests for _replace_bbox_none"""

        assert res == self.grid.actions._replace_bbox_none(bbox)

########NEW FILE########
__FILENAME__ = test_grid_cell_actions
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------


"""
test_grid_cell_actions
======================

Unit tests for _grid_cell_actions.py

"""

import os
import sys

import wx
app = wx.App()

TESTPATH = os.sep.join(os.path.realpath(__file__).split(os.sep)[:-1]) + os.sep
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 3)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 2)

from src.gui._main_window import MainWindow
from src.lib.selection import Selection

from src.lib.testlib import params, pytest_generate_tests


class TestCellActions(object):
    """Cell actions test class"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, title="pyspread", S=None)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    param_set_code = [
        {'key': (0, 0, 0), 'code': "'Test'", 'result': "'Test'"},
        {'key': (0, 0, 0), 'code': "", 'result': None},
        {'key': (0, 0, 1), 'code': None, 'result': None},
        {'key': (999, 99, 2), 'code': "4", 'result': "4"},
    ]

    @params(param_set_code)
    def test_set_code(self, key, code, result):
        """Unit test for set_code"""

        self.main_window.changed_since_save = False

        self.grid.actions.set_code(key, code)

        assert self.grid.code_array(key) == result

    @params(param_set_code)
    def test_quote_code(self, key, code, result):
        """Unit test for quote_code"""

        self.grid.actions.set_code(key, code)
        self.grid.actions.quote_code(key)

        if code and code[0] not in ['"', "'"] and code[-1] not in ['"', "'"]:
            assert self.grid.code_array(key) == '"' + code + '"'
        elif code and code is not None:
            assert self.grid.code_array(key) == code

    @params(param_set_code)
    def test_delete_cell(self, key, code, result):
        """Unit test for delete_cell"""

        self.grid.actions.set_code(key, code)
        self.grid.actions.delete_cell(key)

        assert self.grid.code_array(key) is None

    param_get_reference = [
        {'cursor': (0, 0, 0), 'ref_key': (0, 0, 0), 'abs_ref': "S[0, 0, 0]",
         'rel_ref': "S[X, Y, Z]"},
        {'cursor': (0, 0, 1), 'ref_key': (0, 0, 1), 'abs_ref': "S[0, 0, 1]",
         'rel_ref': "S[X, Y, Z]"},
        {'cursor': (0, 0, 0), 'ref_key': (0, 0, 1), 'abs_ref': "S[0, 0, 1]",
         'rel_ref': "S[X, Y, Z+1]"},
        {'cursor': (9, 0, 0), 'ref_key': (0, 0, 0), 'abs_ref': "S[0, 0, 0]",
         'rel_ref': "S[X-9, Y, Z]"},
        {'cursor': (23, 2, 1), 'ref_key': (2, 2, 2), 'abs_ref': "S[2, 2, 2]",
         'rel_ref': "S[X-21, Y, Z+1]"},
    ]

    @params(param_get_reference)
    def test_get_absolute_reference(self, cursor, ref_key, abs_ref, rel_ref):
        """Unit test for _get_absolute_reference"""

        reference = self.grid.actions._get_absolute_reference(ref_key)

        assert reference == abs_ref

    @params(param_get_reference)
    def test_get_relative_reference(self, cursor, ref_key, abs_ref, rel_ref):
        """Unit test for _get_relative_reference"""

        reference = self.grid.actions._get_relative_reference(cursor, ref_key)

        assert reference == rel_ref

    @params(param_get_reference)
    def test_append_reference_code(self, cursor, ref_key, abs_ref, rel_ref):
        """Unit test for append_reference_code"""

        actions = self.grid.actions

        params = [
            # Normal initial code, absolute reference
            {'initial_code': "3 + ", 'ref_type': "absolute",
             "res": actions._get_absolute_reference(ref_key)},
            # Normal initial code, relative reference
            {'initial_code': "3 + ", 'ref_type': "relative",
             "res": actions._get_relative_reference(cursor, ref_key)},
            # Initial code with reference, absolute reference
            {'initial_code': "3 + S[2, 3, 1]", 'ref_type': "absolute",
             "res": actions._get_absolute_reference(ref_key)},
            # Initial code with reference, relative reference
            {'initial_code': "3 + S[2, 3, 1]", 'ref_type': "relative",
             "res": actions._get_relative_reference(cursor, ref_key)},
        ]

        for param in params:
            initial_code = param['initial_code']
            ref_type = param['ref_type']
            res = param['res']

            self.grid.actions.set_code(cursor, initial_code)

            result_code = \
                actions.append_reference_code(cursor, ref_key, ref_type)

            if "S[" in initial_code:
                assert result_code == initial_code[:4] + res

            else:
                assert result_code == initial_code + res

    param_set_cell_attr = [
        {'selection': Selection([], [], [], [], [(2, 5)]), 'tab': 1,
         'attr': ('bordercolor_right', wx.RED), 'testcell': (2, 5, 1)},
        {'selection': Selection([(0, 0)], [(99, 99)], [], [], []), 'tab': 0,
         'attr': ('bordercolor_right', wx.RED), 'testcell': (2, 5, 0)},
        {'selection': Selection([], [], [], [], [(2, 5)]), 'tab': 1,
         'attr': ('bordercolor_bottom', wx.BLUE), 'testcell': (2, 5, 1)},
        {'selection': Selection([], [], [], [], [(2, 5)]), 'tab': 1,
         'attr': ('bgcolor', wx.RED), 'testcell': (2, 5, 1)},
        {'selection': Selection([], [], [], [], [(2, 5)]), 'tab': 2,
         'attr': ('pointsize', 24), 'testcell': (2, 5, 2)},
    ]

    @params(param_set_cell_attr)
    def test_set_cell_attr(self, selection, tab, attr, testcell):
        """Unit test for _set_cell_attr"""

        self.main_window.changed_since_save = False

        attr = {attr[0]: attr[1]}

        self.grid.actions._set_cell_attr(selection, tab, attr)

        color = self.grid.code_array.cell_attributes[testcell][attr.keys()[0]]

        assert color == attr[attr.keys()[0]]

    def test_set_border_attr(self):
        """Unit test for set_border_attr"""

        self.grid.SelectBlock(10, 10, 20, 20)

        attr = "borderwidth"
        value = 5
        borders = ["top", "inner"]
        tests = {
            (13, 14, 0): 5,
            (53, 14, 0): 1,
        }

        self.grid.actions.set_border_attr(attr, value, borders)
        cell_attributes = self.grid.code_array.cell_attributes

        for cell in tests:
            res = cell_attributes[cell]["borderwidth_bottom"]
            assert res == tests[cell]

    def test_toggle_attr(self):
        """Unit test for toggle_attr"""

        self.grid.SelectBlock(10, 10, 20, 20)

        self.grid.actions.toggle_attr("underline")

        tests = {(13, 14, 0): True, (53, 14, 0): False}

        for cell in tests:
            res = self.grid.code_array.cell_attributes[cell]["underline"]
            assert res == tests[cell]

    param_change_frozen_attr = [
        {'cell': (0, 0, 0), 'code': None, 'result': None},
        {'cell': (0, 0, 0), 'code': "'Test'", 'result': 'Test'},
        {'cell': (2, 2, 0), 'code': "'Test'", 'result': 'Test'},
        {'cell': (2, 1, 0), 'code': "32", 'result': 32},
    ]

    @params(param_change_frozen_attr)
    def test_change_frozen_attr(self, cell, code, result):
        """Unit test for change_frozen_attr"""

        self.grid.actions.cursor = cell
        self.grid.current_table = cell[2]
        self.grid.code_array[cell] = code

        self.grid.actions.change_frozen_attr()

        res = self.grid.code_array.frozen_cache[repr(cell)]

        assert res == result

        self.grid.actions.change_frozen_attr()

        res2 = self.grid.code_array.cell_attributes[cell]["frozen"]

        assert not res2

    param_get_new_cell_attr_state = [
        {'cell': (0, 0, 0), 'attr': "fontweight",
         'before': wx.NORMAL, 'next': wx.BOLD},
        {'cell': (2, 1, 0), 'attr': "fontweight",
         'before': wx.NORMAL, 'next': wx.BOLD},
        {'cell': (2, 1, 0), 'attr': "vertical_align",
         'before': "top", 'next': "middle"},
    ]

    @params(param_get_new_cell_attr_state)
    def test_get_new_cell_attr_state(self, cell, attr, before, next):
        """Unit test for get_new_cell_attr_state"""

        self.grid.actions.cursor = cell
        self.grid.current_table = cell[2]

        selection = Selection([], [], [], [], [cell[:2]])
        self.grid.actions.set_attr(attr, before, selection)

        res = self.grid.actions.get_new_cell_attr_state(cell, attr)

        assert res == next

    param_get_new_selection_attr_state = [
        {'selection': Selection([], [], [], [], [(0, 0)]), 'cell': (0, 0, 0),
         'attr': "fontweight", 'before': wx.NORMAL, 'next': wx.BOLD},
        {'selection': Selection([], [], [], [], [(2, 1)]), 'cell': (2, 1, 0),
         'attr': "fontweight", 'before': wx.NORMAL, 'next': wx.BOLD},
        {'selection': Selection([], [], [], [], [(2, 1)]), 'cell': (2, 1, 0),
         'attr': "fontweight", 'before': wx.BOLD, 'next': wx.NORMAL},
        {'selection': Selection([], [], [], [], [(2, 1)]), 'cell': (2, 1, 0),
         'attr': "vertical_align", 'before': "top", 'next': "middle"},
        {'selection': Selection([(1, 0)], [(23, 2)], [], [], []),
         'cell': (2, 1, 0),
         'attr': "vertical_align", 'before': "top", 'next': "middle"},
    ]

    @params(param_get_new_selection_attr_state)
    def test_get_new_selection_attr_state(self, cell, selection, attr,
                                          before, next):
        """Unit test for get_new_selection_attr_state"""

        self.grid.actions.cursor = cell
        self.grid.current_table = cell[2]

        self.grid.actions.set_attr(attr, before, selection)

        res = self.grid.actions.get_new_selection_attr_state(selection, attr)

        assert res == next

    def test_refresh_selected_frozen_cells(self):
        """Unit test for refresh_selected_frozen_cells"""

        cell = (0, 0, 0)

        code1 = "1"
        code2 = "2"

        self.grid.actions.cursor = cell

        # Fill cell
        self.grid.code_array[cell] = code1

        assert self.grid.code_array[cell] == 1

        # Freeze cell
        self.grid.actions.cursor = cell
        self.grid.current_table = cell[2]
        self.grid.actions.change_frozen_attr()

        res = self.grid.code_array.frozen_cache[repr(cell)]
        assert res == eval(code1)

        # Change cell code
        self.grid.code_array[cell] = code2
        assert self.grid.code_array[cell] == 1

        # Refresh cell
        selection = Selection([], [], [], [], [cell[:2]])
        self.grid.actions.refresh_selected_frozen_cells(selection=selection)
        assert self.grid.code_array[cell] == 2

########NEW FILE########
__FILENAME__ = test_main_window_actions
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------


"""
test_self.main_window_actions.py
===========================

Unit tests for _self.main_window_actions.py

"""

import csv
import os
import sys

import wx
app = wx.App()

TESTPATH = os.sep.join(os.path.realpath(__file__).split(os.sep)[:-1]) + os.sep
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 3)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 2)

from src.gui._main_window import MainWindow
from src.lib.selection import Selection
from src.lib.testlib import grid_values, restore_basic_grid
from src.lib.testlib import params, pytest_generate_tests, basic_setup_test

from src.actions._main_window_actions import CsvInterface, TxtGenerator


class TestCsvInterface(object):
    def setup_method(self, method):
        self.main_window = MainWindow(None, title="pyspread", S=None)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

        self.test_filename = TESTPATH + "test.csv"
        self.test_filename2 = TESTPATH + "test_one_col.csv"
        self.test_filename3 = TESTPATH + "test_write.csv"

    def _get_csv_gen(self, filename, digest_types=None):
        test_file = open(filename)
        dialect = csv.Sniffer().sniff(test_file.read(1024))
        test_file.close()

        if digest_types is None:
            digest_types = [type(1)]

        has_header = False

        return CsvInterface(self.main_window, filename,
                            dialect, digest_types, has_header)

    def test_get_csv_cells_gen(self):
        """Tests generator from csv content"""

        csv_gen = self._get_csv_gen(self.test_filename)

        column = xrange(100)

        cell_gen = csv_gen._get_csv_cells_gen(column)

        for i, cell in enumerate(cell_gen):
            assert str(i) == cell

## Test iter somehow stalls py.test
#    def test_iter(self):
#        """Tests csv generator"""
#
#        csv_gen = self._get_csv_gen(self.test_filename)
#
#        assert [list(col) for col in csv_gen] == [['1', '2'], ['3', '4']]
#
#        csv_gen2 = self._get_csv_gen(self.test_filename2,
#                                     digest_types=[type("")])
#
#        for i, col in enumerate(csv_gen2):
#            list_col = list(col)
#            if i < 6:
#                assert list_col == ["'" + str(i + 1) + "'", "''"]
#            else:
#                assert list_col == ["''", "''"]

    def test_write(self):
        """Tests writing csv file"""

        csv_gen = self._get_csv_gen(self.test_filename)
        csv_gen.path = self.test_filename3

        csv_gen.write(xrange(100) for _ in xrange(100))

        infile = open(self.test_filename3)
        content = infile.read()
        assert content[:10] == "0\t1\t2\t3\t4\t"
        infile.close()


class TestTxtGenerator(object):
    """Tests generating txt files"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

        self.test_filename = TESTPATH + "test.csv"
        self.test_filename_single_col = TESTPATH + "large.txt"
        self.test_filename_notthere = TESTPATH + "notthere.txt"
        self.test_filename_bin = TESTPATH + "test1.pys"

    def test_iter(self):
        """Tests iterating over text files"""

        # Correct file with 2 columns

        txt_gen = TxtGenerator(self.main_window, self.test_filename)

        res = [['1', '2'], ['3', '4']]
        assert list(list(line_gen) for line_gen in txt_gen) == res

        # Correct file with 1 column

        txt_gen = TxtGenerator(self.main_window, self.test_filename_single_col)

        txt_list = []
        for i, line_gen in enumerate(txt_gen):
            txt_list.append(list(line_gen))
            if i == 3:
                break
        assert txt_list == [['00'], ['877452769922012304'],
                            ['877453769923767209'], ['877454769925522116']]

        # Missing file

        txt_gen = TxtGenerator(self.main_window, self.test_filename_notthere)
        assert list(txt_gen) == []

        # Binary file

        txt_gen = TxtGenerator(self.main_window, self.test_filename_bin)

        has_value_error = False

        try:
            print [list(ele) for ele in txt_gen]

        except ValueError:
            has_value_error = True

        ##TODO: This still fails and I do not know how to identify binary files
        ##assert has_value_error # ValueError should occur on binary file


class TestExchangeActions(object):
    """Does nothing because of User interaction in this method"""

    pass


class TestPrintActions(object):
    """Does nothing because of User interaction in this method"""

    pass


class TestClipboardActions(object):
    """Clipboard actions test class. Does not use actual clipboard."""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    param_copy = [
        {'selection': Selection([], [], [], [], [(0, 0)]), 'result': "'Test'"},
        {'selection': Selection([], [], [], [], [(999, 0)]), 'result': "1"},
        {'selection': Selection([], [], [], [], [(999, 99)]),
         'result': "$^%&$^"},
        {'selection': Selection([], [], [], [], [(0, 1)]),
         'result': "1"},
        {'selection': Selection([(0, 1)], [(0, 1)], [], [], []),
         'result': "1"},
        {'selection': Selection([(0, 1)], [(1, 1)], [], [], []),
         'result': "1\n3"},
        {'selection': Selection([(0, 1)], [(1, 2)], [], [], []),
         'result': "1\t2\n3\t4"},
    ]

    @params(param_copy)
    def test_cut(self, selection, result):
        """Test cut, i. e. copy and deletion"""

        restore_basic_grid(self.grid)

        assert self.main_window.actions.cut(selection) == result

        (top, left), (bottom, right) = selection.get_bbox()

        for row in xrange(top, bottom + 1):
            for col in xrange(left, right + 1):
                if (row, col) in selection:
                    key = row, col, 0
                    assert self.code_array[key] is None
                    self.code_array[key] = grid_values[key]

    @params(param_copy)
    def test_copy(self, selection, result):
        """Test copy of single values, lists and matrices"""

        restore_basic_grid(self.grid)

        assert self.main_window.actions.copy(selection) == result

    param_copy_result = [
        {'selection': Selection([], [], [], [], [(0, 0)]), 'result': "Test"},
        {'selection': Selection([], [], [], [], [(999, 0)]), 'result': "1"},
        {'selection': Selection([], [], [], [], [(999, 99)]),
         'result': "invalid syntax (<unknown>, line 1)"},
    ]

    @params(param_copy_result)
    def test_copy_result(self, selection, result):
        """Test copy results of single values, lists and matrices"""

        restore_basic_grid(self.grid)

        assert self.main_window.actions.copy_result(selection) == result

#    param_paste = [
#        {'target': (0, 0), 'data': "1",
#         'test_key': (0, 0, 0), 'test_val': "1"},
#        {'target': (25, 25), 'data': "1\t2",
#         'test_key': (25, 25, 0), 'test_val': "1"},
#        {'target': (25, 25), 'data': "1\t2",
#         'test_key': (25, 26, 0), 'test_val': "2"},
#        {'target': (25, 25), 'data': "1\t2",
#         'test_key': (26, 25, 0), 'test_val': None},
#        {'target': (25, 25), 'data': "1\t2\n3\t4",
#         'test_key': (25, 25, 0),  'test_val': "1"},
#        {'target': (25, 25), 'data': "1\t2\n3\t4",
#         'test_key': (25, 26, 0),  'test_val': "2"},
#        {'target': (25, 25), 'data': "1\t2\n3\t4",
#         'test_key': (26, 25, 0),  'test_val': "3"},
#        {'target': (27, 27), 'data': u"ä",
#         'test_key': (27, 27, 0), 'test_val': u"ä"},
#    ]
#
#    @params(param_paste)
#    def test_paste(self, target, data, test_key, test_val):
#        """Test paste of single values, lists and matrices"""
#
#        basic_setup_test(self.grid, self.main_window.actions.paste,
#                         test_key, test_val, target, data)


class TestMacroActions(object):
    """Unit tests for macro actions"""

    macros = "def f(x): return x * x"

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

    def test_replace_macros(self):
        self.main_window.actions.replace_macros(self.macros)

        assert self.main_window.grid.code_array.macros == self.macros
        self.main_window.actions.replace_macros("")

    def test_execute_macros(self):

        # Unsure how to test since macros are not global in py.test

        pass

    param_open_macros = [
        {'filename': TESTPATH + "macrotest2.py"},
    ]

    @params(param_open_macros)
    def test_open_macros(self, filename):

        testmacro_infile = open(filename)
        testmacro_string = "\n" + testmacro_infile.read()
        testmacro_infile.close()

        self.main_window.actions.open_macros(filename)

        macros = self.main_window.grid.code_array.macros

        assert testmacro_string == macros
        assert self.main_window.grid.code_array.safe_mode

    def test_save_macros(self):
        """Unit tests for save_macros"""

        filepath = TESTPATH + "macro_dummy.py"

        macros = "Test"

        self.main_window.actions.save_macros(filepath, macros)
        macro_file = open(filepath)
        assert macros == macro_file.read()
        macro_file.close()
        os.remove(filepath)

        macro_file = open(filepath, "w")
        self.main_window.actions.save_macros(filepath, macros)
        macro_file.close()
        os.remove(filepath)


class TestHelpActions(object):
    """Does nothing because of User interaction in this method"""

    pass

########NEW FILE########
__FILENAME__ = _grid_actions
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------


"""
_grid_actions.py
=======================

Module for main main grid level actions.
All non-trivial functionality that results from grid actions
and belongs to the grid only goes here.

Provides:
---------
  1. FileActions: Actions which affect the open grid
  2. TableRowActionsMixin: Mixin for TableActions
  3. TableColumnActionsMixin: Mixin for TableActions
  4. TableTabActionsMixin: Mixin for TableActions
  5. TableActions: Actions which affect table
  6. MacroActions: Actions on macros
  7. UnRedoActions: Actions on the undo redo system
  8. GridActions: Actions on the grid as a whole
  9. SelectionActions: Actions on the grid selection
  10. FindActions: Actions for finding and replacing
  11. AllGridActions: All grid actions as a bundle


"""

import itertools
import src.lib.i18n as i18n
import os

try:
    import xlrd
except ImportError:
    xlrd = None

try:
    import xlwt
except ImportError:
    xlwt = None

import wx

from src.config import config
from src.sysvars import get_default_font, is_gtk
from src.gui._grid_table import GridTable
from src.interfaces.pys import Pys
from src.interfaces.xls import Xls

try:
    from src.lib.gpg import sign, verify
    GPG_PRESENT = True

except ImportError:
    GPG_PRESENT = False

from src.lib.selection import Selection
from src.lib.fileio import Bz2AOpen

from src.actions._main_window_actions import Actions
from src.actions._grid_cell_actions import CellActions

from src.gui._events import post_command_event

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


class FileActions(Actions):
    """File actions on the grid"""

    def __init__(self, grid):
        Actions.__init__(self, grid)

        # The pys file version that are expected.
        # The latter version is created
        self.pys_versions = ["0.1"]

        self.saving = False

        self.main_window.Bind(self.EVT_CMD_GRID_ACTION_OPEN, self.open)
        self.main_window.Bind(self.EVT_CMD_GRID_ACTION_SAVE, self.save)

        self.type2interface = {
            "pys": Pys,
            "xls": Xls,
        }

    def _is_aborted(self, cycle, statustext, total_elements=None, freq=None):
        """Displays progress and returns True if abort

        Parameters
        ----------

        cycle: Integer
        \tThe current operation cycle
        statustext: String
        \tLeft text in statusbar to be displayed
        total_elements: Integer:
        \tThe number of elements that have to be processed
        freq: Integer, defaults to None
        \tNo. operations between two abort possibilities, 1000 if None

        """

        if total_elements is None:
            statustext += _("{nele} elements processed. Press <Esc> to abort.")
        else:
            statustext += _("{nele} of {totalele} elements processed. "
                            "Press <Esc> to abort.")

        if freq is None:
            show_msg = False
            freq = 1000
        else:
            show_msg = True

        # Show progress in statusbar each freq (1000) cells
        if cycle % freq == 0:
            if show_msg:
                text = statustext.format(nele=cycle, totalele=total_elements)
                try:
                    post_command_event(self.main_window, self.StatusBarMsg,
                                       text=text)
                except TypeError:
                    # The main window does not exist any more
                    pass

            # Now wait for the statusbar update to be written on screen
            if is_gtk():
                wx.Yield()

            # Abort if we have to
            if self.need_abort:
                # We have to abort`
                return True

        # Continue
        return False

    def validate_signature(self, filename):
        """Returns True if a valid signature is present for filename"""

        if not GPG_PRESENT:
            return False

        sigfilename = filename + '.sig'

        try:
            dummy = open(sigfilename)
            dummy.close()
        except IOError:
            # Signature file does not exist
            return False

        # Check if the sig is valid for the sigfile
        return verify(sigfilename, filename)

    def enter_safe_mode(self):
        """Enters safe mode"""

        self.code_array.safe_mode = True

    def leave_safe_mode(self):
        """Leaves safe mode"""

        self.code_array.safe_mode = False

        # Clear result cache
        self.code_array.result_cache.clear()

        # Execute macros
        self.main_window.actions.execute_macros()

        post_command_event(self.main_window, self.SafeModeExitMsg)

    def approve(self, filepath):
        """Sets safe mode if signature missing of invalid"""

        try:
            signature_valid = self.validate_signature(filepath)

        except ValueError:
            # GPG is not installed
            signature_valid = False

        if signature_valid:
            self.leave_safe_mode()
            post_command_event(self.main_window, self.SafeModeExitMsg)

            statustext = _("Valid signature found. File is trusted.")
            post_command_event(self.main_window, self.StatusBarMsg,
                               text=statustext)

        else:
            self.enter_safe_mode()
            post_command_event(self.main_window, self.SafeModeEntryMsg)

            statustext = \
                _("File is not properly signed. Safe mode "
                  "activated. Select File -> Approve to leave safe mode.")
            post_command_event(self.main_window, self.StatusBarMsg,
                               text=statustext)

    def clear_globals_reload_modules(self):
        """Clears globals and reloads modules"""

        self.code_array.clear_globals()
        self.code_array.reload_modules()

        # Clear result cache
        self.code_array.result_cache.clear()

    def _get_file_version(self, infile):
        """Returns infile version string."""

        # Determine file version
        for line1 in infile:
            if line1.strip() != "[Pyspread save file version]":
                raise ValueError(_("File format unsupported."))
            break

        for line2 in infile:
            return line2.strip()

    def clear(self, shape=None):
        """Empties grid and sets shape to shape

        Clears all attributes, row heights, column withs and frozen states.
        Empties undo/redo list and caches. Empties globals.

        Properties
        ----------

        shape: 3-tuple of Integer, defaults to None
        \tTarget shape of grid after clearing all content.
        \tShape unchanged if None

        """

        # Without setting this explicitly, the cursor is set too late
        self.grid.actions.cursor = 0, 0, 0
        self.grid.current_table = 0

        post_command_event(self.main_window.grid, self.GotoCellMsg,
                           key=(0, 0, 0))

        # Clear cells
        self.code_array.dict_grid.clear()

        # Clear attributes
        del self.code_array.dict_grid.cell_attributes[:]

        if shape is not None:
            # Set shape
            self.code_array.shape = shape

        # Clear row heights and column widths
        self.code_array.row_heights.clear()
        self.code_array.col_widths.clear()

        # Clear caches
        self.code_array.unredo.reset()
        self.code_array.result_cache.clear()

        # Clear globals
        self.code_array.clear_globals()
        self.code_array.reload_modules()

    def open(self, event):
        """Opens a file that is specified in event.attr

        Parameters
        ----------
        event.attr: Dict
        \tkey filepath contains file path of file to be loaded

        """

        filepath = event.attr["filepath"]
        try:
            filetype = event.attr["filetype"]

        except KeyError:
            filetype = "pys"

        type2opener = {"pys": (Bz2AOpen, [filepath, "r"],
                               {"main_window": self.main_window})}
        if xlrd is not None:
            type2opener["xls"] = \
                (xlrd.open_workbook, [filepath], {"formatting_info": True})

        # Specify the interface that shall be used

        opener, op_args, op_kwargs = type2opener[filetype]
        Interface = self.type2interface[filetype]

        # Set state for file open
        self.opening = True

        try:
            with opener(*op_args, **op_kwargs) as infile:
                # Make loading safe
                self.approve(filepath)

                # Disable undo
                self.grid.code_array.unredo.active = True

                try:
                    wx.BeginBusyCursor()
                    self.grid.Disable()
                    self.clear()
                    interface = Interface(self.grid.code_array, infile)
                    interface.to_code_array()

                except ValueError, err:
                    post_command_event(self.main_window, self.StatusBarMsg,
                                       text=str(err))

                finally:
                    self.grid.GetTable().ResetView()
                    post_command_event(self.main_window, self.ResizeGridMsg,
                                       shape=self.grid.code_array.shape)
                    self.grid.Enable()
                    wx.EndBusyCursor()

                # Execute macros
                self.main_window.actions.execute_macros()

                # Enable undo again
                self.grid.code_array.unredo.active = False

                self.grid.GetTable().ResetView()
                self.grid.ForceRefresh()

                # File sucessfully opened. Approve again to show status.
                self.approve(filepath)

        except IOError:
            txt = _("Error opening file {filepath}.").format(filepath=filepath)
            post_command_event(self.main_window, self.StatusBarMsg, text=txt)

            return False

        except EOFError:
            # Normally on empty grids
            pass

        finally:
            # Unset state for file open
            self.opening = False

    def sign_file(self, filepath):
        """Signs file if possible"""

        if not GPG_PRESENT:
            return

        signed_data = sign(filepath)
        signature = signed_data.data

        if signature is None or not signature:
            statustext = _('Error signing file. ') + signed_data.stderr
            try:
                post_command_event(self.main_window, self.StatusBarMsg,
                                   text=statustext)
            except TypeError:
                # The main window does not exist any more
                pass

            return

        with open(filepath + '.sig', 'wb') as signfile:
            signfile.write(signature)

        # Statustext differs if a save has occurred

        if self.code_array.safe_mode:
            statustext = _('File saved and signed')
        else:
            statustext = _('File signed')

        try:
            post_command_event(self.main_window, self.StatusBarMsg,
                               text=statustext)
        except TypeError:
            # The main window does not exist any more
            pass

    def save(self, event):
        """Saves a file that is specified in event.attr

        Parameters
        ----------
        event.attr: Dict
        \tkey filepath contains file path of file to be saved

        """

        filepath = event.attr["filepath"]

        try:
            filetype = event.attr["filetype"]

        except KeyError:
            filetype = "pys"

        Interface = self.type2interface[filetype]

        io_error_text = _("Error writing to file {filepath}.")
        io_error_text = io_error_text.format(filepath=filepath)

        # Set state to file saving
        self.saving = True

        # Make sure that old save file does not get lost on abort save
        tmpfile = filepath + "~"

        try:
            wx.BeginBusyCursor()
            self.grid.Disable()

            if filetype == "pys":
                with Bz2AOpen(tmpfile, "wb", main_window=self.main_window) \
                        as outfile:

                    try:
                        interface = Interface(self.grid.code_array, outfile)
                        interface.from_code_array()

                    except ValueError, err:
                        post_command_event(self.main_window, self.StatusBarMsg,
                                           text=err)

            elif filetype == "xls":
                workbook = xlwt.Workbook()
                interface = Interface(self.grid.code_array, workbook)
                interface.from_code_array()
                workbook.save(tmpfile)

            # Move save file from temp file to filepath
            try:
                os.rename(tmpfile, filepath)

            except OSError:
                # No tmp file present
                pass

        except IOError:
            try:
                post_command_event(self.main_window, self.StatusBarMsg,
                                   text=io_error_text)
            except TypeError:
                # The main window does not exist any more
                pass

            return False

        finally:
            self.saving = False
            self.grid.Enable()
            wx.EndBusyCursor()

        # Mark content as unchanged
        try:
            post_command_event(self.main_window, self.ContentChangedMsg,
                               changed=False)
        except TypeError:
            # The main window does not exist any more
            pass

        # Sign so that the new file may be retrieved without safe mode
        if self.code_array.safe_mode:
            msg = _("File saved but not signed because it is unapproved.")
            try:
                post_command_event(self.main_window, self.StatusBarMsg,
                                   text=msg)
            except TypeError:
                # The main window does not exist any more
                pass

        elif filetype == "pys" and not outfile.aborted:
            self.sign_file(filepath)


class TableRowActionsMixin(Actions):
    """Table row controller actions"""

    def set_row_height(self, row, height):
        """Sets row height and marks grid as changed"""

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        tab = self.grid.current_table

        self.code_array.set_row_height(row, tab, height)
        self.grid.SetRowSize(row, height)

    def insert_rows(self, row, no_rows=1):
        """Adds no_rows rows before row, appends if row > maxrows

        and marks grid as changed

        """

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        tab = self.grid.current_table

        self.code_array.insert(row, no_rows, axis=0, tab=tab)

    def delete_rows(self, row, no_rows=1):
        """Deletes no_rows rows and marks grid as changed"""

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        tab = self.grid.current_table

        try:
            self.code_array.delete(row, no_rows, axis=0, tab=tab)

        except ValueError, err:
            post_command_event(self.main_window, self.StatusBarMsg,
                               text=err.message)


class TableColumnActionsMixin(Actions):
    """Table column controller actions"""

    def set_col_width(self, col, width):
        """Sets column width and marks grid as changed"""

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        tab = self.grid.current_table

        self.code_array.set_col_width(col, tab, width)
        self.grid.SetColSize(col, width)

    def insert_cols(self, col, no_cols=1):
        """Adds no_cols columns before col, appends if col > maxcols

        and marks grid as changed

        """

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        tab = self.grid.current_table

        self.code_array.insert(col, no_cols, axis=1, tab=tab)

    def delete_cols(self, col, no_cols=1):
        """Deletes no_cols column and marks grid as changed"""

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        tab = self.grid.current_table

        try:
            self.code_array.delete(col, no_cols, axis=1, tab=tab)

        except ValueError, err:
            post_command_event(self.main_window, self.StatusBarMsg,
                               text=err.message)


class TableTabActionsMixin(Actions):
    """Table tab controller actions"""

    def insert_tabs(self, tab, no_tabs=1):
        """Adds no_tabs tabs before table, appends if tab > maxtabs

        and marks grid as changed

        """

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        self.code_array.insert(tab, no_tabs, axis=2)

        # Update TableChoiceIntCtrl
        shape = self.grid.code_array.shape
        post_command_event(self.main_window, self.ResizeGridMsg, shape=shape)

    def delete_tabs(self, tab, no_tabs=1):
        """Deletes no_tabs tabs and marks grid as changed"""

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        try:
            self.code_array.delete(tab, no_tabs, axis=2)

            # Update TableChoiceIntCtrl
            shape = self.grid.code_array.shape
            post_command_event(self.main_window, self.ResizeGridMsg,
                               shape=shape)

        except ValueError, err:
            post_command_event(self.main_window, self.StatusBarMsg,
                               text=err.message)


class TableActions(TableRowActionsMixin, TableColumnActionsMixin,
                   TableTabActionsMixin):
    """Table controller actions"""

    def __init__(self, grid):
        TableRowActionsMixin.__init__(self, grid)
        TableColumnActionsMixin.__init__(self, grid)
        TableTabActionsMixin.__init__(self, grid)

        # Action states

        self.pasting = False

        # Bindings

        self.main_window.Bind(wx.EVT_KEY_DOWN, self.on_key)

    def on_key(self, event):
        """Sets abort if pasting and if escape is pressed"""

        # If paste is running and Esc is pressed then we need to abort

        if event.GetKeyCode() == wx.WXK_ESCAPE and \
           self.pasting or self.grid.actions.saving:
            self.need_abort = True

        event.Skip()

    def _get_full_key(self, key):
        """Returns full key even if table is omitted"""

        length = len(key)

        if length == 3:
            return key

        elif length == 2:
            row, col = key
            tab = self.grid.current_table
            return row, col, tab

        else:
            msg = _("Key length {length}  not in (2, 3)").format(length=length)
            raise ValueError(msg)

    def _abort_paste(self):
        """Aborts import"""

        statustext = _("Paste aborted.")
        post_command_event(self.main_window, self.StatusBarMsg,
                           text=statustext)

        self.pasting = False
        self.need_abort = False

    def _show_final_overflow_message(self, row_overflow, col_overflow):
        """Displays overflow message after import in statusbar"""

        if row_overflow and col_overflow:
            overflow_cause = _("rows and columns")
        elif row_overflow:
            overflow_cause = _("rows")
        elif col_overflow:
            overflow_cause = _("columns")
        else:
            raise AssertionError(_("Import cell overflow missing"))

        statustext = \
            _("The imported data did not fit into the grid {cause}. "
              "It has been truncated. Use a larger grid for full import.").\
            format(cause=overflow_cause)
        post_command_event(self.main_window, self.StatusBarMsg,
                           text=statustext)

    def _show_final_paste_message(self, tl_key, no_pasted_cells):
        """Show actually pasted number of cells"""

        plural = "" if no_pasted_cells == 1 else _("s")

        statustext = _("{ncells} cell{plural} pasted at cell {topleft}").\
            format(ncells=no_pasted_cells, plural=plural, topleft=tl_key)

        post_command_event(self.main_window, self.StatusBarMsg,
                           text=statustext)

    def paste_to_current_cell(self, tl_key, data, freq=None):
        """Pastes data into grid from top left cell tl_key

        Parameters
        ----------

        ul_key: Tuple
        \key of top left cell of paste area
        data: iterable of iterables where inner iterable returns string
        \tThe outer iterable represents rows
        freq: Integer, defaults to None
        \tStatus message frequency

        """

        self.pasting = True

        grid_rows, grid_cols, __ = self.grid.code_array.shape

        self.need_abort = False

        tl_row, tl_col, tl_tab = self._get_full_key(tl_key)

        row_overflow = False
        col_overflow = False

        no_pasted_cells = 0

        for src_row, row_data in enumerate(data):
            target_row = tl_row + src_row

            if self.grid.actions._is_aborted(src_row, _("Pasting cells... "),
                                             freq=freq):
                self._abort_paste()
                return False

            # Check if rows fit into grid
            if target_row >= grid_rows:
                row_overflow = True
                break

            for src_col, cell_data in enumerate(row_data):
                target_col = tl_col + src_col

                if target_col >= grid_cols:
                    col_overflow = True
                    break

                if cell_data is not None:
                    # Is only None if pasting into selection
                    key = target_row, target_col, tl_tab

                    try:
                        # Set cell but do not mark unredo
                        # before pasting is finished

                        self.grid.code_array.__setitem__(key, cell_data,
                                                         mark_unredo=False)
                        no_pasted_cells += 1
                    except KeyError:
                        pass

        if row_overflow or col_overflow:
            self._show_final_overflow_message(row_overflow, col_overflow)

        else:
            self._show_final_paste_message(tl_key, no_pasted_cells)

        if no_pasted_cells:
            # If cells have been pasted mark unredo operation
            self.grid.code_array.unredo.mark()

        self.pasting = False

    def selection_paste_data_gen(self, selection, data, freq=None):
        """Generator that yields data for selection paste"""

        (bb_top, bb_left), (bb_bottom, bb_right) = \
            selection.get_grid_bbox(self.grid.code_array.shape)
        bbox_height = bb_bottom - bb_top + 1
        bbox_width = bb_right - bb_left + 1

        for row, row_data in enumerate(itertools.cycle(data)):
            # Break if row is not in selection bbox
            if row >= bbox_height:
                break

            # Duplicate row data if selection is wider than row data
            row_data = list(row_data)
            duplicated_row_data = row_data * (bbox_width // len(row_data) + 1)
            duplicated_row_data = duplicated_row_data[:bbox_width]

            for col in xrange(len(duplicated_row_data)):
                if (bb_top, bb_left + col) not in selection:
                    duplicated_row_data[col] = None

            yield duplicated_row_data

    def paste_to_selection(self, selection, data, freq=None):
        """Pastes data into grid selection"""

        (bb_top, bb_left), (bb_bottom, bb_right) = \
            selection.get_grid_bbox(self.grid.code_array.shape)
        adjusted_data = self.selection_paste_data_gen(selection, data)
        self.paste_to_current_cell((bb_top, bb_left), adjusted_data, freq=freq)

    def paste(self, tl_key, data, freq=None):
        """Pastes data into grid, marks grid changed

        If no selection is present, data is pasted starting with current cell
        If a selection is present, data is pasted fully if the selection is
        smaller. If the selection is larger then data is duplicated.

        Parameters
        ----------

        ul_key: Tuple
        \key of top left cell of paste area
        data: iterable of iterables where inner iterable returns string
        \tThe outer iterable represents rows
        freq: Integer, defaults to None
        \tStatus message frequency

        """

        # Get selection bounding box

        selection = self.get_selection()

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        if selection:
            # There is a selection.  Paste into it
            self.paste_to_selection(selection, data, freq=freq)
        else:
            # There is no selection.  Paste from top left cell.
            self.paste_to_current_cell(tl_key, data, freq=freq)

    def change_grid_shape(self, shape):
        """Grid shape change event handler, marks content as changed"""

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        self.grid.code_array.shape = shape

        # Update TableChoiceIntCtrl
        post_command_event(self.main_window, self.ResizeGridMsg, shape=shape)

        # Clear caches
        self.code_array.unredo.reset()
        self.code_array.result_cache.clear()

    def replace_cells(self, key, sorted_row_idxs):
        """Replaces cells in current selection so that they are sorted"""

        row, col, tab = key

        new_keys = {}
        del_keys = []

        selection = self.grid.actions.get_selection()

        for __row, __col, __tab in self.grid.code_array:
            if __tab == tab and \
               (not selection or (__row, __col) in selection):
                new_row = sorted_row_idxs.index(__row)
                if __row != new_row:
                    new_keys[(new_row, __col, __tab)] = \
                        self.grid.code_array((__row, __col, __tab))
                    del_keys.append((__row, __col, __tab))

        for key in del_keys:
            self.grid.code_array.pop(key, mark_unredo=False)

        for key in new_keys:
            self.grid.code_array.__setitem__(key, new_keys[key],
                                             mark_unredo=False)

        self.grid.code_array.unredo.mark()

    def sort_ascending(self, key):
        """Sorts selection (or grid if none) corresponding to column of key"""

        row, col, tab = key

        scells = self.grid.code_array[:, col, tab]

        def sorter(i):
            sorted_ele = scells[i]
            return sorted_ele is None, sorted_ele

        sorted_row_idxs = sorted(xrange(len(scells)), key=sorter)

        self.replace_cells(key, sorted_row_idxs)

        self.grid.ForceRefresh()

    def sort_descending(self, key):
        """Sorts inversely selection (or grid if none)

        corresponding to column of key

        """

        row, col, tab = key

        scells = self.grid.code_array[:, col, tab]
        sorted_row_idxs = sorted(xrange(len(scells)), key=scells.__getitem__)
        sorted_row_idxs.reverse()

        self.replace_cells(key, sorted_row_idxs)

        self.grid.ForceRefresh()

class UnRedoActions(Actions):
    """Undo and redo operations"""

    def undo(self):
        """Calls undo in model.code_array.unredo, marks content as changed"""

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        self.grid.code_array.unredo.undo()

    def redo(self):
        """Calls redo in model.code_array.unredo, marks content as changed"""

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        self.grid.code_array.unredo.redo()


class GridActions(Actions):
    """Grid level grid actions"""

    def __init__(self, grid):
        Actions.__init__(self, grid)

        self.code_array = grid.code_array

        self.prev_rowcol = []  # Last mouse over cell

        self.main_window.Bind(self.EVT_CMD_GRID_ACTION_NEW, self.new)
        self.main_window.Bind(self.EVT_CMD_GRID_ACTION_TABLE_SWITCH,
                              self.switch_to_table)

    def new(self, event):
        """Creates a new spreadsheet. Expects code_array in event."""

        # Grid table handles interaction to code_array

        self.grid.actions.clear(event.shape)

        _grid_table = GridTable(self.grid, self.grid.code_array)
        self.grid.SetTable(_grid_table, True)

        # Update toolbars
        self.grid.update_entry_line()
        self.grid.update_attribute_toolbar()

    # Zoom actions

    def _zoom_rows(self, zoom):
        """Zooms grid rows"""

        self.grid.SetDefaultRowSize(self.grid.std_row_size * zoom,
                                    resizeExistingRows=True)
        self.grid.SetRowLabelSize(self.grid.row_label_size * zoom)

        for row, tab in self.code_array.row_heights:
            if tab == self.grid.current_table:
                zoomed_row_size = \
                    self.code_array.row_heights[(row, tab)] * zoom
                self.grid.SetRowSize(row, zoomed_row_size)

    def _zoom_cols(self, zoom):
        """Zooms grid columns"""

        self.grid.SetDefaultColSize(self.grid.std_col_size * zoom,
                                    resizeExistingCols=True)
        self.grid.SetColLabelSize(self.grid.col_label_size * zoom)

        for col, tab in self.code_array.col_widths:
            if tab == self.grid.current_table:
                zoomed_col_size = self.code_array.col_widths[(col, tab)] * zoom
                self.grid.SetColSize(col, zoomed_col_size)

    def _zoom_labels(self, zoom):
        """Adjust grid label font to zoom factor"""

        labelfont = self.grid.GetLabelFont()
        default_fontsize = get_default_font().GetPointSize()
        labelfont.SetPointSize(max(1, int(round(default_fontsize * zoom))))
        self.grid.SetLabelFont(labelfont)

    def zoom(self, zoom=None):
        """Zooms to zoom factor"""

        status = True

        if zoom is None:
            zoom = self.grid.grid_renderer.zoom
            status = False

        # Zoom factor for grid content
        self.grid.grid_renderer.zoom = zoom

        # Zoom grid labels
        self._zoom_labels(zoom)

        # Zoom rows and columns
        self._zoom_rows(zoom)
        self._zoom_cols(zoom)

        self.grid.ForceRefresh()

        if status:
            statustext = _(u"Zoomed to {0:.2f}.").format(zoom)

            post_command_event(self.main_window, self.StatusBarMsg,
                               text=statustext)

    def zoom_in(self):
        """Zooms in by zoom factor"""

        zoom = self.grid.grid_renderer.zoom

        target_zoom = zoom * (1 + config["zoom_factor"])

        if target_zoom < config["maximum_zoom"]:
            self.zoom(target_zoom)

    def zoom_out(self):
        """Zooms out by zoom factor"""

        zoom = self.grid.grid_renderer.zoom

        target_zoom = zoom * (1 - config["zoom_factor"])

        if target_zoom > config["minimum_zoom"]:
            self.zoom(target_zoom)

    def on_mouse_over(self, key):
        """Displays cell code of cell key in status bar"""

        def split_lines(string, line_length=80):
            """Returns string that is split into lines of length line_length"""

            result = u""
            line = 0

            while len(string) > line_length * line:
                line_start = line * line_length
                result += string[line_start:line_start+line_length]
                result += '\n'
                line += 1

            return result[:-1]

        row, col, tab = key

        if (row, col) != self.prev_rowcol and row >= 0 and col >= 0:
            self.prev_rowcol[:] = [row, col]

            max_result_length = int(config["max_result_length"])
            table = self.grid.GetTable()
            hinttext = table.GetSource(row, col, tab)[:max_result_length]

            if hinttext is None:
                hinttext = ''

            post_command_event(self.main_window, self.StatusBarMsg,
                               text=hinttext)

            cell_res = self.grid.code_array[row, col, tab]

            if cell_res is None:
                self.grid.SetToolTip(None)
                return

            try:
                cell_res_str = unicode(cell_res)
            except UnicodeEncodeError:
                cell_res_str = unicode(cell_res, encoding='utf-8')

            if len(cell_res_str) > max_result_length:
                cell_res_str = cell_res_str[:max_result_length] + ' [...]'

            self.grid.SetToolTipString(split_lines(cell_res_str))

    def get_visible_area(self):
        """Returns visible area

        Format is a tuple of the top left tuple and the lower right tuple

        """

        grid = self.grid

        top = grid.YToRow(grid.GetViewStart()[1] * grid.ScrollLineX)
        left = grid.XToCol(grid.GetViewStart()[0] * grid.ScrollLineY)

        # Now start at top left for determining the bottom right visible cell

        bottom, right = top, left

        while grid.IsVisible(bottom, left, wholeCellVisible=False):
            bottom += 1

        while grid.IsVisible(top, right, wholeCellVisible=False):
            right += 1

        # The derived lower right cell is *NOT* visible

        bottom -= 1
        right -= 1

        return (top, left), (bottom, right)

    def switch_to_table(self, event):
        """Switches grid to table

        Parameters
        ----------

        event.newtable: Integer
        \tTable that the grid is switched to

        """

        newtable = event.newtable

        no_tabs = self.grid.code_array.shape[2] - 1

        if 0 <= newtable <= no_tabs:
            self.grid.current_table = newtable

            # Change value of entry_line and table choice
            post_command_event(self.main_window, self.TableChangedMsg,
                               table=newtable)

            # Reset row heights and column widths by zooming

            self.zoom()

    def get_cursor(self):
        """Returns current grid cursor cell (row, col, tab)"""

        return self.grid.GetGridCursorRow(), self.grid.GetGridCursorCol(), \
            self.grid.current_table

    def set_cursor(self, value):
        """Changes the grid cursor cell.

        Parameters
        ----------

        value: 2-tuple or 3-tuple of String
        \trow, col, tab or row, col for target cursor position

        """

        if len(value) == 3:
            self.grid._last_selected_cell = row, col, tab = value

            if tab != self.cursor[2]:
                post_command_event(self.main_window,
                                   self.GridActionTableSwitchMsg, newtable=tab)
                if is_gtk():
                    wx.Yield()
        else:
            row, col = value
            self.grid._last_selected_cell = row, col, self.grid.current_table

        if not (row is None and col is None):
            self.grid.MakeCellVisible(row, col)
            self.grid.SetGridCursor(row, col)

    cursor = property(get_cursor, set_cursor)


class SelectionActions(Actions):
    """Actions that affect the grid selection"""

    def get_selection(self):
        """Returns selected cells in grid as Selection object"""

        # GetSelectedCells: individual cells selected by ctrl-clicking
        # GetSelectedRows: rows selected by clicking on the labels
        # GetSelectedCols: cols selected by clicking on the labels
        # GetSelectionBlockTopLeft
        # GetSelectionBlockBottomRight: For blocks selected by dragging
        # across the grid cells.

        block_top_left = self.grid.GetSelectionBlockTopLeft()
        block_bottom_right = self.grid.GetSelectionBlockBottomRight()
        rows = self.grid.GetSelectedRows()
        cols = self.grid.GetSelectedCols()
        cells = self.grid.GetSelectedCells()

        return Selection(block_top_left, block_bottom_right, rows, cols, cells)

    def select_cell(self, row, col, add_to_selected=False):
        """Selects a single cell"""

        self.grid.SelectBlock(row, col, row, col,
                              addToSelected=add_to_selected)

    def select_slice(self, row_slc, col_slc, add_to_selected=False):
        """Selects a slice of cells

        Parameters
        ----------
         * row_slc: Integer or Slice
        \tRows to be selected
         * col_slc: Integer or Slice
        \tColumns to be selected
         * add_to_selected: Bool, defaults to False
        \tOld selections are cleared if False

        """

        if not add_to_selected:
            self.grid.ClearSelection()

        if row_slc == row_slc == slice(None, None, None):
            # The whole grid is selected
            self.grid.SelectAll()

        elif row_slc.stop is None and col_slc.stop is None:
            # A block is selected:
            self.grid.SelectBlock(row_slc.start, col_slc.start,
                                  row_slc.stop - 1, col_slc.stop - 1)
        else:
            for row in xrange(row_slc.start, row_slc.stop, row_slc.step):
                for col in xrange(col_slc.start, col_slc.stop, col_slc.step):
                    self.select_cell(row, col, add_to_selected=True)

    def delete_selection(self):
        """Deletes selected cells, marks content as changed"""

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        selection = self.get_selection()
        current_table = self.grid.current_table

        for row, col, tab in self.grid.code_array.dict_grid.keys():
            if tab == current_table and (row, col) in selection:
                self.grid.actions.delete_cell((row, col, tab),
                                              mark_unredo=False)

        self.grid.code_array.unredo.mark()

        self.grid.code_array.result_cache.clear()

    def delete(self):
        """Deletes a selection if any else deletes the cursor cell

        Refreshes grid after deletion

        """

        if self.grid.IsSelection():
            # Delete selection
            self.grid.actions.delete_selection()

        else:
            # Delete cell at cursor
            cursor = self.grid.actions.cursor
            self.grid.actions.delete_cell(cursor)

        # Update grid
        self.grid.ForceRefresh()

    def quote_selection(self):
        """Quotes selected cells, marks content as changed"""

        selection = self.get_selection()
        current_table = self.grid.current_table
        for row, col, tab in self.grid.code_array.dict_grid.keys():
            if tab == current_table and (row, col) in selection:
                self.grid.actions.quote_code((row, col, tab),
                                             mark_unredo=False)

        self.grid.code_array.unredo.mark()

        self.grid.code_array.result_cache.clear()

    def copy_selection_access_string(self):
        """Copys access_string to selection to the clipboard

        An access string is Python code to reference the selection
        If there is no selection then a reference to the current cell is copied

        """

        selection = self.get_selection()
        if not selection:
            cursor = self.grid.actions.cursor
            selection = Selection([], [], [], [], [tuple(cursor[:2])])
        shape = self.grid.code_array.shape
        tab = self.grid.current_table

        access_string = selection.get_access_string(shape, tab)

        # Copy access string to clipboard
        self.grid.main_window.clipboard.set_clipboard(access_string)

        # Display copy operation and access string in status bar
        statustext = _("Cell reference copied to clipboard: {access_string}")
        statustext = statustext.format(access_string=access_string)

        post_command_event(self.main_window, self.StatusBarMsg,
                           text=statustext)


class FindActions(Actions):
    """Actions for finding inside the grid"""

    def find_all(self, find_string, flags):
        """Return list of all positions of event_find_string in MainGrid.

        Only the code is searched. The result is not searched here.

        Parameters:
        -----------
        gridpos: 3-tuple of Integer
        \tPosition at which the search starts
        find_string: String
        \tString to find in grid
        flags: List of strings
        \t Search flag out of
        \t ["UP" xor "DOWN", "WHOLE_WORD", "MATCH_CASE", "REG_EXP"]

        """

        code_array = self.grid.code_array
        string_match = code_array.string_match

        find_keys = []

        for key in code_array:
            if string_match(code_array(key), find_string, flags) is not None:
                find_keys.append(key)

        return find_keys

    def find(self, gridpos, find_string, flags, search_result=True):
        """Return next position of event_find_string in MainGrid

        Parameters:
        -----------
        gridpos: 3-tuple of Integer
        \tPosition at which the search starts
        find_string: String
        \tString to find in grid
        flags: List of strings
        \tSearch flag out of
        \t["UP" xor "DOWN", "WHOLE_WORD", "MATCH_CASE", "REG_EXP"]
        search_result: Bool, defaults to True
        \tIf True then the search includes the result string (slower)

        """

        findfunc = self.grid.code_array.findnextmatch

        if "DOWN" in flags:
            if gridpos[0] < self.grid.code_array.shape[0]:
                gridpos[0] += 1
            elif gridpos[1] < self.grid.code_array.shape[1]:
                gridpos[1] += 1
            elif gridpos[2] < self.grid.code_array.shape[2]:
                gridpos[2] += 1
            else:
                gridpos = (0, 0, 0)
        elif "UP" in flags:
            if gridpos[0] > 0:
                gridpos[0] -= 1
            elif gridpos[1] > 0:
                gridpos[1] -= 1
            elif gridpos[2] > 0:
                gridpos[2] -= 1
            else:
                gridpos = [dim - 1 for dim in self.grid.code_array.shape]

        return findfunc(tuple(gridpos), find_string, flags, search_result)

    def replace_all(self, findpositions, find_string, replace_string):
        """Replaces occurrences of find_string with replace_string at findpos

        and marks content as changed

        Parameters
        ----------

        findpositions: List of 3-Tuple of Integer
        \tPositions in grid that shall be replaced
        find_string: String
        \tString to be overwritten in the cell
        replace_string: String
        \tString to be used for replacement

        """
        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        for findpos in findpositions:
            old_code = self.grid.code_array(findpos)
            new_code = old_code.replace(find_string, replace_string)

            self.grid.code_array[findpos] = new_code

        statustext = _("Replaced {no_cells} cells.")
        statustext = statustext.format(no_cells=len(findpositions))

        post_command_event(self.main_window, self.StatusBarMsg,
                           text=statustext)

    def replace(self, findpos, find_string, replace_string):
        """Replaces occurrences of find_string with replace_string at findpos

        and marks content as changed

        Parameters
        ----------

        findpos: 3-Tuple of Integer
        \tPosition in grid that shall be replaced
        find_string: String
        \tString to be overwritten in the cell
        replace_string: String
        \tString to be used for replacement

        """

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        old_code = self.grid.code_array(findpos)
        new_code = old_code.replace(find_string, replace_string)

        self.grid.code_array[findpos] = new_code
        self.grid.actions.cursor = findpos

        statustext = _("Replaced {old} with {new} in cell {key}.")
        statustext = statustext.format(old=old_code, new=new_code, key=findpos)

        post_command_event(self.main_window, self.StatusBarMsg,
                           text=statustext)


class AllGridActions(FileActions, TableActions, UnRedoActions,
                     GridActions, SelectionActions, FindActions, CellActions):
    """All grid actions as a bundle"""

    def __init__(self, grid):
        FileActions.__init__(self, grid)
        TableActions.__init__(self, grid)
        UnRedoActions.__init__(self, grid)
        GridActions.__init__(self, grid)
        SelectionActions.__init__(self, grid)
        FindActions.__init__(self, grid)
        CellActions.__init__(self, grid)

    def _replace_bbox_none(self, bbox):
        """Returns bbox, in which None is replaced by grid boundaries"""

        (bb_top, bb_left), (bb_bottom, bb_right) = bbox

        if bb_top is None:
            bb_top = 0

        if bb_left is None:
            bb_left = 0

        if bb_bottom is None:
            bb_bottom = self.code_array.shape[0] - 1

        if bb_right is None:
            bb_right = self.code_array.shape[1] - 1

        return (bb_top, bb_left), (bb_bottom, bb_right)

########NEW FILE########
__FILENAME__ = _grid_cell_actions
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

import wx

import src.lib.i18n as i18n
from src.lib.selection import Selection
from src.actions._main_window_actions import Actions
from src.gui._events import post_command_event

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


"""
_grid_cell_actions.py
=======================

Module for cell level main grid level actions.

Provides:
---------
  1. CellActions: Changes to cell code

"""


class CellActions(Actions):
    """Mixin class that supplies Cell code additions, changes and deletion"""

    def set_code(self, key, code, mark_unredo=True):
        """Sets code of cell key, marks grid as changed"""

        old_code = self.grid.code_array(key)

        try:
            old_code = unicode(old_code, encoding="utf-8")

        except TypeError:
            pass

        if not (old_code is None and not code) and code != old_code:
            # Mark content as changed
            post_command_event(self.main_window, self.ContentChangedMsg,
                               changed=True)

        # Set cell code
        self.grid.code_array.__setitem__(key, code, mark_unredo=mark_unredo)

    def quote_code(self, key, mark_unredo=True):
        """Returns string quoted code """

        old_code = self.grid.code_array(key)
        try:
            old_code = old_code.rstrip()

        except AttributeError:
            # Old code is None --> There is no code to quote
            return

        if old_code and old_code[0] + old_code[-1] not in ('""', "''") and \
            '"' not in old_code:
            self.set_code(key, '"' + old_code + '"', mark_unredo=mark_unredo)

    def delete_cell(self,  key, mark_unredo=True):
        """Deletes key cell"""

        try:
            self.code_array.pop(key, mark_unredo=mark_unredo)

        except KeyError:
            pass

        self.grid.code_array.result_cache.clear()

    def _get_absolute_reference(self, ref_key):
        """Returns absolute reference code for key."""

        key_str = u", ".join(map(str, ref_key))
        return u"S[" + key_str + u"]"

    def _get_relative_reference(self, cursor, ref_key):
        """Returns absolute reference code for key.

        Parameters
        ----------

        cursor: 3-tuple of Integer
        \tCurrent cursor position
        ref_key: 3-tuple of Integer
        \tAbsolute reference key

        """

        magics = ["X", "Y", "Z"]

        # mapper takes magic, key, ref_key to build string
        def get_rel_key_ele(cursor_ele, ref_key_ele):
            """Returns relative key suffix for given key and reference key"""

            # cursor is current cursor position
            # ref_key is absolute target position

            diff_key_ele = ref_key_ele - cursor_ele

            if diff_key_ele == 0:
                return u""

            elif diff_key_ele < 0:
                return u"-" + str(abs(diff_key_ele))

            elif diff_key_ele > 0:
                return u"+" + str(diff_key_ele)

            else:
                msg = _("{key} seems to be no Integer")
                msg = msg.format(key=diff_key_ele)
                raise ValueError(msg)

        key_strings = []

        for magic, cursor_ele, ref_key_ele in zip(magics, cursor, ref_key):
            key_strings.append(magic +
                               get_rel_key_ele(cursor_ele, ref_key_ele))

        key_string = u", ".join(key_strings)

        return u"S[" + key_string + u"]"

    def append_reference_code(self, key, ref_key, ref_type="absolute"):
        """Appends reference code to cell code.

        Replaces existing reference.

        Parameters
        ----------
        key: 3-tuple of Integer
        \tKey of cell that gets the reference
        ref_key: 3-tuple of Integer
        \tKey of cell that is referenced
        ref_type: Sting in ["absolute", "relative"]
        \tAn absolute or a relative reference is added

        """

        if ref_type == "absolute":
            code = self._get_absolute_reference(ref_key)

        elif ref_type == "relative":
            code = self._get_relative_reference(key, ref_key)

        else:
            raise ValueError(_('ref_type has to be "absolute" or "relative".'))

        old_code = self.grid.code_array(key)

        if old_code is None:
            old_code = u""

        if "S" in old_code and old_code[-1] == "]":
            old_code_left, __ = old_code.rsplit("S", 1)
            new_code = old_code_left + code
        else:
            new_code = old_code + code

        post_command_event(self.grid.main_window, self.EntryLineMsg,
                           text=new_code)

        return new_code  # For unit tests

    def _set_cell_attr(self, selection, table, attr):
        """Sets cell attr for key cell and mark grid content as changed

        Parameters
        ----------

        attr: dict
        \tContains cell attribute keys
        \tkeys in ["borderwidth_bottom", "borderwidth_right",
        \t"bordercolor_bottom", "bordercolor_right",
        \t"bgcolor", "textfont",
        \t"pointsize", "fontweight", "fontstyle", "textcolor", "underline",
        \t"strikethrough", "angle", "column-width", "row-height",
        \t"vertical_align", "justification", "frozen", "merge_area"]

        """

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        if selection is not None:
            cell_attributes = self.code_array.cell_attributes
            cell_attributes.undoable_append((selection, table, attr),
                                            mark_unredo=False)

    def set_attr(self, attr, value, selection=None, mark_unredo=True):
        """Sets attr of current selection to value"""

        if selection is None:
            selection = self.grid.selection

        if not selection:
            # Add current cell to selection so that it gets changed
            selection.cells.append(self.grid.actions.cursor[:2])

        attrs = {attr: value}

        table = self.grid.current_table

        # Change model
        self._set_cell_attr(selection, table, attrs)

        if mark_unredo:
            self.code_array.unredo.mark()

    def set_border_attr(self, attr, value, borders):
        """Sets border attribute by adjusting selection to borders

        Parameters
        ----------
        attr: String in ["borderwidth", "bordercolor"]
        \tBorder attribute that shall be changed
        value: wx.Colour or Integer
        \tAttribute value dependent on attribute type
        borders: Iterable over "top", "bottom", "left", "right", "inner"
        \tSpecifies to which borders of the selection the attr is applied

        """

        selection = self.grid.selection
        if not selection:
            selection.cells.append(self.grid.actions.cursor[:2])

        # determine selection for core cells and selection for border cells
        # Then apply according to inner and outer
        # A cell is inner iif it is not at the edge of the selection bbox

        if "inner" in borders:
            if "top" in borders:
                adj_selection = selection + (-1, 0)
                self.set_attr(attr + "_bottom", value, adj_selection,
                              mark_unredo=False)

            if "bottom" in borders:
                self.set_attr(attr + "_bottom", value, mark_unredo=False)

            if "left" in borders:
                adj_selection = selection + (0, -1)
                self.set_attr(attr + "_right", value, adj_selection,
                              mark_unredo=False)

            if "right" in borders:
                self.set_attr(attr + "_right", value, mark_unredo=False)

        else:
            # Adjust selection so that only bounding box edge is in selection
            bbox_tl, bbox_lr = selection.get_bbox()
            if "top" in borders:
                adj_selection = Selection([bbox_tl],
                                          [(bbox_tl[0], bbox_lr[1])],
                                          [], [], []) + (-1, 0)
                self.set_attr(attr + "_bottom", value, adj_selection,
                              mark_unredo=False)

            if "bottom" in borders:
                adj_selection = Selection([(bbox_lr[0], bbox_tl[1])],
                                          [bbox_lr], [], [], [])
                self.set_attr(attr + "_bottom", value, adj_selection,
                              mark_unredo=False)

            if "left" in borders:
                adj_selection = Selection([bbox_tl],
                                          [(bbox_lr[0], bbox_tl[1])],
                                          [], [], []) + (0, -1)
                self.set_attr(attr + "_right", value, adj_selection,
                              mark_unredo=False)

            if "right" in borders:
                adj_selection = Selection([(bbox_tl[0], bbox_lr[1])],
                                          [bbox_lr], [], [], [])
                self.set_attr(attr + "_right", value, adj_selection,
                              mark_unredo=False)

        self.code_array.unredo.mark()

    def toggle_attr(self, attr):
        """Toggles an attribute attr for current selection"""

        selection = self.grid.selection

        # Selection or single cell access?

        if selection:
            value = self.get_new_selection_attr_state(selection, attr)

        else:
            value = self.get_new_cell_attr_state(self.grid.actions.cursor,
                                                 attr)

        # Set the toggled value

        self.set_attr(attr, value, mark_unredo=False)

        self.code_array.unredo.mark()

    # Only cell attributes that can be toggled are contained

    def change_frozen_attr(self):
        """Changes frozen state of cell if there is no selection"""

        # Selections are not supported

        if self.grid.selection:
            statustext = _("Freezing selections is not supported.")
            post_command_event(self.main_window, self.StatusBarMsg,
                               text=statustext)

        cursor = self.grid.actions.cursor

        frozen = self.grid.code_array.cell_attributes[cursor]["frozen"]

        if frozen:
            # We have an frozen cell that has to be unfrozen

            # Delete frozen cache content
            self.grid.code_array.frozen_cache.pop(repr(cursor))

        else:
            # We have an non-frozen cell that has to be frozen

            # Add frozen cache content
            res_obj = self.grid.code_array[cursor]
            self.grid.code_array.frozen_cache[repr(cursor)] = res_obj

        # Set the new frozen state / code
        selection = Selection([], [], [], [], [cursor[:2]])
        self.set_attr("frozen", not frozen, selection=selection)

    def change_locked_attr(self):
        """Changes locked state of cell if there is no selection"""

        raise NotImplementedError

    def unmerge(self, unmerge_area, tab):
        """Unmerges all cells in unmerge_area"""

        top, left, bottom, right = unmerge_area
        selection = Selection([(top, left)], [(bottom, right)], [], [], [])
        attr = {"merge_area": None}

        self._set_cell_attr(selection, tab, attr)

    def merge(self, merge_area, tab):
        """Merges top left cell with all cells until bottom_right"""

        top, left, bottom, right = merge_area
        selection = Selection([(top, left)], [(bottom, right)], [], [], [])
        attr = {"merge_area": merge_area}

        self._set_cell_attr(selection, tab, attr)

    def merge_selected_cells(self, selection):
        """Merges or unmerges cells that are in the selection bounding box

        Parameters
        ----------
        selection: Selection object
        \tSelection for which attr toggle shall be returned

        """

        tab = self.grid.current_table

        # Get the selection bounding box
        bbox = selection.get_bbox()
        if bbox is None:
            row, col, tab = self.grid.actions.cursor
            (bb_top, bb_left), (bb_bottom, bb_right) = (row, col), (row, col)
        else:
            (bb_top, bb_left), (bb_bottom, bb_right) = bbox
        merge_area = bb_top, bb_left, bb_bottom, bb_right

        # Check if top-left cell is already merged
        cell_attributes = self.grid.code_array.cell_attributes
        tl_merge_area = cell_attributes[(bb_top, bb_left, tab)]["merge_area"]

        if tl_merge_area is None:
            self.merge(merge_area, tab)
        else:
            self.unmerge(tl_merge_area, tab)

    attr_toggle_values = {
        "fontweight": [wx.NORMAL, wx.BOLD],
        "fontstyle": [wx.NORMAL, wx.ITALIC],
        "underline": [False, True],
        "strikethrough": [False, True],
        "locked": [False, True],
        "vertical_align": ["top", "middle", "bottom"],
        "justification": ["left", "center", "right"],
        "frozen": [True, False],
    }

    def get_new_cell_attr_state(self, key, attr_key):
        """Returns new attr cell state for toggles

        Parameters
        ----------
        key: 3-Tuple
        \tCell for which attr toggle shall be returned
        attr_key: Hashable
        \tAttribute key

        """

        cell_attributes = self.grid.code_array.cell_attributes
        attr_values = self.attr_toggle_values[attr_key]

        # Map attr_value to next attr_value
        attr_map = dict(zip(attr_values, attr_values[1:] + attr_values[:1]))

        # Return next value from attr_toggle_values value list

        return attr_map[cell_attributes[key][attr_key]]

    def get_new_selection_attr_state(self, selection, attr_key):
        """Toggles new attr selection state and returns it

        Parameters
        ----------
        selection: Selection object
        \tSelection for which attr toggle shall be returned
        attr_key: Hashable
        \tAttribute key

        """

        cell_attributes = self.grid.code_array.cell_attributes
        attr_values = self.attr_toggle_values[attr_key]

        # Map attr_value to next attr_value
        attr_map = dict(zip(attr_values, attr_values[1:] + attr_values[:1]))

        selection_attrs = \
            (attr for attr in cell_attributes if attr[0] == selection)

        attrs = {}
        for selection_attr in selection_attrs:
            attrs.update(selection_attr[2])

        if attr_key in attrs:
            return attr_map[attrs[attr_key]]

        else:
            # Default next value
            return self.attr_toggle_values[attr_key][1]

    def refresh_frozen_cell(self, key):
        """Refreshes a frozen cell"""

        code = self.grid.code_array(key)
        result = self.grid.code_array._eval_cell(key, code)
        self.grid.code_array.frozen_cache[repr(key)] = result

    def refresh_selected_frozen_cells(self, selection=None):
        """Refreshes content of frozen cells that are currently selected

        If there is no selection, the cell at the cursor is updated.

        Parameters
        ----------
        selection: Selection, defaults to None
        \tIf not None then use this selection instead of the grid selection

        """

        if selection is None:
            selection = self.grid.selection

        # Add cursor to empty selection

        if not selection:
            selection.cells.append(self.grid.actions.cursor[:2])

        cell_attributes = self.grid.code_array.cell_attributes

        refreshed_keys = []

        for attr_selection, tab, attr_dict in cell_attributes:
            if tab == self.grid.actions.cursor[2] and \
               "frozen" in attr_dict and attr_dict["frozen"]:
                # Only single cells are allowed for freezing
                skey = attr_selection.cells[0]
                if skey in selection:
                    key = tuple(list(skey) + [tab])
                    if key not in refreshed_keys and \
                       cell_attributes[key]["frozen"]:
                        self.refresh_frozen_cell(key)
                        refreshed_keys.append(key)

        cell_attributes._attr_cache.clear()

########NEW FILE########
__FILENAME__ = _main_window_actions
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------


"""
_main_window_actions.py
=======================

Module for main window level actions.
All non-trivial functionality that results from main window actions
and belongs to the application as whole (in contrast to the grid only)
goes here.

Provides:
---------
  1. ExchangeActions: Actions for foreign format import and export
  2. PrintActions: Actions for printing
  3. ClipboardActions: Actions which affect the clipboard
  4. MacroActions: Actions which affect macros
  5. HelpActions: Actions for getting help
  6. AllMainWindowActions: All main window actions as a bundle

"""

import ast
import base64
import bz2
import os

import wx
import wx.html

from matplotlib.figure import Figure

import src.lib.i18n as i18n
from src.sysvars import get_help_path

from src.config import config
from src.lib.__csv import CsvInterface, TxtGenerator
from src.lib.charts import fig2bmp, fig2x
from src.gui._printout import PrintCanvas, Printout
from src.gui._events import post_command_event, EventMixin

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


class Actions(EventMixin):
    """Actions base class"""

    def __init__(self, grid):
        self.main_window = grid.main_window
        self.grid = grid
        self.code_array = grid.code_array


class ExchangeActions(Actions):
    """Actions for foreign format import and export"""

    def _import_csv(self, path):
        """CSV import workflow"""

        # If path is not set, do nothing
        if not path:
            return

        # Get csv info

        try:
            dialect, has_header, digest_types, encoding = \
                self.main_window.interfaces.get_csv_import_info(path)

        except IOError:
            msg = _("Error opening file {filepath}.").format(filepath=path)
            post_command_event(self.main_window, self.StatusBarMsg, text=msg)
            return

        except TypeError:
            return  # Import is aborted or empty

        return CsvInterface(self.main_window,
                            path, dialect, digest_types, has_header, encoding)

    def _import_txt(self, path):
        """Whitespace-delimited txt import workflow. This should be fast."""

        return TxtGenerator(self.main_window, path)

    def import_file(self, filepath, filterindex):
        """Imports external file

        Parameters
        ----------

        filepath: String
        \tPath of import file
        filterindex: Integer
        \tIndex for type of file, 0: csv, 1: tab-delimited text file

        """

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        if filterindex == 0:
            # CSV import option choice
            return self._import_csv(filepath)
        elif filterindex == 1:
            # TXT import option choice
            return self._import_txt(filepath)
        else:
            msg = _("Unknown import choice {choice}.")
            msg = msg.format(choice=filterindex)
            short_msg = _('Error reading CSV file')

            self.main_window.interfaces.display_warning(msg, short_msg)

    def _export_csv(self, filepath, data, preview_data):
        """CSV export of code_array results

        Parameters
        ----------
        filepath: String
        \tPath of export file
        data: Object
        \tCode array result object slice, i. e. one object or iterable of
        \tsuch objects

        """

        # Get csv info

        csv_info = \
            self.main_window.interfaces.get_csv_export_info(preview_data)

        if csv_info is None:
            return

        try:
            dialect, digest_types, has_header = csv_info
        except TypeError:
            return

        # Export CSV file

        csv_interface = CsvInterface(self.main_window, filepath, dialect,
                                     digest_types, has_header)

        try:
            csv_interface.write(data)

        except IOError, err:
            msg = _("The file {filepath} could not be fully written\n \n"
                    "Error message:\n{msg}")
            msg = msg.format(filepath=filepath, msg=err)
            short_msg = _('Error writing CSV file')
            self.main_window.interfaces.display_warning(msg, short_msg)

    def _export_figure(self, filepath, data, format):
        """Export of single cell that contains a matplotlib figure

        Parameters
        ----------
        filepath: String
        \tPath of export file
        data: Matplotlib Figure
        \tMatplotlib figure that is eported
        format: String in ["png", "pdf", "ps", "eps", "svg"]

        """

        formats = ["svg", "eps", "ps", "pdf", "png"]
        assert format in formats

        data = fig2x(data, format)

        try:
            outfile = open(filepath, "wb")
            outfile.write(data)

        except IOError, err:
            msg = _("The file {filepath} could not be fully written\n \n"
                    "Error message:\n{msg}")
            msg = msg.format(filepath=filepath, msg=err)
            short_msg = _('Error writing SVG file')
            self.main_window.interfaces.display_warning(msg, short_msg)

        finally:
            outfile.close()

    def export_file(self, filepath, filterindex, data, preview_data=None):
        """Export data for other applications

        Parameters
        ----------
        filepath: String
        \tPath of export file
        filterindex: Integer
        \tIndex of the import filter
        data: Object
        \tCode array result object slice, i. e. one object or iterable of
        \tsuch objects

        """

        formats = ["csv", "svg", "eps", "ps", "pdf", "png"]

        if filterindex == 0:
            self._export_csv(filepath, data, preview_data=preview_data)

        elif filterindex >= 1:
            self._export_figure(filepath, data, formats[filterindex])


class PrintActions(Actions):
    """Actions for printing"""

    def print_preview(self, print_area, print_data):
        """Launch print preview"""

        # Create the print canvas
        canvas = PrintCanvas(self.main_window, self.grid, print_area)

        printout = Printout(canvas)
        printout2 = Printout(canvas)

        preview = wx.PrintPreview(printout, printout2, print_data)

        if not preview.Ok():
            print "Printout preview failed.\n"
            return

        pfrm = wx.PreviewFrame(preview, self.main_window, _("Print preview"))

        pfrm.Initialize()
        pfrm.SetPosition(self.main_window.GetPosition())
        pfrm.SetSize(self.main_window.GetSize())
        pfrm.Show(True)

    def printout(self, print_area, print_data):
        """Print out print area

        See:
        http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3471083

        """

        pdd = wx.PrintDialogData(print_data)
        printer = wx.Printer(pdd)

        # Create the print canvas
        canvas = PrintCanvas(self.main_window, self.grid, print_area)

        printout = Printout(canvas)

        if printer.Print(self.main_window, printout, True):
            self.print_data = \
                wx.PrintData(printer.GetPrintDialogData().GetPrintData())

        printout.Destroy()
        canvas.Destroy()


class ClipboardActions(Actions):
    """Actions which affect the clipboard"""

    def cut(self, selection):
        """Cuts selected cells and returns data in a tab separated string

        Parameters
        ----------

        selection: Selection object
        \tSelection of cells in current table that shall be copied

        """

        # Call copy with delete flag

        return self.copy(selection, delete=True)

    def _get_code(self, key):
        """Returns code for given key (one cell)

        Parameters
        ----------

        key: 3-Tuple of Integer
        \t Cell key

        """

        data = self.grid.code_array(key)
        self.grid.code_array.result_cache.clear()

        return data

    def copy(self, selection, getter=None, delete=False):
        """Returns code from selection in a tab separated string

        Cells that are not in selection are included as empty.

        Parameters
        ----------

        selection: Selection object
        \tSelection of cells in current table that shall be copied
        getter: Function, defaults to _get_code
        \tGetter function for copy content
        delete: Bool
        \tDeletes all cells inside selection

        """

        if getter is None:
            getter = self._get_code

        tab = self.grid.current_table

        selection_bbox = selection.get_bbox()

        if not selection_bbox:
            # There is no selection
            bb_top, bb_left = self.grid.actions.cursor[:2]
            bb_bottom, bb_right = bb_top, bb_left
        else:
            replace_none = self.main_window.grid.actions._replace_bbox_none
            (bb_top, bb_left), (bb_bottom, bb_right) = \
                replace_none(selection.get_bbox())

        data = []

        for __row in xrange(bb_top, bb_bottom + 1):
            data.append([])

            for __col in xrange(bb_left, bb_right + 1):
                # Only copy content if cell is in selection or
                # if there is no selection

                if (__row, __col) in selection or not selection_bbox:
                    content = getter((__row, __col, tab))

                    # Delete cell if delete flag is set

                    if delete:
                        try:
                            self.grid.code_array.pop((__row, __col, tab))

                        except KeyError:
                            pass

                    # Store data

                    if content is None:
                        data[-1].append(u"")

                    else:
                        data[-1].append(content)

                else:
                    data[-1].append(u"")

        return "\n".join("\t".join(line) for line in data)

    def _get_result_string(self, key):
        """Returns unicode string of result for given key (one cell)

        Parameters
        ----------

        key: 3-Tuple of Integer
        \t Cell key

        """

        row, col, tab = key

        result_obj = self.grid.code_array[row, col, tab]

        try:
            # Numpy object arrays are converted because of numpy repr bug
            result_obj = result_obj.tolist()

        except AttributeError:
            pass

        return unicode(result_obj)

    def copy_result(self, selection):
        """Returns result

        If selection consists of one cell only and result is a bitmap then
        the bitmap is returned.
        Otherwise the method returns string representations of the result
        for the given selection in a tab separated string.

        """

        bbox = selection.get_bbox()

        if not bbox:
            # There is no selection
            bb_top, bb_left = self.grid.actions.cursor[:2]
            bb_bottom, bb_right = bb_top, bb_left
        else:
            # Thereis a selection
            (bb_top, bb_left), (bb_bottom, bb_right) = bbox

        if bb_top == bb_bottom and bb_left == bb_right:
            # We have  a single selection

            tab = self.grid.current_table
            result = self.grid.code_array[bb_top, bb_left, tab]

            if isinstance(result, wx._gdi.Bitmap):
                # The result is a wx.Bitmap. Return it.
                return result

            elif isinstance(result, Figure):
                # The result is a matplotlib figure
                # Therefore, a wx.Bitmap is returned
                key = bb_top, bb_left, tab
                rect = self.grid.CellToRect(bb_top, bb_left)
                merged_rect = self.grid.grid_renderer.get_merged_rect(
                    self.grid, key, rect)
                dpi = float(wx.ScreenDC().GetPPI()[0])
                zoom = self.grid.grid_renderer.zoom

                return fig2bmp(result, merged_rect.width, merged_rect.height,
                               dpi, zoom)

        # So we have result strings to be returned
        getter = self._get_result_string

        return self.copy(selection, getter=getter)

    def img2code(self, key, img):
        """Pastes wx.Image into single cell"""

        code_template = \
            "wx.ImageFromData({width}, {height}, " + \
            "bz2.decompress(base64.b64decode('{data}'))).ConvertToBitmap()"

        code_alpha_template = \
            "wx.ImageFromDataWithAlpha({width}, {height}, " + \
            "bz2.decompress(base64.b64decode('{data}')), " + \
            "bz2.decompress(base64.b64decode('{alpha}'))).ConvertToBitmap()"

        data = base64.b64encode(bz2.compress(img.GetData(), 9))

        if img.HasAlpha():
            alpha = base64.b64encode(bz2.compress(img.GetAlphaData(), 9))
            code_str = code_alpha_template.format(
                width=img.GetWidth(), height=img.GetHeight(),
                data=data, alpha=alpha)
        else:
            code_str = code_template.format(width=img.GetWidth(),
                                            height=img.GetHeight(), data=data)

        return code_str

    def bmp2code(self, key, bmp):
        """Pastes wx.Bitmap into single cell"""

        return self.img2code(key, bmp.ConvertToImage())

    def _get_paste_data_gen(self, key, data):
        """Generator for paste data

        Can be used in grid.actions.paste

        """

        if type(data) is wx._gdi.Bitmap:
            code_str = self.bmp2code(key, data)
            return [[code_str]]
        else:
            return (line.split("\t") for line in data.split("\n"))

    def paste(self, key, data):
        """Pastes data into grid

        Parameters
        ----------

        key: 2-Tuple of Integer
        \tTop left cell
        data: String or wx.Bitmap
        \tTab separated string of paste data
        \tor paste data image
        """

        data_gen = self._get_paste_data_gen(key, data)

        self.grid.actions.paste(key[:2], data_gen, freq=1000)

        self.main_window.grid.ForceRefresh()

    def _get_pasteas_data(self, dim, obj):
        """Returns list of lists of obj than has dimensionality dim

        Parameters
        ----------
        dim: Integer
        \tDimensionality of obj
        obj: Object
        \tIterable object of dimensionality dim

        """

        if dim == 0:
            return [[repr(obj)]]
        elif dim == 1:
            return [[repr(o)] for o in obj]
        elif dim == 2:
            return [map(repr, o) for o in obj]

    def paste_as(self, key, data):
        """Paste and transform data

        Data may be given as a Python code as well as a tab separated
        multi-line strings similar to paste.

        """

        def error_msg(err):
            msg = _("Error evaluating data: ") + str(err)
            post_command_event(self.main_window, self.StatusBarMsg, text=msg)

        interfaces = self.main_window.interfaces
        key = self.main_window.grid.actions.cursor

        try:
            obj = ast.literal_eval(data)

        except (SyntaxError, AttributeError):
            # This is no Python code so te try to interpret it as paste data
            try:
                obj = [map(ast.literal_eval, line.split("\t"))
                       for line in data.split("\n")]

            except Exception, err:
                # This must just be text.
                try:
                    obj = [line.split('\t') for line in data.split('\n')]
                except Exception, err:
                    # Now I really have no idea
                    error_msg(err)
                    return

        except ValueError, err:
            error_msg(err)
            return

        parameters = interfaces.get_pasteas_parameters_from_user(obj)

        paste_data = self._get_pasteas_data(parameters["dim"], obj)

        if parameters["transpose"]:
            paste_data = zip(*paste_data)

        self.main_window.grid.actions.paste(key, paste_data, freq=1000)


class MacroActions(Actions):
    """Actions which affect macros"""

    def replace_macros(self, macros):
        """Replaces macros"""

        self.grid.code_array.macros = macros

    def execute_macros(self):
        """Executes macros and marks grid as changed"""

        # Mark content as changed
        post_command_event(self.main_window, self.ContentChangedMsg,
                           changed=True)

        (result, err) = self.grid.code_array.execute_macros()

        # Post event to macro dialog
        post_command_event(self.main_window, self.MacroErrorMsg,
                           msg=result, err=err)

    def open_macros(self, filepath):
        """Loads macros from file and marks grid as changed

        Parameters
        ----------
        filepath: String
        \tPath to macro file

        """

        try:
            wx.BeginBusyCursor()
            self.main_window.grid.Disable()

            with open(filepath) as macro_infile:
                # Enter safe mode
                self.main_window.grid.actions.enter_safe_mode()
                post_command_event(self.main_window, self.SafeModeEntryMsg)

                # Mark content as changed
                post_command_event(self.main_window, self.ContentChangedMsg,
                                   changed=True)

                macrocode = macro_infile.read()

                self.grid.code_array.macros += "\n" + macrocode.strip("\n")

        except IOError:
            msg = _("Error opening file {filepath}.").format(filepath=filepath)
            post_command_event(self.main_window, self.StatusBarMsg, text=msg)

            return False

        finally:
            self.main_window.grid.Enable()
            wx.EndBusyCursor()

        # Mark content as changed
        try:
            post_command_event(self.main_window, self.ContentChangedMsg,
                               changed=True)
        except TypeError:
            # The main window does not exist any more
            pass

    def save_macros(self, filepath, macros):
        """Saves macros to file

        Parameters
        ----------
        filepath: String
        \tPath to macro file
        macros: String
        \tMacro code

        """

        io_error_text = _("Error writing to file {filepath}.")
        io_error_text = io_error_text.format(filepath=filepath)

        # Make sure that old macro file does not get lost on abort save
        tmpfile = filepath + "~"

        try:
            wx.BeginBusyCursor()
            self.main_window.grid.Disable()
            with open(tmpfile, "w") as macro_outfile:
                macro_outfile.write(macros)

            # Move save file from temp file to filepath
            try:
                os.rename(tmpfile, filepath)

            except OSError:
                # No tmp file present
                pass

        except IOError:
            try:
                post_command_event(self.main_window, self.StatusBarMsg,
                                   text=io_error_text)
            except TypeError:
                # The main window does not exist any more
                pass

            return False

        finally:
            self.main_window.grid.Enable()
            wx.EndBusyCursor()


class HelpActions(Actions):
    """Actions for getting help"""

    def launch_help(self, helpname, filename):
        """Generic help launcher

        Launches HTMLWindow that shows content of filename
        or the Internet page with the filename url

        Parameters
        ----------

        filename: String
        \thtml file or url

        """

        # Set up window

        position = config["help_window_position"]
        size = config["help_window_size"]

        self.help_window = wx.Frame(self.main_window, -1,
                                    helpname, position, size)
        self.help_htmlwindow = wx.html.HtmlWindow(self.help_window, -1,
                                                  (0, 0), size)

        self.help_window.Bind(wx.EVT_MOVE, self.OnHelpMove)
        self.help_window.Bind(wx.EVT_SIZE, self.OnHelpSize)
        self.help_htmlwindow.Bind(wx.EVT_RIGHT_DOWN, self.OnHelpBack)

        # Get help data
        current_path = os.getcwd()
        os.chdir(get_help_path())

        try:
            if os.path.isfile(filename):
                self.help_htmlwindow.LoadFile(filename)

            else:
                self.help_htmlwindow.LoadPage(filename)

        except IOError:
            self.help_htmlwindow.LoadPage(filename)

        # Show tutorial window

        self.help_window.Show()

        os.chdir(current_path)

    def OnHelpBack(self, event):
        """Goes back apage if possible"""

        if self.help_htmlwindow.HistoryCanBack():
            self.help_htmlwindow.HistoryBack()

    def OnHelpMove(self, event):
        """Help window move event handler stores position in config"""

        position = event.GetPosition()
        config["help_window_position"] = repr((position.x, position.y))

        event.Skip()

    def OnHelpSize(self, event):
        """Help window size event handler stores size in config"""

        size = event.GetSize()
        config["help_window_size"] = repr((size.width, size.height))

        event.Skip()


class AllMainWindowActions(ExchangeActions, PrintActions,
                           ClipboardActions, MacroActions, HelpActions):
    """All main window actions as a bundle"""

    pass

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
pyspread config file
====================

"""

from ast import literal_eval

import wx

##from sysvars import get_color, get_font_string

VERSION = "0.2.8"


class DefaultConfig(object):
    """Contains default config for starting pyspread without resource file"""

    def __init__(self):
        # Config file version
        # -------------------

        self.config_version = VERSION

        # Cell calculation timeout in s
        # -----------------------------
        self.timeout = repr(10)

        # User defined paths
        # ------------------

        standardpaths = wx.StandardPaths.Get()
        self.work_path = standardpaths.GetDocumentsDir()

        # Window configuration
        # --------------------

        self.window_position = "(10, 10)"
        self.window_size = repr((wx.GetDisplaySize()[0] * 9 / 10,
                                 wx.GetDisplaySize()[1] * 9 / 10))
        self.window_layout = "''"
        self.icon_theme = "'Tango'"

        self.help_window_position = repr((wx.GetDisplaySize()[0] * 7 / 10, 15))
        self.help_window_size = repr((wx.GetDisplaySize()[0] * 3 / 10,
                                      wx.GetDisplaySize()[1] * 7 / 10))

        # Grid configuration
        # ------------------

        self.grid_rows = "1000"
        self.grid_columns = "100"
        self.grid_tables = "3"

        self.max_unredo = "5000"

        self.timer_interval = "1000"

        # Maximum result length in a cell in characters
        self.max_result_length = "1000"

        # Colors
        self.grid_color = repr(wx.SYS_COLOUR_GRAYTEXT)
        self.selection_color = repr(wx.SYS_COLOUR_HIGHLIGHT)
        self.background_color = repr(wx.SYS_COLOUR_WINDOW)
        self.text_color = repr(wx.SYS_COLOUR_WINDOWTEXT)
        self.freeze_color = repr(wx.SYS_COLOUR_HIGHLIGHT)

        # Fonts

        self.font = repr(wx.SYS_DEFAULT_GUI_FONT)

        # Default cell font size

        self.font_default_sizes = "[6, 8, 10, 12, 14, 16, 18, 20, 24, 28, 32]"

        # Zoom

        self.minimum_zoom = "0.25"
        self.maximum_zoom = "8.0"

        # Increase and decrease factor on zoom in and zoom out
        self.zoom_factor = "0.05"

        # GPG parameters
        # --------------

        #self.gpg_key_uid = repr('')  # Deprecated
        self.gpg_key_fingerprint = repr('')

        # CSV parameters for import and export
        # ------------------------------------

        # Number of bytes for the sniffer (should be larger than 1st+2nd line)
        self.sniff_size = "65536"

        # Maximum number of characters in wx.TextCtrl
        self.max_textctrl_length = "65534"


class Config(object):
    """Configuration class for the application pyspread"""

    # Only keys in default_config are config keys

    def __init__(self, defaults=None):
        self.config_filename = "pyspreadrc"

        # The current version of pyspread
        self.version = VERSION

        if defaults is None:
            self.defaults = DefaultConfig()

        else:
            self.defaults = defaults()

        self.data = DefaultConfig()

        self.cfg_file = wx.Config(self.config_filename)

        # Config keys to be resetted to default value on version upgrades
        self.reset_on_version_change = ["window_layout"]

        self.load()

    def __getitem__(self, key):
        """Main config element read access"""

        if key == "version":
            return self.version

        try:
            return literal_eval(getattr(self.data, key))

        except KeyError:
            # Probably, there is a problem with the config file --> use default
            setattr(self.data, key, getattr(DefaultConfig(), key))

            return literal_eval(getattr(self.data, key))

    def __setitem__(self, key, value):
        """Main config element write access"""

        setattr(self.data, key, value)

    def load(self):
        """Loads configuration file"""

        # Config files prior to 0.2.4 dor not have config version keys
        old_config = not self.cfg_file.Exists("config_version")

        # Reset data
        self.data.__dict__.update(self.defaults.__dict__)

        for key in self.defaults.__dict__:
            if self.cfg_file.Exists(key):
                setattr(self.data, key, self.cfg_file.Read(key))

        # Reset keys that should be reset on version upgrades
        if old_config or self.version != self.data.config_version:
            for key in self.reset_on_version_change:
                setattr(self.data, key, getattr(DefaultConfig(), key))
            self.data.config_version = self.version

        # Delete gpg_key_uid and insert fingerprint key

        if hasattr(self.data, "gpg_key_uid"):
            oldkey = "gpg_key_uid"
            delattr(self.data, oldkey)
            newkey = "gpg_key_fingerprint"
            setattr(self.data, newkey, getattr(DefaultConfig(), newkey))

    def save(self):
        """Saves configuration file"""

        for key in self.defaults.__dict__:
            data = getattr(self.data, key)

            self.cfg_file.Write(key, data)

config = Config()

########NEW FILE########
__FILENAME__ = icons
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
icons
=====

Provides:
---------
  1) GtkArtProvider: Provides stock and custom icons
  2) Icons: Provides pyspread's icons

"""

import wx

from src.sysvars import get_program_path


class GtkArtProvider(wx.ArtProvider):
    """Provides extra icons in addition to the standard ones

    Used only by Icons class

    """

    def __init__(self, theme, icon_size):

        wx.ArtProvider.__init__(self)

        theme_path, icon_path, action_path, toggle_path = \
            self.get_paths(theme, icon_size)

        self.extra_icons = {
            "PyspreadLogo": theme_path + "pyspread.png",
            "EditCopyRes": action_path + "edit-copy-results.png",
            "FormatTextBold": action_path + "format-text-bold.png",
            "FormatTextItalic": action_path + "format-text-italic.png",
            "FormatTextUnderline": action_path +
                                            "format-text-underline.png",
            "FormatTextStrikethrough": action_path +
                                            "format-text-strikethrough.png",
            "JustifyRight": action_path + "format-justify-right.png",
            "JustifyCenter": action_path + "format-justify-center.png",
            "JustifyLeft": action_path + "format-justify-left.png",
            "AlignTop": action_path + "format-text-aligntop.png",
            "AlignCenter": action_path + "format-text-aligncenter.png",
            "AlignBottom": action_path + "format-text-alignbottom.png",
            "Freeze": action_path + "frozen_small.png",
            "Lock": action_path + "lock.png",
            "Merge": action_path + "format-merge-table-cells.png",
            "AllBorders": toggle_path + "border_all.xpm",
            "LeftBorders": toggle_path + "border_left.xpm",
            "RightBorders": toggle_path + "border_right.xpm",
            "TopBorders": toggle_path + "border_top.xpm",
            "BottomBorders": toggle_path + "border_bottom.xpm",
            "InsideBorders": toggle_path + "border_inside.xpm",
            "OutsideBorders": toggle_path + "border_outside.xpm",
            "TopBottomBorders": toggle_path + "border_top_n_bottom.xpm",
            "MATCH_CASE": toggle_path + "aA.png",
            "REG_EXP": toggle_path + "regex.png",
            "WHOLE_WORD": toggle_path + "wholeword.png",
            "InsertBitmap": action_path + "insert_bmp.png",
            "LinkBitmap": action_path + "link_bmp.png",
            "InsertChart": action_path + "chart_line.png",
            "plot": action_path + "chart_line.png",  # matplotlib plot chart
            "bar": action_path + "chart_column.png",  # matplotlib bar chart
            "boxplot": action_path + "chart_boxplot.png",  # matplotlib boxplot
            "pie": action_path + "chart_pie.png",  # matplotlib pie chart
            "hist": action_path + "chart_histogram.png",  # matplotlib hist
            "annotate": action_path + "chart_annotate.png",  # matplotlib
            "contour": action_path + "chart_contour.png",  # matplotlib
            "Sankey": action_path + "chart_sankey.png",  # matplotlib
            "safe_mode": icon_path + "status/dialog-warning.png",
            "SortAscending": action_path + "edit-sort-ascending.png",
            "SortDescending": action_path + "edit-sort-descending.png",
        }

    def get_paths(self, theme, icon_size):
        """Returns tuple of theme, icon, action and toggle paths"""

        _size_str = "x".join(map(str, icon_size))

        theme_path = get_program_path() + "share/icons/"
        icon_path = theme_path + theme + "/" + _size_str + "/"
        action_path = icon_path + "actions/"
        toggle_path = icon_path + "toggles/"

        return theme_path, icon_path, action_path, toggle_path

    def CreateBitmap(self, artid, client, size):
        """Adds custom images to Artprovider"""

        if artid in self.extra_icons:
            return wx.Bitmap(self.extra_icons[artid], wx.BITMAP_TYPE_ANY)

        else:
            return wx.ArtProvider.GetBitmap(artid, client, size)


class WindowsArtProvider(GtkArtProvider):
    """Provides extra icons for the Windows platform"""

    def __init__(self, theme, icon_size):
        GtkArtProvider.__init__(self, theme, icon_size)

        theme_path, icon_path, action_path, toggle_path = \
            self.get_paths(theme, icon_size)

        windows_icons = {
            wx.ART_NEW: action_path + "document-new.png",
            wx.ART_FILE_OPEN: action_path + "document-open.png",
            wx.ART_FILE_SAVE: action_path + "document-save.png",
            wx.ART_FILE_SAVE_AS: action_path + "document-save-as.png",
            wx.ART_PRINT: action_path + "document-print.png",
            wx.ART_GO_UP: action_path + "go-up.png",
            wx.ART_GO_DOWN: action_path + "go-down.png",
            wx.ART_COPY: action_path + "edit-copy.png",
            wx.ART_CUT: action_path + "edit-cut.png",
            wx.ART_PASTE: action_path + "edit-paste.png",
            wx.ART_UNDO: action_path + "edit-undo.png",
            wx.ART_REDO: action_path + "edit-redo.png",
            wx.ART_FIND: action_path + "edit-find.png",
            wx.ART_FIND_AND_REPLACE: action_path + "edit-find-replace.png",

        }

        self.extra_icons.update(windows_icons)


class Icons(object):
    """Provides icons for pyspread

    Parameters
    ----------
    icon_set: Integer, defaults to wx.ART_OTHER
    \tIcon set as defined by wxArtProvider
    icon_theme: String, defaults to "Tango"
    \tIcon theme
    icon_size: 2-Tuple of Integer, defaults to (24, 24)
    \tI=Size of icon bitmaps

    """

    theme = "Tango"

    icon_size = (24, 24)
    icon_set = wx.ART_OTHER

    icons = {
        "FileNew": wx.ART_NEW,
        "FileOpen": wx.ART_FILE_OPEN,
        "FileSave": wx.ART_FILE_SAVE,
        "FilePrint": wx.ART_PRINT,
        "EditCut": wx.ART_CUT,
        "EditCopy": wx.ART_COPY,
        "EditPaste": wx.ART_PASTE,
        "Undo": wx.ART_UNDO,
        "Redo": wx.ART_REDO,
        "Find": wx.ART_FIND,
        "FindReplace": wx.ART_FIND_AND_REPLACE,
        "GoUp": wx.ART_GO_UP,
        "GoDown": wx.ART_GO_DOWN,
        "Add": wx.ART_ADD_BOOKMARK,
        "Remove": wx.ART_DEL_BOOKMARK,
    }

    def __init__(self, icon_set=wx.ART_OTHER, icon_theme="Tango",
                 icon_size=(24, 24)):

        self.icon_set = icon_set
        self.icon_theme = icon_theme
        self.icon_size = icon_size

        if "__WXMSW__" in wx.PlatformInfo:
            # Windows lacks good quality stock items
            wx.ArtProvider.Push(WindowsArtProvider(icon_theme, icon_size))
        else:
            # Use the platform generic themed icons instead
            wx.ArtProvider.Push(GtkArtProvider(icon_theme, icon_size))

    def __getitem__(self, icon_name):
        """Returns by bitmap

        Parameters
        ----------
        icon_name: String
        \tString identifier of the icon.

        """

        if icon_name in self.icons:
            icon_name = self.icons[icon_name]

        return wx.ArtProvider.GetBitmap(icon_name, self.icon_set,
                                        self.icon_size)

icons = Icons()

########NEW FILE########
__FILENAME__ = _chart_dialog
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread. If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
_chart_dialog
=============

Chart creation dialog with interactive matplotlib chart widget

Provides
--------

* ChartDialog: Chart dialog class

"""

# Architecture
# ------------
#
# Create widgets <Type>Editor for each type
# types are: bool, int, str, color, iterable, marker_style, line_style
# Each widget has a get_code method and a set_code method
#
# A SeriesBoxPanel is defined by:
# [panel_label, (matplotlib_key, widget, label, tooltip), ...]
#
# A <Seriestype>AttributesPanel(SeriesPanelBase) is defined by:
# [seriestype_key, SeriesBoxPanel, ...]
# It is derived from SeriesBasePanel and provides a widgets attribute
#
# SeriesPanelBase provides a method
# __iter__ that yields (key, code) for each widget
#
# SeriesPanel provides a TreeBook of series types
# It is defined by:
# [(seriestype_key, seriestype_label, seriestype_image,
#                                     <Seriestype>AttributesPanel), ...]
#
# AllSeriesPanel provides a flatnotebook with one tab per series
#
# FigureAttributesPanel is equivalent to a <Seriestype>AttributesPanel
#
# FigurePanel provides a matplotlib chart drawing
#
# ChartDialog provides FigureAttributesPanel, Flatnotebook of SeriesPanels,
#                      FigurePanel

from copy import copy

import wx
import matplotlib
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
import wx.lib.colourselect as csel
from wx.lib.intctrl import IntCtrl, EVT_INT
import wx.lib.agw.flatnotebook as fnb

from _widgets import LineStyleComboBox, MarkerStyleComboBox
from _widgets import CoordinatesComboBox
from _events import post_command_event, ChartDialogEventMixin
import src.lib.i18n as i18n
import src.lib.charts as charts
from src.lib.parsers import color2code, code2color, parse_dict_strings
from src.lib.parsers import unquote_string
from icons import icons
from sysvars import get_default_font, get_color

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


# --------------
# Editor widgets
# --------------


class BoolEditor(wx.CheckBox, ChartDialogEventMixin):
    """Editor widget for bool values"""

    def __init__(self, *args, **kwargs):
        wx.CheckBox.__init__(self, *args, **kwargs)

        self.__bindings()

    def __bindings(self):
        """Binds events to handlers"""

        self.Bind(wx.EVT_CHECKBOX, self.OnChecked)

    def get_code(self):
        """Returns '0' or '1'"""

        return self.GetValue()

    def set_code(self, code):
        """Sets widget from code string

        Parameters
        ----------
        code: String
        \tCode representation of bool value

        """

        # If string representations of False are in the code
        # then it has to be converted explicitly

        if code == "False" or code == "0":
            code = False

        self.SetValue(bool(code))

    # Properties

    code = property(get_code, set_code)

    # Handlers

    def OnChecked(self, event):
        """Check event handler"""

        post_command_event(self, self.DrawChartMsg)


class IntegerEditor(IntCtrl, ChartDialogEventMixin):
    """Editor widget for integer values"""

    def __init__(self, *args, **kwargs):
        IntCtrl.__init__(self, *args, **kwargs)

        self.__bindings()

    def __bindings(self):
        """Binds events to handlers"""

        self.Bind(EVT_INT, self.OnInt)

    def get_code(self):
        """Returns string representation of Integer"""

        return unicode(self.GetValue())

    def set_code(self, code):
        """Sets widget from code string

        Parameters
        ----------
        code: String
        \tCode representation of integer value

        """

        self.SetValue(int(code))

    # Properties

    code = property(get_code, set_code)

    # Handlers

    def OnInt(self, event):
        """Check event handler"""

        post_command_event(self, self.DrawChartMsg)


class StringEditor(wx.TextCtrl, ChartDialogEventMixin):
    """Editor widget for string values"""

    def __init__(self, *args, **kwargs):
        wx.TextCtrl.__init__(self, *args, **kwargs)

        self.__bindings()

    def __bindings(self):
        """Binds events to handlers"""

        self.Bind(wx.EVT_TEXT, self.OnText)

    def get_code(self):
        """Returns code representation of value of widget"""

        return self.GetValue()

    def set_code(self, code):
        """Sets widget from code string

        Parameters
        ----------
        code: String
        \tCode representation of widget value

        """

        self.SetValue(code)

    # Properties

    code = property(get_code, set_code)

    # Handlers

    def OnText(self, event):
        """Text entry event handler"""

        post_command_event(self, self.DrawChartMsg)


class TextEditor(wx.Panel, ChartDialogEventMixin):
    """Editor widget for text objects

    The editor provides a taxt ctrl, a font button and a color chooser

    """

    style_wx2mpl = {
        wx.FONTSTYLE_ITALIC: "italic",
        wx.FONTSTYLE_NORMAL: "normal",
        wx.FONTSTYLE_SLANT: "oblique",
    }

    style_mpl2wx = dict((v, k) for k, v in style_wx2mpl.iteritems())

    weight_wx2mpl = {
        wx.FONTWEIGHT_BOLD: "bold",
        wx.FONTWEIGHT_NORMAL: "normal",
        wx.FONTWEIGHT_LIGHT: "light",
    }

    weight_mpl2wx = dict((v, k) for k, v in weight_wx2mpl.iteritems())

    def __init__(self, *args, **kwargs):
        wx.Panel.__init__(self, *args, **kwargs)

        self.textctrl = wx.TextCtrl(self, -1)
        self.fontbutton = wx.Button(self, -1, label=u"\u2131", size=(24, 24))
        self.colorselect = csel.ColourSelect(self, -1, size=(24, 24))

        self.value = u""

        self.chosen_font = None

        self.font_face = None
        self.font_size = None
        self.font_style = None
        self.font_weight = None
        self.color = get_color

        self.__bindings()
        self.__do_layout()

    def __bindings(self):
        """Binds events to handlers"""

        self.textctrl.Bind(wx.EVT_TEXT, self.OnText)
        self.fontbutton.Bind(wx.EVT_BUTTON, self.OnFont)
        self.Bind(csel.EVT_COLOURSELECT, self.OnColor)

    def __do_layout(self):
        grid_sizer = wx.FlexGridSizer(1, 3, 0, 0)

        grid_sizer.Add(self.textctrl, 1, wx.ALL | wx.EXPAND, 2)
        grid_sizer.Add(self.fontbutton, 1, wx.ALL | wx.EXPAND, 2)
        grid_sizer.Add(self.colorselect, 1, wx.ALL | wx.EXPAND, 2)

        grid_sizer.AddGrowableCol(0)

        self.SetSizer(grid_sizer)

        self.fontbutton.SetToolTip(wx.ToolTip(_("Text font")))
        self.colorselect.SetToolTip(wx.ToolTip(_("Text color")))

        self.Layout()

    def get_code(self):
        """Returns code representation of value of widget"""

        return self.textctrl.GetValue()

    def get_kwargs(self):
        """Return kwargs dict for text"""

        kwargs = {}

        if self.font_face:
            kwargs["fontname"] = repr(self.font_face)
        if self.font_size:
            kwargs["fontsize"] = repr(self.font_size)
        if self.font_style in self.style_wx2mpl:
            kwargs["fontstyle"] = repr(self.style_wx2mpl[self.font_style])
        if self.font_weight in self.weight_wx2mpl:
            kwargs["fontweight"] = repr(self.weight_wx2mpl[self.font_weight])

        kwargs["color"] = color2code(self.colorselect.GetValue())

        code = ", ".join(repr(key) + ": " + kwargs[key] for key in kwargs)

        code = "{" + code + "}"

        return code

    def set_code(self, code):
        """Sets widget from code string

        Parameters
        ----------
        code: String
        \tCode representation of widget value

        """

        self.textctrl.SetValue(code)

    def set_kwargs(self, code):
        """Sets widget from kwargs string

        Parameters
        ----------
        code: String
        \tCode representation of kwargs value

        """

        kwargs = {}

        kwarglist = list(parse_dict_strings(code[1:-1]))

        for kwarg, val in zip(kwarglist[::2], kwarglist[1::2]):
            kwargs[unquote_string(kwarg)] = val

        for key in kwargs:
            if key == "color":
                color = code2color(kwargs[key])
                self.colorselect.SetValue(color)
                self.colorselect.SetOwnForegroundColour(color)

            elif key == "fontname":
                self.font_face = unquote_string(kwargs[key])

                if self.chosen_font is None:
                    self.chosen_font = get_default_font()
                self.chosen_font.SetFaceName(self.font_face)

            elif key == "fontsize":
                if kwargs[key]:
                    self.font_size = int(kwargs[key])
                else:
                    self.font_size = get_default_font().GetPointSize()

                if self.chosen_font is None:
                    self.chosen_font = get_default_font()

                self.chosen_font.SetPointSize(self.font_size)

            elif key == "fontstyle":
                self.font_style = \
                    self.style_mpl2wx[unquote_string(kwargs[key])]

                if self.chosen_font is None:
                    self.chosen_font = get_default_font()

                self.chosen_font.SetStyle(self.font_style)

            elif key == "fontweight":
                self.font_weight = \
                    self.weight_mpl2wx[unquote_string(kwargs[key])]

                if self.chosen_font is None:
                    self.chosen_font = get_default_font()

                self.chosen_font.SetWeight(self.font_weight)

    # Properties

    code = property(get_code, set_code)

    # Handlers

    def OnText(self, event):
        """Text entry event handler"""

        post_command_event(self, self.DrawChartMsg)

    def OnFont(self, event):
        """Check event handler"""

        font_data = wx.FontData()

        # Disable color chooser on Windows
        font_data.EnableEffects(False)

        if self.chosen_font:
            font_data.SetInitialFont(self.chosen_font)

        dlg = wx.FontDialog(self, font_data)

        if dlg.ShowModal() == wx.ID_OK:
            font_data = dlg.GetFontData()

            font = self.chosen_font = font_data.GetChosenFont()

            self.font_face = font.GetFaceName()
            self.font_size = font.GetPointSize()
            self.font_style = font.GetStyle()
            self.font_weight = font.GetWeight()

        dlg.Destroy()

        post_command_event(self, self.DrawChartMsg)

    def OnColor(self, event):
        """Check event handler"""

        post_command_event(self, self.DrawChartMsg)


class TickParamsEditor(wx.Panel, ChartDialogEventMixin):
    """Editor widget for axis ticks

    The widget contains: direction, pad, labelsize, bottom, top, left, right

    """

    choice_labels = [_("Inside"), _("Outside"), _("Both")]
    choice_params = ["in", "out", "inout"]

    choice_label2param = dict(zip(choice_labels, choice_params))
    choice_param2label = dict(zip(choice_params, choice_labels))

    def __init__(self, *args, **kwargs):
        wx.Panel.__init__(self, *args, **kwargs)

        self.attrs = {
            "direction": None,
            "pad": None,
            "top": None,
            "right": None,
            "labelsize": None,
        }

        self.direction_choicectrl = wx.Choice(self, -1,
                                              choices=self.choice_labels)
        self.pad_label = wx.StaticText(self, -1, _("Padding"), size=(-1, 15))
        self.pad_intctrl = IntCtrl(self, -1, allow_none=True, value=None,
                                   limited=True)
        self.size_label = wx.StaticText(self, -1, _("Size"), size=(-1, 15))
        self.labelsize_intctrl = IntCtrl(self, -1, allow_none=True, value=None,
                                         min=1, max=99, limited=True)

        style = wx.ALIGN_RIGHT | wx.CHK_3STATE
        self.sec_checkboxctrl = wx.CheckBox(self, -1, label=_("Secondary"),
                                            style=style)

        self.sec_checkboxctrl.Set3StateValue(wx.CHK_UNDETERMINED)
        self.__bindings()
        self.__do_layout()

    def __bindings(self):
        """Binds events to handlers"""

        self.direction_choicectrl.Bind(wx.EVT_CHOICE, self.OnDirectionChoice)
        self.sec_checkboxctrl.Bind(wx.EVT_CHECKBOX, self.OnSecondaryCheckbox)
        self.pad_intctrl.Bind(EVT_INT, self.OnPadIntCtrl)
        self.labelsize_intctrl.Bind(EVT_INT, self.OnLabelSizeIntCtrl)

    def __do_layout(self):
        grid_sizer = wx.FlexGridSizer(1, 3, 0, 0)
        grid_sizer.Add(self.sec_checkboxctrl, 1, wx.ALL | wx.EXPAND, 2)
        grid_sizer.Add(self.pad_label, 1, wx.ALL | wx.EXPAND, 2)
        grid_sizer.Add(self.pad_intctrl, 1, wx.ALL | wx.EXPAND, 2)
        grid_sizer.Add(self.direction_choicectrl, 1, wx.ALL | wx.EXPAND, 2)
        grid_sizer.Add(self.size_label, 1, wx.ALL | wx.EXPAND, 2)
        grid_sizer.Add(self.labelsize_intctrl, 1, wx.ALL | wx.EXPAND, 2)

        grid_sizer.AddGrowableCol(0)
        grid_sizer.AddGrowableCol(1)
        grid_sizer.AddGrowableCol(2)

        self.SetSizer(grid_sizer)

        # Tooltips
        dir_tip = _("Puts ticks inside the axes, outside the axes, or both.")
        self.direction_choicectrl.SetToolTip(wx.ToolTip(dir_tip))
        pad_tip = _("Distance in points between tick and label.")
        self.pad_intctrl.SetToolTip(wx.ToolTip(pad_tip))
        label_tip = _("Tick label font size in points.")
        self.labelsize_intctrl.SetToolTip(wx.ToolTip(label_tip))

        self.Layout()

    def get_code(self):
        """Returns code representation of value of widget"""

        return ""

    def get_kwargs(self):
        """Return kwargs dict for text"""

        kwargs = {}

        for attr in self.attrs:
            val = self.attrs[attr]
            if val is not None:
                kwargs[attr] = repr(val)

        code = ", ".join(repr(key) + ": " + kwargs[key] for key in kwargs)

        code = "{" + code + "}"

        return code

    def set_code(self, code):
        """Sets widget from code string, does nothing here

        Parameters
        ----------
        code: String
        \tCode representation of widget value

        """

        pass

    def set_kwargs(self, code):
        """Sets widget from kwargs string

        Parameters
        ----------
        code: String
        \tCode representation of kwargs value

        """

        kwargs = {}

        kwarglist = list(parse_dict_strings(code[1:-1]))

        for kwarg, val in zip(kwarglist[::2], kwarglist[1::2]):
            kwargs[unquote_string(kwarg)] = val

        for key in kwargs:
            if key == "direction":
                self.attrs[key] = unquote_string(kwargs[key])
                label = self.choice_param2label[self.attrs[key]]
                label_list = self.direction_choicectrl.Items
                self.direction_choicectrl.SetSelection(label_list.index(label))

            elif key == "pad":
                self.attrs[key] = int(kwargs[key])
                self.pad_intctrl.SetValue(self.attrs[key])

            elif key in ["top", "right"]:
                self.attrs[key] = (not kwargs[key] == "False")
                if self.attrs[key]:
                    self.sec_checkboxctrl.Set3StateValue(wx.CHK_CHECKED)
                else:
                    self.sec_checkboxctrl.Set3StateValue(wx.CHK_UNCHECKED)

            elif key == "labelsize":
                self.attrs[key] = int(kwargs[key])
                self.labelsize_intctrl.SetValue(self.attrs[key])

    # Properties

    code = property(get_code, set_code)

    # Event handlers

    def OnDirectionChoice(self, event):
        """Direction choice event handler"""

        label = self.direction_choicectrl.GetItems()[event.GetSelection()]
        param = self.choice_label2param[label]
        self.attrs["direction"] = param

        post_command_event(self, self.DrawChartMsg)

    def OnSecondaryCheckbox(self, event):
        """Top Checkbox event handler"""

        self.attrs["top"] = event.IsChecked()
        self.attrs["right"] = event.IsChecked()

        post_command_event(self, self.DrawChartMsg)

    def OnPadIntCtrl(self, event):
        """Pad IntCtrl event handler"""

        self.attrs["pad"] = event.GetValue()

        post_command_event(self, self.DrawChartMsg)

    def OnLabelSizeIntCtrl(self, event):
        """Label size IntCtrl event handler"""

        self.attrs["labelsize"] = event.GetValue()

        post_command_event(self, self.DrawChartMsg)


class ColorEditor(csel.ColourSelect, ChartDialogEventMixin):
    """Editor widget for 3-tuples of floats that represent color"""

    def __init__(self, *args, **kwargs):
        csel.ColourSelect.__init__(self, *args, **kwargs)

        self.__bindings()

    def __bindings(self):
        """Binds events to handlers"""

        self.Bind(csel.EVT_COLOURSELECT, self.OnColor)

    def get_code(self):
        """Returns string representation of Integer"""

        return color2code(self.GetValue())

    def set_code(self, code):
        """Sets widget from code string

        Parameters
        ----------
        code: String
        \tString representation of 3 tuple of float

        """

        self.SetColour(code2color(code))

    # Properties

    code = property(get_code, set_code)

    # Handlers

    def OnColor(self, event):
        """Check event handler"""

        post_command_event(self, self.DrawChartMsg)


class StyleEditorMixin(object):
    """Mixin class for stzle editors that are based on MatplotlibStyleChoice"""

    def bindings(self):
        """Binds events to handlers"""

        self.Bind(wx.EVT_CHOICE, self.OnStyle)

    def get_code(self):
        """Returns code representation of value of widget"""

        selection = self.GetSelection()

        if selection == wx.NOT_FOUND:
            selection = 0

        # Return code string
        return self.styles[selection][1]

    def set_code(self, code):
        """Sets widget from code string

        Parameters
        ----------
        code: String
        \tCode representation of widget value

        """

        for i, (_, style_code) in enumerate(self.styles):
            if code == style_code:
                self.SetSelection(i)

    # Properties

    code = property(get_code, set_code)

    # Handlers
    # --------

    def OnStyle(self, event):
        """Marker style event handler"""

        post_command_event(self, self.DrawChartMsg)


class MarkerStyleEditor(MarkerStyleComboBox, ChartDialogEventMixin,
                        StyleEditorMixin):
    """Editor widget for marker style string values"""

    def __init__(self, *args, **kwargs):
        MarkerStyleComboBox.__init__(self, *args, **kwargs)

        self.bindings()


class LineStyleEditor(LineStyleComboBox, ChartDialogEventMixin,
                      StyleEditorMixin):
    """Editor widget for line style string values"""

    def __init__(self, *args, **kwargs):
        LineStyleComboBox.__init__(self, *args, **kwargs)

        self.bindings()


class CoordinatesEditor(CoordinatesComboBox, ChartDialogEventMixin,
                        StyleEditorMixin):
    """Editor widget for line style string values"""

    def __init__(self, *args, **kwargs):
        CoordinatesComboBox.__init__(self, *args, **kwargs)

        self.bindings()

# -------------
# Panel widgets
# -------------


class SeriesBoxPanel(wx.Panel):
    """Box panel that contains labels and widgets

    Parameters
    ----------

    * panel_label: String
    \tLabel that is displayed left of the widget
    * labels: List of strings
    \tWidget labels
    * widgets: List of class instances
    \tWidget instance list must be as long as labels

    """

    def __init__(self, parent, box_label, labels, widget_clss, widget_codes,
                 tooltips):

        wx.Panel.__init__(self, parent, -1)

        self.staticbox = wx.StaticBox(self, -1, box_label)

        self.labels = [wx.StaticText(self, -1, label) for label in labels]

        self.widgets = []

        for widget_cls, widget_code, label, tooltip in \
                zip(widget_clss, widget_codes, self.labels, tooltips):
            widget = widget_cls(self, -1)
            widget.code = widget_code
            self.widgets.append(widget)
            if tooltip:
                widget.SetToolTipString(tooltip)

        self.__do_layout()

    def __do_layout(self):
        box_sizer = wx.StaticBoxSizer(self.staticbox, wx.HORIZONTAL)
        grid_sizer = wx.FlexGridSizer(1, 2, 0, 0)

        for label, widget in zip(self.labels, self.widgets):
            grid_sizer.Add(label, 1, wx.ALL | wx.EXPAND, 2)
            grid_sizer.Add(widget, 1, wx.ALL | wx.EXPAND, 2)

        grid_sizer.AddGrowableCol(1)
        box_sizer.Add(grid_sizer, 1, wx.ALL | wx.EXPAND, 2)

        self.SetSizer(box_sizer)

        self.Layout()


class SeriesAttributesPanelBase(wx.Panel):
    """Base class for <Seriestype>AttributesPanel and FigureAttributesPanel"""

    def __init__(self, parent, series_data, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)

        self.data = {}
        self.data.update(self.default_data)

        self.update(series_data)

        self.box_panels = []

        for box_label, keys in self.boxes:
            labels = []
            widget_clss = []
            widget_codes = []
            tooltips = []

            for key in keys:
                widget_label, widget_cls, widget_default = self.data[key]

                widget_clss.append(widget_cls)
                widget_codes.append(widget_default)
                labels.append(widget_label)
                try:
                    tooltips.append(self.tooltips[key])
                except KeyError:
                    tooltips.append("")

            self.box_panels.append(SeriesBoxPanel(self, box_label, labels,
                                                  widget_clss, widget_codes,
                                                  tooltips))

        self.__do_layout()

    def __do_layout(self):
        main_sizer = wx.FlexGridSizer(1, 1, 0, 0)

        for box_panel in self.box_panels:
            main_sizer.Add(box_panel, 1, wx.ALL | wx.EXPAND, 2)

        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(0)
        main_sizer.AddGrowableRow(1)
        main_sizer.AddGrowableRow(2)

        self.SetSizer(main_sizer)

        self.Layout()

    def __iter__(self):
        """Yields (key, code) for each widget"""

        for box_panel, (_, keys) in zip(self.box_panels, self.boxes):
            for widget, key in zip(box_panel.widgets, keys):
                yield key, widget

    def update(self, series_data):
        """Updates self.data from series data

        Parameters
        ----------
         * series_data: dict
        \tKey value pairs for self.data, which correspond to chart attributes

        """

        for key in series_data:
            try:
                data_list = list(self.data[key])
                data_list[2] = str(series_data[key])
                self.data[key] = tuple(data_list)
            except KeyError:
                pass


class PlotAttributesPanel(SeriesAttributesPanelBase):
    """Panel that provides plot series attributes in multiple boxed panels"""

    # Data for series plot
    # matplotlib_key, label, widget_cls, default_code

    default_data = {
        "label": (_("Label"), StringEditor, ""),
        "xdata": (_("X"), StringEditor, ""),
        "ydata": (_("Y"), StringEditor, ""),
        "linestyle": (_("Style"), LineStyleEditor, '-'),
        "linewidth": (_("Width"), IntegerEditor, "1"),
        "color": (_("Color"), ColorEditor, "(0, 0, 0)"),
        "marker": (_("Style"), MarkerStyleEditor, ""),
        "markersize": (_("Size"), IntegerEditor, "5"),
        "markerfacecolor": (_("Face color"), ColorEditor, "(0, 0, 0)"),
        "markeredgecolor": (_("Edge color"), ColorEditor, "(0, 0, 0)"),
    }

    # Boxes and their widgets' matplotlib_keys
    # label, [matplotlib_key, ...]

    boxes = [
        (_("Data"), ["label", "xdata", "ydata"]),
        (_("Line"), ["linestyle", "linewidth", "color"]),
        (_("Marker"), ["marker", "markersize", "markerfacecolor",
                       "markeredgecolor"]),
    ]

    tooltips = {
        "label": _(u"String or anything printable with ‘%s’ conversion"),
        "xdata": _(u"The data np.array for x\n"
                   u"Code must eval to 1D array."),
        "ydata": _(u"The data np.array for y\n"
                   u"Code must eval to 1D array."),
        "linewidth": _(u"The line width in points"),
        "marker": _(u"The line marker"),
        "markersize": _(u"The marker size in points"),
    }


class BarAttributesPanel(SeriesAttributesPanelBase):
    """Panel that provides bar series attributes in multiple boxed panels"""

    # Data for bar plot
    # matplotlib_key, label, widget_cls, default_code

    default_data = {
        "label": (_("Label"), StringEditor, ""),
        "left": (_("Left positions"), StringEditor, ""),
        "height": (_("Bar heights"), StringEditor, ""),
        "width": (_("Bar widths"), StringEditor, ""),
        "bottom": (_("Bar bottoms"), StringEditor, ""),
        "color": (_("Bar color"), ColorEditor, "(0, 0, 0)"),
        "edgecolor": (_("Edge color"), ColorEditor, "(0, 0, 0)"),
    }

    # Boxes and their widgets' matplotlib_keys
    # label, [matplotlib_key, ...]

    boxes = [
        (_("Data"), ["label", "left", "height", "width", "bottom"]),
        (_("Bar"), ["color", "edgecolor"]),
    ]

    tooltips = {
        "label": _(u"String or anything printable with ‘%s’ conversion"),
        "left": _(u"The x coordinates of the left sides of the bars"),
        "height": _(u"The heights of the bars"),
        "width": _(u"The widths of the bars"),
        "bottom": _(u"The y coordinates of the bottom edges of the bars"),
    }


class BoxplotAttributesPanel(SeriesAttributesPanelBase):
    """Panel that provides bar series attributes in multiple boxplot panels"""

    # Data for boxplot
    # matplotlib_key, label, widget_cls, default_code

    default_data = {
        "x": (_("Series"), StringEditor, ""),
        "widths": (_("Box widths"), StringEditor, "0.5"),
        "vert": (_("Vertical"), BoolEditor, True),
        "sym":  (_("Flier"), MarkerStyleEditor, "+"),
        "notch": (_("Notch"), BoolEditor, False),
    }

    # Boxes and their widgets' matplotlib_keys
    # label, [matplotlib_key, ...]

    boxes = [
        (_("Data"), ["x"]),
        (_("Box plot"), ["widths", "vert", "sym", "notch"]),
    ]

    tooltips = {
        "x": _(u"An array or a sequence of vectors"),
        "widths": _(u"Either a scalar or a vector and sets the width of each "
                    u"box\nThe default is 0.5, or\n0.15*(distance between "
                    u"extreme positions)\nif that is smaller"),
        "vert": _(u"If True then boxes are drawn vertical\n"
                  u"If False then boxes are drawn horizontal"),
        "sym": _(u"The symbol for flier points\nEnter an empty string (‘’)\n"
                 u"if you don’t want to show fliers"),
        "notch": _(u"False produces a rectangular box plot\n"
                   u"True produces a notched box plot"),
    }


class HistogramAttributesPanel(SeriesAttributesPanelBase):
    """Panel that provides bar series attributes in histogram panels"""

    # Data for histogram
    # matplotlib_key, label, widget_cls, default_code

    default_data = {
        "label": (_("Label"), StringEditor, ""),
        "x": (_("Series"), StringEditor, ""),
        "bins": (_("Bins"), IntegerEditor, "10"),
        "normed": (_("Normed"), BoolEditor, False),
        "cumulative": (_("Cumulative"), BoolEditor, False),
        "color": (_("Color"), ColorEditor, "(0, 0, 1)"),
    }

    # Boxes and their widgets' matplotlib_keys
    # label, [matplotlib_key, ...]

    boxes = [
        (_("Data"), ["label", "x"]),
        (_("Histogram"), ["bins", "normed", "cumulative", "color"]),
    ]

    tooltips = {
        "label": _(u"String or anything printable with ‘%s’ conversion"),
        "x": _(u"Histogram data series\nMultiple data sets can be provided "
               u"as a list or as a 2-D ndarray in which each column"
               u"is a dataset. Note that the ndarray form is transposed "
               u"relative to the list form."),
        "bins": _(u"Either an integer number of bins or a bin sequence"),
        "normed": _(u"If True then the first element is the counts normalized"
                    u"to form a probability density, i.e., n/(len(x)*dbin)."),
        "cumulative": _(u"If True then each bin gives the counts in that bin"
                        u"\nplus all bins for smaller values."),
    }


class PieAttributesPanel(SeriesAttributesPanelBase):
    """Panel that provides pie series attributes in multiple boxed panels"""

    # Data for pie plot
    # matplotlib_key, label, widget_cls, default_code

    default_data = {
        "x": (_("Series"), StringEditor, ""),
        "labels": (_("Labels"), StringEditor, ""),
        "colors": (_("Colors"), StringEditor, ""),
        "startangle": (_("Start angle"), IntegerEditor, "0"),
        "shadow": (_("Shadow"), BoolEditor, False),
    }

    # Boxes and their widgets' matplotlib_keys
    # label, [matplotlib_key, ...]

    boxes = [
        (_("Data"), ["x"]),
        (_("Pie"), ["labels", "colors", "startangle", "shadow"]),
    ]

    tooltips = {
        "x": _(u"Pie chart data\nThe fractional area of each wedge is given "
               u"by x/sum(x)\nThe wedges are plotted counterclockwise"),
        "labels": _(u"Sequence of wedge label strings"),
        "colors": _(u"Sequence of matplotlib color args through which the pie "
                    u"cycles.\nSupported strings are:\n'b': blue\n'g': green\n"
                    u"'r': red\n'c': cyan\n'm': magenta\n'y': yellow\n'k': "
                    u"black\n'w': white\nGray shades can be given as a string"
                    u"that encodes a float in the 0-1 range, e.g.: '0.75'. "
                    u"You can also specify the color with an html hex string "
                    u"as in: '#eeefff'. Finally, legal html names for colors, "
                    u"such as 'red', 'burlywood' and 'chartreuse' are "
                    u"supported."),
        "startangle": _(u"Rotates the start of the pie chart by angle degrees "
                        u"counterclockwise from the x-axis."),
        "shadow": _(u"If True then a shadow beneath the pie is drawn"),
    }


class AnnotateAttributesPanel(SeriesAttributesPanelBase):
    """Panel that provides annotation attributes in multiple boxed panels"""

    # Data for annotation
    # matplotlib_key, label, widget_cls, default_code

    default_data = {
        "s": (_("Text"), StringEditor, ""),
        "xy": (_("Point"), StringEditor, ""),
        "xycoords": (_("Coordinates"), CoordinatesEditor, "data"),
    }

    # Boxes and their widgets' matplotlib_keys
    # label, [matplotlib_key, ...]

    boxes = [
        (_("Annotation"), ["s", "xy", "xycoords"]),
    ]

    tooltips = {
        "s": _(u"Annotation text"),
        "xy": _(u"Point that is annotated"),
        "xycoords": _(u"String that indicates the coordinates of xy"),
        "xytext": _(u"Location of annotation text"),
        "textcoords": _(u"String that indicates the coordinates of xytext."),
    }


class ContourAttributesPanel(SeriesAttributesPanelBase):
    """Panel that provides contour attributes in multiple boxed panels"""

    # Data for contour plot
    # matplotlib_key, label, widget_cls, default_code

    default_data = {
        "X": (_("X"), StringEditor, ""),
        "Y": (_("Y"), StringEditor, ""),
        "Z": (_("Z"), StringEditor, ""),
        "colors": (_("Colors"), StringEditor, ""),
        "alpha": (_("Alpha"), StringEditor, "1.0"),
        "linestyles": (_("Style"), LineStyleEditor, '-'),
        "linewidths": (_("Width"), IntegerEditor, "1"),
        "contour_labels": (_("Contour labels"), BoolEditor, True),
        "contour_label_fontsize": (_("Font size"), IntegerEditor, "10"),
        "contour_fill": (_("Fill contour"), BoolEditor, False),
        "hatches": (_("Hatches"), StringEditor, ""),
    }

    # Boxes and their widgets' matplotlib_keys
    # label, [matplotlib_key, ...]

    boxes = [
        (_("Data"), ["X", "Y", "Z"]),
        (_("Lines"), ["linestyles", "linewidths", "colors", "alpha"]),
        (_("Areas"), ["contour_fill", "hatches"]),
        (_("Labels"), ["contour_labels", "contour_label_fontsize"]),
    ]

    tooltips = {
        "X": _(u"X coordinates of the surface"),
        "Y": _(u"Y coordinates of the surface"),
        "Z": _(u"Z coordinates of the surface (contour height)"),
        "colors":  _(u"If None, the colormap specified by cmap will be used.\n"
                     u"If a string, like ‘r’ or ‘red’, all levels will be "
                     u"plotted in this color.\nIf a tuple of matplotlib color "
                     u"args (string, float, rgb, etc), different levels will "
                     u"be plotted in different colors in the order"
                     u" specified."),
        "alpha": _(u"The alpha blending value"),
        "linestyles": _(u"Contour line style"),
        "linewidths": _(u"All contour levels will be plotted with this "
                        u"linewidth."),
        "contour_labels": _(u"Adds contour labels"),
        "contour_label_fontsize": _(u"Contour font label size in points"),
        "hatches": _(u"A list of cross hatch patterns to use on the filled "
                     u"areas. A hatch can be one of:\n"
                     u"/   - diagonal hatching\n"
                     u"\   - back diagonal\n"
                     u"|   - vertical\n"
                     u"-   - horizontal\n"
                     u"+   - crossed\n"
                     u"x   - crossed diagonal\n"
                     u"o   - small circle\n"
                     u"O   - large circle\n"
                     u".   - dots\n"
                     u"*   - stars\n"
                     u"Letters can be combined, in which case all the "
                     u"specified hatchings are done. If same letter repeats, "
                     u"it increases the density of hatching of that pattern."),
    }


class SankeyAttributesPanel(SeriesAttributesPanelBase):
    """Panel that provides Sankey plot attributes in multiple boxed panels"""

    # Data for Sankey plot
    # matplotlib_key, label, widget_cls, default_code

    default_data = {
        "flows": (_("Flows"), StringEditor, ""),
        "orientations": (_("Orientations"), StringEditor, ""),
        "labels": (_("Labels"), StringEditor, ""),
        "format": (_("Format"), TextEditor, "%f"),
        "unit": (_("Unit"), TextEditor, ""),
        "rotation": (_("Rotation"), IntegerEditor, "0"),
        "gap": (_("Gap"), StringEditor, "0.25"),
        "radius": (_("Radius"), StringEditor, "0.1"),
        "shoulder": (_("Shoulder"), StringEditor, "0.03"),
        "offset": (_("Offset"), StringEditor, "0.15"),
        "head_angle": (_("Angle"), IntegerEditor, "100"),
        "edgecolor": (_("Edge"), ColorEditor, "(0, 0, 1)"),
        "facecolor": (_("Face"), ColorEditor, "(0, 0, 1)"),
    }

    # Boxes and their widgets' matplotlib_keys
    # label, [matplotlib_key, ...]

    boxes = [
        (_("Data"), ["flows", "orientations", "labels", "format", "unit"]),
        (_("Diagram"), ["rotation", "gap", "radius", "shoulder", "offset",
                        "head_angle"]),
        (_("Area"), ["edgecolor", "facecolor"]),
    ]

    tooltips = {
        "flows": _(u"Array of flow values.\nBy convention, inputs are positive"
                   u" and outputs are negative."),
        "orientations": _(u"List of orientations of the paths.\nValid values "
                          u"are 1 (from/to the top), 0 (from/to the left or "
                          u"right), or -1 (from/to the bottom).\nIf "
                          u"orientations == 0, inputs will break in from the "
                          u"left and outputs will break away to the right."),
        "labels": _(u"List of specifications of the labels for the flows.\n"
                    u"Each value may be None (no labels), ‘’ (just label the "
                    u"quantities), or a labeling string. If a single value is "
                    u"provided, it will be applied to all flows. If an entry "
                    u"is a non-empty string, then the quantity for the "
                    u"corresponding flow will be shown below the string. "
                    u"However, if the unit of the main diagram is None, then "
                    u"quantities are never shown, regardless of the value of "
                    u"this argument."),
        "unit": _(u"String representing the physical unit associated with "
                  u"the flow quantities.\nIf unit is None, then none of the "
                  u"quantities are labeled."),
        "format": _(u"A Python number formatting string to be used in "
                    u"labeling the flow as a quantity (i.e., a number times a "
                    u"unit, where the unit is given)"),
        "rotation": _(u"Angle of rotation of the diagram [deg]"),
        "gap": _(u"Space between paths that break in/break away to/from the "
                 u"top or bottom."),
        "radius": _(u"Inner radius of the vertical paths"),
        "shoulder": _(u"Size of the shoulders of output arrows"),
        "offset": _(u"Text offset (from the dip or tip of the arrow)"),
        "head_angle": _(u"Angle of the arrow heads (and negative of the angle "
                        u"of the tails) [deg]"),
        "edgecolor": _(u"Edge color of Sankey diagram"),
        "facecolor": _(u"Face color of Sankey diagram"),
    }


class FigureAttributesPanel(SeriesAttributesPanelBase):
    """Panel that provides figure attributes in multiple boxed panels"""

    # strftime doc taken from Python documentation

    strftime_doc = _(u"""
Code 	Meaning
%a 	Locale’s abbreviated weekday name.
%A 	Locale’s full weekday name.
%b 	Locale’s abbreviated month name.
%B 	Locale’s full month name.
%c 	Locale’s appropriate date and time representation.
%d 	Day of the month as a decimal number [01,31].
%f 	Microsecond as a decimal number [0,999999], zero-padded on the left
%H 	Hour (24-hour clock) as a decimal number [00,23].
%I 	Hour (12-hour clock) as a decimal number [01,12].
%j 	Day of the year as a decimal number [001,366].
%m 	Month as a decimal number [01,12].
%M 	Minute as a decimal number [00,59].
%p 	Locale’s equivalent of either AM or PM.
%S 	Second as a decimal number [00,61].
%U 	Week number (Sunday first weekday) as a decimal number [00,53].
%w 	Weekday as a decimal number [0(Sunday),6]. 	4
%W 	Week number (Monday first weekday) as a decimal number [00,53].
%x 	Locale’s appropriate date representation.
%X 	Locale’s appropriate time representation.
%y 	Year without century as a decimal number [00,99].
%Y 	Year with century as a decimal number.
%z 	UTC offset in the form +HHMM or -HHMM.
%Z 	Time zone name.
%% 	A literal '%' character.""")

    # Data for figure
    # matplotlib_key, label, widget_cls, default_code

    default_data = {
        "title": (_("Title"), TextEditor, ""),
        "xlabel": (_("Label"), TextEditor, ""),
        "xlim": (_("Limits"), StringEditor, ""),
        "xscale": (_("Log. scale"), BoolEditor, False),
        "xtick_params": (_("X-axis ticks"), TickParamsEditor, ""),
        "ylabel": (_("Label"), TextEditor, ""),
        "ylim": (_("Limits"), StringEditor, ""),
        "yscale": (_("Log. scale"), BoolEditor, False),
        "ytick_params": (_("Y-axis ticks"), TickParamsEditor, ""),
        "xgrid": (_("X-axis grid"), BoolEditor, False),
        "ygrid": (_("Y-axis grid"), BoolEditor, False),
        "legend": (_("Legend"), BoolEditor, False),
        "xdate_format": (_("Date format"), StringEditor, ""),
    }

    # Boxes and their widgets' matplotlib_keys
    # label, [matplotlib_key, ...]

    boxes = [
        (_("Figure"), ["title", "legend"]),
        (_("X-Axis"), ["xlabel", "xlim", "xscale", "xgrid", "xdate_format",
                       "xtick_params"]),
        (_("Y-Axis"), ["ylabel", "ylim", "yscale", "ygrid", "ytick_params"]),
    ]

    tooltips = {
        "title": _(u"The figure title"),
        "xlabel": _(u"The label for the x axis"),
        "xlim": _(u"The data limits for the x axis\nFormat: (xmin, xmax)"),
        "ylabel": _(u"The label for the y axis"),
        "ylim": _(u"The data limits for the y axis\nFormat: (ymin, ymax)"),
        "xdate_format": _(u"If non-empty then the x axis is displays dates.\n"
                          u"Enter an unquoted strftime() format string."
                          u"\n") + strftime_doc,
    }


class SeriesPanel(wx.Panel):
    """Panel that holds attribute information for one series of the chart"""

    plot_types = [
        {"type": "plot", "panel_class": PlotAttributesPanel},
        {"type": "bar", "panel_class": BarAttributesPanel},
        {"type": "hist", "panel_class": HistogramAttributesPanel},
        {"type": "boxplot", "panel_class": BoxplotAttributesPanel},
        {"type": "pie", "panel_class": PieAttributesPanel},
        {"type": "annotate", "panel_class": AnnotateAttributesPanel},
        {"type": "contour", "panel_class": ContourAttributesPanel},
        {"type": "Sankey", "panel_class": SankeyAttributesPanel},
    ]

    def __init__(self, grid, series_dict):

        self.grid = grid

        wx.Panel.__init__(self, grid, -1)

        self.chart_type_book = wx.Treebook(self, -1, style=wx.BK_LEFT)
        self.il = wx.ImageList(24, 24)

        # Add plot panels

        for i, plot_type_dict in enumerate(self.plot_types):
            plot_type = plot_type_dict["type"]
            PlotPanelClass = plot_type_dict["panel_class"]

            series_data = {}
            if plot_type == series_dict["type"]:
                for key in series_dict:
                    series_data[key] = charts.object2code(key,
                                                          series_dict[key])

            plot_panel = PlotPanelClass(self.chart_type_book, series_data, -1)

            self.chart_type_book.AddPage(plot_panel, plot_type, imageId=i)
            self.il.Add(icons[plot_type_dict["type"]])

        self.plot_type = series_dict["type"]

        self._properties()
        self.__do_layout()

    def _properties(self):
        self.chart_type_book.SetImageList(self.il)

    def __do_layout(self):
        main_sizer = wx.FlexGridSizer(1, 1, 0, 0)
        main_sizer.Add(self.chart_type_book, 1, wx.ALL | wx.EXPAND, 2)

        self.SetSizer(main_sizer)

        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableCol(1)

        self.Layout()

    def __iter__(self):
        """Yields all keys of current pot panel"""

        panel = self.get_plot_panel()

        # First yield the panel type because it is not contained in any widget
        chart_type_number = self.chart_type_book.GetSelection()
        chart_type = self.plot_types[chart_type_number]["type"]
        yield "type", chart_type

        for key, code in panel:
            yield key, code

    def get_plot_panel(self):
        """Returns current plot_panel"""

        plot_type_no = self.chart_type_book.GetSelection()
        return self.chart_type_book.GetPage(plot_type_no)

    def set_plot_panel(self, plot_type_no):
        """Sets current plot_panel to plot_type_no"""

        self.chart_type_book.SetSelection(plot_type_no)

    plot_panel = property(get_plot_panel, set_plot_panel)

    def get_plot_type(self):
        """Returns current plot type"""

        return self.plot_types[self.plot_panel]["type"]

    def set_plot_type(self, plot_type):
        """Sets plot type"""

        ptypes = [pt["type"] for pt in self.plot_types]
        self.plot_panel = ptypes.index(plot_type)

    plot_type = property(get_plot_type, set_plot_type)


class AllSeriesPanel(wx.Panel, ChartDialogEventMixin):
    """Panel that holds series panels for all series of the chart"""

    def __init__(self, grid):
        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.THICK_FRAME

        self.grid = grid

        self.updating = False  # Set to true if you want to delete all tabs

        wx.Panel.__init__(self, grid, style=style)

        agwstyle = fnb.FNB_NODRAG | fnb.FNB_DROPDOWN_TABS_LIST | fnb.FNB_BOTTOM
        self.series_notebook = fnb.FlatNotebook(self, -1, agwStyle=agwstyle)

        self.__bindings()
        self.__do_layout()

    def __bindings(self):
        """Binds events to handlers"""

        self.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_CHANGED, self.OnSeriesChanged)
        self.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_CLOSING, self.OnSeriesDeleted)

    def __do_layout(self):
        main_sizer = wx.FlexGridSizer(1, 1, 0, 0)

        main_sizer.Add(self.series_notebook,
                       1, wx.EXPAND | wx.FIXED_MINSIZE, 0)

        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(0)

        self.SetSizer(main_sizer)

        self.Layout()

    def __iter__(self):
        """Yields series panels of the chart's series"""

        no_pages = self.series_notebook.GetPageCount()
        for page_number in xrange(no_pages - 1):
            yield self.series_notebook.GetPage(page_number)

    def update(self, series_list):
        """Updates widget content from series_list

        Parameters
        ----------
        series_list: List of dict
        \tList of dicts with data from all series

        """

        if not series_list:
            self.series_notebook.AddPage(wx.Panel(self, -1), _("+"))
            return

        self.updating = True

        # Delete all tabs in the notebook
        self.series_notebook.DeleteAllPages()

        # Add as many tabs as there are series in code

        for page, attrdict in enumerate(series_list):
            series_panel = SeriesPanel(self.grid, attrdict)
            name = "Series"

            self.series_notebook.InsertPage(page, series_panel, name)

        self.series_notebook.AddPage(wx.Panel(self, -1), _("+"))

        self.updating = False

    # Handlers
    # --------

    def OnSeriesChanged(self, event):
        """FlatNotebook change event handler"""

        selection = event.GetSelection()

        if not self.updating and \
           selection == self.series_notebook.GetPageCount() - 1:
            # Add new series
            new_panel = SeriesPanel(self, {"type": "plot"})
            self.series_notebook.InsertPage(selection, new_panel, _("Series"))

        event.Skip()

    def OnSeriesDeleted(self, event):
        """FlatNotebook closing event handler"""

        # Redraw Chart
        post_command_event(self, self.DrawChartMsg)

        event.Skip()


class FigurePanel(wx.Panel):
    """Panel that draws a matplotlib figure_canvas"""

    def __init__(self, parent):

        wx.Panel.__init__(self, parent)
        self.__do_layout()

    def __do_layout(self):
        self.main_sizer = wx.FlexGridSizer(1, 1, 0, 0)

        self.main_sizer.AddGrowableRow(0)
        self.main_sizer.AddGrowableCol(0)
        self.main_sizer.AddGrowableCol(1)

        self.SetSizer(self.main_sizer)

        self.Layout()

    def _get_figure_canvas(self, figure):
        """Returns figure canvas"""

        return FigureCanvasWxAgg(self, -1, figure)

    def update(self, figure):
        """Updates figure on data change

        Parameters
        ----------
        * figure: matplotlib.figure.Figure
        \tMatplotlib figure object that is displayed in self

        """

        if hasattr(self, "figure_canvas"):
            self.figure_canvas.Destroy()

        self.figure_canvas = self._get_figure_canvas(figure)

        self.figure_canvas.SetSize(self.GetSize())
        figure.subplots_adjust()

        self.main_sizer.Add(self.figure_canvas, 1,
                            wx.EXPAND | wx.FIXED_MINSIZE, 0)

        self.Layout()
        self.figure_canvas.draw()


class ChartDialog(wx.Dialog, ChartDialogEventMixin):
    """Chart dialog for generating chart generation strings"""

    def __init__(self, main_window, key, code):
        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.THICK_FRAME
        wx.Dialog.__init__(self, main_window, -1, style=style)

        self.grid = main_window.grid
        self.key = key

        self.figure_attributes_panel = FigureAttributesPanel(self, {}, -1)
        self.all_series_panel = AllSeriesPanel(self)
        self.figure_panel = FigurePanel(self)

        # Figure cache speeds up screen updates if figure code is unchanged
        self.figure_code_old = None
        self.figure_cache = None

        self.cancel_button = wx.Button(self, wx.ID_CANCEL)
        self.ok_button = wx.Button(self, wx.ID_OK)

        # The code has to be set after all widgets are created
        self.code = code

        self.__set_properties()
        self.__do_layout()
        self.__bindings()

    def __bindings(self):
        """Binds events to handlers"""

        self.Bind(self.EVT_CMD_DRAW_CHART, self.OnUpdateFigurePanel)

    def __set_properties(self):
        self.SetTitle(_("Insert chart"))

        self.figure_attributes_staticbox = wx.StaticBox(self, -1, _(u"Axes"))
        self.series_staticbox = wx.StaticBox(self, -1, _(u"Series"))

    def __do_layout(self):
        main_sizer = wx.FlexGridSizer(2, 1, 2, 2)
        chart_sizer = wx.FlexGridSizer(1, 3, 2, 2)
        figure_attributes_box_sizer = \
            wx.StaticBoxSizer(self.figure_attributes_staticbox, wx.HORIZONTAL)
        series_box_sizer = \
            wx.StaticBoxSizer(self.series_staticbox, wx.VERTICAL)
        button_sizer = wx.FlexGridSizer(1, 3, 0, 3)

        main_sizer.Add(chart_sizer, 1, wx.EXPAND, 0)
        main_sizer.Add(button_sizer, 1, wx.FIXED_MINSIZE, 0)

        chart_sizer.Add(figure_attributes_box_sizer, 1, wx.EXPAND, 0)
        chart_sizer.Add(series_box_sizer, 1, wx.EXPAND, 0)
        chart_sizer.Add(self.figure_panel, 1, wx.EXPAND, 0)

        main_sizer.SetMinSize((1000, -1))
        main_sizer.SetFlexibleDirection(wx.BOTH)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(0)
        try:
            main_sizer.RemoveGrowableRow(1)
        except:
            pass

        chart_sizer.SetMinSize((1000, -1))
        chart_sizer.AddGrowableRow(0)
        chart_sizer.AddGrowableCol(0, proportion=1)
        chart_sizer.AddGrowableCol(1, proportion=1)
        chart_sizer.AddGrowableCol(2, proportion=1)

        figure_attributes_box_sizer.Add(self.figure_attributes_panel,
                                        1, wx.EXPAND, 0)
        series_box_sizer.Add(self.all_series_panel, 1, wx.EXPAND, 0)

        style = wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL
        button_sizer.Add(self.ok_button, 0, style, 3)
        button_sizer.Add(self.cancel_button, 0, style, 3)
        button_sizer.AddGrowableCol(2)

        self.Layout()
        self.SetSizerAndFit(main_sizer)


    def get_figure(self, code):
        """Returns figure from executing code in grid

        Returns an empty matplotlib figure if code does not eval to a
        matplotlib figure instance.

        Parameters
        ----------
        code: Unicode
        \tUnicode string which contains Python code that should yield a figure

        """

        # Caching for fast response if there are no changes
        if code == self.figure_code_old and self.figure_cache:
            return self.figure_cache

        self.figure_code_old = code

        # key is the current cursor cell of the grid
        key = self.grid.actions.cursor
        cell_result = self.grid.code_array._eval_cell(key, code)

        # If cell_result is matplotlib figure
        if isinstance(cell_result, matplotlib.pyplot.Figure):
            # Return it
            self.figure_cache = cell_result
            return cell_result

        else:
            # Otherwise return empty figure
            self.figure_cache = charts.ChartFigure()

        return self.figure_cache

    # Tuple keys have to be put in parentheses
    tuple_keys = ["xdata", "ydata", "left", "height", "width", "bottom",
                  "xlim", "ylim", "x", "labels", "colors", "xy", "xytext",
                  "title", "xlabel", "ylabel", "label", "X", "Y", "Z",
                  "hatches", "flows", "orientations", "labels"]

    # String keys need to be put in "
    string_keys = ["type", "linestyle", "marker", "shadow", "vert", "xgrid",
                   "ygrid", "notch", "sym", "normed", "cumulative",
                   "xdate_format", "xycoords", "textcoords", "linestyles",
                   "contour_labels", "contour_fill", "format", "unit"]

    # Keys, which have to be None if empty
    empty_none_keys = ["colors", "color"]

    def set_code(self, code):
        """Update widgets from code"""

        # Get attributes from code

        attributes = []
        strip = lambda s: s.strip('u').strip("'").strip('"')
        for attr_dict in parse_dict_strings(unicode(code).strip()[19:-1]):
            attrs = list(strip(s) for s in parse_dict_strings(attr_dict[1:-1]))
            attributes.append(dict(zip(attrs[::2], attrs[1::2])))

        if not attributes:
            return

        # Set widgets from attributes
        # ---------------------------

        # Figure attributes
        figure_attributes = attributes[0]

        for key, widget in self.figure_attributes_panel:
            try:
                obj = figure_attributes[key]
                kwargs_key = key + "_kwargs"
                if kwargs_key in figure_attributes:
                    widget.set_kwargs(figure_attributes[kwargs_key])

            except KeyError:
                obj = ""

            widget.code = charts.object2code(key, obj)

        # Series attributes
        self.all_series_panel.update(attributes[1:])

    def get_code(self):
        """Returns code that generates figure from widgets"""

        def dict2str(attr_dict):
            """Returns string with dict content with values as code

            Code means that string identifiers are removed

            """

            result = u"{"

            for key in attr_dict:
                code = attr_dict[key]

                if key in self.string_keys:
                    code = repr(code)

                elif code and key in self.tuple_keys and \
                     not (code[0] in ["[", "("] and code[-1] in ["]", ")"]):

                    code = "(" + code + ")"

                elif key in ["xscale", "yscale"]:
                    if code:
                        code = '"log"'
                    else:
                        code = '"linear"'

                elif key in ["legend"]:
                    if code:
                        code = '1'
                    else:
                        code = '0'

                elif key in ["xtick_params"]:
                    code = '"x"'

                elif key in ["ytick_params"]:
                    code = '"y"'

                if not code:
                    if key in self.empty_none_keys:
                        code = "None"
                    else:
                        code = 'u""'

                result += repr(key) + ": " + code + ", "

            result = result[:-2] + u"}"

            return result

        # cls_name inludes full class name incl. charts
        cls_name = "charts." + charts.ChartFigure.__name__

        attr_dicts = []

        # Figure attributes
        attr_dict = {}
        # figure_attributes is a dict key2code
        for key, widget in self.figure_attributes_panel:
            if key == "type":
                attr_dict[key] = widget
            else:
                attr_dict[key] = widget.code
                try:
                    attr_dict[key+"_kwargs"] = widget.get_kwargs()
                except AttributeError:
                    pass

        attr_dicts.append(attr_dict)

        # Series_attributes is a list of dicts key2code
        for series_panel in self.all_series_panel:
            attr_dict = {}
            for key, widget in series_panel:
                if key == "type":
                    attr_dict[key] = widget
                else:
                    attr_dict[key] = widget.code

            attr_dicts.append(attr_dict)

        code = cls_name + "("

        for attr_dict in attr_dicts:
            code += dict2str(attr_dict) + ", "

        code = code[:-2] + ")"

        return code

    # Properties
    # ----------

    code = property(get_code, set_code)

    # Handlers
    # --------

    def OnUpdateFigurePanel(self, event):
        """Redraw event handler for the figure panel"""

        self.figure_panel.update(self.get_figure(self.code))

########NEW FILE########
__FILENAME__ = _dialogs
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
_dialogs
========

Provides:
---------
  - ChoiceRenderer: Renders choice dialog box for grid
  - CsvParameterWidgets: CSV parameter entry panel content
  - CSVPreviewGrid: Grid in CSV import parameter entry panel
  - CSVPreviewTextCtrl: TextCtrl in CSV export parameter entry panel
  - CsvImportDialog: Dialog for CSV import parameter choice
  - CsvExportDialog:  Dialog for CSV export parameter choice
  - MacroDialog: Dialog for macro management
  - DimensionsEntryDialog
  - CellEntryDialog
  - AboutDialog
  - PreferencesDialog
  - GPGParamsDialog
  - PasteAsDialog

"""

import cStringIO
import csv
import os
import string
import types

import wx
import wx.grid
from wx.lib.wordwrap import wordwrap
import wx.lib.masked
import wx.stc as stc

import src.lib.i18n as i18n
from src.config import config, VERSION
from src.sysvars import get_program_path
from src.gui._widgets import PythonSTC
from src.gui._events import post_command_event
from src.gui._events import MainWindowEventMixin, GridEventMixin
from src.lib.__csv import Digest, sniff, get_first_line, encode_gen
from src.lib.__csv import csv_digest_gen, cell_key_val_gen
from src.lib.exception_handling import get_user_codeframe

import ast
from traceback import print_exception
from StringIO import StringIO
from sys import exc_info
#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


class IntValidator(wx.PyValidator):
    """IntTextCtrl input validation class"""

    def __init__(self):
        wx.PyValidator.__init__(self)\

        self.Bind(wx.EVT_CHAR, self.OnChar)

    def TransferToWindow(self):
            return True

    def TransferFromWindow(self):
            return True

    def Clone(self):
        return wx.Validator()

    def Validate(self, win):
        """Returns True if Value in digits, False otherwise"""

        val = self.GetWindow().GetValue()

        for x in val:
            if x not in string.digits:
                return False

        return True

    def OnChar(self, event):
        """Eats event if key not in digits"""

        key = event.GetKeyCode()

        if key < wx.WXK_SPACE or key == wx.WXK_DELETE or key > 255 or \
           chr(key) in string.digits:
            event.Skip()

        # Returning without calling even.Skip eats the event
        #  before it gets to the text control


# end of class IntValidator

class ChoiceRenderer(wx.grid.PyGridCellRenderer):
    """Renders choice dialog box for grid

    Places an image in a cell based on the row index.
    There are N choices and the choice is made by  choice[row%N]

    """

    def __init__(self, table):

        wx.grid.PyGridCellRenderer.__init__(self)
        self.table = table

        self.iconwidth = 32

    def Draw(self, grid, attr, dc, rect, row, col, is_selected):
        """Draws the text and the combobox icon"""

        render = wx.RendererNative.Get()

        # clear the background
        dc.SetBackgroundMode(wx.SOLID)

        if is_selected:
            dc.SetBrush(wx.Brush(wx.BLUE, wx.SOLID))
            dc.SetPen(wx.Pen(wx.BLUE, 1, wx.SOLID))
        else:
            dc.SetBrush(wx.Brush(wx.WHITE, wx.SOLID))
            dc.SetPen(wx.Pen(wx.WHITE, 1, wx.SOLID))
        dc.DrawRectangleRect(rect)

        cb_lbl = grid.GetCellValue(row, col)
        string_x = rect.x + 2
        string_y = rect.y + 2
        dc.DrawText(cb_lbl, string_x, string_y)

        button_x = rect.x + rect.width - self.iconwidth
        button_y = rect.y
        button_width = self.iconwidth
        button_height = rect.height
        button_size = button_x, button_y, button_width, button_height
        render.DrawComboBoxDropButton(grid, dc, button_size,
                                      wx.CONTROL_CURRENT)


class CsvParameterWidgets(object):
    """
    This class holds the csv parameter entry panel

    It returns a sizer that contains the widgets

    Parameters
    ----------
    parent: wx.Window
    \tWindow at which the widgets will be placed
    csvfilepath: String
    \tPath of csv file

    """

    csv_params = [
        ["encodings", types.TupleType, _("Encoding"),
         _("CSV file encoding.")],
        ["dialects", types.TupleType, _("Dialect"),
         _("To make it easier to specify the format of input and output "
           "records, specific formatting parameters are grouped together "
           "into dialects.\n'excel': Defines the usual properties of an "
           "Excel-generated CSV file.\n'sniffer': Deduces the format of a "
           "CSV file\n'excel-tab': Defines the usual "
           "properties of an Excel-generated TAB-delimited file.")],
        ["delimiter", types.StringType, _("Delimiter"),
         _("A one-character string used to separate fields.")],
        ["doublequote", types.BooleanType, _("Doublequote"),
         _("Controls how instances of quotechar appearing inside a "
           "field should be themselves be quoted. When True, the character "
           "is doubled. When False, the escapechar is used as a prefix to "
           "the quotechar.")],
        ["escapechar", types.StringType, _("Escape character"),
         _("A one-character string used by "
           "the writer to escape the delimiter if quoting is set to "
           "QUOTE_NONE and the quotechar if doublequote is False. On "
           "reading, the escapechar removes any special meaning from the "
           "following character.")],
        ["quotechar", types.StringType, _("Quote character"),
         _("A one-character string used to quote fields containing special "
           "characters, such as the delimiter or quotechar, or which "
           "contain new-line characters.")],
        ["quoting", types.IntType, _("Quoting style"),
         _("Controls when quotes should be recognised.")],
        ["self.has_header", types.BooleanType, _("Header present"),
         _("Analyze the CSV file and treat the first row as strings if it "
           "appears to be a series of column headers.")],
        ["skipinitialspace", types.BooleanType, _("Skip initial space"),
         _("When True, whitespace immediately following the delimiter is "
           "ignored.")],
    ]

    type2widget = {
        types.StringType: wx.TextCtrl,
        types.BooleanType: wx.CheckBox,
        types.TupleType: wx.Choice,
        types.IntType: wx.Choice,
    }

    standard_encodings = (
        "utf-8", "ascii", "big5", "big5hkscs", "cp037", "cp424", "cp437",
        "cp500", "cp720", "cp737", "cp775", "cp850", "cp852", "cp855", "cp856",
        "cp857", "cp858", "cp860", "cp861", "cp862", "cp863", "cp864", "cp865",
        "cp866", "cp869", "cp874", "cp875", "cp932", "cp949", "cp950",
        "cp1006", "cp1026", "cp1140", "cp1250", "cp1251", "cp1252", "cp1253",
        "cp1254", "cp1255", "cp1256", "cp1257", "cp1258", "euc-jp",
        "euc-jis-2004", "euc-jisx0213", "euc-kr", "gb2312", "gbk", "gb18030",
        "hz", "iso2022-jp", "iso2022-jp-1", "iso2022-jp-2", "iso2022-jp-2004",
        "iso2022-jp-3", "iso2022-jp-ext", "iso2022-kr", "latin-1", "iso8859-2",
        "iso8859-3", "iso8859-4", "iso8859-5", "iso8859-6", "iso8859-7",
        "iso8859-8", "iso8859-9", "iso8859-10", "iso8859-13", "iso8859-14",
        "iso8859-15", "iso8859-16", "johab", "koi8-r", "koi8-u",
        "mac-cyrillic", "mac-greek", "mac-iceland", "mac-latin2", "mac-roman",
        "mac-turkish", "ptcp154", "shift-jis", "shift-jis-2004",
        "shift-jisx0213", "utf-32", "utf-32-be", "utf-32-le", "utf-16",
        "utf-16-be", "utf-16-le", "utf-7", "utf-8-sig",
    )

    # All tuple types from csv_params have choice boxes
    choices = {
        'dialects': tuple(["sniffer"] + csv.list_dialects() + ["user"]),
        'quoting': ("QUOTE_ALL", "QUOTE_MINIMAL",
                    "QUOTE_NONNUMERIC", "QUOTE_NONE"),
        'encodings': standard_encodings,
    }

    widget_handlers = {
        'encodings': "OnEncoding",
        'dialects': "OnDialectChoice",
        'quoting': "OnWidget",
        'delimiter': "OnWidget",
        'escapechar': "OnWidget",
        'quotechar': "OnWidget",
        'doublequote': "OnWidget",
        'self.has_header': "OnWidget",
        'skipinitialspace': "OnWidget",
    }

    def __init__(self, parent, csvfilepath):
        self.parent = parent
        self.csvfilepath = csvfilepath

        self.encoding = self.standard_encodings[0]

        if csvfilepath is None:
            dialect = csv.get_dialect(csv.list_dialects()[0])
            self.has_header = False
        else:
            dialect, self.has_header = sniff(self.csvfilepath)

        self.param_labels = []
        self.param_widgets = []

        self._setup_param_widgets()
        self._do_layout()
        self._update_settings(dialect)

        self.choice_dialects.SetSelection(0)

    def _setup_param_widgets(self):
        """Creates the parameter entry widgets and binds them to methods"""

        for parameter in self.csv_params:
            pname, ptype, plabel, phelp = parameter

            label = wx.StaticText(self.parent, -1, plabel)
            widget = self.type2widget[ptype](self.parent)

            # Append choicebox items and bind handler
            if pname in self.choices:
                widget.AppendItems(self.choices[pname])
                widget.SetValue = widget.Select
                widget.SetSelection(0)

            # Bind event handler to widget
            if ptype is types.StringType or ptype is types.UnicodeType:
                event_type = wx.EVT_TEXT
            elif ptype is types.BooleanType:
                event_type = wx.EVT_CHECKBOX
            else:
                event_type = wx.EVT_CHOICE

            handler = getattr(self, self.widget_handlers[pname])
            self.parent.Bind(event_type, handler, widget)

            #Tool tips
            label.SetToolTipString(phelp)
            widget.SetToolTipString(phelp)

            label.__name__ = wx.StaticText.__name__.lower()
            widget.__name__ = self.type2widget[ptype].__name__.lower()

            self.param_labels.append(label)
            self.param_widgets.append(widget)

            self.__setattr__("_".join([label.__name__, pname]), label)
            self.__setattr__("_".join([widget.__name__, pname]), widget)

    def _do_layout(self):
        """Sizer hell, returns a sizer that contains all widgets"""

        sizer_csvoptions = wx.FlexGridSizer(3, 4, 5, 5)

        # Adding parameter widgets to sizer_csvoptions
        leftpos = wx.LEFT | wx.ADJUST_MINSIZE
        rightpos = wx.RIGHT | wx.EXPAND

        current_label_margin = 0  # smaller for left column
        other_label_margin = 15

        for label, widget in zip(self.param_labels, self.param_widgets):
            sizer_csvoptions.Add(label, 0, leftpos, current_label_margin)
            sizer_csvoptions.Add(widget, 0, rightpos, current_label_margin)

            current_label_margin, other_label_margin = \
                other_label_margin, current_label_margin

        sizer_csvoptions.AddGrowableCol(1)
        sizer_csvoptions.AddGrowableCol(3)

        self.sizer_csvoptions = sizer_csvoptions

    def _update_settings(self, dialect):
        """Sets the widget settings to those of the chosen dialect"""

        # the first parameter is the dialect itself --> ignore
        for parameter in self.csv_params[2:]:
            pname, ptype, plabel, phelp = parameter

            widget = self._widget_from_p(pname, ptype)

            if ptype is types.TupleType:
                ptype = types.ObjectType

            digest = Digest(acceptable_types=[ptype])

            if pname == 'self.has_header':
                if self.has_header is not None:
                    widget.SetValue(digest(self.has_header))
            else:
                value = getattr(dialect, pname)
                widget.SetValue(digest(value))

    def _widget_from_p(self, pname, ptype):
        """Returns a widget from its ptype and pname"""

        widget_name = self.type2widget[ptype].__name__.lower()
        widget_name = "_".join([widget_name, pname])
        return getattr(self, widget_name)

    def OnEncoding(self, event):
        """Stores encoding information"""

        self.encoding = event.GetString()
        event.Skip()

    def OnDialectChoice(self, event):
        """Updates all param widgets confirming to the selcted dialect"""

        dialect_name = event.GetString()
        value = list(self.choices['dialects']).index(dialect_name)

        if dialect_name == 'sniffer':
            if self.csvfilepath is None:
                event.Skip()
                return None
            dialect, self.has_header = sniff(self.csvfilepath)
        elif dialect_name == 'user':
            event.Skip()
            return None
        else:
            dialect = csv.get_dialect(dialect_name)

        #print dialect, self.has_header
        self._update_settings(dialect)

        self.choice_dialects.SetValue(value)

    def OnWidget(self, event):
        """Update the dialect widget to 'user'"""

        self.choice_dialects.SetValue(len(self.choices['dialects']) - 1)
        event.Skip()

    def get_dialect(self):
        """Returns a new dialect that implements the current selection"""

        parameters = {}

        for parameter in self.csv_params[2:]:
            pname, ptype, plabel, phelp = parameter

            widget = self._widget_from_p(pname, ptype)

            if ptype is types.StringType or ptype is types.UnicodeType:
                parameters[pname] = str(widget.GetValue())
            elif ptype is types.BooleanType:
                parameters[pname] = widget.GetValue()
            elif pname == 'quoting':
                choice = self.choices['quoting'][widget.GetSelection()]
                parameters[pname] = getattr(csv, choice)
            else:
                raise TypeError(_("{type} unknown.").format(type=ptype))

        has_header = parameters.pop("self.has_header")

        try:
            csv.register_dialect('user', **parameters)

        except TypeError, err:
            msg = _("The dialect is invalid. \n "
                    "\nError message:\n{msg}").format(msg=err)
            dlg = wx.MessageDialog(self.parent, msg, style=wx.ID_CANCEL)
            dlg.ShowModal()
            dlg.Destroy()
            raise TypeError(err)

        return csv.get_dialect('user'), has_header


class CSVPreviewGrid(wx.grid.Grid):
    """The grid of the csv import parameter entry panel"""

    shape = [10, 10]

    digest_types = {
        'String': types.StringType,
        'Unicode': types.UnicodeType,
        'Integer': types.IntType,
        'Float': types.FloatType,
        'Boolean': types.BooleanType,
        'Object': types.ObjectType,
    }

    # Only add date and time if dateutil is installed
    try:
        import datetime
        digest_types['Date'] = datetime.date
        digest_types['DateTime'] = datetime.datetime
        digest_types['Time'] = datetime.time
    except ImportError:
        pass

    def __init__(self, *args, **kwargs):
        self.has_header = kwargs.pop('has_header')
        self.csvfilepath = kwargs.pop('csvfilepath')

        super(CSVPreviewGrid, self).__init__(*args, **kwargs)

        self.parent = args[0]

        self.CreateGrid(*self.shape)

        self.dtypes = []

        self.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, self.OnMouse)
        self.Bind(wx.grid.EVT_GRID_EDITOR_CREATED, self.OnGridEditorCreated)

    def OnMouse(self, event):
        """Reduces clicks to enter an edit control"""

        self.SetGridCursor(event.Row, event.Col)
        self.EnableCellEditControl(True)
        event.Skip()

    def _set_properties(self):
        self.SetRowLabelSize(0)
        self.SetColLabelSize(0)
        #self.EnableEditing(0)
        self.EnableDragGridSize(0)

    def OnGridEditorCreated(self, event):
        """Used to capture Editor close events"""

        editor = event.GetControl()
        editor.Bind(wx.EVT_KILL_FOCUS, self.OnGridEditorClosed)

        event.Skip()

    def OnGridEditorClosed(self, event):
        """Event handler for end of output type choice"""

        try:
            dialect, self.has_header = \
                self.parent.csvwidgets.get_dialect()
        except TypeError:
            event.Skip()
            return 0

        self.fill_cells(dialect, self.has_header)

    def fill_cells(self, dialect, has_header):
        """Fills the grid for preview of csv data

        Parameters
        ----------
        dialect: csv,dialect
        \tDialect used for csv reader

        """

        # Get columns from csv
        first_line = get_first_line(self.csvfilepath, dialect)
        self.shape[1] = no_cols = len(first_line)

        if no_cols > self.GetNumberCols():
            missing_cols = no_cols - self.GetNumberCols()
            self.AppendCols(missing_cols)

        elif no_cols < self.GetNumberCols():
            obsolete_cols = self.GetNumberCols() - no_cols
            self.DeleteCols(pos=no_cols - 1, numCols=obsolete_cols)

        # Retrieve type choices
        digest_keys = self.get_digest_keys()

        # Is a header present? --> Import as strings in first line
        if has_header:
            for i, header in enumerate(first_line):
                self.SetCellValue(0, i, header)

        # Add Choices
        for col in xrange(self.shape[1]):
            choice_renderer = ChoiceRenderer(self)
            choice_editor = \
                wx.grid.GridCellChoiceEditor(self.digest_types.keys(), False)
            self.SetCellRenderer(has_header, col, choice_renderer)
            self.SetCellEditor(has_header, col, choice_editor)
            self.SetCellValue(has_header, col, digest_keys[col])

        # Fill in the rest of the lines

        self.dtypes = []
        for key in self.get_digest_keys():
            try:
                self.dtypes.append(self.digest_types[key])
            except KeyError:
                self.dtypes.append(types.NoneType)

        topleft = (has_header + 1, 0)

        digest_gen = csv_digest_gen(self.csvfilepath, dialect, has_header,
                                    self.dtypes)

        for row, col, val in cell_key_val_gen(digest_gen, self.shape, topleft):
            self.SetCellValue(row, col, val)

        self.Refresh()

    def get_digest_keys(self):
        """Returns a list of the type choices"""

        digest_keys = []
        for col in xrange(self.GetNumberCols()):
            digest_key = self.GetCellValue(self.has_header, col)
            if digest_key == "":
                digest_key = self.digest_types.keys()[0]
            digest_keys.append(digest_key)

        return digest_keys

    def get_digest_types(self):
        """Returns a list of the target types"""

        return [self.digest_types[digest_key]
                for digest_key in self.get_digest_keys()]


class CSVPreviewTextCtrl(wx.TextCtrl):
    """The grid of the csv export parameter entry panel"""

    preview_lines = 100  # Lines that are shown in preview

    def fill(self, data, dialect):
        """Fills the grid for preview of csv data

        Parameters
        ----------
        data: 2-dim array of strings
        \tData that is written to preview TextCtrl
        dialect: csv,dialect
        \tDialect used for csv reader

        """

        csvfile = cStringIO.StringIO()
        csvwriter = csv.writer(csvfile, dialect=dialect)

        for i, line in enumerate(data):
            csvwriter.writerow(list(encode_gen(line)))
            if i >= self.preview_lines:
                break

        preview = csvfile.getvalue()
        csvfile.close()
        preview = preview.decode("utf-8").replace("\r\n", "\n")
        self.SetValue(preview)


class CsvImportDialog(wx.Dialog):
    """Dialog for CSV import parameter choice with preview grid

    Parameters:
    -----------
    csvfilepath: string, defaults to '.'
    \tPath and Filename of CSV input file

    """

    def __init__(self, *args, **kwds):
        self.csvfilepath = kwds.pop("csvfilepath")
        self.csvfilename = os.path.split(self.csvfilepath)[1]

        kwds["style"] = \
            wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.THICK_FRAME

        wx.Dialog.__init__(self, *args, **kwds)

        self.csvwidgets = CsvParameterWidgets(self, self.csvfilepath)

        dialect, self.has_header = sniff(self.csvfilepath)

        self.grid = CSVPreviewGrid(self, -1,
                                   has_header=self.has_header,
                                   csvfilepath=self.csvfilepath)

        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "")
        self.button_ok = wx.Button(self, wx.ID_OK, "")

        self._set_properties()
        self._do_layout()

        self.grid.fill_cells(dialect, self.has_header)

    def _set_properties(self):
        """Sets dialog title and size limitations of the widgets"""

        title = _("CSV Import: {filepath}").format(filepath=self.csvfilename)
        self.SetTitle(title)
        self.SetSize((600, 600))

        for button in [self.button_cancel, self.button_ok]:
            button.SetMinSize((80, 28))

    def _do_layout(self):
        """Set sizers"""

        sizer_dialog = wx.FlexGridSizer(3, 1, 0, 0)

        # Sub sizers
        sizer_buttons = wx.FlexGridSizer(1, 3, 5, 5)

        # Adding buttons to sizer_buttons
        for button in [self.button_cancel, self.button_ok]:
            sizer_buttons.Add(button, 0, wx.ALL | wx.EXPAND, 5)

        sizer_buttons.AddGrowableRow(0)
        for col in xrange(3):
            sizer_buttons.AddGrowableCol(col)

        # Adding main components
        sizer_dialog.Add(self.csvwidgets.sizer_csvoptions,
                         0, wx.ALL | wx.EXPAND, 5)
        sizer_dialog.Add(self.grid,  1, wx.ALL | wx.EXPAND, 0)
        sizer_dialog.Add(sizer_buttons,  0, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(sizer_dialog)

        sizer_dialog.AddGrowableRow(1)
        sizer_dialog.AddGrowableCol(0)

        self.Layout()
        self.Centre()


# end of class CsvImportDialog


class CsvExportDialog(wx.Dialog):
    """Dialog for CSV export parameter choice with preview text

    Parameters
    ----------
    data: 2-dim array of strings
    \tData that shall be written for preview

    """

    def __init__(self, *args, **kwds):

        self.data = kwds.pop('data')

        kwds["style"] = \
            wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.THICK_FRAME

        wx.Dialog.__init__(self, *args, **kwds)

        self.csvwidgets = CsvParameterWidgets(self, None)
        dialect = csv.get_dialect(csv.list_dialects()[0])
        self.has_header = False

        style = wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
        self.preview_textctrl = CSVPreviewTextCtrl(self, -1, style=style)

        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "")
        self.button_apply = wx.Button(self, wx.ID_APPLY, "")
        self.button_ok = wx.Button(self, wx.ID_OK, "")

        self._set_properties()
        self._do_layout()

        self.preview_textctrl.fill(data=self.data, dialect=dialect)

        self.Bind(wx.EVT_BUTTON, self.OnButtonApply, self.button_apply)

    def _set_properties(self):
        """Sets dialog title and size limitations of the widgets"""

        self.SetTitle("CSV Export")
        self.SetSize((600, 600))

        for button in [self.button_cancel, self.button_apply, self.button_ok]:
            button.SetMinSize((80, 28))

    def _do_layout(self):
        """Set sizers"""

        sizer_dialog = wx.FlexGridSizer(3, 1, 0, 0)

        # Sub sizers
        sizer_buttons = wx.FlexGridSizer(1, 3, 5, 5)

        # Adding buttons to sizer_buttons
        for button in [self.button_cancel, self.button_apply, self.button_ok]:
            sizer_buttons.Add(button, 0, wx.ALL | wx.EXPAND, 5)

        sizer_buttons.AddGrowableRow(0)
        for col in xrange(3):
            sizer_buttons.AddGrowableCol(col)

        # Adding main components
        sizer_dialog.Add(self.csvwidgets.sizer_csvoptions,
                         0, wx.ALL | wx.EXPAND, 5)
        sizer_dialog.Add(self.preview_textctrl,  1, wx.ALL | wx.EXPAND, 0)
        sizer_dialog.Add(sizer_buttons,  0, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(sizer_dialog)

        sizer_dialog.AddGrowableRow(1)
        sizer_dialog.AddGrowableCol(0)

        self.Layout()
        self.Centre()

    def OnButtonApply(self, event):
        """Updates the preview_textctrl"""

        try:
            dialect, self.has_header = self.csvwidgets.get_dialect()
        except TypeError:
            event.Skip()
            return 0

        self.preview_textctrl.fill(data=self.data, dialect=dialect)

        event.Skip()

# end of class CsvImportDialog


class MacroDialog(wx.Frame, MainWindowEventMixin):
    """Macro management dialog"""

    def __init__(self, parent, macros, *args, **kwds):

        # begin wxGlade: MacroDialog.__init__
        kwds["style"] = \
            wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.THICK_FRAME

        self.parent = parent
        self.macros = macros

        wx.Frame.__init__(self, parent, *args, **kwds)

        self.splitter = wx.SplitterWindow(self, -1,
                                          style=wx.SP_3D | wx.SP_BORDER)

        self.upper_panel = wx.Panel(self.splitter, -1)
        self.lower_panel = wx.Panel(self.splitter, -1)

        style = wx.EXPAND | wx.TE_PROCESS_ENTER | wx.TE_PROCESS_TAB | \
            wx.TE_MULTILINE
        self.codetext_ctrl = PythonSTC(self.upper_panel, -1, style=style)

        style = wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH
        self.result_ctrl = wx.TextCtrl(self.lower_panel, -1, style=style)

        self.ok_button = wx.Button(self.lower_panel, wx.ID_OK)
        self.apply_button = wx.Button(self.lower_panel, wx.ID_APPLY)
        self.close_button = wx.Button(self.lower_panel, wx.ID_CLOSE)

        self._set_properties()
        self._do_layout()

        self.codetext_ctrl.SetText(self.macros)

        # Bindings
        self.Bind(stc.EVT_STC_MODIFIED, self.OnText, self.codetext_ctrl)
        self.Bind(wx.EVT_BUTTON, self.OnOk, self.ok_button)
        self.Bind(wx.EVT_BUTTON, self.OnApply, self.apply_button)
        self.Bind(wx.EVT_BUTTON, self.OnClose, self.close_button)
        parent.Bind(self.EVT_CMD_MACROERR, self.update_result_ctrl)

        # States
        self._ok_pressed = False

    def _do_layout(self):
        """Layout sizers"""

        dialog_main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        upper_sizer = wx.BoxSizer(wx.HORIZONTAL)
        lower_sizer = wx.FlexGridSizer(2, 1, 5, 0)
        lower_sizer.AddGrowableRow(0)
        lower_sizer.AddGrowableCol(0)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        upper_sizer.Add(self.codetext_ctrl, 1, wx.EXPAND, 0)
        lower_sizer.Add(self.result_ctrl, 1, wx.EXPAND, 0)
        lower_sizer.Add(button_sizer, 1, wx.EXPAND, 0)
        button_sizer.Add(self.ok_button, 1, wx.EXPAND, 0)
        button_sizer.Add(self.apply_button, 1, wx.EXPAND, 0)
        button_sizer.Add(self.close_button, 1, wx.EXPAND, 0)

        self.upper_panel.SetSizer(upper_sizer)
        self.lower_panel.SetSizer(lower_sizer)

        self.splitter.SplitHorizontally(self.upper_panel,
                                        self.lower_panel,
                                        400)
        dialog_main_sizer.Add(self.splitter, 1, wx.EXPAND, 0)
        self.SetSizer(dialog_main_sizer)
        self.Layout()

    def _set_properties(self):
        """Setup title, size and tooltips"""

        self.SetTitle(_("Macro list"))
        self.SetSize((800, 600))
        self.codetext_ctrl.SetToolTipString(_("Enter python code here."))
        self.ok_button.SetToolTipString(_("Accept all changes"))
        self.apply_button.SetToolTipString(_("Apply changes to current macro"))
        self.close_button.SetToolTipString(_("Remove current macro"))
        self.splitter.SetBackgroundStyle(wx.BG_STYLE_COLOUR)
        self.result_ctrl.SetMinSize((10, 10))

    def OnText(self, event):
        """Event handler for code control"""

        self.macros = self.codetext_ctrl.GetText()

    def OnOk(self, event):
        """Event handler for Ok button"""

        self._ok_pressed = True
        self.OnApply(event)

    def OnApply(self, event):
        """Event handler for Apply button"""

        # See if we have valid python
        try:
            ast.parse(self.macros)
        except:
            # Grab the traceback and print it for the user
            s = StringIO()
            e = exc_info()
            # usr_tb will more than likely be none because ast throws
            #   SytnaxErrorsas occurring outside of the current
            #   execution frame
            usr_tb = get_user_codeframe(e[2]) or None
            print_exception(e[0], e[1], usr_tb, None, s)
            post_command_event(self.parent, self.MacroErrorMsg,
                               err=s.getvalue())
            success = False
        else:
            self.result_ctrl.SetValue('')
            post_command_event(self.parent, self.MacroReplaceMsg,
                               macros=self.macros)
            post_command_event(self.parent, self.MacroExecuteMsg)
            success = True

        event.Skip()
        return success

    def OnClose(self, event):
        """Event handler for Cancel button"""

        # Warn if any unsaved changes
        if self.parent.grid.code_array.macros != self.macros:
            dlg = wx.MessageDialog(
                self, _("There are changes in the macro editor "
                        "which have not yet been applied.  Are you sure you "
                        "wish to close the editor?"), _("Close Editor"),
                wx.YES_NO | wx.ICON_WARNING)
            if dlg.ShowModal() == wx.ID_NO:
                return

        self.Destroy()

    def update_result_ctrl(self, event):
        """Update event result following execution by main window"""

        # Check to see if macro window still exists
        if not self:
            return

        printLen = 0
        self.result_ctrl.SetValue('')
        if hasattr(event, 'msg'):
            # Output of script (from print statements, for example)
            self.result_ctrl.AppendText(event.msg)
            printLen = len(event.msg)
        if hasattr(event, 'err'):
            # Error messages
            errLen = len(event.err)
            errStyle = wx.TextAttr(wx.RED)
            self.result_ctrl.AppendText(event.err)
            self.result_ctrl.SetStyle(printLen, printLen+errLen, errStyle)

        if not hasattr(event, 'err') or event.err == '':
            # No error passed.  Close dialog if user requested it.
            if self._ok_pressed:
                self.Destroy()
        self._ok_pressed = False


# end of class MacroDialog


class DimensionsEntryDialog(wx.Dialog):
    """Input dialog for the 3 dimensions of a grid"""

    def __init__(self, parent, *args, **kwds):
        kwds["style"] = \
            wx.DEFAULT_DIALOG_STYLE | wx.MINIMIZE_BOX | wx.STAY_ON_TOP
        wx.Dialog.__init__(self, parent, *args, **kwds)

        self.Rows_Label = wx.StaticText(self, -1, _("Rows"),
                                        style=wx.ALIGN_CENTRE)
        self.X_DimensionsEntry = wx.TextCtrl(self, -1, "")
        self.Columns_Label = wx.StaticText(self, -1, _("Columns"),
                                           style=wx.ALIGN_CENTRE)
        self.Y_DimensionsEntry = wx.TextCtrl(self, -1, "")
        self.Tabs_Label = wx.StaticText(self, -1, _("Tables"),
                                        style=wx.ALIGN_CENTRE)
        self.Z_DimensionsEntry = wx.TextCtrl(self, -1, "")

        self.textctrls = [self.X_DimensionsEntry,
                          self.Y_DimensionsEntry,
                          self.Z_DimensionsEntry]

        self.ok_button = wx.Button(self, wx.ID_OK, "")
        self.cancel_button = wx.Button(self, wx.ID_CANCEL, "")

        self._set_properties()
        self._do_layout()

        self.Bind(wx.EVT_TEXT, self.OnXDim, self.X_DimensionsEntry)
        self.Bind(wx.EVT_TEXT, self.OnYDim, self.Y_DimensionsEntry)
        self.Bind(wx.EVT_TEXT, self.OnZDim, self.Z_DimensionsEntry)

        self.dimensions = [1, 1, 1]

    def _set_properties(self):
        """Wx property setup"""

        self.SetTitle("New grid dimensions")
        self.cancel_button.SetDefault()

    def _do_layout(self):
        """Layout sizers"""

        label_style = wx.LEFT | wx.ALIGN_CENTER_VERTICAL
        button_style = wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL | \
            wx.ALIGN_CENTER_VERTICAL | wx.FIXED_MINSIZE

        grid_sizer_1 = wx.GridSizer(4, 2, 3, 3)

        grid_sizer_1.Add(self.Rows_Label, 0, label_style, 3)
        grid_sizer_1.Add(self.X_DimensionsEntry, 0, wx.EXPAND, 0)
        grid_sizer_1.Add(self.Columns_Label, 0, label_style, 3)
        grid_sizer_1.Add(self.Y_DimensionsEntry, 0, wx.EXPAND, 0)
        grid_sizer_1.Add(self.Tabs_Label, 0, label_style, 3)
        grid_sizer_1.Add(self.Z_DimensionsEntry, 0, wx.EXPAND, 0)
        grid_sizer_1.Add(self.ok_button, 0, button_style, 3)
        grid_sizer_1.Add(self.cancel_button, 0, button_style, 3)
        self.SetSizer(grid_sizer_1)
        grid_sizer_1.Fit(self)
        self.Layout()
        self.X_DimensionsEntry.SetFocus()

    def _ondim(self, dimension, valuestring):
        """Converts valuestring to int and assigns result to self.dim

        If there is an error (such as an empty valuestring) or if
        the value is < 1, the value 1 is assigned to self.dim

        Parameters
        ----------

        dimension: int
        \tDimension that is to be updated. Must be in [1:4]
        valuestring: string
        \t A string that can be converted to an int

        """

        try:
            self.dimensions[dimension] = int(valuestring)
        except ValueError:
            self.dimensions[dimension] = 1
            self.textctrls[dimension].SetValue(str(1))

        if self.dimensions[dimension] < 1:
            self.dimensions[dimension] = 1
            self.textctrls[dimension].SetValue(str(1))

    def OnXDim(self, event):
        """Event handler for x dimension TextCtrl"""

        self._ondim(0, event.GetString())
        event.Skip()

    def OnYDim(self, event):
        """Event handler for y dimension TextCtrl"""

        self._ondim(1, event.GetString())
        event.Skip()

    def OnZDim(self, event):
        """Event handler for z dimension TextCtrl"""

        self._ondim(2, event.GetString())
        event.Skip()

# end of class DimensionsEntryDialog


class CellEntryDialog(wx.Dialog, GridEventMixin):
    """Allows entring three digits"""

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "Cell Entry")

        self.parent = parent

        self.SetAutoLayout(True)
        VSPACE = 10

        fgs = wx.FlexGridSizer(0, 2)

        fgs.Add(wx.StaticText(self, -1, _("Goto cell:")))
        fgs.Add((1, 1))
        fgs.Add((1, VSPACE))
        fgs.Add((1, VSPACE))

        label = wx.StaticText(self, -1, _("Row: "))
        fgs.Add(label, 0, wx.ALIGN_RIGHT | wx.CENTER)
        self.row_textctrl = \
            wx.TextCtrl(self, -1, "", validator=IntValidator())
        fgs.Add(self.row_textctrl)

        fgs.Add((1, VSPACE))
        fgs.Add((1, VSPACE))

        label = wx.StaticText(self, -1, _("Column: "))
        fgs.Add(label, 0, wx.ALIGN_RIGHT | wx.CENTER)
        self.col_textctrl = \
            wx.TextCtrl(self, -1, "", validator=IntValidator())

        fgs.Add(self.col_textctrl)
        fgs.Add((1, VSPACE))
        fgs.Add((1, VSPACE))
        label = wx.StaticText(self, -1, _("Table: "))
        fgs.Add(label, 0, wx.ALIGN_RIGHT | wx.CENTER)
        self.tab_textctrl = \
            wx.TextCtrl(self, -1, "", validator=IntValidator())

        fgs.Add(self.tab_textctrl)

        buttons = wx.StdDialogButtonSizer()  # wx.BoxSizer(wx.HORIZONTAL)
        b = wx.Button(self, wx.ID_OK, _("OK"))
        b.SetDefault()
        buttons.AddButton(b)
        buttons.AddButton(wx.Button(self, wx.ID_CANCEL, _("Cancel")))
        buttons.Realize()

        border = wx.BoxSizer(wx.VERTICAL)
        border.Add(fgs, 1, wx.GROW | wx.ALL, 25)
        border.Add(buttons)
        self.SetSizer(border)
        border.Fit(self)
        self.Layout()

        self.Bind(wx.EVT_BUTTON, self.OnOk, id=wx.ID_OK)

    def OnOk(self, event):
        """Posts a command event that makes the grid show the entered cell"""

        # Get key values from textctrls

        key_strings = [self.row_textctrl.GetValue(),
                       self.col_textctrl.GetValue(),
                       self.tab_textctrl.GetValue()]

        key = []

        for key_string in key_strings:
            try:
                key.append(int(key_string))
            except ValueError:
                key.append(0)

        # Post event

        post_command_event(self.parent, self.GotoCellMsg, key=tuple(key))


class AboutDialog(object):
    """Displays information about pyspread"""

    def __init__(self, *args, **kwds):
        # First we create and fill the info object
        parent = args[0]

        info = wx.AboutDialogInfo()
        info.Name = "pyspread"
        info.Version = config["version"]
        info.Copyright = "(C) Martin Manns"
        info.Description = wordwrap(
            _("A non-traditional Python spreadsheet application.\nPyspread is "
              "based on and written in the programming language Python."),
            350, wx.ClientDC(parent))
        info.WebSite = ("http://manns.github.io/pyspread/",
                        _("Pyspread Web site"))
        info.Developers = ["Martin Manns"]
        info.DocWriters = ["Martin Manns", "Bosko Markovic"]
        info.Translators = ["Joe Hansen", "Mark Haanen", "Yuri Chornoivan",
                            u"Mario Blättermann", "Christian Kirbach",
                            "Martin Manns", "Andreas Noteng",
                            "Enrico Nicoletto"]

        license_file = open(get_program_path() + "/COPYING", "r")
        license_text = license_file.read()
        license_file.close()

        info.License = wordwrap(license_text, 500, wx.ClientDC(parent))

        # Then we call wx.AboutBox giving it that info object
        wx.AboutBox(info)

    def _set_properties(self):
        """Setup title and label"""

        self.SetTitle(_("About pyspread"))

        label = _("pyspread {version}\nCopyright Martin Manns")
        label = label.format(version=VERSION)

        self.about_label.SetLabel(label)

    def _do_layout(self):
        """Layout sizers"""

        sizer_v = wx.BoxSizer(wx.VERTICAL)
        sizer_h = wx.BoxSizer(wx.HORIZONTAL)

        style = wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL
        sizer_h.Add(self.logo_pyspread, 0, style, 10)
        sizer_h.Add(self.about_label, 0, style, 10)
        sizer_v.Add(sizer_h)
        self.SetSizer(sizer_v)
        sizer_v.Add(self.button_close, 0, style, 10)
        sizer_v.Fit(self)
        self.Layout()
        self.Centre()

    def OnClose(self, event):
        """Destroys dialog"""

        self.Destroy()

# end of class AboutDialog


class CheckBoxCtrl(wx.CheckBox):
    """CheckBox class that mimicks TextCtrl class"""

    def __init__(self, parent, uid, value, **kwargs):
        wx.CheckBox.__init__(self, parent, uid, **kwargs)
        self.SetValue(value)

    def get_value_str(self):
        """Returns string representation of CheckBox state"""

        return repr(self.GetValue())

    Value = property(get_value_str, wx.CheckBox.SetValue)

# end of class CheckBoxCtrl


class PreferencesDialog(wx.Dialog):
    """Dialog for changing pyspread's configuration preferences"""

    parameters = (
        ("max_unredo", {
            "label": _(u"Max. undo steps"),
            "tooltip": _(u"Maximum number of undo steps"),
            "widget": wx.lib.intctrl.IntCtrl,
            "widget_params": {"min": 0, "allow_long": True},
            "prepocessor": int,
        }),
        ("grid_rows", {
            "label": _(u"Grid rows"),
            "tooltip": _(u"Number of grid rows when starting pyspread"),
            "widget": wx.lib.intctrl.IntCtrl,
            "widget_params": {"min": 0, "allow_long": True},
            "prepocessor": int,
        }),
        ("grid_columns", {
            "label": _(u"Grid columns"),
            "tooltip": _(u"Number of grid columns when starting pyspread"),
            "widget": wx.lib.intctrl.IntCtrl,
            "widget_params": {"min": 0, "allow_long": True},
            "prepocessor": int,
        }),
        ("grid_tables", {
            "label": _(u"Grid tables"),
            "tooltip": _(u"Number of grid tables when starting pyspread"),
            "widget": wx.lib.intctrl.IntCtrl,
            "widget_params": {"min": 0, "allow_long": True},
            "prepocessor": int,
        }),
        ("max_result_length", {
            "label": _(u"Max. result length"),
            "tooltip": _(u"Maximum length of cell result string"),
            "widget": wx.lib.intctrl.IntCtrl,
            "widget_params": {"min": 0, "allow_long": True},
            "prepocessor": int,
        }),
        ("timeout", {
            "label": _(u"Timeout"),
            "tooltip": _(u"Maximum time that an evaluation process may take."),
            "widget": wx.lib.intctrl.IntCtrl,
            "widget_params": {"min": 0, "allow_long": True},
            "prepocessor": int,
        }),
        ("timer_interval", {
            "label": _(u"Timer interval"),
            "tooltip": _(u"Interval for periodic updating of timed cells."),
            "widget": wx.lib.intctrl.IntCtrl,
            "widget_params": {"min": 100, "allow_long": True},
            "prepocessor": int,
        }),
        ("gpg_key_fingerprint", {
            "label": _(u"GPG key id"),
            "tooltip": _(u"Fingerprint of the GPG key for signing files"),
            "widget": wx.TextCtrl,
            "widget_params": {},
            "prepocessor": unicode,
        }),
    )

    def __init__(self, *args, **kwargs):
        kwargs["title"] = _(u"Preferences")
        kwargs["style"] = \
            wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.THICK_FRAME
        wx.Dialog.__init__(self, *args, **kwargs)

        self.labels = []

        # Controls for entering parameters, NOT only TextCtrls
        self.textctrls = []

        self.grid_sizer = wx.FlexGridSizer(0, 2, 2, 2)

        for parameter, info in self.parameters:
            label = info["label"]
            tooltip = info["tooltip"]
            value = config[parameter]

            self.labels.append(wx.StaticText(self, -1, label))
            self.labels[-1].SetToolTipString(tooltip)

            widget = info["widget"]
            preproc = info["prepocessor"]

            ctrl = widget(self, -1, preproc(value), **info["widget_params"])
            ctrl.SetToolTipString(tooltip)

            self.textctrls.append(ctrl)

            self.grid_sizer.Add(self.labels[-1], 0,
                                wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
            self.grid_sizer.Add(self.textctrls[-1], 0,
                                wx.EXPAND | wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                                2)

        self.ok_button = wx.Button(self, wx.ID_OK)
        self.cancel_button = wx.Button(self, wx.ID_CANCEL)
        self.grid_sizer.Add(self.ok_button, 0,
                            wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        self.grid_sizer.Add(self.cancel_button, 0,
                            wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)

        self.SetSizer(self.grid_sizer)

        self.grid_sizer.Fit(self)
        self.grid_sizer.AddGrowableCol(1)

        for row in xrange(len(self.parameters)):
            self.grid_sizer.AddGrowableRow(row)

        self.Layout()

        self.SetSize((300, -1))

# end of class PreferencesDialog


class GPGParamsDialog(wx.Dialog):
    """Gets GPG key parameters from user

    This dialog lets the user choose a new GPG key

    """

    def __init__(self, parent, ID, title, params):
        wx.Dialog.__init__(self, parent, ID, title)

        sizer = wx.FlexGridSizer(len(params), 2, 5, 5)

        label = wx.StaticText(self, -1, _("GPG key data"))
        sizer.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add(wx.Panel(self, -1), 0, wx.ALIGN_CENTRE | wx.ALL, 5)

        self.textctrls = []

        for labeltext, __ in params:
            label = wx.StaticText(self, -1, labeltext)
            sizer.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)

            textctrl = wx.TextCtrl(self, -1, "", size=(80, -1))

            self.textctrls.append(textctrl)

            sizer.Add(textctrl, 1, wx.ALIGN_CENTRE | wx.ALL, 5)

        ok_button = wx.Button(self, wx.ID_OK)
        ok_button.SetToolTipString(_("Starts key generation."))
        ok_button.SetDefault()
        sizer.Add(ok_button)

        cancel_button = wx.Button(self, wx.ID_CANCEL)
        cancel_button.SetToolTipString(_("Exits pyspread."))
        sizer.Add(cancel_button)

        self.SetSizer(sizer)
        sizer.Fit(self)

# end of class GPGParamsDialog


class PasteAsDialog(wx.Dialog):
    """Gets paste as parameters from user

    Parameters
    ----------
    obj: Object
    \tObject that shall be pasted

    """

    def __init__(self, parent, id, obj, *args, **kwargs):
        title = _("Paste as")
        wx.Dialog.__init__(self, parent, id, title, *args, **kwargs)

        sizer = wx.FlexGridSizer(3, 2, 5, 5)

        self.dim_label = wx.StaticText(self, -1, _("Dimension of object"))
        self.dim_spinctrl = wx.SpinCtrl(self, -1, "Dim", (30, 50))
        self.dim_spinctrl.SetRange(0, self.get_max_dim(obj))

        self.transpose_label = wx.StaticText(self, -1, _("Transpose"))
        self.transpose_checkbox = wx.CheckBox(self, -1)

        ok_button = wx.Button(self, wx.ID_OK)
        cancel_button = wx.Button(self, wx.ID_CANCEL)

        sizer.Add(self.dim_label)
        sizer.Add(self.dim_spinctrl)

        sizer.Add(self.transpose_label)
        sizer.Add(self.transpose_checkbox)

        sizer.Add(ok_button)
        sizer.Add(cancel_button)

        self.SetSizer(sizer)
        sizer.Fit(self)

    def get_max_dim(self, obj):
        """Returns maximum dimensionality over which obj is iterable <= 2"""

        try:
            iter(obj)

        except TypeError:
            return 0

        try:
            for o in obj:
                iter(o)
                break

        except TypeError:
            return 1

        return 2

    def get_parameters(self):
        """Returns dict of dialog content"""

        return {
            "dim": self.dim_spinctrl.GetValue(),
            "transpose": self.transpose_checkbox.GetValue()
        }

    parameters = property(get_parameters)

########NEW FILE########
__FILENAME__ = _events
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread. If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
_events
=======

Event handler module

Provides
--------

* post_command_event: Posts a command event

"""

import wx
import wx.lib
import wx.lib.newevent


def post_command_event(target, msg_cls, **kwargs):
    """Posts command event to main window

    Command events propagate.

    Parameters
    ----------
     * msg_cls: class
    \tMessage class from new_command_event()
     * kwargs: dict
    \tMessage arguments

    """

    msg = msg_cls(id=-1, **kwargs)
    wx.PostEvent(target, msg)


new_command_event = wx.lib.newevent.NewCommandEvent


class MainWindowEventMixin(object):
    """Mixin class for mainwindow events"""

    TitleMsg, EVT_CMD_TITLE = new_command_event()

    SafeModeEntryMsg, EVT_CMD_SAFE_MODE_ENTRY = new_command_event()
    SafeModeExitMsg, EVT_CMD_SAFE_MODE_EXIT = new_command_event()

    PreferencesMsg, EVT_CMD_PREFERENCES = new_command_event()

    CloseMsg, EVT_CMD_CLOSE = new_command_event()

    FontDialogMsg, EVT_CMD_FONTDIALOG = new_command_event()
    TextColorDialogMsg, EVT_CMD_TEXTCOLORDIALOG = new_command_event()
    BgColorDialogMsg, EVT_CMD_BGCOLORDIALOG = new_command_event()

    ManualMsg, EVT_CMD_MANUAL = new_command_event()
    TutorialMsg, EVT_CMD_TUTORIAL = new_command_event()
    FaqMsg, EVT_CMD_FAQ = new_command_event()
    PythonTutorialMsg, EVT_CMD_PYTHON_TURORIAL = new_command_event()
    AboutMsg, EVT_CMD_ABOUT = new_command_event()

    MacroListMsg, EVT_CMD_MACROLIST = new_command_event()
    MacroReplaceMsg, EVT_CMD_MACROREPLACE = new_command_event()
    MacroExecuteMsg, EVT_CMD_MACROEXECUTE = new_command_event()
    MacroLoadMsg, EVT_CMD_MACROLOAD = new_command_event()
    MacroSaveMsg, EVT_CMD_MACROSAVE = new_command_event()
    MacroErrorMsg, EVT_CMD_MACROERR = new_command_event()

    MainToolbarToggleMsg, EVT_CMD_MAINTOOLBAR_TOGGLE = new_command_event()
    MacroToolbarToggleMsg, EVT_CMD_MACROTOOLBAR_TOGGLE = new_command_event()
    AttributesToolbarToggleMsg, EVT_CMD_ATTRIBUTESTOOLBAR_TOGGLE = \
                                            new_command_event()
    FindToolbarToggleMsg, EVT_CMD_FIND_TOOLBAR_TOGGLE = new_command_event()
    EntryLineToggleMsg, EVT_CMD_ENTRYLINE_TOGGLE = new_command_event()
    TableChoiceToggleMsg, EVT_CMD_TABLECHOICE_TOGGLE = new_command_event()

    ToolbarUpdateMsg, EVT_CMD_TOOLBAR_UPDATE = new_command_event()

    ContentChangedMsg, EVT_CONTENT_CHANGED = new_command_event()


class GridCellEventMixin(object):
    """Mixin class for grid cell events"""

    # Cell code entry events

    CodeEntryMsg, EVT_CMD_CODE_ENTRY = new_command_event()

    # Cell attribute events

    FontMsg, EVT_CMD_FONT = new_command_event()
    FontSizeMsg, EVT_CMD_FONTSIZE = new_command_event()
    FontBoldMsg, EVT_CMD_FONTBOLD = new_command_event()
    FontItalicsMsg, EVT_CMD_FONTITALICS = new_command_event()
    FontUnderlineMsg, EVT_CMD_FONTUNDERLINE = new_command_event()
    FontStrikethroughMsg, EVT_CMD_FONTSTRIKETHROUGH = new_command_event()
    FrozenMsg, EVT_CMD_FROZEN = new_command_event()
    LockMsg, EVT_CMD_LOCK = new_command_event()
    MergeMsg, EVT_CMD_MERGE = new_command_event()
    JustificationMsg, EVT_CMD_JUSTIFICATION = new_command_event()
    AlignmentMsg, EVT_CMD_ALIGNMENT = new_command_event()
    BorderChoiceMsg, EVT_CMD_BORDERCHOICE = new_command_event()
    BorderWidthMsg, EVT_CMD_BORDERWIDTH = new_command_event()
    BorderColorMsg, EVT_CMD_BORDERCOLOR = new_command_event()
    BackgroundColorMsg, EVT_CMD_BACKGROUNDCOLOR = new_command_event()
    TextColorMsg, EVT_CMD_TEXTCOLOR = new_command_event()
    RotationDialogMsg,  EVT_CMD_ROTATIONDIALOG = new_command_event()
    TextRotationMsg, EVT_CMD_TEXTROTATATION = new_command_event()

    # Cell edit events

    EditorShownMsg, EVT_CMD_EDITORSHOWN = new_command_event()
    EditorHiddenMsg, EVT_CMD_EDITORHIDDEN = new_command_event()

    # Cell selection events

    CellSelectedMsg, EVT_CMD_CELLSELECTED = new_command_event()


class GridEventMixin(object):
    """Mixin class for grid events"""

    # File events

    NewMsg, EVT_CMD_NEW = new_command_event()
    OpenMsg, EVT_CMD_OPEN = new_command_event()
    SaveMsg, EVT_CMD_SAVE = new_command_event()
    SaveAsMsg, EVT_CMD_SAVEAS = new_command_event()
    ImportMsg, EVT_CMD_IMPORT = new_command_event()
    ExportMsg, EVT_CMD_EXPORT = new_command_event()
    ApproveMsg, EVT_CMD_APPROVE = new_command_event()
    ClearGobalsMsg, EVT_CMD_CLEAR_GLOBALS = new_command_event()

    # Print events

    PageSetupMsg, EVT_CMD_PAGE_SETUP = new_command_event()
    PrintPreviewMsg, EVT_CMD_PRINT_PREVIEW = new_command_event()
    PrintMsg, EVT_CMD_PRINT = new_command_event()

    # Clipboard events

    CutMsg, EVT_CMD_CUT = new_command_event()
    CopyMsg, EVT_CMD_COPY = new_command_event()
    CopyResultMsg, EVT_CMD_COPY_RESULT = new_command_event()
    PasteMsg, EVT_CMD_PASTE = new_command_event()
    PasteAsMsg, EVT_CMD_PASTE_AS = new_command_event()

    # Sorting events
    SortAscendingMsg, EVT_CMD_SORT_ASCENDING = new_command_event()
    SortDescendingMsg, EVT_CMD_SORT_DESCENDING = new_command_event()

    # Grid edit mode events

    SelectAll, EVT_CMD_SELECT_ALL = new_command_event()
    EnterSelectionModeMsg, EVT_CMD_ENTER_SELECTION_MODE = new_command_event()
    ExitSelectionModeMsg, EVT_CMD_EXIT_SELECTION_MODE = new_command_event()
    SelectionMsg, EVT_CMD_SELECTION = new_command_event()

    # Grid view events

    ViewFrozenMsg, EVT_CMD_VIEW_FROZEN = new_command_event()
    RefreshSelectionMsg, EVT_CMD_REFRESH_SELECTION = new_command_event()
    TimerToggleMsg, EVT_CMD_TIMER_TOGGLE = new_command_event()
    DisplayGotoCellDialogMsg, EVT_CMD_DISPLAY_GOTO_CELL_DIALOG = \
        new_command_event()
    GotoCellMsg, EVT_CMD_GOTO_CELL = new_command_event()
    ZoomInMsg, EVT_CMD_ZOOM_IN = new_command_event()
    ZoomOutMsg, EVT_CMD_ZOOM_OUT = new_command_event()
    ZoomStandardMsg, EVT_CMD_ZOOM_STANDARD = new_command_event()

    # Find events

    FindMsg, EVT_CMD_FIND = new_command_event()
    FindFocusMsg, EVT_CMD_FOCUSFIND = new_command_event()
    ReplaceMsg, EVT_CMD_REPLACE = new_command_event()

    # Grid change events

    InsertRowsMsg, EVT_CMD_INSERT_ROWS = new_command_event()
    InsertColsMsg, EVT_CMD_INSERT_COLS = new_command_event()
    InsertTabsMsg, EVT_CMD_INSERT_TABS = new_command_event()
    DeleteRowsMsg, EVT_CMD_DELETE_ROWS = new_command_event()
    DeleteColsMsg, EVT_CMD_DELETE_COLS = new_command_event()
    DeleteTabsMsg, EVT_CMD_DELETE_TABS = new_command_event()

    ShowResizeGridDialogMsg, EVT_CMD_SHOW_RESIZE_GRID_DIALOG = \
        new_command_event()

    QuoteMsg, EVT_CMD_QUOTE = new_command_event()

    TableChangedMsg, EVT_CMD_TABLE_CHANGED = new_command_event()

    InsertBitmapMsg, EVT_CMD_INSERT_BMP = new_command_event()
    LinkBitmapMsg, EVT_CMD_LINK_BMP = new_command_event()
    InsertChartMsg, EVT_CMD_INSERT_CHART = new_command_event()
    ResizeGridMsg, EVT_CMD_RESIZE_GRID = new_command_event()

    # Grid attribute events

    # Undo/Redo events

    UndoMsg, EVT_CMD_UNDO = new_command_event()
    RedoMsg, EVT_CMD_REDO = new_command_event()


class GridActionEventMixin(object):
    """Mixin class for grid action events"""

    # Tuple dim
    GridActionNewMsg, EVT_CMD_GRID_ACTION_NEW = new_command_event()

    # Attr dict: keys: filepath: string, interface: object
    GridActionOpenMsg, EVT_CMD_GRID_ACTION_OPEN = new_command_event()
    GridActionSaveMsg, EVT_CMD_GRID_ACTION_SAVE = new_command_event()

    # For calling the grid
    GridActionTableSwitchMsg, EVT_CMD_GRID_ACTION_TABLE_SWITCH = \
                                                      new_command_event()


class EntryLineEventMixin(object):
    """Mixin class for entry line events"""

    EntryLineMsg, EVT_ENTRYLINE_MSG = new_command_event()
    LockEntryLineMsg, EVT_ENTRYLINE_LOCK = new_command_event()
    ##EntryLineSelectionMsg, EVT_ENTRYLINE_SELECTION_MSG = new_command_event()


class StatusBarEventMixin(object):
    """Mixin class for statusbar events"""

    StatusBarMsg, EVT_STATUSBAR_MSG = wx.lib.newevent.NewEvent()


class EventMixin(MainWindowEventMixin, GridCellEventMixin, StatusBarEventMixin,
                 GridActionEventMixin, EntryLineEventMixin, GridEventMixin):
    """Event collector class"""

    pass


class ChartDialogEventMixin(object):
    """Mixin class for chart dialog events.

    Class remains independent from EventMixin container class

    """

    DrawChartMsg, EVT_CMD_DRAW_CHART = new_command_event()
########NEW FILE########
__FILENAME__ = _grid
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
_grid
=====

Provides
--------
 1. Grid: The main grid of pyspread
 2. MainWindowEventHandlers: Event handlers for Grid

"""

import wx.grid

from _events import post_command_event, EventMixin

from _grid_table import GridTable
from _grid_renderer import GridRenderer
from _gui_interfaces import GuiInterfaces
from _menubars import ContextMenu
from _chart_dialog import ChartDialog

import src.lib.i18n as i18n
from src.sysvars import is_gtk
from src.config import config

from src.lib.selection import Selection
from src.model.model import CodeArray

from src.actions._grid_actions import AllGridActions
from src.gui._grid_cell_editor import GridCellEditor

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


class Grid(wx.grid.Grid, EventMixin):
    """Pyspread's main grid"""

    def __init__(self, main_window, *args, **kwargs):
        S = kwargs.pop("S")

        self.main_window = main_window

        self._states()

        self.interfaces = GuiInterfaces(self.main_window)

        if S is None:
            dimensions = kwargs.pop("dimensions")
        else:
            dimensions = S.shape
            kwargs.pop("dimensions")

        wx.grid.Grid.__init__(self, main_window, *args, **kwargs)

        self.SetDefaultCellBackgroundColour(wx.Colour(255, 255, 255, 255))

        # Cursor position on entering selection mode
        self.sel_mode_cursor = None

        # Set multi line editor
        self.SetDefaultEditor(GridCellEditor(main_window))

        # Create new grid
        if S is None:
            self.code_array = CodeArray(dimensions)
            post_command_event(self, self.GridActionNewMsg, shape=dimensions)
        else:
            self.code_array = S

        _grid_table = GridTable(self, self.code_array)
        self.SetTable(_grid_table, True)

        # Grid renderer draws the grid
        self.grid_renderer = GridRenderer(self.code_array)
        self.SetDefaultRenderer(self.grid_renderer)

        # Context menu for quick access of important functions
        self.contextmenu = ContextMenu(parent=self)

        # Handler classes contain event handler methods
        self.handlers = GridEventHandlers(self)
        self.cell_handlers = GridCellEventHandlers(self)

        # Grid actions
        self.actions = AllGridActions(self)

        # Layout and bindings
        self._layout()
        self._bind()

        # Update toolbars
        self.update_entry_line()
        self.update_attribute_toolbar()

        # Focus on grid so that typing can start immediately
        self.SetFocus()

    def _states(self):
        """Sets grid states"""

        # The currently visible table
        self.current_table = 0

        # The cell that has been selected before the latest selection
        self._last_selected_cell = 0, 0, 0

        # If we are viewing cells based on their frozen status or normally
        #  (When true, a cross-hatch is displayed for frozen cells)
        self._view_frozen = False

        # Timer for updating frozen cells
        self.timer_running = False

    def _layout(self):
        """Initial layout of grid"""

        self.EnableGridLines(False)

        # Standard row and col sizes for zooming
        self.std_row_size = self.GetRowSize(0)
        self.std_col_size = self.GetColSize(0)

        # Standard row and col label sizes for zooming
        self.col_label_size = self.GetColLabelSize()
        self.row_label_size = self.GetRowLabelSize()

        self.SetRowMinimalAcceptableHeight(1)
        self.SetColMinimalAcceptableWidth(1)

        self.SetCellHighlightPenWidth(0)

    def _bind(self):
        """Bind events to handlers"""

        main_window = self.main_window

        handlers = self.handlers
        c_handlers = self.cell_handlers

        # Non wx.Grid events

        self.Bind(wx.EVT_MOUSEWHEEL, handlers.OnMouseWheel)
        self.Bind(wx.EVT_KEY_DOWN, handlers.OnKey)

        # Grid events

        self.GetGridWindow().Bind(wx.EVT_MOTION, handlers.OnMouseMotion)
        self.Bind(wx.grid.EVT_GRID_RANGE_SELECT, handlers.OnRangeSelected)

        # Context menu

        self.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, handlers.OnContextMenu)

        # Cell code events

        main_window.Bind(self.EVT_CMD_CODE_ENTRY, c_handlers.OnCellText)

        main_window.Bind(self.EVT_CMD_INSERT_BMP, c_handlers.OnInsertBitmap)
        main_window.Bind(self.EVT_CMD_LINK_BMP, c_handlers.OnLinkBitmap)
        main_window.Bind(self.EVT_CMD_INSERT_CHART,
                         c_handlers.OnInsertChartDialog)

        # Cell attribute events

        main_window.Bind(self.EVT_CMD_FONT, c_handlers.OnCellFont)
        main_window.Bind(self.EVT_CMD_FONTSIZE, c_handlers.OnCellFontSize)
        main_window.Bind(self.EVT_CMD_FONTBOLD, c_handlers.OnCellFontBold)
        main_window.Bind(self.EVT_CMD_FONTITALICS,
                         c_handlers.OnCellFontItalics)
        main_window.Bind(self.EVT_CMD_FONTUNDERLINE,
                         c_handlers.OnCellFontUnderline)
        main_window.Bind(self.EVT_CMD_FONTSTRIKETHROUGH,
                         c_handlers.OnCellFontStrikethrough)
        main_window.Bind(self.EVT_CMD_FROZEN, c_handlers.OnCellFrozen)
        main_window.Bind(self.EVT_CMD_LOCK, c_handlers.OnCellLocked)
        main_window.Bind(self.EVT_CMD_MERGE, c_handlers.OnMerge)
        main_window.Bind(self.EVT_CMD_JUSTIFICATION,
                         c_handlers.OnCellJustification)
        main_window.Bind(self.EVT_CMD_ALIGNMENT, c_handlers.OnCellAlignment)
        main_window.Bind(self.EVT_CMD_BORDERWIDTH,
                         c_handlers.OnCellBorderWidth)
        main_window.Bind(self.EVT_CMD_BORDERCOLOR,
                         c_handlers.OnCellBorderColor)
        main_window.Bind(self.EVT_CMD_BACKGROUNDCOLOR,
                         c_handlers.OnCellBackgroundColor)
        main_window.Bind(self.EVT_CMD_TEXTCOLOR, c_handlers.OnCellTextColor)
        main_window.Bind(self.EVT_CMD_ROTATIONDIALOG,
                         c_handlers.OnTextRotationDialog)
        main_window.Bind(self.EVT_CMD_TEXTROTATATION,
                         c_handlers.OnCellTextRotation)

        # Cell selection events

        self.Bind(wx.grid.EVT_GRID_CMD_SELECT_CELL, c_handlers.OnCellSelected)

        # Grid edit mode events

        main_window.Bind(self.EVT_CMD_ENTER_SELECTION_MODE,
                         handlers.OnEnterSelectionMode)
        main_window.Bind(self.EVT_CMD_EXIT_SELECTION_MODE,
                         handlers.OnExitSelectionMode)

        # Grid view events

        main_window.Bind(self.EVT_CMD_VIEW_FROZEN, handlers.OnViewFrozen)
        main_window.Bind(self.EVT_CMD_REFRESH_SELECTION,
                         handlers.OnRefreshSelectedCells)
        main_window.Bind(self.EVT_CMD_TIMER_TOGGLE,
                         handlers.OnTimerToggle)
        self.Bind(wx.EVT_TIMER, handlers.OnTimer)
        main_window.Bind(self.EVT_CMD_DISPLAY_GOTO_CELL_DIALOG,
                         handlers.OnDisplayGoToCellDialog)
        main_window.Bind(self.EVT_CMD_GOTO_CELL, handlers.OnGoToCell)
        main_window.Bind(self.EVT_CMD_ZOOM_IN, handlers.OnZoomIn)
        main_window.Bind(self.EVT_CMD_ZOOM_OUT, handlers.OnZoomOut)
        main_window.Bind(self.EVT_CMD_ZOOM_STANDARD, handlers.OnZoomStandard)

        # Find events
        main_window.Bind(self.EVT_CMD_FIND, handlers.OnFind)
        main_window.Bind(self.EVT_CMD_REPLACE, handlers.OnShowFindReplace)
        main_window.Bind(wx.EVT_FIND, handlers.OnReplaceFind)
        main_window.Bind(wx.EVT_FIND_NEXT, handlers.OnReplaceFind)
        main_window.Bind(wx.EVT_FIND_REPLACE, handlers.OnReplace)
        main_window.Bind(wx.EVT_FIND_REPLACE_ALL, handlers.OnReplaceAll)
        main_window.Bind(wx.EVT_FIND_CLOSE, handlers.OnCloseFindReplace)

        # Grid change events

        main_window.Bind(self.EVT_CMD_INSERT_ROWS, handlers.OnInsertRows)
        main_window.Bind(self.EVT_CMD_INSERT_COLS, handlers.OnInsertCols)
        main_window.Bind(self.EVT_CMD_INSERT_TABS, handlers.OnInsertTabs)

        main_window.Bind(self.EVT_CMD_DELETE_ROWS, handlers.OnDeleteRows)
        main_window.Bind(self.EVT_CMD_DELETE_COLS, handlers.OnDeleteCols)
        main_window.Bind(self.EVT_CMD_DELETE_TABS, handlers.OnDeleteTabs)

        main_window.Bind(self.EVT_CMD_SHOW_RESIZE_GRID_DIALOG,
                         handlers.OnResizeGridDialog)
        main_window.Bind(self.EVT_CMD_QUOTE, handlers.OnQuote)

        main_window.Bind(wx.grid.EVT_GRID_ROW_SIZE, handlers.OnRowSize)
        main_window.Bind(wx.grid.EVT_GRID_COL_SIZE, handlers.OnColSize)

        main_window.Bind(self.EVT_CMD_SORT_ASCENDING, handlers.OnSortAscending)
        main_window.Bind(self.EVT_CMD_SORT_DESCENDING,
                         handlers.OnSortDescending)

        # Undo/Redo events

        main_window.Bind(self.EVT_CMD_UNDO, handlers.OnUndo)
        main_window.Bind(self.EVT_CMD_REDO, handlers.OnRedo)

    _get_selection = lambda self: self.actions.get_selection()
    selection = property(_get_selection, doc="Grid selection")

    # Collison helper functions for grid drawing
    # ------------------------------------------

    def is_merged_cell_drawn(self, key):
        """True if key in merged area shall be drawn

        This is the case if it is the top left most visible key of the merge
        area on the screen.

        """

        row, col, tab = key

        # Is key not merged? --> False
        cell_attributes = self.code_array.cell_attributes

        top, left, __ = cell_attributes.get_merging_cell(key)

        # Case 1: Top left cell of merge is visible
        # --> Only top left cell returns True
        top_left_drawn = \
            row == top and col == left and \
            self.IsVisible(row, col, wholeCellVisible=False)

        # Case 2: Leftmost column is visible
        # --> Only top visible leftmost cell returns True

        left_drawn = \
            col == left and \
            self.IsVisible(row, col, wholeCellVisible=False) and \
            not self.IsVisible(row-1, col, wholeCellVisible=False)

        # Case 3: Top row is visible
        # --> Only left visible top cell returns True

        top_drawn = \
            row == top and \
            self.IsVisible(row, col, wholeCellVisible=False) and \
            not self.IsVisible(row, col-1, wholeCellVisible=False)

        # Case 4: Top row and leftmost column are invisible
        # --> Only top left visible cell returns True

        middle_drawn = \
            self.IsVisible(row, col, wholeCellVisible=False) and \
            not self.IsVisible(row-1, col, wholeCellVisible=False) and \
            not self.IsVisible(row, col-1, wholeCellVisible=False)

        return top_left_drawn or left_drawn or top_drawn or middle_drawn

    def update_entry_line(self, key=None):
        """Updates the entry line

        Parameters
        ----------
        key: 3-tuple of Integer, defaults to current cell
        \tCell to which code the entry line is updated

        """

        if key is None:
            key = self.actions.cursor

        cell_code = self.GetTable().GetValue(*key)

        post_command_event(self, self.EntryLineMsg, text=cell_code)

    def lock_entry_line(self, lock):
        """Lock or unlock entry line

        Parameters
        ----------
        lock: Bool
        \tIf True then the entry line is locked if Falsse unlocked

        """

        post_command_event(self, self.LockEntryLineMsg, lock=lock)

    def update_attribute_toolbar(self, key=None):
        """Updates the attribute toolbar

        Parameters
        ----------
        key: 3-tuple of Integer, defaults to current cell
        \tCell to which attributes the attributes toolbar is updated

        """

        if key is None:
            key = self.actions.cursor

        post_command_event(self, self.ToolbarUpdateMsg, key=key,
                           attr=self.code_array.cell_attributes[key])

# End of class Grid


class GridCellEventHandlers(object):
    """Contains grid cell event handlers incl. attribute events"""

    def __init__(self, grid):
        self.grid = grid

    # Cell code entry events

    def OnCellText(self, event):
        """Text entry event handler"""

        row, col, _ = self.grid.actions.cursor

        self.grid.GetTable().SetValue(row, col, event.code)

        event.Skip()

    def OnInsertBitmap(self, event):
        """Insert bitmap event handler"""

        # Get file name
        wildcard = "*"
        message = _("Select bitmap for current cell")
        style = wx.OPEN | wx.CHANGE_DIR
        filepath, __ = \
            self.grid.interfaces.get_filepath_findex_from_user(wildcard,
                                                               message, style)

        try:
            img = wx.EmptyImage(1, 1)
            img.LoadFile(filepath)
        except TypeError:
            return

        if img.GetSize() == (-1, -1):
            # Bitmap could not be read
            return

        key = self.grid.actions.cursor
        code = self.grid.main_window.actions.img2code(key, img)

        self.grid.actions.set_code(key, code)

    def OnLinkBitmap(self, event):
        """Link bitmap event handler"""

        # Get file name
        wildcard = "*"
        message = _("Select bitmap for current cell")
        style = wx.OPEN | wx.CHANGE_DIR
        filepath, __ = \
            self.grid.interfaces.get_filepath_findex_from_user(wildcard,
                                                               message, style)
        try:
            bmp = wx.Bitmap(filepath)
        except TypeError:
            return

        if bmp.Size == (-1, -1):
            # Bitmap could not be read
            return

        code = "wx.Bitmap(r'{filepath}')".format(filepath=filepath)

        key = self.grid.actions.cursor
        self.grid.actions.set_code(key, code)

    def OnInsertChartDialog(self, event):
        """Chart dialog event handler"""

        key = self.grid.actions.cursor

        cell_code = self.grid.code_array(key)

        if cell_code is None:
            cell_code = u""

        chart_dialog = ChartDialog(self.grid.main_window, key, cell_code)

        if chart_dialog.ShowModal() == wx.ID_OK:
            code = chart_dialog.get_code()
            key = self.grid.actions.cursor
            self.grid.actions.set_code(key, code)

    # Cell attribute events

    def OnCellFont(self, event):
        """Cell font event handler"""

        self.grid.actions.set_attr("textfont", event.font)

        self.grid.ForceRefresh()

        self.grid.update_attribute_toolbar()

        event.Skip()

    def OnCellFontSize(self, event):
        """Cell font size event handler"""

        self.grid.actions.set_attr("pointsize", event.size)

        self.grid.ForceRefresh()

        self.grid.update_attribute_toolbar()

        event.Skip()

    def OnCellFontBold(self, event):
        """Cell font bold event handler"""

        try:
            try:
                weight = getattr(wx, event.weight[2:])

            except AttributeError:
                msg = _("Weight {weight} unknown").format(weight=event.weight)
                raise ValueError(msg)

            self.grid.actions.set_attr("fontweight", weight)

        except AttributeError:
            self.grid.actions.toggle_attr("fontweight")

        self.grid.ForceRefresh()

        self.grid.update_attribute_toolbar()

        event.Skip()

    def OnCellFontItalics(self, event):
        """Cell font italics event handler"""

        try:
            try:
                style = getattr(wx, event.style[2:])

            except AttributeError:
                msg = _("Style {style} unknown").format(style=event.style)
                raise ValueError(msg)

            self.grid.actions.set_attr("fontstyle", style)

        except AttributeError:
            self.grid.actions.toggle_attr("fontstyle")

        self.grid.ForceRefresh()

        self.grid.update_attribute_toolbar()

        event.Skip()

    def OnCellFontUnderline(self, event):
        """Cell font underline event handler"""

        self.grid.actions.toggle_attr("underline")

        self.grid.ForceRefresh()

        self.grid.update_attribute_toolbar()

        event.Skip()

    def OnCellFontStrikethrough(self, event):
        """Cell font strike through event handler"""

        self.grid.actions.toggle_attr("strikethrough")

        self.grid.ForceRefresh()

        self.grid.update_attribute_toolbar()

        event.Skip()

    def OnCellFrozen(self, event):
        """Cell frozen event handler"""

        self.grid.actions.change_frozen_attr()

        self.grid.ForceRefresh()

        self.grid.update_attribute_toolbar()

        event.Skip()

    def OnCellLocked(self, event):
        """Cell locked event handler"""

        self.grid.actions.toggle_attr("locked")

        self.grid.ForceRefresh()

        self.grid.update_attribute_toolbar()

        event.Skip()

    def OnMerge(self, event):
        """Merge cells event handler"""

        self.grid.actions.merge_selected_cells(self.grid.selection)

        self.grid.ForceRefresh()

        self.grid.update_attribute_toolbar()

    def OnCellJustification(self, event):
        """Horizontal cell justification event handler"""

        self.grid.actions.toggle_attr("justification")

        self.grid.ForceRefresh()

        self.grid.update_attribute_toolbar()

        event.Skip()

    def OnCellAlignment(self, event):
        """Vertical cell alignment event handler"""

        self.grid.actions.toggle_attr("vertical_align")

        self.grid.ForceRefresh()

        self.grid.update_attribute_toolbar()

        event.Skip()

    def OnCellBorderWidth(self, event):
        """Cell border width event handler"""

        self.grid.actions.set_border_attr("borderwidth",
                                          event.width, event.borders)

        self.grid.ForceRefresh()

        self.grid.update_attribute_toolbar()

        event.Skip()

    def OnCellBorderColor(self, event):
        """Cell border color event handler"""

        self.grid.actions.set_border_attr("bordercolor",
                                          event.color, event.borders)

        self.grid.ForceRefresh()

        self.grid.update_attribute_toolbar()

        event.Skip()

    def OnCellBackgroundColor(self, event):
        """Cell background color event handler"""

        self.grid.actions.set_attr("bgcolor", event.color)

        self.grid.ForceRefresh()

        self.grid.update_attribute_toolbar()

        event.Skip()

    def OnCellTextColor(self, event):
        """Cell text color event handler"""

        self.grid.actions.set_attr("textcolor", event.color)

        self.grid.ForceRefresh()

        self.grid.update_attribute_toolbar()

        event.Skip()

    def OnTextRotationDialog(self, event):
        """Text rotation dialog event handler"""

        cond_func = lambda i: 0 <= i <= 359
        get_int = self.grid.interfaces.get_int_from_user
        angle = get_int(_("Enter text angle in degrees."), cond_func)

        if angle is not None:
            post_command_event(self.grid.main_window,
                               self.grid.TextRotationMsg, angle=angle)

        self.grid.ForceRefresh()

        self.grid.update_attribute_toolbar()

    def OnCellTextRotation(self, event):
        """Cell text rotation event handler"""

        self.grid.actions.set_attr("angle", event.angle, mark_unredo=True)

        self.grid.ForceRefresh()

        self.grid.update_attribute_toolbar()

        if is_gtk():
            wx.Yield()

        event.Skip()

    def OnCellSelected(self, event):
        """Cell selection event handler"""

        # If in selection mode do nothing
        # This prevents the current cell from changing
        if not self.grid.IsEditable():
            return

        key = row, col, tab = event.Row, event.Col, self.grid.current_table

        # Is the cell merged then go to merging cell
        merge_area = self.grid.code_array.cell_attributes[key]["merge_area"]

        if merge_area is not None:
            top, left, bottom, right = merge_area
            if self.grid._last_selected_cell == (top, left, tab):
                if row == top + 1:
                    self.grid.actions.set_cursor((bottom + 1, left, tab))
                    return
                elif col == left + 1:
                    self.grid.actions.set_cursor((top, right + 1, tab))
                    return
            elif (row, col) != (top, left):
                self.grid.actions.set_cursor((top, left, tab))
                return

        # Redraw cursor
        self.grid.ForceRefresh()

        # Disable entry line if cell is locked
        self.grid.lock_entry_line(
            self.grid.code_array.cell_attributes[key]["locked"])

        # Update entry line
        self.grid.update_entry_line(key)

        # Update attribute toolbar
        self.grid.update_attribute_toolbar(key)

        self.grid._last_selected_cell = key

        event.Skip()


class GridEventHandlers(object):
    """Contains grid event handlers"""

    def __init__(self, grid):
        self.grid = grid
        self.interfaces = grid.interfaces
        self.main_window = grid.main_window

    def OnMouseMotion(self, event):
        """Mouse motion event handler"""

        grid = self.grid

        pos_x, pos_y = grid.CalcUnscrolledPosition(event.GetPosition())

        row = grid.YToRow(pos_y)
        col = grid.XToCol(pos_x)
        tab = grid.current_table

        key = row, col, tab

        merge_area = self.grid.code_array.cell_attributes[key]["merge_area"]
        if merge_area is not None:
            top, left, bottom, right = merge_area
            row, col = top, left

        grid.actions.on_mouse_over((row, col, tab))

        event.Skip()

    def OnKey(self, event):
        """Handles non-standard shortcut events"""

        grid = self.grid
        actions = grid.actions

        shift, alt, ctrl = 1, 1 << 1, 1 << 2

        # Shortcuts key tuple: (modifier, keycode)
        # Modifier may be e. g. shift | ctrl

        shortcuts = {
            # <Esc> pressed
            (0, 27): lambda: setattr(actions, "need_abort", True),
            # <Del> pressed
            (0, 127): actions.delete,
            # <Home> pressed
            (0, 313): lambda: actions.set_cursor((grid.GetGridCursorRow(), 0)),
            # <Ctrl> + R pressed
            (ctrl, 82): actions.copy_selection_access_string,
            # <Ctrl> + + pressed
            (ctrl, 388): actions.zoom_in,
            # <Ctrl> + - pressed
            (ctrl, 390): actions.zoom_out,
            # <Shift> + <Space> pressed
            (shift, 32): lambda: grid.SelectRow(grid.GetGridCursorRow()),
            # <Ctrl> + <Space> pressed
            (ctrl, 32): lambda: grid.SelectCol(grid.GetGridCursorCol()),
            # <Shift> + <Ctrl> + <Space> pressed
            (shift | ctrl, 32): grid.SelectAll,
        }

        keycode = event.GetKeyCode()
        #print keycode

        modifier = shift * event.ShiftDown() | \
            alt * event.AltDown() | ctrl * event.ControlDown()

        if (modifier, keycode) in shortcuts:
            shortcuts[(modifier, keycode)]()

        else:
            event.Skip()

    def OnRangeSelected(self, event):
        """Event handler for grid selection"""

        # If grid editing is disabled then pyspread is in selection mode
        if not self.grid.IsEditable():
            selection = self.grid.selection
            row, col, __ = self.grid.sel_mode_cursor
            if (row, col) in selection:
                self.grid.ClearSelection()
            else:
                self.grid.SetGridCursor(row, col)
                post_command_event(self.grid, self.grid.SelectionMsg,
                                   selection=selection)

    # Grid view events

    def OnViewFrozen(self, event):
        """Show cells as frozen status"""

        self.grid._view_frozen = not self.grid._view_frozen

        self.grid.ForceRefresh()

        event.Skip()

    def OnDisplayGoToCellDialog(self, event):
        """Shift a given cell into view"""

        self.interfaces.display_gotocell()

        event.Skip()

    def OnGoToCell(self, event):
        """Shift a given cell into view"""

        row, col, tab = event.key

        self.grid.actions.cursor = row, col, tab
        self.grid.MakeCellVisible(row, col)

        event.Skip()

    def OnEnterSelectionMode(self, event):
        """Event handler for entering selection mode, disables cell edits"""

        self.grid.sel_mode_cursor = list(self.grid.actions.cursor)
        self.grid.EnableDragGridSize(False)
        self.grid.EnableEditing(False)

    def OnExitSelectionMode(self, event):
        """Event handler for leaving selection mode, enables cell edits"""

        self.grid.sel_mode_cursor = None
        self.grid.EnableDragGridSize(True)
        self.grid.EnableEditing(True)

    def OnRefreshSelectedCells(self, event):
        """Event handler for refreshing the selected cells via menu"""

        self.grid.actions.refresh_selected_frozen_cells()
        self.grid.ForceRefresh()

        event.Skip()

    def OnTimerToggle(self, event):
        """Toggles the timer for updating frozen cells"""

        if self.grid.timer_running:
            # Stop timer
            self.grid.timer_running = False
            self.grid.timer.Stop()
            del self.grid.timer

        else:
            # Start timer
            self.grid.timer_running = True
            self.grid.timer = wx.Timer(self.grid)
            self.grid.timer.Start(config["timer_interval"])

    def OnTimer(self, event):
        """Update all frozen cells because of timer call"""

        self.timer_updating = True

        shape = self.grid.code_array.shape[:2]
        selection = Selection([(0, 0)], [(shape)], [], [], [])
        self.grid.actions.refresh_selected_frozen_cells(selection)
        self.grid.ForceRefresh()

    def OnZoomIn(self, event):
        """Event handler for increasing grid zoom"""

        self.grid.actions.zoom_in()

        event.Skip()

    def OnZoomOut(self, event):
        """Event handler for decreasing grid zoom"""

        self.grid.actions.zoom_out()

        event.Skip()

    def OnZoomStandard(self, event):
        """Event handler for resetting grid zoom"""

        self.grid.actions.zoom(zoom=1.0)

        event.Skip()

    def OnContextMenu(self, event):
        """Context menu event handler"""

        self.grid.PopupMenu(self.grid.contextmenu)

        event.Skip()

    def OnMouseWheel(self, event):
        """Event handler for mouse wheel actions

        Invokes zoom when mouse when Ctrl is also pressed

        """

        if event.ControlDown():
            if event.WheelRotation > 0:
                post_command_event(self.grid, self.grid.ZoomInMsg)
            else:
                post_command_event(self.grid, self.grid.ZoomOutMsg)
        else:
            event.Skip()

    # Find events

    def OnFind(self, event):
        """Find functionality, called from toolbar, returns find position"""

        # Search starts in next cell after the current one
        gridpos = list(self.grid.actions.cursor)
        text, flags = event.text, event.flags
        findpos = self.grid.actions.find(gridpos, text, flags)

        if findpos is None:
            # If nothing is found mention it in the statusbar and return

            statustext = _("'{text}' not found.").format(text=text)

        else:
            # Otherwise select cell with next occurrence if successful
            self.grid.actions.cursor = findpos

            # Update statusbar
            statustext = _(u"Found '{text}' in cell {key}.")
            statustext = statustext.format(text=text, key=findpos)

        post_command_event(self.grid.main_window, self.grid.StatusBarMsg,
                           text=statustext)

        event.Skip()

    def OnShowFindReplace(self, event):
        """Calls the find-replace dialog"""

        data = wx.FindReplaceData(wx.FR_DOWN)
        dlg = wx.FindReplaceDialog(self.grid, data, "Find & Replace",
                                   wx.FR_REPLACEDIALOG)
        dlg.data = data  # save a reference to data
        dlg.Show(True)

    def _wxflag2flag(self, wxflag):
        """Converts wxPython integer flag to pyspread flag list"""

        wx_flags = {
            0: ["UP", ],
            1: ["DOWN"],
            2: ["UP", "WHOLE_WORD"],
            3: ["DOWN", "WHOLE_WORD"],
            4: ["UP", "MATCH_CASE"],
            5: ["DOWN", "MATCH_CASE"],
            6: ["UP", "WHOLE_WORD", "MATCH_CASE"],
            7: ["DOWN", "WHOLE_WORD", "MATCH_CASE"],
        }

        return wx_flags[wxflag]

    def OnReplaceFind(self, event):
        """Called when a find operation is started from F&R dialog"""

        event.text = event.GetFindString()
        event.flags = self._wxflag2flag(event.GetFlags())

        self.OnFind(event)

    def OnReplace(self, event):
        """Called when a replace operation is started, returns find position"""

        find_string = event.GetFindString()
        flags = self._wxflag2flag(event.GetFlags())
        replace_string = event.GetReplaceString()

        gridpos = list(self.grid.actions.cursor)

        findpos = self.grid.actions.find(gridpos, find_string, flags,
                                         search_result=False)

        if findpos is None:
            statustext = _(u"'{find_string}' not found.")
            statustext = statustext.format(find_string=find_string)

        else:
            self.grid.actions.replace(findpos, find_string, replace_string)
            self.grid.actions.cursor = findpos

            # Update statusbar
            statustext = _(u"Replaced '{find_string}' in cell {key} with "
                           u"{replace_string}.")
            statustext = statustext.format(find_string=find_string,
                                           key=findpos,
                                           replace_string=replace_string)

        post_command_event(self.grid.main_window, self.grid.StatusBarMsg,
                           text=statustext)

        event.Skip()

    def OnReplaceAll(self, event):
        """Called when a replace all operation is started"""

        find_string = event.GetFindString()
        flags = self._wxflag2flag(event.GetFlags())
        replace_string = event.GetReplaceString()

        findpositions = self.grid.actions.find_all(find_string, flags)

        self.grid.actions.replace_all(findpositions, find_string,
                                      replace_string)

        event.Skip()

    def OnCloseFindReplace(self, event):
        """Called when the find&replace dialog is closed"""

        event.GetDialog().Destroy()

        event.Skip()

    # Grid change events

    def _get_no_rowscols(self, bbox):
        """Returns tuple of number of rows and cols from bbox"""

        if bbox is None:
            return 1, 1
        else:
            (bb_top, bb_left), (bb_bottom, bb_right) = bbox
            if bb_top is None:
                bb_top = 0
            if bb_left is None:
                bb_left = 0
            if bb_bottom is None:
                bb_bottom = self.grid.code_array.shape[0] - 1
            if bb_right is None:
                bb_right = self.grid.code_array.shape[1] - 1

            return bb_bottom - bb_top + 1, bb_right - bb_left + 1

    def OnInsertRows(self, event):
        """Insert the maximum of 1 and the number of selected rows"""

        bbox = self.grid.selection.get_bbox()

        if bbox is None or bbox[1][0] is None:
            # Insert rows at cursor
            ins_point = self.grid.actions.cursor[0] - 1
            no_rows = 1
        else:
            # Insert at lower edge of bounding box
            ins_point = bbox[0][0] - 1
            no_rows = self._get_no_rowscols(bbox)[0]

        self.grid.actions.insert_rows(ins_point, no_rows)

        self.grid.GetTable().ResetView()

        # Update the default sized cell sizes
        self.grid.actions.zoom()

        event.Skip()

    def OnInsertCols(self, event):
        """Inserts the maximum of 1 and the number of selected columns"""

        bbox = self.grid.selection.get_bbox()

        if bbox is None or bbox[1][1] is None:
            # Insert rows at cursor
            ins_point = self.grid.actions.cursor[1] - 1
            no_cols = 1
        else:
            # Insert at right edge of bounding box
            ins_point = bbox[0][1] - 1
            no_cols = self._get_no_rowscols(bbox)[1]

        self.grid.actions.insert_cols(ins_point, no_cols)

        self.grid.GetTable().ResetView()

        # Update the default sized cell sizes
        self.grid.actions.zoom()

        event.Skip()

    def OnInsertTabs(self, event):
        """Insert one table into grid"""

        self.grid.actions.insert_tabs(self.grid.current_table - 1, 1)
        self.grid.GetTable().ResetView()
        self.grid.actions.zoom()

        event.Skip()

    def OnDeleteRows(self, event):
        """Deletes rows from all tables of the grid"""

        bbox = self.grid.selection.get_bbox()

        if bbox is None or bbox[1][0] is None:
            # Insert rows at cursor
            del_point = self.grid.actions.cursor[0]
            no_rows = 1
        else:
            # Insert at lower edge of bounding box
            del_point = bbox[0][0]
            no_rows = self._get_no_rowscols(bbox)[0]

        self.grid.actions.delete_rows(del_point, no_rows)

        self.grid.GetTable().ResetView()

        # Update the default sized cell sizes
        self.grid.actions.zoom()

        event.Skip()

    def OnDeleteCols(self, event):
        """Deletes columns from all tables of the grid"""

        bbox = self.grid.selection.get_bbox()

        if bbox is None or bbox[1][1] is None:
            # Insert rows at cursor
            del_point = self.grid.actions.cursor[1]
            no_cols = 1
        else:
            # Insert at right edge of bounding box
            del_point = bbox[0][1]
            no_cols = self._get_no_rowscols(bbox)[1]

        self.grid.actions.delete_cols(del_point, no_cols)

        self.grid.GetTable().ResetView()

        # Update the default sized cell sizes
        self.grid.actions.zoom()

        event.Skip()

    def OnDeleteTabs(self, event):
        """Deletes tables"""

        self.grid.actions.delete_tabs(self.grid.current_table, 1)
        self.grid.GetTable().ResetView()
        self.grid.actions.zoom()

        event.Skip()

    def OnResizeGridDialog(self, event):
        """Resizes current grid by appending/deleting rows, cols and tables"""

        # Get grid dimensions

        new_shape = self.interfaces.get_dimensions_from_user(no_dim=3)

        if new_shape is None:
            return

        self.grid.actions.change_grid_shape(new_shape)

        self.grid.GetTable().ResetView()

        statustext = _("Grid dimensions changed to {shape}.")
        statustext = statustext.format(shape=new_shape)
        post_command_event(self.grid.main_window, self.grid.StatusBarMsg,
                           text=statustext)

        event.Skip()

    def OnQuote(self, event):
        """Quotes selection or if none the current cell"""

        grid = self.grid
        grid.DisableCellEditControl()

        # Is a selection present?
        if self.grid.IsSelection():
            # Enclose all selected cells
            self.grid.actions.quote_selection()

            # Update grid
            self.grid.ForceRefresh()

        else:
            row = self.grid.GetGridCursorRow()
            col = self.grid.GetGridCursorCol()
            key = row, col, grid.current_table

            self.grid.actions.quote_code(key)

            grid.MoveCursorDown(False)

    # Grid attribute events

    def OnRowSize(self, event):
        """Row size event handler"""

        row = event.GetRowOrCol()
        tab = self.grid.current_table
        rowsize = self.grid.GetRowSize(row) / self.grid.grid_renderer.zoom

        # Detect for resizing group of rows
        rows = self.grid.GetSelectedRows()
        if len(rows) == 0:
            rows = [row, ]

        # Detect for selection of rows spanning all columns
        selection = self.grid.selection
        num_cols = self.grid.code_array.shape[1]-1
        for box in zip(selection.block_tl, selection.block_br):
            leftmost_col = box[0][1]
            rightmost_col = box[1][1]
            if leftmost_col == 0 and rightmost_col == num_cols:
                rows += range(box[0][0], box[1][0]+1)

        for row in rows:
            self.grid.code_array.set_row_height(row, tab, rowsize,
                                                mark_unredo=False)
            self.grid.SetRowSize(row, rowsize)
        self.grid.code_array.unredo.mark()

        event.Skip()
        self.grid.Refresh()

    def OnColSize(self, event):
        """Column size event handler"""

        col = event.GetRowOrCol()
        tab = self.grid.current_table
        colsize = self.grid.GetColSize(col) / self.grid.grid_renderer.zoom

        # Detect for resizing group of cols
        cols = self.grid.GetSelectedCols()
        if len(cols) == 0:
            cols = [col, ]

        # Detect for selection of rows spanning all columns
        selection = self.grid.selection
        num_rows = self.grid.code_array.shape[0]-1
        for box in zip(selection.block_tl, selection.block_br):
            top_row = box[0][0]
            bottom_row = box[1][0]
            if top_row == 0 and bottom_row == num_rows:
                cols += range(box[0][1], box[1][1]+1)

        for col in cols:
            self.grid.code_array.set_col_width(col, tab, colsize,
                                               mark_unredo=False)
            self.grid.SetColSize(col, colsize)
        self.grid.code_array.unredo.mark()

        event.Skip()
        self.grid.Refresh()

    def OnSortAscending(self, event):
        """Sort ascending event handler"""

        try:
            self.grid.actions.sort_ascending(self.grid.actions.cursor)
            statustext = _(u"Sorting complete.")

        except Exception, err:
            statustext = _(u"Sorting failed: {}").format(err)

        post_command_event(self.grid.main_window, self.grid.StatusBarMsg,
                           text=statustext)

    def OnSortDescending(self, event):
        """Sort descending event handler"""

        try:
            self.grid.actions.sort_descending(self.grid.actions.cursor)
            statustext = _(u"Sorting complete.")

        except Exception, err:
            statustext = _(u"Sorting failed: {}").format(err)

        post_command_event(self.grid.main_window, self.grid.StatusBarMsg,
                           text=statustext)

    # Undo and redo events

    def OnUndo(self, event):
        """Calls the grid undo method"""

        self.grid.actions.undo()
        self.grid.GetTable().ResetView()
        self.grid.Refresh()
        # Reset row heights and column widths by zooming
        self.grid.actions.zoom()
        # Update toolbars
        self.grid.update_entry_line()
        self.grid.update_attribute_toolbar()

    def OnRedo(self, event):
        """Calls the grid redo method"""

        self.grid.actions.redo()
        self.grid.GetTable().ResetView()
        self.grid.Refresh()
        # Reset row heights and column widths by zooming
        self.grid.actions.zoom()
        # Update toolbars
        self.grid.update_entry_line()
        self.grid.update_attribute_toolbar()

# End of class GridEventHandlers

########NEW FILE########
__FILENAME__ = _grid_cell_editor
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Jason Sexauer, Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
_grid_cell_editor.py
=====

Provides
--------
 1. GridCellEditor -- Editor displayed when user dobule clicks to edit
    a cell in the grid
"""

import wx
import string

from _events import post_command_event
from src.gui._widgets import GridEventMixin


class GridCellEditor(wx.grid.PyGridCellEditor, GridEventMixin):
    """In grid cell editor for entering code
    Refer to :
    https://github.com/wxWidgets/wxPython/blob/master/demo/GridCustEditor.py
    """
    def __init__(self, main_window):

        self.main_window = main_window
        wx.grid.PyGridCellEditor.__init__(self)

    def Create(self, parent, id, evtHandler):
        """
        Called to create the control, which must derive from wx.Control.
        *Must Override*
        """
        self._tc = wx.TextCtrl(parent, id, "")

        # Disable if cell is clocked, enable if cell is not locked
        grid = self.main_window.grid
        key = grid.actions.cursor
        locked = grid.code_array.cell_attributes[key]["locked"]
        self._tc.Enable(not locked)
        self._tc.Show(not locked)

        self._tc.SetInsertionPoint(0)
        self.SetControl(self._tc)

        if evtHandler:
            self._tc.PushEventHandler(evtHandler)

    def SetSize(self, rect):
        """
        Called to position/size the edit control within the cell rectangle.
        If you don't fill the cell (the rect) then be sure to override
        PaintBackground and do something meaningful there.
        """
        self._tc.SetDimensions(rect.x, rect.y, rect.width+2, rect.height+2,
                               wx.SIZE_ALLOW_MINUS_ONE)
        self._tc.Layout()

    def Show(self, show, attr):
        """
        Show or hide the edit control.  You can use the attr (if not None)
        to set colours or fonts for the control.
        """
        super(GridCellEditor, self).Show(show, attr)

    def PaintBackground(self, rect, attr):
        """
        Draws the part of the cell not occupied by the edit control.  The
        base  class version just fills it with background colour from the
        attribute.  In this class the edit control fills the whole cell so
        don't do anything at all in order to reduce flicker.
        """

    def BeginEdit(self, row, col, grid):
        """
        Fetch the value from the table and prepare the edit control
        to begin editing.  Set the focus to the edit control.
        *Must Override*
        """

        # Disable if cell is clocked, enable if cell is not locked
        grid = self.main_window.grid
        key = grid.actions.cursor
        locked = grid.code_array.cell_attributes[key]["locked"]
        self._tc.Enable(not locked)
        self._tc.Show(not locked)

        # Mirror our changes onto the main_window's code bar
        self._tc.Bind(wx.EVT_CHAR, self.OnChar)

        # Save cell and grid info
        self._row = row
        self._col = [col, ]  # List of columns we are occupying
        self._grid = grid

        self.startValue = grid.GetTable().GetValue(row, col)
        # Set up the textcontrol to look like this cell (TODO: Does not work)
        self._tc.SetValue(str(self.startValue))  # was self.startValue
        self._tc.SetFont(grid.GetCellFont(row, col))
        self._tc.SetBackgroundColour(grid.GetCellBackgroundColour(row, col))
        self._update_control_length()

        self._tc.SetInsertionPointEnd()
        self._tc.SetFocus()

        # For this example, select the text
        self._tc.SetSelection(0, self._tc.GetLastPosition())

    def EndEdit(self, row, col, grid, oldVal=None):
        """
        End editing the cell.  This function must check if the current
        value of the editing control is valid and different from the
        original value (available as oldval in its string form.)  If
        it has not changed then simply return None, otherwise return
        the value in its string form.
        *Must Override*
        """
        # Mirror our changes onto the main_window's code bar
        self._tc.Unbind(wx.EVT_KEY_UP)

        oldVal = self.startValue
        val = self._tc.GetValue()
        self.ApplyEdit(row, col, grid)

        del self._col
        del self._row
        del self._grid

    def ApplyEdit(self, row, col, grid):
        """
        This function should save the value of the control into the
        grid or grid table. It is called only after EndEdit() returns
        a non-None value.
        *Must Override*
        """
        val = self._tc.GetValue()
        grid.GetTable().SetValue(row, col, val)  # update the table

        self.startValue = ''
        self._tc.SetValue('')

    def Reset(self):
        """
        Reset the value in the control back to its starting value.
        *Must Override*
        """

        try:
            self._tc.SetValue(self.startValue)
        except TypeError:
            # Start value was None
            pass
        self._tc.SetInsertionPointEnd()
        # Update the Entry Line
        post_command_event(self.main_window, self.TableChangedMsg,
                           updated_cell=self.startValue)

    def IsAcceptedKey(self, evt):
        """
        Return True to allow the given key to start editing: the base class
        version only checks that the event has no modifiers.  F2 is special
        and will always start the editor.
        """

        ## We can ask the base class to do it
        #return super(MyCellEditor, self).IsAcceptedKey(evt)

        # or do it ourselves
        return (not (evt.ControlDown() or evt.AltDown()) and
                evt.GetKeyCode() != wx.WXK_SHIFT)

    def StartingKey(self, evt):
        """
        If the editor is enabled by pressing keys on the grid, this will be
        called to let the editor do something about that first key if desired.
        """
        key = evt.GetKeyCode()
        ch = None
        if key in [
                wx.WXK_NUMPAD0, wx.WXK_NUMPAD1, wx.WXK_NUMPAD2, wx.WXK_NUMPAD3,
                wx.WXK_NUMPAD4, wx.WXK_NUMPAD5, wx.WXK_NUMPAD6, wx.WXK_NUMPAD7,
                wx.WXK_NUMPAD8, wx.WXK_NUMPAD9]:

            ch = ch = chr(ord('0') + key - wx.WXK_NUMPAD0)

        elif key < 256 and key >= 0 and chr(key) in string.printable:
            ch = chr(key)

        if ch is not None and self._tc.IsEnabled():
            # For this example, replace the text.  Normally we would append it.
            #self._tc.AppendText(ch)
            self._tc.SetValue(ch)
            self._tc.SetInsertionPointEnd()
        else:
            evt.Skip()

    def StartingClick(self):
        """
        If the editor is enabled by clicking on the cell, this method will be
        called to allow the editor to simulate the click on the control if
        needed.
        """

    def Destroy(self):
        """final cleanup"""
        super(GridCellEditor, self).Destroy()

    def Clone(self):
        """
        Create a new object which is the copy of this one
        *Must Override*
        """
        return GridCellEditor()

    def OnChar(self, event):
        self._update_control_length()
        val = self._tc.GetValue()
        post_command_event(self.main_window, self.TableChangedMsg,
                           updated_cell=val)
        event.Skip()

    def _update_control_length(self):
        val = self._tc.GetValue()
        extent = self._tc.GetTextExtent(val)[0] + 15  # Small margin
        width, height = self._tc.GetSizeTuple()
        new_width = None
        while width < extent:
            # We need to reszie into the next cell's column
            next_col = self._col[-1] + 1
            new_width = width + self._grid.GetColSize(next_col)
            self._col.append(next_col)
            width = new_width
        if new_width:
            pos = self._tc.GetPosition()
            self.SetSize(wx.Rect(pos[0],pos[1],new_width-2, height-2))

########NEW FILE########
__FILENAME__ = _grid_renderer
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
_grid_renderer
==============

Provides
--------

1) GridRenderer: Draws the grid
2) Background: Background drawing

"""

from math import pi, sin, cos
import types

import wx.grid

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot

from src.lib.charts import fig2bmp
import src.lib.i18n as i18n
from src.lib import xrect
from src.lib.parsers import get_pen_from_data, get_font_from_data
from src.config import config
from src.sysvars import get_color

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


class GridRenderer(wx.grid.PyGridCellRenderer):
    """This renderer draws borders and text at specified font, size, color"""

    def __init__(self, data_array):

        wx.grid.PyGridCellRenderer.__init__(self)

        self.data_array = data_array

        # Background key is (width, height, bgbrush,
        # borderwidth_bottom, borderwidth_right,
        # bordercolor_bottom, bordercolor_right)
        self.backgrounds = {}

        # Fontcache speeds up font retrieval
        self.font_cache = {}

        # Bitmap cache speeds up bitmap scaling
        self.bmp_cache = {}

        # Zoom of grid
        self.zoom = 1.0

        # Old cursor position
        self.old_cursor_row_col = 0, 0

    def get_zoomed_size(self, size):
        """Returns zoomed size as Integer

        Parameters
        ----------

        font_size: Integer
        \tOriginal font size

        """

        return max(1.0, round(size * self.zoom))

    def get_textbox_edges(self, text_pos, text_extent):
        """Returns upper left, lower left, lower right, upper right of text"""

        string_x, string_y, angle = text_pos

        pt_ul = string_x, string_y
        pt_ll = string_x, string_y + text_extent[1]
        pt_lr = string_x + text_extent[0], string_y + text_extent[1]
        pt_ur = string_x + text_extent[0], string_y

        if not -0.0001 < angle < 0.0001:
            rot_angle = angle / 180.0 * pi

            def rotation(x, y, angle, base_x=0.0, base_y=0.0):
                x -= base_x
                y -= base_y

                __x = cos(rot_angle) * x + sin(rot_angle) * y
                __y = -sin(rot_angle) * x + cos(rot_angle) * y

                __x += base_x
                __y += base_y

                return __x, __y

            pt_ul = rotation(pt_ul[0], pt_ul[1], rot_angle,
                             base_x=string_x, base_y=string_y)
            pt_ll = rotation(pt_ll[0], pt_ll[1], rot_angle,
                             base_x=string_x, base_y=string_y)
            pt_ur = rotation(pt_ur[0], pt_ur[1], rot_angle,
                             base_x=string_x, base_y=string_y)
            pt_lr = rotation(pt_lr[0], pt_lr[1], rot_angle,
                             base_x=string_x, base_y=string_y)

        return pt_ul, pt_ll, pt_lr, pt_ur

    def get_text_rotorect(self, text_pos, text_extent):
        """Returns a RotoRect for given cell text"""

        pt_ll = self.get_textbox_edges(text_pos, text_extent)[1]

        rr_x, rr_y = pt_ll
        text_ext_x, text_ext_y = text_extent

        angle = float(text_pos[2])

        return xrect.RotoRect(rr_x, rr_y, text_ext_x, text_ext_y, angle)

    def draw_textbox(self, dc, text_pos, text_extent):

        pt_ul, pt_ll, pt_lr, pt_ur = self.get_textbox_edges(text_pos,
                                                            text_extent)

        dc.DrawLine(pt_ul[0], pt_ul[1], pt_ll[0], pt_ll[1])
        dc.DrawLine(pt_ll[0], pt_ll[1], pt_lr[0], pt_lr[1])
        dc.DrawLine(pt_lr[0], pt_lr[1], pt_ur[0], pt_ur[1])
        dc.DrawLine(pt_ur[0], pt_ur[1], pt_ul[0], pt_ul[1])

    def draw_text_label(self, dc, res, rect, grid, key):
        """Draws text label of cell

        Text is truncated at config["max_result_length"]

        """

        result_length = config["max_result_length"]

        try:
            res_text = unicode(res)[:result_length]

        except UnicodeDecodeError:
            res_text = unicode(res, encoding="utf-8")[:result_length]

        if not res_text:
            return

        row, col, tab = key

        cell_attributes = self.data_array.cell_attributes[key]

        # Text font attributes
        textfont = cell_attributes["textfont"]
        pointsize = cell_attributes["pointsize"]
        fontweight = cell_attributes["fontweight"]
        fontstyle = cell_attributes["fontstyle"]
        underline = cell_attributes["underline"]

        strikethrough = cell_attributes["strikethrough"]

        # Text placement attributes
        vertical_align = cell_attributes["vertical_align"]
        justification = cell_attributes["justification"]
        angle = cell_attributes["angle"]

        # Text color attributes

        textcolor = wx.Colour()
        textcolor.SetRGB(cell_attributes["textcolor"])

        # Get font from font attribute strings

        font = self.get_font(textfont, pointsize, fontweight, fontstyle,
                             underline)
        dc.SetFont(font)

        text_x, text_y = self.get_text_position(dc, rect, res_text, angle,
                                                vertical_align, justification)

        #__rect = xrect.Rect(rect.x, rect.y, rect.width, rect.height)

        text_extent = dc.GetTextExtent(res_text)

        dc.SetBackgroundMode(wx.TRANSPARENT)
        dc.SetTextForeground(textcolor)

        # If cell rect stays inside cell, we simply draw

        text_pos = text_x, text_y, angle

        dc.SetClippingRect(rect)
        dc.DrawRotatedText(res_text, *text_pos)
        text_extent = dc.GetTextExtent(res_text)
        if strikethrough:
            self._draw_strikethrough_line(grid, dc, rect, text_x,
                                          text_y, angle, text_extent)
        dc.DestroyClippingRegion()

    def _draw_strikethrough_line(self, grid, dc, rect,
                                 string_x, string_y, angle, text_extent):
        """Draws a strikethrough line"""

        strikethroughwidth = self.get_zoomed_size(1.5)
        dc.SetPen(wx.Pen(wx.BLACK, strikethroughwidth, wx.SOLID))

        x1 = string_x
        y1 = string_y + text_extent[1] / 2
        x2 = string_x + text_extent[0]
        y2 = string_y + text_extent[1] / 2

        if not -0.0001 < angle < 0.0001:

            rot_angle = angle / 180.0 * pi

            def rotation(x, y, angle, base_x=0.0, base_y=0.0):
                x -= base_x
                y -= base_y

                __x = cos(rot_angle) * x + sin(rot_angle) * y
                __y = -sin(rot_angle) * x + cos(rot_angle) * y

                __x += base_x
                __y += base_y

                return __x, __y

            x1, y1 = rotation(x1, y1, rot_angle,
                              base_x=string_x, base_y=string_y)
            x2, y2 = rotation(x2, y2, rot_angle,
                              base_x=string_x, base_y=string_y)

        dc.DrawLine(x1, y1, x2, y2)

    def get_font(self, textfont, pointsize, fontweight, fontstyle, underline):
        """Returns font for given attribute strings

        Parameters
        ----------

        textfont: String
        \tString that describes the type of font
        pointsize: Integer
        \tFont size in points
        fontweight: Integer in (wx.NORMAL, wx.BOLD)
        \tFontsize integer
        fontstyle: Integer in (wx.NORMAL, wx.ITALICS)
        \tString that describes the font style
        underlined: Bool
        \tFont is underlined if True

        """

        fontsize = self.get_zoomed_size(pointsize)

        font_key = textfont, fontsize, fontweight, fontstyle, underline
        if font_key in self.font_cache:
            return self.font_cache[font_key]

        # Get a real font from textfont string

        font = get_font_from_data(textfont)
        font.SetPointSize(fontsize)
        font.SetWeight(fontweight)
        font.SetStyle(fontstyle)
        font.SetUnderlined(underline)
        font.SetFaceName(textfont)  # Windows hack

        self.font_cache[font_key] = font

        return font

    def get_text_position(self, dc, rect, res_text, angle,
                          vertical_align, justification):
        """Returns text x, y position in cell"""

        text_extent = dc.GetTextExtent(res_text)

        # Vertical alignment

        if vertical_align == "middle":
            string_y = rect.y + rect.height / 2 - text_extent[1] / 2 + 1

        elif vertical_align == "bottom":
            string_y = rect.y + rect.height - text_extent[1]

        elif vertical_align == "top":
            string_y = rect.y + 2

        else:
            msg = _("Vertical alignment {align} not in (top, middle, bottom)")
            msg = msg.format(align=vertical_align)
            raise ValueError(msg)

        # Justification

        if justification == "left":
            string_x = rect.x + 2

        elif justification == "center":
            # First calculate x value for unrotated text
            string_x = rect.x + rect.width / 2 - 1

            # Now map onto rotated xy position
            rot_angle = angle / 180.0 * pi
            string_x = string_x - text_extent[0] / 2 * cos(rot_angle)
            string_y = string_y + text_extent[0] / 2 * sin(rot_angle)

        elif justification == "right":
            # First calculate x value for unrotated text
            string_x = rect.x + rect.width - 2

            # Now map onto rotated xy position
            rot_angle = angle / 180.0 * pi
            string_x = string_x - text_extent[0] * cos(rot_angle)
            string_y = string_y + text_extent[0] * sin(rot_angle)
        else:
            msg = _("Cell justification {just} not in (left, center, right)")
            msg = msg.format(just=justification)
            raise ValueError(msg)

        return string_x, string_y

    def _draw_cursor(self, dc, grid, row, col,
                     pen=wx.BLACK_PEN, brush=wx.BLACK_BRUSH):
        """Draws cursor as Rectangle in lower right corner"""

        key = row, col, grid.current_table
        rect = grid.CellToRect(row, col)
        rect = self.get_merged_rect(grid, key, rect)

        # Check if cell is invisible
        if rect is None:
            return

        size = self.get_zoomed_size(1.0)

        caret_length = int(min([rect.width, rect.height]) / 5.0)

        pen.SetWidth(size)

        # Inner right and lower borders
        border_left = rect.x
        border_right = rect.x + rect.width - size - 1
        border_upper = rect.y
        border_lower = rect.y + rect.height - size - 1

        points_lr = [
            (border_right, border_lower - caret_length),
            (border_right, border_lower),
            (border_right - caret_length, border_lower),
            (border_right, border_lower),
        ]

        points_ur = [
            (border_right, border_upper + caret_length),
            (border_right, border_upper),
            (border_right - caret_length, border_upper),
            (border_right, border_upper),
        ]

        points_ul = [
            (border_left, border_upper + caret_length),
            (border_left, border_upper),
            (border_left + caret_length, border_upper),
            (border_left, border_upper),
        ]

        points_ll = [
            (border_left, border_lower - caret_length),
            (border_left, border_lower),
            (border_left + caret_length, border_lower),
            (border_left, border_lower),
        ]

        point_list = [points_lr, points_ur, points_ul, points_ll]

        dc.DrawPolygonList(point_list, pens=pen, brushes=brush)

        self.old_cursor_row_col = row, col

    def update_cursor(self, dc, grid, row, col):
        """Whites out the old cursor and draws the new one"""

        old_row, old_col = self.old_cursor_row_col

        self._draw_cursor(dc, grid, old_row, old_col,
                          pen=wx.WHITE_PEN, brush=wx.WHITE_BRUSH)
        self._draw_cursor(dc, grid, row, col)

    def get_merging_cell(self, grid, key):
        """Returns row, col, tab of merging cell if the cell key is merged"""

        return grid.code_array.cell_attributes.get_merging_cell(key)

    def get_merged_rect(self, grid, key, rect):
        """Returns cell rect for normal or merged cells and None for merged"""

        row, col, tab = key

        # Check if cell is merged:
        cell_attributes = grid.code_array.cell_attributes
        merge_area = cell_attributes[row, col, tab]["merge_area"]

        if merge_area is None:
            return rect

        else:
            # We have a merged cell
            top, left, bottom, right = merge_area

            # Are we drawing the top left cell?
            if top == row and left == col:
                # Set rect to merge area
                ul_rect = grid.CellToRect(row, col)
                br_rect = grid.CellToRect(bottom, right)

                width = br_rect.x - ul_rect.x + br_rect.width
                height = br_rect.y - ul_rect.y + br_rect.height

                rect = wx.Rect(ul_rect.x, ul_rect.y, width, height)

                return rect

    def draw_bitmap(self, dc, bmp, rect, grid, key, scale=True):
        """Draws wx.Bitmap bmp on cell

        The bitmap is scaled to match the cell rect

        """

        def scale(img, width, height):
            """Returns a scaled version of the bitmap bmp"""

            img = img.Scale(width, height, quality=wx.IMAGE_QUALITY_HIGH)
            return wx.BitmapFromImage(img)


        if scale:
            img = bmp.ConvertToImage()
            bmp_key = img, rect.width, rect.height

            if bmp_key in self.bmp_cache:
                return self.bmp_cache[bmp_key]

            bmp = scale(*bmp_key)
            self.bmp_cache[bmp_key] = bmp

        dc.DrawBitmap(bmp, rect.x, rect.y)

    def draw_matplotlib_figure(self, dc, figure, rect, grid, key):
        """Draws a matplotlib.pyplot.Figure on cell

        The figure is converted into a wx.Bitmap,
        which is then drawn by draw_bitmap.

        """

        crop_rect = wx.Rect(rect.x, rect.y, rect.width - 1, rect.height - 1)

        width, height = crop_rect.width, crop_rect.height
        dpi = float(wx.ScreenDC().GetPPI()[0])

        bmp = fig2bmp(figure, width, height, dpi, self.zoom)

        self.draw_bitmap(dc, bmp, crop_rect, grid, key, scale=False)

    def Draw(self, grid, attr, dc, rect, row, col, isSelected, printing=False):
        """Draws the cell border and content"""

        key = row, col, grid.current_table

        rect = self.get_merged_rect(grid, key, rect)
        if rect is None:
            # Merged cell
            if grid.is_merged_cell_drawn(key):
                row, col, __ = key = self.get_merging_cell(grid, key)
                rect = grid.CellToRect(row, col)
                rect = self.get_merged_rect(grid, key, rect)
            else:
                return

        lower_right_rect_extents = self.get_lower_right_rect_extents(key, rect)


        if isSelected:
            grid.selection_present = True

            bg = Background(grid, rect, lower_right_rect_extents,
                            self.data_array, row, col, grid.current_table,
                            isSelected)
        else:
            width, height = rect.width, rect.height

            bg_components = ["bgcolor",
                             "borderwidth_bottom", "borderwidth_right",
                             "bordercolor_bottom", "bordercolor_right"]
            if grid._view_frozen:
                bg_components += ['frozen']

            bg_components += [lower_right_rect_extents]

            bg_key = tuple([width, height] +
                           [self.data_array.cell_attributes[key][bgc]
                               for bgc in bg_components[:-1]] + \
                           [bg_components[-1]])

            try:
                bg = self.backgrounds[bg_key]

            except KeyError:
                if len(self.backgrounds) > 10000:
                    # self.backgrounds may grow quickly

                    self.backgrounds = {}

                bg = self.backgrounds[bg_key] = \
                    Background(grid, rect, lower_right_rect_extents,
                               self.data_array, *key)

        dc.Blit(rect.x, rect.y, rect.width, rect.height,
                bg.dc, 0, 0, wx.COPY)

        # Check if the dc is drawn manually be a return func
        try:
            res = self.data_array[row, col, grid.current_table]

        except IndexError:
            return

        if isinstance(res, types.FunctionType):
            # Add func_dict attribute
            # so that we are sure that it uses a dc
            try:
                res(grid, attr, dc, rect)
            except TypeError:
                pass

        elif isinstance(res, wx._gdi.Bitmap):
            # A bitmap is returned --> Draw it!
            self.draw_bitmap(dc, res, rect, grid, key)

        elif isinstance(res, matplotlib.pyplot.Figure):
            # A matplotlib figure is returned --> Draw it!
            self.draw_matplotlib_figure(dc, res, rect, grid, key)

        elif res is not None:
            self.draw_text_label(dc, res, rect, grid, key)

        if grid.actions.cursor[:2] == (row, col):
            self.update_cursor(dc, grid, row, col)

    def get_lower_right_rect_extents(self, key, rect):
        """Returns lower right rect x,y,w,h tuple if rect needed else None"""

        row, col, tab = key
        cell_attributes = self.data_array.cell_attributes
        x, y, w, h = 0, 0, rect.width - 1, rect.height - 1

        # Do we need to draw a lower right rectangle?
        bottom_key = row + 1, col, tab
        right_key = row, col + 1, tab


        right_width = cell_attributes[key]["borderwidth_right"]
        bottom_width = cell_attributes[key]["borderwidth_bottom"]

        bottom_width_right = cell_attributes[right_key]["borderwidth_bottom"]
        right_width_bottom = cell_attributes[bottom_key]["borderwidth_right"]

        if bottom_width < bottom_width_right and \
           right_width < right_width_bottom:
            return (x + w - right_width_bottom,
                    y + h - bottom_width_right,
                    right_width_bottom, bottom_width_right)

# end of class TextRenderer


class Background(object):
    """Memory DC with background content for given cell"""

    def __init__(self, grid, rect, lower_right_rect_extents, data_array,
                 row, col, tab, selection=False):
        self.grid = grid
        self.data_array = data_array

        self.key = row, col, tab

        self.dc = wx.MemoryDC()
        self.rect = rect
        self.bmp = wx.EmptyBitmap(rect.width, rect.height)

        self.lower_right_rect_extents = lower_right_rect_extents

        self.selection = selection

        self.dc.SelectObject(self.bmp)
        self.dc.SetBackgroundMode(wx.TRANSPARENT)

        self.dc.SetDeviceOrigin(0, 0)

        self.draw()

    def draw(self):
        """Does the actual background drawing"""

        self.draw_background(self.dc)
        self.draw_border_lines(self.dc)

    def draw_background(self, dc):
        """Draws the background of the background"""

        attr = self.data_array.cell_attributes[self.key]

        if self.selection:
            color = get_color(config["selection_color"])
        else:
            rgb = attr["bgcolor"]
            color = wx.Colour()
            color.SetRGB(rgb)
        bgbrush = wx.Brush(color, wx.SOLID)
        dc.SetBrush(bgbrush)
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangle(0, 0, self.rect.width, self.rect.height)

        # Draw frozen cell background rect
        if self.grid._view_frozen and attr['frozen']:
            style = wx.FDIAGONAL_HATCH
            freeze_color = get_color(config['freeze_color'])
            freeze_brush = wx.Brush(freeze_color, style)
            dc.SetBrush(freeze_brush)
            dc.DrawRectangle(0, 0, self.rect.width, self.rect.height)

    def draw_border_lines(self, dc):
        """Draws lines"""

        x, y, w, h = 0, 0, self.rect.width - 1, self.rect.height - 1
        row, col, tab = key = self.key

        cell_attributes = self.data_array.cell_attributes

        # Get borderpens and bgbrushes for rects
        # Each cell draws its bottom and its right line only
        bottomline = x, y + h, x + w, y + h
        rightline = x + w, y, x + w, y + h
        lines = [bottomline, rightline]

        # Bottom line pen

        bottom_color = cell_attributes[key]["bordercolor_bottom"]
        bottom_width = cell_attributes[key]["borderwidth_bottom"]
        bottom_pen = get_pen_from_data(
            (bottom_color, bottom_width, int(wx.SOLID)))

        # Right line pen

        right_color = cell_attributes[key]["bordercolor_right"]
        right_width = cell_attributes[key]["borderwidth_right"]
        right_pen = get_pen_from_data(
            (right_color, right_width, int(wx.SOLID)))

        borderpens = [bottom_pen, right_pen]

        # If 0 width then no border is drawn

        if bottom_width == 0:
            borderpens.pop(0)
            lines.pop(0)

        if right_width == 0:
            borderpens.pop(-1)
            lines.pop(-1)

        # Topmost line if in topmost cell

        if row == 0:
            lines.append((x, y, x + w, y))
            topkey = -1, col, tab
            color = cell_attributes[topkey]["bordercolor_bottom"]
            width = cell_attributes[topkey]["borderwidth_bottom"]
            top_pen = get_pen_from_data((color, width, int(wx.SOLID)))
            borderpens.append(top_pen)

        # Leftmost line if in leftmost cell

        if col == 0:
            lines.append((x, y, x, y + h))
            leftkey = row, -1, tab
            color = cell_attributes[leftkey]["bordercolor_bottom"]
            width = cell_attributes[leftkey]["borderwidth_bottom"]
            left_pen = get_pen_from_data((color, width, int(wx.SOLID)))
            borderpens.append(left_pen)

        zoomed_pens = []
        get_zoomed_size = self.grid.grid_renderer.get_zoomed_size

        for pen in borderpens:
            bordercolor = pen.GetColour()
            borderwidth = pen.GetWidth()
            borderstyle = pen.GetStyle()

            zoomed_borderwidth = get_zoomed_size(borderwidth)
            zoomed_pen = wx.Pen(bordercolor, zoomed_borderwidth, borderstyle)
            zoomed_pen.SetJoin(wx.JOIN_MITER)

            zoomed_pens.append(zoomed_pen)

        dc.DrawLineList(lines, zoomed_pens)

        # Draw lower right rectangle if
        # 1) the next cell to the right has a greater bottom width and
        # 2) the next cell to the bottom has a greater right width

        if self.lower_right_rect_extents is not None:
            rx, ry, rw, rh = self.lower_right_rect_extents
            rwz = get_zoomed_size(rw)
            rhz = get_zoomed_size(rh)
            rxz = round(rx + rw - rwz / 2.0)
            ryz = round(ry + rh - rhz / 2.0)
            rect = wx.Rect(rxz, ryz, rwz, rhz)

            # The color of the lower right rectangle is the color of the
            # bottom line of the next cell to the right

            rightkey = row, col + 1, tab
            lr_color = wx.Colour()

            lr_color.SetRGB(cell_attributes[rightkey]["bordercolor_bottom"])

            lr_brush = wx.Brush(lr_color, wx.SOLID)

            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.SetBrush(lr_brush)

            dc.DrawRectangle(*rect)


# end of class Background

########NEW FILE########
__FILENAME__ = _grid_table
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------


"""
_grid_table
===========

Provides
--------

1) GridTable: Handles interaction to data_array

"""

import wx
import wx.grid

from src.config import config


class GridTable(wx.grid.PyGridTableBase):
    """Table base class that handles interaction between Grid and data_array"""

    def __init__(self, grid, data_array):
        self.grid = grid
        self.data_array = data_array

        wx.grid.PyGridTableBase.__init__(self)

        # we need to store the row length and column length to
        # see if the table has changed size
        self._rows = self.GetNumberRows()
        self._cols = self.GetNumberCols()

    def GetNumberRows(self):
        """Return the number of rows in the grid"""

        return self.data_array.shape[0]

    def GetNumberCols(self):
        """Return the number of columns in the grid"""

        return self.data_array.shape[1]

    def GetRowLabelValue(self, row):
        """Returns row number"""

        return str(row)

    def GetColLabelValue(self, col):
        """Returns column number"""

        return str(col)

    def GetSource(self, row, col, table=None):
        """Return the source string of a cell"""

        if table is None:
            table = self.grid.current_table

        value = self.data_array((row, col, table))

        if value is None:
            return u""
        else:
            return value

    def GetValue(self, row, col, table=None):
        """Return the result value of a cell, line split if too much data"""

        if table is None:
            table = self.grid.current_table

        try:
            cell_code = self.data_array((row, col, table))
        except IndexError:
            cell_code = None

        # Put EOLs into result if it is too long
        maxlength = int(config["max_textctrl_length"])

        if cell_code is not None and len(cell_code) > maxlength:
            chunk = 80
            cell_code = "\n".join(cell_code[i:i + chunk]
                                  for i in xrange(0, len(cell_code), chunk))

        return cell_code

    def SetValue(self, row, col, value, refresh=True):
        """Set the value of a cell, merge line breaks"""

        # Join code that has been split because of long line issue
        value = "".join(value.split("\n"))

        key = row, col, self.grid.current_table
        self.grid.actions.set_code(key, value)

    def UpdateValues(self):
        """Update all displayed values"""

        # This sends an event to the grid table
        # to update all of the values

        msg = wx.grid.GridTableMessage(self,
                wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.grid.ProcessTableMessage(msg)

    def ResetView(self):
        """
        (Grid) -> Reset the grid view.   Call this to
        update the grid if rows and columns have been added or deleted

        """

        grid = self.grid

        grid.BeginBatch()

        for current, new, delmsg, addmsg in [
            (self._rows, self.GetNumberRows(),
             wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED,
             wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED),
            (self._cols, self.GetNumberCols(),
             wx.grid.GRIDTABLE_NOTIFY_COLS_DELETED,
             wx.grid.GRIDTABLE_NOTIFY_COLS_APPENDED),
        ]:

            if new < current:
                msg = wx.grid.GridTableMessage(self, delmsg, new,
                                               current - new)
                grid.ProcessTableMessage(msg)
            elif new > current:
                msg = wx.grid.GridTableMessage(self, addmsg, new - current)
                grid.ProcessTableMessage(msg)
                self.UpdateValues()

        grid.EndBatch()

        self._rows = self.GetNumberRows()
        self._cols = self.GetNumberCols()

        # Adjust rows
        row_heights = grid.code_array.row_heights
        for key in row_heights:
            if key[1] == grid.current_table:
                row = key[0]
                if row_heights[key] is None:
                    # Default row size
                    grid.SetRowSize(row, self.grid.GetDefaultRowSize())
                else:
                    grid.SetRowSize(row, row_heights[key])

        # Adjust columns
        col_widths = grid.code_array.col_widths
        for key in col_widths:
            if key[1] == self.grid.current_table:
                col = key[0]
                if col_widths[key] is None:
                    # Default row size
                    grid.SetColSize(col, self.grid.GetDefaultColSize())
                else:
                    grid.SetColSize(col, col_widths[key])

        # update the scrollbars and the displayed part
        # of the grid

        grid.Freeze()
        grid.AdjustScrollbars()
        grid.Refresh()
        grid.Thaw()

# end of class MainGridTable
########NEW FILE########
__FILENAME__ = _gui_interfaces
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
_gui_interfaces
===============

Provides:
---------
  1) GuiInterfaces: Main window interfaces to GUI elements

"""

import csv
from itertools import islice
import os
import sys
import types

import wx
import wx.lib.agw.genericmessagedialog as GMD

import src.lib.i18n as i18n

from _dialogs import MacroDialog, DimensionsEntryDialog, AboutDialog
from _dialogs import CsvImportDialog, CellEntryDialog, CsvExportDialog
from _dialogs import PreferencesDialog, GPGParamsDialog, PasteAsDialog

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


class ModalDialogInterfaceMixin(object):
    """Main window interfaces to modal dialogs"""

    def get_dimensions_from_user(self, no_dim):
        """Queries grid dimensions in a model dialog and returns n-tuple

        Parameters
        ----------
        no_dim: Integer
        \t Number of grid dimensions, currently must be 3

        """

        # Grid dimension dialog

        if no_dim != 3:
            raise NotImplementedError(
                _("Currently, only 3D grids are supported."))

        dim_dialog = DimensionsEntryDialog(self.main_window)

        if dim_dialog.ShowModal() != wx.ID_OK:
            dim_dialog.Destroy()
            return

        dim = tuple(dim_dialog.dimensions)
        dim_dialog.Destroy()

        return dim

    def get_preferences_from_user(self):
        """Launches preferences dialog and returns dict with preferences"""

        dlg = PreferencesDialog(self.main_window)

        change_choice = dlg.ShowModal()

        preferences = {}

        if change_choice == wx.ID_OK:
            for (parameter, _), ctrl in zip(dlg.parameters, dlg.textctrls):
                preferences[parameter] = repr(ctrl.Value)

        dlg.Destroy()

        return preferences

    def get_save_request_from_user(self):
        """Queries user if grid should be saved"""

        msg = _("There are unsaved changes.\nDo you want to save?")

        dlg = GMD.GenericMessageDialog(
            self.main_window, msg,
            _("Unsaved changes"), wx.YES_NO | wx.ICON_QUESTION | wx.CANCEL)

        save_choice = dlg.ShowModal()

        dlg.Destroy()

        if save_choice == wx.ID_YES:
            return True

        elif save_choice == wx.ID_NO:
            return False

    def get_filepath_findex_from_user(self, wildcard, message, style):
        """Opens a file dialog and returns filepath and filterindex

        Parameters
        ----------
        wildcard: String
        \tWildcard string for file dialog
        message: String
        \tMessage in the file dialog
        style: Integer
        \tDialog style, e. g. wx.OPEN | wx.CHANGE_DIR

        """

        dlg = wx.FileDialog(self.main_window, wildcard=wildcard,
                            message=message, style=style)

        filepath = None
        filter_index = None

        if dlg.ShowModal() == wx.ID_OK:
            filepath = dlg.GetPath()
            filter_index = dlg.GetFilterIndex()

        return filepath, filter_index

    def display_warning(self, message, short_message,
                        style=wx.OK | wx.ICON_WARNING):
        """Displays a warning message"""

        dlg = GMD.GenericMessageDialog(self.main_window, message,
                                       short_message, style)
        dlg.ShowModal()
        dlg.Destroy()

    def get_warning_choice(self, message, short_message,
                           style=wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING):
        """Launches proceeding dialog and returns True if ok to proceed"""

        dlg = GMD.GenericMessageDialog(self.main_window, message,
                                       short_message, style)

        choice = dlg.ShowModal()

        dlg.Destroy()

        return choice == wx.ID_YES

    def get_print_setup(self, print_data):
        """Opens print setup dialog and returns print_data"""

        psd = wx.PageSetupDialogData(print_data)
        ##psd.EnablePrinter(False)
        psd.CalculatePaperSizeFromId()
        dlg = wx.PageSetupDialog(self.main_window, psd)
        dlg.ShowModal()

        # this makes a copy of the wx.PrintData instead of just saving
        # a reference to the one inside the PrintDialogData that will
        # be destroyed when the dialog is destroyed
        new_print_data = wx.PrintData(dlg.GetPageSetupData().GetPrintData())

        dlg.Destroy()

        return new_print_data

    def get_csv_import_info(self, path):
        """Launches the csv dialog and returns csv_info

        csv_info is a tuple of dialect, has_header, digest_types

        Parameters
        ----------

        path: String
        \tFile path of csv file

        """

        csvfilename = os.path.split(path)[1]

        try:
            filterdlg = CsvImportDialog(self.main_window, csvfilepath=path)

        except csv.Error, err:
            # Display modal warning dialog

            msg = _("'{filepath}' does not seem to be a valid CSV file.\n \n"
                    "Opening it yielded the error:\n{error}")
            msg = msg.format(filepath=csvfilename, error=err)
            short_msg = _('Error reading CSV file')

            self.display_warning(msg, short_msg)

            return

        if filterdlg.ShowModal() == wx.ID_OK:
            dialect, has_header = filterdlg.csvwidgets.get_dialect()
            digest_types = filterdlg.grid.dtypes
            encoding = filterdlg.csvwidgets.encoding

        else:
            filterdlg.Destroy()

            return

        filterdlg.Destroy()

        return dialect, has_header, digest_types, encoding

    def get_csv_export_info(self, preview_data):
        """Shows csv export preview dialog and returns csv_info

        csv_info is a tuple of dialect, has_header, digest_types

        Parameters
        ----------
        preview_data: Iterable of iterables
        \tContains csv export data row-wise

        """

        preview_rows = 100
        preview_cols = 100

        export_preview = list(list(islice(col, None, preview_cols))
                              for col in islice(preview_data, None,
                                                preview_rows))

        filterdlg = CsvExportDialog(self.main_window, data=export_preview)

        if filterdlg.ShowModal() == wx.ID_OK:
            dialect, has_header = filterdlg.csvwidgets.get_dialect()
            digest_types = [types.StringType]
        else:
            filterdlg.Destroy()
            return

        filterdlg.Destroy()

        return dialect, has_header, digest_types

    def get_int_from_user(self, title="Enter integer value",
                          cond_func=lambda i: i is not None):
        """Opens an integer entry dialog and returns integer

        Parameters
        ----------
        title: String
        \tDialog title
        cond_func: Function
        \tIf cond_func of int(<entry_value> then result is returned.
        \tOtherwise the dialog pops up again.

        """

        is_integer = False

        while not is_integer:
            dlg = wx.TextEntryDialog(None, title, title)

            if dlg.ShowModal() == wx.ID_OK:
                result = dlg.GetValue()
            else:
                return None

            dlg.Destroy()

            try:
                integer = int(result)

                if cond_func(integer):
                    is_integer = True

            except ValueError:
                pass

        return integer

    def get_pasteas_parameters_from_user(self, obj):
        """Opens a PasteAsDialog and returns parameters dict"""

        dlg = PasteAsDialog(None, -1, obj)
        dlg_choice = dlg.ShowModal()

        if dlg_choice != wx.ID_OK:
            dlg.Destroy()
            return None

        parameters = {}
        parameters.update(dlg.parameters)
        dlg.Destroy()

        return parameters


class DialogInterfaceMixin(object):
    """Main window interfaces to dialogs that are not modal"""

    def display_gotocell(self):
        """Displays goto cell dialog"""

        dlg = CellEntryDialog(self.main_window)

        dlg.Show()

    def display_macros(self):
        """Displays macro dialog"""

        macros = self.main_window.grid.code_array.macros

        dlg = MacroDialog(self.main_window, macros, -1)

        dlg.Show()

    def display_about(self, parent):
        """Displays About dialog"""

        AboutDialog(parent)


class GuiInterfaces(DialogInterfaceMixin, ModalDialogInterfaceMixin):
    """Main window interfaces to GUI elements"""

    def __init__(self, main_window):
        self.main_window = main_window


def get_key_params_from_user():
    """Displays parameter entry dialog and returns parameter dict"""

    gpg_key_parameters = [
        ('key_type', 'DSA'),
        ('key_length', '2048'),
        ('subkey_type', 'ELG-E'),
        ('subkey_length', '2048'),
        ('expire_date', '0'),
    ]

    params = [
        [_('Real name'), 'name_real'],
    ]

    vals = [""] * len(params)

    while "" in vals:
        dlg = GPGParamsDialog(None, -1, "Enter GPG key parameters", params)
        dlg.CenterOnScreen()

        for val, textctrl in zip(vals, dlg.textctrls):
            textctrl.SetValue(val)

        if dlg.ShowModal() != wx.ID_OK:
            sys.exit()

        vals = [textctrl.Value for textctrl in dlg.textctrls]

        dlg.Destroy()

        if "" in vals:
            msg = _("Please enter a value in each field.")

            dlg = GMD.GenericMessageDialog(None, msg, _("Missing value"),
                                           wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()

    for (__, key), val in zip(params, vals):
        gpg_key_parameters.insert(-2, (key, val))

    return dict(gpg_key_parameters)
########NEW FILE########
__FILENAME__ = _main_window
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
_main_window
============

Provides:
---------
  1) MainWindow: Main window of the application pyspread

"""

import ast
import os

import wx
import wx.lib.agw.aui as aui

from matplotlib.figure import Figure

import src.lib.i18n as i18n
from src.config import config
from src.sysvars import get_python_tutorial_path, is_gtk

from _menubars import MainMenu
from _toolbars import MainToolbar, MacroToolbar, FindToolbar, AttributesToolbar
from _widgets import EntryLineToolbarPanel, StatusBar

from src.lib.clipboard import Clipboard

from _gui_interfaces import GuiInterfaces
from src.gui.icons import icons

from _grid import Grid

from _events import post_command_event, EventMixin

from src.actions._main_window_actions import AllMainWindowActions

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


class MainWindow(wx.Frame, EventMixin):
    """Main window of pyspread"""

    def __init__(self, parent, *args, **kwargs):
        try:
            S = kwargs.pop("S")

        except KeyError:
            S = None

        wx.Frame.__init__(self, parent, *args, **kwargs)

        self.interfaces = GuiInterfaces(self)

        try:
            self._mgr = aui.AuiManager(self)

        except Exception:
            # This may fail if py.testv runs under Windows
            # Therefore, we set up a basic framework for the unit tests
            self.grid = Grid(self, -1, S=S, dimensions=(1000, 100, 3))
            self.clipboard = Clipboard()
            self.actions = AllMainWindowActions(self.grid)

        self.parent = parent

        self.handlers = MainWindowEventHandlers(self)

        # Program states
        # --------------

        self._states()

        # GUI elements
        # ------------

        # Menu Bar
        self.menubar = wx.MenuBar()
        self.main_menu = MainMenu(parent=self, menubar=self.menubar)
        self.SetMenuBar(self.menubar)

        # Disable menu item for leaving safe mode
        post_command_event(self, self.SafeModeExitMsg)

        # Status bar
        statusbar = StatusBar(self)
        self.SetStatusBar(statusbar)

        welcome_text = _("Welcome to pyspread.")
        post_command_event(self, self.StatusBarMsg, text=welcome_text)

        # Toolbars
        self.main_toolbar = MainToolbar(self, -1)
        self.macro_toolbar = MacroToolbar(self, -1)
        self.find_toolbar = FindToolbar(self, -1)
        self.attributes_toolbar = AttributesToolbar(self, -1)

        # Entry line
        self.entry_line_panel = EntryLineToolbarPanel(self, -1)

        # Main grid

        dimensions = (
            config["grid_rows"],
            config["grid_columns"],
            config["grid_tables"],
        )

        self.grid = Grid(self, -1, S=S, dimensions=dimensions)

        # Clipboard
        self.clipboard = Clipboard()

        # Main window actions

        self.actions = AllMainWindowActions(self.grid)

        # Layout and bindings

        self._set_properties()
        self._do_layout()
        self._bind()

    def _states(self):
        """Sets main window states"""

        # Has the current file been changed since the last save?
        self.changed_since_save = False
        self.filepath = None

        # Print data

        self.print_data = wx.PrintData()
        # wx.PrintData properties setup from
        # http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3471083

    def _set_properties(self):
        """Setup title, icon, size, scale, statusbar, main grid"""

        self.set_icon(icons["PyspreadLogo"])

        # Set initial size to 90% of screen
        self.SetInitialSize(config["window_size"])
        self.SetPosition(config["window_position"])

        # Without minimum size, initial size is minimum size in wxGTK
        self.SetMinSize((2, 2))

        # Leave save mode
        post_command_event(self, self.SafeModeExitMsg)

    def _set_menu_toggles(self):
        """Enable menu bar view item checkmarks"""

        toggles = [
            (self.main_toolbar, "main_window_toolbar", _("Main toolbar")),
            (self.macro_toolbar, "macro_toolbar", _("Macro toolbar")),
            (self.attributes_toolbar, "attributes_toolbar",
             _("Format toolbar")),
            (self.find_toolbar, "find_toolbar", _("Find toolbar")),
            (self.entry_line_panel, "entry_line_panel", _("Entry line")),
        ]

        for toolbar, pane_name, toggle_label in toggles:
            # Get pane from aui manager
            pane = self._mgr.GetPane(pane_name)

            # Get menu item to toggle
            toggle_id = self.menubar.FindMenuItem(_("View"), toggle_label)

            toggle_item = self.menubar.FindItemById(toggle_id)

            # Adjust toggle to pane visibility
            toggle_item.Check(pane.IsShown())

    def _do_layout(self):
        """Adds widgets to the aui manager and controls the layout"""

        # Add the toolbars to the manager

        self._mgr.AddPane(self.main_toolbar, aui.AuiPaneInfo().
                          Name("main_window_toolbar").
                          Caption(_("Main toolbar")).
                          ToolbarPane().Top().Row(0))

        self._mgr.AddPane(self.find_toolbar, aui.AuiPaneInfo().
                          Name("find_toolbar").Caption(_("Find toolbar")).
                          ToolbarPane().Top().Row(0))

        self._mgr.AddPane(self.attributes_toolbar, aui.AuiPaneInfo().
                          Name("attributes_toolbar").
                          Caption(_("Format toolbar")).
                          ToolbarPane().Top().Row(1))

        self._mgr.AddPane(self.macro_toolbar, aui.AuiPaneInfo().
                          Name("macro_toolbar").Caption(_("Macro toolbar")).
                          Gripper(True).ToolbarPane().Top().Row(1))

        self._mgr.AddPane(self.entry_line_panel, aui.AuiPaneInfo().
                          Name("entry_line_panel").Caption(_("Entry line")).
                          MinSize((10, 20)).Row(2).CaptionVisible(False).
                          Top().CloseButton(True).Gripper(True).
                          MaximizeButton(True))

        # Load perspective from config
        window_layout = config["window_layout"]

        if window_layout:
            self._mgr.LoadPerspective(window_layout)

        # Add the main grid
        self._mgr.AddPane(self.grid, aui.AuiPaneInfo().
                          Name("grid").Caption(_("Main grid")).CentrePane())

        # Tell the manager to 'commit' all the changes just made
        self._mgr.Update()
        self._mgr.GetPane("attributes_toolbar")
        self._mgr.Update()

        self._set_menu_toggles()

    def _bind(self):
        """Bind events to handlers"""

        handlers = self.handlers

        # Main window events
        self.Bind(wx.EVT_MOVE, handlers.OnMove)
        self.Bind(wx.EVT_SIZE, handlers.OnSize)

        # Content changed event, adjusts title bar with star
        self.Bind(self.EVT_CONTENT_CHANGED, handlers.OnContentChanged)

        # Program state events

        self.Bind(self.EVT_CMD_TITLE, handlers.OnTitle)
        self.Bind(self.EVT_CMD_SAFE_MODE_ENTRY, handlers.OnSafeModeEntry)
        self.Bind(self.EVT_CMD_SAFE_MODE_EXIT, handlers.OnSafeModeExit)
        self.Bind(wx.EVT_CLOSE, handlers.OnClose)
        self.Bind(self.EVT_CMD_CLOSE, handlers.OnClose)

        # Preferences events

        self.Bind(self.EVT_CMD_PREFERENCES, handlers.OnPreferences)

        # Toolbar toggle events

        self.Bind(self.EVT_CMD_MAINTOOLBAR_TOGGLE,
                  handlers.OnMainToolbarToggle)
        self.Bind(self.EVT_CMD_MACROTOOLBAR_TOGGLE,
                  handlers.OnMacroToolbarToggle)
        self.Bind(self.EVT_CMD_ATTRIBUTESTOOLBAR_TOGGLE,
                  handlers.OnAttributesToolbarToggle)
        self.Bind(self.EVT_CMD_FIND_TOOLBAR_TOGGLE,
                  handlers.OnFindToolbarToggle)
        self.Bind(self.EVT_CMD_ENTRYLINE_TOGGLE,
                  handlers.OnEntryLineToggle)
        self.Bind(aui.EVT_AUI_PANE_CLOSE, handlers.OnPaneClose)

        # File events

        self.Bind(self.EVT_CMD_NEW, handlers.OnNew)
        self.Bind(self.EVT_CMD_OPEN, handlers.OnOpen)
        self.Bind(self.EVT_CMD_SAVE, handlers.OnSave)
        self.Bind(self.EVT_CMD_SAVEAS, handlers.OnSaveAs)
        self.Bind(self.EVT_CMD_IMPORT, handlers.OnImport)
        self.Bind(self.EVT_CMD_EXPORT, handlers.OnExport)
        self.Bind(self.EVT_CMD_APPROVE, handlers.OnApprove)
        self.Bind(self.EVT_CMD_CLEAR_GLOBALS, handlers.OnClearGlobals)

        # Find events
        self.Bind(self.EVT_CMD_FOCUSFIND, handlers.OnFocusFind)

        # Format events
        self.Bind(self.EVT_CMD_FONTDIALOG, handlers.OnFontDialog)
        self.Bind(self.EVT_CMD_TEXTCOLORDIALOG, handlers.OnTextColorDialog)
        self.Bind(self.EVT_CMD_BGCOLORDIALOG, handlers.OnBgColorDialog)

        # Print events

        self.Bind(self.EVT_CMD_PAGE_SETUP, handlers.OnPageSetup)
        self.Bind(self.EVT_CMD_PRINT_PREVIEW, handlers.OnPrintPreview)
        self.Bind(self.EVT_CMD_PRINT, handlers.OnPrint)

        # Edit Events
        self.Bind(self.EVT_CMD_SELECT_ALL, handlers.OnSelectAll)

        # Clipboard events

        self.Bind(self.EVT_CMD_CUT, handlers.OnCut)
        self.Bind(self.EVT_CMD_COPY, handlers.OnCopy)
        self.Bind(self.EVT_CMD_COPY_RESULT, handlers.OnCopyResult)
        self.Bind(self.EVT_CMD_PASTE, handlers.OnPaste)
        self.Bind(self.EVT_CMD_PASTE_AS, handlers.OnPasteAs)

        # Help events

        self.Bind(self.EVT_CMD_MANUAL, handlers.OnManual)
        self.Bind(self.EVT_CMD_TUTORIAL, handlers.OnTutorial)
        self.Bind(self.EVT_CMD_FAQ, handlers.OnFaq)
        self.Bind(self.EVT_CMD_PYTHON_TURORIAL, handlers.OnPythonTutorial)
        self.Bind(self.EVT_CMD_ABOUT, handlers.OnAbout)

        self.Bind(self.EVT_CMD_MACROLIST, handlers.OnMacroList)
        self.Bind(self.EVT_CMD_MACROREPLACE, handlers.OnMacroReplace)
        self.Bind(self.EVT_CMD_MACROEXECUTE, handlers.OnMacroExecute)
        self.Bind(self.EVT_CMD_MACROLOAD, handlers.OnMacroListLoad)
        self.Bind(self.EVT_CMD_MACROSAVE, handlers.OnMacroListSave)

    def set_icon(self, bmp):
        """Sets main window icon to given wx.Bitmap"""

        _icon = wx.EmptyIcon()
        _icon.CopyFromBitmap(bmp)
        self.SetIcon(_icon)

    def get_safe_mode(self):
        """Returns safe_mode state from code_array"""

        return self.grid.code_array.safe_mode

    safe_mode = property(get_safe_mode)

# End of class MainWindow


class MainWindowEventHandlers(EventMixin):
    """Contains main window event handlers"""

    def __init__(self, parent):
        self.main_window = parent
        self.interfaces = parent.interfaces

    # Main window events

    def OnMove(self, event):
        """Main window move event"""

        # Store window position in config

        position = event.GetPosition()

        config["window_position"] = repr((position.x, position.y))

    def OnSize(self, event):
        """Main window move event"""

        # Store window size in config

        size = event.GetSize()

        config["window_size"] = repr((size.width, size.height))

    def OnContentChanged(self, event):
        """Titlebar star adjustment event handler"""

        self.main_window.changed_since_save = event.changed

        title = self.main_window.GetTitle()

        if event.changed:
            # Put * in front of title
            if title[:2] != "* ":
                new_title = "* " + title
                post_command_event(self.main_window, self.main_window.TitleMsg,
                                   text=new_title)

        elif title[:2] == "* ":
            # Remove * in front of title
            new_title = title[2:]
            post_command_event(self.main_window, self.main_window.TitleMsg,
                               text=new_title)

    def OnTitle(self, event):
        """Title change event handler"""

        self.main_window.SetTitle(event.text)

    def OnSafeModeEntry(self, event):
        """Safe mode entry event handler"""

        # Enable menu item for leaving safe mode

        self.main_window.main_menu.enable_file_approve(True)

        self.main_window.grid.Refresh()

        event.Skip()

    def OnSafeModeExit(self, event):
        """Safe mode exit event handler"""

        # Run macros

        ##self.MainGrid.model.pysgrid.sgrid.execute_macros(safe_mode=False)

        # Disable menu item for leaving safe mode

        self.main_window.main_menu.enable_file_approve(False)

        self.main_window.grid.Refresh()

        event.Skip()

    def OnClose(self, event):
        """Program exit event handler"""

        # If changes have taken place save of old grid

        if self.main_window.changed_since_save:
            save_choice = self.interfaces.get_save_request_from_user()

            if save_choice is None:
                # Cancelled close operation
                return

            elif save_choice:
                # User wants to save content
                post_command_event(self.main_window, self.main_window.SaveMsg)

        # Save the AUI state

        config["window_layout"] = repr(self.main_window._mgr.SavePerspective())

        # Uninit the AUI stuff

        self.main_window._mgr.UnInit()

        # Save config
        config.save()

        # Close main_window

        self.main_window.Destroy()

        # Set file mode to 600 to protect GPG passwd a bit
        sp = wx.StandardPaths.Get()
        pyspreadrc_path = sp.GetUserConfigDir() + "/." + config.config_filename
        try:
            os.chmod(pyspreadrc_path, 0600)
        except OSError:
            dummyfile = open(pyspreadrc_path, "w")
            dummyfile.close()
            os.chmod(pyspreadrc_path, 0600)

    # Preferences events

    def OnPreferences(self, event):
        """Preferences event handler that launches preferences dialog"""

        preferences = self.interfaces.get_preferences_from_user()

        if preferences:
            for key in preferences:
                if type(config[key]) in (type(u""), type("")):
                    config[key] = preferences[key]
                else:
                    config[key] = ast.literal_eval(preferences[key])

    # Toolbar events

    def _toggle_pane(self, pane):
        """Toggles visibility of given aui pane

        Parameters
        ----------

        pane: String
        \tPane name

        """

        if pane.IsShown():
            pane.Hide()
        else:
            pane.Show()

        self.main_window._mgr.Update()

    def OnMainToolbarToggle(self, event):
        """Main window toolbar toggle event handler"""

        self.main_window.main_toolbar.SetGripperVisible(True)
        main_toolbar_info = \
            self.main_window._mgr.GetPane("main_window_toolbar")

        self._toggle_pane(main_toolbar_info)

        event.Skip()

    def OnMacroToolbarToggle(self, event):
        """Macro toolbar toggle event handler"""

        self.main_window.macro_toolbar.SetGripperVisible(True)
        macro_toolbar_info = self.main_window._mgr.GetPane("macro_toolbar")

        self._toggle_pane(macro_toolbar_info)

        event.Skip()

    def OnAttributesToolbarToggle(self, event):
        """Format toolbar toggle event handler"""

        self.main_window.attributes_toolbar.SetGripperVisible(True)
        attributes_toolbar_info = \
            self.main_window._mgr.GetPane("attributes_toolbar")

        self._toggle_pane(attributes_toolbar_info)

        event.Skip()

    def OnFindToolbarToggle(self, event):
        """Search toolbar toggle event handler"""

        self.main_window.find_toolbar.SetGripperVisible(True)

        find_toolbar_info = self.main_window._mgr.GetPane("find_toolbar")

        self._toggle_pane(find_toolbar_info)

        event.Skip()

    def OnEntryLineToggle(self, event):
        """Entry line toggle event handler"""

        entry_line_panel_info = \
            self.main_window._mgr.GetPane("entry_line_panel")

        self._toggle_pane(entry_line_panel_info)

        event.Skip()

    def OnPaneClose(self, event):
        """Pane close toggle event handler (via close button)"""

        toggle_label = event.GetPane().caption

        # Get menu item to toggle
        menubar = self.main_window.menubar
        toggle_id = menubar.FindMenuItem(_("View"), toggle_label)
        toggle_item = menubar.FindItemById(toggle_id)

        # Adjust toggle to pane visibility
        toggle_item.Check(False)

        menubar.UpdateMenus()

        self.main_window._mgr.Update()

        event.Skip()

    # File events

    def OnNew(self, event):
        """New grid event handler"""

        # If changes have taken place save of old grid

        if self.main_window.changed_since_save:
            save_choice = self.interfaces.get_save_request_from_user()

            if save_choice is None:
                # Cancelled close operation
                return

            elif save_choice:
                # User wants to save content
                post_command_event(self.main_window, self.main_window.SaveMsg)

        # Get grid dimensions

        shape = self.interfaces.get_dimensions_from_user(no_dim=3)

        if shape is None:
            return

        # Set new filepath and post it to the title bar

        self.main_window.filepath = None
        post_command_event(self.main_window, self.main_window.TitleMsg,
                           text="pyspread")

        # Clear globals
        self.main_window.grid.actions.clear_globals_reload_modules()

        # Create new grid
        post_command_event(self.main_window, self.main_window.GridActionNewMsg,
                           shape=shape)

        # Update TableChoiceIntCtrl
        post_command_event(self.main_window, self.main_window.ResizeGridMsg,
                           shape=shape)

        if is_gtk():
            wx.Yield()

        self.main_window.grid.actions.change_grid_shape(shape)

        self.main_window.grid.GetTable().ResetView()
        self.main_window.grid.ForceRefresh()

        # Display grid creation in status bar
        msg = _("New grid with dimensions {dim} created.").format(dim=shape)
        post_command_event(self.main_window, self.main_window.StatusBarMsg,
                           text=msg)

        self.main_window.grid.ForceRefresh()

        if is_gtk():
            wx.Yield()

        # Mark content as unchanged
        try:
            post_command_event(self.main_window, self.ContentChangedMsg,
                               changed=False)
        except TypeError:
            # The main window does not exist any more
            pass

    def OnOpen(self, event):
        """File open event handler"""

        # If changes have taken place save of old grid

        if self.main_window.changed_since_save:
            save_choice = self.interfaces.get_save_request_from_user()

            if save_choice is None:
                # Cancelled close operation
                return

            elif save_choice:
                # User wants to save content
                post_command_event(self.main_window, self.main_window.SaveMsg)

        # Get filepath from user

        try:
            import xlrd
            wildcard = \
                _("Pyspread file") + " (*.pys)|*.pys|" + \
                _("Excel file") + " (*.xls)|*.xls|" + \
                _("All files") + " (*.*)|*.*"

        except ImportError:
            wildcard = \
                _("Pyspread file") + " (*.pys)|*.pys|" + \
                _("All files") + " (*.*)|*.*"
            xlrd = None

        message = _("Choose file to open.")
        style = wx.OPEN
        filepath, filterindex = \
            self.interfaces.get_filepath_findex_from_user(wildcard, message,
                                                          style)

        if filepath is None:
            return

        filetype = "pys" if xlrd is None or filterindex != 1 else "xls"

        # Change the main window filepath state

        self.main_window.filepath = filepath

        # Load file into grid
        post_command_event(self.main_window,
                           self.main_window.GridActionOpenMsg,
                           attr={"filepath": filepath, "filetype": filetype})

        # Set Window title to new filepath

        title_text = filepath.split("/")[-1] + " - pyspread"
        post_command_event(self.main_window,
                           self.main_window.TitleMsg, text=title_text)

        self.main_window.grid.ForceRefresh()

        if is_gtk():
            wx.Yield()

        # Mark content as unchanged
        try:
            post_command_event(self.main_window, self.ContentChangedMsg,
                               changed=False)
        except TypeError:
            # The main window does not exist any more
            pass

    def OnSave(self, event):
        """File save event handler"""

        try:
            filetype = event.attr["filetype"]

        except (KeyError, AttributeError):
            filetype = "pys"

        # If there is no filepath then jump to save as

        if self.main_window.filepath is None:
            post_command_event(self.main_window,
                               self.main_window.SaveAsMsg)
            return

        # Save the grid

        post_command_event(self.main_window,
                           self.main_window.GridActionSaveMsg,
                           attr={"filepath": self.main_window.filepath,
                                 "filetype": filetype})

        # Display file save in status bar

        statustext = self.main_window.filepath.split("/")[-1] + " saved."
        post_command_event(self.main_window,
                           self.main_window.StatusBarMsg,
                           text=statustext)

    def OnSaveAs(self, event):
        """File save as event handler"""

        # Get filepath from user

        try:
            import xlwt
            wildcard = \
                _("Pyspread file") + " (*.pys)|*.pys|" + \
                _("Excel file") + " (*.xls)|*.xls|" + \
                _("All files") + " (*.*)|*.*"

        except ImportError:
            wildcard = \
                _("Pyspread file") + " (*.pys)|*.pys|" + \
                _("All files") + " (*.*)|*.*"

        message = _("Choose filename for saving.")
        style = wx.SAVE
        filepath, filterindex = \
            self.interfaces.get_filepath_findex_from_user(wildcard, message,
                                                          style)

        if filepath is None:
            return 0

        filetype = "pys" if xlwt is None or filterindex != 1 else "xls"

        # Look if path is already present
        if os.path.exists(filepath):
            if not os.path.isfile(filepath):
                # There is a directory with the same path
                statustext = _("Directory present. Save aborted.")
                post_command_event(self.main_window,
                                   self.main_window.StatusBarMsg,
                                   text=statustext)
                return 0

            # There is a file with the same path
            message = \
                _("The file {filepath} is already present.\nOverwrite?")\
                .format(filepath=filepath)
            short_msg = _("File collision")

            if not self.main_window.interfaces.get_warning_choice(message,
                                                                  short_msg):

                statustext = _("File present. Save aborted by user.")
                post_command_event(self.main_window,
                                   self.main_window.StatusBarMsg,
                                   text=statustext)
                return 0

        # Put pys suffix if wildcard choice is 0
        if filterindex == 0 and filepath[-4:] != ".pys":
            filepath += ".pys"

        # Set the filepath state
        self.main_window.filepath = filepath

        # Set Window title to new filepath
        title_text = filepath.split("/")[-1] + " - pyspread"
        post_command_event(self.main_window, self.main_window.TitleMsg,
                           text=title_text)

        # Now jump to save
        post_command_event(self.main_window, self.main_window.SaveMsg,
                           attr={"filetype": filetype})

    def OnImport(self, event):
        """File import event handler"""

        # Get filepath from user

        wildcard = \
            _("CSV file") + " (*.*)|*.*|" + \
            _("Tab delimited text file") + " (*.*)|*.*"
        message = _("Choose file to import.")
        style = wx.OPEN
        filepath, filterindex = \
            self.interfaces.get_filepath_findex_from_user(wildcard, message,
                                                          style)

        if filepath is None:
            return

        # Get generator of import data
        import_data = self.main_window.actions.import_file(filepath,
                                                           filterindex)

        if import_data is None:
            return

        # Paste import data to grid
        grid = self.main_window.grid
        tl_cell = grid.GetGridCursorRow(), grid.GetGridCursorCol()

        grid.actions.paste(tl_cell, import_data)

        self.main_window.grid.ForceRefresh()

    def OnExport(self, event):
        """File export event handler

        Currently, only CSV export is supported

        """

        code_array = self.main_window.grid.code_array
        tab = self.main_window.grid.current_table

        selection = self.main_window.grid.selection

        # Check if no selection is present

        selection_bbox = selection.get_bbox()

        wildcard = _("CSV file") + " (*.*)|*.*"

        if selection_bbox is None:
            # No selection --> Use smallest filled area for bottom right edge
            maxrow, maxcol, __ = code_array.get_last_filled_cell(tab)

            (top, left), (bottom, right) = (0, 0), (maxrow, maxcol)

        else:
            (top, left), (bottom, right) = selection_bbox

        # Generator of row and column keys in correct order

        __top = 0 if top is None else top
        __bottom = code_array.shape[0] if bottom is None else bottom + 1
        __left = 0 if left is None else left
        __right = code_array.shape[1] if right is None else right + 1

        def data_gen(top, bottom, left, right):
            for row in xrange(top, bottom):
                yield (code_array[row, col, tab]
                       for col in xrange(left, right))

        data = data_gen(__top, __bottom, __left, __right)
        preview_data = data_gen(__top, __bottom, __left, __right)

        # Get target filepath from user

        # No selection --> Provide svg export of current cell
        # if current cell is a matplotlib figure
        if selection_bbox is None:
            cursor = self.main_window.grid.actions.cursor
            figure = code_array[cursor]
            if isinstance(figure, Figure):
                wildcard += \
                    "|" + _("SVG file") + " (*.svg)|*.svg" + \
                    "|" + _("EPS file") + " (*.eps)|*.eps" + \
                    "|" + _("PS file") + " (*.ps)|*.ps" + \
                    "|" + _("PDF file") + " (*.pdf)|*.pdf" + \
                    "|" + _("PNG file") + " (*.png)|*.png"

        message = _("Choose filename for export.")
        style = wx.SAVE
        path, filterindex = \
            self.interfaces.get_filepath_findex_from_user(wildcard, message,
                                                          style)

        # If an svg is exported then the selection bbox
        # has to be changed to the current cell
        if filterindex >= 1:
            data = figure

        # Export file
        # -----------

        self.main_window.actions.export_file(path, filterindex, data,
                                             preview_data)

    def OnApprove(self, event):
        """File approve event handler"""

        if not self.main_window.safe_mode:
            return

        msg = _(u"You are going to approve and trust a file that\n"
                u"you have not created yourself.\n"
                u"After proceeding, the file is executed.\n \n"
                u"It may harm your system as any program can.\n"
                u"Please check all cells thoroughly before\nproceeding.\n \n"
                u"Proceed and sign this file as trusted?")

        short_msg = _("Security warning")

        if self.main_window.interfaces.get_warning_choice(msg, short_msg):
            # Leave safe mode
            self.main_window.grid.actions.leave_safe_mode()

            # Display safe mode end in status bar

            statustext = _("Safe mode deactivated.")
            post_command_event(self.main_window, self.main_window.StatusBarMsg,
                               text=statustext)

    def OnClearGlobals(self, event):
        """Clear globals event handler"""

        msg = _("Deleting globals and reloading modules cannot be undone."
                " Proceed?")
        short_msg = _("Really delete globals and modules?")

        choice = self.main_window.interfaces.get_warning_choice(msg, short_msg)

        if choice:
            self.main_window.grid.actions.clear_globals_reload_modules()

            statustext = _("Globals cleared and base modules reloaded.")
            post_command_event(self.main_window, self.main_window.StatusBarMsg,
                               text=statustext)

    # Print events

    def OnPageSetup(self, event):
        """Page setup handler for printing framework"""

        print_data = self.main_window.print_data
        new_print_data = \
            self.main_window.interfaces.get_print_setup(print_data)
        self.main_window.print_data = new_print_data

    def _get_print_area(self):
        """Returns selection bounding box or visible area"""

        # Get print area from current selection
        selection = self.main_window.grid.selection
        print_area = selection.get_bbox()

        # If there is no selection use the visible area on the screen
        if print_area is None:
            print_area = self.main_window.grid.actions.get_visible_area()

        return print_area

    def OnPrintPreview(self, event):
        """Print preview handler"""

        print_area = self._get_print_area()
        print_data = self.main_window.print_data

        self.main_window.actions.print_preview(print_area, print_data)

    def OnPrint(self, event):
        """Print event handler"""

        print_area = self._get_print_area()
        print_data = self.main_window.print_data

        self.main_window.actions.printout(print_area, print_data)

    # Clipboard events

    def OnCut(self, event):
        """Clipboard cut event handler"""

        entry_line = \
            self.main_window.entry_line_panel.entry_line_panel.entry_line

        if wx.Window.FindFocus() != entry_line:
            selection = self.main_window.grid.selection
            data = self.main_window.actions.cut(selection)
            self.main_window.clipboard.set_clipboard(data)

            self.main_window.grid.ForceRefresh()

        else:
            entry_line.Cut()

        event.Skip()

    def OnCopy(self, event):
        """Clipboard copy event handler"""

        focus = self.main_window.FindFocus()

        if isinstance(focus, wx.TextCtrl):
            # Copy selection from TextCtrl if in focus
            focus.Copy()

        else:
            selection = self.main_window.grid.selection
            data = self.main_window.actions.copy(selection)
            self.main_window.clipboard.set_clipboard(data)

        event.Skip()

    def OnCopyResult(self, event):
        """Clipboard copy results event handler"""

        selection = self.main_window.grid.selection
        data = self.main_window.actions.copy_result(selection)

        # Check if result is a bitmap
        if type(data) is wx._gdi.Bitmap:
            # Copy bitmap to clipboard
            self.main_window.clipboard.set_clipboard(data, datatype="bitmap")

        else:
            # Copy string representation of result to clipboard

            self.main_window.clipboard.set_clipboard(data, datatype="text")

        event.Skip()

    def OnPaste(self, event):
        """Clipboard paste event handler"""

        data = self.main_window.clipboard.get_clipboard()

        focus = self.main_window.FindFocus()

        if isinstance(focus, wx.TextCtrl):
            # Paste into TextCtrl if in focus
            focus.WriteText(data)

        else:
            # We got a grid selection
            key = self.main_window.grid.actions.cursor

            self.main_window.actions.paste(key, data)

        self.main_window.grid.ForceRefresh()

        event.Skip()

    def OnPasteAs(self, event):
        """Clipboard paste as event handler"""

        data = self.main_window.clipboard.get_clipboard()
        key = self.main_window.grid.actions.cursor

        self.main_window.actions.paste_as(key, data)

        self.main_window.grid.ForceRefresh()

        event.Skip()

    # Edit events
    def OnSelectAll(self, event):
        """Select all cells event handler"""

        entry_line = \
            self.main_window.entry_line_panel.entry_line_panel.entry_line

        if wx.Window.FindFocus() != entry_line:
            self.main_window.grid.SelectAll()

        else:
            entry_line.SelectAll()

    # View events

    def OnFocusFind(self, event):
        """Event handler for focusing find toolbar text widget"""

        self.main_window.find_toolbar.search.SetFocus()

    # Format events

    def OnFontDialog(self, event):
        """Event handler for launching font dialog"""

        # Get current font data from current cell
        cursor = self.main_window.grid.actions.cursor
        attr = self.main_window.grid.code_array.cell_attributes[cursor]

        size, style, weight, font = \
            [attr[name] for name in ["pointsize", "fontstyle", "fontweight",
                                     "textfont"]]
        current_font = wx.Font(int(size), -1, style, weight, 0, font)

        # Get Font from dialog

        fontdata = wx.FontData()
        fontdata.EnableEffects(True)
        fontdata.SetInitialFont(current_font)

        dlg = wx.FontDialog(self.main_window, fontdata)

        if dlg.ShowModal() == wx.ID_OK:
            fontdata = dlg.GetFontData()
            font = fontdata.GetChosenFont()

            post_command_event(self.main_window, self.main_window.FontMsg,
                               font=font.FaceName)
            post_command_event(self.main_window, self.main_window.FontSizeMsg,
                               size=font.GetPointSize())

            post_command_event(self.main_window, self.main_window.FontBoldMsg,
                               weight=font.GetWeightString())
            post_command_event(self.main_window,
                               self.main_window.FontItalicsMsg,
                               style=font.GetStyleString())

            if is_gtk():
                wx.Yield()

            self.main_window.grid.update_attribute_toolbar()

    def OnTextColorDialog(self, event):
        """Event handler for launching text color dialog"""

        dlg = wx.ColourDialog(self.main_window)

        # Ensure the full colour dialog is displayed,
        # not the abbreviated version.
        dlg.GetColourData().SetChooseFull(True)

        if dlg.ShowModal() == wx.ID_OK:

            # Fetch color data
            data = dlg.GetColourData()
            color = data.GetColour().GetRGB()

            post_command_event(self.main_window, self.main_window.TextColorMsg,
                               color=color)

        dlg.Destroy()

    def OnBgColorDialog(self, event):
        """Event handler for launching background color dialog"""

        dlg = wx.ColourDialog(self.main_window)

        # Ensure the full colour dialog is displayed,
        # not the abbreviated version.
        dlg.GetColourData().SetChooseFull(True)

        if dlg.ShowModal() == wx.ID_OK:

            # Fetch color data
            data = dlg.GetColourData()
            color = data.GetColour().GetRGB()

            post_command_event(self.main_window,
                               self.main_window.BackgroundColorMsg,
                               color=color)

        dlg.Destroy()

    # Macro events

    def OnMacroList(self, event):
        """Macro list dialog event handler"""

        self.main_window.interfaces.display_macros()

        event.Skip()

    def OnMacroReplace(self, event):
        """Macro change event handler"""

        self.main_window.actions.replace_macros(event.macros)

    def OnMacroExecute(self, event):
        """Macro execution event handler"""

        self.main_window.actions.execute_macros()

    def OnMacroListLoad(self, event):
        """Macro list load event handler"""

        # Get filepath from user

        wildcard = \
            _("Macro file") + " (*.py)|*.py|" + \
            _("All files") + " (*.*)|*.*"
        message = _("Choose macro file.")

        style = wx.OPEN
        filepath, filterindex = \
            self.interfaces.get_filepath_findex_from_user(wildcard, message,
                                                          style)

        if filepath is None:
            return

        # Enter safe mode because macro file could be harmful

        post_command_event(self.main_window, self.main_window.SafeModeEntryMsg)

        # Load macros from file

        self.main_window.actions.open_macros(filepath)

        event.Skip()

    def OnMacroListSave(self, event):
        """Macro list save event handler"""

        # Get filepath from user

        wildcard = \
            _("Macro file") + " (*.py)|*.py|" + \
            _("All files") + " (*.*)|*.*"
        message = _("Choose macro file.")

        style = wx.SAVE
        filepath, filterindex = \
            self.interfaces.get_filepath_findex_from_user(wildcard, message,
                                                          style)

        # Save macros to file

        macros = self.main_window.grid.code_array.macros
        self.main_window.actions.save_macros(filepath, macros)

        event.Skip()

    # Help events

    def OnManual(self, event):
        """Manual launch event handler"""

        self.main_window.actions.launch_help("First steps in pyspread",
                                             "First steps.html")

    def OnTutorial(self, event):
        """Tutorial launch event handler"""

        self.main_window.actions.launch_help("Pyspread tutorial",
                                             "tutorial.html")

    def OnFaq(self, event):
        """FAQ launch event handler"""

        self.main_window.actions.launch_help("Pyspread tutorial", "faq.html")

    def OnPythonTutorial(self, event):
        """Python tutorial launch event handler"""

        self.main_window.actions.launch_help("Python tutorial",
                                             get_python_tutorial_path())

    def OnAbout(self, event):
        """About dialog event handler"""

        self.main_window.interfaces.display_about(self.main_window)

# End of class MainWindowEventHandlers
########NEW FILE########
__FILENAME__ = _menubars
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
_menubars
===========

Provides menubars

Provides:
---------
  1. ContextMenu: Context menu for main grid
  2. MainMenu: Main menu of pyspread

"""

import wx

from _events import post_command_event, EventMixin

import src.lib.i18n as i18n

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


class _filledMenu(wx.Menu):
    """Menu that fills from the attribute menudata.

    Parameters:
    parent: object
    \tThe parent object that hosts the event handler methods
    menubar: wx.Menubar, defaults to parent
    \tThe menubar to which the menu is attached

    menudata has the following structure:
    [
        [wx.Menu, _("Menuname"), [
            [wx.MenuItem, ["Methodname"), _("Itemlabel"), _("Help")]] ,
            ...
            "Separator",
            ...
            [wx.Menu, ...],
            ...
        ],
    ...
    ]

    """

    menudata = []

    def __init__(self, *args, **kwargs):
        self.parent = kwargs.pop('parent')
        try:
            self.menubar = kwargs.pop('menubar')
        except KeyError:
            self.menubar = self.parent
        wx.Menu.__init__(self, *args, **kwargs)

        # id - message type storage
        self.ids_msgs = {}

        # Stores approve_item for disabling
        self.approve_item = None

        self._add_submenu(self, self.menudata)

    def _add_submenu(self, parent, data):
        """Adds items in data as a submenu to parent"""

        for item in data:
            obj = item[0]
            if obj == wx.Menu:
                try:
                    __, menuname, submenu, menu_id = item
                except ValueError:
                    __, menuname, submenu = item
                    menu_id = -1

                menu = obj()
                self._add_submenu(menu, submenu)

                if parent == self:
                    self.menubar.Append(menu, menuname)
                else:
                    parent.AppendMenu(menu_id, menuname, menu)

            elif obj == wx.MenuItem:
                try:
                    msgtype, shortcut, helptext, item_id = item[1]
                except ValueError:
                    msgtype, shortcut, helptext = item[1]
                    item_id = wx.NewId()

                try:
                    style = item[2]
                except IndexError:
                    style = wx.ITEM_NORMAL

                menuitem = obj(parent, item_id, shortcut, helptext, style)

                parent.AppendItem(menuitem)

                if _("&Approve file") == shortcut:
                    self.approve_item = menuitem

                self.ids_msgs[item_id] = msgtype

                self.parent.Bind(wx.EVT_MENU, self.OnMenu, id=item_id)

            elif obj == "Separator":
                parent.AppendSeparator()

            else:
                raise TypeError(_("Menu item unknown"))

    def OnMenu(self, event):
        """Menu event handler"""

        msgtype = self.ids_msgs[event.GetId()]
        post_command_event(self.parent, msgtype)

# end of class _filledMenu


class ContextMenu(_filledMenu, EventMixin):
    """Context menu for grid operations"""

    def __init__(self, *args, **kwargs):

        item = wx.MenuItem

        self.menudata = [
            [item, [self.CutMsg, _("Cu&t"), _("Cut cell to clipboard"),
                    wx.ID_CUT]],
            [item, [self.CopyMsg, _("&Copy"),
                    _("Copy input strings to clipboard"), wx.ID_COPY]],
            [item, [self.PasteMsg, _("&Paste"),
                    _("Paste cells from clipboard"), wx.ID_PASTE]],
            [item, [self.InsertRowsMsg, _("Insert &rows"),
                    _("Insert rows at cursor")]],
            [item, [self.InsertColsMsg, _("&Insert columns"),
                    _("Insert columns at cursor")]],
            [item, [self.DeleteRowsMsg, _("Delete rows"), _("Delete rows")]],
            [item, [self.DeleteColsMsg, _("Delete columns"),
                    _("Delete columns")]],
        ]

        _filledMenu.__init__(self, *args, **kwargs)

# end of class ContextMenu


class MainMenu(_filledMenu, EventMixin):
    """Main application menu"""

    def __init__(self, *args, **kwargs):

        item = wx.MenuItem

        self.menudata = [
            [wx.Menu, _("&File"), [
                [item, [self.NewMsg, _("&New") + "\tCtrl+n",
                        _("Create a new, empty spreadsheet"), wx.ID_NEW]],
                [item, [self.OpenMsg, _("&Open"),
                        _("Open spreadsheet from file"), wx.ID_OPEN]],
                ["Separator"],
                [item, [self.SaveMsg, _("&Save") + "\tCtrl+s",
                        _("Save spreadsheet"), wx.ID_SAVE]],
                [item, [self.SaveAsMsg, _("Save &As") + "\tShift+Ctrl+s",
                        _("Save spreadsheet to a new file")], wx.ID_SAVEAS],
                ["Separator"],
                [item, [self.ImportMsg, _("&Import"),
                        _("Import a file and paste it into current grid")]],
                [item, [self.ExportMsg, _("&Export"), _("Export selection to "
                        "file (Supported formats: CSV)")]],
                ["Separator"],
                [item, [self.ApproveMsg, _("&Approve file"),
                        _("Approve, unfreeze and sign the current file")]],
                ["Separator"],
                [item, [self.ClearGobalsMsg, _("&Clear globals"),
                        _("Deletes global variables from memory and reloads "
                          "base modules"), wx.ID_CLEAR]],
                ["Separator"],
                [item, [self.PageSetupMsg, _("Page setup"),
                        _("Setup printer page"), wx.ID_PAGE_SETUP]],
                [item, [self.PrintPreviewMsg, _("Print preview") +
                        "\tShift+Ctrl+p", _("Print preview"), wx.ID_PREVIEW]],
                [item, [self.PrintMsg, _("&Print") + "\tCtrl+p",
                        _("Print current spreadsheet"), wx.ID_PRINT]],
                ["Separator"],
                [item, [self.PreferencesMsg, _("Preferences..."),
                        _("Change preferences of pyspread"),
                        wx.ID_PREFERENCES]],
                ["Separator"],
                [item, [self.CloseMsg, _("&Quit") + "\tCtrl+q",
                        _("Quit pyspread"), wx.ID_EXIT]]]],
            [wx.Menu, _("&Edit"), [
                [item, [self.UndoMsg, _("&Undo") + "\tCtrl+z",
                        _("Undo last step"), wx.ID_UNDO]],
                [item, [self.RedoMsg, _("&Redo") + "\tShift+Ctrl+z",
                        _("Redo last undone step"), wx.ID_REDO]],
                ["Separator"],
                [item, [self.CutMsg, _("Cu&t") + "\tCtrl+x",
                        _("Cut cell to clipboard"), wx.ID_CUT]],
                [item, [self.CopyMsg, _("&Copy") + "\tCtrl+c",
                        _("Copy the input strings of the cells to clipboard"),
                        wx.ID_COPY]],
                [item, [self.CopyResultMsg,
                        _("Copy &Results") + "\tShift+Ctrl+c",
                        _("Copy the result strings of the cells to the "
                          "clipboard")]],
                [item, [self.PasteMsg, _("&Paste") + "\tCtrl+v",
                        _("Paste cells from clipboard"), wx.ID_PASTE]],
                [item, [self.PasteAsMsg, _("Paste &As...") + "\tShift+Ctrl+v",
                        _("Transform clipboard and paste cells into grid")]],
                [item, [self.SelectAll, _("Select A&ll") + "\tCtrl+A",
                        _("Select All Cells")]],
                ["Separator"],
                [item, [self.FindFocusMsg, _("&Find") + "\tCtrl+f",
                        _("Find cell by content"), wx.ID_FIND]],
                [item, [self.ReplaceMsg, _("Replace...") + "\tCtrl+Shift+f",
                        _("Replace strings in cells"), wx.ID_REPLACE]],
                ["Separator"],
                [item, [self.QuoteMsg, _("Quote cell(s)") + "\tCtrl+Enter",
                        _('Converts cell content to strings by adding quotes '
                          '("). If a selection is present then its cells are '
                          'quoted.')]],
                ["Separator"],
                [item, [self.SortAscendingMsg, _("Sort &ascending"),
                        _("Sort rows in selection or current table ascending "
                          "corresponding to row at cursor.")]],
                [item, [self.SortDescendingMsg, _("Sort &descending"),
                        _("Sort rows in selection or current table descending "
                          "corresponding to row at cursor.")]],
                ["Separator"],
                [item, [self.InsertRowsMsg, _("Insert &rows"),
                        _("Insert rows at cursor")]],
                [item, [self.InsertColsMsg, _("&Insert columns"),
                        _("Insert columns at cursor")]],
                [item, [self.InsertTabsMsg, _("Insert &table"),
                        _("Insert table before current table")]],
                ["Separator"],
                [item, [self.DeleteRowsMsg, _("Delete rows"),
                        _("Delete rows")]],
                [item, [self.DeleteColsMsg, _("Delete columns"),
                        _("Delete columns")]],
                [item, [self.DeleteTabsMsg, _("Delete table"),
                        _("Delete current table")]],
                ["Separator"],
                [item, [self.ShowResizeGridDialogMsg, _("Resize grid"),
                        _("Resize grid")]]]],
            [wx.Menu, _("&View"), [
                [wx.Menu, _("Toolbars"), [
                    [item, [self.MainToolbarToggleMsg, _("Main toolbar"),
                            _("Shows and hides the main toolbar.")],
                        wx.ITEM_CHECK],
                    [item, [self.MacroToolbarToggleMsg, _("Macro toolbar"),
                            _("Shows and hides the macro toolbar.")],
                        wx.ITEM_CHECK],
                    [item, [self.AttributesToolbarToggleMsg,
                            _("Format toolbar"),
                            _("Shows and hides the format toolbar.")],
                        wx.ITEM_CHECK],
                    [item, [self.FindToolbarToggleMsg, _("Find toolbar"),
                            _("Shows and hides the find toolbar.")],
                        wx.ITEM_CHECK]]],
                [item, [self.EntryLineToggleMsg, _("Entry line"),
                        _("Shows and hides the entry line.")], wx.ITEM_CHECK],
                ["Separator"],
                [item, [self.DisplayGotoCellDialogMsg,
                        _("Go to cell") + "\tCtrl+G",
                        _("Moves the grid to a cell."), wx.ID_INDEX]],
                ["Separator"],
                [item, [self.ZoomInMsg, _("Zoom in") + "\tCtrl++",
                        _("Zoom in grid."), wx.ID_ZOOM_IN]],
                [item, [self.ZoomOutMsg, _("Zoom out") + "\tCtrl+-",
                        _("Zoom out grid."), wx.ID_ZOOM_OUT]],
                [item, [self.ZoomStandardMsg, _("Normal size") + "\tCtrl+0",
                        _("Show grid in standard zoom."), wx.ID_ZOOM_100]],
                ["Separator"],
                [item, [self.RefreshSelectionMsg,
                        _("Refresh selected cells") + "\tF5",
                        _("Refresh selected cells even when frozen"),
                        wx.ID_REFRESH]],
                [item, [self.TimerToggleMsg,
                        _("Toggle periodic updates"),
                        _("Toggles periodic cell updates for frozen cells")],
                 wx.ITEM_CHECK],
                ["Separator"],
                [item, [self.ViewFrozenMsg, _("Show Frozen"),
                        _("Shows which cells are currently frozen in a "
                          "crosshatch.")],
                 wx.ITEM_CHECK]]],
            [wx.Menu, _("F&ormat"), [
                [item, [self.FontDialogMsg, _("Font..."),
                        _("Launch font dialog.")]],
                [item, [self.FontBoldMsg, _("Bold") + "\tCtrl+B",
                        _("Toggles bold."), wx.ID_BOLD]],
                [item, [self.FontItalicsMsg, _("Italics") + "\tCtrl+I",
                        _("Toggles italics."), wx.ID_ITALIC]],
                [item, [self.FontUnderlineMsg, _("Underline") + "\tCtrl+U",
                        _("Toggles underline."), wx.ID_UNDERLINE]],
                [item, [self.FontStrikethroughMsg, _("Strikethrough"),
                        _("Toggles strikethrough.")]],
                ["Separator"],
                [item, [self.FrozenMsg, _("Frozen"),
                        _("Toggles frozen state of cell. ") +
                        _("Frozen cells are updated only "
                          "when F5 is pressed.")]],
                [item, [self.LockMsg, _("Lock"),
                        _("Lock cell. Locked cells cannot be changed.")]],
                [item, [self.MergeMsg, _("Merge cells"),
                        _("Merges / unmerges selected cells. ")]],

                ["Separator"],
                [wx.Menu, _("Justification"), [
                    [item, [self.JustificationMsg, _("Left"), _("Left"),
                            wx.ID_JUSTIFY_LEFT]],
                    [item, [self.JustificationMsg, _("Center"), _("Center"),
                            wx.ID_JUSTIFY_CENTER]],
                    [item, [self.JustificationMsg, _("Right"), _("Right"),
                            wx.ID_JUSTIFY_RIGHT]],
                ]],
                [wx.Menu, _("Alignment"), [
                    [item, [self.AlignmentMsg, alignment, alignment]]
                    for alignment in [_("Top"), _("Center"), _("Bottom")]]],
                ["Separator"],
                [item, [self.TextColorDialogMsg, _("Text color..."),
                        _("Launch color dialog to specify text color.")]],
                [item, [self.BgColorDialogMsg, _("Background color..."),
                        _("Launch color dialog to specify background "
                          "color.")]],
                ["Separator"],
                [item, [self.RotationDialogMsg, _("Rotation..."),
                        _("Set text rotation.")]]]],
            [wx.Menu, _("&Macro"), [
                [item, [self.MacroListMsg, _("&Macro list") + "\tCtrl+m",
                        _("Choose, fill in, manage, and create macros")]],
                [item, [self.MacroLoadMsg, _("&Load macro list"),
                        _("Load macro list")]],
                [item, [self.MacroSaveMsg, _("&Save macro list"),
                        _("Save macro list")]],
                ["Separator"],
                [item, [self.InsertBitmapMsg, _("Insert bitmap..."),
                        _("Insert bitmap from file into cell")]],
                [item, [self.LinkBitmapMsg, _("Link bitmap..."),
                        _("Link bitmap from file into cell")]],
                [item, [self.InsertChartMsg, _("Insert chart..."),
                        _("Insert chart into cell")]]]],
            [wx.Menu, _("&Help"), [
                [item, [self.ManualMsg, _("First &Steps"),
                        _("Launch First Steps in pyspread"), wx.ID_HELP]],
                [item, [self.TutorialMsg, _("&Tutorial"),
                        _("Launch tutorial")]],
                [item, [self.FaqMsg, _("&FAQ"),
                        _("Frequently asked questions")]],
                ["Separator"],
                [item, [self.PythonTutorialMsg, _("&Python tutorial"),
                        _("Python tutorial for coding information (online)")]],
                ["Separator"],
                [item, [self.AboutMsg, _("&About"), _("About pyspread"),
                        wx.ID_ABOUT]]]]
        ]

        _filledMenu.__init__(self, *args, **kwargs)

    def enable_file_approve(self, enable=True):
        """Enables or disables menu item (for entering/leaving save mode)"""

        self.approve_item.Enable(enable)

# end of class MainMenu

########NEW FILE########
__FILENAME__ = _printout
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
_printout.py
============

Printout handling module

"""

import wx

import src.lib.i18n as i18n

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


class PrintCanvas(wx.ScrolledWindow):
    """Canvas for print and print preview"""

    def __init__(self, parent, grid, print_area, id=-1, size=wx.DefaultSize):
        wx.ScrolledWindow.__init__(self, parent, id, (0, 0), size=size,
                                   style=wx.SUNKEN_BORDER)

        self.grid = grid
        self.print_area = print_area

        self.lines = []

        # Get dc size

        self.width, self.height = self._get_dc_size()

        self.x = self.y = 0
        self.curLine = []

        self.grid_attr = wx.grid.GridCellAttr()

        self.SetBackgroundColour("WHITE")
        self.SetCursor(wx.StockCursor(wx.CURSOR_PENCIL))

        self.SetVirtualSize((self.width, self.height))
        self.SetScrollRate(20, 20)

        self.Show(False)

    def _get_dc_size(self):
        """Returns width and height of print dc"""

        grid = self.grid
        (top, left), (bottom, right) = self.print_area

        tl_rect = grid.CellToRect(top, left)
        br_rect = grid.CellToRect(bottom, right)

        width = br_rect.x + br_rect.width - tl_rect.x
        height = br_rect.y + br_rect.height - tl_rect.y

        return width, height

    def draw_func(self, dc, rect, row, col):
        """Redirected Draw function from main grid"""

        return self.grid.grid_renderer.Draw(self.grid, self.grid_attr,
                                dc, rect, row, col, False, printing=True)

    def get_print_rect(self, grid_rect):
        """Returns wx.Rect that is correctly positioned on the print canvas"""

        grid = self.grid

        rect_x = grid_rect.x - \
                 grid.GetScrollPos(wx.HORIZONTAL) * grid.GetScrollLineX()
        rect_y = grid_rect.y - \
                 grid.GetScrollPos(wx.VERTICAL) * grid.GetScrollLineY()

        return wx.Rect(rect_x, rect_y, grid_rect.width, grid_rect.height)

    def DoDrawing(self, dc):
        """Main drawing method"""

        (top, left), (bottom, right) = self.print_area

        dc.BeginDrawing()

        for row in xrange(bottom, top - 1, -1):
            for col in xrange(right, left - 1, -1):

                #Draw cell content

                grid_rect = self.grid.CellToRect(row, col)
                rect = self.get_print_rect(grid_rect)

                self.draw_func(dc, rect, row, col)

                # Draw grid

                ##self.grid._main_grid.text_renderer.redraw_imminent = False
                if col == left:
                    dc.DrawLine(rect.x, rect.y, rect.x, rect.y + rect.height)
                elif col == right:
                    dc.DrawLine(rect.x + rect.width, rect.y,
                                rect.x + rect.width, rect.y + rect.height)
                if row == top:
                    dc.DrawLine(rect.x, rect.y, rect.x + rect.width, rect.y)
                elif row == bottom:
                    dc.DrawLine(rect.x, rect.y + rect.height,
                                rect.x + rect.width, rect.y + rect.height)
        dc.EndDrawing()


class Printout(wx.Printout):
    def __init__(self, canvas):
        wx.Printout.__init__(self)
        self.canvas = canvas

    def OnBeginDocument(self, start, end):
        return super(Printout, self).OnBeginDocument(start, end)

    def OnEndDocument(self):
        super(Printout, self).OnEndDocument()

    def OnBeginPrinting(self):
        super(Printout, self).OnBeginPrinting()

    def OnEndPrinting(self):
        super(Printout, self).OnEndPrinting()

    def OnPreparePrinting(self):
        super(Printout, self).OnPreparePrinting()

    def HasPage(self, page):
        if page <= 2:
            return True
        else:
            return False

    def GetPageInfo(self):
        return (1, 1, 1, 1)

    def OnPrintPage(self, page):
        dc = self.GetDC()

        # Set scaling factors

        maxX = self.canvas.width
        maxY = self.canvas.height

        # Let's have at least 50 device units margin
        marginX = 50
        marginY = 50

        # Add the margin to the graphic size
        maxX = maxX + (2 * marginX)
        maxY = maxY + (2 * marginY)

        # Get the size of the DC in pixels
        w, h = dc.GetSizeTuple()

        # Calculate a suitable scaling factor
        scaleX = float(w) / maxX
        scaleY = float(h) / maxY

        # Use x or y scaling factor, whichever fits on the DC
        actualScale = min(scaleX, scaleY)

        # Calculate the position on the DC for centering the graphic
        posX = (w - (self.canvas.width * actualScale)) / 2.0
        posY = (h - (self.canvas.height * actualScale)) / 2.0

        # Set the scale and origin
        dc.SetUserScale(actualScale, actualScale)
        dc.SetDeviceOrigin(int(posX), int(posY))

        #-------------------------------------------

        self.canvas.DoDrawing(dc)
        page_text = _("Page: {page}").format(page=page)
        dc.DrawText(page_text, marginX / 2, maxY - marginY)

        return True
########NEW FILE########
__FILENAME__ = _toolbars
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
_toolbars
===========

Provides toolbars

Provides:
---------
  1. MainToolbar: Main toolbar of pyspread
  2. FindToolbar: Toolbar for Find operation
  3. AttributesToolbar: Toolbar for editing cell attributes

"""

import wx
import wx.lib.colourselect as csel
import wx.lib.agw.aui as aui

from _events import post_command_event, EventMixin

import src.lib.i18n as i18n

from src.config import config
from src.sysvars import get_default_font, get_font_list
from icons import icons

import _widgets

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


class ToolbarBase(aui.AuiToolBar, EventMixin):
    """Base class for toolbars, requires self.toolbardata set in init

    Toolbardata has the following structure:
    [["tool type", "method name", "label", "tool tip"], ... ]

    Tool types are:

    "T": Simple tool
    "S": Separator
    "C": Control
    "O": Check tool / option button

    """

    def __init__(self, parent, *args, **kwargs):

        # Toolbars should be able to overflow
        kwargs["agwStyle"] = aui.AUI_TB_OVERFLOW | aui.AUI_TB_GRIPPER

        aui.AuiToolBar.__init__(self, parent, *args, **kwargs)

        self.SetToolBitmapSize(icons.icon_size)

        self.ids_msgs = {}
        self.label2id = {}

        self.parent = parent

        self.SetGripperVisible(True)

    def add_tools(self):
        """Adds tools from self.toolbardata to self"""

        for data in self.toolbardata:
            # tool type is in data[0]

            if data[0] == "T":
                # Simple tool

                _, msg_type, label, tool_tip = data
                icon = icons[label]

                self.label2id[label] = tool_id = wx.NewId()

                self.AddSimpleTool(tool_id, label, icon,
                                   short_help_string=tool_tip)

                self.ids_msgs[tool_id] = msg_type

                self.parent.Bind(wx.EVT_TOOL, self.OnTool, id=tool_id)

            elif data[0] == "S":
                # Separator

                self.AddSeparator()

            elif data[0] == "C":
                # Control

                _, control, tool_tip = data

                self.AddControl(control, label=tool_tip)

            elif data[0] == "O":
                # Check tool / option button

                _, label, tool_tip = data
                icon = icons[label]

                self.label2id[label] = tool_id = wx.NewId()

                self.AddCheckTool(tool_id, label, icon, icon, tool_tip)

            else:
                raise ValueError("Unknown tooltype " + str(data[0]))

        self.SetCustomOverflowItems([], [])
        self.Realize()

        # Adjust Toolbar size
        self.SetSize(self.DoGetBestSize())

    def OnTool(self, event):
        """Toolbar event handler"""

        msgtype = self.ids_msgs[event.GetId()]
        post_command_event(self, msgtype)


class MainToolbar(ToolbarBase):
    """Main application toolbar, built from attribute toolbardata"""

    def __init__(self, parent, *args, **kwargs):

        ToolbarBase.__init__(self, parent, *args, **kwargs)

        self.toolbardata = [
            ["T", self.NewMsg, "FileNew", _("New")],
            ["T", self.OpenMsg, "FileOpen", _("Open")],
            ["T", self.SaveMsg, "FileSave", _("Save")],
            ["S"],
            ["T", self.UndoMsg, "Undo", _("Undo")],
            ["T", self.RedoMsg, "Redo", _("Redo")],
            ["S"],
            ["T", self.FindFocusMsg, "Find", _("Find")],
            ["T", self.ReplaceMsg, "FindReplace", _("Replace")],
            ["S"],
            ["T", self.CutMsg, "EditCut", _("Cut")],
            ["T", self.CopyMsg, "EditCopy", _("Copy")],
            ["T", self.CopyResultMsg, "EditCopyRes", _("Copy Results")],
            ["T", self.PasteMsg, "EditPaste", _("Paste")],
            ["S"],
            ["T", self.SortAscendingMsg, "SortAscending", _("Sort ascending")],
            ["T", self.SortDescendingMsg, "SortDescending",
             _("Sort descending")],
            ["S"],
            ["T", self.PrintMsg, "FilePrint", _("Print")],
        ]

        self.add_tools()

# end of class MainToolbar


class MacroToolbar(ToolbarBase):
    """Macro toolbar, built from attribute toolbardata"""

    def __init__(self, parent, *args, **kwargs):

        ToolbarBase.__init__(self, parent, *args, **kwargs)

        self.toolbardata = [
            ["T", self.InsertBitmapMsg, "InsertBitmap", _("Insert bitmap")],
            ["T", self.LinkBitmapMsg, "LinkBitmap", _("Link bitmap")],
            ["T", self.InsertChartMsg, "InsertChart", _("Insert chart")],
        ]

        self.add_tools()

# end of class MainToolbar


class FindToolbar(ToolbarBase):
    """Toolbar for find operations (replaces wxFindReplaceDialog)"""

    def __init__(self, parent, *args, **kwargs):

        ToolbarBase.__init__(self, parent, *args, **kwargs)

        self.search_history = []
        self.search_options = ["DOWN"]
        self.search_options_buttons = ["MATCH_CASE", "REG_EXP", "WHOLE_WORD"]

        # Controls
        # --------

        # Search entry control
        search_tooltip = _("Find in code and results")
        self.search = wx.SearchCtrl(self, size=(140, -1),
                                    style=wx.TE_PROCESS_ENTER | wx.NO_BORDER)
        self.search.SetToolTip(wx.ToolTip(search_tooltip))
        self.menu = self.make_menu()
        self.search.SetMenu(self.menu)

        # Search direction togglebutton
        direction_tooltip = _("Search direction")
        iconnames = ["GoDown", "GoUp"]
        bmplist = [icons[iconname] for iconname in iconnames]
        self.search_direction_tb = _widgets.BitmapToggleButton(self, bmplist)
        self.search_direction_tb.SetToolTip(wx.ToolTip(direction_tooltip))

        # Toolbar data
        # ------------

        self.toolbardata = [
            ["C", self.search, search_tooltip],
            ["C", self.search_direction_tb, direction_tooltip],
            ["O", "MATCH_CASE", _("Case sensitive")],
            ["O", "REG_EXP", _("Regular expression")],
            ["O", "WHOLE_WORD", _("Surrounded by whitespace")],
        ]

        self.add_tools()

        # Bindings and polish
        # -------------------

        self._bindings()

    def _bindings(self):
        self.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, self.OnSearch, self.search)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnSearch, self.search)
        self.Bind(wx.EVT_MENU_RANGE, self.OnSearchFlag)
        self.Bind(wx.EVT_BUTTON, self.OnSearchDirectionButton,
                  self.search_direction_tb)
        self.Bind(wx.EVT_MENU, self.OnMenu)

    def make_menu(self):
        """Creates the search menu"""

        menu = wx.Menu()
        item = menu.Append(-1, "Recent Searches")
        item.Enable(False)

        for __id, txt in enumerate(self.search_history):
            menu.Append(__id, txt)
        return menu

    def OnMenu(self, event):
        """Search history has been selected"""

        __id = event.GetId()
        try:
            menuitem = event.GetEventObject().FindItemById(__id)
            selected_text = menuitem.GetItemLabel()
            self.search.SetValue(selected_text)
        except AttributeError:
            # Not called by menu
            event.Skip()

    def OnSearch(self, event):
        """Event handler for starting the search"""

        search_string = self.search.GetValue()

        if search_string not in self.search_history:
            self.search_history.append(search_string)
        if len(self.search_history) > 10:
            self.search_history.pop(0)

        self.menu = self.make_menu()
        self.search.SetMenu(self.menu)

        search_flags = self.search_options + ["FIND_NEXT"]

        post_command_event(self, self.FindMsg, text=search_string,
                           flags=search_flags)

        self.search.SetFocus()

    def OnSearchDirectionButton(self, event):
        """Event handler for search direction toggle button"""

        if "DOWN" in self.search_options:
            flag_index = self.search_options.index("DOWN")
            self.search_options[flag_index] = "UP"
        elif "UP" in self.search_options:
            flag_index = self.search_options.index("UP")
            self.search_options[flag_index] = "DOWN"
        else:
            raise AttributeError(_("Neither UP nor DOWN in search_flags"))

        event.Skip()

    def OnSearchFlag(self, event):
        """Event handler for search flag toggle buttons"""

        for label in self.search_options_buttons:
            button_id = self.label2id[label]
            if button_id == event.GetId():
                if event.IsChecked():
                    self.search_options.append(label)
                else:
                    flag_index = self.search_options.index(label)
                    self.search_options.pop(flag_index)

        event.Skip()

# end of class FindToolbar


class AttributesToolbar(aui.AuiToolBar, EventMixin):
    """Toolbar for editing cell attributes

    Class attributes
    ----------------

    border_toggles: Toggles for border changes, points to
                    (top, bottom, left, right, inner, outer)
    bordermap: Meaning of each border_toggle item

    """

    border_toggles = [
        ("AllBorders",       (1, 1, 1, 1, 1, 1)),
        ("LeftBorders",      (0, 0, 1, 0, 1, 1)),
        ("RightBorders",     (0, 0, 0, 1, 1, 1)),
        ("TopBorders",       (1, 0, 0, 0, 1, 1)),
        ("BottomBorders",    (0, 1, 0, 0, 1, 1)),
        ("OutsideBorders",   (1, 1, 1, 1, 0, 1)),
        ("TopBottomBorders", (1, 1, 0, 0, 0, 1)),
    ]

    bordermap = {
        "AllBorders":       ("top", "bottom", "left", "right", "inner"),
        "LeftBorders":      ("left"),
        "RightBorders":     ("right"),
        "TopBorders":       ("top"),
        "BottomBorders":    ("bottom"),
        "OutsideBorders":   ("top", "bottom", "left", "right"),
        "TopBottomBorders": ("top", "bottom"),
    }

    def __init__(self, parent, *args, **kwargs):
        kwargs["style"] = aui.AUI_TB_OVERFLOW
        aui.AuiToolBar.__init__(self, parent, *args, **kwargs)

        self.parent = parent

        self.SetToolBitmapSize(icons.icon_size)

        self._create_font_choice_combo()
        self._create_font_size_combo()
        self._create_font_face_buttons()
        self._create_justification_button()
        self._create_alignment_button()
        self._create_borderchoice_combo()
        self._create_penwidth_combo()
        self._create_color_buttons()
        self._create_merge_button()
        self._create_textrotation_spinctrl()

        self.Realize()

        # Adjust Toolbar size
        self.SetSize(self.DoGetBestSize())

    # Create toolbar widgets
    # ----------------------

    def _create_font_choice_combo(self):
        """Creates font choice combo box"""

        self.fonts = get_font_list()
        self.font_choice_combo = \
            _widgets.FontChoiceCombobox(self, choices=self.fonts,
                                        style=wx.CB_READONLY, size=(125, -1))

        self.font_choice_combo.SetToolTipString(_(u"Text font"))

        self.AddControl(self.font_choice_combo)

        self.Bind(wx.EVT_COMBOBOX, self.OnTextFont, self.font_choice_combo)
        self.parent.Bind(self.EVT_CMD_TOOLBAR_UPDATE, self.OnUpdate)

    def _create_font_size_combo(self):
        """Creates font size combo box"""

        self.std_font_sizes = config["font_default_sizes"]
        font_size = str(get_default_font().GetPointSize())
        self.font_size_combo = \
            wx.ComboBox(self, -1, value=font_size, size=(60, -1),
                        choices=map(unicode, self.std_font_sizes),
                        style=wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER)

        self.font_size_combo.SetToolTipString(_(u"Text size\n(points)"))

        self.AddControl(self.font_size_combo)
        self.Bind(wx.EVT_COMBOBOX, self.OnTextSize, self.font_size_combo)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnTextSize, self.font_size_combo)

    def _create_font_face_buttons(self):
        """Creates font face buttons"""

        font_face_buttons = [
            (wx.FONTFLAG_BOLD, "OnBold", "FormatTextBold", _("Bold")),
            (wx.FONTFLAG_ITALIC, "OnItalics", "FormatTextItalic",
             _("Italics")),
            (wx.FONTFLAG_UNDERLINED, "OnUnderline", "FormatTextUnderline",
                _("Underline")),
            (wx.FONTFLAG_STRIKETHROUGH, "OnStrikethrough",
                "FormatTextStrikethrough", _("Strikethrough")),
            (wx.FONTFLAG_MASK, "OnFreeze", "Freeze", _("Freeze")),
            (wx.FONTFLAG_NOT_ANTIALIASED, "OnLock", "Lock", _("Lock cell")),
        ]

        for __id, method, iconname, helpstring in font_face_buttons:
            bmp = icons[iconname]
            self.AddCheckTool(__id, iconname, bmp, bmp,
                              short_help_string=helpstring)
            self.Bind(wx.EVT_TOOL, getattr(self, method), id=__id)

    def _create_justification_button(self):
        """Creates horizontal justification button"""

        iconnames = ["JustifyLeft", "JustifyCenter", "JustifyRight"]
        bmplist = [icons[iconname] for iconname in iconnames]
        self.justify_tb = _widgets.BitmapToggleButton(self, bmplist)
        self.justify_tb.SetToolTipString(_(u"Justification"))
        self.Bind(wx.EVT_BUTTON, self.OnJustification, self.justify_tb)
        self.AddControl(self.justify_tb)

    def _create_alignment_button(self):
        """Creates vertical alignment button"""

        iconnames = ["AlignTop", "AlignCenter", "AlignBottom"]
        bmplist = [icons[iconname] for iconname in iconnames]

        self.alignment_tb = _widgets.BitmapToggleButton(self, bmplist)
        self.alignment_tb.SetToolTipString(_(u"Alignment"))
        self.Bind(wx.EVT_BUTTON, self.OnAlignment, self.alignment_tb)
        self.AddControl(self.alignment_tb)

    def _create_borderchoice_combo(self):
        """Create border choice combo box"""

        choices = [c[0] for c in self.border_toggles]
        self.borderchoice_combo = \
            _widgets.BorderEditChoice(self, choices=choices,
                                      style=wx.CB_READONLY, size=(50, -1))

        self.borderchoice_combo.SetToolTipString(
            _(u"Choose borders for which attributes are changed"))

        self.borderstate = self.border_toggles[0][0]

        self.AddControl(self.borderchoice_combo)

        self.Bind(wx.EVT_COMBOBOX, self.OnBorderChoice,
                  self.borderchoice_combo)

        self.borderchoice_combo.SetValue("AllBorders")

    def _create_penwidth_combo(self):
        """Create pen width combo box"""

        choices = map(unicode, xrange(12))
        self.pen_width_combo = \
            _widgets.PenWidthComboBox(self, choices=choices,
                                      style=wx.CB_READONLY, size=(50, -1))

        self.pen_width_combo.SetToolTipString(_(u"Border width"))
        self.AddControl(self.pen_width_combo)
        self.Bind(wx.EVT_COMBOBOX, self.OnLineWidth, self.pen_width_combo)

    def _create_color_buttons(self):
        """Create color choice buttons"""

        button_size = (30, 30)
        button_style = wx.NO_BORDER

        try:
            self.linecolor_choice = \
                csel.ColourSelect(self, -1, unichr(0x2500), (0, 0, 0),
                                  size=button_size, style=button_style)
        except UnicodeEncodeError:
            # ANSI wxPython installed
            self.linecolor_choice = \
                csel.ColourSelect(self, -1, "-", (0, 0, 0),
                                  size=button_size, style=button_style)

        self.bgcolor_choice = \
            csel.ColourSelect(self, -1, "", (255, 255, 255),
                              size=button_size, style=button_style)
        self.textcolor_choice = \
            csel.ColourSelect(self, -1, "A", (0, 0, 0),
                              size=button_size, style=button_style)

        self.linecolor_choice.SetToolTipString(_(u"Border line color"))
        self.bgcolor_choice.SetToolTipString(_(u"Cell background"))
        self.textcolor_choice.SetToolTipString(_(u"Text color"))

        self.AddControl(self.linecolor_choice)
        self.AddControl(self.bgcolor_choice)
        self.AddControl(self.textcolor_choice)

        self.linecolor_choice.Bind(csel.EVT_COLOURSELECT, self.OnLineColor)
        self.bgcolor_choice.Bind(csel.EVT_COLOURSELECT, self.OnBGColor)
        self.textcolor_choice.Bind(csel.EVT_COLOURSELECT, self.OnTextColor)

    def _create_merge_button(self):
        """Create merge button"""

        bmp = icons["Merge"]
        self.mergetool_id = wx.NewId()
        self.AddCheckTool(self.mergetool_id, "Merge", bmp, bmp,
                          short_help_string=_("Merge cells"))
        self.Bind(wx.EVT_TOOL, self.OnMerge, id=self.mergetool_id)

    def _create_textrotation_spinctrl(self):
        """Create text rotation spin control"""

        self.rotation_spinctrl = wx.SpinCtrl(self, -1, "", size=(50, -1))
        self.rotation_spinctrl.SetRange(-179, 180)
        self.rotation_spinctrl.SetValue(0)

        # For compatibility with toggle buttons
        self.rotation_spinctrl.GetToolState = lambda x: None
        self.rotation_spinctrl.SetToolTipString(_(u"Cell text rotation"))

        self.AddControl(self.rotation_spinctrl)

        self.Bind(wx.EVT_SPINCTRL, self.OnRotate, self.rotation_spinctrl)

    # Update widget state methods
    # ---------------------------

    def _update_font(self, textfont):
        """Updates text font widget

        Parameters
        ----------

        textfont: String
        \tFont name

        """

        try:
            fontface_id = self.fonts.index(textfont)
        except ValueError:
            fontface_id = 0

        self.font_choice_combo.Select(fontface_id)

    def _update_pointsize(self, pointsize):
        """Updates text size widget

        Parameters
        ----------

        pointsize: Integer
        \tFont point size

        """

        self.font_size_combo.SetValue(str(pointsize))

    def _update_font_weight(self, font_weight):
        """Updates font weight widget

        Parameters
        ----------

        font_weight: Integer
        \tButton down iif font_weight == wx.FONTWEIGHT_BOLD

        """

        toggle_state = font_weight & wx.FONTWEIGHT_BOLD == wx.FONTWEIGHT_BOLD

        self.ToggleTool(wx.FONTFLAG_BOLD, toggle_state)

    def _update_font_style(self, font_style):
        """Updates font style widget

        Parameters
        ----------

        font_style: Integer
        \tButton down iif font_style == wx.FONTSTYLE_ITALIC

        """

        toggle_state = font_style & wx.FONTSTYLE_ITALIC == wx.FONTSTYLE_ITALIC

        self.ToggleTool(wx.FONTFLAG_ITALIC, toggle_state)

    def _update_frozencell(self, frozen):
        """Updates frozen cell widget

        Parameters
        ----------

        frozen: Bool or string
        \tUntoggled iif False

        """

        toggle_state = not frozen is False

        self.ToggleTool(wx.FONTFLAG_MASK, toggle_state)

    def _update_lockedcell(self, locked):
        """Updates frozen cell widget

        Parameters
        ----------

        locked: Bool or string
        \tUntoggled iif False

        """

        self.ToggleTool(wx.FONTFLAG_NOT_ANTIALIASED, locked)

    def _update_underline(self, underlined):
        """Updates underline widget

        Parameters
        ----------

        underlined: Bool
        \tToggle state

        """

        self.ToggleTool(wx.FONTFLAG_UNDERLINED, underlined)

    def _update_strikethrough(self, strikethrough):
        """Updates text strikethrough widget

        Parameters
        ----------

        strikethrough: Bool
        \tToggle state

        """

        self.ToggleTool(wx.FONTFLAG_STRIKETHROUGH, strikethrough)

    def _update_justification(self, justification):
        """Updates horizontal text justification button

        Parameters
        ----------

        justification: String in ["left", "center", "right"]
        \tSwitches button to untoggled if False and toggled if True

        """

        states = {"left": 2, "center": 0, "right": 1}

        self.justify_tb.state = states[justification]

        self.justify_tb.toggle(None)
        self.justify_tb.Refresh()

    def _update_alignment(self, alignment):
        """Updates vertical text alignment button

        Parameters
        ----------

        alignment: String in ["top", "middle", "right"]
        \tSwitches button to untoggled if False and toggled if True

        """

        states = {"top": 2, "middle": 0, "bottom": 1}

        self.alignment_tb.state = states[alignment]

        self.alignment_tb.toggle(None)
        self.alignment_tb.Refresh()

    def _update_fontcolor(self, fontcolor):
        """Updates text font color button

        Parameters
        ----------

        fontcolor: Integer
        \tText color in integer RGB format

        """

        textcolor = wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOWTEXT)
        textcolor.SetRGB(fontcolor)

        self.textcolor_choice.SetColour(textcolor)

    def _update_merge(self, merged):
        """Updates cell merge toggle control"""

        self.ToggleTool(self.mergetool_id, merged)

    def _update_textrotation(self, angle):
        """Updates text rotation spin control"""

        self.rotation_spinctrl.SetValue(angle)

    def _update_bgbrush(self, bgcolor):
        """Updates background color"""

        brush_color = wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW)
        brush_color.SetRGB(bgcolor)

        self.bgcolor_choice.SetColour(brush_color)

    def _update_bordercolor(self, bordercolor):
        """Updates background color"""

        border_color = wx.SystemSettings_GetColour(wx.SYS_COLOUR_ACTIVEBORDER)
        border_color.SetRGB(bordercolor)

        self.linecolor_choice.SetColour(border_color)

    def _update_borderwidth(self, borderwidth):
        """Updates background color"""

        self.pen_width_combo.SetSelection(borderwidth)

    # Attributes toolbar event handlers
    # ---------------------------------

    def OnUpdate(self, event):
        """Updates the toolbar states"""

        attributes = event.attr

        self._update_font(attributes["textfont"])
        self._update_pointsize(attributes["pointsize"])
        self._update_font_weight(attributes["fontweight"])
        self._update_font_style(attributes["fontstyle"])
        self._update_frozencell(attributes["frozen"])
        self._update_lockedcell(attributes["locked"])
        self._update_underline(attributes["underline"])
        self._update_strikethrough(attributes["strikethrough"])
        self._update_justification(attributes["justification"])
        self._update_alignment(attributes["vertical_align"])
        self._update_fontcolor(attributes["textcolor"])
        self._update_merge(attributes["merge_area"] is not None)
        self._update_textrotation(attributes["angle"])
        self._update_bgbrush(attributes["bgcolor"])
        self._update_bordercolor(attributes["bordercolor_bottom"])
        self._update_borderwidth(attributes["borderwidth_bottom"])

        self.Refresh()

    def OnBorderChoice(self, event):
        """Change the borders that are affected by color and width changes"""

        choicelist = event.GetEventObject().GetItems()
        self.borderstate = choicelist[event.GetInt()]

    def OnLineColor(self, event):
        """Line color choice event handler"""

        color = event.GetValue().GetRGB()
        borders = self.bordermap[self.borderstate]

        post_command_event(self, self.BorderColorMsg, color=color,
                           borders=borders)

    def OnLineWidth(self, event):
        """Line width choice event handler"""

        linewidth_combobox = event.GetEventObject()
        idx = event.GetInt()
        width = int(linewidth_combobox.GetString(idx))
        borders = self.bordermap[self.borderstate]

        post_command_event(self, self.BorderWidthMsg, width=width,
                           borders=borders)

    def OnBGColor(self, event):
        """Background color choice event handler"""

        color = event.GetValue().GetRGB()

        post_command_event(self, self.BackgroundColorMsg, color=color)

    def OnTextColor(self, event):
        """Text color choice event handler"""

        color = event.GetValue().GetRGB()

        post_command_event(self, self.TextColorMsg, color=color)

    def OnTextFont(self, event):
        """Text font choice event handler"""

        fontchoice_combobox = event.GetEventObject()
        idx = event.GetInt()

        try:
            font_string = fontchoice_combobox.GetString(idx)
        except AttributeError:
            font_string = event.GetString()

        post_command_event(self, self.FontMsg, font=font_string)

    def OnTextSize(self, event):
        """Text size combo text event handler"""

        try:
            size = int(event.GetString())

        except Exception:
            size = get_default_font().GetPointSize()

        post_command_event(self, self.FontSizeMsg, size=size)

    def OnBold(self, event):
        """Bold toggle button event handler"""

        post_command_event(self, self.FontBoldMsg)

    def OnItalics(self, event):
        """Italics toggle button event handler"""

        post_command_event(self, self.FontItalicsMsg)

    def OnUnderline(self, event):
        """Underline toggle button event handler"""

        post_command_event(self, self.FontUnderlineMsg)

    def OnStrikethrough(self, event):
        """Strikethrough toggle button event handler"""

        post_command_event(self, self.FontStrikethroughMsg)

    def OnFreeze(self, event):
        """Frozen toggle button event handler"""

        post_command_event(self, self.FrozenMsg)

    def OnLock(self, event):
        """Lock toggle button event handler"""

        post_command_event(self, self.LockMsg)

    def OnJustification(self, event):
        """Justification toggle button event handler"""

        post_command_event(self, self.JustificationMsg)

    def OnAlignment(self, event):
        """Alignment toggle button event handler"""

        post_command_event(self, self.AlignmentMsg)

    def OnMerge(self, event):
        """Merge button event handler"""

        post_command_event(self, self.MergeMsg)

    def OnRotate(self, event):
        """Rotation spin control event handler"""

        angle = self.rotation_spinctrl.GetValue()

        post_command_event(self, self.TextRotationMsg, angle=angle)

# end of class AttributesToolbar

########NEW FILE########
__FILENAME__ = _widgets
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
_widgets
========

Provides:
---------
  1. PythonSTC: Syntax highlighting editor
  2. ImageComboBox: Base class for image combo boxes
  3. PenWidthComboBox: ComboBox for pen width selection
  4. MatplotlibStyleChoice: Base class for matplotlib chart style choices
  5. LineStyleComboBox: ChoiceBox for selection matplotlib line styles
  6. MarkerStyleComboBox: ChoiceBox for selection matplotlib marker styles
  7. FontChoiceCombobox: ComboBox for font selection
  8. BorderEditChoice: ComboBox for border selection
  9. BitmapToggleButton: Button that toggles through a list of bitmaps
 10. EntryLine: The line for entering cell code
 11. StatusBar: Main window statusbar
 12. TableChoiceIntCtrl: IntCtrl for choosing the current grid table

"""

import keyword
from copy import copy

import wx
import wx.grid
import wx.combo
import wx.stc as stc
from wx.lib.intctrl import IntCtrl, EVT_INT

import src.lib.i18n as i18n
from src.config import config
from src.sysvars import get_default_font, is_gtk

from _events import post_command_event, EntryLineEventMixin, GridCellEventMixin
from _events import StatusBarEventMixin, GridEventMixin, GridActionEventMixin
from _events import MainWindowEventMixin

from icons import icons

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


class PythonSTC(stc.StyledTextCtrl):
    """Editor that highlights Python source code.

    Stolen from the wxPython demo.py

    """

    def __init__(self, *args, **kwargs):
        stc.StyledTextCtrl.__init__(self, *args, **kwargs)

        self._style()

        self.CmdKeyAssign(ord('B'), stc.STC_SCMOD_CTRL, stc.STC_CMD_ZOOMIN)
        self.CmdKeyAssign(ord('N'), stc.STC_SCMOD_CTRL, stc.STC_CMD_ZOOMOUT)

        self.SetLexer(stc.STC_LEX_PYTHON)
        self.SetKeyWords(0, " ".join(keyword.kwlist))

        self.SetProperty("fold", "1")
        self.SetProperty("tab.timmy.whinge.level", "1")
        self.SetMargins(0, 0)

        self.SetViewWhiteSpace(False)
        self.SetUseAntiAliasing(True)

        self.SetEdgeMode(stc.STC_EDGE_BACKGROUND)
        self.SetEdgeColumn(78)

        # Setup a margin to hold fold markers
        self.SetMarginType(2, stc.STC_MARGIN_SYMBOL)
        self.SetMarginMask(2, stc.STC_MASK_FOLDERS)
        self.SetMarginSensitive(2, True)
        self.SetMarginWidth(2, 12)

        # Import symbol style from config file
        for marker in self.fold_symbol_style:
            self.MarkerDefine(*marker)

        self.Bind(stc.EVT_STC_UPDATEUI, self.OnUpdateUI)
        self.Bind(stc.EVT_STC_MARGINCLICK, self.OnMarginClick)

        # Global default styles for all languages
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,
                          "face:%(helv)s,size:%(size)d" % self.faces)
        self.StyleClearAll()  # Reset all to be like the default

        # Import text style specs from config file
        for spec in self.text_styles:
            self.StyleSetSpec(*spec)

        self.SetCaretForeground("BLUE")

        self.SetMarginType(1, stc.STC_MARGIN_NUMBER)
        self.SetMarginWidth(1, 30)

    def _style(self):
        """Set editor style"""

        self.fold_symbols = 2

        """
        Fold symbols
        ------------

        The following styles are pre-defined:
          "arrows"      Arrow pointing right for contracted folders,
                        arrow pointing down for expanded
          "plusminus"   Plus for contracted folders, minus for expanded
          "circletree"  Like a flattened tree control using circular headers
                        and curved joins
          "squaretree"  Like a flattened tree control using square headers

        """

        self.faces = {
            'times': 'Times',
            'mono': 'Courier',
            'helv': wx.SystemSettings.GetFont(
                    wx.SYS_DEFAULT_GUI_FONT).GetFaceName(),
            'other': 'new century schoolbook',
            'size': 10,
            'size2': 8,
        }

        white = "white"
        gray = "#404040"

        # Fold circle tree symbol style from demo.py
        self.fold_symbol_style = [
            (stc.STC_MARKNUM_FOLDEROPEN,
             stc.STC_MARK_CIRCLEMINUS, white, gray),
            (stc.STC_MARKNUM_FOLDER,
             stc.STC_MARK_CIRCLEPLUS, white, gray),
            (stc.STC_MARKNUM_FOLDERSUB,
             stc.STC_MARK_VLINE, white, gray),
            (stc.STC_MARKNUM_FOLDERTAIL,
             stc.STC_MARK_LCORNERCURVE, white, gray),
            (stc.STC_MARKNUM_FOLDEREND,
             stc.STC_MARK_CIRCLEPLUSCONNECTED, white, gray),
            (stc.STC_MARKNUM_FOLDEROPENMID,
             stc.STC_MARK_CIRCLEMINUSCONNECTED, white, gray),
            (stc.STC_MARKNUM_FOLDERMIDTAIL,
             stc.STC_MARK_TCORNERCURVE, white, gray),
        ]

        """
        Text styles
        -----------

        The lexer defines what each style is used for, we just have to define
        what each style looks like.  The Python style set is adapted from
        Scintilla sample property files.

        """

        self.text_styles = [
            (stc.STC_STYLE_DEFAULT,
             "face:%(helv)s,size:%(size)d" % self.faces),
            (stc.STC_STYLE_LINENUMBER,
             "back:#C0C0C0,face:%(helv)s,size:%(size2)d" % self.faces),
            (stc.STC_STYLE_CONTROLCHAR,
             "face:%(other)s" % self.faces),
            (stc.STC_STYLE_BRACELIGHT,
             "fore:#FFFFFF,back:#0000FF,bold"),
            (stc.STC_STYLE_BRACEBAD,
             "fore:#000000,back:#FF0000,bold"),

            # Python styles
            # -------------

            # Default
            (stc.STC_P_DEFAULT,
             "fore:#000000,face:%(helv)s,size:%(size)d" % self.faces),

            # Comments
            (stc.STC_P_COMMENTLINE,
             "fore:#007F00,face:%(other)s,size:%(size)d" % self.faces),

            # Number
            (stc.STC_P_NUMBER,
             "fore:#007F7F,size:%(size)d" % self.faces),

            # String
            (stc.STC_P_STRING,
             "fore:#7F007F,face:%(helv)s,size:%(size)d" % self.faces),

            # Single quoted string
            (stc.STC_P_CHARACTER,
             "fore:#7F007F,face:%(helv)s,size:%(size)d" % self.faces),

            # Keyword
            (stc.STC_P_WORD,
             "fore:#00007F,bold,size:%(size)d" % self.faces),

            # Triple quotes
            (stc.STC_P_TRIPLE,
             "fore:#7F0000,size:%(size)d" % self.faces),

            # Triple double quotes
            (stc.STC_P_TRIPLEDOUBLE,
             "fore:#7F0000,size:%(size)d" % self.faces),

            # Class name definition
            (stc.STC_P_CLASSNAME,
             "fore:#0000FF,bold,underline,size:%(size)d" % self.faces),

            # Function or method name definition
            (stc.STC_P_DEFNAME,
             "fore:#007F7F,bold,size:%(size)d" % self.faces),

            # Operators
            (stc.STC_P_OPERATOR, "bold,size:%(size)d" % self.faces),

            # Identifiers
            (stc.STC_P_IDENTIFIER,
             "fore:#000000,face:%(helv)s,size:%(size)d" % self.faces),

            # Comment-blocks
            (stc.STC_P_COMMENTBLOCK,
             "fore:#7F7F7F,size:%(size)d" % self.faces),

            # End of line where string is not closed
            (stc.STC_P_STRINGEOL,
             "fore:#000000,face:%(mono)s,back:#E0C0E0,eol,size:%(size)d"
             % self.faces),
        ]

    def OnUpdateUI(self, evt):
        """Syntax highlighting while editing"""

        # check for matching braces
        brace_at_caret = -1
        brace_opposite = -1
        char_before = None
        caret_pos = self.GetCurrentPos()

        if caret_pos > 0:
            char_before = self.GetCharAt(caret_pos - 1)
            style_before = self.GetStyleAt(caret_pos - 1)

        # check before
        if char_before and chr(char_before) in "[]{}()" and \
           style_before == stc.STC_P_OPERATOR:
            brace_at_caret = caret_pos - 1

        # check after
        if brace_at_caret < 0:
            char_after = self.GetCharAt(caret_pos)
            style_after = self.GetStyleAt(caret_pos)

            if char_after and chr(char_after) in "[]{}()" and \
               style_after == stc.STC_P_OPERATOR:
                brace_at_caret = caret_pos

        if brace_at_caret >= 0:
            brace_opposite = self.BraceMatch(brace_at_caret)

        if brace_at_caret != -1 and brace_opposite == -1:
            self.BraceBadLight(brace_at_caret)
        else:
            self.BraceHighlight(brace_at_caret, brace_opposite)

    def OnMarginClick(self, evt):
        """When clicked, old and unfold as needed"""

        if evt.GetMargin() == 2:
            if evt.GetShift() and evt.GetControl():
                self.fold_all()
            else:
                line_clicked = self.LineFromPosition(evt.GetPosition())

                if self.GetFoldLevel(line_clicked) & \
                   stc.STC_FOLDLEVELHEADERFLAG:
                    if evt.GetShift():
                        self.SetFoldExpanded(line_clicked, True)
                        self.expand(line_clicked, True, True, 1)
                    elif evt.GetControl():
                        if self.GetFoldExpanded(line_clicked):
                            self.SetFoldExpanded(line_clicked, False)
                            self.expand(line_clicked, False, True, 0)
                        else:
                            self.SetFoldExpanded(line_clicked, True)
                            self.expand(line_clicked, True, True, 100)
                    else:
                        self.ToggleFold(line_clicked)

    def fold_all(self):
        """Folds/unfolds all levels in the editor"""

        line_count = self.GetLineCount()
        expanding = True

        # find out if we are folding or unfolding
        for line_num in range(line_count):
            if self.GetFoldLevel(line_num) & stc.STC_FOLDLEVELHEADERFLAG:
                expanding = not self.GetFoldExpanded(line_num)
                break

        line_num = 0

        while line_num < line_count:
            level = self.GetFoldLevel(line_num)
            if level & stc.STC_FOLDLEVELHEADERFLAG and \
               (level & stc.STC_FOLDLEVELNUMBERMASK) == stc.STC_FOLDLEVELBASE:

                if expanding:
                    self.SetFoldExpanded(line_num, True)
                    line_num = self.expand(line_num, True)
                    line_num = line_num - 1
                else:
                    last_child = self.GetLastChild(line_num, -1)
                    self.SetFoldExpanded(line_num, False)

                    if last_child > line_num:
                        self.HideLines(line_num + 1, last_child)

            line_num = line_num + 1

    def expand(self, line, do_expand, force=False, vislevels=0, level=-1):
        """Multi-purpose expand method from original STC class"""

        lastchild = self.GetLastChild(line, level)
        line += 1

        while line <= lastchild:
            if force:
                if vislevels > 0:
                    self.ShowLines(line, line)
                else:
                    self.HideLines(line, line)
            elif do_expand:
                self.ShowLines(line, line)

            if level == -1:
                level = self.GetFoldLevel(line)

            if level & stc.STC_FOLDLEVELHEADERFLAG:
                if force:
                    self.SetFoldExpanded(line, vislevels - 1)
                    line = self.expand(line, do_expand, force, vislevels - 1)

                else:
                    expandsub = do_expand and self.GetFoldExpanded(line)
                    line = self.expand(line, expandsub, force, vislevels - 1)
            else:
                line += 1

        return line

# end of class PythonSTC


class ImageComboBox(wx.combo.OwnerDrawnComboBox):
    """Base class for image combo boxes

    The class provides alternating backgrounds. Stolen from demo.py

    """

    def OnDrawBackground(self, dc, rect, item, flags):
        """Called for drawing the background area of each item

        Overridden from OwnerDrawnComboBox

        """

        # If the item is selected, or its item is even,
        # or if we are painting the combo control itself
        # then use the default rendering.

        if (item & 1 == 0 or flags & (wx.combo.ODCB_PAINTING_CONTROL |
                                      wx.combo.ODCB_PAINTING_SELECTED)):
            try:
                wx.combo.OwnerDrawnComboBox.OnDrawBackground(self, dc,
                                                             rect, item, flags)
            finally:
                return

        # Otherwise, draw every other background with
        # different color.

        bg_color = wx.Colour(240, 240, 250)
        dc.SetBrush(wx.Brush(bg_color))
        dc.SetPen(wx.Pen(bg_color))
        dc.DrawRectangleRect(rect)


class PenWidthComboBox(ImageComboBox):
    """Combo box for choosing line width for cell borders"""

    def OnDrawItem(self, dc, rect, item, flags):

        if item == wx.NOT_FOUND:
            return

        r = wx.Rect(*rect)  # make a copy
        r.Deflate(3, 5)

        pen_style = wx.SOLID
        if item == 0:
            pen_style = wx.TRANSPARENT
        pen = wx.Pen(dc.GetTextForeground(), item, pen_style)
        pen.SetCap(wx.CAP_BUTT)

        dc.SetPen(pen)

        # Draw the example line in the combobox
        dc.DrawLine(r.x + 5, r.y + r.height / 2,
                    r.x + r.width - 5, r.y + r.height / 2)

# end of class PenWidthComboBox

# Chart dialog widgets for matplotlib interaction
# -----------------------------------------------


class MatplotlibStyleChoice(wx.Choice):
    """Base class for line and marker choice for matplotlib charts"""

    # Style label and code are stored in styles as a list of tuples
    styles = []

    def __init__(self, *args, **kwargs):
        kwargs["choices"] = [style[0] for style in self.styles]
        wx.Choice.__init__(self, *args, **kwargs)

    def get_style_code(self, label):
        """Returns code for given label string

        Inverse of get_code

        Parameters
        ----------
        label: String
        \tLlabel string, field 0 of style tuple

        """

        for style in self.styles:
            if style[0] == label:
                return style[1]

        msg = _("Label {label} is invalid.").format(label=label)
        raise ValueError(msg)

    def get_label(self, code):
        """Returns string label for given code string

        Inverse of get_code

        Parameters
        ----------
        code: String
        \tCode string, field 1 of style tuple

        """

        for style in self.styles:
            if style[1] == code:
                return style[0]

        msg = _("Code {code} is invalid.").format(code=code)
        raise ValueError(msg)


class LineStyleComboBox(MatplotlibStyleChoice):
    """Combo box for choosing line style for matplotlib charts"""

    styles = [
        ("Solid line style", "-"),
        ("Dashed line style", "--"),
        ("Dash-dot line style", "-."),
        ("Dotted line style", ":"),
    ]


class MarkerStyleComboBox(MatplotlibStyleChoice):
    """Choice box for choosing matplotlib chart markers"""

    styles = [
        ("No marker", ""),
        ("Point marker", "."),
        ("Pixel marker", ","),
        ("Circle marker", "o"),
        ("Triangle_down marker", "v"),
        ("Triangle_up marker", "^"),
        ("Triangle_left marker", "<"),
        ("Triangle_right marker", ">"),
        ("Tri_down marker", "1"),
        ("Tri_up marker", "2"),
        ("Tri_left marker", "3"),
        ("Tri_right marker", "4"),
        ("Square marker", "s"),
        ("Pentagon marker", "p"),
        ("Star marker", "*"),
        ("Hexagon1 marker", "h"),
        ("hexagon2 marker", "H"),
        ("Plus marker", "+"),
        ("X marker", "x"),
        ("Diamond marker", "D"),
        ("Thin_diamond marker", "d"),
        ("Vline marker", "|"),
        ("Hline marker", "_"),
    ]


class CoordinatesComboBox(MatplotlibStyleChoice):
    """Combo box for choosing annotation coordinates for matplotlib charts"""

    styles = [
        ("Figure points", "figure points"),
        ("Figure pixels", "figure pixels"),
        ("Figure fraction", "figure fraction"),
        ("Axes points", "axes points"),
        ("Axes pixels", "axes pixels"),
        ("Axes fraction", "axes fraction"),
        ("Data", "data"),
        ("Offset points", "offset points"),
        ("Polar", "polar"),
    ]


# End of chart dialog widgets for matplotlib interaction
# ------------------------------------------------------


class FontChoiceCombobox(ImageComboBox):
    """Combo box for choosing fonts"""

    def OnDrawItem(self, dc, rect, item, flags):

        if item == wx.NOT_FOUND:
            return

        __rect = wx.Rect(*rect)  # make a copy
        __rect.Deflate(3, 5)

        font_string = self.GetString(item)

        font = get_default_font()
        font.SetFaceName(font_string)
        font.SetFamily(wx.FONTFAMILY_SWISS)
        dc.SetFont(font)

        text_width, text_height = dc.GetTextExtent(font_string)
        text_x = __rect.x
        text_y = __rect.y + int((__rect.height - text_height) / 2.0)

        # Draw the example text in the combobox
        dc.DrawText(font_string, text_x, text_y)

# end of class FontChoiceCombobox


class BorderEditChoice(ImageComboBox):
    """Combo box for selecting the cell borders that shall be changed"""

    def OnDrawItem(self, dc, rect, item, flags):

        if item == wx.NOT_FOUND:
            return

        r = wx.Rect(*rect)  # make a copy
        item_name = self.GetItems()[item]

        bmp = icons[item_name]

        icon = wx.EmptyIcon()
        icon.CopyFromBitmap(bmp)

        # Draw the border icon in the combobox
        dc.DrawIcon(icon, r.x, r.y)

    def OnMeasureItem(self, item):
        """Returns the height of the items in the popup"""

        item_name = self.GetItems()[item]
        return icons[item_name].GetHeight()

    def OnMeasureItemWidth(self, item):
        """Returns the height of the items in the popup"""

        item_name = self.GetItems()[item]
        return icons[item_name].GetWidth()

# end of class BorderEditChoice


class BitmapToggleButton(wx.BitmapButton):
    """Toggle button that goes through a list of bitmaps

    Parameters
    ----------
    bitmap_list: List of wx.Bitmap
    \tMust be non-empty

    """

    def __init__(self, parent, bitmap_list):

        assert len(bitmap_list) > 0

        self.bitmap_list = []
        for bmp in bitmap_list:
            if '__WXMSW__' not in wx.PlatformInfo:
                # Setting a mask fails on Windows.
                # Therefore transparency is set only for other platforms
                mask = wx.Mask(bmp, wx.BLUE)
                bmp.SetMask(mask)

            self.bitmap_list.append(bmp)

        self.state = 0

        super(BitmapToggleButton, self).__init__(
            parent, -1, self.bitmap_list[0], style=wx.BORDER_NONE)

        # For compatibility with toggle buttons
        setattr(self, "GetToolState", lambda x: self.state)

        self.Bind(wx.EVT_LEFT_UP, self.toggle, self)

    def toggle(self, event):
        """Toggles state to next bitmap"""

        if self.state < len(self.bitmap_list) - 1:
            self.state += 1
        else:
            self.state = 0

        self.SetBitmapLabel(self.bitmap_list[self.state])

        try:
            event.Skip()
        except AttributeError:
            pass

        """For compatibility with toggle buttons"""
        setattr(self, "GetToolState", lambda x: self.state)

# end of class BitmapToggleButton


class EntryLineToolbarPanel(wx.Panel):
    """Panel that contains an EntryLinePanel and a TableChoiceIntCtrl"""

    def __init__(self, parent, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)

        # Panel with EntryLine and button
        self.entry_line_panel = EntryLinePanel(self, parent, -1)

        # IntCtrl for table choice
        self.table_choice = TableChoiceIntCtrl(self, parent,
                                               config["grid_tables"])

        self.__do_layout()

    def __do_layout(self):
        main_sizer = wx.FlexGridSizer(1, 2, 0, 0)

        main_sizer.Add(self.entry_line_panel, 1, wx.ALL | wx.EXPAND, 1)
        main_sizer.Add(self.table_choice, 1, wx.ALL | wx.EXPAND, 1)

        main_sizer.AddGrowableRow(0)
        main_sizer.AddGrowableCol(0)

        self.SetSizer(main_sizer)

        self.Layout()

# end of class EntryLineToolbarPanel


class EntryLinePanel(wx.Panel, GridEventMixin, GridActionEventMixin):
    """Panel that contains an EntryLine and a bitmap toggle button

    The button changes the state of the grid. If pressed, a grid selection
    is inserted into the EntryLine.

    """

    def __init__(self, parent, main_window, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.main_window = main_window

        style = wx.TE_PROCESS_ENTER | wx.TE_MULTILINE
        self.entry_line = EntryLine(self, main_window, style=style)
        self.selection_toggle_button = \
            wx.ToggleButton(self, -1, size=(24, -1), label=u"\u25F0")

        tooltip = wx.ToolTip(_("Toggles link insertion mode."))
        self.selection_toggle_button.SetToolTip(tooltip)
        self.selection_toggle_button.Bind(wx.EVT_TOGGLEBUTTON, self.OnToggle)

        if not is_gtk():
            # TODO: Selections still do not work right on Windows
            self.selection_toggle_button.Disable()

        self.__do_layout()

    def __do_layout(self):
        main_sizer = wx.FlexGridSizer(1, 2, 0, 0)

        main_sizer.Add(self.entry_line, 1, wx.ALL | wx.EXPAND, 1)
        main_sizer.Add(self.selection_toggle_button, 1, wx.ALL | wx.EXPAND, 1)

        main_sizer.AddGrowableRow(0)
        main_sizer.AddGrowableCol(0)

        self.SetSizer(main_sizer)

        self.Layout()

    def OnToggle(self, event):
        """Toggle button event handler"""

        if self.selection_toggle_button.GetValue():
            self.entry_line.last_selection = self.entry_line.GetSelection()
            self.entry_line.last_selection_string = \
                self.entry_line.GetStringSelection()
            self.entry_line.last_table = self.main_window.grid.current_table
            self.entry_line.Disable()
            post_command_event(self, self.EnterSelectionModeMsg)

        else:
            self.entry_line.Enable()
            post_command_event(self, self.GridActionTableSwitchMsg,
                               newtable=self.entry_line.last_table)
            post_command_event(self, self.ExitSelectionModeMsg)

# end of class EntryLinePanel


class EntryLine(wx.TextCtrl, EntryLineEventMixin, GridCellEventMixin,
                GridEventMixin, GridActionEventMixin):
    """"The line for entering cell code"""

    def __init__(self, parent, main_window, id=-1, *args, **kwargs):
        kwargs["style"] = wx.TE_PROCESS_ENTER | wx.TE_MULTILINE
        wx.TextCtrl.__init__(self, parent, id, *args, **kwargs)

        self.SetSize((700, 25))

        self.parent = parent
        self.main_window = main_window
        self.ignore_changes = False

        # Store last text selection of self before going into selection mode
        self.last_selection = None
        self.last_selection_string = None
        # The current table has to be stored on entering selection mode
        self.last_table = None

        main_window.Bind(self.EVT_ENTRYLINE_MSG, self.OnContentChange)
        main_window.Bind(self.EVT_CMD_SELECTION, self.OnGridSelection)
        main_window.Bind(self.EVT_ENTRYLINE_LOCK, self.OnLock)

        self.SetToolTip(wx.ToolTip(_("Enter Python expression here.")))

        self.Bind(wx.EVT_TEXT, self.OnText)
        self.Bind(wx.EVT_CHAR, self.OnChar)
        self.main_window.Bind(self.EVT_CMD_TABLE_CHANGED, self.OnTableChanged)

    def OnContentChange(self, event):
        """Event handler for updating the content"""

        if event.text is None:
            self.SetValue(u"")
        else:
            self.SetValue(event.text)

        event.Skip()

    def OnGridSelection(self, event):
        """Event handler for grid selection in selection mode adds text"""

        current_table = copy(self.main_window.grid.current_table)

        post_command_event(self, self.GridActionTableSwitchMsg,
                           newtable=self.last_table)
        if is_gtk():
                wx.Yield()
        sel_start, sel_stop = self.last_selection

        shape = self.main_window.grid.code_array.shape
        selection_string = event.selection.get_access_string(shape,
                                                             current_table)

        self.Replace(sel_start, sel_stop, selection_string)
        self.last_selection = sel_start, sel_start + len(selection_string)

        post_command_event(self, self.GridActionTableSwitchMsg,
                           newtable=current_table)

    def OnLock(self, event):
        """Event handler for locking the entry line"""

        self.Enable(not event.lock)

    def OnText(self, event):
        """Text event method evals the cell and updates the grid"""

        if not self.ignore_changes:
            post_command_event(self, self.CodeEntryMsg, code=event.GetString())

        event.Skip()

    def OnChar(self, event):
        """Key event method

         * Forces grid update on <Enter> key
         * Handles insertion of cell access code

        """

        if not self.ignore_changes:

            # Handle special keys
            keycode = event.GetKeyCode()

            if keycode == 13:
                # <Enter> pressed --> Focus on grid
                self.main_window.grid.SetFocus()

                # Ignore <Ctrl> + <Enter> and Quote content
                if event.ControlDown():
                    self.SetValue('"' + self.GetValue() + '"')

                return

        event.Skip()

    def OnTableChanged(self, event):
        """Table changed event handler"""

        if hasattr(event, 'updated_cell'):
            # Event posted by cell edit widget.  Even more up to date
            #  than the current cell's contents
            try:
                self.SetValue(event.updated_cell)

            except TypeError:
                # None instead of string present
                pass

        else:
            current_cell = self.main_window.grid.actions.cursor
            current_cell_code = self.main_window.grid.code_array(current_cell)

            if current_cell_code is None:
                self.SetValue(u"")
            else:
                self.SetValue(current_cell_code)

        event.Skip()

# end of class EntryLine


class StatusBar(wx.StatusBar, StatusBarEventMixin, MainWindowEventMixin):
    """Main window statusbar"""

    def __init__(self, parent):
        wx.StatusBar.__init__(self, parent, -1)

        self.SetFieldsCount(2)

        self.size_changed = False

        safemode_bmp = icons["safe_mode"]

        self.safemode_staticbmp = wx.StaticBitmap(self, 1001, safemode_bmp)
        tooltip = wx.ToolTip(
            _("Pyspread is in safe mode.\nExpressions are not evaluated."))
        self.safemode_staticbmp.SetToolTip(tooltip)

        self.SetStatusWidths([-1, safemode_bmp.GetWidth() + 4])

        self.safemode_staticbmp.Hide()

        parent.Bind(self.EVT_STATUSBAR_MSG, self.OnMessage)
        parent.Bind(self.EVT_CMD_SAFE_MODE_ENTRY, self.OnSafeModeEntry)
        parent.Bind(self.EVT_CMD_SAFE_MODE_EXIT, self.OnSafeModeExit)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_IDLE, self.OnIdle)

    def OnMessage(self, event):
        """Statusbar message event handler"""

        self.SetStatusText(event.text)

    def OnSize(self, evt):
        self.Reposition()  # for normal size events

        # Set a flag so the idle time handler will also do the repositioning.
        # It is done this way to get around a buglet where GetFieldRect is not
        # accurate during the EVT_SIZE resulting from a frame maximize.
        self.size_changed = True

    def OnIdle(self, event):
        if self.size_changed:
            self.Reposition()

    def Reposition(self):
        """Reposition the checkbox"""

        rect = self.GetFieldRect(1)
        self.safemode_staticbmp.SetPosition((rect.x, rect.y))
        self.size_changed = False

    def OnSafeModeEntry(self, event):
        """Safe mode entry event handler"""

        self.safemode_staticbmp.Show(True)

        event.Skip()

    def OnSafeModeExit(self, event):
        """Safe mode exit event handler"""

        self.safemode_staticbmp.Hide()

        event.Skip()

# end of class StatusBar


class TableChoiceIntCtrl(IntCtrl, GridEventMixin, GridActionEventMixin):
    """ComboBox for choosing the current grid table"""

    def __init__(self, parent, main_window, no_tabs):
        self.parent = parent
        self.main_window = main_window
        self.no_tabs = no_tabs

        IntCtrl.__init__(self, parent, limited=True, allow_long=True)

        self.SetMin(0)
        self.SetMax(no_tabs - 1)

        tipmsg = _("For switching tables enter the table number or "
                   "use the mouse wheel.")
        self.SetToolTip(wx.ToolTip(tipmsg))

        # State for preventing to post GridActionTableSwitchMsg
        self.switching = False

        self.Bind(EVT_INT, self.OnInt)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.main_window.Bind(self.EVT_CMD_RESIZE_GRID, self.OnResizeGrid)
        self.main_window.Bind(self.EVT_CMD_TABLE_CHANGED, self.OnTableChanged)

    def change_max(self, no_tabs):
        """Updates to a new number of tables

        Fixes current table if out of bounds.

        Parameters
        ----------
        no_tabs: Integer
        \tNumber of tables for choice

        """

        self.no_tabs = no_tabs

        if self.GetValue() >= no_tabs:
            self.SetValue(no_tabs - 1)

        self.SetMax(no_tabs - 1)

    # Event handlers

    def OnResizeGrid(self, event):
        """Event handler for grid resizing"""

        self.change_max(event.shape[2])

    def OnInt(self, event):
        """IntCtrl event method that updates the current table"""

        self.SetMax(self.no_tabs - 1)
        if event.GetValue() > self.GetMax():
            self.SetValue(self.GetMax())
            return

        if not self.switching:
            self.switching = True
            post_command_event(self, self.GridActionTableSwitchMsg,
                               newtable=event.GetValue())
            if is_gtk():
                wx.Yield()
            self.switching = False

    def OnMouseWheel(self, event):
        """Mouse wheel event handler"""

        # Prevent lost IntCtrl changes
        if self.switching:
            return

        self.SetMax(self.no_tabs - 1)

        if event.GetWheelRotation() > 0:
            new_table = self.GetValue() + 1
        else:
            new_table = self.GetValue() - 1

        if self.IsInBounds(new_table):
            self.SetValue(new_table)

    def OnShapeChange(self, event):
        """Grid shape change event handler"""

        self.change_max(event.shape[2])

        event.Skip()

    def OnTableChanged(self, event):
        """Table changed event handler"""

        if hasattr(event, 'table'):
            self.SetValue(event.table)

        event.Skip()

# end of class TableChoiceIntCtrl
########NEW FILE########
__FILENAME__ = pys
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""

pys
===

This file contains interfaces to the native pys file format.

It is split into the following sections

 * shape
 * code
 * attributes
 * row_heights
 * col_widths
 * macros

"""

import ast
from collections import OrderedDict
import src.lib.i18n as i18n
from itertools import imap

from src.lib.selection import Selection

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


class Pys(object):
    """Interface between code_array and pys file

    The pys file is read from disk with the read method.
    The pys file is written to disk with the write method.

    Parameters
    ----------

    code_array: model.CodeArray object
    \tThe code_array object data structure
    pys_file: file
    \tFile like object in pys format

    """

    def __init__(self, code_array, pys_file):
        self.code_array = code_array
        self.pys_file = pys_file

        self._section2reader = {
            "[Pyspread save file version]\n": self._pys_assert_version,
            "[shape]\n": self._pys2shape,
            "[grid]\n": self._pys2code,
            "[attributes]\n": self._pys2attributes,
            "[row_heights]\n": self._pys2row_heights,
            "[col_widths]\n": self._pys2col_widths,
            "[macros]\n": self._pys2macros,
        }

        self._section2writer = OrderedDict([
            ("[Pyspread save file version]\n", self._version2pys),
            ("[shape]\n", self._shape2pys),
            ("[grid]\n", self._code2pys),
            ("[attributes]\n", self._attributes2pys),
            ("[row_heights]\n", self._row_heights2pys),
            ("[col_widths]\n", self._col_widths2pys),
            ("[macros]\n", self._macros2pys),
        ])

    def _split_tidy(self, string, maxsplit=None):
        """Rstrips string for \n and splits string for \t"""

        if maxsplit is None:
            return string.rstrip("\n").split("\t")
        else:
            return string.rstrip("\n").split("\t", maxsplit)

    def _get_key(self, *keystrings):
        """Returns int key tuple from key string list"""

        return tuple(imap(int, keystrings))

    def _pys_assert_version(self, line):
        """Asserts pys file version"""

        if line != "0.1\n":
            # Abort if file version not supported
            msg = _("File version {version} unsupported (not 0.1).").format(
                version=line.strip())
            raise ValueError(msg)

    def _version2pys(self):
        """Writes pys file version to pys file

        Format: <version>\n

        """

        self.pys_file.write("0.1\n")

    def _shape2pys(self):
        """Writes shape to pys file

        Format: <rows>\t<cols>\t<tabs>\n

        """

        shape_line = u"\t".join(map(unicode, self.code_array.shape)) + u"\n"
        self.pys_file.write(shape_line)

    def _pys2shape(self, line):
        """Updates shape in code_array"""

        self.code_array.shape = self._get_key(*self._split_tidy(line))

    def _code2pys(self):
        """Writes code to pys file

        Format: <row>\t<col>\t<tab>\t<code>\n

        """

        for key in self.code_array:
            key_str = u"\t".join(repr(ele) for ele in key)
            code_str = self.code_array(key)
            out_str = key_str + u"\t" + code_str + u"\n"

            self.pys_file.write(out_str.encode("utf-8"))

    def _pys2code(self, line):
        """Updates code in pys code_array"""

        row, col, tab, code = self._split_tidy(line, maxsplit=3)
        key = self._get_key(row, col, tab)

        self.code_array.dict_grid[key] = unicode(code, encoding='utf-8')

    def _attributes2pys(self):
        """Writes attributes to pys file

        Format:
        <selection[0]>\t[...]\t<tab>\t<key>\t<value>\t[...]\n

        """

        for selection, tab, attr_dict in self.code_array.cell_attributes:
            sel_list = [selection.block_tl, selection.block_br,
                        selection.rows, selection.cols, selection.cells]

            tab_list = [tab]

            attr_dict_list = []
            for key in attr_dict:
                attr_dict_list.append(key)
                attr_dict_list.append(attr_dict[key])

            line_list = map(repr, sel_list + tab_list + attr_dict_list)

            self.pys_file.write(u"\t".join(line_list) + u"\n")

    def _pys2attributes(self, line):
        """Updates attributes in code_array"""

        splitline = self._split_tidy(line)

        selection_data = map(ast.literal_eval, splitline[:5])
        selection = Selection(*selection_data)

        tab = int(splitline[5])

        attrs = {}
        for col, ele in enumerate(splitline[6:]):
            if not (col % 2):
                # Odd entries are keys
                key = ast.literal_eval(ele)

            else:
                # Even cols are values
                attrs[key] = ast.literal_eval(ele)

        self.code_array.cell_attributes.append((selection, tab, attrs))

    def _row_heights2pys(self):
        """Writes row_heights to pys file

        Format: <row>\t<tab>\t<value>\n

        """

        for row, tab in self.code_array.dict_grid.row_heights:
            height = self.code_array.dict_grid.row_heights[(row, tab)]
            height_strings = map(repr, [row, tab, height])
            self.pys_file.write(u"\t".join(height_strings) + u"\n")

    def _pys2row_heights(self, line):
        """Updates row_heights in code_array"""

        # Split with maxsplit 3
        row, tab, height = self._split_tidy(line)
        key = self._get_key(row, tab)

        try:
            self.code_array.row_heights[key] = float(height)

        except ValueError:
            pass

    def _col_widths2pys(self):
        """Writes col_widths to pys file

        Format: <col>\t<tab>\t<value>\n

        """

        for col, tab in self.code_array.dict_grid.col_widths:
            width = self.code_array.dict_grid.col_widths[(col, tab)]
            width_strings = map(repr, [col, tab, width])
            self.pys_file.write(u"\t".join(width_strings) + u"\n")

    def _pys2col_widths(self, line):
        """Updates col_widths in code_array"""

        # Split with maxsplit 3
        col, tab, width = self._split_tidy(line)
        key = self._get_key(col, tab)

        try:
            self.code_array.col_widths[key] = float(width)

        except ValueError:
            pass

    def _macros2pys(self):
        """Writes macros to pys file

        Format: <macro code line>\n

        """

        macros = self.code_array.dict_grid.macros
        pys_macros = macros.encode("utf-8")
        self.pys_file.write(pys_macros)

    def _pys2macros(self, line):
        """Updates macros in code_array"""

        if self.code_array.dict_grid.macros and \
           self.code_array.dict_grid.macros[-1] != "\n":
            # The last macro line does not end with \n
            # Therefore, if not new line is inserted, the codeis broken
            self.code_array.dict_grid.macros += "\n"

        self.code_array.dict_grid.macros += line.decode("utf-8")

    # Access via model.py data
    # ------------------------

    def from_code_array(self):
        """Replaces everything in pys_file from code_array"""

        for key in self._section2writer:
            self.pys_file.write(key)
            self._section2writer[key]()

            try:
                if self.pys_file.aborted:
                    break
            except AttributeError:
                # pys_fileis not opened via fileio.BZAopen
                pass

    def to_code_array(self):
        """Replaces everything in code_array from pys_file"""

        state = None

        # Check if version section starts with first line
        first_line = True

        # Reset pys_file to start to enable multiple calls of this method
        self.pys_file.seek(0)

        for line in self.pys_file:
            if first_line:
                # If Version section does not start with first line then
                # the file is invalid.
                if line == "[Pyspread save file version]\n":
                    first_line = False
                else:
                    raise ValueError(_("File format unsupported."))

            if line in self._section2reader:
                state = line

            elif state is not None:
                self._section2reader[state](line)

########NEW FILE########
__FILENAME__ = test_pys
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
test_pys
========

Unit tests for pys.py

"""

import bz2
import os
import sys

from src.interfaces.pys import Pys
from src.lib.selection import Selection
from src.lib.testlib import params, pytest_generate_tests
from src.model.model import CodeArray

TESTPATH = os.sep.join(os.path.realpath(__file__).split(os.sep)[:-1]) + os.sep
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 3)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 2)


class TestPys(object):
    """Unit tests for Pys"""

    def setup_method(self, method):
        """Creates Pys class with code_array and temporary test.pys file"""

        # All data structures are initially empty
        # The test file pys_file has entries in each category

        self.code_array = CodeArray((1000, 100, 3))
        self.pys_infile = bz2.BZ2File(TESTPATH + "pys_test1.pys")
        self.pys_outfile_path = TESTPATH + "pys_test2.pys"
        self.pys_in = Pys(self.code_array, self.pys_infile)

    def write_pys_out(self, method_name, *args, **kwargs):
        """Helper that writes an pys_out file"""

        outfile = bz2.BZ2File(self.pys_outfile_path, "w")
        pys_out = Pys(self.code_array, outfile)
        method = getattr(pys_out, method_name)
        method(*args, **kwargs)
        outfile.close()

    def read_pys_out(self):
        """Returns string of pys_out content and removes pys_out"""

        outfile = bz2.BZ2File(self.pys_outfile_path)
        res = outfile.read()
        outfile.close()

        # Clean up the test dir
        os.remove(self.pys_outfile_path)

        return res

    param_split_tidy = [
        {'string': "1", 'maxsplit': None, 'res': ["1"]},
        {'string': "1\t2", 'maxsplit': None, 'res': ["1", "2"]},
        {'string': "1\t2\n", 'maxsplit': None, 'res': ["1", "2"]},
        {'string': "1\t2\t3", 'maxsplit': 1, 'res': ["1", "2\t3"]},
        {'string': "1\t2\t3\n", 'maxsplit': 1, 'res': ["1", "2\t3"]},
    ]

    @params(param_split_tidy)
    def test_split_tidy(self, string, maxsplit, res):
        """Test _split_tidy method"""

        assert self.pys_in._split_tidy(string, maxsplit) == res

    param_get_key = [
        {'keystrings': ["1", "2", "3"], 'res': (1, 2, 3)},
        {'keystrings': ["0", "0", "0"], 'res': (0, 0, 0)},
        {'keystrings': ["0", "0"], 'res': (0, 0)},
        {'keystrings': ["-2", "-2", "23"], 'res': (-2, -2, 23)},
        {'keystrings': map(str, xrange(100)), 'res': tuple(xrange(100))},
        {'keystrings': map(unicode, xrange(100)), 'res': tuple(xrange(100))},
    ]

    @params(param_get_key)
    def test_get_key(self, keystrings, res):
        """Test _get_key method"""

        assert self.pys_in._get_key(*keystrings) == res

    param_pys_assert_version = [
        {'line': "\n", 'res': False},
        {'line': "0.1\n", 'res': True},
        {'line': "0.2\n", 'res': False},
    ]

    @params(param_pys_assert_version)
    def test_pys_assert_version(self, line, res):
        """Test _pys_assert_version method"""

        try:
            self.pys_in._pys_assert_version(line)
            assert res

        except ValueError:
            assert not res

    def test_version2pys(self):
        """Test _version2pys method"""

        self.write_pys_out("_version2pys")
        assert self.read_pys_out() == "0.1\n"

    param_shape2pys = [
        {'shape': (1000, 100, 3), 'res': "1000\t100\t3\n"},
        {'shape': (1, 1, 1), 'res': "1\t1\t1\n"},
        {'shape': (1000000, 1000000, 2), 'res': "1000000\t1000000\t2\n"},
    ]

    @params(param_shape2pys)
    def test_shape2pys(self, shape, res):
        """Test _shape2pys method"""

        self.code_array.dict_grid.shape = shape
        self.write_pys_out("_shape2pys")
        assert self.read_pys_out() == res

    @params(param_shape2pys)
    def test_pys2shape(self, res, shape):
        """Test _pys2shape method"""

        self.pys_in._pys2shape(res)
        assert self.code_array.dict_grid.shape == shape

    param_code2pys = [
        {'code': "0\t0\t0\tTest\n", 'key': (0, 0, 0), 'val': "Test"},
        {'code': "10\t0\t0\t" + u"öäüß".encode("utf-8") + "\n",
         'key': (10, 0, 0), 'val': u"öäüß"},
        {'code': "2\t0\t0\tTest\n", 'key': (2, 0, 0), 'val': "Test"},
        {'code': "2\t0\t0\t" + "a" * 100 + '\n', 'key': (2, 0, 0),
         'val': "a" * 100},
        {'code': '0\t0\t0\t"Test"\n', 'key': (0, 0, 0), 'val': '"Test"'},
    ]

    @params(param_code2pys)
    def test_code2pys(self, key, val, code):
        """Test _code2pys method"""

        self.code_array[key] = val
        self.write_pys_out("_code2pys")
        res = self.read_pys_out()

        assert res == code

    @params(param_code2pys)
    def test_pys2code(self, val, code, key):
        """Test _pys2code method"""

        self.pys_in._pys2code(code)
        assert self.code_array(key) == val

    param_attributes2pys = [
        {'code': "[]\t[]\t[]\t[]\t[(3, 4)]\t0\t'borderwidth_bottom'\t42\n",
         'selection': Selection([], [], [], [], [(3, 4)]), 'table': 0,
         'key': (3, 4, 0), 'attr': 'borderwidth_bottom', 'val': 42},
    ]

    @params(param_attributes2pys)
    def test_attributes2pys(self, selection, table, key, attr, val, code):
        """Test _attributes2pys method"""

        self.code_array.dict_grid.cell_attributes.undoable_append(
            (selection, table, {attr: val}), mark_unredo=False)

        self.write_pys_out("_attributes2pys")
        assert self.read_pys_out() == code

    @params(param_attributes2pys)
    def test_pys2attributes(self, selection, table, key, attr, val, code):
        """Test _pys2attributes method"""

        self.pys_in._pys2attributes(code)

        attrs = self.code_array.dict_grid.cell_attributes[key]
        assert attrs[attr] == val

    param_row_heights2pys = [
        {'row': 0, 'tab': 0, 'height': 0.1, 'code': "0\t0\t0.1\n"},
        {'row': 0, 'tab': 0, 'height': 0.0, 'code': "0\t0\t0.0\n"},
        {'row': 10, 'tab': 0, 'height': 1.0, 'code': "10\t0\t1.0\n"},
        {'row': 10, 'tab': 10, 'height': 1.0, 'code': "10\t10\t1.0\n"},
        {'row': 10, 'tab': 10, 'height': 100.0, 'code': "10\t10\t100.0\n"},
    ]

    @params(param_row_heights2pys)
    def test_row_heights2pys(self, row, tab, height, code):
        """Test _row_heights2pys method"""

        self.code_array.dict_grid.row_heights[(row, tab)] = height
        self.write_pys_out("_row_heights2pys")
        assert self.read_pys_out() == code

    @params(param_row_heights2pys)
    def test_pys2row_heights(self, row, tab, height, code):
        """Test _pys2row_heights method"""

        self.pys_in._pys2row_heights(code)
        assert self.code_array.dict_grid.row_heights[(row, tab)] == height

    param_col_widths2pys = [
        {'col': 0, 'tab': 0, 'width': 0.1, 'code': "0\t0\t0.1\n"},
        {'col': 0, 'tab': 0, 'width': 0.0, 'code': "0\t0\t0.0\n"},
        {'col': 10, 'tab': 0, 'width': 1.0, 'code': "10\t0\t1.0\n"},
        {'col': 10, 'tab': 10, 'width': 1.0, 'code': "10\t10\t1.0\n"},
        {'col': 10, 'tab': 10, 'width': 100.0, 'code': "10\t10\t100.0\n"},
    ]

    @params(param_col_widths2pys)
    def test_col_widths2pys(self, col, tab, width, code):
        """Test _col_widths2pys method"""

        self.code_array.dict_grid.col_widths[(col, tab)] = width
        self.write_pys_out("_col_widths2pys")
        assert self.read_pys_out() == code

    @params(param_col_widths2pys)
    def test_pys2col_widths(self, col, tab, width, code):
        """Test _pys2col_widths method"""

        self.pys_in._pys2col_widths(code)
        assert self.code_array.dict_grid.col_widths[(col, tab)] == width

    param_macros2pys = [
        {'code': u"Test"},
        {'code': u""},
        {'code': u"Test1\nTest2"},
        {'code': u"öäüß"},
    ]

    @params(param_macros2pys)
    def test_macros2pys(self, code):
        """Test _macros2pys method"""

        self.code_array.dict_grid.macros = code
        self.write_pys_out("_macros2pys")
        res = self.read_pys_out().decode("utf-8")
        assert res == code

    @params(param_macros2pys)
    def test_pys2macros(self, code):
        """Test _pys2macros method"""

        self.pys_in._pys2macros(code.encode("utf-8"))
        assert self.code_array.dict_grid.macros == code

    def test_from_code_array(self):
        """Test from_code_array method"""

        self.pys_infile.seek(0)
        self.pys_in.to_code_array()

        outfile = bz2.BZ2File(self.pys_outfile_path, "w")
        pys_out = Pys(self.code_array, outfile)
        pys_out.from_code_array()
        outfile.close()

        self.pys_infile.seek(0)
        in_data = self.pys_infile.read()

        outfile = bz2.BZ2File(self.pys_outfile_path)
        out_data = outfile.read()
        outfile.close()

        # Clean up the test dir
        os.remove(self.pys_outfile_path)

        assert in_data == out_data

    def test_to_code_array(self):
        """Test to_code_array method"""

        self.pys_in.to_code_array()

        assert self.code_array((0, 0, 0)) == '"Hallo"'

########NEW FILE########
__FILENAME__ = xls
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# xlspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# xlspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with xlspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""

xls
===

This file contains interfaces to Excel xls file format.

"""

from copy import copy
from datetime import datetime
from itertools import product

try:
    import xlrd

except ImportError:
    xlrd = None

try:
    import xlwt

except ImportError:
    xlwt = None

import wx

import src.lib.i18n as i18n

from src.lib.selection import Selection

from src.sysvars import get_dpi, get_default_text_extent


#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


class Xls(object):
    """Interface between code_array and xls file

    The xls file is read from disk with the read method.
    The xls file is written to disk with the write method.

    Parameters
    ----------

    code_array: model.CodeArray object
    \tThe code_array object data structure
    workbook: xlrd Workbook object
    \tFile like object in xls format

    """

    def __init__(self, code_array, workbook):
        self.code_array = code_array
        self.workbook = workbook

        self.xls_max_rows = 65536
        self.xls_max_cols = 256
        self.xls_max_tabs = 256  # Limit tables to 255 to avoid cluttered Excel

    def idx2colour(self, idx):
        """Returns wx.Colour"""

        return wx.Colour(*self.workbook.colour_map[idx])

    def color2idx(self, red, green, blue):
        """Get an Excel index from"""

        xlwt_colors = [
            (0, 0, 0), (255, 255, 255), (255, 0, 0), (0, 255, 0), (0, 0, 255),
            (255, 255, 0), (255, 0, 255), (0, 255, 255), (0, 0, 0),
            (255, 255, 255), (255, 0, 0), (0, 255, 0), (0, 0, 255),
            (255, 255, 0), (255, 0, 255), (0, 255, 255), (128, 0, 0),
            (0, 128, 0), (0, 0, 128), (128, 128, 0), (128, 0, 128),
            (0, 128, 128), (192, 192, 192), (128, 128, 128), (153, 153, 255),
            (153, 51, 102), (255, 255, 204), (204, 255, 255), (102, 0, 102),
            (255, 128, 128), (0, 102, 204), (204, 204, 255), (0, 0, 128),
            (255, 0, 255), (255, 255, 0), (0, 255, 255), (128, 0, 128),
            (128, 0, 0), (0, 128, 128), (0, 0, 255), (0, 204, 255),
            (204, 255, 255), (204, 255, 204), (255, 255, 153), (153, 204, 255),
            (255, 153, 204), (204, 153, 255), (255, 204, 153), (51, 102, 255),
            (51, 204, 204), (153, 204, 0), (255, 204, 0), (255, 153, 0),
            (255, 102, 0), (102, 102, 153), (150, 150, 150), (0, 51, 102),
            (51, 153, 102), (0, 51, 0), (51, 51, 0), (153, 51, 0),
            (153, 51, 102), (51, 51, 153), (51, 51, 51)
        ]

        distances = [abs(red - r) + abs(green - g) + abs(blue - b)
                     for r, g, b in xlwt_colors]

        min_dist_idx = distances.index(min(distances))

        return min_dist_idx

    def _shape2xls(self, worksheets):
        """Writes shape to xls file

        Format: <rows>\t<cols>\t<tabs>\n

        """

        __, __, tabs = self.code_array.shape

        if tabs > self.xls_max_tabs:
            tabs = self.xls_max_tabs

        for tab in xrange(tabs):
            worksheet = self.workbook.add_sheet(str(tab))
            worksheets.append(worksheet)

    def _xls2shape(self):
        """Updates shape in code_array"""

        sheets = self.workbook.sheets()
        nrows = sheets[0].nrows
        ncols = sheets[0].ncols
        ntabs = len(sheets)

        self.code_array.shape = nrows, ncols, ntabs

    def _code2xls(self, worksheets):
        """Writes code to xls file

        Format: <row>\t<col>\t<tab>\t<code>\n

        """

        xls_max_shape = self.xls_max_rows, self.xls_max_cols, self.xls_max_tabs

        for key in self.code_array:
            if all(kele < mele for kele, mele in zip(key, xls_max_shape)):
                # Cell lies within Excel boundaries
                row, col, tab = key
                code_str = self.code_array(key)
                style = self._get_xfstyle(worksheets, key)
                worksheets[tab].write(row, col, label=code_str, style=style)

    def _xls2code(self, worksheet, tab):
        """Updates code in xls code_array"""

        type2mapper = {
            0: lambda x: None,  # Empty cell
            1: lambda x: repr(x),  # Text cell
            2: lambda x: repr(x),  # Number cell
            3: lambda x: repr(datetime(
                xlrd.xldate_as_tuple(x, self.workbook.datemode))),  # Date
            4: lambda x: repr(bool(x)),  # Boolean cell
            5: lambda x: repr(x),  # Error cell
            6: lambda x: None,  # Blank cell
        }

        rows, cols = worksheet.nrows, worksheet.ncols
        for row, col in product(xrange(rows), xrange(cols)):
            cell_type = worksheet.cell_type(row, col)
            cell_value = worksheet.cell_value(row, col)

            key = row, col, tab
            self.code_array[key] = type2mapper[cell_type](cell_value)

    def _get_xfstyle(self, worksheets, key):
        """Gets XFStyle for cell key"""

        dict_grid = self.code_array.dict_grid

        # Get all cells in selections

        pys_style = dict_grid.cell_attributes[key]
        xfstyle = xlwt.XFStyle()

        # Font
        # ----

        if "textfont" in pys_style:

            font = xlwt.Font()

            font.name = pys_style["textfont"]

            if "pointsize" in pys_style:
                font.height = pys_style["pointsize"] * 20.0

            if "fontweight" in pys_style:
                font.bold = (pys_style["fontweight"] == wx.BOLD)

            if "fontstyle" in pys_style:
                font.italic = (pys_style["fontstyle"] == wx.ITALIC)

            if "textcolor" in pys_style:
                textcolor = wx.Colour()
                textcolor.SetRGB(pys_style["textcolor"])
                font.colour_index = self.color2idx(*textcolor.Get())

            if "underline" in pys_style:
                font.underline_type = pys_style["underline"]

            if "strikethrough" in pys_style:
                font.struck_out = pys_style["strikethrough"]

            xfstyle.font = font

        # Alignment
        # ---------

        if any(e in pys_style for e in ["justification", "vertical_align",
                                        "angle"]):
            alignment = xlwt.Alignment()

        if "justification" in pys_style:
            justification2xfalign = {
                "left": 1,
                "center": 2,
                "right": 3,
            }

            alignment.horz = justification2xfalign[pys_style["justification"]]

        if "vertical_align" in pys_style:
            vertical_align2xfalign = {
                "top": 0,
                "middle": 1,
                "bottom": 2,
            }

            alignment.vert = \
                vertical_align2xfalign[pys_style["vertical_align"]]

        if "angle" in pys_style:
            def angle2xfrotation(angle):
                """Returns angle from xlrotatation"""

                # angle is counterclockwise
                if 0 <= angle <= 90:
                    return angle

                elif -90 <= angle < 0:
                    return 90 - angle

                return 0

            alignment.rota = angle2xfrotation(pys_style["angle"])

        if any(e in pys_style for e in ["justification", "vertical_align",
                                        "angle"]):
            xfstyle.alignment = alignment

        # Background
        # ----------

        if "bgcolor" in pys_style:
            pattern = xlwt.Pattern()
            pattern.pattern = xlwt.Pattern.SOLID_PATTERN

            bgcolor = wx.Colour()
            bgcolor.SetRGB(pys_style["bgcolor"])
            pattern.pattern_fore_colour = self.color2idx(*bgcolor.Get())

            xfstyle.pattern = pattern

        # Border
        # ------

#        width2border_line_style = {
#            1: 0,
#            1: 1,
#            2: 1,
#            3: 1,
#            4: 1,
#            5: 2,
#            6: 2,
#            7: 5,
#            8: 5,
#            9: 5,
#        }
#
#        border_keys = [
#            "borderwidth_right",
#            "borderwidth_bottom",
#            "bordercolor_right"
#            "bordercolor_bottom"
#        ]
#
#        if any(border_key in pys_style for border_key in border_keys):
#            border = xlwt.Borders()
#
#        try:
#            border_pys_style = pys_style["borderwidth_right"]
#            border_line_style = width2border_line_style[border_pys_style]
#            border.right_line_style = border_line_style
#
#        except KeyError:
#            # No or unknown border width
#            pass
#
#        try:
#            border_pys_style = pys_style["borderwidth_bottom"]
#            border_line_style = width2border_line_style[border_pys_style]
#            border.bottom_line_style = border_line_style
#
#        except KeyError:
#            # No or unknown border width
#            pass
#
#        try:
#            print pys_style["bordercolor_right"]
#            border_pys_style = pys_style["bordercolor_right"]
#            bcolor = wx.Colour()
#            bcolor.SetRGB(border_pys_style)
#            border.right_colour_index = self.color2idx(*bgcolor.Get())
#            print bcolor, border.right_colour_index
#
#        except KeyError:
#            # No or unknown border color
#            pass
#
#        try:
#            border_pys_style = pys_style["bordercolor_bottom"]
#            bcolor = wx.Colour()
#            bcolor.SetRGB(border_pys_style)
#            border.bottom_colour_index = self.color2idx(*bgcolor.Get())
#
#        except KeyError:
#            # No or unknown border color
#            pass
#
#        if any(border_key in pys_style for border_key in border_keys):
#            xfstyle.border = border

        return xfstyle

    def _xls2attributes(self, worksheet, tab):
        """Updates attributes in code_array"""

        # Merged cells
        for top, bottom, left, right in worksheet.merged_cells:
            attrs = {"merge_area": (top, left, bottom - 1, right - 1)}
            selection = Selection([(top, left)], [(bottom - 1, right - 1)],
                                  [], [], [])
            self.code_array.cell_attributes.append((selection, tab, attrs))

        # Which cell comprise which format ids
        xf2cell = dict((xfid, []) for xfid in xrange(self.workbook.xfcount))
        rows, cols = worksheet.nrows, worksheet.ncols
        for row, col in product(xrange(rows), xrange(cols)):
            xfid = worksheet.cell_xf_index(row, col)
            xf2cell[xfid].append((row, col))

        for xfid, xf in enumerate(self.workbook.xf_list):
            selection = Selection([], [], [], [], xf2cell[xfid])
            selection_above = selection.shifted(-1, 0)
            selection_left = selection.shifted(0, -1)

            attributes = {}

            # Alignment

            xfalign2justification = {
                0: "left",
                1: "left",
                2: "center",
                3: "right",
                4: "left",
                5: "left",
                6: "center",
                7: "left",
            }

            xfalign2vertical_align = {
                0: "top",
                1: "middle",
                2: "bottom",
                3: "middle",
                4: "middle",
            }

            def xfrotation2angle(xfrotation):
                """Returns angle from xlrotatation"""

                # angle is counterclockwise
                if 0 <= xfrotation <= 90:
                    return xfrotation

                elif 90 < xfrotation <= 180:
                    return - (xfrotation - 90)

                return 0

            try:
                attributes["justification"] = \
                    xfalign2justification[xf.alignment.hor_align]

                attributes["vertical_align"] = \
                    xfalign2vertical_align[xf.alignment.vert_align]

                attributes["angle"] = \
                    xfrotation2angle(xf.alignment.rotation)

            except AttributeError:
                pass

            # Background
            if xf.background.fill_pattern == 1:
                color_idx = xf.background.pattern_colour_index
                color = self.idx2colour(color_idx)
                attributes["bgcolor"] = color.GetRGB()

            # Border
            border_line_style2width = {
                0: 1,
                1: 3,
                2: 5,
                5: 7,
            }

            bottom_color_idx = xf.border.bottom_colour_index
            if self.workbook.colour_map[bottom_color_idx] is not None:
                bottom_color = self.idx2colour(bottom_color_idx)
                attributes["bordercolor_bottom"] = bottom_color.GetRGB()

            right_color_idx = xf.border.right_colour_index
            if self.workbook.colour_map[right_color_idx] is not None:
                right_color = self.idx2colour(right_color_idx)
                attributes["bordercolor_right"] = right_color.GetRGB()

            bottom_width = border_line_style2width[xf.border.bottom_line_style]
            attributes["borderwidth_bottom"] = bottom_width

            right_width = border_line_style2width[xf.border.right_line_style]
            attributes["borderwidth_right"] = right_width

            # Font

            font = self.workbook.font_list[xf.font_index]

            attributes["textfont"] = font.name
            attributes["pointsize"] = font.height / 20.0

            fontweight = wx.BOLD if font.weight == 700 else wx.NORMAL
            attributes["fontweight"] = fontweight

            if font.italic:
                attributes["fontstyle"] = wx.ITALIC

            if self.workbook.colour_map[font.colour_index] is not None:
                attributes["textcolor"] = \
                    self.idx2colour(font.colour_index).GetRGB()

            if font.underline_type:
                attributes["underline"] = True

            if font.struck_out:
                attributes["strikethrough"] = True

            # Handle cells above for top borders

            attributes_above = {}
            top_width = border_line_style2width[xf.border.top_line_style]
            if top_width != 1:
                attributes_above["borderwidth_bottom"] = top_width
            top_color_idx = xf.border.top_colour_index
            if self.workbook.colour_map[top_color_idx] is not None:
                top_color = self.idx2colour(top_color_idx)
                attributes_above["bordercolor_bottom"] = top_color.GetRGB()

            # Handle cells above for left borders

            attributes_left = {}
            left_width = border_line_style2width[xf.border.left_line_style]
            if left_width != 1:
                attributes_left["borderwidth_right"] = left_width
            left_color_idx = xf.border.left_colour_index
            if self.workbook.colour_map[left_color_idx] is not None:
                left_color = self.idx2colour(left_color_idx)
                attributes_above["bordercolor_right"] = left_color.GetRGB()

            if attributes_above:
                self._cell_attribute_append(selection_above, tab,
                                            attributes_above)
            if attributes_left:
                self._cell_attribute_append(selection_left, tab,
                                            attributes_left)
            if attributes:
                self._cell_attribute_append(selection, tab, attributes)

    def _cell_attribute_append(self, selection, tab, attributes):
        """Appends to cell_attributes with checks"""

        cell_attributes = self.code_array.cell_attributes

        thick_bottom_cells = []
        thick_right_cells = []

        # Does any cell in selection.cells have a larger bottom border?

        if "borderwidth_bottom" in attributes:
            bwidth = attributes["borderwidth_bottom"]
            for row, col in selection.cells:
                __bwidth = cell_attributes[row, col, tab]["borderwidth_bottom"]
                if __bwidth > bwidth:
                    thick_bottom_cells.append((row, col))

        # Does any cell in selection.cells have a larger right border?
        if "borderwidth_right" in attributes:
            rwidth = attributes["borderwidth_right"]
            for row, col in selection.cells:
                __rwidth = cell_attributes[row, col, tab]["borderwidth_right"]
                if __rwidth > rwidth:
                    thick_right_cells.append((row, col))

        for thick_cell in thick_bottom_cells + thick_right_cells:
            selection.cells.pop(selection.cells.index(thick_cell))

        cell_attributes.append((selection, tab, attributes))

        if thick_bottom_cells:
            bsel = copy(selection)
            bsel.cells = thick_bottom_cells
            battrs = copy(attributes)
            battrs.pop("borderwidth_bottom")
            cell_attributes.append((bsel, tab, battrs))

        if thick_right_cells:
            rsel = copy(selection)
            rsel.cells = thick_right_cells
            rattrs = copy(attributes)
            rattrs.pop("borderwidth_right")
            cell_attributes.append((bsel, tab, battrs))

    def _row_heights2xls(self, worksheets):
        """Writes row_heights to xls file

        Format: <row>\t<tab>\t<value>\n

        """

        xls_max_rows, xls_max_tabs = self.xls_max_rows, self.xls_max_tabs

        dict_grid = self.code_array.dict_grid

        for row, tab in dict_grid.row_heights:
            if row < xls_max_rows and tab < xls_max_tabs:
                height_pixels = dict_grid.row_heights[(row, tab)]
                height_inches = height_pixels / float(get_dpi()[1])
                height_points = height_inches * 72.0

                worksheets[tab].row(row).height_mismatch = True
                worksheets[tab].row(row).height = int(height_points * 20.0)

    def _xls2row_heights(self, worksheet, tab):
        """Updates row_heights in code_array"""

        for row in xrange(worksheet.nrows):
            try:
                height_points = worksheet.rowinfo_map[row].height / 20.0
                height_inches = height_points / 72.0
                height_pixels = height_inches * get_dpi()[1]

                self.code_array.row_heights[row, tab] = height_pixels

            except KeyError:
                pass

    def _col_widths2xls(self, worksheets):
        """Writes col_widths to xls file

        Format: <col>\t<tab>\t<value>\n

        """

        xls_max_cols, xls_max_tabs = self.xls_max_cols, self.xls_max_tabs

        dict_grid = self.code_array.dict_grid

        for col, tab in dict_grid.col_widths:
            if col < xls_max_cols and tab < xls_max_tabs:
                width_0 = get_default_text_extent("0")[0]
                width_pixels = dict_grid.col_widths[(col, tab)]
                width_0_char = width_pixels * 1.2 / width_0

                worksheets[tab].col(col).width_mismatch = True
                worksheets[tab].col(col).width = int(width_0_char * 256.0)

    def _xls2col_widths(self, worksheet, tab):
        """Updates col_widths in code_array"""

        for col in xrange(worksheet.ncols):
            try:
                width_0_char = worksheet.colinfo_map[col].width / 256.0
                width_0 = get_default_text_extent("0")[0]
                # Scale relative to 10 point font instead of 12 point
                width_pixels = width_0_char * width_0 / 1.2

                self.code_array.col_widths[col, tab] = width_pixels

            except KeyError:
                pass

    # Access via model.py data
    # ------------------------

    def from_code_array(self):
        """Returns xls workbook object with everything from code_array"""

        worksheets = []
        self._shape2xls(worksheets)

        self._code2xls(worksheets)

        self._row_heights2xls(worksheets)
        self._col_widths2xls(worksheets)

        return self.workbook

    def to_code_array(self):
        """Replaces everything in code_array from xls_file"""

        self._xls2shape()

        worksheets = self.workbook.sheet_names()

        for tab, worksheet_name in enumerate(worksheets):
            worksheet = self.workbook.sheet_by_name(worksheet_name)
            self._xls2code(worksheet, tab)
            self._xls2attributes(worksheet, tab)
            self._xls2row_heights(worksheet, tab)
            self._xls2col_widths(worksheet, tab)

########NEW FILE########
__FILENAME__ = charts
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread. If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
charts
======

Provides matplotlib figure that are chart templates

Provides
--------

* object2code: Returns code for widget from dict object
* fig2bmp: Returns wx.Bitmap from matplotlib chart
* ChartFigure: Main chart class

"""

from copy import copy
from cStringIO import StringIO
import datetime
import i18n
import warnings
import types

import wx

from matplotlib.figure import Figure
from matplotlib.sankey import Sankey
from matplotlib import dates
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


def object2code(key, code):
    """Returns code for widget from dict object"""

    if key in ["xscale", "yscale"]:
        if code == "log":
            code = True
        else:
            code = False

    else:
        code = unicode(code)

    return code


def fig2bmp(figure, width, height, dpi, zoom):
    """Returns wx.Bitmap from matplotlib chart

    Parameters
    ----------
    fig: Object
    \tMatplotlib figure
    width: Integer
    \tImage width in pixels
    height: Integer
    \tImage height in pixels
    dpi = Float
    \tDC resolution

    """

    dpi *= float(zoom)

    figure.set_figwidth(width / dpi)
    figure.set_figheight(height / dpi)
    figure.subplots_adjust()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            # The padding is too small for small sizes. This fixes it.
            figure.tight_layout(pad=1.0/zoom)

        except ValueError:
            pass

    figure.set_canvas(FigureCanvas(figure))
    png_stream = StringIO()

    figure.savefig(png_stream, format='png', dpi=(dpi))

    png_stream.seek(0)
    img = wx.ImageFromStream(png_stream, type=wx.BITMAP_TYPE_PNG)

    return wx.BitmapFromImage(img)


def fig2x(figure, format):
    """Returns svg from matplotlib chart"""

    # Save svg to file like object svg_io
    io = StringIO()
    figure.savefig(io, format=format)

    # Rewind the file like object
    io.seek(0)

    data = io.getvalue()
    io.close()

    return data


class ChartFigure(Figure):
    """Chart figure class with drawing method"""

    plot_type_fixed_attrs = {
        "plot": ["ydata"],
        "bar": ["left", "height"],
        "boxplot": ["x"],
        "hist": ["x"],
        "pie": ["x"],
        "contour": ["X", "Y", "Z"],
        "contourf": ["X", "Y", "Z"],
        "Sankey": [],
    }

    plot_type_xy_mapping = {
        "plot": ["xdata", "ydata"],
        "bar": ["left", "height"],
        "boxplot": ["x", "x"],
        "hist": ["label", "x"],
        "pie": ["labels", "x"],
        "annotate": ["xy", "xy"],
        "contour": ["X", "Y"],
        "contourf": ["X", "Y", "Z"],
        "Sankey": ["flows", "orientations"],
    }

    contour_label_attrs = {
        "contour_labels": "contour_labels",
        "contour_label_fontsize": "fontsize",
        "contour_label_colors": "colors",
    }

    contourf_attrs = {
        "contour_fill": "contour_fill",
        "hatches": "hatches",
    }

    def __init__(self, *attributes):

        Figure.__init__(self, (5.0, 4.0), facecolor="white")

        self.attributes = attributes

        self.__axes = self.add_subplot(111)

        # Insert empty attributes with a dict for figure attributes
        if not self.attributes:
            self.attributes = [{}]

        self.draw_chart()

    def _xdate_setter(self, xdate_format='%Y-%m-%d'):
        """Makes x axis a date axis with auto format

        Parameters
        ----------

        xdate_format: String
        \tSets date formatting

        """

        if xdate_format:
            # We have to validate xdate_format. If wrong then bail out.
            try:
                datetime.date(2000, 1, 1).strftime(xdate_format)

            except ValueError:
                return

            self.__axes.xaxis_date()
            formatter = dates.DateFormatter(xdate_format)
            self.__axes.xaxis.set_major_formatter(formatter)

            # The autofmt method does not work in matplotlib 1.3.0
            #self.autofmt_xdate()

    def _setup_axes(self, axes_data):
        """Sets up axes for drawing chart"""

        self.__axes.clear()

        key2setter = {
            "title": self.__axes.set_title,
            "xlabel": self.__axes.set_xlabel,
            "ylabel": self.__axes.set_ylabel,
            "xscale": self.__axes.set_xscale,
            "yscale": self.__axes.set_yscale,
            "xtick_params": self.__axes.tick_params,
            "ytick_params": self.__axes.tick_params,
            "xlim": self.__axes.set_xlim,
            "ylim": self.__axes.set_ylim,
            "xgrid": self.__axes.xaxis.grid,
            "ygrid": self.__axes.yaxis.grid,
            "xdate_format": self._xdate_setter,
        }

        for key in key2setter:
            if key in axes_data and axes_data[key]:
                try:
                    kwargs_key = key + "_kwargs"
                    kwargs = axes_data[kwargs_key]

                except KeyError:
                    kwargs = {}

                key2setter[key](axes_data[key], **kwargs)

    def _setup_legend(self, axes_data):
        """Sets up legend for drawing chart"""

        if "legend" in axes_data and axes_data["legend"]:
            self.__axes.legend()

    def draw_chart(self):
        """Plots chart from self.attributes"""

        if not hasattr(self, "attributes"):
            return

        # The first element is always axes data
        self._setup_axes(self.attributes[0])

        for attribute in self.attributes[1:]:

            series = copy(attribute)
            # Extract chart type
            chart_type_string = series.pop("type")

            x_str, y_str = self.plot_type_xy_mapping[chart_type_string]
            # Check xdata length
            if x_str in series and \
               len(series[x_str]) != len(series[y_str]):
                # Wrong length --> ignore xdata
                series.pop(x_str)
            else:
                # Solve the problem that the series data may contain utf-8 data
                series_list = list(series[x_str])
                series_unicode_list = []
                for ele in series_list:
                    if isinstance(ele, types.StringType):
                        try:
                            series_unicode_list.append(ele.decode('utf-8'))
                        except Exception:
                            series_unicode_list.append(ele)
                    else:
                        series_unicode_list.append(ele)
                series[x_str] = tuple(series_unicode_list)

            fixed_attrs = []
            if chart_type_string in self.plot_type_fixed_attrs:
                for attr in self.plot_type_fixed_attrs[chart_type_string]:
                    # Remove attr if it is a fixed (non-kwd) attr
                    # If a fixed attr is missing, insert a dummy
                    try:
                        fixed_attrs.append(tuple(series.pop(attr)))
                    except KeyError:
                        fixed_attrs.append(())

            # Remove contour chart label info from series
            cl_attrs = {}
            for contour_label_attr in self.contour_label_attrs:
                if contour_label_attr in series:
                    cl_attrs[self.contour_label_attrs[contour_label_attr]] = \
                        series.pop(contour_label_attr)

            # Remove contourf attributes from series
            cf_attrs = {}
            for contourf_attr in self.contourf_attrs:
                if contourf_attr in series:
                    cf_attrs[self.contourf_attrs[contourf_attr]] = \
                        series.pop(contourf_attr)

            if not fixed_attrs or all(fixed_attrs):
                # Draw series to axes

                # Do we have a Sankey plot --> build it
                if chart_type_string == "Sankey":
                    Sankey(self.__axes, **series).finish()

                else:
                    chart_method = getattr(self.__axes, chart_type_string)
                    plot = chart_method(*fixed_attrs, **series)

                # Do we have a filled contour?
                try:
                    if cf_attrs.pop("contour_fill"):
                        cf_attrs.update(series)
                        if "linewidths" in cf_attrs:
                            cf_attrs.pop("linewidths")
                        if "linestyles" in cf_attrs:
                            cf_attrs.pop("linestyles")
                        if not cf_attrs["hatches"]:
                            cf_attrs.pop("hatches")
                        self.__axes.contourf(plot, **cf_attrs)
                except KeyError:
                    pass

                # Do we have a contour chart label?
                try:
                    if cl_attrs.pop("contour_labels"):
                        self.__axes.clabel(plot, **cl_attrs)
                except KeyError:
                    pass


        # The legend has to be set up after all series are drawn
        self._setup_legend(self.attributes[0])


class BasemapFigure(Figure):
    """Basemap figure class with drawing method"""

    def draw_basemap(self):
        """Plots basemap from self.attributes"""

        raise NotImplementedError

########NEW FILE########
__FILENAME__ = clipboard
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
clipboard
=========

Provides
--------

 * Clipboard: Clipboard interface class

"""

import wx

import src.lib.i18n as i18n

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


class Clipboard(object):
    """Clipboard access

    Provides:
    ---------
    get_clipboard: Get clipboard content
    set_clipboard: Set clipboard content
    grid_paste: Inserts data into grid target

    """

    clipboard = wx.TheClipboard

    def _convert_clipboard(self, datastring=None, sep='\t'):
        """Converts data string to iterable.

        Parameters:
        -----------
        datastring: string, defaults to None
        \tThe data string to be converted.
        \tself.get_clipboard() is called if set to None
        sep: string
        \tSeparator for columns in datastring

        """

        if datastring is None:
            datastring = self.get_clipboard()

        data_it = ((ele for ele in line.split(sep))
                            for line in datastring.splitlines())
        return data_it

    def get_clipboard(self):
        """Returns the clipboard content

        If a bitmap is contained then it is returned.
        Otherwise, the clipboard text is returned.

        """

        bmpdata = wx.BitmapDataObject()
        textdata = wx.TextDataObject()

        if self.clipboard.Open():
            is_bmp_present = self.clipboard.GetData(bmpdata)
            self.clipboard.GetData(textdata)
            self.clipboard.Close()
        else:
            wx.MessageBox(_("Can't open the clipboard"), _("Error"))

        if is_bmp_present:
            return bmpdata.GetBitmap()
        else:
            return textdata.GetText()

    def set_clipboard(self, data, datatype="text"):
        """Writes data to the clipboard

        Parameters
        ----------
        data: Object
        \tData object for clipboard
        datatype: String in ["text", "bitmap"]
        \tIdentifies datatype to be copied to teh clipboard

        """

        error_log = []

        if datatype == "text":
            data = wx.TextDataObject(text=data)

        elif datatype == "bitmap":
            data = wx.BitmapDataObject(bitmap=data)

        else:
            msg = _("Datatype {type} unknown").format(type=datatype)
            raise ValueError(msg)

        if self.clipboard.Open():
            self.clipboard.SetData(data)
            self.clipboard.Close()
        else:
            wx.MessageBox(_("Can't open the clipboard"), _("Error"))

        return error_log

# end of class Clipboard

########NEW FILE########
__FILENAME__ = exception_handling
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns, Jason Sexauer
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""

Exception Handeling
==========

exception_handling.py contains functions for handeling exceptions generated by

user code

Provides
--------

* get_user_codeframe: Returns traceback that only includes the user's execute
                      code frames

"""


def get_user_codeframe(tb):
    """Modify traceback to only include the user code's execution frame
    Always call in this fashion:
        e = sys.exc_info()
        user_tb = get_user_codeframe(e[2]) or e[2]
    so that you can get the original frame back if you need to
    (this is necessary because copying traceback objects is tricky and
    this is a good workaround)

    """
    while tb is not None:
        f = tb.tb_frame
        co = f.f_code
        filename = co.co_filename
        if filename[0] == '<':
            # This is a meta-descriptor
            # (probably either "<unknown>" or "<string>")
            # and is likely the user's code we're executing
            return tb
        else:
            tb = tb.tb_next
    # We could not find the user's frame.
    return False

########NEW FILE########
__FILENAME__ = fileio
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""

fileio
======

This module provides file reader and writer classes.
These classes behave like open but provide status messages and can be aborted.


Provides
--------

 * AOpen: Read and write files with status messages and abort option

"""

import bz2
import i18n

import wx

from src.gui._events import post_command_event
from src.sysvars import is_gtk

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


class AOpenMixin(object):
    """AOpen mixin class"""

    def set_initial_state(self, kwargs):
        """Sets class state from kwargs attributes, pops extra kwargs"""

        self.main_window = kwargs.pop("main_window")

        try:
            statustext = kwargs.pop("statustext")

        except KeyError:
            statustext = ""

        try:
            self.total_lines = kwargs.pop("total_lines")
            self.statustext = statustext + \
                _("{nele} of {totalele} elements processed.")

        except KeyError:
            self.total_lines = None
            self.statustext = statustext + _("{nele} elements processed.")

        try:
            self.freq = kwargs.pop("freq")

        except KeyError:
            self.freq = 1000

        # The aborted attribute makes next() to raise StopIteration
        self.aborted = False

        # Line counter
        self.line = 0

        # Bindings
        self.main_window.Bind(wx.EVT_KEY_DOWN, self.on_key)

    def next(self):

        """Next that shows progress in statusbar for each <freq> cells"""

        self.progress_status()

        # Check abortes state and raise StopIteration if aborted
        if self.aborted:
            statustext = _("File loading aborted.")
            post_command_event(self.main_window, self.main_window.StatusBarMsg,
                               text=statustext)
            raise StopIteration

        return self.parent_cls.next(self)

    def write(self, *args, **kwargs):
        """Write that shows progress in statusbar for each <freq> cells"""

        self.progress_status()

        # Check abortes state and raise StopIteration if aborted
        if self.aborted:
            statustext = _("File saving aborted.")
            post_command_event(self.main_window, self.main_window.StatusBarMsg,
                               text=statustext)
            return False

        return self.parent_cls.write(self, *args, **kwargs)

    def progress_status(self):
        """Displays progress in statusbar"""

        if self.line % self.freq == 0:
            text = self.statustext.format(nele=self.line,
                                          totalele=self.total_lines)

            if self.main_window.grid.actions.pasting:
                try:
                    post_command_event(self.main_window,
                                       self.main_window.StatusBarMsg,
                                       text=text)
                except TypeError:
                    # The main window does not exist any more
                    pass
            else:
                # Write directly to the status bar because the event queue
                # is not emptied during file access

                self.main_window.GetStatusBar().SetStatusText(text)

            # Now wait for the statusbar update to be written on screen
            if is_gtk():
                wx.Yield()

        self.line += 1

    def on_key(self, event):
        """Sets aborted state if escape is pressed"""

        if self.main_window.grid.actions.pasting and \
           event.GetKeyCode() == wx.WXK_ESCAPE:
            self.aborted = True

        event.Skip()


class AOpen(AOpenMixin, file):
    """Read and write files with status messages and abort option

    Extra Key Word Parameters (extends open)
    ----------------------------------------

    main_window: Object
    \tMain window object, must be set
    statustext: String, defaults to ""
    \tLeft text in statusbar to be displayed
    total_lines: Integer, defaults to None
    \tThe number of elements that have to be processed
    freq: Integer, defaults to 1000
    \tNo. operations between two abort possibilities

    """

    parent_cls = file

    def __init__(self, *args, **kwargs):

        self.set_initial_state(kwargs)

        file.__init__(self, *args, **kwargs)


class Bz2AOpen(AOpenMixin, bz2.BZ2File):
    """Read and write bz2 files with status messages and abort option

    Extra Key Word Parameters (extends open)
    ----------------------------------------

    main_window: Object
    \tMain window object, must be set
    statustext: String, defaults to ""
    \tLeft text in statusbar to be displayed
    total_lines: Integer, defaults to None
    \tThe number of elements that have to be processed
    freq: Integer, defaults to 1000
    \tNo. operations between two abort possibilities

    """

    parent_cls = bz2.BZ2File

    def __init__(self, *args, **kwargs):

        self.set_initial_state(kwargs)

        bz2.BZ2File.__init__(self, *args, **kwargs)

########NEW FILE########
__FILENAME__ = gpg
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""

gpg
===

GPG handling functions

Provides
--------

 * genkey: Generates gpg key
 * sign: Returns detached signature for file
 * verify: verifies stream against signature

"""

import sys

import wx
import wx.lib.agw.genericmessagedialog as GMD
import gnupg

import src.lib.i18n as i18n
from src.config import config
from src.gui._gui_interfaces import get_key_params_from_user

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


def choose_key(gpg_private_keys, gpg_private_fingerprints):
    """Displays gpg key choice and returns key"""

    uid_strings_fp = []
    uid_string_fp2key = {}

    for key, fingerprint in zip(gpg_private_keys, gpg_private_fingerprints):
        for uid_string in key['uids']:
            uid_string_fp = '"' + uid_string + ' (' + fingerprint + ')'
            uid_strings_fp.append(uid_string_fp)
            uid_string_fp2key[uid_string_fp] = key

    msg = _('Choose a GPG key for signing pyspread save files.\n'
            'The GPG key must not have a passphrase set.')

    dlg = wx.SingleChoiceDialog(None, msg, _('Choose key'), uid_strings_fp,
                                wx.CHOICEDLG_STYLE)

    dlg.SetBestFittingSize()

    childlist = list(dlg.GetChildren())
    childlist[-3].SetLabel(_("Use chosen key"))
    childlist[-2].SetLabel(_("Create new key"))

    if dlg.ShowModal() == wx.ID_OK:
        uid_string_fp = dlg.GetStringSelection()
        key = uid_string_fp2key[uid_string_fp]

    else:
        key = None

    dlg.Destroy()

    return key


def genkey():
    """Creates a new standard GPG key"""

    gpg = gnupg.GPG()

    gpg.encoding = 'utf-8'

    # Check if standard key is already present

    pyspread_key_fingerprint = str(config["gpg_key_fingerprint"])
    gpg_private_keys = gpg.list_keys(True)
    gpg_private_fingerprints = gpg.list_keys(True).fingerprints

    pyspread_key = None

    for private_key, fingerprint in zip(gpg_private_keys,
                                        gpg_private_fingerprints):
        if pyspread_key_fingerprint == fingerprint:
            pyspread_key = private_key

    if pyspread_key is None:
        # If no GPG key is set in config, choose one
        pyspread_key = choose_key(gpg_private_keys, gpg_private_fingerprints)

    if pyspread_key:
        # A key has been chosen
        fingerprint = \
            gpg_private_fingerprints[gpg_private_keys.index(pyspread_key)]
        config["gpg_key_fingerprint"] = repr(fingerprint)

    else:
        # No key has been chosen --> Create new one
        gpg_key_parameters = get_key_params_from_user()

        input_data = gpg.gen_key_input(**gpg_key_parameters)

        # Generate key
        # ------------

        # Show infor dialog

        style = wx.ICON_INFORMATION | wx.DIALOG_NO_PARENT | wx.OK | wx.CANCEL
        pyspread_key_uid = gpg_key_parameters["name_real"]
        short_message = _("New GPG key").format(pyspread_key_uid)
        message = _("After confirming this dialog, a new GPG key ") + \
            _("'{key}' will be generated.").format(key=pyspread_key_uid) + \
            _(" \n \nThis may take some time.\nPlease wait.\n \n") + \
            _("Canceling this operation exits pyspread.")
        dlg = GMD.GenericMessageDialog(None, message, short_message, style)
        dlg.Centre()

        if dlg.ShowModal() == wx.ID_OK:
            dlg.Destroy()
            fingerprint = gpg.gen_key(input_data)

            for private_key in gpg.list_keys(True):
                if str(fingerprint) == private_key['fingerprint']:
                    config["gpg_key_fingerprint"] = repr(
                        private_key.fingerprint)

        else:
            dlg.Destroy()
            sys.exit()


def sign(filename):
    """Returns detached signature for file"""

    gpg = gnupg.GPG()

    signfile = open(filename, "rb")

    signed_data = gpg.sign_file(signfile, keyid=config["gpg_key_fingerprint"],
                                detach=True)
    signfile.close()

    return signed_data


def verify(sigfilename, filefilename=None):
    """Verifies a signature, returns True if successful else False."""

    gpg = gnupg.GPG()

    sigfile = open(sigfilename, "rb")

    verified = gpg.verify_file(sigfile, filefilename)

    sigfile.close()

    return verified

########NEW FILE########
__FILENAME__ = i18n
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
i18n
====

This module handles internationalization

"""

import os
import gettext
import sys

import wx

#  Translation files are located in
#  @LOCALE_DIR@/@LANGUAGE@/LC_MESSAGES/@APP_NAME@.mo
APP_NAME = "pyspread"

APP_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))

# .mo files  are located in APP_Dir/locale/LANGUAGECODE/LC_MESSAGES/
LOCALE_DIR = os.path.join(APP_DIR, 'locale')

# Choose the language
# -------------------
# A list is provided,gettext uses the first translation available in the list
DEFAULT_LANGUAGES = ['en_US']

langid = wx.LANGUAGE_DEFAULT
wxlocale = wx.Locale(langid)
languages = [wxlocale.GetCanonicalName()]

# Languages and locations of translations are in env + default locale

#languages += DEFAULT_LANGUAGES

mo_location = LOCALE_DIR

# gettext initialization
# ----------------------

language = gettext.translation(APP_NAME, mo_location, languages=languages,
                               fallback=True)
########NEW FILE########
__FILENAME__ = parsers
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""

parsers
=======

Provides
--------

 * get_font_from_data
 * get_pen_from_data
 * color2code
 * code2color
 * parse_dict_strings

"""

import ast

import wx

from src.sysvars import get_default_font


def get_font_from_data(fontdata):
    """Returns wx.Font from fontdata string"""

    textfont = get_default_font()

    if fontdata != "":
        nativefontinfo = wx.NativeFontInfo()
        nativefontinfo.FromString(fontdata)

        # OS X does not like a PointSize of 0
        # Therefore, it is explicitly set to the system default font point size

        if not nativefontinfo.GetPointSize():
            nativefontinfo.SetPointSize(get_default_font().GetPointSize())

        textfont.SetNativeFontInfo(nativefontinfo)

    return textfont


def get_pen_from_data(pendata):
    """Returns wx.Pen from pendata attribute list"""

    pen_color = wx.Colour()
    pen_color.SetRGB(pendata[0])
    pen = wx.Pen(pen_color, *pendata[1:])
    pen.SetJoin(wx.JOIN_MITER)

    return pen


def code2color(color_string):
    """Returns wx.Colour from a string of a 3-tuple of floats in [0.0, 1.0]"""

    color_tuple = ast.literal_eval(color_string)
    color_tuple_int = map(lambda x: int(x * 255.0), color_tuple)

    return wx.Colour(*color_tuple_int)


def color2code(color):
    """Returns repr of 3-tuple of floats in [0.0, 1.0] from wx.Colour"""

    return unicode(tuple(i / 255.0 for i in color.Get()))


def unquote_string(code):
    """Returns a string from code that contains aa repr of the string"""

    if code[0] in ['"', "'"]:
        start = 1
    else:
        # start may have a Unicode or raw string
        start = 2

    return code[start:-1]


def parse_dict_strings(code):
    """Generator of elements of a dict that is given in the code string

    Parsing is shallow, i.e. all content is yielded as strings

    Parameters
    ----------
    code: String
    \tString that contains a dict

    """

    i = 0
    level = 0
    chunk_start = 0
    curr_paren = None

    for i, char in enumerate(code):
        if char in ["(", "[", "{"] and curr_paren is None:
            level += 1
        elif char in [")", "]", "}"] and curr_paren is None:
            level -= 1
        elif char in ['"', "'"]:
            if curr_paren == char:
                curr_paren = None
            elif curr_paren is None:
                curr_paren = char

        if level == 0 and char in [':', ','] and curr_paren is None:
            yield code[chunk_start: i].strip()
            chunk_start = i + 1

    yield code[chunk_start:i + 1].strip()

########NEW FILE########
__FILENAME__ = selection
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
Selection
=========

Grid selection representation

"""

from itertools import izip


class Selection(object):
    """Represents grid selection

    Parameters
    ----------

    block_top_left: List of 2-tuples
    \tTop left edges of all selection rectangles
    block_bottom_right: List of 2-tuples
    \tBottom right edges of all selection rectangles
    rows: List
    \tList of selected rows
    cols: List
    \tList of selected columns
    cells: List of 2-tuples
    \tList of (row, column) tuples of individually selected cells

    """

    def __init__(self, block_top_left, block_bottom_right, rows, cols, cells):
        self.block_tl = block_top_left
        self.block_br = block_bottom_right
        self.rows = rows
        self.cols = cols
        self.cells = cells

    def __nonzero__(self):
        """Returns True iif any attribute is non-empty"""

        return any((self.block_tl,
                    self.block_br,
                    self.rows,
                    self.cols,
                    self.cells))

    def __repr__(self):
        """String output for printing selection"""

        params = self.block_tl, self.block_br, self.rows, self.cols, self.cells

        return "Selection" + repr(params)

    def __eq__(self, other):
        """Returns True if self and other selection are equal

        Selections are equal iif the order of each attribute is equal
        because order precedence may change the selection outcome in the grid.

        """

        assert type(other) is type(self)

        attrs = ("block_tl", "block_br", "rows", "cols", "cells")

        return all(getattr(self, at) == getattr(other, at) for at in attrs)

    def __contains__(self, cell):
        """Returns True iif cell is in selection

        Parameters
        ----------

        cell: 2-Tuple
        \tIndex of cell that is checked if it is inside selection.

        """

        assert len(cell) == 2

        cell_row, cell_col = cell

        # Block selections
        for top_left, bottom_right in izip(self.block_tl, self.block_br):
            top, left = top_left
            bottom, right = bottom_right

            if top <= cell_row <= bottom and left <= cell_col <= right:
                return True

        # Row and column selections

        if cell_row in self.rows or cell_col in self.cols:
            return True

        # Cell selections
        if cell in self.cells:
            return True

        return False

    def __add__(self, value):
        """Shifts selection down and / or right

        Parameters
        ----------

        value: 2-tuple
        \tRows and cols to be shifted up

        """

        delta_row, delta_col = value

        block_tl = [(t + delta_row, l + delta_col) for t, l in self.block_tl]
        block_br = [(t + delta_row, l + delta_col) for t, l in self.block_br]
        rows = [row + delta_row for row in self.rows]
        cols = [col + delta_col for col in self.cols]
        cells = [(r + delta_row, c + delta_col) for r, c in self.cells]

        return Selection(block_tl, block_br, rows, cols, cells)

    def insert(self, point, number, axis):
        """Inserts number of rows/cols/tabs into selection at point on axis
        Parameters
        ----------

        point: Integer
        \tAt this point the rows/cols are inserted or deleted
        number: Integer
        \tNumber of rows/cols to be inserted, negative number deletes
        axis: Integer in 0, 1
        \tDefines whether rows or cols are affected

        """

        def build_tuple_list(source_list, point, number, axis):
            """Returns adjusted tuple list for single cells"""

            target_list = []

            for tl in source_list:
                tl_list = list(tl)
                if tl[axis] > point:
                    tl_list[axis] += number
                target_list.append(tuple(tl_list))

            return target_list

        self.block_tl = build_tuple_list(self.block_tl, point, number, axis)

        self.block_br = build_tuple_list(self.block_br, point, number, axis)

        if axis == 0:
            self.rows = \
                [row + number if row > point else row for row in self.rows]
        elif axis == 1:
            self.cols = \
                [col + number if col > point else col for col in self.cols]
        else:
            raise ValueError("Axis not in [0, 1]")

        self.cells = build_tuple_list(self.cells, point, number, axis)

    def get_bbox(self):
        """Returns ((top, left), (bottom, right)) of bounding box

        A bounding box is the smallest rectangle that contains all selections.
        Non-specified boundaries are None.

        """

        bb_top, bb_left, bb_bottom, bb_right = [None] * 4

        # Block selections

        for top_left, bottom_right in zip(self.block_tl, self.block_br):
            top, left = top_left
            bottom, right = bottom_right

            if bb_top is None or bb_top > top:
                bb_top = top
            if bb_left is None or bb_left > left:
                bb_left = left
            if bb_bottom is None or bb_bottom < bottom:
                bb_bottom = bottom
            if bb_right is None or bb_right > right:
                bb_right = right

        # Row and column selections

        for row in self.rows:
            if bb_top is None or bb_top > row:
                bb_top = row
            if bb_bottom is None or bb_bottom < row:
                bb_bottom = row

        for col in self.cols:
            if bb_left is None or bb_left > col:
                bb_left = col
            if bb_right is None or bb_right < col:
                bb_right = col

        # Cell selections

        for cell in self.cells:
            cell_row, cell_col = cell

            if bb_top is None or bb_top > cell_row:
                bb_top = cell_row
            if bb_left is None or bb_left > cell_col:
                bb_left = cell_col
            if bb_bottom is None or bb_bottom < cell_row:
                bb_bottom = cell_row
            if bb_right is None or bb_right < cell_col:
                bb_right = cell_col

        if all(val is None for val in [bb_top, bb_left, bb_bottom, bb_right]):
            return None

        return ((bb_top, bb_left), (bb_bottom, bb_right))

    def get_grid_bbox(self, shape):
        """Returns ((top, left), (bottom, right)) of bounding box

        A bounding box is the smallest rectangle that contains all selections.
        Non-specified boundaries are filled i from size.

        Parameters
        ----------

        shape: 3-Tuple of Integer
        \tGrid shape

        """

        (bb_top, bb_left), (bb_bottom, bb_right) = self.get_bbox()

        if bb_top is None:
            bb_top = 0
        if bb_left is None:
            bb_left = 0
        if bb_bottom is None:
            bb_bottom = shape[0]
        if bb_right is None:
            bb_right = shape[1]

        return ((bb_top, bb_left), (bb_bottom, bb_right))

    def get_access_string(self, shape, table):
        """Returns a string, with which the selection can be accessed

        Parameters
        ----------
        shape: 3-tuple of Integer
        \tShape of grid, for which the generated keys are valid
        table: Integer
        \tThird component of all returned keys. Must be in dimensions

        """

        rows, columns, tables = shape

        # Negative dimensions cannot be
        assert all(dim > 0 for dim in shape)

        # Current table has to be in dimensions
        assert 0 <= table < tables

        string_list = []

        # Block selections
        templ = "[(r, c, {}) for r in xrange({}, {}) for c in xrange({}, {})]"
        for (top, left), (bottom, right) in izip(self.block_tl, self.block_br):
            string_list += [templ.format(table, top, bottom + 1,
                                         left, right + 1)]

        # Fully selected rows
        template = "[({}, c, {}) for c in xrange({})]"
        for row in self.rows:
            string_list += [template.format(row, table, columns)]

        # Fully selected columns
        template = "[(r, {}, {}) for r in xrange({})]"
        for column in self.cols:
            string_list += [template.format(column, table, rows)]

        # Single cells
        for row, column in self.cells:
            string_list += [repr([(row, column, table)])]

        key_string = " + ".join(string_list)

        if len(string_list) == 0:
            return ""

        elif len(self.cells) == 1 and len(string_list) == 1:
            return "S[{}]".format(string_list[0][1:-1])

        else:
            template = "[S[key] for key in {} if S[key] is not None]"
            return template.format(key_string)

    def shifted(self, rows, cols):
        """Returns a new selection that is shifted by rows and cols.

        Negative values for rows and cols may result in a selection
        that addresses negative cells.

        Parameters
        ----------
        rows: Integer
        \tNumber of rows that the new selection is shifted down
        cols: Integer
        \tNumber of columns that the new selection is shifted right

        """

        shifted_block_tl = \
            [(row + rows, col + cols) for row, col in self.block_tl]
        shifted_block_br = \
            [(row + rows, col + cols) for row, col in self.block_br]
        shifted_rows = [row + rows for row in self.rows]
        shifted_cols = [col + cols for col in self.cols]
        shifted_cells = [(row + rows, col + cols) for row, col in self.cells]

        return Selection(shifted_block_tl, shifted_block_br, shifted_rows,
                         shifted_cols, shifted_cells)

    def grid_select(self, grid, clear_selection=True):
        """Selects cells of grid with selection content"""

        if clear_selection:
            grid.ClearSelection()

        for (tl, br) in zip(self.block_tl, self.block_br):
            grid.SelectBlock(tl[0], tl[1], br[0], br[1], addToSelected=True)

        for row in self.rows:
            grid.SelectRow(row, addToSelected=True)

        for col in self.cols:
            grid.SelectCol(col, addToSelected=True)

        for cell in self.cells:
            grid.SelectBlock(cell[0], cell[1], cell[0], cell[1],
                             addToSelected=True)
########NEW FILE########
__FILENAME__ = test_clipboard
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------


"""
test_clipboard
==============

Unit tests for clipboard.py

"""

import os
import sys

import wx
app = wx.App()

TESTPATH = os.sep.join(os.path.realpath(__file__).split(os.sep)[:-1]) + os.sep
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 3)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 2)

from src.lib.testlib import params, pytest_generate_tests

from src.lib.clipboard import Clipboard


class TestClipboard(object):
    """Unit tests for Clipboard"""

    clipboard = Clipboard()

    param_convert_clipboard = [
        {'data': "1\t2\t3", 'sep': "\t", 'res': [['1', '2', '3']]},
        {'data': "1\t2\t3\n4\t5\t6", 'sep': "\t",
         'res': [['1', '2', '3'], ['4', '5', '6']]},
        {'data': "1,2,3\n4,5,6", 'sep': ",",
         'res': [['1', '2', '3'], ['4', '5', '6']]},
    ]

    @params(param_convert_clipboard)
    def test_convert_clipboard(self, data, sep, res):
        """Unit test for _convert_clipboard"""

        gengen = self.clipboard._convert_clipboard(data, sep)
        result = list(list(linegen) for linegen in gengen)

        assert result == res

    param_set_get_clipboard = [
        {'text': ""},
        {'text': "Test"},
        {'text': u"ÓÓó€ëáßðïœ"},
        {'text': "Test1\tTest2"},
        {'text': "\b"},
    ]

    @params(param_set_get_clipboard)
    def test_set_get_clipboard(self, text):
        """Unit test for get_clipboard and set_clipboard"""

        clipboard = wx.TheClipboard

        textdata = wx.TextDataObject()
        textdata.SetText(text)
        clipboard.Open()
        clipboard.SetData(textdata)
        clipboard.Close()

        assert self.clipboard.get_clipboard() == text

########NEW FILE########
__FILENAME__ = test_csv
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------


"""
test_csv
========

Unit tests for __csv.py

"""

import os
import sys
import types

import wx
app = wx.App()

TESTPATH = os.sep.join(os.path.realpath(__file__).split(os.sep)[:-1]) + os.sep
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 3)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 2)

from src.gui._main_window import MainWindow
from src.lib.testlib import params, pytest_generate_tests
import src.lib.__csv as __csv
from src.lib.__csv import Digest, CsvInterface, TxtGenerator, sniff

param_sniff = [
    {'filepath': TESTPATH + 'test1.csv', 'header': True, 'delimiter': ',',
     'doublequote': 0, 'quoting': 0, 'quotechar': '"',
     'lineterminator': "\r\n", 'skipinitialspace': 0},
]


@params(param_sniff)
def test_sniff(filepath, header, delimiter, doublequote, quoting, quotechar,
               lineterminator, skipinitialspace):
    """Unit test for sniff"""

    dialect, __header = __csv.sniff(filepath)
    assert __header == header
    assert dialect.delimiter == delimiter
    assert dialect.doublequote == doublequote
    assert dialect.quoting == quoting
    assert dialect.quotechar == quotechar
    assert dialect.lineterminator == lineterminator
    assert dialect.skipinitialspace == skipinitialspace


param_first_line = [
    {'filepath': TESTPATH + 'test1.csv',
     'first_line': ["Text", "Number", "Float", "Date"]},
]


@params(param_first_line)
def test_get_first_line(filepath, first_line):
    """Unit test for get_first_line"""

    dialect, __header = __csv.sniff(filepath)
    __first_line = __csv.get_first_line(filepath, dialect)

    assert __first_line == first_line


param_digested_line = [
    {'line': "1, 3, 1",
     'digest_types': [types.StringType, types.IntType, types.FloatType],
     'res': ["1", 3, 1.0]},
    {'line': "1",
     'digest_types': [types.FloatType],
     'res': [1.0]},
    {'line': u"1, Gsdfjkljö",
     'digest_types': [types.FloatType, types.UnicodeType],
     'res': [1.0, u"Gsdfjkljö"]},
]


@params(param_digested_line)
def digested_line(line, digest_types, res):
    """Unit test for digested_line"""

    assert __csv.digested_line(line, digest_types) == res


def test_cell_key_val_gen():
    """Unit test for cell_key_val_gen"""

    list_of_lists = [range(10), range(10)]
    gen = __csv.cell_key_val_gen(list_of_lists, (100, 100, 10))
    for row, col, value in gen:
        assert col == value


class TestDigest(object):
    """Unit tests for Digest"""

    param_make_string = [
        {'val': 1, 'acc_types': [types.StringType], 'res': "1"},
        {'val': None, 'acc_types': [types.StringType], 'res': ""},
        {'val': 1, 'acc_types': [types.UnicodeType], 'res': u"1"},
        {'val': None, 'acc_types': [types.UnicodeType], 'res': u""},
    ]

    @params(param_make_string)
    def test_make(self, val, acc_types, res):
        """Unit test for make_foo"""

        digest = Digest(acc_types)

        assert digest(val) == res
        assert type(digest(val)) is type(res)


class TestCsvInterface(object):
    """Unit tests for CsvInterface"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

        filepath = TESTPATH + 'test1.csv'
        self.dialect, __ = sniff(filepath)
        self.digest_types = [types.UnicodeType]
        has_header = True

        self.interface = CsvInterface(self.main_window, filepath, self.dialect,
                                      self.digest_types, has_header)

#    def test_iter(self):
#        """Unit test for __iter__"""
#
#        testline = [u"Test1", u"234", u"3.34", u"2012/12/04"]
#
#        for i, line in enumerate(self.interface):
#            if i:
#                for j, ele in enumerate(line):
#                    assert ele == repr(testline[j])

    def test_get_csv_cells_gen(self):
        """Unit test for _get_csv_cells_gen"""

        data = [u'324', u'234', u'sdfg']
        res = self.interface._get_csv_cells_gen(data)

        for ele, rele in zip(data, res):
            assert repr(ele) == rele

    def test_write(self):
        """Unit test for write"""

        filepath = TESTPATH + 'dummy.csv'
        interface = CsvInterface(self.main_window, filepath, self.dialect,
                                 self.digest_types, False)

        interface.write([["test", "world"], ["", "hello"]])

        dummy = open(filepath, "w")
        interface.write(["test", "world"])
        dummy.close()

        os.remove(filepath)


class TestTxtGenerator(object):
    """Unit tests for TxtGenerator"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid
        self.code_array = self.grid.code_array

        filepath = TESTPATH + 'test_txt.csv'
        self.txtgen = TxtGenerator(self.main_window, filepath)

    def test_iter(self):
        """Unit test for __iter__"""

        res = [[ele for ele in line] for line in self.txtgen]
        assert res == [["Hallo", "Welt"], ["Test", "2"]]

########NEW FILE########
__FILENAME__ = test_gpg
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------


"""
test_gpg
========

Unit tests for gpg.py

"""

import os
import sys

import wx
app = wx.App()

TESTPATH = os.sep.join(os.path.realpath(__file__).split(os.sep)[:-1]) + os.sep
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 3)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 2)

import src.lib.gpg as gpg
from src.lib.testlib import params, pytest_generate_tests


def _set_sig(filename, sigfilename):
    """Creates a signature sigfilename for file filename"""

    signature = gpg.sign(filename).data

    sigfile = open(sigfilename, "w")
    sigfile.write(signature)
    sigfile.close()


def test_sign():
    """Unit test for sign"""

    filename = TESTPATH + "test1.pys"
    sigfilename = filename + ".sig"

    _set_sig(filename, sigfilename)

    valid = gpg.verify(sigfilename, filename)

    assert valid

param_verify = [
    {'filename': TESTPATH + "test1.pys",
     'sigfilename': TESTPATH + "test1.pys.sig", 'valid': 1},
    {'filename': TESTPATH + "test1.pys",
     'sigfilename': TESTPATH + "test1.pys.empty", 'valid': 0},
    {'filename': TESTPATH + "test1.pys",
     'sigfilename': TESTPATH + "test1.pys.nonsense", 'valid': 0},
]


@params(param_verify)
def test_sign_verify(filename, sigfilename, valid):
    """Unit test for verify"""

    if valid:
        assert gpg.verify(sigfilename, filename)
    else:
        assert not gpg.verify(sigfilename, filename)

########NEW FILE########
__FILENAME__ = test_parsers
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------


"""
test_parsers
============

Unit tests for parsers.py

"""

import os
import sys

import wx
app = wx.App()

TESTPATH = os.sep.join(os.path.realpath(__file__).split(os.sep)[:-1]) + os.sep
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 3)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 2)

from src.lib.testlib import params, pytest_generate_tests

from src.lib.parsers import get_font_from_data, get_pen_from_data

param_font = [
    {"fontdata": "Courier New 13", "face": "Courier New", "size": 13},
    {"fontdata": "Arial 43", "face": "Arial", "size": 43},
]


# In Windows, base fonts seem to have no face name
# Therefore, the following test fails
if not "__WXMSW__" in wx.PlatformInfo:

    @params(param_font)
    def test_get_font_from_data(fontdata, face, size):
        """Unit test for get_font_from_data"""

        try:
            font = get_font_from_data(fontdata)
        except:
            # msttcorefonts is missing
            return

        assert font.GetFaceName() == face
        assert font.GetPointSize() == size

param_pen = [
    {"pendata": [wx.RED.GetRGB(), 4], "width": 4,
     "color": wx.Colour(255, 0, 0, 255)},
    {"pendata": [wx.BLUE.GetRGB(), 1], "width": 1,
     "color": wx.Colour(0, 0, 255, 255)},
    {"pendata": [wx.GREEN.GetRGB(), 0], "width": 0,
     "color": wx.Colour(0, 255, 0, 255)},
]


@params(param_pen)
def test_get_pen_from_data(pendata, width, color):
    """Unit test for get_pen_from_data"""

    pen = get_pen_from_data(pendata)

    assert pen.GetColour() == color
    assert pen.GetWidth() == width
########NEW FILE########
__FILENAME__ = test_selection
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------


"""
test_selection
==============

Unit tests for selection.py

"""

import os
import sys

import wx
app = wx.App()

TESTPATH = os.sep.join(os.path.realpath(__file__).split(os.sep)[:-1]) + os.sep
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 3)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 2)

from src.lib.testlib import params, pytest_generate_tests

from src.lib.selection import Selection

from src.gui._main_window import MainWindow


class TestSelection(object):
    """Unit tests for Selection"""

    def setup_method(self, method):
        self.main_window = MainWindow(None, -1)
        self.grid = self.main_window.grid

    param_test_nonzero = [
        {'sel': Selection([], [], [], [], [(32), (34)])},
        {'sel': Selection([], [], [], [], [(32, 53), (34, 56)])},
        {'sel': Selection([], [], [], [3], [])},
        {'sel': Selection([], [], [2], [], [])},
        {'sel': Selection([(1, 43)], [(2, 354)], [], [], [])},
    ]

    @params(param_test_nonzero)
    def test_nonzero(self, sel):
        """Unit test for __nonzero__"""

        assert sel

    def test_repr(self):
        """Unit test for __repr__"""

        selection = Selection([], [], [], [], [(32, 53), (34, 56)])
        assert str(selection) == \
            "Selection([], [], [], [], [(32, 53), (34, 56)])"

    param_test_eq = [
        {'sel1': Selection([], [], [], [], [(32, 53), (34, 56)]),
         'sel2': Selection([], [], [], [], [(32, 53), (34, 56)]),
         'res': True},
        {'sel1': Selection([], [], [], [], [(32, 53)]),
         'sel2': Selection([], [], [], [], [(32, 53), (34, 56)]),
         'res': False},
        {'sel1': Selection([], [], [], [], [(34, 56), (32, 53)]),
         'sel2': Selection([], [], [], [], [(32, 53), (34, 56)]),
         'res': False},
        {'sel1': Selection([], [], [3, 5], [1, 4], [(32, 53)]),
         'sel2': Selection([], [], [5, 3], [1, 4], [(32, 53)]),
         'res': False},
        {'sel1': Selection([], [], [3, 5], [1, 4], [(32, 2343)]),
         'sel2': Selection([], [], [5, 3], [1, 4], [(32, 53)]),
         'res': False},
        {'sel1': Selection([(2, 3), (9, 10)], [(5, 9), (100, 34)], [], [], []),
         'sel2': Selection([(2, 3), (9, 10)], [(5, 9), (100, 34)], [], [], []),
         'res': True},
        {'sel1': Selection([(9, 10), (2, 3)], [(100, 34), (5, 9)], [], [], []),
         'sel2': Selection([(2, 3), (9, 10)], [(5, 9), (100, 34)], [], [], []),
         'res': False},
    ]

    @params(param_test_eq)
    def test_eq(self, sel1, sel2, res):
        """Unit test for __eq__"""

        assert (sel1 == sel2) == res
        assert (sel2 == sel1) == res

    param_test_contains = [
        # Cell selections
        {'sel': Selection([], [], [], [], [(32, 53), (34, 56)]),
         'key': (32, 53), 'res': True},
        {'sel': Selection([], [], [], [], [(32, 53), (34, 56)]),
         'key': (23, 34534534), 'res': False},
        # Block selections
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'key': (4, 5), 'res': True},
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'key': (99, 199), 'res': True},
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'key': (100, 200), 'res': True},
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'key': (0, 0), 'res': False},
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'key': (0, 1), 'res': False},
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'key': (1, 0), 'res': False},
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'key': (4, 4), 'res': False},
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'key': (3, 5), 'res': False},
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'key': (100, 201), 'res': False},
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'key': (10**10, 10**10), 'res': False},
        # Row selection
        {'sel': Selection([], [], [3], [], []),
         'key': (0, 0), 'res': False},
        {'sel': Selection([], [], [3], [], []),
         'key': (3, 0), 'res': True},
        {'sel': Selection([], [], [3, 5], [], []),
         'key': (3, 0), 'res': True},
        {'sel': Selection([], [], [3, 5], [], []),
         'key': (5, 0), 'res': True},
        {'sel': Selection([], [], [3, 5], [], []),
         'key': (4, 0), 'res': False},
        # Column selection
        {'sel': Selection([], [], [], [2, 234, 434], []),
         'key': (234, 234), 'res': True},
        {'sel': Selection([], [], [], [2, 234, 434], []),
         'key': (234, 0), 'res': False},
        # Combinations
        {'sel': Selection([(0, 0)], [(90, 23)], [0], [0, 34], [((0, 0))]),
         'key': (0, 0), 'res': True},
    ]

    @params(param_test_contains)
    def test_contains(self, sel, key, res):
        """Unit test for __contains__

        Used in: ele in selection

        """

        assert (key in sel) == res

    param_test_add = [
        {'sel': Selection([], [], [], [], [(0, 0), (34, 56)]),
         'add': (4, 5),
         'res': Selection([], [], [], [], [(4, 5), (38, 61)])},
        {'sel': Selection([], [], [], [], [(0, 0), (34, 56)]),
         'add': (0, 0),
         'res': Selection([], [], [], [], [(0, 0), (34, 56)])},
        {'sel': Selection([], [], [], [], [(0, 0), (34, 56)]),
         'add': (-3, -24),
         'res': Selection([], [], [], [], [(-3, -24), (31, 32)])},
        {'sel': Selection([(2, 5)], [(4, 6)], [1], [0], [(0, 0), (34, 56)]),
         'add': (1, 0),
         'res': Selection([(3, 5)], [(5, 6)], [2], [0], [(1, 0), (35, 56)])},
    ]

    @params(param_test_add)
    def test_add(self, sel, add, res):
        """Unit test for __add__"""

        val = sel + add
        assert val == res

    param_test_insert = [
        {'sel': Selection([], [], [2], [], []),
         'point': 1, 'number': 10, 'axis': 0,
         'res': Selection([], [], [12], [], [])},
        {'sel': Selection([], [], [], [], [(234, 23)]),
         'point': 20, 'number': 4, 'axis': 1,
         'res': Selection([], [], [], [], [(234, 27)])},
        {'sel': Selection([], [], [21], [33, 44], [(234, 23)]),
         'point': 40, 'number': 4, 'axis': 1,
         'res': Selection([], [], [21], [33, 48], [(234, 23)])},
    ]

    @params(param_test_insert)
    def test_insert(self, sel, point, number, axis, res):
        """Unit test for insert"""

        sel.insert(point, number, axis)
        assert sel == res

    param_test_get_bbox = [
        {'sel': Selection([], [], [], [], [(32, 53), (34, 56)]),
         'res': ((32, 53), (34, 56))},
        {'sel': Selection([(4, 5)], [(100, 200)], [], [], []),
         'res': ((4, 5), (100, 200))},
    ]

    @params(param_test_get_bbox)
    def test_get_bbox(self, sel, res):
        """Unit test for get_bbox"""

        assert sel.get_bbox() == res

    param_get_access_string = [
        {'sel': Selection([], [], [], [], [(32, 53), (34, 56)]),
         'shape': (1000, 100, 3), 'table': 0,
         'res': "[S[key] for key in [(32, 53, 0)] + [(34, 56, 0)] "
                "if S[key] is not None]"},
        {'sel': Selection([], [], [4, 5], [53], []),
         'shape': (1000, 100, 3), 'table': 2,
         'res': "[S[key] for key in [(4, c, 2) for c in xrange(100)] + "
                "[(5, c, 2) for c in xrange(100)] + [(r, 53, 2) for r in "
                "xrange(1000)] if S[key] is not None]"},
        {'sel': Selection([(0, 0), (2, 2)], [(1, 1), (7, 5)], [], [], []),
         'shape': (1000, 100, 3), 'table': 0,
         'res': "[S[key] for key in [(r, c, 0) for r in xrange(0, 2) for c in "
                "xrange(0, 2)] + [(r, c, 0) for r in xrange(2, 8) for c in "
                "xrange(2, 6)] if S[key] is not None]"},
    ]

    @params(param_get_access_string)
    def test_get_access_string(self, sel, shape, table, res):
        """Unit test for get_access_string"""

        assert sel.get_access_string(shape, table) == res

    param_test_shifted = [
        {'sel': Selection([], [], [], [], [(32, 53), (34, 56)]),
         'rows': 0, 'cols': 0,
         'res': Selection([], [], [], [], [(32, 53), (34, 56)])},
        {'sel': Selection([], [], [], [], [(32, 53), (34, 56)]),
         'rows': 1, 'cols': 1,
         'res': Selection([], [], [], [], [(33, 54), (35, 57)])},
        {'sel': Selection([], [], [], [], [(32, 53), (34, 56)]),
         'rows': -1, 'cols': 0,
         'res': Selection([], [], [], [], [(31, 53), (33, 56)])},
        {'sel': Selection([], [], [], [], [(32, 53), (34, 56)]),
         'rows': -1, 'cols': -1,
         'res': Selection([], [], [], [], [(31, 52), (33, 55)])},
        {'sel': Selection([], [], [], [], [(32, 53), (34, 56)]),
         'rows': -1, 'cols': 1,
         'res': Selection([], [], [], [], [(31, 54), (33, 57)])},
        {'sel': Selection([], [], [], [], [(32, 53), (34, 56)]),
         'rows': -100, 'cols': 100,
         'res': Selection([], [], [], [], [(-68, 153), (-66, 156)])},
        {'sel': Selection([(0, 0), (1, 1)], [(10, 10), (50, 50)], [], [], []),
         'rows': 1, 'cols': 0,
         'res': Selection([(1, 0), (2, 1)], [(11, 10), (51, 50)], [], [], [])},
        {'sel': Selection([], [], [1, 4, 6], [3, 4], []),
         'rows': 2, 'cols': 1,
         'res': Selection([], [], [3, 6, 8], [4, 5], [])},
    ]

    @params(param_test_shifted)
    def test_shifted(self, sel, rows, cols, res):
        """Unit test for shifted"""

        assert sel.shifted(rows, cols) == res

    param_test_grid_select = [
        {'sel': Selection([], [], [], [], [(1, 0), (2, 0)]),
         'key': (1, 0), 'res': True},
        {'sel': Selection([], [], [], [], [(1, 0), (2, 0)]),
         'key': (0, 0), 'res': False},
        {'sel': Selection([], [], [1, 2], [], []),
         'key': (0, 0), 'res': False},
        {'sel': Selection([], [], [1, 2], [], []),
         'key': (1, 0), 'res': True},
        {'sel': Selection([], [], [], [3], []),
         'key': (0, 3), 'res': True},
        {'sel': Selection([], [], [], [3], []),
         'key': (0, 0), 'res': False},
        {'sel': Selection([(0, 0)], [(2, 2)], [], [], []),
         'key': (1, 1), 'res': True},
    ]

    @params(param_test_grid_select)
    def test_grid_select(self, sel, key, res):
        """Unit test for grid_select"""

        sel.grid_select(self.grid)
        assert self.grid.IsInSelection(*key) == res


########NEW FILE########
__FILENAME__ = test_typechecks
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit test for typechecks.py"""

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Foobar.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

import os
import sys

import wx
app = wx.App()

TESTPATH = os.sep.join(os.path.realpath(__file__).split(os.sep)[:-1]) + os.sep
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 3)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 2)

from src.lib.testlib import params, pytest_generate_tests

from src.lib.typechecks import is_slice_like, is_string_like, is_generator_like

param_slc = [
    {"slc": slice(None, None, None), "res": True},
    {"slc": slice(None, 4, 34), "res": True},
    {"slc": -2, "res": False},
    {"slc": [1, 2, 3], "res": False},
    {"slc": (1, 2, 3), "res": False},
    {"slc": {}, "res": False},
    {"slc": None, "res": False},
]


@params(param_slc)
def test_is_slice_like(slc, res):
    """Unit test for is_slice_like"""

    assert is_slice_like(slc) == res

param_str = [
    {"string": "", "res": True},
    {"string": u"", "res": True},
    {"string": "Test", "res": True},
    {"string": u"x" * 1000, "res": True},
    {"string": ['1'], "res": False},
    {"string": ('1', '2', '3'), "res": False},
    {"string": {None: '3'}, "res": False},
    {"string": None, "res": False},
]


@params(param_str)
def test_is_string_like(string, res):
    """Unit test for is_string_like"""

    assert is_string_like(string) == res

param_gen = [
    {"gen": (i for i in [3, 4]), "res": True},
    {"gen": (str(i) for i in xrange(1000)), "res": True},
    {"gen": ((2, 3) for _ in xrange(10)), "res": True},
    {"gen": u"x" * 1000, "res": False},
    {"gen": ['1'], "res": False},
    {"gen": ('1', '2', '3'), "res": False},
    {"gen": {None: '3'}, "res": False},
    {"gen": None, "res": False},
]


@params(param_gen)
def test_is_generator_like(gen, res):
    """Unit test for is_generator_like"""

    assert is_generator_like(gen) == res

########NEW FILE########
__FILENAME__ = test_xrect
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------


"""
test_xrect
==========

Unit tests for xrect.py

"""

from math import sin, cos, pi
import os
import sys

import numpy

TESTPATH = os.sep.join(os.path.realpath(__file__).split(os.sep)[:-1]) + os.sep
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 3)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 2)

import src.lib.xrect as xrect


# test support code
def params(funcarglist):
    def wrapper(function):
        function.funcarglist = funcarglist
        return function
    return wrapper


def pytest_generate_tests(metafunc):
    for funcargs in getattr(metafunc.function, 'funcarglist', ()):
        metafunc.addcall(funcargs=funcargs)

# Actual test code
# ----------------


class TestRect(object):
    """Unit tests for Rect"""

    param_comb_get_bbox = [
        {'x': 0, 'y': 0, 'w': 1, 'h': 1},
        {'x': 0, 'y': 1, 'w': 1, 'h': 1},
        {'x': 1, 'y': 0, 'w': 1, 'h': 1},
        {'x': 10, 'y': 10, 'w': 1, 'h': 1},
        {'x': 10, 'y': 10, 'w': 0, 'h': 0},
        {'x': 10, 'y': 10, 'w': 11, 'h': 11},
        {'x': 10, 'y': 10, 'w': 111, 'h': 21},
        {'x': 1234230, 'y': 1234320, 'w': 134, 'h': 23423423},
    ]

    @params(param_comb_get_bbox)
    def test_get_bbox(self, x, y, w, h):
        rect = xrect.Rect(x, y, w, h)
        assert rect.get_bbox() == (x, x + w, y, y + h)

    param_comb_collides = [
        {'x1': 0, 'y1': 0, 'w1': 1, 'h1': 1,
         'x2': 0, 'y2': 0, 'w2': 1, 'h2': 1, 'collision': True},
    ]

    @params(param_comb_collides)
    def test_is_bbox_not_intersecting(self, x1, y1, w1, h1,
                                      x2, y2, w2, h2, collision):
        rect1 = xrect.Rect(x1, y1, w1, h1)
        rect2 = xrect.Rect(x2, y2, w2, h2)

        assert rect1.is_bbox_not_intersecting(rect2) != collision

    @params(param_comb_collides)
    def test_collides(self, x1, y1, w1, h1,
                      x2, y2, w2, h2, collision):
        rect1 = xrect.Rect(x1, y1, w1, h1)
        rect2 = xrect.Rect(x2, y2, w2, h2)

        assert rect1.collides(rect2) == collision


class TestRotoOriginRect(object):
    """Unit tests for RotoOriginRect"""

    param_comb_get_bbox = [ \
        {'w': 1, 'h': 1, 'angle': 0},
        {'w': 0, 'h': 0, 'angle': 0},
        {'w': 10, 'h': 10, 'angle': 0},
        {'w': 10, 'h': 20, 'angle': 0},
        {'w': 10, 'h': 10, 'angle': 10},
        {'w': 20, 'h': 10, 'angle': 10},
        {'w': 45, 'h': 45, 'angle': 45},
        {'w': 210, 'h': 10, 'angle': 78},
        {'w': 2310, 'h': 2310, 'angle': 230},
        {'w': 110, 'h': 2310, 'angle': -20},
        {'w': 10, 'h': 10, 'angle': 121231320},
    ]

    @params(param_comb_get_bbox)
    def test_get_bbox(self, w, h, angle):
        rect = xrect.RotoOriginRect(w, h, angle)

        rad_angle = angle / 180.0 * pi

        bbox_from_method = rect.get_bbox()

        trafo = numpy.matrix([cos(rad_angle), -sin(rad_angle),
                             sin(rad_angle), cos(rad_angle)]).reshape(2, 2)

        points = [numpy.array([-w / 2.0, -h / 2.0]).reshape(2, 1),
                  numpy.array([-w / 2.0, h / 2.0]).reshape(2, 1),
                  numpy.array([w / 2.0, h / 2.0]).reshape(2, 1),
                  numpy.array([w / 2.0, -h / 2.0]).reshape(2, 1)]

        p_rots = [trafo * point for point in points]

        bbox_x_min = float(min(p_rot[0] for p_rot in p_rots))
        bbox_x_max = float(max(p_rot[0] for p_rot in p_rots))
        bbox_y_min = float(min(p_rot[1] for p_rot in p_rots))
        bbox_y_max = float(max(p_rot[1] for p_rot in p_rots))

        bbox_calculated = bbox_x_min, bbox_x_max, bbox_y_min, bbox_y_max

        for b1, b2 in zip(bbox_from_method, bbox_calculated):
            print b1, b2
            assert abs(b1 - b2) < 1.0E-10

    param_comb_rotoorigin_collide = [
        # Identity
        {'x': -10, 'y': -5, 'w': 20, 'h': 10, 'angle': 0, 'res': True},
        # Move x
        {'x': -40, 'y': -5, 'w': 20, 'h': 10, 'angle': 0, 'res': False},
        {'x': -31, 'y': 0, 'w': 20, 'h': 10, 'angle': 0, 'res': False},
        {'x': -30, 'y': 0, 'w': 20, 'h': 10, 'angle': 0, 'res': True},
        {'x': 0, 'y': 0, 'w': 20, 'h': 10, 'angle': 0, 'res': True},
        {'x': 9, 'y': 0, 'w': 20, 'h': 10, 'angle': 0, 'res': True},
        {'x': 10, 'y': 0, 'w': 20, 'h': 10, 'angle': 0, 'res': True},
        {'x': 11, 'y': 0, 'w': 20, 'h': 10, 'angle': 0, 'res': False},
        {'x': 20, 'y': 0, 'w': 20, 'h': 10, 'angle': 0, 'res': False},
        # Move y
        {'x': -10, 'y': -20, 'w': 20, 'h': 10, 'angle': 0, 'res': False},
        {'x': -10, 'y': -16, 'w': 20, 'h': 10, 'angle': 0, 'res': False},
        {'x': -10, 'y': -15, 'w': 20, 'h': 10, 'angle': 0, 'res': True},
        {'x': -10, 'y': 4, 'w': 20, 'h': 10, 'angle': 0, 'res': True},
        {'x': -10, 'y': 5, 'w': 20, 'h': 10, 'angle': 0, 'res': True},
        {'x': -10, 'y': 6, 'w': 20, 'h': 10, 'angle': 0, 'res': False},
        {'x': -10, 'y': 10, 'w': 20, 'h': 10, 'angle': 0, 'res': False},
        # Move x and y
        {'x': -40, 'y': -20, 'w': 20, 'h': 10, 'angle': 0, 'res': False},
        {'x': -31, 'y': -16, 'w': 20, 'h': 10, 'angle': 0, 'res': False},
        {'x': -30, 'y': -15, 'w': 20, 'h': 10, 'angle': 0, 'res': True},
        {'x': 10, 'y': 5, 'w': 20, 'h': 10, 'angle': 0, 'res': True},
        {'x': 11, 'y': 6, 'w': 20, 'h': 10, 'angle': 0, 'res': False},
        # Move size
        {'x': -100, 'y': -50, 'w': 200, 'h': 100, 'angle': 0, 'res': True},
        {'x': -1, 'y': -0.5, 'w': 2, 'h': 1, 'angle': 0, 'res': True},
        {'x': -1, 'y': -0.5, 'w': 0, 'h': 0, 'angle': 0, 'res': True},
        # Move angle
        {'x': -10, 'y': -5, 'w': 20, 'h': 10, 'angle': 0.1, 'res': True},
        {'x': -10, 'y': -5, 'w': 20, 'h': 10, 'angle': 1, 'res': True},
        {'x': -10, 'y': -5, 'w': 20, 'h': 10, 'angle': 45.0, 'res': True},
        {'x': -10, 'y': -5, 'w': 20, 'h': 10, 'angle': -90.0, 'res': True},
        # Move angle and x
        {'x': -50, 'y': -5, 'w': 20, 'h': 10, 'angle': -0.1, 'res': False},
        {'x': -50, 'y': -5, 'w': 20, 'h': 10, 'angle': 0.1, 'res': False},
        {'x': -50, 'y': -5, 'w': 20, 'h': 10, 'angle': 1.0, 'res': False},
        {'x': -50, 'y': -5, 'w': 20, 'h': 10, 'angle': 90, 'res': False},
        {'x': 50, 'y': -5, 'w': 20, 'h': 10, 'angle': -0.1, 'res': False},
        {'x': 50, 'y': -5, 'w': 20, 'h': 10, 'angle': 0.1, 'res': False},
        {'x': 50, 'y': -5, 'w': 20, 'h': 10, 'angle': 1.0, 'res': False},
        # Move angle and size
        {'x': -20, 'y': -10, 'w': 40, 'h': 20, 'angle': 45.0, 'res': True},
        {'x': 8, 'y': 5, 'w': 2, 'h': 2, 'angle': -1.0, 'res': False},
        {'x': 8, 'y': 5, 'w': 2, 'h': 2, 'angle': 1.0, 'res': True},
    ]

    @params(param_comb_rotoorigin_collide)
    def test_rotoorigin_collide(self, x, y, w, h, angle, res):

        base_rect = xrect.RotoOriginRect(20, 10, angle)
        clash_rect = xrect.Rect(x, y, w, h)

        assert base_rect.collides(clash_rect) == res


class TestRotoRect(object):
    """Unit tests for RotoRect"""

    param_get_center = [
        {'x': 0, 'y': 0, 'w': 20, 'h': 10, 'angle': 0, 'res': (10, 5)},
        {'x': 50, 'y': 0, 'w': 20, 'h': 10, 'angle': 0, 'res': (60, 5)},
        {'x': 50, 'y': 0, 'w': 20, 'h': 10, 'angle': 90, 'res': (55, -10)},
        {'x': 50, 'y': 0, 'w': 20, 'h': 10, 'angle': 270, 'res': (45, 10)},
    ]

    @params(param_get_center)
    def test_get_center(self, x, y, w, h, angle, res):
        rect = xrect.RotoRect(x, y, w, h, angle)
        center = rect.get_center()
        assert map(round, center) == map(round, res)

    param_get_edges = [
        {'x': 0, 'y': 0, 'w': 20, 'h': 10, 'angle': 0,
         'res': ((0, 0), (20, 0), (0, 10), (20, 10))},
        {'x': 50, 'y': 0, 'w': 20, 'h': 10, 'angle': 0,
         'res': ((50, 0), (70, 0), (50, 10), (70, 10))},
        {'x': 50, 'y': 0, 'w': 20, 'h': 10, 'angle': 90,
         'res': ((50, 0), (50, -20), (60, 0), (60, -20))},
    ]

    @params(param_get_edges)
    def test_get_edges(self, x, y, w, h, angle, res):
        rect = xrect.RotoRect(x, y, w, h, angle)
        edges = rect.get_edges()
        for edge, resele in zip(edges, res):
            assert map(round, edge) == map(round, resele)

    param_collides_axisaligned_rect = [
        # Identity
        {'x': 0, 'y': 0, 'w': 20, 'h': 10, 'angle': 0,
         'x1': -10, 'y1': -5, 'w1': 20, 'h1': 10, 'res': True},
        # Shifted
        {'x': 50, 'y': 0, 'w': 20, 'h': 10, 'angle': 0,
         'x1': -10, 'y1': -5, 'w1': 20, 'h1': 10, 'res': False},
        # Shifted and rotated
        {'x': 50, 'y': 0, 'w': 20, 'h': 10, 'angle': 30,
         'x1': -10, 'y1': -5, 'w1': 20, 'h1': 10, 'res': False},
        {'x': 50, 'y': 0, 'w': 20, 'h': 10, 'angle': 30,
         'x1': -10, 'y1': -5, 'w1': 100, 'h1': 10, 'res': True},
    ]

    @params(param_collides_axisaligned_rect)
    def test_collides_axisaligned_rect(self, x, y, w, h, angle,
                                       x1, y1, w1, h1, res):
        base_rect = xrect.RotoRect(x, y, w, h, angle)
        clash_rect = xrect.Rect(x1, y1, w1, h1)

        assert base_rect.collides(clash_rect) == res

########NEW FILE########
__FILENAME__ = testlib
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
testlib.py
==========

Helper functions for unit tests

"""

import wx

# Standard grid values for initial filling

grid_values = { \
    (0, 0, 0): "'Test'",
    (999, 0, 0): "1",
    (999, 99, 0): "$^%&$^",
    (0, 1, 0): "1",
    (0, 2, 0): "2",
    (1, 1, 0): "3",
    (1, 2, 0): "4",
    (1, 2, 2): "78",
}

# Helper methods for efficient testing


def _fill_grid(grid, values):
    """Fills grid with values (use e. g. grid_values)"""

    for key in values:
        grid.code_array[key] = values[key]


def restore_basic_grid(grid):
    """Restores basic, filled grid"""

    default_test_shape = (1000, 100, 3)

    grid.actions.clear(default_test_shape)
    _fill_grid(grid, grid_values)


def basic_setup_test(grid, func, test_key, test_val, *args, **kwargs):
    """Sets up basic test env, runs func and tests test_key in grid"""

    restore_basic_grid(grid)

    func(*args, **kwargs)
    grid.code_array.result_cache.clear()
    assert grid.code_array(test_key) == test_val


def params(funcarglist):
    """Test function parameter decorator

    Provides arguments based on the dict funcarglist.

    """

    def wrapper(function):
        function.funcarglist = funcarglist
        return function
    return wrapper


def pytest_generate_tests(metafunc):
    """Enables params to work in py.test environment"""

    for funcargs in getattr(metafunc.function, 'funcarglist', ()):
        metafunc.addcall(funcargs=funcargs)
########NEW FILE########
__FILENAME__ = typechecks
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""

Typechecks
==========

typechecks.py contains functions for checking type likeness,
i. e. existence of typical attributes of a type for objects.

"""


def is_slice_like(obj):
    """Returns True if obj is slice like, i.e. has attribute indices"""

    return hasattr(obj, "indices")


def is_string_like(obj):
    """Returns True if obj is string like, i.e. has method split"""

    return hasattr(obj, "split")


def is_generator_like(obj):
    """Returns True if obj is string like, i.e. has method next"""

    return hasattr(obj, "next")
########NEW FILE########
__FILENAME__ = xrect
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""2D Rectangle collision library"""

from math import sin, cos, pi


class Rect(object):
    """Rectangle class for axis aligned 2D rectangles

    Parameters
    ----------
    x: Number
    \tX-Coordinate of rectangle origin (lower left dot if angle == 0)
    y: Number
    \tY-Coordinate of rectangle origin (lower left dot if angle == 0)
    width: Number
    \tRectangle number
    height: Number
    \tRectangle height

    """

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def __str__(self):
        return "Rect(" + \
               ", ".join(map(str, (self.x, self.y,
                                   self.width, self.height))) + \
               ")"

    def get_bbox(self):
        """Returns bounding box (xmin, xmax, ymin, ymax)"""

        x_min = self.x
        x_max = x_min + self.width
        y_min = self.y
        y_max = self.y + self.height

        return x_min, x_max, y_min, y_max

    def is_bbox_not_intersecting(self, other):
        """Returns False iif bounding boxed of self and other intersect"""

        self_x_min, self_x_max, self_y_min, self_y_max = self.get_bbox()
        other_x_min, other_x_max, other_y_min, other_y_max = other.get_bbox()

        return \
            self_x_min > other_x_max or \
            other_x_min > self_x_max or \
            self_y_min > other_y_max or \
            other_y_min > self_y_max

    def is_point_in_rect(self, pt_x, pt_y):
        """Returns True iif point is inside the rectangle (border included)

        Parameters
        ----------

         * pt_x: Number
        \tx-value of point
         * pt_y: Number
        \ty-value of point

        """

        x_min, x_max, y_min, y_max = self.get_bbox()

        return x_min <= pt_x <= x_max and y_min <= pt_y <= y_max

    def collides(self, other):
        """Returns collision with axis aligned rect"""

        return not self.is_bbox_not_intersecting(other)


class RotoOriginRect(Rect):
    """Rectangle class for origin centered rotated rectangles

    Parameters
    ----------
    width: Number
    \tRectangle number
    height: Number
    \tRectangle height
    angle: Number:
    \tRectangle rotation angle clock-wise around origin

    """

    def __init__(self, width, height, angle):
        Rect.__init__(self, -width / 2.0, -height / 2.0, width, height)
        self.angle = angle / 180.0 * pi

    def __str__(self):
        return "RotoOriginRect(" + \
            ", ".join(map(str, (self.x, self.y,
                                self.width, self.height, self.angle))) + \
            ")"

    def get_bbox(self):
        """Returns bounding box (xmin, xmax, ymin, ymax)"""

        width = self.width
        height = self.height

        cos_angle = cos(self.angle)
        sin_angle = sin(self.angle)

        x_diff = 0.5 * width
        y_diff = 0.5 * height

        # self rotates around (0, 0).
        c_x_diff = cos_angle * x_diff
        s_x_diff = sin_angle * x_diff

        c_y_diff = cos_angle * y_diff
        s_y_diff = sin_angle * y_diff

        if cos_angle > 0:
            if sin_angle > 0:
                x_max = c_x_diff + s_y_diff
                x_min = -x_max
                y_max = c_y_diff + s_x_diff
                y_min = -y_max
            else:  # sin_angle <= 0.0
                x_max = c_x_diff - s_y_diff
                x_min = -x_max
                y_max = c_y_diff - s_x_diff
                y_min = -y_max

        else:  # cos(angle) <= 0.0
            if sin_angle > 0:
                x_min = c_x_diff - s_y_diff
                x_max = -x_min
                y_min = c_y_diff - s_x_diff
                y_max = -y_min
            else:  # sin_angle <= 0.0
                x_min = c_x_diff + s_y_diff
                x_max = -x_min
                y_min = c_y_diff + s_x_diff
                y_max = -y_min

        return x_min, x_max, y_min, y_max

    def is_edge_not_excluding_vertices(self, other):
        """Returns False iif any edge excludes all vertices of other."""

        c_a = cos(self.angle)
        s_a = sin(self.angle)

        # Get min and max of other.

        other_x_min, other_x_max, other_y_min, other_y_max = other.get_bbox()

        self_x_diff = 0.5 * self.width
        self_y_diff = 0.5 * self.height

        if c_a > 0:
            if s_a > 0:
                return \
                    c_a * other_x_max + s_a * other_y_max < -self_x_diff or \
                    c_a * other_x_min + s_a * other_y_min >  self_x_diff or \
                    c_a * other_y_max - s_a * other_x_min < -self_y_diff or \
                    c_a * other_y_min - s_a * other_x_max >  self_y_diff

            else:  # s_a <= 0.0
                return \
                    c_a * other_x_max + s_a * other_y_min < -self_x_diff or \
                    c_a * other_x_min + s_a * other_y_max >  self_x_diff or \
                    c_a * other_y_max - s_a * other_x_max < -self_y_diff or \
                    c_a * other_y_min - s_a * other_x_min >  self_y_diff

        else:  # c_a <= 0.0
            if s_a > 0:
                return \
                    c_a * other_x_min + s_a * other_y_max < -self_x_diff or \
                    c_a * other_x_max + s_a * other_y_min >  self_x_diff or \
                    c_a * other_y_min - s_a * other_x_min < -self_y_diff or \
                    c_a * other_y_max - s_a * other_x_max >  self_y_diff

            else:  # s_a <= 0.0
                return \
                    c_a * other_x_min + s_a * other_y_min < -self_x_diff or \
                    c_a * other_x_max + s_a * other_y_max >  self_x_diff or \
                    c_a * other_y_min - s_a * other_x_max < -self_y_diff or \
                    c_a * other_y_max - s_a * other_x_min >  self_y_diff

    def collides(self, other):
        """Returns collision with axis aligned rect"""

        angle = self.angle
        width = self.width
        height = self.height

        if angle == 0:
            return other.collides(Rect(-0.5 * width,
                                       -0.5 * height, width, height))

        # Phase 1
        #
        #  * Form bounding box on tilted rectangle P.
        #  * Check whether bounding box and other intersect.
        #  * If not, then self and other do not intersect.
        #  * Otherwise proceed to Phase 2.

        # Now perform the standard rectangle intersection test.

        if self.is_bbox_not_intersecting(other):
            return False

        # Phase 2
        #
        # If we get here, check the edges of self to see
        #  * if one of them excludes all vertices of other.
        #  * If so, then self and other do not intersect.
        #  * (If not, then self and other do intersect.)

        return not self.is_edge_not_excluding_vertices(other)


class RotoRect(object):
    """Rectangle class for generic rotated rectangles

    Parameters
    ----------
    x: Number
    \tX-Coordinate of rectangle origin (lower left dot if angle == 0)
    y: Number
    \tY-Coordinate of rectangle origin (lower left dot if angle == 0)
    width: Number
    \tRectangle number
    height: Number
    \tRectangle height
    angle: Number:
    \tRectangle rotation angle counter clock-wise around origin

    """

    def __init__(self, x, y, width, height, angle):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.angle = angle

    def __str__(self):
        return "RotoRect(" + \
            ", ".join(map(str, (self.x, self.y,
                                self.width, self.height, self.angle))) + \
            ")"

    def sin_a(self):
        """Returns sin of rect angle"""

        return sin(self.angle / 180.0 * pi)

    def cos_a(self):
        """Returns cos of rect angle"""

        return cos(self.angle / 180.0 * pi)

    def get_vec_lr(self):
        """Returns vector from left to right"""

        return self.width * self.cos_a(), -self.width * self.sin_a()

    def get_vec_tb(self):
        """Returns vector from top to bottom"""

        return self.height * self.sin_a(), self.height * self.cos_a()


    def get_center(self):
        """Returns rectangle center"""

        lr_x, lr_y = self.get_vec_lr()
        tb_x, tb_y = self.get_vec_tb()

        center_x = self.x + (lr_x + tb_x) / 2.0
        center_y = self.y + (lr_y + tb_y) / 2.0

        return center_x, center_y

    def get_edges(self):
        """Returns 2-tuples for each edge

        top_left
        top_right
        bottom_left
        bottom_right

        """

        lr_x, lr_y = self.get_vec_lr()
        tb_x, tb_y = self.get_vec_tb()

        top_left = self.x, self.y
        top_right = self.x + lr_x, self.y + lr_y
        bottom_left = self.x + tb_x, self.y + tb_y
        bottom_right = self.x + lr_x + tb_x, self.y + lr_y + tb_y

        return top_left, top_right, bottom_left, bottom_right

    def collides_axisaligned_rect(self, other):
        """Returns collision with axis aligned other rect"""

        # Shift both rects so that self is centered at origin

        self_shifted = RotoOriginRect(self.width, self.height, -self.angle)

        s_a = self.sin_a()
        c_a = self.cos_a()

        center_x = self.x + self.width / 2.0 * c_a - self.height / 2.0 * s_a
        center_y = self.y - self.height / 2.0 * c_a - self.width / 2.0 * s_a

        other_shifted = Rect(other.x - center_x, other.y - center_y,
                             other.width, other.height)

        # Calculate collision

        return self_shifted.collides(other_shifted)

    def collides(self, other):
        """Returns collision with other rect"""

        # Is other rect not axis aligned?
        if hasattr(other, "angle"):
            raise NotImplementedError("Non-axis aligned rects not implemented")

        else:  # Other rect is axis aligned
            return self.collides_axisaligned_rect(other)

########NEW FILE########
__FILENAME__ = __csv
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
csvlib
======

Provides
--------

 * sniff: Sniffs CSV dialect and header info
 * get_first_line
 * csv_digest_gen
 * cell_key_val_gen
 * Digest: Converts any object to target type as good as possible
 * CsvInterface
 * TxtGenerator

"""

import ast
import csv
import datetime
import os
import types

import wx

from src.config import config

from src.gui._events import post_command_event, StatusBarEventMixin

import src.lib.i18n as i18n
from src.lib.fileio import AOpen

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


def sniff(filepath):
    """
    Sniffs CSV dialect and header info from csvfilepath

    Returns a tuple of dialect and has_header

    """

    with open(filepath, "rb") as csvfile:
        sample = csvfile.read(config["sniff_size"])

    sniffer = csv.Sniffer()
    dialect = sniffer.sniff(sample)()
    has_header = sniffer.has_header(sample)

    return dialect, has_header


def get_first_line(filepath, dialect):
    """Returns List of first line items of file filepath"""

    with open(filepath, "rb") as csvfile:
        csvreader = csv.reader(csvfile, dialect=dialect)

        for first_line in csvreader:
            break

    return first_line


def digested_line(line, digest_types):
    """Returns list of digested values in line"""

    digested_line = []
    for i, ele in enumerate(line):
        try:
            digest_key = digest_types[i]

        except IndexError:
            digest_key = digest_types[0]

        digest = Digest(acceptable_types=[digest_key])

        try:
            digested_line.append(repr(digest(ele)))

        except Exception:
            digested_line.append("")

    return digested_line


def csv_digest_gen(filepath, dialect, has_header, digest_types):
    """Generator of digested values from csv file in filepath

    Parameters
    ----------
    filepath:String
    \tFile path of csv file to read
    dialect: Object
    \tCsv dialect
    digest_types: tuple of types
    \tTypes of data for each col

    """

    with open(filepath, "rb") as csvfile:
        csvreader = csv.reader(csvfile, dialect=dialect)

        if has_header:
            # Ignore first line
            for line in csvreader:
                break

        for line in csvreader:
            yield digested_line(line, digest_types)


def cell_key_val_gen(iterable, shape, topleft=(0, 0)):
    """Generator of row, col, value tuple from iterable of iterables

    it: Iterable of iterables
    \tMatrix that shall be mapped on target grid
    shape: Tuple of Integer
    \tShape of target grid
    topleft: 2-tuple of Integer
    \tTop left cell for insertion of it

    """

    top, left = topleft

    for __row, line in enumerate(iterable):
        row = top + __row
        if row >= shape[0]:
            break

        for __col, value in enumerate(line):
            col = left + __col
            if col >= shape[1]:
                break

            yield row, col, value


def encode_gen(line, encoding="utf-8"):
    """Encodes all Unicode strings in line to encoding

    Parameters
    ----------
    line: Iterable of Unicode strings
    \tDate to be encoded
    encoding: String, defaults to "utf-8"
    \tTarget encoding

    """

    for ele in line:
        if isinstance(ele, types.UnicodeType):
            yield ele.encode(encoding)
        else:
            yield ele


class Digest(object):
    """
    Maps types to types that are acceptable for target class

    The Digest class handles data of unknown type. Its objects are
    callable. They return an acceptable data type, which may be the fallback
    data type if everything else fails.

    The Digest class is intended to be subclassed by the target class.

    Parameters:
    -----------

    acceptable_types: list of types, defaults to None
    \tTypes that are acceptable for the target_class.
    \tThey are ordered highest preference first
    \tIf None, the string representation of the object is returned

    fallback_type: type, defaults to types.UnicodeType
    \t

    """

    def __init__(self, acceptable_types=None, fallback_type=None,
                 encoding="utf-8"):

        if acceptable_types is None:
            acceptable_types = [None]

        self.acceptable_types = acceptable_types
        self.fallback_type = fallback_type
        self.encoding = encoding

        # Type conversion functions

        def make_string(obj):
            """Makes a string object from any object"""

            if type(obj) is types.StringType:
                return obj

            if obj is None:
                return ""
            try:
                return str(obj)

            except Exception:
                return repr(obj)

        def make_unicode(obj):
            """Makes a unicode object from any object"""

            if type(obj) is types.UnicodeType:
                return obj

            elif isinstance(obj, types.StringType):
                # Try UTF-8
                return obj.decode(self.encoding)

            if obj is None:
                return u""

            try:
                return unicode(obj)

            except Exception:
                return repr(obj)

        def make_slice(obj):
            """Makes a slice object from slice or int"""

            if isinstance(obj, slice):
                return obj

            try:
                return slice(obj, obj + 1, None)

            except Exception:
                return None

        def make_date(obj):
            """Makes a date from comparable types"""

            from dateutil.parser import parse

            try:
                return parse(obj).date()

            except Exception:
                return None

        def make_datetime(obj):
            """Makes a datetime from comparable types"""

            from dateutil.parser import parse

            try:
                return parse(obj)

            except Exception:
                return None

        def make_time(obj):
            """Makes a time from comparable types"""

            from dateutil.parser import parse

            try:
                return parse(obj).time()

            except Exception:
                return None

        def make_object(obj):
            """Returns the object"""
            try:
                return ast.literal_eval(obj)

            except Exception:
                return None

        self.typehandlers = {
            None: repr,
            types.StringType: make_string,
            types.UnicodeType: make_unicode,
            types.SliceType: make_slice,
            types.BooleanType: bool,
            types.ObjectType: make_object,
            types.IntType: int,
            types.FloatType: float,
            types.CodeType: make_object,
            datetime.date: make_date,
            datetime.datetime: make_datetime,
            datetime.time: make_time,
        }

        if self.fallback_type is not None and \
           self.fallback_type not in self.typehandlers:

            err_msg = _("Fallback type {type} unknown.").\
                format(type=str(self.fallback_type))

            raise NotImplementedError(err_msg)

    def __call__(self, orig_obj):
        """Returns acceptable object"""

        errormessage = ""

        type_found = False

        for target_type in self.acceptable_types:
            if target_type in self.typehandlers:
                type_found = True
                break
        if not type_found:
            target_type = self.fallback_type

        try:
            acceptable_obj = self.typehandlers[target_type](orig_obj)
            return acceptable_obj
        except TypeError, err:
            errormessage += str(err)

        try:
            acceptable_obj = self.typehandlers[self.fallback_type](orig_obj)
            return acceptable_obj
        except TypeError, err:
            errormessage += str(err)

        return errormessage

# end of class Digest


class CsvInterface(StatusBarEventMixin):
    """CSV interface class

    Provides
    --------
     * __iter__: CSV reader - generator of generators of csv data cell content
     * write: CSV writer

    """

    def __init__(self, main_window, path, dialect, digest_types, has_header,
                 encoding='utf-8'):
        self.main_window = main_window
        self.path = path
        self.csvfilename = os.path.split(path)[1]

        self.dialect = dialect
        self.digest_types = digest_types
        self.has_header = has_header

        self.encoding = encoding

        self.first_line = False

    def __iter__(self):
        """Generator of generators that yield csv data"""

        with AOpen(self.path, "rb", main_window=self.main_window) as csv_file:
            csv_reader = csv.reader(csv_file, self.dialect)

            self.first_line = self.has_header

            for line in csv_reader:
                yield self._get_csv_cells_gen(line)
                break

            self.first_line = False

            for line in csv_reader:
                yield self._get_csv_cells_gen(line)

        msg = _("File {filename} imported successfully.").format(
            filename=self.csvfilename)
        post_command_event(self.main_window, self.StatusBarMsg, text=msg)

    def _get_csv_cells_gen(self, line):
        """Generator of values in a csv line"""

        digest_types = self.digest_types

        for j, value in enumerate(line):
            if self.first_line:
                digest_key = None
                digest = lambda x: x.decode(self.encoding)
            else:
                try:
                    digest_key = digest_types[j]
                except IndexError:
                    digest_key = digest_types[0]

                digest = Digest(acceptable_types=[digest_key],
                                encoding=self.encoding)

            try:
                digest_res = digest(value)

                if digest_res == "\b":
                    digest_res = None

                elif digest_key is not types.CodeType:
                    digest_res = repr(digest_res)

            except Exception:
                digest_res = ""

            yield digest_res

    def write(self, iterable):
        """Writes values from iterable into CSV file"""

        io_error_text = _("Error writing to file {filepath}.")
        io_error_text = io_error_text.format(filepath=self.path)

        try:

            with open(self.path, "wb") as csvfile:
                csv_writer = csv.writer(csvfile, self.dialect)

                for line in iterable:
                    csv_writer.writerow(
                        list(encode_gen(line, encoding=self.encoding)))

        except IOError:
            txt = \
                _("Error opening file {filepath}.").format(filepath=self.path)
            try:
                post_command_event(self.main_window, self.StatusBarMsg,
                                   text=txt)
            except TypeError:
                # The main window does not exist any more
                pass

            return False


class TxtGenerator(StatusBarEventMixin):
    """Generator of generators of Whitespace separated txt file cell content"""

    def __init__(self, main_window, path):
        self.main_window = main_window
        try:
            self.infile = open(path)

        except IOError:
            statustext = "Error opening file " + path + "."
            post_command_event(self.main_window, self.StatusBarMsg,
                               text=statustext)
            self.infile = None

    def __iter__(self):

        # If self.infile is None then stopiteration is reached immediately
        if self.infile is None:
            return

        for line in self.infile:
            yield (col for col in line.split())

        self.infile.close()

########NEW FILE########
__FILENAME__ = model
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""

Model
=====

The model contains the core data structures of pyspread.
It is divided into layers.

Layer 3: CodeArray
Layer 2: DataArray
Layer 1: DictGrid
Layer 0: KeyValueStore

"""

import ast
import base64
import bz2
from copy import copy
import cStringIO
import datetime
from itertools import imap, ifilter, product
import re
import sys
from types import SliceType, IntType

import numpy

import wx

from src.config import config

from src.lib.typechecks import is_slice_like, is_string_like, is_generator_like
from src.lib.selection import Selection

import src.lib.charts as charts

from src.sysvars import get_color, get_font_string

from unredo import UnRedo


class KeyValueStore(dict):
    """Key-Value store in memory. Currently a dict with default value None.

    This class represents layer 0 of the model.

    """

    def __missing__(self, value):
        """Returns the default value None"""

        return

# End of class KeyValueStore

# -----------------------------------------------------------------------------


class CellAttributes(list):
    """Stores cell formatting attributes in a list of 3 - tuples

    The first element of each tuple is a Selection.
    The second element is the table
    The third element is a dict of attributes that are altered.

    The class provides attribute read access to single cells via __getitem__
    Otherwise it behaves similar to a list.

    Note that for the method undoable_append to work, unredo has to be
    defined as class attribute.

    """

    default_cell_attributes = {
        "borderwidth_bottom": 1,
        "borderwidth_right": 1,
        "bordercolor_bottom": get_color(config["grid_color"]).GetRGB(),
        "bordercolor_right": get_color(config["grid_color"]).GetRGB(),
        "bgcolor": get_color(config["background_color"]).GetRGB(),
        "textfont": get_font_string(config["font"]),
        "pointsize": 10,
        "fontweight": wx.NORMAL,
        "fontstyle": wx.NORMAL,
        "textcolor": get_color(config["text_color"]).GetRGB(),
        "underline": False,
        "strikethrough": False,
        "locked": False,
        "angle": 0.0,
        "column-width": 150,
        "row-height": 26,
        "vertical_align": "top",
        "justification": "left",
        "frozen": False,
        "merge_area": None,
    }

    # Cache for __getattr__ maps key to tuple of len and attr_dict

    _attr_cache = {}

    def undoable_append(self, value, mark_unredo=True):
        """Appends item to list and provides undo and redo functionality"""

        undo_operation = (self.pop, [])
        redo_operation = (self.undoable_append, [value, mark_unredo])

        self.unredo.append(undo_operation, redo_operation)

        if mark_unredo:
            self.unredo.mark()

        self.append(value)
        self._attr_cache.clear()

    def __getitem__(self, key):
        """Returns attribute dict for a single key"""

        assert not any(type(key_ele) is SliceType for key_ele in key)

        if key in self._attr_cache:
            cache_len, cache_dict = self._attr_cache[key]

            # Use cache result only if no new attrs have been defined
            if cache_len == len(self):
                return cache_dict

        row, col, tab = key

        result_dict = copy(self.default_cell_attributes)

        for selection, table, attr_dict in self:
            if tab == table and (row, col) in selection:
                result_dict.update(attr_dict)

        # Upddate cache with current length and dict
        self._attr_cache[key] = (len(self), result_dict)

        return result_dict

    def get_merging_cell(self, key):
        """Returns key of cell that merges the cell key

        or None if cell key not merged

        Parameters
        ----------
        key: 3-tuple of Integer
        \tThe key of the cell that is merged

        """

        row, col, tab = key

        merging_cell = None

        def is_in_merge_area(row, col, merge_area):
            top, left, bottom, right = merge_area
            return top <= row <= bottom and left <= col <= right

        for selection, table, attr_dict in self:
            try:
                merge_area = attr_dict["merge_area"]
                if table == tab and merge_area is not None:
                    # We have a merge area in the cell's table
                    if is_in_merge_area(row, col, merge_area):
                        merging_cell = merge_area[0], merge_area[1], tab
            except KeyError:
                pass

        return merging_cell

    # Allow getting and setting elements in list
    get_item = list.__getitem__
    set_item = list.__setitem__

# End of class CellAttributes


class DictGrid(KeyValueStore):
    """The core data class with all information that is stored in a pys file.

    Besides grid code access via standard dict operations, it provides
    the following attributes:

    * cell_attributes: Stores cell formatting attributes
    * macros:          String of all macros

    This class represents layer 1 of the model.

    Parameters
    ----------
    shape: n-tuple of integer
    \tShape of the grid

    """

    def __init__(self, shape):
        KeyValueStore.__init__(self)

        self.shape = shape

        self.cell_attributes = CellAttributes()

        self.macros = u""

        self.row_heights = {}  # Keys have the format (row, table)
        self.col_widths = {}  # Keys have the format (col, table)

    def __getitem__(self, key):

        shape = self.shape

        for axis, key_ele in enumerate(key):
            if shape[axis] <= key_ele or key_ele < -shape[axis]:
                msg = "Grid index {key} outside grid shape {shape}."
                msg = msg.format(key=key, shape=shape)
                raise IndexError(msg)

        return KeyValueStore.__getitem__(self, key)

# End of class DictGrid

# -----------------------------------------------------------------------------


class DataArray(object):
    """DataArray provides enhanced grid read/write access.

    Enhancements comprise:
     * Slicing
     * Multi-dimensional operations such as insertion and deletion along 1 axis
     * Undo/redo operations

    This class represents layer 2 of the model.

    Parameters
    ----------
    shape: n-tuple of integer
    \tShape of the grid

    """

    def __init__(self, shape):
        self.dict_grid = DictGrid(shape)

        # Undo and redo management
        self.unredo = UnRedo()
        self.dict_grid.cell_attributes.unredo = self.unredo

        # Safe mode
        self.safe_mode = False

    # Data is the central content interface for loading / saving data.
    # It shall be used for loading and saving from and to pys and other files.
    # It shall be used for loading and saving macros.
    # It is not used for importinf and exporting data because these operations
    # are partial to the grid.

    def _get_data(self):
        """Returns dict of data content.

        Keys
        ----

        shape: 3-tuple of Integer
        \tGrid shape
        grid: Dict of 3-tuples to strings
        \tCell content
        attributes: List of 3-tuples
        \tCell attributes
        row_heights: Dict of 2-tuples to float
        \t(row, tab): row_height
        col_widths: Dict of 2-tuples to float
        \t(col, tab): col_width
        macros: String
        \tMacros from macro list

        """

        data = {}

        data["shape"] = self.shape
        data["grid"] = {}.update(self.dict_grid)
        data["attributes"] = [ca for ca in self.cell_attributes]
        data["row_heights"] = self.row_heights
        data["col_widths"] = self.col_widths
        data["macros"] = self.macros

        return data

    def _set_data(self, **kwargs):
        """Sets data from given parameters

        Old values are deleted.
        If a paremeter is not given, nothing is changed.

        Parameters
        ----------

        shape: 3-tuple of Integer
        \tGrid shape
        grid: Dict of 3-tuples to strings
        \tCell content
        attributes: List of 3-tuples
        \tCell attributes
        row_heights: Dict of 2-tuples to float
        \t(row, tab): row_height
        col_widths: Dict of 2-tuples to float
        \t(col, tab): col_width
        macros: String
        \tMacros from macro list

        """

        if "shape" in kwargs:
            self.shape = kwargs["shape"]

        if "grid" in kwargs:
            self.dict_grid.clear()
            self.dict_grid.update(kwargs["grid"])

        if "attributes" in kwargs:
            self.attributes[:] = kwargs["attributes"]

        if "row_heights" in kwargs:
            self.row_heights = kwargs["row_heights"]

        if "col_widths" in kwargs:
            self.col_widths = kwargs["col_widths"]

        if "macros" in kwargs:
            self.macros = kwargs["macros"]

    data = property(_get_data, _set_data)

    # Row and column attributes mask
    # Keys have the format (row, table)

    def _get_row_heights(self):
        """Returns row_heights dict"""

        return self.dict_grid.row_heights

    def _set_row_heights(self, row_heights):
        """Sets  macros string"""

        self.dict_grid.row_heights = row_heights

    row_heights = property(_get_row_heights, _set_row_heights)

    def _get_col_widths(self):
        """Returns col_widths dict"""

        return self.dict_grid.col_widths

    def _set_col_widths(self, col_widths):
        """Sets  macros string"""

        self.dict_grid.col_widths = col_widths

    col_widths = property(_get_col_widths, _set_col_widths)

    # Cell attributes mask
    def _get_cell_attributes(self):
        """Returns cell_attributes list"""

        return self.dict_grid.cell_attributes

    def _set_cell_attributes(self, value):
        """Setter for cell_atributes"""

        # Empty cell_attributes first
        self.cell_attributes[:] = []
        self.cell_attributes.extend(value)

    cell_attributes = attributes = \
        property(_get_cell_attributes, _set_cell_attributes)

    def __iter__(self):
        """Returns iterator over self.dict_grid"""

        return iter(self.dict_grid)

    def _get_macros(self):
        """Returns macros string"""

        return self.dict_grid.macros

    def _set_macros(self, macros):
        """Sets  macros string"""

        self.dict_grid.macros = macros

    macros = property(_get_macros, _set_macros)

    def keys(self):
        """Returns keys in self.dict_grid"""

        return self.dict_grid.keys()

    def pop(self, key, mark_unredo=True):
        """Pops dict_grid with undo and redo support

        Parameters
        ----------
        key: 3-tuple of Integer
        \tCell key that shall be popped
        mark_unredo: Boolean, defaults to True
        \tIf True then an unredo marker is set after the operation

        """

        result = self.dict_grid.pop(key)

        # UnRedo support

        if mark_unredo:
            self.unredo.mark()

        undo_operation = (self.__setitem__, [key, result, mark_unredo])
        redo_operation = (self.pop, [key, mark_unredo])

        self.unredo.append(undo_operation, redo_operation)

        if mark_unredo:
            self.unredo.mark()

        # End UnRedo support

        return result

    # Shape mask

    def _get_shape(self):
        """Returns dict_grid shape"""

        return self.dict_grid.shape

    def _set_shape(self, shape, mark_unredo=True):
        """Deletes all cells beyond new shape and sets dict_grid shape

        Parameters
        ----------
        shape: 3-tuple of Integer
        \tTarget shape for grid
        mark_unredo: Boolean, defaults to True
        \tIf True then an unredo marker is set after the operation

        """

        # Delete each cell that is beyond new borders

        old_shape = self.shape

        if any(new_axis < old_axis
               for new_axis, old_axis in zip(shape, old_shape)):
            for key in self.dict_grid.keys():
                if any(key_ele >= new_axis
                       for key_ele, new_axis in zip(key, shape)):
                    self.pop(key)

        # Set dict_grid shape attribute

        self.dict_grid.shape = shape

        # UnRedo support

        undo_operation = (self._set_shape, [old_shape, mark_unredo])
        redo_operation = (self._set_shape, [shape, mark_unredo])

        self.unredo.append(undo_operation, redo_operation)

        if mark_unredo:
            self.unredo.mark()

        # End UnRedo support

    shape = property(_get_shape, _set_shape)

    def get_last_filled_cell(self, table=None):
        """Returns key for the bottommost rightmost cell with content

        Parameters
        ----------
        table: Integer, defaults to None
        \tLimit search to this table

        """

        maxrow = 0
        maxcol = 0

        for row, col, tab in self.dict_grid:
            if table is None or tab == table:
                maxrow = max(row, maxrow)
                maxcol = max(col, maxcol)

        return maxrow, maxcol, table

    # Pickle support

    def __getstate__(self):
        """Returns dict_grid for pickling

        Note that all persistent data is contained in the DictGrid class

        """

        return {"dict_grid": self.dict_grid}

    # Slice support

    def __getitem__(self, key):
        """Adds slicing access to cell code retrieval

        The cells are returned as a generator of generators, of ... of unicode.

        Parameters
        ----------
        key: n-tuple of integer or slice
        \tKeys of the cell code that is returned

        Note
        ----
        Classical Excel type addressing (A$1, ...) may be added here

        """

        for key_ele in key:
            if is_slice_like(key_ele):
                # We have something slice-like here

                return self.cell_array_generator(key)

            elif is_string_like(key_ele):
                # We have something string-like here
                msg = "Cell string based access not implemented"
                raise NotImplementedError(msg)

        # key_ele should be a single cell

        return self.dict_grid[key]

    def __setitem__(self, key, value, mark_unredo=True):
        """Accepts index and slice keys

        Parameters
        ----------
        key: 3-tuple of Integer or Slice object
        \tCell key(s) that shall be set
        value: Object (should be Unicode or similar)
        \tCode for cell(s) to be set
        mark_unredo: Boolean, defaults to True
        \tIf True then an unredo marker is set after the operation

        """

        single_keys_per_dim = []

        for axis, key_ele in enumerate(key):
            if is_slice_like(key_ele):
                # We have something slice-like here

                length = key[axis]
                slice_range = xrange(*key_ele.indices(length))
                single_keys_per_dim.append(slice_range)

            elif is_string_like(key_ele):
                # We have something string-like here

                raise NotImplementedError

            else:
                # key_ele is a single cell

                single_keys_per_dim.append((key_ele, ))

        single_keys = product(*single_keys_per_dim)

        unredo_mark = False

        for single_key in single_keys:
            if value:
                # UnRedo support

                old_value = self(key)

                try:
                    old_value = unicode(old_value, encoding="utf-8")
                except TypeError:
                    pass

                # We seem to have double calls on __setitem__
                # This hack catches them

                if old_value != value:

                    unredo_mark = True

                    undo_operation = (self.__setitem__,
                                      [key, old_value, mark_unredo])
                    redo_operation = (self.__setitem__,
                                      [key, value, mark_unredo])

                    self.unredo.append(undo_operation, redo_operation)

                    # End UnRedo support

                self.dict_grid[single_key] = value
            else:
                # Value is empty --> delete cell
                try:
                    self.dict_grid.pop(key)

                except (KeyError, TypeError):
                    pass

        if mark_unredo and unredo_mark:
            self.unredo.mark()

    def cell_array_generator(self, key):
        """Generator traversing cells specified in key

        Parameters
        ----------
        key: Iterable of Integer or slice
        \tThe key specifies the cell keys of the generator

        """

        for i, key_ele in enumerate(key):

            # Get first element of key that is a slice
            if type(key_ele) is SliceType:
                slc_keys = xrange(*key_ele.indices(self.dict_grid.shape[i]))
                key_list = list(key)

                key_list[i] = None

                has_subslice = any(type(ele) is SliceType for ele in key_list)

                for slc_key in slc_keys:
                    key_list[i] = slc_key

                    if has_subslice:
                        # If there is a slice left yield generator
                        yield self.cell_array_generator(key_list)

                    else:
                        # No slices? Yield value
                        yield self[tuple(key_list)]

                break

    def _shift_rowcol(self, insertion_point, no_to_insert, mark_unredo):
        """Shifts row and column sizes when a table is inserted or deleted"""

        if mark_unredo:
            self.unredo.mark()

        # Shift row heights

        new_row_heights = {}
        del_row_heights = []

        for row, tab in self.row_heights:
            if tab > insertion_point:
                new_row_heights[(row, tab + no_to_insert)] = \
                    self.row_heights[(row, tab)]
                del_row_heights.append((row, tab))

        for row, tab in new_row_heights:
            self.set_row_height(row, tab, new_row_heights[(row, tab)],
                                mark_unredo=False)

        for row, tab in del_row_heights:
            if (row, tab) not in new_row_heights:
                self.set_row_height(row, tab, None, mark_unredo=False)

        # Shift column widths

        new_col_widths = {}
        del_col_widths = []

        for col, tab in self.col_widths:
            if tab > insertion_point:
                new_col_widths[(col, tab + no_to_insert)] = \
                    self.col_widths[(col, tab)]
                del_col_widths.append((col, tab))

        for col, tab in new_col_widths:
            self.set_col_width(col, tab, new_col_widths[(col, tab)],
                               mark_unredo=False)

        for col, tab in del_col_widths:
            if (col, tab) not in new_col_widths:
                self.set_col_width(col, tab, None, mark_unredo=False)

        if mark_unredo:
            self.unredo.mark()

    def _adjust_rowcol(self, insertion_point, no_to_insert, axis, tab=None,
                       mark_unredo=True):
        """Adjusts row and column sizes on insertion/deletion"""

        if axis == 2:
            self._shift_rowcol(insertion_point, no_to_insert, mark_unredo)
            return

        assert axis in (0, 1)

        if mark_unredo:
            self.unredo.mark()

        cell_sizes = self.col_widths if axis else self.row_heights
        set_cell_size = self.set_col_width if axis else self.set_row_height

        new_sizes = {}
        del_sizes = []

        for pos, table in cell_sizes:
            if pos > insertion_point and (tab is None or tab == table):
                if 0 <= pos + no_to_insert < self.shape[axis]:
                    new_sizes[(pos + no_to_insert, table)] = \
                        cell_sizes[(pos, table)]
                del_sizes.append((pos, table))

        for pos, table in new_sizes:
            set_cell_size(pos, table, new_sizes[(pos, table)],
                          mark_unredo=False)

        for pos, table in del_sizes:
            if (pos, table) not in new_sizes:
                set_cell_size(pos, table, None, mark_unredo=False)

        if mark_unredo:
            self.unredo.mark()

    def _adjust_cell_attributes(self, insertion_point, no_to_insert, axis,
                                tab=None, cell_attrs=None, mark_unredo=True):
        """Adjusts cell attributes on insertion/deletion"""

        if mark_unredo:
            self.unredo.mark()

        old_cell_attrs = self.cell_attributes[:]

        if axis < 2:
            # Adjust selections

            if cell_attrs is None:
                cell_attrs = []

                for key in self.cell_attributes:
                    selection, table, value = key
                    if tab is None or tab == table:
                        new_sel = copy(selection)
                        new_val = copy(value)
                        new_sel.insert(insertion_point, no_to_insert, axis)
                        # Update merge area if present
                        if "merge_area" in value:
                            top, left, bottom, right = value["merge_area"]
                            ma_sel = Selection([(top, left)],
                                               [(bottom, right)], [], [], [])
                            ma_sel.insert(insertion_point, no_to_insert, axis)
                            __top, __left = ma_sel.block_tl[0]
                            __bottom, __right = ma_sel.block_br[0]

                            new_val["merge_area"] = \
                                __top, __left, __bottom, __right

                        cell_attrs.append((new_sel, table, new_val))

            self.cell_attributes[:] = cell_attrs

            self.cell_attributes._attr_cache.clear()

        elif axis == 2:
            # Adjust tabs
            new_tabs = []
            for selection, old_tab, value in self.cell_attributes:
                if old_tab > insertion_point and \
                   (tab is None or tab == old_tab):
                    new_tabs.append((selection, old_tab + no_to_insert, value))
                else:
                    new_tabs.append(None)

            for i, sel_tab_val in enumerate(new_tabs):
                if sel_tab_val is not None:
                    self.dict_grid.cell_attributes.set_item(i, sel_tab_val)

            self.cell_attributes._attr_cache.clear()

        else:
            raise ValueError("Axis must be in [0, 1, 2]")

        undo_operation = (self._adjust_cell_attributes,
                          [insertion_point, -no_to_insert, axis, tab,
                           old_cell_attrs, mark_unredo])
        redo_operation = (self._adjust_cell_attributes,
                          [insertion_point, no_to_insert, axis, tab,
                           cell_attrs, mark_unredo])

        self.unredo.append(undo_operation, redo_operation)

        if mark_unredo:
            self.unredo.mark()

    def insert(self, insertion_point, no_to_insert, axis, tab=None):
        """Inserts no_to_insert rows/cols/tabs/... before insertion_point

        Parameters
        ----------

        insertion_point: Integer
        \tPont on axis, before which insertion takes place
        no_to_insert: Integer >= 0
        \tNumber of rows/cols/tabs that shall be inserted
        axis: Integer
        \tSpecifies number of dimension, i.e. 0 == row, 1 == col, ...
        tab: Integer, defaults to None
        \tIf given then insertion is limited to this tab for axis < 2

        """

        self.unredo.mark()

        if not 0 <= axis <= len(self.shape):
            raise ValueError("Axis not in grid dimensions")

        if insertion_point > self.shape[axis] or \
           insertion_point < -self.shape[axis]:
            raise IndexError("Insertion point not in grid")

        new_keys = {}
        del_keys = []

        for key in self.dict_grid.keys():
            if key[axis] > insertion_point and (tab is None or tab == key[2]):
                new_key = list(key)
                new_key[axis] += no_to_insert
                if 0 <= new_key[axis] < self.shape[axis]:
                    new_keys[tuple(new_key)] = self(key)
                del_keys.append(key)

        # Now re-insert moved keys

        for key in new_keys:
            self.__setitem__(key, new_keys[key], mark_unredo=False)

        for key in del_keys:
            if key not in new_keys and self(key) is not None:
                self.pop(key, mark_unredo=False)

        self._adjust_rowcol(insertion_point, no_to_insert, axis, tab=tab,
                            mark_unredo=False)
        self._adjust_cell_attributes(insertion_point, no_to_insert, axis,
                                     tab=tab, mark_unredo=False)

        self.unredo.mark()

    def delete(self, deletion_point, no_to_delete, axis, tab=None):
        """Deletes no_to_delete rows/cols/... starting with deletion_point

        Axis specifies number of dimension, i.e. 0 == row, 1 == col, ...

        """

        self.unredo.mark()

        if not 0 <= axis < len(self.shape):
            raise ValueError("Axis not in grid dimensions")

        if no_to_delete < 0:
            raise ValueError("Cannot delete negative number of rows/cols/...")

        elif no_to_delete >= self.shape[axis]:
            raise ValueError("Last row/column/table must not be deleted")

        if deletion_point > self.shape[axis] or \
           deletion_point <= -self.shape[axis]:
            raise IndexError("Deletion point not in grid")

        new_keys = {}
        del_keys = []

        # Note that the loop goes over a list that copies all dict keys
        for key in self.dict_grid.keys():
            if tab is None or tab == key[2]:
                if deletion_point <= key[axis] < deletion_point + no_to_delete:
                    del_keys.append(key)

                elif key[axis] >= deletion_point + no_to_delete:
                    new_key = list(key)
                    new_key[axis] -= no_to_delete

                    new_keys[tuple(new_key)] = self(key)
                    del_keys.append(key)

        # Now re-insert moved keys

        for key in new_keys:
            self.__setitem__(key, new_keys[key], mark_unredo=False)

        for key in del_keys:
            if key not in new_keys and self(key) is not None:
                self.pop(key, mark_unredo=False)

        if axis in (0, 1):
            self._adjust_rowcol(deletion_point, -no_to_delete, axis, tab=tab,
                                mark_unredo=False)
        self._adjust_cell_attributes(deletion_point, -no_to_delete, axis,
                                     tab=tab, mark_unredo=False)

        self.unredo.mark()

    def set_row_height(self, row, tab, height, mark_unredo=True):
        """Sets row height"""

        if mark_unredo:
            self.unredo.mark()

        try:
            old_height = self.row_heights.pop((row, tab))

        except KeyError:
            old_height = None

        if height is not None:
            self.row_heights[(row, tab)] = float(height)

        # Make undoable

        undo_operation = (self.set_row_height,
                          [row, tab, old_height, mark_unredo])
        redo_operation = (self.set_row_height, [row, tab, height, mark_unredo])

        self.unredo.append(undo_operation, redo_operation)

        if mark_unredo:
            self.unredo.mark()

    def set_col_width(self, col, tab, width, mark_unredo=True):
        """Sets column width"""

        if mark_unredo:
            self.unredo.mark()

        try:
            old_width = self.col_widths.pop((col, tab))

        except KeyError:
            old_width = None

        if width is not None:
            self.col_widths[(col, tab)] = float(width)

        # Make undoable

        undo_operation = (self.set_col_width,
                          [col, tab, old_width, mark_unredo])
        redo_operation = (self.set_col_width, [col, tab, width, mark_unredo])

        self.unredo.append(undo_operation, redo_operation)

        if mark_unredo:
            self.unredo.mark()

    # Element access via call

    __call__ = __getitem__

# End of class DataArray

# -----------------------------------------------------------------------------


class CodeArray(DataArray):
    """CodeArray provides objects when accessing cells via __getitem__

    Cell code can be accessed via function call

    This class represents layer 3 of the model.

    """

    # Cache for results from __getitem__ calls
    result_cache = {}

    # Cache for frozen objects
    frozen_cache = {}

    def __setitem__(self, key, value, mark_unredo=True):
        """Sets cell code and resets result cache"""

        # Prevent unchanged cells from being recalculated on cursor movement

        repr_key = repr(key)

        unchanged = (repr_key in self.result_cache and
                     value == self(key)) or \
                    ((value is None or value == "") and
                     repr_key not in self.result_cache)

        DataArray.__setitem__(self, key, value, mark_unredo=mark_unredo)

        if not unchanged:
            # Reset result cache
            self.result_cache = {}

    def __getitem__(self, key):
        """Returns _eval_cell"""

        # Frozen cell handling
        if all(type(k) is not SliceType for k in key):
            frozen_res = self.cell_attributes[key]["frozen"]
            if frozen_res:
                if repr(key) in self.frozen_cache:
                    return self.frozen_cache[repr(key)]
                else:
                    # Frozen cache is empty.
                    # Maybe we have a reload without the frozen cache
                    result = self._eval_cell(key, self(key))
                    self.frozen_cache[repr(key)] = result
                    return result

        # Normal cell handling

        if repr(key) in self.result_cache:
            return self.result_cache[repr(key)]

        elif self(key) is not None:
            result = self._eval_cell(key, self(key))
            self.result_cache[repr(key)] = result

            return result

    def _make_nested_list(self, gen):
        """Makes nested list from generator for creating numpy.array"""

        res = []

        for ele in gen:
            if ele is None:
                res.append(None)

            elif not is_string_like(ele) and is_generator_like(ele):
                # Nested generator
                res.append(self._make_nested_list(ele))

            else:
                res.append(ele)

        return res

    def _get_assignment_target_end(self, ast_module):
        """Returns position of 1st char after assignment traget.

        If there is no assignment, -1 is returned

        If there are more than one of any ( expressions or assigments)
        then a ValueError is raised.

        """

        if len(ast_module.body) > 1:
            raise ValueError("More than one expression or assignment.")

        elif len(ast_module.body) > 0 and \
                type(ast_module.body[0]) is ast.Assign:
            if len(ast_module.body[0].targets) != 1:
                raise ValueError("More than one assignment target.")
            else:
                return len(ast_module.body[0].targets[0].id)

        return -1

    def _get_updated_environment(self, env_dict=None):
        """Returns globals environment with 'magic' variable

        Parameters
        ----------
        env_dict: Dict, defaults to {'S': self}
        \tDict that maps global variable name to value

        """

        if env_dict is None:
            env_dict = {'S': self}

        env = globals().copy()
        env.update(env_dict)

        return env

    def _eval_cell(self, key, code):
        """Evaluates one cell and returns its result"""

        # Set up environment for evaluation

        env_dict = {'X': key[0], 'Y': key[1], 'Z': key[2], 'bz2': bz2,
                    'base64': base64, 'charts': charts,
                    'R': key[0], 'C': key[1], 'T': key[2], 'S': self}
        env = self._get_updated_environment(env_dict=env_dict)

        _old_code = self(key)

        # Return cell value if in safe mode

        if self.safe_mode:
            return code

        # If cell is not present return None

        if code is None:
            return

        elif is_generator_like(code):
            # We have a generator object

            return numpy.array(self._make_nested_list(code), dtype="O")

        # If only 1 term in front of the "=" --> global

        try:
            assignment_target_error = None
            module = ast.parse(code)
            assignment_target_end = self._get_assignment_target_end(module)

        except ValueError, err:
            assignment_target_error = ValueError(err)

        except AttributeError, err:
            # Attribute Error includes RunTimeError
            assignment_target_error = AttributeError(err)

        except Exception, err:
            assignment_target_error = Exception(err)

        if assignment_target_error is None and assignment_target_end != -1:
            glob_var = code[:assignment_target_end]
            expression = code.split("=", 1)[1]
            expression = expression.strip()

            # Delete result cache because assignment changes results
            self.result_cache.clear()

        else:
            glob_var = None
            expression = code

        if assignment_target_error is not None:
            result = assignment_target_error

        else:

            try:
                import signal

                signal.signal(signal.SIGALRM, self.handler)
                signal.alarm(config["timeout"])

            except:
                # No POSIX system
                pass

            try:
                result = eval(expression, env, {})

            except AttributeError, err:
                # Attribute Error includes RunTimeError
                result = AttributeError(err)

            except RuntimeError, err:
                result = RuntimeError(err)

            except Exception, err:
                result = Exception(err)

            finally:
                try:
                    signal.alarm(0)
                except:
                    # No POSIX system
                    pass

        # Change back cell value for evaluation from other cells
        self.dict_grid[key] = _old_code

        if glob_var is not None:
            globals().update({glob_var: result})

        return result

    def pop(self, key, mark_unredo=True):
        """Pops dict_grid with undo and redo support

        Parameters
        ----------
        key: 3-tuple of Integer
        \tCell key that shall be popped
        mark_unredo: Boolean, defaults to True
        \tIf True then an unredo marker is set after the operation

        """

        try:
            self.result_cache.pop(repr(key))

        except KeyError:
            pass

        return DataArray.pop(self, key, mark_unredo=mark_unredo)

    def reload_modules(self):
        """Reloads modules that are available in cells"""

        import src.lib.charts as charts
        modules = [charts, bz2, base64, re, ast, sys, wx, numpy, datetime]

        for module in modules:
            reload(module)

    def clear_globals(self):
        """Clears all newly assigned globals"""

        base_keys = ['cStringIO', 'IntType', 'KeyValueStore', 'UnRedo',
                     'is_generator_like', 'is_string_like', 'bz2', 'base64',
                     '__package__', 're', 'config', '__doc__', 'SliceType',
                     'CellAttributes', 'product', 'ast', '__builtins__',
                     '__file__', 'charts', 'sys', 'is_slice_like', '__name__',
                     'copy', 'imap', 'wx', 'ifilter', 'Selection', 'DictGrid',
                     'numpy', 'CodeArray', 'DataArray', 'datetime']

        for key in globals().keys():
            if key not in base_keys:
                globals().pop(key)

    def execute_macros(self):
        """Executes all macros and returns result string

        Executes macros only when not in safe_mode

        """

        if self.safe_mode:
            return '', "Safe mode activated. Code not executed."

        # Windows exec does not like Windows newline
        self.macros = self.macros.replace('\r\n', '\n')

        # Set up environment for evaluation
        globals().update(self._get_updated_environment())

        # Create file-like string to capture output
        code_out = cStringIO.StringIO()
        code_err = cStringIO.StringIO()
        err_msg = cStringIO.StringIO()

        # Capture output and errors
        sys.stdout = code_out
        sys.stderr = code_err

        try:
            import signal

            signal.signal(signal.SIGALRM, self.handler)
            signal.alarm(config["timeout"])

        except:
            # No POSIX system
            pass

        try:
            exec(self.macros, globals())
            try:
                signal.alarm(0)
            except:
                # No POSIX system
                pass

        except Exception:
            # Print exception
            # (Because of how the globals are handled during execution
            # we must import modules here)
            from traceback import print_exception
            from src.lib.exception_handling import get_user_codeframe
            exc_info = sys.exc_info()
            user_tb = get_user_codeframe(exc_info[2]) or exc_info[2]
            print_exception(exc_info[0], exc_info[1], user_tb, None, err_msg)
        # Restore stdout and stderr
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

        results = code_out.getvalue()
        errs = code_err.getvalue() + err_msg.getvalue()

        code_out.close()
        code_err.close()

        # Reset result cache
        self.result_cache.clear()

        # Reset frozen cache
        self.frozen_cache.clear()

        return results, errs

    def _sorted_keys(self, keys, startkey, reverse=False):
        """Generator that yields sorted keys starting with startkey

        Parameters
        ----------

        keys: Iterable of tuple/list
        \tKey sequence that is sorted
        startkey: Tuple/list
        \tFirst key to be yielded
        reverse: Bool
        \tSort direction reversed if True

        """

        tuple_key = lambda t: t[::-1]
        if reverse:
            tuple_cmp = lambda t: t[::-1] > startkey[::-1]
        else:
            tuple_cmp = lambda t: t[::-1] < startkey[::-1]

        searchkeys = sorted(keys, key=tuple_key, reverse=reverse)
        searchpos = sum(1 for _ in ifilter(tuple_cmp, searchkeys))

        searchkeys = searchkeys[searchpos:] + searchkeys[:searchpos]

        for key in searchkeys:
            yield key

    def string_match(self, datastring, findstring, flags=None):
        """
        Returns position of findstring in datastring or None if not found.
        Flags is a list of strings. Supported strings are:
         * "MATCH_CASE": The case has to match for valid find
         * "WHOLE_WORD": The word has to be surrounded by whitespace characters
                         if in the middle of the string
         * "REG_EXP":    A regular expression is evaluated.

        """

        if type(datastring) is IntType:  # Empty cell
            return None

        if flags is None:
            flags = []

        if "REG_EXP" in flags:
            match = re.search(findstring, datastring)
            if match is None:
                pos = -1
            else:
                pos = match.start()
        else:
            if "MATCH_CASE" not in flags:
                datastring = datastring.lower()
                findstring = findstring.lower()

            if "WHOLE_WORD" in flags:
                pos = -1
                matchstring = r'\b' + findstring + r'+\b'
                for match in re.finditer(matchstring, datastring):
                    pos = match.start()
                    break  # find 1st occurrance
            else:
                pos = datastring.find(findstring)

        if pos == -1:
            return None
        else:
            return pos

    def findnextmatch(self, startkey, find_string, flags, search_result=True):
        """ Returns a tuple with the position of the next match of find_string

        Returns None if string not found.

        Parameters:
        -----------
        startkey:   Start position of search
        find_string:String to be searched for
        flags:      List of strings, out of
                    ["UP" xor "DOWN", "WHOLE_WORD", "MATCH_CASE", "REG_EXP"]
        search_result: Bool, defaults to True
        \tIf True then the search includes the result string (slower)

        """

        assert "UP" in flags or "DOWN" in flags
        assert not ("UP" in flags and "DOWN" in flags)

        if search_result:
            def is_matching(key, find_string, flags):
                code = self(key)
                if self.string_match(code, find_string, flags) is not None:
                    return True
                else:
                    res_str = unicode(self[key])
                    return self.string_match(res_str, find_string, flags) \
                        is not None

        else:
            def is_matching(code, find_string, flags):
                code = self(key)
                return self.string_match(code, find_string, flags) is not None

        # List of keys in sgrid in search order

        reverse = "UP" in flags

        for key in self._sorted_keys(self.keys(), startkey, reverse=reverse):
            if is_matching(key, find_string, flags):
                return key

    def handler(self, signum, frame):
        raise RuntimeError("Timeout after {} s.".format(config["timeout"]))

# End of class CodeArray

########NEW FILE########
__FILENAME__ = test_model
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------


"""
test_model
==========

Unit tests for model.py

"""

import ast
import fractions  ## Yes, it is required
import math  ## Yes, it is required
import os
import sys

import py.test as pytest
import numpy

import wx
app = wx.App()

TESTPATH = os.sep.join(os.path.realpath(__file__).split(os.sep)[:-1]) + os.sep
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 3)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 2)

from src.lib.testlib import params, pytest_generate_tests

from src.model.model import KeyValueStore, CellAttributes, DictGrid
from src.model.model import DataArray, CodeArray

from src.lib.selection import Selection

from src.model.unredo import UnRedo


class TestKeyValueStore(object):
    """Unit tests for KeyValueStore"""

    def setup_method(self, method):
        """Creates empty KeyValueStore"""

        self.k_v_store = KeyValueStore()

    def test_missing(self):
        """Test if missing value returns None"""

        key = (1, 2, 3)
        assert self.k_v_store[key] is None

        self.k_v_store[key] = 7

        assert self.k_v_store[key] == 7


class TestCellAttributes(object):
    """Unit tests for CellAttributes"""

    def setup_method(self, method):
        """Creates empty CellAttributes"""

        self.cell_attr = CellAttributes()
        self.cell_attr.unredo = UnRedo()

    def test_undoable_append(self):
        """Test undoable_append"""

        selection = Selection([], [], [], [], [(23, 12)])
        table = 0
        attr = {"angle": 0.2}

        self.cell_attr.undoable_append((selection, table, attr))

        # Check if 2 items - the actual action and the marker - have been added
        assert len(self.cell_attr.unredo.undolist) == 2
        assert len(self.cell_attr.unredo.redolist) == 0
        assert not self.cell_attr._attr_cache

    def test_getitem(self):
        """Test __getitem__"""

        selection_1 = Selection([(2, 2)], [(4, 5)], [55], [55, 66], [(34, 56)])
        selection_2 = Selection([], [], [], [], [(32, 53), (34, 56)])

        self.cell_attr.append((selection_1, 0, {"testattr": 3}))
        self.cell_attr.append((selection_2, 0, {"testattr": 2}))

        assert self.cell_attr[32, 53, 0]["testattr"] == 2
        assert self.cell_attr[2, 2, 0]["testattr"] == 3

    def test_get_merging_cell(self):
        """Test get_merging_cell"""

        selection_1 = Selection([], [], [], [], [(2, 2)])
        selection_2 = Selection([], [], [], [], [(3, 2)])

        self.cell_attr.append((selection_1, 0, {"merge_area": (2, 2, 5, 5)}))
        self.cell_attr.append((selection_2, 0, {"merge_area": (3, 2, 9, 9)}))
        self.cell_attr.append((selection_1, 1, {"merge_area": (2, 2, 9, 9)}))

        # Cell 1. 1, 0 is not merged
        assert self.cell_attr.get_merging_cell((1, 1, 0)) is None

        # Cell 3. 3, 0 is merged to cell 3, 2, 0
        assert self.cell_attr.get_merging_cell((3, 3, 0)) == (3, 2, 0)

        # Cell 2. 2, 0 is merged to cell 2, 2, 0
        assert self.cell_attr.get_merging_cell((2, 2, 0)) == (2, 2, 0)


class TestDictGrid(object):
    """Unit tests for DictGrid"""

    def setup_method(self, method):
        """Creates empty DictGrid"""

        self.dict_grid = DictGrid((100, 100, 100))

    def test_getitem(self):
        """Unit test for __getitem__"""

        with pytest.raises(IndexError):
            self.dict_grid[100, 0, 0]

        self.dict_grid[(2, 4, 5)] = "Test"
        assert self.dict_grid[(2, 4, 5)] == "Test"


class TestDataArray(object):
    """Unit tests for DataArray"""

    def setup_method(self, method):
        """Creates empty DataArray"""

        self.data_array = DataArray((100, 100, 100))

    def test_iter(self):
        """Unit test for __iter__"""

        assert list(iter(self.data_array)) == []

        self.data_array[(1, 2, 3)] = "12"
        self.data_array[(1, 2, 4)] = "13"

        assert sorted(list(iter(self.data_array))) == [(1, 2, 3), (1, 2, 4)]

    def test_keys(self):
        """Unit test for keys"""

        assert self.data_array.keys() == []

        self.data_array[(1, 2, 3)] = "12"
        self.data_array[(1, 2, 4)] = "13"

        assert sorted(self.data_array.keys()) == [(1, 2, 3), (1, 2, 4)]

    def test_pop(self):
        """Unit test for pop"""

        self.data_array[(1, 2, 3)] = "12"
        self.data_array[(1, 2, 4)] = "13"

        assert "12" == self.data_array.pop((1, 2, 3))

        assert sorted(self.data_array.keys()) == [(1, 2, 4)]

    def test_shape(self):
        """Unit test for _get_shape and _set_shape"""

        assert self.data_array.shape == (100, 100, 100)

        self.data_array.shape = (10000, 100, 100)

        assert self.data_array.shape == (10000, 100, 100)

    param_get_last_filled_cell = [
        {'content': {(0, 0, 0): "2"}, 'table': 0, 'res': (0, 0)},
        {'content': {(2, 0, 2): "2"}, 'table': 0, 'res': (0, 0)},
        {'content': {(2, 0, 2): "2"}, 'table': None, 'res': (2, 0)},
        {'content': {(2, 0, 2): "2"}, 'table': 2, 'res': (2, 0)},
        {'content': {(32, 30, 0): "432"}, 'table': 0, 'res': (32, 30)},
    ]

    @params(param_get_last_filled_cell)
    def test_get_last_filled_cell(self, content, table, res):
        """Unit test for get_last_filled_cellet_end"""

        for key in content:
            self.data_array[key] = content[key]

        assert self.data_array.get_last_filled_cell(table)[:2] == res

    def test_getstate(self):
        """Unit test for __getstate__ (pickle support)"""

        assert "dict_grid" in self.data_array.__getstate__()

    def test_slicing(self):
        """Unit test for __getitem__ and __setitem__"""

        self.data_array[0, 0, 0] = "'Test'"
        self.data_array[0, 0, 0] = "'Tes'"

        assert self.data_array[0, 0, 0] == "'Tes'"

    def test_cell_array_generator(self):
        """Unit test for cell_array_generator"""

        cell_array = self.data_array[:5, 0, 0]

        assert list(cell_array) == [None] * 5

        cell_array = self.data_array[:5, :5, 0]

        assert [list(c) for c in cell_array] == [[None] * 5] * 5

        cell_array = self.data_array[:5, :5, :5]

        assert [[list(e) for e in c] for c in cell_array] == \
            [[[None] * 5] * 5] * 5

    def test_set_cell_attributes(self):
        """Unit test for _set_cell_attributes"""

        cell_attributes = ["Test"]
        self.data_array._set_cell_attributes(cell_attributes)
        assert self.data_array.cell_attributes == cell_attributes

    param_adjust_cell_attributes = [
        {'inspoint': 0, 'noins': 5, 'axis': 0,
         'src': (4, 3, 0), 'target': (9, 3, 0)},
        {'inspoint': 34, 'noins': 5, 'axis': 0,
         'src': (4, 3, 0), 'target': (4, 3, 0)},
        {'inspoint': 0, 'noins': 0, 'axis': 0,
         'src': (4, 3, 0), 'target': (4, 3, 0)},
        {'inspoint': 1, 'noins': 5, 'axis': 1,
         'src': (4, 3, 0), 'target': (4, 8, 0)},
        {'inspoint': 1, 'noins': 5, 'axis': 1,
         'src': (4, 3, 1), 'target': (4, 8, 1)},
    ]

    @params(param_adjust_cell_attributes)
    def test_adjust_cell_attributes(self, inspoint, noins, axis, src, target):
        """Unit test for _adjust_cell_attributes"""

        row, col, tab = src

        val = {"angle": 0.2}

        attrs = [(Selection([], [], [], [], [(row, col)]), tab, val)]
        self.data_array._set_cell_attributes(attrs)
        self.data_array._adjust_cell_attributes(inspoint, noins, axis)

        for key in val:
            assert self.data_array.cell_attributes[target][key] == val[key]

    def test_insert(self):
        """Unit test for insert operation"""

        self.data_array[2, 3, 0] = 42
        self.data_array.insert(1, 1, 0)

        assert self.data_array[2, 3, 0] is None

        assert self.data_array[3, 3, 0] == 42

    def test_delete(self):
        """Tests delete operation"""

        self.data_array[2, 3, 4] = "42"
        self.data_array.delete(1, 1, 0)

        assert self.data_array[2, 3, 4] is None
        assert self.data_array[1, 3, 4] == "42"

        try:
            self.data_array.delete(1, 1000, 0)
            assert False
        except ValueError:
            pass

    def test_set_row_height(self):
        """Unit test for set_row_height"""

        self.data_array.set_row_height(7, 1, 22.345)
        assert self.data_array.row_heights[7, 1] == 22.345

    def test_set_col_width(self):
        """Unit test for set_col_width"""

        self.data_array.set_col_width(7, 1, 22.345)
        assert self.data_array.col_widths[7, 1] == 22.345


class TestCodeArray(object):
    """Unit tests for CodeArray"""

    def setup_method(self, method):
        """Creates empty DataArray"""

        self.code_array = CodeArray((100, 10, 3))

    def test_slicing(self):
        """Unit test for __getitem__ and __setitem__"""

        #Test for item getting, slicing, basic evaluation correctness

        shape = self.code_array.shape
        x_list = [0, shape[0]-1]
        y_list = [0, shape[1]-1]
        z_list = [0, shape[2]-1]
        for x, y, z in zip(x_list, y_list, z_list):
            assert self.code_array[x, y, z] is None
            self.code_array[:x, :y, :z]
            self.code_array[:x:2, :y:2, :z:-1]

        get_shape = numpy.array(self.code_array[:, :, :]).shape
        orig_shape = self.code_array.shape
        assert get_shape == orig_shape

        gridsize = 100
        filled_grid = CodeArray((gridsize, 10, 1))
        for i in [-2**99, 2**99, 0]:
            for j in xrange(gridsize):
                filled_grid[j, 0, 0] = str(i)
                filled_grid[j, 1, 0] = str(i) + '+' + str(j)
                filled_grid[j, 2, 0] = str(i) + '*' + str(j)

            for j in xrange(gridsize):
                assert filled_grid[j, 0, 0] == i
                assert filled_grid[j, 1, 0] == i + j
                assert filled_grid[j, 2, 0] == i * j

            for j, funcname in enumerate(['int', 'math.ceil',
                                          'fractions.Fraction']):
                filled_grid[0, 0, 0] = "fractions = __import__('fractions')"
                filled_grid[0, 0, 0]
                filled_grid[1, 0, 0] = "math = __import__('math')"
                filled_grid[1, 0, 0]
                filled_grid[j, 3, 0] = funcname + ' (' + str(i) + ')'
                #res = eval(funcname + "(" + "i" + ")")

                assert filled_grid[j, 3, 0] == eval(funcname + "(" + "i" + ")")
        #Test X, Y, Z
        for i in xrange(10):
            self.code_array[i, 0, 0] = str(i)
        assert [self.code_array((i, 0, 0)) for i in xrange(10)] == \
            map(str, xrange(10))

        assert [self.code_array[i, 0, 0] for i in xrange(10)] == range(10)

        # Test cycle detection

        filled_grid[0, 0, 0] = "numpy.arange(0, 10, 0.1)"
        filled_grid[1, 0, 0] = "sum(S[0,0,0])"

        assert filled_grid[1, 0, 0] == sum(numpy.arange(0, 10, 0.1))

        ##filled_grid[0, 0, 0] = "S[5:10, 1, 0]"
        ##assert filled_grid[0, 0, 0].tolist() == range(7, 12)

    def test_make_nested_list(self):
        """Unit test for _make_nested_list"""

        def gen():
            """Nested generator"""

            yield (("Test" for _ in xrange(2)) for _ in xrange(2))

        res = self.code_array._make_nested_list(gen())

        assert res == [[["Test" for _ in xrange(2)] for _ in xrange(2)]]

    param_get_assignment_target_end = [
        {'code': "a=5", 'res': 1},
        {'code': "a = 5", 'res': 1},
        {'code': "5", 'res': -1},
        {'code': "a == 5", 'res': -1},
        {'code': "", 'res': -1},
        {'code': "fractions = __import__('fractions')", 'res': 9},
        {'code': "math = __import__('math')", 'res': 4},
        {'code': "a = 3==4", 'res': 1},
        {'code': "a == 3 < 44", 'res': -1},
        {'code': "a != 3 < 44", 'res': -1},
        {'code': "a >= 3 < 44", 'res': -1},
        {'code': "a = 3 ; a < 44", 'res': None},
    ]

    @params(param_get_assignment_target_end)
    def test_get_assignment_target_end(self, code, res):
        """Unit test for _get_assignment_target_end"""

        module = ast.parse(code)

        if res is None:
            try:
                self.code_array._get_assignment_target_end(module)
                raise ValueError("Multiple expressions cell not identified")
            except ValueError:
                pass
        else:
            assert self.code_array._get_assignment_target_end(module) == res

    param_eval_cell = [
        {'key': (0, 0, 0), 'code': "2 + 4", 'res': 6},
        {'key': (1, 0, 0), 'code': "S[0, 0, 0]", 'res': None},
        {'key': (43, 2, 1), 'code': "X, Y, Z", 'res': (43, 2, 1)},
    ]

    @params(param_eval_cell)
    def test_eval_cell(self, key, code, res):
        """Unit test for _eval_cell"""

        self.code_array[key] = code
        assert self.code_array._eval_cell(key, code) == res

    def test_execute_macros(self):
        """Unit test for execute_macros"""

        self.code_array.macros = "a = 5\ndef f(x): return x ** 2"
        self.code_array.execute_macros()
        assert self.code_array._eval_cell((0, 0, 0), "a") == 5
        assert self.code_array._eval_cell((0, 0, 0), "f(2)") == 4

    def test_sorted_keys(self):
        """Unit test for _sorted_keys"""

        code_array = self.code_array

        keys = [(1, 0, 0), (2, 0, 0), (0, 1, 0), (0, 99, 0), (0, 0, 0),
                (0, 0, 99), (1, 2, 3)]
        assert list(code_array._sorted_keys(keys, (0, 1, 0))) == \
            [(0, 1, 0), (0, 99, 0), (1, 2, 3), (0, 0, 99), (0, 0, 0),
             (1, 0, 0), (2, 0, 0)]
        sk = list(code_array._sorted_keys(keys, (0, 3, 0), reverse=True))
        assert sk == [(0, 1, 0), (2, 0, 0), (1, 0, 0), (0, 0, 0), (0, 0, 99),
                      (1, 2, 3), (0, 99, 0)]

    def test_string_match(self):
        """Tests creation of string_match"""

        code_array = self.code_array

        test_strings = [
            "", "Hello", " Hello", "Hello ", " Hello ", "Hello\n",
            "THelloT", " HelloT", "THello ", "hello", "HELLO", "sd"
        ]

        search_string = "Hello"

        # Normal search
        flags = []
        results = [None, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0, None]
        for test_string, result in zip(test_strings, results):
            res = code_array.string_match(test_string, search_string, flags)
            assert res == result

        flags = ["MATCH_CASE"]
        results = [None, 0, 1, 0, 1, 0, 1, 1, 1, None, None, None]
        for test_string, result in zip(test_strings, results):
            res = code_array.string_match(test_string, search_string, flags)
            assert res == result

        flags = ["WHOLE_WORD"]
        results = [None, 0, 1, 0, 1, 0, None, None, None, 0, 0, None]
        for test_string, result in zip(test_strings, results):
            res = code_array.string_match(test_string, search_string, flags)
            assert res == result

    def test_findnextmatch(self):
        """Find method test"""

        code_array = self.code_array

        for i in xrange(100):
            code_array[i, 0, 0] = str(i)

        assert code_array[3, 0, 0] == 3
        assert code_array.findnextmatch((0, 0, 0), "3", "DOWN") == (3, 0, 0)
        assert code_array.findnextmatch((0, 0, 0), "99", "DOWN") == (99, 0, 0)

########NEW FILE########
__FILENAME__ = test_unredo
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------


"""
test_unredo
===========

Unit tests for unredo.py

"""

import os
import sys

import wx
app = wx.App()

TESTPATH = os.sep.join(os.path.realpath(__file__).split(os.sep)[:-1]) + os.sep
sys.path.insert(0, TESTPATH)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 3)
sys.path.insert(0, TESTPATH + (os.sep + os.pardir) * 2)

from src.model.unredo import UnRedo


class TestUnRedo(object):
    """Unit test for UnRedo"""
    def setup_method(self, method):
        """Setup for dummy undo steps"""

        self.unredo = UnRedo()
        self.list = []
        self.step = (self.list.append, ["Test"], self.list.pop, [])

    def test_mark(self):
        """Test for marking step delimiters"""

        self.unredo.mark()
        assert self.unredo.undolist == []  # Empty undolist needs no marking

        self.unredo.undolist = [self.step]
        self.unredo.mark()
        assert self.unredo.undolist[-1] == "MARK"

    def test_undo(self):
        """Test for undo operation"""
        self.unredo.undolist = [self.step]
        self.unredo.undo()
        assert self.list == ["Test"]
        assert self.unredo.redolist == [self.step]

        # Test Mark
        self.unredo.mark()
        self.list.pop()
        self.unredo.append(self.step[:2], self.step[2:])
        self.unredo.undo()
        assert self.list == ["Test"]
        assert "MARK" not in self.unredo.undolist
        assert "MARK" in self.unredo.redolist

        # When Redolist != [], a MARK should appear
        self.unredo.mark()
        self.list.pop()
        self.unredo.append(self.step[:2], self.step[2:])
        self.unredo.redolist.append('foo')
        self.unredo.undo()
        assert self.list == ["Test"]
        assert "MARK" not in self.unredo.undolist
        assert "MARK" in self.unredo.redolist

    def test_redo(self):
        """Test for redo operation"""
        self.list.append("Test")
        self.unredo.redolist = [self.step]
        self.unredo.redo()
        assert self.list == []

        # Test Mark

    def test_reset(self):
        """Test for resettign undo"""

        self.unredo.reset()
        assert self.unredo.undolist == []
        assert self.unredo.redolist == []

    def test_append(self):
        """Tests append operation"""

        self.unredo.append(self.step[:2], self.step[2:])
        assert len(self.unredo.undolist) == 1
        assert self.unredo.undolist[0] == self.step

########NEW FILE########
__FILENAME__ = unredo
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""

UnRedo
======

UnRedo contains the UnRedo class that manages undo and redo operations.

"""

from src.config import config


class UnRedo(object):
    """Undo/Redo framework class.

    For each undo-able operation, the undo/redo framework stores the
    undo operation and the redo operation. For each step, a 4-tuple of:
    1) the function object that has to be called for the undo operation
    2) the undo function parameters as a list
    3) the function object that has to be called for the redo operation
    4) the redo function parameters as a list
    is stored.

    One undo step in the application can comprise of multiple operations.
    Undo steps are separated by the string "MARK".

    The attributes should only be written to by the class methods.

    Attributes
    ----------
    undolist: List
    \t
    redolist: List
    \t
    active: Boolean
    \tTrue while an undo or a redo step is executed.

    """

    def __init__(self):
        """[(undofunc, [undoparams, ...], redofunc, [redoparams, ...]),
        ..., "MARK", ...]
        "MARK" separartes undo/redo steps

        """

        self.undolist = []
        self.redolist = []
        self.active = False

    def mark(self):
        """Inserts a mark in undolist and empties redolist"""

        if self.undolist and self.undolist[-1] != "MARK":
            self.undolist.append("MARK")

    def undo(self):
        """Undos operations until next mark and stores them in the redolist"""

        self.active = True

        while self.undolist and self.undolist[-1] == "MARK":
            self.undolist.pop()

        if self.redolist and self.redolist[-1] != "MARK":
            self.redolist.append("MARK")

        while self.undolist:
            step = self.undolist.pop()
            self.redolist.append(step)
            if step == "MARK":
                break
            step[0](*step[1])

        self.active = False

    def redo(self):
        """Redos operations until next mark and stores them in the undolist"""

        self.active = True

        while self.redolist and self.redolist[-1] == "MARK":
            self.redolist.pop()

        if self.undolist and self.undolist[-1] != "MARK":
            self.undolist.append("MARK")

        while self.redolist:
            step = self.redolist.pop()
            if step == "MARK":
                break
            self.undolist.append(step)
            step[2](*step[3])

        self.active = False

    def reset(self):
        """Empties both undolist and redolist"""

        self.__init__()

    def append(self, undo_operation, operation):
        """Stores an operation and its undo operation in the undolist

        undo_operation: (undo_function, [undo_function_attribute_1, ...])
        operation: (redo_function, [redo_function_attribute_1, ...])

        """

        if self.active:
            return False

        # If the lists grow too large they are emptied
        if len(self.undolist) > config["max_unredo"] or \
           len(self.redolist) > config["max_unredo"]:
            self.reset()

        # Check attribute types
        for unredo_operation in [undo_operation, operation]:
            iter(unredo_operation)
            assert len(unredo_operation) == 2
            assert hasattr(unredo_operation[0], "__call__")
            iter(unredo_operation[1])

        if not self.active:
            self.undolist.append(undo_operation + operation)

# End of class UnRedo

########NEW FILE########
__FILENAME__ = pyspread
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""

========
pyspread
========

Python spreadsheet application

Run this script to start the application.

Provides
--------

* Commandlineparser: Gets command line options and parameters
* MainApplication: Initial command line operations and application launch

"""

import sys
import optparse

import wx
__ = wx.App(False)  # Windows Hack

from sysvars import get_program_path
import lib.i18n as i18n


#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext

sys.setrecursionlimit(10000)
sys.path.insert(0, get_program_path())

# Patch for using with PyScripter thanks to Colin J. Williams
# If wx exists in sys,modules, we dont need to import wx version.
# wx is already imported if the PyScripter wx engine is used.

try:
    sys.modules['wx']
except KeyError:
    # Select wx version 2.8 if possible
    try:
        import wxversion
        wxversion.select(['2.8', '2.9'])

    except ImportError:
        pass

from src.gui._events import post_command_event, GridActionEventMixin

DEBUG = False


class Commandlineparser(object):
    """
    Command line handling

    Methods:
    --------

    parse: Returns command line options and arguments as 2-tuple

    """

    def __init__(self):
        from src.config import config
        self.config = config

        usage_str = _("usage: %prog [options] [filename]")
        version = config["version"]
        version_str = _("%prog {version}").format(version=version)
        self.parser = optparse.OptionParser(usage=usage_str,
                                            version=version_str)

        grid_shape = (
            config["grid_rows"],
            config["grid_columns"],
            config["grid_tables"],
        )

        self.parser.add_option(
            "-d", "--dimensions", type="int", nargs=3,
            dest="dimensions", default=grid_shape,
            help=_("Dimensions of empty grid (works only without filename) "
                   "rows, cols, tables [default: %default]")
        )

    def parse(self):
        """
        Returns a a tuple (options, filename)

        options: The command line options
        filename: String (defaults to None)
        \tThe name of the file that is loaded on start-up

        """
        options, args = self.parser.parse_args()

        # If one dimension is 0 then the grid has no cells
        if min(options.dimensions) < 1:
            print _("Cell dimension must be > 0.")
            sys.exit()

        # No MDI yet, pyspread can be started several times though
        if len(args) > 1:
            print _("Only one file may be opened at a time.")
            sys.exit()

        filename = None
        if len(args) == 1:
            # A filename is provided and hence opened
            filename = args[0]

        return options, filename

# end of class Commandlineparser


class MainApplication(wx.App, GridActionEventMixin):
    """Main application class for pyspread."""

    dimensions = (1, 1, 1)  # Will be overridden anyways
    options = {}
    filename = None

    def __init__(self, *args, **kwargs):

        try:
            self.S = kwargs.pop("S")
        except KeyError:
            self.S = None

        # call parent class initializer
        wx.App.__init__(self, *args, **kwargs)

    def OnInit(self):
        """Init class that is automatically run on __init__"""

        # Get command line options and arguments
        self.get_cmd_args()

        # Initialize the prerequisitions to construct the main window
        wx.InitAllImageHandlers()

        # Main window creation
        from src.gui._main_window import MainWindow

        self.main_window = MainWindow(None, title="pyspread", S=self.S)

        ## Initialize file loading via event

        # Create GPG key if not present

        try:
            from src.lib.gpg import genkey
            genkey()

        except ImportError:
            pass

        except ValueError:
            # python-gnupg is installed but gnupg is not insatlled

            pass

        # Show application window
        self.SetTopWindow(self.main_window)
        self.main_window.Show()

        # Load filename if provided
        if self.filepath is not None:
            post_command_event(self.main_window, self.GridActionOpenMsg,
                               attr={"filepath": self.filepath})
            self.main_window.filepath = self.filepath

        return True

    def get_cmd_args(self):
        """Returns command line arguments

        Created attributes
        ------------------

        options: dict
        \tCommand line options
        dimensions: Three tuple of Int
        \tGrid dimensions, default value (1,1,1).
        filename: String
        \tFile name that is loaded on start

        """

        cmdp = Commandlineparser()
        self.options, self.filepath = cmdp.parse()

        if self.filename is None:
            rows, columns, tables = self.options.dimensions
            cmdp.config["grid_rows"] = str(rows)
            cmdp.config["grid_columns"] = str(columns)
            cmdp.config["grid_tables"] = str(tables)


def pyspread(S=None):
    """Parses command line and starts pyspread"""

    # Initialize main application
    app = MainApplication(S=S, redirect=False)

    app.MainLoop()


if __name__ == "__main__":
    if 'unicode' not in wx.PlatformInfo:
        print _("You need a unicode build of wxPython to run pyspread.")

    else:
        if DEBUG:
            import cProfile
            cProfile.run('pyspread()')
        else:
            pyspread()

########NEW FILE########
__FILENAME__ = sysvars
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""

sysvars
=======

System environment access

"""

import os

import wx


# OS
def is_gtk():
    return "__WXGTK__" in wx.PlatformInfo

# Paths


def get_program_path():
    """Returns the path in which pyspread is installed"""

    return os.path.dirname(__file__) + '/../'


def get_help_path():
    """Returns the pyspread help path"""

    return get_program_path() + "doc/help/"


def get_python_tutorial_path():
    """Returns the Python tutorial path"""

    # If the OS has the Python tutorial installed locally, use it.
    # the current path is for Debian

    if os.path.isfile("/usr/share/doc/python-doc/html/tutorial/index.html"):
        return "/usr/share/doc/python-doc/html/tutorial/index.html"

    else:
        return "http://docs.python.org/2/tutorial/"

# System settings


def get_dpi():
    """Returns screen dpi resolution"""

    pxmm_2_dpi = lambda (pixels, length_mm): pixels * 25.6 / length_mm
    return map(pxmm_2_dpi, zip(wx.GetDisplaySize(), wx.GetDisplaySizeMM()))


def get_color(name):
    """Returns system color from name"""

    return wx.SystemSettings.GetColour(name)


def get_default_font():
    """Returns default font"""

    return wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)


def get_font_string(name):
    """Returns string representation of named system font"""

    return wx.SystemSettings.GetFont(name).GetFaceName()

# Fonts


def get_font_list():
    """Returns a sorted list of all system font names"""

    font_enum = wx.FontEnumerator()
    font_enum.EnumerateFacenames(wx.FONTENCODING_SYSTEM)
    font_list = font_enum.GetFacenames()
    font_list.sort()

    return font_list


def get_default_text_extent(text):
    """Returns the text extent for the default font"""

    return wx.GetApp().GetTopWindow().GetTextExtent(text)

########NEW FILE########
__FILENAME__ = runtests
#! /usr/bin/env python

sources = """
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
"""

import sys
import base64
import zlib
import imp

class DictImporter(object):
    def __init__(self, sources):
        self.sources = sources

    def find_module(self, fullname, path=None):
        if fullname in self.sources:
            return self
        if fullname + '.__init__' in self.sources:
            return self
        return None

    def load_module(self, fullname):
        # print "load_module:",  fullname
        from types import ModuleType
        try:
            s = self.sources[fullname]
            is_pkg = False
        except KeyError:
            s = self.sources[fullname + '.__init__']
            is_pkg = True

        co = compile(s, fullname, 'exec')
        module = sys.modules.setdefault(fullname, ModuleType(fullname))
        module.__file__ = "%s/%s" % (__file__, fullname)
        module.__loader__ = self
        if is_pkg:
            module.__path__ = [fullname]

        do_exec(co, module.__dict__)
        return sys.modules[fullname]

    def get_source(self, name):
        res = self.sources.get(name)
        if res is None:
            res = self.sources.get(name + '.__init__')
        return res

if __name__ == "__main__":
    if sys.version_info >= (3, 0):
        exec("def do_exec(co, loc): exec(co, loc)\n")
        import pickle
        sources = sources.encode("ascii") # ensure bytes
        sources = pickle.loads(zlib.decompress(base64.decodebytes(sources)))
    else:
        import cPickle as pickle
        exec("def do_exec(co, loc): exec co in loc\n")
        sources = pickle.loads(zlib.decompress(base64.decodestring(sources)))

    importer = DictImporter(sources)
    sys.meta_path.insert(0, importer)

    entry = "import py; raise SystemExit(py.test.cmdline.main())"
    do_exec(entry, locals())

########NEW FILE########
