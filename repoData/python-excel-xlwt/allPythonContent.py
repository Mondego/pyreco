__FILENAME__ = licences
# -*- coding: cp1252 -*-

"""
Portions copyright © 2007, Stephen John Machin, Lingfo Pty Ltd
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer. 

2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution. 

3. None of the names of Stephen John Machin, Lingfo Pty Ltd and any
contributors may be used to endorse or promote products derived from this
software without specific prior written permission. 

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS
BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
THE POSSIBILITY OF SUCH DAMAGE.
"""

"""
  Copyright (C) 2005 Roman V. Kiseliov
  All rights reserved.
 
  Redistribution and use in source and binary forms, with or without
  modification, are permitted provided that the following conditions
  are met:
 
  1. Redistributions of source code must retain the above copyright
     notice, this list of conditions and the following disclaimer.
 
  2. Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in
     the documentation and/or other materials provided with the
     distribution.
 
  3. All advertising materials mentioning features or use of this
     software must display the following acknowledgment:
     "This product includes software developed by
      Roman V. Kiseliov <roman@kiseliov.ru>."
 
  4. Redistributions of any form whatsoever must retain the following
     acknowledgment:
     "This product includes software developed by
      Roman V. Kiseliov <roman@kiseliov.ru>."
 
  THIS SOFTWARE IS PROVIDED BY Roman V. Kiseliov ``AS IS'' AND ANY
  EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
  PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL Roman V. Kiseliov OR
  ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
  NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
  LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
  HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
  STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
  ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
  OF THE POSSIBILITY OF SUCH DAMAGE.

Roman V. Kiseliov
Russia
Kursk
Libknecht St., 4

+7(0712)56-09-83

<roman@kiseliov.ru>
Subject: pyExcelerator
"""

"""
Portions of xlwt.Utils based on:
pyXLWriter - A library for generating Excel Spreadsheets

The licensing of pyXLWriter is as follows:

 Copyright (c) 2004 Evgeny Filatov <fufff@users.sourceforge.net>
 Copyright (c) 2002-2004 John McNamara (Perl Spreadsheet::WriteExcel)

 This library is free software; you can redistribute it and/or modify it
 under the terms of the GNU Lesser General Public License as published by
 the Free Software Foundation; either version 2.1 of the License, or
 (at your option) any later version.

 This library is distributed in the hope that it will be useful, but
 WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
 General Public License for more details:

 http://www.gnu.org/licenses/lgpl.html

 pyXLWriter also makes reference to the PERL Spreadsheet::WriteExcel as follows:
 
 ----------------------------------------------------------------------------
  This module was written/ported from PERL Spreadsheet::WriteExcel module
  The author of the PERL Spreadsheet::WriteExcel module is John McNamara
  <jmcnamara@cpan.org>
 ----------------------------------------------------------------------------

"""


########NEW FILE########
__FILENAME__ = RKbug
from xlwt import *
import sys
from struct import pack, unpack

def cellname(rowx, colx):
    # quick kludge, works up to 26 cols :-)
    return chr(ord('A') + colx) + str(rowx + 1)

def RK_pack_check(num, anint, case=None):
    if not(-0x7fffffff - 1 <= anint <= 0x7fffffff):
        print "RK_pack_check: not a signed 32-bit int: %r (%r); case: %r" \
            % (anint, hex(anint), case)
    pstr = pack("<i", anint)
    actual = unpack_RK(pstr)
    if actual != num:
        print "RK_pack_check: round trip failure: %r (%r); case %r;  %r in, %r out" \
            % (anint, hex(anint), case, num, actual)
 

def RK_encode(num, blah=0):
    """\
    Return a 4-byte RK encoding of the input float value
    if possible, else return None.
    """
    rk_encoded = 0
    packed = pack('<d', num)

    if blah: print
    if blah: print repr(num)
    w01, w23 = unpack('<2i', packed)
    if not w01 and not(w23 & 3):
        # 34 lsb are 0
        if blah: print "float RK", w23, hex(w23)
        return RK_pack_check(num, w23, 0)
        # return RKRecord(
        #    self.__parent.get_index(), self.__idx, self.__xf_idx, w23).get()

    if -0x20000000 <= num < 0x20000000:
        inum = int(num)
        if inum == num:
            if blah: print "30-bit integer RK", inum, hex(inum)
            rk_encoded = 2 | (inum << 2)
            if blah: print "rk", rk_encoded, hex(rk_encoded)
            return RK_pack_check(num, rk_encoded, 2)
            # return RKRecord(
            #     self.__parent.get_index(), self.__idx, self.__xf_idx, rk_encoded).get()

    temp = num * 100
    packed100 = pack('<d', temp)
    w01, w23 = unpack('<2i', packed100)
    if not w01 and not(w23 & 3):
        # 34 lsb are 0
        if blah: print "float RK*100", w23, hex(w23)
        return RK_pack_check(num, w23 | 1, 1)
        # return RKRecord(
        #    self.__parent.get_index(), self.__idx, self.__xf_idx, w23 | 1).get()

    if -0x20000000 <= temp < 0x20000000:
        itemp = int(round(temp, 0))
        if blah: print (itemp == temp), (itemp / 100.0 == num)
        if itemp / 100.0 == num:
            if blah: print "30-bit integer RK*100", itemp, hex(itemp)
            rk_encoded = 3 | (itemp << 2)
            return RK_pack_check(num, rk_encoded, 3)
            # return RKRecord(
            #    self.__parent.get_index(), self.__idx, self.__xf_idx, rk_encoded).get()

    if blah: print "Number" 
    # return NumberRecord(
    #    self.__parent.get_index(), self.__idx, self.__xf_idx, num).get()

def unpack_RK(rk_str):
    flags = ord(rk_str[0])
    if flags & 2:
        # There's a SIGNED 30-bit integer in there!
        i,  = unpack('<i', rk_str)
        i >>= 2 # div by 4 to drop the 2 flag bits
        if flags & 1:
            return i / 100.0
        return float(i)
    else:
        # It's the most significant 30 bits of an IEEE 754 64-bit FP number
        d, = unpack('<d', '\0\0\0\0' + chr(flags & 252) + rk_str[1:4])
        if flags & 1:
            return d / 100.0
        return d

testvals = (
    130.63999999999999,
    130.64,
    -18.649999999999999,
    -18.65,
    137.19999999999999,
    137.20,
    -16.079999999999998,
    -16.08,
    0,
    1,
    2,
    3,
    0x1fffffff,
    0x20000000,
    0x20000001,
    1000999999,
    0x3fffffff,
    0x40000000,
    0x40000001,
    0x7fffffff,
    0x80000000,
    0x80000001,
    0xffffffff,
    0x100000000,
    0x100000001,
    )

XLS = 1
BLAH = 1

def main(do_neg):
    if XLS:
        w = Workbook()
        ws = w.add_sheet('Test RK encoding')
        for colx, heading in enumerate(('actual', 'expected', 'OK') * 2):
            ws.write(0, colx, heading)
    rx = 0
    for neg in range(do_neg + 1):
        for seed in testvals:
            rx += 1
            for i in range(2):
                bv = [seed, seed /100.00][i] * (1 - 2 * neg)
                bv = float(bv) # pyExcelerator cracks it with longs
                cx = i * 3
                if XLS:
                    ws.write(rx, cx, bv)
                    ws.write(rx, cx + 1, repr(bv))
                    ws.write(rx, cx + 2, Formula(
                        '%s=VALUE(%s)' % (cellname(rx, cx), cellname(rx, cx + 1))
                        ))
                else:
                    RK_encode(bv, blah=BLAH)
    if XLS:                        
        w.save('RKbug%d.xls' % do_neg)

if __name__ == "__main__":
    # arg == 0: only positive test values used
    # arg == 1: both positive & negative test values used
    main(int(sys.argv[1]))

########NEW FILE########
__FILENAME__ = test_biff_records
#!/usr/bin/env python
#coding:utf-8
# Author:  mozman --<mozman@gmx.at>
# Purpose: test BIFF records
# Created: 09.12.2010
# Copyright (C) 2010, Manfred Moitzi
# License: BSD licence

import unittest

from xlwt import BIFFRecords

class TestSharedStringTable(unittest.TestCase):
    def test_shared_string_table(self):
        expected_result = b'\xfc\x00\x11\x00\x01\x00\x00\x00\x01\x00\x00\x00\x03\x00\x01\x1e\x04;\x04O\x04'
        string_record = BIFFRecords.SharedStringTable(encoding='cp1251')
        string_record.add_str(u'ÐžÐ»Ñ')
        self.assertEqual(expected_result, string_record.get_biff_record())

if __name__=='__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_compound_doc
#!/usr/bin/env python
#coding:utf-8
# Author:  mozman --<mozman@gmx.at>
# Purpose: test CompoundDoc
# Created: 09.12.2010
# Copyright (C) 2010, Manfred Moitzi
# License: BSD licence

import unittest

from xlwt.CompoundDoc import XlsDoc

DIR = b'R\x00o\x00o\x00t\x00 \x00E\x00n\x00t\x00r\x00y\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x16\x00\x05\x01\xff\xff\xff\xff\xff\xff\xff\xff\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xfe\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00W\x00o\x00r\x00k\x00b\x00o\x00o\x00k\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x12\x00\x02\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xfe\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xfe\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00'

PACKED_SAT = b'\x01\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00\x04\x00\x00\x00\x05\x00\x00\x00\x06\x00\x00\x00\x07\x00\x00\x00\xfe\xff\xff\xff\xfd\xff\xff\xff\xfe\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
PACKED_MSAT_1ST = b'\x08\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
PACKED_MSAT_2ND = b""
BOOK_STREAM_SECT = [0, 1, 2, 3, 4, 5, 6, 7]
SAT_SECT = [8]
MSAT_SECT_2ND = []

HEADER = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00>\x00\x03\x00\xfe\xff\t\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\t\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\xfe\xff\xff\xff\x00\x00\x00\x00\xfe\xff\xff\xff\x00\x00\x00\x00'

class TestXlsDoc(unittest.TestCase):
    def test_build_directory(self):
        xlsdoc = XlsDoc()
        xlsdoc.book_stream_len = 0x1000
        xlsdoc._build_directory()
        self.assertEqual(DIR, xlsdoc.dir_stream)

    def test_build_sat(self):
        xlsdoc = XlsDoc()
        xlsdoc.book_stream_len = 0x1000
        xlsdoc._build_directory()
        xlsdoc._build_sat()
        self.assertEqual(PACKED_SAT, xlsdoc.packed_SAT)
        self.assertEqual(PACKED_MSAT_1ST, xlsdoc.packed_MSAT_1st)
        self.assertEqual(PACKED_MSAT_2ND, xlsdoc.packed_MSAT_2nd)
        self.assertEqual(BOOK_STREAM_SECT, xlsdoc.book_stream_sect)
        self.assertEqual(SAT_SECT, xlsdoc.SAT_sect)
        self.assertEqual(MSAT_SECT_2ND, xlsdoc.MSAT_sect_2nd)

    def test_build_header(self):
        xlsdoc = XlsDoc()
        xlsdoc.book_stream_len = 0x1000
        xlsdoc._build_directory()
        xlsdoc._build_sat()
        xlsdoc._build_header()
        self.assertEqual(HEADER, xlsdoc.header)

if __name__=='__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_easyxf
#!/usr/bin/env python
#coding:utf-8
# Author:  mozman --<mozman@gmx.at>
# Purpose: test_mini
# Created: 03.12.2010
# Copyright (C) 2010, Manfred Moitzi
# License: BSD licence

import sys
import os
import unittest
import filecmp
import datetime

import xlwt as xlwt
ezxf = xlwt.easyxf

def write_xls(file_name, sheet_name, headings, data, heading_xf, data_xfs):
    book = xlwt.Workbook()
    sheet = book.add_sheet(sheet_name)
    rowx = 0
    for colx, value in enumerate(headings):
        sheet.write(rowx, colx, value, heading_xf)
    sheet.set_panes_frozen(True) # frozen headings instead of split panes
    sheet.set_horz_split_pos(rowx+1) # in general, freeze after last heading row
    sheet.set_remove_splits(True) # if user does unfreeze, don't leave a split there
    for row in data:
        rowx += 1
        for colx, value in enumerate(row):
            sheet.write(rowx, colx, value, data_xfs[colx])
    book.save(file_name)

def from_tst_dir(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

EXAMPLE_XLS = 'xlwt_easyxf_simple_demo.xls'

class TestUnicode0(unittest.TestCase):
    def create_example_xls(self):
        mkd = datetime.date
        hdngs = ['Date', 'Stock Code', 'Quantity', 'Unit Price', 'Value', 'Message']
        kinds =  'date    text          int         price         money    text'.split()
        data = [
            [mkd(2007, 7, 1), 'ABC', 1000, 1.234567, 1234.57, ''],
            [mkd(2007, 12, 31), 'XYZ', -100, 4.654321, -465.43, 'Goods returned'],
            ] + [
                [mkd(2008, 6, 30), 'PQRCD', 100, 2.345678, 234.57, ''],
            ] * 100

        heading_xf = ezxf('font: bold on; align: wrap on, vert centre, horiz center')
        kind_to_xf_map = {
            'date': ezxf(num_format_str='yyyy-mm-dd'),
            'int': ezxf(num_format_str='#,##0'),
            'money': ezxf('font: italic on; pattern: pattern solid, fore-colour grey25',
                num_format_str='$#,##0.00'),
            'price': ezxf(num_format_str='#0.000000'),
            'text': ezxf(),
            }
        data_xfs = [kind_to_xf_map[k] for k in kinds]
        write_xls(EXAMPLE_XLS, 'Demo', hdngs, data, heading_xf, data_xfs)

    def test_example_xls(self):
        self.create_example_xls()
        self.assertTrue(filecmp.cmp(from_tst_dir(EXAMPLE_XLS),
                                    from_tst_dir('output-0.7.2/'+EXAMPLE_XLS),
                                    shallow=False))

if __name__=='__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_mini
#!/usr/bin/env python
#coding:utf-8
# Author:  mozman --<mozman@gmx.at>
# Purpose: test_mini
# Created: 03.12.2010
# Copyright (C) 2010, Manfred Moitzi
# License: BSD licence

import sys
import os
import unittest
import filecmp

import xlwt

def from_tst_dir(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

class TestMini(unittest.TestCase):
    def test_create_mini_xls(self):
        book = xlwt.Workbook()
        sheet = book.add_sheet('xlwt was here')
        book.save('mini.xls')

        self.assertTrue(filecmp.cmp(from_tst_dir('mini.xls'),
                                    from_tst_dir(os.path.join('output-0.7.2', 'mini.xls')),
                                    shallow=False))

if __name__=='__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_simple
#!/usr/bin/env python
#coding:utf-8
# Author:  mozman --<mozman@gmx.at>
# Purpose: test_simple
# Created: 05.12.2010
# Copyright (C) 2010, Manfred Moitzi
# License: BSD licence

import sys
import os
import unittest
import filecmp
from datetime import datetime

import xlwt

def from_tst_dir(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

class TestSimple(unittest.TestCase):
    def create_simple_xls(self):
        font0 = xlwt.Font()
        font0.name = 'Times New Roman'
        font0.colour_index = 2
        font0.bold = True

        style0 = xlwt.XFStyle()
        style0.font = font0

        style1 = xlwt.XFStyle()
        style1.num_format_str = 'D-MMM-YY'

        wb = xlwt.Workbook()
        ws = wb.add_sheet('A Test Sheet')

        ws.write(0, 0, 'Test', style0)
        ws.write(1, 0, datetime(2010, 12, 5), style1)
        ws.write(2, 0, 1)
        ws.write(2, 1, 1)
        ws.write(2, 2, xlwt.Formula("A3+B3"))

        wb.save('simple.xls')

    def test_create_simple_xls(self):
        self.create_simple_xls()
        self.assertTrue(filecmp.cmp(from_tst_dir('simple.xls'),
                                    from_tst_dir(os.path.join('output-0.7.2', 'simple.xls')),
                                    shallow=False))

if __name__=='__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_unicode1
#!/usr/bin/env python
#coding:utf-8
# Author:  mozman --<mozman@gmx.at>
# Purpose: test_mini
# Created: 03.12.2010
# Copyright (C) 2010, Manfred Moitzi
# License: BSD licence

import sys
import os
import unittest
import filecmp

import xlwt

def from_tst_dir(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

def create_example_xls(filename):
    w = xlwt.Workbook()
    ws1 = w.add_sheet(u'\N{GREEK SMALL LETTER ALPHA}\N{GREEK SMALL LETTER BETA}\N{GREEK SMALL LETTER GAMMA}')

    ws1.write(0, 0, u'\N{GREEK SMALL LETTER ALPHA}\N{GREEK SMALL LETTER BETA}\N{GREEK SMALL LETTER GAMMA}')
    ws1.write(1, 1, u'\N{GREEK SMALL LETTER DELTA}x = 1 + \N{GREEK SMALL LETTER DELTA}')

    ws1.write(2,0, u'A\u2262\u0391.')     # RFC2152 example
    ws1.write(3,0, u'Hi Mom -\u263a-!')   # RFC2152 example
    ws1.write(4,0, u'\u65E5\u672C\u8A9E') # RFC2152 example
    ws1.write(5,0, u'Item 3 is \u00a31.') # RFC2152 example
    ws1.write(8,0, u'\N{INTEGRAL}')       # RFC2152 example

    w.add_sheet(u'A\u2262\u0391.')     # RFC2152 example
    w.add_sheet(u'Hi Mom -\u263a-!')   # RFC2152 example
    one_more_ws = w.add_sheet(u'\u65E5\u672C\u8A9E') # RFC2152 example
    w.add_sheet(u'Item 3 is \u00a31.') # RFC2152 example

    one_more_ws.write(0, 0, u'\u2665\u2665')

    w.add_sheet(u'\N{GREEK SMALL LETTER ETA WITH TONOS}')
    w.save(filename)

EXAMPLE_XLS = 'unicode1.xls'

class TestUnicode1(unittest.TestCase):

    def test_example_xls(self):
        create_example_xls(EXAMPLE_XLS)
        self.assertTrue(filecmp.cmp(from_tst_dir(EXAMPLE_XLS),
                                    from_tst_dir(os.path.join('output-0.7.2', EXAMPLE_XLS)),
                                    shallow=False))
if __name__=='__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_unicodeutils
#!/usr/bin/env python
#coding:utf-8
# Author:  mozman
# Purpose:
# Created: 05.12.2010
# Copyright (C) 2010, Manfred Moitzi
# License: BSD licence

import sys
import unittest

from xlwt.UnicodeUtils import upack1, upack2

class TestUpack(unittest.TestCase):
    def test_upack1(self):
        result = b'\x1d\x00abcdefghijklmnopqrstuvwxyz\xd6\xc4\xdc'
        ustr = upack1(u"abcdefghijklmnopqrstuvwxyzÃ–Ã„Ãœ")
        self.assertEqual(ustr, result)

    def test_upack2_ascii(self):
        result = b'\x1d\x00\x00abcdefghijklmnopqrstuvwxyz\xd6\xc4\xdc'
        ustr = upack2(u"abcdefghijklmnopqrstuvwxyzÃ–Ã„Ãœ")
        self.assertEqual(ustr, result)

    def test_upack2_latin1(self):
        result = b'\x1d\x00\x00abcdefghijklmnopqrstuvwxyz\xd6\xc4\xdc'
        ustr = upack2(u"abcdefghijklmnopqrstuvwxyzÃ–Ã„Ãœ", encoding='latin1')
        self.assertEqual(ustr, result)

    def test_upack2_cp1251(self):
        result = b'\x1d\x00\x00abcdefghijklmnopqrstuvwxyz\xce\xeb\xff'
        ustr = upack2(u"abcdefghijklmnopqrstuvwxyz\xce\xeb\xff", encoding='cp1251')
        self.assertEqual(ustr, result)

    def test_unicode(self):
        chr_ = chr if (sys.version_info[0] >= 3) else unichr
        result = b'\x00\x02\x01\x00\x00\x01\x00\x02\x00\x03\x00\x04\x00\x05\x00\x06\x00\x07\x00\x08\x00\t\x00\n\x00\x0b\x00\x0c\x00\r\x00\x0e\x00\x0f\x00\x10\x00\x11\x00\x12\x00\x13\x00\x14\x00\x15\x00\x16\x00\x17\x00\x18\x00\x19\x00\x1a\x00\x1b\x00\x1c\x00\x1d\x00\x1e\x00\x1f\x00 \x00!\x00"\x00#\x00$\x00%\x00&\x00\'\x00(\x00)\x00*\x00+\x00,\x00-\x00.\x00/\x000\x001\x002\x003\x004\x005\x006\x007\x008\x009\x00:\x00;\x00<\x00=\x00>\x00?\x00@\x00A\x00B\x00C\x00D\x00E\x00F\x00G\x00H\x00I\x00J\x00K\x00L\x00M\x00N\x00O\x00P\x00Q\x00R\x00S\x00T\x00U\x00V\x00W\x00X\x00Y\x00Z\x00[\x00\\\x00]\x00^\x00_\x00`\x00a\x00b\x00c\x00d\x00e\x00f\x00g\x00h\x00i\x00j\x00k\x00l\x00m\x00n\x00o\x00p\x00q\x00r\x00s\x00t\x00u\x00v\x00w\x00x\x00y\x00z\x00{\x00|\x00}\x00~\x00\x7f\x00\x80\x00\x81\x00\x82\x00\x83\x00\x84\x00\x85\x00\x86\x00\x87\x00\x88\x00\x89\x00\x8a\x00\x8b\x00\x8c\x00\x8d\x00\x8e\x00\x8f\x00\x90\x00\x91\x00\x92\x00\x93\x00\x94\x00\x95\x00\x96\x00\x97\x00\x98\x00\x99\x00\x9a\x00\x9b\x00\x9c\x00\x9d\x00\x9e\x00\x9f\x00\xa0\x00\xa1\x00\xa2\x00\xa3\x00\xa4\x00\xa5\x00\xa6\x00\xa7\x00\xa8\x00\xa9\x00\xaa\x00\xab\x00\xac\x00\xad\x00\xae\x00\xaf\x00\xb0\x00\xb1\x00\xb2\x00\xb3\x00\xb4\x00\xb5\x00\xb6\x00\xb7\x00\xb8\x00\xb9\x00\xba\x00\xbb\x00\xbc\x00\xbd\x00\xbe\x00\xbf\x00\xc0\x00\xc1\x00\xc2\x00\xc3\x00\xc4\x00\xc5\x00\xc6\x00\xc7\x00\xc8\x00\xc9\x00\xca\x00\xcb\x00\xcc\x00\xcd\x00\xce\x00\xcf\x00\xd0\x00\xd1\x00\xd2\x00\xd3\x00\xd4\x00\xd5\x00\xd6\x00\xd7\x00\xd8\x00\xd9\x00\xda\x00\xdb\x00\xdc\x00\xdd\x00\xde\x00\xdf\x00\xe0\x00\xe1\x00\xe2\x00\xe3\x00\xe4\x00\xe5\x00\xe6\x00\xe7\x00\xe8\x00\xe9\x00\xea\x00\xeb\x00\xec\x00\xed\x00\xee\x00\xef\x00\xf0\x00\xf1\x00\xf2\x00\xf3\x00\xf4\x00\xf5\x00\xf6\x00\xf7\x00\xf8\x00\xf9\x00\xfa\x00\xfb\x00\xfc\x00\xfd\x00\xfe\x00\xff\x00\x00\x01\x01\x01\x02\x01\x03\x01\x04\x01\x05\x01\x06\x01\x07\x01\x08\x01\t\x01\n\x01\x0b\x01\x0c\x01\r\x01\x0e\x01\x0f\x01\x10\x01\x11\x01\x12\x01\x13\x01\x14\x01\x15\x01\x16\x01\x17\x01\x18\x01\x19\x01\x1a\x01\x1b\x01\x1c\x01\x1d\x01\x1e\x01\x1f\x01 \x01!\x01"\x01#\x01$\x01%\x01&\x01\'\x01(\x01)\x01*\x01+\x01,\x01-\x01.\x01/\x010\x011\x012\x013\x014\x015\x016\x017\x018\x019\x01:\x01;\x01<\x01=\x01>\x01?\x01@\x01A\x01B\x01C\x01D\x01E\x01F\x01G\x01H\x01I\x01J\x01K\x01L\x01M\x01N\x01O\x01P\x01Q\x01R\x01S\x01T\x01U\x01V\x01W\x01X\x01Y\x01Z\x01[\x01\\\x01]\x01^\x01_\x01`\x01a\x01b\x01c\x01d\x01e\x01f\x01g\x01h\x01i\x01j\x01k\x01l\x01m\x01n\x01o\x01p\x01q\x01r\x01s\x01t\x01u\x01v\x01w\x01x\x01y\x01z\x01{\x01|\x01}\x01~\x01\x7f\x01\x80\x01\x81\x01\x82\x01\x83\x01\x84\x01\x85\x01\x86\x01\x87\x01\x88\x01\x89\x01\x8a\x01\x8b\x01\x8c\x01\x8d\x01\x8e\x01\x8f\x01\x90\x01\x91\x01\x92\x01\x93\x01\x94\x01\x95\x01\x96\x01\x97\x01\x98\x01\x99\x01\x9a\x01\x9b\x01\x9c\x01\x9d\x01\x9e\x01\x9f\x01\xa0\x01\xa1\x01\xa2\x01\xa3\x01\xa4\x01\xa5\x01\xa6\x01\xa7\x01\xa8\x01\xa9\x01\xaa\x01\xab\x01\xac\x01\xad\x01\xae\x01\xaf\x01\xb0\x01\xb1\x01\xb2\x01\xb3\x01\xb4\x01\xb5\x01\xb6\x01\xb7\x01\xb8\x01\xb9\x01\xba\x01\xbb\x01\xbc\x01\xbd\x01\xbe\x01\xbf\x01\xc0\x01\xc1\x01\xc2\x01\xc3\x01\xc4\x01\xc5\x01\xc6\x01\xc7\x01\xc8\x01\xc9\x01\xca\x01\xcb\x01\xcc\x01\xcd\x01\xce\x01\xcf\x01\xd0\x01\xd1\x01\xd2\x01\xd3\x01\xd4\x01\xd5\x01\xd6\x01\xd7\x01\xd8\x01\xd9\x01\xda\x01\xdb\x01\xdc\x01\xdd\x01\xde\x01\xdf\x01\xe0\x01\xe1\x01\xe2\x01\xe3\x01\xe4\x01\xe5\x01\xe6\x01\xe7\x01\xe8\x01\xe9\x01\xea\x01\xeb\x01\xec\x01\xed\x01\xee\x01\xef\x01\xf0\x01\xf1\x01\xf2\x01\xf3\x01\xf4\x01\xf5\x01\xf6\x01\xf7\x01\xf8\x01\xf9\x01\xfa\x01\xfb\x01\xfc\x01\xfd\x01\xfe\x01\xff\x01'
        unicodestring = ''.join( [chr_(i) for i in range(0x200)])
        self.assertEqual(result, upack2(unicodestring))

if __name__=='__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = antlr
## This file is part of PyANTLR. See LICENSE.txt for license
## details..........Copyright (C) Wolfgang Haefelinger, 2004.

## This file was copied for use with xlwt from the 2.7.7 ANTLR distribution. Yes, it
## says 2.7.5 below. The 2.7.5 distribution version didn't have a
## version in it.

## Here is the contents of the ANTLR 2.7.7 LICENSE.txt referred to above.

# SOFTWARE RIGHTS
#
# ANTLR 1989-2006 Developed by Terence Parr
# Partially supported by University of San Francisco & jGuru.com
#
# We reserve no legal rights to the ANTLR--it is fully in the
# public domain. An individual or company may do whatever
# they wish with source code distributed with ANTLR or the
# code generated by ANTLR, including the incorporation of
# ANTLR, or its output, into commerical software.
#
# We encourage users to develop software with ANTLR. However,
# we do ask that credit is given to us for developing
# ANTLR. By "credit", we mean that if you use ANTLR or
# incorporate any source code into one of your programs
# (commercial product, research project, or otherwise) that
# you acknowledge this fact somewhere in the documentation,
# research report, etc... If you like ANTLR and have
# developed a nice tool with the output, please mention that
# you developed it using ANTLR. In addition, we ask that the
# headers remain intact in our source code. As long as these
# guidelines are kept, we expect to continue enhancing this
# system and expect to make other tools available as they are
# completed.
#
# The primary ANTLR guy:
#
# Terence Parr
# parrt@cs.usfca.edu
# parrt@antlr.org

## End of contents of the ANTLR 2.7.7 LICENSE.txt ########################

## get sys module
import sys

version = sys.version.split()[0]
if version < '2.2.1':
    False = 0
if version < '2.3':
    True = not False

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                     global symbols                             ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

### ANTLR Standard Tokens
SKIP                = -1
INVALID_TYPE        = 0
EOF_TYPE            = 1
EOF                 = 1
NULL_TREE_LOOKAHEAD = 3
MIN_USER_TYPE       = 4

### ANTLR's EOF Symbol
EOF_CHAR            = ''

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                    general functions                           ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

## Version should be automatically derived from configure.in. For now,
## we need to bump it ourselfs. Don't remove the <version> tags.
## <version>
def version():
    r = {
        'major'  : '2',
        'minor'  : '7',
        'micro'  : '5',
        'patch'  : '' ,
        'version': '2.7.5'
        }
    return r
## </version>

def error(fmt,*args):
    if fmt:
        print "error: ", fmt % tuple(args)

def ifelse(cond,_then,_else):
    if cond :
        r = _then
    else:
        r = _else
    return r

def is_string_type(x):
    # return  (isinstance(x,str) or isinstance(x,unicode))
    # Simplify; xlwt doesn't support Python < 2.3
    return isinstance(basestring)

def assert_string_type(x):
    assert is_string_type(x)
    pass

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                     ANTLR Exceptions                           ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class ANTLRException(Exception):

    def __init__(self, *args):
        Exception.__init__(self, *args)


class RecognitionException(ANTLRException):

    def __init__(self, *args):
        ANTLRException.__init__(self, *args)
        self.fileName = None
        self.line = -1
        self.column = -1
        if len(args) >= 2:
            self.fileName = args[1]
        if len(args) >= 3:
            self.line = args[2]
        if len(args) >= 4:
            self.column = args[3]

    def __str__(self):
        buf = ['']
        if self.fileName:
            buf.append(self.fileName + ":")
        if self.line != -1:
            if not self.fileName:
                buf.append("line ")
            buf.append(str(self.line))
            if self.column != -1:
                buf.append(":" + str(self.column))
            buf.append(":")
        buf.append(" ")
        return str('').join(buf)

    __repr__ = __str__


class NoViableAltException(RecognitionException):

    def __init__(self, *args):
        RecognitionException.__init__(self, *args)
        self.token = None
        self.node  = None
        if isinstance(args[0],AST):
            self.node = args[0]
        elif isinstance(args[0],Token):
            self.token = args[0]
        else:
            raise TypeError("NoViableAltException requires Token or AST argument")

    def __str__(self):
        if self.token:
            line = self.token.getLine()
            col  = self.token.getColumn()
            text = self.token.getText()
            return "unexpected symbol at line %s (column %s): \"%s\"" % (line,col,text)
        if self.node == ASTNULL:
            return "unexpected end of subtree"
        assert self.node
        ### hackish, we assume that an AST contains method getText
        return "unexpected node: %s" % (self.node.getText())

    __repr__ = __str__


class NoViableAltForCharException(RecognitionException):

    def __init__(self, *args):
        self.foundChar = None
        if len(args) == 2:
            self.foundChar = args[0]
            scanner = args[1]
            RecognitionException.__init__(self, "NoViableAlt",
                                          scanner.getFilename(),
                                          scanner.getLine(),
                                          scanner.getColumn())
        elif len(args) == 4:
            self.foundChar = args[0]
            fileName = args[1]
            line = args[2]
            column = args[3]
            RecognitionException.__init__(self, "NoViableAlt",
                                          fileName, line, column)
        else:
            RecognitionException.__init__(self, "NoViableAlt",
                                          '', -1, -1)

    def __str__(self):
        mesg = "unexpected char: "
        if self.foundChar >= ' ' and self.foundChar <= '~':
            mesg += "'" + self.foundChar + "'"
        elif self.foundChar:
            mesg += "0x" + hex(ord(self.foundChar)).upper()[2:]
        else:
            mesg += "<None>"
        return mesg

    __repr__ = __str__


class SemanticException(RecognitionException):

    def __init__(self, *args):
        RecognitionException.__init__(self, *args)


class MismatchedCharException(RecognitionException):

    NONE = 0
    CHAR = 1
    NOT_CHAR = 2
    RANGE = 3
    NOT_RANGE = 4
    SET = 5
    NOT_SET = 6

    def __init__(self, *args):
        self.args = args
        if len(args) == 5:
            # Expected range / not range
            if args[3]:
                self.mismatchType = MismatchedCharException.NOT_RANGE
            else:
                self.mismatchType = MismatchedCharException.RANGE
            self.foundChar = args[0]
            self.expecting = args[1]
            self.upper = args[2]
            self.scanner = args[4]
            RecognitionException.__init__(self, "Mismatched char range",
                                          self.scanner.getFilename(),
                                          self.scanner.getLine(),
                                          self.scanner.getColumn())
        elif len(args) == 4 and is_string_type(args[1]):
            # Expected char / not char
            if args[2]:
                self.mismatchType = MismatchedCharException.NOT_CHAR
            else:
                self.mismatchType = MismatchedCharException.CHAR
            self.foundChar = args[0]
            self.expecting = args[1]
            self.scanner = args[3]
            RecognitionException.__init__(self, "Mismatched char",
                                          self.scanner.getFilename(),
                                          self.scanner.getLine(),
                                          self.scanner.getColumn())
        elif len(args) == 4 and isinstance(args[1], BitSet):
            # Expected BitSet / not BitSet
            if args[2]:
                self.mismatchType = MismatchedCharException.NOT_SET
            else:
                self.mismatchType = MismatchedCharException.SET
            self.foundChar = args[0]
            self.set = args[1]
            self.scanner = args[3]
            RecognitionException.__init__(self, "Mismatched char set",
                                          self.scanner.getFilename(),
                                          self.scanner.getLine(),
                                          self.scanner.getColumn())
        else:
            self.mismatchType = MismatchedCharException.NONE
            RecognitionException.__init__(self, "Mismatched char")

    ## Append a char to the msg buffer.  If special,
    #  then show escaped version
    #
    def appendCharName(self, sb, c):
        if not c or c == 65535:
            # 65535 = (char) -1 = EOF
            sb.append("'<EOF>'")
        elif c == '\n':
            sb.append("'\\n'")
        elif c == '\r':
            sb.append("'\\r'");
        elif c == '\t':
            sb.append("'\\t'")
        else:
            sb.append('\'' + c + '\'')

    ##
    # Returns an error message with line number/column information
    #
    def __str__(self):
        sb = ['']
        sb.append(RecognitionException.__str__(self))

        if self.mismatchType == MismatchedCharException.CHAR:
            sb.append("expecting ")
            self.appendCharName(sb, self.expecting)
            sb.append(", found ")
            self.appendCharName(sb, self.foundChar)
        elif self.mismatchType == MismatchedCharException.NOT_CHAR:
            sb.append("expecting anything but '")
            self.appendCharName(sb, self.expecting)
            sb.append("'; got it anyway")
        elif self.mismatchType in [MismatchedCharException.RANGE, MismatchedCharException.NOT_RANGE]:
            sb.append("expecting char ")
            if self.mismatchType == MismatchedCharException.NOT_RANGE:
                sb.append("NOT ")
            sb.append("in range: ")
            appendCharName(sb, self.expecting)
            sb.append("..")
            appendCharName(sb, self.upper)
            sb.append(", found ")
            appendCharName(sb, self.foundChar)
        elif self.mismatchType in [MismatchedCharException.SET, MismatchedCharException.NOT_SET]:
            sb.append("expecting ")
            if self.mismatchType == MismatchedCharException.NOT_SET:
                sb.append("NOT ")
            sb.append("one of (")
            for i in range(len(self.set)):
                self.appendCharName(sb, self.set[i])
            sb.append("), found ")
            self.appendCharName(sb, self.foundChar)

        return str().join(sb).strip()

    __repr__ = __str__


class MismatchedTokenException(RecognitionException):

    NONE = 0
    TOKEN = 1
    NOT_TOKEN = 2
    RANGE = 3
    NOT_RANGE = 4
    SET = 5
    NOT_SET = 6

    def __init__(self, *args):
        self.args =  args
        self.tokenNames = []
        self.token = None
        self.tokenText = ''
        self.node =  None
        if len(args) == 6:
            # Expected range / not range
            if args[3]:
                self.mismatchType = MismatchedTokenException.NOT_RANGE
            else:
                self.mismatchType = MismatchedTokenException.RANGE
            self.tokenNames = args[0]
            self.expecting = args[2]
            self.upper = args[3]
            self.fileName = args[5]

        elif len(args) == 4 and isinstance(args[2], int):
            # Expected token / not token
            if args[3]:
                self.mismatchType = MismatchedTokenException.NOT_TOKEN
            else:
                self.mismatchType = MismatchedTokenException.TOKEN
            self.tokenNames = args[0]
            self.expecting = args[2]

        elif len(args) == 4 and isinstance(args[2], BitSet):
            # Expected BitSet / not BitSet
            if args[3]:
                self.mismatchType = MismatchedTokenException.NOT_SET
            else:
                self.mismatchType = MismatchedTokenException.SET
            self.tokenNames = args[0]
            self.set = args[2]

        else:
            self.mismatchType = MismatchedTokenException.NONE
            RecognitionException.__init__(self, "Mismatched Token: expecting any AST node", "<AST>", -1, -1)

        if len(args) >= 2:
            if isinstance(args[1],Token):
                self.token = args[1]
                self.tokenText = self.token.getText()
                RecognitionException.__init__(self, "Mismatched Token",
                                              self.fileName,
                                              self.token.getLine(),
                                              self.token.getColumn())
            elif isinstance(args[1],AST):
                self.node = args[1]
                self.tokenText = str(self.node)
                RecognitionException.__init__(self, "Mismatched Token",
                                              "<AST>",
                                              self.node.getLine(),
                                              self.node.getColumn())
            else:
                self.tokenText = "<empty tree>"
                RecognitionException.__init__(self, "Mismatched Token",
                                              "<AST>", -1, -1)

    def appendTokenName(self, sb, tokenType):
        if tokenType == INVALID_TYPE:
            sb.append("<Set of tokens>")
        elif tokenType < 0 or tokenType >= len(self.tokenNames):
            sb.append("<" + str(tokenType) + ">")
        else:
            sb.append(self.tokenNames[tokenType])

    ##
    # Returns an error message with line number/column information
    #
    def __str__(self):
        sb = ['']
        sb.append(RecognitionException.__str__(self))

        if self.mismatchType == MismatchedTokenException.TOKEN:
            sb.append("expecting ")
            self.appendTokenName(sb, self.expecting)
            sb.append(", found " + self.tokenText)
        elif self.mismatchType == MismatchedTokenException.NOT_TOKEN:
            sb.append("expecting anything but '")
            self.appendTokenName(sb, self.expecting)
            sb.append("'; got it anyway")
        elif self.mismatchType in [MismatchedTokenException.RANGE, MismatchedTokenException.NOT_RANGE]:
            sb.append("expecting token ")
            if self.mismatchType == MismatchedTokenException.NOT_RANGE:
                sb.append("NOT ")
            sb.append("in range: ")
            appendTokenName(sb, self.expecting)
            sb.append("..")
            appendTokenName(sb, self.upper)
            sb.append(", found " + self.tokenText)
        elif self.mismatchType in [MismatchedTokenException.SET, MismatchedTokenException.NOT_SET]:
            sb.append("expecting ")
            if self.mismatchType == MismatchedTokenException.NOT_SET:
                sb.append("NOT ")
            sb.append("one of (")
            for i in range(len(self.set)):
                self.appendTokenName(sb, self.set[i])
            sb.append("), found " + self.tokenText)

        return str().join(sb).strip()

    __repr__ = __str__


class TokenStreamException(ANTLRException):

    def __init__(self, *args):
        ANTLRException.__init__(self, *args)


# Wraps an Exception in a TokenStreamException
class TokenStreamIOException(TokenStreamException):

    def __init__(self, *args):
        if args and isinstance(args[0], Exception):
            io = args[0]
            TokenStreamException.__init__(self, str(io))
            self.io = io
        else:
            TokenStreamException.__init__(self, *args)
            self.io = self


# Wraps a RecognitionException in a TokenStreamException
class TokenStreamRecognitionException(TokenStreamException):

    def __init__(self, *args):
        if args and isinstance(args[0], RecognitionException):
            recog = args[0]
            TokenStreamException.__init__(self, str(recog))
            self.recog = recog
        else:
            raise TypeError("TokenStreamRecognitionException requires RecognitionException argument")

    def __str__(self):
        return str(self.recog)

    __repr__ = __str__


class TokenStreamRetryException(TokenStreamException):

    def __init__(self, *args):
        TokenStreamException.__init__(self, *args)


class CharStreamException(ANTLRException):

    def __init__(self, *args):
        ANTLRException.__init__(self, *args)


# Wraps an Exception in a CharStreamException
class CharStreamIOException(CharStreamException):

    def __init__(self, *args):
        if args and isinstance(args[0], Exception):
            io = args[0]
            CharStreamException.__init__(self, str(io))
            self.io = io
        else:
            CharStreamException.__init__(self, *args)
            self.io = self


class TryAgain(Exception):
    pass


###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                       Token                                    ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class Token(object):
    SKIP                = -1
    INVALID_TYPE        = 0
    EOF_TYPE            = 1
    EOF                 = 1
    NULL_TREE_LOOKAHEAD = 3
    MIN_USER_TYPE       = 4

    def __init__(self,**argv):
        try:
            self.type = argv['type']
        except:
            self.type = INVALID_TYPE
        try:
            self.text = argv['text']
        except:
            self.text = "<no text>"

    def isEOF(self):
        return (self.type == EOF_TYPE)

    def getColumn(self):
        return 0

    def getLine(self):
        return 0

    def getFilename(self):
        return None

    def setFilename(self,name):
        return self

    def getText(self):
        return "<no text>"

    def setText(self,text):
        if is_string_type(text):
            pass
        else:
            raise TypeError("Token.setText requires string argument")
        return self

    def setColumn(self,column):
        return self

    def setLine(self,line):
        return self

    def getType(self):
        return self.type

    def setType(self,type):
        if isinstance(type,int):
            self.type = type
        else:
            raise TypeError("Token.setType requires integer argument")
        return self

    def toString(self):
        ## not optimal
        type_ = self.type
        if type_ == 3:
            tval = 'NULL_TREE_LOOKAHEAD'
        elif type_ == 1:
            tval = 'EOF_TYPE'
        elif type_ == 0:
            tval = 'INVALID_TYPE'
        elif type_ == -1:
            tval = 'SKIP'
        else:
            tval = type_
        return '["%s",<%s>]' % (self.getText(),tval)

    __str__ = toString
    __repr__ = toString

### static attribute ..
Token.badToken = Token( type=INVALID_TYPE, text="<no text>")

if __name__ == "__main__":
    print "testing .."
    T = Token.badToken
    print T

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                       CommonToken                              ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class CommonToken(Token):

    def __init__(self,**argv):
        Token.__init__(self,**argv)
        self.line = 0
        self.col  = 0
        try:
            self.line = argv['line']
        except:
            pass
        try:
            self.col = argv['col']
        except:
            pass

    def getLine(self):
        return self.line

    def getText(self):
        return self.text

    def getColumn(self):
        return self.col

    def setLine(self,line):
        self.line = line
        return self

    def setText(self,text):
        self.text = text
        return self

    def setColumn(self,col):
        self.col = col
        return self

    def toString(self):
        ## not optimal
        type_ = self.type
        if type_ == 3:
            tval = 'NULL_TREE_LOOKAHEAD'
        elif type_ == 1:
            tval = 'EOF_TYPE'
        elif type_ == 0:
            tval = 'INVALID_TYPE'
        elif type_ == -1:
            tval = 'SKIP'
        else:
            tval = type_
        d = {
           'text' : self.text,
           'type' : tval,
           'line' : self.line,
           'colm' : self.col
           }

        fmt = '["%(text)s",<%(type)s>,line=%(line)s,col=%(colm)s]'
        return fmt % d

    __str__ = toString
    __repr__ = toString


if __name__ == '__main__' :
    T = CommonToken()
    print T
    T = CommonToken(col=15,line=1,text="some text", type=5)
    print T
    T = CommonToken()
    T.setLine(1).setColumn(15).setText("some text").setType(5)
    print T
    print T.getLine()
    print T.getColumn()
    print T.getText()
    print T.getType()

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                    CommonHiddenStreamToken                     ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class CommonHiddenStreamToken(CommonToken):
    def __init__(self,*args):
        CommonToken.__init__(self,*args)
        self.hiddenBefore = None
        self.hiddenAfter  = None

    def getHiddenAfter(self):
        return self.hiddenAfter

    def getHiddenBefore(self):
        return self.hiddenBefore

    def setHiddenAfter(self,t):
        self.hiddenAfter = t

    def setHiddenBefore(self, t):
        self.hiddenBefore = t

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                       Queue                                    ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

## Shall be a circular buffer on tokens ..
class Queue(object):

    def __init__(self):
        self.buffer = [] # empty list

    def append(self,item):
        self.buffer.append(item)

    def elementAt(self,index):
        return self.buffer[index]

    def reset(self):
        self.buffer = []

    def removeFirst(self):
        self.buffer.pop(0)

    def length(self):
        return len(self.buffer)

    def __str__(self):
        return str(self.buffer)

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                       InputBuffer                              ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class InputBuffer(object):
    def __init__(self):
        self.nMarkers = 0
        self.markerOffset = 0
        self.numToConsume = 0
        self.queue = Queue()

    def __str__(self):
        return "(%s,%s,%s,%s)" % (
           self.nMarkers,
           self.markerOffset,
           self.numToConsume,
           self.queue)

    def __repr__(self):
        return str(self)

    def commit(self):
        self.nMarkers -= 1

    def consume(self) :
        self.numToConsume += 1

    ## probably better to return a list of items
    ## because of unicode. Or return a unicode
    ## string ..
    def getLAChars(self) :
        i = self.markerOffset
        n = self.queue.length()
        s = ''
        while i<n:
            s += self.queue.elementAt(i)
        return s

    ## probably better to return a list of items
    ## because of unicode chars
    def getMarkedChars(self) :
        s = ''
        i = 0
        n = self.markerOffset
        while i<n:
            s += self.queue.elementAt(i)
        return s

    def isMarked(self) :
        return self.nMarkers != 0

    def fill(self,k):
        ### abstract method
        raise NotImplementedError()

    def LA(self,k) :
        self.fill(k)
        return self.queue.elementAt(self.markerOffset + k - 1)

    def mark(self) :
        self.syncConsume()
        self.nMarkers += 1
        return self.markerOffset

    def rewind(self,mark) :
        self.syncConsume()
        self.markerOffset = mark
        self.nMarkers -= 1

    def reset(self) :
        self.nMarkers = 0
        self.markerOffset = 0
        self.numToConsume = 0
        self.queue.reset()

    def syncConsume(self) :
        while self.numToConsume > 0:
            if self.nMarkers > 0:
                # guess mode -- leave leading characters and bump offset.
                self.markerOffset += 1
            else:
                # normal mode -- remove first character
                self.queue.removeFirst()
            self.numToConsume -= 1

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                       CharBuffer                               ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class CharBuffer(InputBuffer):
    def __init__(self,reader):
        ##assert isinstance(reader,file)
        super(CharBuffer,self).__init__()
        ## a reader is supposed to be anything that has
        ## a method 'read(int)'.
        self.input = reader

    def __str__(self):
        base = super(CharBuffer,self).__str__()
        return "CharBuffer{%s,%s" % (base,str(input))

    def fill(self,amount):
        try:
            self.syncConsume()
            while self.queue.length() < (amount + self.markerOffset) :
                ## retrieve just one char - what happend at end
                ## of input?
                c = self.input.read(1)
                ### python's behaviour is to return the empty string  on
                ### EOF, ie. no exception whatsoever is thrown. An empty
                ### python  string  has  the  nice feature that it is of
                ### type 'str' and  "not ''" would return true. Contrary,
                ### one can't  do  this: '' in 'abc'. This should return
                ### false,  but all we  get  is  then  a TypeError as an
                ### empty string is not a character.

                ### Let's assure then that we have either seen a
                ### character or an empty string (EOF).
                assert len(c) == 0 or len(c) == 1

                ### And it shall be of type string (ASCII or UNICODE).
                assert is_string_type(c)

                ### Just append EOF char to buffer. Note that buffer may
                ### contain then just more than one EOF char ..

                ### use unicode chars instead of ASCII ..
                self.queue.append(c)
        except Exception,e:
            raise CharStreamIOException(e)
        ##except: # (mk) Cannot happen ...
            ##error ("unexpected exception caught ..")
            ##assert 0

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                       LexerSharedInputState                    ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class LexerSharedInputState(object):
    def __init__(self,ibuf):
        assert isinstance(ibuf,InputBuffer)
        self.input = ibuf
        self.column = 1
        self.line = 1
        self.tokenStartColumn = 1
        self.tokenStartLine = 1
        self.guessing = 0
        self.filename = None

    def reset(self):
        self.column = 1
        self.line = 1
        self.tokenStartColumn = 1
        self.tokenStartLine = 1
        self.guessing = 0
        self.filename = None
        self.input.reset()

    def LA(self,k):
        return self.input.LA(k)

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                    TokenStream                                 ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class TokenStream(object):
    def nextToken(self):
        pass

    def __iter__(self):
        return TokenStreamIterator(self)

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                    TokenStreamIterator                                 ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class TokenStreamIterator(object):
    def __init__(self,inst):
        if isinstance(inst,TokenStream):
            self.inst = inst
            return
        raise TypeError("TokenStreamIterator requires TokenStream object")

    def next(self):
        assert self.inst
        item = self.inst.nextToken()
        if not item or item.isEOF():
            raise StopIteration()
        return item

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                    TokenStreamSelector                        ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class TokenStreamSelector(TokenStream):

    def __init__(self):
        self._input = None
        self._stmap = {}
        self._stack = []

    def addInputStream(self,stream,key):
        self._stmap[key] = stream

    def getCurrentStream(self):
        return self._input

    def getStream(self,sname):
        try:
            stream = self._stmap[sname]
        except:
            raise ValueError("TokenStream " + sname + " not found");
        return stream;

    def nextToken(self):
        while 1:
            try:
                return self._input.nextToken()
            except TokenStreamRetryException,r:
                ### just retry "forever"
                pass

    def pop(self):
        stream = self._stack.pop();
        self.select(stream);
        return stream;

    def push(self,arg):
        self._stack.append(self._input);
        self.select(arg)

    def retry(self):
        raise TokenStreamRetryException()

    def select(self,arg):
        if isinstance(arg,TokenStream):
            self._input = arg
            return
        if is_string_type(arg):
            self._input = self.getStream(arg)
            return
        raise TypeError("TokenStreamSelector.select requires " +
                        "TokenStream or string argument")

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                      TokenStreamBasicFilter                    ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class TokenStreamBasicFilter(TokenStream):

    def __init__(self,input):

        self.input = input;
        self.discardMask = BitSet()

    def discard(self,arg):
        if isinstance(arg,int):
            self.discardMask.add(arg)
            return
        if isinstance(arg,BitSet):
            self.discardMark = arg
            return
        raise TypeError("TokenStreamBasicFilter.discard requires" +
                        "integer or BitSet argument")

    def nextToken(self):
        tok = self.input.nextToken()
        while tok and self.discardMask.member(tok.getType()):
            tok = self.input.nextToken()
        return tok

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                      TokenStreamHiddenTokenFilter              ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class TokenStreamHiddenTokenFilter(TokenStreamBasicFilter):

    def __init__(self,input):
        TokenStreamBasicFilter.__init__(self,input)
        self.hideMask = BitSet()
        self.nextMonitoredToken = None
        self.lastHiddenToken = None
        self.firstHidden = None

    def consume(self):
        self.nextMonitoredToken = self.input.nextToken()

    def consumeFirst(self):
        self.consume()

        p = None;
        while self.hideMask.member(self.LA(1).getType()) or \
              self.discardMask.member(self.LA(1).getType()):
            if self.hideMask.member(self.LA(1).getType()):
                if not p:
                    p = self.LA(1)
                else:
                    p.setHiddenAfter(self.LA(1))
                    self.LA(1).setHiddenBefore(p)
                    p = self.LA(1)
                self.lastHiddenToken = p
                if not self.firstHidden:
                    self.firstHidden = p
            self.consume()

    def getDiscardMask(self):
        return self.discardMask

    def getHiddenAfter(self,t):
        return t.getHiddenAfter()

    def getHiddenBefore(self,t):
        return t.getHiddenBefore()

    def getHideMask(self):
        return self.hideMask

    def getInitialHiddenToken(self):
        return self.firstHidden

    def hide(self,m):
        if isinstance(m,int):
            self.hideMask.add(m)
            return
        if isinstance(m.BitMask):
            self.hideMask = m
            return

    def LA(self,i):
        return self.nextMonitoredToken

    def nextToken(self):
        if not self.LA(1):
            self.consumeFirst()

        monitored = self.LA(1)

        monitored.setHiddenBefore(self.lastHiddenToken)
        self.lastHiddenToken = None

        self.consume()
        p = monitored

        while self.hideMask.member(self.LA(1).getType()) or \
              self.discardMask.member(self.LA(1).getType()):
            if self.hideMask.member(self.LA(1).getType()):
                p.setHiddenAfter(self.LA(1))
                if p != monitored:
                    self.LA(1).setHiddenBefore(p)
                p = self.lastHiddenToken = self.LA(1)
            self.consume()
        return monitored

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                       StringBuffer                             ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class StringBuffer:
    def __init__(self,string=None):
        if string:
            self.text = list(string)
        else:
            self.text = []

    def setLength(self,sz):
        if not sz :
            self.text = []
            return
        assert sz>0
        if sz >= self.length():
            return
        ### just reset to empty buffer
        self.text = self.text[0:sz]

    def length(self):
        return len(self.text)

    def append(self,c):
        self.text.append(c)

    ### return buffer as string. Arg 'a' is  used  as index
    ## into the buffer and 2nd argument shall be the length.
    ## If 2nd args is absent, we return chars till end of
    ## buffer starting with 'a'.
    def getString(self,a=None,length=None):
        if not a :
            a = 0
        assert a>=0
        if a>= len(self.text) :
            return ""

        if not length:
            ## no second argument
            L = self.text[a:]
        else:
            assert (a+length) <= len(self.text)
            b = a + length
            L = self.text[a:b]
        s = ""
        for x in L : s += x
        return s

    toString = getString ## alias

    def __str__(self):
        return str(self.text)

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                       Reader                                   ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

## When reading Japanese chars, it happens that a stream returns a
## 'char' of length 2. This looks like  a  bug  in the appropriate
## codecs - but I'm  rather  unsure about this. Anyway, if this is
## the case, I'm going to  split  this string into a list of chars
## and put them  on  hold, ie. on a  buffer. Next time when called
## we read from buffer until buffer is empty.
## wh: nov, 25th -> problem does not appear in Python 2.4.0.c1.

class Reader(object):
    def __init__(self,stream):
        self.cin = stream
        self.buf = []

    def read(self,num):
        assert num==1

        if len(self.buf):
            return self.buf.pop()

        ## Read a char - this may return a string.
        ## Is this a bug in codecs/Python?
        c = self.cin.read(1)

        if not c or len(c)==1:
            return c

        L = list(c)
        L.reverse()
        for x in L:
            self.buf.append(x)

        ## read one char ..
        return self.read(1)

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                       CharScanner                              ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class CharScanner(TokenStream):
    ## class members
    NO_CHAR = 0
    EOF_CHAR = ''  ### EOF shall be the empty string.

    def __init__(self, *argv, **kwargs):
        super(CharScanner, self).__init__()
        self.saveConsumedInput = True
        self.tokenClass = None
        self.caseSensitive = True
        self.caseSensitiveLiterals = True
        self.literals = None
        self.tabsize = 8
        self._returnToken = None
        self.commitToPath = False
        self.traceDepth = 0
        self.text = StringBuffer()
        self.hashString = hash(self)
        self.setTokenObjectClass(CommonToken)
        self.setInput(*argv)

    def __iter__(self):
        return CharScannerIterator(self)

    def setInput(self,*argv):
        ## case 1:
        ## if there's no arg we default to read from
        ## standard input
        if not argv:
            import sys
            self.setInput(sys.stdin)
            return

        ## get 1st argument
        arg1 = argv[0]

        ## case 2:
        ## if arg1 is a string,  we assume it's a file name
        ## and  open  a  stream  using 2nd argument as open
        ## mode. If there's no 2nd argument we fall back to
        ## mode '+rb'.
        if is_string_type(arg1):
            f = open(arg1,"rb")
            self.setInput(f)
            self.setFilename(arg1)
            return

        ## case 3:
        ## if arg1 is a file we wrap it by a char buffer (
        ## some additional checks?? No, can't do this in
        ## general).
        if isinstance(arg1,file):
            self.setInput(CharBuffer(arg1))
            return

        ## case 4:
        ## if arg1 is of type SharedLexerInputState we use
        ## argument as is.
        if isinstance(arg1,LexerSharedInputState):
            self.inputState = arg1
            return

        ## case 5:
        ## check whether argument type is of type input
        ## buffer. If so create a SharedLexerInputState and
        ## go ahead.
        if isinstance(arg1,InputBuffer):
            self.setInput(LexerSharedInputState(arg1))
            return

        ## case 6:
        ## check whether argument type has a method read(int)
        ## If so create CharBuffer ...
        try:
            if arg1.read:
                rd = Reader(arg1)
                cb = CharBuffer(rd)
                ss = LexerSharedInputState(cb)
                self.inputState = ss
            return
        except:
            pass

        ## case 7:
        ## raise wrong argument exception
        raise TypeError(argv)

    def setTabSize(self,size) :
        self.tabsize = size

    def getTabSize(self) :
        return self.tabsize

    def setCaseSensitive(self,t) :
        self.caseSensitive = t

    def setCommitToPath(self,commit) :
        self.commitToPath = commit

    def setFilename(self,f) :
        self.inputState.filename = f

    def setLine(self,line) :
        self.inputState.line = line

    def setText(self,s) :
        self.resetText()
        self.text.append(s)

    def getCaseSensitive(self) :
        return self.caseSensitive

    def getCaseSensitiveLiterals(self) :
        return self.caseSensitiveLiterals

    def getColumn(self) :
        return self.inputState.column

    def setColumn(self,c) :
        self.inputState.column = c

    def getCommitToPath(self) :
        return self.commitToPath

    def getFilename(self) :
        return self.inputState.filename

    def getInputBuffer(self) :
        return self.inputState.input

    def getInputState(self) :
        return self.inputState

    def setInputState(self,state) :
        assert isinstance(state,LexerSharedInputState)
        self.inputState = state

    def getLine(self) :
        return self.inputState.line

    def getText(self) :
        return str(self.text)

    def getTokenObject(self) :
        return self._returnToken

    def LA(self,i) :
        c = self.inputState.input.LA(i)
        if not self.caseSensitive:
            ### E0006
            c = c.__class__.lower(c)
        return c

    def makeToken(self,type) :
        try:
            ## dynamically load a class
            assert self.tokenClass
            tok = self.tokenClass()
            tok.setType(type)
            tok.setColumn(self.inputState.tokenStartColumn)
            tok.setLine(self.inputState.tokenStartLine)
            return tok
        except:
            self.panic("unable to create new token")
        return Token.badToken

    def mark(self) :
        return self.inputState.input.mark()

    def _match_bitset(self,b) :
        if b.member(self.LA(1)):
            self.consume()
        else:
            raise MismatchedCharException(self.LA(1), b, False, self)

    def _match_string(self,s) :
        for c in s:
            if self.LA(1) == c:
                self.consume()
            else:
                raise MismatchedCharException(self.LA(1), c, False, self)

    def match(self,item):
        if is_string_type(item):
            return self._match_string(item)
        else:
            return self._match_bitset(item)

    def matchNot(self,c) :
        if self.LA(1) != c:
            self.consume()
        else:
            raise MismatchedCharException(self.LA(1), c, True, self)

    def matchRange(self,c1,c2) :
        if self.LA(1) < c1 or self.LA(1) > c2 :
            raise MismatchedCharException(self.LA(1), c1, c2, False, self)
        else:
            self.consume()

    def newline(self) :
        self.inputState.line += 1
        self.inputState.column = 1

    def tab(self) :
        c = self.getColumn()
        nc = ( ((c-1)/self.tabsize) + 1) * self.tabsize + 1
        self.setColumn(nc)

    def panic(self,s='') :
        print "CharScanner: panic: " + s
        sys.exit(1)

    def reportError(self,ex) :
        print ex

    def reportError(self,s) :
        if not self.getFilename():
            print "error: " + str(s)
        else:
            print self.getFilename() + ": error: " + str(s)

    def reportWarning(self,s) :
        if not self.getFilename():
            print "warning: " + str(s)
        else:
            print self.getFilename() + ": warning: " + str(s)

    def resetText(self) :
        self.text.setLength(0)
        self.inputState.tokenStartColumn = self.inputState.column
        self.inputState.tokenStartLine = self.inputState.line

    def rewind(self,pos) :
        self.inputState.input.rewind(pos)

    def setTokenObjectClass(self,cl):
        self.tokenClass = cl

    def testForLiteral(self,token):
        if not token:
            return
        assert isinstance(token,Token)

        _type = token.getType()

        ## special tokens can't be literals
        if _type in [SKIP,INVALID_TYPE,EOF_TYPE,NULL_TREE_LOOKAHEAD] :
            return

        _text = token.getText()
        if not _text:
            return

        assert is_string_type(_text)
        _type = self.testLiteralsTable(_text,_type)
        token.setType(_type)
        return _type

    def testLiteralsTable(self,*args):
        if is_string_type(args[0]):
            s = args[0]
            i = args[1]
        else:
            s = self.text.getString()
            i = args[0]

        ## check whether integer has been given
        if not isinstance(i,int):
            assert isinstance(i,int)

        ## check whether we have a dict
        assert isinstance(self.literals,dict)
        try:
            ## E0010
            if not self.caseSensitiveLiterals:
                s = s.__class__.lower(s)
            i = self.literals[s]
        except:
            pass
        return i

    def toLower(self,c):
        return c.__class__.lower()

    def traceIndent(self):
        print ' ' * self.traceDepth

    def traceIn(self,rname):
        self.traceDepth += 1
        self.traceIndent()
        print "> lexer %s c== %s" % (rname,self.LA(1))

    def traceOut(self,rname):
        self.traceIndent()
        print "< lexer %s c== %s" % (rname,self.LA(1))
        self.traceDepth -= 1

    def uponEOF(self):
        pass

    def append(self,c):
        if self.saveConsumedInput :
            self.text.append(c)

    def commit(self):
        self.inputState.input.commit()

    def consume(self):
        if not self.inputState.guessing:
            c = self.LA(1)
            if self.caseSensitive:
                self.append(c)
            else:
                # use input.LA(), not LA(), to get original case
                # CharScanner.LA() would toLower it.
                c =  self.inputState.input.LA(1)
                self.append(c)

            if c and c in "\t":
                self.tab()
            else:
                self.inputState.column += 1
        self.inputState.input.consume()

    ## Consume chars until one matches the given char
    def consumeUntil_char(self,c):
        while self.LA(1) != EOF_CHAR and self.LA(1) != c:
            self.consume()

    ## Consume chars until one matches the given set
    def consumeUntil_bitset(self,bitset):
        while self.LA(1) != EOF_CHAR and not self.set.member(self.LA(1)):
            self.consume()

    ### If symbol seen is EOF then generate and set token, otherwise
    ### throw exception.
    def default(self,la1):
        if not la1 :
            self.uponEOF()
            self._returnToken = self.makeToken(EOF_TYPE)
        else:
            self.raise_NoViableAlt(la1)

    def filterdefault(self,la1,*args):
        if not la1:
            self.uponEOF()
            self._returnToken = self.makeToken(EOF_TYPE)
            return

        if not args:
            self.consume()
            raise TryAgain()
        else:
            ### apply filter object
            self.commit();
            try:
                func=args[0]
                args=args[1:]
                apply(func,args)
            except RecognitionException, e:
                ## catastrophic failure
                self.reportError(e);
                self.consume();
            raise TryAgain()

    def raise_NoViableAlt(self,la1=None):
        if not la1: la1 = self.LA(1)
        fname = self.getFilename()
        line  = self.getLine()
        col   = self.getColumn()
        raise NoViableAltForCharException(la1,fname,line,col)

    def set_return_token(self,_create,_token,_ttype,_offset):
        if _create and not _token and (not _ttype == SKIP):
            string = self.text.getString(_offset)
            _token = self.makeToken(_ttype)
            _token.setText(string)
        self._returnToken = _token
        return _token

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                   CharScannerIterator                          ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class CharScannerIterator:

    def __init__(self,inst):
        if isinstance(inst,CharScanner):
            self.inst = inst
            return
        raise TypeError("CharScannerIterator requires CharScanner object")

    def next(self):
        assert self.inst
        item = self.inst.nextToken()
        if not item or item.isEOF():
            raise StopIteration()
        return item

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                       BitSet                                   ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

### I'm assuming here that a long is 64bits. It appears however, that
### a long is of any size. That means we can use a single long as the
### bitset (!), ie. Python would do almost all the work (TBD).

class BitSet(object):
    BITS     = 64
    NIBBLE   = 4
    LOG_BITS = 6
    MOD_MASK = BITS -1

    def __init__(self,data=None):
        if not data:
            BitSet.__init__(self,[long(0)])
            return
        if isinstance(data,int):
            BitSet.__init__(self,[long(data)])
            return
        if isinstance(data,long):
            BitSet.__init__(self,[data])
            return
        if not isinstance(data,list):
            raise TypeError("BitSet requires integer, long, or " +
                            "list argument")
        for x in data:
            if not isinstance(x,long):
                raise TypeError(self,"List argument item is " +
                                "not a long: %s" % (x))
        self.data = data

    def __str__(self):
        bits = len(self.data) * BitSet.BITS
        s = ""
        for i in xrange(0,bits):
            if self.at(i):
                s += "1"
            else:
                s += "o"
            if not ((i+1) % 10):
                s += '|%s|' % (i+1)
        return s

    def __repr__(self):
        return str(self)

    def member(self,item):
        if not item:
            return False

        if isinstance(item,int):
            return self.at(item)

        if not is_string_type(item):
            raise TypeError(self,"char or unichar expected: %s" % (item))

        ## char is a (unicode) string with at most lenght 1, ie.
        ## a char.

        if len(item) != 1:
            raise TypeError(self,"char expected: %s" % (item))

        ### handle ASCII/UNICODE char
        num = ord(item)

        ### check whether position num is in bitset
        return self.at(num)

    def wordNumber(self,bit):
        return bit >> BitSet.LOG_BITS

    def bitMask(self,bit):
        pos = bit & BitSet.MOD_MASK  ## bit mod BITS
        return (1L << pos)

    def set(self,bit,on=True):
        # grow bitset as required (use with care!)
        i = self.wordNumber(bit)
        mask = self.bitMask(bit)
        if i>=len(self.data):
            d = i - len(self.data) + 1
            for x in xrange(0,d):
                self.data.append(0L)
            assert len(self.data) == i+1
        if on:
            self.data[i] |=  mask
        else:
            self.data[i] &= (~mask)

    ### make add an alias for set
    add = set

    def off(self,bit,off=True):
        self.set(bit,not off)

    def at(self,bit):
        i = self.wordNumber(bit)
        v = self.data[i]
        m = self.bitMask(bit)
        return v & m


###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                      some further funcs                        ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

def illegalarg_ex(func):
    raise ValueError(
       "%s is only valid if parser is built for debugging" %
       (func.func_name))

def runtime_ex(func):
    raise RuntimeException(
       "%s is only valid if parser is built for debugging" %
       (func.func_name))

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                       TokenBuffer                              ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class TokenBuffer(object):
    def __init__(self,stream):
        self.input = stream
        self.nMarkers = 0
        self.markerOffset = 0
        self.numToConsume = 0
        self.queue = Queue()

    def reset(self) :
        self.nMarkers = 0
        self.markerOffset = 0
        self.numToConsume = 0
        self.queue.reset()

    def consume(self) :
        self.numToConsume += 1

    def fill(self, amount):
        self.syncConsume()
        while self.queue.length() < (amount + self.markerOffset):
            self.queue.append(self.input.nextToken())

    def getInput(self):
        return self.input

    def LA(self,k) :
        self.fill(k)
        return self.queue.elementAt(self.markerOffset + k - 1).type

    def LT(self,k) :
        self.fill(k)
        return self.queue.elementAt(self.markerOffset + k - 1)

    def mark(self) :
        self.syncConsume()
        self.nMarkers += 1
        return self.markerOffset

    def rewind(self,mark) :
        self.syncConsume()
        self.markerOffset = mark
        self.nMarkers -= 1

    def syncConsume(self) :
        while self.numToConsume > 0:
            if self.nMarkers > 0:
                # guess mode -- leave leading characters and bump offset.
                self.markerOffset += 1
            else:
                # normal mode -- remove first character
                self.queue.removeFirst()
            self.numToConsume -= 1

    def __str__(self):
        return "(%s,%s,%s,%s,%s)" % (
           self.input,
           self.nMarkers,
           self.markerOffset,
           self.numToConsume,
           self.queue)

    def __repr__(self):
        return str(self)

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                       ParserSharedInputState                   ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class ParserSharedInputState(object):

    def __init__(self):
        self.input = None
        self.reset()

    def reset(self):
        self.guessing = 0
        self.filename = None
        if self.input:
            self.input.reset()

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                       Parser                                   ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class Parser(object):

    def __init__(self, *args, **kwargs):
        self.tokenNames = None
        self.returnAST  = None
        self.astFactory = None
        self.tokenTypeToASTClassMap = {}
        self.ignoreInvalidDebugCalls = False
        self.traceDepth = 0
        if not args:
            self.inputState = ParserSharedInputState()
            return
        arg0 = args[0]
        assert isinstance(arg0,ParserSharedInputState)
        self.inputState = arg0
        return

    def getTokenTypeToASTClassMap(self):
        return self.tokenTypeToASTClassMap


    def addMessageListener(self, l):
        if not self.ignoreInvalidDebugCalls:
            illegalarg_ex(addMessageListener)

    def addParserListener(self,l) :
        if (not self.ignoreInvalidDebugCalls) :
            illegalarg_ex(addParserListener)

    def addParserMatchListener(self, l) :
        if (not self.ignoreInvalidDebugCalls) :
            illegalarg_ex(addParserMatchListener)

    def addParserTokenListener(self, l) :
        if (not self.ignoreInvalidDebugCalls):
            illegalarg_ex(addParserTokenListener)

    def addSemanticPredicateListener(self, l) :
        if (not self.ignoreInvalidDebugCalls):
            illegalarg_ex(addSemanticPredicateListener)

    def addSyntacticPredicateListener(self, l) :
        if (not self.ignoreInvalidDebugCalls):
            illegalarg_ex(addSyntacticPredicateListener)

    def addTraceListener(self, l) :
        if (not self.ignoreInvalidDebugCalls):
            illegalarg_ex(addTraceListener)

    def consume(self):
        raise NotImplementedError()

    def _consumeUntil_type(self,tokenType):
        while self.LA(1) != EOF_TYPE and self.LA(1) != tokenType:
            self.consume()

    def _consumeUntil_bitset(self, set):
        while self.LA(1) != EOF_TYPE and not set.member(self.LA(1)):
            self.consume()

    def consumeUntil(self,arg):
        if isinstance(arg,int):
            self._consumeUntil_type(arg)
        else:
            self._consumeUntil_bitset(arg)

    def defaultDebuggingSetup(self):
        pass

    def getAST(self) :
        return self.returnAST

    def getASTFactory(self) :
        return self.astFactory

    def getFilename(self) :
        return self.inputState.filename

    def getInputState(self) :
        return self.inputState

    def setInputState(self, state) :
        self.inputState = state

    def getTokenName(self,num) :
        return self.tokenNames[num]

    def getTokenNames(self) :
        return self.tokenNames

    def isDebugMode(self) :
        return self.false

    def LA(self, i):
        raise NotImplementedError()

    def LT(self, i):
        raise NotImplementedError()

    def mark(self):
        return self.inputState.input.mark()

    def _match_int(self,t):
        if (self.LA(1) != t):
            raise MismatchedTokenException(
               self.tokenNames, self.LT(1), t, False, self.getFilename())
        else:
            self.consume()

    def _match_set(self, b):
        if (not b.member(self.LA(1))):
            raise MismatchedTokenException(
               self.tokenNames,self.LT(1), b, False, self.getFilename())
        else:
            self.consume()

    def match(self,set) :
        if isinstance(set,int):
            self._match_int(set)
            return
        if isinstance(set,BitSet):
            self._match_set(set)
            return
        raise TypeError("Parser.match requires integer ot BitSet argument")

    def matchNot(self,t):
        if self.LA(1) == t:
            raise MismatchedTokenException(
               tokenNames, self.LT(1), t, True, self.getFilename())
        else:
            self.consume()

    def removeMessageListener(self, l) :
        if (not self.ignoreInvalidDebugCalls):
            runtime_ex(removeMessageListener)

    def removeParserListener(self, l) :
        if (not self.ignoreInvalidDebugCalls):
            runtime_ex(removeParserListener)

    def removeParserMatchListener(self, l) :
        if (not self.ignoreInvalidDebugCalls):
            runtime_ex(removeParserMatchListener)

    def removeParserTokenListener(self, l) :
        if (not self.ignoreInvalidDebugCalls):
            runtime_ex(removeParserTokenListener)

    def removeSemanticPredicateListener(self, l) :
        if (not self.ignoreInvalidDebugCalls):
            runtime_ex(removeSemanticPredicateListener)

    def removeSyntacticPredicateListener(self, l) :
        if (not self.ignoreInvalidDebugCalls):
            runtime_ex(removeSyntacticPredicateListener)

    def removeTraceListener(self, l) :
        if (not self.ignoreInvalidDebugCalls):
            runtime_ex(removeTraceListener)

    def reportError(self,x) :
        fmt = "syntax error:"
        f = self.getFilename()
        if f:
            fmt = ("%s:" % f) + fmt
        if isinstance(x,Token):
            line = x.getColumn()
            col  = x.getLine()
            text = x.getText()
            fmt  = fmt + 'unexpected symbol at line %s (column %s) : "%s"'
            print >>sys.stderr, fmt % (line,col,text)
        else:
            print >>sys.stderr, fmt,str(x)

    def reportWarning(self,s):
        f = self.getFilename()
        if f:
            print "%s:warning: %s" % (f,str(x))
        else:
            print "warning: %s" % (str(x))

    def rewind(self, pos) :
        self.inputState.input.rewind(pos)

    def setASTFactory(self, f) :
        self.astFactory = f

    def setASTNodeClass(self, cl) :
        self.astFactory.setASTNodeType(cl)

    def setASTNodeType(self, nodeType) :
        self.setASTNodeClass(nodeType)

    def setDebugMode(self, debugMode) :
        if (not self.ignoreInvalidDebugCalls):
            runtime_ex(setDebugMode)

    def setFilename(self, f) :
        self.inputState.filename = f

    def setIgnoreInvalidDebugCalls(self, value) :
        self.ignoreInvalidDebugCalls = value

    def setTokenBuffer(self, t) :
        self.inputState.input = t

    def traceIndent(self):
        print " " * self.traceDepth

    def traceIn(self,rname):
        self.traceDepth += 1
        self.trace("> ", rname)

    def traceOut(self,rname):
        self.trace("< ", rname)
        self.traceDepth -= 1

    ### wh: moved from ASTFactory to Parser
    def addASTChild(self,currentAST, child):
        if not child:
            return
        if not currentAST.root:
            currentAST.root = child
        elif not currentAST.child:
            currentAST.root.setFirstChild(child)
        else:
            currentAST.child.setNextSibling(child)
        currentAST.child = child
        currentAST.advanceChildToEnd()

    ### wh: moved from ASTFactory to Parser
    def makeASTRoot(self,currentAST,root) :
        if root:
            ### Add the current root as a child of new root
            root.addChild(currentAST.root)
            ### The new current child is the last sibling of the old root
            currentAST.child = currentAST.root
            currentAST.advanceChildToEnd()
            ### Set the new root
            currentAST.root = root

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                       LLkParser                                ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class LLkParser(Parser):

    def __init__(self, *args, **kwargs):
        try:
            arg1 = args[0]
        except:
            arg1 = 1

        if isinstance(arg1,int):
            super(LLkParser,self).__init__()
            self.k = arg1
            return

        if isinstance(arg1,ParserSharedInputState):
            super(LLkParser,self).__init__(arg1)
            self.set_k(1,*args)
            return

        if isinstance(arg1,TokenBuffer):
            super(LLkParser,self).__init__()
            self.setTokenBuffer(arg1)
            self.set_k(1,*args)
            return

        if isinstance(arg1,TokenStream):
            super(LLkParser,self).__init__()
            tokenBuf = TokenBuffer(arg1)
            self.setTokenBuffer(tokenBuf)
            self.set_k(1,*args)
            return

        ### unknown argument
        raise TypeError("LLkParser requires integer, " +
                        "ParserSharedInputStream or TokenStream argument")

    def consume(self):
        self.inputState.input.consume()

    def LA(self,i):
        return self.inputState.input.LA(i)

    def LT(self,i):
        return self.inputState.input.LT(i)

    def set_k(self,index,*args):
        try:
            self.k = args[index]
        except:
            self.k = 1

    def trace(self,ee,rname):
        print type(self)
        self.traceIndent()
        guess = ""
        if self.inputState.guessing > 0:
            guess = " [guessing]"
        print(ee + rname + guess)
        for i in xrange(1,self.k+1):
            if i != 1:
                print(", ")
            if self.LT(i) :
                v = self.LT(i).getText()
            else:
                v = "null"
            print "LA(%s) == %s" % (i,v)
        print("\n")

    def traceIn(self,rname):
        self.traceDepth += 1;
        self.trace("> ", rname);

    def traceOut(self,rname):
        self.trace("< ", rname);
        self.traceDepth -= 1;

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                    TreeParserSharedInputState                  ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class TreeParserSharedInputState(object):
    def __init__(self):
        self.guessing = 0

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                       TreeParser                               ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class TreeParser(object):

    def __init__(self, *args, **kwargs):
        self.inputState = TreeParserSharedInputState()
        self._retTree   = None
        self.tokenNames = []
        self.returnAST  = None
        self.astFactory = ASTFactory()
        self.traceDepth = 0

    def getAST(self):
        return self.returnAST

    def getASTFactory(self):
        return self.astFactory

    def getTokenName(self,num) :
        return self.tokenNames[num]

    def getTokenNames(self):
        return self.tokenNames

    def match(self,t,set) :
        assert isinstance(set,int) or isinstance(set,BitSet)
        if not t or t == ASTNULL:
            raise MismatchedTokenException(self.getTokenNames(), t,set, False)

        if isinstance(set,int) and t.getType() != set:
            raise MismatchedTokenException(self.getTokenNames(), t,set, False)

        if isinstance(set,BitSet) and not set.member(t.getType):
            raise MismatchedTokenException(self.getTokenNames(), t,set, False)

    def matchNot(self,t, ttype) :
        if not t or (t == ASTNULL) or (t.getType() == ttype):
            raise MismatchedTokenException(getTokenNames(), t, ttype, True)

    def reportError(self,ex):
        print >>sys.stderr,"error:",ex

    def  reportWarning(self, s):
        print "warning:",s

    def setASTFactory(self,f):
        self.astFactory = f

    def setASTNodeType(self,nodeType):
        self.setASTNodeClass(nodeType)

    def setASTNodeClass(self,nodeType):
        self.astFactory.setASTNodeType(nodeType)

    def traceIndent(self):
        print " " * self.traceDepth

    def traceIn(self,rname,t):
        self.traceDepth += 1
        self.traceIndent()
        print("> " + rname + "(" +
              ifelse(t,str(t),"null") + ")" +
              ifelse(self.inputState.guessing>0,"[guessing]",""))

    def traceOut(self,rname,t):
        self.traceIndent()
        print("< " + rname + "(" +
              ifelse(t,str(t),"null") + ")" +
              ifelse(self.inputState.guessing>0,"[guessing]",""))
        self.traceDepth -= 1

    ### wh: moved from ASTFactory to TreeParser
    def addASTChild(self,currentAST, child):
        if not child:
            return
        if not currentAST.root:
            currentAST.root = child
        elif not currentAST.child:
            currentAST.root.setFirstChild(child)
        else:
            currentAST.child.setNextSibling(child)
        currentAST.child = child
        currentAST.advanceChildToEnd()

    ### wh: moved from ASTFactory to TreeParser
    def makeASTRoot(self,currentAST,root):
        if root:
            ### Add the current root as a child of new root
            root.addChild(currentAST.root)
            ### The new current child is the last sibling of the old root
            currentAST.child = currentAST.root
            currentAST.advanceChildToEnd()
            ### Set the new root
            currentAST.root = root

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###               funcs to work on trees                           ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

def rightmost(ast):
    if ast:
        while(ast.right):
            ast = ast.right
    return ast

def cmptree(s,t,partial):
    while(s and t):
        ### as a quick optimization, check roots first.
        if not s.equals(t):
            return False

        ### if roots match, do full list match test on children.
        if not cmptree(s.getFirstChild(),t.getFirstChild(),partial):
            return False

        s = s.getNextSibling()
        t = t.getNextSibling()

    r = ifelse(partial,not t,not s and not t)
    return r

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                          AST                                   ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class AST(object):
    def __init__(self):
        pass

    def addChild(self, c):
        pass

    def equals(self, t):
        return False

    def equalsList(self, t):
        return False

    def equalsListPartial(self, t):
        return False

    def equalsTree(self, t):
        return False

    def equalsTreePartial(self, t):
        return False

    def findAll(self, tree):
        return None

    def findAllPartial(self, subtree):
        return None

    def getFirstChild(self):
        return self

    def getNextSibling(self):
        return self

    def getText(self):
        return ""

    def getType(self):
        return INVALID_TYPE

    def getLine(self):
        return 0

    def getColumn(self):
        return 0

    def getNumberOfChildren(self):
        return 0

    def initialize(self, t, txt):
        pass

    def initialize(self, t):
        pass

    def setFirstChild(self, c):
        pass

    def setNextSibling(self, n):
        pass

    def setText(self, text):
        pass

    def setType(self, ttype):
        pass

    def toString(self):
        self.getText()

    __str__ = toString

    def toStringList(self):
        return self.getText()

    def toStringTree(self):
        return self.getText()

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                       ASTNULLType                              ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

### There is only one instance of this class **/
class ASTNULLType(AST):
    def __init__(self):
        AST.__init__(self)
        pass

    def getText(self):
        return "<ASTNULL>"

    def getType(self):
        return NULL_TREE_LOOKAHEAD


###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                       BaseAST                                  ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class BaseAST(AST):

    verboseStringConversion = False
    tokenNames = None

    def __init__(self):
        self.down  = None ## kid
        self.right = None ## sibling

    def addChild(self,node):
        if node:
            t = rightmost(self.down)
            if t:
                t.right = node
            else:
                assert not self.down
                self.down = node

    def getNumberOfChildren(self):
        t = self.down
        n = 0
        while t:
            n += 1
            t = t.right
        return n

    def doWorkForFindAll(self,v,target,partialMatch):
        sibling = self

        while sibling:
            c1 = partialMatch and sibling.equalsTreePartial(target)
            if c1:
                v.append(sibling)
            else:
                c2 = not partialMatch and sibling.equalsTree(target)
                if c2:
                    v.append(sibling)

            ### regardless of match or not, check any children for matches
            if sibling.getFirstChild():
                sibling.getFirstChild().doWorkForFindAll(v,target,partialMatch)

            sibling = sibling.getNextSibling()

    ### Is node t equal to 'self' in terms of token type and text?
    def equals(self,t):
        if not t:
            return False
        return self.getText() == t.getText() and self.getType() == t.getType()

    ### Is t an exact structural and equals() match of this tree.  The
    ### 'self' reference is considered the start of a sibling list.
    ###
    def equalsList(self, t):
        return cmptree(self, t, partial=False)

    ### Is 't' a subtree of this list?
    ### The siblings of the root are NOT ignored.
    ###
    def equalsListPartial(self,t):
        return cmptree(self,t,partial=True)

    ### Is tree rooted at 'self' equal to 't'?  The siblings
    ### of 'self' are ignored.
    ###
    def equalsTree(self, t):
        return self.equals(t) and \
               cmptree(self.getFirstChild(), t.getFirstChild(), partial=False)

    ### Is 't' a subtree of the tree rooted at 'self'?  The siblings
    ### of 'self' are ignored.
    ###
    def equalsTreePartial(self, t):
        if not t:
            return True
        return self.equals(t) and cmptree(
           self.getFirstChild(), t.getFirstChild(), partial=True)

    ### Walk the tree looking for all exact subtree matches.  Return
    ### an ASTEnumerator that lets the caller walk the list
    ### of subtree roots found herein.
    def findAll(self,target):
        roots = []

        ### the empty tree cannot result in an enumeration
        if not target:
            return None
        # find all matches recursively
        self.doWorkForFindAll(roots, target, False)
        return roots

    ### Walk the tree looking for all subtrees.  Return
    ###  an ASTEnumerator that lets the caller walk the list
    ###  of subtree roots found herein.
    def findAllPartial(self,sub):
        roots = []

        ### the empty tree cannot result in an enumeration
        if not sub:
            return None

        self.doWorkForFindAll(roots, sub, True)  ### find all matches recursively
        return roots

    ### Get the first child of this node None if not children
    def getFirstChild(self):
        return self.down

    ### Get the next sibling in line after this one
    def getNextSibling(self):
        return self.right

    ### Get the token text for this node
    def getText(self):
        return ""

    ### Get the token type for this node
    def getType(self):
        return 0

    def getLine(self):
        return 0

    def getColumn(self):
        return 0

    ### Remove all children */
    def removeChildren(self):
        self.down = None

    def setFirstChild(self,c):
        self.down = c

    def setNextSibling(self, n):
        self.right = n

    ### Set the token text for this node
    def setText(self, text):
        pass

    ### Set the token type for this node
    def setType(self, ttype):
        pass

    ### static
    def setVerboseStringConversion(verbose,names):
        verboseStringConversion = verbose
        tokenNames = names
    setVerboseStringConversion = staticmethod(setVerboseStringConversion)

    ### Return an array of strings that maps token ID to it's text.
    ##  @since 2.7.3
    def getTokenNames():
        return tokenNames

    def toString(self):
        return self.getText()

    ### return tree as lisp string - sibling included
    def toStringList(self):
        ts = self.toStringTree()
        sib = self.getNextSibling()
        if sib:
            ts += sib.toStringList()
        return ts

    __str__ = toStringList

    ### return tree as string - siblings ignored
    def toStringTree(self):
        ts = ""
        kid = self.getFirstChild()
        if kid:
            ts += " ("
        ts += " " + self.toString()
        if kid:
            ts += kid.toStringList()
            ts += " )"
        return ts

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                       CommonAST                                ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

### Common AST node implementation
class CommonAST(BaseAST):
    def __init__(self,token=None):
        super(CommonAST,self).__init__()
        self.ttype = INVALID_TYPE
        self.text  = "<no text>"
        self.line  = 0
        self.column= 0
        self.initialize(token)
        #assert self.text

    ### Get the token text for this node
    def getText(self):
        return self.text

    ### Get the token type for this node
    def getType(self):
        return self.ttype

    ### Get the line for this node
    def getLine(self):
        return self.line

    ### Get the column for this node
    def getColumn(self):
        return self.column

    def initialize(self,*args):
        if not args:
            return

        arg0 = args[0]

        if isinstance(arg0,int):
            arg1 = args[1]
            self.setType(arg0)
            self.setText(arg1)
            return

        if isinstance(arg0,AST) or isinstance(arg0,Token):
            self.setText(arg0.getText())
            self.setType(arg0.getType())
            self.line = arg0.getLine()
            self.column = arg0.getColumn()
            return

    ### Set the token text for this node
    def setText(self,text_):
        assert is_string_type(text_)
        self.text = text_

    ### Set the token type for this node
    def setType(self,ttype_):
        assert isinstance(ttype_,int)
        self.ttype = ttype_

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                     CommonASTWithHiddenTokens                  ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class CommonASTWithHiddenTokens(CommonAST):

    def __init__(self,*args):
        CommonAST.__init__(self,*args)
        self.hiddenBefore = None
        self.hiddenAfter  = None

    def getHiddenAfter(self):
        return self.hiddenAfter

    def getHiddenBefore(self):
        return self.hiddenBefore

    def initialize(self,*args):
        CommonAST.initialize(self,*args)
        if args and isinstance(args[0],Token):
            assert isinstance(args[0],CommonHiddenStreamToken)
            self.hiddenBefore = args[0].getHiddenBefore()
            self.hiddenAfter  = args[0].getHiddenAfter()

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                       ASTPair                                  ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class ASTPair(object):
    def __init__(self):
        self.root = None          ### current root of tree
        self.child = None         ### current child to which siblings are added

    ### Make sure that child is the last sibling */
    def advanceChildToEnd(self):
        if self.child:
            while self.child.getNextSibling():
                self.child = self.child.getNextSibling()

    ### Copy an ASTPair.  Don't call it clone() because we want type-safety */
    def copy(self):
        tmp = ASTPair()
        tmp.root = self.root
        tmp.child = self.child
        return tmp

    def toString(self):
        r = ifelse(not root,"null",self.root.getText())
        c = ifelse(not child,"null",self.child.getText())
        return "[%s,%s]" % (r,c)

    __str__ = toString
    __repr__ = toString


###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                       ASTFactory                               ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class ASTFactory(object):
    def __init__(self,table=None):
        self._class = None
        self._classmap = ifelse(table,table,None)

    def create(self,*args):
        if not args:
            return self.create(INVALID_TYPE)

        arg0 = args[0]
        arg1 = None
        arg2 = None

        try:
            arg1 = args[1]
            arg2 = args[2]
        except:
            pass

        # ctor(int)
        if isinstance(arg0,int) and not arg2:
            ### get class for 'self' type
            c = self.getASTNodeType(arg0)
            t = self.create(c)
            if t:
                t.initialize(arg0, ifelse(arg1,arg1,""))
            return t

        # ctor(int,something)
        if isinstance(arg0,int) and arg2:
            t = self.create(arg2)
            if t:
                t.initialize(arg0,arg1)
            return t

        # ctor(AST)
        if isinstance(arg0,AST):
            t = self.create(arg0.getType())
            if t:
                t.initialize(arg0)
            return t

        # ctor(token)
        if isinstance(arg0,Token) and not arg1:
            ttype = arg0.getType()
            assert isinstance(ttype,int)
            t = self.create(ttype)
            if t:
                t.initialize(arg0)
            return t

        # ctor(token,class)
        if isinstance(arg0,Token) and arg1:
            assert isinstance(arg1,type)
            assert issubclass(arg1,AST)
            # this creates instance of 'arg1' using 'arg0' as
            # argument. Wow, that's magic!
            t = arg1(arg0)
            assert t and isinstance(t,AST)
            return t

        # ctor(class)
        if isinstance(arg0,type):
            ### next statement creates instance of type (!)
            t = arg0()
            assert isinstance(t,AST)
            return t


    def setASTNodeClass(self,className=None):
        if not className:
            return
        assert isinstance(className,type)
        assert issubclass(className,AST)
        self._class = className

    ### kind of misnomer - use setASTNodeClass instead.
    setASTNodeType = setASTNodeClass

    def getASTNodeClass(self):
        return self._class



    def getTokenTypeToASTClassMap(self):
        return self._classmap

    def setTokenTypeToASTClassMap(self,amap):
        self._classmap = amap

    def error(self, e):
        import sys
        print >> sys.stderr, e

    def setTokenTypeASTNodeType(self, tokenType, className):
        """
        Specify a mapping between a token type and a (AST) class.
        """
        if not self._classmap:
            self._classmap = {}

        if not className:
            try:
                del self._classmap[tokenType]
            except:
                pass
        else:
            ### here we should also perform actions to ensure that
            ### a. class can be loaded
            ### b. class is a subclass of AST
            ###
            assert isinstance(className,type)
            assert issubclass(className,AST)  ## a & b
            ### enter the class
            self._classmap[tokenType] = className

    def getASTNodeType(self,tokenType):
        """
        For a given token type return the AST node type. First we
        lookup a mapping table, second we try _class
        and finally we resolve to "antlr.CommonAST".
        """

        # first
        if self._classmap:
            try:
                c = self._classmap[tokenType]
                if c:
                    return c
            except:
                pass
        # second
        if self._class:
            return self._class

        # default
        return CommonAST

    ### methods that have been moved to file scope - just listed
    ### here to be somewhat consistent with original API
    def dup(self,t):
        return antlr.dup(t,self)

    def dupList(self,t):
        return antlr.dupList(t,self)

    def dupTree(self,t):
        return antlr.dupTree(t,self)

    ### methods moved to other classes
    ### 1. makeASTRoot  -> Parser
    ### 2. addASTChild  -> Parser

    ### non-standard: create alias for longish method name
    maptype = setTokenTypeASTNodeType

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###                       ASTVisitor                               ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

class ASTVisitor(object):
    def __init__(self,*args):
        pass

    def visit(self,ast):
        pass

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###
###               static methods and variables                     ###
###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx###

ASTNULL = ASTNULLType()

### wh: moved from ASTFactory as there's nothing ASTFactory-specific
### in this method.
def make(*nodes):
    if not nodes:
        return None

    for i in xrange(0,len(nodes)):
        node = nodes[i]
        if node:
            assert isinstance(node,AST)

    root = nodes[0]
    tail = None
    if root:
        root.setFirstChild(None)

    for i in xrange(1,len(nodes)):
        if not nodes[i]:
            continue
        if not root:
            root = tail = nodes[i]
        elif not tail:
            root.setFirstChild(nodes[i])
            tail = root.getFirstChild()
        else:
            tail.setNextSibling(nodes[i])
            tail = tail.getNextSibling()

        ### Chase tail to last sibling
        while tail.getNextSibling():
            tail = tail.getNextSibling()
    return root

def dup(t,factory):
    if not t:
        return None

    if factory:
        dup_t = factory.create(t.__class__)
    else:
        raise TypeError("dup function requires ASTFactory argument")
    dup_t.initialize(t)
    return dup_t

def dupList(t,factory):
    result = dupTree(t,factory)
    nt = result
    while t:
        ## for each sibling of the root
        t = t.getNextSibling()
        nt.setNextSibling(dupTree(t,factory))
        nt = nt.getNextSibling()
    return result

def dupTree(t,factory):
    result = dup(t,factory)
    if t:
        result.setFirstChild(dupList(t.getFirstChild(),factory))
    return result

###xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
### $Id$

# Local Variables:    ***
# mode: python        ***
# py-indent-offset: 4 ***
# End:                ***

########NEW FILE########
__FILENAME__ = BIFFRecords
# -*- coding: cp1252 -*-
from struct import pack
from UnicodeUtils import upack1, upack2, upack2rt

class SharedStringTable(object):
    _SST_ID = 0x00FC
    _CONTINUE_ID = 0x003C

    def __init__(self, encoding):
        self.encoding = encoding
        self._str_indexes = {}
        self._rt_indexes = {}
        self._tally = []
        self._add_calls = 0
        # Following 3 attrs are used for temporary storage in the
        # get_biff_record() method and methods called by it. The pseudo-
        # initialisation here is for documentation purposes only.
        self._sst_record = None
        self._continues = None
        self._current_piece = None

    def add_str(self, s):
        if self.encoding != 'ascii' and not isinstance(s, unicode):
            s = unicode(s, self.encoding)
        self._add_calls += 1
        if s not in self._str_indexes:
            idx = len(self._str_indexes) + len(self._rt_indexes)
            self._str_indexes[s] = idx
            self._tally.append(1)
        else:
            idx = self._str_indexes[s]
            self._tally[idx] += 1
        return idx
	
    def add_rt(self, rt):
        rtList = []
        for s, xf in rt:
            if self.encoding != 'ascii' and not isinstance(s, unicode):
                s = unicode(s, self.encoding)
            rtList.append((s, xf))
        rt = tuple(rtList)
        self._add_calls += 1
        if rt not in self._rt_indexes:
            idx = len(self._str_indexes) + len(self._rt_indexes)
            self._rt_indexes[rt] = idx
            self._tally.append(1)
        else:
            idx = self._rt_indexes[rt]
            self._tally[idx] += 1
        return idx

    def del_str(self, idx):
        # This is called when we are replacing the contents of a string cell.
        # handles both regular and rt strings
        assert self._tally[idx] > 0
        self._tally[idx] -= 1
        self._add_calls -= 1

    def str_index(self, s):
        return self._str_indexes[s]

    def rt_index(self, rt):
        return self._rt_indexes[rt]

    def get_biff_record(self):
        self._sst_record = ''
        self._continues = [None, None]
        self._current_piece = pack('<II', 0, 0)
        data = [(idx, s) for s, idx in self._str_indexes.iteritems()]
        data.extend([(idx, s) for s, idx in self._rt_indexes.iteritems()])
        data.sort() # in index order
        for idx, s in data:
            if self._tally[idx] == 0:
                s = u''
            if isinstance(s, str) or isinstance(s, unicode):
                self._add_to_sst(s)
            else:
                self._add_rt_to_sst(s)
        del data
        self._new_piece()
        self._continues[0] = pack('<2HII', self._SST_ID, len(self._sst_record), self._add_calls, len(self._str_indexes) + len(self._rt_indexes))
        self._continues[1] = self._sst_record[8:]
        self._sst_record = None
        self._current_piece = None
        result = ''.join(self._continues)
        self._continues = None
        return result


    def _add_to_sst(self, s):
        u_str = upack2(s, self.encoding)

        is_unicode_str = u_str[2] == '\x01'
        if is_unicode_str:
            atom_len = 5 # 2 byte -- len,
                         # 1 byte -- options,
                         # 2 byte -- 1st sym
        else:
            atom_len = 4 # 2 byte -- len,
                         # 1 byte -- options,
                         # 1 byte -- 1st sym

        self._save_atom(u_str[0:atom_len])
        self._save_splitted(u_str[atom_len:], is_unicode_str)
	
    def _add_rt_to_sst(self, rt):
        rt_str, rt_fr = upack2rt(rt, self.encoding)
        is_unicode_str = rt_str[2] == '\x09'
        if is_unicode_str:
            atom_len = 7 # 2 byte -- len,
                         # 1 byte -- options,
                         # 2 byte -- number of rt runs
                         # 2 byte -- 1st sym
        else:
            atom_len = 6 # 2 byte -- len,
                         # 1 byte -- options,
                         # 2 byte -- number of rt runs
                         # 1 byte -- 1st sym
        self._save_atom(rt_str[0:atom_len])
        self._save_splitted(rt_str[atom_len:], is_unicode_str)
        for i in range(0, len(rt_fr), 4):
            self._save_atom(rt_fr[i:i+4])

    def _new_piece(self):
        if self._sst_record == '':
            self._sst_record = self._current_piece
        else:
            curr_piece_len = len(self._current_piece)
            self._continues.append(pack('<2H%ds'%curr_piece_len, self._CONTINUE_ID, curr_piece_len, self._current_piece))
        self._current_piece = ''

    def _save_atom(self, s):
        atom_len = len(s)
        free_space = 0x2020 - len(self._current_piece)
        if free_space < atom_len:
            self._new_piece()
        self._current_piece += s

    def _save_splitted(self, s, is_unicode_str):
        i = 0
        str_len = len(s)
        while i < str_len:
            piece_len = len(self._current_piece)
            free_space = 0x2020 - piece_len
            tail_len = str_len - i
            need_more_space = free_space < tail_len

            if not need_more_space:
                atom_len = tail_len
            else:
                if is_unicode_str:
                    atom_len = free_space & 0xFFFE
                else:
                    atom_len = free_space

            self._current_piece += s[i:i+atom_len]

            if need_more_space:
                self._new_piece()
                if is_unicode_str:
                    self._current_piece += '\x01'
                else:
                    self._current_piece += '\x00'

            i += atom_len


class BiffRecord(object):

    _rec_data = '' # class attribute; child classes need to set this.

    # Sheer waste.
    # def __init__(self):
    #     self._rec_data = ''

    def get_rec_id(self):
        return _REC_ID

    def get_rec_header(self):
        return pack('<2H', self._REC_ID, len(self._rec_data))

    # Not over-ridden by any child classes, never called (except by "get"; see below).
    # def get_rec_data(self):
    #     return self._rec_data

    def get(self):
        # data = self.get_rec_data()
        data = self._rec_data
        if len(data) > 0x2020: # limit for BIFF7/8
            chunks = []
            pos = 0
            while pos < len(data):
                chunk_pos = pos + 0x2020
                chunk = data[pos:chunk_pos]
                chunks.append(chunk)
                pos = chunk_pos
            continues = pack('<2H', self._REC_ID, len(chunks[0])) + chunks[0]
            for chunk in chunks[1:]:
                continues += pack('<2H%ds'%len(chunk), 0x003C, len(chunk), chunk)
                # 0x003C -- CONTINUE record id
            return continues
        else:
            return self.get_rec_header() + data


class Biff8BOFRecord(BiffRecord):
    """
    Offset Size Contents
    0      2    Version, contains 0600H for BIFF8 and BIFF8X
    2      2    Type of the following data:
                  0005H = Workbook globals
                  0006H = Visual Basic module
                  0010H = Worksheet
                  0020H = Chart
                  0040H = Macro sheet
                  0100H = Workspace file
    4      2    Build identifier
    6      2    Build year
    8      4    File history flags
    12     4    Lowest Excel version that can read all records in this file
    """
    _REC_ID      = 0x0809
    # stream types
    BOOK_GLOBAL = 0x0005
    VB_MODULE   = 0x0006
    WORKSHEET   = 0x0010
    CHART       = 0x0020
    MACROSHEET  = 0x0040
    WORKSPACE   = 0x0100

    def __init__(self, rec_type):
        version  = 0x0600
        build    = 0x0DBB
        year     = 0x07CC
        file_hist_flags = 0x00L
        ver_can_read    = 0x06L

        self._rec_data = pack('<4H2I', version, rec_type, build, year, file_hist_flags, ver_can_read)


class InteraceHdrRecord(BiffRecord):
    _REC_ID = 0x00E1

    def __init__(self):
        self._rec_data = pack('BB', 0xB0, 0x04)


class InteraceEndRecord(BiffRecord):
    _REC_ID = 0x00E2

    def __init__(self):
        self._rec_data = ''


class MMSRecord(BiffRecord):
    _REC_ID = 0x00C1

    def __init__(self):
        self._rec_data = pack('<H', 0x00)


class WriteAccessRecord(BiffRecord):
    """
    This record is part of the file protection. It contains the name of the
    user  that  has  saved  the  file. The user name is always stored as an
    equal-sized  string.  All  unused  characters after the name are filled
    with space characters. It is not required to write the mentioned string
    length. Every other length will be accepted too.
    """
    _REC_ID = 0x005C

    def __init__(self, owner):
        uowner = owner[0:0x30]
        uowner_len = len(uowner)
        self._rec_data = pack('%ds%ds' % (uowner_len, 0x70 - uowner_len), uowner, ' '*(0x70 - uowner_len))


class DSFRecord(BiffRecord):
    """
    This  record  specifies  if the file contains an additional BIFF5/BIFF7
    workbook stream.
    Record DSF, BIFF8:
    Offset Size Contents
    0        2     0 = Only the BIFF8 Workbook stream is present
                   1 = Additional BIFF5/BIFF7 Book stream is in the file
    A  double  stream file can be read by Excel 5.0 and Excel 95, and still
    contains  all  new  features  added to BIFF8 (which are left out in the
    BIFF5/BIFF7 Book stream).
    """
    _REC_ID = 0x0161

    def __init__(self):
        self._rec_data = pack('<H', 0x00)


class TabIDRecord(BiffRecord):
    _REC_ID = 0x013D

    def __init__(self, sheetcount):
        for i in range(sheetcount):
            self._rec_data += pack('<H', i+1)


class FnGroupCountRecord(BiffRecord):
    _REC_ID = 0x009C

    def __init__(self):
        self._rec_data = pack('BB', 0x0E, 0x00)


class WindowProtectRecord(BiffRecord):
    """
    This record is part of the worksheet/workbook protection. It determines
    whether  the window configuration of this document is protected. Window
    protection is not active, if this record is omitted.
    """
    _REC_ID = 0x0019

    def __init__(self, wndprotect):
        self._rec_data = pack('<H', wndprotect)


class ObjectProtectRecord(BiffRecord):
    """
    This record is part of the worksheet/workbook protection.
    It determines whether the objects of the current sheet are protected.
    Object protection is not active, if this record is omitted.
    """
    _REC_ID = 0x0063


    def __init__(self, objprotect):
        self._rec_data = pack('<H', objprotect)


class ScenProtectRecord(BiffRecord):
    """
    This record is part of the worksheet/workbook protection. It
    determines whether the scenarios of the current sheet are protected.
    Scenario protection is not active, if this record is omitted.
    """
    _REC_ID = 0x00DD


    def __init__(self, scenprotect):
        self._rec_data = pack('<H', scenprotect)


class ProtectRecord(BiffRecord):
    """
    This  record is part of the worksheet/workbook protection. It specifies
    whether  a  worksheet  or a workbook is protected against modification.
    Protection is not active, if this record is omitted.
    """

    _REC_ID = 0x0012

    def __init__(self, protect):
        self._rec_data = pack('<H', protect)


class PasswordRecord(BiffRecord):
    """
    This record is part of the worksheet/workbook protection. It
    stores a 16-bit hash value, calculated from the worksheet or workbook
    protection password.
    """
    _REC_ID = 0x0013
    def passwd_hash(self, plaintext):
        """
        Based on the algorithm provided by Daniel Rentz of OpenOffice.
        """
        if plaintext == "":
            return 0

        passwd_hash = 0x0000
        for i, char in enumerate(plaintext):
            c = ord(char) << (i + 1)
            low_15 = c & 0x7fff
            high_15 = c & 0x7fff << 15
            high_15 = high_15 >> 15
            c = low_15 | high_15
            passwd_hash ^= c
        passwd_hash ^= len(plaintext)
        passwd_hash ^= 0xCE4B
        return passwd_hash

    def __init__(self, passwd = ""):
        self._rec_data = pack('<H', self.passwd_hash(passwd))


class Prot4RevRecord(BiffRecord):
    _REC_ID = 0x01AF

    def __init__(self):
        self._rec_data = pack('<H', 0x00)


class Prot4RevPassRecord(BiffRecord):
    _REC_ID = 0x01BC

    def __init__(self):
        self._rec_data = pack('<H', 0x00)


class BackupRecord(BiffRecord):
    """
    This  record  contains  a Boolean value determining whether Excel makes
    a backup of the file while saving.
    """
    _REC_ID = 0x0040

    def __init__(self, backup):
        self._rec_data = pack('<H', backup)

class HideObjRecord(BiffRecord):
    """
    This record specifies whether and how to show objects in the workbook.

    Record HIDEOBJ, BIFF3-BIFF8:
    Offset  Size    Contents
    0       2       Viewing mode for objects:
                        0 = Show all objects
                        1 = Show placeholders
                        2 = Do not show objects
    """
    _REC_ID = 0x008D

    def __init__(self):
        self._rec_data = pack('<H', 0x00)



class RefreshAllRecord(BiffRecord):
    """
    """

    _REC_ID = 0x01B7

    def __init__(self):
        self._rec_data = pack('<H', 0x00)


class BookBoolRecord(BiffRecord):
    """
    This record contains a Boolean value determining whether to save values
    linked  from external workbooks (CRN records and XCT records). In BIFF3
    and BIFF4 this option is stored in the WSBOOL record.

    Record BOOKBOOL, BIFF5-BIFF8:

    Offset  Size    Contents
    0       2       0 = Save external linked values;
                    1 = Do not save external linked values
    """

    _REC_ID = 0x00DA

    def __init__(self):
        self._rec_data = pack('<H', 0x00)


class CountryRecord(BiffRecord):
    """
    This   record   stores  two  Windows  country  identifiers.  The  first
    represents  the  user  interface language of the Excel version that has
    saved  the file, and the second represents the system regional settings
    at the time the file was saved.

    Record COUNTRY, BIFF3-BIFF8:

    Offset  Size    Contents
    0       2       Windows country identifier of the user interface language of Excel
    2       2       Windows country identifier of the system regional settings

    The  following  table  shows most of the used country identifiers. Most
    of  these  identifiers  are  equal to the international country calling
    codes.

    1   USA
    2   Canada
    7   Russia
    """

    _REC_ID = 0x008C

    def __init__(self, ui_id, sys_settings_id):
        self._rec_data = pack('<2H', ui_id, sys_settings_id)


class UseSelfsRecord(BiffRecord):
    """
    This  record  specifies if the formulas in the workbook can use natural
    language  formulas.  This  type  of  formula can refer to cells by its
    content or the content of the column or row header cell.

    Record USESELFS, BIFF8:

    Offset  Size    Contents
    0       2       0 = Do not use natural language formulas
                    1 = Use natural language formulas

    """

    _REC_ID = 0x0160

    def __init__(self):
        self._rec_data = pack('<H', 0x01)


class EOFRecord(BiffRecord):
    _REC_ID = 0x000A

    def __init__(self):
        self._rec_data = ''


class DateModeRecord(BiffRecord):
    """
    This  record  specifies  the  base date for displaying date values. All
    dates  are  stored as count of days past this base date. In BIFF2-BIFF4
    this   record  is  part  of  the  Calculation  Settings  Block.
    In BIFF5-BIFF8 it is stored in the Workbook Globals Substream.

    Record DATEMODE, BIFF2-BIFF8:

    Offset  Size    Contents
    0       2       0 = Base is 1899-Dec-31 (the cell = 1 represents 1900-Jan-01)
                    1 = Base is 1904-Jan-01 (the cell = 1 represents 1904-Jan-02)
    """
    _REC_ID = 0x0022

    def __init__(self, from1904):
        if from1904:
            self._rec_data = pack('<H', 1)
        else:
            self._rec_data = pack('<H', 0)


class PrecisionRecord(BiffRecord):
    """
    This record stores if formulas use the real cell values for calculation
    or  the  values  displayed  on  the screen. In BIFF2- BIFF4 this record
    is  part of the Calculation Settings Block. In BIFF5-BIFF8 it is stored
    in the Workbook Globals Substream.

    Record PRECISION, BIFF2-BIFF8:

    Offset  Size    Contents
    0       2       0 = Use displayed values;
                    1 = Use real cell values
    """
    _REC_ID = 0x000E

    def __init__(self, use_real_values):
        if use_real_values:
            self._rec_data = pack('<H', 1)
        else:
            self._rec_data = pack('<H', 0)


class CodepageBiff8Record(BiffRecord):
    """
    This record stores the text encoding used to write byte strings, stored
    as MS Windows code page identifier. The CODEPAGE record in BIFF8 always
    contains  the  code  page  1200  (UTF-16).  Therefore  it is not
    possible  to  obtain the encoding used for a protection password (it is
    not UTF-16).

    Record CODEPAGE, BIFF2-BIFF8:

    Offset  Size    Contents
    0       2       Code page identifier used for byte string text encoding:
                      016FH = 367 = ASCII
                      01B5H = 437 = IBM PC CP-437 (US)
                      02D0H = 720 = IBM PC CP-720 (OEM Arabic)
                      02E1H = 737 = IBM PC CP-737 (Greek)
                      0307H = 775 = IBM PC CP-775 (Baltic)
                      0352H = 850 = IBM PC CP-850 (Latin I)
                      0354H = 852 = IBM PC CP-852 (Latin II (Central European))
                      0357H = 855 = IBM PC CP-855 (Cyrillic)
                      0359H = 857 = IBM PC CP-857 (Turkish)
                      035AH = 858 = IBM PC CP-858 (Multilingual Latin I with Euro)
                      035CH = 860 = IBM PC CP-860 (Portuguese)
                      035DH = 861 = IBM PC CP-861 (Icelandic)
                      035EH = 862 = IBM PC CP-862 (Hebrew)
                      035FH = 863 = IBM PC CP-863 (Canadian (French))
                      0360H = 864 = IBM PC CP-864 (Arabic)
                      0361H = 865 = IBM PC CP-865 (Nordic)
                      0362H = 866 = IBM PC CP-866 (Cyrillic (Russian))
                      0365H = 869 = IBM PC CP-869 (Greek (Modern))
                      036AH = 874 = Windows CP-874 (Thai)
                      03A4H = 932 = Windows CP-932 (Japanese Shift-JIS)
                      03A8H = 936 = Windows CP-936 (Chinese Simplified GBK)
                      03B5H = 949 = Windows CP-949 (Korean (Wansung))
                      03B6H = 950 = Windows CP-950 (Chinese Traditional BIG5)
                      04B0H = 1200 = UTF-16 (BIFF8)
                      04E2H = 1250 = Windows CP-1250 (Latin II) (Central European)
                      04E3H = 1251 = Windows CP-1251 (Cyrillic)
                      04E4H = 1252 = Windows CP-1252 (Latin I) (BIFF4-BIFF7)
                      04E5H = 1253 = Windows CP-1253 (Greek)
                      04E6H = 1254 = Windows CP-1254 (Turkish)
                      04E7H = 1255 = Windows CP-1255 (Hebrew)
                      04E8H = 1256 = Windows CP-1256 (Arabic)
                      04E9H = 1257 = Windows CP-1257 (Baltic)
                      04EAH = 1258 = Windows CP-1258 (Vietnamese)
                      0551H = 1361 = Windows CP-1361 (Korean (Johab))
                      2710H = 10000 = Apple Roman
                      8000H = 32768 = Apple Roman
                      8001H = 32769 = Windows CP-1252 (Latin I) (BIFF2-BIFF3)
    """
    _REC_ID = 0x0042
    UTF_16 = 0x04B0

    def __init__(self):
        self._rec_data = pack('<H', self.UTF_16)

class Window1Record(BiffRecord):
    """
    Offset Size Contents
    0      2    Horizontal position of the document window (in twips = 1/20 of a point)
    2      2    Vertical position of the document window (in twips = 1/20 of a point)
    4      2    Width of the document window (in twips = 1/20 of a point)
    6      2    Height of the document window (in twips = 1/20 of a point)
    8      2    Option flags:
                  Bits  Mask  Contents
                  0     0001H 0 = Window is visible 1 = Window is hidden
                  1     0002H 0 = Window is open 1 = Window is minimised
                  3     0008H 0 = Horizontal scroll bar hidden 1 = Horizontal scroll bar visible
                  4     0010H 0 = Vertical scroll bar hidden 1 = Vertical scroll bar visible
                  5     0020H 0 = Worksheet tab bar hidden 1 = Worksheet tab bar visible
    10     2    Index to active (displayed) worksheet
    12     2    Index of first visible tab in the worksheet tab bar
    14     2    Number of selected worksheets (highlighted in the worksheet tab bar)
    16     2    Width of worksheet tab bar (in 1/1000 of window width). The remaining space is used by the
                horizontal scrollbar.
    """
    _REC_ID = 0x003D
    # flags

    def __init__(self,
                 hpos_twips, vpos_twips,
                 width_twips, height_twips,
                 flags,
                 active_sheet,
                 first_tab_index, selected_tabs, tab_width):
        self._rec_data = pack('<9H', hpos_twips, vpos_twips,
                                      width_twips, height_twips,
                                      flags,
                                      active_sheet,
                                      first_tab_index, selected_tabs, tab_width)

class FontRecord(BiffRecord):
    """
    WARNING
        The font with index 4 is omitted in all BIFF versions.
        This means the first four fonts have zero-based indexes, and
        the fifth font and all following fonts are referenced with one-based
        indexes.

    Offset Size Contents
    0      2    Height of the font (in twips = 1/20 of a point)
    2      2    Option flags:
                  Bit Mask    Contents
                  0   0001H   1 = Characters are bold (redundant, see below)
                  1   0002H   1 = Characters are italic
                  2   0004H   1 = Characters are underlined (redundant, see below)
                  3   0008H   1 = Characters are struck out
                        0010H 1 = Outline
                        0020H  1 = Shadow
    4     2     Colour index
    6     2     Font weight (100-1000).
                Standard values are 0190H (400) for normal text and 02BCH
                (700) for bold text.
    8     2     Escapement type:
                  0000H = None
                  0001H = Superscript
                  0002H = Subscript
    10    1     Underline type:
                  00H = None
                  01H = Single
                  21H = Single accounting
                  02H = Double
                  22H = Double accounting
    11    1     Font family:
                  00H = None (unknown or don't care)
                  01H = Roman (variable width, serifed)
                  02H = Swiss (variable width, sans-serifed)
                  03H = Modern (fixed width, serifed or sans-serifed)
                  04H = Script (cursive)
                  05H = Decorative (specialised, i.e. Old English, Fraktur)
    12    1     Character set:
                  00H = 0 = ANSI Latin
                  01H = 1 = System default
                  02H = 2 = Symbol
                  4DH = 77 = Apple Roman
                  80H = 128 = ANSI Japanese Shift-JIS
                  81H = 129 = ANSI Korean (Hangul)
                  82H = 130 = ANSI Korean (Johab)
                  86H = 134 = ANSI Chinese Simplified GBK
                  88H = 136 = ANSI Chinese Traditional BIG5
                  A1H = 161 = ANSI Greek
                  A2H = 162 = ANSI Turkish
                  A3H = 163 = ANSI Vietnamese
                  B1H = 177 = ANSI Hebrew
                  B2H = 178 = ANSI Arabic
                  BAH = 186 = ANSI Baltic
                  CCH = 204 = ANSI Cyrillic
                  DEH = 222 = ANSI Thai
                  EEH = 238 = ANSI Latin II (Central European)
                  FFH = 255 = OEM Latin I
    13    1     Not used
    14    var.  Font name:
                  BIFF5/BIFF7: Byte string, 8-bit string length
                  BIFF8: Unicode string, 8-bit string length
    The boldness and underline flags are still set in the options field,
    but not used on reading the font. Font weight and underline type
    are specified in separate fields instead.
    """
    _REC_ID = 0x0031

    def __init__(self,
                    height, options, colour_index, weight, escapement,
                    underline, family, charset,
                    name):
        uname = upack1(name)
        uname_len = len(uname)

        self._rec_data = pack('<5H4B%ds' % uname_len, height, options, colour_index, weight, escapement,
                                                underline, family, charset, 0x00,
                                                uname)

class NumberFormatRecord(BiffRecord):
    """
    Record FORMAT, BIFF8:
    Offset  Size    Contents
    0       2       Format index used in other records
    2       var.    Number format string (Unicode string, 16-bit string length)

    From  BIFF5  on,  the built-in number formats will be omitted. The built-in
    formats  are  dependent  on  the current regional settings of the operating
    system.  The following table shows which number formats are used by default
    in  a  US-English  environment.  All indexes from 0 to 163 are reserved for
    built-in formats. The first user-defined format starts at 164.

    The built-in number formats, BIFF5-BIFF8

    Index   Type        Format string
    0       General     General
    1       Decimal     0
    2       Decimal     0.00
    3       Decimal     #,##0
    4       Decimal     #,##0.00
    5       Currency    "$"#,##0_);("$"#,##
    6       Currency    "$"#,##0_);[Red]("$"#,##
    7       Currency    "$"#,##0.00_);("$"#,##
    8       Currency    "$"#,##0.00_);[Red]("$"#,##
    9       Percent     0%
    10      Percent     0.00%
    11      Scientific  0.00E+00
    12      Fraction    # ?/?
    13      Fraction    # ??/??
    14      Date        M/D/YY
    15      Date        D-MMM-YY
    16      Date        D-MMM
    17      Date        MMM-YY
    18      Time        h:mm AM/PM
    19      Time        h:mm:ss AM/PM
    20      Time        h:mm
    21      Time        h:mm:ss
    22      Date/Time   M/D/YY h:mm
    37      Account     _(#,##0_);(#,##0)
    38      Account     _(#,##0_);[Red](#,##0)
    39      Account     _(#,##0.00_);(#,##0.00)
    40      Account     _(#,##0.00_);[Red](#,##0.00)
    41      Currency    _("$"* #,##0_);_("$"* (#,##0);_("$"* "-"_);_(@_)
    42      Currency    _(* #,##0_);_(* (#,##0);_(* "-"_);_(@_)
    43      Currency    _("$"* #,##0.00_);_("$"* (#,##0.00);_("$"* "-"??_);_(@_)
    44      Currency    _(* #,##0.00_);_(* (#,##0.00);_(* "-"??_);_(@_)
    45      Time        mm:ss
    46      Time        [h]:mm:ss
    47      Time        mm:ss.0
    48      Scientific  ##0.0E+0
    49      Text        @
    """
    _REC_ID = 0x041E

    def __init__(self, idx, fmtstr):
        ufmtstr = upack2(fmtstr)
        ufmtstr_len = len(ufmtstr)

        self._rec_data = pack('<H%ds' % ufmtstr_len, idx, ufmtstr)


class XFRecord(BiffRecord):
    """
    XF Substructures
    -------------------------------------------------------------------------
    XF_TYPE_PROT  XF Type and Cell Protection (3 Bits), BIFF3-BIFF8
    These 3 bits are part of a specific data byte.
    Bit Mask    Contents
    0   01H     1 = Cell is locked
    1   02H     1 = Formula is hidden
    2   04H     0 = Cell XF; 1 = Style XF

    XF_USED_ATTRIB   Attributes   Used  from  Parent  Style  XF  (6  Bits),
    BIFF3-BIFF8  Each  bit  describes  the  validity  of  a  specific group
    of  attributes.  In  cell XFs a cleared bit means the attributes of the
    parent  style XF are used (but only if the attributes are valid there),
    a  set  bit  means  the  attributes  of  this XF are used. In style XFs
    a cleared bit means the attribute setting is valid, a set bit means the
    attribute should be ignored.
    Bit Mask    Contents
    0   01H     Flag for number format
    1   02H     Flag for font
    2   04H     Flag for horizontal and vertical alignment, text wrap, indentation, orientation, rotation, and
                text direction
    3   08H     Flag for border lines
    4   10H     Flag for background area style
    5   20H     Flag for cell protection (cell locked and formula hidden)

    XF_HOR_ALIGN  Horizontal Alignment (3 Bits), BIFF2-BIFF8 The horizontal
    alignment consists of 3 bits and is part of a specific data byte.
    Value   Horizontal alignment
    00H     General
    01H     Left
    02H     Centred
    03H     Right
    04H     Filled
    05H     Justified (BIFF4-BIFF8X)
    06H     Centred across selection (BIFF4-BIFF8X)
    07H     Distributed (BIFF8X)

    XF_VERT_ALIGN Vertical Alignment (2 or 3 Bits), BIFF4-BIFF8
    The vertical alignment consists of 2 bits (BIFF4) or 3 bits (BIFF5-BIFF8)
    and is part of a specific data byte. Vertical alignment is not available
    in BIFF2 and BIFF3.
    Value   Vertical alignment
    00H     Top
    01H     Centred
    02H     Bottom
    03H     Justified (BIFF5-BIFF8X)
    04H     Distributed (BIFF8X)

    XF_ORIENTATION  Text  Orientation  (2  Bits),  BIFF4-BIFF7  In the BIFF
    versions  BIFF4-BIFF7,  text  can  be  rotated  in  steps of 90 degrees
    or  stacked.  The  orientation  mode  consists of 2 bits and is part of
    a specific data byte. In BIFF8 a rotation angle occurs instead of these
    flags.
    Value   Text orientation
    00H     Not rotated
    01H     Letters are stacked top-to-bottom, but not rotated
    02H     Text is rotated 90 degrees counterclockwise
    03H     Text is rotated 90 degrees clockwise

    XF_ROTATION Text Rotation Angle (1 Byte), BIFF8
    Value   Text rotation
    0       Not rotated
    1-90    1 to 90 degrees counterclockwise
    91-180  1 to 90 degrees clockwise
    255     Letters are stacked top-to-bottom, but not rotated

    XF_BORDER_34  Cell  Border  Style  (4  Bytes), BIFF3-BIFF4 Cell borders
    contain a line style and a line colour for each line of the border.
    Bit     Mask        Contents
    2-0     00000007H   Top line style
    7-3     000000F8H   Colour index for top line colour
    10-8    00000700H   Left line style
    15-11   0000F800H   Colour index for left line colour
    18-16   00070000H   Bottom line style
    23-19   00F80000H   Colour index for bottom line colour
    26-24   07000000H   Right line style
    31-27   F8000000H   Colour index for right line colour

    XF_AREA_34  Cell  Background  Area  Style (2 Bytes), BIFF3-BIFF4 A cell
    background  area  style  contains  an area pattern and a foreground and
    background colour.
    Bit     Mask    Contents
    5-0     003FH   Fill pattern
    10-6    07C0H   Colour index for pattern colour
    15-11   F800H   Colour index for pattern background
 ---------------------------------------------------------------------------------------------
    Record XF, BIFF8:
    Offset      Size    Contents
    0           2       Index to FONT record
    2           2       Index to FORMAT record
    4           2       Bit     Mask    Contents
                        2-0     0007H   XF_TYPE_PROT . XF type, cell protection (see above)
                        15-4    FFF0H   Index to parent style XF (always FFFH in style XFs)
    6           1       Bit     Mask    Contents
                        2-0     07H     XF_HOR_ALIGN . Horizontal alignment (see above)
                        3       08H     1 = Text is wrapped at right border
                        6-4     70H     XF_VERT_ALIGN . Vertical alignment (see above)
    7           1       XF_ROTATION: Text rotation angle (see above)
    8           1       Bit     Mask    Contents
                        3-0     0FH     Indent level
                        4       10H     1 = Shrink content to fit into cell
                        5               merge
                        7-6     C0H     Text direction (BIFF8X only)
                                        00b = According to context
                                        01b = Left-to-right
                                        10b = Right-to-left
    9           1       Bit     Mask    Contents
                        7-2     FCH     XF_USED_ATTRIB . Used attributes (see above)
    10          4       Cell border lines and background area:
                        Bit     Mask      Contents
                        3-0     0000000FH Left line style
                        7-4     000000F0H Right line style
                        11-8    00000F00H Top line style
                        15-12   0000F000H Bottom line style
                        22-16   007F0000H Colour index for left line colour
                        29-23   3F800000H Colour index for right line colour
                        30      40000000H 1 = Diagonal line from top left to right bottom
                        31      80000000H 1 = Diagonal line from bottom left to right top
    14          4       Bit     Mask      Contents
                        6-0     0000007FH Colour index for top line colour
                        13-7    00003F80H Colour index for bottom line colour
                        20-14   001FC000H Colour index for diagonal line colour
                        24-21   01E00000H Diagonal line style
                        31-26   FC000000H Fill pattern
    18          2       Bit     Mask    Contents
                        6-0     007FH   Colour index for pattern colour
                        13-7    3F80H   Colour index for pattern background

    """
    _REC_ID = 0x00E0

    def __init__(self, xf, xftype='cell'):
        font_xf_idx, fmt_str_xf_idx, alignment, borders, pattern, protection = xf
        fnt = pack('<H', font_xf_idx)
        fmt = pack('<H', fmt_str_xf_idx)
        if xftype == 'cell':
            prt = pack('<H',
                ((protection.cell_locked    & 0x01) << 0) |
                ((protection.formula_hidden & 0x01) << 1)
            )
        else:
            prt = pack('<H', 0xFFF5)
        aln = pack('B',
            ((alignment.horz & 0x07) << 0) |
            ((alignment.wrap & 0x01) << 3) |
            ((alignment.vert & 0x07) << 4)
        )
        rot = pack('B', alignment.rota)
        txt = pack('B',
            ((alignment.inde & 0x0F) << 0) |
            ((alignment.shri & 0x01) << 4) |
            ((alignment.merg & 0x01) << 5) |
            ((alignment.dire & 0x03) << 6)
        )
        if xftype == 'cell':
            used_attr = pack('B', 0xF8)
        else:
            used_attr = pack('B', 0xF4)

        if borders.left == borders.NO_LINE:
            borders.left_colour = 0x00
        if borders.right == borders.NO_LINE:
            borders.right_colour = 0x00
        if borders.top == borders.NO_LINE:
            borders.top_colour = 0x00
        if borders.bottom == borders.NO_LINE:
            borders.bottom_colour = 0x00
        if borders.diag == borders.NO_LINE:
            borders.diag_colour = 0x00
        brd1 = pack('<L',
            ((borders.left          & 0x0F) << 0 ) |
            ((borders.right         & 0x0F) << 4 ) |
            ((borders.top           & 0x0F) << 8 ) |
            ((borders.bottom        & 0x0F) << 12) |
            ((borders.left_colour   & 0x7F) << 16) |
            ((borders.right_colour  & 0x7F) << 23) |
            ((borders.need_diag1    & 0x01) << 30) |
            ((borders.need_diag2    & 0x01) << 31)
        )
        brd2 = pack('<L',
            ((borders.top_colour    & 0x7F) << 0 ) |
            ((borders.bottom_colour & 0x7F) << 7 ) |
            ((borders.diag_colour   & 0x7F) << 14) |
            ((borders.diag          & 0x0F) << 21) |
            ((pattern.pattern       & 0x3F) << 26)
        )
        pat = pack('<H',
            ((pattern.pattern_fore_colour & 0x7F) << 0 ) |
            ((pattern.pattern_back_colour & 0x7F) << 7 )
        )
        self._rec_data = fnt + fmt + prt + \
                        aln + rot + txt + used_attr + \
                        brd1 + brd2 + \
                        pat

class StyleRecord(BiffRecord):
    """
    STYLE record for user-defined cell styles, BIFF3-BIFF8:
    Offset  Size    Contents
    0       2       Bit     Mask    Contents
                    11-0    0FFFH   Index to style XF record
                    15      8000H   Always 0 for user-defined styles
    2       var.    BIFF2-BIFF7: Non-empty byte string, 8-bit string length
                    BIFF8: Non-empty Unicode string, 16-bit string length
    STYLE record for built-in cell styles, BIFF3-BIFF8:
    Offset  Size    Contents
    0       2       Bit     Mask    Contents
                    11-0    0FFFH   Index to style XF record
                    15      8000H   Always 1 for built-in styles
    2       1       Identifier of the built-in cell style:
                        00H = Normal
                        01H = RowLevel_lv (see next field)
                        02H = ColLevel_lv (see next field)
                        03H = Comma
                        04H = Currency
                        05H = Percent
                        06H = Comma [0] (BIFF4-BIFF8)
                        07H = Currency [0] (BIFF4-BIFF8)
                        08H = Hyperlink (BIFF8)
                        09H = Followed Hyperlink (BIFF8)
    3       1       Level for RowLevel or ColLevel style
                    (zero-based, lv), FFH otherwise
    The  RowLevel  and  ColLevel  styles specify the formatting of subtotal
    cells  in  a specific outline level. The level is specified by the last
    field  in the STYLE record. Valid values are 0-6 for the outline levels
    1-7.
    """
    _REC_ID = 0x0293

    def __init__(self):
        self._rec_data = pack('<HBB', 0x8000, 0x00, 0xFF)
        # TODO: implement user-defined styles???


class PaletteRecord(BiffRecord):
    """
    This  record  contains  the  definition  of  all  user-defined  colours
    available for cell and object formatting.

    Record PALETTE, BIFF3-BIFF8:

    Offset  Size    Contents
    0       2       Number of following colours (nm). Contains 16 in BIFF3-BIFF4 and 56 in BIFF5-BIFF8.
    2       4*nm    List of nm RGB colours

    The following table shows how colour indexes are used in other records:

    Colour index    Resulting colour or internal list index
    00H             Built-in Black (R = 00H, G = 00H, B = 00H)
    01H             Built-in White (R = FFH, G = FFH, B = FFH)
    02H             Built-in Red (R = FFH, G = 00H, B = 00H)
    03H             Built-in Green (R = 00H, G = FFH, B = 00H)
    04H             Built-in Blue (R = 00H, G = 00H, B = FFH)
    05H             Built-in Yellow (R = FFH, G = FFH, B = 00H)
    06H             Built-in Magenta (R = FFH, G = 00H, B = FFH)
    07H             Built-in Cyan (R = 00H, G = FFH, B = FFH)
    08H             First user-defined colour from the PALETTE record (entry 0 from record colour list)
    .........................

    17H (BIFF3-BIFF4) Last user-defined colour from the PALETTE record (entry 15 or 55 from record colour list)
    3FH (BIFF5-BIFF8)

    18H (BIFF3-BIFF4) System window text colour for border lines (used in records XF, CF, and
    40H (BIFF5-BIFF8) WINDOW2 (BIFF8 only))

    19H (BIFF3-BIFF4) System window background colour for pattern background (used in records XF, and CF)
    41H (BIFF5-BIFF8)

    43H             System face colour (dialogue background colour)
    4DH             System window text colour for chart border lines
    4EH             System window background colour for chart areas
    4FH             Automatic colour for chart border lines (seems to be always Black)
    50H             System ToolTip background colour (used in note objects)
    51H             System ToolTip text colour (used in note objects)
    7FFFH           System window text colour for fonts (used in records FONT, EFONT, and CF)

    """
    _REC_ID = 0x0092

    def __init__(self, custom_palette):
        n_colours = len(custom_palette)
        assert n_colours == 56
        # Pack number of colors with little-endian, what xlrd and excel expect.
        self._rec_data = pack('<H', n_colours)
        # Microsoft lists colors in big-endian format with 24 bits/color.
        # Pad LSB of each color with 0x00, and write out in big-endian.
        fmt = '>%dI' % n_colours
        self._rec_data += pack(fmt, *(custom_palette))

class BoundSheetRecord(BiffRecord):
    """
    This  record  is  located  in  the workbook globals area and represents
    a  sheet  inside  of  the  workbook. For each sheet a BOUNDSHEET record
    is  written.  It  stores  the sheet name and a stream offset to the BOF
    record    within   the   workbook   stream.  The  record  is also known
    as BUNDLESHEET.

    Record BOUNDSHEET, BIFF5-BIFF8:
    Offset  Size    Contents
    0       4       Absolute stream position of the BOF record of the sheet represented by this record. This
                    field is never encrypted in protected files.
    4       1       Visibility:
                        00H = Visible
                        01H = Hidden
                        02H = Strong hidden
    5       1       Sheet type:
                        00H = Worksheet
                        02H = Chart
                        06H = Visual Basic module
    6       var.    Sheet name:
                        BIFF5/BIFF7: Byte string, 8-bit string length
                        BIFF8: Unicode string, 8-bit string length
    """
    _REC_ID = 0x0085

    def __init__(self, stream_pos, visibility, sheetname, encoding='ascii'):
        usheetname = upack1(sheetname, encoding)
        uusheetname_len = len(usheetname)

        self._rec_data = pack('<LBB%ds' % uusheetname_len, stream_pos, visibility, 0x00, usheetname)


class ContinueRecord(BiffRecord):
    """
    Whenever  the content of a record exceeds the given limits (see table),
    the  record  must  be  split.  Several  CONTINUE records containing the
    additional data are added after the parent record.

    BIFF version    Maximum data size of a record
    BIFF2-BIFF7     2080 bytes (2084 bytes including record header)
    BIFF8           8224 bytes (8228 bytes including record header) (0x2020)

    Record CONTINUE, BIFF2-BIFF8:
    Offset  Size    Contents
    0       var.    Data continuation of the previous record

    Unicode  strings  are  split in a special way. At the beginning of each
    CONTINUE  record  the option flags byte is repeated. Only the character
    size  flag  will  be set in this flags byte, the Rich-Text flag and the
    Far-East  flag  are set to zero. In each CONTINUE record it is possible
    that  the  character  size  changes  from  8-bit  characters  to 16-bit
    characters and vice versa.

    Never  a  Unicode  string  is  split  until  and  including  the  first
    character.  That means, all header fields (string length, option flags,
    optional Rich-Text size, and optional Far-East data size) and the first
    character  of  the string have to occur together in the leading record,
    or  have  to  be  moved completely into the CONTINUE record. Formatting
    runs cannot be split between their components (character index and FONT
    record  index).  If  a string is split between two formatting runs, the
    option flags field will not be repeated in the CONTINUE record.
    """
    _REC_ID = 0x003C


class SSTRecord(BiffRecord):
    """
    This  record  contains  a  list  of  all  strings  used anywhere in the
    workbook.  Each string occurs only once. The workbook uses indexes into
    the list to reference the strings.

    Record SST, BIFF8:
    Offset  Size    Contents
    0       4       Total number of strings in the workbook (see below)
    4       4       Number of following strings (nm)
    8       var.    List of nm Unicode strings, 16-bit string length

    The  first  field  of  the  SST  record  counts  the  total  occurrence
    of  strings  in  the  workbook.  For  instance,  the string AAA is used
    3  times  and  the string BBB is used 2 times. The first field contains
    5 and the second field contains 2, followed by the two strings.
    """
    _REC_ID = 0x00FC


class ExtSSTRecord(BiffRecord):
    """
    This  record  occurs  in  conjunction  with  the SST record. It is used
    by  Excel  to create a hash table with stream offsets to the SST record
    to optimise string search operations. Excel may not shorten this record
    if  strings  are deleted from the shared string table, so the last part
    might  contain  invalid  data. The stream indexes in this record divide
    the SST into portions containing a constant number of strings.

    Record EXTSST, BIFF8:

    Offset  Size    Contents
    0       2       Number of strings in a portion, this number is >=8
    2       var.    List of OFFSET structures for all portions. Each OFFSET contains the following data:
                        Offset Size Contents
                        0       4   Absolute stream position of first string of the portion
                        4       2   Position of first string of the portion inside of current record,
                                    including record header. This counter restarts at zero, if the SST
                                    record is continued with a CONTINUE record.
                        6       2   Not used
    """
    _REC_ID = 0x00FF

    def __init__(self, sst_stream_pos, str_placement, portions_len):
        extsst = {}
        abs_stream_pos = sst_stream_pos
        str_counter = 0
        portion_counter = 0
        while str_counter < len(str_placement):
            str_chunk_num, pos_in_chunk = str_placement[str_counter]
            if str_chunk_num <> portion_counter:
                portion_counter = str_chunk_num
                abs_stream_pos += portions_len[portion_counter-1]
                #print hex(abs_stream_pos)
            str_stream_pos = abs_stream_pos + pos_in_chunk + 4 # header
            extsst[str_counter] = (pos_in_chunk, str_stream_pos)
            str_counter += 1

        exsst_str_count_delta = max(8, len(str_placement)*8/0x2000) # maybe smth else?
        self._rec_data = pack('<H', exsst_str_count_delta)
        str_counter = 0
        while str_counter < len(str_placement):
            self._rec_data += pack('<IHH', extsst[str_counter][1], extsst[str_counter][0], 0)
            str_counter += exsst_str_count_delta

class DimensionsRecord(BiffRecord):
    """
    Record DIMENSIONS, BIFF8:

    Offset  Size    Contents
    0       4       Index to first used row
    4       4       Index to last used row, increased by 1
    8       2       Index to first used column
    10      2       Index to last used column, increased by 1
    12      2       Not used
    """
    _REC_ID = 0x0200
    def __init__(self, first_used_row, last_used_row, first_used_col, last_used_col):
        if first_used_row > last_used_row or first_used_col > last_used_col:
            # Special case: empty worksheet
            first_used_row = first_used_col = 0
            last_used_row = last_used_col = -1
        self._rec_data = pack('<2L3H',
            first_used_row, last_used_row + 1,
            first_used_col, last_used_col + 1,
            0x00)


class Window2Record(BiffRecord):
    """
    Record WINDOW2, BIFF8:

    Offset  Size Contents
    0       2 Option flags (see below)
    2       2 Index to first visible row
    4       2 Index to first visible column
    6       2 Colour index of grid line colour. Note that in BIFF2-BIFF7 an RGB colour is
                written instead.
    8       2 Not used
    10      2 Cached magnification factor in page break preview (in percent); 0 = Default (60%)
    12      2 Cached magnification factor in normal view (in percent); 0 = Default (100%)
    14      4 Not used

    In  BIFF8  this record stores used magnification factors for page break
    preview  and  normal  view.  These  values  are  used  to  restore  the
    magnification,  when the view is changed. The real magnification of the
    currently  active  view  is  stored  in the SCL record. The type of the
    active view is stored in the option flags field (see below).

     0 0001H 0 = Show formula results 1 = Show formulas
     1 0002H 0 = Do not show grid lines 1 = Show grid lines
     2 0004H 0 = Do not show sheet headers 1 = Show sheet headers
     3 0008H 0 = Panes are not frozen 1 = Panes are frozen (freeze)
     4 0010H 0 = Show zero values as empty cells 1 = Show zero values
     5 0020H 0 = Manual grid line colour 1 = Automatic grid line colour
     6 0040H 0 = Columns from left to right 1 = Columns from right to left
     7 0080H 0 = Do not show outline symbols 1 = Show outline symbols
     8 0100H 0 = Keep splits if pane freeze is removed 1 = Remove splits if pane freeze is removed
     9 0200H 0 = Sheet not selected 1 = Sheet selected (BIFF5-BIFF8)
    10 0400H 0 = Sheet not visible 1 = Sheet visible (BIFF5-BIFF8)
    11 0800H 0 = Show in normal view 1 = Show in page break preview (BIFF8)

    The freeze flag specifies, if a following PANE record describes unfrozen or frozen panes.

    *** This class appends the optional SCL record ***

    Record SCL, BIFF4-BIFF8:

    This record stores the magnification of the active view of the current worksheet.
    In BIFF8 this can be either the normal view or the page break preview.
    This is determined in the WINDOW2 record. The SCL record is part of the
    Sheet View Settings Block.

    Offset  Size    Contents
    0       2       Numerator of the view magnification fraction (num)
    2       2       Denumerator [denominator] of the view magnification fraction (den)
    The magnification is stored as reduced fraction. The magnification results from num/den.

    SJM note: Excel expresses (e.g.) 25% in reduced form i.e. 1/4. Reason unknown. This code
    writes 25/100, and Excel is happy with that.

    """
    _REC_ID = 0x023E

    def __init__(self, options, first_visible_row, first_visible_col,
        grid_colour, preview_magn, normal_magn, scl_magn):
        self._rec_data = pack('<7HL', options,
                                    first_visible_row, first_visible_col,
                                    grid_colour,
                                    0x00,
                                    preview_magn, normal_magn,
                                    0x00L)
        if scl_magn is not None:
            self._scl_rec = pack('<4H', 0x00A0, 4, scl_magn, 100)
        else:
            self._scl_rec = ''

    def get(self):
        return self.get_rec_header() + self._rec_data + self._scl_rec


class PanesRecord(BiffRecord):
    """
    This record stores the position of window panes. It is part of the Sheet
    View Settings Block. If the sheet does not contain any splits, this
    record will not occur.
    A sheet can be split in two different ways, with unfrozen panes or with
    frozen panes. A flag in the WINDOW2 record specifies, if the panes are
    frozen, which affects the contents of this record.

    Record PANE, BIFF2-BIFF8:
    Offset      Size        Contents
    0           2           Position of the vertical split
                            (px, 0 = No vertical split):
                            Unfrozen pane: Width of the left pane(s)
                            (in twips = 1/20 of a point)
                            Frozen pane: Number of visible
                            columns in left pane(s)
    2           2           Position of the horizontal split
                            (py, 0 = No horizontal split):
                            Unfrozen pane: Height of the top pane(s)
                            (in twips = 1/20 of a point)
                            Frozen pane: Number of visible
                            rows in top pane(s)
    4           2           Index to first visible row
                            in bottom pane(s)
    6           2           Index to first visible column
                            in right pane(s)
    8           1           Identifier of pane with active
                            cell cursor
    [9]         1           Not used (BIFF5-BIFF8 only, not written
                            in BIFF2-BIFF4)

    If the panes are frozen, pane 0 is always active, regardless
    of the cursor position. The correct identifiers for all possible
    combinations of visible panes are shown in the following pictures.

    px = 0, py = 0                  px = 0, py > 0
    --------------------------      ------------|-------------
    |                        |      |                        |
    |                        |      |           3            |
    |                        |      |                        |
    -           3            -      --------------------------
    |                        |      |                        |
    |                        |      |           2            |
    |                        |      |                        |
    --------------------------      ------------|-------------

    px > 0, py = 0                  px > 0, py > 0
    ------------|-------------      ------------|-------------
    |           |            |      |           |            |
    |           |            |      |     3     |      2     |
    |           |            |      |           |            |
    -     3     |      1     -      --------------------------
    |           |            |      |           |            |
    |           |            |      |     1     |      0     |
    |           |            |      |           |            |
    ------------|-------------      ------------|-------------
    """
    _REC_ID = 0x0041
    
    valid_active_pane = {
        # entries are of the form:
        # (int(px > 0),int(px>0)) -> allowed values
        (0,0):(3,),
        (0,1):(2,3),
        (1,0):(1,3),
        (1,1):(0,1,2,3),
        }
    
    def __init__(self, px, py, first_row_bottom, first_col_right, active_pane):
        allowed = self.valid_active_pane.get(
            (int(px > 0),int(py > 0))
            )
        if active_pane not in allowed:
            raise ValueError('Cannot set active_pane to %i, must be one of %s' % (
                    active_pane, ', '.join(allowed)
                    ))
        self._rec_data = pack('<5H',
                              px, py,
                              first_row_bottom, first_col_right,
                              active_pane)


class RowRecord(BiffRecord):
    """
    This  record  contains  the properties of a single row in a sheet. Rows
    and cells in a sheet are divided into blocks of 32 rows.

    Record ROW, BIFF3-BIFF8:

    Offset  Size    Contents
    0       2       Index of this row
    2       2       Index to column of the first cell which is described by a cell record
    4       2       Index to column of the last cell which is described by a cell record,
                    increased by 1
    6       2       Bit     Mask    Contents
                    14-0    7FFFH   Height of the row, in twips = 1/20 of a point
                    15      8000H   0 = Row has custom height; 1 = Row has default height
    8       2       Not used
    10      2       In BIFF3-BIFF4 this field contains a relative offset
                    to calculate stream position of the first cell record
                    for this row. In BIFF5-BIFF8 this field is not used
                    anymore, but the DBCELL record instead.
    12      4       Option flags and default row formatting:
                    Bit     Mask        Contents
                    2-0     00000007H   Outline level of the row
                    4       00000010H   1 = Outline group starts or ends here (depending
                                        on where the outline buttons are located,
                                        see WSBOOL record), and is collapsed
                    5       00000020H   1 = Row is hidden (manually, or by a filter or outline group)
                    6       00000040H   1 = Row height and default font height do not match
                    7       00000080H   1 = Row has explicit default format (fl)
                    8       00000100H   Always 1
                    27-16   0FFF0000H   If fl=1: Index to default XF record
                    28      10000000H   1 = Additional space above the row. This flag is set,
                                        if the upper border of at least one cell in this row
                                        or if the lower border of at least one cell in the row
                                        above is formatted with a thick line style.
                                        Thin and medium line styles are not taken into account.
                    29      20000000H   1 = Additional space below the row. This flag is set,
                                        if the lower border of at least one cell in this row
                                        or if the upper border of at least one cell in the row
                                        below is formatted with a medium or thick line style.
                                        Thin line styles are not taken into account.
    """

    _REC_ID = 0x0208

    def __init__(self, index, first_col, last_col, height_options, options):
        self._rec_data = pack('<6HL', index, first_col, last_col + 1,
                                        height_options,
                                        0x00, 0x00,
                                        options)

class LabelSSTRecord(BiffRecord):
    """
    This record represents a cell that contains a string. It replaces the
    LABEL record and RSTRING record used in BIFF2-BIFF7.
    """
    _REC_ID = 0x00FD

    def __init__(self, row, col, xf_idx, sst_idx):
        self._rec_data = pack('<3HL', row, col, xf_idx, sst_idx)


class MergedCellsRecord(BiffRecord):
    """
    This record contains all merged cell ranges of the current sheet.

    Record MERGEDCELLS, BIFF8:

    Offset  Size    Contents
    0       var.    Cell range address list with all merged ranges

    ------------------------------------------------------------------

    A cell range address list consists of a field with the number of ranges
    and the list of the range addresses.

    Cell range address list, BIFF8:

    Offset  Size            Contents
    0       2               Number of following cell range addresses (nm)
    2       8*nm            List of nm cell range addresses

    ---------------------------------------------------------------------
    Cell range address, BIFF8:

    Offset  Size    Contents
    0       2       Index to first row
    2       2       Index to last row
    4       2       Index to first column
    6       2       Index to last column

    """
    _REC_ID = 0x00E5

    def __init__(self, merged_list):
        i = len(merged_list) - 1
        while i >= 0:
            j = 0
            merged = ''
            while (i >= 0) and (j < 0x403):
                r1, r2, c1, c2 = merged_list[i]
                merged += pack('<4H', r1, r2, c1, c2)
                i -= 1
                j += 1
            self._rec_data += pack('<3H', self._REC_ID, len(merged) + 2, j) + \
                                    merged

    # for some reason Excel doesn't use CONTINUE
    def get(self):
        return self._rec_data

class MulBlankRecord(BiffRecord):
    """
    This  record  represents  a  cell  range  of empty cells. All cells are
    located in the same row.

    Record MULBLANK, BIFF5-BIFF8:

    Offset  Size    Contents
    0       2       Index to row
    2       2       Index to first column (fc)
    4       2*nc    List of nc=lc-fc+1 16-bit indexes to XF records
    4+2*nc  2       Index to last column (lc)
    """
    _REC_ID = 0x00BE

    def __init__(self, row, first_col, last_col, xf_index):
        blanks_count = last_col-first_col+1
        self._rec_data = pack('<%dH' % blanks_count, *([xf_index] * blanks_count))
        self._rec_data = pack('<2H', row, first_col) +  self._rec_data + pack('<H',  last_col)


class BlankRecord(BiffRecord):
    """
    This  record  represents  an empty cell.

    Record BLANK, BIFF5-BIFF8:

    Offset  Size    Contents
    0       2       Index to row
    2       2       Index to first column (fc)
    4       2       indexes to XF record
    """
    _REC_ID = 0x0201

    def __init__(self, row, col, xf_index):
        self._rec_data = pack('<3H', row, col, xf_index)


class RKRecord(BiffRecord):
    """
    This record represents a cell that contains an RK value (encoded integer or
    floating-point value). If a floating-point value cannot be encoded to an RK value,
    a NUMBER record will be written.
    """
    _REC_ID = 0x027E

    def __init__(self, row, col, xf_index, rk_encoded):
        self._rec_data = pack('<3Hi', row, col, xf_index, rk_encoded)


class NumberRecord(BiffRecord):
    """
    This record represents a cell that contains an IEEE-754 floating-point value.
    """
    _REC_ID = 0x0203

    def __init__(self, row, col, xf_index, number):
        self._rec_data = pack('<3Hd', row, col, xf_index, number)

class BoolErrRecord(BiffRecord):
    """
    This record represents a cell that contains a boolean or error value.
    """
    _REC_ID = 0x0205

    def __init__(self, row, col, xf_index, number, is_error):
        self._rec_data = pack('<3HBB', row, col, xf_index, number, is_error)


class FormulaRecord(BiffRecord):
    """
    Offset Size Contents
    0      2    Index to row
    2      2    Index to column
    4      2    Index to XF record
    6      8    Result of the formula
    14     2    Option flags:
                Bit Mask    Contents
                0   0001H   1 = Recalculate always
                1   0002H   1 = Calculate on open
                3   0008H   1 = Part of a shared formula
    16     4    Not used
    20     var. Formula data (RPN token array)

    """
    _REC_ID = 0x0006

    def __init__(self, row, col, xf_index, rpn, calc_flags=0):
        self._rec_data = pack('<3HQHL', row, col, xf_index, 0xFFFF000000000003, calc_flags & 3, 0) + rpn


class GutsRecord(BiffRecord):
    """
    This record contains information about the layout of outline symbols.

    Record GUTS, BIFF3-BIFF8:

    Offset  Size    Contents
    0       2       Width of the area to display row outlines (left of the sheet), in pixel
    2       2       Height of the area to display column outlines (above the sheet), in pixel
    4       2       Number of visible row outline levels (used row levels + 1; or 0, if not used)
    6       2       Number of visible column outline levels (used column levels + 1; or 0, if not used)

    """

    _REC_ID = 0x0080

    def __init__(self, row_gut_width, col_gut_height, row_visible_levels, col_visible_levels):
        self._rec_data = pack('<4H', row_gut_width, col_gut_height, row_visible_levels, col_visible_levels)

class WSBoolRecord(BiffRecord):
    """
    This  record stores a 16 bit value with Boolean options for the current
    sheet.  From BIFF5 on the "Save external linked values" option is moved
    to the record BOOKBOOL.

    Option flags of record WSBOOL, BIFF3-BIFF8:

    Bit     Mask    Contents
    0       0001H   0 = Do not show automatic page breaks
                    1 = Show automatic page breaks
    4       0010H   0 = Standard sheet
                    1 = Dialogue sheet (BIFF5-BIFF8)
    5       0020H   0 = No automatic styles in outlines
                    1 = Apply automatic styles to outlines
    6       0040H   0 = Outline buttons above outline group
                    1 = Outline buttons below outline group
    7       0080H   0 = Outline buttons left of outline group
                    1 = Outline buttons right of outline group
    8       0100H   0 = Scale printout in percent
                    1 = Fit printout to number of pages
    9       0200H   0 = Save external linked values (BIFF3?BIFF4 only)
                    1 = Do not save external linked values (BIFF3?BIFF4 only)
    10      0400H   0 = Do not show row outline symbols
                    1 = Show row outline symbols
    11      0800H   0 = Do not show column outline symbols
                    1 = Show column outline symbols
    13-12   3000H   These flags specify the arrangement of windows.
                    They are stored in BIFF4 only.
                    00 = Arrange windows tiled
                    01 = Arrange windows horizontal
                    10 = Arrange windows vertical112 = Arrange windows cascaded
    The following flags are valid for BIFF4-BIFF8 only:
    14      4000H   0 = Standard expression evaluation
                    1 = Alternative expression evaluation
    15      8000H   0 = Standard formula entries
                    1 = Alternative formula entries

    """
    _REC_ID = 0x0081

    def __init__(self, options):
        self._rec_data = pack('<H', options)

class ColInfoRecord(BiffRecord):
    """
    This record specifies the width for a given range of columns.
    If a column does not have a corresponding COLINFO record,
    the width specified in the record STANDARDWIDTH is used. If
    this record is also not present, the contents of the record
    DEFCOLWIDTH is used instead.
    This record also specifies a default XF record to use for
    cells in the columns that are not described by any cell record
    (which contain the XF index for that cell). Additionally,
    the option flags field contains hidden, outline, and collapsed
    options applied at the columns.

    Record COLINFO, BIFF3-BIFF8:

    Offset  Size    Contents
    0       2       Index to first column in the range
    2       2       Index to last column in the range
    4       2       Width of the columns in 1/256 of the width of the zero character, using default font
                    (first FONT record in the file)
    6       2       Index to XF record for default column formatting
    8       2       Option flags:
                    Bits    Mask    Contents
                    0       0001H   1 = Columns are hidden
                    10-8    0700H   Outline level of the columns (0 = no outline)
                    12      1000H   1 = Columns are collapsed
    10      2       Not used

    """
    _REC_ID = 0x007D

    def __init__(self, first_col, last_col, width, xf_index, options, unused):
        self._rec_data = pack('<6H', first_col, last_col, width, xf_index, options, unused)

class CalcModeRecord(BiffRecord):
    """
    This record is part of the Calculation Settings Block.
    It specifies whether to calculate formulas manually,
    automatically or automatically except for multiple table operations.

    Record CALCMODE, BIFF2-BIFF8:

    Offset  Size    Contents
    0       2       FFFFH = automatic except for multiple table operations
                    0000H = manually
                    0001H = automatically (default)
    """
    _REC_ID = 0x000D

    def __init__(self, calc_mode):
        self._rec_data = pack('<h', calc_mode)


class CalcCountRecord(BiffRecord):
    """
    This record is part of the Calculation Settings Block. It specifies the maximum
    number of times the formulas should be iteratively calculated. This is a fail-safe
    against mutually recursive formulas locking up a spreadsheet application.

    Record CALCCOUNT, BIFF2-BIFF8:

    Offset  Size    Contents
    0       2       Maximum number of iterations allowed in circular references
    """

    _REC_ID = 0x000C

    def __init__(self, calc_count):
        self._rec_data = pack('<H', calc_count)

class RefModeRecord(BiffRecord):
    """
    This record is part of the Calculation Settings Block.
    It stores which method is used to show cell addresses in formulas.
    The “RC” mode uses numeric indexes for rows and columns,
    i.e. “R(1)C(-1)”, or “R1C1:R2C2”.
    The “A1” mode uses characters for columns and numbers for rows,
    i.e. “B1”, or “$A$1:$B$2”.

    Record REFMODE, BIFF2-BIFF8:

    Offset  Size    Contents
    0       2       0 = RC mode; 1 = A1 mode

    """
    _REC_ID = 0x00F

    def __init__(self, ref_mode):
        self._rec_data = pack('<H', ref_mode)

class IterationRecord(BiffRecord):
    """
    This record is part of the Calculation Settings Block.
    It stores if iterations are allowed while calculating recursive formulas.

    Record ITERATION, BIFF2-BIFF8:

    Offset  Size    Contents
    0       2       0 = Iterations off; 1 = Iterations on
    """
    _REC_ID = 0x011

    def __init__(self, iterations_on):
        self._rec_data = pack('<H', iterations_on)

class DeltaRecord(BiffRecord):
    """
    This record is part of the Calculation Settings Block.
    It stores the maximum change of the result to exit an iteration.

    Record DELTA, BIFF2-BIFF8:

    Offset  Size    Contents
    0       8       Maximum change in iteration
                    (IEEE 754 floating-point value,
                     64bit double precision)
    """
    _REC_ID = 0x010

    def __init__(self, delta):
        self._rec_data = pack('<d', delta)

class SaveRecalcRecord(BiffRecord):
    """
    This record is part of the Calculation Settings Block.
    It contains the “Recalculate before save” option in
    Excel's calculation settings dialogue.

    Record SAVERECALC, BIFF3-BIFF8:

    Offset  Size    Contents
    0       2       0 = Do not recalculate;
                    1 = Recalculate before saving the document

    """
    _REC_ID = 0x05F

    def __init__(self, recalc):
        self._rec_data = pack('<H', recalc)

class PrintHeadersRecord(BiffRecord):
    """
    This record stores if the row and column headers
    (the areas with row numbers and column letters) will be printed.

    Record PRINTHEADERS, BIFF2-BIFF8:

    Offset  Size    Contents
    0       2       0 = Do not print row/column headers;
                    1 = Print row/column headers
    """
    _REC_ID = 0x02A

    def __init__(self, print_headers):
        self._rec_data = pack('<H', print_headers)


class PrintGridLinesRecord(BiffRecord):
    """
    This record stores if sheet grid lines will be printed.

    Record PRINTGRIDLINES, BIFF2-BIFF8:

    Offset  Size    Contents
    0       2       0 = Do not print sheet grid lines;
                    1 = Print sheet grid lines

    """
    _REC_ID = 0x02B

    def __init__(self, print_grid):
        self._rec_data = pack('<H', print_grid)


class GridSetRecord(BiffRecord):
    """
    This record specifies if the option to print sheet grid lines
    (record PRINTGRIDLINES) has ever been changed.

    Record GRIDSET, BIFF3-BIFF8:

    Offset  Size    Contents
    0       2       0 = Print grid lines option never changed
                    1 = Print grid lines option changed
    """
    _REC_ID = 0x082

    def __init__(self, print_grid_changed):
        self._rec_data = pack('<H', print_grid_changed)


class DefaultRowHeightRecord(BiffRecord):
    """
    This record specifies the default height and default flags
    for rows that do not have a corresponding ROW record.

    Record DEFAULTROWHEIGHT, BIFF3-BIFF8:

    Offset  Size    Contents
    0       2       Option flags:
                    Bit Mask    Contents
                    0   0001H   1 = Row height and default font height do not match
                    1   0002H   1 = Row is hidden
                    2   0004H   1 = Additional space above the row
                    3   0008H   1 = Additional space below the row
    2       2       Default height for unused rows, in twips = 1/20 of a point

    """
    _REC_ID = 0x0225

    def __init__(self, options, def_height):
        self._rec_data = pack('<2H', options, def_height)


class DefColWidthRecord(BiffRecord):
    """
    This record specifies the default column width for columns that
    do not have a specific width set using the record COLINFO or COLWIDTH.
    This record has no effect, if a STANDARDWIDTH record is present in the file.

    Record DEFCOLWIDTH, BIFF2-BIFF8:

    Offset  Size    Contents
    0       2       Column width in characters, using the width of the zero
                    character from default font (first FONT record in the file)
    """
    _REC_ID = 0x0055

    def __init__(self, def_width):
        self._rec_data = pack('<H', options, def_width)

class HorizontalPageBreaksRecord(BiffRecord):
    """
    This  record  is  part  of  the  Page  Settings  Block. It contains all
    horizontal manual page breaks.

    Record HORIZONTALPAGEBREAKS, BIFF8:
    Offset  Size  Contents
    0       2     Number of following row index structures (nm)
    2       6nm   List of nm row index structures. Each row index
                  structure contains:
                    Offset  Size    Contents
                    0       2       Index to first row below the page break
                    2       2       Index to first column of this page break
                    4       2       Index to last column of this page break

    The row indexes in the lists must be ordered ascending.
    If in BIFF8 a row contains several page breaks, they must be ordered
    ascending by start column index.
    """
    _REC_ID = 0x001B

    def __init__(self, breaks_list):
        self._rec_data = pack('<H', len(breaks_list))
        for r, c1, c2 in breaks_list:
            self._rec_data += pack('<3H', r, c1, c2)

class VerticalPageBreaksRecord(BiffRecord):
    """
    This  record  is  part  of  the  Page  Settings  Block. It contains all
    vertical manual page breaks.

    Record VERTICALPAGEBREAKS, BIFF8:
    Offset  Size  Contents
    0       2     Number of following column index structures (nm)
    2       6nm   List of nm column index structures. Each column index
                  structure contains:
                    Offset  Size    Contents
                    0       2       Index to first column following the page
                                    break
                    2       2       Index to first row of this page break
                    4       2       Index to last row of this page break

    The column indexes in the lists must be ordered ascending.
    If in BIFF8 a column contains several page breaks, they must be ordered
    ascending by start row index.
    """
    _REC_ID = 0x001A

    def __init__(self, breaks_list):
        self._rec_data = pack('<H', len(breaks_list))
        for r, c1, c2 in breaks_list:
            self._rec_data += pack('<3H', r, c1, c2)

class HeaderRecord(BiffRecord):
    """
    This record is part of the Page Settings Block. It specifies the
    page  header  string  for  the current worksheet. If this record is not
    present  or  completely  empty  (record  size is 0), the sheet does not
    contain a page header.

    Record HEADER for non-empty page header, BIFF2-BIFF8:
    Offset      Size    Contents
    0           var.    Page header string
                        BIFF2-BIFF7:    Non-empty byte string, 8bit string
                        length
                        BIFF8: Non-empty Unicode string, 16bit string length
    The  header  string may contain special commands, i.e. placeholders for
    the  page  number,  current  date, or text formatting attributes. These
    fields  are  represented  by  single  letters (exception: font name and
    size,  see  below)  with  a  leading  ampersand ("&"). If the ampersand
    is  part  of the regular header text, it will be duplicated ("&&"). The
    page  header is divided into 3 sections: the left, the centred, and the
    right  section.  Each  section  is introduced by a special command. All
    text  and all commands following are part of the selected section. Each
    section  starts  with the text formatting specified in the default font
    (first  FONT  record  in  the  file). Active formatting attributes from
    a previous section do not go into the next section.

    The following table shows all available commands:

    Command         Contents
    &&              The "&" character itself
    &L              Start of the left section
    &C              Start of the centred section
    &R              Start of the right section
    &P              Current page number
    &N              Page count
    &D              Current date
    &T              Current time
    &A              Sheet name (BIFF5-BIFF8)
    &F              File name without path
    &Z              File path without file name (BIFF8X)
    &G              Picture (BIFF8X)
    &B              Bold on/off (BIFF2-BIFF4)
    &I              Italic on/off (BIFF2-BIFF4)
    &U              Underlining on/off
    &E              Double underlining on/off (BIFF5-BIFF8)
    &S              Strikeout on/off
    &X              Superscript on/off (BIFF5-BIFF8)
    &Y              Subscript on/off (BIFF5-BIFF8)
    &"<fontname>"   Set new font <fontname>
    &"<fontname>,<fontstyle>"
                    Set new font with specified style <fontstyle>.
                    The style <fontstyle> is in most cases one of
                    "Regular", "Bold", "Italic", or "Bold Italic".
                    But this setting is dependent on the used font,
                    it may differ (localised style names, or "Standard",
                    "Oblique", ...). (BIFF5-BIFF8)
    &<fontheight>   Set font height in points (<fontheight> is a decimal value).
                    If this command is followed by a plain number to be printed
                    in the header, it will be separated from the font height
                    with a space character.

    """
    _REC_ID = 0x0014

    def __init__(self, header_str):
        self._rec_data = upack2(header_str)

class FooterRecord(BiffRecord):
    """
    Semantic is equal to HEADER record
    """
    _REC_ID = 0x0015

    def __init__(self, footer_str):
        self._rec_data = upack2(footer_str)


class HCenterRecord(BiffRecord):
    """
    This  record  is  part  of the Page Settings Block. It specifies if the
    sheet is centred horizontally when printed.

    Record HCENTER, BIFF3-BIFF8:

    Offset  Size    Contents
    0       2       0 = Print sheet left aligned
                    1 = Print sheet centred horizontally

    """
    _REC_ID = 0x0083

    def __init__(self, is_horz_center):
        self._rec_data = pack('<H', is_horz_center)


class VCenterRecord(BiffRecord):
    """
    This  record  is  part  of the Page Settings Block. It specifies if the
    sheet is centred vertically when printed.

    Record VCENTER, BIFF3-BIFF8:

    Offset  Size    Contents
    0       2       0 = Print sheet aligned at top page border
                    1 = Print sheet vertically centred

    """
    _REC_ID = 0x0084

    def __init__(self, is_vert_center):
        self._rec_data = pack('<H', is_vert_center)


class LeftMarginRecord(BiffRecord):
    """
    This  record  is  part of the Page Settings Block. It contains the left
    page margin of the current worksheet.

    Record LEFTMARGIN, BIFF2-BIFF8:

    Offset  Size    Contents
    0       8       Left page margin in inches
                    (IEEE 754 floating-point value, 64bit double precision)

    """
    _REC_ID = 0x0026

    def __init__(self, margin):
        self._rec_data = pack('<d', margin)


class RightMarginRecord(BiffRecord):
    """
    This  record  is  part of the Page Settings Block. It contains the right
    page margin of the current worksheet.

    Offset  Size    Contents
    0       8       Right page margin in inches
                    (IEEE 754 floating-point value, 64?bit double precision)

    """
    _REC_ID = 0x0027

    def __init__(self, margin):
        self._rec_data = pack('<d', margin)

class TopMarginRecord(BiffRecord):
    """
    This  record  is  part of the Page Settings Block. It contains the top
    page margin of the current worksheet.

    Offset  Size    Contents
    0       8       Top page margin in inches
                    (IEEE 754 floating-point value, 64?bit double precision)

    """
    _REC_ID = 0x0028

    def __init__(self, margin):
        self._rec_data = pack('<d', margin)


class BottomMarginRecord(BiffRecord):
    """
    This  record  is  part of the Page Settings Block. It contains the bottom
    page margin of the current worksheet.

    Offset  Size    Contents
    0       8       Bottom page margin in inches
                    (IEEE 754 floating-point value, 64?bit double precision)

    """
    _REC_ID = 0x0029

    def __init__(self, margin):
        self._rec_data = pack('<d', margin)

class SetupPageRecord(BiffRecord):
    """
    This   record   is  part of the Page Settings Block. It stores the page
    format   settings   of   the  current sheet. The pages may be scaled in
    percent   or  by  using  an  absolute  number of pages. This setting is
    located   in  the  WSBOOL  record.  If  pages  are  scaled in  percent,
    the   scaling  factor  in  this  record is used, otherwise the "Fit  to
    pages"  values. One of the "Fit to pages" values may be 0. In this case
    the sheet is scaled to fit only to the other value.

    Record SETUP, BIFF5-BIFF8:

    Offset      Size    Contents
    0           2       Paper size (see below)
    2           2       Scaling factor in percent
    4           2       Start page number
    6           2       Fit worksheet width to this number of pages
                        (0 = use as many as needed)
    8           2       Fit worksheet height to this number of pages
                        (0 = use as many as needed)
    10          2       Option flags:
                        Bit     Mask        Contents
                        0       0001H       0 = Print pages in columns
                                            1 = Print pages in rows
                        1       0002H       0 = Landscape
                                            1 = Portrait
                        2       0004H       1 = Paper size, scaling factor,
                                            paper orientation (portrait/landscape),
                                            print resolution and number of copies
                                            are not initialised
                        3       0008H       0 = Print coloured
                                            1 = Print black and white
                        4       0010H       0 = Default print quality
                                            1 = Draft quality
                        5       0020H       0 = Do not print cell notes
                                            1 = Print cell notes
                        6       0040H       0 = Paper orientation setting is valid
                                            1 = Paper orientation setting not
                                            initialised
                        7       0080H       0 = Automatic page numbers
                                            1 = Use start page number
                        The following flags are valid for BIFF8 only:
                        9       0200H       0 = Print notes as displayed
                                            1 = Print notes at end of sheet
                        11-10   0C00H       00 = Print errors as displayed
                                            01 = Do not print errors
                                            10 = Print errors as "--"
                                            11 = Print errors as "#N/A!"
    12          2       Print resolution in dpi
    14          2       Vertical print resolution in dpi
    16          8       Header margin (IEEE 754 floating-point value,
                        64bit double precision)
    24          8       Footer margin (IEEE 754 floating-point value,
                        64bit double precision)
    32          2       Number of copies to print


    PAPER TYPES:

    Index   Paper type              Paper size
    0       Undefined
    1       Letter                  8 1/2" x 11"
    2       Letter small            8 1/2" x 11"
    3       Tabloid                 11" x 17"
    4       Ledger                  17" x 11"
    5       Legal                   8 1/2" x 14"
    6       Statement               5 1/2" x 8 1/2"
    7       Executive               7 1/4" x 10 1/2"
    8       A3                      297mm x 420mm
    9       A4                      210mm x 297mm
    10      A4 small                210mm x 297mm
    11      A5                      148mm x 210mm
    12      B4 (JIS)                257mm x 364mm
    13      B5 (JIS)                182mm x 257mm
    14      Folio                   8 1/2" x 13"
    15      Quarto                  215mm x 275mm
    16      10x14                   10" x 14"
    17      11x17                   11" x 17"
    18      Note                    8 1/2" x 11"
    19      Envelope #9             3 7/8" x 8 7/8"
    20      Envelope #10            4 1/8" x 9 1/2"
    21      Envelope #11            4 1/2" x 10 3/8"
    22      Envelope #12            4 3/4" x 11"
    23      Envelope #14            5" x 11 1/2"
    24      C                       17" x 22"
    25      D                       22" x 34"
    26      E                       34" x 44"
    27      Envelope DL             110mm x 220mm
    28      Envelope C5             162mm x 229mm
    29      Envelope C3             324mm x 458mm
    30      Envelope C4             229mm x 324mm
    31      Envelope C6             114mm x 162mm
    32      Envelope C6/C5          114mm x 229mm
    33      B4 (ISO)                250mm x 353mm
    34      B5 (ISO)                176mm x 250mm
    35      B6 (ISO)                125mm x 176mm
    36      Envelope Italy          110mm x 230mm
    37      Envelope Monarch        3 7/8" x 7 1/2"
    38      63/4 Envelope           3 5/8" x 6 1/2"
    39      US Standard Fanfold     14 7/8" x 11"
    40      German Std. Fanfold     8 1/2" x 12"
    41      German Legal Fanfold    8 1/2" x 13"
    42      B4 (ISO)                250mm x 353mm
    43      Japanese Postcard       100mm x 148mm
    44      9x11                    9" x 11"
    45      10x11                   10" x 11"
    46      15x11                   15" x 11"
    47      Envelope Invite         220mm x 220mm
    48      Undefined
    49      Undefined
    50      Letter Extra            9 1/2" x 12"
    51      Legal Extra             9 1/2" x 15"
    52      Tabloid Extra           11 11/16" x 18"
    53      A4 Extra                235mm x 322mm
    54      Letter Transverse       8 1/2" x 11"
    55      A4 Transverse           210mm x 297mm
    56      Letter Extra Transv.    9 1/2" x 12"
    57      Super A/A4              227mm x 356mm
    58      Super B/A3              305mm x 487mm
    59      Letter Plus             8 1/2" x 12 11/16"
    60      A4 Plus                 210mm x 330mm
    61      A5 Transverse           148mm x 210mm
    62      B5 (JIS) Transverse     182mm x 257mm
    63      A3 Extra                322mm x 445mm
    64      A5 Extra                174mm x 235mm
    65      B5 (ISO) Extra          201mm x 276mm
    66      A2                      420mm x 594mm
    67      A3 Transverse           297mm x 420mm
    68      A3 Extra Transverse     322mm x 445mm
    69      Dbl. Japanese Postcard  200mm x 148mm
    70      A6                      105mm x 148mm
    71
    72
    73
    74
    75      Letter Rotated          11" x 8 1/2"
    76      A3 Rotated              420mm x 297mm
    77      A4 Rotated              297mm x 210mm
    78      A5 Rotated              210mm x 148mm
    79      B4 (JIS) Rotated        364mm x 257mm
    80      B5 (JIS) Rotated        257mm x 182mm
    81      Japanese Postcard Rot.  148mm x 100mm
    82      Dbl. Jap. Postcard Rot. 148mm x 200mm
    83      A6 Rotated              148mm x 105mm
    84
    85
    86
    87
    88      B6 (JIS)                128mm x 182mm
    89      B6 (JIS) Rotated        182mm x 128mm
    90      12x11                   12" x 11"

    """
    _REC_ID = 0x00A1
    def __init__(self, paper, scaling, start_num, fit_width_to, fit_height_to,
                    options,
                    hres, vres,
                    header_margin, footer_margin,
                    num_copies):
        self._rec_data = pack('<8H2dH', paper, scaling, start_num,
                                        fit_width_to, fit_height_to, \
                                        options,
                                        hres, vres,
                                        header_margin, footer_margin,
                                        num_copies)

class NameRecord(BiffRecord):
    """
    This record is part of a Link Table. It contains the name and the token
    array of an internal defined name. Token arrays of defined names
    contain tokens with aberrant token classes.

    Record NAME, BIFF5/BIFF7:
    Offset      Size    Contents
       0          2     Option flags, see below
       2          1     Keyboard shortcut (only for command macro names, see below)
       3          1     Length of the name (character count, ln)
       4          2     Size of the formula data (sz)
       6          2     0 = Global name, otherwise index to EXTERNSHEET record (one-based)
       8          2     0 = Global name, otherwise index to sheet (one-based)
      10          1     Length of menu text (character count, lm)
      11          1     Length of description text (character count, ld)
      12          1     Length of help topic text (character count, lh)
      13          1     Length of status bar text (character count, ls)
      14         ln     Character array of the name
    14+ln        sz     Formula data (RPN token array without size field, 4)
  14+ln+sz       lm     Character array of menu text
     var.        ld     Character array of description text
     var.        lh     Character array of help topic text
     var.        ls     Character array of status bar text

    Record NAME, BIFF8:
    Offset      Size Contents
       0          2  Option flags, see below
       2          1  Keyboard shortcut (only for command macro names, see below)
       3          1  Length of the name (character count, ln)
       4          2  Size of the formula data (sz)
       6          2  Not used
       8          2  0 = Global name, otherwise index to sheet (one-based)
      10          1  Length of menu text (character count, lm)
      11          1  Length of description text (character count, ld)
      12          1  Length of help topic text (character count, lh)
      13          1  Length of status bar text (character count, ls)
      14        var. Name (Unicode string without length field, 3.4)
     var.        sz  Formula data (RPN token array without size field, 4)
    [var.]      var. (optional, only if lm > 0) Menu text (Unicode string without length field, 3.4)
    [var.]      var. (optional, only if ld > 0) Description text (Unicode string without length field, 3.4)
    [var.]      var. (optional, only if lh > 0) Help topic text (Unicode string without length field, 3.4)
    [var.]      var. (optional, only if ls > 0) Status bar text (Unicode string without length field, 3.4)
    """
    _REC_ID = 0x0018

    def __init__(self, options, keyboard_shortcut, name, sheet_index, rpn, menu_text='', desc_text='', help_text='', status_text=''):
        if type(name) == int:
            uname = chr(name)
        else:
            uname = upack1(name)[1:]
        uname_len = len(uname)

        #~ self._rec_data = pack('<HBBHHHBBBB%ds%ds' % (uname_len, len(rpn)), options, keyboard_shortcut, uname_len, len(rpn), 0x0000, sheet_index, len(menu_text), len(desc_text), len(help_text), len(status_text), uname, rpn) + menu_text + desc_text + help_text + status_text
        self._rec_data = pack('<HBBHHHBBBBB%ds%ds' % (uname_len, len(rpn)), options, keyboard_shortcut, uname_len, len(rpn), 0x0000, sheet_index, 0x00, len(menu_text), len(desc_text), len(help_text), len(status_text), uname, rpn) + menu_text + desc_text + help_text + status_text

# Excel (both 2003 and 2007) don't like refs
# split over a record boundary, which is what the
# standard BiffRecord.get method does.

# 8224 max data bytes in a BIFF record
# 6 bytes per ref
# 1370 = floor((8224 - 2) / 6.0) max refs in a record

_maxRefPerRecord = 1370

class ExternSheetRecord(BiffRecord):
    """
    In BIFF8 the record stores a list with indexes to SUPBOOK
    records (list of REF structures, 6.100). See 5.10.3 for
    details about external references in BIFF8.

    Record EXTERNSHEET, BIFF8:
    Offset          Size      Contents
       0             2        Number of following REF structures (nm)
       2           6nm        List of nm REF structures. Each REF contains the following data:
                              Offset     Size     Contents
                                 0         2      Index to SUPBOOK record
                                 2         2      Index to first SUPBOOK sheet
                                 4         2      Index to last SUPBOOK sheet
    """
    _REC_ID = 0x0017

    def __init__(self, refs):

        # do we always need this ref? or only if there are no refs?
        # (I believe that if there are no refs then we should not generate the link table - Ruben)
        #refs.insert(0, (0,0,0))

        self.refs = refs

    def get(self):
        res = []
        nrefs = len(self.refs)
        for idx in xrange(0, nrefs, _maxRefPerRecord):
            chunk = self.refs[idx:idx+_maxRefPerRecord]
            krefs = len(chunk)
            if idx: # CONTINUE record
                header = pack("<HH", 0x003C, 6 * krefs)
            else: # ExternSheetRecord
                header = pack("<HHH", self._REC_ID, 6 * krefs + 2, nrefs)
            res.append(header)
            res.extend([pack("<HHH", *r) for r in chunk])
        return ''.join(res)

class SupBookRecord(BiffRecord):
    """
    This record mainly stores the URL of an external document
    and a list of sheet names inside this document. Furthermore
    it is used to store DDE and OLE object links, or to indicate
    an internal 3D reference or an add-in function. See 5.10.3
    for details about external references in BIFF8.

    """
    _REC_ID = 0x01AE

class InternalReferenceSupBookRecord(SupBookRecord):
    """
    In each file occurs a SUPBOOK that is used for internal 3D
    references. It stores the number of sheets of the own document.

    Record SUPBOOK for 3D references, BIFF8:
    Offset         Size   Contents
      0             2     Number of sheets in this document
      2             2     01H 04H (relict of BIFF5/BIFF7, the byte string "<04H>", see 3.9.1)

    """

    def __init__(self, num_sheets):
        self._rec_data = pack('<HBB', num_sheets, 0x01, 0x04)

class XcallSupBookRecord(SupBookRecord):
    """
    Add-in function names are stored in EXTERNNAME records following this record.

    Offset  Size    Contents
    0       2       0001H
    2       2       01H 3AH (relict of BIFF5, the byte string ':', see EXTERNSHEET record, 5.41)

    """

    def __init__(self):
        self._rec_data = pack('<HBB', 1, 0x01, 0x3A)


class ExternnameRecord(BiffRecord):
    """
    Record EXTERNNAME for external names and Analysis add-in functions, BIFF5-BIFF8:
    Offset  Size    Contents
    0       2       Option flags (see below)
    2       2       0 for global names, or:
                    BIFF5: One-based index to EXTERNSHEET record containing the sheet name,
                    BIFF8: One-based index to sheet list in preceding EXTERNALBOOK record.
    4       2       Not used
    6       var.    BIFF5: Name (byte string, 8-bit string length, ?2.5.2).
                    BIFF8: Name (Unicode string, 8-bit string length, ?2.5.3).
                    See DEFINEDNAME record (?5.33) for a list of built-in names, if the built-in flag is set
                    in the option flags above.
    var.    var.    Formula data (RPN token array, ?3)

    Option flags for external names (BIFF5-BIFF8)
    Bit     Mask    Contents
    0       0001H   0 = Standard name; 1 = Built-in name
    1       0002H   0 = Manual link; 1 = Automatic link (DDE links and OLE links only)
    2       0004H   1 = Picture link (DDE links and OLE links only)
    3       0008H   1 = This is the “StdDocumentName” identifier (DDE links only)
    4       0010H   1 = OLE link
    14-5    7FE0H   Clipboard format of last successful update (DDE links and OLE links only)
    15      8000H   1 = Iconified picture link (BIFF8 OLE links only)
    """
    _REC_ID = 0x0023

    def __init__(self, options=0, index=0, name=None, fmla=None):
        self._rec_data = pack('<HHH', options, index, 0) + upack1(name) + fmla


########NEW FILE########
__FILENAME__ = Bitmap
# -*- coding: windows-1251 -*-

#  Portions are Copyright (C) 2005 Roman V. Kiseliov
#  Portions are Copyright (c) 2004 Evgeny Filatov <fufff@users.sourceforge.net>
#  Portions are Copyright (c) 2002-2004 John McNamara (Perl Spreadsheet::WriteExcel)

from BIFFRecords import BiffRecord
from struct import pack, unpack


def _size_col(sheet, col):
    return sheet.col_width(col)


def _size_row(sheet, row):
    return sheet.row_height(row)


def _position_image(sheet, row_start, col_start, x1, y1, width, height):
    """Calculate the vertices that define the position of the image as required by
    the OBJ record.

             +------------+------------+
             |     A      |      B     |
       +-----+------------+------------+
       |     |(x1,y1)     |            |
       |  1  |(A1)._______|______      |
       |     |    |              |     |
       |     |    |              |     |
       +-----+----|    BITMAP    |-----+
       |     |    |              |     |
       |  2  |    |______________.     |
       |     |            |        (B2)|
       |     |            |     (x2,y2)|
       +---- +------------+------------+

    Example of a bitmap that covers some of the area from cell A1 to cell B2.

    Based on the width and height of the bitmap we need to calculate 8 vars:
        col_start, row_start, col_end, row_end, x1, y1, x2, y2.
    The width and height of the cells are also variable and have to be taken into
    account.
    The values of col_start and row_start are passed in from the calling
    function. The values of col_end and row_end are calculated by subtracting
    the width and height of the bitmap from the width and height of the
    underlying cells.
    The vertices are expressed as a percentage of the underlying cell width as
    follows (rhs values are in pixels):

           x1 = X / W *1024
           y1 = Y / H *256
           x2 = (X-1) / W *1024
           y2 = (Y-1) / H *256

           Where:  X is distance from the left side of the underlying cell
                   Y is distance from the top of the underlying cell
                   W is the width of the cell
                   H is the height of the cell

    Note: the SDK incorrectly states that the height should be expressed as a
    percentage of 1024.

    col_start  - Col containing upper left corner of object
    row_start  - Row containing top left corner of object
    x1  - Distance to left side of object
    y1  - Distance to top of object
    width  - Width of image frame
    height  - Height of image frame

    """
    # Adjust start column for offsets that are greater than the col width
    while x1 >= _size_col(sheet, col_start):
        x1 -= _size_col(sheet, col_start)
        col_start += 1
    # Adjust start row for offsets that are greater than the row height
    while y1 >= _size_row(sheet, row_start):
        y1 -= _size_row(sheet, row_start)
        row_start += 1
    # Initialise end cell to the same as the start cell
    row_end = row_start   # Row containing bottom right corner of object
    col_end = col_start   # Col containing lower right corner of object
    width = width + x1 - 1
    height = height + y1 - 1
    # Subtract the underlying cell widths to find the end cell of the image
    while (width >= _size_col(sheet, col_end)):
        width -= _size_col(sheet, col_end)
        col_end += 1
    # Subtract the underlying cell heights to find the end cell of the image
    while (height >= _size_row(sheet, row_end)):
        height -= _size_row(sheet, row_end)
        row_end += 1
    # Bitmap isn't allowed to start or finish in a hidden cell, i.e. a cell
    # with zero height or width.
    if ((_size_col(sheet, col_start) == 0) or (_size_col(sheet, col_end) == 0)
            or (_size_row(sheet, row_start) == 0) or (_size_row(sheet, row_end) == 0)):
        return
    # Convert the pixel values to the percentage value expected by Excel
    x1 = int(float(x1) / _size_col(sheet, col_start) * 1024)
    y1 = int(float(y1) / _size_row(sheet, row_start) * 256)
    # Distance to right side of object
    x2 = int(float(width) / _size_col(sheet, col_end) * 1024)
    # Distance to bottom of object
    y2 = int(float(height) / _size_row(sheet, row_end) * 256)
    return (col_start, x1, row_start, y1, col_end, x2, row_end, y2)


class ObjBmpRecord(BiffRecord):
    _REC_ID = 0x005D    # Record identifier

    def __init__(self, row, col, sheet, im_data_bmp, x, y, scale_x, scale_y):
        # Scale the frame of the image.
        width = im_data_bmp.width * scale_x
        height = im_data_bmp.height * scale_y

        # Calculate the vertices of the image and write the OBJ record
        coordinates = _position_image(sheet, row, col, x, y, width, height)
        # print coordinates
        col_start, x1, row_start, y1, col_end, x2, row_end, y2 = coordinates

        """Store the OBJ record that precedes an IMDATA record. This could be generalise
        to support other Excel objects.

        """
        cObj = 0x0001      # Count of objects in file (set to 1)
        OT = 0x0008        # Object type. 8 = Picture
        id = 0x0001        # Object ID
        grbit = 0x0614     # Option flags
        colL = col_start    # Col containing upper left corner of object
        dxL = x1            # Distance from left side of cell
        rwT = row_start     # Row containing top left corner of object
        dyT = y1            # Distance from top of cell
        colR = col_end      # Col containing lower right corner of object
        dxR = x2            # Distance from right of cell
        rwB = row_end       # Row containing bottom right corner of object
        dyB = y2            # Distance from bottom of cell
        cbMacro = 0x0000    # Length of FMLA structure
        Reserved1 = 0x0000  # Reserved
        Reserved2 = 0x0000  # Reserved
        icvBack = 0x09      # Background colour
        icvFore = 0x09      # Foreground colour
        fls = 0x00          # Fill pattern
        fAuto = 0x00        # Automatic fill
        icv = 0x08          # Line colour
        lns = 0xff          # Line style
        lnw = 0x01          # Line weight
        fAutoB = 0x00       # Automatic border
        frs = 0x0000        # Frame style
        cf = 0x0009         # Image format, 9 = bitmap
        Reserved3 = 0x0000  # Reserved
        cbPictFmla = 0x0000 # Length of FMLA structure
        Reserved4 = 0x0000  # Reserved
        grbit2 = 0x0001     # Option flags
        Reserved5 = 0x0000  # Reserved

        data = pack("<L", cObj)
        data += pack("<H", OT)
        data += pack("<H", id)
        data += pack("<H", grbit)
        data += pack("<H", colL)
        data += pack("<H", dxL)
        data += pack("<H", rwT)
        data += pack("<H", dyT)
        data += pack("<H", colR)
        data += pack("<H", dxR)
        data += pack("<H", rwB)
        data += pack("<H", dyB)
        data += pack("<H", cbMacro)
        data += pack("<L", Reserved1)
        data += pack("<H", Reserved2)
        data += pack("<B", icvBack)
        data += pack("<B", icvFore)
        data += pack("<B", fls)
        data += pack("<B", fAuto)
        data += pack("<B", icv)
        data += pack("<B", lns)
        data += pack("<B", lnw)
        data += pack("<B", fAutoB)
        data += pack("<H", frs)
        data += pack("<L", cf)
        data += pack("<H", Reserved3)
        data += pack("<H", cbPictFmla)
        data += pack("<H", Reserved4)
        data += pack("<H", grbit2)
        data += pack("<L", Reserved5)

        self._rec_data = data

def _process_bitmap(bitmap):
    """Convert a 24 bit bitmap into the modified internal format used by Windows.
    This is described in BITMAPCOREHEADER and BITMAPCOREINFO structures in the
    MSDN library.

    """
    # Open file and binmode the data in case the platform needs it.
    fh = file(bitmap, "rb")
    try:
        # Slurp the file into a string.
        data = fh.read()
    finally:
        fh.close()
    # Check that the file is big enough to be a bitmap.
    if len(data) <= 0x36:
        raise Exception("bitmap doesn't contain enough data.")
    # The first 2 bytes are used to identify the bitmap.
    if (data[:2] != "BM"):
        raise Exception("bitmap doesn't appear to to be a valid bitmap image.")
    # Remove bitmap data: ID.
    data = data[2:]
    # Read and remove the bitmap size. This is more reliable than reading
    # the data size at offset 0x22.
    #
    size = unpack("<L", data[:4])[0]
    size -=  0x36   # Subtract size of bitmap header.
    size +=  0x0C   # Add size of BIFF header.
    data = data[4:]
    # Remove bitmap data: reserved, offset, header length.
    data = data[12:]
    # Read and remove the bitmap width and height. Verify the sizes.
    width, height = unpack("<LL", data[:8])
    data = data[8:]
    if (width > 0xFFFF):
        raise Exception("bitmap: largest image width supported is 65k.")
    if (height > 0xFFFF):
        raise Exception("bitmap: largest image height supported is 65k.")
    # Read and remove the bitmap planes and bpp data. Verify them.
    planes, bitcount = unpack("<HH", data[:4])
    data = data[4:]
    if (bitcount != 24):
        raise Exception("bitmap isn't a 24bit true color bitmap.")
    if (planes != 1):
        raise Exception("bitmap: only 1 plane supported in bitmap image.")
    # Read and remove the bitmap compression. Verify compression.
    compression = unpack("<L", data[:4])[0]
    data = data[4:]
    if (compression != 0):
        raise Exception("bitmap: compression not supported in bitmap image.")
    # Remove bitmap data: data size, hres, vres, colours, imp. colours.
    data = data[20:]
    # Add the BITMAPCOREHEADER data
    header = pack("<LHHHH", 0x000c, width, height, 0x01, 0x18)
    data = header + data
    return (width, height, size, data)


class ImDataBmpRecord(BiffRecord):
    _REC_ID = 0x007F

    def __init__(self, filename):
        """Insert a 24bit bitmap image in a worksheet. The main record required is
        IMDATA but it must be proceeded by a OBJ record to define its position.

        """
        BiffRecord.__init__(self)

        self.width, self.height, self.size, data = _process_bitmap(filename)
        # Write the IMDATA record to store the bitmap data
        cf = 0x09
        env = 0x01
        lcb = self.size
        self._rec_data = pack("<HHL", cf, env, lcb) + data



########NEW FILE########
__FILENAME__ = Cell
# -*- coding: windows-1252 -*-

from struct import unpack, pack
import BIFFRecords

class StrCell(object):
    __slots__ = ["rowx", "colx", "xf_idx", "sst_idx"]

    def __init__(self, rowx, colx, xf_idx, sst_idx):
        self.rowx = rowx
        self.colx = colx
        self.xf_idx = xf_idx
        self.sst_idx = sst_idx

    def get_biff_data(self):
        # return BIFFRecords.LabelSSTRecord(self.rowx, self.colx, self.xf_idx, self.sst_idx).get()
        return pack('<5HL', 0x00FD, 10, self.rowx, self.colx, self.xf_idx, self.sst_idx)

class BlankCell(object):
    __slots__ = ["rowx", "colx", "xf_idx"]

    def __init__(self, rowx, colx, xf_idx):
        self.rowx = rowx
        self.colx = colx
        self.xf_idx = xf_idx

    def get_biff_data(self):
        # return BIFFRecords.BlankRecord(self.rowx, self.colx, self.xf_idx).get()
        return pack('<5H', 0x0201, 6, self.rowx, self.colx, self.xf_idx)

class MulBlankCell(object):
    __slots__ = ["rowx", "colx1", "colx2", "xf_idx"]

    def __init__(self, rowx, colx1, colx2, xf_idx):
        self.rowx = rowx
        self.colx1 = colx1
        self.colx2 = colx2
        self.xf_idx = xf_idx

    def get_biff_data(self):
        return BIFFRecords.MulBlankRecord(self.rowx,
            self.colx1, self.colx2, self.xf_idx).get()

class NumberCell(object):
    __slots__ = ["rowx", "colx", "xf_idx", "number"]

    def __init__(self, rowx, colx, xf_idx, number):
        self.rowx = rowx
        self.colx = colx
        self.xf_idx = xf_idx
        self.number = float(number)

    def get_encoded_data(self):
        rk_encoded = 0
        num = self.number

        # The four possible kinds of RK encoding are *not* mutually exclusive.
        # The 30-bit integer variety picks up the most.
        # In the code below, the four varieties are checked in descending order
        # of bangs per buck, or not at all.
        # SJM 2007-10-01

        if -0x20000000 <= num < 0x20000000: # fits in 30-bit *signed* int
            inum = int(num)
            if inum == num: # survives round-trip
                # print "30-bit integer RK", inum, hex(inum)
                rk_encoded = 2 | (inum << 2)
                return 1, rk_encoded

        temp = num * 100

        if -0x20000000 <= temp < 0x20000000:
            # That was step 1: the coded value will fit in
            # a 30-bit signed integer.
            itemp = int(round(temp, 0))
            # That was step 2: "itemp" is the best candidate coded value.
            # Now for step 3: simulate the decoding,
            # to check for round-trip correctness.
            if itemp / 100.0 == num:
                # print "30-bit integer RK*100", itemp, hex(itemp)
                rk_encoded = 3 | (itemp << 2)
                return 1, rk_encoded

        if 0: # Cost of extra pack+unpack not justified by tiny yield.
            packed = pack('<d', num)
            w01, w23 = unpack('<2i', packed)
            if not w01 and not(w23 & 3):
                # 34 lsb are 0
                # print "float RK", w23, hex(w23)
                return 1, w23

            packed100 = pack('<d', temp)
            w01, w23 = unpack('<2i', packed100)
            if not w01 and not(w23 & 3):
                # 34 lsb are 0
                # print "float RK*100", w23, hex(w23)
                return 1, w23 | 1

        #print "Number"
        #print
        return 0, pack('<5Hd', 0x0203, 14, self.rowx, self.colx, self.xf_idx, num)

    def get_biff_data(self):
        isRK, value = self.get_encoded_data()
        if isRK:
            return pack('<5Hi', 0x27E, 10, self.rowx, self.colx, self.xf_idx, value)
        return value # NUMBER record already packed

class BooleanCell(object):
    __slots__ = ["rowx", "colx", "xf_idx", "number"]

    def __init__(self, rowx, colx, xf_idx, number):
        self.rowx = rowx
        self.colx = colx
        self.xf_idx = xf_idx
        self.number = number

    def get_biff_data(self):
        return BIFFRecords.BoolErrRecord(self.rowx,
            self.colx, self.xf_idx, self.number, 0).get()

error_code_map = {
    0x00:  0, # Intersection of two cell ranges is empty
    0x07:  7, # Division by zero
    0x0F: 15, # Wrong type of operand
    0x17: 23, # Illegal or deleted cell reference
    0x1D: 29, # Wrong function or range name
    0x24: 36, # Value range overflow
    0x2A: 42, # Argument or function not available
    '#NULL!' :  0, # Intersection of two cell ranges is empty
    '#DIV/0!':  7, # Division by zero
    '#VALUE!': 36, # Wrong type of operand
    '#REF!'  : 23, # Illegal or deleted cell reference
    '#NAME?' : 29, # Wrong function or range name
    '#NUM!'  : 36, # Value range overflow
    '#N/A!'  : 42, # Argument or function not available
}

class ErrorCell(object):
    __slots__ = ["rowx", "colx", "xf_idx", "number"]

    def __init__(self, rowx, colx, xf_idx, error_string_or_code):
        self.rowx = rowx
        self.colx = colx
        self.xf_idx = xf_idx
        try:
            self.number = error_code_map[error_string_or_code]
        except KeyError:
            raise Exception('Illegal error value (%r)' % error_string_or_code)

    def get_biff_data(self):
        return BIFFRecords.BoolErrRecord(self.rowx,
            self.colx, self.xf_idx, self.number, 1).get()

class FormulaCell(object):
    __slots__ = ["rowx", "colx", "xf_idx", "frmla", "calc_flags"]

    def __init__(self, rowx, colx, xf_idx, frmla, calc_flags=0):
        self.rowx = rowx
        self.colx = colx
        self.xf_idx = xf_idx
        self.frmla = frmla
        self.calc_flags = calc_flags

    def get_biff_data(self):
        return BIFFRecords.FormulaRecord(self.rowx,
            self.colx, self.xf_idx, self.frmla.rpn(), self.calc_flags).get()

# module-level function for *internal* use by the Row module

def _get_cells_biff_data_mul(rowx, cell_items):
    # Return the BIFF data for all cell records in the row.
    # Adjacent BLANK|RK records are combined into MUL(BLANK|RK) records.
    pieces = []
    nitems = len(cell_items)
    i = 0
    while i < nitems:
        icolx, icell = cell_items[i]
        if isinstance(icell, NumberCell):
            isRK, value = icell.get_encoded_data()
            if not isRK:
                pieces.append(value) # pre-packed NUMBER record
                i += 1
                continue
            muldata = [(value, icell.xf_idx)]
            target = NumberCell
        elif isinstance(icell, BlankCell):
            muldata = [icell.xf_idx]
            target = BlankCell
        else:
            pieces.append(icell.get_biff_data())
            i += 1
            continue
        lastcolx = icolx
        j = i
        packed_record = ''
        for j in xrange(i+1, nitems):
            jcolx, jcell = cell_items[j]
            if jcolx != lastcolx + 1:
                nexti = j
                break
            if not isinstance(jcell, target):
                nexti = j
                break
            if target == NumberCell:
                isRK, value = jcell.get_encoded_data()
                if not isRK:
                    packed_record = value
                    nexti = j + 1
                    break
                muldata.append((value, jcell.xf_idx))
            else:
                muldata.append(jcell.xf_idx)
            lastcolx = jcolx
        else:
            nexti = j + 1
        if target == NumberCell:
            if lastcolx == icolx:
                # RK record
                value, xf_idx = muldata[0]
                pieces.append(pack('<5Hi', 0x027E, 10, rowx, icolx, xf_idx, value))
            else:
                # MULRK record
                nc = lastcolx - icolx + 1
                pieces.append(pack('<4H', 0x00BD, 6 * nc + 6, rowx, icolx))
                pieces.append(''.join([pack('<Hi', xf_idx, value) for value, xf_idx in muldata]))
                pieces.append(pack('<H', lastcolx))
        else:
            if lastcolx == icolx:
                # BLANK record
                xf_idx = muldata[0]
                pieces.append(pack('<5H', 0x0201, 6, rowx, icolx, xf_idx))
            else:
                # MULBLANK record
                nc = lastcolx - icolx + 1
                pieces.append(pack('<4H', 0x00BE, 2 * nc + 6, rowx, icolx))
                pieces.append(''.join([pack('<H', xf_idx) for xf_idx in muldata]))
                pieces.append(pack('<H', lastcolx))
        if packed_record:
            pieces.append(packed_record)
        i = nexti
    return ''.join(pieces)


########NEW FILE########
__FILENAME__ = Column
# -*- coding: windows-1252 -*-

from BIFFRecords import ColInfoRecord

class Column(object):
    def __init__(self, colx, parent_sheet):
        if not(isinstance(colx, int) and 0 <= colx <= 255):
            raise ValueError("column index (%r) not an int in range(256)" % colx)
        self._index = colx
        self._parent = parent_sheet
        self._parent_wb = parent_sheet.get_parent()
        self._xf_index = 0x0F

        self.width = 0x0B92
        self.hidden = 0
        self.level = 0
        self.collapse = 0
        self.user_set = 0
        self.best_fit = 0
        self.unused = 0
        
    def set_width(self, width):
        if not(isinstance(width, int) and 0 <= width <= 65535):
            raise ValueError("column width (%r) not an int in range(65536)" % width)
        self._width = width

    def get_width(self):
        return self._width

    width = property(get_width, set_width)

    def set_style(self, style):
        self._xf_index = self._parent_wb.add_style(style)

    def width_in_pixels(self):
        # *** Approximation ****
        return int(round(self.width * 0.0272 + 0.446, 0))

    def get_biff_record(self):
        options =  (self.hidden & 0x01) << 0
        options |= (self.user_set & 0x01) << 1
        options |= (self.best_fit & 0x01) << 2
        options |= (self.level & 0x07) << 8
        options |= (self.collapse & 0x01) << 12

        return ColInfoRecord(self._index, self._index, self.width, self._xf_index, options, self.unused).get()




########NEW FILE########
__FILENAME__ = CompoundDoc
# -*- coding: windows-1252 -*-

import struct
        
# This implementation writes only 'Root Entry', 'Workbook' streams
# and 2 empty streams for aligning directory stream on sector boundary
# 
# LAYOUT:
# 0         header
# 76                MSAT (1st part: 109 SID)
# 512       workbook stream
# ...       additional MSAT sectors if streams' size > about 7 Mb == (109*512 * 128)
# ...       SAT
# ...       directory stream
#
# NOTE: this layout is "ad hoc". It can be more general. RTFM

class XlsDoc:
    SECTOR_SIZE = 0x0200
    MIN_LIMIT   = 0x1000

    SID_FREE_SECTOR  = -1
    SID_END_OF_CHAIN = -2
    SID_USED_BY_SAT  = -3
    SID_USED_BY_MSAT = -4

    def __init__(self):
        #self.book_stream = ''                # padded
        self.book_stream_sect = []

        self.dir_stream = ''
        self.dir_stream_sect = []

        self.packed_SAT = ''
        self.SAT_sect = []

        self.packed_MSAT_1st = ''
        self.packed_MSAT_2nd = ''
        self.MSAT_sect_2nd = []

        self.header = ''

    def _build_directory(self): # align on sector boundary
        self.dir_stream = ''

        dentry_name      = '\x00'.join('Root Entry\x00') + '\x00'
        dentry_name_sz   = len(dentry_name)
        dentry_name_pad  = '\x00'*(64 - dentry_name_sz)
        dentry_type      = 0x05 # root storage
        dentry_colour    = 0x01 # black
        dentry_did_left  = -1
        dentry_did_right = -1
        dentry_did_root  = 1
        dentry_start_sid = -2
        dentry_stream_sz = 0

        self.dir_stream += struct.pack('<64s H 2B 3l 9L l L L',
           dentry_name + dentry_name_pad,
           dentry_name_sz,
           dentry_type,
           dentry_colour,
           dentry_did_left, 
           dentry_did_right,
           dentry_did_root,
           0, 0, 0, 0, 0, 0, 0, 0, 0,
           dentry_start_sid,
           dentry_stream_sz,
           0
        )

        dentry_name      = '\x00'.join('Workbook\x00') + '\x00'
        dentry_name_sz   = len(dentry_name)
        dentry_name_pad  = '\x00'*(64 - dentry_name_sz)
        dentry_type      = 0x02 # user stream
        dentry_colour    = 0x01 # black
        dentry_did_left  = -1
        dentry_did_right = -1
        dentry_did_root  = -1
        dentry_start_sid = 0     
        dentry_stream_sz = self.book_stream_len

        self.dir_stream += struct.pack('<64s H 2B 3l 9L l L L',
           dentry_name + dentry_name_pad,
           dentry_name_sz,
           dentry_type,
           dentry_colour,
           dentry_did_left, 
           dentry_did_right,
           dentry_did_root,
           0, 0, 0, 0, 0, 0, 0, 0, 0, 
           dentry_start_sid,
           dentry_stream_sz,
           0
        )
        
        # padding
        dentry_name      = ''
        dentry_name_sz   = len(dentry_name)
        dentry_name_pad  = '\x00'*(64 - dentry_name_sz)
        dentry_type      = 0x00 # empty
        dentry_colour    = 0x01 # black
        dentry_did_left  = -1
        dentry_did_right = -1
        dentry_did_root  = -1
        dentry_start_sid = -2
        dentry_stream_sz = 0

        self.dir_stream += struct.pack('<64s H 2B 3l 9L l L L',
           dentry_name + dentry_name_pad,
           dentry_name_sz,
           dentry_type,
           dentry_colour,
           dentry_did_left, 
           dentry_did_right,
           dentry_did_root,
           0, 0, 0, 0, 0, 0, 0, 0, 0,
           dentry_start_sid,
           dentry_stream_sz,
           0
        ) * 2
    
    def _build_sat(self):
        # Build SAT
        book_sect_count = self.book_stream_len >> 9
        dir_sect_count  = len(self.dir_stream) >> 9
        
        total_sect_count     = book_sect_count + dir_sect_count
        SAT_sect_count       = 0
        MSAT_sect_count      = 0
        SAT_sect_count_limit = 109
        while total_sect_count > 128*SAT_sect_count or SAT_sect_count > SAT_sect_count_limit:
            SAT_sect_count   += 1
            total_sect_count += 1
            if SAT_sect_count > SAT_sect_count_limit:
                MSAT_sect_count      += 1
                total_sect_count     += 1
                SAT_sect_count_limit += 127


        SAT = [self.SID_FREE_SECTOR]*128*SAT_sect_count

        sect = 0
        while sect < book_sect_count - 1:
            self.book_stream_sect.append(sect)
            SAT[sect] = sect + 1
            sect += 1
        self.book_stream_sect.append(sect)
        SAT[sect] = self.SID_END_OF_CHAIN
        sect += 1

        while sect < book_sect_count + MSAT_sect_count:
            self.MSAT_sect_2nd.append(sect)
            SAT[sect] = self.SID_USED_BY_MSAT
            sect += 1

        while sect < book_sect_count + MSAT_sect_count + SAT_sect_count:
            self.SAT_sect.append(sect)            
            SAT[sect] = self.SID_USED_BY_SAT
            sect += 1

        while sect < book_sect_count + MSAT_sect_count + SAT_sect_count + dir_sect_count - 1:
            self.dir_stream_sect.append(sect)
            SAT[sect] = sect + 1
            sect += 1
        self.dir_stream_sect.append(sect)
        SAT[sect] = self.SID_END_OF_CHAIN
        sect += 1

        self.packed_SAT = struct.pack('<%dl' % (SAT_sect_count*128), *SAT)

        MSAT_1st = [self.SID_FREE_SECTOR]*109
        for i, SAT_sect_num in zip(range(0, 109), self.SAT_sect):
            MSAT_1st[i] = SAT_sect_num
        self.packed_MSAT_1st = struct.pack('<109l', *MSAT_1st)

        MSAT_2nd = [self.SID_FREE_SECTOR]*128*MSAT_sect_count
        if MSAT_sect_count > 0:
            MSAT_2nd[- 1] = self.SID_END_OF_CHAIN

        i = 109
        msat_sect = 0
        sid_num = 0
        while i < SAT_sect_count:
            if (sid_num + 1) % 128 == 0:
                #print 'link: ',
                msat_sect += 1
                if msat_sect < len(self.MSAT_sect_2nd):
                    MSAT_2nd[sid_num] = self.MSAT_sect_2nd[msat_sect]
            else:
                #print 'sid: ',
                MSAT_2nd[sid_num] = self.SAT_sect[i]
                i += 1
            #print sid_num, MSAT_2nd[sid_num]
            sid_num += 1

        self.packed_MSAT_2nd = struct.pack('<%dl' % (MSAT_sect_count*128), *MSAT_2nd)

        #print vars()
        #print zip(range(0, sect), SAT)
        #print self.book_stream_sect
        #print self.MSAT_sect_2nd
        #print MSAT_2nd
        #print self.SAT_sect
        #print self.dir_stream_sect


    def _build_header(self):
        doc_magic             = '\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'
        file_uid              = '\x00'*16
        rev_num               = '\x3E\x00'
        ver_num               = '\x03\x00'
        byte_order            = '\xFE\xFF'
        log_sect_size         = struct.pack('<H', 9)
        log_short_sect_size   = struct.pack('<H', 6)
        not_used0             = '\x00'*10
        total_sat_sectors     = struct.pack('<L', len(self.SAT_sect))
        dir_start_sid         = struct.pack('<l', self.dir_stream_sect[0])
        not_used1             = '\x00'*4        
        min_stream_size       = struct.pack('<L', 0x1000)
        ssat_start_sid        = struct.pack('<l', -2)
        total_ssat_sectors    = struct.pack('<L', 0)

        if len(self.MSAT_sect_2nd) == 0:
            msat_start_sid        = struct.pack('<l', -2)
        else:
            msat_start_sid        = struct.pack('<l', self.MSAT_sect_2nd[0])

        total_msat_sectors    = struct.pack('<L', len(self.MSAT_sect_2nd))

        self.header =       ''.join([  doc_magic,
                                        file_uid,
                                        rev_num,
                                        ver_num,
                                        byte_order,
                                        log_sect_size,
                                        log_short_sect_size,
                                        not_used0,
                                        total_sat_sectors,
                                        dir_start_sid,
                                        not_used1,
                                        min_stream_size,
                                        ssat_start_sid,
                                        total_ssat_sectors,
                                        msat_start_sid,
                                        total_msat_sectors
                                    ])
                                        

    def save(self, file_name_or_filelike_obj, stream):
        # 1. Align stream on 0x1000 boundary (and therefore on sector boundary)
        padding = '\x00' * (0x1000 - (len(stream) % 0x1000))
        self.book_stream_len = len(stream) + len(padding)

        self._build_directory()
        self._build_sat()
        self._build_header()
        
        f = file_name_or_filelike_obj
        we_own_it = not hasattr(f, 'write')
        if we_own_it:
            f = open(file_name_or_filelike_obj, 'w+b')
        f.write(self.header)
        f.write(self.packed_MSAT_1st)
        # There are reports of large writes failing when writing to "network shares" on Windows.
        # MS says in KB899149 that it happens at 32KB less than 64MB.
        # This is said to be alleviated by using "w+b" mode instead of "wb".
        # One xlwt user has reported anomalous results at much smaller sizes,
        # The fallback is to write the stream in 4 MB chunks.
        try:
            f.write(stream)
        except IOError, e:
            if e.errno != 22: # "Invalid argument" i.e. 'stream' is too big
                raise # some other problem
            chunk_size = 4 * 1024 * 1024
            for offset in xrange(0, len(stream), chunk_size):
                f.write(buffer(stream, offset, chunk_size))
        f.write(padding)
        f.write(self.packed_MSAT_2nd)
        f.write(self.packed_SAT)
        f.write(self.dir_stream)
        if we_own_it:
            f.close()

########NEW FILE########
__FILENAME__ = big-16Mb
#!/usr/bin/env python
# tries stress SST, SAT and MSAT

from time import *
from xlwt.Workbook import *
from xlwt.Style import *

style = XFStyle()

wb = Workbook()
ws0 = wb.add_sheet('0')

colcount = 200 + 1
rowcount = 6000 + 1

t0 = time()
print "\nstart: %s" % ctime(t0)

print "Filling..."
for col in xrange(colcount):
    print "[%d]" % col, 
    for row in xrange(rowcount):
        #ws0.write(row, col, "BIG(%d, %d)" % (row, col))
        ws0.write(row, col, "BIG")

t1 = time() - t0
print "\nsince starting elapsed %.2f s" % (t1)

print "Storing..."
wb.save('big-16Mb.xls')

t2 = time() - t0
print "since starting elapsed %.2f s" % (t2)



########NEW FILE########
__FILENAME__ = big-35Mb
#!/usr/bin/env python
# tries stress SST, SAT and MSAT

from time import *
from xlwt import *

style = XFStyle()

wb = Workbook()
ws0 = wb.add_sheet('0')

colcount = 200 + 1
rowcount = 6000 + 1

t0 = time()

for col in xrange(colcount):
    for row in xrange(rowcount):
        ws0.write(row, col, "BIG(%d, %d)" % (row, col))

t1 = time() - t0
print "\nsince starting elapsed %.2f s" % (t1)

print "Storing..."
wb.save('big-35Mb.xls')

t2 = time() - t0
print "since starting elapsed %.2f s" % (t2)



########NEW FILE########
__FILENAME__ = blanks
#!/usr/bin/env python
# -*- coding: windows-1251 -*-
# Copyright (C) 2005 Kiseliov Roman

from xlwt import *

font0 = Font()
font0.name = 'Times New Roman'
font0.struck_out = True
font0.bold = True

style0 = XFStyle()
style0.font = font0


wb = Workbook()
ws0 = wb.add_sheet('0')

ws0.write(1, 1, 'Test', style0)

for i in range(0, 0x53):
    borders = Borders()
    borders.left = i
    borders.right = i
    borders.top = i
    borders.bottom = i

    style = XFStyle()
    style.borders = borders

    ws0.write(i, 2, '', style)
    ws0.write(i, 3, hex(i), style0)

ws0.write_merge(5, 8, 6, 10, "")

wb.save('blanks.xls')

########NEW FILE########
__FILENAME__ = col_width
#!/usr/bin/env python
# -*- coding: windows-1251 -*-
# Copyright (C) 2005 Kiseliov Roman
__rev_id__ = """$Id$"""


from xlwt import *

w = Workbook()
ws = w.add_sheet('Hey, Dude')

for i in range(6, 80):
    fnt = Font()
    fnt.height = i*20
    style = XFStyle()
    style.font = fnt
    ws.write(1, i, 'Test')
    ws.col(i).width = 0x0d00 + i
w.save('col_width.xls')

########NEW FILE########
__FILENAME__ = country
#!/usr/bin/env python
# -*- coding: windows-1252 -*-
# Copyright (C) 2007 John Machin

from xlwt import *

w = Workbook()
w.country_code = 61
ws = w.add_sheet('AU')
w.save('country.xls')

########NEW FILE########
__FILENAME__ = dates
#!/usr/bin/env python
# -*- coding: windows-1251 -*-
# Copyright (C) 2005 Kiseliov Roman

from xlwt import *
from datetime import datetime

w = Workbook()
ws = w.add_sheet('Hey, Dude')

fmts = [
    'M/D/YY',
    'D-MMM-YY',
    'D-MMM',
    'MMM-YY',
    'h:mm AM/PM',
    'h:mm:ss AM/PM',
    'h:mm',
    'h:mm:ss',
    'M/D/YY h:mm',
    'mm:ss',
    '[h]:mm:ss',
    'mm:ss.0',
]

i = 0
for fmt in fmts:
    ws.write(i, 0, fmt)

    style = XFStyle()
    style.num_format_str = fmt

    ws.write(i, 4, datetime.now(), style)

    i += 1

w.save('dates.xls')

########NEW FILE########
__FILENAME__ = format
#!/usr/bin/env python
# -*- coding: windows-1251 -*-
# Copyright (C) 2005 Kiseliov Roman

from xlwt import *

font0 = Font()
font0.name = 'Times New Roman'
font0.struck_out = True
font0.bold = True

style0 = XFStyle()
style0.font = font0


wb = Workbook()
ws0 = wb.add_sheet('0')

ws0.write(1, 1, 'Test', style0)

for i in range(0, 0x53):
    fnt = Font()
    fnt.name = 'Arial'
    fnt.colour_index = i
    fnt.outline = True

    borders = Borders()
    borders.left = i

    style = XFStyle()
    style.font = fnt
    style.borders = borders

    ws0.write(i, 2, 'colour', style)
    ws0.write(i, 3, hex(i), style0)


wb.save('format.xls')

########NEW FILE########
__FILENAME__ = formulas
#!/usr/bin/env python
# -*- coding: windows-1251 -*-
# Copyright (C) 2005 Kiseliov Roman

from xlwt import *

w = Workbook()
ws = w.add_sheet('F')

ws.write(0, 0, Formula("-(1+1)"))
ws.write(1, 0, Formula("-(1+1)/(-2-2)"))
ws.write(2, 0, Formula("-(134.8780789+1)"))
ws.write(3, 0, Formula("-(134.8780789e-10+1)"))
ws.write(4, 0, Formula("-1/(1+1)+9344"))

ws.write(0, 1, Formula("-(1+1)"))
ws.write(1, 1, Formula("-(1+1)/(-2-2)"))
ws.write(2, 1, Formula("-(134.8780789+1)"))
ws.write(3, 1, Formula("-(134.8780789e-10+1)"))
ws.write(4, 1, Formula("-1/(1+1)+9344"))

ws.write(0, 2, Formula("A1*B1"))
ws.write(1, 2, Formula("A2*B2"))
ws.write(2, 2, Formula("A3*B3"))
ws.write(3, 2, Formula("A4*B4*sin(pi()/4)"))
ws.write(4, 2, Formula("A5%*B5*pi()/1000"))

##############
## NOTE: parameters are separated by semicolon!!!
##############


ws.write(5, 2, Formula("C1+C2+C3+C4+C5/(C1+C2+C3+C4/(C1+C2+C3+C4/(C1+C2+C3+C4)+C5)+C5)-20.3e-2"))
ws.write(5, 3, Formula("C1^2"))
ws.write(6, 2, Formula("SUM(C1;C2;;;;;C3;;;C4)"))
ws.write(6, 3, Formula("SUM($A$1:$C$5)"))

ws.write(7, 0, Formula('"lkjljllkllkl"'))
ws.write(7, 1, Formula('"yuyiyiyiyi"'))
ws.write(7, 2, Formula('A8 & B8 & A8'))
ws.write(8, 2, Formula('now()'))

ws.write(10, 2, Formula('TRUE'))
ws.write(11, 2, Formula('FALSE'))
ws.write(12, 3, Formula('IF(A1>A2;3;"hkjhjkhk")'))

w.save('formulas.xls')

########NEW FILE########
__FILENAME__ = formula_names
#!/usr/bin/env python
# -*- coding: windows-1251 -*-
# Copyright (C) 2005 Kiseliov Roman

from xlwt import *
from xlwt.ExcelFormulaParser import FormulaParseException

w = Workbook()
ws = w.add_sheet('F')

## This example is a little silly since the formula building is
## so simplistic that it often fails because the generated text
## has the wrong number of parameters for the function being
## tested.

i = 0
succeed_count = 0
fail_count = 0
for n in sorted(ExcelMagic.std_func_by_name):
    ws.write(i, 0, n)
    text = n + "($A$1)"
    try:
        formula = Formula(text)
    except FormulaParseException,e:
        print "Could not parse %r: %s" % (text,e.args[0])
        fail_count += 1
    else:
        ws.write(i, 3, formula)
        succeed_count += 1
    i += 1

w.save('formula_names.xls')

print "succeeded with %i functions, failed with %i" % (succeed_count,fail_count)

########NEW FILE########
__FILENAME__ = hyperlinks
#!/usr/bin/env python
# -*- coding: windows-1251 -*-
# Copyright (C) 2005 Kiseliov Roman

from xlwt import *

f = Font()
f.height = 20*72
f.name = 'Verdana'
f.bold = True
f.underline = Font.UNDERLINE_DOUBLE
f.colour_index = 4

h_style = XFStyle()
h_style.font = f

w = Workbook()
ws = w.add_sheet('F')

##############
## NOTE: parameters are separated by semicolon!!!
##############

n = "HYPERLINK"
ws.write_merge(1, 1, 1, 10, Formula(n + '("http://www.irs.gov/pub/irs-pdf/f1000.pdf";"f1000.pdf")'), h_style)
ws.write_merge(2, 2, 2, 25, Formula(n + '("mailto:roman.kiseliov@gmail.com?subject=pyExcelerator-feedback&Body=Hello,%20Roman!";"pyExcelerator-feedback")'), h_style)

w.save("hyperlinks.xls")

########NEW FILE########
__FILENAME__ = image
#!/usr/bin/env python
# -*- coding: windows-1251 -*-
# Copyright (C) 2005 Kiseliov Roman

from xlwt import *

w = Workbook()
ws = w.add_sheet('Image')
ws.insert_bitmap('python.bmp', 2, 2)
ws.insert_bitmap('python.bmp', 10, 2)

w.save('image.xls')

########NEW FILE########
__FILENAME__ = image_chg_col_wid
# This demonstrates the effect of changing the column width
# when inserting a picture/image.

import xlwt
w = xlwt.Workbook()
ws = w.add_sheet('Image')

ws.write(0, 2, "chg wid: none")
ws.insert_bitmap('python.bmp', 2, 2)

ws.write(0, 4, "chg wid: after")
ws.insert_bitmap('python.bmp', 2, 4)
ws.col(4).width = 20 * 256

ws.write(0, 6, "chg wid: before")
ws.col(6).width = 20 * 256
ws.insert_bitmap('python.bmp', 2, 6)

ws.write(0, 8, "chg wid: after")
ws.insert_bitmap('python.bmp', 2, 8)
ws.col(5).width = 8 * 256

ws.write(0, 10, "chg wid: before")
ws.col(10).width = 8 * 256
ws.insert_bitmap('python.bmp', 2, 10)

w.save('image_chg_col_wid.xls')

########NEW FILE########
__FILENAME__ = merged
#!/usr/bin/env python
# -*- coding: windows-1251 -*-
# Copyright (C) 2005 Kiseliov Roman

from xlwt import *

fnt = Font()
fnt.name = 'Arial'
fnt.colour_index = 4
fnt.bold = True

borders = Borders()
borders.left = 6
borders.right = 6
borders.top = 6
borders.bottom = 6

al = Alignment()
al.horz = Alignment.HORZ_CENTER
al.vert = Alignment.VERT_CENTER

style = XFStyle()
style.font = fnt
style.borders = borders
style.alignment = al


wb = Workbook()
ws0 = wb.add_sheet('sheet0')
ws1 = wb.add_sheet('sheet1')
ws2 = wb.add_sheet('sheet2')

for i in range(0, 0x200, 2):
    ws0.write_merge(i, i+1, 1, 5, 'test %d' % i, style)
    ws1.write_merge(i, i, 1, 7, 'test %d' % i, style)
    ws2.write_merge(i, i+1, 1, 7 + (i%10), 'test %d' % i, style)


wb.save('merged.xls')

########NEW FILE########
__FILENAME__ = merged0
#!/usr/bin/env python
# -*- coding: windows-1251 -*-
# Copyright (C) 2005 Kiseliov Roman

from xlwt import *

wb = Workbook()
ws0 = wb.add_sheet('sheet0')


fnt = Font()
fnt.name = 'Arial'
fnt.colour_index = 4
fnt.bold = True

borders = Borders()
borders.left = 6
borders.right = 6
borders.top = 6
borders.bottom = 6

style = XFStyle()
style.font = fnt
style.borders = borders

ws0.write_merge(3, 3, 1, 5, 'test1', style)
ws0.write_merge(4, 10, 1, 5, 'test2', style)
ws0.col(1).width = 0x0d00

wb.save('merged0.xls')

########NEW FILE########
__FILENAME__ = merged1
#!/usr/bin/env python
# -*- coding: windows-1251 -*-
# Copyright (C) 2005 Kiseliov Roman

from xlwt import *

wb = Workbook()
ws0 = wb.add_sheet('sheet0')

fnt1 = Font()
fnt1.name = 'Verdana'
fnt1.bold = True
fnt1.height = 18*0x14

pat1 = Pattern()
pat1.pattern = Pattern.SOLID_PATTERN
pat1.pattern_fore_colour = 0x16

brd1 = Borders()
brd1.left = 0x06
brd1.right = 0x06
brd1.top = 0x06
brd1.bottom = 0x06

fnt2 = Font()
fnt2.name = 'Verdana'
fnt2.bold = True
fnt2.height = 14*0x14

brd2 = Borders()
brd2.left = 0x01
brd2.right = 0x01
brd2.top = 0x01
brd2.bottom = 0x01

pat2 = Pattern()
pat2.pattern = Pattern.SOLID_PATTERN
pat2.pattern_fore_colour = 0x01F

fnt3 = Font()
fnt3.name = 'Verdana'
fnt3.bold = True
fnt3.italic = True
fnt3.height = 12*0x14

brd3 = Borders()
brd3.left = 0x07
brd3.right = 0x07
brd3.top = 0x07
brd3.bottom = 0x07

fnt4 = Font()

al1 = Alignment()
al1.horz = Alignment.HORZ_CENTER
al1.vert = Alignment.VERT_CENTER

al2 = Alignment()
al2.horz = Alignment.HORZ_RIGHT
al2.vert = Alignment.VERT_CENTER

al3 = Alignment()
al3.horz = Alignment.HORZ_LEFT
al3.vert = Alignment.VERT_CENTER

style1 = XFStyle()
style1.font = fnt1
style1.alignment = al1
style1.pattern = pat1
style1.borders = brd1

style2 = XFStyle()
style2.font = fnt2
style2.alignment = al1
style2.pattern = pat2
style2.borders = brd2

style3 = XFStyle()
style3.font = fnt3
style3.alignment = al1
style3.pattern = pat2
style3.borders = brd3

price_style = XFStyle()
price_style.font = fnt4
price_style.alignment = al2
price_style.borders = brd3
price_style.num_format_str = '_(#,##0.00_) "money"'

ware_style = XFStyle()
ware_style.font = fnt4
ware_style.alignment = al3
ware_style.borders = brd3


ws0.merge(3, 3, 1, 5, style1)
ws0.merge(4, 10, 1, 6, style2)
ws0.merge(14, 16, 1, 7, style3)
ws0.col(1).width = 0x0d00


wb.save('merged1.xls')

########NEW FILE########
__FILENAME__ = mini
#!/usr/bin/env python
# -*- coding: windows-1251 -*-
# Copyright (C) 2005 Kiseliov Roman

from xlwt import *

w = Workbook()
ws = w.add_sheet('xlwt was here')
w.save('mini.xls')

########NEW FILE########
__FILENAME__ = numbers_demo
#!/usr/bin/env python
# -*- coding: windows-1251 -*-
# Copyright (C) 2005 Kiseliov Roman

from xlwt import *

w = Workbook()
ws = w.add_sheet('Hey, Dude')

ws.write(0, 0, 1)
ws.write(1, 0, 1.23)
ws.write(2, 0, 12345678)
ws.write(3, 0, 123456.78)

ws.write(0, 1, -1)
ws.write(1, 1, -1.23)
ws.write(2, 1, -12345678)
ws.write(3, 1, -123456.78)

ws.write(0, 2, -17867868678687.0)
ws.write(1, 2, -1.23e-5)
ws.write(2, 2, -12345678.90780980)
ws.write(3, 2, -123456.78)

w.save('numbers.xls')

########NEW FILE########
__FILENAME__ = num_formats
#!/usr/bin/env python
# -*- coding: windows-1251 -*-
# Copyright (C) 2005 Kiseliov Roman

from xlwt import *

w = Workbook()
ws = w.add_sheet('Hey, Dude')

fmts = [
    'general',
    '0',
    '0.00',
    '#,##0',
    '#,##0.00',
    '"$"#,##0_);("$"#,##',
    '"$"#,##0_);[Red]("$"#,##',
    '"$"#,##0.00_);("$"#,##',
    '"$"#,##0.00_);[Red]("$"#,##',
    '0%',
    '0.00%',
    '0.00E+00',
    '# ?/?',
    '# ??/??',
    'M/D/YY',
    'D-MMM-YY',
    'D-MMM',
    'MMM-YY',
    'h:mm AM/PM',
    'h:mm:ss AM/PM',
    'h:mm',
    'h:mm:ss',
    'M/D/YY h:mm',
    '_(#,##0_);(#,##0)',
    '_(#,##0_);[Red](#,##0)',
    '_(#,##0.00_);(#,##0.00)',
    '_(#,##0.00_);[Red](#,##0.00)',
    '_("$"* #,##0_);_("$"* (#,##0);_("$"* "-"_);_(@_)',
    '_(* #,##0_);_(* (#,##0);_(* "-"_);_(@_)',
    '_("$"* #,##0.00_);_("$"* (#,##0.00);_("$"* "-"??_);_(@_)',
    '_(* #,##0.00_);_(* (#,##0.00);_(* "-"??_);_(@_)',
    'mm:ss',
    '[h]:mm:ss',
    'mm:ss.0',
    '##0.0E+0',
    '@'   
]

i = 0
for fmt in fmts:
    ws.write(i, 0, fmt)

    style = XFStyle()
    style.num_format_str = fmt

    ws.write(i, 4, -1278.9078, style)

    i += 1

w.save('num_formats.xls')

########NEW FILE########
__FILENAME__ = outline
#!/usr/bin/env python
# -*- coding: windows-1251 -*-
# Copyright (C) 2005 Kiseliov Roman

from xlwt import *

fnt = Font()
fnt.name = 'Arial'
fnt.colour_index = 4
fnt.bold = True

borders = Borders()
borders.left = 6
borders.right = 6
borders.top = 6
borders.bottom = 6

style = XFStyle()
style.font = fnt
style.borders = borders

wb = Workbook()

ws0 = wb.add_sheet('Rows Outline')

ws0.write_merge(1, 1, 1, 5, 'test 1', style)
ws0.write_merge(2, 2, 1, 4, 'test 1', style)
ws0.write_merge(3, 3, 1, 3, 'test 2', style)
ws0.write_merge(4, 4, 1, 4, 'test 1', style)
ws0.write_merge(5, 5, 1, 4, 'test 3', style)
ws0.write_merge(6, 6, 1, 5, 'test 1', style)
ws0.write_merge(7, 7, 1, 5, 'test 4', style)
ws0.write_merge(8, 8, 1, 4, 'test 1', style)
ws0.write_merge(9, 9, 1, 3, 'test 5', style)

ws0.row(1).level = 1
ws0.row(2).level = 1
ws0.row(3).level = 2
ws0.row(4).level = 2
ws0.row(5).level = 2
ws0.row(6).level = 2
ws0.row(7).level = 2
ws0.row(8).level = 1
ws0.row(9).level = 1


ws1 = wb.add_sheet('Columns Outline')

ws1.write_merge(1, 1, 1, 5, 'test 1', style)
ws1.write_merge(2, 2, 1, 4, 'test 1', style)
ws1.write_merge(3, 3, 1, 3, 'test 2', style)
ws1.write_merge(4, 4, 1, 4, 'test 1', style)
ws1.write_merge(5, 5, 1, 4, 'test 3', style)
ws1.write_merge(6, 6, 1, 5, 'test 1', style)
ws1.write_merge(7, 7, 1, 5, 'test 4', style)
ws1.write_merge(8, 8, 1, 4, 'test 1', style)
ws1.write_merge(9, 9, 1, 3, 'test 5', style)

ws1.col(1).level = 1
ws1.col(2).level = 1
ws1.col(3).level = 2
ws1.col(4).level = 2
ws1.col(5).level = 2
ws1.col(6).level = 2
ws1.col(7).level = 2
ws1.col(8).level = 1
ws1.col(9).level = 1


ws2 = wb.add_sheet('Rows and Columns Outline')

ws2.write_merge(1, 1, 1, 5, 'test 1', style)
ws2.write_merge(2, 2, 1, 4, 'test 1', style)
ws2.write_merge(3, 3, 1, 3, 'test 2', style)
ws2.write_merge(4, 4, 1, 4, 'test 1', style)
ws2.write_merge(5, 5, 1, 4, 'test 3', style)
ws2.write_merge(6, 6, 1, 5, 'test 1', style)
ws2.write_merge(7, 7, 1, 5, 'test 4', style)
ws2.write_merge(8, 8, 1, 4, 'test 1', style)
ws2.write_merge(9, 9, 1, 3, 'test 5', style)

ws2.row(1).level = 1
ws2.row(2).level = 1
ws2.row(3).level = 2
ws2.row(4).level = 2
ws2.row(5).level = 2
ws2.row(6).level = 2
ws2.row(7).level = 2
ws2.row(8).level = 1
ws2.row(9).level = 1

ws2.write_merge(1, 1, 1, 5, 'test 1', style)
ws2.write_merge(2, 2, 1, 4, 'test 1', style)
ws2.write_merge(3, 3, 1, 3, 'test 2', style)
ws2.write_merge(4, 4, 1, 4, 'test 1', style)
ws2.write_merge(5, 5, 1, 4, 'test 3', style)
ws2.write_merge(6, 6, 1, 5, 'test 1', style)
ws2.write_merge(7, 7, 1, 5, 'test 4', style)
ws2.write_merge(8, 8, 1, 4, 'test 1', style)
ws2.write_merge(9, 9, 1, 3, 'test 5', style)

ws2.col(1).level = 1
ws2.col(2).level = 1
ws2.col(3).level = 2
ws2.col(4).level = 2
ws2.col(5).level = 2
ws2.col(6).level = 2
ws2.col(7).level = 2
ws2.col(8).level = 1
ws2.col(9).level = 1


wb.save('outline.xls')

########NEW FILE########
__FILENAME__ = panes
#!/usr/bin/env python
# -*- coding: windows-1251 -*-
# Copyright (C) 2005 Kiseliov Roman

from xlwt import *

w = Workbook()
ws1 = w.add_sheet('sheet 1')
ws2 = w.add_sheet('sheet 2')
ws3 = w.add_sheet('sheet 3')
ws4 = w.add_sheet('sheet 4')
ws5 = w.add_sheet('sheet 5')
ws6 = w.add_sheet('sheet 6')

for i in range(0x100):
    ws1.write(i/0x10, i%0x10, i)

for i in range(0x100):
    ws2.write(i/0x10, i%0x10, i)

for i in range(0x100):
    ws3.write(i/0x10, i%0x10, i)

for i in range(0x100):
    ws4.write(i/0x10, i%0x10, i)

for i in range(0x100):
    ws5.write(i/0x10, i%0x10, i)

for i in range(0x100):
    ws6.write(i/0x10, i%0x10, i)

ws1.panes_frozen = True
ws1.horz_split_pos = 2

ws2.panes_frozen = True
ws2.vert_split_pos = 2

ws3.panes_frozen = True
ws3.horz_split_pos = 1
ws3.vert_split_pos = 1

ws4.panes_frozen = False
ws4.horz_split_pos = 12
ws4.horz_split_first_visible = 2

ws5.panes_frozen = False
ws5.vert_split_pos = 40
ws4.vert_split_first_visible = 2

ws6.panes_frozen = False
ws6.horz_split_pos = 12
ws4.horz_split_first_visible = 2
ws6.vert_split_pos = 40
ws4.vert_split_first_visible = 2

w.save('panes.xls')


########NEW FILE########
__FILENAME__ = panes2
#!/usr/bin/env python
# -*- coding: ascii -*-
# portions Copyright (C) 2005 Kiseliov Roman

import xlwt

w = xlwt.Workbook()
sheets = [w.add_sheet('sheet ' + str(sheetx+1)) for sheetx in xrange(7)]
ws1, ws2, ws3, ws4, ws5, ws6, ws7 = sheets
for sheet in sheets:
    for i in range(0x100):
        sheet.write(i // 0x10, i % 0x10, i)

H = 1
V = 2
HF = H + 2
VF = V + 2

ws1.panes_frozen = True
ws1.horz_split_pos = H
ws1.horz_split_first_visible = HF

ws2.panes_frozen = True
ws2.vert_split_pos = V
ws2.vert_split_first_visible = VF

ws3.panes_frozen = True
ws3.horz_split_pos = H
ws3.vert_split_pos = V
ws3.horz_split_first_visible = HF
ws3.vert_split_first_visible = VF

H = 10
V = 12
HF = H + 2
VF = V + 2

ws4.panes_frozen = False
ws4.horz_split_pos = H * 12.75 # rows
ws4.horz_split_first_visible = HF

ws5.panes_frozen = False
ws5.vert_split_pos = V * 8.43 # rows
ws5.vert_split_first_visible = VF

ws6.panes_frozen = False
ws6.horz_split_pos = H * 12.75 # rows
ws6.horz_split_first_visible = HF
ws6.vert_split_pos = V * 8.43 # cols
ws6.vert_split_first_visible = VF

ws7.split_position_units_are_twips = True
ws7.panes_frozen = False
ws7.horz_split_pos = H * 250 + 240 # twips
ws7.horz_split_first_visible = HF
ws7.vert_split_pos = V * 955 + 410 # twips
ws7.vert_split_first_visible = VF

w.save('panes2.xls')


########NEW FILE########
__FILENAME__ = panes3
from xlwt import Workbook
from xlwt.BIFFRecords import PanesRecord
w = Workbook()

# do each of the 4 scenarios with each of the 4 possible
# active pane settings

for px,py in (
    (0,0),   # no split
    (0,10),  # horizontal split
    (10,0),  # vertical split
    (10,10), # both split
    ):
    
    for active in range(4):

        # 0 - logical bottom-right pane
        # 1 - logical top-right pane
        # 2 - logical bottom-left pane
        # 3 - logical top-left pane

        # only set valid values:
        if active not in PanesRecord.valid_active_pane.get(
            (int(px > 0),int(py > 0))
            ):
            continue

        sheet = w.add_sheet('px-%i py-%i active-%i' %(
                px,py,active
                ))

        for rx in range(20):
            for cx in range(20):
                sheet.write(rx,cx,'R%iC%i'%(rx,cx))

        sheet.panes_frozen = False
        sheet.vert_split_pos = px * 8.43
        sheet.horz_split_pos = py * 12.75
        sheet.active_pane = active

w.save('panes3.xls')


########NEW FILE########
__FILENAME__ = parse-fmla
from xlwt import ExcelFormulaParser, ExcelFormula
import sys

f = ExcelFormula.Formula(
""" -((1.80 + 2.898 * 1)/(1.80 + 2.898))*
AVERAGE((1.80 + 2.898 * 1)/(1.80 + 2.898); 
        (1.80 + 2.898 * 1)/(1.80 + 2.898); 
        (1.80 + 2.898 * 1)/(1.80 + 2.898)) + 
SIN(PI()/4)""")

#for t in f.rpn():
#    print "%15s %15s" % (ExcelFormulaParser.PtgNames[t[0]], t[1])

########NEW FILE########
__FILENAME__ = protection
# Copyright (C) 2005 Kiseliov Roman

from xlwt import *

fnt = Font()
fnt.name = 'Arial'
fnt.colour_index = 4
fnt.bold = True

borders = Borders()
borders.left = 6
borders.right = 6
borders.top = 6
borders.bottom = 6

style = XFStyle()
style.font = fnt
style.borders = borders

wb = Workbook()

ws0 = wb.add_sheet('Rows Outline')

ws0.write_merge(1, 1, 1, 5, 'test 1', style)
ws0.write_merge(2, 2, 1, 4, 'test 1', style)
ws0.write_merge(3, 3, 1, 3, 'test 2', style)
ws0.write_merge(4, 4, 1, 4, 'test 1', style)
ws0.write_merge(5, 5, 1, 4, 'test 3', style)
ws0.write_merge(6, 6, 1, 5, 'test 1', style)
ws0.write_merge(7, 7, 1, 5, 'test 4', style)
ws0.write_merge(8, 8, 1, 4, 'test 1', style)
ws0.write_merge(9, 9, 1, 3, 'test 5', style)

ws0.row(1).level = 1
ws0.row(2).level = 1
ws0.row(3).level = 2
ws0.row(4).level = 2
ws0.row(5).level = 2
ws0.row(6).level = 2
ws0.row(7).level = 2
ws0.row(8).level = 1
ws0.row(9).level = 1


ws1 = wb.add_sheet('Columns Outline')

ws1.write_merge(1, 1, 1, 5, 'test 1', style)
ws1.write_merge(2, 2, 1, 4, 'test 1', style)
ws1.write_merge(3, 3, 1, 3, 'test 2', style)
ws1.write_merge(4, 4, 1, 4, 'test 1', style)
ws1.write_merge(5, 5, 1, 4, 'test 3', style)
ws1.write_merge(6, 6, 1, 5, 'test 1', style)
ws1.write_merge(7, 7, 1, 5, 'test 4', style)
ws1.write_merge(8, 8, 1, 4, 'test 1', style)
ws1.write_merge(9, 9, 1, 3, 'test 5', style)

ws1.col(1).level = 1
ws1.col(2).level = 1
ws1.col(3).level = 2
ws1.col(4).level = 2
ws1.col(5).level = 2
ws1.col(6).level = 2
ws1.col(7).level = 2
ws1.col(8).level = 1
ws1.col(9).level = 1


ws2 = wb.add_sheet('Rows and Columns Outline')

ws2.write_merge(1, 1, 1, 5, 'test 1', style)
ws2.write_merge(2, 2, 1, 4, 'test 1', style)
ws2.write_merge(3, 3, 1, 3, 'test 2', style)
ws2.write_merge(4, 4, 1, 4, 'test 1', style)
ws2.write_merge(5, 5, 1, 4, 'test 3', style)
ws2.write_merge(6, 6, 1, 5, 'test 1', style)
ws2.write_merge(7, 7, 1, 5, 'test 4', style)
ws2.write_merge(8, 8, 1, 4, 'test 1', style)
ws2.write_merge(9, 9, 1, 3, 'test 5', style)

ws2.row(1).level = 1
ws2.row(2).level = 1
ws2.row(3).level = 2
ws2.row(4).level = 2
ws2.row(5).level = 2
ws2.row(6).level = 2
ws2.row(7).level = 2
ws2.row(8).level = 1
ws2.row(9).level = 1

ws2.col(1).level = 1
ws2.col(2).level = 1
ws2.col(3).level = 2
ws2.col(4).level = 2
ws2.col(5).level = 2
ws2.col(6).level = 2
ws2.col(7).level = 2
ws2.col(8).level = 1
ws2.col(9).level = 1


ws0.protect = True
ws0.wnd_protect = True
ws0.obj_protect = True
ws0.scen_protect = True
ws0.password = "123456"

ws1.protect = True
ws1.wnd_protect = True
ws1.obj_protect = True
ws1.scen_protect = True
ws1.password = "abcdefghij"

ws2.protect = True
ws2.wnd_protect = True
ws2.obj_protect = True
ws2.scen_protect = True
ws2.password = "ok"

wb.protect = True
wb.wnd_protect = True
wb.obj_protect = True
wb.save('protection.xls')

########NEW FILE########
__FILENAME__ = row_styles
#!/usr/bin/env python
# -*- coding: windows-1251 -*-
# Copyright (C) 2005 Kiseliov Roman

from xlwt import *

w = Workbook()
ws = w.add_sheet('Hey, Dude')

for i in range(6, 80):
    fnt = Font()
    fnt.height = i*20
    style = XFStyle()
    style.font = fnt
    ws.write(i, 1, 'Test')
    ws.row(i).set_style(style)
w.save('row_styles.xls')

########NEW FILE########
__FILENAME__ = row_styles_empty
#!/usr/bin/env python
# -*- coding: windows-1251 -*-
# Copyright (C) 2005 Kiseliov Roman
__rev_id__ = """$Id$"""


from pyExcelerator import *

w = Workbook()
ws = w.add_sheet('Hey, Dude')

for i in range(6, 80):
    fnt = Font()
    fnt.height = i*20
    style = XFStyle()
    style.font = fnt
    ws.row(i).set_style(style)
w.save('row_styles_empty.xls')

########NEW FILE########
__FILENAME__ = simple
import xlwt
from datetime import datetime

font0 = xlwt.Font()
font0.name = 'Times New Roman'
font0.colour_index = 2
font0.bold = True

style0 = xlwt.XFStyle()
style0.font = font0

style1 = xlwt.XFStyle()
style1.num_format_str = 'D-MMM-YY'

wb = xlwt.Workbook()
ws = wb.add_sheet('A Test Sheet')

ws.write(0, 0, 'Test', style0)
ws.write(1, 0, datetime.now(), style1)
ws.write(2, 0, 1)
ws.write(2, 1, 1)
ws.write(2, 2, xlwt.Formula("A3+B3"))

wb.save('example.xls')

########NEW FILE########
__FILENAME__ = sst
#!/usr/bin/env python
# -*- coding: windows-1251 -*-
# Copyright (C) 2005 Kiseliov Roman

from xlwt import *

font0 = Formatting.Font()
font0.name = 'Arial'
font1 = Formatting.Font()
font1.name = 'Arial Cyr'
font2 = Formatting.Font()
font2.name = 'Times New Roman'
font3 = Formatting.Font()
font3.name = 'Courier New Cyr'

num_format0 = '0.00000'
num_format1 = '0.000000'
num_format2 = '0.0000000'
num_format3 = '0.00000000'

st0 = XFStyle()
st1 = XFStyle()
st2 = XFStyle()
st3 = XFStyle()
st4 = XFStyle()

st0.font = font0
st0.num_format = num_format0

st1.font = font1
st1.num_format = num_format1

st2.font = font2
st2.num_format = num_format2

st3.font = font3
st3.num_format = num_format3

wb = Workbook()

wb.add_style(st0)
wb.add_style(st1)
wb.add_style(st2)
wb.add_style(st3)

ws0 = wb.add_sheet('0')
ws0.write(0, 0, 'Olya'*0x4000, st0)

#for i in range(0, 0x10):
#    ws0.write(i, 2, ('%d'%i)*0x4000, st1)
    
wb.save('sst.xls')

########NEW FILE########
__FILENAME__ = unicode0
#!/usr/bin/env python
import xlwt

# Strings passed to (for example) Worksheet.write can be unicode objects,
# or str (8-bit) objects, which are then decoded into unicode.
# The encoding to be used defaults to 'ascii'. This can be overridden
# when the Workbook instance is created:

book = xlwt.Workbook(encoding='cp1251')
sheet = book.add_sheet('cp1251-demo')
sheet.write(0, 0, '\xce\xeb\xff')
book.save('unicode0.xls')

########NEW FILE########
__FILENAME__ = unicode1
#!/usr/bin/env python
# -*- coding: windows-1251 -*-
# Copyright (C) 2005 Kiseliov Roman

from xlwt import *

w = Workbook()
ws1 = w.add_sheet(u'\N{GREEK SMALL LETTER ALPHA}\N{GREEK SMALL LETTER BETA}\N{GREEK SMALL LETTER GAMMA}')

ws1.write(0, 0, u'\N{GREEK SMALL LETTER ALPHA}\N{GREEK SMALL LETTER BETA}\N{GREEK SMALL LETTER GAMMA}')
ws1.write(1, 1, u'\N{GREEK SMALL LETTER DELTA}x = 1 + \N{GREEK SMALL LETTER DELTA}')

ws1.write(2,0, u'A\u2262\u0391.')     # RFC2152 example
ws1.write(3,0, u'Hi Mom -\u263a-!')   # RFC2152 example
ws1.write(4,0, u'\u65E5\u672C\u8A9E') # RFC2152 example
ws1.write(5,0, u'Item 3 is \u00a31.') # RFC2152 example
ws1.write(8,0, u'\N{INTEGRAL}')       # RFC2152 example

w.add_sheet(u'A\u2262\u0391.')     # RFC2152 example
w.add_sheet(u'Hi Mom -\u263a-!')   # RFC2152 example
one_more_ws = w.add_sheet(u'\u65E5\u672C\u8A9E') # RFC2152 example
w.add_sheet(u'Item 3 is \u00a31.') # RFC2152 example

one_more_ws.write(0, 0, u'\u2665\u2665')

w.add_sheet(u'\N{GREEK SMALL LETTER ETA WITH TONOS}')
w.save('unicode1.xls')


########NEW FILE########
__FILENAME__ = unicode2
#!/usr/bin/env python
# -*- coding: windows-1251 -*-
# Copyright (C) 2005 Kiseliov Roman

from xlwt import *

w = Workbook()
ws1 = w.add_sheet(u'\N{GREEK SMALL LETTER ALPHA}\N{GREEK SMALL LETTER BETA}\N{GREEK SMALL LETTER GAMMA}\u2665\u041e\u041b\u042f\u2665')

fnt = Font()
fnt.height = 26*20
style = XFStyle()
style.font = fnt

for i in range(0x10000):
    ws1.write(i/0x10, i%0x10, unichr(i), style)

w.save('unicode2.xls')


########NEW FILE########
__FILENAME__ = wsprops
props = \
[
        'name',
        'parent',
        'rows',
        'cols',
        'merged_ranges',
        'bmp_rec',
        'show_formulas',
        'show_grid',
        'show_headers',
        'panes_frozen',
        'show_empty_as_zero',
        'auto_colour_grid',
        'cols_right_to_left',
        'show_outline',
        'remove_splits',
        'selected',
        'hidden',
        'page_preview',
        'first_visible_row',
        'first_visible_col',
        'grid_colour',
        'preview_magn',
        'normal_magn',
        'row_gut_width',
        'col_gut_height',
        'show_auto_page_breaks',
        'dialogue_sheet',
        'auto_style_outline',
        'outline_below',
        'outline_right',
        'fit_num_pages',
        'show_row_outline',
        'show_col_outline',
        'alt_expr_eval',
        'alt_formula_entries',
        'row_default_height',
        'col_default_width',
        'calc_mode',
        'calc_count',
        'RC_ref_mode',
        'iterations_on',
        'delta',
        'save_recalc',
        'print_headers',
        'print_grid',
        'grid_set',
        'vert_page_breaks',
        'horz_page_breaks',
        'header_str',
        'footer_str',
        'print_centered_vert',
        'print_centered_horz',
        'left_margin',
        'right_margin',
        'top_margin',
        'bottom_margin',
        'paper_size_code',
        'print_scaling',
        'start_page_number',
        'fit_width_to_pages',
        'fit_height_to_pages',
        'print_in_rows',
        'portrait',
        'print_not_colour',
        'print_draft',
        'print_notes',
        'print_notes_at_end',
        'print_omit_errors',
        'print_hres',
        'print_vres',
        'header_margin',
        'footer_margin',
        'copies_num',
]

from xlwt import *

wb = Workbook()
ws = wb.add_sheet('sheet')

print ws.name
print ws.parent
print ws.rows
print ws.cols
print ws.merged_ranges
print ws.bmp_rec
print ws.show_formulas
print ws.show_grid
print ws.show_headers
print ws.panes_frozen
print ws.show_empty_as_zero
print ws.auto_colour_grid
print ws.cols_right_to_left
print ws.show_outline
print ws.remove_splits
print ws.selected
# print ws.hidden
print ws.page_preview
print ws.first_visible_row
print ws.first_visible_col
print ws.grid_colour
print ws.preview_magn
print ws.normal_magn
#print ws.row_gut_width
#print ws.col_gut_height
print ws.show_auto_page_breaks
print ws.dialogue_sheet
print ws.auto_style_outline
print ws.outline_below
print ws.outline_right
print ws.fit_num_pages
print ws.show_row_outline
print ws.show_col_outline
print ws.alt_expr_eval
print ws.alt_formula_entries
print ws.row_default_height
print ws.col_default_width
print ws.calc_mode
print ws.calc_count
print ws.RC_ref_mode
print ws.iterations_on
print ws.delta
print ws.save_recalc
print ws.print_headers
print ws.print_grid
#print ws.grid_set
print ws.vert_page_breaks
print ws.horz_page_breaks
print ws.header_str
print ws.footer_str
print ws.print_centered_vert
print ws.print_centered_horz
print ws.left_margin
print ws.right_margin
print ws.top_margin
print ws.bottom_margin
print ws.paper_size_code
print ws.print_scaling
print ws.start_page_number
print ws.fit_width_to_pages
print ws.fit_height_to_pages
print ws.print_in_rows
print ws.portrait
print ws.print_colour
print ws.print_draft
print ws.print_notes
print ws.print_notes_at_end
print ws.print_omit_errors
print ws.print_hres
print ws.print_vres
print ws.header_margin
print ws.footer_margin
print ws.copies_num

########NEW FILE########
__FILENAME__ = xlwt_easyxf_simple_demo

# Write an XLS file with a single worksheet, containing
# a heading row and some rows of data.

import xlwt
import datetime
ezxf = xlwt.easyxf

def write_xls(file_name, sheet_name, headings, data, heading_xf, data_xfs):
    book = xlwt.Workbook()
    sheet = book.add_sheet(sheet_name)
    rowx = 0
    for colx, value in enumerate(headings):
        sheet.write(rowx, colx, value, heading_xf)
    sheet.set_panes_frozen(True) # frozen headings instead of split panes
    sheet.set_horz_split_pos(rowx+1) # in general, freeze after last heading row
    sheet.set_remove_splits(True) # if user does unfreeze, don't leave a split there
    for row in data:
        rowx += 1
        for colx, value in enumerate(row):
            sheet.write(rowx, colx, value, data_xfs[colx])
    book.save(file_name)

if __name__ == '__main__':
    import sys
    mkd = datetime.date
    hdngs = ['Date', 'Stock Code', 'Quantity', 'Unit Price', 'Value', 'Message']
    kinds =  'date    text          int         price         money    text'.split()
    data = [
        [mkd(2007, 7, 1), 'ABC', 1000, 1.234567, 1234.57, ''],
        [mkd(2007, 12, 31), 'XYZ', -100, 4.654321, -465.43, 'Goods returned'],
        ] + [
            [mkd(2008, 6, 30), 'PQRCD', 100, 2.345678, 234.57, ''],
        ] * 100

    heading_xf = ezxf('font: bold on; align: wrap on, vert centre, horiz center')
    kind_to_xf_map = {
        'date': ezxf(num_format_str='yyyy-mm-dd'),
        'int': ezxf(num_format_str='#,##0'),
        'money': ezxf('font: italic on; pattern: pattern solid, fore-colour grey25',
            num_format_str='$#,##0.00'),
        'price': ezxf(num_format_str='#0.000000'),
        'text': ezxf(),
        }
    data_xfs = [kind_to_xf_map[k] for k in kinds]
    write_xls('xlwt_easyxf_simple_demo.xls', 'Demo', hdngs, data, heading_xf, data_xfs)

########NEW FILE########
__FILENAME__ = zoom_magnification
import xlwt
book = xlwt.Workbook()
for magn in (0, 60, 100, 75, 150):
    for preview in (False, True):
        sheet = book.add_sheet('magn%d%s' % (magn, "np"[preview]))
        if preview:
            sheet.preview_magn = magn
        else:
            sheet.normal_magn = magn
        sheet.page_preview = preview
        for rowx in range(100):
            sheet.write(rowx, 0, "Some text")
book.save("zoom_magnification.xls")


########NEW FILE########
__FILENAME__ = ExcelFormula
# -*- coding: windows-1252 -*-

import ExcelFormulaParser, ExcelFormulaLexer
import struct
from antlr import ANTLRException


class Formula(object):
    __slots__ = ["__init__",  "__s", "__parser", "__sheet_refs", "__xcall_refs"]


    def __init__(self, s):
        try:
            self.__s = s
            lexer = ExcelFormulaLexer.Lexer(s)
            self.__parser = ExcelFormulaParser.Parser(lexer)
            self.__parser.formula()
            self.__sheet_refs = self.__parser.sheet_references
            self.__xcall_refs = self.__parser.xcall_references
        except ANTLRException, e:
            # print e
            raise ExcelFormulaParser.FormulaParseException, "can't parse formula " + s

    def get_references(self):
        return self.__sheet_refs, self.__xcall_refs

    def patch_references(self, patches):
        for offset, idx in patches:
            self.__parser.rpn = self.__parser.rpn[:offset] + struct.pack('<H', idx) + self.__parser.rpn[offset+2:]

    def text(self):
        return self.__s

    def rpn(self):
        '''
        Offset    Size    Contents
        0         2       Size of the following formula data (sz)
        2         sz      Formula data (RPN token array)
        [2+sz]    var.    (optional) Additional data for specific tokens

        '''
        return struct.pack("<H", len(self.__parser.rpn)) + self.__parser.rpn


########NEW FILE########
__FILENAME__ = ExcelFormulaLexer
# -*- coding: windows-1252 -*-

from antlr import EOF, CommonToken as Tok, TokenStream, TokenStreamException
import ExcelFormulaParser
from re import compile as recompile, LOCALE, IGNORECASE, VERBOSE


int_const_pattern = r"\d+\b"
flt_const_pattern = r"""
    (?:
        (?: \d* \. \d+ ) # .1 .12 .123 etc 9.1 etc 98.1 etc
        |
        (?: \d+ \. ) # 1. 12. 123. etc
    )
    # followed by optional exponent part
    (?: [Ee] [+-]? \d+ ) ?
    """
str_const_pattern = r'"(?:[^"]|"")*"'
#range2d_pattern   = recompile(r"\$?[A-I]?[A-Z]\$?\d+:\$?[A-I]?[A-Z]\$?\d+"
ref2d_r1c1_pattern = r"[Rr]0*[1-9][0-9]*[Cc]0*[1-9][0-9]*"
ref2d_pattern     = r"\$?[A-I]?[A-Z]\$?0*[1-9][0-9]*"
true_pattern      = r"TRUE\b"
false_pattern     = r"FALSE\b"
if_pattern        = r"IF\b"
choose_pattern    = r"CHOOSE\b"
name_pattern      = r"\w[\.\w]*"
quotename_pattern = r"'(?:[^']|'')*'" #### It's essential that this bracket be non-grouping.
ne_pattern        = r"<>"
ge_pattern        = r">="
le_pattern        = r"<="

pattern_type_tuples = (
    (flt_const_pattern, ExcelFormulaParser.NUM_CONST),
    (int_const_pattern, ExcelFormulaParser.INT_CONST),
    (str_const_pattern, ExcelFormulaParser.STR_CONST),
#    (range2d_pattern  , ExcelFormulaParser.RANGE2D),
    (ref2d_r1c1_pattern, ExcelFormulaParser.REF2D_R1C1),
    (ref2d_pattern    , ExcelFormulaParser.REF2D),
    (true_pattern     , ExcelFormulaParser.TRUE_CONST),
    (false_pattern    , ExcelFormulaParser.FALSE_CONST),
    (if_pattern       , ExcelFormulaParser.FUNC_IF),
    (choose_pattern   , ExcelFormulaParser.FUNC_CHOOSE),
    (name_pattern     , ExcelFormulaParser.NAME),
    (quotename_pattern, ExcelFormulaParser.QUOTENAME),
    (ne_pattern,        ExcelFormulaParser.NE),
    (ge_pattern,        ExcelFormulaParser.GE),
    (le_pattern,        ExcelFormulaParser.LE),
)

_re = recompile(
    '(' + ')|('.join([i[0] for i in pattern_type_tuples]) + ')',
    VERBOSE+LOCALE+IGNORECASE)

_toktype = [None] + [i[1] for i in pattern_type_tuples]
# need dummy at start because re.MatchObject.lastindex counts from 1

single_char_lookup = {
    '=': ExcelFormulaParser.EQ,
    '<': ExcelFormulaParser.LT,
    '>': ExcelFormulaParser.GT,
    '+': ExcelFormulaParser.ADD,
    '-': ExcelFormulaParser.SUB,
    '*': ExcelFormulaParser.MUL,
    '/': ExcelFormulaParser.DIV,
    ':': ExcelFormulaParser.COLON,
    ';': ExcelFormulaParser.SEMICOLON,
    ',': ExcelFormulaParser.COMMA,
    '(': ExcelFormulaParser.LP,
    ')': ExcelFormulaParser.RP,
    '&': ExcelFormulaParser.CONCAT,
    '%': ExcelFormulaParser.PERCENT,
    '^': ExcelFormulaParser.POWER,
    '!': ExcelFormulaParser.BANG,
    }

class Lexer(TokenStream):
    def __init__(self, text):
        self._text = text[:]
        self._pos = 0
        self._line = 0

    def isEOF(self):
        return len(self._text) <= self._pos

    def curr_ch(self):
        return self._text[self._pos]

    def next_ch(self, n = 1):
        self._pos += n

    def is_whitespace(self):
        return self.curr_ch() in " \t\n\r\f\v"

    def match_pattern(self):
        m = _re.match(self._text, self._pos)
        if not m:
            return None
        self._pos = m.end(0)
        return Tok(type = _toktype[m.lastindex], text = m.group(0), col = m.start(0) + 1)

    def nextToken(self):
        # skip whitespace
        while not self.isEOF() and self.is_whitespace():
            self.next_ch()
        if self.isEOF():
            return Tok(type = EOF)
        # first, try to match token with 2 or more chars
        t = self.match_pattern()
        if t:
            return t
        # second, we want 1-char tokens
        te = self.curr_ch()
        try:
            ty = single_char_lookup[te]
        except KeyError:
            raise TokenStreamException(
                "Unexpected char %r in column %u." % (self.curr_ch(), self._pos))
        self.next_ch()
        return Tok(type=ty, text=te, col=self._pos)

if __name__ == '__main__':
    try:
        for t in Lexer(""" 1.23 456 "abcd" R2C2 a1 iv65536 true false if choose a_name 'qname' <> >= <= """):
            print t
    except TokenStreamException, e:
        print "error:", e

########NEW FILE########
__FILENAME__ = ExcelFormulaParser
### $ANTLR 2.7.7 (20060930): "xlwt/excel-formula.g" -> "ExcelFormulaParser.py"$
### import antlr and other modules ..
import sys
import antlr

version = sys.version.split()[0]
if version < '2.2.1':
    False = 0
if version < '2.3':
    True = not False
### header action >>>
import struct
import Utils
from UnicodeUtils import upack1
from ExcelMagic import *

_RVAdelta =     {"R": 0, "V": 0x20, "A": 0x40}
_RVAdeltaRef =  {"R": 0, "V": 0x20, "A": 0x40, "D": 0x20}
_RVAdeltaArea = {"R": 0, "V": 0x20, "A": 0x40, "D": 0}


class FormulaParseException(Exception):
   """
   An exception indicating that a Formula could not be successfully parsed.
   """
### header action <<<
### preamble action>>>

### preamble action <<<

### >>>The Known Token Types <<<
SKIP                = antlr.SKIP
INVALID_TYPE        = antlr.INVALID_TYPE
EOF_TYPE            = antlr.EOF_TYPE
EOF                 = antlr.EOF
NULL_TREE_LOOKAHEAD = antlr.NULL_TREE_LOOKAHEAD
MIN_USER_TYPE       = antlr.MIN_USER_TYPE
TRUE_CONST = 4
FALSE_CONST = 5
STR_CONST = 6
NUM_CONST = 7
INT_CONST = 8
FUNC_IF = 9
FUNC_CHOOSE = 10
NAME = 11
QUOTENAME = 12
EQ = 13
NE = 14
GT = 15
LT = 16
GE = 17
LE = 18
ADD = 19
SUB = 20
MUL = 21
DIV = 22
POWER = 23
PERCENT = 24
LP = 25
RP = 26
LB = 27
RB = 28
COLON = 29
COMMA = 30
SEMICOLON = 31
REF2D = 32
REF2D_R1C1 = 33
BANG = 34
CONCAT = 35

class Parser(antlr.LLkParser):
    ### user action >>>
    ### user action <<<

    def __init__(self, *args, **kwargs):
        antlr.LLkParser.__init__(self, *args, **kwargs)
        self.tokenNames = _tokenNames
        ### __init__ header action >>>
        self.rpn = ""
        self.sheet_references = []
        self.xcall_references = []
        ### __init__ header action <<<

    def formula(self):

        pass
        self.expr("V")

    def expr(self,
        arg_type
    ):

        pass
        self.prec0_expr(arg_type)
        while True:
            if ((self.LA(1) >= EQ and self.LA(1) <= LE)):
                pass
                la1 = self.LA(1)
                if False:
                    pass
                elif la1 and la1 in [EQ]:
                    pass
                    self.match(EQ)
                    op = struct.pack('B', ptgEQ)
                elif la1 and la1 in [NE]:
                    pass
                    self.match(NE)
                    op = struct.pack('B', ptgNE)
                elif la1 and la1 in [GT]:
                    pass
                    self.match(GT)
                    op = struct.pack('B', ptgGT)
                elif la1 and la1 in [LT]:
                    pass
                    self.match(LT)
                    op = struct.pack('B', ptgLT)
                elif la1 and la1 in [GE]:
                    pass
                    self.match(GE)
                    op = struct.pack('B', ptgGE)
                elif la1 and la1 in [LE]:
                    pass
                    self.match(LE)
                    op = struct.pack('B', ptgLE)
                else:
                        raise antlr.NoViableAltException(self.LT(1), self.getFilename())

                self.prec0_expr(arg_type)
                self.rpn += op
            else:
                break


    def prec0_expr(self,
        arg_type
    ):

        pass
        self.prec1_expr(arg_type)
        while True:
            if (self.LA(1)==CONCAT):
                pass
                pass
                self.match(CONCAT)
                op = struct.pack('B', ptgConcat)
                self.prec1_expr(arg_type)
                self.rpn += op
            else:
                break


    def prec1_expr(self,
        arg_type
    ):

        pass
        self.prec2_expr(arg_type)
        while True:
            if (self.LA(1)==ADD or self.LA(1)==SUB):
                pass
                la1 = self.LA(1)
                if False:
                    pass
                elif la1 and la1 in [ADD]:
                    pass
                    self.match(ADD)
                    op = struct.pack('B', ptgAdd)
                elif la1 and la1 in [SUB]:
                    pass
                    self.match(SUB)
                    op = struct.pack('B', ptgSub)
                else:
                        raise antlr.NoViableAltException(self.LT(1), self.getFilename())

                self.prec2_expr(arg_type)
                self.rpn += op;
                          # print "**prec1_expr4 %s" % arg_type
            else:
                break


    def prec2_expr(self,
        arg_type
    ):

        pass
        self.prec3_expr(arg_type)
        while True:
            if (self.LA(1)==MUL or self.LA(1)==DIV):
                pass
                la1 = self.LA(1)
                if False:
                    pass
                elif la1 and la1 in [MUL]:
                    pass
                    self.match(MUL)
                    op = struct.pack('B', ptgMul)
                elif la1 and la1 in [DIV]:
                    pass
                    self.match(DIV)
                    op = struct.pack('B', ptgDiv)
                else:
                        raise antlr.NoViableAltException(self.LT(1), self.getFilename())

                self.prec3_expr(arg_type)
                self.rpn += op
            else:
                break


    def prec3_expr(self,
        arg_type
    ):

        pass
        self.prec4_expr(arg_type)
        while True:
            if (self.LA(1)==POWER):
                pass
                pass
                self.match(POWER)
                op = struct.pack('B', ptgPower)
                self.prec4_expr(arg_type)
                self.rpn += op
            else:
                break


    def prec4_expr(self,
        arg_type
    ):

        pass
        self.prec5_expr(arg_type)
        la1 = self.LA(1)
        if False:
            pass
        elif la1 and la1 in [PERCENT]:
            pass
            self.match(PERCENT)
            self.rpn += struct.pack('B', ptgPercent)
        elif la1 and la1 in [EOF,EQ,NE,GT,LT,GE,LE,ADD,SUB,MUL,DIV,POWER,RP,COMMA,SEMICOLON,CONCAT]:
            pass
        else:
                raise antlr.NoViableAltException(self.LT(1), self.getFilename())


    def prec5_expr(self,
        arg_type
    ):

        la1 = self.LA(1)
        if False:
            pass
        elif la1 and la1 in [TRUE_CONST,FALSE_CONST,STR_CONST,NUM_CONST,INT_CONST,FUNC_IF,FUNC_CHOOSE,NAME,QUOTENAME,LP,REF2D]:
            pass
            self.primary(arg_type)
        elif la1 and la1 in [SUB]:
            pass
            self.match(SUB)
            self.primary(arg_type)
            self.rpn += struct.pack('B', ptgUminus)
        else:
                raise antlr.NoViableAltException(self.LT(1), self.getFilename())


    def primary(self,
        arg_type
    ):

        str_tok = None
        int_tok = None
        num_tok = None
        ref2d_tok = None
        ref2d1_tok = None
        ref2d2_tok = None
        ref3d_ref2d = None
        ref3d_ref2d2 = None
        name_tok = None
        func_tok = None
        la1 = self.LA(1)
        if False:
            pass
        elif la1 and la1 in [TRUE_CONST]:
            pass
            self.match(TRUE_CONST)
            self.rpn += struct.pack("2B", ptgBool, 1)
        elif la1 and la1 in [FALSE_CONST]:
            pass
            self.match(FALSE_CONST)
            self.rpn += struct.pack("2B", ptgBool, 0)
        elif la1 and la1 in [STR_CONST]:
            pass
            str_tok = self.LT(1)
            self.match(STR_CONST)
            self.rpn += struct.pack("B", ptgStr) + upack1(str_tok.text[1:-1].replace("\"\"", "\""))
        elif la1 and la1 in [NUM_CONST]:
            pass
            num_tok = self.LT(1)
            self.match(NUM_CONST)
            self.rpn += struct.pack("<Bd", ptgNum, float(num_tok.text))
        elif la1 and la1 in [FUNC_IF]:
            pass
            self.match(FUNC_IF)
            self.match(LP)
            self.expr("V")
            la1 = self.LA(1)
            if False:
                pass
            elif la1 and la1 in [SEMICOLON]:
                pass
                self.match(SEMICOLON)
            elif la1 and la1 in [COMMA]:
                pass
                self.match(COMMA)
            else:
                    raise antlr.NoViableAltException(self.LT(1), self.getFilename())

            self.rpn += struct.pack("<BBH", ptgAttr, 0x02, 0) # tAttrIf
            pos0 = len(self.rpn) - 2
            self.expr(arg_type)
            la1 = self.LA(1)
            if False:
                pass
            elif la1 and la1 in [SEMICOLON]:
                pass
                self.match(SEMICOLON)
            elif la1 and la1 in [COMMA]:
                pass
                self.match(COMMA)
            else:
                    raise antlr.NoViableAltException(self.LT(1), self.getFilename())

            self.rpn += struct.pack("<BBH", ptgAttr, 0x08, 0) # tAttrSkip
            pos1 = len(self.rpn) - 2
            self.rpn = self.rpn[:pos0] + struct.pack("<H", pos1-pos0) + self.rpn[pos0+2:]
            self.expr(arg_type)
            self.match(RP)
            self.rpn += struct.pack("<BBH", ptgAttr, 0x08, 3) # tAttrSkip
            self.rpn += struct.pack("<BBH", ptgFuncVarR, 3, 1) # 3 = nargs, 1 = IF func
            pos2 = len(self.rpn)
            self.rpn = self.rpn[:pos1] + struct.pack("<H", pos2-(pos1+2)-1) + self.rpn[pos1+2:]
        elif la1 and la1 in [FUNC_CHOOSE]:
            pass
            self.match(FUNC_CHOOSE)
            arg_type = "R"
            rpn_chunks = []
            self.match(LP)
            self.expr("V")
            rpn_start = len(self.rpn)
            ref_markers = [len(self.sheet_references)]
            while True:
                if (self.LA(1)==COMMA or self.LA(1)==SEMICOLON):
                    pass
                    la1 = self.LA(1)
                    if False:
                        pass
                    elif la1 and la1 in [SEMICOLON]:
                        pass
                        self.match(SEMICOLON)
                    elif la1 and la1 in [COMMA]:
                        pass
                        self.match(COMMA)
                    else:
                            raise antlr.NoViableAltException(self.LT(1), self.getFilename())

                    mark = len(self.rpn)
                    la1 = self.LA(1)
                    if False:
                        pass
                    elif la1 and la1 in [TRUE_CONST,FALSE_CONST,STR_CONST,NUM_CONST,INT_CONST,FUNC_IF,FUNC_CHOOSE,NAME,QUOTENAME,SUB,LP,REF2D]:
                        pass
                        self.expr(arg_type)
                    elif la1 and la1 in [RP,COMMA,SEMICOLON]:
                        pass
                        self.rpn += struct.pack("B", ptgMissArg)
                    else:
                            raise antlr.NoViableAltException(self.LT(1), self.getFilename())

                    rpn_chunks.append(self.rpn[mark:])
                    ref_markers.append(len(self.sheet_references))
                else:
                    break

            self.match(RP)
            self.rpn = self.rpn[:rpn_start]
            nc = len(rpn_chunks)
            chunklens = [len(chunk) for chunk in rpn_chunks]
            skiplens = [0] * nc
            skiplens[-1] = 3
            for ic in xrange(nc-1, 0, -1):
               skiplens[ic-1] = skiplens[ic] + chunklens[ic] + 4
            jump_pos = [2 * nc + 2]
            for ic in xrange(nc):
               jump_pos.append(jump_pos[-1] + chunklens[ic] + 4)
            chunk_shift = 2 * nc + 6 # size of tAttrChoose
            for ic in xrange(nc):
               for refx in xrange(ref_markers[ic], ref_markers[ic+1]):
                   ref = self.sheet_references[refx]
                   self.sheet_references[refx] = (ref[0], ref[1], ref[2] + chunk_shift)
               chunk_shift += 4 # size of tAttrSkip
            choose_rpn = []
            choose_rpn.append(struct.pack("<BBH", ptgAttr, 0x04, nc)) # 0x04 is tAttrChoose
            choose_rpn.append(struct.pack("<%dH" % (nc+1), *jump_pos))
            for ic in xrange(nc):
               choose_rpn.append(rpn_chunks[ic])
               choose_rpn.append(struct.pack("<BBH", ptgAttr, 0x08, skiplens[ic])) # 0x08 is tAttrSkip
            choose_rpn.append(struct.pack("<BBH", ptgFuncVarV, nc+1, 100)) # 100 is CHOOSE fn
            self.rpn += "".join(choose_rpn)
        elif la1 and la1 in [LP]:
            pass
            self.match(LP)
            self.expr(arg_type)
            self.match(RP)
            self.rpn += struct.pack("B", ptgParen)
        else:
            if (self.LA(1)==INT_CONST) and (_tokenSet_0.member(self.LA(2))):
                pass
                int_tok = self.LT(1)
                self.match(INT_CONST)
                # print "**int_const", int_tok.text
                int_value = int(int_tok.text)
                if int_value <= 65535:
                   self.rpn += struct.pack("<BH", ptgInt, int_value)
                else:
                   self.rpn += struct.pack("<Bd", ptgNum, float(int_value))
            elif (self.LA(1)==REF2D) and (_tokenSet_0.member(self.LA(2))):
                pass
                ref2d_tok = self.LT(1)
                self.match(REF2D)
                # print "**ref2d %s %s" % (ref2d_tok.text, arg_type)
                r, c = Utils.cell_to_packed_rowcol(ref2d_tok.text)
                ptg = ptgRefR + _RVAdeltaRef[arg_type]
                self.rpn += struct.pack("<B2H", ptg, r, c)
            elif (self.LA(1)==REF2D) and (self.LA(2)==COLON):
                pass
                ref2d1_tok = self.LT(1)
                self.match(REF2D)
                self.match(COLON)
                ref2d2_tok = self.LT(1)
                self.match(REF2D)
                r1, c1 = Utils.cell_to_packed_rowcol(ref2d1_tok.text)
                r2, c2 = Utils.cell_to_packed_rowcol(ref2d2_tok.text)
                ptg = ptgAreaR + _RVAdeltaArea[arg_type]
                self.rpn += struct.pack("<B4H", ptg, r1, r2, c1, c2)
            elif (self.LA(1)==INT_CONST or self.LA(1)==NAME or self.LA(1)==QUOTENAME) and (self.LA(2)==COLON or self.LA(2)==BANG):
                pass
                sheet1=self.sheet()
                sheet2 = sheet1
                la1 = self.LA(1)
                if False:
                    pass
                elif la1 and la1 in [COLON]:
                    pass
                    self.match(COLON)
                    sheet2=self.sheet()
                elif la1 and la1 in [BANG]:
                    pass
                else:
                        raise antlr.NoViableAltException(self.LT(1), self.getFilename())

                self.match(BANG)
                ref3d_ref2d = self.LT(1)
                self.match(REF2D)
                ptg = ptgRef3dR + _RVAdeltaRef[arg_type]
                rpn_ref2d = ""
                r1, c1 = Utils.cell_to_packed_rowcol(ref3d_ref2d.text)
                rpn_ref2d = struct.pack("<3H", 0x0000, r1, c1)
                la1 = self.LA(1)
                if False:
                    pass
                elif la1 and la1 in [COLON]:
                    pass
                    self.match(COLON)
                    ref3d_ref2d2 = self.LT(1)
                    self.match(REF2D)
                    ptg = ptgArea3dR + _RVAdeltaArea[arg_type]
                    r2, c2 = Utils.cell_to_packed_rowcol(ref3d_ref2d2.text)
                    rpn_ref2d = struct.pack("<5H", 0x0000, r1, r2, c1, c2)
                elif la1 and la1 in [EOF,EQ,NE,GT,LT,GE,LE,ADD,SUB,MUL,DIV,POWER,PERCENT,RP,COMMA,SEMICOLON,CONCAT]:
                    pass
                else:
                        raise antlr.NoViableAltException(self.LT(1), self.getFilename())

                self.rpn += struct.pack("<B", ptg)
                self.sheet_references.append((sheet1, sheet2, len(self.rpn)))
                self.rpn += rpn_ref2d
            elif (self.LA(1)==NAME) and (_tokenSet_0.member(self.LA(2))):
                pass
                name_tok = self.LT(1)
                self.match(NAME)
                raise Exception("[formula] found unexpected NAME token (%r)" % name_tok.txt)
                # #### TODO: handle references to defined names here
            elif (self.LA(1)==NAME) and (self.LA(2)==LP):
                pass
                func_tok = self.LT(1)
                self.match(NAME)
                func_toku = func_tok.text.upper()
                if func_toku in all_funcs_by_name:
                   (opcode,
                   min_argc,
                   max_argc,
                   func_type,
                   arg_type_str) = all_funcs_by_name[func_toku]
                   arg_type_list = list(arg_type_str)
                else:
                   raise Exception("[formula] unknown function (%s)" % func_tok.text)
                # print "**func_tok1 %s %s" % (func_toku, func_type)
                xcall = opcode < 0
                if xcall:
                   # The name of the add-in function is passed as the 1st arg
                   # of the hidden XCALL function
                   self.xcall_references.append((func_toku, len(self.rpn) + 1))
                   self.rpn += struct.pack("<BHHH",
                       ptgNameXR,
                       0xadde, # ##PATCHME## index to REF entry in EXTERNSHEET record
                       0xefbe, # ##PATCHME## one-based index to EXTERNNAME record
                       0x0000) # unused
                self.match(LP)
                arg_count=self.expr_list(arg_type_list, min_argc, max_argc)
                self.match(RP)
                if arg_count > max_argc or arg_count < min_argc:
                   raise Exception, "%d parameters for function: %s" % (arg_count, func_tok.text)
                if xcall:
                   func_ptg = ptgFuncVarR + _RVAdelta[func_type]
                   self.rpn += struct.pack("<2BH", func_ptg, arg_count + 1, 255) # 255 is magic XCALL function
                elif min_argc == max_argc:
                   func_ptg = ptgFuncR + _RVAdelta[func_type]
                   self.rpn += struct.pack("<BH", func_ptg, opcode)
                elif arg_count == 1 and func_tok.text.upper() == "SUM":
                   self.rpn += struct.pack("<BBH", ptgAttr, 0x10, 0) # tAttrSum
                else:
                   func_ptg = ptgFuncVarR + _RVAdelta[func_type]
                   self.rpn += struct.pack("<2BH", func_ptg, arg_count, opcode)
            else:
                raise antlr.NoViableAltException(self.LT(1), self.getFilename())


    def sheet(self):
        ref = None

        sheet_ref_name = None
        sheet_ref_int = None
        sheet_ref_quote = None
        la1 = self.LA(1)
        if False:
            pass
        elif la1 and la1 in [NAME]:
            pass
            sheet_ref_name = self.LT(1)
            self.match(NAME)
            ref = sheet_ref_name.text
        elif la1 and la1 in [INT_CONST]:
            pass
            sheet_ref_int = self.LT(1)
            self.match(INT_CONST)
            ref = sheet_ref_int.text
        elif la1 and la1 in [QUOTENAME]:
            pass
            sheet_ref_quote = self.LT(1)
            self.match(QUOTENAME)
            ref = sheet_ref_quote.text[1:-1].replace("''", "'")
        else:
                raise antlr.NoViableAltException(self.LT(1), self.getFilename())

        return ref

    def expr_list(self,
        arg_type_list, min_argc, max_argc
    ):
        arg_cnt = None

        arg_cnt = 0
        arg_type = arg_type_list[arg_cnt]
        # print "**expr_list1[%d] req=%s" % (arg_cnt, arg_type)
        la1 = self.LA(1)
        if False:
            pass
        elif la1 and la1 in [TRUE_CONST,FALSE_CONST,STR_CONST,NUM_CONST,INT_CONST,FUNC_IF,FUNC_CHOOSE,NAME,QUOTENAME,SUB,LP,REF2D]:
            pass
            self.expr(arg_type)
            arg_cnt += 1
            while True:
                if (self.LA(1)==COMMA or self.LA(1)==SEMICOLON):
                    pass
                    if arg_cnt < len(arg_type_list):
                       arg_type = arg_type_list[arg_cnt]
                    else:
                       arg_type = arg_type_list[-1]
                    if arg_type == "+":
                       arg_type = arg_type_list[-2]
                    # print "**expr_list2[%d] req=%s" % (arg_cnt, arg_type)
                    la1 = self.LA(1)
                    if False:
                        pass
                    elif la1 and la1 in [SEMICOLON]:
                        pass
                        self.match(SEMICOLON)
                    elif la1 and la1 in [COMMA]:
                        pass
                        self.match(COMMA)
                    else:
                            raise antlr.NoViableAltException(self.LT(1), self.getFilename())

                    la1 = self.LA(1)
                    if False:
                        pass
                    elif la1 and la1 in [TRUE_CONST,FALSE_CONST,STR_CONST,NUM_CONST,INT_CONST,FUNC_IF,FUNC_CHOOSE,NAME,QUOTENAME,SUB,LP,REF2D]:
                        pass
                        self.expr(arg_type)
                    elif la1 and la1 in [RP,COMMA,SEMICOLON]:
                        pass
                        self.rpn += struct.pack("B", ptgMissArg)
                    else:
                            raise antlr.NoViableAltException(self.LT(1), self.getFilename())

                    arg_cnt += 1
                else:
                    break

        elif la1 and la1 in [RP]:
            pass
        else:
                raise antlr.NoViableAltException(self.LT(1), self.getFilename())

        return arg_cnt


_tokenNames = [
    "<0>",
    "EOF",
    "<2>",
    "NULL_TREE_LOOKAHEAD",
    "TRUE_CONST",
    "FALSE_CONST",
    "STR_CONST",
    "NUM_CONST",
    "INT_CONST",
    "FUNC_IF",
    "FUNC_CHOOSE",
    "NAME",
    "QUOTENAME",
    "EQ",
    "NE",
    "GT",
    "LT",
    "GE",
    "LE",
    "ADD",
    "SUB",
    "MUL",
    "DIV",
    "POWER",
    "PERCENT",
    "LP",
    "RP",
    "LB",
    "RB",
    "COLON",
    "COMMA",
    "SEMICOLON",
    "REF2D",
    "REF2D_R1C1",
    "BANG",
    "CONCAT"
]


### generate bit set
def mk_tokenSet_0():
    ### var1
    data = [ 37681618946L, 0L]
    return data
_tokenSet_0 = antlr.BitSet(mk_tokenSet_0())


########NEW FILE########
__FILENAME__ = ExcelMagic
# -*- coding: ascii -*-
"""
lots of Excel Magic Numbers
"""

# Boundaries BIFF8+

MAX_ROW = 65536
MAX_COL = 256


biff_records = {
    0x0000: "DIMENSIONS",
    0x0001: "BLANK",
    0x0002: "INTEGER",
    0x0003: "NUMBER",
    0x0004: "LABEL",
    0x0005: "BOOLERR",
    0x0006: "FORMULA",
    0x0007: "STRING",
    0x0008: "ROW",
    0x0009: "BOF",
    0x000A: "EOF",
    0x000B: "INDEX",
    0x000C: "CALCCOUNT",
    0x000D: "CALCMODE",
    0x000E: "PRECISION",
    0x000F: "REFMODE",
    0x0010: "DELTA",
    0x0011: "ITERATION",
    0x0012: "PROTECT",
    0x0013: "PASSWORD",
    0x0014: "HEADER",
    0x0015: "FOOTER",
    0x0016: "EXTERNCOUNT",
    0x0017: "EXTERNSHEET",
    0x0018: "NAME",
    0x0019: "WINDOWPROTECT",
    0x001A: "VERTICALPAGEBREAKS",
    0x001B: "HORIZONTALPAGEBREAKS",
    0x001C: "NOTE",
    0x001D: "SELECTION",
    0x001E: "FORMAT",
    0x001F: "FORMATCOUNT",
    0x0020: "COLUMNDEFAULT",
    0x0021: "ARRAY",
    0x0022: "1904",
    0x0023: "EXTERNNAME",
    0x0024: "COLWIDTH",
    0x0025: "DEFAULTROWHEIGHT",
    0x0026: "LEFTMARGIN",
    0x0027: "RIGHTMARGIN",
    0x0028: "TOPMARGIN",
    0x0029: "BOTTOMMARGIN",
    0x002A: "PRINTHEADERS",
    0x002B: "PRINTGRIDLINES",
    0x002F: "FILEPASS",
    0x0031: "FONT",
    0x0036: "TABLE",
    0x003C: "CONTINUE",
    0x003D: "WINDOW1",
    0x003E: "WINDOW2",
    0x0040: "BACKUP",
    0x0041: "PANE",
    0x0042: "CODEPAGE",
    0x0043: "XF",
    0x0044: "IXFE",
    0x0045: "EFONT",
    0x004D: "PLS",
    0x0050: "DCON",
    0x0051: "DCONREF",
    0x0053: "DCONNAME",
    0x0055: "DEFCOLWIDTH",
    0x0056: "BUILTINFMTCNT",
    0x0059: "XCT",
    0x005A: "CRN",
    0x005B: "FILESHARING",
    0x005C: "WRITEACCESS",
    0x005D: "OBJ",
    0x005E: "UNCALCED",
    0x005F: "SAFERECALC",
    0x0060: "TEMPLATE",
    0x0063: "OBJPROTECT",
    0x007D: "COLINFO",
    0x007E: "RK",
    0x007F: "IMDATA",
    0x0080: "GUTS",
    0x0081: "WSBOOL",
    0x0082: "GRIDSET",
    0x0083: "HCENTER",
    0x0084: "VCENTER",
    0x0085: "BOUNDSHEET",
    0x0086: "WRITEPROT",
    0x0087: "ADDIN",
    0x0088: "EDG",
    0x0089: "PUB",
    0x008C: "COUNTRY",
    0x008D: "HIDEOBJ",
    0x008E: "BUNDLESOFFSET",
    0x008F: "BUNDLEHEADER",
    0x0090: "SORT",
    0x0091: "SUB",
    0x0092: "PALETTE",
    0x0093: "STYLE",
    0x0094: "LHRECORD",
    0x0095: "LHNGRAPH",
    0x0096: "SOUND",
    0x0098: "LPR",
    0x0099: "STANDARDWIDTH",
    0x009A: "FNGROUPNAME",
    0x009B: "FILTERMODE",
    0x009C: "FNGROUPCOUNT",
    0x009D: "AUTOFILTERINFO",
    0x009E: "AUTOFILTER",
    0x00A0: "SCL",
    0x00A1: "SETUP",
    0x00A9: "COORDLIST",
    0x00AB: "GCW",
    0x00AE: "SCENMAN",
    0x00AF: "SCENARIO",
    0x00B0: "SXVIEW",
    0x00B1: "SXVD",
    0x00B2: "SXVI",
    0x00B4: "SXIVD",
    0x00B5: "SXLI",
    0x00B6: "SXPI",
    0x00B8: "DOCROUTE",
    0x00B9: "RECIPNAME",
    0x00BC: "SHRFMLA",
    0x00BD: "MULRK",
    0x00BE: "MULBLANK",
    0x00C1: "MMS",
    0x00C2: "ADDMENU",
    0x00C3: "DELMENU",
    0x00C5: "SXDI",
    0x00C6: "SXDB",
    0x00C7: "SXFIELD",
    0x00C8: "SXINDEXLIST",
    0x00C9: "SXDOUBLE",
    0x00CD: "SXSTRING",
    0x00CE: "SXDATETIME",
    0x00D0: "SXTBL",
    0x00D1: "SXTBRGITEM",
    0x00D2: "SXTBPG",
    0x00D3: "OBPROJ",
    0x00D5: "SXIDSTM",
    0x00D6: "RSTRING",
    0x00D7: "DBCELL",
    0x00DA: "BOOKBOOL",
    0x00DC: "SXEXT|PARAMQRY",
    0x00DD: "SCENPROTECT",
    0x00DE: "OLESIZE",
    0x00DF: "UDDESC",
    0x00E0: "XF",
    0x00E1: "INTERFACEHDR",
    0x00E2: "INTERFACEEND",
    0x00E3: "SXVS",
    0x00E5: "MERGEDCELLS",
    0x00E9: "BITMAP",
    0x00EB: "MSODRAWINGGROUP",
    0x00EC: "MSODRAWING",
    0x00ED: "MSODRAWINGSELECTION",
    0x00F0: "SXRULE",
    0x00F1: "SXEX",
    0x00F2: "SXFILT",
    0x00F6: "SXNAME",
    0x00F7: "SXSELECT",
    0x00F8: "SXPAIR",
    0x00F9: "SXFMLA",
    0x00FB: "SXFORMAT",
    0x00FC: "SST",
    0x00FD: "LABELSST",
    0x00FF: "EXTSST",
    0x0100: "SXVDEX",
    0x0103: "SXFORMULA",
    0x0122: "SXDBEX",
    0x0137: "CHTRINSERT",
    0x0138: "CHTRINFO",
    0x013B: "CHTRCELLCONTENT",
    0x013D: "TABID",
    0x0140: "CHTRMOVERANGE",
    0x014D: "CHTRINSERTTAB",
    0x015F: "LABELRANGES",
    0x0160: "USESELFS",
    0x0161: "DSF",
    0x0162: "XL5MODIFY",
    0x0196: "CHTRHEADER",
    0x01A9: "USERBVIEW",
    0x01AA: "USERSVIEWBEGIN",
    0x01AB: "USERSVIEWEND",
    0x01AD: "QSI",
    0x01AE: "SUPBOOK",
    0x01AF: "PROT4REV",
    0x01B0: "CONDFMT",
    0x01B1: "CF",
    0x01B2: "DVAL",
    0x01B5: "DCONBIN",
    0x01B6: "TXO",
    0x01B7: "REFRESHALL",
    0x01B8: "HLINK",
    0x01BA: "CODENAME",
    0x01BB: "SXFDBTYPE",
    0x01BC: "PROT4REVPASS",
    0x01BE: "DV",
    0x01C0: "XL9FILE",
    0x01C1: "RECALCID",
    0x0200: "DIMENSIONS",
    0x0201: "BLANK",
    0x0203: "NUMBER",
    0x0204: "LABEL",
    0x0205: "BOOLERR",
    0x0206: "FORMULA",
    0x0207: "STRING",
    0x0208: "ROW",
    0x0209: "BOF",
    0x020B: "INDEX",
    0x0218: "NAME",
    0x0221: "ARRAY",
    0x0223: "EXTERNNAME",
    0x0225: "DEFAULTROWHEIGHT",
    0x0231: "FONT",
    0x0236: "TABLE",
    0x023E: "WINDOW2",
    0x0243: "XF",
    0x027E: "RK",
    0x0293: "STYLE",
    0x0406: "FORMULA",
    0x0409: "BOF",
    0x041E: "FORMAT",
    0x0443: "XF",
    0x04BC: "SHRFMLA",
    0x0800: "SCREENTIP",
    0x0803: "WEBQRYSETTINGS",
    0x0804: "WEBQRYTABLES",
    0x0809: "BOF",
    0x0862: "SHEETLAYOUT",
    0x0867: "SHEETPROTECTION",
    0x1001: "UNITS",
    0x1002: "ChartChart",
    0x1003: "ChartSeries",
    0x1006: "ChartDataformat",
    0x1007: "ChartLineformat",
    0x1009: "ChartMarkerformat",
    0x100A: "ChartAreaformat",
    0x100B: "ChartPieformat",
    0x100C: "ChartAttachedlabel",
    0x100D: "ChartSeriestext",
    0x1014: "ChartChartformat",
    0x1015: "ChartLegend",
    0x1016: "ChartSerieslist",
    0x1017: "ChartBar",
    0x1018: "ChartLine",
    0x1019: "ChartPie",
    0x101A: "ChartArea",
    0x101B: "ChartScatter",
    0x101C: "ChartChartline",
    0x101D: "ChartAxis",
    0x101E: "ChartTick",
    0x101F: "ChartValuerange",
    0x1020: "ChartCatserrange",
    0x1021: "ChartAxislineformat",
    0x1022: "ChartFormatlink",
    0x1024: "ChartDefaulttext",
    0x1025: "ChartText",
    0x1026: "ChartFontx",
    0x1027: "ChartObjectLink",
    0x1032: "ChartFrame",
    0x1033: "BEGIN",
    0x1034: "END",
    0x1035: "ChartPlotarea",
    0x103A: "Chart3D",
    0x103C: "ChartPicf",
    0x103D: "ChartDropbar",
    0x103E: "ChartRadar",
    0x103F: "ChartSurface",
    0x1040: "ChartRadararea",
    0x1041: "ChartAxisparent",
    0x1043: "ChartLegendxn",
    0x1044: "ChartShtprops",
    0x1045: "ChartSertocrt",
    0x1046: "ChartAxesused",
    0x1048: "ChartSbaseref",
    0x104A: "ChartSerparent",
    0x104B: "ChartSerauxtrend",
    0x104E: "ChartIfmt",
    0x104F: "ChartPos",
    0x1050: "ChartAlruns",
    0x1051: "ChartAI",
    0x105B: "ChartSerauxerrbar",
    0x105D: "ChartSerfmt",
    0x105F: "Chart3DDataFormat",
    0x1060: "ChartFbi",
    0x1061: "ChartBoppop",
    0x1062: "ChartAxcext",
    0x1063: "ChartDat",
    0x1064: "ChartPlotgrowth",
    0x1065: "ChartSiindex",
    0x1066: "ChartGelframe",
    0x1067: "ChartBoppcustom",
    0xFFFF: ""
}


all_funcs_by_name = {
    # Includes Analysis ToolPak aka ATP aka add-in aka xcall functions,
    # distinguished by -ve opcode.
    # name: (opcode, min # args, max # args, func return type, func arg types)
    # + in func arg types means more of the same.
    'ABS'         : ( 24, 1,  1, 'V', 'V'),
    'ACCRINT'     : ( -1, 6,  7, 'V', 'VVVVVVV'),
    'ACCRINTM'    : ( -1, 3,  5, 'V', 'VVVVV'),
    'ACOS'        : ( 99, 1,  1, 'V', 'V'),
    'ACOSH'       : (233, 1,  1, 'V', 'V'),
    'ADDRESS'     : (219, 2,  5, 'V', 'VVVVV'),
    'AMORDEGRC'   : ( -1, 7,  7, 'V', 'VVVVVVV'),
    'AMORLINC'    : ( -1, 7,  7, 'V', 'VVVVVVV'),
    'AND'         : ( 36, 1, 30, 'V', 'D+'),
    'AREAS'       : ( 75, 1,  1, 'V', 'R'),
    'ASC'         : (214, 1,  1, 'V', 'V'),
    'ASIN'        : ( 98, 1,  1, 'V', 'V'),
    'ASINH'       : (232, 1,  1, 'V', 'V'),
    'ATAN'        : ( 18, 1,  1, 'V', 'V'),
    'ATAN2'       : ( 97, 2,  2, 'V', 'VV'),
    'ATANH'       : (234, 1,  1, 'V', 'V'),
    'AVEDEV'      : (269, 1, 30, 'V', 'D+'),
    'AVERAGE'     : (  5, 1, 30, 'V', 'D+'),
    'AVERAGEA'    : (361, 1, 30, 'V', 'D+'),
    'BAHTTEXT'    : (368, 1,  1, 'V', 'V'),
    'BESSELI'     : ( -1, 2,  2, 'V', 'VV'),
    'BESSELJ'     : ( -1, 2,  2, 'V', 'VV'),
    'BESSELK'     : ( -1, 2,  2, 'V', 'VV'),
    'BESSELY'     : ( -1, 2,  2, 'V', 'VV'),
    'BETADIST'    : (270, 3,  5, 'V', 'VVVVV'),
    'BETAINV'     : (272, 3,  5, 'V', 'VVVVV'),
    'BIN2DEC'     : ( -1, 1,  1, 'V', 'V'),
    'BIN2HEX'     : ( -1, 1,  2, 'V', 'VV'),
    'BIN2OCT'     : ( -1, 1,  2, 'V', 'VV'),
    'BINOMDIST'   : (273, 4,  4, 'V', 'VVVV'),
    'CEILING'     : (288, 2,  2, 'V', 'VV'),
    'CELL'        : (125, 1,  2, 'V', 'VR'),
    'CHAR'        : (111, 1,  1, 'V', 'V'),
    'CHIDIST'     : (274, 2,  2, 'V', 'VV'),
    'CHIINV'      : (275, 2,  2, 'V', 'VV'),
    'CHITEST'     : (306, 2,  2, 'V', 'AA'),
    'CHOOSE'      : (100, 2, 30, 'R', 'VR+'),
    'CLEAN'       : (162, 1,  1, 'V', 'V'),
    'CODE'        : (121, 1,  1, 'V', 'V'),
    'COLUMN'      : (  9, 0,  1, 'V', 'R'),
    'COLUMNS'     : ( 77, 1,  1, 'V', 'R'),
    'COMBIN'      : (276, 2,  2, 'V', 'VV'),
    'COMPLEX'     : ( -1, 2,  3, 'V', 'VVV'),
    'CONCATENATE' : (336, 1, 30, 'V', 'V+'),
    'CONFIDENCE'  : (277, 3,  3, 'V', 'VVV'),
    'CONVERT'     : ( -1, 3,  3, 'V', 'VVV'),
    'CORREL'      : (307, 2,  2, 'V', 'AA'),
    'COS'         : ( 16, 1,  1, 'V', 'V'),
    'COSH'        : (230, 1,  1, 'V', 'V'),
    'COUNT'       : (  0, 1, 30, 'V', 'D+'),
    'COUNTA'      : (169, 1, 30, 'V', 'D+'),
    'COUNTBLANK'  : (347, 1,  1, 'V', 'R'),
    'COUNTIF'     : (346, 2,  2, 'V', 'RV'),
    'COUPDAYBS'   : ( -1, 3,  5, 'V', 'VVVVV'),
    'COUPDAYS'    : ( -1, 3,  5, 'V', 'VVVVV'),
    'COUPDAYSNC'  : ( -1, 3,  5, 'V', 'VVVVV'),
    'COUPNCD'     : ( -1, 3,  5, 'V', 'VVVVV'),
    'COUPNUM'     : ( -1, 3,  5, 'V', 'VVVVV'),
    'COUPPCD'     : ( -1, 3,  5, 'V', 'VVVVV'),
    'COVAR'       : (308, 2,  2, 'V', 'AA'),
    'CRITBINOM'   : (278, 3,  3, 'V', 'VVV'),
    'CUMIPMT'     : ( -1, 6,  6, 'V', 'VVVVVV'),
    'CUMPRINC'    : ( -1, 6,  6, 'V', 'VVVVVV'),
    'DATE'        : ( 65, 3,  3, 'V', 'VVV'),
    'DATEDIF'     : (351, 3,  3, 'V', 'VVV'),
    'DATEVALUE'   : (140, 1,  1, 'V', 'V'),
    'DAVERAGE'    : ( 42, 3,  3, 'V', 'RRR'),
    'DAY'         : ( 67, 1,  1, 'V', 'V'),
    'DAYS360'     : (220, 2,  3, 'V', 'VVV'),
    'DB'          : (247, 4,  5, 'V', 'VVVVV'),
    'DBCS'        : (215, 1,  1, 'V', 'V'),
    'DCOUNT'      : ( 40, 3,  3, 'V', 'RRR'),
    'DCOUNTA'     : (199, 3,  3, 'V', 'RRR'),
    'DDB'         : (144, 4,  5, 'V', 'VVVVV'),
    'DEC2BIN'     : ( -1, 1,  2, 'V', 'VV'),
    'DEC2HEX'     : ( -1, 1,  2, 'V', 'VV'),
    'DEC2OCT'     : ( -1, 1,  2, 'V', 'VV'),
    'DEGREES'     : (343, 1,  1, 'V', 'V'),
    'DELTA'       : ( -1, 1,  2, 'V', 'VV'),
    'DEVSQ'       : (318, 1, 30, 'V', 'D+'),
    'DGET'        : (235, 3,  3, 'V', 'RRR'),
    'DISC'        : ( -1, 4,  5, 'V', 'VVVVV'),
    'DMAX'        : ( 44, 3,  3, 'V', 'RRR'),
    'DMIN'        : ( 43, 3,  3, 'V', 'RRR'),
    'DOLLAR'      : ( 13, 1,  2, 'V', 'VV'),
    'DOLLARDE'    : ( -1, 2,  2, 'V', 'VV'),
    'DOLLARFR'    : ( -1, 2,  2, 'V', 'VV'),
    'DPRODUCT'    : (189, 3,  3, 'V', 'RRR'),
    'DSTDEV'      : ( 45, 3,  3, 'V', 'RRR'),
    'DSTDEVP'     : (195, 3,  3, 'V', 'RRR'),
    'DSUM'        : ( 41, 3,  3, 'V', 'RRR'),
    'DURATION'    : ( -1, 5,  6, 'V', 'VVVVVV'),
    'DVAR'        : ( 47, 3,  3, 'V', 'RRR'),
    'DVARP'       : (196, 3,  3, 'V', 'RRR'),
    'EDATE'       : ( -1, 2,  2, 'V', 'VV'),
    'EFFECT'      : ( -1, 2,  2, 'V', 'VV'),
    'EOMONTH'     : ( -1, 1,  2, 'V', 'VV'),
    'ERF'         : ( -1, 1,  2, 'V', 'VV'),
    'ERFC'        : ( -1, 1,  1, 'V', 'V'),
    'ERROR.TYPE'  : (261, 1,  1, 'V', 'V'),
    'EVEN'        : (279, 1,  1, 'V', 'V'),
    'EXACT'       : (117, 2,  2, 'V', 'VV'),
    'EXP'         : ( 21, 1,  1, 'V', 'V'),
    'EXPONDIST'   : (280, 3,  3, 'V', 'VVV'),
    'FACT'        : (184, 1,  1, 'V', 'V'),
    'FACTDOUBLE'  : ( -1, 1,  1, 'V', 'V'),
    'FALSE'       : ( 35, 0,  0, 'V', '-'),
    'FDIST'       : (281, 3,  3, 'V', 'VVV'),
    'FIND'        : (124, 2,  3, 'V', 'VVV'),
    'FINDB'       : (205, 2,  3, 'V', 'VVV'),
    'FINV'        : (282, 3,  3, 'V', 'VVV'),
    'FISHER'      : (283, 1,  1, 'V', 'V'),
    'FISHERINV'   : (284, 1,  1, 'V', 'V'),
    'FIXED'       : ( 14, 2,  3, 'V', 'VVV'),
    'FLOOR'       : (285, 2,  2, 'V', 'VV'),
    'FORECAST'    : (309, 3,  3, 'V', 'VAA'),
    'FREQUENCY'   : (252, 2,  2, 'A', 'RR'),
    'FTEST'       : (310, 2,  2, 'V', 'AA'),
    'FV'          : ( 57, 3,  5, 'V', 'VVVVV'),
    'FVSCHEDULE'  : ( -1, 2,  2, 'V', 'VA'),
    'GAMMADIST'   : (286, 4,  4, 'V', 'VVVV'),
    'GAMMAINV'    : (287, 3,  3, 'V', 'VVV'),
    'GAMMALN'     : (271, 1,  1, 'V', 'V'),
    'GCD'         : ( -1, 1, 29, 'V', 'V+'),
    'GEOMEAN'     : (319, 1, 30, 'V', 'D+'),
    'GESTEP'      : ( -1, 1,  2, 'V', 'VV'),
    'GETPIVOTDATA': (358, 2, 30, 'A', 'VAV+'),
    'GROWTH'      : ( 52, 1,  4, 'A', 'RRRV'),
    'HARMEAN'     : (320, 1, 30, 'V', 'D+'),
    'HEX2BIN'     : ( -1, 1,  2, 'V', 'VV'),
    'HEX2DEC'     : ( -1, 1,  1, 'V', 'V'),
    'HEX2OCT'     : ( -1, 1,  2, 'V', 'VV'),
    'HLOOKUP'     : (101, 3,  4, 'V', 'VRRV'),
    'HOUR'        : ( 71, 1,  1, 'V', 'V'),
    'HYPERLINK'   : (359, 1,  2, 'V', 'VV'),
    'HYPGEOMDIST' : (289, 4,  4, 'V', 'VVVV'),
    'IF'          : (  1, 2,  3, 'R', 'VRR'),
    'IMABS'       : ( -1, 1,  1, 'V', 'V'),
    'IMAGINARY'   : ( -1, 1,  1, 'V', 'V'),
    'IMARGUMENT'  : ( -1, 1,  1, 'V', 'V'),
    'IMCONJUGATE' : ( -1, 1,  1, 'V', 'V'),
    'IMCOS'       : ( -1, 1,  1, 'V', 'V'),
    'IMDIV'       : ( -1, 2,  2, 'V', 'VV'),
    'IMEXP'       : ( -1, 1,  1, 'V', 'V'),
    'IMLN'        : ( -1, 1,  1, 'V', 'V'),
    'IMLOG10'     : ( -1, 1,  1, 'V', 'V'),
    'IMLOG2'      : ( -1, 1,  1, 'V', 'V'),
    'IMPOWER'     : ( -1, 2,  2, 'V', 'VV'),
    'IMPRODUCT'   : ( -1, 2,  2, 'V', 'VV'),
    'IMREAL'      : ( -1, 1,  1, 'V', 'V'),
    'IMSIN'       : ( -1, 1,  1, 'V', 'V'),
    'IMSQRT'      : ( -1, 1,  1, 'V', 'V'),
    'IMSUB'       : ( -1, 2,  2, 'V', 'VV'),
    'IMSUM'       : ( -1, 1, 29, 'V', 'V+'),
    'INDEX'       : ( 29, 2,  4, 'R', 'RVVV'),
    'INDIRECT'    : (148, 1,  2, 'R', 'VV'),
    'INFO'        : (244, 1,  1, 'V', 'V'),
    'INT'         : ( 25, 1,  1, 'V', 'V'),
    'INTERCEPT'   : (311, 2,  2, 'V', 'AA'),
    'INTRATE'     : ( -1, 4,  5, 'V', 'VVVVV'),
    'IPMT'        : (167, 4,  6, 'V', 'VVVVVV'),
    'IRR'         : ( 62, 1,  2, 'V', 'RV'),
    'ISBLANK'     : (129, 1,  1, 'V', 'V'),
    'ISERR'       : (126, 1,  1, 'V', 'V'),
    'ISERROR'     : (  3, 1,  1, 'V', 'V'),
    'ISEVEN'      : ( -1, 1,  1, 'V', 'V'),
    'ISLOGICAL'   : (198, 1,  1, 'V', 'V'),
    'ISNA'        : (  2, 1,  1, 'V', 'V'),
    'ISNONTEXT'   : (190, 1,  1, 'V', 'V'),
    'ISNUMBER'    : (128, 1,  1, 'V', 'V'),
    'ISODD'       : ( -1, 1,  1, 'V', 'V'),
    'ISPMT'       : (350, 4,  4, 'V', 'VVVV'),
    'ISREF'       : (105, 1,  1, 'V', 'R'),
    'ISTEXT'      : (127, 1,  1, 'V', 'V'),
    'KURT'        : (322, 1, 30, 'V', 'D+'),
    'LARGE'       : (325, 2,  2, 'V', 'RV'),
    'LCM'         : ( -1, 1, 29, 'V', 'V+'),
    'LEFT'        : (115, 1,  2, 'V', 'VV'),
    'LEFTB'       : (208, 1,  2, 'V', 'VV'),
    'LEN'         : ( 32, 1,  1, 'V', 'V'),
    'LENB'        : (211, 1,  1, 'V', 'V'),
    'LINEST'      : ( 49, 1,  4, 'A', 'RRVV'),
    'LN'          : ( 22, 1,  1, 'V', 'V'),
    'LOG'         : (109, 1,  2, 'V', 'VV'),
    'LOG10'       : ( 23, 1,  1, 'V', 'V'),
    'LOGEST'      : ( 51, 1,  4, 'A', 'RRVV'),
    'LOGINV'      : (291, 3,  3, 'V', 'VVV'),
    'LOGNORMDIST' : (290, 3,  3, 'V', 'VVV'),
    'LOOKUP'      : ( 28, 2,  3, 'V', 'VRR'),
    'LOWER'       : (112, 1,  1, 'V', 'V'),
    'MATCH'       : ( 64, 2,  3, 'V', 'VRR'),
    'MAX'         : (  7, 1, 30, 'V', 'D+'),
    'MAXA'        : (362, 1, 30, 'V', 'D+'),
    'MDETERM'     : (163, 1,  1, 'V', 'A'),
    'MDURATION'   : ( -1, 5,  6, 'V', 'VVVVVV'),
    'MEDIAN'      : (227, 1, 30, 'V', 'D+'),
    'MID'         : ( 31, 3,  3, 'V', 'VVV'),
    'MIDB'        : (210, 3,  3, 'V', 'VVV'),
    'MIN'         : (  6, 1, 30, 'V', 'D+'),
    'MINA'        : (363, 1, 30, 'V', 'D+'),
    'MINUTE'      : ( 72, 1,  1, 'V', 'V'),
    'MINVERSE'    : (164, 1,  1, 'A', 'A'),
    'MIRR'        : ( 61, 3,  3, 'V', 'RVV'),
    'MMULT'       : (165, 2,  2, 'A', 'AA'),
    'MOD'         : ( 39, 2,  2, 'V', 'VV'),
    'MODE'        : (330, 1, 30, 'V', 'A+'), ################ weird #################
    'MONTH'       : ( 68, 1,  1, 'V', 'V'),
    'MROUND'      : ( -1, 2,  2, 'V', 'VV'),
    'MULTINOMIAL' : ( -1, 1, 29, 'V', 'V+'),
    'N'           : (131, 1,  1, 'V', 'R'),
    'NA'          : ( 10, 0,  0, 'V', '-'),
    'NEGBINOMDIST': (292, 3,  3, 'V', 'VVV'),
    'NETWORKDAYS' : ( -1, 2,  3, 'V', 'VVR'),
    'NOMINAL'     : ( -1, 2,  2, 'V', 'VV'),
    'NORMDIST'    : (293, 4,  4, 'V', 'VVVV'),
    'NORMINV'     : (295, 3,  3, 'V', 'VVV'),
    'NORMSDIST'   : (294, 1,  1, 'V', 'V'),
    'NORMSINV'    : (296, 1,  1, 'V', 'V'),
    'NOT'         : ( 38, 1,  1, 'V', 'V'),
    'NOW'         : ( 74, 0,  0, 'V', '-'),
    'NPER'        : ( 58, 3,  5, 'V', 'VVVVV'),
    'NPV'         : ( 11, 2, 30, 'V', 'VD+'),
    'OCT2BIN'     : ( -1, 1,  2, 'V', 'VV'),
    'OCT2DEC'     : ( -1, 1,  1, 'V', 'V'),
    'OCT2HEX'     : ( -1, 1,  2, 'V', 'VV'),
    'ODD'         : (298, 1,  1, 'V', 'V'),
    'ODDFPRICE'   : ( -1, 9,  9, 'V', 'VVVVVVVVV'),
    'ODDFYIELD'   : ( -1, 9,  9, 'V', 'VVVVVVVVV'),
    'ODDLPRICE'   : ( -1, 8,  8, 'V', 'VVVVVVVV'),
    'ODDLYIELD'   : ( -1, 8,  8, 'V', 'VVVVVVVV'),
    'OFFSET'      : ( 78, 3,  5, 'R', 'RVVVV'),
    'OR'          : ( 37, 1, 30, 'V', 'D+'),
    'PEARSON'     : (312, 2,  2, 'V', 'AA'),
    'PERCENTILE'  : (328, 2,  2, 'V', 'RV'),
    'PERCENTRANK' : (329, 2,  3, 'V', 'RVV'),
    'PERMUT'      : (299, 2,  2, 'V', 'VV'),
    'PHONETIC'    : (360, 1,  1, 'V', 'R'),
    'PI'          : ( 19, 0,  0, 'V', '-'),
    'PMT'         : ( 59, 3,  5, 'V', 'VVVVV'),
    'POISSON'     : (300, 3,  3, 'V', 'VVV'),
    'POWER'       : (337, 2,  2, 'V', 'VV'),
    'PPMT'        : (168, 4,  6, 'V', 'VVVVVV'),
    'PRICE'       : ( -1, 6,  7, 'V', 'VVVVVVV'),
    'PRICEDISC'   : ( -1, 4,  5, 'V', 'VVVVV'),
    'PRICEMAT'    : ( -1, 5,  6, 'V', 'VVVVVV'),
    'PROB'        : (317, 3,  4, 'V', 'AAVV'),
    'PRODUCT'     : (183, 1, 30, 'V', 'D+'),
    'PROPER'      : (114, 1,  1, 'V', 'V'),
    'PV'          : ( 56, 3,  5, 'V', 'VVVVV'),
    'QUARTILE'    : (327, 2,  2, 'V', 'RV'),
    'QUOTIENT'    : ( -1, 2,  2, 'V', 'VV'),
    'RADIANS'     : (342, 1,  1, 'V', 'V'),
    'RAND'        : ( 63, 0,  0, 'V', '-'),
    'RANDBETWEEN' : ( -1, 2,  2, 'V', 'VV'),
    'RANK'        : (216, 2,  3, 'V', 'VRV'),
    'RATE'        : ( 60, 3,  6, 'V', 'VVVVVV'),
    'RECEIVED'    : ( -1, 4,  5, 'V', 'VVVVV'),
    'REPLACE'     : (119, 4,  4, 'V', 'VVVV'),
    'REPLACEB'    : (207, 4,  4, 'V', 'VVVV'),
    'REPT'        : ( 30, 2,  2, 'V', 'VV'),
    'RIGHT'       : (116, 1,  2, 'V', 'VV'),
    'RIGHTB'      : (209, 1,  2, 'V', 'VV'),
    'ROMAN'       : (354, 1,  2, 'V', 'VV'),
    'ROUND'       : ( 27, 2,  2, 'V', 'VV'),
    'ROUNDDOWN'   : (213, 2,  2, 'V', 'VV'),
    'ROUNDUP'     : (212, 2,  2, 'V', 'VV'),
    'ROW'         : (  8, 0,  1, 'V', 'R'),
    'ROWS'        : ( 76, 1,  1, 'V', 'R'),
    'RSQ'         : (313, 2,  2, 'V', 'AA'),
    'RTD'         : (379, 3, 30, 'A', 'VVV+'),
    'SEARCH'      : ( 82, 2,  3, 'V', 'VVV'),
    'SEARCHB'     : (206, 2,  3, 'V', 'VVV'),
    'SECOND'      : ( 73, 1,  1, 'V', 'V'),
    'SERIESSUM'   : ( -1, 4,  4, 'V', 'VVVA'),
    'SIGN'        : ( 26, 1,  1, 'V', 'V'),
    'SIN'         : ( 15, 1,  1, 'V', 'V'),
    'SINH'        : (229, 1,  1, 'V', 'V'),
    'SKEW'        : (323, 1, 30, 'V', 'D+'),
    'SLN'         : (142, 3,  3, 'V', 'VVV'),
    'SLOPE'       : (315, 2,  2, 'V', 'AA'),
    'SMALL'       : (326, 2,  2, 'V', 'RV'),
    'SQRT'        : ( 20, 1,  1, 'V', 'V'),
    'SQRTPI'      : ( -1, 1,  1, 'V', 'V'),
    'STANDARDIZE' : (297, 3,  3, 'V', 'VVV'),
    'STDEV'       : ( 12, 1, 30, 'V', 'D+'),
    'STDEVA'      : (366, 1, 30, 'V', 'D+'),
    'STDEVP'      : (193, 1, 30, 'V', 'D+'),
    'STDEVPA'     : (364, 1, 30, 'V', 'D+'),
    'STEYX'       : (314, 2,  2, 'V', 'AA'),
    'SUBSTITUTE'  : (120, 3,  4, 'V', 'VVVV'),
    'SUBTOTAL'    : (344, 2, 30, 'V', 'VR+'),
    'SUM'         : (  4, 1, 30, 'V', 'D+'),
    'SUMIF'       : (345, 2,  3, 'V', 'RVR'),
    'SUMPRODUCT'  : (228, 1, 30, 'V', 'A+'),
    'SUMSQ'       : (321, 1, 30, 'V', 'D+'),
    'SUMX2MY2'    : (304, 2,  2, 'V', 'AA'),
    'SUMX2PY2'    : (305, 2,  2, 'V', 'AA'),
    'SUMXMY2'     : (303, 2,  2, 'V', 'AA'),
    'SYD'         : (143, 4,  4, 'V', 'VVVV'),
    'T'           : (130, 1,  1, 'V', 'R'),
    'TAN'         : ( 17, 1,  1, 'V', 'V'),
    'TANH'        : (231, 1,  1, 'V', 'V'),
    'TBILLEQ'     : ( -1, 3,  3, 'V', 'VVV'),
    'TBILLPRICE'  : ( -1, 3,  3, 'V', 'VVV'),
    'TBILLYIELD'  : ( -1, 3,  3, 'V', 'VVV'),
    'TDIST'       : (301, 3,  3, 'V', 'VVV'),
    'TEXT'        : ( 48, 2,  2, 'V', 'VV'),
    'TIME'        : ( 66, 3,  3, 'V', 'VVV'),
    'TIMEVALUE'   : (141, 1,  1, 'V', 'V'),
    'TINV'        : (332, 2,  2, 'V', 'VV'),
    'TODAY'       : (221, 0,  0, 'V', '-'),
    'TRANSPOSE'   : ( 83, 1,  1, 'A', 'A'),
    'TREND'       : ( 50, 1,  4, 'A', 'RRRV'),
    'TRIM'        : (118, 1,  1, 'V', 'V'),
    'TRIMMEAN'    : (331, 2,  2, 'V', 'RV'),
    'TRUE'        : ( 34, 0,  0, 'V', '-'),
    'TRUNC'       : (197, 1,  2, 'V', 'VV'),
    'TTEST'       : (316, 4,  4, 'V', 'AAVV'),
    'TYPE'        : ( 86, 1,  1, 'V', 'V'),
    'UPPER'       : (113, 1,  1, 'V', 'V'),
    'USDOLLAR'    : (204, 1,  2, 'V', 'VV'),
    'VALUE'       : ( 33, 1,  1, 'V', 'V'),
    'VAR'         : ( 46, 1, 30, 'V', 'D+'),
    'VARA'        : (367, 1, 30, 'V', 'D+'),
    'VARP'        : (194, 1, 30, 'V', 'D+'),
    'VARPA'       : (365, 1, 30, 'V', 'D+'),
    'VDB'         : (222, 5,  7, 'V', 'VVVVVVV'),
    'VLOOKUP'     : (102, 3,  4, 'V', 'VRRV'),
    'WEEKDAY'     : ( 70, 1,  2, 'V', 'VV'),
    'WEEKNUM'     : ( -1, 1,  2, 'V', 'VV'),
    'WEIBULL'     : (302, 4,  4, 'V', 'VVVV'),
    'WORKDAY'     : ( -1, 2,  3, 'V', 'VVR'),
    'XIRR'        : ( -1, 2,  3, 'V', 'AAV'),
    'XNPV'        : ( -1, 3,  3, 'V', 'VAA'),
    'YEAR'        : ( 69, 1,  1, 'V', 'V'),
    'YEARFRAC'    : ( -1, 2,  3, 'V', 'VVV'),
    'YIELD'       : ( -1, 6,  7, 'V', 'VVVVVVV'),
    'YIELDDISC'   : ( -1, 4,  5, 'V', 'VVVVV'),
    'YIELDMAT'    : ( -1, 5,  6, 'V', 'VVVVVV'),
    'ZTEST'       : (324, 2,  3, 'V', 'RVV'),
    }

# Formulas Parse things

ptgExp          = 0x01
ptgTbl          = 0x02
ptgAdd          = 0x03
ptgSub          = 0x04
ptgMul          = 0x05
ptgDiv          = 0x06
ptgPower        = 0x07
ptgConcat       = 0x08
ptgLT           = 0x09
ptgLE           = 0x0a
ptgEQ           = 0x0b
ptgGE           = 0x0c
ptgGT           = 0x0d
ptgNE           = 0x0e
ptgIsect        = 0x0f
ptgUnion        = 0x10
ptgRange        = 0x11
ptgUplus        = 0x12
ptgUminus       = 0x13
ptgPercent      = 0x14
ptgParen        = 0x15
ptgMissArg      = 0x16
ptgStr          = 0x17
ptgExtend       = 0x18
ptgAttr         = 0x19
ptgSheet        = 0x1a
ptgEndSheet     = 0x1b
ptgErr          = 0x1c
ptgBool         = 0x1d
ptgInt          = 0x1e
ptgNum          = 0x1f

ptgArrayR       = 0x20
ptgFuncR        = 0x21
ptgFuncVarR     = 0x22
ptgNameR        = 0x23
ptgRefR         = 0x24
ptgAreaR        = 0x25
ptgMemAreaR     = 0x26
ptgMemErrR      = 0x27
ptgMemNoMemR    = 0x28
ptgMemFuncR     = 0x29
ptgRefErrR      = 0x2a
ptgAreaErrR     = 0x2b
ptgRefNR        = 0x2c
ptgAreaNR       = 0x2d
ptgMemAreaNR    = 0x2e
ptgMemNoMemNR   = 0x2f
ptgNameXR       = 0x39
ptgRef3dR       = 0x3a
ptgArea3dR      = 0x3b
ptgRefErr3dR    = 0x3c
ptgAreaErr3dR   = 0x3d

ptgArrayV       = 0x40
ptgFuncV        = 0x41
ptgFuncVarV     = 0x42
ptgNameV        = 0x43
ptgRefV         = 0x44
ptgAreaV        = 0x45
ptgMemAreaV     = 0x46
ptgMemErrV      = 0x47
ptgMemNoMemV    = 0x48
ptgMemFuncV     = 0x49
ptgRefErrV      = 0x4a
ptgAreaErrV     = 0x4b
ptgRefNV        = 0x4c
ptgAreaNV       = 0x4d
ptgMemAreaNV    = 0x4e
ptgMemNoMemNV   = 0x4f
ptgFuncCEV      = 0x58
ptgNameXV       = 0x59
ptgRef3dV       = 0x5a
ptgArea3dV      = 0x5b
ptgRefErr3dV    = 0x5c
ptgAreaErr3dV   = 0x5d

ptgArrayA       = 0x60
ptgFuncA        = 0x61
ptgFuncVarA     = 0x62
ptgNameA        = 0x63
ptgRefA         = 0x64
ptgAreaA        = 0x65
ptgMemAreaA     = 0x66
ptgMemErrA      = 0x67
ptgMemNoMemA    = 0x68
ptgMemFuncA     = 0x69
ptgRefErrA      = 0x6a
ptgAreaErrA     = 0x6b
ptgRefNA        = 0x6c
ptgAreaNA       = 0x6d
ptgMemAreaNA    = 0x6e
ptgMemNoMemNA   = 0x6f
ptgFuncCEA      = 0x78
ptgNameXA       = 0x79
ptgRef3dA       = 0x7a
ptgArea3dA      = 0x7b
ptgRefErr3dA    = 0x7c
ptgAreaErr3dA   = 0x7d


PtgNames = {
    ptgExp         : "ptgExp",
    ptgTbl         : "ptgTbl",
    ptgAdd         : "ptgAdd",
    ptgSub         : "ptgSub",
    ptgMul         : "ptgMul",
    ptgDiv         : "ptgDiv",
    ptgPower       : "ptgPower",
    ptgConcat      : "ptgConcat",
    ptgLT          : "ptgLT",
    ptgLE          : "ptgLE",
    ptgEQ          : "ptgEQ",
    ptgGE          : "ptgGE",
    ptgGT          : "ptgGT",
    ptgNE          : "ptgNE",
    ptgIsect       : "ptgIsect",
    ptgUnion       : "ptgUnion",
    ptgRange       : "ptgRange",
    ptgUplus       : "ptgUplus",
    ptgUminus      : "ptgUminus",
    ptgPercent     : "ptgPercent",
    ptgParen       : "ptgParen",
    ptgMissArg     : "ptgMissArg",
    ptgStr         : "ptgStr",
    ptgExtend      : "ptgExtend",
    ptgAttr        : "ptgAttr",
    ptgSheet       : "ptgSheet",
    ptgEndSheet    : "ptgEndSheet",
    ptgErr         : "ptgErr",
    ptgBool        : "ptgBool",
    ptgInt         : "ptgInt",
    ptgNum         : "ptgNum",
    ptgArrayR      : "ptgArrayR",
    ptgFuncR       : "ptgFuncR",
    ptgFuncVarR    : "ptgFuncVarR",
    ptgNameR       : "ptgNameR",
    ptgRefR        : "ptgRefR",
    ptgAreaR       : "ptgAreaR",
    ptgMemAreaR    : "ptgMemAreaR",
    ptgMemErrR     : "ptgMemErrR",
    ptgMemNoMemR   : "ptgMemNoMemR",
    ptgMemFuncR    : "ptgMemFuncR",
    ptgRefErrR     : "ptgRefErrR",
    ptgAreaErrR    : "ptgAreaErrR",
    ptgRefNR       : "ptgRefNR",
    ptgAreaNR      : "ptgAreaNR",
    ptgMemAreaNR   : "ptgMemAreaNR",
    ptgMemNoMemNR  : "ptgMemNoMemNR",
    ptgNameXR      : "ptgNameXR",
    ptgRef3dR      : "ptgRef3dR",
    ptgArea3dR     : "ptgArea3dR",
    ptgRefErr3dR   : "ptgRefErr3dR",
    ptgAreaErr3dR  : "ptgAreaErr3dR",
    ptgArrayV      : "ptgArrayV",
    ptgFuncV       : "ptgFuncV",
    ptgFuncVarV    : "ptgFuncVarV",
    ptgNameV       : "ptgNameV",
    ptgRefV        : "ptgRefV",
    ptgAreaV       : "ptgAreaV",
    ptgMemAreaV    : "ptgMemAreaV",
    ptgMemErrV     : "ptgMemErrV",
    ptgMemNoMemV   : "ptgMemNoMemV",
    ptgMemFuncV    : "ptgMemFuncV",
    ptgRefErrV     : "ptgRefErrV",
    ptgAreaErrV    : "ptgAreaErrV",
    ptgRefNV       : "ptgRefNV",
    ptgAreaNV      : "ptgAreaNV",
    ptgMemAreaNV   : "ptgMemAreaNV",
    ptgMemNoMemNV  : "ptgMemNoMemNV",
    ptgFuncCEV     : "ptgFuncCEV",
    ptgNameXV      : "ptgNameXV",
    ptgRef3dV      : "ptgRef3dV",
    ptgArea3dV     : "ptgArea3dV",
    ptgRefErr3dV   : "ptgRefErr3dV",
    ptgAreaErr3dV  : "ptgAreaErr3dV",
    ptgArrayA      : "ptgArrayA",
    ptgFuncA       : "ptgFuncA",
    ptgFuncVarA    : "ptgFuncVarA",
    ptgNameA       : "ptgNameA",
    ptgRefA        : "ptgRefA",
    ptgAreaA       : "ptgAreaA",
    ptgMemAreaA    : "ptgMemAreaA",
    ptgMemErrA     : "ptgMemErrA",
    ptgMemNoMemA   : "ptgMemNoMemA",
    ptgMemFuncA    : "ptgMemFuncA",
    ptgRefErrA     : "ptgRefErrA",
    ptgAreaErrA    : "ptgAreaErrA",
    ptgRefNA       : "ptgRefNA",
    ptgAreaNA      : "ptgAreaNA",
    ptgMemAreaNA   : "ptgMemAreaNA",
    ptgMemNoMemNA  : "ptgMemNoMemNA",
    ptgFuncCEA     : "ptgFuncCEA",
    ptgNameXA      : "ptgNameXA",
    ptgRef3dA      : "ptgRef3dA",
    ptgArea3dA     : "ptgArea3dA",
    ptgRefErr3dA   : "ptgRefErr3dA",
    ptgAreaErr3dA  : "ptgAreaErr3dA"
}


error_msg_by_code = {
    0x00: u"#NULL!",  # intersection of two cell ranges is empty
    0x07: u"#DIV/0!", # division by zero
    0x0F: u"#VALUE!", # wrong type of operand
    0x17: u"#REF!",   # illegal or deleted cell reference
    0x1D: u"#NAME?",  # wrong function or range name
    0x24: u"#NUM!",   # value range overflow
    0x2A: u"#N/A"    # argument or function not available
}

########NEW FILE########
__FILENAME__ = Formatting
#!/usr/bin/env python
'''
The  XF  record is able to store explicit cell formatting attributes or the
attributes  of  a cell style. Explicit formatting includes the reference to
a  cell  style  XF  record. This allows to extend a defined cell style with
some  explicit  attributes.  The  formatting  attributes  are  divided into
6 groups:

Group           Attributes
-------------------------------------
Number format   Number format index (index to FORMAT record)
Font            Font index (index to FONT record)
Alignment       Horizontal and vertical alignment, text wrap, indentation,
                orientation/rotation, text direction
Border          Border line styles and colours
Background      Background area style and colours
Protection      Cell locked, formula hidden

For  each  group  a flag in the cell XF record specifies whether to use the
attributes  contained  in  that  XF  record  or  in  the  referenced  style
XF  record. In style XF records, these flags specify whether the attributes
will  overwrite  explicit  cell  formatting  when  the  style is applied to
a  cell. Changing a cell style (without applying this style to a cell) will
change  all  cells which already use that style and do not contain explicit
cell  attributes for the changed style attributes. If a cell XF record does
not  contain  explicit  attributes  in a group (if the attribute group flag
is not set), it repeats the attributes of its style XF record.

'''

import BIFFRecords

class Font(object):

    ESCAPEMENT_NONE         = 0x00
    ESCAPEMENT_SUPERSCRIPT  = 0x01
    ESCAPEMENT_SUBSCRIPT    = 0x02

    UNDERLINE_NONE          = 0x00
    UNDERLINE_SINGLE        = 0x01
    UNDERLINE_SINGLE_ACC    = 0x21
    UNDERLINE_DOUBLE        = 0x02
    UNDERLINE_DOUBLE_ACC    = 0x22

    FAMILY_NONE         = 0x00
    FAMILY_ROMAN        = 0x01
    FAMILY_SWISS        = 0x02
    FAMILY_MODERN       = 0x03
    FAMILY_SCRIPT       = 0x04
    FAMILY_DECORATIVE   = 0x05

    CHARSET_ANSI_LATIN          = 0x00
    CHARSET_SYS_DEFAULT         = 0x01
    CHARSET_SYMBOL              = 0x02
    CHARSET_APPLE_ROMAN         = 0x4D
    CHARSET_ANSI_JAP_SHIFT_JIS  = 0x80
    CHARSET_ANSI_KOR_HANGUL     = 0x81
    CHARSET_ANSI_KOR_JOHAB      = 0x82
    CHARSET_ANSI_CHINESE_GBK    = 0x86
    CHARSET_ANSI_CHINESE_BIG5   = 0x88
    CHARSET_ANSI_GREEK          = 0xA1
    CHARSET_ANSI_TURKISH        = 0xA2
    CHARSET_ANSI_VIETNAMESE     = 0xA3
    CHARSET_ANSI_HEBREW         = 0xB1
    CHARSET_ANSI_ARABIC         = 0xB2
    CHARSET_ANSI_BALTIC         = 0xBA
    CHARSET_ANSI_CYRILLIC       = 0xCC
    CHARSET_ANSI_THAI           = 0xDE
    CHARSET_ANSI_LATIN_II       = 0xEE
    CHARSET_OEM_LATIN_I         = 0xFF

    def __init__(self):
        # twip = 1/20 of a point = 1/1440 of a inch
        # usually resolution == 96 pixels per 1 inch
        # (rarely 120 pixels per 1 inch or another one)

        self.height = 0x00C8 # 200: this is font with height 10 points
        self.italic = False
        self.struck_out = False
        self.outline = False
        self.shadow = False
        self.colour_index = 0x7FFF
        self.bold = False
        self._weight = 0x0190 # 0x02BC gives bold font
        self.escapement = self.ESCAPEMENT_NONE
        self.underline = self.UNDERLINE_NONE
        self.family = self.FAMILY_NONE
        self.charset = self.CHARSET_SYS_DEFAULT
        self.name = 'Arial'

    def get_biff_record(self):
        height = self.height

        options = 0x00
        if self.bold:
            options |= 0x01
            self._weight = 0x02BC
        if self.italic:
            options |= 0x02
        if self.underline != self.UNDERLINE_NONE:
            options |= 0x04
        if self.struck_out:
            options |= 0x08
        if self.outline:
            options |= 0x010
        if self.shadow:
            options |= 0x020

        colour_index = self.colour_index
        weight = self._weight
        escapement = self.escapement
        underline = self.underline
        family = self.family
        charset = self.charset
        name = self.name

        return BIFFRecords.FontRecord(height, options, colour_index, weight, escapement,
                    underline, family, charset,
                    name)

    def _search_key(self):
        return (
            self.height,
            self.italic,
            self.struck_out,
            self.outline,
            self.shadow,
            self.colour_index,
            self.bold,
            self._weight,
            self.escapement,
            self.underline,
            self.family,
            self.charset,
            self.name,
            )

class Alignment(object):
    HORZ_GENERAL                = 0x00
    HORZ_LEFT                   = 0x01
    HORZ_CENTER                 = 0x02
    HORZ_RIGHT                  = 0x03
    HORZ_FILLED                 = 0x04
    HORZ_JUSTIFIED              = 0x05 # BIFF4-BIFF8X
    HORZ_CENTER_ACROSS_SEL      = 0x06 # Centred across selection (BIFF4-BIFF8X)
    HORZ_DISTRIBUTED            = 0x07 # Distributed (BIFF8X)

    VERT_TOP                    = 0x00
    VERT_CENTER                 = 0x01
    VERT_BOTTOM                 = 0x02
    VERT_JUSTIFIED              = 0x03 # Justified (BIFF5-BIFF8X)
    VERT_DISTRIBUTED            = 0x04 # Distributed (BIFF8X)

    DIRECTION_GENERAL           = 0x00 # BIFF8X
    DIRECTION_LR                = 0x01
    DIRECTION_RL                = 0x02

    ORIENTATION_NOT_ROTATED     = 0x00
    ORIENTATION_STACKED         = 0x01
    ORIENTATION_90_CC           = 0x02
    ORIENTATION_90_CW           = 0x03

    ROTATION_0_ANGLE            = 0x00
    ROTATION_STACKED            = 0xFF

    WRAP_AT_RIGHT               = 0x01
    NOT_WRAP_AT_RIGHT           = 0x00

    SHRINK_TO_FIT               = 0x01
    NOT_SHRINK_TO_FIT           = 0x00

    def __init__(self):
        self.horz = self.HORZ_GENERAL
        self.vert = self.VERT_BOTTOM
        self.dire = self.DIRECTION_GENERAL
        self.orie = self.ORIENTATION_NOT_ROTATED
        self.rota = self.ROTATION_0_ANGLE
        self.wrap = self.NOT_WRAP_AT_RIGHT
        self.shri = self.NOT_SHRINK_TO_FIT
        self.inde = 0
        self.merg = 0

    def _search_key(self):
        return (
            self.horz, self.vert, self.dire, self.orie, self.rota,
            self.wrap, self.shri, self.inde, self.merg,
            )

class Borders(object):
    NO_LINE = 0x00
    THIN    = 0x01
    MEDIUM  = 0x02
    DASHED  = 0x03
    DOTTED  = 0x04
    THICK   = 0x05
    DOUBLE  = 0x06
    HAIR    = 0x07
    #The following for BIFF8
    MEDIUM_DASHED               = 0x08
    THIN_DASH_DOTTED            = 0x09
    MEDIUM_DASH_DOTTED          = 0x0A
    THIN_DASH_DOT_DOTTED        = 0x0B
    MEDIUM_DASH_DOT_DOTTED      = 0x0C
    SLANTED_MEDIUM_DASH_DOTTED  = 0x0D

    NEED_DIAG1      = 0x01
    NEED_DIAG2      = 0x01
    NO_NEED_DIAG1   = 0x00
    NO_NEED_DIAG2   = 0x00

    def __init__(self):
        self.left   = self.NO_LINE
        self.right  = self.NO_LINE
        self.top    = self.NO_LINE
        self.bottom = self.NO_LINE
        self.diag   = self.NO_LINE

        self.left_colour   = 0x40
        self.right_colour  = 0x40
        self.top_colour    = 0x40
        self.bottom_colour = 0x40
        self.diag_colour   = 0x40

        self.need_diag1 = self.NO_NEED_DIAG1
        self.need_diag2 = self.NO_NEED_DIAG2

    def _search_key(self):
        return (
             self.left, self.right, self.top, self.bottom, self.diag,
             self.left_colour, self.right_colour, self.top_colour,
             self.bottom_colour, self.diag_colour,
             self.need_diag1, self.need_diag2,
            )

class Pattern(object):
    # patterns 0x00 - 0x12
    NO_PATTERN      = 0x00
    SOLID_PATTERN   = 0x01

    def __init__(self):
        self.pattern = self.NO_PATTERN
        self.pattern_fore_colour = 0x40
        self.pattern_back_colour = 0x41

    def _search_key(self):
        return (
            self.pattern,
            self.pattern_fore_colour,
            self.pattern_back_colour,
            )

class Protection(object):
    def __init__(self):
        self.cell_locked = 1
        self.formula_hidden = 0

    def _search_key(self):
        return (
            self.cell_locked,
            self.formula_hidden,
            )

########NEW FILE########
__FILENAME__ = Row
# -*- coding: windows-1252 -*-

import BIFFRecords
import Style
from Cell import StrCell, BlankCell, NumberCell, FormulaCell, MulBlankCell, BooleanCell, ErrorCell, \
    _get_cells_biff_data_mul
import ExcelFormula
import datetime as dt
from Formatting import Font

try:
    from decimal import Decimal
except ImportError:
    # Python 2.3: decimal not supported; create dummy Decimal class
    class Decimal(object):
        pass


class Row(object):
    __slots__ = [# private variables
                 "__idx",
                 "__parent",
                 "__parent_wb",
                 "__cells",
                 "__min_col_idx",
                 "__max_col_idx",
                 "__xf_index",
                 "__has_default_xf_index",
                 "__height_in_pixels",
                 # public variables
                 "height",
                 "has_default_height",
                 "height_mismatch",
                 "level",
                 "collapse",
                 "hidden",
                 "space_above",
                 "space_below"]

    def __init__(self, rowx, parent_sheet):
        if not (isinstance(rowx, (int, long)) and 0 <= rowx <= 65535):
            raise ValueError("row index was %r, not allowed by .xls format" % rowx)
        self.__idx = rowx
        self.__parent = parent_sheet
        self.__parent_wb = parent_sheet.get_parent()
        self.__cells = {}
        self.__min_col_idx = 0
        self.__max_col_idx = 0
        self.__xf_index = 0x0F
        self.__has_default_xf_index = 0
        self.__height_in_pixels = 0x11

        self.height = 0x00FF
        self.has_default_height = 0x00
        self.height_mismatch = 0
        self.level = 0
        self.collapse = 0
        self.hidden = 0
        self.space_above = 0
        self.space_below = 0


    def __adjust_height(self, style):
        twips = style.font.height
        points = float(twips)/20.0
        # Cell height in pixels can be calcuted by following approx. formula:
        # cell height in pixels = font height in points * 83/50 + 2/5
        # It works when screen resolution is 96 dpi
        pix = int(round(points*83.0/50.0 + 2.0/5.0))
        if pix > self.__height_in_pixels:
            self.__height_in_pixels = pix


    def __adjust_bound_col_idx(self, *args):
        for arg in args:
            iarg = int(arg)
            if not ((0 <= iarg <= 255) and arg == iarg):
                raise ValueError("column index (%r) not an int in range(256)" % arg)
            sheet = self.__parent
            if iarg < self.__min_col_idx:
                self.__min_col_idx = iarg
            if iarg > self.__max_col_idx:
                self.__max_col_idx = iarg
            if iarg < sheet.first_used_col:
                sheet.first_used_col = iarg
            if iarg > sheet.last_used_col:
                sheet.last_used_col = iarg

    def __excel_date_dt(self, date): 
        adj = False
        if isinstance(date, dt.date):
            if self.__parent_wb.dates_1904:
                epoch_tuple = (1904, 1, 1)
            else:
                epoch_tuple = (1899, 12, 31)
                adj = True
            if isinstance(date, dt.datetime):
                epoch = dt.datetime(*epoch_tuple)
            else:
                epoch = dt.date(*epoch_tuple)
        else: # it's a datetime.time instance
            date = dt.datetime.combine(dt.datetime(1900, 1, 1), date)
            epoch = dt.datetime(1900, 1, 1)
        delta = date - epoch
        xldate = delta.days + delta.seconds / 86400.0                      
        # Add a day for Excel's missing leap day in 1900
        if adj and xldate > 59:
            xldate += 1
        return xldate    

    def get_height_in_pixels(self):
        return self.__height_in_pixels


    def set_style(self, style):
        self.__adjust_height(style)
        self.__xf_index = self.__parent_wb.add_style(style)
        self.__has_default_xf_index = 1


    def get_xf_index(self):
        return self.__xf_index


    def get_cells_count(self):
        return len(self.__cells)


    def get_min_col(self):
        return self.__min_col_idx


    def get_max_col(self):
        return self.__max_col_idx


    def get_row_biff_data(self):
        height_options = (self.height & 0x07FFF)
        height_options |= (self.has_default_height & 0x01) << 15

        options =  (self.level & 0x07) << 0
        options |= (self.collapse & 0x01) << 4
        options |= (self.hidden & 0x01) << 5
        options |= (self.height_mismatch & 0x01) << 6
        options |= (self.__has_default_xf_index & 0x01) << 7
        options |= (0x01 & 0x01) << 8
        options |= (self.__xf_index & 0x0FFF) << 16
        options |= (self.space_above & 1) << 28
        options |= (self.space_below & 1) << 29

        return BIFFRecords.RowRecord(self.__idx, self.__min_col_idx,
            self.__max_col_idx, height_options, options).get()

    def insert_cell(self, col_index, cell_obj):
        if col_index in self.__cells:
            if not self.__parent._cell_overwrite_ok:
                msg = "Attempt to overwrite cell: sheetname=%r rowx=%d colx=%d" \
                    % (self.__parent.name, self.__idx, col_index)
                raise Exception(msg)
            prev_cell_obj = self.__cells[col_index]
            sst_idx = getattr(prev_cell_obj, 'sst_idx', None)
            if sst_idx is not None:
                self.__parent_wb.del_str(sst_idx)
        self.__cells[col_index] = cell_obj

    def insert_mulcells(self, colx1, colx2, cell_obj):
        self.insert_cell(colx1, cell_obj)
        for col_index in xrange(colx1+1, colx2+1):
            self.insert_cell(col_index, None)

    def get_cells_biff_data(self):
        cell_items = [item for item in self.__cells.iteritems() if item[1] is not None]
        cell_items.sort() # in column order
        return _get_cells_biff_data_mul(self.__idx, cell_items)
        # previously:
        # return ''.join([cell.get_biff_data() for colx, cell in cell_items])

    def get_index(self):
        return self.__idx

    def set_cell_text(self, colx, value, style=Style.default_style):
        self.__adjust_height(style)
        self.__adjust_bound_col_idx(colx)
        xf_index = self.__parent_wb.add_style(style)
        self.insert_cell(colx, StrCell(self.__idx, colx, xf_index, self.__parent_wb.add_str(value)))

    def set_cell_blank(self, colx, style=Style.default_style):
        self.__adjust_height(style)
        self.__adjust_bound_col_idx(colx)
        xf_index = self.__parent_wb.add_style(style)
        self.insert_cell(colx, BlankCell(self.__idx, colx, xf_index))

    def set_cell_mulblanks(self, first_colx, last_colx, style=Style.default_style):
        assert 0 <= first_colx <= last_colx <= 255
        self.__adjust_height(style)
        self.__adjust_bound_col_idx(first_colx, last_colx)
        xf_index = self.__parent_wb.add_style(style)
        # ncols = last_colx - first_colx + 1
        self.insert_mulcells(first_colx, last_colx, MulBlankCell(self.__idx, first_colx, last_colx, xf_index))

    def set_cell_number(self, colx, number, style=Style.default_style):
        self.__adjust_height(style)
        self.__adjust_bound_col_idx(colx)
        xf_index = self.__parent_wb.add_style(style)
        self.insert_cell(colx, NumberCell(self.__idx, colx, xf_index, number))

    def set_cell_date(self, colx, datetime_obj, style=Style.default_style):
        self.__adjust_height(style)
        self.__adjust_bound_col_idx(colx)
        xf_index = self.__parent_wb.add_style(style)
        self.insert_cell(colx,
            NumberCell(self.__idx, colx, xf_index, self.__excel_date_dt(datetime_obj)))

    def set_cell_formula(self, colx, formula, style=Style.default_style, calc_flags=0):
        self.__adjust_height(style)
        self.__adjust_bound_col_idx(colx)
        xf_index = self.__parent_wb.add_style(style)
        self.__parent_wb.add_sheet_reference(formula)
        self.insert_cell(colx, FormulaCell(self.__idx, colx, xf_index, formula, calc_flags=0))

    def set_cell_boolean(self, colx, value, style=Style.default_style):
        self.__adjust_height(style)
        self.__adjust_bound_col_idx(colx)
        xf_index = self.__parent_wb.add_style(style)
        self.insert_cell(colx, BooleanCell(self.__idx, colx, xf_index, bool(value)))

    def set_cell_error(self, colx, error_string_or_code, style=Style.default_style):
        self.__adjust_height(style)
        self.__adjust_bound_col_idx(colx)
        xf_index = self.__parent_wb.add_style(style)
        self.insert_cell(colx, ErrorCell(self.__idx, colx, xf_index, error_string_or_code))

    def write(self, col, label, style=Style.default_style):
        self.__adjust_height(style)
        self.__adjust_bound_col_idx(col)
        style_index = self.__parent_wb.add_style(style)
        if isinstance(label, basestring):
            if len(label) > 0:
                self.insert_cell(col,
                    StrCell(self.__idx, col, style_index, self.__parent_wb.add_str(label))
                    )
            else:
                self.insert_cell(col, BlankCell(self.__idx, col, style_index))
        elif isinstance(label, bool): # bool is subclass of int; test bool first
            self.insert_cell(col, BooleanCell(self.__idx, col, style_index, label))
        elif isinstance(label, (float, int, long, Decimal)):
            self.insert_cell(col, NumberCell(self.__idx, col, style_index, label))
        elif isinstance(label, (dt.datetime, dt.date, dt.time)):
            date_number = self.__excel_date_dt(label)
            self.insert_cell(col, NumberCell(self.__idx, col, style_index, date_number))
        elif label is None:
            self.insert_cell(col, BlankCell(self.__idx, col, style_index))
        elif isinstance(label, ExcelFormula.Formula):
            self.__parent_wb.add_sheet_reference(label)
            self.insert_cell(col, FormulaCell(self.__idx, col, style_index, label))
        elif isinstance(label, (list, tuple)):
            self.__rich_text_helper(col, label, style, style_index)
        else:
            raise Exception("Unexpected data type %r" % type(label))

    def set_cell_rich_text(self, col, rich_text_list, style=Style.default_style):
        self.__adjust_height(style)
        self.__adjust_bound_col_idx(col)
        if not isinstance(rich_text_list, (list, tuple)):
            raise Exception("Unexpected data type %r" % type(rich_text_list))
        self.__rich_text_helper(col, rich_text_list, style)

    def __rich_text_helper(self, col, rich_text_list, style, style_index=None):
        if style_index is None:
            style_index = self.__parent_wb.add_style(style)
        default_font = None    
        rt = []
        for data in rich_text_list:
            if isinstance(data, basestring):
                s = data
                font = default_font
            elif isinstance(data, (list, tuple)):
                if not isinstance(data[0], basestring) or not isinstance(data[1], Font):
                    raise Exception ("Unexpected data type %r, %r" % (type(data[0]), type(data[1])))
                s = data[0]
                font = self.__parent_wb.add_font(data[1])
            else:
                raise Exception ("Unexpected data type %r" % type(data))
            if s:
                rt.append((s, font))
                if default_font is None:
                    default_font = self.__parent_wb.add_font(style.font)
        if rt:
            self.insert_cell(col, StrCell(self.__idx, col, style_index, self.__parent_wb.add_rt(rt)))
        else:
            self.insert_cell(col, BlankCell(self.__idx, col, style_index))

    write_blanks = set_cell_mulblanks
    write_rich_text = set_cell_rich_text





########NEW FILE########
__FILENAME__ = Style
# -*- coding: windows-1252 -*-

import Formatting
from BIFFRecords import NumberFormatRecord, XFRecord, StyleRecord

FIRST_USER_DEFINED_NUM_FORMAT_IDX = 164

class XFStyle(object):

    def __init__(self):
        self.num_format_str  = 'General'
        self.font            = Formatting.Font()
        self.alignment       = Formatting.Alignment()
        self.borders         = Formatting.Borders()
        self.pattern         = Formatting.Pattern()
        self.protection      = Formatting.Protection()

default_style = XFStyle()

class StyleCollection(object):
    _std_num_fmt_list = [
            'general',
            '0',
            '0.00',
            '#,##0',
            '#,##0.00',
            '"$"#,##0_);("$"#,##0)',
            '"$"#,##0_);[Red]("$"#,##0)',
            '"$"#,##0.00_);("$"#,##0.00)',
            '"$"#,##0.00_);[Red]("$"#,##0.00)',
            '0%',
            '0.00%',
            '0.00E+00',
            '# ?/?',
            '# ??/??',
            'M/D/YY',
            'D-MMM-YY',
            'D-MMM',
            'MMM-YY',
            'h:mm AM/PM',
            'h:mm:ss AM/PM',
            'h:mm',
            'h:mm:ss',
            'M/D/YY h:mm',
            '_(#,##0_);(#,##0)',
            '_(#,##0_);[Red](#,##0)',
            '_(#,##0.00_);(#,##0.00)',
            '_(#,##0.00_);[Red](#,##0.00)',
            '_("$"* #,##0_);_("$"* (#,##0);_("$"* "-"_);_(@_)',
            '_(* #,##0_);_(* (#,##0);_(* "-"_);_(@_)',
            '_("$"* #,##0.00_);_("$"* (#,##0.00);_("$"* "-"??_);_(@_)',
            '_(* #,##0.00_);_(* (#,##0.00);_(* "-"??_);_(@_)',
            'mm:ss',
            '[h]:mm:ss',
            'mm:ss.0',
            '##0.0E+0',
            '@'
    ]

    def __init__(self, style_compression=0):
        self.style_compression = style_compression
        self.stats = [0, 0, 0, 0, 0, 0]
        self._font_id2x = {}
        self._font_x2id = {}
        self._font_val2x = {}

        for x in (0, 1, 2, 3, 5): # The font with index 4 is omitted in all BIFF versions
            font = Formatting.Font()
            search_key = font._search_key()
            self._font_id2x[font] = x
            self._font_x2id[x] = font
            self._font_val2x[search_key] = x

        self._xf_id2x = {}
        self._xf_x2id = {}
        self._xf_val2x = {}

        self._num_formats = {}
        for fmtidx, fmtstr in zip(range(0, 23), StyleCollection._std_num_fmt_list[0:23]):
            self._num_formats[fmtstr] = fmtidx
        for fmtidx, fmtstr in zip(range(37, 50), StyleCollection._std_num_fmt_list[23:]):
            self._num_formats[fmtstr] = fmtidx

        self.default_style = XFStyle()
        self._default_xf = self._add_style(self.default_style)[0]

    def add(self, style):
        if style == None:
            return 0x10
        return self._add_style(style)[1]

    def _add_style(self, style):
        num_format_str = style.num_format_str
        if num_format_str in self._num_formats:
            num_format_idx = self._num_formats[num_format_str]
        else:
            num_format_idx = (
                FIRST_USER_DEFINED_NUM_FORMAT_IDX
                + len(self._num_formats)
                - len(StyleCollection._std_num_fmt_list)
                )
            self._num_formats[num_format_str] = num_format_idx

        font = style.font
        if font in self._font_id2x:
            font_idx = self._font_id2x[font]
            self.stats[0] += 1
        elif self.style_compression:
            search_key = font._search_key()
            font_idx = self._font_val2x.get(search_key)
            if font_idx is not None:
                self._font_id2x[font] = font_idx
                self.stats[1] += 1
            else:
                font_idx = len(self._font_x2id) + 1 # Why plus 1? Font 4 is missing
                self._font_id2x[font] = font_idx
                self._font_val2x[search_key] = font_idx
                self._font_x2id[font_idx] = font
                self.stats[2] += 1
        else:
            font_idx = len(self._font_id2x) + 1
            self._font_id2x[font] = font_idx
            self.stats[2] += 1

        gof = (style.alignment, style.borders, style.pattern, style.protection)
        xf = (font_idx, num_format_idx) + gof
        if xf in self._xf_id2x:
            xf_index = self._xf_id2x[xf]
            self.stats[3] += 1
        elif self.style_compression == 2:
            xf_key = (font_idx, num_format_idx) + tuple([obj._search_key() for obj in gof])
            xf_index = self._xf_val2x.get(xf_key)
            if xf_index is not None:
                self._xf_id2x[xf] = xf_index
                self.stats[4] += 1
            else:
                xf_index = 0x10 + len(self._xf_x2id)
                self._xf_id2x[xf] = xf_index
                self._xf_val2x[xf_key] = xf_index
                self._xf_x2id[xf_index] = xf
                self.stats[5] += 1
        else:
            xf_index = 0x10 + len(self._xf_id2x)
            self._xf_id2x[xf] = xf_index
            self.stats[5] += 1

        if xf_index >= 0xFFF:
            # 12 bits allowed, 0xFFF is a sentinel value
            raise ValueError("More than 4094 XFs (styles)")

        return xf, xf_index
        
    def add_font(self, font):
        return self._add_font(font)
        
    def _add_font(self, font):
        if font in self._font_id2x:
            font_idx = self._font_id2x[font]
            self.stats[0] += 1
        elif self.style_compression:
            search_key = font._search_key()
            font_idx = self._font_val2x.get(search_key)
            if font_idx is not None:
                self._font_id2x[font] = font_idx
                self.stats[1] += 1
            else:
                font_idx = len(self._font_x2id) + 1 # Why plus 1? Font 4 is missing
                self._font_id2x[font] = font_idx
                self._font_val2x[search_key] = font_idx
                self._font_x2id[font_idx] = font
                self.stats[2] += 1
        else:
            font_idx = len(self._font_id2x) + 1
            self._font_id2x[font] = font_idx
            self.stats[2] += 1
            
        return font_idx


    def get_biff_data(self):
        result = ''
        result += self._all_fonts()
        result += self._all_num_formats()
        result += self._all_cell_styles()
        result += self._all_styles()
        return result

    def _all_fonts(self):
        result = ''
        if self.style_compression:
            alist = self._font_x2id.items()
        else:
            alist = [(x, o) for o, x in self._font_id2x.items()]
        alist.sort()
        for font_idx, font in alist:
            result += font.get_biff_record().get()
        return result

    def _all_num_formats(self):
        result = ''
        alist = [
            (v, k)
            for k, v in self._num_formats.items()
            if v >= FIRST_USER_DEFINED_NUM_FORMAT_IDX
            ]
        alist.sort()
        for fmtidx, fmtstr in alist:
            result += NumberFormatRecord(fmtidx, fmtstr).get()
        return result

    def _all_cell_styles(self):
        result = ''
        for i in range(0, 16):
            result += XFRecord(self._default_xf, 'style').get()
        if self.style_compression == 2:
            alist = self._xf_x2id.items()
        else:
            alist = [(x, o) for o, x in self._xf_id2x.items()]
        alist.sort()
        for xf_idx, xf in alist:
            result += XFRecord(xf).get()
        return result

    def _all_styles(self):
        return StyleRecord().get()

# easyxf and its supporting objects ###################################

class EasyXFException(Exception):
    pass

class EasyXFCallerError(EasyXFException):
    pass

class EasyXFAuthorError(EasyXFException):
    pass

class IntULim(object):
    # If astring represents a valid unsigned integer ('123', '0xabcd', etc)
    # and it is <= limit, return the int value; otherwise return None.

    def __init__(self, limit):
        self.limit = limit

    def __call__(self, astring):
        try:
            value = int(astring, 0)
        except ValueError:
            return None
        if not 0 <= value <= self.limit:
            return None
        return value

bool_map = {
    # Text values for all Boolean attributes
    '1': 1, 'yes': 1, 'true':  1, 'on':  1,
    '0': 0, 'no':  0, 'false': 0, 'off': 0,
    }

border_line_map = {
    # Text values for these borders attributes:
    # left, right, top, bottom and diag
    'no_line':  0x00,
    'thin':     0x01,
    'medium':   0x02,
    'dashed':   0x03,
    'dotted':   0x04,
    'thick':    0x05,
    'double':   0x06,
    'hair':     0x07,
    'medium_dashed':                0x08,
    'thin_dash_dotted':             0x09,
    'medium_dash_dotted':           0x0a,
    'thin_dash_dot_dotted':         0x0b,
    'medium_dash_dot_dotted':       0x0c,
    'slanted_medium_dash_dotted':   0x0d,
    }

charset_map = {
    # Text values for font.charset
    'ansi_latin':           0x00,
    'sys_default':          0x01,
    'symbol':               0x02,
    'apple_roman':          0x4d,
    'ansi_jap_shift_jis':   0x80,
    'ansi_kor_hangul':      0x81,
    'ansi_kor_johab':       0x82,
    'ansi_chinese_gbk':     0x86,
    'ansi_chinese_big5':    0x88,
    'ansi_greek':           0xa1,
    'ansi_turkish':         0xa2,
    'ansi_vietnamese':      0xa3,
    'ansi_hebrew':          0xb1,
    'ansi_arabic':          0xb2,
    'ansi_baltic':          0xba,
    'ansi_cyrillic':        0xcc,
    'ansi_thai':            0xde,
    'ansi_latin_ii':        0xee,
    'oem_latin_i':          0xff,
    }


# Text values for colour indices. "grey" is a synonym of "gray".
# The names are those given by Microsoft Excel 2003 to the colours
# in the default palette. There is no great correspondence with
# any W3C name-to-RGB mapping.
_colour_map_text = """\
aqua 0x31
black 0x08
blue 0x0C
blue_gray 0x36
bright_green 0x0B
brown 0x3C
coral 0x1D
cyan_ega 0x0F
dark_blue 0x12
dark_blue_ega 0x12
dark_green 0x3A
dark_green_ega 0x11
dark_purple 0x1C
dark_red 0x10
dark_red_ega 0x10
dark_teal 0x38
dark_yellow 0x13
gold 0x33
gray_ega 0x17
gray25 0x16
gray40 0x37
gray50 0x17
gray80 0x3F
green 0x11
ice_blue 0x1F
indigo 0x3E
ivory 0x1A
lavender 0x2E
light_blue 0x30
light_green 0x2A
light_orange 0x34
light_turquoise 0x29
light_yellow 0x2B
lime 0x32
magenta_ega 0x0E
ocean_blue 0x1E
olive_ega 0x13
olive_green 0x3B
orange 0x35
pale_blue 0x2C
periwinkle 0x18
pink 0x0E
plum 0x3D
purple_ega 0x14
red 0x0A
rose 0x2D
sea_green 0x39
silver_ega 0x16
sky_blue 0x28
tan 0x2F
teal 0x15
teal_ega 0x15
turquoise 0x0F
violet 0x14
white 0x09
yellow 0x0D"""

colour_map = {}
for _line in _colour_map_text.splitlines():
    _name, _num = _line.split()
    _num = int(_num, 0)
    colour_map[_name] = _num
    if 'gray' in _name:
        colour_map[_name.replace('gray', 'grey')] = _num
del _colour_map_text, _line, _name, _num

def add_palette_colour(colour_str, colour_index):
    if not (8 <= colour_index <= 63):
        raise Exception("add_palette_colour: colour_index (%d) not in range(8, 64)" % 
                (colour_index))
    colour_map[colour_str] = colour_index

# user-defined palette defines 56 RGB colors from entry 8 - 64
#excel_default_palette_b8 = [ # (red, green, blue)
#    (  0,  0,  0), (255,255,255), (255,  0,  0), (  0,255,  0),
#    (  0,  0,255), (255,255,  0), (255,  0,255), (  0,255,255),
#    (128,  0,  0), (  0,128,  0), (  0,  0,128), (128,128,  0),
#    (128,  0,128), (  0,128,128), (192,192,192), (128,128,128),
#    (153,153,255), (153, 51,102), (255,255,204), (204,255,255),
#    (102,  0,102), (255,128,128), (  0,102,204), (204,204,255),
#    (  0,  0,128), (255,  0,255), (255,255,  0), (  0,255,255),
#    (128,  0,128), (128,  0,  0), (  0,128,128), (  0,  0,255),
#    (  0,204,255), (204,255,255), (204,255,204), (255,255,153),
#    (153,204,255), (255,153,204), (204,153,255), (255,204,153),
#    ( 51,102,255), ( 51,204,204), (153,204,  0), (255,204,  0),
#    (255,153,  0), (255,102,  0), (102,102,153), (150,150,150),
#    (  0, 51,102), ( 51,153,102), (  0, 51,  0), ( 51, 51,  0),
#    (153, 51,  0), (153, 51,102), ( 51, 51,153), ( 51, 51, 51),
#    ]

# Default colour table for BIFF8 copied from 
# OpenOffice.org's Documentation of the Microsoft Excel File Format, Excel Version 2003
# Note palette has LSB padded with 2 bytes 0x00
excel_default_palette_b8 = ( 
0x00000000, 
0xFFFFFF00, 
0xFF000000, 
0x00FF0000, 
0x0000FF00, 
0xFFFF0000, 
0xFF00FF00, 
0x00FFFF00,
0x80000000, 
0x00800000, 
0x00008000, 
0x80800000, 
0x80008000, 
0x00808000, 
0xC0C0C000, 
0x80808000, 
0x9999FF00, 
0x99336600, 
0xFFFFCC00, 
0xCCFFFF00, 
0x66006600, 
0xFF808000, 
0x0066CC00, 
0xCCCCFF00, 
0x00008000, 
0xFF00FF00, 
0xFFFF0000, 
0x00FFFF00, 
0x80008000, 
0x80000000, 
0x00808000, 
0x0000FF00, 
0x00CCFF00, 
0xCCFFFF00, 
0xCCFFCC00, 
0xFFFF9900, 
0x99CCFF00, 
0xFF99CC00, 
0xCC99FF00, 
0xFFCC9900, 
0x3366FF00, 
0x33CCCC00, 
0x99CC0000, 
0xFFCC0000, 
0xFF990000, 
0xFF660000, 
0x66669900, 
0x96969600, 
0x00336600, 
0x33996600, 
0x00330000, 
0x33330000, 
0x99330000, 
0x99336600, 
0x33339900, 
0x33333300)

assert len(excel_default_palette_b8) == 56

pattern_map = {
    # Text values for pattern.pattern
    # xlwt/doc/pattern_examples.xls showcases all of these patterns.
    'no_fill':              0,
    'none':                 0,
    'solid':                1,
    'solid_fill':           1,
    'solid_pattern':        1,
    'fine_dots':            2,
    'alt_bars':             3,
    'sparse_dots':          4,
    'thick_horz_bands':     5,
    'thick_vert_bands':     6,
    'thick_backward_diag':  7,
    'thick_forward_diag':   8,
    'big_spots':            9,
    'bricks':               10,
    'thin_horz_bands':      11,
    'thin_vert_bands':      12,
    'thin_backward_diag':   13,
    'thin_forward_diag':    14,
    'squares':              15,
    'diamonds':             16,
    }

def any_str_func(s):
    return s.strip()

def colour_index_func(s, maxval=0x7F):
    try:
        value = int(s, 0)
    except ValueError:
        return None
    if not (0 <= value <= maxval):
        return None
    return value

colour_index_func_7 = colour_index_func

def colour_index_func_15(s):
    return colour_index_func(s, maxval=0x7FFF)

def rotation_func(s):
    try:
        value = int(s, 0)
    except ValueError:
        return None
    if not (-90 <= value <= 90):
        raise EasyXFCallerError("rotation %d: should be -90 to +90 degrees" % value)
    if value < 0:
        value = 90 - value # encode as 91 to 180 (clockwise)
    return value

xf_dict = {
    'align': 'alignment', # synonym
    'alignment': {
        'dire': {
            'general': 0,
            'lr': 1,
            'rl': 2,
            },
        'direction': 'dire',
        'horiz': 'horz',
        'horizontal': 'horz',
        'horz': {
            'general': 0,
            'left': 1,
            'center': 2,
            'centre': 2, # "align: horiz centre" means xf.alignment.horz is set to 2
            'right': 3,
            'filled': 4,
            'justified': 5,
            'center_across_selection': 6,
            'centre_across_selection': 6,
            'distributed': 7,
            },
        'inde': IntULim(15), # restriction: 0 <= value <= 15
        'indent': 'inde',
        'rota': [{'stacked': 255, 'none': 0, }, rotation_func],
        'rotation': 'rota',
        'shri': bool_map,
        'shrink': 'shri',
        'shrink_to_fit': 'shri',
        'vert': {
            'top': 0,
            'center': 1,
            'centre': 1,
            'bottom': 2,
            'justified': 3,
            'distributed': 4,
            },
         'vertical': 'vert',
         'wrap': bool_map,
         },
    'border': 'borders',
    'borders': {
        'left':     [border_line_map, IntULim(0x0d)],
        'right':    [border_line_map, IntULim(0x0d)],
        'top':      [border_line_map, IntULim(0x0d)],
        'bottom':   [border_line_map, IntULim(0x0d)],
        'diag':     [border_line_map, IntULim(0x0d)],
        'top_colour':       [colour_map, colour_index_func_7],
        'bottom_colour':    [colour_map, colour_index_func_7],
        'left_colour':      [colour_map, colour_index_func_7],
        'right_colour':     [colour_map, colour_index_func_7],
        'diag_colour':      [colour_map, colour_index_func_7],
        'top_color':        'top_colour',
        'bottom_color':     'bottom_colour',
        'left_color':       'left_colour',
        'right_color':      'right_colour',
        'diag_color':       'diag_colour',
        'need_diag1':  bool_map,
        'need_diag2':  bool_map,
        },
    'font': {
        'bold': bool_map,
        'charset': charset_map,
        'color':  'colour_index',
        'color_index':  'colour_index',
        'colour':  'colour_index',
        'colour_index': [colour_map, colour_index_func_15],
        'escapement': {'none': 0, 'superscript': 1, 'subscript': 2},
        'family': {'none': 0, 'roman': 1, 'swiss': 2, 'modern': 3, 'script': 4, 'decorative': 5, },
        'height': IntULim(0xFFFF), # practical limits are much narrower e.g. 160 to 1440 (8pt to 72pt)
        'italic': bool_map,
        'name': any_str_func,
        'outline': bool_map,
        'shadow': bool_map,
        'struck_out': bool_map,
        'underline': [bool_map, {'none': 0, 'single': 1, 'single_acc': 0x21, 'double': 2, 'double_acc': 0x22, }],
        },
    'pattern': {
        'back_color':   'pattern_back_colour',
        'back_colour':  'pattern_back_colour',
        'fore_color':   'pattern_fore_colour',
        'fore_colour':  'pattern_fore_colour',
        'pattern': [pattern_map, IntULim(16)],
        'pattern_back_color':   'pattern_back_colour',
        'pattern_back_colour':  [colour_map, colour_index_func_7],
        'pattern_fore_color':   'pattern_fore_colour',
        'pattern_fore_colour':  [colour_map, colour_index_func_7],
        },
    'protection': {
        'cell_locked' :   bool_map,
        'formula_hidden': bool_map,
        },
    }

def _esplit(s, split_char, esc_char="\\"):
    escaped = False
    olist = ['']
    for c in s:
        if escaped:
            olist[-1] += c
            escaped = False
        elif c == esc_char:
            escaped = True
        elif c == split_char:
            olist.append('')
        else:
            olist[-1] += c
    return olist

def _parse_strg_to_obj(strg, obj, parse_dict,
    field_sep=",", line_sep=";", intro_sep=":", esc_char="\\", debug=False):
    for line in _esplit(strg, line_sep, esc_char):
        line = line.strip()
        if not line:
            break
        split_line = _esplit(line, intro_sep, esc_char)
        if len(split_line) != 2:
            raise EasyXFCallerError('line %r should have exactly 1 "%c"' % (line, intro_sep))
        section, item_str = split_line
        section = section.strip().lower()
        for counter in range(2):
            result = parse_dict.get(section)
            if result is None:
                raise EasyXFCallerError('section %r is unknown' % section)
            if isinstance(result, dict):
                break
            if not isinstance(result, str):
                raise EasyXFAuthorError(
                    'section %r should map to dict or str object; found %r' % (section, type(result)))
            # synonym
            old_section = section
            section = result
        else:
            raise EasyXFAuthorError('Attempt to define synonym of synonym (%r: %r)' % (old_section, result))
        section_dict = result
        section_obj = getattr(obj, section, None)
        if section_obj is None:
            raise EasyXFAuthorError('instance of %s class has no attribute named %s' % (obj.__class__.__name__, section))
        for kv_str in _esplit(item_str, field_sep, esc_char):
            guff = kv_str.split()
            if not guff:
                continue
            k = guff[0].lower().replace('-', '_')
            v = ' '.join(guff[1:])
            if not v:
                raise EasyXFCallerError("no value supplied for %s.%s" % (section, k))
            for counter in xrange(2):
                result = section_dict.get(k)
                if result is None:
                    raise EasyXFCallerError('%s.%s is not a known attribute' % (section, k))
                if not isinstance(result, basestring):
                    break
                # synonym
                old_k = k
                k = result
            else:
                raise EasyXFAuthorError('Attempt to define synonym of synonym (%r: %r)' % (old_k, result))
            value_info = result
            if not isinstance(value_info, list):
                value_info = [value_info]
            for value_rule in value_info:
                if isinstance(value_rule, dict):
                    # dict maps strings to integer field values
                    vl = v.lower().replace('-', '_')
                    if vl in value_rule:
                        value = value_rule[vl]
                        break
                elif callable(value_rule):
                    value = value_rule(v)
                    if value is not None:
                        break
                else:
                    raise EasyXFAuthorError("unknown value rule for attribute %r: %r" % (k, value_rule))
            else:
                raise EasyXFCallerError("unexpected value %r for %s.%s" % (v, section, k))
            try:
                orig = getattr(section_obj, k)
            except AttributeError:
                raise EasyXFAuthorError('%s.%s in dictionary but not in supplied object' % (section, k))
            if debug: print "+++ %s.%s = %r # %s; was %r" % (section, k, value, v, orig)
            setattr(section_obj, k, value)

def easyxf(strg_to_parse="", num_format_str=None,
    field_sep=",", line_sep=";", intro_sep=":", esc_char="\\", debug=False):
    xfobj = XFStyle()
    if num_format_str is not None:
        xfobj.num_format_str = num_format_str
    if strg_to_parse:
        _parse_strg_to_obj(strg_to_parse, xfobj, xf_dict,
            field_sep=field_sep, line_sep=line_sep, intro_sep=intro_sep, esc_char=esc_char, debug=debug)
    return xfobj

def easyfont(strg_to_parse="", field_sep=",", esc_char="\\", debug=False):
    xfobj = XFStyle()
    if strg_to_parse:
        _parse_strg_to_obj("font: " + strg_to_parse, xfobj, xf_dict,
            field_sep=field_sep, line_sep=";", intro_sep=":", esc_char=esc_char, debug=debug)
    return xfobj.font

########NEW FILE########
__FILENAME__ = UnicodeUtils
# -*- coding: windows-1252 -*-

'''
From BIFF8 on, strings are always stored using UTF-16LE  text encoding. The
character  array  is  a  sequence  of  16-bit  values4.  Additionally it is
possible  to  use  a  compressed  format, which omits the high bytes of all
characters, if they are all zero.

The following tables describe the standard format of the entire string, but
in many records the strings differ from this format. This will be mentioned
separately. It is possible (but not required) to store Rich-Text formatting
information  and  Asian  phonetic information inside a Unicode string. This
results  in  four  different  ways  to  store a string. The character array
is not zero-terminated.

The  string  consists  of  the  character count (as usual an 8-bit value or
a  16-bit value), option flags, the character array and optional formatting
information.  If the string is empty, sometimes the option flags field will
not occur. This is mentioned at the respective place.

Offset  Size    Contents
0       1 or 2  Length of the string (character count, ln)
1 or 2  1       Option flags:
                  Bit   Mask Contents
                  0     01H  Character compression (ccompr):
                               0 = Compressed (8-bit characters)
                               1 = Uncompressed (16-bit characters)
                  2     04H  Asian phonetic settings (phonetic):
                               0 = Does not contain Asian phonetic settings
                               1 = Contains Asian phonetic settings
                  3     08H  Rich-Text settings (richtext):
                               0 = Does not contain Rich-Text settings
                               1 = Contains Rich-Text settings
[2 or 3] 2      (optional, only if richtext=1) Number of Rich-Text formatting runs (rt)
[var.]   4      (optional, only if phonetic=1) Size of Asian phonetic settings block (in bytes, sz)
var.     ln or 
         2·ln   Character array (8-bit characters or 16-bit characters, dependent on ccompr)
[var.]   4·rt   (optional, only if richtext=1) List of rt formatting runs 
[var.]   sz     (optional, only if phonetic=1) Asian Phonetic Settings Block 
'''


from struct import pack

def upack2(s, encoding='ascii'):
    # If not unicode, make it so.
    if isinstance(s, unicode):
        us = s
    else:
        us = unicode(s, encoding)
    # Limit is based on number of content characters
    # (not on number of bytes in packed result)
    len_us = len(us)
    if len_us > 32767:
        raise Exception('String longer than 32767 characters')
    try:
        encs = us.encode('latin1')
        # Success here means all chars are in U+0000 to U+00FF
        # inclusive, meaning that we can use "compressed format".
        flag = 0
        n_items = len_us
    except UnicodeEncodeError:
        encs = us.encode('utf_16_le')
        flag = 1
        n_items = len(encs) // 2
        # n_items is the number of "double byte characters" i.e. MS C wchars
        # Can't use len(us).
        # len(u"\U0001D400") -> 1 on a wide-unicode build 
        # and 2 on a narrow-unicode build.
        # We need n_items == 2 in this case.
    return pack('<HB', n_items, flag) + encs

def upack2rt(rt, encoding='ascii'):
    us = u''
    fr = ''
    offset = 0
    # convert rt strings to unicode if not already unicode
    # also generate the formatting run for the styles added
    for s, fontx in rt:
        if not isinstance(s, unicode):
            s = unicode(s, encoding)
        us += s
        if fontx is not None:
            # code in Rows.py ensures that
            # fontx can be None only for the first piece
            fr += pack('<HH', offset, fontx)        
        # offset is the number of MS C wchar characters.
        # That is 1 if c <= u'\uFFFF' else 2 
        offset += len(s.encode('utf_16_le')) // 2
    num_fr = len(fr) // 4 # ensure result is int
    if offset > 32767:
        raise Exception('String longer than 32767 characters')
    try:
        encs = us.encode('latin1')
        # Success here means all chars are in U+0000 to U+00FF
        # inclusive, meaning that we can use "compressed format".
        flag = 0 | 8
        n_items = len(encs)
    except UnicodeEncodeError:
        encs = us.encode('utf_16_le')
        flag = 1 | 8
        n_items = len(encs) // 2 # see comments in upack2 function above
    return pack('<HBH', n_items, flag, num_fr) + encs, fr

def upack1(s, encoding='ascii'):
    # Same as upack2(), but with a one-byte length field.
    if isinstance(s, unicode):
        us = s
    else:
        us = unicode(s, encoding)
    len_us = len(us)
    if len_us > 255:
        raise Exception('String longer than 255 characters')
    try:
        encs = us.encode('latin1')
        flag = 0
        n_items = len_us
    except UnicodeEncodeError:
        encs = us.encode('utf_16_le')
        flag = 1
        n_items = len(encs) // 2 
    return pack('<BB', n_items, flag) + encs

########NEW FILE########
__FILENAME__ = Utils
# see the xlwt.license module for details of licensing.

# Utilities for work with reference to cells and with sheetnames

import re
from ExcelMagic import MAX_ROW, MAX_COL

_re_cell_ex = re.compile(r"(\$?)([A-I]?[A-Z])(\$?)(\d+)", re.IGNORECASE)
_re_row_range = re.compile(r"\$?(\d+):\$?(\d+)")
_re_col_range = re.compile(r"\$?([A-I]?[A-Z]):\$?([A-I]?[A-Z])", re.IGNORECASE)
_re_cell_range = re.compile(r"\$?([A-I]?[A-Z]\$?\d+):\$?([A-I]?[A-Z]\$?\d+)", re.IGNORECASE)
_re_cell_ref = re.compile(r"\$?([A-I]?[A-Z]\$?\d+)", re.IGNORECASE)


def col_by_name(colname):
    """'A' -> 0, 'Z' -> 25, 'AA' -> 26, etc
    """
    col = 0
    power = 1
    for i in xrange(len(colname)-1, -1, -1):
        ch = colname[i]
        col += (ord(ch) - ord('A') + 1) * power
        power *= 26
    return col - 1


def cell_to_rowcol(cell):
    """Convert an Excel cell reference string in A1 notation
    to numeric row/col notation.

    Returns: row, col, row_abs, col_abs

    """
    m = _re_cell_ex.match(cell)
    if not m:
        raise Exception("Ill-formed single_cell reference: %s" % cell)
    col_abs, col, row_abs, row = m.groups()
    row_abs = bool(row_abs)
    col_abs = bool(col_abs)
    row = int(row) - 1
    col = col_by_name(col.upper())
    return row, col, row_abs, col_abs


def cell_to_rowcol2(cell):
    """Convert an Excel cell reference string in A1 notation
    to numeric row/col notation.

    Returns: row, col

    """
    m = _re_cell_ex.match(cell)
    if not m:
        raise Exception("Error in cell format")
    col_abs, col, row_abs, row = m.groups()
    # Convert base26 column string to number
    # All your Base are belong to us.
    row = int(row) - 1
    col = col_by_name(col.upper())
    return row, col


def rowcol_to_cell(row, col, row_abs=False, col_abs=False):
    """Convert numeric row/col notation to an Excel cell reference string in
    A1 notation.

    """
    assert 0 <= row < MAX_ROW # MAX_ROW counts from 1
    assert 0 <= col < MAX_COL # MAX_COL counts from 1
    d = col // 26
    m = col % 26
    chr1 = ""    # Most significant character in AA1
    if row_abs:
        row_abs = '$'
    else:
        row_abs = ''
    if col_abs:
        col_abs = '$'
    else:
        col_abs = ''
    if d > 0:
        chr1 = chr(ord('A') + d  - 1)
    chr2 = chr(ord('A') + m)
    # Zero index to 1-index
    return col_abs + chr1 + chr2 + row_abs + str(row + 1)

def rowcol_pair_to_cellrange(row1, col1, row2, col2,
    row1_abs=False, col1_abs=False, row2_abs=False, col2_abs=False):
    """Convert two (row,column) pairs
    into a cell range string in A1:B2 notation.

    Returns: cell range string
    """
    assert row1 <= row2
    assert col1 <= col2
    return (
        rowcol_to_cell(row1, col1, row1_abs, col1_abs)
        + ":"
        + rowcol_to_cell(row2, col2, row2_abs, col2_abs)
        )

def cellrange_to_rowcol_pair(cellrange):
    """Convert cell range string in A1 notation to numeric row/col
    pair.

    Returns: row1, col1, row2, col2

    """
    cellrange = cellrange.upper()
    # Convert a row range: '1:3'
    res = _re_row_range.match(cellrange)
    if res:
        row1 = int(res.group(1)) - 1
        col1 = 0
        row2 = int(res.group(2)) - 1
        col2 = -1
        return row1, col1, row2, col2
    # Convert a column range: 'A:A' or 'B:G'.
    # A range such as A:A is equivalent to A1:A16384, so add rows as required
    res = _re_col_range.match(cellrange)
    if res:
        col1 = col_by_name(res.group(1).upper())
        row1 = 0
        col2 = col_by_name(res.group(2).upper())
        row2 = -1
        return row1, col1, row2, col2
    # Convert a cell range: 'A1:B7'
    res = _re_cell_range.match(cellrange)
    if res:
        row1, col1 = cell_to_rowcol2(res.group(1))
        row2, col2 = cell_to_rowcol2(res.group(2))
        return row1, col1, row2, col2
    # Convert a cell reference: 'A1' or 'AD2000'
    res = _re_cell_ref.match(cellrange)
    if res:
        row1, col1 = cell_to_rowcol2(res.group(1))
        return row1, col1, row1, col1
    raise Exception("Unknown cell reference %s" % (cellrange))


def cell_to_packed_rowcol(cell):
    """ pack row and column into the required 4 byte format """
    row, col, row_abs, col_abs = cell_to_rowcol(cell)
    if col >= MAX_COL:
        raise Exception("Column %s greater than IV in formula" % cell)
    if row >= MAX_ROW: # this for BIFF8. for BIFF7 available 2^14
        raise Exception("Row %s greater than %d in formula" % (cell, MAX_ROW))
    col |= int(not row_abs) << 15
    col |= int(not col_abs) << 14
    return row, col

# === sheetname functions ===

def valid_sheet_name(sheet_name):
    if sheet_name == u"" or sheet_name[0] == u"'" or len(sheet_name) > 31:
        return False
    for c in sheet_name:
        if c in u"[]:\\?/*\x00":
            return False
    return True

def quote_sheet_name(unquoted_sheet_name):
    if not valid_sheet_name(unquoted_sheet_name):
        raise Exception(
            'attempt to quote an invalid worksheet name %r' % unquoted_sheet_name)
    return u"'" + unquoted_sheet_name.replace(u"'", u"''") + u"'"

########NEW FILE########
__FILENAME__ = Workbook
# -*- coding: windows-1252 -*-
'''
Record Order in BIFF8
  Workbook Globals Substream
      BOF Type = workbook globals
      Interface Header
      MMS
      Interface End
      WRITEACCESS
      CODEPAGE
      DSF
      TABID
      FNGROUPCOUNT
      Workbook Protection Block
            WINDOWPROTECT
            PROTECT
            PASSWORD
            PROT4REV
            PROT4REVPASS
      BACKUP
      HIDEOBJ
      WINDOW1
      DATEMODE
      PRECISION
      REFRESHALL
      BOOKBOOL
      FONT +
      FORMAT *
      XF +
      STYLE +
    ? PALETTE
      USESELFS

      BOUNDSHEET +

      COUNTRY
    ? Link Table
      SST
      ExtSST
      EOF
'''

import BIFFRecords
import Style

class Workbook(object):

    #################################################################
    ## Constructor
    #################################################################
    def __init__(self, encoding='ascii', style_compression=0):
        self.encoding = encoding
        self.__owner = 'None'
        self.__country_code = None # 0x07 is Russia :-)
        self.__wnd_protect = 0
        self.__obj_protect = 0
        self.__protect = 0
        self.__backup_on_save = 0
        # for WINDOW1 record
        self.__hpos_twips = 0x01E0
        self.__vpos_twips = 0x005A
        self.__width_twips = 0x3FCF
        self.__height_twips = 0x2A4E
        self.__custom_palette_b8 = None

        self.__active_sheet = 0
        self.__first_tab_index = 0
        self.__selected_tabs = 0x01
        self.__tab_width_twips = 0x0258

        self.__wnd_hidden = 0
        self.__wnd_mini = 0
        self.__hscroll_visible = 1
        self.__vscroll_visible = 1
        self.__tabs_visible = 1

        self.__styles = Style.StyleCollection(style_compression)

        self.__dates_1904 = 0
        self.__use_cell_values = 1

        self.__sst = BIFFRecords.SharedStringTable(self.encoding)

        self.__worksheets = []
        self.__worksheet_idx_from_name = {}
        self.__sheet_refs = {}
        self._supbook_xref = {}
        self._xcall_xref = {}
        self._ownbook_supbookx = None
        self._ownbook_supbook_ref = None
        self._xcall_supbookx = None
        self._xcall_supbook_ref = None



    #################################################################
    ## Properties, "getters", "setters"
    #################################################################

    def get_style_stats(self):
        return self.__styles.stats[:]

    def set_owner(self, value):
        self.__owner = value

    def get_owner(self):
        return self.__owner

    owner = property(get_owner, set_owner)

    #################################################################

    def set_country_code(self, value):
        self.__country_code = value

    def get_country_code(self):
        return self.__country_code

    country_code = property(get_country_code, set_country_code)

    #################################################################

    def set_wnd_protect(self, value):
        self.__wnd_protect = int(value)

    def get_wnd_protect(self):
        return bool(self.__wnd_protect)

    wnd_protect = property(get_wnd_protect, set_wnd_protect)

    #################################################################

    def set_obj_protect(self, value):
        self.__obj_protect = int(value)

    def get_obj_protect(self):
        return bool(self.__obj_protect)

    obj_protect = property(get_obj_protect, set_obj_protect)

    #################################################################

    def set_protect(self, value):
        self.__protect = int(value)

    def get_protect(self):
        return bool(self.__protect)

    protect = property(get_protect, set_protect)

    #################################################################

    def set_backup_on_save(self, value):
        self.__backup_on_save = int(value)

    def get_backup_on_save(self):
        return bool(self.__backup_on_save)

    backup_on_save = property(get_backup_on_save, set_backup_on_save)

    #################################################################

    def set_hpos(self, value):
        self.__hpos_twips = value & 0xFFFF

    def get_hpos(self):
        return self.__hpos_twips

    hpos = property(get_hpos, set_hpos)

    #################################################################

    def set_vpos(self, value):
        self.__vpos_twips = value & 0xFFFF

    def get_vpos(self):
        return self.__vpos_twips

    vpos = property(get_vpos, set_vpos)

    #################################################################

    def set_width(self, value):
        self.__width_twips = value & 0xFFFF

    def get_width(self):
        return self.__width_twips

    width = property(get_width, set_width)

    #################################################################

    def set_height(self, value):
        self.__height_twips = value & 0xFFFF

    def get_height(self):
        return self.__height_twips

    height = property(get_height, set_height)

    #################################################################

    def set_active_sheet(self, value):
        self.__active_sheet = value & 0xFFFF
        self.__first_tab_index = self.__active_sheet

    def get_active_sheet(self):
        return self.__active_sheet

    active_sheet = property(get_active_sheet, set_active_sheet)

    #################################################################

    def set_tab_width(self, value):
        self.__tab_width_twips = value & 0xFFFF

    def get_tab_width(self):
        return self.__tab_width_twips

    tab_width = property(get_tab_width, set_tab_width)

    #################################################################

    def set_wnd_visible(self, value):
        self.__wnd_hidden = int(not value)

    def get_wnd_visible(self):
        return not bool(self.__wnd_hidden)

    wnd_visible = property(get_wnd_visible, set_wnd_visible)

    #################################################################

    def set_wnd_mini(self, value):
        self.__wnd_mini = int(value)

    def get_wnd_mini(self):
        return bool(self.__wnd_mini)

    wnd_mini = property(get_wnd_mini, set_wnd_mini)

    #################################################################

    def set_hscroll_visible(self, value):
        self.__hscroll_visible = int(value)

    def get_hscroll_visible(self):
        return bool(self.__hscroll_visible)

    hscroll_visible = property(get_hscroll_visible, set_hscroll_visible)

    #################################################################

    def set_vscroll_visible(self, value):
        self.__vscroll_visible = int(value)

    def get_vscroll_visible(self):
        return bool(self.__vscroll_visible)

    vscroll_visible = property(get_vscroll_visible, set_vscroll_visible)

    #################################################################

    def set_tabs_visible(self, value):
        self.__tabs_visible = int(value)

    def get_tabs_visible(self):
        return bool(self.__tabs_visible)

    tabs_visible = property(get_tabs_visible, set_tabs_visible)

    #################################################################

    def set_dates_1904(self, value):
        self.__dates_1904 = int(value)

    def get_dates_1904(self):
        return bool(self.__dates_1904)

    dates_1904 = property(get_dates_1904, set_dates_1904)

    #################################################################

    def set_use_cell_values(self, value):
        self.__use_cell_values = int(value)

    def get_use_cell_values(self):
        return bool(self.__use_cell_values)

    use_cell_values = property(get_use_cell_values, set_use_cell_values)

    #################################################################

    def get_default_style(self):
        return self.__styles.default_style

    default_style = property(get_default_style)

    #################################################################

    def set_colour_RGB(self, colour_index, red, green, blue):
        if not(8 <= colour_index <= 63):
            raise Exception("set_colour_RGB: colour_index (%d) not in range(8, 64)" % 
                    colour_index)
        if min(red, green, blue) < 0 or max(red, green, blue) > 255:
            raise Exception("set_colour_RGB: colour values (%d,%d,%d) must be in range(0, 256)" 
                    % (red, green, blue))
        if self.__custom_palette_b8 is None: 
            self.__custom_palette_b8 = list(Style.excel_default_palette_b8)
        # User-defined Palette starts at colour index 8,
        # so subtract 8 from colour_index when placing in palette
        palette_index = colour_index - 8
        self.__custom_palette_b8[palette_index] = red << 24 | green << 16 | blue << 8

    ##################################################################
    ## Methods
    ##################################################################

    def add_style(self, style):
        return self.__styles.add(style)
    
    def add_font(self, font):
        return self.__styles.add_font(font)

    def add_str(self, s):
        return self.__sst.add_str(s)

    def del_str(self, sst_idx):
        self.__sst.del_str(sst_idx)

    def str_index(self, s):
        return self.__sst.str_index(s)
        
    def add_rt(self, rt):
        return self.__sst.add_rt(rt)
    
    def rt_index(self, rt):
        return self.__sst.rt_index(rt)

    def add_sheet(self, sheetname, cell_overwrite_ok=False):
        import Worksheet, Utils
        if not isinstance(sheetname, unicode):
            sheetname = sheetname.decode(self.encoding)
        if not Utils.valid_sheet_name(sheetname):
            raise Exception("invalid worksheet name %r" % sheetname)
        lower_name = sheetname.lower()
        if lower_name in self.__worksheet_idx_from_name:
            raise Exception("duplicate worksheet name %r" % sheetname)
        self.__worksheet_idx_from_name[lower_name] = len(self.__worksheets)
        self.__worksheets.append(Worksheet.Worksheet(sheetname, self, cell_overwrite_ok))
        return self.__worksheets[-1]

    def get_sheet(self, sheetnum):
        return self.__worksheets[sheetnum]

    def raise_bad_sheetname(self, sheetname):
        raise Exception("Formula: unknown sheet name %s" % sheetname)

    def convert_sheetindex(self, strg_ref, n_sheets):
        idx = int(strg_ref)
        if 0 <= idx < n_sheets:
            return idx
        msg = "Formula: sheet index (%s) >= number of sheets (%d)" % (strg_ref, n_sheets)
        raise Exception(msg)

    def _get_supbook_index(self, tag):
        if tag in self._supbook_xref:
            return self._supbook_xref[tag]
        self._supbook_xref[tag] = idx = len(self._supbook_xref)
        return idx

    def setup_ownbook(self):
        self._ownbook_supbookx = self._get_supbook_index(('ownbook', 0))
        self._ownbook_supbook_ref = None
        reference = (self._ownbook_supbookx, 0xFFFE, 0xFFFE)
        if reference in self.__sheet_refs:
            raise Exception("can't happen")
        self.__sheet_refs[reference] = self._ownbook_supbook_ref = len(self.__sheet_refs)

    def setup_xcall(self):
        self._xcall_supbookx = self._get_supbook_index(('xcall', 0))
        self._xcall_supbook_ref = None
        reference = (self._xcall_supbookx, 0xFFFE, 0xFFFE)
        if reference in self.__sheet_refs:
            raise Exception("can't happen")
        self.__sheet_refs[reference] = self._xcall_supbook_ref = len(self.__sheet_refs)

    def add_sheet_reference(self, formula):
        patches = []
        n_sheets = len(self.__worksheets)
        sheet_refs, xcall_refs = formula.get_references()

        for ref0, ref1, offset in sheet_refs:
            if not ref0.isdigit():
                try:
                    ref0n = self.__worksheet_idx_from_name[ref0.lower()]
                except KeyError:
                    self.raise_bad_sheetname(ref0)
            else:
                ref0n = self.convert_sheetindex(ref0, n_sheets)
            if ref1 == ref0:
                ref1n = ref0n
            elif not ref1.isdigit():
                try:
                    ref1n = self.__worksheet_idx_from_name[ref1.lower()]
                except KeyError:
                    self.raise_bad_sheetname(ref1)
            else:
                ref1n = self.convert_sheetindex(ref1, n_sheets)
            if ref1n < ref0n:
                msg = "Formula: sheets out of order; %r:%r -> (%d, %d)" \
                    % (ref0, ref1, ref0n, ref1n)
                raise Exception(msg)
            if self._ownbook_supbookx is None:
                self.setup_ownbook()
            reference = (self._ownbook_supbookx, ref0n, ref1n)
            if reference in self.__sheet_refs:
                patches.append((offset, self.__sheet_refs[reference]))
            else:
                nrefs = len(self.__sheet_refs)
                if nrefs > 65535:
                    raise Exception('More than 65536 inter-sheet references')
                self.__sheet_refs[reference] = nrefs
                patches.append((offset, nrefs))

        for funcname, offset in xcall_refs:
            if self._ownbook_supbookx is None:
                self.setup_ownbook()
            if self._xcall_supbookx is None:
                self.setup_xcall()
            # print funcname, self._supbook_xref
            patches.append((offset, self._xcall_supbook_ref))
            if not isinstance(funcname, unicode):
                funcname = funcname.decode(self.encoding)
            if funcname in self._xcall_xref:
                idx = self._xcall_xref[funcname]
            else:
                self._xcall_xref[funcname] = idx = len(self._xcall_xref)
            patches.append((offset + 2, idx + 1))

        formula.patch_references(patches)

    ##################################################################
    ## BIFF records generation
    ##################################################################

    def __bof_rec(self):
        return BIFFRecords.Biff8BOFRecord(BIFFRecords.Biff8BOFRecord.BOOK_GLOBAL).get()

    def __eof_rec(self):
        return BIFFRecords.EOFRecord().get()

    def __intf_hdr_rec(self):
        return BIFFRecords.InteraceHdrRecord().get()

    def __intf_end_rec(self):
        return BIFFRecords.InteraceEndRecord().get()

    def __intf_mms_rec(self):
        return BIFFRecords.MMSRecord().get()

    def __write_access_rec(self):
        return BIFFRecords.WriteAccessRecord(self.__owner).get()

    def __wnd_protect_rec(self):
        return BIFFRecords.WindowProtectRecord(self.__wnd_protect).get()

    def __obj_protect_rec(self):
        return BIFFRecords.ObjectProtectRecord(self.__obj_protect).get()

    def __protect_rec(self):
        return BIFFRecords.ProtectRecord(self.__protect).get()

    def __password_rec(self):
        return BIFFRecords.PasswordRecord().get()

    def __prot4rev_rec(self):
        return BIFFRecords.Prot4RevRecord().get()

    def __prot4rev_pass_rec(self):
        return BIFFRecords.Prot4RevPassRecord().get()

    def __backup_rec(self):
        return BIFFRecords.BackupRecord(self.__backup_on_save).get()

    def __hide_obj_rec(self):
        return BIFFRecords.HideObjRecord().get()

    def __window1_rec(self):
        flags = 0
        flags |= (self.__wnd_hidden) << 0
        flags |= (self.__wnd_mini) << 1
        flags |= (self.__hscroll_visible) << 3
        flags |= (self.__vscroll_visible) << 4
        flags |= (self.__tabs_visible) << 5

        return BIFFRecords.Window1Record(self.__hpos_twips, self.__vpos_twips,
                                self.__width_twips, self.__height_twips,
                                flags,
                                self.__active_sheet, self.__first_tab_index,
                                self.__selected_tabs, self.__tab_width_twips).get()

    def __codepage_rec(self):
        return BIFFRecords.CodepageBiff8Record().get()

    def __country_rec(self):
        if not self.__country_code:
            return ''
        return BIFFRecords.CountryRecord(self.__country_code, self.__country_code).get()

    def __dsf_rec(self):
        return BIFFRecords.DSFRecord().get()

    def __tabid_rec(self):
        return BIFFRecords.TabIDRecord(len(self.__worksheets)).get()

    def __fngroupcount_rec(self):
        return BIFFRecords.FnGroupCountRecord().get()

    def __datemode_rec(self):
        return BIFFRecords.DateModeRecord(self.__dates_1904).get()

    def __precision_rec(self):
        return BIFFRecords.PrecisionRecord(self.__use_cell_values).get()

    def __refresh_all_rec(self):
        return BIFFRecords.RefreshAllRecord().get()

    def __bookbool_rec(self):
        return BIFFRecords.BookBoolRecord().get()

    def __all_fonts_num_formats_xf_styles_rec(self):
        return self.__styles.get_biff_data()

    def __palette_rec(self):
        if self.__custom_palette_b8 is None: 
            return ''
        info = BIFFRecords.PaletteRecord(self.__custom_palette_b8).get()
        return info

    def __useselfs_rec(self):
        return BIFFRecords.UseSelfsRecord().get()

    def __boundsheets_rec(self, data_len_before, data_len_after, sheet_biff_lens):
        #  .................................
        # BOUNDSEHEET0
        # BOUNDSEHEET1
        # BOUNDSEHEET2
        # ..................................
        # WORKSHEET0
        # WORKSHEET1
        # WORKSHEET2
        boundsheets_len = 0
        for sheet in self.__worksheets:
            boundsheets_len += len(BIFFRecords.BoundSheetRecord(
                0x00L, sheet.visibility, sheet.name, self.encoding
                ).get())

        start = data_len_before + boundsheets_len + data_len_after

        result = ''
        for sheet_biff_len,  sheet in zip(sheet_biff_lens, self.__worksheets):
            result += BIFFRecords.BoundSheetRecord(
                start, sheet.visibility, sheet.name, self.encoding
                ).get()
            start += sheet_biff_len
        return result

    def __all_links_rec(self):
        pieces = []
        temp = [(idx, tag) for tag, idx in self._supbook_xref.items()]
        temp.sort()
        for idx, tag in temp:
            stype, snum = tag
            if stype == 'ownbook':
                rec = BIFFRecords.InternalReferenceSupBookRecord(len(self.__worksheets)).get()
                pieces.append(rec)
            elif stype == 'xcall':
                rec = BIFFRecords.XcallSupBookRecord().get()
                pieces.append(rec)
                temp = [(idx, name) for name, idx in self._xcall_xref.items()]
                temp.sort()
                for idx, name in temp:
                    rec = BIFFRecords.ExternnameRecord(
                        options=0, index=0, name=name, fmla='\x02\x00\x1c\x17').get()
                    pieces.append(rec)
            else:
                raise Exception('unknown supbook stype %r' % stype)
        if len(self.__sheet_refs) > 0:
            # get references in index order
            temp = [(idx, ref) for ref, idx in self.__sheet_refs.items()]
            temp.sort()
            temp = [ref for idx, ref in temp]
            externsheet_record = BIFFRecords.ExternSheetRecord(temp).get()
            pieces.append(externsheet_record)
        return ''.join(pieces)

    def __sst_rec(self):
        return self.__sst.get_biff_record()

    def __ext_sst_rec(self, abs_stream_pos):
        return ''
        #return BIFFRecords.ExtSSTRecord(abs_stream_pos, self.sst_record.str_placement,
        #self.sst_record.portions_len).get()

    def get_biff_data(self):
        before = ''
        before += self.__bof_rec()
        before += self.__intf_hdr_rec()
        before += self.__intf_mms_rec()
        before += self.__intf_end_rec()
        before += self.__write_access_rec()
        before += self.__codepage_rec()
        before += self.__dsf_rec()
        before += self.__tabid_rec()
        before += self.__fngroupcount_rec()
        before += self.__wnd_protect_rec()
        before += self.__protect_rec()
        before += self.__obj_protect_rec()
        before += self.__password_rec()
        before += self.__prot4rev_rec()
        before += self.__prot4rev_pass_rec()
        before += self.__backup_rec()
        before += self.__hide_obj_rec()
        before += self.__window1_rec()
        before += self.__datemode_rec()
        before += self.__precision_rec()
        before += self.__refresh_all_rec()
        before += self.__bookbool_rec()
        before += self.__all_fonts_num_formats_xf_styles_rec()
        before += self.__palette_rec()
        before += self.__useselfs_rec()

        country            = self.__country_rec()
        all_links          = self.__all_links_rec()

        shared_str_table   = self.__sst_rec()
        after = country + all_links + shared_str_table

        ext_sst = self.__ext_sst_rec(0) # need fake cause we need calc stream pos
        eof = self.__eof_rec()

        self.__worksheets[self.__active_sheet].selected = True
        sheets = ''
        sheet_biff_lens = []
        for sheet in self.__worksheets:
            data = sheet.get_biff_data()
            sheets += data
            sheet_biff_lens.append(len(data))

        bundlesheets = self.__boundsheets_rec(len(before), len(after)+len(ext_sst)+len(eof), sheet_biff_lens)

        sst_stream_pos = len(before) + len(bundlesheets) + len(country)  + len(all_links)
        ext_sst = self.__ext_sst_rec(sst_stream_pos)

        return before + bundlesheets + after + ext_sst + eof + sheets

    def save(self, filename):
        import CompoundDoc

        doc = CompoundDoc.XlsDoc()
        doc.save(filename, self.get_biff_data())



########NEW FILE########
__FILENAME__ = Worksheet
# -*- coding: windows-1252 -*-
'''
            BOF
            UNCALCED
            INDEX
            Calculation Settings Block
            PRINTHEADERS
            PRINTGRIDLINES
            GRIDSET
            GUTS
            DEFAULTROWHEIGHT
            WSBOOL
            Page Settings Block
            Worksheet Protection Block
            DEFCOLWIDTH
            COLINFO
            SORT
            DIMENSIONS
            Row Blocks
            WINDOW2
            SCL
            PANE
            SELECTION
            STANDARDWIDTH
            MERGEDCELLS
            LABELRANGES
            PHONETIC
            Conditional Formatting Table
            Hyperlink Table
            Data Validity Table
            SHEETLAYOUT (BIFF8X only)
            SHEETPROTECTION (BIFF8X only)
            RANGEPROTECTION (BIFF8X only)
            EOF
'''

import BIFFRecords
import Bitmap
import Style
import tempfile

class Worksheet(object):

    # a safe default value, 3 is always valid!
    active_pane = 3
    
    #################################################################
    ## Constructor
    #################################################################
    def __init__(self, sheetname, parent_book, cell_overwrite_ok=False):
        import Row
        self.Row = Row.Row

        import Column
        self.Column = Column.Column

        self.__name = sheetname
        self.__parent = parent_book
        self._cell_overwrite_ok = cell_overwrite_ok

        self.__rows = {}
        self.__cols = {}
        self.__merged_ranges = []
        self.__bmp_rec = ''

        self.__show_formulas = 0
        self.__show_grid = 1
        self.__show_headers = 1
        self.__panes_frozen = 0
        self.show_zero_values = 1
        self.__auto_colour_grid = 1
        self.__cols_right_to_left = 0
        self.__show_outline = 1
        self.__remove_splits = 0
        # Multiple sheets can be selected, but only one can be active
        # (hold down Ctrl and click multiple tabs in the file in OOo)
        self.__selected = 0
        # "sheet_visible" should really be called "sheet_active"
        # and is 1 when this sheet is the sheet displayed when the file
        # is open. More than likely only one sheet should ever be set as
        # visible.
        # The same sheet should be specified in Workbook.active_sheet
        # (that way, both the WINDOW1 record in the book and the WINDOW2
        # records in each sheet will be in agreement)
        # The visibility of the sheet is found in the "visibility"
        # attribute obtained from the BOUNDSHEET record.
        self.__sheet_visible = 0
        self.__page_preview = 0

        self.__first_visible_row = 0
        self.__first_visible_col = 0
        self.__grid_colour = 0x40
        self.__preview_magn = 0 # use default (60%)
        self.__normal_magn = 0 # use default (100%)
        self.__scl_magn = None
        self.explicit_magn_setting = False

        self.visibility = 0 # from/to BOUNDSHEET record.

        self.__vert_split_pos = None
        self.__horz_split_pos = None
        self.__vert_split_first_visible = None
        self.__horz_split_first_visible = None

        # This is a caller-settable flag:

        self.split_position_units_are_twips = False

        # Default is False for backward compatibility with pyExcelerator
        # and previous versions of xlwt.
        #   if panes_frozen:
        #       vert/horz_split_pos are taken as number of rows/cols
        #   else: # split
        #       if split_position_units_are_twips:
        #           vert/horz_split_pos are taken as number of twips
        #       else:
        #           vert/horz_split_pos are taken as
        #           number of rows(cols) * default row(col) height (width) (i.e. 12.75 (8.43) somethings)
        #           and converted to twips by approximate formulas
        # Callers who are copying an existing file should use
        #     xlwt_worksheet.split_position_units_are_twips = True
        # because that's what's actually in the file.

		# There are 20 twips to a point. There are 72 points to an inch.

        self.__row_gut_width = 0
        self.__col_gut_height = 0

        self.__show_auto_page_breaks = 1
        self.__dialogue_sheet = 0
        self.__auto_style_outline = 0
        self.__outline_below = 0
        self.__outline_right = 0
        self.__fit_num_pages = 0
        self.__show_row_outline = 1
        self.__show_col_outline = 1
        self.__alt_expr_eval = 0
        self.__alt_formula_entries = 0

        self.__row_default_height = 0x00FF
        self.row_default_height_mismatch = 0
        self.row_default_hidden = 0
        self.row_default_space_above = 0
        self.row_default_space_below = 0

        self.__col_default_width = 0x0008

        self.__calc_mode = 1
        self.__calc_count = 0x0064
        self.__RC_ref_mode = 1
        self.__iterations_on = 0
        self.__delta = 0.001
        self.__save_recalc = 0

        self.__print_headers = 0
        self.__print_grid = 0
        self.__grid_set = 1
        self.__vert_page_breaks = []
        self.__horz_page_breaks = []
        self.__header_str = '&P'
        self.__footer_str = '&F'
        self.__print_centered_vert = 0
        self.__print_centered_horz = 1
        self.__left_margin = 0.3 #0.5
        self.__right_margin = 0.3 #0.5
        self.__top_margin = 0.61 #1.0
        self.__bottom_margin = 0.37 #1.0
        self.__paper_size_code = 9 # A4
        self.__print_scaling = 100
        self.__start_page_number = 1
        self.__fit_width_to_pages = 1
        self.__fit_height_to_pages = 1
        self.__print_in_rows = 1
        self.__portrait = 1
        self.__print_not_colour = 0
        self.__print_draft = 0
        self.__print_notes = 0
        self.__print_notes_at_end = 0
        self.__print_omit_errors = 0
        self.__print_hres = 0x012C # 300 dpi
        self.__print_vres = 0x012C # 300 dpi
        self.__header_margin = 0.1
        self.__footer_margin = 0.1
        self.__copies_num = 1

        self.__wnd_protect = 0
        self.__obj_protect = 0
        self.__protect = 0
        self.__scen_protect = 0
        self.__password = ''

        self.last_used_row = 0
        self.first_used_row = 65535
        self.last_used_col = 0
        self.first_used_col = 255
        self.row_tempfile = None
        self.__flushed_rows = {}
        self.__row_visible_levels = 0

    #################################################################
    ## Properties, "getters", "setters"
    #################################################################

    def set_name(self, value):
        self.__name = value

    def get_name(self):
        return self.__name

    name = property(get_name, set_name)

    #################################################################

    def get_parent(self):
        return self.__parent

    parent = property(get_parent)

    #################################################################

    def get_rows(self):
        return self.__rows

    rows = property(get_rows)

    #################################################################

    def get_cols(self):
        return self.__cols

    cols = property(get_cols)

    #################################################################

    def get_merged_ranges(self):
        return self.__merged_ranges

    merged_ranges = property(get_merged_ranges)

    #################################################################

    def get_bmp_rec(self):
        return self.__bmp_rec

    bmp_rec = property(get_bmp_rec)

    #################################################################

    def set_show_formulas(self, value):
        self.__show_formulas = int(value)

    def get_show_formulas(self):
        return bool(self.__show_formulas)

    show_formulas = property(get_show_formulas, set_show_formulas)

    #################################################################

    def set_show_grid(self, value):
        self.__show_grid = int(value)

    def get_show_grid(self):
        return bool(self.__show_grid)

    show_grid = property(get_show_grid, set_show_grid)

    #################################################################

    def set_show_headers(self, value):
        self.__show_headers = int(value)

    def get_show_headers(self):
        return bool(self.__show_headers)

    show_headers = property(get_show_headers, set_show_headers)

    #################################################################

    def set_panes_frozen(self, value):
        self.__panes_frozen = int(value)

    def get_panes_frozen(self):
        return bool(self.__panes_frozen)

    panes_frozen = property(get_panes_frozen, set_panes_frozen)

    #################################################################

    ### def set_show_empty_as_zero(self, value):
    ###     self.__show_empty_as_zero = int(value)

    ### def get_show_empty_as_zero(self):
    ###     return bool(self.__show_empty_as_zero)

    ### show_empty_as_zero = property(get_show_empty_as_zero, set_show_empty_as_zero)

    #################################################################

    def set_auto_colour_grid(self, value):
        self.__auto_colour_grid = int(value)

    def get_auto_colour_grid(self):
        return bool(self.__auto_colour_grid)

    auto_colour_grid = property(get_auto_colour_grid, set_auto_colour_grid)

    #################################################################

    def set_cols_right_to_left(self, value):
        self.__cols_right_to_left = int(value)

    def get_cols_right_to_left(self):
        return bool(self.__cols_right_to_left)

    cols_right_to_left = property(get_cols_right_to_left, set_cols_right_to_left)

    #################################################################

    def set_show_outline(self, value):
        self.__show_outline = int(value)

    def get_show_outline(self):
        return bool(self.__show_outline)

    show_outline = property(get_show_outline, set_show_outline)

    #################################################################

    def set_remove_splits(self, value):
        self.__remove_splits = int(value)

    def get_remove_splits(self):
        return bool(self.__remove_splits)

    remove_splits = property(get_remove_splits, set_remove_splits)

    #################################################################

    def set_selected(self, value):
        self.__selected = int(value)

    def get_selected(self):
        return bool(self.__selected)

    selected = property(get_selected, set_selected)

    #################################################################

    def set_sheet_visible(self, value):
        self.__sheet_visible = int(value)

    def get_sheet_visible(self):
        return bool(self.__sheet_visible)

    sheet_visible = property(get_sheet_visible, set_sheet_visible)

    #################################################################

    def set_page_preview(self, value):
        self.__page_preview = int(value)

    def get_page_preview(self):
        return bool(self.__page_preview)

    page_preview = property(get_page_preview, set_page_preview)

    #################################################################

    def set_first_visible_row(self, value):
        self.__first_visible_row = value

    def get_first_visible_row(self):
        return self.__first_visible_row

    first_visible_row = property(get_first_visible_row, set_first_visible_row)

    #################################################################

    def set_first_visible_col(self, value):
        self.__first_visible_col = value

    def get_first_visible_col(self):
        return self.__first_visible_col

    first_visible_col = property(get_first_visible_col, set_first_visible_col)

    #################################################################

    def set_grid_colour(self, value):
        self.__grid_colour = value

    def get_grid_colour(self):
        return self.__grid_colour

    grid_colour = property(get_grid_colour, set_grid_colour)

    #################################################################

    def set_preview_magn(self, value):
        self.__preview_magn = value

    def get_preview_magn(self):
        return self.__preview_magn

    preview_magn = property(get_preview_magn, set_preview_magn)

    #################################################################

    def set_normal_magn(self, value):
        self.__normal_magn = value

    def get_normal_magn(self):
        return self.__normal_magn

    normal_magn = property(get_normal_magn, set_normal_magn)

    #################################################################

    def set_scl_magn(self, value):
        self.__scl_magn = value

    def get_scl_magn(self):
        return self.__scl_magn

    scl_magn = property(get_scl_magn, set_scl_magn)


    #################################################################

    def set_vert_split_pos(self, value):
        self.__vert_split_pos = abs(value)

    def get_vert_split_pos(self):
        return self.__vert_split_pos

    vert_split_pos = property(get_vert_split_pos, set_vert_split_pos)

    #################################################################

    def set_horz_split_pos(self, value):
        self.__horz_split_pos = abs(value)

    def get_horz_split_pos(self):
        return self.__horz_split_pos

    horz_split_pos = property(get_horz_split_pos, set_horz_split_pos)

    #################################################################

    def set_vert_split_first_visible(self, value):
        self.__vert_split_first_visible = abs(value)

    def get_vert_split_first_visible(self):
        return self.__vert_split_first_visible

    vert_split_first_visible = property(get_vert_split_first_visible, set_vert_split_first_visible)

    #################################################################

    def set_horz_split_first_visible(self, value):
        self.__horz_split_first_visible = abs(value)

    def get_horz_split_first_visible(self):
        return self.__horz_split_first_visible

    horz_split_first_visible = property(get_horz_split_first_visible, set_horz_split_first_visible)

    #################################################################

    #def set_row_gut_width(self, value):
    #    self.__row_gut_width = value
    #
    #def get_row_gut_width(self):
    #    return self.__row_gut_width
    #
    #row_gut_width = property(get_row_gut_width, set_row_gut_width)
    #
    #################################################################
    #
    #def set_col_gut_height(self, value):
    #    self.__col_gut_height = value
    #
    #def get_col_gut_height(self):
    #    return self.__col_gut_height
    #
    #col_gut_height = property(get_col_gut_height, set_col_gut_height)
    #
    #################################################################

    def set_show_auto_page_breaks(self, value):
        self.__show_auto_page_breaks = int(value)

    def get_show_auto_page_breaks(self):
        return bool(self.__show_auto_page_breaks)

    show_auto_page_breaks = property(get_show_auto_page_breaks, set_show_auto_page_breaks)

    #################################################################

    def set_dialogue_sheet(self, value):
        self.__dialogue_sheet = int(value)

    def get_dialogue_sheet(self):
        return bool(self.__dialogue_sheet)

    dialogue_sheet = property(get_dialogue_sheet, set_dialogue_sheet)

    #################################################################

    def set_auto_style_outline(self, value):
        self.__auto_style_outline = int(value)

    def get_auto_style_outline(self):
        return bool(self.__auto_style_outline)

    auto_style_outline = property(get_auto_style_outline, set_auto_style_outline)

    #################################################################

    def set_outline_below(self, value):
        self.__outline_below = int(value)

    def get_outline_below(self):
        return bool(self.__outline_below)

    outline_below = property(get_outline_below, set_outline_below)

    #################################################################

    def set_outline_right(self, value):
        self.__outline_right = int(value)

    def get_outline_right(self):
        return bool(self.__outline_right)

    outline_right = property(get_outline_right, set_outline_right)

    #################################################################

    def set_fit_num_pages(self, value):
        self.__fit_num_pages = value

    def get_fit_num_pages(self):
        return self.__fit_num_pages

    fit_num_pages = property(get_fit_num_pages, set_fit_num_pages)

    #################################################################

    def set_show_row_outline(self, value):
        self.__show_row_outline = int(value)

    def get_show_row_outline(self):
        return bool(self.__show_row_outline)

    show_row_outline = property(get_show_row_outline, set_show_row_outline)

    #################################################################

    def set_show_col_outline(self, value):
        self.__show_col_outline = int(value)

    def get_show_col_outline(self):
        return bool(self.__show_col_outline)

    show_col_outline = property(get_show_col_outline, set_show_col_outline)

    #################################################################

    def set_alt_expr_eval(self, value):
        self.__alt_expr_eval = int(value)

    def get_alt_expr_eval(self):
        return bool(self.__alt_expr_eval)

    alt_expr_eval = property(get_alt_expr_eval, set_alt_expr_eval)

    #################################################################

    def set_alt_formula_entries(self, value):
        self.__alt_formula_entries = int(value)

    def get_alt_formula_entries(self):
        return bool(self.__alt_formula_entries)

    alt_formula_entries = property(get_alt_formula_entries, set_alt_formula_entries)

    #################################################################

    def set_row_default_height(self, value):
        self.__row_default_height = value

    def get_row_default_height(self):
        return self.__row_default_height

    row_default_height = property(get_row_default_height, set_row_default_height)

    #################################################################

    def set_col_default_width(self, value):
        self.__col_default_width = value

    def get_col_default_width(self):
        return self.__col_default_width

    col_default_width = property(get_col_default_width, set_col_default_width)

    #################################################################

    def set_calc_mode(self, value):
        self.__calc_mode = value & 0x03

    def get_calc_mode(self):
        return self.__calc_mode

    calc_mode = property(get_calc_mode, set_calc_mode)

    #################################################################

    def set_calc_count(self, value):
        self.__calc_count = value

    def get_calc_count(self):
        return self.__calc_count

    calc_count = property(get_calc_count, set_calc_count)

    #################################################################

    def set_RC_ref_mode(self, value):
        self.__RC_ref_mode = int(value)

    def get_RC_ref_mode(self):
        return bool(self.__RC_ref_mode)

    RC_ref_mode = property(get_RC_ref_mode, set_RC_ref_mode)

    #################################################################

    def set_iterations_on(self, value):
        self.__iterations_on = int(value)

    def get_iterations_on(self):
        return bool(self.__iterations_on)

    iterations_on = property(get_iterations_on, set_iterations_on)

    #################################################################

    def set_delta(self, value):
        self.__delta = value

    def get_delta(self):
        return self.__delta

    delta = property(get_delta, set_delta)

    #################################################################

    def set_save_recalc(self, value):
        self.__save_recalc = int(value)

    def get_save_recalc(self):
        return bool(self.__save_recalc)

    save_recalc = property(get_save_recalc, set_save_recalc)

    #################################################################

    def set_print_headers(self, value):
        self.__print_headers = int(value)

    def get_print_headers(self):
        return bool(self.__print_headers)

    print_headers = property(get_print_headers, set_print_headers)

    #################################################################

    def set_print_grid(self, value):
        self.__print_grid = int(value)

    def get_print_grid(self):
        return bool(self.__print_grid)

    print_grid = property(get_print_grid, set_print_grid)

    #################################################################
    #
    #def set_grid_set(self, value):
    #    self.__grid_set = int(value)
    #
    #def get_grid_set(self):
    #    return bool(self.__grid_set)
    #
    #grid_set = property(get_grid_set, set_grid_set)
    #
    #################################################################

    def set_vert_page_breaks(self, value):
        self.__vert_page_breaks = value

    def get_vert_page_breaks(self):
        return self.__vert_page_breaks

    vert_page_breaks = property(get_vert_page_breaks, set_vert_page_breaks)

    #################################################################

    def set_horz_page_breaks(self, value):
        self.__horz_page_breaks = value

    def get_horz_page_breaks(self):
        return self.__horz_page_breaks

    horz_page_breaks = property(get_horz_page_breaks, set_horz_page_breaks)

    #################################################################

    def set_header_str(self, value):
        if isinstance(value, str):
            value = unicode(value, self.__parent.encoding)
        self.__header_str = value

    def get_header_str(self):
        return self.__header_str

    header_str = property(get_header_str, set_header_str)

    #################################################################

    def set_footer_str(self, value):
        if isinstance(value, str):
            value = unicode(value, self.__parent.encoding)
        self.__footer_str = value

    def get_footer_str(self):
        return self.__footer_str

    footer_str = property(get_footer_str, set_footer_str)

    #################################################################

    def set_print_centered_vert(self, value):
        self.__print_centered_vert = int(value)

    def get_print_centered_vert(self):
        return bool(self.__print_centered_vert)

    print_centered_vert = property(get_print_centered_vert, set_print_centered_vert)

    #################################################################

    def set_print_centered_horz(self, value):
        self.__print_centered_horz = int(value)

    def get_print_centered_horz(self):
        return bool(self.__print_centered_horz)

    print_centered_horz = property(get_print_centered_horz, set_print_centered_horz)

    #################################################################

    def set_left_margin(self, value):
        self.__left_margin = value

    def get_left_margin(self):
        return self.__left_margin

    left_margin = property(get_left_margin, set_left_margin)

    #################################################################

    def set_right_margin(self, value):
        self.__right_margin = value

    def get_right_margin(self):
        return self.__right_margin

    right_margin = property(get_right_margin, set_right_margin)

    #################################################################

    def set_top_margin(self, value):
        self.__top_margin = value

    def get_top_margin(self):
        return self.__top_margin

    top_margin = property(get_top_margin, set_top_margin)

    #################################################################

    def set_bottom_margin(self, value):
        self.__bottom_margin = value

    def get_bottom_margin(self):
        return self.__bottom_margin

    bottom_margin = property(get_bottom_margin, set_bottom_margin)

    #################################################################

    def set_paper_size_code(self, value):
        self.__paper_size_code = value

    def get_paper_size_code(self):
        return self.__paper_size_code

    paper_size_code = property(get_paper_size_code, set_paper_size_code)

    #################################################################

    def set_print_scaling(self, value):
        self.__print_scaling = value

    def get_print_scaling(self):
        return self.__print_scaling

    print_scaling = property(get_print_scaling, set_print_scaling)

    #################################################################

    def set_start_page_number(self, value):
        self.__start_page_number = value

    def get_start_page_number(self):
        return self.__start_page_number

    start_page_number = property(get_start_page_number, set_start_page_number)

    #################################################################

    def set_fit_width_to_pages(self, value):
        self.__fit_width_to_pages = value

    def get_fit_width_to_pages(self):
        return self.__fit_width_to_pages

    fit_width_to_pages = property(get_fit_width_to_pages, set_fit_width_to_pages)

    #################################################################

    def set_fit_height_to_pages(self, value):
        self.__fit_height_to_pages = value

    def get_fit_height_to_pages(self):
        return self.__fit_height_to_pages

    fit_height_to_pages = property(get_fit_height_to_pages, set_fit_height_to_pages)

    #################################################################

    def set_print_in_rows(self, value):
        self.__print_in_rows = int(value)

    def get_print_in_rows(self):
        return bool(self.__print_in_rows)

    print_in_rows = property(get_print_in_rows, set_print_in_rows)

    #################################################################

    def set_portrait(self, value):
        self.__portrait = int(value)

    def get_portrait(self):
        return bool(self.__portrait)

    portrait = property(get_portrait, set_portrait)

    #################################################################

    def set_print_colour(self, value):
        self.__print_not_colour = int(not value)

    def get_print_colour(self):
        return not bool(self.__print_not_colour)

    print_colour = property(get_print_colour, set_print_colour)

    #################################################################

    def set_print_draft(self, value):
        self.__print_draft = int(value)

    def get_print_draft(self):
        return bool(self.__print_draft)

    print_draft = property(get_print_draft, set_print_draft)

    #################################################################

    def set_print_notes(self, value):
        self.__print_notes = int(value)

    def get_print_notes(self):
        return bool(self.__print_notes)

    print_notes = property(get_print_notes, set_print_notes)

    #################################################################

    def set_print_notes_at_end(self, value):
        self.__print_notes_at_end = int(value)

    def get_print_notes_at_end(self):
        return bool(self.__print_notes_at_end)

    print_notes_at_end = property(get_print_notes_at_end, set_print_notes_at_end)

    #################################################################

    def set_print_omit_errors(self, value):
        self.__print_omit_errors = int(value)

    def get_print_omit_errors(self):
        return bool(self.__print_omit_errors)

    print_omit_errors = property(get_print_omit_errors, set_print_omit_errors)

    #################################################################

    def set_print_hres(self, value):
        self.__print_hres = value

    def get_print_hres(self):
        return self.__print_hres

    print_hres = property(get_print_hres, set_print_hres)

    #################################################################

    def set_print_vres(self, value):
        self.__print_vres = value

    def get_print_vres(self):
        return self.__print_vres

    print_vres = property(get_print_vres, set_print_vres)

    #################################################################

    def set_header_margin(self, value):
        self.__header_margin = value

    def get_header_margin(self):
        return self.__header_margin

    header_margin = property(get_header_margin, set_header_margin)

    #################################################################

    def set_footer_margin(self, value):
        self.__footer_margin = value

    def get_footer_margin(self):
        return self.__footer_margin

    footer_margin = property(get_footer_margin, set_footer_margin)

    #################################################################

    def set_copies_num(self, value):
        self.__copies_num = value

    def get_copies_num(self):
        return self.__copies_num

    copies_num = property(get_copies_num, set_copies_num)

    ##################################################################

    def set_wnd_protect(self, value):
        self.__wnd_protect = int(value)

    def get_wnd_protect(self):
        return bool(self.__wnd_protect)

    wnd_protect = property(get_wnd_protect, set_wnd_protect)

    #################################################################

    def set_obj_protect(self, value):
        self.__obj_protect = int(value)

    def get_obj_protect(self):
        return bool(self.__obj_protect)

    obj_protect = property(get_obj_protect, set_obj_protect)

    #################################################################

    def set_protect(self, value):
        self.__protect = int(value)

    def get_protect(self):
        return bool(self.__protect)

    protect = property(get_protect, set_protect)

    #################################################################

    def set_scen_protect(self, value):
        self.__scen_protect = int(value)

    def get_scen_protect(self):
        return bool(self.__scen_protect)

    scen_protect = property(get_scen_protect, set_scen_protect)

    #################################################################

    def set_password(self, value):
        self.__password = value

    def get_password(self):
        return self.__password

    password = property(get_password, set_password)

    ##################################################################
    ## Methods
    ##################################################################

    def get_parent(self):
        return self.__parent

    def write(self, r, c, label="", style=Style.default_style):
        self.row(r).write(c, label, style)

    def write_rich_text(self, r, c, rich_text_list, style=Style.default_style):
        self.row(r).set_cell_rich_text(c, rich_text_list, style)

    def merge(self, r1, r2, c1, c2, style=Style.default_style):
        # Stand-alone merge of previously written cells.
        # Problems: (1) style to be used should be existing style of
        # the top-left cell, not an arg.
        # (2) should ensure that any previous data value in
        # non-top-left cells is nobbled.
        # Note: if a cell is set by a data record then later
        # is referenced by a [MUL]BLANK record, Excel will blank
        # out the cell on the screen, but OOo & Gnu will not
        # blank it out. Need to do something better than writing
        # multiple records. In the meantime, avoid this method and use
        # write_merge() instead.
        if c2 > c1:
            self.row(r1).write_blanks(c1 + 1, c2,  style)
        for r in range(r1+1, r2+1):
            self.row(r).write_blanks(c1, c2,  style)
        self.__merged_ranges.append((r1, r2, c1, c2))

    def write_merge(self, r1, r2, c1, c2, label="", style=Style.default_style):
        assert 0 <= c1 <= c2 <= 255
        assert 0 <= r1 <= r2 <= 65535
        self.write(r1, c1, label, style)
        if c2 > c1:
            self.row(r1).write_blanks(c1 + 1, c2,  style) # skip (r1, c1)
        for r in range(r1+1, r2+1):
            self.row(r).write_blanks(c1, c2,  style)
        self.__merged_ranges.append((r1, r2, c1, c2))

    def insert_bitmap(self, filename, row, col, x = 0, y = 0, scale_x = 1, scale_y = 1):
        bmp = Bitmap.ImDataBmpRecord(filename)
        obj = Bitmap.ObjBmpRecord(row, col, self, bmp, x, y, scale_x, scale_y)

        self.__bmp_rec += obj.get() + bmp.get()

    def col(self, indx):
        if indx not in self.__cols:
            self.__cols[indx] = self.Column(indx, self)
        return self.__cols[indx]

    def row(self, indx):
        if indx not in self.__rows:
            if indx in self.__flushed_rows:
                raise Exception("Attempt to reuse row index %d of sheet %r after flushing" % (indx, self.__name))
            self.__rows[indx] = self.Row(indx, self)
            if indx > self.last_used_row:
                self.last_used_row = indx
            if indx < self.first_used_row:
                self.first_used_row = indx
        return self.__rows[indx]

    def row_height(self, row): # in pixels
        if row in self.__rows:
            return self.__rows[row].get_height_in_pixels()
        else:
            return 17

    def col_width(self, col): # in pixels
        if col in self.__cols:
            return self.__cols[col].width_in_pixels()
        else:
            return 64


    ##################################################################
    ## BIFF records generation
    ##################################################################

    def __bof_rec(self):
        return BIFFRecords.Biff8BOFRecord(BIFFRecords.Biff8BOFRecord.WORKSHEET).get()

    def __update_row_visible_levels(self):
        if self.__rows:
            temp = max([self.__rows[r].level for r in self.__rows]) + 1
            self.__row_visible_levels = max(temp, self.__row_visible_levels)

    def __guts_rec(self):
        self.__update_row_visible_levels()
        col_visible_levels = 0
        if len(self.__cols) != 0:
            col_visible_levels = max([self.__cols[c].level for c in self.__cols]) + 1
        return BIFFRecords.GutsRecord(
            self.__row_gut_width, self.__col_gut_height, self.__row_visible_levels, col_visible_levels).get()

    def __defaultrowheight_rec(self):
        options = 0x0000
        options |= (self.row_default_height_mismatch & 1) << 0
        options |= (self.row_default_hidden & 1) << 1
        options |= (self.row_default_space_above & 1) << 2
        options |= (self.row_default_space_below & 1) << 3
        defht = self.__row_default_height
        return BIFFRecords.DefaultRowHeightRecord(options, defht).get()

    def __wsbool_rec(self):
        options = 0x00
        options |= (self.__show_auto_page_breaks & 0x01) << 0
        options |= (self.__dialogue_sheet & 0x01) << 4
        options |= (self.__auto_style_outline & 0x01) << 5
        options |= (self.__outline_below & 0x01) << 6
        options |= (self.__outline_right & 0x01) << 7
        options |= (self.__fit_num_pages & 0x01) << 8
        options |= (self.__show_row_outline & 0x01) << 10
        options |= (self.__show_col_outline & 0x01) << 11
        options |= (self.__alt_expr_eval & 0x01) << 14
        options |= (self.__alt_formula_entries & 0x01) << 15

        return BIFFRecords.WSBoolRecord(options).get()

    def __eof_rec(self):
        return BIFFRecords.EOFRecord().get()

    def __colinfo_rec(self):
        result = ''
        for col in self.__cols:
            result += self.__cols[col].get_biff_record()
        return result

    def __dimensions_rec(self):
        return BIFFRecords.DimensionsRecord(
            self.first_used_row, self.last_used_row,
            self.first_used_col, self.last_used_col
            ).get()

    def __window2_rec(self):
        # Appends SCL record.
        options = 0
        options |= (self.__show_formulas        & 0x01) << 0
        options |= (self.__show_grid            & 0x01) << 1
        options |= (self.__show_headers         & 0x01) << 2
        options |= (self.__panes_frozen         & 0x01) << 3
        options |= (self.show_zero_values       & 0x01) << 4
        options |= (self.__auto_colour_grid     & 0x01) << 5
        options |= (self.__cols_right_to_left   & 0x01) << 6
        options |= (self.__show_outline         & 0x01) << 7
        options |= (self.__remove_splits        & 0x01) << 8
        options |= (self.__selected             & 0x01) << 9
        options |= (self.__sheet_visible        & 0x01) << 10
        options |= (self.__page_preview         & 0x01) << 11
        if self.explicit_magn_setting:
            # Experimentation: caller can set the scl magn.
            # None -> no SCL record written
            # Otherwise 10 <= scl_magn <= 400 or scl_magn == 0
            # Note: value 0 means use 100 for normal view, 60 for page break preview
            # BREAKING NEWS: Excel interprets scl_magn = 0 very literally, your
            # sheet appears like a tiny dot on the screen
            scl_magn = self.__scl_magn
        else:
            if self.__page_preview:
                scl_magn = self.__preview_magn
                magn_default = 60
            else:
                scl_magn = self.__normal_magn
                magn_default = 100
            if scl_magn == magn_default or scl_magn == 0:
                # Emulate what we think MS does
                scl_magn = None # don't write an SCL record
        return BIFFRecords.Window2Record(
            options, self.__first_visible_row, self.__first_visible_col,
            self.__grid_colour,
            self.__preview_magn, self.__normal_magn, scl_magn).get()

    def __panes_rec(self):
        if self.__vert_split_pos is None and self.__horz_split_pos is None:
            return ""

        if self.__vert_split_pos is None:
            self.__vert_split_pos = 0
        if self.__horz_split_pos is None:
            self.__horz_split_pos = 0

        if self.__panes_frozen:
            if self.__vert_split_first_visible is None:
                self.__vert_split_first_visible = self.__vert_split_pos
            if self.__horz_split_first_visible is None:
                self.__horz_split_first_visible = self.__horz_split_pos

            # when frozen, the active pane has to be specifically set:
            if self.__vert_split_pos > 0 and self.__horz_split_pos > 0:
                active_pane = 0
            elif self.__vert_split_pos > 0 and self.__horz_split_pos == 0:
                active_pane = 1
            elif self.__vert_split_pos == 0 and self.__horz_split_pos > 0:
                active_pane = 2
            else:
                active_pane = 3
        else:
            if self.__vert_split_first_visible is None:
                self.__vert_split_first_visible = 0
            if self.__horz_split_first_visible is None:
                self.__horz_split_first_visible = 0
            if not self.split_position_units_are_twips:
                # inspired by pyXLWriter
                if self.__horz_split_pos > 0:
                    self.__horz_split_pos = 20 * self.__horz_split_pos + 255
                if self.__vert_split_pos > 0:
                    self.__vert_split_pos = 113.879 * self.__vert_split_pos + 390

            # when split, the active pain can be set as required:
            active_pane = self.active_pane

        result = BIFFRecords.PanesRecord(*map(int, (
            self.__vert_split_pos,
            self.__horz_split_pos,
            self.__horz_split_first_visible,
            self.__vert_split_first_visible,
            active_pane
            ))).get()

        return result

    def __row_blocks_rec(self):
        result = []
        for row in self.__rows.itervalues():
            result.append(row.get_row_biff_data())
            result.append(row.get_cells_biff_data())
        return ''.join(result)

    def __merged_rec(self):
        return BIFFRecords.MergedCellsRecord(self.__merged_ranges).get()

    def __bitmaps_rec(self):
        return self.__bmp_rec

    def __calc_settings_rec(self):
        result = ''
        result += BIFFRecords.CalcModeRecord(self.__calc_mode & 0x01).get()
        result += BIFFRecords.CalcCountRecord(self.__calc_count & 0xFFFF).get()
        result += BIFFRecords.RefModeRecord(self.__RC_ref_mode & 0x01).get()
        result += BIFFRecords.IterationRecord(self.__iterations_on & 0x01).get()
        result += BIFFRecords.DeltaRecord(self.__delta).get()
        result += BIFFRecords.SaveRecalcRecord(self.__save_recalc & 0x01).get()
        return result

    def __print_settings_rec(self):
        result = ''
        result += BIFFRecords.PrintHeadersRecord(self.__print_headers).get()
        result += BIFFRecords.PrintGridLinesRecord(self.__print_grid).get()
        result += BIFFRecords.GridSetRecord(self.__grid_set).get()
        result += BIFFRecords.HorizontalPageBreaksRecord(self.__horz_page_breaks).get()
        result += BIFFRecords.VerticalPageBreaksRecord(self.__vert_page_breaks).get()
        result += BIFFRecords.HeaderRecord(self.__header_str).get()
        result += BIFFRecords.FooterRecord(self.__footer_str).get()
        result += BIFFRecords.HCenterRecord(self.__print_centered_horz).get()
        result += BIFFRecords.VCenterRecord(self.__print_centered_vert).get()
        result += BIFFRecords.LeftMarginRecord(self.__left_margin).get()
        result += BIFFRecords.RightMarginRecord(self.__right_margin).get()
        result += BIFFRecords.TopMarginRecord(self.__top_margin).get()
        result += BIFFRecords.BottomMarginRecord(self.__bottom_margin).get()

        setup_page_options =  (self.__print_in_rows & 0x01) << 0
        setup_page_options |=  (self.__portrait & 0x01) << 1
        setup_page_options |=  (0x00 & 0x01) << 2
        setup_page_options |=  (self.__print_not_colour & 0x01) << 3
        setup_page_options |=  (self.__print_draft & 0x01) << 4
        setup_page_options |=  (self.__print_notes & 0x01) << 5
        setup_page_options |=  (0x00 & 0x01) << 6
        setup_page_options |=  (0x01 & 0x01) << 7
        setup_page_options |=  (self.__print_notes_at_end & 0x01) << 9
        setup_page_options |=  (self.__print_omit_errors & 0x03) << 10

        result += BIFFRecords.SetupPageRecord(self.__paper_size_code,
                                self.__print_scaling,
                                self.__start_page_number,
                                self.__fit_width_to_pages,
                                self.__fit_height_to_pages,
                                setup_page_options,
                                self.__print_hres,
                                self.__print_vres,
                                self.__header_margin,
                                self.__footer_margin,
                                self.__copies_num).get()
        return result

    def __protection_rec(self):
        result = ''
        result += BIFFRecords.ProtectRecord(self.__protect).get()
        result += BIFFRecords.ScenProtectRecord(self.__scen_protect).get()
        result += BIFFRecords.WindowProtectRecord(self.__wnd_protect).get()
        result += BIFFRecords.ObjectProtectRecord(self.__obj_protect).get()
        result += BIFFRecords.PasswordRecord(self.__password).get()
        return result

    def get_biff_data(self):
        result = [
            self.__bof_rec(),
            self.__calc_settings_rec(),
            self.__guts_rec(),
            self.__defaultrowheight_rec(),
            self.__wsbool_rec(),
            self.__colinfo_rec(),
            self.__dimensions_rec(),
            self.__print_settings_rec(),
            self.__protection_rec(),
            ]
        if self.row_tempfile:
            self.row_tempfile.flush()
            self.row_tempfile.seek(0)
            result.append(self.row_tempfile.read())
            self.row_tempfile.seek(0, 2) # to EOF
            # Above seek() is necessary to avoid a spurious IOError
            # with Errno 0 if the caller continues on writing rows
            # and flushing row data after the save().
            # See http://bugs.python.org/issue3207
        result.extend([
            self.__row_blocks_rec(),
            self.__merged_rec(),
            self.__bitmaps_rec(),
            self.__window2_rec(),
            self.__panes_rec(),
            self.__eof_rec(),
            ])
        return ''.join(result)

    def flush_row_data(self):
        if self.row_tempfile is None:
            self.row_tempfile = tempfile.TemporaryFile()
        self.row_tempfile.write(self.__row_blocks_rec())
        for rowx in self.__rows:
            self.__flushed_rows[rowx] = 1
        self.__update_row_visible_levels()
        self.__rows = {}



########NEW FILE########
