__FILENAME__ = formatting
"""
Utilities to format values into more meaningful strings.
Inspired by James Bennett's template_utils and Django's
template filters.
"""
import re
import statestyle


def _saferound(value, decimal_places):
    """
    Rounds a float value off to the desired precision
    """
    try:
        f = float(value)
    except ValueError:
        return ''
    format = '%%.%df' % decimal_places
    return format % f


def ap_state(value, failure_string=None):
    """
    Converts a state's name, postal abbreviation or FIPS to A.P. style.
    
    Example usage:
    
        >> ap_state("California")
        'Calif.'
    
    """
    try:
        return statestyle.get(value).ap
    except:
        if failure_string:
            return failure_string
        else:
            return value


def capfirst(value, failure_string='N/A'):
    """
    Capitalizes the first character of the value.
    
    If the submitted value isn't a string, returns the `failure_string` keyword
    argument.
    
    Cribbs from django's default filter set
    """
    try:
        value = value.lower()
        return value[0].upper() + value[1:]
    except:
        return failure_string


def dollars(value):
    return u'$%s'% intcomma(value)


def dollar_signs(value, failure_string='N/A'):
    """
    Converts an integer into the corresponding number of dollar sign symbols.
    
    If the submitted value isn't a string, returns the `failure_string` keyword
    argument.
    
    Meant to emulate the illustration of price range on Yelp.
    """
    try:
        count = int(value)
    except ValueError:
        return failure_string
    string = ''
    for i in range(0, count):
        string += '$'
    return string


def image(value, width='', height=''):
    """
    Accepts a URL and returns an HTML image tag ready to be displayed.
    
    Optionally, you can set the height and width with keyword arguments.
    """
    style = ""
    if width:
        style += "width:%s" % width
    if height:
        style += "height:%s" % height
    data_dict = dict(src=value, style=style)
    return '<img src="%(src)s" style="%(style)s">' % data_dict


def link(title, url):
    return u'<a href="%(url)s" title="%(title)s">%(title)s</a>' % {
        'url': url,
        'title': title
    }


def intcomma(value):
    """
    Borrowed from django.contrib.humanize
    
    Converts an integer to a string containing commas every three digits.
    For example, 3000 becomes '3,000' and 45000 becomes '45,000'.
    """
    orig = str(value)
    new = re.sub("^(-?\d+)(\d{3})", '\g<1>,\g<2>', orig)
    if orig == new:
        return new
    else:
        return intcomma(new)


def percentage(value, decimal_places=1, multiply=True, failure_string='N/A'):
    """
    Converts a floating point value into a percentage value.
    
    Number of decimal places set by the `decimal_places` kwarg. Default is one.
    
    By default the number is multiplied by 100. You can prevent it from doing
    that by setting the `multiply` keyword argument to False.
    
    If the submitted value isn't a string, returns the `failure_string` keyword
    argument.
    """
    try:
        value = float(value)
    except ValueError:
        return failure_string
    if multiply:
        value = value * 100
    return _saferound(value, decimal_places) + '%'


def percent_change(value, decimal_places=1, multiply=True, failure_string='N/A'):
    """
    Converts a floating point value into a percentage change value.
    
    Number of decimal places set by the `precision` kwarg. Default is one.
    
    Non-floats are assumed to be zero division errors and are presented as
    'N/A' in the output.
    
    By default the number is multiplied by 100. You can prevent it from doing
    that by setting the `multiply` keyword argument to False.
    """
    try:
        f = float(value)
        if multiply:
            f = f * 100
    except ValueError:
       return  failure_string
    s = _saferound(f, decimal_places)
    if f > 0:
        return '+' + s + '%'
    else:
        return s + '%'


def ratio(value, decimal_places=0, failure_string='N/A'):
    """
    Converts a floating point value a X:1 ratio.
    
    Number of decimal places set by the `precision` kwarg. Default is one.
    """
    try:
        f = float(value)
    except ValueError:
        return failure_string
    return _saferound(f, decimal_places) + ':1'


def stateface(value):
    """
    Converts a state's name, postal abbreviation or FIPS to ProPublica's stateface
    font code.
    
    Example usage:
    
        >> stateface("California")
        'E'
    
    Documentation: http://propublica.github.com/stateface/
    """
    try:
        return statestyle.get(value).stateface
    except:
        return value


def state_postal(value):
    """
    Converts a state's name, or FIPS to its postal abbreviation
    
    Example usage:
    
        >> ap_state("California")
        'Calif.'
    
    """
    try:
        return statestyle.get(value).postal
    except:
        return value


def title(value, failure_string='N/A'):
    """
    Converts a string into titlecase.
    
    Lifted from Django.
    """
    try:
        value = value.lower()
        t = re.sub("([a-z])'([A-Z])", lambda m: m.group(0).lower(), value.title())
        result = re.sub("\d([A-Z])", lambda m: m.group(0).lower(), t)
        if not result:
            return failure_string
        return result
    except:
        return failure_string


DEFAULT_FORMATTERS = {
    'ap_state': ap_state,
    'capfirst': capfirst,
    'dollars': dollars,
    'dollar_signs': dollar_signs,
    'intcomma': intcomma,
    'image': image,
    'link': link,
    'percentage': percentage,
    'percent_change': percent_change,
    'ratio': ratio,
    'stateface': stateface,
    'state_postal': state_postal,
    'title': title,
}


class Formatter(object):
    """
    A formatter is a function (or any callable, really)
    that takes a value and returns a nicer-looking value,
    most likely a sting.
    
    Formatter stores and calls those functions, keeping
    the namespace uncluttered.
    
    Formatting functions should take a value as the first
    argument--usually the value of the Datum on which the
    function is called--followed by any number of positional
    arguments.
    
    In the context of TableFu, those arguments may refer to
    other columns in the same row.
    
    >>> formatter = Formatter()
    >>> formatter(1200, 'intcomma')
    '1,200'
    >>> formatter(1200, 'dollars')
    '$1,200'
    """
    
    def __init__(self):
        self._filters = {}
        for name, func in DEFAULT_FORMATTERS.items():
            self.register(name, func)
    
    def __call__(self, value, func, *args, **kwargs):
        if not callable(func):
            func = self._filters[func]
        return func(value, *args, **kwargs)
    
    def register(self, name=None, func=None):
        if not func and not name:
            return

        if callable(name) and not func:
            func = name
            name = func.__name__
        elif func and not name:
            name = func.__name__
        
        self._filters[name] = func
    
    def unregister(self, name=None, func=None):
        if not func and not name:
            return
        if not name:
            name = func.__name__
        
        if name not in self._filters:
            return
        
        del self._filters[name]
        

# Unless you need to subclass or keep formatting functions
# isolated, you can just import this instance.
format = Formatter()

########NEW FILE########
__FILENAME__ = test
#! /usr/bin/env python
import csv
import unittest
import urllib2
from table_fu import TableFu
from table_fu.formatting import Formatter


class TableTest(unittest.TestCase):
    
    def setUp(self):
        self.csv_file = open('tests/test.csv')
        self.table = [['Author', 'Best Book', 'Number of Pages', 'Style'],
            ['Samuel Beckett', 'Malone Muert', '120', 'Modernism'],
            ['James Joyce', 'Ulysses', '644', 'Modernism'],
            ['Nicholson Baker', 'Mezannine', '150', 'Minimalism'],
            ['Vladimir Sorokin', 'The Queue', '263', 'Satire'],
            ['Ayn Rand', 'Atlas Shrugged', '1088', 'Science fiction']]

    def tearDown(self):
        self.csv_file.close()


class BigTableTest(TableTest):

    def test_table(self):
        "Create a table from an open CSV file"
        t = TableFu(self.csv_file)
        self.table.pop(0)
        self.assertEqual(t.table, self.table)

    def test_table_from_list(self):
        "Create a table from a two-dimensional list"
        t = TableFu(self.table)
        self.table.pop(0)
        self.assertEqual(t.table, self.table)

    def test_table_two_ways(self):
        "Two ways to create the same table"
        t1 = TableFu(self.csv_file)
        t2 = TableFu(self.table)
        self.assertEqual(t1.table, t2.table)


class ColumnTest(TableTest):

    def test_get_columns(self):
        "Get a table's (default) columns"
        t = TableFu(self.csv_file)
        self.assertEqual(t.columns, self.table[0])

    def test_set_columns(self):
        "Set new columns for a table"
        t = TableFu(self.csv_file)
        columns = ['Style', 'Author']
        t.columns = columns
        self.assertEqual(t.columns, columns)


class HeaderTest(TableTest):
    
    def test_get_headers(self):
        "Get the table's headers"
        t = TableFu(self.csv_file)
        self.assertEqual(t.headers, self.table[0])


class RowTest(TableTest):
    
    def test_count_rows(self):
        "Count rows, not including headings"
        t = TableFu(self.csv_file)
        self.table.pop(0)
        self.assertEqual(len(list(t.rows)), len(self.table))
        self.assertEqual(len(t), len(self.table))

    def test_get_row(self):
        "Get one row by slicing the table"
        t = TableFu(self.csv_file)
        self.assertEqual(t[1], list(t.rows)[1])

    def test_check_row(self):
        "Check that row numbers are assigned correctly"
        t = TableFu(self.csv_file)
        self.table.pop(0)
        for i, row in enumerate(self.table):
            self.assertEqual(
                t[i].cells,
                self.table[i]
            )


class RowColumnTest(TableTest):
     
    def test_limit_columns(self):
        "Column definitions are passed to rows"
        t = TableFu(self.csv_file)
        t.columns = ['Author', 'Style']
        self.assertEqual(
            str(t[0]),
            'Samuel Beckett, Modernism'
            )


class DatumTest(TableTest):
    
    def test_get_datum(self):
        "Get one cell at a time"
        t = TableFu(self.csv_file)
        for row in t.rows:
            for c in self.table[0]:
                self.assertEqual(c, row[c].column_name)

    def test_set_datum(self):
        "Set a new value for one cell"
        t = TableFu(self.csv_file)
        modernism = t[0]
        modernism['Author'] = "Someone new"
        self.assertEqual(str(modernism['Author']), "Someone new")

    def test_datum_values(self):
        "Ensure every cell has the right value"
        t = TableFu(self.csv_file)
        columns = self.table.pop(0)
        for i, row in enumerate(t.rows):
            for index, column in enumerate(columns):
                self.assertEqual(
                    self.table[i][index],
                    str(row[column])
                )
    
    def test_update_values(self):
        "Update multiple cell values for a given row"
        t = TableFu(self.csv_file)
        modernism = t[0]
        kerouac = {
            'Author': 'Jack Kerouac',
            'Best Book': 'On the Road',
            'Number of Pages': '320',
            'Style': 'Beat'
        }
        modernism.update(kerouac)
        self.assertEqual(
            set(kerouac.values()),
            set(modernism.cells)
        )
    
    def test_datum_equality(self):
        "Data are tested on their values"
        t = TableFu(self.csv_file)
        self.assertEqual(t[0]['Author'], 'Samuel Beckett')
    
    def test_keys(self):
        "Get keys for a row, which should match the table's columns"
        t = TableFu(self.csv_file)
        modernism = t[0]
        self.assertEqual(modernism.keys(), t.columns)
    
    def test_values(self):
        "Get values for a row"
        t = TableFu(self.csv_file)
        modernism = t[0]
        values = [d.value for d in modernism.data]
        self.assertEqual(modernism.values(), values)
    
    def test_items(self):
        "Get key-value pairs for a row"
        t = TableFu(self.csv_file)
        modernism = t[0]
        self.assertEqual(
            modernism.items(),
            zip(modernism.keys(), modernism.values())
        )
    
    def test_list_row(self):
        "Convert a row back to a list"
        t = TableFu(self.csv_file)
        modernism = t[0]
        self.assertEqual(
            list(modernism),
            modernism.values()
        )


class ErrorTest(TableTest):
    
    def test_bad_key(self):
        "Non-existent columns raise a KeyError"
        t = TableFu(self.csv_file)
        for row in t.rows:
            self.assertRaises(
                KeyError,
                row.__getitem__,
                'not-a-key'
            )
    
    def test_bad_total(self):
        "Only number-like fields can be totaled"
        t = TableFu(self.csv_file)
        self.assertRaises(ValueError, t.total, 'Author')


class SortTest(TableTest):
    
    def test_sort(self):
        "Sort a table in place"
        t = TableFu(self.csv_file)
        self.table.pop(0)
        self.table.sort(key=lambda row: row[0])
        t.sort('Author')
        self.assertEqual(
            t[0].cells,
            self.table[0]
        )

class ValuesTest(TableTest):

    def test_values(self):
        "Return one column's values for all rows"
        t = TableFu(self.csv_file)
        self.table.pop(0)
        authors = [row[0] for row in self.table]
        self.assertEqual(authors, t.values('Author'))
    
    def test_unique_values(self):
        "Adding unique=True returns a set"
        t = TableFu(self.table)
        self.table.pop(0)
        styles = set([row[-1] for row in self.table])
        self.assertEqual(t.values('Style', unique=True), styles)
    
    def test_totals(self):
        "Total values for a table across rows"
        t = TableFu(self.csv_file)
        self.table.pop(0)
        pages = sum([float(row[2]) for row in self.table])
        self.assertEqual(pages, t.total('Number of Pages'))


class FacetTest(TableTest):

    def test_facet(self):
        "Facet tables based on shared column values"
        t = TableFu(self.csv_file)
        tables = t.facet_by('Style')
        style_row = self.table[4]
        self.assertEqual(
            style_row,
            tables[2][0].cells
        )

class FilterTest(TableTest):
    
    def test_count(self):
        "Count is like len()"
        t = TableFu(self.csv_file)
        self.assertEqual(len(t), t.count())
    
    def test_filter(self):
        "Filtering returns a new TableFu instance"
        t = TableFu(self.csv_file)
        f = t.filter(Author='Samuel Beckett')
        self.assertEqual(type(t), type(f))
        self.assertEqual(t.columns, f.columns)
    
    def test_simple_filter(self):
        "Filter by keyword args"
        t = TableFu(self.csv_file)
        f = t.filter(Author='Samuel Beckett')
        self.assertEqual(f[0].cells, self.table[1])
    
    def test_multi_filter(self):
        "Filter by multiple keywords"
        t = TableFu(self.csv_file)
        f = t.filter(Style='Modernism', Author='Samuel Beckett')
        self.assertEqual(f[0].cells, self.table[1])
    
    def test_big_filter(self):
        arra = open('tests/arra.csv')
        t = TableFu(arra)
        f = t.filter(State='ALABAMA', County='COLBERT')
        self.assertEqual(f.count(), 5)


class OptionsTest(TableTest):
    
    def test_sort_option_str(self):
        "Sort the table by a string field, Author"
        t = TableFu(self.csv_file, sorted_by={"Author": {'reverse': True}})
        self.table.pop(0)
        self.table.sort(key=lambda row: row[0], reverse=True)
        self.assertEqual(t[0].cells, self.table[0])
    
    def test_sort_option_int(self):
        "Sorting the table by an int field, Number of Pages"
        t = TableFu(self.csv_file)
        pages = t.values('Number of Pages')
        pages = sorted(pages, reverse=True)
        t.sort('Number of Pages', reverse=True)
        self.assertEqual(t.values('Number of Pages'), pages)


class DatumFormatTest(TableTest):
    
    def setUp(self):
        self.csv_file = open('tests/sites.csv')
    
    def test_cell_format(self):
        "Format a cell"
        t = TableFu(self.csv_file)
        t.formatting = {'Name': {
            'filter': 'link',
            'args': ['URL']
            }
        }
        
        self.assertEqual(
            str(t[0]['Name']),
            '<a href="http://www.chrisamico.com" title="ChrisAmico.com">ChrisAmico.com</a>'
        )

class HTMLTest(TableTest):
    
    def test_datum_td(self):
        "Output a cell as a <td> element"
        t = TableFu(self.csv_file)
        beckett = t[0]['Author']
        self.assertEqual(
            beckett.as_td(),
            '<td style="" class="datum">Samuel Beckett</td>'
        )
    
    def test_row_tr(self):
        "Output a row as a <tr> element"
        t = TableFu(self.csv_file)
        row = t[0]
        self.assertEqual(
            row.as_tr(),
            '<tr id="row0" class="row even"><td style="" class="datum">Samuel Beckett</td><td style="" class="datum">Malone Muert</td><td style="" class="datum">120</td><td style="" class="datum">Modernism</td></tr>'
        )
    
    def test_header_th(self):
        t = TableFu(self.csv_file)
        hed = t.headers[0]
        self.assertEqual(hed.as_th(), '<th style="" class="header">Author</th>')


class StyleTest(TableTest):
    
    def test_datum_style(self):
        t = TableFu(self.csv_file, style={'Author': 'text-align:left;'})
        beckett = t[0]['Author']
        self.assertEqual(beckett.style, 'text-align:left;')
    
    def test_datum_td_style(self):
        t = TableFu(self.csv_file, style={'Author': 'text-align:left;'})
        beckett = t[0]['Author']
        self.assertEqual(
            beckett.as_td(),
            '<td style="text-align:left;" class="datum">Samuel Beckett</td>'
        )
    
    def test_header_style(self):
        t = TableFu(self.csv_file, style={'Author': 'text-align:left;'})
        hed = t.headers[0]
        self.assertEqual(hed.style, 'text-align:left;')
    
    def test_header_th_style(self):
        t = TableFu(self.csv_file, style={'Author': 'text-align:left;'})
        hed = t.headers[0]
        self.assertEqual(
            hed.as_th(),
            '<th style="text-align:left;" class="header">Author</th>'
        )


class OutputTest(TableTest):
    
    def setUp(self):
        self.csv_file = open('tests/arra.csv')
    
    def tearDown(self):
        self.csv_file.close()    
    
    def test_csv(self):
        t = TableFu(self.csv_file)
        self.csv_file.seek(0)
        for test, control in zip(t.csv(), self.csv_file.readline()):
            self.assertEqual(test.strip(), control.strip()) # controlling for newlines
    
    def test_json(self):
        try:
            import json
        except ImportError:
            try:
                import simplejson as json
            except ImportError:
                return
        
        t = TableFu(self.csv_file)
        self.csv_file.seek(0)
        reader = csv.DictReader(self.csv_file)
        jsoned = json.dumps([row for row in reader])
        self.assertEqual(t.json(), jsoned)
    
    def test_python(self):
        t = TableFu(self.csv_file)
        self.csv_file.seek(0)
        reader = csv.DictReader(self.csv_file)
        jsoned = [row for row in reader]
        self.assertEqual(list(t.dict()), jsoned)


class ManipulationTest(TableTest):
    
    def test_transpose(self):
        t = TableFu(self.table)
        result = [
            ['Author', 'Samuel Beckett', 'James Joyce', 'Nicholson Baker', 'Vladimir Sorokin', 'Ayn Rand'],
            ['Best Book', 'Malone Muert', 'Ulysses', 'Mezannine', 'The Queue', 'Atlas Shrugged'],
            ['Number of Pages', '120', '644', '150', '263', '1088'],
            ['Style', 'Modernism', 'Modernism', 'Minimalism', 'Satire', 'Science fiction']
        ]
        
        transposed = t.transpose()
        self.assertEqual(transposed.table, result[1:])
        self.assertEqual(transposed.columns, [
            'Author',
            'Samuel Beckett',
            'James Joyce',
            'Nicholson Baker',
            'Vladimir Sorokin',
            'Ayn Rand',
        ])
    
    def test_row_map(self):
        """
        Test map a function to rows, or a subset of fields
        """
        t = TableFu(self.table)
        result = [s.lower() for s in t.values('Style')]
        self.assertEqual(result, t.map(lambda row: row['Style'].value.lower()))
    
    def test_map_values(self):
        """
        Test mapping a function to specific column values
        """
        t = TableFu(self.table)
        result = [s.lower() for s in t.values('Style')]
        self.assertEqual(result, t.map(str.lower, 'Style'))
    
    def test_map_many_values(self):
        """
        Test mapping a function to multiple columns
        """
        t = TableFu(self.table)
        result = [
            [s.lower() for s in t.values(value)]
            for value in ['Best Book', 'Style']
        ]
        self.assertEqual(result, t.map(str.lower, 'Best Book', 'Style'))


class FormatTest(unittest.TestCase):

    def setUp(self):
        self.format = Formatter()


class RegisterTest(FormatTest):

    def test_register(self):
        "Register a new format function"

        def test(value, *args):
            args = list(args)
            args.insert(0, value)
            return args
        self.format.register(test)
        self.assertEqual(test, self.format._filters['test'])
    
    def test_intcomma(self):
        "Use intcomma for nicer number formatting"
        self.assertEqual(
            self.format(1200, 'intcomma'),
            '1,200'
        )
    
    def test_ap_state(self):
        "Return AP state style of a state"
        self.assertEqual(
            self.format(6, 'ap_state'),
            'Calif.'
        )
        self.assertEqual(
            self.format('California', 'ap_state'),
            'Calif.'
        )
        self.assertEqual(
            self.format('CA', 'ap_state'),
            'Calif.'
        )
        self.assertEqual(
            self.format('California', 'ap_state'),
            'Calif.'
        )
        self.assertEqual(
            self.format('foo', 'ap_state'),
            'foo'
        )
        self.assertEqual(
            self.format('foo', 'ap_state', failure_string='bar'),
            'bar'
        )
    
    def test_capfirst(self):
        "Returns a string with only the first character capitalized"
        self.assertEqual(
            self.format('ALLCAPS', 'capfirst'),
            'Allcaps'
        )
        self.assertEqual(
            self.format('whisper', 'capfirst'),
            'Whisper'
        )
        self.assertEqual(
            self.format('CaMeLcAsE', 'capfirst'),
            'Camelcase'
        )
        self.assertEqual(
            self.format('', 'capfirst'),
            'N/A'
        )
        self.assertEqual(
            self.format(1, 'capfirst'),
            'N/A'
        )
        self.assertEqual(
            self.format(1, 'capfirst', failure_string='bar'),
            'bar'
        )
    
    def test_dollar_signs(self):
        "Converts an integer into the corresponding number of dollar sign symbols."
        self.assertEqual(
            self.format(1, 'dollar_signs'),
            '$'
        )
        self.assertEqual(
            self.format(5, 'dollar_signs'),
            '$$$$$'
        )
        self.assertEqual(
            self.format('foo', 'dollar_signs'),
            'N/A'
        )
        self.assertEqual(
            self.format('foo', 'dollar_signs', failure_string='bar'),
            'bar'
        )
    
    def test_image(self):
        "Returns an HTML image tag"
        self.assertEqual(
            self.format('http://lorempixel.com/400/200/', 'image'),
            '<img src="http://lorempixel.com/400/200/" style="">'
        )
    
    def test_percentage(self):
        "Converts a floating point value into a percentage value."
        self.assertEqual(
            self.format(0.02, 'percentage'),
            '2.0%'
        )
        self.assertEqual(
            self.format(0.10560, 'percentage'),
            '10.6%'
        )
        self.assertEqual(
            self.format(0.10560, 'percentage', multiply=False),
            '0.1%'
        )
        self.assertEqual(
            self.format(0.10560, 'percentage', decimal_places=3),
            '10.560%'
        )
        self.assertEqual(
            self.format('foo', 'percentage'),
            'N/A'
        )
        self.assertEqual(
            self.format('foo', 'percentage', failure_string='bar'),
            'bar'
        )
    
    def test_percent_change(self):
        "Converts a floating point value into a percentage change value."
        self.assertEqual(
            self.format(0.02, 'percent_change'),
            '+2.0%'
        )
        self.assertEqual(
            self.format(-0.10560, 'percent_change'),
            '-10.6%'
        )
        self.assertEqual(
            self.format(-0.10560, 'percent_change', multiply=False),
            '-0.1%'
        )
        self.assertEqual(
            self.format(-0.10560, 'percent_change', decimal_places=3),
            '-10.560%'
        )
        self.assertEqual(
            self.format('foo', 'percent_change'),
            'N/A'
        )
        self.assertEqual(
            self.format('foo', 'percent_change', failure_string='bar'),
            'bar'
        )
    
    def test_ratio(self):
        "Converts a floating point value a X:1 ratio."
        self.assertEqual(
            self.format(1, 'ratio'),
            '1:1'
        )
        self.assertEqual(
            self.format(2, 'ratio'),
            '2:1'
        )
        self.assertEqual(
            self.format(2.2, 'ratio'),
            '2:1'
        )
        self.assertEqual(
            self.format('foo', 'ratio'),
            'N/A'
        )
        self.assertEqual(
            self.format('foo', 'ratio', failure_string='bar'),
            'bar'
        )
    
    def test_stateface(self):
        "Returns ProPublica stateface"
        self.assertEqual(
            self.format('California', 'stateface'),
            'E'
        )
        self.assertEqual(
            self.format('Wyo.', 'stateface'),
            'x'
        )
    
    def test_state_postal(self):
        "Returns a state's postal code"
        self.assertEqual(
            self.format('California', 'state_postal'),
            'CA'
        )
        self.assertEqual(
            self.format('Wyo.', 'state_postal'),
            'WY'
        )
        self.assertEqual(
            self.format('foo', 'state_postal'),
            'foo'
        )
    
    def test_title(self):
        "Converts a string into titlecase."
        self.assertEqual(
            self.format('ALLCAPS YO', 'title'),
            'Allcaps Yo'
        )
        self.assertEqual(
            self.format('whisper ing', 'title'),
            'Whisper Ing'
        )
        self.assertEqual(
            self.format('CaMeLcAsE', 'title'),
            'Camelcase'
        )
        self.assertEqual(
            self.format('', 'title'),
            'N/A'
        )
        self.assertEqual(
            self.format(1, 'title'),
            'N/A'
        )


class OpenerTest(unittest.TestCase):
    
    def test_from_file(self):
        t1 = TableFu.from_file('tests/arra.csv')
        t2 = TableFu(open('tests/arra.csv'))
        self.assertEqual(t1.table, t2.table)
    
    def test_from_url(self):
        url = "http://spreadsheets.google.com/pub?key=thJa_BvqQuNdaFfFJMMII0Q&output=csv"
        t1 = TableFu.from_url(url)
        t2 = TableFu(urllib2.urlopen(url))
        self.assertEqual(t1.table, t2.table)

class RemoteTest(unittest.TestCase):
    
    def test_use_url(self):
        "Use a response from urllib2.urlopen as our base file"
        url = "http://spreadsheets.google.com/pub?key=thJa_BvqQuNdaFfFJMMII0Q&output=csv"
        response1 = urllib2.urlopen(url)
        response2 = urllib2.urlopen(url)
        reader = csv.reader(response1)
        columns = reader.next()
        t = TableFu(response2)
        self.assertEqual(columns, t.columns)


class UpdateTest(TableTest):
    """
    Tests for things that update or otherwise transform data
    """
    def test_transform_to_int(self):
        """
        Convert the Number of Pages field to integers
        """
        t = TableFu(self.csv_file)
        pages = t.values('Number of Pages')
        t.transform('Number of Pages', int)
        for s, i in zip(pages, t.values('Number of Pages')):
            self.assertEqual(int(s), i)
        


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
