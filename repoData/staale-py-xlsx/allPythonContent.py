__FILENAME__ = formatting
# -*- coding: cp1252 -*-

##
#
# THIS IS AN EXERPT FROM XLRD's (https://github.com/python-excel/xlrd) FORMATTING.PY
#
#
# Module for formatting information.
#
# <p>Copyright © 2005-2012 Stephen John Machin, Lingfo Pty Ltd</p>
# <p>This module is part of the xlrd package, which is released under
# a BSD-style licence.</p>
##

# No part of the content of this file was derived from the works of David Giffin.

# 2010-10-30 SJM Added space after colon in "# coding" line to work around IBM iSeries Python bug
# 2009-05-31 SJM Fixed problem with non-zero reserved bits in some STYLE records in Mac Excel files
# 2008-08-03 SJM Ignore PALETTE record when Book.formatting_info is false
# 2008-08-03 SJM Tolerate up to 4 bytes trailing junk on PALETTE record
# 2008-05-10 SJM Do some XF checks only when Book.formatting_info is true
# 2008-02-08 SJM Preparation for Excel 2.0 support
# 2008-02-03 SJM Another tweak to is_date_format_string()
# 2007-12-04 SJM Added support for Excel 2.x (BIFF2) files.
# 2007-10-13 SJM Warning: style XF whose parent XF index != 0xFFF
# 2007-09-08 SJM Work around corrupt STYLE record
# 2007-07-11 SJM Allow for BIFF2/3-style FORMAT record in BIFF4/8 file

from __future__ import unicode_literals
import re


date_chars = 'ymdhs' # year, month/minute, day, hour, second
date_char_dict = {}
for _c in date_chars + date_chars.upper():
    date_char_dict[_c] = 5
del _c, date_chars

skip_char_dict = {}
for _c in '$-+/(): ':
    skip_char_dict[_c] = 1

num_char_dict = {
    '0': 5,
    '#': 5,
    '?': 5,
    }

non_date_formats = {
    '0.00E+00':1,
    '##0.0E+0':1,
    'General' :1,
    'GENERAL' :1, # OOo Calc 1.1.4 does this.
    'general' :1,  # pyExcelerator 0.6.3 does this.
    '@'       :1,
    }

fmt_bracketed_sub = re.compile(r'\[[^]]*\]').sub


def is_date_format_string(fmt):
    # Heuristics:
    # Ignore "text" and [stuff in square brackets (aarrgghh -- see below)].
    # Handle backslashed-escaped chars properly.
    # E.g. hh\hmm\mss\s should produce a display like 23h59m59s
    # Date formats have one or more of ymdhs (caseless) in them.
    # Numeric formats have # and 0.
    # N.B. u'General"."' hence get rid of "text" first.
    # TODO: Find where formats are interpreted in Gnumeric
    # TODO: u'[h]\\ \\h\\o\\u\\r\\s' ([h] means don't care about hours > 23)
    state = 0
    s = ''
    ignorable = lambda key: key in skip_char_dict
    for c in fmt:
        if state == 0:
            if c == '"':
                state = 1
            elif c in r"\_*":
                state = 2
            elif ignorable(c):
                pass
            else:
                s += c
        elif state == 1:
            if c == '"':
                state = 0
        elif state == 2:
            # Ignore char after backslash, underscore or asterisk
            state = 0
        assert 0 <= state <= 2
    s = fmt_bracketed_sub('', s)
    if s in non_date_formats:
        return False
    state = 0
    separator = ";"
    got_sep = 0
    date_count = num_count = 0
    for c in s:
        if c in date_char_dict:
            date_count += date_char_dict[c]
        elif c in num_char_dict:
            num_count += num_char_dict[c]
        elif c == separator:
            got_sep = 1
    # print num_count, date_count, repr(fmt)
    if date_count and not num_count:
        return True
    if num_count and not date_count:
        return False
    return date_count > num_count

########NEW FILE########
__FILENAME__ = test_basic
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import unittest

import six

from xlsx import Workbook

class WorkbookTestCase(unittest.TestCase):

    def setUp(self):
        """ Getting all file from fixtures dir """
        self.workbooks = {}
        fixtures_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                    'fixtures'))
        xlsx_files = os.listdir(fixtures_dir)
        for filename in xlsx_files:
            self.workbooks[filename] = Workbook(
                os.path.join(fixtures_dir, filename))

    def test_basic(self):
        """ These test will run for all test files """

        for filename, workbook in self.workbooks.items():
            for sheet in workbook:
                assert hasattr(sheet, 'id')
                assert isinstance(sheet.name, six.string_types)
                assert isinstance(sheet.rows(), dict)
                assert isinstance(sheet.cols(), dict)

                for row_num, cells in six.iteritems(sheet.rows()):
                    assert isinstance(row_num, int)
                    assert isinstance(cells, list)
                    for cell in cells:
                        assert hasattr(cell, 'id')
                        assert hasattr(cell, 'column')
                        assert hasattr(cell, 'row')
                        assert hasattr(cell, 'value')
                        assert cell.row == row_num

    def test_test1(self):
        """ Specific test for `testdata/test1.xslx` file including
        unicode strings and different date formats
        """
        workbook = self.workbooks['test1.xlsx']

        self.assertEqual(workbook[1].name, 'рускии')
        self.assertEqual(workbook[2].name, '性 文化交流 例如')
        self.assertEqual(workbook[3].name, 'تعد. بحق طائ')

        for row_num, cells in six.iteritems(workbook[1].rows()):
            if row_num == 1:
                self.assertEqual(cells[0].value, 'лорем ипсум')
                self.assertEqual(cells[1].value, '2')
            if row_num == 2: #Test date fields
                self.assertEqual(cells[0].value, (2010, 11, 12, 0, 0, 0))
                self.assertEqual(cells[1].value, (1987, 12, 20, 0, 0, 0))
                self.assertEqual(cells[2].value, (1987, 12, 20, 0, 0, 0))
                self.assertEqual(cells[3].value, (1987, 12, 20, 0, 0, 0))
                break

        # Cell A1 in '性 文化交流 例如'
        self.assertEqual(workbook[2].cols()['A'][0].value,
                         '性 文化交流 例如')
        self.assertEqual(workbook[2].cols()['A'][1].value,
                         'エム セシビ め「こを バジョン')

    def test_dcterms_modified(self):
        self.assertTrue(self.workbooks['test1.xlsx'].dcterms_modified is None)
        self.assertEqual(self.workbooks['modified_date.xlsx'].dcterms_modified,
                         '2012-07-01T05:04:12Z')

    def test_cell_str(self):
        workbook = self.workbooks['test1.xlsx']
        cell = workbook[2].cols()['A'][0]
        value = '<Cell [A1] : "性 文化交流 例如" (None)>'
        # Python 2 returns bytestring (str type), Python 3 returns unicode (str type).
        if six.PY2:
            self.assertEqual(str(cell), value.encode('utf-8'))
        else: # Python 3.
            self.assertEqual(str(cell), value)

    def test_cell_unicode(self):
        workbook = self.workbooks['test1.xlsx']
        cell = workbook[2].cols()['A'][0]
        value = '<Cell [A1] : "性 文化交流 例如" (None)>'
        # Both Python 2 and 3 should return the same (unicode, or str on Python 3) here.
        self.assertEqual(cell.__unicode__(), value)

    def test_dates(self):
        # tests out different date formats
        workbook = self.workbooks['test_dates.xlsx']
        self.assertEqual(workbook[1]['B1'].value, '1')
        self.assertEqual(workbook[1]['B2'].value, (2012, 8, 13, 0, 0, 0))
        self.assertEqual(workbook[1]['B3'].value, (1900, 3, 1, 0, 0, 0))
        self.assertEqual(workbook[1]['B4'].value, (2200, 12, 31, 0, 0, 0))
        self.assertEqual(workbook[1]['B5'].value, (2012, 8, 13, 12, 11, 0))


class FileHandleWorkbookTestCase(WorkbookTestCase):
    """
    Run all the same tests in WorkbookTestCase, but using open file handles
    instead of file paths.
    """

    def setUp(self):
        """ Getting all file from fixtures dir """
        self.workbooks = {}
        fixtures_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                    'fixtures'))
        xlsx_files = os.listdir(fixtures_dir)
        for filename in xlsx_files:
            filepath = os.path.join(fixtures_dir, filename)
            self.workbooks[filename] = Workbook(open(filepath, 'rb'))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = timemachine
# -*- coding: utf-8 -*-
"""
Compatibility shims for different Python versions.
"""

import sys


def int_floor_div(x, y):
    return divmod(x, y)[0]


class UnicodeMixin(object):
    """
    Mixin class to handle defining proper __str__/__unicode__ methods for
    cross-compatibility with running on either Python 2 or 3.

    Define a __unicode__ method that returns unicode on the target class, and
    this mixin will add the proper __str__ method.
    """
    if sys.version_info[0] >= 3: # Python 3
        def __str__(self):
            return self.__unicode__()
    else:  # Python 2
        def __str__(self):
            return self.__unicode__().encode('utf8')

########NEW FILE########
__FILENAME__ = xldate
# -*- coding: cp1252 -*-

# No part of the content of this file was derived from the works of David Giffin.

##
# <p>Copyright ? 2005-2008 Stephen John Machin, Lingfo Pty Ltd</p>
# <p>This module is part of the xlrd package, which is released under a BSD-style licence.</p>
#
# <p>Provides function(s) for dealing with Microsoft Excel ? dates.</p>
##

# 2008-10-18 SJM Fix bug in xldate_from_date_tuple (affected some years after 2099)

# The conversion from days to (year, month, day) starts with
# an integral "julian day number" aka JDN.
# FWIW, JDN 0 corresponds to noon on Monday November 24 in Gregorian year -4713.
# More importantly:
#    Noon on Gregorian 1900-03-01 (day 61 in the 1900-based system) is JDN 2415080.0
#    Noon on Gregorian 1904-01-02 (day  1 in the 1904-based system) is JDN 2416482.0

from xlsx.timemachine import int_floor_div as ifd

_JDN_delta = (2415080 - 61, 2416482 - 1)
assert _JDN_delta[1] - _JDN_delta[0] == 1462

class XLDateError(ValueError): pass

class XLDateNegative(XLDateError): pass
class XLDateAmbiguous(XLDateError): pass
class XLDateTooLarge(XLDateError): pass
class XLDateBadDatemode(XLDateError): pass
class XLDateBadTuple(XLDateError): pass

_XLDAYS_TOO_LARGE = (2958466, 2958466 - 1462) # This is equivalent to 10000-01-01

##
# Convert an Excel number (presumed to represent a date, a datetime or a time) into
# a tuple suitable for feeding to datetime or mx.DateTime constructors.
# @param xldate The Excel number
# @param datemode 0: 1900-based, 1: 1904-based.
# <br>WARNING: when using this function to
# interpret the contents of a workbook, you should pass in the Book.datemode
# attribute of that workbook. Whether
# the workbook has ever been anywhere near a Macintosh is irrelevant.
# @return Gregorian (year, month, day, hour, minute, nearest_second).
# <br>Special case: if 0.0 <= xldate < 1.0, it is assumed to represent a time;
# (0, 0, 0, hour, minute, second) will be returned.
# <br>Note: 1904-01-01 is not regarded as a valid date in the datemode 1 system; its "serial number"
# is zero.
# @throws XLDateNegative xldate < 0.00
# @throws XLDateAmbiguous The 1900 leap-year problem (datemode == 0 and 1.0 <= xldate < 61.0)
# @throws XLDateTooLarge Gregorian year 10000 or later
# @throws XLDateBadDatemode datemode arg is neither 0 nor 1
# @throws XLDateError Covers the 4 specific errors

def xldate_as_tuple(xldate, datemode):
    if datemode not in (0, 1):
        raise XLDateBadDatemode(datemode)
    if xldate == 0.00:
        return (0, 0, 0, 0, 0, 0)
    if xldate < 0.00:
        raise XLDateNegative(xldate)
    xldays = int(xldate)
    frac = xldate - xldays
    seconds = int(round(frac * 86400.0))
    assert 0 <= seconds <= 86400
    if seconds == 86400:
        hour = minute = second = 0
        xldays += 1
    else:
        # second = seconds % 60; minutes = seconds // 60
        minutes, second = divmod(seconds, 60)
        # minute = minutes % 60; hour    = minutes // 60
        hour, minute = divmod(minutes, 60)
    if xldays >= _XLDAYS_TOO_LARGE[datemode]:
        raise XLDateTooLarge(xldate)

    if xldays == 0:
        return (0, 0, 0, hour, minute, second)

    if xldays < 61 and datemode == 0:
        raise XLDateAmbiguous(xldate)

    jdn = xldays + _JDN_delta[datemode]
    yreg = (ifd(ifd(jdn * 4 + 274277, 146097) * 3, 4) + jdn + 1363) * 4 + 3
    mp = ifd(yreg % 1461, 4) * 535 + 333
    d = ifd(mp % 16384, 535) + 1
    # mp /= 16384
    mp >>= 14
    if mp >= 10:
        return (ifd(yreg, 1461) - 4715, mp - 9, d, hour, minute, second)
    else:
        return (ifd(yreg, 1461) - 4716, mp + 3, d, hour, minute, second)

# === conversions from date/time to xl numbers

def _leap(y):
    if y % 4: return 0
    if y % 100: return 1
    if y % 400: return 0
    return 1

_days_in_month = (None, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

##
# Convert a date tuple (year, month, day) to an Excel date.
# @param year Gregorian year.
# @param month 1 <= month <= 12
# @param day 1 <= day <= last day of that (year, month)
# @param datemode 0: 1900-based, 1: 1904-based.
# @throws XLDateAmbiguous The 1900 leap-year problem (datemode == 0 and 1.0 <= xldate < 61.0)
# @throws XLDateBadDatemode datemode arg is neither 0 nor 1
# @throws XLDateBadTuple (year, month, day) is too early/late or has invalid component(s)
# @throws XLDateError Covers the specific errors

def xldate_from_date_tuple(year_month_day, datemode):
    (year, month, day) = year_month_day

    if datemode not in (0, 1):
        raise XLDateBadDatemode(datemode)

    if year == 0 and month == 0 and day == 0:
        return 0.00

    if not (1900 <= year <= 9999):
        raise XLDateBadTuple("Invalid year: %r" % ((year, month, day),))
    if not (1 <= month <= 12):
        raise XLDateBadTuple("Invalid month: %r" % ((year, month, day),))
    if  day < 1 \
    or (day > _days_in_month[month] and not(day == 29 and month == 2 and _leap(year))):
        raise XLDateBadTuple("Invalid day: %r" % ((year, month, day),))

    Yp = year + 4716
    M = month
    if M <= 2:
        Yp = Yp - 1
        Mp = M + 9
    else:
        Mp = M - 3
    jdn = ifd(1461 * Yp, 4) + ifd(979 * Mp + 16, 32) + \
        day - 1364 - ifd(ifd(Yp + 184, 100) * 3, 4)
    xldays = jdn - _JDN_delta[datemode]
    if xldays <= 0:
        raise XLDateBadTuple("Invalid (year, month, day): %r" % ((year, month, day),))
    if xldays < 61 and datemode == 0:
        raise XLDateAmbiguous("Before 1900-03-01: %r" % ((year, month, day),))
    return float(xldays)

##
# Convert a time tuple (hour, minute, second) to an Excel "date" value (fraction of a day).
# @param hour 0 <= hour < 24
# @param minute 0 <= minute < 60
# @param second 0 <= second < 60
# @throws XLDateBadTuple Out-of-range hour, minute, or second

def xldate_from_time_tuple(hour_minute_second):
    (hour, minute, second) = hour_minute_second
    if 0 <= hour < 24 and 0 <= minute < 60 and 0 <= second < 60:
        return ((second / 60.0 + minute) / 60.0 + hour) / 24.0
    raise XLDateBadTuple("Invalid (hour, minute, second): %r" % ((hour, minute, second),))

##
# Convert a datetime tuple (year, month, day, hour, minute, second) to an Excel date value.
# For more details, refer to other xldate_from_*_tuple functions.
# @param datetime_tuple (year, month, day, hour, minute, second)
# @param datemode 0: 1900-based, 1: 1904-based.

def xldate_from_datetime_tuple(datetime_tuple, datemode):
    return (
        xldate_from_date_tuple(datetime_tuple[:3], datemode)
        +
        xldate_from_time_tuple(datetime_tuple[3:])
        )

########NEW FILE########
