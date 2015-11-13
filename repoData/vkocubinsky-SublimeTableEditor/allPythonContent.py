__FILENAME__ = table_base
# table_base.py - Key classes and methods for pretty print text table.

# Copyright (C) 2012  Free Software Foundation, Inc.

# Author: Valery Kocubinsky
# Package: SublimeTableEditor
# Homepage: https://github.com/vkocubinsky/SublimeTableEditor

# This file is part of SublimeTableEditor.

# SublimeTableEditor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SublimeTableEditor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with SublimeTableEditor.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import print_function
from __future__ import division

import math
import re
import csv

try:
    from . import table_line_parser as tparser
    from .widechar_support import wlen, wcount
except ValueError:
    import table_line_parser as tparser
    from widechar_support import wlen, wcount


class TableConfiguration:
    def __init__(self):
        self.keep_space_left = False
        self.align_number_right = True
        self.detect_header = True
        self.intelligent_formatting = True

        #only for simple syntax
        self.hline_out_border = None
        self.hline_in_border = None
        self.custom_column_alignment = True


class TableSyntax:

    def __init__(self, name, table_configuration):
        self.name = name
        self.table_configuration = table_configuration or TableConfiguration()

        self.align_number_right = self.table_configuration.align_number_right
        self.detect_header = self.table_configuration.detect_header
        self.keep_space_left = self.table_configuration.keep_space_left
        self.intelligent_formatting = self.table_configuration.intelligent_formatting

        self.line_parser = tparser.LineParserPlus("(?:[|])")
        # Must be set in sublass constructor
        self.table_parser = None
        self.table_driver = None




class Column(object):
    ALIGN_LEFT = 'left'
    ALIGN_RIGHT = 'right'
    ALIGN_CENTER = 'center'

    def __init__(self, row):
        self.row = row
        self.table = row.table
        self.syntax = row.table.syntax
        self.col_len = 0
        self.align = None
        self.header = None
        self.colspan = 1
        self.rowspan = 1
        self.pseudo_columns = []
        self.left_border_text = '|'
        self.right_border_text = '|'

    def min_len(self):
        raise NotImplementedError

    def render(self):
        raise NotImplementedError

    def align_follow(self):
        return None

    def pseudo(self):
        return False


class PseudoColumn(Column):

    def __init__(self, row, master_column):
        Column.__init__(self, row)
        self.master_column = master_column
        self.data = ''

    def render(self):
        return ''

    def min_len(self):
        return self.master_column.min_len()

    def pseudo(self):
        return True


class Row:

    def __init__(self, table):
        self.table = table
        self.syntax = table.syntax
        self.columns = []

    def __getitem__(self, index):
        return self.columns[index]

    def __len__(self):
        return len(self.columns)

    def is_header_separator(self):
        return False

    def is_separator(self):
        return False

    def is_data(self):
        return False

    def is_align(self):
        return False

    def append(self, column):
        self.columns.append(column)
        for i in range(0, column.colspan - 1):
            psedo_column = PseudoColumn(self, column)
            column.pseudo_columns.append(psedo_column)
            self.columns.append(psedo_column)

    def new_empty_column(self):
        raise NotImplementedError

    def create_column(self, text):
        raise NotImplementedError

    def render(self):
        r = ""
        for ind, column in enumerate(self.columns):
            if column.pseudo():
                continue
            if ind == 0:
                r += self.convert_border(column.left_border_text)
            r += column.render()
            r += self.convert_border(column.right_border_text)
        return r

    def convert_border(self, border_text):
        # if separator converts to data
        return border_text.replace('+', '|')


class DataRow(Row):

    def new_empty_column(self):
        return DataColumn(self, '')

    def create_column(self, text):
        return DataColumn(self, text)

    def is_data(self):
        return True


class DataColumn(Column):

    def __init__(self, row, data):
        Column.__init__(self, row)
        self.data = data
        self.left_space = ' '
        self.right_space = ' '

    def _norm(self):
        if self.syntax.keep_space_left:
            if self.header:
                norm = self.data.strip()
            else:
                norm = self.data.rstrip()
                if norm[:1] == ' ':
                    norm = norm[1:]
        else:
            norm = self.data.strip()
        return norm

    def min_len(self):
        return int(math.ceil(self.total_min_len()/self.colspan))

    def total_min_len(self):
        # min of '   ' or ' xxxx '
        space_len = len(self.left_space) + len(self.right_space)
        total_min_len = max(space_len + 1, wlen(self._norm()) + space_len)
        total_min_len = (total_min_len
                         + (len(self.left_border_text) - 1)
                         + (len(self.right_border_text) - 1))
        return total_min_len

    def render(self):
        # colspan -1 is count of '|'
        total_col_len = (self.col_len
                         + (self.colspan - 1)
                         + sum([col.col_len for col in self.pseudo_columns]))

        #if self.syntax.multi_markdown_syntax():
        #    total_col_len = total_col_len - (self.colspan - 1)
        total_col_len = (total_col_len
                         # left border already calculated
                         # - (len(self.left_border_text) - 1)
                         - (len(self.right_border_text) - 1))

        norm = self._norm()
        space_len = len(self.left_space) + len(self.right_space)

        total_align_len = total_col_len - wcount(norm)
        if self.header and self.syntax.detect_header:
            align_value = norm.center(total_align_len - space_len, ' ')
        elif self.align == Column.ALIGN_RIGHT:
            align_value = norm.rjust(total_align_len - space_len, ' ')
        elif self.align == Column.ALIGN_CENTER:
            align_value = norm.center(total_align_len - space_len, ' ')
        else:
            align_value = norm.ljust(total_align_len - space_len, ' ')
        return self.left_space + align_value + self.right_space


def check_condition(condition, message):
    if not condition:
        raise TableException(message)


class TextTable:

    def __init__(self, syntax):
        self.syntax = syntax
        self.prefix = ""
        self.rows = []
        self.pack()

    def __len__(self):
        return len(self.rows)

    def empty(self):
        return len(self.rows) == 0

    def __getitem__(self, index):
        return self.rows[index]

    def _max_column_count(self):
        return max([len(row) for row in self.rows])

    def _rstrip(self):
        if len(self.rows) <= 1:
            return
        max_column_count = self._max_column_count()
        long_lines_count = 0
        long_line_ind = 0
        for row_ind, row in enumerate(self.rows):
            if len(row) == max_column_count:
                long_lines_count += 1
                long_line_ind = row_ind

        if long_lines_count == 1:
            row = self.rows[long_line_ind]
            overspans = sum([column.colspan - 1 for column in row.columns])
            if row.is_data() and overspans > 0:
                shift = 0
                for shift, column in enumerate(row[::-1]):
                    if column.pseudo() or len(column.data.strip()) > 0:
                        break
                if shift > 0:
                    if len(self.rows) == 2:
                        if shift != overspans:
                            return

                    row.columns = row.columns[:-shift]

    def pack(self):
        if len(self.rows) == 0:
            return

        column_count = self._max_column_count()

        if column_count == 0:
            self.rows = []
            return

        #intelligent formatting
        if self.syntax.intelligent_formatting:
            self._rstrip()
            column_count = self._max_column_count()

        #adjust/extend column count
        rowspans = [0] * column_count
        for row in self.rows:
            overcols = sum([rowspan for rowspan in rowspans if rowspan > 0])

            diff_count = column_count - len(row) - overcols
            for i in range(diff_count):
                row.columns.append(row.new_empty_column())
            if len(row) == 0:
                row.columns.append(row.new_empty_column())

            #prepare rowspans for next row
            for col_ind, rowspan in enumerate(rowspans):
                if rowspan > 0:
                    rowspans[col_ind] = rowspans[col_ind] - 1

            for col_ind, column in enumerate(row.columns):
                rowspans[col_ind] = rowspans[col_ind] + column.rowspan - 1

        #calculate column lens
        col_lens = [0] * column_count
        for row in self.rows:
            for col_ind, column in enumerate(row.columns):
                col_lens[col_ind] = max(col_lens[col_ind], column.min_len())

        #set column len
        for row in self.rows:
            for column, col_len in zip(row.columns, col_lens):
                column.col_len = col_len

        #header
        header_separator_index = -1
        first_data_index = -1
        if self.syntax.detect_header:
            for row_ind, row in enumerate(self.rows):
                if first_data_index == -1 and row.is_data():
                    first_data_index = row_ind
                if (first_data_index != -1 and header_separator_index == -1
                        and row.is_header_separator()):
                    header_separator_index = row_ind
                    for header_index in range(first_data_index, header_separator_index):
                        if self.rows[header_index].is_data():
                            for column in self.rows[header_index].columns:
                                column.header = True

        #set column alignment
        data_alignment = [None] * len(col_lens)
        for row_ind, row in enumerate(self.rows):
            if row_ind < header_separator_index:
                if row.is_align():
                    for col_ind, column in enumerate(row.columns):
                        data_alignment[col_ind] = column.align_follow()
                continue
            elif row.is_align():
                for col_ind, column in enumerate(row.columns):
                    data_alignment[col_ind] = column.align_follow()
            elif row.is_data():
                for col_ind, column in enumerate(row.columns):
                    if data_alignment[col_ind] is None:
                        if self.syntax.align_number_right and self._is_number_column(row_ind, col_ind):
                            data_alignment[col_ind] = Column.ALIGN_RIGHT
                        else:
                            data_alignment[col_ind] = Column.ALIGN_LEFT
                    column.align = data_alignment[col_ind]

    def _is_number_column(self, start_row_ind, col_ind):
        assert self.rows[start_row_ind].is_data()
        for row in self.rows[start_row_ind:]:
            if (row.is_data()
                    and col_ind < len(row.columns)
                    and len(row.columns[col_ind].data.strip()) > 0):
                        try:
                            float(row.columns[col_ind].data)
                        except ValueError:
                            return False
        return True

    def render_lines(self):
        return [self.prefix + row.render() for row in self.rows]

    def render(self):
        return "\n".join(self.render_lines())

    def is_col_colspan(self, col):
        for row in self.rows:
            if col < len(row):
                if row[col].pseudo() or row[col].colspan > 1:
                    return True
        return False

    def is_row_colspan(self, row):
        for column in self[row].columns:
            if column.pseudo() or column.colspan > 1:
                    return True
        return False

    def assert_not_col_colspan(self, col):
        check_condition(self.is_col_colspan(col) is False,
                        "Expected not colspan column, but column {0}"
                        " is colspan".format(col))

    def delete_column(self, col):
        self.assert_not_col_colspan(col)
        for row in self.rows:
            if col < len(row):
                del row.columns[col]
        self.pack()

    def swap_columns(self, i, j):
        self.assert_not_col_colspan(i)
        self.assert_not_col_colspan(j)
        for row in self.rows:
            if i < len(row) and j < len(row):
                row.columns[i], row.columns[j] = row.columns[j], row.columns[i]
        self.pack()

    def delete_row(self, i):
        assert 0 <= i < len(self.rows)

        del self.rows[i]
        self.pack()

    def swap_rows(self, i, j):
        check_condition((0 <= i < len(self.rows) and
                        0 <= j < len(self.rows)),
                        "Index out of range")

        self.rows[i], self.rows[j] = self.rows[j], self.rows[i]
        for column in self.rows[i].columns:
            column.header = False
        for column in self.rows[j].columns:
            column.header = False

        self.pack()

    def insert_empty_row(self, i):
        check_condition(i >= 0, "Index should be more than zero")

        self.rows.insert(i, DataRow(self))
        self.pack()

    def insert_empty_column(self, i):
        check_condition(i >= 0, "Index should be more than zero")
        self.assert_not_col_colspan(i)

        for row in self.rows:
            row.columns.insert(i, row.new_empty_column())
        self.pack()


class TableException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class TablePos:

    def __init__(self, row_num, field_num):
        self.row_num = row_num
        self.field_num = field_num

    def __repr__(self):
        return "TablePos({self.row_num}, {self.field_num})".format(self=self)

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return (self.row_num == other.row_num
                and self.field_num == other.field_num)


class TableDriver:

    def __init__(self, syntax):
        self.syntax = syntax

    def visual_column_count(self, table, row_ind):
        return sum([1 for column in table[row_ind].columns
                   if not column.pseudo()])

    def internal_to_visual_index(self, table, internal_pos):
        visual_pos = TablePos(internal_pos.row_num, internal_pos.field_num)
        for col_ind in range(internal_pos.field_num + 1):
            if table[internal_pos.row_num][col_ind].pseudo():
                visual_pos.field_num -= 1
        return visual_pos

    def visual_to_internal_index(self, table, visual_pos):
        internal_pos = TablePos(visual_pos.row_num, 0)
        count_visual = 0
        internal_pos.field_num = 0
        for col_ind in range(len(table[visual_pos.row_num])):
            if not table[visual_pos.row_num][col_ind].pseudo():
                count_visual += 1
                internal_pos.field_num = col_ind
            if count_visual == visual_pos.field_num + 1:
                break
        else:
            print("WARNING: Visual Index Not found")
        return internal_pos

    def get_cursor(self, table, visual_pos):
        #
        # '   |  1 |  2  |  3_| 4 |'
        internal_pos = self.visual_to_internal_index(table, visual_pos)
        base_len = (len(table.prefix)
                    + sum([column.col_len - wcount(column.render()) for column, ind
                          in zip(table[visual_pos.row_num].columns,
                                 range(internal_pos.field_num))])
                    + internal_pos.field_num + 1  # count of '|'
                    )
        text = table[internal_pos.row_num][internal_pos.field_num].render()
        match = re.search(r"([^\s])\s*$", text)
        if match:
            col_pos = match.end(1)
        else:
            col_pos = 1
        return base_len + col_pos

    def editor_move_column_left(self, table, table_pos):
        internal_pos = self.visual_to_internal_index(table, table_pos)
        field_num = internal_pos.field_num
        if field_num > 0:
            if (table.is_col_colspan(field_num) or
                    table.is_col_colspan(field_num - 1)):
                raise TableException("Move Column Left is not "
                                     "permitted for colspan column")
            else:
                table.swap_columns(field_num, field_num - 1)
                return ("Column moved to left",
                        TablePos(table_pos.row_num, table_pos.field_num - 1))
        else:
            raise TableException("Move Column Left doesn't "
                                 "make sence for the first column in the "
                                 "table.")

    def editor_move_column_right(self, table, table_pos):
        internal_pos = self.visual_to_internal_index(table, table_pos)
        field_num = internal_pos.field_num

        if field_num < len(table[table_pos.row_num]) - 1:
            if (table.is_col_colspan(field_num) or
                    table.is_col_colspan(field_num + 1)):
                raise TableException("Move Column Right is not "
                                     "permitted for colspan column")
            else:
                table.swap_columns(field_num, field_num + 1)
                return ("Column moved to right",
                        TablePos(table_pos.row_num, table_pos.field_num + 1))
        else:
            raise TableException("Move Column Right doesn't "
                                 "make sense for the last column in the "
                                 "table.")

    def editor_move_row_up(self, table, table_pos):
        if table_pos.row_num > 0:
            table.swap_rows(table_pos.row_num, table_pos.row_num - 1)
            return("Row moved up",
                   TablePos(table_pos.row_num - 1, table_pos.field_num))
        else:
            raise TableException("Move Row Up doesn't make sense for the "
                                 "first row in the table")

    def editor_move_row_down(self, table, table_pos):
        if table_pos.row_num + 1 < len(table):
            table.swap_rows(table_pos.row_num, table_pos.row_num + 1)
            return ("Row moved down",
                    TablePos(table_pos.row_num + 1, table_pos.field_num))
        else:
            raise TableException("Move Row Down doesn't make sense for the "
                                 "last row in the table")

    def editor_next_row(self, table, table_pos):
        if table_pos.row_num + 1 < len(table):
            if table[table_pos.row_num + 1].is_header_separator():
                table.insert_empty_row(table_pos.row_num + 1)
        else:
            table.insert_empty_row(len(table))
        return ("Moved to next row",
                TablePos(table_pos.row_num + 1, table_pos.field_num))

    def editor_delete_column(self, table, table_pos):
        internal_pos = self.visual_to_internal_index(table, table_pos)
        field_num = internal_pos.field_num

        if table.is_col_colspan(field_num):
            raise TableException("Delete column is not permitted for "
                                 "colspan column")
        else:
            table.delete_column(field_num)
            new_table_pos = TablePos(table_pos.row_num,
                                     table_pos.field_num)
            if (not table.empty() and
                    table_pos.field_num == len(table[table_pos.row_num])):
                new_table_pos.field_num = new_table_pos.field_num - 1
            return("Column deleted", new_table_pos)

    def editor_insert_column(self, table, table_pos):
        internal_pos = self.visual_to_internal_index(table, table_pos)
        field_num = internal_pos.field_num

        if table.is_col_colspan(field_num):
            raise TableException("Insert column is not permitted for "
                                 "colspan column")
        else:
            table.insert_empty_column(field_num)
            return ("Column inserted",
                    TablePos(table_pos.row_num, table_pos.field_num))

    def editor_kill_row(self, table, table_pos):
        table.delete_row(table_pos.row_num)
        new_table_pos = TablePos(table_pos.row_num, table_pos.field_num)
        if table_pos.row_num == len(table):
            new_table_pos.row_num = new_table_pos.row_num - 1
        return ("Row deleted", new_table_pos)

    def editor_insert_row(self, table, table_pos):
        table.insert_empty_row(table_pos.row_num)
        return ("Row inserted",
                TablePos(table_pos.row_num, table_pos.field_num))

    def editor_insert_single_hline(self, table, table_pos):
        raise TableException("Syntax {0} doesn't support insert single line"
                             .format(self.syntax.name))

    def editor_insert_double_hline(self, table, table_pos):
        raise TableException("Syntax {0} doesn't support insert double line"
                             .format(self.syntax.name))

    def editor_insert_hline_and_move(self, table, table_pos):
        raise TableException("Syntax {0} doesn't support insert single line "
                             "and move".format(self.syntax.name))

    def editor_align(self, table, table_pos):
        return ("Table aligned",
                TablePos(table_pos.row_num, table_pos.field_num))

    def editor_join_lines(self, table, table_pos):
        if (table_pos.row_num + 1 < len(table)
            and table[table_pos.row_num].is_data()
            and table[table_pos.row_num + 1].is_data()
            and not table.is_row_colspan(table_pos.row_num)
                and not table.is_row_colspan(table_pos.row_num + 1)):

            for curr_col, next_col in zip(table[table_pos.row_num].columns,
                                          table[table_pos.row_num + 1].columns):
                curr_col.data = curr_col.data.strip() + " " + next_col.data.strip()

            table.delete_row(table_pos.row_num + 1)
            return ("Rows joined",
                    TablePos(table_pos.row_num, table_pos.field_num))
        else:
            raise TableException("Join columns is not permitted")

    def editor_next_field(self, table, table_pos):
        pos = TablePos(table_pos.row_num, table_pos.field_num)

        moved = False
        while True:
            if table[pos.row_num].is_separator():
                if pos.row_num + 1 < len(table):
                    pos.field_num = 0
                    pos.row_num += 1
                    moved = True
                    continue
                else:
                    #sel_row == last_table_row
                    table.insert_empty_row(len(table))
                    pos.field_num = 0
                    pos.row_num += 1
                    break
            elif moved:
                break
            elif pos.field_num + 1 < self.visual_column_count(table, pos.row_num):
                pos.field_num += 1
                break
            elif pos.row_num + 1 < len(table):
                pos.field_num = 0
                pos.row_num += 1
                moved = True
                continue
            else:
                #sel_row == last_table_row
                table.insert_empty_row(len(table))
                pos.field_num = 0
                pos.row_num += 1
                break
        return ("Cursor position changed", pos)

    def editor_previous_field(self, table, table_pos):
        pos = TablePos(table_pos.row_num, table_pos.field_num)
        moved = False
        while True:
            if table[pos.row_num].is_separator():
                if pos.row_num > 0:
                    pos.row_num -= 1
                    pos.field_num = self.visual_column_count(table, pos.row_num) - 1
                    moved = True
                    continue
                else:
                    #row_num == 0
                    pos.field_num = 0
                    break
            elif moved:
                break
            elif pos.field_num > 0:
                pos.field_num -= 1
                break
            elif pos.row_num > 0:
                pos.row_num -= 1
                pos.field_num = self.visual_column_count(table, pos.row_num) - 1
                moved = True
                continue
            else:
                #row_num == 0
                break
        return ("Cursor position changed", pos)

    def parse_csv(self, text):
        try:
            table = TextTable(self.syntax)
            dialect = csv.Sniffer().sniff(text)
            table_reader = csv.reader(text.splitlines(), dialect)
            for cols in table_reader:
                row = DataRow(table)
                for col in cols:
                    row.columns.append(DataColumn(row, col))
                table.rows.append(row)
        except csv.Error:
            table = TextTable(self.syntax)
            for line in text.splitlines():
                row = DataRow(table)
                row.columns.append(DataColumn(row, line))
                table.rows.append(row)
        table.pack()
        return table


class BaseTableParser:

    def __init__(self, syntax):
        self.syntax = syntax

    def parse_row(self, table, line):
        row = self.create_row(table, line)

        for line_cell in line.cells:
            column = self.create_column(table, row, line_cell)
            row.append(column)
        return row

    def create_row(self, table, line):
        raise NotImplementedError

    def create_column(self, table, row, line_cell):
        column = row.create_column(line_cell.text)
        column.left_border_text = line_cell.left_border_text
        column.right_border_text = line_cell.right_border_text
        return column

    def is_table_row(self, row):
        return re.match(r"^\s*[|+]",row) is not None

    def parse_text(self, text):
        table = TextTable(self.syntax)
        lines = text.splitlines()
        for ind, line in enumerate(lines):

            line = self.syntax.line_parser.parse(line)
            if ind == 0:
                table.prefix = line.prefix
            row = self.parse_row(table, line)
            table.rows.append(row)
        table.pack()
        return table

########NEW FILE########
__FILENAME__ = table_border_syntax
# table_border_syntax.py - Base classes for table with borders: Pandoc,
# Emacs Org mode, Simple, reStrucutredText

# Copyright (C) 2012  Free Software Foundation, Inc.

# Author: Valery Kocubinsky
# Package: SublimeTableEditor
# Homepage: https://github.com/vkocubinsky/SublimeTableEditor

# This file is part of SublimeTableEditor.

# SublimeTableEditor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SublimeTableEditor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with SublimeTableEditor.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import print_function
from __future__ import division

import re

try:
    from . import table_base as tbase
except ValueError:
    import table_base as tbase


class SeparatorRow(tbase.Row):

    def __init__(self, table, separator='-', size=0):
        tbase.Row.__init__(self, table)
        self.separator = separator
        for i in range(size):
            self.columns.append(SeparatorColumn(self, self.separator))

    def new_empty_column(self):
        return SeparatorColumn(self, self.separator)

    def create_column(self, text):
        return SeparatorColumn(self, self.separator)

    def is_header_separator(self):
        return True

    def is_separator(self):
        return True

    def render(self):
        r = self.syntax.hline_out_border
        for ind, column in enumerate(self.columns):
            if ind != 0:
                r += self.syntax.hline_in_border
            r += column.render()
        r += self.syntax.hline_out_border
        return r


class SeparatorColumn(tbase.Column):
    def __init__(self, row, separator):
        tbase.Column.__init__(self, row)
        self.separator = separator

    def min_len(self):
        # '---' or '==='
        return 3

    def render(self):
        return self.separator * self.col_len


class BorderTableDriver(tbase.TableDriver):

    def editor_insert_single_hline(self, table, table_pos):
        table.rows.insert(table_pos.row_num + 1, SeparatorRow(table, '-'))
        table.pack()
        return ("Single separator row inserted",
                tbase.TablePos(table_pos.row_num, table_pos.field_num))

    def editor_insert_double_hline(self, table, table_pos):
        table.rows.insert(table_pos.row_num + 1, SeparatorRow(table, '='))
        table.pack()
        return ("Double separator row inserted",
                tbase.TablePos(table_pos.row_num, table_pos.field_num))

    def editor_insert_hline_and_move(self, table, table_pos):
        table.rows.insert(table_pos.row_num + 1, SeparatorRow(table, '-'))
        table.pack()
        if table_pos.row_num + 2 < len(table):
            if table[table_pos.row_num + 2].is_separator():
                table.insert_empty_row(table_pos.row_num + 2)
        else:
            table.insert_empty_row(table_pos.row_num + 2)
        return("Single separator row inserted",
               tbase.TablePos(table_pos.row_num + 2, 0))


class BorderTableParser(tbase.BaseTableParser):

    def _is_single_row_separator(self, str_cols):
        if len(str_cols) == 0:
            return False
        for col in str_cols:
            if not re.match(r"^\s*[\-]+\s*$", col):
                return False
        return True

    def _is_double_row_separator(self, str_cols):
        if len(str_cols) == 0:
            return False
        for col in str_cols:
            if not re.match(r"^\s*[\=]+\s*$", col):
                return False
        return True

    def create_row(self, table, line):
        if self._is_single_row_separator(line.str_cols()):
            row = SeparatorRow(table, '-')
        elif self._is_double_row_separator(line.str_cols()):
            row = SeparatorRow(table, '=')
        else:
            row = self.create_data_row(table, line)
        return row

    def create_data_row(self, table, line):
        return tbase.DataRow(table)

########NEW FILE########
__FILENAME__ = table_emacs_org_mode_syntax
# table_emacs_org_mode_syntax.py - Emacs Org mode table syntax

# Copyright (C) 2012  Free Software Foundation, Inc.

# Author: Valery Kocubinsky
# Package: SublimeTableEditor
# Homepage: https://github.com/vkocubinsky/SublimeTableEditor

# This file is part of SublimeTableEditor.

# SublimeTableEditor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SublimeTableEditor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with SublimeTableEditor.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import print_function
from __future__ import division

try:
    from . import table_base as tbase
    from . import table_border_syntax as tborder
except ValueError:
    import table_base as tbase
    import table_border_syntax as tborder


def create_syntax(table_configuration=None):
    return EmacsOrgModeTableSyntax(table_configuration)


class EmacsOrgModeTableSyntax(tbase.TableSyntax):

    def __init__(self, table_configuration):
        tbase.TableSyntax.__init__(self, "Emacs Org mode", table_configuration)

        self.table_parser = tborder.BorderTableParser(self)
        self.table_driver = tborder.BorderTableDriver(self)

        self.hline_out_border = '|'
        self.hline_in_border = '+'

########NEW FILE########
__FILENAME__ = table_lib
# table_lib.py - pretty print text table.

# Copyright (C) 2012  Free Software Foundation, Inc.

# Author: Valery Kocubinsky
# Package: SublimeTableEditor
# Homepage: https://github.com/vkocubinsky/SublimeTableEditor

# This file is part of SublimeTableEditor.

# SublimeTableEditor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SublimeTableEditor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with SublimeTableEditor.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
from __future__ import division

import csv

try:
    from . import table_base as tbase
    from . import table_simple_syntax as simple
    from . import table_emacs_org_mode_syntax as emacs
    from . import table_pandoc_syntax as pandoc
    from . import table_multi_markdown_syntax as markdown
    from . import table_re_structured_text_syntax as re_structured_text
    from . import table_textile_syntax as textile
except ValueError:
    import table_base as tbase
    import table_simple_syntax as simple
    import table_emacs_org_mode_syntax as emacs
    import table_pandoc_syntax as pandoc
    import table_multi_markdown_syntax as markdown
    import table_re_structured_text_syntax as re_structured_text
    import table_textile_syntax as textile


def simple_syntax(table_configuration=None):
    return create_syntax("Simple", table_configuration)


def emacs_org_mode_syntax(table_configuration=None):
    return create_syntax("EmacsOrgMode", table_configuration)


def pandoc_syntax(table_configuration=None):
    return create_syntax("Pandoc", table_configuration)


def re_structured_text_syntax(table_configuration=None):
    return create_syntax("reStructuredText", table_configuration)


def multi_markdown_syntax(table_configuration=None):
    return create_syntax("MultiMarkdown", table_configuration=table_configuration)


def textile_syntax(table_configuration=None):
    return create_syntax("Textile", table_configuration=table_configuration)


def create_syntax(syntax_name, table_configuration=None):
    modules = {
        "Simple": simple,
        "EmacsOrgMode": emacs,
        "Pandoc": pandoc,
        "MultiMarkdown": markdown,
        "reStructuredText": re_structured_text,
        "Textile": textile
    }

    if syntax_name in modules:
        module = modules[syntax_name]
    else:
        raise ValueError("Syntax {syntax_name} doesn't supported"
                         .format(syntax_name=syntax_name))

    syntax = module.create_syntax(table_configuration)
    return syntax

########NEW FILE########
__FILENAME__ = table_lib_test
# table_lib_test.py - unittest for table_lib

# Copyright (C) 2012  Free Software Foundation, Inc.

# Author: Valery Kocubinsky
# Package: SublimeTableEditor
# Homepage: https://github.com/vkocubinsky/SublimeTableEditor

# This file is part of SublimeTableEditor.

# SublimeTableEditor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SublimeTableEditor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with SublimeTableEditor.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import difflib

try:
    from . import table_lib
    from . import table_base as tbase
except ValueError:
    import table_lib
    import table_base as tbase


class BaseTableTest(unittest.TestCase):

    def assert_table_equals(self, expected, formatted):
        if formatted != expected:
            diff = list(difflib.unified_diff(expected.splitlines(),
                                             formatted.splitlines()))
            msg = ("Formatted table and Expected table doesn't match. " +
                   "\nExpected:\n{0}" +
                   "\nActual:\n{1}" +
                   "\nDiff:\n {2}").format(expected, formatted, "\n".join(diff))
            self.fail(msg)


class SimpleSyntaxTest(BaseTableTest):

    def setUp(self):
        self.syntax = table_lib.simple_syntax()

    def testBasic(self):
        unformatted = """
| Name | Gender | Age |
| Text Column | Char Column | Number Column |
|-------------|-------------|---------------|
| Alisa | F | 21 |
| Alex | M | 22 |
""".strip()

        expected = """
|     Name    |    Gender   |      Age      |
| Text Column | Char Column | Number Column |
|-------------|-------------|---------------|
| Alisa       | F           |            21 |
| Alex        | M           |            22 |
""".strip()

        t = self.syntax.table_parser.parse_text(unformatted)
        formatted = t.render()
        self.assert_table_equals(expected, formatted)

    def testSpace(self):
        unformatted = """\
    | Name | Gender | Age |
    | Text Column | Char Column | Number Column |
    |-------------|-------------|---------------|
    | Alisa | F | 21 |
    | Alex | M | 22 |
""".rstrip()

        expected = """\
    |     Name    |    Gender   |      Age      |
    | Text Column | Char Column | Number Column |
    |-------------|-------------|---------------|
    | Alisa       | F           |            21 |
    | Alex        | M           |            22 |
""".rstrip()

        t = self.syntax.table_parser.parse_text(unformatted)
        formatted = t.render()
        self.assert_table_equals(expected, formatted)

    def testCustomAlignment(self):
        unformatted = """
| Name | Gender | Age |
| > | # | < |
|---|---|---|
| Alisa | F | 21 |
| Alex | M | 22 |
""".strip()

        expected = """
|  Name | Gender | Age |
| >>>>> | ###### | <<< |
|-------|--------|-----|
| Alisa |   F    | 21  |
|  Alex |   M    | 22  |
""".strip()

        t = self.syntax.table_parser.parse_text(unformatted)
        formatted = t.render()
        self.assert_table_equals(expected, formatted)

    def testMoveColumnRight(self):
        text = """
|     Name    |    Gender   |      Age      |
| Text Column | Char Column | Number Column |
|-------------|-------------|---------------|
| Alisa       | F           |            21 |
| Alex        | M           |            22 |
        """.strip()

        expected = """
|     Name    |      Age      |    Gender   |
| Text Column | Number Column | Char Column |
|-------------|---------------|-------------|
| Alisa       |            21 | F           |
| Alex        |            22 | M           |
        """.strip()

        t = self.syntax.table_parser.parse_text(text)
        d = self.syntax.table_driver
        msg, pos = d.editor_move_column_right(t, tbase.TablePos(0, 1))
        self.assertEqual(tbase.TablePos(0, 2), pos)
        self.assert_table_equals(expected, t.render())

    def testMoveColumnLeft(self):
        text = """
|     Name    |    Gender   |      Age      |
| Text Column | Char Column | Number Column |
|-------------|-------------|---------------|
| Alisa       | F           |            21 |
| Alex        | M           |            22 |
        """.strip()

        expected = """
|     Name    |      Age      |    Gender   |
| Text Column | Number Column | Char Column |
|-------------|---------------|-------------|
| Alisa       |            21 | F           |
| Alex        |            22 | M           |
        """.strip()

        t = self.syntax.table_parser.parse_text(text)
        d = self.syntax.table_driver
        msg, pos = d.editor_move_column_left(t, tbase.TablePos(0, 2))
        self.assertEqual(tbase.TablePos(0, 1), pos)
        self.assert_table_equals(expected, t.render())

    def testDeleteColumn(self):
        text = """
|     Name    |    Gender   |      Age      |
| Text Column | Char Column | Number Column |
|-------------|-------------|---------------|
| Alisa       | F           |            21 |
| Alex        | M           |            22 |
        """.strip()

        expected = """
|     Name    |      Age      |
| Text Column | Number Column |
|-------------|---------------|
| Alisa       |            21 |
| Alex        |            22 |
        """.strip()

        t = self.syntax.table_parser.parse_text(text)
        d = self.syntax.table_driver
        msg, pos = d.editor_delete_column(t, tbase.TablePos(0, 1))
        self.assertEqual(tbase.TablePos(0, 1), pos)
        self.assert_table_equals(expected, t.render())

    def testMoveRowDown(self):
        text = """
|     Name    |    Gender   |      Age      |
| Text Column | Char Column | Number Column |
|-------------|-------------|---------------|
| Alisa       | F           |            21 |
| Alex        | M           |            22 |
        """.strip()

        expected = """
|     Name    |    Gender   |      Age      |
| Text Column | Char Column | Number Column |
|-------------|-------------|---------------|
| Alex        | M           |            22 |
| Alisa       | F           |            21 |
        """.strip()

        t = self.syntax.table_parser.parse_text(text)
        d = self.syntax.table_driver
        msg, pos = d.editor_move_row_down(t, tbase.TablePos(3, 0))
        self.assertEqual(tbase.TablePos(4, 0), pos)
        self.assert_table_equals(expected, t.render())

    def testMoveRowUp(self):
        text = """
|     Name    |    Gender   |      Age      |
| Text Column | Char Column | Number Column |
|-------------|-------------|---------------|
| Alisa       | F           |            21 |
| Alex        | M           |            22 |
        """.strip()

        expected = """
|     Name    |    Gender   |      Age      |
| Text Column | Char Column | Number Column |
|-------------|-------------|---------------|
| Alex        | M           |            22 |
| Alisa       | F           |            21 |
        """.strip()

        t = self.syntax.table_parser.parse_text(text)
        d = self.syntax.table_driver
        msg, pos = d.editor_move_row_up(t, tbase.TablePos(4, 0))
        self.assertEqual(tbase.TablePos(3, 0), pos)
        self.assert_table_equals(expected, t.render())

    def testKillRow(self):
        text = """
|     Name    |    Gender   |      Age      |
| Text Column | Char Column | Number Column |
|-------------|-------------|---------------|
| Alisa       | F           |            21 |
| Alex        | M           |            22 |
        """.strip()

        expected = """
|     Name    |    Gender   |      Age      |
| Text Column | Char Column | Number Column |
|-------------|-------------|---------------|
| Alisa       | F           |            21 |
        """.strip()

        t = self.syntax.table_parser.parse_text(text)
        d = self.syntax.table_driver
        msg, pos = d.editor_kill_row(t, tbase.TablePos(4, 0))
        self.assertEqual(tbase.TablePos(3, 0), pos)
        self.assert_table_equals(expected, t.render())

    def testInsertColumn(self):
        text = """
|     Name    |    Gender   |      Age      |
| Text Column | Char Column | Number Column |
|-------------|-------------|---------------|
| Alisa       | F           |            21 |
| Alex        | M           |            22 |
        """.strip()

        expected = """
|     Name    |   |    Gender   |      Age      |
| Text Column |   | Char Column | Number Column |
|-------------|---|-------------|---------------|
| Alisa       |   | F           |            21 |
| Alex        |   | M           |            22 |
        """.strip()

        t = self.syntax.table_parser.parse_text(text)
        d = self.syntax.table_driver
        msg, pos = d.editor_insert_column(t, tbase.TablePos(0, 1))
        self.assertEqual(tbase.TablePos(0, 1), pos)
        self.assert_table_equals(expected, t.render())

    def testInsertRow(self):
        text = """
|     Name    |    Gender   |      Age      |
| Text Column | Char Column | Number Column |
|-------------|-------------|---------------|
| Alisa       | F           |            21 |
| Alex        | M           |            22 |
        """.strip()

        expected = """
|     Name    |    Gender   |      Age      |
| Text Column | Char Column | Number Column |
|-------------|-------------|---------------|
|             |             |               |
| Alisa       | F           |            21 |
| Alex        | M           |            22 |
        """.strip()

        t = self.syntax.table_parser.parse_text(text)
        d = self.syntax.table_driver
        msg, pos = d.editor_insert_row(t, tbase.TablePos(3, 0))
        self.assertEqual(tbase.TablePos(3, 0), pos)
        self.assert_table_equals(expected, t.render())

    def testInsertSingleHline(self):
        text = """
|     Name    |    Gender   |      Age      |
| Text Column | Char Column | Number Column |
| Alisa       | F           |            21 |
| Alex        | M           |            22 |
        """.strip()

        expected = """
|     Name    |    Gender   |      Age      |
| Text Column | Char Column | Number Column |
|-------------|-------------|---------------|
| Alisa       | F           |            21 |
| Alex        | M           |            22 |
        """.strip()

        t = self.syntax.table_parser.parse_text(text)
        d = self.syntax.table_driver
        msg, pos = d.editor_insert_single_hline(t, tbase.TablePos(1, 0))
        self.assertEqual(tbase.TablePos(1, 0), pos)
        self.assert_table_equals(expected, t.render())

    def testInsertHlineAndMove(self):
        text = """
|     Name    |    Gender   |      Age      |
| Text Column | Char Column | Number Column |
| Alisa       | F           |            21 |
| Alex        | M           |            22 |
        """.strip()

        expected = """
|     Name    |    Gender   |      Age      |
| Text Column | Char Column | Number Column |
|-------------|-------------|---------------|
| Alisa       | F           |            21 |
| Alex        | M           |            22 |
        """.strip()

        t = self.syntax.table_parser.parse_text(text)
        d = self.syntax.table_driver
        msg, pos = d.editor_insert_hline_and_move(t, tbase.TablePos(1, 0))
        self.assertEqual(tbase.TablePos(3, 0), pos)
        self.assert_table_equals(expected, t.render())

    def testInsertDoubleHline(self):
        text = """
|     Name    |    Gender   |      Age      |
| Text Column | Char Column | Number Column |
| Alisa       | F           |            21 |
| Alex        | M           |            22 |
        """.strip()

        expected = """
|     Name    |    Gender   |      Age      |
| Text Column | Char Column | Number Column |
|=============|=============|===============|
| Alisa       | F           |            21 |
| Alex        | M           |            22 |
        """.strip()

        t = self.syntax.table_parser.parse_text(text)
        d = self.syntax.table_driver
        msg, pos = d.editor_insert_double_hline(t, tbase.TablePos(1, 0))
        self.assertEqual(tbase.TablePos(1, 0), pos)
        self.assert_table_equals(expected, t.render())

    def testParseCsv(self):
        csv_text = """
a,b,c
1,2,3
        """.strip()

        expected = """
| a | b | c |
| 1 | 2 | 3 |
        """.strip()

        d = self.syntax.table_driver
        t = d.parse_csv(csv_text)
        self.assert_table_equals(expected, t.render())


class TextileSyntaxTest(BaseTableTest):

    def setUp(self):
        self.syntax = table_lib.textile_syntax()

    def testBasic(self):
        unformatted = """
|_. attribute list |
|<. align left |
| cell|
|>. align right|
|=. center|
|<>. justify |
|^. valign top |
|~. bottom|
|     >.  poor syntax
|(className). class|
|{key:value}. style|
""".strip()

        expected = """
|_.  attribute list |
|<. align left      |
| cell              |
|>.     align right |
|=.      center     |
|<>. justify        |
|^. valign top      |
|~. bottom          |
|>.     poor syntax |
|(className). class |
|{key:value}. style |
""".strip()

        t = self.syntax.table_parser.parse_text(unformatted)
        formatted = t.render()
        self.assert_table_equals(expected, formatted)

    def testCompoundSyntax(self):
        unformatted = r"""
|_>. header |_. centered header |
|>^. right and top align | long text to show alignment |
|=\2. centered colspan|
|<>(red). justified |~=. centered |
|{text-shadow:0 1px 1px black;}(highlight)<~. syntax overload | normal text |
""".strip()

        expected = r"""
|_>.                                                   header |_.      centered header      |
|>^.                                      right and top align | long text to show alignment |
|=\2.                                    centered colspan                                   |
|<>(red). justified                                           |~=.         centered         |
|{text-shadow:0 1px 1px black;}(highlight)<~. syntax overload | normal text                 |
""".strip()

        t = self.syntax.table_parser.parse_text(unformatted)
        formatted = t.render()
        self.assert_table_equals(expected, formatted)

    def testColspan(self):
        unformatted = r"""
|\2. spans two cols |
| col 1 | col 2 |
""".strip()

        expected = r"""
|\2. spans two cols   |
| col 1    | col 2    |
""".strip()

        t = self.syntax.table_parser.parse_text(unformatted)
        formatted = t.render()
        self.assert_table_equals(expected, formatted)

    def testRowspan(self):
        unformatted = r"""
|/3. spans 3 rows | a |
| b |
| c |
""".strip()

        expected = r"""
|/3. spans 3 rows | a |
| b               |
| c               |
""".strip()

        t = self.syntax.table_parser.parse_text(unformatted)
        formatted = t.render()
        self.assert_table_equals(expected, formatted)

    def testIntelligentFormatting(self):
        self.syntax.intelligent_formatting = True
        unformatted = r"""
|_. Attribute Name |_. Required |_. Value Type |
| \3. All Events                 |            |              |
""".strip()

        expected = r"""
|_. Attribute Name |_. Required |_. Value Type |
|\3. All Events                                |
""".strip()

        t = self.syntax.table_parser.parse_text(unformatted)
        formatted = t.render()
        self.assert_table_equals(expected, formatted)

    def testVisualTointernalIndex(self):

        unformatted = r"""
| a     | b     | c        | d     | e     | f        |
|\2. visual 0   | visual 1 |\2. visual 2   | visual 3 |
| 0     | 1     | 2        | 3     | 4     | 5        |
""".strip()

        t = self.syntax.table_parser.parse_text(unformatted)
        d = self.syntax.table_driver
        #formatted = t.render()

        # test visual_to_internal_index
        self.assertEqual(tbase.TablePos(1, 0), d.visual_to_internal_index(t, tbase.TablePos(1, 0)))
        self.assertEqual(tbase.TablePos(1, 2), d.visual_to_internal_index(t, tbase.TablePos(1, 1)))
        self.assertEqual(tbase.TablePos(1, 3), d.visual_to_internal_index(t, tbase.TablePos(1, 2)))
        self.assertEqual(tbase.TablePos(1, 5), d.visual_to_internal_index(t, tbase.TablePos(1, 3)))

        self.assertEqual(tbase.TablePos(1, 5), d.visual_to_internal_index(t, tbase.TablePos(1, 1000)))

        # test trivial
        for col in range(len(t[0])):
            self.assertEqual(tbase.TablePos(0, col), d.visual_to_internal_index(t, tbase.TablePos(0, col)))
            self.assertEqual(tbase.TablePos(2, col), d.visual_to_internal_index(t, tbase.TablePos(2, col)))

            self.assertEqual(tbase.TablePos(0, col), d.internal_to_visual_index(t, tbase.TablePos(0, col)))
            self.assertEqual(tbase.TablePos(2, col), d.internal_to_visual_index(t, tbase.TablePos(2, col)))

        # test internal_to_visual_index
        self.assertEqual(tbase.TablePos(1, 0), d.internal_to_visual_index(t, tbase.TablePos(1, 0)))
        self.assertEqual(tbase.TablePos(1, 0), d.internal_to_visual_index(t, tbase.TablePos(1, 1)))
        self.assertEqual(tbase.TablePos(1, 1), d.internal_to_visual_index(t, tbase.TablePos(1, 2)))
        self.assertEqual(tbase.TablePos(1, 2), d.internal_to_visual_index(t, tbase.TablePos(1, 3)))
        self.assertEqual(tbase.TablePos(1, 2), d.internal_to_visual_index(t, tbase.TablePos(1, 4)))
        self.assertEqual(tbase.TablePos(1, 3), d.internal_to_visual_index(t, tbase.TablePos(1, 5)))


class MultiMarkdownSyntaxTest(BaseTableTest):

    def setUp(self):
        self.syntax = table_lib.multi_markdown_syntax()

    def testBasic(self):
        unformatted = """\
| Name | Gender | Age |
| Text Column | Char Column | Number Column |
|-:|:-:|:-|
| Alisa | F | 21 |
| Alex | M | 22 |
""".rstrip()

        expected = """\
|     Name    |    Gender   |      Age      |
| Text Column | Char Column | Number Column |
| ----------: | :---------: | :------------ |
|       Alisa |      F      | 21            |
|        Alex |      M      | 22            |
""".rstrip()

        t = self.syntax.table_parser.parse_text(unformatted)
        formatted = t.render()
        self.assert_table_equals(expected, formatted)

    def testColspan(self):
                unformatted = """\
    |                 |          Grouping           ||
    |   First Header  | Second Header | Third Header |
    |    ------------ | :-------:     | --------:    |
    |   Content       |          *Long Cell*        ||
    |   Content       |   **Cell**    |         Cell |
    |   New section   |     More      |         Data |
    |   And more      |            And more          |
    | :---: |||
        """.rstrip()

                expected = """\
    |              |           Grouping          ||
    | First Header | Second Header | Third Header |
    | ------------ | :-----------: | -----------: |
    | Content      |         *Long Cell*         ||
    | Content      |    **Cell**   |         Cell |
    | New section  |      More     |         Data |
    | And more     |    And more   |              |
    | :---------------------------------------: |||
        """.rstrip()

                t = self.syntax.table_parser.parse_text(unformatted)
                formatted = t.render()
                self.assert_table_equals(expected, formatted)

    text = """

"""


class ReStructuredTextSyntaxTest(BaseTableTest):

    def setUp(self):
        self.syntax = table_lib.re_structured_text_syntax()

    def testBasic(self):
        unformatted = """\
+-------------+
| widget code |
+===============================================+
| code-block::javascript                        |
|                                               |
|    widget.dispatchEvent('onSetTags', object); |
+-----------------------------------------------+
""".rstrip()

        expected = """\
+-----------------------------------------------+
|                  widget code                  |
+===============================================+
| code-block::javascript                        |
|                                               |
|    widget.dispatchEvent('onSetTags', object); |
+-----------------------------------------------+
""".rstrip()

        self.syntax.keep_space_left = True
        t = self.syntax.table_parser.parse_text(unformatted)
        formatted = t.render()
        self.assert_table_equals(expected, formatted)

    def testDetectHeader(self):
        unformatted = """\
+---------+
|  header |
+------------------------------+
|    long and shifted data row |
+------------------------------+
""".rstrip()

        expected = """\
+------------------------------+
|  header                      |
+------------------------------+
|    long and shifted data row |
+------------------------------+
""".rstrip()

        self.syntax.detect_header = False
        self.syntax.keep_space_left = True
        t = self.syntax.table_parser.parse_text(unformatted)
        formatted = t.render()
        self.assert_table_equals(expected, formatted)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = table_line_parser
# table_line_parser.py - Parse one line in a table.

# Copyright (C) 2012  Free Software Foundation, Inc.

# Author: Valery Kocubinsky
# Package: SublimeTableEditor
# Homepage: https://github.com/vkocubinsky/SublimeTableEditor

# This file is part of SublimeTableEditor.

# SublimeTableEditor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SublimeTableEditor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with SublimeTableEditor.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
from __future__ import division

import re


class LineRegion:
    def __init__(self, begin, end):
        self.begin = begin
        self.end = end

    def __repr__(self):
        return "LineRegion(begin={0.begin}, end={0.end})".format(self)

    def __str__(self):
        return self.__repr__()


class LineCell:
    def __init__(self, line_text, left_border, right_border):
        self.cell_region = LineRegion(left_border.end, right_border.begin)
        self.left_border = left_border
        self.right_border = right_border
        self.text = line_text[self.cell_region.begin:self.cell_region.end]
        if self.right_border.begin == self.right_border.end:
            self.right_border_text = '|'
        else:
            self.right_border_text = line_text[self.right_border.begin:self.right_border.end]
        self.left_border_text = line_text[self.left_border.begin:self.left_border.end]


class Line:
    def __init__(self):
        self.cells = []
        self.prefix = ""

    def str_cols(self):
        return [cell.text for cell in self.cells]

    def field_num(self, pos):
        for ind, cell in enumerate(self.cells):
            if cell.right_border.end > pos:
                return ind
        else:
            return len(self.cells) - 1


class LineParser:
    def __init__(self, border_pattern):
        self.border_pattern = border_pattern

    def parse(self, line_text):

        line = Line()

        mo = re.search(r"[^\s]", line_text)
        if mo:
            line.prefix = line_text[:mo.start()]
        else:
            line.prefix = ""

        borders = []

        last_border_end = 0
        for m in re.finditer(self.border_pattern, line_text):
            borders.append(LineRegion(m.start(), m.end()))
            last_border_end = m.end()

        if last_border_end < len(line_text.rstrip()):
            borders.append(LineRegion(len(line_text), len(line_text)))

        left_border = None
        for right_border in borders:
            if left_border is None:
                left_border = right_border
            else:
                line.cells.append(LineCell(line_text, left_border, right_border))
                left_border = right_border
        return line


class LineParserPlus:

    def __init__(self, border_pattern):
        self.plus_line_parser = LineParser("(?:[+|])")

        self.plus_line_pattern = re.compile("^\s*[+]")
        self.single_hline_pattern = re.compile('^\s*[|+]\s*-[\s|+-]+$')
        self.double_hline_pattern = re.compile('^\s*[|+]\s*=[\s|+=]+$')

        self.data_line_parser = LineParser(border_pattern)

    def parse(self, line_text):
        if (self.single_hline_pattern.match(line_text) or
                self.double_hline_pattern.match(line_text) or
                self.plus_line_pattern.match(line_text)):
            return self.plus_line_parser.parse(line_text)
        else:
            return self.data_line_parser.parse(line_text)


########NEW FILE########
__FILENAME__ = table_multi_markdown_syntax
# table_multi_markdown_syntax.py - Support MultiMarkdown table syntax

# Copyright (C) 2012  Free Software Foundation, Inc.

# Author: Valery Kocubinsky
# Package: SublimeTableEditor
# Homepage: https://github.com/vkocubinsky/SublimeTableEditor

# This file is part of SublimeTableEditor.

# SublimeTableEditor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SublimeTableEditor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with SublimeTableEditor.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import print_function
from __future__ import division

import math
import re


try:
    from . import table_base as tbase
    from . import table_line_parser as tparser
except ValueError:
    import table_base as tbase
    import table_line_parser as tparser


def create_syntax(table_configuration=None):
    return MultiMarkdownTableSyntax(table_configuration)


class MultiMarkdownTableSyntax(tbase.TableSyntax):

    def __init__(self, table_configuration):
        tbase.TableSyntax.__init__(self, "Multi Markdown", table_configuration)

        self.line_parser = tparser.LineParserPlus("(?:(?:\|\|+)|(?:\|))")
        self.table_parser = MultiMarkdownTableParser(self)
        self.table_driver = MultiMarkdownTableDriver(self)


class MultiMarkdownAlignColumn(tbase.Column):
    PATTERN = r"^\s*([\:]?[\-]+[\:]?)\s*$"

    def __init__(self, row, data):
        tbase.Column.__init__(self, row)
        col = data.strip()
        if col.count(':') == 2:
            self._align_follow = tbase.Column.ALIGN_CENTER
        elif col[0] == ':':
            self._align_follow = tbase.Column.ALIGN_LEFT
        elif col[-1] == ':':
            self._align_follow = tbase.Column.ALIGN_RIGHT
        else:
            self._align_follow = None

    def min_len(self):
        return int(math.ceil(self.total_min_len()/self.colspan))

    def total_min_len(self):
        # ' :-: ' or ' :-- ' or ' --: ' or ' --- '
        return 5 + self.colspan - 1

    def render(self):
        total_col_len = self.col_len + (self.colspan - 1) + sum([col.col_len for col in self.pseudo_columns])
        total_col_len = total_col_len - (self.colspan - 1)

        if self._align_follow == tbase.Column.ALIGN_CENTER:
            return ' :' + '-' * (total_col_len - 4) + ': '
        elif self._align_follow == tbase.Column.ALIGN_LEFT:
            return ' :' + '-' * (total_col_len - 4) + '- '
        elif self._align_follow == tbase.Column.ALIGN_RIGHT:
            return ' -' + '-' * (total_col_len - 4) + ': '
        else:
            return ' -' + '-' * (total_col_len - 4) + '- '

    def align_follow(self):
        return self._align_follow

    @staticmethod
    def match_cell(str_col):
        return re.match(MultiMarkdownAlignColumn.PATTERN, str_col)


class MultiMarkdownAlignRow(tbase.Row):

    def new_empty_column(self):
        return MultiMarkdownAlignColumn(self, '-')

    def create_column(self, text):
        return MultiMarkdownAlignColumn(self, text)

    def is_header_separator(self):
        return True

    def is_separator(self):
        return True

    def is_align(self):
        return True


class MultiMarkdownTableParser(tbase.BaseTableParser):

    def _is_multi_markdown_align_row(self, str_cols):
        if len(str_cols) == 0:
            return False
        for col in str_cols:
            if not MultiMarkdownAlignColumn.match_cell(col):
                return False
        return True

    def create_row(self, table, line):
        if self._is_multi_markdown_align_row(line.str_cols()):
            row = MultiMarkdownAlignRow(table)
        else:
            row = tbase.DataRow(table)
        return row

    def create_column(self, table, row, line_cell):
        column = tbase.BaseTableParser.create_column(self, table, row, line_cell)
        if len(line_cell.right_border_text) > 1:
            column.colspan = len(line_cell.right_border_text)
        return column


class MultiMarkdownTableDriver(tbase.TableDriver):

    def editor_insert_single_hline(self, table, table_pos):
        table.rows.insert(table_pos.row_num + 1, MultiMarkdownAlignRow(table))
        table.pack()
        return ("Single separator row inserted",
                tbase.TablePos(table_pos.row_num, table_pos.field_num))

    def editor_insert_hline_and_move(self, table, table_pos):
        table.rows.insert(table_pos.row_num + 1, MultiMarkdownAlignRow(table))
        table.pack()
        if table_pos.row_num + 2 < len(table):
            if table[table_pos.row_num + 2].is_separator():
                table.insert_empty_row(table_pos.row_num + 2)
        else:
            table.insert_empty_row(table_pos.row_num + 2)
        return("Single separator row inserted",
               tbase.TablePos(table_pos.row_num + 2, 0))

########NEW FILE########
__FILENAME__ = table_pandoc_syntax
# table_pandoc_syntax.py - Pandoc table syntax

# Copyright (C) 2012  Free Software Foundation, Inc.

# Author: Valery Kocubinsky
# Package: SublimeTableEditor
# Homepage: https://github.com/vkocubinsky/SublimeTableEditor

# This file is part of SublimeTableEditor.

# SublimeTableEditor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SublimeTableEditor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with SublimeTableEditor.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import print_function
from __future__ import division


try:
    from . import table_base as tbase
    from . import table_border_syntax as tborder
except ValueError:
    import table_base as tbase
    import table_border_syntax as tborder


def create_syntax(table_configuration=None):
    return PandocTableSyntax(table_configuration)


class PandocTableSyntax(tbase.TableSyntax):

    def __init__(self, table_configuration):
        tbase.TableSyntax.__init__(self, "Pandoc", table_configuration)

        self.table_parser = tborder.BorderTableParser(self)
        self.table_driver = tborder.BorderTableDriver(self)

        self.hline_out_border = '+'
        self.hline_in_border = '+'

########NEW FILE########
__FILENAME__ = table_plugin
# table_plugin.py - sublime plugins for pretty print text table

# Copyright (C) 2012  Free Software Foundation, Inc.

# Author: Valery Kocubinsky
# Package: SublimeTableEditor
# Homepage: https://github.com/vkocubinsky/SublimeTableEditor

# This file is part of SublimeTableEditor.

# SublimeTableEditor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SublimeTableEditor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with SublimeTableEditor.  If not, see <http://www.gnu.org/licenses/>.

import sublime
import sublime_plugin
import re

try:
    from . import table_lib as tlib
    from . import table_base as tbase
except ValueError:
    import table_lib as tlib
    import table_base as tbase


class TableContext:

    def __init__(self, view, sel, syntax):
        self.view = view
        (sel_row, sel_col) = self.view.rowcol(sel.begin())
        self.syntax = syntax

        self.first_table_row = self._get_first_table_row(sel_row, sel_col)
        self.last_table_row = self._get_last_table_row(sel_row, sel_col)
        self.table_text = self._get_table_text(self.first_table_row, self.last_table_row)
        self.visual_field_num = self._visual_field_num(sel_row, sel_col)
        self.row_num = sel_row - self.first_table_row

        self.table_pos = tbase.TablePos(self.row_num, self.visual_field_num)

        self.table = self.syntax.table_parser.parse_text(self.table_text)
        self.table_driver = self.syntax.table_driver
        self.field_num = self.table_driver.visual_to_internal_index(self.table, self.table_pos).field_num

    def _get_table_text(self, first_table_row, last_table_row):
        begin_point = self.view.line(self.view.text_point(first_table_row, 0)
                                     ).begin()
        end_point = self.view.line(self.view.text_point(last_table_row, 0)
                                   ).end()
        return self.view.substr(sublime.Region(begin_point, end_point))

    def _get_last_table_row(self, sel_row, sel_col):
        row = sel_row
        last_table_row = sel_row
        last_line = self.view.rowcol(self.view.size())[0]
        while (row <= last_line and self._is_table_row(row)):
            last_table_row = row
            row = row + 1
        return last_table_row

    def _get_first_table_row(self, sel_row, sel_col):
        row = sel_row
        first_table_row = sel_row
        while (row >= 0 and self._is_table_row(row)):
            first_table_row = row
            row = row - 1
        return first_table_row

    def _is_table_row(self, row):
        text = self._get_text(row)
        return self.syntax.table_parser.is_table_row(text)

    def _visual_field_num(self, sel_row, sel_col):
        line_text = self._get_text(sel_row)
        line = self.syntax.line_parser.parse(line_text)
        return line.field_num(sel_col)

    def _get_text(self, row):
        point = self.view.text_point(row, 0)
        region = self.view.line(point)
        text = self.view.substr(region)
        return text


class AbstractTableCommand(sublime_plugin.TextCommand):

    def detect_syntax(self):
        if self.view.settings().has("table_editor_syntax"):
            syntax_name = self.view.settings().get("table_editor_syntax")
        else:
            syntax_name = self.auto_detect_syntax_name()

        table_configuration = tbase.TableConfiguration()

        border_style = (self.view.settings().get("table_editor_border_style", None)
                        or self.view.settings().get("table_editor_style", None))
        if border_style == "emacs":
            table_configuration.hline_out_border = '|'
            table_configuration.hline_in_border = '+'
        elif border_style == "grid":
            table_configuration.hline_out_border = '+'
            table_configuration.hline_in_border = '+'
        elif border_style == "simple":
            table_configuration.hline_out_border = '|'
            table_configuration.hline_in_border = '|'

        if self.view.settings().has("table_editor_custom_column_alignment"):
            table_configuration.custom_column_alignment = self.view.settings().get("table_editor_custom_column_alignment")

        if self.view.settings().has("table_editor_keep_space_left"):
            table_configuration.keep_space_left = self.view.settings().get("table_editor_keep_space_left")

        if self.view.settings().has("table_editor_align_number_right"):
            table_configuration.align_number_right = self.view.settings().get("table_editor_align_number_right")

        if self.view.settings().has("table_editor_detect_header"):
            table_configuration.detect_header = self.view.settings().get("table_editor_detect_header")

        if self.view.settings().has("table_editor_intelligent_formatting"):
            table_configuration.intelligent_formatting = self.view.settings().get("table_editor_intelligent_formatting")

        syntax = tlib.create_syntax(syntax_name, table_configuration)
        return syntax

    def auto_detect_syntax_name(self):
        view_syntax = self.view.settings().get('syntax')
        if (view_syntax == 'Packages/Markdown/MultiMarkdown.tmLanguage' or
                view_syntax == 'Packages/Markdown/Markdown.tmLanguage'):
            return "MultiMarkdown"
        elif view_syntax == 'Packages/Textile/Textile.tmLanguage':
            return "Textile"
        elif (view_syntax == 'Packages/RestructuredText/reStructuredText.tmLanguage'):
            return "reStructuredText"
        else:
            return "Simple"

    def merge(self, edit, ctx):
        table = ctx.table
        new_lines = table.render_lines()
        first_table_row = ctx.first_table_row
        last_table_row = ctx.last_table_row
        rows = range(first_table_row, last_table_row + 1)
        for row, new_text in zip(rows, new_lines):
            region = self.view.line(self.view.text_point(row, 0))
            old_text = self.view.substr(region)
            if old_text != new_text:
                self.view.replace(edit, region, new_text)

        #case 1: some lines inserted
        if len(rows) < len(new_lines):
            row = last_table_row
            for new_text in new_lines[len(rows):]:
                end_point = self.view.line(self.view.text_point(row, 0)).end()
                self.view.insert(edit, end_point, "\n" + new_text)
                row = row + 1
        #case 2: some lines deleted
        elif len(rows) > len(new_lines):
            for row in rows[len(new_lines):]:
                region = self.view.line(self.view.text_point(row, 0))
                self.view.erase(edit, region)

    def create_context(self, sel):
        return TableContext(self.view, sel, self.detect_syntax())

    def run(self, edit):
        new_sels = []
        for sel in self.view.sel():
            new_sel = self.run_one_sel(edit, sel)
            new_sels.append(new_sel)
        self.view.sel().clear()
        for sel in new_sels:
            self.view.sel().add(sel)
            self.view.show(sel, False)

    def run_one_sel(self, edit, sel):
        ctx = self.create_context(sel)
        try:
            msg, table_pos = self.run_operation(ctx)
            self.merge(edit, ctx)
            sublime.status_message("Table Editor: {0}".format(msg))
            return self.table_pos_sel(ctx, table_pos)
        except tbase.TableException as err:
            sublime.status_message("Table Editor: {0}".format(err))
            return self.table_pos_sel(ctx, ctx.table_pos)

    def visual_field_sel(self, ctx, row_num, visual_field_num):
        if ctx.table.empty():
            pt = self.view.text_point(ctx.first_table_row, 0)
        else:
            pos = tbase.TablePos(row_num, visual_field_num)
            col = ctx.table_driver.get_cursor(ctx.table, pos)
            pt = self.view.text_point(ctx.first_table_row + row_num, col)
        return sublime.Region(pt, pt)

    def table_pos_sel(self, ctx, table_pos):
        return self.visual_field_sel(ctx, table_pos.row_num,
                                     table_pos.field_num)

    def field_sel(self, ctx, row_num, field_num):
        if ctx.table.empty():
            visual_field_num = 0
        else:
            pos = tbase.TablePos(row_num, field_num)
            visual_field_num = ctx.table_driver.internal_to_visual_index(ctx.table, pos).field_num
        return self.visual_field_sel(ctx, row_num, visual_field_num)


class TableEditorAlignCommand(AbstractTableCommand):
    """
    Key: ctrl+shift+a
    Re-align the table without change the current table field.
    Move cursor to begin of the current table field.
    """
    def run_operation(self, ctx):
        return ctx.table_driver.editor_align(ctx.table, ctx.table_pos)


class TableEditorNextField(AbstractTableCommand):
    """
    Key: tab
    Re-align the table, move to the next field.
    Creates a new row if necessary.
    """
    def run_operation(self, ctx):
        return ctx.table_driver.editor_next_field(ctx.table, ctx.table_pos)


class TableEditorPreviousField(AbstractTableCommand):
    """
    Key: shift+tab
    Re-align, move to previous field.
    """
    def run_operation(self, ctx):
        return ctx.table_driver.editor_previous_field(ctx.table, ctx.table_pos)


class TableEditorNextRow(AbstractTableCommand):
    """
    Key: enter
    Re-align the table and move down to next row.
    Creates a new row if necessary.
    At the beginning or end of a line, enter still does new line.
    """
    def run_operation(self, ctx):
        return ctx.table_driver.editor_next_row(ctx.table, ctx.table_pos)


class TableEditorMoveColumnLeft(AbstractTableCommand):
    """
    Key: alt+left
    Move the current column left.
    """
    def run_operation(self, ctx):
        return ctx.table_driver.editor_move_column_left(ctx.table,
                                                        ctx.table_pos)


class TableEditorMoveColumnRight(AbstractTableCommand):
    """
    Key: alt+right
    Move the current column right.
    """
    def run_operation(self, ctx):
        return ctx.table_driver.editor_move_column_right(ctx.table,
                                                         ctx.table_pos)


class TableEditorDeleteColumn(AbstractTableCommand):
    """
    Key: alt+shift+left
    Kill the current column.
    """
    def run_operation(self, ctx):
        return ctx.table_driver.editor_delete_column(ctx.table,
                                                     ctx.table_pos)


class TableEditorInsertColumn(AbstractTableCommand):
    """
    Keys: alt+shift+right
    Insert a new column to the left of the cursor position.
    """
    def run_operation(self, ctx):
        return ctx.table_driver.editor_insert_column(ctx.table,
                                                     ctx.table_pos)


class TableEditorKillRow(AbstractTableCommand):
    """
    Key : alt+shift+up
    Kill the current row.
    """
    def run_operation(self, ctx):
        return ctx.table_driver.editor_kill_row(ctx.table, ctx.table_pos)


class TableEditorInsertRow(AbstractTableCommand):
    """
    Key: alt+shift+down
    Insert a new row above the current row.
    """
    def run_operation(self, ctx):
        return ctx.table_driver.editor_insert_row(ctx.table, ctx.table_pos)


class TableEditorMoveRowUp(AbstractTableCommand):
    """
    Key: alt+up
    Move the current row up.
    """
    def run_operation(self, ctx):
        return ctx.table_driver.editor_move_row_up(ctx.table, ctx.table_pos)


class TableEditorMoveRowDown(AbstractTableCommand):
    """
    Key: alt+down
    Move the current row down.
    """
    def run_operation(self, ctx):
        return ctx.table_driver.editor_move_row_down(ctx.table,
                                                     ctx.table_pos)


class TableEditorInsertSingleHline(AbstractTableCommand):
    """
    Key: ctrl+k,-
    Insert single horizontal line below current row.
    """
    def run_operation(self, ctx):
        return ctx.table_driver.editor_insert_single_hline(ctx.table,
                                                           ctx.table_pos)


class TableEditorInsertDoubleHline(AbstractTableCommand):
    """
    Key: ctrl+k,=
    Insert double horizontal line below current row.
    """
    def run_operation(self, ctx):
        return ctx.table_driver.editor_insert_double_hline(ctx.table,
                                                           ctx.table_pos)


class TableEditorHlineAndMove(AbstractTableCommand):
    """
    Key: ctrl+k, enter
    Insert a horizontal line below current row,
    and move the cursor into the row below that line.
    """
    def run_operation(self, ctx):
        return ctx.table_driver.editor_insert_hline_and_move(ctx.table,
                                                             ctx.table_pos)


class TableEditorSplitColumnDown(AbstractTableCommand):
    """
    Key: alt+enter
    Split rest of cell down from current cursor position,
    insert new line bellow if current row is last row in the table
    or if next line is hline
    """
    def remove_rest_line(self, edit, sel):
        end_region = self.view.find("\|",
                                    sel.begin())
        rest_region = sublime.Region(sel.begin(), end_region.begin())
        rest_data = self.view.substr(rest_region)
        self.view.replace(edit, rest_region, "")
        return rest_data.strip()

    def run_one_sel(self, edit, sel):
        ctx = self.create_context(sel)
        field_num = ctx.field_num
        row_num = ctx.row_num
        if (ctx.table[row_num].is_separator() or
                ctx.table[row_num].is_header_separator()):
            sublime.status_message("Table Editor: Split column is not "
                                   "permitted for separator or header "
                                   "separator line")
            return self.table_pos_sel(ctx, ctx.table_pos)
        if row_num + 1 < len(ctx.table):
            if len(ctx.table[row_num + 1]) - 1 < field_num:
                sublime.status_message("Table Editor: Split column is not "
                                       "permitted for short line")
                return self.table_pos_sel(ctx, ctx.table_pos)
            elif ctx.table[row_num + 1][field_num].pseudo():
                sublime.status_message("Table Editor: Split column is not "
                                       "permitted to colspan column")
                return self.table_pos_sel(ctx, ctx.table_pos)

        (sel_row, sel_col) = self.view.rowcol(sel.begin())
        rest_data = self.remove_rest_line(edit, sel)

        ctx = self.create_context(sel)

        field_num = ctx.field_num
        row_num = ctx.row_num

        if row_num + 1 == len(ctx.table) or ctx.table[row_num + 1].is_separator():
            ctx.table.insert_empty_row(row_num + 1)

        row_num = row_num + 1
        ctx.table[row_num][field_num].data = rest_data + " " + ctx.table[row_num][field_num].data.strip()
        ctx.table.pack()
        self.merge(edit, ctx)
        sublime.status_message("Table Editor: Column splitted down")
        return self.field_sel(ctx, row_num, field_num)


class TableEditorJoinLines(AbstractTableCommand):
    """
    Key: ctrl+j
    Join current row and next row into one if next row is not hline
    """
    def run_operation(self, ctx):
        return ctx.table_driver.editor_join_lines(ctx.table, ctx.table_pos)


class TableEditorCsvToTable(AbstractTableCommand):
    """
    Command: table_csv_to_table
    Key: ctrl+k, |
    Convert selected CSV region into table
    """

    def run_one_sel(self, edit, sel):
        if sel.empty():
            return sel
        else:
            syntax = self.detect_syntax()
            text = self.view.substr(sel)
            table = syntax.table_driver.parse_csv(text)
            self.view.replace(edit, sel, table.render())

            first_row = self.view.rowcol(sel.begin())[0]

            pt = self.view.text_point(first_row, syntax.table_driver.get_cursor(table, tbase.TablePos(0, 0)))
            sublime.status_message("Table Editor: Table created from CSV")
            return sublime.Region(pt, pt)


class TableEditorDisableForCurrentView(sublime_plugin.TextCommand):

    def run(self, args, prop):
        self.view.settings().set(prop, False)


class TableEditorEnableForCurrentView(sublime_plugin.TextCommand):

    def run(self, args, prop):
        self.view.settings().set(prop, True)


class TableEditorDisableForCurrentSyntax(sublime_plugin.TextCommand):

    def run(self, edit):
        syntax = self.view.settings().get('syntax')
        if syntax is not None:
            m = re.search("([^/]+)[.]tmLanguage$", syntax)
            if m:
                base_name = m.group(1) + ".sublime-settings"
                settings = sublime.load_settings(base_name)
                settings.erase("enable_table_editor")
                sublime.save_settings(base_name)


class TableEditorEnableForCurrentSyntax(sublime_plugin.TextCommand):

    def run(self, edit):
        syntax = self.view.settings().get('syntax')
        if syntax is not None:
            m = re.search("([^/]+)[.]tmLanguage$", syntax)
            if m:
                base_name = m.group(1) + ".sublime-settings"
                settings = sublime.load_settings(base_name)
                settings.set("enable_table_editor", True)
                sublime.save_settings(base_name)


class TableEditorSetSyntax(sublime_plugin.TextCommand):

    def run(self, edit, syntax):
        self.view.settings().set("enable_table_editor", True)
        self.view.settings().set("table_editor_syntax", syntax)
        sublime.status_message("Table Editor: set syntax to '{0}'"
                               .format(syntax))

########NEW FILE########
__FILENAME__ = table_plugin_test
# table_plugin_test.py - sublime plugin with integration tests

# Copyright (C) 2012  Free Software Foundation, Inc.

# Author: Valery Kocubinsky
# Package: SublimeTableEditor
# Homepage: https://github.com/vkocubinsky/SublimeTableEditor

# This file is part of SublimeTableEditor.

# SublimeTableEditor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SublimeTableEditor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with SublimeTableEditor.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
import sublime
import sublime_plugin


class CommandDef:

    def __init__(self, name, args=None):
        self.name = name
        self.args = args


class CallbackTest:
    def __init__(self, name, syntax):
        self.name = name
        self.commands = []
        self.commands.append(CommandDef("table_editor_set_syntax",
                                        {"syntax": syntax}))
        self.commands.append(CommandDef("table_editor_disable_for_current_view",
                                        {"prop": "table_editor_keep_space_left"}))
        self.commands.append(CommandDef("table_editor_enable_for_current_view",
                                        {"prop": "table_editor_detect_header"}))
        self.commands.append(CommandDef("table_editor_enable_for_current_view",
                                        {"prop": "table_editor_align_number_right"}))
        self.commands.append(CommandDef("table_editor_enable_for_current_view",
                                        {"prop": "table_editor_intelligent_formatting"}))
        self.commands.append(CommandDef("select_all"))
        self.commands.append(CommandDef("cut"))

    def expected_value(self):
        pass

    def test(actual_value):
        pass


class SimpleBasicEditingTest(CallbackTest):
    def __init__(self):
        CallbackTest.__init__(self, "Basic Editing", "Simple")
        self.commands.append(CommandDef("insert", {"characters": self.description}))
        self.commands.append(CommandDef("insert", {"characters": """
| Name | Phone |
|-"""}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "Anna"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "123456789"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "Alexander"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "987654321"}))
        self.commands.append(CommandDef("table_editor_next_field"))

    @property
    def description(self):
        return """Test: {0}
- Simple Table Syntax
- Create simple table
- Navigate with tab key
- Automatic row creation
- Fill the table
""".format(self.name)

    def expected_value(self):
        return """{0}
|    Name   |   Phone   |
|-----------|-----------|
| Anna      | 123456789 |
| Alexander | 987654321 |
|           |           |""".format(self.description)


class SimpleQuickTableCreateTest(CallbackTest):
    def __init__(self):
        CallbackTest.__init__(self, "Quick Table Creation", "Simple")
        self.commands.append(CommandDef("insert", {"characters": self.description}))
        self.commands.append(CommandDef("insert", {"characters": """
| Name | Phone"""}))
        self.commands.append(CommandDef("table_editor_hline_and_move"))

    @property
    def description(self):
        return """Test: {0}
- Simple Table Syntax
- Quick table creation with key ctrl+k,enter
""".format(self.name)

    def expected_value(self):
        return """{0}
| Name | Phone |
|------|-------|
|      |       |""".format(self.description)


class SimpleGridTableTest(CallbackTest):
    def __init__(self):
        CallbackTest.__init__(self, "Grid Table Creation", "Simple")
        self.commands.append(CommandDef("insert", {"characters": self.description}))
        self.commands.append(CommandDef("insert", {"characters": """
| Name | Phone |
|="""}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "Anna"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "123456789"}))
        self.commands.append(CommandDef("table_editor_hline_and_move"))
        self.commands.append(CommandDef("insert", {"characters": "Alexander"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "987654321"}))
        self.commands.append(CommandDef("table_editor_hline_and_move"))

    @property
    def description(self):
        return """Test: {0}
- Simple Table Syntax
- Create simple table
- Use double hline
- Add lines separated by single hline
""".format(self.name)

    def expected_value(self):
        return """{0}
|    Name   |   Phone   |
|===========|===========|
| Anna      | 123456789 |
|-----------|-----------|
| Alexander | 987654321 |
|-----------|-----------|
|           |           |""".format(self.description)


class SimpleColumnsTest(CallbackTest):
    def __init__(self):
        CallbackTest.__init__(self, "Work with columns", "Simple")
        self.commands.append(CommandDef("insert", {"characters": self.description}))
        self.commands.append(CommandDef("insert", {"characters": """
| Name | Phone |
|-"""}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "Anna"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "123456789"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "Alexander"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "987654321"}))
        self.commands.append(CommandDef("table_editor_next_row"))
        self.commands.append(CommandDef("table_editor_insert_column"))
        for i in range(0, 3):
            self.commands.append(CommandDef("table_editor_previous_field"))
        self.commands.append(CommandDef("insert", {"characters": "28"}))
        for i in range(0, 3):
            self.commands.append(CommandDef("table_editor_previous_field"))
        self.commands.append(CommandDef("insert", {"characters": "32"}))
        for i in range(0, 3):
            self.commands.append(CommandDef("table_editor_previous_field"))
        self.commands.append(CommandDef("insert", {"characters": "Age"}))
        self.commands.append(CommandDef("table_editor_move_column_right"))
        self.commands.append(CommandDef("table_editor_delete_column"))

    @property
    def description(self):
        return """Test: {0}
- Simple Table Syntax
- Create simple table
- Insert And Fill Column
- Move Column Right
- Delete Column
""".format(self.name)

    def expected_value(self):
        return """{0}
|    Name   |   Phone   |
|-----------|-----------|
| Anna      | 123456789 |
| Alexander | 987654321 |
|           |           |""".format(self.description)


class SimpleRowsTest(CallbackTest):
    def __init__(self):
        CallbackTest.__init__(self, "Work with rows", "Simple")
        self.commands.append(CommandDef("insert", {"characters": self.description}))
        self.commands.append(CommandDef("insert", {"characters": """
|    Name   |   Phone   | Age |
|-----------|-----------|-----|
| Anna      | 123456789 |  32 |
| Alexander | 987654321 |  28 |"""}))
        self.commands.append(CommandDef("table_editor_next_field"))
        for i in range(4):
            self.commands.append(CommandDef("table_editor_previous_field"))
        self.commands.append(CommandDef("table_editor_insert_row"))
        self.commands.append(CommandDef("table_editor_kill_row"))

    @property
    def description(self):
        return """Test: {0}
- Simple Table Syntax
- Insert Row
- Delete Row
""".format(self.name)

    def expected_value(self):
        return """{0}
|    Name   |   Phone   | Age |
|-----------|-----------|-----|
| Anna      | 123456789 |  32 |
| Alexander | 987654321 |  28 |
|           |           |     |""".format(self.description)


class SimpleLongRowsTest(CallbackTest):
    def __init__(self):
        CallbackTest.__init__(self, "Work with long rows", "Simple")
        self.commands.append(CommandDef("insert", {"characters": self.description}))
        self.commands.append(CommandDef("insert", {"characters": """
|    Name   |   Phone   | Age |             Position             |
|-----------|-----------|-----|----------------------------------|
| Anna      | 123456789 |  32 | Senior Software Engineer         |
| Alexander | 987654321 |  28 | Senior Software Testing Engineer |"""}))
        self.commands.append(CommandDef("table_editor_next_field"))
        for i in range(5):
            self.commands.append(CommandDef("table_editor_previous_field"))
        self.commands.append(CommandDef("table_editor_insert_single_hline"))
        self.commands.append(CommandDef("move", {"by": "words", "forward": False}))
        self.commands.append(CommandDef("table_editor_split_column_down"))
        for i in range(4):
            self.commands.append(CommandDef("table_editor_previous_field"))
        self.commands.append(CommandDef("move", {"by": "words", "forward": False}))
        self.commands.append(CommandDef("table_editor_split_column_down"))
        for i in range(4):
            self.commands.append(CommandDef("table_editor_previous_field"))
        self.commands.append(CommandDef("table_editor_join_lines"))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("table_editor_hline_and_move"))

    @property
    def description(self):
        return """Test: {0}
- Simple Table Syntax
- Split Row
- Join Rows
- Insert hlines
""".format(self.name)

    def expected_value(self):
        return """{0}
|    Name   |   Phone   | Age |             Position             |
|-----------|-----------|-----|----------------------------------|
| Anna      | 123456789 |  32 | Senior Software Engineer         |
|-----------|-----------|-----|----------------------------------|
| Alexander | 987654321 |  28 | Senior Software Testing Engineer |
|-----------|-----------|-----|----------------------------------|
|           |           |     |                                  |""".format(self.description)


class SimpleCustomAlignTest(CallbackTest):

    def __init__(self):
        CallbackTest.__init__(self, "Custom align test", "Simple")
        self.commands.append(CommandDef("insert", {"characters": self.description}))
        self.commands.append(CommandDef("insert", {"characters": """
| column A | column B | column C |
| < | > | # |
|-"""}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "1"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "one"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "'1'"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "2"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "two"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "'2'"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": ">"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "<"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "#"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "1"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "one"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "'1'"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "2"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "two"}))
        self.commands.append(CommandDef("table_editor_next_field"))
        self.commands.append(CommandDef("insert", {"characters": "'2'"}))
        self.commands.append(CommandDef("table_editor_next_field"))

    @property
    def description(self):
        return """Test: {0}
- Simple Table Syntax
- Create table with separator
- Navigate with tab key
- Custom align
""".format(self.name)

    def expected_value(self):
        return """{0}
| column A | column B | column C |
| <<<<<<<< | >>>>>>>> | ######## |
|----------|----------|----------|
| 1        |      one |   '1'    |
| 2        |      two |   '2'    |
| >>>>>>>> | <<<<<<<< | ######## |
|        1 | one      |   '1'    |
|        2 | two      |   '2'    |
|          |          |          |""".format(self.description)


class reStructuredTextKeepSpaceLeftTest(CallbackTest):
    def __init__(self):
        CallbackTest.__init__(self, "Keep Spece left", "reStructuredText")
        self.commands.append(CommandDef("table_editor_enable_for_current_view", {"prop": "table_editor_keep_space_left"}))
        self.commands.append(CommandDef("insert", {"characters": self.description}))
        self.commands.append(CommandDef("insert", {"characters": """
+-------------+
| widget code |
+===============================================+
| code-block::javascript                        |
|                                               |
|    widget.dispatchEvent('onSetTags', object); |
+-----------------------------------------------+"""}))
        self.commands.append(CommandDef("table_editor_align"))


    @property
    def description(self):
        return """Test: {0}
- reStructuredText Syntax
""".format(self.name)

    def expected_value(self):
        return """{0}
+-----------------------------------------------+
|                  widget code                  |
+===============================================+
| code-block::javascript                        |
|                                               |
|    widget.dispatchEvent('onSetTags', object); |
+-----------------------------------------------+""".format(self.description)


class reStructuredTextDisableDetectHeaderTest(CallbackTest):
    def __init__(self):
        CallbackTest.__init__(self, "Disable Detect Header Test", "reStructuredText")
        self.commands.append(CommandDef("table_editor_disable_for_current_view", {"prop": "table_editor_detect_header"}))
        self.commands.append(CommandDef("insert", {"characters": self.description}))
        self.commands.append(CommandDef("insert", {"characters": """
+--------+
| header |
+--------+
| long and shifted data row |
+---------------------------+"""}))
        self.commands.append(CommandDef("table_editor_align"))


    @property
    def description(self):
        return """Test: {0}
- reStructuredText Syntax
- Disable detect header
""".format(self.name)

    def expected_value(self):
        return """{0}
+---------------------------+
| header                    |
+---------------------------+
| long and shifted data row |
+---------------------------+""".format(self.description)


class PandocAlignTest(CallbackTest):
    def __init__(self):
        CallbackTest.__init__(self, "Pandoc Align Test", "Pandoc")
        self.commands.append(CommandDef("insert", {"characters": self.description}))
        self.commands.append(CommandDef("insert", {"characters": """
+-----------+-----------+-----+
|    Name   |   Phone   | Age |
+===========+===========+=====+
| Anna      | 123456789 |  32 |
+-----------+-----------+-----+
| Alexander | 987654321 |  28 |
+-----------+-----------+-----+"""}))
        self.commands.append(CommandDef("table_editor_align"))

    @property
    def description(self):
        return """Test: {0}
- Pandoc Syntax
""".format(self.name)

    def expected_value(self):
        return """{0}
+-----------+-----------+-----+
|    Name   |   Phone   | Age |
+===========+===========+=====+
| Anna      | 123456789 |  32 |
+-----------+-----------+-----+
| Alexander | 987654321 |  28 |
+-----------+-----------+-----+""".format(self.description)


class EmacsOrgModeAlignTest(CallbackTest):
    def __init__(self):
        CallbackTest.__init__(self, "EmacsOrgMode Align Test", "EmacsOrgMode")
        self.commands.append(CommandDef("insert", {"characters": self.description}))
        self.commands.append(CommandDef("insert", {"characters": """
|-----------+-----------+-----|
|    Name   |   Phone   | Age |
|===========+===========+=====|
| Anna      | 123456789 |  32 |
|-----------+-----------+-----|
| Alexander | 987654321 |  28 |
|-----------+-----------+-----|"""}))
        self.commands.append(CommandDef("table_editor_align"))

    @property
    def description(self):
        return """Test: {0}
- EmacsOrgMode Syntax
""".format(self.name)

    def expected_value(self):
        return """{0}
|-----------+-----------+-----|
|    Name   |   Phone   | Age |
|===========+===========+=====|
| Anna      | 123456789 |  32 |
|-----------+-----------+-----|
| Alexander | 987654321 |  28 |
|-----------+-----------+-----|""".format(self.description)


class MarkdownColspanTest(CallbackTest):
    def __init__(self):
        CallbackTest.__init__(self, "MultiMarkdown Colspan Test", "MultiMarkdown")
        self.commands.append(CommandDef("insert", {"characters": self.description}))
        self.commands.append(CommandDef("insert", {"characters": """
|              |           Grouping          ||
| First Header | Second Header | Third Header |
| ------------ | :-----------: | -----------: |
| Content      |         *Long Cell*         ||
| Content      |    **Cell**   |         Cell |
| New section  |      More     |         Data |
| And more     |    And more   |              |
| :---------------------------------------: |||"""}))
        self.commands.append(CommandDef("table_editor_align"))

    @property
    def description(self):
        return """Test: {0}
- MultiMarkdown Syntax
""".format(self.name)

    def expected_value(self):
        return """{0}
|              |           Grouping          ||
| First Header | Second Header | Third Header |
| ------------ | :-----------: | -----------: |
| Content      |         *Long Cell*         ||
| Content      |    **Cell**   |         Cell |
| New section  |      More     |         Data |
| And more     |    And more   |              |
| :---------------------------------------: |||""".format(self.description)


class TextileAlignTest(CallbackTest):
    def __init__(self):
        CallbackTest.__init__(self, "Textile Align Test", "Textile")
        self.commands.append(CommandDef("insert", {"characters": self.description}))
        self.commands.append(CommandDef("insert", {"characters": """
|_.   Name  |_. Age |_. Custom Alignment Demo |
| Anna      | 20 |<. left                  |
| Alexander | 27 |>.                 right |
| Misha     | 42 |=.         center        |
|           |    |                         |"""}))
        self.commands.append(CommandDef("table_editor_align"))

    @property
    def description(self):
        return """Test: {0}
- Textile Syntax
""".format(self.name)

    def expected_value(self):
        return """{0}
|_.   Name  |_. Age |_. Custom Alignment Demo |
| Anna      |    20 |<. left                  |
| Alexander |    27 |>.                 right |
| Misha     |    42 |=.         center        |
|           |       |                         |""".format(self.description)


class TextileColspanTest(CallbackTest):
    def __init__(self):
        CallbackTest.__init__(self, "Textile Colspan Test", "Textile")
        self.commands.append(CommandDef("insert", {"characters": self.description}))
        self.commands.append(CommandDef("insert", {"characters": r"""
|\2. spans two cols   |
| col 1    | col 2    |"""}))
        self.commands.append(CommandDef("table_editor_align"))

    @property
    def description(self):
        return """Test: {0}
- Textile Syntax
""".format(self.name)

    def expected_value(self):
        return r"""{0}
|\2. spans two cols   |
| col 1    | col 2    |""".format(self.description)


class TextileRowspanTest(CallbackTest):
    def __init__(self):
        CallbackTest.__init__(self, "Textile Rowspan Test", "Textile")
        self.commands.append(CommandDef("insert", {"characters": self.description}))
        self.commands.append(CommandDef("insert", {"characters": r"""
|/3. spans 3 rows | a |
| b |
| c |"""}))
        self.commands.append(CommandDef("table_editor_align"))

    @property
    def description(self):
        return """Test: {0}
- Textile Syntax
""".format(self.name)

    def expected_value(self):
        return r"""{0}
|/3. spans 3 rows | a |
| b               |
| c               |""".format(self.description)


class TableEditorTestSuite(sublime_plugin.TextCommand):
    COMMAND_TIMEOUT = 25
    TEST_TIMEOUT = 50

    def __init__(self, view):
        sublime_plugin.TextCommand.__init__(self, view)

    def run(self):
        tests = []
        tests.append(SimpleBasicEditingTest())
        tests.append(SimpleQuickTableCreateTest())
        tests.append(SimpleGridTableTest())
        tests.append(SimpleColumnsTest())
        tests.append(SimpleRowsTest())
        tests.append(SimpleLongRowsTest())
        tests.append(SimpleCustomAlignTest())
        tests.append(reStructuredTextKeepSpaceLeftTest())
        tests.append(reStructuredTextDisableDetectHeaderTest())
        tests.append(PandocAlignTest())
        tests.append(EmacsOrgModeAlignTest())
        tests.append(MarkdownColspanTest())
        tests.append(TextileAlignTest())
        tests.append(TextileColspanTest())
        tests.append(TextileRowspanTest())

        self.run_tests(tests, 0, 0)

    def run_tests(self, tests, test_ind, command_ind):
        if test_ind >= len(tests):
            self.view.run_command("select_all")
            self.view.run_command("cut")
            self.view.run_command("insert", {"characters": """
{0} tests ran sucessfully

Click ctrl+w to close this window""".format(len(tests))})
            return
        test = tests[test_ind]
        if command_ind == 0:
            print("run test", test.name)
        command = test.commands[command_ind]
        self.view.run_command(command.name, command.args)
        if command_ind + 1 < len(test.commands):
            sublime.set_timeout(lambda: self.run_tests(tests, test_ind, command_ind + 1),
                                TableEditorTestSuite.COMMAND_TIMEOUT)
        else:
            text = self.get_buffer_text()
            if text.strip() != tests[test_ind].expected_value().strip():
                self.view.run_command("move_to", {"extend": False, "to": "eof"})
                self.view.run_command("insert", {"characters": """
Test {0} failed:
Expected:
{1}<<<
Actual:
{2}<<<
""".format(tests[test_ind].name, tests[test_ind].expected_value(), text)})
            else:
                self.view.run_command("move_to", {"extend": False, "to": "eof"})
                self.view.run_command("insert", {"characters": """
Test {0} executed sucessfully
""".format(tests[test_ind].name)})

                sublime.set_timeout(lambda: self.run_tests(tests, test_ind + 1, 0),
                                    TableEditorTestSuite.TEST_TIMEOUT)

    def get_buffer_text(self):
        return self.view.substr(sublime.Region(0, self.view.size()))


class TableEditorFilmCommand(sublime_plugin.WindowCommand):

    def run(self):
        view = self.window.new_file()
        view.set_scratch(True)
        view.set_name("Sublime Table Editor Film")
        view.settings().set("table_editor_border_style", "simple")
        view.run_command("table_editor_enable_for_current_view", {"prop": "enable_table_editor"})
        suite = TableEditorTestSuite(view)
        suite.run()

########NEW FILE########
__FILENAME__ = table_re_structured_text_syntax
# re_structured_text_syntax.py - Support reStructuredText table syntax

# Copyright (C) 2012  Free Software Foundation, Inc.

# Author: Valery Kocubinsky
# Package: SublimeTableEditor
# Homepage: https://github.com/vkocubinsky/SublimeTableEditor

# This file is part of SublimeTableEditor.

# SublimeTableEditor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SublimeTableEditor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with SublimeTableEditor.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import print_function
from __future__ import division

try:
    from . import table_base as tbase
    from . import table_border_syntax as tborder
except ValueError:
    import table_base as tbase
    import table_border_syntax as tborder


def create_syntax(table_configuration=None):
    return ReStructuredTextTableSyntax(table_configuration)


class ReStructuredTextTableSyntax(tbase.TableSyntax):

    def __init__(self, table_configuration):
        tbase.TableSyntax.__init__(self, "reStructuredText", table_configuration)

        self.table_parser = tborder.BorderTableParser(self)
        self.table_driver = tborder.BorderTableDriver(self)

        self.hline_out_border = '+'
        self.hline_in_border = '+'

########NEW FILE########
__FILENAME__ = table_simple_syntax
# table_simple_syntax.py - Support Simple table syntax

# Copyright (C) 2012  Free Software Foundation, Inc.

# Author: Valery Kocubinsky
# Package: SublimeTableEditor
# Homepage: https://github.com/vkocubinsky/SublimeTableEditor

# This file is part of SublimeTableEditor.

# SublimeTableEditor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SublimeTableEditor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with SublimeTableEditor.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import print_function
from __future__ import division

import re


try:
    from . import table_base as tbase
    from . import table_border_syntax as tborder
except ValueError:
    import table_base as tbase
    import table_border_syntax as tborder


def create_syntax(table_configuration=None):
    return SimpleTableSyntax(table_configuration)


class SimpleTableSyntax(tbase.TableSyntax):

    def __init__(self, table_configuration):
        tbase.TableSyntax.__init__(self, "Simple", table_configuration)
        self.custom_column_alignment = self.table_configuration.custom_column_alignment

        self.table_parser = SimpleTableParser(self)
        self.table_driver = tborder.BorderTableDriver(self)


        self.hline_out_border = '|'
        self.hline_in_border = '|'
        if self.table_configuration.hline_out_border is not None:
            self.hline_out_border = self.table_configuration.hline_out_border
        if self.table_configuration.hline_in_border is not None:
            self.hline_in_border = self.table_configuration.hline_in_border



class CustomAlignColumn(tbase.Column):
    ALIGN_MAP = {'<': tbase.Column.ALIGN_LEFT,
                 '>': tbase.Column.ALIGN_RIGHT,
                 '#': tbase.Column.ALIGN_CENTER}

    PATTERN = r"^\s*((?:[\<]+)|(?:[\>]+)|(?:[\#]+))\s*$"

    def __init__(self, row, data):
        tbase.Column.__init__(self, row)
        self.align_char = re.search(r"[\<]|[\>]|[\#]", data).group(0)

    def align_follow(self):
        return CustomAlignColumn.ALIGN_MAP[self.align_char]

    def min_len(self):
        # ' < ' or ' > ' or ' # '
        return 3

    def render(self):
        return ' ' + self.align_char * (self.col_len - 2) + ' '

    @staticmethod
    def match_cell(str_col):
        return re.match(CustomAlignColumn.PATTERN, str_col)


class CustomAlignRow(tbase.Row):

    def new_empty_column(self):
        return CustomAlignColumn(self, '#')

    def create_column(self, text):
        return CustomAlignColumn(self, text)

    def is_align(self):
        return True


class SimpleTableParser(tborder.BorderTableParser):

    def _is_custom_align_row(self, str_cols):
        if len(str_cols) == 0:
            return False
        for col in str_cols:
            if not CustomAlignColumn.match_cell(col):
                return False
        return True

    def create_row(self, table, line):
        if (self.syntax.custom_column_alignment and
                self._is_custom_align_row(line.str_cols())):
            row = CustomAlignRow(table)
        else:
            row = tborder.BorderTableParser.create_row(self, table, line)
        return row

########NEW FILE########
__FILENAME__ = table_textile_syntax
# table_textile_syntax.py - Support Textile table syntax

# Copyright (C) 2012  Free Software Foundation, Inc.

# Author: Valery Kocubinsky
# Package: SublimeTableEditor
# Homepage: https://github.com/vkocubinsky/SublimeTableEditor

# This file is part of SublimeTableEditor.

# SublimeTableEditor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SublimeTableEditor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with SublimeTableEditor.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import print_function
from __future__ import division

import math
import re


try:
    from . import table_base as tbase
    from .widechar_support import wlen, wcount
except ValueError:
    import table_base as tbase
    from widechar_support import wlen, wcount

def create_syntax(table_configuration=None):
    return TextileTableSyntax(table_configuration)


class TextileTableSyntax(tbase.TableSyntax):

    def __init__(self, table_configuration):
        tbase.TableSyntax.__init__(self, "Textile", table_configuration)

        self.table_parser = TextileTableParser(self)
        self.table_driver = tbase.TableDriver(self)


class TextileCellColumn(tbase.Column):
    PATTERN = (
        r"\s*("
        # Sequence of one or more table cell terms
        r"(?:"
            # Single character modifiers
            r"[_<>=~^:-]|"
            # Row and col spans
            r"(?:[/\\]\d+)|"
            # Styling and classes
            r"(?:\{.*?\})|(?:\(.*?\))"
        r")+"
        # Terminated by a period
        r"\.)\s+(.*)$")
    COLSPAN_PATTERN = r"\\(\d+)"
    ROWSPAN_PATTERN = r"/(\d+)"

    def __init__(self, row, data):
        tbase.Column.__init__(self, row)
        cell_mo = re.match(TextileCellColumn.PATTERN, data)
        self.attr = cell_mo.group(1)
        self.data = cell_mo.group(2).strip()

        colspan_mo = re.search(TextileCellColumn.COLSPAN_PATTERN, self.attr)
        if colspan_mo:
            self.colspan = int(colspan_mo.group(1))

        rowspan_mo = re.search(TextileCellColumn.ROWSPAN_PATTERN, self.attr)
        if rowspan_mo:
            self.rowspan = int(rowspan_mo.group(1))

    def min_len(self):
        return int(math.ceil(self.total_min_len()/self.colspan))

    def total_min_len(self):
        # '<. data '
        return len(self.attr) + wlen(self.data) + 2

    def render(self):
        # colspan -1 is count of '|'
        total_col_len = self.col_len + (self.colspan - 1) + sum([col.col_len for col in self.pseudo_columns])

        total_align_len = total_col_len - wcount(self.data)
        if '>' in self.attr and not '<>' in self.attr:
            return self.attr + ' ' + self.data.rjust(total_align_len - len(self.attr) - 2, ' ') + ' '
        elif '=' in self.attr or '_' in self.attr:
            return self.attr + ' ' + self.data.center(total_align_len - len(self.attr) - 2, ' ') + ' '
        else:
            return self.attr + ' ' + self.data.ljust(total_align_len - len(self.attr) - 2, ' ') + ' '

    @staticmethod
    def match_cell(str_col):
        return re.match(TextileCellColumn.PATTERN, str_col)


class TextileRow(tbase.Row):

    def new_empty_column(self):
        return tbase.DataColumn(self, '')

    def create_column(self, text):
        if TextileCellColumn.match_cell(text):
            return TextileCellColumn(self, text)
        else:
            return tbase.DataColumn(self, text)

    def is_data(self):
        return not self.is_header_separator()

    def is_header_separator(self):
        for column in self.columns:
            if not isinstance(column, TextileCellColumn):
                return False
            if '_' not in column.attr:
                return False
        return True


class TextileTableParser(tbase.BaseTableParser):

    def create_row(self, table, line):
        return TextileRow(table)

########NEW FILE########
__FILENAME__ = widechar_support
# widechar_support.py - Wide character support for SublimeTableEditor.

# Copyright (C) 2013  Free Software Foundation, Inc.

# Author: Zealic Zeng, Valery Kocubinsky
# Package: SublimeTableEditor
# Homepage: https://github.com/zealic/contrib-SublimeTableEditor

# This file is part of SublimeTableEditor.

# SublimeTableEditor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SublimeTableEditor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with SublimeTableEditor.  If not, see <http://www.gnu.org/licenses/>.

import sys
import locale

breakable_char_ranges = [
    #http://en.wikipedia.org/wiki/Han_unification
    (0x4E00, 0x9FFF),   # CJK Unified Ideographs
    (0x3400, 0x4DBF),   # CJK Unified Ideographs Extension A
    (0xF900, 0xFAFF),   # CJK Compatibility Ideographs
    (0x2E80, 0x2EFF),   # CJK Radicals Supplement
    (0x3000, 0x303F),   # CJK Symbols and Punctuation
    (0x31C0, 0x31EF),   # CJK Strokes
    (0x2FF0, 0x2FFF),   # Ideographic Description Characters
    (0x2F00, 0x2FDF),   # Kangxi Radicals
    (0x3200, 0x32FF),   # Enclosed CJK Letters and Months
    (0x3300, 0x33FF),   # CJK Compatibility
    (0xF900, 0xFAFF),   # CJK Compatibility Ideographs
    (0xFE30, 0xFE4F),   # CJK Compatibility Forms
    # See http://en.wikipedia.org/wiki/Hiragana
    (0x3040, 0x309F),   # Hiragana
    # See http://en.wikipedia.org/wiki/Katakana
    (0x30A0, 0x30FF),   # Katakana
    # See http://en.wikipedia.org/wiki/Hangul
    (0x1100, 0x11FF),   # Hangul Jamo
    (0x3130, 0x318F),   # Hangul Compatibility Jamo
    (0xA960, 0xA97F),   # Hangul Jamo Extended-A
    (0xD7B0, 0xD7FF),   # Hangul Jamo Extended-B
    (0xAC00, 0xD7A3),   # Hangul syllables
    # See http://en.wikipedia.org/wiki/Kanbun
    (0x3190, 0x319F),   # Kanbun
    # See http://en.wikipedia.org/wiki/Halfwidth_and_Fullwidth_Forms
    (0xFF00, 0xFFEF),    # Halfwidth and Fullwidth Forms
]



def _is_widechar(c):
    c = ord(c)
    for i in breakable_char_ranges:
        if isinstance(i, tuple):
            start, end = i
            if c >= start and c <= end:
                return True
        else:
            if i == c:
                return True
    return False


def _norm_text(text):
    if sys.version_info[0] == 2 and isinstance(text, str):
        text = unicode(text, locale.getpreferredencoding())
    return text


def wcount(text):
    text = _norm_text(text)
    count = 0
    for c in text:
        if _is_widechar(c):
            count = count + 1
    return count


def wlen(text):
    text = _norm_text(text)
    return len(text) + wcount(text)

########NEW FILE########
