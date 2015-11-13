__FILENAME__ = build
#!/usr/bin/env python
import os

source_dir = 'src'
output_dir = 'ftplugin'


def build():
    py_src = file(os.path.join(source_dir, 'rst_tables.py')).read()
    vim_src = file(os.path.join(source_dir, 'base.vim')).read()
    combined_src = vim_src.replace('__PYTHON_SOURCE__', py_src)
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    output_path = os.path.join(output_dir, 'rst_tables.vim')
    file(output_path, 'w').write(combined_src)

if __name__ == '__main__':
    build()

########NEW FILE########
__FILENAME__ = rst_tables
import vim
import re
import textwrap
from vim_bridge import bridged


def get_table_bounds():
    row, col = vim.current.window.cursor
    upper = lower = row
    try:
        while vim.current.buffer[upper - 1].strip():
            upper -= 1
    except IndexError:
        pass
    else:
        upper += 1

    try:
        while vim.current.buffer[lower - 1].strip():
            lower += 1
    except IndexError:
        pass
    else:
        lower -= 1

    match = re.match('^(\s*).*$', vim.current.buffer[upper-1])

    return (upper, lower, match.group(1))

def join_rows(rows, sep='\n'):
    """Given a list of rows (a list of lists) this function returns a
    flattened list where each the individual columns of all rows are joined
    together using the line separator.

    """
    output = []
    for row in rows:
        # grow output array, if necessary
        if len(output) <= len(row):
            for i in range(len(row) - len(output)):
                output.extend([[]])

        for i, field in enumerate(row):
            field_text = field.strip()
            if field_text:
                output[i].append(field_text)
    return map(lambda lines: sep.join(lines), output)


def line_is_separator(line):
    return re.match('^[\t +=-]+$', line)


def has_line_seps(raw_lines):
    for line in raw_lines:
        if line_is_separator(line):
            return True
    return False


def partition_raw_lines(raw_lines):
    """Partitions a list of raw input lines so that between each partition, a
    table row separator can be placed.

    """
    if not has_line_seps(raw_lines):
        return map(lambda x: [x], raw_lines)

    curr_part = []
    parts = [curr_part]
    for line in raw_lines:
        if line_is_separator(line):
            curr_part = []
            parts.append(curr_part)
        else:
            curr_part.append(line)

    # remove any empty partitions (typically the first and last ones)
    return filter(lambda x: x != [], parts)


def unify_table(table):
    """Given a list of rows (i.e. a table), this function returns a new table
    in which all rows have an equal amount of columns.  If all full column is
    empty (i.e. all rows have that field empty), the column is removed.

    """
    max_fields = max(map(lambda row: len(row), table))
    empty_cols = [True] * max_fields
    output = []
    for row in table:
        curr_len = len(row)
        if curr_len < max_fields:
            row += [''] * (max_fields - curr_len)
        output.append(row)

        # register empty columns (to be removed at the end)
        for i in range(len(row)):
            if row[i].strip():
                empty_cols[i] = False

    # remove empty columns from all rows
    table = output
    output = []
    for row in table:
        cols = []
        for i in range(len(row)):
            should_remove = empty_cols[i]
            if not should_remove:
                cols.append(row[i])
        output.append(cols)

    return output


def split_table_row(row_string):
    if row_string.find("|") >= 0:
        # first, strip off the outer table drawings
        row_string = re.sub(r'^\s*\||\|\s*$', '', row_string)
        return re.split(r'\s*\|\s*', row_string.strip())
    return re.split(r'\s\s+', row_string.rstrip())


def parse_table(raw_lines):
    row_partition = partition_raw_lines(raw_lines)
    lines = map(lambda row_string: join_rows(map(split_table_row, row_string)),
                row_partition)
    return unify_table(lines)


def table_line(widths, header=False):
    if header:
        linechar = '='
    else:
        linechar = '-'
    sep = '+'
    parts = []
    for width in widths:
        parts.append(linechar * width)
    if parts:
        parts = [''] + parts + ['']
    return sep.join(parts)


def get_field_width(field_text):
    return max(map(lambda s: len(s), field_text.split('\n')))


def split_row_into_lines(row):
    row = map(lambda field: field.split('\n'), row)
    height = max(map(lambda field_lines: len(field_lines), row))
    turn_table = []
    for i in range(height):
        fields = []
        for field_lines in row:
            if i < len(field_lines):
                fields.append(field_lines[i])
            else:
                fields.append('')
        turn_table.append(fields)
    return turn_table


def get_column_widths(table):
    widths = []
    for row in table:
        num_fields = len(row)
        # dynamically grow
        if num_fields >= len(widths):
            widths.extend([0] * (num_fields - len(widths)))
        for i in range(num_fields):
            field_text = row[i]
            field_width = get_field_width(field_text)
            widths[i] = max(widths[i], field_width)
    return widths


def get_column_widths_from_border_spec(slice):
    border = None
    for row in slice:
        if line_is_separator(row):
            border = row.strip()
            break

    if border is None:
        raise RuntimeError('Cannot reflow this table. Top table border not found.')

    left = right = None
    if border[0] == '+':
        left = 1
    if border[-1] == '+':
        right = -1
    return map(lambda drawing: max(0, len(drawing) - 2), border[left:right].split('+'))


def pad_fields(row, widths):
    """Pads fields of the given row, so each field lines up nicely with the
    others.

    """
    widths = map(lambda w: ' %-' + str(w) + 's ', widths)

    # Pad all fields using the calculated widths
    new_row = []
    for i in range(len(row)):
        col = row[i]
        col = widths[i] % col.strip()
        new_row.append(col)
    return new_row


def reflow_row_contents(row, widths):
    new_row = []
    for i, field in enumerate(row):
        wrapped_lines = textwrap.wrap(field.replace('\n', ' '), widths[i])
        new_row.append("\n".join(wrapped_lines))
    return new_row


def draw_table(indent, table, manual_widths=None):
    if table == []:
        return []

    if manual_widths is None:
        col_widths = get_column_widths(table)
    else:
        col_widths = manual_widths

    # Reserve room for the spaces
    sep_col_widths = map(lambda x: x + 2, col_widths)
    header_line = table_line(sep_col_widths, header=True)
    normal_line = table_line(sep_col_widths, header=False)

    output = [indent+normal_line]
    first = True
    for row in table:

        if manual_widths:
            row = reflow_row_contents(row, manual_widths)

        row_lines = split_row_into_lines(row)

        # draw the lines (num_lines) for this row
        for row_line in row_lines:
            row_line = pad_fields(row_line, col_widths)
            output.append(indent+"|".join([''] + row_line + ['']))

        # then, draw the separator
        if first:
            output.append(indent+header_line)
            first = False
        else:
            output.append(indent+normal_line)

    return output


@bridged
def reformat_table():
    upper, lower, indent = get_table_bounds()
    slice = vim.current.buffer[upper - 1:lower]
    table = parse_table(slice)
    slice = draw_table(indent, table)
    vim.current.buffer[upper - 1:lower] = slice


@bridged
def reflow_table():
    upper, lower, indent = get_table_bounds()
    slice = vim.current.buffer[upper - 1:lower]
    widths = get_column_widths_from_border_spec(slice)
    table = parse_table(slice)
    slice = draw_table(indent, table, widths)
    vim.current.buffer[upper - 1:lower] = slice

########NEW FILE########
__FILENAME__ = vim
from mock import Mock

eval = Mock()
command = Mock()

########NEW FILE########
__FILENAME__ = test_rst_tables
# Mock out the vim library
import sys
sys.path = ['tests/mocks'] + sys.path
import vim
import mock

vimvar = {}


def fake_eval(x):
    global vimvar
    return vimvar[x]

vim.eval = fake_eval
vim.current = mock.Mock()
vimvar['foo'] = 'bar'

# Begin normal module loading
import os
import unittest

# Load test subjects
from rst_tables import get_table_bounds, reformat_table, parse_table, \
             reflow_table, draw_table, table_line, get_column_widths, \
             get_column_widths_from_border_spec, pad_fields, unify_table, \
             join_rows, partition_raw_lines, split_row_into_lines, \
             reflow_row_contents

class TestRSTTableFormatter(unittest.TestCase):

    def setUp(self):
        # Default vim cursor for all tests is at line 4
        vim.current = mock.Mock()
        self.set_vim_cursor(4, 0)

    def tearDown(self):
        del vim.current

    def set_vim_cursor(self, row, col):
        vim.current.window.cursor = (row, col)

    def read_fixture(self, name):
        return open(os.path.join('tests/fixtures/', name + '.txt'),
                    'r').read().split('\n')

    def load_fixture_in_vim(self, name):
        vim.current.buffer = self.read_fixture(name)

    def testGetBounds(self):
        self.load_fixture_in_vim('default')
        self.assertEquals((3, 6), get_table_bounds())

    def testGetBoundsOnBeginOfFile(self):
        self.load_fixture_in_vim('default')
        vim.current.window.cursor = (1, 0)
        self.assertEquals((1, 1), get_table_bounds())

    def testGetBoundsOnEndOfFile(self):
        self.load_fixture_in_vim('default')
        vim.current.window.cursor = (8, 0)
        self.assertEquals((8, 9), get_table_bounds())

    def testJoinSimpleRows(self):
        input_rows = [['x', 'y', 'z'], ['foo', 'bar']]
        expected = ['x\nfoo', 'y\nbar', 'z']
        self.assertEquals(expected, join_rows(input_rows))

        input_rows.append(['apple', '', 'pear'])
        expected = ['x foo apple', 'y bar', 'z pear']
        self.assertEquals(expected, join_rows(input_rows, sep=' '))

    def testPartitionRawLines(self):
        self.assertEquals([], partition_raw_lines([]))
        self.assertEquals([['']], partition_raw_lines(['']))
        self.assertEquals(
                [['foo'], ['bar']],
                partition_raw_lines(['foo', 'bar']))
        self.assertEquals(
                [['foo'], ['bar']],
                partition_raw_lines(['foo', '+----+', 'bar']))
        self.assertEquals(
                [['foo', 'bar'], ['baz']],
                partition_raw_lines(['+-----+', 'foo', 'bar', '----', 'baz']))

    def testParseSimpleTable(self):
        self.assertEquals([['x y z']], parse_table(['x y z']))
        self.assertEquals([['x', 'y z']], parse_table(['x  y z']))
        self.assertEquals([['x', 'y', 'z']], parse_table(['x  y          z']))

    def testParseTable(self):
        self.load_fixture_in_vim('default')
        expected = [
                ['Column 1', 'Column 2'],
                ['Foo', 'Put two (or more) spaces as a field separator.'],
                ['Bar', 'Even very very long lines like these are fine, as long as you do not put in line endings here.'],
                ['Qux', 'This is the last line.'],
                ]
        self.assertEquals(expected, parse_table(vim.current.buffer[2:6]))

    def testParseTableUnifiesColumns(self):
        input = ['x  y', 'a  b    c', 'only one']
        expected = [['x', 'y', ''], ['a', 'b', 'c'], ['only one', '', '']]
        self.assertEquals(expected, parse_table(input))

    def testUnifyTables(self):
        input = [[' x ', '  y'], ['xxx', ' yyyy ', 'zz']]
        expected = [[' x ', '  y', ''], ['xxx', ' yyyy ', 'zz']]
        self.assertEquals(expected, unify_table(input))

    def testUnifyTablesRemovesEmptyColumns(self):
        input = [['x', '', 'y'], ['xxx', '', 'yyyy', 'zz', '         ']]
        expected = [['x', 'y', ''], ['xxx', 'yyyy', 'zz']]
        self.assertEquals(expected, unify_table(input))

    def testParseDealsWithSpacesAtLineEnd(self):
        input = ['x  y     ', 'a  b ', 'only one']
        expected = [['x', 'y'], ['a', 'b'], ['only one', '']]
        self.assertEquals(expected, parse_table(input))

    def testParseValidTable(self):
        input = ['+-----+----+',
                 '| Foo | Mu |',
                 '+=====+====+',
                 '| x   | y  |',
                 '+-----+----+']
        expect = [['Foo', 'Mu'], ['x', 'y']]
        self.assertEquals(expect, parse_table(input))

    def testParseCorruptedTable(self):
        input = ['+---+---------+',
                 '| Foo | Mu                   |',
                 '+=====+====+',
                 '| x   | This became somewhat larger  |',
                 'blah   | A new line| ',
                 '+-----+----+']
        expect = [['Foo', 'Mu'],
                  ['x\nblah', 'This became somewhat larger\nA new line']]
        self.assertEquals(expect, parse_table(input))

        input = ['+---+---------+',
                 '| Foo | Mu                   |',
                 '+=====+====+',
                 '| x   | This became somewhat larger  |',
                 'blah   | A new line|| ',
                 '+-----+----+']
        expect = [['Foo', 'Mu'],
                  ['x\nblah', 'This became somewhat larger\nA new line']]
        self.assertEquals(expect, parse_table(input))

    def testParseMultiLineFields(self):
        input = """\
+-----+---------------------+
| Foo | Bar                 |
+=====+=====================+
| x   | This is a long line |
|     | that is spread out  |
|     | over multiple lines |
+-----+---------------------+""".split('\n')
        expect = [['Foo', 'Bar'],
                  ['x', 'This is a long line\nthat is spread out\nover multiple lines']]
        self.assertEquals(expect, parse_table(input))

    def testSplitRowIntoLines(self):
        input = ['Foo', 'Bar']
        expect = [['Foo', 'Bar']]
        self.assertEquals(expect, split_row_into_lines(input))
        input = ['One\nTwo\nThree', 'Only one']
        expect = [['One', 'Only one'], ['Two', ''], ['Three', '']]
        self.assertEquals(expect, split_row_into_lines(input))
        input = ['One\n\n\nThree', 'Foo\nBar']
        expect = [['One', 'Foo'], ['', 'Bar'], ['', ''], ['Three', '']]
        self.assertEquals(expect, split_row_into_lines(input))

    def testDrawMultiLineFields(self):
        input = [['Foo', 'Bar'],
                  ['x', 'This is a long line\nthat is spread out\nover multiple lines']]
        expect = """\
+-----+---------------------+
| Foo | Bar                 |
+=====+=====================+
| x   | This is a long line |
|     | that is spread out  |
|     | over multiple lines |
+-----+---------------------+""".split('\n')
        self.assertEquals(expect, draw_table(input))

    def testTableLine(self):
        self.assertEquals('', table_line([], True))
        self.assertEquals('++', table_line([0], True))
        self.assertEquals('+++', table_line([0,0], True))
        self.assertEquals('++-+', table_line([0,1]))
        self.assertEquals('+===+', table_line([3], True))
        self.assertEquals('+===+====+', table_line([3,4], True))
        self.assertEquals('+------------------+---+--------------------+',
                table_line([18,3,20]))

    def testGetColumnWidths(self):
        self.assertEquals([], get_column_widths([[]]))
        self.assertEquals([0], get_column_widths([['']]))
        self.assertEquals([1,2,3], get_column_widths([['x','yy','zzz']]))
        self.assertEquals([3,3,3],
                get_column_widths(
                    [
                        ['x','y','zzz'],
                        ['xxx','yy','z'],
                        ['xx','yyy','zz'],
                    ]))

    def testGetColumnWidthsForMultiLineFields(self):
        self.assertEquals([3,6],
                get_column_widths([['Foo\nBar\nQux',
                                    'This\nis\nreally\nneat!']]))

    def testGetColumnWidthsFromBorderSpec(self):
        input = ['+----+-----+--+-------+',
                 '| xx | xxx |  | xxxxx |',
                 '+====+=====+==+=======+']
        self.assertEquals([2, 3, 0, 5],
            get_column_widths_from_border_spec(input))

    def testPadFields(self):
        table = [['Name', 'Type', 'Description'],
                 ['Lollypop', 'Candy', 'Yummy'],
                 ['Crisps', 'Snacks', 'Even more yummy, I tell you!']]
        expected_padding = [
                 [' Name     ', ' Type   ', ' Description                  '],
                 [' Lollypop ', ' Candy  ', ' Yummy                        '],
                 [' Crisps   ', ' Snacks ', ' Even more yummy, I tell you! ']]
        widths = get_column_widths(table)
        for input, expect in zip(table, expected_padding):
            self.assertEquals(expect, pad_fields(input, widths))

    def testReflowRowContentsWithEnoughWidth(self):
        input = ['Foo\nbar', 'This line\nis spread\nout over\nfour lines.']
        expect = ['Foo bar', 'This line is spread out over four lines.']
        self.assertEquals(expect, reflow_row_contents(input, [99,99]))

    def testReflowRowContentsWithWrapping(self):
        input = ['Foo\nbar', 'This line\nis spread\nout over\nfour lines.']
        expect = ['Foo bar', 'This line is spread\nout over four lines.']
        self.assertEquals(expect, reflow_row_contents(input, [10,20]))

        input = ['Foo\nbar', 'This line\nis spread\nout over\nfour lines.']
        expect = ['Foo bar', 'This\nline\nis\nspread\nout\nover\nfour\nlines.']
        self.assertEquals(expect, reflow_row_contents(input, [10,6]))

    def testReflowRowContentsWithoutRoom(self):
        #self.assertEquals(expect, reflow_row_contents(input))
        pass

    def testDrawTable(self):
        self.assertEquals([], draw_table([]))
        self.assertEquals(['+--+', '|  |', '+==+'], draw_table([['']]))
        self.assertEquals(['+-----+', '| Foo |', '+=====+'],
                draw_table([['Foo']]))
        self.assertEquals(
                ['+-----+----+',
                 '| Foo | Mu |',
                 '+=====+====+',
                 '| x   | y  |',
                 '+-----+----+'],
                draw_table([['Foo', 'Mu'], ['x', 'y']]))


    def testCreateTable(self):
        self.load_fixture_in_vim('default')
        expect = """\
This is paragraph text *before* the table.

+----------+------------------------------------------------------------------------------------------------+
| Column 1 | Column 2                                                                                       |
+==========+================================================================================================+
| Foo      | Put two (or more) spaces as a field separator.                                                 |
+----------+------------------------------------------------------------------------------------------------+
| Bar      | Even very very long lines like these are fine, as long as you do not put in line endings here. |
+----------+------------------------------------------------------------------------------------------------+
| Qux      | This is the last line.                                                                         |
+----------+------------------------------------------------------------------------------------------------+

This is paragraph text *after* the table, with
a line ending.
""".split('\n')
        reformat_table()
        self.assertEquals(expect, vim.current.buffer)

    def testCreateComplexTable(self):
        raw_lines = self.read_fixture('multiline-cells')
        # strip off the last (empty) line from raw_lines (since that line does
        # not belong to the table
        del raw_lines[-1]
        expect = """\
+----------------+---------------------------------------------------------------+
| Feature        | Description                                                   |
+================+===============================================================+
| Ease of use    | Drop dead simple!                                             |
+----------------+---------------------------------------------------------------+
| Foo            | Bar, qux, mux                                                 |
+----------------+---------------------------------------------------------------+
| Predictability | Lorem ipsum dolor sit amet, consectetur adipiscing elit.      |
+----------------+---------------------------------------------------------------+
|                | Nullam congue dapibus aliquet. Integer ut rhoncus leo. In hac |
+----------------+---------------------------------------------------------------+
|                | habitasse platea dictumst. Phasellus pretium iaculis.         |
+----------------+---------------------------------------------------------------+
""".rstrip().split('\n')
        self.assertEquals(expect, draw_table(parse_table(raw_lines)))

    def testReflowTable(self):
        self.load_fixture_in_vim('reflow')
        expect = """\
This is paragraph text *before* the table.

+----------+--------------------------+
| Column 1 | Column 2                 |
+==========+==========================+
| Foo      | Put two (or more) spaces |
|          | as a field separator.    |
+----------+--------------------------+
| Bar      | Even very very long      |
|          | lines like these are     |
|          | fine, as long as you do  |
|          | not put in line endings  |
|          | here.                    |
+----------+--------------------------+
| Qux      | This is the last line.   |
+----------+--------------------------+

This is paragraph text *after* the table, with
a line ending.
""".split('\n')
        reflow_table()
        self.assertEquals(expect, vim.current.buffer)


########NEW FILE########
